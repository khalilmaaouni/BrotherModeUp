# REFUTATION 2: adversarial pass over the F1 to F4 fixes

Target: the working tree of /Users/khalil.maaouni/Documents/BrotherModeUp
(staged L03 plus the unstaged fixes), tools/bm_controller.py against
tools/bm_store.py schema 15. Read only except this file. No fix was
applied to any file; this report is the only write made.

Baseline first: the four new test classes pass on this tree, so every
break below is found on a tree the implementer considers fixed.

```
$ cd /Users/khalil.maaouni/Documents/BrotherModeUp/tools
$ python3 -m unittest test_bm_controller.TestF1AsyncRejectWhoseRollbackAlsoFails \
    test_bm_controller.TestF2EveryWriteScopePathIsGateChecked \
    test_bm_controller.TestF3AsyncSpendAfterARevoke \
    test_bm_controller.TestF4DependentOfAFailedUnitDoesNotStallTheRun -v
...
Ran 7 tests in 0.113s

OK
```

The full suite was NOT run (suite lock respected). Every probe below ran
against its own throwaway Store under a fresh tempfile.TemporaryDirectory
in /tmp. No .brothermode store in any real project directory was touched.

## Verdict summary

| Finding | Verdict | What survives | Reproduction |
|---|---|---|---|
| F1 async reject whose rollback also fails | REFUTED | HIGH (safety) | 2 sequences on receive_result, 1 more on check_timeouts |
| F2 every write_scope path is gate checked | REFUTED | MEDIUM new hole, plus a HIGH pre-existing hole the fix does not close | contract amend straddling the per-path loop; ancestor path widening |
| F3 spend after a revoke | STANDS | LOW residual, self healing | only a two-call concurrent-writer window, recovered on the next step |
| F4 dependent of a FAILED unit does not stall the run | REFUTED | LOW | a SKIPPED dependency, and a FAILED dependency plus any gated lane |

Verdict: F1 REFUTED. The fix repairs exactly the two states it walks
(CHECKPOINTED and WAITING_HUMAN) and leaves four states in which the
original defect reproduces verbatim. Two of them are reachable with
shipped CLI commands and no contract change.

Verdict: F2 REFUTED. The multi-path loop does what its tests say, but it
records the LAST path's contract revision, which opens a new hole in the
staleness protocol that did not exist when only one path was checked. The
property the fix claims to establish (a unit cannot be authorised outside
allowed_paths) is also still false by a second route the fix does not
touch.

Verdict: F3 STANDS. Attacks including a double result and an injected
concurrent revoke produced only one residual: a revoke landing between
the guard's own latest_contract read and record_spend still raises, and
the next step() resumes the RESULT_IN dispatch and settles it cleanly.
That is a genuine narrowing of the original defect, not a restatement.

Verdict: F4 REFUTED. The escalation recognises only a FAILED dependency
and judges the whole run by unit status alone, so two ordinary
configurations still park the run in CHECKPOINTED forever and still burn
every one of run_to_completion's max_steps, which is the exact symptom
F4 was written to remove.

---

## F1: REFUTED

### What the fix does

tools/bm_controller.py:504-505 calls `_walk_to_executing` then
`_ensure_verifying` before verification. `_walk_to_executing`
(tools/bm_controller.py:1014-1036) detours to READY only from
CHECKPOINTED and WAITING_HUMAN (line 1029) and then moves READY to
EXECUTING. `_ensure_verifying` (1038-1048) fires only from EXECUTING.
Every other run state is a silent no-op, and the rejection path still
attempts FAILED_TERMINAL at tools/bm_controller.py:947-949, which
CONTROLLER_STATE_TRANSITIONS (tools/bm_store.py:2501-2524) allows only
from VERIFYING and FAILED_RECOVERABLE.

### Reproduction 1 (simplest: three shipped CLI commands, no contract move)

Probe: scratchpad/probe_f1f_stop_then_result.py. Sequence, each line
being what one CLI command does:

1. `begin` plus `plan` one unit u1, write_scope ["a.py"], a done_check
   that fails, then `step` with a worker returning status "pending"
   (exactly what the production RecordIntentWorker does). The run parks
   in EXECUTING with an open dispatch.
2. `engine.stop("p1", ...)` (`bm-controller stop`). The run reaches
   STOPPED. The contract is NOT touched, so its revision does not move.
3. `engine.receive_result("p1", dispatch_id, "claims done", ["a.py"],
   cost={"tokens": 1})` (`bm-controller record-result`), with the
   rollback command failing.

Output:

```
== founder stop, then a late result (rollback exit=1) ==
  run state after stop: STOPPED
  contract revision unchanged: 1 state: live
  receive_result RAISED: OwnershipRefused: run '0dcf...' is STOPPED; moving it to FAILED_TERMINAL is not legal from there. Legal moves from STOPPED: (none, terminal).
  run state: STOPPED
  founder steps: 0
  unit status on a STOPPED run: READY retry: 1
```

The founder is never warned about the dirty write scope (0 open human
steps), which is the exact consequence F1 named. The staleness re-read
cannot absorb it, because the contract never moved.

Secondary observation from the same probe with a CLEAN rollback:
`receive_result` returns "rejected" and re-queues the unit to READY on a
run that is already STOPPED. A terminal run should not be growing new
selectable work.

### Reproduction 2 (DELIVERABLE_READY, and the run then re-dispatches)

Probe: scratchpad/probe_f1d_deliverable_ready.py. All four steps are
shipped CLI commands (start, plan, step, record-result).

1. `plan` u1 (async, parks) and u2 (returns immediately). One `step`
   dispatches both; u2 settles, so `_settle_after_wave` leaves the run
   CHECKPOINTED with u1's dispatch still open.
2. `plan` again with a graph that omits u1 (a founder re-plan).
   upsert_units marks u1 SKIPPED (tools/bm_store.py:12953-12961) while
   its dispatch stays DISPATCHED.
3. `step`. Nothing is non-terminal, so `_deliver_or_hold` runs and the
   run reaches DELIVERABLE_READY.
4. `record-result` for u1's still-open dispatch, done_check failing,
   rollback failing.

Output:

```
wave 1 dispatched: ['u1', 'u2'] completed: ['u2']
run state: CHECKPOINTED
unit statuses: {'u1': 'DISPATCHED', 'u2': 'DONE'}
after re-plan statuses: {'u1': 'SKIPPED', 'u2': 'DONE'} run: READY
u1 dispatch still open: DISPATCHED
after step run state: DELIVERABLE_READY note: deliverable ready
u1 fence before result: active
receive_result RAISED: OwnershipRefused: run 'b5f9...' is DELIVERABLE_READY; moving it to FAILED_TERMINAL is not legal from there. Legal moves from DELIVERABLE_READY: COMPLETE, READY, STOPPING, PAUSED.
run state after: DELIVERABLE_READY
u1 fence after: active
open human steps: 0
final unit statuses: {'u1': 'READY', 'u2': 'DONE'}
next step dispatched: ['u1'] state: DELIVERABLE_READY
u1 dispatch count: 2
```

Every consequence F1 listed is present: the call aborts before the
founder warning, the fence is left ACTIVE, the run keeps a state claiming
the deliverable is ready, and the unit is dispatched a second time with
its write scope possibly dirty.

### The state matrix

Probe: scratchpad/probe_f1_state_matrix.py. One unit parked async, the
run moved along LEGAL edges only to each target state, then a rejected
result whose rollback also fails. The contract is left alone so the
staleness branch does not mask the state-walk question.

```
EXECUTING           -> outcome=rejected  final=FAILED_TERMINAL    founder_steps=1 fence=parked
VERIFYING           -> outcome=rejected  final=FAILED_TERMINAL    founder_steps=1 fence=parked
CHECKPOINTED        -> outcome=rejected  final=FAILED_TERMINAL    founder_steps=1 fence=parked
READY               -> outcome=rejected  final=FAILED_TERMINAL    founder_steps=1 fence=parked
WAITING_HUMAN       -> outcome=rejected  final=FAILED_TERMINAL    founder_steps=1 fence=parked
DELIVERABLE_READY   -> outcome=RAISED    final=DELIVERABLE_READY  founder_steps=0 fence=active
PAUSED              -> outcome=RAISED    final=PAUSED             founder_steps=0 fence=active
FAILED_RECOVERABLE  -> outcome=rejected  final=FAILED_TERMINAL    founder_steps=1 fence=parked
STOPPING            -> outcome=RAISED    final=STOPPING           founder_steps=0 fence=active
STOPPED             -> outcome=RAISED    final=STOPPED            founder_steps=0 fence=active
```

Honest scoping of the four breaks:

- STOPPED and STOPPING are reachable with no contract move at all,
  through `bm-controller stop` (reproduction 1). Live.
- DELIVERABLE_READY is reachable through a re-plan (reproduction 2).
  Live.
- PAUSED is reached in production only when the contract itself is
  paused, and set_contract_state appends a new revision
  (tools/bm_store.py:12026-12067), so the staleness re-read at
  tools/bm_controller.py:888-890 rejects the result before `_reject` is
  reached. PAUSED is therefore LATENT, not currently exploitable. That
  last sentence is inference from reading set_contract_state, not a
  probed end-to-end result.

### Sibling path the fix did not cover: check_timeouts

tools/bm_controller.py:534-575 records a result and a verification and
then calls `_reject` at line 568 with NO `_ensure_verifying` in between,
so the same FAILED_TERMINAL move is attempted from EXECUTING.

Probe: scratchpad/probe_f1b_timeouts.py.

```
dispatched: ['u1']
run state after async park: EXECUTING
unit status: DISPATCHED fence: active
check_timeouts RAISED: OwnershipRefused: run 'bb74...' is EXECUTING; moving it to FAILED_TERMINAL is not legal from there. Legal moves from EXECUTING: VERIFYING, STOPPING, PAUSED, FAILED_RECOVERABLE.
run state after check_timeouts: EXECUTING
fence state after check_timeouts: active
open human steps: 0
unit status/retry: FAILED 1
next step raised: OwnershipRefused run 'bb74...' is EXECUTING; moving it to READY is not legal from there.
```

With a CLEAN rollback the run is still wedged, because check_timeouts
never walks the run out of EXECUTING at all. Probe:
scratchpad/probe_f1c_deliver_from_executing.py (two timeouts, breaker
exhausted):

```
state after park 1: EXECUTING
timeout 1 abandoned: ['u1']
state after timeout 1: EXECUTING
state after park 2: EXECUTING
timeout 2 abandoned: ['u1']
unit status/retry after timeout 2: FAILED 2
run state: EXECUTING
step RAISED: OwnershipRefused: run '5b8a...' is EXECUTING; moving it to READY is not legal from there. Legal moves from EXECUTING: VERIFYING, STOPPING, PAUSED, FAILED_RECOVERABLE.
run_to_completion RAISED: (same)
```

Every subsequent `step` raises, permanently. The offending move is
`_deliver_or_hold`'s converge-before-delivery at
tools/bm_controller.py:1211-1215, which assumes the run can reach READY.

Reachability caveat, stated plainly: check_timeouts is a public engine
method but is NOT wired to a CLI subcommand (tools/bm_controller.py:1318
says so). It is reachable from any scheduler or SDK caller, and from the
test suite (tools/test_bm_controller.py:531), not from the eight shipped
commands.

### Suggested shape of a real fix (not applied)

Make the walk total rather than enumerated. From any state that cannot
reach VERIFYING, either refuse the whole call up front with a named
refusal (a result arriving for a stopped or delivered run is a real
situation, not a state-machine accident), or write the dirty-rollback
founder step and release the fence FIRST and attempt the state move last,
so a founder warning can never be lost to an illegal move. Add the same
`_ensure_verifying` to check_timeouts.

---

## F2: REFUTED

### New hole the fix introduces: the revision straddle

`_gate_check_write_scope` (tools/bm_controller.py:689-730) makes one
gate_check call per distinct path and returns the LAST verdict.
`_claim_and_dispatch` records `verdict["revision"]` from that last
verdict (tools/bm_controller.py:793-795), and that recorded revision is
the whole input to the staleness re-read at
tools/bm_controller.py:888-890. If a contract amend lands between two of
the per-path calls, path 1 was judged under the OLD revision, the
dispatch is stamped with the NEW one, and the staleness protocol sees no
movement.

Probe: scratchpad/probe_f2_revision_straddle.py. The concurrent writer is
a second `sign_contract(..., supersede=True)` fired from inside the first
gate_check call, which is what a second process running `bm-autonomy`
against the same SQLite store does.

```
  gate_check #1 path='docs/x.md' -> ALLOWED rev=1
  [concurrent writer] amended to revision 2, allowed_paths now ['src']
  gate_check #2 path='src/a.py' -> ALLOWED rev=2
  worker brief write_scope: ['docs/x.md', 'src/a.py']
dispatched: ['u1'] completed: ['u1']
unit status: DONE
dispatch recorded contract_revision: 2 status: VERIFIED
live contract revision: 2 allowed_paths: ['src']
gate_check on docs/x.md under the LIVE contract: REFUSED-SCOPE
fence files claimed: ['docs/x.md', 'src/a.py']
RESULT: unit accepted under a contract that forbids one of its write paths: True
```

Control, proving this is NEW and not pre-existing: the identical race
against a SINGLE-path unit (the pre-fix shape) is caught, because the
recorded revision is then the one the path was actually judged under.
Probe: scratchpad/probe_f2_singlepath_control.py.

```
  gate_check #1 path='docs/x.md' -> ALLOWED rev=1
  [concurrent writer] amended to revision 2, allowed_paths now ['src']
dispatched: ['u1'] completed: []
unit status: READY
dispatch recorded contract_revision: 1 status: REJECTED
RESULT: unit accepted under a contract that forbids one of its write paths: False
```

Severity MEDIUM: it needs a concurrent supersede amend that narrows
allowed_paths, landing between two store reads. That is precisely the
TOCTOU class the design's step 13 exists to close, so it should not be
left open by the component that feeds it. Fix shape: capture the FIRST
verdict's revision, and refuse (or re-run the whole loop) if any later
verdict reports a different revision.

### The property the fix claims is still false by another route

The docstring at tools/bm_controller.py:689-718 argues that gate_check is
the only component comparing a unit's scope against allowed_paths and
therefore must see every path. True, and yet the comparison it performs
is an OVERLAP test, not a CONTAINMENT test: `paths_overlap`
(tools/bm_store.py:537-561) is symmetric and treats "." as overlapping
everything, and gate_check uses it at tools/bm_store.py:12578-12586. A
unit that declares the PARENT of an allowed path, or ".", passes on every
path.

Probe: scratchpad/probe_f2b_ancestor_scope.py, contract allowed_paths
["src/app"]:

```
  gate_check path='src/app/main.py'  -> ALLOWED
  gate_check path='src/secrets.env'  -> REFUSED-SCOPE
  gate_check path='src'              -> ALLOWED
  gate_check path='.'                -> ALLOWED
  gate_check path='secrets'          -> REFUSED-SCOPE
dispatched: ['u1']
brief handed to the worker, write_scope: ['src']
unit status: DONE
fence files claimed: ['src']
```

So the escape F2 closed (a forbidden path listed second) is reachable
again by widening the first path instead of adding a second: the worker
is handed a brief and a fence covering all of `src`, including
`src/secrets.env`, which gate_check refuses when named directly.

Honest attribution: this is a store-level property that predates the fix.
I am NOT claiming the fix introduced it. I am claiming the fix does not
achieve the security property its own docstring states, and that a
reviewer reading that docstring would believe otherwise.

### F2 attacks that failed (fix held)

- Empty write_scope: `paths or [None]` still gate-checks the risk class
  (tools/bm_controller.py:725), confirmed by the fix's own passing test.
- Duplicate paths: deduplicated in declaration order, no verdict change.
- read_scope: deliberately not gate-checked, and allowed_paths is a write
  boundary; the brief carries read_scope but the fence claims only
  write_scope, and no write authorisation is derived from it. NO-DATA,
  not a finding.
- Unit mutation between the check and the claim: `_claim_and_dispatch`
  uses the SAME in-memory row for the gate check, the fence claim and the
  brief, and a concurrent re-plan cannot land anyway, because the run is
  already EXECUTING by then (tools/bm_controller.py:397) and upsert_units
  refuses when READY is not a legal move from the run's state
  (tools/bm_store.py:12999-13008).

---

## F3: STANDS

The guard at tools/bm_controller.py:516-521 (and its twin on the
synchronous path at 864-869) does what it claims. Two attacks:

- Double result. `receive_result` twice on one dispatch refuses cleanly
  at record_result, before any state walk, and leaves the run state and
  the spend meter untouched. Probe: scratchpad/probe_f3.py, attack A.

```
  first: u1
  second call refused: OwnershipRefused: dispatch '91eb...' is VERIFIED, not DISPATCHED; a result was alre
  run state unchanged by the refused duplicate: True
  spend after one accepted + one refused result: 1
```

- The guard is itself a read-then-act pair, so a revoke landing between
  the latest_contract read and record_spend still raises. Probe:
  scratchpad/probe_f3.py, attack B, with the revoke injected inside the
  guard's own read.

```
  [concurrent writer] revoked right after the guard read
  receive_result RAISED: OwnershipRefused: project 'p1' has no live contract (revoked); spend can only be recorded against a live authorisation.
  run state: VERIFYING
  unit status: RESULT_IN fence: active
  recovery step note: resumed a RESULT_IN dispatch straight to verification (crash between result and commit)
  recovery run state: READY
  unit status after recovery: READY fence: parked
  dispatch status: REJECTED
```

The window shrinks from "any moment between dispatch and record-result",
which is minutes to hours, to two adjacent store calls, and the RESULT_IN
resume branch settles the dispatch correctly on the very next step. That
is a real fix, and the residual is LOW and self healing. Recorded as a
residual, not a refutation.

CLI input paths are clean too: cmd_record_result parses tokens and
minutes through `_int_flag(..., minimum=0)`
(tools/bm_controller.py:1747-1748 and 1446-1467), so record_spend's
ValueError guards for negative or non-integer cost cannot be reached from
the shipped command.

---

## F4: REFUTED

### Reproduction 1: a SKIPPED dependency

`_block_unreachable_units` recognises only `status_by_id.get(dep) ==
"FAILED"` (tools/bm_controller.py:1156). `select_ready_units` requires
every dependency to be DONE (tools/bm_store.py:13052-13054), and
upsert_units marks any unit absent from a re-plan SKIPPED
(tools/bm_store.py:12953-12961). A SKIPPED dependency is therefore just
as permanently unreachable as a FAILED one, and nothing escalates it.

Probe: scratchpad/probe_f4c_skipped_dep.py. Sequence: plan u0, u1, u2
(u2 depends on u1), then re-plan with u0 and u2 only, then
run_to_completion.

```
statuses after the re-plan: {'u0': 'READY', 'u1': 'SKIPPED', 'u2': 'PENDING'}
steps taken: 15 of max_steps=15
final summary state: CHECKPOINTED | store state: CHECKPOINTED
note: no unit is currently selectable (dependencies unmet or in flight); waiting
statuses: {'u0': 'DONE', 'u1': 'SKIPPED', 'u2': 'PENDING'}
open founder steps: 0
STALLED AND SPUN: True
```

This is F4's original symptom word for word: the run rests in
CHECKPOINTED with no delivery, no terminal state and no founder gate, and
run_to_completion burns every one of its max_steps.

### Reproduction 2: a FAILED dependency plus any founder-gated lane

The whole-run judgement at tools/bm_controller.py:1097 asks whether every
non-terminal unit has status BLOCKED. A unit whose LANE has an open human
step is not selectable but keeps status READY, so the judgement is false,
the escalation finds nothing new to escalate, and the run rests in
CHECKPOINTED.

Probe: scratchpad/probe_f4_stall.py, case C: u1 fails its breaker, u2
depends on u1, g1 sits in a lane with an open founder step.

```
== C: failed dependency plus a gated lane ==
  steps taken: 20 of max_steps=20
  final summary state: CHECKPOINTED | store state: CHECKPOINTED
  statuses: {'u1': 'FAILED', 'u2': 'BLOCKED', 'g1': 'READY'}
  note: no unit is currently selectable (dependencies unmet or in flight); waiting
  SPUN THROUGH EVERY STEP: True
```

Case D in the same probe shows the spin is not exclusive to F4's
territory: a single gated lane with nothing failed at all also spins
run_to_completion through every step, resting in READY. That part is
pre-existing and outside the F4 fix's claim, recorded here so the two are
not confused.

### F4 attacks that failed (fix held)

- Retrying dependency. mark_unit_failed leaves a unit READY while
  retry_count is within the ceiling (tools/bm_store.py:13236), and the
  escalation only looks for FAILED, so a merely retrying dependency does
  NOT misfire. Probe: scratchpad/probe_f4.py attack A: 0 human steps
  after the retryable failure, and the run finishes DELIVERABLE_READY
  with both units green.
- One-shot guard hiding a later wave. The guard only suppresses the
  single recursive re-entry; every later call of `_handle_no_ready_units`
  arrives with escalate_unreachable=True. Two independent lanes, each
  failing its own head unit, both get their own founder step. Probe:
  scratchpad/probe_f4.py attack B: `founder steps naming each unreachable
  unit: {'a2': True, 'b2': True}`, run reaches WAITING_HUMAN in 2 steps.
- Collateral lane blocking. block_lane_units flips healthy PENDING and
  READY units of the same lane to BLOCKED (probe scratchpad/probe_f4.py
  attack C: u3 ends BLOCKED though it only ever waited on a gated lane).
  Those units were already unselectable because queue_human_step blocks
  the lane, and BLOCKED is reversible through unblock_lane_units, so this
  is a cost of the design's own pairing rather than a defect. Recorded as
  an observation.

---

## Attempts log

Probes live in the session scratchpad
(/private/tmp/claude-1598639508/-Users-khalil-maaouni-Documents-Development-Work-Frameworks-BrothermeUp/e2edd454-7254-4d3a-ad14-5c05858ffb3a/scratchpad),
which is ephemeral. Each probe's sequence is reproduced in full above, so
every finding can be rebuilt from this file alone.

| # | Attack | Probe | Result |
|---|---|---|---|
| 1 | Baseline: do the four new test classes pass | unittest, four classes | PASS, 7 tests |
| 2 | F1 on check_timeouts with a failing rollback | probe_f1b_timeouts.py | BREAK, illegal-state-move from EXECUTING |
| 3 | F1 on check_timeouts with a clean rollback, breaker exhausted | probe_f1c_deliver_from_executing.py | BREAK, every later step() raises |
| 4 | F1 from DELIVERABLE_READY after a re-plan | probe_f1d_deliverable_ready.py | BREAK, original defect verbatim plus a second dispatch |
| 5 | F1 state matrix over ten run states | probe_f1_state_matrix.py | BREAK in 4 of 10 states |
| 6 | F1 after a founder stop, no contract move | probe_f1f_stop_then_result.py | BREAK, simplest reproduction |
| 7 | F1 double result | probe_f3.py attack A | HELD |
| 8 | F1 PAUSED reachability with an unchanged revision | read of set_contract_state, tools/bm_store.py:12026-12067 | HELD, latent only (inference, not probed) |
| 9 | F2 amend straddling the per-path loop | probe_f2_revision_straddle.py | BREAK, new hole |
| 10 | F2 single-path control under the same race | probe_f2_singlepath_control.py | HELD, proves 9 is new |
| 11 | F2 ancestor or "." write_scope widening | probe_f2b_ancestor_scope.py | BREAK, claimed property false |
| 12 | F2 empty write_scope, duplicate paths, read_scope abuse | code read plus the fix's own tests | HELD |
| 13 | F2 unit mutation between check and claim | code read, tools/bm_controller.py:397 and tools/bm_store.py:12999 | HELD, a concurrent re-plan is refused |
| 14 | F3 revoke inside the guard window | probe_f3.py attack B | RESIDUAL, self healing on the next step |
| 15 | F3 malformed or negative cost from the CLI | code read, _int_flag minimum=0 | HELD |
| 16 | F4 merely retrying dependency | probe_f4.py attack A | HELD, no misfire |
| 17 | F4 second wave on a later call | probe_f4.py attack B | HELD |
| 18 | F4 collateral same-lane blocking | probe_f4.py attack C | Observation only |
| 19 | F4 failed dependency plus a gated lane | probe_f4_stall.py case C | BREAK, still spins max_steps |
| 20 | F4 one gated lane, nothing failed | probe_f4_stall.py case D | BREAK, pre-existing, outside F4's claim |
| 21 | F4 SKIPPED dependency | probe_f4c_skipped_dep.py | BREAK, original symptom verbatim |

Discovery ran until a round produced nothing new: round 1 found attempts
2 to 8, round 2 found 9, 11, 19 and 21, round 3 (unit mutation, cost
parsing, collateral blocking, PAUSED reachability) found no new break.

## What was not checked

- The full test suite was not run (suite lock). Only the four new classes
  were executed.
- The CLI subcommands were exercised as engine calls, never as real
  subprocesses; the argument parsing of record-result and plan was read,
  not run.
- Genuine multi-process concurrency was simulated inside one process by a
  delegating store wrapper. The SQLite locking behaviour of two real
  concurrent bm-controller processes was not tested.
- tools/bm_store.py was read only where the controller touches it (state
  tables, gate_check, spend, units, contracts, path helpers). The rest of
  its 15210 lines was not reviewed.
- The PAUSED row of the F1 state matrix is classified as latent by
  reading set_contract_state, not by an end-to-end probe.
