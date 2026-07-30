# Release process

Written 2026-07-26, the day the first version was cut. Read this before cutting
any release, and read it especially if you are a machine (an AI coding
session) about to run these steps: three of them are marked FOUNDER-GATED and
a machine must refuse to perform them.

## The problem this solves

The install instruction in `README.md` and `docs/SETUP.md` clones a git
branch into `~/.claude/skills/brothermode`, and the code in that directory
then runs automatically on every Claude Code session through five hooks
(`SessionStart`, `SessionEnd`, `Stop`, `PreCompact`, `PreToolUse`; `python3
tools/bm_project_facts.py --field hook_events` prints the live list). The
original external audit of this project named that combination, a moving branch
feeding
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
(problem 2).

CORRECTED 2026-07-27. The paragraph here used to say no version had ever been
tagged and continuous integration had never executed. Both statements were false
by the time anyone read them: `v2.0.0-rc.1` was tagged on 2026-07-26 and CI has
run more than twenty times. The instruction attached to the old paragraph, "do
not let a later, cleaner-sounding paragraph replace it", was well meant and
became a defence of a stale fact. Prefer a statement that names its date and its
evidence over one that asks to be preserved.

## The version scheme

`VERSION`, one line, holds the current semantic version. Read it rather than
trusting a number typed into this paragraph:

```bash
cat VERSION
python3 tools/bm_project_facts.py --field release_tag
```

The current candidate is `2.0.0-rc.5`, cut 2026-07-31 at the close of the
first-rank execution loops 0 through 5 (`CHANGELOG.md` has the entries: release
truth, receipt-gated state changes, bounded gate manifests, mandatory work
identity, privacy hardening). At the moment this page was written the TAG
`v2.0.0-rc.5` was not yet created: this project creates release tags through
the GitHub Desktop app (a command-line tag does not push from Desktop,
confirmed empirically), so the tag is cut by the founder immediately after the
release-cut commit lands, and the release-truth suite holds this page honest
in both directions: its tag tests SKIP with a stated reason while the tag does
not exist and become mandatory the moment it does.

`2.0.0-rc.4` before it is superseded, cut 2026-07-29 when the four parallel
work lanes were merged back into `v2`.

CORRECTED 2026-07-30, kept for the record. The paragraph about rc.4 used to say
the TAG `v2.0.0-rc.4` did not exist yet and that cutting it was still pending.
That stopped being true the moment the founder cut it: `git tag -l` lists it,
`git cat-file -t v2.0.0-rc.4` reports `tag` (annotated, not lightweight, as
the steps below require), and it points at the exact commit that set `VERSION`
to `2.0.0-rc.4`. HEAD then moved twelve commits past that tag, on purpose:
this project lands a wave of work on top of a cut tag before the next one is
cut, so a moving HEAD is not a sign the tag itself is stale. `git describe
--tags` shows where HEAD stands relative to it. `2.0.0-rc.3` before it is
superseded, not withdrawn, as is `v2.0.0-rc.2`. `v2.0.0-rc.1` IS withdrawn;
see the section below for why that distinction matters.

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
  project (only test suites and adversarial review), and one confirmed defect is
  still open (a refused `adopt` attempt still writes a permanent handover block
  into `STATE.md`). Continuous integration now passes on all three platforms and
  both supported Python versions, including the recovery suite, which is a
  change from rc.1 rather than a claim about it.
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

Promoting the current candidate to a plain `2.0.0` later should require, at
minimum, one real project run through the V2 store for at least a week. Two
conditions that used to stand here are now MET and struck rather than left
looking unfinished: green CI on all three platforms and both Python versions
with the recovery suite included, and the `adopt` defect, closed 2026-07-28
(`docs/NOT-FINALIZED.md` item 5). The dogfood window is the one that remains.
Until it closes, do not describe this project as `2.0.0` anywhere.

## How a user pins a version instead of tracking a branch

Tags exist now, so this is the install instruction, not a future one:

```bash
git clone --branch v2.0.0-rc.5 --depth 1 https://github.com/khalilmaaouni/BrotherModeUp.git ~/.claude/skills/brothermode
```

`--branch v2.0.0-rc.5` checks out that exact tag, not a moving branch head. It
is the current candidate; `python3 tools/bm_project_facts.py --field
release_tag` prints the tag matching whatever tree you are reading.
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
5. **FOUNDER-GATED: create the git tag.** `git tag -a v$(cat VERSION) -m "..."`
   (annotated, not lightweight, so the tag carries its own message and
   date). A machine must not run this command on its own initiative; it is
   the moment a version becomes a permanent, citable release.
6. **FOUNDER-GATED: push the tag.** `git push origin v$(cat VERSION)`. Pushing a
   tag is the moment this becomes visible and clonable by anyone; the
   founder decides when that happens, never a machine acting alone.
7. **FOUNDER-GATED: publish anything else** (a GitHub Release entry
   attaching `CHECKSUMS.sha256` as a release asset, an announcement, a
   website update). Same reasoning as steps 5 and 6: irreversible,
   human-facing, and the founder's call.

## v2.0.0-rc.1 is WITHDRAWN, and why that matters more than a version number

Withdrawn 2026-07-27. Do not install it.

The tag `v2.0.0-rc.1` points at commit `7c2e0ec`, whose CI run FAILED on Windows
for a real handle leak. The branch then moved 14 commits past it while the
`VERSION` file still read `2.0.0-rc.1`. So an immutable tag and a moving branch
both claimed the same identity while containing materially different code, and
one of the two was broken on a platform this project promises to support.

That is worse than shipping a bug. A version number is a promise that two people
saying "2.0.0-rc.1" are talking about the same bytes. Once that stops being true,
every other honesty guarantee in this repository is unverifiable, because there is
no way to say WHICH code a claim was ever about.

`v2.0.0-rc.2` is cut from a commit whose full matrix is green on Linux, macOS and
Windows, on both supported Python versions, with the recovery suite included.
Checksums are regenerated LAST, after every other change, so the manifest
describes exactly what the tag contains rather than what it contained partway
through preparing it.

## What has and has not happened, stated honestly

CURRENT STATE, 2026-07-31, first, because the dated entries under it are a LOG
and several of them were true only on the day they were written. `VERSION`
reads `2.0.0-rc.5` and its tag is cut by the founder through GitHub Desktop
immediately after the release-cut commit; until that moment the pinned clone
command above does not resolve, the release-truth tests SKIP with a stated
reason, and this sentence is the honest record of that window. Four earlier
tags exist (`v2.0.0-rc.1` withdrawn, `v2.0.0-rc.2` superseded, `v2.0.0-rc.3`
superseded, `v2.0.0-rc.4` superseded). CORRECTED 2026-07-30: the 2026-07-29
entry directly below said no tag had been cut for `rc.4` and that its pinned
clone would not resolve; both were true that day and stopped being true when
the founder cut that tag, which is exactly why it is dated evidence rather
than kept as today's paragraph. CI is green on three platforms as of 2026-07-27; the Windows handle
leak that failed on `rc.1` is fixed. The checksum manifest was regenerated at
the rc.4 release-cut commit, which is the exact commit the tag points at, so
it describes the tagged tree rather than an earlier one. Read the entries
below as the arc, not as today's status; `docs/KNOWN-LIMITS.md` is the live
one.

- **A release IS tagged now.** Corrected 2026-07-26: `v2.0.0-rc.1` exists on
  commit `7c2e0ec`, published as a GitHub pre-release. The clone command above
  works. Recipe note worth keeping: GitHub Desktop does not push a tag created
  outside the app, so the tag and the release were created through the GitHub
  web interface instead.
- **Continuous integration HAS executed, and it FAILED.** Corrected
  2026-07-26: this line previously said CI had never run. It has run 18 times,
  and on the tagged commit the job `store (windows-latest, 3.x)` exited 1 with
  `PermissionError: [WinError 32]` on `store.sqlite3`. Cause: database handles
  were opened and never closed. POSIX permits deleting a file that still has an
  open handle, so every macOS and Linux leg passed and the leak stayed
  invisible. Do not treat this release as green on three platforms; read
  `docs/KNOWN-LIMITS.md` for the current state.
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

## Ratified: where the business summary and the whitepaper live

Founder-ratified 2026-07-30, settled, and not to be reopened. This is not a
release step; it is recorded here because this is the release identity work
that surfaced it, and this file is this project's home for a decision stated
once rather than re-argued in every document that touches it.

`tools/bm_docs.py` generates a numbered documentation folder from this
project's own store, and two of its pages sit outside the literal tier table
its own design spec describes:

- `BA-SUMMARY.md` stays at tier 2, `10-business/BA-SUMMARY.md`: the business
  narrative belongs beside `REQUIREMENTS.md`, which is also tier 2.
- `WHITEPAPER.md` stays at tier 3, `20-technical/WHITEPAPER.md`: the long-form
  account of why the project is built this way sits at the deepest tier,
  alongside `CODE-MAP.md` and `PROCESS-DIAGRAMS.md`.

Until this loop, that placement was recorded only as a code comment inside
`tools/bm_docs.py`, beside its `FILES` tuple. `tools/bm_docs.py` is outside
this document's fence, so its own comment still needs to change to point here
rather than re-deriving the reasoning; that edit belongs to whoever owns that
file next.
