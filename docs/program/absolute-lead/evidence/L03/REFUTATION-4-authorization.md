# REFUTATION 4, the AUTHORISATION lens

Target: the CURRENT working tree at /Users/khalil.maaouni/Documents/BrotherModeUp,
after FIX-round4-store-report.md and FIX-round4-controller-report.md landed.

Read in full before probing: DESIGN-round4.md, FIX-round4-store-report.md,
FIX-round4-controller-report.md (including its three collisions),
REFUTATION-2-fixes.md, REFUTATION-3-authorization.md.

Every probe ran against its own throwaway Store under a fresh
tempfile.TemporaryDirectory(), or against a throwaway BROTHERMODE_ROOT under
/tmp driven by the shipped CLI. No real .brothermode directory was touched.
tools/test_all.py was NOT run. No file in the tree was modified except this
report. No git state was changed (the only git commands run were
`git status`, `git log` and a `git init` inside a throwaway /tmp directory
used to measure a pathspec).

Probe sources are in this session's scratchpad (p2, p3b, p4, p5, p7, p7b, p8,
p9, p10, p11, p12, p13, p14, p15 plus probe_common.py). That directory is
EPHEMERAL; every reproduction below is written out here in full, with its
verbatim output, so this page stands alone.

---

## VERDICTS, one line each

| # | Verdict | Sev | One line |
|---|---|---|---|
| F1 | **REFUTED** | HIGH | Glob containment was narrowed on the CANDIDATE side only. A unit that DECLARES the same glob is still ALLOWED, and the fence it claims plus the hook that enforces it still reduce that glob to its literal prefix, so `allowed_paths ['*.py']` still authorises the WHOLE project. AZ F-A2 is not closed, and gate_check's own stated property is false. |
| F2 | **REFUTED** | HIGH | `bm-controller plan --project p1 --run <another project's run id>` writes the foreign run: it un-pauses a PAUSED run (law L1), cancels its open dispatches, parks its fences and replaces its unit graph. `plan`'s new PAUSED guard checks a different run from the one it writes. |
| F3 | **REFUTED** | HIGH | A glob write_scope is never resolved past its literal prefix, so gate_check ALLOWS a scope whose files resolve OUTSIDE the project root, while refusing the same path named directly. `src/[a]pp` is ALLOWED where `src/app` is REFUSED-SCOPE. |
| F4 | **REFUTED** | HIGH | The PAUSED hold does not hold on the only route to PAUSED the shipped CLI has: the meter is never charged (SM C reopened for the held path) and the held answer is REJECTED as stale on resume, running `git restore` against the founder's files and burning a retry, which is exactly what design 18.1 says it removed. The new test reaches PAUSED through a route no shipped command has. |
| F5 | **REFUTED** | HIGH | After the 3am kill switch (`bm-autonomy stop`, or `revoke`), one `bm-controller record-result` still executes the unit's own done_check command AND a `git restore` rollback in the project root. Round 4's section 10.6 is what ADDED the rollback to that branch. |
| F6 | **REFUTED** | MEDIUM | A unit_id that `upsert_units` accepts but `valid_name` refuses wedges the run permanently in EXECUTING: every `step` exits 1, and `plan`, the documented recovery, is refused from EXECUTING. |
| F7 | **REFUTED** | MEDIUM | The other half of LV 7's crash window (fence claimed, `claim_unit` not yet committed) leaves an ACTIVE unit fence with the unit still READY. No orphan branch sees it, and every later step parks on CONTENTION forever with a note that says no founder action is needed. |
| F8 | **REFUTED** | MEDIUM | The re-await route checks the fence's STATE and never its CONTENT or its owner, so a fence emptied under an open dispatch still re-awaits and hands out a brief for files the fence no longer holds. |
| F9 | **REFUTED** | MEDIUM | `read_scope` is never canonicalised and never checked, so a brief hands a worker `/etc`, `../../../Users` and `~/.ssh/id_rsa` as its read scope while the identical entry in `write_scope` is refused `path-escape` at plan time. |
| F10 | **REFUTED (data for a deferral)** | LOW | A unit with an EMPTY write_scope is dispatched under a narrow contract and claims an EMPTY fence. Design 16.3 defers this as NO-DATA; here is the data. |
| F11 | **REFUTED** | LOW | `gate_check` DOES raise. `_coerce_path_entry` is documented as TOTAL and is not: an object whose `__fspath__` or `__repr__` raises anything but TypeError escapes as itself. |
| F12 | **REFUTED** | LOW | Two founder-facing notes state causes that did not happen: `_resume_dispatched`'s default REFUSED note blames the live contract for a fence problem, and `_NOTE_CONTENTION`'s "no founder action is needed" is unconditional and false in F7. |
| S1 | **STANDS** | | The ONE choke point. Two `self.worker.run` sites in the whole tree, both obtaining their brief from `_authorise_dispatch`; `record_dispatch` and `_build_brief` have no other caller. 6 attacks, including the rebuilt `_resume_dispatched` and all three crash-resume branches, produced no route to a worker without a gate check. |
| S2 | **STANDS** | | The foreign-dispatch guard in `receive_result`. A dispatch of another project refuses `foreign-dispatch` with nothing recorded, no run moved and no meter charged. AZ F-A3 and SM K are closed. |
| S3 | **STANDS** | | The CANCELLED dispatch law, on its own terms: `record_result` refuses `dispatch-cancelled`, a revived unit gets a FRESH attempt and never the cancelled one, a double drop is idempotent under the 2-tuple contract, and a CANCELLED dispatch is invisible to `_open_dispatch_units` and to `check_timeouts`. 7 attacks, no counterexample. |
| S4 | **STANDS** | | The NON-glob branch of `path_within_allowed`. 23595 triples, 0 containment violations with a non-glob allowed path, under both readings of "names a file". |
| S5 | **STANDS** | | `_rollback_command` shell quoting (`shlex.quote`, no injection) and the glob rule's regex behaviour (no catastrophic backtracking on Python 3.9.6). |

Scoring rule used: HIGH means reachable from the shipped CLI or the
production engine loop, MEDIUM means it needs a crash at a named
two-statement boundary, a concurrent writer or an SDK caller, LOW means
founder-facing prose or an exotic input.

---

# THE FINDINGS

## F1 (HIGH) Glob containment narrowed the candidate side only, so the whole-project grant AZ F-A2 found is still there

### The property that is claimed

tools/bm_store.py:12634, inside `gate_check`'s own docstring:

```
     The property this establishes, stated so a reader can hold
     the code to it: a path this check ALLOWS can never name a
     file that a directly named path would be REFUSED for.
```

DESIGN-round4 section 5.1 restates it as the teachable rule: "a plain path
grants its subtree, a glob grants exactly what it matches at its own depth."

### The rule as landed

tools/bm_store.py:621 to 631:

```python
    if not _has_glob(na):
        return _prefix_contains(na, nb)
    a_segs = na.split("/")
    b_segs = nb.split("/")
    if len(a_segs) != len(b_segs):
        return False
    return all(fnmatch.fnmatchcase(b, a) for a, b in zip(a_segs, b_segs))
```

The rule narrows which CANDIDATE strings a glob admits. It changes nothing
about what a candidate, once admitted, goes on to name. Three things read the
admitted string afterwards, and all three still use the pre-round-4
coverage-key reduction, which `_coverage_key` (tools/bm_store.py:520) and
`paths_overlap` (tools/bm_store.py:537) keep verbatim by design ("`paths_overlap`,
`_coverage_key` and `_literal_prefix_dir` are NOT touched", design 5.1):

1. `_authorise_dispatch` claims the fence over the unit's write_scope
   (tools/bm_controller.py:1633);
2. `_build_brief` hands the same write_scope to the worker
   (tools/bm_controller.py:1650);
3. tools/bm_fence_hook.py:637 decides whether a write is inside that fence
   with `bs.paths_overlap(rel, r["path"])`.

### Reproduction 1: the property search, re-run against the NEW rule

Probe p9, 23595 (allowed, candidate, file) triples over every one and two
segment path built from `src app api * ?pp [ab] *.py a.py b.py ** secrets.env deep`,
against a fixed file set. Two definitions of "names a file" are reported so
the result cannot be argued away: STRICT (a glob names only what it matches at
its own depth, the design's own reading) and FENCE (what the claim and the
hook actually cover).

```
$ python3 p9_property_search.py
STRICT (a glob names only its own depth): 23595 triples checked, 38 violations, 38 of them with a GLOB allowed path, 0 with a NON-GLOB allowed path
   allowed='*'        allows 'src'        -> refuses 'src/app/main.py'
   allowed='*'        allows 'api'        -> refuses 'api/pay.py'
   allowed='**'       allows 'src'        -> refuses 'src/app/main.py'
   allowed='src/*'    allows 'src/app'    -> refuses 'src/app/main.py'
   allowed='src/?pp'  allows 'src/app'    -> refuses 'src/app/main.py'
   allowed='src/**'   allows 'src/app'    -> refuses 'src/app/main.py'
   allowed='*/app'    allows 'src/app'    -> refuses 'src/app/main.py'
   allowed='*/*'      allows 'src/app'    -> refuses 'src/app/main.py'
   allowed='**/app'   allows 'src/app'    -> refuses 'src/app/main.py'

FENCE  (what the claim and the hook actually cover): 23595 triples checked, 5119 violations, 5119 of them with a GLOB allowed path, 0 with a NON-GLOB allowed path
   allowed='*'        allows '*.py'       -> refuses 'src/app/main.py'
   allowed='*.py'     allows '*.py'       -> refuses 'src/app/main.py'
   allowed='?pp'      allows '?pp'        -> refuses 'src/app/main.py'
   ...

non-glob allowed paths, violations: STRICT=0 FENCE=0
```

The non-glob branch is clean, exactly as design 5.1 promised (that is verdict
S4). Every violation comes from the new glob branch.

### Reproduction 2: the whole-project grant, end to end

Probe p10. Contract `allowed_paths ['*.py']`, one unit whose `write_scope` is
the same glob:

```
$ python3 p10_leading_wildcard_whole_project.py
contract allowed_paths: ['*.py']
gate_check per path, named DIRECTLY:
   'infra/terraform/prod.tfstate'     -> REFUSED-SCOPE
   'src/app/main.py'                  -> REFUSED-SCOPE
   '.git/config'                      -> REFUSED-SCOPE
   '.brothermode/store.sqlite3'       -> REFUSED-SCOPE
   'secrets.env'                      -> REFUSED-SCOPE
   '*.py'                             -> ALLOWED
   'main.py'                          -> ALLOWED

step: dispatched=['u1'] state=DELIVERABLE_READY
brief write_scope: [['*.py']]
fence files: ['*.py']
coverage key of '*.py': ''
   fence claim '*.py' covers 'infra/terraform/prod.tfstate'     -> True   (tools/bm_fence_hook.py:637 uses exactly this call)
   fence claim '*.py' covers 'src/app/main.py'                  -> True
   fence claim '*.py' covers '.git/config'                      -> True
   fence claim '*.py' covers '.brothermode/store.sqlite3'       -> True
   fence claim '*.py' covers 'secrets.env'                      -> True
```

The coverage key of `*.py` is the empty string, which `_prefix_contains`
(tools/bm_store.py:512) treats as the root. That is AZ F-A2's own sentence,
word for word ("because a leading wildcard reduces to the EMPTY prefix which
`_prefix_contains` treats as the root, `['*.py']` admitted the WHOLE project,
terraform state and env file included", now quoted back in
`path_within_allowed`'s docstring as a thing of the past).

### Reproduction 3: four shipped commands, no concurrency

```
$ export BROTHERMODE_ROOT=/tmp/az4glob.beXrrO
$ python3 tools/bm_store.py init
$ python3 tools/bm_project.py start --project-id p1 ...
$ python3 tools/bm_autonomy.py sign --project p1 --outcome ship \
      --done-definition true --allowed-path '*.py' --risk-class file-create \
      --signed-by "Khalil Maaouni" --actor-type human --actor-name khalil --session-id sess1
--- bm-autonomy gate-check, each path named directly ---
  infra/terraform/prod.tfstate -> REFUSED-SCOPE: 'infra/terraform/prod.tfstate' is outside this contract's allowed paths. (revision 1)
  .git/config -> REFUSED-SCOPE: '.git/config' is outside this contract's allowed paths. (revision 1)
  src/app/main.py -> REFUSED-SCOPE: 'src/app/main.py' is outside this contract's allowed paths. (revision 1)
  *.py -> ALLOWED: authorised against risk class 'file-create'. (revision 1)
$ python3 tools/bm_controller.py plan --project p1 --run $R --units-file /tmp/az4glob.json ...
planned 1 unit(s) for run 1885ed862d41460dbb87e98433bc6202
$ python3 tools/bm_controller.py step --project p1 ...
{"controller_brief": {"attempt": 1, "objective": "edit the python files", "prior_failure_note": "", "read_scope": [], "risk_class": "file-create", "role": "builder", "unit_id": "u1", "write_scope": ["*.py"]}}
run 1885ed862d41460dbb87e98433bc6202: state EXECUTING
dispatched: u1
reason: IN_FLIGHT
```

The units file is one object with `"write_scope": ["*.py"]`. That is the whole
attack: spell the write scope the same way the contract spells the boundary.

### Reproduction 4: the plain directory candidate, which needs no glob in the unit at all

Probe p2. Contract `allowed_paths ['src/*']`, unit write_scope `['src/app']`:

```
contract allowed_paths: ['src/*']
  gate_check('src/app'               ) -> ALLOWED
  gate_check('src/app/main.py'       ) -> REFUSED-SCOPE
  gate_check('src/app/deep/keys.pem' ) -> REFUSED-SCOPE
  gate_check('src'                   ) -> REFUSED-SCOPE

step summary: dispatched=['u1'] state='DELIVERABLE_READY' reason=None
brief handed to the worker: [['src/app']]
fence files claimed: ['src/app']  state='complete'
fence covers src/app/deep/keys.pem: True
```

A plain directory is the recursive spelling by the design's own rule, so a
glob contract grants a subtree the moment any unit names a directory the glob
matches. tools/test_bm_store.py:17446 and 17480 assert this exact pair
(`("src/app", "ALLOWED")` beside `("src/app/main.py", "REFUSED-SCOPE")`), and
tools/test_bm_store.py:17420 asserts `("api/*.py", "ALLOWED")` beside
`("api/sub/deep/secrets.env", "REFUSED-SCOPE")`. The suite pins the hole in
the same table that pins the fix.

### Why this is damage and not bookkeeping

`_rollback_command` (tools/bm_controller.py:1915 to 1921) composes
`git restore -- <shlex.quote(p) for p in write_scope>` and every rejection
path runs it. For write_scope `['*.py']` that is `git restore -- '*.py'`, and
git pathspec globbing is recursive. Measured in a throwaway repository:

```
$ git init -q .; ...three files committed, then all three modified...
before:
 M other/keep.txt
 M src/deep/nested.py
 M top.py
--- running the rollback the controller composes for write_scope ['*.py'] ---
git restore -- '*.py'
EXIT=0
after:
 M other/keep.txt
top.py now: v1
src/deep/nested.py now: v1
```

`src/deep/nested.py` is at a depth the round-4 rule says the glob does not
grant, and the engine's own rollback destroys the founder's uncommitted work
there.

### Smallest honest fix, for whoever owns it

Either refuse a glob on the DECLARATION side (a write_scope entry containing
`* ? [` refused at `upsert_units`, so the depth-exact rule only ever meets
depth-exact paths), or make the fence and the hook use the same depth-exact
containment the gate now uses. Narrowing one of the three readers and leaving
the other two on coverage keys is what produced this.

---

## F2 (HIGH) `plan` takes run_id as an independent argument and never checks it against the project, so a plan aimed at p1 un-pauses and rewrites p2

### The code

tools/bm_controller.py:608 to 623:

```python
        run = self._run_or_refuse(project_id)
        self._refuse_if_paused(run, "plan")
        ...
        result = self.store.upsert_units(run_id, units, self.actor)
```

`run` is the project's CURRENT run. `run_id` is the caller's argument. The
PAUSED guard design 4.2 added is applied to `run`, and every write lands on
`run_id`. tools/bm_controller.py:2811 is where the shipped command lets the
founder supply it:

```python
        run_id = kv.get("run") or run["run_id"]
```

`upsert_units` takes its `project_id` from the run row it was handed
(tools/bm_store.py:12969), so the foreign write is fully consistent with
itself and refuses nothing.

### Reproduction, entirely through the shipped CLI

Root /tmp/az4cli.vpBzjU. p2 is a healthy run with work in flight, paused by
the founder the only way the CLI allows.

```
$ python3 tools/bm_controller.py step --project p2 ...
note: waiting for 1 open dispatch(es); record a result with bm-controller record-result
reason: IN_FLIGHT
$ python3 tools/bm_autonomy.py pause --project p2 --reason "founder pressed pause" ...
project p2 contract -> paused (revision 2)
$ python3 tools/bm_controller.py step --project p2 ...
note: contract is paused
reason: FOUNDER_WAITING
--- p2 status BEFORE ---
project p2: run ac6123b17f5247a8bca948001336948b, state PAUSED (workflow version 1)
units: 1 total
  DISPATCHED: 1
open dispatches (record a result for each):
  v1: dispatch 9f3848070fe64bea90708962d24434f0
```

Now one command aimed at p1, carrying p2's run id:

```
$ python3 tools/bm_controller.py plan --project p1 --run ac6123b17f5247a8bca948001336948b \
      --units-file /tmp/az4u9.json --controller-id ctrl1 --actor-type model --actor-name c --session-id s1
planned 1 unit(s) for run ac6123b17f5247a8bca948001336948b
dropped 1 unit(s) from the graph: v1
cancelled 1 open dispatch(es) belonging to those units; a result for one of them will now be refused
EXIT=0
--- p2 status AFTER ---
project p2: run ac6123b17f5247a8bca948001336948b, state READY (workflow version 1)
units: 2 total
  READY: 1
  SKIPPED: 1
--- p1 status AFTER ---
project p1: run 44e91da67463418682e39451780f7f78, state READY (workflow version 1)
units: 1 total
  READY: 1
--- p2 contract ---
project p2: revision 2, state paused
```

Five things happened to a project the command did not name: the run left
PAUSED (law L1: "Only `bm-controller resume` leaves PAUSED"), an open dispatch
was CANCELLED, a fence was parked, the unit graph was replaced by another
project's units, and p2 is now a READY run under a PAUSED contract.

The in-process probe p6 shows the unit rows carry p2's project_id:

```
plan(--project p1 --run <p2 run>) returned: {'count': 1, 'skipped': ['v1'], 'cancelled_dispatches': ['3663a...'], 'orphaned_fences': [('v1', 'd5d1c...')]}
p2 run state AFTER: READY
p2's unit v1: SKIPPED
p2's dispatch: CANCELLED
p2's fence: parked
p2's run now holds: [('v1', 'p2', 'SKIPPED'), ('u9', 'p2', 'READY')]
p1's run still holds: [('u1', 'READY')]
p2 contract state is still: paused
```

This is AZ F-A3 and SM K (a foreign id used as an independent argument) in the
one command round 4 did not fix. Design 12.2 closed it for `receive_result`
and verdict S2 below confirms that closure holds; `plan` was not looked at.

### Smallest honest fix

The same two-line shape section 10.2 step 2 uses: refuse
`foreign-run` when `run_id != run["run_id"]`, or drop `--run` from `cmd_plan`
and always use the project's current run.

---

## F3 (HIGH) A glob write_scope escapes the project root, because canonicalize_path never resolves past the literal prefix

### The code

`canonicalize_path` (tools/bm_store.py:685 to 707) resolves only the literal
prefix of a glob and appends the wildcard tail verbatim:

```python
    for i, seg in enumerate(segs):
        if _has_glob(seg):
            tail_segs = segs[i:]
            break
        lit_segs.append(seg)
    literal_dir = "/".join(lit_segs)
    resolved = _resolve_against_root(root, literal_dir, cwd)
    if tail_segs:
        return _join_relative(resolved, "/".join(tail_segs))
```

`_resolve_against_root` is the only thing that ever calls `os.path.realpath`,
so no symlink under a wildcard is ever seen. Round 4 turned the resulting
`OwnershipRefused('path-escape')` into a REFUSED-SCOPE verdict for directly
named paths (design 5.4), which makes the asymmetry a verdict asymmetry:
the same file is ALLOWED under one spelling and REFUSED under another.

### Reproduction (probe p4)

A project root containing `src/app`, a symlink pointing outside the tree,
which is what a repository with a linked vendor directory or a linked build
output looks like:

```
$ python3 p4_glob_tail_symlink_escape.py
gate_check('src/*'               ) -> ALLOWED       authorised against risk class 'file-create'.
gate_check('src/app'             ) -> REFUSED-SCOPE 'src/app' cannot be read as a path inside this project (path 'src/app'...
gate_check('src/app/secrets.env' ) -> REFUSED-SCOPE 'src/app/secrets.env' cannot be read as a path inside this project ...

step: dispatched=['u1'] state=DELIVERABLE_READY
brief write_scope handed out: [['src/*']]
fence files: ['src/*']
fence covers src/app/secrets.env: True
realpath of src/app: /private/var/folders/bx/4mv547hj3nxdv72rb00whvjsgmklcm/T/tmp6c9x9dz5
```

The contract in that probe is `['src/*']`. It also reproduces under the
commonest contract of all, `['.']`, and the glob can name the escaping
directory EXACTLY:

```
allowed=["."] gate_check('src/*'             ) -> ALLOWED
allowed=["."] gate_check('src/app'           ) -> REFUSED-SCOPE
allowed=["."] gate_check('src/app/secrets.env') -> REFUSED-SCOPE
allowed=["."] gate_check('src/?pp'           ) -> ALLOWED
allowed=["."] gate_check('src/[a]pp'         ) -> ALLOWED
```

`src/[a]pp` matches exactly one path, `src/app`, and gets the opposite verdict
from naming it. That is a deliberate-bypass primitive, not a corner case: any
refused path can be re-spelled as a character class that matches only itself.

### Why the round-4 change matters here

Before round 4 the directly named path RAISED out of `gate_check`, which the
controller could not survive (AZ F-A5). Now it returns REFUSED-SCOPE and the
run keeps going, so the two spellings of one path sit side by side in the same
verdict vocabulary, with the wrong one being the permissive one.

---

## F4 (HIGH) The PAUSED hold does not hold on the only route to PAUSED the shipped CLI has

### The two facts that collide

1. The engine writes PAUSED in exactly one place, tools/bm_controller.py:676,
   inside step()'s contract branch, and it writes it BECAUSE the contract is
   paused. There is no `bm-controller pause` subcommand (COMMANDS: complete,
   plan, record-result, resume, start, status, step, stop), and
   `bm-controller resume` (tools/bm_controller.py:3057) only reverses the run.
2. `_record_spend` (tools/bm_controller.py:1006 to 1026) skips when the
   contract is not live, and `set_contract_state` appends a NEW revision every
   time.

So on the only production route into PAUSED, the contract is never live while
the run is paused, and the dispatch's stamped revision is always behind by at
least two by the time the founder resumes.

### Reproduction (probe p13)

```
$ python3 p13_paused_hold_through_the_shipped_route.py
dispatch stamped contract_revision=1
after bm-autonomy pause: contract revision=2 state=paused
after one step: run=PAUSED reason='FOUNDER_WAITING'

record-result -> 'held'
spend tokens: 0   (the test asserts 11)
unit=RESULT_IN retry=0 fence=active

after bm-autonomy resume: contract revision=3 state=live
after the resuming step: unit=READY retry=1 run=READY
commands executed: ['true', 'git restore -- a.py']
spend tokens at the end: 0
verifications on the dispatch: [('stale: contract moved from revision 1 to 3 between dispatch and verification', None)]
```

Both halves of design 4.3 fail on this route:

* **the meter is never charged.** 0 tokens, not 11. That is SM C's own defect
  ("every late result silently drops its SPEND", a regression the round-4
  design moved the spend block specifically to close) reopened for the new
  `"held"` outcome word, and the breaker under-counts by exactly the held
  unit's cost. Nothing charges it later either: `_record_spend` has two
  callers (tools/bm_controller.py:974 and 1714) and the RESULT_IN resume
  branch is neither.
* **the answer does not survive the pause.** It is rejected as stale,
  `git restore -- a.py` runs against the founder's files, and `retry_count`
  goes 0 to 1. Design 18.1's supersession argument for retiring the old PAUSED
  test row is, verbatim, "the real answer survives the pause and is accepted
  afterwards, instead of being destroyed (rolled back on disk, retry burned)
  because a founder pressed pause". On the shipped route the answer is
  destroyed, rolled back on disk, with a retry burned.

### Why the suite is green anyway

tools/test_bm_controller.py:1988:

```python
def _pause_the_run(store, run):
    """Move a run to PAUSED the way the store's own table allows, so the
    tests below ask what the ENGINE does from PAUSED rather than whether
    PAUSED was reachable ..."""
    store.set_run_state(run["run_id"], "PAUSED", _actor(),
                        "founder paused the run", "sess1")
```

The helper leaves the contract LIVE, which no shipped command can do, and
`test_a_result_arriving_on_a_paused_run_is_recorded_and_held`
(tools/test_bm_controller.py:2109) then asserts `spend_totals == 11` and DONE
after resume. The class is honest about deliberately not asking whether PAUSED
was reachable; the consequence is that the two assertions that carry the whole
benefit of the change are only true in a state the product cannot enter.
I ran the class against the current tree to be sure I am not describing a
failing test:

```
$ python3 -m unittest -v test_bm_controller.TestR3PausedIsAFounderOnlyGate ...
Ran 10 tests in 0.161s
OK
```

---

## F5 (HIGH) The 3am kill switch does not stop command execution, and round 4 added one more command to what runs after it

### The code

`receive_result` (tools/bm_controller.py:897) never reads the contract state.
The only contract read on the path is the staleness re-read INSIDE
`_verify_and_finish` (tools/bm_controller.py:1733), which happens AFTER the
unit's own done_check has already been executed at line 1729:

```python
        outcome = self.checker.run(unit["done_check"] or "true",
                                   cwd=self.store.root)
```

and the stale branch then runs the rollback, which is NEW in round 4. Its own
comment says so (tools/bm_controller.py:1746 to 1751): "The staleness
rejection ALSO rolls back and warns ... this branch used to park the fence and
return". Design 10.6 is the section that added it.

`SubprocessCheckRunner.run` (tools/bm_controller.py:197) is
`subprocess.run(command, shell=True, cwd=cwd)`. In full auto the unit graph,
including `done_check` and `verifier`, is model-authored: "the unit graph is
the one judgement the design leaves to the orchestrating model"
(tools/bm_controller.py:2784).

### Reproduction A, four shipped commands, no crash (probe p12)

```
$ python3 p12_record_result_after_stop.py
contract: stopped   gate_check: REFUSED-STATE
commands run so far: []

receive_result -> 'rejected'
commands the command executed: ['./unit-authored-done-check.sh', 'git restore -- a.py']
unit status: READY
run state: READY
spend: 0
```

Sequence: `start`, `plan`, `step`, `bm-autonomy stop`, `bm-controller
record-result`. gate_check says REFUSED-STATE ("Nothing is authorised while it
is not live", tools/bm_store.py:12657) and two commands run anyway.

### Reproduction B, the crash-resume branch (probe p11)

```
== stop (the 3am kill switch) ==
contract state: stopped
gate_check now says: REFUSED-STATE
commands the step executed: ['./unit-authored-done-check.sh', 'git restore -- a.py']

== revoke ==
contract state: revoked
gate_check now says: REFUSED-STATE
commands the step executed: ['./unit-authored-done-check.sh', 'git restore -- a.py']
```

Here it is plain `bm-controller step`: `_resume_result_in_and_orphans` runs
BEFORE the live-contract read by design (step 1 before step 2), goes straight
to `_verify_and_finish`, and executes the same two commands.

### The honest counter-argument, and why it does not hold

The design's position is that a RESULT_IN dispatch is "judged on its own
merits" unconditionally. Judging is a store read and a verdict. Running a
model-authored shell command and mutating the working tree with `git restore`
after the founder pulled the kill switch is not judging. The rollback in
particular is a NEW filesystem mutation this round introduced on a path the
kill switch is supposed to have closed.

---

## F6 (MEDIUM) A unit_id the store accepts and the fence refuses wedges the run permanently

`upsert_units` validates the id only as "a non-empty string"
(tools/bm_store.py:12959). `_authorise_dispatch` builds the fence name at
tools/bm_controller.py:1631 as `"unit-" + unit["unit_id"]`, and `Store.claim`
runs `valid_name` (tools/bm_store.py:395), which raises ValueError for
whitespace, for `/ \ : ? * " < > |`, for a leading dot and for anything over
60 characters. The raise happens after step() has already walked the run to
EXECUTING (tools/bm_controller.py:735), and `_authorise_dispatch`'s only
`except` there is `bs.OwnershipRefused` (tools/bm_controller.py:1637).

### Reproduction, shipped CLI, five commands

```
$ python3 tools/bm_controller.py plan --project p1 --run $R --units-file /tmp/az4bad.json ...
planned 1 unit(s) for run f7b7c6da17d64fa49d21514b4c98595e
--- step 1 ---
bm_controller: refused: name contains a reserved character (/): 'unit-api/pay'
EXIT=1
--- step 2 ---
bm_controller: refused: name contains a reserved character (/): 'unit-api/pay'
EXIT=1
--- the founder tries to re-plan the bad unit away ---
bm_controller: refused: run 'f7b7c6da17d64fa49d21514b4c98595e' is EXECUTING; upsert_units always flips a run to READY, but that move is not legal from there. Legal moves from EXECUTING: VERIFYING, STOPPING, PAUSED, FAILED_RECOVERABLE.
EXIT=1
--- status ---
project p1: run f7b7c6da17d64fa49d21514b4c98595e, state EXECUTING (workflow version 1)
units: 1 total
  READY: 1
```

The units file is one object with `"unit_id": "api/pay"`, which is exactly the
naming a planner produces for a unit that owns a directory. Probe p14 shows
the same for `"a b"` and for any id over 55 characters (the `unit-` prefix eats
five of the sixty), and shows `.hidden` passing only because the prefix hides
the leading dot.

The wedge is the finding, not the refusal: main() catches ValueError
(tools/bm_controller.py:2409 area) so there is no traceback, but the run is
left EXECUTING with nothing in flight, `_unwind_empty_wave` is never reached
because the exception leaves the wave early, and `plan`, which design 8.3 and
8.5 name as the founder's recovery, is refused from EXECUTING. Only
`bm-controller stop` escapes.

---

## F7 (MEDIUM) The other half of LV 7's crash window: an active fence over a unit that is still READY

Design 8.6 closes "a CLAIMED unit with NO dispatch row at all ... the crash
window between `claim_unit` (13107) and `record_dispatch` (13129)". The window
one statement EARLIER is still open: `Store.claim` commits at
tools/bm_controller.py:1633, `claim_unit` at 1639. A crash between them leaves
an ACTIVE fence named `unit-<id>` while the unit row is still READY with a
NULL `fence_uuid`, and none of `_resume_result_in_and_orphans`' three orphan
branches (DONE, SKIPPED, CLAIMED, tools/bm_controller.py:1243 to 1273) matches
a READY unit.

`Store.claim` only reclaims in place for the SAME non-empty session
(tools/bm_store.py:10166), and the CLI mints a fresh session id per process
when `--session-id` is omitted (tools/bm_controller.py:2531), so the next
invocation cannot take it back.

### Reproduction (probe p15, built against `bc.bs` per design 17.4)

```
after the crash: unit status=READY fence_uuid=None; fence 6678468b is active
new session id: 'controller-a' (the old fence holds 'cli-OLD')
step 1: dispatched=[] reason='CONTENTION' state=CHECKPOINTED
        note: another writer holds a fence over this unit's files, or the contract was amended twice while the unit was being checked; no founder action is needed and the next step tries the same unit again
step 2: dispatched=[] reason='CONTENTION' state=CHECKPOINTED
...
step 5: dispatched=[] reason='CONTENTION' state=CHECKPOINTED
worker calls: {}
fence still: active
open founder steps: 0
run_to_completion: 1 step(s), last reason='CONTENTION' state=CHECKPOINTED
```

Forever, with zero founder steps, and a note that tells the founder to do
nothing. LV 7's own summary of the shape it found ("an active fence and no
founder step naming it") is reproduced verbatim by the half of the window that
was not closed.

---

## F8 (MEDIUM) The re-await route trusts the fence's STATE and never its CONTENT or its owner

tools/bm_controller.py:1603 to 1621:

```python
            record = (self.store.get(unit["fence_uuid"])
                      if unit["fence_uuid"] else None)
            if record is None or record.state != "active":
```

Design 6.2 step 5b calls this "the fence check". It compares one field. A
same-session reclaim (documented at tools/bm_store.py:10146, "files=[] is a
deliberate release, always honored") empties the fence and changes its owner
while leaving it active.

### Reproduction (probe p8, part b)

```
after wave 1: fence files=['a.py'] state=active
after the reclaim: fence files=[] state=active owner='someone-else'
step 2: dispatched=[] reason='IN_FLIGHT' worker asked again: True
brief write_scope: ['a.py']
fence still: files=[] state=active
```

The worker is handed a brief for `a.py` under a fence that holds nothing.
Design step 6's promise ("claim files before dispatch, durable before the
worker runs") is not re-established on the re-await route; only the existence
of a row is. MEDIUM because it needs a second writer sharing the session id.

---

## F9 (MEDIUM) read_scope is never canonicalised, so a brief can hand a worker the whole machine to read

`upsert_units` canonicalises every write_scope entry through
`_coerce_path_entry` and `canonicalize_path` (design 12.4, landed at
tools/bm_store.py:13010 to 13020) and stores `read_scope` with a bare
`json.dumps(u.get("read_scope") or [])`. `_build_brief`
(tools/bm_controller.py:1655) hands it to the worker unchanged.

```
write_scope with an escaping path:
  refused 'path-escape': path '/etc/passwd' resolves outside the project root /private/var/fold...
read_scope stored verbatim: ['/etc', '../../../Users', '~/.ssh/id_rsa']
brief handed to the worker: ['/etc', '../../../Users', '~/.ssh/id_rsa']
dispatched: ['u1']
```

The contract in that probe grants `allowed_paths ['docs']`.
`_gate_check_write_scope`'s docstring (tools/bm_controller.py:1432) states
that read_scope is deliberately not gate-checked because allowed_paths is a
write boundary, and that decision is defensible. Storing a read scope that
leaves the project root without even canonicalising it is a different
decision, and it is not written down anywhere. In full auto the read scope is
model-authored.

---

## F10 (LOW, data for design 16.3) An empty write_scope is dispatched with an empty fence

Design 16.3 defers AZ F-A10 on the grounds that "Round 2 already ruled the
empty-write-scope case NO-DATA on its own terms". Here is the data (probe p8,
part a), under a contract that grants only `docs`:

```
contract allowed_paths: ['docs']
step: dispatched=['u1'] reason='IN_FLIGHT'
brief: {'unit_id': 'u1', ..., 'write_scope': [], 'risk_class': 'file-create', ...}
fence: state=active files=[]
gate_check('src/prod/db.sql') for the same class: REFUSED-SCOPE
```

The unit is authorised, dispatched and fenced over nothing. In default
(non-strict) mode tools/bm_fence_hook.py:637 finds no covering claim and no
foreign claim, so nothing refuses a write anywhere. The deferral is still a
reasonable call about contract semantics; it is no longer NO-DATA.

---

## F11 (LOW) gate_check does raise, because `_coerce_path_entry` is not total

`_coerce_path_entry`'s docstring (tools/bm_store.py:721) says: "TOTAL: for ANY
input, this either returns a string or raises OwnershipRefused reason
'bad-path'". It catches only TypeError from `os.fspath`, and it formats the
refusal with `%r`.

Probe p5, 30 hostile path values against `Store.gate_check`:

```
  empty string       -> REFUSED-SCOPE
  int                -> REFUSED-SCOPE
  list               -> REFUSED-SCOPE
  nested list        -> REFUSED-SCOPE
  dict               -> REFUSED-SCOPE
  set                -> REFUSED-SCOPE
  bytearray          -> REFUSED-SCOPE
  NUL byte           -> ALLOWED            (design 12.4 discloses this)
  lone surrogate     -> ALLOWED
  weird repr         -> RAISED RuntimeError: repr blows up
  fspath raises      -> RAISED RuntimeError: fspath blows up
```

Twenty-eight of thirty return a verdict, which is the design's claim holding.
The two that raise are an SDK caller's problem only (the CLI passes strings
and the controller passes store-loaded strings), hence LOW. Also confirmed in
the same probe: a project with no contract at all returns REFUSED-NO-CONTRACT
for a bad path rather than dereferencing a None contract row.

---

## F12 (LOW) Two founder-facing notes state a cause that did not happen

1. `_resume_dispatched`'s default REFUSED note (tools/bm_controller.py:1357)
   is "the live contract no longer authorises the in-flight unit's write
   scope", used for EVERY `REFUSED` outcome, including the two that have
   nothing to do with the contract (the stale-stamp branch and the fence
   branch). Probe p3b, where a re-plan cleared the unit's fence pointer and
   the contract never moved:

```
step2: dispatched=[] completed=[] reason=None state=READY
        note=the live contract no longer authorises the in-flight unit's write scope; its dispatch was closed and no worker was re-asked
```

2. `_NOTE_CONTENTION` ends "no founder action is needed and the next step
   tries the same unit again". In F7 that is false forever. LV 5's finding was
   precisely a note that misstated whether a founder is needed; the fix
   replaced one unconditional claim with the opposite unconditional claim.

---

# WHAT STANDS (attacks that failed)

### S1 The ONE choke point stands, with 6 attacks against it

Route enumeration on the current tree:

```
$ grep -rn "record_dispatch\|worker\.run\|_build_brief\|_authorise_dispatch" tools/*.py | grep -v "^tools/test_"
tools/bm_controller.py:747:            claimed, outcome = self._authorise_dispatch(
tools/bm_controller.py:778:                claimed, self.worker.run(claimed["brief"]), project_id,
tools/bm_controller.py:1347:        claimed, outcome = self._authorise_dispatch(
tools/bm_controller.py:1363:            claimed, self.worker.run(claimed["brief"]), project_id, run_id)
tools/bm_controller.py:1622:            brief = self._build_brief(unit, open_dispatch["attempt"])
tools/bm_controller.py:1642:        dispatch_id = self.store.record_dispatch(
tools/bm_controller.py:1645:        brief = self._build_brief(unit, attempt)
```

Two `worker.run` sites, both fed by `_authorise_dispatch`; both `_build_brief`
calls and the single `record_dispatch` call are inside `_authorise_dispatch`,
after the gate check. The ast guard that pins this is green:

```
$ python3 -m unittest test_bm_controller.TestR3EveryDispatchRouteIsGateChecked test_bm_controller.TestR3PausedIsAFounderOnlyGate
Ran 10 tests in 0.161s
OK
```

Attacked and failed: (a) the rebuilt `_resume_dispatched` with a narrowed
contract, (b) the RESULT_IN crash-resume branch (it never builds a brief and
never calls the worker; it does run commands, which is F5, not a dispatch),
(c) the SKIPPED-fence and CLAIMED-no-dispatch resume branches (same), (d) a
re-plan that REDEFINES an in-flight unit (probe p3b: the redefinition clears
`fence_uuid`, so the re-await refuses at step 5b and the worker is not asked
again under the old fence), (e) `check_timeouts` (it abandons, it never
dispatches), (f) `cmd_status` and `_report_trace` (read only). No route
reached a worker without `_gate_check_write_scope` running first over the
whole write_scope.

### S2 The foreign-dispatch guard stands

```
p1 spend before: 0  p2 spend before: 0
refused 'foreign-dispatch': dispatch '5accaef...' belongs to run '01d4cd4...' of project 'p2',
p1 spend after: 0  p2 spend after: 0
p2 dispatch status: DISPATCHED
p2 unit v1: DISPATCHED
```

Nothing recorded, nothing charged, no run moved. AZ F-A3 and SM K are closed
for `receive_result`. (F2 is the same class in a different command.)

### S3 The CANCELLED dispatch law stands on its own terms

Probes p7 and p7b:

```
(a) plan drop: {'count': 1, 'skipped': ['u2'], 'cancelled_dispatches': ['b2d4...'], 'orphaned_fences': [('u2', '2acd...')]}
    u2 status=SKIPPED dispatches=[(1, 'CANCELLED')] fence=parked
(b) receive_result refused 'dispatch-cancelled': dispatch 'b2d4...' is CANCELLED: a re-plan dropped unit
    spend tokens 1 -> 1
(c) plan revive: {'count': 2, 'skipped': [], 'cancelled_dispatches': [], 'orphaned_fences': []}
    u2 status=READY retry=0
    step: dispatched=['u2'] reason='IN_FLIGHT'
    u2 dispatches now: [(1, 'CANCELLED'), (2, 'DISPATCHED')]
(d) second consecutive drop: {'count': 1, 'skipped': ['u2'], 'cancelled_dispatches': [], 'orphaned_fences': [('u2', 'd505...')]}
    u2 fence state: parked
```

A revived unit gets a FRESH dispatch (attempt 2) and never the cancelled one,
the meter is not charged for a refused result, the 2-tuple `orphaned_fences`
contract unpacks and re-parks idempotently on a double drop, and a CANCELLED
dispatch is invisible to `_open_dispatch_units` (tools/bm_controller.py:854)
and therefore to `check_timeouts` and to the IN_FLIGHT early return.

One reachability limit worth recording rather than scoring: the whole law only
applies while `plan` is legal, and `plan` is refused from EXECUTING. A run
whose only in-flight unit parked (which is what the production
`RecordIntentWorker` always produces) sits in EXECUTING, so the founder cannot
drop or revive anything until a result is recorded or the run is stopped:

```
(f) a single-unit run: can the founder re-plan while it parks?
    step: state=EXECUTING reason='IN_FLIGHT'
    plan(drop u1) REFUSED 'illegal-state-move': run '87f5...' is EXECUTING; upsert_units always flips a run to READY, but t...
    plan(add u2) REFUSED 'illegal-state-move': ...
```

### S4 The non-glob branch of `path_within_allowed` stands

23595 triples, 0 violations with a non-glob allowed path, under both readings
(see F1 reproduction 1). Design 5.1's claim that the branch is behaviourally
identical holds, and `TestGlobNarrowingBreaksNothingElse` plus
`TestGlobAllowedPathsAreDepthExact` plus
`TestGateCheckReturnsAVerdictInsteadOfRaising` are green on this tree:

```
$ python3 -m unittest test_bm_store.TestGlobAllowedPathsAreDepthExact test_bm_store.TestGlobNarrowingBreaksNothingElse test_bm_store.TestGateCheckReturnsAVerdictInsteadOfRaising
Ran 9 tests in 0.193s
OK
```

### S5 Two attacks that simply failed

* **Command injection through write_scope.** `_rollback_command` uses
  `shlex.quote` per entry with a `--` separator, so `a.py; curl evil` cannot
  break out. (The blast radius in F1 comes from git's own pathspec globbing,
  not from the shell.) The `SubprocessCheckRunner` docstring's claim that it
  never runs "text this file composes itself" is inaccurate, since
  `_rollback_command` composes text, but the composition is safe.
* **Catastrophic backtracking in the new glob rule.** Python 3.9.6's
  `fnmatch.translate` collapses star runs, so `a*a*a*...b` against a 60
  character candidate and 40 stars against a 200 character candidate both
  return in 0.000s.

---

# ATTEMPTS LOG

Ordered as run. Each line says what was attacked and what came back.

1. Route enumeration by grep over the whole tree for `record_dispatch`,
   `worker.run`, `_build_brief`, `_authorise_dispatch`, `claim_unit`. Two
   worker routes, one dispatch recorder. No finding (S1).
2. Read `_authorise_dispatch` (tools/bm_controller.py:1483 to 1648),
   `_resume_dispatched` (1306), `step` (627 to 794),
   `_resume_result_in_and_orphans` (1205), `receive_result` (897),
   `_record_spend` (1006), `plan` (588), `gate_check` (tools/bm_store.py:12611),
   `path_within_allowed` (565), `upsert_units` (12897), `claim` (10125).
3. Small grid property search over the new glob rule. 38 violations. **F1.**
4. End-to-end confirmation of the directory-candidate shape through the engine
   and then through the shipped CLI. **F1.**
5. Adversarial glob matrix: pattern at depth, leading wildcard, `**`,
   character classes, unbalanced `[`, bad ranges, case folding on darwin,
   trailing slash and `//` spellings. Only the containment direction breaks;
   the depth and case behaviour is as designed.
6. Symlink created after the plan, under a wildcard. **F3.**
7. `_has_glob` on the allowed side with a non-wildcard `[`: narrows rather
   than widens. No finding.
8. Re-plan that REDEFINES an in-flight unit: the redefinition clears
   `fence_uuid` and the re-await refuses; the fence is re-claimed in place by
   the same session on the next wave, so no orphan. No finding, except the
   wrong note (**F12**).
9. Hostile path battery against `gate_check`, 30 values plus a no-contract
   project. **F11**, plus confirmation that the design's REFUSED-SCOPE
   conversion holds for every ordinary hostile value.
10. `plan`'s `run_id` argument against the project it reads. **F2**, confirmed
    through the shipped CLI.
11. CANCELLED law: drop, refuse, revive, double drop, drop while RESULT_IN,
    attempt numbering, `check_timeouts` visibility. No counterexample (S3),
    plus the EXECUTING reachability limit recorded there.
12. Foreign dispatch id from another project into `receive_result`. Refused
    with nothing written (S2).
13. Spend attribution: which revision absorbs a charge when the contract moved
    between dispatch and result. NO-DATA: `_spend_sum`
    (tools/bm_store.py:2758) is project-cumulative "regardless of which
    contract revision they were recorded against", so the attribution cannot
    change an outcome. Reported as no finding.
14. Spend on the PAUSED hold path. **F4** (never charged on the shipped
    route), which is the spend finding this lens was asked for.
15. Kill switch followed by `record-result`, and by `step` on a RESULT_IN
    dispatch. **F5.**
16. Command injection through write_scope into `_rollback_command`. Refuted
    (S5).
17. git pathspec blast radius of `git restore -- '*.py'` in a throwaway repo.
    Confirms F1's damage.
18. Unit id shapes that `upsert_units` accepts and `valid_name` refuses.
    **F6**, confirmed through the shipped CLI.
19. The `claim` to `claim_unit` crash window. **F7.** The first run of this
    probe produced a false positive (an uncaught OwnershipRefused) because the
    probe harness loaded `bm_store` a second time; re-run against `bc.bs` per
    design 17.4, which is what the finding above reports.
20. Fence content and ownership under an open dispatch. **F8.**
21. Empty write_scope. **F10.**
22. read_scope canonicalisation. **F9.**
23. Catastrophic backtracking in the new glob rule. Refuted (S5).
24. Final idea round: fence-name collisions between the controller fence and a
    unit fence (impossible, different prefixes); a second dispatch row on the
    re-await route (never opened, confirmed by reading and by S3's attempt
    counts); `record_verification` against a CANCELLED dispatch (unreachable,
    the unit is SKIPPED and invisible to every open-dispatch read);
    `_finish`'s ValueError on an unknown stop reason (engine internal). Nothing
    new. Stopping here per the brief's rule.

---

# WHAT I DID NOT CHECK

* **tools/test_all.py was not run**, as instructed, and neither were the full
  `test_bm_controller.py` or `test_bm_store.py` suites. I ran five individual
  classes (listed above) and no others, so I make NO claim about the three
  collisions the controller writer reported or about the store writer's one.
* **Two real operating-system processes against one store.** Every probe here
  is a single process. F8's "second writer" is a second call in the same
  process holding the same session id.
* **The fence hook end to end.** I read tools/bm_fence_hook.py:600 to 665 and
  quote line 637, but I did not drive a real hook payload through it, so F1's
  and F10's enforcement half is established by reading plus a direct
  `paths_overlap` call, not by an intercepted write.
* **The bash audit net** (tools/bm_bash_audit.py) was not exercised at all.
* **docs/AUTONOMY.md, docs/KNOWN-LIMITS.md and docs/FULL-AUTO.md** were not
  reviewed for whether they now describe the glob rule correctly. The
  controller writer records that docs/AUTONOMY.md was not written; F1 and F3
  mean the sentence that WAS written elsewhere ("a glob grants exactly what it
  matches at its own depth") is not true of the system as a whole, only of one
  of its three readers.
* **Windows and Linux path behaviour.** Everything here ran on darwin, where
  `_normcase` folds case and normalises to NFC. The `fnmatchcase` choice
  (design 5.1's fourth property) was read, not tested on win32.
* **Whether F2, F6 or F7 have ever occurred in a real run.** I demonstrated
  reachability, not incidence.
* **`check_timeouts`** beyond reading it and confirming CANCELLED invisibility:
  it is wired to no subcommand (tools/bm_controller.py:1695 area says so), so
  it is SDK-only surface and I did not attack its clock.
* **The E4 end-to-end artifact** and every other evidence page were not
  touched or regenerated.
