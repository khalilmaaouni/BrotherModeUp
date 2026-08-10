# LOOP V1: acceptance contract with an independent verifier

Status: DRAFT for strongest-tier review. Written against `main` this
session; every symbol below was opened and confirmed, not recalled. No em
or en dashes anywhere in this document.

Ties to north star: `docs/plan/PROGRAM-PLAN-2026-08-10.md` section 5, Loop
V1 ("Brief 3.5, 3.6, Loop 5 of the brief... today the verifier is
model-authored by the same flow"). WBS rows:
`docs/closure/WBS-NORTH-STAR-2026-08-10.md:158` N5 ("Acceptance contract
frozen before implementation, classified by testability") and `:159` N6
("Independent verifier with an information boundary, not a persona").
North star objective it serves: independent proof, the second of the
brief's three pillars alongside bounded autonomy and recoverable state.

House style mirrors `docs/plan/RELEASE-v3.1.0-PLAN.md` section 5: every
step names its files and ends with one runnable done-check.

## 1. What exists today, confirmed by file and line

The freeze half of N5 already exists. `tools/bm_autonomy.py:429`
`cmd_sign` requires `--done-definition` (`_require(kv, "done-definition",
usage)` at line 439) before a contract can be signed at all; `cmd_sign`
stores it via `store.sign_contract` (line 451) and echoes it back at line
460. A contract's `done_definition` is therefore frozen text, set once,
before any unit under it runs. What N5 is MISSING is classification by
testability: the freeze accepts any string and never marks whether that
string names something a machine can check.

The independence half of N6 is unmet. `tools/bm_controller.py:3243`
`_verify_and_finish` is the controller's own account of itself: its
docstring calls it "the controller's OWN done-check (INDEPENDENT of the
worker: a worker that lies about tests is caught here because the real
exit code is re-read, never the worker's claim)". But the command it
re-runs, `unit["done_check"]` (line 3288, `self._run_command(project_id,
unit["done_check"] or "true", ...)`), is itself authored by the SAME
planning flow that produced the unit in the first place. Independence from
the WORKER's claim is real and load-bearing (staleness re-read, contract
re-read, both documented in that method's own comments); independence
from the PLANNER's own acceptance criteria is not present anywhere in this
file. There is no `cmd_verify` in `tools/bm_autonomy.py` (grepped: only
`cmd_sign`, `cmd_show`, `cmd_gate_check`, `cmd_assume`, `cmd_interrupt`,
`cmd_spend`, `cmd_pause`, `cmd_resume`, `cmd_stop`, `cmd_revoke`,
`cmd_status`, `cmd_queue_human_step`, `cmd_human_steps`,
`cmd_checkpoint`).

## 2. Architecture: build independence ONTO the freeze, not a new contract store

V1 does not replace `sign_contract` or `_verify_and_finish`. It adds two
things to the seam that already exists:

1. At freeze time (`cmd_sign`), classify `done_definition` by
   testability, so the frozen text itself states whether a machine can
   grade it.
2. At verify time (`_verify_and_finish`), the command re-run stays (it is
   the worker-independence mechanism and REFUTATION-4 AZ F5 already
   protects its ordering), but the JUDGMENT of whether the re-run
   satisfies the frozen `done_definition` moves to a fresh-context pass
   that never saw the unit's own `done_check` text or its authoring
   session, only the frozen criteria and the re-run's raw output.

```
today:   sign (freeze text) -> plan (author done_check) -> dispatch ->
         _verify_and_finish re-runs done_check, PLANNER'S OWN judgment
         of pass/fail (the done_check's own exit code, chosen by the
         same flow that wrote it)

V1:      sign (freeze text + testability class, bm_autonomy.py) -> plan
         -> dispatch -> _verify_and_finish re-runs done_check (UNCHANGED)
         -> tools/bm_verify.py (new) is handed ONLY: the frozen
         done_definition, the re-run's raw stdout/stderr/exit code, and
         nothing else naming the unit, the planner, or the worker's own
         narration. It returns ACCEPT, REJECT, or
         INSUFFICIENT_EVIDENCE, never a bare boolean.
```

`tools/bm_verify.py` is new because no existing module holds a judgment
step with an enforced information boundary; the freeze and the re-run
stay exactly where they are, per the instruction to build onto the
existing freeze rather than a parallel contract store.

## 3. Work breakdown

| ID | Step | Files | EXTENDS or NEW | Done-check |
|---|---|---|---|---|
| V1.1 | Classify `done_definition` by testability at sign time: `mechanical` (a command whose exit code decides it), `evidenced` (a quoted artifact a human or verifier reads, e.g. a screenshot path), `asserted` (no mechanical check exists yet, matching the program plan's own "several are not yet mechanically checkable" note) | `tools/bm_autonomy.py` near `cmd_sign` (line 429) | EXTENDS | `python3 tools/test_bm_autonomy.py` OK; a new test signs three contracts, one per class, and asserts the stored row carries the class |
| V1.2 | Refuse `verified` autonomy mode (the same label Loop 5's live deny canary gates, `bm_controller.py:5023`) for any run whose contract is classified `asserted`, unless a human step is queued alongside it | `tools/bm_autonomy.py`, `tools/bm_controller.py` | EXTENDS | a test signs an `asserted` contract, attempts a verified-mode run, and asserts refusal naming the class |
| V1.3 | Build `tools/bm_verify.py`: `judge(done_definition, testability_class, raw_output)` returns ACCEPT, REJECT, or INSUFFICIENT_EVIDENCE. For `mechanical`, judgment is the exit code alone, no model call. For `evidenced`, a fresh-context model call receives ONLY the frozen text and the raw output, never the unit id, the session id, or any prior narration | `tools/bm_verify.py` (new) | NEW, the judgment seam | a fixture with a passing exit code and one with a failing exit code are judged correctly for `mechanical`; an `evidenced` fixture with fabricated success narration is judged from the artifact only, asserted by feeding contradicting narration and an artifact that fails, expecting REJECT |
| V1.4 | Wire `_verify_and_finish` (`bm_controller.py:3243`) to call `bm_verify.judge` AFTER its existing re-run and re-read, passing only the frozen `done_definition` and the re-run's raw output, never `unit["done_check"]`'s source text | `tools/bm_controller.py` | EXTENDS | `python3 tools/test_bm_controller.py` OK; a new test confirms the call into `bm_verify` never receives the unit id or done_check string, by asserting on the exact argument tuple |
| V1.5 | Stale-evidence rejection: `judge` refuses any `evidenced` submission whose artifact's mtime predates the current dispatch's start time | `tools/bm_verify.py` | NEW | a fixture with an artifact timestamped before dispatch start returns REJECT with reason `stale evidence` |
| V1.6 | Register `bm_verify.py`'s commands in the effect-class registry | `tools/bm_effects.py` | EXTENDS the registry pattern | `python3 tools/test_bm_effects.py` OK; `judge` itself classified `pure_read` since it writes nothing, only the caller's receipt write is `ledger_write` |
| V1.7 | Independent refute pass over V1.1 to V1.6 | none, read-only | matches Loop 2's own 2.6 pattern | reviewer names a case the classification or the information boundary misses, or states plainly it could not |

## 4. Seeded-defect matrix, per the north-star brief's Loop 5 set

Each defect is seeded into a fixture, then `bm_verify.judge` is run
against it. A defect that `judge` accepts is a bug in `judge`, not in the
fixture; each row below states what must be REJECTED or flagged
INSUFFICIENT_EVIDENCE, at a pre-registered rate quoted in the same test
run (the program plan requires "a pre-registered rate", so V1.3's tests
fix the expected outcome before the code is written, RED first).

| Seeded defect | How it is seeded | Required verdict |
|---|---|---|
| Weakened tests | fixture's `mechanical` command is a test file with an assertion loosened (e.g. `assertTrue(True)` swapped in) but the frozen `done_definition` still names the original behavior | REJECT once `judge` is handed the frozen text and the weakened test's real output, since the two do not match |
| Deleted assertions | same fixture family, an assertion removed rather than loosened | REJECT, same mechanism |
| Mocked-away behavior | `evidenced` fixture whose artifact was produced against a mock, stated in a metadata field `judge` is required to read | REJECT when the metadata names a mock and the frozen criteria required the real path |
| Stale evidence | V1.5's own case | REJECT, `stale evidence` reason |
| Flag never enabled | `evidenced` fixture claiming a feature flag change took effect, artifact shows the flag's prior value unchanged | REJECT, mismatch between claimed and observed state |
| Dead UI path | `evidenced` fixture, a screenshot path that does not exist or is unreadable on disk | INSUFFICIENT_EVIDENCE, distinct from REJECT since no evidence was produced at all, not evidence that failed |

## 5. Sizing

2 to 4 days, MEDIUM confidence, matching the program plan's own estimate
for Loop V1. Variance is concentrated in V1.3's `evidenced` class, the
only branch needing a fresh-context model call with an enforced
information boundary; the `mechanical` branch is pure exit-code logic and
carries the HIGH-confidence half of this estimate.

## 6. Remaining and Unverified

- Whether `bm_autonomy.py`'s `sign_contract` store method
  (`tools/bm_store.py`) already has a spare column for a testability
  class, or whether V1.1 needs a schema migration, was not checked
  against `bm_store.py`'s contract table this session.
- What "fresh-context model call" means operationally inside
  `bm_controller.py`'s existing `SubprocessCheckRunner` seam (the file's
  own comment names it as the only two subprocess call sites alongside
  the fence canary) was not resolved; V1.3 assumes a callable boundary
  exists or can be added without reopening that gate, which needs
  confirming against `SubprocessCheckRunner`'s actual constructor.
- The Codex lane's cross-model verifier, named in the program plan as
  making this "cheap later", is Loop CX's own work; this draft does not
  assume Codex is available and V1.3's fresh-context call is scoped to
  work with whatever runtime signed the contract.
- Loop C1 (convergence engine) depends on V1 per the program plan; this
  draft did not check what shape C1 expects `judge`'s REJECT reasons to
  take, since C1 has no plan document yet.
- No test suite was run by this draft, per the fence instruction covering
  this session; every done-check above, including the seeded-defect
  matrix's pre-registered rate, is UNRUN and needs its own RED-then-GREEN
  pass before this loop is called built.
