# LOOP C1: the convergence engine, step-level plan

Status: DRAFT. Written against `main`, house style copied from
`docs/plan/RELEASE-v3.1.0-PLAN.md` section 5 (ID, Task, Files, Done-check,
Owner columns; every task names its files and one runnable done-check). No
em or en dashes anywhere in this file.

Source: `docs/plan/PROGRAM-PLAN-2026-08-10.md` section 5, Loop C1 ("verifier
findings append tasks, bounded rounds, deterministic checks outrank
judgment. Depends on V1. Done-check: a seeded three-gap task converges
without human re-prompting, within its round ceiling"), and
`docs/closure/WBS-NORTH-STAR-2026-08-10.md` row N7 ("Convergence engine
that appends tasks rather than reporting gaps | Not in tree"), tied to
brief section 3.7 and the Spec Kit precedent this program answers (program
plan section 4: "Spec Kit `converge` VERIFIED: appends them as new tasks
under a Convergence section").

DEPENDS ON Loop V1 (acceptance contract with an independent verifier,
program plan section 5). V1 is not yet landed. This document plans C1's
own files; it does not restate V1's plan. Where a step needs a V1 output
that does not exist yet, the step says so and names the stub it builds
against in the meantime.

## The store constraint this loop must design around

Read first, both confirmed by opening the files this session:

- `brotherme/core/schema.py` lines 40-49: ten task states in fixed forward
  order (`planned`, `ready`, `active`, `blocked`, `awaiting review`,
  `verified`, `accepted`, `delivered`, `monitored`, `closed`).
  `LEGAL_TRANSITIONS` (lines 63-73) allows only `planned -> ready`,
  `ready -> active`, `active -> blocked|awaiting review`,
  `blocked -> active`, and so on in strict single-step order; `closed` has
  no legal exit.
- `tools/bm_project.py` `cmd_next` (line 912) reads candidates with
  `store.list_tasks(project_id, status="ready", raw=want_raw)` (line 928):
  filtering is on state alone. `depends_on` is a stored field
  (`cmd_task_add`, line 978 onward, `--depends-on` maps to
  `task["depends_on"]`) but `cmd_next` never reads it. No dependency
  evaluation happens anywhere in this file.
- Consequence for this loop: a task the engine creates as a finding sits in
  `planned` and is invisible to `next` until something transitions it to
  `ready`, and a `depends_on` value on it is decorative unless C1 itself
  enforces the order. The engine must drive every transition by hand
  (`bm_project task transition --to ...`, `tools/bm_project.py` lines
  1039-1057) rather than relying on the store to sequence work.

## Steps

| ID | Step | Files | Extends or new | Done-check |
|---|---|---|---|---|
| C1.1 | Define the convergence unit: one verifier finding becomes one task, with a fixed field mapping (finding id in `reason`, source check in `assignment_reason`, severity in `priority`) and a round counter stored on the task or a sibling record | `tools/bm_converge.py` (new) | New. No converge module exists in `tools/` today (`ls tools/bm_converge.py` fails before this step) | a unit test constructs one synthetic finding dict and asserts the mapped task fields match the fixed mapping, no store involved |
| C1.2 | Round-bounded driver: given a project id and a round ceiling, call the verifier (V1's entry point, or a stub function with the same signature if V1 has not landed when this step starts), turn each open finding into a task via `bm_project.py`'s own `create_task` path (not a raw store call, so validation and attribution stay identical to a human-typed `task add`), and transition each new task `planned -> ready` immediately so `next` can see it | `tools/bm_converge.py` | Extends `tools/bm_project.py` only by calling its existing `cmd_task_add` / `store.create_task` and `store.transition_task`; adds no new verbs there | against a tempfile store, one synthetic finding round-trips to a task in state `ready`, confirmed with `bm_project task list` (or `store.list_tasks`) showing status `ready`, not `planned` |
| C1.3 | Deterministic-outranks-judgment gate: before asking the verifier for a judgment-based finding, run every check the finding's class has a mechanical test for (the fixed acceptance checks from V1, or in the interim the project's own `pytest`/`test_*` exit code) and only surface a finding the mechanical check did not already resolve | `tools/bm_converge.py` | Extends V1's check runner if it exists by the time this step starts; otherwise New against a documented stub interface this step defines and V1 must satisfy | a fixture with one mechanically-resolvable gap and one judgment-only gap: the driver appends exactly one task, for the judgment-only gap, and the mechanically-resolvable gap never becomes a task |
| C1.4 | Convergence loop: after each round, re-run the mechanical checks; a task whose check now passes transitions `ready -> active -> awaiting review -> verified` (each hop a separate `transition_task` call, since the schema forbids skipping states) and the round counter increments; the loop stops at the round ceiling or when zero open findings remain, whichever comes first | `tools/bm_converge.py` | Extends `tools/bm_project.py` transitions only, no schema change | the seeded three-gap fixture (C1.6) converges to zero open findings in fewer rounds than the ceiling, and the loop's own log names which round closed each of the three |
| C1.5 | Never silently drop a finding: a finding the driver cannot turn into a legal task (missing project, illegal transition, store refusal) is logged to a distinct output stream and counted, never swallowed | `tools/bm_converge.py` | Extends the driver from C1.2 to C1.4 | a fixture that forces one `SchemaError` (e.g. a duplicate task id) surfaces it by name in the driver's stderr-equivalent output and in its returned summary count, and the process does not raise past the driver into a bare traceback |
| C1.6 | The seeded three-gap fixture: a tempfile store with a project carrying exactly three known gaps (one mechanically checkable and already broken, one mechanically checkable and already fixed, one judgment-only), used as the acceptance gate | `tools/test_bm_converge.py` (new) | New | `python3 tools/test_bm_converge.py` run standalone: the fixture converges (zero open findings) within the declared round ceiling with no human input between rounds, and the test asserts the exact round count is less than or equal to the ceiling |
| C1.7 | Purity and registration: classify every new `bm_converge.py` command in the effect-class registry, then register the module in all four required places | `tools/bm_effects.py`, `tools/test_all.py`, `.github/workflows/tests.yml`, `pyproject.toml`, `tools/write_sites.json`, `CHECKSUMS.sha256` | Extends `tools/bm_effects.py`'s existing `REGISTRY` dict (pattern at `tools/bm_effects.py` lines 1-80); the four-places contract is the one Loop 2 and the CX plan both already use, not a new contract | `python3 tools/test_bm_effects.py` OK after registration; `python3 tools/test_bm.py` OK; checksums regenerated LAST per the standing rule, `git add` new files before regenerating |
| C1.8 | Independent refute pass: a reviewer tries to make the driver either silently drop a finding or accept a mechanically-failing task as `verified` | none, read-only | N/A | the reviewer names a hole in C1.1 to C1.7, or states plainly it tried and could not; recorded before this loop is called closed |

## Acceptance gate

The program plan's own words: "a seeded three-gap task converges without
human re-prompting, within its round ceiling." Concretely: C1.6's fixture,
run by C1.6's test, with zero calls into the driver between the start of
the test and its assertion of zero open findings. A round ceiling the test
does not reach is not evidence of convergence; the test must show the
ceiling would have caught a non-converging case, which is why one of the
three seeded gaps starts already fixed (C1.6) rather than all three
starting broken.

SIZE: 1 to 2 days after V1, MEDIUM confidence, matching the program plan's
own estimate. C1.3's dependency on V1's check runner is the main variance:
if V1 lands with a different interface than the stub this loop assumes,
C1.3 and C1.4 need rework, which could push this to 3 days.

## Remaining

- V1 is not landed; C1.3's stub interface is this document's own
  assumption, not a frozen contract, and must be reconciled against V1's
  actual entry point before C1 starts for real.
- Whether `create_task` / `transition_task` enforce the `depends_on` field
  at all (the store constraint section above says `next` does not; whether
  the store layer itself does anything with it on write was not checked
  this session and is UNVERIFIED).
- Whether a finding maps to exactly one task or can map to zero (already
  resolved) or many (a finding spanning multiple files) is a design
  decision this document defers to C1.1's implementer, not decided here.
- No code in this loop has been written or run yet; every done-check above
  is a target, not a result.

## Unverified

- The exact shape of V1's verifier output (what a "finding" dict contains)
  is inferred from the program plan's prose, not read from V1 code, because
  V1 is not in the tree.
- Whether `store.create_task` performs its own state-machine validation
  independent of `bm_project.py`'s CLI layer, or relies entirely on the CLI
  to call `transition_task` afterward, was read from `cmd_task_add`
  (defaults `status` to `"planned"`) but not traced into `bm_store.py`
  itself this session.
