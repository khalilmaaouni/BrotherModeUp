# Correction learning: the execution program, corrected against the repository

Date: 2026-07-28
Branch: v2
Baseline commit: a379877
Source plan: docs/superpowers/plans/2026-07-28-correction-learning-source-plan.md
Status: ratified by the founder 2026-07-28. All four decisions in section 3 are
answered; see section 3.1 for what was chosen.

This file is the plan we execute. The source plan is the input, kept verbatim in
the repository so nobody has to trust a summary of it. Where this file and the
source plan disagree, this file wins, and every disagreement below states the
evidence that caused it.

---

## 1. Verified baseline, 2026-07-28

Every number here came from a command run today, on this machine, at commit
a379877 with a clean working tree.

```
python3 tools/test_bm.py            -> Ran 92 tests, OK (skipped=2), 20.7s
python3 tools/test_bm_store.py      -> Ran 244 tests, OK, 7.5s
python3 tools/test_bm_autosave.py   -> Ran 34 tests, OK, 16.4s
python3 tools/test_bm_fence_hook.py -> Ran 49 tests, OK, 1.0s
```

Total 419 tests, 2 skipped, zero failures.

Environment facts that constrain the work:

- `SCHEMA_VERSION = 1` (tools/bm_store.py:73). No migration machinery exists.
- FTS5 IS available locally: sqlite 3.51.0 under Python 3.9.6.
- CI matrix: the store suite runs on ubuntu, macos AND windows, across Python
  `3.9` and `3.x`. **Python 3.9 is the floor.** No `X | Y` unions, no `match`,
  no builtin-generic annotations evaluated at runtime.
- Exactly one live store exists on this machine:
  `/Users/khalil.maaouni/Documents/BrotherModeUp/.brothermode/store.sqlite3`.
  Migration blast radius is one file, and it is the founder's own.

---

## 2. Where the source plan is wrong, and what changes

Six findings. Five are corrections of fact. The sixth is an argument.

### 2.1 The file inventory is stale (section 0.3)

The plan names two test suites and six production files. The repository has FOUR
suites and eight production modules. Missing from the plan entirely:

- `tools/bm_autosave.py` (1,671 lines) and `tools/test_bm_autosave.py` (34 tests)
- `tools/bm_fence_hook.py` (670 lines) and `tools/test_bm_fence_hook.py` (49 tests)

Consequence: every loop-close instruction that says "run the full regression
suites" means FOUR commands, not two. Any loop that touches the fence hook or
autosave has coverage the plan does not know about.

### 2.2 Bumping SCHEMA_VERSION without a migration branch QUARANTINES live stores

This is the highest-risk correction in this document.

The plan (Loop 1, 4.1) says "refuse to open a store whose schema is newer than the
binary." The actual behaviour is stronger and cuts the other way. In
`_verify_schema_or_raise` (tools/bm_store.py:1983):

```python
if found_version != str(SCHEMA_VERSION):
    self._quarantine_and_raise(...)
```

Any mismatch in EITHER direction quarantines: the store file and its WAL sidecars
are moved into a per-incident quarantine directory. So the instant
`SCHEMA_VERSION` becomes `2`, every existing schema-1 store is quarantined on next
open, including the founder's own live store in this repository.

Mandatory order of operations for Loop 1, which the source plan does not state:

1. Add the migration dispatch INSIDE `_verify_schema_or_raise`, so an older
   known version routes to migration instead of to quarantine.
2. Build a real schema-1 fixture and prove it migrates.
3. Prove an unknown NEWER version still quarantines.
4. Only then change the constant to 2.
5. Back up `.brothermode/store.sqlite3` before the first real run on this machine.

A second detail the plan misses: `_verify_schema_or_raise` only checks that the
tables in `_TABLES` are PRESENT, never that no others exist (comment at
tools/bm_store.py:781). That is deliberate and it is what makes an interrupted
migration survivable, but it also means a HALF-created learning table set passes
the presence check. The plan's requirement "a partially created learning table set
is refused as corrupt" therefore needs a new mechanism, not a reuse of the
existing one. Simplest honest mechanism: write the schema_version bump LAST inside
the same exclusive transaction as the table creation, so a half migration leaves
version 1 and re-runs cleanly.

### 2.3 Corrections are captured in the VAULT, not in SQLite

The plan's data flow assumes candidates land in `.brothermode/store.sqlite3`.
They do not. Today (tools/bm_telemetry.py:91):

```python
CORRECTIONS = os.path.join(VAULT, "99-System", "telemetry", "corrections.jsonl")
```

That file is GLOBAL across every project on the machine, owner-only (0600),
appended at SessionEnd by a single English regex (bm_telemetry.py:110).

This is a genuine architectural fork, not a detail, because the plan's invariant
L5 (scope isolation: a project rule is never retrieved in another project) is in
direct tension with a global capture file. Loop 4 cannot be written until this is
decided. The fork is question 3 in section 3 below.

Whatever is chosen, Loop 4 additionally owes a BACKFILL: existing
corrections.jsonl rows are real founder evidence and must become
`detected_correction` candidates rather than being orphaned.

### 2.4 LESSONS.md and TOOLBOX.md already exist, hand written, referenced by no code

The plan's Loop 10 says to create `docs/knowledge/LESSONS.md` and
`docs/knowledge/TOOLBOX.md` as generated views. Both files already exist with
substantial hand-authored content (defect classes with calibrated mechanical
stops, verified tool recipes with dates). A grep of `tools/*.py`, `SKILL.md` and
`references/*.md` finds no code that reads or writes either file.

So Loop 10 as written would OVERWRITE hand-written knowledge with generated
output. It must become a migration loop: import the existing content into the
store as seed rows, then generate, with a test that proves no existing class or
recipe was lost. This is exactly the failure class already recorded in the
repository's own LESSONS.md.

### 2.5 The plan ignores fourteen open items that already exist

`docs/NOT-FINALIZED.md` lists fourteen OPEN, PARTIAL or UNPROVEN items. Two of
them will actively corrupt this program's evidence if left alone:

- **Item 5, the adopt defect (OPEN, survived two audits).** A REFUSED adoption
  still writes a permanent "Adopted from dead/stalled thread" handover block into
  STATE.md. A learning system whose whole claim is "we record what actually
  happened" cannot be built on top of a component that writes a known lie to disk.
- **Item 10, the suites cannot run concurrently.** They rename a module aside
  mid-run. This program adds a FIFTH suite and ends every one of fifteen loops
  with "run the full regressions." Serial-only test runs with no enforced serial
  runner means flakes get blamed on the new code.

Recommendation: a new **Loop 0.5** closes both before schema work starts. Both are
small. Everything else in NOT-FINALIZED.md stays open and stays documented.

### 2.6 The argument: Loop 9 and Loop 10 contradict the plan's own principle

The plan's section 13 says, correctly:

> Delete or relabel any metric that cannot move mechanically or cannot support a
> decision at current volume.

Loop 9 then specifies permanent train/validation/test partitions, content-hash
mutation detection, a rejection buffer, baseline-versus-candidate scoring with a
strictly-positive acceptance threshold, and a release-only test partition. That is
machine-learning evaluation infrastructure. It will be measuring a corpus of
perhaps twenty to forty rules belonging to one person.

At that volume a validation partition holds maybe eight cases. A "statistically
significant improvement" over eight cases does not exist. Building the partition
machinery does not make the measurement honest, it makes an unsupportable number
look rigorous, which is the precise failure the plan names as memory theatre.

Loop 10 has a milder version of the same problem: generated knowledge views are
worth building when the source data is too large to curate by hand. Two
hand-written files that are currently good is not that situation yet.

My recommendation is to DEFER Loop 9 and Loop 10 until real usage produces
retrieval misses that matter, and to say so in the release notes rather than
shipping the machinery and calling it measured. This is question 2 in section 3.

I will build both exactly as specified if the founder disagrees. The argument is
recorded so the decision is his and not mine by default.

---

## 3. Four decisions I need from the founder

These change what gets built, so they come before Loop 0 closes, not after.

1. **Sequencing.** Fifteen loops in the source order, value arriving at the end?
   Or the MVP slice in section 4 (value arriving at loop 7 of 17), dogfood, then
   the rest? I recommend MVP-first.
2. **Loop 9 (evaluation partitions) and Loop 10 (generated knowledge views).**
   Build now, or defer until there is data volume to justify them? I recommend
   defer, per 2.6.
3. **Where candidates live.** Per-project SQLite only (clean scope isolation, but
   corrections captured while working in project A about a GLOBAL preference need
   an explicit promotion step)? Or keep the vault's global corrections.jsonl as
   the capture channel and treat the per-project store as the system of record for
   approved rules? I lean per-project store as system of record, vault file kept
   as an inbox, because it preserves both properties.
4. **Execution mode and gates.** Do I run the loops inline in this session, one
   commit per loop, reporting each loop close and continuing without asking? Or
   does each loop close wait for founder sign-off? And are commits to branch `v2`
   pre-authorised, with the push held for GitHub Desktop at the end as the repo's
   own never-forget line requires?

### 3.1 Founder decisions, 2026-07-28

1. **Sequencing: MVP first, then dogfood.** Loops 0, 0.5, 1, 2, 3, 5, 11A, then a
   real dogfood window, then the rest.
2. **Loops 9 and 10: DEFERRED**, with the reason published in the release notes.
   Loop 9 reopens when the rule corpus is large enough for a partition to decide
   anything. Loop 10 reopens when hand-curating LESSONS and TOOLBOX actually
   becomes the bottleneck. Neither is abandoned; both are unbuilt on purpose.
3. **Candidate storage: per-project store is the system of record, the vault's
   corrections.jsonl remains a global capture inbox.** Approved rules live in each
   project's `.brothermode/store.sqlite3`. Triage promotes an inbox row into the
   right project, with global scope available as an explicit choice at approval.
4. **Execution: run and commit each loop, report, continue.** One commit per loop
   on branch `v2`. I stop on a failed gate or a decision that is genuinely the
   founder's. The push to GitHub is held for GitHub Desktop at the end, per the
   repository's own never-forget line.

---

## 4. The corrected loop program

Seventeen loops. Two are new (0.5 and 11A split out), two are deferred pending
question 2, and every source loop keeps its number so the two documents stay
cross-referenceable.

Each loop closes with the report contract in the source plan section 0.4, and
each loop's regression gate is now all FOUR suites:

```bash
python3 tools/test_bm.py
python3 tools/test_bm_store.py
python3 tools/test_bm_autosave.py
python3 tools/test_bm_fence_hook.py
```

### Phase A: foundation (no user-visible change)

| Loop | Name | Adds | Risk |
|---|---|---|---|
| 0 | Baseline freeze | a baseline spec with today's command output | none |
| 0.5 | **NEW** Close the two evidence-corrupting open items | adopt-defect fix, serial test runner | low |
| 1 | Schema v2 and migration safety | 7 tables, migration dispatch, redaction proof | **HIGH, see 2.2** |
| 2 | Learning store API | transactional lifecycle methods, pure helpers | medium |

Loop 0.5 detail. Two independent fixes, one commit each:
- Move the handover write in the adopt path so a REFUSED adoption writes nothing.
  Calibration: reinject the old order, prove the new test fails.
- Add `tools/run_all_tests.py` that runs the four suites SERIALLY with a single
  exit code, and make it the documented loop-close gate. This does not fix the
  underlying module-rename design, and the known limit stays open and stated.

### Phase B: the founder can actually use it

| Loop | Name | Value delivered |
|---|---|---|
| 3 | Explicit capture and review CLI | founder can capture, approve, edit, reject, forget a rule |
| 5 | Scoped explainable retrieval | founder can ask "what rules apply here" and see why |
| 11A | Skill-driven retrieval (stage A only) | BrotherMode itself pulls rules on substantial tasks |

**This is the MVP.** After Loop 11A the product claim "remembers corrections and
retrieves the right rule at the right time" is true and demonstrable. Loop 4
(automatic capture) is deliberately AFTER this, because a review queue with
nothing to review it against is just noise.

### Phase C: dogfood gate

| Loop | Name |
|---|---|
| 14a | **First dogfood window.** Real founder work only. No new features. |

Minimum before Phase D starts: several genuine corrections captured, at least one
approved rule retrieved at the right moment, at least one rejection, and an honest
answer to "did this create more ceremony than value." Manufacturing events to fill
the checklist is forbidden and would poison every later measurement.

### Phase D: close the loop

| Loop | Name | Depends on |
|---|---|---|
| 4 | Automatic candidate capture (+ corrections.jsonl backfill) | question 3 |
| 6 | Duplicates, contradictions, supersession, `learning-verify` | Loop 2 |
| 7 | Retrieval and application lifecycle | Loop 5 |
| 8 | Rework, escaped defects, repeated corrections | Loop 7 |
| 11B | Optional UserPromptSubmit hook | Loop 11A proved useful |

### Phase E: harden and tell the truth

| Loop | Name |
|---|---|
| 12 | Security, privacy, adversarial review |
| 13 | Documentation, scorecard replacement, honest metrics |
| 14b | Release decision with published Remaining and Unverified lists |

### Deferred pending question 2

| Loop | Name | Reopen when |
|---|---|---|
| 9 | Evaluation partitions and replay | there are enough rules for a partition to decide anything |
| 10 | Generated LESSONS and TOOLBOX views | hand curation actually becomes the bottleneck |

---

## 5. Invariants added to the source plan's L1 to L15

- **L16. Migration never quarantines a known older store.** A schema-1 store
  opened by a schema-2 binary migrates. Only an UNKNOWN or NEWER version
  quarantines. Calibration: remove the migration branch, prove the fixture
  quarantines, restore, prove it migrates.
- **L17. Generated views never destroy hand-authored content.** Any generation
  step over a file that already had content must prove, by test, that every
  pre-existing class or recipe survives.
- **L18. The loop-close gate is all four suites, serially, one exit code.**
- **L19. Python 3.9 is the floor.** CI proves it; local development must not
  drift ahead of it.

---

## 6. Honest sizing

The source plan asks for roughly seven tables, three new production modules,
three new documentation files, and by its own required-test lists somewhere
between 150 and 250 new tests, each load-bearing guard calibrated by reinjecting
its defect.

This is a T3 program measured in days of working sessions, not one session. Loop
14a is calendar time and cannot be compressed by effort. Anyone who tells you the
whole thing lands tonight is describing a smaller thing than what is written here.

The MVP slice (loops 0, 0.5, 1, 2, 3, 5, 11A) is the part with a real completion
date, and it is the part that makes the product claim true.

---

## 7. What is NOT covered

Stated here so it is never mistaken for covered:

- NOT-FINALIZED items 1, 2, 3, 4, 6, 7, 8, 9, 11, 12, 13, 14 stay open. Only 5
  and 10 are addressed, by Loop 0.5, and only because they corrupt this program's
  own evidence.
- No independent second-model adversarial re-audit is scheduled here. NOT-FINALIZED
  item 12 remains deferred.
- Bash writes remain outside the fence hook. A learning CLI invoked through Bash
  is therefore NOT fence-gated, which matters for Loop 3 and is a known limit to
  restate rather than to quietly inherit.
- No Windows machine is available on this desk. Windows behaviour is asserted by
  CI only, never observed.
