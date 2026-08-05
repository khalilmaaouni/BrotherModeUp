# FIX-L09-auth: the three founder-ratified authorisation narrowings

Date: 2026-08-06. Loop: L09. Writer: the L09 authorisation agent.
Scope: tools/bm_store.py, tools/bm_controller.py, tools/bm_autonomy.py and
their three test files, plus this evidence directory. Nothing else was
written by this loop. No commit, no push, no docs edit, no store write to
the live .brothermode/, no touch of tools/write_sites.json or
tools/test_all.py.

None of the six cross-family findings was live in this file set, and no
fix for any of them was needed: all six have real closing tests (table in
section 5).

RED evidence: docs/program/absolute-lead/evidence/L09/RED-auth.txt,
captured against the untouched tree before any implementation change.
All three RED runs exited 1; the handful of tests that already passed in
RED are the deliberate controls, labelled as such in that file.

---

## 1. GAP 1, the path floor (CLOSED)

### What landed

- A SIXTH entry in `AUTONOMY_FLOORS` (tools/bm_store.py):
  `("governance-write", "writing to the authorisation machinery itself:
  the project's own .brothermode store, its .git directory, or
  .claude/settings.json")`. Same shape as the five: keyed by id, refusal
  quotes the description. Every existing floor mechanism picked it up for
  free: `sign_contract` refuses it in risk_classes
  (`risk-class-is-floor`), `gate_check` refuses it as an action class
  (`REFUSED-FLOOR`), `upsert_units` refuses a unit requesting it,
  `queue_human_step` can tie a human step to it.
- `AUTONOMY_FLOOR_PATHS = (STORE_DIRNAME, ".git", ".claude/settings.json")`
  and the predicate `_governance_floor_hit(candidate)`: true when a
  canonical root-relative path names or falls inside one of the three
  surfaces. Containment is `_prefix_contains` at a separator boundary
  (so `.gitignore` and `.github` stay outside `.git`, and `.claude`
  itself is NOT protected, only its settings.json). A glob candidate is
  reduced to its `_coverage_key` literal prefix, which only ever widens
  the REFUSAL, never a grant.
- Enforced at the SAME two points the five floors are:
  - SIGN time (`sign_contract`): an `allowed_paths` entry that names a
    protected surface (literally, or as a glob whose literal prefix sits
    inside one: `.git`, `.git/config`, `.git/*`, `.brothermode`,
    `.brothermode/*`, `.claude/settings.json`) refuses
    `path-is-floor` with nothing written. A broad allowance (`.`, `*`,
    `**`) stays signable, exactly as the founder's own pinned test
    demands (a `.` contract is legitimate).
  - GATE time (`gate_check`): a candidate path inside a protected
    surface returns `REFUSED-FLOOR` with `floor: "governance-write"`,
    checked BEFORE the allowed_paths loop, so the floor holds under
    every spelling of the allowance: `.`, `*`, `**`, a covering glob,
    or a hand-written row that bypassed sign_contract. The gate_check
    docstring's normative check order gained this as check 5 (items
    renumbered 6 to 9).
- Wording: every "five safety floors" refusal and comment in
  tools/bm_store.py and tools/bm_autonomy.py now says six; the
  bm_autonomy module docstring section is now "THE SIX FLOORS" and
  documents the path-shaped floor and the empty-scope sign rule.

### Refusal wording, verbatim

Sign time (OwnershipRefused, reason `path-is-floor`):

> allowed_paths entry %r names a surface of 'governance-write' (writing
> to the authorisation machinery itself: the project's own .brothermode
> store, its .git directory, or .claude/settings.json), one of the six
> safety floors. No contract wording can grant it, and a contract that
> tries is a finding worth telling the founder about rather than a
> permission to honour. Remove the entry and sign again.

Gate time (verdict `REFUSED-FLOOR`, floor `governance-write`):

> %r falls inside a surface of 'governance-write' (writing to the
> authorisation machinery itself: the project's own .brothermode store,
> its .git directory, or .claude/settings.json), one of the six safety
> floors. No contract, ever, can authorise a write there; this
> contract's allowed_paths were not consulted.

### The spelling sweep, proven

`TestSixthFloorGovernancePaths` (tools/test_bm_store.py) sweeps the
broad allowances `.`, `*`, `**` against seven protected candidates
(REFUSED-FLOOR every time), eight protected allowance spellings at sign
time (path-is-floor, nothing written), and seven neighbours that must
STAY allowed (`.gitignore`, `.github/workflows/ci.yml`, `.claude`,
`.claude/other.json`, `brothermode/x.py`, `src/git/config`, `src/a.py`).
`TestSixthFloorThroughTheCLI` (tools/test_bm_autonomy.py) proves the
same at the two shipped doors (sign and gate-check, exit codes and JSON
verdict asserted).

### One refusal WORD changed for one hostile path (not a break)

`test_the_whole_project_grant_needs_a_glob_no_unit_can_declare`
(tools/test_bm_store.py) expected `.git/config` under allowance
`['*.py']` to be `REFUSED-SCOPE`; it is now the sharper `REFUSED-FLOOR`.
The path was refused before and is refused now; no legitimate contract
broke, so this is not the founder's flip condition. The test's
expectation table was updated with a dated comment. Verbatim failure
before the update:

> AssertionError: 'REFUSED-FLOOR' != 'REFUSED-SCOPE' : '.git/config' is
> not what the pattern literally matches

---

## 2. GAP 2, driver adoption (CLOSED)

### What landed

- Driver identity is the run row's `session_id`, which `open_run` has
  always recorded from the engine at begin(). NO SCHEMA CHANGE was
  needed (the brief's preferred design): the runs table already carries
  the session id, so there is no new migration and no S5 exempt entry.
- `ControllerEngine._refuse_foreign_driver(run, action)`
  (tools/bm_controller.py): raises `not-driver` when the run's recorded
  session is non-empty and differs from the engine's. Wired into the
  three doors the brief names:
  - `step`: after the terminal early-return (a finished run's summary is
    a read anyone may take, mirroring the fence store's
    ownership-guards-only-ACTIVE-records law), before every other
    branch including the pause read.
  - `receive_result`: before ANYTHING is recorded or charged, for
    non-terminal runs. A TERMINAL run's late-result recording remains
    open to any session, deliberately: the late-result path exists for
    results arriving after a stop, adoption of a terminal run is
    refused, and refusing the recording would make already-spent work
    unaccountable (disclosed in section 7).
  - `stop`: after the quiet no-run/terminal no-op, before draining.
- The ONE deliberate takeover path, rhyming with cmd_adopt
  (tools/bm_store.py fence adoption): `Store.adopt_run(project_id,
  session_id, actor, note="")` updates the run's session_id and records
  attribution event `controller.run.adopted` in the SAME transaction,
  its reason naming both sessions and the note. Refuses `no-run` and
  `run-terminal` (terminal derived from CONTROLLER_STATE_TRANSITIONS'
  empty tuples, never restated). Idempotent no-op (`adopted: False`)
  when the caller already drives, recording nothing, the same
  success-not-refusal shape set_contract_state gives. Unlike fence
  adoption there is no liveness signal for a controller session, so
  there is no adopt-from-live-session split: EVERY adoption of another
  session's run is treated as the deliberate displacement and recorded
  as one (stated in the method's docstring).
- `ControllerEngine.adopt(project_id, note="")`: thin delegate.
- CLI: new `adopt` subcommand (`adopt --project ID --actor-name NAME
  [--actor-type human|model] [--session-id SID] [--note TEXT] [--json]`),
  registered in COMMANDS (now nine), calling the store directly under
  the same thin-CLI law as resume and complete. The empty-driver
  carve-out (a run row with session_id '' from before this law) is not
  guarded, mirroring the fence store's non-empty-session rule, and is
  pinned by a test.

### Refusal wording, verbatim (OwnershipRefused, reason `not-driver`)

> controller run %r is driven by session %r, and this engine is session
> %r, so %s is refused: a run has one driver, the same law the
> controller fence enforces at begin(). If that session is gone, or this
> takeover is deliberate, run `bm-controller adopt` for this project
> (engine: adopt()), which records the handover and makes this session
> the driver; then %s again.

details carries `run_id`, `driver_session_id`, `caller_session_id`
(the same held-by shape the fence store's not-owner refusal uses).

### Existing fixtures updated (each models "the same driver"), disclosed in full

Four sites in tools/test_bm_controller.py, each a crash-resume or
next-wave fixture whose fresh engine stood in for the SAME driver
restarted; each now passes the first engine's session id (or reads the
recorded driver off the run row), with a dated comment at every site:

1. `TestFault1KilledBetweenResultAndCommit` (engine2 gets
   `session_id=engine1.session_id`).
2. The workflow-version-bump restart fixture around line 741 (same).
3. `TestEndToEndE4` simulated process death (same, via
   `session_id=engine.session_id` at the rebuild).
4. `TestCrossFamilyF5StaleSelectionIsDeferred.test_the_next_wave_makes_progress_on_the_replanned_graph`
   (reads `store.get_run(...)["session_id"]` and passes it).

Plus one fixture constant: `CLI_ACTOR` in tools/test_bm_controller.py now
carries `--session-id sess-cli-tester`, so every multi-invocation CLI
flow in the suite arrives as ONE driver. This is not an invention of this
loop: it is the store's own documented convention
(`_default_cli_session_id`'s docstring: "a human doing a multi-step CLI
workflow ... must pass the SAME --session explicitly across those
invocations"). `TestControllerCLIAdopt` builds its flags by hand because
its subject is two different sessions. No test was weakened or deleted;
every prior invariant those fixtures pinned still passes.

### What this means for the shipped CLI (founder-facing behaviour change)

`bm-controller step`, `record-result` and `stop` invoked WITHOUT
`--session-id` mint a fresh per-process session and will now be refused
on a run another session started, with the refusal naming the owner and
the `adopt` command. The founder either passes the same `--session-id`
across the flow (the documented convention above) or runs
`bm-controller adopt --project X` once, which records the handover. The
orchestrator's docs delta below states this.

---

## 3. GAP 3, empty allowed_paths (CLOSED)

### What landed

- `AUTONOMY_READ_ONLY_RISK_CLASSES = ("read-only-inspect",
  "browser-read")` (tools/bm_store.py), with a comment stating it is the
  schema's only way to express read-only work.
- `sign_contract` refuses reason `no-write-scope` when `allowed_paths`
  is empty and any granted risk class is outside that read-only set.
  Ordering: after the signer and risk-class (floor) checks and after
  path canonicalisation, so `risk-class-is-floor` and `path-escape`
  keep firing first (pinned by a test). Nothing is written on refusal.
- Still legal with an empty scope: a contract granting only
  read-only-inspect and/or browser-read, and the degenerate contract
  granting nothing (it authorises no work, so it bounds no work). Both
  pinned.

### Refusal wording, verbatim (OwnershipRefused, reason `no-write-scope`)

> this contract grants %s but declares no allowed_paths, so nothing
> bounds WHERE that work may write: risk class alone is not a boundary.
> Declare the paths the work may touch in allowed_paths (a directory
> grants its whole subtree, '.' grants the whole project), or, for
> genuinely read-only work, grant only the read-only classes
> (read-only-inspect, browser-read), which need no write scope.

### The read-only edge, FINDING (the brief asked for it either way)

The schema has NO explicit read-only marker: `autonomy_contracts` has no
such column, and a unit's only related field is `risk_class`. Therefore
the accepted way to express read-only work is to grant only the
read-only classes, and the refusal message names that route verbatim
(requirement satisfied via the second branch of the founder's rule).
Judgement call, stated for review: `build`, `test-run`, `app-drive`,
`local-commit` and `local-branch` are treated as WRITING classes (each
changes something: artifacts, app state, git state), so each of them
alone with an empty scope refuses; the sweep test covers all eight
writing classes individually.

### Existing fixtures updated, disclosed in full

- tools/test_bm_store.py `_sign` helper: default `allowed_paths` moved
  `[]` to `["."]` (the legitimate whole-project allowance), because the
  helper's default risk classes grant file-edit. One dated comment at
  the helper. Every test that is ABOUT the empty scope passes `[]`
  explicitly. No stored-row assertion depended on the old default
  (verified: the full suite passes with no other edit).
- tools/test_bm_autonomy.py: ten `_sign(root, extra=("--risk-class",
  ...))` fixture calls gained `"--allowed-path", "."`. The two floor and
  unknown-class refusal tests needed no change (their refusals fire
  before the path checks, which is itself pinned by the new ordering
  test).

These are the convenience-fixture edits the ratified narrowing forces,
not policy collisions: in every one of them the contract's purpose was
"a live contract granting file-edit", which `["."]` preserves exactly.
No legitimate contract became unsignable, so the founder's flip
condition was not met.

---

## 4. Policy collisions encountered

None that met the founder's flip condition (a legitimate signed contract
breaking). The two closest calls, both resolved and both disclosed
above with their reasoning: the REFUSED-SCOPE to REFUSED-FLOOR word
change for `.git/config` under a glob allowance (section 1), and the
fixture-default edits (sections 2 and 3). The founder's own pinned
whole-root test (`test_a_whole_root_contract_still_allows_everything_including_dot`)
passes untouched, which is the sharpest witness that no legitimate
allowance narrowed.

---

## 5. The six cross-family findings: verification table

All six verified CLOSED with real closing tests that would fail if the
defect were reintroduced. No defect was live; no new test was needed.

| # | Finding | Closing test(s) | Verified how |
|---|---------|-----------------|--------------|
| 1 | string retry_ceiling crashing mark_unit_failed | `TestCrossFamilyF1UnitNumberTypes` (tools/test_bm_store.py), sharpest: `test_the_shipped_failure_path_never_reaches_a_typeerror`; plus `TestCrossFamilyF1ShippedPlanRefusesABadNumber` (tools/test_bm_controller.py) at the shipped CLI | Read in full. The shipped-failure-path test is self-calibrating: either the plan is refused by name, or the string reaches the column and mark_unit_failed raises the very TypeError the finding describes; there is no third outcome, so removing the boundary check fails the test with the original crash. |
| 2 | non-dict worker results bypassing malformed-result rejection (`_handle_worker_result`) | `TestCrossFamilyF2NonDictWorkerResult` (tools/test_bm_controller.py) | Read in full. Four behavioural tests (None, list, str, int) each assert the SAME recorded rejection a malformed dict gets and explicitly fail on AttributeError; a fifth structural test pins that the isinstance shape check precedes every read of the result. |
| 3 | inherited GIT_DIR/GIT_WORK_TREE redirecting rollback | `TestCrossFamilyF3InheritedGitEnvironment` and `TestCrossFamilyF3ShippedRecordResultCannotBeRedirected` (tools/test_bm_controller.py) | Read in full. The P-and-Q reproduction runs REAL git under a poisoned environment through the shipped SubprocessCheckRunner and asserts Q's founder edit survives AND P's rollback still works; a second test asserts the whole GIT_ class is stripped from the child; a third that legitimate env survives. Un-stripping the variables fails the reproduction test. |
| 4 | ReadOnlyStore opening SQLite read-write before query_only | `TestCrossFamilyF4ReadOnlyOpensReadOnly` (tools/test_bm_store.py) | Read in full. Behavioural: a read-only open creates nothing in the store directory, and survives a chmod-0500 directory (with an honest platform skip note). Structural: `_connect_read_only` must hand `mode=ro`/`uri=True` to sqlite3.connect and a plain `sqlite3.connect(path,` in that function fails the test. Plus the WAL read-through honesty control and the URI metacharacter sweep. |
| 5 | claim_unit lacking a status predicate | `TestCrossFamilyF5ClaimCannotResurrectARemovedUnit` (tools/test_bm_store.py); controller half `TestCrossFamilyF5StaleSelectionIsDeferred` (tools/test_bm_controller.py) | Read in full. Behavioural: a stale claim on a SKIPPED unit refuses `unit-not-claimable` leaving status and fence linkage untouched. Structural: the UPDATE itself must carry `WHERE unit_id=? AND status IN` plus a rowcount check. Note: the closing predicate is deliberately the SET select_ready_units selects (PENDING or READY), not a literal `status='READY'`; the control test that shapes this is in the class and its reasoning is sound (a literal READY-only predicate would refuse every dependent unit). |
| 6 | record_verification overwriting a terminal verdict | `TestCrossFamilyF6VerdictIsAtMostOnce` (tools/test_bm_store.py) | Read in full. A second verdict (opposite OR identical) refuses `already-verified` leaving the first verdict's row intact; the loser's rejection cannot re-open a DONE unit (status, retry_count and checkpoint_ref all asserted); the two legitimate never-RESULT_IN verification routes are kept by a control test. |

---

## 6. DOCS DELTAS FOR THE ORCHESTRATOR

I made no docs edits. Exact replacement wording follows.

### docs/KNOWN-LIMITS.md

Under "### Deferred, each with its reason", REMOVE the three bullets
("No path floor: ...", "The duplicate-controller refusal is only on
`begin()`. ...", "An empty `allowed_paths` still authorises a unit that
declares no write scope. ...") and, in a new "### Closed 2026-08-06
(L09)" subsection directly above "### Deferred, each with its reason"
(or wherever closed items are recorded in that file's convention), ADD:

> - **The path floor is CLOSED (2026-08-06, founder decision
>   2026-08-05).** A sixth safety floor, `governance-write`, makes
>   writes to BrotherMode's own `.brothermode` store directory, to
>   `.git` (config included) and to `.claude/settings.json`
>   un-authorisable by any contract wording. `sign` refuses an
>   `allowed_paths` entry that names one of those surfaces
>   (`path-is-floor`), and `gate_check` refuses a candidate path inside
>   one (`REFUSED-FLOOR`) BEFORE the `allowed_paths` comparison, so the
>   floor holds under `.`, `*`, `**`, any covering glob, and any
>   hand-written row. A `.` contract stays signable; the floor bites
>   the protected path, never the broad allowance. What remains open by
>   design: a fence claimed over `.` still covers the protected files
>   at the fence layer; the gate refuses any attempt to authorise them
>   as a write path, and the fence hook's own git-containment check is
>   the second defence there.
> - **Controller ownership on `step`, `record-result` and `stop` is
>   CLOSED (2026-08-06).** The run's recorded session id is the driver
>   identity; a caller whose session does not match is refused
>   `not-driver`, with the refusal naming the owning session and the
>   one deliberate takeover path: `bm-controller adopt`, which records
>   the handover durably (attribution event `controller.run.adopted`),
>   mirroring STATE.md fence adoption. Consequence a founder must know:
>   a multi-process CLI flow must carry the SAME `--session-id` across
>   invocations (the store's own documented session convention), or run
>   `adopt` once per takeover. A run row with no recorded session (a
>   store from before this law) is not guarded, the same rule the fence
>   store applies. Still not ownership-guarded: `plan` and the unwired
>   `check_timeouts` (disclosed below), and a TERMINAL run's late
>   result may be recorded by any session, because adoption of a
>   finished run is refused and already-spent work must stay
>   accountable.
> - **An empty `allowed_paths` no longer authorises writing work
>   (CLOSED 2026-08-06, founder decision 2026-08-05).** `sign` refuses
>   (`no-write-scope`) a contract that grants any writing risk class
>   with no declared `allowed_paths`. Genuinely read-only work stays
>   expressible the one way the schema has: grant only
>   `read-only-inspect` and/or `browser-read` (there is no explicit
>   read-only marker column), and the refusal message names that route.

If the file keeps a residual-limits list, ADD these two lines to it:

> - `bm-controller plan` and `check_timeouts` perform no driver
>   ownership check; the L09 round scoped the check to `step`,
>   `record-result` and `stop` as ratified.
> - A candidate path that is an ANCESTOR of a protected surface (`.`
>   itself, or a bare `*`) is still judged by the ordinary scope rules,
>   matching the pinned rule that a `.` contract allows `.`; the floor
>   refuses candidates equal to or inside the protected surfaces.

### docs/AUTONOMY.md

Replace the heading "## The five floors, never grantable by any
contract" with "## The six floors, never grantable by any contract",
and append to its bullet list:

> - `governance-write`: writing to the authorisation machinery itself:
>   the project's own `.brothermode` store, its `.git` directory, or
>   `.claude/settings.json`

After the existing "`gate-check` refuses a floor WITHOUT even reading
the contract" paragraph, ADD:

> `governance-write` is the one PATH-shaped floor (landed 2026-08-06,
> founder decision 2026-08-05). It is enforced twice: `sign` refuses an
> `allowed_paths` entry that names one of the three surfaces, and
> `gate-check` refuses any candidate path inside one before the
> contract's `allowed_paths` are consulted, so no spelling of a broad
> allowance (`.`, `*`, `**`, a covering glob) can reach them. A
> legitimate `local-commit` or `local-branch` is unaffected: those are
> ACTION classes going through git's own porcelain, not path grants
> over `.git`.

In the `sign` documentation, ADD:

> `sign` also refuses a contract that grants any writing risk class
> while declaring no `--allowed-path` (`no-write-scope`): risk class
> alone is not a boundary. Genuinely read-only work signs with no paths
> by granting only `read-only-inspect` and/or `browser-read`, which is
> the schema's one way to say read-only.

Wording nit for a later pass (not this loop's file): tools/bm_lead.py
line 564 says "one of the five floors" in a docstring; docs/FULL-AUTO.md
should also gain the `adopt` command beside the other eight if it lists
them.

---

## 7. Deltas, residuals, and what was NOT done

- WRITE SITES: no delta. No added line in any non-test tools/*.py
  matches the scanner's write patterns (verified by grepping the diff
  for every WRITE_PATTERNS regex; zero hits).
- Raw-execute router / S5 migration exemptions: no delta. No schema
  migration was added; GAP 2 reuses the existing controller_runs
  session_id column, exactly the no-schema-change design the brief
  preferred. The purge dict is untouched.
- NOT ownership-guarded (scoped out by the brief, disclosed): `plan`
  and `check_timeouts`. Both are candidates for the same one-line guard;
  the orchestrator should decide, since `plan` rewrites the unit graph.
- Terminal-run late results: any session may still record a result on a
  COMPLETE/STOPPED/FAILED_TERMINAL run (reasoning in section 2).
- Ancestor candidates: gate_check still allows candidate `.` (and the
  same class, a bare `*` candidate) under a `.` contract, because the
  founder's own pinned test requires it; the floor refuses candidates
  equal to or inside the protected surfaces. A fence over `.` therefore
  still covers protected files at the FENCE layer; the git-containment
  defence in the fence hook (TestFinding5GitContainment) is the
  standing second wall there.
- The sixth floor does not affect `local-commit`/`local-branch` action
  classes (git porcelain writes to .git are an action, not a path
  grant); stated in AUTONOMY_FLOOR_PATHS' comment.
- Not run by this loop (outside the done-check and partly outside my
  writable set): tools/test_bm.py, tools/test_bm_docs.py and the rest
  of the suite family. Note: docs/AUTONOMY.md still says "five floors"
  until the orchestrator lands the deltas above; I found no mechanical
  docs-sync test pinning the floor count (grepped test_bm_docs.py), but
  I did not run that suite.
- CONCURRENT SESSION OBSERVED: while this loop ran, other uncommitted
  changes appeared in the working tree (tools/bm_fence_hook.py,
  tools/bm_runtimes.py, tools/test_bm.py, several docs). None of them
  are mine; my writes were confined to the six allowed tools files and
  this evidence directory. My done-check below was run against the tree
  as it stood at the end, so it includes whatever state those
  concurrent edits were in at that moment.

---

## 8. Done-check, verbatim

Run after the last edit of this loop, in this order, each exiting 0.

```
$ python3 -m py_compile tools/bm_store.py tools/bm_controller.py tools/bm_autonomy.py tools/test_bm_store.py tools/test_bm_controller.py tools/test_bm_autonomy.py
compile-ok
$ python3 tools/test_bm_store.py
Ran 988 tests in 37.844s

OK
exit=0
$ python3 tools/test_bm_autonomy.py
Ran 63 tests in 50.036s

OK
exit=0
$ python3 tools/test_bm_controller.py
Ran 202 tests in 27.350s

OK
exit=0
```

Counts, before and after (no drops, all growth is new tests):

| Suite | Before | After | Delta |
|-------|--------|-------|-------|
| tools/test_bm_store.py | 976 OK | 988 OK | +12 (TestSixthFloorGovernancePaths 6, TestEmptyScopeRefusedAtSigning 6) |
| tools/test_bm_autonomy.py | 58 OK | 63 OK | +5 (TestSixthFloorThroughTheCLI 3, TestEmptyScopeSignRefusalThroughTheCLI 2) |
| tools/test_bm_controller.py | 191 OK | 202 OK | +11 (TestDriverAdoption 10, TestControllerCLIAdopt 1) |

---

# REFUTE ROUND 2 FIXES

An adversarial refuter (docs/program/absolute-lead/evidence/L09/REFUTE-auth-gaps.md)
REFUTED claims A and B end-to-end and left claim C (empty scope) SURVIVED.
This round closes the three reproduced holes the coordinator ratified for
fix (A1, B2, B3) plus the disclosed A2 store-layer gap as defense in
depth. Claim C was NOT touched. Finding B1 (session identity is
self-asserted and public) was deliberately NOT fixed: authenticating a
session id is the fence system's own trust model and a scope extension
the founder did not authorise; no token or secret layer was added, and
the driver guard still compares the self-asserted `--session-id` exactly
as before. The orchestrator discloses B1 in the docs.

Method: each hole was reproduced as a RED test with its calibration twin
FIRST, appended to RED-auth.txt under "L09 REFUTE ROUND 2 RED" and
captured failing (the holes) / passing (the twins and the round-1
regression floor) against the tree before the fix, then fixed at the
class.

## FIX A1: the Claude settings FAMILY is floored, not one literal

Before: `AUTONOMY_FLOOR_PATHS = (STORE_DIRNAME, ".git",
".claude/settings.json")`. `.claude/settings.local.json` was signable,
gate-passed under a `.` contract, and the refuter got a fence and a
dispatched brief over it. In Claude Code the local settings file carries
the same `permissions`/`hooks` power as the shared one and takes HIGHER
precedence, so it is the same authorisation-machinery write the floor
exists to forbid.

After: the two governance DIRECTORY surfaces stay in
`AUTONOMY_FLOOR_PATHS = (STORE_DIRNAME, ".git")`, and the Claude settings
files are floored by a new `_is_claude_settings_path(normalized)`
predicate wired into `_governance_floor_hit`. It floors any file directly
under `.claude` whose final component starts with the stem `settings.`
and ends with `.json`: `settings.json`, `settings.local.json`, and any
same-power `settings.<qualifier>.json` variant. It leaves ALLOWED:
`.claude` itself, `.claude/other.json`, `.claude/mysettings.json` (stem
must START the name), `src/settings.json` and a bare `settings.json` (not
under `.claude`). Enforced at BOTH points, unchanged in shape from round
1: sign time (`path-is-floor`, nothing written) and gate time
(`REFUSED-FLOOR`, `floor: governance-write`, before the allowance loop).

### The exact floor path list, and why (with the grep cited)

- `.brothermode` (STORE_DIRNAME) and `.git`: directory subtrees, matched
  by separator-boundary containment (unchanged from round 1).
- `.claude/settings.json`: cited in scripts/doctor.py, scripts/uninstall.py,
  scripts/rehearse_fresh_install.py.
- `.claude/settings.local.json`: cited in scripts/install.py and the
  2026-08-04 handovers under docs/closure/ (HANDOVER-FULL-AUTO-TO-2.0.0,
  HANDOVER-2026-08-04-TO-A-NEW-MACHINE, PLAN-LOOPS-2-7).
- NO managed/enterprise settings FILE was floored, because none is cited
  in this tree: `grep -rni "managed-settings\|managed_settings" scripts/
  docs/ tools/` returned nothing, and the `enterprise` hits under docs/
  are about Claude subscription plans (ROADMAP.md, visual-surface
  research), not a settings file. An enterprise managed-settings file
  lives at an ABSOLUTE system path outside any project root and so is
  unreachable through a project-relative write scope regardless. The
  floor covers only names the codebase actually cites, plus the
  same-shaped local/scoped variant of them, honouring "do not invent one".

Refusal wording is unchanged except the floor description now reads
"... its .git directory, or a .claude settings file (.claude/settings.json
or .claude/settings.local.json)".

RED -> GREEN: `TestRefuteRound2SettingsFamilyFloor` (tools/test_bm_store.py):
sign refuses settings.local.json; gate REFUSED-FLOOR for settings.json,
settings.local.json AND settings.staging.json under a `.` contract;
neighbours (`.claude`, `.claude/other.json`, `.claude/mysettings.json`,
`src/settings.json`, `settings.json`) stay ALLOWED. Also proven through
the CLI is unchanged; the round-1 CLI floor test still covers
settings.json.

## FIX A2: unit write_scope is floored at PLAN time

Before: `Store.upsert_units` validated a unit's `risk_class` against the
floor ids and canonicalised every `write_scope` entry, but never floored
those entries, so a unit row naming `.git/config` was persisted verbatim.
The refuter confirmed this does NOT become a dispatched write (the
dispatch route's `_gate_check_write_scope` floors it via gate_check
before any fence is claimed), so it was defended-in-depth, not
independently exploitable.

After: right after the write_scope entries are canonicalised,
`upsert_units` refuses `write-scope-is-floor` (nothing written) if any
canonical entry hits `_governance_floor_hit`. The gate remains the
standing wall; this closes the class one layer earlier so no later reader
(a fence claim, a hand-run gate, an SDK caller that never ran `plan`) has
to be the one that catches it.

RED -> GREEN: `TestRefuteRound2UnitWriteScopeFloor` (tools/test_bm_store.py):
a unit write_scope naming `.git/config`, `.brothermode/store.sqlite3` or
`.claude/settings.local.json` is refused with nothing written; an
ordinary `src/a.py` write_scope still plans.

## FIX B2: `plan` now carries the driver guard

Before: `ControllerEngine.plan` (bm_controller.py) called `_run_or_refuse`
and `_refuse_if_paused` but NOT `_refuse_foreign_driver`, so a foreign
session injected the unit graph the honest driver's next step then
dispatched. `plan` is the single most powerful mutation (it defines what
work runs and rewrites the graph, cascading DONE units) and was the one
door round 1 left open.

After: `_refuse_foreign_driver(run, "plan")` is called in the same shape
`step` uses, BEFORE `_refuse_if_paused`, so a foreign session learns "not
yours" before it learns anything about the run's pause state. A
legitimate crash-resume replan is the SAME driver (or a session that ran
`adopt` first), which passes.

RED -> GREEN: `TestRefuteRound2PlanAndTerminalResult` (tools/test_bm_controller.py):
a foreign session's plan is refused `not-driver` with NO unit graph
injected; the same driver (including a fresh engine carrying the same
session id, the crash-resume shape) still plans.

## FIX B3: `receive_result` guards the terminal path too

Before: `receive_result` called `_refuse_foreign_driver` only when
`run["state"] not in _TERMINAL_STATES`, so a foreign session recorded a
late result on a STOPPED run.

After: the guard is UNCONDITIONAL. The legitimate late-result-after-stop
case comes from the run's OWN driver (whose work was in flight when stop
landed and whose session matches), which passes; only a foreign session
is refused.

RED -> GREEN: `TestRefuteRound2PlanAndTerminalResult`: a foreign
session's late result on a STOPPED run is refused `not-driver` with
nothing recorded (`resulted_at` stays None); the run's own driver's late
result on the same terminal run still records (`resulted_at` set, a
string outcome returned).

## What I did NOT touch

- Claim C (empty allowed_paths): SURVIVED per the refuter, untouched.
- B1 (self-asserted, public session identity): NOT fixed by design, per
  the coordinator. No token, secret, HMAC or identity-authentication
  layer was added (verified: the diff adds none). The driver guard
  remains accountability plus the audited `adopt` handover, not
  cryptographic access control; the orchestrator discloses this.
- The Windows trailing-dot/space floor vector the refuter flagged as
  SUSPECTED/unreproduced: not addressed here (it needs a Windows run, and
  the refuter reasoned `os.path.realpath` almost certainly collapses it
  before the floor runs). Flagged, not closed.

## Regression floor kept green

The round-1 "what HELD" cases remain the floor and still pass: every
spelling attack on `.git`/`.brothermode`/`.claude/settings.json` is
REFUSED-FLOOR (TestSixthFloorGovernancePaths sweeps `.`, `*`, `**`), the
neighbours stay ALLOWED, and a genuinely different session is refused
`not-driver` on step/receive_result/stop (TestDriverAdoption). The
round-2 tests add the settings family, the unit-scope floor, and the
plan/terminal-result guards on top.

## Done-check, verbatim (run after the last round-2 edit)

```
$ python3 -m py_compile tools/bm_store.py tools/bm_controller.py tools/bm_autonomy.py tools/test_bm_store.py tools/test_bm_controller.py tools/test_bm_autonomy.py
compile-ok, exit=0

$ python3 tools/test_bm_store.py
Ran 993 tests in 46.957s

OK

$ python3 tools/test_bm_autonomy.py
Ran 63 tests in 43.436s

OK

$ python3 tools/test_bm_controller.py
Ran 206 tests in 29.739s

OK
```

## Final three-suite counts (round 1 -> round 2)

| Suite | After round 1 | After round 2 | Delta |
|-------|---------------|---------------|-------|
| tools/test_bm_store.py | 988 OK | 993 OK | +5 (TestRefuteRound2SettingsFamilyFloor 3, TestRefuteRound2UnitWriteScopeFloor 2) |
| tools/test_bm_autonomy.py | 63 OK | 63 OK | 0 (settings family and empty-scope CLI doors already covered; behaviour unchanged) |
| tools/test_bm_controller.py | 202 OK | 206 OK | +4 (TestRefuteRound2PlanAndTerminalResult 4) |

## Docs delta addendum for the orchestrator (round 2)

The round-1 docs deltas stand. Amend them as follows:

- Wherever the round-1 delta names the governance-write surfaces as
  ".brothermode store, .git, and .claude/settings.json", REPLACE
  ".claude/settings.json" with "a .claude settings file (.claude/settings.json
  or .claude/settings.local.json, and same-power settings.<qualifier>.json
  variants)".
- In the KNOWN-LIMITS "Controller ownership" closed item, the guarded
  door list becomes "step, plan, record-result and stop" (plan was added
  this round); a terminal run's late result is now refused for a FOREIGN
  session and allowed only for the run's own driver. `check_timeouts`
  remains unwired and unguarded.
- Add a one-line residual: B1, driver identity is a self-asserted,
  publicly-readable session id, so the not-driver guard is accountability
  (plus the audited `adopt` handover), not cryptographic access control;
  authenticating a session id was out of scope for L09.
