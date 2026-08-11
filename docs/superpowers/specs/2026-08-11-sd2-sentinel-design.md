# SD2, the sentinel: design

Status: CURRENT. Ratified 2026-08-11 morning through the founder question windows
(decisions 2 to 7 in docs/decisions/RATIFIED-2026-08-11-morning.md).
Replaces the session-bound watchdog (RF-6) and extends tools/bm_stall.py
(Loop SD, landed at d7dc252) from a passive session-start sweep into an
active, durable detector. No em or en dashes.

## The problem, in scars

- The watchdog was a cron inside a session; the session died, the guard
  died, and re-arm was manual every time (RF-6, 2026-08-10 evening).
- Seven stale-fence bites in 24 hours; nine dead provisional records sat
  in the registry for days until this morning's founder-approved cleanup.
- The 8 August runaway: spend climbing, tree unchanged, no mechanical
  observer. The stop condition was a sentence, not a check.
- Four near-poisoned gate runs in one night, avoided only by hand checks.

## What exists, so this builds on it

- tools/bm_stall.py: liveness oracle (owner_liveness, pure function),
  pure-read sweep, findings with exact clearing commands, --json output,
  session-start wiring (fail open), registered pure_read in bm_effects.
- tools/bm_controller.py heartbeats and orphan resume, but only inside a
  Full-Auto run.
- The spend guard hook (machine level) and session cap hook.

## Architecture: three layers

### Layer 1, evidence writers (new signals into the store)

- SessionStart hook writes a heartbeat row: session label, pid, started
  timestamp. A lightweight PostToolUse touch refreshes it at most once per
  minute (never per call; hook overhead is a measured budget, see Loop X2).
- Gate runs already write a sentinel file (PO-1 pattern); test_all gains
  the RF-5 gate receipt, which doubles as the gate-liveness signal.
- Dispatch briefs may declare a stall threshold per work item; the claim
  carries it (store field, default 30 minutes for work, 4 hours fences).

### Layer 2, the detector (bm_stall.py grows)

Five checks, each pure-read, each RED FIRST against a fixture built from
the named scars above:

| Signal | Detects | Evidence read |
|---|---|---|
| S1 dead owner | fence or claim whose owner session cannot return | heartbeat rows (now with pid), controller runs, staleness window |
| S2 in-flight stall | live owner, zero progress past the item's threshold | newest of: file mtimes under the claim's files, commits touching them, store transitions |
| S3 spend without progress | meter climbing while the tree does not change | spend ledger deltas vs tree deltas over the same window |
| S4 hung gate | suite past its ceiling, or sentinel never lands | gate receipt or sentinel file age, pgrep result |
| S5 dead provisional | never-promoted record with a dead owner | provisional records plus S1 verdict |

### Layer 3, response (the part the watchdog never had)

- Escalation ladder: every finding lands on the board strip; HIGH raises
  a macOS notification; CRITICAL (S3 during any run, S4 during a tagged
  gate) sends a phone push. Severity mapping lives in one table.
- Allow-listed auto-clear: ONLY S1 and S5 findings whose owner is
  provably dead (stale heartbeat AND dead pid AND no live controller run)
  may be cleared automatically, using the same adopt-then-cancel or
  adopt-then-park verbs a human would run, each action writing a receipt
  row naming the finding that justified it. Everything else remains
  report-and-propose. A finding with any live signal is NEVER auto-cleared.
- Durability: a launchd LaunchAgent (com.brothermode.sentinel) runs the
  sweep every 5 minutes with a small jitter, machine level, surviving
  session death and reboots. The session hooks keep instant in-session
  detection. The sweep flags a missing or unloaded LaunchAgent as its own
  finding (the sentinel watches its replacement, as the sweep already
  flags a dead watchdog today).

## Failure policy

Fail open everywhere the watchdog failed closed silently: a broken
sentinel must never block work, and a sweep that cannot read its inputs
reports NO-DATA loudly rather than a clean pass (the NO-DATA law).
Auto-clear fails toward NOT clearing: any error mid-clear leaves the
record untouched and raises the finding to HIGH.

## Done-checks (loop exit)

1. Each of the five signals caught RED FIRST against its fixture, then
   green.
2. A seeded stall (synthetic claim, dead owner, planted files) is
   detected, auto-cleared under the allow-list, and its receipt row names
   the finding. The same fixture with one live signal is NOT cleared.
3. Kill the session mid-run: the launchd sentinel still detects and
   reports within one interval. Quoted from the launchd log.
4. Hook overhead stays within the measured budget (test_bm_hookperf).
5. Four-places registration plus checksums; verify-install exit 0.

## Deliberately out

Auto-clear beyond S1 and S5 (an in-flight stall is a judgment call);
cross-machine sentinels; any model-driven judgment inside the detector.
The detector is deterministic end to end; models never decide liveness.

FLIP: if a month of S2 reports shows the same human response every time,
propose that response as its own allow-listed action, as a reviewed
change.
