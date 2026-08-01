#!/usr/bin/env python3
"""BrotherMode Bash-write DETECTION hook (Loop 6 design D-1): the honest
answer to the one gap docs/HOOKS.md has stated for months and never closed.

WHY THIS EXISTS
  tools/bm_fence_hook.py enforces one writer per file for Edit, Write,
  MultiEdit and NotebookEdit, and it says so itself: Bash is deliberately
  absent from WRITE_TOOLS, because no reliable parse of arbitrary shell
  exists and pretending to gate it would be a guarantee that file cannot
  keep. A shell redirect, `sed -i`, `tee`, or a script invoked through Bash
  can still cross a fence, invisibly, and until this file nothing noticed.

  Gating Bash is not on the table (it would need a PreToolUse payload that
  names the files a command will touch, which the harness does not provide,
  or an OS-level write mediator, which is outside "Python 3.9, standard
  library only"). What IS achievable without either of those: notice AFTER
  the fact. This file is a PreToolUse/PostToolUse PAIR, both wired to the
  same `Bash` matcher, that snapshots every fenced file before a Bash call
  and re-hashes it after. When a fenced file changed and the session that
  ran the Bash call is not that fence's owner, it raises a real alert row
  through the service layer and prints one plain sentence to stderr. That
  is detection, not prevention: the write already happened. Docs/HOOKS.md
  and docs/KNOWN-LIMITS.md say so in as many words, because a reader who
  believes this closes the Bash gap has been misled.

THE RULES THIS FILE OBEYS (same three bm_fence_hook.py states, plus one)
  1. FAIL OPEN, LOUDLY. Nothing here ever blocks a Bash call: both
     entrypoints below always return 0, whatever went wrong. A hook that
     failed closed on its own bug would brick every shell command the
     founder runs. Every failure path prints its reason to stderr, same
     policy as bm_fence_hook.py's own stated one.
  2. STDOUT IS RESERVED. A PreToolUse hook's stdout is the permission
     decision channel; this hook never has a decision to make, so it never
     writes to stdout at all, on either entrypoint, so a future reader
     cannot mistake output here for something Claude Code will parse.
     Every diagnostic, including the one required sentence naming a breach,
     goes to stderr.
  3. CANONICAL PATHS AND IDENTITY, SHARED WITH THE FENCE HOOK, NOT
     REIMPLEMENTED. This file loads tools/bm_fence_hook.py by path (the same
     importlib-by-path technique bm_fence_hook.py itself uses for
     tools/bm_store.py) and calls its own `active_claims` and
     `session_label`, so "which paths are fenced" and "does this session own
     that fence" can never drift from what the PreToolUse fence hook already
     enforces for Edit/Write/MultiEdit/NotebookEdit. The store itself is
     never opened directly by sqlite3 here for the READ half either: it goes
     through tools/bm_store.py exactly the way bm_fence_hook.py resolves it
     (ReadOnlyStore, inside active_claims). Only the WRITE half (raising the
     alert) opens a writable Store, because ReadOnlyStore has no path to
     raise_alert by construction.
  4. CONSENT-GATED, MIRRORING tools/bm_autosave.py. Pre-consent, both
     entrypoints check first, before reading stdin, before touching the
     filesystem, and print one sentence naming `scripts/setup.py`. Nothing
     is written, not a snapshot file, not an alert row.

WHAT THIS ACTUALLY COVERS, STATED RATHER THAN IMPLIED
  A snapshot only exists for a claim path that is a REAL, EXISTING FILE at
  the moment the Bash call starts (a literal `os.path.isfile` check on the
  claim's stored path, root-relative, joined onto the project root). A
  claim on a directory or a glob-shaped path (bm_store.paths_overlap's `*`,
  `?`, `[` handling) is not expanded into the files it would cover: this
  file does not walk the tree to discover what a glob claim spans, so a new
  file created inside a claimed directory during the Bash call is invisible
  to it. That is a real, stated limitation, not a silent gap: see the "What
  this cannot see" section of docs/HOOKS.md.

Python 3.9, standard library only, cross-platform. No em or en dashes
anywhere in this file, its comments, or its output.
"""
import hashlib
import io
import json
import os
import sys
import time
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Module loaders. Each by path, each independent of whatever any other
# tools/*.py file already loaded in this process, matching the rationale
# bm_fence_hook.py and bm_autosave.py both state for the same technique: a
# plain `import bm_store` would depend on whichever sys.path the caller
# happened to have, and this file is invoked by Claude Code with an
# arbitrary cwd. Every loader is deferred into a function and never raises:
# an unimportable module is a fail-OPEN condition, printed, not a crash in
# front of every Bash call.
# ---------------------------------------------------------------------------
_BS = None
_BS_ERROR = None
_FH = None
_FH_ERROR = None


def _load_store_module():
    global _BS, _BS_ERROR
    if _BS is not None or _BS_ERROR is not None:
        return _BS
    try:
        import importlib.util
        path = os.path.join(HERE, "bm_store.py")
        spec = importlib.util.spec_from_file_location("bm_store", path)
        if spec is None or spec.loader is None:
            _BS_ERROR = "no import spec for %s" % path
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sys.modules.setdefault("bm_store", mod)
        _BS = mod
        return _BS
    except Exception as e:
        _BS_ERROR = "%s: %s" % (type(e).__name__, e)
        return None


def _load_fence_hook_module():
    """Loads tools/bm_fence_hook.py by path. This file OWNS no logic for
    "which paths are fenced" or "who owns them": it reuses the already
    tested `active_claims` and `session_label` from the fence hook itself,
    the same way bm_autosave.py reuses tools/bm_store.py rather than
    restating its schema."""
    global _FH, _FH_ERROR
    if _FH is not None or _FH_ERROR is not None:
        return _FH
    try:
        import importlib.util
        path = os.path.join(HERE, "bm_fence_hook.py")
        spec = importlib.util.spec_from_file_location("bm_fence_hook", path)
        if spec is None or spec.loader is None:
            _FH_ERROR = "no import spec for %s" % path
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sys.modules.setdefault("bm_fence_hook", mod)
        _FH = mod
        return _FH
    except Exception as e:
        _FH_ERROR = "%s: %s" % (type(e).__name__, e)
        return None


# ---------------------------------------------------------------------------
# Consent gate (mirrors tools/bm_autosave.py's exactly: same technique, same
# schema, same fail-CLOSED-on-any-error direction, same env override). A
# second, independent copy on purpose, matching how bm_autosave.py itself
# duplicates rather than imports tools/bm_telemetry.py's own _consented:
# each write-capable entry point owns its own gate rather than trusting a
# shared import to still be gating tomorrow.
# ---------------------------------------------------------------------------
_bm_setup_cache = []


def _load_bm_setup():
    try:
        import importlib.util
        root = os.path.dirname(HERE)
        spec = importlib.util.spec_from_file_location(
            "bm_setup_for_bash_audit", os.path.join(root, "scripts", "setup.py"))
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _get_bm_setup():
    if not _bm_setup_cache:
        _bm_setup_cache.append(_load_bm_setup())
    return _bm_setup_cache[0]


def _consented():
    """True only when scripts/setup.py's own is_consented() says so. Fails
    CLOSED (not consented) on any load error, missing config, or a corrupt
    one."""
    mod = _get_bm_setup()
    if mod is None:
        return False
    try:
        cfg, _err = mod.read_config()
        return bool(mod.is_consented(cfg))
    except Exception:
        return False


_CONSENT_REQUIRED_LINE = (
    "bm_bash_audit: setup is not complete yet; run: python3 scripts/setup.py")


# ---------------------------------------------------------------------------
# Output funnel. ONE, on purpose (rule 2 above): stderr only. There is no
# _out() here, unlike bm_fence_hook.py, because this file never has a
# decision to emit.
# ---------------------------------------------------------------------------

def _warn(s):
    try:
        sys.stderr.write(s if s.endswith("\n") else s + "\n")
        sys.stderr.flush()
    except Exception:
        pass


class _FailOpen(Exception):
    """Raised anywhere this file cannot proceed SAFELY. Always caught at the
    top of each entrypoint; always produces a printed reason and exit 0."""


def _read_stdin_json():
    try:
        raw = sys.stdin.read()
    except Exception as e:
        return None, "stdin could not be read (%s: %s)" % (type(e).__name__, e)
    if not raw or not raw.strip():
        return None, "stdin was empty"
    try:
        return json.loads(raw), None
    except Exception as e:
        return None, "stdin was not valid JSON (%s: %s)" % (type(e).__name__, e)


# ---------------------------------------------------------------------------
# Snapshot storage. Lives beside the fence token directory, inside the same
# .brothermode container the store and the fence hook already use, so it
# inherits whatever gitignore and containment treatment that directory has.
# ---------------------------------------------------------------------------
SNAPSHOT_DIRNAME = "bash-audit"
_SLOT_DOMAIN = "bm-bash-audit-slot-v1|"

# A4 (loop6 refuter finding): a snapshot written at PreToolUse is normally
# removed once its matching PostToolUse comparison finishes (see
# _run_post). When that PostToolUse never runs at all -- the Bash call was
# denied before it started, the hook itself timed out, or the session was
# killed mid-call -- the snapshot is orphaned: nothing else ever cleans it
# up, and each one holds paths plus sha256 digests of every file that was
# fenced at that moment, unbounded, forever. 24 hours is the TTL: long
# enough that no snapshot from an in-progress session is ever mistaken for
# an orphan (a PostToolUse fires seconds after its PreToolUse, not hours
# later), short enough that a crashed session's leftovers do not linger.
SNAPSHOT_TTL_SECONDS = 24 * 60 * 60

ALERT_PROJECT_ID = "brothermode-bash-audit"
ALERT_SEVERITY = "high"
ALERT_CATEGORY = "fence-breach"


def _sha256_hex(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def snapshot_dir(root, bs):
    store_dirname = bs.STORE_DIRNAME if bs is not None else ".brothermode"
    return os.path.join(root, store_dirname, SNAPSHOT_DIRNAME)


def snapshot_slot(session_id, tool_use_id):
    """The snapshot FILENAME's stem, keyed on both the session and the exact
    tool call: two Bash calls in the same session must never share a
    snapshot, or the second call's PostToolUse would compare against the
    wrong baseline (or none, if the first call already deleted it)."""
    return _sha256_hex(_SLOT_DOMAIN + session_id + "|" + (tool_use_id or ""))[:32]


def snapshot_path(root, bs, session_id, tool_use_id):
    return os.path.join(snapshot_dir(root, bs),
                        snapshot_slot(session_id, tool_use_id) + ".json")


def _sha256_file(path):
    """Chunked, so a large fenced file is never read whole into memory."""
    h = hashlib.sha256()
    with io.open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_json_atomic(bs, path, obj):
    """The one write primitive this file uses for the snapshot: a temp file
    beside the target, tightened to 0600, then os.replace, mirroring
    tools/bm_autosave.py's _write_text_atomic exactly (same shape, same
    reason: a reader must never see a half-written snapshot)."""
    tmp = "%s.tmp-%d" % (path, os.getpid())
    text = json.dumps(obj)
    with io.open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    if bs is not None:
        bs._chmod_best_effort(tmp, 0o600)
    os.replace(tmp, path)


def _ensure_snapshot_dir(root, bs):
    d = snapshot_dir(root, bs)
    if not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
        if bs is not None:
            bs._chmod_best_effort(d, 0o700)
        else:
            try:
                os.chmod(d, 0o700)
            except OSError:
                pass
    if bs is not None:
        bs._refuse_if_symlink_escape(d)
    return d


def _reap_stale_snapshots(root, bs):
    """A4 (loop6 refuter finding): best-effort age-based cleanup for
    orphaned snapshot files, run at the START of every pre phase (see
    _run_pre). Removes any *.json file under the snapshot directory whose
    own mtime is older than SNAPSHOT_TTL_SECONDS (24 hours). Never raises
    and never blocks the pre phase's own work: a single unreadable or
    unremovable entry, or a directory that cannot be listed at all, is
    skipped rather than fatal, because this is housekeeping, not part of
    the snapshot-and-compare contract this file exists for."""
    try:
        d = snapshot_dir(root, bs)
        if not os.path.isdir(d):
            return
        cutoff = time.time() - SNAPSHOT_TTL_SECONDS
        for name in os.listdir(d):
            if not name.endswith(".json"):
                continue
            p = os.path.join(d, name)
            try:
                if os.path.isfile(p) and os.stat(p).st_mtime < cutoff:
                    os.remove(p)
            except OSError:
                continue
    except Exception:
        pass


def _entry_for_claim(root, rel_path, row):
    """(path, size, mtime, sha256, owner metadata) for ONE claimed path, or
    None when that path is not a real, readable file right now (a directory
    or glob-shaped claim, or a claim on a path that does not exist yet).
    Never raises: a file this process cannot read is simply not snapshotted,
    the same best-effort posture tools/bm_autosave.py takes on its own
    per-path reads."""
    if not isinstance(rel_path, str) or not rel_path.strip():
        return None
    abs_path = os.path.join(root, rel_path.replace("/", os.sep))
    try:
        if not os.path.isfile(abs_path):
            return None
        st = os.stat(abs_path)
        sha = _sha256_file(abs_path)
    except OSError:
        return None
    return {
        "path": rel_path,
        "size": st.st_size,
        "mtime": st.st_mtime,
        "sha256": sha,
        "owner_session_id": row.get("session_id") or "",
        "record_name": row.get("name") or "",
        "lifecycle_uuid": row.get("lifecycle_uuid") or "",
    }


def _remove_snapshot_best_effort(path):
    """Delete a snapshot file whose job is finished. Never raises: an
    unreadable filesystem here must not turn a successful comparison into a
    reported failure. Called ONLY after a comparison completes, per A3
    (see _run_post): never from an early-return or a _FailOpen path, or a
    retry would have nothing left to compare against."""
    try:
        os.remove(path)
    except OSError:
        pass


def _load_snapshot(path):
    """The saved snapshot, or raise _FailOpen naming why it could not be
    used. Both "missing" and "corrupt" land here, on purpose: a caller that
    cannot verify a baseline must fail open exactly the same way whichever
    of the two happened, per D-4(e)."""
    if not os.path.isfile(path):
        raise _FailOpen("no snapshot was recorded for this session and Bash "
                        "call (%s); nothing to compare against" % path)
    try:
        with io.open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise _FailOpen("the snapshot at %s could not be read (%s: %s)"
                        % (path, type(e).__name__, e))
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        raise _FailOpen("the snapshot at %s is not shaped as expected" % path)
    return data


# ---------------------------------------------------------------------------
# The breach message. Every field that could carry founder-typed free text
# (a record's name is typed by whoever claimed it) is run through the SAME
# export-policy functions tools/bm_store.py's own export path uses
# (redact_text, then mask_absolute_paths), so a fake secret or an absolute
# path typed into a record's name cannot land in the alert unmasked. The
# claimed path itself is already root-relative by construction (bm_store
# canonicalizes every claim to a root-relative POSIX string before it is
# stored), so masking it is a defensive no-op in the ordinary case rather
# than a load-bearing one, and it is still run through the same funnel
# rather than assumed safe.
# ---------------------------------------------------------------------------

def _breach_message(bs, rel_path, entry, offending_session_id):
    safe_path = bs.mask_absolute_paths(bs.redact_text(rel_path))
    safe_name = bs.mask_absolute_paths(
        bs.redact_text(entry.get("record_name") or "(unnamed record)"))
    return (
        "a Bash command run by session %s changed %s, which is inside the "
        "active fence %r (lifecycle %s), and that session is not the "
        "fence's owner. The fence hook cannot see Bash writes; this is the "
        "after-the-fact detection for one."
        % (offending_session_id, safe_path, safe_name,
           entry.get("lifecycle_uuid") or "(unknown)"))


def _raise_breach_alert(bs, root, rel_path, entry, offending_session_id):
    """Open a writable Store, raise ONE alert row, close it. Never called
    pre-consent (both entrypoints gate before this is reachable) and never
    called for the fence's own owner (the caller filters that first)."""
    message = _breach_message(bs, rel_path, entry, offending_session_id)
    alert = {
        "alert_id": uuid.uuid4().hex,
        "severity": ALERT_SEVERITY,
        "category": ALERT_CATEGORY,
        "message": message,
        "why_it_matters": (
            "one writer per file is BrotherMode's headline promise, and a "
            "Bash write bypasses the PreToolUse fence entirely, so this is "
            "the only place that promise can still be checked for a "
            "command run outside Edit, Write, MultiEdit or NotebookEdit."),
        "recommended_action": (
            "review the change to the path named above, confirm it was "
            "intended, and if the fence should move, adopt it deliberately "
            "with `bm_store.py adopt ... --adopt-from-live-session` rather "
            "than leaving it crossed silently."),
        "requires_human": True,
        "created_at": bs.now_iso(),
        "resolved_at": None,
    }
    actor = {
        "actor_type": "hook",
        "actor_name": "bm_bash_audit",
        "session_id": offending_session_id,
    }
    store = bs.Store(root, create=False)
    try:
        store.raise_alert(alert, ALERT_PROJECT_ID, actor)
    finally:
        store.close()
    safe_path = bs.mask_absolute_paths(bs.redact_text(rel_path))
    _warn("bm_bash_audit: a Bash write outside its fence changed %s; a "
         "high-severity fence-breach alert was raised and needs a human."
         % safe_path)


# ---------------------------------------------------------------------------
# PreToolUse: snapshot every fenced, currently-existing file.
# ---------------------------------------------------------------------------

def _run_pre(payload):
    if not isinstance(payload, dict):
        raise _FailOpen("hook payload was not a JSON object")
    tool_name = payload.get("tool_name")
    if not isinstance(tool_name, str) or tool_name != "Bash":
        return  # matcher already restricts this; defensive re-check only
    session_id = payload.get("session_id")
    if not isinstance(session_id, str) or not session_id.strip():
        raise _FailOpen("hook payload carried no session_id")
    session_id = session_id.strip()
    tool_use_id = payload.get("tool_use_id")
    tool_use_id = tool_use_id.strip() if isinstance(tool_use_id, str) else ""

    bs = _load_store_module()
    if bs is None:
        raise _FailOpen("bm_store.py could not be imported (%s)" % _BS_ERROR)
    fh = _load_fence_hook_module()
    if fh is None:
        raise _FailOpen("bm_fence_hook.py could not be imported (%s)" % _FH_ERROR)

    cwd = payload.get("cwd")
    cwd = cwd if isinstance(cwd, str) and cwd.strip() else None
    root, _source = bs.resolve_root(cwd)
    if root is None:
        raise _FailOpen("no BrotherMode project root found from %s"
                        % (cwd or os.getcwd()))

    # A4: reap anything orphaned from an earlier call before doing this
    # call's own work. Best effort, never fatal to this pre phase.
    _reap_stale_snapshots(root, bs)

    if not os.path.isfile(bs.store_path(root)):
        raise _FailOpen("no store at %s; nothing to snapshot" % bs.store_path(root))

    try:
        rows = fh.active_claims(root)
    except Exception as e:
        raise _FailOpen("could not read active claims (%s: %s)"
                        % (type(e).__name__, e))
    if not rows:
        raise _FailOpen("the store holds no active claims; nothing is fenced")

    entries = []
    for row in rows:
        e = _entry_for_claim(root, row.get("path"), row)
        if e is not None:
            entries.append(e)
    if not entries:
        raise _FailOpen("no active claim resolved to an existing file")

    snapshot = {
        "schema": 1,
        "session_id": session_id,
        "tool_use_id": tool_use_id,
        "root": root,
        "created_at": bs.now_iso(),
        "entries": entries,
    }
    _ensure_snapshot_dir(root, bs)
    spath = snapshot_path(root, bs, session_id, tool_use_id)
    if bs is not None:
        bs._refuse_if_symlink_escape(spath)
    _write_json_atomic(bs, spath, snapshot)


def cmd_pre(argv):
    if not _consented():
        _warn(_CONSENT_REQUIRED_LINE)
        return 0
    payload, err = _read_stdin_json()
    try:
        if err is not None:
            raise _FailOpen(err)
        _run_pre(payload)
    except _FailOpen as e:
        _warn("bm_bash_audit: FAILING OPEN before the Bash call, nothing "
             "was snapshotted. Reason: %s" % e)
    except Exception as e:
        _warn("bm_bash_audit: FAILING OPEN before the Bash call after an "
             "unexpected error, nothing was snapshotted. Reason: %s: %s"
             % (type(e).__name__, e))
    return 0


# ---------------------------------------------------------------------------
# PostToolUse: re-hash the snapshot, raise an alert for every fenced path a
# non-owning session changed.
# ---------------------------------------------------------------------------

def _run_post(payload):
    if not isinstance(payload, dict):
        raise _FailOpen("hook payload was not a JSON object")
    tool_name = payload.get("tool_name")
    if not isinstance(tool_name, str) or tool_name != "Bash":
        return
    session_id = payload.get("session_id")
    if not isinstance(session_id, str) or not session_id.strip():
        raise _FailOpen("hook payload carried no session_id")
    session_id = session_id.strip()
    tool_use_id = payload.get("tool_use_id")
    tool_use_id = tool_use_id.strip() if isinstance(tool_use_id, str) else ""

    bs = _load_store_module()
    if bs is None:
        raise _FailOpen("bm_store.py could not be imported (%s)" % _BS_ERROR)
    fh = _load_fence_hook_module()
    if fh is None:
        raise _FailOpen("bm_fence_hook.py could not be imported (%s)" % _FH_ERROR)

    cwd = payload.get("cwd")
    cwd = cwd if isinstance(cwd, str) and cwd.strip() else None
    root, _source = bs.resolve_root(cwd)
    if root is None:
        raise _FailOpen("no BrotherMode project root found from %s"
                        % (cwd or os.getcwd()))

    spath = snapshot_path(root, bs, session_id, tool_use_id)
    snapshot = _load_snapshot(spath)

    try:
        my_label = fh.session_label(root, session_id)
    except Exception as e:
        raise _FailOpen("this session's fence label could not be derived "
                        "(%s: %s)" % (type(e).__name__, e))

    breaches = []
    for entry in snapshot.get("entries", []):
        rel_path = entry.get("path")
        if not isinstance(rel_path, str) or not rel_path.strip():
            continue
        owner = entry.get("owner_session_id") or ""
        if owner == my_label:
            continue  # the fence's own owner made this change
        abs_path = os.path.join(root, rel_path.replace("/", os.sep))
        changed = False
        try:
            if not os.path.isfile(abs_path):
                changed = True  # deleted: a content change too
            else:
                st = os.stat(abs_path)
                if st.st_size != entry.get("size"):
                    changed = True
                else:
                    changed = _sha256_file(abs_path) != entry.get("sha256")
        except OSError:
            continue  # cannot verify; best effort, not counted as a breach
        if changed:
            breaches.append((rel_path, entry))

    if not breaches:
        # A3 fix (loop6 refuter finding): the snapshot is removed only once
        # the comparison it exists for has actually completed. This used to
        # be removed unconditionally right after _load_snapshot, BEFORE this
        # store-existence check below, so a post phase that could not reach
        # the store lost its baseline with no way to retry. Every early
        # return and every raised _FailOpen above and below this point must
        # leave the snapshot exactly where it was.
        _remove_snapshot_best_effort(spath)
        return

    if not os.path.isfile(bs.store_path(root)):
        raise _FailOpen("no store at %s; %d breach(es) found but could not "
                        "be recorded" % (bs.store_path(root), len(breaches)))
    for rel_path, entry in breaches:
        _raise_breach_alert(bs, root, rel_path, entry, session_id)
    # Every breach was recorded successfully: this snapshot's job is done.
    _remove_snapshot_best_effort(spath)


def cmd_post(argv):
    if not _consented():
        _warn(_CONSENT_REQUIRED_LINE)
        return 0
    payload, err = _read_stdin_json()
    try:
        if err is not None:
            raise _FailOpen(err)
        _run_post(payload)
    except _FailOpen as e:
        _warn("bm_bash_audit: FAILING OPEN after the Bash call, no fenced "
             "path could be checked. Reason: %s" % e)
    except Exception as e:
        _warn("bm_bash_audit: FAILING OPEN after the Bash call after an "
             "unexpected error, no fenced path could be checked. "
             "Reason: %s: %s" % (type(e).__name__, e))
    return 0


_COMMANDS = {
    "pre": cmd_pre,
    "post": cmd_post,
}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in _COMMANDS:
        return _COMMANDS[argv[0]](argv[1:])
    _warn("bm_bash_audit: usage: bm_bash_audit.py pre|post (invoked as a "
         "PreToolUse/PostToolUse hook with a JSON payload on stdin)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
