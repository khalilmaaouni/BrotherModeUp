---
description: Check the installed version against the newest release and explain how to update, in plain language
---

Outcome to produce: tell the user their installed version, the newest available version, whether they match, and the exact update steps for their install path.

1. Read the VERSION file at the BrotherME root (the folder this command's plugin or skill is installed in). That is the installed version.
2. Check the newest release tag: `git ls-remote --tags https://github.com/khalilmaaouni/BrotherModeUp.git`. If the network refuses, say plainly the check could not run, and do not guess a version.
3. Tell the user, in plain words: their installed version, the newest version, and whether they match.
4. If they already match, say so and stop; no update steps needed.
5. If an update is available, give the exact steps for their own install path only:
   - Plugin install: `/plugin marketplace update brotherme-marketplace`, then `/plugin update brotherme`, then restart Claude Code.
   - Pinned clone: inside the skill folder, run `git fetch --tags`, then `git checkout <newest tag>` (the exact commands are in docs/RELEASE.md).
6. Give one recommended next action, and state any time cost as a range, never a promise, in plain words a non-engineer would follow.
7. Say plainly: updating never touches the user's project data or records; it only replaces the BrotherME files themselves.
