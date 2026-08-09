# Branch decisions: the path to one main

Status: CURRENT. Written 2026-08-10 against `main` at `9b8c324`. Every
containment claim below was computed, not eyeballed, and the command that
computed it is named. No em or en dashes.

The north star ends with ONE clean main branch. Today there are 20 remote
branches, 19 besides main, and 18 of those carry commits that exist nowhere
else. This file turns that into a small number of yes-or-no answers.

**Re-run the proofs before acting.** Every table here ages the moment anyone
pushes. The commands are given so they can be re-run rather than trusted.

---

## GROUP A: DELETE NOW. Zero loss, mechanically proven.

Four branches hold nothing that is not held elsewhere. This is not a judgement
call and it needs no review of the work itself.

**A1. The three `phase-c` siblings are subsets of `phase-c/continuity`.**
Proven with `git merge-base --is-ancestor origin/<b> origin/phase-c/continuity`,
which returned YES for all three:

| Branch | Unique commits | Status |
|---|---|---|
| `phase-c/liveness` | 4 | every one also on `phase-c/continuity` |
| `phase-c/continue-flows` | 3 | every one also on `phase-c/continuity` |
| `phase-c/continue-subcommand` | 2 | every one also on `phase-c/continuity` |

They are a stack: `continuity` (7) contains `liveness` (4) contains
`continue-flows` (3) contains `continue-subcommand` (2). Keep `continuity`,
delete the other three, and no commit is lost.

**A2. `claude/gracious-sammet-456ce7` is a byte-identical duplicate of
`archive/2026-08-08-retired-team-briefing`.** Both tips are `d4f2f91`. Keep the
`archive/` one, whose name says what it is, and delete the `claude/` one, whose
generated name says nothing.

**Command for group A:**

```
git push origin --delete phase-c/liveness phase-c/continue-flows phase-c/continue-subcommand claude/gracious-sammet-456ce7
```

**Done-check.** `git branch -r | grep -v HEAD | wc -l` drops from 20 to 16, and
`git rev-list --count origin/main..origin/phase-c/continuity` is still 7, which
proves the surviving branch kept the work.

---

## GROUP B: REAL WORK, NOT YET IN MAIN. Each needs a merge-or-abandon answer.

Eleven distinct bodies of work. Grouped by what they actually do, because the
branch names do not say and several branches carry the same fix.

### B1. The bash-audit alert path. Three branches, one defect family.

- `claude/laughing-engelbart-4ba095` (5): "Stop the first bash-audit alert from
  breaking verify forever", plus a manifest rebuild.
- `claude/charming-goldwasser-6d8423` (2): "Give the bash-audit alert path a
  project to be attributed to", plus a manifest rebuild.
- `fix/system-projects-excluded-from-project-counts` (1): "Stop the bash-audit
  bookkeeping row from counting as the founder's project".

**Why this matters more than its size.** The first one says an alert breaks
`verify` FOREVER. `verify-install.sh` is the integrity check a user runs to
confirm what they installed. A first alert permanently breaking it is the same
class of defect found on 2026-08-04, when the test suite's own build artifacts
made `verify-install` report FAILED. A checker that cries wolf gets ignored, and
then it protects nobody.

**Recommendation: MERGE all three.** They are small, they are fixes, and they
touch the same area, so they should land together and be gated once.

### B2. Continuity: `brothermode continue`. One branch.

`phase-c/continuity` (7), the survivor from group A. Adds a handoff packet
generated from records, makes the successor's permission mode an explicit choice
rather than a default, and proves a successor is alive rather than merely
spawned.

**Why it matters.** This is the feature that would have prevented the thing that
actually went wrong on 8 August, when three sessions died holding work. It is
directly on the north star's "memory" leg.

**Recommendation: MERGE, and gate it hard.** It touches session spawning, which
is the blast radius of the runaway. The permission-mode-as-explicit-choice
commit deserves reading line by line before it lands.

### B3. Phase 5, the progress view. One branch.

`phase-5/progress-view` (7): draws the Gantt as a seventh shape, puts it on the
product page as one section rather than a second page, reaches the phase from the
command line, and gives the page the house typography.

**Confirmed NOT in main**: all four sampled commits returned
`in-main=NO` from `git merge-base --is-ancestor`.

**Why it matters.** The progress page IS the product feature named in the north
star. The page the founder is reading today is a hand-maintained snapshot; this
branch is the generator.

**Recommendation: MERGE.** The page currently marks P5 at 5 of 6, so this is
most of the remaining sixth.

### B4. Phase 3, one honest install. Two branches, overlapping.

- `phase-3/install-truth` (3): "Fix stale plugin id in source of truth, correct
  the docs' false failure claim".
- `claude/jovial-tereshkova-830231` (2): "Retire the stale plugin-install failure
  note, now that the pin is v3.0.0".

Both correct a stale claim about plugin install failing. Check whether either
supersedes the other before merging both; they may conflict on the same lines.

**Why it matters.** The page lists P3 at 0 of 5, and "one honest install path" is
a north-star clause. Also relevant: the founder's team installs by handing the
repository link to their own Claude, so a false failure note in the docs is read
by a MODEL and acted on. Doc accuracy here is install reliability.

**Recommendation: MERGE, after resolving the overlap.**

### B5. The design and visual layer. One branch.

`claude/reverent-bhaskara-2c96c9` (9): lifts the design's ban on timeline and
gantt per a founder decision of 2026-08-08, makes `bm_visual.py` count its own
shapes correctly, plus manifest rebuilds.

**Note the dependency.** The ban-lifting commit is what ALLOWS B3's Gantt to
exist. If B3 merges without it, the design document and the shipped page
contradict each other.

**Recommendation: MERGE, and merge it BEFORE or WITH B3.**

### B6. Progress page brevity budget. One branch.

`feature/progress-page-template` (3): "Cap the progress page: a brevity budget
the reader can survive, with nothing deleted".

**Recommendation: MERGE with B3.** Same feature, and a budget applied after the
page ships is a rewrite rather than a cap.

### B7. Phase 6, the findings ledger. One branch.

`phase-6/findings-ledger` (3): reconciles both adversarial reviews into one
findings ledger.

**Recommendation: MERGE.** The page has P6 at 2 of 6 and this is step 1 of it.

### B8. CI and doctor determinism. Two branches.

- `relay7/ci-doctor-fix` (4): "Stop the doctor test asserting a fact about the
  machine it runs on", plus filing the independent gate that let Phase 5 merge.
- `fix/hookperf-projection-determinism` (1): "Prove the projection invariant on
  fixed inputs, not on the runner's mood".

**Why these two are the same disease.** Both are tests that measure the MACHINE
rather than the code. This project has a long record of exactly that failure:
the C-11 timing flake, and two earlier stopwatch tests before it. The page's
watch list currently says the SBE gates are RED on all five jobs at the newest
run. A flaky gate teaches people to re-run rather than read.

**Recommendation: MERGE BOTH FIRST, before anything else in group B.** A red or
flaky gate makes every later merge unverifiable, because nobody can tell a real
regression from the runner's mood.

### B9. The team briefing booklet. One branch.

`archive/2026-08-08-retired-team-briefing` (5): a developer-facing booklet, its
mock-ups replaced with real tool output, and a correction of a false claim about
how far the docs suite holds it.

**Its own name says RETIRED**, and it sits under `archive/`. That is a decision
somebody already took.

**Recommendation: FOUNDER DECISION.** Either it is genuinely retired, in which
case the branch can be deleted once the founder confirms nothing in it is wanted,
or it is not retired and the name is wrong. Do not delete an `archive/` branch on
a session's own judgement: archive means somebody wanted it kept.

### B10. The dashboard write-on-help defect. One branch.

`claude/practical-kowalevski-471524` (4): "Stop `bm_store dashboard --help` from
performing a write".

**Why it matters out of proportion to its size.** A `--help` flag that WRITES is
a real defect: help is the one command a nervous user runs to find out what
something does before letting it touch anything. It also breaks the project's own
pre-consent rule, which says the tool writes nothing before setup consent exists.

**Recommendation: MERGE.**

---

## CORRECTION 2026-08-10, after the first gate run. B2 MOVES FROM LAST TO FIRST.

The order below was written before anything was merged. The first real gate run
disproved its top assumption and the corrected order is here rather than in the
list, which is left as written.

**MAIN IS ALREADY RED, and it was red before any merge in this file.**
`test_all: 2880 tests across 27 suites, 2 skipped, 455.1s wall. 1 SUITE(S)
FAILED`, exit 0 on the runner but one suite down:
`test_brothermode_cli.py: Ran 82 tests, FAILED (failures=6, errors=5)`.

**Not caused by the B8 merges**, proven two ways rather than assumed:
`tools/test_brothermode_cli.py` is byte-identical to its content at `9b8c324`
(the pre-merge tip), and `git diff 9b8c324 HEAD --stat` reports no change to
either that test or `tools/brothermode_cli.py`.

**Root cause.** All eleven failures are successor-liveness tests
(`TestLaunchRecordsLiveness`, `TestDeadSuccessorIsAFinding`,
`TestSilentButRunningIsNotAFailure`, `TestTheSecondHandoverDoesNotQuoteTheFirst`).
The failure shape is `IndexError: list index out of range` on
`self.liveness_rows()[0]`: a launch records NO liveness evidence, so the list is
empty. The tests for the feature are on main; the commit that makes a launch
record that evidence, `9fe992b` "Make the launch prove the successor is alive,
not just spawned", is on `phase-c/continuity` and unmerged.

**So B2 is not the risky thing to do last. It is the thing main is currently
broken without.** Its own commit message names the incident it closes: on
2026-08-08 the first relay was spawned, died in the same second on a prompt a
variadic `--add-dir` had swallowed, and was reported as launched, after which
the program sat still until the founder restarted it by hand. That is the exact
failure mode the 8 August runaway ran on.

**Corrected order: B8 (done), then B2, then the rest as listed.** B2 still
deserves the most careful review because it touches session spawning; "review it
hardest" and "merge it last" were conflated in the original list and they are
not the same instruction.

**UNVERIFIED, and it must be checked before B2 is called the fix:** that merging
`phase-c/continuity` actually turns these eleven tests green. Nobody has run
that. Merge it in a scratch copy and run `python3 tools/test_brothermode_cli.py`
BEFORE landing it on main. If it does not fix them, the tests were landed ahead
of any implementation and that is a separate defect with a separate owner.

## The order I would merge in, and why (as originally written, see correction above)

1. **B8 first**, both determinism fixes. Until the gate is trustworthy, no later
   merge can be verified, and the page already reports all five SBE jobs red.
2. **B1**, the bash-audit alert family, three branches gated once. Small, and one
   of them permanently breaks the integrity checker.
3. **B10**, the write-on-help fix. Small, self-contained, real.
4. **B5 then B3 and B6 together.** The design amendment must not land after the
   feature it authorises.
5. **B4**, install truth, after resolving the two-branch overlap.
6. **B7**, the findings ledger.
7. **B2 last**, continuity, because it touches session spawning and deserves the
   most careful gate, run when nothing else is in flight.

After each merge: full gate green on the MERGED tree before the next one starts.
A green branch and a green merge are not the same claim.

---

## What this does NOT decide

- Whether any of these branches conflict with each other. Not computed. Several
  touch `CHECKSUMS.sha256`, which is generated, so expect conflicts there and
  regenerate rather than hand-merging, per this project's standing practice.
- Whether the work inside each branch is CORRECT. This file classifies branches
  by what they claim to do, read off their commit subjects. Each merge still
  needs its own review.
- The two tags and the SBE workflow edits the progress page lists as waiting on
  the founder. Those are separate and still waiting.

---

## DECISIONS TAKEN ON THE FOUNDER'S BEHALF, 2026-08-10 night

The founder went to sleep having deferred every pending approval to this
session's judgement. Recorded at the moment they were taken, with the
alternative and the flip condition, because a decision discovered later in a
report is the correction-class failure this project names.

**DECISION 1: the two release tags are NOT cut tonight. Blocked on evidence,
not on nerve.**
A release tag is a promise that a version name and a set of bytes are the same
thing, and this project already withdrew `v2.0.0-rc.1` for breaking exactly
that. MAIN IS RED: `test_all` reports 1 of 27 suites failing,
`test_brothermode_cli.py` at 6 failures and 5 errors. A tag cut from a red tree
publishes a version whose own gate does not pass.
ALTERNATIVE CONSIDERED: cut them anyway, since the red is inherited and
unrelated to the release content. REJECTED: "unrelated" is a judgement, a tag
is permanent, and the asymmetry is severe.
FLIP CONDITION: `test_all` ALL GREEN at exit 0 on the commit being tagged, and
CI agreeing on that same commit.

**DECISION 2: the `phase-c/continuity` merge is NOT completed tonight.**
Attempted, then aborted. The abort was checked rather than assumed, after the
fact: `.git/MERGE_HEAD` absent, zero conflict markers across `tools/`, `docs/`
and `scripts/`, zero unmerged paths, clean `git status`.
It conflicts in two files, and the one that matters is `tools/write_sites.json`,
the reviewed write-site manifest that refuses new file-writing code nobody has
reviewed. Its conflict is in the narrative comment and the per-file counts, so
resolving it correctly means RE-DERIVING the counts by running the scanner over
the merged tree, not choosing a side. A careless resolution silently weakens the
control itself.
ALTERNATIVE CONSIDERED: resolve it now, since main is red without this merge.
REJECTED: the session was nearly out of context, and a security manifest
hand-merged on fumes is how a control gets quietly broken. Unattended work from
a low-context session is the shape of the 8 August runaway.
FLIP CONDITION: a session with room to run the scanner, re-derive every count,
and gate the merged tree before landing. It is FIRST in the merge order.

**DECISION 3: the archive branch was tagged, not deleted outright.**
`archive/team-briefing-2026-08-08`, annotated, on `d4f2f91`, pushed, holding all
five booklet commits; the branch is gone. Not a release tag: no version, and the
release-truth suite ignores it.
FLIP CONDITION: none needed. `git checkout archive/team-briefing-2026-08-08`
returns the booklet whole.

**NOTHING THAT WRITES IS LEFT RUNNING.** The watchdog is READ-ONLY by the
founder's own choice, and its tick prompt explicitly overrides the watchdog
skill's clause that an idle tick should resume unblocked work. No relay, no
successor, no auto-spawn. The mechanism behind the 8 August runaway was
disarmed on 2026-08-09 and this session did not re-arm it.

---

## CORRECTION 2026-08-10, by an independent Opus reviewer. THE RED PREMISE WAS FALSE.

An independent reviewer, briefed to DISPROVE rather than confirm, refuted the
headline finding above. The correction is kept here rather than replacing the
wrong text, because the sequence is the point.

**MAIN IS NOT RED.** The eleven failures are MACHINE STATE, not code. Proven by
A/B/A at one commit on a clean tree:

```
RUN A default        FAILED (failures=6, errors=5)
RUN B CAP=99         OK          (Ran 82 tests)
RUN C default        FAILED (failures=6, errors=5)
```

The failure text names its own cause: "The relay stopped here, and started
nothing: 3 Claude sessions are already live against the machine-wide cap of 3."
The liveness tests in `tools/test_brothermode_cli.py` assert a fact about the
HOST. That is the identical defect class `b3227ed` just fixed for the doctor
test, "Stop the doctor test asserting a fact about the machine it runs on", and
the same family as the C-11 timing flake and the two stopwatch tests before it.

**THE GATE IS SELF-POISONING.** Running `test_all.py` concurrently with other
Claude sessions manufactures its own failure, because the session cap is 3 and
the audit sessions consume it. So "flip condition: ALL GREEN" is UNREACHABLE
whenever more than two sessions are live. A gate that cannot pass while the
team works is not a gate.

**FIX, and it is the same shape as the one already applied to the doctor test:**
those tests must state their precondition and SKIP when the cap is saturated,
or the gate must reserve cap headroom. Until then every red reading from this
suite is ambiguous between a real defect and a busy machine.

**WHAT THIS INVALIDATES.** Decision 1 above says the release tags stay uncut
"because main is RED". THAT REASON IS WRONG and is withdrawn. The decision
itself still stands, on a DIFFERENT and independent reason discovered
afterwards: `v3.0.0` is already tagged, `main` is 44 commits past it, and
`VERSION` still reads `3.0.0` with `release_tag` reporting `v3.0.0` and
`is_development` False. That is the two-trees ambiguity that withdrew
`v2.0.0-rc.1`, live right now. A tag cannot be cut for a version already
tagged, and inventing a new version number for 44 commits nobody in that
session had read is not a defect that can be fixed afterwards, because the
wrong name is permanent.

**ALSO CORRECTED: the two merges landed ZERO bytes.**
`git diff 9b8c324 73c1e59 --stat` and `git diff 73c1e59 68e9c25 --stat` are both
EMPTY. The content was already in main; the doctor fix arrived earlier via
`e9c8b21 (#23)`. Only history was recorded. Describing them as "two determinism
fixes landed" overstated the change, and the correct statement is that two
branches were absorbed whose content main already had.

**CONFIRMED by the same reviewer, so the good news is evidenced too:** no commit
was lost by any deletion (all five recovered tips resolve inside their keeper,
`git fsck --unreachable` shows zero objects dated 2026-08-10), the aborted merge
left no residue anywhere in the repository, and `verify-install.sh` PASSES at
exit 0 with 694 entries matching and nothing extra.

**STILL UNVERIFIED, in the reviewer's own words:** the full gate has not been
re-run with cap headroom, so only the single suite is known to go green, not the
whole gate; its run spanned a push so it mixed two trees; and GitHub CI on
`c29f1c0` was not checked.
