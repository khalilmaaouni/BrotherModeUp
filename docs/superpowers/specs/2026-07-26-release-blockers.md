# Release blockers, from the final adversarial check

**HISTORICAL DOCUMENT, dated 2026-07-26. Do not read it as current state.** It is a dated working record: the plan, the verdicts, the blockers and the numbers in it belong to that day and were not updated afterwards. Items it calls open may since have been closed. Superseded by `README.md` and `docs/KNOWN-LIMITS.md` for status, `docs/NOT-FINALIZED.md` for the defect register, `CHANGELOG.md` for what changed since, and `python3 tools/bm_project_facts.py` for version, release tag, hook events and suites.

Verdict: DO NOT PUBLISH until items 1 and 2 are closed. Both were reproduced by the
orchestrator by hand, and both are in code shipped and scored earlier today.

## BLOCKER 1: recovered work is world-readable (VERIFIED BY ORCHESTRATOR)

`recover` creates its worktree with mkdtemp and then removes the directory so git can
create the path, which throws away mkdtemp's owner-only mode. Reproduced with a
world-writable temp directory (Linux /tmp semantics):

    recovered dir:         drwxr-xr-x
    recovered secret file: -rw-r--r--
    contents readable:     PRIVATE draft: acquisition terms, do not share

So on any shared machine, every local account can read a recovered working tree,
untracked private files included. The store itself is correctly owner-only, which makes
this an inconsistency as well as a hole.

Fix: chmod the recovery directory to 0700 immediately after git creates it, before the
checkout, and verify the mode in the test. Also state the mode in the printed output so
the user can see what protection they have.

## BLOCKER 2: the reversibility promise is broken (VERIFIED BY ORCHESTRATOR)

The founder's ratified hard requirement for thread mode was that it can be switched off
mid-project with nothing lost and every thread resumable. Reproduced:

    monday:  off    -> "threads remain on disk under threads/ and are resumable."
    tuesday: resume -> "refused (not-owner): ... only that session may move it to
                        'active' (adoption is the exception for a dead session's record)"

And the owning session id appears ZERO times in the dashboard and ZERO times in any
thread file, so a user cannot even discover who holds it without dumping the database.

This is my own specification error, the fourth of this build. I wrote the not-owner guard
to stop a live session's fence being stolen, and did not notice it also blocks the
legitimate resume-tomorrow case, which is the whole point of the feature.

Fix, and the rule is clean once stated: OWNERSHIP GUARDS ONLY ACTIVE RECORDS. A parked
record has no live writer by definition, so any session may resume it and becomes its
owner in the same transition. Active records keep the guard, and adopt remains the
exception for an active record whose session is dead. Update the law's wording if it
implies otherwise, and add a calibrated test for resume-from-a-different-session across
an off boundary.

## GATE 3: a refused adopt still writes its handover into STATE.md

Delivery happens before the transition, so a refused adopt permanently records a LIVE
thread as "Adopted from dead/stalled thread", and the fingerprint dedupe then suppresses
the true header when off drains it later. The function's own docstring claims a failure
here changes nothing. Fix: transition first, deliver second, or roll back the delivery.

## GATE 4: thread mode leaves the store in a state its own verify calls a problem

The thread CLI never renders the root STATE.md, so session start now prints "verify: 1
problem(s) found" on every run, and the remedy it prints cannot be run from the project
root because it names a relative tools path. Fix: have the thread commands refresh the
view like the store commands do, and print an absolute or resolvable command.

## GATE 5: neither CLI validates flag names

`start X --file f` (singular) creates a thread with the flag text as its objective and NO
fence, exit 0. `checkpoint X --note "..."` reports success and stores nothing. Unknown
flags must be refused, because a silently unfenced thread breaks the one guarantee this
project exists to provide.

## GATE 6: the documents describe a system that no longer exists

Confirmed by executing the documents' own commands: the README's verification grep is
promised to return nothing and returns 61 hits; the README and the limits file both say
the store is imported by nothing and both name the deleted registry as a live tool; the
quickstart states the wrong expected output for its own verification step, on a page whose
rule is to stop when output does not match; the benchmark tells a stranger to cd into a
path only I have; the security document lists V1 files that no longer exist and an
`absorb` command that is not in the CLI; and the documented uninstall leaves the sensitive
store, the thread files, the status file and its backups, the autosave refs, and three
permanent entries in the user's git exclude file, in every project touched.

Fix: correct every one of these against executed output, and add an uninstall path that
actually removes per-project state, or say plainly that it does not and how to do it by
hand.
