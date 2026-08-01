# The release-closure program, Fable-reviewed and amended

Status: CURRENT. Written 2026-08-01. Source: the founder-supplied external
review "BrotherME Final Release Closure Plan" (GPT SOL, 2,631 lines, in
Downloads; copy it into docs/evidence/ at Loop 0 so the program's source
survives). That document demanded Fable review before any implementation;
this file IS that review. Founder approval gate: EXECUTION HAS NOT STARTED
and does not start until the founder approves this plan.

## 1. Verdict on the external review

ACCURATE. All ten release blockers it names were checked against the tree
and hold: the rc.11 tag was never cut and three commits have since landed
on a tree still calling itself rc.11; the SQLite store, the canonical
schema in brotherme/core/schema.py, JSONL events, and markdown files are
overlapping state systems; the beginner commands are prompts, not
mechanical operations; one local plugin install, no external; consent flow
incomplete; the fence does not gate Bash and fails open; runtimes are
documented beyond proof; forecasts and attribution are not derived from
one source; no real project has run the full lifecycle. Its fifteen
non-negotiable rules are compatible with this project's constitution and
its separation-of-duties table matches the guided loop law already in
references/delegation.md.

## 2. What Fable ACCEPTS unchanged

- The executive decision: do NOT release from rc.11; run a release-closure
  program, not a feature wave. Feature freeze: nothing new unless it
  closes a blocker named in the source document.
- The priority order 1 through 9 (release identity, single source of
  truth, executable beginner commands, consent-first install, task and
  evidence lifecycle, security closure, runtime adapters, real usage,
  final release). The dependency logic is sound.
- ADR-1 through ADR-8, especially: SQLite the sole durable authority;
  markdown, HTML, dashboards and packets become generated views; every
  mutation through one service layer with state change and attribution in
  one transaction; evidence precedes advancement.
- The four-level runtime truth ladder (core compatible, guidance
  integrated, hooks integrated, fully verified) and the narrow-release
  rule: fully verify Claude Code, verify at most two more runtimes,
  label the rest honestly, expand after evidence.
- The separation of duties: Fable plans, briefs, and adversarially
  reviews; a Builder-profile model implements; a Fast-Worker profile does
  mechanical work; the founder alone releases. The writer and the final
  reviewer are never the same execution context.
- The 9/10 definition and the honest ceiling: external validation cannot
  exceed roughly 8.5 before real usage; no score inflation.

## 3. Fable's AMENDMENTS, each with its dependency argument

A1. RELEASE IDENTITY, resolved harder than the source asks: rc.11 joins
rc.10 as SUPERSEDED WITHOUT EVER BEING TAGGED (same recorded reasoning:
a late tag would recreate the rc.8 two-trees ambiguity). Loop 0 cuts a
release branch and freezes; the next version name appears exactly once,
on the release branch, on the release commit. docs/RELEASE.md gains the
program's version law.

A2. DOGFOOD MOVES EARLY. The source schedules real validation as Loop 8,
after runtime adapters. But its own gate demands seven CALENDAR days of
real founder work, which no engineering can compress. Dependency: dogfood
needs executable beginner commands over unified state (Loops 1 and 2),
not runtime adapters (Loop 7). Therefore the founder's real project
STARTS the day Loop 2 closes and runs in parallel with Loops 3 through 7.
This cuts two to five calendar days from the critical path and surfaces
lifecycle defects while builders are still warm.

A3. INTEGRATION, NOT REINVENTION, of the schema. The source's section 8
tables (projects, forecasts, tasks, dependencies, attribution, alerts,
evidence, runtime runs) overlap the canonical schema already landed in
brotherme/core/schema.py (five objects, ten states, one event stream)
and the store's existing tables. Loop 1's first brief is a mapping
document: existing table or object, target table, migration or rename,
delete-list for the parallel bookkeeping. No table is created twice.

A4. EXISTING MACHINERY IS LOAD-BEARING. The learned-rules store
(bm_learn), telemetry hooks, fence hook, autosave, and the docs engine
survive as-is unless a blocker names them. The loops extend the store
they already use; any brief that would fork them is refused.

A5. THE USEFULNESS GATE JOINS THE PROGRAM. Every founder-facing surface a
loop touches (status view, dashboard, delivery packet, onboarding flow)
passes the red-reader gate (hostile user, 3 of 5 minimum) before the
founder sees it. This is the 2026-08-01 lesson; the source document
predates it.

A6. SBE DESIGN LAW, mapped not duplicated. The founder invoked the SBE
design discipline. This program is tier T3 by SBE intake (sensitive, not
reversible in an hour). The source document plus this file constitute the
design dossier (purpose, process, architecture with ADRs, data model,
expression, verification, in that order). Loop 0 runs the mechanical SBE
design checks against this dossier where the tooling applies. Disclosed
plainly: those checks have not run yet.

A7. BUDGETS BECOME MEASURED. The source's envelopes (1.2M to 2.8M tokens
whole-program) are accepted as planning ranges; this machine's telemetry
(11.7M tokens across 16 sessions in the last day exists as proof of
capacity) reforecasts them after Loops 1 and 2, as the source itself
requires.

## 4. The program map (amended order)

Loop 0: Release truth and freeze. Branch, version law, source document
archived into evidence, SBE design checks run. GATE: one tree, one name,
CI green on it. FOUNDER REPORT 1.
Loop 1: State unification. The mapping document, then migrations; every
mutation through the service layer, one transaction with attribution.
GATE: crash tests recover; no second source of truth remains. FOUNDER
REPORT 2.
Loop 2: Beginner commands become mechanical operations over the store
(start, status, next, review, deliver, update, help reading real state).
GATE: a scripted first project runs end to end through the seven
commands. FOUNDER REPORT 3, and DOGFOOD STARTS HERE (A2).
Loop 3: First-run consent, install, update, doctor, uninstall on clean
machines. GATE: fresh-machine install without developer help.
Loop 4: Task and delivery spine (the source's atomic operations). GATE:
lifecycle states travel only through the service layer.
Loop 5: Forecasting, attribution, alerts, status from stored records
only. GATE: every displayed number traces to a row and its evidence.
FOUNDER REPORT 4 (loops 3 to 5 land together as the mid-program report).
Loop 6: Security and privacy closure: Bash-write detection, optional
fail-closed mode, consent-first disclosure, export and deletion. GATE:
threat model explicit; detection demonstrated.
Loop 7: Runtime adapters: one core, conformance suite, Claude fully
verified plus at most two runtimes; the rest labeled. GATE: conformance
passes on real runtimes only. FOUNDER REPORT 5.
Loop 8: Validation evidence assembled: the dogfood record (running since
Loop 2), three fresh-machine outside installs, one non-technical user,
one recovered interruption, one failed review causing rework, one
reforecast, one delivery. GATE: the source's minimum external-validation
list, every item with evidence.
Loop 9: Fable adversarial release review: attempt to disqualify. Any
Critical refuses the release. Then the founder alone tags and publishes.
FINAL FOUNDER REPORT with the go/no-go matrix and scorecard.

## 5. Reporting contract (the founder asked for this explicitly)

At each FOUNDER REPORT: outcome first, the gate evidence quoted, spend
against envelope, forecast update with confidence and the moving
assumption, decisions needed as question windows, bad news first. No
report, no next loop.

## 6. Execution note

This plan was produced at the end of a very long session. Execution
starts in a FRESH session that reads: this file, the source document, the
STATE.md digest, and the vault. That is the recommended path; the plan
file is the baton and nothing here depends on this conversation's memory.
