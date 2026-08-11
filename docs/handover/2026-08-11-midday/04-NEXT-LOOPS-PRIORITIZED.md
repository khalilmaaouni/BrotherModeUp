# The next loops, fully prioritized

Status: CURRENT, 2026-08-11 midday. The one document a continuing session
needs. Ordering follows the ratified roadmap
(docs/plan/ROADMAP-2026-08-11-GRAPH-ENGINEERING.md) and seventy recorded
founder decisions. Two writer lanes maximum, always. No em or en dashes.

## Priority 0: adopt the fence and build SD2

The fence sd2-sentinel-build (lifecycle e1e74722) is claimed and waiting:
adopt it (`python3 tools/bm_store.py adopt e1e74722bbc34372abd26cda68591763
--version 1 --session <YOUR_SESSION_ID> --adopt-from-live-session`), then
build RED FIRST from the dossier:
- Spec: docs/superpowers/specs/2026-08-11-sd2-sentinel-design.md
- Dossier (T2, all design gates green): docs/sbe/sd2-sentinel/
- The build order is the verification plan's rows V1 to V6; the
  kill-test (V3) is the loop's namesake check.
- Decisions binding it: 2 to 7 morning (engine, auto-clear, signals,
  heartbeat, alerts, thresholds).
EFFORT: 1.5 to 3 days, MEDIUM-HIGH confidence. SWARM: Opus 4.8 or Sonnet
builder in worktrees returning deltas, orchestrator lands and verifies;
fresh-context refute on the auto-clear seam before close (falsification
brief: try to make it clear live work).

## Lane B, parallel: CX Codex Phase 0 to 2

Ratified order after SL-quick (which is CLOSED). Phase 0 pins the current
green baseline (e0fe5ec or later, re-count the suite numbers), per the
corrected spec in docs/plan/PROGRAM-PLAN-2026-08-10.md section CX.
EFFORT: phases 0 to 2 inside the 4 to 8 day range, MEDIUM-LOW.

## Then, Lane A: CC command center generator

Spec S1 to S7 approved; SD2 supplies the flightcheck's stall input; the
gate receipt chip reads .brothermode/gate-receipt.json (live). The hand
page deletes at S7. EFFORT: 1.5 to 3 days, MEDIUM.

## Wave 2 after those: the verified graph

G1 governor with the four ratified validator checks (write overlap, gate
ordering, evidence gap, cycles and retry bounds; advisory two weeks then
refusing; COMPLEX plans only), GE2 slim typed edges on the existing
tables, V1 with criterion records and computed evidence freshness, D1,
C1. BINDING: the four duplicate-risk warnings in
docs/plan/GE0-TRUTH-MAP-2026-08-11.md (reuse critical_path from
bm_docs.py, extend the upsert_units cycle check, build on the claims
overlap machinery, structure evidence.ref rather than adding a table).
EFFORT: ratified Wave 2 plus 2 to 4 days, MEDIUM.

## Standing rules for every loop

Fences first, RED first, quoted green after the last edit, receipts over
narration, no tracked edits while a gate runs (M20), board republished at
every loop close to the stable artifact link, typed return packets at the
1500 cap, and no unattended stretches until SD2 catches a seeded stall
end to end (decision 27). The founder's execution mode is attended waves
with gates at loop closes.
