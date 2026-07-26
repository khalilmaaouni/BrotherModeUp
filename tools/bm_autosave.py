#!/usr/bin/env python3
"""BrotherMode autosave (Phase 2, ratified design 2026-07-26): mechanical,
verifiable work-preservation. Replaces tools/bm_autosave.sh, removed in this
same change (docs/superpowers/specs/2026-07-26-phase2-recovery-design.md).

WHY THIS EXISTS
  Every "never lose work" rule in the constitution is PROSE the model must
  remember to run, at exactly the moment (running out of tokens, failing
  repeatedly) it is least able to remember anything. This module closes that
  hole mechanically: the harness fires it, not the model. Autosave is the
  component a founder reaches for when everything else has already gone
  wrong, which is why a backup that can silently be empty, or that deletes a
  file on restore, is worse than no backup: it replaces caution with false
  confidence. Seven such defects were reproduced by executing the V1 shell
  script (see the spec's table); this module closes all seven at once.

WHY PYTHON, NOT SHELL (deliberate, ratified)
  Windows support is ratified scope and shell scripts do not run there.

WHY SUBPROCESS IS ALLOWED IN THIS MODULE ONLY (deliberate, documented
exception, NOT a silent widening; tools/test_bm.py's no-network gate bans
`subprocess` in every other tools/*.py on purpose)
  git is the one external binary this project needs to snapshot a working
  tree, and there is no stdlib way to drive it. Every subprocess call in
  this file invokes `git` directly (argv list, never a shell string) with a
  fixed, reviewed argument shape; none of them is push, fetch, pull, clone,
  or remote, so the audited "no network, ever" property still holds: every
  call is local. SECURITY.md should record this same exception (out of this
  change's fence; flagged, not silently assumed).

WHAT CHANGED FROM V1 (closes FA, FC, FD, FE, FI, F2b, and the writer half
of J; see the spec for the full defect table)
  - One fixed ref (refs/brothermode/autosave) is now a NAMESPACE per
    worktree and per session, so linked worktrees of one repository can
    never overwrite each other's only backup (FA).
  - The temporary index is seeded from HEAD (`git read-tree HEAD`) before
    working-tree changes are staged, so a tracked file that secret-exclusion
    skips still carries its last committed content into the snapshot
    instead of vanishing (FC's root cause). Recovery never restores INTO the
    live working tree at all: it checks out the snapshot into a brand new
    `git worktree`, so the old delete-on-restore path cannot exist (FC).
  - A clean working tree (matches HEAD) clears this worktree's "latest"
    pointer instead of leaving it aimed at old, deliberately-discarded WIP
    (FD).
  - Every git call's return code is checked before its output is trusted; a
    failure aborts the whole snapshot BEFORE anything touches the existing
    latest pointer, and the universal empty-tree sha is refused explicitly
    as a second, independent guard (FE).
  - Every environment variable this module reads is parsed defensively:
    unset, zero, negative, non-numeric, and absurdly large all fall back to
    the default with one warning line, and every entrypoint exits 0 no
    matter what (FI).
  - `git rev-parse --show-toplevel` is resolved FIRST, and every git call
    after that runs with `-C <toplevel>`, so a snapshot triggered from a
    subdirectory still covers the whole repository instead of silently
    scoping the "." pathspec to that subdirectory (F2b).
  - A successful snapshot writes one row into the store's autosave_receipts
    table (schema shipped in Phase 1, tools/bm_store.py), giving a separate
    "is this actually saved" reader something true to check instead of
    assuming (the writer half of J; the reader half, the compact-hint
    consumer in tools/bm_telemetry.py, is a different fenced change).

NOTE ON worktree_id (a documented deviation from one literal phrasing in the
design draft, verified by direct execution rather than assumed)
  worktree_id is a short hash of THIS worktree's own resolved toplevel path,
  not of `git rev-parse --git-common-dir`. Common-dir was tried first and
  rejected: it resolves to the SAME shared main .git directory for every
  linked worktree of one repository (confirmed by running `git worktree add`
  and comparing --git-common-dir from both checkouts), so hashing it alone
  cannot be what distinguishes two worktrees, and using it as the sole input
  would reproduce FA rather than close it. The toplevel path is exactly what
  differs between two worktrees of the same repository, and it is stable for
  the life of that worktree, which is what a per-worktree ref namespace and
  "latest" pointer both need.

Python 3.9, standard library only (the one documented subprocess exception
above). No em or en dashes anywhere in this file, its comments, or output.
"""
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Configuration and constants.
# ---------------------------------------------------------------------------
VAULT = os.environ.get("BROTHERMODE_VAULT", os.path.expanduser("~/BrotherModeVault"))
TEL_DIR = os.path.join(VAULT, "99-System", "telemetry")

REF_NAMESPACE = "refs/brothermode/autosave"
EMPTY_TREE_SHA = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

DEFAULT_TICK_EVERY = 20
DEFAULT_RUNAWAY_AT = 600
DEFAULT_RETAIN = 10

# Secret-shaped paths: excluded from the STAGE step only, never from the
# seed (requirement 5, FC). Mirrors tools/bm_autosave.sh's own list exactly,
# so the set of protected shapes does not silently narrow in the rewrite.
SECRET_EXCLUDE_PATHSPECS = (
    ":(exclude,glob)**/.env", ":(exclude).env", ":(exclude,glob)**/.env.*",
    ":(exclude,glob)**/*.pem", ":(exclude,glob)**/*.key", ":(exclude,glob)**/*.p12",
    ":(exclude,glob)**/*.keystore", ":(exclude,glob)**/id_rsa", ":(exclude,glob)**/id_dsa",
    ":(exclude,glob)**/*.pfx",
)
# The same shapes, as plain glob suffixes, for the informational
# captured/excluded counts on the receipt (best-effort only; the pathspecs
# above are the real, enforced boundary, not this classifier).
SECRET_GLOBS = (
    "**/.env", ".env", "**/.env.*", "**/*.pem", "**/*.key", "**/*.p12",
    "**/*.keystore", "**/id_rsa", "**/id_dsa", "**/*.pfx",
)

_UNSAFE_REF_CHARS = re.compile(r"[^A-Za-z0-9_.-]")


class SnapshotAborted(Exception):
    """Raised internally when a git step fails partway through building a
    snapshot, so the caller stops before update-ref ever touches the
    existing latest pointer (FE). Always caught inside snapshot(); never
    escapes this module, because autosave is advisory and must never block
    a session."""


def _warn(msg):
    """The one place this module writes a warning. Never raises: a full
    disk or a closed stderr must not turn an advisory warning into a crash."""
    try:
        sys.stderr.write("bm_autosave: WARNING: %s\n" % msg)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Defensive environment parsing (requirement 10, FI): every env var this
# module reads goes through here. Unset, zero, negative, non-numeric, and
# absurdly large all fall back to `default` with exactly one warning line
# (unset is the normal, expected path and warns nothing); nothing here ever
# raises. The old shell script did `$((n % TICK_EVERY))`, a hard crash the
# moment TICK_EVERY was 0 or not a number.
# ---------------------------------------------------------------------------
def _parse_int_env(name, default, minimum=1, maximum=10_000_000):
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        n = int(raw.strip())
    except ValueError:
        _warn("%s=%r is not an integer; using the default (%d)" % (name, raw, default))
        return default
    if n < minimum:
        _warn("%s=%d is below the minimum (%d); using the default (%d)"
              % (name, n, minimum, default))
        return default
    if n > maximum:
        _warn("%s=%d is unreasonably large (over %d); using the default (%d)"
              % (name, n, maximum, default))
        return default
    return n


# ---------------------------------------------------------------------------
# git plumbing: the one wrapper every call in this module goes through.
# ---------------------------------------------------------------------------
def _run_git(toplevel, *args, env=None):
    """Every git call in this module runs through here, always with
    `-C <toplevel>` (requirement 2, F2b): resolving the repository root
    once and rooting every subsequent call there, instead of relying on the
    caller's cwd, is what makes a snapshot triggered from a subdirectory
    still cover the whole repository rather than silently scoping the '.'
    pathspec to that subdirectory. Returns a CompletedProcess-shaped result
    even when git itself cannot be executed, so every caller's return-code
    check works uniformly."""
    e = dict(os.environ)
    if env:
        e.update(env)
    try:
        return subprocess.run(
            ["git", "-C", toplevel] + list(args),
            capture_output=True, text=True, env=e)
    except OSError as ex:
        return subprocess.CompletedProcess(args, 127, "", str(ex))


def _checked(result, step):
    """The ONE gate every git call's return code passes through before its
    output is trusted (requirement 4, FE): a non-zero return code raises
    SnapshotAborted naming the step, so a caller can never accidentally
    continue past a failure the way the old shell script did (a failed
    `git add` was ignored there, and an empty tree replaced a good
    snapshot). Deliberately its own named function, not an inline `if`, so
    a reinjection test can prove calibration by monkeypatching exactly this
    name back to a pass-through and watching the guarantee break."""
    if result.returncode != 0:
        raise SnapshotAborted(
            "%s failed (rc=%s): %s" % (step, result.returncode, (result.stderr or "").strip()))
    return result


def resolve_toplevel(start_dir):
    """git rev-parse --show-toplevel from start_dir, resolved to a real
    path (requirement 2, MUST run first). Returns None when start_dir is
    not inside a git repository: a non-git project is a clean, silent
    no-op, since advisory surfaces fail open."""
    try:
        r = subprocess.run(["git", "-C", start_dir, "rev-parse", "--show-toplevel"],
                            capture_output=True, text=True)
    except OSError:
        return None
    if r.returncode != 0:
        return None
    top = r.stdout.strip()
    if not top:
        return None
    return os.path.realpath(top)


def worktree_id_for(toplevel):
    """A short, stable hash of THIS worktree's own checkout path. See the
    module header's NOTE for why this is the toplevel path and not
    `git rev-parse --git-common-dir` (that value is identical across every
    linked worktree of one repository, verified by direct execution, and so
    cannot be what distinguishes them)."""
    return hashlib.sha256(os.path.realpath(toplevel).encode("utf-8", "replace")).hexdigest()[:12]


def _safe_ref_component(s):
    """Sanitize a caller-supplied string (a hook's session_id) before it
    becomes part of a git ref path: git ref components reject some
    characters outright, and a rejected ref name must never surface as a
    crash (every path here still exits 0), only as an honest warning from
    _checked's caller."""
    s = _UNSAFE_REF_CHARS.sub("_", s or "")
    s = s.strip(".") or "unknown"
    return s


def snapshot_ref(worktree_id, session_id, stamp):
    return "%s/%s/%s/%s" % (REF_NAMESPACE, worktree_id, _safe_ref_component(session_id), stamp)


def latest_ref(worktree_id):
    return "%s/%s/latest" % (REF_NAMESPACE, worktree_id)


def _stamp():
    """A lexically sortable, effectively-unique snapshot identifier: a
    zero-padded microsecond epoch (so string sort order equals chronological
    order, which retention pruning relies on) plus a short random suffix so
    two snapshots requested in the same microsecond can never collide."""
    return "%020d-%s" % (int(time.time() * 1_000_000), uuid.uuid4().hex[:6])


def _is_secret_shaped(rel_path):
    """Best-effort classifier for the receipt's informational
    captured/excluded counts ONLY. The real, enforced boundary is
    SECRET_EXCLUDE_PATHSPECS, passed straight to git; this never gates
    anything, it only labels a number a human might read later."""
    name = os.path.basename(rel_path)
    for g in SECRET_GLOBS:
        leaf = g.rsplit("/", 1)[-1]
        if fnmatch.fnmatch(name, leaf):
            return True
        if fnmatch.fnmatch(rel_path, g.replace("**/", "*/")) or fnmatch.fnmatch(rel_path, g):
            return True
    return False


def _count_paths(toplevel):
    """Informational captured/excluded counts for the receipt row: how many
    changed paths (tracked edits + untracked new files) the real working
    tree currently has, split by whether they look secret-shaped. Read-only
    (`git status`); never touches the temp index this snapshot is building."""
    r = _run_git(toplevel, "status", "--porcelain", "-z", "--untracked-files=all")
    if r.returncode != 0:
        return 0, 0
    entries = [e for e in r.stdout.split("\x00") if e]
    captured = excluded = 0
    for entry in entries:
        path = entry[3:] if len(entry) > 3 else entry
        if _is_secret_shaped(path):
            excluded += 1
        else:
            captured += 1
    return captured, excluded


def _clear_latest_if_present(toplevel, worktree_id):
    """FD: when the working tree matches HEAD, this worktree's "latest"
    pointer is cleared rather than left aimed at old, deliberately-discarded
    WIP, so a stale snapshot can never present itself as current."""
    ref = latest_ref(worktree_id)
    check = _run_git(toplevel, "rev-parse", "-q", "--verify", ref)
    if check.returncode == 0:
        _run_git(toplevel, "update-ref", "-d", ref)


def _prune_old_snapshots(toplevel, worktree_id, retain=None):
    """Requirement 8 (retention): keep the last `retain` snapshot refs per
    worktree (default 10), never the only one.

    Sort on the STAMP ALONE, never the whole ref name. A ref looks like
    <namespace>/<worktree>/<session>/<stamp>, so sorting the full string ranks
    the session id above the timestamp: a snapshot from a session whose id sorts
    early is treated as older than every snapshot from a session whose id sorts
    late, no matter when either was taken. That is not a cosmetic ordering bug.
    Reproduced 2026-07-26: ten snapshots from session zzz-old, then the newest
    snapshot from session aaa-new, and the pruner deleted THE NEWEST while
    keeping all ten older ones. In a module whose entire purpose is not losing
    work, sorting by the wrong key destroys exactly the snapshot the founder
    would reach for."""
    if retain is None:
        retain = _parse_int_env("BROTHERMODE_AUTOSAVE_RETAIN", DEFAULT_RETAIN)
    prefix = "%s/%s/" % (REF_NAMESPACE, worktree_id)
    r = _run_git(toplevel, "for-each-ref", "--format=%(refname)", prefix)
    if r.returncode != 0:
        return
    refs = [line.strip() for line in r.stdout.splitlines() if line.strip()]
    snap_refs = sorted(
        (ref for ref in refs if not ref.endswith("/latest")),
        key=lambda r: r.rsplit("/", 1)[-1])
    if len(snap_refs) <= 1:
        return  # never prune the only snapshot
    excess = snap_refs[: max(0, len(snap_refs) - max(retain, 1))]
    for ref in excess:
        _run_git(toplevel, "update-ref", "-d", ref)


# ---------------------------------------------------------------------------
# Receipts (requirement 9, the writer half of J): best-effort, advisory.
# Reuses tools/bm_store.py's own Store class (loaded by path, the same
# importlib pattern bm_store.py itself uses for bm_telemetry) rather than
# reimplementing schema or connection handling; this module never writes
# SQL DDL of its own and never changes bm_store.py.
#
# Every warning below fires every time it applies, deliberately NOT
# deduplicated across calls: unlike bm_store.py's long-lived Store object
# (many renders in one process, where a repeated warning really would be
# spam), a real invocation of this module is its own fresh, short-lived
# process per hook fire, so "once" and "every time" already coincide there.
# ---------------------------------------------------------------------------
def _load_bm_store():
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "bm_store_for_autosave", os.path.join(HERE, "bm_store.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception as e:
        _warn("could not load bm_store.py (%r); the snapshot still counts, "
              "but no receipt was recorded" % (e,))
        return None


def _open_store_for_receipt(toplevel):
    bs = _load_bm_store()
    if bs is None:
        return None, None
    try:
        root, _source = bs.resolve_root(toplevel)
    except Exception:
        root = None
    if root is None:
        _warn("no BrotherMode store root found from %s; the snapshot still "
              "counts, but no receipt was recorded" % toplevel)
        return None, None
    try:
        store = bs.Store(root, create=False)
    except Exception as e:
        _warn("could not open the BrotherMode store (%r); the snapshot still "
              "counts, but no receipt was recorded" % (e,))
        return None, None
    return bs, store


def _write_receipt(toplevel, worktree_id, session_id, snapshot_sha, tree_sha,
                    source_head, captured, excluded):
    """Advisory only: a missing or refusing store must never fail a
    snapshot that already succeeded (requirement 9's own text: "warn once
    and continue")."""
    bs, store = _open_store_for_receipt(toplevel)
    if store is None:
        return
    try:
        conn = store.conn
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "INSERT INTO autosave_receipts (worktree_id, session_id, snapshot_sha, "
            "tree_sha, source_head, captured_count, excluded_count, created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (worktree_id, session_id, snapshot_sha, tree_sha, source_head or "",
             captured, excluded, bs.now_iso()))
        conn.execute("COMMIT")
    except Exception as e:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        _warn("could not write an autosave receipt (%r); the snapshot still "
              "counts, but is not recorded" % (e,))
    finally:
        try:
            store.close()
        except Exception:
            pass


def has_receipt(toplevel, worktree_id, session_id):
    """True when a receipt row exists for this worktree AND this session.
    This is the honest ground truth a compact-hint reader needs to stop
    claiming "your files are autosaved" without checking (J); writing it is
    this module's job, reading it from the hook is a separate fenced
    change."""
    bs, store = _open_store_for_receipt(toplevel)
    if store is None:
        return False
    try:
        row = store.conn.execute(
            "SELECT 1 FROM autosave_receipts WHERE worktree_id=? AND session_id=? LIMIT 1",
            (worktree_id, session_id)).fetchone()
        return row is not None
    except Exception:
        return False
    finally:
        try:
            store.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# The core operation.
# ---------------------------------------------------------------------------
def snapshot(toplevel, session_id, reason):
    """Snapshot the working tree of `toplevel` into a namespaced ref.
    Never raises past this function: every caller (a hook or the CLI) must
    exit 0 regardless (never-block). Returns a small dict describing what
    happened, for tests and for anyone who wants to log it.

    The pipeline, in order (requirement 5, FC): seed a throwaway temp index
    from HEAD when HEAD exists, stage the current working tree onto it
    (secret-shaped paths excluded from this stage only, never from the
    seed), write the resulting tree, and either commit it (dirty case) or
    clear the latest pointer (clean case, FD). Every git call's return code
    is checked (FE) before the next step runs, and the empty tree sha is
    refused explicitly as a second, independent guard."""
    worktree_id = worktree_id_for(toplevel)
    tmp_fd, index_path = tempfile.mkstemp(prefix="bm-autosave-index-")
    os.close(tmp_fd)
    try:
        os.remove(index_path)  # git rejects a zero-byte index; let it build a fresh one
    except OSError:
        pass
    try:
        head = _run_git(toplevel, "rev-parse", "-q", "--verify", "HEAD")
        has_head = head.returncode == 0
        idx_env = {"GIT_INDEX_FILE": index_path}

        if has_head:
            _checked(_run_git(toplevel, "read-tree", "HEAD", env=idx_env), "read-tree HEAD")

        _checked(
            _run_git(toplevel, "add", "-A", "--", ".", *SECRET_EXCLUDE_PATHSPECS, env=idx_env),
            "add")

        tree = _checked(_run_git(toplevel, "write-tree", env=idx_env), "write-tree").stdout.strip()
        if not tree or tree == EMPTY_TREE_SHA:
            _warn("write-tree produced the empty tree; refusing to publish an "
                  "empty snapshot over any existing one")
            return {"ok": False, "reason": "empty-tree"}

        if has_head:
            head_tree = _run_git(toplevel, "rev-parse", "-q", "--verify", "HEAD^{tree}").stdout.strip()
            if tree == head_tree:
                _clear_latest_if_present(toplevel, worktree_id)
                return {"ok": True, "reason": "clean", "tree": tree}

        parent = head.stdout.strip() if has_head else ""
        msg = "brothermode autosave: %s" % reason
        if parent:
            commit_result = _run_git(toplevel, "commit-tree", tree, "-p", parent, "-m", msg)
        else:
            commit_result = _run_git(toplevel, "commit-tree", tree, "-m", msg)
        commit = _checked(commit_result, "commit-tree").stdout.strip()
        if not commit:
            _warn("commit-tree produced no sha; aborting without touching the latest pointer")
            return {"ok": False, "reason": "no-commit"}

        sref = snapshot_ref(worktree_id, session_id, _stamp())
        _checked(_run_git(toplevel, "update-ref", sref, commit), "update-ref snapshot")
        _checked(_run_git(toplevel, "update-ref", latest_ref(worktree_id), commit), "update-ref latest")

        _prune_old_snapshots(toplevel, worktree_id)

        captured, excluded = _count_paths(toplevel)
        _write_receipt(toplevel, worktree_id, session_id, commit, tree, parent, captured, excluded)

        return {"ok": True, "reason": reason, "commit": commit, "tree": tree, "ref": sref}
    except SnapshotAborted as e:
        _warn(str(e))
        return {"ok": False, "reason": "aborted", "error": str(e)}
    finally:
        try:
            os.remove(index_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Hook and CLI entrypoints. Every one of these exits 0 no matter what
# (requirement 10): main() wraps the whole dispatch in a bare except.
# ---------------------------------------------------------------------------
def _read_hook_payload():
    """Best-effort JSON parse of stdin, matching bm_telemetry.py's own hook
    readers. Never raises: a hook that sends garbage, or nothing, must not
    crash an advisory tool."""
    try:
        raw = sys.stdin.read()
    except Exception:
        return {}
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def cmd_precompact():
    """PreCompact hook target: snapshot once, unconditionally. Fired right
    before the token-death moment. Returns the snapshot() result (or None
    on a clean no-op) so a caller, including a test, can inspect what
    happened; the hook itself ignores the return value."""
    payload = _read_hook_payload()
    cwd = payload.get("cwd") or os.getcwd()
    session_id = payload.get("session_id") or "unknown"
    toplevel = resolve_toplevel(cwd)
    if toplevel is None:
        return None  # not a git repo here: clean no-op, advisory surfaces fail open
    return snapshot(toplevel, session_id, "precompact")


def _tick_counter_path(session_id):
    safe = _safe_ref_component(session_id)
    return os.path.join(TEL_DIR, ".autosave-tick-%s" % safe)


def cmd_tick():
    """PostToolUse hook target, opt-in via BROTHERMODE_AUTOSAVE: snapshot
    every N tool calls, and warn once on a runaway session."""
    if not os.environ.get("BROTHERMODE_AUTOSAVE"):
        return
    payload = _read_hook_payload()
    cwd = payload.get("cwd") or os.getcwd()
    session_id = payload.get("session_id") or "unknown"
    toplevel = resolve_toplevel(cwd)
    if toplevel is None:
        return
    every = _parse_int_env("BROTHERMODE_AUTOSAVE_EVERY", DEFAULT_TICK_EVERY)
    runaway_at = _parse_int_env("BROTHERMODE_RUNAWAY_AT", DEFAULT_RUNAWAY_AT)

    ctr_path = _tick_counter_path(session_id)
    try:
        os.makedirs(TEL_DIR, exist_ok=True)
    except OSError:
        pass
    try:
        with open(ctr_path, "r") as f:
            n = int((f.read() or "0").strip())
    except (OSError, ValueError):
        n = 0
    n += 1
    try:
        with open(ctr_path, "w") as f:
            f.write(str(n))
    except OSError:
        pass

    if n % every == 0:
        snapshot(toplevel, session_id, "tick %d" % n)

    if n >= runaway_at:
        warned_path = ctr_path + ".warned"
        if not os.path.exists(warned_path):
            try:
                open(warned_path, "w").close()
            except OSError:
                pass
            try:
                sys.stdout.write(json.dumps({
                    "systemMessage":
                        "BrotherMode: this session has made %d tool calls, which can "
                        "signal an unbounded loop. Run `python3 %s recover` to see "
                        "what is autosaved." % (n, os.path.abspath(__file__))
                }) + "\n")
            except Exception:
                pass


def cmd_recover(argv):
    """Print exactly how to get saved work back, and DO it: create a NEW
    git worktree at a temporary path checked out at the latest snapshot,
    and print its location. Never writes into the live working tree
    (requirement 6): the old in-place `git restore --worktree .` path,
    which could delete a tracked file the snapshot never captured (FC), is
    gone, not merely warned about."""
    start = argv[0] if argv else os.getcwd()
    toplevel = resolve_toplevel(start)
    if toplevel is None:
        print("bm_autosave: %s is not inside a git repository" % start)
        return
    worktree_id = worktree_id_for(toplevel)
    ref = latest_ref(worktree_id)
    r = _run_git(toplevel, "rev-parse", "-q", "--verify", ref)
    sha = r.stdout.strip() if r.returncode == 0 else ""
    if not sha:
        print("bm_autosave: no autosave found for %s (ref %s is empty)." % (toplevel, ref))
        return
    tmp_dir = tempfile.mkdtemp(prefix="bm-autosave-recover-")
    try:
        os.rmdir(tmp_dir)  # `git worktree add` wants a path that does not exist yet
    except OSError:
        pass
    wt = _run_git(toplevel, "worktree", "add", "--detach", tmp_dir, sha)
    if wt.returncode != 0:
        print("bm_autosave: could not create a recovery worktree (%s)"
              % (wt.stderr or "").strip())
        return
    print("bm_autosave: recovered snapshot %s into a NEW worktree at:" % sha)
    print("  %s" % tmp_dir)
    print("  Your live working tree at %s was never touched. Inspect the folder "
          "above, copy back what you need, then run" % toplevel)
    print("  `git -C %s worktree remove %s` when you are done with it."
          % (toplevel, tmp_dir))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    mode = argv[0] if argv else ""
    try:
        if mode == "precompact":
            cmd_precompact()
        elif mode == "tick":
            cmd_tick()
        elif mode == "recover":
            cmd_recover(argv[1:])
        else:
            print("usage: bm_autosave.py {precompact|tick|recover [repo]}")
    except Exception as e:
        # The absolute backstop (requirement 10): nothing this module does
        # is allowed to block a session, so even a bug here is swallowed and
        # reported, never raised.
        _warn("swallowed error (never blocks): %r" % (e,))
    sys.exit(0)


if __name__ == "__main__":
    main()
