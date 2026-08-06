# M14: the founder's morning report points at a commit that is not on the branch

## WHAT HAPPENED

Plain language: the report written for the founder at the end of the night names
the commit that fixed the dogfooding bug as `af375ee`. That commit was amended
twice before being pushed, so the commit that actually carries the fix is
`c1d7a47`. `af375ee` exists only as an orphaned object in this one local clone. On
the founder's machine, or on a fresh clone, or on GitHub, `git show af375ee` finds
nothing.

The report is correct about what happened. It is wrong about the one identifier a
reader would use to go and look at it.

## HOW IT WAS FOUND

By me, in this task, while reconstructing the night from `git reflog`. It was not
caught before delivery: the report was written at 02:40 and handed to the founder
with the wrong hash in it.

## THE EVIDENCE

The report, at
`/Users/khalil.maaouni/Documents/BrotherModeUp-handovers/2026-08-06-MORNING-REPORT.md`
line 19:

```
Fixed across every place that matters, with a test that will catch the next
one. Commit af375ee.
```

What the branch actually contains, verified in this task:

```
$ git log --oneline -5
c1d7a47 Stop a rendered project page from failing the user's own integrity check
04d3133 Open the 2.1 development line, with the changelog and release log to match
ac7ef87 Make the fence bite Codex writes, and shut three doors in the autonomy contract
745e2d7 Freeze the comparative benchmark before any run, so the scoring cannot chase the result
b02756f Land the visual surface: the founder's page, its vocabulary, and the register that keeps it honest

$ git log --all --oneline | grep af375ee
(no output, exit 1)

$ git cat-file -t af375ee
commit
```

So the object exists locally and is reachable from nothing. The reflog explains it:

```
c1d7a47 HEAD@{0}: commit (amend): Stop a rendered project page from failing ...
964ca84 HEAD@{1}: commit (amend): Stop a rendered project page from failing ...
af375ee HEAD@{2}: commit: Stop a rendered project page from failing ...
```

A SECOND CLAIM IN THE SAME REPORT THAT I COULD NOT VERIFY, recorded here rather
than in a footnote. Line 56 says "The final full suite ran green on that exact
commit: 2442 tests across 20 suites". The 2442 gate is recorded in the commit
message of ac7ef87, which is two commits earlier, and `c1d7a47` changed two test
files after it. `c1d7a47`'s own evidence line claims only `test_bm.py and
test_install.py both green`. A full-suite run may well have happened on c1d7a47 and
simply not been written down, so this is UNVERIFIED rather than wrong, and the next
session should re-run the gate on HEAD before quoting that number anywhere.

## HOW IT WAS FIXED

Not fixed at the time. It is corrected here, and the correct identifier for the
dogfooding fix is `c1d7a47`. Nothing in the repository is wrong; the error is in
the delivered report only.

## THE RULE THIS PRODUCES

Never quote a commit hash you captured before the commit was final: read it back
with `git log --oneline -1` after the last amend and after the push, and quote that,
because an amended hash is a pointer to nothing on every machine except the one that
made it.

## WAS IT CAUGHT BEFORE OR AFTER IT COULD HURT A USER

After. This one reached the founder. The harm is small (a dead link in a report,
not a broken product) but the class is not small: a founder-facing document that
cites unverifiable identifiers teaches the reader to stop checking, which is the
opposite of what an evidence-first project is for.
