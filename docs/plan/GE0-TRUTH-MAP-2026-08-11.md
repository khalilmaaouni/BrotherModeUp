# GE0 truth map: what already exists for the graph

Status: CURRENT. Read-only inventory against main at 17d8512, produced by
a navigator agent and spot-checked by the orchestrator (critical_path at
bm_docs.py:444, the ready-only filter at bm_project.py:944, and the
two-column dependencies table, each confirmed by hand). Roadmap:
docs/plan/ROADMAP-2026-08-11-GRAPH-ENGINEERING.md. No em or en dashes.

## Verdicts, one row per spec proposal

| Target | Verdict | Where |
|---|---|---|
| Typed graph nodes on tasks | ABSENT | tasks table has status, priority, phase; no node type anywhere |
| Typed edges | ABSENT | dependencies(task_id, depends_on_task_id) only, no edge type column |
| Static graph validation | PARTIAL | upsert_units (bm_store.py:14620) checks dangling deps and cycles for CONTROLLER units only; the tasks table has zero dependency evaluation, and cmd_next (bm_project.py:944) filters status ready without reading depends_on |
| Write scopes per unit | EXISTS | tasks and controller_units both carry read_scope and write_scope; claims carry the fence path |
| Acceptance criterion records | ABSENT | done_definition is one free-text field; acceptance_checks a JSON list column, not addressable rows |
| Evidence links | EXISTS | evidence(subject_type, subject_id) with app-level existence checks; the gap is structure inside ref, not the join |
| Attribution | EXISTS | attribution table written by every mutating store method |
| Workflow motif memory | ABSENT | all learning_ tables are correction shaped; nothing stores a successful structure |
| Graph telemetry | PARTIAL | bm_telemetry records per-session tokens and calls; no run, node, edge or width fields |
| Typed dispatch and return packets | EXISTS | UnitBrief out and WorkerResult in are typed dicts already (bm_controller.py:216, :3185); the gap is the Claude-harness subagent lane, not the controller |
| Canonical booklet source | EXISTS | docs/book/ is CURRENT (2026-07-30 onward); docs/WHITEPAPER.md is marked UNAUDITED and older |
| Critical path | EXISTS | generic critical_path(weights, edges) at bm_docs.py:444 with tests; runs over the fence graph today, reusable for tasks |
| Width metric | ABSENT | no parallelism width computed anywhere |

## Duplicate-risk warnings, binding on Wave 2 builders

1. Reuse critical_path() from bm_docs.py; do not write a second one.
2. Extend the upsert_units cycle check to the tasks graph; do not write a
   parallel checker.
3. The write-overlap check builds ON the existing claims overlap
   machinery (_find_overlap, bm_store.py:11444), not beside it.
4. No new receipt table: structure the existing evidence.ref instead.

## What this changes in the roadmap pricing

The Wave 2 fold is cheaper than feared in two places (packets and
critical path largely exist) and confirmed necessary in the three the
founder ratified: node and edge typing, criterion records, and the
validator for the TASKS graph, whose dependency blindness is the live
defect this map re-confirmed at the code.
