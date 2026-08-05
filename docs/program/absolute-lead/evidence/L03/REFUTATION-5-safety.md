# REFUTATION 5, the SAFETY GATE AND AUTHORISATION lens

## PUSH VERDICT: PUSH-BLOCKER FOUND

One finding meets the bar on its own, with an end to end reproduction
through the shipped command line and no concurrency:

**S1. A `write_scope` entry that is a git PATHSPEC (`:/`, `:!x`,
`:(exclude)x`) is accepted by the round-5 literal-write-scope rule, and the
engine's own rollback then restores the WHOLE working tree.** Every
uncommitted founder edit in the project is destroyed. With `:/` the
rollback exits 0, so no dirty-write-scope warning is ever queued and the
founder is told only "dispatch rejected". This is the exact damage
`docs/KNOWN-LIMITS.md` says round 5 closed, reached by a spelling the new
gate does not look for.

A second finding, S2, meets the letter of the "executes something the
founder forbade" clause and I flag it as a blocker candidate with its
counter-argument stated: after the founder's SPEND CEILING has tripped and
`bm-autonomy gate-check` says `REFUSED-BREAKER`, one `bm-controller
record-result` still runs the unit's model-authored `done_check` AND the
founder's whole `done_definition`, accepts the unit and declares the run
`DELIVERABLE_READY`. Round 5's rule gates commands on the contract's
liveness and on nothing else, so the second of the founder's two brakes
stops no command at all.

Everything else below is a disclosure item.

---

## VERDICTS, one line each

| Claim under attack | Verdict |
|---|---|
| AZ F5: no engine path executes a subprocess unless the CONTRACT is live | **STANDS** for the contract. p11 and p12 re-run against the REAL runner, four ways, zero commands, marker file absent (probe A) |
| The same rule stated as "the founder's kill switch stops everything" | **REFUTED**, S2: the spend breaker gates no command, and the delivery path runs the founder's whole suite after it trips |
| `self.checker.run` at exactly one line behind `_run_command` | **STANDS** as a fact about the shipped file (grep and AST both agree) |
| "A command site added OUTSIDE the gate fails that test" (FIX report section 2) | **REFUTED**, S5: the AST guard passes with `subprocess.run`, `os.system`, `getattr(self.checker, "run")` and `runner = self.checker` added inline in `_verify_and_finish` |
| "Liveness is NOT folded in... a revoked contract never reaches the revision comparison" (FIX report section 3) | **REFUTED**, S3: a stop or revoke landing DURING the done_check reaches it, is classified as a non-move, and the unit is accepted under a killed contract. Round 4 rejected it as stale |
| AZ F4: the PAUSED hold holds on the shipped route | **STANDS**. hold, hold+stop, hold+revoke, hold+re-plan and double hold all behave (probe I) |
| The uncharged meter is "a breaker reading low by one unit's cost" (KNOWN-LIMITS) | **REFUTED as to magnitude**, S7: a whole run completes to DELIVERABLE_READY, 270 claimed tokens against a 100 token ceiling, metered 0, verdict `ok` |
| AZ F2: `plan --project p1 --run <p2's run>` is refused | **STANDS** end to end at the CLI; p2 stays PAUSED, its dispatch survives (probe F) |
| Every controller store write names its project | **STANDS** for the engine (48 of 50 call sites); the 2 that do not are `cmd_resume` and `cmd_complete`, and neither can cross a project (NO-DATA) |
| "A write scope is a LITERAL PATH, never a pattern" closes it "for every reader at once" (`literal_scope_entry` docstring) | **REFUTED**, S1 (git pathspec magic) and S4 (a bare JSON string is iterated character by character) |
| Non-string write_scope entries are refused `bad-path` | **STANDS** for entries; **REFUTED for the container**, S6: `"write_scope": 7` is an uncaught `TypeError` out of the shipped `plan` |

Severity key, per the brief: HIGH = reachable from a shipped command or the
production loop. MEDIUM = needs a concurrent writer or an SDK caller.
LOW = exotic.

---

# THE FINDINGS

## S1 (HIGH, PUSH-BLOCKER) A git pathspec in `write_scope` makes the rollback restore the whole working tree

### The code

`tools/bm_store.py:489`

```python
_GLOB_CHARS = frozenset("*?[")
```

`tools/bm_store.py:795`, `literal_scope_entry`, is the round-5 gate. It
refuses an entry containing one of those three characters, and its own
docstring states the property it is protecting:

> the same string is read three more times afterwards by machinery that
> reduces it to its literal prefix directory: the fence claim,
> `tools/bm_fence_hook.py`'s covering check ... and the engine's
> `git restore --` rollback, where git's own pathspec globbing is
> recursive.

`tools/bm_controller.py:2529`, the third reader:

```python
        return "git restore -- " + " ".join(
            shlex.quote(p) for p in write_scope)
```

`shlex.quote` protects the SHELL. It does not protect GIT. Git's pathspec
language has magic that begins with a colon, and none of `:`, `!`, `^`,
`(` or `)` is in `_GLOB_CHARS`. `canonicalize_path` treats these strings as
ordinary relative paths inside the root, so they survive.

Rollback call sites, all three reachable: `tools/bm_controller.py:1445`
(`_handle_late_result`), `:2285` (the staleness branch) and `:2424`
(`_reject`, which is where a failing `done_check` lands).

### What git actually does with the surviving spellings

Probe: a throwaway git repo per row, two tracked files, both modified.

```
=== git pathspec magic variants against a real repo ===
:!keep.txt               exit=0  keep=EDIT   other=v1
:^keep.txt               exit=0  keep=EDIT   other=v1
:(exclude)keep.txt       exit=0  keep=EDIT   other=v1
:                        exit=0  keep=v1     other=v1
:/                       exit=0  keep=v1     other=v1
:(top)                   exit=0  keep=v1     other=v1
:(icase)KEEP.TXT         exit=0  keep=v1     other=EDIT

=== same, with GIT_LITERAL_PATHSPECS=1 ===
:!keep.txt               exit=1  keep=EDIT   other=EDIT   error: pathspec ':!keep.txt' did not match any file(s) known to git
:(exclude)keep.txt       exit=1  keep=EDIT   other=EDIT   error: pathspec ':(exclude)keep.txt' did not match any file(s) known to git
```

`v1` means the file was reverted. Exit 0 in every magic row means the
engine reads the rollback as a SUCCESS and queues no dirty-write-scope
warning.

### What the store stores

`pC_scope_shapes.py`, engine `plan` against a throwaway store:

```
git pathspec magic :/        ACCEPTED stored=[':']
                               rollback='git restore -- :'
git pathspec exclude :!x     ACCEPTED stored=[':!x']
                               rollback="git restore -- ':!x'"
```

Note the first row: `:/` is canonicalised to `:`, which is the spelling
that restores the entire tree.

### Reproduction 1, end to end, shipped CLI, `write_scope [":!keep.txt"]`

Sequence: `bm_project start`, `bm_autonomy sign --allowed-path .`,
`bm-controller start`, `plan`, `step`, `record-result`. The unit's
`done_check` is `false`, so the unit is rejected and rolled back. The
contract is the whole-project one `docs/FULL-AUTO.md` itself documents
("A contract signed with `.` authorises the whole project").

```
$ bash pD_rollback_escape.sh
--- founder tree before the controller runs ---
 M docs/notes.md
 M keep.txt
 M src/app.py
src/app.py  = FOUNDER UNCOMMITTED EDIT
docs/notes.md = FOUNDER UNCOMMITTED EDIT
controller run 8ec21aa5329548c8bf0c883dfe96c91c started for project p1 (state NEW)
planned 1 unit(s) for run 8ec21aa5329548c8bf0c883dfe96c91c
--- dispatch beeb0f7756ab433c93a492913d093acd recorded; done_check is `false`, so the unit is rejected and rolled back ---
dispatch beeb0f7756ab433c93a492913d093acd rejected; the unit re-queues for one retry or escalates, per the circuit breaker
--- founder tree AFTER the rollback ---
 M keep.txt
?? units.json
src/app.py    = v1
docs/notes.md = v1
keep.txt      = FOUNDER UNCOMMITTED EDIT
```

The unit declared ONE entry. Two files it never named lost their
uncommitted contents. The one file the `:!` names is the one that
survived.

### Reproduction 2, the silent version, `write_scope [":/"]`

Same script with the one entry changed:

```
$ bash pD_rootspec.sh
--- founder tree AFTER the rollback ---
?? units.json
src/app.py    = v1
docs/notes.md = v1
keep.txt      = v1
```

`git status --short` shows NO modified file left. Every uncommitted change
in the project is gone, the rollback exited 0, and the only thing the
founder was told is `dispatch ... rejected; the unit re-queues for one
retry or escalates, per the circuit breaker`.

### The bound, stated honestly

The contract must admit the entry. Control, same script under
`--allowed-path src`:

```
$ bash pD_control_narrow.sh
run 8c4e05fce92e4e689bb7f2db66eef949: state CHECKPOINTED
dispatched: (none)
note: no selectable unit could be claimed this wave (fence overlap, or
gate_check refused and the circuit breaker absorbed it); tried again next step
```

So this needs `allowed_paths` that admits a one-segment name, which `.`
does (`path_within_allowed(".", anything)` is True) and which the product
documents as a supported shape. Under a narrow contract the unit is never
dispatched.

The honest counter-argument, and why it does not dissolve the finding: in
full auto `done_check` and `verifier` are model-authored SHELL, so a
HOSTILE model already has arbitrary execution under a live contract, and
this buys it nothing. The finding is not about a hostile model. It is that
`:/` and `:!x` are the natural git idioms for "the repo root" and
"everything except", a planner writing either gets no refusal, the founder
reading `write_scope: [":!keep.txt"]` sees one file, the fence claims a
path that does not exist so it protects nothing, and the engine's OWN
composed command, not the model's, wipes the tree.

### Smallest fix

Either refuse a leading `:` in `literal_scope_entry` (one comparison, in
the same place the glob rule lives), or run the rollback with
`GIT_LITERAL_PATHSPECS=1` in the environment, which the sweep above shows
neutralises every magic spelling. Doing both is cheap. The fence claim and
`bm_fence_hook`'s coverage check should be re-checked for the same family
in the same change.

---

## S2 (HIGH, blocker candidate) The spend breaker gates no command; a tripped ceiling still runs the founder's whole done-definition

### The code

`tools/bm_controller.py:596` to `:626`, the one gate:

```python
        if not self._contract_is_live(project_id):
            return None
        return self.checker.run(command, cwd=self.store.root)
```

Liveness is the ONLY question asked. `step()` asks the other one at
`tools/bm_controller.py:951` (`if spend["verdict"] == "hard-stop":` then
drain), and `_authorise_dispatch` treats a `REFUSED-BREAKER` gate verdict
as `DRAIN`, that is, "stop the whole run". Neither `_verify_and_finish`
(`:2249`) nor `_deliver_or_hold` (`:2985`) consults the breaker, and
`receive_result` never reaches step 3 at all.

### Reproduction, shipped CLI, no concurrency

```
$ bash pJ2_breaker_cli.sh
--- the founder's ceiling is blown ---
{
  "minutes": 500,
  "minutes_ceiling": 100,
{
  "contract_id": "113f1fe0ed964cdd956fc5c6da2c1efe",
  "floor": null,
  "reason": "spend is at or over 100 percent of a ceiling; the breaker has tripped.",
  "revision": 1,
  "verdict": "REFUSED-BREAKER"
}
--- one shipped record-result ---
unit u1 accepted (dispatch d25d5bafab0c446ebe41d5dd8dabcec7)
note: deliverable ready
reason: DELIVERED
founder-gated remainder: 0 open human step(s), 0 failed unit(s)
done_check ran:      YES
done_definition ran: YES
run state: DELIVERABLE_READY
```

Sequence: `sign --token-ceiling 100 --minutes-ceiling 100`, `start`,
`plan`, `step`, `bm-autonomy spend --tokens 500 --minutes 500`,
`bm-controller record-result`. The `done_check` and the `done_definition`
are `touch` commands, so execution is visible on the filesystem.

The rollback leg too, when the unit fails:

```
$ python3 pJ_breaker.py
spend_totals: {'tokens': 500, 'minutes': 500, 'verdict': 'hard-stop'}
gate_check now says: REFUSED-BREAKER | spend is at or over 100 percent of a ceiling; the breaker has tripped.
contract state: live
receive_result -> 'rejected'
commands the shipped record-result executed: ['touch /var/.../DONE_CHECK_RAN && false', 'git restore -- a.py']
done_check marker on disk: True
unit: READY
run: FAILED_TERMINAL
```

That is REFUTATION-4 AZ F5's own sentence with one word changed:
gate_check says REFUSED-BREAKER and two commands run anyway, one of them a
`git restore` in the founder's working tree.

### Why I call it blocker-candidate rather than blocker

The counter-argument is real: the dispatch was authorised under a valid
revision before the ceiling blew, and judging already-authorised work is
the same argument the design makes for RESULT_IN. What makes it a finding
anyway is the inconsistency: round 5 decided the opposite for a stopped
contract (nothing runs, the result is rejected, a founder step is queued),
and the most expensive command in the system, the founder's whole test
suite at `:3012`, is the one this leaves ungated. `docs/FULL-AUTO.md`'s own
example done-definition is `python3 tools/test_bm.py`.

---

## S3 (MEDIUM) A stop or revoke that lands DURING a command is no longer stale, so the unit is accepted under a killed contract, and the founder is told the opposite

### The claim being refuted

`FIX-round5-controller-report.md` section 3:

> **Liveness is not folded in.** Whether a stopped or revoked contract may
> be acted on at all is a separate question, asked earlier and more
> strictly by section 2's gate ... So classifying `revoke` as a lifecycle
> kind does not weaken anything: a revoked contract never reaches the
> revision comparison.

### The code

`tools/bm_controller.py:391`

```python
_LIFECYCLE_CHANGE_KINDS = frozenset(("pause", "resume", "stop", "revoke"))
```

`_verify_and_finish` reads the contract at `:2249`, runs the `done_check`
at `:2254`, and asks `_authorisation_moved` at `:2263`. The window between
`:2249` and `:2263` is exactly as long as the founder's `done_check`, which
in production is a test suite. A stop or revoke landing inside it is read
as a non-move, so the staleness branch is skipped and, with no `verifier`
on the unit, the result is accepted.

### Reproduction A, a real second process, shipped CLI

The unit's `done_check` IS the kill switch: a real
`python3 tools/bm_autonomy.py revoke --project p1` subprocess, which is a
faithful stand-in for the founder pulling it in another terminal while the
check runs.

```
$ bash pG_revoke_midcommand.sh
contract before record-result: live
unit u1 accepted (dispatch 5b3063b9088c48d88d8a4a816d107dcf)
note: the contract is revoked, not live: nothing is authorised, so the result was recorded and rejected and NO command was executed (no done_check, no verifier, no rollback). The fence is parked and a founder step names the unit
reason: CONTRACT_NOT_LIVE
contract after record-result:  revoked
run state: CHECKPOINTED
```

Two founder-facing statements in one command, both false. The unit was
accepted, not rejected. A command WAS executed: the done_check, which is
what revoked the contract.

### Reproduction B, deterministic, both kill words

```
$ python3 pG2_revoke_midcommand.py
== the founder revoked the contract during the done_check ==
  commands executed: ['true']
  contract now: revoked  stamped revision: 1  latest revision: 2
  _authorisation_moved -> False (round 4 compared the integers, which would be True)
  receive_result -> 'u1'
  unit status: DONE  dispatch status: VERIFIED
  dispatch row: {'status': 'VERIFIED', 'verifier_verdict': 'pass'}
  fence: complete
  founder-facing note: 'the contract is revoked, not live: nothing is authorised, so the result was recorded and rejected and NO command was executed (no done_check, no verifier, no rollback). The fence is parked and a founder step names the unit'

== the founder stopped the contract during the done_check ==
  commands executed: ['true']
  contract now: stopped  stamped revision: 1  latest revision: 2
  _authorisation_moved -> False (round 4 compared the integers, which would be True)
  receive_result -> 'u1'
  unit status: DONE  dispatch status: VERIFIED
  dispatch row: {'status': 'VERIFIED', 'verifier_verdict': 'pass'}
  fence: complete
```

The unit is DONE, a `unit-green` checkpoint is written, the fence is
released `complete`, and no founder step names any of it. This is strictly
weaker than round 4, which rejected the same sequence as stale.

### The second half: the note is wrong by construction, not only in a race

`tools/bm_controller.py:2627` (`_settle_after_wave`) reuses
`_NOTE_CONTRACT_NOT_LIVE`, defined at `:447`, whose text hard-codes "the
result was recorded and rejected and NO command was executed ... The fence
is parked and a founder step names the unit". On the settle path that
sentence describes a different branch's behaviour. One note constant is
serving two branches whose facts differ.

### Smallest fix

Either drop `stop` and `revoke` from `_LIFECYCLE_CHANGE_KINDS` (they are
not reversible, so treating them as authorisation-preserving buys nothing
the liveness gate does not already give), or re-read the contract after the
`done_check` and before acceptance. Give the settle path its own note.

---

## S4 (HIGH) A `write_scope` that is a bare JSON string is iterated character by character, fencing the project root

### The code

`tools/bm_store.py:13162`

```python
                write_scope = [canonicalize_path(
                                   self.root,
                                   literal_scope_entry(p, unit_id=uid),
                                   cwd=None)
                               for p in (u.get("write_scope") or [])]
```

A Python string is iterable, so `"a.py"` yields `'a'`, `'.'`, `'p'`, `'y'`.
`.` canonicalises to `.`, the project ROOT. The store's own
`_normalize_files` (`tools/bm_store.py:849`) documents the exact defence
this loop is missing:

> A bare string is ONE path, not an iterable of characters, the same
> defensive rule bm_registry's `_safe_path_list` enforces

`tools/bm_controller.py:863` has the same shape for `read_scope`.

### Reproduction, shipped CLI

```
$ bash pL_barestring.sh
--- the unit declares  "write_scope": "a.py"  (a string, not an array) ---
planned 1 unit(s) for run 3937a0654b7f479ab10180d637c023cf
--- the brief the worker is handed ---
{"controller_brief": {"attempt": 1, "objective": "edit one file", "prior_failure_note": "", "read_scope": [], "risk_class": "file-edit", "role": "builder", "unit_id": "u1", "write_scope": ["a", ".", "p", "y"]}}
run 3937a0654b7f479ab10180d637c023cf: state EXECUTING
dispatched: u1
--- what the fence actually holds ---
  unit u1 write_scope = ['a', '.', 'p', 'y']
  fence unit-u1 state active holds ['.', 'a', 'p', 'y']
```

Consequences, all silent:

1. The brief handed to the worker (in full auto, the orchestrating model)
   says it may write `.`, the whole project.
2. The unit's fence holds `.`, so `bm_fence_hook`'s covering check makes
   every other writer's write anywhere in the project refusable, from one
   unit.
3. The rollback becomes `git restore -- a . p y`, which git refuses whole
   (`error: pathspec 'a' did not match any file(s) known to git`, exit 1),
   so this leg does at least produce the dirty-write-scope warning.

`read_scope` behaves the same way:

```
list                 ACCEPTED read_scope=['src']
bare string          ACCEPTED read_scope=['s', 'r', 'c']
escape in a string   REFUSED path-escape
int                  RAISED TypeError: 'int' object is not iterable
```

Same bound as S1: the exploded entries must pass `gate_check`, which under
`allowed_paths ["."]` they do.

---

## S5 (LOW) The structural guard passes with a real ungated command in the file

### The claim being refuted

`FIX-round5-controller-report.md` section 2:

> A seventh command site added later is gated by construction; a command
> site added OUTSIDE the gate fails that test.

### The code

`tools/test_bm_controller.py:3643`, `_checker_call_site_functions`, matches
one AST shape only: `ast.Attribute(attr="run")` whose value is
`ast.Attribute(attr="checker")` whose value is `ast.Name(id="self")`.

### Reproduction

The guard function is copied verbatim into `pH_ast_guard.py` and run
against MUTATED COPIES of the controller source held in memory. The repo
file is never written and none of the mutant code is executed.

```
$ python3 pH_ast_guard.py
as shipped                                           -> GUARD PASSES  enclosing=['_run_command']
subprocess.run() added inline in _verify_and_finish  -> GUARD PASSES  enclosing=['_run_command']
getattr(self.checker, 'run') in _verify_and_finish   -> GUARD PASSES  enclosing=['_run_command']
runner = self.checker; runner.run(...)               -> GUARD PASSES  enclosing=['_run_command']
os.system() added inline                             -> GUARD PASSES  enclosing=['_run_command']
```

Nothing else covers this: `tools/test_bm.py:1143` bans importing
`subprocess`, but its `allowed` map names `bm_controller.py` explicitly, so
a second `subprocess.run` call site in that file trips no test, and
`os.system` needs no new import at all. The shipped file today is clean;
the guard is what is overstated.

---

## S6 (LOW) A scalar `write_scope` is an uncaught TypeError out of the shipped `plan`

`main()` at `tools/bm_controller.py:3902` catches `bs.BMStoreError` and
`ValueError`. A non-iterable container reaches the loop at
`tools/bm_store.py:13162` and raises `TypeError`.

```
$ python3 tools/bm_controller.py plan --project p1 --units-file u.json ...
Traceback (most recent call last):
  File ".../bm_controller.py", line 3903, in main
    return COMMANDS[cmd](argv[1:])
  File ".../bm_controller.py", line 3547, in cmd_plan
    result = engine.plan(project_id, run_id, units)
  File ".../bm_controller.py", line 792, in plan
    result = self.store.upsert_units(run_id, units, self.actor,
  File ".../bm_store.py", line 13162, in upsert_units
    write_scope = [canonicalize_path(
TypeError: 'int' object is not iterable
EXIT=1
```

with `"write_scope": 7`. This is REFUTATION-3 AZ F-A8's class, closed for
an ENTRY by `literal_scope_entry` and still open for the CONTAINER. Nothing
is written (the transaction is inside the store), so the damage is a
traceback rather than corruption.

---

## S7 (HIGH reachability, accounting damage) The uncharged meter is not "one unit's cost", it is the whole run's, and the work is accepted

`docs/KNOWN-LIMITS.md` discloses:

> a run that is paused mid-flight and resumed has a breaker reading low by
> one unit's cost, visible in the checkpoint trail.

The reachable magnitude is unbounded. Sequence per unit, all shipped:
`bm-autonomy pause`, `bm-controller record-result --tokens N`,
`bm-autonomy resume`, `bm-controller resume`, `bm-controller step`.

```
$ python3 pE2_meter_full.py
u1: record-result -> held      unit now DONE    claimed=90 metered=0 verdict=ok
u2: record-result -> held      unit now DONE    claimed=180 metered=0 verdict=ok
u3: record-result -> held      unit now DONE    claimed=270 metered=0 verdict=ok
run state: DELIVERABLE_READY
commands executed by the engine: ['true', 'true', 'true', 'echo done']
token ceiling was 100; total claimed cost was 270
final spend_totals: {'tokens': 0, 'minutes': 0, 'verdict': 'ok'}
spend-uncharged checkpoints: 3
open founder steps: 0
```

Every unit is DONE, the run is DELIVERABLE_READY, the ceiling was never
approached in the store's view, and no founder step exists. The three
`spend-uncharged` checkpoints are the whole trail, and they are only
visible to a founder who reads the checkpoint log.

**Why this is NOT a blocker.** The numbers are self-reported by the caller
(`--tokens N`, defaulted to 0 at `tools/bm_controller.py:3598`), so a
caller that wants free work simply omits the flag. The meter is advisory
against an uncooperative caller in the first place, and this hole only
costs an HONEST one its accounting. What should change is the disclosure
wording, from "one unit's cost" to "every result recorded during a pause,
without limit".

---

# WHAT STANDS (attacks that failed)

### AZ F5's own two sequences: zero commands, four ways

Re-run against the REAL `SubprocessCheckRunner` (subclassed only to keep a
tape; every taped command really executes), with the unit's `done_check`
set to `touch <marker>` so execution is visible on the filesystem too.

```
$ python3 pA_killswitch.py
== p12 record-result after 'stopped' ==
  contract: stopped  gate_check: REFUSED-STATE
  receive_result -> 'rejected'
  commands executed: []
  done_check marker on disk: False
  stop_reason: 'CONTRACT_NOT_LIVE'
  unit status: READY  fence: parked
== p11 step (RESULT_IN resume) after 'stopped' ==
  commands executed: []
  done_check marker on disk: False
  stop_reason: 'CONTRACT_NOT_LIVE'
  fence: parked
== p12 record-result after 'revoked' ==   ... commands executed: []
== p11 step (RESULT_IN resume) after 'revoked' ==  ... commands executed: []
```

I could not make a command run under a dead contract by any route I found:
not through `_close_without_running`'s branches, not through the worker
(the shipped `RecordIntentWorker` only prints), not through a second object
(there is no other holder of a `CheckRunner`), and not through `plan`,
`start`, `status`, `stop`, `resume` or `complete`, none of which reach
`_run_command` at all. `check_timeouts` is still wired to no subcommand
(`tools/bm_controller.py:3146` says so).

### AZ F2, the foreign run, is closed at the command line

```
$ bash pF_foreignrun.sh
p2 run 2734dffcb21f4b3ab1245e0bbd3cd52a state BEFORE: PAUSED
bm_controller: refused: upsert_units was called for project 'p1', but run
'2734dffcb21f4b3ab1245e0bbd3cd52a' belongs to project 'p2' ... A run id is
not a capability: name that project's own run, or omit the project and let
the caller's own lookup stand.
EXIT=1
p2 run 2734dffcb21f4b3ab1245e0bbd3cd52a state AFTER:  PAUSED
p2 unit counts: None open dispatches: {'p2-u1': '7bee85fcd59a400db6b91efaa791d8da'}
```

p2 stays PAUSED, keeps its open dispatch and keeps its graph.

An AST sweep of `tools/bm_controller.py` finds 50 calls to the eleven
guarded store methods; 48 pass `project_id=`. The two that do not are
`cmd_resume` (`:3812`) and `cmd_complete` (`:3856`), and both take the run
id from `store.get_run(project_id)` two lines earlier, so there is no
caller-supplied run to disagree with. NO-DATA, not a finding, but they are
the two routes on the opt-out side of the guard and one keyword each would
close that.

### The PAUSED hold matrix

```
$ python3 pI_hold_matrix.py
== hold, resume, accept ==
  record-result -> 'held'  reason: CONTRACT_PAUSED
  after the hold         unit=RESULT_IN dispatch=RESULT_IN  fence=active   run=PAUSED
                         commands=[]
  after both resumes     unit=DONE      dispatch=VERIFIED   fence=complete run=DELIVERABLE_READY
                         commands=['true', 'echo done']
== hold then bm-controller stop ==
  after controller stop  unit=RESULT_IN dispatch=RESULT_IN  fence=parked   run=STOPPED
== hold then bm-autonomy revoke ==
  after autonomy revoke + step unit=RESULT_IN dispatch=RESULT_IN  fence=active   run=PAUSED
== hold then re-plan ==
  re-plan refused: run-paused
== double hold ==
  second record-result refused: already-resulted
  spend-uncharged checkpoints: 1
```

The hold holds, nothing is judged, nothing is rolled back, the fence stays
where it is, the answer survives both resumes and is accepted, a re-plan is
refused, and a second record is refused `already-resulted` with exactly one
disclosure checkpoint.

One observation worth a line, and it belongs to the liveness lens rather
than mine: **hold then `bm-autonomy revoke` leaves the fence ACTIVE and the
run PAUSED indefinitely.** `step()` returns at its own PAUSED guard
(`tools/bm_controller.py:900`) before step 2 can drain, so the kill switch
does not release the fence. It is recoverable (`bm-controller resume` then
`step`, or `bm-controller stop`, which parks it), and `_NOTE_RUN_PAUSED`
names the first of those, so nothing is silent. LOW.

### The literal-write-scope rule stands for the glob characters

```
plain list                   ACCEPTED stored=['a.py']
bare STRING with a glob      REFUSED glob-write-scope
backslash escaped star       REFUSED glob-write-scope
nested list                  REFUSED bad-path
int entry                    REFUSED bad-path
None entry                   REFUSED bad-path
double dot inside            ACCEPTED stored=['a.py']
semicolon in entry           ACCEPTED stored=['a.py; rm -rf ~']
                               rollback="git restore -- 'a.py; rm -rf ~'"
```

Notably: `shlex.quote` does hold, so there is NO shell injection through
`write_scope`. Unicode and percent-encoded lookalikes (the fullwidth star,
`%2A.py`) are accepted but are not glob-active in git or in `fnmatch`, so
they are not a bypass either. NO-DATA on all of these.

---

# ATTEMPTS LOG

Every probe below used its own throwaway store under `mktemp -d` or
`tempfile.TemporaryDirectory()`, with `BROTHERMODE_ROOT` pointed at it for
the CLI runs. No real `.brothermode` store was opened and no repo file was
written. `python3 tools/test_all.py` was NOT run, per the brief.

| # | Attack | Result |
|---|---|---|
| A | Re-run p11 and p12 (stop and revoke, record-result and step) against the real subprocess runner, count commands, check a marker file | FAILED to refute. Zero commands, four ways |
| B | Reach `checker.run` through a second object, the worker, a hook, a CLI command | FAILED. `self.checker.run` appears once, `_run_command` is the only caller path, the shipped worker only prints |
| C | Break the gate with a contract that goes dead between the read and the run | Partly. The one-command TOCTOU is inherent and one command wide; its interesting consequence is S3, not an extra command |
| D | Spend breaker as a second brake on commands | **S2**. Reproduced at the CLI and in process |
| E | `_close_without_running` branches, held path, and whether anything runs there | FAILED to refute. Nothing runs on either branch |
| F | Defeat the AST guard | **S5**. Four ungated spellings pass |
| G | PAUSED hold matrix: hold, resume, accept, stop, revoke, re-plan, double | FAILED to refute the hold. One LOW liveness observation (active fence after a revoke) |
| H | Exploit the uncharged meter past a ceiling | **S7**. 270 tokens against a 100 ceiling, run delivered, meter 0. Downgraded because the numbers are caller-supplied anyway |
| I | Foreign-run write at the CLI, plus an AST sweep of all 50 guarded store calls | FAILED to refute. 48 of 50 pass the keyword, the other 2 cannot cross a project |
| J | Write-scope spellings: unicode, percent-encoded, escaped, separators, nested lists, non-string types, non-list containers | **S4** (bare string), **S6** (scalar container). Unicode and encoded lookalikes are NO-DATA |
| K | Shell injection through `write_scope` into the rollback | FAILED. `shlex.quote` holds |
| L | Git pathspec magic through `write_scope` into the rollback | **S1**. Reproduced end to end, twice, in a real git repo |
| M | Bypass the literal rule through a route other than `upsert_units` | FAILED. `upsert_units` is the only writer of a unit's `write_scope`, and the controller's fence claim reads the post-gate value |

Probe sources are in the session scratchpad under `r5safety/` and are
EPHEMERAL: `h.py` (harness), `clienv.sh` (a throwaway root that is also a
git repo, built by the shipped CLIs), `pA_killswitch.py`,
`pC_scope_shapes.py`, `pD_rollback_escape.sh`, `pD_rootspec.sh`,
`pD_control_narrow.sh`, `pE_meter.py`, `pE2_meter_full.py`,
`pF_foreignrun.sh`, `pG_revoke_midcommand.sh`, `pG2_revoke_midcommand.py`,
`pH_ast_guard.py`, `pI_hold_matrix.py`, `pJ_breaker.py`,
`pJ2_breaker_cli.sh`, `pL_barestring.sh`. Each one is short and its whole
shape is described where it is cited above.

---

# WHAT I DID NOT CHECK

* **`tools/test_all.py` was not run**, per the brief. I make no claim about
  suite health. I ran no unittest class either; every result above is a
  probe.
* **Two real operating system processes contending for one store file**,
  except in S3's reproduction A, where the second process is the
  `bm-autonomy revoke` the done_check spawns. I did not exercise two
  controllers stepping the same project at once.
* **`bm_fence_hook.py` was read for its role in S1 and S4 but never RUN.**
  My claim that a fence over `.` makes every other write refusable, and
  that a fence over `:!keep.txt` protects nothing, follows from the fence
  contents I did observe; I did not drive the hook to see it refuse.
* **`bm_autosave.py`, the `hooks/` directory and the MCP surface** were
  grepped for a subprocess reachable from the eight shipped controller
  commands and none is; I did not audit them for anything else.
* **The `read_scope` half of S4 was measured in process only**, not through
  the CLI, and its consequences (what a worker does with an exploded read
  scope) were not pursued.
* **Windows and Linux.** Everything ran on darwin, with the system git.
  Git's pathspec magic is not platform specific, but the exact `git
  restore` exit codes were observed on this machine only.
* **Whether any of these has occurred in a real run.** Reachability was
  demonstrated; incidence was not.
* **The working tree already carried two changes when I started**
  (`docs/program/absolute-lead/evidence/L03/E4-endtoend.json` modified and
  `docs/program/absolute-lead/DESIGN-insight-ledger-and-handback.md`
  untracked). Neither is mine; this report is the only file I wrote in the
  repository.
