---
name: verify
description: Confirm that the evidence for a piece of finished work exists and is current, and report plainly where it does not. Use only when the user explicitly asks whether something is verified, proven, or safe to hand over; never invoke speculatively just because a change looks complete.
---

Outcome to produce: an honest answer to "is this actually proven", naming what ran, when it ran, and what has no evidence at all, in plain language.

Verify is a thin routing surface over checks that already exist. It introduces no engine of its own, and the first thing to be clear about is what it does NOT do: it never runs a fresh check in order to make an answer look better, and it never treats the absence of evidence as a pass. Absent evidence is reported as absent.

Enter the review flow of the brotherme skill and apply every point of the definition-of-done checklist at references/definition-of-done.md. The mechanical command is `python3 "${CLAUDE_PLUGIN_ROOT}/tools/brothermode_cli.py" review <task_id>` (the packaged console script is `brothermode review`), which records the evidence and moves the task through its real state; never answer from memory of this conversation about whether it passed. A plugin install exports `${CLAUDE_PLUGIN_ROOT}` for skill and command content, so that path resolves on its own; on a clone install, where the variable is unset, run `python3 tools/brothermode_cli.py review <task_id>` instead, from the BrotherMode root (`~/.claude/skills/brothermode`). Either way, run it from the user's project folder so it reads and writes that project's own records.

The evidence a verification reads is assembled by `tools/bm_project.py deliver`, which builds the delivery packet. Verify's job is to confirm that packet's evidence exists and is current for the work in front of it, never to generate new evidence of its own. Evidence recorded before the last edit is stale, and stale evidence is reported as stale rather than counted.

v3 note: this skill introduces no new command, no new store table, and no new check beyond what review and deliver already run. It is the name the public six-command surface uses for the acceptance question, and it routes to the same flow `review` has always used; `review` remains the engine underneath and keeps working exactly as it does today. Side-effect classification, matching `review`'s own: the mechanical command writes project state, so model auto-invocation stays RESTRICTED and the description above narrows the trigger to an explicit ask, rather than adding a frontmatter field, because Claude Code's skill frontmatter offers only a boolean (`disable-model-invocation`), not a three-state control.
