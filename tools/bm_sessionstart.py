#!/usr/bin/env python3
"""BrotherMode SessionStart: digest plus mechanical nags. MUST always exit 0.

THE WINDOWS PORT (2026-08-17). This file is tools/bm_sessionstart.sh ported
statement for statement to Python, because `sh` is not on the Windows PATH
and a SessionStart hook wired through it was installed-and-silently-dead on
any Windows machine without Git Bash. The port was proved byte-identical to
the shell version with diff, on the same fixtures the consent suite uses
(an unconsented HOME, then a consented one), before the shell version was
deleted. Python is the interpreter every other hook already requires, so
this adds no new dependency on any platform. Windows behavior remains
UNVERIFIED until a real Windows machine runs it; nothing in this file has
been exercised outside POSIX yet, and docs/WINDOWS-CHECK.md is the protocol
for closing that.

Output is injected into session context (10k char cap; we stay far under).
Every check is fail-open ON PURPOSE, matching the shell version line for
line: this hook runs at every session start, so a tool that is absent on an
older install, or that crashes, must degrade to silence (or one short line)
rather than take the session down with it. That is why most calls below
discard stderr and ignore their exit codes; the shell spelled it 2>/dev/null
and `|| true`, and this file spells it _run(..) with the same intent.

The subprocess import is a NAMED exception in tools/test_bm.py's
zero-network suite, the same local-execution posture as bm_autosave.py
driving git: every process this file starts is a sibling tool from this
repository, on this machine, with no network anywhere. SECURITY.md
documents it beside the other named exceptions.

Consent gate (Loop 3 design D-1): before any write or store command below,
check consent via scripts/setup.py's cheap --consent-state probe (exit 0
consented, non-zero otherwise: absent config, setup_complete false, or a
broken config all read the same way here, fail closed). Not consented means
this script prints exactly one plain sentence and exits 0 having written
nothing at all: no digest, no telemetry, no store verify. scripts/setup.py
is the ONLY place that creates ~/.brotherme/config.json.

Python 3.9, standard library only. No em or en dashes anywhere in this
file, its comments, or its output.
"""

import io
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.dirname(HERE)

#: What the store-health capture is allowed to stay silent about: silent when
#: healthy or when no store exists yet, printed whenever verify reports
#: something the founder has to act on. "refused (schema-" is matched too
#: (2026-08-04): a store one schema behind or ahead stopped being reported as
#: STORE CORRUPT that day, which is the truth, but it is still actionable
#: (one writable command migrates it); without this alternative the fix would
#: have traded a scary visible message for an accurate invisible one.
_STORE_WORRY = re.compile(
    r"problem\(s\) found|STORE CORRUPT|refused \(schema-|WARNING|"
    r"unexpected error|db-busy|stale-identity|Traceback")


def _say(text):
    """Write to stdout AND FLUSH, and the flush is the load-bearing half.

    The shell version's children inherited stdout and wrote as they ran, so
    every line landed in the order the script produced it. Python buffers a
    pipe, so without this the whole digest arrived AFTER every child's
    output and the injected context read in a different order than it had
    for a year. Found by diffing the two versions on a consented fixture
    before the shell one was deleted; the CONTENT matched on the first try
    and only the order did not, which is exactly the class of difference a
    port is most likely to ship."""
    sys.stdout.write(text)
    sys.stdout.flush()


def _tool(*parts):
    return os.path.join(DIR, *parts)


def _run(args, stdin_text=None, capture=False, keep_stderr=False):
    """One sibling tool, with the shell version's exact degrade semantics:
    OSError (interpreter or file missing) reads as a silent non-run, the
    same way 2>/dev/null swallowed it, and the caller decides what an exit
    code means. Returns (returncode, stdout) with stdout None unless
    captured."""
    kwargs = {"universal_newlines": True}
    if stdin_text is not None:
        kwargs["input"] = stdin_text
    else:
        kwargs["stdin"] = subprocess.DEVNULL
    if capture:
        kwargs["stdout"] = subprocess.PIPE
    if keep_stderr:
        kwargs["stderr"] = subprocess.STDOUT if capture else None
    else:
        kwargs["stderr"] = subprocess.DEVNULL
    try:
        result = subprocess.run([sys.executable] + list(args), **kwargs)
    except OSError:
        return 127, ""
    return result.returncode, (result.stdout if capture else None)


def main():
    # Capture the hook JSON from stdin ONCE so we can both ignore it
    # (digest/nags) and replay it to the compaction hint below. The shell
    # version's PAYLOAD="$(cat)" stripped trailing newlines; matched here.
    try:
        payload = sys.stdin.read()
    except (IOError, OSError, ValueError):
        payload = ""
    payload = payload.rstrip("\n")

    # The shell spelled this >/dev/null 2>&1: the probe is an exit code, and
    # nothing it might print belongs in session context.
    code, _ = _run([_tool("scripts", "setup.py"), "--consent-state"],
                   capture=True)
    if code != 0:
        _say("BrotherMode setup is not complete yet; run: "
             "python3 scripts/setup.py\n")
        return 0

    try:
        with io.open(_tool("DIGEST.md"), encoding="utf-8") as fh:
            _say(fh.read())
    except (IOError, OSError):
        pass

    _run([_tool("tools", "bm_telemetry.py"), "startup-nags"])
    # PROGRESS PAGE OWED (founder directive 2026-08-10): one line ONLY when a
    # plan exists and the page is missing or older than that plan; silent
    # otherwise, because a nag that fires every session stops being read.
    _run([_tool("tools", "bm_progress_check.py"), "status"])
    # Stall sweep (Loop SD): pure read, prints stale fences and dead owners
    # with their exact clearing command. Fail-open like everything here.
    _run([_tool("tools", "bm_stall.py"), "sweep"])

    # BATON CEREMONY OPENING HALF (R1.3). CLAUDE.md's baton ceremony section
    # calls `bm_handover.py detect` the START half every session runs before
    # new work. detect promises exit 0 always and turns every read failure it
    # knows about into a stated NO-DATA line, so a non-zero exit or empty
    # output here means something UNEXPECTED happened (the file moved), and
    # that case degrades to one short line, never a traceback.
    code, detect_out = _run([_tool("tools", "bm_handover.py"), "detect"],
                            capture=True)
    detect_out = (detect_out or "").rstrip("\n")
    if code == 0 and detect_out:
        _say(detect_out + "\n")
    else:
        _say(
            "baton ceremony check (bm_handover.py detect) could not run "
            "this session; run it by hand, see CLAUDE.md baton ceremony "
            "section\n")

    # CLOSE-PACK OWED (2026-08-12): a session opens being told the previous
    # one left no handover, which is the person who can still do something
    # about it. Silent when nothing is owed. Runs HERE rather than on Stop
    # because this script has already passed the consent door, so the check
    # inherits that gate instead of needing its own.
    code, owed_out = _run([_tool("tools", "bm_handover.py"), "owed"],
                          capture=True)
    if code != 127 and owed_out:
        for line in owed_out.splitlines(True):
            if not line.startswith("CURRENT"):
                _say(line)

    _run([_tool("tools", "bm_telemetry.py"), "check-update"])

    # IDLE CONTROL (O19 plus A4, founder order 2026-08-15: never stay idle).
    # Two one-line verdicts, both fail open, because a session that cannot
    # compute its idle verdict must still start; the absence of the line is
    # itself visible.
    _run([_tool("tools", "bm_idle.py"), "check"])
    code, cal_out = _run([_tool("tools", "bm_forecast.py"), "calibrate",
                          "--clock", "agent", "--basis", "judged"],
                         capture=True)
    if code != 127 and cal_out:
        lines = cal_out.splitlines(True)
        if lines:
            _say(lines[-1])

    # If this session resumed from a compaction, point it at the autosave.
    _run([_tool("tools", "bm_telemetry.py"), "compact-hint"],
         stdin_text=payload)

    # Store health: silent when healthy or when no store exists yet, printed
    # whenever there is something real to see, so a lost database is never a
    # session's whole SessionStart output being nothing.
    _code, health = _run([_tool("tools", "bm_store.py"), "verify"],
                         capture=True, keep_stderr=True)
    health = (health or "").rstrip("\n")
    if health and _STORE_WORRY.search(health):
        _say(health + "\n")
    return 0


if __name__ == "__main__":
    try:
        code = main()
    except Exception:
        # The header's contract: MUST always exit 0. An unexpected crash in
        # a session-start nag must never take the session down with it.
        code = 0
    sys.exit(code)
