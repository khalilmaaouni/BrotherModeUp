# Loop 1 state mapping: every state system, its target, and what dies

Status: CURRENT. Written 2026-08-01, Loop 1 of the release-closure program
(docs/superpowers/specs/2026-08-01-release-closure-program-ratified.md,
amendment A3: integration, not reinvention). Work record
loop1-state-unification, lifecycle 18620ddf4cd446c282be87dc43e60c91.

This is the mapping document A3 requires BEFORE any migration lands: for
every piece of durable state, its existing home, its target in the one
SQLite store, whether the move is a migration, a rename, or a retirement,
and the delete-list for parallel bookkeeping. No table is created twice.
Nothing in this file changes code; it gates the migration briefs that do.

## 1. Inventory: the four overlapping state systems (verified today)

S1. SQLite store `.brothermode/store.sqlite3` (tools/bm_store.py, schema
    version 11). Tables, from the DDL at bm_store.py:1166 onward: meta,
    records, claims, decisions, digests, directives, transitions,
    autosave_receipts, handovers, notes, provisional_records, and the ten
    learning_* tables (rules, candidates, rule_versions, evidence, edges,
    applications, approval_receipts, state_change_receipts,
    retrieval_runs, retrieval_membership).
S2. Canonical object schema brotherme/core/schema.py: five shapes
    (Project, Forecast, Task, AttributionEvent, Alert), ten states with
    LEGAL_TRANSITIONS, and its OWN JSONL event stream (append_event /
    read_events). These objects have no tables yet; they live only as
    JSONL events wherever a caller pointed them.
S3. JSONL telemetry `outcomes.jsonl`, hook-written by bm_telemetry.py at
    SessionEnd. Feeds the weekly review.
S4. Markdown and JSON registries: STATE.md (292 lines of hand-written
    wave-era fence prose above the generated block), threads/registry.json
    plus threads/thread-mode.json (V1 registry leftovers, still read by
    bm_threads.py, bm_telemetry.py, test_bm.py, verified by grep today),
    and the Kay Vault session logs (out of scope: the vault is memory,
    not project state, per references/memory.md).

## 2. The mapping table

Target store is S1, the existing store. The service layer is the existing
`Store` class; new tables get methods on it, never a second writer. Every
mutation lands in ONE transaction together with its attribution row
(program ADR: state change and attribution are inseparable).

| Source (today) | Target table | Move | Notes |
|---|---|---|---|
| schema.py Project shape (JSONL events only) | projects (NEW) | migration: create table, replay any existing project JSONL | source doc section 8 table; shape validation stays in schema.py, storage moves here |
| schema.py Forecast shape | forecasts (NEW) | migration: create + replay | every displayed forecast number must trace to a row (Loop 5 gate depends on this) |
| schema.py Task shape | tasks (NEW) | migration: create + replay | tasks are beginner-surface work items; NOT a rename of records (see below) |
| (none today) | dependencies (NEW) | create | source doc table; empty at birth |
| schema.py AttributionEvent shape | attribution (NEW) | migration: create + replay | store transitions table stays for record (fence) history; attribution covers the five shapes |
| schema.py Alert shape | alerts (NEW) | migration: create + replay | |
| (scattered: records.evidence column, prose in docs/evidence/) | evidence (NEW) | create; records.evidence column STAYS | records.evidence is fence-close evidence and remains; the new table is task and delivery evidence with a row per artifact |
| (none today) | runtime_runs (NEW) | create | Loop 7 writes into it; created now so Loop 7 adds no schema |
| store records + claims + transitions | records, claims, transitions | none, survives | the ownership and fence ledger; already the single writer path |
| learning_* (ten tables) | unchanged | none, survives | A4: load-bearing machinery, no blocker names it |
| autosave_receipts, handovers, notes, decisions, digests, directives, meta, provisional_records | unchanged | none, survives | |
| schema.py JSONL event stream (append_event / read_events) | store event ingestion | retire after replay | the functions become an import shim that writes through the Store, then delete once no caller remains (grep gate) |
| outcomes.jsonl (S3) | unchanged this loop | none, survives | hook-written telemetry; ingestion into the store is NOT a release blocker, stays JSONL |
| STATE.md hand-written waves (lines above the marker) | none | archive + delete | verbatim copy to docs/evidence/2026-08-01-state-md-wave-era.md, then STATE.md becomes a short prose header plus the generated block |
| threads/registry.json, thread-mode.json, store-engine | none | rewire then delete | bm_threads.py, bm_telemetry.py, test_bm.py still read them (grep, today); each reader moves to the store FIRST, then the files go; a blind delete is refused |

## 3. The delete-list (parallel bookkeeping that must end this loop)

D1. STATE.md wave prose (lines 1-292 today): archived verbatim, then cut.
D2. threads/ directory: after the three readers are rewired to the store.
D3. schema.py JSONL stream: after replay into the new tables and a grep
    for callers returns only the shim.
D4. Stale store rows, dispositioned through the service layer (complete
    or cancel with a note), never SQL-deleted: the '--help' active
    ephemeral record (CLI defect artifact, defect class already fixed in
    the 2026-07-30 fence sweep), 'land-ledger-cut-rc8-upgrade-live'
    (rc.8-era, superseded by the release-closure program), the four
    stale provisional records from sessions 17838b98 and eb70addd
    (dummies-book-revival, finish-and-ship-rc10,
    help-artifact-and-explainer-v2, loop0-release-truth), and the
    superseded first claim of this very record (19f8ca253de146ec9dcac4248441c8fc,
    adopted after a session-id mismatch; its successor is
    18620ddf4cd446c282be87dc43e60c91). Founder sees this list in Founder
    Report 2 before disposition.

## 4. What this loop does NOT touch

Learning store, telemetry hooks, fence hook, autosave, docs engine (A4).
The vault. outcomes.jsonl. No beginner-command work (that is Loop 2).

## 5. Gate restated

Loop 1 closes when: crash tests recover; `bm_store.py verify` healthy;
no second source of truth remains (the delete-list executed); every
mutation of the five shapes goes through the Store in one transaction
with attribution. Evidence quoted in Founder Report 2.
