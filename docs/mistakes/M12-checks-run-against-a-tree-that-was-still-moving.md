# M12: checks were run against a tree that was still moving

## WHAT HAPPENED

Plain language: when several writers work in parallel, a test run only tells you
the truth about the exact tree it read. If a file lands while the run is happening,
or between the run and the report, the result describes a tree that no longer
exists. That happened during the night, and it means some intermediate green
results were not evidence of anything.

Two instances, one verified in the record and one reported by the orchestrator.

1. VERIFIED. A writer finished its checks and wrote its report, and another
   writer's file appeared in the tree at 22:21 while it was doing so. The writer
   caught it, re-checked, and appended a late note (see M11 for the collision that
   note found). Had it not re-checked, its report would have described a tree that
   had already moved on.

2. REPORTED BY THE ORCHESTRATOR, UNVERIFIED BY ME: a full gate (the whole test
   suite) was run while files were still being edited underneath it, making that
   run's result untrustworthy, and it was re-run after the last edit. I found no
   record of the discarded run in the repository, which is expected, because a
   discarded run leaves no artifact. What I can verify is the discipline it
   produced, which is quoted below.

## HOW IT WAS FOUND

Instance 1: by the writer itself, which re-read the tree after its last edit
instead of trusting its earlier reading.

Instance 2: by the orchestrator, by noticing that edits were still landing while
the gate ran.

## THE EVIDENCE

Instance 1, from
`/Users/khalil.maaouni/Documents/BrotherModeUp/docs/program/absolute-lead/evidence/L05/RED-F.txt`
line 190:

```
LATE NOTE (added after the last edit, because the tree moved underneath it)

tools/test_bm_visual.py appeared in the tree at 22:21 while this writer was
finishing, landed by Writer D.
```

Instance 2, the discipline in the commit messages of the night, verified with
`git log --format='%B' | grep -c "quiet machine"` which returns 5 across the whole
history, three of them from this run and the evening before it:

```
b02756f: Evidence, run after the last edit on a quiet machine (load 5.2):
         test_all: 2370 tests across 20 suites, 6 skipped, 308.2s wall. ALL GREEN

ac7ef87: Evidence, run after the last edit on a quiet machine (load 2.x):
         test_all: 2442 tests across 20 suites, 6 skipped, 352.2s wall. ALL GREEN
```

And the origin of the phrase, from the commit immediately before this run
(c59dd2a, 2026-08-05 21:25), which records the earlier version of the same failure:

```
Gate after the last edit, on a quiet machine because two earlier runs were
killed under a load average of 45 and a killed gate is not a result:
test_all, 2244 tests across 18 suites, 6 skipped, 403.3s wall, ALL GREEN,
exit 0.
```

## HOW IT WAS FIXED

The gate was re-run after the last edit, on a quiet machine, and only that run was
quoted as evidence. Both night commits state the condition in the message itself
(load average included), so a reader can tell whether the number was measured under
sane conditions.

The rule is now visible in three places a future session will actually read: both
commit messages of the night, and
`/Users/khalil.maaouni/Documents/BrotherModeUp/CHANGELOG.md:10`, which carries
`Gate after the last edit, on a quiet machine: test_all: 2442 tests across 20
suites`.

## THE RULE THIS PRODUCES

A test run counts only if it started after the last edit and nothing wrote to the
tree while it ran; state the load average and the timing in the same sentence as
the result, and treat a run that overlapped an edit as no result at all.

## WAS IT CAUGHT BEFORE OR AFTER IT COULD HURT A USER

Before any user impact, but this is the failure with the worst potential in the
folder, because its damage is invisible. A gate that ran on a moving tree still
prints OK. Every other mistake in this folder was caught by something; this one can
only be caught by the person who knows what was happening at the time, and the only
defence is the habit of re-running after the last edit and saying so.
