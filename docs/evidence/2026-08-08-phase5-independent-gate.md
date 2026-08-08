# Phase 5, the independent gate that carried the merge

Status: CURRENT. This is an evidence record of a run that happened, so it stays
true as written; it is superseded only by a later gate on a later tree.

Date: 2026-08-08. Recorded by relay session `5f7fcde6`, which wrote none of the
code it gated. Branch under test: `phase-5/progress-view` at `0195784`. Merged
after this run as `8f3980b` through pull request 22.

No em or en dashes anywhere in this document.

## Why a second gate existed at all

The handover packet named one thing as the item that could not wait: the full
gate had never completed on this branch. Three earlier attempts had produced no
usable result. One came back red, and its three failing suites were diagnosed as
one real regression (since fixed in `d94c42b`) plus two load flakes. One was
killed at exit 144 partway through. One finished green under orchestrator
session `28ac90ad`, at 588.7s wall with load rising from 6.82 to 8.17.

That third run is a real green and is not disputed here. This document records a
second, independent one, run by a session with no authorship stake in the code,
on a machine that was quiet rather than climbing. Both are on the record.

## The waiting, which is part of the evidence

Another session's suite held the machine when this relay picked up the baton.
Rather than run a third concurrent suite, this gate waited 675 seconds for that
process to exit and started only afterwards. The project's own known-mistakes
ledger opens with the rule that a gate run on a moving or loaded tree is not a
result, and the day had already spent an afternoon proving it.

## The run, verbatim

    running test_bm_hookperf.py      OK     19 tests   12.1s
    running test_brothermode_cli.py  OK     26 tests    9.6s
    running test_bm.py               OK    279 tests   45.4s

    test_all: the clean-checkout check is SKIPPED, this checkout has no .git directory. A SKIP is not a pass: nothing here proves the suites left this tree alone.
    test_all: 2748 tests across 26 suites, 2 skipped, 476.6s wall. ALL GREEN
    EXIT=0

Load average at both ends, falling rather than rising:

    LOAD-START 13:39:55  load averages: 4.60 6.08 6.36
    LOAD-END   13:47:51  load averages: 3.08 4.65 5.63

## Two caveats stated rather than left to be inferred

1. The gate skipped its own clean-checkout check, and said so, because a linked
   worktree has a `.git` file and not a `.git` directory. A skip is not a pass,
   so the check was replaced by hand: `git status --porcelain` was empty both
   immediately before and immediately after the run, which is the property that
   check exists to establish.
2. `test_bm_hookperf.py` is the known load-flaky suite. It passed INSIDE this
   gate, at 19 tests in 12.1s, not merely alone afterwards. Nothing about it was
   waived, skipped, or re-run to obtain that line.

The push gate is separate and was already satisfied by the manifest rebuild in
`0195784`: `prepush-check: PASSED: the committed manifest describes the
committed tree. Safe to push.`

## What merging cleared, verified rather than assumed

This branch carried the store from schema 17 to schema 18. While it sat
unmerged, every other lane read a store its own code was too old to open and was
refused a fence with "schema-ahead", correctly and by design. Relays 4 and 5
both worked without a store fence and said so.

After the merge, checked from a fresh worktree off merged main:

- `tools/bm_store.py` on main carries `SCHEMA_VERSION = 18`.
- `python3 tools/brothermode_cli.py status --project-id v3-finalization` opens
  the live store and prints this program's own state, with no schema-ahead
  refusal: `Progress: 12 of 25 tasks accepted`.

## The finding this run surfaced, which is NOT a Phase 5 regression

The GitHub Actions checks on pull request 22 are red: the `gate` job and the
four `suite` jobs on ubuntu and macos. The failure is identical on main and
predates this branch:

    tools/test_brothermode_cli.py, line 254, in test_doctor_json_flag_forwards
    AssertionError: Lists differ: [1, 4, 10] != [9]
    doctor may only be red mid-train on the manifest check; any other FAIL is real: [1, 4, 10]

Same assertion, same line, same five jobs, on main at `17b777b` (run
31232249169) and on the v3.0.0 tag commit `d485699` (run 31228116121). The last
green run on main was `5acd22e` (run 31192433783), so this entered between
`5acd22e` and `d485699`.

On a GitHub runner, `doctor` reports checks 1, 4 and 10 failing, while the test
tolerates only check 9 (the manifest check) being red mid-train. The same test
passes on this machine, so the cause is environmental rather than a logic
regression. Which three checks those are, and why the runner differs, is
undiagnosed. It belongs to main, not to Phase 5, and it is the top open item.
