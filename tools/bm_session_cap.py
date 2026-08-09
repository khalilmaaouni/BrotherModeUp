#!/usr/bin/env python3
"""tools/bm_session_cap.py: the machine-wide cap on concurrent sessions.

A PreToolUse hook. It refuses ONE thing: starting another Claude Code
session when too many are already running. Everything else passes through
untouched.

WHY THIS EXISTS
  On 2026-08-08 this project's own caps were prose. SKILL.md said three
  fences per shared tree and nine agents; the machine ran fifteen sessions
  at once and forty across ten hours, spending roughly 6.4 million output
  tokens and 1.69 billion cache-read tokens while the founder was away from
  the screen. Nothing counted. Nothing could have refused.

  The lesson is narrower than "add limits". The limits already existed. The
  contract signed that morning carried a token ceiling of 3,000,000 and
  tools/bm_controller.py compares spend against it correctly, but
  autonomy_spend held zero rows all night, so the comparison read 0 against
  3,000,000 forever. A control that depends on a meter fails exactly when
  the meter is what broke. So this file measures the one thing that cannot
  be under-reported by a bookkeeping gap: how many session transcripts are
  being written to right now.

WHAT IT GATES, AND WHY ONLY THAT
  A session spawn, and nothing else. Concretely: a Bash command that runs
  `claude -p` or `claude --print`. That is the surface the 2026-08-08 relay
  used (tools/bm_continue.py's printable_command prints exactly this shape)
  and it is the one that multiplies, because each spawned session can spawn
  more. Subagents dispatched inside one session are NOT gated here: they
  die with their parent, they are the sanctioned delegation path, and a cap
  that fought normal delegation would be switched off inside a day. That is
  a deliberate scope decision, not an oversight; it is stated in
  docs/KNOWN-LIMITS.md terms right here so nobody reads this file as
  broader protection than it is.

WHAT "LIVE" MEANS, HONESTLY
  A session is counted as live when its transcript file under the Claude
  Code projects directory has been written to inside RECENCY_SECONDS. That
  is a PROXY, not a fact: a session idling longer than the window reads as
  finished, and a crashed session reads as finished only after the window
  passes. It was chosen over inspecting the process table because it needs
  no subprocess, costs one directory walk, and cannot be fooled by a
  session whose process name differs across install methods. A proxy that
  runs on every launch beats a truth that is too expensive to consult.

FAIL OPEN ON ITS OWN FAILURE, NEVER ON ITS OWN VERDICT
  If the counter cannot read the projects directory, it warns on stderr and
  ALLOWS: a brake that bricks a founder's machine when it breaks is worse
  than the fleet it was meant to stop, and the same reasoning governs
  tools/bm_fence_hook.py. It does NOT fail open when the count succeeds and
  says the cap is reached. That case is the entire point of the file.

Python 3.9, standard library only. No network, no subprocess.
"""

import json
import os
import re
import sys
import time

#: The cap itself. Four concurrent sessions: enough for a founder's own
#: session plus a relay plus one lane of parallel work, small enough that a
#: self-replicating chain meets it within minutes rather than hours. A
#: THRESHOLD MEASURED ON ONE ESTATE (this machine, 2026-08-09), not a law:
#: raise it deliberately with the environment variable below.
CAP_DEFAULT = 4

#: Environment overrides. The projects root is overridable for tests and
#: for installs that relocate it; nothing else reads it.
CAP_ENV = "BROTHERMODE_SESSION_CAP"
PROJECTS_ENV = "BROTHERMODE_PROJECTS_ROOT"

#: How recently a transcript must have been written for its session to
#: count as live. Ten minutes: longer than any single turn observed on
#: 2026-08-08 (the slowest hour held 1,431 turns across thirteen sessions),
#: short enough that yesterday's forty dead sessions do not lock the
#: founder out of their own machine this morning.
RECENCY_SECONDS = 600

#: The spawn shapes this refuses. Anchored on a word boundary rather than
#: on the start of the line, because every real launch the relay prints is
#: wrapped: `nohup claude -p '...' > log 2>&1 &`, often after a `cd`. A
#: matcher that only saw line-initial `claude` would pass every launch this
#: file exists to stop.
_SPAWN = re.compile(r"(?:^|[;&|]|\s)claude\s+(?:-p|--print)\b")


def deny_payload(reason):
    """The deny object, in the exact shape the PreToolUse contract
    requires and tools/bm_fence_hook.py already emits. Kept identical to
    that file on purpose: two refusal shapes in one product is one shape
    the harness silently ignores."""
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}


def _warn(message):
    sys.stderr.write(message.rstrip("\n") + "\n")


def projects_root(env=None):
    """Where Claude Code keeps its session transcripts."""
    env = os.environ if env is None else env
    override = env.get(PROJECTS_ENV)
    if override:
        return override
    return os.path.expanduser(os.path.join("~", ".claude", "projects"))


def cap(env=None):
    """The cap in force. An unreadable value returns the default rather
    than raising: a typo in an environment variable must not be able to
    deny every launch on the machine, nor to allow every one."""
    env = os.environ if env is None else env
    raw = env.get(CAP_ENV)
    if raw is None:
        return CAP_DEFAULT
    try:
        return max(0, int(str(raw).strip()))
    except (TypeError, ValueError):
        _warn("bm_session_cap: %s is %r, which is not a number of "
              "sessions, so the default of %d is in force."
              % (CAP_ENV, raw, CAP_DEFAULT))
        return CAP_DEFAULT


def count_live_sessions(root, now=None, recency=RECENCY_SECONDS):
    """How many session transcripts were written to inside the window, or
    None when the directory cannot be read at all. None is the signal to
    FAIL OPEN; a zero count is a real answer and means the machine is
    idle. Those two must never collapse into one value, which is why this
    returns None rather than 0 on failure."""
    now = time.time() if now is None else now
    cutoff = now - recency
    try:
        projects = os.listdir(root)
    except OSError as exc:
        _warn("bm_session_cap: the session directory could not be read "
              "(%s), so no session count is claimed and this launch is "
              "allowed." % exc)
        return None
    live = 0
    for project in projects:
        pdir = os.path.join(root, project)
        try:
            names = os.listdir(pdir)
        except OSError:
            # ONE unreadable project directory is not a failure to count:
            # it is one directory missing from an otherwise real number.
            # Refusing the whole count here would fail open on a permission
            # quirk in a single folder, which is how a cap quietly stops
            # being a cap.
            _warn("bm_session_cap: skipped an unreadable project directory "
                  "(%s); the count below excludes it." % project)
            continue
        for name in names:
            if not name.endswith(".jsonl"):
                continue
            try:
                if os.path.getmtime(os.path.join(pdir, name)) >= cutoff:
                    live += 1
            except OSError:
                continue
    return live


def is_session_spawn(envelope):
    """True when this tool call would start another Claude Code session.
    Only Bash can: every other tool is out of scope by construction, and
    saying so here keeps the gate narrow in one readable place."""
    if not isinstance(envelope, dict):
        return False
    if envelope.get("tool_name") != "Bash":
        return False
    tool_input = envelope.get("tool_input")
    if not isinstance(tool_input, dict):
        return False
    command = tool_input.get("command")
    if not isinstance(command, str):
        return False
    return bool(_SPAWN.search(command))


def decide(envelope, projects_root=None, env=None, now=None):
    """The whole decision: a deny payload, or None to allow. Pure apart
    from the filesystem read, so the cap's behaviour can be proven without
    a hook harness, a real session, or a real `claude` binary."""
    env = os.environ if env is None else env
    if not is_session_spawn(envelope):
        return None
    root = (projects_root if projects_root is not None
            else globals()["projects_root"](env))
    live = count_live_sessions(root, now=now)
    if live is None:
        return None
    limit = cap(env)
    if live < limit:
        return None
    return deny_payload(
        "BrotherMode session cap: %d Claude sessions have been active in "
        "the last %d minutes and the cap is %d, so this launch is refused. "
        "On 2026-08-08 an unattended chain reached fifteen at once and "
        "spent millions of tokens with nobody watching, which is why this "
        "refuses rather than warns. Close a session and try again, or raise "
        "the cap deliberately with %s=N in the environment of the session "
        "doing the launching. Do not work around this by starting the "
        "session another way."
        % (live, RECENCY_SECONDS // 60, limit, CAP_ENV))


def main(argv=None):
    """The hook invocation: one JSON envelope on stdin, one JSON object on
    stdout when refusing, nothing at all when allowing. Exit 0 either way,
    because a non-zero exit reads as a BROKEN HOOK to the harness rather
    than as a refusal, and a refusal nobody honours is theatre."""
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        raw = sys.stdin.read()
    except (OSError, ValueError) as exc:
        _warn("bm_session_cap: stdin could not be read (%s); allowing."
              % exc)
        return 0
    try:
        envelope = json.loads(raw) if raw.strip() else {}
    except ValueError as exc:
        _warn("bm_session_cap: the hook envelope was not JSON (%s); "
              "allowing, because a cap that guesses at a malformed "
              "envelope refuses the wrong calls." % exc)
        return 0
    decision = decide(envelope)
    if decision is not None:
        sys.stdout.write(json.dumps(decision))
    return 0


if __name__ == "__main__":
    sys.exit(main())
