# Wastage and errors, session 02f14e48, 2026-08-02

Status: CURRENT. Written at the founder's explicit instruction: record the
wastage and the errors, and do not repeat them. Everything below is this
session's own failure, quantified where a number exists. It is kept in the
repository rather than in a private note because a failure nobody can read is
a failure that gets repeated.

## The one that repeated in the same session, so it goes first

**Structured-output caps set too tight, twice, costing four agents.**

Two multi-agent runs were launched with a shared output schema whose string and
array limits were smaller than the findings the agents actually had.

| Run | Agents | Completed | Lost to the cap |
|---|---|---|---|
| repo-professional-audit | 21 | 19 | 2 |
| closure-baseline | 8 | 6 | 2 |

The second run then failed outright, because one agent's failure propagated
before the synthesis step. Recovering it required raising the caps and
resuming, and raising a **shared** schema changes the cache key for **every**
agent, so the resume re-ran work that had already succeeded. First run alone
was 1,305,154 subagent tokens and 419 tool calls.

Three separate mistakes stacked here, and each has its own correction:

1. Caps were guessed rather than sized against the work. One agent returned
   exactly 40 entries against a 40-item limit, which is the shape of truncation
   pressure, not of a complete answer.
2. A single agent's schema failure was allowed to kill an eight-agent run.
3. The fix was applied to the shared schema instead of to the one failing
   agent, converting a targeted repair into a full re-run.

**Corrections adopted:** size caps generously from the start, since an unused
allowance costs nothing and a tight one costs the whole answer; give a failing
agent its own relaxed schema rather than editing the shared one on resume; and
where a synthesis step depends on a fan-out, let a single agent's failure
degrade the result instead of destroying the run.

## Gate runs killed by load, twice

Two full-suite runs ended in `EXIT=143`, which is SIGTERM, not a test failure.
Both were started while a large agent fleet was still running, at load averages
around 13 to 15. Roughly ten minutes of suite time produced nothing usable, and
the second one briefly looked like a red gate until the exit code was read.

**Correction adopted:** before starting a suite, check both the suite lock and
the machine, not just the lock. A fleet in flight is load in flight. This
project already learned the load lesson twice in its own records; this session
made it a third time, which is why it is written here rather than assumed.

## A fix shipped on a premise that was false

Commit `fb405cc` added `.brothermode/` to `.gitignore`, on the claim that any
user was one `git add -A` from committing their own store. Every fact cited in
it was true. The conclusion was not: `docs/ba/REQUIREMENTS.md` R-06 requires
`init` to write `.git/info/exclude` without touching the founder's own
`.gitignore`, and `tools/bm_store.py:3460-3497` implements exactly that, so the
exposure does not exist. Reverted as `8a25f7c`.

It was caught by an adversarial review of my own change, which is the mechanism
working. It should not have needed catching.

**Correction adopted:** before fixing something that looks obviously broken,
grep the requirements and design records for whether it is deliberate. A true
fact with a wrong consequence bolted on is still a wrong finding.

## A false alarm reached the founder's phone

Three sessions independently concluded the computer-use lock was orphaned, and
a notification went to the founder telling him he was blocked on something that
was blocking nobody. The lock was held by a live session the whole time, and
the premise that eliminated it came from that session's own probe rather than
from its own grant receipt.

**Correction adopted, and it is the sharpest one of the day:** when eliminating
yourself as the holder of a shared resource, cite the receipt in your own
transcript, not a probe of the resource. A refusal is one sample at one instant;
a grant is a recorded fact. Elimination reasoning is only as sound as its
weakest input, and it fails silently because every step looks valid.

## A claim to the founder that was true but incomplete

I reported that the release branch had fixed the broken public install command.
It had fixed the unresolvable tag. It had not fixed that the tag it pins,
`v2.0.0-rc.9`, contains no `skills/`, no `commands/` and no `.claude-plugin/`,
so the recommended path installs a product without the layer the README sells.
Corrected in the same session once `git ls-tree` was actually run against the
tag's tree.

**Correction adopted:** verifying that a tag resolves is not verifying that its
tree contains what the documentation promises. Check the contents, not the ref.

## Smaller waste, recorded for completeness

- One gate run wasted because untracked dated drafts sat in the working tree
  and the documentation suite correctly refused them. The suite scans the
  working tree, not only tracked files; `git status` before a gate would have
  caught it. The drafts were preserved to the handovers directory, not deleted.
- One blocked attempt at `gh pr merge`, tried before establishing whether an
  irreversible public action was permitted. The block was correct and was not
  routed around.
- This document's own ledger file, `references/mistakes.md`, opens by claiming
  it was extracted verbatim from `SKILL.md` section 13. `SKILL.md` has no
  section 13 today. Found while writing this; corrected in the same change.

## What did not go wrong, recorded so the ledger is not only negative

The consent-before-persistence probe passed on its first hostile run. The
enforcement findings, the CI root cause, and the install-tag defect were each
reproduced before being reported, in both directions where a fix was claimed.
No work was lost: every branch deletion was proven contained first, every
worktree confirmed clean first, and every displaced file was preserved to a
durable path rather than removed.
