# Loop 2 design: the seven beginner commands become mechanical operations

Status: CURRENT. Written 2026-08-01 by the orchestrator (Fable), from the
scout report of the same day. Gate (program map): a scripted first project
runs end to end through the seven commands. Founder Report 3 follows.

## Findings this design stands on (scout, 2026-08-01, file:line verified)

- All seven commands/brotherme-*.md are prose instructions; none contains
  or invokes a mechanical operation (grep for bm_store, store.sqlite3,
  .brothermode across commands/ and skills/brotherme returns nothing).
- The schema-12 service methods (upsert_project, add_forecast,
  create_task, transition_task, raise_alert, resolve_alert, add_evidence,
  record_runtime_run, bm_store.py:9785-10060) have NO CLI subcommands and
  NO read accessors; the only read path is whole-DB dump().
- SKILL.md:34 still names CANVAS.md as the source of truth for status and
  next: exactly the parallel bookkeeping Loop 1 exists to end.

## Decisions (ADR style, short)

D-1. ONE new thin CLI, tools/bm_project.py, wrapping the existing Store
     service methods. Rejected: growing bm_store.py's command table by
     ten subcommands (it is the ownership ledger CLI; project lifecycle
     is a different user and register). Rejected: code inside command
     markdown (not executable, not testable). No fork of the store: the
     new CLI imports Store the same way bm_learn.py does. Flip condition:
     if bm_project.py ever needs its own SQL, it has become a second
     writer and must be folded back.
D-2. Read accessors land in bm_store.py on Store AND ReadOnlyStore:
     get_project, list_projects, list_tasks(project_id, status=None),
     get_task, list_forecasts(project_id), latest_forecast(project_id),
     list_alerts(resolved=None), list_evidence(subject_type, subject_id),
     list_attribution(project_id, limit). Redaction: same export_column
     policy as dump(); no new disclosure surface.
D-3. Command files stay the model-facing surface but every one now names
     the exact mechanical command(s) to run and forbids answering from
     memory of the conversation: start -> `bm_project.py start` (creates
     the projects row + first tasks + forecast through the service
     layer); status -> `bm_project.py status` (rows only); next ->
     `bm_project.py next` (dependency-and-state computed suggestion);
     review -> `bm_project.py review <task>` (evidence recorded, state
     moved through schema.transition); deliver -> `bm_project.py deliver`
     (delivery packet generated FROM rows); update stays the pinned
     git ls-remote flow; help unchanged except it now states the store is
     the source of truth. CANVAS.md and DELIVERY-PACKET.md become
     GENERATED views written by start/deliver, never read as truth.
D-4. The gate is executable: tools/test_bm_project.py includes
     test_scripted_first_project_end_to_end, driving all seven command
     surfaces through subprocess against a temp root, asserting rows,
     attribution for every mutation, and that CANVAS.md regenerates
     byte-stable from rows.

## Work packages (serial, one writer at a time; refuters read-only)

WP-A: bm_store.py read accessors + their tests (test_bm_store.py).
WP-B: tools/bm_project.py + tools/test_bm_project.py + test_all wiring.
WP-C: commands/*.md, skills/brotherme/SKILL.md, project-template notes,
      test_bm.py command-wiring tests updated, docs regenerated if the
      docs engine requires it.

Verification: after WP-C, read-only refuters with distinct lenses
(correctness of the end-to-end script's assertions; beginner-register
compliance of every user-facing sentence; privacy: no new unredacted
surface). Findings fixed by the active implementer, never by reviewers.

## Out of scope

Consent/install (Loop 3), forecasting content beyond storing what start
collects (Loop 5 owns derived numbers), runtime adapters (Loop 7).
