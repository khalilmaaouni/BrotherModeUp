# Documentation engine, gate deep-dive packs, and the adoption book

Date: 2026-07-30
Branch: main (v2 retired; main is the only branch)
Baseline commit: 6cc94bc, tag v2.0.0-rc.4, gate "test_all: 911 tests across 7
suites, 1 skipped. ALL GREEN", clean-clone from the tag verified.
Status: CURRENT, founder-ratified 2026-07-30 through question windows. Every
decision in section 2 carries the founder's recorded answer.

This spec is the single source of truth for the three builds. Implementers point
at it by path and line range; they never restate it.

---

## 1. Why this exists

BrotherMode records more about a project than any document it produces: work
records, decisions, transitions, rule applications, gate outcomes, failures.
Today a human arriving cold cannot see any of it without reading a transcript,
and an engineer asked to approve an AI decision cannot see the code that
decision would change.

Two features close that gap, and one book teaches it:

1. A per-project `Documentation/` folder, generated mostly from recorded facts.
2. A per-gate deep-dive pack an engineer can review before deciding.
3. An illustrated book, because a team that does not understand loops will not
   use them.

---

## 2. Founder decisions, ratified 2026-07-30

| # | Decision | Chosen |
|---|---|---|
| 1 | Build order | Gate packs, then documentation engine, then book |
| 2 | Right-sizing | Auto-tier from measured signals, reason printed, flag overrides |
| 3 | Heavy formats | Markdown plus mermaid always (stdlib); PDF, Word, Excel via an OPTIONAL exporter that reports honestly when tooling is absent |
| 4 | Gate pack trigger | On demand at the gate, link in the question window |
| 5 | Collaboration layer | Store-backed rows rendered into docs, authored and anchored |
| 6 | Book form | Self-contained illustrated HTML plus PDF export |
| 7 | Critical alerts | BLOCK a gate close, with a recorded founder override |
| 8 | P14 audit | Internal audit labelled same-family; outside review stays open |

Out of scope, named so it is never mistaken for covered: P13 dogfood window,
P14 outside-family audit, P19 external beta runs.

---

## 3. Invariants this work may not break

Inherited, and each already enforced by a test:

- **I1.** Python 3.9 floor. No unions with the pipe operator, no match, no
  builtin generics evaluated at runtime.
- **I2.** Standard library only for anything mandatory. No dependency may become
  required. The optional exporter must degrade to a plain statement of what it
  could not produce.
- **I3.** No network and no subprocess in shipping `tools/*.py`, with the single
  documented exemption already recorded for `bm_autosave.py`.
- **I4.** `tools/bm_store.py` is the only writer of the store. Pure helpers live
  in `bm_learning.py`. CLIs hold no semantics.
- **I5.** Every write site is inventoried in `tools/write_sites.json`.
- **I6.** Every `conn.execute` routes through `_exec` or is exempt-listed with a
  stated reason.
- **I7.** No em dashes and no en dashes anywhere, including generated output.
- **I8.** Schema changes are additive and atomic, version bump written last in
  the same exclusive transaction, fixtures built from a real store, and a known
  older version migrates rather than quarantines.
- **I9.** Founder text is withheld by default in every export.

New, introduced by this spec:

- **I10. Generated output never destroys human text.** Any generator writing a
  file that may contain human content must preserve every HUMAN block verbatim.
  Calibration is mandatory: reinject a destructive generator, prove the test
  fails, restore, prove it passes.
- **I11. A rendered code excerpt must resolve.** Any pack citing file and line
  re-reads the file at generation time. A citation that no longer resolves is a
  build failure, never a silently stale quote.
- **I12. Prose is cached against facts.** Every generated prose block records the
  hash of the facts it describes. Unchanged facts must not trigger regeneration.
- **I13. Tiers auto-raise only.** An automatic tier decision may increase
  documentation depth, never decrease it. Lowering is an explicit founder flag.

---

## 4. Phase A: gate deep-dive packs

### A.1 What a pack is

A markdown file under `Documentation/30-decisions/D-<n>-<slug>.md`, generated on
demand for one gate or decision, complete enough that a backend, frontend or data
engineer can review the choice without reading a transcript.

Required sections, in this order:

1. **The decision, in one paragraph of plain language**, and what happens if it
   is wrong.
2. **Options**, each with trade-offs, plus the recommendation and its reason.
3. **The code**, as live excerpts with path and line range, showing exactly what
   would change. Re-read at generation time per I11.
4. **Dependency map**: every caller, test and document that touches those lines,
   discovered by search, not asserted.
5. **Risks**: what breaks, blast radius, and the rollback command.
6. **What the store already knows**: related approved rules, prior decisions in
   this area, prior recorded failures.
7. **A diagram**: mermaid flowchart of the affected path.
8. **Review**: slots where a named engineer records verdict, notes and residual
   concerns; those writes land in the store, not only in the file.

### A.2 Trigger and cost

Nothing is generated until asked. The gate's question window carries a one-line
statement of stakes plus the path the pack would occupy. Generation is a single
command; the pack is written to disk and its existence recorded.

### A.3 Alerts with teeth

Note kind `alert` carries a severity. An unresolved `alert` at severity
`critical`, anchored to the gate or to any file the gate would change, REFUSES
the gate close. The refusal names the alert, its author and its anchor. The
founder may override; the override records the founder's reason and the alert
stays visible as overridden, never deleted.

### A.4 Acceptance

- A pack generated for a real gate in this repository contains all eight
  sections, and every code citation resolves to the line it quotes.
- Mutating a cited file so a line moves makes generation fail loudly.
- An unresolved critical alert refuses a gate close; the override path records a
  reason; a resolved alert does not refuse.
- Every new guard calibrated by reinjection.
- `python3 tools/test_all.py` green after the last edit, quoted.

---

## 5. Phase B: the documentation engine

### B.1 Layout

```
Documentation/
  00-START-HERE.md
  10-business/     BA-SUMMARY.md REQUIREMENTS.md WBS.md SCHEDULE.md
  20-technical/    ARCHITECTURE.md DATA-MODEL.md PROCESS-DIAGRAMS.md
                   DEPENDENCIES.md CODE-MAP.md
  30-decisions/    INDEX.md D-<n>-<slug>.md
  40-handover/     HANDOVER.md RUNBOOK.md
  90-generated/    facts.json
```

Numbered directories so a stranger's reading order is unambiguous.

### B.2 Three generation sources, in cost order

- **Projection, free.** Store rows render directly: WBS from work records,
  SCHEDULE from records plus dependencies (mermaid gantt plus a critical path
  computed by longest-path over the dependency graph), decision INDEX from gates
  and decisions, notes and lineage inline, applications and outcomes.
- **Introspection, free.** Repository scans: data model as a mermaid entity
  diagram from schema introspection, dependency graph from imports, module
  inventory, test inventory.
- **Prose, paid and minimal.** Only BA summary narrative, decision rationale,
  code explanation at tier depth, handover narrative and whitepaper. Each block
  stores a fact hash per I12.

### B.3 Tiers

| Tier | Fits | Emits |
|---|---|---|
| 1 lean | a script, a single-file fix, a spike | START-HERE, decision INDEX, HANDOVER |
| 2 standard | most projects | tier 1 plus REQUIREMENTS, WBS, SCHEDULE, ARCHITECTURE, DATA-MODEL, DEPENDENCIES, RUNBOOK |
| 3 full | multi-contributor, long-lived, regulated | tier 2 plus PROCESS-DIAGRAMS, CODE-MAP, whitepaper, optional exports |

Signals: tracked file count, distinct contributors, recorded gate count, risk
flags in the store, project age. The chosen tier and the signals that chose it
are printed and written into START-HERE. `--tier N` overrides. Per I13 automatic
movement raises only.

### B.4 Human blocks

Generated files carry the existing generated-file header. Human text lives
between explicit begin and end markers, preserved verbatim across regeneration
per I10.

### B.5 The handover document

`40-handover/HANDOVER.md` is written for a human with no AI: what the project
is, current state with the command that proves it, what is done, in flight, and
not started, where the code lives module by module, how to run and test it, the
known traps, the open decisions with their packs, and who to ask. It must be
usable by someone who has never spoken to me.

### B.6 Optional exporter

A separate module, never imported by the engine's mandatory path. It attempts
PDF, Word and Excel using tooling already on the machine, and when tooling is
missing it says exactly which format could not be produced and why. It never
raises into the generator, and it never becomes a dependency.

### B.7 Acceptance

- Running the engine on this repository produces the tier it announces, with the
  reason.
- Regeneration twice in a row is byte-identical (no churn) and preserves a
  planted HUMAN block; the calibrated destructive variant fails the test.
- The critical path in SCHEDULE matches a hand-computed path on a fixture.
- Unchanged facts skip prose regeneration, proven by a hash comparison.
- Exporter absence degrades to a stated limitation, not a crash.
- `python3 tools/test_all.py` green after the last edit, quoted.

---

## 6. Phase C: the collaboration layer

Note kinds: `insight`, `alert`, `question`, `review`, `todo`, `risk`. Each row
carries author identity (founder, assistant, or a named human), anchor (file and
line, decision, gate, or work record), body, severity where applicable, created
and resolved timestamps, and the session that wrote it.

Rendering: docs and packs show notes at their anchors. Lineage is a query:
everything that touched a decision, in order, with authors.

Retention: resolved notes stay, marked resolved. Nothing is deleted by a
generator.

Acceptance: an anchored note appears in the rendered doc at its anchor; lineage
returns the full chain for a decision; a note anchored to a moved line is
reported rather than silently dropped.

---

## 7. Phase D: the book

One self-contained HTML file (inline CSS, mermaid rendered inline, no external
requests) plus a PDF export. Twelve chapters:

1. The problem, told as a working day, no jargon.
2. Install in ten minutes: individual and team.
3. Your first loop, with a real transcript.
4. The five questions kept apart: capture, interpretation, approval,
   application, outcome.
5. How to correct it, and what happens to a correction.
6. Gates and deep dives: how an engineer reviews an AI decision.
7. The Documentation folder, toured.
8. Working with a team: parallel work, fences, handovers, other teams' repos.
9. Task types: what to hand over, what to keep.
10. Other runtimes: what works, what is unverified, and why that distinction
    matters.
11. When it goes wrong: troubleshooting, recovery, honest limits.
12. Glossary.

Every claim in the book must be true of the shipped code at the tag it
documents, and any figure must come from a command the author ran.

Acceptance: the HTML opens offline with diagrams rendered; no external network
reference; every command shown was executed; PDF produced or its absence stated.

---

## 8. Testing strategy

- Projection tests: fixture rows produce expected rendered content.
- Calibrated I10 test: destructive generator variant must fail.
- Calibrated I11 test: moved line must fail generation.
- I12 test: unchanged facts skip regeneration.
- Tier selection tests across the three tiers plus the override.
- Critical path correctness on a known graph.
- Alert-blocks-gate, override-records-reason, resolved-does-not-block.
- Doc consistency: extend `tools/test_bm_docs.py` rather than adding a suite,
  unless a new suite is registered in `test_all.py`, which refuses unlisted
  suites.

---

## 9. Rollback

Each phase is one or more commits on `main`. Every generated artifact lives under
`Documentation/` or `docs/`, so reverting a phase removes generated output
without touching the engine's data. No schema change in this spec is destructive;
each is additive with its own migration test.

---

## 10. What this spec deliberately does not do

- No new mandatory dependency, no service, no network call.
- No project management tool integration.
- No claim that documentation replaces the dogfood window or the outside audit.
- No automatic tier reduction.
- No deletion of any human-authored text, ever.
