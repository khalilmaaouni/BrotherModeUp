Status: CURRENT as of 2026-08-17. Written by the session that found it.
Line numbers were correct on 2026-08-17 and may move.
NOTE: the README table in this directory documents only the original sixteen
records and was not extended. Deliberate, not an oversight: the README says a
future session reads this DIRECTORY, and the file names carry their own subject.

# M24: three claim controls, none able to reach a verdict, all reading as green

## What happened

One line of code needed to be added to `tools/bm_effects.py`. It took four
refusals from three registries to get there, and each refused for a different
wrong reason.

1. The sibling repository's single-writer hook reported 35 live fence lines with
   no readable `files:` scope. The received explanation, written in
   `docs/plan/ADOPTER-TEAM-PROBLEMS-AND-SOLUTIONS-2026-08-15.md` as finding H9,
   was that the fence registry had rotted and the fix was to clear the stale
   July lines. That explanation is WRONG, and acting on it would have deleted
   legitimate prose from a state file.
2. `tools/bm_stall.py sweep` reported `0 finding(s). No active fence,
   provisional record, or claim looks stale or contradictory right now.` while a
   fence held by a session absent from the live session list was actively
   blocking a write, and reported the same 0 after that fence was cleared. The
   sweep is blind to fence ownership in both directions.
3. The `.sbe` task registry in each repository held writer claims from sessions
   that were gone: 17 in the sibling from one session, and one here claiming
   `tools`, `docs` and `skills`, three entire directories. The tool states the
   cause in its own output: `Expiry is informational: nothing here deletes on a
   clock.`
4. The two registries cannot see each other. The fence hook reads `STATE.md` and
   allowed a write the `.sbe` registry refused; the `.sbe` authority guard
   refused an edit to `STATE.md` that the fence hook allowed.

## How it was found

By needing to write one line, and by being refused. Not by a test, not by a
sweep, and not by reading either registry. The drift check refused an attempt to
answer the fence question by searching `STATE.md` directly and insisted the
control be asked instead. Asking the control produced the real diagnosis; the
text search would have listed 35 live fences and they would have been believed,
which is the same trap recorded at PS 818 for this same finding.

## The evidence

The matcher, read off its owning module at `tools/sbe_score.py:449`, which
`tools/sbe_fence_hook.py:250` deliberately borrows rather than re-typing:

    return (s.startswith(("- ", "* ")) and "agent" in s.lower()
            and "LANDED" not in s and "ADOPTED" not in s)

A bare substring test on the word agent. So each of these ordinary bullets is
counted as a live writer claim and then reported as unenforceable:

    - ORCHESTRATOR VERIFIES. The agent does not commit and does not push.
    - STALL: no file anywhere in the tree, including agent worktrees, changed
    - INTEGRATION (orchestrator, per design/phase-0/INTEGRATION.md): four lane
    - Tasks 3 and 4: commits 0652ec7 and 080fc30 on branch worktree-agent-a387

The last qualifies only because a BRANCH NAME contains the word.

The registry was not degrading. Pointing the hook itself at three of the
`STATE.md.bak-*` backups, and reading the control's own summary line rather than
counting its output, gives a monotonically IMPROVING series:

    backup 2026-08-11   0 enforceable, "every write would be ALLOWED"
    backup 2026-08-15   1 enforceable
    backup 2026-08-17   4 enforceable
    current             5 enforceable

That also refutes a plausible second hypothesis, offered by a peer session, that
the brothermode store's rewrite of `STATE.md` that morning broke the scopes. It
did not. The lines were already unreadable on 2026-08-11.

The severe part is not noise. When the count of genuinely readable fences reaches
zero, `read_fences` raises and the hook FAILS OPEN, which is the 2026-08-11 line
above: every write allowed, announced in a message that reads like a warning
about fences rather than about a matcher.

## How it was fixed

The claims were cleared on the founder's decision of 2026-08-17, each through
`sbe task close --force --who --why`, which the tool permanently marks FORCED and
never reads as clean, and the fence was marked ADOPTED with a note stating that
the CLAIM was cleared and the work was not done. Pre-change snapshots of both
registries are at `~/Documents/BrotherArchive/claim-registries-2026-08-17`.

THE MATCHER WAS NOT FIXED, deliberately, and this is the open half. Narrowing it
is a safety tradeoff rather than a bug fix: the comment at
`tools/sbe_fence_hook.py:250` records that the BROADER of the shipped parses was
chosen on purpose, because a missed fence is an unprotected file, and the project
ships three divergent copies of the rule (one in `sbe_score.py`, two in
`sbe_telemetry.py` accepting only `- `). It goes to a design pass, then to the
founder. Filed as open.

Neither the stall sweep's blindness nor the missing expiry was fixed either.

## The rule it produces

A claim registry needs three things or it degrades into a wall: a claim must name
a scope the control can READ, a claim must EXPIRE or at least report its owner as
gone, and where two registries govern one tree, each must see the other's claims.
A registry with none of the three does not fail loudly. It accumulates, blocks
honest work, and reads as protection.

The narrower rule that produced every correct step here: ask the control, never
search the control's file. A substring matcher and a hand-written search can
agree with each other while both are wrong about what the tool enforces.

THE PATTERN IS NOT CONFINED TO THIS ONE MATCHER, and that is worth more than the
finding itself. While this file was being written, the drift check on this machine
refused the Write because the sentence explaining the lesson CONTAINED the words
it watches for. A substring matcher flagged prose that merely mentions its
subject, which is exactly what `is_live_fence` does when it counts a branch named
`worktree-agent-a387` as a writer claim. Two independent controls, written by
different hands for different jobs, share one defect: they match on a word
appearing rather than on a structure being declared. Any future control that
decides something important from a substring should be assumed to have this bug
until someone feeds it prose that merely talks about the subject.

## Two more instances, found after this file was first written

The prediction in the section above was that any control deciding something
important from a substring should be assumed to have this bug. It took under an
hour to find two more, both while closing the session that wrote the prediction.

THIRD INSTANCE, the handover pack's secret scan. It refused to build the zip,
naming four lines. All four were ordinary prose: three said "a fix pass was
dispatched" and the fourth said "no credential was touched" in a safety
statement. The scan matches the words `pass` and `credential` appearing, so a
sentence REPORTING that no credentials were touched is flagged as containing one.
The recovery the tool offers is to edit the wording, which is what was done, and
that is the right recovery: the scan is fail-closed on purpose and a fail-closed
scan with false positives is far better than the reverse. But note what it costs:
a session under time pressure learns to rephrase rather than to look, and the
next real secret arrives dressed as a false positive.

FOURTH INSTANCE, and this one is the registry defect rather than the substring
one, found inside the closing control itself. `bm_handover.py verify-close`
returned NO-DATA at exit 2, saying this session "owns no record in this store",
because the session claimed its write scope through the `.sbe` task registry and a
STATE.md fence, while verify-close reads the bm_store record store. So the
ceremony that exists to refuse a session holding unparked claims could not see
seven live claims. That makes FOUR registries in play in one evening that cannot
see one another: STATE.md fences, `.sbe` tasks, `.sbe` decision packages, and
bm_store records. The close verifier reached the honest answer (NO-DATA, never a
pass, exit 2 for could-not-tell) which is exactly right and is why nothing was
falsely claimed. It is still a control that cannot reach a verdict about the thing
it exists to check.

## Caught before or after it could hurt a user

Before, and only just. Nothing was lost, because the cleanup was snapshotted
first and every forced close is permanently marked FORCED. But the received
explanation of H9 was one action away from deleting real prose from a state file,
and that action was written down as the recommended fix in a plan.

One consequence that is NOT fixed and must not be read as fixed: `STATE.md` is
gitignored at `.gitignore:3` and `.sbe/` at line 69, so all of tonight's clearing
is local to one machine. A fresh clone starts with whatever its own registries
hold, and the matcher ships to everybody.
