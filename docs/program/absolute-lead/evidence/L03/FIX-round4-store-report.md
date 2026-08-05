# FIX round 4, the STORE half: report

Writer: round-4 store-half writer. Scope: DESIGN-round4.md sections 5.1 to
5.5, 8.1, 8.3, the store-side parts of 12.2, 12.3 and 12.4, the store
entries of 15.2, and the tools/test_bm_store.py rows of section 17.2.

Files written, and nothing else:

* tools/bm_store.py
* tools/test_bm_store.py
* docs/program/absolute-lead/evidence/L03/RED-round4-store.txt (the RED
  evidence)
* this report

Not touched: tools/bm_controller.py, tools/test_bm_controller.py, any doc,
any checksum, any git state. tools/test_all.py was NOT run.

---

## 0. READ THIS FIRST: one blocked item, and the done-check is NOT DONE

`python3 tools/test_bm_store.py` exits 1, with exactly ONE failure, and it
is an existing test the design did not predict. Per the brief ("if the
design forces a collision with an existing test, STOP on that item and
record it in your report; never weaken an existing test") and per the
design's own section 18.8 ("a writer who finds a SEVENTH test needing a
change must stop and report it rather than editing it"), I did NOT edit it.

**The collision.** tools/test_bm_store.py:16779, in
`TestControllerUpsertUnits.test_writes_the_whole_graph_and_flips_the_run_to_ready`:

```
self.assertEqual(out, {"count": 2})
```

That is an EXACT whole-dict assertion on `upsert_units`' return, and design
section 8.1 mandates three additional keys on that return. The two cannot
both hold. Verbatim failure from the final run:

```
======================================================================
FAIL: test_writes_the_whole_graph_and_flips_the_run_to_ready (__main__.TestControllerUpsertUnits)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_bm_store.py", line 16779, in test_writes_the_whole_graph_and_flips_the_run_to_ready
    self.assertEqual(out, {"count": 2})
AssertionError: {'count': 2, 'skipped': [], 'cancelled_dispatches': [], 'orphaned_fences': []} != {'count': 2}
- {'cancelled_dispatches': [], 'count': 2, 'orphaned_fences': [], 'skipped': []}
+ {'count': 2}

----------------------------------------------------------------------
Ran 839 tests in 27.446s

FAILED (failures=1)
EXIT=1
```

Why the design missed it: section 8.1 checked the CONTROLLER consumer
("`cmd_plan` reads only `result["count"]`, so the extra keys break
nothing") and section 18.7 reviewed only the two store classes the glob
change touches. Nobody grepped the store suite for an exact-shape
assertion on this return.

**Why I could not dodge it.** The only shapes that keep
`out == {"count": 2}` true are (a) not returning the new keys at all, which
removes the mechanism section 8.2 step 4 depends on (`plan()` iterates
`result["orphaned_fences"]`), or (b) returning the extra keys only when
non-empty, which makes `upsert_units`' return shape conditional and turns
every honest `result["skipped"]` into a KeyError on the quiet path. Both
are worse than the collision.

**The one-line remedy, for whoever owns the decision** (it is NOT a
weakening: it keeps the exact-whole-dict assertion and pins three more
facts, that a plain plan drops nothing, cancels nothing and orphans
nothing):

```python
                self.assertEqual(out, {"count": 2, "skipped": [],
                                       "cancelled_dispatches": [],
                                       "orphaned_fences": []})
```

Every other item in my scope has a passing command quoted in section 1;
nothing below is called done without one, and section 7 lists exactly what
I did not verify. The store suite goes green the moment this one line is
settled.

---

## 1. Done-check, run after the last edit

### 1.1 The whole store suite

```
$ cd /Users/khalil.maaouni/Documents/BrotherModeUp && python3 tools/test_bm_store.py
...
Ran 839 tests in 27.446s

FAILED (failures=1)
EXIT=1
```

**NOT DONE**, for exactly the one reason in section 0 and no other. 839
tests ran; 820 is the count the design predicted for the untouched suite
(section 17.3) and 820 + 19 new = 839, so no test was deleted or lost.
One failure, zero errors.

### 1.2 The nineteen new tests, the eight new classes

```
$ cd /Users/khalil.maaouni/Documents/BrotherModeUp/tools && python3 -m unittest \
    test_bm_store.TestGlobAllowedPathsAreDepthExact \
    test_bm_store.TestGlobNarrowingBreaksNothingElse \
    test_bm_store.TestGateCheckReturnsAVerdictInsteadOfRaising \
    test_bm_store.TestGateCheckVerdictComesFromOneContractRead \
    test_bm_store.TestUpsertUnitsClosesTheSkippedLifecycle \
    test_bm_store.TestUpsertUnitsRefusesANonPathWriteScopeEntry \
    test_bm_store.TestReleaseClaimedUnit \
    test_bm_store.TestGetDispatch
...................
----------------------------------------------------------------------
Ran 19 tests in 0.306s

OK
EXIT=0
```

Per class: TestGlobAllowedPathsAreDepthExact 4, TestGlobNarrowingBreaks
NothingElse 2, TestGateCheckReturnsAVerdictInsteadOfRaising 3,
TestGateCheckVerdictComesFromOneContractRead 1, TestUpsertUnitsClosesThe
SkippedLifecycle 4, TestUpsertUnitsRefusesANonPathWriteScopeEntry 1,
TestReleaseClaimedUnit 2, TestGetDispatch 2. Total 19.

### 1.3 The autonomy suite, because it consumes gate_check directly

Design 17.3 calls this not optional, and it is a store-side consumer
(tools/bm_autonomy.py:527 and 539), so I ran it:

```
$ cd /Users/khalil.maaouni/Documents/BrotherModeUp/tools && python3 test_bm_autonomy.py
..........................................................
----------------------------------------------------------------------
Ran 58 tests in 23.029s

OK
EXIT=0
```

The controller suite is the controller-half writer's done-check and I did
not run it; see section 7.

---

## 2. SIGNATURES: build on these, not on the design's prose

Every function I added, or whose signature or return shape moved. Exact
`def` lines from tools/bm_store.py as it now stands.

| # | Line | Exact signature | Status |
|---|---|---|---|
| 1 | 565 | `def path_within_allowed(allowed, candidate):` | signature UNCHANGED, behaviour changed (glob branch only), returns bool |
| 2 | 2618 | `CONTROLLER_DISPATCH_STATUSES = ("DISPATCHED", "RESULT_IN", "VERIFIED", "REJECTED", "CANCELLED")` | NEW module tuple |
| 3 | 12527 | `def spend_totals(self, project_id):` | signature and return shape UNCHANGED; body now delegates |
| 4 | 12535 | `def _spend_totals_from(self, project_id, latest):` | NEW |
| 5 | 12611 | `def gate_check(self, project_id, action_class, path=None, surface=None):` | signature UNCHANGED, never raises on a bad path, one contract read |
| 6 | 12897 | `def upsert_units(self, run_id, units, actor):` | signature UNCHANGED, **RETURN SHAPE CHANGED** |
| 7 | 13371 | `def record_result(self, dispatch_id, worker_claim, result_artifacts, actor):` | signature and success return UNCHANGED, one NEW refusal reason |
| 8 | 13503 | `def release_claimed_unit(self, unit_id, actor):` | NEW |
| 9 | 13642 | `def get_dispatch(self, dispatch_id, raw=False):` | NEW |
| 10 | 13960 | `def _spend_totals_from(self, project_id, latest):` (ReadOnlyStore) | NEW pass-through, see 2.7 |
| 11 | 14012 | `def get_dispatch(self, dispatch_id, raw=False):` (ReadOnlyStore) | NEW pass-through |

### 2.1 `upsert_units` return, the one shape change

```python
{"count": int,                       # units in THIS call, unchanged meaning
 "skipped": [unit_id, ...],          # unit ids this call dropped
 "cancelled_dispatches": [dispatch_id, ...],
 "orphaned_fences": [(unit_id, fence_uuid), ...]}
```

All four keys are ALWAYS present; the three new ones are `[]` on a plan
that drops nothing. `orphaned_fences` entries are 2-TUPLES, not dicts and
not lists, so `for unit_id, fence_uuid in result["orphaned_fences"]:`
unpacks directly. Only units with a non-empty `fence_uuid` appear there.

Behaviour note the design does not state, and the controller writer should
know: a unit that was ALREADY SKIPPED by an earlier plan and is still
absent from this one is re-reported in `skipped` (and its fence in
`orphaned_fences`) on every later plan that also omits it. The re-park is
harmless because `_release_fence` is idempotent on a fence that is not
active, but `cmd_plan`'s founder-facing count will say "1 skipped" on each
such re-plan. I kept the design's literal loop rather than adding a
"changed status only" filter it did not ask for.

### 2.2 `get_dispatch` return

The full `controller_dispatches` row as a dict, or `None` for an unknown
id. Keys: `dispatch_id, unit_id, run_id, project_id, attempt,
contract_revision, fence_uuid, status, worker_claim, result_artifacts,
done_check_exit, verifier_verdict, session_id, created_at, resulted_at`.

**Use `raw=True`, which is what design section 10.2 step 2 already says.**
At the `raw=False` default this goes through `_export_row`, and I verified
what that withholds by running it:

```
raw=False: ... 'fence_uuid': '[WITHHELD: 2 chars of founder text]', ...
               'result_artifacts': '[WITHHELD: 2 chars of founder text]',
               'session_id': '[WITHHELD: 4 chars of founder text]' ...
raw=True : ... 'fence_uuid': 'f1', 'result_artifacts': [], 'session_id': 'sess' ...
```

`dispatch_id`, `unit_id`, `run_id`, `project_id`, `attempt`,
`contract_revision` and `status` survive at raw=False, so the foreign-id
guard of 12.2 would work either way, but anything reading the fence uuid
or the artifacts needs raw=True, and `result_artifacts` decodes to a real
list only at raw=True.

### 2.3 `release_claimed_unit` return and refusals

```python
{"unit_id": str, "status": "READY" or "PENDING"}
```

READY or PENDING by dependency satisfaction, the same recomputation
`unblock_lane_units` performs. It clears `fence_uuid` on the unit row and
does NOT touch `retry_count` (a claim that never became a dispatch was
never an attempt). Refusals: `'not-found'` for an unknown unit id,
`'unit-not-claimed'` for any status other than CLAIMED. It does NOT
release the fence itself; the engine parks it, same split as
`orphaned_fences` and for the same nested-BEGIN reason.

### 2.4 `record_result`'s new refusal

Success return is unchanged (`{'dispatch_id', 'unit_id', 'status':
'RESULT_IN'}`). New branch, checked BEFORE the existing
`'already-resulted'` branch:

* reason `'dispatch-cancelled'`, message "dispatch %r is CANCELLED: a
  re-plan dropped unit %r from the unit graph, so this dispatch was
  cancelled and the result cannot be recorded against it."

VERIFIED and REJECTED still refuse `'already-resulted'`, unchanged.

### 2.5 `gate_check`'s new verdict path

Still returns the same five keys and still never writes. A path that
cannot be read as a path (non-string, empty, or resolving outside the
root, including through a symlink created after the plan was written) now
returns:

```python
{"verdict": "REFUSED-SCOPE", "floor": None,
 "reason": "%r cannot be read as a path inside this project (%s), so "
           "nothing about it can be authorised." % (path, exc),
 "contract_id": latest["contract_id"], "revision": latest["revision"]}
```

No new verdict word. `_gate_check_one_pass` and `bm-autonomy gate-check`
need no new branch.

### 2.6 `_spend_totals_from`

Returns exactly what `spend_totals` returns (`tokens, minutes,
token_ceiling, minutes_ceiling, token_pct, minutes_pct, verdict`), against
an already-read raw contract row. `latest=None` is accepted and yields the
no-data shape, so `spend_totals`' public behaviour for a project with no
contract is byte-identical.

### 2.7 One deviation from the design's inventory, and why

Design 15.2 lists a ReadOnlyStore pass-through for `get_dispatch` only. A
pass-through for `_spend_totals_from` is ALSO required and I added one
(tools/bm_store.py:13960). Reason, caught by an existing test rather than
by me: `ReadOnlyStore` does not inherit from `Store`, it borrows methods by
explicit delegation, so the moment `Store.spend_totals` and
`Store.gate_check` reach `self._spend_totals_from`, a read-only
`spend_totals` raised

```
AttributeError: 'ReadOnlyStore' object has no attribute '_spend_totals_from'
```

in `TestAutonomyConcurrencyReadOnlyAndClock.test_adversarial_a_read_only_store_answers_gate_check_and_has_no_write_method_at_all`.
The pass-through only SELECTs, so it is safe on a `query_only` connection.
This is an addition to the design's inventory, not a change to any
behaviour it specified.

---

## 3. What changed in tools/bm_store.py, per design section

| Design | Change | Where |
|---|---|---|
| 5.1 | `import fnmatch` joins the stdlib block | 62 |
| 5.1 | `path_within_allowed`: non-glob branch is now the literal `_prefix_contains(na, nb)` (identical expression, since `_coverage_key(na) == na` for a non-glob), glob branch is segment-count-exact `fnmatch.fnmatchcase` per segment | 565 to 625 |
| 5.4 | `gate_check` wraps `canonicalize_path(self.root, _coerce_path_entry(path), cwd=None)` in `except (OwnershipRefused, ValueError)` and returns REFUSED-SCOPE | 12700 to 12712 |
| 5.5 | `spend_totals` delegates to the new `_spend_totals_from`; `gate_check` calls `self._spend_totals_from(project_id, latest)` with the row it already read | 12527, 12535, 12727 |
| 8.1 | `CONTROLLER_DISPATCH_STATUSES` with the new terminal `CANCELLED` | 2618 |
| 8.1 | `upsert_units`' SKIPPED loop cancels that unit's `DISPATCHED`/`RESULT_IN` dispatches in the same transaction, and collects `skipped`, `cancelled_dispatches`, `orphaned_fences` | 13158 to 13190 |
| 8.1 | `upsert_units` returns the four keys | 13233 |
| 8.1 | `record_result` refuses `'dispatch-cancelled'` for a CANCELLED dispatch | 13388 |
| 8.3 | `upsert_units` REVIVES a byte-identical re-add of a SKIPPED unit, writing ONLY the status via `_status_for` | 13056 to 13078 |
| 12.2 | `Store.get_dispatch` plus the ReadOnlyStore pass-through | 13642, 14012 |
| 12.3 | the unit INSERT is wrapped in `except sqlite3.IntegrityError`, which looks the id's owner up and raises `OwnershipRefused('unit-id-taken', ...)` naming the id, the owning project, the owning run and the fix (prefix ids per project); re-raises if no owner row exists, so a NON-primary-key integrity failure is never mislabelled | 13102 to 13156 |
| 12.4 | `upsert_units` canonicalises each write_scope entry through `_coerce_path_entry` first | 13010 to 13020 |
| 15.2 | `Store.release_claimed_unit` | 13503 |

Also updated, prose only: `upsert_units`' docstring (the new return shape,
the cancel, the revival, the `unit-id-taken` refusal), `gate_check`'s
step-5 docstring line (an unreadable path is a verdict, not a raise), and
the ReadOnlyStore comment that enumerates the write methods it refuses to
define (now names `release_claimed_unit`).

**Not touched, deliberately:** `paths_overlap`, `_coverage_key`,
`_literal_prefix_dir`, `_prefix_contains`, `_normcase`, `_to_posix`,
`canonicalize_path`, `CONTROLLER_STATE_TRANSITIONS`,
`CONTROLLER_UNIT_STATES`, `AUTONOMY_FLOORS`, `SCHEMA_VERSION` (still 15),
`_MIGRATIONS`, `_DUMP_SAFE_COLUMNS`, and all DDL. No schema change of any
kind: `CANCELLED` is a new value in an unconstrained TEXT column
(`controller_dispatches.status` has no CHECK).

---

## 4. RED first: the evidence, and the one control

`docs/program/absolute-lead/evidence/L03/RED-round4-store.txt`, 325 lines,
one labelled block per class, captured by running each class against the
UNTOUCHED tools/bm_store.py BEFORE any store edit:

```
cd /Users/khalil.maaouni/Documents/BrotherModeUp/tools
python3 -m unittest -v test_bm_store.<class>
```

| Class | RED result on the untouched tree |
|---|---|
| TestGlobAllowedPathsAreDepthExact | FAILED (failures=4) |
| TestGlobNarrowingBreaksNothingElse | OK (CONTROL, see below) |
| TestGateCheckReturnsAVerdictInsteadOfRaising | FAILED (errors=3) |
| TestGateCheckVerdictComesFromOneContractRead | FAILED (failures=1) |
| TestUpsertUnitsClosesTheSkippedLifecycle | FAILED (failures=1, errors=3) |
| TestUpsertUnitsRefusesANonPathWriteScopeEntry | FAILED (errors=1) |
| TestReleaseClaimedUnit | FAILED (errors=2) |
| TestGetDispatch | FAILED (errors=2) |

Seven of eight reproduce their finding. Representative lines, verbatim
from that file:

```
AssertionError: 'ALLOWED' != 'REFUSED-SCOPE'
 : allowed_paths ['*.py'], candidate 'secrets.env' must be REFUSED-SCOPE, got ALLOWED

bm_store.OwnershipRefused: path 'escape/x.py' resolves outside the project root /private/var/...
ValueError: empty path
AttributeError: 'int' object has no attribute 'strip'

AssertionError: Tuples differ: ('ALLOWED', 1) != ('REFUSED-BREAKER', 1)
```

**The eighth is a CONTROL and is stated as one, in the RED file, in its own
docstring and here.** `TestGlobNarrowingBreaksNothingElse` is green before
AND after on purpose: the containment property AZ proved over 6682 triples
lives in the non-glob branch, which section 5.1 leaves behaviourally
identical, and this class exists to fail if the glob narrowing takes a
plain path with it. It is the same role AZ's own C1b control plays in the
controller suite ("must stay green", design 17.1). I am flagging it
because design 17 says a class that passes on the untouched tree is not
evidence; this one is not offered as evidence of a defect, it is offered
as a regression fence, and the design's own 5.1 property list is what it
pins.

---

## 5. The nineteen tests, and what each pins

tools/test_bm_store.py, appended at 17368 to 17825, one section header and
one helper (`_gate_verdicts`, 17377) that asserts verdicts through
`Store.gate_check` rather than through `path_within_allowed`, because
gate_check is the founder-facing surface (design 5.3).

* **TestGlobAllowedPathsAreDepthExact** (17397, 4 tests). The four
  matrices of section 5.3: `api/*.py` (including the `api/pay.py/`
  trailing-slash convergence row and the `api/**` row that proves `**` is
  not recursive), `*.py`, `*` and `src/*`, then `src/*/main.py`,
  `src/?.py` and `src/[ab].py`.
* **TestGlobNarrowingBreaksNothingElse** (17457, 2 tests). The non-glob
  rows of 5.3 (`src`, `src/app`, `.`) and a spelling matrix over
  `["src"], ["src/"], ["./src"], ["src/."]` against `./src/a.py`,
  `src/./a.py`, `src//a.py`, `src/a.py/` and `src/sub/../a.py`, plus a
  case-mismatched allowed path GATED on `bs._CASE_INSENSITIVE_PLATFORMS`
  so the row is asserted only where `_normcase` actually folds.
* **TestGateCheckReturnsAVerdictInsteadOfRaising** (17501, 3 tests).
  Symlink created after the plan, non-string path, empty path. Each
  asserts REFUSED-SCOPE plus a real `contract_id` and `revision`.
* **TestGateCheckVerdictComesFromOneContractRead** (17549, 1 test). A
  supersede is injected into gate_check's own SECOND `_latest_contract_row`
  call via `mock.patch.object(bs, "_latest_contract_row", ...)`, exactly
  as AZ's D1.5 probe does it. The assertion is on the VERDICT, not on a
  call count: a verdict stamped revision 1 must be revision 1's verdict in
  every field. Once there is only one read, nothing fires.
* **TestUpsertUnitsClosesTheSkippedLifecycle** (17602, 4 tests). Dispatch
  cancellation plus the `'dispatch-cancelled'` refusal on the same
  dispatch; `orphaned_fences`; the byte-identical revival (asserting
  retry_count, definition_hash and created_at all survive); the
  `'unit-id-taken'` refusal with a clean rollback (zero units, run still
  PLANNING).
* **TestUpsertUnitsRefusesANonPathWriteScopeEntry** (17715, 1 test). The
  `[5] / [['a.py']] / [{'p':'a.py'}] / [True]` matrix, each refusing
  `'bad-path'` and writing nothing.
* **TestReleaseClaimedUnit** (17743, 2 tests). READY for a dependency-free
  unit and PENDING for a dependent one, fence cleared, retry_count
  untouched; `'unit-not-claimed'` and `'not-found'`.
* **TestGetDispatch** (17793, 2 tests). The row with its `run_id` and
  `project_id`; None for an unknown id, on both `Store` and
  `ReadOnlyStore`, plus an assertion that `release_claimed_unit` is NOT
  defined on `ReadOnlyStore`.

I did not modify any existing test, in this file or anywhere else.

---

## 6. Verification I ran beyond the suites

* **Blast radius of `path_within_allowed`, grepped not assumed.** Exactly
  one live caller in the whole tree, `Store.gate_check`
  (tools/bm_store.py:12708). The only other hits are the two docstring
  mentions (tools/bm_store.py:12631, tools/bm_controller.py:938). The
  design's 5.2 claim holds.
* **`upsert_units`' one production caller** is
  tools/bm_controller.py:394 (`ControllerEngine.plan`), which returns the
  dict onward. That is the controller half's to handle.
* **`spend_totals` callers** (tools/bm_autonomy.py:792,
  tools/bm_controller.py:449 and 2200, tools/bm_store.py:12488) all use
  the public method, whose signature and return shape did not move.
* **No em dash or en dash** in either file I wrote or in the RED file
  (grep over all three, zero hits).
* **`git status --porcelain`** on my three paths: `tools/bm_store.py` and
  `tools/test_bm_store.py` modified, the RED file untracked. I ran no git
  command that changes state.

---

## 7. What I did NOT do, stated plainly

* **The done-check is NOT DONE** on `python3 tools/test_bm_store.py`, for
  the single collision in section 0. Everything else in that run passed.
* **tools/test_all.py was not run**, as instructed.
* **tools/test_bm_controller.py was not run.** The store's `upsert_units`
  return, `record_result`'s new refusal and the tighter `path_within_allowed`
  are all reachable from that suite, so it may well be red until the
  controller half lands. I make NO claim about it either way.
* **I did not touch tools/bm_controller.py**, so nothing in this change is
  wired up yet: `get_dispatch`, `release_claimed_unit`,
  `orphaned_fences`, `cancelled_dispatches` and `CONTROLLER_DISPATCH_STATUSES`
  have no production caller until the controller half exists. The store
  methods are proven by their own tests; the ENGINE behaviour those
  primitives exist for is unproven here.
* **Design 16.1 (AUTONOMY_FLOORS, the path floor) is untouched**, as
  instructed and as the design defers.
* **`CONTROLLER_STATE_TRANSITIONS` was not widened.** `upsert_units` still
  makes exactly its old PLANNING to READY move through
  `_set_run_state_locked`.
* **Not verified by me:** whether `cmd_status`' open-dispatch display
  (tools/bm_controller.py:2189 to 2195) filters correctly now that
  CANCELLED exists. The design (section 13) asserts it already reads
  dispatch rows and only needs CANCELLED excluded, "which it is". I read
  neither that code nor that claim, because bm_controller.py is outside my
  scope. The controller-half writer should confirm it rather than inherit
  the assumption.
* **Not verified by me:** the docs. Sections 5.1, 12.1, 12.3, 12.4 and 16
  all require disclosure text in docs/AUTONOMY.md and
  docs/KNOWN-LIMITS.md, and I wrote none of it: docs are outside my scope.
  In particular the glob rule ("a plain path grants its subtree, a glob
  grants exactly what it matches at its own depth") is now TRUE IN CODE
  and UNDOCUMENTED, and the FIX-round3 disclosure that AZ F-A2 refuted is
  still standing in whatever doc carries it.
* **The NUL-byte path row** AZ noted alongside F-A8 stays accepted, as
  design 12.4 states. `_coerce_path_entry` refuses non-strings only.
