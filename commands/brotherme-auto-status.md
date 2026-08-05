---
description: Show where the Full-Auto controller run stands right now, in plain language
---

Outcome to produce: one short status view of the CONTROLLER run (distinct from `/brotherme-status`, which reports the project's own beginner-facing status) that the user can read in under a minute.

NAMING NOTE for whoever maintains this file: `/brotherme-status` already exists and reports `python3 tools/bm_project.py status`, a different, established command this file must never collide with or silently redefine. This command is named `/brotherme-auto-status` on purpose, alongside `/brotherme-auto` and `/brotherme-stop`, so both status views can be reached without either one shadowing the other.

Enter the Full-Auto status flow. Run the mechanical command `python3 tools/bm_controller.py status --project <id>` and read its output; never answer from memory of this conversation about where the run stands. That path is relative to the BrotherME install folder, not the user's project folder: a plugin install runs it from the plugin's own root, a clone install runs it from `~/.claude/skills/brothermode`; prefix that install path onto the command, and still run it from the user's project folder so it reads that project's own records.

Translate the report into plain language: the run's state (and what that state means for what happens next, per `docs/FULL-AUTO.md`'s state-machine section), how many units are in each stage, any unit whose result is still awaited (name it, since that is exactly what would block `/brotherme-auto` from making further progress without the user's help), the spend verdict, and any open, founder-only step. If there is no controller run for this project yet, say so plainly and point at `/brotherme-auto` to begin one.
