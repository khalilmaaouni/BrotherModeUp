# BrotherMode V2 Correction Learning Execution Plan

**Target executor:** Claude Code Opus 5  
**Repository:** `khalilmaaouni/BrotherModeUp`  
**Target branch:** `v2`  
**Plan status:** Execution-ready specification  
**Primary objective:** Make BrotherMode the strongest local, evidence-driven operating system for a solo founder by implementing trustworthy correction learning without weakening its simplicity, privacy, or founder ownership.

---

## 0. Instructions to Claude Code Opus 5

You are executing a staged engineering program inside BrotherMode V2. Do not treat this file as a list of suggestions. Treat each numbered loop as an independently verifiable increment.

### 0.1 Execution contract

For every loop:

1. Read the named source files before proposing code.
2. Confirm the current branch, commit, working tree status, and test baseline.
3. Write a brief implementation note naming:
   - the defect class or missing capability;
   - the invariant being introduced;
   - the files you expect to modify;
   - the tests that will prove the change.
4. Claim the files through BrotherMode before writing when the installed workflow supports it.
5. Implement the smallest complete vertical slice.
6. Run deterministic tests before asking an agent or model to judge anything.
7. Calibrate new tests whenever practical:
   - prove the test passes with the fix;
   - temporarily reinject the old defect or disable the new guard;
   - prove the test fails for the intended reason;
   - restore the fix;
   - prove it passes again.
8. Run the full regression suites at the loop close.
9. Update documentation and known limits in the same loop when behavior changes.
10. Commit one loop at a time. Do not mix unrelated loops into one commit.
11. Produce the loop-close report defined in section 0.4.
12. Stop after a failed gate. Do not continue and hide the failure inside later work.

### 0.2 Non-negotiable architecture constraints

The implementation must preserve all of the following unless the founder explicitly changes the scope:

- `tools/bm_store.py` remains the only writer of `.brothermode/store.sqlite3`.
- SQLite remains the canonical local source of truth.
- The production core remains Python standard library only.
- The core makes no network calls.
- No Docker, PostgreSQL, Bun, Chroma, Node runtime, external service, cloud account, or API key becomes mandatory.
- The system remains optimized for a solo founder or individual contributor, not for enterprise or distributed-team governance.
- The founder owns the constitution. An acting session may propose a constitutional amendment but may not approve or land one automatically.
- A correction candidate is not an approved rule.
- Silence is not confirmation.
- A model-generated confidence score is not evidence.
- Any free text added to the SQLite schema is sensitive by default and must remain covered by the existing default-deny dump redaction.
- Every new path written inside a project must pass through the existing safe project path mechanism.
- Every new mutation must be transactional, version-aware where concurrent updates matter, and explicit about fail-closed versus advisory behavior.
- Existing safety invariants, ownership guarantees, autosave behavior, and cross-platform tests must not regress.
- The learning system must degrade safely when optional full-text search is unavailable.
- The learning system must never block ordinary work because a non-critical analytics or retrieval feature failed. Approval, ownership, corruption, schema, or security checks may fail closed where the specification says they must.

### 0.3 Source files that define current truth

Read these before Loop 0 and re-read relevant files at each loop:

- `README.md`
- `SKILL.md`
- `DIGEST.md`
- `SECURITY.md`
- `RUBRIC.md`
- `tools/bm_store.py`
- `tools/bm_telemetry.py`
- `tools/bm_score.py`
- `tools/bm_sessionstart.sh`
- `tools/bm_threads.py`
- `tools/bm_autosave.py`
- `tools/test_bm.py`
- `tools/test_bm_store.py`
- `tools/WEEKLY-REVIEW.md`
- `docs/KNOWN-LIMITS.md`
- `docs/HOW-IT-WORKS.md`
- `docs/SETUP.md`
- `docs/QUICKSTART.md`
- `docs/superpowers/specs/2026-07-26-self-learning-redesign.md`
- `docs/superpowers/specs/2026-07-26-release-blockers.md`

The current baseline includes a V2 transactional store in WAL mode, immutable lifecycle UUIDs, expected-version guards, conservative file overlap detection, default-deny dump redaction, safe project path handling, autosave receipts, session telemetry, correction-candidate scanning, and two regression suites. The self-learning redesign is approved in principle but explicitly not implemented.

### 0.4 Required loop-close report

At the end of every loop, report exactly:

```text
LOOP <number> CLOSE
Status: PASS | PARTIAL | FAIL
Commit: <sha or NOT COMMITTED>
Files changed:
- ...

Invariant added or strengthened:
- ...

Verification run:
- <command> -> <result>
- <command> -> <result>

Calibration performed:
- <test name>: pass -> reinjected defect fails -> restored pass
or
- NOT PERFORMED: <specific reason>

Remaining:
- ...

Unverified:
- ...

Known limits changed:
- yes/no; <details>
```

No success claim is valid without fresh command output from the current loop.

---

# 1. Product position and design goal

BrotherMode should not compete by accumulating the largest number of agents, commands, skills, databases, or services. Its defensible position is:

> A local, evidence-driven operating system for a solo founder's AI work that remembers corrections, retrieves the right rule at the right time, proves whether the rule helped, and never changes the founder's constitution without permission.

The correction-learning system must distinguish five separate questions:

1. **Capture:** Did the founder provide a correction or reveal a preference?
2. **Interpretation:** What narrow trigger, action, and reason does the evidence support?
3. **Approval:** Has the founder approved that interpretation as a rule?
4. **Application:** Was the rule retrieved and followed when relevant?
5. **Outcome:** Did following or ignoring the rule lead to rework, an escaped defect, acceptance, or another correction?

Most competing systems combine several of these into one opaque claim that the agent "learned." BrotherMode must keep them separate and auditable.

---

# 2. Target architecture

## 2.1 Three-layer precedence model

Implement three separate layers with strict precedence.

### Layer A: Constitution

Source:

- `SKILL.md`
- its extracted references;
- immutable founder-approved principles.

Properties:

- highest precedence;
- founder-owned;
- cannot be automatically edited;
- can only be amended through a founder-approved proposal plus regression checks;
- may define hard gates, safety floors, and general working law.

### Layer B: Approved founder model

Source:

- structured learned rules stored in `.brothermode/store.sqlite3`;
- each rule has an atomic trigger, observable action, founder reason, scope, provenance, lifecycle state, version history, and application history.

Properties:

- can shape behavior when relevant;
- cannot override Layer A;
- can be narrowed, contradicted, superseded, deprecated, or forgotten;
- must be founder-approved before normal application;
- can be project-specific, domain-specific, artifact-specific, relationship-specific, tool-specific, or global.

### Layer C: Observations and candidates

Source examples:

- explicit corrections;
- automatically detected correction-shaped messages;
- rework;
- escaped defects;
- founder selection among options;
- verified successful procedures;
- manual rewrites;
- imported community rules;
- contradictory evidence.

Properties:

- never injected as settled truth;
- never auto-promoted to approved rules;
- can be reviewed, merged, split, rejected, or attached as supporting/contradicting evidence;
- raw text remains sensitive and redacted at every non-private output boundary.

## 2.2 Core data flow

```text
Founder message or external outcome
        |
        v
Candidate capture with immutable source reference
        |
        v
Deterministic deduplication and nearby-rule lookup
        |
        v
Founder review: approve / edit / split / merge / reject
        |
        v
Versioned approved rule in transactional store
        |
        v
Task-time retrieval with scope and relevance ranking
        |
        v
Application record: shown / applied / ignored / unknown
        |
        v
External outcome: accepted / rework / escaped defect / correction
        |
        v
Rule evaluation: useful / retrieval miss / compliance failure /
bad rule / contradiction / not decidable
        |
        v
Optional constitutional amendment proposal, never automatic landing
```

## 2.3 Learning states

Do not use unsupported decimal confidence as the primary truth. Use evidence states.

### Candidate states

- `pending`
- `under_review`
- `approved`
- `merged`
- `split`
- `rejected`
- `expired`

### Rule states

- `approved`: explicitly approved by the founder.
- `confirmed`: approved plus at least one independent supporting event.
- `settled`: repeatedly applied with supporting outcomes and no unresolved contradiction.
- `contradicted`: material conflicting founder evidence exists; normal auto-injection is suppressed.
- `deprecated`: intentionally retired but retained for history.
- `superseded`: replaced by a named newer rule.
- `forgotten`: tombstoned at the founder's request; excluded from retrieval and normal output.

No transition into `approved`, `confirmed`, or `settled` may be based only on an acting model's judgment.

---

# 3. Proposed file layout

Use the existing store as the only mutation boundary. Recommended files:

```text
tools/
  bm_store.py                 # schema, migrations, transactional learning methods
  bm_learn.py                 # learning CLI and hook entrypoints; no direct DB writes
  bm_learning.py              # pure parsing, normalization, ranking, conflict helpers
  bm_eval.py                  # deterministic replay and partition checks
  test_bm_store.py            # store-level schema and transaction tests
  test_bm_learning.py         # learning domain, CLI, retrieval, and outcome tests
  test_bm.py                  # hook and integration tests

docs/
  CORRECTION-LEARNING.md      # user and operator reference
  LEARNING-SCHEMA.md          # schema and lifecycle reference
  LEARNING-EVALUATION.md      # replay, partitions, and limits
  knowledge/
    LESSONS.md                # generated view, never source of truth
    TOOLBOX.md                # generated view, never source of truth
```

If adding three production Python files is judged unnecessary, `bm_learning.py` may be folded into `bm_learn.py`. Do not fold all logic into `bm_store.py`; keep the store readable and preserve its role as mutation boundary rather than turning it into every user-facing workflow.

---

# 4. Proposed SQLite schema version 2

## 4.1 Migration policy

- Increment `SCHEMA_VERSION` from `1` to `2`.
- Add an explicit migration path from schema 1 to schema 2.
- Never rebuild the database by copying only parsed rows.
- Back up the raw database files before migration using SQLite-safe mechanics.
- Run migration inside an exclusive transaction.
- Keep migration idempotent.
- Verify required tables, columns, indexes, triggers, and metadata after migration.
- Refuse to open a store whose schema is newer than the binary.
- Refuse a partially migrated schema rather than guessing.
- Test migration from a real schema-1 fixture.
- Test interruption and rollback.
- Test Windows handle closure.

## 4.2 Core tables

The final SQL may be adapted to existing store conventions, but the semantics below are required.

### `learning_candidates`

```sql
CREATE TABLE learning_candidates (
  candidate_uuid TEXT PRIMARY KEY,
  source_type TEXT NOT NULL CHECK(source_type IN (
    'explicit_correction',
    'detected_correction',
    'rework',
    'escaped_defect',
    'revealed_choice',
    'verified_procedure',
    'manual',
    'imported'
  )),
  source_session_id TEXT NOT NULL DEFAULT '',
  source_record_uuid TEXT,
  source_ref TEXT NOT NULL DEFAULT '',
  raw_text TEXT NOT NULL DEFAULT '',
  proposed_trigger TEXT NOT NULL DEFAULT '',
  proposed_action TEXT NOT NULL DEFAULT '',
  proposed_because TEXT NOT NULL DEFAULT '',
  proposed_domain TEXT NOT NULL DEFAULT '',
  proposed_scope_type TEXT NOT NULL DEFAULT 'project' CHECK(proposed_scope_type IN (
    'global', 'project', 'domain', 'artifact', 'relationship', 'tool'
  )),
  proposed_scope_key TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN (
    'pending', 'under_review', 'approved', 'merged', 'split', 'rejected', 'expired'
  )),
  content_hash TEXT NOT NULL,
  redaction_count INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  reviewed_at TEXT,
  review_note TEXT NOT NULL DEFAULT '',
  resulting_rule_uuid TEXT,
  FOREIGN KEY(source_record_uuid) REFERENCES records(lifecycle_uuid),
  FOREIGN KEY(resulting_rule_uuid) REFERENCES learning_rules(rule_uuid)
);
```

Required indexes:

```sql
CREATE INDEX learning_candidates_status_idx
  ON learning_candidates(status, created_at);
CREATE INDEX learning_candidates_source_idx
  ON learning_candidates(source_session_id, source_type);
CREATE INDEX learning_candidates_hash_idx
  ON learning_candidates(content_hash);
```

Do not use a global unique constraint on `content_hash`; the same words in two different scopes may be distinct evidence. Deduplicate through explicit logic using source, scope, and normalized content.

### `learning_rules`

```sql
CREATE TABLE learning_rules (
  rule_uuid TEXT PRIMARY KEY,
  current_version INTEGER NOT NULL DEFAULT 1,
  state TEXT NOT NULL CHECK(state IN (
    'approved', 'confirmed', 'settled', 'contradicted',
    'deprecated', 'superseded', 'forgotten'
  )),
  rule_type TEXT NOT NULL DEFAULT 'preference' CHECK(rule_type IN (
    'preference', 'procedure', 'safety', 'communication',
    'tooling', 'quality', 'delegation', 'decision_right'
  )),
  severity TEXT NOT NULL DEFAULT 'soft' CHECK(severity IN ('soft', 'gate')),
  scope_type TEXT NOT NULL CHECK(scope_type IN (
    'global', 'project', 'domain', 'artifact', 'relationship', 'tool'
  )),
  scope_key TEXT NOT NULL DEFAULT '',
  founder_approved_at TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  superseded_by TEXT,
  forgotten_at TEXT,
  FOREIGN KEY(superseded_by) REFERENCES learning_rules(rule_uuid)
);
```

### `learning_rule_versions`

```sql
CREATE TABLE learning_rule_versions (
  rule_uuid TEXT NOT NULL REFERENCES learning_rules(rule_uuid) ON DELETE CASCADE,
  version INTEGER NOT NULL,
  trigger_text TEXT NOT NULL,
  action_text TEXT NOT NULL,
  because_text TEXT NOT NULL,
  domain TEXT NOT NULL DEFAULT '',
  tags_json TEXT NOT NULL DEFAULT '[]',
  change_type TEXT NOT NULL CHECK(change_type IN (
    'created', 'edited', 'narrowed', 'broadened',
    'contradiction_resolution', 'restored'
  )),
  change_reason TEXT NOT NULL DEFAULT '',
  source_candidate_uuid TEXT,
  approved_by TEXT NOT NULL DEFAULT 'founder',
  created_at TEXT NOT NULL,
  PRIMARY KEY(rule_uuid, version),
  FOREIGN KEY(source_candidate_uuid) REFERENCES learning_candidates(candidate_uuid)
);
```

Never overwrite a prior rule version. `learning_rules.current_version` points to the current immutable version row.

### `learning_evidence`

```sql
CREATE TABLE learning_evidence (
  evidence_uuid TEXT PRIMARY KEY,
  rule_uuid TEXT REFERENCES learning_rules(rule_uuid) ON DELETE CASCADE,
  candidate_uuid TEXT REFERENCES learning_candidates(candidate_uuid) ON DELETE CASCADE,
  polarity TEXT NOT NULL CHECK(polarity IN ('support', 'contradict', 'neutral')),
  evidence_type TEXT NOT NULL CHECK(evidence_type IN (
    'founder_quote', 'founder_approval', 'revealed_choice',
    'rework', 'escaped_defect', 'verified_application',
    'ignored_application', 'manual_review', 'import_source'
  )),
  source_session_id TEXT NOT NULL DEFAULT '',
  source_record_uuid TEXT,
  source_ref TEXT NOT NULL DEFAULT '',
  excerpt TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  FOREIGN KEY(source_record_uuid) REFERENCES records(lifecycle_uuid),
  CHECK(rule_uuid IS NOT NULL OR candidate_uuid IS NOT NULL)
);
```

### `learning_edges`

```sql
CREATE TABLE learning_edges (
  from_rule_uuid TEXT NOT NULL REFERENCES learning_rules(rule_uuid) ON DELETE CASCADE,
  to_rule_uuid TEXT NOT NULL REFERENCES learning_rules(rule_uuid) ON DELETE CASCADE,
  relation TEXT NOT NULL CHECK(relation IN (
    'duplicate_of', 'contradicts', 'supersedes',
    'derived_from', 'supports', 'applies_to'
  )),
  note TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  PRIMARY KEY(from_rule_uuid, to_rule_uuid, relation),
  CHECK(from_rule_uuid <> to_rule_uuid)
);
```

### `learning_applications`

```sql
CREATE TABLE learning_applications (
  application_uuid TEXT PRIMARY KEY,
  rule_uuid TEXT NOT NULL REFERENCES learning_rules(rule_uuid),
  rule_version INTEGER NOT NULL,
  session_id TEXT NOT NULL,
  record_uuid TEXT,
  task_fingerprint TEXT NOT NULL DEFAULT '',
  task_excerpt TEXT NOT NULL DEFAULT '',
  retrieved_at TEXT NOT NULL,
  retrieval_rank INTEGER,
  retrieval_score REAL,
  scope_match TEXT NOT NULL DEFAULT '',
  shown_to_model INTEGER NOT NULL DEFAULT 0 CHECK(shown_to_model IN (0,1)),
  disposition TEXT NOT NULL DEFAULT 'unknown' CHECK(disposition IN (
    'followed', 'ignored', 'not_relevant', 'unknown'
  )),
  disposition_reason TEXT NOT NULL DEFAULT '',
  verification_ref TEXT NOT NULL DEFAULT '',
  outcome TEXT NOT NULL DEFAULT 'pending' CHECK(outcome IN (
    'pending', 'accepted', 'rework', 'escaped_defect',
    'corrected_again', 'not_decidable'
  )),
  outcome_ref TEXT NOT NULL DEFAULT '',
  closed_at TEXT,
  FOREIGN KEY(record_uuid) REFERENCES records(lifecycle_uuid),
  FOREIGN KEY(rule_uuid, rule_version)
    REFERENCES learning_rule_versions(rule_uuid, version)
);
```

### `learning_evaluation_cases`

```sql
CREATE TABLE learning_evaluation_cases (
  case_uuid TEXT PRIMARY KEY,
  partition TEXT NOT NULL CHECK(partition IN ('train', 'validation', 'test')),
  source_rule_uuid TEXT REFERENCES learning_rules(rule_uuid),
  source_candidate_uuid TEXT REFERENCES learning_candidates(candidate_uuid),
  prompt_text TEXT NOT NULL,
  expected_rules_json TEXT NOT NULL DEFAULT '[]',
  forbidden_rules_json TEXT NOT NULL DEFAULT '[]',
  deterministic_checks_json TEXT NOT NULL DEFAULT '[]',
  weight REAL NOT NULL DEFAULT 1.0,
  frozen_at TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
  content_hash TEXT NOT NULL UNIQUE
);
```

The partition is permanent. Once frozen, a case may be deactivated but never reassigned from validation/test into training.

### `learning_evaluation_runs`

```sql
CREATE TABLE learning_evaluation_runs (
  run_uuid TEXT PRIMARY KEY,
  started_at TEXT NOT NULL,
  ended_at TEXT,
  candidate_hash TEXT NOT NULL,
  baseline_hash TEXT NOT NULL,
  partition TEXT NOT NULL CHECK(partition IN ('validation', 'test')),
  status TEXT NOT NULL CHECK(status IN ('running', 'passed', 'failed', 'aborted')),
  score REAL,
  baseline_score REAL,
  regression_count INTEGER NOT NULL DEFAULT 0,
  reason TEXT NOT NULL DEFAULT ''
);
```

### `learning_evaluation_outcomes`

```sql
CREATE TABLE learning_evaluation_outcomes (
  run_uuid TEXT NOT NULL REFERENCES learning_evaluation_runs(run_uuid) ON DELETE CASCADE,
  case_uuid TEXT NOT NULL REFERENCES learning_evaluation_cases(case_uuid),
  passed INTEGER NOT NULL CHECK(passed IN (0,1)),
  score REAL NOT NULL,
  evidence TEXT NOT NULL DEFAULT '',
  PRIMARY KEY(run_uuid, case_uuid)
);
```

## 4.3 Optional FTS5 structures

FTS5 must be probed at runtime. If available, create an external-content or contentless index over the current active rule version. Do not duplicate source-of-truth fields without synchronization tests.

Recommended searchable fields:

- trigger;
- action;
- because;
- domain;
- scope key;
- tags.

If FTS5 is unavailable:

- report the capability as unavailable;
- use deterministic token overlap and exact phrase matching;
- do not fail normal BrotherMode startup;
- do not claim BM25 retrieval;
- include the fallback mode in diagnostics.

---

# 5. Global invariants for correction learning

Implement these as named invariants in code, tests, and documentation.

## L1. Founder approval owns promotion

No candidate becomes an approved rule unless an explicit founder approval action is recorded.

## L2. Constitution precedence

No learned rule may override or weaken an active constitutional gate. A conflict is surfaced for review and the constitutional rule wins until the founder changes it.

## L3. Atomic rule shape

Each rule has one trigger and one observable action. A compound candidate must be split or rejected.

## L4. Source provenance

Every approved rule has at least one immutable evidence row pointing to the source candidate and founder approval.

## L5. Scope isolation

A project-scoped rule is never retrieved in another project. A relationship-, artifact-, domain-, or tool-scoped rule is only eligible when the task context supplies a matching key.

## L6. Silence is not evidence

The absence of a correction never changes a rule state by itself.

## L7. No contradictory active injection

Two unresolved rules with overlapping trigger and scope but incompatible actions may not both be injected. The conflict must be suppressed and presented for review.

## L8. Immutable version history

Editing a rule creates a new version. Prior versions remain queryable and applications continue pointing to the version actually shown.

## L9. Retrieval is explainable

Every retrieved rule can explain why it was selected: scope, keyword/FTS match, state, and rank.

## L10. Applications are attributable

The system can distinguish retrieval failure, compliance failure, and bad-rule failure.

## L11. Evaluation partitions do not leak

Validation and test cases never become training inputs.

## L12. External outcomes grade the system

Rework, escaped defects, repeated corrections, founder approval, and real verification are stronger evidence than model self-ratings.

## L13. No automatic constitutional rewrite

An optimizer may generate a patch proposal only. It cannot write `SKILL.md` or approve the patch.

## L14. Sensitive by default

Every new text field is redacted from diagnostic dumps unless explicitly reviewed as structurally safe.

## L15. Optional features fail soft

FTS, analytics views, and learning summaries may degrade. Corrupt storage, untrusted migration state, approval violations, and security violations fail closed.

---

# 6. Execution loops

## Loop 0 - Establish repository truth and freeze the baseline

### Objective

Create a reproducible baseline before changing schema or behavior.

### Files to inspect

All files in section 0.3, plus CI workflow files under `.github/workflows/`.

### Actions

1. Confirm the `v2` branch and record the current commit SHA.
2. Run:

```bash
python3 tools/test_bm.py
python3 tools/test_bm_store.py
```

3. Record exact test counts, skips, duration, and platform.
4. Run the repository's documented network and subprocess checks.
5. Verify current schema version and list existing tables through a scratch project, not a real user project.
6. Exercise one complete scratch lifecycle:
   - init;
   - claim or thread start;
   - checkpoint;
   - park/off;
   - resume;
   - complete/adopt as applicable;
   - verify;
   - dump;
   - cleanup.
7. Confirm the current correction pipeline:
   - generate a transcript fixture containing a correction phrase;
   - run `bm_telemetry.py outcomes-append` through the existing test mechanism;
   - inspect the correction JSONL row;
   - prove it is only a candidate and not an applied rule.
8. Create `docs/superpowers/specs/<date>-correction-learning-baseline.md` containing:
   - commit;
   - test output;
   - schema tables;
   - current correction behavior;
   - known limits;
   - measurements used later for regression comparison.

### Tests to add

None unless the baseline exposes a missing test needed to state current truth. Do not begin feature work in this loop.

### Done gate

- Both existing suites pass.
- The baseline document contains exact command output.
- The current schema and correction behavior are reproduced, not inferred.
- Any baseline failure is resolved or explicitly blocks later loops.

### Commit

Documentation-only commit:

```text
Document correction-learning baseline before schema changes
```

---

## Loop 1 - Add schema version 2 and migration safety

### Objective

Add the learning tables without changing user-facing behavior.

### Primary files

- `tools/bm_store.py`
- `tools/test_bm_store.py`
- `docs/LEARNING-SCHEMA.md`
- `docs/KNOWN-LIMITS.md`

### Implementation steps

1. Define schema version 2.
2. Separate fresh-schema creation from versioned migration if the file currently assumes only one DDL shape.
3. Add a migration registry such as:

```python
_MIGRATIONS = {
    1: _migrate_1_to_2,
}
```

4. Make migration transactional and idempotent.
5. Add the tables and indexes from section 4.
6. Add schema verification for:
   - required tables;
   - required columns;
   - primary keys;
   - foreign keys;
   - check constraints where introspection is practical;
   - schema version metadata.
7. Extend `_TABLES` and any structural tests.
8. Review `_DUMP_SAFE_COLUMNS`:
   - do not add any new free-text field;
   - add only structural identifiers, enums, timestamps, numeric values, and hashes after explicit review;
   - prove every new unlisted text field is redacted.
9. Add `Store` methods for read-only schema diagnostics if needed, but do not add user-facing learning mutations yet.
10. Ensure every opened connection closes on all platforms.
11. Add a scratch schema-1 fixture and migrate it in tests.

### Required tests

- Fresh schema 2 contains every required table and index.
- Schema 1 migrates to schema 2 without losing existing rows.
- Running migration twice changes nothing.
- An interrupted migration rolls back completely.
- A newer unknown schema is refused clearly.
- A partially created learning table set is refused as corrupt/incomplete.
- Every new free-text column is redacted in dump output.
- Structural safe-column allowlist test fails if a new text column is accidentally marked safe.
- Store handles are closed after migration and test cleanup.
- Foreign keys are enabled and enforced.
- Windows-compatible cleanup remains green.

### Calibration

Temporarily remove one required table from the migrated fixture and prove schema verification fails. Restore it and prove pass.

### Done gate

- No user-facing learning command exists yet.
- Existing behavior is unchanged.
- Both legacy suites and new migration tests pass.
- Raw schema-1 data survives byte-for-byte where fields are not transformed.

### Commit

```text
Add transactional schema v2 for correction learning
```

---

## Loop 2 - Implement the learning store API

### Objective

Expose safe, typed, transactional methods through `Store` while keeping `bm_store.py` the only database writer.

### Primary files

- `tools/bm_store.py`
- `tools/bm_learning.py`
- `tools/test_bm_store.py`
- `tools/test_bm_learning.py`

### Required store methods

Names may follow project conventions, but capabilities must include:

```text
capture_learning_candidate(...)
get_learning_candidate(...)
list_learning_candidates(...)
review_learning_candidate(...)
approve_learning_candidate(...)
reject_learning_candidate(...)
create_learning_rule(...)
get_learning_rule(...)
list_learning_rules(...)
edit_learning_rule(...)
change_learning_rule_state(...)
add_learning_evidence(...)
add_learning_edge(...)
list_learning_edges(...)
record_learning_application(...)
close_learning_application(...)
create_evaluation_case(...)
list_evaluation_cases(...)
record_evaluation_run(...)
```

### Domain rules

1. Candidate UUIDs and rule UUIDs are full random UUIDs and never reused.
2. Candidate capture is append-only except for review status and review metadata.
3. Approval must atomically:
   - validate the candidate is reviewable;
   - create the rule;
   - create version 1;
   - create founder-approval evidence;
   - update candidate status and resulting rule UUID;
   - commit all or nothing.
4. Rejecting a candidate retains the evidence and rejection reason.
5. Editing a rule appends a version and updates `current_version` atomically.
6. A rule cannot enter `confirmed` or `settled` without named supporting evidence.
7. A rule cannot enter `contradicted` without a contradiction evidence row or edge.
8. A rule cannot enter `superseded` without a valid successor rule and `supersedes` edge.
9. Forgotten rules remain tombstoned for integrity but return no content through normal retrieval.
10. Any expected-version mismatch fails closed with a named stale identity/version error.

### Pure helper functions

In `tools/bm_learning.py`, implement and test pure functions for:

- whitespace and Unicode normalization without silently changing meaning;
- content hashes;
- candidate atomicity checks;
- scope validation;
- trigger tokenization;
- exact duplicate comparison;
- deterministic lexical similarity fallback;
- state transition validation;
- safe short display rendering;
- task fingerprinting that avoids storing full sensitive prompts when not necessary.

### Required tests

- Approval is atomic.
- Approval without explicit founder flag/ref is refused.
- Repeated approval does not create duplicate rules.
- Failed rule insertion leaves the candidate pending.
- Rule edits preserve earlier versions.
- Applications point to the exact version shown.
- Invalid state transitions are refused.
- Supersession requires a real successor.
- Forgetting suppresses text from normal reads.
- Raw text is redacted in dumps.
- Non-ASCII founder text round-trips correctly.
- Control characters are neutralized in generated displays.
- Concurrent edits with stale versions fail closed.
- Read-only methods do not mutate timestamps or state.

### Calibration

Monkeypatch or reinject the old non-atomic approval order: update candidate first, then fail rule creation. Prove the test detects the half-approved state. Restore transactional approval and pass.

### Done gate

The internal API can represent the full lifecycle but no automatic capture, retrieval hook, or founder CLI is active yet.

### Commit

```text
Add transactional learning lifecycle API
```

---

## Loop 3 - Build explicit correction capture and review CLI

### Objective

Provide a high-fidelity founder-controlled path from correction to approved rule.

### Primary files

- `tools/bm_learn.py`
- `tools/bm_learning.py`
- `tools/bm_store.py`
- `tools/test_bm_learning.py`
- `docs/CORRECTION-LEARNING.md`
- `docs/QUICKSTART.md`
- `docs/SETUP.md`

### CLI contract

Implement a discoverable command surface. Suggested commands:

```bash
python3 tools/bm_learn.py capture \
  --trigger "when writing an executive incident update" \
  --action "state customer and revenue impact before technical detail" \
  --because "leaders need the business state first" \
  --domain communication \
  --scope project \
  --source-session "$SESSION_ID"

python3 tools/bm_learn.py candidates
python3 tools/bm_learn.py show-candidate <candidate-id>
python3 tools/bm_learn.py approve <candidate-id>
python3 tools/bm_learn.py approve <candidate-id> \
  --trigger "..." --action "..." --because "..." --scope artifact --scope-key executive-update
python3 tools/bm_learn.py reject <candidate-id> --because "too specific"
python3 tools/bm_learn.py rules
python3 tools/bm_learn.py show-rule <rule-id>
python3 tools/bm_learn.py edit <rule-id> --expected-version <n> ...
python3 tools/bm_learn.py deprecate <rule-id> --because "..."
python3 tools/bm_learn.py forget <rule-id> --yes
```

### Command behavior

- Default output is concise and safe.
- `--json` provides machine-readable output.
- Unknown flags exit non-zero and name the flag.
- Mutations require an explicit project root.
- `approve` must require a founder-controlled confirmation channel. In the CLI this is the explicit invocation itself; do not allow a background hook to call approval.
- `capture` defaults to project scope when scope is ambiguous.
- `capture` may accept `--raw-text`, but it must redact secret-shaped content before storage or clearly separate encrypted/private raw source if encryption is implemented later. For this phase, use the existing best-effort redaction and owner-only storage.
- Candidate display shows IDs, proposed rule fields, scope, source, and redaction count.
- Candidate display never prints raw sensitive excerpts unless an explicit `--show-source` flag is supplied and the user is warned.
- `approve` can edit the structured interpretation without modifying the immutable original evidence.
- Reject reasons are retained and shown during future duplicate detection.

### Atomicity validator

Reject or require splitting when a candidate contains multiple independent actions. A deterministic first-pass validator may flag:

- multiple imperative bullet points;
- semicolon-separated independent actions;
- repeated "and always" structures;
- multiple unrelated domains.

This is advisory at capture and blocking at approval unless the founder passes an explicit override with a reason. The override is evidence, not silent bypass.

### Required tests

- Every command validates flags.
- Capture defaults to project scope.
- Approval requires explicit command invocation and source provenance.
- Approval can narrow scope.
- Approval can edit interpretation without editing evidence.
- Rejection preserves evidence.
- Forget requires confirmation.
- JSON and human output agree on identifiers and state.
- Source output redacts secrets.
- Control characters cannot forge extra CLI rows.
- No command writes outside the project store.
- CLI exits are documented and tested.

### Done gate

A founder can explicitly capture, inspect, approve, edit, reject, deprecate, and forget rules. Nothing is automatically applied yet.

### Commit

```text
Add founder-controlled correction review workflow
```

---

## Loop 4 - Upgrade automatic correction candidate capture

### Objective

Improve recall of correction opportunities without auto-approving anything.

### Current problem to close

The current mechanism uses a short English regex, ignores messages over a fixed length, stores little structure, and runs at SessionEnd. It is useful as a cheap signal but not a full learning pipeline.

### Primary files

- `tools/bm_telemetry.py`
- `tools/bm_learning.py`
- `tools/bm_store.py`
- `tools/test_bm.py`
- `tools/test_bm_learning.py`

### Capture channels

Implement three channels in descending trust:

1. **Explicit capture** from Loop 3.
2. **Deterministic correction candidate detection** from founder messages.
3. **Outcome-derived candidates** from rework and escaped defects.

No channel auto-approves.

### Transcript pairing

Extend transcript parsing to optionally produce a bounded correction context:

```text
previous assistant response summary or hash
founder correction message
session id
project
current work record if known
nearby artifact references
```

Do not persist entire assistant responses by default. Store a hash and a short redacted excerpt sufficient for review.

### Detection rules

Preserve the regex as one feature, but add deterministic signals:

- direct negation or replacement language;
- "I asked for X, not Y" patterns;
- immediate retry after a delivered writing artifact;
- explicit "remember," "never," "always," or "from now on" instructions;
- founder-edited structured output when a before/after artifact is available;
- a rework signal referencing the same artifact or work record;
- an escaped defect matching a prior green completion.

Do not treat ordinary disagreement, brainstorming, questions, or a changed business decision as a permanent preference automatically.

### Language support

Do not hard-code English-only semantics as the sole path. Implement:

- Unicode-safe capture;
- configurable phrase packs loaded from a local data structure;
- English, French, and Japanese starter phrases only when backed by tests;
- explicit capture as the universal fallback.

Phrase packs produce candidates, never rules, so false positives are review cost rather than behavioral contamination.

### Deduplication

At capture time:

1. Normalize the proposed text and scope.
2. Check same session plus same normalized text.
3. Check recent candidates with the same source and hash.
4. Search nearby approved/rejected candidates.
5. If equivalent, attach evidence to the existing candidate or show a possible duplicate; do not silently discard a potentially different correction.

### Required tests

- Existing correction fixtures still work.
- Long corrections produce bounded excerpts rather than being silently ignored.
- English, French, and Japanese starter patterns produce candidates.
- Non-correction negation does not flood the queue in named negative fixtures.
- Duplicate SessionEnd flushes do not duplicate candidates.
- Assistant or subagent quotations of rule text are not captured as founder corrections.
- Outcome-derived candidates contain the correct work record and artifact reference.
- Secret-shaped content is redacted.
- Automatic capture never creates an approved rule.

### Metrics

Record descriptive capture metrics only:

- candidates detected;
- candidates approved;
- candidates rejected;
- duplicate suggestions;
- false positive reason categories.

Do not call these accuracy until a labeled review set exists.

### Done gate

The review queue is materially richer, but all behavior remains founder-approved.

### Commit

```text
Expand correction candidate capture without auto-promotion
```

---

## Loop 5 - Implement scoped lexical retrieval with progressive disclosure

### Objective

Retrieve a small number of relevant approved rules at the right time with an explanation for every result.

### Primary files

- `tools/bm_store.py`
- `tools/bm_learning.py`
- `tools/bm_learn.py`
- `tools/test_bm_learning.py`
- `docs/CORRECTION-LEARNING.md`

### Retrieval command

```bash
python3 tools/bm_learn.py relevant \
  --query "draft an executive update about the registrar outage" \
  --domain communication \
  --artifact executive-update \
  --project-root "$PWD" \
  --limit 5
```

### Eligibility rules

Exclude:

- candidates;
- rejected rules;
- deprecated rules unless explicitly requested;
- forgotten rules;
- superseded rules;
- contradicted rules from automatic injection;
- rules whose scope does not match the supplied task context.

### Scope ordering

Use deterministic specificity precedence:

1. exact relationship or artifact match;
2. exact tool or domain match;
3. current project;
4. global.

A narrower rule may override a broader learned rule, but neither may override the constitution.

### Ranking

Do not create a mysterious composite score as the only explanation. Rank lexicographically by named components:

1. scope specificity;
2. constitutional compatibility;
3. rule state (`settled`, `confirmed`, `approved`);
4. FTS/BM25 or lexical relevance;
5. recent verified successful application;
6. unresolved warning penalties;
7. stable tie-breaker by rule UUID.

Return the components with each result.

Example:

```text
BM-L-3f9a  rank=1
Scope: artifact:executive-update (exact)
State: confirmed
Match: trigger terms "executive update", "impact"
Reason: leaders need the business state first
Action: state customer and revenue impact before technical detail
Evidence: 2 supporting, 0 unresolved contradictions
```

### Progressive disclosure

Default injection contains:

- rule ID;
- trigger;
- action;
- one-line reason;
- state;
- scope.

Detailed evidence, source excerpts, version history, and application history are available through `show-rule` or `why`, not injected by default.

### FTS5 behavior

- Probe and record availability.
- Create and synchronize the FTS index if available.
- Add tests for insert, edit, supersede, forget, and migration synchronization.
- Fallback retrieval must be deterministic and covered by the same relevance fixtures.
- Diagnostics must say `fts5` or `lexical-fallback`.

### Token and result budgets

- Default maximum: 5 rules.
- Default text budget: define and enforce a conservative character/token proxy.
- When over budget, preserve higher-ranked rules and truncate explanatory text, never trigger/action identity.
- Report omitted result count.

### Required tests

- Exact artifact scope outranks project and global.
- Project rules never leak to another project.
- Contradicted rules are suppressed.
- Forgotten rules never appear.
- Superseded rules are excluded and successor appears.
- FTS index follows edits and deletes/tombstones.
- Fallback mode produces stable results.
- Ranking explanation matches actual ordering.
- Output budget is enforced.
- Malicious control characters cannot forge another rule block.
- Query text is never written to the store by a read-only retrieval.

### Calibration

Disable the scope filter and prove the cross-project isolation test fails. Restore it and pass.

### Done gate

The founder or session can ask for relevant rules and receive a small, explainable set. No automatic hook injection yet.

### Commit

```text
Add scoped explainable retrieval for approved founder rules
```

---

## Loop 6 - Add duplicate, contradiction, and supersession handling

### Objective

Prevent rule bloat and incompatible active instructions.

### Primary files

- `tools/bm_learning.py`
- `tools/bm_store.py`
- `tools/bm_learn.py`
- `tools/test_bm_learning.py`

### Relationship semantics

- `duplicate_of`: semantically equivalent trigger and action in compatible scope.
- `contradicts`: overlapping trigger/scope with materially incompatible actions.
- `supersedes`: a newer rule intentionally replaces an older one.
- `derived_from`: a narrower or generalized rule originated from another.
- `supports`: separate rule provides reinforcing evidence or procedure.
- `applies_to`: explicit mapping to artifact, relationship, tool, or domain rule.

### Conflict detection pipeline

When a candidate is captured or a rule is approved/edited:

1. Retrieve nearby rules by exact normalized terms and FTS/lexical similarity.
2. Compare scope overlap.
3. Compare trigger overlap.
4. Compare actions:
   - exact/near duplicate;
   - compatible narrowing;
   - incompatible action;
   - not comparable.
5. Present suggestions; never auto-resolve semantic conflicts.
6. Block approval when an unresolved high-overlap contradiction would create two injectable active rules.
7. Allow founder override only by choosing:
   - narrow one scope;
   - supersede one;
   - mark one contradicted;
   - record an explicit precedence condition.

### CLI additions

```bash
python3 tools/bm_learn.py conflicts
python3 tools/bm_learn.py link <a> contradicts <b> --because "..."
python3 tools/bm_learn.py merge <candidate> --into <rule>
python3 tools/bm_learn.py supersede <old-rule> --with <new-rule> --because "..."
python3 tools/bm_learn.py resolve-conflict <edge-or-pair> ...
```

### Duplicate behavior

A duplicate candidate should normally add evidence to the existing rule or pending candidate rather than create another rule. Preserve the new source event.

### Required tests

- Exact duplicates merge evidence without losing provenance.
- Same action under distinct scopes remains separate.
- Overlapping scope plus incompatible action blocks approval.
- Narrower explicit scope can coexist with a broader rule.
- Supersession is atomic and retrieval immediately prefers the successor.
- Cyclic supersession is refused.
- Self-edges are refused.
- Forgotten or deprecated rules do not create active conflicts.
- Conflict output redacts source excerpts by default.

### Invariant checker

Add a deterministic `learning-verify` operation that reports:

- unresolved injectable contradictions;
- broken edges;
- cyclic supersession;
- current versions missing;
- rules without approval evidence;
- invalid scope keys;
- FTS drift;
- applications pointing to nonexistent versions.

### Done gate

There is no path to silently accumulate contradictory active rules.

### Commit

```text
Add conflict graph and supersession for learned rules
```

---

## Loop 7 - Record retrieval and application lifecycle

### Objective

Measure whether the right rules were surfaced and followed instead of merely counting stored rules.

### Primary files

- `tools/bm_store.py`
- `tools/bm_learn.py`
- `tools/bm_learning.py`
- `tools/test_bm_learning.py`
- `SKILL.md`
- `DIGEST.md`

### Application lifecycle

When rules are retrieved for a substantial task:

1. Create an application row per rule version.
2. Record task fingerprint, session, work record, rank, retrieval mode, and scope match.
3. Mark whether the rule was shown to the acting model.
4. At task close, record disposition:
   - followed;
   - ignored;
   - not relevant;
   - unknown.
5. If ignored, require a reason for substantial or gate rules.
6. Later link external outcomes.

### CLI additions

```bash
python3 tools/bm_learn.py relevant ... --record-applications --session "$SESSION_ID" --record "$WORK_UUID"
python3 tools/bm_learn.py disposition <application-id> followed --verification-ref "test:..."
python3 tools/bm_learn.py disposition <application-id> ignored --because "founder made a one-off exception"
python3 tools/bm_learn.py applications --session "$SESSION_ID"
```

### Skill integration

Update the BrotherMode law so substantial tasks must:

- retrieve relevant founder rules before planning or delivering;
- name applied rule IDs in the work record or loop-close report;
- state why any retrieved gate rule was not followed;
- avoid retrieval for trivial tasks when the proportionality classifier says it is unnecessary.

Do not force heavy ceremony on SIMPLE tasks. Define a lightweight threshold such as:

- no retrieval for a one-line obvious edit unless a global safety gate applies;
- retrieval for communication artifacts, architecture decisions, multi-file changes, risky operations, or tasks linked to prior corrections.

### Failure classification

Implement deterministic classification where evidence exists:

- **retrieval miss:** a relevant approved rule existed but was not retrieved.
- **compliance failure:** the rule was retrieved, shown, and ignored or violated.
- **bad rule:** the rule was followed and linked to rework/correction without stronger conflicting context.
- **scope error:** an irrelevant rule was retrieved because scope was too broad.
- **not decidable:** evidence is insufficient.

Never force a classification when data is missing.

### Required tests

- Applications point to immutable rule versions.
- Editing a rule does not rewrite old application history.
- Read-only retrieval without `--record-applications` creates no rows.
- Recording is idempotent per task/rule/version where intended.
- Gate rule ignores require reasons.
- Trivial-task bypass is explicit and does not create fake applications.
- Failure classification fixtures cover all five outcomes.
- Missing evidence returns `not_decidable`.

### Done gate

BrotherMode can answer, for a given task, which rules were retrieved, shown, followed, ignored, and why.

### Commit

```text
Track learned-rule retrieval and application outcomes
```

---

## Loop 8 - Link rework, escaped defects, and repeated corrections

### Objective

Close the loop using external evidence that the graded party cannot fabricate.

### Primary files

- `tools/bm_telemetry.py`
- `tools/bm_store.py`
- `tools/bm_learn.py`
- `tools/test_bm.py`
- `tools/test_bm_learning.py`
- `tools/WEEKLY-REVIEW.md`

### Existing signals to preserve

- `REWORK`
- `ESCAPED DEFECT`
- founder-provenance felt outcome

### Integration behavior

Extend rework and escaped-defect recording so each event can reference:

- original session;
- original work record;
- artifact or task fingerprint;
- rule applications from that work;
- new correction candidate if one exists.

### Repeated correction detection

When a new correction candidate is reviewed, compare it to active approved rules.

If it matches a settled or confirmed rule:

- create supporting or contradicting evidence as appropriate;
- mark a `corrected_again` outcome on relevant prior applications;
- emit a loop failure:
  - retrieval miss;
  - compliance failure;
  - bad rule;
  - scope error;
  - not decidable.

The system must not merely increment `times_applied` or a correction count.

### CLI additions

```bash
python3 tools/bm_learn.py rework \
  --original-session ... --record ... --artifact ... --because "..."

python3 tools/bm_learn.py escaped-defect \
  --original-session ... --record ... --defect-class ... --evidence "..."

python3 tools/bm_learn.py loop-failures --since 30d
python3 tools/bm_learn.py rule-outcomes <rule-id>
```

### Weekly review output

Replace ungrounded correction trend claims with:

- repeated settled corrections;
- retrieval misses;
- compliance failures;
- bad-rule candidates;
- unresolved contradictions;
- rules never retrieved;
- rules retrieved but always marked irrelevant;
- rework and escaped defects linked to rules;
- unattributed outcomes listed separately;
- `NOT DECIDABLE` where sample size or attribution is insufficient.

### Required tests

- Rework links to prior applications.
- Escaped defect links to the exact prior rule version.
- Repeated correction against a settled rule creates a loop failure.
- Unrelated correction does not falsely blame a rule.
- Missing links result in `not_decidable`.
- Founder rating without provenance remains unattributed.
- The graded session cannot create founder approval evidence through telemetry.

### Done gate

BrotherMode can distinguish storage growth from actual behavioral improvement.

### Commit

```text
Grade learned rules with rework and escaped-defect evidence
```

---

## Loop 9 - Build permanent evaluation partitions and deterministic replay

### Objective

Evaluate retrieval and rule changes without training/validation leakage or self-judging theatre.

### Primary files

- `tools/bm_eval.py`
- `tools/bm_store.py`
- `tools/bm_learning.py`
- `tools/test_bm_learning.py`
- `docs/LEARNING-EVALUATION.md`

### Evaluation layers

#### Layer 1: deterministic structural checks

Examples:

- correct rule retrieved;
- forbidden rule not retrieved;
- scope isolation;
- expected order;
- contradiction suppression;
- output budget;
- version and provenance integrity;
- constitutional conflict rejection.

#### Layer 2: executable artifact checks

Examples:

- command exit status;
- file existence;
- schema match;
- diff checks;
- required section order;
- banned phrase absence;
- test command output.

#### Layer 3: founder review or external judge

Only for behavior that cannot be reduced to a deterministic check. The product itself must not require a networked evaluator. Opus may help generate proposals during development, but permanent acceptance evidence must include founder approval or a reproducible external review artifact.

### Partition rules

- Assign `train`, `validation`, or `test` at case creation.
- Store the partition permanently.
- Validation/test prompts and expected outcomes never feed proposal generation.
- A case may be deactivated but not reassigned.
- The final test partition is opened only for release candidates, not every edit.
- Keep content hashes to detect mutation.

### Candidate amendment workflow

A constitutional or retrieval-policy amendment proposal must:

1. name the signal it intends to improve;
2. name the existing text or logic it displaces;
3. generate a bounded patch, not a wholesale rewrite;
4. remain under the configured size budget;
5. pass all safety invariants;
6. positively beat baseline on validation by a non-zero margin;
7. introduce zero critical regressions;
8. be presented to the founder;
9. remain unapplied until founder approval;
10. receive a dedicated commit and rollback reference.

Set default acceptance threshold strictly above zero. A tie does not justify change.

### Rejection buffer

Persist rejected proposals with:

- patch hash;
- reason;
- failed cases;
- score delta;
- date;
- source evidence.

Future proposal generation must inspect the rejection buffer and avoid repeating an unchanged rejected patch.

### Commands

```bash
python3 tools/bm_eval.py freeze-case ... --partition validation
python3 tools/bm_eval.py list-cases --partition validation
python3 tools/bm_eval.py retrieval --partition validation
python3 tools/bm_eval.py compare --baseline <ref> --candidate <ref>
python3 tools/bm_eval.py release-test --candidate <ref>
python3 tools/bm_eval.py verify-partitions
```

### Required tests

- Validation/test cases never appear in training queries.
- Partition cannot be changed after freezing.
- Mutation of frozen prompt or expectation is detected.
- Tie score is rejected.
- Positive aggregate score with a critical regression is rejected.
- Rejection buffer persists.
- Candidate patch cannot write `SKILL.md` automatically.
- Founder approval is required after evaluation pass.
- Deterministic checks run before any optional judge path.

### Calibration

Deliberately inject a validation case into the training query and prove the leakage test fails. Restore isolation and pass.

### Done gate

BrotherMode has a trustworthy local evaluation harness for retrieval and rule-policy changes, with honest limits around subjective behavior.

### Commit

```text
Add leak-proof replay evaluation for correction learning
```

---

## Loop 10 - Generate LESSONS and TOOLBOX views

### Objective

Turn verified experience into small, retrievable knowledge artifacts without creating a second source of truth.

### Primary files

- `tools/bm_learn.py`
- `tools/bm_store.py`
- `tools/bm_learning.py`
- `docs/knowledge/LESSONS.md`
- `docs/knowledge/TOOLBOX.md`
- `tools/test_bm_learning.py`

### LESSONS model

Organize by defect class, not incident.

Each generated section contains:

```text
Class
What it looks like
Why it happens
Mechanical stop
Recent appearances, capped
Total appearance count
State: OPEN or CLOSED
Last verified
```

A `CLOSED` class must name a test, grep, gate, or command whose reference resolves. If it does not resolve, generation or verification fails.

A sixth appearance replaces the oldest displayed appearance while incrementing the total count.

### TOOLBOX model

Each entry contains:

```text
Tool name
Purpose
Verified invocation
Version or environment
Verification date
Known gotchas from real failures
Do not use it for
Staleness state
```

Rules:

- create an entry only after verified use;
- every invocation carries a date and version/environment;
- version-sensitive entries become `STALE` after the configured interval;
- stale entries remain visible but are not injected as trusted procedure;
- documentation reading alone is not verified use.

### Generated-view rules

- SQLite remains source of truth.
- Generated files are overwritten only within clearly marked generated regions or wholly generated files.
- Use `safe_project_path` for output.
- Refuse symlink/hardlink escapes.
- Make output deterministic for stable diffs.
- Do not include raw founder quotes or secrets.
- Include generation timestamp only if it does not create noisy diffs; prefer source revision/count metadata.

### Commands

```bash
python3 tools/bm_learn.py lessons
python3 tools/bm_learn.py toolbox
python3 tools/bm_learn.py knowledge-verify
```

### Required tests

- Closed lesson with missing mechanical stop fails.
- Appearance display cap works while total count remains correct.
- Stale toolbox entries are marked and suppressed from trusted injection.
- Generated output is deterministic.
- Generated output contains no raw secret-shaped source text.
- Path safety applies.
- Manual edits to generated regions are overwritten or refused according to documented policy.

### Done gate

Knowledge compounds through verified, bounded artifacts rather than unlimited transcript summaries.

### Commit

```text
Generate bounded lessons and verified tool knowledge views
```

---

## Loop 11 - Integrate retrieval into BrotherMode and hooks

### Objective

Make approved rules appear automatically when relevant without flooding context or adding network/service dependencies.

### Primary files

- `SKILL.md`
- `DIGEST.md`
- `tools/bm_sessionstart.sh`
- `tools/bm_learn.py`
- hook configuration examples in `docs/SETUP.md`
- `tools/test_bm.py`

### Stage A: skill-driven retrieval

Before adding a hook, wire the law so BrotherMode explicitly runs `bm_learn.py relevant` for substantial tasks.

This stage must be dogfooded first.

### Stage B: optional `UserPromptSubmit` hook

After Stage A proves useful, add an optional deterministic hook that:

1. reads the prompt JSON from stdin;
2. resolves the current project safely;
3. performs local FTS/lexical retrieval only;
4. returns at most the configured number of concise rule summaries;
5. performs no network calls and no model call;
6. stays under a measured latency budget;
7. creates no application rows unless the returned rules are actually injected and a session ID is available;
8. degrades silently or with one concise warning when the learning store is unavailable, except corruption/security conditions which remain explicit.

### Injection format

```text
RELEVANT FOUNDER RULES
- BM-L-... [artifact:executive-update, confirmed]
  When: ...
  Do: ...
  Because: ...

Use these only where relevant. Constitution overrides learned rules.
For evidence or conflicts, run: python3 tools/bm_learn.py why <id>
```

### Context budget

- hard maximum rule count;
- hard maximum output characters;
- no raw evidence excerpts;
- no application history;
- no candidate rules;
- no contradicted rules;
- show omitted count when truncated.

### Hook tests

- empty store adds no noise;
- exact relevant rule appears;
- unrelated rules do not appear;
- cross-project rules do not appear;
- hook input with secrets is not persisted by retrieval;
- output respects budget;
- hook remains fast under a large rule fixture;
- FTS unavailable fallback works;
- corrupted store reports a truthful actionable warning;
- duplicate hook execution does not create duplicate application rows.

### Setup and uninstall

Update setup and uninstall documentation for any new hook. Uninstall must remove only BrotherMode-owned hook entries and document that learning rows remain in the project store until the project cleanup command is run.

### Done gate

Relevant rules arrive with low friction and measured bounded overhead.

### Commit

```text
Inject relevant founder rules with bounded local retrieval
```

---

## Loop 12 - Security, privacy, and adversarial review

### Objective

Prove that correction learning does not create a new data-leak or integrity surface.

### Primary files

- `SECURITY.md`
- `tools/bm_store.py`
- `tools/bm_learn.py`
- `tools/bm_learning.py`
- all three test files
- `docs/KNOWN-LIMITS.md`

### Threat model additions

Review and test:

1. Founder writes a secret inside a correction.
2. Secret is placed in trigger, action, reason, scope key, review note, edge note, or evidence excerpt.
3. Diagnostic dump attempts to expose new text columns.
4. Generated LESSONS or TOOLBOX view leaks source text.
5. Malicious control characters forge CLI or markdown output.
6. Symlinked generated knowledge path copies external content into the project.
7. Hardlinked store or sidecar exposes raw database bytes.
8. Imported rule contains prompt injection or unsafe instructions.
9. A model attempts to approve its own candidate.
10. A stale session edits an already changed rule.
11. Two processes approve or edit the same candidate/rule concurrently.
12. FTS triggers drift from source tables.
13. Forgotten content remains visible through FTS.
14. Backup, migration, or WAL sidecars inherit weak permissions.
15. Windows cannot guarantee owner-only semantics for a new artifact.

### Security decisions

- Imported rules are `pending` and untrusted by default.
- Raw source excerpts are hidden from default output.
- Free-text columns are dump-redacted by default.
- FTS tables must not create an alternate unredacted dump path.
- Forget must remove content from active search indexes while retaining only the minimum tombstone needed for integrity.
- No remote import is required for the initial release.
- No model-generated text is treated as founder approval.
- Any export is secret-redacted and excludes project paths, relationship names, session IDs, and founder quotations unless explicitly requested.

### Adversarial review roles

Run independent read-only reviews with different lenses:

- correctness and transactionality;
- security and privacy;
- concurrency and crash recovery;
- cross-platform behavior;
- test calibration and false confidence;
- product proportionality for a solo founder.

Every finding must be reproduced or dismissed with evidence. Do not fix a report merely because a reviewer said it.

### Required gates

- full tests on supported platforms;
- network grep remains clean;
- subprocess inventory remains expected;
- new text-column redaction test;
- FTS forgotten-content test;
- concurrent approval/edit tests;
- migration backup and rollback tests;
- generated-view path escape tests;
- Windows known-limit statement updated truthfully.

### Done gate

No unresolved critical or high security finding. Medium findings are either fixed or explicitly documented with a founder-approved release decision.

### Commit

```text
Harden correction learning against data leaks and stale writes
```

---

## Loop 13 - Documentation, scorecard replacement, and release contract

### Objective

Remove obsolete self-learning claims and document exactly what is now measured.

### Primary files

- `README.md`
- `SKILL.md`
- `DIGEST.md`
- `RUBRIC.md`
- `tools/bm_score.py`
- `tools/WEEKLY-REVIEW.md`
- `docs/KNOWN-LIMITS.md`
- `docs/HOW-IT-WORKS.md`
- `docs/CORRECTION-LEARNING.md`
- `docs/LEARNING-SCHEMA.md`
- `docs/LEARNING-EVALUATION.md`
- `CHANGELOG.md`

### Replace theatre metrics

Delete or relabel any metric that cannot move mechanically or cannot support a decision at current volume.

The correction-learning review should report:

- candidates captured;
- founder approval/rejection counts;
- repeated settled corrections;
- retrieval misses;
- compliance failures;
- bad-rule candidates;
- scope errors;
- unresolved contradictions;
- rules never retrieved;
- rules frequently retrieved but marked irrelevant;
- rework and escaped defects linked to rule applications;
- provenance-backed felt outcomes;
- unattributed outcomes separately;
- `NOT DECIDABLE` for unsupported trend claims.

### Product wording

Use:

- "founder-approved correction memory";
- "evidence-backed learned rules";
- "retrieval and outcome tracking";
- "local correction-learning system."

Avoid claiming:

- autonomous self-improvement;
- statistical learning from a small number of sessions;
- guaranteed zero repeated corrections;
- correctness from an LLM judge;
- production readiness before dogfooding.

### Doctor/diagnostics

Add a diagnostic command or section reporting:

- schema version;
- learning table health;
- FTS availability and sync;
- pending candidates;
- unresolved contradictions;
- evaluation partition health;
- stale TOOLBOX entries;
- last successful learning verification;
- whether automatic retrieval hook is configured.

### Done gate

Documentation, code, and scorecard use the same terminology and make no stronger claim than the evidence supports.

### Commit

```text
Document evidence-backed correction learning and honest metrics
```

---

## Loop 14 - Real founder dogfooding and release decision

### Objective

Use the system on real work before declaring the correction engine production-ready.

### Minimum dogfood protocol

Run BrotherMode through a sustained period of real founder work. Prefer at least:

- multiple projects or domains;
- communication and coding tasks;
- at least several explicit corrections;
- at least one rule edit;
- at least one rejected candidate;
- at least one duplicate or conflict review;
- at least one rework or escaped-defect linkage;
- at least one compaction/resume lifecycle;
- at least one retrieval in FTS and fallback test mode.

Do not manufacture events merely to increase counts. Use genuine work and record missing cases as untested.

### Dogfood review questions

1. Did candidate review become annoying?
2. Were important corrections missed?
3. Were false positives understandable and cheap to dismiss?
4. Did project scope prevent contamination?
5. Did relevant rules arrive before the mistake?
6. Were irrelevant rules over-injected?
7. Could the founder understand why each rule appeared?
8. Did a repeated correction classify correctly?
9. Did any rule make the output worse?
10. Did the system create more ceremony than value?
11. Was latency noticeable?
12. Did privacy controls hide necessary evidence or expose too much?
13. Did the generated knowledge artifacts remain small and useful?
14. Did any unsupported metric invite false confidence?

### Release gates

Do not label the feature production-ready unless all are true:

1. Every approved rule has founder provenance.
2. No background path can approve a rule.
3. No learned rule can override the constitution.
4. Cross-project isolation passes adversarial tests.
5. Contradictory injectable rules are blocked.
6. Repeated settled corrections create a loop failure.
7. Rework and escaped defects can trace to rule applications when references exist.
8. Evaluation partitions are permanently isolated.
9. Amendment ties are rejected; positive improvement and no critical regression are required.
10. Rollback restores prior rule/policy behavior.
11. New text fields and outputs pass redaction tests.
12. Full CI is green on supported platforms.
13. Real founder work has exercised the system.
14. Remaining and unverified lists are published.

### Release artifacts

- release notes;
- updated known limits;
- dogfood evidence summary without private content;
- migration and rollback instructions;
- exact test counts and CI links;
- versioned schema documentation.

### Commit

```text
Record correction-learning dogfood evidence and release decision
```

---

# 7. Optional later loops - not part of the first trustworthy release

## Optional Loop A - Semantic retrieval adapter

Only begin after lexical retrieval has measured misses that matter.

Requirements:

- optional and disabled by default;
- local provider preferred;
- no mandatory API key;
- no mandatory service;
- clean fallback to FTS/lexical search;
- semantic similarity never resolves contradictions automatically;
- embedding data is treated as sensitive derived data;
- model/version recorded;
- re-indexing is explicit;
- retrieval evaluation must prove improvement over lexical baseline.

Do not add PostgreSQL, Docker, pgvector, Bun, or Chroma as a required dependency.

## Optional Loop B - Cross-runtime adapters

Keep the core store and learning lifecycle runtime-neutral. Add thin adapters for Codex, OpenCode, Cursor, or Gemini only after Claude Code behavior is stable.

Each adapter translates:

- session start/end;
- user prompt submission;
- tool activity;
- compaction/restart if available;
- explicit correction capture;
- task completion.

Do not duplicate learning logic in each adapter.

## Optional Loop C - Safe export/import

Exports:

- default to structured rules without founder quotations;
- redact secrets and paths;
- exclude session IDs and relationship names;
- include schema version and provenance class, not private provenance content.

Imports:

- become `pending` candidates;
- default to project scope;
- are marked `imported` and untrusted;
- cannot auto-promote or auto-apply;
- must pass local review and constitutional conflict checks.

---

# 8. Testing strategy

## 8.1 Test layers

### Unit tests

Pure normalization, hashing, scope matching, ranking, state transitions, conflict helpers, and redaction.

### Store tests

Transactions, migration, foreign keys, version history, concurrent updates, rollback, FTS synchronization, and handle closure.

### CLI tests

Arguments, exit codes, JSON output, safe display, approval controls, and idempotence.

### Hook tests

Payload parsing, bounded output, duplicate invocation, no network, no unintended writes, compaction/start interactions, and platform behavior.

### Integration tests

Candidate -> approval -> retrieval -> application -> outcome -> review.

### Adversarial tests

Secret injection, control characters, symlink/hardlink escapes, stale sessions, conflict cycles, schema skew, corrupt JSON/SQLite state, FTS drift, and cross-project contamination.

### Mutation/calibration tests

For every load-bearing guard, reinject a representative old defect or monkeypatch the guard to the unsafe behavior and prove the test fails.

## 8.2 Required end-to-end scenarios

### Scenario 1: Explicit communication preference

1. Capture a correction.
2. Approve it for artifact scope.
3. Retrieve it for a matching task.
4. Record it followed.
5. Link accepted outcome.
6. Verify state remains approved/confirmed according to policy.

### Scenario 2: Cross-project isolation

1. Approve a project rule in project A.
2. Query the same terms in project B.
3. Prove the rule is absent.
4. Add a global rule and prove only that rule appears.

### Scenario 3: Contradiction

1. Approve a broad global rule.
2. Propose an incompatible project rule.
3. Block approval until scope/precedence is resolved.
4. Approve the narrower rule.
5. Prove project retrieval selects the narrow rule and global retrieval selects the broad one.

### Scenario 4: Repeated correction

1. Approve and settle a rule.
2. Retrieve it for a matching task.
3. Mark it ignored.
4. Capture the same correction again.
5. Classify compliance failure.

### Scenario 5: Bad rule

1. Approve a rule.
2. Retrieve and follow it.
3. Founder sends the artifact back because the rule was wrong in this context.
4. Link rework.
5. Classify bad-rule candidate or scope error.
6. Contradict, narrow, edit, or deprecate through founder review.

### Scenario 6: Retrieval miss

1. Approved relevant rule exists.
2. Force retrieval configuration that omits it.
3. Work receives same correction.
4. Classify retrieval miss.
5. Add a frozen evaluation case.

### Scenario 7: Migration and rollback

1. Create schema-1 store with active work.
2. Migrate to schema 2.
3. Verify old work and new empty learning tables.
4. Simulate migration failure.
5. Prove old store remains usable.

### Scenario 8: Forget

1. Approve and retrieve a rule.
2. Forget it.
3. Prove it disappears from normal reads and FTS.
4. Prove historical application integrity remains without exposing forgotten text.

---

# 9. Performance and proportionality budgets

BrotherMode must remain lightweight.

Set and measure budgets rather than assuming them.

Recommended initial targets on a normal local project:

- empty-store retrieval: effectively unnoticeable;
- retrieval from 1,000 rules: target under 100 ms on supported CI hardware where stable timing is possible;
- hook output: at most 5 rules and a conservative character budget;
- no database connection left open after a CLI process exits;
- no background daemon;
- no periodic model call;
- no automatic optimizer loop;
- no correction review interruption during ordinary work;
- pending-candidate nag at most once per configured interval;
- generated views bounded and deterministic.

Timing assertions can be flaky across CI. Use generous regression thresholds or benchmark reporting rather than brittle absolute failures unless the environment is controlled.

---

# 10. Rollback strategy

## 10.1 Code rollback

Each loop is one commit. Revert the loop commit if its gate fails after landing.

## 10.2 Schema rollback

Do not automatically downgrade a live database by dropping learning tables. Instead:

- back up before migration;
- provide a documented export of legacy work-state tables if rollback is required;
- allow an older binary to refuse a newer schema clearly;
- never silently ignore schema-2 tables and write as schema 1.

## 10.3 Rule rollback

Rule edits create versions. Restore a prior version through a new `restored` version, preserving history.

## 10.4 Policy rollback

Constitutional or retrieval-policy changes must have:

- baseline reference;
- candidate reference;
- validation run;
- founder approval;
- dedicated commit;
- one-command git revert path.

## 10.5 Hook rollback

The optional prompt hook must be independently removable without removing the learning store or explicit CLI.

---

# 11. Definition of strongest-in-position

BrotherMode is strongest in its chosen position when it can prove the following better than larger alternatives:

1. **Local simplicity:** one local SQLite store and standard-library core.
2. **Founder sovereignty:** no automatic approval or constitutional rewrite.
3. **Correction fidelity:** original evidence, structured interpretation, and approval are separate.
4. **Scope safety:** project and contextual rules do not contaminate unrelated work.
5. **Explainable retrieval:** every rule appears for named reasons.
6. **Conflict integrity:** incompatible rules cannot silently co-exist in active injection.
7. **Outcome attribution:** retrieval miss, compliance failure, and bad rule are distinguishable.
8. **External grading:** rework, escaped defects, repeated corrections, and founder evidence outrank self-rating.
9. **Evaluation honesty:** permanent holdouts, positive improvement requirements, and no automatic landing.
10. **Security by default:** new free text is redacted and path/store protections remain intact.
11. **Proportionality:** trivial work stays trivial; substantial work receives disciplined memory and gates.
12. **Honest maturity:** real founder dogfooding precedes production claims.

---

# 12. Master execution checklist

## Foundation

- [ ] Loop 0 baseline frozen
- [ ] Schema version 2 migration implemented
- [ ] Migration rollback tested
- [ ] New text fields default-redacted
- [ ] Store API implemented

## Founder workflow

- [ ] Explicit capture
- [ ] Candidate review
- [ ] Founder approval
- [ ] Edit/version history
- [ ] Reject/deprecate/forget

## Capture

- [ ] Deterministic transcript candidates
- [ ] Long-message bounded capture
- [ ] Multilingual starter fixtures
- [ ] Outcome-derived candidates
- [ ] Duplicate SessionEnd protection

## Retrieval

- [ ] FTS5 probe
- [ ] Lexical fallback
- [ ] Scope isolation
- [ ] Progressive disclosure
- [ ] Explainable ranking
- [ ] Context budget

## Integrity

- [ ] Duplicate merge
- [ ] Contradiction blocking
- [ ] Supersession
- [ ] Cycle detection
- [ ] Learning verify command

## Outcomes

- [ ] Application recording
- [ ] Immutable version attribution
- [ ] Rework linkage
- [ ] Escaped-defect linkage
- [ ] Repeated-correction loop failure
- [ ] Not-decidable path

## Evaluation

- [ ] Permanent partitions
- [ ] Leakage tests
- [ ] Deterministic replay
- [ ] Tie rejection
- [ ] Critical-regression gate
- [ ] Rejection buffer
- [ ] Founder approval after pass

## Knowledge

- [ ] LESSONS generated view
- [ ] Mechanical-stop validation
- [ ] TOOLBOX generated view
- [ ] Staleness
- [ ] Deterministic output

## Integration

- [ ] Skill-driven retrieval
- [ ] Optional prompt hook
- [ ] Hook latency and budget
- [ ] Setup documentation
- [ ] Uninstall documentation

## Security and release

- [ ] Full adversarial review
- [ ] Supported-platform CI green
- [ ] Known limits updated
- [ ] Scorecard theatre removed
- [ ] Real founder dogfood completed
- [ ] Release decision documented

---

# 13. First prompt to give Claude Code Opus 5

Use this plan from the repository root and begin only with Loop 0.

```text
Read BrotherMode_V2_Correction_Learning_Execution_Plan.md in full.
Execute Loop 0 only.

Before writing anything:
1. Confirm the current repository root, branch, commit, and git status.
2. Read every source file named in sections 0.3 and Loop 0.
3. Run the existing test suites and documented safety checks.
4. Reproduce the current correction-candidate behavior in a scratch project.
5. Create the baseline specification requested by Loop 0.

Do not begin Loop 1.
Do not change production behavior.
Do not claim success without fresh command output.
At the end, return the exact LOOP 0 CLOSE report defined in section 0.4.
```

After Loop 0 passes, use:

```text
Continue with Loop <N> only from BrotherMode_V2_Correction_Learning_Execution_Plan.md.
Re-read the Loop <N> requirements and relevant current source files.
Treat the previous loop's committed state as the baseline.
Implement the smallest complete vertical slice, calibrate load-bearing tests, run full regressions, update known limits, commit the loop separately, and return the exact loop-close report.
Do not begin the next loop.
```

---

# 14. Final instruction

The purpose of this program is not to make BrotherMode look more intelligent. It is to make improvement traceable.

A successful correction-learning system must be able to show:

- what the founder actually said or did;
- how that evidence was interpreted;
- whether the founder approved the interpretation;
- where the rule applies;
- why it was retrieved;
- whether it was followed;
- what happened afterward;
- whether the rule, retrieval, or compliance failed;
- what changed because of that evidence;
- how to reverse the change.

Anything less is memory theatre. Anything more complicated than necessary weakens BrotherMode's position.
