# Defect: the v3.2.0 tag and VERSION disagree about which commit is the release

Status: CURRENT, OPEN, and it needs a founder decision rather than a fix.

Found 2026-08-12 12:15 JST by the full gate at `cab847d`.

## What the gate says

```
tag v3.2.0 points at 54ff2c28cd40b31de135c595e0328540ce7e9c17
but the commit that last set VERSION to 3.2.0 is eecb782d9fdd0d212d42ca1370af76eaa5e88cd4;
the tag and VERSION disagree about which commit is the release
```

One suite of thirty five. The other thirty four are green, 3136 tests.

## Why it is not from this session's work

This session touched neither VERSION nor any tag:

```
$ git diff --name-only 5e5fe7c..cab847d | grep -c "^VERSION$"
0
```

## What actually happened, as far as it can be established without guessing

History was rewritten under this session while it worked. Commits this session
had already made under one identity now exist under another: the commit
messaged "The consent gate refused a hook I wired in a hurry" was committed
here as `62d2350` and also exists as `6f21611`. Both objects are still
reachable. `origin/main` moved to `d369270`, which is an ancestor of the
current HEAD, so a rebase or a merge folded this session's line onto another
session's.

The release-cut commit was carried along by that rewrite and acquired a new
identity, `eecb782`. The tag `v3.2.0` still points at the OLD object,
`54ff2c2`. So the tag and the VERSION file now name different commits as the
release, which is exactly what the release-truth check exists to catch. The
check is working; the repository is what changed.

## Why it is not being fixed here

Retagging a published release is a founder decision, not a cleanup. The tag
`v3.2.0` is on the remote and is what the install card, the tester pack and
both product install commands pin to. Moving it changes what every tester
downloads. This session has no licence for that and is not taking one.

## The three options, for the founder

1. **Retag `v3.2.0` onto `eecb782`** and force-update the remote tag. Makes
   the tag agree with VERSION. Everyone who already pinned gets a different
   object under the same name, which is the thing tags are supposed never to
   do.
2. **Cut `v3.2.1`** from the current tree, leave `v3.2.0` alone, and update
   the install card and tester pack to the new number. Costs a version number,
   breaks nothing that already exists.
3. **Leave it and record the divergence**, accepting a red suite until the
   next release cut naturally resolves it. Cheapest today, and it means the
   gate stays red, which trains everyone to ignore it. Not recommended for
   that reason.

Recommended: option 2. It is the only one that neither rewrites published
history nor leaves a gate permanently red.

## What this costs until it is decided

`python3 tools/test_all.py` exits 1 on this one check. Any session that
requires ALL GREEN before pushing is blocked, or has to know about this file.
That is the real cost and it is why this needs deciding rather than carrying.
