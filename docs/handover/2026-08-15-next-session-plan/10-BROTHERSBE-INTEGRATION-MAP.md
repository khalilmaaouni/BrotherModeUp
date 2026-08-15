Status: CURRENT.

# BrotherMode and BrotherSBE, enforced against stated: the parity read

Queue item O11, executed 2026-08-16 by a read-only reviewer over both
repositories, every classification anchored to the file that proves it.
This page is the integration map the vision-fold session designs from:
complementarity, never duplication, per the founder's standing order.

## Duplicated, one owner proposed

1. One-writer-per-file fencing: BrotherMode's bm_fence_hook.py
   (sqlite-backed, hooks/hooks.json PreToolUse) and BrotherSBE's own
   sbe_fence_hook.py (STATE.md-registry-backed) are two independent
   mechanisms with two failure surfaces. Proposed owner: BrotherMode, the
   general coordination primitive; BrotherSBE consumes it through its
   team-coordination module instead of maintaining a second hook.
2. Consent and telemetry write-gating: BrotherMode's is mechanically
   stronger (zero writes pre-consent, proven by test_bm_consent.py
   walking HOME); BrotherSBE gates nags behind a profile flag. Proposed
   owner: BrotherMode.

## One-sided, the sibling's users need it

1. Bash-write detection after the fact (bm_bash_audit.py hash pair):
   only BrotherMode. BrotherSBE's blast-radius law L14 is human review
   only, in its own words, and its domain (migrations, SQL) is where the
   gap bites hardest. Integration move 1: L14 consumes bm_bash_audit.
2. Mechanical evidence gates (sbe_gate.py --strict: pinned-snapshot
   re-derivation, signed approval, migration row counts): only
   BrotherSBE. BrotherMode's every-number-verbatim promise is prose with
   no enforcing file. Integration move 3 candidate for numbers on
   founder-facing pages.
3. Effect-class command registry (bm_effects.py, UndeclaredCommand):
   only BrotherMode. BrotherSBE's 85 tools have no documented-read-only
   trap.
4. The hollow-check honesty sweep (sbe_checks.py full fixtures hollowed
   by evals/test_no_data_class.py, so no check can silently PASS over
   absent evidence): only BrotherSBE. Integration move 2: port the sweep
   onto doctor.py and the effects checks.

## Missing in both, stated rather than implied

- OS-level write containment: both fences are cooperative, both say so.
- Identity behind an approval: both products prove an answer was given,
  neither proves who gave it, and both admit it in their limits pages.
- Cross-repo concurrent-write detection: both hooks are single-project
  rooted, and a session working both trees at once (exactly what the
  integration creates) is unguarded by either. This is the first NEW
  control the integration program should size.

## The three moves, priority order

1. BrotherSBE L14 consumes bm_bash_audit.py rather than human review
   alone.
2. Retire sbe_fence_hook.py in favour of bm_fence_hook.py behind
   BrotherSBE's coordination module.
3. Port the honesty sweep onto BrotherMode's own checks.

Each is a design decision for the vision-fold session, ratified through
founder windows, with the labour test and the no-new-gates rule from
docs/plan/ADOPTER-REVIEW-ADAPTATION-2026-08-15.md applied to each.
