# 02. Process map

## The process, end to end

Three layers, in the order evidence flows.

1. EVIDENCE WRITERS. SessionStart hook writes a heartbeat row (session
   label, pid, timestamp) to the store's private directory; a PostToolUse
   touch refreshes it at most once per minute. Gate runs write the RF-5
   receipt (already live at 943c59a). Dispatch briefs may declare a
   per-item stall threshold carried on the claim; undeclared items get
   defaults (30 minutes work, 4 hours fences).
2. THE DETECTOR. bm_stall.py grows four signals beside the existing dead
   owner sweep: in-flight stall (live owner, zero file, commit or store
   deltas past threshold), spend without progress (spend ledger delta
   against tree delta over the same window), hung gate (receipt or
   sentinel age plus process check), dead provisional (existing). Every
   check stays pure read.
3. RESPONSE. Findings land on the board strip always; HIGH raises a macOS
   notification; CRITICAL (spend-without-progress during any run, hung
   gate during a tagged gate) sends a phone push. Allow-listed auto-clear
   applies ONLY to dead-owner and dead-provisional findings where every
   liveness signal is dead; it runs the same adopt-then-park or
   adopt-then-cancel verbs a human would, writing a receipt row naming the
   finding. Any error mid-clear leaves the record untouched and raises the
   finding to HIGH.

## Cadence and actors
In session: hooks fire on session events, instant detection. Out of
session: a launchd LaunchAgent (com.brothermode.sentinel) runs the sweep
every 5 minutes with jitter, machine level. The sweep flags a missing or
unloaded LaunchAgent as its own finding, so the sentinel watches its
replacement the way the v1 sweep already flags a dead watchdog.

## Failure behavior
Fail open everywhere the watchdog failed closed silently: a broken
sentinel never blocks work; a sweep that cannot read its inputs reports
NO-DATA loudly, never a clean pass.
