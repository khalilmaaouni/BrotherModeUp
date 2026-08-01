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
6. Pinned clone only, right after the checkout: run `python3 scripts/doctor.py`. Its CHECKSUMS.sha256 self-check is what catches a half-finished update, a checkout that stopped partway or a working tree with local edits left over from before, by naming the exact file that does not match what was released. A plugin install has no checkout step to verify this way; `/plugin update` verifies its own files.
7. Then re-run `python3 scripts/doctor.py` once more, the same way you would right after a fresh install: every one of its ten checks should read PASS or SKIP (SKIP is not a failure, it means that check found nothing to look at). If any check reads FAIL, follow the one-sentence fix it prints before doing anything else.
8. Rollback, if a FAIL will not clear: `git checkout <the tag you were on before>` inside the skill folder, then run `python3 scripts/doctor.py` again to confirm the rollback itself is healthy.
9. Give one recommended next action, and state any time cost as a range, never a promise, in plain words a non-engineer would follow.
10. Say plainly: updating never touches the user's project data or records; it only replaces the BrotherME files themselves.
