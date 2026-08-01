# Founder Report 2: Loop 1, state unification

Status: CURRENT. 2026-08-01. Program: release-closure
(2026-08-01-release-closure-program-ratified.md). Mode: founder-directed
autonomous run; decisions taken with recommended defaults are marked and
reversible.

## Outcome first

One database is now the only durable truth for project state, and every
change to it records who did it and why in the same transaction. The
parallel bookkeeping the external review flagged is gone or generated.

## Gate evidence, quoted

- test_all after the final edit: "test_all: 1278 tests across 9 suites,
  6 skipped, 112.9s wall. ALL GREEN" (run in the orchestrator session,
  never trusted from a builder).
- Store integrity: "verify: healthy, 0 problem(s)".
- Crash recovery: the suite includes mid-migration crash tests for the
  new schema 12 (a crash between DDL statements leaves the store
  recoverable) and forced-failure atomicity tests (entity row and its
  attribution row land together or not at all).

## What landed (commits on release/2.0-final, local, unpushed)

3342393 mapping document; c1810f2 migration brief + STATE.md prose
archived (D1); 2fe2cb9 schema 12, eight tables, service layer with
attribution; Loop 2 design commit; latest commit: JSONL stream retired,
V1 registry deleted, loss named (D2+D3).

## Bad news, first-class

- The wave-1 scratch directory threads/store-engine/ was deleted
  unarchived (it was never git-tracked). Bounded, superseded content,
  but bytes are gone. Full record:
  docs/evidence/2026-08-01-d2-deletion-record.md. Lesson queued for the
  known-mistakes ledger: archive untracked files before delete-list
  execution.
- Five stale provisional records belonging to session 17838b98 were NOT
  cleaned: the store flags that session live, and displacing a live
  session breaks the one-writer law for zero benefit (they fence no
  files). They stay visible in the dashboard until that session dies or
  you say displace.

## Decisions taken under the autonomous directive (all reversible)

- Two dead-session records closed by deliberate adopt ('--help' defect
  artifact; the superseded rc.8-era land-ledger record).
- thread-mode.json kept (live mode switch, not ownership truth).

## Spend and forecast

Loop 1 spend: roughly 320k builder tokens across two builders plus one
scout (subagent meters), well inside the source envelope. Forecast to
program end, unchanged assumptions: Loops 2 through 7 are engineering
and fit this cadence (medium confidence); Loop 8 needs 7 CALENDAR days
of your real usage from the day Loop 2 closes (the clock, not tokens,
is the constraint); Loop 9 ends with the tag only you may cut.

## Next

Loop 2 starts immediately (design ratified and committed): the seven
beginner commands become real operations over the store, gated by a
scripted first project running end to end.
