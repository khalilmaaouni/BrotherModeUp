---
description: Take a decision and the work under it back into your own hands, with nothing lost
argument-hint: <the decision you want to take back, and why>
---

Outcome to produce: the user takes one decision and the work under it back, and gets one page a developer can pick up from, with nothing deleted and nothing hidden.

Enter the handback flow of the brotherme skill. Run the mechanical command `python3 tools/bm_lead.py handback --project-id <id> --decision-id <the decision the user named> --why "<their reason, in their own words>"` (the packaged console script is `bm-lead handback`) and read its output; never describe what happened from memory of this conversation. That path is relative to the BrotherME install folder, not the user's project folder: a plugin install runs it from the plugin's own root, a clone install runs it from `~/.claude/skills/brothermode`; prefix that install path onto the command, and still run it from the user's project folder so it reads and writes that project's own records. If the user has not named which decision, run `/brotherme-decisions` first and let them pick one; never guess.

Explain in plain language, before running it, what taking it back does, in this order, because the order is the safety property:

1. Autonomous work stops first. The authorisation the user signed is paused, so nothing else can start while the handover is being written. Pausing is reversible; the authorisation can be resumed later without signing again.
2. What is known right now is written down: what should happen next, what question is still open, and the evidence behind both.
3. The work in progress is set down rather than abandoned, and the file it was holding is released, so another person or another session can pick it up.
4. The project records that the user took this decision, what would have been chosen instead, what else was weighed and why not, and what would have changed that choice.
5. One page is generated for whoever takes over: what they are taking on, the decision that was in front of us, what would have been chosen and why, the open question, the files, the commands to reproduce the current state, any work that was still in flight, and where to pick up.

Then say plainly what nothing here does: nothing is deleted, nothing already recorded is rewritten, and the choice that was not taken is kept alongside the user's own reason, so a reader a month later sees both. Work that was already in flight when control changed hands stays in flight and is listed by name on the handover page rather than silently cancelled.

If any step after the pause fails, report it with the error card format in references/kickoff.md (What happened, Impact, Recommended action, What remains safe), say plainly that the authorisation is paused and which steps did not run, and do not resume the authorisation to tidy the failure up. A half-finished handback that has been un-paused is a project running on its own again while a person believes they have the wheel.
