# LOOP B1: benchmark, option A, step-level plan

Status: DRAFT. Written against `main`, house style copied from
`docs/plan/RELEASE-v3.1.0-PLAN.md` section 5 (ID, Task, Files, Done-check,
Owner columns; every task names its files and one runnable done-check). No
em or en dashes anywhere in this file.

Source: `docs/plan/PROGRAM-PLAN-2026-08-10.md` section 5, Loop B1 ("Build
`docs/NORTH-STAR.md` with VADR and the column naming which of the fifteen
conditions is mechanically checkable today. Done-check: the corpus runs
twice from identical snapshots with mechanically comparable output"), and
`docs/closure/WBS-NORTH-STAR-2026-08-10.md` sections W1.1 to W1.3 (locate or
build the harness; the corpus; the VADR definition) and S1 ("the benchmark
is the P0, and it is UNRUN").

## What already exists, so this plan extends rather than duplicates

- `scripts/benchmark_comparative.py` (header read this session, lines 1-90
  and the function index): a working v2 harness, Python 3.9 stdlib only,
  living under `scripts/` (not `tools/`) because it drives real subprocess
  model calls. `--list`, `--dry-run`, `--task Tn --arm A|B`,
  `--probe-installed` are all implemented. `checks_t1`..`checks_h7` and
  `build_t1`..`build_h7` (function index, lines 40-90) already cover
  thirteen tasks (T1-T6, H1-H7), more than option A's ten.
- `docs/BENCHMARK-COMPARATIVE.md`: protocol v2 frozen 2026-08-07, one
  recorded run (`20260807T140548Z-v2`, 26 cells, all exit 0, deterministic
  checks only). The page states plainly: "No v2 cell [of the wired task
  set] has been run" for the H-task wiring inside the harness beyond what
  the recorded run covered, and "the blind judgment rubric has not been
  graded for this run yet, and no aggregate score exists until it does."
- `docs/evidence/benchmark-run-2026-08-10.json`: a DIFFERENT, simpler
  harness output shape than the v2 protocol above (`system: "bare"` vs
  `"brothermode"`, per-task `acceptance.accepted`/`reason`,
  `agent.exit_code`/`stderr_tail`/`wall_seconds`/`timed_out`). This is a
  real recorded run (`dedupe-order`, `reset-token` tasks visible in the
  first 60 lines read this session), but it is not in the same shape as
  `scripts/benchmark_comparative.py`'s own `checks.json`/`manifest.json`
  artifact layout described in that script's docstring. Reconciling which
  of these two is authoritative, or whether both are kept as separate
  evidence lines, is B1.1 below, not assumed here.
- No `docs/NORTH-STAR.md` exists yet (WBS W1.3 names it as a deliverable,
  not as something already in tree).

## Steps

| ID | Step | Files | Extends or new | Done-check |
|---|---|---|---|---|
| B1.1 | Reconcile the two evidence shapes: confirm whether `docs/evidence/benchmark-run-2026-08-10.json` was produced by `scripts/benchmark_comparative.py` or by a separate ad hoc script, and record the answer in the harness doc so the next reader is not left guessing | `docs/BENCHMARK-COMPARATIVE.md` | Extends the existing status section | a sentence naming the producing script (or naming it unknown, with the search command that failed to find one) is added and visible in a `grep` for the run id `benchmark-run-2026-08-10` in that file |
| B1.2 | VADR definition: write the metric, its counter-metrics (interventions, cost, rework, recovery, false refusals, evidence completeness, per program plan section 1), and a fifteen-row table, one row per brief condition, with a column stating MECHANICAL (names the exact check) or HUMAN-ASSERTED (names why no check exists today) | `docs/NORTH-STAR.md` (new) | New | `grep -c "MECHANICAL\|HUMAN-ASSERTED" docs/NORTH-STAR.md` returns 15, one per condition row |
| B1.3 | Corpus option A: select or write ten tasks, BrotherMode vs vanilla Claude Code only (WBS W1.2's explicit recommendation: "fast but weak", labelled as option A). Reuse `scripts/benchmark_comparative.py`'s existing T1-T6 and four of H1-H7 rather than inventing ten new tasks, since six are already built and calibrated (`sanity_t1`..`sanity_t6` functions already exist) | `scripts/benchmark_comparative.py` (task selection only, no new `build_*`/`checks_*` functions unless the existing thirteen do not cover ten suitable tasks) | Extends. New `build_*`/`checks_*` pairs only if the existing set cannot supply ten after review | `python3 scripts/benchmark_comparative.py --list` prints exactly the ten selected task ids, named in `docs/NORTH-STAR.md`'s corpus section |
| B1.4 | Arm definition confirmed unchanged: arm A plain `claude -p` in an empty `CLAUDE_CONFIG_DIR`, arm B the shipped plugin install path, exactly as `docs/BENCHMARK-COMPARATIVE.md`'s "Protocol version 2" section already specifies. This step performs no new design, only confirms option A does not require a third arm and records that confirmation | `docs/NORTH-STAR.md` | N/A, confirmation only | the corpus section of `docs/NORTH-STAR.md` states "two arms, per BENCHMARK-COMPARATIVE.md protocol v2" and cites the section by name |
| B1.5 | Blind grading wiring: the H-task rubric already exists in `docs/BENCHMARK-COMPARATIVE.md` ("The blind rubric, v2 additions" and "The blind rubric (fixed)" sections) and `scripts/bench_blind_pack.py` already exists with a passing `--self-test` per that doc's "v2 status" paragraph. Wire the ten-task corpus's outputs through the existing blind pack tool rather than writing a second grading path | `scripts/bench_blind_pack.py` (invocation only; new code only if the existing tool cannot consume the ten-task output as-is) | Extends | `python3 scripts/bench_blind_pack.py --self-test` OK, then a real run over the ten-task corpus produces a pack the tool accepts without a schema error |
| B1.6 | Two identical-snapshot runs, the acceptance gate itself: run the ten-task corpus twice from the same starting commit and the same fixture-build code path, with no code change between the two runs | none (produces artifacts under the harness's existing `EVIDENCE` directory, `scripts/benchmark_comparative.py` line ~38) | N/A, execution only | both runs' `checks.json` files, task by task, report the same PASS/FAIL/SKIP verdict for every deterministic check; a byte-for-byte diff of the two verdict tables, not the full transcripts, is quoted as the done-check evidence |
| B1.7 | Publish the comparison table in `docs/NORTH-STAR.md`, cross-referencing `docs/BENCHMARK-COMPARATIVE.md` rather than duplicating its historical sections, and mark every number as INTERNAL EVIDENCE per that document's own honesty rule | `docs/NORTH-STAR.md` | Extends B1.2's file | the file contains the exact sentence "self-graded, one machine, no outside user" or an equivalent carrying the same caveat, matching the existing wording in `docs/BENCHMARK-COMPARATIVE.md` |

## Acceptance gate

The program plan's own words, matching WBS W1.1's done-check verbatim: "the
corpus runs twice from identical snapshots with mechanically comparable
output." B1.6 is the literal execution of this gate; B1.1 through B1.5 are
the wiring that must exist before B1.6 can be run for real, and B1.7 is the
write-up that makes the result legible without re-deriving it from raw
artifacts.

SIZE: 2 to 4 days for option A, MEDIUM confidence, matching the program
plan's own estimate. The lower end applies if B1.3 finds the existing
T1-T6 plus four H-tasks sufficient with no new `build_*`/`checks_*` code;
the upper end applies if new tasks must be written and calibrated
(`sanity_*` both-ways per task, the same calibration discipline Loop 3 of
the release plan already requires elsewhere in this program).

## Remaining

- Which ten of the thirteen existing tasks (T1-T6, H1-H7) become option A's
  corpus is not decided in this document; B1.3's implementer chooses and
  records the choice with a reason, since the brief's option A does not
  name specific tasks.
- The reconciliation in B1.1 has not been performed; this document states
  the discrepancy between the two evidence shapes but does not resolve it.
- `docs/NORTH-STAR.md` does not exist yet; every file reference to it above
  describes a step's output, not a file this session has read.
- No run of any kind (single or twice-repeated) has happened for this loop;
  the recorded run cited in `docs/BENCHMARK-COMPARATIVE.md` predates this
  plan and does not satisfy B1.6's twice-from-identical-snapshots gate on
  its own, since it is one run, not two compared against each other.

## Unverified

- Whether `scripts/bench_blind_pack.py` can consume a ten-task corpus
  output without modification (B1.5) was inferred from its documented
  `--self-test` passing on an unspecified fixture set, not from tracing
  its input schema against the ten selected tasks.
- Whether the ten tasks chosen from T1-H7 give BrotherMode vs vanilla
  Claude Code (option A's stated pair) a discriminating result, as opposed
  to the deterministic-ceiling saturation the recorded run already showed
  for T1-T6 ("T1 to T6 hit the deterministic ceiling in both arms" per
  `docs/BENCHMARK-COMPARATIVE.md`), is a live risk this document flags but
  does not resolve; H1's fence-collision task is the one the existing
  record shows actually discriminating (0/2 vs 2/2), so the corpus
  selection in B1.3 should weight toward H-class tasks over saturated
  T-class ones, a recommendation only, not a decision made here.
