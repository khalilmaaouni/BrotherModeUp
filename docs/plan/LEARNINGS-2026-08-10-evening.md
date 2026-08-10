# What this session actually learned, 2026-08-10 evening

Status: CURRENT. Written by session 6bf23670. No em or en dashes.

Seven learnings. Each names the evidence, and each cost something real to get.
The first three are corrections to this session's OWN work, which is why they
are first: they are the ones a fresh session is most likely to repeat.

---

## 1. A test can be written for a defect it cannot see

THE BIGGEST ONE. The effect-class purity test specified early in this session
snapshots a throwaway project before and after a command and asserts byte
equality. Against a healthy store it PASSES for every command, INCLUDING the
ones that open a writable store while documenting themselves as read-only.

Why it cannot see it: sqlite auto-checkpoints and removes its `-wal` and `-shm`
files when the last connection closes cleanly, `_ensure_git_excludes` is
idempotent and already satisfied, and a pure SELECT leaves the database file
byte-identical. The write happens and leaves no trace the probe can find.

THE REACHABLE CONDITION is a store that is BEHIND. `Store.__init__` calls
`_verify_schema_or_raise(migrate=True)`, so a documented read-only command
MIGRATES an out-of-date database. Proven: a store forced to `schema_version 17`
handed to `bm_project.py status --project-id nosuch` exited 1 having found no
such project, and came back at `18` with a different md5.

THE RULE: before writing down "X is not there", show the instrument can detect X
when it IS there. This project already had that rule written down. It did not
prevent this.

## 2. Three of my own probes returned nulls I nearly recorded as findings

While chasing learning 1, three separate probes failed to reach the code at all:
one exited on a missing store, one on a usage error, one on a missing argument.
Each printed a clean "no migration detected" that I could have written into a
report. The fourth reached the code and found the opposite.

THE RULE: a null result from a probe you did not prove could reach the target is
NO-DATA, never a finding. Check the probe ran before believing what it says.

## 3. A test that stops looking after its first hit under-reports by 3x

The purity test found ONE offender. Once that command migrated the store, the
store was current, and a current store cannot be migrated again, so every later
command was measured in a state where the defect was unreachable and came back
clean. Re-downgrading the store before EVERY command took it from 1 offender to
3.

THE RULE: when a check mutates the thing it measures, reset between subjects.

## 4. An alarm that fires on your own actions trains you to ignore it

The foreign-commit monitor armed tonight fired twice within minutes on the
session's OWN pushes. It tested whether `origin/main` MOVED, which is a change
detector, not the foreign-change detector the watchdog needs.

Fixed: the right test is whether `origin/main` holds commits THIS CHECKOUT DOES
NOT HAVE (`git merge-base --is-ancestor origin/main HEAD`). Same failure family
as a gate that goes red on a busy laptop: both teach people to stop reading.

## 5. A document that names the current commit is stale the moment it lands

The handover written tonight warns that a gate verdict belongs to one commit,
then opened by naming main at a SHA that committing the handover immediately
invalidated. A fresher number would have gone stale on the next commit.

THE RULE: name the COMMAND, not the number. `git rev-parse --short HEAD @{u}`.

## 6. Stale fences from dead sessions block writers forever, and nothing looks

FIVE instances found in one day: `README.md`, `SKILL.md` twice, the findings
ledger, and the README narrowing itself, where another session had claimed that
exact work and died without doing it. Each blocked every writer permanently and
each was cleared by hand.

The detection is trivial: is the owning session alive? Nothing runs it. This is
the single clearest unowned defect in the repository right now.

## 7. Measuring beats reasoning, and it is cheap

The plan allocated one to two days to merging eleven branches. Merging each in a
throwaway worktree and diffing the result against main took about three hours
and showed main ALREADY HELD ALL OF IT. Four of them would have made main worse:
one would have dragged a file back 297 lines, dropped the relay brake and the
session cap, and reintroduced a wall-clock test that had just been removed.

A merge plan built from branch names and commit subjects is a guess.
`git merge-tree --write-tree` against the target, then a diff, is a measurement,
and it costs minutes.

---

## The pattern under all seven

Six of these are the same shape: something that LOOKED like evidence was not.
A passing test that could not fail, a null from a probe that never ran, a clean
result from a check that stopped early, an alarm firing on itself, a stale SHA
presented as current, a merge plan built from names.

The project's founding law is that a rule in a prompt is not a control. Tonight
adds the sibling: a check that cannot fail is not a control either, and it is
harder to spot, because it is green.
