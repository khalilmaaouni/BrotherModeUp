# REFUTATION 6, the FINAL PUSH GATE for the L03 controller

## PUSH VERDICT: NO PUSH-BLOCKER

Round 6's two commits (5afc895, then 1e40b8e) clear the bar this gate was
given. I attacked all five claims with reproductions and could not produce
a HIGH finding, reachable from a shipped command, that executes something
the founder forbade, authorises a write outside the contract, or destroys
founder data.

**S1, the round-5 push blocker, is genuinely closed on both sides.** I ran
56 write-scope spellings through the store gate, the engine gate and then a
REAL `git restore` in a fresh throwaway repository per row, plus poisoned
rows that never passed `plan`, driven through all three rollback call sites
with the real subprocess runner. Nothing both survives the two gates and
makes git touch a file the unit did not declare.

**S2's substance is closed.** The round-5 sequence now runs zero commands,
a second unit cannot ride the carve-out, the founder's done-definition
never runs under it, spend exactly AT the ceiling refuses, and a refused
SCOPE and a dead contract each stop every command.

Six findings sit below the bar and are disclosure items. Two are HIGH and
both contradict shipped founder-facing documentation, so they want fixing
or writing down rather than leaving:

* **F1**, S3 is closed for the done_check window and OPEN for the VERIFIER
  window. A stop or revoke landing during a unit's model-authored
  `verifier` is never re-asked, so the unit is accepted under a killed
  contract with zero founder steps. Reproduced at the shipped CLI with a
  real second process.
* **F2**, on the carve-out path the shipped `record-result` tells the
  founder "NO command was run for this result" while the unit's done_check,
  its verifier and a `git restore` in the working tree all ran in that same
  call. `docs/FULL-AUTO.md` says in as many words: "The controller never
  tells you nothing ran when something did."

---

## VERDICTS, one line each

| Claim under attack | Verdict |
|---|---|
| S1 (a): the rollback is built so git cannot read a path as a pattern | **STANDS**. 56 spellings against real git; every magic spelling that reaches git at all exits 1 and reverts nothing (probes A1, A1b) |
| S1 (b): the engine refuses unsafe entries independently of the store | **STANDS**. Poisoned `[':/']`, `[':!keep.txt']`, `['../x']`, `['']`, `'a.py'` rows all reach `_rollback_plan` and compose NO command; a founder step is queued each time (probe E3) |
| S1: `plan` refuses before the run moves | **STANDS** for a leading colon (run stays NEW). Partly, for the re-spelled `./:!x` family: only the STORE catches those, so the run reaches PLANNING. Not a wedge, `plan` again recovers (probe A8) |
| S1: no route reaches the rollback without the refusal | **STANDS**. `git restore` is composed at exactly one line (`:3183`); `_handle_late_result`, `_reject_as_stale`, `_reject` and `check_timeouts` all reach it through `_rollback_plan`, which asks `_unsafe_write_scope` first |
| S1: no shell injection through `write_scope` | **STANDS**. Six metacharacter spellings through the REAL runner in a real repo; `PWNED=False` every time (probe E2) |
| S2: "a tripped breaker, a refused scope and a dead contract each stop every command" | **STANDS**. Round 5's own sequence: zero commands, no delivery (probe A2 case 1). Refused SCOPE: zero commands (E1). Dead contract: zero commands (A5 part 3) |
| S2: the carve-out is bounded to ONE already-paid unit | **STANDS**. A second unit is refused, the meter carrying the first unit's cost (probe C1) |
| S2: the founder's whole done-definition never runs under the carve-out | **STANDS** (probes C2, A2 cases 2 and 3): `_deliver_or_hold` passes no `charged`, so the exemption cannot reach it |
| S2: spend exactly AT the ceiling refuses | **STANDS** (A2 case 4 refuses at 100 of 100; case 5 at 99 allows) |
| S3: "CLOSED, both halves ... re-reads the whole authorisation AFTER the done_check returns and BEFORE anything is accepted" | **REFUTED**, F1. The re-read sits before the VERIFIER, not before the acceptance |
| `docs/KNOWN-LIMITS.md`: "The mid-command kill re-reads the authorisation after every command" | **REFUTED**, F1. It re-reads after the done_check only |
| `docs/FULL-AUTO.md`: "The controller never tells you nothing ran when something did" | **REFUTED**, F2 |
| S5: "four bypass spellings now FAIL the guard" | **STANDS**, reproduced independently in a scratch copy (probe A5 part 1) |
| S5: the guard makes an ungated command site fail by construction | **REFUTED**, F3. Five more spellings PASS; four of them really start a process under a revoked contract |
| S4/S6 engine side: both scopes must be a list of paths | **STANDS** for str, int, dict, set, bytes; tuple accepted, an absent key means no scope (probe D3) |
| The store report's disclosed `read_scope` gap is closed by the engine | **STANDS**. `_refuse_bad_scopes` asks the container question BEFORE `_validated_units` canonicalises, so a bare string never reaches the store as one-character paths (probe D3) |
| S7: a run cannot be delivered while an accepted unit's cost was never metered | **STANDS** (probe D1: `SPEND_STOP`, delivery refused) |
| S7: `spend-reconciliation` is "a reserved lane no unit is ever planned into" | **REFUTED**, F5. `plan` accepts it, and any step in it blocks delivery citing spend that was never uncharged |
| `_authorisation_refusal`'s new SCOPE half is total | **REFUTED**, F4. A non-iterable `write_scope` is an uncaught TypeError out of `receive_result` |

Severity key: HIGH means reachable from a shipped command. LOW means it
needs a row or a source edit no shipped command produces.

---

# THE FINDINGS

## F1 (HIGH, not a blocker) S3 is closed for the done_check and OPEN for the verifier: a kill landing during the VERIFIER accepts the unit under a killed contract

### The claim being refuted

`FIX-round6-controller-report.md` section 1: "**S3** ... **CLOSED**, both
halves". Section 4: "`_verify_and_finish` now re-reads the whole
authorisation AFTER the done_check returns and BEFORE anything is
accepted."

`docs/KNOWN-LIMITS.md`: "**The mid-command kill re-reads the authorisation
after every command.**"

`docs/FULL-AUTO.md`, the founder-facing page: "A kill that lands WHILE a
command is running is handled too, and honestly."

### The code

`tools/bm_controller.py`, inside `_verify_and_finish`:

```
:2766   outcome = self._run_command(project_id, unit["done_check"] ...)
:2780   after = self._authorisation_refusal(project_id, unit, charged)   <- the round 6 re-read
:2795   moved, latest_revision = self._authorisation_moved(...)
:2807       v_outcome = self._run_command(project_id, unit["verifier"], ...)
:2821   self.store.record_verification(... accepted ...)
:2826   checkpoint_id = self.store.record_checkpoint(... "unit-green" ...)
:2829   self.store.mark_unit_done(...)
:2831   self._release_fence(claimed["fence_uuid"], "complete", "unit green")
```

The re-read is at `:2780`. The verifier runs at `:2807`. Between `:2807`
and the acceptance at `:2821` nothing is asked again. `_run_command` asks
the authorisation BEFORE it runs the verifier, which covers a kill landing
before the verifier starts and misses one landing while it runs. In full
auto the verifier is model-authored shell, so its duration is unbounded,
which is exactly the argument REFUTATION-5 S3 made about the done_check.

### Reproduction A, deterministic, all four kill words, both windows

The kill is fired by the CheckRunner itself when a NAMED command executes,
so it lands at a precisely named instant rather than by luck. Own
throwaway store per row.

```
$ python3 p5_s3_windows.py
==========================================================================
S3 window A: the kill lands during the DONE_CHECK (round 6's fix)
==========================================================================
revoke during done_check, unit HAS a verifier
   contract now : revoked
   commands ran : ['CHECK']
   outcome      : rejected  unit=READY    dispatch=REJECTED
   accepted-as-DONE=False        open founder steps: 1

stop during done_check      -> rejected, unit READY, 1 founder step
pause during done_check     -> rejected, unit READY, 1 founder step
amend during done_check     -> rejected, unit READY, 1 founder step

==========================================================================
S3 window B: the kill lands during the VERIFIER, that is, AFTER the
round-6 re-read and BEFORE the acceptance
==========================================================================
revoke during the VERIFIER
   contract now : revoked
   commands ran : ['CHECK', 'VERIFY']
   outcome      : u1        unit status DONE, dispatch VERIFIED
   verifier_verdict='pass'  accepted-as-green=True
   open founder steps: 0

stop during the VERIFIER    -> unit green, verdict 'pass', 0 founder steps
pause during the VERIFIER   -> unit green, verdict 'pass', 0 founder steps
amend during the VERIFIER   -> unit green, verdict 'pass', 0 founder steps,
                               and the run then ran the founder's whole
                               done-definition and reached DELIVERABLE_READY
                               under a contract that no longer admits the
                               unit's write scope
```

### Reproduction B, end to end, shipped CLI, a REAL second process

The unit's `verifier` IS `python3 tools/bm_autonomy.py revoke --project
p1`, a real subprocess, which is a faithful stand-in for the founder
revoking in another terminal while the verifier runs. This is the technique
REFUTATION-5 used for the done_check.

```
$ bash p6_s3_cli.sh
=== kill lands during the DONE_CHECK (round 6 closed this) ===
    dispatch 4e76a340... rejected; the unit re-queues for one retry or escalates
    reason: CONTRACT_NOT_LIVE
  unit status    : READY
  dispatch status: REJECTED   verifier_verdict='the contract became revoked
                   while unit u1 was being checked ... the result is rejected
                   rather than accepted'
  open founder steps: 1

=== kill lands during the VERIFIER (one command later) ===
    unit u1 accepted (dispatch 341e77ee...)
    reason: CONTRACT_NOT_LIVE
  unit status    : DONE
  dispatch status: VERIFIED   verifier_verdict='pass'
  run state      : CHECKPOINTED
  open founder steps: 0
```

The founder pulled the switch, the unit is green, the fence is released
`complete`, the dispatch says `pass`, and no founder step names any of it.
The note that same command prints says "a founder step names any unit that
was rejected", and there are zero steps because nothing was rejected.

### Why it is NOT a push blocker

The verifier started under a live authorisation, so nothing forbidden was
executed at the moment it started. No new write is authorised: the unit is
finished, and the next `step` finds the contract dead and drains. Nothing
is destroyed. It is the same MEDIUM shape REFUTATION-5 gave S3, one command
further along, and its real cost is that three shipped sentences (the FIX
report, `KNOWN-LIMITS.md` and `FULL-AUTO.md`) claim it cannot happen.

### Smallest fix

Ask `_authorisation_refusal` once more immediately before
`record_verification` at `:2821`, and route a refusal there through the
same `_reject_as_stale` the done_check window already uses. One call and
one branch, and the property the docs already state becomes true for every
command rather than for the first one.

---

## F2 (HIGH, not a blocker) The founder is told NO command ran, in the same command in which three ran

### The claim being refuted

`docs/FULL-AUTO.md`: "The controller never tells you nothing ran when
something did."

`FIX-round6-controller-report.md` section 4 records the identical defect
class as CLOSED for the contract note: "`_settle_after_wave` reused
`_NOTE_CONTRACT_NOT_LIVE`, whose text hard-codes 'NO command was executed',
about a wave that may well have just run a command. The settle path has its
own note now."

### The code

`_NOTE_SPEND_BREAKER` is defined at `tools/bm_controller.py:500` and its
text hard-codes the "nothing ran" branch:

```
    "the founder's SPEND CEILING has tripped, so nothing is authorised and "
    "NO command was run for this result: not the unit's done_check, not "
    "its verifier, not the rollback and not the whole done-definition (%s)."
```

Three use sites: `:2957` (`_close_without_running`, where it is true), and
`:3291` (`_settle_after_wave`) and `:3675` (`_deliver_or_hold`), where the
same wave may have just executed commands. The fix applied to
`_NOTE_CONTRACT_NOT_LIVE` was not applied to the note this round
introduced.

### Reproduction, shipped CLI, markers on disk

Ceiling 100 tokens. The unit's `done_check` and the contract's
`done_definition` are `touch` commands, so execution is a file.

```
$ bash p3_s2_cli.sh
=== carve-out: pre-spend 99, result claims 5 ===
  gate-check says: ALLOWED
  --- record-result ---
    unit u1 accepted (dispatch f166abbd...)
    note: the founder's SPEND CEILING has tripped, so nothing is authorised
    and NO command was run for this result: not the unit's done_check, not
    its verifier, not the rollback and not the whole done-definition (spend
    is at or over 100 percent of a ceiling (104 token(s) of 100 ...))
    reason: SPEND_STOP
  done_check ran      : YES
  done_definition ran : NO
```

The marker file says the done_check ran. The note says it did not.

In process, with the command tape, on the rejection leg where the rollback
also runs:

```
$ python3 p4_carveout.py
C3  what EXACTLY runs under the carve-out
  receive_result -> rejected
  commands the engine REALLY ran: ['CHECK-u1', 'VERIFY-u1', 'git restore -- a.py']
  note: the founder's SPEND CEILING has tripped ... NO command was run for
        this result: not the unit's done_check, not its verifier, not the
        rollback and not the whole done-definitio...
```

Three commands, one of them a `git restore` in the founder's working tree,
and one sentence naming all three as not having run.

### Why it is NOT a push blocker

The commands themselves are the documented carve-out and `KNOWN-LIMITS.md`
describes them accurately. Nothing outside the unit's declared write scope
is touched, no new work starts, and no deliverable is declared. What fails
is the report to the founder, which is a disclosure defect rather than one
of the three blocker clauses.

### Smallest fix

Give `_settle_after_wave` and `_deliver_or_hold` their own breaker note, as
round 6 already did with `_NOTE_SETTLE_CONTRACT_NOT_LIVE` at `:475`. The
delivery one only has to say the done-definition did not run and no
deliverable was declared, which is the only thing that branch knows.

---

## F3 (LOW) The rebuilt structural guard is still overstated: five more spellings pass it, four of them really start a process

### What I verified first

The FIX report's own claim is true. I re-ran the four round-5 spellings
against `_execution_primitive_offences` in a SCRATCH COPY of
`tools/bm_controller.py` held in memory; the repo file was never written
and no mutant code was executed at this stage.

```
$ python3 p7_s5_guard.py
R5-1  subprocess.run() inline                    -> GUARD FAILS
R5-2  os.system() inline                         -> GUARD FAILS
R5-3  getattr(self.checker, 'run')               -> GUARD FAILS
R5-4  runner = self.checker; runner.run(...)     -> GUARD FAILS
as shipped (no mutation)                         -> GUARD PASSES
round 5's own property, _checker_call_site_functions() = ['_run_command']
```

### The fifth spelling, and four more

`_dotted_name` (`tools/test_bm_controller.py:3722`) builds the name from
the LOCAL identifier, and the guard then tests `root == "subprocess"` or
membership in `_BANNED_DOTTED_CALLS`. Neither survives an import alias, and
nothing in the guard reads `ast.Import` or `ast.ImportFrom` at all.

```
NEW-A from subprocess import run as X;  X(cmd, shell=True)   -> GUARD PASSES
NEW-B import subprocess as sp;          sp.run(cmd, ...)     -> GUARD PASSES
NEW-C from os import system as X;       X(cmd)               -> GUARD PASSES
NEW-D operator.attrgetter("checker")(self).run(cmd, ...)     -> GUARD PASSES
NEW-E import subprocess as _sp;         _sp.Popen(cmd, ...)  -> GUARD PASSES
```

NEW-D passes because the gated attribute is reached as a STRING rather than
as an `ast.Attribute`, and because `attrgetter(...)(self).run` is not a
plain dotted chain, so `_dotted_name` returns None.

### The mutants really run an ungated command

Each passing mutant was written to a THROWAWAY temp file, imported from
there (never the repo file), and driven with a REVOKED contract. The
bypass command is `touch <marker>` inside the same temp directory.

```
PART 3: does a PASSING spelling really run an ungated command?
  NEW-A  contract: revoked  receive_result -> 'rejected'
         gated CheckRunner calls : []
         UNGATED command really ran (marker on disk): True
  NEW-B  ... marker on disk: True
  NEW-C  ... marker on disk: True
  NEW-D  gated CheckRunner calls : ['touch .../UNGATED_COMMAND_RAN']
         (it reached the checker object and called it OUTSIDE the gate; the
          marker is False only because the injected tape does not execute)
  NEW-E  ... marker on disk: True
```

The shipped file is clean, exactly as round 5 said. What is overstated is
still the claim, now at a higher bar than before.

### Smallest fix

Resolve aliases before the name test: walk `ast.Import` and
`ast.ImportFrom` first, map every local binding back to its real module,
and refuse `from subprocess import ...` and `from os import system` by
name. Add `operator.attrgetter`, `operator.methodcaller` and
`functools.partial` to the banned dotted calls, or, more cheaply, assert
that the module's whole import list is exactly the expected one.

---

## F4 (LOW) The new SCOPE half of the authorisation gate is not total

`_authorisation_refusal` (`:880`) calls `_gate_check_write_scope`, which
iterates at `tools/bm_controller.py:2323`:

```python
        for path in unit["write_scope"] or []:
```

without first asking `_unsafe_scope_container`, which is what
`_authorise_dispatch` does at `:2406` before anything else. So the JUDGING
path this round created is missing the container question the DISPATCH path
has:

```
$ python3 p9_mixed.py
E3 ... poison=7
Traceback (most recent call last):
  File ".../bm_controller.py", line 1676, in receive_result
  File ".../bm_controller.py", line 2760, in _verify_and_finish
    refusal = self._authorisation_refusal(project_id, unit, charged)
  File ".../bm_controller.py", line 881, in _authorisation_refusal
  File ".../bm_controller.py", line 2323, in _gate_check_write_scope
    for path in unit["write_scope"] or []:
TypeError: 'int' object is not iterable
```

`main()` catches `bs.BMStoreError` and `ValueError` only, so this leaves as
a traceback rather than a refusal. It is REFUTATION-5 S6's class, closed
for `plan` this round and reopened one method along.

Not reachable from a shipped command: `plan` refuses `"write_scope": 7`
(verified, probe D4). It is reachable for exactly the population
`_unsafe_scope_entry`'s own docstring says the engine-side rule exists for,
"a store written by an older version, a hand-written row, an SDK caller
that never ran `bm-controller plan`". A bare-string container reaches the
same gate check and is walked character by character there; it is contained
downstream, because `_rollback_plan` refuses it and composes nothing
(`poison='a.py' -> rejected, commands=['false'], founder steps: 1`).

Smallest fix: one `_unsafe_scope_container` call at the top of
`_gate_check_write_scope`, or in `_authorisation_refusal` before it.

---

## F5 (LOW) `spend-reconciliation` is not a reserved lane, and its block names a cause that did not happen

`KNOWN-LIMITS.md` discloses the collision ("A unit graph that plans units
into a lane of that name would have them gated by the disclosure. No
shipped fixture does; do not name a lane that."). The measured consequence
is larger than that sentence: nothing reserves the name, and the block is
on DELIVERY of the whole run, carrying a note that states a fact that is
false.

```
$ python3 p8_s7_and_store.py
D2  plan ACCEPTED a unit in lane 'spend-reconciliation'
    receive_result -> u1
    run state=CHECKPOINTED reason=SPEND_STOP
    note: the done-definition was not run and nothing was delivered: 1
          accepted unit(s) cost spend this engine could NOT charge, so the
          breaker reads LOW and a ceiling cannot mean anything until that
          is fixed...
    spend_totals: {'tokens': 0, ..., 'verdict': 'ok'}
```

No spend was ever uncharged. The step in that lane was an ordinary founder
step. `_unreconciled_uncharged_spend` (`:1778`) selects by LANE alone, so
any step in that lane reads as an uncharged cost.

Smallest fix: refuse the reserved lane name in `_validated_units` (one
comparison, beside the unit-id rule already there), or select the
disclosure steps by a marker the disclosure itself writes rather than by
lane.

---

## F6 (disclosure) Resolving the reconciliation step does not charge the meter

S7's block is real and it works (probe D1: `SPEND_STOP`, no delivery). The
way out is two shipped commands, and the engine checks only that the step
is resolved, never that the charge landed:

```
D1  -- founder RESOLVES the step WITHOUT charging the spend --
    run state now : DELIVERABLE_READY   reason=DELIVERED
    spend_totals  : {'tokens': 0, ..., 'verdict': 'ok'}
    commands: ['CHECK-u1', 'DONE_DEF']
```

90 tokens claimed, 0 metered, the run delivered. The round-6 report does
not claim otherwise ("the way out is two shipped commands"), so this is a
completeness note on the disclosure rather than a refutation of it.

---

# WHAT STANDS (attacks that failed)

### S1's execution side: 56 spellings, real git per row

Every candidate went through `bs.canonical_write_scope_entry`
(declaration), then `bc._unsafe_scope_entry` on the STORED string
(execution), then the command composed exactly as `:3183` composes it, run
in a fresh git repo with three tracked files all carrying uncommitted
edits.

```
$ python3 p1_pathspec_sweep.py     (abridged; full table in the probe output)
declared             | store                        | engine   | git effect
'src/app.py'         | ACCEPTED                     | ok       | exit=0 reverted=['src/app.py']
'src'                | ACCEPTED                     | ok       | exit=0 reverted=['src/app.py']
'.'                  | ACCEPTED                     | ok       | exit=0 reverted=ALL THREE
':/'  ':'  ':!keep.txt'  ':^x'  ':(exclude)x'  ':(top)'  ':(icase)X'
':(glob)**/*.py'  ':(attr:binary)'  '::'  ':(literal)keep.txt'
                     | REFUSED pathspec-write-scope | REFUSED  | no command composed
' :/'  '\t:/'  '\x0b:/'  '\x0c:/'  '\x1c:/'  '\x85:/'  '\xa0:/'
'\u2000:/'  '\u3000:/'
                     | REFUSED pathspec-write-scope | REFUSED  | no command composed
'./:/'  './:!keep.txt'  'a/../:!keep.txt'  'sub/../:'  './/:/'
                     | REFUSED pathspec-write-scope | (n/a)    | never stored
'-keep.txt' '--' '--all' '~/x'
                     | ACCEPTED                     | REFUSED  | no command composed
'/etc/passwd' 'C:/Windows' '\\srv\share'
                     | REFUSED absolute-write-scope | REFUSED  | no command composed
'*.py' 'src/*' '[k]eep.txt' '?eep.txt'
                     | REFUSED glob-write-scope     | REFUSED  | no command composed
'\ufeff:/'           | ACCEPTED                     | ok       | exit=1 reverted=none
'：/' '∶/' '﹕/'      | ACCEPTED                     | ok       | exit=1 reverted=none
'src/:/'  'src/:!keep.txt'
                     | ACCEPTED                     | ok       | exit=1 reverted=none
'keep.txt\n:/'       | ACCEPTED                     | REFUSED  | no command composed
```

The lookalike rows are the interesting ones and they are NO-DATA: a colon
that is not the FIRST byte of the argument is not magic to git, so each is
a literal path nothing matches, exits 1 (which is the dirty-write-scope
warning path, so the founder hears about it) and reverts nothing. The same
holds for every re-spelling that reaches git without passing the store
(probe A1b, twelve rows, all exit 1, all `reverted=none`).

`.` still restores the whole tree and is still an accepted write scope.
That is the round-5 disclosure, unchanged and correctly disclosed.

### S1: a poisoned row through every rollback call site

Pass-through Store proxy rewriting one unit's `write_scope` on the way out,
standing in for a hand-written row or an SDK caller, in a REAL git repo
with the REAL `SubprocessCheckRunner`. The unit's `done_check` is `false`,
so this is the rejection leg that rolls back.

```
$ python3 p9_mixed.py
  poison=[':/']           -> rejected  commands=['false']
      tree after: {'a.py': 'FOUNDER EDIT', 'keep.txt': 'FOUNDER EDIT'}   steps: 1
  poison=[':!keep.txt']   -> rejected  commands=['false']    tree intact    steps: 1
  poison=['../outside.txt'] -> rejected commands=[]          tree intact    steps: 1
  poison=['']             -> rejected  commands=[]           tree intact    steps: 1
  poison='a.py'           -> rejected  commands=['false']    tree intact    steps: 1
  poison=['.']            -> rejected  commands=['false', 'git restore -- .']
      (the declared whole-project scope, behaving as declared)
```

### S1: no shell injection

Six metacharacter spellings, through the real runner, in a real repo:

```
  'a.py; touch PWNED'   ran=["git restore -- 'a.py; touch PWNED'"]   PWNED=False
  'a.py && touch PWNED' ran=["git restore -- 'a.py && touch PWNED'"] PWNED=False
  'a.py$(touch PWNED)'  ...                                          PWNED=False
  'a.py`touch PWNED`'   ...                                          PWNED=False
  'a.py|touch PWNED'    ...                                          PWNED=False
  'a.py\ttouch PWNED'   ...                                          PWNED=False
```

### S1: an empty scope, and combinations

`write_scope: []` composes no command and warns nothing (`_rollback_plan`
returns `(None, None)` at `:3177`), which is the deferred
empty-write-scope question rather than a new one. `["a.py", ":/"]` is
refused whole at `plan`. There is no construct in git's pathspec language
that makes two individually safe entries dangerous together, and I found
none.

### S1 at the shipped CLI

```
$ bash p10_s1_cli.sh
--- write_scope [":/"] ---
    bm_controller: refused: unit 'u1' cannot be planned: its write_scope
    entry ':/' begins with ':', which git reads as PATHSPEC MAGIC ...
    run 6aa6194f...: state NEW      dispatched: (none)
    tree after: keep.txt=FOUNDER EDIT src/app.py=FOUNDER EDIT docs/notes.md=FOUNDER EDIT
--- write_scope [":!keep.txt"] ---   identical shape, run NEW, tree intact
--- write_scope ["./:!keep.txt"] --- refused by the STORE, run PLANNING, tree intact
--- write_scope ["src/app.py"] ---   planned, state EXECUTING, dispatched u1
```

### S2: the round-5 sequence, and the whole ceiling matrix

```
$ bash p3_s2_cli.sh
=== R5 S2 verbatim: ceiling blown BEFORE record-result, no cost claimed ===
  gate-check says: REFUSED-BREAKER
    dispatch 560cf0e3... rejected; ... reason: SPEND_STOP
  done_check ran      : NO
  done_definition ran : NO
=== exactly AT the ceiling: pre-spend 100, no cost claimed ===
  gate-check says: REFUSED-BREAKER      done_check: NO   done_definition: NO
=== one under the ceiling: pre-spend 99, no cost claimed ===
  gate-check says: ALLOWED              done_check: YES  done_definition: YES
```

### S2: the carve-out cannot be widened

```
$ python3 p4_carveout.py
C1  two lanes, each claiming 150 tokens against a 100 ceiling
  u1 -> u1        spend now tokens=150 verdict=hard-stop   commands: ['CHECK-u1']
  u2 -> rejected  spend now tokens=300                     commands: ['CHECK-u1']
C2  the done-definition under the carve-out
  commands: ['CHECK-u1']        (no DONE_DEF)
  next step -> state=STOPPED reason=TERMINAL
C5  the ceiling blown by a separate spend, the unit claims 5 tokens
  receive_result -> rejected    commands: []
```

The arithmetic is why: once the meter carries the first unit's cost, the
residual stays above the ceiling for every later unit, so subtracting the
NEXT unit's own charge can never put it back under. `_deliver_or_hold`
(`:3662`, `:3711`) passes no `charged`, so the exemption cannot reach the
founder's suite by construction. `--tokens` and `--minutes` take
`minimum=0` at the CLI, so the meter cannot be walked backwards either.

### S2: a refused SCOPE and a dead contract

```
E1  the contract is AMENDED to exclude the unit's write scope
  gate_check now: REFUSED-SCOPE
  receive_result -> 'rejected'
  commands executed: []
```

Dead contract, from the S5 mutation harness's own control (probe A5 part 3,
every mutant run): `contract: revoked, receive_result -> 'rejected', gated
CheckRunner calls: []`.

### S4/S6 and the read_scope gap

```
$ python3 p8_s7_and_store.py
D3  read_scope list         -> ACCEPTED stored=['src']
    read_scope bare string  -> REFUSED (bad-scope, naming the explosion)
    read_scope int          -> REFUSED bad-scope
    read_scope dict         -> REFUSED bad-scope
    read_scope tuple        -> ACCEPTED stored=['src']
    read_scope set          -> REFUSED bad-scope
    read_scope None         -> ACCEPTED stored=[]
```

The store report's disclosed gap ("a bare string arrives as a list of
one-character strings the store's container check cannot distinguish") is
genuinely closed by the engine, because `_refuse_bad_scopes` asks the
container question BEFORE `_validated_units` canonicalises.

### No write-scope spelling reaches a fence

```
D4  ['a.py']        stored=['a.py']    fence=['a.py']    brief=['a.py']
    ':/'  [':/']  [':!keep.txt']  ['./:!keep.txt']  ['']  ['a.py', ':/']
    7  [None]       plan REFUSED, nothing stored, no fence
    []              stored=[]          fence=[]          brief=[]
    ['.']           stored=['.']       fence=['.']       brief=['.']
    ('a.py',)       stored=['a.py']    fence=['a.py']    brief=['a.py']
    ['\ufeff:']     stored/fence/brief carry it (a literal name to git)
    ['src/:!x']     stored/fence/brief carry it (a literal name to git)
```

`_authorise_dispatch` asks `_unsafe_write_scope` at `:2406`, before the
gate check and before the fence claim, so the ordering is right.

### The engine/store asymmetry on the re-spelled family is not a wedge

`_unsafe_scope_entry` reads the DECLARED string and does not resolve it, so
`./:!keep.txt` passes the engine rule and is caught only by the store's
second look, inside `upsert_units`. That leaves the run in `PLANNING`
rather than `NEW`, which is the exact state the controller report says its
own refusal exists to avoid. It recovers:

```
$ bash p11_replan.sh
1) plan './:!keep.txt'  -> refused (store second look), run PLANNING
2) plan 'src/app.py'    -> planned 1 unit(s)
3) step                 -> state EXECUTING, dispatched u1
```

NO-DATA, recorded because the report's own argument for the engine-side
refusal does not hold for that family.

---

# ATTEMPTS LOG

Every probe used its own throwaway store under `mktemp -d` or
`tempfile.TemporaryDirectory()`, with `BROTHERMODE_ROOT` pointed at it for
the CLI runs, and every git probe used its own temp git repository. No real
`.brothermode` store was opened, no repository git state was changed, and
this report is the only file written in the repository.
`python3 tools/test_all.py` was NOT run, per the brief; no unittest class
was run either.

| # | Attack | Result |
|---|---|---|
| A1 | 56 write-scope spellings through both gates and then real git, counting files reverted per row | FAILED to refute. No spelling both passes and touches an undeclared file |
| A1b | Twelve engine-accepted, store-rewritten spellings handed straight to git | FAILED. All exit 1, `reverted=none` |
| A1c | S1 at the shipped CLI: refusal, run state, founder tree | FAILED to refute. Refused, run NEW, three uncommitted edits intact |
| A2 | The spend breaker at the shipped CLI, five ceiling positions, markers on disk | FAILED to refute S2. Produced **F2** (the false note) |
| C1..C6 | Widen the carve-out: second unit, done-definition, non-own cost, held-then-resumed result | FAILED. Bounded to one already-paid unit, exactly as claimed |
| A3 | Kill at every point around the command, four kill words, both windows | **F1**. The verifier window is open |
| A3b | The same at the shipped CLI with a real `bm_autonomy revoke` subprocess | **F1** reproduced end to end |
| A5 | Reproduce the four mutations, then hunt a fifth; execute the passing mutants | **F3**. Four claimed failures confirmed; five new spellings pass, four really start a process |
| D1 | S7's delivery block, then resolve the step without charging | Block STANDS. **F6** on the completeness of the remedy |
| D2 | Plan a unit into `SPEND_RECONCILE_LANE`; queue an unrelated step there | **F5**. Nothing reserves the lane; the block names a false cause |
| D3 | Every read_scope container shape through `plan` | FAILED to refute. The store's disclosed gap is closed by the engine |
| D4 | Fourteen write-scope shapes, reading the FENCE and the BRIEF the store actually holds | FAILED to refute |
| E1 | A contract amended to exclude the unit's scope, then a result | FAILED to refute. Zero commands |
| E2 | Shell injection through `write_scope` into the rollback, real runner, real repo | FAILED. `shlex.quote` holds |
| E3 | Poisoned rows through all three rollback call sites, real runner, real repo | FAILED to refute. Produced **F4** (a TypeError, not a rollback) |
| A8 | Recovery from the `PLANNING` state a store-side refusal leaves behind | FAILED to refute. `plan` again works |

Probe sources are in the session scratchpad under `r6ref/` and are
EPHEMERAL: `clienv.sh`, `p1_pathspec_sweep.py`, `p2_rawgit.py`,
`p3_s2_cli.sh`, `p4_carveout.py`, `p5_s3_windows.py`, `p6_s3_cli.sh`,
`p7_s5_guard.py`, `p8_s7_and_store.py`, `p9_mixed.py`, `p10_s1_cli.sh`,
`p11_replan.sh`, each with its captured `.out` (503 lines of output in
total). Each one is short and its whole shape is described where it is
cited above.

---

# WHAT I DID NOT CHECK

* **`tools/test_all.py` was not run**, per the brief, and neither was any
  unittest class. I make no claim about suite health, and I did not verify
  either FIX report's quoted test counts.
* **Rounds 1 to 5 were not re-litigated.** Everything above is scoped to
  what round 6 changed. Where an earlier round's disclosure surfaced in a
  probe (`.` as a whole-project scope, an empty write scope, the
  self-reported cost numbers), I recorded the observation and did not
  attack it.
* **`tools/bm_fence_hook.py` was neither read nor run.** Both FIX reports
  name it as an unchecked third reader. My claim is only about what the
  store holds as a fence (probe D4), not about what the hook does with it.
* **Concurrency.** Every probe is single process, except F1's reproduction
  B, where the second process is the `bm_autonomy revoke` the verifier
  spawns. Two controllers stepping the same project at once was not
  exercised.
* **`bm_autosave.py`, `hooks/`, the MCP surface, `bm_project.py` and
  `bm_learn.py`** were not audited. I did not repeat round 5's sweep for a
  subprocess reachable from the eight shipped controller commands.
* **`bm_autonomy.py`'s own `spend` and `human-steps` surfaces** were used
  but not attacked. I confirmed `--tokens` and `--minutes` refuse negatives
  at the controller CLI (`minimum=0`) and did not test whether
  `Store.record_spend` refuses a negative charge from a Python caller.
* **The three extra store reads per judged command** the FIX report
  discloses were not measured on a large store.
* **Windows and Linux.** Everything ran on darwin, Python 3.9.6, with the
  system git (the same 2.50.1 the FIX report names). Git's pathspec magic
  is not platform specific, but the exact `git restore` exit codes were
  observed on this machine only.
* **Whether any of these has occurred in a real run.** Reachability was
  demonstrated; incidence was not.
* **The working tree was CLEAN when I started** (`git status --short`
  returned nothing at HEAD 1e40b8e), unlike the state rounds 5 and 6
  recorded, so I inherited no pre-existing modification to account for.
  This report is the only file I wrote in the repository, and I made no git
  state change of any kind.
