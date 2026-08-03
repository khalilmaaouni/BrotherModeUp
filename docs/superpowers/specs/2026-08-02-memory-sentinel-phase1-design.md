# Memory Sentinel, Phase 1 design (the implementable spec)

Status: CURRENT. Written 2026-08-02 by the orchestrator (Fable) as sole writer of
this file. Ratified inputs: the founder answered two decision windows on
2026-08-02, choosing reversible-everything autonomy and the trigger-point,
silence-biased sentinel over the every-step variant. Proposal:
`docs/proposals/2026-08-02-full-auto-and-codex-execution-modes.md` (in the
`main` checkout at `~/Documents/BrotherModeUp`, not yet on this branch).

This file is the SINGLE SOURCE OF TRUTH for the three implementer briefs.
Implementers POINT at this file by path and line range; they never restate it.
Where this file and an implementer's memory disagree, this file wins. Where this
file and the shipped code disagree, that is a finding to report, not a thing to
silently reconcile.

## 0. What is being built, in one paragraph

A watcher that records what the working agent has learned (requirements,
environment facts, what already failed) and, at five named moments, decides
whether to surface exactly one reminder or to stay silent. Silence is the
default and is recorded as a decision with its reason, not as an absence.
Every decision, injected or silent, writes one row so that "did the reminder
help" is answerable from rows later instead of from anybody's impression.

Grounding, so nobody has to take the design on faith: Meta's arXiv 2607.08716
measured that exposing the whole memory bank passively scored WORSE than
selective injection (61.5 vs 64.3 macro average), that removing the silence
option also lost (63.5 vs 64.3), and that an uncalibrated memory agent made its
worker actively worse (reward 0.709 down to 0.693). Those three results are why
this design is silence-biased, one-reminder-at-a-time, and measured from day one.

## 1. Scope of Phase 1

IN: schema 12 to 13 migration with four tables; Store methods over them; a new
module `tools/bm_sentinel.py` with a command line; a new suite
`tools/test_bm_sentinel.py`; registration of that suite in BOTH
`tools/test_all.py` and `.github/workflows/tests.yml`.

OUT (Phase 2 or later, do not build): the Full-Auto autonomy contract, the
circuit breaker, the kill switch, wiring the sentinel into any hook, any model
call from inside the sentinel, and any automatic judging of whether an
intervention helped.

DELIBERATELY NOT A MODEL CALL. The Phase 1 selection policy is deterministic
(section 4). This follows the project's own L18 discipline: try the mechanical
check first, and record which one answered. A model-scored selector is a Phase 4
question to be settled by the calibration ledger this phase creates, not by
preference now.

## 2. Storage: schema 12 to 13, additive only

Follow `_migrate_11_to_12` exactly (tools/bm_store.py:2500-2523) as the template:
one `_SENTINEL_DDL` string split by the existing `_split_ddl` helper the same way
`_LOOP1_DDL_STATEMENTS` is built (tools/bm_store.py:2128-2129), a
`_migrate_12_to_13(conn)` function whose body is two loops over the DDL and index
statement lists, an entry `12: _migrate_12_to_13` appended to `_MIGRATIONS`
(tools/bm_store.py:2526-2538), and a matching `if SCHEMA_VERSION >= 13:` block at
the end of `_ensure_schema` (tools/bm_store.py:4299-4308 shows the shape).
`SCHEMA_VERSION` moves from 12 to 13.

Every statement is `CREATE TABLE IF NOT EXISTS` or `CREATE INDEX IF NOT EXISTS`,
because `_ensure_schema` calls the migration against a brand new store that
already has the tables. The migration must never commit, roll back, or open a
transaction: it runs inside the caller's `BEGIN EXCLUSIVE`.

No backfill. There is no prior sentinel data anywhere, so the tables are created
empty and stay empty until the new methods write to them. State that in the
docstring the way `_migrate_11_to_12` states its own no-replay grounds.

### 2.1 `sentinel_knowledge`

Facts the agent verified and must not lose: requirements, constraints,
environment properties, file paths, tool-confirmed observations.

| Column | Type | Notes |
|---|---|---|
| id | TEXT PRIMARY KEY | uuid4 hex |
| project_id | TEXT NOT NULL | |
| session_id | TEXT | nullable; the session that recorded it |
| kind | TEXT NOT NULL | one of: requirement, constraint, environment, path, fact |
| content | TEXT NOT NULL | the fact, one sentence |
| source | TEXT NOT NULL | where it came from: a command, a file path, or "founder" |
| created_at | TEXT NOT NULL | ISO 8601 UTC, same helper style as elsewhere |
| last_surfaced_at | TEXT | NULL until first surfaced |
| surface_count | INTEGER NOT NULL DEFAULT 0 | |
| active | INTEGER NOT NULL DEFAULT 1 | 0 means retired |
| superseded_by | TEXT | id of the row that replaced it, else NULL |

Index on (project_id, active).

### 2.2 `sentinel_procedural`

What was tried and what happened. This is the table that stops the repeat-a-
failed-attempt failure.

| Column | Type | Notes |
|---|---|---|
| id | TEXT PRIMARY KEY | uuid4 hex |
| project_id | TEXT NOT NULL | |
| session_id | TEXT | |
| attempt | TEXT NOT NULL | what was tried, in the words that would be recognised again |
| outcome | TEXT NOT NULL | one of: failed, succeeded, ruled_out |
| diagnosis | TEXT | why, when known; nullable |
| created_at | TEXT NOT NULL | |
| last_surfaced_at | TEXT | |
| surface_count | INTEGER NOT NULL DEFAULT 0 | |
| active | INTEGER NOT NULL DEFAULT 1 | |

Index on (project_id, outcome, active).

### 2.3 `sentinel_status`

The watcher's private view of progress and open risks. Meta's status field is
never shown to the worker; ours is never injected either, and section 4 must not
select from this table. Append-only: a new row per update, latest read by
created_at then rowid.

| Column | Type | Notes |
|---|---|---|
| id | TEXT PRIMARY KEY | uuid4 hex |
| project_id | TEXT NOT NULL | |
| session_id | TEXT | |
| summary | TEXT NOT NULL | |
| open_risks | TEXT | nullable |
| created_at | TEXT NOT NULL | |

Index on (project_id, created_at).

### 2.4 `sentinel_interventions`

The calibration ledger. One row per decision, INCLUDING every silence.

| Column | Type | Notes |
|---|---|---|
| id | TEXT PRIMARY KEY | uuid4 hex |
| project_id | TEXT NOT NULL | |
| session_id | TEXT | |
| trigger | TEXT NOT NULL | one of: phase_boundary, pre_risky, post_failure, tool_interval, resume |
| decision | TEXT NOT NULL | inject or silent |
| memory_ids | TEXT | comma-separated ids injected; empty string when silent |
| reminder | TEXT | the exact text injected; NULL when silent |
| reason | TEXT NOT NULL | why this decision, including why silent |
| created_at | TEXT NOT NULL | |
| judged | TEXT NOT NULL DEFAULT 'unjudged' | unjudged, useful, or noise |
| judged_at | TEXT | |
| judged_by | TEXT | |

Index on (project_id, trigger), and on (project_id, judged).

## 3. Store methods

Add to the `Store` class, mirroring the style of `upsert_project`
(tools/bm_store.py:9908) for actor handling and transaction use. Every method
takes `actor` last where the neighbouring methods do.

```
add_knowledge(self, project_id, kind, content, source, session_id, actor) -> str (id)
add_procedural(self, project_id, attempt, outcome, diagnosis, session_id, actor) -> str
set_status(self, project_id, summary, open_risks, session_id, actor) -> str
latest_status(self, project_id) -> dict or None
active_knowledge(self, project_id, kinds=None) -> list of dict
active_procedural(self, project_id, outcomes=None) -> list of dict
retire_memory(self, table, memory_id, superseded_by, actor) -> bool
mark_surfaced(self, table, memory_ids) -> int (rows updated)
record_intervention(self, project_id, trigger, decision, memory_ids, reminder, reason, session_id, actor) -> str
judge_intervention(self, intervention_id, judged, judged_by) -> bool
intervention_stats(self, project_id) -> dict
recent_interventions(self, project_id, limit) -> list of dict
```

`table` in `retire_memory` and `mark_surfaced` accepts only the literal strings
`sentinel_knowledge` and `sentinel_procedural`; anything else raises, and the
table name is never interpolated from caller input into SQL without passing that
whitelist first.

AMENDMENT 1, 2026-08-02, raised by implementer STORE and ratified by the
orchestrator. As first written, this section gave `retire_memory` a
`superseded_by` argument for BOTH whitelisted tables, while section 2.2 gives
that column only to `sentinel_knowledge`. The spec contradicted itself, and the
implementer stopped and reported it instead of inventing a column or silently
dropping the value. Both of those would have been worse than the contradiction.
RESOLUTION: `superseded_by` is written only for `sentinel_knowledge`. A
`superseded_by` supplied for `sentinel_procedural` is REFUSED BY NAME, not
ignored, because a caller who passes it believes supersession is being recorded
and silence would let that belief stand. `sentinel_procedural` does not gain the
column: a procedural memory records what happened, and what happened is not
superseded by a later attempt, it is joined by one.

Validation is refusal, not coercion: an unknown `kind`, `outcome`, `trigger`,
`decision`, or `judged` value raises `ValueError` naming the field and the
allowed set. A value silently coerced is a value nobody can audit.

`intervention_stats` returns `{"total": int, "injected": int, "silent": int,
"useful": int, "noise": int, "unjudged": int, "useful_ratio": float or None}`.
`useful_ratio` is `None`, never `0.0`, when `useful + noise == 0`, and the
caller renders that as NO-DATA. A ratio computed over zero judgements is the
exact shape of number this project refuses to print.

## 4. The selection policy, deterministic and silence-biased

`select(trigger, context, knowledge, procedural, recent_interventions) -> (decision, memories, reason)`

A pure function. No I/O, no clock reads beyond what is passed in, no store
access. It is pure so the suite can drive every branch with plain data.

Order of evaluation, first match wins:

1. **Nothing to say.** Empty knowledge and empty procedural: `("silent", [], "no memories recorded")`.
2. **Cooldown.** Any memory injected in the last `COOLDOWN_N` interventions
   (default 5, module constant) is not eligible this round. If cooldown empties
   the candidate set: `("silent", [], "every candidate is in cooldown")`.
3. **post_failure.** Candidates are active procedural rows with outcome
   `failed` or `ruled_out` whose `attempt` shares at least `MIN_TOKEN_OVERLAP`
   (default 2) lowercase alphanumeric tokens of length >= 4 with `context`.
   Highest overlap wins; ties break by lower `surface_count`, then older
   `created_at`. No candidate: silent, reason `"no prior attempt matches this
   failure"`.
4. **pre_risky.** Same matching as post_failure against `context`, restricted to
   outcome `failed`. No candidate: silent, reason `"no prior failure matches
   this action"`.
5. **resume.** Candidates are active knowledge of kind `requirement` or
   `constraint`, ordered by `surface_count` ascending then `created_at`
   ascending. Resume is the one trigger allowed to surface a memory that has
   been surfaced before, because the ledger records resume as this project's
   worst decay moment. No candidate: silent, reason `"no requirements or
   constraints recorded"`.
6. **phase_boundary.** Same as resume but restricted to `surface_count == 0`.
   No candidate: silent, reason `"every requirement has already been
   surfaced"`.
7. **tool_interval.** Silent unless a `requirement` or `constraint` exists with
   `surface_count == 0`. Otherwise silent, reason `"nothing new since the last
   check"`.

AMENDMENT 3, 2026-08-02, from the adversarial review. Branch 2 as written
tests cooldown against the WHOLE memory pool, and every trigger branch then
narrows to its own kind. A round where the only trigger-relevant memory is in
cooldown, but some unrelated memory is not, therefore falls past branch 2 and
lands on a trigger branch that finds no candidate, which recorded a reason like
"no prior attempt matches this failure". That is false, and it is the reason
written into `sentinel_interventions`.

Why it is not cosmetic: that reason is the ONLY evidence Phase 4 has when it
decides whether the policy is too strict. A round suppressed by cooldown, filed
as "nothing matched", argues for loosening the matcher when the cooldown was
the cause, so the ledger would teach the opposite of the truth.

RESOLUTION: the decision is unchanged (still silent), and the branch order is
unchanged. Only the recorded reason changes. Every branch that finds no
candidate asks whether ITS OWN candidate set had members before cooldown
removed them. All suppressed gives "every candidate for this trigger is in
cooldown"; some suppressed appends the count to the branch's own reason; none
suppressed keeps the branch's reason as written. The suite must prove both
directions: that a cooldown-suppressed round is not filed as a no-match, and
that a genuine no-match is not blamed on cooldown.

Hard invariants the suite must prove, not assume:

- `select` NEVER returns more than one memory. One reminder, one moment.
- `select` NEVER returns a `sentinel_status` row. Status is private, always.
- Every `silent` return carries a non-empty reason.
- An unknown trigger raises `ValueError` naming the allowed set; it never falls
  through to silent, because a typo that reads as "the sentinel chose silence"
  is indistinguishable from working software.

Reminder rendering, when the decision is inject:

```
MEMORY: <content or attempt>
WHY NOW: <trigger-specific one-liner>
SOURCE: <source, or the diagnosis for a procedural memory>
```

Three lines, never more. Meta's own instruction to their memory agent is the
rule copied here: no strategic advice, no restating what is already visible, no
taking over planning.

AMENDMENT 2, 2026-08-02, found by the orchestrator's write-site review and
fixed in the same pass. "Three lines, never more" is a SECURITY property, not a
formatting preference, and the first implementation could not hold it. The
reminder is injected into a working agent's context by design, and the memories
it renders are written by agents that read web pages, files and command output.
A stored memory containing a newline could therefore forge extra MEMORY, WHY
NOW or SOURCE lines inside a block the reading agent has every reason to treat
as system authored. Every interpolated field passes through
`bm_learning.safe_display`, which strips control characters and caps length, the
same defence and the same reason as `bm_learn.py`. A failed load of that helper
REFUSES to render rather than falling back to raw text. The suite must prove
this with a memory carrying an embedded newline and a forged MEMORY line, and
assert the output is exactly three lines.

## 5. Command line: `tools/bm_sentinel.py`

Template to mirror for structure, exit codes and docstring register:
`tools/bm_ledger.py` (its module docstring states the laws it enforces, then
`EXIT_OK, EXIT_REFUSED, EXIT_USAGE = 0, 1, 2`).

Commands:

| Command | Does |
|---|---|
| `remember-knowledge --project ID --kind K --content C --source S [--session S]` | one row, prints the id |
| `remember-procedural --project ID --attempt A --outcome O [--diagnosis D] [--session S]` | one row, prints the id |
| `status-set --project ID --summary S [--risks R] [--session S]` | one row, prints the id |
| `check --project ID --trigger T [--context TEXT] [--session S]` | runs `select`, records the intervention either way, prints the reminder or `SILENT: <reason>` |
| `judge ID useful\|noise [--by WHO]` | grades one intervention |
| `list --project ID [--kind K] [--outcome O]` | the active memories |
| `stats --project ID` | the counts; `useful_ratio` prints `NO-DATA` when nothing is judged |
| `retire --project ID --id ID [--superseded-by ID]` | retires one memory |

`check` exits 0 whether it injected or stayed silent. Silence is a successful
outcome of the command, not a failure of it. Exit 1 is reserved for a refusal
(unknown project, invalid enum), exit 2 for usage.

Constraints inherited from this repository, all mechanical:

- Python 3.9, standard library only.
- NO `import subprocess` and no network in any shipping module under `tools/`;
  `tools/test_bm.py` enforces this and will fail the build. The test file may
  import subprocess (its `test_` prefix is the documented exemption).
- No em dashes and no en dashes anywhere: not in code, comments, docstrings,
  or printed output.
- Errors surface. No bare `except`, no `except: pass`, no discarded return
  value from a write.

## 6. The suite: `tools/test_bm_sentinel.py`

WRITTEN FROM THIS SPEC, NOT FROM THE IMPLEMENTATION. This project's failure
ledger records `tests-written-backwards-from-the-fix`: a test authored from the
code confirms the code's own assumptions and proves nothing. The test author
reads this file and the two template files named above, and does not read the
implementer's output before writing the assertions.

Required coverage, at minimum:

1. Migration: an old store at schema 12 opens, migrates to 13, and the four
   tables exist with the stated columns; a brand new store also has them; the
   migration is idempotent when run twice.
2. Every Store method: happy path, and the refusal path for each invalid enum
   value, asserting the error names the field and the allowed set.
3. `select`, every numbered branch in section 4, driven with plain data.
4. The four hard invariants in section 4, each as its own named test, including
   that an unknown trigger raises rather than returning silent.
5. `intervention_stats` returns `useful_ratio is None` with zero judgements, and
   the command line prints `NO-DATA` for it.
6. A silence is recorded as a row with a non-empty reason, proven by reading the
   row back after `check`.
7. `retire_memory` and `mark_surfaced` refuse a table name outside the
   whitelist.

Calibration requirement, non-negotiable: at least one test must be shown RED
before the implementation exists, by running the suite against the unmodified
tree and quoting the failure. A suite that has only ever been green proves
nothing about whether it can fail.

## 7. Done-checks, runnable, quoted in every close

```bash
cd ~/BrotherModeUp-worktrees/full-auto && python3 tools/test_bm_sentinel.py
```
```bash
cd ~/BrotherModeUp-worktrees/full-auto && python3 tools/test_bm_store.py
```
```bash
cd ~/BrotherModeUp-worktrees/full-auto && python3 tools/test_bm.py
```
```bash
cd ~/BrotherModeUp-worktrees/full-auto && python3 tools/test_all.py
```

`test_bm.py` is listed because it is the module-hygiene gate (no subprocess, no
network in shipping modules) and it is the one most likely to reject a
first draft. `test_all.py` additionally checks that every suite named in
`SUITES` is executed by a step in `.github/workflows/tests.yml`, so registering
the new suite in only one of those two places fails the gate.

## 8. File ownership for this phase

One writer per file, no exceptions:

| File | Owner |
|---|---|
| tools/bm_store.py | implementer STORE |
| tools/bm_sentinel.py | implementer SENTINEL |
| tools/test_bm_sentinel.py | implementer TESTS |
| tools/test_all.py | orchestrator only |
| .github/workflows/tests.yml | orchestrator only |
| this spec | orchestrator only |

An implementer that believes it needs a file it does not own stops and reports
that as a finding. It does not edit the file, and it does not work around the
constraint by putting the code somewhere it does own.
