# Release process

Written 2026-07-26, the day the first version was cut. Read this before cutting
any release, and read it especially if you are a machine (an AI coding
session) about to run these steps: three of them are marked FOUNDER-GATED and
a machine must refuse to perform them.

## The problem this solves

The install instruction in `README.md` and `docs/SETUP.md` clones a git
branch into `~/.claude/skills/brothermode`, and the code in that directory
then runs automatically on every Claude Code session through four hooks
(`SessionStart`, `SessionEnd`, `Stop`, `PreCompact`). The original external
audit of this project named that combination, a moving branch feeding
auto-run code, as the weakest link in the whole design. Two problems live
inside that one sentence:

1. **"Moving branch" means the code you run today can be different from the
   code you reviewed yesterday**, with no signal that anything changed. A
   `git pull` silently replaces what is on disk.
2. **Nobody could answer "what exactly did I install"** without reading
   every file by hand, because there was no manifest and no release to point
   at.

This document is the discipline that answers both: tagged, immutable
releases (problem 1) with a checksum manifest a user can check against
(problem 2). It does not perform a release. As of this writing, no version of
this project has ever been tagged, and continuous integration has never
executed against this content (`docs/KNOWN-LIMITS.md`). Say that to whoever
reads this next; do not let a later, cleaner-sounding paragraph replace it.

## The version scheme

`VERSION`, one line, holds the current semantic version:
`2.0.0-rc.1`.

Reasoning, stated plainly because a version number is a claim and this one
should be checked rather than trusted:

- **`2.0.0`, not `1.x`.** V1's storage was a JSON registry (`bm_registry.py`);
  Phase 3, landed the same day this file was written, replaced it with a
  SQLite-backed store (`tools/bm_store.py`) and deleted the old registry
  outright, with no compatibility shim. That is a breaking change to the
  project's own storage format, which is exactly what a major version bump
  communicates under semver. Calling this `1.x` would undersell what changed
  underneath every command.
- **`-rc.1`, not a bare `2.0.0`.** Semver reserves the right to ship a
  pre-release identifier precisely for "believed feature-complete, not yet
  proven," and every fact needed to justify that sits in
  `docs/KNOWN-LIMITS.md` as of today: the engine has never run on a real
  project (only test suites and adversarial review), continuous integration
  has never executed even once, Windows behavior is proxied rather than
  run on real Windows, and one confirmed defect is still open (a refused
  `adopt` attempt still writes a permanent handover block into `STATE.md`).
  Shipping `2.0.0` plain would assert a confidence this project does not
  have yet. `2.0.0-rc.1` sorts before `2.0.0` under semver precedence rules,
  which is the honest ordering: this is a candidate for `2.0.0`, not `2.0.0`
  itself, until it has survived contact with a real project and a real CI
  run.
- **Why not `0.x`.** `0.x` conventionally signals "anything can break
  without notice, including the public interface." This project's public
  interface (the CLI commands, the hook contract, the vault layout) is
  intentionally more stable than that going forward; the uncertainty here is
  about proof, not about the interface being provisional. A release
  candidate says "we believe this is right and are asking reality to
  confirm it," which matches the actual situation better than `0.x` would.

Promoting `2.0.0-rc.1` to a plain `2.0.0` later should require, at minimum:
one real project run through the V2 store for at least a week, one green CI
run on every platform in the matrix, and the still-open `adopt` defect
closed. Until then, do not describe this project as `2.0.0` anywhere.

## How a user pins a version instead of tracking a branch

Once a tag exists (it does not yet; see "What has and has not happened" below),
the install instruction becomes:

```bash
git clone --branch v2.0.0-rc.1 --depth 1 https://github.com/khalilmaaouni/BrotherModeUp.git ~/.claude/skills/brothermode
```

`--branch v2.0.0-rc.1` checks out that exact tag, not a moving branch head.
`--depth 1` is optional (a shallow clone of just that tag), included because
most users have no reason to carry this project's full history into their
skills directory.

To move to a later release deliberately, rather than by accident:

```bash
cd ~/.claude/skills/brothermode
git fetch --tags
git checkout v2.0.1   # or whatever the next tag is
```

This never runs on its own. Nothing in this project auto-updates itself; an
update is always a command the user (or the user's own script) chooses to
run.

## How a user verifies what they installed

After cloning a tag, verify the files on disk match what that tag published:

```bash
cd ~/.claude/skills/brothermode
sh scripts/verify-install.sh
```

This checks the current directory's files against `CHECKSUMS.sha256`
(published in the repository at that tag; see the release steps below) in
BOTH directions: it names any file the manifest lists that is missing or does
not match on disk, AND any file present on disk that the manifest does not
list, then exits nonzero if anything differs either way. That second
direction was added 2026-07-26 (final-blockers spec, BLOCKER 2) after an
external check reproduced the exact gap it closes: a planted file
(`tools/bm_helper.py` containing a shell-out backdoor) was invisible to a
version of this check that only ever asked "does every NAMED file match",
and it reported PASSED at exit 0 with the backdoor still present. An ADDED
file is exactly the shape that matters for code that runs automatically on
every session, which is why both directions are checked now, not one. A
clean pass reads:

```
verify-install: N file(s) match, 0 mismatched, 0 missing, 0 extra (present on disk, absent from the manifest)
verify-install: PASSED. Every file the manifest names matches on disk,
verify-install: and no file exists on disk that the manifest does not name.
```

Read the last lines the script prints, always: matching the manifest proves
your files are what the manifest says, not that the manifest itself is
trustworthy. Fetch the manifest from a channel you trust (the tag itself, or
a signed release asset), never from the same place a compromised copy of the
code would also come from.

## Cutting a release: the exact steps

Steps 1 through 4 are things a maintainer or a machine may do. Steps 5
through 7 are marked FOUNDER-GATED: an automated agent (a Claude Code
session, a CI job acting on its own) must refuse to perform them and hand
control back to the human founder instead. This project has never been
tagged, so this is also, honestly, an untested runbook; treat the first real
run of it as a test of the runbook, not just of the code.

1. **Confirm the working tree is clean and every test suite is green.** Run
   the commands `README.md`'s own gate section names, not a guess:
   `python3 tools/test_bm.py`, `python3 tools/test_bm_store.py`, and
   `python3 tools/test_bm_autosave.py` if that file is exercised separately.
   Do not proceed on a red suite.
2. **Update `VERSION`** to the new version, following the scheme above, and
   **add a `CHANGELOG.md` entry** at the top of the file (newest first, the
   existing convention) describing what changed for a user: what is new,
   what broke, what is still unproven. Keep it consistent with
   `docs/KNOWN-LIMITS.md`; do not let a changelog entry claim more certainty
   than the limits file admits.
3. **Generate the checksum manifest**, from the repository root, after steps
   1 and 2 are committed (the manifest must describe the exact tree being
   released, not an earlier one):
   ```bash
   sh scripts/checksums.sh CHECKSUMS.sha256
   ```
   Commit `CHECKSUMS.sha256` itself in the same commit as the version bump,
   so the tag below covers the manifest along with the code it describes.
4. **Run `sh scripts/verify-install.sh` against the repository root** as a
   final sanity check before tagging: it should report every tracked file
   matching the manifest you just committed. This is the last automatic
   step; everything after this line is founder-gated.
5. **FOUNDER-GATED: create the git tag.** `git tag -a v2.0.0-rc.1 -m "..."`
   (annotated, not lightweight, so the tag carries its own message and
   date). A machine must not run this command on its own initiative; it is
   the moment a version becomes a permanent, citable release.
6. **FOUNDER-GATED: push the tag.** `git push origin v2.0.0-rc.1`. Pushing a
   tag is the moment this becomes visible and clonable by anyone; the
   founder decides when that happens, never a machine acting alone.
7. **FOUNDER-GATED: publish anything else** (a GitHub Release entry
   attaching `CHECKSUMS.sha256` as a release asset, an announcement, a
   website update). Same reasoning as steps 5 and 6: irreversible,
   human-facing, and the founder's call.

## What has and has not happened, stated honestly

- **No release has ever been tagged.** `git tag -l` in this repository
  returns nothing as of this writing. The `--branch v2.0.0-rc.1` clone
  command above will not work until step 5 actually runs.
- **Continuous integration has never executed.** `.github/workflows/tests.yml`
  is configured (three platforms, two Python versions for the store suite)
  but nothing has been pushed to trigger it yet, per `docs/KNOWN-LIMITS.md`.
  The first push that triggers it is also the first real test of that
  configuration, and it may fail in ways only a real run can surface.
- **`scripts/checksums.sh` and `scripts/verify-install.sh` are new as of this
  same day** and have been exercised against this repository's own working
  tree (a passing run, a deliberately tampered copy that correctly reported
  the tampering, a planted extra file that correctly reported PASSED at exit
  0 until the 2026-07-26 fix, and now correctly fails and names it, and a
  git-tracked filename containing a quote and a non-ASCII character, which
  the same fix now hashes instead of silently dropping) but never against an
  actual tagged release, because none exists yet.
- **This runbook itself is unproven.** These seven steps are written down
  correctly to the best of the author's knowledge, but no one has followed
  them start to finish. The first real release is also the first test of
  this document; if a step is wrong, fix this file in the same change that
  discovers the problem, rather than silently working around it once.
