# Ratified decisions, 2026-08-11 morning

Status: CURRENT until a later decisions record supersedes a numbered line.

Thirty founder answers through the question windows, session
`bm1-f4c8f68d1ce30dd72faab418`, recorded at the moment of taking per the
order-of-work law. Each names its flip condition where one exists. No em or
en dashes.

## Release

1. TAG v3.1.0: YES, cut now. The R5 founder gate is satisfied by this
   recorded answer; the tag sequence (version files, changelog, checksums
   last, full gate on the exact commit, tag, push) still runs in full.

## SD2, the sentinel (replaces the watchdog)

2. Engine: HYBRID. Session hooks for in-session detection plus a launchd
   background job covering hours with no live session. FLIP: if launchd
   proves unreliable across sleep cycles, fall back to hook-only plus a
   login-item re-arm, recorded as its own decision.
3. Action policy: REPORT PLUS ALLOW-LISTED AUTO-CLEAR. Provably dead
   owners past the staleness window may be auto-cleared, every action
   writing a receipt row. Everything else stays report-and-propose. This
   deliberately flips the 2026-08-10 sweep-only decision D-2; the recorded
   flip condition (repeated identical accepted clearances) was met early
   by seven stale-fence bites in 24 hours.
4. Signals, all four: dead sessions and fences; in-flight stalls (live
   fence, zero deltas past threshold); spend without progress; hung gates.
5. Heartbeat: YES, hook-written pid plus timestamp per session, closing
   bm_stall's stated no-pid gap.
6. Alerts: TIERED. Board strip always, macOS banner for high, phone push
   for critical only.
7. Thresholds: PER WORK ITEM with defaults (30 minutes work, 4 hours
   fences); adaptive thresholds parked until real data exists.

## Command center

8. Loop CC runs in Lane A immediately after SD2 (SD2 feeds its
   flightcheck).
9. Republish cadence: every loop close plus SD2 high or critical alerts.
   No hourly cron.
10. Board additions: SD2 findings strip, spend meter, decisions-waiting
    cards, gate receipt chip (RF-5).
11. Session-start surface: rendered in panel plus the stable artifact
    link.

## Self-learning

12. SL-quick lands as a one-day Wave 1 bundle in Lane B before Codex:
    RF-1 commit-msg hook, RF-2 claim session-id default, RF-4 message
    catalog, RF-5 gate receipt, PO recipes into project docs.
13. Mistake miner: BUILD. bm_learn drafts rules from telemetry and
    docs/mistakes with evidence attached; nothing self-approves; the
    existing receipt lane is the only door.
14. Vault optimization: EXECUTE the filed half-day plan.
15. Recall at dispatch: YES, every subagent brief carries matched rules
    automatically.

## Positioning

16. Primary proof of category lead: the VADR benchmark, published.
17. Benchmark corpus: 25 tasks.
18. Pilot recruitment starts after CC and G1 land.
19. Competitor comparison page with verified verdicts: PUBLISH.

## Product priorities

20. Preview lane stays after the core. FLIP: a pilot user failing to
    understand a delivery without seeing it run pulls P1 forward.
21. First-run simplicity stays after CX Phase 2.
22. CX Codex port confirmed: Lane B after SL-quick, phases 0 to 5 first.
23. Cursor: adapter-seam rework after CX Phase 1, stays out of tree until
    then.

## Governance

24. Wave 1 lanes: A is SD2 then CC; B is SL-quick then CX.
25. Registry cleanup: EXECUTED this morning. Nine dead provisional
    records adopted then cancelled with receipts; sweep now reports zero
    findings. The overnight session parked its own ten fences at close.
26. Spend ceilings stand: 800k hard, 500k soft per session.
27. No unattended stretches until SD2 catches a seeded stall end to end.
28. Execution mode: attended waves, founder gates at loop closes.

## Verification

29. V1 verifier independence: CROSS-MODEL REQUIRED at V1 close.
30. Plan verdict: APPROVED as amended by these answers.
