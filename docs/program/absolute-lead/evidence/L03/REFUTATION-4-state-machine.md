# REFUTATION 4, the STATE MACHINE lens: the round-4 controller rebuild

Target: the CURRENT working tree at /Users/khalil.maaouni/Documents/BrotherModeUp,
tools/bm_controller.py (3177 lines) and the tools/bm_store.py entry points it
calls. Read only except this file. No git state was changed. tools/test_all.py
was NOT run. Every probe built its own throwaway store under a fresh temp dir
in /tmp; no real .brothermode directory was touched.

Read first, in full: DESIGN-round4.md, FIX-round4-store-report.md,
FIX-round4-controller-report.md (including its three collisions),
REFUTATION-2-fixes.md, REFUTATION-3-state-machine.md,
REFUTATION-3-authorization.md, REFUTATION-3-liveness.md, docs/FULL-AUTO.md,
docs/KNOWN-LIMITS.md.

Probe scripts: /private/tmp/claude-1598639508/-Users-khalil-maaouni-Documents-Development-Work-Frameworks-BrothermeUp/e2edd454-7254-4d3a-ad14-5c05858ffb3a/scratchpad/sm4/
(17 scripts, listed in the attempts log). That directory is EPHEMERAL; every
output that matters is pasted verbatim below.

---

## VERDICT LINES

| # | Verdict | Severity | One line |
|---|---|---|---|
| F1 | **FALSIFIED** | HIGH | a re-plan that redefines a unit whose dispatch is still open orphans that unit's fence, and every later pass parks in `CONTENTION` forever while telling the founder no action is needed |
| F2 | **FALSIFIED** | HIGH | the round-4 "held" answer is destroyed on the only route to `PAUSED` the shipped CLI offers: rejected for staleness on resume, retry burned, `git restore` run against the founder's files, meter never charged |
| F3 | **FALSIFIED** | HIGH | five `step()` exits return `stop_reason` None while the store holds a documented stop state, because `_settle_after_wave` computes the reason into a throwaway dict; the `reason:` line docs/FULL-AUTO.md:130 promises is absent, and `founder_gated` is dropped with it |
| F4 | **FALSIFIED** | HIGH | a crash between `mark_unit_done` and the settle leaves the run durably `VERIFYING`, which round 4 removed from `_DISPATCH_SOURCE_STATES`, so every later pass is `FOUNDER_WAITING` with zero open founder steps and a note naming three commands, two of which refuse |
| F5 | **FALSIFIED** | MEDIUM | `_resume_dispatched` gives ONE note to all three `REFUSED` causes, so two of the three tell the founder the contract changed when it did not |
| F6 | **FALSIFIED** | MEDIUM | a `DRAIN` verdict mid wave does not stop the wave: the worker is still handed the brief and the founder's done_check still runs, on a run the store already says is `STOPPED` |
| F7 | **FALSIFIED** | MEDIUM | `bm-controller stop` while the done-definition is running makes `bm-controller step` exit 1 with `illegal-state-move`, after writing a `deliverable-ready` checkpoint to a stopped run |
| F8 | **FALSIFIED** | MEDIUM | one wave, one dirty rollback, one outage: `FAILED_RECOVERABLE` is attempted from `FAILED_TERMINAL` and the refusal escapes `step()` |
| F9 | **FALSIFIED** | MEDIUM | design 6.4's invariant still fails on the SYNCHRONOUS path: an outage earlier in the same wave makes `_ensure_verifying` a no op, so the next unit's result is judged from `FAILED_RECOVERABLE` |
| F10 | **FALSIFIED** | LOW | the BLOCKED view `_handle_late_result` writes on a terminal run has no reverse gear: no later `step()` ever drives a terminal run, so resolving the founder step never clears it |
| S1 | **STANDS** | | law L2: `summary["state"]` equalled the store state at return time in every one of 27 summaries across 9 scenario families |
| S2 | **STANDS** | | the PAUSED founder-only gate: 8 entry points, only `receive_result` wrote anything, and only what design 4.3 authorises |
| S3 | **STANDS** | | the orchestrator's third ruling: `FAILED_RECOVERABLE` IS the store state in s1 under all four outage shapes (first wave, second wave, both mixed orders) |
| S4 | **STANDS** | | SM C: a late result on a STOPPED run charges the meter, 0 to 9000 |
| S5 | **STANDS** | | SM D: a late result at the retry ceiling with a dead contract leaves an open founder step naming the unit |
| S6 | **STANDS** | | design 6.4 on the ASYNCHRONOUS paths: `receive_result` and `check_timeouts` both reach VERIFYING from `FAILED_RECOVERABLE` |
| S7 | **STANDS** | | held twice, held then revoke, held then re-plan drops the unit: no double charge, no duplicate acceptance, the drop stands |

---

## F1 (HIGH, CONFIRMED): a re-plan of a unit with an open dispatch parks the run in CONTENTION forever

### What the machinery claims

Round 4's `_authorise_dispatch` catches a fence refusal on the fresh route and
returns `DEFER` (tools/bm_controller.py:1637 to 1638), which `step()` turns
into `CONTENTION` (tools/bm_controller.py:765 to 767) with the round-4 note

```
tools/bm_controller.py:383  _NOTE_CONTENTION = ("another writer holds a fence over this unit's files, "
tools/bm_controller.py:384                      "or the contract was amended twice while the unit was "
tools/bm_controller.py:385                      "being checked; no founder action is needed and the "
tools/bm_controller.py:386                      "next step tries the same unit again")
```

DESIGN-round4 3.4 fixes that wording, and its table says of `CONTENTION`:
"a fence overlap or a double contract amend deferred every unit; **no, and the
note may not say otherwise**". docs/FULL-AUTO.md ships the same promise:
"`CONTENTION` in particular never means a founder is needed: it clears when the
other writer releases its fence or the contract stops moving."

### The defect

`upsert_units`' redefinition UPDATE sets `fence_uuid=NULL`
(tools/bm_store.py:13095) on a unit whose fence is still ACTIVE, and
`orphaned_fences` is appended to ONLY inside the dropped-unit loop
(tools/bm_store.py:13196), so `ControllerEngine.plan`'s new orphan-parking loop
(tools/bm_controller.py:618 to 621) parks nothing. Round 4's
`_resume_result_in_and_orphans` gained a SKIPPED-fence branch
(tools/bm_controller.py:1253) and a CLAIMED-with-no-dispatch branch (1262) but
no branch for a unit whose fence pointer was cleared while the fence was live,
so nothing ever reclaims it. `Store.claim` only reclaims an active name in place
when the caller's session_id matches the one on file
(tools/bm_store.py:10165), and tools/bm_controller.py:2531 gives every CLI
process "a fresh unguessable id per process when omitted", so the next process
gets `name-active` forever.

### Reproduction, SHIPPED CLI ONLY, no concurrency, no crash

Probe `sm4/h4_cli_replan_contention.py`, real subprocesses of bm_store.py,
bm_project.py, bm_autonomy.py and bm_controller.py against a throwaway
BROTHERMODE_ROOT. Sequence: `init`, `project start`, `autonomy sign`,
`controller start`, `controller plan` (u1, u2), `controller start`
(dispatches both, parks), `controller record-result` for u1 only,
`controller plan` again with u2's objective changed, then `controller step`.

```
open dispatches after the first wave: {'u1': 'eff8fbb9e80a470b9988103cdc58f1cc', 'u2': '013173d1383940c5b632ee4d3b881be0'}
$ bm_controller.py record-result
  exit=0
  | unit u1 accepted (dispatch eff8fbb9e80a470b9988103cdc58f1cc)

=== the founder re-plans, changing u2's objective ===
$ bm_controller.py plan
  exit=0
  | planned 2 unit(s) for run b365463f81f34e799947289955c89c43

=== every later pass ===
$ bm_controller.py step
  exit=0
  | run b365463f81f34e799947289955c89c43: state READY
  | note: the live contract no longer authorises the in-flight unit's write scope; its dispatch was closed and no worker was re-asked
$ bm_controller.py step
  exit=0
  | run b365463f81f34e799947289955c89c43: state CHECKPOINTED
  | note: another writer holds a fence over this unit's files, or the contract was amended twice while the unit was being checked; no founder action is needed and the next step tries the same unit again
  | reason: CONTENTION
$ bm_controller.py step
  ... identical ...
$ bm_controller.py step
  ... identical ...

run state: CHECKPOINTED
units    : {'DONE': 1, 'READY': 1}
open human steps: 0
```

The in-process form, `sm4/h3_replan_fresh_engine.py`, uses a FRESH
`ControllerEngine` per command (what the CLI does) and shows the state
underneath:

```
run state: CHECKPOINTED, u2 dispatch still open
after the re-plan: u2 status=READY fence_uuid=None; the fence unit-u2 is still active

step 1: state=READY        reason=None        dispatched=[]
step 2: state=CHECKPOINTED reason=CONTENTION  dispatched=[]
step 3: state=CHECKPOINTED reason=CONTENTION  dispatched=[]
...
step 8: state=CHECKPOINTED reason=CONTENTION  dispatched=[]

units: {'u1': 'DONE', 'u2': 'READY'}
u2 dispatch rows: [(1, 'REJECTED')]
open founder steps: 0
orphan fence at the end: active (unit-u2)
run_to_completion: 1 step(s), last reason=CONTENTION state=CHECKPOINTED
```

### Why the re-plan is accepted at all

`upsert_units` refuses only when READY is not legal from the run's state
(tools/bm_store.py:13234 to 13243). It IS legal from CHECKPOINTED, which is
exactly where `receive_result` leaves a run that still has another dispatch open
(`_settle_after_wave`, tools/bm_controller.py:1980, then
`_handle_no_ready_units`'s IN_FLIGHT early return, 2068 to 2072). A re-plan
while the run is EXECUTING is refused cleanly, which is why probe
`sm4/h1_replan_redefines_inflight.py` did NOT reproduce and `h2`/`h3` did: the
window is "one unit answered, another is still in flight", which is the ordinary
shape of every multi-unit run driven by the production RecordIntentWorker.

### Consequence

The run never delivers, never fails, never queues a founder step, and the one
founder-facing line it prints says no founder action is needed. The escape
exists (`bm_store.py park` can park a fence by name, tools/bm_store.py:15435)
but nothing in the controller's output names it, and the founder has no reason
to look for it. The same `fence_uuid=NULL` clearing appears in the fault-3
cascade (tools/bm_store.py:13223) with the same orphan shape for DONE units.

### The narrower defect underneath

`_authorise_dispatch`'s `DEFER` outcome cannot tell a LIVE competing writer from
a fence nobody owns any more, so the note is a guess. Round 3 was refuted for
claiming a founder was needed when none was (LV 5); round 4 now claims none is
needed when one is. The honest fix is to distinguish them (the fence record's
own session and state are both readable at that point), not to pick a side.

---

## F2 (HIGH, CONFIRMED): the "held" answer is destroyed on the only route to PAUSED the CLI offers

### What the machinery claims

DESIGN-round4 4.3 and 18.1: the held answer "survives the pause and is accepted
afterwards, instead of being destroyed (rolled back on disk, retry burned)".
docs/FULL-AUTO.md:75 to 85 ships it to the founder:

> `PAUSED`: the underlying contract was paused, or the founder asked the
> controller to pause. ... A result that arrives during a pause is RECORDED AND
> HELD, never rejected: the answer is durable and the meter is charged, but
> nothing is judged and no rollback command touches your files, so a pause never
> destroys real work. `bm-controller resume` plus one `step` then verifies the
> held answer on its own merits.

### The defect

There is no `bm-controller pause` command (COMMANDS, tools/bm_controller.py:3128
to 3137, has eight: start, step, plan, record-result, status, stop, resume,
complete). The ONLY producer of a PAUSED run is `step()`'s contract-paused
branch (tools/bm_controller.py:675 to 679). Reaching it requires
`bm-autonomy pause`, and `set_contract_state` "appends revision N+1"
(tools/bm_store.py:12112). The dispatch was stamped with revision N
(tools/bm_controller.py:1643), so `_verify_and_finish`'s staleness re-read
(1733 to 1760) rejects the held answer the moment the founder resumes. Every
consequence design 4.3 says it removed then happens one command later.

The test that pins the fixed behaviour reaches PAUSED with
`store.set_run_state(run["run_id"], "PAUSED", ...)`
(`_pause_the_run`, tools/test_bm_controller.py:1988 to 1994), which leaves the
contract revision untouched. That state is not reachable through any shipped
command, and its own docstring says so on purpose ("ask what the ENGINE does
from PAUSED rather than whether PAUSED was reachable"). The consequence is that
`TestR3PausedIsAFounderOnlyGate.test_a_result_arriving_on_a_paused_run_is_recorded_and_held`
passes while the founder-facing promise fails.

### Reproduction, SHIPPED CLI ONLY

Probe `sm4/d1_cli_held_pause.py`, real subprocesses, a real `out.txt` written to
disk before the result is recorded:

```
=== the founder presses pause ===
$ bm_autonomy.py pause --project p1 --reason
  | project p1 contract -> paused (revision 2)

=== bm-controller step (the engine writes the run PAUSED) ===
  | run a17f63b6...: state PAUSED
  | note: contract is paused
  | reason: FOUNDER_WAITING

=== the worker's real answer arrives ===
$ bm_controller.py record-result --project p1 --dispatch-id
  | dispatch b479979b... recorded and HELD: the run is PAUSED, so nothing was judged, no rollback ran and the fence is still held.

=== the founder resumes the RUN ===
  | project p1 controller run a17f63b6...: PAUSED -> READY

=== the next step: what happened to the held answer? ===
  | run a17f63b6...: state WAITING_HUMAN
  | completed: (none)
  | note: resumed a RESULT_IN dispatch straight to verification (crash between result and commit)

=== the verdict ===
run state        : WAITING_HUMAN
units by status  : {'READY': 1}
open human steps : 1
spend            : {... 'tokens': 0 ...}
out.txt still on disk: True
```

The in-process form, `sm4/d2_why_held_dies.py`, names the mechanism and runs the
control where the founder resumes the CONTRACT first:

```
=== resume the contract first: False ===
dispatch stamped with contract revision 1
contract revision after `bm-autonomy pause`: 2
record-result -> 'held'
spend after the hold: 0
dispatch status=REJECTED verdict='stale: contract moved from revision 1 to 2 between dispatch and verification'
unit status=READY retry_count=1 fence=parked
CheckRunner was asked to run: ['true', 'git restore -- out.txt']

=== resume the contract first: True ===
contract revision after `bm-autonomy resume`: 3
dispatch status=REJECTED verdict='stale: contract moved from revision 1 to 3 between dispatch and verification'
unit status=READY retry_count=1 fence=parked
CheckRunner was asked to run: ['true', 'git restore -- out.txt']
```

No founder ordering saves it: the revision only ever increases.

### Consequence, against the shipped paragraph

* "the meter is charged": FALSE. `_record_spend`'s live-contract guard
  (tools/bm_controller.py:1021 to 1023) skips a paused contract, so
  `--tokens 9000` charged 0. SM C's under-count survives for exactly the pause
  case, which is the case design 4.3 added the call for.
* "no rollback command touches your files": FALSE one command later.
  `git restore -- out.txt` ran against the founder's tree.
* "a pause never destroys real work": FALSE. The answer is REJECTED, a retry is
  burned, and in the CLI run the failed rollback also queued a dirty-scope
  founder step ("open human steps: 1").
* "verifies the held answer on its own merits": FALSE. It is judged stale before
  its merits are reached.
* "or the founder asked the controller to pause" names a command that does not
  exist.

The held answer is still RECORDED, so nothing is lost that a founder could not
recover by hand. What is lost is every property the design and the doc claim.

---

## F3 (HIGH, CONFIRMED): five step() exits report no stop_reason on a stop state

### What the machinery claims

Law L3 (DESIGN-round4 section 2): "Control flow reads the enum, never the prose.
`stop_reason` is the only field any loop or CLI driver branches on." Section 3.1:
`None` means "the wave made progress and a loop may call `step()` again".
docs/FULL-AUTO.md:130: "No line is empty and no reason is missing. A pass with no
`reason:` line made progress and the loop kept going."

### The defect

`_settle_after_wave` calls the reason-computing method with a throwaway dict:

```
tools/bm_controller.py:1991        summary = {"note": ""}
tools/bm_controller.py:1992        self._handle_no_ready_units(project_id, run_id, summary)
```

Every `_set_reason` and every `founder_gated` block that `_handle_no_ready_units`
(2033) or `_deliver_or_hold` (2242) writes during a settle is written into that
dict and dropped. Each caller of `_settle_after_wave` then returns through
`_finish` with `stop_reason` left None (step's own wave at 787 to 789,
`_resume_result_in_and_orphans` at 666 to 668, `_resume_dispatched` at 1364 to
1376). `cmd_step` prints the reason only `if summary.get("stop_reason")`
(tools/bm_controller.py:2767), so the line simply disappears.

### Reproduction

Probe `sm4/f1_reason_vs_store.py`, five routes, each printing the summary beside
the store read at return time:

```
route                                  summary[state]      store state         stop_reason      reason: line?
sync wave delivers                     DELIVERABLE_READY   DELIVERABLE_READY   None             NO
RESULT_IN resume delivers              DELIVERABLE_READY   DELIVERABLE_READY   None             NO
re-await delivers                      DELIVERABLE_READY   DELIVERABLE_READY   None             NO
sync wave settles into WAITING_HUMAN   WAITING_HUMAN       WAITING_HUMAN       None             NO
mid-wave drain                         STOPPED             STOPPED             None             NO
```

F2's shipped-CLI run is the same defect seen by a founder: `bm-controller step`
printed `state WAITING_HUMAN` with an open founder step and no `reason:` line at
all.

`founder_gated` goes the same way. Probe `sm4/f2_founder_gated_lost.py`, one
unit, one open founder step in another lane:

```
step1 state=DELIVERABLE_READY reason=None      founder_gated=None
step2 state=DELIVERABLE_READY reason='DELIVERED' founder_gated=None
```

The step that actually delivered carries neither; the next step carries the
reason but `_deliver_or_hold`'s already-delivered early return (2268 to 2274)
writes nothing, so `_report_trace`'s "founder-gated remainder" line
(tools/bm_controller.py:2619 to 2623) is unreachable on this path. With the
production RecordIntentWorker every delivery happens inside a settle, so it is
unreachable in production, which contradicts docs/FULL-AUTO.md's own
"The founder-gated remainder, what DELIVERABLE_READY actually names" section.

### Consequence, bounded honestly

Both shipped drivers still stop, because `_loop_stops`' second clause reads
`summary["state"]` against `_RUN_TO_COMPLETION_STOP_STATES`
(tools/bm_controller.py:437 to 439). A driver that obeys L3 and the doc and
branches on the enum alone takes exactly ONE extra `step()`, which then reports
the right reason and writes nothing new. So this is an honesty and contract
defect, not a spin. It matters because the design made `stop_reason` the
primary control signal and the doc promises it is never missing.

---

## F4 (HIGH, CONFIRMED): a crash before the settle wedges the run in VERIFYING

### The defect

Round 4 derives `_DISPATCH_SOURCE_STATES` from `_DISPATCH_WALK_EDGES`
(tools/bm_controller.py:241 to 242, 314 to 316), which contains no edge out of
VERIFYING, so `_may_dispatch("VERIFYING")` is False and `step()` returns
FOUNDER_WAITING at 728 to 733. `_unwind_empty_wave` (867) only unwinds
EXECUTING. `_DELIVERY_WALK_EDGES` DOES carry VERIFYING to CHECKPOINTED (244),
so the omission is in the dispatch walk alone.

VERIFYING is durable after a crash between `mark_unit_done` and
`_settle_after_wave` inside `receive_result` (tools/bm_controller.py:1002 to
1003), which is the fault the class docstring says must be survivable ("A crash
between two Store calls in the same engine method is exactly what the ten fault
tests exercise").

### Reproduction

Probe `sm4/c2_verifying_wedge.py`: a delegating Store that raises SystemExit on
the VERIFYING to CHECKPOINTED move (a power loss, or Ctrl-C during
`bm-controller record-result`), then a FRESH engine against the same store:

```
crashed: simulated power loss before CHECKPOINTED
after crash: state=VERIFYING units={'u1': 'DONE', 'u2': 'PENDING'}
step1 state=VERIFYING reason=FOUNDER_WAITING dispatched=[] note='1 unit(s) are selectable but the run is VERIFYING, which only a founder can move (bm-contr'
   the shipped drivers stop here
selectable units the run will never start: ['u2']
open founder steps: 0
```

The note is `tools/bm_controller.py:731 to 733`: "which only a founder can move
(bm-controller resume, complete or stop)". Of the three, `resume` is a no-op on
a non-PAUSED run (tools/bm_controller.py:3057 to 3061, prints "already
VERIFYING, not PAUSED. Nothing to do", exit 0), `complete` is refused by
`CONTROLLER_STATE_TRANSITIONS` (COMPLETE is legal only from DELIVERABLE_READY,
tools/bm_store.py:2572), and only `stop` works, which abandons the remaining
work. The command that would actually rescue it, `bm-controller plan` (a re-plan
flips the run to READY, tools/bm_store.py:13234 to 13245), is the one command
the note does not name.

This is LV 2's own dead end restated: WAITING for a founder with ZERO open
founder steps and nothing a founder can resolve.

Round 3 would have dispatched from VERIFYING and then settled VERIFYING to
CHECKPOINTED, converging on a state lie rather than a wedge. I did NOT run round
3 to confirm that, so treat the comparison as unverified; the reproduction above
is against the current tree only.

---

## F5 (MEDIUM, CONFIRMED): the re-await refusal note names the wrong cause two times out of three

`_authorise_dispatch` returns `REFUSED` from three different branches: the
gate-refusal branch (tools/bm_controller.py:1534 to 1577), the stale-stamp
branch (1584 to 1602) and the dead-fence branch (1605 to 1621).
`_resume_dispatched` maps all three to one sentence, the `.get` default at
tools/bm_controller.py:1357 to 1359:

```
"the live contract no longer authorises the in-flight unit's write scope; its
 dispatch was closed and no worker was re-asked"
```

F1's shipped-CLI run printed exactly that after a re-plan that never touched the
contract (`sm4/h4_cli_replan_contention.py`, first step after the re-plan). The
contract was live and unchanged at revision 1 throughout. A founder reading that
line would go and inspect their contract.

---

## F6 (MEDIUM, CONFIRMED): a mid-wave DRAIN still hands the worker a brief

`step()` checks `_may_dispatch` once, before the loop (tools/bm_controller.py:
727 to 733), and the loop over `ready` (746 to 751) collects outcomes without
breaking. A `REFUSED-STATE` verdict on the SECOND unit calls `_begin_stopping`
(1529 to 1533), which walks the run to STOPPED and parks the FIRST unit's fence,
and then the worker loop at 776 to 785 runs anyway for whatever was already
authorised.

Probe `sm4/c1_mid_wave_drain.py`, with a delegating Store that performs the
founder's own `bm-autonomy revoke` between the two gate_check calls of one wave
(one process; a second process doing it is the real shape, and it is the window
design step 2 names):

```
summary state=STOPPED stop_reason=None dispatched=['u1'] completed=[]
store state          = STOPPED
unit statuses        = {'u1': 'READY', 'u2': 'READY'}
worker was handed    = 1 brief(s): [('u1', 1)]
checker ran          = ['true']
contract state       = revoked
fence u1             = parked
checkpoints          = ['stopped', 'heartbeat']
```

The worker was asked for real work AFTER the run reached STOPPED and after its
fence was parked, and the founder's `done_check` subprocess ran on a stopped
run. The design's own words for `stop` are "STARTS NO new unit". A retry was
burned on u1 by the staleness rejection that followed.

---

## F7 (MEDIUM, CONFIRMED): a founder stop during the done-definition raises out of step()

`_deliver_or_hold` reads `cur` once (tools/bm_controller.py:2267), then runs the
founder's WHOLE done_definition through the CheckRunner (2285), which for a real
project is a test suite that takes minutes, and only then uses that stale `cur`
to walk and deliver (2305 to 2314). This is the widest TOCTOU window in the
file, and the other writer is a founder running a shipped command.

Probe `sm4/i1_stop_during_done_definition.py` (a second engine calls
`stop("p1")` from inside the done_definition call):

```
step RAISED OwnershipRefused: run '0cd0f376...' is STOPPED; moving it to DELIVERABLE_READY is not legal from there. Legal moves from STOPPED: (none, terminal).
store state: STOPPED
units: {'u1': 'DONE'}
checkpoints: ['deliverable-ready', 'stopped', 'unit-green', 'heartbeat']
checker calls: ['true', 'echo done']
```

`main()` catches this as a refusal (tools/bm_controller.py:3154 to 3162), so the
founder sees "bm_controller: refused: run ... is STOPPED" and exit 1 from a move
they never asked for. Worse, `record_checkpoint(deliverable-ready)` (2299 to
2301) already committed, so the audit trail now carries a deliverable-ready
checkpoint written after the stop.

---

## F8 (MEDIUM, CONFIRMED): one wave, a dirty rollback and an outage, and the refusal escapes step()

`_handle_worker_result`'s outage branch is the only `set_run_state` in the wave
loop with no guard of its own:

```
tools/bm_controller.py:1691            self.store.set_run_state(
tools/bm_controller.py:1692                run_id, "FAILED_RECOVERABLE", self.actor,
```

`FAILED_RECOVERABLE` is not legal from `FAILED_TERMINAL`
(tools/bm_store.py:2571), and `_reject`'s dirty-rollback branch can put the run
in FAILED_TERMINAL earlier in the SAME wave (tools/bm_controller.py:1824 to
1829). Probe `sm4/j1_mixed_wave_illegal_move.py`, both plan orders:

```
--- plan order ['u_bad', 'u_out'] ---
step RAISED OwnershipRefused: run '676cc1bf...' is FAILED_TERMINAL; moving it to FAILED_RECOVERABLE is not legal from there.
store state: FAILED_TERMINAL
units: {'u_bad': 'READY', 'u_out': 'DISPATCHED'}
fence u_bad  parked
fence u_out  active
open founder steps: 1

--- plan order ['u_out', 'u_bad'] ---
step returned: state=FAILED_TERMINAL reason=None
```

Reachability: `_handle_worker_result`'s "unavailable" and "malformed" branches
are unreachable through the shipped CLI, because `RecordIntentWorker.run`
always returns `"pending"` (tools/bm_controller.py:184 to 187). This needs an
embedded or SDK WorkerAdapter, hence MEDIUM. The second order also shows F3
again (reason None on a FAILED_TERMINAL run), and both orders leave u_out's
fence ACTIVE on a terminal run.

---

## F9 (MEDIUM, CONFIRMED): design 6.4's invariant still fails on the synchronous path

Design 6.4 closes SM I by adding `FAILED_RECOVERABLE: READY` to
`_RESULT_WALK_EDGES` (tools/bm_controller.py:229 to 231) and to
`_walk_to_executing` (1946). Both are on the RESULT paths. The synchronous wave
calls `_ensure_verifying` alone (1701, 1713), which acts only from EXECUTING
(1962 to 1965), so an outage earlier in the same wave leaves the run in
FAILED_RECOVERABLE and the next unit's result is judged from there.

Probe `sm4/a1_outage_shapes.py`, reading the run state from INSIDE the
CheckRunner (the only way to see the state the engine actually judged from):

```
--- C: mixed wave, plan order ['u_out', 'u_ok'] ---
summary state=FAILED_RECOVERABLE stop_reason=None dispatched=['u_out', 'u_ok'] completed=['u_ok']
store   state=FAILED_RECOVERABLE
unit statuses: {'u_out': 'DISPATCHED', 'u_ok': 'DONE'}
run state seen from INSIDE each check: [('check-u_ok', 'FAILED_RECOVERABLE')]

--- D: mixed wave, plan order ['u_ok', 'u_out'] ---
run state seen from INSIDE each check: [('check-u_ok', 'VERIFYING')]
```

Order decides it. In shape C `_settle_after_wave` also early-returns
(tools/bm_controller.py:1982 to 1984), so the wave never settles and the unit's
green is not followed by any delivery decision until the next pass. I found no
data loss in the shapes I drove: the next `step()` reverses FAILED_RECOVERABLE
to READY and the run converges. Same SDK-caller reachability caveat as F8.

---

## F10 (LOW, CONFIRMED): the BLOCKED view a late result writes on a terminal run never reverses

FIX-round4-controller-report 4.2 justifies the fourth `_reconcile_lane_blocks`
call site (tools/bm_controller.py:1109) with: "a late result can land on a run
no later `step()` will ever drive (a STOPPED one), so deriving the status here
rather than 'on the next wave' is what keeps the view from being permanently
stale; the same reconcile reverses it when the step above is resolved." The
second half does not hold, for the same reason the first half is true.

Probe `sm4/g1_late_result.py`, case d:

```
units before: {'u1': 'DISPATCHED', 'u2': 'DISPATCHED'}
units after : {'u1': 'BLOCKED', 'u2': 'DISPATCHED'}
open steps: [('build', 'unit u1 returned a result after the run ')]
after resolving, units: {'u1': 'BLOCKED', 'u2': 'DISPATCHED'} (nothing re-reconciles a STOPPED run: no step() will ever drive it)
```

Cosmetic on a terminal run, which is why this is LOW, but it is the one place
where round 4's "BLOCKED is a view, reconciled in both directions" is a one-way
door again.

---

## What STOOD, with the attempt counts

### S1: law L2, the one exit funnel (27 summaries, 9 scenario families)

`_finish` (tools/bm_controller.py:518 to 547) re-reads the run row at 546 on
every exit, and I found no exit that bypasses it: all sixteen `return`
statements in `step()` (647, 657, 668, 678, 681, 689, 703, 715, 718, 729, 762,
766, 771, 789, 791, 792) go through it. In every probe that printed both, the
summary's state equalled the store read taken immediately afterwards, including
the four outage shapes, the five F3 routes, the PAUSED matrix and the held
lifecycles. The `stop_reason` half of the same law is F3.

Exceptions mid-step do not produce a lying summary; they produce NO summary
(F7 and F8 both exit 1 through `main()`'s BMStoreError handler).

### S2: the PAUSED founder-only gate (8 entry points)

Probe `sm4/b1_paused_matrix.py` snapshots the run state, unit statuses, dispatch
statuses, fence states, human steps, interruptions and spend before and after
each entry point on a PAUSED run with two open dispatches:

```
step                   result=('PAUSED', 'FOUNDER_WAITING', [], 'the controller run is PAUSED; only bm-co')
                       wrote: NOTHING
run_to_completion      result=[('PAUSED', 'FOUNDER_WAITING')]
                       wrote: NOTHING
check_timeouts         result=[]
                       wrote: NOTHING
plan (drop u2)         raised OwnershipRefused: controller run '...' is PAUSED, so plan is refused
                       wrote: NOTHING
receive_result         result='held'
                       wrote: {'units': ... 'u1': 'RESULT_IN' ..., 'dispatches': ... 'RESULT_IN' ..., 'spend': (0, 9000)}
stop                   wrote: {'state': ('PAUSED', 'STOPPED'), 'fences': (active, active) -> (parked, parked)}
begin (second)         raised OwnershipRefused: project 'p1' already has a non-terminal run
check_timeouts (expired) result=[]
                       wrote: NOTHING
```

No path dispatched, judged, verified, delivered or abandoned. I also traced
every `set_run_state` call in the file (21 of them, grepped) and confirmed that
none can leave PAUSED: `_walk_to_executing` (1946) does not list PAUSED,
`_ensure_verifying` and `_settle_after_wave` act only from EXECUTING/VERIFYING/
CHECKPOINTED, `_unwind_empty_wave` only from EXECUTING, `_handle_no_ready_units`
only from READY/CHECKPOINTED, `_deliver_or_hold` is bounded by
`_DELIVERY_SOURCE_STATES`, `_reject`'s FAILED_TERMINAL is guarded by the store's
own table, and `plan` is refused. Only `stop` leaves PAUSED, which is a founder
action.

F2 is not a hole in this gate. The gate holds; what fails is what happens after
the founder leaves it.

### S3: the orchestrator's third ruling, FAILED_RECOVERABLE in s1 (4 shapes)

Probe `sm4/a1_outage_shapes.py`:

```
--- A: single unit, unavailable on wave 1 ---
summary state=FAILED_RECOVERABLE stop_reason=OUTAGE
store   state=FAILED_RECOVERABLE          AGREE: True
--- B: single unit, unavailable on wave 2 (re-await route) ---
wave2 summary state=FAILED_RECOVERABLE stop_reason=OUTAGE
wave2 store   state=FAILED_RECOVERABLE   AGREE: True
--- C: mixed wave ['u_out', 'u_ok'] ---   AGREE: True (state FAILED_RECOVERABLE)
--- D: mixed wave ['u_ok', 'u_out'] ---   AGREE: True (state FAILED_RECOVERABLE)
```

The orchestrator's ruling on collision 3 is correct in all four shapes:
`FAILED_RECOVERABLE` is what the store holds when `step()` returns, so the
one-line remedy `self.assertEqual(s1["state"], "FAILED_RECOVERABLE")` pins the
truth. Note that in the mixed shapes the reason is None, not OUTAGE (a unit
recorded something, so `any_recorded` wins at tools/bm_controller.py:787); that
is defensible and is not F3, because the wave did make progress.

### S4 and S5: the late-result handler (SM C and SM D)

Probe `sm4/g1_late_result.py`:

```
--- a: late result on a STOPPED run, live contract ---
spend before: 0 ... spend after: 9000
founder (steps, interruptions): (0, 0) -> (1, 1)
--- b: STOPPED run, contract REVOKED ---
spend after: 0 (the live-contract guard skips it)
founder after: (1, 0)
--- c: late result AT the retry ceiling, contract revoked ---
founder before: (0, 0) -> founder after: (1, 0)
unit status=FAILED retry_count=1
  step [lane 'default']: unit u1 returned a result after the run reached STOPPED. ...
```

SM C (`tokens 0 -> 0`) and SM D (`before=(0, 0) after=(0, 0)`) are both closed on
the routes the reports name. Case (e) also shows that a unit declared with
`lane=""` is stored as `default` (tools/bm_store.py:13100), so the empty-lane
hole I went looking for does not exist.

### S6: FAILED_RECOVERABLE through its legal edge, on the asynchronous paths

Probe `sm4/e1_failed_recoverable_contexts.py`:

```
--- a: receive_result on a FAILED_RECOVERABLE run ---
run state now: CHECKPOINTED
state seen from inside each check: [('check-u1', 'VERIFYING')]
--- b: check_timeouts on a FAILED_RECOVERABLE run ---
check_timeouts -> ['u1', 'u2']   run state now: READY   dispatches: REJECTED, REJECTED
--- c: step() with the worker back ---
state seen from inside each check: [('check-u1', 'VERIFYING'), ('echo done', 'CHECKPOINTED')]
units: {'u1': 'DONE'}
```

Design 6.4's row is real on both asynchronous paths. F9 is the one context it
does not cover. Note that `check_timeouts` now walks a FAILED_RECOVERABLE run
all the way out of the fault state, which is new behaviour (it inherits
`_walk_to_executing`'s new FAILED_RECOVERABLE clause) and which design 11.1
describes as "the walk untouched"; I could construct no damage from it.

### S7: the rest of the held lifecycle

Probe `sm4/b2_held_lifecycle.py`:

```
--- b: held TWICE (same dispatch) ---
second raised OwnershipRefused: dispatch '...' is RESULT_IN, not DISPATCHED; a result was already recorded for it
spend tokens: 100 (double charge would be 200)
--- c: two units held, then resume ---
step1 completed=['u1'] ; step2 completed=['u2'] ; both DONE, both fences complete
--- e: held, resume, re-plan DROPS the unit ---
re-plan result: {'count': 1, 'skipped': ['u1'], 'cancelled_dispatches': ['8c9160...'], 'orphaned_fences': [('u1', '045b05...')]}
u1 dispatches: ['CANCELLED'] ; u1 fence parked ; u1 SKIPPED
--- f: held, then founder stop ---
state=STOPPED units={'u1': 'RESULT_IN'} fences=[('u1', 'parked')]
```

At-most-once recording, the spend rule, the drop-cancels-the-dispatch chain and
the fence parking all hold. Case (f) leaves a RESULT_IN dispatch row open on a
STOPPED run forever, which `cmd_status` will keep displaying as "record a result
for each"; harmless (the run is terminal and `record_result` refuses) but untidy.

---

## Attempts log

Seventeen probe scripts, run against the current working tree, each with its own
throwaway store. New-idea rounds: three. The third round produced F7 and F8 and
one new observation; a fourth round of ideas (listed at the end of this section)
produced nothing new, which is where I stopped.

| Probe | Attack | Outcome |
|---|---|---|
| `a1_outage_shapes.py` | the third ruling, 4 outage shapes, plus the state seen from inside the checker | S3 stands, F9 found |
| `b1_paused_matrix.py` | 8 entry points against a PAUSED run, full before/after snapshot | S2 stands |
| `b2_held_lifecycle.py` | held then resume, held twice, held then revoke, held then re-plan, held then stop, held then supersede | S7 stands, first sighting of F3 |
| `c1_mid_wave_drain.py` | a revoke landing between two gate_checks of one wave | F6 |
| `c2_verifying_wedge.py` | a crash between mark_unit_done and the settle | F4 |
| `d1_cli_held_pause.py` | the held lifecycle through 10 real CLI subprocesses | F2, and F3 seen by a founder |
| `d2_why_held_dies.py` | the mechanism, and the resume-the-contract-first control | F2 confirmed under both orderings |
| `e1_failed_recoverable_contexts.py` | FAILED_RECOVERABLE under receive_result, check_timeouts and step | S6 stands |
| `f1_reason_vs_store.py` | five step() exits, reason against the store | F3 |
| `f2_founder_gated_lost.py` | founder_gated on the delivering step | F3, second half |
| `g1_late_result.py` | SM C, SM D, the manufactured status, the empty lane | S4, S5 stand; F10 |
| `h1_replan_redefines_inflight.py` | a re-plan redefining a unit while the run is EXECUTING | refused cleanly, NO finding |
| `h2_replan_redefines_open_unit.py` | the same from CHECKPOINTED, one engine object | orphan fence found, masked by the same-session reclaim |
| `h3_replan_fresh_engine.py` | the same with a fresh engine per command | F1 |
| `h4_cli_replan_contention.py` | the same through real CLI subprocesses | F1 confirmed end to end |
| `i1_stop_during_done_definition.py` | a founder stop inside the done-definition window | F7 |
| `j1_mixed_wave_illegal_move.py` | a dirty rollback and an outage in one wave, both orders | F8 |

Ideas attacked that produced NOTHING (no finding, stated so they are not
re-attacked blind):

* Two units answering "unavailable" in one wave: `set_run_state` is idempotent
  on a same-state move (tools/bm_store.py:12864 to 12866), so no refusal.
* A `stop_reason` of TERMINAL on a non-terminal run: every TERMINAL exit is
  preceded by `_begin_stopping`, which ends at STOPPED.
* A `stop_reason` of DELIVERED on a non-delivered run: `_deliver_or_hold` writes
  it only after the DELIVERABLE_READY move or from the already-delivered branch.
* A second open dispatch for one unit: `_resume_dispatched` always runs before
  `select_ready_units`, so a unit with an open dispatch never reaches the fresh
  route, and `UNIQUE(unit_id, attempt)` backs it up.
* `_unwind_empty_wave` running twice, or on a run with a CLAIMED unit: idempotent
  by its EXECUTING check, and the CLAIMED case is caught by the round-4 resume
  branch on the next pass.
* A DELIVERABLE_READY run with selectable units (the `_may_dispatch` park):
  unreachable, because delivery requires every unit terminal and nothing turns a
  terminal unit selectable except a re-plan, which flips the run to READY.
* An empty `lane` on a unit: coerced to "default" by `upsert_units`.
* `_finish`'s ValueError guard: every writer of the field goes through
  `_set_reason` or `_finish`, both of which validate against `STOP_REASONS`.

---

## What I did NOT check

* **tools/test_all.py and the two suites were not run**, as instructed. I make
  no claim about the 99/839 counts in the two FIX reports.
* **The store half's own scope**: `path_within_allowed`, the glob matrix,
  `gate_check`'s no-raise change, `_spend_totals_from`, `release_claimed_unit`
  and `get_dispatch` were read where the controller touches them, and not
  attacked. That was the authorization lens's brief, not mine.
* **Round 3's behaviour was not executed.** Where I say round 4 changed an
  outcome (F4 in particular), the comparison is read from the current code and
  the round-3 reports, not from running round 3. Labelled unverified in place.
* **Two real operating-system processes against one store.** Every concurrency
  probe here is a single process with a delegating Store wrapper, exactly as the
  previous rounds' probes were. F6 and F7 are therefore reproduced as ordering,
  not as true parallelism.
* **The production worker's own behaviour.** F8 and F9 need a WorkerAdapter
  other than `RecordIntentWorker`, which I did not build beyond the fakes.
* **`bm_autonomy.py`'s own surface** beyond `sign`, `pause`, `resume`, `revoke`
  and `show`, which F2 and F6 needed.
* **The ast guard, the E4 artifact, docs/AUTONOMY.md's absence, and the three
  collisions' remedies as text.** The orchestrator's rulings on the paired block
  in TestFault8 and on retiring the DELIVERABLE_READY late-result test were
  taken as given; I only tested the third (S3), which holds.
* **Attribution rows, checkpoints and the dump surface** were sampled only where
  a probe printed them (F7's checkpoint ordering).
* **Performance**: `_open_dispatch_units` walks every unit and every dispatch of
  the run on every call, and it is now called from `step`, `check_timeouts`,
  `_resume_dispatched`, `_handle_no_ready_units` and `_anything_in_flight`. Not
  measured, not a correctness claim.
