# The GitHub Actions red on main, diagnosed and fixed

Date: 2026-08-08. Session: relay 7 of the v3 finalization program.
Branch: `relay7/ci-doctor-fix`, worktree `.claude/worktrees/relay7-ci-doctor`.

## What was red

Every GitHub Actions run on `main` since the v3.0.0 release identity commit,
across all five jobs (gate, plus suite on ubuntu and macos), failed the same
single assertion:

```
FAIL: test_doctor_json_flag_forwards (__main__.TestDoctorIsByteIdenticalToDirectScript)
  File "/home/runner/work/BrotherModeUp/BrotherModeUp/tools/test_brothermode_cli.py", line 254, in test_doctor_json_flag_forwards
    self.assertEqual(failing, [9],
AssertionError: Lists differ: [1, 4, 10] != [9]
- [1, 4, 10]
+ [9] : doctor may only be red mid-train on the manifest check; any other FAIL is real: [1, 4, 10]
```

Read from `gh api repos/khalilmaaouni/BrotherModeUp/actions/jobs/93058015383/logs`.
It passed on the founder's machine every time, so it was environment
dependent rather than a logic regression.

## What checks 1, 4 and 10 are

The ids are 1-based positions in the pinned list `run_all_checks` returns
(`scripts/doctor.py:928`). Named, they are:

| id | key | title |
|----|-----|-------|
| 1 | fence | the write fence is wired and actually denies a foreign write |
| 4 | consent | setup has been completed |
| 10 | settings_json | settings.json is valid JSON |

## Why a hosted runner fails them and this machine does not

All three are facts about whether BrotherMode is INSTALLED, not about the
code under test:

- **1 fence** calls `doctor(settings_path)`, which needs hooks wired into
  `~/.claude/settings.json` to prove a foreign write is denied.
- **4 consent** reads the setup config and fails when
  `scripts/setup.py` has never been run.
- **10 settings_json** fails at `read_settings`, whose first branch is
  "no settings file at ~/.claude/settings.json".

A GitHub hosted runner checks the repository out and runs the suite. It
never runs `scripts/install.py` or `scripts/setup.py`, so there is no
settings file and no completed setup, and all three report that truthfully.
The founder's machine has a completed install, so all three PASS there and
only check 9 (checksums) can legitimately go red mid-train.

Reproduced locally before any edit, which is what turned a hypothesis into
a finding:

```
$ FAKEHOME=$(mktemp -d) && HOME="$FAKEHOME" python3 scripts/doctor.py --json | ...
1 fence FAIL
2 version PASS
3 runtime PASS
4 consent FAIL
5 vault SKIP
6 duplicate_install SKIP
7 store FAIL
8 mode_wiring SKIP
9 checksums SKIP
10 settings_json FAIL
```

(Check 7 store additionally fails under a redirected HOME, which is an
artifact of that redirection and not of CI; CI's store is created fresh
under the runner's own home. Checks 1, 4 and 10 reproduce exactly.)

## When it entered

Commit `6edd19d`, "2026-08-08 Unpin the doctor test from push-boundary
state, keep every real FAIL fatal", inside the bisect range relay 6
established (last green `5acd22e`, red by `d485699`). That commit correctly
stopped pinning doctor to exit 0, but replaced the pin with an assertion on
WHICH checks may fail, which is the same environment dependence in a
different shape.

## The call: the test was wrong, not the code

doctor is behaving correctly. Reporting FAIL for fence, consent and
settings_json on a machine with no install is doctor telling the exact
truth, and it is the whole point of a doctor command. Changing doctor to
soften those into SKIPs would make it lie about real installs, where those
same three failures are exactly what a user needs told.

The defect is that `test_doctor_json_flag_forwards` asserted doctor's
verdict while its own comment stated it existed to prove the `--json` flag
FORWARDS. A verdict is a property of the host; forwarding is a property of
the wrapper.

## The fix

Two changes in `tools/test_brothermode_cli.py`, no assertion weakened or
deleted:

1. `test_doctor_json_flag_forwards` now proves forwarding differentially:
   the wrapper's `doctor --json` return code and stdout must equal the
   direct `scripts/doctor.py --json` run, and the payload must carry ten
   checks. This is environment-independent by construction, since both
   sides run in the same environment, and it is a strictly stronger proof
   of forwarding than the old exit-code check.
2. The install-health guard moves, word for word including its failure
   message, into a new test
   `test_doctor_reports_only_expected_failures_on_a_real_install`, which
   first asks doctor whether this machine has a completed install and
   skips, naming the check that proved it, when it does not.

No coverage is lost. CI never verified install health and never could,
because CI has no install; it only produced a false red.

## Done-check, run after the last edit

```
$ python3 tools/test_brothermode_cli.py
Ran 27 tests in 8.331s
OK
```

Under the hosted-runner condition, which is the failure this fixes:

```
$ FAKEHOME=$(mktemp -d) && HOME="$FAKEHOME" python3 tools/test_brothermode_cli.py TestDoctorIsByteIdenticalToDirectScript -v
test_doctor_json_flag_forwards ... ok
test_doctor_reports_only_expected_failures_on_a_real_install ... skipped "BrotherMode is not installed on this machine (doctor's consent check says 'FAIL'), so there is no install for this check to report on."
test_doctor_stdout_is_byte_identical ... ok
Ran 3 tests in 0.288s
OK (skipped=1)
```

Load average at the time of the full-file run: 3.08 (1 minute).

## What this does NOT prove, stated so it is not assumed

- The full gate (`tools/test_all.py`) was not re-run in this session. The
  file this change touches was run in full and is green; the rest of the
  suite is unchanged by this commit and was last proven green by relay 6
  at `8f3980b`.
- Green CI on the pull request is the real confirmation, and it had not
  reported yet when this document was written.
- Nothing here verifies install health ON a hosted runner. It cannot be
  verified there without installing BrotherMode in CI first, which is a
  separate decision with its own consequences and is listed as an open
  option rather than taken.
