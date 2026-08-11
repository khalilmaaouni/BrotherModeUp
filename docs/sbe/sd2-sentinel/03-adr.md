# 03. Architecture decision record

## Context
The watchdog was a cron inside a session: the session died, the guard died,
re-arm was manual (RF-6, seven stale-fence bites in 24 hours, the 8 August
runaway unobserved for ten hours). The passive v1 sweep runs only at
session start and cannot act. Something must watch when nothing runs.

## Criteria
Named, with the value observed on this estate: survival across session
death = mandatory (the defining scar); detection latency in session =
under a minute (hooks already fire per event); false-clear risk =
near zero tolerated (a wrong clear releases a live fence); ops maturity =
one operator, so at most one new moving part; reversibility = the
mechanism must uninstall in minutes.

## Options considered

### Rejected: hooks only
Session hooks detect instantly while a session runs and cost no new
infrastructure, but they are blind exactly when nothing runs, which is the
RF-6 failure restated. Survival across session death is the criterion that
kills this option.

### Rejected: per-session cron re-arm
What we had. The guard's lifetime equals the session's lifetime by
construction, and re-arm depends on a person remembering. It is the
failure itself, kept for the record as the second distinct alternative.

## Decision
Hybrid: session hooks for instant in-session detection, plus one machine
level launchd LaunchAgent running the sweep every 5 minutes, surviving
session death and reboots. Auto-clear is allow-listed to provably dead
work only, receipted per action. Founder decision 2, 2026-08-11.

## Consequences
One OS-level moving part to install and health-check; the sweep flags its
absence as a finding, so the new part is watched by the thing it serves.
Detection latency out of session is bounded by the 5 minute interval.
launchd behavior across sleep cycles is unmeasured until the kill-test.

## What would flip it
launchd proving unreliable across sleep cycles flips to hook-only plus a
login-item re-arm, recorded as its own decision (the flip condition
ratified with decision 2). A month of identical accepted clearances on an
S2 finding class may widen the allow-list, only as a reviewed change.
