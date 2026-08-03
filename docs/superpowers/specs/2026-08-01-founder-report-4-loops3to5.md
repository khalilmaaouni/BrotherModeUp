# Founder Report 4: Loops 3, 4 and 5

Status: CURRENT. 2026-08-01. Program: release-closure. Mode:
founder-directed autonomous run.

## Bad news first

A claim I made to you in Report 3's neighborhood was false, and an
adversarial reviewer proved it rather than a test catching it. Loop 3
shipped a consent gate and I told you a fresh install writes nothing
before the person says yes. One hook was ungated: the automatic snapshot
that fires when a session runs out of room wrote git references, a
commit object containing untracked working files, and an event file, all
with no consent config present. The reviewer reproduced it in a
throwaway home directory and pasted the three paths it created.

Why the suite missed it: every consent test drove the two hooks I knew
about. Nothing drove the snapshot hook. The fix is not only the gate; it
is a permanent step zero in the install rehearsal that drives ALL the
hooks with no consent present and asserts the reference list and the
whole file tree are unchanged. A future hook that forgets the gate now
fails that step.

Second correction, smaller: the doctor counted a skipped check as a
proof. A dirty working tree turned the release-integrity check into a
skip, and the run still reported healthy. It now says how many of ten
were proven, how many skipped, how many failed, and --strict refuses any
skip at all.

## Outcome

Loops 3, 4 and 5 are closed. A stranger's install now asks before it
writes; the doctor answers ten questions instead of one and tells a
non-engineer exactly what command fixes each failure; forecasts and
alerts are stored records rather than prose; and no number can appear on
a status screen unless a row backs it.

## Gate evidence, quoted

- "test_all: 1354 tests across 11 suites, 6 skipped, 159.0s wall.
  ALL GREEN" and "verify: healthy, 0 problem(s)", run in the
  orchestrator session after the final edit.
- Loop 3 gate: the rehearsal (scripts/rehearse_fresh_install.py) drives
  the documented clone-path story end to end in a throwaway home, both
  runs pasted unedited in docs/evidence/2026-08-01-fresh-home-rehearsal.md.
- Loop 4 gate: lifecycle states travel only through the service layer,
  mapped to running tests in the Loop 4 close-out spec (no new code).
- Loop 5 gate: test_every_displayed_number_traces_to_a_row harvests
  every number from status, next, forecast show, alert list and the
  delivery packet and fails the build if one has no row behind it.

## What the rehearsal caught on its own

The release integrity manifest was fifteen commits stale, which would
have failed the doctor's integrity check on every clean checkout,
including continuous integration. Regenerated, and regenerated again in
the latest commit, so a clean clone passes.

## Decisions taken (reversible)

- Skips still exit zero (a skip can be legitimate) but are counted and
  named; --strict exists for anyone who wants zero tolerance.
- Bash writes will be detected, not blocked (Loop 6 design): blocking
  them means gating the shell, which breaks the tool.

## Spend and forecast

Loops 3 to 5 spend: roughly 2.4M subagent tokens including three
adversarial reviewers and two fix batches. Remaining: Loop 6 (security
closure, designed), Loop 7 (runtime adapters), Loop 8 (validation
evidence, gated on your real usage, seven calendar days), Loop 9
(adversarial release review, then your tag). Engineering confidence
medium; the calendar gate is not compressible.

## The one thing waiting on you

Twenty-one commits sit on the local branch, unpushed. GitHub Desktop
control was denied at the permission dialog, and your standing rule
forbids a quiet terminal push. Grant the dialog, push from the app
yourself, or say the word and I will use the terminal once.
