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
import shutil
import sqlite3
import sys
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


def _sanitize_for_display(s):
    """Neutralize every C0 control character (0x00-0x1F) and DEL (0x7F) in
    founder-typed text before it enters a generated view or a terminal
    (SOFT D + SOFT E, one pass: both are "a control character reached
    somewhere it should not have"): a raw newline in an objective forged a
    counterfeit record block inside STATE.md while verify() reported
    healthy (SOFT D), and a raw ANSI escape reached a real terminal and
    erased another record's line (SOFT E). valid_name already rejects
    non-printables in NAMES; free-text fields had no equivalent gate. Each
    offending byte becomes a visible \\xHH escape, the same representation
    _out() uses for an unencodable character."""
    if not s:
        return s
    out = []
    for ch in s:
        cp = ord(ch)
        if cp < 0x20 or cp == 0x7f:
            out.append("\\x%02x" % cp)
        else:
            out.append(ch)
    return "".join(out)


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


def _coverage_key(normalized):
    """The directory prefix `normalized` (an already to_posix'd, case-
    folded path) claims: itself when it has no wildcard segment, or its
    _literal_prefix_dir when it does. Computed ONCE per side (the measured
    optimization, prerelease fix round): a non-glob path's coverage key
    IS the path, so _prefix_contains(key, key) already covers exact
    match, and _prefix_contains in either direction already covers plain
    directory containment; this is what lets paths_overlap collapse three
    historical rules (exact match, containment, and the glob literal-
    prefix rule) into the single prefix check below. Measured: verify()
    at 1000 active claims fell from 1621.6 ms to 202.4 ms, and building
    500 records fell from 10381 ms to 2460 ms, from the redundant
    re-normalization paths_overlap used to do on every call even though
    both sides already arrive canonical."""
    return _literal_prefix_dir(normalized) if _has_glob(normalized) else normalized


def paths_overlap(a, b):
    """True when two declared claim paths can name the same file.

    One rule, not three: each side reduces to a COVERAGE KEY (see
    _coverage_key), the directory prefix it claims, and the two paths
    overlap exactly when one key contains the other at a separator
    boundary (or either is the whole-root prefix), which is what
    _prefix_contains already means by "equal, root, or ancestor". api/*.py
    and api/pay.* share coverage key "api" and MUST conflict, even though
    no single filename matches both patterns."""
    na = _normcase(_to_posix(a))
    nb = _normcase(_to_posix(b))
    if not na or not nb:
        return False
    # GATE 1 (fix-round 2026-07-26): '.' is the canonical form of the whole
    # root (see _to_posix and canonicalize_path) and MUST overlap every
    # other path, since it names every file in the project. Kept as an
    # explicit special case: '.' is not a prefix of a path the way
    # _prefix_contains understands "" to be, so the unified check below
    # cannot subsume it.
    if na == "." or nb == ".":
        return True
    ka = _coverage_key(na)
    kb = _coverage_key(nb)
    return _prefix_contains(ka, kb) or _prefix_contains(kb, ka)


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
    closes four defects at once):
    1. Resolves a relative path against cwd BEFORE expressing it
       root-relative, so a claim typed from a subdirectory and the same
       claim typed from the root store the identical string. cwd=None (the
       default for every Python-API caller) means "resolve against root
       itself", NOT os.getcwd(); only the CLI passes cwd=os.getcwd()
       explicitly (see _resolve_against_root for the actual rule).
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
    canonical root-relative path strings, preserving input order. A
    bare string is ONE path, not an iterable of characters, the same
    defensive rule bm_registry's _safe_path_list enforces: claim(...,
    files="a.py") must fence one path, not one character at a time.

    Every entry passes through _coerce_path_entry (TOTAL: string or raise)
    and then canonicalize_path (root-relative, or raise 'path-escape'):
    NOTHING is ever silently dropped. A non-iterable files argument also
    raises 'bad-path' rather than quietly becoming an empty list. A
    NON-EMPTY input that still yields zero stored claims (every entry
    blank, or all collapse to the same path) raises too: a record that
    reports success while fencing nothing is exactly the defect this
    closes. Called BEFORE _transaction() opens (see claim()), so any raise
    here happens before a single byte is written: atomic by construction,
    never a partial fence."""
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
        out.append(canon)
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
    reaching STATE.md or a terminal unredacted. dump() redacts by default
    (GATE C, fix-round 6) and raises this exact exception when it cannot;
    only the explicit, documented dump(raw=True) skips redaction entirely."""

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
    # duplicates is the same as no warning. A FIXED, hardcoded message
    # (never founder text), written with the same raw primitive the funnel
    # uses (_raw_write is defined later in this file; resolved at call
    # time, well after the whole module has loaded) so even this warning
    # never raises UnicodeEncodeError.
    if _WARNED_NO_REDACT:
        return
    _WARNED_NO_REDACT.append(True)
    _raw_write(sys.stderr,
               "bm_store: WARNING: could not load the bm_telemetry redactor (%s); "
               "refusing to render generated views (STATE.md, render_digest, the "
               "dashboard) rather than emit unredacted text. dump() and the raw "
               "sqlite file are unaffected.\n" % _REDACT_LOAD_ERROR)


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
                 "version", "created_at", "updated_at", "files")

    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw.get(k))

    def __repr__(self):
        return ("Record(name=%r, lifecycle_uuid=%r, state=%r, version=%r)"
                % (self.name, self.lifecycle_uuid, self.state, self.version))


# ---------------------------------------------------------------------------
# Schema (schema_version 1). autosave_receipts ships now, unused, so Phase 2
# needs no migration.
#
# Prerelease fix round deletions, both with no consumer anywhere in this
# project (grepped before removing): ttl_hours (the law promised a fence
# past its TTL is treated as released, and nothing anywhere expires
# anything: a claim with a TTL of 0.36 seconds still blocked a second claim
# a second later) and claims.is_glob (written on every insert, read back by
# nothing: paths_overlap already detects a glob from the PATH TEXT itself,
# never from a stored flag). The deliveries table is deleted too: no writer
# anywhere, and docs/KNOWN-LIMITS.md already committed that Phase 3 would
# either write it or it would go. Neither deletion touches a store that
# already has these columns/table; SCHEMA_VERSION is unchanged because
# _verify_schema_or_raise only requires the tables in _TABLES to be
# PRESENT, never that no others exist, so an old store's now-orphaned
# columns and table are harmless leftovers, not a migration.
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
  version INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS one_active_per_name ON records(name) WHERE state='active';
CREATE TABLE IF NOT EXISTS claims (
  lifecycle_uuid TEXT NOT NULL REFERENCES records(lifecycle_uuid) ON DELETE CASCADE,
  path TEXT NOT NULL,
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
CREATE TABLE IF NOT EXISTS transitions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lifecycle_uuid TEXT NOT NULL,
  from_state TEXT,
  to_state TEXT NOT NULL,
  session_id TEXT NOT NULL DEFAULT '',
  note TEXT NOT NULL DEFAULT '',
  at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS transitions_lifecycle_uuid_idx ON transitions(lifecycle_uuid);
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
           "transitions", "autosave_receipts")

# GATE C (fix-round 6, 2026-07-26): DEFAULT-DENY. dump() used to redact an
# enumerated list of "known sensitive" fields (objective, tier, claim paths,
# decisions, digests) and print everything else in cleartext, which is
# exactly why transitions.note, directives.text, records.evidence,
# records.check_cmd, and records.owner leaked: nobody had listed them. This
# is the inverse: every (table, column) pair below is the CLOSED,
# deliberately reviewed set of structurally non-sensitive data (identifiers,
# enums, versions, counts, hashes, timestamps); every OTHER text-typed
# column, read live from the schema via PRAGMA table_info (see
# _text_columns), is redacted automatically. A new text column added to
# _DDL without being added here is redacted by default, not exposed by
# default: the failure direction that matters is flipped.
# records.name was in this set until fix-round 7 (2026-07-26): it was
# treated as an identifier-shaped column like lifecycle_uuid, but a NAME is
# founder-typed free text (valid_name only rejects reserved characters and
# whitespace; it happily accepts "AKIAIOSFODNN7EXAMPLE" or "password=hunter2"
# as a name), so listing it here meant the one dump column an adversary
# could put a real secret shape into was also the one this allowlist
# exempted from redaction. Removing it means dump()'s existing default-deny
# machinery (below) now redacts it exactly like every other free-text
# column, with no new call site: the record is still identifiable via its
# lifecycle_uuid, which is never redacted and sits right beside the name at
# every other exit (render_state_md, render_digest).
_DUMP_SAFE_COLUMNS = frozenset((
    ("meta", "key"), ("meta", "value"),
    ("records", "lifecycle_uuid"), ("records", "lifetime"),
    ("records", "state"), ("records", "session_id"),
    ("records", "created_at"), ("records", "updated_at"),
    ("claims", "lifecycle_uuid"),
    ("decisions", "lifecycle_uuid"), ("decisions", "created_at"),
    ("digests", "lifecycle_uuid"), ("digests", "created_at"),
    ("directives", "lifecycle_uuid"), ("directives", "created_at"),
    ("directives", "delivered_at"),
    ("transitions", "lifecycle_uuid"), ("transitions", "from_state"),
    ("transitions", "to_state"), ("transitions", "session_id"), ("transitions", "at"),
    ("autosave_receipts", "worktree_id"), ("autosave_receipts", "session_id"),
    ("autosave_receipts", "snapshot_sha"), ("autosave_receipts", "tree_sha"),
    ("autosave_receipts", "source_head"), ("autosave_receipts", "created_at"),
))


def _text_columns(conn, table):
    """Column names in `table` with TEXT storage affinity, read from the
    LIVE schema via PRAGMA table_info, not a hand-maintained list: a new
    column joins this the moment it exists in _DDL, with no other code
    change required for it to be redacted by default (GATE C)."""
    out = []
    for row in conn.execute("PRAGMA table_info(%s)" % table).fetchall():
        col_type = (row["type"] or "").upper()
        if any(kw in col_type for kw in ("CHAR", "TEXT", "CLOB")):
            out.append(row["name"])
    return out


def _ownership_guard_applies(current_state):
    """BLOCKER 2 (release-blockers spec, 2026-07-26): the not-owner guard
    in Store.transition() protects a record ONLY while it is CURRENTLY
    'active' (a live writer exists). Extracted as its own tiny, named
    function -- rather than left as an inline comparison inside
    transition() -- so a reinjection test can monkeypatch this exact
    module symbol back to the OLD, unconditional shape (always True) and
    prove that a resume from a different session used to be wrongly
    refused after a park, without duplicating transition()'s surrounding
    transactional logic in the test."""
    return current_state == "active"


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


def _refuse_if_symlink_escape(expected_path):
    """The ONE containment check for any path this module treats as living
    LITERALLY at expected_path (GATE D, extended to the store file and its
    sidecars as GATE B): a symlinked .brothermode DIRECTORY was refused,
    but .brothermode/store.sqlite3 (and its -wal/-shm) were never checked,
    so a symlinked store FILE still wrote the raw database outside the
    project root. Only checks paths that already exist (os.path.lexists,
    which does not follow the final symlink): a path about to be freshly
    created cannot be an escape yet. Raises OwnershipRefused 'path-escape'."""
    if not os.path.lexists(expected_path):
        return
    real_path = os.path.realpath(expected_path)
    if real_path != expected_path:
        raise OwnershipRefused(
            "path-escape",
            "%s is a symlink (or contains one) resolving to %s; refusing "
            "to use it rather than write the sensitive store outside the "
            "project root or chmod that target" % (expected_path, real_path),
            details={"expected": expected_path, "resolved": real_path})


def _refuse_if_hardlinked(expected_path):
    """SOFT D: the symlink check above cannot see a HARDLINK. A second,
    git-visible filename hardlinked to .brothermode/store.sqlite3 (or its
    -wal/-shm) shares the same inode, so os.path.realpath(expected_path)
    still equals expected_path (no symlink to resolve) even though the raw
    sqlite bytes are also reachable, and committable, through that other
    name. st_nlink counts every hard-linked name a file has; an ordinary,
    unshared file always reports 1. Only checks paths that already exist."""
    if not os.path.lexists(expected_path):
        return
    try:
        st = os.stat(expected_path)
    except OSError:
        return
    if st.st_nlink > 1:
        raise OwnershipRefused(
            "path-escape",
            "%s has %d hard links (expected exactly 1); a hardlink cannot "
            "be detected by inspecting the path alone, unlike a symlink, so "
            "refusing rather than risk the sensitive store also being "
            "reachable, and committable, through another name. Find the "
            "other name with `find <search-root> -samefile %s`, remove it, "
            "and retry." % (expected_path, st.st_nlink, expected_path))


def _looks_like_git_admin_dir(path):
    """True only when path ALREADY EXISTS and has the layout a real git
    administrative directory has (a HEAD file plus an objects or refs
    directory). Used to validate a .git file's 'gitdir:' pointer before
    ever creating anything at the path it names (SOFT G, fix-round 6,
    2026-07-26): a .git file's content is not a trusted input (it can be
    crafted or corrupted), and following an unchecked pointer straight into
    os.makedirs plus a write is an arbitrary-directory-creation primitive.
    Never creates path; only inspects it."""
    if not os.path.isdir(path):
        return False
    if not os.path.isfile(os.path.join(path, "HEAD")):
        return False
    return (os.path.isdir(os.path.join(path, "objects"))
            or os.path.isdir(os.path.join(path, "refs")))


def _resolve_git_common_dir(root):
    """The directory that actually holds info/exclude for this checkout
    (GATE C). A normal checkout: <root>/.git. A worktree: .git is a FILE
    containing 'gitdir: <path>' pointing at <main>/.git/worktrees/<name>;
    info/exclude is NOT per-worktree, it is shared once at the top of the
    MAIN checkout's .git, named by that worktree gitdir's own 'commondir'
    file (present since git 2.5); returning early on a .git FILE used to
    leave nothing excluded inside a worktree, so `git add -A` staged the
    raw store. Returns None when there is no git here, or it could not be
    read.

    SOFT G: the pointer is validated with _looks_like_git_admin_dir before
    being trusted, and NEVER created by us: a crafted .git file naming an
    arbitrary path (e.g. 'gitdir: /etc') used to make this return that path
    verbatim, and the caller would os.makedirs a tree there. Raises
    OwnershipRefused('path-escape') instead."""
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
    if not _looks_like_git_admin_dir(worktree_gitdir):
        raise OwnershipRefused(
            "path-escape",
            "the .git file at %s points to %s, which does not exist or "
            "does not look like real git administrative state; refusing "
            "to create directories or write anything there"
            % (git_path, worktree_gitdir),
            details={"git_file": git_path, "pointer_target": worktree_gitdir})
    commondir_file = os.path.join(worktree_gitdir, "commondir")
    if os.path.isfile(commondir_file):
        try:
            with open(commondir_file, encoding="utf-8", errors="replace") as f:
                rel = f.read().strip()
        except OSError:
            return worktree_gitdir
        common = os.path.realpath(os.path.join(worktree_gitdir, rel))
        if not _looks_like_git_admin_dir(common):
            raise OwnershipRefused(
                "path-escape",
                "the commondir file at %s points to %s, which does not "
                "exist or does not look like real git administrative "
                "state; refusing to create directories or write anything "
                "there" % (commondir_file, common),
                details={"commondir_file": commondir_file, "pointer_target": common})
        return common
    return worktree_gitdir


def _ensure_git_excludes(root):
    """Append .brothermode/, threads/, STATE.md to the resolved git common
    dir's info/exclude when git is present here and the entries are absent
    (worktree support is GATE C). Called from Store.__init__ on EVERY open
    (GATE 7), not only from init: any command creates .brothermode/
    store.sqlite3 as a side effect, so a routine `git add -A` run before
    anyone happens to run `init` used to commit the store, secrets and
    all. Idempotent: calling it on every open costs nothing once the
    entries are present."""
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
        # issue). The store itself is already created and usable. Routed
        # through the stderr funnel (fix-round 7) like every other warning.
        _warn("bm_store: warning: could not update %s (%s)" % (exclude_path, e))


def _is_transient_busy_error(e):
    """True only for the two sqlite3.OperationalError messages that mean
    "another connection holds the lock right now, try again shortly" (fix-
    round 8, IMPORTANT: every OperationalError used to get the SAME "busy
    or locked, wait and retry" advice, so a genuinely missing table gave
    advice that can never work and hid CRITICAL A's own reproduction behind
    a comforting, wrong message). Every other OperationalError (a missing
    table or column, a disk I/O error, ...) means something is actually
    wrong, and deserves to say so."""
    msg = str(e).lower()
    return "database is locked" in msg or "database is busy" in msg


def _exec(store, sql, params=()):
    """The ONE place any SQL statement runs against a Store's connection
    (GATE 4): Store.__init__ only probed the schema at OPEN time, so damage
    on a later page opened fine and leaked a raw sqlite3.DatabaseError out
    of claim(), dump(), and verify(), unquarantined, exit 1. Every query in
    this module routes through here so the same split applies everywhere:
    a transient busy/locked OperationalError refuses 'db-busy'; any other
    DatabaseError, OperationalError included, quarantines (CRITICAL A: also
    the backstop for a table dropped from under an already-open connection,
    not only one caught at the next fresh open). sqlite3.IntegrityError is
    let through UNCHANGED: a unique-constraint hit is caller-shaped, not
    corruption (see transition()'s 'name-active' handling, GATE 6), and the
    caller is better placed to turn it into a named refusal than this is."""
    try:
        return store.conn.execute(sql, params)
    except sqlite3.IntegrityError:
        raise
    except sqlite3.OperationalError as e:
        if not _is_transient_busy_error(e):
            store._quarantine_and_raise(e)
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

    def __init__(self, root, busy_timeout_ms=5000, create=True):
        """busy_timeout_ms defaults to the spec's 5000; exposed as a keyword
        so a test can force a near-instant "database is locked" without a
        real multi-second wait. Store(root) alone still matches the spec's
        constructor exactly.

        create=False: refuse 'no-store' rather than silently create one,
        naming the exact command to run. Only the CLI's `init` passes
        create=True (the default); every other CLI command passes
        create=False, because "only init creates a store" only means
        something if every other path can refuse instead. Direct Python-API
        callers (this module's own tests included) keep the permissive
        default."""
        self.root = os.path.realpath(root)
        self.conn = None
        expected_store_dir = store_dir(self.root)
        if not create and not os.path.isfile(store_path(self.root)):
            raise OwnershipRefused(
                "no-store",
                "no store exists at %s; run `python3 tools/bm_store.py "
                "init` to create one" % store_path(self.root),
                details={"path": store_path(self.root)})
        os.makedirs(expected_store_dir, exist_ok=True)
        # GATE D (fix-round 3, 2026-07-26): claim paths were already
        # symlink-checked and refused as 'path-escape', but .brothermode
        # itself was not, so a repository carrying .brothermode -> docs (or
        # -> ../shared) wrote the sensitive store outside the project root,
        # defeated the exclude line entirely, and chmod'd the LINK TARGET.
        # Same containment rule, checked BEFORE any chmod or DB open.
        _refuse_if_symlink_escape(expected_store_dir)
        # GATE B (fix-round 5, 2026-07-26): the DIRECTORY check above is not
        # enough; the store FILE itself (and its -wal/-shm sidecars) must be
        # checked too, or a symlinked store.sqlite3 alone writes the raw
        # database outside the project root while the directory looks fine.
        expected_path = store_path(self.root)
        _refuse_if_symlink_escape(expected_path)
        _refuse_if_symlink_escape(expected_path + "-wal")
        _refuse_if_symlink_escape(expected_path + "-shm")
        # SOFT D (fix-round 7, 2026-07-26): same containment intent as the
        # symlink checks above, for the threat a symlink check cannot see.
        _refuse_if_hardlinked(expected_path)
        _refuse_if_hardlinked(expected_path + "-wal")
        _refuse_if_hardlinked(expected_path + "-shm")
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
        # CRITICAL A (fix-round 8): a non-empty file at this path already
        # existed before this open, so its schema must be VERIFIED, never
        # blindly recreated; a brand new path gets _ensure_schema exactly
        # as before. Computed before sqlite3.connect, which creates the
        # file itself when it is missing.
        pre_existing = os.path.isfile(self.path)
        try:
            conn = sqlite3.connect(self.path, timeout=5.0, isolation_level=None)
            conn.row_factory = sqlite3.Row
            self.conn = conn
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=%d" % int(busy_timeout_ms))
            conn.execute("PRAGMA foreign_keys=ON")
            if pre_existing:
                self._verify_schema_or_raise()
            else:
                self._ensure_schema()
            self._ensure_indexes()
            # A read, not just a connect: a corrupt file can open fine and
            # only fail the instant something touches its b-tree pages. Fail
            # here, at construction, rather than on the caller's first real
            # query deep inside an unrelated transaction. Later-page
            # corruption (after this probe passes) is caught by _exec()
            # instead, on every subsequent query (GATE 4).
            self.conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        except sqlite3.OperationalError as e:
            # OperationalError (busy or locked) is a DatabaseError subclass,
            # so this MUST stay before the DatabaseError clause below or it
            # is never reached. A merely-busy database is transient, not
            # corrupt: refuse fail-closed with a retry message and touch
            # nothing. Anything else (fix-round 8: a missing table, for
            # instance) is NOT transient, and quarantines like any other
            # DatabaseError instead of giving retry advice that can never
            # work (see _is_transient_busy_error).
            if not _is_transient_busy_error(e):
                self._quarantine_and_raise(e)
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

    def _ensure_indexes(self):
        """Executed on EVERY open, pre-existing store or brand new (the
        measured optimization, prerelease fix round): CREATE INDEX IF NOT
        EXISTS living only inside _DDL is a SILENT NO-OP for any store that
        already existed before the index was added, because _ensure_schema
        (the only thing that runs _DDL) only ever runs for a BRAND NEW
        file; an existing store takes the _verify_schema_or_raise path
        instead, which never touches _DDL at all. Idempotent (IF NOT
        EXISTS) and measured at 0.006 ms, so running it unconditionally
        here costs nothing once the index exists, and closes the gap for
        every store created before this line did."""
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS transitions_lifecycle_uuid_idx "
            "ON transitions(lifecycle_uuid)")

    def _verify_schema_or_raise(self):
        """CRITICAL A (fix-round 8, reproduced independently: claim alpha on
        api/pay.py, drop the claims table, claim beta on the same path ->
        GRANTED at exit 0, verify -> healthy). _ensure_schema's CREATE TABLE
        IF NOT EXISTS ran unconditionally on every open, so a table missing
        from an EXISTING store (dropped by hand, or left mid-migration) was
        silently recreated empty instead of caught: the double-fence class
        re-entering through the schema door, with a Phase 2/3 migration as
        the realistic trigger. Called only when the file already existed
        before this open; a brand new file still gets _ensure_schema. Every
        expected table must be present and schema_version must match
        exactly, or this quarantines rather than silently repairing."""
        found = {r["name"] for r in self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        missing = sorted(t for t in _TABLES if t not in found)
        if missing:
            self._quarantine_and_raise(
                ValueError("existing store is missing expected table(s): %s" % ", ".join(missing)))
        row = self.conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        found_version = row["value"] if row is not None else None
        if found_version != str(SCHEMA_VERSION):
            self._quarantine_and_raise(
                ValueError("existing store schema_version is %r, expected %r"
                           % (found_version, str(SCHEMA_VERSION))))

    def _quarantine_and_raise(self, cause):
        """Quarantine store.sqlite3 AND its -wal/-shm sidecars into a
        per-incident DIRECTORY (GATE 5): a single renamed FILE let two
        quarantines in the same second collide (os.replace silently
        destroying the first's evidence) and left the sidecars (where the
        actually-lost records can live, WAL keeping recent writes there
        before a checkpoint) behind entirely. The directory name carries
        microsecond precision plus a uuid4 suffix via os.makedirs(exist_ok=
        False), so a name is never reused and nothing is ever replaced onto
        an existing path.

        GATE C: sidecars are COPIED into the quarantine directory BEFORE
        self.conn.close() runs, not after: a newer bundled SQLite (3.53.1,
        with a recent Python 3.13) DELETES stale -wal/-shm files as part of
        close()'s own cleanup, so the old close-then-move order sometimes
        found nothing left to move, worse than the original defect and
        silently version-dependent. Copying while the handle is still open
        is unaffected by whatever close() does to the originals; the main
        file is still moved only after close(), since close() can only act
        on the connection's own handle, not a sidecar file."""
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        suffix = uuid.uuid4().hex[:8]
        qdir = self.path + ".quarantine-%s-%s" % (stamp, suffix)
        # GATE B (fix-round 5, 2026-07-26): the quarantine TARGET is already
        # containment-safe by construction, not by an extra check: exist_ok
        # is False, so if anything (a symlink included) already sits at
        # qdir, os.makedirs raises FileExistsError, caught below, and
        # nothing is ever written through it.
        try:
            os.makedirs(qdir, exist_ok=False)
        except OSError as mkdir_err:
            if self.conn is not None:
                try:
                    self.conn.close()
                except Exception:
                    pass
                self.conn = None
            raise StoreCorrupt(
                "%s is not a readable SQLite database (%s), and a quarantine "
                "directory could not be created either (%s). Nothing was "
                "moved: the damaged file is still at %s; move it aside by "
                "hand, then run init again."
                % (self.path, cause, mkdir_err, self.path))
        # GATE C: preserve the sidecars' CURRENT bytes before close() gets
        # any chance to delete or checkpoint them away. Best-effort: a copy
        # failure here is not fatal by itself, since the finalize pass below
        # (after close) still falls back to moving the original if it
        # survived close() after all.
        preserved = set()
        for src in (self.path + "-wal", self.path + "-shm"):
            if not os.path.exists(src):
                continue
            dst = os.path.join(qdir, os.path.basename(src))
            try:
                shutil.copy2(src, dst)
                _chmod_best_effort(dst, 0o600)
                preserved.add(dst)
            except OSError:
                pass
        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None
        moved, failed = list(preserved), []
        # The main file is not a WAL/SHM sidecar and was never at risk from
        # close() the way GATE C describes, so it is moved here, after
        # close, exactly as before fix-round 7.
        main_dst = os.path.join(qdir, os.path.basename(self.path))
        if os.path.exists(self.path):
            try:
                os.replace(self.path, main_dst)
                _chmod_best_effort(main_dst, 0o600)
                moved.append(main_dst)
            except OSError as move_err:
                failed.append("%s (%s)" % (self.path, move_err))
        # A sidecar still present at its original path after close() (this
        # SQLite version left it behind rather than deleting it) is now
        # redundant with the copy already safely inside qdir: remove the
        # stale original instead of leaving a duplicate scattered outside
        # the quarantine directory. If no copy was preserved above (the
        # copy itself failed), fall back to the original move-in-place
        # behavior so a failed COPY is not also a failed quarantine.
        for src in (self.path + "-wal", self.path + "-shm"):
            if not os.path.exists(src):
                continue
            dst = os.path.join(qdir, os.path.basename(src))
            if dst in preserved:
                try:
                    os.remove(src)
                except OSError:
                    pass
            else:
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
        # SOFT F (fix-round 5, 2026-07-26): this used to say "run init", but
        # since fix-round 4, init REFUSES without --acknowledge-quarantine
        # while this exact quarantine directory exists, so the printed
        # instruction could not be followed. Name the command that actually
        # works: inspect first, THEN acknowledge to start a fresh store.
        raise StoreCorrupt(
            "%s was not a readable SQLite database (%s). It has been "
            "quarantined, together with its -wal/-shm sidecars where "
            "present, to the directory %s (never deleted, never "
            "overwritten: this directory name is unique per incident). "
            "Inspect that directory by hand to recover any records, then "
            "run `python3 tools/bm_store.py init --acknowledge-quarantine` "
            "to start a fresh store." % (self.path, cause, qdir),
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
            # self.conn can already be None here (fix-round 8, found while
            # testing CRITICAL A's new quarantine-on-OperationalError path):
            # a DatabaseError raised mid-transaction routes through _exec,
            # which quarantines and closes/nulls the connection BEFORE this
            # handler ever runs, so a bare self.conn.execute("ROLLBACK")
            # raised AttributeError on None and masked the real
            # StoreCorrupt with a confusing one. Nothing to roll back on a
            # connection that is already gone.
            if self.conn is not None:
                try:
                    self.conn.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
            raise
        else:
            _exec(self, "COMMIT")

    def _record_by_uuid(self, lifecycle_uuid):
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
            version=row["version"],
            created_at=row["created_at"], updated_at=row["updated_at"],
            files=files)

    def get(self, lifecycle_uuid):
        """Read-only fetch of one record by identity. Not named in the
        ratified API list, but every mutation already needs this internally
        to build its return value, and tests and future callers need a way
        to re-read a record without reaching into private methods: exposing
        it is a small, pure-read addition, not a behavior change."""
        return self._record_by_uuid(lifecycle_uuid)

    # -- claim ---------------------------------------------------------

    def _find_overlap(self, norm_files, exclude_uuid=None):
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
        for path in norm_files:
            for r in rows:
                if paths_overlap(path, r["path"]):
                    return (r["name"], r["lifecycle_uuid"], (path, r["path"]))
        return None

    def _admit(self, name, lifetime, norm_files, exclude_uuid=None):
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
        conflict = self._find_overlap(norm_files, exclude_uuid=exclude_uuid)
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
        # SOFT G (fix-round 5, 2026-07-26): the same path string is
        # redacted in the dashboard but was printed raw here; a claim path
        # that happens to contain a secret-shaped substring reached the
        # terminal unredacted through this one message. The message is
        # redacted; details["paths"] stays raw for programmatic callers,
        # since main() only ever prints str(exception), never .details.
        # Redaction here is best-effort: the OVERLAP REFUSAL itself is the
        # safety mechanism and must never become unreliable (surfacing as
        # 'redaction-unavailable' instead of 'overlap') just because the
        # redactor happens to be unavailable at that moment.
        other_name, other_uuid, pair = conflict
        def _safe(p):
            try:
                return _sanitize_for_display(redact_text(p))
            except RedactionUnavailable:
                return "(redacted: unavailable)"
        safe_pair = (_safe(pair[0]), _safe(pair[1]))
        raise OwnershipRefused(
            "overlap",
            "claim overlaps active record '%s' (lifecycle %s): %r vs %r"
            % (other_name, other_uuid, safe_pair[0], safe_pair[1]),
            details={"lifecycle_uuid": other_uuid, "name": other_name,
                     "paths": list(pair)})

    #: Every field a reclaim can update, other than files (handled
    #: separately because it is a list, not a scalar). GATE D's structural
    #: test enumerates this SAME tuple, so a field added here without also
    #: being added to _reclaim_active's None-check below fails that test
    #: instead of shipping a silent-wipe defect.
    UPDATABLE_SCALAR_FIELDS = ("objective", "owner", "tier", "check_cmd")

    def _reclaim_active(self, row, objective, norm, owner, tier, check_cmd):
        """The same session re-declaring a name it already holds active.
        Updates in place, keeps the SAME lifecycle_uuid.

        GATE D: the None-versus-empty rule (GATE A, files) applies to EVERY
        updatable scalar field (see UPDATABLE_SCALAR_FIELDS): None means
        "not supplied", leaving the stored value untouched; any other
        value, an explicit empty string included, is a deliberate write,
        even to clear the field (a reclaim that only wanted to change the
        tier used to silently wipe the objective).

        norm is None when the caller did not supply files: the existing
        claims are left COMPLETELY untouched. norm is a (possibly empty)
        list when the caller explicitly supplied files: [] is a deliberate,
        allowed release, and still re-checks overlap against every OTHER
        active record, since skipping that check would let a same-session
        reclaim silently seize a path a different session already holds."""
        if norm is not None:
            conflict = self._find_overlap(norm, exclude_uuid=row["lifecycle_uuid"])
            if conflict is not None:
                self._raise_overlap(conflict)
        ts = now_iso()
        new_objective = objective if objective is not None else row["objective"]
        new_owner = owner if owner is not None else row["owner"]
        new_tier = tier if tier is not None else row["tier"]
        new_check = check_cmd if check_cmd is not None else row["check_cmd"]
        _exec(self,
            "UPDATE records SET objective=?, owner=?, tier=?, check_cmd=?, "
            "version=version+1, updated_at=? WHERE lifecycle_uuid=?",
            (new_objective, new_owner, new_tier, new_check, ts, row["lifecycle_uuid"]))
        if norm is not None:
            _exec(self, "DELETE FROM claims WHERE lifecycle_uuid=?", (row["lifecycle_uuid"],))
            for path in norm:
                _exec(self,
                    "INSERT INTO claims (lifecycle_uuid, path) VALUES (?,?)",
                    (row["lifecycle_uuid"], path))
        return self._record_by_uuid(row["lifecycle_uuid"])

    def claim(self, name, lifetime, objective=None, files=None, owner=None, session_id="",
              tier=None, check_cmd=None, cwd=None):
        """Register (or, for the SAME non-empty session re-declaring, update
        in place) one unit of work. Every refusal here closes a confirmed
        defect: silent takeover of an active name (F3, and again through
        the CLI door as GATE 3), unbounded file overlap (F1/F2/F11 and the
        GATE 1 canonicalization class), and an uncapped persistent count.

        cwd is the directory relative paths in files are resolved against
        BEFORE being canonicalized root-relative (GATE 1): a claim typed
        from a subdirectory and the same claim typed from the root must
        store the identical string. The default, cwd=None, means "resolve
        against root itself", NOT os.getcwd(): only the CLI passes
        cwd=os.getcwd() explicitly (see canonicalize_path).

        GATE D: objective, owner, tier, and check_cmd default to None, the
        same "not supplied" sentinel files uses (GATE A). On a NEW claim,
        None simply means empty. On a RECLAIM, None LEAVES the stored value
        untouched; any other value, an explicit "" included, is a
        deliberate write, even to clear the field (a reclaim that only
        wanted to update the tier used to silently erase the objective).
        files follows the same rule: None leaves existing claims untouched
        on a reclaim; files=[] is a deliberate release, always honored."""
        valid_name(name)
        if lifetime not in ("persistent", "ephemeral"):
            raise ValueError(
                "lifetime must be 'persistent' or 'ephemeral', got %r" % (lifetime,))
        files_supplied = files is not None
        norm = _normalize_files(files, self.root, cwd) if files_supplied else None
        with self._transaction():
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
                        active, objective, norm, owner, tier, check_cmd)
                raise OwnershipRefused(
                    "name-active",
                    "'%s' is already active as lifecycle %s under session "
                    "%r; that session must park, complete, or adopt it "
                    "before this name can be claimed again (or resume it "
                    "yourself if you hold that session)"
                    % (name, active["lifecycle_uuid"], active["session_id"]),
                    details={"lifecycle_uuid": active["lifecycle_uuid"], "name": name,
                             "held_by_session_id": active["session_id"]})
            # A brand new record with files not supplied is simply an
            # empty fence (unchanged prior behavior); only a RECLAIM (the
            # branch above) treats "not supplied" as "leave alone".
            new_claim_files = norm if files_supplied else []
            self._admit(name, lifetime, new_claim_files)
            lifecycle_uuid = uuid.uuid4().hex
            ts = now_iso()
            _exec(self,
                "INSERT INTO records (lifecycle_uuid, name, lifetime, state, "
                "objective, owner, session_id, tier, check_cmd, evidence, "
                "version, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (lifecycle_uuid, name, lifetime, "active", objective or "",
                 owner or "", session_id or "", tier or "", check_cmd or "",
                 "", 1, ts, ts))
            for path in new_claim_files:
                _exec(self,
                    "INSERT INTO claims (lifecycle_uuid, path) VALUES (?,?)",
                    (lifecycle_uuid, path))
            _exec(self,
                "INSERT INTO transitions (lifecycle_uuid, from_state, to_state, "
                "session_id, note, at) VALUES (?,?,?,?,?,?)",
                (lifecycle_uuid, None, "active", session_id or "", "claimed", ts))
            return self._record_by_uuid(lifecycle_uuid)

    # -- transition ------------------------------------------------------

    def transition(self, lifecycle_uuid, expected_version, to_state,
                    session_id="", note="", evidence="", adopt_from_live_session=False):
        """Move a record along its legal state graph. Every failure to match
        lifecycle_uuid, expected_version, AND a legal source state for
        to_state raises StaleIdentity naming the actual current state and
        version, so a caller reacts to an illegal move and a stale version
        the same way: re-read the record and decide what is actually true.

        OWNERSHIP GUARDS ONLY ACTIVE RECORDS (BLOCKER 2 fix, release-blockers
        spec, 2026-07-26; this was my own specification error, per that
        spec). A non-empty owning session_id blocks a move ONLY when the
        record's CURRENT state (row["state"], before this transition) is
        'active': that is the one state with a live writer to protect. A
        parked record has no live writer by definition, so ANY session may
        resume it and becomes its owner in the same transition; that is the
        whole point of the founder's reversibility requirement (`off` today,
        `resume` tomorrow from a different session, must work). The OLD
        check compared session_id unconditionally for every to_state except
        'adopted', which wrongly refused that legitimate resume-tomorrow
        case: a parked record's session_id column still holds its last
        owner (park does not clear it), so resuming looked identical to
        stealing someone else's still-live work. Since 'parked'/'complete'
        can only be reached FROM 'active' (see _LEGAL_MOVES), the
        state=='active' condition is a no-op for those two moves (the guard
        keeps working exactly as before); it only changes 'active' itself
        (resume), which can never be reached FROM 'active' at all, so the
        guard no longer applies there.

        'adopted' (SOFT 10) remains the one exception among moves FROM an
        ACTIVE record: adopting a dead session's ACTIVE record is the
        legitimate cross-session path, and even that was originally too
        wide (SOFT E): adopting a record CURRENTLY ACTIVE under a
        different, live session is a takeover dressed as adoption, so it
        now requires adopt_from_live_session=True (CLI:
        --adopt-from-live-session) explicitly, and the displacement is
        named in the refusal and the transition's note. Adopting a PARKED
        record needs neither exception: a parked record already has no
        live writer to displace.

        GATE 6: resuming (or parking/completing) into a name another
        lifecycle now holds active violates the one-active-per-name unique
        index; caught here and turned into the same 'name-active' refusal
        claim() uses, rather than an unhandled sqlite3.IntegrityError."""
        if to_state not in _LEGAL_MOVES:
            raise ValueError("unknown target state %r" % (to_state,))
        if to_state == "complete" and not (evidence or "").strip():
            raise OwnershipRefused(
                "missing-evidence",
                "active -> complete requires non-empty evidence (the "
                "check_cmd result)",
                details={"lifecycle_uuid": lifecycle_uuid})
        allowed_from = _LEGAL_MOVES[to_state]
        with self._transaction():
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
            if to_state != "adopted":
                # BLOCKER 2 fix: the guard fires only when the record is
                # CURRENTLY active (a live writer exists to protect). A
                # parked (or adopted) record resuming to 'active' never has
                # row["state"] == "active" here (see the docstring), so this
                # never blocks a legitimate cross-session resume.
                if (_ownership_guard_applies(row["state"]) and row["session_id"]
                        and row["session_id"] != (session_id or "")):
                    raise OwnershipRefused(
                        "not-owner",
                        "lifecycle %s is ACTIVE under a different session; "
                        "only that session may move it to '%s' (adoption is "
                        "the exception for a dead session's record)"
                        % (lifecycle_uuid, to_state),
                        details={"lifecycle_uuid": lifecycle_uuid,
                                 "held_by_session_id": row["session_id"]})
            elif (row["state"] == "active" and row["session_id"]
                    and row["session_id"] != (session_id or "")):
                if not adopt_from_live_session:
                    raise OwnershipRefused(
                        "live-session-adopt-blocked",
                        "lifecycle %s is ACTIVE under a different, live "
                        "session %r; adopting it requires explicit "
                        "adopt_from_live_session=True (CLI: "
                        "--adopt-from-live-session), which displaces that "
                        "session" % (lifecycle_uuid, row["session_id"]),
                        details={"lifecycle_uuid": lifecycle_uuid,
                                 "displaced_session_id": row["session_id"]})
                displaced = row["session_id"]
                note = ("%s (displaced live session %r)" % (note, displaced)
                        if note else "displaced live session %r" % displaced)
            if to_state == "active":
                # GATE A (fix-round 3, 2026-07-26): resume must clear the
                # SAME admission gate claim() does, against the record's OWN
                # claims and lifetime, excluding itself from both checks
                # (it is not active yet, so this is defensive, not required
                # by the current schema, but keeps _admit's contract honest
                # regardless of call order). On conflict the record stays
                # parked: nothing here has mutated state yet.
                claim_rows = _exec(self,
                    "SELECT path FROM claims WHERE lifecycle_uuid=?",
                    (lifecycle_uuid,)).fetchall()
                norm_files = [r["path"] for r in claim_rows]
                self._admit(row["name"], row["lifetime"], norm_files,
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
            return self._record_by_uuid(lifecycle_uuid)

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
        with self._transaction():
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
        with self._transaction():
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
        with self._transaction():
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

    # -- autosave receipts --------------------------------------------------

    def write_autosave_receipt(self, worktree_id, session_id, snapshot_sha, tree_sha,
                                source_head, captured_count, excluded_count):
        """The ONE way an autosave receipt is written (the wiring item,
        prerelease fix round): tools/bm_autosave.py used to run hand-written
        BEGIN IMMEDIATE / INSERT / COMMIT directly on this Store's own
        connection, bypassing _exec (GATE 4's one place every statement in
        this module routes through, to tell a merely-busy database apart
        from a genuinely corrupt one). A receipt write now gets the exact
        same busy/corrupt handling every other mutation in this file gets,
        instead of a second, weaker copy of it living in bm_autosave.py."""
        with self._transaction():
            _exec(self,
                "INSERT INTO autosave_receipts (worktree_id, session_id, snapshot_sha, "
                "tree_sha, source_head, captured_count, excluded_count, created_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (worktree_id, session_id, snapshot_sha, tree_sha, source_head or "",
                 captured_count, excluded_count, now_iso()))

    def delete_autosave_receipts(self, worktree_id, snapshot_shas):
        """Delete every autosave receipt row for `worktree_id` whose
        snapshot_sha is in `snapshot_shas` (GATE F, prerelease fix round): a
        receipt must never outlive the ref that made it true. Reproduced:
        thirteen sessions, retention ten, and the pruned session's receipt
        row survived, so has_receipt kept reporting safety for work whose
        ref was gone. Called by bm_autosave.py's pruner in the SAME call
        that deletes the refs. Returns the number of rows deleted."""
        shas = [s for s in (snapshot_shas or []) if s]
        if not shas:
            return 0
        with self._transaction():
            placeholders = ",".join("?" for _ in shas)
            cur = _exec(self,
                "DELETE FROM autosave_receipts WHERE worktree_id=? AND snapshot_sha IN (%s)"
                % placeholders, tuple([worktree_id] + shas))
            return cur.rowcount

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

    def _digest_files_block(self, lifecycle_uuid, digest_row):
        """The '## Files' section's content for render_digest (GATE D,
        prerelease fix round): the ACTUAL claimed paths from the claims
        table, the one place a record's real fence lives, with any
        free-text files_note appended as a supplementary line. Before
        this, the section was built from files_note ALONE, so a record
        actively holding a live fence rendered "Files: (none)" the moment
        nobody had typed a files_note on a checkpoint: the one field a
        resuming session most needs to see. A separate, named method (not
        inlined in render_digest) so a reinjection test can monkeypatch
        exactly this symbol back to the old, notes-only shape and prove
        the calibration."""
        claimed = [r["path"] for r in _exec(self,
            "SELECT path FROM claims WHERE lifecycle_uuid=? ORDER BY path",
            (lifecycle_uuid,)).fetchall()]
        claimed_text = (", ".join(_sanitize_for_display(redact_text(p)) for p in claimed)
                        if claimed else "(none)")
        note_text = (_sanitize_for_display(redact_text(digest_row["files_note"]))
                     if digest_row and digest_row["files_note"] else "")
        block = claimed_text + ("\n" + note_text if note_text else "")
        return _truncate(block, _SECTION_BUDGETS["files_note"])

    def render_digest(self, lifecycle_uuid):
        """A bounded, human-readable handover for one lifecycle. Each
        section below is truncated to ITS OWN fixed budget, independently of
        every other section (see _SECTION_BUDGETS): V1's one shared 4000-char
        pool let a long run of decisions crowd out next_intent entirely
        (F12), exactly the field a resuming session needs first. Advisory
        for a missing record (renders a plain string instead of raising),
        but NOT advisory for redaction: every founder-typed field below
        (objective, next_intent, blockers, files_note, each decision's
        topic and text, and the record NAME) is passed through
        redact_text() before truncation, and raises RedactionUnavailable
        rather than render unredacted text if that cannot happen. The
        header carries the objective (SOFT E; the ratified spec's own
        budget list names it), not just name/state/lifetime. NAME is
        redacted unconditionally here, unlike render_state_md's per-field
        calls that can all be skipped on an all-empty-optional-fields
        record (GATE B): a record's name is never empty, so this call
        always runs, and a missing redactor is always caught."""
        row = _exec(self,
            "SELECT * FROM records WHERE lifecycle_uuid=?", (lifecycle_uuid,)).fetchone()
        if row is None:
            return "(no record with lifecycle_uuid %s)" % lifecycle_uuid
        objective_text = (_sanitize_for_display(redact_text(row["objective"]))
                          if row["objective"] else "(no objective)")
        name_text = _sanitize_for_display(redact_text(row["name"]))
        header = _truncate(
            "lifecycle %s: %s (%s, %s): %s"
            % (lifecycle_uuid[:8], name_text, row["state"], row["lifetime"], objective_text),
            _SECTION_BUDGETS["header"])
        digest_row = _exec(self,
            "SELECT * FROM digests WHERE lifecycle_uuid=? ORDER BY seq DESC LIMIT 1",
            (lifecycle_uuid,)).fetchone()
        next_intent = _truncate(
            _sanitize_for_display(redact_text(digest_row["next_intent"])) if digest_row else "",
            _SECTION_BUDGETS["next_intent"])
        blockers = _truncate(
            _sanitize_for_display(redact_text(digest_row["blockers"])) if digest_row else "",
            _SECTION_BUDGETS["blockers"])
        files_block = self._digest_files_block(lifecycle_uuid, digest_row)
        decisions = _exec(self,
            "SELECT * FROM decisions WHERE lifecycle_uuid=? ORDER BY seq DESC",
            (lifecycle_uuid,)).fetchall()
        new_lines, used, idx = [], 0, 0
        while idx < len(decisions):
            d = decisions[idx]
            line = "- [%s] %s" % (_sanitize_for_display(redact_text(d["topic"])),
                                   _sanitize_for_display(redact_text(d["text"])))
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
            # SOFT E (fix-round 7, 2026-07-26): the loop above broke on its
            # very FIRST iteration because the newest decision alone already
            # exceeds the budget, so new_lines is empty even though a
            # decision exists. The old behavior rendered a placeholder
            # saying so with ZERO actual decision content: the one field
            # this section exists to show. Truncate that single decision to
            # fit instead (the same _truncate() every other section uses,
            # so the marker is consistent), so a resuming session sees the
            # BEGINNING of the decision rather than nothing. It is excluded
            # from `older` below so it is not also shown a second time.
            first = decisions[0]
            first_line = "- [%s] %s" % (_sanitize_for_display(redact_text(first["topic"])),
                                         _sanitize_for_display(redact_text(first["text"])))
            newest_block = _truncate(first_line, _SECTION_BUDGETS["decisions_new"])
            older = decisions[1:]
        else:
            newest_block = "(none)"
        older_lines, older_used, older_shown = [], 0, 0
        for d in older:
            line = "- [%s] %s" % (_sanitize_for_display(redact_text(d["topic"])),
                                   _sanitize_for_display(redact_text(d["text"])))
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
            "## Files", files_block,
            "## Decisions", newest_block,
        ]
        if older:
            sections.append("### Older decisions")
            sections.append(older_block if older_block else "(none)")
        return "\n\n".join(sections) + "\n"

    def dump(self, raw=False):
        """Full JSON-serializable export of every table.

        GATE C: redacts BY DEFAULT-DENY. Every TEXT-typed column not in
        _DUMP_SAFE_COLUMNS (read live from the schema, see _text_columns)
        is redacted, whatever its name; an earlier enumerated allowlist of
        "known-sensitive" fields missed transitions.note, directives.text,
        records.evidence/check_cmd/owner precisely because nobody had
        listed them. dump is exactly what a founder pipes into a file, a
        paste, or an issue, so silent cleartext by default is the wrong
        direction. raw=True (CLI: --raw) is the explicit, named escape
        hatch for a human who really needs the unredacted sqlite contents
        (SECURITY.md documents the file itself as sensitive); never the
        default."""
        out = {}
        for t in _TABLES:
            rows = _exec(self, "SELECT * FROM %s" % t).fetchall()
            out[t] = [dict(r) for r in rows]
        if raw:
            return out
        for t in _TABLES:
            text_cols = _text_columns(self.conn, t)
            redact_cols = [c for c in text_cols if (t, c) not in _DUMP_SAFE_COLUMNS]
            if not redact_cols:
                continue
            for row_dict in out[t]:
                for col in redact_cols:
                    if row_dict.get(col):
                        row_dict[col] = redact_text(row_dict[col])
        return out


# ---------------------------------------------------------------------------
# Read-only access (fix-round 4, 2026-07-26): verify, dump, and dashboard
# are diagnostics. A diagnostic that can write is a diagnostic that can
# silently CREATE the very thing it claims to be checking, and then report
# health about the empty shell it just made. This class never creates a
# directory, a file, or a WAL sidecar, never runs schema DDL, and enforces
# read-only with PRAGMA query_only=ON on a PLAIN connection (GATE A,
# fix-round 6, 2026-07-26: no sqlite URI, ever; see _connect_read_only).
# ---------------------------------------------------------------------------

def _connect_read_only(path, timeout=5.0):
    """Open an EXISTING file read-only, without ever building a sqlite URI
    (GATE A, VERIFIED BY ORCHESTRATOR). A URI's query string only escapes
    '?' and '#'; sqlite itself percent-DECODES everything else in the
    filename, so a project path containing '%' (e.g. p%41) silently
    resolved to a COMPLETELY DIFFERENT file, and every read-only command
    opened another project's database, reported it healthy, and never saw
    the caller's own data. Escaping '%' too would still leave a
    pattern-language bug waiting for the next special character; deleting
    URIs removes the whole class. The caller has already proven the file
    exists (os.path.isfile), so a plain sqlite3.connect(path) is
    unambiguous: no escaping, no decoding, no URI grammar. Read-only is
    enforced at the SQL level with PRAGMA query_only=ON, the FIRST
    statement on the connection, which makes any write raise
    sqlite3.OperationalError rather than silently succeed."""
    conn = sqlite3.connect(path, timeout=timeout, isolation_level=None)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only = ON")
        conn.execute("PRAGMA busy_timeout=5000")
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        raise
    return conn


class ReadOnlyStore(object):
    """Opens an EXISTING store read-only. Refuses 'no-store' before ever
    calling sqlite3.connect if the file is not already there (fix-round 4):
    the old behavior let verify/dump/dashboard silently create an empty
    store and then report it healthy, seconds after a truncation had just
    quarantined the real one. A zero-length existing file is corruption
    here exactly as it is for the writable Store (GATE B, fix-round 3)."""

    def __init__(self, root):
        self.root = os.path.realpath(root)
        self.conn = None
        # GATE D (round 3) plus GATE B (round 5, 2026-07-26): the same
        # containment checks the writable Store applies, so a diagnostic
        # cannot be tricked by a symlinked .brothermode directory or a
        # symlinked store file/sidecar either.
        _refuse_if_symlink_escape(store_dir(self.root))
        self.path = store_path(self.root)
        if not os.path.isfile(self.path):
            raise OwnershipRefused(
                "no-store",
                "no store exists at %s; run `python3 tools/bm_store.py "
                "init` to create one" % self.path,
                details={"path": self.path})
        _refuse_if_symlink_escape(self.path)
        _refuse_if_symlink_escape(self.path + "-wal")
        _refuse_if_symlink_escape(self.path + "-shm")
        # SOFT D (fix-round 7, 2026-07-26): same containment intent as the
        # symlink checks above, for the threat a symlink check cannot see.
        _refuse_if_hardlinked(self.path)
        _refuse_if_hardlinked(self.path + "-wal")
        _refuse_if_hardlinked(self.path + "-shm")
        if os.path.getsize(self.path) == 0:
            self._quarantine_and_raise(
                ValueError("store file exists but is zero bytes (truncated, or never finished writing)"))
        try:
            conn = _connect_read_only(self.path)
            self.conn = conn
            # CRITICAL A (fix-round 8): the same structural verification the
            # writable Store applies on an existing file, so a diagnostic
            # command (dashboard, dump, verify) run against a store missing
            # a table quarantines and says so, rather than opening "clean"
            # and reporting whatever is left as healthy.
            self._verify_schema_or_raise()
            self.conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        except sqlite3.OperationalError as e:
            if not _is_transient_busy_error(e):
                self._quarantine_and_raise(e)
            if self.conn is not None:
                try:
                    self.conn.close()
                except Exception:
                    pass
                self.conn = None
            raise OwnershipRefused(
                "db-busy",
                "the store at %s is busy or locked (%s); wait a moment and "
                "retry." % (self.path, e))
        except sqlite3.DatabaseError as e:
            self._quarantine_and_raise(e)

    def _quarantine_and_raise(self, cause):
        # Reuses Store's implementation verbatim (it only touches
        # self.conn/self.path, both present here): one quarantine
        # mechanism, not two copies to keep in sync.
        return Store._quarantine_and_raise(self, cause)

    def _verify_schema_or_raise(self):
        # Reuses Store's implementation verbatim, same reasoning as above.
        return Store._verify_schema_or_raise(self)

    def dump(self, raw=False):
        # Reuses Store.dump() verbatim: it only calls _exec(self, ...) over
        # _TABLES, which works identically against a read-only connection.
        return Store.dump(self, raw=raw)

    def close(self):
        if self.conn is not None:
            try:
                self.conn.close()
            finally:
                self.conn = None


def _find_quarantine_dirs(root):
    """Every quarantine directory currently sitting beside the store,
    newest first (the timestamp-plus-uuid naming sorts lexicographically).

    GATE B: NEVER glob. glob.glob interpolates the root into a pattern
    string, so a project path containing [ ] * or ? (e.g. a directory
    literally named 'p[1]') is read as GLOB SYNTAX rather than a literal
    path, and an outstanding quarantine silently stops matching. Deletes
    the pattern language for this lookup entirely (same shape as GATE A):
    os.listdir the containing directory literally and match the
    quarantine marker by a plain string prefix."""
    store_dirname_path = store_dir(root)
    prefix = STORE_FILENAME + ".quarantine-"
    try:
        entries = os.listdir(store_dirname_path)
    except OSError:
        return []
    hits = [os.path.join(store_dirname_path, name) for name in entries
            if name.startswith(prefix)
            and os.path.isdir(os.path.join(store_dirname_path, name))]
    return sorted(hits, reverse=True)


def _is_quarantine_acknowledged(qdir):
    return os.path.isfile(os.path.join(qdir, "ACKNOWLEDGED"))


def _unacknowledged_quarantine_dirs(root):
    return [d for d in _find_quarantine_dirs(root) if not _is_quarantine_acknowledged(d)]


def _quarantine_record_count(qdir):
    """Best-effort record count from a quarantined file, or None when that
    cannot be determined. It is quarantined because it could not be read
    normally, so failing here is the expected common case, not a bug."""
    qpath = os.path.join(qdir, STORE_FILENAME)
    if not os.path.isfile(qpath) or os.path.getsize(qpath) == 0:
        return None
    try:
        conn = _connect_read_only(qpath, timeout=1.0)
        try:
            row = conn.execute("SELECT COUNT(*) FROM records").fetchone()
            return row[0] if row else None
        finally:
            conn.close()
    except Exception:
        return None


def _quarantine_summary(qdir):
    count = _quarantine_record_count(qdir)
    return "%s (%s)" % (qdir, "%d record(s) recoverable" % count if count is not None
                         else "record count unknown")


def _acknowledge_quarantine(qdir):
    """Mark one quarantine directory acknowledged WITHOUT deleting it
    (fix-round 4): it is the founder's one chance to recover lost records,
    so nothing here ever removes it, only records that someone looked."""
    try:
        with open(os.path.join(qdir, "ACKNOWLEDGED"), "w", encoding="utf-8") as f:
            f.write("acknowledged %s\n" % now_iso())
    except OSError as e:
        _warn("bm_store: warning: could not write acknowledgement marker in "
              "%s (%s)" % (qdir, e))


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

def _load_atomic_write():
    try:
        import importlib.util
        here = os.path.dirname(os.path.abspath(__file__))
        spec = importlib.util.spec_from_file_location(
            "bm_telemetry_for_store_atomic_write", os.path.join(here, "bm_telemetry.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "atomic_write"):
            return mod.atomic_write, None
        return None, "bm_telemetry.py has no atomic_write()"
    except Exception as e:
        return None, repr(e)


_ATOMIC_WRITE, _ATOMIC_WRITE_LOAD_ERROR = _load_atomic_write()


def _atomic_write_text(path, text):
    """Delegates to bm_telemetry.atomic_write (prerelease fix round: this
    function used to be its own, weaker duplicate of the same idea, with
    no directory fsync and a cleanup path that only caught OSError).
    bm_telemetry.py is the one owner of crash-atomic file replacement in
    this project now; loaded dynamically by path (the same pattern
    _load_redact already uses above), since bm_store.py keeps no static
    import on bm_telemetry.py. Raises OSError, same as before, on a
    genuine write failure, or when bm_telemetry.py itself could not be
    loaded: every existing caller already handles or propagates that."""
    if _ATOMIC_WRITE is None:
        raise OSError(
            "bm_telemetry.atomic_write is unavailable (%s); cannot write %s"
            % (_ATOMIC_WRITE_LOAD_ERROR, path))
    _ATOMIC_WRITE(path, text)


def _redacted_view_text(raw):
    """redact_text(), then _neutralize_markers(), then _sanitize_for_display():
    the ONE pipeline every founder-typed field goes through before entering
    a generated view (GATE 8, fix-round 2026-07-26; SOFT D/E, fix-round 5).
    Order matters: redaction runs on the real content first; marker and
    control-character neutralization run last, on exactly what is about to
    be embedded, so neither a fake marker nor a forged newline/ANSI escape
    can hide inside a secret pattern's replacement text either."""
    return _sanitize_for_display(_neutralize_markers(redact_text(raw)))


def render_state_md(root):
    """The generated human view of every record. Advisory for missing data
    (never raises for that), but every founder-typed field rendered below
    (objective, tier, session id, claim paths, next intent) is passed
    through _redacted_view_text() first (GATE 8a: tier and claim paths used
    to reach
    STATE.md unredacted), and raises RedactionUnavailable rather than emit
    unredacted text if that cannot happen. The literal BEGIN/END marker
    strings are neutralized inside that same pipeline (GATE 8b), so founder
    text can never masquerade as a real marker and corrupt the generated
    block's boundary. A store that cannot even be opened propagates
    StoreCorrupt or OwnershipRefused('no-store'); a later-page corruption
    during rendering is caught by _exec (GATE 4). Read-only: the dashboard
    is a diagnostic and must never create the store it is displaying."""
    store = ReadOnlyStore(root)
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
                # BLOCKER 2 fix (release-blockers spec, 2026-07-26): the
                # owning session id used to appear NOWHERE in this view (or
                # in any thread file), so a human could not tell who held a
                # record without dumping the database. session_id is
                # founder-suppliable (--session) like tier, so it goes
                # through the same redactor rather than being assumed safe.
                session_text = (_redacted_view_text(r["session_id"])
                                if r["session_id"] else "no session")
                # Round 7 (2026-07-26): the record NAME is founder-typed text
                # (valid_name only rejects reserved characters and
                # whitespace; a name shaped like a real secret passes it
                # cleanly), redacted here like every other field. Unlike
                # tier/objective/files/next_intent below, name is NOT NULL
                # and never empty, so this call is never conditional on
                # emptiness: a missing redactor is always caught the moment
                # this function renders anything at all, closing the GATE B
                # hole where an all-empty-optional-fields record produced
                # zero redact_text() calls and zero warnings. The lifecycle
                # uuid prefix printed right beside it is the stable way to
                # refer to a record whose name is now redacted.
                #
                # The wiring item (prerelease fix round): this line used to
                # print only an eight-character uuid PREFIX and no version,
                # while every mutating command (park/resume/complete/adopt/
                # checkpoint/decide) needs the FULL lifecycle_uuid and the
                # CURRENT version to act at all. Printing both means a human
                # reading STATE.md can act on what they read without a
                # separate `dump` round trip.
                lines.append("- %s (%s, version %s, %s) [%s] owner-session: %s"
                             % (_redacted_view_text(r["name"]), r["lifecycle_uuid"],
                                r["version"], r["lifetime"], tier_text, session_text))
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
    file that does not exist yet gets just the generated block.

    GATE A (VERIFIED BY ORCHESTRATOR: hand-edit a rendered STATE.md the way
    a human would, deleting the END line and adding their own notes, then
    render twice): the old naive containment test ("BEGIN in existing and
    END in existing") let render 1 append a fresh block after the damaged
    file, then let render 2's splice use the FIRST BEGIN and the ONLY END,
    deleting everything between them, notes included, at exit 0 with no
    warning. The marker-injection guard only ever neutralized markers
    arriving FROM THE STORE (GATE 8b); it trusted markers already IN THE
    FILE. Fixed by failing closed: the existing file's marker COUNT must be
    exactly (0, 0) or (1, 1), or this refuses ('view-markers-damaged')
    rather than guess which BEGIN belongs to which END. Whenever the file
    already has content and passes that check, it is saved first as
    STATE.md.bak-<UTC stamp> (reported on stderr): a generated file may
    overwrite its own block, but may never irrecoverably lose what a human
    wrote.

    GATE B: the final write routes through _write_generated_file (THE FILE
    FUNNEL), never _atomic_write_text directly, so a missing redactor
    refuses the ENTIRE write instead of silently writing raw founder text
    (the record NAME) at exit 0 with no warning. See docs/superpowers/specs/
    2026-07-26-phase1-fix-round-7.md for the full incident writeups."""
    generated = render_state_md(root)
    path = os.path.join(root, "STATE.md")
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            existing = f.read()
    except OSError:
        existing = ""
    begin_count = existing.count(_STATE_BEGIN)
    end_count = existing.count(_STATE_END)
    if (begin_count, end_count) not in ((0, 0), (1, 1)):
        raise OwnershipRefused(
            "view-markers-damaged",
            "%s has a damaged generated-view marker pair (found %d BEGIN "
            "marker(s) and %d END marker(s); a healthy file has exactly "
            "one of each, or neither). Refusing to write it: a partial or "
            "duplicated marker pair cannot be told apart from human prose "
            "that must be preserved, and guessing has destroyed a real "
            "handover before. Repair by hand so the file has exactly one "
            "'%s' line followed by exactly one '%s' line, or remove both "
            "and let this command add a fresh block, then re-run it. "
            "Nothing was changed." % (path, begin_count, end_count, _STATE_BEGIN, _STATE_END))
    if existing:
        # GATE A: back up whatever is already there before this write can
        # touch it, whether the next step is a splice or an append. The
        # stamp carries microsecond precision (like the quarantine
        # directory name, GATE 5) plus a short random suffix on collision,
        # so two renders in the same microsecond still each get their own
        # backup rather than one silently overwriting the other.
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        backup_path = path + ".bak-" + stamp
        if os.path.lexists(backup_path):
            backup_path = backup_path + "-" + uuid.uuid4().hex[:8]
        _atomic_write_text(backup_path, existing)
        _warn("bm_store: saved the previous STATE.md as %s before rewriting it" % backup_path)
    if begin_count == 1:
        pre, rest = existing.split(_STATE_BEGIN, 1)
        _mid, post = rest.split(_STATE_END, 1)
        new_text = pre + generated + post
    elif existing:
        sep = "" if existing.endswith("\n\n") else ("\n" if existing.endswith("\n") else "\n\n")
        new_text = existing + sep + generated
    else:
        new_text = generated
    return _write_generated_file(path, new_text)


def _refresh_state_view(root):
    """Regenerate STATE.md after a mutation (the wiring item, prerelease
    fix round): write_state_view had ZERO callers anywhere in this
    module's own CLI, so the human-readable status file was never
    regenerated after `init`. Called from every mutating command and from
    `dashboard`.

    Advisory, the same principle GATE C states for redaction specifically,
    generalized here to every reason a view refresh can refuse: the
    mutation THIS CALL follows has already committed by the time this
    runs, so a view-refresh failure must never be reported as though the
    mutation itself failed. Failures are warned, never raised past this
    point; a genuinely corrupt store is the one exception, since that is
    real damage a founder must see immediately, not a cosmetic view gap."""
    try:
        write_state_view(root)
    except RedactionUnavailable:
        _warn_no_redact_once()
    except OwnershipRefused as e:
        _warn("bm_store: could not refresh the generated STATE.md view after "
              "this command (%s: %s); the command's own result above is "
              "still accurate. Fix the file by hand, then re-run any "
              "command to regenerate it." % (e.reason, e))


def _verify_view_reflects_active_records(store, root):
    """The GATE B check (prerelease fix round): every ACTIVE record's
    lifecycle uuid must appear inside STATE.md's ACTUAL generated block ON
    DISK, never a fresh render computed from the SAME rows this function
    just read. The old check called render_state_md(root) and compared the
    live rows against a document built from those SAME live rows in the
    SAME call: that comparison can never disagree with itself, which is
    exactly why it caught nothing. Executed: deleting STATE.md entirely,
    and overwriting it with garbage, both left the old check reporting
    healthy. An absent file, or a file with a damaged or missing marker
    pair, is a problem here, not a silent skip. A separate, named function
    (not inlined in verify()) so a reinjection test can monkeypatch
    exactly this symbol back to the old, tautological shape and prove the
    calibration.

    An absent or unreadable STATE.md is a problem ONLY when there is at
    least one ACTIVE record it should be showing: a pristine, just-`init`ed
    project with nothing claimed yet is genuinely healthy with no STATE.md
    at all, and reporting a problem there would be crying wolf on the one
    state this project's own SOFT 11 finding calls "trivially healthy" on
    purpose."""
    active_rows = _exec(store,
        "SELECT lifecycle_uuid, name FROM records WHERE state='active'").fetchall()
    problems = []
    state_path = os.path.join(root, "STATE.md")
    try:
        with open(state_path, encoding="utf-8", errors="replace") as f:
            on_disk = f.read()
    except OSError:
        if active_rows:
            # GATE 4 fix (release-blockers spec, 2026-07-26): this project
            # is installed once and used FROM other projects' roots (the
            # `root` this problem is about is very often NOT this file's
            # own directory), so a hardcoded relative "tools/bm_store.py"
            # named a path that does not exist at that root at all. The
            # remedy now names THIS file's own absolute path, the same
            # os.path.abspath(__file__) shape bm_autosave.py's recover
            # nudge already uses, so it is resolvable regardless of the
            # caller's cwd or which project's root triggered the problem.
            problems.append(
                "STATE.md does not exist at %s; run `python3 %s "
                "dashboard` (or any mutating command) to generate it"
                % (state_path, os.path.abspath(__file__)))
        return problems
    begin_idx = on_disk.find(_STATE_BEGIN)
    end_idx = on_disk.find(_STATE_END)
    has_block = begin_idx != -1 and end_idx != -1 and end_idx > begin_idx
    if on_disk and not has_block:
        if active_rows:
            problems.append(
                "STATE.md at %s has no readable generated-view block (missing "
                "or out-of-order BEGIN/END markers); it is stale or was "
                "hand-edited past recognition" % state_path)
        return problems
    generated_block = on_disk[begin_idx:end_idx] if has_block else ""
    # IMPORTANT (fix-round 8): checks the lifecycle_uuid PREFIX, never the
    # raw NAME: a short name (or one that also occurs inside other
    # rendered text) would satisfy a substring test vacuously, and a
    # redacted name (round 7: a name shaped like a real secret) would
    # never satisfy it even when the record legitimately IS in the view.
    # The lifecycle_uuid prefix is never redacted and is printed beside
    # every record, so it is both non-vacuous and correct regardless of
    # name redaction.
    for r in active_rows:
        if r["lifecycle_uuid"][:8] not in generated_block:
            problems.append(
                "active record %r (%s) does not appear in the generated STATE.md view"
                % (r["name"], r["lifecycle_uuid"][:8]))
    return problems


def verify(root):
    """Machine invariants over the whole store. Empty list means healthy.
    This replaces V1's one-directional check (fixes F15): the store IS both
    directions, so verify checks the same union-of-claims invariant claim()
    enforces at write time, plus the generated view and transition history,
    rather than trusting that nothing has drifted since the last write.

    Read-only: opens via ReadOnlyStore, never creating the thing it is
    diagnosing. The health vocabulary is reserved: an unacknowledged
    quarantine is reported as a PROBLEM here (not silently skipped),
    because "healthy" may only be printed when a store was actually
    opened, read, and found consistent."""
    unacknowledged = _unacknowledged_quarantine_dirs(root)
    problems = [
        "unacknowledged quarantine directory %s; recover what you need, "
        "then run `python3 tools/bm_store.py init --acknowledge-quarantine`"
        % _quarantine_summary(d) for d in unacknowledged]
    store = ReadOnlyStore(root)
    try:
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
        problems.extend(_verify_view_reflects_active_records(store, root))
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

# ---------------------------------------------------------------------------
# THE OUTPUT FUNNEL. Five separate findings in one round shared one root
# cause: a founder-typed string reached SOME exit (verify's problems, the
# path-escape message, the record NAME, the --session echo) without going
# through redaction, because redaction was invoked per call site, per
# field, and a missed field is invisible until someone reproduces it. THE
# FIX IS STRUCTURAL: every byte this module sends to stdout, stderr, or a
# generated file passes through exactly one of the named functions below;
# none can be bypassed with a bare print()/sys.stdout.write()/
# sys.stderr.write() or a raw file write (a structural test greps for it).
#
# _out/_warn redact AND sanitize UNCONDITIONALLY, no opt-out, for ORDINARY
# SINGLE-LINE messages: a founder-controlled value like --session never
# goes through valid_name's ASCII-printable check, so a stray control
# character reaching a real terminal is a live risk _sanitize_for_display
# closes. It must NEVER run blanket over an already-ASSEMBLED multi-line
# document (the dashboard, dump's JSON): its job is defusing a SINGLE
# VALUE's control characters before embedding, not judging a document's
# OWN newlines/indentation, which escaping corrupts instead of protecting
# (reproduced once: JSON went invalid, the dashboard became one unreadable
# line). Content that is already protected per field, or has zero founder
# influence, or already had its redact decision made upstream, uses one of
# the two narrower exceptions instead: _out_prerendered (redact only, still
# fails closed: the dashboard) and _out_unprotected (neither: static help
# text, and dump's already-decided JSON payload in both modes).
# ---------------------------------------------------------------------------

def _protect_text(t):
    """The value-level half of the funnel: redact_text() then
    _sanitize_for_display(), unconditionally, on ANY string before it can
    reach a stream or a file. Called on the FULLY ASSEMBLED text at each
    funnel boundary (not just on fields someone remembered were
    "founder-typed"), so a record's NAME (round 7: was never redacted
    anywhere, and valid_name happily accepts AKIAIOSFODNN7EXAMPLE or
    password=hunter2 as a name) or any future field is covered automatically.
    Raises RedactionUnavailable when the redactor cannot be loaded; never
    returns unredacted text."""
    return _sanitize_for_display(redact_text(t or ""))


def _raw_write(stream, text):
    """The lowest-level primitive: write text to stream, encoding-safe
    (GATE 9, fix-round 2026-07-26: UnicodeEncodeError's only ancestor besides
    UnicodeError is ValueError, so an unencodable character used to reach
    main()'s ValueError handler and misreport an already-committed success
    as 'bad-input'). Used ONLY by the three funnel functions; never called
    directly by a command."""
    try:
        stream.write(text)
    except UnicodeEncodeError:
        enc = getattr(stream, "encoding", None) or "ascii"
        try:
            stream.buffer.write(text.encode(enc, errors="backslashreplace"))
        except Exception:
            stream.write(text.encode("ascii", errors="backslashreplace").decode("ascii"))
    try:
        stream.flush()
    except Exception:
        pass


def _out(s, end="\n"):
    """THE STDOUT FUNNEL. Every byte reaching stdout is redacted and
    sanitized first, unconditionally: if the redactor cannot be loaded,
    this REFUSES (RedactionUnavailable propagates to main(), exit 2) rather
    than print anything, even a purely structural message, because "call
    sites lose the ability to opt out" is the whole point (GATE B: the old
    per-field design let the missing-redactor check simply never fire when
    the field that would have triggered it happened to be empty)."""
    _raw_write(sys.stdout, _protect_text(s) + end)


def _out_prerendered(s, end=""):
    """For MULTI-LINE content already protected FIELD BY FIELD before
    assembly (render_state_md's dashboard output: every value it embeds
    already went through _redacted_view_text, including the record name as
    of this round), where the document's own newlines and indentation are
    this module's structure, not founder text. Runs redact_text() as a
    defense-in-depth safety net across the whole assembled document (a
    stateless pattern scan for secret SHAPES; it does not care about
    newlines the way _sanitize_for_display does, so it cannot corrupt this
    document's structure the way blanket sanitizing would), and still fails
    CLOSED exactly like _out: if the redactor cannot be loaded, this raises
    RedactionUnavailable and prints nothing, rather than let a generated
    view escape the one round-6/7 promise it exists to keep."""
    _raw_write(sys.stdout, redact_text(s or "") + end)


def _out_unprotected(s, end="\n"):
    """The narrow, named exception to the funnel, for two cases where
    running redact_text() or _sanitize_for_display() would be WRONG, not
    merely unnecessary: (1) main()'s usage/help text (this module's own
    __doc__ and command list) has zero founder influence by construction,
    so there is nothing to redact and requiring a working redactor just to
    show --help would be wrong; (2) cmd_dump's JSON payload in both modes,
    where store.dump() is ITSELF the redaction boundary (default-deny per
    column, or the documented, warned raw=True escape hatch), so redacting
    the already-decided, SERIALIZED text again is redundant, and
    sanitizing it is destructive: JSON's own structural indentation is not
    founder text, and blanket-sanitizing corrupts it (and silently
    re-redacts --raw's own secret, defeating the flag).

    Restricted to exactly these two callers; a structural test enumerates
    and counts them, so a new call site is a deliberate, reviewed choice."""
    _raw_write(sys.stdout, s + end)


def _warn(s, end="\n"):
    """THE STDERR FUNNEL (advisory surfaces fail OPEN, per the project's two
    failure policies: a warning must never block work). Redacts and
    sanitizes like _out(), but if the redactor is unavailable, degrades to
    the fixed, hardcoded _warn_no_redact_once() notice instead of raising:
    the ORIGINAL text is discarded either way, so a warning can never leak
    what redaction would have caught, but a broken redactor never silences
    every warning in the program either."""
    try:
        safe = _protect_text(s)
    except RedactionUnavailable:
        _warn_no_redact_once()
        return
    _raw_write(sys.stderr, safe + end)


def _write_generated_file(path, text):
    """THE FILE FUNNEL (see THE OUTPUT FUNNEL note below): the only path
    allowed to write a generated file (currently STATE.md, via
    write_state_view). Runs redact_text() over the whole text unconditionally
    before _atomic_write_text ever sees it; if the redactor is unavailable
    this raises RedactionUnavailable and nothing is written.

    Deliberately skips _sanitize_for_display (unlike _protect_text, for
    single-line messages): the text is a multi-line DOCUMENT whose own
    newlines, and the real BEGIN/END markers, are structure this module is
    writing on purpose, not founder-typed injection; sanitizing the whole
    document a second time would escape them into literal \\x0a text and
    corrupt the file. Every founder-typed VALUE was already sanitized per
    field before assembly (_redacted_view_text); redact_text() here is a
    defense-in-depth secret-pattern scan that does not touch newlines, so it
    is safe even over human prose preserved outside the markers.

    Returns the protected text actually written (never the unprotected
    input), so a caller holding the return value never disagrees with disk."""
    protected = redact_text(text or "")
    _atomic_write_text(path, protected)
    return protected


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


def _reject_unknown_flags(cmd_name, kv, allowed):
    """GATE 5 (release-blockers spec, 2026-07-26): _parse_kv stores ANY
    "--flag" shape without complaint, and every command below used to read
    back only the keys it recognized, silently dropping the rest. Reported
    success at exit 0 either way: a typo'd flag (e.g. --note where the
    command wants --files-note) was simply ignored, storing nothing for it.
    A caller must be told the exact command failed, not learn it later from
    a missing fence or a missing digest, so this refuses hard: named
    flag(s), exit 2, and (because this runs before the command's own store
    call) nothing is ever attempted."""
    unknown = sorted(set(kv) - set(allowed))
    if unknown:
        _out("%s: unrecognized flag(s) %s (recognized: %s)"
             % (cmd_name, ", ".join("--" + u for u in unknown),
                ", ".join("--" + a for a in sorted(allowed))))
        sys.exit(2)


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
    kv = _parse_kv(argv)
    _reject_unknown_flags("init", kv, ("acknowledge-quarantine",))
    acknowledge = "acknowledge-quarantine" in kv
    root, source = resolve_root()
    if root is None:
        # init is the one command allowed to proceed with no-root: its whole
        # job is to CREATE the marker. Falling back to cwd is the only
        # sensible choice when nothing else anchors a project here.
        root = os.path.realpath(os.getcwd())
        source = "cwd (nothing found to anchor on; this becomes the new root)"
    unacknowledged = _unacknowledged_quarantine_dirs(root)
    if unacknowledged and not acknowledge:
        # Fix-round 4 (2026-07-26): a quarantine is remembered until an
        # explicit act acknowledges it, mirroring the ratified autosave
        # receipt rule. init must not just barrel past a prior data loss.
        raise OwnershipRefused(
            "unacknowledged-quarantine",
            "%d quarantine director%s not been acknowledged: %s. Recover "
            "what you need, then run `python3 tools/bm_store.py init "
            "--acknowledge-quarantine` to continue (the directory is never "
            "deleted by this)."
            % (len(unacknowledged), "y has" if len(unacknowledged) == 1 else "ies have",
               "; ".join(_quarantine_summary(d) for d in unacknowledged)),
            details={"quarantine_dirs": unacknowledged})
    init_project(root)
    if acknowledge:
        for d in unacknowledged:
            _acknowledge_quarantine(d)
    _out("bm_store: initialized %s (root resolved via %s)" % (store_path(root), source))


def cmd_claim(argv):
    if not argv:
        _out("usage: claim <name> --lifetime persistent|ephemeral --objective TEXT "
             "[--files PATH ...] [--release-files] [--owner X] [--session SID] "
             "[--tier T] [--check CMD]")
        _out("  --files with at least one path REPLACES the fence (on a reclaim).")
        _out("  --release-files explicitly releases every file (on a reclaim); "
             "omitting --files entirely LEAVES the existing fence untouched, "
             "it can never be dropped by accident.")
        _out("  On a reclaim, omitting --objective/--tier/--check/--owner LEAVES "
             "each untouched; typing the flag, even with an empty value, sets it.")
        sys.exit(2)
    name = argv[0]
    kv = _parse_kv(argv[1:])
    _reject_unknown_flags("claim", kv,
        ("lifetime", "objective", "files", "release-files", "owner",
         "session", "tier", "check"))
    root, _source = require_root()
    lifetime = " ".join(kv.get("lifetime", [])) or "ephemeral"
    # GATE D (fix-round 6, 2026-07-26): the SAME None-vs-empty rule GATE A
    # (round 5) applied only to --files now applies to every updatable
    # scalar flag. Omitting a flag entirely means None (not supplied,
    # leaves an existing value untouched on a reclaim); typing the flag AT
    # ALL, even with an empty join result, is the caller's deliberate
    # value, including a deliberate clear. Before this, cmd_claim always
    # joined an absent flag to "", indistinguishable from "clear it", so a
    # reclaim with only --tier silently erased the objective.
    objective = " ".join(kv["objective"]) if "objective" in kv else None
    # GATE A (fix-round 5, 2026-07-26): a bare '--files' with no paths and no
    # '--release-files' is treated as NOT SUPPLIED (files=None, preserves an
    # existing fence on reclaim), not as an accidental release. Only a
    # non-empty '--files a.py ...' or the explicit '--release-files' counts
    # as "the caller really means this".
    explicit_files = kv.get("files", [])
    if "release-files" in kv:
        files = []
    elif explicit_files:
        files = explicit_files
    else:
        files = None
    owner = " ".join(kv["owner"]) if "owner" in kv else None
    # GATE 3: an omitted --session gets a fresh per-process id, never "".
    session_id = " ".join(kv.get("session", [])) or _default_cli_session_id()
    tier = " ".join(kv["tier"]) if "tier" in kv else None
    check_cmd = " ".join(kv["check"]) if "check" in kv else None
    # Fix-round 4: only `init` creates a store; claim refuses 'no-store'.
    store = Store(root, create=False)
    try:
        rec = store.claim(name, lifetime, objective, files, owner=owner,
                           session_id=session_id, tier=tier, check_cmd=check_cmd,
                           cwd=os.getcwd())
    finally:
        store.close()
    _refresh_state_view(root)
    _out("claimed '%s' as lifecycle %s (version %s, session %s)"
         % (rec.name, rec.lifecycle_uuid, rec.version, rec.session_id))


def _cmd_transition(argv, to_state, usage):
    if not argv:
        _out("usage: %s" % usage)
        sys.exit(2)
    lifecycle_uuid = argv[0]
    kv = _parse_kv(argv[1:])
    _reject_unknown_flags("transition", kv,
        ("version", "session", "note", "evidence", "adopt-from-live-session"))
    ver_raw = kv.get("version")
    if not ver_raw:
        _out("usage: %s" % usage)
        _out("  --version is required (optimistic concurrency: pass the version you last saw)")
        sys.exit(2)
    expected_version = int(ver_raw[0])
    session_id = " ".join(kv.get("session", []))
    note = " ".join(kv.get("note", []))
    evidence = " ".join(kv.get("evidence", []))
    # SOFT E (fix-round 6, 2026-07-26): required only to adopt a record that
    # is currently active under a DIFFERENT, live session; harmless to pass
    # or omit for park/resume/complete, which never check it.
    adopt_from_live_session = "adopt-from-live-session" in kv
    root, _source = require_root()
    store = Store(root, create=False)
    try:
        before = store.get(lifecycle_uuid)
        rec = store.transition(lifecycle_uuid, expected_version, to_state,
                                session_id=session_id, note=note, evidence=evidence,
                                adopt_from_live_session=adopt_from_live_session)
    finally:
        store.close()
    _refresh_state_view(root)
    if (to_state == "adopted" and before is not None and before.state == "active"
            and before.session_id and before.session_id != session_id):
        _out("%s: displaced live session %r from '%s' (lifecycle %s)"
             % (to_state, before.session_id, rec.name, rec.lifecycle_uuid))
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
    _cmd_transition(argv, "adopted",
                     "adopt <lifecycle_uuid> --version N [--session SID] [--note TEXT] "
                     "[--adopt-from-live-session]  (required to adopt a record that is "
                     "currently active under a different, live session)")


def cmd_checkpoint(argv):
    if not argv:
        _out("usage: checkpoint <lifecycle_uuid> --version N --next TEXT "
             "[--blockers TEXT] [--files-note TEXT] [--body TEXT]")
        sys.exit(2)
    lifecycle_uuid = argv[0]
    kv = _parse_kv(argv[1:])
    _reject_unknown_flags("checkpoint", kv,
        ("version", "next", "blockers", "files-note", "body"))
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
    store = Store(root, create=False)
    try:
        seq = store.checkpoint(lifecycle_uuid, expected_version, next_intent,
                                blockers=blockers, files_note=files_note, body=body)
    finally:
        store.close()
    _refresh_state_view(root)
    # IMPORTANT (fix-round 8): checkpoint bumps the record's version but
    # never returned or printed it, so the founder's very next command
    # (which needs --version) failed stale-identity against a version it
    # was never told about. expected_version + 1 is the new version: the
    # compare-and-swap this just passed only ever increments by exactly 1,
    # never skips or double-increments, so this is exact, not a guess.
    _out("checkpoint %d recorded for %s (version %s)" % (seq, lifecycle_uuid, expected_version + 1))


def cmd_decide(argv):
    if not argv:
        _out("usage: decide <lifecycle_uuid> --version N --topic T --text TEXT")
        sys.exit(2)
    lifecycle_uuid = argv[0]
    kv = _parse_kv(argv[1:])
    _reject_unknown_flags("decide", kv, ("version", "topic", "text"))
    ver_raw = kv.get("version")
    if not ver_raw:
        _out("decide: --version is required (optimistic concurrency)")
        sys.exit(2)
    expected_version = int(ver_raw[0])
    topic = " ".join(kv.get("topic", []))
    text = " ".join(kv.get("text", []))
    root, _source = require_root()
    store = Store(root, create=False)
    try:
        seq = store.decide(lifecycle_uuid, expected_version, topic, text)
    finally:
        store.close()
    _refresh_state_view(root)
    # IMPORTANT (fix-round 8): same reasoning as cmd_checkpoint above.
    _out("decision %d recorded for %s (version %s)" % (seq, lifecycle_uuid, expected_version + 1))


def cmd_dashboard(argv):
    root, _source = require_root()
    # _out_prerendered, not _out (fix-round 7): render_state_md's own
    # newlines are this document's structure, not founder text; blanket
    # _sanitize_for_display would escape every one of them into literal
    # \x0a text (reproduced during this round). See THE OUTPUT FUNNEL note.
    _out_prerendered(render_state_md(root), end="")
    _refresh_state_view(root)


def cmd_dump(argv):
    kv = _parse_kv(argv)
    _reject_unknown_flags("dump", kv, ("raw",))
    raw = "raw" in kv
    root, _source = require_root()
    store = ReadOnlyStore(root)  # fix-round 4: dump is a diagnostic, never creates
    try:
        if raw:
            # GATE C (fix-round 5, updated fix-round 6 for default-deny):
            # --raw prints every non-structural text field UNREDACTED. Named
            # and warned at the point of use, never the default. SOFT F
            # (fix-round 6): to stderr, so `dump --raw > file.json` is still
            # valid JSON.
            _warn("bm_store: --raw: printing every non-structural text "
                  "field UNREDACTED (cleartext).")
        data = store.dump(raw=raw)
    finally:
        store.close()
    # _out_unprotected, not _out (fix-round 7): store.dump() already made
    # the redact/no-redact call on the DATA (default-deny per column, or
    # the deliberate --raw skip warned above); re-running _out()'s blanket
    # protect on the SERIALIZED JSON both redoes that decision and corrupts
    # the JSON's own structural indentation, and for --raw it silently
    # re-redacted the very secret the flag exists to show (reproduced
    # during this round). See THE OUTPUT FUNNEL note.
    _out_unprotected(json.dumps(data, indent=2, sort_keys=True))


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


def _warn_if_unacknowledged_quarantine(root):
    """Printed before EVERY command (fix-round 4, 2026-07-26): a founder who
    runs any command, not just verify, is told a quarantine happened and is
    still unacknowledged. Best-effort: root resolution failing here is not
    this function's problem, the command itself will report it."""
    if root is None:
        return
    try:
        unacknowledged = _unacknowledged_quarantine_dirs(root)
    except Exception:
        return
    if not unacknowledged:
        return
    # SOFT F (fix-round 6, 2026-07-26): to stderr. This prints before EVERY
    # command, including dump; a warning on stdout made `dump > file.json`
    # invalid JSON while a quarantine was outstanding.
    _warn("bm_store: WARNING: %d unacknowledged quarantine director%s: %s. "
          "Run `python3 tools/bm_store.py init --acknowledge-quarantine` "
          "after recovering what you need."
          % (len(unacknowledged), "y" if len(unacknowledged) == 1 else "ies",
             "; ".join(_quarantine_summary(d) for d in unacknowledged)))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    cmd = argv[0] if argv else ""
    rest = argv[1:]
    fn = _COMMANDS.get(cmd)
    if fn is None:
        # _out_unprotected, not _out (fix-round 7): this module's own
        # docstring and command list have zero founder influence, ever, so
        # there is nothing to redact; forcing bm_telemetry to load just to
        # print --help would make an unrelated module's bug block a founder
        # from seeing usage text, and _out()'s sanitize pass would mangle
        # this multi-line docstring's own newlines into literal \x0a text
        # (reproduced during this round). See THE OUTPUT FUNNEL note.
        _out_unprotected((__doc__ or "").strip())
        _out_unprotected("\ncommands: %s" % ", ".join(sorted(_COMMANDS)))
        sys.exit(0 if cmd == "" else 2)
    root_for_warning, _src = resolve_root()
    _warn_if_unacknowledged_quarantine(root_for_warning)
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
        # Routed through the stderr funnel (fix-round 7): _warn/_raw_write
        # already carry their own layered encode-safety fallback, so the
        # separate try/except this line used to need is no longer necessary.
        _warn("bm_store: could not encode CLI output for this terminal "
              "(%r); the command may have already succeeded or failed "
              "before this print." % (e,))
        sys.exit(1)
    except ValueError as e:
        # A caller-input error (bad name, bad lifetime, unknown target
        # state): the caller's mistake, not corruption, so a plain refusal.
        _out("refused (bad-input): %s" % (e,))
        sys.exit(2)
    except RedactionUnavailable as e:
        # GATE C (prerelease fix round): MUST be caught here, before the
        # OwnershipRefused clause below (its own base class). With
        # bm_telemetry.py absent, a claim COMMITTED and then this
        # command's own confirmation print raised RedactionUnavailable;
        # falling through to the OwnershipRefused handler below tried to
        # _out("refused (...)"), which itself calls redact_text() on the
        # very message it is printing and raised RedactionUnavailable a
        # SECOND time, uncaught, out of the except block itself: exit 1
        # with a raw traceback reporting an already-committed success as
        # though nothing happened. Degrades to the SAME fixed, hardcoded
        # notice _warn_no_redact_once() already uses elsewhere (never a
        # redacted print, so this cannot raise a second time) and exits 1,
        # an environment problem, never 2 ("refused"): the reporting path
        # must never be what decides whether committed work is reported
        # as blocked.
        _warn_no_redact_once()
        _raw_write(sys.stderr,
                   "bm_store: this command's own confirmation could not be "
                   "printed because of the missing redactor above; run "
                   "`python3 tools/bm_store.py verify` or `dump` once "
                   "bm_telemetry.py is restored to see whether it actually "
                   "took effect.\n")
        sys.exit(1)
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
