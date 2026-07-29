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

Python 3.9, standard library only. No network, no subprocess. That claim now
covers strictly more code than it used to, and it was kept DELIBERATELY when
FINDING 5 needed git's real state: root resolution walks the filesystem
directly, and the git containment check reads git's own on-disk files
(.git/index, .gitignore, .git/info/exclude) and parses them here in pure
Python rather than shelling out to `git ls-files` or `git check-ignore`.
Three reasons, all of them load-bearing:
  * bm_telemetry.py loads this module by path and documents that doing so
    "keeps this module's own no-subprocess property intact"; SECURITY.md
    publishes that property and a mechanical test in test_bm.py enforces it
    per file. An import here would silently break all three at once.
  * this check runs on EVERY store open, including inside a repository the
    founder did not create, and executing a PATH-resolved binary from that
    position is a bigger surface than reading four files.
  * a subprocess that cannot be spawned (no git on PATH, a locked-down hook
    environment) gives an "unknown" answer that a security check has to
    treat as a refusal anyway, so the dependency buys nothing.
The cost is stated where it is paid: see _git_index_tracked_paths and
_git_ignore_decision for exactly which git behaviours are implemented and
which are deliberately not.
No em or en dashes anywhere in this file, its comments, or its output.
"""
import contextlib
import weakref
import datetime
import hashlib
import io
import json
import os
import posixpath
import re
import shlex
import shutil
import sqlite3
import sys
import uuid

SCHEMA_VERSION = 2
STORE_DIRNAME = ".brothermode"
STORE_FILENAME = "store.sqlite3"
MAX_ACTIVE_PERSISTENT = 3

def invocation(script_name, module_file):
    """The command a reader can actually paste, in the layout they have.

    P17 put six commands on PATH, which made every hardcoded
    `python3 tools/bm_*.py ...` instruction a lie for anyone who installed
    from pipx, uv, or pip: there is no tools/ directory in a packaged
    install, so the first refusal such a user sees names a file that does
    not exist. This resolves the instruction instead of hardcoding it.

    Two layouts, one rule. The console script is named only when this
    module was imported FROM the environment that owns the script (module
    under sys.prefix AND an executable of that name beside sys.executable),
    because a founder running a repo checkout while some other environment
    happens to have bm-store on PATH must not be pointed at that other
    install. Otherwise the answer is the module's own absolute path, which
    is correct from any cwd and in any project (the shape verify()'s
    STATE.md nudge already used). Never raises: an instruction string is
    not worth a traceback, so any surprise degrades to the path form."""
    try:
        here = os.path.abspath(module_file)
        prefix = os.path.abspath(sys.prefix)
        candidate = os.path.join(
            os.path.dirname(os.path.abspath(sys.executable)), script_name)
        if (here.startswith(prefix + os.sep)
                and os.path.isfile(candidate)
                and os.access(candidate, os.X_OK)):
            return script_name
        return "python3 %s" % shlex.quote(here)
    except Exception:
        return "python3 %s" % module_file


def _cmd():
    """This tool's own invocation, for user-facing instruction text."""
    return invocation("bm-store", __file__)


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


def resolve_root(start=None, refuse_past_git_boundary=False):
    """Return (root_path, source), source in ("env", "marker", "git"), or
    (None, None) when nothing anchors a project here.

    Order matters and is deliberate: BROTHERMODE_ROOT always wins because a
    human or a script set it on purpose. Failing that, a marker directory
    ANYWHERE up the tree beats a closer .git, so once `init` has run, a
    nested .git (a submodule, a vendored dependency) can never shadow the
    real project root (fixes F2 / F42 / the F2b class).

    refuse_past_git_boundary (FINDING 11, MEDIUM) is OPT-IN and defaults
    OFF, which is the whole point. The precedence above is CORRECT for the
    bug class it was written for, and simply preferring the nearest .git
    would reopen F2 / F42 / F2b, so this does NOT change the ordering for
    anybody. What it adds is a second, requestable question: does the root
    this resolver picked sit ABOVE a nearer git boundary, meaning the
    caller is standing in a repository of its own that would silently
    attach to a DIFFERENT parent project's store?

    bm_autosave.py discovered that question privately (see
    _resolve_receipt_root there: "resolve_root(toplevel) can walk UP PAST
    this snapshot's own git toplevel") and carries its own copy of the
    check. A private copy is a check the next consumer does not get, so it
    lives here now and every consumer can ask for it.

    When it fires, this REFUSES rather than picking a side: choosing the
    nearer .git reopens the vendored-submodule bug, choosing the further
    marker is the cross-project attachment being reported, and guessing
    between two defensible answers is what got this class of bug shipped
    twice already. The refusal names BROTHERMODE_ROOT, which is the
    explicit answer.

    Source "env" is exempt on purpose: BROTHERMODE_ROOT IS the explicit
    root the refusal asks for, so checking it against the filesystem would
    turn the only remedy into another dead end. A caller that also needs to
    validate an explicitly-set root against its own expectations (as
    bm_autosave does, comparing against its snapshot's toplevel) still has
    to do that itself; this parameter does not cover it."""
    env = os.environ.get("BROTHERMODE_ROOT")
    if env:
        p = os.path.realpath(env)
        if os.path.isdir(p):
            return p, "env"
    cur = os.path.realpath(start or os.getcwd())
    chain = _walk_up(cur)
    for d in chain:
        if os.path.isdir(os.path.join(d, ".brothermode")):
            if refuse_past_git_boundary:
                # chain is closest-first, so anything reached BEFORE the
                # marker directory is strictly nearer to `start` than the
                # root we were about to return. A .git ABOVE the marker is
                # not a disagreement at all (the marker is still the
                # innermost anchor), which is why the walk stops at d.
                for nearer in chain:
                    if nearer == d:
                        break
                    if os.path.exists(os.path.join(nearer, ".git")):
                        raise OwnershipRefused(
                            "root-ambiguous",
                            "two different answers for 'which project is "
                            "this': %s is its own git repository, but the "
                            "nearest BrotherMode marker is further up at "
                            "%s. Attaching this repository to that parent "
                            "project's store would put this work in "
                            "another project's ledger, and preferring the "
                            "nearer .git would let a vendored submodule "
                            "shadow a real project root again (F2 / F42). "
                            "Say which you mean: run `%s init` inside %s "
                            "to give it its own store, or set "
                            "BROTHERMODE_ROOT=%s to attach to the parent on "
                            "purpose."
                            % (nearer, d, _cmd(), nearer, d),
                            details={"git_boundary": nearer, "marker_root": d})
            return d, "marker"
    for d in chain:
        # .git is a directory in a normal clone and a FILE in a worktree
        # (it holds "gitdir: <path>"); os.path.exists covers both, so
        # worktrees resolve a root the same way a normal checkout does.
        if os.path.exists(os.path.join(d, ".git")):
            return d, "git"
    return None, None


def require_root(start=None, refuse_past_git_boundary=False):
    """resolve_root(), or an OwnershipRefused the CLI (or any other caller)
    can render as a clear next step. "No root" is itself an ownership
    refusal, not a crash: nothing was touched, and the message says exactly
    what to run. refuse_past_git_boundary is passed straight through; see
    resolve_root for what it does and why it is opt-in."""
    root, source = resolve_root(start, refuse_past_git_boundary=refuse_past_git_boundary)
    if root is None:
        raise OwnershipRefused(
            "no-root",
            "no BrotherMode project root found (checked BROTHERMODE_ROOT, "
            "then every parent directory for .brothermode/, then for .git). "
            "Run `%s init` here or in the intended "
            "project root, or set BROTHERMODE_ROOT to point at it." % _cmd(),
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


def _scrubbed_field(L, t):
    """Normalize, then scrub, one founder-supplied learning field.

    LOOP 12. The learning tables used to scrub only raw_text, so a secret typed
    into --trigger, --action, --because, --domain or --scope-key landed in
    sqlite in cleartext and was copied forward into every rule version and every
    display surface. This is the one place that pairing is decided, so a new
    field cannot be added and quietly skip half of it. Normalize first so the
    scrubber sees the same whitespace form that gets stored."""
    return redact_text(L.normalize_text(t))


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

_TABLES_V1 = ("meta", "records", "claims", "decisions", "digests", "directives",
              "transitions", "autosave_receipts")

# Schema 2 adds correction learning. Kept as a SEPARATE tuple, and the live
# _TABLES chosen by SCHEMA_VERSION below, because _verify_schema_or_raise has to
# know which tables a store at THAT version is supposed to have. Without this, a
# perfectly healthy schema-1 store would fail the presence check against schema
# 2's table list and be quarantined before the version check ever ran, which is
# the exact destructive outcome the migration exists to prevent.
_TABLES_LEARNING = ("learning_candidates", "learning_rules",
                    "learning_rule_versions", "learning_evidence",
                    "learning_edges", "learning_applications")

_TABLES_V2 = _TABLES_V1 + _TABLES_LEARNING

_TABLES_BY_VERSION = {1: _TABLES_V1, 2: _TABLES_V2}

_TABLES = _TABLES_BY_VERSION[SCHEMA_VERSION]

# The learning schema. Applied to a NEW store by _ensure_schema (via _DDL below)
# and to an EXISTING schema-1 store by _migrate_1_to_2, which runs this exact
# same text: one definition, so a migrated store and a fresh store cannot drift.
#
# Deliberately NOT included from the source plan: learning_evaluation_cases,
# learning_evaluation_runs and learning_evaluation_outcomes. Those belong to
# Loop 9, which the founder deferred on 2026-07-28 (see
# docs/superpowers/specs/2026-07-28-correction-learning-program.md section 3.1).
# Creating their tables now would be schema for a feature nobody is building,
# and an empty table is a standing invitation to write a half-feature against it.
#
# content_hash carries NO global UNIQUE constraint, on purpose: the same words in
# two different scopes are two different pieces of evidence, and a unique index
# here would silently discard the second one. Deduplication is explicit logic
# over (source, scope, normalized content), which is Loop 6's job.
_LEARNING_DDL = """
CREATE TABLE IF NOT EXISTS learning_rules (
  rule_uuid TEXT PRIMARY KEY,
  current_version INTEGER NOT NULL DEFAULT 1,
  state TEXT NOT NULL CHECK(state IN (
    'approved','confirmed','settled','contradicted',
    'deprecated','superseded','forgotten')),
  rule_type TEXT NOT NULL DEFAULT 'preference' CHECK(rule_type IN (
    'preference','procedure','safety','communication',
    'tooling','quality','delegation','decision_right')),
  severity TEXT NOT NULL DEFAULT 'soft' CHECK(severity IN ('soft','gate')),
  scope_type TEXT NOT NULL CHECK(scope_type IN (
    'global','project','domain','artifact','relationship','tool')),
  scope_key TEXT NOT NULL DEFAULT '',
  founder_approved_at TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  superseded_by TEXT REFERENCES learning_rules(rule_uuid),
  forgotten_at TEXT
);
CREATE TABLE IF NOT EXISTS learning_candidates (
  candidate_uuid TEXT PRIMARY KEY,
  source_type TEXT NOT NULL CHECK(source_type IN (
    'explicit_correction','detected_correction','rework','escaped_defect',
    'revealed_choice','verified_procedure','manual','imported')),
  source_session_id TEXT NOT NULL DEFAULT '',
  source_record_uuid TEXT REFERENCES records(lifecycle_uuid),
  source_ref TEXT NOT NULL DEFAULT '',
  raw_text TEXT NOT NULL DEFAULT '',
  proposed_trigger TEXT NOT NULL DEFAULT '',
  proposed_action TEXT NOT NULL DEFAULT '',
  proposed_because TEXT NOT NULL DEFAULT '',
  proposed_domain TEXT NOT NULL DEFAULT '',
  proposed_scope_type TEXT NOT NULL DEFAULT 'project' CHECK(proposed_scope_type IN (
    'global','project','domain','artifact','relationship','tool')),
  proposed_scope_key TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN (
    'pending','under_review','approved','merged','split','rejected','expired')),
  content_hash TEXT NOT NULL,
  redaction_count INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  reviewed_at TEXT,
  review_note TEXT NOT NULL DEFAULT '',
  resulting_rule_uuid TEXT REFERENCES learning_rules(rule_uuid)
);
CREATE TABLE IF NOT EXISTS learning_rule_versions (
  rule_uuid TEXT NOT NULL REFERENCES learning_rules(rule_uuid) ON DELETE CASCADE,
  version INTEGER NOT NULL,
  trigger_text TEXT NOT NULL,
  action_text TEXT NOT NULL,
  because_text TEXT NOT NULL,
  domain TEXT NOT NULL DEFAULT '',
  tags_json TEXT NOT NULL DEFAULT '[]',
  change_type TEXT NOT NULL CHECK(change_type IN (
    'created','edited','narrowed','broadened',
    'contradiction_resolution','restored')),
  change_reason TEXT NOT NULL DEFAULT '',
  source_candidate_uuid TEXT REFERENCES learning_candidates(candidate_uuid),
  approved_by TEXT NOT NULL DEFAULT 'founder',
  created_at TEXT NOT NULL,
  PRIMARY KEY(rule_uuid, version)
);
CREATE TABLE IF NOT EXISTS learning_evidence (
  evidence_uuid TEXT PRIMARY KEY,
  rule_uuid TEXT REFERENCES learning_rules(rule_uuid) ON DELETE CASCADE,
  candidate_uuid TEXT REFERENCES learning_candidates(candidate_uuid) ON DELETE CASCADE,
  polarity TEXT NOT NULL CHECK(polarity IN ('support','contradict','neutral')),
  evidence_type TEXT NOT NULL CHECK(evidence_type IN (
    'founder_quote','founder_approval','revealed_choice','rework',
    'escaped_defect','verified_application','ignored_application',
    'manual_review','import_source')),
  source_session_id TEXT NOT NULL DEFAULT '',
  source_record_uuid TEXT REFERENCES records(lifecycle_uuid),
  source_ref TEXT NOT NULL DEFAULT '',
  excerpt TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  CHECK(rule_uuid IS NOT NULL OR candidate_uuid IS NOT NULL)
);
CREATE TABLE IF NOT EXISTS learning_edges (
  from_rule_uuid TEXT NOT NULL REFERENCES learning_rules(rule_uuid) ON DELETE CASCADE,
  to_rule_uuid TEXT NOT NULL REFERENCES learning_rules(rule_uuid) ON DELETE CASCADE,
  relation TEXT NOT NULL CHECK(relation IN (
    'duplicate_of','contradicts','supersedes',
    'derived_from','supports','applies_to')),
  note TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  PRIMARY KEY(from_rule_uuid, to_rule_uuid, relation),
  CHECK(from_rule_uuid <> to_rule_uuid)
);
CREATE TABLE IF NOT EXISTS learning_applications (
  application_uuid TEXT PRIMARY KEY,
  rule_uuid TEXT NOT NULL,
  rule_version INTEGER NOT NULL,
  session_id TEXT NOT NULL,
  record_uuid TEXT REFERENCES records(lifecycle_uuid),
  task_fingerprint TEXT NOT NULL DEFAULT '',
  task_excerpt TEXT NOT NULL DEFAULT '',
  retrieved_at TEXT NOT NULL,
  retrieval_rank INTEGER,
  retrieval_score REAL,
  scope_match TEXT NOT NULL DEFAULT '',
  shown_to_model INTEGER NOT NULL DEFAULT 0 CHECK(shown_to_model IN (0,1)),
  disposition TEXT NOT NULL DEFAULT 'unknown' CHECK(disposition IN (
    'followed','ignored','not_relevant','unknown')),
  disposition_reason TEXT NOT NULL DEFAULT '',
  verification_ref TEXT NOT NULL DEFAULT '',
  outcome TEXT NOT NULL DEFAULT 'pending' CHECK(outcome IN (
    'pending','accepted','rework','escaped_defect',
    'corrected_again','not_decidable')),
  outcome_ref TEXT NOT NULL DEFAULT '',
  closed_at TEXT,
  FOREIGN KEY(rule_uuid, rule_version)
    REFERENCES learning_rule_versions(rule_uuid, version)
);
"""

_LEARNING_INDEX_DDL = """
CREATE INDEX IF NOT EXISTS learning_candidates_status_idx
  ON learning_candidates(status, created_at);
CREATE INDEX IF NOT EXISTS learning_candidates_source_idx
  ON learning_candidates(source_session_id, source_type);
CREATE INDEX IF NOT EXISTS learning_candidates_hash_idx
  ON learning_candidates(content_hash);
CREATE INDEX IF NOT EXISTS learning_rules_scope_idx
  ON learning_rules(scope_type, scope_key, state);
CREATE INDEX IF NOT EXISTS learning_evidence_rule_idx
  ON learning_evidence(rule_uuid, polarity);
CREATE INDEX IF NOT EXISTS learning_applications_rule_idx
  ON learning_applications(rule_uuid, rule_version);
CREATE INDEX IF NOT EXISTS learning_applications_session_idx
  ON learning_applications(session_id, retrieved_at);
"""


def _split_ddl(script):
    """Split a DDL script into individual statements.

    Exists because sqlite3.Connection.executescript() issues an implicit COMMIT
    before it runs anything. Inside Store._migrate_from's BEGIN EXCLUSIVE that
    silently ENDS the transaction, so the DDL lands piecemeal in autocommit and
    the closing COMMIT fails with "cannot commit - no transaction is active".
    Reproduced live on 2026-07-29 against a real schema-1 store: the migration
    appeared to succeed while the all-or-nothing property it advertises was
    false, which is precisely the half-migrated state the whole loop exists to
    make impossible.

    Safe as a plain split because this project's DDL contains no semicolon
    inside any string literal or comment; a test asserts the statement count so
    that adding one cannot pass unnoticed."""
    return tuple(s.strip() for s in script.split(";") if s.strip())


_LEARNING_DDL_STATEMENTS = _split_ddl(_LEARNING_DDL)
_LEARNING_INDEX_STATEMENTS = _split_ddl(_LEARNING_INDEX_DDL)


def _migrate_1_to_2(conn):
    """Schema 1 to 2: add the correction-learning tables. ADDITIVE ONLY.

    Not one existing row is read, rewritten, copied or deleted. The source
    plan's rule "never rebuild the database by copying only parsed rows" is
    satisfied trivially here because nothing is rebuilt at all: schema 1 data
    survives byte for byte, which is the property the migration test asserts by
    comparing every pre-migration row against its post-migration self.

    Runs INSIDE the caller's exclusive transaction (Store._migrate_from). It
    must therefore never COMMIT, never ROLLBACK and never open its own
    transaction, or the caller's all-or-nothing guarantee is broken. That rules
    out executescript(), which commits implicitly before it runs; see
    _split_ddl for the incident that proved it."""
    for statement in _LEARNING_DDL_STATEMENTS:
        conn.execute(statement)
    for statement in _LEARNING_INDEX_STATEMENTS:
        conn.execute(statement)


# The registry maps FROM-version to the step that raises it by exactly one.
# Chained by Store._migrate_from, so a future 2->3 lands here as one more entry
# and every older store still walks the whole way up.
_MIGRATIONS = {
    1: _migrate_1_to_2,
}

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
_CANDIDATE_SOURCE_TYPES = (
    "explicit_correction", "detected_correction", "rework", "escaped_defect",
    "revealed_choice", "verified_procedure", "manual", "imported")

_LEARNING_MOD = None


def _learning():
    """Load bm_learning.py from THIS file's directory, by path.

    Same technique bm_telemetry.py uses to load this module, and for the same
    reason: bm_store.py is loaded by path from several places, so a plain
    `import bm_learning` would depend on whichever sys.path the caller happened
    to have. Cached after the first load."""
    global _LEARNING_MOD
    if _LEARNING_MOD is None:
        import importlib.util
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "bm_learning.py")
        spec = importlib.util.spec_from_file_location("bm_learning", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _LEARNING_MOD = mod
    return _LEARNING_MOD


def _one_or_refuse(rows, kind, prefix):
    """Resolve a uuid PREFIX to exactly one row, or refuse.

    Refusing ambiguity is deliberate and matches how thread identity is
    resolved elsewhere in this project: picking "the first match" for a short
    prefix is how a founder edits the wrong rule and never finds out."""
    if not rows:
        raise OwnershipRefused("not-found", "no %s matches %r" % (kind, prefix))
    if len(rows) > 1:
        raise OwnershipRefused("ambiguous", "%r matches %d %ss (%s); use more characters"
            % (prefix, len(rows), kind,
               ", ".join(r[0][:8] for r in rows)))
    return dict(rows[0])


# WITHHELD ENTIRELY from dump, not merely passed through the scrubber.
#
# NOT-FINALIZED item 15, found by the Loop 0 baseline: redact_text is a secret
# SCRUBBER. It removes secret-shaped substrings and lets ordinary prose through
# untouched, which was harmless while every text column held a work objective
# the founder had typed about their own project. These two columns are
# different in kind: they hold the founder's VERBATIM WORDS, captured from a
# correction, including whatever a frustrated founder happened to say about a
# client, a number, or a person. A dump is exactly what gets piped into a file
# or pasted into an issue.
#
# So these are replaced by a length marker rather than scrubbed. The marker
# keeps a dump structurally honest (you can see evidence exists and how much of
# it) without reproducing any of it. --raw still returns everything, and
# SECURITY.md already documents the database file itself as sensitive.
_DUMP_WITHHELD_COLUMNS = frozenset((
    ("learning_candidates", "raw_text"),
    ("learning_evidence", "excerpt"),
    ("learning_applications", "task_excerpt"),
))

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


def safe_project_path(root, *parts):
    """THE PATH FUNNEL: the ONE public way this project builds a path to a
    generated file inside a project root, and the only shape allowed to be
    opened or written. Public on purpose, so bm_threads.py and any other
    caller use this instead of growing their own os.path.join.

        safe_project_path(root, "STATE.md")
        safe_project_path(root, "threads", name + ".md")

    Returns the absolute, containment-checked path. Creates NOTHING.

    WHY (finding 2B, CONFIRMED by execution): every root-relative path in
    this module except the store itself was a bare os.path.join, and
    os.path.join followed by open() follows a symlink silently. With
    STATE.md symlinked at a file outside the project, write_state_view read
    the TARGET's bytes and wrote them to <root>/STATE.md.bak-<stamp>, an
    ordinary in-repo file no project's .gitignore knows about, so a routine
    `git add -A` committed the copied content. Fixing that one call site
    would have left call site N+1 open, which is exactly how the twelve
    hand-fixed database handles were followed by a thirteenth leak, so the
    containment lives here and a structural test fails the build when a new
    site joins a root without it.

    Reuses the two containment primitives above rather than growing a third
    piece of symlink logic beside them:
      * _refuse_if_symlink_escape on EVERY existing component, root's
        immediate child down through the leaf, so a symlinked PARENT
        DIRECTORY is caught too, not only a symlinked leaf;
      * _refuse_if_hardlinked on any component that is a regular FILE.
        Deliberately NOT on directories: a POSIX directory always reports
        st_nlink >= 2 ('.' plus its parent's entry; measured on this
        machine: 2 for an empty directory, 4 with two subdirectories), so
        applying the hardlink check to a directory would refuse every
        legitimate path on the platform.

    The path is built under the RESOLVED root, so a project living beneath
    a symlinked prefix (macOS /tmp -> /private/tmp) is normal rather than
    an escape, and the final result must still resolve to itself and sit
    inside that resolved root. Any violation raises
    OwnershipRefused('path-escape') naming the path and what it resolved
    to."""
    if not parts:
        raise OwnershipRefused(
            "path-escape",
            "safe_project_path was called with no path components under %s; "
            "a generated file must name itself" % (root,))
    real_root = os.path.realpath(root)
    for part in parts:
        if not isinstance(part, str) or not part:
            raise OwnershipRefused(
                "path-escape",
                "%r is not a usable path component under %s" % (part, real_root))
        if os.path.isabs(part) or os.path.splitdrive(part)[0]:
            raise OwnershipRefused(
                "path-escape",
                "path component %r is absolute; safe_project_path only builds "
                "paths RELATIVE to the project root %s, so an absolute part "
                "(which os.path.join would silently let win over the root) is "
                "refused rather than obeyed" % (part, real_root),
                details={"component": part, "root": real_root})
    candidate = os.path.normpath(os.path.join(real_root, *parts))
    prefix = real_root if real_root.endswith(os.sep) else real_root + os.sep
    if not candidate.startswith(prefix):
        raise OwnershipRefused(
            "path-escape",
            "%s resolves to %s, which is not inside the project root %s; "
            "refusing to read or write it" % ("/".join(parts), candidate, real_root),
            details={"expected": candidate, "root": real_root})
    walked = real_root
    for component in os.path.relpath(candidate, real_root).split(os.sep):
        walked = os.path.join(walked, component)
        _refuse_if_symlink_escape(walked)
        if os.path.isfile(walked):
            _refuse_if_hardlinked(walked)
    resolved = os.path.realpath(candidate)
    if resolved != candidate:
        raise OwnershipRefused(
            "path-escape",
            "%s resolves to %s; refusing to read or write a generated file "
            "through anything that does not resolve to itself inside the "
            "project root %s" % (candidate, resolved, real_root),
            details={"expected": candidate, "resolved": resolved,
                     "root": real_root})
    return candidate


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


def _resolve_git_dirs(root):
    """(worktree_gitdir, common_dir) for the checkout whose TOP LEVEL is
    root, or (None, None) when there is no git here or it could not be
    read (GATE C, split into two values for FINDING 5).

    A normal checkout: both are <root>/.git. A worktree: .git is a FILE
    containing 'gitdir: <path>' pointing at <main>/.git/worktrees/<name>,
    and the two answers DIVERGE, which is exactly why they are returned
    separately now:
      * common_dir holds info/exclude, which is NOT per-worktree; it is
        shared once at the top of the MAIN checkout's .git, named by that
        worktree gitdir's own 'commondir' file (present since git 2.5).
        Returning early on a .git FILE used to leave nothing excluded
        inside a worktree, so `git add -A` staged the raw store.
      * worktree_gitdir holds the INDEX, which IS per-worktree. Reading the
        common dir's index to answer "is the store tracked here" would
        answer it for a DIFFERENT worktree.

    SOFT G: the pointer is validated with _looks_like_git_admin_dir before
    being trusted, and NEVER created by us: a crafted .git file naming an
    arbitrary path (e.g. 'gitdir: /etc') used to make this return that path
    verbatim, and the caller would os.makedirs a tree there. Raises
    OwnershipRefused('path-escape') instead."""
    git_path = os.path.join(root, ".git")
    if os.path.isdir(git_path):
        return git_path, git_path
    if not os.path.isfile(git_path):
        return None, None
    try:
        with open(git_path, encoding="utf-8", errors="replace") as f:
            content = f.read().strip()
    except OSError:
        return None, None
    if not content.startswith("gitdir:"):
        return None, None
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
            return worktree_gitdir, worktree_gitdir
        common = os.path.realpath(os.path.join(worktree_gitdir, rel))
        if not _looks_like_git_admin_dir(common):
            raise OwnershipRefused(
                "path-escape",
                "the commondir file at %s points to %s, which does not "
                "exist or does not look like real git administrative "
                "state; refusing to create directories or write anything "
                "there" % (commondir_file, common),
                details={"commondir_file": commondir_file, "pointer_target": common})
        return worktree_gitdir, common
    return worktree_gitdir, worktree_gitdir


def _resolve_git_common_dir(root):
    """The directory that actually holds info/exclude for this checkout.
    Kept as its own name because _ensure_git_excludes wants exactly this
    one value and nothing else; see _resolve_git_dirs for the reasoning
    and for the worktree pointer validation (SOFT G)."""
    return _resolve_git_dirs(root)[1]


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


# ---------------------------------------------------------------------------
# FINDING 5 (HIGH): git containment is now CHECKED, not merely attempted.
#
# The store holds founder objectives, decisions, digests and directives in
# CLEARTEXT: redaction happens at the display boundary (dump, render_digest,
# render_state_md), so the sqlite file itself is the sensitive artefact
# SECURITY.md says it is. Everything protecting it from git was, until now,
# a best-effort WRITE: _ensure_git_excludes appends three lines to
# info/exclude and swallows OSError so the store still opens. Two holes
# follow directly from "write, never verify":
#   * an exclude rule does NOT untrack a file git already tracks. A repo
#     that already has .brothermode/store.sqlite3 in its index (added by
#     accident, or by someone else, or inherited by cloning a repo the
#     founder did not create) keeps committing the raw store on every
#     routine `git add -A`, with every exclude line present and correct.
#   * when the write fails, the store opens anyway and nothing is excluded.
#
# So the write stays (it is what makes the healthy case healthy) and is now
# followed by a CHECK of git's actual state, run on every writable open,
# before sqlite3.connect creates or touches the database. Two questions,
# both answered from git's own files:
#   1. is any of .brothermode/, the store, or its -wal/-shm sidecars in the
#      index? -> refuse 'git-tracked-store', naming the untracking command.
#   2. are those paths genuinely ignored? -> refuse 'git-exposed-store'.
# An answer that cannot be established (an index this parser does not
# understand, an unreadable .gitignore) refuses 'git-state-unknown' rather
# than assuming the safe answer, because assuming the safe answer is the
# defect being closed.
#
# ESCAPE HATCH, documented rather than hidden: BROTHERMODE_SKIP_GIT_CONTAINMENT
# set to any non-empty value skips the whole check and warns loudly, for the
# founder who has looked and decided. The refusals also name BROTHERMODE_ROOT,
# which is the pre-existing, better answer for "I want the store to live
# outside this repository entirely": point it at a directory no git repo
# contains and this check has nothing to complain about.
# ---------------------------------------------------------------------------

SKIP_GIT_CONTAINMENT_ENV = "BROTHERMODE_SKIP_GIT_CONTAINMENT"


def _git_decode_varint(data, pos):
    """(value, new_pos) for git's own varint encoding (varint.c
    decode_varint), used by version 4 index entries. (None, pos) when the
    buffer ends mid-number."""
    if pos >= len(data):
        return None, pos
    c = data[pos]
    pos += 1
    val = c & 0x7F
    while c & 0x80:
        if pos >= len(data):
            return None, pos
        val += 1
        c = data[pos]
        pos += 1
        val = (val << 7) + (c & 0x7F)
    return val, pos


def _git_index_tracked_paths(index_path):
    """Every path recorded in a git index, as a set of posix strings
    relative to the worktree top. Returns None for "cannot be established",
    which callers MUST treat as unknown and refuse on, never as "nothing is
    tracked": a parser that silently reports an empty set on an index it
    does not understand is the same fail-open shape FINDING 5 is about.
    A MISSING index is different and returns an empty set: a repository
    with no index has nothing staged or tracked at all.

    Pure parsing, no subprocess (see the module header for why). Format:
    git's Documentation/gitformat-index.txt. A 12 byte header ("DIRC", a
    big-endian version, a big-endian entry count), then one entry each:
    62 bytes of stat data, sha and flags, plus 2 more flag bytes when the
    extended bit is set (version 3+), then the path. Versions 2 and 3 store
    the path literally and NUL-pad every entry to a multiple of 8; version
    4 stores it prefix-compressed against the previous path (a varint of
    how many trailing bytes to strip, then the new suffix, NUL terminated)
    and does not pad. Extensions after the entries are not read: nothing
    after the entry table changes which paths are tracked."""
    try:
        with open(index_path, "rb") as f:
            data = f.read()
    except FileNotFoundError:
        return set()
    except OSError:
        return None
    if len(data) < 12 or data[:4] != b"DIRC":
        return None
    version = int.from_bytes(data[4:8], "big")
    count = int.from_bytes(data[8:12], "big")
    if version not in (2, 3, 4):
        return None
    # A cheap sanity bound before looping `count` times: the smallest
    # possible entry is well over 8 bytes, so a count this large cannot
    # describe this file and means the header is not what it claims.
    if count > max(len(data) - 12, 0) // 8:
        return None
    pos = 12
    prev = b""
    paths = set()
    for _ in range(count):
        start = pos
        if start + 62 > len(data):
            return None
        flags = int.from_bytes(data[start + 60:start + 62], "big")
        pos = start + 62
        if version >= 3 and (flags & 0x4000):
            if pos + 2 > len(data):
                return None
            pos += 2
        if version == 4:
            strip, pos = _git_decode_varint(data, pos)
            if strip is None or strip > len(prev):
                return None
            end = data.find(b"\x00", pos)
            if end < 0:
                return None
            name = prev[:len(prev) - strip] + data[pos:end]
            pos = end + 1
        else:
            name_len = flags & 0x0FFF
            if name_len == 0x0FFF:
                # 0xFFF is a saturating marker, not a length: the real name
                # runs to the terminating NUL.
                end = data.find(b"\x00", pos)
                if end < 0:
                    return None
                name = data[pos:end]
            else:
                if pos + name_len > len(data):
                    return None
                name = data[pos:pos + name_len]
            pos += len(name)
            # 1 to 8 NULs, padding the whole entry to a multiple of 8 while
            # keeping the name NUL terminated (git's ondisk_ce_size).
            pos += 8 - ((pos - start) % 8)
            if pos > len(data):
                return None
        prev = name
        paths.add(name.decode("utf-8", "replace"))
    return paths


def _gitignore_pattern_to_regex(pattern, anchored):
    """Compile ONE gitignore pattern (already stripped of its '!' and of a
    trailing '/') into a regex matched against a path relative to the
    directory that pattern came from. Returns None when it cannot be
    compiled, which the caller turns into "ignore status unknown" rather
    than into a silently dropped rule.

    Implemented: '*' and '?' stopping at '/', character classes, backslash
    escapes, '**/' at the start, '/**' at the end, '/**/' in the middle,
    anchoring (a pattern containing a slash is relative to its own
    directory; one without matches at any depth below it)."""
    out = []
    i = 0
    n = len(pattern)
    while i < n:
        c = pattern[i]
        if c == "\\" and i + 1 < n:
            out.append(re.escape(pattern[i + 1]))
            i += 2
            continue
        if c == "*":
            j = i
            while j < n and pattern[j] == "*":
                j += 1
            if (j - i) >= 2 and (i == 0 or pattern[i - 1] == "/") \
                    and (j >= n or pattern[j] == "/"):
                if j >= n:
                    out.append(".*")          # trailing '/**': everything inside
                else:
                    out.append("(?:[^/]*/)*")  # '**/': zero or more directories
                    j += 1                     # consume the slash it owns
                i = j
                continue
            # Anything else, including '**' not bounded by slashes, is a
            # run of ordinary asterisks (git: "other consecutive asterisks
            # are considered regular asterisks").
            out.append("[^/]*")
            i = j
            continue
        if c == "?":
            out.append("[^/]")
            i += 1
            continue
        if c == "[":
            j = i + 1
            if j < n and pattern[j] in "!^":
                j += 1
            if j < n and pattern[j] == "]":
                j += 1
            while j < n and pattern[j] != "]":
                j += 1
            if j >= n:
                out.append(re.escape("["))     # unterminated class: literal
                i += 1
                continue
            body = pattern[i + 1:j]
            if body.startswith("!"):
                body = "^" + body[1:]
            out.append("[" + body + "]")
            i = j + 1
            continue
        out.append(re.escape(c))
        i += 1
    prefix = "" if anchored else "(?:.*/)?"
    try:
        return re.compile(prefix + "".join(out) + r"\Z", re.DOTALL)
    except re.error:
        return None


def _read_gitignore_rules(path):
    """The rules in one .gitignore or info/exclude file, in file order, as
    (regex, negated, dir_only) tuples. [] for a file that is not there (no
    rules is a real, healthy answer). None when the file exists but cannot
    be read or contains a pattern this module cannot compile, so an
    unreadable rule can never be silently skipped: skipping a NEGATION
    would flip the answer from "exposed" to "ignored", which is the one
    direction that must not happen."""
    if not os.path.isfile(path):
        return []
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except OSError:
        return None
    rules = []
    for line in lines:
        if not line or line.startswith("#"):
            continue
        line = _strip_gitignore_trailing_space(line)
        if not line:
            continue
        negated = line.startswith("!")
        if negated:
            line = line[1:]
        dir_only = line.endswith("/")
        if dir_only:
            line = line[:-1]
        if not line:
            continue
        anchored = "/" in line
        if line.startswith("/"):
            line = line[1:]
        rx = _gitignore_pattern_to_regex(line, anchored)
        if rx is None:
            return None
        rules.append((rx, negated, dir_only))
    return rules


def _strip_gitignore_trailing_space(line):
    """Trailing spaces are not part of a gitignore pattern unless the last
    one is backslash escaped."""
    i = len(line)
    while i > 0 and line[i - 1] in " \t":
        backslashes = 0
        k = i - 2
        while k >= 0 and line[k] == "\\":
            backslashes += 1
            k -= 1
        if backslashes % 2 == 1:
            break
        i -= 1
    return line[:i]


def _gitignore_sources(worktree_top, common_dir, relpath):
    """(file_path, base_relpath) for every ignore file that can speak about
    relpath, in INCREASING precedence: info/exclude first, then .gitignore
    at the worktree top, then one per directory on the way down. Git's own
    order, minus core.excludesFile and the global ~/.config/git/ignore,
    which are deliberately not read: skipping them can only make this
    module conclude "not ignored" where git would say "ignored", which
    refuses a safe repo (recoverable, and the refusal names the escape
    hatch) instead of admitting an exposed one."""
    sources = [(os.path.join(common_dir, "info", "exclude"), "")]
    sources.append((os.path.join(worktree_top, ".gitignore"), ""))
    cur = ""
    for part in relpath.split("/")[:-1]:
        cur = (cur + "/" + part) if cur else part
        sources.append(
            (os.path.join(worktree_top, cur.replace("/", os.sep), ".gitignore"), cur))
    return sources


def _last_matching_gitignore_rule(worktree_top, common_dir, relpath, is_dir):
    """True (ignored), False (not ignored), or None (cannot be
    established), for ONE path, ignoring its parent directories. Git's
    rule: the highest-precedence file that matches decides, and within a
    file the LAST matching line decides, so walking sources low to high and
    overwriting reproduces it."""
    decision = False
    for src_path, base in _gitignore_sources(worktree_top, common_dir, relpath):
        rules = _read_gitignore_rules(src_path)
        if rules is None:
            return None
        if not rules:
            continue
        if base:
            if not relpath.startswith(base + "/"):
                continue
            rel = relpath[len(base) + 1:]
        else:
            rel = relpath
        for rx, negated, dir_only in rules:
            if dir_only and not is_dir:
                continue
            if rx.match(rel):
                decision = not negated
    return decision


def _git_ignore_decision(worktree_top, common_dir, relpath, is_dir):
    """Would git ignore relpath (posix, relative to worktree_top)? True,
    False, or None for "cannot be established".

    Checks every ancestor directory first, because git stops descending at
    the first excluded directory and a file under one cannot be re-included
    ("It is not possible to re-include a file if a parent directory of that
    file is excluded"). That is also what makes the healthy case work: the
    line _ensure_git_excludes writes is '.brothermode/', a DIRECTORY rule,
    and the store file inside it is ignored by inheritance rather than by
    any rule naming it."""
    parts = [p for p in relpath.split("/") if p]
    if not parts:
        return None
    for i in range(len(parts)):
        sub = "/".join(parts[:i + 1])
        sub_is_dir = True if i < len(parts) - 1 else is_dir
        decision = _last_matching_gitignore_rule(
            worktree_top, common_dir, sub, sub_is_dir)
        if decision is None:
            return None
        if decision:
            return True
    return False


def _enclosing_git_context(start):
    """(worktree_top, worktree_gitdir, common_dir) for the git checkout
    that CONTAINS start, or (None, None, None) when there is none.

    Walks UP rather than only checking <start>/.git, which _ensure_git_excludes
    does. That difference is deliberate and is part of FINDING 5: a
    .brothermode marker can sit in a SUBDIRECTORY of a repository (run
    `init` in a subdirectory and it does), in which case <root>/.git does
    not exist, _ensure_git_excludes writes nothing at all, and `git add -A`
    from the repository top commits the raw store with no rule anywhere
    objecting. Looking only where the exclude file would have gone would
    miss exactly the case where no exclude file was written."""
    for d in _walk_up(os.path.realpath(start)):
        if os.path.exists(os.path.join(d, ".git")):
            worktree_gitdir, common_dir = _resolve_git_dirs(d)
            if worktree_gitdir is None:
                return None, None, None
            return d, worktree_gitdir, common_dir
    return None, None, None


def _refuse_if_git_can_commit_store(root):
    """THE CHECK (FINDING 5). Refuses when git's real state says the raw
    store is, or could become, committable. Silent and fast when the store
    is properly contained, and a no-op when there is no git here at all,
    since nothing can commit what no repository contains."""
    if os.environ.get(SKIP_GIT_CONTAINMENT_ENV, "").strip():
        _warn("bm_store: WARNING: %s is set, so the git containment check is "
              "SKIPPED. The raw store at %s holds founder objectives, "
              "decisions, digests and directives in cleartext; nothing is "
              "checking that git will not commit it."
              % (SKIP_GIT_CONTAINMENT_ENV, store_path(root)))
        return
    worktree_top, worktree_gitdir, common_dir = _enclosing_git_context(root)
    if worktree_top is None:
        return
    targets = [store_dir(root), store_path(root),
               store_path(root) + "-wal", store_path(root) + "-shm"]
    rels = []
    for target in targets:
        rel = os.path.relpath(os.path.realpath(target), worktree_top)
        if rel == os.pardir or rel.startswith(os.pardir + os.sep):
            return          # the store is not inside this checkout after all
        rels.append(_to_posix(rel))
    dir_rel, file_rels = rels[0], rels[1:]

    tracked = _git_index_tracked_paths(os.path.join(worktree_gitdir, "index"))
    if tracked is None:
        raise OwnershipRefused(
            "git-state-unknown",
            "the git index at %s could not be read or parsed, so whether "
            "this repository already tracks the raw store at %s cannot be "
            "established. Refusing rather than assuming it does not: the "
            "store holds founder objectives, decisions, digests and "
            "directives in cleartext. Check the repository with `git -C %s "
            "status`, or set %s=1 to open anyway once you have looked."
            % (os.path.join(worktree_gitdir, "index"), store_path(root),
               worktree_top, SKIP_GIT_CONTAINMENT_ENV),
            details={"index": os.path.join(worktree_gitdir, "index"),
                     "worktree_top": worktree_top})

    hits = sorted(p for p in tracked
                  if p in file_rels or p == dir_rel or p.startswith(dir_rel + "/"))
    if hits:
        raise OwnershipRefused(
            "git-tracked-store",
            "git already TRACKS the raw BrotherMode store in %s (tracked "
            "path(s): %s). An ignore rule does not untrack a tracked file, "
            "so the next routine `git add -A` would commit founder "
            "objectives, decisions, digests and directives in cleartext. "
            "Untrack it, keeping the file on disk, with `git -C %s rm "
            "--cached -r --ignore-unmatch -- %s`, then commit that "
            "removal. If it was ever COMMITTED, the contents are still in "
            "history and removing them needs a history rewrite (git "
            "filter-repo) plus a force push. To keep the store out of this "
            "repository entirely, set BROTHERMODE_ROOT to a directory no "
            "git repository contains. To open anyway, set %s=1."
            % (worktree_top, ", ".join(hits), worktree_top, dir_rel,
               SKIP_GIT_CONTAINMENT_ENV),
            details={"worktree_top": worktree_top, "tracked": hits,
                     "store_dir": dir_rel})

    for rel, is_dir in [(dir_rel, True)] + [(r, False) for r in file_rels]:
        decision = _git_ignore_decision(worktree_top, common_dir, rel, is_dir)
        if decision is None:
            raise OwnershipRefused(
                "git-state-unknown",
                "whether git ignores %s inside %s could not be established "
                "(an ignore file could not be read, or holds a pattern this "
                "checker cannot compile). Refusing rather than guessing, "
                "because the raw store holds founder objectives, decisions, "
                "digests and directives in cleartext. Check it yourself with "
                "`git -C %s check-ignore -v %s`, or set %s=1 to open anyway."
                % (rel, worktree_top, worktree_top, rel, SKIP_GIT_CONTAINMENT_ENV),
                details={"worktree_top": worktree_top, "path": rel})
        if not decision:
            raise OwnershipRefused(
                "git-exposed-store",
                "git does NOT ignore %s inside the repository at %s, so the "
                "raw store (founder objectives, decisions, digests and "
                "directives, in cleartext) is one `git add -A` away from "
                "being committed. BrotherMode tries to add the rule itself "
                "on every open, so seeing this means the write failed, the "
                "store sits somewhere that write does not cover, or a later "
                "rule re-includes it. Fix it by adding the line '/%s' to "
                "either %s or %s (and removing anything that re-includes "
                "it), then confirm with `git -C %s check-ignore -v %s`. To "
                "keep the store out of this repository entirely, set "
                "BROTHERMODE_ROOT to a directory no git repository "
                "contains. To open anyway, set %s=1."
                % (rel, worktree_top, dir_rel,
                   os.path.join(worktree_top, ".gitignore"),
                   os.path.join(common_dir, "info", "exclude"),
                   worktree_top, rel, SKIP_GIT_CONTAINMENT_ENV),
                details={"worktree_top": worktree_top, "path": rel,
                         "store_dir": dir_rel})


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


# FINDING 7: the exact conditions that may MOVE a founder's database.
#
# Before this, _is_transient_busy_error was a two-string allowlist and
# everything outside it was ASSUMED to be corruption, with no evidence that
# the file was damaged at all. A transient disk I/O error, a permission
# problem or a network-volume hiccup during the SessionStart hook's
# automatic `verify` was therefore enough to move a perfectly healthy store
# aside. The default is now inverted: quarantine happens only for a NAMED
# condition, and anything unrecognized reports without touching the file.
#
# QUARANTINES (evidence that the file itself is damaged):
#   * a cause that is not a sqlite3.Error at all. This module raises those
#     itself, and only after reading the file: zero length on disk, a table
#     genuinely absent from sqlite_master, a schema_version that does not
#     match. Those are findings, not guesses.
#   * type(cause) is exactly sqlite3.DatabaseError. Measured (Python 3.9.6,
#     SQLite 3.51.0): SQLITE_NOTADB raises DatabaseError('file is not a
#     database') and SQLITE_CORRUPT raises DatabaseError('database disk
#     image is malformed'); both arrive as the BASE class, never as an
#     OperationalError. That is the corruption class, by construction.
#   * a message naming corruption or a not-a-database file (below), so a
#     future SQLite that routes one of these through a subclass is still
#     caught.
#   * "no such table" / "no such column" from an OperationalError. This is
#     structural schema damage, not an environment hiccup: every table
#     named here is created by this module's own DDL, so sqlite reporting
#     one missing is evidence the schema was damaged (CRITICAL A,
#     fix-round 8, reproduced: drop the claims table, claim again, GRANTED
#     at exit 0). Kept deliberately.
#
# ONLY REPORTS NOW (the file is left exactly where it is, byte for byte):
#   "database is locked" / "database is busy" (already refused 'db-busy'
#   before reaching here), "disk I/O error", "unable to open database
#   file", "attempt to write a readonly database", "database or disk is
#   full", "not authorized", permission errors, and every other
#   OperationalError, ProgrammingError, DataError, InternalError or
#   NotSupportedError this list does not name.
_CORRUPTION_MESSAGE_FRAGMENTS = (
    "database disk image is malformed",
    "file is not a database",
    "file is encrypted or is not a database",
    "malformed database schema",
    "unsupported file format",
)
_SCHEMA_DAMAGE_MESSAGE_FRAGMENTS = ("no such table", "no such column")


def _quarantine_is_warranted(cause):
    """True only when `cause` is evidence the store FILE is damaged. See the
    note above for the exact conditions on each side of the line. Fails
    SAFE: an unrecognized error returns False, so the destructive action
    requires a positive reason rather than the absence of one."""
    if not isinstance(cause, sqlite3.Error):
        return True
    if type(cause) is sqlite3.DatabaseError:
        return True
    msg = str(cause).lower()
    if any(frag in msg for frag in _CORRUPTION_MESSAGE_FRAGMENTS):
        return True
    if isinstance(cause, sqlite3.OperationalError):
        return any(frag in msg for frag in _SCHEMA_DAMAGE_MESSAGE_FRAGMENTS)
    return False


def _exec(store, sql, params=()):
    """The ONE place any SQL statement runs against a Store's connection
    (GATE 4): Store.__init__ only probed the schema at OPEN time, so damage
    on a later page opened fine and leaked a raw sqlite3.DatabaseError out
    of claim(), dump(), and verify(), unquarantined, exit 1. Every query in
    this module routes through here so the same split applies everywhere:
    a transient busy/locked OperationalError refuses 'db-busy'; any other
    DatabaseError goes to the store's quarantine entry point, which decides
    (FINDING 7) whether the evidence names a damaged FILE, in which case a
    writable store moves it aside, or an environment failure, in which case
    it is reported and the file is left untouched. A read-only store never
    moves anything either way. Structural schema damage such as a dropped
    table still quarantines (CRITICAL A: this is also the backstop for a
    table dropped from under an already-open connection, not only one
    caught at the next fresh open). sqlite3.IntegrityError is
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


# Every Store/ReadOnlyStore whose sqlite handle is currently open. This is the
# MECHANICAL STOP for the leak class behind the Windows CI failure (run 18,
# commit 7c2e0ec): that round fixed 12 known call sites by hand, and a
# hand-fixed call site is not a fixed class, because the 13th site is written
# by someone who never read the fix. The suite asserts this set is empty at
# teardown, so ANY future site that opens a store and abandons it fails the
# suite on every platform, not only on the one that happens to lock files.
#
# A WeakSet rather than a list, deliberately: a store that has been garbage
# collected no longer holds an OS handle (CPython closes the sqlite connection
# when it finalizes), so counting it would report a leak that cannot hurt
# anyone. What broke Windows was a store still REFERENCED and still open when
# the directory was removed, and that is exactly what stays visible here.
_OPEN_STORES = weakref.WeakSet()

# Discipline tracking, OFF by default. _OPEN_STORES tracks stores that are
# still alive, which turned out to be the wrong question: a store abandoned
# inside a test is freed the moment the test function returns, so by the time
# any external checker looks, the set is empty and the leak reports clean.
# That was measured, not assumed: a deliberately reinjected leak passed a
# liveness-based check.
#
# What matters is whether a store was ever closed, not whether it is still
# alive when someone asks. _UNCLOSED holds a STRONG reference, so an abandoned
# store stays visible after collection would have hidden it. It is opt-in
# precisely because strong references retain sqlite connections: the test
# runner sets _TRACK_UNCLOSED, and the shipping CLI never does, so normal use
# keeps exactly the memory profile it had before.
_TRACK_UNCLOSED = False
_UNCLOSED = set()


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
                "no store exists at %s; run `%s init` to create one"
                % (store_path(self.root), _cmd()),
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
        # FINDING 5 (2026-07-27): the write above is best effort and always
        # was; this VERIFIES git's real state, and it runs here on purpose,
        # AFTER the write (so the healthy case is made healthy first) and
        # BEFORE sqlite3.connect below (so a refusal happens while the
        # sensitive database still does not exist, or still has not been
        # touched). An empty .brothermode/ directory may be left behind by
        # a refusal, exactly as the symlink and hardlink refusals above
        # already do; git does not track empty directories, so it carries
        # nothing.
        _refuse_if_git_can_commit_store(self.root)
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
            _OPEN_STORES.add(self)
            if _TRACK_UNCLOSED:
                _UNCLOSED.add(self)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=%d" % int(busy_timeout_ms))
            conn.execute("PRAGMA foreign_keys=ON")
            if pre_existing:
                # migrate=True: this is the WRITABLE store, the only path
                # allowed to raise an older store's schema. ReadOnlyStore keeps
                # the safe default and refuses instead.
                self._verify_schema_or_raise(migrate=True)
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
            # instance) is NOT transient, and goes to the quarantine entry
            # point instead of giving retry advice that can never work (see
            # _is_transient_busy_error). FINDING 7: reaching that entry
            # point is no longer the same thing as being moved; only named
            # evidence of a damaged file moves anything, and only from a
            # class that has write authority.
            if not _is_transient_busy_error(e):
                self._quarantine_and_raise(e)
            if self.conn is not None:
                try:
                    self.conn.close()
                except Exception:
                    pass
                self.conn = None
                _UNCLOSED.discard(self)
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
        # A brand new store is created directly at SCHEMA_VERSION, never at 1
        # and then migrated: one less path to get wrong. The learning tables
        # come from the SAME _LEARNING_DDL text the migration runs, so a fresh
        # store and a migrated store cannot drift apart.
        if SCHEMA_VERSION >= 2:
            self.conn.executescript(_LEARNING_DDL)
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
        # Same reasoning as the line above, for the learning tables: an index
        # living only inside a migration is a silent no-op for any store that
        # migrated before the index was added. Guarded on the tables actually
        # existing, so this stays inert while SCHEMA_VERSION is 1.
        if SCHEMA_VERSION >= 2:
            self.conn.executescript(_LEARNING_INDEX_DDL)

    def _verify_schema_or_raise(self, migrate=False):
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
        exactly, or this quarantines rather than silently repairing.

        VERSION IS READ FIRST, tables second (correction-learning Loop 1,
        2026-07-28). The original order checked _TABLES presence BEFORE the
        version, which was correct while only one schema had ever existed and
        becomes destructive the moment a second one does: a perfectly healthy
        schema-1 store, opened by a schema-2 binary, is missing the schema-2
        tables by definition, so it was quarantined before the version check
        could route it to a migration. Quarantining a store whose only problem
        is that it predates an upgrade is data loss dressed as caution.

        Four outcomes, and only one of them quarantines:
          * version matches -> verify this version's tables, as before;
          * version is a KNOWN older one -> verify THAT version's tables, then
            migrate if this caller may write, or raise a clear "needs
            migration" refusal if it may not (a read-only diagnostic must never
            migrate, and must never quarantine for this either);
          * version is NEWER than this binary -> refuse and say so. The store
            is fine; the binary is old. Touching it would be the damage.
          * version is missing, unparseable, or an unknown older one -> that is
            genuine corruption or an unsupported downgrade, and quarantines.

        migrate=False is the SAFE default so that any caller which forgets to
        opt in gets the refusal rather than a surprise write. ReadOnlyStore
        borrows this method unbound and therefore inherits that default."""
        found = {r["name"] for r in self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        row = self.conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        found_version = row["value"] if row is not None else None
        if found_version is None:
            self._quarantine_and_raise(
                ValueError("existing store has no schema_version row in meta"))
        try:
            fv = int(found_version)
        except (TypeError, ValueError):
            self._quarantine_and_raise(
                ValueError("existing store schema_version is not an integer: %r"
                           % (found_version,)))
            return
        if fv > SCHEMA_VERSION:
            # Deliberately NOT a quarantine. Moving a newer, healthy store
            # aside because an older binary opened it would destroy exactly the
            # data the newer binary was looking after.
            self._refuse_without_quarantine(
                "store schema_version is %d but this BrotherMode understands at "
                "most %d. Upgrade BrotherMode; do not downgrade the store. "
                "Nothing was touched." % (fv, SCHEMA_VERSION))
        expected = _TABLES_BY_VERSION.get(fv)
        if expected is None:
            self._quarantine_and_raise(
                ValueError("existing store schema_version is %d, which this "
                           "BrotherMode has no migration path from (known: %s)"
                           % (fv, ", ".join(str(k) for k in sorted(_TABLES_BY_VERSION)))))
            return
        missing = sorted(t for t in expected if t not in found)
        if missing:
            self._quarantine_and_raise(
                ValueError("existing store (schema %d) is missing expected "
                           "table(s): %s" % (fv, ", ".join(missing))))
        if fv == SCHEMA_VERSION:
            return
        # A known older version, structurally intact. Migrate, or refuse
        # clearly if this caller is not allowed to write.
        if not migrate:
            self._refuse_without_quarantine(
                "store is at schema %d and this BrotherMode is at %d. A "
                "read-only command cannot migrate it. Run any normal "
                "BrotherMode command (for example `verify` through the writable "
                "path, or `claim`) once to migrate, then retry. Nothing was "
                "touched." % (fv, SCHEMA_VERSION))
        self._migrate_from(fv)

    def _refuse_without_quarantine(self, message):
        """Refuse an open WITHOUT moving the store aside, closing the handle on
        the way out.

        Quarantine is for a DAMAGED store. A store that is merely newer than
        this binary, or merely older and awaiting migration, is undamaged, and
        moving it would be the only data loss in the situation. But a refusal
        still has to close the connection it opened: the leak detector in
        test_bm_store.py exists because an unclosed handle passes on POSIX and
        fails on Windows, which is how it reached CI run 18 undetected."""
        try:
            self.close()
        except Exception:
            pass
        raise StoreCorrupt(message)

    def _migrate_from(self, from_version):
        """Walk the migration chain from `from_version` up to SCHEMA_VERSION.

        Three properties, each a named requirement rather than a preference,
        and each calibrated by a test:

        BACKED UP FIRST. A copy of the store is written through sqlite's own
        backup API before a single DDL statement runs. A filesystem copy is not
        equivalent: with WAL enabled, recent committed writes can still live in
        the -wal sidecar, so copying the main file alone can produce a backup
        missing the newest records. The backup API checkpoints for us.

        ONE EXCLUSIVE TRANSACTION, AND THE VERSION MOVES LAST. Every table and
        index is created, and only then is meta.schema_version updated, all
        inside BEGIN EXCLUSIVE. An interruption anywhere rolls the whole thing
        back and leaves the store at its old version, structurally untouched
        and re-runnable. This ordering is what makes a half-migration
        impossible, which matters because _verify_schema_or_raise checks that
        expected tables are PRESENT and deliberately does not check that no
        others exist: a half-created table set with an already-bumped version
        would otherwise pass verification and look healthy.

        IDEMPOTENT. Every statement is CREATE ... IF NOT EXISTS, so running the
        migration twice is a no-op rather than an error."""
        backup_path = "%s.pre-schema%d-migration" % (self.path, SCHEMA_VERSION)
        try:
            bconn = sqlite3.connect(backup_path)
            try:
                self.conn.backup(bconn)
            finally:
                bconn.close()
            _chmod_best_effort(backup_path, 0o600)
        except (sqlite3.Error, OSError, AttributeError) as exc:
            # Fail CLOSED. A migration whose backup did not land is exactly the
            # operation nobody should be allowed to run unattended.
            self._refuse_without_quarantine(
                "refusing to migrate from schema %d: the pre-migration backup "
                "could not be written to %s (%s). Nothing was changed."
                % (from_version, backup_path, exc))
        version = from_version
        try:
            self.conn.execute("BEGIN EXCLUSIVE")
            while version < SCHEMA_VERSION:
                step = _MIGRATIONS.get(version)
                if step is None:
                    raise StoreCorrupt(
                        "no migration registered from schema %d to %d"
                        % (version, version + 1))
                step(self.conn)
                version += 1
            # LAST, inside the same transaction: see the docstring.
            self.conn.execute(
                "UPDATE meta SET value = ? WHERE key = 'schema_version'",
                (str(SCHEMA_VERSION),))
            self.conn.execute("COMMIT")
        except BaseException:
            try:
                self.conn.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            # Close before re-raising. Store.__init__ only catches sqlite3
            # errors, so anything else raised in here escapes construction with
            # the connection still open, and the caller has no object to close
            # because __init__ never returned one. On POSIX that is invisible;
            # on Windows the leaked handle makes the store file undeletable and
            # unreopenable. Caught by the suite's leak detector while writing
            # test_calibrated_interrupted_migration_rolls_back_completely.
            try:
                self.close()
            except Exception:
                pass
            raise
        # Re-verify from scratch: the migration CLAIMS to have produced a
        # schema-N store, and this proves it rather than trusting it. Any
        # shortfall now is genuine corruption, so the quarantine path is right.
        self._verify_schema_or_raise(migrate=False)

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
        on the connection's own handle, not a sidecar file.

        FINDING 7: this is THE MOVER, and only a class with write authority
        can reach it. ReadOnlyStore used to call it verbatim (one line:
        `return Store._quarantine_and_raise(self, cause)`), so a read-only
        health check could move the real database; it now OVERRIDES this
        entry point and raises instead, which makes the containment
        structural rather than a boolean somebody has to remember to check.
        The classification guard below is the second half of the same fix:
        even with write authority, only NAMED evidence of a damaged file
        may move it (see _quarantine_is_warranted)."""
        if not _quarantine_is_warranted(cause):
            self.close()
            raise StoreCorrupt(
                "%s could not be read as a SQLite database (%s). That error "
                "does not name corruption or a not-a-database file, so it was "
                "treated as an environment problem (a disk or permission or "
                "network-volume failure), NOT as a verdict on the file: "
                "nothing was moved, renamed, copied or deleted, and the store "
                "is still at its original path with its original bytes. Fix "
                "the underlying condition and re-run the command." % (self.path, cause))
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
                _UNCLOSED.discard(self)
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
            _UNCLOSED.discard(self)
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
            "run `%s init --acknowledge-quarantine` "
            "to start a fresh store." % (self.path, cause, qdir, _cmd()),
            quarantine_path=qdir)

    def close(self):
        """Idempotent: a second call finds self.conn already None and is a
        harmless no-op, so callers never need to guard a close-in-finally
        with an extra 'if store is not None and store.conn is not None'."""
        _OPEN_STORES.discard(self)
        _UNCLOSED.discard(self)
        if self.conn is not None:
            try:
                self.conn.close()
            finally:
                self.conn = None
                _UNCLOSED.discard(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Windows CI defect (GitHub Actions run 18, commit 7c2e0ec, job
        # 'store (windows-latest, 3.x)'): callers that opened a Store and
        # never closed it left the sqlite3 handle open, which POSIX
        # tolerates silently but Windows enforces as a locked file, so a
        # later attempt to remove the containing directory raised
        # PermissionError. close() runs here regardless of how the with
        # block exits (return, break, or an exception in flight), which is
        # the whole reason to prefer this over a bare call at the end of a
        # function body.
        self.close()
        return False

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

    # ------------------------------------------------------------------
    # Correction learning (Loop 2). Every mutation below is transactional and
    # every one of them fails CLOSED: a refusal raises a named error and
    # changes nothing, rather than returning a soft failure a caller can
    # mistake for success.
    # ------------------------------------------------------------------

    def capture_learning_candidate(self, source_type, raw_text="", trigger="",
                                    action="", because="", domain="",
                                    scope_type="project", scope_key="",
                                    session_id="", record_uuid=None,
                                    source_ref=""):
        """Record an OBSERVATION. Never a rule.

        This is the only way text enters the learning system, and nothing it
        writes affects behaviour: a candidate is inert until a founder approves
        it (invariant L1). raw_text is stored through the existing secret
        scrubber and is additionally WITHHELD from dump (see
        _DUMP_WITHHELD_COLUMNS), because it holds verbatim founder words."""
        L = _learning()
        if source_type not in _CANDIDATE_SOURCE_TYPES:
            raise OwnershipRefused(
                "bad-source-type",
                "unknown source type %r (known: %s)"
                % (source_type, ", ".join(_CANDIDATE_SOURCE_TYPES)))
        scope_err = L.validate_scope(scope_type, scope_key)
        if scope_err:
            raise OwnershipRefused("bad-scope", scope_err)
        clean_raw = redact_text(raw_text or "")
        # LOOP 12: only raw_text used to be scrubbed. proposed_trigger,
        # proposed_action, proposed_because, proposed_domain and
        # proposed_scope_key went through normalize_text alone, so a secret
        # typed into --action or --trigger was written to sqlite in cleartext,
        # copied unscrubbed into learning_rule_versions at approval, and printed
        # in cleartext by rules, why and candidates. Same scrubber, every
        # founder-supplied field, at the one door text enters through.
        clean_trigger = _scrubbed_field(L, trigger)
        clean_action = _scrubbed_field(L, action)
        clean_because = _scrubbed_field(L, because)
        clean_domain = _scrubbed_field(L, domain)
        clean_scope_key = _scrubbed_field(L, scope_key)
        # Count, not a flag: how much was scrubbed is review-relevant, and it is
        # the only signal a reviewer gets that captured text was touched at all.
        nred = (clean_raw.count("[REDACTED]")
                + sum(t.count("[REDACTED]") for t in
                      (clean_trigger, clean_action, clean_because,
                       clean_domain, clean_scope_key)))
        cuuid = uuid.uuid4().hex
        # Hashed on what is actually STORED, so two captures that differ only
        # inside a masked secret are one candidate rather than two.
        chash = L.content_hash(clean_trigger, clean_action, scope_type,
                               clean_scope_key)
        with self._transaction():
            _exec(self,
                  "INSERT INTO learning_candidates (candidate_uuid, source_type, "
                  "source_session_id, source_record_uuid, source_ref, raw_text, "
                  "proposed_trigger, proposed_action, proposed_because, "
                  "proposed_domain, proposed_scope_type, proposed_scope_key, "
                  "status, content_hash, redaction_count, created_at) "
                  "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'pending',?,?,?)",
                  (cuuid, source_type, session_id or "", record_uuid,
                   redact_text(source_ref or ""), clean_raw,
                   clean_trigger, clean_action,
                   clean_because, clean_domain,
                   scope_type, clean_scope_key, chash, nred,
                   now_iso()))
        return self.get_learning_candidate(cuuid)

    def get_learning_candidate(self, prefix):
        rows = _exec(self, "SELECT * FROM learning_candidates "
                           "WHERE candidate_uuid LIKE ? ORDER BY created_at",
                     (prefix + "%",)).fetchall()
        return _one_or_refuse(rows, "candidate", prefix)

    def list_learning_candidates(self, status=None):
        if status:
            return [dict(r) for r in _exec(
                self, "SELECT * FROM learning_candidates WHERE status = ? "
                      "ORDER BY created_at", (status,)).fetchall()]
        return [dict(r) for r in _exec(
            self, "SELECT * FROM learning_candidates ORDER BY created_at").fetchall()]

    def import_correction_inbox(self, rows, scope_key=None, source_label="corrections.jsonl"):
        """Loop 4 backfill: promote rows from the GLOBAL capture inbox into THIS
        project's store as pending candidates. Imports nothing else, approves
        nothing, and touches the inbox file not at all.

        Architecture, per the founder's decision 3.1.3: the per-project store is
        the system of record and the vault's corrections.jsonl is a global
        capture inbox. Triage moves an inbox row into a project. Global scope is
        an explicit choice the founder makes at APPROVAL, never a default here,
        so an imported candidate lands project-scoped and stays that way until
        he says otherwise.

        IDEMPOTENT BY CONSTRUCTION. Identity is a property of the row itself
        (session id plus normalized text, bm_learning.inbox_identity), not of
        when the import ran, so running the backfill twice imports nothing the
        second time and no bookkeeping file has to be trusted to make that true.

        A row is deliberately imported with an EMPTY proposed action. The
        founder writes the rule at approval; approval refuses an empty action as
        non-atomic. So the automatic path cannot produce something approvable
        without him typing the rule, which is invariant L1 held up by the shape
        of the data rather than by a promise.

        `rows` are already-parsed dicts, so this method reads no file and the
        single-writer property of this module is unchanged. A row that parsed as
        valid JSON but is NOT an object (a bare string, a number, a list) is
        counted as malformed and skipped: the inbox file is edited by hand and
        by other tools, and a founder-facing backfill may not die on a traceback
        because one line was the wrong shape."""
        L = _learning()
        imported, skipped, flagged, malformed = [], 0, 0, 0
        # One pass to learn which WORDS are already here, folded for case and
        # whitespace. The previous version compared the stored text with a raw
        # SQL equality, so a restatement with sentence capitalization produced a
        # second unlinked candidate and no possible-duplicate note at all.
        echoes = {}
        for prior in _exec(self,
                           "SELECT candidate_uuid, raw_text FROM learning_candidates "
                           "WHERE source_type='detected_correction' "
                           "ORDER BY created_at").fetchall():
            echoes.setdefault(L.text_echo_key(prior["raw_text"]), prior["candidate_uuid"])
        with self._transaction():
            for row in rows or []:
                if not isinstance(row, dict):
                    malformed += 1
                    continue
                text = row.get("text") or ""
                if not L.normalize_text(text):
                    skipped += 1
                    continue
                session_id = (row.get("session_id") or "")
                chash = L.inbox_identity(session_id, text)
                dup = _exec(self,
                            "SELECT candidate_uuid FROM learning_candidates "
                            "WHERE content_hash=? AND source_type='detected_correction'",
                            (chash,)).fetchall()
                if dup:
                    skipped += 1
                    continue
                clean_raw = redact_text(text)
                # Same words, different session, whatever the capitalization or
                # spacing. NOT a silent drop: the founder repeating himself is
                # the strongest evidence there is, so it is imported and the
                # echo is written into the review note for him to judge.
                ekey = L.text_echo_key(clean_raw)
                echo = echoes.get(ekey)
                note = ""
                if echo:
                    flagged += 1
                    note = ("possible duplicate of candidate %s, same text from a "
                            "different session" % echo[:8])
                cuuid = uuid.uuid4().hex
                echoes.setdefault(ekey, cuuid)
                ref = "%s ts=%s project=%s" % (source_label, row.get("ts") or "?",
                                               row.get("project") or "?")
                _exec(self,
                      "INSERT INTO learning_candidates (candidate_uuid, source_type, "
                      "source_session_id, source_ref, raw_text, proposed_scope_type, "
                      "proposed_scope_key, status, content_hash, redaction_count, "
                      "created_at, review_note) "
                      "VALUES (?,'detected_correction',?,?,?,'project',?,'pending',?,?,?,?)",
                      (cuuid, session_id, ref[:500], clean_raw,
                       L.normalize_text(scope_key or os.path.basename(self.root)),
                       chash, clean_raw.count("[REDACTED]"), now_iso(), note[:500]))
                imported.append(cuuid)
        return {"imported": len(imported), "skipped": skipped,
                "possible_duplicates": flagged, "malformed": malformed,
                "candidate_uuids": imported}

    OUTCOME_SOURCE_TYPES = ("rework", "escaped_defect")

    def capture_outcome_candidate(self, source_type, record_prefix, artifact_ref="",
                                  summary="", session_id="", scope_key=None,
                                  detail="", reuse_duplicate=False):
        """Capture channel 3: a candidate derived from an OUTCOME rather than
        from something the founder typed.

        Rework (the same artifact redone) and an escaped defect (a problem found
        after a record was completed) are evidence that some preference was not
        followed. That evidence is worth reviewing, so it becomes a pending
        candidate carrying the work record it came from and the artifact it is
        about, which is what a reviewer needs to judge it.

        FAILS CLOSED. An unknown source type, an unresolvable record, or an
        artifact reference that can be neither given nor derived from the
        record's claims is a refusal that writes nothing. A candidate that
        cannot say WHICH work it came from is worse than no candidate.

        Like every other capture path this writes an EMPTY proposed action, so
        nothing here can become a rule without the founder writing it at
        approval. This method is not a detector: something that observed the
        rework calls it. Automatic detection of rework from the record stream is
        NOT built, and docs/NOT-FINALIZED.md says so rather than implying it."""
        L = _learning()
        if source_type not in self.OUTCOME_SOURCE_TYPES:
            raise OwnershipRefused(
                "bad-source-type",
                "outcome candidates are %s, not %r"
                % (" or ".join(self.OUTCOME_SOURCE_TYPES), source_type))
        rows = _exec(self, "SELECT * FROM records WHERE lifecycle_uuid LIKE ?",
                     ((record_prefix or "") + "%",)).fetchall()
        rec = _one_or_refuse(rows, "record", record_prefix or "")
        artifact = L.normalize_text(artifact_ref or "")
        if not artifact:
            claimed = [r["path"] for r in _exec(
                self, "SELECT path FROM claims WHERE lifecycle_uuid=? ORDER BY path",
                (rec["lifecycle_uuid"],)).fetchall()]
            artifact = ", ".join(claimed[:5])
        if not artifact:
            raise OwnershipRefused(
                "no-artifact",
                "record %s claims no path, so pass the artifact this is about"
                % rec["lifecycle_uuid"][:8])
        clean_raw = redact_text(summary or "")
        cuuid = uuid.uuid4().hex
        chash = L.content_hash(source_type, rec["lifecycle_uuid"], artifact, clean_raw)
        ref = "%s record=%s artifact=%s" % (source_type, rec["lifecycle_uuid"][:8], artifact)
        # `detail` carries a caller-supplied classifier (Loop 8 passes the
        # escaped defect's class). It joins the reference rather than the raw
        # text so it survives the dump withholding that hides raw_text, which
        # is what makes a defect class readable in a review without the
        # founder's verbatim words coming with it.
        detail = L.normalize_text(detail or "")
        if detail:
            ref = "%s %s" % (ref, detail)
        prior = _exec(self, "SELECT candidate_uuid FROM learning_candidates "
                            "WHERE content_hash=? AND source_type=? ORDER BY created_at "
                            "LIMIT 1", (chash, source_type)).fetchall()
        note = ""
        if prior:
            # Repeated rework on the same artifact is MORE evidence, not less,
            # so it is recorded and linked rather than dropped.
            note = ("possible duplicate of candidate %s, same outcome on the same "
                    "artifact" % prior[0]["candidate_uuid"][:8])
        if reuse_duplicate:
            # The grading caller (record_outcome_event) asks for this, and only
            # it does. A graded outcome event reported twice is ONE event: the
            # command re-run by hand, the hook that fired twice. Minting a
            # second candidate there made the weekly review's counts grow with
            # keystrokes, which is precisely the storage-growth-mistaken-for-
            # learning failure this loop exists to detect.
            #
            # Identity is the content hash (source type, record, artifact and
            # the founder's own summary) plus the full reference, so a defect
            # class that differs is a different event. A genuinely second
            # rework says so in its own words and gets its own candidate. Only
            # a PENDING candidate is reused: one already reviewed is a closed
            # decision, and a new event after it deserves its own review.
            same = _exec(self,
                "SELECT candidate_uuid FROM learning_candidates "
                "WHERE content_hash=? AND source_type=? AND source_ref=? "
                "AND status='pending' ORDER BY created_at LIMIT 1",
                (chash, source_type, ref[:500])).fetchall()
            if same:
                out = self.get_learning_candidate(same[0]["candidate_uuid"])
                out["reused_existing"] = True
                return out
        with self._transaction():
            _exec(self,
                  "INSERT INTO learning_candidates (candidate_uuid, source_type, "
                  "source_session_id, source_record_uuid, source_ref, raw_text, "
                  "proposed_scope_type, proposed_scope_key, status, content_hash, "
                  "redaction_count, created_at, review_note) "
                  "VALUES (?,?,?,?,?,?,'project',?,'pending',?,?,?,?)",
                  (cuuid, source_type, session_id or rec["session_id"] or "",
                   rec["lifecycle_uuid"], ref[:500], clean_raw,
                   L.normalize_text(scope_key or os.path.basename(self.root)),
                   chash, clean_raw.count("[REDACTED]"), now_iso(), note[:500]))
        out = self.get_learning_candidate(cuuid)
        out["reused_existing"] = False
        return out

    def learning_capture_metrics(self):
        """DESCRIPTIVE counts only, and named that way on purpose.

        Candidates detected, approved, rejected, how many carry a possible
        duplicate note, and which KIND of reason the founder gave when he
        rejected one. These are volumes, not accuracy: nothing here is a
        precision or recall number, because no labelled review set exists and
        calling a count an accuracy is the memory theatre the plan forbids.

        The false positive categories are buckets over the founder's own stated
        rejection reason (bm_learning.false_positive_category). A reason that
        matches no bucket counts as "other" rather than being pushed into one."""
        L = _learning()
        by_status, by_source = {}, {}
        for r in _exec(self, "SELECT status, COUNT(*) AS n FROM learning_candidates "
                             "GROUP BY status").fetchall():
            by_status[r["status"]] = r["n"]
        for r in _exec(self, "SELECT source_type, COUNT(*) AS n FROM learning_candidates "
                             "GROUP BY source_type").fetchall():
            by_source[r["source_type"]] = r["n"]
        dups = _exec(self, "SELECT COUNT(*) AS n FROM learning_candidates "
                           "WHERE review_note LIKE 'possible duplicate%'").fetchone()["n"]
        rules = _exec(self, "SELECT COUNT(*) AS n FROM learning_rules").fetchone()["n"]
        fp = {}
        for r in _exec(self, "SELECT review_note FROM learning_candidates "
                             "WHERE status='rejected'").fetchall():
            cat = L.false_positive_category(r["review_note"])
            fp[cat] = fp.get(cat, 0) + 1
        return {"candidates_by_status": by_status, "candidates_by_source": by_source,
                "possible_duplicates": dups, "rules_total": rules,
                "false_positive_reasons": fp,
                "note": "descriptive counts, not accuracy: there is no labelled review set"}

    def approve_learning_candidate(self, prefix, founder_ref, trigger=None,
                                    action=None, because=None, scope_type=None,
                                    scope_key=None, rule_type="preference",
                                    severity="soft", domain=None,
                                    atomicity_override="", conflict_override=""):
        """Promote a candidate into an approved rule. ATOMIC and FOUNDER-GATED.

        founder_ref is mandatory and free-form (a command invocation, a message
        reference). It exists so that invariant L1 is enforced by the schema
        path rather than by convention: there is NO code path that creates a
        rule without one, so a background hook cannot approve anything even if
        it wanted to. A model's own judgement is not a founder_ref, and nothing
        here checks that, which is stated honestly in docs rather than pretended
        away: the guarantee is that approval is an explicit, recorded, attributed
        act, not that a determined local process could not fake one.

        All five writes (rule, version 1, approval evidence, candidate status,
        resulting link) happen in ONE transaction. A failure part way leaves the
        candidate pending, never half approved."""
        L = _learning()
        if not (founder_ref or "").strip():
            raise OwnershipRefused("no-founder-ref", "approval requires an explicit founder reference; a rule with no "
                "recorded approver is exactly what invariant L1 forbids")
        cand = self.get_learning_candidate(prefix)
        if cand["status"] != "pending":
            raise OwnershipRefused("not-pending", "candidate %s is %r, only a pending candidate can be approved"
                % (cand["candidate_uuid"][:8], cand["status"]))
        # Scrubbed here as well as at capture: approval accepts NEW text typed
        # on the command line, so the candidate having been cleaned says nothing
        # about what the founder just passed in (LOOP 12).
        trig = _scrubbed_field(L, trigger if trigger is not None else cand["proposed_trigger"])
        act = _scrubbed_field(L, action if action is not None else cand["proposed_action"])
        why = _scrubbed_field(L, because if because is not None else cand["proposed_because"])
        stype = scope_type or cand["proposed_scope_type"]
        skey = _scrubbed_field(L, scope_key if scope_key is not None else cand["proposed_scope_key"])
        dom = _scrubbed_field(L, domain if domain is not None else cand["proposed_domain"])
        founder_ref = redact_text(founder_ref)
        if not trig or not act:
            raise OwnershipRefused("incomplete-rule", "a rule needs both a trigger and an action; got trigger=%r action=%r"
                % (trig, act))
        scope_err = L.validate_scope(stype, skey)
        if scope_err:
            raise OwnershipRefused("bad-scope", scope_err)
        problems = L.atomicity_problems(act)
        if problems and not atomicity_override.strip():
            raise OwnershipRefused("not-atomic", "this action looks like more than one rule (%s). Split it, or "
                "re-run with an explicit override reason. A compound rule cannot "
                "be graded: when the outcome is bad you cannot tell which half "
                "was wrong." % "; ".join(problems))
        # THE DONE GATE OF LOOP 6: there is no path to silently accumulate
        # contradictory active rules. Approval is the only door into the
        # injectable set, so the check belongs here rather than in a report the
        # founder has to remember to run. The refusal names the other rule and
        # the ways out; the founder may override, and the override is written
        # down as evidence AND as an edge, so the conflict stays visible in
        # `conflicts`, in retrieval and in verify rather than being settled by
        # having been forced through once.
        prospective = {"scope_type": stype, "scope_key": skey,
                       "trigger_text": trig, "action_text": act}
        found = self.conflicts_against(prospective)
        if not conflict_override.strip():
            if found["contradictions"]:
                other, v = found["contradictions"][0]
                raise OwnershipRefused(
                    "unresolved-contradiction",
                    "this would create a second injectable rule contradicting %s "
                    "(%s). Resolve it first: narrow one scope, supersede one, mark "
                    "one contradicted, or re-run with an explicit override reason. "
                    "Existing rule says: %s"
                    % (other["rule_uuid"][:8], "; ".join(v["reasons"]),
                       _learning().safe_display(other["action_text"], 120)))
            if found["duplicates"]:
                other, v = found["duplicates"][0]
                raise OwnershipRefused(
                    "duplicate-rule",
                    "rule %s already says this in the same scope (%s). A repeat is "
                    "evidence, not a second rule: merge the candidate into it, or "
                    "re-run with an explicit override reason if they really differ."
                    % (other["rule_uuid"][:8], "; ".join(v["reasons"])))
        ruuid = uuid.uuid4().hex
        ts = now_iso()
        with self._transaction():
            _exec(self,
                  "INSERT INTO learning_rules (rule_uuid, current_version, state, "
                  "rule_type, severity, scope_type, scope_key, founder_approved_at, "
                  "created_at, updated_at) VALUES (?,1,'approved',?,?,?,?,?,?,?)",
                  (ruuid, rule_type, severity, stype, skey, ts, ts, ts))
            _exec(self,
                  "INSERT INTO learning_rule_versions (rule_uuid, version, "
                  "trigger_text, action_text, because_text, domain, change_type, "
                  "change_reason, source_candidate_uuid, approved_by, created_at) "
                  "VALUES (?,1,?,?,?,?,'created',?,?, 'founder', ?)",
                  (ruuid, trig, act, why, dom,
                   ("founder approval: %s" % founder_ref)[:500],
                   cand["candidate_uuid"], ts))
            _exec(self,
                  "INSERT INTO learning_evidence (evidence_uuid, rule_uuid, "
                  "candidate_uuid, polarity, evidence_type, source_session_id, "
                  "source_ref, excerpt, created_at) "
                  "VALUES (?,?,?,'support','founder_approval',?,?,?,?)",
                  (uuid.uuid4().hex, ruuid, cand["candidate_uuid"],
                   cand["source_session_id"], founder_ref[:500],
                   redact_text(cand["raw_text"] or ""), ts))
            if problems:
                # The override is EVIDENCE, not a silent bypass.
                _exec(self,
                      "INSERT INTO learning_evidence (evidence_uuid, rule_uuid, "
                      "polarity, evidence_type, source_ref, excerpt, created_at) "
                      "VALUES (?,?,'neutral','manual_review',?,?,?)",
                      (uuid.uuid4().hex, ruuid, founder_ref[:500],
                       ("atomicity override: %s (flags: %s)"
                        % (redact_text(atomicity_override),
                           "; ".join(problems)))[:500], ts))
            if conflict_override.strip() and (found["contradictions"] or found["duplicates"]):
                _exec(self,
                      "INSERT INTO learning_evidence (evidence_uuid, rule_uuid, "
                      "polarity, evidence_type, source_ref, excerpt, created_at) "
                      "VALUES (?,?,'neutral','manual_review',?,?,?)",
                      (uuid.uuid4().hex, ruuid, founder_ref[:500],
                       ("conflict override: %s (against: %s)"
                        % (redact_text(conflict_override),
                           ", ".join(o["rule_uuid"][:8] for o, _v
                                     in found["contradictions"] + found["duplicates"])))[:500],
                       ts))
                for other, _v in found["contradictions"]:
                    _exec(self, "INSERT OR IGNORE INTO learning_edges (from_rule_uuid, "
                                "to_rule_uuid, relation, note, created_at) "
                                "VALUES (?,?,'contradicts',?,?)",
                          (ruuid, other["rule_uuid"],
                           L.normalize_text(conflict_override)[:500], ts))
                for other, _v in found["duplicates"]:
                    _exec(self, "INSERT OR IGNORE INTO learning_edges (from_rule_uuid, "
                                "to_rule_uuid, relation, note, created_at) "
                                "VALUES (?,?,'duplicate_of',?,?)",
                          (ruuid, other["rule_uuid"],
                           L.normalize_text(conflict_override)[:500], ts))
            _exec(self,
                  "UPDATE learning_candidates SET status='approved', reviewed_at=?, "
                  "resulting_rule_uuid=? WHERE candidate_uuid=?",
                  (ts, ruuid, cand["candidate_uuid"]))
        return self.get_learning_rule(ruuid)

    def reject_learning_candidate(self, prefix, reason):
        """Reject, KEEPING the evidence and the stated reason. A rejected
        candidate is a decision worth remembering: it is what stops the same
        suggestion being re-proposed forever."""
        if not (reason or "").strip():
            raise OwnershipRefused("no-reason", "rejection requires a reason")
        cand = self.get_learning_candidate(prefix)
        if cand["status"] != "pending":
            raise OwnershipRefused("not-pending", "candidate %s is %r, not pending" % (cand["candidate_uuid"][:8],
                                                     cand["status"]))
        with self._transaction():
            _exec(self, "UPDATE learning_candidates SET status='rejected', "
                        "reviewed_at=?, review_note=? WHERE candidate_uuid=?",
                  (now_iso(), _learning().normalize_text(reason)[:500],
                   cand["candidate_uuid"]))
        return self.get_learning_candidate(cand["candidate_uuid"])

    def get_learning_rule(self, prefix):
        rows = _exec(self, "SELECT r.*, v.trigger_text, v.action_text, "
                           "v.because_text, v.domain FROM learning_rules r "
                           "JOIN learning_rule_versions v "
                           "  ON v.rule_uuid = r.rule_uuid AND v.version = r.current_version "
                           "WHERE r.rule_uuid LIKE ?", (prefix + "%",)).fetchall()
        return _one_or_refuse(rows, "rule", prefix)

    def list_learning_rules(self, states=None, include_forgotten=False):
        """Rules with their CURRENT version's text joined on.

        Forgotten rules are excluded by default at the lowest level, so no
        caller has to remember to filter them: a tombstone that leaks its text
        through an ordinary list would defeat the point of forgetting."""
        sql = ("SELECT r.*, v.trigger_text, v.action_text, v.because_text, v.domain "
               "FROM learning_rules r JOIN learning_rule_versions v "
               "  ON v.rule_uuid = r.rule_uuid AND v.version = r.current_version")
        clauses, params = [], []
        if not include_forgotten:
            clauses.append("r.state != 'forgotten'")
        if states:
            clauses.append("r.state IN (%s)" % ",".join("?" * len(states)))
            params.extend(states)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY r.created_at"
        return [dict(r) for r in _exec(self, sql, tuple(params)).fetchall()]

    def edit_learning_rule(self, prefix, expected_version, trigger=None,
                            action=None, because=None, domain=None,
                            change_type="edited", change_reason=""):
        """Append a NEW version. Prior versions are never overwritten, so an
        application recorded against version 2 still says exactly what the model
        was shown (invariant L8).

        expected_version is the same optimistic-concurrency guard the rest of
        this store uses: a stale caller fails closed rather than clobbering."""
        L = _learning()
        rule = self.get_learning_rule(prefix)
        if int(expected_version) != int(rule["current_version"]):
            raise StaleIdentity(
                "expected version %s; rule %s is at version %s"
                % (expected_version, rule["rule_uuid"][:8], rule["current_version"]),
                current_version=rule["current_version"])
        # Same scrub as capture and approval: an edit is new founder text.
        trig = _scrubbed_field(L, trigger if trigger is not None else rule["trigger_text"])
        act = _scrubbed_field(L, action if action is not None else rule["action_text"])
        why = _scrubbed_field(L, because if because is not None else rule["because_text"])
        dom = _scrubbed_field(L, domain if domain is not None else rule["domain"])
        if not trig or not act:
            raise OwnershipRefused("incomplete-rule", "a rule needs both a trigger and an action")
        nv = int(rule["current_version"]) + 1
        ts = now_iso()
        with self._transaction():
            _exec(self,
                  "INSERT INTO learning_rule_versions (rule_uuid, version, "
                  "trigger_text, action_text, because_text, domain, change_type, "
                  "change_reason, approved_by, created_at) "
                  "VALUES (?,?,?,?,?,?,?,?, 'founder', ?)",
                  (rule["rule_uuid"], nv, trig, act, why, dom, change_type,
                   _scrubbed_field(L, change_reason)[:500], ts))
            _exec(self, "UPDATE learning_rules SET current_version=?, updated_at=? "
                        "WHERE rule_uuid=?", (nv, ts, rule["rule_uuid"]))
        return self.get_learning_rule(rule["rule_uuid"])

    def change_learning_rule_state(self, prefix, target, reason="",
                                    successor_prefix=None):
        """Move a rule between lifecycle states, refusing illegal moves and
        refusing the ones that need evidence they do not have.

        Two named refusals implement plan rules 6 and 8 directly: nothing
        reaches 'confirmed' or 'settled' without at least one SUPPORTING
        evidence row that is not the original approval, and nothing reaches
        'superseded' without a real successor plus its edge."""
        L = _learning()
        rule = self.get_learning_rule(prefix)
        err = L.state_transition_error(rule["state"], target)
        if err:
            raise OwnershipRefused("illegal-state-move", err)
        if target in ("confirmed", "settled"):
            n = _exec(self, "SELECT COUNT(*) AS n FROM learning_evidence "
                            "WHERE rule_uuid=? AND polarity='support' "
                            "AND evidence_type != 'founder_approval'",
                      (rule["rule_uuid"],)).fetchone()["n"]
            if not n:
                raise OwnershipRefused("no-supporting-evidence", "a rule cannot become %r on its approval alone; it needs at "
                    "least one independent supporting event. Approval is the "
                    "founder's intent, not evidence the rule worked." % target)
        successor = None
        if target == "superseded":
            if not successor_prefix:
                raise OwnershipRefused("no-successor", "supersession requires the rule that replaces this one")
            successor = self.get_learning_rule(successor_prefix)
            if successor["rule_uuid"] == rule["rule_uuid"]:
                raise OwnershipRefused("self-supersession", "a rule cannot supersede itself")
            # A cycle means no member of the loop is the current instruction,
            # because each one claims to have been replaced. The state machine
            # does not catch this on its own: a rule that is already superseded
            # may still be named as the SUCCESSOR of a third rule, which is how
            # a three-rule loop forms without any single step looking wrong.
            existing = [(e["from_rule_uuid"], e["to_rule_uuid"])
                        for e in self.list_learning_edges()
                        if e["relation"] == "supersedes"]
            if L.supersession_cycle(existing, successor["rule_uuid"], rule["rule_uuid"]):
                raise OwnershipRefused(
                    "supersession-cycle",
                    "rule %s already supersedes %s through other rules; adding this "
                    "would close a loop in which no rule is the current one"
                    % (rule["rule_uuid"][:8], successor["rule_uuid"][:8]))
            # A successor that cannot be retrieved is not a replacement, it is a
            # deletion wearing a replacement's words. Supersession means "this
            # instruction lives on over there", and the CLI prints exactly that,
            # so a forgotten, deprecated, contradicted or already superseded
            # successor would make the store contradict its own output while the
            # founder's live instruction went silent with nothing in its place.
            # Checked AFTER the cycle test on purpose: a loop is the more
            # structural fault and keeps its own named refusal.
            if successor["state"] not in L.INJECTABLE_STATES:
                raise OwnershipRefused(
                    "successor-cannot-speak",
                    "rule %s is %r, so it can never be retrieved, and superseding "
                    "%s with it would silence that instruction and put nothing in "
                    "its place. Supersede with a rule that can still speak (%s), "
                    "or deprecate this one instead."
                    % (successor["rule_uuid"][:8], successor["state"],
                       rule["rule_uuid"][:8], ", ".join(L.INJECTABLE_STATES)))
        ts = now_iso()
        with self._transaction():
            if successor is not None:
                _exec(self, "INSERT OR IGNORE INTO learning_edges (from_rule_uuid, "
                            "to_rule_uuid, relation, note, created_at) "
                            "VALUES (?,?,'supersedes',?,?)",
                      (successor["rule_uuid"], rule["rule_uuid"],
                       L.normalize_text(reason)[:500], ts))
                _exec(self, "UPDATE learning_rules SET superseded_by=? WHERE rule_uuid=?",
                      (successor["rule_uuid"], rule["rule_uuid"]))
            _exec(self, "UPDATE learning_rules SET state=?, updated_at=?, "
                        "forgotten_at=CASE WHEN ?='forgotten' THEN ? ELSE forgotten_at END "
                        "WHERE rule_uuid=?",
                  (target, ts, target, ts, rule["rule_uuid"]))
        return self.get_learning_rule(rule["rule_uuid"])

    def add_learning_evidence(self, rule_prefix, polarity, evidence_type,
                               excerpt="", session_id="", source_ref="",
                               record_uuid=None):
        """Attach an observation to a rule. This is how a rule earns its way to
        'confirmed': something happened that was not the founder saying yes."""
        rule = self.get_learning_rule(rule_prefix)
        with self._transaction():
            _exec(self,
                  "INSERT INTO learning_evidence (evidence_uuid, rule_uuid, polarity, "
                  "evidence_type, source_session_id, source_record_uuid, source_ref, "
                  "excerpt, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                  (uuid.uuid4().hex, rule["rule_uuid"], polarity, evidence_type,
                   session_id or "", record_uuid, source_ref or "",
                   redact_text(excerpt or ""), now_iso()))
        return self.list_learning_evidence(rule["rule_uuid"])

    def list_learning_evidence(self, rule_prefix):
        rule = self.get_learning_rule(rule_prefix)
        return [dict(r) for r in _exec(
            self, "SELECT * FROM learning_evidence WHERE rule_uuid=? "
                  "ORDER BY created_at", (rule["rule_uuid"],)).fetchall()]

    # -----------------------------------------------------------------
    # Loop 6: the conflict graph.
    #
    # learning_edges existed from Loop 1 and nothing wrote to it, which is a
    # standing invitation to build half a feature against an empty table. From
    # here it is the record of how rules relate: what duplicates what, what
    # contradicts what, and what replaced what.
    #
    # THE RULE THAT GOVERNS ALL OF IT: this code DESCRIBES conflicts and
    # REFUSES to let one accumulate silently. It never decides which rule
    # wins. Every resolution below is executed on the founder's instruction and
    # recorded with a reason.
    # -----------------------------------------------------------------

    def list_learning_edges(self, rule_prefix=None):
        """Edges, optionally only the ones touching one rule (either end)."""
        if rule_prefix:
            rule = self.get_learning_rule(rule_prefix)
            return [dict(r) for r in _exec(
                self, "SELECT * FROM learning_edges WHERE from_rule_uuid=? "
                      "OR to_rule_uuid=? ORDER BY created_at",
                (rule["rule_uuid"], rule["rule_uuid"])).fetchall()]
        return [dict(r) for r in _exec(
            self, "SELECT * FROM learning_edges ORDER BY created_at").fetchall()]

    def link_learning_rules(self, from_prefix, to_prefix, relation, note=""):
        """Record how two rules relate.

        'supersedes' is deliberately NOT accepted here. Supersession is not a
        note about two rules, it is a state change on one of them, and letting
        a plain link write half of it would leave a rule claiming to be
        replaced while it is still being injected. Use
        change_learning_rule_state, which does both in one transaction."""
        L = _learning()
        if relation not in L.RELATIONS:
            raise OwnershipRefused(
                "bad-relation", "unknown relation %r (known: %s)"
                % (relation, ", ".join(L.RELATIONS)))
        if relation == "supersedes":
            raise OwnershipRefused(
                "use-supersede",
                "a supersedes edge is written by supersession itself, so the edge "
                "and the state change can never disagree; supersede the rule "
                "instead of linking it")
        a = self.get_learning_rule(from_prefix)
        b = self.get_learning_rule(to_prefix)
        if a["rule_uuid"] == b["rule_uuid"]:
            raise OwnershipRefused(
                "self-edge", "a rule cannot be linked to itself (%s)"
                % a["rule_uuid"][:8])
        ts = now_iso()
        with self._transaction():
            _exec(self, "INSERT OR IGNORE INTO learning_edges (from_rule_uuid, "
                        "to_rule_uuid, relation, note, created_at) VALUES (?,?,?,?,?)",
                  (a["rule_uuid"], b["rule_uuid"], relation,
                   L.normalize_text(note)[:500], ts))
        return [e for e in self.list_learning_edges(a["rule_uuid"])
                if e["to_rule_uuid"] == b["rule_uuid"] and e["relation"] == relation][0]

    def merge_learning_candidate(self, candidate_prefix, rule_prefix, reason=""):
        """Fold a DUPLICATE candidate into the rule it repeats, as evidence.

        The plan's duplicate behaviour, implemented literally: a repeat of an
        existing rule should strengthen that rule, not create a second copy of
        it, and the new source event must survive. So the candidate's own text
        becomes a founder_quote evidence row on the existing rule, and the
        candidate is marked 'merged' pointing at the rule it went into. Nothing
        is deleted and the provenance chain still ends at a source event.

        Worth stating: that evidence row is a SUPPORT row that is not a
        founder_approval, so a founder repeating himself is exactly the
        independent evidence a rule needs to reach 'confirmed'. That is the
        intended meaning, not a side effect."""
        cand = self.get_learning_candidate(candidate_prefix)
        if cand["status"] != "pending":
            raise OwnershipRefused(
                "not-pending", "candidate %s is %r, only a pending candidate can be merged"
                % (cand["candidate_uuid"][:8], cand["status"]))
        rule = self.get_learning_rule(rule_prefix)
        L = _learning()
        ts = now_iso()
        excerpt = cand["raw_text"] or cand["proposed_action"] or ""
        with self._transaction():
            _exec(self,
                  "INSERT INTO learning_evidence (evidence_uuid, rule_uuid, "
                  "candidate_uuid, polarity, evidence_type, source_session_id, "
                  "source_record_uuid, source_ref, excerpt, created_at) "
                  "VALUES (?,?,?,'support','founder_quote',?,?,?,?,?)",
                  (uuid.uuid4().hex, rule["rule_uuid"], cand["candidate_uuid"],
                   cand["source_session_id"], cand["source_record_uuid"],
                   ("merged into %s: %s" % (rule["rule_uuid"][:8], reason))[:500],
                   redact_text(excerpt), ts))
            _exec(self, "UPDATE learning_candidates SET status='merged', reviewed_at=?, "
                        "review_note=?, resulting_rule_uuid=? WHERE candidate_uuid=?",
                  (ts, L.normalize_text(reason)[:500], rule["rule_uuid"],
                   cand["candidate_uuid"]))
        return self.get_learning_rule(rule["rule_uuid"])

    def _conflict_side(self, rule):
        """One side of a reported conflict, in DISPLAY form.

        This is the redaction boundary for conflict output. It carries the
        rule's own trigger and action, which the founder wrote and approved,
        and nothing else: no candidate raw_text, no evidence excerpt, no
        source reference. Conflict reports get read out loud and pasted into
        notes, and the verbatim capture text is the most sensitive column in
        the store."""
        L = _learning()
        return {"rule_uuid": rule["rule_uuid"], "state": rule["state"],
                "scope": L.safe_scope(rule["scope_type"], rule["scope_key"]),
                "severity": rule["severity"],
                "trigger": L.safe_display(rule["trigger_text"], 160),
                "action": L.safe_display(rule["action_text"], 160)}

    def learning_conflicts(self):
        """Conflicts between rules that CAN currently speak.

        Only injectable states are compared. A deprecated, superseded,
        contradicted or forgotten rule cannot reach a session, so it is history
        rather than a live conflict, and reporting it as one would train the
        founder to ignore this output.

        A conflict counts if it was DETECTED lexically or DECLARED by the
        founder with `link a contradicts b`. Declared always wins: the detector
        cannot see "use tabs" against "use spaces", and the founder can.

        Pairwise, O(n squared) over injectable rules. That is tens of rows on a
        real store; if it ever stops being tens, the fix is an index, not a
        silent cap on how many conflicts get reported."""
        L = _learning()
        rules = self.list_learning_rules(states=L.INJECTABLE_STATES)
        declared = {}
        for e in self.list_learning_edges():
            if e["relation"] in ("contradicts", "duplicate_of"):
                declared[(e["from_rule_uuid"], e["to_rule_uuid"])] = e["relation"]
        out = {"contradictions": [], "duplicates": []}
        for i in range(len(rules)):
            for j in range(i + 1, len(rules)):
                a, b = rules[i], rules[j]
                v = L.conflict_verdict(a, b)
                rel = (declared.get((a["rule_uuid"], b["rule_uuid"]))
                       or declared.get((b["rule_uuid"], a["rule_uuid"])) or "")
                verdict = v["verdict"]
                if rel == "contradicts":
                    verdict = "contradiction"
                elif rel == "duplicate_of" and verdict != "contradiction":
                    verdict = "duplicate"
                if verdict not in ("contradiction", "duplicate"):
                    continue
                pair = {"a": self._conflict_side(a), "b": self._conflict_side(b),
                        "declared": rel, "detected": v["verdict"],
                        "scope_relation": v["scope_relation"],
                        "trigger_overlap": v["trigger_overlap"],
                        "action_relation": v["action_relation"],
                        "reasons": v["reasons"]}
                if verdict == "contradiction":
                    out["contradictions"].append(pair)
                else:
                    out["duplicates"].append(pair)
        return out

    def conflicts_against(self, proposed):
        """Conflicts a PROSPECTIVE rule would have with the injectable ones.

        Used by approval before anything is written, so a contradiction is
        refused at the door rather than discovered later by a founder reading a
        report. `proposed` is a plain dict with scope_type, scope_key,
        trigger_text and action_text."""
        L = _learning()
        found = {"contradictions": [], "duplicates": []}
        for other in self.list_learning_rules(states=L.INJECTABLE_STATES):
            v = L.conflict_verdict(proposed, other)
            if v["verdict"] == "contradiction":
                found["contradictions"].append((other, v))
            elif v["verdict"] == "duplicate":
                found["duplicates"].append((other, v))
        return found

    def resolve_learning_conflict(self, loser_prefix, other_prefix, how, reason=""):
        """Execute a founder's decision about ONE conflict, atomically.

        `how` names what happens to the rule the founder chose to stand down:
        superseded by the other one, marked contradicted, or deprecated. This
        method does not choose, rank, or suggest which rule that is. It exists
        so the state change and the edge that explains it land together, rather
        than leaving a rule silenced with no record of why."""
        if how == "superseded":
            return self.change_learning_rule_state(
                loser_prefix, "superseded", reason=reason,
                successor_prefix=other_prefix)
        if how not in ("contradicted", "deprecated"):
            raise OwnershipRefused(
                "bad-resolution",
                "unknown resolution %r (known: superseded, contradicted, deprecated)"
                % (how,))
        if not (reason or "").strip():
            raise OwnershipRefused(
                "no-reason", "resolving a conflict requires a reason; the next reader "
                "of this store has to be able to see why one rule stopped speaking")
        L = _learning()
        loser = self.get_learning_rule(loser_prefix)
        other = self.get_learning_rule(other_prefix)
        if loser["rule_uuid"] == other["rule_uuid"]:
            raise OwnershipRefused("self-edge", "a rule cannot resolve a conflict with itself")
        err = L.state_transition_error(loser["state"], how)
        if err:
            raise OwnershipRefused("illegal-state-move", err)
        ts = now_iso()
        with self._transaction():
            _exec(self, "INSERT OR IGNORE INTO learning_edges (from_rule_uuid, "
                        "to_rule_uuid, relation, note, created_at) "
                        "VALUES (?,?,'contradicts',?,?)",
                  (loser["rule_uuid"], other["rule_uuid"],
                   L.normalize_text(reason)[:500], ts))
            _exec(self, "UPDATE learning_rules SET state=?, updated_at=? WHERE rule_uuid=?",
                  (how, ts, loser["rule_uuid"]))
        return self.get_learning_rule(loser["rule_uuid"])

    # The checks learning_verify runs, named here so the CLI can print the list
    # it actually ran rather than a hand-written one that drifts from it.
    LEARNING_CHECKS = (
        "unresolved-contradiction", "broken-edge", "supersession-cycle",
        "dead-successor", "missing-current-version", "no-approval-evidence",
        "invalid-scope", "fts-drift", "application-without-version",
    )

    def learning_verify(self):
        """Deterministic integrity findings for the learning tables. READ ONLY.

        Same job `verify` does for the work records: state plainly whether the
        store is in a condition its own rules allow. Every finding names the
        rows involved. An empty finding list is the only thing that means clean,
        and the caller gets `ok` rather than having to interpret a count."""
        L = _learning()
        findings = []

        def add(code, detail, refs=()):
            findings.append({"code": code, "detail": detail, "refs": list(refs)})

        for pair in self.learning_conflicts()["contradictions"]:
            add("unresolved-contradiction",
                "rules %s and %s are both injectable and contradict (%s)"
                % (pair["a"]["rule_uuid"][:8], pair["b"]["rule_uuid"][:8],
                   "declared by the founder" if pair["declared"] else "detected"),
                (pair["a"]["rule_uuid"], pair["b"]["rule_uuid"]))
        for row in _exec(self,
                "SELECT e.from_rule_uuid AS f, e.to_rule_uuid AS t, e.relation AS rel "
                "FROM learning_edges e "
                "LEFT JOIN learning_rules a ON a.rule_uuid = e.from_rule_uuid "
                "LEFT JOIN learning_rules b ON b.rule_uuid = e.to_rule_uuid "
                "WHERE a.rule_uuid IS NULL OR b.rule_uuid IS NULL").fetchall():
            add("broken-edge",
                "edge %s %s %s points at a rule that no longer exists"
                % (row["f"][:8], row["rel"], row["t"][:8]), (row["f"], row["t"]))
        cyc = L.supersession_cycles(
            [(e["from_rule_uuid"], e["to_rule_uuid"])
             for e in self.list_learning_edges() if e["relation"] == "supersedes"])
        for ruuid in cyc:
            add("supersession-cycle",
                "rule %s sits on a supersession loop, so no rule in that loop is "
                "the current one" % ruuid[:8], (ruuid,))
        # Supersession is refused up front when the named successor cannot
        # speak, but a successor can go quiet AFTERWARDS: forgetting or
        # deprecating it is a legal move that leaves the rule it replaced
        # silenced with nothing standing in for it. Nothing else in this store
        # would ever mention that again, so the checker has to.
        states = dict((r["rule_uuid"], r["state"])
                      for r in self.list_learning_rules(include_forgotten=True))
        for ruuid, succ in sorted(
                (r["rule_uuid"], r["superseded_by"])
                for r in self.list_learning_rules(include_forgotten=True)
                if r["state"] == "superseded" and r["superseded_by"]):
            succ_state = states.get(succ)
            if succ_state is None or succ_state not in L.INJECTABLE_STATES:
                add("dead-successor",
                    "rule %s was superseded by %s, which is %s, so that "
                    "instruction is silenced with nothing in its place"
                    % (ruuid[:8], succ[:8],
                       "gone" if succ_state is None else repr(succ_state)),
                    (ruuid, succ))
        for row in _exec(self,
                "SELECT r.rule_uuid AS u FROM learning_rules r "
                "LEFT JOIN learning_rule_versions v "
                "  ON v.rule_uuid = r.rule_uuid AND v.version = r.current_version "
                "WHERE v.rule_uuid IS NULL").fetchall():
            add("missing-current-version",
                "rule %s names a current version that has no row" % row["u"][:8],
                (row["u"],))
        for row in _exec(self,
                "SELECT r.rule_uuid AS u FROM learning_rules r WHERE NOT EXISTS ("
                "  SELECT 1 FROM learning_evidence e WHERE e.rule_uuid = r.rule_uuid "
                "  AND e.evidence_type = 'founder_approval')").fetchall():
            add("no-approval-evidence",
                "rule %s has no founder_approval evidence, which invariant L1 requires "
                "of every rule" % row["u"][:8], (row["u"],))
        for r in self.list_learning_rules(include_forgotten=True):
            err = L.validate_scope(r["scope_type"], r["scope_key"])
            if err:
                add("invalid-scope", "rule %s: %s" % (r["rule_uuid"][:8], err),
                    (r["rule_uuid"],))
        for row in _exec(self,
                "SELECT a.application_uuid AS u FROM learning_applications a "
                "LEFT JOIN learning_rule_versions v "
                "  ON v.rule_uuid = a.rule_uuid AND v.version = a.rule_version "
                "WHERE v.rule_uuid IS NULL").fetchall():
            add("application-without-version",
                "application %s points at a rule version that does not exist"
                % row["u"][:8], (row["u"],))
        return {
            "ok": not findings,
            "findings": findings,
            "checks": list(self.LEARNING_CHECKS),
            "rules": len(self.list_learning_rules(include_forgotten=True)),
            "edges": len(self.list_learning_edges()),
            # Stated rather than silently skipped: the fts-drift check runs and
            # finds nothing because there is no FTS index in this schema to
            # drift from. Retrieval is lexical (see bm_learning's docstring).
            # When an index lands, this note becomes a real comparison and the
            # check name does not have to change.
            "notes": ["fts-drift: no FTS index exists in this schema, retrieval "
                      "mode is %s, so there is nothing to drift from"
                      % L.RETRIEVAL_MODE],
        }

    # How many gates may be carried PAST the caller's limit. Not a tuning
    # knob and deliberately small: a gate is carried because a safety rule
    # must not vanish behind a limit, and a list long enough to skim past
    # protects nobody. Gates beyond this are reported as a count, so the
    # founder is told they exist and can re-run with a larger limit.
    _GATE_CARRY_CAP = 3

    def retrieve_learning_rules(self, query, context=None, limit=5,
                                 include_reasons=True):
        """Rules relevant to a task, most relevant first, each able to say why.

        Read-only by contract: it writes nothing, records no application, and
        does not store the query. Recording an application is a separate,
        explicit call, so merely ASKING what applies can never pollute the
        outcome data (invariant L10 depends on that separation).

        Eligibility is a hard filter before ranking: only injectable states,
        and only rules whose scope the supplied context actually matches."""
        L = _learning()
        context = context or {}
        in_scope = [r for r in self.list_learning_rules(states=L.INJECTABLE_STATES)
                    if L.scope_matches(r["scope_type"], r["scope_key"], context)]
        # RELEVANCE FLOOR, added after a dogfood run on the founder's real
        # corrections surfaced a rule about pushing to GitHub in response to a
        # question about the colour of a breathing orb. Scope said eligible,
        # relevance was zero, and it was still returned. That is the
        # over-injection the dogfood review questions ask about, and a founder
        # who sees one irrelevant rule stops reading the relevant ones.
        #
        # A rule with NO shared term with the task is not retrieved. The single
        # exception is severity 'gate': a safety rule is exactly the thing that
        # must appear even when the person did not use its vocabulary, and
        # that asymmetry is the whole reason severity exists as a field.
        eligible = [r for r in in_scope
                    if r.get("severity") == "gate"
                    or L.lexical_overlap(query, r.get("trigger_text", ""),
                                         r.get("action_text", ""),
                                         r.get("because_text", ""),
                                         r.get("domain", "")) > 0]
        eligible.sort(key=lambda r: L.rank_key(r, query, context))
        # A LIMIT MAY NOT SILENCE A GATE, AND A GATE MAY NOT UNBOUND THE LIMIT.
        #
        # The relevance floor above already says a gate appears even when the
        # founder never used its vocabulary. Truncating the ranked list took
        # that straight back: enough chatty soft rules ahead of a gate at the
        # default limit, or limit=0 from any caller, and the safety rule
        # vanished with no line saying it had been dropped.
        #
        # The first attempt at that carried EVERY gate past the limit, which
        # removed the only bound injection had. A store with twelve gates then
        # returned twelve rules for every query at every limit, most of them at
        # relevance 0.0. That is the "unbounded returns, polluted context"
        # failure this tool claims to prevent, and it is how a founder learns
        # to stop reading the list.
        #
        # So: the limit binds ordinary rules, gates are carried past it, and
        # the carry itself is capped. Carried gates are the highest ranked
        # ones, and any gate the cap cuts is COUNTED AND REPORTED rather than
        # silently dropped. The disclosure is what makes the bound honest.
        n = max(0, int(limit))
        chosen = list(eligible[:n])
        carried = [r for r in eligible[n:] if r.get("severity") == "gate"]
        gates_omitted = max(0, len(carried) - self._GATE_CARRY_CAP)
        carried = carried[:self._GATE_CARRY_CAP]
        chosen.extend(carried)
        out = []
        for i, r in enumerate(chosen, 1):
            row = dict(r)
            row["rank"] = i
            if include_reasons:
                row["why"] = L.explain_rank(r, query, context)
            out.append(row)
        # CONFLICTS ARE SURFACED, NEVER SILENTLY RESOLVED (Loop 6).
        #
        # If two injectable rules contradict each other and one of them is about
        # to be shown, dropping the other or ranking it lower would be this tool
        # deciding which of the founder's instructions is the real one. It does
        # not get to do that. Both stay in the result, the pair is reported, and
        # the founder resolves it. The counterpart is included in full even when
        # it did not itself pass the relevance floor, because showing one side of
        # a contradiction is worse than showing neither.
        shown = set(r["rule_uuid"] for r in out)
        conflicts = []
        if shown:
            for pair in self.learning_conflicts()["contradictions"]:
                if (pair["a"]["rule_uuid"] in shown
                        or pair["b"]["rule_uuid"] in shown):
                    conflicts.append(pair)
        against = {}
        for pair in conflicts:
            au, bu = pair["a"]["rule_uuid"], pair["b"]["rule_uuid"]
            against.setdefault(au, set()).add(bu)
            against.setdefault(bu, set()).add(au)
        for row in out:
            row["conflicts_with"] = sorted(against.get(row["rule_uuid"], ()))
        return {"mode": L.RETRIEVAL_MODE, "results": out,
                "omitted": max(0, len(eligible) - len(chosen)),
                "eligible": len(eligible),
                "gates_carried": len(carried),
                "gates_omitted": gates_omitted,
                "gate_carry_cap": self._GATE_CARRY_CAP,
                "conflicts": conflicts}

    # -----------------------------------------------------------------
    # Loop 7: the application lifecycle.
    #
    # learning_applications existed from Loop 1 and nothing wrote to it, which
    # is the same standing invitation to build half a feature that the edges
    # table was before Loop 6. From here it is the record of what was surfaced
    # for a task, whether the acting model saw it, and what happened next.
    #
    # THREE PROPERTIES THIS CODE OWES, and each has a test:
    #
    # 1. Asking stays free. retrieve_learning_rules above is read only and
    #    stays that way. Recording is a SEPARATE call the caller opts into, so
    #    curiosity can never pollute the outcome data (invariant L10).
    # 2. Recording never breaks a retrieval. record_learning_applications
    #    returns the rules whatever happens to the write, and reports the write
    #    failure in a field rather than raising over the top of the answer the
    #    caller actually needed. A learning system that can make retrieval fail
    #    is worse than one that forgets.
    # 3. History is immutable. An application points at a rule VERSION, and
    #    every read joins that version's text, so editing a rule tomorrow can
    #    never rewrite what a model was shown yesterday (invariant L8).
    # -----------------------------------------------------------------

    # A result limit that means "every eligible rule". Named rather than a bare
    # number at the call site so nobody reads it as a tuning knob: the miss
    # check has to see the WHOLE eligible set, or the rules it fails to notice
    # are exactly the ones a small limit already hid.
    _ALL_ELIGIBLE = 100000

    def _resolve_record_uuid(self, prefix):
        """A work record prefix to its full uuid, or a named refusal.

        Deliberately loud rather than degraded: an application that silently
        loses its link to the work it belongs to is exactly the row that cannot
        be graded later, and a mistyped id is the caller's error, not a
        database failure to absorb."""
        if not prefix:
            return None
        rows = _exec(self, "SELECT lifecycle_uuid FROM records "
                           "WHERE lifecycle_uuid LIKE ?", (prefix + "%",)).fetchall()
        return _one_or_refuse(rows, "record", prefix)["lifecycle_uuid"]

    def record_learning_applications(self, query, context=None, limit=5,
                                      session_id="", record_prefix=None,
                                      shown_to_model=True, task_excerpt=None):
        """Retrieve rules for a task AND record that they were surfaced.

        One application row per returned rule VERSION. Idempotent per
        (task fingerprint, rule, version, session): running the same retrieval
        twice in one session records once and reports the rest as already
        present, because a model that re-reads its rules mid-task has not
        applied them twice.

        Idempotent does NOT mean the second call is discarded. The natural
        order of work is retrieve first, claim the work record second, then
        re-run with --record once there is something to link to. A row whose
        record_uuid is still missing therefore has it ATTACHED here and comes
        back counted as `linked`. Nothing else in this codebase can set that
        column afterwards, so dropping the flag would strand the row for good
        and permanently unlink the application from the work it belongs to.
        An application already pointing at a DIFFERENT record is refused
        rather than moved: completing a missing link is repair, changing an
        existing one is rewriting history.

        The retrieval result is returned whatever happens to the write. If the
        insert fails, `record_error` carries the reason and no partial rows
        survive, and the caller still gets the rules it asked for."""
        L = _learning()
        record_uuid = self._resolve_record_uuid(record_prefix)
        res = self.retrieve_learning_rules(query, context=context, limit=limit)
        out = dict(res)
        fingerprint = L.task_fingerprint(query)
        excerpt = query if task_excerpt is None else task_excerpt
        out["task_fingerprint"] = fingerprint
        out["session_id"] = session_id or ""
        out["recorded"] = 0
        out["already_recorded"] = 0
        out["linked"] = 0
        out["applications"] = []
        out["record_error"] = ""
        ts = now_iso()
        try:
            recorded, already, linked, uuids = 0, 0, 0, []
            with self._transaction():
                for r in res["results"]:
                    version = int(r["current_version"])
                    prior = _exec(self,
                        "SELECT application_uuid AS u, record_uuid AS rec "
                        "FROM learning_applications "
                        "WHERE task_fingerprint=? AND rule_uuid=? AND rule_version=? "
                        "AND session_id=?",
                        (fingerprint, r["rule_uuid"], version,
                         session_id or "")).fetchone()
                    if prior is not None:
                        already += 1
                        uuids.append(prior["u"])
                        if record_uuid is not None and prior["rec"] != record_uuid:
                            if prior["rec"]:
                                raise OwnershipRefused(
                                    "record-already-linked",
                                    "application %s already belongs to work "
                                    "record %s; a link is completed here, never "
                                    "moved, so close that application instead of "
                                    "re-pointing it at %s"
                                    % (prior["u"][:8], prior["rec"][:8],
                                       record_uuid[:8]))
                            _exec(self,
                                  "UPDATE learning_applications SET record_uuid=? "
                                  "WHERE application_uuid=?",
                                  (record_uuid, prior["u"]))
                            linked += 1
                        continue
                    au = uuid.uuid4().hex
                    scope_match = r["scope_type"] if r["scope_type"] == "global" \
                        else "%s:%s" % (r["scope_type"], r["scope_key"])
                    score = None
                    if isinstance(r.get("why"), dict):
                        score = r["why"].get("relevance")
                    _exec(self,
                          "INSERT INTO learning_applications (application_uuid, "
                          "rule_uuid, rule_version, session_id, record_uuid, "
                          "task_fingerprint, task_excerpt, retrieved_at, "
                          "retrieval_rank, retrieval_score, scope_match, "
                          "shown_to_model) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                          (au, r["rule_uuid"], version, session_id or "",
                           record_uuid, fingerprint,
                           redact_text(L.safe_display(excerpt, 500)), ts,
                           int(r["rank"]), score, scope_match,
                           1 if shown_to_model else 0))
                    recorded += 1
                    uuids.append(au)
            out["recorded"] = recorded
            out["already_recorded"] = already
            out["linked"] = linked
            out["applications"] = uuids
        except (OwnershipRefused, sqlite3.IntegrityError) as e:
            # PROPERTY 2 above, enforced here and nowhere else. The transaction
            # has already rolled back, so nothing partial survives; the caller
            # keeps the rules and is told plainly that the bookkeeping did not
            # land, instead of losing the answer to a bookkeeping problem.
            #
            # DELIBERATELY NARROW. A busy store and a constraint violation are
            # bookkeeping problems and are absorbed. StoreCorrupt is NOT caught
            # here and never will be: a damaged database is not a degraded
            # write to shrug off, and hiding it behind a successful-looking
            # retrieval is how a corrupt store keeps being used.
            out["record_error"] = "%s" % (e,)
        return out

    def get_learning_application(self, prefix):
        rows = _exec(self, "SELECT * FROM learning_applications "
                           "WHERE application_uuid LIKE ?", (prefix + "%",)).fetchall()
        return _one_or_refuse(rows, "application", prefix)

    def list_learning_applications(self, session_id=None, rule_prefix=None,
                                    record_prefix=None, task_fingerprint=None,
                                    disposition=None):
        """Applications, each carrying the rule text AS IT WAS APPLIED.

        The join is on (rule_uuid, rule_version), never on the rule's CURRENT
        version. That is invariant L8 made structural rather than promised: a
        rule edited after the fact cannot rewrite the history of what a model
        was actually shown."""
        sql = ("SELECT a.*, v.trigger_text, v.action_text, v.because_text, "
               "r.severity, r.rule_type, r.state AS rule_state "
               "FROM learning_applications a "
               "JOIN learning_rule_versions v "
               "  ON v.rule_uuid = a.rule_uuid AND v.version = a.rule_version "
               "JOIN learning_rules r ON r.rule_uuid = a.rule_uuid")
        clauses, params = [], []
        if session_id is not None:
            clauses.append("a.session_id = ?")
            params.append(session_id)
        if rule_prefix:
            clauses.append("a.rule_uuid = ?")
            params.append(self.get_learning_rule(rule_prefix)["rule_uuid"])
        if record_prefix:
            clauses.append("a.record_uuid = ?")
            params.append(self._resolve_record_uuid(record_prefix))
        if task_fingerprint:
            clauses.append("a.task_fingerprint = ?")
            params.append(task_fingerprint)
        if disposition:
            clauses.append("a.disposition = ?")
            params.append(disposition)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY a.retrieved_at, a.retrieval_rank"
        return [dict(r) for r in _exec(self, sql, tuple(params)).fetchall()]

    def set_application_disposition(self, prefix, disposition, reason="",
                                     verification_ref="", outcome=None,
                                     outcome_ref=""):
        """Close the loop on one application: was this rule followed, and why.

        Ignoring a gate or a substantial rule REQUIRES a reason. That refusal
        is the whole point of the field: a gate quietly skipped and never
        explained is the failure this mechanism exists to make visible, and a
        blank reason would let it pass as bookkeeping.

        The disposition also lands as evidence on the rule, so a rule that
        keeps being followed earns its way towards 'confirmed' and a rule that
        keeps being ignored carries the contradicting evidence to show for it.

        ONE evidence row per application, replaced in place, never
        accumulated. Evidence counts APPLICATIONS, not keystrokes. The earlier
        shape wrote a row whenever the disposition CHANGED, which stopped
        verbatim repeats and nothing else: alternating followed and ignored on
        a single application (the realistic "I closed that one wrong, fix it")
        manufactured unbounded support and contradict rows for a rule with
        exactly one application. That ledger is what the founder reads in
        `why` and what admits a rule to 'confirmed', so it may not be forgeable
        from one row. Moving to a disposition that asserts nothing (unknown or
        not_relevant) REMOVES the row rather than leaving behind a claim the
        application no longer makes."""
        L = _learning()
        if disposition not in L.DISPOSITIONS:
            raise OwnershipRefused(
                "bad-disposition", "unknown disposition %r (known: %s)"
                % (disposition, ", ".join(L.DISPOSITIONS)))
        if outcome is not None and outcome not in L.APPLICATION_OUTCOMES:
            raise OwnershipRefused(
                "bad-outcome", "unknown outcome %r (known: %s)"
                % (outcome, ", ".join(L.APPLICATION_OUTCOMES)))
        app = self.get_learning_application(prefix)
        rule = self.get_learning_rule(app["rule_uuid"])
        reason_text = L.normalize_text(reason or "")
        if L.disposition_needs_reason(disposition, rule["severity"],
                                      rule["rule_type"]) and not reason_text:
            raise OwnershipRefused(
                "no-ignore-reason",
                "rule %s is %s, so ignoring it needs a stated reason; say why "
                "and it is recorded rather than argued about later"
                % (rule["rule_uuid"][:8],
                   "a GATE rule" if rule["severity"] == "gate"
                   else "a substantial rule (%s)" % rule["rule_type"]))
        ts = now_iso()
        source_ref = "application %s" % app["application_uuid"][:8]
        # Derived from the application uuid rather than random, so the row this
        # application owns is addressable and there can only ever be one of it.
        evidence_uuid = uuid.uuid5(
            uuid.NAMESPACE_URL,
            "brothermode:application-evidence:%s" % app["application_uuid"]).hex
        with self._transaction():
            _exec(self,
                  "UPDATE learning_applications SET disposition=?, "
                  "disposition_reason=?, verification_ref=?, closed_at=? "
                  "WHERE application_uuid=?",
                  (disposition, reason_text[:500],
                   L.normalize_text(verification_ref or "")[:500],
                   None if disposition == "unknown" else ts,
                   app["application_uuid"]))
            if outcome is not None:
                _exec(self,
                      "UPDATE learning_applications SET outcome=?, outcome_ref=? "
                      "WHERE application_uuid=?",
                      (outcome, L.normalize_text(outcome_ref or "")[:500],
                       app["application_uuid"]))
            # Clear this application's claim before restating it. The second
            # match is by source_ref so rows written by the earlier
            # accumulating shape are cleaned up as each application is closed
            # again, without a migration. Two applications of the SAME rule
            # sharing an eight-hex prefix would over-delete by one row, which
            # deflates rather than inflates support: the safe direction, and
            # the only direction a stale ledger may err in.
            _exec(self,
                  "DELETE FROM learning_evidence WHERE evidence_uuid=? "
                  "OR (rule_uuid=? AND source_ref=?)",
                  (evidence_uuid, rule["rule_uuid"], source_ref))
            if disposition in ("followed", "ignored"):
                # Inlined rather than routed through add_learning_evidence
                # because _transaction is not reentrant and this must land in
                # the SAME transaction as the disposition it describes.
                _exec(self,
                      "INSERT INTO learning_evidence (evidence_uuid, rule_uuid, "
                      "polarity, evidence_type, source_session_id, "
                      "source_record_uuid, source_ref, excerpt, created_at) "
                      "VALUES (?,?,?,?,?,?,?,?,?)",
                      (evidence_uuid, rule["rule_uuid"],
                       "support" if disposition == "followed" else "contradict",
                       "verified_application" if disposition == "followed"
                       else "ignored_application",
                       app["session_id"], app["record_uuid"], source_ref,
                       redact_text(reason_text[:300]), ts))
        return self.get_learning_application(app["application_uuid"])

    def classify_learning_applications(self, session_id=None):
        """Grade what happened, refusing to grade what has no evidence.

        Two kinds of finding come out of here. Per application, the pure
        classifier in bm_learning decides from the row alone. Per TASK, this
        method can see something no single row can: a rule that was
        retrievable for that task, already approved when the task ran, and has
        no application row at all. That is a retrieval miss.

        Two honest limits, stated rather than discovered later:
          - The retrieval context is not stored, so it is reconstructed from
            the scope_match values that WERE recorded. A project rule missed by
            a task where no project-scoped rule was recorded stays invisible.
            That undercounts misses, which is the safe direction.
          - A rule that was eligible but fell below the caller's result limit
            counts as a miss too, and the finding says at what rank. It did not
            reach the acting model, which is what the class means, and calling
            it something softer would hide a limit that is set too low.
        A task whose excerpt was not kept returns not_decidable rather than a
        guess."""
        L = _learning()
        apps = self.list_learning_applications(session_id=session_id)
        graded, counts = [], {}
        for a in apps:
            cls, why = L.classify_application(a["disposition"],
                                              a["shown_to_model"], a["outcome"])
            row = dict(a)
            row["classification"] = cls
            row["classification_reason"] = why
            graded.append(row)
            counts[cls or "no_finding"] = counts.get(cls or "no_finding", 0) + 1
        tasks = {}
        for a in apps:
            tasks.setdefault((a["session_id"], a["task_fingerprint"]), []).append(a)
        misses, undecidable = [], []
        for (sid, fingerprint), group in sorted(tasks.items()):
            excerpt = ""
            for a in group:
                if a["task_excerpt"]:
                    excerpt = a["task_excerpt"]
                    break
            if not excerpt:
                undecidable.append({
                    "session_id": sid, "task_fingerprint": fingerprint,
                    "reason": "no task text was kept for this task, so what else "
                              "was retrievable cannot be reconstructed"})
                continue
            context = {}
            for a in group:
                if a["scope_match"] and ":" in a["scope_match"]:
                    kind, key = a["scope_match"].split(":", 1)
                    context[kind] = key
            when = min(a["retrieved_at"] for a in group)
            seen = set(a["rule_uuid"] for a in group)
            res = self.retrieve_learning_rules(excerpt, context=context,
                                                limit=self._ALL_ELIGIBLE)
            for r in res["results"]:
                if r["rule_uuid"] in seen:
                    continue
                if r["founder_approved_at"] > when:
                    # A rule the founder approved AFTER the task ran cannot
                    # have been missed by it. Without this the classifier would
                    # blame every past task for not knowing today's rules.
                    continue
                misses.append({
                    "session_id": sid, "task_fingerprint": fingerprint,
                    "rule_uuid": r["rule_uuid"], "rank": r["rank"],
                    # The task's own timestamp, so a review window can include
                    # or exclude this miss. A miss has no row of its own, and
                    # without this it would be undateable and would therefore
                    # appear in every window forever.
                    "task_retrieved_at": when,
                    "classification": "retrieval_miss",
                    "classification_reason":
                        "rule %s was approved before this task ran and ranks %d "
                        "of %d for it, but no application row exists, so it "
                        "never reached the acting model"
                        % (r["rule_uuid"][:8], r["rank"], res["eligible"])})
        counts["retrieval_miss"] = len(misses)
        return {"applications": graded, "retrieval_misses": misses,
                "not_decidable_tasks": undecidable, "counts": counts,
                "classes": list(L.FAILURE_CLASSES)}

    # -----------------------------------------------------------------
    # Loop 8: external grading.
    #
    # Everything above this line can be produced by the session being graded.
    # A model can retrieve its own rules, record its own applications and
    # close them 'followed', and the ledger would look excellent while the
    # founder's actual experience got worse. That is memory theatre with a
    # database behind it.
    #
    # The three signals here cannot be produced that way, and each is anchored
    # outside the grader's own say-so:
    #   REWORK            a work record that had to be done again.
    #   ESCAPED DEFECT    a defect found after that record was called done.
    #   REPEATED CORRECTION  the founder saying the same thing twice.
    #
    # None of them AUTO-APPROVES anything. A repeated correction produces
    # evidence, a graded application outcome, and a named loop failure. It
    # never promotes a candidate, never edits a rule, and never changes a
    # rule's state. Approval stays founder-only, here as everywhere.
    # -----------------------------------------------------------------

    # States where a repeated correction is a genuine loop failure. An
    # 'approved' rule has never been independently confirmed by anything, so a
    # correction repeating it is closer to first evidence than to a failure,
    # and grading it as a failure would manufacture findings out of rules that
    # were only just written.
    REPEAT_GRADED_STATES = ("confirmed", "settled")

    # A candidate's source translated into the evidence type it produces. The
    # mapping exists so a repeated correction carries the KIND of external
    # evidence it actually is, rather than everything landing as one generic
    # type nobody can filter later.
    _REPEAT_EVIDENCE_TYPES = {
        "rework": "rework",
        "escaped_defect": "escaped_defect",
        "explicit_correction": "founder_quote",
        "detected_correction": "founder_quote",
        "revealed_choice": "revealed_choice",
        "imported": "import_source",
    }

    def _applications_for_work(self, rule_uuid, record_uuid, session_id):
        """The applications of one rule inside one piece of work.

        The record link WINS whenever the outcome names a record. Session is a
        backstop and only a backstop, for the one case that produced it: an
        application recorded before the record was claimed carries a session
        and no record. Requiring both links would report a retrieval miss for
        work that demonstrably did retrieve the rule.

        Unioning the two, which is what this did until an adversarial pass
        drove two records through one session, is the opposite error and the
        worse one. A session holds many pieces of work. An outcome on record A
        would then grade every rule applied to record B as well, and a rule
        obeyed correctly in unrelated work came back as a bad_rule the founder
        was told to go and edit. An application that names a DIFFERENT record
        is not in this work, whatever session it shares.

        With no record on the outcome, session is all there is and the match
        degrades to it: that is honest, because nothing narrower exists."""
        out = []
        for a in self.list_learning_applications(rule_prefix=rule_uuid):
            if record_uuid:
                if a["record_uuid"] == record_uuid:
                    out.append(a)
                elif (session_id and not a["record_uuid"]
                      and a["session_id"] == session_id):
                    out.append(a)
            elif session_id and a["session_id"] == session_id:
                out.append(a)
        return out

    def _grade_outcome_link(self, cand, app, kind, ts, mark_outcome):
        """Write ONE application's share of an outcome event. Caller holds the
        transaction, because the evidence and the outcome it describes have to
        land together or not at all."""
        L = _learning()
        cls, why, polarity = L.classify_repeated_correction([app], True)
        if mark_outcome and app["outcome"] != mark_outcome:
            _exec(self,
                  "UPDATE learning_applications SET outcome=?, outcome_ref=? "
                  "WHERE application_uuid=?",
                  (mark_outcome,
                   ("%s candidate %s (was %s)"
                    % (mark_outcome, cand["candidate_uuid"][:8],
                       app["outcome"]))[:500],
                   app["application_uuid"]))
        ev = uuid.uuid5(
            uuid.NAMESPACE_URL,
            "brothermode:outcome-evidence:%s:%s"
            % (cand["candidate_uuid"], app["application_uuid"])).hex
        # Replaced in place rather than appended. The same outcome event
        # reported twice is one event, and letting it accumulate would let a
        # rule be argued into or out of 'confirmed' by repetition alone.
        _exec(self, "DELETE FROM learning_evidence WHERE evidence_uuid=?", (ev,))
        _exec(self,
              "INSERT INTO learning_evidence (evidence_uuid, rule_uuid, "
              "candidate_uuid, polarity, evidence_type, source_session_id, "
              "source_record_uuid, source_ref, excerpt, created_at) "
              "VALUES (?,?,?,?,?,?,?,?,?,?)",
              (ev, app["rule_uuid"], cand["candidate_uuid"], polarity,
               self._REPEAT_EVIDENCE_TYPES.get(kind, "manual_review"),
               app["session_id"], app["record_uuid"],
               ("%s candidate=%s application=%s rule_version=%d"
                % (kind, cand["candidate_uuid"][:8],
                   app["application_uuid"][:8], app["rule_version"]))[:500],
               redact_text(why[:300]), ts))
        return {"application_uuid": app["application_uuid"],
                "rule_uuid": app["rule_uuid"],
                "rule_version": app["rule_version"],
                "disposition": app["disposition"],
                "classification": cls, "classification_reason": why,
                "polarity": polarity, "evidence_uuid": ev}

    def record_outcome_event(self, kind, record_prefix, session_id="",
                             artifact_ref="", summary="", defect_class=""):
        """Record rework or an escaped defect AND link it to what was applied.

        Loop 4 already turned these into pending candidates. What was missing
        was the other half: which rules were in play when that work happened.
        Without the link the event is a note; with it, the event grades the
        rules that were supposed to prevent it.

        Every application of every rule inside that work record (or, when the
        record link is not there yet, that session) gets the outcome recorded
        against it and one evidence row pointing at the exact rule VERSION
        that was shown. The candidate stays PENDING: an escaped defect is
        evidence for review, never a rule.

        When nothing is linked, the result says so in `notes` and the counts
        stay at zero. It does not estimate, and it does not quietly imply the
        rules were fine.

        IDEMPOTENT for an identical event. Running the same command twice
        reuses the pending candidate the first run created and re-states the
        same evidence rows rather than adding more, so the weekly review
        counts events and not keystrokes. A second, genuinely different rework
        on the same artifact is described in different words and gets its own
        candidate."""
        L = _learning()
        if kind not in self.OUTCOME_SOURCE_TYPES:
            raise OwnershipRefused(
                "bad-source-type",
                "outcome events are %s, not %r"
                % (" or ".join(self.OUTCOME_SOURCE_TYPES), kind))
        detail = ""
        if defect_class:
            detail = "defect_class=%s" % L.normalize_text(defect_class)
        cand = self.capture_outcome_candidate(
            kind, record_prefix, artifact_ref=artifact_ref, summary=summary,
            session_id=session_id, detail=detail, reuse_duplicate=True)
        apps = []
        for a in self.list_learning_applications(
                record_prefix=cand["source_record_uuid"]):
            apps.append(a)
        seen = set(a["application_uuid"] for a in apps)
        # Session is the backstop for applications that have no record link
        # yet, and ONLY for those. An application naming a different record
        # belongs to different work, and grading it here would blame a rule
        # for an outcome it was never in. Same rule as _applications_for_work,
        # deliberately: the two must not be able to disagree about what "this
        # work" means.
        if cand["source_session_id"]:
            for a in self.list_learning_applications(
                    session_id=cand["source_session_id"]):
                if a["application_uuid"] in seen or a["record_uuid"]:
                    continue
                apps.append(a)
                seen.add(a["application_uuid"])
        ts = now_iso()
        graded = []
        with self._transaction():
            for a in sorted(apps, key=lambda x: x["application_uuid"]):
                graded.append(self._grade_outcome_link(cand, a, kind, ts, kind))
        notes = []
        if cand.get("reused_existing"):
            notes.append(
                "this is the same outcome already recorded as candidate %s, so "
                "it stays one event and no second candidate was written"
                % cand["candidate_uuid"][:8])
        if not graded:
            notes.append(
                "no rule application was recorded for that work, so no rule can "
                "be graded from this event: linkage not measured")
        counts = {}
        for g in graded:
            counts[g["classification"]] = counts.get(g["classification"], 0) + 1
        return {"kind": kind, "candidate": cand,
                "candidate_uuid": cand["candidate_uuid"],
                "record_uuid": cand["source_record_uuid"],
                "session_id": cand["source_session_id"],
                "artifact_ref": cand["source_ref"],
                "defect_class": L.normalize_text(defect_class or ""),
                "linked_applications": graded, "counts": counts,
                "notes": notes}

    def detect_repeated_correction(self, candidate_prefix, record=False):
        """Is this correction one the founder already gave us?

        Compares a candidate against the rules that are already CONFIRMED or
        SETTLED, and for every match says why that rule failed to prevent it:
        never retrieved, retrieved and skipped, retrieved into work it did not
        fit, or followed and wrong anyway. That distinction is the entire
        product claim. Incrementing a counter would tell the founder the same
        thing happened again and nothing at all about which part of the system
        to fix.

        READ ONLY unless `record` is set, deliberately mirroring retrieval:
        asking whether something repeats must never itself change the ledger,
        or the act of reviewing would manufacture the evidence being reviewed.

        Even with `record`, this APPROVES NOTHING. The candidate's status is
        untouched and no rule changes state."""
        L = _learning()
        cand = self.get_learning_candidate(candidate_prefix)
        parts = [cand["proposed_trigger"], cand["proposed_action"],
                 cand["proposed_because"], cand["proposed_domain"],
                 cand["raw_text"]]
        query = " ".join(p for p in parts if p).strip()
        context = {}
        if cand["proposed_scope_type"] != "global" and cand["proposed_scope_key"]:
            context[cand["proposed_scope_type"]] = cand["proposed_scope_key"]
        links_known = bool(cand["source_record_uuid"] or cand["source_session_id"])
        out = {"candidate_uuid": cand["candidate_uuid"],
               "candidate_status": cand["status"],
               "recorded": bool(record), "repeats": [], "unsettled_matches": [],
               "counts": {}, "notes": [],
               "classes": list(L.FAILURE_CLASSES)}
        if not query:
            out["notes"].append(
                "this candidate carries no text to compare, so whether it "
                "repeats an existing rule is not measured")
            return out
        res = self.retrieve_learning_rules(query, context=context,
                                            limit=self._ALL_ELIGIBLE)
        matches = []
        for r in res["results"]:
            if r["state"] in self.REPEAT_GRADED_STATES:
                matches.append(r)
            else:
                out["unsettled_matches"].append({
                    "rule_uuid": r["rule_uuid"], "state": r["state"],
                    "reason": "rule %s matches this correction but is %r, not "
                              "yet %s, so a repeat of it is first evidence "
                              "rather than a loop failure"
                              % (r["rule_uuid"][:8], r["state"],
                                 " or ".join(self.REPEAT_GRADED_STATES))})
        if not links_known:
            out["notes"].append(
                "this candidate names neither a session nor a work record, so "
                "every match below is not_decidable rather than blamed on a rule")
        ts = now_iso()
        findings = []
        for r in matches:
            apps = self._applications_for_work(
                r["rule_uuid"], cand["source_record_uuid"],
                cand["source_session_id"])
            cls, why, polarity = L.classify_repeated_correction(apps, links_known)
            findings.append({
                "rule_uuid": r["rule_uuid"], "rule_state": r["state"],
                "rule_version": r["current_version"],
                "classification": cls, "classification_reason": why,
                "polarity": polarity,
                "applications": [a["application_uuid"] for a in apps],
                "recorded": False})
            if not record:
                continue
            with self._transaction():
                for a in apps:
                    if a["outcome"] == "corrected_again":
                        continue
                    _exec(self,
                          "UPDATE learning_applications SET outcome=?, "
                          "outcome_ref=? WHERE application_uuid=?",
                          ("corrected_again",
                           ("corrected again by candidate %s (was %s)"
                            % (cand["candidate_uuid"][:8], a["outcome"]))[:500],
                           a["application_uuid"]))
                ev = uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    "brothermode:repeat-evidence:%s:%s"
                    % (cand["candidate_uuid"], r["rule_uuid"])).hex
                _exec(self, "DELETE FROM learning_evidence WHERE evidence_uuid=?",
                      (ev,))
                _exec(self,
                      "INSERT INTO learning_evidence (evidence_uuid, rule_uuid, "
                      "candidate_uuid, polarity, evidence_type, "
                      "source_session_id, source_record_uuid, source_ref, "
                      "excerpt, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                      (ev, r["rule_uuid"], cand["candidate_uuid"], polarity,
                       self._REPEAT_EVIDENCE_TYPES.get(cand["source_type"],
                                                        "manual_review"),
                       cand["source_session_id"], cand["source_record_uuid"],
                       ("repeated_correction candidate=%s rule_version=%d "
                        "class=%s" % (cand["candidate_uuid"][:8],
                                      int(r["current_version"]), cls))[:500],
                       redact_text(why[:300]), ts))
            findings[-1]["recorded"] = True
            findings[-1]["evidence_uuid"] = ev
        counts = {}
        for f in findings:
            counts[f["classification"]] = counts.get(f["classification"], 0) + 1
        out["repeats"] = findings
        out["counts"] = counts
        if not findings and not out["unsettled_matches"]:
            out["notes"].append(
                "no confirmed or settled rule matches this correction, so it "
                "does not repeat one this system already knows")
        return out

    def _repeat_evidence_pairs(self):
        """(candidate, rule) pairs that are genuinely a REPEAT of that rule.

        Two exclusions, each of which produced a wrong finding when driving the
        real CLI. 'founder_approval' evidence carries the candidate the rule
        was BORN from, and counting it would report every rule as repeating
        itself the moment it was approved. The same candidate reaching the same
        rule through some other evidence type is excluded for the same reason:
        a rule's own origin is not a correction of it."""
        rows = _exec(self,
            "SELECT candidate_uuid AS c, rule_uuid AS r, "
            "MIN(created_at) AS at FROM learning_evidence "
            "WHERE candidate_uuid IS NOT NULL AND rule_uuid IS NOT NULL "
            "AND evidence_type <> 'founder_approval' "
            "GROUP BY candidate_uuid, rule_uuid ORDER BY at").fetchall()
        out = []
        for row in rows:
            cand = self.get_learning_candidate(row["c"])
            if cand["resulting_rule_uuid"] == row["r"]:
                continue
            out.append({"c": row["c"], "r": row["r"], "at": row["at"]})
        return out

    def _window_start(self, window_days=None):
        """The ISO cutoff for a review window, or "" for no window.

        The clock lives here rather than in bm_learning, which stays pure, and
        rather than in the CLI, which would let two callers disagree about
        what 'the last 30 days' means."""
        if window_days is None:
            return ""
        delta = datetime.timedelta(days=float(window_days))
        return (datetime.datetime.now(datetime.timezone.utc)
                - delta).strftime("%Y-%m-%dT%H:%M:%SZ")

    def learning_loop_failures(self, window_days=None):
        """The honest weekly answer to 'is this actually learning?'.

        Every number here is a count of rows that exist. Nothing is estimated,
        nothing is projected, and anything the data cannot decide comes back
        under not_decidable or as a 'not measured' note instead of a figure.
        That restraint is the point: a plausible number nobody can trace is
        worse than an admitted gap, because the founder would act on it."""
        L = _learning()
        since = self._window_start(window_days)
        graded = self.classify_learning_applications()
        apps = [a for a in graded["applications"]
                if not since or a["retrieved_at"] >= since]
        misses = [m for m in graded["retrieval_misses"]
                  if not since or m.get("task_retrieved_at", "") >= since]
        by_class = {}
        for a in apps:
            if a["classification"]:
                by_class.setdefault(a["classification"], []).append(a)
        # Repeated corrections are RECOMPUTED from the application rows rather
        # than read back from a stored label. A stored class would go stale the
        # moment a disposition was corrected, and the founder correcting a
        # mistaken disposition is exactly the thing this report must not punish.
        repeats = []
        pairs = [p for p in self._repeat_evidence_pairs()]
        for p in pairs:
            if since and p["at"] < since:
                continue
            cand = self.get_learning_candidate(p["c"])
            rule = self.get_learning_rule(p["r"])
            links_known = bool(cand["source_record_uuid"]
                               or cand["source_session_id"])
            work = self._applications_for_work(
                rule["rule_uuid"], cand["source_record_uuid"],
                cand["source_session_id"])
            cls, why, polarity = L.classify_repeated_correction(work, links_known)
            repeats.append({
                "candidate_uuid": cand["candidate_uuid"],
                "source_type": cand["source_type"],
                "rule_uuid": rule["rule_uuid"], "rule_state": rule["state"],
                "settled": rule["state"] in self.REPEAT_GRADED_STATES,
                "is_correction":
                    cand["source_type"] not in self.OUTCOME_SOURCE_TYPES,
                "classification": cls, "classification_reason": why,
                "polarity": polarity, "at": p["at"]})
        never, always_irrelevant = [], []
        for rule in self.list_learning_rules():
            rows = self.list_learning_applications(rule_prefix=rule["rule_uuid"])
            if not rows:
                never.append({"rule_uuid": rule["rule_uuid"],
                              "state": rule["state"],
                              "approved_at": rule["founder_approved_at"]})
            elif all(x["disposition"] == "not_relevant" for x in rows):
                always_irrelevant.append({"rule_uuid": rule["rule_uuid"],
                                          "applications": len(rows)})
        linked_candidates = set(p["c"] for p in pairs)
        outcome_linked, unattributed = [], []
        for c in self.list_learning_candidates():
            if c["source_type"] not in self.OUTCOME_SOURCE_TYPES:
                continue
            if since and c["created_at"] < since:
                continue
            row = {"candidate_uuid": c["candidate_uuid"],
                   "source_type": c["source_type"],
                   "record_uuid": c["source_record_uuid"] or "",
                   "created_at": c["created_at"]}
            if c["candidate_uuid"] in linked_candidates:
                outcome_linked.append(row)
            else:
                row["reason"] = ("no rule application was recorded for that "
                                 "work, so this outcome is attributed to no rule")
                unattributed.append(row)
        contradictions = self.learning_conflicts()["contradictions"]
        counts = {}
        for name in L.FAILURE_CLASSES:
            counts[name] = len(by_class.get(name, ()))
        counts["retrieval_miss"] += len(misses)
        notes = []
        if not apps and not misses:
            notes.append("no rule application falls in this window, so every "
                         "class below is not measured rather than zero")
        if graded["not_decidable_tasks"]:
            notes.append("%d task(s) kept no text, so what else was retrievable "
                         "for them cannot be reconstructed"
                         % len(graded["not_decidable_tasks"]))
        return {
            "window_days": window_days, "since": since,
            "applications_in_window": len(apps),
            "counts": counts,
            "repeated_corrections": repeats,
            # A CORRECTION repeated is the founder giving the same instruction
            # twice, and that is what the weekly review's line by that name
            # promises him. Rework and escaped defects are outcomes, not
            # instructions: nobody restated anything, so they are graded under
            # their own line below and never counted as the founder repeating
            # himself. Folding them in told him he had said a thing N times
            # when he had said it once.
            "repeated_settled_corrections": [r for r in repeats
                                             if r["settled"] and r["is_correction"]],
            "outcome_gradings": [r for r in repeats if not r["is_correction"]],
            "retrieval_misses": misses,
            "compliance_failures": by_class.get("compliance_failure", []),
            "bad_rule_candidates": by_class.get("bad_rule", []),
            "scope_errors": by_class.get("scope_error", []),
            "not_decidable": by_class.get("not_decidable", []),
            "not_decidable_tasks": graded["not_decidable_tasks"],
            "unresolved_contradictions": contradictions,
            "rules_never_retrieved": never,
            "rules_always_not_relevant": always_irrelevant,
            "outcomes_linked_to_rules": outcome_linked,
            "unattributed_outcomes": unattributed,
            "classes": list(L.FAILURE_CLASSES), "notes": notes}

    def learning_rule_outcomes(self, prefix):
        """One rule's whole external record: what happened after it was shown.

        Counts only. A rule with no applications reports 'not measured' rather
        than a rate over zero, because a percentage of nothing is the most
        confident-looking lie a report of this kind can tell."""
        L = _learning()
        rule = self.get_learning_rule(prefix)
        apps = self.list_learning_applications(rule_prefix=rule["rule_uuid"])
        dispositions, outcomes, versions = {}, {}, {}
        for a in apps:
            dispositions[a["disposition"]] = dispositions.get(a["disposition"], 0) + 1
            outcomes[a["outcome"]] = outcomes.get(a["outcome"], 0) + 1
            key = str(a["rule_version"])
            versions[key] = versions.get(key, 0) + 1
        evidence = self.list_learning_evidence(rule["rule_uuid"])
        polarity = {}
        for e in evidence:
            polarity[e["polarity"]] = polarity.get(e["polarity"], 0) + 1
        repeats = []
        for pair in self._repeat_evidence_pairs():
            if pair["r"] != rule["rule_uuid"]:
                continue
            cand = self.get_learning_candidate(pair["c"])
            work = self._applications_for_work(
                rule["rule_uuid"], cand["source_record_uuid"],
                cand["source_session_id"])
            cls, why, pol = L.classify_repeated_correction(
                work, bool(cand["source_record_uuid"] or cand["source_session_id"]))
            repeats.append({"candidate_uuid": cand["candidate_uuid"],
                            "source_type": cand["source_type"],
                            "is_correction":
                                cand["source_type"] not in self.OUTCOME_SOURCE_TYPES,
                            "classification": cls, "classification_reason": why,
                            "polarity": pol})
        graded = []
        for a in apps:
            cls, why = L.classify_application(a["disposition"],
                                              a["shown_to_model"], a["outcome"])
            graded.append({"application_uuid": a["application_uuid"],
                           "rule_version": a["rule_version"],
                           "session_id": a["session_id"],
                           "disposition": a["disposition"],
                           "outcome": a["outcome"],
                           "classification": cls,
                           "classification_reason": why})
        notes = []
        if not apps:
            notes.append("this rule has never been recorded as applied, so "
                         "whether it works is not measured")
        return {"rule_uuid": rule["rule_uuid"], "state": rule["state"],
                "severity": rule["severity"], "rule_type": rule["rule_type"],
                "current_version": rule["current_version"],
                "applications": len(apps),
                "by_disposition": dispositions, "by_outcome": outcomes,
                "by_rule_version": versions,
                "evidence_by_polarity": polarity,
                "graded_applications": graded,
                "repeated_corrections": repeats, "notes": notes}

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

    def identity_by_name(self, name):
        """Every record whose name is EXACTLY `name`, newest first, as a
        list of dicts holding lifecycle_uuid plus structural metadata ONLY:
        lifecycle_uuid, lifetime, state, version, session_id, created_at,
        updated_at. No objective, no owner, no tier, no check_cmd, no
        evidence, and not the name itself, which the caller already has
        because it is the query.

        THIS EXISTS BECAUSE IDENTITY RESOLUTION IS NOT PRESENTATION.
        bm_threads.py resolves a thread name through store.dump(), and
        dump() is a DISPLAY boundary whose default-deny redaction (GATE C)
        rewrites records.name along with every other free-text column. A
        name that trips the redactor ("AKIAIOSFODNN7EXAMPLE" is a legal
        name: valid_name only rejects reserved characters and whitespace)
        therefore comes back as "[REDACTED]", matches nothing, and the
        thread that was stored perfectly well can never be found again
        while its fence stays claimed. Redaction belongs at the boundary
        where text LEAVES the machine, not in the lookup that decides which
        lifecycle a caller is talking about, so this reads the records
        table directly and returns nothing a redactor would have needed to
        touch.

        Ordering matches what bm_threads._find_record already does with
        dump()'s rows (most recently updated first), with lifecycle_uuid
        as a deterministic tie break so two records updated in the same
        second do not come back in an order that depends on sqlite's row
        layout. Callers keep their own ambiguity policy: this returns every
        match rather than picking one, because picking one is the caller's
        refusal to make."""
        rows = _exec(self,
            "SELECT lifecycle_uuid, lifetime, state, version, session_id, "
            "created_at, updated_at FROM records WHERE name = ? "
            "ORDER BY updated_at DESC, lifecycle_uuid ASC", (name,)).fetchall()
        return [dict(r) for r in rows]

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
                    if not row_dict.get(col):
                        continue
                    if (t, col) in _DUMP_WITHHELD_COLUMNS:
                        # Withheld, not scrubbed: see _DUMP_WITHHELD_COLUMNS.
                        row_dict[col] = "[WITHHELD: %d chars of founder text]" % len(
                            row_dict[col])
                    else:
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
        # FINDING 5 (2026-07-27): the diagnostics run through this class, and
        # a diagnostic that reports a healthy store while git is committing
        # its cleartext contents is the same failure shape fix-round 4
        # already closed once ("report health about the empty shell it just
        # made"). Refusing is not writing: nothing here moves, renames or
        # creates anything, and the refusal message IS the diagnosis, naming
        # both the remediation and the escape hatch.
        _refuse_if_git_can_commit_store(self.root)
        self.path = store_path(self.root)
        if not os.path.isfile(self.path):
            raise OwnershipRefused(
                "no-store",
                "no store exists at %s; run `%s init` to create one"
                % (self.path, _cmd()),
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
            _OPEN_STORES.add(self)
            if _TRACK_UNCLOSED:
                _UNCLOSED.add(self)
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
                _UNCLOSED.discard(self)
            raise OwnershipRefused(
                "db-busy",
                "the store at %s is busy or locked (%s); wait a moment and "
                "retry." % (self.path, e))
        except sqlite3.DatabaseError as e:
            self._quarantine_and_raise(e)

    def _quarantine_and_raise(self, cause):
        """FINDING 7, CONFIRMED: a read-only health check must NEVER move the
        real database. This used to be one line, `return
        Store._quarantine_and_raise(self, cause)`, so every quarantine the
        writable store could perform, a diagnostic could perform too. The
        SessionStart hook runs `bm_store.py verify` automatically against
        the founder's real project, so a transient disk I/O error, a
        permission problem or a network-volume hiccup during that read was
        enough to move a healthy store aside.

        Overriding here rather than checking a flag inside the mover is the
        point: ReadOnlyStore does not inherit from Store, so with this
        delegation removed there is NO path from a read-only object to the
        code that renames or moves anything. Write authority, not error
        classification, decides whether the destructive action is reachable
        at all.

        Reports and preserves: the connection is closed (so the handle
        cannot outlive the failure, the leak class from CI run 18) and the
        file is left byte for byte where it was. StoreCorrupt is
        deliberately the same exception type this raised before, so every
        caller outside this module keeps the behavior it already handles;
        only the side effect is gone."""
        self.close()
        raise StoreCorrupt(
            "%s could not be read as a SQLite database (%s). This was a "
            "READ-ONLY diagnostic, which has no authority to write: nothing "
            "was moved, renamed, copied or deleted, and the file is still at "
            "its original path with its original bytes. Inspect it by hand; "
            "if it really is damaged, a writable command is the only thing "
            "that may quarantine it." % (self.path, cause))

    def _verify_schema_or_raise(self):
        # Reuses Store's implementation verbatim, same reasoning as above.
        # migrate is left at its default False: a read-only diagnostic must
        # never migrate. It gets a clear "needs migration" refusal instead.
        return Store._verify_schema_or_raise(self)

    def _refuse_without_quarantine(self, message):
        """Borrowed for the same reason as _verify_schema_or_raise above, and
        MISSING until a live probe caught it (correction-learning Loop 1,
        2026-07-29): opening a real schema-1 store with a schema-2 binary
        through `verify` raised AttributeError instead of the intended refusal.
        All 419 tests were green, because not one of them opened an
        out-of-date store through the READ-ONLY path. The regression test for
        this is test_readonly_store_on_schema1_refuses_cleanly."""
        return Store._refuse_without_quarantine(self, message)

    def dump(self, raw=False):
        # Reuses Store.dump() verbatim: it only calls _exec(self, ...) over
        # _TABLES, which works identically against a read-only connection.
        return Store.dump(self, raw=raw)

    def identity_by_name(self, name):
        # Same reuse, same reason: one SELECT through _exec, no writes. A
        # read-only consumer resolving a name needs this at least as much
        # as a writable one, since it is the diagnostic that has to explain
        # why a thread cannot be found.
        return Store.identity_by_name(self, name)

    def close(self):
        """Idempotent, same contract as Store.close()."""
        _OPEN_STORES.discard(self)
        _UNCLOSED.discard(self)
        if self.conn is not None:
            try:
                self.conn.close()
            finally:
                self.conn = None
                _UNCLOSED.discard(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Same rationale as Store.__exit__: a diagnostic read (dashboard,
        # verify, has_receipt) that opens a ReadOnlyStore and forgets to
        # close it leaks exactly the same handle.
        self.close()
        return False


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
    2026-07-26-phase1-fix-round-7.md for the full incident writeups.

    FINDING 2B: both the read below and the backup write route through
    safe_project_path (THE PATH FUNNEL), computed BEFORE any work is done,
    so a symlinked STATE.md refuses 'path-escape' instead of having its
    target's bytes read and copied into an in-repo STATE.md.bak-<stamp>
    that `git add -A` would then commit."""
    path = safe_project_path(root, "STATE.md")
    generated = render_state_md(root)
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
        #
        # FINDING 2B: the backup NAME is built root-relative and pushed
        # back through the funnel (never `path + ".bak-"`, a raw string
        # concatenation the funnel cannot see), so a symlink pre-planted at
        # the backup name is refused instead of written through.
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        backup_name = "STATE.md.bak-" + stamp
        backup_path = safe_project_path(root, backup_name)
        if os.path.lexists(backup_path):
            backup_path = safe_project_path(
                root, backup_name + "-" + uuid.uuid4().hex[:8])
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
    # FINDING 2B: the same funnel write_state_view uses, so this diagnostic
    # read cannot be pointed at a file outside the project either. verify()
    # promises a LIST of problems, never a crash, so a containment refusal
    # becomes a reported problem here rather than an exception escaping a
    # health check.
    try:
        state_path = safe_project_path(root, "STATE.md")
    except OwnershipRefused as e:
        return ["STATE.md under %s cannot be read safely (%s: %s); nothing "
                "was read or written" % (root, e.reason, e)]
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
                "STATE.md does not exist at %s; run `%s "
                "dashboard` (or any mutating command) to generate it"
                % (state_path, _cmd()))
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
        "then run `%s init --acknowledge-quarantine`"
        % (_quarantine_summary(d), _cmd()) for d in unacknowledged]
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
            "what you need, then run `%s init "
            "--acknowledge-quarantine` to continue (the directory is never "
            "deleted by this)."
            % (len(unacknowledged), "y has" if len(unacknowledged) == 1 else "ies have",
               "; ".join(_quarantine_summary(d) for d in unacknowledged), _cmd()),
            details={"quarantine_dirs": unacknowledged})
    # init_project returns the Store it just opened (its own schema-setup
    # side effects need a live connection); this command only needs the
    # side effects, so close it right away instead of leaking the handle
    # for the rest of the process (the real, product-level shape of the
    # Windows CI defect this fix-round exists for).
    init_project(root).close()
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
          "Run `%s init --acknowledge-quarantine` "
          "after recovering what you need."
          % (len(unacknowledged), "y" if len(unacknowledged) == 1 else "ies",
             "; ".join(_quarantine_summary(d) for d in unacknowledged), _cmd()))


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
                   "`%s verify` or `dump` once "
                   "bm_telemetry.py is restored to see whether it actually "
                   "took effect.\n" % _cmd())
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
