# The graph engineering roadmap, ratified 2026-08-11 midday

Status: CURRENT. EXTENDS docs/plan/PROGRAM-PLAN-2026-08-11-RATIFIED.md and
folds the founder's graph engineering spec into it; decisions in
docs/decisions/RATIFIED-2026-08-11-graph-engineering.md (all forty).
The north star is UNCHANGED: from intent to a verified, review-ready
deliverable with bounded autonomy, independent proof and recoverable
state. Graph engineering is the methodology for that path, not a new
star. No em or en dashes.

## The one-paragraph thesis

BrotherMode already executes a model-authored work graph safely (store,
controller, fences, checks, recovery). What it does not yet do: VERIFY the
graph before running it, make PROOF navigable from claim to receipt, or
REMEMBER success. This roadmap adds exactly those three, folded into the
loops that already own the seams, under four new laws: minimum sufficient
graph, every edge carries a reason, proof must reach the claim,
parallelism requires proven independence.

## Wave 1 (open now, unchanged)

Lane A: SD2 sentinel, then CC board generator. Lane B: CX Codex phases 0
to 2. SL-quick CLOSED today (all four rule fixes landed, gate receipt live
at 943c59a). Plus GE0: the truth map, read-only, EXISTS or PARTIAL or
ABSENT or DUPLICATE-RISK for every spec proposal, filed before Wave 2
prices itself.

## Wave 2: the verified graph (each fold inside its ratified host loop)

| Host loop | Delivers as ratified | The graph fold | Done-check |
|---|---|---|---|
| G1 governor | Admission decision, ten adversaries stopped | Static checks as admission's front half: write overlap, gate ordering, evidence gap, cycles and retry bounds; advisory two weeks then refusing; COMPLEX plans only | Each seeded bad graph refused by the smallest rule, a valid graph passes, bad news first |
| GE2 slim (inside G1) | none of its own | Node type and typed edge labels on the EXISTING tasks and dependencies tables; eight node types, six edge types | A current controller plan round-trips without loss |
| V1 verifier | Frozen criteria, cross-model verification | Criterion records with stable IDs; criterion to verifier to receipt links; computed evidence freshness | A seeded missing-proof criterion blocks delivery naming the absent evidence |
| D1 delivery | State machine to DELIVERED | Delivery computes coverage: every claim reachable from evidence newer than the last relevant edit; gap blocks, founder override recorded per item | H7 benchmark passes repeatedly |
| C1 convergence | Findings become bounded tasks | Findings name their violated criterion; fix nodes carry lineage edges; rounds ceilinged | Seeded three-gap project converges without re-prompting |

Telemetry starts here: every real and benchmark run records shape, width,
critical path, retries, interventions, cost where real, outcome; absent
measurements say NOT MEASURED. Size: the ratified Wave 2 plus 2 to 4
attended days, MEDIUM confidence pending GE0.

## Wave 3: measure

B0 protocol freeze binds the held-out law (corpus splits at creation).
B1 at 25 tasks, TWO arms: current planner vs planner plus graph
validation. The recall arm waits for memory. The complex-subset reasoning
experiment (candidate-graph Navigator strategy) runs small and internal.
E1, A1, S1 as ratified.

## Wave 4: remember

SL-deep grows BOTH memories, never merged: the mistake miner (scars) and
workflow memory (motifs: normalized shape, conditions, measured outcomes;
OBSERVED automatically at verified delivery; promotion risk-scaled, 3
uses low risk, 5 plus founder look for release shapes; retrieval worded
"strongest measured precedent", tested). The attribution ladder runs on
every rework, insufficient-evidence a legal verdict, maker never
approves. M1 evaluates both memories on held-out tasks and adds the
recall arm.

## Wave 5: explain, validate, adapt

README conservative section now (already licensed); staged upgrades only
as capabilities measure. Booklet chapter after the validator ships.
Persona validation inside the pilot. Last, hard-gated behind B1: the
optimization laboratory, frozen snapshots, held-out tasks, founder yes
before any default, constitution permanently outside the search space.

## Token-light rules (effective now)

Typed return packets for all dispatches (1500-token budget, oversize
fails); dispatch briefs carry a JSON header beside the prose; handoff
metrics record only what is real.

## What was deliberately rejected from the spec, with flip conditions

- A separate bm-graph verify command (admission is the one door). FLIP:
  an engineer-facing need CC cannot serve.
- New storage beside the store. FLIP: a fact the extended tables provably
  cannot express.
- The full 14-node and 13-edge vocabulary. FLIP: a validator check that
  needs a missing type.
- Any hand-built graph visualization. FLIP: none; generated-only is law.
- The 20-stage process as product surface. It stays internal method.
