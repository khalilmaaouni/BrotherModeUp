# REFUTATION 3, state-machine lens: the F1 round-3 fixes

Target: the CURRENT working tree of /Users/khalil.maaouni/Documents/BrotherModeUp,
tools/bm_controller.py (unstaged round-3 change) against tools/bm_store.py
schema 15. Read only except this file. No git state was changed. No full
suite was run. Every probe built its own throwaway Store under a fresh
tempfile.TemporaryDirectory in /tmp, or a throwaway BROTHERMODE_ROOT for
the real-CLI probes; no .brothermode inside any real project was touched.

Lens: state-machine correctness only. F2's containment work and F3's spend
guard were touched only where a state question ran through them.

---

## Verdict lines

| Surface | Verdict | Attempts | What survives |
|---|---|---|---|
| 1. `_RESULT_WALK_EDGES` / `_REJECTABLE_STATES` derivation (212 to 301) | STANDS as a derivation; ONE break inside the set | 5 | the set is a true fixed point of its own edge data and no walk edge can be refused by run data, but FAILED_RECOVERABLE is admitted by identity and the implementation cannot move it, so the "VERIFYING before any verification" invariant is violated for that one member |
| 2. `_handle_late_result` (662 to 724) | REFUTED | 9 | ordering and the 14-state matrix hold, but the branch silently drops the result's SPEND, delivers nothing to the founder when the unit is at its retry ceiling, makes `step` report a state the store does not hold, and manufactures a BLOCKED status the rest of the engine does not understand |
| 3. `check_timeouts` (725 to 788) | STANDS | 6 | the walk, the late-result routing and the `_settle_after_wave` convergence are correct from every one of the 14 reachable states, dirty and clean; one residual needs a concurrent writer and self heals |
| 4. `_reject` consequence order (1214 to 1292) | STANDS on the order; ONE break beside it | 5 | the founder warning and the fence release precede the state move in every state, and the interruption skip can never lose the warning; but on the branch where the run SURVIVES, the unit is left READY and unblocked, so a surviving run re-dispatches a possibly dirty write scope |
| 5. Disclosed residual 3 (`_resume_result_in_and_orphans` from PAUSED and STOPPING) | STOPPING half REFUTED as unreachable; PAUSED half is WORSE than disclosed | 4 | no shipped command sequence ever leaves a run observably in STOPPING, so the bad re-queue on STOPPING is not reachable; the PAUSED re-queue is not "arguably correct", because the very next `step` re-dispatches the re-queued unit while the run is still PAUSED |

Plus three findings that are pure state-machine defects and sit beside,
not inside, the five named surfaces. The first is the most serious thing
in this report.

| Finding | Severity | One line |
|---|---|---|
| A. `step` dispatches new units while the run state is PAUSED | HIGH | reproduced through the real shipped CLI; the same change declares PAUSED unjudgeable for results while leaving it authorising for dispatches |
| B. `_deliver_or_hold`'s new legal-edge guard performs the founder-only PAUSED to READY edge | HIGH | a PAUSED run un-pauses itself and declares its deliverable ready |
| C. `run_to_completion` still burns every max_steps on the ORDINARY async park | MEDIUM | undisclosed residual; the fix report discloses only the soft-spend-stop spin |

---

## Findings, most serious first

### A. A PAUSED run dispatches new work. HIGH.

Code path: `step` at tools/bm_controller.py:486 calls `_walk_to_executing`
(tools/bm_controller.py:1340), which moves only CHECKPOINTED, WAITING_HUMAN
and READY. From PAUSED it is a SILENT NO-OP, and nothing downstream
re-checks. `record_checkpoint` (489), `_claim_and_dispatch` (498), the fence
claim and `record_dispatch` all proceed, and the worker is handed the brief.

This is the mirror image of what round 3 established. The same change
derives `_RESULT_WALKABLE_STATES` (tools/bm_controller.py:255) and puts
PAUSED outside it, with `_walk_reaches_rejectable`'s own docstring
(tools/bm_controller.py:229 to 238) saying "un-pausing is a founder action,
design section 1's own words for `resume`". So the engine will not move a
PAUSED run to judge a result, and will dispatch new work from it.

Reproduced through the REAL shipped command line, as subprocesses, against
a throwaway BROTHERMODE_ROOT (probe p08_cli_paused_dispatch.py). Only the
project row and the signed contract were created in process; every command
below is a genuine subprocess of tools/bm_controller.py and
tools/bm_autonomy.py.

```
  $ bm_controller start --project p1 --outcome "ship it" --done-definition true ...
    exit=0  | controller run 24ffc2fb... started for project p1 (state NEW)
  $ bm_controller plan --project p1 --units-json [u1, u2 depends on u1] ...
    exit=0  | planned 2 unit(s)
  $ bm_controller step --project p1 ...
    exit=0  | state EXECUTING | dispatched: u1
  $ bm_controller record-result --project p1 --dispatch-id 2b352868... ...
    exit=0  | unit u1 accepted
  $ bm_autonomy pause --project p1 --reason "founder pause" ...
    exit=0  | project p1 contract -> paused (revision 2)
  $ bm_controller step --project p1 ...
    exit=0  | state PAUSED | dispatched: (none) | note: contract is paused
  $ bm_controller status --project p1
    exit=0  | project p1: run 24ffc2fb..., state PAUSED
            | units: 2 total   PENDING: 1   DONE: 1
  $ bm_autonomy resume --project p1 --reason "founder resume" ...
    exit=0  | project p1 contract -> live (revision 3)

  ---- the founder does NOT run `bm-controller resume` ----

  $ bm_controller step --project p1 ...
    exit=0  | {"controller_brief": {"attempt": 1, "objective": "unit u2", ...}}
            | run 24ffc2fb...: state PAUSED
            | dispatched: u2
            | note: ... every dispatched unit is pending (async); parked in EXECUTING
  $ bm_controller status --project p1
    exit=0  | project p1: run 24ffc2fb..., state PAUSED
            | open dispatches (record a result for each):
            |   u2: dispatch 41e2413e...

  FINAL: run state=PAUSED units={'u1': 'DONE', 'u2': 'DISPATCHED'}
```

Three separate consequences in that last pair of commands:

1. A unit brief was handed to the orchestrating model, a fence was claimed
   and a dispatch row was written, while the run's durable state says
   PAUSED. `bm-controller status`, the founder's one window on this, says
   PAUSED with an open dispatch.
2. The note the founder reads says "parked in EXECUTING" for a run the same
   command's own first line calls PAUSED.
3. The engine has now dispatched work whose result it is guaranteed to
   refuse: `receive_result` will read PAUSED, find it outside
   `_RESULT_WALKABLE_STATES`, and route the answer to `_handle_late_result`,
   which rejects it, BLOCKS the unit and queues a founder step. Confirmed at
   engine level in probe p03_dispatch_from_paused.py and in the matrix rows
   below.

`bm-controller resume` exists (tools/bm_controller.py:2294) and would have
moved PAUSED to READY, but nothing requires it and nothing refuses `step`
without it. The contract-level pause and the run-level pause are two
different objects and only one of them is enforced.

Honest attribution: the `_walk_to_executing` no-op predates round 3. What
round 3 changed is that `_reject` can no longer RAISE from PAUSED
(the new legal-move guard at tools/bm_controller.py:1246), so this path now
runs to completion quietly instead of failing loudly. Probe
p02_paused_run_live_contract.py, case B, drives exactly that: a PAUSED run
re-awaits its dispatch, the rollback fails, and

```
  after the re-await           run=PAUSED  units={'u1': 'READY'} steps=0
  NEXT step dispatched: ['u1'] state: PAUSED
  after the next step          run=PAUSED  units={'u1': 'FAILED'} steps=1
  dispatch rows u1: [(1, 'REJECTED'), (2, 'REJECTED')]
  RESULT: unit with a DIRTY write scope re-dispatched: True
```

### B. A PAUSED run un-pauses itself and declares its deliverable ready. HIGH.

Code path: `_deliver_or_hold`'s new guard, tools/bm_controller.py:1577 to
1592. It reads the current state, and when the state is not READY or
CHECKPOINTED it asks only whether READY is a LEGAL move
(`"READY" not in bs.CONTROLLER_STATE_TRANSITIONS.get(cur, ())`), then takes
it. PAUSED to READY is legal (tools/bm_store.py:2556), and it is precisely
the founder-only `resume` edge `bm-controller resume` exists to perform and
that `_walk_reaches_rejectable` refuses to walk. Legality is not the right
test here; ownership of the edge is.

Probe p09_deliver_guard_and_spin.py, part a, shipped commands only:

```
  step dispatched: ['u1', 'u2']
  record-result u1 -> u1
  record-result u2 -> rejected                (done_check fails, retry 1)
  units: {'u1': 'DONE', 'u2': 'READY'} run: READY
  step re-dispatched: ['u2'] run: EXECUTING
  after bm-autonomy pause + step: run = PAUSED
  record-result u2 (attempt 2) -> rejected     (late result, ceiling hit)
  units: {'u1': 'DONE', 'u2': 'FAILED'} run: PAUSED
  step summary: {'state': 'DELIVERABLE_READY', 'note': 'deliverable ready'}
  RUN STATE: PAUSED -> DELIVERABLE_READY
  RESULT: the founder's pause was reversed by the engine and the run
          declared its deliverable ready: True
  `bm-controller complete` then works: {'state': 'COMPLETE', 'changed': True}
```

The full table of what the guard permits, printed from
`bs.CONTROLLER_STATE_TRANSITIONS` in the same probe:

```
  READY / CHECKPOINTED         -> delivers in place            (intended)
  PLANNING, VERIFYING, WAITING_HUMAN, DELIVERABLE_READY,
  PAUSED, FAILED_RECOVERABLE   -> MOVES IT to READY first
  NEW, ORIENTING, EXECUTING, COMPLETE, STOPPING, STOPPED,
  FAILED_TERMINAL              -> refuses, stays put           (intended)
```

Two of those movers are wrong for reasons the guard cannot see: PAUSED is
the founder's edge, and DELIVERABLE_READY means the run is walked back to
READY and forward to DELIVERABLE_READY again on every later `step`,
re-running the whole done_definition and writing two extra state rows each
time.

Honest attribution: the pre-round-3 code took the same PAUSED to READY move
unconditionally, so the BEHAVIOUR is pre-existing. What round 3 added is a
guard that reads as though the question had been settled, and a docstring
("Converge along a LEGAL edge or not at all") that states the wrong
predicate. The refutation is of the claim, not of a newly introduced bug.

### C. Every late result silently drops its SPEND. HIGH. Regression.

Code path: `receive_result` records the result (tools/bm_controller.py:610),
reads the state (613), and returns through `_handle_late_result` at 614 to
616. The `record_spend` block lives at 636 to 651, AFTER that return. The
pre-round-3 code recorded the spend before it reached the state move, so the
tokens landed on the meter and only the state move failed.

Probe p14_before_after_spend.py runs the identical sequence against the
PRE-round-3 tree (`git show :tools/bm_controller.py` plus
`git show :tools/bm_store.py`, both from the index so the pair is
self-consistent) and against the working tree:

```
== PRE-round-3 tree (git index) ==
  before   run state at record-result: DELIVERABLE_READY
  before   receive_result -> u1
  before   spend tokens 0 -> 9000, minutes 0 -> 120

== working tree ==
  after    run state at record-result: DELIVERABLE_READY
  after    receive_result -> rejected
  after    spend tokens 0 -> 0, minutes 0 -> 0
```

The most reachable variant needs four shipped commands and no re-plan,
because `bm-controller stop` stops the RUN and leaves the CONTRACT live:

```
== spend loss via `bm-controller stop` (the contract stays LIVE) ==
  run: STOPPED | contract: live rev 1
  receive_result -> rejected
  spend tokens 0 -> 0, minutes 0 -> 0
```

That is: `start`, `plan`, `step`, `stop`, `record-result --tokens 7500
--minutes 90`, and 7500 tokens of real worker cost never reach the meter
the contract's ceiling is computed from. The circuit breaker under-counts by
exactly the amount of every late result:

```
  ceilings 10000 tokens / 1000 minutes; after a 9999/999 late result the
  verdict is 'ok' at tokens=0 minutes=0
```

The old behaviour was also wrong (it ACCEPTED the unit on a delivered run,
which is the thing F1 set out to stop). The trade made was an over-accept
for a spend leak; the leak was not named in the fix report.

### D. A late result on a unit at its retry ceiling tells the founder nothing at all. HIGH.

`_handle_late_result`'s own docstring (tools/bm_controller.py:662 to 689)
promises five consequences, the fifth being "an interruption names the late
result and the run state, so the founder can see WHY a real result was not
accepted". Two guards remove every founder-visible one of them at once:

- the founder step and the lane block are inside
  `if outcome["status"] != "FAILED"` (tools/bm_controller.py:697), so a unit
  whose retry ceiling is already spent gets neither;
- `_record_interruption` (tools/bm_controller.py:1279) returns None when the
  contract is not live, and a stopped or revoked contract is one of the most
  common reasons the run is in a late-result state at all.

Probe p06_late_result_battery.py, case B, shipped commands only
(`step`, `record-result`, `step`, `bm-autonomy stop`, `step`,
`record-result`):

```
  after rejection 1: unit=READY retry=1 run=READY
  re-dispatched: ['u1'] run: EXECUTING
  after bm-autonomy stop + step: run=STOPPED note=draining: contract is stopped
  receive_result -> rejected
  unit: FAILED dispatch: REJECTED
  founder (open human steps, interruptions): before=(0, 0) after=(0, 0)
  RESULT: a real result was discarded with NO new founder-visible record
          at all: True
```

The founder ran a worker, the worker did the work, the answer arrived, and
the only trace is a REJECTED dispatch row nothing surfaces.

### E. `bm-controller step` reports a state the store does not hold. HIGH.

`_handle_no_ready_units` writes `summary["state"] = "WAITING_HUMAN"`
unconditionally at tools/bm_controller.py:1444, while the actual move at
1440 to 1443 happens only when the run is READY or CHECKPOINTED. Round 3
widened the branch that reaches line 1444 (`_is_founder_waiting`,
tools/bm_controller.py:1454, now counts a PENDING or READY unit in a gated
lane, not only a BLOCKED one), and round 3's `_handle_late_result` is what
manufactures the BLOCKED units that trip it, so the mismatch is reachable in
strictly more situations than before.

`step` returns that summary straight to the caller at
tools/bm_controller.py:477 to 478 with no re-read from the store.

Probe p06_late_result_battery.py, case A, shipped commands only
(`start`, `plan`, `step`, `plan` again dropping u1, `step`, `record-result`,
`step`):

```
  wave 1 dispatched=['u1', 'u2'] completed=['u2'] run=CHECKPOINTED
  after re-plan: {'u1': 'SKIPPED', 'u2': 'DONE'}
  step -> run=DELIVERABLE_READY note=deliverable ready
  u1 dispatch still open: DISPATCHED
  receive_result -> rejected
  run: DELIVERABLE_READY units: {'u1': 'BLOCKED', 'u2': 'DONE'}
  step 1: summary state=WAITING_HUMAN   store state=DELIVERABLE_READY
  step 2: summary state=WAITING_HUMAN   store state=DELIVERABLE_READY
  MISMATCH between the step summary and the persisted run state: True
```

`bm-controller step --json` prints WAITING_HUMAN; `bm-controller status`,
reading the same store a second later, prints DELIVERABLE_READY.

The same lie is load bearing: `run_to_completion` stops on
`summary["state"] in _RUN_TO_COMPLETION_STOP_STATES`
(tools/bm_controller.py:562), so the loop terminates because of a state the
run is not in. Probe p07_stopping_and_blocked.py, case 4, on a run wedged in
EXECUTING with one BLOCKED unit:

```
  run=EXECUTING units={'u1': 'BLOCKED'}
  run_to_completion steps: 1  last summary state: WAITING_HUMAN
  store state: EXECUTING
```

### F. BLOCKED is not in `_DEAD_DEPENDENCY_STATUSES`, and round 3 is what creates BLOCKED units. HIGH.

`_DEAD_DEPENDENCY_STATUSES` is `("FAILED", "SKIPPED")`
(tools/bm_controller.py:300) and `_block_unreachable_units` tests it at
tools/bm_controller.py:1515. Round 3 added two new producers of BLOCKED
units (`_handle_late_result` at tools/bm_controller.py:706, and
`_block_unreachable_units` itself at 1553), and no production caller of
`Store.unblock_lane_units` exists anywhere:

```
$ grep -rn "unblock_lane_units" tools/*.py | grep -v test_
tools/bm_controller.py:23    (docstring: the store method list)
tools/bm_controller.py:680   (docstring: "reversible through unblock_lane_units")
tools/bm_controller.py:1488  (docstring: "BLOCKED is reversible")
tools/bm_store.py:13314      (the definition)
tools/bm_store.py:13344      (its own attribution write)
```

So a BLOCKED dependency is exactly as permanently unreachable as a FAILED
one, and the escalation that exists to name that condition does not
recognise it. Probe p15_blocked_is_not_dead.py:

```
_DEAD_DEPENDENCY_STATUSES = ('FAILED', 'SKIPPED')

== a live run whose only blocker is a BLOCKED unit ==
  after stop + record-result: {'u0': 'DONE', 'u1': 'BLOCKED', 'u2': 'PENDING'}
  gated lanes: {'alpha'}
  is u2 founder-waiting by the round-3 test? False
  is u2's dependency DEAD by the round-3 test? False

== the same shape on a run that is NOT terminal ==
  run=PAUSED units={'u1': 'BLOCKED', 'u2': 'PENDING'}
  after resolving the human step, units: {'u1': 'BLOCKED', 'u2': 'PENDING'}
  run_to_completion steps: 1 of 10
  final store state: READY  summary state: READY
  last note: no unit is currently selectable (dependencies unmet or in
             flight); waiting; nothing is in flight either, so the run is
             parked until a founder acts
  units: {'u1': 'BLOCKED', 'u2': 'PENDING'}
  open founder steps naming u2: []
```

The run rests in READY with no delivery, no terminal state and no founder
step naming u2, which is F4's symptom sentence word for word, arrived at
through a status round 3 itself introduced. Credit where due: the F4
no-progress stop DOES fire here (1 step of 10, not 10 of 10), so
`run_to_completion` no longer spins. The stall it was meant to surface is
still not surfaced.

Resolving the queued human step does not help: `unblock_lane_units` is never
called, so the unit stays BLOCKED and `select_ready_units` never returns it
again. Probe p07_stopping_and_blocked.py, case 3:

```
  after the late result: {'u1': 'BLOCKED', 'u2': 'DISPATCHED'} steps/interr: (1, 1)
  after resolving every human step: {'u1': 'BLOCKED', 'u2': 'DISPATCHED'} open steps: 0
  select_ready_units now: []
```

A re-plan (`bm-controller plan`) does rescue it, because `upsert_units`
recomputes the status of any unit it redefines. That escape hatch is real
and is why I am calling the permanence MEDIUM rather than HIGH; the missing
escalation above is the HIGH half.

### G. The state read and the handler body are not atomic. MEDIUM.

`receive_result` reads the state at tools/bm_controller.py:613 and branches
on it at 614. A concurrent writer moving the run between that read and the
body puts the call on the wrong side of the branch. Probe
p06_late_result_battery.py, case D, with a delegating store wrapper firing
the move inside the engine's own `get_run`:

```
  walkable read, then STOPPED before the walk (state at read: EXECUTING)
    [concurrent writer] run -> STOPPED
    receive_result -> rejected
    run: STOPPED unit: READY fence: parked steps/interr: (1, 1)

  unwalkable read, then back to a walkable state (state at read: PAUSED)
    [concurrent writer] run -> EXECUTING
    receive_result -> rejected
    run: EXECUTING unit: BLOCKED fence: parked steps/interr: (2, 1)
```

The first row is REFUTATION-2 reproduction 1's own secondary observation
reproduced on the fixed tree: a STOPPED run gaining a READY unit, with no
BLOCKED pairing and no "the run must not start new work" founder step. The
second row leaves the run wedged in EXECUTING with its only unit BLOCKED,
which is the case that produces finding E's `run_to_completion` lie.

### H. `_reject` leaves the unit selectable on the one branch where the run survives. MEDIUM.

Order inside the dirty-rollback branch (tools/bm_controller.py:1240 to 1259)
is exactly as the fix claims: `_warn_dirty_write_scope`, then
`_release_fence`, then the state move, and the move only when
`CONTROLLER_STATE_TRANSITIONS` allows FAILED_TERMINAL from where the run
stands. I attacked the order five ways and it held (see the attempts log).
The interruption skip cannot lose the warning either: `queue_human_step`
(tools/bm_store.py:12342) needs only SOME contract in any state, and
`Store.open_run` refuses to open a run at all without a LIVE contract, so by
the time any rejection path exists a contract row always exists. Probed:

```
$ python3 p04_stopping_wedge.py
contracts on file: None
begin RAISED: OwnershipRefused project 'p1' has no live contract (no
contract); a controller run needs a live authorisation to gate_check against.
```

The gap is what the branch does NOT do. `_handle_late_result` pairs its
rejection with `queue_human_step` plus `block_lane_units` so the unit ends
BLOCKED; `_reject` does not, and its warning goes to the hard-coded lane
"default" (tools/bm_controller.py:1273) rather than the unit's own lane. On
every state where FAILED_TERMINAL is legal that does not matter, because the
run is terminal a line later. On the `else` branch it does: the run survives
and the unit is READY. Probe p02_paused_run_live_contract.py, case B, quoted
in full under finding A, ends with a second dispatch of a unit whose
rollback had just failed. Reaching `_reject` from a surviving state needs a
worker adapter that answers synchronously through `_resume_dispatched`; the
production `RecordIntentWorker` always returns "pending", so this is an SDK
caller path, not a shipped-CLI one.

### I. FAILED_RECOVERABLE is in the walkable set but the walk cannot move it. MEDIUM.

`_RESULT_WALKABLE_STATES` admits FAILED_RECOVERABLE because it is already in
`_REJECTABLE_STATES`, not because any edge carries it there. Neither
`_walk_to_executing` (tools/bm_controller.py:1340) nor `_ensure_verifying`
(1364) can move it. The rejection is therefore legal, which is what the
derivation was checking, but the OTHER invariant the same method's comment
states at tools/bm_controller.py:620 to 622 is violated: "a result is
recorded, so the run moves to VERIFYING BEFORE any verification runs (design
step 10). Omitting it is not cosmetic."

Probe p16_verifying_invariant.py reads the run's persisted state from inside
the CheckRunner, so the value printed is the state at the exact moment each
founder-authored command runs:

```
  start=EXECUTING           outcome=u1   [('true','VERIFYING'), ('verify.sh','VERIFYING'), ('echo done','CHECKPOINTED')]
                                          final=DELIVERABLE_READY unit=DONE
  start=CHECKPOINTED        outcome=u1   [('true','VERIFYING'), ('verify.sh','VERIFYING'), ('echo done','CHECKPOINTED')]
                                          final=DELIVERABLE_READY unit=DONE
  start=WAITING_HUMAN       outcome=u1   [('true','VERIFYING'), ('verify.sh','VERIFYING'), ('echo done','CHECKPOINTED')]
                                          final=DELIVERABLE_READY unit=DONE
  start=FAILED_RECOVERABLE  outcome=u1   [('true','FAILED_RECOVERABLE'), ('verify.sh','FAILED_RECOVERABLE')]
                                          final=FAILED_RECOVERABLE unit=DONE
```

Three of the four members reach VERIFYING before the done_check; the fourth
never does, and its run is left in FAILED_RECOVERABLE with the unit DONE and
no delivery attempted, because `_settle_after_wave`
(tools/bm_controller.py:1392) returns early from any state that is not
CHECKPOINTED. A crash between the done_check and `mark_unit_done` in that
row leaves a durable state saying nothing was ever verified, which is the
exact durability property the walk exists to provide. FAILED_RECOVERABLE is
set only by `_handle_worker_result` on a worker status of "unavailable"
(tools/bm_controller.py:1112), which the production `RecordIntentWorker`
never returns, so this needs an SDK worker adapter.

### J. `run_to_completion` still burns every max_steps on the ORDINARY async park. MEDIUM. Undisclosed.

The F4 fix added a no-progress stop at tools/bm_controller.py:564 to 571,
gated on `summary.get("note") in _NO_PROGRESS_NOTES`. The note a parked
async wave actually writes is `_resume_dispatched`'s "re-awaited an
in-flight dispatch" (tools/bm_controller.py:896), which is in neither
constant, so the stop never fires for the shape the production worker
ALWAYS produces. Probe p09_deliver_guard_and_spin.py, part c:

```
  steps taken: 12 of max_steps=12
  worker invocations for u1: 12
  notes seen: ['no spend ceiling on file (no-data); starting units and sayin',
               're-awaited an in-flight dispatch (crash resume or provider-o']
  final state: EXECUTING
  RESULT: run_to_completion burned every step and re-invoked the worker on
          each one: True
```

With the production `RecordIntentWorker` that is the same unit brief printed
to stdout max_steps times, default 500, which is the exact symptom
`_drive_until_parked`'s docstring (tools/bm_controller.py:1913 to 1930) says
it was written to avoid. The shipped CLI is safe because `cmd_start` calls
`_drive_until_parked`, and nothing in production calls
`run_to_completion` at all (grepped: every hit in tools/ outside the tests
is a docstring). So this is an SDK and test surface, MEDIUM. It is a SECOND
`run_to_completion` spin beside the soft-spend-stop one the fix report
discloses as residual 4, and it is not mentioned.

### K. A dispatch id from a previous run crashes with an uncaught TypeError. MEDIUM.

`_handle_late_result` dereferences `self._unit_row(run_id, unit_id)`
(tools/bm_controller.py:690 and 700) and `receive_result` does the same at
652, but `_unit_row` (tools/bm_controller.py:1642) searches only the CURRENT
run's units, while `Store.record_result` accepts any dispatch id in the
project. A dispatch belonging to an earlier, now-terminal run resolves to
None. Probe p10_cross_run_dispatch.py:

```
== run 2 EXECUTING (walkable path) ==
  run 1 after stop: STOPPED   u1 dispatch: DISPATCHED
  receive_result RAISED: TypeError: 'NoneType' object is not subscriptable
  caught by the CLI's main() (BMStoreError, ValueError)? False
  the old dispatch is now: RESULT_IN

== run 2 STOPPED (late-result path) ==
  receive_result RAISED: TypeError: 'NoneType' object is not subscriptable
  caught by the CLI's main() (BMStoreError, ValueError)? False
  the old dispatch is now: REJECTED
```

On the late-result path the crash happens at line 700, AFTER
`record_verification` and `mark_unit_failed` have already committed, so the
old run's unit is resurrected with its retry count bumped, its dispatch is
REJECTED, and the fence park, the rollback and the interruption never run.
`main()` (tools/bm_controller.py:2409 to 2420) catches only `BMStoreError`
and `ValueError`, so a TypeError would surface as a raw traceback.

Reachability is the reason this is MEDIUM, and I verified the limit rather
than assuming it: `cmd_start` (tools/bm_controller.py:1983 to 1990) calls
`begin()` only when `get_run` returns None, and `get_run` returns the most
recent run whatever its state, so the shipped CLI can NEVER open a second
controller run for a project. Confirmed through the real CLI
(p12_cli_crash_and_complete.py):

```
  $ bm-controller stop --project p1     exit=0 | EXECUTING -> STOPPED
  $ bm-controller start --project p1    exit=0 | run ee7a1a34..., now STOPPED
                                               | note: run is terminal; nothing to do
  $ bm-controller plan --project p1     exit=1 | refused: run is STOPPED; upsert_units
                                               | always flips a run to READY ...
  $ bm-controller record-result --dispatch-id <old>   exit=0 | rejected
  RESULT: uncaught traceback rather than a refusal: False | exit=0
```

So through the CLI the "old" dispatch is still the current run's dispatch and
the handler is correct. An SDK caller invoking `engine.begin()` directly
reaches the crash.

### L. `check_timeouts` racing a real result. MEDIUM, self healing.

`check_timeouts` reads the open dispatches (tools/bm_controller.py:754) and
calls `record_result` at 764. A real result landing between the two makes
`record_result` refuse 'already-resulted', which propagates out of
`check_timeouts` and skips the `_settle_after_wave` at 786. Probe
p05_check_timeouts.py, case B, with the race fired from inside the engine's
own `list_dispatches`:

```
  [concurrent writer] a real record-result lands
  check_timeouts RAISED: OwnershipRefused: dispatch '74f6c90f...' is
    RESULT_IN, not DISPATCHED; a result was already recorded for it
  run: EXECUTING unit: RESULT_IN dispatch: RESULT_IN fence: active
  recovery step: {'state': 'DELIVERABLE_READY',
                  'note': 'resumed a RESULT_IN dispatch straight to
                           verification (crash between result and commit)'}
  unit: DONE
```

The RESULT_IN resume branch settles it correctly on the very next `step`, so
this is a residual, not a refutation.

---

## What held, with the evidence

### Surface 1: the derivation is sound

Read straight off the module under attack
(probe p00_baseline.py):

```
_REJECTABLE_STATES     : ['FAILED_RECOVERABLE', 'VERIFYING']
_RESULT_WALK_EDGES     : {'CHECKPOINTED': 'READY', 'EXECUTING': 'VERIFYING',
                          'READY': 'EXECUTING', 'WAITING_HUMAN': 'READY'}
_RESULT_WALKABLE_STATES: ['CHECKPOINTED', 'EXECUTING', 'FAILED_RECOVERABLE',
                          'READY', 'VERIFYING', 'WAITING_HUMAN']
late-result states     : ['NEW', 'ORIENTING', 'PLANNING', 'DELIVERABLE_READY',
                          'COMPLETE', 'PAUSED', 'STOPPING', 'STOPPED',
                          'FAILED_TERMINAL']
```

The set IS the fixed point of its own edge relation, the edge data does match
what `_walk_to_executing` and `_ensure_verifying` actually do today, and the
import-time guard at tools/bm_controller.py:261 to 266 does check every edge
against the store's table.

"Can a walk edge be refused under specific run data" is a NO. `set_run_state`
(tools/bm_store.py:12757 to 12785) has exactly three guards: the row exists,
current equals new (an idempotent no-op, never a refusal), and membership in
`CONTROLLER_STATE_TRANSITIONS`. None of them reads a unit, a dispatch, a
fence, a human step or a contract. The 28-cell matrix below is the empirical
half of that answer: no cell raised.

### Surface 2: the ordering and the 14-state matrix

Probe p01_matrix.py drives one unit parked async, walks the run along LEGAL
edges only to each of the 14 reachable states, then fires a result whose
done_check fails.

```
ROLLBACK exit=1  (dirty write scope, the fault-10 case)
start state         outcome   final state         steps  fence    unit      dispatch
EXECUTING           rejected  FAILED_TERMINAL     1      parked   READY     REJECTED
VERIFYING           rejected  FAILED_TERMINAL     1      parked   READY     REJECTED
CHECKPOINTED        rejected  FAILED_TERMINAL     1      parked   READY     REJECTED
READY               rejected  FAILED_TERMINAL     1      parked   READY     REJECTED
WAITING_HUMAN       rejected  FAILED_TERMINAL     1      parked   READY     REJECTED
FAILED_RECOVERABLE  rejected  FAILED_TERMINAL     1      parked   READY     REJECTED
DELIVERABLE_READY   rejected  DELIVERABLE_READY   2      parked   BLOCKED   REJECTED
PAUSED              rejected  PAUSED              2      parked   BLOCKED   REJECTED
STOPPING            rejected  STOPPING            2      parked   BLOCKED   REJECTED
STOPPED             rejected  STOPPED             2      parked   BLOCKED   REJECTED
COMPLETE            rejected  COMPLETE            2      parked   BLOCKED   REJECTED
FAILED_TERMINAL     rejected  FAILED_TERMINAL     2      parked   BLOCKED   REJECTED
ORIENTING           rejected  ORIENTING           2      parked   BLOCKED   REJECTED
PLANNING            rejected  PLANNING            2      parked   BLOCKED   REJECTED

ROLLBACK exit=0  (clean)
EXECUTING           rejected  READY               0      parked   READY     REJECTED
VERIFYING           rejected  READY               0      parked   READY     REJECTED
CHECKPOINTED        rejected  READY               0      parked   READY     REJECTED
READY               rejected  READY               0      parked   READY     REJECTED
WAITING_HUMAN       rejected  READY               0      parked   READY     REJECTED
FAILED_RECOVERABLE  rejected  FAILED_RECOVERABLE  0      parked   READY     REJECTED
DELIVERABLE_READY   rejected  DELIVERABLE_READY   1      parked   BLOCKED   REJECTED
PAUSED              rejected  PAUSED              1      parked   BLOCKED   REJECTED
STOPPING            rejected  STOPPING            1      parked   BLOCKED   REJECTED
STOPPED             rejected  STOPPED             1      parked   BLOCKED   REJECTED
COMPLETE            rejected  COMPLETE            1      parked   BLOCKED   REJECTED
FAILED_TERMINAL     rejected  FAILED_TERMINAL     1      parked   BLOCKED   REJECTED
ORIENTING           rejected  ORIENTING           1      parked   BLOCKED   REJECTED
PLANNING            rejected  PLANNING            1      parked   BLOCKED   REJECTED
```

Nothing raised anywhere. Every fence is parked. Every dispatch is closed.
Every unwalkable state leaves the run exactly where it was. The four rows
REFUTATION-2 reproduced (DELIVERABLE_READY, PAUSED, STOPPING, STOPPED) are
repaired, and the fix generalises to five more states that report never
reached.

A late result whose unit was already SKIPPED works (finding E's probe, the
unit ends BLOCKED). A double result refuses cleanly at `record_result` and
changes nothing (p06 case C). A unit with an empty write_scope skips the
rollback and still gets its step, its fence park and its interruption
(p06 case E).

### Surface 3: `check_timeouts`

The same 28-cell matrix through `check_timeouts` instead of
`receive_result` (probe p05_check_timeouts.py) produced the identical
outcomes: `abandoned=['u1']` in all 28, no raise, fence parked, dispatch
REJECTED, dirty rollback reaching FAILED_TERMINAL from every walkable state
and no move at all from every unwalkable one.

Repeated timeouts do not double count:

```
  call 1 abandoned=['u1'] run=READY unit=READY dispatches=[(1, 'REJECTED')]
    (a step in between dispatched: ['u1'], run=EXECUTING)
  call 2 abandoned=['u1'] run=READY unit=READY dispatches=[(1,'REJECTED'),(2,'REJECTED')]
  call 3 abandoned=[]     run=READY unit=READY dispatches=[(1,'REJECTED'),(2,'REJECTED')]
```

A two-unit wave whose FIRST rollback fails handles the second unit through
the late-result branch, because the run is FAILED_TERMINAL by then:

```
  abandoned: ['u1', 'u2'] run: FAILED_TERMINAL
  units: {'u1': 'BLOCKED', 'u2': 'BLOCKED'}
  steps: ['the rollback command for unit u1 failed (exit 1); its write_scope may ',
          'unit u2 returned a result after the run reached FAILED_TERMINAL. The r']
  u1 fence: parked dispatch: REJECTED
  u2 fence: parked dispatch: REJECTED
```

The `_settle_after_wave` added at tools/bm_controller.py:786 converges
correctly from every walkable state (clean rows end READY, or
FAILED_RECOVERABLE when that is where the run stood) and returns early from
every state that already claimed the run. probe_f1c's permanent wedge is
gone.

### Surface 5: STOPPING is not reachable

Residual 3's STOPPING half cannot be reached by any shipped command
sequence, because `_begin_stopping` (tools/bm_controller.py:1607) runs
STOPPING to STOPPED inside a single call and nothing in it can refuse:
`record_checkpoint` (tools/bm_store.py:12422) and `queue_human_step` need
only SOME contract in any state, and a run cannot exist without one.

Probe p07_stopping_and_blocked.py, cases 1:

```
  states observed after each shipped command: [('step','EXECUTING'),
                                               ('stop','STOPPED'),
                                               ('step','STOPPED')]
  STOPPING ever observed: False

  contract-revoked route (bm-autonomy revoke, then bm-controller step):
    after revoke + step: run=STOPPED note=draining: contract is revoked
    STOPPING persisted: False
```

The PAUSED half of residual 3 IS reachable, and the fix report's assessment
of it ("for a PAUSED run arguably correct, a pause is reversible") is wrong,
because finding A means the re-queued unit is immediately re-dispatched.
Probe p07 case 2, with the crash simulated exactly the way design fault 1
simulates it (`Store.record_result` committed, then the process discarded):

```
  run after pause + step: PAUSED
  crash simulated: unit=RESULT_IN dispatch=RESULT_IN run=PAUSED
  resume-branch step: state=PAUSED note=resumed a RESULT_IN dispatch straight
                      to verification (crash between result and commit)
  run=PAUSED unit=READY
  NEXT step dispatched=['u1'] while the run is PAUSED
  dispatch rows: [(1, 'REJECTED'), (2, 'DISPATCHED')]
```

---

## Observations, not findings

Reproduced, outside the round-3 change, recorded so they are not confused
with it.

1. **A project can never start a second controller run through the CLI.**
   `cmd_start` calls `begin()` only when `get_run` returns None, and
   `get_run` returns the newest run whatever its state. Once a run is
   COMPLETE or STOPPED, `bm-controller start` prints "run is terminal;
   nothing to do" forever and `bm-controller plan` refuses. Verified through
   the real CLI in p12_cli_crash_and_complete.py, both for a COMPLETE run
   and for a STOPPED one.
2. **`bm-controller complete` never releases the controller fence.** Only
   `_begin_stopping` releases `controller-<project>`. An SDK caller invoking
   `engine.begin()` after a COMPLETE run gets
   `OwnershipRefused: 'controller-p1' is already active as lifecycle ...`
   (probe p11_cross_run_full.py). Masked in practice by observation 1.
3. **The staleness rejection never rolls back.** `_verify_and_finish`'s
   stale-revision branch (tools/bm_controller.py:1171 to 1184) records the
   verification, fails the unit and parks the fence, but never runs the
   rollback command and never warns about a dirty scope, unlike every other
   rejection path. Unchanged by round 3.
4. **`_warn_dirty_write_scope` writes into the hard-coded lane "default"**
   (tools/bm_controller.py:1273), not the unit's own lane, so a dirty
   rollback for a unit in lane "build" gates lane "default" project wide via
   `select_ready_units`'s blocked-lane query (tools/bm_store.py:13082).
5. **`_handle_no_ready_units` reads human steps project wide**, not run
   wide (tools/bm_controller.py:1435), so an unresolved step left by any
   earlier run or by `bm-autonomy queue-human-step` gates the same lane in a
   new run. Recoverable by resolving the step; recorded for completeness.

---

## Attempts log

| # | Attack | Probe | Result |
|---|---|---|---|
| 1 | Read the derived sets off the module; is the set closed under its own edges | p00_baseline.py | HELD |
| 2 | Is any walk edge refusable by run data | code read of Store.set_run_state (tools/bm_store.py:12757) plus attempts 3 and 4 | HELD, no data-dependent guard exists |
| 3 | receive_result from all 14 reachable run states, dirty rollback | p01_matrix.py | HELD, 14 of 14 |
| 4 | receive_result from all 14, clean rollback | p01_matrix.py | HELD, 14 of 14 |
| 5 | Does the FAILED_RECOVERABLE member ever reach VERIFYING | p16_verifying_invariant.py | BREAK, finding I |
| 6 | Does a PAUSED run with a live contract dispatch new work | p02, p03 | BREAK, finding A |
| 7 | The same through the real shipped CLI as subprocesses | p08_cli_paused_dispatch.py | BREAK confirmed, finding A |
| 8 | STOPPING wedge via a run with no contract | p04_stopping_wedge.py | HELD, open_run refuses without a live contract |
| 9 | Is STOPPING observable between two shipped commands | p07 case 1 | HELD, never; residual 3's STOPPING half is unreachable |
| 10 | Residual 3's PAUSED half, crash plus pause plus resume | p07 case 2 | BREAK, worse than disclosed |
| 11 | check_timeouts matrix, 14 states x dirty and clean | p05_check_timeouts.py | HELD, 28 of 28 |
| 12 | check_timeouts called repeatedly on the same unit | p05 case A | HELD |
| 13 | check_timeouts racing a real record-result | p05 case B | RESIDUAL, self healing, finding L |
| 14 | Two units timing out, the first rollback dirty | p05 case C | HELD |
| 15 | Late result on a unit a re-plan marked SKIPPED, on a delivered run | p06 case A | HELD on the rejection; BREAK on the reported state, finding E |
| 16 | Late result on a unit at its retry ceiling with a stopped contract | p06 case B | BREAK, finding D |
| 17 | Late result whose unit was already DONE (double result) | p06 case C | HELD |
| 18 | The run moving between the state read and the handler body, both directions | p06 case D | BREAK, finding G |
| 19 | Late result with an empty write_scope | p06 case E | HELD |
| 20 | Is a BLOCKED unit recoverable through any shipped command | p07 case 3 plus grep for unblock_lane_units | BREAK, finding F |
| 21 | Does an EXECUTING run with only BLOCKED units ever move | p07 case 4 | BREAK, finding E's second half |
| 22 | `_deliver_or_hold`'s legal-edge guard from every state | p09 part b | BREAK, finding B |
| 23 | A PAUSED run delivering itself, shipped commands only | p09 part a | BREAK, finding B |
| 24 | run_to_completion on an ordinary async park | p09 part c | BREAK, finding J |
| 25 | A dispatch id from an earlier run | p10_cross_run_dispatch.py | BREAK, finding K |
| 26 | The same through the real CLI | p12_cli_crash_and_complete.py | HELD at CLI level; start never opens a second run |
| 27 | Complete, then start a second run | p12 part 1, p11 | Observations 1 and 2 |
| 28 | Spend accounting on the late-result branch | p13_spend_on_late_result.py | BREAK, finding C |
| 29 | Before and after attribution for the spend hole | p14_before_after_spend.py | BREAK confirmed as a REGRESSION |
| 30 | Spend loss via `bm-controller stop` with a live contract | inline probe, quoted in finding C | BREAK, 4 shipped commands |
| 31 | Is BLOCKED a dead dependency for the F4 escalation | p15_blocked_is_not_dead.py | BREAK, finding F |
| 32 | Does the F4 no-progress stop fire on that shape | p15 part 2 | HELD, 1 step of 10 |
| 33 | `_reject` order under a dirty rollback in every state | p01 and p05 matrices, 56 cells | HELD |
| 34 | Can the interruption skip lose the founder warning | code read of queue_human_step plus p04 | HELD, a contract always exists once a run does |

Discovery ran until a round produced nothing new. Round 1 found attempts 1
to 10, round 2 found 11 to 19, round 3 found 20 to 24, round 4 found 25 to
30, round 5 found 31 and 32, round 6 found attempt 5. Round 7 (the fence
transition guards, `_release_fence` on a null fence uuid, cross-run
`check_timeouts`, `_settle_after_wave` from every walkable state a second
way, the import guard's own drift behaviour) produced nothing that met the
evidence bar, so I stopped.

Probes live in the session scratchpad, which is EPHEMERAL:
/private/tmp/claude-1598639508/-Users-khalil-maaouni-Documents-Development-Work-Frameworks-BrothermeUp/e2edd454-7254-4d3a-ad14-5c05858ffb3a/scratchpad/probes/
Every sequence is reproduced in full above, so each finding can be rebuilt
from this file alone.

---

## What I did not check

- **The full suite.** tools/test_all.py was never run (suite lock), and
  neither were tools/test_bm_controller.py or tools/test_bm_store.py in
  full. I did not run even the round-3 test classes; every result above
  comes from my own probes against the working tree, so I am NOT reporting
  on whether the fix's own 23 tests pass. The fix report says they do; I did
  not verify that claim.
- **F2 and F3.** The containment change in `bs.path_within_allowed` and the
  gate_check straddle logic were read, not attacked. Out of this lens.
- **Genuine multi-process concurrency.** Findings G and L used a delegating
  store wrapper inside one process, the same simulation REFUTATION-2 used.
  Two real concurrent `bm-controller` processes against one SQLite file were
  not tested, so the SQLite locking behaviour under those races is unknown.
- **tools/bm_store.py beyond the controller's own surface.** I read
  `set_run_state`, `record_result`, `record_verification`, `mark_unit_done`,
  `mark_unit_failed`, `block_lane_units`, `unblock_lane_units`,
  `select_ready_units`, `upsert_units`, `queue_human_step`,
  `record_interruption`, `record_checkpoint`, `set_contract_state`,
  `require_root`, `transition` and the two state tables. The rest of its
  15256 lines was not reviewed.
- **`_begin_stopping` under a mid-call crash.** I proved STOPPING is never
  observable between two shipped commands; I did NOT test a process killed
  inside `_begin_stopping`, which is the one remaining way to persist it and
  would re-open residual 3's STOPPING half.
- **The unit-status machine.** `CONTROLLER_UNIT_STATES` includes VERIFYING,
  which nothing in the controller ever sets; I noticed it and did not chase
  what else assumes it.
- **Severity of finding E's harm.** I proved the reported state differs from
  the persisted one and that `run_to_completion` stops on the reported one.
  I did NOT trace every consumer of `bm-controller step --json` to say what
  a wrong state costs downstream.
- **`bm-controller status`'s own rendering.** Read in the real-CLI probes,
  never audited as a code path.
