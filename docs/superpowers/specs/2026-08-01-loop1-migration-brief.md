# Loop 1 migration brief: schema 11 to 12, the five shapes get their tables

Status: CURRENT. Written 2026-08-01 by the orchestrator (Fable), gated by
docs/superpowers/specs/2026-08-01-loop1-state-mapping.md. Implementer: one
Builder-profile agent. Reviewer: Fable (never the writer, per the ratified
separation of duties).

## Verified facts the brief relies on

- brotherme/core/schema.py append_event/read_events have ZERO callers
  outside schema.py itself, and no .jsonl shape-event files exist anywhere
  in the tree (grep + find, 2026-08-01). REPLAY IS THEREFORE A NO-OP and
  no replay code ships. The mapping doc's "create + replay" rows collapse
  to "create".
- Store schema is version 11; migrations are chained additive functions
  in _MIGRATIONS (bm_store.py:2313), each running inside
  Store._migrate_from's BEGIN EXCLUSIVE. Latest example: _migrate_10_to_11
  with _LOOP4_DDL (bm_store.py:1880 onward).
- The CHECK-constraint wall is real and named repeatedly in bm_store.py
  comments (schema 9, 10, 11 all hit it): SQLite cannot alter a CHECK
  without a table rebuild.

## The change

Schema version 11 becomes 12. One new DDL block (_LOOP1_DDL), eight
tables, ADDITIVE ONLY, CREATE TABLE IF NOT EXISTS, no ALTER on any
existing table:

- projects: one column per Project.FIELDS (schema.py:247), TEXT
  throughout, project_id PRIMARY KEY, LIST_FIELDS stored as JSON arrays
  in TEXT.
- forecasts: per Forecast.FIELDS, forecast_id PRIMARY KEY, project_id
  REFERENCES projects(project_id).
- tasks: per Task.FIELDS, task_id PRIMARY KEY, project_id REFERENCES
  projects(project_id). depends_on stays a JSON list column AND is
  mirrored into the dependencies table by the service layer (the table is
  the queryable truth, the column is the shape's wire form).
- dependencies: task_id, depends_on_task_id, PRIMARY KEY(task_id,
  depends_on_task_id), both REFERENCES tasks(task_id).
- attribution: per AttributionEvent.FIELDS, event_id PRIMARY KEY,
  project_id NOT NULL, task_id nullable. Append-only: no UPDATE or DELETE
  path exists in the service layer.
- alerts: per Alert.FIELDS, alert_id PRIMARY KEY, requires_human INTEGER
  0/1, resolved_at nullable.
- evidence: evidence_id TEXT PRIMARY KEY, subject_type TEXT NOT NULL,
  subject_id TEXT NOT NULL, kind TEXT NOT NULL DEFAULT '', ref TEXT NOT
  NULL DEFAULT '', note TEXT NOT NULL DEFAULT '', created_at TEXT NOT
  NULL. records.evidence column is UNTOUCHED.
- runtime_runs: run_id TEXT PRIMARY KEY, runtime TEXT NOT NULL, suite
  TEXT NOT NULL DEFAULT '', started_at TEXT NOT NULL, finished_at TEXT,
  result TEXT NOT NULL DEFAULT '', evidence_ref TEXT NOT NULL DEFAULT ''.
  Empty at birth; Loop 7 writes into it.

NO CHECK constraints on any enum-like column (status, severity,
confidence, actor_type). Validation happens at the service layer through
the schema.py shapes, which already own the enums and the ten states.
This is the lesson of schemas 9 through 11, applied in advance.

## Service layer (same Store class, no second writer)

New methods on Store, each ONE transaction that writes the row AND its
attribution event together, both-or-neither:

- upsert_project(project_dict, actor) -> validates via schema.Project,
  writes projects row + attribution row (event_type 'project.upserted').
- add_forecast(forecast_dict, actor) -> append-only (never edits an old
  forecast), forecasts row + attribution row.
- create_task(task_dict, actor) -> tasks row + dependencies mirror rows +
  attribution row.
- transition_task(task_id, new_status, reason, actor) -> calls
  schema.transition() for legality (ten states, 'done' forbidden by
  name), updates tasks.status, attribution row. Illegal transition
  refuses; nothing is written.
- raise_alert(alert_dict, actor) / resolve_alert(alert_id, actor) ->
  alerts row + attribution row.
- add_evidence(evidence_dict, actor) -> evidence row + attribution row.
- record_runtime_run(run_dict, actor) -> runtime_runs row + attribution
  row.

actor is a small dict (actor_type, actor_name, session_id, runtime,
model) validated against AttributionEvent's enums. Import schema.py the
same way tools/test_bm_schema.py does; bm_store stays stdlib-only and
subprocess-free.

## Tests (tools/test_bm_store.py, same suite, same idioms)

1. Migration: a real v11 store opens at v12 with all eight tables; a
   fresh store creates at v12 directly; the existing mid-migration crash
   pattern (test_bm_store.py:854 area) extended to 11->12: a crash
   between DDL statements leaves the store recoverable and verify
   healthy after reopen.
2. Atomicity: force a failure after the entity write but before the
   attribution write (or vice versa) inside one method; assert NEITHER
   row exists after rollback. One such test per method family minimum.
3. Legality: transition_task refuses an illegal state move and the
   forbidden 'done' by name; nothing written on refusal.
4. Append-only: no service method mutates an existing attribution or
   forecasts row.
5. verify() extended: attribution rows referencing a missing project or
   task are reported as problems; the eight tables' existence is part of
   the v12 schema check.

## Done-check (the builder runs this and pastes the tail)

python3 tools/test_all.py exits 0, ALL GREEN, and
python3 tools/bm_store.py verify prints "healthy".

## Out of scope for this brief

schema.py edits (the JSONL stream retirement is a separate brief),
threads/ rewires, STATE.md prose archive, beginner commands. A needed
change to any file outside tools/bm_store.py and tools/test_bm_store.py
is REPORTED back, never edited.
