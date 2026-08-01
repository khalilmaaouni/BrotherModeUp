---
description: Check the current work against the definition of done and report what passes and what does not
---

Outcome to produce: an honest review verdict the user can trust, leading with what is solid and what is not, in plain language.

Enter the review flow of the brotherme skill. Run the mechanical command `python3 tools/bm_project.py review <task_id>` to record the evidence and move the task through its real state; never answer from memory of this conversation about whether it passed. That path is relative to the BrotherME install folder, not the user's project folder: a plugin install runs it from the plugin's own root, a clone install runs it from `~/.claude/skills/brothermode`; prefix that install path onto the command, and still run it from the user's project folder so it reads and writes that project's own records. Apply every point of the definition-of-done checklist at references/definition-of-done.md to the current work. Each point gets a pass or a not-yet with the evidence that proves it (a command that ran, a file that exists, a check that passed). Never soften a failing point; bad news comes first.
