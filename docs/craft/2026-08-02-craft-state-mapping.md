# Craft state mapping: every proposed record against the store that exists

Status: CURRENT. This is brief C1 of the Product Craft program, the second and
last craft artifact permitted before the program's start conditions hold (see
docs/craft/FABLE-PRODUCT-CRAFT-RESEARCH-REVIEW.md, sections G and H). Written
2026-08-02 by Fable 5 (session 02f14e48, work record e33a240d). Docs only; no
code, no migration, no schema change happens in this brief.

Ground truth: tools/bm_store.py at release/2.0-final commit 502871da
(SCHEMA_VERSION = 12 at line 76). The branch has moved since (4116d3a at
writing time) and moves again before C2; every line number and decision here
is RE-DERIVED against the tree that exists when C2 starts. A mapping decision
contradicted by that re-derivation stops C2 until this document is amended.

## The rule this document enforces

Release-closure amendment A3, applied to craft: integration, not reinvention.
No table is created twice; nothing becomes a second source of truth. The
plan's section 8.5 proposed eleven craft tables; this mapping lands the same
information in THREE new tables, one extended table, and five reuse decisions.

## The mapping, record by record

Plan record (section 9.x) to store decision:

1. Craft Brief (9.1): CREATE, into craft_records (type brief).
2. Experience Reference (9.2): CREATE, into craft_provenance (kind reference).
3. Journey Spec (9.3): CREATE, into craft_records (type journey).
4. Brand Direction (9.4): CREATE, into craft_records (type direction).
5. Design System Version (9.5): CREATE, into craft_records (type
   system_version).
6. Component Record (9.6): CREATE, into craft_records (type component).
7. Screen Spec (9.7): CREATE, into craft_records (type screen_spec).
8. Motion Spec (9.8): CREATE, into craft_records (type motion_spec).
9. Localization Context (9.9): CREATE, into craft_messages (its access
   pattern differs: per-message lookup by semantic id, per-locale review
   state, screenshot linkage; folding it into craft_records would force
   payload parsing on every message query).
10. Media Asset (9.10): CREATE, into craft_provenance (kind media_asset;
    same provenance discipline as references, plus consent_status,
    rights_note and cost columns that stay empty for plain references).
11. Visual Evidence (9.11): EXTEND the existing evidence table.
12. Craft Review (9.12): CREATE, into craft_records (type review), with the
    verdict and severity counts in the payload and the review's own
    supersession chain through the shared supersedes_id column.

Net new tables: craft_records, craft_provenance, craft_messages. Extended:
evidence. Everything else is reuse.

## The three new tables, shaped by the store's own conventions

craft_records: record_id, project_id, lifecycle_id, record_type (CHECK list
fixed at migration time: brief, journey, direction, system_version,
component, screen_spec, motion_spec, review), version, status (CHECK:
draft, proposed, approved, rejected, superseded), payload (validated JSON,
schema per record_type enforced in the service layer, exactly as forecasts
stores assumptions as JSON at bm_store.py:2031), content_hash,
supersedes_id, approved_by, approved_at, created_at, actor.

craft_provenance: provenance_id, project_id, lifecycle_id, kind (CHECK:
reference, media_asset), source, source_uri, retrieved_at, source_version,
license_note, input_hash, output_hash, transformation, consent_status,
rights_note, cost_note, approved_by, linked_task_id, final_usage, status,
created_at, actor.

craft_messages: message_id (semantic, unique per project and lifecycle),
project_id, lifecycle_id, source_locale, source_text, meaning, product_area,
screen_record_id, constraints (JSON: variables, plurals, character limits),
screenshot_evidence_id, target_locales (JSON), maturity (CHECK: machine_draft,
model_reviewed, human_reviewed, domain_approved, in_context_approved),
review_status, created_at, actor.

Design consequences accepted knowingly:

- One craft_records table with a type column, not eight tables. The store's
  own precedent cuts both ways (v11 to v12 added eight per-entity shape
  tables), but the craft record types share an identical lifecycle (version,
  status, supersession, approval, hash) and differ only in payload; eight
  tables would copy the same seven columns eight times. The CHECK list on
  record_type is fixed at migration time on purpose: adding a type is a
  migration, visible in the chain, never a silent widening. This is the same
  wall the refuters proved on notes.kind (CHECK cannot be altered in
  SQLite, bm_store.py comment near line 1875), accepted here as a feature.
- Every new table carries project_id AND lifecycle_id directly. Lifecycle
  isolation (INVARIANTS.md I3) is a column filter, never a join guess.

## The one extension: evidence

The generic evidence table (bm_store.py:2099, columns evidence_id,
subject_type, subject_id, kind, ref, note, created_at) lacks every field the
review's section I requires for visual evidence and has no dedup key. C2
adds, additively: commit_sha, environment, viewport, theme, locale, ui_state,
motion_preference, content_hash, all defaulting to empty so existing rows
and existing writers are untouched, plus one partial unique index on
(subject_type, subject_id, kind, content_hash) WHERE content_hash != '' so a
retried screenshot capture cannot double-record (exactly-once, INVARIANTS.md
I2). Deduplication logic is net-new service code, not a property the table
grants by itself.

## The five reuse decisions, each with its isolation path stated

- alerts (bm_store.py:2088): REUSE for craft alerts. The table has NO
  project_id column; isolation is by the category convention
  craft:<project_id>:<cause> and the resolve path already deduplicates by
  cause. This is stated, not assumed; if the release program ever adds a
  project column to alerts, craft rows adopt it in the same migration.
- forecasts (bm_store.py:2021): REUSE unchanged for craft loop forecasts;
  it already carries project_id and ranges with confidence and assumptions.
- decisions plus the receipt lane: REUSE for founder approvals (direction
  selection, scope approval, media consent). The receipt-gated pattern that
  guards rule promotion is the model; C2 wires craft approvals through the
  same one-time receipt shape rather than inventing a parallel approval
  table. Isolation: decisions rows name the craft record id in their body;
  the approving receipt references the exact record version hash.
- runtime_runs (bm_store.py:2108): REUSE for capability checks (review
  section E.2). One row per surface probe: runtime, suite set to
  craft-capability:<surface>, result set to the section 8.9 label,
  evidence_ref pointing at the probe evidence. No new table until real
  usage proves this shape too small.
- notes: REUSE strictly within its existing CHECK lists (kind insight,
  alert, question, review, todo, risk; anchor_type file, candidate, rule,
  record, decision). No new kinds. A craft observation that fits none of
  these goes into craft_records payloads or nowhere.

## Redaction, classified before the first export

The export funnel is default-deny (verified by the refuter pass: unlisted
columns are withheld). Classification for the new columns, to land in
_DUMP_SAFE_COLUMNS in the same C2 change as the tables:

- Safe (ids, enums, timestamps, hashes): record_id, project_id,
  lifecycle_id, record_type, version, status, content_hash, supersedes_id,
  created_at, approved_at, kind, maturity, review_status, retrieved_at,
  message_id, and the evidence extension's viewport, theme, locale,
  ui_state, motion_preference, commit_sha, environment, content_hash.
- Scrub-only or withheld (founder prose and provider content): payload,
  source_text, meaning, source_uri, license_note, rights_note,
  transformation, cost_note, final_usage. Brand theses and audience truths
  are the founder's private thinking and never leave the machine unredacted.

## Migration shape

_migrate_12_to_13, additive only: three CREATE TABLE IF NOT EXISTS, the
evidence ALTER TABLE ADD COLUMN set, one partial unique index, plus the
craft entries in _TABLES_BY_VERSION and the redaction lists. Backup first,
one exclusive transaction, version bump last: the existing _migrate_from
mechanism (bm_store.py:4836) provides all three and rolls back whole on
interruption, proven by the refuter pass. Rollback for C2 is the backup the
mechanism itself writes.

## Generated views

DESIGN.md and the design/ views render through the same marker-splice
pattern as STATE.md and CANVAS.md (_splice_generated, bm_project.py:324):
disposable, rebuildable byte-stable from the store, redaction funnel
applied. Deleting any generated craft view and regenerating it must produce
equivalent content; that is a C2 test, not a hope.

## Delete-list

Empty. No craft bookkeeping predates this program; there is nothing to
retire.

## What this mapping deliberately does not decide

- Exact JSON payload schemas per record_type: C2 design, validated in the
  service layer with malformed-payload tests.
- The felt shape of capability probing (which tool surfaces, what counts as
  reachable): C2 design per review E.2.
- Whether craft_messages needs its own screenshot table at scale: deferred
  until a real multi-locale project exists.

## SBE design checks

Run against this dossier at authoring time; the verdict is quoted in the
session log and the pull request. Where the tooling reports NO-DATA because
the dossier lacks its intake shape, that is disclosed as NO-DATA, never
dressed up as a pass; the full SBE dossier lands with C2, where the tier is
computed from real intake answers.

## Fable acceptance

Accepted by Fable 5 on 2026-08-02 as the C1 artifact required by start
condition 3, on these terms: the mapping holds at the pinned commit; C2
re-derives every citation before writing code; any contradiction stops C2.
Start conditions 1 (release program ended, 2.0.0 tagged) and 2 (founder
scope approval) remain open and are the founder's alone.
