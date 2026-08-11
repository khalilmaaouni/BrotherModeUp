# Read me first

Status: CURRENT as of 2026-08-11 morning. Written by session
`bm1-4a167de53be0a5cce34ce046`, the overnight session. No em or en dashes.

Do not trust any commit number in this pack without running
`git rev-parse --short HEAD`; a document that names HEAD is stale the moment
it is committed. Every gate verdict here names the SHA it was proved at.

Read in this order:
1. `01-HANDOVER.md`: what is done, in flight, not started, held, and open.
2. `04-NEXT-LOOPS-PRIORITIZED.md`: the one document Fable needs to continue.
3. `02-LEARNINGS-AND-MISTAKES.md`: what the night taught, and what it cost.
4. `03-RULES-AND-PROCESS-FIXES.md`: what to change so the same lessons stop
   repeating.
5. `05-VAULT-AND-OBSIDIAN.md`: memory hygiene, best practices to keep.
6. `COMMAND-CENTER.html`: the board as it stood at packing time; the live
   copy is `docs/plan/COMMAND-CENTER.html` on `main` and is newer the moment
   anyone works.

The single most important line in the pack: every mechanical prerequisite
for the v3.1.0 tag is green and bound to `27a9719`, later hardened through
`d7dc252`; the tag waits only for the founder's explicit yes, and nothing
in this pack may be read as that yes.
