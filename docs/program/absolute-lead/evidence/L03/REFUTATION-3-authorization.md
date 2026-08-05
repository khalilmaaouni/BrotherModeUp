# REFUTATION 3, lens: authorization and TOCTOU in the F2 round-3 fixes

Target: the working tree of /Users/khalil.maaouni/Documents/BrotherModeUp,
tools/bm_controller.py against tools/bm_store.py schema 15. Read only
except this file. No git state was changed. tools/test_all.py was never
run, and no test file was executed at all this pass.

Every probe below ran against its own throwaway Store under a fresh
tempfile.TemporaryDirectory in /tmp, or against a store created by hand in
a fresh mktemp directory for the subprocess runs of the real CLI. No
.brothermode directory inside any real project was opened.

## Verdict lines

| Surface | Verdict | Severity of what survives |
|---|---|---|
| 1. `path_within_allowed` adversarial inputs (bm_store.py:564-603) | STANDS as containment, REFUTED as a boundary | HIGH via the glob branch |
| 2. `gate_check` containment (bm_store.py:12573-12632) | Stated property STANDS, 0 counterexamples in 6682 triples | HIGH, the founder-facing boundary is far wider than the property |
| 3. `_gate_check_write_scope` / `_gate_check_one_pass` straddle and deferral (bm_controller.py:902-1003) | STANDS, 14 placements attempted | none |
| 4. The dispatch stamp (bm_controller.py:1074-1080) | STANDS, 8 constructed races | none |
| The F2 SECURITY PROPERTY as written (bm_controller.py:940-952) | REFUTED by a route that never reaches gate_check | HIGH |

Ten findings with reproductions follow, ordered by severity. Several of
them are pre-existing code the round-3 fix did not touch; each is reported
because it defeats, or is reached through, the exact property this fix
round claims to have established, and each is reachable. Attribution is
stated on every one.

Verdict on surface 3 in one sentence: the straddle machinery is sound. I
fired an amend at every call position of a two-path loop and of a
four-path loop, from inside the first call of the re-run pass, and on
every call at once, and could not make it stamp a revision that some path
of the brief was not judged under, nor make the deferral burn a retry,
drain the run, or fail the unit.

Verdict on surface 4 in one sentence: in all eight races I could construct
with a delegating store wrapper, the recorded contract_revision equalled
the single revision every path of that brief was judged under, and where
the live contract had moved past it the staleness re-read rejected the
dispatch.

---

## F-A1 (HIGH): the worker is handed the full brief with NO gate_check at all

Route: `_resume_dispatched`, tools/bm_controller.py:858-898, called from
`step()` at :466. It builds the brief at :882 and calls
`self.worker.run(brief)` at :890. There is no `gate_check` on this path,
and no re-read of allowed_paths or risk_classes.

Why this refutes F2 rather than merely sitting beside it. The fix's own
docstring at tools/bm_controller.py:946-952 rests the security property on
this sentence: "allowed_paths is the founder's boundary on what the
autonomous system may touch and gate_check is the ONLY component that ever
compares a unit's scope against it: the fence claim (step 6) and the brief
(_build_brief) both carry the FULL write_scope, so a forbidden path listed
second would be claimed and handed to a worker as authorised". On this
route the brief is handed to a worker as authorised while gate_check sees
no path at all. The consequence the docstring names is reached by a
shorter road than the one it closes.

`_resume_dispatched`'s own docstring reasons carefully about the contract
having "moved to stopped/revoked" and about the spend breaker, and I
confirmed both of those guards work (control below). It does not consider
a contract that is still live and NARROWER.

Reproduction, four shipped commands, no concurrency, no second process.
Probe: scratchpad/authz/c1_reawait_no_gatecheck.py.

1. `bm-autonomy sign` with allowed_paths ['docs', 'src'].
2. `bm-controller plan` u1 write_scope ['docs/x.md'], then `bm-controller
   step` with a worker returning status "pending" (exactly what the
   production RecordIntentWorker does). The run parks EXECUTING with an
   open dispatch and an ACTIVE fence.
3. `bm-autonomy sign --supersede` narrowing allowed_paths to ['src']. The
   contract stays LIVE.
4. `bm-controller step`.

```
  WORKER CALL #1 write_scope=['docs/x.md'] attempt=1
wave 1: dispatched=['u1'] state=EXECUTING
dispatch stamped rev=1 status=DISPATCHED
founder narrowed the contract to ['src'], revision 2, state=live
gate_check on docs/x.md under the LIVE contract: REFUSED-SCOPE
  WORKER CALL #2 write_scope=['docs/x.md'] attempt=1
wave 2: note='re-awaited an in-flight dispatch (crash resume or provider-outage recovery)' state=EXECUTING
worker call count: {'u1': 2}
dispatch count (at-most-once still holds): 1
fence still held, files: ['docs/x.md'] state: active
RESULT: the worker was handed a brief whose write_scope the live contract REFUSES, with no gate_check in between: True
```

Control in the same probe, proving the branch is not simply unguarded: a
REVOKE IS caught by step 2 and the run drains without re-asking the
worker.

```
== C1b same shape, but the founder REVOKES instead of narrowing ==
  wave 2 note='draining: contract is revoked' state=STOPPED
  worker calls: {'u1': 1}
```

What survives after the fact: the staleness re-read at
tools/bm_controller.py:1171 still rejects the RESULT when it arrives,
because the revision moved. So the record is eventually correct. What is
NOT recovered is that a worker was told, a second time, to write a path
the founder had just forbidden, and the fence over that path stayed
active. Rejecting the answer afterwards does not un-write the file, which
is the whole reason step 2 sits ahead of the worker rather than behind it.

Attribution: `_resume_dispatched` predates this fix round and the round-2
report did not name it. I am not claiming the fix introduced it. I am
claiming the property the fix states in its own docstring is false while
this route exists, and that a reviewer reading that docstring would
believe otherwise.

---

## F-A2 (HIGH): the glob branch authorises far more than the disclosure says

FIX-round3-report.md disclosure 2 reads: "A glob in allowed_paths still
authorises its literal prefix directory. `allowed_paths ['api/*.py']`
admits `api/notes.md`". That sentence describes a sibling FILE in the same
directory. The rule is `_coverage_key` (tools/bm_store.py:520-534) applied
to the allowed side inside `path_within_allowed` (tools/bm_store.py:600),
and it is much wider than one sibling file.

Probe: scratchpad/authz/a2_glob_widening.py, through `Store.gate_check`,
which is what `bm-autonomy gate-check` and the controller both call.

```
== A2.1 contract allowed_paths ['api/*.py'] ==
    gate_check 'api/pay.py'               -> ALLOWED
    gate_check 'api/notes.md'             -> ALLOWED
    gate_check 'api'                      -> ALLOWED
    gate_check 'api/sub/deep/secrets.env' -> ALLOWED
    gate_check 'api/*'                    -> ALLOWED
    gate_check 'api/**'                   -> ALLOWED
    gate_check 'other/x.py'               -> REFUSED-SCOPE
    gate_check '.'                        -> REFUSED-SCOPE

== A2.2 contract allowed_paths ['*.py'] (root-level glob) ==
    gate_check 'main.py'                          -> ALLOWED
    gate_check 'secrets.env'                      -> ALLOWED
    gate_check 'src/prod/db.sql'                  -> ALLOWED
    gate_check 'infra/terraform/prod.tfstate'     -> ALLOWED
    gate_check '.github/workflows/ci.yml'         -> ALLOWED
    gate_check '.'                                -> REFUSED-SCOPE
```

Three things beyond the disclosure. First, the DIRECTORY itself is
admitted, not only files inside it, so one unit can declare write_scope
['api'] and be authorised over the whole subtree. Second, arbitrary DEPTH
is admitted (`api/sub/deep/secrets.env`), not just the named directory's
own files. Third, a glob whose first segment is the wildcard has the empty
string as its coverage key, and `_prefix_contains` returns True for every
candidate against the empty prefix (tools/bm_store.py:510-517), so
`allowed_paths ['*.py']` is a WHOLE-PROJECT contract in everything except
its own text.

Driven end to end through the controller in the same probe, so this is not
a store-level curiosity:

```
== A2.3 the same contract, driven through the controller ==
  unit write_scope declared: ['api'] (the whole directory)
  dispatched: ['u1'] completed: ['u1']
  brief handed to the worker, write_scope: ['api']
  fence files claimed: ['api']

== A2.4 root-level glob, driven through the controller ==
  dispatched: ['u1'] completed: ['u1']
  brief write_scope: ['infra/terraform/prod.tfstate', 'secrets.env']
  unit status: DONE
```

A contract a founder wrote as "python files at the repo root" accepted,
dispatched and completed a unit whose write scope is the terraform state
and the env file.

Quantified in scratchpad/authz/a4_property_search.py over a 30 path
universe, one allowed path at a time:

```
  allowed='src'            admits 12/30
  allowed='src/*'          admits 12/30
  allowed='src/*.py'       admits 12/30
  allowed='src/app'        admits  5/30
  allowed='*.py'           admits 29/30
  allowed='*'              admits 29/30
  allowed='api/*.py'       admits  5/30   (identical to allowed='api')
```

`src/*.py` and `src` authorise exactly the same set. The glob narrows
nothing.

There is also an internal inconsistency worth naming: under
`allowed_paths ['*.py']` every path in the project is ALLOWED but the
whole root `.` is REFUSED-SCOPE, because the candidate side has an
explicit early return for `.` (tools/bm_store.py:599) while the allowed
side reduces to the empty prefix. The boundary refuses the honest spelling
of what it grants.

Attribution: the reduction is deliberate and pre-existing (it is what
keeps `api/pay.py` working, as the fix report says). The finding is that
the disclosure understates the blast radius by a wide margin, and that
docs/KNOWN-LIMITS.md should say "a glob authorises its whole literal
prefix subtree at any depth, and a leading wildcard authorises the entire
project" rather than naming one sibling file.

---

## F-A3 (HIGH): record-result charges spend to a contract that never authorised the work, then crashes

`receive_result` (tools/bm_controller.py:589-660) takes `project_id` and
`dispatch_id` as INDEPENDENT arguments and never checks that the dispatch
belongs to the named project's current run. In order it: reads project A's
run (:608), records the result against project B's dispatch (:610),
records spend against project A (:649-651), then calls
`self._unit_row(run_id, unit_id)` at :652, which returns None because unit
b1 is not in run A, and dereferences it at :656.

Reproduction through the real shipped CLI as subprocesses, two projects in
one store, each with a token_ceiling of 1000:

```
$ bm_controller.py record-result --project pa --dispatch-id <pb's dispatch> \
    --worker-claim done --artifact src/b.py --tokens 700 --minutes 5 ...
    return COMMANDS[cmd](argv[1:])
  File ".../tools/bm_controller.py", line 2137, in cmd_record_result
    outcome = engine.receive_result(
  File ".../tools/bm_controller.py", line 656, in receive_result
    "fence_uuid": unit["fence_uuid"],
TypeError: 'NoneType' object is not subscriptable
exit=1
spend after:
  pa tokens 700 state VERIFYING
  pb tokens 0 state EXECUTING
```

Consequences, all four confirmed in that run: project A's spend meter is
burned to 70 percent of its ceiling for work project B's contract
authorised; project A's run is moved to VERIFYING with nothing in flight;
project B's dispatch is left RESULT_IN with its unit stuck; and the
failure is a raw Python traceback, because `main()` catches only
`bs.BMStoreError` and `ValueError` (tools/bm_controller.py:2408-2419) and
`TypeError` is neither.

Same defect without a second project, for a caller using the engine
directly: a dispatch id from an OLDER, stopped run of the same project
after a new run has been opened. Probe scratchpad/authz/i1_round6.py, I3:

```
  run 1 state: STOPPED
  run 2 opened: 48c803f5
  UNCAUGHT TypeError: 'NoneType' object is not subscriptable
  run 2 state=VERIFYING
  spend: 3
```

That second route needs an SDK caller, because `cmd_start` only calls
`begin()` when `get_run` returns None (tools/bm_controller.py:1985), so
the shipped CLI cannot open a second run for one project. The two-project
route needs nothing but the CLI.

Attribution: pre-existing, outside the round-3 diff. It is in this report
because the object being confused is the authorisation anchor itself: the
spend recorded is charged against a contract that did not authorise the
dispatch, which is the same class of error surface 4 exists to prevent.

---

## F-A4 (HIGH): `bm-controller plan` traces back on a unit id another project already used

`controller_units.unit_id` is a GLOBAL PRIMARY KEY
(tools/bm_store.py:2472-2473), not `(run_id, unit_id)`. The insert at
tools/bm_store.py:12974 therefore raises a raw `sqlite3.IntegrityError`,
which `main()` does not catch.

Reproduction through the real CLI, two projects in one store, project p1
having planned a unit called "u1":

```
$ bm_controller.py plan --project p2 --units-json '[{"unit_id":"u1", ...}]' ...
    return COMMANDS[cmd](argv[1:])
  File ".../tools/bm_controller.py", line 2085, in cmd_plan
    result = engine.plan(project_id, run_id, units)
  File ".../tools/bm_store.py", line 12974, in upsert_units
    _exec(self,
sqlite3.IntegrityError: UNIQUE constraint failed: controller_units.unit_id
exit=1
```

Unit ids like "u1", "setup" or "tests" across two projects in one store is
the ordinary case, not an exotic one. The same collision blocks a SECOND
RUN of one project for an SDK caller (probe
scratchpad/authz/e2_unit_id_pk.py, E2.1), though the CLI cannot reach that
state for the reason given in F-A3.

One thing held, and is worth recording: the transaction rolls back
cleanly. After the failed plan the run has zero units and sits in
PLANNING, so a re-plan with fresh ids recovers.

```
== E2.3 is the half-written graph rolled back? ==
  plan raised IntegrityError
  project B units after the failed plan: []
  project B run state: PLANNING
```

Attribution: pre-existing schema, outside the round-3 diff. Reported
because it is a shipped-command traceback found while attacking the
authorisation path, and because it blocked one of my own authorization
probes until I renamed the units.

---

## F-A5 (HIGH): gate_check RAISES instead of returning a verdict, and the round-3 call site has no guard

`Store.gate_check` canonicalises the candidate at tools/bm_store.py:12625
with `canonicalize_path`, which raises `OwnershipRefused('path-escape')`
for anything resolving outside the root (tools/bm_store.py:613-652). The
new `_gate_check_one_pass` calls it at tools/bm_controller.py:995-996
inside a bare loop, so the exception leaves `step()` entirely.

Trigger with no concurrency and no malicious input: a write_scope path
whose literal prefix directory becomes a SYMLINK out of the root AFTER the
plan was written. `ln -s /Volumes/Big/build build` is an ordinary thing to
find in a repository. Probe scratchpad/authz/a3_gatecheck_raises.py:

```
planned write_scope: ['build/out.txt']
build/ is now a symlink to a directory outside the root
step RAISED: OwnershipRefused: path 'build/out.txt' resolves outside the project root /private/var/.../tmpscqcj1qc
run state after: EXECUTING
unit status after: READY
step 2 RAISED: OwnershipRefused
step 3 RAISED: OwnershipRefused
bm-autonomy gate-check equivalent RAISED: OwnershipRefused: path 'build/out.txt' resolves outside the project root ...
```

The run is wedged permanently in EXECUTING: the unit is never failed, no
retry is burned, no human step is queued, no interruption is recorded, and
every later `step` repeats the refusal. `bm-controller start` dies on its
first iteration. The CLI does print a clean "refused" line rather than a
traceback for this one, because `OwnershipRefused` IS a `BMStoreError`,
but a refusal that repeats forever with no escalation is the stall F4 was
written to remove, arrived at from the authorisation side.

Compare with the neighbouring refusals, which the same probe family shows
are handled properly: a `..` path, an absolute path and a root escape are
all refused at PLAN time by `upsert_units` (probe
scratchpad/authz/f1_last_round.py, F1.2), so the only way to reach the
raising gate_check is a filesystem change after planning.

Attribution: the missing try/except predates round 3 (round 2's
`_gate_check_write_scope` had none either), but the call now lives in a
function this round created, and the round's own theme was "an illegal
move must not swallow the founder's warning". This is the same shape one
layer up.

---

## F-A6 (HIGH by the reachability rule): the boundary has no path floor, so a whole-project contract authorises the store that holds it

The five safety floors (tools/bm_store.py:2596-2607) are all RISK CLASSES:
credential-entry, payment, account-signin, permanent-delete,
publish-release. There is no path-level floor anywhere in gate_check. A
contract signed with `allowed_paths ['.']`, the natural founder choice for
"work on this repo" and the default in the test fixture
(tools/test_bm_controller.py:271), therefore authorises the store's own
directory. Probe scratchpad/authz/j1_round7.py:

```
  gate_check '.brothermode'               -> ALLOWED
  gate_check '.brothermode/store.db'      -> ALLOWED
  gate_check '.brothermode/store.db-wal'  -> ALLOWED
  gate_check '.git'                       -> ALLOWED
  gate_check '.git/config'                -> ALLOWED
  gate_check '.claude/settings.json'      -> ALLOWED
  dispatched=['u1'] completed=['u1']
  brief write_scope handed to the worker: ['.brothermode/store.db']
  fence files: ['.brothermode/store.db']
```

The unit was dispatched, the fence claimed the database file, and the
brief handed the worker the path to the store holding the contract, the
spend meter, the fence table and the audit trail. The `permanent-delete`
floor ("permanent deletion, or any write to production state") does not
fire, because the class is self-declared by the planner and this unit
declared `file-edit`.

Stated honestly: this is not an attacker capability on its own. It
requires the unit graph to name that path, and the unit graph comes from
the orchestrating model, which the design trusts to plan. What is
demonstrated is that the BOUNDARY does not refuse it: the one component
whose job is to compare a unit's scope against the founder's boundary
returns ALLOWED for the file that stores the boundary. Severity HIGH
follows the brief's reachability rule, not a claim that it is being
exploited today.

Attribution: pre-existing, outside the round-3 diff. Searched SECURITY.md,
INVARIANTS.md, docs/KNOWN-LIMITS.md and docs/FULL-AUTO.md for a disclosure
of it and found none.

---

## F-A7 (MEDIUM): the duplicate-controller refusal is only on begin()

`begin()` claims a persistent controller fence and refuses a second
controller with 'name-active' (tools/bm_controller.py:359-365, confirmed
below). `step()`, `receive_result()` and `stop()` perform no ownership
check at all, so the guard is bypassed by calling `step` instead of
`start`. Probes scratchpad/authz/g1_second_controller.py and
scratchpad/authz/h1_round5.py:

```
== G1.1 ==
  engine B begin() refused: name-active
  engine B step(): dispatched=['u1', 'u2'] completed=['u1', 'u2'] state=DELIVERABLE_READY
  worker B was called for: {'u1': 1, 'u2': 1}
  run row controller_id: ctrlA
  engine B stop() ACCEPTED, run now STOPPED

== H1 a second controller answers the owner's open dispatch ==
  owner ctrlA: unit=DISPATCHED fence owner='ctrlA' state=active
  ctrlB step: completed=['u1'] note='re-awaited an in-flight dispatch (crash resume or provider-outage recovery)'
  after: unit=DONE fence=complete
  ctrlB's worker was called: {'u1': 1}
  run row still owned by: ctrlA
```

A second controller id ran its own worker for a dispatch it did not open,
marked the unit DONE, released a fence owned by ctrlA, and stopped the
run, all while the run row still names ctrlA as the controller.

Honest scoping: my probes are sequential inside one process, so I have NOT
demonstrated two SIMULTANEOUS controllers double-dispatching a unit (the
unit status transitions look like they would refuse that). What is fully
reproduced is that the ownership guard the design places on begin() does
not exist on the three methods that actually drive, answer and terminate a
run. MEDIUM rather than HIGH because the damaging version needs a second
operator or process actually running.

---

## F-A8 (MEDIUM): a non-string write_scope entry is an uncaught AttributeError

`upsert_units` canonicalises every write_scope entry at
tools/bm_store.py:12897-12899. `canonicalize_path` calls `_to_posix`,
which does `(p or "").strip()` at tools/bm_store.py:451. A JSON number,
array or object in write_scope therefore raises `AttributeError`, which
`main()` does not catch. Through the real CLI:

```
$ bm_controller.py plan --project pb --units-json '[{... "write_scope":[5] ...}]' ...
  File ".../tools/bm_store.py", line 672, in canonicalize_path
    posix = _to_posix(p)
  File ".../tools/bm_store.py", line 451, in _to_posix
    p = (p or "").strip()
AttributeError: 'int' object has no attribute 'strip'
exit=1
```

The store already owns the correct behaviour for this exact class on the
FENCE side: `_coerce_path_entry` (tools/bm_store.py:690-720) exists
because "a claim() that silently dropped a non-str entry ... still
returned a Record reporting success". The authorisation input skips that
gate. The unit graph is produced by a model, so a number or a nested
object in write_scope is a realistic input, not a hostile one.

Full matrix, probe scratchpad/authz/g1_second_controller.py G1.2:

```
  [5]              UNCAUGHT AttributeError: 'int' object has no attribute 'strip'
  [['a.py']]       UNCAUGHT AttributeError: 'list' object has no attribute 'strip'
  [{'p': 'a.py'}]  UNCAUGHT AttributeError: 'dict' object has no attribute 'strip'
  [True]           UNCAUGHT AttributeError: 'bool' object has no attribute 'strip'
  ['a\x00.py']     ACCEPTED -> ['a\x00.py']
```

The last row is a separate small oddity: a path containing a NUL byte is
accepted and stored, and flows into the fence and the brief.

---

## F-A9 (LOW): one gate_check verdict formed from two contract revisions

`gate_check` reads the latest contract at tools/bm_store.py:12586 and then
calls `self.spend_totals(project_id)` at :12641, which performs its OWN
`_latest_contract_row` read at :12487 to fetch the ceilings. The two reads
are not in one transaction, so a `sign --supersede` landing between them
produces a single verdict whose class and path halves come from revision N
and whose breaker half comes from revision N+1, reported under revision N,
which is the field the docstring at :12583-12585 says the caller can use
"to prove later which authorisation it acted on".

Probe scratchpad/authz/d1_stamp_races.py D1.5, concurrent writer injected
inside gate_check's own second read:

```
  rev 1: token_ceiling=10, spend=50 -> verdict hard-stop
  gate_check with NO race: REFUSED-BREAKER
  [concurrent writer between gate_check's two contract reads] amended to revision 2, token_ceiling now 100000
  gate_check WITH the race: verdict=ALLOWED revision=1
  under revision 1 alone the verdict is: REFUSED-BREAKER (ceiling 10, spend 50)
```

LOW, with the bound stated plainly. Surface 4's own invariant is not
broken: every PATH was still judged under revision 1, and that is what is
stamped. In the controller the dangerous direction needs TWO amends,
because step 3's own spend gate (tools/bm_controller.py:449-456) would
have hard-stopped first under the low ceiling. On `bm-autonomy gate-check`
one amend is enough to print the mixed verdict to the founder.

---

## F-A10 (LOW): an empty allowed_paths still authorises a unit

A contract signed with `allowed_paths []`, meaning the founder granted no
writable path at all, refuses every named path but ALLOWS a unit whose
write_scope is empty, because the path check at tools/bm_store.py:12623 is
skipped entirely when `path is None`. Probe
scratchpad/authz/f1_last_round.py F1.3:

```
  gate_check path='a.py': REFUSED-SCOPE
  gate_check path=None : ALLOWED
  dispatched=['u1'] completed=['u1']
  unit=DONE fence files=[]
```

The unit is dispatched under its risk class alone with a fence claiming
nothing, so nothing is protected and nothing is compared. Round 2 ruled
the empty write_scope case HELD, and it does hold on its own terms; the
new observation is only that "no path granted" and "no path declared"
combine to mean "authorised".

---

## What STANDS, with the attempt counts

### Containment instead of overlap (surfaces 1 and 2): STANDS

The round-2 ancestor break is genuinely closed, and I could not reopen it.
Probe scratchpad/probe_a1_pwa_matrix.py ran 38 adversarial input pairs
through `path_within_allowed` directly:

```
'src/app'      'src'                          False  ancestor (was the round-2 break)
'src/app'      '.'                            False  root candidate
'src/app'      'src/appendix.py'              False  sibling prefix a/bc
'src/app'      'src/app-secrets.env'          False  sibling prefix with dash
'src/app'      'src/app/../secrets.env'       False  dotdot escape in candidate
'src/app'      'src/app/'                     True   trailing slash under
'src/app'      ''                             False  empty candidate
''             'src/app'                      False  empty allowed
'src/app'      None                           False  None candidate
None           'src/app'                      False  None allowed
'src/app'      'src/*'                        False  glob candidate at ancestor level
'src/app'      '*'                            False  bare star candidate
```

No input raised. None and the empty string are handled. Backslashes,
trailing slashes, dot segments and dotdot segments normalise identically
on both sides.

The stated property was then searched exhaustively rather than argued.
Probe scratchpad/authz/a4_property_search.py enumerates every allowed set
of size 1 and 2 over 14 path shapes, crosses them with 30 candidates, and
for every ALLOWED candidate C tests every file F in the universe that C
names (equal, strictly under, or matched by C read as a glob), looking for
an F that is REFUSED:

```
allowed sets checked: 105
(allowed, candidate, file) triples checked: 6682
counterexamples to the stated property: 0
```

The first run of that probe reported 55 counterexamples, all of them
artifacts of my own `names()` relation (it counted `src/app/../secrets.env`
as named by `src/app`, and `.` as a file matched by `*`). Both sides are
now put in the store's own canonical form first and `.` is excluded as a
file. Recording the false start because the corrected result is the one
that matters: the property as WORDED holds. What does not hold is the
founder's reading of it, which is F-A2.

Unicode and case folding attack, REFUTED with filesystem evidence.
`_normcase` case-folds on darwin and win32, and `'ss'.casefold() ==
'ß'.casefold()`, so `allowed_paths ['ss']` admits `ß/secret.env`. I
expected a widening and checked the filesystem instead of assuming:

```
$ mkdir ss && mkdir "ß"
mkdir: ß: File exists
$ python3 -c "print(os.stat('ss').st_ino, os.stat('ß').st_ino)"
143884270 143884270
```

On this APFS volume `ss` and the sharp s are ONE directory with one inode,
and the same holds for `k` and the Kelvin sign. The fold matches the
filesystem, so it authorises nothing extra. On a case-sensitive platform
`_normcase` does not fold at all. No finding.

### The straddle machinery (surface 3): STANDS, 14 placements

Probes scratchpad/authz/b1_straddle.py, b2_deferral_and_control.py and
k1_round8.py. The concurrent writer is a supersede amend fired from inside
a chosen gate_check call, the same simulation round 2 used.

Amend inside call 1 of the first pass, the round-2 break, now caught by
the re-run:

```
    gate_check #1 path='docs/x.md'    -> ALLOWED       rev=1
    [concurrent writer] amended to revision 2, allowed_paths now ['src']
    gate_check #2 path='src/a.py'     -> ALLOWED       rev=2
    gate_check #3 path='docs/x.md'    -> REFUSED-SCOPE rev=2
  wave 1 dispatched=[] completed=[] state=EXECUTING
  unit status=READY retry_count=1
```

No dispatch, no stamp, the forbidden path refused under the newer
contract. The round-2 reproduction does not reproduce.

Amend on EVERY gate_check call, which is the double straddle the deferral
exists for, run for three waves:

```
  wave 1 dispatched=[] completed=[] state=EXECUTING
  wave 2 dispatched=[] completed=[] state=EXECUTING
  wave 3 dispatched=[] completed=[] state=EXECUTING
  unit status=READY retry_count=0
  run state: EXECUTING
  open human steps: 0
```

Every claim the fix makes for the deferral holds: no drain, no
`mark_unit_failed`, no retry burned, the unit stays READY. And when the
amender stops, the unit is genuinely retried, not stranded:

```
== B2.1 deferral on wave 1 only, then a quiet wave 2 ==
  after wave 1: unit status=READY retry=0 run=EXECUTING dispatches=0
  wave 2 dispatched=['u1'] completed=['u1'] state=DELIVERABLE_READY
  dispatch stamped rev=5 status=VERIFIED
  live revision: 5
```

A REFUSED-SCOPE earned on the RE-RUN pass is handled identically to one
earned on the first pass, checked against a no-race control:

```
== B2.2 control: REFUSED-SCOPE with NO race (first pass) ==
  after wave 1: unit status=READY retry=1 run=EXECUTING dispatches=0 human_steps=0
  worker called: {}

== B2.3 REFUSED-SCOPE earned on the RE-RUN pass ==
  after wave 1: unit status=READY retry=1 run=EXECUTING dispatches=0 human_steps=0
  worker called: {}

== B2.4 retry ceiling under a permanent refusal (both shapes) ==
  no race      steps=2 unit=FAILED retry=2 run=EXECUTING human_steps=0
  re-run pass  steps=2 unit=FAILED retry=2 run=EXECUTING human_steps=0
```

Identical status, retry count, run state, note and worker call count.

The brief asked specifically about an amend fired from inside the FIRST
call of the RE-RUN pass. Two shapes were run. When that first re-run call
returns a REFUSAL the loop short-circuits on the refusal and never sees
the straddle (B1.2), which is conservative: the unit is failed, nothing is
dispatched. When it returns ALLOWED and a later call straddles, the second
straddle fires and the unit defers (B1.3). Neither produces a dispatch.

### The dispatch stamp (surface 4): STANDS, 8 races

Probes scratchpad/authz/d1_stamp_races.py, i1_round6.py and k1_round8.py.
The amend was fired from inside gate_check's last call, inside `claim`,
inside `claim_unit`, inside `record_dispatch`, and between the two units
of one wave; and a four-path write scope was swept with the amend placed
after each call position in turn.

```
== D1 amend fired inside gate_check ==      revisions judged [1]  STAMP=1  in judged set: True  status=REJECTED
== D1 amend fired inside claim ==           gate_check re-read first, REFUSED-SCOPE rev=2, no dispatch
== D1 amend fired inside claim_unit ==      revisions judged [1]  STAMP=1  in judged set: True  status=REJECTED
== D1 amend fired inside record_dispatch == revisions judged [1]  STAMP=1  in judged set: True  status=REJECTED

== I1 amend between two units of one wave ==
  u1: judged under [1], STAMP=1, match=True, status=REJECTED
  u2: judged under [2], STAMP=2, match=True, status=VERIFIED

== four paths, amend after each call in turn ==
amend after call 1: judged_revs=[1, 2] stamp=2  revisions of the judging pass: [2, 2, 2, 2]  covers every path: True
amend after call 2: judged_revs=[1, 2] stamp=2  revisions of the judging pass: [2, 2, 2, 2]  covers every path: True
amend after call 3: judged_revs=[1, 2] stamp=2  revisions of the judging pass: [2, 2, 2, 2]  covers every path: True
amend after call 4: judged_revs=[1]    stamp=1  revisions of the judging pass: [1, 1, 1, 1]  covers every path: True
```

In every case the stamp equalled the single revision the judging pass used
for all four paths, and where the live contract had moved past the stamp
the staleness re-read rejected the dispatch (status REJECTED) instead of
accepting it. I could not construct a race that stamps a revision some
path was not judged under.

### Other attacks that held

- A concurrent re-plan while the run is EXECUTING, which round 2 named as
  the reason "the same in-memory unit row" is safe, is genuinely refused:
  `run '...' is EXECUTING; upsert_units always flips a run to READY, but
  that move is not legal from there`.
- `..`, absolute paths and glob-tail escapes are refused at PLAN time with
  reason `path-escape`, and `sign_contract` refuses an absolute
  allowed_path the same way.
- `gate_check` with action_class None, "", wrong case, trailing space or a
  non-string all return REFUSED-CLASS rather than raising.
- Path spellings converge: `src/app`, `src/app/`, `./src/app`,
  `src/./app`, `src/app/.`, `SRC/APP` and `src//app` all reach the same
  verdict, and leading or trailing whitespace is stripped identically on
  both sides.
- A duplicate `receive_result` on one dispatch is refused cleanly and the
  spend meter does not move (1 token after one accepted and one refused
  result).
- A contract WIDENED while a dispatch is open still rejects the in-flight
  result, because the staleness re-read compares revisions rather than
  scopes. That is a false rejection and a burned retry, not an
  authorisation hole. Recorded as a cost, not a finding.

---

## Attempts log

Probes live in the session scratchpad under `authz/`
(/private/tmp/claude-1598639508/-Users-khalil-maaouni-Documents-Development-Work-Frameworks-BrothermeUp/e2edd454-7254-4d3a-ad14-5c05858ffb3a/scratchpad/authz),
which is EPHEMERAL. Every sequence and every output block above is
reproduced in full here, so each finding can be rebuilt from this file
alone.

| # | Round | Attack | Probe | Result |
|---|---|---|---|---|
| 1 | 1 | 38 adversarial inputs to `path_within_allowed` | probe_a1_pwa_matrix.py | HELD as containment, glob branch flagged |
| 2 | 1 | sharp-s and Kelvin casefold widening | mkdir plus inode check on APFS | HELD, fold matches the filesystem |
| 3 | 1 | glob allowed path admits the directory and any depth | authz/a2_glob_widening.py | BREAK, F-A2 |
| 4 | 1 | leading-wildcard allowed path admits the whole project | authz/a2_glob_widening.py A2.2/A2.4 | BREAK, F-A2 |
| 5 | 1 | gate_check raising instead of refusing (symlink after plan) | authz/a3_gatecheck_raises.py | BREAK, F-A5 |
| 6 | 2 | exhaustive counterexample search, 105 sets, 6682 triples | authz/a4_property_search.py | HELD, 0 counterexamples |
| 7 | 2 | amend inside call 1 of the first pass | authz/b1_straddle.py B1.1 | HELD |
| 8 | 2 | amend inside call 1 of the RE-RUN pass | authz/b1_straddle.py B1.2 | HELD |
| 9 | 2 | amend on every call, double straddle deferral | authz/b1_straddle.py B1.3 | HELD |
| 10 | 2 | amend inside the LAST call of pass 1 | authz/b1_straddle.py B1.4 | HELD, staleness rejects |
| 11 | 2 | single-path unit, amend inside its only call | authz/b1_straddle.py B1.5 | HELD, staleness rejects |
| 12 | 2 | deferral does not burn a retry or drain, unit retried next wave | authz/b2_deferral_and_control.py B2.1 | HELD |
| 13 | 2 | REFUSED-SCOPE on the re-run pass versus a no-race control | authz/b2_deferral_and_control.py B2.2/B2.3/B2.4 | HELD, identical |
| 14 | 3 | brief handed to a worker with no gate_check (re-await) | authz/c1_reawait_no_gatecheck.py | BREAK, F-A1 |
| 15 | 3 | revoke control for the same route | authz/c1_reawait_no_gatecheck.py C1b | HELD, drains |
| 16 | 3 | stamp under races inside claim, claim_unit, record_dispatch | authz/d1_stamp_races.py | HELD |
| 17 | 3 | gate_check's own two contract reads split by an amend | authz/d1_stamp_races.py D1.5 | BREAK, F-A9 (LOW) |
| 18 | 4 | non-string write_scope entry | authz/e1_round3_ideas.py, authz/g1_second_controller.py G1.2, real CLI | BREAK, F-A8 |
| 19 | 4 | concurrent re-plan while EXECUTING | authz/e1_round3_ideas.py E1.2 | HELD, refused |
| 20 | 4 | global unit_id primary key | authz/e2_unit_id_pk.py, real CLI | BREAK, F-A4 |
| 21 | 4 | absolute paths, `..`, glob-tail escapes at plan and at sign | authz/f1_last_round.py F1.1/F1.2 | HELD |
| 22 | 4 | allowed_paths=[] with an empty write_scope | authz/f1_last_round.py F1.3 | BREAK, F-A10 (LOW) |
| 23 | 4 | path spelling convergence | authz/f1_last_round.py F1.4 | HELD |
| 24 | 4 | second controller drives a run it does not own | authz/g1_second_controller.py G1.1 | BREAK, F-A7 |
| 25 | 5 | second controller answers the owner's open dispatch | authz/h1_round5.py H1 | BREAK, F-A7 |
| 26 | 5 | record-result naming project A with project B's dispatch | authz/h1_round5.py H2, real CLI | BREAK, F-A3 |
| 27 | 5 | gate_check action_class edge values | authz/h1_round5.py H3 | HELD |
| 28 | 6 | amend between two units of one wave | authz/i1_round6.py I1 | HELD |
| 29 | 6 | contract WIDENED while a dispatch is open | authz/i1_round6.py I2 | Observation, false rejection |
| 30 | 6 | dispatch from an older terminal run of the same project | authz/i1_round6.py I3 | BREAK, F-A3 second route |
| 31 | 7 | the store's own directory under a `.` contract | authz/j1_round7.py J1 | BREAK, F-A6 |
| 32 | 7 | whitespace, tab and newline in a declared path | authz/j1_round7.py J2 | HELD |
| 33 | 7 | duplicate receive_result | authz/j1_round7.py J3 | HELD |
| 34 | 8 | four-path straddle sweep, amend after every call position | authz/k1_round8.py | HELD, nothing new |

Discovery stopped at round 8, which produced no new break: the four-path
sweep across all eight amend placements confirmed the straddle detector
and the stamp at every position. Rounds 1 to 7 each produced at least one
new break, which is why the loop ran that long.

---

## What I did not check

- tools/test_all.py, the suite lock. Not run, as instructed. I also did
  not run tools/test_bm_controller.py or tools/test_bm_store.py at all, so
  I make NO claim about whether the round-3 tests still pass. Every result
  above comes from a standalone probe or a real CLI subprocess.
- Genuine multi-process concurrency. Every "concurrent writer" is a
  delegating wrapper inside one process, exactly as REFUTATION-2 and the
  round-3 fix's own tests simulate it. The SQLite locking behaviour of two
  real `bm-controller` processes against one store is untested, and
  F-A7's damaging version (two simultaneous drivers) is therefore argued
  from the guard's absence, not from an observed double dispatch.
- F1, F3 and F4 territory. I read `_handle_late_result`, `check_timeouts`
  and `run_to_completion` only far enough to know they were not my lens,
  and did not attack them. Two things noticed in passing and not pursued:
  a run parks in EXECUTING with ZERO open human steps after a gate_check
  refusal exhausts a unit's retries (authz/b2_deferral_and_control.py
  B2.4), and `cmd_start` can never open a second run for a project once
  the first is terminal (tools/bm_controller.py:1985), which that
  docstring says is deliberate.
- tools/bm_autonomy.py's `cmd_gate_check` was read, not driven. Its
  documented root-relative path convention (tools/bm_autonomy.py:126-133)
  is an explicit, disclosed deviation, so I did not treat it as a finding.
- `read_scope` and the `surface` argument to gate_check. read_scope is
  deliberately not gate-checked and round 2 already ruled that NO-DATA;
  `surface` is never passed by the controller.
- tools/bm_bash_audit.py, the advisory after-the-fact net. Whether it
  would catch any of the writes authorised above is unexamined.
- The PAUSED and STOPPING interaction with the per-path loop. I fired
  amends and supersedes, never a pause landing mid-loop.
- Every finding marked "pre-existing" was confirmed as reachable but NOT
  bisected against git history; the attribution rests on reading the
  round-3 fix report's own list of changed lines, not on a diff I ran.
- tools/bm_store.py was read only where the authorisation path touches it
  (path helpers, gate_check, sign_contract, spend_totals, upsert_units,
  claim, the schema for controller_units). The rest of its 15256 lines was
  not reviewed.
