---
description: Start a project with a short guided conversation that ends in one clear project brief
argument-hint: <what you want to build or achieve>
---

The user wants to start a project. Their goal, in their own words: $ARGUMENTS

Outcome to produce: one clear project brief (the Project Canvas) and one recommended first decision, in plain language, with a realistic time and cost range.

Enter the guided kickoff flow of the brotherme skill. Follow the kickoff instructions at references/kickoff.md: size up the goal, ask only the questions whose answers change the scope, one decision at a time with a recommended option first. Once the goal, scope, and first decision are settled, run the mechanical command `python3 tools/bm_project.py start` with the gathered details: it creates the project record in the store and regenerates CANVAS.md from those rows. Never fill CANVAS.md by hand and never answer from memory of this conversation about what the project record holds; the command's own output is the only source of truth. If the goal above is empty, ask for it in one sentence before anything else.
