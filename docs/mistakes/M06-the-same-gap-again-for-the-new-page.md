# M06: the same gap again, for the brand new page shipped that same night

## WHAT HAPPENED

Plain language: the visual surface that landed this night writes two new things
into a user's project: `PROJECT-VIEW.html` at the project root, and brief pages in
a `Handover/` directory. Neither was added to `.gitignore`, to the checksum
manifest builder, to the integrity checker, or to the installer's copy exclusions.

Result: the moment any user ran the new headline feature (`bm-view render`), their
own integrity check would fail with an EXTRA file. The feature and the bug shipped
in the same night, in commit b02756f.

This is exactly the class closed in M05 fourteen minutes earlier, on the same
evening, by the same session. Closing the class for the old names did not prompt
anyone to ask whether the night's own new names were covered.

## HOW IT WAS FOUND

By dogfooding, meaning the session ran BrotherMe's own release program through the
product on this repository, rendered a real page (39494 bytes), and then ran the
integrity check on the tree with the page present. Not by a test, not by review.
Running the product on itself is what surfaced it.

## THE EVIDENCE

The commit that closed it, `git show --stat --format=full c1d7a47`, message
verbatim:

```
Stop a rendered project page from failing the user's own integrity check

Found by dogfooding tonight's own release program through the product:
bm-view render writes PROJECT-VIEW.html at the project root and the brief
pages land in a Handover/ directory, but neither was gitignored or excluded
from the checksum manifest, so any user who rendered a page would then see
verify-install FAIL with an EXTRA file. This is the same class as the CANVAS
generated-view gap closed earlier tonight.

Evidence: git check-ignore PROJECT-VIEW.html now matches; verify-install
PASSED with the 39494-byte rendered page present on disk; test_bm.py and
test_install.py both green.
```

Timing, from `git log --date=format:'%Y-%m-%d %H:%M'`:

```
ac7ef87 2026-08-06 02:11   (M05 closed here)
c1d7a47 2026-08-06 02:25   (M06 closed here)
```

## HOW IT WAS FIXED

Five places in commit c1d7a47:

1. `/Users/khalil.maaouni/Documents/BrotherModeUp/.gitignore` gained
   `/PROJECT-VIEW.html`, `/Handover/` and `/Handover-*/`.
2. `/Users/khalil.maaouni/Documents/BrotherModeUp/scripts/checksums.sh` gained the
   four `Handover` path prunes at lines 175 to 178 and
   `! -name 'PROJECT-VIEW.html'` at line 186.
3. `/Users/khalil.maaouni/Documents/BrotherModeUp/scripts/verify-install.sh` gained
   the same at lines 170 to 173 and line 181.
4. `/Users/khalil.maaouni/Documents/BrotherModeUp/scripts/install.py`
   `COPY_EXCLUDE_NAMES` at scripts/install.py:123 gained `PROJECT-VIEW.html` and
   `Handover`.
5. The guard was widened to hold the whole family, not just the new names:
   `TestGitignoreCoversGeneratedProjectViews` at
   `/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_bm.py:6090` now
   asserts all seven patterns in `.gitignore` and asserts that both manifest
   scripts prune `Handover`. That test is the thing that makes the next generated
   filename cost somebody a line instead of a broken install.

## THE RULE THIS PRODUCES

When you close a bug class, immediately grep the tree for every other member of
that class including the code you shipped tonight, and add the guard that holds
the family; fixing the instance you were shown is half a fix.

## WAS IT CAUGHT BEFORE OR AFTER IT COULD HURT A USER

Before, by hours, and only because the session dogfooded its own release. The
feature landed at 00:29 (b02756f) and the exclusion gap was closed at 02:25
(c1d7a47), both before any user could install the 2.1 line, and the v2.1.0 tag is
still not cut. Had the dogfooding step been skipped, the first thing a new user did
with the flagship feature would have told them their install was corrupt.
