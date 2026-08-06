Status: HISTORICAL record of one incident class, first written 2026-08-07.
It describes what went wrong three times in one night and the rule that
closes it. No em or en dashes.

# M18: the local gate cannot see a stale manifest, and CI can

## What happened

Three times in the night of 2026-08-06, a branch passed the full local gate
ALL GREEN on a clean tree, was pushed, and then failed in continuous
integration on the doctor calibration tests with a line of this shape:

    FAIL: 1 of N listed file(s) do not match CHECKSUMS.sha256:
    <file> does not match its checksum.

Each time the cause was the same: a tracked file was edited after
`scripts/checksums.sh` last ran, so the committed manifest no longer
described the committed tree.

## Why the local gate could not catch it

The doctor calibration inside the suite checks the INSTALLED copy at
`~/.claude/skills/brothermode`, whose manifest matches because it was
cloned from a tag. In continuous integration there is no installed copy:
the checkout IS the tree under test, so the same check reads the branch's
own manifest and sees the drift. The local gate is not lying; it is
answering a different question.

## The rule

Run `sh scripts/verify-install.sh` against the repository root as the LAST
step before every push, not only during a release. It is the one command
that asks the question CI asks. When it reports mismatched or extra files,
rebuild the manifest with `sh scripts/checksums.sh CHECKSUMS.sha256`,
commit that as the final commit on the branch, and push.

Ordering, stated once because getting it wrong is the whole incident:
commit every change, run the gate, THEN rebuild the manifest, then commit
the manifest, then verify, then push. A manifest rebuilt before the last
edit describes a tree that no longer exists.

## What it cost

Three continuous integration cycles, roughly fifteen minutes each, on
three separate branches in one night. Nothing shipped wrong: every failure
was caught by the machine rather than by a user, which is the system
behaving correctly. The cost was time, and the fix is one command.
