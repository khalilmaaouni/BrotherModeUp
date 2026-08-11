# Learnings, mistakes, and what went best

Status: CURRENT, 2026-08-11 midday. Every line carries its evidence. No em
or en dashes.

## Learnings the session paid for

1. A gate holds the WHOLE tracked tree, documentation included. Editing
   the board mid-gate appended a synthetic clean-checkout FAILURE and
   voided a 9 minute run by design. M20 on the permanent record; the
   ledger line in references/mistakes.md widened to say so.
2. bm_learn cancel refuses a foreign record (not-owner guard);
   adopt-then-cancel is the only recovery path for a dead session's
   provisional record. Matches the overnight session's learning 8 from
   hours earlier; now proven twice in one day.
3. A closing session can park its own fences BETWEEN two of your sweeps:
   the 28-to-18 finding drop was coordination, not a defect. Query the
   store's transitions before concluding anything about a moving count.
4. The gate receipt works: the 943c59a verdict was read from
   .brothermode/gate-receipt.json instead of hand-quoted, first use, same
   day it landed.
5. test_bm_plugin_install.py is load-sensitive: 1 failure inside a gate
   run that overlapped a builder's suites, then 6 consecutive standalone
   greens. Watch item, not chased; the walltime-lint class suggests the
   fix shape.
6. The slop-gate drift detector false-positives on the literal word
   "fallback" even when it names a ratified founder decision. Answer it
   with the evidence and continue; never work around the hook.
7. The write-sites manifest demands an entry for ANY file writing to an
   output funnel; a builder correctly deviated from its file allowlist to
   satisfy the gate, read the loader first, and reproduced the RED before
   editing. The deviation-with-evidence pattern is the right one.
8. sbe_design's diagram check requires every mermaid node to trace to a
   declared entity or component; declaring components as bullets in
   06-diagrams.md itself is the one-file form and it passes.
9. Store heartbeat age is computed from the record's own updated_at plus
   session activity; token files in .brothermode/fence are keyed by
   sha256 of the harness id, so slot collisions are effectively
   impossible.

## Mistakes, named

1. M20, mine: refreshed the board while my own gate ran. Cost one gate
   run plus the re-run; no work lost (in-flight copy saved to scratch
   first). The rule that failed was read as being about code; it is
   about tracked bytes.
2. Reached for a scheduled wakeup while two tracked background jobs were
   already going to notify. Slop-gate refused it, correctly. Dropped.
3. The first cleanup attempt ran cancel before adopt and collected nine
   refusals; the recovery order is adopt then cancel (learning 2).

## What went best, kept as practice

1. RED FIRST held everywhere: both builders quoted failing output before
   every fix, and the SD2 dossier's verification plan pins it for the
   build.
2. Two builder dispatches, both worktree-isolated, both landed by the
   orchestrator with suites re-run by my own hands; zero collisions.
3. Decisions taken through the windows at the moment they arose: seventy
   in one day, each with a flip condition, none discovered later in a
   summary.
4. The board obeyed its own brevity budget after measurement showed it
   violating five caps, and nothing was deleted to get there.
5. The stall detector's first real day: 28 findings, exact clearing
   commands, zero findings after cleanup. The feature earned its keep
   before its successor was even designed.
