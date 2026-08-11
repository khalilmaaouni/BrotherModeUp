# 01. Purpose brief

## Outcome
A stall detector that survives the sessions it watches. The current sweep
(tools/bm_stall.py) runs only at session start and proposes only; the old
watchdog died with its own session (RF-6). SD2 makes detection continuous,
durable across session death and reboot, and able to clear provably dead
work automatically with a receipt per action.

## Who it is for
P1, the non-engineer founder: hears about a stall through the board, a
desktop notice, or a phone push for critical, without reading logs. P2,
the solo builder: recovery without archaeology. Every Claude session on
this machine is a consumer of its fences and heartbeats.

## Success conditions
1. Each of the five signals (dead owner, in-flight stall, spend without
   progress, hung gate, dead provisional) caught RED first against a
   fixture built from this week's real scars.
2. A seeded dead-owner stall is auto-cleared under the allow-list with a
   receipt naming the finding; the same fixture with one live signal is
   NOT cleared.
3. The kill-test: the owning session dies mid-run and the launchd job
   still detects and reports within one interval, quoted from its log.
4. Hook overhead stays inside the measured budget (test_bm_hookperf).
5. Four-places registration and verify-install exit 0.

## Explicit exclusions
No model judgment inside the detector (deterministic end to end). No
auto-clear beyond dead-owner and dead-provisional findings. No
cross-machine sentinels. The watchdog cron pattern retires only when the
kill-test passes.

## Main risks
Session liveness across machine sleep is designed from data, not yet
measured (the spec names this). A false auto-clear would release a live
session's fence: guarded by requiring every liveness signal dead plus a
receipt, and clearing fails toward NOT clearing.

## Founder-held decisions
All taken 2026-08-11 morning, decisions 2 to 7 in
docs/decisions/RATIFIED-2026-08-11-morning.md: hybrid engine, allow-listed
auto-clear, all four signals, hook-written heartbeat, tiered alerts,
per-item thresholds.
