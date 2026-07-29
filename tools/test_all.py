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

WHAT LOOP 9 ADDED
  1. An INTERPROCESS LOCK. The module-rename hazard above is a real corruption
     risk, not a theoretical one, and running serially inside ONE runner does
     nothing about a second runner started in another terminal. The lock is
     taken by this runner and by the rename windows inside test_bm_store.py, so
     the two cannot overlap even across processes. It is a GUARD, not a fix: the
     suites still rename a module aside. See docs/NOT-FINALIZED.md item 10.
  2. PER SUITE TIMEOUTS with hung-suite diagnostics, so a wedged suite is
     reported as a timeout with its partial output instead of hanging the gate
     until somebody notices and kills it.
  3. --artifacts DIR, which writes the FULL output of every suite to disk so CI
     can upload it on failure. Without that flag this file still writes no files.
  4. A CI INVENTORY CHECK: every suite in SUITES must be named in
     .github/workflows/tests.yml, so a suite cannot be in the local gate and
     absent from CI, or the reverse. Local and CI run the SAME check, because CI
     runs this file.

Python 3.9, standard library only. No network. Writes no files except the lock
described above, and the suite logs when --artifacts is passed.

No em or en dashes anywhere in this file, its comments, or its output.
"""

import errno
import hashlib
import io
import os
import re
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
WORKFLOW = os.path.join(REPO, ".github", "workflows", "tests.yml")

# A suite that hangs is worse than a suite that fails: it burns the whole gate
# with no diagnosis. 900s is roughly 4x the worst observed wall time under heavy
# contention (test_bm went 20s to 202s on 2026-07-27), so it fires on a wedge
# rather than on a slow machine.
DEFAULT_TIMEOUT = float(os.environ.get("BROTHERMODE_TEST_TIMEOUT", "900"))

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


# -- interprocess gate lock -------------------------------------------------
#
# The lock is keyed to THIS checkout, not to the machine: two worktrees rename
# their OWN copy of bm_telemetry.py, so they cannot corrupt each other and must
# not block each other either. It lives in the system temp directory rather than
# in the repo so it never shows up in git status.

LOCK_ENV = "BROTHERMODE_TEST_GATE_LOCK"
LOCK_TIMEOUT = float(os.environ.get("BROTHERMODE_TEST_LOCK_TIMEOUT", "900"))
# A lock older than this is a crashed run, not a live one. Deliberately longer
# than any plausible full gate run.
LOCK_STALE_SECONDS = 3600.0


class GateLockBusy(Exception):
    """Another gate run holds the lock and did not release it in time."""


def lock_path():
    tag = hashlib.sha256(HERE.encode("utf-8")).hexdigest()[:16]
    return os.path.join(tempfile.gettempdir(),
                        "brothermode-test-gate-%s.lock" % tag)


def _lock_holder(path):
    try:
        with io.open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read().strip() or "(holder record not yet written)"
    except (IOError, OSError):
        return "(holder record unreadable)"


def _lock_is_stale(path):
    """True only when the holder is provably gone. An unparseable or empty file
    is a lock being taken RIGHT NOW, not a dead one, so it falls back to age."""
    try:
        with io.open(path, encoding="utf-8", errors="replace") as fh:
            fields = fh.read().split()
    except (IOError, OSError):
        return False
    try:
        pid = int(fields[0])
        stamp = float(fields[1])
    except (IndexError, ValueError):
        try:
            return (time.time() - os.path.getmtime(path)) > LOCK_STALE_SECONDS
        except OSError:
            return False
    if (time.time() - stamp) > LOCK_STALE_SECONDS:
        return True
    if os.name == "posix" and pid > 0:
        try:
            os.kill(pid, 0)
        except OSError as exc:
            # ESRCH means no such process. EPERM means it exists and is not
            # ours, which is alive, not stale.
            return exc.errno == errno.ESRCH
    return False


def acquire_gate_lock(timeout=None, owner="test_all", quiet=False):
    """Take the checkout-wide test lock. Returns a handle, or None when an
    ancestor process already holds it (test_all running a suite as a child), in
    which case there is nothing to take and nothing to release."""
    if os.environ.get(LOCK_ENV):
        return None
    path = lock_path()
    deadline = time.time() + (LOCK_TIMEOUT if timeout is None else timeout)
    announced = False
    while True:
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise
            if _lock_is_stale(path):
                if not quiet:
                    sys.stderr.write(
                        "test_all: removing a stale gate lock from a crashed "
                        "run: %s\n" % _lock_holder(path))
                try:
                    os.remove(path)
                except OSError:
                    pass
                continue
            if time.time() >= deadline:
                raise GateLockBusy(
                    "another test run holds %s (%s). The suites rename a module "
                    "aside mid-run, so two at once corrupt each other "
                    "(docs/NOT-FINALIZED.md item 10). Wait for it, or delete "
                    "that file if you are sure the holder is dead."
                    % (path, _lock_holder(path)))
            if not announced and not quiet:
                sys.stderr.write(
                    "test_all: waiting for another test run to finish: %s\n"
                    % _lock_holder(path))
                announced = True
            time.sleep(0.25)
            continue
        with os.fdopen(fd, "w") as fh:
            fh.write("%d %.3f %s\n" % (os.getpid(), time.time(), owner))
        # Children inherit this, which is how a suite launched BY this runner
        # knows the lock is already held rather than deadlocking against it.
        os.environ[LOCK_ENV] = path
        return path


def release_gate_lock(handle):
    if not handle:
        return
    os.environ.pop(LOCK_ENV, None)
    try:
        os.remove(handle)
    except OSError:
        pass


# -- CI inventory ------------------------------------------------------------

_CI_SUITE_RE = re.compile(r"tools/(test_[A-Za-z0-9_]+\.py)")


def _ci_inventory():
    """Suites named in the CI workflow. None when there is no workflow file,
    which is the normal case for an extracted copy of the skill: an end user's
    checkout has no .github, and that must not be reported as a CI gap."""
    try:
        with io.open(WORKFLOW, encoding="utf-8") as fh:
            text = fh.read()
    except (IOError, OSError):
        return None
    return set(_CI_SUITE_RE.findall(text))


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


def _run_one(name, timeout=None):
    """Run one suite in its own process. Returns (ok, tests, skipped, seconds,
    tail, output). Never raises: a suite that cannot start at all, or hangs, is
    a RESULT reported with its reason, not an exception that hides the rest."""
    path = os.path.join(HERE, name)
    if timeout is None:
        timeout = DEFAULT_TIMEOUT
    started = time.time()
    try:
        proc = subprocess.run(
            [sys.executable, path],
            cwd=HERE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            timeout=timeout)
    except OSError as exc:
        return (False, 0, 0, time.time() - started,
                "could not start: %s" % exc, "could not start: %s" % exc)
    except subprocess.TimeoutExpired as exc:
        # A hung suite used to hang the gate. Report it as a timeout, keep the
        # partial output (it names the last test that started, which is almost
        # always the one that wedged), and carry on with the other suites.
        elapsed = time.time() - started
        partial = exc.output or ""
        if isinstance(partial, bytes):
            partial = partial.decode("utf-8", "replace")
        lines = [ln for ln in partial.splitlines() if ln.strip()]
        tail = ("TIMED OUT after %.0fs (limit %.0fs), killed. Last output: %s"
                % (elapsed, timeout,
                   " | ".join(lines[-3:]) if lines else "(none)"))
        return False, 0, 0, elapsed, tail, partial + "\n" + tail + "\n"
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
    return ok, tests, skipped, elapsed, tail, out


def main(argv):
    if any(a in ("-h", "--help") for a in argv):
        sys.stdout.write(__doc__)
        return 0
    artifacts = None
    timeout = DEFAULT_TIMEOUT
    rest = list(argv)
    while rest:
        arg = rest.pop(0)
        if arg == "--artifacts":
            if not rest:
                sys.stderr.write("test_all: --artifacts needs a directory\n")
                return 2
            artifacts = rest.pop(0)
        elif arg == "--timeout":
            if not rest:
                sys.stderr.write("test_all: --timeout needs seconds\n")
                return 2
            try:
                timeout = float(rest.pop(0))
            except ValueError:
                sys.stderr.write("test_all: --timeout wants a number\n")
                return 2
        elif arg == "--check-only":
            # Inventory checks without running anything. For a CI leg that only
            # needs to prove local and CI agree.
            known, unlisted, missing = _discover()
            return _inventory_gate(known, unlisted, missing)
        else:
            sys.stderr.write(
                "test_all: unrecognized argument %s (recognized: --help, "
                "--artifacts DIR, --timeout SECONDS, --check-only)\n" % arg)
            return 2

    known, unlisted, missing = _discover()
    rc = _inventory_gate(known, unlisted, missing)
    if rc:
        return rc

    try:
        lock = acquire_gate_lock(owner="test_all pid %d" % os.getpid())
    except GateLockBusy as exc:
        sys.stderr.write("test_all: REFUSING to run. %s\n" % exc)
        return 2
    try:
        return _run_all(known, artifacts, timeout)
    finally:
        release_gate_lock(lock)


def _inventory_gate(known, unlisted, missing):
    """Every refusal that must fire before a single test runs. Returns 0 or 2."""
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
    ci = _ci_inventory()
    if ci is None:
        sys.stdout.write(
            "test_all: no %s in this checkout, so the CI inventory check is "
            "SKIPPED (normal for an extracted copy).\n"
            % os.path.relpath(WORKFLOW, REPO))
        return 0
    absent = [n for n in known if n not in ci]
    if absent:
        sys.stderr.write(
            "test_all: REFUSING to run. These suites are in the local gate but "
            "are never run by CI: %s. Add a step for each to %s, or the same "
            "claim is tested on your machine and nowhere else.\n"
            % (", ".join(absent), os.path.relpath(WORKFLOW, REPO)))
        return 2
    phantom = sorted(n for n in ci
                     if n != "test_all.py" and n not in known)
    if phantom:
        sys.stderr.write(
            "test_all: REFUSING to run. CI runs suites that this gate does not "
            "know about: %s. Either add them to SUITES or remove them from %s.\n"
            % (", ".join(phantom), os.path.relpath(WORKFLOW, REPO)))
        return 2
    return 0


def _write_artifact(artifacts, name, body):
    """Full output to disk so CI can upload it on failure. Best effort by
    design: losing a log must never turn a green gate red or a red one green."""
    try:
        if not os.path.isdir(artifacts):
            os.makedirs(artifacts)
        with io.open(os.path.join(artifacts, name), "w", encoding="utf-8") as fh:
            fh.write(body)
    except (IOError, OSError) as exc:
        sys.stderr.write("test_all: could not write artifact %s: %s\n"
                         % (name, exc))


def _run_all(known, artifacts, timeout):
    sys.stdout.write(
        "test_all: %d suites, serially, one process each, %.0fs timeout each\n\n"
        % (len(known), timeout))
    results = []
    total_tests = total_skipped = 0
    wall = time.time()
    for name in known:
        sys.stdout.write("  running %-24s " % name)
        sys.stdout.flush()
        ok, tests, skipped, elapsed, tail, out = _run_one(name, timeout)
        results.append((name, ok, tests, skipped, elapsed, tail))
        total_tests += tests
        total_skipped += skipped
        if artifacts:
            _write_artifact(artifacts, name + ".log", out)
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
    summary = (
        "test_all: %d tests across %d suites, %d skipped, %.1fs wall. %s\n"
        % (total_tests, len(known), total_skipped, wall,
           "ALL GREEN" if not failed else "%d SUITE(S) FAILED" % len(failed)))
    sys.stdout.write(summary)
    if artifacts:
        _write_artifact(artifacts, "summary.txt", "".join(
            ["%s  %s  %d tests  %d skipped  %.1fs  %s\n"
             % (("OK" if ok else "FAIL"), name, tests, skipped, elapsed, tail)
             for name, ok, tests, skipped, elapsed, tail in results]) + summary)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
