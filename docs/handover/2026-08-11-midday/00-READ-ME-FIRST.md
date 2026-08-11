# Read me first

Status: CURRENT as of 2026-08-11 midday. Written by session
bm1-f4c8f68d1ce30dd72faab418, the morning and midday session. No em or en
dashes.

Do not trust any commit number here without running
`git rev-parse --short HEAD`. Every verdict in this pack names the commit
it was proved at.

Read in this order:
1. 01-HANDOVER.md: done, in flight, not started, fences, open questions.
2. 04-NEXT-LOOPS-PRIORITIZED.md: the one document a continuing session
   needs.
3. 02-LEARNINGS-AND-MISTAKES.md: what this session taught and cost.
4. 03-RULES-AND-PROCESS-FIXES.md: what changed as a rule, what remains.
5. 05-VAULT-AND-OBSIDIAN.md: memory state.
6. COMMAND-CENTER.html: the board at packing time; the live copy is
   docs/plan/COMMAND-CENTER.html on main and the stable artifact link.

The three most important lines in the pack:
- v3.1.0 IS RELEASED: tagged, pushed, gated, install-verified.
- The SD2 sentinel build is OPEN: fence claimed (lifecycle e1e74722),
  intake T2, design dossier ALL FIVE GATES GREEN under strict at e0fe5ec.
  The successor adopts that fence and builds RED first from
  docs/sbe/sd2-sentinel/07-verification.md.
- Seventy founder decisions are on record with flip conditions:
  docs/decisions/RATIFIED-2026-08-11-morning.md (30) and
  docs/decisions/RATIFIED-2026-08-11-graph-engineering.md (40). Nothing
  is waiting on the founder.
