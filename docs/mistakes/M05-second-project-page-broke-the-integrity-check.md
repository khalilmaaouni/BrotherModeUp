# M05: a second project's generated page failed the user's own integrity check

## WHAT HAPPENED

Plain language: BrotherMe ships a command that lets a user verify their install is
untampered (`scripts/verify-install.sh`). It walks the installed tree and compares
every file against a signed list. Any file it finds that is not on the list is
reported as EXTRA and the check FAILS.

BrotherMe also generates project pages into the project root: `CANVAS.md` and
`DELIVERY-PACKET.md` for a single project, and `CANVAS-<project_id>.md` and
`DELIVERY-PACKET-<project_id>.md` once a user has more than one project.

The two scripts that build and check the file list excluded only the plain
`CANVAS.md`. They did not exclude the multi-project names, and they did not
exclude the delivery packet at all. Git ignored all four names correctly; the
integrity scripts did not. So a user with two projects, or any user who generated
a delivery packet, would run the integrity check and be told their install had
been tampered with.

## HOW IT WAS FOUND

By the orchestrator reading the exclusion lists side by side against `.gitignore`
during the structural consistency pass, not by a test. There was no test comparing
the three lists to each other at that point.

## THE EVIDENCE

The state before the fix, read straight out of git history (run in this task):

```
$ git show ac7ef87^:scripts/verify-install.sh | grep -n "CANVAS\|DELIVERY"
173:    ! -name 'CANVAS.md' \

$ git show ac7ef87^:.gitignore | grep -n "CANVAS\|DELIVERY"
32:/CANVAS.md
33:/DELIVERY-PACKET.md
34:/CANVAS-*.md
35:/DELIVERY-PACKET-*.md
```

Four patterns in `.gitignore`, one in the integrity script. The three missing
names are the failure.

## HOW IT WAS FIXED

Three exclusions added to each of the two scripts, in commit ac7ef87:

- `/Users/khalil.maaouni/Documents/BrotherModeUp/scripts/verify-install.sh`, the
  find prune list around line 174.
- `/Users/khalil.maaouni/Documents/BrotherModeUp/scripts/checksums.sh`, the
  matching list around line 184.

Both now carry `! -name 'CANVAS-*.md'`, `! -name 'DELIVERY-PACKET.md'` and
`! -name 'DELIVERY-PACKET-*.md'` beside the original `CANVAS.md`.

The commit's own evidence line:

```
verify-install: 361 files match, 0 mismatched, 0 missing, 0 extra. PASSED.
```

Read M06 next: the same class of gap was still open for two more generated names
and was found again fourteen minutes later, which is the real lesson here.

## THE RULE THIS PRODUCES

Every generated filename must be excluded in all three places at once (`.gitignore`,
`scripts/checksums.sh`, `scripts/verify-install.sh`), and the pattern family
(`NAME-*.ext`, not just `NAME.ext`) must be covered, because the second project is
where the plain name stops being enough.

## WAS IT CAUGHT BEFORE OR AFTER IT COULD HURT A USER

After it could have hurt a user, and this one is genuinely uncomfortable. The
multi-project CANVAS filenames existed in shipped code before tonight, so any
BrotherMe user with two projects who ran the integrity check would have been told
their installation was tampered with. Nobody reported it because the user base is
the founder plus this repo. It was caught by reading, not by a guard, and only
because the night included a deliberate consistency pass.
