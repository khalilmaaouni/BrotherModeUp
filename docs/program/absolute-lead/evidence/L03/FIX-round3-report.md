# FIX round 3: closing REFUTATION-2 against the L03 controller

Target tree: /Users/khalil.maaouni/Documents/BrotherModeUp
Input report: docs/program/absolute-lead/evidence/L03/REFUTATION-2-fixes.md
RED evidence: docs/program/absolute-lead/evidence/L03/RED-round3-refutation2-tests.txt
Files written: tools/bm_controller.py, tools/bm_store.py,
tools/test_bm_controller.py, tools/test_bm_store.py, docs/FULL-AUTO.md,
docs/KNOWN-LIMITS.md, and this report. Nothing else. No git state was
changed, no checksums regenerated, tools/test_all.py never run.

One further file shows as modified and was NOT edited by hand:
docs/program/absolute-lead/evidence/L03/E4-endtoend.json, which
TestEndToEndE4 regenerates on every run of tools/test_bm_controller.py by
its own documented design (it is the latest run's evidence, not a golden
file). Running the required done-check rewrites it; nothing else can.

Method: every reproduction in the input report was written as a test
FIRST, run against the untouched tree, and its failure captured to the RED
file above (two labelled blocks, 13 controller tests and 3 store tests,
9 failures and 8 errors between them). Only then was production code
touched. The four F-class tests from round 2 and the 45 pre-existing
controller tests were treated as law throughout; none was weakened, and no
collision with any of them arose.

---

## F1: the late result, and the sibling path

### What was wrong

`receive_result` walked CHECKPOINTED and WAITING_HUMAN to EXECUTING and
assumed every other state could be judged from. Four could not, and the
store refused the FAILED_TERMINAL move out of them, which aborted the call
BEFORE the founder was warned about a dirty write scope and BEFORE the
fence was released. `check_timeouts` did not walk at all.

### What changed

**tools/bm_controller.py:212-301 (new module-level derivation).**
`_RESULT_WALK_EDGES` states the engine's own walk as DATA;
`_REJECTABLE_STATES` is derived from `bs.CONTROLLER_STATE_TRANSITIONS`
(the states FAILED_TERMINAL is legal from); `_walk_reaches_rejectable`
walks those edges; `_RESULT_WALKABLE_STATES` is the resulting set
(READY, EXECUTING, VERIFYING, CHECKPOINTED, WAITING_HUMAN,
FAILED_RECOVERABLE). An import-time check raises RuntimeError if any walk
edge is not in the store's own table, so a future widening of the walk
cannot silently disagree with the law. The store law was NOT widened.

**tools/bm_controller.py:589-616 (`receive_result`).** After
`record_result`, the run state is read; anything outside
`_RESULT_WALKABLE_STATES` returns through `_handle_late_result` and no
state move is attempted.

**tools/bm_controller.py:662-724 (`_handle_late_result`, new).** In order:
record the verification (dispatch ends REJECTED), record the rejection
(`mark_unit_failed`), and when that returns the unit to READY, pair
`queue_human_step` with `block_lane_units` so the unit ends BLOCKED
instead of selectable; run the rollback and warn the founder if it left
the scope dirty; park the fence; record an interruption naming the late
result and the run state. The run state is the one thing left untouched.
This is what closes reproduction 1's secondary observation (a STOPPED run
gaining a READY unit) and reproduction 2's second dispatch.

**tools/bm_controller.py:725-788 (`check_timeouts`, walk at 767-775, settle at 786-787).** Now
performs the same state read, routes an unwalkable state to
`_handle_late_result`, otherwise walks `_walk_to_executing` then
`_ensure_verifying` before `record_verification` and `_reject`, and calls
`_settle_after_wave` once after the loop so the run converges along legal
edges instead of being left in EXECUTING.

**tools/bm_controller.py:1214-1292 (`_reject` at 1214, `_warn_dirty_write_scope` at 1268, `_record_interruption` at 1279).** Consequence order on the
dirty-rollback branch is now: founder warning, fence park, THEN the state
move, and the move is attempted only when
`CONTROLLER_STATE_TRANSITIONS` allows FAILED_TERMINAL from wherever the
run actually stands; when it does not, the halt is recorded as an
interruption instead. No illegal move can swallow the warning or the
release any more. Two helpers were extracted:
`_warn_dirty_write_scope` (one wording for both paths) and
`_record_interruption` (skips when the contract is not live, because
`Store.record_interruption` refuses there and that refusal must not be
able to destroy work already recorded).

**tools/bm_controller.py:1556-1600 (`_deliver_or_hold`, the legal-edge guard at 1585).** The
converge-before-delivery move is attempted only when READY is legal from
the current state; otherwise the summary says so and the run stays put.
This is the exact line the report's probe_f1c raised on.

### Evidence

`TestR2F1LateResultOnARunStateThatCannotReachVerifying` (4 tests:
reproduction 1 dirty, reproduction 1 clean, reproduction 2, and the
four red rows of the state matrix as subtests) and
`TestR2F1CheckTimeoutsWalksTheSameStatesAsReceiveResult` (2 tests:
probe_f1b and probe_f1c). probe_f1c now ends DELIVERABLE_READY with zero
exceptions.

---

## F2: one revision for the whole scope, and containment instead of overlap

### Every caller of gate_check, grepped before changing it

Production callers (2):

- tools/bm_autonomy.py:527, `cmd_gate_check`, the founder-facing
  `bm-autonomy gate-check` command. Narrows with this change, which is the
  point of the change.
- tools/bm_controller.py:995 (inside `_gate_check_one_pass`), the
  controller's per-path dispatch precondition.

Definition and delegation (2): tools/bm_store.py:12554 (`Store.gate_check`)
and tools/bm_store.py:13697 (`ReadOnlyStore.gate_check`, a pass-through).

Test callers (4 files): tools/test_bm_controller.py:349 and the F2
classes; tools/test_bm_store.py (15459, 15466, 15484, 15487, 15506,
15536, 15538, 15549, 15581, 15591, 15605, 15607, 15721, 15757, 15773,
15793, 15899, plus the new class); tools/test_bm_autonomy.py (235, 636,
657, 728, all through the CLI). Every one of them still passes.

Documentation mentions (no call): references/autonomy.md, docs/AUTONOMY.md,
docs/FULL-AUTO.md, docs/KNOWN-LIMITS.md, two L02 evidence pages, one
design spec.

### What changed

**tools/bm_store.py:564-603 (`path_within_allowed`, new).** Containment,
one-directional: equal to an allowed path, or strictly under it at a
separator boundary. `.` on the allowed side still contains everything;
`.` as the checked path is contained only by `.` itself. A glob on the
allowed side reduces to its coverage key (unchanged behaviour for
`api/*.py`); the candidate side is never reduced. `paths_overlap` is
untouched and keeps its symmetric fence semantics.

**tools/bm_store.py:12573-12580 (`gate_check` docstring, check 5) and
:12626-12627 (the comparison itself).** The docstring now states the
property the code actually enforces: a path this check ALLOWS can never
name a file that a directly named path would be REFUSED for.

**tools/bm_controller.py:902-1003 (`_gate_check_write_scope` at 902, the new
`_gate_check_one_pass` at 984).** One pass captures the FIRST verdict's revision
and reports `straddled` when any later verdict comes back under a
different one, checked BEFORE the ALLOWED check. A straddle re-runs the
whole loop once against the newer contract; a second straddle returns
this file's own `_DEFERRED_CONTENTION` verdict.
**tools/bm_controller.py:1005-1027 (`_claim_and_dispatch`, the deferral at 1020)** treats that
verdict as a deferral: no drain, no `mark_unit_failed`, no retry burned,
the unit is tried again next wave. The revision returned on a
non-straddled pass is by construction the revision every path was judged
under, and that is what is stamped on the dispatch.

The docstrings of both `_gate_check_write_scope` and `Store.gate_check`
now state the property in the form the code enforces, which was the
report's specific complaint about a reader believing otherwise.

### Evidence

`TestR2F2TheRevisionEveryPathWasJudgedUnder` (3 tests: the straddle with a
concurrent supersede amend fired from inside the first gate_check call,
the double straddle deferral, and the ancestor widening at controller
level) and `TestGateCheckPathIsContainmentNotOverlap` in
tools/test_bm_store.py (3 tests: the ancestor matrix from
probe_f2b_ancestor_scope, the whole-root contract, and a no-regression
check on the sibling-prefix boundary).

---

## F4: dead dependencies, founder-waiting lanes, and the spin

**tools/bm_controller.py:294-300 (`_DEAD_DEPENDENCY_STATUSES`) and
:1467-1554 (`_block_unreachable_units`, the dead-status test at 1515).** SKIPPED is now as dead as
FAILED, and the founder step names the dead unit AND its status, with the
right instruction for each ("its retry ceiling is exhausted" against "a
re-plan dropped it from the unit graph").

**tools/bm_controller.py:1403-1466 (`_handle_no_ready_units` at 1403, the new
`_is_founder_waiting` at 1454).** The whole-run judgement is now by
selectability, not status alone: a non-terminal unit is founder-waiting
when it is BLOCKED, or when it is PENDING/READY in a lane holding an open
human step. Work that is genuinely in flight is never founder-waiting.
When every non-terminal unit is founder-waiting the run moves to
WAITING_HUMAN, which also closes the report's case D.

**tools/bm_controller.py:538-587 (`run_to_completion` at 538, the new
`_anything_in_flight` at 574).** A pass that dispatched nothing, completed
nothing, moved the run state nowhere and wrote one of the two named
no-progress notes, with no open dispatch, ends the loop and returns the
current trace with the note extended to say the run is parked. The two
notes are now module constants (`_NOTHING_SELECTABLE_NOTE`,
`_NOTHING_CLAIMABLE_NOTE`) so the producer and this consumer cannot drift.

### Evidence

`TestR2F4DeadDependenciesAndFounderGatedLanes` (4 tests: the SKIPPED
dependency from probe_f4c, case C, case D, and the no-progress stop
driven by an unrelated fence holding the unit's file).

---

## Done-check, run after the last edit

```
$ cd /Users/khalil.maaouni/Documents/BrotherModeUp
$ python3 tools/test_bm_controller.py
python3 tools/test_bm_controller.py exit=0
----------------------------------------------------------------------
Ran 58 tests in 13.008s

OK
```

```
$ cd /Users/khalil.maaouni/Documents/BrotherModeUp/tools
$ python3 test_bm_store.py
python3 tools/test_bm_store.py exit=0
----------------------------------------------------------------------
Ran 820 tests in 34.337s

OK
```

```
$ cd /Users/khalil.maaouni/Documents/BrotherModeUp/tools
$ python3 -m unittest test_bm_controller.TestF1AsyncRejectWhoseRollbackAlsoFails \
    test_bm_controller.TestF2EveryWriteScopePathIsGateChecked \
    test_bm_controller.TestF3AsyncSpendAfterARevoke \
    test_bm_controller.TestF4DependentOfAFailedUnitDoesNotStallTheRun \
    test_bm_controller.TestR2F1LateResultOnARunStateThatCannotReachVerifying \
    test_bm_controller.TestR2F1CheckTimeoutsWalksTheSameStatesAsReceiveResult \
    test_bm_controller.TestR2F2TheRevisionEveryPathWasJudgedUnder \
    test_bm_controller.TestR2F4DeadDependenciesAndFounderGatedLanes \
    test_bm_store.TestGateCheckPathIsContainmentNotOverlap
unittest exit=0
----------------------------------------------------------------------
Ran 23 tests in 0.461s

OK
```

Two neighbouring suites were also run, unasked, because this change edits
a store primitive the founder-facing autonomy command consumes:

```
$ python3 test_bm_autonomy.py
Ran 58 tests in 43.219s

OK
```

```
$ python3 test_bm.py
OK (skipped=1)
```

Controller test count went from 45 to 58 (13 new), store from 817 to 820
(3 new). Warnings: none before, none after; no test file emits a warning
count in this repository, and no new compiler or runtime warning appeared
in any output above.

---

## What I could not close, and why

1. **tools/test_bm_docs.py fails on one file, and it is not mine.**
   `FAILED (failures=1)`, on
   `docs/evidence/2026-08-05-mirrorforge-source-program.md`: "marked
   historical but names nothing to read instead". That file is UNTRACKED
   in this working tree (`git status` shows `??`), predates this change,
   is outside my file fence, and is unrelated to L03. My own two doc edits
   (docs/FULL-AUTO.md, docs/KNOWN-LIMITS.md) pass every check in that
   suite. Recorded, not resolved.

2. **A glob in allowed_paths still authorises its literal prefix
   directory.** `allowed_paths ['api/*.py']` admits `api/notes.md`, because
   the allowed side reduces through `_coverage_key`, which is what
   `paths_overlap` already did and what keeps `api/pay.py` working. The
   mandate was the ancestor case; narrowing the glob case would change
   fence behaviour too and is a separate decision. Disclosed in
   docs/KNOWN-LIMITS.md.

3. **`_resume_result_in_and_orphans` was not routed to the late-result
   handler.** A crash mid-verification followed by a founder pause leaves
   a RESULT_IN dispatch that the resume branch judges from PAUSED. It can
   no longer RAISE (the `_reject` legal-move guard covers it, and
   `_settle_after_wave` returns early from PAUSED), but on a rejection it
   still re-queues the unit to READY, which for a PAUSED run is arguably
   correct (a pause is reversible) and for STOPPING is not. Out of the
   mandate, which named receive_result and check_timeouts. Flagged rather
   than changed.

4. **run_to_completion still spins under a soft spend stop with nothing in
   flight.** That pass writes the soft-stop note, not one of the two
   no-progress notes, so the new stop does not fire. It is a real spin, it
   is not in the input report, and widening the stop to that note is a
   behaviour decision I did not make on my own. Disclosed in
   docs/KNOWN-LIMITS.md.

5. **A test-harness artifact worth the orchestrator's attention, found
   while writing the RED tests.** tools/test_bm_controller.py loads
   bm_store INDEPENDENTLY of the load tools/bm_controller.py performs, so
   `bs.OwnershipRefused` in the test file is a DIFFERENT class from the one
   the engine catches. Any engine branch that CATCHES a store refusal (the
   fence-overlap deferral in `_claim_and_dispatch` is the only one today)
   cannot be exercised by a test whose store comes from the test file's own
   load: the exception escapes instead. My one test that needs that branch
   builds its store from `bc.bs` and says why in its docstring. The other
   57 tests are untouched; deciding whether the whole file should share one
   load is not my call.

6. **Not checked at all.** tools/test_all.py (suite lock, the
   orchestrator's gate). Real two-process SQLite contention: the F2
   straddle is still simulated by a delegating wrapper inside one process,
   exactly as the input report simulated it. The CLI was exercised as
   engine calls plus the pre-existing subprocess CLI tests, and no new CLI
   test was added, because no command surface changed.
