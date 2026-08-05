# FIX round 7, the CONTROLLER, the last fix round before a public push

Writer: the round-7 CONTROLLER writer, the only writer this round. Files
written, and only these:

* `tools/bm_controller.py`
* `tools/test_bm_controller.py`
* `docs/FULL-AUTO.md`
* `docs/KNOWN-LIMITS.md`
* `docs/program/absolute-lead/evidence/L03/RED-round7.txt`
* this report

`tools/bm_store.py` and `tools/test_bm_store.py` were readable and writable
this round and were **NOT written**. Nothing needed them: every one of the
five findings is a question the ENGINE asks (or fails to ask) about a row
it already holds, so every fix belongs where the question is asked.
`SECURITY.md` was **not written** either, because its line-count guard did
not trip (section 0 has the measurement).

Input read in full before any edit: `REFUTATION-6-pushgate.md` (F1 to F6,
the verdict table and the attempts log), then
`FIX-round6-controller-report.md`.

---

## 0. Done-check, run after the last edit

```
$ cd /Users/khalil.maaouni/Documents/BrotherModeUp
$ python3 tools/test_bm_controller.py
...
Ran 169 tests in 13.205s

OK
EXIT=0
```

```
$ python3 tools/test_bm.py
...
Ran 276 tests in 44.461s

OK (skipped=1)
EXIT=0
```

```
$ cd /Users/khalil.maaouni/Documents/BrotherModeUp/tools
$ python3 -m unittest \
    test_bm_controller.TestR7EveryCommandTheJudgingPathRunsIsInventoried \
    test_bm_controller.TestR7TheKillSwitchIsAskedAtEveryWindow \
    test_bm_controller.TestR7TheFounderNoteNamesWhatActuallyRan \
    test_bm_controller.TestR7TheJudgingGateRefusesAMalformedScopeContainer \
    test_bm_controller.TestR7TheReservedLaneIsMechanicallyReserved \
    test_bm_controller.TestR7TheGuardCoversAliasedExecutionPrimitives
...
Ran 23 tests in 1.464s

OK
EXIT=0
```

**23 new tests in 6 new classes.** At RED capture, before any edit to
`tools/bm_controller.py`: **14 red (13 failures, 1 error), 9 green as
controls**. The whole capture is verbatim in `RED-round7.txt`.

`python3 tools/test_bm_store.py` was NOT run and is not owed: the store was
not touched (`git status --short` shows `tools/bm_store.py` unmodified).
`tools/test_all.py` was NOT run, per the brief.

**The `test_bm.py` line-count guard did not trip, so `SECURITY.md` was not
edited.** Re-measured with that file's own published command:

```
$ find tools -name "*.py" -o -name "*.sh" | xargs wc -l | tail -1
   92295 total
```

`SECURITY.md` line 101 claims "about 91,100 lines" (corrected by someone
after round 6 reported the drift). Drift is 1.3 percent against a 15
percent guard, so the figure is still true after this round's added lines.
`test_bm.py`'s `test_security_md_line_count_claim_is_still_true` passes,
which is the authority here rather than my arithmetic.

**Existing tests are law and none was edited.** No collision occurred.
`CONTROLLER_STATE_TRANSITIONS`, `STOP_REASONS` and `AUTONOMY_FLOORS` were
not widened: every reason word used this round (`CONTRACT_NOT_LIVE`,
`SPEND_STOP`, `FOUNDER_WAITING`, `CONTRACT_PAUSED`, `DELIVERED`) was
already in the enum. The glob ALLOWANCE rule was not touched.

---

## 1. Per-finding table

| Finding | Sev | Verdict | Where |
|---|---|---|---|
| **F1**, a kill landing during the VERIFIER accepts the unit under a killed contract | HIGH, the founder's kill switch | **CLOSED**, and widened: the window set is now complete and includes one F1 did not name (the delivery window) | `_authorisation_window`, `_verify_and_finish` (3 windows), `_deliver_or_hold` (the 4th), `_refusal_stop`, `_R7_COMMAND_SITES` |
| **F2**, the shipped record-result prints "NO command was run" in a call in which three ran | HIGH, honesty | **CLOSED** by deriving every such sentence from a ledger of what executed, never from the branch that writes it | `_run_command`'s ledger, `_nothing_ran_clause`, `_nothing_executed_clause`, `_step_execution_clause`, `_spend_breaker_note`, `_contract_not_live_note`, `_close_without_running`, `_settle_after_wave`, `_deliver_or_hold` |
| **F3**, five more bypass spellings pass the structural guard | LOW | **CLOSED for those five**, plus three more this writer found by attacking its own fix. The boundary it does NOT cover is stated in section 4 rather than claimed away | `_execution_primitive_offences`, `_ALLOWED_MODULE_IMPORTS`, `_import_alias_targets`, `_resolved_dotted`, `_BANNED_MODULE_ATTRIBUTE_NAMES`, `_BANNED_NAMESPACE_ROOTS`, `_RUNNER_CLASS` |
| **F4**, a non-iterable `write_scope` is an uncaught TypeError out of `receive_result` | LOW | **CLOSED** as a named refusal with its own verdict word and its own founder-facing sentence | `_gate_check_write_scope`, `_REFUSED_SCOPE_SHAPE`, `_close_without_running` |
| **F5**, `spend-reconciliation` is documented as reserved and is not | LOW | **CLOSED**, both halves, justified in section 5: reserved mechanically at plan time AND selected by a marker rather than by lane | `_validated_units`, `_SPEND_RECONCILE_MARKER`, `_disclose_uncharged_spend`, `_unreconciled_uncharged_spend` |
| F6, resolving the reconciliation step does not charge the meter | disclosure | **NOT ATTEMPTED**, and not closable from this file: the fix is a cost column on `Store.record_result`, in the store. Left open, section 6 | |

---

## 2. F1: the window inventory, and why the set is complete

### The complete list of commands the judging path can run

There are exactly **six command sites** in `tools/bm_controller.py`, and
`_run_command` is the only door to the `CheckRunner`. That is not a claim,
it is `test_the_command_sites_are_exactly_the_inventoried_ones`, which
compares the AST against a hard-coded inventory and fails if a site is
added, moved or removed:

| # | Method | Command | Window after it |
|---|---|---|---|
| 1 | `_verify_and_finish` | the unit's `done_check` | **W1** |
| 2 | `_verify_and_finish` | the unit's `verifier` | **W2** |
| 3 | `_reject_as_stale` | `git restore` rollback | none, by the argument below |
| 4 | `_reject` | `git restore` rollback | none, by the argument below |
| 5 | `_handle_late_result` | `git restore` rollback | none, by the argument below |
| 6 | `_deliver_or_hold` | the founder's WHOLE done-definition | **W4** |

Plus **W3**, which follows no command at all: it sits immediately before
`record_verification`, the first statement that writes down what happened
to the unit.

**The four windows that now exist:**

* **W1**, after the `done_check`. Round 6's, absorbed into the shared
  helper unchanged, its founder-facing sentence kept word for word.
* **W2**, after the `verifier`. **This is F1.** In full auto the verifier is
  model-authored shell of unbounded duration, and round 6 asked nothing
  between it and the acceptance.
* **W3**, immediately before the acceptance is written. Adjacent to W2
  today and kept anyway: "re-asked after every command" and "re-asked
  immediately before the acceptance" are two different promises, and the
  second must not depend on nobody ever inserting a statement between them.
* **W4**, after the founder's whole done-definition and before
  `record_checkpoint('deliverable-ready')` and the walk to
  `DELIVERABLE_READY`. **F1 did not name this one.** It is the same defect
  one method along, on the longest-running command in the system: a
  `bm-autonomy stop` pressed during the founder's test suite was followed,
  in the same call, by their run being declared ready. Declaring a
  deliverable is an acceptance, so it is gated like one.

**Why sites 3, 4 and 5 need no window after them, stated so a reader can
disagree with me:** each is a `git restore` on a path where the unit has
ALREADY been rejected and the rejection has already been written down.
Nothing is accepted after a rollback, no further command follows it in that
method, and the rollback itself is refused BEFORE it runs by
`_run_command`'s own gate (a dead contract composes the command and runs
nothing, which is the kill switch working). A window there could change a
sentence, never an outcome. Those sentences are F2's subject instead, which
is where they belong.

### One helper, not two copies

`_authorisation_window` is the single ask-and-answer for W1, W2 and W3. It
re-reads the WHOLE authorisation (`_authorisation_refusal`: contract state,
spend breaker, and the unit's whole write scope under one revision), and on
a refusal routes through `_reject_as_stale`, the SAME sequence round 6's
done_check window and the ordinary staleness branch already used, never a
lookalike of it: rejected verification carrying the real exit code, the
unit back through the circuit breaker, the rollback, the fence parked, a
founder step, and the caller's summary given a reason from the enum.

W4 lives in `_deliver_or_hold` and does not go through that helper, for one
reason: it has no unit, no dispatch and no fence, so there is nothing to
reject. It shares what CAN be shared, the ask (`_authorisation_refusal`)
and the sentence builder (`_refusal_stop`), which this round also folded
the two pre-command refusal chains into, so the breaker sentence has one
author instead of three.

### The reproduction, closed

`TestR7TheKillSwitchIsAskedAtEveryWindow` uses the refuter's own technique
one command later: the unit's VERIFIER is itself the kill switch, so the
stop lands at a precisely named instant rather than by luck. Before the
fix, verbatim:

```
FAIL: test_a_revoke_during_the_verifier_is_not_an_acceptance
AssertionError: 'u1' != 'rejected'

FAIL: test_a_kill_during_the_verifier_owes_the_founder_a_step
AssertionError: False is not true : a founder step names the unit: []

FAIL: test_a_revoke_during_the_done_definition_declares_no_deliverable
AssertionError: 'DELIVERABLE_READY' == 'DELIVERABLE_READY'
```

After: `checker.calls == ['true', 'verify-u1']` (both commands really ran,
so the window under test is genuinely the verifier's), outcome `rejected`,
the unit is not accepted, the dispatch is not recorded as verified, the
fence is `parked`, one founder step names `u1`, and the reason is
`CONTRACT_NOT_LIVE`.

**No wedge was introduced, and I checked rather than assumed.** After W4
fires the run stays `CHECKPOINTED` and the founder's own remedy works on
the next step, driven through a probe in a throwaway store:

```
revoke   after the kill: state=CHECKPOINTED   reason=CONTRACT_NOT_LIVE
revoke   after the founder acts: state=DELIVERABLE_READY reason=DELIVERED
after the ceiling blew : state=CHECKPOINTED reason=SPEND_STOP
after sign --supersede: state=DELIVERABLE_READY reason=DELIVERED
```

`test_a_live_contract_still_accepts_and_still_delivers` is the control that
matters most: on a run nobody killed, every window is a no-op, the commands
are `['true', 'verify-u1', 'echo done']` in that order, and the run
delivers.

---

## 3. F2: the sentence is derived from what ran, not from which branch

### What was wrong, and why round 6's fix could not hold

Round 6 fixed this class once, by giving `_settle_after_wave` its own note
constant. The defect came straight back in the constant that same round
INTRODUCED: `_NOTE_SPEND_BREAKER` hard-codes "NO command was run for this
result: not the unit's done_check, not its verifier, not the rollback and
not the whole done-definition", and two of its three use sites are reached
in calls that may have just run all three. A per-branch constant cannot fix
this class, because the branch is the wrong thing to derive the sentence
from: it says which rule refused, not what already executed.

### The fix

`_run_command` is the ONE door to the `CheckRunner`, so it is the one place
that knows the truth. It now appends a short label to a per-call **ledger**
AFTER the runner returns. Every "nothing ran" sentence in the file is built
from that ledger by one of three functions (`_nothing_ran_clause`,
`_nothing_executed_clause`, `_step_execution_clause`). A command site that
does not name itself is a test failure
(`test_every_command_site_names_itself_to_the_ledger`), so the ledger
cannot silently miss a command.

The ledger is reset at every public entry (`step`, `receive_result`,
`check_timeouts`). It is the only thing kept on `self`, it feeds prose and
nothing else, and no control flow reads it, which is what keeps it inside
the engine's own "hold no state across a call" rule rather than an
exception to it.

The refuter's own reproduction, at the engine, now reads:

```
the founder's SPEND CEILING has tripped (spend is at or over 100 percent
of a ceiling (104 token(s) of 100, 0 minute(s) of 100); the breaker has
tripped.), so nothing further is authorised and no command was run after
that point, and what this call HAD already run, each under an
authorisation that was live at the moment it started, is: the unit's
done_check. Raise the ceiling with bm-autonomy sign --supersede, or
accept the stop; the run drains on the next bm-controller step

commands the engine really ran: ['true']
```

`test_the_same_note_still_says_nothing_ran_when_nothing_ran` is the control
and matters as much: on the leg where nothing ran, the founder must still
be told "NO command was run", so the fix is not "delete the sentence".

### Every other founder-facing string on that path, and what I found

| String | Site | Verdict |
|---|---|---|
| `_NOTE_SPEND_BREAKER` | `_close_without_running`, `_settle_after_wave`, `_deliver_or_hold` | **WAS FALSE at two of three sites.** Now `_spend_breaker_note(reason, ledger)` |
| `nothing_ran` ("NO command was executed (no done_check, no verifier, no rollback)") | `_close_without_running`, every branch | **WAS FALSE**, and F2 did not name this one: `_close_without_running` is also reached from the VERIFIER's own refusal, where the done_check has already run. Now derived |
| the founder step "Nothing was executed for it: not its done_check, not its verifier and not its rollback" | `_close_without_running` | **SAME DEFECT, same branch.** Now derived. This is the copy a founder still has days later, so it mattered more than the summary |
| the two fence notes "nothing was judged and nothing was run" | `_close_without_running` | **SAME DEFECT.** Now derived |
| `_NOTE_CONTRACT_NOT_LIVE` ("NO command was executed") | `_close_without_running`, `_handle_late_result` | **FALSE on the same verifier branch** (true at the late-result site, where the rollback is gated off). Now `_contract_not_live_note(state, ledger)` |
| `_reject_as_stale`'s founder step, "its done_check RAN" | the F1 windows | True, and it now names the actual list instead of assuming it |
| `_NOTE_SETTLE_CONTRACT_NOT_LIVE` | `_settle_after_wave` | **CHECKED, no change.** Round 6 built it for exactly this reason and it claims nothing about what ran |
| `_NOTE_CONTRACT_DIED_MIDCOMMAND` | the F1 windows | **CHECKED, no change.** It is the one note in the file that says a command DID run |
| `_NOTE_SPEND_UNRECONCILED` | `_deliver_or_hold` | **CHECKED, no change** for this defect. Its own falseness is F5, fixed there |
| `_deliver_or_hold`'s two CONTRACT_NOT_LIVE notes | `_deliver_or_hold` | **CHECKED, no change.** Both are scoped to the done-definition, which genuinely did not run on those branches |
| `_refuse_unsafe_scope`'s "Nothing was claimed, nothing was handed to a worker" | the dispatch path | **CHECKED, no change.** True: that path refuses before anything is claimed |
| `_handle_late_result`'s own step text | late results | **CHECKED, no change.** It claims nothing about what ran |
| `_warn_unrollbackable_scope`'s "whatever it wrote is still there" | rollback refusals | **CHECKED, no change.** True by construction |

`docs/FULL-AUTO.md` keeps its promise and now says HOW it is kept, so the
promise and the mechanism sit in the same paragraph.

**One honest bound, disclosed in `KNOWN-LIMITS.md`:** the ledger is per
CALL, not per unit. On `bm-controller record-result`, which handles exactly
one result, those are the same set. On a `step` wave that judges several
units, the sentence names every command the WAVE ran, which is coarser than
per-unit and still true.

---

## 4. F3: the guard, the mutation evidence, and the tenth spelling

### What landed

Four rules, in the order they kill the most:

1. **The import list is pinned by name.** Every binding anywhere in the
   file, including inside a function body, must be a plain unaliased import
   of one of the eight modules the file already has. That alone kills
   `import subprocess as sp`, `from os import system as X` and every
   primitive that needs a module the file lacks (`operator`, `functools`,
   `pty`, `multiprocessing`, `ctypes`, `asyncio`). It is the refuter's own
   "more cheaply" suggestion, hard-coded so a future import is a deliberate
   edit rather than a silent widening.
2. **Names are resolved through those imports before they are tested**, so
   a rebinding that gets past rule 1 is still read as what it really names.
3. **A banned name is an offence wherever it appears**, not only where it
   is called: `runner = os.system` then `runner(cmd)` is two ordinary
   statements and one ungated process.
4. **The `checker` attribute is gated on its NAME**, whatever object it
   hangs off, because `holder = self` is `runner = self.checker` with one
   more step in it.

### The mutation evidence

Every spelling is spliced into a SCRATCH COPY of `tools/bm_controller.py`
held in memory. The repo file is never written and no mutant is ever
executed: the only thing done with it is `ast.parse`. The round-6 guard is
not described here, it is extracted from git at `1e40b8e` and run, so every
`round6=PASSES` is that guard's own verdict. The full table and every
failure message are verbatim in `RED-round7.txt`; the summary:

```
subprocess.run() added inline in _verify_and_finish             round6=FAILS   round7=FAILS
os.system() added inline in _verify_and_finish                  round6=FAILS   round7=FAILS
getattr(self.checker, 'run') in _verify_and_finish              round6=FAILS   round7=FAILS
runner = self.checker; runner.run(...) in _verify_and_finish    round6=FAILS   round7=FAILS
NEW-A  from subprocess import run as X; X(cmd, shell=True)      round6=PASSES  round7=FAILS
NEW-B  import subprocess as sp; sp.run(cmd, ...)                round6=PASSES  round7=FAILS
NEW-C  from os import system as X; X(cmd)                       round6=PASSES  round7=FAILS
NEW-D  operator.attrgetter('checker')(self).run(cmd, ...)       round6=PASSES  round7=FAILS
NEW-E  import subprocess as _sp; _sp.Popen(cmd, ...)            round6=PASSES  round7=FAILS
HUNT-1 an alias of SELF, not of the checker                     round6=PASSES  round7=FAILS
HUNT-2 the builtins namespace, subscripted                      round6=PASSES  round7=FAILS
HUNT-3 importlib.import_module, which needs no new import name  round6=PASSES  round7=FAILS
HUNT-4 a banned primitive bound WITHOUT being called            round6=PASSES  round7=FAILS
HUNT-5 the gated object handed back out of the gate             round6=FAILS   round7=FAILS
HUNT-6 subprocess borrowed from the loaded sibling module's namespace  round6=PASSES  round7=FAILS
HUNT-7 os.system borrowed the same way, which really works      round6=PASSES  round7=FAILS
HUNT-8 a SECOND class in the module, calling subprocess directly  round6=FAILS   round7=FAILS
HUNT-9 self.__dict__ to reach the checker without naming it     round6=FAILS   round7=FAILS
HUNT-14 a second SubprocessCheckRunner, built outside the gate  round6=PASSES  round7=FAILS

THE CONTROL: the shipped file, unmutated
round 6 guard -> []
round 7 guard -> []
pinned import list -> ['datetime', 'importlib.util', 'json', 'os', 'shlex',
                       'subprocess', 'sys', 'uuid']
```

Round 6's four are kept as a calibration class of their own
(`test_the_round_six_four_still_fail`), so a guard rebuilt to catch five new
spellings but that stopped catching the four it already caught fails the
suite.

### Did I find a tenth spelling? YES, three, against my own fix

I attacked the ROUND 7 guard, not round 6's, and it lost twice before it
held:

* **HUNT-6 and HUNT-7, the module-namespace hop.** `bm_controller.py` loads
  `bm_store.py` by path and binds it as `bs`, and `bm_store.py` imports
  `os`, so **`bs.os.system('echo pwned')` is a working ungated command
  site** that alias resolution cannot see: `bs` is the return value of a
  function, so nothing in the source says what it holds. Closed by
  `_BANNED_MODULE_ATTRIBUTE_NAMES`, which makes a module name reached as an
  ATTRIBUTE an offence. Safe here because the shipped file reaches none of
  them that way (`importlib.util` and `os.path` are a NAME followed by an
  attribute, the other way round).
* **HUNT-14, a second runner.** Every rule gated the checker OBJECT and the
  primitives, and none of them stopped
  `SubprocessCheckRunner().run(cmd, cwd='.')`, which builds a second runner
  with no gate in front of it. Closed by pinning the class NAME to the one
  CLI factory that constructs it.

A third hunt round (a lambda holding the primitive, the primitive in a dict
literal, `type(self).checker`, an in-method subclass of the seam class,
swapping `self.checker` at runtime, `self.checker.run.__self__`) found
nothing new: all six fail the guard.

### The boundary, stated plainly, because an honest boundary beats a false claim

**The guard is NOT total. Here is exactly what it does not cover.**

* **The module's own `_load` helper.**
  `importlib.util.spec_from_file_location` plus `spec.loader.exec_module`
  executes a sibling `.py` file by path, and it is how every tool in this
  repository loads `bm_store.py`. Banning it would fail the shipped file.
  So a future edit could reach a command through a sibling module's own
  FUNCTION rather than through a primitive named in the guard, and it would
  look like any other `bs.` call. I closed the reachable half (borrowing a
  sibling's IMPORTS); the other half is open.
* **The injected `WorkerAdapter` seam.** `self.worker.run(brief)` is not
  gated by this guard. The production adapter starts no process (it prints
  a brief and parks), but an SDK caller injects its own, and that is the
  caller's code rather than this module's.
* **Ordinary `os` I/O that is not a process start.** `os.write` to an
  already-open descriptor is not refused. The primitives that could CREATE
  such a descriptor for a shell (`os.openpty`, `pty.spawn`, `os.fork`) are
  all refused.
* **It reads source, not behaviour.** It is a guard against a future edit,
  not a sandbox. The runtime control is `_run_command`'s gate; this is the
  structural claim that the gate cannot be walked around by accident.

The class it DOES cover, stated as a claim the next refuter can attack:
*no execution primitive can be reached from anywhere in
`tools/bm_controller.py` outside `SubprocessCheckRunner.run` by any
spelling that resolves through this file's own imports, names, attributes
or classes.* All nineteen spellings above are inside that class.
`bs.<a sibling's own function>` is outside it.

---

## 5. F4 and F5, and the choice each one forced

### F4, the SCOPE half of the refusal is now total

`_gate_check_write_scope` asks `_unsafe_scope_container` before it iterates
anything, exactly as `_authorise_dispatch` has always done at its own top,
and returns this file's own verdict word `_REFUSED_SCOPE_SHAPE` with its
own founder-facing sentence in `_close_without_running`. Not "the contract
refuses this scope", which would send a founder to widen a contract that is
not the problem: the scope is not a shape that can be read AS a scope, so
no path in it was ever judged.

Before: `TypeError: 'int' object is not iterable` out of `receive_result`,
at the exact line the refuter quoted (the traceback is in
`RED-round7.txt`). After: outcome `rejected`, **zero commands executed**, a
founder step naming the unit, and `main()` sees a refusal rather than a
traceback.

**What I deliberately did NOT move, and why:** the ENTRY question (a git
pathspec, a glob, an option-looking path) stays where it is acted on, in
`_rollback_plan`. Moving it into the judging gate would refuse the
`done_check` of a unit whose answer is already in hand, over a fault in a
field the check does not use, and it collides head-on with an existing test
(`test_a_scope_that_goes_bad_after_dispatch_is_never_rolled_back` asserts
the founder is told the scope was "NOT rolled back", a message only the
rollback path writes). Existing tests are law. The container question is
different in kind: without it there is no loop to run at all.

### F5, I took BOTH halves of the choice, and here is the justification

The refuter offered "either reserve it mechanically at plan time or stop
claiming it is reserved", plus a second option ("select by a marker the
disclosure writes"). I did the reservation AND the marker, because they
close different routes and neither closes the other's:

* **`plan` refuses the lane name** (`_validated_units`, beside the unit-id
  rule, before the ORIENTING walk, so nothing is written and the run has
  not moved). This is what makes the shipped documentation TRUE: "a
  reserved lane no unit is ever planned into" is now enforced rather than
  hoped for, and no unit can ever be gated by a bookkeeping step. It closes
  the route through the shipped commands.
* **The delivery block selects by a marker the disclosure itself writes**,
  not by lane. This closes the route the reservation cannot: a step queued
  into that lane by anything other than the disclosure (an SDK caller, a
  future tool, a hand-written row) no longer blocks a whole run's delivery
  citing spend that was never uncharged. The refuter's probe D2 is exactly
  that shape, and its note stated a cause that had not happened.

Choosing only the reservation would have left D2's own false sentence
reachable; choosing only the marker would have left the documentation
false. The cost is one string constant that one method writes and one
method reads.
`test_a_real_disclosure_still_blocks_delivery` is the control: the marker
narrows the selection, it does not put a hole in it.

---

## 6. What I did NOT check, what is only partly checked, and what is left open

* **`tools/test_all.py` was not run**, per the brief. I make no claim about
  the gate.
* **`tools/test_bm_store.py` was not run** and the store was not touched.
  Nothing in this round reads or writes it, and `git status` confirms it is
  unmodified.
* **F6 is not attempted and stays OPEN**: resolving a reconciliation step
  does not charge the meter, so 90 claimed tokens can still reach
  `DELIVERABLE_READY` metered as 0 if a founder resolves the step without
  running the `bm-autonomy spend` the step names. The engine checks that
  the step is RESOLVED, never that the charge landed. The fix is a cost
  column on `Store.record_result`, or a resolution the store validates,
  which is a store change. Round 6 said the same and I agree with it rather
  than papering over it.
* **`tools/bm_fence_hook.py` was not read or run.** Three FIX reports now
  name it as an unchecked third reader of a write scope. Still unchecked.
* **Concurrency.** Every test and probe here is single process. The kill
  switch is simulated by the CheckRunner firing it at a named instant,
  which is a faithful stand-in for a second terminal but is not two
  processes. Round 6's refuter drove a REAL second process at the CLI for
  the done_check window; I did not repeat that at the CLI for the verifier
  or the delivery window, and the engine-level tests are what I stand on.
* **No CLI-level test was added this round.** All 23 new tests are engine
  tests. The paths they cover are reached by `bm-controller record-result`
  and `bm-controller step`, and the existing CLI section is untouched and
  green, but there is no subprocess-level reproduction of F1 or F2.
* **The cost of the windows was not measured.** W2 and W3 are adjacent for
  a unit with a verifier, so such a unit pays for one authorisation read
  (three store reads) it does not strictly need today. That is deliberate
  (section 2) and disclosed in `KNOWN-LIMITS.md`, and I did not measure it
  on a large store.
* **The AST guard's boundary is real and named** (section 4): the `_load`
  mechanism, the injected worker seam, and non-process `os` I/O are outside
  what it can see. I would rather hand the next refuter that sentence than
  a claim they can knock over.
* **`docs/program/absolute-lead/evidence/L03/E4-endtoend.json` shows as
  modified.** It is regenerated by `TestEndToEndE4` on every run, by that
  test's own documented design, and was already modified in the working
  tree before this writer started.
* **Platform.** Everything ran on darwin, Python 3.9.6. Nothing this round
  touches git or the filesystem in a platform-specific way; the AST rules
  and the note builders are pure Python.
