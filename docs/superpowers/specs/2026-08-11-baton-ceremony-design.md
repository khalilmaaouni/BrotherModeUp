# The Baton Ceremony: session handover as law, 2026-08-11

Status: RATIFIED by the founder through seven question windows on 2026-08-11
(afternoon session, harness 53c70dcb). Design approved for build in the same
round. No em or en dashes anywhere in this document.

## 1. Purpose, and the objective it serves

Sessions die; work must not. The founder's directive, verbatim in intent: at
every session switch there is a proper ceremony, closing the past session and
preparing a ZIP with full documentation, learnings, follow ups, the command
center, misses and near misses, and errors, and this becomes a rule at every
start of a new brothermode session.

North star objective served: continuity. Every prior loss this machine has
recorded (dead sessions leaving provisional records, stale locks, a 3 of 5
close rating raised to 4 of 5 only after the close report was rewritten) is a
failure of the baton, not of the work.

## 2. Decisions ratified today, with flip conditions

1. SCOPE: the rule covers BOTH ends. A close ceremony before a session ends,
   a start ceremony before new work. Chosen over close-only and start-only.
2. ENFORCEMENT: mechanical detect plus tool. A written rule alone was
   rejected; a hard-blocking hook was rejected as hostile to quick sessions.
3. PACK FORMAT: hybrid. A tool generates the traceable skeleton from the
   store; the closing session writes the narrative. Fully generated and fully
   hand authored both rejected.
4. ORDER: ceremony built first, then Loop 4 user journeys (BrotherSBE).
5. INSTALL LAG: the install clone at ~/.claude/skills/brothermode is updated
   to current now; the two dirty files it carried are preserved to a dated
   patch in the handovers folder first, never lost.
6. SD2: the sd2-sentinel-build fence stays PARKED except for one manifest
   edit (section 6). SD2 is not built this session. Flip condition: the
   founder orders SD2 built.
7. HOOK WIRING DEFERRED: bm_sessionstart.sh and hooks/hooks.json sit under
   the SD2 fence and are not edited for wiring this session. Detection
   meanwhile is the existing session start verify plus the detect command.
   Flip condition: SD2 lands, or the founder frees those files.

## 3. The rule, exact text

The CLOSE half. Before a brothermode session ends, in this order:

1. Refresh the handover pack: run
   `python3 tools/bm_handover.py skeleton` from the project folder, then fill
   every narrative slot by hand (learnings, mistakes, near misses, next
   loops). The six files follow the 2026-08-11 midday shape: 00-READ-ME-FIRST,
   01-HANDOVER, 02-LEARNINGS-AND-MISTAKES, 03-RULES-AND-PROCESS-FIXES,
   04-NEXT-LOOPS-PRIORITIZED, 05-VAULT-AND-OBSIDIAN, plus 06-CLOSE-REPORT and
   a copy of the command center page.
2. The close report opens with one unmissable line: FINISHED or UNFINISHED,
   and if UNFINISHED, exactly where the baton lies (the morning session's 4
   of 5 lesson, kept as law).
3. Park every record this session holds, with handover text, through
   `bm_store.py park`, so the handover row and the state transition are one
   transaction.
4. Commit the pack folder in the project repository. The zip is packaging and
   never the only home (ratified precedent, commit 6db52b2).
5. Zip the pack: `python3 tools/bm_handover.py zip`, landing in
   ~/Documents/BrotherModeUp-handovers/ with a date and slot name.
6. Update the memory vault session log to the close moment.
7. Run `python3 tools/bm_handover.py verify-close` and quote its verdict. A
   FAIL means the ceremony is not done; the session does not claim closure.

The START half. At every new brothermode session, before any new work:

1. Run `python3 tools/bm_handover.py detect` and read what it reports: the
   newest pack, its age, unacknowledged handovers, and leftovers held by dead
   sessions.
2. Read the newest pack in its stated order.
3. Acknowledge consumed handovers (`bm_store.py handover-ack`), and adopt or
   park every dead session leftover with receipts (adopt then park or adopt
   then continue; cancel before adopt is the recorded mistake, never repeated).
4. Open this session's own work record via bm_learn apply.
5. State the baton line to the founder: what was adopted, what was parked,
   what the pack says comes next.

## 4. The tool: tools/bm_handover.py

Python 3.9, standard library only, no network, no subprocess. Store access is
read only through bm_store's public functions; every mutation the ceremony
needs (park, handover-ack) stays in bm_store where it already lives. Output
documents are written through the same audited primitive the repository
already trusts for generated documents.

Commands:

- `skeleton [--out DIR] [--slot NAME]`: writes the pack folder (default
  docs/handover/<date>-<slot>/) with the six narrative files pre filled from
  the store (records, fences, unacked handovers, decisions, verify output)
  and clearly marked narrative slots (the marker is FILL-BY-HAND). Copies the
  command center page when one exists. Refuses to overwrite a slot a human
  already filled (the I10 rule: generated output never destroys human text).
- `verify-close [--pack DIR]`: the mechanical checklist. FAIL when a
  narrative slot is still FILL-BY-HAND, when the close report lacks the
  FINISHED or UNFINISHED line, when the newest zip is older than the pack,
  when this session still owns unparked records. NO-DATA when there is no
  store or no pack to judge, stated plainly, never a PASS. Exit 0 only on
  PASS.
- `zip [--pack DIR]`: packages the pack folder to
  ~/Documents/BrotherModeUp-handovers/BrotherMode-Handover-<date>-<slot>.zip.
  Idempotent by content: re zipping an unchanged pack says so.
- `detect`: the successor's first command. Reports newest pack and zip with
  ages, unacknowledged handovers, and records or fences whose owning session
  is dead, each with its clearing command. Read only, exit 0 always (it
  informs; the start half of the rule is what acts).

## 5. What is reused, not rebuilt

- bm_store handovers table, park with handover payload, handovers listing,
  handover-ack (schema 5, transactional). The ceremony adds no store schema.
- bm_lead.py handover-pack: the seven generated ledger pages remain available
  and the skeleton's 00 file points at them; nothing is duplicated.
- The existing session start verify remains the ambient detector; detect is
  its on demand twin with pack awareness.
- The midday pack shape (six files plus close report plus command center) is
  the template, taken from the copy filed in git at 6db52b2 and 12e6259.

## 6. The write sites collision, and its lawful path

test_no_unreviewed_write_sites demands a reviewed count in
tools/write_sites.json for any tool that writes files. That manifest is under
the parked sd2-sentinel-build fence (lifecycle e1e74722) whose owning session
is dead. The lawful path, proven twice on this machine: adopt, edit, park
back. This session adopts the fence, adds the reviewed entry for
tools/bm_handover.py with its exact site count and a review note, re parks the
fence with a note saying SD2 remains unbuilt at unchanged priority, and
records the receipts. No other fenced file is touched.

## 7. Where the rule binds

- ~/.claude/CLAUDE.md, brothermode section: the binding machine wide text,
  naming tools/bm_handover.py as the enforcing file. Enforced by:
  verify-close and detect. Landed by this session (user scope file, founder
  standing instruction to keep it current).
- SKILL.md amendment: PROPOSED, not landed. One entry appended to the vault
  pending amendments note. The constitution is founder owned.
- This repository: docs/handover/README.md gains the ceremony contract so the
  repo explains its own packs.

## 8. Verification plan, RED first, in build order

- V1 skeleton: from a temp store with two records, skeleton writes all seven
  files, each pre filled section naming its record ids; FILL-BY-HAND markers
  present. RED before the tool exists.
- V2 human text survives: re running skeleton over a filled pack changes no
  human bytes (I10).
- V3 verify-close bites: an unfilled slot FAILs naming the file and line; a
  missing FINISHED line FAILs; a pack newer than the newest zip FAILs; all
  clean PASSes; no store is NO-DATA and exit nonzero.
- V4 zip: creates the dated zip in the handovers folder; unchanged content
  re run reports idempotence.
- V5 detect: seeded dead session record is reported with its clearing
  command; fresh pack reports ages; empty estate is NO-DATA not silence.
- V6 write sites: test_no_unreviewed_write_sites green with the new entry;
  count matches the scanner exactly.
- CLOSE: the full gate (tools/test_all.py) green after the last edit, quoted
  from .brothermode/gate-receipt.json, plus this session closing itself with
  the new ceremony as its first live run.

## 9. Execution and tiers, declared

Orchestrator builds inline as sole writer. Lane: main Anthropic lane, tier
Fable, reason: constitution adjacent tool, strict law repository, high
coupling to the store API; mechanical bulk is too small to brief out.
Adversarial review before close: one read only reviewer pass (falsification
brief per PO-5). No cheap lane use: this work fails the mechanical test.

## 10. Remaining and honest limits

- The ceremony cannot force a crashed session to have written a pack; the
  start half exists exactly for that case, and detect names the dead.
- verify-close checks structure and freshness, not narrative quality; the
  founder's felt rating remains the only judge of prose.
- Hook wiring deferred (decision 7): until SD2 lands, nothing refuses a
  session that skips detect; the session start verify still surfaces
  leftovers ambiently.
- The rule binds Claude sessions through CLAUDE.md; other runtimes receive
  it only when the SKILL.md amendment lands (founder gate).
