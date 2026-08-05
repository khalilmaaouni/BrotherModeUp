# FIX round 4, the CONTROLLER half: report

Writer: round-4 controller-half writer. Scope: every DESIGN-round4.md
section that is not store-side, namely 3, 4, 6, 7, 8.2 and 8.4 to 8.6, 9,
10, 11, the controller placement of 12.1 to 12.4, 13, the controller rows
of 14 and 15.1, the tools/test_bm_controller.py entries of 17.1, and the
migrations of section 18.

Files written, and nothing else:

* tools/bm_controller.py
* tools/test_bm_controller.py
* docs/FULL-AUTO.md
* docs/KNOWN-LIMITS.md
* docs/program/absolute-lead/evidence/L03/RED-round4-controller.txt
* this report

Not touched: tools/bm_store.py, tools/test_bm_store.py, docs/AUTONOMY.md,
references/autonomy.md, any checksum, any git state. tools/test_all.py was
NOT run.

---

## 0. READ THIS FIRST: three collisions, and the done-check is NOT DONE

`python3 tools/test_bm_controller.py` exits 1. 99 tests ran (58 existing
plus 41 new, no test deleted or lost). Three of them fail, and **all three
are existing tests the design predicted would need no change**. Per the
brief ("if you find a SEVENTH existing test needing a change beyond section
18's six, STOP on that item and record it, never edit it") and per section
18.8 itself, I did NOT edit any of them. All 41 new tests pass, and so do
the other 55 existing ones.

Each collision below is stated with the verbatim failure, why the design's
own behavioural sections force it, why I could not dodge it, and the
minimal remedy for whoever owns the decision.

### Collision 1: `TestFault8RestartWithNewerWorkflowVersion` (tools/test_bm_controller.py:689)

```
======================================================================
ERROR: test_reuses_unchanged_units_skips_dropped_ones_never_reruns_done (__main__.TestFault8RestartWithNewerWorkflowVersion)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_bm_controller.py", line 714, in test_reuses_unchanged_units_skips_dropped_ones_never_reruns_done
    engine1.step("p1")  # dispatches "keep" and "done_but_dropped"
  File "/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_controller.py", line 777, in step
    claimed, self.worker.run(claimed["brief"]), project_id,
  File "/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_bm_controller.py", line 221, in run
    script = self.scripts[unit_id]
KeyError: 'still_pending_dropped'
```

**What forces it.** The test makes an UNPAIRED `block_lane_units` call at
tools/test_bm_controller.py:712:

```python
                store.block_lane_units(run["run_id"], "never-selected",
                                       _actor())
```

with no `queue_human_step` in lane `never-selected`. Design section 8.4
makes BLOCKED a materialised view of "this lane holds an open founder
step", reconciled in BOTH directions on every wave, and section 18.4 states
the consequence explicitly: "an UNPAIRED `block_lane_units` call, with no
open step in that lane, is now reversed by the reconcile on the next wave.
That is the pairing law made executable." It then asserts "No test in
either suite makes an unpaired call." That last sentence is factually
wrong: this test makes one. So `_reconcile_lane_blocks` correctly unblocks
the lane, `still_pending_dropped` becomes selectable, and the test's
FakeWorker has no script for it, which is the very outcome the test's own
comment says must not happen ("it must never be dispatched in this test").

**Why I could not dodge it.** The only escape is to drop the unblock
direction of the reconcile, which is section 8.4's whole point, which
section 18.4 names, and which
`TestR3BlockedIsAMaterialisedViewOfTheLaneGate` (three of its four tests)
directly requires. There is no provenance column that could restrict the
unblock to lanes this engine blocked, and adding one is a schema-16
migration the design explicitly avoids (15.4).

**The minimal remedy** (it is not a weakening: it PAIRS the call, which is
what `block_lane_units`' own docstring says every call needs, and it makes
the test's intent, "never selected", true by the mechanism the store
actually enforces):

```python
                store.block_lane_units(run["run_id"], "never-selected",
                                       _actor())
                store.queue_human_step(
                    "p1", "", "never-selected",
                    "this lane is held for the founder in this test", "",
                    [], "sess1", _actor())
```

### Collision 2: `TestR2F1LateResultOnARunStateThatCannotReachVerifying.test_a_late_result_on_deliverable_ready_never_dispatches_a_second_time` (tools/test_bm_controller.py:1567)

```
======================================================================
ERROR: test_a_late_result_on_deliverable_ready_never_dispatches_a_second_time (__main__.TestR2F1LateResultOnARunStateThatCannotReachVerifying)
REFUTATION-2 F1 reproduction 2, all four steps shipped CLI
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_bm_controller.py", line 1598, in test_a_late_result_on_deliverable_ready_never_dispatches_a_second_time
    outcome = engine.receive_result(
  File "/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_controller.py", line 966, in receive_result
    self.store.record_result(
  File "/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_store.py", line 13396, in record_result
    raise OwnershipRefused(
bm_store.OwnershipRefused: dispatch '48c4c78ffa924c5dbcb5ba3a360202b8' is CANCELLED: a re-plan dropped unit 'u1' from the unit graph, so this dispatch was cancelled and the result cannot be recorded against it.
```

**This one was ALREADY RED before I touched anything.** It is caused by the
STORE half, which landed first: I recorded the baseline at the start of
this session, before my first edit, and it was `Ran 58 tests ... FAILED
(errors=1)` with exactly this error. It is in my report because it is a
controller-suite test and nobody else has reported it.

**What forces it.** The test drives a re-plan that drops `u1` and then
calls `receive_result` for `u1`'s still-open dispatch, expecting
`"rejected"`. Design section 8.1 closes the SKIPPED lifecycle at the
source: a dropped unit's open dispatch becomes CANCELLED in the same
transaction, and `record_result` refuses `'dispatch-cancelled'`. Design
17.1's own test plan states the required new behaviour in as many words:
"`receive_result` on it REFUSES 'dispatch-cancelled' (today it marks the
dropped unit DONE, LV finding 4)".

**Why I could not dodge it.** Catching the refusal inside `receive_result`
and routing it to `_handle_late_result` would restore exactly the behaviour
LV finding 4 refuted (a dropped unit's late answer being processed) and
would falsify the new test that pins the refusal.

**The remedy** is a supersession decision, not a one-line edit, because the
whole test asserts a behaviour the design replaces. The property it
protected ("a delivered run never re-dispatches the unit its late result
belonged to") is now enforced one layer earlier and is pinned by
`TestR3TheSkippedLifecycleClosesAtTheSource.test_a_result_for_a_cancelled_dispatch_refuses_instead_of_reviving_the_unit`
(tools/test_bm_controller.py:2623), which additionally asserts the founder's
drop stands and no meter is charged. Recommended: retire this test with a
docstring note pointing at its replacement, the same way section 18.1
retires the PAUSED row.

### Collision 3: `TestFault9ProviderOutageThenRecovery` (tools/test_bm_controller.py:767, asserting at line 786)

```
======================================================================
FAIL: test_dispatch_stays_open_across_the_outage_and_recovers_without_a_duplicate (__main__.TestFault9ProviderOutageThenRecovery)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_bm_controller.py", line 786, in test_dispatch_stays_open_across_the_outage_and_recovers_without_a_duplicate
    self.assertEqual(s1["state"], "EXECUTING")
AssertionError: 'FAILED_RECOVERABLE' != 'EXECUTING'
```

**What forces it.** Design 3.2's rule for `_finish`:
"`summary["state"] = self.store.get_run(project_id, raw=True)["state"]`,
unconditionally, last thing before returning". In round 3, `step()` assigned
`summary["state"]` BEFORE the worker loop and re-read it only on the
`any_recorded` branch. A worker answering `"unavailable"` records nothing,
so that re-read was skipped and the summary kept the stale `EXECUTING`
while the store already held `FAILED_RECOVERABLE`. The assertion at line
786 is asserting the stale value. It is SM E and LV 3 in miniature, inside
a test the design's section 18.6 cleared as needing "No change, verified
against the new control flow rather than assumed", having checked the line
numbers but not that the value at 786 was stale.

**Why I could not dodge it.** Keeping `s1["state"] == "EXECUTING"` requires
the summary to report a state the store does not hold, which is exactly
what law L2 exists to forbid and what
`TestR3TheSummaryStateIsTheStoreState` pins.

**The minimal one-line remedy** (strictly stronger: it pins the state the
store actually holds at return time, which is the whole point of the
funnel):

```python
                self.assertEqual(s1["state"], "FAILED_RECOVERABLE")
```

Everything else in that test already passes unchanged: the dispatch stays
DISPATCHED, `_dispatch_count` stays 1 across both outage waves, s2 is
`FAILED_RECOVERABLE`, s3 reaches DONE with one dispatch and three worker
calls.

---

## 1. Done-check, run after the last edit

### 1.1 The controller suite

```
$ cd /Users/khalil.maaouni/Documents/BrotherModeUp && python3 tools/test_bm_controller.py
----------------------------------------------------------------------
Ran 99 tests in 9.851s

FAILED (failures=1, errors=2)
EXIT=1
```

**NOT DONE**, for exactly the three collisions in section 0 and no other
reason. 99 = 58 existing + 41 new, so no test was deleted or lost (the
design predicted 58 plus the new classes, section 17.3). One of the three
was already failing before my first edit.

### 1.2 tools/test_bm.py, which wires the command docs

```
$ cd /Users/khalil.maaouni/Documents/BrotherModeUp && python3 tools/test_bm.py
Ran 276 tests in 44.676s

OK (skipped=1)
EXIT=0
```

Run AFTER the doc edits to docs/FULL-AUTO.md and docs/KNOWN-LIMITS.md, not
before.

### 1.3 The forty-one new tests, the eleven new classes

```
$ cd /Users/khalil.maaouni/Documents/BrotherModeUp/tools && python3 -m unittest \
    test_bm_controller.TestR3PausedIsAFounderOnlyGate \
    test_bm_controller.TestR3TheSummaryStateIsTheStoreState \
    test_bm_controller.TestR3StopReasonDrivesEveryLoopDriver \
    test_bm_controller.TestR3TheExecutingWedgeUnwinds \
    test_bm_controller.TestR3TheSkippedLifecycleClosesAtTheSource \
    test_bm_controller.TestR3BlockedIsAMaterialisedViewOfTheLaneGate \
    test_bm_controller.TestR3EveryDispatchRouteIsGateChecked \
    test_bm_controller.TestR3ForeignAndCancelledDispatchIdsRefuse \
    test_bm_controller.TestR3LateResultKeepsItsSpendAndItsFounderRecord \
    test_bm_controller.TestR3FailedRecoverableReachesVerifying \
    test_bm_controller.TestR3TheClaimedCrashWindowRecovers
----------------------------------------------------------------------
Ran 41 tests in 0.566s

OK
EXIT=0
```

Per class, each run on its own, counts matching design 17.1's table exactly:

```
TestR3PausedIsAFounderOnlyGate 6
TestR3TheSummaryStateIsTheStoreState 3
TestR3StopReasonDrivesEveryLoopDriver 6
TestR3TheExecutingWedgeUnwinds 2
TestR3TheSkippedLifecycleClosesAtTheSource 5
TestR3BlockedIsAMaterialisedViewOfTheLaneGate 4
TestR3EveryDispatchRouteIsGateChecked 4
TestR3ForeignAndCancelledDispatchIdsRefuse 3
TestR3LateResultKeepsItsSpendAndItsFounderRecord 4
TestR3FailedRecoverableReachesVerifying 2
TestR3TheClaimedCrashWindowRecovers 2
```

6 + 3 + 6 + 2 + 5 + 4 + 4 + 3 + 4 + 2 + 2 = 41.

The store suite is the store-half writer's done-check and I did not run it.
tools/test_all.py was not run, as instructed.

---

## 2. RED first: the evidence

`docs/program/absolute-lead/evidence/L03/RED-round4-controller.txt`, one
labelled block per class, captured by running each class against the
UNTOUCHED tools/bm_controller.py BEFORE any controller edit:

```
cd /Users/khalil.maaouni/Documents/BrotherModeUp/tools
python3 -m unittest -v test_bm_controller.<class>
```

| Class | RED result on the untouched tree |
|---|---|
| TestR3PausedIsAFounderOnlyGate | FAILED (failures=5, errors=1) |
| TestR3TheSummaryStateIsTheStoreState | FAILED (failures=2) |
| TestR3StopReasonDrivesEveryLoopDriver | FAILED (failures=3, errors=3) |
| TestR3TheExecutingWedgeUnwinds | FAILED (failures=1), then FAILED (failures=2) after strengthening |
| TestR3TheSkippedLifecycleClosesAtTheSource | FAILED (failures=3) |
| TestR3BlockedIsAMaterialisedViewOfTheLaneGate | FAILED (failures=2, errors=1) |
| TestR3EveryDispatchRouteIsGateChecked | FAILED (failures=2) |
| TestR3ForeignAndCancelledDispatchIdsRefuse | FAILED (errors=2) |
| TestR3LateResultKeepsItsSpendAndItsFounderRecord | FAILED (failures=3, errors=1) |
| TestR3FailedRecoverableReachesVerifying | FAILED (failures=1, errors=1) |
| TestR3TheClaimedCrashWindowRecovers | FAILED (failures=1) |

Every one of the eleven CLASSES is red, which is design 17's bar. Nine
INDIVIDUAL tests inside them were green on the untouched tree; eight of
those are controls and every one of them says so in its own docstring, with
the reason. The ninth,
`TestR3TheExecutingWedgeUnwinds.test_the_wedge_note_never_appears_in_any_summary`,
was green because LV p9 only reaches the wedge note on the SECOND driver
call (the first stops on round 3's own no-progress note). I strengthened it
to drive twice and re-captured, which is appended to the RED file under its
own heading; it now reproduces verbatim:

```
AssertionError: 'is not a legal move' unexpectedly found in 'the
done-definition passes but the run is EXECUTING, from which delivery is not
a legal move; staying in place'
```

Representative RED lines from the other blocks, verbatim from that file:

```
AssertionError: ['u1'] != []            (a PAUSED run dispatched u1)
AssertionError: 'PAUSED' != 'DELIVERABLE_READY'   (the engine un-paused it)
AssertionError: 'rejected' != 'held'
AssertionError: 12 != 1                 (the soft spend stop, 12 of 12 steps)
AssertionError: 15 != 1                 (the outage, 15 asks)
AssertionError: 2 != 1 : no worker is handed a brief the LIVE contract refuses
AttributeError: module 'bm_controller' has no attribute '_DISPATCH_WALK_EDGES'
TypeError: 'NoneType' object is not subscriptable
```

---

## 3. Per-section change inventory, tools/bm_controller.py

Line numbers are the file AS IT NOW STANDS.

| Design | Change | Where |
|---|---|---|
| 3.1 | `STOP_REASONS`, the eight-word closed set, with each word's meaning and whether a founder must act | 348 to 367 |
| 3.2 | `ControllerEngine._finish`, the ONE exit from `step()`: re-reads the run row, validates the reason against the enum, leaves an already-set reason alone | 518 |
| 3.2 | `ControllerEngine._set_reason`, the only other writer of the field | 549 |
| 3.3 | `step()`'s summary gains `stop_reason`; `state`, `note`, `dispatched`, `completed`, `founder_gated` keep their meanings | 627, 632 |
| 3.4 | `_NOTE_CONTENTION`, `_NOTE_NOTHING_SELECTABLE`, `_NOTE_IN_FLIGHT`, `_NOTE_SPEND_STOP`, `_NOTE_OUTAGE`, `_NOTE_RUN_PAUSED` | 383 to 400 |
| 3.4 | `_NO_PROGRESS_NOTES` DELETED; the loop drivers append nothing to any note | (removed) |
| 4.1 | `_run_or_refuse`, `_is_paused`, `_refuse_if_paused` | 486, 498, 501 |
| 4.2 | `step` returns `FOUNDER_WAITING` + `_NOTE_RUN_PAUSED` from PAUSED, before any resume branch or contract read, with no store write | 646 to 654 |
| 4.2 | `check_timeouts` returns `[]` on a PAUSED run | 1148 |
| 4.2 | `plan` calls `_refuse_if_paused(run, "plan")` | 608 |
| 4.2 | `run_to_completion` has no guard of its own; its first `step()` stops the loop | 806 |
| 4.3 | `receive_result` records the result and the spend and returns `"held"` | 960 to 964 |
| 4.4 | `_deliver_or_hold`'s source test is `_DELIVERY_SOURCE_STATES`, which excludes PAUSED by construction | 2242, 2278 |
| 6.1 to 6.2 | `_authorise_dispatch(project_id, run_id, unit, open_dispatch=None)`, the ONE route from a unit row to a brief; `_claim_and_dispatch` DELETED, its body is the fresh route | 1483 |
| 6.2 step 4 | the re-await route closes the in-flight dispatch and parks the fence before the breaker | 1538 to 1552 |
| 6.2 step 5a | the stale-stamp branch | 1594 to 1614 |
| 6.2 step 5b | the fence check, no re-claim, no CLAIMED flip-back | 1615 to 1634 |
| 6.3 | `_resume_dispatched` rebuilt around the choke point, with the `_may_dispatch` guard and the outcome-to-reason map | 1306 |
| 6.4 | `FAILED_RECOVERABLE: READY` joins `_RESULT_WALK_EDGES`; `_walk_to_executing` gains it in the detour | 229, 1943 |
| 6.5 | `_handle_worker_result` returns `(outcome, reason)`; both call sites updated | 1663, 776, 1361 |
| 7.1 | `_walk_reaches`, `_DISPATCH_WALK_EDGES`, `_DISPATCH_SOURCE_STATES`, `_may_dispatch`; `_walk_reaches_rejectable` is now a one-line call | 260, 241, 314, 861, 282 |
| 7.1 | the import-time guard checks all THREE edge maps | 331 |
| 7.1 | `step()` asks `_may_dispatch` once, immediately before `_walk_to_executing` | 749 to 757 |
| 7.2 | `_unwind_empty_wave` | 867 |
| 7.2 | called from `step()`'s no-dispatch return and from `_handle_no_ready_units` step 1 | 760, 2066 |
| 8.2 | `plan` parks `orphaned_fences` and reconciles the lane blocks | 588, 617 to 622 |
| 8.4 | `_reconcile_lane_blocks`, the FIRST production caller of `unblock_lane_units`, both directions, no write unless it changes something | 1994 |
| 8.4 | call sites: `step()` before `select_ready_units`, `plan()`, `_handle_no_ready_units` after an escalation, `_handle_late_result` | 709, 622, 2086, 1109 |
| 8.5 | `_unreachable_units` (pure, BLOCKED units are candidates) and `_escalate_unreachable_units`; `_block_unreachable_units` DELETED | 2132, 2170 |
| 8.5 | `_is_founder_waiting(unit, gated_lanes, unreachable)` gains the third arm | 2113 |
| 8.6 | `_handle_no_ready_units` rewritten, `escalate_unreachable` parameter GONE | 2033 |
| 8.6 | `_resume_result_in_and_orphans` gains the SKIPPED-fence branch and the CLAIMED-with-no-dispatch branch | 1246 to 1265 |
| 9.1 | `_loop_stops`, used by `run_to_completion` and `_drive_until_parked` | 424, 806, 2650 |
| 9.2 | `_DELIVERY_WALK_EDGES`, `_DELIVERY_TARGETS`, `_DELIVERY_SOURCE_STATES`; `_deliver_or_hold` rewritten, no `summary["state"]` write | 244, 249, 322, 2242 |
| 10.1 | `_record_spend`, the ONE spend rule, called before the walkability branch | 1006, 973 |
| 10.2 | `receive_result` in the design's order: run, dispatch, unit, paused, record, spend, branch | 897 |
| 10.3 | `_handle_late_result` takes the unit ROW, queues the founder step UNCONDITIONALLY, and no longer calls `block_lane_units` | 1028 |
| 10.4 | `_warn_dirty_write_scope(project_id, unit_id, exit_code, lane)`; all three callers pass the unit's own lane | 1846, 1093, 1755, 1817 |
| 10.5 | `_reject`'s survive branch: the dirty-scope step now lands in the unit's own lane, which the reconcile turns into a lane gate. The order at the top of `_reject` is UNCHANGED | 1811 to 1820 |
| 10.6 | `_verify_and_finish`'s stale branch runs the rollback and warns, before the unchanged fence park | 1749 to 1758 |
| 11.1 | `check_timeouts` gains the PAUSED guard and iterates `_open_dispatch_units` | 1148, 1151 |
| 11.2 | `record_result` wrapped in `try/except bs.OwnershipRefused` with `continue` | 1156 to 1170 |
| 12.2 | `receive_result` refuses `'not-found'` and `'foreign-dispatch'` from `get_dispatch(raw=True)` before anything is recorded or charged | 917 to 946 |
| 13 | `_open_dispatch_units`, the ONE in-flight predicate; `_anything_in_flight` delegates; `_IN_FLIGHT_UNIT_STATUSES` DELETED | 834, 858 |
| 14 | `cmd_step` prints `reason:` | 2771 |
| 14 | `_report_trace` prints `reason:` | 2618 |
| 14 | `cmd_plan` reports skipped and cancelled counts, plain and `--json` | 2820 to 2831 |
| 14 | `cmd_record_result` gains the `"held"` branch | 2889 |
| module docstring | the house-law list now names `release_claimed_unit` and `get_dispatch` (seventeen store methods, not fifteen) | 18 to 27 |

Sections 5.x, 8.1, 8.3, 12.3, 12.4 and the store rows of 15.2 are the store
half's and I did not touch them.

### 3.1 Verified derived sets, printed from the landed module

```
DISPATCH_SOURCE ['CHECKPOINTED', 'EXECUTING', 'READY', 'WAITING_HUMAN']
DELIVERY_SOURCE ['CHECKPOINTED', 'EXECUTING', 'READY', 'VERIFYING', 'WAITING_HUMAN']
RESULT_WALKABLE ['CHECKPOINTED', 'EXECUTING', 'FAILED_RECOVERABLE', 'READY', 'VERIFYING', 'WAITING_HUMAN']
```

Both new sets match design 7.1 and 9.2 exactly. `CONTROLLER_STATE_TRANSITIONS`
was not widened; the import-time guard proves all three edge maps against it
at load, and `TestR3FailedRecoverableReachesVerifying`'s second test asserts
the same thing from outside.

---

## 4. The section-18 migrations, each quoted before and after

Two of section 18's items required an edit. The other four (18.3, 18.4,
18.5, 18.6) said "no change"; three of those held and one did not, which is
collision 3 above.

### 4.1 Section 18.1: the PAUSED row moves out (tools/test_bm_controller.py:1601)

BEFORE:

```python
    def test_the_four_red_rows_of_the_state_matrix_never_raise(self):
        """REFUTATION-2 F1's state matrix: DELIVERABLE_READY, PAUSED,
        STOPPING and STOPPED all raised OwnershipRefused out of
        receive_result, losing the founder warning and leaving the fence
        ACTIVE. The contract is left alone throughout, so the staleness
        branch cannot mask the state-walk question."""
        red_rows = {
            "DELIVERABLE_READY": ("VERIFYING", "CHECKPOINTED",
                                  "DELIVERABLE_READY"),
            "PAUSED": ("PAUSED",),
            "STOPPING": ("STOPPING",),
            "STOPPED": ("STOPPING", "STOPPED"),
        }
```

AFTER (the method is renamed to match what it now covers; the docstring
gains the supersession argument in full, and the three remaining rows and
the whole of `_assert_late_result_handled` are byte-identical):

```python
    def test_the_three_red_rows_of_the_state_matrix_never_raise(self):
        """REFUTATION-2 F1's state matrix: DELIVERABLE_READY, PAUSED,
        STOPPING and STOPPED all raised OwnershipRefused out of
        receive_result, losing the founder warning and leaving the fence
        ACTIVE. The contract is left alone throughout, so the staleness
        branch cannot mask the state-walk question.

        THE PAUSED ROW MOVED OUT on 2026-08-05, into
        TestR3PausedIsAFounderOnlyGate's
        test_a_result_arriving_on_a_paused_run_is_recorded_and_held
        (DESIGN-round4 section 18.1). Every assertion it loses here (the
        founder was warned about a dirty scope, the fence is parked, an
        interruption names the late result) is a CONSEQUENCE OF REJECTING
        the result, and rejecting a real answer because a founder pressed a
        REVERSIBLE pause is the behaviour being removed, so asserting its
        consequences would pin the defect. What replaces it is stronger on
        the property this class exists to protect: the answer survives the
        pause and is verified on its own merits after `bm-controller
        resume`, instead of being rolled back on disk with a retry burned.
        The other three rows stay verbatim, including the whole of
        _assert_late_result_handled."""
        red_rows = {
            "DELIVERABLE_READY": ("VERIFYING", "CHECKPOINTED",
                                  "DELIVERABLE_READY"),
            "STOPPING": ("STOPPING",),
            "STOPPED": ("STOPPING", "STOPPED"),
        }
```

The replacement is
`TestR3PausedIsAFounderOnlyGate.test_a_result_arriving_on_a_paused_run_is_recorded_and_held`
(tools/test_bm_controller.py:2109), which asserts the outcome word `"held"`,
the dispatch left RESULT_IN, the run still PAUSED, the fence still ACTIVE,
`retry_count` still 0, that NO `git restore` command ran, that the meter WAS
charged, and that a founder resume plus one `step` then marks the unit DONE.

### 4.2 Section 18.2: `_assert_late_result_handled` gains an assertion (tools/test_bm_controller.py:1479)

BEFORE (the tail of the helper):

```python
        questions = [i["question"] for i in
                     store.list_interruptions("p1", raw=True)]
        self.assertTrue(
            any("late result" in q and state in q for q in questions),
            "an interruption names the late result and the run state: %r"
            % (questions,))
```

AFTER (nothing removed, one assertion added):

```python
        questions = [i["question"] for i in
                     store.list_interruptions("p1", raw=True)]
        self.assertTrue(
            any("late result" in q and state in q for q in questions),
            "an interruption names the late result and the run state: %r"
            % (questions,))
        # Added 2026-08-05 (DESIGN-round4 section 18.2). SM D: the founder
        # step used to sit behind `if outcome['status'] != 'FAILED'`, and
        # _record_interruption returns None on a contract that is not live,
        # so a unit at its retry ceiling produced NO founder-visible record
        # at all. An open step naming the unit now exists in EVERY case,
        # below the ceiling and at it.
        self.assertTrue(
            any("u1" in w for w in steps),
            "an open founder step names the unit in every case, not only "
            "below the retry ceiling: %r" % (steps,))
```

**Deviation from 18.2, stated rather than silent.** Section 18.2 asks for
TWO added assertions; I added one and did not add the other, because the
two it lists are mutually unsatisfiable against the assertion it says will
not change. Its second addition is "the unit's status is NOT `BLOCKED`",
while the existing assertion beside it is `assertNotEqual(row["status"],
"READY")`. `mark_unit_failed` returns exactly READY or FAILED, and in these
scenarios it returns READY (retry_ceiling is 1 and this is the first
failure), so "not BLOCKED" and "not READY" cannot both hold. Section 18.2
resolves this incorrectly, by asserting both while also saying "the unit is
left in whatever `mark_unit_failed` returned".

I resolved it in favour of the behavioural sections, which are unambiguous.
Section 10.3's real content is that `block_lane_units` and BLOCKED are
removed from the late-result path as an INDEPENDENT fact, and its own
closing sentence says "section 8.4's reconcile marks its units BLOCKED as a
view of that step, reversibly". So `_handle_late_result` queues the founder
step and calls `_reconcile_lane_blocks`, which derives BLOCKED from the step
it just wrote. The unit therefore IS BLOCKED afterwards, the existing
NOT-READY assertion holds unchanged, and the property section 18.2's second
assertion was reaching for (that this status is no longer a one-way door) is
pinned directly, and better, by
`TestR3LateResultKeepsItsSpendAndItsFounderRecord.test_the_blocked_status_the_late_result_causes_is_reversible`
(tools/test_bm_controller.py:3205), which resolves the step and asserts the
status reverses.

The alternative (not calling the reconcile there) would have made the unit
READY and broken `test_a_clean_rollback_on_a_stopped_run_still_requeues_nothing`
(tools/test_bm_controller.py:1542) as well, which section 18 does not name
at all, so it would have cost a fourth collision for no gain.

Adding a call site to `_reconcile_lane_blocks` beyond the three section 8.4
enumerates is the second half of this deviation. The reason it is right
rather than merely convenient: a late result can land on a run no later
`step()` will ever drive (a STOPPED one), so "reconciled on the next wave"
would leave the view permanently stale exactly where the founder most needs
it to be true.

### 4.3 Sections 18.3, 18.4, 18.5, 18.6: the "no change" claims, checked

* **18.3** (`TestF4DependentOfAFailedUnitDoesNotStallTheRun` at 1293 and
  `TestR2F4DeadDependenciesAndFounderGatedLanes` at 1816): HELD. All four
  BLOCKED assertions (1339, 1385, 1858, 1903) pass unchanged. I did not
  change their docstrings, since the design lists that as optional prose.
* **18.4** (`TestHumanBlockedLaneDoesNotStallIndependentLane` at 926): HELD.
  The test pairs its `block_lane_units` call with a `queue_human_step` in
  the same lane, so the reconcile finds the lane gated and leaves the
  BLOCKED status alone. Its sibling claim, that no test makes an unpaired
  call, did NOT hold; that is collision 1.
* **18.5** (`TestEndToEndE4` at 1975): HELD, and better than predicted. The
  regenerated artifact's ONLY diff is the four uuid4 `checkpoint_ref`
  values, which the class's own docstring says are the only bytes that
  differ run to run. `run_states_visited` did not change at all. Verbatim
  `git diff` of the artifact is four `checkpoint_ref` lines and nothing
  else.
* **18.6** (`TestFault9ProviderOutageThenRecovery` at 762 and
  `TestFault6CostCeilingReached` at 583): Fault 6 HELD (`summary["state"]
  == "STOPPED"` is read back by `_finish`). Fault 9 did NOT hold; that is
  collision 3.

I edited no other existing test in this file or anywhere else.

---

## 5. Deviations from the design, each with its reason

Three, all of them forced by an internal inconsistency in the design or by
an existing refutation-born assertion the design does not authorise
changing. Nothing here changes a behaviour the design specifies; each moves
where or how finely it is applied.

1. **Section 18.2's second added assertion is not added**, and
   `_reconcile_lane_blocks` gains a fourth call site inside
   `_handle_late_result`. Full argument in 4.2 above.
2. **Section 8.5's escalation gates at WAVE granularity, not inside the
   loop.** The design says "add that lane to `gated_lanes` so a second unit
   in the same lane does not queue a second step", which would collapse two
   unreachable units sharing one lane into a single step. Existing test
   `TestF4DependentOfAFailedUnitDoesNotStallTheRun.test_a_transitively_blocked_unit_is_told_which_unit_actually_failed`
   (tools/test_bm_controller.py:1392 to 1394) asserts
   `sorted(steps) == ["u2", "u3"]`, one step per unreachable unit, each
   naming its OWN chain, and section 18.3 explicitly protects that class
   from change. So the gate is computed from the lanes gated at the START of
   the wave, and lanes newly gated within the wave are folded in at the end.
   The anti-spam property is unchanged (the marker is still state-derived
   and still checked once per wave), and
   `TestR3BlockedIsAMaterialisedViewOfTheLaneGate.test_ten_consecutive_steps_queue_exactly_one_escalation_step`
   pins it. The full reasoning is written into
   `_escalate_unreachable_units`' own docstring, not only here.
3. **`_resume_dispatched` looks for an open dispatch BEFORE applying the
   `_may_dispatch` guard**, rather than after, as section 6.3's bullet order
   implies. Applying the guard first would make `step()` return
   FOUNDER_WAITING from a DELIVERABLE_READY run with nothing in flight, and
   `_handle_no_ready_units` and `_deliver_or_hold` would then never run, so
   section 9.2's item 1 (the `DELIVERED` reason, written without touching
   the store) would be unreachable in the ordinary case. The guard is
   applied exactly where 6.3's own justification places it ("after section 8
   a delivered run cannot hold an open dispatch, but the guard costs one
   comparison"), that is, when there IS an open dispatch it may not act on.

A fourth, smaller reading: design 17.1 asks the contention test to assert
"the note must NOT contain 'founder'", while design 3.4's own
`_NOTE_CONTENTION` text contains the phrase "no founder action is needed".
The constants are decision-complete, so I kept them verbatim and asserted
the property the finding is actually about: the note must NOT contain "until
a founder acts" (LV 5's false claim), and MUST contain "no founder action is
needed".

---

## 6. Verification I ran beyond the suites

* **Blast radius of every deleted or re-signed symbol, grepped not
  assumed.** `_claim_and_dispatch`, `_block_unreachable_units`,
  `_IN_FLIGHT_UNIT_STATUSES` and `_NO_PROGRESS_NOTES` have ZERO remaining
  references in tools/bm_controller.py. Outside the controller and its own
  test file, no `.py` in the repository mentions any of them, nor
  `_handle_worker_result`, `_handle_late_result` or
  `_warn_dirty_write_scope`; the only hits in tools/test_bm_controller.py
  are prose inside docstrings. `run_to_completion`, `receive_result` and
  `check_timeouts` have no callers outside bm_controller.py and its test
  file either.
* **`cmd_status`' open-dispatch display, which the store writer flagged as
  unverified.** I read it (tools/bm_controller.py:2932 to 2939). It filters
  `d["status"] in ("DISPATCHED", "RESULT_IN")`, an allow-list, so the new
  CANCELLED status is excluded automatically. The design's section 13 claim
  holds. The unit-status pre-filter above it is display-only and a CANCELLED
  dispatch's unit is SKIPPED, so it is excluded twice over.
* **The ast guard is not a restatement of the code.** It parses
  tools/bm_controller.py and asserts that `self.worker.run` appears in
  exactly two function bodies, `step` and `_resume_dispatched`, and that
  both also call `self._authorise_dispatch`. It was RED before the change
  (three call sites, one of them ungated) and a third route added later
  fails it.
* **No em dash or en dash** in any of the four files I wrote: zero hits
  across tools/bm_controller.py, tools/test_bm_controller.py,
  docs/FULL-AUTO.md and docs/KNOWN-LIMITS.md.
* **No TODO, FIXME, XXX, bare `print(`, `pdb` or `breakpoint(`** in
  tools/bm_controller.py.
* **`git status --porcelain` and `git diff --stat`.** My four files plus the
  RED file and this report. tools/bm_store.py and tools/test_bm_store.py
  also appear, which is the store half's own uncommitted work, not mine; I
  issued no edit to either. The E4 artifact shows as modified because
  `TestEndToEndE4` regenerates it on every run by its own documented design.
  I ran no git command that changes state.

---

## 7. What I did NOT do, stated plainly

* **The done-check is NOT DONE** on `python3 tools/test_bm_controller.py`,
  for the three collisions in section 0 and nothing else. One of the three
  was red before my first edit.
* **tools/test_all.py was not run**, as instructed. **The store suite was
  not run**, as instructed; I make no claim about it. The autonomy suite
  (tools/test_bm_autonomy.py) is a store-side consumer and I did not run it
  either, since I changed nothing it reads.
* **docs/AUTONOMY.md was NOT written.** Design sections 5.1 and 16 require
  the glob rule and the three deferrals to land there as well. My brief
  allows `references/autonomy.md` only "IF the design names it", and the
  design names `docs/AUTONOMY.md`, which is a different file and is not on
  my write list. So: the glob rule and the three deferrals ARE now written
  in docs/KNOWN-LIMITS.md and the founder-facing halves in
  docs/FULL-AUTO.md, and **docs/AUTONOMY.md still carries neither**. That
  is an open item for whoever owns that file.
* **The FIX-round3 disclosure that AZ F-A2 refuted** is in
  docs/KNOWN-LIMITS.md and I did not delete it. I appended a section that
  explicitly supersedes it and says so in its own heading, because deleting
  the old paragraph would erase the record of what was believed and when.
  Whoever prefers a single current statement should collapse the two.
* **Not verified by me: the four `bm-controller` CLI behaviours I changed
  were exercised only through the in-process engine and the existing CLI
  subprocess tests.** No new CLI subprocess test asserts the `reason:` line,
  the `held` message, or `plan`'s new skipped and cancelled counts. The
  existing CLI tests pass, which proves those lines do not break the
  commands, not that their text is right.
* **Not verified by me: two real operating-system processes** against one
  store. Every concurrency probe here, as in the last round, is a single
  process with a delegating wrapper.
* **SM observation 5 is recorded, not changed**, as design 8.5 directs: an
  open founder step still gates its lane project wide, across runs, because
  the human-steps table has no run id. Disclosed in docs/KNOWN-LIMITS.md.
* **SM G is bounded, not closed**, as design 12.1 directs, and
  docs/KNOWN-LIMITS.md says so in the design's own words. I wrote no test
  for the race itself; the two tests that matter cover its two measured
  consequences, and both are in the new classes.
* **`CONTROLLER_STATE_TRANSITIONS` was not widened** and no state move
  outside design 15.3's table is attempted anywhere.
