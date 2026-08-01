---
description: Recommend the single best next step for the project
---

Outcome to produce: one recommended next action, stated first, with a short reason and a realistic time range. Alternatives only when they are materially useful.

Enter the next-step flow of the brotherme skill. Run the mechanical command `python3 tools/bm_project.py next` to get the current recommended task straight from the store; never answer from memory of this conversation or from reading CANVAS.md by hand, since CANVAS.md is a generated view, not the source of truth. Present that recommendation as exactly one next step. If a decision from the user is blocking progress, present that decision first, with a recommended option, following the decision card format in references/kickoff.md. Estimates follow the rules in references/forecasting.md: always ranges with a confidence level, never single numbers.
