#!/usr/bin/env python3
"""Run every BrotherMode suite SERIALLY and return one exit code.

WHY THIS EXISTS
  There are four suites, not one, and the number keeps growing. Until now the
  loop-close gate was "run the tests", which in practice meant whichever suites
  the person remembered, and a suite nobody ran is a suite that is not gating
  anything. This file is the gate: one command, one exit code, every suite.

WHY SERIALLY, AND WHY THAT IS NOT A STYLE CHOICE
  The suites used to rename a module aside mid-run, so two running at once
  corrupted each other (reproduced 2026-07-27: the fence hook suite failed once
  under contention and passed on re-run). The P9 fix round removed the rename
  technique itself, so that particular hazard is gone rather than guarded. This
  still runs serially: the suites share one checkout, spawn subprocesses, and
  compete for the same temp and git state, so a parallel runner here would buy
  wall time at the cost of flakes nobody can reproduce.

WHY EACH SUITE GETS ITS OWN PROCESS
  Importing two suites into one Python process is not isolation: they patch
  module globals, install fakes, and load the same modules under different
  names. A subprocess per suite is the isolation, and it is also what makes a
  crashed or hung suite reportable instead of fatal to the run.

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
  1. An INTERPROCESS LOCK, so two gate runs started in two terminals against
     the same checkout do not interleave. The rename hazard it was originally
     written for is gone (the P9 fix round removed the technique), but two
     concurrent runs still share one working tree, so the lock stays.
  2. PER SUITE TIMEOUTS with hung-suite diagnostics, so a wedged suite is
     reported as a timeout with its partial output instead of hanging the gate
     until somebody notices and kills it. The timeout kills the suite with
     SIGKILL, which runs no cleanup in the child: that is safe only because no
     suite mutates this checkout any more, and it must stay that way.
  3. --artifacts DIR, which writes the FULL output of every suite to disk so CI
     can upload it on failure. Without that flag this file still writes no files.
  4. A CI INVENTORY CHECK: every suite in SUITES must be EXECUTED by a step in
     .github/workflows/tests.yml, so a suite cannot be in the local gate and
     absent from CI, or the reverse. Local and CI run the SAME check, because CI
     runs this file. "Executed", not "mentioned": see the CI inventory section.

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
import threading
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
    # Documentation consistency runs first: it takes a fraction of a second and
    # it fails on a fact that has drifted rather than on code, so a stale README
    # is reported before the long suites run rather than after them.
    "test_bm_docs.py",
    "test_bm_store.py",
    # Loop 2 (2026-08-01): the mechanical command line over the Store
    # service methods and D-2 read accessors in bm_store.py. Placed right
    # after the store suite it wraps, before the other subprocess-heavy
    # suites, since it drives tools/bm_project.py as a real subprocess and
    # depends on the store schema the suite above already proved sound.
    # NO APOSTROPHE ANYWHERE IN THIS COMMENT, ON PURPOSE: the fact loader
    # in bm_project_facts.py extracts every quoted span inside this tuple
    # with a plain quote-to-quote regex, so a stray apostrophe in a
    # comment here opens a fake quoted region that swallows real suite
    # names. Reproduced directly while writing this: it broke test_bm_docs
    # dot py, the test named test every named suite file exists.
    "test_bm_project.py",
    # U1, the autonomy contract layer (loop L02, 2026-08-05): the CLI over
    # the schema 14 autonomy Store service methods added to bm_store.py.
    # NO APOSTROPHE ANYWHERE IN THIS COMMENT, ON PURPOSE (see the note
    # above): placed right after the project CLI suite, before the other
    # subprocess-heavy suites, since it drives tools/bm_autonomy.py as a
    # real subprocess and depends on the schema-14 tables the store suite
    # two entries up already proved sound.
    "test_bm_autonomy.py",
    # U2, the durable Full-Auto controller (loop L03, 2026-08-05): the
    # engine tests drive ControllerEngine in process against the schema
    # 15 tables, and the CLI section drives tools/bm_controller.py as a
    # real subprocess, the same way test_bm_autonomy.py drives its own
    # CLI. NO APOSTROPHE ANYWHERE IN THIS COMMENT, ON PURPOSE (see the
    # note above): placed right after the autonomy suite it builds on,
    # since the controller run needs a live contract the autonomy CLI
    # already proved sound.
    "test_bm_controller.py",
    # L04 (2026-08-05): founder mode, IC mode, the record of what was
    # decided, the half hour catch-up and the handover pages, over the
    # schema 16 tables. NO APOSTROPHE ANYWHERE IN THIS COMMENT, ON PURPOSE
    # (see the note above): placed right after the controller suite whose
    # run state and unit rows this one reads, and it drives
    # tools/bm_lead.py in process for most of its work plus as a real
    # subprocess for the pre-consent proof.
    "test_bm_lead.py",
    # L05 (2026-08-05): the visual surface. The vocabulary suite first
    # (the drawn shapes, the alert ladder, the insight box and the
    # rewritten refusals in tools/bm_visual.py), then the page and CLI
    # suite (tools/bm_view.py: the live project view, the consent door,
    # the empty states and the developer brief page). NO APOSTROPHE
    # ANYWHERE IN THESE COMMENTS, ON PURPOSE (see the note above): placed
    # right after the lead surface suite whose collectors both modules
    # read, over the schema 17 tables the store suite already proved
    # sound.
    "test_bm_visual.py",
    "test_bm_view.py",
    # v3 Wave B (2026-08-08): the native agent definitions pin and the
    # hook chain measurement suite, registered the same day they landed
    # so the inventory gate never runs past an unlisted suite.
    "test_bm_agents.py",
    "test_bm_hookperf.py",
    # v3 Wave C (2026-08-08): the lifecycle canary step pins. The live
    # canary script itself stays unregistered like probe-installed, it
    # needs a real claude binary; these pins are fast and deterministic.
    "test_bm_e2e_pins.py",
    "test_bm_fence_hook.py",
    # Loop 6 WP-G (2026-08-01): the Bash-write detection suite for
    # tools/bm_bash_audit.py. Placed right after the fence hook suite it
    # extends: both drive real subprocesses against a throwaway project and
    # share the same session-identity module.
    "test_bm_bash_audit.py",
    # D6 (2026-08-07): the hook cost benchmark, tools/bm_hookbench.py, and
    # the page it generates, docs/PERFORMANCE.md. NO APOSTROPHE ANYWHERE IN
    # THIS COMMENT, ON PURPOSE (see the file-level note above). Placed right
    # after the two hook suites whose programs it times, since it drives the
    # same hook entrypoints against a throwaway store and asserts nothing
    # about how long they took, only that the page is generated from a real
    # run and refuses the numbers it cannot take honestly.
    "test_bm_hookbench.py",
    # The wall-clock lint and its own calibration, added 2026-08-10. It is the
    # machine that refuses the single most frequent defect in the recorded
    # history of this repository: a test asserting an absolute wall-clock
    # duration, which measures the HOST rather than the code and goes red on a
    # busy laptop while nothing changed. Found and fixed SEVEN separate times
    # in ten days by seven different people; review caught it every time and
    # prevented it zero times, which is the whole argument for a lint over
    # more care. Placed beside the two benchmark suites because it is the rule
    # those suites are the sanctioned exception to: the allow list names them,
    # so an absolute ceiling stays legal exactly where timing IS the
    # measurement and nowhere else. NO APOSTROPHE ANYWHERE IN THIS COMMENT, ON
    # PURPOSE (see the file-level note above). Written once with an apostrophe
    # on 2026-08-10, which made the fact loader read a bare s as a suite name
    # and turned test_bm_docs red, exactly as the note two hundred lines above
    # says it would.
    "test_bm_lint_walltime.py",
    # The progress-page check, added 2026-08-10 on a founder directive. The
    # progress page is how a non-engineer founder sees where a project stands,
    # and sessions kept BUILDING it and never SHOWING it, so it had to be
    # asked for. tools/bm_progress_check.py decides mechanically, per project,
    # whether a plan exists and whether the page is missing or older than that
    # plan, and tools/bm_sessionstart.sh runs it at every session start so the
    # verdict arrives in context instead of depending on memory. This suite
    # holds its calibration, including the purity assertion: the tool must
    # change zero bytes, because it runs on every single session start. NO
    # APOSTROPHE ANYWHERE IN THIS COMMENT, ON PURPOSE (see the file-level note
    # above).
    "test_bm_progress_check.py",
    # The status line and footer links, the 2026-08-05 answer 7 named in
    # docs/program/absolute-lead/DESIGN-visual-surface.md section 14, item
    # 1: tools/bm_statusline.py, a fail silent script BrotherMode ships but
    # does not install, and the footerLinksRegexes calibration against
    # docs/STATUS-LINE.md. NO APOSTROPHE ANYWHERE IN THIS COMMENT, ON
    # PURPOSE (see the file-level note above). Placed right after the hook
    # cost benchmark suite: both are small, fast, stdlib and filesystem
    # only additions that read the same tools/bm_lead.py collector the
    # visual surface suites above already proved sound.
    "test_bm_statusline.py",
    "test_install.py",
    # Loop 3 WP-D (2026-08-01): the consent gate suite for scripts/setup.py,
    # tools/bm_sessionstart.sh, and the SessionEnd path in tools/bm_telemetry.py.
    # NO APOSTROPHE IN THIS COMMENT, ON PURPOSE (see the file-level note above):
    # placed right after the installer suite; both drive real subprocesses
    # against a fake HOME, and this one is fast.
    "test_bm_consent.py",
    "test_bm_runtimes.py",
    "test_bm_autosave.py",
    # The loop estimate ledger, landed from the live install 2026-07-31. Early
    # for the same reason as the docs suite: it is fast and it fails on one of
    # its own three laws rather than on timing.
    "test_bm_ledger.py",
    # The canonical protocol schema (Loop 0, 2026-07-31): fast, pure library
    # tests, and its drift test fails on a spec/code mismatch rather than on
    # timing, so it runs with the other cheap early suites.
    "test_bm_schema.py",
    # The Memory Sentinel (Phase 1 of the Full-Auto program, 2026-08-02): the
    # schema 13 tables, the Store methods over them, and the deterministic
    # selector. Placed with the cheap early suites because most of it drives a
    # pure function with plain data and the rest uses a throwaway store, so it
    # fails on a policy branch rather than on timing.
    "test_bm_sentinel.py",
    # The machine-wide session cap (2026-08-09, after an unattended chain
    # ran fifteen sessions at once): pure functions over a throwaway
    # directory of fake transcripts, no store and no subprocess, so it
    # belongs with the cheap early suites and fails on a policy branch
    # rather than on machine state. No apostrophes and no quoted words in
    # this comment: the docs suite parses this block with quote tracking,
    # and both a possessive and a quoted phrase here have each become a
    # phantom suite name once.
    "test_bm_session_cap.py",
    # C-06 (closure register): builds a real wheel, installs it into a
    # throwaway venv, and invokes every console script pyproject.toml
    # declares, the exact adversarial test the register names. Runs near
    # the end of the fast suites because it needs network egress once (to
    # upgrade pip inside its own throwaway venv) and takes real seconds
    # rather than a fraction of one; it reports SKIPPED rather than
    # failing red when that egress is not available, so an offline
    # machine still gets ALL GREEN rather than a false alarm.
    "test_bm_packaging_install.py",
    # The plugin path install suite (N-3 / B-3, 2026-08-04): drives the real
    # claude CLI through marketplace add, install, uninstall and marketplace
    # remove, against a throwaway copy of the tree. Placed with the other
    # environment dependent suites at the end: class B and class C need a
    # claude binary on PATH and skip without one, but class A always runs.
    "test_bm_plugin_install.py",
    # tools/brothermode_cli.py, the one deterministic public runtime
    # boundary named in V3-FREEZE-2026-08-07.md answer 4: a thin dispatch
    # layer over tools/bm_project.py, tools/bm_lead.py, tools/bm_view.py,
    # scripts/doctor.py, tools/bm_autosave.py and scripts/install.py. NO
    # APOSTROPHE ANYWHERE IN THIS COMMENT, ON PURPOSE (see the file level
    # note above). Placed right before the largest suite, after every
    # adapter it wraps has already proven sound in its own suite above:
    # the load bearing test in this suite runs its own status subcommand
    # and the real bm_lead.py status side by side as two subprocesses and
    # diffs their stdout byte for byte, so the adapters must already be
    # trustworthy before this suite can say anything meaningful about the
    # boundary in front of them.
    "test_brothermode_cli.py",
    "test_bm.py",
)

# unittest writes its summary to stderr. Both shapes appear in real output:
#   "Ran 244 tests in 7.452s"
#   "OK (skipped=2)"  /  "FAILED (failures=1, errors=2)"
_RAN_RE = re.compile(r"^Ran (\d+) tests? in ([\d.]+)s", re.M)
_SKIP_RE = re.compile(r"skipped=(\d+)")


# -- interprocess gate lock -------------------------------------------------
#
# The lock is keyed to THIS checkout, not to the machine: two worktrees exercise
# their OWN copy of the tools, so they cannot corrupt each other and must not
# block each other either. It lives in the system temp directory rather than in
# the repo so it never shows up in git status.

LOCK_ENV = "BROTHERMODE_TEST_GATE_LOCK"
LOCK_TIMEOUT = float(os.environ.get("BROTHERMODE_TEST_LOCK_TIMEOUT", "900"))
# AGE IS THE FALLBACK, NOT THE TEST (fix round, 2026-07-29). This used to be
# 3600s and was consulted BEFORE the holder's liveness, so a run that had been
# going for an hour and one second was declared dead and had its lock taken
# from underneath it. 3600s was not even longer than a legitimate run: the
# default 900s timeout times four suites is exactly 3600s, and the CI gate job
# passes --timeout 1200, so up to 4800s. Now liveness decides wherever a pid
# can be probed, and this threshold only applies where it cannot (Windows, or
# an unparseable holder record). 24 hours is longer than any run that is not
# already abandoned.
LOCK_STALE_SECONDS = 86400.0

# Paths this process actually holds, mapped to the exact bytes it wrote. A
# release must never remove a lock file this process did not take: if its own
# lock was stolen while it ran, deleting the thief's file lets a THIRD run in.
_HELD = {}


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
    is a lock being taken RIGHT NOW, not a dead one, so it falls back to age.

    LIVENESS IS CHECKED FIRST, AND IT WINS. A process that answers os.kill(pid,
    0) is running, and a running gate is not stale no matter how long it has
    been running. Age is only consulted where the pid cannot be probed."""
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
    if os.name == "posix" and pid > 0:
        try:
            os.kill(pid, 0)
        except OSError as exc:
            # ESRCH means no such process, which is the ONLY provably gone
            # case. EPERM means it exists and is not ours, which is alive.
            return exc.errno == errno.ESRCH
        # Alive. Not stale, however old. A slow gate is not a dead one.
        return False
    return (time.time() - stamp) > LOCK_STALE_SECONDS


def acquire_gate_lock(timeout=None, owner="test_all", quiet=False):
    """Take the checkout-wide test lock. Returns a handle, or None when an
    ancestor process already holds it (test_all running a suite as a child), in
    which case there is nothing to take and nothing to release."""
    path = lock_path()
    inherited = os.environ.get(LOCK_ENV)
    if inherited:
        if inherited == path and os.path.exists(path):
            return None
        # Any other value cannot mean "an ancestor holds this checkout's
        # lock". Treating it as if it did turned one exported environment
        # variable into a silent, unannounced disabling of the only mutual
        # exclusion the suites have. Say so, then take the lock properly.
        if not quiet:
            sys.stderr.write(
                "test_all: ignoring %s=%r: it does not name this checkout's "
                "live gate lock (%s), so it cannot mean an ancestor holds it. "
                "Taking the lock normally.\n" % (LOCK_ENV, inherited, path))
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
                    "another test run holds %s (%s). The suites share this one "
                    "checkout and its temp and git state, so two at once "
                    "produce flakes nobody can reproduce. Wait for it, or "
                    "delete that file if you are sure the holder is dead."
                    % (path, _lock_holder(path)))
            if not announced and not quiet:
                sys.stderr.write(
                    "test_all: waiting for another test run to finish: %s\n"
                    % _lock_holder(path))
                announced = True
            time.sleep(0.25)
            continue
        token = "%d %.3f %s\n" % (os.getpid(), time.time(), owner)
        with os.fdopen(fd, "w") as fh:
            fh.write(token)
        _HELD[path] = token
        # Children inherit this, which is how a suite launched BY this runner
        # knows the lock is already held rather than deadlocking against it.
        os.environ[LOCK_ENV] = path
        return path


def release_gate_lock(handle, quiet=False):
    """Give up a lock THIS process took. Never removes a lock file whose
    contents are not the ones this process wrote: if the lock was stolen (a
    stale-detection mistake, or somebody deleting the file by hand), the file
    now on disk belongs to another run, and removing it would admit a third."""
    if not handle:
        return
    token = _HELD.pop(handle, None)
    if os.environ.get(LOCK_ENV) == handle:
        os.environ.pop(LOCK_ENV, None)
    if token is None:
        if not quiet:
            sys.stderr.write(
                "test_all: NOT removing %s: this process never took it.\n"
                % handle)
        return
    try:
        with io.open(handle, encoding="utf-8", errors="replace") as fh:
            current = fh.read()
    except (IOError, OSError):
        return
    if current != token:
        if not quiet:
            sys.stderr.write(
                "test_all: NOT removing %s: it is held by another run now "
                "(%s), so this run's lock was taken from it while it ran. "
                "Report this: it means two gates may have overlapped.\n"
                % (handle, current.strip()))
        return
    try:
        os.remove(handle)
    except OSError:
        pass


# -- CI inventory ------------------------------------------------------------
#
# WHY THIS IS NOT A regex OVER THE WHOLE FILE (fix round, 2026-07-29)
#   It used to be. re.findall over the raw workflow text answers "is this
#   filename MENTIONED", and the check needs "is this suite RUN". Four
#   mutations were reproduced against the old version and all four were
#   reported as agreement: commenting the step out, adding `if: false` to it,
#   replacing its command with `echo TODO <path>`, and (the reverse direction)
#   a prose comment naming a deleted suite, which hard blocked the whole gate
#   at exit 2 with zero tests run. The workflow already leaned on the
#   looseness: tools/test_all.py was matched from a comment.
#
#   So this reads the workflow as the small, specific structure GitHub Actions
#   actually uses (steps, each a mapping with `run:` and maybe `if:`) and
#   counts a suite only when a real shell command executes it through a Python
#   interpreter. It is deliberately NOT a general YAML parser: stdlib only, no
#   PyYAML, and a parser this file cannot fully implement is a parser nobody
#   should trust. Every place it gives up, it gives up by NOT counting the
#   suite as covered, which fails closed (the gate refuses) rather than open
#   (a suite silently untested).

_CI_SUITE_RE = re.compile(r"tools/(test_[A-Za-z0-9_]+\.py)")
# A python interpreter as the command word: python, python3, py, or a path
# ending in one of those.
_PYTHON_RE = re.compile(r"(?:^|[\s;&|(=])(?:[\w./\\:-]*[/\\])?py(?:thon3?)?"
                        r"(?:\.exe)?(?:\s|$)")
# Command separators inside one `run:` body. Each segment is judged on its own,
# so a suite named in a different command than the interpreter does not count.
_SEGMENT_RE = re.compile(r"[\n;]|&&|\|\||\|")
_FALSE_IF_RE = re.compile(
    r"^(?:false|'false'|\"false\"|\$\{\{\s*false\s*\}\})$", re.I)
# YAML block scalar headers: |, >, |-, >+, |2 and so on.
_BLOCK_RE = re.compile(r"^[|>][+-]?\d*$")


def _strip_comment(line):
    """Drop a trailing comment, respecting quotes. Serves double duty: a YAML
    comment outside a block scalar and a shell comment inside one both start at
    a '#' that begins the line or follows whitespace. Dropping either can only
    REMOVE a mention, never invent one, so the worst case is a refusal."""
    quote = None
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            return line[:i].rstrip()
    return line


def _ci_steps(text):
    """Every step block under a `steps:` key, as raw text. Comment-only lines
    are already gone, which is the point: a commented-out step is not a step."""
    blocks = []
    cur = None
    steps_indent = None
    for raw in text.splitlines():
        line = _strip_comment(raw.rstrip())
        if not line.strip():
            if cur is not None:
                cur.append(line)
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if steps_indent is not None:
            closed = indent < steps_indent or (
                indent == steps_indent and not stripped.startswith("-"))
            if closed:
                if cur is not None:
                    blocks.append("\n".join(cur))
                    cur = None
                steps_indent = None
        if stripped == "steps:":
            steps_indent = indent
            continue
        if steps_indent is None:
            continue
        if stripped == "-" or stripped.startswith("- "):
            if cur is not None:
                blocks.append("\n".join(cur))
            cur = [line]
        elif cur is not None:
            cur.append(line)
    if cur is not None:
        blocks.append("\n".join(cur))
    return blocks


def _step_field(block, key):
    """One top-level field of a step mapping, or None. Handles both an inline
    scalar (run: python3 x.py) and a block scalar (run: | plus indented lines).
    A nested mapping (a `with:` body) sits below the key indent and is
    therefore never mistaken for a sibling field."""
    lines = block.split("\n")
    first = lines[0]
    lead = len(first) - len(first.lstrip())
    key_indent = lead + 2
    head = first.strip()
    if head.startswith("- "):
        norm = [" " * key_indent + head[2:]]
    elif head == "-":
        norm = [""]
    else:
        norm = [first]
    norm.extend(lines[1:])
    for idx, line in enumerate(norm):
        if not line.strip():
            continue
        if (len(line) - len(line.lstrip())) != key_indent:
            continue
        stripped = line.strip()
        if not stripped.startswith(key + ":"):
            continue
        value = stripped[len(key) + 1:].strip()
        if value and not _BLOCK_RE.match(value):
            return value
        body = []
        for nxt in norm[idx + 1:]:
            if not nxt.strip():
                body.append("")
                continue
            if (len(nxt) - len(nxt.lstrip())) <= key_indent:
                break
            body.append(nxt.strip())
        return "\n".join(body)
    return None


def _ci_inventory():
    """Suites a CI step actually EXECUTES. None when there is no workflow file,
    which is the normal case for an extracted copy of the skill: an end user's
    checkout has no .github, and that must not be reported as a CI gap."""
    try:
        with io.open(WORKFLOW, encoding="utf-8") as fh:
            text = fh.read()
    except (IOError, OSError):
        return None
    executed = set()
    for block in _ci_steps(text):
        condition = _step_field(block, "if")
        if condition is not None and _FALSE_IF_RE.match(condition.strip()):
            # A step that can never run is not coverage. Any OTHER condition
            # (a platform guard, for instance) still counts: it runs on at
            # least one leg, which is more than zero.
            continue
        command = _step_field(block, "run")
        if not command:
            continue
        for segment in _SEGMENT_RE.split(command):
            if not _PYTHON_RE.search(segment):
                # `echo TODO tools/test_x.py` mentions a suite and runs
                # nothing. Only an interpreter invocation counts.
                continue
            executed.update(_CI_SUITE_RE.findall(segment))
    return executed


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


def _run_until_silent(path, silence_limit):
    """Run a suite, killing it only when it STOPS PRODUCING OUTPUT.

    CHANGED 2026-07-31, and the reason is the same one that produced two test
    fixes earlier the same day: a bare wall-clock budget measures the MACHINE,
    not the code. The old rule killed any suite whose TOTAL runtime passed the
    limit, so on a machine running six sessions a suite that normally takes 40
    to 90 seconds was killed at 907 seconds while its output showed tests still
    passing, on two different machines within an hour. A red that names no
    defect is worse than a slow green: it teaches the reader to re-run instead
    of to read.

    The distinction that fixes it: a HANG is a suite that stops progressing,
    and that is observable, while slowness is not a defect at all. unittest
    emits a line per test, so silence is the signal and elapsed time is noise.
    A genuinely wedged suite still trips this, at the same limit as before,
    because a wedged suite emits nothing.

    HOW THE LIMIT IS DERIVED, because the obvious next mistake is to lower it.
    Silence between lines is ONE TEST'S RUNTIME, and that is exactly as
    load-sensitive as the total was. Shortening this number reintroduces the
    same defect one level down: a test that takes 8s unloaded takes 400s at
    load 50, and a 60s or 120s limit would kill it and print STOPPED
    PROGRESSING just as wrongly as the old message did, only sooner and with
    more confidence.

    So the limit is: the slowest SINGLE test in the slowest suite, times the
    worst load multiple worth tolerating. Both halves are measured, not felt.
    Load multiples actually observed on 2026-07-31 with six sessions on one
    box: the store suite 12.4s to 584.5s (47x) and the docs suite 15s to 670.7s
    (45x). A 45x design margin is therefore ordinary here, not paranoid.

    900s is KEPT unchanged for that reason: it clears a 45x multiple on a 20s
    test. Nobody has yet measured the slowest single test, so nobody has earned
    the right to lower it. The cheap measurement when someone wants the real
    number: run one suite with -v on a QUIET machine and take the largest gap
    between consecutive test lines. That figure, times the multiple you choose
    on purpose, is the limit.

    Returns (ok, output, timed_out). Never raises for a suite that merely runs
    long. Reads incrementally on a thread so a suite writing a lot cannot fill
    the pipe buffer and deadlock, which plain Popen.wait() would allow."""
    proc = subprocess.Popen(
        [sys.executable, path], cwd=HERE,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        universal_newlines=True, bufsize=1)
    chunks = []
    last = [time.time()]

    def _pump():
        for line in iter(proc.stdout.readline, ""):
            chunks.append(line)
            last[0] = time.time()
        try:
            proc.stdout.close()
        except Exception:
            pass

    pump = threading.Thread(target=_pump)
    pump.daemon = True
    pump.start()
    timed_out = False
    while True:
        if proc.poll() is not None:
            break
        if time.time() - last[0] > silence_limit:
            timed_out = True
            proc.kill()
            break
        time.sleep(0.5)
    pump.join(timeout=10)
    try:
        proc.wait(timeout=10)
    except Exception:
        pass
    return (proc.returncode == 0 and not timed_out), "".join(chunks), timed_out


def _run_one(name, timeout=None):
    """Run one suite in its own process. Returns (ok, tests, skipped, seconds,
    tail, output). Never raises: a suite that cannot start at all, or hangs, is
    a RESULT reported with its reason, not an exception that hides the rest."""
    path = os.path.join(HERE, name)
    if timeout is None:
        timeout = DEFAULT_TIMEOUT
    started = time.time()
    try:
        ok_run, partial, timed_out = _run_until_silent(path, timeout)
    except OSError as exc:
        return (False, 0, 0, time.time() - started,
                "could not start: %s" % exc, "could not start: %s" % exc)
    if timed_out:
        # A hung suite used to hang the gate. Report it as a timeout, keep the
        # partial output (it names the last test that started, which is almost
        # always the one that wedged), and carry on with the other suites.
        elapsed = time.time() - started
        lines = [ln for ln in partial.splitlines() if ln.strip()]
        tail = ("STOPPED PROGRESSING: no output for %.0fs (limit %.0fs), killed "
                "after %.0fs total. Last output: %s"
                % (timeout, timeout, elapsed,
                   " | ".join(lines[-3:]) if lines else "(none)"))
        return False, 0, 0, elapsed, tail, partial + "\n" + tail + "\n"
    class _P(object):
        pass
    proc = _P()
    proc.stdout = partial
    proc.returncode = 0 if ok_run else 1
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


def _worktree_dirt():
    """Tracked paths the suites modified, as (paths, skip_reason). Exactly one
    of the two is ever truthy: a reason means the question could not be asked,
    which is never the same answer as "nothing changed"."""
    if not os.path.isdir(os.path.join(REPO, ".git")):
        return [], "this checkout has no .git directory"
    try:
        r = subprocess.run(
            ["git", "-C", REPO, "status", "--porcelain", "--untracked-files=no"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, timeout=30,
            # git honours GIT_DIR and GIT_WORK_TREE over -C, so an inherited
            # pair would have this report another repository's tree.
            env={k: v for k, v in os.environ.items()
                 if not k.startswith("GIT_")})
    except (OSError, subprocess.SubprocessError) as exc:
        return [], "git could not be run here (%s)" % exc
    if r.returncode != 0:
        return [], "git status exited %d here" % r.returncode
    return sorted(ln[3:].strip() for ln in r.stdout.splitlines() if ln.strip()), ""


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
    dirty, dirt_skip = _worktree_dirt()
    if dirt_skip:
        sys.stdout.write("test_all: the clean-checkout check is SKIPPED, %s. A "
                         "SKIP is not a pass: nothing here proves the suites "
                         "left this tree alone.\n" % dirt_skip)
    elif dirty:
        failed = failed + [("clean-checkout", False, 0, 0, 0.0,
                            "the suites modified tracked files")]
        sys.stdout.write(
            "test_all: REFUSING to report green. The suites left these tracked "
            "paths modified: %s. A suite that writes into this checkout "
            "invalidates CHECKSUMS.sha256, so scripts/verify-install.sh then "
            "tells the user their install may be tampered with, and "
            "scripts/doctor.py SKIPS its integrity check on any dirty tree, "
            "which is the documented quickstart order. Write the artifact "
            "outside the tree, or behind an opt-in environment variable, the "
            "way tools/test_bm_controller.py does for the E4 evidence.\n"
            % ", ".join(dirty))
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
