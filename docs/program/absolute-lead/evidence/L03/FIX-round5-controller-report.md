# FIX round 5, the CONTROLLER half of the L03 hardening

Writer: the round-5 controller writer. Files written, and no others:
`tools/bm_controller.py`, `tools/test_bm_controller.py`, `docs/FULL-AUTO.md`,
`docs/KNOWN-LIMITS.md`, and under
`docs/program/absolute-lead/evidence/L03/`: this report and
`RED-round5-controller.txt`.

`tools/bm_store.py` and `tools/test_bm_store.py` were READ and never
written; the round-5 store writer owns both.
`docs/program/absolute-lead/evidence/L03/E4-endtoend.json` was regenerated
by `TestEndToEndE4`, which regenerates it on every run by that class's own
documented design; the only bytes that differ are four `checkpoint_ref`
uuid4 values.

Method: fail first. Every finding below got a test encoding the refuter's
own probe sequence, every one of those tests was captured failing against
the tree before any controller edit, and the captures are in
`RED-round5-controller.txt`. Existing tests were treated as law: one
collided, and the collision is recorded in full below with what was changed
instead. `CONTROLLER_STATE_TRANSITIONS` is not widened; no walk edge map in
this file changed.

---

## 1. Per-finding table

| Finding | Sev | Verdict | Where |
|---|---|---|---|
| AZ F5, the kill switch does not stop command execution | HIGH, SAFETY | **CLOSED** | `_run_command`, `_verify_and_finish`, `_close_without_running`, `_resume_result_in_and_orphans`, `_deliver_or_hold`, `_reject`, `_handle_late_result` |
| AZ F4, the PAUSED hold does not hold on the shipped route | HIGH | **CLOSED** for the hold, the judgement and the acceptance after resume; the METER is **disclosed, not charged** (section 6) | `receive_result`, `_close_without_running`, `_authorisation_moved`, `_disclose_uncharged_spend` |
| LV L4-F2, the contract-paused note loops forever | HIGH | **CLOSED** | `STOP_REASONS`, `_NOTE_CONTRACT_PAUSED`, `step` |
| LV L4-F3, an upstream founder gate parks as NOTHING_SELECTABLE | HIGH | **CLOSED** | `_founder_gated_units`, `_founder_gated_note`, `_handle_no_ready_units` |
| LV L4-F1, the settle path discards the wave's verdict | HIGH | **CLOSED** | `_settle_after_wave` and its five callers, `receive_result`'s `summary` out parameter, `cmd_record_result` |
| LV L4-F4, the VERIFYING park names three commands that cannot move it | MEDIUM | **CLOSED** | `_NOTE_DISPATCH_OPEN_UNMOVABLE`, `_resume_dispatched` |
| LV L4-F5, the fourth orphan shape is not modelled | MEDIUM | **CLOSED** | `_resume_result_in_and_orphans`, `_open_dispatches` |
| AZ F6, a unit id the fence refuses wedges the run | MEDIUM | **CLOSED**, at plan time (the preferred option) | `_validated_units`, `plan` |
| AZ F8, the re-await checks the fence's state only | MEDIUM | **CLOSED** | `_fence_no_longer_holds`, `_authorise_dispatch` step 5b |
| AZ F9, read_scope is never canonicalised | MEDIUM | **CLOSED** | `_validated_units`, `plan` |
| AZ F12, two founder notes state a cause that did not happen | LOW | **CLOSED** | `_NOTE_CONTENTION`, the three refusal words `_resume_dispatched` now maps |
| AZ F2, `plan` writes a foreign project's run | HIGH | **CLOSED** (handed to this writer mid-round by the orchestrator) | `plan`, plus `project_id=` threaded through all 48 controller store writes |
| AZ F10, an empty write_scope is dispatched and fences nothing | LOW | **DISCLOSED**, `docs/KNOWN-LIMITS.md` | out of scope by brief |
| Path floor (design 16.1) | | **DISCLOSED**, `docs/KNOWN-LIMITS.md` | out of scope by brief |
| Duplicate-driver adoption (design 16.2) | | **DISCLOSED**, `docs/KNOWN-LIMITS.md` | out of scope by brief |
| LV L4-F6, a retirement note claims three properties, two are pinned | LOW | **DISCLOSED**, `docs/KNOWN-LIMITS.md` | out of scope by brief |
| LV L4-F7, the suite is one test below a numeric floor | LOW | **DISCLOSED**, `docs/KNOWN-LIMITS.md` | out of scope by brief |

Nothing is BLOCKED.

---

## 2. AZ F5, the subprocess gate, and its proof

### The rule as implemented

No engine path executes ANY subprocess unless the contract is live at the
moment of execution, read immediately before. One method does it:

```python
def _run_command(self, project_id, command):
    if not self._contract_is_live(project_id):
        return None
    return self.checker.run(command, cwd=self.store.root)
```

`None` means NOTHING RAN, and every caller treats it that way rather than
inventing an exit code: an unrun check has no verdict.

### The call sites now gated, exhaustively

`self.checker.run` appears at exactly ONE line in the whole file, inside
`_run_command`. Six call sites reach it, and each was a real command
before:

| Line | Method | Command |
|---|---|---|
| 1445 | `_handle_late_result` | the unit's rollback (`git restore -- <write_scope>`) |
| 2254 | `_verify_and_finish` | the unit's own model-authored `done_check` |
| 2285 | `_verify_and_finish`, staleness branch | the rollback design 10.6 ADDED this round |
| 2295 | `_verify_and_finish` | the unit's own model-authored `verifier` |
| 2424 | `_reject` | the unit's rollback (reached from the malformed branch and from `check_timeouts`) |
| 3012 | `_deliver_or_hold` | the founder's whole `done_definition` |

Grep, whole file:

```
$ grep -n "self\.checker\.run\|self\._run_command(" tools/bm_controller.py
623:        any self.checker.run call."""
626:        return self.checker.run(command, cwd=self.store.root)
1445:            rb = self._run_command(project_id, rollback_cmd)
2254:        outcome = self._run_command(project_id, unit["done_check"] or "true")
2285:                rb = self._run_command(project_id, rollback_cmd)
2295:            v_outcome = self._run_command(project_id, unit["verifier"])
2424:            rb = self._run_command(project_id, rollback_cmd)
3012:            outcome = self._run_command(project_id, done_definition)
```

Line 623 is prose inside `_run_command`'s own docstring. The structural
guard that keeps this true is
`TestR5NoCommandRunsUnderADeadContract.test_every_checker_call_sits_behind_one_gated_call_site`,
which parses the file with `ast` and asserts the set of enclosing function
names of every `self.checker.run` call is exactly `{"_run_command"}`. A
seventh command site added later is gated by construction; a command site
added OUTSIDE the gate fails that test.

### The two branch points, which is where the founder-facing behaviour lives

The gate alone stops execution. What happens INSTEAD is decided in two
places, both of which read the contract for themselves:

* `_verify_and_finish`, first statement after the unit row read. This is
  the single method both refuted sequences land in: `record-result` after
  `bm-autonomy stop` (p12) and `step` on a RESULT_IN dispatch after a
  revoke (p11).
* `_resume_result_in_and_orphans`' RESULT_IN branch, which by design runs
  BEFORE step 2's live-contract read, so it asks for itself.

Both route to `_close_without_running`, which gives two different answers
because the two conditions are not the same thing:

* **paused** is reversible, so the answer is HELD: nothing recorded against
  the dispatch, no retry burned, the fence left where it is.
* **stopped, revoked or gone**: the result is already recorded and real, so
  a rejected verification carrying the reason, the unit through the circuit
  breaker, the fence PARKED, a founder step naming the unit and the
  contract state, and `stop_reason` `CONTRACT_NOT_LIVE`. Zero commands.

### The proof: p11 and p12 execute ZERO commands

Probe, against the REAL `SubprocessCheckRunner` (subclassed only to keep a
tape, and every recorded command is really executed), with the unit's
`done_check` set to `touch <marker>` so execution is visible from the
filesystem as well as from the tape. Throwaway store under
`tempfile.TemporaryDirectory()`.

```
== p12 (record-result) after `bm-autonomy stopped` ==
  contract state: stopped   gate_check: REFUSED-STATE
  receive_result -> 'rejected'
  commands the command executed: []
  done_check marker on disk: False
  stop_reason: 'CONTRACT_NOT_LIVE'
  unit status: READY   fence: parked
  founder steps: ['unit u1 returned a result after the contract was stopped. Nothing was ']
== p11 (step, RESULT_IN resume) after `bm-autonomy stopped` ==
  contract state: stopped   gate_check: REFUSED-STATE
  commands the step executed: []
  done_check marker on disk: False
  stop_reason: 'CONTRACT_NOT_LIVE'
  note: the contract is stopped, not live: nothing is authorised, so the result was recorded and rejected and NO command was executed (no done_check, no verifier, no rollback). The fence is parked and a founder step names the unit
  fence: parked
== p12 (record-result) after `bm-autonomy revoked` ==
  contract state: revoked   gate_check: REFUSED-STATE
  receive_result -> 'rejected'
  commands the command executed: []
  done_check marker on disk: False
  stop_reason: 'CONTRACT_NOT_LIVE'
  unit status: READY   fence: parked
  founder steps: ['unit u1 returned a result after the contract was revoked. Nothing was ']
== p11 (step, RESULT_IN resume) after `bm-autonomy revoked` ==
  contract state: revoked   gate_check: REFUSED-STATE
  commands the step executed: []
  done_check marker on disk: False
  stop_reason: 'CONTRACT_NOT_LIVE'
  note: the contract is revoked, not live: nothing is authorised, so the result was recorded and rejected and NO command was executed (no done_check, no verifier, no rollback). The fence is parked and a founder step names the unit
  fence: parked
```

The refuter measured, for both sequences and both kill words:
`commands the step executed: ['./unit-authored-done-check.sh', 'git restore -- a.py']`.
It is now `[]`, four times over, and the marker file the done-check would
have created does not exist.

Probe source: `p_r5_killswitch.py`, session scratchpad, EPHEMERAL. It is
short and its whole shape is described above; the permanent form of the
same property is the two `TestR5NoCommandRunsUnderADeadContract` tests,
which assert `checker.calls` is unchanged across the call.

---

## 3. AZ F4, the held answer, and the mechanism for the staleness collision

Three separate defects sat under this finding.

**One, the hold did not fire on the shipped route.** Round 4 held only on
`run["state"] == "PAUSED"`. `receive_result` now holds when the run is
PAUSED **or** the contract is paused, so a result arriving after
`bm-autonomy pause` and before the next `step` is held rather than judged
in full.

**Two, nothing was judged or rolled back.** Covered by section 2's gate:
the paused branch of `_close_without_running` touches nothing at all.

**Three, the held answer was rejected as stale on resume.** This is the
mechanism the brief asked me to explain.

### The mechanism: a lifecycle revision is not an authorisation move

`Store.set_contract_state` appends a new revision for every pause, resume,
stop and revoke, and its own docstring says it copies every authorisation
column forward verbatim (outcome, done_definition, allowed_paths,
allowed_surfaces, risk_classes, both ceilings, signed_by, signed_at). A
pause plus a resume therefore moves the revision integer by two and changes
NOTHING a dispatch was authorised to do. Comparing integers destroyed a
real answer for it.

`_authorisation_moved(project_id, stamped_revision)` replaces the integer
comparison in both places that made it (`_verify_and_finish`'s step-13
re-read and `_authorise_dispatch`'s step-5a stale stamp). It reads
`Store.contract_revisions` and returns moved=True only if some revision
strictly after the stamped one has a `change_kind` outside
`{pause, resume, stop, revoke}`, that is, a `sign` or an `amend`.

The dispatch's own stamped revision is still what the comparison uses, as
the brief requires; what changed is what the OTHER side of the comparison
means.

Three properties this keeps, stated because they are what makes it safe:

* **Liveness is not folded in.** Whether a stopped or revoked contract may
  be acted on at all is a separate question, asked earlier and more
  strictly by section 2's gate, which refuses and runs nothing. So
  classifying `revoke` as a lifecycle kind does not weaken anything: a
  revoked contract never reaches the revision comparison.
* **A real amend still rejects.** `sign_contract(supersede=True)` writes
  `change_kind` `amend`. Pinned by
  `TestR5TheHeldAnswerSurvivesAPausedContract.test_a_real_amend_across_the_pause_is_still_stale`,
  which pauses, holds, resumes, THEN narrows `allowed_paths`, and asserts
  the unit is not DONE and the dispatch REJECTED. It was green before the
  fix and is green after, which is what makes it a control.
* **Conservative on doubt.** An unreadable chain, or one longer than the
  window read back, reports moved=True, which is the round-4 answer.

### What did NOT get fixed: the meter

The brief says the meter is charged as design 10.1 requires. Design 10.1's
rule IS the live-contract guard, and `Store.record_spend` refuses
`no-live-contract` outright, so on the shipped route, where the CONTRACT is
what is paused, the charge cannot be made at the moment the answer is held.
It cannot be deferred to the resume either, because `Store.record_result`
carries no cost column, so the number is gone by the time the held answer
is judged.

What was actually wrong, and is now fixed, is that the skip was SILENT:
the breaker under-counted by exactly the held unit's cost with nothing to
reconcile against, which is REFUTATION-3 SM C's own defect reopened for the
new `"held"` outcome word. `_disclose_uncharged_spend` records a checkpoint
of kind `spend-uncharged` naming the exact tokens, minutes and contract
state. A checkpoint rather than a founder step on purpose: a founder step
gates the unit's whole lane through `select_ready_units`, which would block
the very lane the founder is about to resume.

The exact store change that would close it properly is in section 8.

---

## 4. The other closures, one paragraph each

**LV L4-F2.** `STOP_REASONS` gains `CONTRACT_PAUSED`, and `step`'s PAUSED
guard reads the contract to choose between it and `FOUNDER_WAITING`. The
new note names `bm-autonomy resume` and then `bm-controller resume`, in
that order, and says why the second alone loops. Step 2's own contract
branch uses the same reason and note. `test_following_the_note_actually_clears_the_pause`
drives the two commands the note names and asserts the run delivers.

**LV L4-F3.** `_founder_gated_units` computes the founder-waiting set as a
fixpoint: the base is `_is_founder_waiting` unchanged, and a PENDING,
READY or BLOCKED unit whose dependency is in the set joins it, inheriting
its blocker's LANE rather than getting one of its own. `_handle_no_ready_units`
tests membership in that set instead of calling `_is_founder_waiting`
directly, so the run reaches the WAITING_HUMAN store move and the
FOUNDER_WAITING reason. `_founder_gated_note` names the blocking lanes and
the open steps' text. Pure, recomputed every wave, no new column, law L4
intact.

**LV L4-F1.** `_settle_after_wave` takes the caller's own summary, and it
is a required argument so a future caller cannot pass a throwaway by
accident. All five callers pass a real one: `step` passes its wave summary;
`_resume_result_in_and_orphans` and `_resume_dispatched` each pass a local
one and lift its `stop_reason`, `note` and `founder_gated` into the dict
they return, which `step` then merges; `receive_result` passes the new
optional `summary` out parameter; `check_timeouts` passes its own. Round 4
forwarded only the note from the two resume branches, so a delivery reached
through a crash resume also reported "call step() again"; both now forward
the reason and the founder-gated block. `cmd_record_result` prints the
note, the reason and the founder-gated remainder, and `--json` carries
them.

**LV L4-F4.** `_NOTE_DISPATCH_OPEN_UNMOVABLE` names `record-result` and the
actual dispatch id, and says explicitly that `resume` only moves a PAUSED
run and `complete` is refused from here. The reason stays FOUNDER_WAITING,
which the refuter called defensible.

**LV L4-F5.** A fourth branch in the same loop the other three live in: a
unit whose status is DISPATCHED or RESULT_IN with NO open dispatch row.
Fence parked, unit returned through `mark_unit_failed` rather than
`release_claimed_unit`, because unlike a CLAIMED unit this one did have an
attempt and the circuit breaker owns that decision. The CLAIMED branch was
widened from "no dispatch rows at all" to "no OPEN dispatch", which is the
same question asked the way `_open_dispatch_units` asks it; the new helper
`_open_dispatches` is the per-unit form of that one definition.

**AZ F6.** `_validated_units` runs `bs.valid_name(UNIT_FENCE_PREFIX +
unit_id)` for every unit and refuses `bad-unit-id` naming the fence name
and the store's own reason. It runs at the TOP of `plan`, before the
ORIENTING walk and before `upsert_units`, so nothing is written and the run
has not moved: the wedge has no state to recover from.
`test_the_refusal_leaves_no_wedge` re-plans a good graph afterwards and
drives it to DELIVERABLE_READY.

**AZ F8.** `_fence_no_longer_holds` replaces the one-field state check. It
returns a phrase, not a boolean, so the founder note can say which of the
four things is wrong: the fence is gone, it is not active, its OWNER is no
longer this controller, or it no longer holds a named path. Containment,
via `bs.path_within_allowed(fence_file, declared_path)`, in the same
direction `gate_check` uses, so a fence narrowed to a subdirectory does not
pass for a unit that declared the parent.

**AZ F9.** `_validated_units` canonicalises every read_scope entry through
the same two store primitives the store's own write_scope path uses
(`bs._coerce_path_entry` then `bs.canonicalize_path`), so a path escape
refuses `path-escape` at plan time and the stored value is canonical. The
unit dicts are shallow-copied; the caller's own dicts are not mutated.
read_scope is still deliberately NOT gate-checked against `allowed_paths`,
which is a WRITE boundary; that decision is unchanged and its reasoning
stays in `_gate_check_write_scope`'s docstring.

**AZ F12.** `_authorise_dispatch` now returns three distinct refusal words
on the re-await route, `REFUSED`, `REFUSED-STALE` and `REFUSED-FENCE`, and
`_resume_dispatched` maps each to a note that says what actually happened.
The fence note says the contract did NOT move. The new words can only occur
when `open_dispatch` is not None, so the fresh route in `step` is
untouched. `_NOTE_CONTENTION` keeps its "no founder action is needed for a
transient overlap" (an existing test pins that phrase, see section 5) and
adds the case it was missing: if it repeats on every step, the fence is
held by a writer that is not coming back and somebody has to release it.

**AZ F2**, handed over mid-round by the orchestrator. Every store write
this file makes now passes `project_id=`, 48 call sites across all eleven
guarded entry points, so `Store._refuse_foreign_run` refuses
`run-not-in-project` before touching anything. Threading it everywhere and
not only on the `plan` path is deliberate: the guard only bites when the
caller passes the keyword, so a route left without it is a route on the
opt-out side of the check. `plan` was the reproduced hole and gets the
test; the other routes get the same protection for free.

---

## 5. The one collision with an existing test, and what changed instead

`TestF3AsyncSpendAfterARevoke.test_no_exception_escapes_spend_is_skipped_and_the_result_is_rejected_as_stale`
failed after the first version of `_close_without_running`, verbatim:

```
FAIL: test_no_exception_escapes_spend_is_skipped_and_the_result_is_rejected_as_stale
  File "tools/test_bm_controller.py", line 1297, in test_no_exception_...
    self.assertEqual(row["status"], "READY")
AssertionError: 'BLOCKED' != 'READY'
```

Cause: `_close_without_running` queued its founder step and then called
`_reconcile_lane_blocks`, which materialised the BLOCKED view immediately,
so the unit the test expects READY was BLOCKED.

The test was NOT edited. `_close_without_running` no longer reconciles.
That is the correct answer on its own terms and not a concession: the
founder step in the unit's own lane IS the mechanism (`select_ready_units`'
blocked-lane query makes the lane unselectable without any status write),
and BLOCKED is a VIEW that the next wave derives, which is law L4.
`_handle_late_result` still reconciles for the reason its own comment
gives, that a late result can land on a run no later `step()` will ever
drive; a result closed under a dead contract is not that case, because the
very next `step` drains the run. Writing a BLOCKED status onto a run that
is about to drain would leave a status nobody reverses.

No other existing test changed behaviour, and none was edited. Three
existing tests are worth naming as the ones that constrained the design:

* `TestRevokedContractMidUnit` requires a revoke mid-unit to still produce
  a REJECTED dispatch whose verdict text contains "stale". The dead-contract
  verification text keeps that word, accurately: the authorisation the
  dispatch was stamped under is exactly stale.
* `TestF3AsyncSpendAfterARevoke` requires `spend_totals == 0` after a
  revoke, which is why the meter answer in section 3 is disclosure and not
  a widened guard.
* `test_a_fence_overlap_is_contention_and_says_so` asserts
  `"no founder action is needed"` is IN the contention note, which is why
  AZ F12's second half qualifies that phrase rather than removing it.

---

## 6. What I need from the store writer

Nothing is blocking. Two requests, both additive, neither needed for this
round to land.

1. **A held result's meter cannot be charged (section 3).** Either would
   close it, and the second is the better shape:
   * `Store.record_spend(..., allow_paused=False)`, so a caller can charge
     against a contract that is PAUSED but not stopped or revoked. A pause
     suspends an authorisation; it does not remove it.
   * or a cost carried on the recorded result, e.g.
     `Store.record_result(dispatch_id, worker_claim, artifacts, actor,
     cost=None)` persisted on the dispatch row, so the controller can defer
     the charge to the moment the held answer is finally judged under a
     live contract. This is strictly better, because it also lets a
     stopped-contract result's cost be reconciled later rather than lost.
2. **Confirmation of two couplings this file now has.** `_validated_units`
   calls `bs._coerce_path_entry`, which is private, deliberately, so
   read_scope passes the IDENTICAL gate write_scope passes rather than a
   second implementation that can drift. If that helper is ever renamed or
   its contract changed, this file needs to move with it. `_authorisation_moved`
   depends on `Store.set_contract_state` continuing to copy every
   authorisation column forward verbatim for `pause`, `resume`, `stop` and
   `revoke`, and on `change_kind` staying the field that distinguishes those
   from `sign` and `amend`. Both facts are quoted from that method's own
   docstring; if either changes, the staleness rule must change with it.

I depended on exactly the two things the brief said to assume: the
glob-in-write_scope refusal (nothing in this file or its suite declares a
pattern write scope, so nothing changed for it) and the project-versus-run
ownership check (now wired, section 4).

---

## 7. Done-check

Run after the last edit, from `/Users/khalil.maaouni/Documents/BrotherModeUp`.

```
$ python3 tools/test_bm_controller.py
----------------------------------------------------------------------
Ran 124 tests in 9.001s

OK
EXIT=0
```

```
$ python3 tools/test_bm.py
Ran 276 tests in 42.322s
OK (skipped=1)
EXIT=0
```

Targeted run over the twelve new classes:

```
$ cd tools && python3 -m unittest \
    test_bm_controller.TestR5NoCommandRunsUnderADeadContract \
    test_bm_controller.TestR5TheHeldAnswerSurvivesAPausedContract \
    test_bm_controller.TestR5AContractPauseIsNotARunPause \
    test_bm_controller.TestR5AnUpstreamFounderGateIsFounderWaiting \
    test_bm_controller.TestR5TheSettlePathCarriesItsVerdict \
    test_bm_controller.TestR5TheVerifyingParkNamesTheRealRecovery \
    test_bm_controller.TestR5TheFourthOrphanShapeRecovers \
    test_bm_controller.TestR5PlanRefusesAUnitIdTheFenceWouldRefuse \
    test_bm_controller.TestR5PlanRefusesAForeignRun \
    test_bm_controller.TestR5ReadScopeIsCanonicalisedLikeWriteScope \
    test_bm_controller.TestR5TheReAwaitChecksTheFenceContentAndOwner \
    test_bm_controller.TestR5FounderNotesStateWhatActuallyHappened
..........................
----------------------------------------------------------------------
Ran 26 tests in 0.327s

OK
```

Counts: the controller suite went from 98 test methods to 124 (26 new
across 12 classes, 2 of them labelled THE CONTROL in their own docstrings
and green before the fix). `tools/test_all.py` and the store suite were NOT
run, as instructed.

No line in `tools/bm_controller.py` exceeds 79 columns. No em or en dash
appears in any file this round wrote (`grep -n "[em dash][en dash]"` over
all six returns nothing).

---

## 8. What I did NOT check, and what is only partly checked

* **`tools/test_all.py`, `tools/test_bm_store.py` and
  `tools/test_bm_autonomy.py` were not run**, as instructed. I make no
  claim about any of them. The `project_id=` threading in section 4 touches
  eleven store methods from this file's side only; the store writer's own
  suite is what proves the store side.
* **Two real operating-system processes against one store.** Every probe
  and every test here is a single process. The concurrency-shaped windows
  the refuters recorded as unexplored stay unexplored.
* **A real process kill.** The fourth orphan shape and the VERIFYING park
  are constructed with a direct `record_verification` and a direct
  `set_run_state`, which stand in for the first half of a two-call window,
  exactly as the refuter constructed them. No process was killed.
* **`check_timeouts` under a real clock.** It is still wired to no
  subcommand, so in production nothing times a hung dispatch out. Unchanged
  this round beyond the summary argument and the gated rollback.
* **The CLI section of the controller suite** ran as part of the full file
  and is green, but I added no CLI subprocess test of my own for the new
  `reason:` and `founder-gated remainder:` lines `record-result` now prints.
  That output is covered in-process, by
  `test_record_result_reports_the_settled_verdict_to_its_caller`, not
  end to end.
* **AZ F7** (an ACTIVE fence over a unit that is still READY, the half of
  the claim-to-claim_unit window that stays open) was NOT on my list and is
  NOT closed. The engine cannot see that fence from the unit row, because
  the unit's `fence_uuid` is NULL; finding it needs a lookup by fence NAME,
  which is a shape this file does not have. Its founder-facing half, the
  note that told the founder nothing was needed, IS fixed (AZ F12). The
  underlying strand is not.
* **AZ F11** (`_coerce_path_entry` is not total for an object whose
  `__repr__` or `__fspath__` raises) was not on my list and is not closed.
  It is a store-side property and an SDK caller's problem only; note that
  `_validated_units` now calls that helper on read_scope, so the same LOW
  exotic-input hole is reachable through `plan` from an SDK caller passing
  such an object, exactly as it already was through write_scope.
* **`docs/AUTONOMY.md` and `references/autonomy.md` were not reviewed or
  written.** `docs/FULL-AUTO.md` and `docs/KNOWN-LIMITS.md` are the two I
  own and both are updated.
* **Windows and Linux.** Everything ran on darwin.
* **Whether any of these has ever occurred in a real run.** Reachability
  was demonstrated; incidence was not.
