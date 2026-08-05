# REFUTATION 3, liveness lens: the round-3 fixes on parking, founder
# waiting, dead dependencies and regressions

Target: the working tree of /Users/khalil.maaouni/Documents/BrotherModeUp
after FIX-round3-report.md landed. Read only except this file; no file in
the tree was edited and no git state was changed. Every probe ran against
its own throwaway Store under a fresh tempfile.TemporaryDirectory in /tmp,
loading tools/bm_controller.py by path and reusing ITS bm_store load
(bc.bs), which is the production shape. No .brothermode directory in any
real project was touched. tools/test_all.py was never run.

Guard on the one file the test suite rewrites: the four checkpoint_ref
values in docs/program/absolute-lead/evidence/L03/E4-endtoend.json are
byte-identical before and after everything below (fcc6da3f..., c4336e3d...,
a8ecaeb3..., 5da93fd4...), so nothing here regenerated it.

My lens: liveness, F4, and regressions in the round-3 fixes. F1, F2 and F3
were attacked only where they touch those.

Baseline first, so every break below is found on a tree the implementer
considers fixed:

```
$ cd /Users/khalil.maaouni/Documents/BrotherModeUp/tools
$ python3 -m unittest -v test_bm_controller.TestF1AsyncRejectWhoseRollbackAlsoFails \
    test_bm_controller.TestF2EveryWriteScopePathIsGateChecked \
    test_bm_controller.TestF3AsyncSpendAfterARevoke \
    test_bm_controller.TestF4DependentOfAFailedUnitDoesNotStallTheRun
Ran 7 tests in 0.123s

OK
```

## Verdict lines

| # | Claim under attack | Verdict | Severity | Reproduction |
|---|---|---|---|---|
| 1 | `_deliver_or_hold`'s new legal-edge guard makes a stuck run safe ("the next step tries again") | REFUTED | HIGH | p9: a gate-refused unit leaves the run in EXECUTING forever, done-definition passing, delivery refused on every future step |
| 2 | SKIPPED as a dead dependency removes the F4 stall | REFUTED | HIGH | p5, p6, p12, p15: the escalation replaces a recoverable spin with a BLOCKED remainder no production code can reverse; pre-round-3 control delivers, current tree cannot |
| 3 | The founder-waiting branch moves the run to WAITING_HUMAN | REFUTED | HIGH | p11: the summary says WAITING_HUMAN while the store stays EXECUTING, and both shipped loop drivers stop on the summary |
| 4 | A dropped (SKIPPED) unit is dead to the controller | REFUTED | HIGH (pre-existing, contradicts round 3) | p4 case B: `record-result` on the dropped unit's still-open dispatch marks it DONE |
| 5 | The new park stop means "parked until a founder acts" | REFUTED | MEDIUM | p2 (concurrent fence holder), p3 (the round-3 DEFERRED-CONTENTION verdict): zero founder steps, and the next step proceeds after a non-founder event |
| 6 | run_to_completion no longer burns max_steps with nothing to do | REFUTED | MEDIUM | p1 (soft spend stop, residual 4 reproduced), p8 case C (failing done-definition, founder's whole suite re-run once per wasted step), p8 case D (outage) |
| 7 | The escalation runs whenever nothing is in flight | REFUTED | LOW | p13: `_IN_FLIGHT_UNIT_STATUSES` and `_anything_in_flight` disagree about CLAIMED, so a crash-stranded unit is parked and never named |
| A | `_is_founder_waiting`: in-flight work is never founder-waiting | STANDS (2 attacks) | n/a | p4 case A, plus the mixed-lane variants below |
| B | check_timeouts walks and settles correctly | STANDS (1 hard attack) | n/a | p14 case C: two timeouts in one call, both rollbacks failing, both founder warnings written, both fences parked |
| C | `path_within_allowed` narrows only what F2 meant to narrow | STANDS (18 spellings) | n/a | p10: the only two narrowings are the intended ones |
| D | FIX residual 5, the dual-load OwnershipRefused split | CONFIRMED test-only | LOW | p7: production reaches the deferral, a foreign store defeats it |
| E | Regressions in the 4 F-classes and 8 pre-existing fault classes | NONE FOUND | n/a | 12 single-class unittest runs, all OK |

Headline judgement: the round-3 park stop is correct only for the two notes
it names, and the CLI never reaches it at all. The two F4 changes it ships
alongside (SKIPPED as a dead dependency, selectability as the
founder-waiting test) each make a run WORSE off than the stall they
replaced: one converts a recoverable spin into a run that can never
deliver, the other reports a state it did not write.

---

## Finding 1 (HIGH): the legal-edge guard turns a permanent exception into a permanent silent stall

**Code path.** tools/bm_controller.py:1585, inside `_deliver_or_hold`:

```python
if "READY" not in bs.CONTROLLER_STATE_TRANSITIONS.get(cur, ()):
    summary["note"] = ("the done-definition passes but the run "
                       "is %s, from which delivery is not a "
                       "legal move; staying in place" % cur)
    return
```

The comment above it says "the caller's note says why nothing happened and
the next step tries again". Nothing in the engine can move a run out of
EXECUTING once there is no unit left to dispatch: `_walk_to_executing` is
only called when `select_ready_units` returned something (step(), line
486), and `_settle_after_wave` is only called when a result was recorded.
So the next step tries again and fails again, forever.

**Sequence, all shipped commands, no concurrency.**

1. `bm-autonomy sign` with `--allowed-path src`.
2. `bm-controller plan` one unit u1 whose write_scope is `docs/x.md`, a
   path the contract does not allow.
3. `bm-controller start`. Wave 1 walks the run to EXECUTING (486), then
   `_gate_check_write_scope` returns REFUSED-SCOPE and
   `_claim_and_dispatch` routes it to `mark_unit_failed`
   (tools/bm_controller.py:1050). Nothing is dispatched, nothing is
   recorded, and the run is LEFT in EXECUTING.
4. A second wave exhausts the breaker; u1 is FAILED, so no unit is
   non-terminal and `_deliver_or_hold` runs. The done-definition passes.
   READY is not legal from EXECUTING, so the guard returns.

**Probe output** (scratchpad/p9_executing_wedge.py):

```
contract allowed_paths: ['src']
step 1: dispatched=[] state=EXECUTING note=no selectable unit could be claimed this wave (fence overlap, or gate_
  statuses: {'u1': 'READY'}
  store run state: EXECUTING
  legal moves from EXECUTING: ('VERIFYING', 'STOPPING', 'PAUSED', 'FAILED_RECOVERABLE')

run_to_completion: 1 step(s) of max_steps=20
  final state=EXECUTING
  final note: no selectable unit could be claimed this wave (...); nothing is in flight either, so the run is parked until a founder acts
  store run state: EXECUTING

== is it recoverable by any engine action? ==
  _drive_until_parked (the shipped `start`/`step` path): 1 step(s), state now EXECUTING
  a FRESH engine (crash resume): state=EXECUTING note=the done-definition passes but the run is EXECUTING, from which delive
  statuses: {'u1': 'FAILED'}
  open founder steps: 0
  DELIVERABLE FOREVER OUT OF REACH: True

== and the wedge note is not a no-progress constant ==
  run_to_completion: 20 step(s) of max_steps=20
  done_definition executed 21 time(s) in that one call
  final note: the done-definition passes but the run is EXECUTING, from which delivery is not a legal move; staying in place

== the only escape ==
  after stop: STOPPED
```

Three consequences, all in that output: the deliverable is ready and can
never be delivered; there is no founder step, so nothing tells the founder
what to do; and because the wedge note is not one of the two module
constants, run_to_completion burns every remaining step and re-runs the
founder's whole done-definition once per wasted step (21 executions in one
call here; with the production SubprocessCheckRunner and the default
max_steps=500 that is 500 real test-suite runs).

**Attribution, stated plainly.** The collision is not new: before this
round the same line called `set_run_state(run_id, "READY", ...)`
unconditionally and RAISED, which is REFUTATION-2's probe_f1c. The git diff
of this hunk shows exactly that removed shape. What round 3 changed is the
failure mode, from a loud permanent exception to a silent permanent stall,
and the comment it added asserts a recovery ("the next step tries again")
that the probe disproves. The only escapes the probe found are
`bm-controller stop` (reaches STOPPED) or pausing the contract.

---

## Finding 2 (HIGH): SKIPPED as a dead dependency converts a recoverable stall into a run that can never deliver

**Code path.** tools/bm_controller.py:300 (`_DEAD_DEPENDENCY_STATUSES =
("FAILED", "SKIPPED")`), consumed at 1515, with `block_lane_units` at
1552-1553. The docstring at 1488 says "BLOCKED is reversible
(unblock_lane_units) the moment a founder re-plans or repairs the failed
dependency". Two facts kill that sentence:

- `unblock_lane_units` has NO production caller. `grep -rn
  unblock_lane_units --include=*.py tools/` returns the definition
  (tools/bm_store.py:13314), two docstring mentions in bm_controller.py
  (lines 680 and 1488), and tests. It is not one of bm_controller.py's
  eight subcommands and bm_autonomy.py never calls it.
- `Store.upsert_units` skips a unit whose definition hash is unchanged
  (tools/bm_store.py:12949, "byte-identical redefinition: reuse,
  untouched"), so the re-plan the escalation TELLS the founder to make
  does not clear the BLOCKED status, and does not even revive the dropped
  dependency.

**Sequence, all shipped commands.** `bm-controller plan` u1 and u2 (u2
depends on u1); `bm-controller plan` again with u2 only, which marks u1
SKIPPED (tools/bm_store.py:13006); `bm-controller start`; then follow the
escalation's own instruction (re-plan, resolve the step).

**Probe output** (scratchpad/p5_skipped_replan.py, byte-identical re-plan):

```
  after dropping u1: statuses={'u1': 'SKIPPED', 'u2': 'PENDING'} run=READY open_steps=0
  escalation run: 1 step(s), final=WAITING_HUMAN note=only founder-gated lanes remain
  after escalation: statuses={'u1': 'SKIPPED', 'u2': 'BLOCKED'} run=WAITING_HUMAN open_steps=1
  founder step says: unit u2 can never run: it depends on unit u1, which is SKIPPED (a re-plan dropped it from the unit graph). Re-plan or repair unit u1 and resolve this step, or stop the run; the controller will not start u2 on its own.
  after the repairing re-plan: statuses={'u1': 'SKIPPED', 'u2': 'BLOCKED'} run=READY open_steps=1
  run after re-plan: 1 step(s), final=WAITING_HUMAN note=only founder-gated lanes remain
  run after resolving the step: 1 step(s), final=WAITING_HUMAN note=only founder-gated lanes remain
  final: statuses={'u1': 'SKIPPED', 'u2': 'BLOCKED'} run=WAITING_HUMAN open_steps=0
  RUN DELIVERED: False
```

The last two lines are the whole finding: the run rests in WAITING_HUMAN,
reporting "only founder-gated lanes remain", with ZERO open founder steps
and nothing a founder can resolve. `_is_founder_waiting`
(tools/bm_controller.py:1462) returns True for a BLOCKED unit
unconditionally, so a BLOCKED remainder reports founder-gating forever even
after every human step is resolved.

With a CHANGED definition for u1 the same probe revives u1 and runs it to
DONE, and u2 is still BLOCKED and still never runs:

```
  final: statuses={'u1': 'DONE', 'u2': 'BLOCKED'} run=WAITING_HUMAN open_steps=0
  RUN DELIVERED: False
```

**Control, showing the round-3 line is the cause and not the pre-existing
shape.** scratchpad/p6_control_preround3.py runs the identical founder
sequence twice, the first time with `bc._DEAD_DEPENDENCY_STATUSES` set back
to `("FAILED",)` in memory, which is what tools/bm_controller.py tested
before this round:

```
== PRE-ROUND-3 control: SKIPPED is not a dead dependency ==
  stall run: 1 step(s) final=READY note=no unit is currently selectable (...); nothing is in flight either, so the run is parked until a founder acts
  after the stall: statuses={'u1': 'SKIPPED', 'u2': 'PENDING'} run=READY open_steps=0
  after the repairing re-plan: statuses={'u1': 'READY', 'u2': 'PENDING'} run=READY open_steps=0
  recovery run: 2 step(s) final=DELIVERABLE_READY
  final: statuses={'u1': 'DONE', 'u2': 'DONE'} run=DELIVERABLE_READY open_steps=0
  RUN DELIVERED: True

== CURRENT tree: SKIPPED is a dead dependency ==
  ...
  final: statuses={'u1': 'DONE', 'u2': 'BLOCKED'} run=WAITING_HUMAN open_steps=0
  RUN DELIVERED: False
```

Before the fix the founder's repair delivered the run. After the fix the
same repair cannot. The same probe also shows the dead end pre-exists for
FAILED dependencies (round 2's own escalation), so the one-way door is not
new; what round 3 did was point it at a completely ordinary founder action,
re-planning without a unit.

**Blast radius.** `block_lane_units` flips EVERY PENDING/READY unit of the
lane, so units that had nothing to do with the dropped dependency are lost
too. scratchpad/p12_collateral_block.py, where u3 is healthy and merely
waiting on a founder-gated lane elsewhere:

```
after the drop: {'u0': 'SKIPPED', 'u2': 'PENDING', 'u3': 'PENDING', 'g1': 'READY'}
escalation run: 1 step(s) final=WAITING_HUMAN note=only founder-gated lanes remain
statuses: {'u0': 'SKIPPED', 'u2': 'BLOCKED', 'u3': 'BLOCKED', 'g1': 'READY'}
u3 was HEALTHY and is now: BLOCKED
after resolving every step and restoring u0: {'u0': 'READY', 'u2': 'BLOCKED', 'u3': 'BLOCKED', 'g1': 'READY'}
recovery run: 1 step(s) final=WAITING_HUMAN
final statuses: {'u0': 'DONE', 'u2': 'BLOCKED', 'u3': 'BLOCKED', 'g1': 'DONE'}
RUN DELIVERED: False
```

**The one escape the probes found** (scratchpad/p15_escape.py): a re-plan
that changes the BLOCKED unit's OWN definition, which is not what the
founder step asks for.

```
deadlock: {'u1': 'SKIPPED', 'u2': 'BLOCKED'} run=WAITING_HUMAN
after resolving every step: {'u1': 'SKIPPED', 'u2': 'BLOCKED'}
after a re-plan that CHANGES the blocked unit too: {'u1': 'READY', 'u2': 'PENDING'}
recovery run: 2 step(s) final=DELIVERABLE_READY
RUN DELIVERED: True
```

---

## Finding 3 (HIGH): the run reports WAITING_HUMAN without being moved there

**Code path.** tools/bm_controller.py:1439-1445:

```python
cur = self.store.get_run(project_id, raw=True)["state"]
if cur in ("READY", "CHECKPOINTED"):
    self.store.set_run_state(run_id, "WAITING_HUMAN", ...)
summary["state"] = "WAITING_HUMAN"
summary["note"] = "only founder-gated lanes remain"
```

The store write is guarded, the summary is not. Both shipped loop drivers
stop on the SUMMARY: run_to_completion at 562 and `_drive_until_parked` at
tools/bm_controller.py:1937, and `_report_trace` (1889) prints
`last["state"]` to the founder. The guard itself is pre-existing (the git
diff shows those three lines unchanged); what round 3 changed is the
CONDITION that reaches it, from "every non-terminal unit is BLOCKED" to
`all(self._is_founder_waiting(...))`, which is now satisfied by ordinary
READY units in a gated lane, in states the old condition never reached.

**Sequence, all shipped commands, no concurrency.** `bm-autonomy sign
--allowed-path src`; `bm-controller plan` u1 (write_scope docs/x.md, lane
lane-a) and u2 (write_scope src/b.py, lane lane-b); `bm-autonomy
queue-human-step --lane lane-b`; `bm-controller start`.

**Probe output** (scratchpad/p11_state_lie.py):

```
open founder steps: 1
step 1: summary state=EXECUTING      store state=EXECUTING    note=no selectable unit could be claimed this wav
        statuses: {'u1': 'READY', 'u2': 'READY'}
step 2: summary state=EXECUTING      store state=EXECUTING    note=no selectable unit could be claimed this wav
        statuses: {'u1': 'FAILED', 'u2': 'READY'}
step 3: summary state=WAITING_HUMAN  store state=EXECUTING    note=only founder-gated lanes remain
        statuses: {'u1': 'FAILED', 'u2': 'READY'}

SUMMARY SAYS WAITING_HUMAN WHILE THE STORE SAYS EXECUTING: True

== what the two shipped loop drivers do with that ==
  _drive_until_parked: 1 step(s), last summary state=WAITING_HUMAN, store state=EXECUTING
  run_to_completion: 1 step(s), last summary state=WAITING_HUMAN, store state=EXECUTING
```

So `bm-controller start` reports "now WAITING_HUMAN" through
`_report_trace` while `bm-controller status`, which reads the run row,
reports EXECUTING, for the same run at the same moment. (The `start` and
`status` half of that sentence is read from the two command bodies; the
summary-versus-store disagreement itself is probed above. The check that
would close the gap is a subprocess test running `start` then `status`
against one temp root, which I did not run because no CLI test was in my
mandate and the CLI classes were out of scope.) The run does recover once
the founder resolves the step (the next wave dispatches from EXECUTING), so
the harm is a false report, not a wedge.

---

## Finding 4 (HIGH reachability, moderate harm): a re-plan-dropped unit is resurrected by its own late result

**Code path.** `receive_result` (tools/bm_controller.py:589) branches on
the RUN state only (614). A unit dropped by a re-plan is SKIPPED
(tools/bm_store.py:13006) while its dispatch stays open, and SKIPPED is one
of the two statuses `_DEAD_DEPENDENCY_STATUSES` (300) calls permanently
dead. Nothing on the result path consults the unit status, so from any
walkable run state the result is accepted and the dead unit is marked DONE.

**Sequence, all shipped commands.** `plan` u1 and u2; `start` (u1 parks
async under RecordIntentWorker); `plan` again without u1; `record-result`
for u1's still-open dispatch.

**Probe output** (scratchpad/p4_founder_waiting.py, case B):

```
  wave 1 dispatched=['u1', 'u2'] completed=['u2'] state=CHECKPOINTED
  after re-plan statuses: {'u1': 'SKIPPED', 'u2': 'DONE', 'u3': 'READY'}
  open dispatches: [('u1', 'SKIPPED', 'DISPATCHED')]
  steps taken: 1
  final state=WAITING_HUMAN note=only founder-gated lanes remain
  open dispatches STILL: [('u1', 'SKIPPED', 'DISPATCHED')]
  WAITING_HUMAN WITH AN OPEN DISPATCH: True
  receive_result returned: u1
  run state after the late result: WAITING_HUMAN
  statuses: {'u1': 'DONE', 'u2': 'DONE', 'u3': 'BLOCKED'}
```

Two things in one output. First, the run reaches WAITING_HUMAN with a
dispatch still open, which is the exact statement `_is_founder_waiting`'s
docstring says it will never make ("calling the run founder-gated while a
worker is mid-unit would be a false statement about the run"); it is
reachable because a SKIPPED unit is filtered out of `non_terminal` at 1431
while its dispatch stays open. Second, the late result for the dropped unit
is ACCEPTED: u1 goes SKIPPED to DONE, its fence is released as complete and
its spend is recorded, silently reversing the founder's re-plan.

**Attribution.** Pre-existing: the old `_walk_to_executing` also detoured
WAITING_HUMAN to READY. I am not claiming round 3 introduced it. I am
claiming round 3 made the engine assert the opposite in two new places
(`_DEAD_DEPENDENCY_STATUSES` calls SKIPPED dead, `_handle_late_result`
protects DELIVERABLE_READY from exactly this), so the same drop is
permanent or reversible depending only on which run state the result
happens to arrive in.

Related, from the same family (scratchpad/p14_round4.py case B):
`check_timeouts` only inspects units whose STATUS is DISPATCHED
(tools/bm_controller.py:752), so a dropped unit's open dispatch is never
timed out either. It stays open indefinitely.

---

## Finding 5 (MEDIUM): FALSE PARK, twice

**Code path.** tools/bm_controller.py:564-571. The stop fires on
`_NOTHING_CLAIMABLE_NOTE`, which `_claim_and_dispatch` writes for a fence
overlap (1069) and for the round-3 `_DEFERRED_CONTENTION` verdict (1020).
Both are explicitly TRANSIENT by their own docstrings ("deferred to a later
wave", "tried again next wave"), and the loop rewrites the note to say the
run "is parked until a founder acts".

**Reproduction A, a concurrent fence holder** (scratchpad/p2_false_park_fence.py):

```
concurrent holder fence: other-agent state=active files=['a.py']
steps taken: 2 of max_steps=20
final state: EXECUTING
final note: no selectable unit could be claimed this wave (...); nothing is in flight either, so the run is parked until a founder acts
statuses: {'u1': 'READY'}
open founder steps: 0
worker was called: {}

== fence released by the concurrent holder, no founder ==
next step dispatched=['u1'] completed=['u1'] state=DELIVERABLE_READY
statuses: {'u1': 'DONE'}
```

Zero founder steps exist, and the event that unblocks the run is another
agent releasing its fence, not a founder.

**Reproduction B, the round-3 F2 deferral** (scratchpad/p3_false_park_contention.py),
with a supersede amend fired from inside gate_check, the same simulation
REFUTATION-2 used:

```
steps taken: 2 of max_steps=20
final state: EXECUTING
final note: no selectable unit could be claimed this wave (...); nothing is in flight either, so the run is parked until a founder acts
statuses: {'u1': 'READY'}
open founder steps: 0
live contract revision now: 9

== the amending writer stops. NO founder action ==
next step dispatched=['u1'] completed=['u1'] state=DELIVERABLE_READY
```

So the F2 fix's own contention deferral feeds the F4 fix's park stop and
produces a false statement about the run. MEDIUM: both need a concurrent
writer.

---

## Finding 6 (MEDIUM): MISSED PARK, three notes the stop does not cover

**Code path.** `_NO_PROGRESS_NOTES` (tools/bm_controller.py:278) holds
exactly two notes. `step()` can return a zero-progress summary with at
least three others.

**6a, the soft spend stop** (FIX-round3-report residual 4, reproduced;
scratchpad/p1_softstop_spin.py). Note written at
tools/bm_controller.py:481:

```
wave 1 dispatched=['u1'] completed=['u1'] state=READY
spend verdict now: soft-stop
statuses: {'u1': 'DONE', 'u2': 'PENDING'}
open dispatches in flight: False

== run_to_completion with max_steps=12 ==
steps taken: 12
last note: soft-stop: 1 unit(s) selectable but no new dispatch; finishing in-flight work only
every step identical: True
SPUN THROUGH EVERY STEP: True

== shipped-CLI control: _drive_until_parked, same state ==
steps taken: 1
```

**Severity from shipped commands, which the brief asked me to judge:**
LOW to MEDIUM, not HIGH. `bm-controller start` and `bm-controller step` do
NOT call run_to_completion; they call `_drive_until_parked`
(tools/bm_controller.py:1911), which breaks on any wave that neither
dispatched nor completed. The control run above stops in one step. The spin
is reachable only from an SDK caller or a scheduler using
`ControllerEngine.run_to_completion` directly. The same fact has an
uncomfortable corollary for the round-3 work: the entire park stop added to
run_to_completion is unreachable from the shipped CLI, because
`_drive_until_parked` already stops earlier on a broader condition.

**6b, the failing done-definition, which is the expensive one**
(scratchpad/p8_missed_parks.py case C):

```
== C: done-definition fails, every unit DONE ==
  steps taken: 15 of max_steps=15
  final state=CHECKPOINTED
  final note: final done-definition check failed (exit 1); staying in place for inspection
  done_definition executed 15 time(s) in ONE run_to_completion call
  SPUN THROUGH EVERY STEP: True
  shipped-CLI control (_drive_until_parked): 1 step(s)
```

Each wasted step re-runs the founder's WHOLE done-definition through
CheckRunner, which in production is a real subprocess. At the default
max_steps=500 that is 500 test-suite runs for one call.

**6c, an outage that never recovers** (same probe, case D): 15 of 15 steps,
15 worker asks, note "re-awaited an in-flight dispatch (crash resume or
provider-outage recovery)", state FAILED_RECOVERABLE. Recorded as a spin
rather than a defect: retrying an outage is the documented design, and a
dispatch really is open, so the park stop is right to abstain. The cost is
that there is no backoff and no bound other than max_steps.

---

## Finding 7 (LOW): the two round-3 in-flight helpers disagree, and a CLAIMED unit falls between them

**Code path.** `_IN_FLIGHT_UNIT_STATUSES` (tools/bm_controller.py:292)
counts CLAIMED, so `_block_unreachable_units` returns False at 1499 and
never escalates. `_anything_in_flight` (574) deliberately reads DISPATCH
rows instead, and a CLAIMED unit has none, so run_to_completion parks. A
crash between `claim_unit` and `record_dispatch`, one Store call earlier
than fault 1's own window, therefore strands a unit with an ACTIVE fence
and no founder step naming it.

**Probe output** (scratchpad/p13_claimed_crash.py):

```
after the crash window: statuses={'u1': 'CLAIMED'} run=EXECUTING
dispatch rows for u1: 0
fence state: active

fresh engine run_to_completion: 1 step(s)
  final state=EXECUTING
  final note: no unit is currently selectable (...); nothing is in flight either, so the run is parked until a founder acts
  statuses: {'u1': 'CLAIMED'}
  open founder steps: 0
  fence STILL: active
  _anything_in_flight says: False
  CLAIMED counted as in flight by the escalation: True
```

The park itself is honest here (a founder does have to act). The defect is
that nothing escalates, nothing releases the fence, and the two helpers
added in the same round define "in flight" two different ways.

---

## What held

**A. `_is_founder_waiting` versus genuinely in-flight work: STANDS, 2
attacks.** The brief's exact shape, a dependency in a healthy lane still in
flight with the dependent PENDING in a gated lane, does not reach
WAITING_HUMAN (scratchpad/p4_founder_waiting.py case A):

```
  wave 1 dispatched=['u1'] state=EXECUTING
  statuses: {'u1': 'DISPATCHED', 'u2': 'BLOCKED'}
  open dispatches: [('u1', 'DISPATCHED', 'DISPATCHED')]
  step 2 state=EXECUTING note=re-awaited an in-flight dispatch (crash resume or provider-outage recovery)
  WRONGLY WAITING_HUMAN WITH WORK IN FLIGHT: False
```

Every in-flight status (CLAIMED, DISPATCHED, RESULT_IN, VERIFYING) fails
both arms of the test at 1462-1465, so the only way through it is a unit
whose STATUS is terminal while its dispatch is open, which is finding 4.
A second attack, a unit with an empty lane name, is refused by the store:
`upsert_units` writes `u.get("lane") or "default"`
(tools/bm_store.py:12965 and 12995), so lane "" cannot exist and the
`if s["lane"]` filter at 1436 cannot drop a real lane.

**B. check_timeouts under a double failure: STANDS, 1 hard attack.** Two
units time out in one call and both rollbacks fail, so the first rejection
moves the run before the second is judged (scratchpad/p14_round4.py case C):

```
  abandoned=['u1', 'u2']
  run=FAILED_TERMINAL statuses={'u1': 'FAILED', 'u2': 'FAILED'}
  founder steps: 2
    - the rollback command for unit u1 failed (exit 1); its write_scope may be left dirty and needs ma
    - the rollback command for unit u2 failed (exit 1); its write_scope may be left dirty and needs ma
  u1 fence: parked
  u2 fence: parked
```

Both founder warnings survive and both fences are parked, which is exactly
what the round-3 reordering promised. Also probed: run_to_completion on a
draining run terminates in one step at STOPPED (case A).

**C. The store's containment change: STANDS, 18 spellings**
(scratchpad/p10_path_matrix.py). The only two rows where
`path_within_allowed` refuses what `paths_overlap` allowed are the two the
F2 fix meant to close:

```
allowed      candidate          overlap   within    verdict
src          .                  True      False     NARROWED (was allowed, now refused)
src/app      src                True      False     NARROWED (was allowed, now refused)
```

Every realistic spelling a unit graph might carry survives: `./src/a.py`,
`src/./a.py`, `src//a.py`, a trailing-slash allowed path, a case-mismatched
allowed path, a glob allowed path, and a glob candidate all keep their old
verdict. No collateral narrowing found.

**D. FIX residual 5, the dual-load OwnershipRefused split: test-only,
demonstrated.** tools/bm_controller.py has exactly two `except bs.*` sites:
the fence-overlap deferral at 1069 and `except bs.BMStoreError` in main()
at 2409. Production builds the Store from the controller's own load
(`_store()` at 1734, `ControllerEngine` constructed only at 1748), and no
other production module imports bm_controller (grep over the repo finds
only three commands/*.md documents). The deferral branch is reached in the
production shape and defeated only when the store comes from a second
independent load (scratchpad/p7_dual_load.py):

```
== production shape: the store comes from bm_controller's own load ==
  store module is the engine's own load: True
  step returned: dispatched=[] note=no selectable unit could be claimed this wave (fence overlap
  DEFERRAL BRANCH REACHED: True

== test-file shape: the store comes from a SECOND independent load ==
  store module is the engine's own load: False
  step RAISED: OwnershipRefused (module bm_store_second)
  DEFERRAL BRANCH REACHED: False
```

One case this does not cover, and the check that would cover it: an SDK
embedder that loads bm_store itself and passes that Store into
ControllerEngine would hit the same split, in both catch sites. Testing
that needs a caller outside this repository, since nothing inside it
constructs the engine except bm_controller.py:1748; the probe above already
shows the mechanism, so such a test would only widen the caller list, not
change the mechanism.

**E. Regressions in the named test classes: NONE FOUND.** The four round-2
F-classes (7 tests, output at the top of this report) plus eight
pre-existing fault classes, each run as its own single-class unittest
invocation:

```
$ cd /Users/khalil.maaouni/Documents/BrotherModeUp/tools
$ for c in TestFault3DependencyChangedOutputInvalidatesEvidence TestFault4WorkerHangs \
    TestFault6CostCeilingReached TestFault7FounderCancelsDuringFanOut \
    TestFault9ProviderOutageThenRecovery TestFault10RollbackItselfFails \
    TestHumanBlockedLaneDoesNotStallIndependentLane TestRevokedContractMidUnit; do
    python3 -m unittest test_bm_controller.$c; done
--- TestFault3DependencyChangedOutputInvalidatesEvidence   Ran 1 test  OK
--- TestFault4WorkerHangs                                  Ran 1 test  OK
--- TestFault6CostCeilingReached                           Ran 1 test  OK
--- TestFault7FounderCancelsDuringFanOut                   Ran 1 test  OK
--- TestFault9ProviderOutageThenRecovery                   Ran 1 test  OK
--- TestFault10RollbackItselfFails                         Ran 1 test  OK
--- TestHumanBlockedLaneDoesNotStallIndependentLane        Ran 1 test  OK
--- TestRevokedContractMidUnit                             Ran 1 test  OK
```

I picked those eight because they sit on the changed lines: check_timeouts
(fault 4), the reordered `_reject` (fault 10), the drain and late-result
territory (fault 7), spend and the loop (fault 6), the re-plan cascade and
delivery (fault 3), `_resume_dispatched` (fault 9), the founder-waiting
judgement (blocked lane), and the gate_check drain (revoked contract). All
green. Note what that means and does not mean: findings 1, 2 and 3 are
behaviour changes NO test in the file covers, and finding 2 is shown by a
control run, not by a failing test.

**E4 fixture drift:** `git diff` on
docs/program/absolute-lead/evidence/L03/E4-endtoend.json shows four changed
lines, all four `checkpoint_ref` uuid4 values, exactly as
TestEndToEndE4's docstring says. No status, state, count or verdict moved.
The claim in the fix report is accurate.

---

## Attempts log

| # | Attack | Probe or command | Result |
|---|---|---|---|
| 1 | Baseline: the four round-2 F-classes on this tree | unittest, 4 classes | PASS, 7 tests |
| 2 | MISSED PARK: soft spend stop, nothing in flight | p1_softstop_spin.py | BREAK, 12 of 12 steps; CLI control stops in 1 |
| 3 | FALSE PARK: concurrent fence holder | p2_false_park_fence.py | BREAK, "parked until a founder acts" with 0 founder steps |
| 4 | FALSE PARK: round-3 DEFERRED-CONTENTION verdict | p3_false_park_contention.py | BREAK, same false note from the F2 fix's own deferral |
| 5 | FALSE PARK: dependency completing via receive_result | reasoning plus p4 | HELD: an open dispatch always makes `_anything_in_flight` True, and a closed dispatch cannot take a result |
| 6 | `_is_founder_waiting`: in-flight dep, healthy lane, gated dependent | p4_founder_waiting.py case A | HELD |
| 7 | `_is_founder_waiting`: SKIPPED unit with an open dispatch | p4_founder_waiting.py case B | BREAK, WAITING_HUMAN with work in flight, and the dropped unit is resurrected to DONE |
| 8 | `_is_founder_waiting`: empty lane name evades `gated_lanes` | read of tools/bm_store.py:12965, 12995 | HELD, `u.get("lane") or "default"` |
| 9 | SKIPPED escalation versus a byte-identical re-plan | p5_skipped_replan.py | BREAK, run dead in WAITING_HUMAN with 0 open steps |
| 10 | SKIPPED escalation versus a changed re-plan | p5_skipped_replan.py | BREAK, dependent stays BLOCKED forever |
| 11 | Is the round-3 line the cause | p6_control_preround3.py | YES, pre-round-3 delivers, current tree cannot |
| 12 | Is the same dead end pre-existing for FAILED deps | p6_control_preround3.py | YES, round 3 widened the trigger, it did not create the door |
| 13 | Collateral: a healthy unit sharing the blocked lane | p12_collateral_block.py | BREAK, u3 permanently BLOCKED |
| 14 | Any escape from the BLOCKED remainder | p15_escape.py, grep for unblock_lane_units | Only a re-plan that changes the blocked unit's OWN definition |
| 15 | Summary state versus store state on the founder-waiting branch | p11_state_lie.py | BREAK, summary WAITING_HUMAN, store EXECUTING |
| 16 | Permanent EXECUTING wedge through the new delivery guard | p9_executing_wedge.py | BREAK, undeliverable forever, 20 of 20 steps, 21 done-definition runs |
| 17 | MISSED PARK: failing done-definition | p8_missed_parks.py case C | BREAK, 15 of 15 steps, 15 suite runs |
| 18 | MISSED PARK: unrecoverable provider outage | p8_missed_parks.py case D | Spin recorded, not called a defect |
| 19 | Regression matrix for `path_within_allowed` | p10_path_matrix.py | HELD, only the two intended narrowings |
| 20 | Residual 5, dual-load OwnershipRefused | p7_dual_load.py plus grep of catch sites | Test-only, production reaches the branch |
| 21 | Regressions: 4 F-classes plus 8 pre-existing fault classes | 12 single-class unittest runs | All OK |
| 22 | E4 fixture drift | git diff | Four checkpoint uuids only, as documented |
| 23 | CLAIMED crash window versus the escalation guard | p13_claimed_crash.py | BREAK (LOW), stranded unit, active fence, no escalation |
| 24 | Park stop on a draining run | p14_round4.py case A | HELD, STOPPED in 1 step |
| 25 | check_timeouts on a run with a dropped unit | p14_round4.py case B | Observation: a SKIPPED unit's open dispatch is never timed out (status filter at 752) |
| 26 | check_timeouts, two timeouts, both rollbacks failing | p14_round4.py case C | HELD, both warnings, both fences parked |

Discovery stopped by the rule in the brief. Round 1 produced attempts 2 to
8, round 2 produced 9 to 15, round 3 produced 16 to 20 and 23, round 4
(attempts 24 to 26, all fresh ideas: draining runs, timeouts against
founder-gated and re-planned runs, and a double rollback failure inside one
check_timeouts call) produced no new break, so I stopped there.

Probe files live in the session scratchpad
(/private/tmp/claude-1598639508/-Users-khalil-maaouni-Documents-Development-Work-Frameworks-BrothermeUp/e2edd454-7254-4d3a-ad14-5c05858ffb3a/scratchpad),
which is ephemeral. Every sequence is written out above, so each finding
can be rebuilt from this file alone.

## What I did not check, and what would check it

- tools/test_all.py and the full tools/test_bm_controller.py file: not run
  (suite lock, and running the whole controller file rewrites the E4
  evidence artifact). Only 12 single-class invocations plus the 4-class
  baseline ran. Closing this needs the orchestrator's own gate run.
- The CLI as real subprocesses: everything here drove engine calls and
  `_drive_until_parked` in-process. The six TestControllerCLI* classes were
  not run, and `_report_trace`'s printed state (finding 3's founder-visible
  half) was read, not executed. A subprocess test of `start` followed by
  `status` against one temp root would close it.
- Real two-process SQLite contention: simulated inside one process by a
  delegating store wrapper, exactly as REFUTATION-2 simulated it. Closing
  it needs two real `bm-controller` processes against one store file.
- F1, F2 and F3 outside the liveness surface: the rest of REFUTATION-2's
  F1 state matrix was not re-walked, and I relied on the fix report's own
  evidence there.
- tools/bm_store.py beyond the controller's touch points (upsert_units,
  select_ready_units, block/unblock_lane_units, gate_check, path helpers,
  spend, human steps). The other roughly 15000 lines were not reviewed.
- Finding 1's pre-round-3 failure mode (an exception rather than a stall):
  taken from the git diff of that hunk and REFUTATION-2's probe_f1c output.
  Running the pre-fix tree would confirm it directly.
- Whether commands/brotherme-auto.md and its siblings promise anything
  about the run state or re-plan behaviour findings 3 and 4 contradict:
  not read, so the founder-facing impact is judged from engine and CLI code
  only.
- No fix was applied to any file. This report is the only write I made.
