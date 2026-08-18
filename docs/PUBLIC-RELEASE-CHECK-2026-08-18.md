Status: CURRENT.

# The public release check, 2026-08-18

What was examined before this repository goes public again, what was found,
what was changed, and what was deliberately left alone. Every claim below
names the command that produced it, so a reader can rerun the check rather
than trust the paragraph.

This repository was public until 2026-08-17, when a client confidentiality
problem was found and it was taken private. That problem is the reason this
page exists, and the first section is about whether it is actually closed.

## 1. The confidentiality blocker is closed

The 2026-08-17 pack (docs/handover/2026-08-17-adopter-feedback-finish/)
recorded a scrub of the working tree and then said the important part
plainly: GIT HISTORY WAS NOT FIXED, roughly 196 occurrences of the adopter
team's real name remained readable with git log on a public clone, and
closing it was the owner's decision. That was TASK 0, and it blocked every
public push.

TASK 0 HAS SINCE BEEN EXECUTED. The evidence is a history rewrite, not a
promise:

    git cat-file -t 38c859b     # the scrub commit named in the close report
    -> not present

Twenty six of the twenty nine commit SHAs cited in older close reports are
unreachable in the current history; only the three most recent, written after
the rewrite, resolve. A rewrite is the only thing that invalidates SHAs that
way. The substitution artifact it left behind is visible in blobs dated
before the fix was written:

    git show 2f03d6c:CLAUDE.md | grep "Bitbucket carries"
    -> "Bitbucket carries the the adopter team team"

which is what replacing a name inside "the NAME team" produces. Checked
against the whole history rather than against the tree:

    git log --all -p | grep -oE "\bthe [A-Z][A-Za-z&.-]{2,20} team\b"
    -> no matches

Roles, not names, are what survives: the analyst lead, the engineering lead,
the QA lead, the testers. A scan of the full history for personal names beside
reporting verbs returns the owner's own name and nothing else.

## 2. No credential is in the tree or in the history

    git grep -nE "(ghp_|gho_|ghs_|github_pat_)[A-Za-z0-9]{20,}|sk-(ant-)?[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|BEGIN (RSA|OPENSSH|EC|PGP) PRIVATE KEY|xox[baprs]-[A-Za-z0-9-]{10,}"
    git log --all -p | grep -E "^\+.*(same pattern)"

Every hit in both is a documented fake: AKIAIOSFODNN7EXAMPLE is AWS's own
example key, and sk-ant-api03-ABCDEFGHIJKLMNOP and
ghp_abcdefghijklmnopqrstuvwxyz012345 are redaction fixtures whose whole
purpose is to be caught by the redactor. scripts/allowed_signers holds a
PUBLIC key and is meant to be published: it is the half that verifies a gate
receipt, and the file says so.

## 3. What leaked, and what was changed

Three sites on the live surface carried the identity of the machine that
wrote them. All three are fixed in this change.

  scripts/local-gates.sh, the sandbox deny rule. The vault deny path
  defaulted to one operator's Obsidian vault BY NAME, which published that
  private name from a tracked file. It now reads BROTHERMODE_VAULT, and when
  no vault is declared it SAYS so in the note that reaches the receipt rather
  than substituting a generic guess. The guess would have been worse than the
  gap: it would deny a directory nobody owns while the real vault stayed
  readable, and the receipt would still have read "no vault".

  scripts/gates-when-quiet.sh, the repository loop. Two absolute paths naming
  the owner's account became $HOME-relative defaults with per repository
  overrides, matching the pattern the same file already used for its log path.

  PROJECT.md, the identity card. The canonical path and the Codex spec path
  are now written $HOME-relative, and the vault is named generically, which
  is what founder decision D-B2 (2026-08-11) already required of new writing.

Verified after the last edit:

    git grep -n "/Users/khalil" -- . ':!docs/'
    -> no matches

## 4. What was deliberately NOT changed, and why

The dated material under docs/ still contains the owner's home path on
roughly 200 files and a private vault name on 39 lines. This was left alone
on purpose, for a reason that is worth stating because it looks like an
omission:

MOST OF IT IS VERBATIM COMMAND OUTPUT. Rewriting an `ls -ld` transcript so it
prints a path that was never printed falsifies the evidence, and this project
treats dated evidence as evidence. Worse, it would buy nothing: those same
bytes are in git history, so a public clone reads them either way. A scrub of
the tree would produce the APPEARANCE of cleanliness without the fact of it,
which is the exact failure mode this repository is built to refuse.

The material is also low consequence. It reveals a macOS account name that
the repository's own ownership already publishes, and a folder name. It is
not a credential and it is not a third party's information.

If the owner wants it gone, the honest instrument is a second history rewrite
covering both, not an edit to the working tree. That is a founder decision
and it is recorded here as open rather than quietly skipped.

## 5. What a machine may not do, and what is still owed

THE VISIBILITY FLIP IS NOT A MACHINE ACTION. No tool available to a session
can change repository visibility, and it is the kind of one way, outward
facing change that belongs to a person. The steps are in
docs/RELEASE.md's spirit and are three clicks: Settings, then the Danger Zone,
then Change visibility to public.

STILL OWED, found by this check and NOT fixed here because it cannot be:
v3.3.0, the tag the project tells installers to use
(`python3 tools/bm_project_facts.py --field install_target_tag`), ships a
CHECKSUMS.sha256 that mis-describes two of its own files:

    docs/plan/COMMAND-CENTER.html
    docs/plan/FINALIZATION-ROADMAP-2026-08-15.md

    git show v3.3.0:CHECKSUMS.sha256 | grep -F "  docs/plan/COMMAND-CENTER.html"
    -> ae7c385d...
    git cat-file -p $(git ls-tree -r v3.3.0 -- docs/plan/COMMAND-CENTER.html | awk '{print $3}') | sha256sum
    -> 967ac195...

scripts/verify-install.sh makes exactly the guarantee those hashes break, so
an installer of v3.3.0 who runs the integrity check gets a failure on a
correct install. The current tree's manifest is correct; only the tag is
wrong, and a tag is immutable, so the fix is a new release. Cutting one is
FOUNDER-GATED by docs/RELEASE.md and a machine must refuse it.

This defect was invisible to every session before this one because the
check that finds it, TestReleaseTruth's manifest test in tools/test_bm_docs.py,
SKIPS when the tag is absent, and a shallow clone has no tags. It was found
by fetching the full history in order to audit it.

## 6. The gate that keeps this closed

tools/test_bm_docs.py gained
TestThePublicSurfaceCarriesNoOperatorIdentity, two rules over every tracked
file except the dated material under docs/ and CHANGELOG.md:

  an absolute home path may name only a placeholder account, never a real one
  a vault is reached through BROTHERMODE_VAULT or written as a placeholder,
  never spelled out

Both were proven by reintroducing the exact leak each was written for and
watching the suite go red, then removing it and watching it go green. The
vault rule FAILED that proof on its first draft: it excluded whitespace, and
the name that leaked contains a space, so it missed the very string it
existed to catch. That is recorded here because the first draft would have
passed review and protected nothing.

The rules name no vault and no account. Pinning the leaked name in the check
meant to retire it would publish it again from the check itself.

## 7. A second history rewrite landed while this check was running

Recorded because it changes what a tag name means, and the next session will
otherwise be confused by it.

Between the start of this check and its end, origin/main was rewritten and
force pushed again. Measured, not inferred:

    git rev-list --left-right --count origin/main...HEAD
    -> 638   638

Six hundred and thirty eight commits on each side, every SHA different, one
file of content different. A full rewrite, not a merge. The single content
change is the removal of

    docs/program/absolute-lead/evidence/BENCH/20260807T140548Z-v2/H7/B/transcript.txt

from every commit. That file is a raw agent session transcript in JSONL:
internal message and hook identifiers, rate limit events, thinking token
counts. Purging it before publication is the right call.

THE CONSEQUENCE FOR TAGS, which is the part that bites. Release tags were
re-pointed by the rewrite, so a tag name no longer identifies one commit
across clones:

    local  v3.3.0 (fetched before the rewrite) -> 7736faf
    origin v3.3.0 (fetched after)              -> c035390

Same subject, same author date, different SHA. Anyone holding a clone from
before the rewrite has a v3.3.0 that no longer exists on the remote. On a
public repository that is worse than untidy, because docs/RELEASE.md sells
tagged releases as immutable and a checksum manifest as the thing that proves
an install. `git fetch --tags` alone does NOT repair it: it refuses the
re-pointed tags with "would clobber existing tag" and leaves the stale ones in
place. `git fetch --tags --force` is what actually re-points them.

The manifest defect in section 5 was re-verified against ORIGIN's v3.3.0
after this was discovered, not just the local one. It reproduces identically
on both, so that finding stands whichever v3.3.0 a reader has.

This work was rebased onto the rewritten origin/main rather than pushed from
the old base. Pushing the old base would have restored all 638 superseded
commits to the remote, and with them the transcript the rewrite had just
removed.
