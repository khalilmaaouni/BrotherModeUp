---
description: Recommend the single best next step for the project
---

Outcome to produce: one recommended next action, stated first, with a short reason and a realistic time range. Alternatives only when they are materially useful.

Enter the next-step flow of the brotherme skill. Run the mechanical command `python3 tools/bm_project.py next` to get the current recommended task straight from the store; never answer from memory of this conversation or from reading CANVAS.md by hand, since CANVAS.md is a generated view, not the source of truth. That path is relative to the BrotherME install folder, not the user's project folder: a plugin install runs it from the plugin's own root, a clone install runs it from `~/.claude/skills/brothermode`; prefix that install path onto the command, and still run it from the user's project folder so it reads that project's own records. Present that recommendation as exactly one next step. If a decision from the user is blocking progress, present that decision first, with a recommended option, following the decision card format in references/kickoff.md. Estimates follow the rules in references/forecasting.md: always ranges with a confidence level, never single numbers.
