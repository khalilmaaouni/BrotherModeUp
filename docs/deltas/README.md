Status: CURRENT. Written 2026-08-15.

# Deltas for the assurance repository, held here because folding them was not safe

These patches were produced by writer agents working in isolated worktrees
under `~/Documents/BrotherSBE/.claude/worktrees/`. They are NOT applied. They
live in this repository so they survive a worktree prune, per the rule that a
deliverable is never left only in a scratch location.

## Why they were not folded

Two reasons, both checked rather than assumed.

1. A second session was committing to `~/Documents/BrotherSBE` throughout
   (two commits landed during this work, and its working tree was dirty).
   Folding into a tree somebody else is mutating, then running that repo's
   own suite over the result, measures their work as much as mine. That is a
   named failure in this project's history, not a hypothetical.
2. The one-writer control there is INERT. Asked directly rather than grepped,
   `python3 tools/sbe_fence_hook.py fences` reports about twenty live claim
   lines with no readable `files:` scope, and says for each one that it "did
   NOT enforce it". So nothing mechanical would have stopped a collision, and
   nothing would have reported one afterwards. That is filed as finding G9.

The fold therefore belongs to whoever holds that repository next, with its
own suite run on the merged tree. Each patch below names its done-check so
that run is a check rather than a fresh judgment.

## The patches

### sbe-unexamined-classes.patch

Closes P14 solution 2: any all-green summary now prints the classes it did
not examine, by name, as NO-DATA. The classes are regression, cross-device,
performance, user experience, and localisation or translated copy.

Target: `tools/sbe_report.py`, chosen over `src/brothersbe/status.py` because
the reporting entry point is the one that produces the literal all-green
SUMMARY line a person accepts against, and it always exits 0 by design.

Reporting only. No verdict logic touched, no exit code path touched. A class
that a receipt actually mentions is not reported as unexamined.

Done-check, from the worktree: `python3 tools/test_sbe_report.py` reported
23 tests OK, with three of them written failing first (the all-green target
naming every class, the exit code identical before and after, and a receipt
mentioning one class excluding only that class).

One thing that run also found, worth carrying: `tools/test_sbe.py` has ONE
pre-existing failure on that tree, a template-marker case in
`templates/dossier`, confirmed pre-existing by stashing the change and
reproducing it. It is not caused by this patch and it is not fixed by it.

### sbe-staleness-clock.patch

Closes the smallest increment of P10: a design dossier now records the commit
its intake was answered against, and a new check reports it STALE once the
repository has moved past that commit by a declared distance. Stale is
NO-DATA, never FAIL, because a stale design is an unknown rather than a
defect. A dossier with no recorded commit is NO-DATA naming the absence, so a
dossier predating the feature cannot read as fresh.

Target: `tools/sbe_design.py` and `tools/test_sbe.py`, both inside the lane's
fence, nothing else touched.

Two design decisions worth keeping, both explained in the diff. The recorded
commit is a new optional key on the intake file rather than a reuse of the
existing convergence pin, because that pin is an exact-match field whose own
test requires ANY drift to be a hard failure demanding a deliberate re-bind;
reusing it would have made ordinary later commits fail an unrelated check.
And the walk is bounded at fifty first-parent hops, reporting NO-DATA rather
than guessing the moment it meets a root commit or an unreadable object,
which matches the file's existing convention.

Done-check, from the worktree: the three new tests ran red first (no verdict
line for staleness, because the check did not exist), then green. The full
`tools/test_sbe.py` reported 118 tests with one failure, and that failure was
confirmed pre-existing by stashing the two changed files and reproducing it
identically on the unmodified tree.

That is the SECOND independent confirmation of the same pre-existing failure,
from a different lane that stashed different files. Two lanes agreeing that a
red test is not theirs is worth more than either saying it alone.

### sbe-tier-split-superseded.patch

SUPERSEDED, kept only as evidence. This lane was building the additive versus
breaking split for the sizing defect when a concurrent session landed the same
fix at `4912bd8`. The lane was stopped as soon as that was noticed. The patch
is kept because it contains two tests written to fail first, and whoever folds
work here may want to compare them against the tests that actually shipped.

Do not apply this patch. Read it, take any test it has that the landed version
lacks, and discard the rest.
