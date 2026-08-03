HISTORICAL source archive (2026-08-01). Superseded by docs/superpowers/specs/2026-08-01-release-closure-program-ratified.md, which ratifies this plan with seven amendments; the ratified file governs.
The body below is the unmodified original from Downloads, SHA256 efa462beacb4e325227d6177f14c76d59ee1805f1c9f03e639ba4de1c0914544. Strip everything above and including the marker line to re-derive it.
<!-- verbatim original below -->
# BrotherME Final Release Closure Plan

## Fable-Governed Final Loop Before Official Release

**Document status:** Draft implementation plan.  
**Mandatory first action:** Claude Fable must review, challenge, reorder, and explicitly approve or revise this plan before any implementation begins.  
**Repository:** `khalilmaaouni/BrotherModeUp`  
**Prepared:** 2026-08-01  
**Target:** The last coordinated engineering loop before an official BrotherME 2.0 release.

---

# 1. Executive decision

BrotherME should **not** be released from the current `2.0.0-rc.11` state.

The current tree contains excellent governance, recovery, learning, documentation, and beginner-facing ideas. It also contains several release-blocking structural weaknesses:

1. The advertised `v2.0.0-rc.11` tag was not resolvable during the latest independent review.
2. Additional commits were made after the commit described as the `rc.11` release cut while the tree continued to identify itself as `rc.11`.
3. The original SQLite work store, the new canonical schema and JSONL events, and Markdown project files form overlapping state systems.
4. The beginner commands are still partly instructional prompts rather than mechanically integrated project operations.
5. The plugin has only one recorded local installation and no clean GitHub installation by an outside user.
6. The first-run consent and configuration flow is incomplete.
7. The write fence does not cover arbitrary shell writes and fails open when its state is unhealthy.
8. Cross-runtime support is documented more broadly than it is behaviorally proven.
9. Forecasts, attribution, alerts, and progress summaries are not yet all derived from one mechanically maintained source.
10. The product has not completed a real project through the full lifecycle.

The final loop must therefore be a **release-closure program**, not another feature wave.

The core recommendation is:

> Keep the existing SQLite store as the only durable source of truth. Integrate the new Project, Forecast, Task, AttributionEvent, Alert, and Evidence concepts into that store. Make every beginner command a thin, deterministic operation or view over that source. Generate Markdown and HTML from it. Then validate installation, security boundaries, runtime adapters, and a real project before releasing.

This is the lowest-rework path because it preserves the strongest existing engine and removes parallel bookkeeping rather than building another subsystem.

---

# 2. Non-negotiable rules for this final loop

1. **No implementation starts before Fable reviews this plan.**
2. **No new persona, book, command, law, framework, or conceptual feature is added unless it closes a release blocker in this document.**
3. **No release version is used by more than one byte-identical tree.**
4. **SQLite is the only authoritative project state.**
5. **Markdown, JSON, HTML, dashboards, status messages, and delivery packets are generated views, never competing sources of truth.**
6. **Every state change and its attribution event commit in one transaction.**
7. **Every implementation task has one writer, a declared scope, a runnable done-check, and an independent reviewer.**
8. **Fable plans and judges. A lower Claude model implements. Fable independently checks the result.**
9. **The executor does not define or weaken its own acceptance criteria.**
10. **A test may not be counted as evidence until its failure path has been calibrated or its property has been independently demonstrated.**
11. **A platform or runtime is called supported only after its conformance suite passes on the real runtime.**
12. **Official release is refused while any Critical finding remains open.**
13. **The founder alone approves irreversible release actions, credentials, publication, and production deployment.**
14. **No claim is broader than the actual verified boundary.**
15. **The goal is not maximum functionality. The goal is the smallest coherent product that reliably carries a person from an idea to a verified delivery.**

---

# 3. What “above 9/10” means

A score above 9 must correspond to observable behavior, not confidence or document quality.

| Metric | 9/10 release standard |
|---|---|
| Release integrity | One signed or annotated immutable tag, one release commit, matching manifests, checksums, evidence, and green CI on those exact bytes |
| Beginner onboarding | At least 90% of fresh test users install and start their first project without developer intervention |
| Installation | Plugin install, update, doctor, migration, and uninstall pass on clean supported environments |
| Project-state correctness | No conflicting source of truth; state and attribution change atomically; crash tests demonstrate recoverability |
| Lifecycle completeness | A real project travels from brief to planned, active, reviewed, verified, accepted, delivered, monitored, and closed |
| Status trustworthiness | Every displayed number and state is computed from stored records and linked evidence |
| Forecasting | Ranges, assumptions, confidence, and forecast history are stored; actuals are measured where available; unknown remains unknown |
| Attribution | Actor, runtime, model, task, reason, outputs, evidence, and immutable code references are recorded |
| Security | Declared threat model is explicit; supported write paths are enforced; shell escapes are detected; high-risk failure can be configured fail-closed |
| Privacy | Local data behavior is disclosed before first write; export and deletion are simple; permissions are verified; no network occurs automatically |
| Recovery | Interrupted work, compaction, and stale ownership recover without overwriting live work |
| Verification | Independent review, post-final-change checks, and latest-commit evidence are required before delivery |
| Cross-runtime architecture | One runtime-neutral core and normalized adapter contract; no duplicated business logic |
| Cross-runtime verified breadth | At least three real runtimes pass the complete conformance suite |
| Maintainability | Small public surface, versioned schema, migration tests, generated facts, archived history, no parallel implementation |
| Real-world validation | At least one substantial dogfood project and three outside users before 2.0; a true 9/10 requires broader post-release evidence |

## 3.1 Metrics that cannot honestly exceed 9 before usage

Two metrics cannot be raised above 9 by code alone:

### External validation

A stable product cannot earn a 9/10 external-validation score without sustained external usage. The minimum release gate in this plan can raise it to approximately 7.5–8.5:

- one real founder project;
- at least seven calendar days;
- at least three outside fresh-machine installations;
- at least one non-technical participant;
- one interrupted and recovered session;
- one failed review that causes rework;
- one material reforecast;
- one actual delivery.

A true 9+ requires approximately:

- 30 days of usage;
- ten or more external users;
- multiple project types;
- measured retention;
- comparative results against plain Claude Code and at least one competitor.

### Cross-runtime verified breadth

A runtime-neutral architecture can exceed 9 in this loop. Actual behavioral support across every CLI and IDE cannot honestly exceed 9 unless each runtime is installed, payloads are captured, adapters are implemented, and conformance passes.

The release must therefore distinguish:

- **Core compatible**
- **Guidance integrated**
- **Hooks integrated**
- **Fully verified**

---

# 4. Operating model: Fable directs, lower Claude models build

## 4.1 Roles

### Fable: Release Architect, Researcher, Orchestrator, and Final Reviewer

Fable owns:

- plan review;
- current-platform research;
- architecture decisions;
- task decomposition;
- dependency ordering;
- task briefs;
- acceptance criteria;
- risk identification;
- security and migration decisions;
- model and runtime routing;
- adversarial review;
- final synthesis;
- release go/no-go recommendation.

Fable must remain read-only during ordinary implementation review. It may propose patches but should not silently become both author and reviewer of the same unit.

### Builder: lower Claude model

Use the current lower-cost Claude model capable of reliable repository implementation, normally the Builder profile.

The Builder owns:

- production code;
- migrations;
- deterministic tests;
- integration fixtures;
- command wiring;
- generated views;
- documentation changes specified in the brief;
- correcting findings returned by Fable.

The Builder does not:

- change the architecture;
- alter acceptance criteria;
- declare a release;
- weaken tests to obtain green;
- expand scope;
- make founder decisions.

### Fast Worker: smallest Claude model suitable for mechanical work

Use for:

- repetitive manifest generation;
- file inventory updates;
- fixture creation from approved examples;
- consistent terminology replacements;
- generated documentation;
- formatting;
- checksum refreshes;
- mechanical test matrix additions.

The Fast Worker never owns security logic, state transitions, migrations, release semantics, or final review.

### Founder

The founder owns:

- the target product promise;
- data-retention choices;
- support policy;
- release scope;
- credentials;
- official marketplace submission;
- release tag and publication;
- final acceptance.

---

## 4.2 Mandatory separation of duties

For every task:

1. Fable writes and signs the brief.
2. One lower Claude model implements.
3. The implementer runs the local done-check.
4. Fable reviews the actual diff and current files.
5. Fable reruns or requests rerun of the done-check.
6. A second lower model may apply narrowly scoped fixes.
7. Fable confirms the final state.
8. The orchestrator lands the commit only after all gates pass.

The writer and final reviewer must not be the same execution context.

---

## 4.3 Model routing

| Work | Default profile |
|---|---|
| Architecture, migration design, security boundary, release plan | Fable |
| Research on current runtime contracts | Fable |
| Normal implementation | Builder |
| Database migration and concurrency logic | Builder, Fable review mandatory |
| Mechanical documentation and fixtures | Fast Worker |
| Adversarial code review | Fable |
| Visual UX verification | Fable or a vision-capable reviewer |
| Release evidence and go/no-go | Fable plus founder |
| Irreversible publication | Founder only |

---

## 4.4 Budget policy

The ranges below are planning envelopes, not promises. Reforecast after Loops 1 and 2.

| Workstream | Fable envelope | Builder/Fast Worker envelope | Confidence |
|---|---:|---:|---|
| Plan review and final architecture | 40k–90k | 0 | Medium |
| Release truth and freeze | 15k–35k | 25k–60k | Medium |
| State unification and migrations | 50k–110k | 180k–420k | Low |
| Guided command integration | 30k–70k | 120k–280k | Low |
| Installation and first-run flow | 25k–60k | 90k–220k | Low |
| Security boundary improvements | 40k–90k | 120k–300k | Low |
| Runtime adapters | 60k–140k | 250k–600k | Low |
| Validation, dogfood, evidence | 50k–130k | 100k–250k | Low |
| Final adversarial and release pass | 50k–120k | 30k–80k | Medium |

**Whole-program planning range:** 1.2M–2.8M effective tokens.

This range must not become a target. The rule is to stop when the acceptance gate is satisfied, not when the budget is consumed.

---

# 5. Mandatory Fable review before implementation

## 5.1 Fable input set

Fable must read at least:

- this document;
- `README.md`;
- `VERSION`;
- `CHANGELOG.md`;
- `SECURITY.md`;
- `SKILL.md`;
- `docs/KNOWN-LIMITS.md`;
- `docs/NOT-FINALIZED.md`;
- `docs/RELEASE.md`;
- `docs/QUICKSTART.md`;
- `docs/RUNTIMES.md`;
- `docs/specs/canonical-project-protocol.md`;
- `brotherme/core/schema.py`;
- `tools/bm_store.py`;
- `tools/bm_threads.py`;
- `tools/bm_telemetry.py`;
- `tools/bm_fence_hook.py`;
- `tools/bm_autosave.py`;
- `tools/bm_ledger.py`;
- `tools/test_all.py`;
- `.github/workflows/tests.yml`;
- `.claude-plugin/plugin.json`;
- `.claude-plugin/marketplace.json`;
- `hooks/hooks.json`;
- every `/brotherme-*` command;
- the latest 30 commits;
- every open release-blocking issue or register item.

## 5.2 Exact Fable review prompt

```text
You are Claude Fable acting as the final release architect for BrotherME.

This is the last coordinated engineering loop before an official release.
Do not implement anything.

Review:
1. The current repository at HEAD.
2. The attached Final Release Closure Plan.
3. Current release tags and version identity.
4. The current SQLite store, canonical schema, JSONL event layer, guided commands,
   plugin packaging, hooks, runtime adapters, security boundaries, and release evidence.

Your job is to challenge the plan, not endorse it.

Return exactly:

A. VERDICT
- GO
- REVISE
- STOP

B. TOP RELEASE RISKS
For each:
- severity;
- evidence;
- consequence;
- smallest durable fix;
- whether it belongs before or after state unification.

C. REMOVE OR DEFER
List anything in the plan or repository that should be removed or deferred to reduce
surface area, rework, token cost, or release risk.

D. ARCHITECTURE DECISIONS
Confirm or reject:
- SQLite as the sole source of truth;
- JSONL as export only;
- generated Markdown/HTML;
- one runtime-neutral service layer;
- one primary public command;
- capability-tiered runtime claims;
- Fable plans/reviews and lower models implement.

E. REORDERED EXECUTION PLAN
Give the smallest coherent sequence. Name hard dependencies.

F. FIRST THREE IMPLEMENTATION BRIEFS
Each brief must contain:
- goal;
- exact files readable;
- exact files writable;
- files explicitly forbidden;
- migration and compatibility constraints;
- runnable done-check;
- expected return format;
- estimated time and token range;
- rollback method.

G. RELEASE GO/NO-GO MATRIX
Define objective conditions. No subjective confidence language.

H. PLAN AMENDMENTS
Write the exact edits that should be made to this document before implementation.

Do not praise the product unless the praise changes a decision.
Do not assume any claim is true because a document says so.
Check the implementation, tags, commits, tests, and evidence.
```

## 5.3 Required Fable artifact

Save the result as:

```text
docs/release/FINAL-RELEASE-PLAN-FABLE-REVIEW.md
```

The file must contain:

- Fable verdict;
- commit SHA reviewed;
- date;
- unresolved questions;
- approved architecture decisions;
- changed sequencing;
- release target;
- first implementation briefs;
- explicit statement that implementation may or may not begin.

## 5.4 Start gate

Implementation may begin only when all are true:

- Fable verdict is `GO`;
- every Critical plan finding is resolved in the plan;
- the founder approves the final scope;
- release branch and worktrees are created;
- `main` is no longer ambiguously using a released version identity.

---

# 6. Release strategy and branch discipline

## 6.1 Do not late-tag the current `rc.11`

If `v2.0.0-rc.11` was not published immediately from the release-cut commit and `main` has moved beyond it, do not create the tag late.

Instead:

1. Mark `rc.11` as `SUPERSEDED, NEVER TAGGED`.
2. Change `VERSION`, Python package version, plugin version, marketplace version, generated install text, and changelog to a development identity such as:

```text
2.0.0-rc.12.dev1
```

3. Keep the latest actually resolvable release as the public install target until the final release candidate exists.
4. Cut the next release from one exact commit.
5. Tag immediately after that commit.
6. Push the tag before any further commit.
7. After the tag, immediately bump `main` to the next development version.

## 6.2 Final branch model

Create:

```text
release/2.0-final
```

Rules:

- branch from a clean, verified main;
- no unrelated changes;
- no direct implementation by the orchestrator;
- each loop in an isolated worktree or short-lived branch;
- merge in dependency order;
- one commit train;
- every merged loop gets full gate;
- no release commit until all validation evidence exists.

## 6.3 Commit law

Each implementation commit must answer:

- What invariant changed?
- What prior failure does this close?
- What evidence can make the change fail?
- Which migration applies?
- Which claims or docs changed?
- What remains unproven?

Avoid release-story essays in production source comments. Keep detailed incident narrative in the commit and evidence record.

---

# 7. Architecture decisions for minimum rework

## ADR-1: SQLite remains the sole durable authority

**Decision:** Extend the existing SQLite store. Do not create another authoritative database or file.

The following move into SQLite:

- Project;
- Forecast;
- Task;
- Task dependency;
- Attribution event;
- Alert;
- Evidence reference;
- Runtime execution;
- User-visible decision;
- Delivery and monitoring state.

## ADR-2: Canonical Python objects become validation and service DTOs

`brotherme/core/schema.py` remains useful, but it must no longer imply independent persistence.

Its role:

- define field names;
- validate payloads;
- validate state names;
- serialize service input/output;
- maintain compatibility with adapters.

Its role is not:

- own the event log;
- mutate state independently;
- create a second source of truth.

## ADR-3: JSONL becomes an export or diagnostic format

The canonical attribution record should live in SQLite.

JSONL may be generated for:

- export;
- inspection;
- analytics;
- backup;
- portability.

Do not make a task-state transition in SQLite and separately append its required attribution to JSONL. That creates a two-phase failure without a transaction.

## ADR-4: Every mutation goes through one service layer

Create:

```text
brotherme/core/project_service.py
```

or an equivalent narrow module.

All public operations call this layer. It owns:

- transactions;
- idempotency;
- state validation;
- dependency validation;
- evidence requirements;
- attribution;
- forecast history;
- alert creation and resolution;
- generated-view refresh requests.

No command writes project tables directly.

## ADR-5: Generated views are disposable

Generate:

- `CANVAS.md`;
- `STATUS.md`;
- `DELIVERY-PACKET.md`;
- `Documentation/`;
- HTML deep tour;
- runtime summaries.

A deleted view can be regenerated from SQLite. A hand-edited view is never trusted as state.

Human comments may live in clearly separate sections or separate files.

## ADR-6: One public product command

Add one primary command:

```text
/brotherme <goal or request>
```

It routes to start, status, next, review, delivery, help, or update based on project state and user wording.

Keep existing commands as discoverable aliases for advanced or explicit use.

Do not add more public commands in this loop.

## ADR-7: Runtime-specific logic stays in adapters

Core project behavior must not know whether the caller is Claude, Codex, Gemini, Qwen, Kimi, Cursor, or another interface.

Runtime adapters normalize:

- session identity;
- model identity;
- tool name;
- tool input;
- lifecycle event;
- token telemetry;
- write path;
- command registration;
- hook decision output.

## ADR-8: Evidence precedes advancement

A state may advance only when its evidence rule passes.

Examples:

- `active → awaiting review`: expected outputs exist.
- `awaiting review → verified`: reviewer is independent and checks pass after final edit.
- `verified → accepted`: authorized human or explicit configured owner accepts.
- `accepted → delivered`: delivery artifact or target reference exists.
- `delivered → monitored`: monitoring window and signal are defined.
- `monitored → closed`: monitoring window ended and unresolved critical alerts equal zero.

---

# 8. Target SQLite extension

Fable must approve the final DDL before implementation.

## 8.1 Minimum tables

### `projects`

```sql
project_id TEXT PRIMARY KEY
name TEXT NOT NULL
goal TEXT NOT NULL
user_outcome TEXT
project_type TEXT
primary_persona TEXT
experience_level TEXT
status TEXT NOT NULL
phase TEXT NOT NULL
scope_in_json TEXT NOT NULL
scope_out_json TEXT NOT NULL
success_criteria_json TEXT NOT NULL
assumptions_json TEXT NOT NULL
unknowns_json TEXT NOT NULL
risks_json TEXT NOT NULL
created_at TEXT NOT NULL
updated_at TEXT NOT NULL
version INTEGER NOT NULL
```

### `forecasts`

```sql
forecast_id TEXT PRIMARY KEY
project_id TEXT NOT NULL
minimum_duration_minutes INTEGER
likely_duration_minutes INTEGER
maximum_duration_minutes INTEGER
input_token_min INTEGER
input_token_max INTEGER
output_token_min INTEGER
output_token_max INTEGER
effective_token_min INTEGER
effective_token_max INTEGER
confidence TEXT NOT NULL
assumptions_json TEXT NOT NULL
unknowns_json TEXT NOT NULL
calculation_basis TEXT NOT NULL
next_reforecast_event TEXT
created_at TEXT NOT NULL
supersedes_forecast_id TEXT
FOREIGN KEY(project_id) REFERENCES projects(project_id)
```

Forecasts are append-only.

### `project_tasks`

```sql
task_id TEXT PRIMARY KEY
project_id TEXT NOT NULL
title TEXT NOT NULL
user_value TEXT
reason TEXT
status TEXT NOT NULL
priority INTEGER NOT NULL
assigned_human TEXT
assigned_runtime TEXT
assigned_model_profile TEXT
assignment_reason TEXT
reviewer_runtime TEXT
reviewer_model_profile TEXT
read_scope_json TEXT NOT NULL
write_scope_json TEXT NOT NULL
expected_outputs_json TEXT NOT NULL
acceptance_checks_json TEXT NOT NULL
time_forecast_json TEXT
token_forecast_json TEXT
confidence TEXT
actual_time_seconds INTEGER
actual_input_tokens INTEGER
actual_output_tokens INTEGER
actual_effective_tokens INTEGER
blockers_json TEXT NOT NULL
started_at TEXT
completed_at TEXT
version INTEGER NOT NULL
FOREIGN KEY(project_id) REFERENCES projects(project_id)
```

### `task_dependencies`

```sql
task_id TEXT NOT NULL
depends_on_task_id TEXT NOT NULL
created_at TEXT NOT NULL
PRIMARY KEY(task_id, depends_on_task_id)
FOREIGN KEY(task_id) REFERENCES project_tasks(task_id)
FOREIGN KEY(depends_on_task_id) REFERENCES project_tasks(task_id)
```

The service must reject cycles.

### `attribution_events`

```sql
event_id TEXT PRIMARY KEY
project_id TEXT NOT NULL
task_id TEXT
event_type TEXT NOT NULL
actor_type TEXT NOT NULL
actor_name TEXT NOT NULL
runtime TEXT
model TEXT
session_id TEXT
action TEXT NOT NULL
reason TEXT
input_artifacts_json TEXT NOT NULL
output_artifacts_json TEXT NOT NULL
evidence_ref TEXT
commit_sha TEXT
created_at TEXT NOT NULL
event_hash TEXT NOT NULL
previous_event_hash TEXT
FOREIGN KEY(project_id) REFERENCES projects(project_id)
FOREIGN KEY(task_id) REFERENCES project_tasks(task_id)
```

A hash chain is optional for ordinary use but recommended because it makes rewritten historical attribution detectable.

### `project_alerts`

```sql
alert_id TEXT PRIMARY KEY
project_id TEXT NOT NULL
task_id TEXT
severity TEXT NOT NULL
category TEXT NOT NULL
dedupe_key TEXT NOT NULL
message TEXT NOT NULL
why_it_matters TEXT
recommended_action TEXT
requires_human INTEGER NOT NULL
created_at TEXT NOT NULL
resolved_at TEXT
resolution_evidence_ref TEXT
UNIQUE(project_id, dedupe_key, resolved_at)
```

Use a partial unique index for unresolved alerts if supported.

### `evidence_refs`

```sql
evidence_id TEXT PRIMARY KEY
project_id TEXT NOT NULL
task_id TEXT
kind TEXT NOT NULL
label TEXT NOT NULL
uri_or_path TEXT NOT NULL
commit_sha TEXT
content_hash TEXT
check_name TEXT
check_exit_code INTEGER
recorded_at TEXT NOT NULL
recorded_by_event_id TEXT
```

### `runtime_runs`

```sql
run_id TEXT PRIMARY KEY
project_id TEXT
task_id TEXT
runtime TEXT NOT NULL
model TEXT
session_id TEXT
started_at TEXT NOT NULL
ended_at TEXT
input_tokens INTEGER
output_tokens INTEGER
cache_read_tokens INTEGER
reasoning_tokens INTEGER
tool_calls INTEGER
measurement_quality TEXT NOT NULL
```

`measurement_quality` must be one of:

- `measured`;
- `partially_measured`;
- `estimated`;
- `not_available`.

Never convert missing telemetry into zero.

---

# 9. Atomic service operations

Each operation below must update state and attribution in one SQLite transaction.

## 9.1 Project operations

- `create_project`
- `update_project_direction`
- `approve_project_canvas`
- `archive_project`

## 9.2 Forecast operations

- `create_forecast`
- `reforecast`
- `record_actuals`

Never edit an existing forecast. Append a new one that supersedes it.

## 9.3 Task operations

- `create_task`
- `add_dependency`
- `make_ready`
- `start_task`
- `block_task`
- `unblock_task`
- `submit_for_review`
- `record_review`
- `verify_task`
- `accept_task`
- `deliver_task`
- `start_monitoring`
- `close_task`
- `reopen_as_new_task`

A closed task remains terminal. New work links to the previous task.

## 9.4 Evidence operations

- `record_check`
- `record_artifact`
- `record_commit`
- `record_pull_request`
- `record_deployment`
- `record_monitoring_signal`

## 9.5 Alert operations

- `raise_alert`
- `escalate_alert`
- `resolve_alert`

Duplicate causes update or escalate one unresolved alert, not create noise.

---

# 10. Loop 0 — Release truth and feature freeze

## Objective

Remove version ambiguity and create a stable base for implementation.

## Why first

Every later test, installation, migration, and runtime adapter must identify the exact source tree. Continuing on an ambiguous release identity poisons all later evidence.

## Fable work

- inspect tags, commits, versions, manifests, changelog, README, release docs;
- decide whether `rc.11` is never-tagged or published;
- specify the next development and candidate versions;
- review release-identity tests;
- approve the freeze list.

## Builder work

1. Set a development version.
2. Synchronize:
   - `VERSION`;
   - `pyproject.toml`;
   - plugin manifest;
   - marketplace manifest;
   - generated facts;
   - changelog;
   - quickstart;
   - release docs.
3. Mark never-tagged versions clearly.
4. Add a test:
   - released version requires a resolvable tag;
   - development version must not claim a release tag;
   - main after a release must use a development identity.
5. Add a test that the README install target resolves through a local mock or remote release verification lane.
6. Freeze new features.

## Acceptance gates

- one current development identity;
- no nonexistent tag in beginner install instructions;
- no two commits claim the same release version;
- all manifests agree;
- test suite green;
- Fable release-truth review passes.

## Rollback

Revert this loop as one commit. No data migration occurs.

## Planning range

- Time: 0.5–1.5 working days.
- Tokens: 40k–95k.
- Confidence: Medium.

---

# 11. Loop 1 — Unify project state in SQLite

## Objective

Eliminate competing state systems.

## Why second

Every beginner command, status view, forecast, alert, runtime adapter, and delivery check depends on a stable state contract.

## Fable work

- approve final schema;
- decide migration version;
- review concurrency and transaction boundaries;
- identify existing store tables that can be reused;
- refuse unnecessary duplication;
- write implementation briefs for separate non-overlapping modules.

## Builder work

1. Extend the existing `bm_store.py` migration chain.
2. Add canonical project tables.
3. Introduce `project_service.py`.
4. Move canonical transitions into service operations.
5. Store attribution in SQLite.
6. Keep JSONL as generated export only.
7. Implement idempotency keys.
8. Implement dependency-cycle detection.
9. Implement task readiness query.
10. Add migration backup and rollback evidence.
11. Add read-only compatibility for old stores.
12. Add a migration report shown once.

## Required properties

- a state transition cannot commit without its attribution event;
- an attribution event cannot claim a state transition that did not commit;
- repeated identical requests are idempotent;
- stale expected versions refuse;
- concurrent task claims cannot both succeed;
- dependency cycles refuse;
- a deleted generated view does not damage state;
- a corrupted export does not quarantine the store;
- a corrupted store is quarantined without deletion.

## Tests

### Unit

- field validation;
- transition rules;
- dependency rules;
- alert deduplication;
- forecast append-only behavior.

### Transactional

Seed failures:

- exception after state update but before event insert;
- exception after event insert but before commit;
- two writers claiming one task;
- stale version;
- duplicate event id;
- repeated delivery request.

### Migration

- empty store;
- current live schema;
- oldest supported V2 fixture;
- store with learning rules;
- store with active thread;
- store with quarantined side file;
- interrupted migration.

### Property tests

- every legal forward lifecycle;
- every illegal skip;
- every backward move requires reason;
- closed is terminal;
- ready means dependencies satisfied;
- no two active tasks have overlapping protected write scopes in the same workspace.

## Acceptance gates

- all canonical data persists in SQLite;
- JSONL is not required for correctness;
- old functionality remains green;
- migration is reversible from backup;
- Fable cannot produce a split-brain scenario using the supported APIs;
- generated views can be deleted and regenerated identically.

## Rollback

- migration backup;
- schema version check;
- explicit downgrade not required, but restoration from pre-migration backup must be tested;
- release cannot proceed while any live store is only partially migrated.

## Planning range

- Time: 2–5 working days.
- Tokens: 250k–600k.
- Confidence: Low until Fable reviews current schema internals.

---

# 12. Loop 2 — Make the beginner layer executable

## Objective

Turn friendly commands into real operations over the authoritative store.

## Public experience

The preferred interaction becomes:

```text
/brotherme Build a multilingual booking product
```

BrotherME then recognizes the current state and enters the correct flow.

Aliases remain:

- `/brotherme-start`
- `/brotherme-status`
- `/brotherme-next`
- `/brotherme-review`
- `/brotherme-deliver`
- `/brotherme-help`
- `/brotherme-update`

## Internal CLI

Create one internal CLI, for example:

```text
bm-project
```

Minimum commands:

```text
bm-project setup
bm-project create
bm-project status --json
bm-project next --json
bm-project task-start
bm-project task-block
bm-project task-submit
bm-project review
bm-project verify
bm-project accept
bm-project deliver
bm-project monitor
bm-project close
bm-project forecast
bm-project alert
bm-project evidence
bm-project export
bm-project delete
bm-project doctor
```

These are internal and may be numerous. The user sees one product command.

## Fable work

- map every guided flow to exact service operations;
- decide what requires human confirmation;
- define minimal question policy;
- review all default user-visible language;
- verify that every displayed field has a mechanical source.

## Builder work

### `/brotherme-start`

1. Run setup if needed.
2. Create Project record.
3. Conduct only scope-changing questions.
4. Store decisions.
5. Create initial Forecast.
6. Generate and show Canvas.
7. Record explicit approval.
8. Create initial Tasks.
9. Generate `CANVAS.md` view.

### `/brotherme-status`

1. Query SQLite.
2. Compute:
   - accepted tasks over planned tasks;
   - active task;
   - unresolved decision;
   - latest forecast;
   - unresolved changed risk;
   - latest evidence;
   - deterministic next task.
3. Render exactly the eight beginner fields.
4. Never read nearby files as authority.

### `/brotherme-next`

1. Query dependency-ready tasks.
2. Rank deterministically.
3. Return one recommended next task.
4. If blocked on a human decision, return a decision card.
5. Store the recommendation event.

### `/brotherme-review`

1. Freeze implementation commit.
2. Assign an independent reviewer.
3. Record reviewer identity.
4. Run declared checks.
5. Attach evidence.
6. Advance or return the task to active with reason.

### `/brotherme-deliver`

1. Confirm all required tasks verified or accepted.
2. Confirm checks ran after final relevant change.
3. Generate Delivery Packet.
4. Require explicit acceptance when configured.
5. Record delivery evidence.
6. Start monitoring or explain why monitoring is not applicable.

## User-visible rule

Every displayed claim must carry one of:

- `measured`;
- `derived`;
- `estimated`;
- `not available`.

The label may remain hidden in the beginner view but must exist in the advanced view and data.

## Acceptance gates

- no command treats Markdown as authority;
- one restart does not lose state;
- status after restart is identical;
- every action appears in attribution;
- no task advances without evidence;
- the default view remains readable in under one minute;
- five scripted personas complete the flow without internal terminology.

## Rollback

Command files can revert while the new store remains. The old expert CLI must continue to function during the candidate period.

## Planning range

- Time: 2–4 working days.
- Tokens: 180k–420k.
- Confidence: Low.

---

# 13. Loop 3 — First-run setup, installation, update, and uninstall

## Objective

Make installation and first use beginner-safe and consent-first.

## 13.1 Canonical installation

The primary installation path is the Claude plugin/marketplace path.

The pinned clone becomes an advanced fallback and recovery path.

## 13.2 First-run configuration

Use one small local config file:

```text
~/.brotherme/config.json
```

Example:

```json
{
  "schema_version": 1,
  "setup_complete": true,
  "vault_path": "/Users/name/BrotherModeVault",
  "privacy_notice_version": "2026-08-01",
  "installation_mode": "plugin",
  "security_mode": "standard"
}
```

Do not require shell-profile environment variables for normal users.

Retain environment variables as advanced overrides.

## 13.3 Consent order

Before any hook writes user content:

1. detect that setup is incomplete;
2. perform no content write;
3. show one plain notice at the first interactive BrotherME command;
4. ask where private memory should live;
5. explain what is stored;
6. create configuration only after confirmation;
7. run doctor;
8. begin the project.

SessionStart before setup may report that setup is required, but it must not create the vault or store project prose.

## 13.4 Duplicate-install migration

Detect:

- plugin installed;
- old manual clone exists;
- old settings hooks exist;
- development copy exists;
- duplicate manifest names;
- duplicate hook commands.

Offer:

```text
BrotherME found an older manual installation.

Recommended:
Keep the plugin installation and remove only BrotherME's old hook entries.
Your project data and private memory will not be deleted.

[Apply recommended fix]
[Show details]
[Cancel]
```

Do not silently delete user files.

## 13.5 Doctor

`bm-project doctor` verifies:

- version identity;
- manifest agreement;
- plugin root;
- hook registration;
- duplicate hooks;
- Python availability;
- writable config;
- vault permissions;
- project-store health;
- Git availability for autosave;
- runtime adapter state;
- unsupported guarantees.

Return one summary:

```text
Ready
Ready with limitations
Needs action
Unsafe to continue
```

## 13.6 Update

Update flow:

1. read current immutable version;
2. query current release metadata only when user invokes update;
3. identify the proposed immutable tag;
4. show changelog and known limitations;
5. verify the tag exists;
6. verify manifest/checksum;
7. ask for approval;
8. update;
9. restart required runtime;
10. rerun doctor;
11. never touch project data.

## 13.7 Uninstall

One command should:

- disable BrotherME hooks;
- remove plugin;
- preserve project data by default;
- offer export;
- offer project-memory deletion separately;
- explain what remains.

## Tests

- clean macOS user;
- clean Ubuntu user;
- clean WSL user;
- existing manual clone;
- both plugin and manual hooks;
- moved installation path;
- no Python;
- no Git;
- read-only vault;
- interrupted update;
- old version migration;
- uninstall with existing projects.

## Fresh-user gate

At least five people who did not build BrotherME must:

1. install;
2. start;
3. understand where data lives;
4. create a first project;
5. obtain status;
6. uninstall or update;

without developer intervention.

A recorded prompt from the product is allowed. Live human troubleshooting is not.

## Planning range

- Time: 2–4 working days plus user testing.
- Tokens: 130k–350k.
- Confidence: Low.

---

# 14. Loop 4 — Complete the task and delivery spine

## Objective

Make the full lifecycle operational without copying a large project-management suite.

## 14.1 Minimum task graph

Implement only:

- task creation;
- dependencies;
- cycle prevention;
- ready-task query;
- priority;
- active ownership;
- write scope;
- review assignment;
- acceptance checks;
- evidence;
- lifecycle state.

Do not add:

- Gantt charts;
- story points;
- sprints;
- team billing;
- complex resource scheduling;
- custom issue tracker UI.

## 14.2 Work isolation

### Shared tree

- maximum one active writer per protected path;
- active ownership recorded before work;
- overlapping claims refuse.

### Parallel writes

Use separate Git worktrees.

Each task records:

- worktree path;
- base commit;
- branch;
- write scope;
- merge order.

## 14.3 Shell-change reconciliation

Do not attempt to fully parse shell syntax.

Use a stronger pattern:

1. record baseline Git/file state before a mutating task;
2. let the tool run under the normal permission system;
3. inspect changed paths after the operation;
4. compare them to the declared write scope;
5. raise a High alert for escaped changes;
6. refuse review/acceptance until reconciled;
7. preserve evidence.

Add a PostToolUse or equivalent adapter event where available.

This converts arbitrary shell writes from invisible bypasses into detectable scope violations.

## 14.4 Review

Review must be:

- separate runtime session or agent;
- read-only;
- based on acceptance criteria;
- refute-first;
- severity split;
- attached to one commit;
- repeated after any fix affecting reviewed scope.

The reviewer may not edit.

## 14.5 Delivery

Delivery packet includes:

- outcome;
- scope delivered;
- scope not delivered;
- acceptance results;
- final commit;
- checks and timestamps;
- review findings and resolution;
- usage or deployment reference;
- monitoring plan;
- rollback;
- known limitations;
- next recommended action.

## 14.6 Browser and visual QA

Do not build a browser engine.

When the product has a user interface:

- require a browser-capable tool or manual evidence;
- capture screenshots or test artifacts;
- compare against the approved outcome;
- verify responsive and error states;
- record evidence.

## 14.7 Deployment and monitoring

Use an evidence adapter instead of provider-specific logic in the core.

The core only requires:

- delivery target;
- deployment identifier;
- health check;
- rollback reference;
- monitoring period;
- unresolved alerts.

Provider integrations may be added later.

## Acceptance gates

- dependency graph selects the correct next task;
- overlapping writer is blocked;
- shell scope escape is detected;
- writer cannot verify own task;
- review references latest commit;
- a post-review edit invalidates previous verification;
- delivery refuses missing evidence;
- monitoring and closure are distinct.

## Planning range

- Time: 2–5 working days.
- Tokens: 220k–520k.
- Confidence: Low.

---

# 15. Loop 5 — Forecasting, attribution, status, and alerts

## Objective

Make progress communication trustworthy rather than merely polished.

## 15.1 Forecasting

Initial release may use current size bands, but must label their basis as:

```text
planning-envelope
```

After ten completed tasks of a comparable shape, add a simple empirical basis:

- median actual duration;
- 20th–80th percentile duration;
- median effective token use;
- rework frequency;
- confidence from sample size.

Do not add machine learning.

## 15.2 Forecast composition

Separate:

- active work time;
- external waiting time;
- human decision time;
- monitoring time.

Store each where possible.

## 15.3 Reforecast

Reforecast when:

- discovery ends;
- scope changes;
- a dependency is missing;
- actual time exceeds the likely range;
- measured token use approaches the upper range;
- verification creates new tasks;
- a human decision changes direction;
- a task is split or cancelled.

Never silently modify an old forecast.

## 15.4 Attribution

Each meaningful operation records:

- who or what;
- runtime;
- model;
- session;
- task;
- action;
- reason;
- inputs;
- outputs;
- evidence;
- commit;
- timestamp.

## 15.5 Attribution confidence

Add:

```text
actor_identity_quality:
- runtime_measured
- process_declared
- user_declared
- unknown
```

Do not imply cryptographic identity when it is not available.

## 15.6 Status

Default status uses only computed fields:

- Goal;
- Direction;
- Progress;
- Time remaining;
- Decision needed;
- Risk;
- Evidence;
- Next step.

Avoid “70% complete” unless the denominator is measurable.

Prefer:

```text
4 of 9 planned tasks accepted
```

## 15.7 Alerts

Persist and deduplicate alerts.

Minimum severities:

- Info;
- Attention;
- High;
- Critical.

Minimum causes:

- scope escape;
- missing verification;
- stale task;
- forecast movement;
- repeated failure;
- conflicting writer;
- unsupported enforcement claim;
- release identity mismatch;
- data-permission weakness;
- unresolved critical issue.

## 15.8 No false background claim

BrotherME may proactively report during active runtime events.

It must not claim continuous monitoring unless a real scheduled or connected monitor exists.

## Acceptance gates

- all status values trace to records;
- no missing telemetry appears as zero;
- forecast history remains inspectable;
- duplicate alert causes produce one open alert;
- actor identity quality is visible in advanced view;
- status after restart is stable;
- user can understand status without technical terminology.

## Planning range

- Time: 1.5–3 working days.
- Tokens: 120k–300k.
- Confidence: Medium after state unification.

---

# 16. Loop 6 — Security and privacy closure

## Objective

Raise safety through clear boundaries and detection, not through overclaiming.

## 16.1 Threat model

Publish an explicit matrix.

| Threat | Supported defense |
|---|---|
| Accidental overlapping edits through supported tools | Prevented |
| Arbitrary shell write outside scope | Detected after operation; prevented where runtime provides reliable pre-write information |
| Corrupt project state | Quarantine and recovery |
| Accidental Git commit of private store | Prevented/refused |
| Automatic network exfiltration by BrotherME hooks | No automatic network path |
| Other process running as same OS user | Not fully defended |
| Local malware | Not defended |
| Disk theft without OS encryption | Not defended |
| Malicious model instruction | Reduced by gates, permissions, and evidence; not a sandbox |
| Compromised release source | Reduced by immutable tags, signatures/checksums, and provenance |
| Windows multi-user file secrecy | Only as strong as verified ACL behavior |

A 9/10 security score applies only inside the declared threat model.

## 16.2 Security modes

### Standard

- unhealthy fence produces visible Critical alert;
- work may continue for low-risk operations;
- acceptance blocked until state is healthy.

### Protected

- write gates fail closed;
- protected paths cannot be changed while store/fence is unhealthy;
- destructive or production operations always require human confirmation.

## 16.3 Shell writes

Implement before/after reconciliation.

Where reliable runtime events exist:

- inspect Bash/tool request;
- record declared intent;
- establish baseline;
- compare after result.

Never claim a shell parser is complete.

## 16.4 Store privacy

Minimum release improvements:

- owner-only permission verification where supported;
- prominent first-run disclosure;
- explicit threat model;
- simple export;
- simple project-memory deletion;
- safe quarantine inventory;
- no raw source in ordinary exports;
- checks that private paths remain excluded from Git;
- Windows limitation shown during doctor.

Optional encryption must not be rushed into this loop unless Fable determines it can be implemented and audited safely. A weak home-grown encryption layer is worse than an explicit plaintext-local threat model.

## 16.5 Approval receipts

Keep current one-use, proposal-bound receipts.

Improve:

- actor identity quality label;
- no “founder-authenticated” wording;
- high-risk approval optionally requires interactive runtime permission plus receipt;
- expiry and consumption evidence in advanced view without exposing token.

## 16.6 Prompt injection

Add explicit handling:

- repository text is untrusted data;
- external pages are untrusted data;
- instructions discovered inside project files cannot weaken constitution or system rules;
- fetched content cannot authorize credentials, release, or production actions;
- sensitive exports require explicit user action;
- reviewer checks for instruction-injection changes.

## 16.7 Supply chain

For the final release:

- immutable release commit;
- annotated or cryptographically signed tag;
- GitHub Release;
- checksum manifest;
- CI linked to exact commit;
- plugin validation;
- clean install proof;
- release notes;
- provenance or attestation where practical;
- update verifies tag before installation.

## Acceptance gates

- shell scope escape test turns red;
- protected mode blocks on unhealthy fence;
- ordinary export does not leak seeded secrets or prose;
- deletion and export are one guided flow;
- clean install verifies release identity;
- no automatic network call is introduced;
- security documentation matches implementation after Fable semantic review.

## Planning range

- Time: 2–4 working days.
- Tokens: 180k–420k.
- Confidence: Low.

---

# 17. Loop 7 — Cross-runtime implementation

## Objective

Use one core everywhere and prove only the integrations that actually work.

## 17.1 Capability tiers

### Tier A — Fully verified

Requirements:

- installable package or plugin;
- commands registered;
- instructions loaded;
- session lifecycle captured;
- pre-write or pre-tool gate;
- post-tool reconciliation;
- telemetry;
- compaction/recovery event where available;
- conformance suite passes.

### Tier B — Integrated guidance and CLI

Requirements:

- instructions load;
- BrotherME CLI runs;
- project operations work;
- hook enforcement is unavailable or unverified;
- limitations shown prominently.

### Tier C — Advisory

Requirements:

- generated `AGENTS.md` or equivalent;
- user can manually invoke BrotherME CLI;
- no enforcement claim.

## 17.2 Adapter interface

Create:

```text
brotherme/runtimes/base.py
brotherme/runtimes/claude.py
brotherme/runtimes/codex.py
brotherme/runtimes/gemini.py
brotherme/runtimes/qwen.py
brotherme/runtimes/kimi.py
brotherme/runtimes/generic.py
```

Normalized events:

```text
SESSION_START
SESSION_END
USER_PROMPT
BEFORE_TOOL
AFTER_TOOL
TOOL_FAILURE
BEFORE_COMPACT
AFTER_COMPACT
STOP
SUBAGENT_START
SUBAGENT_END
```

Normalized payload:

```json
{
  "runtime": "",
  "runtime_version": "",
  "session_id": "",
  "agent_id": "",
  "agent_type": "",
  "event": "",
  "cwd": "",
  "tool_name": "",
  "tool_input": {},
  "tool_result": {},
  "model": "",
  "token_usage": {},
  "raw_payload_hash": ""
}
```

## 17.3 Payload fixtures

For each Tier A runtime:

1. install the actual runtime;
2. create a minimal fixture repository;
3. register a capture hook;
4. trigger every supported event;
5. store redacted real payload fixtures;
6. write adapter parser tests;
7. write decision-output tests;
8. execute the full conformance scenario.

Do not infer payload shape from event names.

## 17.4 Recommended release order

1. Claude Code
2. Codex CLI
3. Gemini CLI
4. Qwen Code
5. Kimi Code
6. Generic `AGENTS.md`
7. IDEs through the underlying runtime or ACP/MCP

## 17.5 Claude Code

Target Tier A.

Use:

- plugin manifest;
- commands;
- skills;
- hooks;
- model selection;
- Fable as planner/reviewer when available;
- lower Claude profiles as executors.

## 17.6 Codex CLI

Target Tier A if the real hook and plugin surfaces pass conformance.

Use:

- `AGENTS.md` for durable repository guidance;
- project hook config;
- runtime plugin/skill packaging where supported;
- normalized hook adapter;
- Codex model as an optional Builder or independent reviewer.

Do not duplicate project logic in `AGENTS.md`.

## 17.7 Gemini CLI

Target Tier A or B based on hook-extension packaging verified at implementation time.

Use:

- `gemini-extension.json`;
- `GEMINI.md`;
- skills;
- commands;
- hooks;
- IDE integration through Gemini CLI.

Keep Gemini-specific hook format in its adapter package, not the shared Claude hook file.

## 17.8 Qwen Code

Target Tier A.

Qwen Code provides extension packaging and extensive lifecycle hooks. Build a Qwen-specific extension manifest and payload adapter. Even when Qwen can import compatible marketplace assets, use explicit conformance rather than assuming hook compatibility.

## 17.9 Kimi Code

Target Tier A.

Kimi provides plugins, commands, skills, hooks, and ACP integration. Its hooks are documented as fail-open, so BrotherME must not present them as the sole high-risk security boundary. Combine them with permission approval and post-operation scope reconciliation.

## 17.10 Cursor, Windsurf, Cline, Roo, Aider, Copilot and other IDEs

Prefer the simplest truthful route:

- use the Tier A CLI through its IDE integration when available;
- use MCP/ACP when it preserves the runtime;
- otherwise provide Tier C `AGENTS.md` and BrotherME CLI;
- do not build a unique full adapter for every editor in the final loop.

## 17.11 Runtime conformance suite

Every Tier A runtime must complete:

1. install;
2. initialize without writing before consent;
3. create project;
4. create forecast;
5. create tasks;
6. obtain deterministic status;
7. claim task;
8. refuse overlapping writer;
9. detect shell scope escape;
10. record actual runtime/model/session;
11. survive compaction or restart;
12. submit review;
13. independently verify;
14. deliver;
15. export;
16. uninstall without deleting project data.

## Acceptance gates

- no duplicated business logic;
- real payload fixtures;
- three Tier A runtimes minimum for a 9+ breadth claim;
- unsupported runtimes label enforcement as unavailable;
- install and uninstall tested;
- Fable reviews every adapter’s security semantics.

## Planning range

- Time: 4–8 working days.
- Tokens: 350k–850k.
- Confidence: Low.

If time is insufficient, release with Claude Tier A and the others clearly Tier B/C. Do not delay truth to preserve a broad marketing claim.

---

# 18. Loop 8 — Real validation and evidence

## Objective

Replace simulated confidence with actual product evidence.

## 18.1 Founder dogfood project

Use one meaningful project that includes:

- discovery;
- at least ten tasks;
- one external dependency;
- one user-interface or visual check;
- one review failure;
- one reforecast;
- one interruption and recovery;
- one delivery;
- one monitoring period.

Do not use BrotherME’s own repository as the only dogfood project. Self-referential success can hide product assumptions.

## 18.2 External testers

Minimum three:

- one non-technical founder;
- one experienced engineer;
- one user on a different supported OS.

They must use clean profiles or machines.

## 18.3 Comparison

For a small set of matched tasks compare:

- BrotherME;
- plain Claude Code;
- gstack or another lifecycle competitor where appropriate.

Measure:

- time to first useful action;
- questions asked;
- rework;
- escaped defects;
- tokens;
- wall time;
- recovery time;
- status accuracy;
- user understanding;
- delivery completion.

## 18.4 Evidence files

Create:

```text
docs/evidence/2.0/
  release-identity.md
  ci-exact-bytes.md
  clean-install-macos.md
  clean-install-linux.md
  clean-install-wsl.md
  plugin-github-install.md
  runtime-claude-conformance.md
  runtime-codex-conformance.md
  runtime-gemini-conformance.md
  runtime-qwen-conformance.md
  runtime-kimi-conformance.md
  founder-dogfood.md
  external-beginner-test.md
  external-engineer-test.md
  security-adversarial.md
  migration-matrix.md
  benchmark.md
  known-limitations.md
```

Only create runtime files for tested runtimes.

## 18.5 Evidence law

Every evidence file states:

- exact commit;
- exact tag if available;
- environment;
- runtime version;
- commands;
- result;
- what it proves;
- what it does not prove;
- unexpected failures;
- corrective action.

## Acceptance gates

- real project closes;
- three external installations complete;
- critical usability failure rate is zero;
- no unresolved Critical security or data finding;
- release claims match evidence;
- Fable audits the raw evidence, not just summaries.

## Planning range

- Engineering time: 1–3 working days.
- Calendar observation: at least 7 days.
- Tokens: 150k–400k.
- Confidence: Medium.

---

# 19. Loop 9 — Final Fable adversarial release review

## Objective

Attempt to disqualify the release.

Fable must not begin from the assumption that the release should happen.

## 19.1 Review lenses

### Product truth

- Is this a real integrated product or a prompt layer?
- Does every public claim have evidence?
- Is the beginner flow understandable?
- Are unsupported capabilities clearly labeled?

### State and concurrency

- Can two sources disagree?
- Can one operation partially commit?
- Can two writers claim the same scope?
- Can generated views drift?
- Can a stale task be accepted?

### Security and privacy

- Can shell writes escape unnoticed?
- Can a failed hook create a false safety impression?
- Can project content leak in exports, logs, paths, backups, or quarantine?
- Can a malicious repository instruction weaken gates?
- Can an update execute unreviewed moving code?

### Release integrity

- Does the tag exist?
- Does it identify the exact commit?
- Do version files match?
- Does CI run on those bytes?
- Do checksums describe those bytes?
- Does a clean install reproduce them?

### Runtime truth

- Which runtimes are genuinely Tier A?
- Did real payloads pass?
- Does each adapter block and report correctly?
- Are fail-open semantics disclosed?

### User journey

- Can a first-time user install?
- Does first write occur only after consent?
- Can the user understand status?
- Can the user recover?
- Can the user export and delete data?
- Can the user finish a project?

## 19.2 Exact Fable final-review prompt

```text
Act as a hostile release reviewer.

The founder wants to release BrotherME 2.0.
Your task is to stop the release if any public promise, data boundary,
lifecycle transition, installation path, runtime claim, security boundary,
or evidence chain is false, ambiguous, untested, or broader than reality.

Review the exact proposed release commit and tag.

Do not rely on summaries. Inspect:
- implementation;
- migrations;
- commands;
- hook adapters;
- manifests;
- generated views;
- tests;
- evidence;
- known limitations;
- dogfood records;
- external tester records.

Return:
1. GO or NO-GO.
2. Critical findings.
3. High findings.
4. Claims that must be narrowed.
5. Tests that cannot fail for their intended reason.
6. State divergence scenarios.
7. Supply-chain failures.
8. Runtime support table based only on demonstrated behavior.
9. Exact release text you approve.
10. The one strongest reason not to release.

A GO verdict is valid only if no Critical finding remains and every release
gate has direct evidence tied to the proposed tag.
```

## 19.3 Final gate

A release requires:

- Fable `GO`;
- founder approval;
- no Critical findings;
- every High finding resolved or explicitly converted into a scoped known limitation that does not contradict the release promise;
- exact-byte CI green;
- clean installation;
- real dogfood;
- external user evidence;
- release tag created immediately from the approved commit.

---

# 20. Final release procedure

## 20.1 Pre-release

1. Freeze branch.
2. Run full deterministic gate.
3. Run runtime conformance.
4. Run migration matrix.
5. Run fresh installs.
6. Run privacy/security fixtures.
7. Generate docs from current facts.
8. Fable semantic documentation review.
9. Generate checksums last.
10. Commit release candidate.
11. Confirm clean tree.
12. Fable final review.

## 20.2 Founder-gated release

1. Update version to `2.0.0`.
2. Create final changelog.
3. Generate final checksums.
4. Verify files.
5. Commit.
6. Create annotated or signed `v2.0.0` tag immediately.
7. Push the tag.
8. Confirm the remote resolves it.
9. Confirm CI runs on the exact tag commit.
10. Create GitHub Release with checksums and evidence links.
11. Submit or publish marketplace entry.
12. Test public installation from the release source.
13. Bump `main` to `2.0.1.dev1`.

## 20.3 Public release promise

Recommended:

> BrotherME guides a founder from an idea to a verified delivery while preserving project direction, decisions, attribution, recovery, and human control. Claude Code is the primary verified runtime. Other runtimes are labeled according to their tested integration level. BrotherME keeps its own project memory locally and does not call the network automatically.

Do not claim:

- guaranteed quality;
- complete security;
- support for every IDE;
- cryptographically authenticated founder approval;
- semantic memory in every language;
- continuous monitoring without a monitor;
- one-writer enforcement over arbitrary filesystem processes;
- proven productivity beyond measured trials.

---

# 21. File-level implementation map

## Existing files likely modified

```text
VERSION
pyproject.toml
README.md
CHANGELOG.md
SECURITY.md
SKILL.md
docs/KNOWN-LIMITS.md
docs/NOT-FINALIZED.md
docs/RELEASE.md
docs/QUICKSTART.md
docs/RUNTIMES.md
docs/specs/canonical-project-protocol.md
.claude-plugin/plugin.json
.claude-plugin/marketplace.json
hooks/hooks.json
commands/brotherme*.md
references/forecasting.md
references/status-view.md
references/pulse.md
references/delegation.md
tools/bm_store.py
tools/bm_threads.py
tools/bm_telemetry.py
tools/bm_fence_hook.py
tools/bm_autosave.py
tools/bm_project_facts.py
tools/test_all.py
.github/workflows/tests.yml
```

## New files recommended

```text
brotherme/core/project_service.py
brotherme/core/project_views.py
brotherme/core/runtime_events.py
brotherme/runtimes/base.py
brotherme/runtimes/claude.py
brotherme/runtimes/codex.py
brotherme/runtimes/gemini.py
brotherme/runtimes/qwen.py
brotherme/runtimes/kimi.py
brotherme/runtimes/generic.py
tools/bm_project.py
tools/test_bm_project_service.py
tools/test_bm_project_cli.py
tools/test_bm_runtime_adapters.py
tools/test_bm_install_e2e.py
tools/test_bm_release_truth.py
docs/release/FINAL-RELEASE-PLAN-FABLE-REVIEW.md
docs/release/FINAL-RELEASE-GO-NO-GO.md
```

Avoid creating separate codebases under each runtime folder. Packaging manifests may differ; core logic must not.

---

# 22. Test pyramid

## Layer 1 — Pure deterministic tests

- schema;
- transitions;
- dependency cycles;
- forecast append-only behavior;
- alert deduplication;
- evidence requirements;
- adapter parsing;
- user-view rendering.

## Layer 2 — SQLite integration

- atomic transitions;
- migration;
- concurrency;
- stale versions;
- idempotency;
- crash injection;
- quarantine;
- permissions.

## Layer 3 — CLI integration

- setup;
- create;
- status;
- next;
- review;
- deliver;
- export;
- delete;
- doctor.

## Layer 4 — Runtime conformance

- real hook payload;
- allow/deny behavior;
- command registration;
- restart;
- compaction;
- telemetry;
- installation.

## Layer 5 — User journey

- beginner;
- engineer;
- interrupted project;
- cross-runtime;
- delivery and monitoring.

## Layer 6 — Release truth

- version;
- tag;
- manifest;
- checksum;
- exact CI commit;
- clean installation;
- update;
- uninstall.

A green lower layer cannot substitute for a missing higher layer.

---

# 23. Work briefs

Every Fable brief must use this template.

```text
Task:
User value:
Failure being closed:
Why now:
Dependencies:

Readable files:
Writable files:
Forbidden files:

Required behavior:
Non-goals:
Compatibility constraints:
Migration constraints:
Security constraints:

Implementation guidance:
- smallest seam;
- existing abstraction to reuse;
- behavior that must remain unchanged.

Done-check:
- exact command;
- expected result;
- calibration or seeded failure.

Return:
- changed files;
- behavior;
- tests;
- exact gate line;
- remaining uncertainty.

Time range:
Token range:
Confidence:
Rollback:
```

No implementation brief may say “update relevant files.” It must name them.

---

# 24. Progress reporting during the loop

Use one release pulse after each merged loop.

```text
Final release pulse

Status:
Loop completed:
Release blockers closed:
Release blockers remaining:
Forecast:
Tokens:
Evidence:
New risk:
Decision needed:
Next:
```

Do not report percentages unless based on closed blockers over fixed blockers.

Recommended progress unit:

```text
6 of 10 release gates passed
```

---

# 25. Stop conditions

Stop implementation and return to Fable when:

- architecture changes;
- migration affects unexpected tables;
- a lower model needs files outside its brief;
- a test must be weakened;
- two authoritative state paths remain;
- an adapter payload differs materially from documentation;
- a release claim must expand;
- the task exceeds its upper budget by 30%;
- the same done-check fails twice;
- security failure appears in a shared abstraction;
- backward compatibility cannot be preserved;
- Fable finds a new Critical issue.

---

# 26. Go/no-go matrix

| Gate | GO condition | Automatic NO-GO |
|---|---|---|
| Release identity | Remote tag resolves to approved commit | Missing, late, moved, or ambiguous tag |
| State authority | SQLite is sole authority | Markdown/JSONL can disagree |
| Atomicity | State and attribution commit together | Partial commit possible |
| Beginner install | Fresh users install unaided | Manual developer fix required |
| Consent | No content write before setup consent | Hook writes private content first |
| Status | Every field derived from store | Model reconstructs from prose |
| Task graph | Dependencies and claims enforced | Two writers or cycle succeeds |
| Review | Independent and latest-commit | Writer self-verifies |
| Delivery | Evidence after final change | Delivery without proof |
| Shell scope | Escape detected and blocks acceptance | Escape is invisible |
| Privacy | Export/delete/permissions pass | Seeded data leaks |
| Runtime | Claimed tier passes conformance | Documentation-only support |
| Migration | All fixtures migrate and recover | Partial or destructive migration |
| CI | Green on exact release commit | Green exists only on another commit |
| Real use | Dogfood and external tests complete | No real project |
| Fable | Final verdict GO | Critical or unresolved NO-GO |

---

# 27. Target post-loop scorecard

These are achievable only if the gates pass.

| Metric | Expected score |
|---|---:|
| Vision and differentiation | 9.6 |
| Founder governance | 9.7 |
| Release integrity | 9.5 |
| Project-state correctness | 9.4 |
| Beginner language and UX | 9.2 |
| Installation | 9.2 |
| Full lifecycle | 9.1 |
| Attribution and status | 9.2 |
| Forecast transparency | 9.0 |
| Verification and review | 9.4 |
| Recovery | 9.3 |
| Privacy within declared threat model | 9.1 |
| Security within declared threat model | 9.0 |
| Maintainability | 9.1 |
| Cross-runtime architecture | 9.3 |
| Cross-runtime verified breadth | 8.0–9.2 depending on actual conformance |
| Real-world validation at release | 7.5–8.5 |
| Real-world validation after 30 days | 9.0+ if evidence supports it |

The overall product may exceed 9 only after real-world validation stops being the limiting factor.

---

# 28. Simplifications that prevent rework

1. Extend SQLite; do not introduce another database.
2. Generate files; do not synchronize hand-edited copies.
3. One service layer; do not let commands write tables.
4. One public command; keep aliases.
5. One runtime-neutral event contract; adapters only translate.
6. Do not build a browser, deployment platform, issue tracker, or monitoring service.
7. Store evidence references and integrate existing tools.
8. Use static forecast bands until enough actual data exists.
9. Use worktrees and after-the-fact reconciliation rather than a complete shell parser.
10. Archive historical docs instead of continuously patching old operational prose.
11. Use a small number of high-value end-to-end tests.
12. Stop adding personas and tutorials until the product proves the path.

---

# 29. Recommended final timeline

This is a planning range, not a promise.

| Phase | Likely duration |
|---|---:|
| Fable plan review | 0.5–1 day |
| Release truth and freeze | 0.5–1.5 days |
| State unification | 2–5 days |
| Guided command integration | 2–4 days |
| Onboarding and installation | 2–4 days |
| Task/delivery spine | 2–5 days |
| Forecast, attribution, alerts | 1.5–3 days |
| Security closure | 2–4 days |
| Runtime adapters | 4–8 days |
| Engineering validation | 1–3 days |
| Required dogfood observation | 7 calendar days |
| Final Fable review and release | 0.5–1.5 days |

**Likely total:** approximately 2–4 calendar weeks, depending primarily on runtime breadth and defects found.

The fastest responsible route to release is:

- fully verify Claude;
- verify two additional runtimes;
- label all others as guidance/CLI compatible;
- release the narrow truth;
- expand after evidence.

Attempting five full runtime integrations before the core state is unified is the highest-rework path and must be refused.

---

# 30. Final recommendation to Fable

Fable should approve the plan only if it agrees with the following priority:

1. Release identity.
2. Single source of truth.
3. Executable beginner commands.
4. Consent-first installation.
5. Task and evidence lifecycle.
6. Security boundary closure.
7. Runtime adapters.
8. Real usage.
9. Final release.

If Fable recommends a different order, it must demonstrate the dependency that justifies it.

The best path to success is not to add more sophistication.

It is to make these five statements mechanically true:

1. The user can install BrotherME easily.
2. BrotherME always knows the authoritative project state.
3. Every task has a reason, owner, budget, status, and evidence.
4. Nothing is delivered without independent verification after the final change.
5. Every public claim identifies the exact boundary and evidence behind it.

When those are true, BrotherME becomes a coherent product rather than an exceptional collection of safeguards and instructions.

---

# 31. Source assumptions for runtime planning

The implementation team must re-check current official documentation during Fable’s review because runtime contracts change quickly.

Useful current primary references include:

- Anthropic Claude Fable and advisor/orchestration guidance:
  - https://www.anthropic.com/claude/fable
  - https://www.anthropic.com/webinars/building-on-the-claude-platform-claude-fable-5-and-model-orchestration-patterns
- OpenAI Codex repository and configuration:
  - https://github.com/openai/codex
  - https://developers.openai.com/codex/config-advanced
- Gemini CLI extension and hook documentation:
  - https://github.com/google-gemini/gemini-cli/blob/main/docs/extensions/index.md
  - https://github.com/google-gemini/gemini-cli/blob/main/docs/hooks/writing-hooks.md
- Qwen Code extension and hook documentation:
  - https://qwenlm.github.io/qwen-code-docs/en/users/extension/introduction/
  - https://qwenlm.github.io/qwen-code-docs/en/users/features/hooks/
- Kimi Code plugin and hook documentation:
  - https://www.kimi.com/code/docs/en/kimi-code-cli/customization/plugins.html
  - https://www.kimi.com/code/docs/en/kimi-code-cli/customization/hooks.html

These references justify an adapter architecture. They do not constitute proof that BrotherME works in those runtimes. Only real conformance runs can do that.
