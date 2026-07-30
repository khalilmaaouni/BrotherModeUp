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
import secrets
import shlex
import shutil
import sqlite3
import sys
import unicodedata
import uuid

SCHEMA_VERSION = 10
STORE_DIRNAME = ".brothermode"
STORE_FILENAME = "store.sqlite3"
MAX_ACTIVE_PERSISTENT = 3

# How long an approval receipt stays usable. Short on purpose: the receipt
# exists to carry ONE human answer across the gap between the question window
# and the approve command, not to sit in a file being reusable tomorrow. The
# CLI cannot ask for longer; a caller passing more is clamped to this.
APPROVAL_RECEIPT_TTL_SECONDS = 900
# Domain separation, so a hash of the same random string somewhere else in this
# project can never be mistaken for a receipt token hash.
_RECEIPT_TOKEN_DOMAIN = "brothermode-approval-receipt-v1:"
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
    and friends, case-sensitive default filesystems) does not.

    GATE 3 (fix-round 2026-07-29): the same platforms are also UNICODE
    NORMALIZATION insensitive. On APFS and HFS+, 'src/café.py' (NFD) and
    'src/café.py' (NFC) are ONE inode and TWO different Python strings, so a
    claim stored in one spelling did not overlap a write in the other and the
    fence hook allowed a foreign session straight through its default
    (non-strict) path: covering=[], foreign=[], no decision, allow. Folding
    to NFC AFTER casefold (casefold can itself denormalize) makes both
    spellings one comparison key, which closes that bypass for
    paths_overlap and for the claim-time overlap check that shares it.
    Linux is normalization PRESERVING and sensitive, where the two really
    are different files, so it is deliberately left alone."""
    if sys.platform in _CASE_INSENSITIVE_PLATFORMS:
        return unicodedata.normalize("NFC", p.casefold())
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


class HandoverLost(OwnershipRefused):
    """A transition asked for a handover and the store could not prove one
    exists for it after the write. Raised INSIDE transition()'s transaction,
    so the transition rolls back with it: the record does not move.

    Fix round for LOOP P12 (2026-07-29). _insert_handover used to swallow the
    UNIQUE-index IntegrityError unconditionally and return "already", and
    transition() discarded that return value, so a losing insert committed a
    lifecycle move with NO handover row anywhere. The dedupe index was keyed on
    (lifecycle_uuid, payload_fingerprint) for all time, and the fingerprint does
    not cover state, version, transition_id or heading, so the SECOND park of a
    record whose payload had not changed wrote nothing at all once the first
    handover had been acknowledged: `handovers` reported none, STATE.md had no
    Handovers section, and `verify` called it healthy. This exception is what
    that path raises now when the swallow cannot be justified by a
    still-undelivered twin carrying the same text. Subclasses OwnershipRefused
    because the outcome is a refusal with nothing changed, which is exactly how
    every CLI already reports it."""

    def __init__(self, message, details=None):
        super(HandoverLost, self).__init__("handover-lost", message, details)


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


def _resolve_proposal(L, cand, trigger, action, because, scope_type, scope_key,
                      domain, rule_type, severity, atomicity_override="",
                      conflict_override="", alerts_override=""):
    """The exact rule a candidate plus a set of overrides would become.

    ONE function, called by the receipt minting path and by the approval path,
    because the whole Model A guarantee rests on both computing the same thing.
    Two copies of this arithmetic would drift, and the drift would be silent: a
    receipt that never matches (approval impossible) or, far worse, a
    fingerprint that ignores a field the founder was shown.

    Scrubbing happens HERE rather than after, so the fingerprint covers the text
    that will actually be stored, not the text before the secret scrubber
    rewrote it."""
    return {
        "trigger": _scrubbed_field(L, trigger if trigger is not None else cand["proposed_trigger"]),
        "action": _scrubbed_field(L, action if action is not None else cand["proposed_action"]),
        "because": _scrubbed_field(L, because if because is not None else cand["proposed_because"]),
        "scope_type": scope_type or cand["proposed_scope_type"],
        "scope_key": _scrubbed_field(L, scope_key if scope_key is not None else cand["proposed_scope_key"]),
        "domain": _scrubbed_field(L, domain if domain is not None else cand["proposed_domain"]),
        "rule_type": rule_type,
        "severity": severity,
        # FIX ROUND P3, 2026-07-29. These two were parameters of approval and of
        # nothing else, so a receipt minted for a clean question could be spent
        # with --override-conflict attached and force a second injectable rule
        # contradicting an approved gate rule, on an answer given about a
        # question that never mentioned the conflict. Bypassing a guard changes
        # what the rule set DOES, so by the rule stated in approval_fingerprint
        # it belongs in the fingerprint. The BOOLEAN goes in, not the wording:
        # what the founder is consenting to is the bypass, not the excuse, and
        # binding the excuse text would fail receipts over a retyped word.
        "override_atomicity": bool((atomicity_override or "").strip()),
        "override_conflict": bool((conflict_override or "").strip()),
        # Schema 7, 2026-07-30. In the fingerprint for exactly the reason the
        # two flags above are: proceeding past an unresolved critical alert
        # changes what the approval DOES, so the founder's answer has to have
        # been given about the override as well. A receipt minted for a clean
        # question cannot be spent with --override-alerts attached.
        "override_alerts": bool((alerts_override or "").strip()),
    }


def _proposal_fingerprint(L, cand, prop):
    """Bind a receipt to the candidate AND to the rule text being approved.

    candidate_uuid and content_hash cover "the candidate changed under me":
    content_hash is computed from the captured words, so an edit to the source
    text moves it. The proposal fields cover "the rule text changed between the
    question and the approval", which is the case a candidate-only fingerprint
    would miss entirely, because the approve command can override every one of
    them on the command line."""
    return L.approval_fingerprint((
        cand["candidate_uuid"], cand["content_hash"],
        prop["trigger"], prop["action"], prop["because"],
        prop["scope_type"], prop["scope_key"], prop["domain"],
        prop["rule_type"], prop["severity"],
        "override_atomicity=%d" % int(prop["override_atomicity"]),
        "override_conflict=%d" % int(prop["override_conflict"]),
        "override_alerts=%d" % int(prop["override_alerts"])))


def _resolve_edit(L, rule, trigger, action, because, domain):
    """The exact text a rule edit would produce, scrubbed exactly as approval
    scrubs it. Called by the edit-receipt minting path AND by the edit itself,
    for the reason given on _resolve_proposal: two copies of this arithmetic
    would drift, and the drift would be silent."""
    return {
        "trigger": _scrubbed_field(L, trigger if trigger is not None else rule["trigger_text"]),
        "action": _scrubbed_field(L, action if action is not None else rule["action_text"]),
        "because": _scrubbed_field(L, because if because is not None else rule["because_text"]),
        "domain": _scrubbed_field(L, domain if domain is not None else rule["domain"]),
    }


def _edit_fingerprint(L, rule, next_version, prop):
    """Bind an edit receipt to ONE rule, ONE version bump, and ONE new text.

    The literal "edit" is domain separation, and it is load bearing: edit
    receipts live in the same table as approval receipts, and this is what
    stops one being spent as the other. rule_uuid stops the receipt moving to a
    different rule; next_version stops it being replayed after some other edit
    already bumped the version underneath it."""
    return L.approval_fingerprint((
        "edit", rule["rule_uuid"], str(next_version),
        prop["trigger"], prop["action"], prop["because"], prop["domain"]))


def _state_change_fingerprint(L, kind, target_uuid, content_parts):
    """Bind a state-change receipt to ONE command kind, ONE target, and the
    exact material content of the change proposed for it.

    ONE helper beside _proposal_fingerprint and _edit_fingerprint, shared by
    every one of the five rule-altering commands that are not create or edit
    (supersede, resolve-conflict, deprecate, forget, resolve-note), used by
    the minting path and the spending path so the two can never silently
    drift (same reason _resolve_proposal gives for why two copies of this
    arithmetic is the failure mode). `kind` is domain separation exactly like
    the literal "edit" is for _edit_fingerprint: it is what stops a receipt
    minted for one of the five commands from ever being spendable as another,
    and what stops it from ever being spendable as an approval or edit
    receipt (which, in addition, live in an entirely separate table).
    `content_parts` is an ordered tuple of the fields that describe WHAT is
    being done to the target (new state, successor uuid, reason, and so on);
    a change to any of them moves the hash and dies the receipt, exactly as a
    changed trigger or action dies an approval receipt."""
    return L.approval_fingerprint(
        (kind, target_uuid) + tuple(content_parts))


def _approval_guards(store, L, prop, cand):
    """The refusals that stand between a proposal and the injectable set.

    ONE function, called by the receipt minting path AND by the approval path,
    for the same reason _resolve_proposal is (FIX ROUND P3, 2026-07-29). Before
    this, only approval ran them, so `grant-approval` happily printed a token
    for a candidate that directly contradicted an approved gate rule and said
    nothing about it: the founder answered a question that never mentioned the
    contradiction, and the approver alone decided to force it through. Running
    them at mint means the question cannot be asked at all until the conflict is
    either resolved or explicitly being overridden, and an override is now part
    of the fingerprint, so the answer is given about the override too.

    ALERTS WITH TEETH (schema 7, 2026-07-30, founder decision 7 of the
    documentation and gate-pack spec). An unresolved critical alert anchored to
    this candidate, or to any file this approval would change, REFUSES here. The
    refusal names the alert, its author and its anchor, because an alert that
    blocks and cannot be traced to a person is a wall with no door. The founder
    may override, and the override is part of what he answered (it is in the
    fingerprint) and is written onto the alert row itself by
    approve_learning_candidate, so the alert stays visible as overridden rather
    than being settled by having been forced through once.

    Raises OwnershipRefused, or returns quietly. Never writes."""
    if not prop["trigger"] or not prop["action"]:
        raise OwnershipRefused(
            "incomplete-rule",
            "a rule needs both a trigger and an action; got trigger=%r "
            "action=%r" % (prop["trigger"], prop["action"]))
    scope_err = L.validate_scope(prop["scope_type"], prop["scope_key"])
    if scope_err:
        raise OwnershipRefused("bad-scope", scope_err)
    problems = L.atomicity_problems(prop["action"])
    if problems and not prop["override_atomicity"]:
        raise OwnershipRefused(
            "not-atomic",
            "this action looks like more than one rule (%s). Split it, or "
            "re-run with an explicit override reason. A compound rule cannot "
            "be graded: when the outcome is bad you cannot tell which half "
            "was wrong." % "; ".join(problems))
    found = store.conflicts_against({
        "scope_type": prop["scope_type"], "scope_key": prop["scope_key"],
        "trigger_text": prop["trigger"], "action_text": prop["action"]})
    if not prop["override_conflict"]:
        if found["contradictions"]:
            other, v = found["contradictions"][0]
            raise OwnershipRefused(
                "unresolved-contradiction",
                "this would create a second injectable rule contradicting %s "
                "(%s). Resolve it first: narrow one scope, supersede one, mark "
                "one contradicted, or re-run with an explicit override reason. "
                "Existing rule says: %s"
                % (other["rule_uuid"][:8], "; ".join(v["reasons"]),
                   L.safe_display(other["action_text"], 120)))
        if found["duplicates"]:
            other, v = found["duplicates"][0]
            raise OwnershipRefused(
                "duplicate-rule",
                "rule %s already says this in the same scope (%s). A repeat is "
                "evidence, not a second rule: merge the candidate into it, or "
                "re-run with an explicit override reason if they really differ."
                % (other["rule_uuid"][:8], "; ".join(v["reasons"])))
    alerts = store.blocking_alerts(cand)
    if alerts and not prop["override_alerts"]:
        first = alerts[0]
        # An alert already overridden at ANOTHER gate still blocks this one (see
        # blocking_alerts), so the refusal says so: without that sentence a
        # founder who remembers overriding this alert last week reads the
        # refusal as a bug rather than as a second gate asking about the same
        # unanswered concern.
        again = ""
        if first["overridden_at"] is not None:
            again = (" This alert was overridden at an earlier gate (%s: %s) "
                     "and is still unresolved, so it stands in front of this "
                     "one too."
                     % (first["overridden_at"],
                        L.safe_display(first["override_reason"], 120)))
        raise OwnershipRefused(
            "unresolved-critical-alert",
            "a critical alert is unresolved and stands in front of this "
            "approval: %s wrote %r about %s (note %s). Resolve it, or re-run "
            "with an explicit override reason. %d unresolved critical alert(s) "
            "match this approval.%s"
            % (L.safe_display(first["author"], 60),
               L.safe_display(first["body"], 160), first["matched"],
               first["note_uuid"][:8], len(alerts), again),
            details={"note_uuids": [a["note_uuid"] for a in alerts]})
    return {"atomicity_problems": problems, "conflicts": found,
            "blocking_alerts": alerts}


def _receipt_token_hash(token):
    """The only transformation a receipt token ever gets. Domain separated so a
    sha256 of the same string computed elsewhere in this project cannot be
    mistaken for a receipt hash."""
    return hashlib.sha256(
        (_RECEIPT_TOKEN_DOMAIN + token).encode("utf-8")).hexdigest()


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

# Schema 3 adds the human approval receipt (post-audit LOOP 3, founder decision
# 2026-07-29: Model A). Its own tuple for the same reason schema 2 got one: a
# healthy schema-2 store must be checked against schema 2's table list, or the
# version check never runs and a store whose only fault is predating the upgrade
# gets quarantined.
_TABLES_RECEIPTS = ("learning_approval_receipts",)

_TABLES_V3 = _TABLES_V2 + _TABLES_RECEIPTS

# Schema 4 adds the retrieval run (post-audit LOOP P6). Its own tuple for the
# third time and for the third identical reason: a healthy schema-3 store must
# be checked against schema 3's table list, or the version check never runs and
# a store whose only fault is predating the upgrade gets quarantined.
_TABLES_RETRIEVAL = ("learning_retrieval_runs",)

_TABLES_V4 = _TABLES_V3 + _TABLES_RETRIEVAL

# Schema 5 adds the transactional handover (post-audit LOOP P12). Its own tuple
# for the fourth time and for the fourth identical reason: a healthy schema-4
# store must be checked against schema 4's table list, or the version check
# never runs and a store whose only fault is predating the upgrade gets
# quarantined.
_TABLES_HANDOVER = ("handovers",)

_TABLES_V5 = _TABLES_V4 + _TABLES_HANDOVER

# Schema 6 adds NO table: it only replaces the handover dedupe index (see
# _migrate_5_to_6). It still needs its own entry, because _TABLES is looked up
# by SCHEMA_VERSION and a missing key is an import-time KeyError. Sharing the
# schema-5 tuple by name rather than copying it keeps the two versions provably
# identical in what they require to be present.
_TABLES_V6 = _TABLES_V5

# Schema 7 adds the anchored note (phase A of the documentation and gate-pack
# spec, 2026-07-30). Its own tuple for the fifth time and for the fifth
# identical reason: a healthy schema-6 store must be checked against schema 6's
# table list, or the version check never runs and a store whose only fault is
# predating the upgrade gets quarantined.
_TABLES_NOTES = ("notes",)

_TABLES_V7 = _TABLES_V6 + _TABLES_NOTES

# Schema 8 adds NO table: it adds ONE column to notes (notes.anchor_line_hash,
# phase C of the same spec). It still needs its own entry, for the same reason
# schema 6 needed one: _TABLES is looked up by SCHEMA_VERSION and a missing key
# is an import-time KeyError. Sharing the schema-7 tuple by name rather than
# copying it keeps the two versions provably identical in what must be present.
_TABLES_V8 = _TABLES_V7

# Schema 9 adds the generic state-change receipt (LOOP 2, 2026-07-30):
# supersede, resolve-conflict, deprecate, forget and resolving a critical
# alert all move a rule out of the injectable set or silence one, and only
# create and edit had a receipt in front of them. ONE table, ONE mint
# function and ONE spend function serve all five call sites rather than five
# bespoke checks: this project's own failure ledger names a cross-cutting
# concern implemented per call site as the root cause behind four separate
# bugs. `learning_approval_receipts` cannot be reused (its approval_choice
# CHECK constraint accepts only 'approve' and its candidate_uuid is a NOT
# NULL foreign key into learning_candidates; a supersede or a resolve-note
# target is a rule or a note, not a candidate). Its own tuple for the sixth
# time and for the sixth identical reason: a healthy schema-8 store must be
# checked against schema 8's table list, or the version check never runs and
# a store whose only fault is predating the upgrade gets quarantined.
_TABLES_STATE_CHANGE_RECEIPTS = ("learning_state_change_receipts",)

_TABLES_V9 = _TABLES_V8 + _TABLES_STATE_CHANGE_RECEIPTS

# Schema 10 (LOOP 3, 2026-07-30) adds two columns to the EXISTING
# learning_applications table (presentation, action_reached), not a new
# table, so the table LIST is provably identical to schema 9's. Same shape
# as _TABLES_V8 = _TABLES_V7 above, for the same reason: a healthy
# schema-9 store must be checked against schema 9's table list, or the
# version check never runs and a store whose only fault is predating this
# upgrade gets quarantined.
_TABLES_V10 = _TABLES_V9

_TABLES_BY_VERSION = {1: _TABLES_V1, 2: _TABLES_V2, 3: _TABLES_V3,
                      4: _TABLES_V4, 5: _TABLES_V5, 6: _TABLES_V6,
                      7: _TABLES_V7, 8: _TABLES_V8, 9: _TABLES_V9,
                      10: _TABLES_V10}

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

# The approval receipt (schema 3). What a row here means: a human was asked a
# question about ONE candidate and answered it, and that answer has not yet been
# spent.
#
# nonce_hash is the ONLY trace of the token. The token itself is shown once, by
# the founder-side mint command, and is never written to the store, to a log, to
# an error message or to a transcript. A stolen store therefore yields no usable
# receipt: sha256 of a 48-hex-character secret is not reversible.
#
# founder_response_hash is a hash, not the words. The founder's literal answer
# is the most sensitive text in this whole flow and the store has no reason to
# keep it: the hash is enough to prove later that a given answer produced this
# receipt, and useless to anyone who reads the file.
#
# candidate_fingerprint binds the receipt to WHAT WAS SHOWN. If the candidate
# text, its scope, or the rule text being approved changes between the question
# and the approval, the fingerprint no longer matches and the receipt is dead.
# That is the difference between "the founder said yes" and "the founder said
# yes TO THIS".
#
# consumed_rule_uuid carries NO foreign key on purpose: consumption is the FIRST
# statement of the approval transaction, before the rule row exists, so that a
# second approval racing for the same receipt loses on the UPDATE rather than
# after having already written a rule.
_RECEIPT_DDL = """
CREATE TABLE IF NOT EXISTS learning_approval_receipts (
  receipt_uuid TEXT PRIMARY KEY,
  candidate_uuid TEXT NOT NULL REFERENCES learning_candidates(candidate_uuid) ON DELETE CASCADE,
  approval_choice TEXT NOT NULL CHECK(approval_choice IN ('approve')),
  nonce_hash TEXT NOT NULL UNIQUE,
  candidate_fingerprint TEXT NOT NULL,
  founder_response_hash TEXT NOT NULL,
  issued_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  consumed_at TEXT,
  consumed_rule_uuid TEXT
);
"""

_RECEIPT_INDEX_DDL = """
CREATE INDEX IF NOT EXISTS learning_approval_receipts_candidate_idx
  ON learning_approval_receipts(candidate_uuid, consumed_at);
"""

_RECEIPT_DDL_STATEMENTS = _split_ddl(_RECEIPT_DDL)
_RECEIPT_INDEX_STATEMENTS = _split_ddl(_RECEIPT_INDEX_DDL)

# The generic state-change receipt (schema 9, LOOP 2, 2026-07-30). ONE table
# for every rule-altering command that is not create or edit: supersede,
# resolve-conflict, deprecate, forget, and resolving a critical alert. Same
# shape as learning_approval_receipts and for the same reasons (see the block
# comment above it), with two differences forced by having five callers
# instead of one:
#
# kind is the discriminator a bare copy of learning_approval_receipts has no
# room for: its approval_choice CHECK accepts only 'approve'. Domain
# separation here works exactly like the literal "edit" does for
# _edit_fingerprint (see _state_change_fingerprint): a receipt minted for one
# kind can never spend as another, and the CHECK constraint below is the
# first of three independent places that is enforced (the fingerprint and the
# spend function's own comparison are the other two).
#
# target_uuid carries NO foreign key, deliberately, and for a stronger reason
# than consumed_rule_uuid's below: which table it points into DEPENDS ON
# kind (a rule for supersede/resolve-conflict/deprecate/forget, a note for
# resolve-note), so no single REFERENCES clause could ever be correct for
# every row.
_STATE_CHANGE_RECEIPT_DDL = """
CREATE TABLE IF NOT EXISTS learning_state_change_receipts (
  receipt_uuid TEXT PRIMARY KEY,
  kind TEXT NOT NULL CHECK(kind IN (
    'supersede', 'resolve-conflict', 'deprecate', 'forget', 'resolve-note')),
  target_uuid TEXT NOT NULL,
  nonce_hash TEXT NOT NULL UNIQUE,
  content_fingerprint TEXT NOT NULL,
  founder_response_hash TEXT NOT NULL,
  issued_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  consumed_at TEXT,
  consumed_target_uuid TEXT
);
"""

_STATE_CHANGE_RECEIPT_INDEX_DDL = """
CREATE INDEX IF NOT EXISTS learning_state_change_receipts_target_idx
  ON learning_state_change_receipts(kind, target_uuid, consumed_at);
"""

_STATE_CHANGE_RECEIPT_DDL_STATEMENTS = _split_ddl(_STATE_CHANGE_RECEIPT_DDL)
_STATE_CHANGE_RECEIPT_INDEX_STATEMENTS = _split_ddl(_STATE_CHANGE_RECEIPT_INDEX_DDL)

# The five kinds, named once so the CHECK constraint, the CLI, and the
# enumeration test that discovers rule-altering commands all read from the
# same list rather than three hand-typed copies that can drift.
STATE_CHANGE_RECEIPT_KINDS = (
    "supersede", "resolve-conflict", "deprecate", "forget", "resolve-note")

# change_learning_rule_state's DEFAULT receipt kind for each target state
# that unconditionally requires one (LOOP 2, 2026-07-30). 'confirmed' and
# 'settled' are deliberately absent: those two transitions are evidence-graded
# lifecycle promotions, not rule-text changes, and are not gated by this map.
# A caller may override the default (resolve_learning_conflict does, so its
# own 'superseded' branch gates under 'resolve-conflict' rather than
# 'supersede'), but may NOT opt out of gating entirely for a target that is a
# key in this map: that is the difference between this and the old
# receipt_kind=None-means-ungated shape, which a direct Python caller could
# simply omit.
STATE_CHANGE_GATE_KIND = {
    "superseded": "supersede",
    "deprecated": "deprecate",
    "forgotten": "forget",
}

# The retrieval run (schema 4, post-audit LOOP P6). What a row here means: at
# this moment, for THIS task in THIS scope context, the retrieval was asked for
# with THESE parameters and returned this many of this many eligible rules.
#
# WHY IT EXISTS AS A ROW rather than as fields on the application rows. A
# retrieval-miss finding is a statement about what was NOT returned, and the
# rules that were not returned have no application row to hang context on. The
# classifier used to rebuild the context by reading the scope_match values of
# the rows that DID land, which is circular: a task where no project rule was
# returned reported an empty project context, so every project rule it missed
# was invisible and the miss count read zero. Reproduced on the real CLI before
# this table was written (limit 0, one global gate and one project rule in
# scope: the project rule was cut, and classify reported no misses at all).
#
# query_hash, NOT the query. The hash is enough to recognise the same task text
# coming back and useless to anyone reading the file. task_excerpt is the same
# bounded, scrubbed, redacted 500 characters learning_applications already
# keeps, mirrored here so a run is self-contained; it is withheld from dump
# like its twin, and a caller that passes task_excerpt="" stores none of it.
#
# eligible_count and returned_count are the DENOMINATOR, recorded at the time.
# Recomputing them later against today's corpus is the thing this whole loop
# refuses: rules get added, edited and forgotten, and a denominator that moves
# under the founder is worse than no denominator.
_RETRIEVAL_RUN_DDL = """
CREATE TABLE IF NOT EXISTS learning_retrieval_runs (
  retrieval_uuid TEXT PRIMARY KEY,
  session_id TEXT NOT NULL DEFAULT '',
  record_uuid TEXT REFERENCES records(lifecycle_uuid),
  task_fingerprint TEXT NOT NULL,
  task_excerpt TEXT NOT NULL DEFAULT '',
  query_hash TEXT NOT NULL,
  project_key TEXT NOT NULL DEFAULT '',
  domain_key TEXT NOT NULL DEFAULT '',
  artifact_key TEXT NOT NULL DEFAULT '',
  relationship_key TEXT NOT NULL DEFAULT '',
  tool_key TEXT NOT NULL DEFAULT '',
  requested_limit INTEGER NOT NULL,
  retrieval_mode TEXT NOT NULL,
  eligible_count INTEGER NOT NULL,
  returned_count INTEGER NOT NULL,
  created_at TEXT NOT NULL
);
"""

_RETRIEVAL_RUN_INDEX_DDL = """
CREATE INDEX IF NOT EXISTS learning_retrieval_runs_task_idx
  ON learning_retrieval_runs(session_id, task_fingerprint, created_at);
"""

_RETRIEVAL_RUN_DDL_STATEMENTS = _split_ddl(_RETRIEVAL_RUN_DDL)
_RETRIEVAL_RUN_INDEX_STATEMENTS = _split_ddl(_RETRIEVAL_RUN_INDEX_DDL)

# The handover (schema 5, post-audit LOOP P12). What a row here means: at the
# moment a record changed lifecycle state, this is what the outgoing session was
# leaving behind for whoever picks the work up.
#
# WHY IT IS A TABLE AND NOT AN APPEND. Until this loop, bm_threads.py delivered
# a handover by APPENDING text to the project's root STATE.md under its own
# directory lock, while write_state_view independently read that same file,
# rebuilt it and atomically REPLACED it, taking no lock at all. Interleave the
# two and the append lands on a file the replace is about to overwrite: the
# record is parked, the handover text is gone, and nothing anywhere holds a
# second copy. Reproduced on 2026-07-29 against a real store before this change
# (record state 'parked', handover tag absent from STATE.md, no table to recover
# it from). The fix is not a bigger lock. It is that the handover and the
# lifecycle transition that produced it are ONE sqlite transaction, and STATE.md
# becomes a pure render of that truth which can be regenerated at any time.
#
# transition_id carries the atomicity claim in the schema itself: it is the
# rowid of the transitions row written by the SAME transaction, so a handover
# whose transition rolled back cannot exist, and a transition whose handover
# insert raised rolled back with it. The partial unique index on it means one
# transition can own at most one handover.
#
# payload_fingerprint is the store's own full 64-hex handover_payload
# fingerprint, and the retry dedupe is
# UNIQUE(lifecycle_uuid, payload_fingerprint, heading) WHERE delivered_at IS
# NULL: a second attempt at the same handover text for the same lifecycle,
# while the first copy is still on the founder's screen, loses on the index
# instead of writing the text twice. That replaces bm_threads' old trick of
# scanning a text file for an HTML comment marker.
#
# Fix round (2026-07-29): that index used to be UNIQUE(lifecycle_uuid,
# payload_fingerprint) over ALL rows, delivered or not, and that is a dedupe
# that deletes handovers rather than deduplicating text. The fingerprint covers
# objective, files, owner, tier, check, evidence, latest digest and decisions.
# It does NOT cover state, version, transition_id, heading or the session ids.
# So a record parked, acknowledged, resumed and parked again with no new
# checkpoint produced the identical fingerprint, the insert lost, the swallow
# hid it, and the second park had no handover ANYWHERE: no row, no STATE.md
# section, and `verify` reported healthy. Two changes make that unreachable.
# The index is now PARTIAL on delivered_at IS NULL, so an acknowledged row can
# never suppress a new one (the founder has already seen and dismissed it, and
# it no longer renders). And heading is part of the key, so a park heading the
# founder typed and the adoption heading that follows it are two different
# handovers instead of one, which is what stopped an adopted record from
# rendering under a stale "Drained from thread mode" header forever.
#
# body holds the rendered digest (already passed through redact_text by
# render_digest, which refuses rather than render unredacted text), and it is
# passed through _redacted_view_text AGAIN on the way into STATE.md like every
# other founder-typed field: the store file itself is documented as sensitive in
# SECURITY.md, the generated view is not.
#
# delivered_at is NULL until a founder acknowledges the handover
# (`handover-ack`). An undelivered handover renders into STATE.md on every
# regeneration, so a crash between the commit and the render costs nothing: the
# next render puts it back. Acknowledging is idempotent; it never deletes the
# row, so `dump` still holds the whole history.
_HANDOVER_DDL = """
CREATE TABLE IF NOT EXISTS handovers (
  handover_uuid TEXT PRIMARY KEY,
  lifecycle_uuid TEXT NOT NULL REFERENCES records(lifecycle_uuid),
  transition_id INTEGER,
  from_session_id TEXT NOT NULL DEFAULT '',
  to_session_id TEXT NOT NULL DEFAULT '',
  payload_fingerprint TEXT NOT NULL,
  heading TEXT NOT NULL DEFAULT '',
  body TEXT NOT NULL DEFAULT '',
  delivered_at TEXT,
  created_at TEXT NOT NULL
);
"""

_HANDOVER_INDEX_DDL = """
CREATE UNIQUE INDEX IF NOT EXISTS handovers_undelivered_text_idx
  ON handovers(lifecycle_uuid, payload_fingerprint, heading)
  WHERE delivered_at IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS handovers_transition_idx
  ON handovers(transition_id) WHERE transition_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS handovers_undelivered_idx
  ON handovers(created_at) WHERE delivered_at IS NULL;
"""

_HANDOVER_DDL_STATEMENTS = _split_ddl(_HANDOVER_DDL)
_HANDOVER_INDEX_STATEMENTS = _split_ddl(_HANDOVER_INDEX_DDL)

# The anchored note (schema 7). Phase A of
# docs/superpowers/specs/2026-07-30-documentation-and-gate-packs-design.md needs
# exactly one thing from the collaboration layer of section 6: an alert a human
# wrote, anchored somewhere, that can REFUSE an approval. The table is built to
# section 6's full column list rather than to phase A's needs, so phase C
# extends it (more kinds in use, rendering, lineage queries) instead of
# replacing it and migrating twice.
#
# WHY THE KIND VOCABULARY IS THE WHOLE OF SECTION 6 ALREADY. A CHECK constraint
# is the one part of this that a later migration cannot widen cheaply in SQLite
# (it takes a table rebuild), so the six kinds are here from the start even
# though phase A only reads 'alert' and writes 'review'.
#
# severity is '' for the kinds that have none. Only 'critical' has teeth, and
# only on kind 'alert' (see blocking_alerts): a critical 'todo' refuses nothing,
# because a todo is not a warning and inventing a meaning for it would be a
# refusal nobody asked for.
#
# resolved_at and overridden_at are SEPARATE and neither is a delete. A resolved
# alert is answered; an overridden alert is unanswered and proceeded past
# anyway, and it keeps showing up as overridden for exactly that reason.
# override_reason is NOT NULL DEFAULT '' at the schema level and mandatory in
# the API: the override is only worth having if it is written down.
#
# anchor_line is nullable INTEGER: an alert about a whole file has no line, and
# a zero would be a line number that does not exist.
_NOTES_DDL = """
CREATE TABLE IF NOT EXISTS notes (
  note_uuid TEXT PRIMARY KEY,
  kind TEXT NOT NULL CHECK(kind IN (
    'insight','alert','question','review','todo','risk')),
  severity TEXT NOT NULL DEFAULT '' CHECK(severity IN (
    '','info','warning','critical')),
  author TEXT NOT NULL DEFAULT '',
  author_kind TEXT NOT NULL CHECK(author_kind IN (
    'founder','assistant','human')),
  anchor_type TEXT NOT NULL CHECK(anchor_type IN (
    'file','candidate','rule','record','decision')),
  anchor_key TEXT NOT NULL,
  anchor_line INTEGER,
  body TEXT NOT NULL DEFAULT '',
  session_id TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  resolved_at TEXT,
  resolution TEXT NOT NULL DEFAULT '',
  overridden_at TEXT,
  override_by TEXT NOT NULL DEFAULT '',
  override_reason TEXT NOT NULL DEFAULT ''
);
"""

_NOTES_INDEX_DDL = """
CREATE INDEX IF NOT EXISTS notes_anchor_idx
  ON notes(anchor_type, anchor_key, kind);
CREATE INDEX IF NOT EXISTS notes_open_alert_idx
  ON notes(kind, severity, resolved_at);
"""

_NOTES_DDL_STATEMENTS = _split_ddl(_NOTES_DDL)
_NOTES_INDEX_STATEMENTS = _split_ddl(_NOTES_INDEX_DDL)

# Schema 8, phase C. ONE additive column: the fingerprint of the source line a
# file anchor points at, taken when the note was written.
#
# WHY IT EXISTS. Section 6 requires that a note anchored to a line that has
# SINCE MOVED be reported rather than silently dropped, and a line number alone
# cannot answer that question: line 5 of a file that still has 200 lines
# resolves to whatever sits at line 5 now, so a reviewer reads a note about code
# that has moved elsewhere as though it described the code in front of them.
# Reproduced against a real store before this column existed: a note anchored at
# api/pay.py:99 in a six line file was accepted, listed and rendered, and no
# command ever mentioned that the line did not exist.
#
# WHY A HASH RATHER THAN THE LINE ITSELF. Two reasons, in this order. The
# column would otherwise hold source text, which is the kind of content the
# export policy has to withhold, and the name chosen here ends in _hash, so
# export_column withholds it BY SHAPE with no list to remember (see
# _DUMP_DIGEST_SUFFIXES). And a fingerprint is all the resolver needs: it can
# say "still there", "now at line 41" or "no longer in the file" from a digest
# alone, which is exactly what a reviewer has to be told.
#
# DEFAULT ''. An empty fingerprint means "not recorded" (a note written before
# schema 8, a whole-file anchor with no line, or an anchored line that was
# blank), and bm_learning.resolve_anchor_line reports that state as
# unverifiable rather than pretending the anchor was checked.
_NOTES_V8_COLUMN = ("anchor_line_hash", "TEXT NOT NULL DEFAULT ''")

# Schema 10 (LOOP 3, 2026-07-30): two columns added to learning_applications,
# not a widened shown_to_model. shown_to_model's own CHECK(shown_to_model IN
# (0,1)) cannot be altered in SQLite (ALTER TABLE has no MODIFY/DROP
# CONSTRAINT), which is the exact wall _migrate_8_to_9's own comment names
# for the receipt table, so a six-way distinction (present in the manifest,
# expanded in full, action reached, followed, violated, not relevant) is
# built ADDITIVELY instead of by widening a boolean. `disposition` already
# carries followed/ignored/not_relevant/unknown (a gate ignored while it
# applied IS a violation, read off the existing value; nothing new is needed
# for that half). What was missing is the PRESENTATION half (was this row
# shown as the compact manifest line or as full text) and whether the
# query's own wording reached the gate's action. 'unknown' is the default for
# both, and it STAYS 'unknown' for every row written before schema 10: same
# rule as anchor_line_hash above, no backfilled guess for a run this loop
# never observed.
_APPLICATIONS_V10_COLUMNS = (
    ("presentation",
     "TEXT NOT NULL DEFAULT 'unknown' "
     "CHECK(presentation IN ('manifest','expanded','unknown'))"),
    ("action_reached",
     "TEXT NOT NULL DEFAULT 'unknown' "
     "CHECK(action_reached IN ('yes','no','unknown'))"),
)

NOTE_KINDS = ("insight", "alert", "question", "review", "todo", "risk")
NOTE_SEVERITIES = ("", "info", "warning", "critical")
NOTE_AUTHOR_KINDS = ("founder", "assistant", "human")
NOTE_ANCHOR_TYPES = ("file", "candidate", "rule", "record", "decision")
# The one severity with teeth, on the one kind that has them.
BLOCKING_NOTE_KIND = "alert"
BLOCKING_NOTE_SEVERITY = "critical"

# The one column added to an existing table by any migration in this project.
# NULL for every row written before schema 4, and it STAYS null: a legacy
# application is reported as legacy by classify_learning_applications, never
# backfilled with a run that did not happen.
_APPLICATION_RUN_COLUMN = "retrieval_uuid"

_APPLICATION_RUN_COLUMN_DDL = (
    "ALTER TABLE learning_applications ADD COLUMN retrieval_uuid TEXT "
    "REFERENCES learning_retrieval_runs(retrieval_uuid)")


# ----------------------------------------------------------------------
# OPTIONAL FTS5 FAST PATH (post-audit LOOP P7).
#
# WHAT IS AND IS NOT PART OF THE STORE'S CONTRACT.
#   The index below is NOT part of the schema. It carries no schema_version, it
#   is absent from every _TABLES_* tuple, and _verify_schema_or_raise never
#   looks for it. That is deliberate and it is the whole invariant: a store
#   opens, reads, writes, verifies and passes its suite on a SQLite build with
#   no FTS5 module at all. Deleting the table by hand costs a founder nothing
#   but speed. Everything the index holds is DERIVED from learning_rule_versions
#   and can be rebuilt from it at any time.
#
# WHY IT IS OFF UNTIL ASKED FOR.
#   Project rule: an optional capability ships DISABLED and falls back to the
#   stdlib path. FTS5 is compiled into most SQLite builds but not all, its
#   tokenizer decides what counts as a word, and its ranking is a number the
#   founder cannot re-derive by hand. None of that should arrive by surprise in
#   a tool whose selling point is that its retrieval is explainable. So the
#   default mode stays lexical and the founder turns the fast path on with
#   BROTHERMODE_FTS5=1.
#
# WHAT IS INDEXED, AND WHAT MUST NEVER BE.
#   Only the fields of the CURRENT version of a rule: trigger, action, because,
#   domain and scope key. Those are exactly the fields that are already injected
#   into a model's context, so indexing them exposes nothing that retrieval did
#   not already show. Raw founder corrections (learning_candidates.raw_text),
#   evidence excerpts, and rejected candidate text are NEVER indexed. Those are
#   the columns the store treats as the sensitive ones, and an FTS index is a
#   second, unredacted copy of whatever goes into it. There is a test that reads
#   the index back and fails if founder source text is found in it.
_FTS_TABLE = "learning_rule_fts"
_FTS_REBUILD_TABLE = "learning_rule_fts_rebuild"

# The founder's opt in. Any of 1/true/yes/on enables the fast path; anything
# else, including the variable being unset, leaves retrieval lexical.
FTS5_ENV = "BROTHERMODE_FTS5"

# The force-unavailable switch, and it is not only a test hook: a founder whose
# SQLite has a broken FTS5 needs a way to turn the fast path off without
# editing code. It WINS over FTS5_ENV, because the safe direction is off.
FTS5_DISABLE_ENV = "BROTHERMODE_NO_FTS5"

_TRUE_VALUES = ("1", "true", "yes", "on")

# The indexed columns, in the order they are written. Named once so the
# creation DDL, the row writer and the drift check cannot disagree about which
# fields are in the index, which is the classic way a drift check starts
# passing while the index is wrong.
_FTS_TEXT_COLUMNS = ("trigger_text", "action_text", "because_text",
                     "domain", "scope_key")

# porter unicode61: unicode61 folds accents and case, so a French rule matches
# the same task text a bare ASCII tokenizer would miss, and Japanese text is at
# least stored and retrievable as whole runs rather than mangled. porter is
# English stemming, which is what buys "pushing" matching a rule written about
# "push"; it does nothing for French or Japanese, and this file does not
# pretend otherwise. rule_uuid and rule_version are UNINDEXED: they are
# identifiers to join on, not text to search.
_FTS_CREATE_SQL = (
    "CREATE VIRTUAL TABLE IF NOT EXISTS %%s USING fts5("
    "rule_uuid UNINDEXED, rule_version UNINDEXED, %s, "
    "tokenize=\"porter unicode61\")" % ", ".join(_FTS_TEXT_COLUMNS))


def fts5_requested(env=None):
    """Has the founder asked for the fast path? Pure, reads a mapping."""
    env = os.environ if env is None else env
    if (env.get(FTS5_DISABLE_ENV, "") or "").strip().lower() in _TRUE_VALUES:
        return False
    return (env.get(FTS5_ENV, "") or "").strip().lower() in _TRUE_VALUES


def _fts5_probe(conn):
    """Does THIS sqlite build actually have FTS5? Answered by asking it to
    build one, in temp, and throwing it away.

    Not answered from sqlite_version, and not from a compile-option list: both
    have been wrong on real builds, and the only question that matters is
    whether CREATE VIRTUAL TABLE ... USING fts5 succeeds on this connection.

    Raw execute rather than _exec on purpose (and listed as exempt in the
    suite's routing test with this reason): a missing fts5 module raises
    OperationalError, and _exec would read that as structural damage and
    QUARANTINE a perfectly healthy store. A probe that can destroy the thing it
    probes is worse than no probe."""
    try:
        conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS "
                     "temp.brothermode_fts5_probe USING fts5(x)")
        conn.execute("DROP TABLE IF EXISTS temp.brothermode_fts5_probe")
        return True
    except sqlite3.Error:
        return False


def _migrate_3_to_4(conn):
    """Schema 3 to 4: add the retrieval run. ADDITIVE ONLY.

    Also the ONE place schema 4 is applied, to a brand new store as well as to
    a migrating one (Store._ensure_schema calls this function directly), for
    the same reason _LEARNING_DDL is shared: two copies of a schema drift, and
    a fresh store that differs from a migrated one is a bug nobody sees until a
    founder who has been here since schema 1 hits it alone.

    The ALTER is guarded on the live schema rather than on the version number,
    which makes the step idempotent in the only way that matters: SQLite has no
    ADD COLUMN IF NOT EXISTS, and re-running an unguarded ALTER raises
    "duplicate column name" and would abort the caller's transaction.

    Runs INSIDE the caller's exclusive transaction (Store._migrate_from), so it
    must never COMMIT, never ROLLBACK and never open its own transaction. See
    _split_ddl for the incident that proved executescript cannot be used here.

    What it deliberately does NOT do: it does not invent a retrieval run for
    any application row that already exists. Those retrievals happened without
    their context being kept, and writing a plausible-looking run for them
    would manufacture exactly the historical facts this loop exists to stop the
    classifier from assuming."""
    for statement in _RETRIEVAL_RUN_DDL_STATEMENTS:
        conn.execute(statement)
    for statement in _RETRIEVAL_RUN_INDEX_STATEMENTS:
        conn.execute(statement)
    columns = set()
    for row in conn.execute("PRAGMA table_info(learning_applications)").fetchall():
        # Index 1 rather than the name, because this runs against both a
        # Row-factory connection (the live store) and a plain tuple one (a
        # test building an old store by hand).
        columns.add(row[1])
    if _APPLICATION_RUN_COLUMN not in columns:
        conn.execute(_APPLICATION_RUN_COLUMN_DDL)


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
def _migrate_2_to_3(conn):
    """Schema 2 to 3: add the approval receipt table. ADDITIVE ONLY.

    Same contract as _migrate_1_to_2 and for the same reasons: no existing row
    is read or rewritten, every statement is CREATE ... IF NOT EXISTS, and it
    runs inside the caller's BEGIN EXCLUSIVE so it must never commit, roll back
    or open a transaction of its own.

    What this migration deliberately does NOT do: it does not invalidate,
    rewrite or annotate any rule approved before receipts existed. Those rules
    were approved under the old, weaker guarantee, and rewriting history to make
    them look receipt-backed would be the dishonest half of this change. The
    honest half is that from here on, no NEW rule can be created without one."""
    for statement in _RECEIPT_DDL_STATEMENTS:
        conn.execute(statement)
    for statement in _RECEIPT_INDEX_STATEMENTS:
        conn.execute(statement)


def _migrate_4_to_5(conn):
    """Schema 4 to 5: add the handovers table. ADDITIVE ONLY.

    Same contract as every migration before it, and the same three
    prohibitions: no existing row is read or rewritten, every statement is
    CREATE ... IF NOT EXISTS, and it runs inside the caller's BEGIN EXCLUSIVE
    so it must never commit, roll back, or open a transaction of its own (see
    _split_ddl for the incident that proved executescript cannot be used here).

    What this migration deliberately does NOT do: it does not parse the
    handovers that older versions APPENDED into STATE.md and import them as
    rows. Those are human prose in a human file, written with a marker that was
    never a schema, and a parser guessing where one ends would either truncate a
    founder's handover or swallow the prose around it. They stay exactly where
    they are and stay readable; only NEW handovers use the table. That is the
    migration rule the loop plan states, and it is also the only honest option:
    there is no marker in those files reliable enough to round-trip."""
    for statement in _HANDOVER_DDL_STATEMENTS:
        conn.execute(statement)
    for statement in _HANDOVER_INDEX_STATEMENTS:
        conn.execute(statement)


def _migrate_5_to_6(conn):
    """Schema 5 to 6: replace the handover dedupe index. NO ROW IS TOUCHED.

    Schema 5 shipped UNIQUE(lifecycle_uuid, payload_fingerprint) across every
    handover row for all time. Schema 6 replaces it with
    UNIQUE(lifecycle_uuid, payload_fingerprint, heading) WHERE delivered_at IS
    NULL. See the _HANDOVER_DDL comment for why: the old key made an
    acknowledged handover permanently suppress the next one for the same
    lifecycle, so a second park could commit with no handover at all.

    This is the first migration that DROPs anything, and the exception is
    deliberate and narrow: an index is not data. Every handovers row survives
    byte for byte, and the new key is strictly WEAKER than the old one (fewer
    row pairs collide), so no existing row can fail it and the CREATE cannot
    raise on a store that was legal a moment ago. Nothing recreates the old
    index, and a store that has already been opened by schema 6 is left alone
    by the IF EXISTS / IF NOT EXISTS pair.

    Same contract as every migration before it otherwise: it runs inside the
    caller's BEGIN EXCLUSIVE, so it must never commit, roll back, or open a
    transaction of its own (see _split_ddl)."""
    conn.execute("DROP INDEX IF EXISTS handovers_lifecycle_fingerprint_idx")
    for statement in _HANDOVER_INDEX_STATEMENTS:
        conn.execute(statement)


def _migrate_6_to_7(conn):
    """Schema 6 to 7: add the notes table. ADDITIVE ONLY.

    Same contract as every migration before it, and the same three
    prohibitions: no existing row is read or rewritten, every statement is
    CREATE ... IF NOT EXISTS, and it runs inside the caller's BEGIN EXCLUSIVE
    so it must never commit, roll back, or open a transaction of its own (see
    _split_ddl for the incident that proved executescript cannot be used here).

    What this migration deliberately does NOT do: it does not invent notes out
    of existing rows. A transition note, a checkpoint blocker and a rejected
    candidate all look a little like an alert and none of them was written as
    one, so importing them would put words in an author's mouth and, worse,
    could manufacture a critical alert that refuses an approval nobody was
    warned about. Old stores arrive at schema 7 with an empty notes table, which
    is the honest state: nobody has written a note yet."""
    for statement in _NOTES_DDL_STATEMENTS:
        conn.execute(statement)
    for statement in _NOTES_INDEX_STATEMENTS:
        conn.execute(statement)


def _migrate_7_to_8(conn):
    """Schema 7 to 8: add notes.anchor_line_hash. ADDITIVE ONLY.

    One ALTER TABLE ADD COLUMN with a NOT NULL DEFAULT, which SQLite performs
    without rewriting a row and which cannot lose data: every existing note
    keeps every field it had and arrives with an empty fingerprint, reported as
    unverifiable rather than as a checked anchor.

    GUARDED ON PRAGMA table_info rather than assumed absent, because this step
    also runs from _ensure_schema for a brand new store, where the column may
    already be there: ADD COLUMN on an existing name is a hard sqlite3 error and
    a fresh store would refuse to open. The guard is what lets one text serve
    both paths, which is the rule every migration above follows.

    Same contract as every migration before it: it runs inside the caller's
    BEGIN EXCLUSIVE, so it must never commit, roll back, or open a transaction
    of its own (see _split_ddl).

    What it deliberately does NOT do: it does not open a single source file to
    backfill a fingerprint for an existing note. The file has had every
    opportunity to change since the note was written, so a fingerprint taken now
    would record TODAY's line as the anchored one and permanently destroy the
    only fact that could have proved the line moved. An empty fingerprint says
    "unknown", which is true; a backfilled one would say "unmoved", which would
    be a guess wearing evidence's clothes."""
    have = {r[1] for r in conn.execute("PRAGMA table_info(notes)").fetchall()}
    name, decl = _NOTES_V8_COLUMN
    if name not in have:
        conn.execute("ALTER TABLE notes ADD COLUMN %s %s" % (name, decl))


def _migrate_8_to_9(conn):
    """Schema 8 to 9: add the generic state-change receipt table. ADDITIVE
    ONLY.

    Same contract as every migration before it: no existing row is read,
    rewritten, or deleted, every statement is CREATE ... IF NOT EXISTS, and it
    runs inside the caller's BEGIN EXCLUSIVE, so it must never commit, roll
    back, or open a transaction of its own (see _split_ddl for the incident
    that proved executescript cannot be used here).

    What this migration deliberately does NOT do: it does not touch a single
    previously superseded, deprecated, forgotten or contradicted rule, and it
    does not touch a single previously resolved note. Those moves happened
    under the guarantee that existed at the time; rewriting them to look
    receipt-backed would be the dishonest half of this change, exactly as
    _migrate_2_to_3 states for the rules approved before receipts existed.
    From here on, supersede, resolve-conflict, deprecate, forget and resolving
    a critical alert all require one."""
    for statement in _STATE_CHANGE_RECEIPT_DDL_STATEMENTS:
        conn.execute(statement)
    for statement in _STATE_CHANGE_RECEIPT_INDEX_STATEMENTS:
        conn.execute(statement)


def _migrate_9_to_10(conn):
    """Schema 9 to 10: add learning_applications.presentation and
    .action_reached. ADDITIVE ONLY.

    Same contract as _migrate_7_to_8 (the last column-only migration): each
    is one ALTER TABLE ADD COLUMN with a NOT NULL DEFAULT, guarded on
    PRAGMA table_info so this is safe whether it runs against a genuinely
    old schema-9 store or, via _ensure_schema, against a brand new one that
    already has the column. Runs inside the caller's BEGIN EXCLUSIVE, so it
    must never commit, roll back, or open a transaction of its own.

    What this deliberately does NOT do: it does not read a single existing
    learning_applications row to infer what was actually shown for it. A row
    written before this loop existed has no recorded answer to "manifest or
    expanded", and 'unknown' says exactly that; guessing 'expanded' because
    that used to be the only shape full text came in would be describing
    today's categories onto a run that predates them."""
    have = {r[1] for r in conn.execute(
        "PRAGMA table_info(learning_applications)").fetchall()}
    for name, decl in _APPLICATIONS_V10_COLUMNS:
        if name not in have:
            conn.execute(
                "ALTER TABLE learning_applications ADD COLUMN %s %s"
                % (name, decl))


_MIGRATIONS = {
    1: _migrate_1_to_2,
    2: _migrate_2_to_3,
    3: _migrate_3_to_4,
    4: _migrate_4_to_5,
    5: _migrate_5_to_6,
    6: _migrate_6_to_7,
    7: _migrate_7_to_8,
    8: _migrate_8_to_9,
    9: _migrate_9_to_10,
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
# LOOP 11 GENERALISED THIS. Those three columns were withheld because they
# hold verbatim founder words; the reasoning above is not special to them.
# records.objective, records.evidence, digests.body, transitions.note,
# decisions.text and directives.text are founder prose too, and the scrubber
# was never able to catch prose: "never mention the Q3 miss to Acme" carries
# no secret SHAPE at all, so an ordinary dump reproduced it verbatim.
# _DUMP_WITHHELD_COLUMNS is therefore no longer a list to maintain: WITHHELD
# IS NOW THE DEFAULT for every text column that is not structurally safe
# (_DUMP_SAFE_COLUMNS) and not explicitly scrub-only
# (_DUMP_SCRUB_ONLY_COLUMNS). The name is kept because tests and comments
# refer to it, and it still documents the three original findings.
_DUMP_WITHHELD_COLUMNS = frozenset((
    ("learning_candidates", "raw_text"),
    ("learning_evidence", "excerpt"),
    ("learning_applications", "task_excerpt"),
    # The same founder text, mirrored onto the retrieval run (LOOP P6). Listed
    # explicitly rather than by column name alone, because the withhold set is
    # keyed on (table, column) and a new table carrying the same column name
    # would otherwise be scrubbed instead of withheld.
    ("learning_retrieval_runs", "task_excerpt"),
))

# FIX ROUND P3, 2026-07-29. redact_text is PATTERN based: it finds things that
# LOOK like secrets (keys, tokens, paths, addresses). A hex digest looks like
# nothing, so every *_hash and *_fingerprint column sailed through the
# default-deny pass verbatim. Not cosmetic: founder_response_hash is an unsalted
# sha256 of the founder's literal answer, and real answers are short ("oui",
# "yes", "yes, always"), so a ten-word wordlist turns the digest back into the
# words mint_approval_receipt promises the store never keeps. Identical answers
# also show as identical digests, which is exactly the correlation the design
# says it does not hold. Digests are therefore WITHHELD by name-shape, read from
# the live schema like everything else here, so the next digest column anyone
# adds is covered the day it exists rather than the day someone remembers to
# list it. A digest carries no diagnostic value in a dump anyway: you cannot
# read it, you can only compare it, and comparing is the leak. Columns already
# in _DUMP_SAFE_COLUMNS (git shas) are allowlisted before this rule is reached.
_DUMP_DIGEST_SUFFIXES = ("_hash", "_fingerprint")

# The ONLY founder-typed columns an ordinary export still renders, scrubbed
# rather than withheld. Both are short IDENTIFIERS in practice, not prose: a
# record's name is how a founder asks for that record by hand, and tier is a
# T1/T2/T3 enum in every non-adversarial store. Withholding the name would
# leave a dump with no human-readable handle at all (only the uuid), which is
# the point at which people reach for --raw and lose the whole policy. Both
# still pass through the secret scrubber AND absolute-path masking below, so
# a name of "AKIAIOSFODNN7EXAMPLE" or "/Users/someone/clients/acme" does not
# survive. Adding a column here is a deliberate privacy decision, and the
# structural test test_export_policy_scrub_only_set_stays_closed makes
# growing this set fail loudly rather than quietly.
_DUMP_SCRUB_ONLY_COLUMNS = frozenset((
    ("records", "name"),
    ("records", "tier"),
    # FIX-ROUND 11: claims.path was WITHHELD, which broke the thing the
    # fence primitive exists for. A second agent asking bm_fences which file
    # is fenced got "[WITHHELD: 5 chars of founder text]" and could not
    # avoid the collision. A claimed path is RELATIVE, project-internal
    # structure, which the path-masking comment below itself calls "exactly
    # what the policy says stays"; withholding it was a collision-safety
    # regression bought for no privacy. It is scrub-only, not safe, so a
    # caller who claims an ABSOLUTE path still gets it masked and a
    # secret-shaped one still gets it redacted.
    ("claims", "path"),
))

# FIX-ROUND 11 (reported and reproduced): session ids were listed as
# structurally SAFE, i.e. returned unchanged, on the theory that they are
# machine identifiers. They are not: --session is caller-supplied free text
# (a uuid is only the fallback when the flag is absent), so
# `claim --session "/Users/jane.doe/Clients/Acme"` put an absolute path, and
# `--session sk-live_...` put a live vendor key, into an ordinary dump
# VERBATIM, twice (records.session_id and transitions.session_id). Rather
# than withhold them outright, which would break every join a dump is read
# for, these columns are SHAPE-GATED: a value that looks like a generated
# session identifier passes unchanged, and anything else is withheld like
# any other founder text.
_DUMP_ID_SHAPED_COLUMNS = frozenset((
    ("records", "session_id"),
    ("transitions", "session_id"),
    ("autosave_receipts", "session_id"),
    ("autosave_receipts", "worktree_id"),
    ("learning_candidates", "source_session_id"),
    ("learning_evidence", "source_session_id"),
    ("learning_applications", "session_id"),
))

# "cli-<32 hex>" (_default_cli_session_id), a bare or dashed uuid, a worktree
# label, a short hand-typed tag. No separator, no space, no punctuation
# beyond . _ - and no room for a sentence.
_ID_SHAPED_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")


def is_id_shaped(value):
    """True when `value` is safe to export as an identifier: it has the shape
    of a generated id AND survives the secret scrubber unchanged, so a
    vendor key such as sk-live_abcdefghijklmnopqrstuvwx (which matches the
    shape) is still caught."""
    if not isinstance(value, str) or not _ID_SHAPED_RE.match(value):
        return False
    return redact_text(value) == value

# ABSOLUTE PATHS (LOOP 11 workstream A). A path is not secret-shaped, so the
# scrubber never touched it, yet "/Users/jane.doe/clients/acme-turnaround"
# names a person, an employer and a client in one string. Ordinary exports
# mask absolute POSIX paths, Windows drive paths (C:\...) and UNC paths
# (\\server\share). Relative paths are left alone: they are project-internal
# structure, which is exactly what the policy says stays.
#
# FIX-ROUND 11 (reported, reproduced, fixed here): the body class used to be
# the ASCII allowlist [A-Za-z0-9_.~\-/\\]. A match STOPS at the first
# character outside the class, and the (?<![A-Za-z0-9_]) lookbehind then
# blocks re-matching at the next separator, so the mask removed the
# WORTHLESS PREFIX and left the SENSITIVE TAIL standing:
#   /Users/mueller/Kunden/Siemens (real u-umlaut) -> "[PATH WITHHELD]ller/..."
#   /Users/<CJK name>/<CJK client>/ACME           -> both names visible
#   /Users/j/C++Projects/acme-secret  -> "[PATH WITHHELD]++Projects/acme-secret"
#   also @ % # & = and every other punctuation mark outside the allowlist.
# Every non-ASCII path component (CJK, Cyrillic, Greek, accented Latin, which
# is most of the world's home directories) leaked in full, and the stated
# LIMIT below claimed the only gap was a SPACE. The class is therefore now a
# DENYLIST: a path component is anything that is not whitespace, not a
# control character, and not one of the few characters that really do end a
# path in prose. Two flat classes in sequence, no alternation, no nesting, so
# matching stays linear (400k characters still mask in single-digit ms).
#
# LIMITS, stated rather than hidden, and this is now the WHOLE list:
#  - a path containing a SPACE is masked only up to that space
#    ("/Users/j/Dev Work/x" leaves "Work/x" visible). Deliberate: swallowing
#    spaces would eat the rest of any sentence that merely mentions a path,
#    which is worse in the text exports this also runs in.
#  - masking stops at " ' ` < > | , ; : ( ) [ ] { } for that same prose
#    reason. Some of those (" < > | :) are illegal in a Windows path
#    outright, the rest are legal but rare in a real one, and all of them
#    are common sentence punctuation; a path that does contain one is masked
#    only up to it.
#  - a trailing . ! or ? stays outside the marker, so "see /Users/j/x." keeps
#    its full stop.
_ABS_PATH_BODY = r"[^\s\x00-\x1f\x7f\"'`<>|,;:()\[\]{}]"
_ABS_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_])"
    r"(?:[A-Za-z]:[\\/]|\\\\|/)"
    # First component character: the body class minus the separators, so a
    # bare "/" or "//" in prose is not itself treated as a path.
    + r"[^\s\x00-\x1f\x7f\"'`<>|,;:()\[\]{}/\\]"
    + _ABS_PATH_BODY + r"*")

PATH_WITHHELD_MARKER = "[PATH WITHHELD]"

# Sentence punctuation that is legal in a POSIX filename but almost never
# used in one, and very often ends the sentence a path sits in.
_ABS_PATH_TRAILING = ".!?"


def _mask_one_path(match):
    """Replace one matched path, leaving trailing sentence punctuation."""
    matched = match.group(0)
    kept = matched.rstrip(_ABS_PATH_TRAILING)
    if len(kept) < 2:
        # Only a separator survived ("/." in prose): not a path, leave it.
        return matched
    return PATH_WITHHELD_MARKER + matched[len(kept):]


def mask_absolute_paths(text):
    """Replace absolute filesystem paths with PATH_WITHHELD_MARKER.

    Pure, no I/O, safe on any string. Returns the input unchanged when it is
    not a string, so a caller iterating sqlite rows never has to type-check."""
    if not isinstance(text, str) or not text:
        return text
    return _ABS_PATH_RE.sub(_mask_one_path, text)


def withheld_marker(value):
    """The one marker every withheld field uses. Structurally honest (you can
    see the field is populated and how much of it there is) without
    reproducing a character of it."""
    return "[WITHHELD: %d chars of founder text]" % len(value)


def export_column(table, column, value):
    """THE CENTRAL WITHHOLDING POLICY. Given one (table, column, value) from
    the store, return what an ordinary, non-raw export may show for it.

    Every JSON and text export that renders whole store rows goes through
    here, so the policy lives in exactly one place and a new column joins it
    by default rather than by remembering to add it. Order matters:

      1. digest-shaped column      -> WITHHELD, whatever else it is listed as
      2. structurally safe column  -> value, unchanged
      3. id-shaped column          -> value if it really is id-shaped,
                                      WITHHELD if the caller put prose,
                                      a path or a key in it
      4. scrub-only column         -> secret-scrubbed, paths masked
      5. anything else that is text-> WITHHELD entirely

    RELEASE CUT, 2026-07-29: the digest rule is FIRST, not last. FIX ROUND P3
    withheld digests inside dump() alone and reached them before the safe list;
    LOOP 11 moved the safe list in front of everything and listed two
    digest-shaped columns (learning_candidates.content_hash,
    learning_applications.task_fingerprint) as structural. Merging the two lanes
    with the safe check first would have re-exported those digests, which is the
    exact leak P3 closed, so the shape rule runs before the allowlist and covers
    every export rather than only dump. Git shas stay visible: they are named
    *_sha and *_head, not *_hash or *_fingerprint.

    Raises RedactionUnavailable through redact_text rather than falling back
    to cleartext, exactly like every other exit in this file."""
    if isinstance(value, str) and value and column.endswith(_DUMP_DIGEST_SUFFIXES):
        # Withheld by name-shape: see _DUMP_DIGEST_SUFFIXES. A short answer
        # behind an unsalted digest is guessable, and redact_text cannot see a
        # digest at all.
        return "[WITHHELD: %d-char digest]" % len(value)
    if (table, column) in _DUMP_SAFE_COLUMNS:
        return value
    if not isinstance(value, str) or not value:
        return value
    if (table, column) in _DUMP_ID_SHAPED_COLUMNS:
        return value if is_id_shaped(value) else withheld_marker(value)
    if (table, column) in _DUMP_SCRUB_ONLY_COLUMNS:
        return mask_absolute_paths(redact_text(value))
    return withheld_marker(value)


def withhold_digest_columns(table, row):
    """One store row as a CLI's --json may print it, with every digest-shaped
    column run through export_column. Pure; returns a new dict.

    WHY THIS EXISTS BESIDE export_column RATHER THAN INSTEAD OF IT. dump() renders
    whole rows and passes every column through the full policy. A CLI's --json
    prints ONE entity to the operator who just typed the command, so it
    deliberately shows columns dump withholds: a note's body is the text that
    operator typed a second earlier, and withholding it there would send people
    to --raw and lose the whole policy. The DIGEST rule is the one part that must
    hold on that surface too, because a digest is unreadable and therefore
    useless as diagnostics, while an unsalted digest of a line of a file is a
    confirmation oracle for text every other surface redacts.

    FIX ROUND P2, 2026-07-30, reproduced against a real store before this
    existed: `bm_store dump` printed notes.anchor_line_hash as
    "[WITHHELD: 64-char digest]" while `bm_learn notes --json` two commands away
    printed the exact sha256 of the anchored line, so a note anchored at
    .env line 3 handed out a byte for byte check on the value of
    SECRET_KEY=... that facts.json redacts. The column was named with a _hash
    suffix precisely so the shape rule would cover it; this is the surface where
    the shape rule was never reached."""
    out = dict(row)
    for column in list(out):
        if column.endswith(_DUMP_DIGEST_SUFFIXES):
            out[column] = export_column(table, column, out[column])
    return out

_DUMP_SAFE_COLUMNS = frozenset((
    ("meta", "key"), ("meta", "value"),
    ("records", "lifecycle_uuid"), ("records", "lifetime"),
    ("records", "state"),
    ("records", "created_at"), ("records", "updated_at"),
    ("claims", "lifecycle_uuid"),
    ("decisions", "lifecycle_uuid"), ("decisions", "created_at"),
    ("digests", "lifecycle_uuid"), ("digests", "created_at"),
    ("directives", "lifecycle_uuid"), ("directives", "created_at"),
    ("directives", "delivered_at"),
    ("transitions", "lifecycle_uuid"), ("transitions", "from_state"),
    ("transitions", "to_state"), ("transitions", "at"),
    ("autosave_receipts", "snapshot_sha"), ("autosave_receipts", "tree_sha"),
    ("autosave_receipts", "source_head"), ("autosave_receipts", "created_at"),
    # LOOP P12. Identifiers, two session ids and two timestamps only. heading
    # and body are DELIBERATELY absent: they are founder-typed handover prose
    # and go through the default-deny redaction like every other free-text
    # column. payload_fingerprint is not listed either, and does not need to
    # be: it ends in _fingerprint, so _DUMP_DIGEST_SUFFIXES withholds it by
    # shape. It is NAMED that way for exactly that reason: a bare 'fingerprint'
    # slipped past the shape rule and dumped in cleartext (caught by this
    # loop's own dump test), and matching the existing convention closes it
    # without inventing a second mechanism.
    ("handovers", "handover_uuid"), ("handovers", "lifecycle_uuid"),
    ("handovers", "from_session_id"), ("handovers", "to_session_id"),
    ("handovers", "delivered_at"), ("handovers", "created_at"),
    # Schema 7. Identifiers, schema enums and timestamps only. author,
    # anchor_key, body, resolution and override_reason are DELIBERATELY absent:
    # an author is a person's name, an anchor key is a path, and the other three
    # are human prose. They go through the default-deny redaction like every
    # other free-text column, so a dump shows that a critical alert exists and
    # withholds what it says.
    ("notes", "note_uuid"), ("notes", "kind"), ("notes", "severity"),
    ("notes", "author_kind"), ("notes", "anchor_type"),
    ("notes", "created_at"), ("notes", "resolved_at"),
    ("notes", "overridden_at"),
    # LOOP 11: the schema-2 learning tables were never listed here, because
    # under the old policy an unlisted column was merely SCRUBBED and a uuid
    # survives scrubbing unchanged. Under withhold-by-default an unlisted
    # uuid comes back as a length marker, which would make a dump unusable
    # (rows no longer join) without protecting anything: these are machine
    # identifiers, schema enums, content hashes and timestamps. Free-text
    # columns of the same tables (raw_text, proposed_*, review_note,
    # trigger/action/because, tags_json, scope_key, source_ref, excerpt,
    # note, task_excerpt, disposition_reason, *_ref) are deliberately absent
    # and are therefore withheld.
    ("learning_rules", "rule_uuid"), ("learning_rules", "state"),
    ("learning_rules", "rule_type"), ("learning_rules", "severity"),
    ("learning_rules", "scope_type"),
    ("learning_rules", "founder_approved_at"), ("learning_rules", "created_at"),
    ("learning_rules", "updated_at"), ("learning_rules", "superseded_by"),
    ("learning_rules", "forgotten_at"),
    ("learning_candidates", "candidate_uuid"),
    ("learning_candidates", "source_type"),
    ("learning_candidates", "source_record_uuid"),
    ("learning_candidates", "proposed_scope_type"),
    ("learning_candidates", "status"), ("learning_candidates", "content_hash"),
    ("learning_candidates", "created_at"), ("learning_candidates", "reviewed_at"),
    ("learning_candidates", "resulting_rule_uuid"),
    ("learning_rule_versions", "rule_uuid"),
    ("learning_rule_versions", "change_type"),
    ("learning_rule_versions", "source_candidate_uuid"),
    ("learning_rule_versions", "created_at"),
    ("learning_evidence", "evidence_uuid"), ("learning_evidence", "rule_uuid"),
    ("learning_evidence", "candidate_uuid"), ("learning_evidence", "polarity"),
    ("learning_evidence", "evidence_type"),
    ("learning_evidence", "source_record_uuid"),
    ("learning_evidence", "created_at"),
    ("learning_edges", "from_rule_uuid"), ("learning_edges", "to_rule_uuid"),
    ("learning_edges", "relation"), ("learning_edges", "created_at"),
    ("learning_applications", "application_uuid"),
    ("learning_applications", "rule_uuid"),
    ("learning_applications", "record_uuid"),
    ("learning_applications", "task_fingerprint"),
    ("learning_applications", "retrieved_at"),
    ("learning_applications", "scope_match"),
    ("learning_applications", "disposition"),
    ("learning_applications", "outcome"),
    ("learning_applications", "closed_at"),
    # LOOP 3 (schema 10): presentation and action_reached are schema enums,
    # exactly like disposition and outcome above, never founder-typed free
    # text, so they belong on this list for the same reason those two do.
    ("learning_applications", "presentation"),
    ("learning_applications", "action_reached"),
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
            # LOOP P7: the optional fast path, after the schema is known good
            # and inside the same protected block. It cannot raise past its own
            # body; the worst case is that the store opens lexical.
            self._ensure_fts()
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
        if SCHEMA_VERSION >= 3:
            self.conn.executescript(_RECEIPT_DDL)
        if SCHEMA_VERSION >= 4:
            # The migration step itself, not a copy of it: see _migrate_3_to_4
            # on why a fresh store and a migrated store must run one text.
            _migrate_3_to_4(self.conn)
        if SCHEMA_VERSION >= 5:
            # Same rule as schema 4 above: the migration step is the ONE text,
            # run here for a fresh store and by _migrate_from for an old one.
            _migrate_4_to_5(self.conn)
        if SCHEMA_VERSION >= 6:
            # A fresh store already gets the schema-6 index shape from
            # _migrate_4_to_5 (both run the same _HANDOVER_INDEX_STATEMENTS),
            # so this is a no-op DROP of a name that was never created. It runs
            # anyway for the same reason as the two above: one text, one path,
            # no drift between a store born at 6 and one migrated to it.
            _migrate_5_to_6(self.conn)
        if SCHEMA_VERSION >= 7:
            # Same rule as every step above: the migration step is the ONE text,
            # run here for a fresh store and by _migrate_from for an old one.
            _migrate_6_to_7(self.conn)
        if SCHEMA_VERSION >= 8:
            # Same rule again. _migrate_7_to_8 checks PRAGMA table_info before
            # its ALTER TABLE precisely so this call is safe on a store that was
            # just created with the column already present.
            _migrate_7_to_8(self.conn)
        if SCHEMA_VERSION >= 9:
            # Same rule as every step above: the migration step is the ONE
            # text, run here for a fresh store and by _migrate_from for an
            # old one.
            _migrate_8_to_9(self.conn)
        if SCHEMA_VERSION >= 10:
            # Same rule again. _migrate_9_to_10 checks PRAGMA table_info
            # before its ALTER TABLE precisely so this call is safe on a
            # store that was just created with the columns already present.
            _migrate_9_to_10(self.conn)
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
        if SCHEMA_VERSION >= 3:
            self.conn.executescript(_RECEIPT_INDEX_DDL)
        if SCHEMA_VERSION >= 4:
            self.conn.executescript(_RETRIEVAL_RUN_INDEX_DDL)
        if SCHEMA_VERSION >= 5:
            self.conn.executescript(_HANDOVER_INDEX_DDL)
        if SCHEMA_VERSION >= 7:
            self.conn.executescript(_NOTES_INDEX_DDL)
        if SCHEMA_VERSION >= 9:
            self.conn.executescript(_STATE_CHANGE_RECEIPT_INDEX_DDL)

    # ------------------------------------------------------------------
    # The optional FTS5 fast path (LOOP P7). Read the block above
    # _FTS_TABLE first: nothing here is allowed to make the store depend
    # on FTS5, and every method in this section is written so that the
    # failure direction is "mode falls back to lexical", never "the store
    # refuses" and never "an index quietly disagrees with the rules".
    # ------------------------------------------------------------------

    def fts_available(self):
        """Is the fast path in force RIGHT NOW for this open store?

        Three conditions, all required: the founder asked for it, this SQLite
        can build one, and the index table exists. Anything else is False and
        retrieval stays lexical."""
        return bool(getattr(self, "_fts_ready", False))

    def _fts_exec(self, sql, params=()):
        """The ONE routing point for statements against the INDEX table.

        Deliberately not _exec, and this is the whole point (P7 fix round).
        _exec sends any non-transient OperationalError to
        _quarantine_and_raise, which MOVES store.sqlite3 and its sidecars into
        a quarantine directory and raises StoreCorrupt. "no such table:
        learning_rule_fts" is exactly that shape, so an OPTIONAL accelerator
        losing its table mid-session took the founder's whole database with
        it, along with the approval in flight. Worse, the `except
        sqlite3.Error` guards written around those calls to keep the failure
        direction lexical could never fire: StoreCorrupt is not a subclass of
        sqlite3.Error, so they were dead code. Reproduced before this fix on a
        real store: drop the index table, approve a candidate, and the result
        was StoreCorrupt with the database gone.

        So the index gets its own routing point with no quarantine in it. A
        sqlite error here comes back to the caller AS a sqlite3.Error, the
        caller switches the fast path off, and retrieval is lexical, which is
        the mode that always works. Statements against the REAL tables stay on
        _exec, where damage still means damage and quarantine is correct."""
        return self.conn.execute(sql, params)

    def _fts_table_exists(self):
        row = _exec(self, "SELECT name FROM sqlite_master WHERE type='table' "
                          "AND name=?", (_FTS_TABLE,)).fetchone()
        return row is not None

    def _ensure_fts(self):
        """Bring the index into existence if it is wanted and possible.

        Called from the same protected open-time path as _ensure_indexes, and
        it can fail in any way it likes: every failure leaves _fts_ready False,
        which means lexical retrieval, which is the mode that always works.

        A brand new index is POPULATED here rather than left empty, because an
        empty index is not the same as a missing one: it would answer every
        query with nothing, and the relevance floor would then hide rules that
        the lexical path would have found. Populating an already-populated
        index is skipped, so this costs one COUNT(*) per open."""
        self._fts_ready = False
        if not fts5_requested():
            return
        if not _fts5_probe(self.conn):
            return
        try:
            existed = self._fts_table_exists()
            self._fts_exec(_FTS_CREATE_SQL % _FTS_TABLE)
            if not existed:
                self._fts_reindex_all()
            self._fts_ready = True
        except (sqlite3.Error, OwnershipRefused):
            # Includes the store having been quarantined by _exec underneath
            # us. Nothing to repair here and nothing to report: the caller's
            # next statement will hit the same condition on the real tables.
            self._fts_ready = False

    def _fts_rows_for_rule(self, rule_uuid):
        """The index row(s) this rule SHOULD have: exactly one, built from its
        current version. Returns [] when the rule or its version is gone, which
        is how a forgotten or half-written rule ends up correctly absent."""
        row = _exec(self,
              "SELECT r.rule_uuid, r.current_version, r.scope_key, "
              "  v.trigger_text, v.action_text, v.because_text, v.domain "
              "FROM learning_rules r JOIN learning_rule_versions v "
              "  ON v.rule_uuid = r.rule_uuid AND v.version = r.current_version "
              "WHERE r.rule_uuid = ?", (rule_uuid,)).fetchone()
        if row is None:
            return []
        return [(row["rule_uuid"], row["current_version"], row["trigger_text"],
                 row["action_text"], row["because_text"], row["domain"],
                 row["scope_key"])]

    def _fts_write_rule(self, rule_uuid):
        """Replace this rule's index row. CALLER HOLDS THE TRANSACTION.

        That is the transactional maintenance the plan asks for: the index row
        lands in the same BEGIN IMMEDIATE as the rule version it describes, so
        a crash between the two is not a state this store can reach.

        If the index write itself fails, the index is DROPPED inside that same
        transaction and the fast path is switched off for this connection. That
        is the deliberate choice: an optional accelerator must never turn a
        founder's rule approval into a refusal, and a half-written index is
        worse than none, so it does not survive either."""
        if not self.fts_available():
            return
        try:
            self._fts_exec("DELETE FROM %s WHERE rule_uuid = ?" % _FTS_TABLE,
                           (rule_uuid,))
            for row in self._fts_rows_for_rule(rule_uuid):
                self._fts_exec("INSERT INTO %s (rule_uuid, rule_version, %s) "
                               "VALUES (?,?,?,?,?,?,?)"
                               % (_FTS_TABLE, ", ".join(_FTS_TEXT_COLUMNS)), row)
        except sqlite3.Error:
            self._fts_ready = False
            try:
                self._fts_exec("DROP TABLE IF EXISTS %s" % _FTS_TABLE)
            except sqlite3.Error:
                # The drop failed too, so the transaction cannot be left to
                # commit: a stale index would survive with no way to know it.
                raise

    def _fts_reindex_all(self):
        """Fill the CURRENT index table from the rules. Caller supplies the
        transaction (or accepts autocommit at open time)."""
        self._fts_exec("DELETE FROM %s" % _FTS_TABLE)
        for row in _exec(self,
                "SELECT r.rule_uuid, r.current_version, r.scope_key, "
                "  v.trigger_text, v.action_text, v.because_text, v.domain "
                "FROM learning_rules r JOIN learning_rule_versions v "
                "  ON v.rule_uuid = r.rule_uuid "
                "  AND v.version = r.current_version").fetchall():
            self._fts_exec("INSERT INTO %s (rule_uuid, rule_version, %s) "
                           "VALUES (?,?,?,?,?,?,?)"
                           % (_FTS_TABLE, ", ".join(_FTS_TEXT_COLUMNS)),
                           (row["rule_uuid"], row["current_version"],
                            row["trigger_text"], row["action_text"],
                            row["because_text"], row["domain"],
                            row["scope_key"]))

    def _fts_reconcile(self):
        """Make the index agree with the rules BEFORE anything reads it, or
        switch the fast path off. True when the index may be trusted.

        THE BUG THIS EXISTS FOR (P7 fix round, reproduced on the real CLI).
        The index is maintained only by connections that have the fast path
        on, and the switch is a per-PROCESS environment variable. One ordinary
        shell that approves or edits a rule without it leaves the index behind
        with no error anywhere, and _ensure_fts repopulated only when it had
        just CREATED the table, so that gap was permanent: the next FTS5 run
        found a table, trusted it, and answered from text the founder had
        already deleted, while the CLI explained the hit as a stem match that
        no live word could produce. That is a correctness failure, not a
        reporting one: bm25 dominates the ranking, so a stale row outranked a
        rule with three times its exact overlap, and --limit then dropped the
        right rule entirely.

        The fix is placed at the point of CONSUMPTION rather than at open,
        because open time cannot see a write another process makes a second
        later, and because verify and index-status keep their value only if
        they can still SEE drift and say so. Cost is two small queries per
        retrieval against a table holding one row per founder rule.

        Repair needs write authority. A store that cannot repair (locked by
        another writer, read-only) turns the fast path off and takes the
        lexical path, which is the mode that always works and is reported
        honestly as mode=lexical."""
        if not self.learning_fts_drift():
            return True
        try:
            self._fts_reindex_all()
        except (sqlite3.Error, OwnershipRefused):
            self._fts_ready = False
            return False
        if self.learning_fts_drift():
            # Repaired and still disagreeing: something about this index is
            # beyond a rewrite, so it does not get to answer queries.
            self._fts_ready = False
            return False
        return True

    def _fts_scores(self, query):
        """BM25 scores by rule_uuid for this task text, or None when the fast
        path did not answer.

        None and {} mean different things and both are load bearing: None means
        NO index query happened, so the run must report mode lexical; {} means
        the index was asked and matched nothing, which is a real fts5 answer.

        _fts_exec rather than _exec: a malformed MATCH expression raises
        OperationalError, and _exec would treat that as structural damage and
        quarantine a healthy store over a founder's punctuation.
        fts_match_query quotes every token precisely so this cannot happen,
        and the except below is the second belt: the fast path switches itself
        off and the caller gets lexical.

        The index is RECONCILED before it answers, every time, because this is
        the one place it is consumed and a stale index here is wrong answers
        rather than slow ones (see _fts_reconcile). That check sits AFTER the
        match expression is built, so a task with nothing searchable in it
        costs nothing: the index is not being asked, so it does not need to be
        right yet."""
        if not self.fts_available():
            return None
        L = _learning()
        match = L.fts_match_query(query)
        if not match:
            # Nothing searchable in the task text. The index was never asked,
            # so claiming mode fts5 would be a lie about where the ranking
            # came from.
            return None
        if not self._fts_reconcile():
            return None
        try:
            rows = self._fts_exec(
                "SELECT rule_uuid, bm25(%s) AS score FROM %s WHERE %s MATCH ?"
                % (_FTS_TABLE, _FTS_TABLE, _FTS_TABLE), (match,)).fetchall()
        except sqlite3.Error:
            self._fts_ready = False
            return None
        return dict((r["rule_uuid"], r["score"]) for r in rows)

    def learning_index_status(self):
        """What the fast path is doing right now, in numbers a founder can
        check. Read only, and safe on a store with no index at all.

        "Safe" now means it: this counted through _exec, so a missing index
        table made a DIAGNOSTIC quarantine the store (P7 fix round). A
        diagnostic that can destroy what it inspects is worse than no
        diagnostic. An unreadable index now reads as the fast path being off,
        which is what it is."""
        L = _learning()
        requested = fts5_requested()
        available = self.fts_available()
        indexed = None
        if available:
            try:
                row = self._fts_exec(
                    "SELECT COUNT(*) AS n FROM %s" % _FTS_TABLE).fetchone()
                indexed = int(row["n"]) if row else 0
            except sqlite3.Error:
                self._fts_ready = False
                available = False
                indexed = None
        return {
            "requested": requested,
            "available": available,
            "mode": L.FTS5_MODE if available else L.RETRIEVAL_MODE,
            "indexed_rows": indexed,
            "rules": len(self.list_learning_rules(include_forgotten=True)),
            "enable_with": "%s=1" % FTS5_ENV,
            "disable_with": "%s=1" % FTS5_DISABLE_ENV,
        }

    def learning_fts_drift(self):
        """Every way the index can disagree with the rules, as a list of
        (code, detail, refs) tuples. Empty when there is nothing to compare.

        This is the check that makes the fast path trustworthy: an index is a
        SECOND copy of the truth, and a second copy nobody compares is just a
        way to be confidently wrong. Four disagreements are detected, and each
        one is a real failure mode rather than a symmetry for its own sake:
        a rule with no row (retrieval silently loses it), a row with no rule
        (a deleted or forgotten rule still matching), a row pinned to an old
        version (the founder's edit did not reach the index), and a row whose
        text differs from the version it names (the worst one, because both
        sides look internally consistent)."""
        out = []
        if not self.fts_available():
            return out
        want = {}
        for row in _exec(self,
                "SELECT r.rule_uuid, r.current_version, r.scope_key, "
                "  v.trigger_text, v.action_text, v.because_text, v.domain "
                "FROM learning_rules r JOIN learning_rule_versions v "
                "  ON v.rule_uuid = r.rule_uuid "
                "  AND v.version = r.current_version").fetchall():
            want[row["rule_uuid"]] = (
                int(row["current_version"]),
                tuple((row[c] or "") for c in _FTS_TEXT_COLUMNS))
        have = {}
        try:
            index_rows = self._fts_exec(
                "SELECT rule_uuid, rule_version, %s FROM %s"
                % (", ".join(_FTS_TEXT_COLUMNS), _FTS_TABLE)).fetchall()
        except sqlite3.Error as e:
            # The index cannot be read at all (dropped underneath us, most
            # likely). That is drift of the loudest kind, and it is reported
            # as drift; through _exec it used to QUARANTINE THE STORE from
            # inside a read-only check (P7 fix round).
            self._fts_ready = False
            return [("fts-drift", "the search index could not be read (%s), so "
                     "the fast path is off and retrieval is lexical; rebuild "
                     "it with bm_learn.py rebuild-index" % e, ())]
        for row in index_rows:
            have.setdefault(row["rule_uuid"], []).append(
                (int(row["rule_version"] or 0),
                 tuple((row[c] or "") for c in _FTS_TEXT_COLUMNS)))
        for ruuid in sorted(want):
            rows = have.get(ruuid, [])
            if not rows:
                out.append(("fts-drift", "rule %s has no row in the search "
                            "index, so the fast path cannot return it"
                            % ruuid[:8], (ruuid,)))
                continue
            if len(rows) > 1:
                out.append(("fts-drift", "rule %s has %d rows in the search "
                            "index and must have exactly one"
                            % (ruuid[:8], len(rows)), (ruuid,)))
            version, text = want[ruuid]
            for have_version, have_text in rows:
                if have_version != version:
                    out.append(("fts-drift", "the search index holds version %d "
                                "of rule %s but its current version is %d"
                                % (have_version, ruuid[:8], version), (ruuid,)))
                elif have_text != text:
                    # Deliberately does NOT print either text. A drift report
                    # is a diagnostic, not a second place founder rule text
                    # gets copied to.
                    out.append(("fts-drift", "the search index text for rule %s "
                                "does not match version %d of that rule"
                                % (ruuid[:8], version), (ruuid,)))
        for ruuid in sorted(have):
            if ruuid not in want:
                out.append(("fts-drift", "the search index holds rule %s, which "
                            "has no current rule version behind it"
                            % (ruuid or "")[:8], (ruuid,)))
        return out

    def rebuild_learning_index(self):
        """Rebuild the search index from the rules, atomically.

        Built into a SEPARATE table and swapped in, all inside one BEGIN
        IMMEDIATE: a reader either sees the whole old index or the whole new
        one, and a crash halfway leaves the old index untouched rather than a
        half-filled one that verify would then have to explain. Rebuilding in
        place would be atomic too by virtue of the transaction, but it would
        also be a window in which the index is empty for anything sharing this
        connection, and this way there is no such window at all."""
        L = _learning()
        if not fts5_requested():
            return {"ok": False, "mode": L.RETRIEVAL_MODE, "indexed": 0,
                    "reason": "the search index is off; enable it with %s=1"
                              % FTS5_ENV}
        if not _fts5_probe(self.conn):
            return {"ok": False, "mode": L.RETRIEVAL_MODE, "indexed": 0,
                    "reason": "this SQLite build has no FTS5 module, so the "
                              "lexical path is the only one available"}
        try:
            return self._rebuild_learning_index_inner(L)
        except sqlite3.Error as e:
            # The rebuild is the REPAIR command, so it is the last place that
            # may take the store down with it: through _exec these statements
            # quarantined the file (P7 fix round). A rebuild that cannot
            # finish leaves the fast path off and says why, through the same
            # ok/reason shape the CLI already turns into exit 2.
            self._fts_ready = False
            return {"ok": False, "mode": L.RETRIEVAL_MODE, "indexed": 0,
                    "reason": "the search index could not be rebuilt (%s); "
                              "retrieval stays lexical" % e}

    def _rebuild_learning_index_inner(self, L):
        """The rebuild itself, split out so rebuild_learning_index owns one
        try/except around the whole transaction rather than one per statement."""
        with self._transaction():
            self._fts_exec("DROP TABLE IF EXISTS %s" % _FTS_REBUILD_TABLE)
            self._fts_exec(_FTS_CREATE_SQL % _FTS_REBUILD_TABLE)
            for row in _exec(self,
                    "SELECT r.rule_uuid, r.current_version, r.scope_key, "
                    "  v.trigger_text, v.action_text, v.because_text, v.domain "
                    "FROM learning_rules r JOIN learning_rule_versions v "
                    "  ON v.rule_uuid = r.rule_uuid "
                    "  AND v.version = r.current_version").fetchall():
                self._fts_exec("INSERT INTO %s (rule_uuid, rule_version, %s) "
                               "VALUES (?,?,?,?,?,?,?)"
                               % (_FTS_REBUILD_TABLE, ", ".join(_FTS_TEXT_COLUMNS)),
                               (row["rule_uuid"], row["current_version"],
                                row["trigger_text"], row["action_text"],
                                row["because_text"], row["domain"],
                                row["scope_key"]))
            self._fts_exec("DROP TABLE IF EXISTS %s" % _FTS_TABLE)
            self._fts_exec("ALTER TABLE %s RENAME TO %s"
                           % (_FTS_REBUILD_TABLE, _FTS_TABLE))
        self._fts_ready = True
        row = self._fts_exec("SELECT COUNT(*) AS n FROM %s" % _FTS_TABLE).fetchone()
        return {"ok": True, "mode": L.FTS5_MODE,
                "indexed": int(row["n"]) if row else 0, "reason": ""}

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
        # A PREFIX is accepted here, resolved to the one record it names or
        # refused by name (schema 7, 2026-07-30). Before this, only a full
        # lifecycle uuid worked and anything shorter was written straight into
        # source_record_uuid, where it linked to no record at all. That link is
        # now load bearing: gate_change_set reads the record's claimed paths to
        # decide which files an approval would change, so a silently broken link
        # would mean an alert anchored to a changed file quietly failing to
        # refuse. Every other id-taking method in this file already resolves a
        # prefix; this one was the exception.
        if record_uuid:
            record_uuid = self._resolve_record_uuid(record_uuid)
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

    def mint_approval_receipt(self, prefix, founder_response, trigger=None,
                               action=None, because=None, scope_type=None,
                               scope_key=None, rule_type="preference",
                               severity="soft", domain=None,
                               atomicity_override="", conflict_override="",
                               alerts_override="",
                               ttl_seconds=APPROVAL_RECEIPT_TTL_SECONDS):
        """Record that a human answered a question about ONE candidate, and
        return a one-time token that lets `approve` act on that answer.

        This is the founder-side half of Model A (post-audit LOOP 3, founder
        decision 2026-07-29). It exists because the previous design was honest
        about intent and dishonest about mechanism: `approve` took a free-text
        founder_ref, the CLI GENERATED a default one saying "run by the
        founder", and any process that could invoke the CLI, or import this
        module, could therefore manufacture an approved rule with nobody
        answering anything. Reproduced on 2026-07-29 against a throwaway store:
        an imported call to bm_learn.main(["approve", id]) created rule 90dc290e
        at exit 0 with no human in the loop.

        WHAT THIS DOES AND DOES NOT PROVE. It proves that this token was minted,
        against this candidate, against this exact rule text, and has not been
        spent. It does NOT prove which human typed the answer: nothing here
        authenticates an identity, and no wording in this project may claim it
        does. What changes is that a background process can no longer approve by
        accident or by default, because there is no default: the token is 48
        hex characters of os.urandom that never touches the store, so it cannot
        be derived from anything a hook can read.

        founder_response is the founder's literal answer. It is HASHED, never
        stored: the store keeps no copy of the words, which keeps the most
        sensitive text in this flow out of the file, out of dump, and out of
        every display surface.

        The returned dict carries the token under "token". That value is the
        secret. Print it once to the person who answered, never into a log."""
        L = _learning()
        if not (founder_response or "").strip():
            raise OwnershipRefused(
                "no-founder-response",
                "minting an approval receipt requires the founder's actual "
                "answer; a receipt with nothing behind it is the forgery this "
                "whole mechanism exists to stop")
        cand = self.get_learning_candidate(prefix)
        if cand["status"] != "pending":
            raise OwnershipRefused(
                "not-pending",
                "candidate %s is %r, only a pending candidate can be approved"
                % (cand["candidate_uuid"][:8], cand["status"]))
        prop = _resolve_proposal(L, cand, trigger, action, because, scope_type,
                                 scope_key, domain, rule_type, severity,
                                 atomicity_override, conflict_override,
                                 alerts_override)
        # Every refusal approval would raise, raised HERE too, so no token is
        # ever printed for a rule the founder was not told the truth about
        # (FIX ROUND P3). The override flags are in the fingerprint above, so a
        # token minted for the clean question cannot be spent with an override.
        guards = _approval_guards(self, L, prop, cand)
        try:
            ttl = int(ttl_seconds)
        except (TypeError, ValueError):
            ttl = APPROVAL_RECEIPT_TTL_SECONDS
        # Clamped, not validated: a caller asking for a week gets fifteen
        # minutes rather than an error, because the ceiling is the property that
        # matters and no caller has a reason to exceed it.
        ttl = max(1, min(ttl, APPROVAL_RECEIPT_TTL_SECONDS))
        token = secrets.token_hex(24)
        ruuid = uuid.uuid4().hex
        issued = datetime.datetime.now(datetime.timezone.utc)
        expires = issued + datetime.timedelta(seconds=ttl)
        with self._transaction():
            _exec(self,
                  "INSERT INTO learning_approval_receipts (receipt_uuid, "
                  "candidate_uuid, approval_choice, nonce_hash, "
                  "candidate_fingerprint, founder_response_hash, issued_at, "
                  "expires_at) VALUES (?,?,'approve',?,?,?,?,?)",
                  (ruuid, cand["candidate_uuid"], _receipt_token_hash(token),
                   _proposal_fingerprint(L, cand, prop),
                   hashlib.sha256(
                       L.normalize_text(founder_response).encode("utf-8")).hexdigest(),
                   issued.strftime("%Y-%m-%dT%H:%M:%SZ"),
                   expires.strftime("%Y-%m-%dT%H:%M:%SZ")))
        out = dict(_exec(self, "SELECT * FROM learning_approval_receipts "
                               "WHERE receipt_uuid=?", (ruuid,)).fetchone())
        # nonce_hash back out of the returned dict: a caller printing the whole
        # record must not print the one column that could be brute forced if the
        # token were ever shortened.
        out.pop("nonce_hash", None)
        out["token"] = token
        out["ttl_seconds"] = ttl
        # What the founder should have been shown, carried back so the CLI can
        # print it beside the token. Present even when an override made the
        # guard pass, because "you are overriding this" is the part he most
        # needs to see written down.
        out["atomicity_problems"] = guards["atomicity_problems"]
        out["contradicts"] = [o["rule_uuid"][:8]
                              for o, _v in guards["conflicts"]["contradictions"]]
        out["duplicates"] = [o["rule_uuid"][:8]
                             for o, _v in guards["conflicts"]["duplicates"]]
        out["override_atomicity"] = prop["override_atomicity"]
        out["override_conflict"] = prop["override_conflict"]
        out["override_alerts"] = prop["override_alerts"]
        # Same reason as the three lines above: an alert being overridden is the
        # part the founder most needs to see written down beside the token.
        out["blocking_alerts"] = [
            {"note_uuid": a["note_uuid"], "author": a["author"],
             "matched": a["matched"], "body": a["body"]}
            for a in guards["blocking_alerts"]]
        return out

    def get_approval_receipt(self, receipt_uuid):
        """Read a receipt by its PUBLIC uuid, for display and for verify. Never
        returns nonce_hash, and there is deliberately no lookup that returns it:
        the token hash leaves this module only through the private consumption
        path below."""
        row = _exec(self, "SELECT * FROM learning_approval_receipts "
                          "WHERE receipt_uuid LIKE ?",
                    (receipt_uuid + "%",)).fetchone()
        if row is None:
            raise OwnershipRefused("no-such-receipt",
                                   "no approval receipt matches %r" % (receipt_uuid,))
        out = dict(row)
        out.pop("nonce_hash", None)
        return out

    def _receipt_for_token(self, token):
        """Look a receipt up BY ITS TOKEN, or refuse.

        The refusal deliberately says nothing about whether the token was
        unknown, malformed or for another store: a caller guessing tokens
        learns nothing from the message it gets back."""
        row = _exec(self, "SELECT * FROM learning_approval_receipts "
                          "WHERE nonce_hash=?",
                    (_receipt_token_hash(token),)).fetchone()
        if row is None:
            raise OwnershipRefused(
                "bad-approval-receipt",
                "that approval receipt is not valid for this store. Ask the "
                "founder the question again and mint a fresh one with "
                "`bm_learn.py grant-approval`.")
        return dict(row)

    def approve_learning_candidate(self, prefix, founder_ref, receipt="",
                                    trigger=None,
                                    action=None, because=None, scope_type=None,
                                    scope_key=None, rule_type="preference",
                                    severity="soft", domain=None,
                                    atomicity_override="", conflict_override="",
                                    alerts_override=""):
        """Promote a candidate into an approved rule. ATOMIC and RECEIPT-GATED.

        `receipt` is a one-time token from mint_approval_receipt, and it is
        MANDATORY. Without it this refuses and writes nothing. That is the whole
        of Model A: the door into the injectable rule set opens only for an
        answer a human actually gave, about this candidate, about this rule
        text, within the last fifteen minutes, and only once.

        Six checks, every one of them fail-CLOSED, and the last four repeated
        inside the transaction as a single conditional UPDATE so that two
        approvals racing for the same receipt cannot both win:
          * the token resolves to a receipt in THIS store;
          * the receipt is for THIS candidate;
          * the receipt has not been consumed;
          * the receipt has not expired;
          * the candidate and the rule text still fingerprint the same as when
            the founder was asked;
          * consumption and rule creation are the same transaction.

        founder_ref stays mandatory and stays free-form. It is now the
        HUMAN-READABLE half of provenance (which question, which conversation),
        not the gate: the receipt is the gate. A model's own judgement is still
        not a founder_ref, and this still does not authenticate an identity.

        All six writes (receipt consumption, rule, version 1, approval evidence,
        candidate status, resulting link) happen in ONE transaction. A failure
        part way leaves the candidate pending and the receipt unspent, never
        half approved."""
        L = _learning()
        if not (founder_ref or "").strip():
            raise OwnershipRefused("no-founder-ref", "approval requires an explicit founder reference; a rule with no "
                "recorded approver is exactly what invariant L1 forbids")
        if not (receipt or "").strip():
            raise OwnershipRefused(
                "no-approval-receipt",
                "approval requires a one-time receipt from a real founder "
                "answer. Ask the question, then run `bm_learn.py "
                "grant-approval <candidate> --answer \"<what he said>\"` and "
                "pass the token to approve. There is no override and no "
                "break-glass: a rule nobody answered for is the exact thing "
                "this refuses to create.")
        cand = self.get_learning_candidate(prefix)
        if cand["status"] != "pending":
            raise OwnershipRefused("not-pending", "candidate %s is %r, only a pending candidate can be approved"
                % (cand["candidate_uuid"][:8], cand["status"]))
        rec = self._receipt_for_token(receipt.strip())
        if rec["candidate_uuid"] != cand["candidate_uuid"]:
            raise OwnershipRefused(
                "receipt-wrong-candidate",
                "that receipt was issued for candidate %s, not %s. One answer "
                "approves one candidate."
                % (rec["candidate_uuid"][:8], cand["candidate_uuid"][:8]))
        if rec["consumed_at"] is not None:
            raise OwnershipRefused(
                "receipt-already-used",
                "that receipt was already spent at %s. An answer approves once; "
                "ask again for another rule." % rec["consumed_at"])
        if rec["expires_at"] < now_iso():
            raise OwnershipRefused(
                "receipt-expired",
                "that receipt expired at %s. A stale answer is not consent to "
                "whatever the candidate says now: ask again."
                % rec["expires_at"])
        # Scrubbed here as well as at capture: approval accepts NEW text typed
        # on the command line, so the candidate having been cleaned says nothing
        # about what the founder just passed in (LOOP 12).
        prop = _resolve_proposal(L, cand, trigger, action, because, scope_type,
                                 scope_key, domain, rule_type, severity,
                                 atomicity_override, conflict_override,
                                 alerts_override)
        if _proposal_fingerprint(L, cand, prop) != rec["candidate_fingerprint"]:
            raise OwnershipRefused(
                "receipt-stale-candidate",
                "the candidate or the rule text has changed since receipt %s "
                "was issued, so that answer was given about something else. "
                "Show the founder what it says now and ask again."
                % rec["receipt_uuid"][:8])
        trig, act, why = prop["trigger"], prop["action"], prop["because"]
        stype, skey, dom = prop["scope_type"], prop["scope_key"], prop["domain"]
        founder_ref = redact_text(founder_ref)
        # THE DONE GATE OF LOOP 6, now shared with the minting path (FIX ROUND
        # P3): there is no path to silently accumulate contradictory active
        # rules, and no path to ask the founder a question that hides one. The
        # refusal names the other rule and the ways out; the founder may
        # override, but the override is part of what he answered (it is in the
        # fingerprint) and is written down as evidence AND as an edge, so the
        # conflict stays visible in `conflicts`, in retrieval and in verify
        # rather than being settled by having been forced through once.
        guards = _approval_guards(self, L, prop, cand)
        problems = guards["atomicity_problems"]
        found = guards["conflicts"]
        overridden_alerts = guards["blocking_alerts"]
        ruuid = uuid.uuid4().hex
        ts = now_iso()
        with self._transaction():
            # FIRST statement in the transaction, and conditional on the receipt
            # still being unspent and unexpired. Everything below is undone if
            # this does not claim exactly one row, so two concurrent approvals
            # holding the same token produce one rule and one refusal, never two
            # rules. BEGIN IMMEDIATE already serializes writers; this is the
            # belt to that braces, and it is also what makes consumption and
            # rule creation the same atomic act rather than two steps with a
            # window between them.
            claimed = _exec(self,
                  "UPDATE learning_approval_receipts SET consumed_at=?, "
                  "consumed_rule_uuid=? WHERE receipt_uuid=? AND "
                  "consumed_at IS NULL AND expires_at >= ?",
                  (ts, ruuid, rec["receipt_uuid"], ts))
            if claimed.rowcount != 1:
                raise OwnershipRefused(
                    "receipt-already-used",
                    "receipt %s was spent or expired between the check and the "
                    "write. Nothing was created."
                    % rec["receipt_uuid"][:8])
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
                   ("founder approval (receipt %s): %s"
                    % (rec["receipt_uuid"][:8], founder_ref))[:500],
                   cand["candidate_uuid"], ts))
            _exec(self,
                  "INSERT INTO learning_evidence (evidence_uuid, rule_uuid, "
                  "candidate_uuid, polarity, evidence_type, source_session_id, "
                  "source_ref, excerpt, created_at) "
                  "VALUES (?,?,?,'support','founder_approval',?,?,?,?)",
                  (uuid.uuid4().hex, ruuid, cand["candidate_uuid"],
                   cand["source_session_id"],
                   ("receipt %s: %s" % (rec["receipt_uuid"][:8], founder_ref))[:500],
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
            if overridden_alerts:
                # Reaching here means the guard passed only because
                # override_alerts was in the fingerprint the founder answered
                # about. The override lands on the ALERT ROW, inside this
                # transaction, so it cannot be true that a rule exists and the
                # alert it was forced past still reads as clean. The alert stays
                # UNRESOLVED (nobody answered it) and stays visible as
                # overridden, which is the founder decision, not a delete.
                #
                # THE ROW COLUMNS ARE A RECORD, NOT A SWITCH (fix round). They
                # say the alert was forced past once, at this gate; they do not
                # disarm it, because blocking_alerts no longer reads them. The
                # UPDATE is still conditional on overridden_at IS NULL so the
                # FIRST override keeps its reason and author, and each later
                # gate's override is recorded as its own evidence row below,
                # against the rule it let through.
                for a in overridden_alerts:
                    _exec(self, "UPDATE notes SET overridden_at=?, "
                                "override_reason=?, override_by=? "
                                "WHERE note_uuid=? AND overridden_at IS NULL",
                          (ts, redact_text(alerts_override)[:500],
                           redact_text(founder_ref)[:200], a["note_uuid"]))
                    _exec(self,
                          "INSERT INTO learning_evidence (evidence_uuid, rule_uuid, "
                          "polarity, evidence_type, source_ref, excerpt, created_at) "
                          "VALUES (?,?,'neutral','manual_review',?,?,?)",
                          (uuid.uuid4().hex, ruuid, founder_ref[:500],
                           ("critical alert override: %s (alert %s by %s about %s)"
                            % (redact_text(alerts_override), a["note_uuid"][:8],
                               a["author"], a["matched"]))[:500], ts))
            _exec(self,
                  "UPDATE learning_candidates SET status='approved', reviewed_at=?, "
                  "resulting_rule_uuid=? WHERE candidate_uuid=?",
                  (ts, ruuid, cand["candidate_uuid"]))
            # LOOP P7: the search index row lands in THIS transaction, beside
            # the version it describes. No-op when the fast path is off.
            self._fts_write_rule(ruuid)
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

    # ------------------------------------------------------------------
    # Anchored notes, and the alert that can refuse an approval (schema 7,
    # phase A of the 2026-07-30 documentation and gate-pack spec).
    #
    # Nothing here interprets a note. add_note records what a human wrote,
    # blocking_alerts answers one question ("is there an unresolved critical
    # alert standing in front of THIS approval"), and _approval_guards turns
    # that answer into a refusal. The decision to refuse lives in exactly one
    # place, and it is the same place the atomicity and contradiction refusals
    # already live, so a receipt cannot be minted for a question that hid an
    # alert and an approval cannot spend one either.
    # ------------------------------------------------------------------

    def add_note(self, kind, body, author, author_kind, anchor_type, anchor_key,
                 severity="", anchor_line=None, session_id=""):
        """Record one anchored note. Never overwrites, never deletes.

        Every field is validated at the door rather than by the CHECK
        constraints alone, so a caller gets a named refusal instead of a
        sqlite3.IntegrityError that _exec would read as structural damage.

        A 'file' anchor goes through canonicalize_path, which is what makes an
        alert anchored to api/pay.py from a subdirectory the same anchor as one
        typed at the root, and what refuses an anchor outside the project. It is
        also why blocking_alerts can compare an anchor against a work record's
        claimed paths at all: both sides are the same canonical string.

        A 'candidate', 'rule' or 'record' anchor goes through
        _resolve_note_anchor, which turns the prefix a human typed into the full
        uuid it names or refuses. Read that method for the two silent failures
        that used to come out of storing an unchecked string here.

        body and author are secret-scrubbed on the way in, like every other
        human-typed column."""
        if kind not in NOTE_KINDS:
            raise OwnershipRefused(
                "unknown-note-kind",
                "unknown note kind %r (known: %s)" % (kind, ", ".join(NOTE_KINDS)))
        if author_kind not in NOTE_AUTHOR_KINDS:
            raise OwnershipRefused(
                "unknown-author-kind",
                "unknown author kind %r (known: %s)"
                % (author_kind, ", ".join(NOTE_AUTHOR_KINDS)))
        if anchor_type not in NOTE_ANCHOR_TYPES:
            raise OwnershipRefused(
                "unknown-anchor-type",
                "unknown anchor type %r (known: %s)"
                % (anchor_type, ", ".join(NOTE_ANCHOR_TYPES)))
        if severity not in NOTE_SEVERITIES:
            raise OwnershipRefused(
                "unknown-severity",
                "unknown severity %r (known: %s)"
                % (severity, ", ".join(s or "(none)" for s in NOTE_SEVERITIES)))
        if kind == BLOCKING_NOTE_KIND and not severity:
            raise OwnershipRefused(
                "alert-needs-severity",
                "an alert without a severity cannot be acted on: say info, "
                "warning or critical. Only critical refuses an approval.")
        if not (body or "").strip():
            raise OwnershipRefused(
                "empty-note", "a note with no body says nothing; write what you saw")
        if not (author or "").strip():
            raise OwnershipRefused(
                "no-note-author",
                "a note needs an author. An anonymous alert can refuse an "
                "approval and name nobody to ask about it, which is the one "
                "thing a refusal must never do.")
        if not (anchor_key or "").strip():
            raise OwnershipRefused(
                "no-anchor",
                "a note needs an anchor: the file, candidate, rule, record or "
                "decision it is about")
        key = anchor_key.strip()
        if anchor_type == "file":
            key = canonicalize_path(self.root, key)
        else:
            key = self._resolve_note_anchor(anchor_type, key)
        if anchor_line is not None:
            try:
                anchor_line = int(anchor_line)
            except (TypeError, ValueError):
                raise OwnershipRefused(
                    "bad-anchor-line",
                    "anchor line must be an integer line number, got %r" % (anchor_line,))
            if anchor_line < 1:
                raise OwnershipRefused(
                    "bad-anchor-line",
                    "line numbers start at 1; got %d" % anchor_line)
        line_hash = ""
        if anchor_type == "file" and anchor_line is not None:
            line_hash = self._anchor_fingerprint(key, anchor_line)
        nuuid = uuid.uuid4().hex
        with self._transaction():
            _exec(self,
                  "INSERT INTO notes (note_uuid, kind, severity, author, "
                  "author_kind, anchor_type, anchor_key, anchor_line, body, "
                  "session_id, created_at, anchor_line_hash) "
                  "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                  (nuuid, kind, severity, redact_text(author.strip()),
                   author_kind, anchor_type, key, anchor_line,
                   redact_text(body), session_id or "", now_iso(), line_hash))
        return self.get_note(nuuid)

    def _anchor_lines(self, rel):
        """The lines of one project file with no trailing newlines, or None when
        the file cannot be read.

        None rather than an exception, because both callers want the same answer
        for an unreadable file and neither wants a traceback: add_note reports it
        as an unfingerprintable anchor, and note_anchor_reports reports it as an
        anchor a reader has to go and check by hand.

        safe_project_path, not os.path.join, for the reason recorded on that
        function: a joined path follows a symlink out of the project silently,
        and this one is built from a string a note author typed."""
        try:
            full = safe_project_path(self.root, rel)
        except (OwnershipRefused, ValueError, OSError):
            return None
        try:
            with open(full, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except (OSError, UnicodeError):
            return None
        lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        # A file ending in a newline splits to a final empty string, which is not
        # a line any editor shows and not a line anybody can anchor to. Dropped
        # after a probe against a real store reported a six line file as having
        # seven, which would have let a note anchor to a line that does not exist
        # and made every reported line count wrong by one.
        if lines and lines[-1] == "":
            lines.pop()
        return lines

    def _anchor_fingerprint(self, rel, line):
        """The fingerprint of the line a file anchor points at, at write time.

        AN OUT OF RANGE LINE IS REFUSED HERE, and that is the same correction
        phase A's fix round made for identifier anchors. Reproduced against a
        real store before this existed: `note --anchor file:api/pay.py --line 99`
        on a six line file was accepted, listed by `notes`, and rendered into the
        documentation as an ordinary anchored note. Nobody was ever told the line
        did not exist, and there is nothing a reader can do with a note pointing
        at a line that was never there.

        A file that cannot be read is NOT refused. A note about a file that this
        process cannot open (generated later, held in another worktree, unreadable
        permissions) is still a note worth keeping, so it is stored with an empty
        fingerprint and reported as unverifiable. The difference between the two
        cases is knowledge: an out of range line is a fact about a file we read,
        while an unreadable file tells us nothing at all."""
        lines = self._anchor_lines(rel)
        if lines is None:
            return ""
        if line > len(lines):
            raise OwnershipRefused(
                "anchor-line-out-of-range",
                "%s has %d line(s), so there is no line %d to anchor a note to. "
                "A note nobody can follow to a line is a note nobody can act "
                "on: check the line number, or drop --line to anchor the note "
                "to the whole file." % (rel, len(lines), line))
        return _learning().anchor_line_digest(lines[line - 1])

    def note_anchor_reports(self, notes=None):
        """Where every file-anchored note's line is NOW. A REPORT, never a
        deletion (spec section 6: a note anchored to a line that has since moved
        is reported rather than silently dropped).

        One implementation, called by the documentation engine and by the gate
        packs, for the same reason blocking_alerts is one implementation: two
        renderers computing this separately would eventually disagree about
        whether a reviewer is looking at the right line, and the disagreement
        would be invisible.

        Files are read ONCE each however many notes point at them, because a
        project with a hundred notes on one module should not read it a hundred
        times.

        Returns one dict per file-anchored note carrying a line number, ordered
        problems first (see bm_learning.ANCHOR_STATES) then oldest first, so a
        reader meets the anchors that no longer resolve before the ones that do.
        A note with no line, or anchored to something other than a file, is not
        in the report at all: there is no line to have moved."""
        L = _learning()
        rows = self.list_notes() if notes is None else notes
        cache = {}
        out = []
        for note in rows:
            if note["anchor_type"] != "file" or not note["anchor_line"]:
                continue
            rel = note["anchor_key"]
            if rel not in cache:
                cache[rel] = self._anchor_lines(rel)
            found = L.resolve_anchor_line(cache[rel], note["anchor_line"],
                                          note.get("anchor_line_hash") or "")
            entry = dict(found)
            entry["note_uuid"] = note["note_uuid"]
            entry["id"] = note["note_uuid"][:8]
            entry["kind"] = note["kind"]
            entry["severity"] = note["severity"]
            entry["author"] = note["author"]
            entry["path"] = rel
            entry["created_at"] = note["created_at"]
            entry["resolved"] = bool(note["resolved_at"])
            entry["problem"] = found["state"] in L.ANCHOR_PROBLEM_STATES
            out.append(entry)
        order = {state: i for i, state in enumerate(L.ANCHOR_STATES)}
        out.sort(key=lambda e: (-order.get(e["state"], 0), e["created_at"],
                                e["note_uuid"]))
        return out

    # The resolvers an identifier anchor is checked against. One entry per
    # anchor type that HAS an identity in the schema, so a new anchor type
    # cannot be added and quietly skip resolution: anything absent from here is
    # named in the refusal below as unresolvable, rather than silently accepted.
    _ANCHOR_RESOLVERS = {
        "candidate": ("candidate",
                      lambda self, key: self.get_learning_candidate(key)["candidate_uuid"]),
        "rule": ("rule",
                 lambda self, key: self.get_learning_rule(key)["rule_uuid"]),
        "record": ("work record",
                   lambda self, key: self._resolve_record_uuid(key)),
    }

    def _resolve_note_anchor(self, anchor_type, key):
        """An identifier anchor to the FULL uuid it names, or a refusal.

        FIX ROUND, phase A: add_note used to range-check only a 'file' anchor
        and take any non-empty string for the other four. Two silent failures
        came out of that, both of them the same shape (an author believes a gate
        is held and nothing is held):

          * `--anchor candidate:deadbeefdeadbeef` naming no candidate was stored
            open, reported as an alert that "REFUSES an approval anchored here",
            and refused nothing, ever, because blocking_alerts had nothing to
            match it against;
          * a SHORT prefix (`--anchor candidate:e`) matched every candidate
            whose uuid started with it, so one note blanketed unrelated gates
            with a refusal nobody had written about them.

        Resolving here fixes both at once: the prefix a human types is resolved
        exactly as every other prefix in this project is resolved (one match or
        a named refusal, never "the first match"), and what lands in the row is
        the full uuid, which is why blocking_alerts can compare by equality.

        'decision' has no single-column identity at schema 7 (a decision is
        (lifecycle_uuid, seq)), so it is stored as typed and stated to be
        toothless by the CLI that writes it, rather than validated against a
        table that cannot answer."""
        entry = self._ANCHOR_RESOLVERS.get(anchor_type)
        if entry is None:
            return key
        label, resolve = entry
        try:
            resolved = resolve(self, key)
        except OwnershipRefused as e:
            if e.reason == "ambiguous":
                # Named separately from the not-found case because the way out is
                # different: type more characters, rather than find the right id.
                raise OwnershipRefused(
                    "ambiguous-anchor",
                    "%r names more than one %s, and an alert that blankets "
                    "several gates refuses work nobody wrote it about: %s"
                    % (key, label, e))
            raise OwnershipRefused(
                "anchor-not-found",
                "no %s matches %r, so an alert anchored there could never "
                "refuse anything and nobody would find out: %s"
                % (label, key, e))
        if not resolved:
            raise OwnershipRefused(
                "anchor-not-found",
                "no %s matches %r, so an alert anchored there could never "
                "refuse anything and nobody would find out" % (label, key))
        return resolved

    def get_note(self, prefix):
        rows = _exec(self, "SELECT * FROM notes WHERE note_uuid LIKE ?",
                     (prefix + "%",)).fetchall()
        return _one_or_refuse(rows, "note", prefix)

    def list_notes(self, kinds=None, anchors=None, include_resolved=True,
                   severities=None):
        """Notes, oldest first. `anchors` is an iterable of (type, key) pairs.

        Oldest first because a note list is a history: the order the concerns
        were raised in is the order a reviewer needs them in."""
        sql = "SELECT * FROM notes"
        where = []
        params = []
        if kinds:
            kinds = tuple(kinds)
            where.append("kind IN (%s)" % ",".join("?" * len(kinds)))
            params.extend(kinds)
        if severities:
            severities = tuple(severities)
            where.append("severity IN (%s)" % ",".join("?" * len(severities)))
            params.extend(severities)
        if anchors is not None:
            pairs = [(t, k) for t, k in anchors]
            if not pairs:
                return []
            where.append("(%s)" % " OR ".join(
                ["(anchor_type=? AND anchor_key=?)"] * len(pairs)))
            for t, k in pairs:
                params.extend((t, k))
        if not include_resolved:
            where.append("resolved_at IS NULL")
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY created_at, note_uuid"
        return [dict(r) for r in _exec(self, sql, tuple(params)).fetchall()]

    def resolve_note(self, prefix, resolution, receipt=""):
        """Mark a note answered. The row STAYS, marked resolved (spec section 6
        retention: nothing is deleted by a generator, and nothing here deletes
        either).

        RECEIPT-GATED since LOOP 2, 2026-07-30, but ONLY for a note that is a
        critical alert (kind 'alert', severity 'critical'). Before this, a
        critical alert could be resolved with no receipt at all, and
        blocking_alerts filters on include_resolved=False, so a resolved
        critical alert stopped blocking approval with no human answer
        anywhere: the exact hole the receipt-gated --override-alerts path was
        built to close, reopened one door over. An ordinary note, and a
        non-critical alert, still resolve exactly as before: no receipt, no
        override, nothing gated, because this method is a RECORD of who said
        what, not the gate itself, for anything that is not a critical alert.

        WHAT THIS STILL DOES NOT PROVE, stated rather than implied: nothing
        here authenticates who resolved the note, exactly as nothing
        authenticates a founder_ref. What it cannot do any more, for a
        critical alert, is happen with nobody having answered anything: the
        resolution text and its timestamp are on the row, and a gate pack
        renders them beside the alert, exactly as before."""
        if not (resolution or "").strip():
            raise OwnershipRefused(
                "no-resolution",
                "resolving a note requires saying what resolved it; a note that "
                "went quiet is not a note that was answered")
        note = self.get_note(prefix)
        if note["resolved_at"] is not None:
            raise OwnershipRefused(
                "already-resolved",
                "note %s was resolved at %s" % (note["note_uuid"][:8],
                                                note["resolved_at"]))
        L = _learning()
        is_critical_alert = (note["kind"] == BLOCKING_NOTE_KIND
                             and note["severity"] == BLOCKING_NOTE_SEVERITY)
        rec = None
        if is_critical_alert:
            content_parts = (L.normalize_text(resolution),)
            rec = self._require_state_change_receipt(
                "resolve-note", note["note_uuid"], receipt, content_parts)
        ts = now_iso()
        with self._transaction():
            if rec is not None:
                # FIRST statement, same reason as everywhere else in this
                # lane: two calls racing for the same token produce one
                # resolution and one refusal, never two.
                self._consume_state_change_receipt(rec, note["note_uuid"], ts)
            _exec(self, "UPDATE notes SET resolved_at=?, resolution=? "
                        "WHERE note_uuid=? AND resolved_at IS NULL",
                  (ts, redact_text(resolution), note["note_uuid"]))
        return self.get_note(note["note_uuid"])

    # THERE IS NO override_note() AND THERE IS NO delete_note(), on purpose.
    #
    # An override is only allowed to happen INSIDE approve_learning_candidate's
    # transaction, where it is bound to a receipt the founder's own answer minted
    # against a fingerprint that includes the override flag. A standalone
    # override method would be a second door into the same room with no receipt
    # on it, and any process able to import this module could walk through it and
    # then approve cleanly. Overriding is therefore not a note operation at all;
    # it is part of one approval, written in the same atomic act as the rule.
    #
    # A delete is never allowed. Spec section 6 retention, and I10 in spirit:
    # generated output never destroys human text.

    def gate_change_set(self, cand):
        """The files an approval would change, discovered from the store.

        Two sources, both recorded rather than guessed:
          * the claimed paths of the work record the candidate came from, which
            is the fence that record declared it would write inside;
          * the proposed scope key when the scope is an artifact, which is a
            path by definition.

        Returns a list of canonical root-relative strings, possibly globs, which
        is why the caller compares them with paths_overlap rather than equality."""
        out = []
        seen = set()

        def _add(p):
            try:
                canon = canonicalize_path(self.root, p)
            except (ValueError, OwnershipRefused):
                # An unusable path is not a change set entry. It is also not a
                # reason to refuse the approval: this method reports what it can
                # prove, and a scope key that is not a path simply is not one.
                return
            key = _normcase(canon)
            if key not in seen:
                seen.add(key)
                out.append(canon)

        record_uuid = cand.get("source_record_uuid")
        if record_uuid:
            for row in _exec(self, "SELECT path FROM claims WHERE "
                                   "lifecycle_uuid=? ORDER BY path",
                             (record_uuid,)).fetchall():
                _add(row["path"])
        if cand.get("proposed_scope_type") == "artifact":
            skey = (cand.get("proposed_scope_key") or "").strip()
            if skey:
                _add(skey)
        return out

    def blocking_alerts(self, cand):
        """Unresolved critical alerts standing in front of THIS approval.

        Anchored to the candidate itself, to the work record it came from, or to
        any file the approval would change (gate_change_set).

        AN OVERRIDE IS NOT A DISARM, and this is the fix round's central
        correction. This method used to skip any note whose overridden_at was
        set, and the override is written on the NOTE ROW, so one founder
        override recorded at one gate made a still-unresolved critical alert
        invisible to every later gate: the next approval saw no alert, printed no
        stakes line about it, asked the founder nothing, and closed clean, while
        `notes --open --severity critical` still listed the alert as unanswered.
        A blocking alert now keeps blocking until it is RESOLVED (someone
        answered it) or until the founder overrides it AT THIS GATE, where the
        override is bound to a receipt minted against a fingerprint that
        includes it. The row's own overridden_at stays exactly what it was, a
        record of the first override, and is reported beside the refusal so a
        founder can see the alert was forced past before.

        Matching is by EQUALITY on the identifier anchors, which is safe because
        add_note resolves a typed prefix to a full uuid at the door. It used to
        be a startswith against the raw anchor, so a one-character anchor
        blanketed every candidate in the store.

        Returns a list of note rows, oldest first, each carrying an extra
        'matched' key naming WHY it blocks, because a refusal that cannot say
        which anchor caught it is a refusal nobody can act on."""
        alerts = self.list_notes(kinds=(BLOCKING_NOTE_KIND,),
                                 severities=(BLOCKING_NOTE_SEVERITY,),
                                 include_resolved=False)
        if not alerts:
            return []
        changed = self.gate_change_set(cand)
        cuuid = cand["candidate_uuid"]
        record_uuid = cand.get("source_record_uuid") or ""
        out = []
        for note in alerts:
            matched = ""
            if note["anchor_type"] == "candidate" and note["anchor_key"] == cuuid:
                matched = "candidate %s" % cuuid[:8]
            elif (note["anchor_type"] == "record" and record_uuid
                    and note["anchor_key"] == record_uuid):
                matched = "work record %s" % record_uuid[:8]
            elif note["anchor_type"] == "file":
                for claimed in changed:
                    if paths_overlap(claimed, note["anchor_key"]):
                        matched = "file %s" % claimed
                        break
            if matched:
                row = dict(note)
                row["matched"] = matched
                out.append(row)
        return out

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

    def _rule_source_candidate(self, rule_uuid):
        """The candidate a rule was approved from, or a refusal.

        An edit receipt has to hang off a real candidate row because that is
        what the receipts table's foreign key points at, and version 1 of every
        rule records the candidate it came from. A rule whose candidate has been
        deleted cannot get an edit receipt: that is a refusal, not a bypass."""
        row = _exec(self, "SELECT source_candidate_uuid FROM learning_rule_versions "
                          "WHERE rule_uuid=? AND version=1", (rule_uuid,)).fetchone()
        cuuid = row["source_candidate_uuid"] if row else None
        if not cuuid:
            raise OwnershipRefused(
                "no-source-candidate",
                "rule %s has no surviving source candidate, so no receipt can be "
                "bound to it. Supersede it with a newly approved rule instead."
                % rule_uuid[:8])
        return cuuid

    def mint_edit_receipt(self, prefix, expected_version, founder_response,
                           trigger=None, action=None, because=None, domain=None,
                           ttl_seconds=APPROVAL_RECEIPT_TTL_SECONDS):
        """Record that a human answered a question about ONE edit to ONE rule,
        and return a one-time token that lets `edit_learning_rule` apply it.

        FIX ROUND P3, 2026-07-29. LOOP 3 receipt-gated the door that CREATES an
        injectable rule and left wide open the door that REWRITES one. Reproduced
        against a throwaway store: an imported call to edit_learning_rule turned
        an approved gate rule saying "never force push to main" into "always
        force push to main, skip review", kept its gate severity, kept the
        receipt already consumed against it, and stamped the new version
        approved_by='founder'. Nobody answered anything. Creation being gated
        while rewriting is free is not a gate, it is a speed bump.

        Same mechanism as mint_approval_receipt, same table, and deliberately
        NOT interchangeable with it: the fingerprint is domain separated with
        the literal "edit" and covers the rule uuid and the exact version bump,
        so an approval receipt cannot be spent on an edit and an edit receipt
        cannot be spent on an approval or replayed onto another rule or another
        version. founder_response is hashed, never stored. The returned dict
        carries the secret under "token"; print it once, log it never."""
        L = _learning()
        if not (founder_response or "").strip():
            raise OwnershipRefused(
                "no-founder-response",
                "minting an edit receipt requires the founder's actual answer; "
                "a receipt with nothing behind it is the forgery this whole "
                "mechanism exists to stop")
        rule = self.get_learning_rule(prefix)
        if int(expected_version) != int(rule["current_version"]):
            raise StaleIdentity(
                "expected version %s; rule %s is at version %s"
                % (expected_version, rule["rule_uuid"][:8], rule["current_version"]),
                current_version=rule["current_version"])
        prop = _resolve_edit(L, rule, trigger, action, because, domain)
        if not prop["trigger"] or not prop["action"]:
            raise OwnershipRefused("incomplete-rule",
                                   "a rule needs both a trigger and an action")
        cuuid = self._rule_source_candidate(rule["rule_uuid"])
        try:
            ttl = int(ttl_seconds)
        except (TypeError, ValueError):
            ttl = APPROVAL_RECEIPT_TTL_SECONDS
        ttl = max(1, min(ttl, APPROVAL_RECEIPT_TTL_SECONDS))
        token = secrets.token_hex(24)
        ruuid = uuid.uuid4().hex
        issued = datetime.datetime.now(datetime.timezone.utc)
        expires = issued + datetime.timedelta(seconds=ttl)
        nv = int(rule["current_version"]) + 1
        with self._transaction():
            _exec(self,
                  "INSERT INTO learning_approval_receipts (receipt_uuid, "
                  "candidate_uuid, approval_choice, nonce_hash, "
                  "candidate_fingerprint, founder_response_hash, issued_at, "
                  "expires_at) VALUES (?,?,'approve',?,?,?,?,?)",
                  (ruuid, cuuid, _receipt_token_hash(token),
                   _edit_fingerprint(L, rule, nv, prop),
                   hashlib.sha256(
                       L.normalize_text(founder_response).encode("utf-8")).hexdigest(),
                   issued.strftime("%Y-%m-%dT%H:%M:%SZ"),
                   expires.strftime("%Y-%m-%dT%H:%M:%SZ")))
        out = dict(_exec(self, "SELECT * FROM learning_approval_receipts "
                               "WHERE receipt_uuid=?", (ruuid,)).fetchone())
        out.pop("nonce_hash", None)
        out["token"] = token
        out["ttl_seconds"] = ttl
        out["rule_uuid"] = rule["rule_uuid"]
        out["next_version"] = nv
        return out

    def edit_learning_rule(self, prefix, expected_version, trigger=None,
                            action=None, because=None, domain=None,
                            change_type="edited", change_reason="", receipt=""):
        """Append a NEW version. Prior versions are never overwritten, so an
        application recorded against version 2 still says exactly what the model
        was shown (invariant L8).

        RECEIPT-GATED since FIX ROUND P3, 2026-07-29, for the reason spelled out
        on mint_edit_receipt: the text this writes is injected verbatim into
        future sessions, so rewriting it is the same act as creating it and gets
        the same door. `receipt` is a one-time token from mint_edit_receipt and
        it is MANDATORY. Without it this refuses and writes nothing. The
        version row still records approved_by='founder', and that sentence is
        now true rather than assumed.

        expected_version is the same optimistic-concurrency guard the rest of
        this store uses: a stale caller fails closed rather than clobbering. It
        is also in the receipt fingerprint, so a receipt cannot survive somebody
        else's edit landing first."""
        L = _learning()
        if not (receipt or "").strip():
            raise OwnershipRefused(
                "no-edit-receipt",
                "editing a rule requires a one-time receipt from a real founder "
                "answer, exactly as approving one does. Ask the question, then "
                "mint with mint_edit_receipt. There is no override and no "
                "break-glass: rule text nobody answered for is the exact thing "
                "this refuses to inject.")
        rule = self.get_learning_rule(prefix)
        if int(expected_version) != int(rule["current_version"]):
            raise StaleIdentity(
                "expected version %s; rule %s is at version %s"
                % (expected_version, rule["rule_uuid"][:8], rule["current_version"]),
                current_version=rule["current_version"])
        # Same scrub as capture and approval: an edit is new founder text.
        prop = _resolve_edit(L, rule, trigger, action, because, domain)
        trig, act, why, dom = (prop["trigger"], prop["action"], prop["because"],
                               prop["domain"])
        if not trig or not act:
            raise OwnershipRefused("incomplete-rule", "a rule needs both a trigger and an action")
        nv = int(rule["current_version"]) + 1
        rec = self._receipt_for_token(receipt.strip())
        if rec["consumed_at"] is not None:
            raise OwnershipRefused(
                "receipt-already-used",
                "that receipt was already spent at %s. An answer edits once; "
                "ask again for another change." % rec["consumed_at"])
        if rec["expires_at"] < now_iso():
            raise OwnershipRefused(
                "receipt-expired",
                "that receipt expired at %s. A stale answer is not consent to "
                "whatever the rule says now: ask again." % rec["expires_at"])
        if _edit_fingerprint(L, rule, nv, prop) != rec["candidate_fingerprint"]:
            raise OwnershipRefused(
                "receipt-stale-edit",
                "receipt %s was not issued for this rule at this version with "
                "this text, so that answer was given about something else. Show "
                "the founder what it says now and ask again."
                % rec["receipt_uuid"][:8])
        ts = now_iso()
        with self._transaction():
            # FIRST statement, conditional on the receipt still being unspent
            # and unexpired, for the same reason approval does it this way: two
            # edits racing for one token produce one new version and one
            # refusal, never two.
            claimed = _exec(self,
                  "UPDATE learning_approval_receipts SET consumed_at=?, "
                  "consumed_rule_uuid=? WHERE receipt_uuid=? AND "
                  "consumed_at IS NULL AND expires_at >= ?",
                  (ts, rule["rule_uuid"], rec["receipt_uuid"], ts))
            if claimed.rowcount != 1:
                raise OwnershipRefused(
                    "receipt-already-used",
                    "receipt %s was spent or expired between the check and the "
                    "write. Nothing was changed." % rec["receipt_uuid"][:8])
            _exec(self,
                  "INSERT INTO learning_rule_versions (rule_uuid, version, "
                  "trigger_text, action_text, because_text, domain, change_type, "
                  "change_reason, approved_by, created_at) "
                  "VALUES (?,?,?,?,?,?,?,?, 'founder', ?)",
                  (rule["rule_uuid"], nv, trig, act, why, dom, change_type,
                   _scrubbed_field(L, ("founder edit (receipt %s): %s"
                                       % (rec["receipt_uuid"][:8], change_reason)))[:500], ts))
            _exec(self, "UPDATE learning_rules SET current_version=?, updated_at=? "
                        "WHERE rule_uuid=?", (nv, ts, rule["rule_uuid"]))
            # LOOP P7: an edit that did not reach the index is the drift the
            # verify check hunts for, so it is written here, in the same
            # transaction, rather than left to a later sweep.
            self._fts_write_rule(rule["rule_uuid"])
        return self.get_learning_rule(rule["rule_uuid"])

    # -----------------------------------------------------------------
    # LOOP 2, 2026-07-30: the generic state-change receipt lane.
    #
    # Five commands can alter the live rule set without going through
    # approve_learning_candidate or edit_learning_rule: supersede,
    # resolve-conflict, deprecate, forget, and resolving a critical alert.
    # Before this, exactly one of them (create, via approval) and its sibling
    # (edit) were receipt-gated; the other five were not, and
    # resolve-conflict standing a GATE rule down with no receipt at all was
    # the most serious of the five holes.
    #
    # ONE mint function and ONE spend path serve all five call sites below,
    # rather than five separate checks hand-written per call site: this
    # project's own failure ledger names a cross-cutting concern implemented
    # per call site as the root cause behind four separate bugs. Each call
    # site still supplies its OWN `kind` and its own content_parts, so a
    # receipt minted for one of the five can never spend as another, exactly
    # as an edit receipt can never spend as an approval.
    # -----------------------------------------------------------------

    def mint_state_change_receipt(self, kind, prefix, founder_response,
                                   content_parts,
                                   ttl_seconds=APPROVAL_RECEIPT_TTL_SECONDS):
        """Record that a human answered a question about ONE proposed change
        to the live rule set that is not a create or an edit, and return a
        one-time token that lets the matching command spend it.

        `kind` must be one of STATE_CHANGE_RECEIPT_KINDS and selects which of
        the five commands (supersede, resolve-conflict, deprecate, forget,
        resolve-note) may later spend this receipt; the table's own CHECK
        constraint refuses anything else at the door. `prefix` is the rule or
        note (a note only for kind='resolve-note') this change would apply
        to, resolved to its full uuid HERE, the same way the spending command
        resolves it, so the two can never disagree about which row a short
        prefix named. `content_parts` is the ordered tuple of fields that
        describe WHAT would change (the destination state, a successor uuid,
        the reason, and so on): it goes into the fingerprint exactly as the
        proposed rule text does for mint_approval_receipt, so a receipt
        minted for one proposed change cannot be spent on a different one.

        founder_response is the founder's literal answer. It is HASHED, never
        stored, exactly as it is for approval and edit receipts. The returned
        dict carries the secret under "token"; print it once, log it never."""
        L = _learning()
        if kind not in STATE_CHANGE_RECEIPT_KINDS:
            raise OwnershipRefused(
                "bad-state-change-kind",
                "unknown state-change receipt kind %r (known: %s)"
                % (kind, ", ".join(STATE_CHANGE_RECEIPT_KINDS)))
        if not (founder_response or "").strip():
            raise OwnershipRefused(
                "no-founder-response",
                "minting a state-change receipt requires the founder's "
                "actual answer; a receipt with nothing behind it is the "
                "forgery this whole mechanism exists to stop")
        if kind == "resolve-note":
            target_uuid = self.get_note(prefix)["note_uuid"]
        else:
            target_uuid = self.get_learning_rule(prefix)["rule_uuid"]
        fp = _state_change_fingerprint(L, kind, target_uuid, content_parts)
        try:
            ttl = int(ttl_seconds)
        except (TypeError, ValueError):
            ttl = APPROVAL_RECEIPT_TTL_SECONDS
        ttl = max(1, min(ttl, APPROVAL_RECEIPT_TTL_SECONDS))
        token = secrets.token_hex(24)
        ruuid = uuid.uuid4().hex
        issued = datetime.datetime.now(datetime.timezone.utc)
        expires = issued + datetime.timedelta(seconds=ttl)
        with self._transaction():
            _exec(self,
                  "INSERT INTO learning_state_change_receipts (receipt_uuid, "
                  "kind, target_uuid, nonce_hash, content_fingerprint, "
                  "founder_response_hash, issued_at, expires_at) "
                  "VALUES (?,?,?,?,?,?,?,?)",
                  (ruuid, kind, target_uuid, _receipt_token_hash(token), fp,
                   hashlib.sha256(L.normalize_text(founder_response)
                                  .encode("utf-8")).hexdigest(),
                   issued.strftime("%Y-%m-%dT%H:%M:%SZ"),
                   expires.strftime("%Y-%m-%dT%H:%M:%SZ")))
        out = dict(_exec(self, "SELECT * FROM learning_state_change_receipts "
                               "WHERE receipt_uuid=?", (ruuid,)).fetchone())
        # nonce_hash back out, exactly as mint_approval_receipt does: a
        # caller printing the whole record must not print the one column
        # that could be brute forced if the token were ever shortened.
        out.pop("nonce_hash", None)
        out["token"] = token
        out["ttl_seconds"] = ttl
        return out

    def _state_change_receipt_for_token(self, token):
        """Look a state-change receipt up BY ITS TOKEN, or refuse.

        Mirrors _receipt_for_token exactly, including the refusal saying
        nothing about whether the token was unknown, malformed, or for
        another store: a caller guessing tokens learns nothing from the
        message it gets back."""
        row = _exec(self, "SELECT * FROM learning_state_change_receipts "
                          "WHERE nonce_hash=?",
                    (_receipt_token_hash(token),)).fetchone()
        if row is None:
            raise OwnershipRefused(
                "bad-state-change-receipt",
                "that receipt is not valid for this store. Ask the founder "
                "the question again and mint a fresh one.")
        return dict(row)

    def _require_state_change_receipt(self, kind, target_uuid, receipt,
                                       content_parts):
        """The read-only half of spending a state-change receipt: look it
        up and refuse for every reason approve_learning_candidate and
        edit_learning_rule already refuse for, so the five call sites below
        cannot drift from each other or from the two receipt paths this
        mirrors. Does NOT consume the receipt: the caller does that with
        _consume_state_change_receipt as the FIRST statement inside its own
        transaction, exactly as approve_learning_candidate and
        edit_learning_rule do, so two callers racing for the same token
        cannot both win. Returns the receipt row."""
        L = _learning()
        if not (receipt or "").strip():
            raise OwnershipRefused(
                "no-state-change-receipt",
                "this changes the live rule set, so it requires a one-time "
                "receipt from a real founder answer, exactly as approving "
                "or editing a rule does. There is no override and no "
                "break-glass: a change nobody answered for is the exact "
                "thing this refuses to make.")
        rec = self._state_change_receipt_for_token(receipt.strip())
        if rec["kind"] != kind:
            raise OwnershipRefused(
                "receipt-wrong-kind",
                "that receipt was minted for %r, not %r. A receipt only "
                "spends as the command it was asked about."
                % (rec["kind"], kind))
        if rec["target_uuid"] != target_uuid:
            raise OwnershipRefused(
                "receipt-wrong-target",
                "that receipt was issued for %s, not %s. One answer "
                "resolves one target."
                % (rec["target_uuid"][:8], target_uuid[:8]))
        if rec["consumed_at"] is not None:
            raise OwnershipRefused(
                "receipt-already-used",
                "that receipt was already spent at %s. An answer resolves "
                "once; ask again for another change." % rec["consumed_at"])
        if rec["expires_at"] < now_iso():
            raise OwnershipRefused(
                "receipt-expired",
                "that receipt expired at %s. A stale answer is not consent "
                "to whatever this says now: ask again." % rec["expires_at"])
        fp = _state_change_fingerprint(L, kind, target_uuid, content_parts)
        if fp != rec["content_fingerprint"]:
            raise OwnershipRefused(
                "receipt-stale-target",
                "the target or the change proposed for it has changed "
                "since receipt %s was issued, so that answer was given "
                "about something else. Show the founder what it says now "
                "and ask again." % rec["receipt_uuid"][:8])
        return rec

    def _consume_state_change_receipt(self, rec, target_uuid, ts):
        """The FIRST statement inside the caller's transaction, conditional
        on the receipt still being unspent and unexpired, for the same
        reason approve_learning_candidate and edit_learning_rule do it this
        way: two calls racing for the same token produce one change and one
        refusal, never two."""
        claimed = _exec(self,
              "UPDATE learning_state_change_receipts SET consumed_at=?, "
              "consumed_target_uuid=? WHERE receipt_uuid=? AND "
              "consumed_at IS NULL AND expires_at >= ?",
              (ts, target_uuid, rec["receipt_uuid"], ts))
        if claimed.rowcount != 1:
            raise OwnershipRefused(
                "receipt-already-used",
                "receipt %s was spent or expired between the check and the "
                "write. Nothing was changed." % rec["receipt_uuid"][:8])

    def change_learning_rule_state(self, prefix, target, reason="",
                                    successor_prefix=None, receipt="",
                                    receipt_kind=None):
        """Move a rule between lifecycle states, refusing illegal moves and
        refusing the ones that need evidence they do not have.

        Two named refusals implement plan rules 6 and 8 directly: nothing
        reaches 'confirmed' or 'settled' without at least one SUPPORTING
        evidence row that is not the original approval, and nothing reaches
        'superseded' without a real successor plus its edge.

        UNCONDITIONALLY receipt-gated for target in ('superseded',
        'deprecated', 'forgotten') since LOOP 2, 2026-07-30: a caller cannot
        opt out by simply omitting receipt_kind, which is the property that
        actually matters against the attack this loop defends against
        (shell access as the same OS user, calling this module directly
        rather than going through bm_learn.py). STATE_CHANGE_GATE_KIND maps
        each gated target to the receipt kind it requires by default;
        receipt_kind overrides that default ONLY to let
        resolve_learning_conflict's own 'superseded' branch gate under its
        OWN kind ('resolve-conflict') instead of 'supersede', since both
        reach this same method and must not be interchangeable. 'confirmed'
        and 'settled' are deliberately NOT in that map and proceed ungated:
        they are evidence-graded lifecycle promotions, not one of the five
        commands this loop closed, and they already carry their own
        no-supporting-evidence guard below."""
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
        rec = None
        gate_kind = STATE_CHANGE_GATE_KIND.get(target)
        if gate_kind:
            # UNCONDITIONAL: a caller cannot skip this by leaving
            # receipt_kind at its default. receipt_kind, when given, only
            # SUBSTITUTES a different kind label (resolve_learning_conflict's
            # own 'resolve-conflict'); it can never remove the gate itself.
            effective_kind = receipt_kind or gate_kind
            content_parts = (target, successor["rule_uuid"] if successor else "",
                             L.normalize_text(reason))
            rec = self._require_state_change_receipt(
                effective_kind, rule["rule_uuid"], receipt, content_parts)
        ts = now_iso()
        with self._transaction():
            if rec is not None:
                # FIRST statement, conditional on the receipt still being
                # unspent and unexpired, for the same reason approval and
                # edit consume theirs this way: two calls racing for the
                # same token produce one change and one refusal, never two.
                self._consume_state_change_receipt(rec, rule["rule_uuid"], ts)
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

    def resolve_learning_conflict(self, loser_prefix, other_prefix, how,
                                   reason="", receipt=""):
        """Execute a founder's decision about ONE conflict, atomically.

        `how` names what happens to the rule the founder chose to stand down:
        superseded by the other one, marked contradicted, or deprecated. This
        method does not choose, rank, or suggest which rule that is. It exists
        so the state change and the edge that explains it land together, rather
        than leaving a rule silenced with no record of why.

        RECEIPT-GATED since LOOP 2, 2026-07-30, for all three resolutions,
        under the ONE kind "resolve-conflict": before this, a conflict
        against an approved GATE rule could be stood down with no human
        answer anywhere, the most serious of the five holes this loop closed.
        `receipt` is a one-time token from mint_state_change_receipt(kind=
        "resolve-conflict", ...) and it is MANDATORY. There is no override and
        no break-glass."""
        if how == "superseded":
            return self.change_learning_rule_state(
                loser_prefix, "superseded", reason=reason,
                successor_prefix=other_prefix, receipt=receipt,
                receipt_kind="resolve-conflict")
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
        content_parts = (how, other["rule_uuid"], L.normalize_text(reason))
        rec = self._require_state_change_receipt(
            "resolve-conflict", loser["rule_uuid"], receipt, content_parts)
        ts = now_iso()
        with self._transaction():
            # FIRST statement, same reason as everywhere else in this lane:
            # two calls racing for the same token produce one change and one
            # refusal, never two.
            self._consume_state_change_receipt(rec, loser["rule_uuid"], ts)
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
        # LOOP P7. Real findings now, not a placeholder: every disagreement
        # between the optional search index and the rules is reported with the
        # same code the checks tuple has always named, so a store that never
        # turns the index on keeps exactly the output it had.
        for code, detail, refs in self.learning_fts_drift():
            add(code, detail, refs)
        status = self.learning_index_status()
        if status["available"]:
            note = ("fts-drift: the search index is on (mode %s), %s row(s) "
                    "indexed for %s rule(s)"
                    % (status["mode"], status["indexed_rows"], status["rules"]))
        elif status["requested"]:
            note = ("fts-drift: the search index was requested but is not "
                    "available on this SQLite build, so retrieval mode is %s "
                    "and there is nothing to drift from" % L.RETRIEVAL_MODE)
        else:
            note = ("fts-drift: no search index is enabled (%s=1 turns it on), "
                    "retrieval mode is %s, so there is nothing to drift from"
                    % (FTS5_ENV, L.RETRIEVAL_MODE))
        return {
            "ok": not findings,
            "findings": findings,
            "checks": list(self.LEARNING_CHECKS),
            "rules": len(self.list_learning_rules(include_forgotten=True)),
            "edges": len(self.list_learning_edges()),
            # Stated rather than silently skipped: the check always runs and
            # always says which of its three situations it was in, so "no
            # findings" can never be read as "the index was not looked at".
            "notes": [note],
        }

    def retrieve_learning_rules(self, query, context=None, limit=5,
                                 include_reasons=True, expand_ids=None):
        """Rules relevant to a task, most relevant first, each able to say why.

        Read-only by contract: it writes nothing, records no application, and
        does not store the query. Recording an application is a separate,
        explicit call, so merely ASKING what applies can never pollute the
        outcome data (invariant L10 depends on that separation).

        Eligibility is a hard filter before ranking: only injectable states,
        and only rules whose scope the supplied context actually matches.

        `limit` caps SOFT rules only. Every applicable live gate rule is
        returned no matter what the caller passed, including limit 0 and
        negative limits, and the result reports gates_returned, gates_total,
        soft_returned and soft_omitted so the two can be told apart.

        LOOP 3 adds the other half: every gate is ALWAYS returned, but not
        every gate is returned as FULL TEXT. `gate_manifest` in the result is
        the compact, bounded-per-gate listing of every applicable gate,
        independent of query or ranking (see bm_learning.gate_manifest).
        Each row also carries `presentation` ('expanded' or 'manifest') and,
        for gates, `expansion_reason`: full text is included in `results`
        only for a gate that clears one of the four Layer B triggers
        (bm_learning.gate_expansion_reason), and even then bm_learning's
        GATE_EXPANSION_CAP bounds how many gates this single call may expand,
        so full-text size cannot grow without limit alongside the corpus.
        `expand_ids` lets a caller pull a specific gate's full text by its
        short id or rule_uuid regardless of relevance. A gate that does not
        make the expansion cut is never dropped from `results`: it is
        included with presentation='manifest', matching the manifest, so
        gates_returned/gates_total keeps meaning exactly what it always has
        (every applicable gate accounted for), and only the TEXT shown for
        it is deferred to the manifest line."""
        L = _learning()
        context = context or {}
        in_scope = [r for r in self.list_learning_rules(states=L.INJECTABLE_STATES)
                    if L.scope_matches(r["scope_type"], r["scope_key"], context)]
        # THE FAST PATH, AND WHY IT ONLY EVER ADDS (LOOP P7).
        #
        # fts_scores is None when the index is off, absent, unavailable, broken
        # or simply not consulted, and every one of those cases takes the
        # lexical path below unchanged. When it is a map, it does two things
        # and no more: it becomes a ranking component (rank_key), and it widens
        # the relevance floor. It never removes a rule the lexical path would
        # have returned, which is what makes "fall back to lexical" a true
        # statement about behaviour rather than about code paths.
        fts_scores = self._fts_scores(query)
        mode = L.FTS5_MODE if fts_scores is not None else L.RETRIEVAL_MODE
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
        #
        # An FTS hit clears the floor too. That is the retrieval GAIN of this
        # loop and not a loosening of the rule: the stemmer matching "pushing"
        # against a rule written about "push" is a real term match that the
        # exact-token floor was throwing away.
        eligible = [r for r in in_scope
                    if L.is_gate(r)
                    or (fts_scores is not None
                        and r["rule_uuid"] in fts_scores)
                    or L.lexical_overlap(query, r.get("trigger_text", ""),
                                         r.get("action_text", ""),
                                         r.get("because_text", ""),
                                         r.get("domain", "")) > 0]
        eligible.sort(key=lambda r: L.rank_key(r, query, context, fts_scores))
        # THE LIMIT APPLIES TO SOFT RULES ONLY (Loop P4).
        #
        # Reproduced on the real CLI before this was written, and recorded as
        # the open half of NOT-FINALIZED item 19: two live global rules, the
        # gate ranked second on lexical relevance, `--limit 1`, and the gate
        # never reached the model. The relevance floor above already says a
        # gate must appear even when the founder did not use its vocabulary.
        # A caller's page size then quietly undid that, which made the
        # exemption decorative.
        #
        # So the split is structural rather than a nudge to the ranking:
        # every applicable gate is returned, ALWAYS, and `limit` decides how
        # many soft rules ride along. Ranking is untouched, which is what
        # keeps Loop 5's retrieval order the founder's call and not this
        # loop's: the gate does not jump the queue, it simply cannot be cut
        # from it. limit=0 therefore means "gates only", and a negative limit
        # clamps to zero and means the same, rather than slicing from the end
        # of the list the way a bare Python slice would.
        gates, soft = L.split_gates(eligible)
        soft_kept = soft[:max(0, int(limit))]
        keep = set(r["rule_uuid"] for r in soft_kept)
        # Re-walked in ranked order rather than concatenated gates-first, so a
        # gate does not appear to have outranked a soft rule that actually
        # ranked above it. `rank` keeps its existing meaning, position in this
        # result, which is why a gate shown alone under limit 0 reads rank 1.
        chosen = [r for r in eligible
                  if L.is_gate(r) or r["rule_uuid"] in keep]
        out = []
        for i, r in enumerate(chosen, 1):
            row = dict(r)
            row["rank"] = i
            if include_reasons:
                row["why"] = L.explain_rank(r, query, context, fts_scores, mode)
            out.append(row)
        # LOOP 3: Layer A (manifest) and Layer B (bounded full-text expansion).
        #
        # gate_manifest is built from `gates` alone: every applicable gate,
        # independent of this call's query or ranking, which is what makes it
        # deterministic across two different queries against the same corpus
        # (see bm_learning.gate_manifest's own docstring).
        #
        # `presentation` decides what a caller SHOWS for each row, never what
        # this method RETURNS: every gate stays in `out`/`results` exactly as
        # before this loop (gates_returned/gates_total keep their existing
        # meaning, nothing is cut), and the dict every row carries still has
        # its full trigger/action/because text. What changes is which gates
        # are worth reading in full THIS call. An explicit --expand request
        # is never capped: the caller named the gate, so withholding it would
        # be the exact hiding Loop P4 already refuses to do for `limit`.
        # Every other trigger competes for GATE_EXPANSION_CAP slots in the
        # same rank order `out` is already in, so the choice of WHICH gates
        # expand when more than the cap qualify is deterministic and matches
        # the founder's own relevance ordering rather than list position.
        # `action_reached` answers ONE narrow question, independent of which
        # trigger (if any) governs `presentation` below: does the query's own
        # wording overlap this row's action_text, i.e. is the thing being
        # attempted the thing this rule's do-clause is about. Computed for
        # every row, gate or soft, because outcome evidence needs the same
        # answer for both once an application is recorded.
        for row in out:
            row["action_reached"] = L.lexical_overlap(
                query, "", row.get("action_text", ""), "", "") > 0
        expand_ids = set(expand_ids or ())
        for row in out:
            if not L.is_gate(row):
                row["presentation"] = "expanded"
                row["expansion_reason"] = None
                continue
            reason = L.gate_expansion_reason(row, query, context,
                                             expand_ids, fts_scores)
            row["expansion_reason"] = reason
            if reason is None:
                row["presentation"] = "manifest"
            elif reason == "requested-by-id":
                row["presentation"] = "expanded"
            else:
                row["presentation"] = None  # decided below, once capped
        cap_left = L.GATE_EXPANSION_CAP
        for row in out:
            if row["presentation"] is None:
                if cap_left > 0:
                    row["presentation"] = "expanded"
                    cap_left -= 1
                else:
                    row["presentation"] = "manifest"
        gate_manifest_data = L.gate_manifest(gates)
        gates_expanded = sum(1 for r in out
                             if L.is_gate(r) and r["presentation"] == "expanded")
        gates_manifest_only = sum(1 for r in out
                                  if L.is_gate(r) and r["presentation"] == "manifest")
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
        # DIAGNOSTICS THAT SEPARATE THE TWO STATEMENTS.
        #
        # `omitted` used to be one number covering both, so a caller could not
        # tell "your limit hid some preferences" from "your limit hid a safety
        # gate". It is kept, and it now counts soft rules only, because after
        # the split it can never mean anything else: gates_omitted is zero by
        # construction and there is a test that says so. gates_total is
        # reported next to gates_returned so the equality is checkable from
        # the outside rather than taken on trust.
        soft_omitted = max(0, len(soft) - len(soft_kept))
        # Counted off the rows actually being handed back, not off the
        # intention above it. If a later edit ever drops a gate between the
        # split and the return, this number moves away from gates_total and
        # the invariant test fails, which is the whole point of reporting both.
        gates_returned = sum(1 for r in out if L.is_gate(r))
        return {"mode": mode, "results": out,
                "omitted": soft_omitted,
                "eligible": len(eligible),
                "gates_returned": gates_returned,
                "gates_total": len(gates),
                "soft_returned": len(soft_kept),
                "soft_omitted": soft_omitted,
                "conflicts": conflicts,
                # LOOP 3. gate_manifest is the compact Layer A listing, every
                # applicable gate, always. gates_expanded/gates_manifest_only
                # split gates_returned by presentation so a caller can prove
                # the expansion cap held without recounting `results` by hand;
                # their sum always equals gates_returned. full_text_count is
                # the actual number of FULL-TEXT blocks this call produced
                # (expanded gates plus every soft rule, which was already
                # bounded by `limit`), which is the number that must stay
                # bounded regardless of corpus size.
                "gate_manifest": gate_manifest_data,
                "gates_expanded": gates_expanded,
                "gates_manifest_only": gates_manifest_only,
                "full_text_count": gates_expanded + len(soft_kept)}

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

    def _prior_application(self, fingerprint, rule_uuid, version, session_id,
                           record_uuid):
        """The existing row THIS retrieval is a repeat of, or None.

        THE IDEMPOTENCE KEY INCLUDES THE WORK RECORD, and it has to.
        It used to be (task fingerprint, rule, version, session) alone, so two
        DIFFERENT pieces of substantial work in one session that happened to
        share task wording collapsed onto one row: the second one recorded
        nothing, and "was this rule followed for that work" became permanently
        unanswerable while the run still read as a clean success. Two units of
        work are two applications of the rule, whatever they were called.

        The lookup is therefore ordered, not a single match:
          1. a row already pointing at THIS record: the same work, seen again.
          2. otherwise an UNCLAIMED row (record_uuid still null): the normal
             order of work, where retrieval happens before the work record
             exists, so the caller re-runs with --record and the link lands.
          3. otherwise nothing: a row belonging to some OTHER work record is
             not this work's row, so this work gets its own.

        Rule 3 is why no link is ever moved: a foreign row is never selected
        here, so it can never be updated, and the "never rewrite an existing
        link" invariant is now a consequence of the lookup rather than a
        refusal bolted on after it.

        With no record supplied there is nothing to key on beyond the old
        four, so the first row wins and the caller is TOLD which work record it
        already belongs to. That ambiguity is real and is disclosed, never
        resolved by guessing."""
        base = ("SELECT application_uuid AS u, record_uuid AS rec "
                "FROM learning_applications "
                "WHERE task_fingerprint=? AND rule_uuid=? AND rule_version=? "
                "AND session_id=?")
        key = (fingerprint, rule_uuid, version, session_id)
        tail = " ORDER BY retrieved_at, application_uuid LIMIT 1"
        if record_uuid is None:
            return _exec(self, base + tail, key).fetchone()
        same = _exec(self, base + " AND record_uuid=?" + tail,
                     key + (record_uuid,)).fetchone()
        if same is not None:
            return same
        return _exec(self, base + " AND (record_uuid IS NULL OR record_uuid='')"
                     + tail, key).fetchone()

    # The scope types that can appear in a retrieval context, mapped to the
    # column that stores each one. Written out rather than derived by string
    # concatenation so a renamed scope type breaks loudly at import review
    # instead of silently writing a context key into no column at all.
    _RUN_CONTEXT_COLUMNS = (
        ("project", "project_key"),
        ("domain", "domain_key"),
        ("artifact", "artifact_key"),
        ("relationship", "relationship_key"),
        ("tool", "tool_key"),
    )

    def _write_retrieval_run(self, run_uuid, res, query, fingerprint,
                             context, limit, session_id, record_uuid, ts):
        """Write the immutable record of ONE retrieval. Caller holds the
        transaction.

        Everything here is a fact from the moment of retrieval, and none of it
        is recomputable later: the corpus moves, rules are edited and
        forgotten, and the caller's limit is not stored anywhere else.

        THE PROMPT IS NOT WRITTEN, AND WAS (FIX ROUND P6). The first version
        defaulted the excerpt to the query itself, so an ordinary `apply` put
        up to 500 characters of the founder's verbatim task text in this table
        on the default path, with nothing justified and no way to opt out.
        What is stored instead is the query HASH, which recognises the same
        task coming back, and the task's search TERMS: sorted, deduplicated,
        stopword-free, order destroyed. That set is exactly what the ranker
        reads, so a past retrieval can still be re-ranked faithfully, and it is
        not the prompt. A task with more terms than L.MAX_QUERY_TERMS stores
        none, and classification then refuses to decide rather than re-ranking
        a truncated set.

        Scope keys are stored WHOLE. safe_display's 200-character cap belongs
        on a screen, not on a value a rule is looked up by: a longer legal key
        came back with an ellipsis, stopped matching its own rule, and the miss
        it should have exposed went silent.

        `limit` is stored as the caller passed it, negative values included:
        clamping it to zero here would hide that a caller asked for something
        impossible, and the retrieval's own clamp is already visible in
        returned_count."""
        L = _learning()
        values = {"project_key": "", "domain_key": "", "artifact_key": "",
                  "relationship_key": "", "tool_key": ""}
        for scope_type, column in self._RUN_CONTEXT_COLUMNS:
            supplied = (context or {}).get(scope_type) or ""
            values[column] = redact_text(L.storage_key(supplied))
        _exec(self,
              "INSERT INTO learning_retrieval_runs (retrieval_uuid, session_id, "
              "record_uuid, task_fingerprint, task_excerpt, query_hash, "
              "project_key, domain_key, artifact_key, relationship_key, "
              "tool_key, requested_limit, retrieval_mode, eligible_count, "
              "returned_count, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
              (run_uuid, session_id, record_uuid, fingerprint,
               L.query_terms(redact_text(query)),
               L.content_hash(query),
               values["project_key"], values["domain_key"],
               values["artifact_key"], values["relationship_key"],
               values["tool_key"], int(limit), res["mode"],
               int(res["eligible"]), len(res["results"]), ts))

    def get_learning_retrieval_run(self, prefix):
        rows = _exec(self, "SELECT * FROM learning_retrieval_runs "
                           "WHERE retrieval_uuid LIKE ?",
                     (prefix + "%",)).fetchall()
        return _one_or_refuse(rows, "retrieval run", prefix)

    def list_learning_retrieval_runs(self, session_id=None,
                                     task_fingerprint=None):
        clauses, params = [], []
        if session_id is not None:
            # `is not None` rather than truthiness, matching
            # list_learning_applications: the empty string is a REAL session id
            # in this schema (a caller that recorded without one), and treating
            # it as "no filter" would silently widen the query.
            clauses.append("session_id = ?")
            params.append(session_id)
        if task_fingerprint:
            clauses.append("task_fingerprint = ?")
            params.append(task_fingerprint)
        # `run_seq` IS THE INSERTION ORDER, AND IT IS HERE BECAUSE created_at
        # ALONE IS NOT AN ORDER (FIX ROUND P6). created_at has one-second
        # resolution, two retrievals of the same task inside one second are
        # routine, and the tie used to be broken by retrieval_uuid, which is
        # random. Which run the classifier treated as the authority therefore
        # changed between byte-identical command sequences, and with it the
        # limit and context every miss was judged against. rowid is monotonic
        # per insert, needs no column and no migration, and orders the two runs
        # the way they actually happened.
        sql = "SELECT *, rowid AS run_seq FROM learning_retrieval_runs"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY created_at, rowid"
        return [dict(r) for r in _exec(self, sql, tuple(params)).fetchall()]

    @staticmethod
    def _authority_run(runs):
        """The run a task is graded against: the EARLIEST one, deterministically.

        A separate function so the ordering it depends on can be reinjected in
        a calibration test instead of being asserted about from the outside."""
        return sorted(runs, key=lambda r: (r["created_at"], r["run_seq"]))[0]

    def _run_context(self, run):
        """The scope context as it was AT RETRIEVAL TIME, from the stored row.

        The one function that turns a run back into the dict retrieval takes,
        so the reconstruction cannot drift from the recording."""
        context = {}
        for scope_type, column in self._RUN_CONTEXT_COLUMNS:
            if run[column]:
                context[scope_type] = run[column]
        return context

    def record_learning_applications(self, query, context=None, limit=5,
                                      session_id="", record_prefix=None,
                                      shown_to_model=True, task_excerpt=None,
                                      expand_ids=None):
        """Retrieve rules for a task AND record that they were surfaced.

        LOOP 3: each application row also records `presentation` ('expanded'
        or 'manifest', from the retrieval's per-row decision) and
        `action_reached` ('yes' when this row's expansion reason was
        specifically that the query's wording reached the gate's own
        action_text, 'no' for every other row, including a soft rule or a
        manifest-only gate). Both are additive columns (schema 10); a row
        written before schema 10 reads back 'unknown' for each, which is the
        honest answer for a run this loop never observed, not a backfilled
        guess.

        One application row per returned rule VERSION per unit of work.
        Idempotent per (task fingerprint, rule, version, session, work record):
        running the same retrieval twice for the same work records once and
        reports the rest as already present, because a model that re-reads its
        rules mid-task has not applied them twice.

        THE WORK RECORD IS PART OF THAT KEY, and see _prior_application for
        why: without it, two different pieces of substantial work in one
        session that shared task wording collapsed onto a single row, and the
        second one recorded nothing while still reporting success.

        Idempotent does NOT mean the second call is discarded. The natural
        order of work is retrieve first, claim the work record second, then
        re-run with --record once there is something to link to. A row whose
        record_uuid is still missing therefore has it ATTACHED here and comes
        back counted as `linked`. Nothing else in this codebase can set that
        column afterwards, so dropping the flag would strand the row for good
        and permanently unlink the application from the work it belongs to.
        An application already pointing at a DIFFERENT record is never touched
        and never moved: that work keeps its row, and this work gets its own.

        The retrieval result is returned whatever happens to the write, and
        that now includes a bad --record. Resolving the work record prefix is
        part of the WRITE, not a precondition of the read, so a mistyped id
        comes back as `record_error` with the rules intact instead of aborting
        the whole run and leaving the caller with no founder rules at all.
        `record_error_kind` says which sort of failure it was, because a bad
        argument will fail identically forever and a busy database will not."""
        L = _learning()
        res = self.retrieve_learning_rules(query, context=context, limit=limit,
                                           expand_ids=expand_ids)
        out = dict(res)
        fingerprint = L.task_fingerprint(query)
        excerpt = query if task_excerpt is None else task_excerpt
        out["task_fingerprint"] = fingerprint
        out["session_id"] = session_id or ""
        out["recorded"] = 0
        out["already_recorded"] = 0
        out["linked"] = 0
        out["applications"] = []
        out["already_linked_records"] = []
        out["record_error"] = ""
        out["record_error_kind"] = ""
        out["retrieval_uuid"] = ""
        # Echoed back because the CLI prints it beside the run id, and reading
        # it off the caller's own argument keeps the printed line true even
        # when the write fails and no run row exists to read it from.
        out["requested_limit"] = int(limit)
        ts = now_iso()
        # ONE RUN ROW PER RECORDED RETRIEVAL, including a repeat that records no
        # new application (LOOP P6). A repeat IS a retrieval: it happened, it
        # had a limit and a context, and dropping it would leave the ledger
        # unable to say the rules were asked for a second time. The uuid is
        # minted before the transaction so the application rows written inside
        # it can carry it, and the row itself is written inside, so a rollback
        # takes the run and its applications together.
        run_uuid = uuid.uuid4().hex
        recorded, already, linked, uuids, elsewhere = 0, 0, 0, [], set()
        try:
            record_uuid = self._resolve_record_uuid(record_prefix)
            with self._transaction():
                self._write_retrieval_run(run_uuid, res, query, fingerprint,
                                          context, limit,
                                          session_id or "", record_uuid, ts)
                for r in res["results"]:
                    version = int(r["current_version"])
                    prior = self._prior_application(
                        fingerprint, r["rule_uuid"], version,
                        session_id or "", record_uuid)
                    if prior is not None:
                        already += 1
                        uuids.append(prior["u"])
                        if record_uuid is not None and not prior["rec"]:
                            _exec(self,
                                  "UPDATE learning_applications SET record_uuid=? "
                                  "WHERE application_uuid=?",
                                  (record_uuid, prior["u"]))
                            linked += 1
                        elif record_uuid is None and prior["rec"]:
                            # Disclosed, never resolved by guessing. Without a
                            # --record this call cannot tell a re-read of that
                            # work from DIFFERENT work worded the same way.
                            elsewhere.add(prior["rec"])
                        continue
                    au = uuid.uuid4().hex
                    scope_match = r["scope_type"] if r["scope_type"] == "global" \
                        else "%s:%s" % (r["scope_type"], r["scope_key"])
                    score = None
                    if isinstance(r.get("why"), dict):
                        score = r["why"].get("relevance")
                    # LOOP 3: presentation and action_reached are read off THIS
                    # row's own retrieval decision, not recomputed, so the
                    # application row can never disagree with what was
                    # actually shown for it in `res["results"]`.
                    presentation = r.get("presentation") or "unknown"
                    action_reached = ("yes" if r.get("action_reached")
                                      else "no")
                    _exec(self,
                          "INSERT INTO learning_applications (application_uuid, "
                          "rule_uuid, rule_version, session_id, record_uuid, "
                          "task_fingerprint, task_excerpt, retrieved_at, "
                          "retrieval_rank, retrieval_score, scope_match, "
                          "shown_to_model, retrieval_uuid, presentation, "
                          "action_reached) "
                          "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                          (au, r["rule_uuid"], version, session_id or "",
                           record_uuid, fingerprint,
                           redact_text(L.safe_display(excerpt, 500)), ts,
                           int(r["rank"]), score, scope_match,
                           1 if shown_to_model else 0, run_uuid,
                           presentation, action_reached))
                    recorded += 1
                    uuids.append(au)
            out["recorded"] = recorded
            out["already_recorded"] = already
            out["linked"] = linked
            out["applications"] = uuids
            out["already_linked_records"] = sorted(elsewhere)
            out["retrieval_uuid"] = run_uuid
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
            # WHICH SORT OF FAILURE, because the honest next step differs and
            # the caller cannot tell them apart from the message. An
            # OwnershipRefused here is the caller's argument being wrong, so
            # re-running the identical command fails identically forever; a
            # database error is transient and re-running is exactly right.
            out["record_error_kind"] = (e.reason
                                        if isinstance(e, OwnershipRefused)
                                        else "write-failed")
            # Rows counted as ALREADY PRESENT were there before this call and
            # survive the rollback, so reporting 0 of them would understate
            # what the database actually holds. Rows this call wrote or linked
            # are gone with the transaction and stay at 0.
            out["already_recorded"] = already
            out["already_linked_records"] = sorted(elsewhere)
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

        THE DENOMINATOR COMES FROM THE STORED RUN, NOT FROM A GUESS (LOOP P6).
        The scope context, the requested limit and the eligible count are read
        off the learning_retrieval_runs row written when the retrieval actually
        happened. Before that row existed, the context was rebuilt from the
        scope_match values of the rows that DID land, which is circular: a task
        where no project rule was returned reported an empty project context,
        so every project rule it missed was invisible and the miss count read
        zero. Reproduced on the real CLI (limit 0, one global gate and one
        project rule in scope: the project rule was cut and classify reported
        no misses).

        MISSES ARE SPLIT BY CAUSE, because the fixes differ:
          - retrieval_miss: the rule ranked INSIDE the limit the caller asked
            for and still has no application row. Ranking or scope is wrong.
          - retrieval_limit_miss: the rule ranked outside that limit. The
            ranking was right and the limit was too small.
        A gate is never a limit miss: gates are exempt from the limit by
        construction, so a missing gate is always the harder finding.

        FIVE THINGS IT REFUSES TO DECIDE, each reported rather than guessed:
          - a task whose application rows predate the run table (legacy);
          - a task that kept no terms, so nothing can be re-ranked;
          - a task whose rule corpus no longer matches the eligible count the
            run recorded, so today's ranking is not that retrieval's ranking
            (see _historical_corpus);
          - a rule whose current version was written AFTER the retrieval, so
            today's text is not the text that would have been ranked;
          - a rule the founder approved after the task ran, which is not a
            miss at all and is skipped silently.

        `not_decidable_tasks` entries carry `evidence` naming which of these it
        was. Every miss carries `miss_kind`, and both kinds stay in
        `retrieval_misses` so the denominator is not split across two lists;
        `counts` reports them under their two separate class names."""
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
        # THE MISS PASS WALKS RUNS, NOT APPLICATION ROWS. A retrieval that
        # returned nothing at all has no application row to be found by, and it
        # is exactly the retrieval most worth grading: with the pass keyed on
        # application rows, a limit that cut every rule produced no findings
        # because it produced no rows.
        runs_by_task = {}
        for run in self.list_learning_retrieval_runs(session_id=session_id):
            runs_by_task.setdefault(
                (run["session_id"], run["task_fingerprint"]), []).append(run)
        misses, undecidable = [], []
        for key in sorted(set(tasks) | set(runs_by_task)):
            sid, fingerprint = key
            group = tasks.get(key, [])
            # THE EARLIEST run for this task is the authority, and earliest is
            # decided by insertion order, not by a random uuid tie-break on a
            # one-second timestamp (see _authority_run). A repeat retrieval of
            # the same task text in the same session may have used a different
            # limit or context, and the first one is when the acting model was
            # actually equipped; `retrieval_runs` reports how many there were
            # so a reader can see the ambiguity rather than having it silently
            # averaged away.
            runs = runs_by_task.get(key, [])
            excerpt = ""
            for a in group:
                if a["task_excerpt"]:
                    excerpt = a["task_excerpt"]
                    break
            run = self._authority_run(runs) if runs else None
            kind, reason = L.retrieval_evidence(
                run["retrieval_uuid"] if run else "",
                (run["task_excerpt"] if run else "") or excerpt)
            if kind != "complete":
                undecidable.append({
                    "session_id": sid, "task_fingerprint": fingerprint,
                    "evidence": kind, "reason": reason})
                continue
            context = self._run_context(run)
            when = run["created_at"]
            requested_limit = max(0, int(run["requested_limit"]))
            # SEEN IS WHAT *THIS* RUN SURFACED, NOT WHAT THE SESSION EVER
            # SURFACED (FIX ROUND P6). Built from every application row for the
            # task, a later, wider retrieval of the same text in the same
            # session marked the cut rules as seen, and the graded run's real
            # misses vanished. That erased the flagship finding of this loop
            # under the ordinary founder workflow: limit was too low, raise it,
            # re-run, and the evidence of the first miss disappeared. Grading
            # run one with knowledge produced by run two is the same
            # circularity this loop removed from the context.
            seen = set(a["rule_uuid"] for a in group
                       if a["retrieval_uuid"] == run["retrieval_uuid"])
            res = self.retrieve_learning_rules(run["task_excerpt"] or excerpt,
                                                context=context,
                                                limit=self._ALL_ELIGIBLE)
            historical, drift = self._historical_corpus(res, run)
            if drift:
                undecidable.append({
                    "session_id": sid, "task_fingerprint": fingerprint,
                    "evidence": "corpus_changed_since_retrieval",
                    "retrieval_uuid": run["retrieval_uuid"],
                    "reason": drift})
                continue
            soft_position = 0
            for r in historical:
                gate = L.is_gate(r)
                if not gate:
                    soft_position += 1
                if r["rule_uuid"] in seen:
                    continue
                written = self._current_version_written_at(r["rule_uuid"])
                if written and written > when:
                    # The rule existed, but not in THIS shape. Ranking today's
                    # text and calling the result a historical miss would blame
                    # a rule for wording it did not have, which is precisely the
                    # attribution error this loop was told to refuse.
                    undecidable.append({
                        "session_id": sid, "task_fingerprint": fingerprint,
                        "rule_uuid": r["rule_uuid"],
                        "evidence": "rule_changed_since_retrieval",
                        "reason":
                            "rule %s has been rewritten since this retrieval "
                            "(version %s written %s, retrieval %s), so whether "
                            "it would have been retrieved then cannot be "
                            "decided from today's text"
                            % (r["rule_uuid"][:8], r["current_version"],
                               written, when)})
                    continue
                if gate or soft_position <= requested_limit:
                    miss_kind, cls = "relevance", "retrieval_miss"
                    tail = ("but no application row exists, so it never "
                            "reached the acting model")
                else:
                    miss_kind, cls = "limit", "retrieval_limit_miss"
                    tail = ("but the retrieval asked for %d soft rule(s) and "
                            "this one sat at soft position %d, so the result "
                            "limit cut it before the acting model saw it"
                            % (requested_limit, soft_position))
                misses.append({
                    "session_id": sid, "task_fingerprint": fingerprint,
                    "rule_uuid": r["rule_uuid"], "rank": r["rank"],
                    "retrieval_uuid": run["retrieval_uuid"],
                    "requested_limit": int(run["requested_limit"]),
                    "eligible_at_retrieval": int(run["eligible_count"]),
                    "returned_at_retrieval": int(run["returned_count"]),
                    "retrieval_runs": len(runs),
                    "miss_kind": miss_kind,
                    # The task's own timestamp, so a review window can include
                    # or exclude this miss. A miss has no row of its own, and
                    # without this it would be undateable and would therefore
                    # appear in every window forever.
                    "task_retrieved_at": when,
                    "classification": cls,
                    "classification_reason":
                        "rule %s was approved before this task ran and ranks %d "
                        "of the %d rule(s) that retrieval found eligible, %s"
                        # THE DENOMINATOR IS THE STORED ONE. Printing today's
                        # eligible count beside a stored run made the sentence
                        # contradict the row it cites (run says 2 eligible,
                        # line said "1 of 1"). The two can only differ when the
                        # corpus moved, and that case no longer reaches here.
                        % (r["rule_uuid"][:8], r["rank"],
                           int(run["eligible_count"]), tail)})
        counts["retrieval_miss"] = sum(1 for m in misses
                                       if m["miss_kind"] == "relevance")
        counts["retrieval_limit_miss"] = sum(1 for m in misses
                                             if m["miss_kind"] == "limit")
        return {"applications": graded, "retrieval_misses": misses,
                "not_decidable_tasks": undecidable, "counts": counts,
                "classes": list(L.FAILURE_CLASSES)}

    @staticmethod
    def _historical_corpus(res, run):
        """The rules that can stand in for the corpus AT RETRIEVAL TIME, or a
        refusal saying why they cannot.

        Returns (rules, drift_reason). A non-empty reason means the caller must
        report not_decidable and grade nothing.

        WHY THIS EXISTS (FIX ROUND P6). The miss split was decided by re-ranking
        TODAY's corpus while claiming the stored run as its authority.
        Deprecating one unrelated rule after the fact moved the missed rule's
        position and flipped its class from retrieval_limit_miss to
        retrieval_miss, which is the difference between "your page size was too
        small" and "your ranking or scope is wrong": opposite fixes, on facts
        that did not change. Reproduced on the real CLI before this was written.

        TWO STEPS, AND THE ORDER MATTERS.
          1. Rules the founder approved AFTER the retrieval are dropped. They
             could not have been in that corpus, and leaving them in inflated
             the soft positions of the rules that were.
          2. What remains is COUNTED against the eligible_count the run itself
             recorded. Equal means today's eligible set can stand in for the
             one that ran. Different means rules have been deprecated,
             forgotten or reworded out of eligibility since, the historical
             corpus is not reconstructable, and the loop's own instruction
             applies: say not_decidable rather than use the current corpus as
             if it were historical.

        The count is the strongest check available from what is stored: the run
        records how many rules were eligible, not which ones. An add and a
        removal that exactly cancel out still read as equal (KNOWN-LIMITS)."""
        when = run["created_at"]
        rules = [r for r in res["results"] if r["founder_approved_at"] <= when]
        recorded = int(run["eligible_count"])
        if len(rules) != recorded:
            return ([], (
                "the rule corpus has changed since this retrieval: it recorded "
                "%d eligible rule(s) and %d of today's eligible rules existed "
                "then, so what would have been retrieved cannot be "
                "reconstructed and no miss can be attributed"
                % (recorded, len(rules))))
        return (rules, "")

    def _current_version_written_at(self, rule_uuid):
        """When the rule's CURRENT text was written, or '' if unknowable.

        Not the rule's creation date: the version's. A rule created last year
        and rewritten this morning has today's text, and ranking that text
        against a retrieval from last year proves nothing about what the
        retrieval would have returned."""
        row = _exec(self,
                    "SELECT v.created_at AS at FROM learning_rules r "
                    "JOIN learning_rule_versions v "
                    "  ON v.rule_uuid = r.rule_uuid "
                    " AND v.version = r.current_version "
                    "WHERE r.rule_uuid = ?", (rule_uuid,)).fetchone()
        return row["at"] if row else ""

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
    # rule's state. Approval stays human-confirmed and receipt-gated, here as
    # everywhere: automatic capture can never approve or promote its own
    # candidate.
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
        # Counted under their own names (LOOP P6). Folding a limit miss into
        # retrieval_miss would tell the founder his retrieval is bad when his
        # page size is small, and those have different fixes.
        counts["retrieval_miss"] += sum(1 for m in misses
                                        if m.get("miss_kind") == "relevance")
        counts["retrieval_limit_miss"] += sum(1 for m in misses
                                              if m.get("miss_kind") == "limit")
        notes = []
        if not apps and not misses:
            notes.append("no rule application falls in this window, so every "
                         "class below is not measured rather than zero")
        for kind, sentence in (
                ("no_task_text",
                 "%d task(s) kept no text, so what else was retrievable for "
                 "them cannot be reconstructed"),
                ("legacy",
                 "%d task(s) predate the retrieval-run record, so their misses "
                 "are incomplete evidence rather than zero"),
                ("rule_changed_since_retrieval",
                 "%d rule(s) have been rewritten since the retrieval that "
                 "might have missed them, so those are not decidable")):
            n = sum(1 for u in graded["not_decidable_tasks"]
                    if u.get("evidence") == kind)
            if n:
                notes.append(sentence % n)
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
                    session_id="", note="", evidence="", adopt_from_live_session=False,
                    handover_heading=None):
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
        claim() uses, rather than an unhandled sqlite3.IntegrityError.

        LOOP P12: handover_heading, when given, writes the record's handover
        into the handovers table INSIDE this same transaction (see
        _insert_handover). That is the loop's whole invariant, and it is the
        reason it is a parameter here rather than a second call the caller
        makes afterwards: a refused transition can no longer leave a delivered
        handover behind (the old GATE 3 defect, in a stronger form), and a
        handover that cannot be built (redaction unavailable) rolls the
        transition back instead of parking a thread whose context is gone.
        Leave it None and nothing about this method changes."""
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
            tcur = _exec(self,
                "INSERT INTO transitions (lifecycle_uuid, from_state, to_state, "
                "session_id, note, at) VALUES (?,?,?,?,?,?)",
                (lifecycle_uuid, row["state"], to_state, session_id or "", note or "", ts))
            if handover_heading is not None:
                self._insert_handover(lifecycle_uuid, tcur.lastrowid,
                                       handover_heading,
                                       from_session_id=row["session_id"],
                                       to_session_id=session_id or "", at=ts)
            return self._record_by_uuid(lifecycle_uuid)

    # -- handovers (LOOP P12) ---------------------------------------------

    def _insert_handover(self, lifecycle_uuid, transition_id, heading,
                          from_session_id="", to_session_id="", at=None):
        """Write ONE handover row. Only ever called from inside an already-open
        transaction (transition()'s), which is the whole invariant: the
        lifecycle transition and the handover it produced commit together or
        neither of them exists.

        Its own named method rather than five inline statements so a
        reinjection test can monkeypatch exactly this symbol (to raise, or to
        write nothing) and prove the calibration of the atomicity tests.

        RedactionUnavailable from render_digest propagates: it aborts the whole
        transaction, so a store that cannot redact parks nothing and writes
        nothing, rather than recording a transition whose handover was lost.

        A duplicate loses on handovers_undelivered_text_idx and is swallowed
        HERE, not by the caller: that is the retry path. But the swallow is
        conditional now (fix round, 2026-07-29). It is only honest while an
        UNDELIVERED row carrying this exact lifecycle, fingerprint AND heading
        is still there to render, which is what makes "the earlier row already
        holds this exact text" true. So the swallow re-reads for that twin and
        raises HandoverLost when it cannot find one, which aborts the caller's
        transaction: no handover, no transition.

        The old code returned "already" for ANY IntegrityError and transition()
        discarded the value, so a park whose insert lost committed a lifecycle
        move with nothing to hand over. The index change (partial on
        delivered_at IS NULL, heading in the key) is what removes the loss; this
        check is what makes a future regression impossible to commit silently
        instead of merely unlikely."""
        payload = self.handover_payload(lifecycle_uuid)
        body = self.render_digest(lifecycle_uuid)
        try:
            _exec(self,
                "INSERT INTO handovers (handover_uuid, lifecycle_uuid, "
                "transition_id, from_session_id, to_session_id, payload_fingerprint, "
                "heading, body, delivered_at, created_at) "
                "VALUES (?,?,?,?,?,?,?,?,NULL,?)",
                (uuid.uuid4().hex, lifecycle_uuid, transition_id,
                 from_session_id or "", to_session_id or "",
                 payload["fingerprint"], heading or "", body or "",
                 at or now_iso()))
            return "delivered"
        except sqlite3.IntegrityError:
            twin = _exec(self,
                "SELECT handover_uuid FROM handovers WHERE lifecycle_uuid=? "
                "AND payload_fingerprint=? AND heading=? AND delivered_at IS NULL",
                (lifecycle_uuid, payload["fingerprint"], heading or "")).fetchone()
            if twin is None:
                raise HandoverLost(
                    "the handover for lifecycle %s could not be written and no "
                    "undelivered copy of it exists; the transition was rolled "
                    "back rather than moving the record with its handover lost"
                    % (lifecycle_uuid,),
                    details={"lifecycle_uuid": lifecycle_uuid,
                             "transition_id": transition_id,
                             "heading": heading or ""})
            return "already"

    def undelivered_handovers(self):
        """Every handover nobody has acknowledged yet, oldest first. Read by
        render_state_md so the generated view carries them, and by the
        `handovers` command. A pure read: RENDERING a handover is not
        DELIVERING it, so a crash between the commit and the render costs
        nothing and the next regeneration puts the text back."""
        return _exec(self,
            "SELECT * FROM handovers WHERE delivered_at IS NULL "
            "ORDER BY created_at, rowid").fetchall()

    def acknowledge_handover(self, handover_uuid):
        """Mark ONE handover as delivered, so it stops rendering into STATE.md.
        Idempotent by construction: the UPDATE is guarded on delivered_at IS
        NULL, so a second call changes nothing and reports 'already' rather
        than restamping the time. Never deletes the row: `dump` keeps the whole
        handover history. Raises StaleIdentity for an unknown uuid, because
        acknowledging something that does not exist is a caller mistake worth
        seeing, not a silent no-op."""
        with self._transaction():
            row = _exec(self,
                "SELECT delivered_at FROM handovers WHERE handover_uuid=?",
                (handover_uuid,)).fetchone()
            if row is None:
                raise StaleIdentity(
                    "no handover with handover_uuid %s" % handover_uuid,
                    current_state=None, current_version=None)
            if row["delivered_at"] is not None:
                return "already"
            _exec(self,
                "UPDATE handovers SET delivered_at=? WHERE handover_uuid=? "
                "AND delivered_at IS NULL", (now_iso(), handover_uuid))
            return "delivered"

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

    def directives_for(self, lifecycle_uuid):
        """Every directive for one record, oldest first, AUTHORITATIVE (the
        rows as stored, not a presentation view).

        LOOP 11, the FINDING 9 shape one more time: bm_threads.cmd_send
        regenerated inbox.md from store.dump()["directives"], so the file a
        founder actually reads was a copy of an EXPORT policy's output. The
        moment directives.text became withheld-by-default (which is right
        for an export that gets pasted into an issue), the founder's own
        inbox would have filled with "[WITHHELD: 42 chars]". A local view
        the founder writes and reads is not an export: it gets the same
        treatment STATE.md gets, authoritative rows scrubbed at the display
        boundary by the caller."""
        rows = _exec(self,
            "SELECT seq, text, created_at, delivered_at FROM directives "
            "WHERE lifecycle_uuid=? ORDER BY seq", (lifecycle_uuid,)).fetchall()
        return [dict(r) for r in rows]

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
        direction.

        LOOP 11: redaction was never enough on its own. redact_text is a
        secret SCRUBBER, and founder prose has no secret shape, so an
        ordinary dump still reproduced objectives, evidence, digest bodies,
        transition notes, decisions and directives verbatim. Every text
        column now goes through export_column, which WITHHOLDS by default
        and scrubs only records.name and records.tier. raw=True (CLI: --raw)
        is the explicit, named escape
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
            # A digest-shaped column is routed through the policy even when the
            # structural allowlist names it, because the shape rule outranks the
            # allowlist inside export_column and skipping it here would put that
            # decision back in two places.
            policy_cols = [c for c in text_cols
                           if (t, c) not in _DUMP_SAFE_COLUMNS
                           or c.endswith(_DUMP_DIGEST_SUFFIXES)]
            if not policy_cols:
                continue
            for row_dict in out[t]:
                for col in policy_cols:
                    if not row_dict.get(col):
                        continue
                    # ONE policy, shared with every other export: see
                    # export_column. Withheld by default, scrubbed only for
                    # the two identifier-shaped columns, and digests withheld
                    # by name-shape whatever list they appear on.
                    row_dict[col] = export_column(t, col, row_dict[col])
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


def _redacted_view_block(raw):
    """The same pipeline as _redacted_view_text, applied LINE BY LINE so that
    real newlines survive (LOOP P12).

    Needed because a handover body is a rendered DOCUMENT, not a field: its
    newlines are its structure. _redacted_view_text is right for every field
    beside it, where a newline arriving in founder text is a forged record
    block (SOFT D) and must become a visible \x0a. Run it on a whole digest
    and every line break in the handover collapses into literal \x0a noise
    (reproduced in the LOOP P12 probe before this existed), which is the same
    mistake _out_prerendered exists to avoid at the terminal.

    Every OTHER control character still becomes a visible escape, and each
    line is still marker-neutralized, so a body cannot forge the generated
    block's boundary or smuggle an ANSI escape through a line of its own."""
    if not raw:
        return raw
    return "\n".join(_redacted_view_text(line) for line in raw.split("\n"))


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
        # LOOP P12: handovers are GENERATED here, inside the markers, from the
        # store's own rows. Nothing appends to STATE.md any more, so the
        # append-versus-replace race that used to erase a handover has no
        # surface left. An undelivered handover reappears on every
        # regeneration until it is acknowledged, which is what makes a crash
        # between the commit and the render cost nothing.
        handovers = _undelivered_handover_rows(store)
        if handovers:
            lines.append("## Handovers (undelivered: %d)" % len(handovers))
            lines.append("_Acknowledge one with: %s handover-ack "
                         "--handover <uuid>_" % _cmd())
            lines.append("")
            for h in handovers:
                lines.append("### %s" % (_redacted_view_text(h["heading"])
                                          if h["heading"] else "(no heading)"))
                lines.append("handover %s (lifecycle %s, %s)"
                             % (h["handover_uuid"], h["lifecycle_uuid"], h["created_at"]))
                # Already redacted once by render_digest at insert time; run
                # through the view funnel again so a body written by an older
                # build, or one carrying the literal BEGIN/END marker text,
                # still cannot corrupt this block's boundary (GATE 8b).
                lines.append(_redacted_view_block(h["body"]) if h["body"] else "(empty)")
                lines.append("")
        lines.append(_STATE_END)
        return "\n".join(lines) + "\n"
    finally:
        store.close()


def _undelivered_handover_rows(store):
    """The handovers STATE.md must show, or an empty list on a store whose
    schema predates them.

    The sqlite_master guard is not defensive clutter: _exec turns a "no such
    table" OperationalError into structural damage and QUARANTINES the store,
    so querying handovers on a schema-4 store that has not been migrated yet
    would destroy it to render a section. Asking sqlite_master first cannot
    fail that way, and an older store simply renders no handover section."""
    present = store.conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='handovers'").fetchone()
    if not present:
        return []
    return _exec(store,
        "SELECT * FROM handovers WHERE delivered_at IS NULL "
        "ORDER BY created_at, rowid").fetchall()


# D5 fix (fence sweep, 2026-07-30): every STATE.md render wrote another
# STATE.md.bak-<timestamp> and nothing ever removed one -- seven accumulated
# in fifteen minutes on one machine, and the autosave warning then listed
# them all. Keep only this many; a named constant, not a magic number,
# because "how many backups is enough" is a policy a founder may want to
# change later.
_STATE_BACKUP_KEEP = 5
# The EXACT shape write_state_view itself produces below: "STATE.md.bak-" +
# a fixed-width UTC stamp ("%Y%m%dT%H%M%S%f", 8 digits + "T" + 12 digits)
# plus an optional "-" + 8 lowercase hex chars (uuid4().hex[:8]) on a same-
# microsecond collision. Deliberately narrow: a file this code did not
# create must never be a deletion candidate.
_STATE_BACKUP_RE = re.compile(r"^STATE\.md\.bak-\d{8}T\d{12}(-[0-9a-f]{8})?$")


def _prune_old_state_backups(root):
    """Delete STATE.md.bak-<timestamp> files beyond the _STATE_BACKUP_KEEP
    most recent, called at the MOMENT write_state_view creates a fresh one,
    never batched at the end. The fixed-width timestamp in the name sorts
    lexically in chronological order, so a plain name sort finds the
    oldest. Every deletion is logged at the point it happens (fix-round
    requirement: 'logging each deletion at the deletion, never batched at
    the end'). Best-effort throughout: a listing or delete failure here
    must never block the render it is a side effect of."""
    try:
        names = sorted(n for n in os.listdir(root) if _STATE_BACKUP_RE.match(n))
    except OSError:
        return
    for name in names[:max(0, len(names) - _STATE_BACKUP_KEEP)]:
        try:
            stale_path = safe_project_path(root, name)
            os.remove(stale_path)
        except (OSError, OwnershipRefused) as e:
            _warn("bm_store: could not prune old backup %s (%s)" % (name, e))
            continue
        _warn("bm_store: pruned old backup %s (keeping the %d most recent)"
              % (stale_path, _STATE_BACKUP_KEEP))


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
        _prune_old_state_backups(root)
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


# THE HUMAN BLOCK MARKERS, owned here because the FUNNEL has to know them.
#
# They live in the store module rather than in bm_packs.py for one reason: the
# funnel below is the only code allowed to write a generated file, and it cannot
# protect a block whose boundaries it cannot see. Phase B's documentation engine
# writes files with the same markers (spec section B.4), so one definition also
# keeps the pack and the engine from drifting into two spellings of the same
# promise. bm_packs.py imports these rather than declaring its own.
HUMAN_BLOCK_BEGIN = "<!-- bm-human:begin -->"
HUMAN_BLOCK_END = "<!-- bm-human:end -->"


def _human_block_spans(text):
    """1-based line numbers of the lines INSIDE human blocks, as a set.

    The markers themselves are generated structure and are not included: they
    are redacted with the rest of the document, which changes nothing because
    they are fixed strings this project writes.

    Deliberately tolerant, for the same reason read_existing in bm_packs.py is:
    an unterminated block runs to the end of the file rather than being treated
    as absent, because guessing "no human text here" is the guess that destroys
    it. A second begin marker INSIDE a block is content, not a nested block."""
    inside = set()
    depth = 0
    for i, line in enumerate(text.split("\n"), 1):
        stripped = line.strip()
        if stripped == HUMAN_BLOCK_BEGIN and not depth:
            depth = 1
            continue
        if stripped == HUMAN_BLOCK_END and depth:
            depth = 0
            continue
        if depth:
            inside.add(i)
    return inside


def human_block_secret_hits(text):
    """Lines inside human blocks that the redactor WOULD have changed.

    Returns a list of 1-based line numbers, empty when there is nothing to say.
    The funnel preserves those lines (see _write_generated_file), so this is how
    a generator tells a human that their own paragraph contains something
    secret-shaped: preserved, and reported, rather than rewritten in silence.

    Raises RedactionUnavailable, like every other caller of redact_text, because
    "I could not check" must never read as "there was nothing to find"."""
    inside = _human_block_spans(text or "")
    if not inside:
        return []
    hits = []
    for i, line in enumerate((text or "").split("\n"), 1):
        if i in inside and redact_text(line) != line:
            hits.append(i)
    return hits


def _redact_outside_human_blocks(text):
    """redact_text over the generated parts of a document, VERBATIM inside the
    human blocks.

    I10 SAYS GENERATED OUTPUT NEVER DESTROYS HUMAN TEXT, and this funnel used to
    break it in the one way nobody would notice. It ran redact_text over the
    whole rendered document, human blocks included, and the redactor is a
    PATTERN scrubber, not a secret oracle: 'the DB password: ask Sam' comes back
    as 'the DB [REDACTED] Sam'. So a reviewer's paragraph was silently rewritten
    on the next regeneration, the CLI reported the block as preserved, the change
    was convergent (a later diff showed nothing), and there was no copy of the
    original anywhere.

    The human block is text a human typed into a file on disk. It never came out
    of the store, so scrubbing it protects nothing that is not already written
    down; what it does is destroy the one thing this project promises never to
    destroy. It is therefore carried through byte for byte, and
    human_block_secret_hits reports anything secret-shaped in it so the founder
    can decide.

    Everything OUTSIDE the markers, which is every line assembled from store
    rows and repository text, is redacted exactly as before. A document with no
    markers (STATE.md) takes the identical whole-text path it always did."""
    inside = _human_block_spans(text or "")
    if not inside:
        return redact_text(text or "")
    out = []
    generated = []

    def _flush():
        if generated:
            out.append(redact_text("\n".join(generated)))
            del generated[:]

    for i, line in enumerate((text or "").split("\n"), 1):
        if i in inside:
            _flush()
            out.append(line)
        else:
            generated.append(line)
    _flush()
    return "\n".join(out)


def _write_generated_file(path, text, protect_human_blocks=False):
    """THE FILE FUNNEL (see THE OUTPUT FUNNEL note below): the only path
    allowed to write a generated file (STATE.md, via write_state_view, and any
    generated document a sibling tool writes through
    write_generated_document). Runs redact_text() over the whole text
    unconditionally before _atomic_write_text ever sees it; if the redactor is
    unavailable this raises RedactionUnavailable and nothing is written.

    protect_human_blocks is OPT IN, and it is off for STATE.md on purpose. A
    caller passing it promises the text is a DOCUMENT THIS PROJECT RENDERED with
    the human markers as its own structure (read _redact_outside_human_blocks for
    what the exemption buys and costs). STATE.md is assembled partly from
    founder-typed store fields, and a field whose value happened to be the begin
    marker would otherwise switch redaction off for the rest of the file, so that
    door stays closed rather than trusted.

    Deliberately skips _sanitize_for_display (unlike _protect_text, for
    single-line messages): the text is a multi-line DOCUMENT whose own
    newlines, and the real BEGIN/END markers, are structure this module is
    writing on purpose, not founder-typed injection; sanitizing the whole
    document a second time would escape them into literal \\x0a text and
    corrupt the file. Every founder-typed VALUE was already sanitized per
    field before assembly (_redacted_view_text); redact_text() here is a
    defense-in-depth secret-pattern scan that does not touch newlines. It is
    NOT run over the human blocks, because a pattern scrubber over human prose
    is not defense, it is deletion: see _redact_outside_human_blocks.

    Returns the protected text actually written (never the unprotected
    input), so a caller holding the return value never disagrees with disk."""
    if protect_human_blocks:
        protected = _redact_outside_human_blocks(text or "")
    else:
        protected = redact_text(text or "")
    _atomic_write_text(path, protected)
    return protected


def write_generated_document(path, text):
    """THE FILE FUNNEL, for a generated DOCUMENT written by a sibling tool.

    Added for the gate deep-dive packs (2026-07-30). bm_packs.py renders a
    markdown document out of store rows and repository text, and a second
    private copy of "redact, then write atomically" in that file would be the
    third time this project grew a weaker duplicate of this exact primitive.
    So there is one funnel and this is its public door: same redact_text over
    everything the generator assembled, same crash-atomic replacement, same
    refusal to write anything at all when the redactor is unavailable, and the
    human blocks carried through verbatim per I10.

    The caller owns the path, and is expected to have built it with
    safe_project_path so it cannot land outside the project. The directory must
    exist; this creates nothing, because a funnel that makes directories is a
    funnel that can write somewhere nobody meant.

    This door, and only this door, protects the human blocks: the text is a
    document a sibling generator rendered, whose markers it wrote itself."""
    return _write_generated_file(path, text, protect_human_blocks=True)


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


def _require_positional(argv, print_usage):
    """Return argv[0] as a command's required positional (a record name or a
    lifecycle_uuid), after confirming one is actually there.

    D1/D2 (fence sweep, 2026-07-30): every `cmd_*` below used to read
    `name = argv[0]` (or `lifecycle_uuid = argv[0]`) the moment argv was
    non-empty, with no check that argv[0] was not itself a flag the caller
    forgot a positional in front of. `claim --help` ran with argv ==
    ["--help"], so "--help" became the record NAME and got claimed for
    real, before `_reject_unknown_flags` ever saw a flag to reject (it never
    runs on argv[0] at all). Same shape for `claim --objective X --files a.py`
    ("--objective" claimed as the name) and for every other command that
    takes a positional first: park/resume/complete/adopt (--version being
    read as the lifecycle_uuid), checkpoint, decide.

    print_usage is the command's OWN existing usage block (a zero-arg
    callable), never a new string invented here, so this refuses in exactly
    the words the empty-argv case already used. Exits 2 without calling
    print_usage twice and without touching the store either way."""
    if not argv or argv[0].startswith("-"):
        print_usage()
        sys.exit(2)
    return argv[0]


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


def _cmd_claim_usage():
    _out("usage: claim <name> --lifetime persistent|ephemeral --objective TEXT "
         "[--files PATH ...] [--release-files] [--owner X] [--session SID] "
         "[--tier T] [--check CMD]")
    _out("  --files with at least one path REPLACES the fence (on a reclaim).")
    _out("  --release-files explicitly releases every file (on a reclaim); "
         "omitting --files entirely LEAVES the existing fence untouched, "
         "it can never be dropped by accident.")
    _out("  On a reclaim, omitting --objective/--tier/--check/--owner LEAVES "
         "each untouched; typing the flag, even with an empty value, sets it.")


def cmd_claim(argv):
    # D1/D2 fix (fence sweep, 2026-07-30): `_require_positional` refuses
    # BEFORE anything reads argv[1:], so `claim --help` or
    # `claim --objective X --files a.py` (no name in front) print this same
    # usage block and exit 2 instead of claiming a record literally named
    # "--help" or "--objective".
    name = _require_positional(argv, _cmd_claim_usage)
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
    # D1/D2-class fix (fence sweep, 2026-07-30): same shape as cmd_claim --
    # `park --version 3` with no lifecycle_uuid in front used to read
    # "--version" as the uuid. See _require_positional's docstring.
    lifecycle_uuid = _require_positional(argv, lambda: _out("usage: %s" % usage))
    kv = _parse_kv(argv[1:])
    _reject_unknown_flags("transition", kv,
        ("version", "session", "note", "evidence", "adopt-from-live-session",
         "handover"))
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
    # LOOP P12: --handover "<heading>" writes the record's handover in the SAME
    # transaction as this move. Absent, no handover is written at all, which is
    # the right default for a park a session does mid-work and expects to
    # resume itself. `" ".join` on the raw flag, so --handover with no value
    # yields an empty heading rather than None, and still asks for a handover.
    handover_heading = (" ".join(kv["handover"]) if "handover" in kv else None)
    root, _source = require_root()
    store = Store(root, create=False)
    try:
        before = store.get(lifecycle_uuid)
        rec = store.transition(lifecycle_uuid, expected_version, to_state,
                                session_id=session_id, note=note, evidence=evidence,
                                adopt_from_live_session=adopt_from_live_session,
                                handover_heading=handover_heading)
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
    # D4 fix (fence sweep, 2026-07-30): --handover "<heading>" is accepted by
    # _reject_unknown_flags's "transition" allow-list (shared by park/resume/
    # complete/adopt) but appeared in none of their usage lines, making the
    # whole person-to-person handover mechanism undiscoverable from the CLI.
    _cmd_transition(argv, "parked",
                     "park <lifecycle_uuid> --version N [--session SID] [--note TEXT] "
                     "[--handover \"<heading>\"]")


def cmd_resume(argv):
    _cmd_transition(argv, "active",
                     "resume <lifecycle_uuid> --version N [--session SID] [--note TEXT] "
                     "[--handover \"<heading>\"]")


def cmd_complete(argv):
    _cmd_transition(argv, "complete",
                     "complete <lifecycle_uuid> --version N --evidence TEXT [--session SID] "
                     "[--note TEXT] [--handover \"<heading>\"]")


def cmd_adopt(argv):
    _cmd_transition(argv, "adopted",
                     "adopt <lifecycle_uuid> --version N [--session SID] [--note TEXT] "
                     "[--adopt-from-live-session]  (required to adopt a record that is "
                     "currently active under a different, live session) "
                     "[--handover \"<heading>\"]")


def _cmd_checkpoint_usage():
    _out("usage: checkpoint <lifecycle_uuid> --version N --next TEXT "
         "[--blockers TEXT] [--files-note TEXT] [--body TEXT]")


def cmd_checkpoint(argv):
    # D1/D2-class fix (fence sweep, 2026-07-30): see _require_positional.
    lifecycle_uuid = _require_positional(argv, _cmd_checkpoint_usage)
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


def _cmd_decide_usage():
    _out("usage: decide <lifecycle_uuid> --version N --topic T --text TEXT")


def cmd_decide(argv):
    # D1/D2-class fix (fence sweep, 2026-07-30): see _require_positional.
    lifecycle_uuid = _require_positional(argv, _cmd_decide_usage)
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
                  "field UNREDACTED (cleartext). That includes founder "
                  "prose an ordinary dump WITHHOLDS entirely (objectives, "
                  "evidence, digest bodies, transition notes, decisions, "
                  "directives, captured corrections) and absolute paths. "
                  "Treat this output like the database file itself.")
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


def cmd_handovers(argv):
    """List the handovers nobody has acknowledged yet. A diagnostic, so it
    reads through ReadOnlyStore and never creates the store it is reporting
    on, exactly like dump and dashboard."""
    _reject_unknown_flags("handovers", _parse_kv(argv), ())
    root, _source = require_root()
    store = ReadOnlyStore(root)
    try:
        rows = _undelivered_handover_rows(store)
        if not rows:
            _out("handovers: none undelivered.")
            return
        _out("handovers: %d undelivered" % len(rows))
        for h in rows:
            _out("- %s  lifecycle %s  %s"
                 % (h["handover_uuid"], h["lifecycle_uuid"], h["created_at"]))
            _out("  %s" % (_redacted_view_text(h["heading"])
                           if h["heading"] else "(no heading)"))
    finally:
        store.close()


def cmd_handover_ack(argv):
    """Acknowledge ONE handover so it stops rendering into STATE.md. The row
    stays; only delivered_at changes. Re-running it is a no-op that says so,
    which is the property that makes a retry after a crash safe."""
    kv = _parse_kv(argv)
    _reject_unknown_flags("handover-ack", kv, ("handover",))
    handover_uuid = " ".join(kv.get("handover", []))
    if not handover_uuid:
        _out("usage: handover-ack --handover <handover_uuid>")
        sys.exit(2)
    root, _source = require_root()
    store = Store(root, create=False)
    try:
        outcome = store.acknowledge_handover(handover_uuid)
    finally:
        store.close()
    _refresh_state_view(root)
    if outcome == "already":
        _out("handover-ack: %s was already acknowledged; nothing changed." % handover_uuid)
    else:
        _out("handover-ack: %s acknowledged; it no longer renders into STATE.md."
             % handover_uuid)


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
    "verify": cmd_verify, "handovers": cmd_handovers,
    "handover-ack": cmd_handover_ack,
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
