# Canonical project protocol

Status: CURRENT. This is a specification document: it defines the shared
vocabulary (lifecycle states and object shapes) that every BrotherMode
surface, chat summaries, status views, templates, and future tooling, is
expected to speak.

Implementation status, updated 2026-08-01 (Loop 2 of the release-closure
program): the five objects and the ten states are enforced in code.
brotherme/core/schema.py holds the shapes and the legality rules;
tools/bm_store.py stores them (schema 12) with an attribution row written
in the same transaction as every mutation; tools/bm_project.py is the
command surface. `project-template/CANVAS.md` and
`project-template/DELIVERY-PACKET.md` remain as the layout the generated
views follow; the generated files are views of the store, never the truth.

Source: the dated source plan recorded at
`docs/evidence/2026-08-01-source-BrotherME_Final_Release_Closure_Plan_Fable_Governed.md`,
whose section 7 carries the same lifecycle transitions and names the same
canonical objects this page defines. That file is a dated record and keeps the
title it was written under; this document restates its rules as the normative
reference so the plan can evolve while this page stays the contract.

## 1. Task lifecycle: the ten states

A task is always in exactly one of these states:

1. `planned`: the task is defined but nothing may start yet.
2. `ready`: everything the task depends on is satisfied; it can be picked up.
3. `active`: someone or something is working on it right now.
4. `blocked`: work cannot continue until a named blocker is cleared.
5. `awaiting review`: the work is finished by its writer and waits for an
   independent reviewer.
6. `verified`: the acceptance checks have passed, with evidence produced
   after the final edit.
7. `accepted`: the person who owns the outcome has approved the result.
8. `delivered`: the result is in the hands of its user.
9. `monitored`: the result is delivered and being watched for problems during
   an agreed window.
10. `closed`: the monitoring window is over and the task is finished for good.

The rule that makes this list mean something: `Done` is not a valid state.
No object in this protocol may carry a state with that name. Instead of one
vague word, this list gives each stage of finishing its own precise name, so
a status always says which evidence and review requirements have been met
rather than hiding whether any were.

State changes move forward through this list. Moving backward (for example
`awaiting review` back to `active` when a reviewer finds a problem) is normal
and must be recorded with a reason, never silent.

## 2. The five object shapes

These are the canonical objects. Field lists are normative: an implementation
must carry every field named here. The shapes are given in YAML form exactly
as the roadmap defines them.

These objects are the single source for chat summaries, CLI status, IDE
panels, reports, and future team views. A surface that shows project state
shows a view of these objects, never a parallel bookkeeping of its own.

### 2.1 Project

One per project. The durable identity and direction of the work; the Project
Canvas is the human-readable view of this object.

```yaml
project_id:
name:
goal:
user_outcome:
project_type:
primary_persona:
experience_level:
status:
phase:
scope_in:
scope_out:
success_criteria:
assumptions:
unknowns:
risks:
kill_criteria:
non_goals:
created_at:
updated_at:
```

`kill_criteria` and `non_goals` joined this shape at schema 19 (R1.1,
2026-08-12). Both are JSON lists, defaulting to empty, exactly as `risks` is.
They are here because PRODUCT-DIRECTION.md section 5.1 names both as things a
project's outcome contract must own, and until now neither could be recorded
at all: a project could state what it was for and what would go wrong, but not
what would make it right to stop, nor what it had deliberately decided not to
be. An empty list means not stated, which is different from stated as none,
and nothing here pretends otherwise.

### 2.2 Forecast

An estimate, always as ranges with a stated confidence, never a single
number. A new forecast object is created at each reforecast; earlier ones are
kept, so the history of estimates is inspectable.

```yaml
forecast_id:
project_id:
minimum_duration:
likely_duration:
maximum_duration:
input_token_range:
output_token_range:
effective_total_token_range:
confidence: low | medium | high
assumptions:
unknowns:
calculation_basis:
next_reforecast_event:
created_at:
```

### 2.3 Task

One unit of work. Its `status` field holds exactly one of the ten lifecycle
states from section 1. Its scope fields (`read_scope`, `write_scope`) are the
protocol form of the one-writer-per-file rule: two tasks may not hold
overlapping write scopes at the same time.

```yaml
task_id:
project_id:
title:
user_value:
reason:
status:
priority:
depends_on:
assigned_human:
assigned_runtime:
assigned_model_profile:
assignment_reason:
reviewer_runtime:
reviewer_model_profile:
read_scope:
write_scope:
expected_outputs:
acceptance_checks:
time_forecast:
token_forecast:
confidence:
actual_time:
actual_tokens:
evidence:
blockers:
started_at:
completed_at:
phase:
```

### 2.4 Attribution event

One recorded action: who or what did something, why, and what it produced.
The append-only stream of these events is how "who did what" is answered
from records rather than from memory.

```yaml
event_id:
project_id:
task_id:
event_type:
actor_type: human | model | hook | automation
actor_name:
runtime:
model:
session_id:
action:
reason:
input_artifacts:
output_artifacts:
evidence_ref:
timestamp:
```

### 2.5 Alert

One thing the user should know about, with its severity and what to do. The
`requires_human` field is the line between "for your information" and "work
is waiting on you".

```yaml
alert_id:
severity: info | attention | high | critical
category:
message:
why_it_matters:
recommended_action:
requires_human:
created_at:
resolved_at:
```

## 3. What conformance means today

Because no implementation exists yet, conformance today means: documents,
templates, and skill instructions in this repository use these state names
and field names when they talk about lifecycle or project objects, and do
not invent parallel vocabularies. When the implementation is built, its
storage and its tests become the enforcement; this page then remains the
reference the implementation is tested against.
