---
description: Generate the handover pages that let another person take this project over
---

Outcome to produce: one folder of generated pages, written from that project's own records, that a person who was not in this conversation can read and act on.

Enter the handover flow of the brotherme skill. Run the mechanical command `python3 tools/bm_lead.py handover-pack --project-id <id>` (the packaged console script is `bm-lead handover-pack`) and read its output; never write any of these pages by hand and never fill a gap in them from memory of this conversation. That path is relative to the BrotherME install folder, not the user's project folder: a plugin install runs it from the plugin's own root, a clone install runs it from `~/.claude/skills/brothermode`; prefix that install path onto the command, and still run it from the user's project folder so it reads and writes that project's own records.

Seven pages are written into a `Handover` folder at the top of the user's project, in reading order:

1. `00-SITUATION.md`: where the project stands, what was authorised, what has been spent against the ceilings, how much of the planned work is accepted, the current forecast, and anything open that only a person can clear.
2. `10-DECISIONS.md`: every decision taken, newest first, grouped by what it was about, each with what else was weighed and what would have changed it.
3. `20-RISKS.md`: the risks still open, newest first, each with what would settle it.
4. `30-CALIBRATIONS.md`: the checks that were deliberately broken to prove a guard actually bites, each with what was broken and what was observed.
5. `40-LEARNINGS.md`: what was learned along the way that a reader would otherwise have to rediscover.
6. `50-TIMELINE.md`: every catch-up in order, oldest first, so a reader can replay the run forwards.
7. `60-HANDBACKS.md`: every decision the user took back, each with the decision it answers and the full page a developer picks up from.

Who this is for: a business analyst or a project lead who has to take the project over or account for it, and who has no access to this conversation. Every claim on every page carries how it was checked and the id of the record it came from, so any line can be traced back rather than trusted. A claim resting on reasoning rather than on a check that ran says so on its own line.

Two properties worth telling the user in plain words. The pages are generated, so regenerating them changes nothing unless the records changed, and a page written today still reads the same a month from now because it only shows what was known at the moment it covers. The pack covers one project: a folder holding several projects produces one set of pages per project rather than a merged view, and no page implies otherwise.

If the project has no records yet, say so plainly and point at `/brotherme-start`; do not generate a folder of empty pages.
