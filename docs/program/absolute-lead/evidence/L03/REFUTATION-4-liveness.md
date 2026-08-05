# REFUTATION 4, the LIVENESS AND REGRESSIONS lens

Independent adversarial refuter, one of three lenses on ROUND 4 of the L03
controller rebuild. Target: the CURRENT working tree at
/Users/khalil.maaouni/Documents/BrotherModeUp. Read-only except this file.
No git command that changes state was run. `python3 tools/test_all.py` was
NOT run; every suite result below is a single unittest class.

Read first, in full: DESIGN-round4.md, FIX-round4-store-report.md,
FIX-round4-controller-report.md, tools/bm_controller.py (all 3177 lines of
the sections this lens covers), and tools/bm_store.py at every point the
controller touches it.

Probe scripts live in /tmp/r4probe and each one builds its own Store under
a fresh `tempfile.TemporaryDirectory()`. The CLI probes point
BROTHERMODE_ROOT, BROTHERMODE_VAULT and HOME inside that same throwaway
root. No real `.brothermode` directory was opened.

---

## VERDICT LINES

| ID | Verdict | Severity | One line |
|---|---|---|---|
| L4-F1 | **STANDS** | HIGH | Every wave that records a result parks through `_settle_after_wave`'s THROWAWAY summary, so `stop_reason`, the note and the whole `founder_gated` block that `_deliver_or_hold` computes are discarded. `bm-controller start` on a delivered run with a FAILED unit never names it. |
| L4-F2 | **STANDS** | HIGH | A run paused because the CONTRACT is paused reports `_NOTE_RUN_PAUSED`, whose only instruction is `bm-controller resume`. Following it loops forever: resume, step, PAUSED, resume. Reproduced through four shipped commands. |
| L4-F3 | **STANDS** | HIGH | A run whose only blocker is an open founder step in an UPSTREAM lane parks as `NOTHING_SELECTABLE`, the one enum value whose documented meaning is "nothing founder-gated ... inspect the graph", and the run state is left READY instead of WAITING_HUMAN. |
| L4-F4 | **STANDS** | MEDIUM | A run left VERIFYING with an open dispatch parks as `FOUNDER_WAITING` with a note naming three founder commands; `resume` no-ops, `complete` is refused by the store, and only `stop` (which kills the run) works. The real recovery is `record-result`. |
| L4-F5 | **STANDS** | MEDIUM | `_resume_result_in_and_orphans` models three orphan shapes and not the fourth: a unit left DISPATCHED behind a CLOSED dispatch. Its fence stays ACTIVE over the founder's files, no founder step names it, and the run parks as `NOTHING_SELECTABLE` forever. Same damage LV 7 found for CLAIMED, one status later, in five two-call crash windows, three of them new in round 4. |
| L4-F6 | **STANDS** | LOW | The retirement note for `test_a_late_result_on_deliverable_ready_never_dispatches_a_second_time` claims its replacement pins three properties. The replacement pins two. The third holds in fact but is asserted by nothing. |
| L4-F7 | **STANDS** | LOW | tools/test_bm_controller.py now holds 98 test methods, 57 of them pre-round-4. DESIGN-round4 section 17.3 sets the bar at "no lower than 58 plus the new tests". The drop is the authorised retirement, so it is disclosed rather than silent, but the design's own numeric gate is not met. |
| ORCH-1 | **REFUTED (NO-DATA)** | n/a | The orchestrator's first ruling (pairing the unpaired `block_lane_units` call in TestFault8) masks NO product defect. `block_lane_units` has exactly ONE call site in tools/bm_controller.py and it is paired by construction; the pairing property holds as a measured invariant across every scenario I drove. |
| LV1-CLOSED | **REFUTED (attempt failed)** | n/a | The EXECUTING wedge is genuinely closed. A run whose only unit is gate-refused now delivers in 3 steps. |
| LV5-CLOSED | **REFUTED (attempt failed)** | n/a | Contention is never reported as founder-waiting, burns no retry, and the run proceeds on the next external step with no founder involved. Both the fresh route and the re-await route. |
| L4-RECON | **REFUTED (attempt failed)** | n/a | Law L4 holds under every attack I built: both directions reconcile, the anti-spam marker holds over ten consecutive steps, a changed re-plan plus a resolve recovers, and a byte-identical re-plan behaves exactly as section 8.5 says it will. |

Genuine attempt count: **30 distinct attack ideas**, logged in section "Attempts".
Seven produced findings. The last full round of new ideas (items 21 to 30)
produced one finding (L4-F5) and nine misses, so I ran one further round
(items 27 to 30) which produced nothing new beyond observations.

---

## L4-F1 (HIGH). The settle path throws the wave's whole verdict away

### The defect

`ControllerEngine._settle_after_wave` ends by calling
`_handle_no_ready_units` with a summary nobody reads:

tools/bm_controller.py:1991 to 1992

```python
        summary = {"note": ""}
        self._handle_no_ready_units(project_id, run_id, summary)
```

`_handle_no_ready_units` is where delivery, the founder-waiting park, the
in-flight park and the escalation all happen, and it is the only caller of
`_deliver_or_hold`. So on EVERY wave that recorded a result, three things
that DESIGN-round4 makes load bearing are computed and then dropped on the
floor:

* `stop_reason` (`DELIVERED`, `FOUNDER_WAITING` or `NOTHING_SELECTABLE`),
  which law L3 says is the ONE field control flow reads;
* the note (`"deliverable ready"`, `"only founder-gated lanes remain"`,
  the done-definition failure text);
* `summary["founder_gated"]`, written at tools/bm_controller.py:2319 to
  2321, which is the only place the run's remaining FAILED units and open
  founder steps are ever attached to a summary.

The second half of the defect is that no LATER step can recover it.
`_deliver_or_hold`'s already-delivered early return sets the reason and the
note but never re-attaches `founder_gated`:

tools/bm_controller.py:2267 to 2274

```python
        cur = self.store.get_run(project_id, raw=True)["state"]
        if cur == "DELIVERABLE_READY":
            self._set_reason(summary, "DELIVERED", "deliverable ready")
            return
```

### Reproduction A, four shipped commands, in-process

`/tmp/r4probe/p04_delivered_reason_lost.py`. One unit exhausts its retry
ceiling, one unit is DONE, so the delivering wave has a founder-gated
remainder worth naming.

```
step 0
   state        = READY
   stop_reason  = None
   note         = 'no spend ceiling on file (no-data); starting units and saying so'
   founder_gated= None
step 1
   state        = DELIVERABLE_READY
   stop_reason  = None
   note         = 'no spend ceiling on file (no-data); starting units and saying so'
   founder_gated= None
store state: DELIVERABLE_READY
units: [('u1', 'FAILED'), ('u2', 'DONE')]

-- one MORE step on the already-delivered run
   state        = DELIVERABLE_READY
   stop_reason  = 'DELIVERED'
   note         = 'deliverable ready'
   founder_gated= None
```

Step 1 IS the delivery. It carries `stop_reason None`, meaning, in design
3.1's own words, "the wave made progress and a loop may call step()
again". The note it carries is stale prose from step 3 of the same wave.
`founder_gated` is absent on the delivering wave and absent on every wave
after it.

### Reproduction B, the shipped CLI

`/tmp/r4probe/p05_cli_founder_gated.py`, real subprocesses of
tools/bm_store.py, tools/bm_project.py, tools/bm_autonomy.py and
tools/bm_controller.py under a throwaway root.

```
run state: DELIVERABLE_READY
units_by_status: {'DONE': 1, 'FAILED': 1}
open_human_steps: 0

=== bm-controller start on the DELIVERED run ===
$ bm_controller.py start --project p1 --controller-id
  rc=0
  | project p1: run 0e7fea644a59466e8b8f08ccc50a5e20, 1 step(s), now DELIVERABLE_READY
  | dispatched 0 unit(s), completed 0 unit(s) this call
  | note: deliverable ready
  | reason: DELIVERED
contains 'founder-gated remainder': False

=== bm-controller step --json on the DELIVERED run ===
{
  "completed": [],
  "dispatched": [],
  "note": "deliverable ready",
  "run_id": "0e7fea644a59466e8b8f08ccc50a5e20",
  "state": "DELIVERABLE_READY",
  "stop_reason": "DELIVERED"
}
```

One of the two units in the graph exhausted its retry ceiling and was
never done. `bm-controller start` says the deliverable is ready and never
mentions it. `bm-controller complete` (tools/bm_controller.py:3084 to
3121) prints nothing about it either. Only `bm-controller status` reveals
it, and nothing in the delivery output points there.

### Reproduction C, the founder's whole test suite runs twice

`/tmp/r4probe/p01_done_definition_count.py`. DESIGN-round4 9.1's own table
promises a failing done-definition costs ONE execution per
`run_to_completion` call ("15 of 15" becomes "1"), and 9.2 item 3 says
"Bounded to ONCE per park decision, because the loop stops on the reason".

```
steps: 2
  0 state=CHECKPOINTED reason=None note='no spend ceiling on file (no-data); starting units and saying so'
  1 state=CHECKPOINTED reason='FOUNDER_WAITING' note='final done-definition check failed (exit 3); the run stays in place fo'
done_definition executions: 2
all checker calls: ['true', 'final-suite', 'final-suite']
run state: CHECKPOINTED
```

Two, not one, and step 0's copy of the failure is invisible: the summary
that step returns carries `reason None` and a note about the spend
ceiling. Through the shipped CLI the same execution happens inside
`bm-controller record-result`, which prints `unit u1 accepted` and says
nothing about the founder's final check having just failed.

### Where the block IS reachable, so the diagnosis is exact

`/tmp/r4probe/p08_verifying_wedge.py` part a. When delivery happens on a
wave that recorded NOTHING (the gate-refused-unit shape), `step()` calls
`_handle_no_ready_units` with the real summary at
tools/bm_controller.py:714 and the block survives:

```
=== a. founder_gated on the step()-owned delivery (gate-refused unit)
   last summary keys: ['completed', 'dispatched', 'founder_gated', 'note', 'run_id', 'state', 'stop_reason']
   founder_gated: {'human_steps': [], 'failed_units': ['u1']}
```

So the loss is specific to the settle path, which is every synchronous
worker wave and every `bm-controller record-result`, that is, the
production route.

### Why the run does not spin

`_loop_stops` (tools/bm_controller.py:437 to 439) survives only on its
second clause, the one its own docstring calls "belt and braces, never the
primary test": `summary["state"] in _RUN_TO_COMPLETION_STOP_STATES`.
DELIVERABLE_READY and WAITING_HUMAN are in that set. The primary test,
the enum, is None on exactly the waves that matter. The
`NOTHING_SELECTABLE` case is not covered by the state clause either
(CHECKPOINTED is not a stop state), which is why reproduction C costs an
extra step and an extra full run of the founder's suite rather than
stopping.

The E4 evidence artifact shows the same shape from outside. Its
`run_states_visited` is
`[READY, READY, READY, READY, DELIVERABLE_READY, DELIVERABLE_READY]`: the
wave that delivers (s4) and then one more step whose only job is to say
`DELIVERED`.

---

## L4-F2 (HIGH). A contract-paused run tells the founder to run the one command that cannot help

### The defect

`step()` pauses the RUN when the CONTRACT is paused
(tools/bm_controller.py:675 to 679). Round 4's new PAUSED guard at 656 to
658 then short-circuits every later step BEFORE the contract is re-read,
and hands the founder the new note constant:

tools/bm_controller.py:397 to 399

```python
_NOTE_RUN_PAUSED = ("the controller run is PAUSED; only bm-controller "
                    "resume leaves that state, and this engine will not "
                    "dispatch, judge or deliver until it does")
```

`cmd_resume` (3055 to 3059) moves PAUSED to READY. The very next `step()`
re-reads the contract, finds it still paused, and writes PAUSED again.
Nothing in the controller's output ever names `bm-autonomy resume`, which
is the command that actually clears it.

### Reproduction, the shipped CLI

`/tmp/r4probe/p11_cli_pause_loop.py`, verbatim:

```
$ bm_autonomy.py pause --project p1
  | project p1 contract -> paused (revision 2)
$ bm_controller.py step --project p1
  | run d8e2d3b108c540ed8e6f4cd6bdeddc7c: state PAUSED
  | note: contract is paused
  | reason: FOUNDER_WAITING
$ bm_controller.py step --project p1
  | run d8e2d3b108c540ed8e6f4cd6bdeddc7c: state PAUSED
  | note: the controller run is PAUSED; only bm-controller resume leaves that state, and this engine will not dispatch, judge or deliver until it does
  | reason: FOUNDER_WAITING

--- the founder does what that note says, three times ---
$ bm_controller.py resume --project p1
  | project p1 controller run d8e2d3b108c540ed8e6f4cd6bdeddc7c: PAUSED -> READY
$ bm_controller.py step --project p1
  | run d8e2d3b108c540ed8e6f4cd6bdeddc7c: state PAUSED
  | note: contract is paused
[the same two commands twice more]

run state after three resumes: PAUSED
```

The in-process form is `/tmp/r4probe/p10_contract_pause_loop.py`; it also
confirms the escape (`set_contract_state("p1", "live", ...)` then one
resume, and the run delivers in one step).

`cmd_record_result`'s new `"held"` branch (tools/bm_controller.py:2888 to
2892) carries the same instruction, so a result held on a
contract-paused run tells the founder the same wrong thing.

This is round-4 machinery, not an inherited defect: the guard at 656 and
the constant at 397 are both new this round, and REFUTATION-3 SM A
established that round 3 did not park here at all.

Minimal remedy, stated for whoever owns the decision: the PAUSED guard
should distinguish the two causes. The run row already records the reason
it was moved to PAUSED (`set_run_state`'s reason at 677 is
`"contract is paused"`), and `latest_contract(project_id)["state"]` is one
read away. When the contract is not live, the note must name the contract
command, not `bm-controller resume`.

---

## L4-F3 (HIGH). A founder-gated run reported as "nothing founder-gated"

### The defect

`_is_founder_waiting` (tools/bm_controller.py:2113 to 2130) calls a unit
founder-waiting when it is BLOCKED, unreachable, or PENDING/READY in a
gated lane. It does NOT consider a unit whose DEPENDENCY is founder-gated.
So a run in which every path forward runs through one gated lane falls
through to:

tools/bm_controller.py:2110 to 2111

```python
        self._set_reason(summary, "NOTHING_SELECTABLE",
                         _NOTE_NOTHING_SELECTABLE)
```

DESIGN-round4 3.1 defines that word as "nothing selectable, nothing in
flight, nothing founder-gated | yes, inspect the graph". Here one
`resolve` unwedges the run. The WAITING_HUMAN store move at 2099 to 2101
is also skipped, so `bm-controller status` reports READY for a run that is
waiting on a human.

### Reproduction

`/tmp/r4probe/p03_nothing_selectable.py`. Lane `build` holds a founder
step (the exact shape `_warn_dirty_write_scope` and `_handle_late_result`
write); u1 is in `build`; u2 is in the ungated lane `test` and depends on
u1.

```
step 0 state=READY reason='NOTHING_SELECTABLE' note='no unit is currently selectable (dependencies unmet or in flight); waiting; nothing is in flight either, so the run is parked until a founder acts'
store run state: READY
   unit u1 build BLOCKED
   unit u2 test PENDING
open founder steps: [('build', 'the rollback for some unit in this lane ')]

-- founder resolves the ONE open step, then one more step
step 0 state=READY              reason=None   note='no spend ceiling on file (no-data); starting units'
step 1 state=DELIVERABLE_READY  reason=None   note='no spend ceiling on file (no-data); starting units'
store run state: DELIVERABLE_READY
```

The prose is honest and the enum is wrong, which is the exact inversion of
law L3 ("control flow reads the enum, never the prose. Notes are for the
founder"). An SDK caller doing what L3 tells it to do reports "inspect the
graph" for a run that one command fixes.

The recovery drive also reproduces L4-F1 again: both summaries carry
`reason None`, and the delivering one carries the spend-ceiling note.

---

## L4-F4 (MEDIUM). The VERIFYING park names three commands, two of which cannot move it

### The defect

`_DISPATCH_SOURCE_STATES` is `{CHECKPOINTED, EXECUTING, READY,
WAITING_HUMAN}`. VERIFYING is deliberately out. `_resume_dispatched`'s
guard (tools/bm_controller.py:1338 to 1345) therefore parks any run left
VERIFYING with an open dispatch:

```python
            return {"completed": [], "stop_reason": "FOUNDER_WAITING",
                    "note": "a dispatch is open but the run is %s, which "
                            "only a founder can move" % state}
```

and `step()`'s own guard at 729 to 733 spells the same claim out as
"(bm-controller resume, complete or stop)".

### Reproduction

`/tmp/r4probe/p08_verifying_wedge.py` part b. I constructed the state with
a direct `set_run_state(VERIFYING)` while a dispatch was open, which is
what a crash between `_ensure_verifying` (inside `_handle_worker_result`)
and `_settle_after_wave` leaves behind.

```
CONTROLLER_STATE_TRANSITIONS['VERIFYING'] = ('CHECKPOINTED', 'READY', 'STOPPING', 'PAUSED', 'FAILED_RECOVERABLE', 'FAILED_TERMINAL')
   reason: FOUNDER_WAITING | note: a dispatch is open but the run is VERIFYING, which only a founder can move
   -- what `bm-controller complete` would do:
      COMPLETE from VERIFYING refused: OwnershipRefused run '7e6aa...' is VERIFYING; moving it to COMPLETE is not legal from there. Legal move
   -- `bm-controller resume` no-ops unless PAUSED (cmd_resume line 3055)
   -- what actually recovers it: record-result
      receive_result -> u1 | run: DELIVERABLE_READY
```

`bm-controller resume` prints "is already VERIFYING, not PAUSED. Nothing
to do." and returns 0. `bm-controller complete` is refused by the store.
Only `stop` works, and `stop` destroys a run that one `record-result` would
have finished. The note therefore points a founder at abandoning a
recoverable run.

Honest scoping: I did not reproduce this from a real process kill, and the
production `RecordIntentWorker` always parks rather than answering
synchronously, so the natural route is a crash inside a synchronous
worker wave. That is why this is MEDIUM and not HIGH.

---

## L4-F5 (MEDIUM). The fourth orphan shape is not modelled

### The defect

`_resume_result_in_and_orphans` (tools/bm_controller.py:1242 to 1273)
recovers three orphan shapes: DONE with an active fence, SKIPPED with an
active fence, and CLAIMED with no dispatch row (LV 7's own finding, closed
this round). It does NOT recover a unit left DISPATCHED behind a dispatch
that is already CLOSED.

That state sits in a two-call crash window in five places, three of them
new in round 4:

| Window | record_verification | mark_unit_failed |
|---|---|---|
| `_authorise_dispatch` step 4, re-await refusal (NEW) | 1541 | 1565 |
| `_authorise_dispatch` step 5a, stale stamp (NEW) | 1589 | 1595 |
| `_authorise_dispatch` step 5b, dead fence (NEW) | 1612 | 1617 |
| `_verify_and_finish` staleness branch | 1736 | 1742 |
| `check_timeouts` | 1188 | 1192 (via `_reject`) |

`Store.record_verification` (tools/bm_store.py) writes the dispatch status
in its own transaction and returns; `mark_unit_failed` is a separate
transaction. A crash between them leaves the unit DISPATCHED, the dispatch
REJECTED, and the fence ACTIVE.

### Reproduction

`/tmp/r4probe/p12_pairing_and_stranded.py` part B. I created the state by
calling `record_verification` directly, which is exactly the first of the
two calls in every window above.

```
=== B. a unit left DISPATCHED behind a CLOSED dispatch
   unit: DISPATCHED dispatch: REJECTED
   step 0 state=CHECKPOINTED   reason='NOTHING_SELECTABLE' note='no unit is currently selectable (dependencies unmet or in fl'
   unit now: DISPATCHED
   open founder steps: 0
   fence state: active
```

This is LV 7's damage verbatim ("fence STILL: active", "open founder
steps: 0"), one unit status later. `_open_dispatch_units` cannot see it (a
closed dispatch), `check_timeouts` cannot see it (a timeout is a
dispatch-row fact), `_unreachable_units` does not consider DISPATCHED
units as candidates, and `_is_founder_waiting` returns False for it, so
the run parks as NOTHING_SELECTABLE with no founder step naming the unit
and a fence held over the founder's files indefinitely.

The remedy is symmetrical with the branch round 4 already added: a fourth
`elif` in the same loop for a unit whose status is CLAIMED, DISPATCHED or
RESULT_IN with NO open dispatch row, parking the fence and returning the
unit through the circuit breaker (DISPATCHED did have an attempt, unlike
CLAIMED, so `mark_unit_failed` rather than `release_claimed_unit` is the
right recovery there).

---

## L4-F6 (LOW). The retirement note claims one property more than its replacement pins

tools/test_bm_controller.py:1581 to 1594 retires
`test_a_late_result_on_deliverable_ready_never_dispatches_a_second_time`
and says:

> The property this test protected, a delivered run never re-dispatches
> the dropped unit, is pinned stronger by
> TestR3TheSkippedLifecycleClosesAtTheSource.
> test_a_result_for_a_cancelled_dispatch_refuses_instead_of_reviving_the_unit,
> which additionally asserts the founder's drop stands and no meter is
> charged.

The replacement is at tools/test_bm_controller.py:2608. Read in full, it
asserts exactly three things: `caught.exception.reason ==
"dispatch-cancelled"`, `u1` is still `SKIPPED`, and
`spend_totals("p1")["tokens"]` is unchanged (plus an `isinstance` check on
the exception type). It never drives another `step()` and never counts
dispatches, so the re-dispatch property is not asserted anywhere in it.
No other test in the file asserts it either.

The property does HOLD in fact. `/tmp/r4probe/p13_retired_property.py`:

```
run state after the drop: DELIVERABLE_READY
receive_result refused: dispatch-cancelled
dispatch count for u1 before=1 after=1
u1 status: SKIPPED
worker calls: {'u1': 1, 'u2': 1}
reasons after: ['DELIVERED']
run state: DELIVERABLE_READY
```

So this is a coverage gap in the supersession argument, not a behavioural
regression. Two lines added to the replacement (drive one more
`run_to_completion` and assert `_dispatch_count(store, "u1") == 1`) close
it.

---

## L4-F7 (LOW). The suite is one test below the design's own numeric floor

Counted by AST rather than by running the suite:

```
TOTAL test methods: 98
```

of which the eleven `TestR3*` classes hold 41, leaving 57 pre-round-4
tests. DESIGN-round4 17.3 states: "Expected counts: controller 58 plus the
new classes' tests ... Any DROP in either number is a deleted test and is a
failure of this change, not a result."

The drop is the authorised retirement in L4-F6, recorded in the file with
its argument, so it is disclosed rather than silent. It is listed here
only because the design's gate is numeric and the number no longer clears
it, which a later round reading 17.3 literally would flag as a failure.

---

## ORCH-1 REFUTED. The TestFault8 pairing edit masks no product defect

The orchestrator's first ruling paired the previously unpaired
`block_lane_units` call in `TestFault8RestartWithNewerWorkflowVersion`
(tools/test_bm_controller.py:712 to 722). I was asked whether that pairing
hides an engine-internal `block_lane_units` call that is not paired
anywhere in tools/bm_controller.py.

**Grep, whole repository, all `.py`:**

```
$ grep -rn "block_lane_units" --include=*.py . \
    | grep -v bm_store.py -e bm_controller.py -e test_bm_store.py -e test_bm_controller.py
(no output)

$ grep -n "block_lane_units" tools/bm_controller.py
23:  record_verification, mark_unit_done, mark_unit_failed, block_lane_units,
2011:        block_lane_units' own docstring already says it is for ("paired
2029:                    self.store.block_lane_units(run_id, lane, self.actor)
```

Line 23 is the module docstring's store-method list and 2011 is prose.
The ONE executable call is 2029, inside `_reconcile_lane_blocks`, under
`if lane in gated:` where `gated` is the set of lanes holding an open
founder step (2018 to 2019). It is paired by construction; there is no
unpaired path to pair.

**Probed as a property, not just grepped.**
`/tmp/r4probe/p12_pairing_and_stranded.py` part A checks, after every
engine action, that every BLOCKED unit's lane is covered by an open
founder step:

```
=== A. pairing property across scenarios
-- A1: dead dependency escalation
   unpaired BLOCKED units at the end: []
-- A2: a late result on a stopped run (the _handle_late_result path)
   receive_result -> rejected
   unpaired BLOCKED units: []
   units: [('u1', 'BLOCKED', 'default'), ('u2', 'DONE', 'default')]
   open steps: [('default', 'unit u1 returned a result afte')]
```

Verdict: the ruling is correct and costs nothing. The only behavioural
consequence of the unblock direction is that any BLOCKED status written by
a non-engine caller is reversed on the next wave, which is the pairing law
made executable and is exactly what DESIGN-round4 18.4 says.

---

## LV1-CLOSED and LV5-CLOSED REFUTED. Two of round 3's liveness findings really are gone

**The EXECUTING wedge (LV 1).** `/tmp/r4probe/p07_enum_matrix.py` case 2:
a run whose only unit's write scope the contract refuses.

```
   steps: 3
     0 state=CHECKPOINTED       reason=None                 note='no selectable unit could be claimed this wave (fen'
     1 state=CHECKPOINTED       reason=None                 note='no selectable unit could be claimed this wave (fen'
     2 state=DELIVERABLE_READY  reason='DELIVERED'          note='deliverable ready'
   final store state: DELIVERABLE_READY
   unit: FAILED
   worker calls: {}
```

Three steps, delivers, no wedge note, no worker call. Round 3's "20 of 20
steps, 21 done_definition executions, DELIVERABLE FOREVER OUT OF REACH:
True" is gone.

**The false park on contention (LV 5).** `/tmp/r4probe/p06_contention.py`.
A foreign owner holds a fence over the unit's files:

```
  step 0 state=CHECKPOINTED   reason='CONTENTION' note="another writer holds a fence over this unit's files, or the contract was amended twice while the unit was being checked; no founder action is needed and the next step tries the same unit again"
  note mentions 'until a founder acts': False
  note mentions 'no founder action is needed': True
  unit status: READY
  retry_count: 0
  -- the other writer lets go, no founder involved
  step 0 state=DELIVERABLE_READY  reason=None         note='no spend ceiling on file (no-data); starting units'
  final store state: DELIVERABLE_READY
  worker calls: {'u1': 1}
```

The reason is CONTENTION, the note is honest, no retry is burned, and the
run proceeds on the next external step with no founder action. Part B of
the same probe drives the re-await route (an open dispatch across a wave)
and reaches DELIVERABLE_READY with `dispatch count for u1: 1`.

---

## L4-RECON REFUTED. Law L4 survived every attack I built

`/tmp/r4probe/p09_reconcile_law.py`, verbatim:

```
=== A. byte-identical re-plan revival
   after escalation             units=[('u1', 'FAILED'), ('u2', 'BLOCKED')] steps=1 state=WAITING_HUMAN
   after identical re-plan      units=[('u1', 'FAILED'), ('u2', 'BLOCKED')] steps=1 state=READY
   resolve=True, after drive    units=[('u1', 'FAILED'), ('u2', 'BLOCKED')] steps=1 state=WAITING_HUMAN
      reasons: ['FOUNDER_WAITING']

=== B. CHANGED re-plan that removes the dead dependency
   resolve=False, after drive   units=[('u1', 'FAILED'), ('u2', 'BLOCKED')] steps=1 state=WAITING_HUMAN
   resolve=True, after drive    units=[('u1', 'FAILED'), ('u2', 'DONE')] steps=0 state=DELIVERABLE_READY

=== C. a healthy unit sharing the escalated lane
   after drive                  units=[('u1', 'FAILED'), ('u2', 'BLOCKED'), ('u3', 'DONE')] steps=1 state=WAITING_HUMAN
      u3 (healthy, same lane) worker calls: 1

=== D. ten consecutive steps after resolve-without-repair
   open steps before resolve: 1 | after ten steps: 1
   all human steps ever: 2
```

Reading each against DESIGN-round4 8.5:

* **A** is the design's own "founder resolves but does not repair" row. A
  byte-identical re-plan does not revive a FAILED unit (the revival rule in
  8.3 is scoped to SKIPPED, and 8.5's table says a FAILED unit's
  retry_count is never cleared), so the run correctly restates the
  condition once. Behaviour matches the design exactly.
* **B** is the "founder repairs and resolves" row: the run delivers, with
  u1 still FAILED and u2 DONE, and zero open steps.
* **C** shows the healthy lane-mate is NOT lost: it completed before the
  escalation and the escalation's block only ever touches PENDING/READY
  units (`block_lane_units`, tools/bm_store.py:13564 to 13567). Even
  without the BLOCKED view, `select_ready_units`' own blocked-lane query
  (tools/bm_store.py:13277 to 13283) makes a gated lane unselectable, so
  the reconcile adds no new collateral.
* **D** is the anti-spam property: ten consecutive `step()` calls after a
  resolve queue exactly one new step.

One wording observation, not a finding: the escalation text says "Re-plan
or repair unit u1", and a founder who re-submits the SAME graph (the
natural reading of "re-plan") gets case A, which does nothing. Only
changing u1's definition, or dropping and re-adding it, moves it. Worth a
clearer sentence.

---

## The stop_reason enum, value by value

Every value constructed and driven. `/tmp/r4probe/p02_reason_matrix.py`,
`p06_contention.py`, `p07_enum_matrix.py`, `p03_nothing_selectable.py`,
`p10_contract_pause_loop.py`.

| Value | Constructed by | Result |
|---|---|---|
| `TERMINAL` | `engine.stop()` then drive | 1 step, `TERMINAL`, state STOPPED. Correct. |
| `DELIVERED` | step on an already-DELIVERABLE_READY run | Correct on that step, but NEVER set on the wave that actually delivers through the settle path (L4-F1). |
| `FOUNDER_WAITING`, PAUSED | founder pause | Correct. Misdirecting when the cause is a paused CONTRACT (L4-F2). |
| `FOUNDER_WAITING`, all founder-gated | dead dependency escalation | Correct when reached from `step()`; lost when reached through settle (L4-F1, probe p09 case C shows `reasons: [None, None]`). |
| `FOUNDER_WAITING`, done-definition fails | failing done_definition | Correct on the second step; the FIRST execution is silent (L4-F1 reproduction C). |
| `FOUNDER_WAITING`, `_may_dispatch` False | run VERIFYING with an open dispatch | Reason is defensible, note is wrong (L4-F4). |
| `SPEND_STOP` | 85 of 100 tokens spent, soft-stop | 1 step, `SPEND_STOP`, zero worker calls. Correct. |
| `OUTAGE` | worker answers "unavailable" | 1 step, `OUTAGE`, 1 worker call, run FAILED_RECOVERABLE. Correct. |
| `CONTENTION` | foreign fence, and the re-await route | Correct, honest note, no retry burned, proceeds next step. |
| `IN_FLIGHT` | production-shaped async park | 1 step, `IN_FLIGHT`, 1 worker call. Correct. |
| `NOTHING_SELECTABLE` | gated upstream lane, ungated downstream unit | WRONG value for a founder-gated run (L4-F3). |

No state I could construct maps to NO enum value: `_finish` sets the field
unconditionally (`summary.setdefault("stop_reason", None)`,
tools/bm_controller.py:543) and every `step()` return goes through it.
What I found instead is three states that map to the value `None`
("keep going") when the wave in fact reached a park decision, and one that
maps to the wrong member.

---

## Regressions: every class run on its own

`python3 -m unittest test_bm_controller.<class>` from
/Users/khalil.maaouni/Documents/BrotherModeUp/tools, one class per
invocation. `tools/test_all.py` was not run.

**The ten fault tests plus the four originals most at risk:**

```
TestFault1KilledBetweenResultAndCommit                       Ran 1 test  OK
TestFault2DuplicateResult                                    Ran 1 test  OK
TestFault3DependencyChangedOutputInvalidatesEvidence         Ran 1 test  OK
TestFault4WorkerHangs                                        Ran 1 test  OK
TestFault5MalformedOutput                                    Ran 1 test  OK
TestFault6CostCeilingReached                                 Ran 1 test  OK
TestFault7FounderCancelsDuringFanOut                         Ran 1 test  OK
TestFault8RestartWithNewerWorkflowVersion                    Ran 1 test  OK
TestFault9ProviderOutageThenRecovery                         Ran 1 test  OK
TestFault10RollbackItselfFails                               Ran 1 test  OK
TestExecutorCannotSelfApprove                                Ran 1 test  OK
TestRevokedContractMidUnit                                   Ran 1 test  OK
TestHumanBlockedLaneDoesNotStallIndependentLane              Ran 1 test  OK
TestDuplicateControllerAndStaleHeartbeatAdoption             Ran 2 tests OK
```

**Every refutation-born class, rounds 1 to 3:**

```
TestF1AsyncRejectWhoseRollbackAlsoFails                        Ran 1 test   OK
TestF2EveryWriteScopePathIsGateChecked                         Ran 3 tests  OK
TestF3AsyncSpendAfterARevoke                                   Ran 1 test   OK
TestF4DependentOfAFailedUnitDoesNotStallTheRun                 Ran 2 tests  OK
TestR2F1LateResultOnARunStateThatCannotReachVerifying          Ran 3 tests  OK
TestR2F1CheckTimeoutsWalksTheSameStatesAsReceiveResult         Ran 2 tests  OK
TestR2F2TheRevisionEveryPathWasJudgedUnder                     Ran 3 tests  OK
TestR2F4DeadDependenciesAndFounderGatedLanes                   Ran 4 tests  OK
TestR3PausedIsAFounderOnlyGate                                 Ran 6 tests  OK
TestR3TheSummaryStateIsTheStoreState                           Ran 3 tests  OK
TestR3StopReasonDrivesEveryLoopDriver                          Ran 6 tests  OK
TestR3TheExecutingWedgeUnwinds                                 Ran 2 tests  OK
TestR3TheSkippedLifecycleClosesAtTheSource                     Ran 5 tests  OK
TestR3BlockedIsAMaterialisedViewOfTheLaneGate                  Ran 4 tests  OK
TestR3EveryDispatchRouteIsGateChecked                          Ran 4 tests  OK
TestR3ForeignAndCancelledDispatchIdsRefuse                     Ran 3 tests  OK
TestR3LateResultKeepsItsSpendAndItsFounderRecord               Ran 4 tests  OK
TestR3FailedRecoverableReachesVerifying                        Ran 2 tests  OK
TestR3TheClaimedCrashWindowRecovers                            Ran 2 tests  OK
TestNoSQLGuard                                                 Ran 4 tests  OK
TestEndToEndE4                                                 Ran 1 test   OK
```

**Store classes touched by round 4, including the one the store writer
reported as blocked:**

```
TestGlobAllowedPathsAreDepthExact                  Ran 4 tests   OK
TestGlobNarrowingBreaksNothingElse                 Ran 2 tests   OK
TestGateCheckReturnsAVerdictInsteadOfRaising       Ran 3 tests   OK
TestGateCheckVerdictComesFromOneContractRead       Ran 1 test    OK
TestUpsertUnitsClosesTheSkippedLifecycle           Ran 4 tests   OK
TestUpsertUnitsRefusesANonPathWriteScopeEntry      Ran 1 test    OK
TestReleaseClaimedUnit                             Ran 2 tests   OK
TestGetDispatch                                    Ran 2 tests   OK
TestControllerUpsertUnits                          Ran 15 tests  OK
TestGateCheckPathIsContainmentNotOverlap           Ran 3 tests   OK
```

**All three of FIX-round4-controller-report.md's collisions are resolved
in the tree I attacked**, and I verified each remedy by reading it, not by
trusting the report:

* Collision 1, TestFault8: the `block_lane_units` call at
  tools/test_bm_controller.py:712 is now followed by a `queue_human_step`
  in the same lane at 719 to 722, with a comment naming DESIGN-round4 8.4.
* Collision 2: the DELIVERABLE_READY late-result test is retired with the
  note at tools/test_bm_controller.py:1581 to 1594 (see L4-F6).
* Collision 3, TestFault9: line 800 now asserts
  `self.assertEqual(s1["state"], "FAILED_RECOVERABLE")` with a comment
  naming law L2.

**The AST guard is genuine, not a restatement.** I read
`test_every_worker_handoff_sits_behind_the_one_choke_point`
(tools/test_bm_controller.py:2960 onwards). It parses the module, collects
the enclosing function name of every `self.worker.run` call and of every
`self._authorise_dispatch` call, asserts the first set is exactly
`["_resume_dispatched", "step"]`, and asserts it is a subset of the
second. A third worker route, or a worker route that bypasses the choke
point, fails it.

**E4 fixture, read for drift.** `run_states_visited` is
`[READY, READY, READY, READY, DELIVERABLE_READY, DELIVERABLE_READY]`,
`final_state` DELIVERABLE_READY, `duplicate_work_count` 0, four DONE units,
one open human step in lane `release` (a lane no unit occupies, so the
reconcile writes nothing there, exactly as DESIGN-round4 18.5 predicts).
Two observations:

1. The artifact's `founder_gated_remainder` block is computed by the TEST
   from the store (tools/test_bm_controller.py:3597 to 3601), not from
   `summary["founder_gated"]`. So E4 does not exercise the engine block
   L4-F1 shows is unreachable, and its name makes it look as though it
   does.
2. The artifact records no `stop_reason` at all. Round 4's central new
   field has no end-to-end evidence in the round's own end-to-end
   artifact.

**Disclosure: I changed four bytes-worth of lines in a repository file.**
Running `TestEndToEndE4` regenerates
docs/program/absolute-lead/evidence/L03/E4-endtoend.json by that class's
own documented design. `git diff --stat` on it after my run:

```
 docs/program/absolute-lead/evidence/L03/E4-endtoend.json | 8 ++++----
 1 file changed, 4 insertions(+), 4 deletions(-)
```

and the diff is four `checkpoint_ref` uuid4 values and nothing else, which
independently confirms FIX-round4-controller-report.md section 4.3's claim
about 18.5. I did not attempt to restore the previous uuids, because doing
so would mean writing bytes into a file I was not authorised to write and
would discard the last real run's evidence.

---

## Attempts

Thirty distinct attack ideas. Seven produced findings.

| # | Idea | Outcome |
|---|---|---|
| 1 | Count done_definition executions per `run_to_completion` against 9.1's "1" | HIT (L4-F1 c) |
| 2 | `stop_reason` on the ordinary happy path | HIT (L4-F1) |
| 3 | Is `summary["founder_gated"]` ever reachable | HIT (L4-F1) |
| 4 | A state that maps to the WRONG enum member | HIT (L4-F3) |
| 5 | Contention as a false founder park, fresh route | MISS, correct |
| 6 | Contention on the re-await route | MISS, correct |
| 7 | `SPEND_STOP`, soft stop with units selectable | MISS, correct |
| 8 | `TERMINAL` | MISS, correct |
| 9 | `OUTAGE` | MISS, correct |
| 10 | `IN_FLIGHT`, the production async park | MISS, correct |
| 11 | LV 1's EXECUTING wedge | MISS, genuinely closed |
| 12 | A run VERIFYING with an open dispatch | HIT (L4-F4) |
| 13 | A run PAUSED because the CONTRACT is paused | HIT (L4-F2) |
| 14 | An empty lane defeating the escalation anti-spam marker | MISS, `upsert_units` defaults lane to "default" (tools/bm_store.py:13100) |
| 15 | The pairing law as a measured property | MISS, holds |
| 16 | Byte-identical re-plan reviving a FAILED unit | MISS, matches design 8.3 and 8.5 |
| 17 | Changed re-plan plus resolve | MISS, recovers and delivers |
| 18 | Healthy collateral in an escalated lane | MISS, `block_lane_units` touches only PENDING/READY and the lane was unselectable anyway |
| 19 | Ten consecutive steps after a resolve without repair | MISS, exactly one step queued |
| 20 | A unit DISPATCHED behind a closed dispatch | HIT (L4-F5) |
| 21 | A unit CLAIMED with a CANCELLED dispatch | MISS, unreachable (`upsert_units` cancels only for SKIPPED units) |
| 22 | A unit RESULT_IN behind a closed dispatch | MISS as a separate case, same class as 20 |
| 23 | Does the retired test's replacement pin all three claimed properties | HIT (L4-F6) |
| 24 | Test count against 17.3's numeric floor | HIT (L4-F7) |
| 25 | Is the AST choke-point guard a restatement of the code | MISS, genuine |
| 26 | E4 fixture drift | MISS on drift (four uuids only); two observations recorded |
| 27 | A mixed wave: one result recorded AND one worker unavailable | Observation: `any_recorded` swallows the `OUTAGE` reason, so the unavailable worker is asked twice across two waves instead of once. Bounded, not a spin. |
| 28 | Any `block_lane_units` caller outside the controller and store | MISS, none in the repository |
| 29 | `_reconcile_lane_blocks`' `units=None` parameter | Observation: dead, no caller passes it (call sites 622, 709, 1109, 2086) |
| 30 | Does a soft spend stop stop the re-await | Observation: no. `_resume_dispatched` runs at line 700, before `may_start_new` is consulted at 717. Defensible (a re-await opens no new dispatch) but the method's own docstring claims a tripped breaker drains instead of re-asking. |

Idea rounds 21 to 30 produced one finding and nine misses or observations,
which is the stopping condition the brief sets.

---

## What I did NOT check

* **`python3 tools/test_all.py` and the full controller and store suites**
  were not run, as instructed. Every green line above is a single class.
  I make no claim about any class I did not name.
* **The CLI section of tools/test_bm_controller.py** (six classes, 18
  tests) was not run. My CLI evidence is my own subprocess probes, not
  those tests.
* **tools/test_bm_autonomy.py and tools/test_bm.py** were not run. The
  autonomy suite consumes `gate_check` and `path_within_allowed`, which
  the store half changed; the other two lenses own that surface.
* **The authorisation lens's surface**: glob containment,
  `path_within_allowed`, `gate_check`'s no-raise contract, the one-contract-read
  property, `_gate_check_write_scope`'s straddle machinery, the fence
  overlap semantics. I read them to understand the control flow and I
  attacked none of them.
* **Two real operating-system processes against one store.** Every probe
  here is a single process. Every concurrency-shaped case I noticed
  (`_deliver_or_hold`'s stale `cur` across the done_definition subprocess,
  SM G's own window) is recorded as unexplored, not as refuted.
* **A real process kill.** L4-F4 and L4-F5 were constructed with direct
  `set_run_state` and `record_verification` calls that stand in for the
  first half of a two-call window. I did not kill a process to produce
  them, and both severities are set accordingly.
* **`check_timeouts` under a real clock.** I read it and traced its new
  `_open_dispatch_units` iteration and its PAUSED guard, but every probe I
  ran drove the engine, not the timeout path. Note that it is still wired
  to no CLI subcommand, so in production nothing ever times a hung
  dispatch out; that is stated in the method's own docstring and is not a
  round-4 change.
* **docs/FULL-AUTO.md, docs/KNOWN-LIMITS.md, docs/AUTONOMY.md and
  references/autonomy.md.** I did not review the documentation half of the
  round at all. FIX-round4-controller-report.md records that
  docs/AUTONOMY.md was left unwritten; I neither confirmed nor refuted
  that.
* **`_report_trace` and `cmd_step` output text beyond the two lines my
  probes printed.** No CLI subprocess test in the repository asserts the
  `reason:` line, the `held` message or `plan`'s new counts, and I added
  none.
* **Performance.** `_open_dispatch_units` is called up to four times per
  `step()` and is O(units x dispatches) with one store call per unit. I
  measured nothing.

---

Probe scripts, for anyone re-running them:
`/tmp/r4probe/h.py` (shared harness), `p01_done_definition_count.py`,
`p02_reason_matrix.py`, `p03_nothing_selectable.py`,
`p04_delivered_reason_lost.py`, `p05_cli_founder_gated.py`,
`p06_contention.py`, `p07_enum_matrix.py`, `p08_verifying_wedge.py`,
`p09_reconcile_law.py`, `p10_contract_pause_loop.py`,
`p11_cli_pause_loop.py`, `p12_pairing_and_stranded.py`,
`p13_retired_property.py`. They are in a session temp directory and will
not survive a reboot; every one of them is short enough to rebuild from
the reproductions quoted above.
