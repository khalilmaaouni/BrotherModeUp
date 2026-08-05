---
description: Start a project with a short guided conversation that ends in one clear project brief
argument-hint: <what you want to build or achieve>
---

The user wants to start a project. Their goal, in their own words: $ARGUMENTS

Outcome to produce: one clear project brief (the Project Canvas) and one recommended first decision, in plain language, with a realistic time and cost range.

Enter the guided kickoff flow of the brotherme skill. Follow the kickoff instructions at references/kickoff.md: size up the goal, ask only the questions whose answers change the scope, one decision at a time with a recommended option first.

FIRST RUN IN A PROJECT, do this before anything mechanical: a brand new project folder has no records yet, and `bm_project.py start` REFUSES rather than creating them, with a message naming `bm_store.py init`. That refusal is correct engine behaviour and it is the wrong thing for a beginner's first minute, so never let them see it. Run `python3 tools/bm_store.py init` in the user's project folder yourself, once, before the first `bm_project.py` command, and say one plain sentence about what it did ("set this folder up to remember your project"). If it is already set up, the command says so and nothing is harmed. Same install-path rule as below.

RECORD THE OUTCOME FIRST, once the user has said in their own words what they want: run `python3 tools/bm_lead.py outcome --project-id <id> --set "<their words>"` (the packaged console script is `bm-lead outcome`), then continue the guided kickoff. There is one command that records what the user is trying to achieve, and this is it, so the goal the status view reads back later is the goal they actually stated rather than a paraphrase gathered twice. Same install-path rule as below.

Once the goal, scope, and first decision are settled, run the mechanical command `python3 tools/bm_project.py start` with the gathered details: it creates the project record in that project's own records and regenerates CANVAS.md from those rows. That path is relative to the BrotherME install folder, not the user's project folder: a plugin install runs it from the plugin's own root, a clone install runs it from `~/.claude/skills/brothermode`; prefix that install path onto the command, and still run it from the user's project folder so it reads and writes that project's own records. Never fill CANVAS.md by hand and never answer from memory of this conversation about what the project record holds; the command's own output is the only source of truth. If the goal above is empty, ask for it in one sentence before anything else.
