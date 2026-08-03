#!/usr/bin/env python3
"""BrotherMode PreToolUse fence hook: the point where "one writer per file"
stops being a ledger entry and becomes an enforcement boundary.

WHY THIS EXISTS (audit finding 8, confirmed by execution)
  BrotherMode's headline promise is that one record owns a set of paths and
  nobody else writes them. Until this file, that promise was recorded and
  never checked: bm_store.py refuses a second CLAIM that overlaps an active
  fence, but nothing sat between an agent and an actual file write. So an
  agent could edit before claiming, claim an incomplete path set and edit
  the rest, edit a path another record owned, or skip BrotherMode entirely.
  The installed hooks were SessionStart, SessionEnd, Stop and PreCompact:
  none of them can refuse anything, because all of them run after or beside
  the write, never in front of it.

  Claude Code's PreToolUse hook is the mechanism that closes this. It
  receives the tool name and its input as JSON on stdin and may return a
  deny decision that stops the call before the tool runs. Contract read from
  https://code.claude.com/docs/en/hooks on 2026-07-27; the exact stdin
  fields and the exact deny shape this file emits are quoted in
  docs/HOOKS.md, which is the document to update if that contract moves.

THE THREE RULES THIS FILE OBEYS
  1. FAIL OPEN, LOUDLY. This hook sits in front of every edit the founder
     makes. A hook that failed closed on its own bug would brick editing
     entirely, so every failure path here (no root, no store, unreadable
     store, corrupt store, unparseable payload, zero claims, any unexpected
     exception) allows the write and prints the reason to stderr. A refusal
     must always come from a real ownership conflict, never from this file
     being broken.
  2. STDOUT IS THE DECISION CHANNEL AND NOTHING ELSE. Claude Code parses
     stdout as JSON. Every diagnostic goes to stderr. That is why this file
     has exactly two output funnels (_out, _warn) and no bare print.
  3. CANONICAL PATHS ONLY. A comparison between unresolved path strings is
     bypassed by '..', by a symlink, by a relative path typed from a
     subdirectory, or by case on a case-insensitive filesystem. Every target
     path is realpath'd and expressed root-relative before it is compared,
     and the comparison itself is bm_store.paths_overlap, the same function
     the store uses to admit a claim, so the fence the hook enforces and the
     fence the store granted can never drift apart.

IDENTITY (audit finding 8B)
  See docs/HOOKS.md for the full statement including the residual limit. In
  short: a session's secret token lives in an owner-only file inside
  .brothermode and is never printed anywhere; the PUBLIC session label that
  STATE.md shows is a one-way hash of that token. Ownership is
  record.session_id == hash(my token). Reading the public label out of
  STATE.md and passing it as your own session therefore buys nothing: the
  hook derives your label from the token you can actually open, not from the
  string you claim to be.

Python 3.9, standard library only, cross-platform. No em or en dashes
anywhere in this file, its comments, or its output.
"""
import hashlib
import io
import json
import os
import posixpath
import secrets
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# Loaded by path rather than by package import: tools/ is not a package, and
# the hook is invoked by Claude Code with an arbitrary cwd, so a plain
# `import bm_store` would resolve against sys.path and could pick up a
# different checkout. Deferred into a function so an import failure is a
# FAIL-OPEN, printed to stderr, rather than a traceback that Claude Code
# would surface as a broken hook in front of every edit.
_BS = None
_BS_ERROR = None


def _load_store_module():
    """Import tools/bm_store.py beside this file, or return None and record
    why. Never raises: an unimportable store is a fail-open condition."""
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


# ---------------------------------------------------------------------------
# Output funnels. Two of them, on purpose (same discipline bm_store.py
# enforces structurally): stdout carries the decision JSON and nothing else,
# stderr carries every diagnostic. Anything printed to stdout that is not the
# decision object corrupts the hook protocol.
# ---------------------------------------------------------------------------

def _out(s):
    sys.stdout.write(s)
    sys.stdout.flush()


def _warn(s):
    sys.stderr.write(s if s.endswith("\n") else s + "\n")
    sys.stderr.flush()


# ---------------------------------------------------------------------------
# The tool surface this hook governs.
# ---------------------------------------------------------------------------

#: Tools that write a file through a structured, parseable path argument.
#: Bash is DELIBERATELY ABSENT: a shell command can write any file, and no
#: reliable parse of arbitrary shell exists, so pretending to gate it would
#: be a guarantee this file cannot keep (stated as a known gap in
#: docs/HOOKS.md rather than papered over here).
WRITE_TOOLS = frozenset((
    "Edit",
    "Write",
    "MultiEdit",
    "NotebookEdit",
    "CreateDirectory",
    "Delete",
))

#: Keys inside tool_input that carry a filesystem path. Collected across the
#: built-in write tools listed in the hooks documentation. Unknown keys are
#: ignored; an unknown WRITE tool that carries none of these keys produces
#: zero targets, which is a fail-open (see decide()), not a silent allow.
PATH_KEYS = ("file_path", "notebook_path", "path", "filePath", "target_file")

FENCE_DIRNAME = "fence"
TOKEN_SUFFIX = ".token"
LABEL_PREFIX = "bm1-"
_SLOT_DOMAIN = "bm-fence-slot-v1|"
_LABEL_DOMAIN = "bm-fence-label-v1|"
_TOKEN_BYTES = 32
_LABEL_HEX = 24


# ---------------------------------------------------------------------------
# Session identity.
# ---------------------------------------------------------------------------

def _sha256_hex(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def fence_dir(root):
    """Beside the store, inside the same .brothermode directory, so the
    token inherits whatever containment and gitignore treatment the store
    already has. The directory name comes from bm_store.STORE_DIRNAME rather
    than a second literal: one of the two would eventually be changed alone."""
    bs = _load_store_module()
    store_dirname = bs.STORE_DIRNAME if bs is not None else ".brothermode"
    return os.path.join(root, store_dirname, FENCE_DIRNAME)


def token_slot(session_id):
    """The FILENAME a session's token lives under, derived from the harness
    session id. Derived rather than stored so two concurrent sessions never
    race over one file, and hashed rather than used literally so a session id
    containing a path separator or a reserved Windows character cannot escape
    the fence directory."""
    return _sha256_hex(_SLOT_DOMAIN + session_id)[:32]


def token_path(root, session_id):
    return os.path.join(fence_dir(root), token_slot(session_id) + TOKEN_SUFFIX)


def label_for_token(token):
    """The PUBLIC session label: a one-way hash of the secret token.

    This is the whole identity design in one line. The label is safe to print
    into STATE.md, safe to paste into a thread file, safe to read out of any
    generated view, because deriving the token from it would require
    inverting SHA-256. And an ownership check compares the label ON THE
    RECORD against the label DERIVED FROM THE TOKEN THIS PROCESS COULD OPEN,
    so copying a label out of STATE.md and presenting it as your own session
    id gains nothing: the hook never takes your word for which label is
    yours, it computes it."""
    return LABEL_PREFIX + _sha256_hex(_LABEL_DOMAIN + token)[:_LABEL_HEX]


def _valid_token_text(t):
    if not isinstance(t, str):
        return False
    t = t.strip()
    if len(t) != _TOKEN_BYTES * 2:
        return False
    try:
        int(t, 16)
    except ValueError:
        return False
    return True


def ensure_token(root, session_id):
    """Return this session's secret token, creating it on first use.

    Created with O_CREAT|O_EXCL at mode 0600 inside a 0700 directory, so two
    processes that somehow share a session id cannot both write it and the
    loser simply reads the winner's file. The 0600 is a real guarantee on
    POSIX and a courtesy on Windows, where os.chmod can only toggle the
    read-only bit and the actual protection is the ACL the directory
    inherits; that difference is stated in docs/HOOKS.md rather than glossed,
    because a permission claim the platform will not keep is worse than none.

    Raises on any filesystem failure. Every caller treats that as fail-open.
    """
    bs = _load_store_module()
    d = fence_dir(root)
    if not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
        if bs is not None:
            bs._chmod_best_effort(d, 0o700)
        else:
            try:
                os.chmod(d, 0o700)
            except OSError:
                pass
    p = token_path(root, session_id)
    # Same containment rule bm_store applies to the store file itself: refuse
    # to follow a symlink that would put a secret outside the project root,
    # or let an attacker point the token file at a file they can read.
    if bs is not None:
        bs._refuse_if_symlink_escape(d)
        bs._refuse_if_symlink_escape(p)
    elif os.path.lexists(p) and os.path.realpath(p) != p:
        raise OSError("token path %s is a symlink resolving to %s"
                      % (p, os.path.realpath(p)))
    if os.path.exists(p):
        with io.open(p, "r", encoding="utf-8") as f:
            existing = f.read()
        if _valid_token_text(existing):
            return existing.strip()
        raise ValueError("token file %s does not hold a %d-character hex token"
                         % (p, _TOKEN_BYTES * 2))
    token = secrets.token_hex(_TOKEN_BYTES)
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    try:
        fd = os.open(p, flags, 0o600)
    except FileExistsError:
        # Lost the create race. The winner's token is the session's token.
        with io.open(p, "r", encoding="utf-8") as f:
            existing = f.read()
        if _valid_token_text(existing):
            return existing.strip()
        raise ValueError("token file %s does not hold a %d-character hex token"
                         % (p, _TOKEN_BYTES * 2))
    try:
        with io.open(fd, "w", encoding="utf-8", closefd=True) as f:
            f.write(token + "\n")
    except Exception:
        try:
            os.close(fd)
        except Exception:
            pass
        raise
    if bs is not None:
        bs._chmod_best_effort(p, 0o600)
    return token


def session_label(root, session_id):
    """The public label for a session, materializing its token if needed."""
    return label_for_token(ensure_token(root, session_id))


# ---------------------------------------------------------------------------
# Path canonicalization.
# ---------------------------------------------------------------------------

def canonical_target(root, raw, cwd=None):
    """A tool's target path as a root-relative POSIX string, symlinks
    resolved, or None when it falls outside the project root.

    Deliberately mirrors bm_store._resolve_against_root rather than calling
    bm_store.canonicalize_path: that function treats '*', '?' and '[' as
    wildcard segments, which is correct for a DECLARED CLAIM and wrong for a
    CONCRETE FILE a tool is about to write. os.path.realpath resolves
    symlinks in whatever prefix of the path already exists and leaves a
    nonexistent trailing component literal, so this works identically for
    Edit on an existing file and Write creating a new one.

    None means "not this project's business" (a different drive, a path
    above the root, an unusable string) and every caller treats that as
    allow: BrotherMode fences a project, not the filesystem."""
    if not isinstance(raw, str) or not raw.strip():
        return None
    root_real = os.path.realpath(root)
    base_dir = cwd if cwd else root_real
    try:
        if os.path.isabs(raw):
            base = raw
        else:
            base = os.path.join(base_dir, raw)
        abs_real = os.path.realpath(base)
        rel = os.path.relpath(abs_real, root_real)
    except (ValueError, OSError):
        # Windows raises ValueError from relpath across drives, which is
        # definitionally outside the root.
        return None
    rel_posix = rel.replace(os.sep, "/")
    if rel_posix == ".." or rel_posix.startswith("../"):
        return None
    rel_posix = posixpath.normpath(rel_posix)
    return rel_posix


def extract_targets(tool_input):
    """Every path a write tool's input names, in input order, de-duplicated.

    Walks nested lists of dicts too, so a MultiEdit-shaped payload whose
    per-edit entries carry their own file_path is not silently reduced to the
    top-level path. Bounded depth: a hook that recursed without limit on a
    hostile payload would hang in front of every edit."""
    out = []
    seen = set()

    def visit(node, depth):
        if depth > 6:
            return
        if isinstance(node, dict):
            for k in PATH_KEYS:
                v = node.get(k)
                if isinstance(v, str) and v.strip() and v not in seen:
                    seen.add(v)
                    out.append(v)
            for v in node.values():
                if isinstance(v, (dict, list)):
                    visit(v, depth + 1)
        elif isinstance(node, list):
            for v in node[:64]:
                visit(v, depth + 1)

    visit(tool_input, 0)
    return out


# ---------------------------------------------------------------------------
# Store lookup.
# ---------------------------------------------------------------------------

class _FailOpen(Exception):
    """Raised anywhere a decision cannot be made SAFELY. Caught at the top of
    decide(). In the default advisory mode it produces an allow plus a stderr
    line; in enforced mode (see enforced_mode below) it produces a DENY. A
    named exception rather than a returned sentinel so a new code path cannot
    forget to check the sentinel and accidentally deny."""


ENFORCED = "enforced"
ADVISORY = "advisory"


def enforced_mode(env=None):
    """True when the operator has opted this machine into fail-closed.

    C-01 (2026-08-03). Until now every failure path in this hook produced an
    allow, and an adversarial probe confirmed it: nine separate conditions
    (store missing, store corrupt, store zero bytes, store present with ZERO
    active claims, five shapes of malformed payload, an unrecognized path key,
    an internal exception mid-decision, bm_store.py unimportable, an
    underivable session identity) each allowed a write across another
    session's active fence, exit 0. BM_FENCE_STRICT did not help, because it
    is read AFTER every one of those raises and is a complete no-op on a
    zero-claims store, which is the state a fresh project sits in.

    Fail-open remains the DEFAULT and is unchanged, deliberately: a hook that
    starts refusing edits on a machine whose owner never asked for it is a
    worse failure than an unenforced fence, and that judgement is recorded in
    this file's own history. Enforcement is therefore opt-in, one variable,
    and it is the only thing that changes behaviour here.

    BM_FENCE_MODE is read rather than reusing BM_FENCE_STRICT because the two
    mean different things and conflating them would silently widen what
    existing users already set: STRICT tightens which PATHS are covered when
    the fence is working, while MODE decides what happens when it CANNOT work.
    """
    if env is None:
        env = os.environ
    return env.get("BM_FENCE_MODE", "").strip().lower() == ENFORCED


def active_claims(root):
    """Every (path, record) pair an ACTIVE record currently fences.

    Read-only by construction: ReadOnlyStore has no path to the code that
    quarantines or moves anything, which matters because this runs in front
    of every edit and a transient disk hiccup must never let a hook relocate
    the founder's database."""
    bs = _load_store_module()
    if bs is None:
        raise _FailOpen("bm_store.py could not be imported (%s)" % _BS_ERROR)
    path = bs.store_path(root)
    if not os.path.isfile(path):
        raise _FailOpen("no store at %s (run `python3 tools/bm_store.py init`)"
                        % path)
    try:
        store = bs.ReadOnlyStore(root)
    except Exception as e:
        raise _FailOpen("store at %s could not be opened read-only (%s: %s)"
                        % (path, type(e).__name__, e))
    try:
        rows = bs._exec(store,
            "SELECT c.path AS path, r.name AS name, "
            "r.lifecycle_uuid AS lifecycle_uuid, r.version AS version, "
            "r.session_id AS session_id "
            "FROM claims c JOIN records r ON r.lifecycle_uuid = c.lifecycle_uuid "
            "WHERE r.state='active'").fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        raise _FailOpen("store at %s could not be read (%s: %s)"
                        % (path, type(e).__name__, e))
    finally:
        store.close()


def _safe_display(text):
    """Founder-typed text on its way into a deny message, redacted the same
    way bm_store._raise_overlap redacts an overlap refusal. A record name and
    a claim path are free text and can hold a secret shape; the deny reason
    is read by the model and lands in a transcript. Best effort on purpose:
    an unavailable redactor must degrade the MESSAGE, never the REFUSAL."""
    bs = _load_store_module()
    if bs is None:
        return "(redacted: unavailable)"
    try:
        return bs._sanitize_for_display(bs.redact_text(text))
    except Exception:
        return "(redacted: unavailable)"


def _takeover_command(row, my_label):
    """The exact command that moves the fence to this session. `adopt` with
    --adopt-from-live-session is bm_store's own documented door for taking a
    record that is active under a different live session; naming anything
    else here would send the reader to a command that refuses."""
    return ("python3 tools/bm_store.py adopt %s --version %s --session %s "
            "--adopt-from-live-session"
            % (row["lifecycle_uuid"], row["version"], my_label))


# ---------------------------------------------------------------------------
# The decision.
# ---------------------------------------------------------------------------

def deny_payload(reason):
    """The deny object, shaped exactly as the PreToolUse contract requires.
    Read from https://code.claude.com/docs/en/hooks on 2026-07-27:

      {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                              "permissionDecision": "deny",
                              "permissionDecisionReason": "..."}}

    Emitted on stdout with exit code 0. Exit 2 would also block, feeding
    stderr back as the reason, but it is the wrong instrument here: exit 2
    means "the hook itself failed", and this hook reserves nonzero-shaped
    failure semantics for nothing at all, because every failure it has is a
    fail-open."""
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}


def decide(payload):
    """Return (decision_object_or_None, stderr_lines).

    None means "no decision": Claude Code applies the normal permission flow.
    That is both the ALLOW answer and the FAIL-OPEN answer, deliberately the
    same value, so no failure path can produce a deny by accident."""
    notes = []
    try:
        if not isinstance(payload, dict):
            raise _FailOpen("hook payload was not a JSON object")
        tool_name = payload.get("tool_name")
        if not isinstance(tool_name, str) or tool_name not in WRITE_TOOLS:
            # Not a file-writing tool. Silent, not loud: this is the common
            # case, and a stderr line per Read or Grep would be noise.
            return None, []
        tool_input = payload.get("tool_input")
        if not isinstance(tool_input, dict):
            raise _FailOpen("tool_input for %s was not a JSON object" % tool_name)
        session_id = payload.get("session_id")
        if not isinstance(session_id, str) or not session_id.strip():
            raise _FailOpen("hook payload carried no session_id, so this "
                            "session has no verifiable identity")
        session_id = session_id.strip()

        raw_targets = extract_targets(tool_input)
        if not raw_targets:
            raise _FailOpen("no target path found in tool_input for %s "
                            "(keys: %s)" % (tool_name, ", ".join(sorted(tool_input))))

        bs = _load_store_module()
        if bs is None:
            raise _FailOpen("bm_store.py could not be imported (%s)" % _BS_ERROR)

        cwd = payload.get("cwd")
        if not isinstance(cwd, str) or not cwd.strip():
            cwd = None
        root, _source = bs.resolve_root(cwd or None)
        if root is None:
            raise _FailOpen("no BrotherMode project root found from %s"
                            % (cwd or os.getcwd()))

        rows = active_claims(root)
        if not rows:
            raise _FailOpen("the store at %s holds no active claims, so there "
                            "is no fence to enforce" % bs.store_path(root))

        try:
            my_label = session_label(root, session_id)
        except Exception as e:
            raise _FailOpen("this session's fence token could not be read or "
                            "created (%s: %s)" % (type(e).__name__, e))

        strict = os.environ.get("BM_FENCE_STRICT", "").strip() not in ("", "0")

        for raw in raw_targets:
            rel = canonical_target(root, raw, cwd)
            if rel is None:
                # Outside the project root. BrotherMode fences a project,
                # not the machine.
                continue
            covering = [r for r in rows if bs.paths_overlap(rel, r["path"])]
            foreign = [r for r in covering if r["session_id"] != my_label]
            if foreign:
                r = foreign[0]
                reason = (
                    "BrotherMode fence: %s is inside the fence of the active "
                    "record %s (lifecycle %s, version %s), which is owned by "
                    "session %s. This session is %s, so it is not the writer "
                    "for that path. Claimed as: %s.\n"
                    "One writer per file is structural, not advisory: do not "
                    "edit across the fence. Report the needed change to the "
                    "owner instead. To take the fence over deliberately, run:\n"
                    "  %s\n"
                    "then re-claim the paths you need with `bm_store.py claim "
                    "... --session %s`."
                    % (rel, _safe_display(r["name"]), r["lifecycle_uuid"],
                       r["version"], r["session_id"] or "(none)", my_label,
                       _safe_display(r["path"]),
                       _takeover_command(r, my_label), my_label))
                return deny_payload(reason), notes
            if strict and not covering:
                reason = (
                    "BrotherMode fence (strict mode): %s is not inside any "
                    "active record's fence, and BM_FENCE_STRICT is set, so "
                    "claim-before-edit is being enforced. Claim it first:\n"
                    "  python3 tools/bm_store.py claim <name> --lifetime "
                    "ephemeral --objective '...' --files %s --session %s"
                    % (rel, rel, my_label))
                return deny_payload(reason), notes
        return None, notes
    except _FailOpen as e:
        if enforced_mode():
            notes.append(
                "bm_fence_hook: FAILING CLOSED, the write is refused because "
                "the fence could not be checked. Reason: %s" % e)
            return deny_payload(
                "BrotherMode is in enforced mode and could not check file "
                "ownership, so this write is refused rather than allowed "
                "unchecked. Reason: %s. Fix the cause, or set "
                "BM_FENCE_MODE=advisory to go back to warning only." % e), notes
        notes.append(
            "bm_fence_hook: FAILING OPEN, the write is allowed and the fence "
            "was NOT checked. Reason: %s" % e)
        return None, notes
    except Exception as e:
        # The blanket catch is the point, not laziness: an unforeseen bug in
        # this file must never become a refusal in front of the founder's
        # editing. Type and message, no traceback, so the stderr line stays
        # one readable sentence.
        #
        # In enforced mode that judgement inverts (C-01): somebody who asked
        # for fail-closed has said they would rather be stopped by a bug in
        # this hook than have it wave a write through unchecked. The message
        # still carries no traceback and no file content.
        if enforced_mode():
            notes.append(
                "bm_fence_hook: FAILING CLOSED after an unexpected error, the "
                "write is refused. Reason: %s: %s" % (type(e).__name__, e))
            return deny_payload(
                "BrotherMode is in enforced mode and this ownership check "
                "failed unexpectedly (%s), so the write is refused rather "
                "than allowed unchecked. Set BM_FENCE_MODE=advisory to go "
                "back to warning only." % type(e).__name__), notes
        notes.append(
            "bm_fence_hook: FAILING OPEN after an unexpected error, the write "
            "is allowed and the fence was NOT checked. Reason: %s: %s"
            % (type(e).__name__, e))
        return None, notes


# ---------------------------------------------------------------------------
# Entry points.
# ---------------------------------------------------------------------------

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


def cmd_hook(argv):
    payload, err = _read_stdin_json()
    if err is not None:
        _warn("bm_fence_hook: FAILING OPEN, the write is allowed and the "
              "fence was NOT checked. Reason: %s" % err)
        return 0
    decision, notes = decide(payload)
    for n in notes:
        _warn(n)
    if decision is not None:
        _out(json.dumps(decision))
    return 0


def cmd_session_label(argv):
    """Print this session's PUBLIC fence label, for use as
    `bm_store.py claim ... --session "$(bm_fence_hook.py session-label ...)"`.

    The session id comes from --session-id, then BM_FENCE_SESSION_ID, then a
    JSON payload on stdin (so this can also be wired as a SessionStart hook,
    which receives session_id in the same field). Never invents one: a made
    up session id would mint a token nobody else could reproduce and quietly
    lock the session out of its own records."""
    session_id = None
    for i, a in enumerate(argv):
        if a == "--session-id" and i + 1 < len(argv):
            session_id = argv[i + 1]
        elif a.startswith("--session-id="):
            session_id = a.split("=", 1)[1]
    if not session_id:
        session_id = os.environ.get("BM_FENCE_SESSION_ID", "")
    if not session_id and not sys.stdin.isatty():
        payload, _err = _read_stdin_json()
        if isinstance(payload, dict):
            session_id = payload.get("session_id") or ""
    session_id = (session_id or "").strip()
    if not session_id:
        _warn("bm_fence_hook: no session id. Pass --session-id X, set "
              "BM_FENCE_SESSION_ID, or feed a hook payload on stdin.")
        return 2
    bs = _load_store_module()
    if bs is None:
        _warn("bm_fence_hook: bm_store.py could not be imported (%s)" % _BS_ERROR)
        return 2
    root, _source = bs.resolve_root()
    if root is None:
        _warn("bm_fence_hook: no BrotherMode project root found from %s"
              % os.getcwd())
        return 2
    try:
        _out(session_label(root, session_id) + "\n")
    except Exception as e:
        _warn("bm_fence_hook: could not read or create this session's token "
              "(%s: %s)" % (type(e).__name__, e))
        return 2
    return 0


def cmd_whoami(argv):
    """Diagnostics on stderr, label on stdout. Prints where the token lives
    and never prints the token itself."""
    bs = _load_store_module()
    if bs is None:
        _warn("bm_store.py unimportable: %s" % _BS_ERROR)
        return 2
    root, source = bs.resolve_root()
    if root is None:
        _warn("no BrotherMode project root found from %s" % os.getcwd())
        return 2
    _warn("root: %s (via %s)" % (root, source))
    _warn("store: %s (exists: %s)"
          % (bs.store_path(root), os.path.isfile(bs.store_path(root))))
    _warn("fence dir: %s" % fence_dir(root))
    rc = cmd_session_label(argv)
    if rc == 0:
        _warn("the label above is PUBLIC and safe to paste; the token behind "
              "it is not printed by any command in this file.")
    return rc


_COMMANDS = {
    "hook": cmd_hook,
    "session-label": cmd_session_label,
    "whoami": cmd_whoami,
}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in _COMMANDS:
        return _COMMANDS[argv[0]](argv[1:])
    if argv and argv[0].startswith("-") is False:
        _warn("bm_fence_hook: unknown command %r; expected one of: %s"
              % (argv[0], ", ".join(sorted(_COMMANDS))))
        return 2
    # No subcommand is the HOOK invocation, because that is how Claude Code
    # calls it: a bare command with a JSON payload on stdin.
    return cmd_hook(argv)


if __name__ == "__main__":
    sys.exit(main())
