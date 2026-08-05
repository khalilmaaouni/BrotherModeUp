# FIX round 5, the STORE half: report

Writer: the round-5 STORE writer. Files written, and no others:

* `tools/bm_store.py`
* `tools/test_bm_store.py`
* `docs/KNOWN-LIMITS.md` (one appended section, nothing above it touched)
* `docs/program/absolute-lead/evidence/L03/RED-round5-store.txt`
* this report

`tools/bm_controller.py`, `tools/test_bm_controller.py` and
`docs/FULL-AUTO.md` belong to the other writer and were READ, never written.

Source: `REFUTATION-4-authorization.md` findings F1, F2, F3, F11, plus F10
as data for a disclosure. Method: fail first, capture, fix, re-run.

---

## 0. READ THIS FIRST: one item is CLOSED IN PART, and it is the headline one

AZ F1 has two halves and this round closes one of them. The half where the
CANDIDATE is a pattern (`write_scope ['*.py']`, the whole-project grant, the
recursive `git restore` rollback, `src/[a]pp` as a bypass spelling) is closed
at the source: a write scope entry must now be a literal path. The half where
a glob ALLOWANCE admits a plain DIRECTORY at its own depth (AZ's own
reproduction 4: contract `['src/*']`, unit `write_scope ['src/app']`, fence
covers `src/app/deep/keys.pem`) SURVIVES, because closing it means moving a
verdict that `tools/test_bm_store.py`'s round-4 matrix pins in both
directions, and an existing test is law. Both candidate remedies were RUN
against those tests and both collide; the verbatim failures are in section 3
and in `RED-round5-store.txt`. It is disclosed in `docs/KNOWN-LIMITS.md`.

AZ F2's store-side guard is landed on eleven entry points and proved by test.
It only BITES when the caller names the project, and the shipped
`bm-controller plan` command lives in the other writer's file, so the CLI
route in AZ's reproduction stays open until that one-argument change lands.
That is stated again in sections 2 and 7 and in `KNOWN-LIMITS.md`.

Checked before landing, so the parallel writer is not broken by this: every
`write_scope` literal in `tools/test_bm_controller.py` and
`tools/bm_controller.py` is already a plain path (16 distinct values, all
literal, listed by
`grep -rnoE 'write_scope\s*=\s*\[[^]]*\]' tools/test_bm_controller.py`), so
the new refusal cannot turn their suite red.

---

## 1. Per-finding table

| Finding | Sev | Verdict | What landed | Proof |
|---|---|---|---|---|
| F1, the candidate half (a unit declares a pattern; the fence and the rollback read it as its literal prefix; `allowed_paths ['*.py']` authorises the project) | HIGH | **CLOSED** | `literal_scope_entry` (bm_store.py:795), called from `upsert_units` (13164) before `canonicalize_path`. A `write_scope` entry containing `*`, `?` or `[` refuses `glob-write-scope`, naming the entry, the unit and the remedy. | `TestWriteScopeEntriesAreLiteralPaths` (5 tests), `TestGlobAllowancesGrantOnlyWhatTheyLiterallyMatch::test_every_pattern_spelling_is_undeclarable_so_the_sweep_is_complete` |
| F1, the allowance half (a glob allowance admits a plain directory, whose subtree the fence then covers) | HIGH | **NOT CLOSED, STOPPED on a pinned-test collision** | nothing; characterised and disclosed instead | section 3, `RED-round5-store.txt` COLLISION block, `KNOWN-LIMITS.md` |
| F3 (`src/[a]pp` ALLOWED where `src/app` is REFUSED-SCOPE, because a glob is never resolved past its literal prefix) | HIGH | **CLOSED on the declaration side** | same one gate: a character class cannot be declared, so there is no second spelling of a refused path to find | `TestWriteScopeEntriesAreLiteralPaths::test_a_character_class_can_no_longer_re_spell_a_path_that_escapes` (real symlink out of a real temp root) |
| F2 (`plan --project p1 --run <p2's run>` writes p2: un-pauses it, cancels its dispatches, parks its fences, replaces its graph) | HIGH | **CLOSED in the store; needs one caller change to close at the CLI** | `Store._refuse_foreign_run` (12928) plus an optional `project_id` on ELEVEN write entry points (section 2), refusing `run-not-in-project` before any write | `TestRunScopedWritesRefuseAForeignProject` (5 tests), including the exact PAUSED-run reproduction |
| F11 (`_coerce_path_entry` documented TOTAL, raises for `__fspath__`/`__repr__` that raise anything but TypeError) | LOW | **CLOSED** | `_safe_repr` (721); `_coerce_path_entry` (736) catches `Exception` at the `os.fspath` boundary and formats every refusal through `_safe_repr`; `gate_check`'s unreadable-path branch does the same | `TestCoercePathEntryIsTotalForAnyObject` (3 tests), object raising `RuntimeError` from BOTH dunders |
| F10 (an empty write scope is dispatched under a narrow contract and claims an empty fence) | LOW | **DISCLOSED, not fixed** (as instructed) | `KNOWN-LIMITS.md`, with the refuter's data replacing the old "NO-DATA" reason | n/a |
| Path floor (design 16.1), duplicate-driver adoption (16.2) | | **already disclosed**, unchanged | pointed at from the new section rather than restated | `KNOWN-LIMITS.md` "Deferred, each with its reason" |

Suite counts: store 839 before, **855 after** (16 new tests, 0 removed).
Autonomy 58 before, 58 after.

---

## 2. F2: every entry point that resolves a run from a caller-supplied id

Grepped, not assumed. The generator that produced this list:

```
python3 - <<'EOF'
import re
src = open('tools/bm_store.py').read()
for m in re.finditer(r'^\s*def (\w+)\(([^)]*)\)', src, re.M):
    if 'run_id' in m.group(2) or 'project_id' in m.group(2):
        print(src[:m.start()].count('\n')+1, m.group(1))
EOF
```

**Before this round, NO store entry point took a project id and a run id
together.** That is the whole reason nothing in the store could refuse AZ's
reproduction: the store was never told which project the caller meant. The
close therefore had to ADD the argument, as an optional one, so no existing
caller or test changes behaviour.

### Guarded (11 write entry points, all now `project_id=None`)

| Entry point | Line | Id the caller supplies | Guard call |
|---|---|---|---|
| `set_run_state` | 12976 | run id | 13000, BEFORE the idempotent no-op |
| `upsert_units` | 13035 | run id | 13114, before any read of the unit graph |
| `claim_unit` | 13458 | unit id | 13474 |
| `record_dispatch` | 13484 | unit id | 13506, before the INSERT |
| `record_result` | 13534 | dispatch id | 13554, before the CANCELLED and status checks |
| `record_verification` | 13589 | dispatch id | 13608 |
| `mark_unit_done` | 13622 | unit id | 13639 |
| `mark_unit_failed` | 13655 | unit id | 13671 |
| `release_claimed_unit` | 13685 | unit id | 13712 |
| `block_lane_units` | 13737 | run id | 13751 |
| `unblock_lane_units` | 13762 | run id | 13774 |

All three tables carry `project_id` and `run_id` on the row, so the guard is
one shared method reading the row the method had already fetched: no schema
change, no second read, no new transaction.

### Deliberately NOT guarded, with the reason

| Entry point | Line | Why not |
|---|---|---|
| `open_run` | 12860 | takes a project id and MINTS the run id; there is no caller-supplied run to disagree with it |
| `select_ready_units` | 13410 | READ only. Also on `ReadOnlyStore` |
| `list_units` | 13814 | READ only |
| `get_run` | 13801 | takes a project id only; the run is derived |
| `get_dispatch`, `list_dispatches` | 13834, 13855 | READ only. `get_dispatch` exists precisely so the ENGINE can perform the foreign check round 4 added |
| `purge_project` | 11336 | takes a project id and a confirmation token; no run id |

The rule I applied: the refusal exists to stop a WRITE landing on a run the
caller did not mean. A read of another project's unit list is an information
question, not a corruption one, and guarding it would change `ReadOnlyStore`'s
surface for no measured defect. It is named here rather than left implicit.

### What still has to happen for F2 to be closed at the CLI

`tools/bm_controller.py:617` calls `self.store.upsert_units(run_id, units,
self.actor)`. Adding `project_id=project_id` there (and at the other engine
call sites that already hold the project id) makes AZ's exact command refuse.
That file belongs to the other writer this round, so the store-side half is
what I landed, and the KNOWN-LIMITS entry says plainly that the refusal
protects callers that opt in until the caller change lands.

---

## 3. F1's surviving half: the collision, measured

The property `gate_check`'s docstring states is: *a path this check ALLOWS
can never name a file that a directly named path would be REFUSED for.*

With patterns removed from the declarable universe, I swept **55440**
(allowed, candidate, file) triples over literal candidates, using the store's
own primitives for both relations (`path_within_allowed` for the verdict,
`_coverage_key` plus `_prefix_contains` for what a fence claim covers, which
is the directional half of the call `tools/bm_fence_hook.py:637` makes).

Result: **35 violations, 0 of them under a non-glob allowance.** Every one is
the same shape: a glob allowance admits a plain directory at exactly the
glob's own depth (`['src/*']` admits `src/app`, `['*']` admits `src`), and a
fence over a directory covers its subtree, while the same contract refuses
`src/app/main.py` by name. AZ's reproduction 4, unchanged by this round.

Closing it means moving the ALLOWANCE side. Both directions were RUN, by
monkeypatching `test_bm_store`'s own `bm_store` instance (`gate_check`
resolves `path_within_allowed` as a module global at call time, so the patch
exercises the shipped path) and running the two round-4 classes that pin the
rule. No source file was edited to produce this.

**Remedy A, a glob allowance grants the subtree of what it matches**
(`len(b) >= len(a)`, match the first `len(a)` segments). Ran 6, failures 1:

```
FAIL: test_a_bare_star_is_one_segment_and_a_directory_glob_is_one_level
      (test_bm_store.TestGlobAllowedPathsAreDepthExact)
  at tools/test_bm_store.py:17441
AssertionError: 'ALLOWED' != 'REFUSED-SCOPE'
 : allowed_paths ['*'], candidate 'src/a.py' must be REFUSED-SCOPE, got ALLOWED (authorised against risk class 'file-edit'.)
```

That is the whole-project grant coming back by the front door: under remedy A,
`['*']` authorises everything at every depth again.

**Remedy C, a glob allowance grants nothing** (patterns refused on both
sides). Ran 6, failures 4:

```
FAIL: test_a_bare_star_is_one_segment_and_a_directory_glob_is_one_level
  at tools/test_bm_store.py:17441
 : allowed_paths ['*'], candidate 'main.py' must be ALLOWED, got REFUSED-SCOPE ('main.py' is outside this contract's allowed paths.)
FAIL: test_a_directory_glob_admits_only_its_own_directory_at_its_own_depth
  at tools/test_bm_store.py:17415
 : allowed_paths ['api/*.py'], candidate 'api/pay.py' must be ALLOWED, got REFUSED-SCOPE ('api/pay.py' is outside this contract's allowed paths.)
FAIL: test_a_leading_wildcard_does_not_escape_its_own_directory
  at tools/test_bm_store.py:17432
 : allowed_paths ['*.py'], candidate 'main.py' must be ALLOWED, got REFUSED-SCOPE ('main.py' is outside this contract's allowed paths.)
FAIL: test_a_wildcard_segment_matches_one_segment_character_for_character
  at tools/test_bm_store.py:17451
 : allowed_paths ['src/*/main.py'], candidate 'src/app/main.py' must be ALLOWED, got REFUSED-SCOPE ('src/app/main.py' is outside this contract's allowed paths.)
```

Remedy C also contradicts this round's own written constraint that
`api/*.py` must keep working as a founder-authored allowance.

**STOPPED, per the method. Minimal proposed remedy for whoever owns the next
round**, stated so it can be costed rather than guessed: the two verdicts that
collide are `("src/app", "ALLOWED")` and `("src/app/main.py",
"REFUSED-SCOPE")` under `["src/*"]`, asserted together at
`tools/test_bm_store.py:17444` to `17447`. They cannot both stay true while a
plain directory grants its subtree. The smallest coherent change is to make a
glob allowance grant the subtree of what it matches (remedy A) AND amend that
one round-4 row plus the `["*"]` row to match, which is a deliberate rule
change with a founder-facing sentence attached ("a pattern grants the subtree
of everything it matches"), not a bug fix. It must be decided by whoever owns
the rule, with the round-4 test matrix edited in the same change and the
teachable one-liner in `docs/AUTONOMY.md` and `docs/KNOWN-LIMITS.md` rewritten
with it. I did not take that decision and did not touch those tests.

What I DID land against it: `TestGlobAllowancesGrantOnlyWhatTheyLiterallyMatch`
characterises the residual exactly (zero violations under a non-glob
allowance; every surviving violation is depth-exact admission followed by
subtree coverage). It stays green if a later round removes the residual
entirely, and goes red the moment a violation of any OTHER shape appears.

---

## 4. SIGNATURES: build on these, not on this report's prose

### 4.1 New module-level function

```python
def literal_scope_entry(f, unit_id=None):
    """total coercion + the literal-path rule for a WRITE SCOPE entry."""
    # returns str, or raises OwnershipRefused:
    #   'bad-path'          (from _coerce_path_entry, unchanged semantics)
    #   'glob-write-scope'  NEW: entry contains one of * ? [
    # details for 'glob-write-scope': {"entry": str, "unit_id": str or None}
```

Public on purpose: any future caller that stores what a worker will WRITE
should share this gate. `Store.claim`'s own `files` argument deliberately does
NOT go through it (a fence claim asks the symmetric "can these two name the
same file", where a glob is meaningful, and `tools/test_bm_store.py:11893`
pins a glob claim working today).

```python
def _safe_repr(f):   # NEW, private: repr() that cannot itself raise
```

### 4.2 New refusal reason

`'glob-write-scope'`, raised by `literal_scope_entry`, therefore reachable
from `upsert_units`. `'run-not-in-project'`, raised by `_refuse_foreign_run`,
reachable from the eleven methods in section 2. Both are new members of the
store's kebab-case refusal vocabulary; neither widens an enumerated constant.

### 4.3 Eleven signatures gained ONE trailing optional keyword

Every one of these gained `project_id=None` as the LAST parameter. No
positional argument moved, no return shape changed, and omitting it reproduces
the previous behaviour exactly (proved by the 839 pre-existing tests, none of
which pass it).

```python
set_run_state(run_id, new_state, actor, reason, session_id, project_id=None)
upsert_units(run_id, units, actor, project_id=None)
claim_unit(unit_id, fence_uuid, actor, project_id=None)
record_dispatch(unit_id, attempt, contract_revision, fence_uuid, session_id,
                actor, project_id=None)
record_result(dispatch_id, worker_claim, result_artifacts, actor,
              project_id=None)
record_verification(dispatch_id, done_check_exit, verifier_verdict, accepted,
                    actor, project_id=None)
mark_unit_done(unit_id, checkpoint_ref, actor, project_id=None)
mark_unit_failed(unit_id, actor, reason, project_id=None)
release_claimed_unit(unit_id, actor, project_id=None)
block_lane_units(run_id, lane, actor, project_id=None)
unblock_lane_units(run_id, lane, actor, project_id=None)
```

### 4.4 One private method added

```python
Store._refuse_foreign_run(row, project_id, what, subject)
# no-op when project_id is None or row['project_id'] == project_id
# else raises OwnershipRefused('run-not-in-project', ...) with details
#   {"named_project_id", "owner_project_id", "owner_run_id"}
```

### 4.5 Return shapes: NONE moved

`upsert_units` still returns `{'count', 'skipped', 'cancelled_dispatches',
'orphaned_fences'}`. `set_run_state` still returns `{'state', 'changed'}`.
`gate_check` still returns the same seven-key verdict dict with the same
closed vocabulary; only the TEXT of the unreadable-path reason changed, from
`%r` of the path to `_safe_repr` of it, which is byte-identical for every
object whose `repr` works.

### 4.6 One behaviour change existing callers can see

A `write_scope` entry containing `*`, `?` or `[` now refuses where it used to
be accepted. Nothing in `tools/`, `docs/`, `references/` or any shipped
example declares such a scope (grepped: the only glob-bearing scope string in
the tree is a fence CLAIM in `tools/test_bm_store.py:11893`, which is
untouched), so no shipped caller changes behaviour. A founder whose plan file
used a pattern now gets a refusal naming the entry and the remedy instead of a
fence over the wrong subtree.

---

## 5. RED first: the evidence

`docs/program/absolute-lead/evidence/L03/RED-round5-store.txt`, captured
against the UNTOUCHED store before any edit, per class:

| Class | Tests | Result at capture |
|---|---|---|
| `TestWriteScopeEntriesAreLiteralPaths` | 5 | 4 failures, 1 error |
| `TestGlobAllowancesGrantOnlyWhatTheyLiterallyMatch` | 3 | 1 error, 2 green by design (one CONTROL, one CHARACTERISATION, both named in the file) |
| `TestRunScopedWritesRefuseAForeignProject` | 5 | 5 errors (`TypeError: ... unexpected keyword argument 'project_id'`) |
| `TestCoercePathEntryIsTotalForAnyObject` | 3 | 3 errors (`RuntimeError: fspath blows up` escaping `gate_check`) |

One of those errors was MY OWN test's bug, not the store's, and the RED file
says so at the top rather than quietly correcting it: the control called
`json.loads` on a `write_scope` that `list_units(raw=True)` had already
decoded. The assertion was corrected to compare the decoded list; the
corrected control was then re-run against the PRE-FIX gate (by monkeypatching
`literal_scope_entry` back to a plain `_coerce_path_entry`) and is green
there too, which is what a control is for.

The COLLISION block in the same file carries section 3's two remedy runs.

---

## 6. Done-check, run after the last edit

Quoted from the brief, in order.

```
$ cd /Users/khalil.maaouni/Documents/BrotherModeUp && python3 tools/test_bm_store.py
----------------------------------------------------------------------
Ran 855 tests in 25.223s

OK
EXIT=0
```

```
$ cd /Users/khalil.maaouni/Documents/BrotherModeUp && python3 tools/test_bm_autonomy.py
----------------------------------------------------------------------
Ran 58 tests in 21.857s

OK
EXIT=0
```

```
$ cd /Users/khalil.maaouni/Documents/BrotherModeUp/tools && python3 -m unittest \
    test_bm_store.TestWriteScopeEntriesAreLiteralPaths \
    test_bm_store.TestGlobAllowancesGrantOnlyWhatTheyLiterallyMatch \
    test_bm_store.TestRunScopedWritesRefuseAForeignProject \
    test_bm_store.TestCoercePathEntryIsTotalForAnyObject
----------------------------------------------------------------------
Ran 16 tests in 0.154s

OK
EXIT=0
```

Counts: 839 store tests before this round, 855 after, so 16 added and none
removed. 58 autonomy tests before and after. `tools/test_all.py` and the
controller suite were NOT run, as instructed.

---

## 7. What I did NOT do, stated plainly

1. **F1's allowance half is open.** Section 3. Disclosed, characterised by a
   test, and stopped on a measured collision rather than worked around.
2. **F2 is not closed at the command line.** The store refuses; the shipped
   `plan` command still does not pass `project_id`, and that file is not
   mine. One argument at `tools/bm_controller.py:617` finishes it.
3. **`Store.claim` still accepts a glob in `files`.** Deliberate: a fence
   claim is the symmetric overlap question and `tools/test_bm_store.py:11893`
   pins the current behaviour. The controller's fence claim is built from a
   unit's `write_scope`, which is now literal, so the controller path
   inherits the property without the fence's own semantics moving.
4. **`read_scope` is still not canonicalised or checked** (AZ F9). Not in my
   brief, not touched, and it is a real HIGH-adjacent finding someone owns.
5. **Read entry points are not project-guarded.** Section 2, with the reason.
6. **No new founder-facing documentation.** `docs/AUTONOMY.md` still teaches
   only the round-4 one-liner; the new `glob-write-scope` refusal is
   explained in `docs/KNOWN-LIMITS.md` and in the refusal message itself, not
   in the autonomy guide, because that page is not mine this round.
7. **Not exercised**: two real processes against one store file, and any run
   of the shipped CLI (every test here drives the store's Python API).
8. **The 35 residual violations are a property of the sweep vocabulary I
   chose**, not a count of anything in the real world. The vocabulary is in
   the test, so the number moves if the vocabulary does; what the test
   asserts is the SHAPE, and the zero under non-glob allowances.
