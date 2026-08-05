# DESIGN round 4: the L03 Full-Auto controller after REFUTATION 3

Target tree: /Users/khalil.maaouni/Documents/BrotherModeUp
Files this design authorises a writer to change:
tools/bm_controller.py, tools/bm_store.py, tools/test_bm_controller.py,
tools/test_bm_store.py, docs/FULL-AUTO.md, docs/KNOWN-LIMITS.md,
docs/AUTONOMY.md, and one new RED evidence file named in section 17.
Nothing else. No git state, no checksums, no other evidence page.

Inputs read in full before writing this: FIX-round3-report.md,
REFUTATION-3-state-machine.md, REFUTATION-3-authorization.md,
REFUTATION-3-liveness.md, tools/bm_controller.py (all 2432 lines), and
tools/bm_store.py at every point the controller touches it.

Every line reference below is to the CURRENT working tree, verified by
reading it, not by memory.

---

## 0. What round 3 established and this design does not touch

These four things STOOD under three independent lenses. No section below
changes their behaviour, and any writer who finds themselves editing them
has misread this document.

1. **The straddle machinery and the one-revision dispatch stamp.**
   `_gate_check_write_scope` (tools/bm_controller.py:902 to 982), its
   two-pass loop (971 to 975), the `_DEFERRED_CONTENTION` verdict (976 to
   982), `_gate_check_one_pass` (984 to 1003) and the stamp at
   tools/bm_controller.py:1074 to 1076. Fourteen amend placements and
   eight constructed races could not break them
   (REFUTATION-3-authorization.md, surfaces 3 and 4). Section 6 REUSES
   `_gate_check_write_scope` verbatim as the first step of the new choke
   point and changes nothing inside it.
2. **The containment property of `path_within_allowed` for NON-GLOB
   paths** (tools/bm_store.py:564 to 600, the `_prefix_contains` branch at
   600). Zero counterexamples in 6682 triples. Section 5 leaves the
   non-glob branch byte-for-byte equivalent and changes only the glob
   branch.
3. **The `check_timeouts` walk and settle** (tools/bm_controller.py:767 to
   775 and 786 to 787). Twenty-eight of twenty-eight matrix cells held.
   Section 11 changes only which units it iterates over and adds the
   PAUSED guard; the walk and the settle are untouched.
4. **The consequence order inside `_reject`** (tools/bm_controller.py:1240
   to 1251: warning, then fence park, then the state move, and the move
   only when `CONTROLLER_STATE_TRANSITIONS` allows it). Attacked five
   ways, held. Section 10 adds ONE thing beside it (section 10.4) and
   reorders nothing.
5. **`_is_founder_waiting` for genuinely in-flight dependencies**
   (tools/bm_controller.py:1454 to 1465). Section 8 adds a third arm to
   the predicate and does not weaken the two that exist.

---

## 1. Coverage table: every refuted finding, and where it is closed

Report keys: **SM** = REFUTATION-3-state-machine.md, **AZ** =
REFUTATION-3-authorization.md, **LV** = REFUTATION-3-liveness.md.

| Finding | One line | Closed in |
|---|---|---|
| SM A (HIGH) | a PAUSED run dispatches new units through the shipped CLI | 4.2, 4.3, 4.5 |
| SM B (HIGH) | `_deliver_or_hold` performs the founder-only PAUSED to READY edge | 4.3, 9.2 |
| SM C (HIGH) | every late result silently drops its SPEND (regression) | 10.1 |
| SM D (HIGH) | a late result at the retry ceiling tells the founder nothing | 10.3 |
| SM E (HIGH) | `step` reports a state the store does not hold | 3.2, 3.3, 7.2 |
| SM F (HIGH) | BLOCKED is manufactured with no reversal and is not a dead status | 8.3, 8.4, 10.4 |
| SM G (MEDIUM) | the state read and the handler body are not atomic | 12.1 (bounded, stated) |
| SM H (MEDIUM) | `_reject`'s survive branch leaves the unit selectable | 10.5 |
| SM I (MEDIUM) | FAILED_RECOVERABLE is judged without ever reaching VERIFYING | 6.4 |
| SM J (MEDIUM) | `run_to_completion` burns max_steps on the ordinary async park | 3.1, 9.1 |
| SM K (MEDIUM) | a dispatch id from a previous run crashes with TypeError | 12.2 |
| SM L (MEDIUM, self healing) | `check_timeouts` racing a real result | 11.2 |
| SM obs 3 | the staleness rejection never rolls back | 10.6 |
| SM obs 4 | `_warn_dirty_write_scope` writes into the hard-coded lane "default" | 10.4 |
| SM obs 5 | `_handle_no_ready_units` reads human steps project wide | 8.5 (stated, not changed) |
| AZ F-A1 (HIGH) | the re-await hands a worker a brief with NO gate_check | 6.1, 6.2, 6.3 |
| AZ F-A2 (HIGH) | a glob admits its prefix directory, any depth, and (leading wildcard) the whole project | 5 |
| AZ F-A3 (HIGH) | record-result charges spend to a contract that never authorised the work, then crashes | 12.2 |
| AZ F-A4 (HIGH) | `plan` tracebacks on a unit id another project used | 12.3 |
| AZ F-A5 (HIGH) | `gate_check` RAISES instead of returning a verdict | 5.4 |
| AZ F-A6 (HIGH) | no path floor: a `.` contract authorises the store's own database | **DEFERRED, 16.1** |
| AZ F-A7 (MEDIUM) | the duplicate-controller refusal is only on `begin()` | **DEFERRED, 16.2** |
| AZ F-A8 (MEDIUM) | a non-string write_scope entry is an uncaught AttributeError | 12.4 |
| AZ F-A9 (LOW) | one gate_check verdict formed from two contract revisions | 5.5 |
| AZ F-A10 (LOW) | an empty allowed_paths still authorises a unit with no write scope | **DEFERRED, 16.3** |
| LV 1 (HIGH) | a gate-refused unit wedges the run in EXECUTING forever | 7.1, 9.2 |
| LV 2 (HIGH) | the SKIPPED escalation creates an irreversible BLOCKED remainder | 8.1, 8.2, 8.3, 8.4 |
| LV 3 (HIGH) | the founder-waiting branch writes WAITING_HUMAN into the summary only | 3.2, 7.2, 8.4 |
| LV 4 (HIGH) | record-result on a dropped unit's still-open dispatch marks it DONE | 8.1 |
| LV 5 (MEDIUM) | the park stop fires on non-founder contention with a founder note | 3.1, 3.4 |
| LV 6a (MEDIUM) | soft spend stop spins | 3.1, 9.1 |
| LV 6b (MEDIUM) | a failing done-definition re-runs the founder's suite once per wasted step | 9.1, 9.3 |
| LV 6c (MEDIUM) | an unrecoverable outage spins | 9.1, 6.5 |
| LV 7 (LOW) | `_IN_FLIGHT_UNIT_STATUSES` and `_anything_in_flight` disagree about CLAIMED | 13 |
| LV 4 related | a dropped unit's open dispatch is never timed out | 8.1, 11.1 |
| FIX residual 3 | `_resume_result_in_and_orphans` re-queues from PAUSED | 4.4 |
| FIX residual 4 | soft spend stop spin | 9.1 |
| FIX residual 5 | the dual-load OwnershipRefused split | 17.4 (test-shape rule) |

Three findings are DEFERRED with a named reason in section 16. Nothing
else is left unmapped.

---

## 2. The five laws this design adds, in one place

Everything below is an application of one of these. A writer who is unsure
what to do in a case this document did not enumerate applies these in
order.

* **L1 PAUSED belongs to the founder.** No engine path dispatches, judges,
  verifies, delivers, abandons or un-pauses a PAUSED run. Only
  `bm-controller resume` (tools/bm_controller.py:2294 to 2329) leaves
  PAUSED.
* **L2 The summary never says anything the store does not hold.** Every
  `step()` exit passes through one funnel that re-reads the run row and
  writes the state it found.
* **L3 Control flow reads the enum, never the prose.** `stop_reason` is
  the only field any loop or CLI driver branches on. Notes are for the
  founder.
* **L4 Derived facts are recomputed, not remembered.** Unreachability is
  recomputed every wave. BLOCKED is a materialised view of "your lane
  holds an open founder step" and is reconciled in both directions on
  every wave.
* **L5 One route, one gate.** A unit row becomes a brief a worker may be
  handed through exactly one function, and that function performs the gate
  check and the fence work.

`CONTROLLER_STATE_TRANSITIONS` (tools/bm_store.py:2540 to 2563) is NOT
widened by any of this. Every state move named below is already in that
table; section 15.3 lists each one with the table line that permits it.

---

## 3. The `stop_reason` enum, and the one exit funnel

### 3.1 The enum

New module-level constant in tools/bm_controller.py, beside the note
constants at 272 to 279:

```python
STOP_REASONS = ("FOUNDER_WAITING", "CONTENTION", "SPEND_STOP", "OUTAGE",
                "NOTHING_SELECTABLE", "IN_FLIGHT", "DELIVERED", "TERMINAL")
```

Every summary `step()` returns carries `summary["stop_reason"]`: either
`None`, meaning the wave made progress and a loop may call `step()` again,
or exactly one member of `STOP_REASONS`, meaning the loop must stop.
`bs` is not involved; this is the ENGINE's own vocabulary about its own
loop, not a store law.

Meaning of each member, fixed here so no writer has to guess:

| Reason | Means | A founder must act? |
|---|---|---|
| `TERMINAL` | the run is COMPLETE, STOPPED or FAILED_TERMINAL | no, it is over |
| `DELIVERED` | the run is DELIVERABLE_READY | yes, `bm-controller complete` |
| `FOUNDER_WAITING` | PAUSED, or every remaining unit waits on a human, or the done-definition fails | yes |
| `SPEND_STOP` | the soft spend stop is on and nothing is in flight | yes, raise the ceiling or accept the stop |
| `OUTAGE` | the worker answered "unavailable" | no, retry later |
| `CONTENTION` | a fence overlap or a double contract amend deferred every unit | **no, and the note may not say otherwise** |
| `IN_FLIGHT` | at least one dispatch is open, awaiting `record-result` | no |
| `NOTHING_SELECTABLE` | nothing selectable, nothing in flight, nothing founder-gated | yes, inspect the graph |

### 3.2 The funnel

New engine method. EVERY `return` in `step()` goes through it, with no
exceptions:

```python
def _finish(self, summary, project_id, stop_reason=None, note=None):
    """The ONE exit from step(). Re-reads the run row and writes the
    state it ACTUALLY found into the summary, so summary['state'] is a
    store read at return time and never a prediction (L2, closes
    SM E and LV 3: _handle_no_ready_units wrote summary['state'] =
    'WAITING_HUMAN' at tools/bm_controller.py:1444 while the store move
    at 1440 to 1443 was guarded, and both shipped loop drivers branch on
    the summary)."""
```

Rules inside it:
* `summary["state"] = self.store.get_run(project_id, raw=True)["state"]`,
  unconditionally, last thing before returning.
* `summary["stop_reason"]` is set from the argument when the argument is
  not None, and otherwise LEFT ALONE, so a reason already written by
  `_handle_no_ready_units` or `_deliver_or_hold` survives the funnel.
* `summary["note"]` is set from the argument when given, otherwise left.
* A `stop_reason` outside `STOP_REASONS` is a `ValueError` raised here.
  This is engine-internal, so a typo must fail loudly in tests rather
  than silently disable a loop stop, exactly the reason the import-time
  walk-edge guard at tools/bm_controller.py:261 to 266 exists.

`_handle_no_ready_units` and `_deliver_or_hold` write their reason
through one tiny helper so the field is never assigned by hand:

```python
def _set_reason(self, summary, stop_reason, note):
```

### 3.3 The summary shape after this change

```
{"run_id": str, "state": str, "dispatched": [str], "completed": [str],
 "note": str, "stop_reason": str or None,
 "founder_gated": {...}   # only on the DELIVERED exit, unchanged}
```
`stop_reason` is ADDITIVE. `state`, `note`, `dispatched`, `completed` and
`founder_gated` keep their current meanings, so `cmd_step`
(tools/bm_controller.py:2039 to 2043) and `_report_trace`
(tools/bm_controller.py:1884 to 1904) keep working; both gain one printed
line for the reason (section 14).

### 3.4 The CONTENTION note may never claim a founder is needed

The current text at tools/bm_controller.py:568 to 570 appends
"nothing is in flight either, so the run is parked until a founder acts"
to whatever note the wave wrote, including
`_NOTHING_CLAIMABLE_NOTE` (274 to 277), which `_claim_and_dispatch`
writes for a fence overlap (1069) and for the round-3 contention deferral
(1020). LV 5 reproduced both. Under this design the loop appends NOTHING;
each reason carries its own fixed note, as module constants beside the
existing ones:

```python
_NOTE_CONTENTION = ("another writer holds a fence over this unit's files, "
                    "or the contract was amended twice while the unit was "
                    "being checked; no founder action is needed and the "
                    "next step tries the same unit again")
_NOTE_NOTHING_SELECTABLE = (_NOTHING_SELECTABLE_NOTE +
                            "; nothing is in flight either, so the run is "
                            "parked until a founder acts")
_NOTE_IN_FLIGHT = ("waiting for %d open dispatch(es); record a result "
                   "with bm-controller record-result")
_NOTE_SPEND_STOP = ("soft-stop: %d unit(s) selectable but no new dispatch; "
                    "raise the ceiling or accept the stop")
_NOTE_OUTAGE = ("the worker reported itself unavailable; the dispatch "
                "stays open and the same attempt is retried on the next "
                "step, no founder action is needed")
_NOTE_RUN_PAUSED = ("the controller run is PAUSED; only bm-controller "
                    "resume leaves that state, and this engine will not "
                    "dispatch, judge or deliver until it does")
```

`_NOTHING_SELECTABLE_NOTE` and `_NOTHING_CLAIMABLE_NOTE` (272 to 277) stay
as prose. `_NO_PROGRESS_NOTES` (278 to 279) is DELETED: its only consumer
is the note-string stop at 566, which `stop_reason` replaces (L3).

---

## 4. PAUSED is a founder-only gate, uniformly

### 4.1 The shared guard

```python
def _run_or_refuse(self, project_id):
    """The run row, or bs.OwnershipRefused('no-run', ...). Exactly the
    refusal step() raises today at tools/bm_controller.py:406 to 410,
    lifted so every entry point shares one copy."""

def _is_paused(self, run):
    return run["state"] == "PAUSED"

def _refuse_if_paused(self, run, action):
    """bs.OwnershipRefused('run-paused', ...) naming `action` and telling
    the founder to run bm-controller resume first."""
```

Both are called at the TOP of the entry point, before any read of the
contract, any unit list, any resume branch. `_resume_result_in_and_orphans`
(tools/bm_controller.py:792) verifies a RESULT_IN dispatch and reverses
FAILED_RECOVERABLE, so the guard must precede it, not follow it.

### 4.2 What each entry point does when the RUN is PAUSED

| Entry point | Behaviour | Why |
|---|---|---|
| `step` (398) | return immediately through `_finish(summary, project_id, "FOUNDER_WAITING", _NOTE_RUN_PAUSED)`. No store write of any kind. | closes SM A: `_walk_to_executing` (1340) is a silent no-op from PAUSED and nothing downstream re-checks, so 498 claims a fence, 1074 records a dispatch and 511 hands the brief to a worker |
| `receive_result` (589) | see 4.3 | the result is real and must not be destroyed |
| `check_timeouts` (725) | return `[]` without touching a dispatch | abandoning a dispatch records a result and a rejected verification and runs a rollback command; that is the engine acting on a paused run |
| `plan` (377) | `_refuse_if_paused(run, "plan")` | `upsert_units` flips the run to READY (tools/bm_store.py:13045 to 13056) and PAUSED to READY IS legal (tools/bm_store.py:2556), so `bm-controller plan` today un-pauses a paused run |
| `run_to_completion` (538) | no guard of its own; its first `step()` returns FOUNDER_WAITING and the loop stops on the first iteration | one guard, checked once (the orchestrator's direction 1) |
| `stop` (1633) | UNCHANGED, allowed | a founder stop is a founder action, and PAUSED to STOPPING is legal (tools/bm_store.py:2557) |
| `begin` (354) | unchanged | `open_run` already refuses 'run-exists' for a non-terminal run (tools/bm_store.py:12716 to 12729) |

### 4.3 `receive_result` on a PAUSED run HOLDS the result

Round 3 routes PAUSED to `_handle_late_result` (614 to 616), which
records a rejected verification, burns a retry, runs the founder's
rollback command against the filesystem and parks the fence. That
destroys a real answer because the founder paused, and a pause is
reversible.

New behaviour, a THIRD outcome word:

1. `record_result(dispatch_id, worker_claim, artifacts, actor)` runs
   (tools/bm_store.py:13175), so the answer is durable and at-most-once
   recording still holds.
2. Spend is recorded under the same live-contract guard section 10.1
   defines.
3. Nothing else. No verification, no rollback, no fence move, no state
   move.
4. `receive_result` returns the string `"held"`.

When the founder runs `bm-controller resume`, the run goes PAUSED to
READY and the very next `step()` reaches
`_resume_result_in_and_orphans`'s RESULT_IN branch (826 to 851), which
walks to VERIFYING and verifies the held answer on its own merits. That
branch already exists and needs no change.

This is what makes SM B unreachable as well: `_deliver_or_hold` can no
longer be entered from a PAUSED run, because every caller of
`_settle_after_wave` is now behind the guard.

### 4.4 `_deliver_or_hold` never takes the PAUSED edge, structurally

Section 9.2 replaces the legality test at tools/bm_controller.py:1585
("is READY legal from here") with an explicit, derived source set that
does not contain PAUSED. Legality is not the right question; ownership of
the edge is, which is exactly what `_walk_reaches_rejectable`'s own
docstring already says at tools/bm_controller.py:229 to 238.

This also closes FIX residual 3: the PAUSED half of
`_resume_result_in_and_orphans` is unreachable because the guard returns
before it. The STOPPING half was proved unreachable by SM surface 5 and
needs nothing.

### 4.5 The founder-facing wording

`cmd_step` and `_report_trace` print the reason and the note. On a PAUSED
run the founder sees, in the same output, `state PAUSED` and a note
naming `bm-controller resume`. SM A's second consequence (a note saying
"parked in EXECUTING" for a run the same output calls PAUSED) cannot
occur, because that note is only written on a path that dispatched.

---

## 5. Authorisation: glob containment, and a gate check that never raises

### 5.1 The exact matching rule

`path_within_allowed` (tools/bm_store.py:564 to 600) becomes:

```python
na = _normcase(_to_posix(allowed))
nb = _normcase(_to_posix(candidate))
if not na or not nb:
    return False
if na == ".":
    return True
if nb == ".":
    return False
if not _has_glob(na):
    return _prefix_contains(na, nb)          # UNCHANGED containment
a_segs = na.split("/")
b_segs = nb.split("/")
if len(a_segs) != len(b_segs):
    return False
return all(fnmatch.fnmatchcase(b, a) for a, b in zip(a_segs, b_segs))
```

Four properties, stated so a reader can hold the code to them:

* **The non-glob branch is behaviourally identical to today.** For a
  non-glob, non-empty, non-dot `na`, `_coverage_key(na) == na`
  (tools/bm_store.py:534), so today's `_prefix_contains(_coverage_key(na),
  nb)` at line 600 and the new `_prefix_contains(na, nb)` are the same
  expression. The 6682-triple property AZ proved therefore survives
  untouched.
* **A glob is DEPTH EXACT.** Segment counts must match, so `api/*.py`
  admits `api/pay.py` and refuses `api`, `api/notes.md` and
  `api/sub/deep/secrets.env`.
* **A leading wildcard does not escape its own directory.** `*.py`
  compares one segment against one segment, so `src/prod/db.sql` (three
  segments) is refused. The empty-prefix widening at
  tools/bm_store.py:515 to 516 is never reached, because the glob branch
  never calls `_coverage_key`.
* **`fnmatchcase`, never `fnmatch`.** `fnmatch.fnmatch` applies
  `os.path.normcase` itself, which on win32 is `ntpath.normcase` and
  rewrites `/` to `\`, the exact defect `_normcase`'s GATE 2 comment
  documents at tools/bm_store.py:462 to 471. Both sides arrive already
  folded by `_normcase`, so case handling stays where it is and stays
  platform-correct.

`**` is NOT recursive under this rule: `api/**` admits exactly the direct
children of `api`. The recursive spelling is the plain directory, `api`,
which the containment branch already handles. That is the whole teachable
rule for a founder: **a plain path grants its subtree, a glob grants
exactly what it matches at its own depth.** It goes in docs/AUTONOMY.md
and docs/KNOWN-LIMITS.md, replacing the disclosure the FIX report wrote
(which named one sibling file and understated the blast radius, AZ F-A2).

`import fnmatch` joins the stdlib import block at tools/bm_store.py:59 to
74. `paths_overlap` (537 to 561), `_coverage_key` (520 to 534) and
`_literal_prefix_dir` (495 to 507) are NOT touched, so every fence
semantic is unchanged (the orchestrator's direction 5).

### 5.2 Blast radius, grepped not assumed

`path_within_allowed` has exactly ONE caller in the whole tree:
`Store.gate_check` at tools/bm_store.py:12626. No test calls it directly.
No test in tools/ signs a contract with a glob in `allowed_paths`
(the controller suite's own `_sign` helper defaults to `["."]`,
tools/test_bm_controller.py:268 to 278). So this change alters no
existing assertion; it only narrows `gate_check` and, through it,
`bm-autonomy gate-check` (tools/bm_autonomy.py:527) and
`_gate_check_one_pass` (tools/bm_controller.py:995).

### 5.3 The test matrix

Every row is a `gate_check` verdict, since that is the founder-facing
surface. Rows marked WAS come straight from AZ's probe output, so the
failing-first evidence is exact.

| allowed_paths | candidate | new verdict | was |
|---|---|---|---|
| `["api/*.py"]` | `api/pay.py` | ALLOWED | ALLOWED |
| `["api/*.py"]` | `api/*.py` | ALLOWED | ALLOWED |
| `["api/*.py"]` | `api/notes.md` | REFUSED-SCOPE | ALLOWED |
| `["api/*.py"]` | `api` | REFUSED-SCOPE | ALLOWED |
| `["api/*.py"]` | `api/sub/deep/secrets.env` | REFUSED-SCOPE | ALLOWED |
| `["api/*.py"]` | `api/*` | REFUSED-SCOPE | ALLOWED |
| `["api/*.py"]` | `api/**` | REFUSED-SCOPE | ALLOWED |
| `["api/*.py"]` | `other/x.py` | REFUSED-SCOPE | REFUSED-SCOPE |
| `["api/*.py"]` | `.` | REFUSED-SCOPE | REFUSED-SCOPE |
| `["*.py"]` | `main.py` | ALLOWED | ALLOWED |
| `["*.py"]` | `secrets.env` | REFUSED-SCOPE | ALLOWED |
| `["*.py"]` | `src/prod/db.sql` | REFUSED-SCOPE | ALLOWED |
| `["*.py"]` | `infra/terraform/prod.tfstate` | REFUSED-SCOPE | ALLOWED |
| `["*.py"]` | `.github/workflows/ci.yml` | REFUSED-SCOPE | ALLOWED |
| `["*"]` | `main.py` | ALLOWED | ALLOWED |
| `["*"]` | `src` | ALLOWED | ALLOWED |
| `["*"]` | `src/a.py` | REFUSED-SCOPE | ALLOWED |
| `["src/*"]` | `src/app` | ALLOWED | ALLOWED |
| `["src/*"]` | `src/app/main.py` | REFUSED-SCOPE | ALLOWED |
| `["src/*"]` | `src` | REFUSED-SCOPE | ALLOWED |
| `["src/*/main.py"]` | `src/app/main.py` | ALLOWED | ALLOWED |
| `["src/*/main.py"]` | `src/main.py` | REFUSED-SCOPE | REFUSED-SCOPE |
| `["src/?.py"]` | `src/a.py` | ALLOWED | ALLOWED |
| `["src/?.py"]` | `src/ab.py` | REFUSED-SCOPE | ALLOWED |
| `["src/[ab].py"]` | `src/a.py` | ALLOWED | ALLOWED |
| `["src/[ab].py"]` | `src/c.py` | REFUSED-SCOPE | ALLOWED |
| `["src"]` | `src`, `src/a.py`, `src/app/deep/x.py` | ALLOWED | ALLOWED |
| `["src"]` | `.`, `srcx`, `src_secrets/keys.py` | REFUSED-SCOPE | REFUSED-SCOPE |
| `["src/app"]` | the whole 15583 matrix in tools/test_bm_store.py | unchanged | unchanged |
| `["."]` | `.`, `src`, `src/app/main.py`, `secrets.env` | ALLOWED | ALLOWED |

Trailing-slash, `./`, `//` and dot-segment spellings converge before the
rule runs, because `_to_posix` (443 to 456) already normalises them; the
matrix includes `api/pay.py/` to pin that.

### 5.4 `gate_check` returns a verdict instead of raising

`Store.gate_check` calls `canonicalize_path` at tools/bm_store.py:12625,
which raises `OwnershipRefused('path-escape')` from
`_resolve_against_root` (613 to 652) whenever the path resolves outside
the root, including through a symlink created AFTER the plan was written,
and raises `ValueError("empty path")` at 674. AZ F-A5 reproduced a run
wedged permanently in EXECUTING because `_gate_check_one_pass`
(tools/bm_controller.py:995) calls it in a bare loop.

Change, inside `gate_check`'s `if path is not None:` block (12623 to
12632):

```python
try:
    candidate = canonicalize_path(self.root, _coerce_path_entry(path),
                                  cwd=None)
except (OwnershipRefused, ValueError) as exc:
    return {"verdict": "REFUSED-SCOPE", "floor": None,
            "reason": "%r cannot be read as a path inside this project "
                      "(%s), so nothing about it can be authorised."
                      % (path, exc),
            "contract_id": latest["contract_id"],
            "revision": latest["revision"]}
```

Three decisions, each justified:

* `_coerce_path_entry` (tools/bm_store.py:690 to 727) is the store's own
  TOTAL path coercion: for any input it returns a string or raises
  `OwnershipRefused('bad-path')`. Reusing it means a non-string path
  becomes a refusal here too, with no new primitive invented.
* The verdict word is **REFUSED-SCOPE, not a new one.** The verdict set is
  a founder-facing vocabulary enumerated in docs/AUTONOMY.md and branched
  on at tools/bm_controller.py:1027 and 1033 and
  tools/bm_autonomy.py:539. Widening it would ripple into all three. The
  controller's existing handling of REFUSED-SCOPE (fail the unit through
  the circuit breaker, escalate at the ceiling) is also exactly the right
  handling for an unresolvable path.
* `gate_check` still NEVER writes (its own docstring, 12555 to 12557).
  Nothing above changes that.

Result on AZ's own reproduction: `bm-controller step` no longer raises
three times in a row; the unit is failed through the breaker, the second
refusal exhausts it, an interruption names the collision
(tools/bm_controller.py:1055 to 1061), and section 8's escalation names
the run's remainder to the founder.

### 5.5 One contract read per verdict

`gate_check` reads the contract at 12586 and then calls
`self.spend_totals(project_id)` at 12641, which performs its own
`_latest_contract_row` read at 12487. AZ F-A9 showed a single verdict
whose class and path halves come from revision N and whose breaker half
comes from N+1.

Change: extract the body of `spend_totals` (12482 to 12498) into

```python
def _spend_totals_from(self, project_id, latest):
    """spend_totals against an ALREADY-READ contract row, so a caller
    that has one does not take a second, racing read."""
```

`spend_totals` keeps its exact public signature and return shape and
becomes `return self._spend_totals_from(project_id,
_latest_contract_row(self, project_id))`. `gate_check` calls
`self._spend_totals_from(project_id, latest)` with the row it read at
12586. Every field of the verdict then comes from one row, which is what
the docstring at 12583 to 12585 already promises.

---

## 6. One choke point for every dispatch

### 6.1 Every current site that records a dispatch or hands out a brief

Grepped, not assumed:

| Site | What it does today |
|---|---|
| `_claim_and_dispatch`, tools/bm_controller.py:1005 to 1080 | gate_check (1018), fence claim (1065), `claim_unit` (1071), `record_dispatch` (1074), `_build_brief` (1077) |
| `step`, tools/bm_controller.py:498 | calls `_claim_and_dispatch` per ready unit |
| `step`, tools/bm_controller.py:511 | `self.worker.run(claimed["brief"])` |
| `_resume_dispatched`, tools/bm_controller.py:858 to 898 | `_build_brief` at 882, `self.worker.run(brief)` at 890, **no gate_check anywhere** (AZ F-A1) |
| `_build_brief`, tools/bm_controller.py:1082 to 1091 | pure builder, called from 1077 and 882 |
| `_resume_result_in_and_orphans`, tools/bm_controller.py:792 to 856 | NOT a dispatch route: it goes straight to `_verify_and_finish` (844) and never builds a brief or calls the worker |
| `RecordIntentWorker.run`, tools/bm_controller.py:183 to 186 | the sink |

So exactly two routes hand a brief to a worker, and one of them has no
gate check at all.

### 6.2 The choke point

```python
def _authorise_dispatch(self, project_id, run_id, unit, open_dispatch=None):
    """THE ONE route from a unit row to a brief a worker may be handed
    (L5). Returns (claimed, outcome):

      claimed  {'unit_id','dispatch_id','fence_uuid','contract_revision',
                'brief'} or None
      outcome  None      claimed is not None, hand the brief over
               'DEFER'   contention: nothing burned, nothing drained,
                         the unit is tried again next wave
               'DRAIN'   REFUSED-STATE or REFUSED-BREAKER: the whole run
                         is draining
               'REFUSED' this unit was failed through the circuit breaker

    open_dispatch is None on the FRESH route and the open dispatch row on
    the RE-AWAIT route. Both routes run the SAME gate check over the
    SAME whole write_scope under ONE contract revision, which is the
    property _gate_check_write_scope's docstring (tools/bm_controller.py:
    910 to 938) states and which the re-await route falsified while it
    existed beside this one (AZ F-A1)."""
```

Body, in order:

1. `verdict, refused_path = self._gate_check_write_scope(project_id, unit)`
   (unchanged code, tools/bm_controller.py:902).
2. `_DEFERRED_CONTENTION` (287): return `(None, "DEFER")`. On the re-await
   route nothing is touched at all: the dispatch stays open and the fence
   stays held, which is what "deferred to a later wave" means.
3. `REFUSED-STATE` or `REFUSED-BREAKER`: `_begin_stopping(...)` exactly as
   today (1027 to 1032), return `(None, "DRAIN")`. `_begin_stopping`
   already parks the fences of CLAIMED, DISPATCHED and RESULT_IN units
   (1620 to 1624).
4. Any other non-ALLOWED verdict: the existing circuit-breaker block
   (1033 to 1062) verbatim, PLUS, when `open_dispatch` is not None, two
   calls before it so the in-flight dispatch is closed rather than left
   open over a path the founder just forbade:
   `record_verification(open_dispatch["dispatch_id"], None,
   "the live contract no longer authorises this unit's write scope: %s",
   False, actor)` and `_release_fence(unit["fence_uuid"], "parked",
   "the live contract no longer authorises this unit's write scope")`.
   Return `(None, "REFUSED")`.
5. ALLOWED, re-await route (`open_dispatch` is not None):
   a. **Stale stamp.** If `verdict["revision"] !=
      open_dispatch["contract_revision"]`, the answer this worker would
      give is already doomed by the staleness re-read at 1171. Close it
      now: `record_verification(..., "stale: contract moved from revision
      %s to %s between dispatch and re-await", False, actor)` (the same
      sentence 1174 to 1176 uses), `mark_unit_failed(...)`,
      `_release_fence(parked)`, return `(None, "REFUSED")`. The next wave
      opens a fresh dispatch under the current revision.
   b. **Fence check.** `record = self.store.get(unit["fence_uuid"])`. If
      it is None or its state is not "active", the fence was released
      while the dispatch was open (a crash residue). Do NOT re-claim and
      do NOT flip a DISPATCHED unit back to CLAIMED: record a rejected
      verification naming that condition, `mark_unit_failed`, return
      `(None, "REFUSED")`. The next wave takes the fresh route, which
      claims a new fence and opens attempt N+1, so at-most-once
      re-dispatch is preserved by `controller_dispatches.UNIQUE(unit_id,
      attempt)` (tools/bm_store.py:2515), not by trust.
   c. `brief = self._build_brief(unit, open_dispatch["attempt"])`;
      return the claimed dict built from the EXISTING `dispatch_id`,
      fence uuid and stamped revision. **No second dispatch row is ever
      opened on this route.**
6. ALLOWED, fresh route: the existing 1063 to 1080 verbatim (fence claim
   inside `try/except bs.OwnershipRefused` returning `(None, "DEFER")`,
   `claim_unit`, `_next_attempt`, `record_dispatch`, `_build_brief`).

### 6.3 `_resume_dispatched`, rebuilt

```python
def _resume_dispatched(self, project_id, run_id):
```
New body:

* If `not self._may_dispatch(state)` (section 7.1), return a result whose
  `stop_reason` is `FOUNDER_WAITING` and touch nothing. Defence in depth:
  after section 8 a delivered run cannot hold an open dispatch, but the
  guard costs one comparison.
* Take the first `(unit, dispatch)` from `_open_dispatch_units(run_id)`
  (section 13) whose dispatch status is `DISPATCHED`.
* `claimed, outcome = self._authorise_dispatch(project_id, run_id, unit,
  open_dispatch=dispatch)`.
* `claimed is None` maps to a stop reason: `DEFER` to `CONTENTION`,
  `DRAIN` to `TERMINAL`, `REFUSED` to `None` (a unit's retry count moved,
  which is progress, so the loop may continue and converge).
* Otherwise `_walk_to_executing`, `self.worker.run(claimed["brief"])`,
  `_handle_worker_result`, `_settle_after_wave` when anything was
  recorded, exactly as 888 to 897 does today.

AZ F-A1's four-command reproduction now ends with the worker called ONCE,
not twice, the fence PARKED rather than left active over `docs/x.md`, and
the run converging instead of re-asking. AZ's own control (C1b, a revoke
instead of a narrowing) is unchanged, because the contract check at
tools/bm_controller.py:432 to 446 still runs first.

### 6.4 FAILED_RECOVERABLE reaches VERIFYING, through a legal edge

SM I: `_RESULT_WALKABLE_STATES` (255) admits FAILED_RECOVERABLE because
FAILED_TERMINAL is legal from it, but neither `_walk_to_executing` (1340)
nor `_ensure_verifying` (1364) can move it, so a result is judged from a
run state that never reached VERIFYING, violating the invariant
tools/bm_controller.py:620 to 622 states.

The orchestrator's direction 8 offers two options. **This design picks
"route it through VERIFYING", and here is the justification against the
store law.**

`CONTROLLER_STATE_TRANSITIONS` already contains every edge needed:
`FAILED_RECOVERABLE` to `READY` (tools/bm_store.py:2561), `READY` to
`EXECUTING` (2546), `EXECUTING` to `VERIFYING` (2548). The engine ALREADY
owns and takes the first of those three: `_resume_result_in_and_orphans`
reverses FAILED_RECOVERABLE to READY unconditionally at the top of every
step (807 to 810). So this is not a new edge, a new permission or a
widening; it is the walk data catching up with what the engine already
does.

Change: one entry in `_RESULT_WALK_EDGES` (217 to 218):

```python
_RESULT_WALK_EDGES = {"CHECKPOINTED": "READY", "WAITING_HUMAN": "READY",
                      "FAILED_RECOVERABLE": "READY",
                      "READY": "EXECUTING", "EXECUTING": "VERIFYING"}
```

and one clause in `_walk_to_executing` (1355): FAILED_RECOVERABLE joins
CHECKPOINTED and WAITING_HUMAN in the detour through READY. The
import-time guard at 261 to 266 checks the new edge against the store's
own table automatically, so a future store change that removed it would
fail at import rather than mid-run.

`_RESULT_WALKABLE_STATES` is unchanged as a SET; what changes is that
FAILED_RECOVERABLE is now in it for the right reason. AZ's p16 matrix row
`start=FAILED_RECOVERABLE` moves from
`[('true','FAILED_RECOVERABLE'), ('verify.sh','FAILED_RECOVERABLE')]
final=FAILED_RECOVERABLE unit=DONE` to the same shape as the other three
rows: VERIFYING before the done_check, CHECKPOINTED at the verifier, and
`final=DELIVERABLE_READY`.

### 6.5 The outage stops the loop

`_handle_worker_result` (1095) returns None for both "pending" (1104) and
"unavailable" (1107 to 1115), so no caller can tell an async park from an
outage. Signature change:

```python
def _handle_worker_result(self, claimed, result, project_id, run_id):
    """Returns (outcome, reason) where reason is 'IN_FLIGHT' for a
    pending async park, 'OUTAGE' for a worker that reported itself
    unavailable, and None otherwise."""
```

Two callers, both updated: tools/bm_controller.py:510 and 889. This is
what lets `run_to_completion` park on an outage instead of re-asking the
same worker `max_steps` times (LV 6c: 15 of 15 steps, 15 worker asks).

---

## 7. The dispatch source law, and the empty-wave unwind

### 7.1 A run either may start work from where it stands, or it may not

New module data, derived exactly the way `_RESULT_WALKABLE_STATES` is
derived, so no state is hand-listed twice:

```python
_DISPATCH_WALK_EDGES = {"CHECKPOINTED": "READY", "WAITING_HUMAN": "READY",
                        "READY": "EXECUTING"}

def _walk_reaches(state, targets, edges):
    """Generalisation of _walk_reaches_rejectable (tools/bm_controller.py:
    229 to 245): does `edges` carry `state` into `targets` without a
    cycle. Same deliberate restriction to the engine's OWN edges rather
    than general reachability over CONTROLLER_STATE_TRANSITIONS, for the
    same documented reason: the store's table would also let PAUSED and
    DELIVERABLE_READY reach EXECUTING, and this engine takes neither."""

_DISPATCH_SOURCE_STATES = frozenset(
    s for s in bs.CONTROLLER_STATES
    if _walk_reaches(s, frozenset(("EXECUTING",)), _DISPATCH_WALK_EDGES))
```

`_walk_reaches_rejectable` (229) is rewritten as a one-line call to
`_walk_reaches`, keeping its docstring. The import-time guard (261 to
266) is extended to check `_DISPATCH_WALK_EDGES` against
`CONTROLLER_STATE_TRANSITIONS` too.

Resulting set: `READY, CHECKPOINTED, WAITING_HUMAN, EXECUTING` (EXECUTING
because a walk that is already at its target reaches it). Deliberately
OUT: `PAUSED` (the founder's edge, L1), `DELIVERABLE_READY` (a delivered
run is un-delivered by a founder's re-plan, which `upsert_units` performs
at tools/bm_store.py:13045 to 13056, never by this engine walking
backwards), `FAILED_RECOVERABLE` (reversed to READY by
`_resume_result_in_and_orphans` at 807 to 810 before any dispatch is
considered), `NEW`, `ORIENTING`, `PLANNING`, `VERIFYING`, `STOPPING`, and
the three terminal states.

```python
def _may_dispatch(self, state):
    return state in _DISPATCH_SOURCE_STATES
```

`step()` checks it once, immediately before `_walk_to_executing` at 486.
When it is False and units ARE selectable, `step()` returns through
`_finish(summary, project_id, "FOUNDER_WAITING", note)` with a note
naming the state and what the founder can do (resume, complete, or stop).
This is the structural closure of SM A, of SM B's second half (the
DELIVERABLE_READY re-walk churn AZ's p09 part b table shows) and of the
whole class those two belong to: `_walk_to_executing`'s silent no-op
(1355 to 1362) can no longer be followed by a dispatch.

### 7.2 The empty-wave unwind

LV 1: `step()` walks the run to EXECUTING at 486 BEFORE knowing whether
any unit will actually be claimed, and nothing walks it back. A wave where
every unit is gate-refused leaves the run in EXECUTING with nothing in
flight, and from EXECUTING neither WAITING_HUMAN nor DELIVERABLE_READY is
legal (tools/bm_store.py:2548), so `_deliver_or_hold`'s guard at 1585
refuses forever.

```python
def _unwind_empty_wave(self, project_id, run_id):
    """A wave that ended with NOTHING in flight has nothing left to
    verify, so leaving the run in EXECUTING is a false statement about
    it and a dead end: EXECUTING's only forward moves are VERIFYING,
    STOPPING, PAUSED and FAILED_RECOVERABLE (tools/bm_store.py:2548).
    Walk it back to a resting state along the SAME legal edges
    _settle_after_wave uses (EXECUTING to VERIFYING to CHECKPOINTED,
    tools/bm_store.py:2548 and 2550), from which both delivery and
    WAITING_HUMAN are legal (2552). Returns True when it moved the run.

    Passing THROUGH VERIFYING with nothing to verify does not violate
    the step-10 invariant _ensure_verifying states (tools/bm_controller.
    py:1364 to 1374): that invariant is 'a recorded result implies
    VERIFYING before verification', a one-way implication, not
    'VERIFYING implies a recorded result'."""
    if self._anything_in_flight(run_id):
        return False
    if self.store.get_run(project_id, raw=True)["state"] != "EXECUTING":
        return False
    # two set_run_state calls, VERIFYING then CHECKPOINTED
```

Exactly two call sites, both at the point where the wave is known to be
over:

* `step()`, immediately before `self._handle_no_ready_units(...)` at 477.
* `step()`, immediately before the no-dispatch return at 503 to 505.

Consequence for LV 1's own reproduction: wave 2 fails u1 through the
breaker, unwinds EXECUTING to CHECKPOINTED, and the following wave finds
`non_terminal` empty and delivers from CHECKPOINTED. `DELIVERABLE FOREVER
OUT OF REACH: True` becomes False, the wedge note is never written, and
because `_handle_no_ready_units` now always runs from READY, CHECKPOINTED
or WAITING_HUMAN, its WAITING_HUMAN move (1440 to 1443) is always legal,
so the summary and the store agree **in fact**, not merely because
`_finish` re-reads (that is SM E and LV 3 closed twice over).

---

## 8. The SKIPPED lifecycle, unreachable units, and the reversal

### 8.1 SKIPPED closes at the source

`upsert_units` marks a dropped unit SKIPPED at tools/bm_store.py:12999 to
13007 and leaves everything else about it alive: its dispatch row stays
DISPATCHED, its fence stays active, and `receive_result` will happily
accept the late answer and mark the dead unit DONE (LV 4). `check_timeouts`
never times it out either, because it filters on unit status at
tools/bm_controller.py:752.

**Store change (tools/bm_store.py, inside `upsert_units`' existing
transaction, right after the SKIPPED UPDATE at 13006):**

```sql
UPDATE controller_dispatches SET status='CANCELLED'
 WHERE unit_id=? AND status IN ('DISPATCHED','RESULT_IN')
```

`CANCELLED` is a new terminal dispatch status. It needs NO schema change:
`controller_dispatches.status` is a bare `TEXT NOT NULL` with no CHECK
(tools/bm_store.py:2507) and there is no closed-set constant for it
today. This design adds one, for the same discipline every other enum in
the file has:

```python
CONTROLLER_DISPATCH_STATUSES = ("DISPATCHED", "RESULT_IN", "VERIFIED",
                                "REJECTED", "CANCELLED")
```

`record_result` (13175 to 13209) gains one branch inside its existing
`row["status"] != "DISPATCHED"` refusal (13192 to 13197): when the status
is CANCELLED the refusal reason is `'dispatch-cancelled'` with its own
sentence ("a re-plan dropped unit X from the unit graph, so this dispatch
was cancelled; the result cannot be recorded against it"), because
"a result was already recorded for it (duplicate result)" would be a
false statement. `main()` catches every `BMStoreError` at
tools/bm_controller.py:2409, so this is exit 1 with a clear line, never a
traceback.

`upsert_units` also RETURNS what it orphaned, additively:

```python
return {"count": len(units),
        "skipped": [unit_id, ...],
        "cancelled_dispatches": [dispatch_id, ...],
        "orphaned_fences": [(unit_id, fence_uuid), ...]}
```

`cmd_plan` reads only `result["count"]` (tools/bm_controller.py:2089 and
2091), so the extra keys break nothing.

**Why the fence is released by the ENGINE and not by `upsert_units`:**
releasing a fence means `Store.transition` (tools/bm_store.py:10177),
which opens its own `self._transaction()` (6018), and SQLite refuses a
nested BEGIN, which is the same reason `_set_run_state_locked` exists
beside `set_run_state` (12744 to 12749). So `upsert_units` reports the
orphans and `ControllerEngine.plan` parks them immediately after the call
(section 8.2). The crash window between the two calls is closed by
extending the orphan-fence resume branch (section 8.6).

### 8.2 `ControllerEngine.plan` after this change

```python
def plan(self, project_id, run_id, units):
```
1. `run = self._run_or_refuse(project_id)`; `self._refuse_if_paused(run,
   "plan")` (section 4.2).
2. The existing NEW to ORIENTING to PLANNING walk (386 to 393), unchanged.
3. `result = self.store.upsert_units(run_id, units, self.actor)`.
4. For each `(unit_id, fence_uuid)` in `result["orphaned_fences"]`:
   `self._release_fence(fence_uuid, "parked", "a re-plan dropped unit %s
   from the unit graph")`. `_release_fence` (1295 to 1328) is already
   idempotent on a fence that is not active.
5. `self._reconcile_lane_blocks(project_id, run_id)` (section 8.4), so a
   re-plan's effect on BLOCKED units is visible immediately rather than on
   the next `step`.
6. Return `result`.

### 8.3 A SKIPPED unit that a later plan re-adds is REVIVED

`upsert_units` skips a unit whose definition hash is unchanged
(tools/bm_store.py:12948 to 12949, "byte-identical redefinition: reuse,
untouched"). LV 2 proved that this makes a founder's drop IRREVERSIBLE:
the re-plan the escalation itself tells the founder to make does not
bring the unit back.

Change, at 12948:

```python
if (prior is not None and prior["definition_hash"] == hashes[uid]
        and prior["status"] != "SKIPPED"):
    continue
```

and a new branch for the SKIPPED case that writes ONLY the status,
recomputed by `_status_for(uid, deps)` (12930 to 12941), leaving
`definition_hash` (genuinely unchanged), `retry_count` (those attempts
really happened) and `created_at` alone.

Justification: the reuse-untouched rule exists to protect COMPLETED work
across a workflow-version change (fault 8, the docstring at 12823 to
12837). SKIPPED is not completed work and is not a fact about the
definition; it is the record of a founder dropping the unit. Re-adding
the unit is the founder undoing exactly that, and the definition hash
being identical is what makes it the SAME unit rather than an argument
for ignoring the request.

### 8.4 BLOCKED becomes a materialised view of the lane gate

The round-3 escalation (`_block_unreachable_units`, 1467 to 1554) writes
BLOCKED through `block_lane_units` (1552 to 1553) and nothing anywhere in
production ever calls `unblock_lane_units`. SM F and LV 2 both land on
that, and LV's p12 showed a healthy unit permanently lost as collateral.

New law: **a unit is BLOCKED exactly when its lane holds an open founder
step.** That is what `block_lane_units`' own docstring says it is for
(tools/bm_store.py:13293 to 13297) and it is what `select_ready_units`
already enforces independently through its blocked-lane query
(13082 to 13086). Making BLOCKED a view of that fact rather than an
independent fact removes the one-way door.

```python
def _reconcile_lane_blocks(self, project_id, run_id, units=None):
    """BLOCKED means 'this lane holds an open founder step', and nothing
    else (L4). Reconciles BOTH directions once per wave: a lane that
    gained a step gets its PENDING/READY units BLOCKED; a lane whose
    last step was resolved gets its BLOCKED units returned to
    PENDING/READY by dependency satisfaction. This is the FIRST
    production caller of Store.unblock_lane_units (tools/bm_store.py:
    13314), whose absence is what made every BLOCKED status in round 3
    permanent."""
```
Body: read the open steps' lanes (the same read `_handle_no_ready_units`
makes at 1435 to 1436), group the run's units by lane, and call
`block_lane_units` only for a gated lane that actually holds a
PENDING/READY unit and `unblock_lane_units` only for an ungated lane that
actually holds a BLOCKED one, so a quiet wave writes no attribution rows.

Call sites: `step()` immediately before `select_ready_units` at 475 (so a
lane ungated a moment ago is selectable in the SAME wave), `plan()` step 5
above, and `_handle_no_ready_units` after an escalation.

### 8.5 The unreachable-unit escalation, recomputed every wave

`_block_unreachable_units` (1467 to 1554) is replaced by two functions:

```python
def _unreachable_units(self, units):
    """unit_id -> (the dependency it waits on, the DEAD unit at the end
    of that chain), for every PENDING, READY or BLOCKED unit whose
    dependency chain ends in a unit that is FAILED or SKIPPED
    (_DEAD_DEPENDENCY_STATUSES, tools/bm_controller.py:300). PURE: no
    store write, no status write, recomputed from the graph every time
    it is asked (L4). The fixed-point walk at 1506 to 1523 moves here
    unchanged except for admitting BLOCKED units as candidates."""

def _escalate_unreachable_units(self, project_id, run_id, units,
                                unreachable, gated_lanes):
    """Queue ONE founder step per unreachable unit whose lane is not
    ALREADY gated, and add that lane to `gated_lanes` so a second unit
    in the same lane does not queue a second step. Returns True when it
    queued anything. Writes NO unit status: section 8.4's reconcile is
    what marks the newly gated lane BLOCKED."""
```

The idempotency marker is **an open founder step in the unit's own lane**,
which is state-derived, needs no new column, and self-heals in both
directions:

* first wave: unreachable, lane ungated, so one step is queued, the lane
  becomes gated, the reconcile marks the lane BLOCKED. The existing tests
  that assert `BLOCKED` (tools/test_bm_controller.py:1339, 1385, 1858,
  1903) still pass, because the lane is genuinely gated.
* every later wave: the lane is gated, so nothing is queued. No spam,
  whatever drives `step()`.
* founder resolves the step but does not repair: the lane ungates, the
  reconcile unblocks the lane, the unit is unreachable again and its lane
  is ungated again, so ONE fresh step is queued. That is not spam, it is
  the condition still being true, restated once per founder action. LV 2's
  "WAITING_HUMAN with ZERO open founder steps and nothing a founder can
  resolve" is exactly this hole, and this closes it.
* founder repairs and resolves: the lane ungates, the reconcile unblocks
  the lane (including LV p12's collateral u3), the unit is no longer
  unreachable, nothing is queued, and `select_ready_units` returns it.
  LV 2's `RUN DELIVERED: False` becomes True, matching the pre-round-3
  control p6 produced, WITHOUT reintroducing the spin that control had.
* founder repairs but does not resolve: the lane stays gated and the run
  rests in WAITING_HUMAN with an open step whose text says to resolve it.
  Honest, and the step's own wording (below) asks for exactly that.

The step's text keeps round 3's two-sentence shape (1545 to 1551),
including the dead unit's STATUS and the different instruction for FAILED
against SKIPPED (1537 to 1544), and gains one clause: "and then resolve
this step; the controller will not start unit X while this step is open."

**What re-plan clears, and what it never clears** (the orchestrator's
direction 4, answered precisely):

| Written by the escalation | Cleared by | Never cleared by the engine |
|---|---|---|
| the BLOCKED statuses of the gated lane | `_reconcile_lane_blocks` on the first wave after the lane's last step is resolved, and by `plan()` step 5 | |
| the unreachability itself | nothing: it is not stored. Reviving the dead unit (section 8.3) removes it by recomputation | |
| the open founder step | | **the engine, ever.** `resolve_human_step` (tools/bm_store.py:12390) records that the required action HAPPENED; the engine writing it would put a claim about a human into the audit trail. The step is founder-owned and stays open until the founder resolves it. |
| a SKIPPED unit's status | a re-plan that re-adds it (section 8.3) | a re-plan that does not name it |
| a FAILED unit's retry_count | | nothing: the attempts really happened |
| a DONE unit's checkpoint_ref | the existing fault-3 cascade (tools/bm_store.py:13009 to 13039) | |

This is a deliberate, named refinement of direction 4's wording ("a
re-plan CLEARS the founder steps the earlier escalation wrote"): the
statuses are cleared, the steps are not, because auto-resolving a human
step would require either provenance columns on `autonomy_human_steps`
(a schema-16 migration this design otherwise does not need) or the engine
asserting a human acted. Leaving the step open is also the conservative
direction: it keeps the lane gated until a human looks.

`_is_founder_waiting` gains a third arm and one argument:

```python
def _is_founder_waiting(self, unit, gated_lanes, unreachable):
    if unit["status"] == "BLOCKED":
        return True
    if unit["unit_id"] in unreachable:
        return True
    return (unit["status"] in ("PENDING", "READY")
            and unit["lane"] in gated_lanes)
```
The in-flight half of the predicate (its docstring at 1457 to 1461, which
STOOD) is preserved: in-flight units are excluded before this is ever
called, by the `IN_FLIGHT` early return in section 8.6.

**SM observation 5 is recorded, not changed.** `list_human_steps` is read
project wide at 1435, so a step left by an earlier run gates the same
lane in a new one. That is the store's own project-scoped human-step
model (`autonomy_human_steps` has no run_id, tools/bm_store.py:12377 to
12384). Narrowing it needs a schema column; the behaviour is recoverable
by resolving the step, and it is disclosed in docs/KNOWN-LIMITS.md.

### 8.6 `_handle_no_ready_units`, rewritten

```python
def _handle_no_ready_units(self, project_id, run_id, summary):
```
The `escalate_unreachable` one-shot re-entry parameter (1404, 1447 to
1450) is GONE: nothing re-enters, because the escalation writes no status
this function then has to re-judge.

Order:
1. `self._unwind_empty_wave(project_id, run_id)` (idempotent; returns
   False unless the run is EXECUTING with nothing in flight).
2. `open_units = self._open_dispatch_units(run_id)`. If any, set
   `IN_FLIGHT` and return. **This is a new early return** and it is what
   makes LV's "WAITING_HUMAN WITH AN OPEN DISPATCH: True" impossible: the
   dispatch rows are consulted before the unit statuses, so a SKIPPED
   unit filtered out of `non_terminal` at 1431 can no longer hide one.
3. `non_terminal` exactly as 1430 to 1431. If empty, `_deliver_or_hold`
   and return.
4. `unreachable = self._unreachable_units(units)`;
   `gated_lanes` as 1435 to 1436.
5. `if self._escalate_unreachable_units(...)`: re-read the units and the
   gated lanes and call `_reconcile_lane_blocks`.
6. If every unit in `non_terminal` is founder-waiting: move the run to
   WAITING_HUMAN when it is READY or CHECKPOINTED (1440 to 1443,
   unchanged, and now always satisfied thanks to step 1), then
   `_set_reason(summary, "FOUNDER_WAITING", "only founder-gated lanes
   remain")`. `_finish` writes the state from the store.
7. Otherwise `_set_reason(summary, "NOTHING_SELECTABLE",
   _NOTE_NOTHING_SELECTABLE)`.

`_resume_result_in_and_orphans` (792) gains two branches, both inside the
loop it already runs over the unit list:

* a SKIPPED unit whose fence is still ACTIVE is parked, with the note "a
  re-plan dropped this unit; releasing the fence it still held". This
  closes the crash window between `upsert_units` and `plan()`'s release
  (section 8.1).
* a CLAIMED unit with NO dispatch row at all is the crash window between
  `claim_unit` (tools/bm_store.py:13107) and `record_dispatch` (13129),
  which LV 7 reproduced as a permanently stranded unit holding an active
  fence with no founder step. Park its fence and call the new
  `Store.release_claimed_unit` (section 15.2), which returns it to
  PENDING or READY by dependency satisfaction WITHOUT burning a retry the
  unit never earned.

---

## 9. Spin closure

### 9.1 One stop predicate, two drivers

```python
def _loop_stops(summary):
    """The ONE predicate both loop drivers use (L3). A loop continues
    only while a wave reported no reason to stop."""
    return (summary.get("stop_reason") is not None
            or summary["state"] in
            ControllerEngine._RUN_TO_COMPLETION_STOP_STATES)
```

The second clause is belt and braces, not the primary test:
`_RUN_TO_COMPLETION_STOP_STATES` (535 to 536) is KEPT exactly as it is,
so a stop reason this design forgot to set somewhere cannot produce a
spin on a delivered, waiting or terminal run.

`run_to_completion` (538 to 572) loses its note-string stop (564 to 571)
and its `state_before` comparison (558 to 559) and becomes: call `step`,
append, `if _loop_stops(summary): break`. `_drive_until_parked` (1907 to
1943) loses its three hand-written break conditions (1935 to 1942) and
uses the same predicate. Both drivers then stop at the SAME point, which
removes the divergence LV 6a's own corollary names (the round-3 park stop
being unreachable from the shipped CLI because `_drive_until_parked`
already stopped earlier on a broader condition). `_drive_until_parked`'s
docstring keeps its reproduced reasoning; the reason it names is now
called `IN_FLIGHT`.

Every reproduced spin closes because each one now sets a reason:

| Spin | Reason set at | Steps before | after |
|---|---|---|---|
| LV 6a / FIX residual 4, soft spend stop | `step`, 480 to 484, `SPEND_STOP` | 12 of 12 | 1 |
| LV 6b, failing done-definition | `_deliver_or_hold`, `FOUNDER_WAITING` | 15 of 15 | 1 |
| LV 6c / SM J, provider outage and the ordinary async park | `_handle_worker_result`, `OUTAGE` / `IN_FLIGHT` | 12 to 15 of max | 1 |
| LV 5 A and B, false park on contention | `_authorise_dispatch`, `CONTENTION` | 2, with a false note | 1, with an honest note |
| LV 1, the EXECUTING wedge | section 7.2 removes the wedge itself | 20 of 20 | delivers |

### 9.2 `_deliver_or_hold`, rewritten

The legality test at 1585 is replaced by derived data, in the same style
as sections 6.4 and 7.1:

```python
_DELIVERY_WALK_EDGES = {"EXECUTING": "VERIFYING",
                        "VERIFYING": "CHECKPOINTED",
                        "WAITING_HUMAN": "READY"}
_DELIVERY_TARGETS = frozenset(("READY", "CHECKPOINTED"))
_DELIVERY_SOURCE_STATES = frozenset(
    s for s in bs.CONTROLLER_STATES
    if _walk_reaches(s, _DELIVERY_TARGETS, _DELIVERY_WALK_EDGES))
```
Every edge is checked against `CONTROLLER_STATE_TRANSITIONS` by the
import-time guard (2548, 2550, 2554). Resulting set: `READY,
CHECKPOINTED, VERIFYING, EXECUTING, WAITING_HUMAN`. PAUSED and
FAILED_RECOVERABLE are deliberately absent, which is SM B closed by
construction rather than by a legality accident.

New order inside the method:

1. `cur == "DELIVERABLE_READY"`: `_set_reason(summary, "DELIVERED",
   "deliverable ready")` and return, writing NOTHING. This closes the
   second half of SM B's table: today the run is walked back to READY and
   forward to DELIVERABLE_READY again on every later step, re-running the
   whole done_definition and writing two extra state rows each time.
2. `cur not in _DELIVERY_SOURCE_STATES`: `_set_reason(summary,
   "FOUNDER_WAITING", "the done-definition was not run: the run is %s,
   which only a founder can move (resume, complete or stop it)")` and
   return. After section 7.2 this is unreachable from `step()`; it is
   defence in depth.
3. The done_definition run (1567 to 1573), unchanged. On failure:
   `_set_reason(summary, "FOUNDER_WAITING", "final done-definition check
   failed (exit %d); the run stays in place for inspection")` and return.
   Bounded to **once per park decision** because the loop stops on the
   reason: LV 6b's 15 executions in one call become 1.
4. `record_checkpoint(deliverable-ready)` (1574 to 1576), unchanged.
5. Walk `cur` to READY or CHECKPOINTED along `_DELIVERY_WALK_EDGES`.
6. `set_run_state(DELIVERABLE_READY)`, the `founder_gated` block (1598 to
   1604) unchanged, `_set_reason(summary, "DELIVERED", "deliverable
   ready")`.

`summary["state"]` is NOT written here any more (1597 is deleted);
`_finish` reads it back from the store.

### 9.3 Why FOUNDER_WAITING is the honest reason for a failing done-definition

The enum the orchestrator fixed has no `DONE_DEFINITION_FAILED`, and
adding one would be re-deciding rather than refining. Of the eight, only
FOUNDER_WAITING is true: every unit is DONE, no autonomous progress is
possible, and the founder's own check is what fails, so a human must look.
`NOTHING_SELECTABLE` would be a lie (nothing is selectable BECAUSE
everything is done). The note carries the exit code and the word
"done-definition", so the founder never has to infer it from the reason.

---

## 10. `_handle_late_result` and `_reject`

### 10.1 Spend is recorded once, before the branch

`receive_result` records the result at 610, reads the state at 613 and
returns through `_handle_late_result` at 614 to 616; the spend block lives
at 636 to 651, AFTER that return (SM C, a REGRESSION against the
pre-round-3 tree, reproduced four shipped commands deep).

Change: move the spend block to immediately after `record_result`, before
the walkability branch. The live-contract guard (646 to 648) moves with
it unchanged, so a revoked contract still skips bookkeeping rather than
crashing, which is what its own comment at 639 to 645 promises. Every
result path, late or not, held or not, then charges the meter exactly
once, under exactly one rule. SM C's `spend tokens 0 -> 0` becomes
`0 -> 9000` and the breaker stops under-counting.

### 10.2 `receive_result`, in order, after this design

1. `run = self._run_or_refuse(project_id)`.
2. `dispatch = self.store.get_dispatch(dispatch_id, raw=True)`
   (section 15.2). Refuse `'not-found'` when None; refuse
   `'foreign-dispatch'` when `dispatch["run_id"] != run["run_id"]`
   (section 12.2).
3. `unit = self._unit_row(run["run_id"], dispatch["unit_id"])`; refuse
   `'not-found'` when None. After step 2 this is unreachable; it is the
   defensive floor under the `TypeError` SM K and AZ F-A3 both landed on.
4. If `self._is_paused(run)`: `record_result`, record spend, return
   `"held"` (section 4.3).
5. `record_result` (unchanged, 610).
6. Record spend (section 10.1).
7. `state = get_run(...)["state"]`; when it is outside
   `_RESULT_WALKABLE_STATES`, `_handle_late_result(project_id, run_id,
   dispatch_id, unit, state)` (note: the UNIT ROW is passed in, not
   re-fetched at 690).
8. Otherwise the walk (634 to 635), `_verify_and_finish`,
   `_settle_after_wave`, unchanged.

### 10.3 `_handle_late_result`, rewritten

Round 3 puts the founder step and the lane block behind `if
outcome["status"] != "FAILED"` (697) and routes the only other
founder-visible record through `_record_interruption` (1279), which
returns None whenever the contract is not live. SM D reproduced a real
result discarded with `founder (open human steps, interruptions):
before=(0, 0) after=(0, 0)`.

New order, and every step is unconditional:

1. `record_verification(dispatch_id, None, reason, False, actor)` (694 to
   695, unchanged).
2. `outcome = mark_unit_failed(unit_id, actor, reason)` (696, unchanged).
3. **Always** `queue_human_step(project_id, "", unit["lane"], text, "",
   [], session, actor)`. The text names the unit, the run state, and
   which of the two the breaker did: re-queued for one more attempt, or
   exhausted (`outcome["status"] == "FAILED"`), mirroring what `_reject`
   tells the founder at the ceiling (1260 to 1264). `queue_human_step`
   needs only SOME contract in any state (tools/bm_store.py:12348 to
   12351), and SM surface 4 proved a contract always exists once a run
   does, so nothing can silence this.
4. The rollback and `_warn_dirty_write_scope` (707 to 712), unchanged
   except for the lane (section 10.4).
5. `_release_fence(parked)` (713 to 714), unchanged.
6. `_record_interruption` (715 to 720), unchanged, and now genuinely
   best-effort: when it is skipped because the contract is not live, step
   3 has already told the founder.

**`block_lane_units` and the BLOCKED status are removed from this path**
(706). The founder step in the unit's own lane is the whole mechanism:
`select_ready_units`' blocked-lane query (tools/bm_store.py:13082 to
13086) makes the lane unselectable on its own, and section 8.4's
reconcile marks its units BLOCKED as a view of that step, reversibly.
That is the pairing law the orchestrator's direction 9 names, with the
half that had no reverse gear taken out.

Nothing here can re-dispatch the unit anyway: every state that routes to
this handler (`NEW, ORIENTING, PLANNING, DELIVERABLE_READY, COMPLETE,
STOPPING, STOPPED, FAILED_TERMINAL`; PAUSED is now held at step 4) is
outside `_DISPATCH_SOURCE_STATES`, so section 7.1 refuses the dispatch
structurally. That is REFUTATION-2's reproduction 2 closed twice.

### 10.4 The dirty-scope warning goes to the unit's own lane

`_warn_dirty_write_scope` (1268 to 1277) writes into the hard-coded lane
`"default"` (1273), so a dirty rollback for a unit in lane `build` gates
lane `default` project wide through `select_ready_units` (SM observation
4). New signature:

```python
def _warn_dirty_write_scope(self, project_id, unit_id, exit_code, lane):
```
Both callers pass the unit's own lane: `_handle_late_result` has the unit
row; `_reject` (1241) reads it through `self._unit_row(run_id, unit_id)`,
which it can, since it already has `run_id`. One wording, still in one
place, which was the point of extracting the helper in round 3.

### 10.5 `_reject`'s survive branch

SM H: on the `else` branch at 1252 to 1258 the run SURVIVES and the unit
is left READY and unblocked, so a surviving run can re-dispatch a unit
whose rollback just failed. Two things now stop that, and neither
reorders the consequence chain that STOOD:

* section 10.4 puts the dirty-scope founder step in the unit's OWN lane,
  which makes that lane unselectable through `select_ready_units` until a
  founder resolves it, and section 8.4's reconcile marks the lane's units
  BLOCKED as a view of it.
* the branch is only reachable when a concurrent writer moved the run
  out from under a caller that had already walked it, and every such
  state is either terminal or outside `_DISPATCH_SOURCE_STATES`.

The order at 1240 to 1251 (warning, fence park, then the guarded move) is
NOT touched.

### 10.6 The staleness rejection also rolls back

SM observation 3: `_verify_and_finish`'s stale branch (1171 to 1184)
records the verification, fails the unit and parks the fence, but never
runs the rollback and never warns about a dirty scope, unlike every other
rejection path. It is a one-line inconsistency in a method this round is
already editing, and leaving it means a founder whose contract moved
mid-unit gets no warning about a half-written scope. Change: after
`mark_unit_failed` at 1178 and before `_release_fence` at 1182, run the
rollback and `_warn_dirty_write_scope` exactly as `_reject` does at 1237
to 1242. The fence park and the return value are unchanged.

---

## 11. `check_timeouts`

### 11.1 What changes

* The PAUSED guard: return `[]` (section 4.2).
* The unit iteration at 751 to 760 is driven by
  `self._open_dispatch_units(run["run_id"])` (section 13) instead of the
  unit-status filter at 752. A dispatch is open or it is not; that is a
  dispatch-row fact. This also means a unit whose STATUS drifted (the
  SKIPPED case LV's p14 case B found) is no longer invisible to the
  timeout, and a CANCELLED dispatch (section 8.1) is correctly invisible.
* Nothing else. The walk (767 to 775), the late-result route (768 to
  770), the `_reject` call (779) and the single `_settle_after_wave` at
  786 to 787 are untouched: 28 of 28 matrix cells held.

### 11.2 The race is bounded, not closed

SM L: a real result landing between the dispatch read (754) and
`record_result` (764) makes `record_result` refuse 'already-resulted',
which propagates out and skips the settle at 786. The refuter also proved
it self heals on the very next `step`, through the RESULT_IN resume
branch. This design wraps the `record_result` call in
`try/except bs.OwnershipRefused` and `continue`s to the next unit, so one
raced unit no longer costs the other units in the same call their settle.
It does not attempt a transaction across the two calls: that would mean a
store method taking the engine's whole loop, which is a bigger change than
the finding earns.

---

## 12. Refusals instead of tracebacks

### 12.1 The state read and the handler body (SM G), bounded and stated

`receive_result` reads the run state at 613 and branches at 614. A
concurrent writer moving the run between the two puts the call on the
wrong side. This design does NOT close it, and says so plainly rather
than implying otherwise: closing it needs the whole result path inside one
store transaction, which means a Store method that runs a CheckRunner
subprocess, which the harness seam exists to forbid
(tools/bm_controller.py:44 to 52).

What the design DOES do is remove both consequences the refuter measured:

* the first probe row (a STOPPED run gaining a READY unit with no pairing
  and no founder step) is closed by section 10.3's unconditional founder
  step and by section 7.1 refusing the dispatch;
* the second row (a run wedged in EXECUTING with its only unit BLOCKED)
  is closed by section 7.2's unwind and section 8.4's reconcile.

So the race survives and its damage does not. This goes in
docs/KNOWN-LIMITS.md in those words.

### 12.2 A dispatch id that belongs to another run or another project

SM K and AZ F-A3 are the same defect from two angles: `receive_result`
takes `project_id` and `dispatch_id` as independent arguments and never
checks that the dispatch belongs to the named project's current run, so
`_unit_row` (1642) returns None and 656 raises an uncaught `TypeError`
that `main()` (2409 to 2420) does not catch, AFTER `record_result` and
the spend have already committed against the wrong contract.

Closed by section 10.2 steps 2 and 3, using the new
`Store.get_dispatch(dispatch_id, raw=False)` (section 15.2). The dispatch
row already carries `run_id` and `project_id`
(tools/bm_store.py:2502 to 2503), so this is a read, not a schema change.
Both of AZ's reproductions become exit 1 with a named refusal, and
neither records a result, moves a run, nor charges a meter.

### 12.3 A unit id another project already used

AZ F-A4: `controller_units.unit_id` is a GLOBAL primary key
(tools/bm_store.py:2473), so `bm-controller plan --project p2` with a unit
called `u1` raises a raw `sqlite3.IntegrityError` out of the INSERT at
12974.

The underlying single-namespace limit is a composite-key table rebuild,
which is NOT an additive change and is out of this round's mandate. The
SYMPTOM is closed here: wrap the INSERT in
`try/except sqlite3.IntegrityError` and raise
`OwnershipRefused('unit-id-taken', ...)` naming the colliding id, the
project that already holds it, and the fix (prefix unit ids per project).
The transaction already rolls back cleanly, which AZ verified (E2.3), so
the run is left with zero units in PLANNING and a re-plan with fresh ids
recovers. The namespace limit itself is disclosed in
docs/KNOWN-LIMITS.md.

### 12.4 A non-string write_scope entry

AZ F-A8: `upsert_units` canonicalises every write_scope entry at 12897 to
12899, and `canonicalize_path` reaches `_to_posix`'s `(p or "").strip()`
(451), so a JSON number, array or object raises an uncaught
`AttributeError` through the shipped `plan` command. The store already
owns the correct behaviour for exactly this class on the fence side:
`_coerce_path_entry` (690 to 727), which exists because "a claim() that
silently dropped a non-str entry still returned a Record reporting
success".

Change: `canonicalize_path(self.root, _coerce_path_entry(p), cwd=None)` at
12897. Exit 1 with 'bad-path' naming the entry and its type, never a
traceback. The NUL-byte row AZ noted in the same matrix stays accepted and
is disclosed in docs/KNOWN-LIMITS.md; refusing it is a separate policy
decision about path bytes that this round does not take.

---

## 13. One definition of "in flight"

LV 7: `_IN_FLIGHT_UNIT_STATUSES` (292 to 293) counts CLAIMED and is read
at 1498, while `_anything_in_flight` (574 to 585) reads DISPATCH rows and
does not, so a unit stranded in the `claim_unit`-to-`record_dispatch`
crash window is simultaneously "in flight" (the escalation abstains) and
"not in flight" (the loop parks), with an active fence and no founder
step naming it.

Resolution: **there is one predicate, and it reads dispatch rows.**

```python
def _open_dispatch_units(self, run_id):
    """[(unit_row, dispatch_row), ...] for every dispatch of this run
    whose status is DISPATCHED or RESULT_IN. The ONE definition of 'work
    is in flight' in this file (LV 7: two helpers added in one round
    disagreed about CLAIMED). A unit's STATUS is not consulted, because
    a status can drift (a rejected late result leaves RESULT_IN behind a
    closed dispatch) while a dispatch row cannot: it is the exactly-once
    spine (tools/bm_store.py:2453 to 2456)."""

def _anything_in_flight(self, run_id):
    return bool(self._open_dispatch_units(run_id))
```

`_IN_FLIGHT_UNIT_STATUSES` is DELETED. CLAIMED does not need to be in any
in-flight set, because section 8.6's new resume branch resolves a CLAIMED
unit with no dispatch row BEFORE anything else in the wave reads it: the
fence is parked and the unit is returned to PENDING or READY through
`Store.release_claimed_unit`. LV 7's probe ends with the fence released,
the unit selectable again and no retry burned, instead of
`fence STILL: active` and `open founder steps: 0`.

Consumers updated: 574 (the definition), 1497 to 1500 (the escalation's
in-flight abstention becomes section 8.6 step 2's early return), 752
(check_timeouts, section 11.1), and 2189 to 2195 (`cmd_status`'s open
dispatch display, which already reads dispatch rows and only needs the
CANCELLED status to be excluded, which it is).

---

## 14. The command line

Thin, per the file's own law at tools/bm_controller.py:1672 to 1709. Four
small changes, no new subcommand:

* `cmd_step` (2018 to 2044): print `reason: <stop_reason>` after the note
  when it is not None. `--json` already prints the whole summary, so the
  new field appears there for free.
* `_report_trace` (1884 to 1904): print the last summary's reason on its
  own line.
* `cmd_record_result` (2104 to 2150): a third branch at 2145 to 2149 for
  the new `"held"` outcome: "result recorded and held: the run is PAUSED,
  so it will be verified after bm-controller resume".
* `cmd_plan` (2055 to 2092): report `result["skipped"]` and
  `result["cancelled_dispatches"]` counts when non-zero, so a founder who
  drops a unit sees that its open dispatch was cancelled.

`cmd_start`, `cmd_status`, `cmd_stop`, `cmd_resume` and `cmd_complete` are
unchanged. `check_timeouts` stays unwired to a subcommand, for the reason
the CLI section's own note gives at tools/bm_controller.py:1695 to 1698.

---

## 15. Inventory

### 15.1 tools/bm_controller.py

| Symbol | Change | Signature |
|---|---|---|
| `STOP_REASONS` | NEW | module tuple, section 3.1 |
| `_NOTE_CONTENTION` etc (6 constants) | NEW | module strings, section 3.4 |
| `_NO_PROGRESS_NOTES` | DELETED | its consumer at 566 is replaced by `stop_reason` |
| `_IN_FLIGHT_UNIT_STATUSES` | DELETED | replaced by `_open_dispatch_units` |
| `_RESULT_WALK_EDGES` | CHANGED | one entry added, section 6.4 |
| `_DISPATCH_WALK_EDGES`, `_DISPATCH_SOURCE_STATES` | NEW | section 7.1 |
| `_DELIVERY_WALK_EDGES`, `_DELIVERY_TARGETS`, `_DELIVERY_SOURCE_STATES` | NEW | section 9.2 |
| `_walk_reaches` | NEW | `(state, targets, edges) -> bool` |
| `_walk_reaches_rejectable` | CHANGED | one-line call to `_walk_reaches` |
| the import-time guard (261 to 266) | CHANGED | now checks all three edge maps |
| `_loop_stops` | NEW | `(summary) -> bool` |
| `_finish` | NEW | `(self, summary, project_id, stop_reason=None, note=None)` |
| `_set_reason` | NEW | `(self, summary, stop_reason, note)` |
| `_run_or_refuse` | NEW | `(self, project_id) -> run row` |
| `_is_paused` | NEW | `(self, run) -> bool` |
| `_refuse_if_paused` | NEW | `(self, run, action)` raises |
| `_open_dispatch_units` | NEW | `(self, run_id) -> [(unit, dispatch)]` |
| `_anything_in_flight` | CHANGED | delegates to the above |
| `_may_dispatch` | NEW | `(self, state) -> bool` |
| `_unwind_empty_wave` | NEW | `(self, project_id, run_id) -> bool` |
| `_authorise_dispatch` | NEW | `(self, project_id, run_id, unit, open_dispatch=None) -> (claimed, outcome)` |
| `_claim_and_dispatch` | DELETED | its body is `_authorise_dispatch`'s fresh route |
| `_resume_dispatched` | REWRITTEN | `(self, project_id, run_id)` |
| `_handle_worker_result` | CHANGED | returns `(outcome, reason)` |
| `_reconcile_lane_blocks` | NEW | `(self, project_id, run_id, units=None)` |
| `_unreachable_units` | NEW | `(self, units) -> {unit_id: (dep, dead)}` |
| `_escalate_unreachable_units` | NEW | `(self, project_id, run_id, units, unreachable, gated_lanes) -> bool` |
| `_block_unreachable_units` | DELETED | split into the two above |
| `_is_founder_waiting` | CHANGED | `(self, unit, gated_lanes, unreachable)` |
| `_handle_no_ready_units` | REWRITTEN | `(self, project_id, run_id, summary)` |
| `_deliver_or_hold` | REWRITTEN | same signature |
| `_warn_dirty_write_scope` | CHANGED | `(self, project_id, unit_id, exit_code, lane)` |
| `_verify_and_finish` | CHANGED | stale branch rolls back, section 10.6 |
| `_handle_late_result` | CHANGED | `(self, project_id, run_id, dispatch_id, unit, state)`, the unit ROW is passed in |
| `receive_result` | CHANGED | same signature, returns `unit_id`, `"rejected"` or `"held"` |
| `check_timeouts` | CHANGED | same signature |
| `plan` | CHANGED | same signature, richer return |
| `step` | CHANGED | same signature, one exit funnel |
| `run_to_completion`, `_drive_until_parked` | CHANGED | same signatures |
| `_walk_to_executing` | CHANGED | FAILED_RECOVERABLE joins the detour |
| `cmd_step`, `cmd_plan`, `cmd_record_result`, `_report_trace` | CHANGED | section 14 |

### 15.2 tools/bm_store.py

| Symbol | Change | Signature |
|---|---|---|
| `import fnmatch` | NEW | joins the block at 59 to 74 |
| `path_within_allowed` | CHANGED | same signature, glob branch only, section 5.1 |
| `CONTROLLER_DISPATCH_STATUSES` | NEW | module tuple, section 8.1 |
| `gate_check` | CHANGED | same signature, never raises, one contract read |
| `_spend_totals_from` | NEW | `(self, project_id, latest)`; `spend_totals` delegates |
| `upsert_units` | CHANGED | same signature, richer return, section 8.1 and 8.3 and 12.3 and 12.4 |
| `record_result` | CHANGED | one refusal branch for CANCELLED |
| `get_dispatch` | NEW | `(self, dispatch_id, raw=False) -> dict or None`, plus the `ReadOnlyStore` pass-through beside 13720 |
| `release_claimed_unit` | NEW | `(self, unit_id, actor) -> {'unit_id','status'}`; refuses `'unit-not-claimed'` unless the status is CLAIMED; sets PENDING or READY by dependency satisfaction and clears `fence_uuid` |

### 15.3 Every state move this design makes, and the table line that permits it

| Move | Made by | Permitted at tools/bm_store.py |
|---|---|---|
| EXECUTING to VERIFYING | `_unwind_empty_wave`, `_ensure_verifying`, `_settle_after_wave` | 2548 |
| VERIFYING to CHECKPOINTED | `_unwind_empty_wave`, `_settle_after_wave` | 2550 |
| CHECKPOINTED to READY | `_walk_to_executing` | 2552 |
| WAITING_HUMAN to READY | `_walk_to_executing`, `_deliver_or_hold` | 2554 |
| FAILED_RECOVERABLE to READY | `_walk_to_executing`, `_resume_result_in_and_orphans` | 2561 |
| READY to EXECUTING | `_walk_to_executing` | 2546 |
| READY or CHECKPOINTED to WAITING_HUMAN | `_handle_no_ready_units` | 2546, 2552 |
| READY or CHECKPOINTED to DELIVERABLE_READY | `_deliver_or_hold` | 2546, 2552 |
| VERIFYING or FAILED_RECOVERABLE to FAILED_TERMINAL | `_reject` | 2551, 2561 |
| anything non-terminal to STOPPING to STOPPED | `_begin_stopping` | 2541 to 2558 |
| PLANNING to READY | `upsert_units` | 2544 |

`CONTROLLER_STATE_TRANSITIONS` is not edited. No move outside this table
is attempted anywhere in the design, and the import-time guard proves the
three walk maps against it at load.

### 15.4 Schema

**No DDL change. No `SCHEMA_VERSION` bump.** `SCHEMA_VERSION` stays 15
(tools/bm_store.py:76) and `_MIGRATIONS` (3315) gains nothing. Every store
change above is either a new method, a new module constant, a new value in
an unconstrained TEXT column (`CANCELLED`, tools/bm_store.py:2507 has no
CHECK), or a behaviour change inside an existing method. `_DUMP_SAFE_COLUMNS`
(the block ending at 4015) needs no edit, because no column is added.

The one place a schema column WOULD have helped is provenance on
`autonomy_human_steps`, so the engine could auto-resolve the steps it
wrote. Section 8.5 explains why this design does not want that even if the
column existed, so the migration is not merely avoided, it is not needed.

---

## 16. Deferred, with the reason for each

These are refuted findings this design deliberately does NOT close. Each
is named here so the orchestrator can decide, and each is disclosed in
docs/KNOWN-LIMITS.md in the same words.

### 16.1 AZ F-A6, no path floor

A contract signed with `allowed_paths ['.']` authorises `.brothermode/
store.db`, `.git/config` and `.claude/settings.json`. Closing it means a
sixth entry in `AUTONOMY_FLOORS` (tools/bm_store.py:2596 to 2607), which
is a founder-facing closed set enumerated in `sign_contract`'s refusals,
in docs/AUTONOMY.md, in tools/bm_autonomy.py's help text and in
tools/test_bm_autonomy.py. That is a policy change about what a founder
may ever authorise, not a defect in the machinery this round was given.
The orchestrator's direction 5 names glob containment only. Recommendation
for a later round: a PATH floor refusing the store's own directory and
the VCS metadata directory, refused in `gate_check` before the
`allowed_paths` comparison at 12623, so no contract can grant it.

### 16.2 AZ F-A7, the duplicate-controller refusal is only on `begin()`

`step`, `receive_result` and `stop` perform no ownership check, so calling
`step` instead of `start` bypasses the fence guard at 359 to 365. Closing
it means deciding an ADOPTION policy for the `controller-<project>` fence:
a legitimate crash resume arrives with a different `--controller-id` and a
still-active fence, which is exactly the shape the fence store's
`adopted` state exists for (tools/bm_store.py:10206 to 10215). Picking
that policy is a design decision beyond this round's ten directions, and
guessing it would risk wedging the shipped resume path that
`cmd_start` (1961 to 2008) depends on. AZ itself scoped the finding
MEDIUM because the damaging version needs two simultaneous drivers, which
it did not demonstrate.

### 16.3 AZ F-A10, an empty `allowed_paths` still authorises a unit with an empty write scope

`gate_check`'s path check is skipped entirely when `path is None` (12623),
so a unit with no declared write scope is judged on its risk class alone.
Round 2 already ruled the empty-write-scope case NO-DATA on its own terms.
Making "no path granted" mean "nothing authorised" is a change to what an
empty `allowed_paths` MEANS, which is founder-facing contract semantics,
not controller machinery. Recommendation: decide it in the contract layer
(`sign_contract` refusing an empty `allowed_paths` outright), not in
`gate_check`.

---

## 17. Test plan

Every class below is NEW. Every one must be written FIRST, run against the
UNTOUCHED tree, and its failure captured to

`docs/program/absolute-lead/evidence/L03/RED-round4-refutation3-tests.txt`

in two labelled blocks (controller, store) with per-class failure and
error counts, exactly the method FIX-round3-report.md used. A class that
PASSES on the untouched tree is not evidence and must be rewritten until
it reproduces the finding it claims.

### 17.1 tools/test_bm_controller.py

| Class | Tests | Failing-first evidence it must produce |
|---|---|---|
| `TestR3PausedIsAFounderOnlyGate` | 6 | (a) a PAUSED run with a live contract dispatches nothing: today `dispatched == ['u2']` (SM A probe p08/p03). (b) `_deliver_or_hold` never moves PAUSED: today the run reaches DELIVERABLE_READY and `complete` then works (SM B probe p09a). (c) `receive_result` returns `"held"`, the dispatch is RESULT_IN, the fence is still active, no rollback ran; then `resume` plus one `step` accepts it: today it returns `"rejected"`, parks the fence and burns a retry. (d) `check_timeouts` returns `[]`: today it abandons and rejects. (e) `plan` refuses `'run-paused'`: today it flips the run to READY. (f) `run_to_completion` returns one summary with `stop_reason == "FOUNDER_WAITING"`. |
| `TestR3TheSummaryStateIsTheStoreState` | 3 | Every summary in a driven trace satisfies `summary["state"] == store.get_run(...)["state"]`: today the founder-waiting branch reports WAITING_HUMAN over a store that says EXECUTING (LV p11) or DELIVERABLE_READY (SM E probe p06 case A), and `run_to_completion` stops on the reported state (SM E probe p07 case 4). |
| `TestR3StopReasonDrivesEveryLoopDriver` | 6 | Soft spend stop: 1 step, `SPEND_STOP`, today 12 of 12 (LV p1). Failing done-definition: the CheckRunner records ONE done_definition execution per `run_to_completion` call, today 15 (LV p8 case C). Outage: 1 step, `OUTAGE`, today 15 worker asks (LV p8 case D). Fence contention: `CONTENTION`, and the note must NOT contain "founder", today it does (LV p2). Double amend: `CONTENTION`, same note assertion (LV p3). Ordinary async park: `IN_FLIGHT` in 1 step with 1 worker invocation, today 12 of 12 with 12 invocations (SM J probe p09 part c). |
| `TestR3TheExecutingWedgeUnwinds` | 2 | A unit whose write_scope the contract refuses leaves the run DELIVERABLE_READY with the run state read from the store; today `DELIVERABLE FOREVER OUT OF REACH: True`, 20 of 20 steps and 21 done_definition executions (LV p9). Second test: the wedge note never appears in any summary. |
| `TestR3TheSkippedLifecycleClosesAtTheSource` | 5 | `upsert_units` cancels the open dispatch (today it stays DISPATCHED). `receive_result` on it REFUSES 'dispatch-cancelled' (today it marks the dropped unit DONE, LV finding 4). `plan` parks the skipped unit's fence (today it stays active). A BYTE-IDENTICAL re-plan revives the SKIPPED unit (today it stays SKIPPED, LV p5). The whole founder recovery (drop, escalate, re-plan, resolve) ends DELIVERABLE_READY with both units DONE: today `RUN DELIVERED: False` (LV p6 control). |
| `TestR3BlockedIsAMaterialisedViewOfTheLaneGate` | 4 | Resolving the step unblocks the lane on the next step (today `select_ready_units` returns `[]` forever, SM F probe p07 case 3). A healthy unit sharing the lane recovers (today permanently BLOCKED, LV p12). Resolving WITHOUT repairing re-queues exactly one step (today: zero steps and a dead WAITING_HUMAN, LV p5). Ten consecutive `step` calls on a stalled run queue exactly ONE escalation step. |
| `TestR3EveryDispatchRouteIsGateChecked` | 4 | The re-await after a narrowing supersede does NOT call the worker a second time and parks the fence: today `worker call count {'u1': 2}` and `fence still held ... state: active` (AZ F-A1 c1). The revoke control still drains with one worker call (AZ C1b, must stay green). The re-await never opens a second dispatch row. A `TestNoSQLGuard`-shaped ast guard (copy its shape from tools/test_bm_controller.py:97) asserting that `self.worker.run` appears in exactly two function bodies, `step` and `_resume_dispatched`, and that each obtains its brief from a call to `_authorise_dispatch`. |
| `TestR3ForeignAndCancelledDispatchIdsRefuse` | 3 | A dispatch id from another PROJECT refuses without recording a result, moving a run or charging a meter: today an uncaught `TypeError` after both commits (AZ F-A3). The same for a dispatch from an earlier terminal run of the same project (SM K probe p10). `main()` never emits a traceback for either. |
| `TestR3LateResultKeepsItsSpendAndItsFounderRecord` | 4 | Spend lands on a STOPPED run: today `tokens 0 -> 0` (SM C probe p14, the four-shipped-command route). A late result at the retry ceiling with a stopped contract produces at least one new founder-visible record: today `before=(0, 0) after=(0, 0)` (SM D probe p06 case B). No BLOCKED status is written by the late-result path. The founder step lands in the UNIT's lane, not "default" (SM observation 4). |
| `TestR3FailedRecoverableReachesVerifying` | 2 | The run's persisted state read from inside the CheckRunner shows VERIFYING at the done_check and the run ends DELIVERABLE_READY: today it stays FAILED_RECOVERABLE with the unit DONE (SM I probe p16). Second test: the import-time walk guard still passes for all three edge maps. |
| `TestR3TheClaimedCrashWindowRecovers` | 2 | A CLAIMED unit with no dispatch row is re-queued and its fence parked on the next step: today `fence STILL: active`, `open founder steps: 0` (LV p13). Its `retry_count` is unchanged. |

### 17.2 tools/test_bm_store.py

| Class | Tests | Failing-first evidence |
|---|---|---|
| `TestGlobAllowedPathsAreDepthExact` | 4 | The four matrices of section 5.3 (`api/*.py`, `*.py`, `*`, `src/*` and `src/*/main.py`), asserted through `Store.gate_check`. Today `api`, `api/notes.md`, `api/sub/deep/secrets.env`, `secrets.env`, `src/prod/db.sql` and `infra/terraform/prod.tfstate` all come back ALLOWED (AZ F-A2 a2). |
| `TestGlobNarrowingBreaksNothingElse` | 2 | The non-glob rows of section 5.3 and the 18-spelling matrix LV p10 ran, asserting that the ONLY verdicts that moved are glob ones. |
| `TestGateCheckReturnsAVerdictInsteadOfRaising` | 3 | The symlink-after-plan case returns REFUSED-SCOPE: today it raises `OwnershipRefused` out of `gate_check` (AZ F-A5 a3). A non-string path and an empty path do the same. |
| `TestGateCheckVerdictComesFromOneContractRead` | 1 | A supersede fired between the two contract reads cannot produce a mixed verdict: today `verdict=ALLOWED revision=1` where revision 1 alone says REFUSED-BREAKER (AZ F-A9 D1.5). |
| `TestUpsertUnitsClosesTheSkippedLifecycle` | 4 | Dispatch cancellation; the byte-identical revival; `orphaned_fences` naming the skipped unit's fence; a colliding unit id refuses `'unit-id-taken'` instead of raising `sqlite3.IntegrityError` (AZ F-A4). |
| `TestUpsertUnitsRefusesANonPathWriteScopeEntry` | 1 | The `[5] / [['a.py']] / [{'p':'a.py'}] / [True]` matrix refuses 'bad-path': today all four are uncaught `AttributeError` (AZ F-A8). |
| `TestReleaseClaimedUnit` | 2 | Happy path and the `'unit-not-claimed'` refusal. |
| `TestGetDispatch` | 2 | A known id returns the row with `run_id` and `project_id`; an unknown id returns None. |

### 17.3 The done-check

After the last edit, in this order, with the command and the last lines of
its output pasted into the fix report:

```
cd /Users/khalil.maaouni/Documents/BrotherModeUp && python3 tools/test_bm_controller.py
cd /Users/khalil.maaouni/Documents/BrotherModeUp/tools && python3 test_bm_store.py
cd /Users/khalil.maaouni/Documents/BrotherModeUp/tools && python3 test_bm_autonomy.py
cd /Users/khalil.maaouni/Documents/BrotherModeUp/tools && python3 test_bm.py
```

The autonomy suite is not optional: this design edits `gate_check` and
`path_within_allowed`, which `bm-autonomy gate-check`
(tools/bm_autonomy.py:517 to 539) consumes directly.

Expected counts: controller 58 plus the new classes' tests; store 820 plus
the new classes' tests. Any DROP in either number is a deleted test and is
a failure of this change, not a result.

### 17.4 One test-shape rule, from FIX residual 5

Any new test that needs an engine branch which CATCHES a store refusal
must build its store from `bc.bs`, not from the test file's own
independent load, and must say why in its docstring, exactly as
tools/test_bm_controller.py:1937 to 1945 does. Two branches now catch:
the fence-overlap deferral inside `_authorise_dispatch` and the new
`record_result` race guard in `check_timeouts`. LV's p7 confirmed the
mechanism; this rule is how the writer avoids walking into it.

---

## 18. MIGRATION: existing tests that must change, and why each change is honest

Six existing test bodies are affected. Every one of them is named here
with the exact assertion that moves and the argument for why the
replacement is not weaker. Nothing else in either suite changes.

### 18.1 `TestR2F1LateResultOnARunStateThatCannotReachVerifying.test_the_four_red_rows_of_the_state_matrix_never_raise` (tools/test_bm_controller.py:1601)

The `red_rows` dict at 1607 to 1613 has four rows. **The PAUSED row (1610)
moves out of this class** into `TestR3PausedIsAFounderOnlyGate` test (c),
where it asserts the new behaviour: the result is RECORDED and HELD,
`receive_result` returns `"held"`, nothing is judged, the fence stays
active, the run stays PAUSED, and a subsequent `bm-controller resume` plus
one `step` ACCEPTS the same result. The other three rows
(DELIVERABLE_READY, STOPPING, STOPPED) stay verbatim, including the whole
of `_assert_late_result_handled` (1479 to 1502).

Why this is a strengthening and not a weakening: the assertions the PAUSED
row loses are "the founder was warned about a dirty scope", "the fence is
parked" and "an interruption names the late result". Every one of those is
a CONSEQUENCE OF REJECTING the result. Under the orchestrator's direction
1 the engine may not judge a paused run at all, so rejecting is the
behaviour being removed, and asserting its consequences would pin the
defect. What replaces them is stronger on the property the class exists to
protect: the real answer survives the pause and is accepted afterwards,
instead of being destroyed (rolled back on disk, retry burned) because a
founder pressed pause. Direction 1 is the orchestrator's own decision and
it postdates this test row, so this is a supersession, not a negotiation.

### 18.2 `TestR2F1LateResultOnARunStateThatCannotReachVerifying._assert_late_result_handled` (1479)

Gains two assertions, removes none: the unit's status is NOT `BLOCKED`
(section 10.3), and an open founder step naming the unit exists in EVERY
case, not only below the retry ceiling (SM D). The existing assertion at
1492 to 1494 ("must never gain newly selectable work") is satisfied by the
lane gate rather than by the BLOCKED status; the assertion text does not
change, because it asserts NOT-READY, and the unit is left in whatever
`mark_unit_failed` returned, which the lane gate makes unselectable and
which 1495 to 1496 already checks directly through `select_ready_units`.

### 18.3 `TestF4DependentOfAFailedUnitDoesNotStallTheRun` (1293) and `TestR2F4DeadDependenciesAndFounderGatedLanes` (1816)

**No assertion changes.** Both classes assert `BLOCKED` (1339, 1385, 1858,
1903) and both keep passing, because section 8.4 marks the escalated
lane's units BLOCKED as a view of the founder step the escalation queues
in that same lane. Only the class docstrings change, to say that BLOCKED
is now a reversible view of the lane gate rather than an independent
status. This is the reason section 8.5 keeps the founder step in the
unit's OWN lane instead of the lane-free alternative: the alternative
would have been cleaner in isolation and would have broken four
refutation-born assertions for no gain in protection.

Both classes GAIN one test each, in the new classes, asserting the
recovery the old ones never checked and the current code cannot perform.

### 18.4 `TestHumanBlockedLaneDoesNotStallIndependentLane` (926)

**No change.** The test calls `block_lane_units` AND queues a step in the
same lane (946 to 950), so section 8.4's reconcile finds the lane gated
and leaves the BLOCKED status alone. The assertion at 956 to 958 holds.

Worth stating for the writer: an UNPAIRED `block_lane_units` call, with no
open step in that lane, is now reversed by the reconcile on the next wave.
That is the pairing law made executable, and it matches
`block_lane_units`' own docstring ("paired with queue_human_step",
tools/bm_store.py:13294 to 13297). No test in either suite makes an
unpaired call.

### 18.5 `TestEndToEndE4` (1975)

**No assertion changes.** The artifact at
docs/program/absolute-lead/evidence/L03/E4-endtoend.json is regenerated on
every run by that class's own documented design (1983 to 1994), and
`run_states_visited` may gain or lose entries because `run_to_completion`
now stops on `DELIVERED` rather than on the state alone. Every assertion
in the class keys on `final_state`, `duplicate_work_count`,
`open_human_steps` and per-unit statuses, none of which this design moves:
the run still ends DELIVERABLE_READY with four DONE units, one open
release step and zero duplicate work. The reconcile writes nothing there,
because no unit is in the gated `release` lane.

### 18.6 `TestFault9ProviderOutageThenRecovery` (762) and `TestFault6CostCeilingReached` (583)

**No change**, verified against the new control flow rather than assumed.
Fault 9 drives `step()` three times explicitly and asserts only run states
and dispatch counts (786, 794, 800 to 805); the new `OUTAGE` reason stops
loops, and this test uses none. Its step 2 still lands in
FAILED_RECOVERABLE and its step 3 still reverses it through
`_resume_result_in_and_orphans` (807 to 810) and reuses the ORIGINAL
dispatch through `_authorise_dispatch`'s re-await route, because the
contract has not moved and the revision check in section 6.2 step 5a
passes. Fault 6 asserts `summary["state"] == "STOPPED"` (624), which
`_finish` reads back from the store.

### 18.7 tools/test_bm_store.py

`TestGateCheckPathIsContainmentNotOverlap` (15570): **no change.** All
three tests use non-glob allowed paths (`src/app`, `.`, `api`), which
section 5.1 leaves behaviourally identical. `TestPathsOverlapBehavior`
(3163): **no change**, `paths_overlap` is untouched.

### 18.8 Collisions

**None.** No change above weakens a refutation-born assertion. The one
that comes closest, 18.1, removes assertions about a behaviour the
orchestrator's own direction 1 forbids, and replaces them with a stricter
end-to-end property. A writer who finds a SEVENTH test needing a change
must stop and report it rather than editing it, because this list is the
whole set this design predicts.

---

## 19. Build order

Each step ends with a runnable check. Do not start a step until the
previous check passes.

1. **RED first.** Write all nineteen new test classes (section 17), run
   both suites, capture the failures to
   `docs/program/absolute-lead/evidence/L03/RED-round4-refutation3-tests.txt`.
   Check: every new class appears in that file with at least one failure
   or error.
2. **Store, pure functions.** `path_within_allowed` (5.1), `gate_check`
   (5.4, 5.5), `_spend_totals_from`. Check: `python3 test_bm_store.py`
   green except the store classes that need step 3, and
   `TestGlobAllowedPathsAreDepthExact` green.
3. **Store, controller methods.** `upsert_units` (8.1, 8.3, 12.3, 12.4),
   `record_result`'s CANCELLED branch, `get_dispatch`,
   `release_claimed_unit`, `CONTROLLER_DISPATCH_STATUSES`. Check:
   `python3 test_bm_store.py` fully green.
4. **Controller, module data.** `STOP_REASONS`, the note constants,
   `_walk_reaches`, the three edge maps and their derived sets, the
   extended import-time guard. Check: `python3 -c "import
   bm_controller"` succeeds and `TestR3FailedRecoverableReachesVerifying`
   test 2 passes.
5. **Controller, the funnel and the guard.** `_finish`, `_set_reason`,
   `_run_or_refuse`, `_is_paused`, `_refuse_if_paused`, and `step`'s
   rewiring to a single exit. Check: `TestR3PausedIsAFounderOnlyGate` and
   `TestR3TheSummaryStateIsTheStoreState` green.
6. **Controller, the choke point.** `_authorise_dispatch`,
   `_resume_dispatched`, `_handle_worker_result`'s new return, the
   deletion of `_claim_and_dispatch`. Check:
   `TestR3EveryDispatchRouteIsGateChecked` green, including the ast guard.
7. **Controller, liveness.** `_open_dispatch_units`, `_may_dispatch`,
   `_unwind_empty_wave`, `_reconcile_lane_blocks`, `_unreachable_units`,
   `_escalate_unreachable_units`, `_handle_no_ready_units`,
   `_deliver_or_hold`, `_loop_stops` and both drivers. Check:
   `TestR3TheExecutingWedgeUnwinds`,
   `TestR3StopReasonDrivesEveryLoopDriver`,
   `TestR3BlockedIsAMaterialisedViewOfTheLaneGate`,
   `TestR3TheSkippedLifecycleClosesAtTheSource` green.
8. **Controller, results.** `receive_result`, `_handle_late_result`,
   `_warn_dirty_write_scope`, `_verify_and_finish`'s stale rollback,
   `check_timeouts`. Check: the three remaining new classes green.
9. **CLI and docs.** Section 14, plus docs/FULL-AUTO.md,
   docs/KNOWN-LIMITS.md and docs/AUTONOMY.md (the glob rule from 5.1, the
   three deferrals from section 16, the SM G bound from 12.1, the unit-id
   namespace from 12.3, the NUL-byte path from 12.4, and the new
   `stop_reason` field). Check: the four commands of section 17.3, all
   green, with counts no lower than 58 and 820 plus the new tests.
10. **Hostile re-read.** `git status`, `git diff --stat`, then re-read
    every hunk for leftover debug prints, half-applied renames, and any
    TODO or placeholder. Confirm no em or en dash entered any file.

---

## OPEN QUESTIONS

None. Every direction the orchestrator gave is resolved above with a
stated mechanic, and the three findings this design does not close are
recorded in section 16 with their reasons rather than left as questions.
Section 18.8 records that no refutation-born test is weakened; the one
supersession, 18.1, follows directly from the orchestrator's own direction
1 and needs no further decision.
