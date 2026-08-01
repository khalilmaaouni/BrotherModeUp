---
description: Show where the project stands right now, in plain language
---

Outcome to produce: one short status view the user can read in under a minute, leading with what has been achieved, not with process.

Enter the status flow of the brotherme skill. Run the mechanical command `python3 tools/bm_project.py status` and read its output; never answer from memory of this conversation about where the project stands. That path is relative to the BrotherME install folder, not the user's project folder: a plugin install runs it from the plugin's own root, a clone install runs it from `~/.claude/skills/brothermode`; prefix that install path onto the command, and still run it from the user's project folder so it reads that project's own records. Translate what it reports into the default status view defined at references/status-view.md: exactly Goal, Direction, Progress, Time remaining, Decision needed, Risk, Evidence, and Next step. Show deeper detail only if the user explicitly asks for the advanced view. For what counts as worth flagging, follow references/pulse.md.

The command's output now carries two more sections, both read from rows, never estimated: the latest forecast (a range with its confidence and the event that triggers the next reforecast, never a single number) feeds Time remaining; unresolved alerts, most urgent first, feed Decision needed and Risk. Pass `--history N` to also see the last N recorded actions (who did what, and when) when the user asks how the project got here; leave it off for the default view.
