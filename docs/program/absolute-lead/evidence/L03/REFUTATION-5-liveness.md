# REFUTATION 5, the LIVENESS, CORRECTNESS AND REGRESSION lens

**PUSH VERDICT: NO PUSH-BLOCKER.**

Nothing I found executes something the founder forbade, authorises a write
outside the contract, or destroys founder data. The one property that would
have blocked the push, the 3am kill switch actually stopping command
execution (AZ F5), I measured from the FILESYSTEM across four shipped-CLI
routes and it holds: zero commands ran. Nine findings below are disclosure
items. The most serious of them, LV5-F1, is a HIGH liveness defect that
leaves a project permanently un-runnable after the kill switch, and the
founder-facing sentence round 5 added tells the founder to perform a
recovery the shipped command line cannot perform.

Independent adversarial refuter, liveness and regression lens, against the
JUST-COMMITTED tree at local commit 5afc895 (not pushed) in
/Users/khalil.maaouni/Documents/BrotherModeUp. Read first, in full:
FIX-round5-controller-report.md, FIX-round5-store-report.md,
REFUTATION-4-authorization.md, REFUTATION-4-liveness.md, then
tools/bm_controller.py at every point this lens touches.

Every probe built its own Store under a fresh `tempfile.TemporaryDirectory()`,
or drove the shipped commands as real subprocesses against a throwaway
`BROTHERMODE_ROOT`, `BROTHERMODE_VAULT` and `HOME` inside another one. No
real `.brothermode` store was opened. `python3 tools/test_all.py` was NOT
run; every green line below is a single unittest class. No git command that
changes state was run.

Probe sources are in this session's scratchpad
(`r5probe/h.py`, `cli.py`, `p01` to `p13`), which is EPHEMERAL; every
reproduction below is written out with its verbatim output so this page
stands alone.

---

## VERDICT LINES

| ID | Verdict | Sev | One line |
|---|---|---|---|
| LV5-F1 | **STANDS** | HIGH | After the kill switch there is no way back. The founder step round 5 added says "Sign a fresh contract and re-plan to attempt it again"; `bm-controller plan` is refused from `STOPPED`, `bm-controller start` resumes the terminal run forever, and no shipped command opens a second run. `docs/FULL-AUTO.md` promises exactly this recovery in two places. |
| LV5-F2 | **STANDS** | MEDIUM | LV L4-F4 is half closed. Round 5 fixed the note on the open-dispatch route; the identical park on the SELECTABLE-UNITS route (bm_controller.py:995 to 1000) still names `resume`, `complete` and `stop`, and there is no open dispatch, so round 5's own remedy (`record-result`) is not available either. Parks forever. |
| LV5-F3 | **STANDS** | MEDIUM | The settle path's new `summary` out parameter is EMPTY on the wave that kills the run. `_settle_after_wave` returns at its third guard without writing anything, so `bm-controller record-result` on a failed rollback prints "the unit re-queues for one retry" (false) with no note and no reason, about a run that just reached `FAILED_TERMINAL`. |
| LV5-F4 | **STANDS** | MEDIUM | `_NOTE_CONTRACT_PAUSED` is issued from four sites where the run is NOT `PAUSED`. There `bm-controller resume`, the second of the two commands the note names, prints "Nothing to do." and the note never mentions the command that does move it. Reproduced through the shipped CLI. |
| LV5-F5 | **STANDS** | MEDIUM | Round 5's new `_validated_units` iterates `read_scope` with a bare `for entry in read_scope`. A `read_scope` emitted as a STRING is shredded character by character, stored, and handed to the worker in the brief as one-character paths. Nothing refuses it. |
| LV5-F6 | **STANDS** | LOW | `docs/FULL-AUTO.md`, a file round 5 wrote, still tells the founder a held result's meter is charged and that spend is charged "whether the result was accepted or not". Both are false on the shipped routes, as round 5's own report says. |
| LV5-F7 | **STANDS** | LOW | AZ F4's own defect returns above the 2000-row revision window. `Store.contract_revisions` returns the chain OLDEST first under a SQL LIMIT, so past 2000 revisions `_authorisation_moved` never sees the latest one, reports moved=True for a pause-and-resume, rejects the real answer, runs `git restore` and burns a retry. Reproduced with a control. |
| LV5-F8 | **STANDS** | LOW | FIX-round5-controller-report.md section 4 says `project_id=` is threaded through "EVERY store write this file makes ... no route into the store is left on the opt-out side of the guard". There are 50 guarded call sites, not 48; two of them (`cmd_resume`:3812, `cmd_complete`:3856) pass no `project_id`. Not exploitable today. |
| LV5-F9 | **STANDS** | LOW | The fourth orphan shape recovers SILENTLY: fence parked, a retry burned for a crash the unit did not cause, `stop_reason` None, zero founder steps and zero interruptions. The brief asked for each crash window to be named to the founder; this one is not. |
| AZ F7 | **CONFIRMED STILL OPEN** (round 5 discloses it) | MEDIUM | An ACTIVE fence over a still-READY unit parks the run on `CONTENTION` on every step forever, with zero founder steps. Round 5's new `_NOTE_CONTENTION` sentence tells the founder to "find the active claim over those files and release it" and names no command; no `bm-controller` command can even display that claim. |
| AZ F5 kill switch | **REFUTED (attempt failed)** | | Genuinely closed. Four shipped-CLI routes, marker measured on disk, zero executions. Independent AST audit: one `self.checker.run` site, six gated callers. |
| LV L4-F1 | **REFUTED for the shapes round 4 reported** | | The delivering wave now carries `DELIVERED` and the `founder_gated` block; the failing done-definition costs ONE execution, not two. Residue is LV5-F3 only. |
| LV L4-F2 | **REFUTED (attempt failed)** | | A contract-paused run reports `CONTRACT_PAUSED`, and following the note's two commands clears it in one step. No loop. |
| LV L4-F3 | **REFUTED (attempt failed)** | | An upstream founder-gated lane now reaches `WAITING_HUMAN` with `FOUNDER_WAITING` and a note naming the blocking lane and step text. |
| LV L4-F5 | **REFUTED (attempt failed)** | | The fourth orphan shape recovers: fence parked, unit re-queued, fresh dispatch. Silence is LV5-F9, not a wedge. |
| AZ F8 | **REFUTED (attempt failed)** | | Both the emptied fence and the taken-over fence are caught on the re-await, the dispatch closed and a fresh attempt opened. |
| AZ F6, AZ F9 | **REFUTED (attempt failed)** | | Every plan-time refusal I could construct leaves the run at `NEW` with nothing written, and a good re-plan drives it to `DELIVERABLE_READY`. |
| Spin class | **REFUTED (attempt failed)** | | Thirteen shapes driven at the default `max_steps=500`. Every one terminates in 3 steps or fewer. No shape spins. |

---

# THE FINDINGS

## LV5-F1 (HIGH). After the kill switch there is no way back, and the round-5 founder step names a recovery no shipped command can perform

### The defect

`_close_without_running`, new this round, queues this founder step
(tools/bm_controller.py:2373 to 2382), verbatim from the store:

```
unit u1 returned a result after the contract was stopped. Nothing was
executed for it: not its done_check, not its verifier and not its rollback,
so its write_scope is in whatever state the worker left it and needs manual
inspection. The result is recorded and rejected and the fence is parked.
Sign a fresh contract and re-plan to attempt it again, then resolve this
step.
```

The next `bm-controller step` drains the run to `STOPPED` (step 2's own
contract branch). From there:

* `bm-controller plan` is refused, because `upsert_units` always flips a run
  to `READY` and that move is not legal from a terminal state;
* `bm-controller start` calls `begin()` only when `Store.get_run` returns
  None (tools/bm_controller.py:3440 to 3442), and `Store.get_run` returns
  the MOST RECENT run for the project whatever state it is in
  (tools/bm_store.py:13801 to 13810), so it resumes the `STOPPED` row
  forever;
* `COMMANDS` (tools/bm_controller.py:3878 to 3887) is `start, step, plan,
  record-result, status, stop, resume, complete`. Nothing else calls
  `begin()`.

`Store.open_run` WOULD accept a second run (its `run-exists` guard exempts
`COMPLETE`, `STOPPED` and `FAILED_TERMINAL`), so the engine supports the
recovery and the command line cannot reach it.

The same dead end holds for `FAILED_TERMINAL` (see LV5-F3's reproduction,
where a failed rollback lands there) and for `COMPLETE`.

### The documentation promises exactly this recovery, twice

`docs/FULL-AUTO.md:86 to 88`:

> `STOPPING` then `STOPPED`: draining in flight work, then done for this
> run. Terminal once `STOPPED`; a fresh contract and a fresh run are what
> restart work, never a reopened `STOPPED` row.

`docs/FULL-AUTO.md:279`:

> re-planning or a fresh run is what attempts the unit again.

### Reproduction, the shipped CLI, real subprocesses

`p02_cli_killswitch_recovery.py`, verbatim:

```
$ bm-controller step --project p1
  | run 974052ce...: state EXECUTING
  | note: waiting for 1 open dispatch(es); record a result with bm-controller record-result
  | reason: IN_FLIGHT
open_dispatches from status: {'u1': 'd4fd774dd81b4db08d42187114ad445d'}

=== the 3am kill switch ===
$ bm-autonomy stop --project p1
  | project p1 contract -> stopped (revision 2)

=== the worker's answer arrives ===
$ bm-controller record-result --project p1 --dispatch-id d4fd774d...
  | dispatch d4fd774d... rejected; the unit re-queues for one retry or escalates, per the circuit breaker
  | note: the contract is stopped, not live: nothing is authorised, so the result was recorded and rejected and NO command was executed (no done_check, no verifier, no rollback). The fence is parked and a founder step names the unit
  | reason: CONTRACT_NOT_LIVE

=== one more step (the drain) ===
$ bm-controller step --project p1
  | run 974052ce...: state STOPPED
  | note: draining: contract is stopped
  | reason: TERMINAL

=== the founder does EXACTLY what that step says ===
$ bm-autonomy sign --project p1 --supersede
  | signed contract for project p1: revision 3 (live, sign)
$ bm-controller plan --project p1 --units-file units.json
  ! bm_controller: refused: run '974052ce...' is STOPPED; upsert_units always flips a run to READY, but that move is not legal from there. Legal moves from STOPPED: (none, terminal).
  rc=1
$ bm-controller start --project p1
  | project p1: run 974052ce..., 1 step(s), now STOPPED
  | note: run is terminal; nothing to do
  | reason: TERMINAL
$ bm-controller step --project p1
  | run 974052ce...: state STOPPED
  | note: run is terminal; nothing to do
  | reason: TERMINAL

final run state: STOPPED
final units: []
```

### Why this is not a push blocker

Nothing forbidden runs, nothing is authorised outside the contract, and no
founder data is destroyed: the run, its units, its dispatches, its
attribution trail and the founder step all persist and are readable. What is
lost is the ability to start NEW autonomous work on that project through the
shipped commands. It is a HIGH liveness defect and a disclosure item, and
the smallest honest fix is either a `bm-controller begin` command or one
condition in `cmd_start` (`if run is None or run["state"] in
_TERMINAL_STATES: begin()`), plus correcting the founder step's sentence if
neither lands.

---

## LV5-F2 (MEDIUM). L4-F4 is closed on one route and open on the next one down

### The defect

Round 5 replaced the three-command note on the OPEN DISPATCH route with
`_NOTE_DISPATCH_OPEN_UNMOVABLE`, which names `record-result` and the actual
dispatch id. The park one branch later, in `step()` itself, was not touched
(tools/bm_controller.py:995 to 1000):

```python
        state_now = self.store.get_run(project_id, raw=True)["state"]
        if not self._may_dispatch(state_now):
            return self._finish(
                summary, project_id, "FOUNDER_WAITING",
                "%d unit(s) are selectable but the run is %s, which only a "
                "founder can move (bm-controller resume, complete or stop)"
                % (len(ready), state_now))
```

On this route there is NO open dispatch, so `record-result`, round 5's own
remedy for the sibling branch, does not exist either. `_deliver_or_hold`
carries a third copy of the same sentence at 3005 to 3007.

### Reproduction

`p09_verifying_wedge_selectable.py`. Two units both declaring `a.py`, so
wave 1 dispatches one and defers the other on the fence overlap, leaving it
READY. The crash is the process dying between the `VERIFYING` write inside
`_handle_worker_result` and the settle that would have followed, which is
the same two-transaction boundary `_settle_after_wave` itself has at
tools/bm_controller.py:2603 and 2608. A FRESH engine is then built against
the SAME store.

```
constructed: run=VERIFYING units=[('u1', 'DONE'), ('u2', 'READY')] open_dispatches=0 selectable=1
  step 0                 state=VERIFYING          reason=FOUNDER_WAITING      note='1 unit(s) are selectable but the run is VERIFYING, which only a founder can move (bm-contr'
  step 1                 state=VERIFYING          reason=FOUNDER_WAITING      note='1 unit(s) are selectable but the run is VERIFYING, which only a founder can move (bm-contr'
  step 2                 state=VERIFYING          reason=FOUNDER_WAITING      note='1 unit(s) are selectable but the run is VERIFYING, which only a founder can move (bm-contr'
  step 3                 state=VERIFYING          reason=FOUNDER_WAITING      note='1 unit(s) are selectable but the run is VERIFYING, which only a founder can move (bm-contr'

   full note: '1 unit(s) are selectable but the run is VERIFYING, which only a founder can move (bm-controller resume, complete or stop)'

-- what each command that note names actually does --
   run is VERIFYING
   bm-controller resume : cmd_resume prints 'is already VERIFYING, not PAUSED. Nothing to do.' and exits 0
   bm-controller complete: REFUSED: run 'b5bfc730...' is VERIFYING; moving it to COMPLETE is not legal from there. Legal moves from VERIFYING: CHECKPOINTED, READY, STOPPING, P
   bm-controller record-result: 0 open dispatch(es) to record
   bm-controller stop   : destroys a run whose remaining unit is one wave from done
   open founder steps   : 0
   units                : [('u1', 'DONE'), ('u2', 'READY')]
```

Severity MEDIUM for the same reason round 4 gave L4-F4 MEDIUM: it needs a
crash at a named two-statement boundary. The damage is round 4's verbatim,
one branch later.

---

## LV5-F3 (MEDIUM). The new settle out parameter is empty on exactly the wave that kills the run

### The defect

`_settle_after_wave` now takes the caller's own summary, which is the L4-F1
fix. Its third guard returns without writing anything into it
(tools/bm_controller.py:2611 to 2613):

```python
        run = self.store.get_run(project_id, raw=True)
        if run["state"] != "CHECKPOINTED":
            return  # PAUSED/STOPPING/FAILED_* already claimed this run
```

A wave whose rejection walked the run to `FAILED_TERMINAL` (fault 10, a
rollback that itself failed) lands exactly there, so `stop_reason` stays
None and whatever note the caller was already carrying survives untouched.

### Reproduction A, the PRODUCTION route (`record-result`)

`p04_record_result_terminal.py`:

```
== record-result on a wave that ends FAILED_TERMINAL ==
   outcome            : rejected
   settled out-param  : {}
   run state          : FAILED_TERMINAL
   unit               : READY
   checker calls      : ['unit-done-check', 'git restore -- a.py']
   what the shipped CLI would print:
     dispatch 422a9a63... rejected; the unit re-queues for one retry or escalates, per the circuit breaker
     note:   (not printed)
     reason: (not printed)
   founder steps queued:
     lane='default' what='the rollback command for unit u1 failed (exit 128); its write_scope may be left dirty and needs manual inspection before any further work in that scope'

   is the run recoverable? next step():
  step                   state=FAILED_TERMINAL    reason=TERMINAL             note='run is terminal; nothing to do'
```

The one line the founder gets, "the unit re-queues for one retry or
escalates, per the circuit breaker", is FALSE: the run is `FAILED_TERMINAL`
and no later step will ever attempt that unit. The dirty write scope is
recorded (correctly) as a founder step, but the command that just caused it
says nothing about the run having died, which is the exact founder-facing
gap L4-F1 named.

### Reproduction B, the synchronous route (`step`)

`p01_settle_early_return.py`:

```
== fault-10 wave (rollback fails) ==
  step 0                 state=FAILED_TERMINAL    reason=None                 note='no spend ceiling on file (no-data); starting units and saying so'
   summary keys: ['completed', 'dispatched', 'note', 'run_id', 'state', 'stop_reason']
   store run state: FAILED_TERMINAL
   unit: READY
   checker calls: ['unit-done-check', 'git restore -- a.py']
   stop_reason IS None: True
   note is the spend-ceiling note: True
```

`stop_reason` is None on a wave that reached a terminal state, and the note
is stale prose from step 3 of the same wave. This is L4-F1's own shape,
surviving on the settle path's early return. It does not spin, because
`_loop_stops`' second clause catches the terminal state, which is what that
clause's own docstring calls "belt and braces, never the primary test".

---

## LV5-F4 (MEDIUM). The contract-paused note is issued from four places where the run is not paused, and there its second command does nothing

### The defect

`_NOTE_CONTRACT_PAUSED` ends "Clear the contract first with bm-autonomy
resume, then bm-controller resume this run". `cmd_resume`
(tools/bm_controller.py:3806 to 3810) returns 0 and prints "Nothing to do."
for any run that is not `PAUSED`. Six sites issue the note; only two of them
are looking at a `PAUSED` run:

| Site | Line | Run state when issued | `bm-controller resume` there |
|---|---|---|---|
| `step()` PAUSED guard | 908 to 910 | PAUSED | correct |
| `step()` step 2 | 939 to 944 | PAUSED (written one line earlier) | correct |
| `receive_result` held branch | 1266 to 1268 | whatever it was, EXECUTING on the shipped route | no-op |
| `_close_without_running` paused branch | 2352 to 2356 | VERIFYING | no-op |
| `_settle_after_wave` paused branch | 2621 to 2623 | CHECKPOINTED | no-op |
| `_deliver_or_hold` paused branch | 2992 to 2994 | READY or CHECKPOINTED | no-op |

### Reproduction, the shipped CLI

`p06_cli_pause_note.py`:

```
run state before the pause: EXECUTING

$ bm-autonomy pause --project p1 --reason "founder pause"
  | project p1 contract -> paused (revision 2)

$ bm-controller record-result --project p1 --dispatch-id c24efdf1... --tokens 9 --minutes 3
  | dispatch c24efdf1... recorded and HELD: nothing was judged, no rollback ran and the fence is still held
  | note: the CONTRACT is paused, and that is what pauses this run; bm-controller resume alone cannot clear it, because the next step re-reads the contract and pauses the run again. Clear the contract first with bm-autonomy resume, then bm-controller resume this run
  | reason: CONTRACT_PAUSED
spend after the HELD result: {"minutes": 0, ..., "tokens": 0, "verdict": "ok"}

--- the founder does EXACTLY what that note says ---
$ bm-autonomy resume --project p1 --reason "founder resume"
  | project p1 contract -> live (revision 3)
$ bm-controller resume --project p1
  | project p1 controller run ffea598a... is already EXECUTING, not PAUSED. Nothing to do.
run state after following the whole note: EXECUTING
units: {'RESULT_IN': 1}

--- and only a further `step`, which the note never mentions, moves it ---
$ bm-controller step --project p1
  | run ffea598a...: state DELIVERABLE_READY
  | completed: u1
  | note: deliverable ready
  | reason: DELIVERED
```

The run does terminate, and I proved it terminates rather than loops, which
is what the brief asked. What is wrong is narrower and still real: the
founder follows the whole instruction, is told "Nothing to do", and is left
with a run that has not moved and no instruction that would move it. This is
the class round 5 closed for L4-F2 and L4-F4, reopened by round 5's own new
note. The same probe run also shows two smaller things: `bm-autonomy resume`
requires `--reason`, which the note does not mention (a founder following it
literally gets a usage error and exit 2), and the meter (LV5-F6).

The in-process cross-check of the settle site, `p03_notes_and_meter.py`
part C:

```
== C. every state a CONTRACT_PAUSED note is issued from ==
  step 0                 state=CHECKPOINTED       reason=CONTRACT_PAUSED      note='the CONTRACT is paused, and that is what pauses this run; bm-controller resume alone canno'
   store run state: CHECKPOINTED
   unit: RESULT_IN
   checker calls: []
```

---

## LV5-F5 (MEDIUM). A string read_scope is shredded into one-character paths and handed to the worker

### The defect

`_validated_units`, new this round (tools/bm_controller.py:858 to 865):

```python
            read_scope = unit.get("read_scope")
            if read_scope:
                canonical = [
                    bs.canonicalize_path(
                        self.store.root, bs._coerce_path_entry(entry))
                    for entry in read_scope]
```

`for entry in read_scope` over a STRING iterates characters. In full auto
the read scope is model authored, and a single-path scope emitted as a bare
string rather than a one-element list is an ordinary malformed-output shape.
Nothing refuses it: each character is coerced, canonicalised, stored, and
handed to the worker in the brief.

### Reproduction

`p11_read_scope_string.py`:

```
read_scope='a.py'    stored=['a', '.', 'p', 'y']                     brief read_scope=['a', '.', 'p', 'y']
read_scope='src'     stored=['s', 'r', 'c']                          brief read_scope=['s', 'r', 'c']
read_scope='README'  stored=['R', 'E', 'A', 'D', 'M', 'E']           brief read_scope=['R', 'E', 'A', 'D', 'M', 'E']
```

A string that happens to contain a slash refuses instead, with a message
naming a path the founder never wrote. `p05_validated_units.py` part A:

```
== A. read_scope='src/app' (a string, not a list) ==
   plan refused: OwnershipRefused path '/' resolves outside the project root /private/var/folders/.../tmp7o5vlnzj
   -- the same value straight into Store.upsert_units (engine bypassed) --
   store ACCEPTED it. stored read_scope = src/app
```

So the coercion is new this round: the store still stores the string as
given, and it is the engine's new pre-pass that turns it into characters. A
dict is coerced the same way, silently, into its keys
(`p05_validated_units.py` part B: `read_scope={'a.py': 1}` is accepted and
stored as `['a.py']`).

This is not an authorisation hole: `read_scope` is a READ boundary and is
deliberately not gate-checked, which is unchanged and correct. It is a
correctness defect in a brief the model then acts on. I score it MEDIUM
rather than HIGH because it needs the orchestrating model to emit a
non-list `read_scope`, and every unit graph in this repository's own
fixtures uses a list; by the brief's literal reachability rule ("reachable
from shipped CLI") it would be HIGH, and I am naming that so the scoring is
not hidden. One line closes it: refuse a non-list `read_scope` in
`_validated_units`, the way the unit id is refused four lines above.

---

## LV5-F6 (LOW). docs/FULL-AUTO.md still tells the founder the meter is charged

`docs/FULL-AUTO.md:81 to 83`, a file this round wrote:

> A result that arrives during a pause is RECORDED AND HELD, never rejected:
> the answer is durable and the meter is charged, but nothing is judged and
> no rollback command touches your files

and `docs/FULL-AUTO.md:280 to 281`, about a rejected late result:

> Spend is charged for the work that really happened, whether the result was
> accepted or not.

Both are false on the shipped routes, and FIX-round5-controller-report.md
section 3 says so in its own words ("the charge cannot be made at the moment
the answer is held"). Measured, `p03_notes_and_meter.py`:

```
== B. the HELD route: is the meter charged? ==
   receive_result -> held
   summary reason: CONTRACT_PAUSED
   spend before: {'tokens': 0, 'minutes': 0}
   spend after : {'tokens': 0, 'minutes': 0}
   docs/FULL-AUTO.md claim 'the meter is charged' holds: False

== A. the CONTRACT_NOT_LIVE founder step, unredacted ==
   receive_result -> rejected
   spend: {'tokens': 0, 'minutes': 0, ..., 'verdict': 'no-data'}
```

and through the shipped CLI, `p06_cli_pause_note.py` with `--tokens 9
--minutes 3`: `spend after the HELD result: {"minutes": 0, ..., "tokens": 0}`.

`docs/FULL-AUTO.md:83 to 85` ("`bm-controller resume` plus one `step` then
verifies the held answer") is inaccurate for the same reason as LV5-F4: on
the only route the shipped CLI has to a hold, `bm-controller resume` is a
no-op and the `step` alone is what verifies it.

The behaviour is disclosed in `docs/KNOWN-LIMITS.md` and in the round-5
report. The founder-facing page that contradicts them is the defect.

---

## LV5-F7 (LOW). AZ F4's defect returns above the 2000-row revision window

### The defect

`_authorisation_moved` (tools/bm_controller.py:660 to 671) reads
`self.store.contract_revisions(project_id, limit=2000, raw=True)` and, if it
never sees the latest revision in those rows, returns moved=True. The
docstring calls that "conservative on doubt". `Store.contract_revisions`
(tools/bm_store.py:12603 to 12608) returns the chain **OLDEST first** under a
SQL `LIMIT`, so for any chain longer than the window the LATEST revision is
never in it, and the doubt becomes permanent rather than conservative.

### Reproduction, with a control

`p10b_revision_window.py`. One thousand pause-and-resume pairs, none of
which changes any authorisation column, then a dispatch, then one more
pause-and-resume:

```
dispatch stamped at revision: 2001
latest revision: 2003   window returns 2000 rows, 1..2000
_authorisation_moved -> moved=True latest=2003
receive_result -> rejected
unit u1: READY retry 1
commands executed: ['true', 'git restore -- a.py']
dispatch ddd2f20c status=REJECTED

-- the CONTROL: the identical sequence on a SHORT chain --
_authorisation_moved -> moved=False latest=3
receive_result -> u1
unit u1: DONE retry 0
commands executed: ['true', 'echo done']
```

Above the boundary the founder's real answer is destroyed, `git restore`
runs over their files and a retry is burned, which is AZ F4's damage
verbatim. Below it, round 5's fix works. Two thousand contract revisions is
a lot of founder actions, so LOW and exotic, but the boundary is silent and
one-way: once a project crosses it, no unit whose contract revision is not
the very latest can ever be accepted again.

---

## LV5-F8 (LOW). The project_id threading claim is off by two

FIX-round5-controller-report.md section 4 states: "Every store write this
file makes now passes `project_id=`, 48 call sites across all eleven guarded
entry points ... the keyword is threaded through EVERY store write this file
makes, not only this command's, so a route left without it is a route on the
opt-out side of the check."

Counted by AST over the eleven guarded entry points named in
FIX-round5-store-report.md section 2:

```
guarded store-write call sites in bm_controller.py: 50
WITH project_id=: 48   WITHOUT: 2
   line 3812  cmd_resume             set_run_state(...)  <-- no project_id=
   line 3856  cmd_complete           set_run_state(...)  <-- no project_id=
```

Neither is exploitable today: both derive `run["run_id"]` from
`store.get_run(project_id)` two lines earlier, so the run always belongs to
the project the founder named. The finding is that the claim "no route into
the store is left on the opt-out side of the guard" is false as written, and
those two commands have no guard if they are ever edited to take a run id.

---

## LV5-F9 (LOW). The fourth orphan shape recovers silently

The brief asked me to confirm each crash window is named to the founder
rather than parked forever. Three of the four recover; none of them is named
to the founder.

`p07_crash_windows.py`, the fourth orphan shape (`record_verification`
called directly, which is the first of the two calls in every one of the
five windows the round-5 report lists):

```
== W1. dispatch CLOSED, unit still DISPATCHED (the 4th shape) ==
   constructed: unit=DISPATCHED dispatch=REJECTED fence=active
  step 0                 state=EXECUTING          reason=None                 note='recovered a unit stranded behind a closed dispatch and parked the fence it still held'
  step 1                 state=EXECUTING          reason=IN_FLIGHT            note='waiting for 1 open dispatch(es); record a result with bm-controller record-result'
      unit u1 : DISPATCHED retry 1 fence_uuid True
      open founder steps: 0 []
```

The recovery is real (fence parked, unit re-queued, fresh attempt), and it
costs the unit a retry for a crash it did not cause, which round 5 argues
for deliberately. What is missing is any durable founder-facing record: no
`queue_human_step`, no `_record_interruption`, and `stop_reason` None, so a
loop driver walks straight past the one note that mentions it. A founder
reading `bm-controller status` afterwards sees a unit at `retry_count` 1
with no reason recorded anywhere.

The same silence applies to the two fence shapes:

```
== W3. fence EMPTIED under an open dispatch (AZ F8) ==
   constructed: fence state=active files=[] owner=ctrl1
  step 0                 state=EXECUTING          reason=None                 note="the fence this unit's dispatch held no longer holds its files (it was released, emptied or"
      unit u1 : DISPATCHED retry 1 fence_uuid True
      open founder steps: 0 []
      worker re-asked? {'u1': 3}

== W4. fence ADOPTED by another owner under an open dispatch ==
   constructed: fence state=active owner=other-controller files=['a.py']
  step 0                 state=EXECUTING          reason=None                 note="the fence this unit's dispatch held no longer holds its files (it was released, emptied or"
      unit u1 : DISPATCHED retry 1 fence_uuid True
      open founder steps: 0 []
```

Both recover, which refutes AZ F8. One observation on the wording: the
`_resume_dispatched` note is the same generic sentence for all four fence
problems, so the specific phrase `_fence_no_longer_holds` computes ("it no
longer exists", "it is parked, not active", "it is now held by X", "it no
longer holds a.py") reaches the verification text and the failure reason but
never the founder's note.

---

## AZ F7 CONFIRMED STILL OPEN. An active fence over a READY unit parks the run forever

Round 5's report section 8 states this is not closed. Confirmed, with the
damage measured. `p07_crash_windows.py`:

```
== W2. fence CLAIMED, unit not (AZ F7, reported NOT closed) ==
   constructed: unit=READY fence=active owner=someone-else files=['a.py']
  step 0                 state=CHECKPOINTED       reason=CONTENTION           note="another writer holds a fence over this unit's files, or the contract was amended twice whi"
  step 1                 state=CHECKPOINTED       reason=CONTENTION           note=...
  step 2                 state=CHECKPOINTED       reason=CONTENTION           note=...
  step 3                 state=CHECKPOINTED       reason=CONTENTION           note=...
      unit u1 : READY retry 0 fence_uuid False
      open founder steps: 0 []
      run state: CHECKPOINTED
```

Round 5's AZ F12 half did land: `_NOTE_CONTENTION` now ends "If this repeats
on every step, the fence is held by a writer that is not coming back: find
the active claim over those files and release it". Two gaps remain, both
founder-facing:

* it names no command, and the brief's own rule for this round is that every
  note names a command that actually moves the run. The shipped way is
  `python3 tools/bm_store.py park <lifecycle_uuid>`;
* nothing in `bm-controller` can show the founder that claim.
  `cmd_status` (tools/bm_controller.py:3684 to 3691) lists open dispatches
  only for units whose OWN status is `DISPATCHED` or `RESULT_IN`, and lists
  no fences at all, so a foreign claim over a READY unit's files is
  invisible to every `bm-controller` command.

---

# THE ATTACKS THAT FAILED, WHICH IS WHERE ROUND 5 IS GENUINELY STRONG

## The kill switch (AZ F5), measured from the filesystem

The round-5 report proves this with a command tape. I measured it a
different way, so the two are independent: the unit's own model-authored
`done_check` is `touch KILLSWITCH-MARKER`, and I ask the filesystem whether
that file exists. Four shipped-CLI routes, real subprocesses, throwaway root.
`p13_cli_killswitch_execution.py`:

```
== record-result after `bm-autonomy stop` ==
   marker before: False
   marker AFTER : False
== step on a RESULT_IN dispatch after `bm-autonomy stop` ==
   marker before: False
   marker AFTER : False
== record-result after `bm-autonomy revoke` ==
   marker before: False
   marker AFTER : False
== step on a RESULT_IN dispatch after `bm-autonomy revoke` ==
   marker before: False
   marker AFTER : False

ROUTES THAT STILL EXECUTED A COMMAND: (none)
```

Structurally, my own AST audit of tools/bm_controller.py, independent of the
suite's guard:

```
  626    _run_command                     <-- the ONE self.checker.run site
  1445   _handle_late_result [gated caller]
  2254   _verify_and_finish  [gated caller]
  2285   _verify_and_finish  [gated caller]
  2295   _verify_and_finish  [gated caller]
  2424   _reject             [gated caller]
  3012   _deliver_or_hold    [gated caller]
```

Six gated callers, one gate. This is the property that would have blocked
the push, and it holds.

## L4-F1, L4-F2, L4-F3 re-measured against round 4's own numbers

`p08_round4_remeasured.py`, side by side with what REFUTATION-4-liveness.md
printed:

```
== L4-F1 reproduction A: the delivering wave's own verdict ==
  step 1 state=DELIVERABLE_READY  reason=DELIVERED   founder_gated={'human_steps': [], 'failed_units': ['u1']}
          note='deliverable ready'
  units: [('u1', 'FAILED'), ('u2', 'DONE')]
```
Round 4 had `reason=None`, `founder_gated=None` on that wave. FIXED.

```
== L4-F1 reproduction C: done_definition executions per run_to_completion ==
  steps: 1
   0 state=CHECKPOINTED     reason=FOUNDER_WAITING  note='final done-definition check failed (exit 3); the run stays in place fo'
  done_definition executions: 1
  all checker calls: ['true', 'final-suite']
```
Round 4 measured 2 steps and 2 executions of the founder's whole suite
(`['true', 'final-suite', 'final-suite']`). Now 1 and 1, which is design
9.1's own number. FIXED.

```
== L4-F3: an upstream founder-gated lane ==
  step 0 state=WAITING_HUMAN    reason=FOUNDER_WAITING    note='only founder-gated lanes remain; what blocks this run is 1 open founder step(s) in lane(s) build: the rollback'
  store run state: WAITING_HUMAN
```
Round 4 had `state=READY reason=NOTHING_SELECTABLE`. FIXED, enum and store
state together.

```
== L4-F2: a contract-paused run, in process ==
  step 0/1/2             state=PAUSED   reason=CONTRACT_PAUSED
  -- the founder follows the note: bm-autonomy resume, then bm-controller resume --
  after 0                state=DELIVERABLE_READY  reason=DELIVERED
```
Round 4's four-command loop is gone. FIXED, and this is the one shape where
following the note literally does clear the run, because there the run
really is `PAUSED` (contrast LV5-F4).

## The plan-time refusals leave no wedge

`p05_validated_units.py` part C, both new refusal kinds:

```
== C. a plan refusal, then a good re-plan ==
   {'unit_id': 'api/pay'}   refused OwnershipRefused: unit id 'api/pay' cannot be used: ...
      run state after refusal: NEW
      re-plan then drive -> DELIVERABLE_READY in 1 step(s)
   {'read_scope': ['../../e refused OwnershipRefused: path '../../etc' resolves outside the project root ...
      run state after refusal: NEW
      re-plan then drive -> DELIVERABLE_READY in 1 step(s)
```

Part D drove ten more unit-graph shapes that plan cleanly, hunting for one
where `step()` RAISES after the run has already been walked to `EXECUTING`
(AZ F6's wedge shape). None found:

```
   empty write_scope entry    plan refused: ValueError
   write_scope ['.']          drove to DELIVERABLE_READY    in 1 step(s)
   write_scope absolute /etc  plan refused: OwnershipRefused
   done_check None            drove to DELIVERABLE_READY    in 1 step(s)
   objective None             drove to DELIVERABLE_READY    in 1 step(s)
   lane empty                 drove to DELIVERABLE_READY    in 1 step(s)
   role None                  drove to DELIVERABLE_READY    in 1 step(s)
   unit_id 60 chars           drove to DELIVERABLE_READY    in 1 step(s)
   risk_class unknown         plan refused: ValueError
   write_scope 2 dupes        drove to DELIVERABLE_READY    in 1 step(s)
```

The two `plan refused` cases refuse from `PLANNING` rather than before the
walk, but `plan` is legal from `PLANNING`, so a re-plan recovers. Not a
wedge.

## No shape spins

`p12_spin_sweep.py`, every shape driven with the DEFAULT `max_steps=500`:

```
spin sweep, run_to_completion default max_steps=500
  happy path                             steps=1    final=DELIVERABLE_READY  reason=DELIVERED
  contract paused                        steps=1    final=PAUSED             reason=CONTRACT_PAUSED
  contract stopped                       steps=1    final=STOPPED            reason=TERMINAL
  contract revoked                       steps=1    final=STOPPED            reason=TERMINAL
  foreign fence (contention)             steps=1    final=CHECKPOINTED       reason=CONTENTION
  async park (production worker)         steps=1    final=EXECUTING          reason=IN_FLIGHT
  provider outage                        steps=1    final=FAILED_RECOVERABLE reason=OUTAGE
  failing done_definition                steps=1    final=CHECKPOINTED       reason=FOUNDER_WAITING
  gate_check refuses the only unit       steps=3    final=DELIVERABLE_READY  reason=DELIVERED
  soft spend stop                        steps=1    final=READY              reason=SPEND_STOP
  4th orphan shape                       steps=2    final=EXECUTING          reason=IN_FLIGHT
  VERIFYING + selectable unit            steps=1    final=VERIFYING          reason=FOUNDER_WAITING
  upstream founder-gated lane            steps=1    final=WAITING_HUMAN      reason=FOUNDER_WAITING
```

Three steps is the worst case. Round 4's own "loops forever" class is gone.

## Two structural claims re-checked by hand

```
tools/bm_controller.py            lines over 79 columns: 0    em or en dash lines: []
tools/test_bm_controller.py       lines over 79 columns: 24   em or en dash lines: []
docs/FULL-AUTO.md                 lines over 79 columns: 8    em or en dash lines: []
docs/KNOWN-LIMITS.md              lines over 79 columns: 111  em or en dash lines: []
FIX-round5-controller-report.md   lines over 79 columns: 32   em or en dash lines: []
```

The report claims 79 columns only for `tools/bm_controller.py`, and that
holds exactly. No em or en dash anywhere in any of the five.

Unit status `VERIFYING` is in `CONTROLLER_UNIT_STATES` and the fourth orphan
branch does not cover it, which looked like a fifth orphan shape. It is not:
no writer anywhere in tools/bm_store.py ever sets a unit to `VERIFYING`
(every `UPDATE controller_units SET status` site checked, lines 13235,
13338, 13377, 13476, 13527, 13581, 13647, 13728, 13789), so the value is
unreachable in production. Recorded as a miss, not a finding.

---

# REGRESSIONS: every class run on its own

`python3 -m unittest test_bm_controller.<class>` from
/Users/khalil.maaouni/Documents/BrotherModeUp/tools, one class per
invocation. `tools/test_all.py` was not run, as instructed.

**The ten fault tests plus the four originals most at risk:**

```
TestFault1KilledBetweenResultAndCommit                     Ran 1 test  OK
TestFault2DuplicateResult                                  Ran 1 test  OK
TestFault3DependencyChangedOutputInvalidatesEvidence       Ran 1 test  OK
TestFault4WorkerHangs                                      Ran 1 test  OK
TestFault5MalformedOutput                                  Ran 1 test  OK
TestFault6CostCeilingReached                               Ran 1 test  OK
TestFault7FounderCancelsDuringFanOut                       Ran 1 test  OK
TestFault8RestartWithNewerWorkflowVersion                  Ran 1 test  OK
TestFault9ProviderOutageThenRecovery                       Ran 1 test  OK
TestFault10RollbackItselfFails                             Ran 1 test  OK
TestExecutorCannotSelfApprove                              Ran 1 test  OK
TestRevokedContractMidUnit                                 Ran 1 test  OK
TestHumanBlockedLaneDoesNotStallIndependentLane            Ran 1 test  OK
TestDuplicateControllerAndStaleHeartbeatAdoption           Ran 2 tests OK
```

**Every refutation-born class, rounds 1 to 3, plus the structural guard and
the end-to-end fixture:**

```
TestF1AsyncRejectWhoseRollbackAlsoFails                    Ran 1 test   OK
TestF2EveryWriteScopePathIsGateChecked                     Ran 3 tests  OK
TestF3AsyncSpendAfterARevoke                               Ran 1 test   OK
TestF4DependentOfAFailedUnitDoesNotStallTheRun             Ran 2 tests  OK
TestR2F1LateResultOnARunStateThatCannotReachVerifying      Ran 3 tests  OK
TestR2F1CheckTimeoutsWalksTheSameStatesAsReceiveResult     Ran 2 tests  OK
TestR2F2TheRevisionEveryPathWasJudgedUnder                 Ran 3 tests  OK
TestR2F4DeadDependenciesAndFounderGatedLanes               Ran 4 tests  OK
TestR3PausedIsAFounderOnlyGate                             Ran 6 tests  OK
TestR3TheSummaryStateIsTheStoreState                       Ran 3 tests  OK
TestR3StopReasonDrivesEveryLoopDriver                      Ran 6 tests  OK
TestR3TheExecutingWedgeUnwinds                             Ran 2 tests  OK
TestR3TheSkippedLifecycleClosesAtTheSource                 Ran 5 tests  OK
TestR3BlockedIsAMaterialisedViewOfTheLaneGate              Ran 4 tests  OK
TestR3EveryDispatchRouteIsGateChecked                      Ran 4 tests  OK
TestR3ForeignAndCancelledDispatchIdsRefuse                 Ran 3 tests  OK
TestR3LateResultKeepsItsSpendAndItsFounderRecord           Ran 4 tests  OK
TestR3FailedRecoverableReachesVerifying                    Ran 2 tests  OK
TestR3TheClaimedCrashWindowRecovers                        Ran 2 tests  OK
TestNoSQLGuard                                             Ran 4 tests  OK
TestEndToEndE4                                             Ran 1 test   OK
```

**Every round-5 class, and the whole CLI section:**

```
TestR5NoCommandRunsUnderADeadContract                      Ran 3 tests  OK
TestR5TheHeldAnswerSurvivesAPausedContract                 Ran 3 tests  OK
TestR5AContractPauseIsNotARunPause                         Ran 3 tests  OK
TestR5AnUpstreamFounderGateIsFounderWaiting                Ran 2 tests  OK
TestR5TheSettlePathCarriesItsVerdict                       Ran 3 tests  OK
TestR5TheVerifyingParkNamesTheRealRecovery                 Ran 1 test   OK
TestR5TheFourthOrphanShapeRecovers                         Ran 1 test   OK
TestR5PlanRefusesAUnitIdTheFenceWouldRefuse                Ran 3 tests  OK
TestR5PlanRefusesAForeignRun                               Ran 2 tests  OK
TestR5ReadScopeIsCanonicalisedLikeWriteScope               Ran 2 tests  OK
TestR5TheReAwaitChecksTheFenceContentAndOwner              Ran 1 test   OK
TestR5FounderNotesStateWhatActuallyHappened                Ran 2 tests  OK
TestControllerCLIStartResumesWithNoDuplicateWork           Ran 1 test   OK
TestControllerCLIStatusReport                              Ran 3 tests  OK
TestControllerCLIStopDrains                                Ran 2 tests  OK
TestControllerCLIPauseAndResume                            Ran 2 tests  OK
TestControllerCLIComplete                                  Ran 1 test   OK
TestControllerCLIExitCodes                                 Ran 9 tests  OK
```

53 classes, every one green on its own. No behaviour change found in any
pre-round-5 class.

Two notes on the round-5 classes, because green is not the same as
sufficient. `TestR5TheVerifyingParkNamesTheRealRecovery` and
`TestR5TheFourthOrphanShapeRecovers` are one test each, and neither asserts
the founder-facing half LV5-F2 and LV5-F9 are about: the first pins the note
on the open-dispatch route and does not ask what happens on the
selectable-units route beside it, and the second pins the recovery and does
not ask whether anything names it to the founder.

---

# The E4 end-to-end fixture

**It still describes a real killed-and-resumed run.** Read in full
(tools/test_bm_controller.py:3411 to 3618): the engine object is genuinely
discarded and rebuilt against the same store between u3's failed attempt 1
and its attempt 2 (line 3531), `_dispatch_count(store, "u3") == 2` is
asserted ("never a third or a duplicate of either"), every unit ends DONE,
`duplicate_work_count` is 0, and the artifact is re-read from disk and
asserted against, so the file and the pass condition cannot diverge.

**Drift: none beyond four uuids.** After my run of that class, `git diff` on
the artifact is four `checkpoint_ref` uuid4 values and nothing else, exactly
as round 4 recorded:

```
 docs/program/absolute-lead/evidence/L03/E4-endtoend.json | 8 ++++----
 1 file changed, 4 insertions(+), 4 deletions(-)
```

`run_states_visited` is still
`[READY, READY, READY, READY, DELIVERABLE_READY, DELIVERABLE_READY]`,
`final_state` DELIVERABLE_READY, `duplicate_work_count` 0, four DONE units,
one open human step. The second DELIVERABLE_READY is the test's own
structure (it calls `run_to_completion` AFTER the delivering step), not the
extra wave round 4 diagnosed.

**Both of round 4's observations about it are unfixed and worth restating,
because this is the round's own end-to-end evidence:**

1. `founder_gated_remainder` is computed by the TEST from the store
   (tools/test_bm_controller.py:3597 to 3601: `len(open_steps)` and
   `open_steps[0]["blocks"]`), not from `summary["founder_gated"]`. So E4
   still does not exercise the engine block that LV L4-F1 was entirely
   about, while its name makes it look as though it does.
2. The artifact records no `stop_reason` at all. Round 5 added two new
   members to that enum (`CONTRACT_PAUSED`, `CONTRACT_NOT_LIVE`) and made the
   settle path carry the field; none of that has any end-to-end evidence in
   the round's own end-to-end artifact.

---

# Attempts

Twenty-four distinct attack ideas. Nine produced findings.

| # | Idea | Outcome |
|---|---|---|
| 1 | Follow the CONTRACT_NOT_LIVE founder step literally through shipped commands | HIT (LV5-F1) |
| 2 | Follow `_NOTE_CONTRACT_PAUSED` literally from each of its six issue sites | HIT (LV5-F4) |
| 3 | Does `_NOTE_DISPATCH_OPEN_UNMOVABLE`'s `record-result` really move a VERIFYING run | MISS, it does; but the sibling branch does not (LV5-F2) |
| 4 | Is `bm-controller status` really where the dispatch id comes from | MISS, `open_dispatches` carries it |
| 5 | A wave shape where `_settle_after_wave` writes nothing into the caller's summary | HIT (LV5-F3) |
| 6 | The same on the PRODUCTION route (`record-result`) | HIT (LV5-F3 reproduction A) |
| 7 | `receive_result`'s summary out parameter on the happy path | MISS, carries reason, note and founder_gated correctly |
| 8 | A wave that dispatches nothing | MISS, correct |
| 9 | The fourth orphan shape: does it recover, is it named | HIT on the naming (LV5-F9), MISS on recovery |
| 10 | Fence claimed but unit not | AZ F7 confirmed still open |
| 11 | Fence emptied under an open dispatch | MISS, recovers |
| 12 | Fence owner changed under an open dispatch | MISS, recovers |
| 13 | A unit graph that still wedges the run after plan succeeds (ten shapes) | MISS, none found |
| 14 | Do the new plan-time refusals leave the run re-plannable | MISS, they do |
| 15 | `read_scope` as a string, as a dict | HIT (LV5-F5) |
| 16 | A fifth orphan shape via unit status VERIFYING | MISS, unreachable, no writer sets it |
| 17 | Spin sweep, thirteen shapes at max_steps=500 | MISS, worst case 3 steps |
| 18 | The kill switch measured from the filesystem, four shipped routes | MISS, genuinely closed |
| 19 | Independent AST audit of every command site | MISS, one gate, six gated callers |
| 20 | The 2000-row revision window | HIT (LV5-F7) |
| 21 | `project_id=` threading, counted by AST | HIT (LV5-F8) |
| 22 | The report's 79-column and no-dash claims | MISS, both hold for the file they are claimed for |
| 23 | E4 drift, and whether it is still a killed-and-resumed run | MISS on drift, two round-4 observations restated |
| 24 | docs/FULL-AUTO.md against measured behaviour | HIT (LV5-F6) |

Ideas 13 to 24 produced four findings and eight misses; ideas 17 to 24
produced three findings and five misses, so I ran one further round (the
revision window, the VERIFYING unit status, the settle path's remaining
callers) which produced one further finding and two misses. That is the
stopping condition the brief sets.

---

# What I did NOT check, and what is only partly checked

* **`python3 tools/test_all.py`, `tools/test_bm_store.py`,
  `tools/test_bm_autonomy.py` and `tools/test_bm.py` were not run**, as
  instructed. Every green line above is a single class of
  `tools/test_bm_controller.py`. I make no claim about any class I did not
  name, and none about the store or autonomy suites.
* **The AUTHORISATION lens's surface**: glob containment,
  `path_within_allowed`, `gate_check`, `literal_scope_entry`,
  `_refuse_foreign_run`'s own correctness, the fence overlap semantics. I
  read them to follow control flow and attacked none of them. AZ F1's
  surviving allowance half and AZ F2's CLI half are the other lenses' to
  judge.
* **Two real operating-system processes against one store.** Every probe
  here is a single process. Every concurrency-shaped window stays
  unexplored.
* **A real process kill.** LV5-F2 was constructed by making one method call
  a no-op for one wave, which stands in for a process death between two
  store transactions, exactly as round 4 constructed L4-F4 and L4-F5. No
  process was killed.
* **`check_timeouts` under a real clock.** Still wired to no CLI subcommand,
  so in production nothing times a hung dispatch out. I drove the engine, not
  the timeout path. Its `_settle_after_wave` call inherits LV5-F3.
* **The store side of LV5-F7.** I did not check whether any other caller of
  `Store.contract_revisions` has the same window problem.
* **Whether LV5-F1 has ever bitten a real project.** Reachability is
  demonstrated; incidence is not.
* **Windows and Linux.** Everything ran on darwin, Python 3.9.6.
* **Performance.** Measured nothing.

# Disclosure: bytes I changed in the repository

Running `TestEndToEndE4` regenerates
`docs/program/absolute-lead/evidence/L03/E4-endtoend.json` by that class's
own documented design. The working tree was CLEAN at 5afc895 when I started
(`git status --short` printed nothing). It is now:

```
 M docs/program/absolute-lead/evidence/L03/E4-endtoend.json
?? docs/program/absolute-lead/DESIGN-insight-ledger-and-handback.md
```

The modification is mine and is the four `checkpoint_ref` uuid4 values and
nothing else. I did not restore the previous values, for the reason round 4
gave: doing so means writing bytes into a file I was not authorised to write
and discarding the last real run's evidence. **Before the push, decide
deliberately whether to commit the regenerated artifact or
`git checkout -- docs/program/absolute-lead/evidence/L03/E4-endtoend.json`;
either is fine, an unnoticed dirty tree at push time is not.**

The untracked `docs/program/absolute-lead/DESIGN-insight-ledger-and-handback.md`
is NOT mine. It appeared during this session and I did not write it or read
it. Somebody else's writer is live in this tree.
