# Loop 8 validation ledger: what exists, what is partial, what only the founder can supply

Status: CURRENT. Written 2026-08-02 by the orchestrator, overnight, founder
asleep. Loop 8's gate is the ratified program's minimum external-validation
list, every item with evidence. This ledger is the honest inventory: it
closes nothing by itself, and it says so. Loop 8 stays OPEN until every row
below reads DONE with evidence a stranger could check.

## The seven required items, row by row

### 1. The dogfood record, running since Loop 2

Required: the founder's real project run through the seven beginner
commands, seven calendar days minimum (amendment A2 started the clock the
day Loop 2 closed, 2026-08-01).

State: NOT STARTED. No dogfood record exists anywhere in this tree or the
vault. No engineering can compress this: the gate demands calendar days of
real founder work. FOUNDER-GATED. The one thing this session can say is
that the commands the dogfood needs are the mechanical ones Loop 2 landed
and the scripted end-to-end gate exercises daily.

### 2. Three fresh-machine outside installs

Required: three installs on machines that are not the author's, by people
who are not the author.

State: NOT DONE, and the nearest evidence is honest about being weaker:
docs/evidence/2026-08-01-fresh-home-rehearsal.md is a SCRIPTED fresh-HOME
rehearsal on the author's machine (scripts/rehearse_fresh_install.py), and
docs/evidence/2026-07-31-first-plugin-install.md is one real install, on
the author's machine, from a local copy. Zero installs from GitHub, zero
other machines, zero other people. FOUNDER-GATED: needs three outside
humans.

### 3. One non-technical user

Required: a non-technical user completes the guided flow.

State: NOT DONE. No evidence of any non-author user. FOUNDER-GATED.

### 4. One recovered interruption

Required: an interrupted work session recovered without loss.

State: CANDIDATE EVIDENCE EXISTS, from this very night, inside the program
itself. The desktop harness stashed the handover's uncommitted six-hook doc
fix out of the working tree twice ("epitaxy: pre-switch" stashes) and once
flipped the checkout's branch between two commands of one chain, so the fix
was committed onto main by accident. Recovery, fully recorded in the
2026-08-02 session log and the git reflog: the stray commit was
cherry-picked onto release/2.0-final as 1c78222 byte-identical (the docs
suite passed before and after), main was reset back to origin/main, and the
rest of the session ran in a dedicated worktree the harness cannot flip.
Nothing was lost. Whether this satisfies the source plan's intent (it asked
for a recovered interruption of PROJECT work, and this was an interruption
of the program's own work) is the founder's call, flagged rather than
assumed. If accepted: DONE. If not: the item stays open until dogfood
produces one.

### 5. One failed review causing rework

Required: a review that failed work and forced a rework, with the trail.

State: DONE, more than once, with commits as evidence. The clearest single
case: the Loop 6 refuter pass found that a clone install never wired the
PostToolUse entrypoint, which failed the loop's first delivery and forced
the installer, its test suite, doctor, and two docs to be reworked together
(commit 3f688e6, "Loop 6 answers its refuters", and the loop6-refuter-fixes
record in the store). Also on file: the Loop 2 refuter pass (twelve
confirmed findings, commit trail in the store's loop2-refuter-fixes
record) and the Loop 3/5 pass (integrity and register findings,
loop35-refuter-fixes). These are internal adversarial reviews, which is
what the program's own separation-of-duties law prescribes.

### 6. One reforecast

Required: budgets reforecast from measured spend, per amendment A7, after
Loops 1 and 2.

State: PARTIAL. The raw measurements exist and are recorded where they
happened: Loop 0's builder spent 261,882 subagent tokens against a
25k-60k envelope (recorded in STATE.md's wave 14 close for exactly this
purpose), and the machine's telemetry shows multi-million-token days
(5.87M output tokens across 9 sessions in the 24h before this session,
from the SessionStart spend line). What does NOT exist is the reforecast
document itself: nobody has re-derived the program's remaining envelope
from those numbers and written it down with confidence and assumptions.
That is machine-doable and small; it was not done tonight because the
honest reforecast should include the founder's dogfood window, which has
not started, so its biggest assumption is still unset. Recommended: write
it the day dogfood starts.

### 7. One delivery

Required: one delivery through the delivery lane.

State: PARTIAL, same shape as item 4. The scripted end-to-end gate runs a
first project through all seven commands including deliver
(tools/test_bm_project.py, inside test_all, green daily), so the LANE is
proven. A real delivery of real founder work has not happened and arrives
with dogfood. FOUNDER-GATED for the real one.

## Summary line for the founder report

Machine-provable rows: 5 (done), 4 (candidate, your call), 7 (lane proven,
real one pending). Founder-only rows: 1, 2, 3, and the real halves of 4, 6
and 7. Loop 8 cannot close tonight and this ledger does not pretend to
close it. The single highest-leverage founder action is starting the
dogfood clock: items 1, 4, 6 and 7 all draw from it.
