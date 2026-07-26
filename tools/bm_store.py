#!/usr/bin/env python3
"""BrotherMode V2 engine core: the ONE transactional store every ownership
mutation goes through (Decision 2, ratified spec 2026-07-26). Nothing else in
this project is allowed to be the source of truth for who owns what work.

WHY THIS EXISTS
  The V1 registries (bm_registry.py plus hand-maintained STATE.md prose) let
  two sessions each believe they held a fence over the same files (F1, F2,
  F11), let a second session silently take over a name someone else was
  actively working under (F3), let two handovers collide on a truncated
  fingerprint and drop the second one (F13), and could not tell a healthy
  empty registry from one a crash had truncated to nothing (F9). None of
  those were one-off bugs: they were the shape you get from a JSON file
  guarded by an advisory lock, asked to also behave like a transactional
  ledger. sqlite3 in WAL mode, one lifecycle_uuid per unit of work that is
  NEVER reused, and two explicit, opposite failure policies close the whole
  class at once rather than patching each instance as it resurfaces.

THE CONTRACT
  - ONE CANONICAL ROOT: resolve_root() walks BROTHERMODE_ROOT, then markers,
    then .git, in that order, never os.getcwd() alone.
  - ONE TRANSACTIONAL STORE: this module is the only writer of
    <root>/.brothermode/store.sqlite3. STATE.md is a GENERATED view, never
    hand-edited truth: render_state_md/write_state_view regenerate it and
    leave any human prose outside its markers untouched.
  - ONE IMMUTABLE IDENTITY: every record's lifecycle_uuid is permanent and
    reused by nothing; every mutation names an expected_version and fails
    CLOSED (StaleIdentity) the moment that version no longer matches.
  - TWO FAILURE POLICIES, EXPLICIT: ownership and lifecycle mutations here
    refuse rather than guess (OwnershipRefused, StaleIdentity, StoreCorrupt).
    The render functions (render_digest, render_state_md, dump) are the
    advisory exception on purpose: handed a missing record they degrade to a
    plain "(no such record)" string instead of raising, because a display
    function that crashes a session over stale digest text is a worse
    failure than one ugly line of output.

Python 3.9, standard library only. No network, no subprocess: root
resolution walks the filesystem directly rather than shelling out to git.
No em or en dashes anywhere in this file, its comments, or its output.
"""
import contextlib
import datetime
import hashlib
import io
import json
import os
import posixpath
import sqlite3
import sys
import tempfile
import uuid

SCHEMA_VERSION = 1
STORE_DIRNAME = ".brothermode"
STORE_FILENAME = "store.sqlite3"
MAX_ACTIVE_PERSISTENT = 3

_STATE_BEGIN = "<!-- BEGIN GENERATED BROTHERMODE STATE (edit outside these markers only) -->"
_STATE_END = "<!-- END GENERATED BROTHERMODE STATE -->"
_MARKER_ESCAPE = "[marker text neutralized]"


def _neutralize_markers(s):
    """Defuse literal occurrences of the BEGIN/END marker strings inside
    founder-typed text before it enters a generated view (GATE 8b, fix-round
    2026-07-26): an objective containing the exact END marker text let
    write_state_view's naive string split find a FAKE marker inside the
    supposedly-generated block, corrupting the human-prose boundary and
    growing an extra marker pair on every subsequent render."""
    if not s:
        return s
    return s.replace(_STATE_BEGIN, _MARKER_ESCAPE).replace(_STATE_END, _MARKER_ESCAPE)


_SECTION_BUDGETS = {
    "header": 400,
    "next_intent": 900,
    "blockers": 600,
    "files_note": 600,
    "decisions_new": 1200,
    "decisions_old": 300,
}


def now_iso():
    """UTC, second precision, ISO 8601. Every timestamp this module writes
    uses this one function, so two rows written a millisecond apart cannot
    be compared as if they were microsecond-precise."""
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Root resolution (fixes F2, F42, the F2b class): one canonical root, never
# os.getcwd() used as an anchor by anything downstream of resolve_root().
# ---------------------------------------------------------------------------

def _walk_up(start):
    """Every ancestor of start, closest first, ending at the filesystem or
    drive root. A plain function (not a generator) so resolve_root can walk
    the same chain twice, once for markers and once for .git, without either
    pass affecting the other."""
    out = []
    cur = start
    while True:
        out.append(cur)
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return out


def resolve_root(start=None):
    """Return (root_path, source), source in ("env", "marker", "git"), or
    (None, None) when nothing anchors a project here.

    Order matters and is deliberate: BROTHERMODE_ROOT always wins because a
    human or a script set it on purpose. Failing that, a marker directory
    ANYWHERE up the tree beats a closer .git, so once `init` has run, a
    nested .git (a submodule, a vendored dependency) can never shadow the
    real project root (fixes F2 / F42 / the F2b class)."""
    env = os.environ.get("BROTHERMODE_ROOT")
    if env:
        p = os.path.realpath(env)
        if os.path.isdir(p):
            return p, "env"
    cur = os.path.realpath(start or os.getcwd())
    chain = _walk_up(cur)
    for d in chain:
        if os.path.isdir(os.path.join(d, ".brothermode")):
            return d, "marker"
    for d in chain:
        # .git is a directory in a normal clone and a FILE in a worktree
        # (it holds "gitdir: <path>"); os.path.exists covers both, so
        # worktrees resolve a root the same way a normal checkout does.
        if os.path.exists(os.path.join(d, ".git")):
            return d, "git"
    return None, None


def require_root(start=None):
    """resolve_root(), or an OwnershipRefused the CLI (or any other caller)
    can render as a clear next step. "No root" is itself an ownership
    refusal, not a crash: nothing was touched, and the message says exactly
    what to run."""
    root, source = resolve_root(start)
    if root is None:
        raise OwnershipRefused(
            "no-root",
            "no BrotherMode project root found (checked BROTHERMODE_ROOT, "
            "then every parent directory for .brothermode/, then for .git). "
            "Run `python3 tools/bm_store.py init` here or in the intended "
            "project root, or set BROTHERMODE_ROOT to point at it.",
            details={"start": os.path.realpath(start or os.getcwd())})
    return root, source


def store_dir(root):
    return os.path.join(root, STORE_DIRNAME)


def store_path(root):
    return os.path.join(store_dir(root), STORE_FILENAME)


# ---------------------------------------------------------------------------
# Name validation (fixes F4): reject, never normalize.
# ---------------------------------------------------------------------------

_NAME_INVALID_CHARS = frozenset('/\\:?*"<>|')


def valid_name(name):
    """Reject anything that is not a plain, filesystem-safe label and say
    exactly why. NO silent normalization, on purpose: a caller who typos a
    name gets a clear refusal, not a program that quietly folds "Payments!"
    and "Payments_" into the same fenced record (the collision class F4
    exists to close). Returns name unchanged when it is valid."""
    if not isinstance(name, str) or not name:
        raise ValueError("name must be a non-empty string")
    if name in (".", ".."):
        raise ValueError("name may not be '%s'" % name)
    if name.startswith("."):
        raise ValueError("name may not start with '.': %r" % name)
    bad = _NAME_INVALID_CHARS.intersection(name)
    if bad:
        raise ValueError(
            "name contains a reserved character (%s): %r"
            % (" ".join(sorted(bad)), name))
    if any(ch.isspace() for ch in name):
        raise ValueError("name may not contain whitespace: %r" % name)
    if len(name) > 60:
        raise ValueError("name is longer than 60 characters: %r" % name)
    # GATE 9 (fix-round 2026-07-26): printable ASCII only, rejecting NUL and
    # every other control character. Without this, a non-ASCII name reached
    # sqlite3.connect fine and only failed later when the CLI tried to PRINT
    # it back on a narrow-encoding stdout, by which point the record had
    # already committed: the failure surfaced as a misreported refusal
    # AFTER a real success. Rejecting here, before any write, means a bad
    # name is refused honestly instead of committed-then-misreported.
    if not (name.isascii() and name.isprintable()):
        raise ValueError(
            "name must be printable ASCII with no control characters: %r" % name)
    return name


def thread_dir_name(name, lifecycle_uuid):
    """threads/<name>-<lifecycle_uuid[:8]>/, per the ratified spec. Not
    consumed until Phase 3 (thread working directories), but the naming rule
    is part of this contract: a new lifecycle can never inherit an old
    lifecycle's on-disk working directory (fixes F14), because the directory
    name itself changes every time the identity does."""
    valid_name(name)
    return "%s-%s" % (name, lifecycle_uuid[:8])


# ---------------------------------------------------------------------------
# Overlap semantics (fixes F1, F2, F11): conservative on purpose.
# Over-blocking costs one refusal to explain; under-blocking loses work.
# ---------------------------------------------------------------------------

def _to_posix(p):
    """Forward-slash form with '.' and '..' segments resolved lexically via
    posixpath.normpath (GATE 1, fix-round 2026-07-26: paths_overlap('db.py',
    'api/../db.py') was False, because '..' was never resolved before
    comparison). This is PURE, no filesystem and no root: it cannot reject
    an escape (that needs canonicalize_path, below, which knows the root).
    The whole-root case ('.', '', './.') normalizes to '.', which
    paths_overlap treats as overlapping everything."""
    p = (p or "").strip()
    if not p:
        return ""
    p = p.replace("\\", "/")
    p = posixpath.normpath(p)
    return p


_CASE_INSENSITIVE_PLATFORMS = ("win32", "darwin")


def _normcase(p):
    """Case-fold the POSIX-form string directly with str.casefold(). NEVER
    route this through os.path.normcase: on win32 that function IS
    ntpath.normcase, which rewrites '/' to '\\' before any of this module's
    separator-boundary checks run, so 'api' vs 'api/pay.py' silently stopped
    conflicting (GATE 2, fix-round 2026-07-26, reproduced by substituting
    ntpath.normcase for os.path.normcase). Gated on platform case
    insensitivity: win32 and darwin fold, every other POSIX platform (Linux
    and friends, case-sensitive default filesystems) does not."""
    if sys.platform in _CASE_INSENSITIVE_PLATFORMS:
        return p.casefold()
    return p


_GLOB_CHARS = frozenset("*?[")


def _has_glob(p):
    return any(ch in _GLOB_CHARS for ch in p)


def _literal_prefix_dir(p):
    """Everything before the first wildcard-bearing path segment. The
    conservative rule treats a glob as claiming its whole literal directory
    rather than reasoning about which filenames the pattern would actually
    match: "*.py" at the root claims the entire tree (prefix ""), and
    "api/*.py" claims "api" (prefix "api")."""
    segs = p.split("/")
    out = []
    for seg in segs:
        if _has_glob(seg):
            break
        out.append(seg)
    return "/".join(out)


def _prefix_contains(a, b):
    """True when directory prefix a is "" (root, contains everything), equal
    to b, or a separator-bounded ancestor of b."""
    if a == b:
        return True
    if a == "":
        return True
    return b.startswith(a + "/")


def paths_overlap(a, b):
    """True when two declared claim paths can name the same file.

    Three rules, in order: exact match after case folding; directory
    containment at a separator boundary in either direction; and, when
    either side contains a wildcard, the CONSERVATIVE glob rule from the
    spec's Overlap semantics section, comparing literal directory prefixes
    instead of trying to reason about which filenames a pattern matches.
    api/*.py and api/pay.* share literal prefix "api" and MUST conflict,
    even though no single filename matches both patterns."""
    na = _normcase(_to_posix(a))
    nb = _normcase(_to_posix(b))
    if not na or not nb:
        return False
    # GATE 1 (fix-round 2026-07-26): '.' is the canonical form of the whole
    # root (see _to_posix and canonicalize_path) and MUST overlap every
    # other path, since it names every file in the project.
    if na == "." or nb == ".":
        return True
    if na == nb:
        return True
    if nb.startswith(na + "/") or na.startswith(nb + "/"):
        return True
    if _has_glob(na) or _has_glob(nb):
        pa = _literal_prefix_dir(na) if _has_glob(na) else na
        pb = _literal_prefix_dir(nb) if _has_glob(nb) else nb
        return _prefix_contains(pa, pb) or _prefix_contains(pb, pa)
    return False


def _join_relative(a, b):
    """Join two already root-relative POSIX components, treating '.' (the
    whole root) as the identity element rather than a literal segment."""
    if not b:
        return a
    if a in ("", "."):
        return b
    return a + "/" + b


def _resolve_against_root(root, rel_literal, cwd=None):
    """The literal (non-glob) portion of a declared path, resolved against a
    caller's cwd and re-expressed root-relative. Raises OwnershipRefused
    reason 'path-escape' when the result falls outside root, including via
    '..' or a symlink (GATE 1, fix-round 2026-07-26): os.path.realpath
    resolves symlinks in whatever prefix of the path already exists and
    leaves any nonexistent trailing components literal, so this works
    whether or not the target file exists yet.

    cwd=None (the default for every Python-API caller, including every test
    in this suite) means "no ambient directory was specified": a relative
    path is resolved AGAINST ROOT ITSELF, i.e. treated as already
    root-relative, exactly as this module always accepted it. Only the CLI
    passes cwd=os.getcwd() explicitly, because that is the one caller for
    whom "the directory the human actually typed this command from" is a
    real, meaningful, and different thing from the project root (the
    subdirectory-vs-root convergence GATE 1 requires)."""
    root_real = os.path.realpath(root)
    base_dir = cwd if cwd is not None else root
    if rel_literal in ("", "."):
        base = base_dir
    elif os.path.isabs(rel_literal):
        base = rel_literal
    else:
        base = os.path.join(base_dir, rel_literal)
    abs_real = os.path.realpath(base)
    try:
        rel = os.path.relpath(abs_real, root_real)
    except ValueError:
        # Windows: os.path.relpath raises when the two paths are on
        # different drives, which is definitionally outside the root.
        rel = None
    rel_posix = rel.replace(os.sep, "/") if rel is not None else None
    if rel_posix is None or rel_posix == ".." or rel_posix.startswith("../"):
        raise OwnershipRefused(
            "path-escape",
            "path %r resolves outside the project root %s"
            % (rel_literal, root_real),
            details={"root": root_real, "resolved": abs_real})
    return rel_posix


def canonicalize_path(root, p, cwd=None):
    """The ONE place a caller-declared path becomes a stored path (GATE 1,
    fix-round 2026-07-26, closes four defects at once):
    1. Resolves a relative path against cwd (default os.getcwd()) BEFORE
       expressing it root-relative, so a claim typed from a subdirectory and
       the same claim typed from the root store the identical string.
    2. Rejects (reason 'path-escape') anything that resolves outside root,
       including via '..' or a symlink.
    3. Stores a root-relative POSIX string with '.'/'..' segments resolved;
       the root itself normalizes to '.', which paths_overlap treats as
       overlapping everything.
    4. A glob keeps its wildcard segment literally, but the LITERAL PREFIX
       before the first wildcard segment is resolved and validated exactly
       like a plain path, so 'sub/../api/*.py' and 'api/*.py' converge."""
    posix = _to_posix(p)
    if not posix:
        raise ValueError("empty path")
    segs = posix.split("/") if posix != "." else []
    lit_segs = []
    tail_segs = None
    for i, seg in enumerate(segs):
        if _has_glob(seg):
            tail_segs = segs[i:]
            break
        lit_segs.append(seg)
    literal_dir = "/".join(lit_segs)
    resolved = _resolve_against_root(root, literal_dir, cwd)
    if tail_segs:
        return _join_relative(resolved, "/".join(tail_segs))
    return resolved


def _coerce_path_entry(f):
    """The ONE gate any single claimed-file entry passes through before it
    can become a stored path (fix-round 2, 2026-07-26: a claim() that
    silently dropped a non-str entry, pathlib.Path being the obvious case,
    still returned a Record reporting success, holding NOTHING, while the
    file it was meant to protect was handed to the next writer). TOTAL: for
    ANY input, this either returns a string or raises OwnershipRefused
    reason 'bad-path' naming the entry and its type. Never returns None,
    never returns anything silently skippable: a fence entry that cannot be
    read as a path is a refusal, not a gap in the fence (this project's own
    recorded lesson: a write whose return value is ignored eventually
    reports success it did not earn)."""
    if isinstance(f, str):
        return f
    try:
        p = os.fspath(f)
    except TypeError:
        raise OwnershipRefused(
            "bad-path",
            "file entry %r (type %s) is not a string or os.PathLike and "
            "cannot be used as a claim path" % (f, type(f).__name__),
            details={"entry": repr(f), "type": type(f).__name__})
    if isinstance(p, bytes):
        try:
            p = os.fsdecode(p)
        except Exception as e:
            raise OwnershipRefused(
                "bad-path",
                "file entry %r (type %s) could not be decoded as a path (%s)"
                % (f, type(f).__name__, e),
                details={"entry": repr(f), "type": type(f).__name__})
    if not isinstance(p, str):
        raise OwnershipRefused(
            "bad-path",
            "file entry %r (type %s) did not canonicalize to a string"
            % (f, type(f).__name__),
            details={"entry": repr(f), "type": type(f).__name__})
    return p


def _normalize_files(files, root, cwd=None):
    """Coerce a caller-supplied files argument into a de-duplicated list of
    (canonical_root_relative_path, is_glob) pairs, preserving input order. A
    bare string is ONE path, not an iterable of characters, the same
    defensive rule bm_registry's _safe_path_list enforces: claim(...,
    files="a.py") must fence one path, not one character at a time.

    Every entry passes through _coerce_path_entry (TOTAL: string or raise)
    and then canonicalize_path (root-relative, or raise 'path-escape'):
    NOTHING is ever silently dropped (fix-round 2, 2026-07-26). A files
    argument that is not iterable at all also raises 'bad-path' rather than
    quietly becoming an empty list. A NON-EMPTY input that still yields zero
    stored claims (every entry blank, or all entries collapse to the same
    path) raises too: a record that reports success while fencing nothing
    is exactly the defect this closes. Called BEFORE _transaction() opens
    (see claim()), so any raise here happens before a single byte is
    written: the whole claim is atomic by construction, never a partial
    fence."""
    if files is None:
        raw = []
    elif isinstance(files, str):
        raw = [files]
    else:
        try:
            raw = list(files)
        except TypeError:
            raise OwnershipRefused(
                "bad-path",
                "files must be a string, an os.PathLike, or an iterable of "
                "those; got %r (type %s)" % (files, type(files).__name__),
                details={"type": type(files).__name__})
    out = []
    seen = set()
    for f in raw:
        p = _coerce_path_entry(f).strip()
        if not p:
            continue
        canon = canonicalize_path(root, p, cwd)
        key = _normcase(canon)
        if key in seen:
            continue
        seen.add(key)
        out.append((canon, _has_glob(canon)))
    if raw and not out:
        raise OwnershipRefused(
            "bad-path",
            "every declared file entry was blank or collapsed to nothing; "
            "a non-empty files argument must yield at least one stored "
            "claim, never a record that reports success while fencing "
            "nothing",
            details={"entry_count": len(raw)})
    return out


def _truncate(s, budget):
    s = s or ""
    if len(s) <= budget:
        return s
    marker = " (truncated)"
    keep = budget - len(marker)
    if keep < 0:
        keep = 0
    return s[:keep].rstrip() + marker


# ---------------------------------------------------------------------------
# Exceptions: the two failure policies made concrete for ownership paths.
# ---------------------------------------------------------------------------

class BMStoreError(Exception):
    """Base class for every refusal and failure this module raises on
    purpose, so a caller can catch just this to know the store said no, or a
    specific subclass to know exactly why."""


class OwnershipRefused(BMStoreError):
    """An ownership mutation was refused on purpose: nothing changed.
    reason is a short machine-checkable code ("invalid-name", "overlap",
    "name-active", "cap", "missing-evidence", "no-root", ...); details
    carries whatever the caller needs to act (the conflicting record, the
    paths involved), so a human reading the CLI's output is told the legal
    next step instead of guessing from a generic message."""

    def __init__(self, reason, message, details=None):
        super(OwnershipRefused, self).__init__(message)
        self.reason = reason
        self.details = details or {}


class StaleIdentity(BMStoreError):
    """An optimistic-concurrency check failed: the caller's expected_version
    (or an assumed state, such as "active") no longer matches what is on
    disk, so the mutation was refused rather than silently applied over a
    write the caller never saw."""

    def __init__(self, message, current_state=None, current_version=None):
        super(StaleIdentity, self).__init__(message)
        self.current_state = current_state
        self.current_version = current_version


class StoreCorrupt(BMStoreError):
    """The database file could not be read as SQLite. It has been
    quarantined (renamed aside, never deleted) rather than silently
    replaced: a fresh empty store that "just works" is indistinguishable
    from one that quietly lost every record it held (fixes F9)."""

    def __init__(self, message, quarantine_path=None):
        super(StoreCorrupt, self).__init__(message)
        self.quarantine_path = quarantine_path


class RedactionUnavailable(OwnershipRefused):
    """bm_telemetry.redact could not be loaded, or itself raised on the
    input. Refusing to render is the safe direction: the alternative is
    founder-typed text (an objective, a decision, a digest section, a note)
    reaching STATE.md or a terminal unredacted. dump() is unaffected: it is
    the documented raw export and never calls redact_text()."""

    def __init__(self, message, details=None):
        super(RedactionUnavailable, self).__init__("redaction-unavailable", message, details)


# ---------------------------------------------------------------------------
# Redaction (amended 2026-07-26, the first draft omitted it): secret
# redaction has exactly one owner in this codebase, bm_telemetry.redact.
# bm_registry imports it this same way (importlib.util.spec_from_file_location
# by path, so this works regardless of the caller's cwd); mirrored here. The
# policy differs from bm_registry on purpose: bm_registry falls back to a
# weaker inline pattern set and keeps going, but every function that calls
# redact_text() here is a GENERATED VIEW leaving the store, so a load failure
# refuses to render rather than emit weaker-than-documented or raw text. Raw
# text lives only inside the sqlite file itself (SECURITY.md documents this
# as sensitive); dump() is the one deliberate, documented exception.
# ---------------------------------------------------------------------------

def _load_redact():
    try:
        import importlib.util
        here = os.path.dirname(os.path.abspath(__file__))
        spec = importlib.util.spec_from_file_location(
            "bm_telemetry_for_store", os.path.join(here, "bm_telemetry.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "redact"):
            return mod.redact, None
        return None, "bm_telemetry.py has no redact()"
    except Exception as e:
        return None, repr(e)


_REDACT, _REDACT_LOAD_ERROR = _load_redact()
_WARNED_NO_REDACT = []


def _warn_no_redact_once():
    # Once, not every call: this fires from inside render functions that may
    # be invoked repeatedly, and a warning nobody can find under a wall of
    # duplicates is the same as no warning.
    if _WARNED_NO_REDACT:
        return
    _WARNED_NO_REDACT.append(True)
    print("bm_store: WARNING: could not load the bm_telemetry redactor (%s); "
          "refusing to render generated views (STATE.md, render_digest, the "
          "dashboard) rather than emit unredacted text. dump() and the raw "
          "sqlite file are unaffected." % _REDACT_LOAD_ERROR, file=sys.stderr)


def redact_text(t):
    """Redact one string through bm_telemetry.redact. Raises
    RedactionUnavailable, never returns raw text, when the redactor could
    not be loaded or itself raised on this input: every caller of this
    function is a generated-view boundary (see the module note above)."""
    if _REDACT is None:
        _warn_no_redact_once()
        raise RedactionUnavailable(
            "bm_telemetry.redact is unavailable (%s)" % _REDACT_LOAD_ERROR)
    try:
        return _REDACT(t or "")[0]
    except Exception as e:
        raise RedactionUnavailable("bm_telemetry.redact raised on input (%r)" % (e,))


# ---------------------------------------------------------------------------
# Record: a read-only snapshot, never a live handle.
# ---------------------------------------------------------------------------

class Record(object):
    """A snapshot of one records row plus its claimed paths, returned by
    every API call that creates or mutates a record. Never mutated in
    place: code that needs fresh data calls the API again, so a cached
    Record can never silently drift from what the store actually holds."""

    __slots__ = ("lifecycle_uuid", "name", "lifetime", "state", "objective",
                 "owner", "session_id", "tier", "check_cmd", "evidence",
                 "ttl_hours", "version", "created_at", "updated_at", "files")

    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw.get(k))

    def to_dict(self):
        return dict((k, getattr(self, k)) for k in self.__slots__)

    def __repr__(self):
        return ("Record(name=%r, lifecycle_uuid=%r, state=%r, version=%r)"
                % (self.name, self.lifecycle_uuid, self.state, self.version))


# ---------------------------------------------------------------------------
# Schema (schema_version 1). autosave_receipts ships now, unused, so Phase 2
# needs no migration.
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT
);
CREATE TABLE IF NOT EXISTS records (
  lifecycle_uuid TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  lifetime TEXT NOT NULL CHECK(lifetime IN ('persistent','ephemeral')),
  state TEXT NOT NULL CHECK(state IN ('active','parked','complete','adopted')),
  objective TEXT NOT NULL DEFAULT '',
  owner TEXT NOT NULL DEFAULT '',
  session_id TEXT NOT NULL DEFAULT '',
  tier TEXT NOT NULL DEFAULT '',
  check_cmd TEXT NOT NULL DEFAULT '',
  evidence TEXT NOT NULL DEFAULT '',
  ttl_hours REAL,
  version INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS one_active_per_name ON records(name) WHERE state='active';
CREATE TABLE IF NOT EXISTS claims (
  lifecycle_uuid TEXT NOT NULL REFERENCES records(lifecycle_uuid) ON DELETE CASCADE,
  path TEXT NOT NULL,
  is_glob INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY(lifecycle_uuid, path)
);
CREATE TABLE IF NOT EXISTS decisions (
  lifecycle_uuid TEXT NOT NULL REFERENCES records(lifecycle_uuid),
  seq INTEGER NOT NULL,
  topic TEXT NOT NULL DEFAULT '',
  text TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  PRIMARY KEY(lifecycle_uuid, seq)
);
CREATE TABLE IF NOT EXISTS digests (
  lifecycle_uuid TEXT NOT NULL REFERENCES records(lifecycle_uuid),
  seq INTEGER NOT NULL,
  next_intent TEXT NOT NULL DEFAULT '',
  blockers TEXT NOT NULL DEFAULT '',
  files_note TEXT NOT NULL DEFAULT '',
  body TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  PRIMARY KEY(lifecycle_uuid, seq)
);
CREATE TABLE IF NOT EXISTS directives (
  lifecycle_uuid TEXT NOT NULL REFERENCES records(lifecycle_uuid),
  seq INTEGER NOT NULL,
  text TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  delivered_at TEXT,
  PRIMARY KEY(lifecycle_uuid, seq)
);
CREATE TABLE IF NOT EXISTS deliveries (
  payload_sha256 TEXT PRIMARY KEY,
  lifecycle_uuid TEXT NOT NULL,
  target TEXT NOT NULL,
  delivered_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS transitions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lifecycle_uuid TEXT NOT NULL,
  from_state TEXT,
  to_state TEXT NOT NULL,
  session_id TEXT NOT NULL DEFAULT '',
  note TEXT NOT NULL DEFAULT '',
  at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS autosave_receipts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  worktree_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  snapshot_sha TEXT NOT NULL,
  tree_sha TEXT NOT NULL,
  source_head TEXT NOT NULL,
  captured_count INTEGER NOT NULL,
  excluded_count INTEGER NOT NULL,
  created_at TEXT NOT NULL
);
"""

_TABLES = ("meta", "records", "claims", "decisions", "digests", "directives",
           "deliveries", "transitions", "autosave_receipts")

_LEGAL_MOVES = {
    "parked": ("active",),
    "active": ("parked",),
    "complete": ("active",),
    "adopted": ("active", "parked"),
}


def _chmod_best_effort(path, mode):
    """Best-effort permission tightening (GATE 7, fix-round 2026-07-26).
    Windows ACLs make a POSIX mode a courtesy at best (os.chmod there can
    only toggle the read-only bit), so a failure, or a silent no-op on a
    platform that will not honor it, is expected and never escalated: this
    function does not claim a guarantee the platform will not keep."""
    try:
        os.chmod(path, mode)
    except OSError:
        pass


def _resolve_git_common_dir(root):
    """The directory that actually holds info/exclude for this checkout
    (GATE C, fix-round 3, 2026-07-26). A normal checkout: <root>/.git. A
    worktree: .git is a FILE containing 'gitdir: <path>' pointing at
    <main>/.git/worktrees/<name>; info/exclude is NOT per-worktree, it is
    shared once at the top of the MAIN checkout's .git, named by that
    worktree gitdir's own 'commondir' file (present since git 2.5). The old
    code returned early on a .git FILE, so nothing was ever excluded inside
    a worktree and `git add -A` staged the raw store. Verified against a
    real `git worktree add`. Returns None when there is no git here at all,
    or anything about it could not be read."""
    git_path = os.path.join(root, ".git")
    if os.path.isdir(git_path):
        return git_path
    if not os.path.isfile(git_path):
        return None
    try:
        with open(git_path, encoding="utf-8", errors="replace") as f:
            content = f.read().strip()
    except OSError:
        return None
    if not content.startswith("gitdir:"):
        return None
    pointer = content[len("gitdir:"):].strip()
    if not os.path.isabs(pointer):
        pointer = os.path.join(root, pointer)
    worktree_gitdir = os.path.realpath(pointer)
    commondir_file = os.path.join(worktree_gitdir, "commondir")
    if os.path.isfile(commondir_file):
        try:
            with open(commondir_file, encoding="utf-8", errors="replace") as f:
                rel = f.read().strip()
            return os.path.realpath(os.path.join(worktree_gitdir, rel))
        except OSError:
            pass
    return worktree_gitdir


def _ensure_git_excludes(root):
    """Append .brothermode/, threads/, STATE.md to the resolved git common
    dir's info/exclude when git is present here and the entries are absent
    (fixes finding 30; worktree support is GATE C, fix-round 3, 2026-07-26).
    Called from Store.__init__ on EVERY open (GATE 7, fix-round 2026-07-26),
    not only from init: any command creates .brothermode/store.sqlite3 as a
    side effect, so a routine `git add -A` run before anyone happens to run
    `init` used to commit the store, cleartext founder secrets and all.
    Idempotent, so calling it on every open costs nothing once the entries
    are already present."""
    git_dir = _resolve_git_common_dir(root)
    if git_dir is None:
        return
    exclude_path = os.path.join(git_dir, "info", "exclude")
    wanted = [".brothermode/", "threads/", "STATE.md"]
    try:
        existing = ""
        if os.path.exists(exclude_path):
            with open(exclude_path, encoding="utf-8", errors="replace") as f:
                existing = f.read()
        lines = existing.splitlines()
        missing = [w for w in wanted if w not in lines]
        if missing:
            os.makedirs(os.path.dirname(exclude_path), exist_ok=True)
            with open(exclude_path, "a", encoding="utf-8") as f:
                if existing and not existing.endswith("\n"):
                    f.write("\n")
                for w in missing:
                    f.write(w + "\n")
    except OSError as e:
        # Advisory: opening the store must still succeed even when
        # .git/info/exclude is not writable (read-only worktree, permission
        # issue). The store itself is already created and usable.
        print("bm_store: warning: could not update %s (%s)" % (exclude_path, e),
              file=sys.stderr)


def _exec(store, sql, params=()):
    """The ONE place any SQL statement runs against a Store's connection
    (GATE 4, fix-round 2026-07-26): Store.__init__ only probed the schema at
    OPEN time, so damage on a later page opened fine and then leaked a raw
    sqlite3.DatabaseError out of claim(), dump(), and verify(), with nothing
    quarantined and the CLI exiting 1 with a driver traceback. Every query
    in this module, from a Store method or from a module-level function
    holding a Store (render_state_md, verify), routes through here so the
    same ratified failure split applies everywhere, not only at open:
    sqlite3.OperationalError refuses 'db-busy', any other
    sqlite3.DatabaseError quarantines and raises StoreCorrupt.
    sqlite3.IntegrityError (itself a DatabaseError subclass) is
    deliberately let through UNCHANGED: a unique-constraint hit is
    caller-shaped, not corruption (see transition()'s 'name-active' handling
    for GATE 6), and the caller is better placed to turn it into a named
    refusal than this generic helper is."""
    try:
        return store.conn.execute(sql, params)
    except sqlite3.IntegrityError:
        raise
    except sqlite3.OperationalError as e:
        raise OwnershipRefused(
            "db-busy",
            "the store at %s is busy or locked (%s); wait a moment and retry."
            % (store.path, e))
    except sqlite3.DatabaseError as e:
        store._quarantine_and_raise(e)


class Store(object):
    """One open connection to <root>/.brothermode/store.sqlite3. Every
    ownership mutation runs inside exactly one BEGIN IMMEDIATE ... COMMIT
    (see _transaction), so a reader never observes a half-written record and
    two writers on the same file never interleave."""

    def __init__(self, root, busy_timeout_ms=5000):
        """busy_timeout_ms defaults to the spec's 5000; exposed as a keyword
        so a test can force a near-instant "database is locked" without a
        real multi-second wait. Store(root) alone still matches the spec's
        constructor exactly."""
        self.root = os.path.realpath(root)
        self.conn = None
        expected_store_dir = store_dir(self.root)
        os.makedirs(expected_store_dir, exist_ok=True)
        # GATE D (fix-round 3, 2026-07-26): claim paths were already
        # symlink-checked and refused as 'path-escape', but .brothermode
        # itself was not, so a repository carrying .brothermode -> docs (or
        # -> ../shared) wrote the sensitive store outside the project root,
        # defeated the exclude line entirely, and chmod'd the LINK TARGET.
        # Same containment rule, checked BEFORE any chmod or DB open.
        real_store_dir = os.path.realpath(expected_store_dir)
        if real_store_dir != expected_store_dir:
            raise OwnershipRefused(
                "path-escape",
                "%s is a symlink (or contains one) resolving to %s; "
                "refusing to use it as the store directory rather than "
                "write the sensitive store outside the project root or "
                "chmod that target" % (expected_store_dir, real_store_dir),
                details={"expected": expected_store_dir, "resolved": real_store_dir})
        # GATE 7 (fix-round 2026-07-26): every open protects itself, not
        # only `init`. A command run before anyone happens to `init` still
        # creates the store directory as a side effect, and that must never
        # be one `git add -A` away from committing a cleartext secret.
        _ensure_git_excludes(self.root)
        _chmod_best_effort(expected_store_dir, 0o700)
        self.path = store_path(self.root)
        if os.path.exists(self.path) and os.path.getsize(self.path) == 0:
            # GATE B (fix-round 3, 2026-07-26): sqlite3 accepts a zero-byte
            # file as a valid, brand-new empty database, so a truncated
            # store never raised DatabaseError and never reached quarantine:
            # every record silently gone, dashboard reporting "No records."
            # at exit 0. An EXISTING zero-length file is corruption, never a
            # fresh database; first-time creation is unaffected, since the
            # file does not exist at all yet when this branch runs, and the
            # normal open path below always ends construction with a real
            # schema on disk, so a zero-byte file can never persist as a
            # legitimate state to be mistaken for one later.
            self._quarantine_and_raise(
                ValueError("store file exists but is zero bytes (truncated, or never finished writing)"))
        try:
            conn = sqlite3.connect(self.path, timeout=5.0, isolation_level=None)
            conn.row_factory = sqlite3.Row
            self.conn = conn
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=%d" % int(busy_timeout_ms))
            conn.execute("PRAGMA foreign_keys=ON")
            self._ensure_schema()
            # A read, not just a connect: a corrupt file can open fine and
            # only fail the instant something touches its b-tree pages. Fail
            # here, at construction, rather than on the caller's first real
            # query deep inside an unrelated transaction. Later-page
            # corruption (after this probe passes) is caught by _exec()
            # instead, on every subsequent query (GATE 4).
            self.conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        except sqlite3.OperationalError as e:
            # Amended 2026-07-26: the first draft quarantined on ANY
            # sqlite3.DatabaseError, and OperationalError (busy or locked) is
            # a subclass of it, so a merely-busy database used to get renamed
            # out from under a concurrent writer, which is itself data loss.
            # A busy or locked database is transient, not corrupt: refuse
            # fail-closed with a clear retry message and touch nothing. This
            # except clause MUST stay before the DatabaseError one below,
            # since OperationalError is a subclass and would otherwise never
            # be reached.
            if self.conn is not None:
                try:
                    self.conn.close()
                except Exception:
                    pass
                self.conn = None
            raise OwnershipRefused(
                "db-busy",
                "the store at %s is busy or locked (%s), most likely another "
                "process writing at the same moment. The file was NOT "
                "touched: wait a moment and retry." % (self.path, e))
        except sqlite3.DatabaseError as e:
            # Every OTHER sqlite3.DatabaseError is the corruption class:
            # quarantine and raise StoreCorrupt (fixes F9).
            self._quarantine_and_raise(e)
        else:
            # GATE 7: tighten the store file (and its sidecars, if WAL mode
            # has already created them) only once we know the connection is
            # genuinely open and healthy.
            _chmod_best_effort(self.path, 0o600)
            _chmod_best_effort(self.path + "-wal", 0o600)
            _chmod_best_effort(self.path + "-shm", 0o600)

    def _ensure_schema(self):
        self.conn.executescript(_DDL)
        self.conn.execute(
            "INSERT OR IGNORE INTO meta (key, value) VALUES ('schema_version', ?)",
            (str(SCHEMA_VERSION),))
        self.conn.execute(
            "INSERT OR IGNORE INTO meta (key, value) VALUES ('project_uuid', ?)",
            (uuid.uuid4().hex,))
        self.conn.execute(
            "INSERT OR IGNORE INTO meta (key, value) VALUES ('created_at', ?)",
            (now_iso(),))

    def _quarantine_and_raise(self, cause):
        """Quarantine store.sqlite3 AND its -wal/-shm sidecars into a
        per-incident DIRECTORY (GATE 5, fix-round 2026-07-26). A single
        renamed FILE had two defects: two quarantines inside the same
        second collided and os.replace silently destroyed the first one's
        evidence, and the -wal/-shm sidecars (where the actually-lost
        records can live, since WAL keeps recent writes there before a
        checkpoint) were left behind entirely. The directory name carries
        microsecond precision plus a uuid4 suffix and is created with
        os.makedirs(exist_ok=False), so a name can never be reused; nothing
        is ever os.replace'd onto an existing path."""
        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        suffix = uuid.uuid4().hex[:8]
        qdir = self.path + ".quarantine-%s-%s" % (stamp, suffix)
        try:
            os.makedirs(qdir, exist_ok=False)
        except OSError as mkdir_err:
            raise StoreCorrupt(
                "%s is not a readable SQLite database (%s), and a quarantine "
                "directory could not be created either (%s). Nothing was "
                "moved: the damaged file is still at %s; move it aside by "
                "hand, then run init again."
                % (self.path, cause, mkdir_err, self.path))
        moved, failed = [], []
        for src in (self.path, self.path + "-wal", self.path + "-shm"):
            if not os.path.exists(src):
                continue
            dst = os.path.join(qdir, os.path.basename(src))
            try:
                os.replace(src, dst)
                _chmod_best_effort(dst, 0o600)
                moved.append(dst)
            except OSError as move_err:
                failed.append("%s (%s)" % (src, move_err))
        if failed and not moved:
            raise StoreCorrupt(
                "%s is not a readable SQLite database (%s), and it could not "
                "be moved into the quarantine directory %s either (%s). "
                "Nothing was deleted: the file is still at its original path."
                % (self.path, cause, qdir, "; ".join(failed)),
                quarantine_path=qdir)
        raise StoreCorrupt(
            "%s was not a readable SQLite database (%s). It has been "
            "quarantined, together with its -wal/-shm sidecars where "
            "present, to the directory %s (never deleted, never "
            "overwritten: this directory name is unique per incident). Run "
            "`python3 tools/bm_store.py init` to start a fresh store, then "
            "inspect the quarantined directory by hand to recover any "
            "records." % (self.path, cause, qdir),
            quarantine_path=qdir)

    def close(self):
        if self.conn is not None:
            try:
                self.conn.close()
            finally:
                self.conn = None

    @contextlib.contextmanager
    def _transaction(self):
        """BEGIN IMMEDIATE takes SQLite's write lock up front, before any
        table is touched, rather than only at the first write statement:
        that closes the classic read-then-upgrade race where two writers
        both pass a check and then both write. BEGIN and COMMIT route
        through _exec (GATE 4) like every other statement; ROLLBACK stays a
        raw call inside its own narrow except, since it runs while another
        exception is already being handled and must never replace it."""
        _exec(self, "BEGIN IMMEDIATE")
        try:
            yield self.conn
        except Exception:
            try:
                self.conn.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise
        else:
            _exec(self, "COMMIT")

    def _record_by_uuid(self, conn, lifecycle_uuid):
        row = _exec(self,
            "SELECT * FROM records WHERE lifecycle_uuid=?", (lifecycle_uuid,)).fetchone()
        if row is None:
            return None
        files = [r["path"] for r in _exec(self,
            "SELECT path FROM claims WHERE lifecycle_uuid=? ORDER BY path",
            (lifecycle_uuid,)).fetchall()]
        return Record(
            lifecycle_uuid=row["lifecycle_uuid"], name=row["name"],
            lifetime=row["lifetime"], state=row["state"],
            objective=row["objective"], owner=row["owner"],
            session_id=row["session_id"], tier=row["tier"],
            check_cmd=row["check_cmd"], evidence=row["evidence"],
            ttl_hours=row["ttl_hours"], version=row["version"],
            created_at=row["created_at"], updated_at=row["updated_at"],
            files=files)

    def get(self, lifecycle_uuid):
        """Read-only fetch of one record by identity. Not named in the
        ratified API list, but every mutation already needs this internally
        to build its return value, and tests and future callers need a way
        to re-read a record without reaching into private methods: exposing
        it is a small, pure-read addition, not a behavior change."""
        return self._record_by_uuid(self.conn, lifecycle_uuid)

    # -- claim ---------------------------------------------------------

    def _find_overlap(self, conn, norm_files, exclude_uuid=None):
        if exclude_uuid is None:
            rows = _exec(self,
                "SELECT r.name AS name, c.lifecycle_uuid AS lifecycle_uuid, "
                "c.path AS path FROM claims c "
                "JOIN records r ON r.lifecycle_uuid = c.lifecycle_uuid "
                "WHERE r.state='active'").fetchall()
        else:
            rows = _exec(self,
                "SELECT r.name AS name, c.lifecycle_uuid AS lifecycle_uuid, "
                "c.path AS path FROM claims c "
                "JOIN records r ON r.lifecycle_uuid = c.lifecycle_uuid "
                "WHERE r.state='active' AND c.lifecycle_uuid != ?",
                (exclude_uuid,)).fetchall()
        for path, _is_glob in norm_files:
            for r in rows:
                if paths_overlap(path, r["path"]):
                    return (r["name"], r["lifecycle_uuid"], (path, r["path"]))
        return None

    def _admit(self, conn, name, lifetime, norm_files, exclude_uuid=None):
        """The ONE admission check any path that grants a record ACTIVE
        status over a set of claims must run (GATE A, fix-round 3,
        2026-07-26): resume (parked -> active) used to re-run NONE of
        claim()'s checks, so it walked straight over another session's
        fence and the persistent cap, and verify() then reported the exact
        overlap the store itself had just created. This is the project's
        cross-cutting-concern law: one primitive, called by both claim()
        and the resume path in transition(), so a third caller cannot
        diverge. Name-uniqueness is NOT checked here: claim() checks it via
        a SELECT before this runs, and resume relies on the UNIQUE INDEX
        itself raising IntegrityError at the UPDATE site (GATE 6); both
        funnel to the same 'name-active' refusal at their own call sites."""
        conflict = self._find_overlap(conn, norm_files, exclude_uuid=exclude_uuid)
        if conflict is not None:
            self._raise_overlap(conflict)
        if lifetime == "persistent":
            if exclude_uuid is None:
                active_persistent = _exec(self,
                    "SELECT COUNT(*) AS c FROM records "
                    "WHERE state='active' AND lifetime='persistent'").fetchone()["c"]
            else:
                active_persistent = _exec(self,
                    "SELECT COUNT(*) AS c FROM records WHERE state='active' "
                    "AND lifetime='persistent' AND lifecycle_uuid != ?",
                    (exclude_uuid,)).fetchone()["c"]
            if active_persistent >= MAX_ACTIVE_PERSISTENT:
                raise OwnershipRefused(
                    "cap",
                    "%d active persistent records already exist (limit "
                    "%d); park or complete one before claiming another"
                    % (active_persistent, MAX_ACTIVE_PERSISTENT),
                    details={"limit": MAX_ACTIVE_PERSISTENT, "active": active_persistent,
                             "name": name})

    def _raise_overlap(self, conflict):
        other_name, other_uuid, pair = conflict
        raise OwnershipRefused(
            "overlap",
            "claim overlaps active record '%s' (lifecycle %s): %r vs %r"
            % (other_name, other_uuid, pair[0], pair[1]),
            details={"lifecycle_uuid": other_uuid, "name": other_name,
                     "paths": list(pair)})

    def _reclaim_active(self, conn, row, objective, norm, owner, tier, check_cmd, ttl_hours):
        """The same session re-declaring a name it already holds active.
        Updates in place, keeps the SAME lifecycle_uuid (this is still the
        same life of the record), and still re-checks overlap against every
        OTHER active record: skipping that check would let a same-session
        reclaim silently seize a path a different session already holds,
        which is exactly the collision the overlap check exists to prevent.
        Mirrors bm_registry.claim()'s reclaim semantics: objective and files
        are always overwritten, owner is left untouched, and tier/check_cmd/
        ttl_hours are only overwritten when a new truthy value is given."""
        conflict = self._find_overlap(conn, norm, exclude_uuid=row["lifecycle_uuid"])
        if conflict is not None:
            self._raise_overlap(conflict)
        ts = now_iso()
        new_tier = tier if tier else row["tier"]
        new_check = check_cmd if check_cmd else row["check_cmd"]
        new_ttl = ttl_hours if ttl_hours is not None else row["ttl_hours"]
        _exec(self,
            "UPDATE records SET objective=?, tier=?, check_cmd=?, ttl_hours=?, "
            "version=version+1, updated_at=? WHERE lifecycle_uuid=?",
            (objective or "", new_tier, new_check, new_ttl, ts, row["lifecycle_uuid"]))
        _exec(self, "DELETE FROM claims WHERE lifecycle_uuid=?", (row["lifecycle_uuid"],))
        for path, is_glob in norm:
            _exec(self,
                "INSERT INTO claims (lifecycle_uuid, path, is_glob) VALUES (?,?,?)",
                (row["lifecycle_uuid"], path, 1 if is_glob else 0))
        return self._record_by_uuid(conn, row["lifecycle_uuid"])

    def claim(self, name, lifetime, objective, files, owner="", session_id="",
              tier="", check_cmd="", ttl_hours=None, cwd=None):
        """Register (or, for the SAME non-empty session re-declaring, update
        in place) one unit of work. Every refusal here closes a confirmed
        defect: silent takeover of an active name (F3, and again through the
        CLI door as GATE 3, fix-round 2026-07-26), unbounded file overlap
        (F1/F2/F11 and the GATE 1 canonicalization class), and an uncapped
        persistent-thread count.

        cwd (default os.getcwd()) is the directory relative paths in files
        are resolved against BEFORE being canonicalized root-relative (GATE
        1): a claim typed from a subdirectory and the same claim typed from
        the root must store the identical string, never two different ones
        that both "win" against overlap checking."""
        valid_name(name)
        if lifetime not in ("persistent", "ephemeral"):
            raise ValueError(
                "lifetime must be 'persistent' or 'ephemeral', got %r" % (lifetime,))
        norm = _normalize_files(files, self.root, cwd)
        with self._transaction() as conn:
            active = _exec(self,
                "SELECT * FROM records WHERE name=? AND state='active'", (name,)).fetchone()
            if active is not None:
                # GATE 3 (fix-round 2026-07-26): an empty or missing session
                # id must NEVER match another empty session id. Two
                # independent CLI processes that both omit --session used to
                # both satisfy (("" or "") == ("" or "")) here, so the
                # second process silently reclaimed the first one's active
                # record: the original F3 takeover, back through the CLI
                # door. Reclaiming in place now requires a NON-EMPTY session
                # id equal to the one on file.
                if session_id and active["session_id"] == session_id:
                    if lifetime != active["lifetime"]:
                        # SOFT F (fix-round 3, 2026-07-26): a reclaim used to
                        # silently keep the OLD lifetime and return a Record
                        # reporting it as though the request was honored,
                        # the same silent-success class as round 2's files
                        # bug. Refused, not silently changed: a lifetime
                        # flip changes cap enforcement and is significant
                        # enough to require an explicit park/re-claim.
                        raise OwnershipRefused(
                            "lifetime-mismatch",
                            "'%s' is active as %r; claim requested %r. "
                            "Reclaiming cannot silently change lifetime: "
                            "park it and claim again with the new lifetime."
                            % (name, active["lifetime"], lifetime),
                            details={"lifecycle_uuid": active["lifecycle_uuid"],
                                     "current_lifetime": active["lifetime"],
                                     "requested_lifetime": lifetime})
                    return self._reclaim_active(
                        conn, active, objective, norm, owner, tier, check_cmd, ttl_hours)
                raise OwnershipRefused(
                    "name-active",
                    "'%s' is already active as lifecycle %s under session "
                    "%r; that session must park, complete, or adopt it "
                    "before this name can be claimed again (or resume it "
                    "yourself if you hold that session)"
                    % (name, active["lifecycle_uuid"], active["session_id"]),
                    details={"lifecycle_uuid": active["lifecycle_uuid"], "name": name,
                             "held_by_session_id": active["session_id"]})
            self._admit(conn, name, lifetime, norm)
            lifecycle_uuid = uuid.uuid4().hex
            ts = now_iso()
            _exec(self,
                "INSERT INTO records (lifecycle_uuid, name, lifetime, state, "
                "objective, owner, session_id, tier, check_cmd, evidence, "
                "ttl_hours, version, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (lifecycle_uuid, name, lifetime, "active", objective or "",
                 owner or "", session_id or "", tier or "", check_cmd or "",
                 "", ttl_hours, 1, ts, ts))
            for path, is_glob in norm:
                _exec(self,
                    "INSERT INTO claims (lifecycle_uuid, path, is_glob) VALUES (?,?,?)",
                    (lifecycle_uuid, path, 1 if is_glob else 0))
            _exec(self,
                "INSERT INTO transitions (lifecycle_uuid, from_state, to_state, "
                "session_id, note, at) VALUES (?,?,?,?,?,?)",
                (lifecycle_uuid, None, "active", session_id or "", "claimed", ts))
            return self._record_by_uuid(conn, lifecycle_uuid)

    # -- transition ------------------------------------------------------

    def transition(self, lifecycle_uuid, expected_version, to_state,
                    session_id="", note="", evidence=""):
        """Move a record along its legal state graph. Every failure to match
        lifecycle_uuid, expected_version, AND a legal source state for
        to_state raises StaleIdentity naming the actual current state and
        version, so an illegal move and a stale version report the same way
        a caller must react to the same way: re-read the record and decide
        what is actually true now (fixes the F5/F6/F7/F8 class).

        SOFT 10 (fix-round 2026-07-26): a non-empty owning session_id must
        match the caller's, or the move is refused 'not-owner', EXCEPT for
        the 'adopted' target: adoption of a dead session's record is the one
        legitimate cross-session path, and it records the adopter's session.

        GATE 6 (fix-round 2026-07-26): resuming (or parking/completing) into
        a name another lifecycle now holds active violates the
        one-active-per-name unique index and used to raise a raw
        sqlite3.IntegrityError that reached the CLI as an unhandled
        exit-1 crash. Caught here and turned into the same 'name-active'
        refusal claim() already uses, exit 2."""
        if to_state not in _LEGAL_MOVES:
            raise ValueError("unknown target state %r" % (to_state,))
        if to_state == "complete" and not (evidence or "").strip():
            raise OwnershipRefused(
                "missing-evidence",
                "active -> complete requires non-empty evidence (the "
                "check_cmd result)",
                details={"lifecycle_uuid": lifecycle_uuid})
        allowed_from = _LEGAL_MOVES[to_state]
        with self._transaction() as conn:
            row = _exec(self,
                "SELECT * FROM records WHERE lifecycle_uuid=?", (lifecycle_uuid,)).fetchone()
            if row is None or row["version"] != expected_version or row["state"] not in allowed_from:
                cur_state = row["state"] if row is not None else None
                cur_version = row["version"] if row is not None else None
                raise StaleIdentity(
                    "expected version %r in a state that allows -> %s; found %s"
                    % (expected_version, to_state,
                       ("no such record" if row is None else
                        "version %s state %r" % (cur_version, cur_state))),
                    current_state=cur_state, current_version=cur_version)
            if (to_state != "adopted" and row["session_id"]
                    and row["session_id"] != (session_id or "")):
                raise OwnershipRefused(
                    "not-owner",
                    "lifecycle %s is owned by a different session; only that "
                    "session may move it to '%s' (adoption is the exception "
                    "for a dead session's record)" % (lifecycle_uuid, to_state),
                    details={"lifecycle_uuid": lifecycle_uuid,
                             "held_by_session_id": row["session_id"]})
            if to_state == "active":
                # GATE A (fix-round 3, 2026-07-26): resume must clear the
                # SAME admission gate claim() does, against the record's OWN
                # claims and lifetime, excluding itself from both checks
                # (it is not active yet, so this is defensive, not required
                # by the current schema, but keeps _admit's contract honest
                # regardless of call order). On conflict the record stays
                # parked: nothing here has mutated state yet.
                claim_rows = _exec(self,
                    "SELECT path, is_glob FROM claims WHERE lifecycle_uuid=?",
                    (lifecycle_uuid,)).fetchall()
                norm_files = [(r["path"], bool(r["is_glob"])) for r in claim_rows]
                self._admit(conn, row["name"], row["lifetime"], norm_files,
                            exclude_uuid=lifecycle_uuid)
            ts = now_iso()
            new_evidence = evidence if to_state == "complete" else row["evidence"]
            try:
                cur = _exec(self,
                    "UPDATE records SET state=?, version=version+1, updated_at=?, "
                    "session_id=?, evidence=? WHERE lifecycle_uuid=? AND version=? AND state=?",
                    (to_state, ts, session_id or row["session_id"], new_evidence,
                     lifecycle_uuid, expected_version, row["state"]))
            except sqlite3.IntegrityError:
                holder = _exec(self,
                    "SELECT lifecycle_uuid FROM records WHERE name=? AND state='active'",
                    (row["name"],)).fetchone()
                raise OwnershipRefused(
                    "name-active",
                    "cannot move lifecycle %s to '%s': the name '%s' is "
                    "already active under a different lifecycle%s"
                    % (lifecycle_uuid, to_state, row["name"],
                       (" (%s)" % holder["lifecycle_uuid"]) if holder else ""),
                    details={"lifecycle_uuid": lifecycle_uuid, "name": row["name"],
                             "held_by_lifecycle_uuid": holder["lifecycle_uuid"] if holder else None})
            if cur.rowcount == 0:
                # Unreachable in practice: BEGIN IMMEDIATE holds the write
                # lock for the whole transaction, so nothing can move the
                # row between the SELECT above and this UPDATE. Kept as a
                # hard failure rather than trusting the pre-check alone,
                # because a mutation that silently no-ops must never be
                # reported as success.
                raise StaleIdentity(
                    "record changed between check and write; retry the transition",
                    current_state=row["state"], current_version=row["version"])
            _exec(self,
                "INSERT INTO transitions (lifecycle_uuid, from_state, to_state, "
                "session_id, note, at) VALUES (?,?,?,?,?,?)",
                (lifecycle_uuid, row["state"], to_state, session_id or "", note or "", ts))
            return self._record_by_uuid(conn, lifecycle_uuid)

    # -- checkpoint / decide / send ---------------------------------------

    def checkpoint(self, lifecycle_uuid, expected_version, next_intent,
                   blockers="", files_note="", body="", decisions=None):
        """Record the current handover digest. Refused unless the record is
        active at exactly expected_version (StaleIdentity otherwise): a
        checkpoint against a parked or already-moved-on record is exactly
        the V1 defect (F5/F6) where a thread kept writing into a record that
        had already been closed out from under it. Decisions passed here are
        appended in the SAME transaction as the digest row (fixes finding
        19): a caller can never see the digest saved without its decisions,
        or vice versa."""
        with self._transaction() as conn:
            row = _exec(self,
                "SELECT * FROM records WHERE lifecycle_uuid=?", (lifecycle_uuid,)).fetchone()
            if row is None or row["version"] != expected_version or row["state"] != "active":
                raise StaleIdentity(
                    "checkpoint requires the record to be ACTIVE at version "
                    "%r; found %s" % (expected_version,
                        ("no such record" if row is None else
                         "version %s state %r" % (row["version"], row["state"]))),
                    current_state=row["state"] if row is not None else None,
                    current_version=row["version"] if row is not None else None)
            ts = now_iso()
            seq = (_exec(self,
                "SELECT COALESCE(MAX(seq),0) AS m FROM digests WHERE lifecycle_uuid=?",
                (lifecycle_uuid,)).fetchone()["m"]) + 1
            _exec(self,
                "INSERT INTO digests (lifecycle_uuid, seq, next_intent, "
                "blockers, files_note, body, created_at) VALUES (?,?,?,?,?,?,?)",
                (lifecycle_uuid, seq, next_intent or "", blockers or "",
                 files_note or "", body or "", ts))
            if decisions:
                dseq = _exec(self,
                    "SELECT COALESCE(MAX(seq),0) AS m FROM decisions WHERE lifecycle_uuid=?",
                    (lifecycle_uuid,)).fetchone()["m"]
                for d in decisions:
                    if isinstance(d, dict):
                        topic, text = d.get("topic", ""), d.get("text", "")
                    elif isinstance(d, (list, tuple)) and len(d) == 2:
                        topic, text = d
                    else:
                        # Same class as the files-list defect (fix-round 2,
                        # 2026-07-26): silently skipping a malformed
                        # decision would let checkpoint() report success
                        # while quietly recording fewer decisions than the
                        # caller asked for. Raising here (inside the open
                        # transaction) rolls back the WHOLE checkpoint,
                        # including the digest row already inserted above:
                        # never a partial, mis-numbered decision history.
                        raise OwnershipRefused(
                            "bad-decision",
                            "decision entry %r (type %s) is not a dict with "
                            "topic/text or a 2-item (topic, text) pair, and "
                            "cannot be stored" % (d, type(d).__name__),
                            details={"entry": repr(d), "type": type(d).__name__})
                    dseq += 1
                    _exec(self,
                        "INSERT INTO decisions (lifecycle_uuid, seq, topic, "
                        "text, created_at) VALUES (?,?,?,?,?)",
                        (lifecycle_uuid, dseq, topic or "", text or "", ts))
            _exec(self,
                "UPDATE records SET version=version+1, updated_at=? WHERE lifecycle_uuid=?",
                (ts, lifecycle_uuid))
            return seq

    def decide(self, lifecycle_uuid, expected_version, topic, text):
        """Record one tagged decision. Carries expected_version and bumps
        the record's version like every other mutation (Decision 3: every
        mutation carries an expected version and fails when stale), but is
        not restricted to the active state the way checkpoint is: a
        decision can legitimately be recorded while reconciling a parked or
        adopted record too."""
        with self._transaction() as conn:
            row = _exec(self,
                "SELECT * FROM records WHERE lifecycle_uuid=?", (lifecycle_uuid,)).fetchone()
            if row is None or row["version"] != expected_version:
                raise StaleIdentity(
                    "decide requires version %r; found %s"
                    % (expected_version,
                       "no such record" if row is None else "version %s" % row["version"]),
                    current_state=row["state"] if row is not None else None,
                    current_version=row["version"] if row is not None else None)
            ts = now_iso()
            seq = (_exec(self,
                "SELECT COALESCE(MAX(seq),0) AS m FROM decisions WHERE lifecycle_uuid=?",
                (lifecycle_uuid,)).fetchone()["m"]) + 1
            _exec(self,
                "INSERT INTO decisions (lifecycle_uuid, seq, topic, text, "
                "created_at) VALUES (?,?,?,?,?)",
                (lifecycle_uuid, seq, topic or "", text or "", ts))
            _exec(self,
                "UPDATE records SET version=version+1, updated_at=? WHERE lifecycle_uuid=?",
                (ts, lifecycle_uuid))
            return seq

    def send(self, lifecycle_uuid, text):
        """A directive INTO an active record only. No expected_version
        parameter (the spec gives this call none), so it does not
        participate in optimistic concurrency the way checkpoint/decide/
        transition do; it is still state-gated (ACTIVE only), and that
        refusal is reported as StaleIdentity for the same reason checkpoint's
        is: the record is no longer in the life the caller assumed it was."""
        with self._transaction() as conn:
            row = _exec(self,
                "SELECT * FROM records WHERE lifecycle_uuid=?", (lifecycle_uuid,)).fetchone()
            if row is None or row["state"] != "active":
                raise StaleIdentity(
                    "send requires an ACTIVE record; found %s"
                    % ("no such record" if row is None else "state %r" % row["state"]),
                    current_state=row["state"] if row is not None else None,
                    current_version=row["version"] if row is not None else None)
            ts = now_iso()
            seq = (_exec(self,
                "SELECT COALESCE(MAX(seq),0) AS m FROM directives WHERE lifecycle_uuid=?",
                (lifecycle_uuid,)).fetchone()["m"]) + 1
            _exec(self,
                "INSERT INTO directives (lifecycle_uuid, seq, text, created_at, "
                "delivered_at) VALUES (?,?,?,?,NULL)",
                (lifecycle_uuid, seq, text or "", ts))
            return seq

    # -- handover / render / dump -----------------------------------------

    def handover_payload(self, lifecycle_uuid):
        """objective, files, owner, tier, check, evidence, the latest digest
        sections, and every decision, plus a FULL 64-hex-char sha256
        fingerprint of the canonical JSON of everything above it (fixes
        F13: V1 truncated its fingerprint to 12 hex chars and two different
        handovers collided on it, silently dropping the second one). The
        dict key is "check" (matching the spec's payload wording) even
        though the underlying column is check_cmd (matching the DDL); the
        two names describe the same value at two different layers."""
        row = _exec(self,
            "SELECT * FROM records WHERE lifecycle_uuid=?", (lifecycle_uuid,)).fetchone()
        if row is None:
            raise StaleIdentity(
                "no record with lifecycle_uuid %s" % lifecycle_uuid,
                current_state=None, current_version=None)
        files = [r["path"] for r in _exec(self,
            "SELECT path FROM claims WHERE lifecycle_uuid=? ORDER BY path",
            (lifecycle_uuid,)).fetchall()]
        digest_row = _exec(self,
            "SELECT * FROM digests WHERE lifecycle_uuid=? ORDER BY seq DESC LIMIT 1",
            (lifecycle_uuid,)).fetchone()
        digest = None
        if digest_row is not None:
            digest = {"seq": digest_row["seq"], "next_intent": digest_row["next_intent"],
                      "blockers": digest_row["blockers"],
                      "files_note": digest_row["files_note"], "body": digest_row["body"]}
        decisions = [
            {"seq": d["seq"], "topic": d["topic"], "text": d["text"], "created_at": d["created_at"]}
            for d in _exec(self,
                "SELECT * FROM decisions WHERE lifecycle_uuid=? ORDER BY seq",
                (lifecycle_uuid,)).fetchall()
        ]
        payload = {
            "lifecycle_uuid": lifecycle_uuid,
            "name": row["name"],
            "objective": row["objective"],
            "files": files,
            "owner": row["owner"],
            "tier": row["tier"],
            "check": row["check_cmd"],
            "evidence": row["evidence"],
            "digest": digest,
            "decisions": decisions,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        payload["fingerprint"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return payload

    def render_digest(self, lifecycle_uuid):
        """A bounded, human-readable handover for one lifecycle. Each
        section below is truncated to ITS OWN fixed budget, independently of
        every other section (see _SECTION_BUDGETS). V1 kept one shared
        4000-char pool where a long run of decisions could crowd out
        next_intent entirely (F12): exactly the field a resuming session
        needs first. Fixed per-section budgets mean next_intent can never be
        displaced, no matter how much decision history exists. Advisory for a
        missing record (renders a plain string instead of raising), but NOT
        advisory for redaction: every founder-typed field below (the
        objective, next_intent, blockers, files_note, each decision's topic
        and text) is passed through redact_text() before truncation, and
        raises RedactionUnavailable rather than rendering unredacted text if
        that cannot happen.

        SOFT E (fix-round 3, 2026-07-26): the header carries the objective,
        as the ratified spec's own budget list names it ("header (lifecycle,
        objective) 400 chars"); it used to carry name/state/lifetime only,
        so a resuming session read a handover that never said what the work
        was for."""
        row = _exec(self,
            "SELECT * FROM records WHERE lifecycle_uuid=?", (lifecycle_uuid,)).fetchone()
        if row is None:
            return "(no record with lifecycle_uuid %s)" % lifecycle_uuid
        objective_text = redact_text(row["objective"]) if row["objective"] else "(no objective)"
        header = _truncate(
            "lifecycle %s: %s (%s, %s): %s"
            % (lifecycle_uuid[:8], row["name"], row["state"], row["lifetime"], objective_text),
            _SECTION_BUDGETS["header"])
        digest_row = _exec(self,
            "SELECT * FROM digests WHERE lifecycle_uuid=? ORDER BY seq DESC LIMIT 1",
            (lifecycle_uuid,)).fetchone()
        next_intent = _truncate(
            redact_text(digest_row["next_intent"]) if digest_row else "",
            _SECTION_BUDGETS["next_intent"])
        blockers = _truncate(
            redact_text(digest_row["blockers"]) if digest_row else "",
            _SECTION_BUDGETS["blockers"])
        files_note = _truncate(
            redact_text(digest_row["files_note"]) if digest_row else "",
            _SECTION_BUDGETS["files_note"])
        decisions = _exec(self,
            "SELECT * FROM decisions WHERE lifecycle_uuid=? ORDER BY seq DESC",
            (lifecycle_uuid,)).fetchall()
        new_lines, used, idx = [], 0, 0
        while idx < len(decisions):
            d = decisions[idx]
            line = "- [%s] %s" % (redact_text(d["topic"]), redact_text(d["text"]))
            cost = len(line) + (1 if new_lines else 0)
            if used + cost > _SECTION_BUDGETS["decisions_new"]:
                break
            new_lines.append(line)
            used += cost
            idx += 1
        older = decisions[idx:]
        if new_lines:
            newest_block = "\n".join(new_lines)
        elif decisions:
            newest_block = ("(truncated: newest decision does not fit the "
                             "%d char budget)" % _SECTION_BUDGETS["decisions_new"])
        else:
            newest_block = "(none)"
        older_lines, older_used, older_shown = [], 0, 0
        for d in older:
            line = "- [%s] %s" % (redact_text(d["topic"]), redact_text(d["text"]))
            cost = len(line) + (1 if older_lines else 0)
            if older_used + cost > _SECTION_BUDGETS["decisions_old"]:
                break
            older_lines.append(line)
            older_used += cost
            older_shown += 1
        older_block = "\n".join(older_lines) if older_lines else ""
        if older_shown < len(older):
            marker = "(%d more, truncated)" % (len(older) - older_shown)
            older_block = (older_block + "\n" + marker) if older_block else marker
        sections = [
            header,
            "## Next intent", next_intent or "(none)",
            "## Blockers", blockers or "(none)",
            "## Files", files_note or "(none)",
            "## Decisions", newest_block,
        ]
        if older:
            sections.append("### Older decisions")
            sections.append(older_block if older_block else "(none)")
        return "\n\n".join(sections) + "\n"

    def dump(self):
        """Full JSON-serializable export of every table, RAW and UNREDACTED
        on purpose: this is the one deliberate escape hatch for a human
        inspecting the store by hand or a future migration, not a display
        view. It never calls redact_text(). SECURITY.md documents the sqlite
        file (and therefore this export) as sensitive; every OTHER function
        in this module that renders founder-typed text for STATE.md, a
        digest, or a terminal redacts it first (see the Redaction section
        near the top of this file)."""
        out = {}
        for t in _TABLES:
            rows = _exec(self, "SELECT * FROM %s" % t).fetchall()
            out[t] = [dict(r) for r in rows]
        return out


# ---------------------------------------------------------------------------
# init: creates the store and, best-effort, keeps its files out of git
# status without touching the founder's own .gitignore (fixes finding 30).
# ---------------------------------------------------------------------------

def init_project(root):
    """Create the store and its schema. GATE 7 (fix-round 2026-07-26) moved
    the .git/info/exclude and chmod work into Store.__init__ itself, since
    every command creates the store directory as a side effect and none of
    them should wait for someone to remember to run `init` first; this
    function is kept as the named, documented entry point the CLI's `init`
    command and any external caller use, and it still does exactly that
    work by constructing a Store."""
    return Store(root)


# ---------------------------------------------------------------------------
# Generated views: render_state_md/write_state_view/verify all take a root
# and open their own Store, since they are typically called standalone
# (from the CLI) rather than from inside an already-open Store workflow.
# ---------------------------------------------------------------------------

def _atomic_write_text(path, text):
    """Crash-atomic whole-file replacement via a same-directory temp file
    plus os.replace, which is atomic on POSIX and on Windows (unlike a plain
    truncating write, which can leave the file empty after a crash mid-write).
    chmod is best-effort: Windows ACLs make a POSIX mode a courtesy, not a
    guarantee, so a failure here must never fail the write itself."""
    d = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(prefix=".bm_store.", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    try:
        os.chmod(path, 0o644)
    except OSError:
        pass


def _redacted_view_text(raw):
    """redact_text() then _neutralize_markers(): the ONE pipeline every
    founder-typed field goes through before entering a generated view
    (GATE 8, fix-round 2026-07-26). Order matters: redaction runs on the
    real content first, marker-neutralization runs last so it operates on
    exactly what is about to be embedded."""
    return _neutralize_markers(redact_text(raw))


def render_state_md(root):
    """The generated human view of every record. Advisory for missing data
    (never raises for that), but every founder-typed field rendered below
    (objective, tier, claim paths, next intent) is passed through
    _redacted_view_text() first (GATE 8a: tier and claim paths used to reach
    STATE.md unredacted), and raises RedactionUnavailable rather than emit
    unredacted text if that cannot happen. The literal BEGIN/END marker
    strings are neutralized inside that same pipeline (GATE 8b), so founder
    text can never masquerade as a real marker and corrupt the generated
    block's boundary. A store that cannot even be opened propagates
    StoreCorrupt from Store(root); a later-page corruption during rendering
    is caught by _exec (GATE 4)."""
    store = Store(root)
    try:
        rows = _exec(store, "SELECT * FROM records ORDER BY state, name").fetchall()
        lines = [_STATE_BEGIN,
                 "_Generated by bm_store.py, %s. Edit outside the markers; "
                 "anything inside them is overwritten on the next render._" % now_iso(),
                 ""]
        if not rows:
            lines.append("No records.")
        by_state = {}
        for r in rows:
            by_state.setdefault(r["state"], []).append(r)
        for state in ("active", "parked", "complete", "adopted"):
            recs = by_state.get(state, [])
            if not recs:
                continue
            lines.append("## %s" % state)
            for r in recs:
                files = [c["path"] for c in _exec(store,
                    "SELECT path FROM claims WHERE lifecycle_uuid=? ORDER BY path",
                    (r["lifecycle_uuid"],)).fetchall()]
                tier_text = _redacted_view_text(r["tier"]) if r["tier"] else "no tier"
                lines.append("- %s (%s, %s) [%s]"
                             % (r["name"], r["lifecycle_uuid"][:8], r["lifetime"], tier_text))
                lines.append("  objective: %s"
                             % (_redacted_view_text(r["objective"]) if r["objective"] else "(none)"))
                files_text = (", ".join(_redacted_view_text(f) for f in files)
                              if files else "(none)")
                lines.append("  files: %s" % files_text)
                digest_row = _exec(store,
                    "SELECT next_intent FROM digests WHERE lifecycle_uuid=? "
                    "ORDER BY seq DESC LIMIT 1", (r["lifecycle_uuid"],)).fetchone()
                if digest_row and digest_row["next_intent"]:
                    lines.append("  next intent: %s" % _redacted_view_text(digest_row["next_intent"]))
            lines.append("")
        lines.append(_STATE_END)
        return "\n".join(lines) + "\n"
    finally:
        store.close()


def write_state_view(root):
    """Regenerate the view and write it into STATE.md between BEGIN/END
    GENERATED markers, preserving any human prose outside them. A file with
    no markers yet gets them appended after whatever prose already exists; a
    file that does not exist yet gets just the generated block."""
    generated = render_state_md(root)
    path = os.path.join(root, "STATE.md")
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            existing = f.read()
    except OSError:
        existing = ""
    if _STATE_BEGIN in existing and _STATE_END in existing:
        pre, rest = existing.split(_STATE_BEGIN, 1)
        _mid, post = rest.split(_STATE_END, 1)
        new_text = pre + generated + post
    elif existing:
        sep = "" if existing.endswith("\n\n") else ("\n" if existing.endswith("\n") else "\n\n")
        new_text = existing + sep + generated
    else:
        new_text = generated
    _atomic_write_text(path, new_text)
    return new_text


def verify(root):
    """Machine invariants over the whole store. Empty list means healthy.
    This replaces V1's one-directional check (fixes F15): the store IS both
    directions, so verify checks the same union-of-claims invariant claim()
    enforces at write time, plus the generated view and transition history,
    rather than trusting that nothing has drifted since the last write."""
    store = Store(root)
    try:
        problems = []
        dupes = _exec(store,
            "SELECT name, COUNT(*) AS c FROM records WHERE state='active' "
            "GROUP BY name HAVING COUNT(*) > 1").fetchall()
        for d in dupes:
            problems.append("more than one ACTIVE record named %r (%d rows)" % (d["name"], d["c"]))
        active_claims = _exec(store,
            "SELECT r.name AS name, c.lifecycle_uuid AS lifecycle_uuid, c.path AS path "
            "FROM claims c JOIN records r ON r.lifecycle_uuid = c.lifecycle_uuid "
            "WHERE r.state='active'").fetchall()
        for i in range(len(active_claims)):
            for j in range(i + 1, len(active_claims)):
                a, b = active_claims[i], active_claims[j]
                if a["lifecycle_uuid"] == b["lifecycle_uuid"]:
                    continue
                if paths_overlap(a["path"], b["path"]):
                    problems.append(
                        "active claims overlap: '%s' (%s) path %r vs '%s' (%s) path %r"
                        % (a["name"], a["lifecycle_uuid"][:8], a["path"],
                           b["name"], b["lifecycle_uuid"][:8], b["path"]))
        rendered = render_state_md(root)
        for r in _exec(store, "SELECT name FROM records WHERE state='active'").fetchall():
            if r["name"] not in rendered:
                problems.append(
                    "active record %r does not appear in the generated STATE.md view"
                    % r["name"])
        for r in _exec(store, "SELECT lifecycle_uuid, name, state FROM records").fetchall():
            last = _exec(store,
                "SELECT to_state FROM transitions WHERE lifecycle_uuid=? ORDER BY id DESC LIMIT 1",
                (r["lifecycle_uuid"],)).fetchone()
            if last is None:
                if r["state"] != "active":
                    problems.append(
                        "record %r (%s) is in state %r with no transitions row"
                        % (r["name"], r["lifecycle_uuid"][:8], r["state"]))
            elif last["to_state"] != r["state"]:
                problems.append(
                    "record %r (%s) is in state %r but its latest transition "
                    "recorded '%s'" % (r["name"], r["lifecycle_uuid"][:8], r["state"], last["to_state"]))
        return problems
    finally:
        store.close()


# ---------------------------------------------------------------------------
# CLI: python3 tools/bm_store.py <command> ...
# Exit 0 success, 2 refusal (reason code on stdout), 1 corruption/unexpected.
# ---------------------------------------------------------------------------

def _out(s, end="\n"):
    """Write one piece of CLI output that can NEVER raise UnicodeEncodeError
    (GATE 9, fix-round 2026-07-26). A name is now ASCII-only (valid_name), but
    an objective, a decision, or a tier is free text and can carry anything;
    on a stdout whose encoding cannot represent it, a bare print() raises
    UnicodeEncodeError, whose ONLY ancestor besides UnicodeError is
    ValueError (verified: UnicodeEncodeError.__mro__ includes ValueError,
    not a sibling of it). Before this helper, that exception reached main()'s
    ValueError handler and reported an already-committed success as a
    'bad-input' refusal. Falling back to backslashreplace means the founder
    always sees SOME text instead of a crash or a misreported outcome."""
    text = s + end
    try:
        sys.stdout.write(text)
    except UnicodeEncodeError:
        enc = getattr(sys.stdout, "encoding", None) or "ascii"
        try:
            sys.stdout.buffer.write(text.encode(enc, errors="backslashreplace"))
        except Exception:
            sys.stdout.write(text.encode("ascii", errors="backslashreplace").decode("ascii"))
        try:
            sys.stdout.flush()
        except Exception:
            pass


def _parse_kv(argv):
    """"--flag value [value ...]" parsing: everything after a flag, up to
    the next flag, is that flag's value list. The same shape bm_threads.py
    uses for its checkpoint command, so a founder who has read one BrotherMode
    CLI can read this one too."""
    kv, key = {}, None
    for a in argv:
        if a.startswith("--"):
            key = a[2:]
            kv.setdefault(key, [])
        elif key is not None:
            kv[key].append(a)
    return kv


def _default_cli_session_id():
    """A fresh, unguessable session id for THIS process (GATE 3, fix-round
    2026-07-26): two independent CLI invocations that both omit --session
    used to both carry session_id="", and an empty session matched another
    empty session, so the second process silently reclaimed the first one's
    active record and exited 0 (the F3 takeover, back through the CLI door).
    Stable for the lifetime of one process; NEVER shared across processes,
    which is exactly what makes two independent invocations un-collidable.
    A human doing a multi-step CLI workflow (claim, then later park/resume)
    must pass the SAME --session explicitly across those invocations; this
    default only protects the case where nobody thought about sessions at
    all."""
    return "cli-" + uuid.uuid4().hex


def cmd_init(argv):
    root, source = resolve_root()
    if root is None:
        # init is the one command allowed to proceed with no-root: its whole
        # job is to CREATE the marker. Falling back to cwd is the only
        # sensible choice when nothing else anchors a project here.
        root = os.path.realpath(os.getcwd())
        source = "cwd (nothing found to anchor on; this becomes the new root)"
    init_project(root)
    _out("bm_store: initialized %s (root resolved via %s)" % (store_path(root), source))


def cmd_claim(argv):
    if not argv:
        _out("usage: claim <name> --lifetime persistent|ephemeral --objective TEXT "
             "[--files PATH ...] [--owner X] [--session SID] [--tier T] "
             "[--check CMD] [--ttl-hours N]")
        sys.exit(2)
    name = argv[0]
    kv = _parse_kv(argv[1:])
    root, _source = require_root()
    lifetime = " ".join(kv.get("lifetime", [])) or "ephemeral"
    objective = " ".join(kv.get("objective", []))
    files = kv.get("files", [])
    owner = " ".join(kv.get("owner", []))
    # GATE 3: an omitted --session gets a fresh per-process id, never "".
    session_id = " ".join(kv.get("session", [])) or _default_cli_session_id()
    tier = " ".join(kv.get("tier", []))
    check_cmd = " ".join(kv.get("check", []))
    ttl_raw = kv.get("ttl-hours")
    ttl_hours = float(ttl_raw[0]) if ttl_raw else None
    store = Store(root)
    try:
        rec = store.claim(name, lifetime, objective, files, owner=owner,
                           session_id=session_id, tier=tier, check_cmd=check_cmd,
                           ttl_hours=ttl_hours, cwd=os.getcwd())
    finally:
        store.close()
    _out("claimed '%s' as lifecycle %s (version %s, session %s)"
         % (rec.name, rec.lifecycle_uuid, rec.version, rec.session_id))


def _cmd_transition(argv, to_state, usage):
    if not argv:
        _out("usage: %s" % usage)
        sys.exit(2)
    lifecycle_uuid = argv[0]
    kv = _parse_kv(argv[1:])
    ver_raw = kv.get("version")
    if not ver_raw:
        _out("usage: %s" % usage)
        _out("  --version is required (optimistic concurrency: pass the version you last saw)")
        sys.exit(2)
    expected_version = int(ver_raw[0])
    session_id = " ".join(kv.get("session", []))
    note = " ".join(kv.get("note", []))
    evidence = " ".join(kv.get("evidence", []))
    root, _source = require_root()
    store = Store(root)
    try:
        rec = store.transition(lifecycle_uuid, expected_version, to_state,
                                session_id=session_id, note=note, evidence=evidence)
    finally:
        store.close()
    _out("%s: '%s' (lifecycle %s) is now %s at version %s"
         % (to_state, rec.name, rec.lifecycle_uuid, rec.state, rec.version))


def cmd_park(argv):
    _cmd_transition(argv, "parked", "park <lifecycle_uuid> --version N [--session SID] [--note TEXT]")


def cmd_resume(argv):
    _cmd_transition(argv, "active", "resume <lifecycle_uuid> --version N [--session SID] [--note TEXT]")


def cmd_complete(argv):
    _cmd_transition(argv, "complete",
                     "complete <lifecycle_uuid> --version N --evidence TEXT [--session SID] [--note TEXT]")


def cmd_adopt(argv):
    _cmd_transition(argv, "adopted", "adopt <lifecycle_uuid> --version N [--session SID] [--note TEXT]")


def cmd_checkpoint(argv):
    if not argv:
        _out("usage: checkpoint <lifecycle_uuid> --version N --next TEXT "
             "[--blockers TEXT] [--files-note TEXT] [--body TEXT]")
        sys.exit(2)
    lifecycle_uuid = argv[0]
    kv = _parse_kv(argv[1:])
    ver_raw = kv.get("version")
    if not ver_raw:
        _out("checkpoint: --version is required (optimistic concurrency)")
        sys.exit(2)
    expected_version = int(ver_raw[0])
    next_intent = " ".join(kv.get("next", []))
    blockers = " ".join(kv.get("blockers", []))
    files_note = " ".join(kv.get("files-note", []))
    body = " ".join(kv.get("body", []))
    root, _source = require_root()
    store = Store(root)
    try:
        seq = store.checkpoint(lifecycle_uuid, expected_version, next_intent,
                                blockers=blockers, files_note=files_note, body=body)
    finally:
        store.close()
    _out("checkpoint %d recorded for %s" % (seq, lifecycle_uuid))


def cmd_decide(argv):
    if not argv:
        _out("usage: decide <lifecycle_uuid> --version N --topic T --text TEXT")
        sys.exit(2)
    lifecycle_uuid = argv[0]
    kv = _parse_kv(argv[1:])
    ver_raw = kv.get("version")
    if not ver_raw:
        _out("decide: --version is required (optimistic concurrency)")
        sys.exit(2)
    expected_version = int(ver_raw[0])
    topic = " ".join(kv.get("topic", []))
    text = " ".join(kv.get("text", []))
    root, _source = require_root()
    store = Store(root)
    try:
        seq = store.decide(lifecycle_uuid, expected_version, topic, text)
    finally:
        store.close()
    _out("decision %d recorded for %s" % (seq, lifecycle_uuid))


def cmd_dashboard(argv):
    root, _source = require_root()
    _out(render_state_md(root), end="")


def cmd_dump(argv):
    root, _source = require_root()
    store = Store(root)
    try:
        data = store.dump()
    finally:
        store.close()
    _out(json.dumps(data, indent=2, sort_keys=True))


def cmd_verify(argv):
    root, _source = require_root()
    problems = verify(root)
    if not problems:
        _out("verify: healthy, 0 problem(s)")
        return
    _out("verify: %d problem(s) found:" % len(problems))
    for p in problems:
        _out("  - %s" % p)
    sys.exit(2)


_COMMANDS = {
    "init": cmd_init, "claim": cmd_claim, "park": cmd_park, "resume": cmd_resume,
    "complete": cmd_complete, "adopt": cmd_adopt, "checkpoint": cmd_checkpoint,
    "decide": cmd_decide, "dashboard": cmd_dashboard, "dump": cmd_dump,
    "verify": cmd_verify,
}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    cmd = argv[0] if argv else ""
    rest = argv[1:]
    fn = _COMMANDS.get(cmd)
    if fn is None:
        _out((__doc__ or "").strip())
        _out("\ncommands: %s" % ", ".join(sorted(_COMMANDS)))
        sys.exit(0 if cmd == "" else 2)
    try:
        fn(rest)
    except SystemExit:
        raise
    except UnicodeEncodeError as e:
        # GATE 9 (fix-round 2026-07-26): MUST be caught before ValueError.
        # UnicodeEncodeError is a ValueError subclass (verified via
        # __mro__), so without this clause first, the ValueError handler
        # below caught it and reported an already-committed success as a
        # bad-input refusal. This is a defense-in-depth backstop: the
        # primary fix is that _out() never lets an encode failure escape a
        # print call in the first place. Reported via stderr (bypassing
        # whatever made stdout narrow) and exit 1: this is an environment
        # problem, not a business refusal, so it is never reported as
        # 'bad-input' (exit 2), which was the original misclassification.
        try:
            sys.stderr.write(
                "bm_store: could not encode CLI output for this terminal "
                "(%r); the command may have already succeeded or failed "
                "before this print.\n" % (e,))
        except Exception:
            pass
        sys.exit(1)
    except ValueError as e:
        # A caller-input error (bad name, bad lifetime, unknown target
        # state): the caller's mistake, not corruption, so a plain refusal.
        _out("refused (bad-input): %s" % (e,))
        sys.exit(2)
    except OwnershipRefused as e:
        _out("refused (%s): %s" % (e.reason, e))
        sys.exit(2)
    except StaleIdentity as e:
        _out("refused (stale-identity): %s" % (e,))
        sys.exit(2)
    except StoreCorrupt as e:
        _out("STORE CORRUPT: %s" % (e,))
        sys.exit(1)
    except Exception as e:
        _out("bm_store: unexpected error: %r" % (e,))
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
