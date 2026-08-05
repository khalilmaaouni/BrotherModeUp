# FIX round 6, the CONTROLLER half of the L03 hardening

Writer: the round-6 CONTROLLER writer. Files written, and only these:

* `tools/bm_controller.py`
* `tools/test_bm_controller.py`
* `docs/FULL-AUTO.md`
* `docs/KNOWN-LIMITS.md`
* `docs/program/absolute-lead/evidence/L03/RED-round6-controller.txt`
* this report

`tools/bm_store.py` and `tools/test_bm_store.py` belong to the parallel
STORE writer this round and were READ but never written. They are closing
the DECLARATION side of S1 (refusing pathspec magic and bad container types
where a write scope enters the store); this report closes the EXECUTION
side, so the fix holds even if a bad entry reaches the engine by some other
route. That duplication is deliberate defence in depth and is written down
as such in both `_unsafe_scope_entry`'s docstring and
`docs/KNOWN-LIMITS.md`.

Input read in full before any edit: `REFUTATION-5-safety.md` (S1 to S7),
`REFUTATION-5-liveness.md`, `FIX-round5-controller-report.md`.

---

## 0. Done-check, run after the last edit

```
$ cd /Users/khalil.maaouni/Documents/BrotherModeUp
$ python3 tools/test_bm_controller.py
...
Ran 146 tests in 9.554s

OK
EXIT=0
```

```
$ cd /Users/khalil.maaouni/Documents/BrotherModeUp/tools
$ python3 -m unittest -v \
    test_bm_controller.TestR6WriteScopePathspecMagicCannotReachGit \
    test_bm_controller.TestR6EngineRefusesMalformedScopeContainers \
    test_bm_controller.TestR6TheSpendBreakerStopsEveryCommand \
    test_bm_controller.TestR6AKillLandingDuringACommandRejects \
    test_bm_controller.TestR6TheExecutionPrimitiveGuardIsStructural \
    test_bm_controller.TestR6TheMeterCannotReadLowOnADeliveredRun
...
Ran 22 tests in 0.484s

OK
EXIT=0
```

**`python3 tools/test_bm.py` is RED, and NOT on behaviour.** Verbatim:

```
$ python3 tools/test_bm.py
======================================================================
FAIL: test_security_md_line_count_claim_is_still_true (__main__.TestProjectSecurityClaims)
SECURITY.md tells the reader how much code they have to audit, and
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_bm.py", line 1126, in test_security_md_line_count_claim_is_still_true
    self.assertLess(drift, 0.15,
AssertionError: 0.16321960216045317 not less than 0.15 : SECURITY.md claims about 76224 lines but the tools are 91092. Update the figure in SECURITY.md.

----------------------------------------------------------------------
Ran 276 tests in 43.775s

FAILED (failures=1, skipped=1)
EXIT=1
```

`SECURITY.md` is not in this writer's permitted file list, so it was not
touched. Measured so nobody has to guess whose lines did it:

| Tree | tools `*.py`+`*.sh` lines | drift vs the 76,224 claimed | verdict |
|---|---|---|---|
| HEAD (5afc895) | 88,740 | 14.10% | green |
| + the STORE writer's 931 | 89,671 | 15.00% | green by 0.00004 |
| + this writer's 1,421 | 91,092 | 16.32% | **RED** |

The gate had 0.9 points of headroom before either writer started and was
going to trip on whichever of us wrote second. **Remedy, one number:**
`SECURITY.md` line 101, change `the tools are about 76,224 lines of` to the
figure that file's own published command reports (91,092 at this capture).
It is a documentation refresh with no behaviour attached, and it needs an
owner who may write that file. Nothing else in `test_bm.py` is red.

`tools/test_all.py` and the store suite were NOT run, per the brief.

---

## 1. Per-finding table

| Finding | Sev | Verdict | Where |
|---|---|---|---|
| **S1**, a git pathspec in `write_scope` makes the rollback restore the whole working tree | HIGH, **PUSH BLOCKER**, data destruction | **CLOSED**, both halves, proved in a real git repo | `_pathspec_literal`, `_unsafe_scope_entry`, `_unsafe_scope_container`, `_refuse_bad_scopes`, `_unsafe_write_scope`, `_refuse_unsafe_scope`, `_rollback_plan`, `_warn_unrollbackable_scope`, `_authorise_dispatch`, `_validated_units` |
| **S2**, the spend breaker gates no command; a tripped ceiling still runs the founder's whole done-definition | HIGH, blocker candidate | **CLOSED**, with ONE documented carve-out forced by an existing test (section 3) | `_authorisation_refusal`, `_breaker_is_this_results_own_cost`, `_run_command`, `_verify_and_finish`, `_close_without_running`, `_settle_after_wave`, `_deliver_or_hold` |
| **S3**, a stop or revoke landing DURING the done_check is a non-move, so the unit is accepted under a killed contract | MEDIUM | **CLOSED**, both halves (the acceptance and the false note) | `_verify_and_finish` post-command re-read, `_reject_as_stale`, `_NOTE_CONTRACT_DIED_MIDCOMMAND`, `_NOTE_SETTLE_CONTRACT_NOT_LIVE`, `_settle_after_wave` |
| **S4**, a bare JSON string `write_scope` is iterated character by character | HIGH | **CLOSED** engine-side (store writer holds the declaration side) | `_unsafe_scope_container`, `_refuse_bad_scopes`; `read_scope` too, which also closes LV5-F5 |
| **S5**, the AST guard passes with four real ungated command sites | LOW | **CLOSED**, with the mutation evidence as the deliverable (section 4) | `_execution_primitive_offences` and its calibration test in `tools/test_bm_controller.py` |
| **S6**, `"write_scope": 7` is an uncaught TypeError out of the shipped `plan` | LOW | **CLOSED** engine-side, as a named refusal that leaves the run un-moved | `_unsafe_scope_container`, `_refuse_bad_scopes` |
| **S7**, the uncharged meter is the whole run's, and the run still delivers | HIGH reachability | **CLOSED by blocking delivery**, not by charging late; justified in section 5 | `SPEND_RECONCILE_LANE`, `_disclose_uncharged_spend`, `_unreconciled_uncharged_spend`, `_deliver_or_hold`, `_NOTE_SPEND_UNRECONCILED` |
| LV5-F6, `docs/FULL-AUTO.md` tells the founder the held meter is charged | LOW | **CLOSED** (it is a file this writer owns) | `docs/FULL-AUTO.md` |
| LV5-F5, a string `read_scope` is shredded into one-character paths | MEDIUM | **CLOSED**, same gate as S4 | `_refuse_bad_scopes` |
| The `test_bm.py` line-count gate | | **BLOCKED**, file outside this writer's list, remedy stated in section 0 | `SECURITY.md` line 101 |
| LV5-F1, F2, F3, F4, F7, F8, F9, AZ F7 | | **NOT ATTEMPTED**, out of scope by brief (liveness lens, disclosure items) | |

`CONTROLLER_STATE_TRANSITIONS` was not widened. `STOP_REASONS` was not
widened either: every reason word this round uses (`SPEND_STOP`,
`CONTRACT_NOT_LIVE`, `CONTRACT_PAUSED`, `FOUNDER_WAITING`) was already in
the enum.

---

## 2. S1, the push blocker, and its real-git-repo proof

### The two halves

**(a) The composed command.** `shlex.quote` protects the SHELL and does
nothing about GIT. `git restore -- ':/'` is a perfectly quoted command that
restores the entire working tree and **exits 0**, so the engine read the
rollback as a success and queued no dirty-write-scope warning at all.

I used **git's own literal escape, `:(literal)<path>`**, applied ONLY to an
entry that could be read as magic (one that begins with `:`; git's pathspec
magic is introduced by a leading colon and by nothing else). Why that
spelling and not the others:

* **`:(literal)` is honoured by this git.** Probed against a real
  repository, git 2.50.1 (Apple Git-155):

  ```
  $ git restore -- ':/'                       exit=0  keep=v1    other=v1
  $ git restore -- ':(literal):/'             exit=1  keep=EDIT  other=EDIT
      error: pathspec ':(literal):/' did not match any file(s) known to git
  $ git restore -- ':!keep.txt'               exit=0  keep=EDIT  other=v1
  $ git restore -- ':(literal):!keep.txt'     exit=1  keep=EDIT  other=EDIT
  $ git restore -- ':(literal)keep.txt'       exit=0  keep=v1    other=EDIT
  ```

  Every magic spelling becomes a literal path nothing matches, so it exits
  1 (which is also the dirty-write-scope warning path, so the founder now
  hears about it), and a plain path under the same escape behaves exactly
  as it always did.
* **`--pathspec-from-file` with NUL separation was not used.** It needs a
  file or stdin, and the `CheckRunner` seam this engine runs commands
  through takes a command string and a cwd and offers neither. Changing
  that seam is a bigger change than the fix needs, and the seam is the
  thing the S5 structural guard is built around.
* **`GIT_LITERAL_PATHSPECS=1` in the environment was not used** even though
  the same probe shows it works. It would apply to EVERY command the
  runner executes, including the founder's own `done_definition`, and a
  founder whose done-definition legitimately says
  `git diff --exit-code -- ':!vendor'` would silently get a different
  answer. A safety fix that quietly changes the meaning of the founder's
  own test suite is not a safety fix.
* **The escape is conditional on purpose, not out of laziness.** A path
  with no leading colon cannot be magic under any git version, so escaping
  it would change the founder-facing rollback command for every ordinary
  unit in the product, and six existing tests in
  `tools/test_bm_controller.py` script the exact string
  `"git restore -- a.py"`. Existing tests are law, so the emitted command
  for an ordinary unit is byte for byte the one round 5 emitted. The escape
  is still real code with its own tests, not a dead branch:
  `test_the_rollback_never_hands_git_a_magic_pathspec` asserts the escaped
  form for seven magic spellings and
  `test_a_plain_path_is_emitted_byte_for_byte_unchanged` pins the control.

**(b) The refusals.** A write scope entry that is not a plain relative path
inside the root is refused in three places, each with a named
founder-visible refusal and never a silent skip:

| Where | What happens |
|---|---|
| `plan` (`_validated_units` to `_refuse_bad_scopes`) | `OwnershipRefused('bad-scope', ...)` naming the unit, the entry and the reason, raised BEFORE the ORIENTING walk, so nothing is written and the run has not moved. The store refuses the same entry too, but inside `upsert_units`, one state walk too late, which leaves the run in `PLANNING` with nothing planned |
| `_authorise_dispatch` (`_unsafe_write_scope` to `_refuse_unsafe_scope`) | the unit is failed through the circuit breaker, a founder step naming the unit and the entry is queued in the unit's own lane (which also stops it being re-selected and re-refused every wave), an interruption is recorded, and an in-flight dispatch is closed with its fence parked |
| the rollback (`_rollback_plan`) | NO `git restore` is composed at all, and `_warn_unrollbackable_scope` queues a founder step saying the unit was NOT rolled back and its write scope needs manual inspection |

The refusal predicate is `_unsafe_scope_entry`: non-string, empty, leading
`:`, leading `-`, leading `~`, absolute, NUL or line break, and finally the
store's own `literal_scope_entry` (globs). Plus `bs.canonicalize_path` at
plan time, which refuses anything resolving outside the root.

### The proof, in a REAL temp git repository

`pS1_realgit.sh`, a throwaway repo per row with three tracked files all
carrying uncommitted founder edits, driven through the SHIPPED command line
(`bm_store init`, `bm_project start`, `bm_autonomy sign --allowed-path .`,
`bm-controller start`, `plan`, `step`) with the round-5 reproduction's own
unit (`done_check` is `false`, so the unit is rejected and rolled back).

**A. The control, so the hazard is shown to be real before it is shown to
be closed.** Round 5's own composed command, in the same repo shape:

```
  $ git restore -- ':/'          (round 5, write_scope [":/"])
    exit=0
    keep.txt      = v1
    src/app.py    = v1
    docs/notes.md = v1

  $ git restore -- ':(literal):/'   (round 6's composed rollback)
error: pathspec ':(literal):/' did not match any file(s) known to git
    exit=1
    keep.txt      = FOUNDER UNCOMMITTED EDIT
    src/app.py    = FOUNDER UNCOMMITTED EDIT
    docs/notes.md = FOUNDER UNCOMMITTED EDIT

  $ git restore -- ':!keep.txt'          (round 5)
    exit=0
    keep.txt      = FOUNDER UNCOMMITTED EDIT
    src/app.py    = v1
    docs/notes.md = v1

  $ git restore -- ':(literal):!keep.txt'   (round 6)
error: pathspec ':(literal):!keep.txt' did not match any file(s) known to git
    exit=1
    keep.txt      = FOUNDER UNCOMMITTED EDIT
    src/app.py    = FOUNDER UNCOMMITTED EDIT
    docs/notes.md = FOUNDER UNCOMMITTED EDIT
```

**B. The round-5 reproduction, re-run through the shipped CLI.** Verbatim,
the `:!keep.txt` row:

```
--- write_scope [":!keep.txt"] ---
  founder tree BEFORE the controller runs:
    keep.txt      = FOUNDER UNCOMMITTED EDIT
    src/app.py    = FOUNDER UNCOMMITTED EDIT
    docs/notes.md = FOUNDER UNCOMMITTED EDIT
  $ bm-controller plan --units-file units.json
    | bm_controller: refused: unit 'u1' cannot be planned: its write_scope entry ':!keep.txt' begins with ':', which git reads as PATHSPEC MAGIC rather than as a file name (':/' is the repository root and ':!x' is 'everything except x'), so a rollback naming it would restore files this unit never declared. Nothing was written and the run has not moved; name the files, or name the directory they live in, which grants its whole subtree.
  $ bm-controller step   (round 5: dispatch, run `false`, roll back)
    | run e66db679c26f4d158ba5a8fa6f1f7b83: state NEW
    | dispatched: (none)
    | completed: (none)
    | note: the done-definition was not run: the run is NEW, which only a founder can move (bm-controller resume, complete or stop it)
    | reason: FOUNDER_WAITING
  founder tree AFTER:
    keep.txt      = FOUNDER UNCOMMITTED EDIT
    src/app.py    = FOUNDER UNCOMMITTED EDIT
    docs/notes.md = FOUNDER UNCOMMITTED EDIT
  git status --short:
     M docs/notes.md
     M keep.txt
     M src/app.py
```

The `:/` row is identical in shape (refused, run still `NEW`, all three
founder edits intact). The plain-path control still plans and dispatches
normally:

```
--- write_scope ["src/app.py"] ---
  $ bm-controller plan --units-file units.json
    | planned 1 unit(s) for run 5b6d5f6e97a448e2af1918ccfa4ba200
  $ bm-controller step
    | {"controller_brief": {..., "write_scope": ["src/app.py"]}}
    | run 5b6d5f6e97a448e2af1918ccfa4ba200: state EXECUTING
    | dispatched: u1
```

**C. The EXECUTION side, which is the half this writer owns.** The
declaration side now refuses in two places, so the CLI proof above never
reaches a rollback. `pS1_execution_side.py` therefore poisons the row AFTER
dispatch, through a pass-through Store proxy standing in for a hand-written
row, an older store or an SDK caller, in a REAL git repo with the REAL
`SubprocessCheckRunner` (every command below genuinely executes):

```
--- poisoned write_scope [":/"] reaches the engine after dispatch ---
  tree BEFORE : {'keep.txt': 'FOUNDER UNCOMMITTED EDIT', 'src/app.py': 'FOUNDER UNCOMMITTED EDIT'}
  the unit's done_check is `false`, so this is the rejection path that rolls back
  commands the engine REALLY executed: ['false']
  outcome     : rejected
  tree AFTER  : {'keep.txt': 'FOUNDER UNCOMMITTED EDIT', 'src/app.py': 'FOUNDER UNCOMMITTED EDIT'}
  founder step: ["unit u1 was NOT rolled back: its write_scope entry ':/' begins with ':', which git reads as PATHSPEC MAGIC rather than as a file name (':/' is the rep"]

--- poisoned write_scope [":!keep.txt"] ---
  commands the engine REALLY executed: ['false']
  tree AFTER  : {'keep.txt': 'FOUNDER UNCOMMITTED EDIT', 'src/app.py': 'FOUNDER UNCOMMITTED EDIT'}
  founder step: ["unit u1 was NOT rolled back: its write_scope entry ':!keep.txt' ..."]

--- CONTROL: the clean row ["src/app.py"] ---
  commands the engine REALLY executed: ['false', 'git restore -- src/app.py']
  tree AFTER  : {'keep.txt': 'FOUNDER UNCOMMITTED EDIT', 'src/app.py': 'v1'}
  founder step: []
```

The control is the important line: the ordinary rollback still runs, with
the identical command string, and restores only the file the unit declared.

### Not re-checked, and I am naming it

`tools/bm_fence_hook.py`'s covering check is the third reader
`literal_scope_entry`'s docstring names, and it is not in this writer's
file list. It was not read or run this round. The refuter's own S1 note
says a fence over `:!keep.txt` protects nothing; with both refusals in
place no such fence can be claimed through `bm-controller plan` any more,
but I did not drive the hook to see it.

---

## 3. S2, the second brake, and the one carve-out an existing test forced

### The rule as implemented

`_run_command` no longer asks "is the contract row live". It asks
`_authorisation_refusal`, which asks the three questions `gate_check` would
refuse for at that instant:

| Question | Refusal | What it now does to the run |
|---|---|---|
| **STATE**: no contract, or paused, stopped, revoked | `REFUSED-NO-CONTRACT` / `REFUSED-STATE` | unchanged from round 5. A paused contract HOLDS the answer (`CONTRACT_PAUSED`); a stopped, revoked or missing one closes without running: rejected verification, unit back through the circuit breaker, fence parked, founder step naming the unit and the dead contract, reason `CONTRACT_NOT_LIVE` |
| **BREAKER**: spend at or over 100 percent of either ceiling | `REFUSED-BREAKER` | NEW. No command runs: not the done_check, not the verifier, not the rollback, not the founder's whole done-definition. The result is closed without running with the breaker's own sentence, a founder step names the unit, the reason is `SPEND_STOP`, and `_settle_after_wave` and `_deliver_or_hold` both stop there too, so no deliverable is declared. `step`'s existing step-3 gate drains the run on the next call |
| **SCOPE**: the unit's whole write scope under one contract revision, via the SAME `_gate_check_write_scope` the dispatch route uses | `REFUSED-SCOPE`, `REFUSED-CLASS`, `REFUSED-FLOOR`, `DEFERRED-CONTENTION` | NEW for the judging path. Closed without running, reason `FOUNDER_WAITING`, note naming what the live contract now refuses. A command run for a unit whose paths the contract no longer admits is a command run outside the contract, whichever direction it writes in |

CLASS and FLOOR are deliberately NOT re-asked when there is no unit (the
founder's own `done_definition`): they are per-unit questions already
answered at dispatch, and the founder's test suite is not a model action
bounded by the risk classes the founder granted the model. Asking them
there would refuse delivery on perfectly valid contracts.

### The collision, and the carve-out it forced

The first version of this fix turned an EXISTING test red. Verbatim:

```
FAIL: test_hard_stop_drains_and_starts_no_new_unit (test_bm_controller.TestFault6CostCeilingReached)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_bm_controller.py", line 621, in test_hard_stop_drains_and_starts_no_new_unit
    self.assertEqual(
AssertionError: 'READY' != 'DONE'
- READY
+ DONE
```

That test's `u1` reports a cost of 100 tokens against a 10 token ceiling,
and the engine charges the meter BEFORE it judges a result (REFUTATION-3 SM
C moved the charge there deliberately, so a late result cannot drop its
spend). So the breaker the gate read a moment later was tripped by `u1`'s
OWN cost, and `u1` was refused its own done_check.

**The test was not edited.** The fix was narrowed instead, and by a rule
rather than an exception: `_breaker_is_this_results_own_cost`. The breaker
refuses every command UNLESS subtracting the spend row this same call just
wrote for this same unit puts both meters back under their ceilings, in
which case the one already-paid unit in flight is still judged.

Why that is a rule and not a fudge:

* it is a **computation over what was durably written**, not a switch a
  caller sets. The value comes from `_record_spend`'s return, which is what
  `Store.record_spend` actually charged. Nobody can pass a number to loosen
  the gate without the meter carrying that same number;
* the founder's ceiling limits what may be SPENT, and this money is already
  spent. Refusing to read an answer that is already paid for destroys it
  and burns a retry without saving a token;
* it is bounded to exactly ONE unit, the one already in flight. `step`'s
  own breaker gate drains the whole run on the next call, and
  `_deliver_or_hold` refuses to declare a deliverable, both of which this
  round's tests pin;
* **the refuted sequence is untouched**, which is the test of whether the
  carve-out is honest. In REFUTATION-5 S2 the ceiling was blown by a
  separate `bm-autonomy spend` BEFORE `bm-controller record-result`, and
  the record-result supplied no cost at all, so there is nothing to
  subtract and the refusal stands. `TestR6TheSpendBreakerStopsEveryCommand`
  reproduces exactly that and now measures zero commands on both of the
  refuter's legs (the accepting one and the rollback one).

The residual is disclosed in `docs/KNOWN-LIMITS.md` in these words: a
caller that self-reports an enormous cost buys the judgement of the one
unit already in flight, it buys nothing else, and it pays the meter in full
to do it.

One second-order detail worth naming: `Store.gate_check` asks the breaker
LAST (its own check 7, after the path check at 5), so a `REFUSED-BREAKER`
verdict coming back from the SCOPE half means every path already passed.
`_authorisation_refusal` therefore honours the same exemption there, or the
carve-out would have been re-imposed through the back door. That is written
into the code as a comment, not left to be rediscovered.

---

## 4. S3, the kill that lands mid-command, and S5, the guard

### S3

`_verify_and_finish` now re-reads the whole authorisation AFTER the
done_check returns and BEFORE anything is accepted. A contract that died or
moved during execution rejects through `_reject_as_stale`, the SAME
sequence the ordinary staleness branch uses (rejected verification carrying
the real exit code, unit back through the circuit breaker, rollback and
warning, fence parked), not a lookalike of it. `_LIFECYCLE_CHANGE_KINDS` is
UNCHANGED: "did the authorisation change" and "is there still an
authorisation" are different questions, and the method now asks both.

S3's second half was a note constant serving two branches whose facts
differ: `_settle_after_wave` reused `_NOTE_CONTRACT_NOT_LIVE`, whose text
hard-codes "NO command was executed", about a wave that may well have just
run a command. The settle path has its own note now
(`_NOTE_SETTLE_CONTRACT_NOT_LIVE`), and the mid-command kill has a third
(`_NOTE_CONTRACT_DIED_MIDCOMMAND`), which is deliberately the one note in
the file that says a command DID run. `test_the_founder_note_does_not_claim_nothing_ran`
asserts the done_check really ran (`checker.calls == ['true']`) and that
the founder-facing note does not contain the words "NO command was
executed".

### S5, and the four mutation failures

The round-5 guard matched ONE AST shape. The round-6 guard
(`_execution_primitive_offences` in `tools/test_bm_controller.py`) asks the
question the claim actually makes:

* `subprocess.*` may be called in exactly one qualified name,
  `SubprocessCheckRunner.run`;
* a list of dotted process-starting calls (`os.system`, `os.popen`, the
  `exec*`/`spawn*` family, `pty.spawn`, `asyncio.create_subprocess_*`, and
  more) may be called nowhere;
* the bare builtins that turn a name into an object at runtime (`getattr`,
  `setattr`, `vars`, `globals`, `eval`, `exec`, `compile`, `__import__`)
  may be called nowhere;
* the attribute names that reach an object's own namespace (`__dict__`,
  `__getattribute__`, `__class__`, `__globals__`) may appear nowhere;
* `self.checker` may appear in exactly two places: bound as an assignment
  target in `ControllerEngine.__init__`, and called as
  `self.checker.run(...)` inside `ControllerEngine._run_command`. Anything
  else, including an alias, is an offence.

**The mutation evidence, which is the deliverable.** Each of the refuter's
four spellings is spliced into a COPY of `tools/bm_controller.py` held in
memory. The repo file is never written and none of the mutant code is ever
executed: the only thing done with it is `ast.parse`.

```
==========================================================================
ROUND 5's GUARD (test_every_checker_call_sits_behind_one_gated_call_site)
==========================================================================
as shipped (no mutation)                             -> GUARD PASSES  enclosing=['_run_command']
subprocess.run() added inline in _verify_and_finish  -> GUARD PASSES  enclosing=['_run_command']
os.system() added inline in _verify_and_finish       -> GUARD PASSES  enclosing=['_run_command']
getattr(self.checker, 'run') in _verify_and_finish   -> GUARD PASSES  enclosing=['_run_command']
runner = self.checker; runner.run(...) in _verify_and_finish -> GUARD PASSES  enclosing=['_run_command']

==========================================================================
ROUND 6's GUARD (_execution_primitive_offences)
==========================================================================
as shipped (no mutation)                             -> GUARD PASSES
subprocess.run() added inline in _verify_and_finish  -> GUARD FAILS
       line 2756  subprocess.run() is called in ControllerEngine._verify_and_finish; the only place this module may start a process is SubprocessCheckRunner.run
os.system() added inline in _verify_and_finish       -> GUARD FAILS
       line 2756  os.system() starts a process outside the CheckRunner entirely (in ControllerEngine._verify_and_finish)
getattr(self.checker, 'run') in _verify_and_finish   -> GUARD FAILS
       line 2756  getattr() in ControllerEngine._verify_and_finish can reach a gated attribute without naming it
       line 2756  self.checker is reached in ControllerEngine._verify_and_finish; it may only be bound in ControllerEngine.__init__ and called as self.checker.run(...) in ControllerEngine._run_command
runner = self.checker; runner.run(...) in _verify_and_finish -> GUARD FAILS
       line 2756  self.checker is reached in ControllerEngine._verify_and_finish; it may only be bound in ControllerEngine.__init__ and called as self.checker.run(...) in ControllerEngine._run_command
```

The same four mutations are a PERMANENT calibration test
(`test_each_of_the_four_bypass_spellings_fails_the_guard`), so a guard
that stops failing fails the suite. Round 5's own property is kept beside
it, not replaced: `_checker_call_site_functions()` is still asserted to be
exactly `{"_run_command"}`. The splice anchor is the `def` line PREFIX, not
the whole signature, so a future argument added to `_verify_and_finish`
cannot silently turn the calibration into a no-op (it did exactly that once
during this round, and the assertion caught it).

---

## 5. S7, the uncharged meter: which half I chose, and why

The brief offered two closures. I took the second: **the run cannot
complete while any accepted unit's cost was never metered.**

Why not "charge when the hold resolves": the number is GONE by then.
`Store.record_result` carries no cost column, so charging late would mean
re-deriving a founder's money from the prose of a checkpoint note I wrote
myself, and `tools/bm_store.py` is another writer's file this round. Adding
a column is the right fix and it is not mine to make.

What landed:

* `_disclose_uncharged_spend` keeps its checkpoint AND queues a founder
  step naming the exact tokens and minutes, the `bm-autonomy spend`
  command that charges them, and the `bm-autonomy human-steps --resolve`
  command that closes it;
* the step goes in `SPEND_RECONCILE_LANE`, a reserved lane no unit is
  planned into. That answers round 5's own stated objection to using a
  founder step at all ("it would block the very lane the founder is about
  to resume"): `Store.select_ready_units` skips lanes holding an open step,
  and a lane with no units skips nothing.
  `test_the_reserved_lane_blocks_no_unit_of_the_run` pins that the held
  unit is still judged and accepted after the resume;
* `_deliver_or_hold` refuses to run the done-definition or declare
  `DELIVERABLE_READY` while any such step is open, with reason
  `SPEND_STOP`;
* the reader is `list_human_steps`, which takes NO limit, deliberately
  chosen over `recent_checkpoints`, which has a window a long run's
  heartbeats would push an old disclosure out of. A question whose answer
  decides whether a founder's ceiling means anything is not a question to
  answer through a window.

**Why a breaker that reads low is now unreachable through the shipped
commands.** The only route to an uncharged cost is a result recorded while
the contract is not live, which is the one place `_record_spend` skips the
charge, and that is the one place that now queues the step. So every
uncharged token has an open step, and every open step blocks delivery. The
way out is two shipped commands (`bm-autonomy spend`, then
`bm-autonomy human-steps --resolve`), not a wedge:
`test_reconciling_the_gap_lets_the_run_deliver` drives exactly that and
reaches `DELIVERABLE_READY`.

The refuter's own magnitude correction is now in `docs/KNOWN-LIMITS.md` in
their words rather than the old ones: not "one unit's cost" but every
result recorded during a pause, without limit.

---

## 6. The RED capture, and what it shows

`docs/program/absolute-lead/evidence/L03/RED-round6-controller.txt` holds,
per class, the verbatim failures of every new test against the untouched
controller: **22 tests, 18 red (14 failures, 4 errors)**, plus the four
that were green at capture and are labelled as controls. The most direct
lines in it:

* S1: `AssertionError: Lists differ: ['git restore -- :/'] != []` with the
  message `no rollback is composed from a poisoned scope: ['true', 'git
  restore -- :/']`;
* S2: `AssertionError: Lists differ: ['true', 'echo done'] != []` (the
  unit's done_check and the founder's whole done-definition, both under a
  tripped ceiling) and `'DELIVERED' != 'SPEND_STOP'`;
* S3: `AssertionError: 'u1' != 'rejected'` (the unit accepted under a
  killed contract) and the note assertion quoting the whole false sentence;
* S7: `AssertionError: 'DELIVERABLE_READY' == 'DELIVERABLE_READY'` with the
  full delivered summary, verdict `DELIVERED`, zero founder steps.

S5's RED capture is the mutation table in section 4 rather than a failing
class, because that finding refutes a CLAIM about the guard rather than the
shipped file, and the round-5 guard passing four ungated command sites IS
the failure.

Both collisions are recorded there verbatim too: the
`TestFault6CostCeilingReached` one with its resolution, and the
`test_bm.py` line-count one with its measured attribution and its one-line
remedy.

---

## 7. What I did NOT check, and what is only partly checked

* **`tools/test_all.py` and the store suite were not run**, per the brief.
  I make no claim about either.
* **`python3 tools/test_bm.py` does not pass**, on `SECURITY.md`'s line
  count, a file outside this writer's list. Section 0 has the numbers and
  the remedy. Nothing else in that suite is red.
* **`tools/bm_fence_hook.py` was not read or run.** It is the third reader
  of a write scope named in `literal_scope_entry`'s docstring, it is
  outside this writer's file list, and REFUTATION-5 S1 and S4 both touch
  it. My claim is only that no pathspec entry and no character-shredded
  entry can now be claimed as a fence through `bm-controller plan`.
* **The liveness lens was not worked.** LV5-F1 (no way back after the kill
  switch), F2, F3, F4, F7 (the 2000-revision window), F8, F9 and AZ F7 are
  untouched; the brief scoped me to the safety findings. LV5-F5 and LV5-F6
  are closed only because they fall inside `_validated_units` and
  `docs/FULL-AUTO.md`, which are mine.
* **The scope half of the new gate is a behaviour change on the judging
  path.** A unit whose write scope the live contract no longer admits now
  has its done_check refused rather than run and then rejected as stale.
  `test_a_real_amend_across_the_pause_is_still_stale` (round 5's own
  control) still passes, and the founder-facing outcome is the same
  rejection, but the ROUTE differs and I did not enumerate every shape that
  reaches it.
* **Three extra store reads per judged command.** The re-read after each
  command is deliberate (it is what makes the moment of execution the
  moment of authorisation), and I did not measure its cost on a large
  store.
* **`E4-endtoend.json` shows as modified.** That artifact is regenerated by
  every run of `TestEndToEndE4`, by that test's own documented design; it
  was already modified in the working tree before this writer started.
* **Concurrency.** Every probe and every test here is single-process. Two
  controllers stepping the same project at once was not exercised.
* **Platforms.** Everything ran on darwin with git 2.50.1 (Apple
  Git-155). The `:(literal)` behaviour is not platform specific, but the
  exact exit codes were observed on this machine only.
