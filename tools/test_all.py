#!/usr/bin/env python3
"""Run every BrotherMode suite SERIALLY and return one exit code.

WHY THIS EXISTS
  There are four suites, not one, and the number keeps growing. Until now the
  loop-close gate was "run the tests", which in practice meant whichever suites
  the person remembered, and a suite nobody ran is a suite that is not gating
  anything. This file is the gate: one command, one exit code, every suite.

WHY SERIALLY, AND WHY THAT IS NOT A STYLE CHOICE
  docs/NOT-FINALIZED.md item 10: the suites rename a module aside mid-run, so two
  running at once corrupt each other. It was reproduced on 2026-07-27 (the fence
  hook suite failed once under contention and passed on re-run). A parallel runner
  here would manufacture exactly that flake and then blame it on whatever code was
  being tested. So this runs them one at a time, on purpose, and the underlying
  design defect stays OPEN and stated rather than being papered over by a runner
  that looks fast.

WHY EACH SUITE GETS ITS OWN PROCESS
  The same module-renaming behaviour means importing two suites into one Python
  process is not isolation either. A subprocess per suite is the isolation, and it
  is also what makes a crashed or hung suite reportable instead of fatal to the
  run.

WHY THIS FILE IS NAMED test_all.py
  tools/test_bm.py's no-network/no-subprocess check bans `import subprocess` in
  every SHIPPING module under tools/, with one documented per-file exemption. A
  test runner cannot exist without subprocess. Rather than widen that exemption
  (which would let a future shipping module inherit it quietly), this file takes
  the `test_` prefix the check already excludes for exactly this stated reason:
  "the test files themselves may import subprocess to drive the CLI they are
  testing, which is local execution, not a network call". This IS test
  infrastructure. The shipping ban is untouched and still covers every module a
  founder actually runs.

Python 3.9, standard library only. No network. Writes no files.

No em or en dashes anywhere in this file, its comments, or its output.
"""

import io
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))

# Declared in the order that fails fastest and cheapest first, so a broken store
# is reported in eight seconds rather than after a full minute of other suites.
# The store suite is the foundation every other one stands on.
SUITES = (
    "test_bm_store.py",
    "test_bm_fence_hook.py",
    "test_bm_autosave.py",
    "test_bm.py",
)

# unittest writes its summary to stderr. Both shapes appear in real output:
#   "Ran 244 tests in 7.452s"
#   "OK (skipped=2)"  /  "FAILED (failures=1, errors=2)"
_RAN_RE = re.compile(r"^Ran (\d+) tests? in ([\d.]+)s", re.M)
_SKIP_RE = re.compile(r"skipped=(\d+)")


def _discover():
    """Every suite that exists on disk, so a NEW suite cannot be silently left
    out of the gate by whoever forgot to add it to SUITES. A file matching
    test_*.py that is not in SUITES is reported loudly rather than skipped: an
    unlisted suite is the exact failure this runner exists to prevent."""
    on_disk = sorted(
        n for n in os.listdir(HERE)
        if n.startswith("test_") and n.endswith(".py") and n != "test_all.py")
    known = list(SUITES)
    unlisted = [n for n in on_disk if n not in known]
    missing = [n for n in known if n not in on_disk]
    return known, unlisted, missing


def _run_one(name):
    """Run one suite in its own process. Returns (ok, tests, skipped, seconds,
    tail). Never raises: a suite that cannot start at all is a RESULT, reported
    with its reason, not an exception that hides the other three."""
    path = os.path.join(HERE, name)
    started = time.time()
    try:
        proc = subprocess.run(
            [sys.executable, path],
            cwd=HERE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True)
    except OSError as exc:
        return False, 0, 0, time.time() - started, "could not start: %s" % exc
    elapsed = time.time() - started
    out = proc.stdout or ""
    m = _RAN_RE.search(out)
    tests = int(m.group(1)) if m else 0
    sm = _SKIP_RE.search(out)
    skipped = int(sm.group(1)) if sm else 0
    ok = proc.returncode == 0
    if ok and tests == 0:
        # A suite that exits 0 having run nothing is not a pass. This is the
        # exit-code-tests-pass-for-the-wrong-reason class from docs/knowledge/
        # LESSONS.md: an import error can exit 0 in some runners and would
        # otherwise be counted as green here.
        ok = False
        tail = "exited 0 but ran 0 tests (import error or empty suite?)"
    else:
        lines = [ln for ln in out.splitlines() if ln.strip()]
        tail = " | ".join(lines[-3:]) if lines else "(no output)"
    return ok, tests, skipped, elapsed, tail


def main(argv):
    if any(a in ("-h", "--help") for a in argv):
        sys.stdout.write(__doc__)
        return 0
    unknown = [a for a in argv if a.startswith("-")]
    if unknown:
        sys.stderr.write(
            "test_all: unrecognized flag(s) %s (recognized: --help)\n"
            % ", ".join(unknown))
        return 2

    known, unlisted, missing = _discover()
    if unlisted:
        sys.stderr.write(
            "test_all: REFUSING to run. These suites exist on disk but are not "
            "in the gate: %s. Add them to SUITES in tools/test_all.py so the "
            "gate covers them, then re-run.\n" % ", ".join(unlisted))
        return 2
    if missing:
        sys.stderr.write(
            "test_all: REFUSING to run. These suites are in the gate but not on "
            "disk: %s. Either restore them or remove them from SUITES.\n"
            % ", ".join(missing))
        return 2

    sys.stdout.write("test_all: %d suites, serially, one process each\n\n"
                     % len(known))
    results = []
    total_tests = total_skipped = 0
    wall = time.time()
    for name in known:
        sys.stdout.write("  running %-24s " % name)
        sys.stdout.flush()
        ok, tests, skipped, elapsed, tail = _run_one(name)
        results.append((name, ok, tests, skipped, elapsed, tail))
        total_tests += tests
        total_skipped += skipped
        sys.stdout.write("%s  %3d tests  %5.1fs\n"
                         % ("OK  " if ok else "FAIL", tests, elapsed))
        sys.stdout.flush()
    wall = time.time() - wall

    failed = [r for r in results if not r[1]]
    sys.stdout.write("\n")
    if failed:
        sys.stdout.write("FAILURES (%d of %d suites):\n" % (len(failed), len(known)))
        for name, _ok, _t, _s, _e, tail in failed:
            sys.stdout.write("  %s: %s\n" % (name, tail))
        sys.stdout.write("\n")
    sys.stdout.write(
        "test_all: %d tests across %d suites, %d skipped, %.1fs wall. %s\n"
        % (total_tests, len(known), total_skipped, wall,
           "ALL GREEN" if not failed else "%d SUITE(S) FAILED" % len(failed)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
