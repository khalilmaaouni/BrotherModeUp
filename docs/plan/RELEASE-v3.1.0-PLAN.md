# Release v3.1.0: goal, architecture, and the work breakdown

Status: CURRENT. Written 2026-08-10 against `main` at `2f60b11`, clean tree, in
sync with `origin/main`. No em or en dashes anywhere in this document.

Supersedes the sequencing in
`BrotherModeUp-handovers/BrotherMode-Handover-2026-08-10/04-plans/WBS-NORTH-STAR-2026-08-10.md`
for the release lane only. That document's S3 (self-poisoning gate) and S4
(version identity) are DONE and are not repeated here; its S5 architecture rows
are deferred by founder decision D5 below.

---

## 1. GOAL

One main branch, a gate that passes, and a `v3.1.0` tag whose every claim is
backed by a check that runs.

Stated as the founder would check it:

1. `git branch -r` shows `main` and nothing else.
2. `python3 tools/test_all.py` reports ALL GREEN at exit 0 on the tagged commit.
3. No sentence in `README.md` promises behaviour the shipped default does not
   perform.
4. The three defect classes that have each recurred more than once are closed by
   a machine that refuses the pattern, not by a rule in a document.
5. A model from a different family has audited the final tree, and its CRITICAL
   and HIGH findings are either fixed or published as known limits.

Anything that does not serve one of those five is out of scope and goes to the
parking lot in section 7.

---

## 2. ARCHITECTURE: what changes structurally, and why that shape

The organising principle comes from this project's own record: fixing an
instance has never once stopped a class recurring. Tests that measure the
machine were found and fixed seven times in ten days by seven different people.
Read-only commands that write were found twice by two different auditors. So
every structural item below is a MACHINE THAT REFUSES THE PATTERN, not a fix to
today's instances.

### A1. Effect classes, closing the class "read-only commands that write"

Every public command declares exactly one of five effect classes in one
registry: `pure_read`, `ledger_write`, `project_write`, `external_write`,
`destructive_external_action`.

One test enforces it: snapshot the working tree, hash the store and its sidecar
files, run every command declared `pure_read`, and fail if a single byte changed
anywhere. A command ABSENT from the registry fails the test rather than
defaulting to anything, so a new command cannot be added without a declaration.

Why a registry and not seven point fixes: seven fixes leave the eighth command
free to repeat the defect. The registry plus the purity test makes the eighth
impossible to merge.

Foundation already present: `ReadOnlyStore` exists at `tools/bm_store.py:16345`,
so the fix for most instances is a constructor swap, not new machinery.

### A2. Wall-clock lint, closing the class "tests that measure the machine"

A lint that fails CI when a test file asserts an absolute wall-clock duration
outside an approved benchmark module. Approved modules sit in one explicit allow
list, so every exception is visible in a diff rather than implied.

Why a lint and not more careful review: review caught this seven times and
prevented it zero times. `assert elapsed < 2.0` is the obvious way to write
"this should be fast" and it is wrong every time, so the only durable fix is a
machine that refuses the line.

The approved replacement shape, which the lint must NOT catch: a ratio between
two input sizes using the MINIMUM of N samples per size (noise only ever adds
latency, so the minimum is the least contaminated sample), or a deterministic
operation count, which load cannot move at all.

### A3. Live deny canary, closing the class "controls that verify a string"

The unattended preflight proves the write fence is on by reading
`BM_FENCE_MODE == "enforced"`. It never checks the hook fires. Under Codex the
hook never fires at all, so an unattended run passes all seven safety
preconditions with zero enforcement.

The replacement: before an unattended run, fire a real probe write at a path a
throwaway claim owns, and confirm the hook actually refused it. If the refusal
cannot be demonstrated, the run does not get the `verified` label.

Why this one matters more than its size: the project's founding law is that a
rule in a prompt is not a control. This is that same failure one level up,
inside the gate guarding unattended runs, which is the exact mechanism that
produced the 8 August runaway.

### A4. Two truth repairs, closing live instances of "claims that outrun code"

Not structural, but both are live and both are read by models, not only by
people. The founder's team installs by handing the repository link to their own
assistant, so a false sentence in `README.md` is EXECUTED, not merely misread.

- The single-writer guarantee in `README.md` is narrowed to what the shipped
  default performs.
- Seven shipped files cite `V3-FREEZE-2026-08-07.md`, a document that does not
  exist in the repository. Found 2026-08-10 while verifying this plan. It is in
  no prior handover, and the findings ledger records this class as FIXED, which
  is now known to be wrong.

### A5. Consolidation to one main

Fourteen remote branches besides main. Three are already fully contained in main
and hold nothing unique. Eleven carry real work. Each merges alone, with the
full gate run on the MERGED tree before the next opens, because a green branch
and a green merge are not the same claim.

### The architecture evolution path, stated so it stays visible

This release is the FOUNDATION lane. The ten-part assurance control plane from
the north-star brief (work governor, runtime capability probe, acceptance
contracts, convergence engine, reconciler, cockpit) is the NEXT program, and it
is deferred deliberately by founder decision D5, not forgotten. The reason is in
section 4: five of the eight known defect classes live in code that architecture
would keep, and a new control plane built on tests nobody can trust inherits
every one of them.

---

## 3. FOUNDER DECISIONS ON RECORD

Taken 2026-08-10 through the question windows, before any work started.

| ID | Decision | Consequence in this plan |
|---|---|---|
| D1 | Tag `v3.1.0` after all merges and a green gate | Loop 7 exists; no tag is cut from a red or unmerged tree |
| D2 | Merge one branch at a time, full gate after each | Loop 1 is a sequence of gated steps, not one merge |
| D3 | Narrow the README claim to what ships | Loop 4, and the default fence mode is NOT flipped in this release |
| D4 | Upgrade the unattended preflight to a live deny canary | Loop 5. Supersedes the earlier warn-and-allow decision, withdrawn with its reason: the founder chose the stronger option once shown the cost |
| D5 | Fix the foundation now, assurance architecture next release | Section 7 parking lot; no north-star architecture item is built here |
| D6 | Effect classes: full taxonomy plus purity test | Loop 2 builds the registry and the test, not seven point fixes |
| D7 | Wall-clock lint: CI-blocking | Loop 3 wires it into the workflow, not into a report |
| D8 | Codex cross-family audit gate before the tag | Loop 6, and unresolved CRITICAL or HIGH findings block Loop 7 |

---

## 4. DECISIONS TAKEN ON THE FOUNDER'S BEHALF

Recorded at the moment they were taken, each with the alternative considered and
what would flip it. A decision discovered later in a report is the
correction-class failure this project names.

**B1. The three already-contained branches are tagged, then deleted.**
`fix/hookperf-projection-determinism`, `fix/stranded-adopted-recovery` and
`relay7/ci-doctor-fix` each returned 0 from
`git rev-list --count origin/main..origin/<branch>`, meaning every commit
already exists on main.
ALTERNATIVE: keep them, on the theory that a branch name is documentation.
REJECTED because the founder's stated goal is one main branch and these hold
nothing unique; a name pointing at commits main already has is noise in every
future listing.
FLIP CONDITION: if any of the three holds an uncommitted stash or a note outside
git, it stays until that is extracted.

**B2. Every branch is tagged before deletion.**
An annotated tag on each tip, named `archive/<branch>-2026-08-10`.
ALTERNATIVE: delete outright, since a merge commit already contains the history.
REJECTED because the cost is one command per branch and the failure it prevents
(needing to inspect a branch in isolation after the name is gone) is expensive
and irreversible. The never-lose-work rule outranks tidiness.
FLIP CONDITION: none needed; the tags are cheap and removable later.

**B3. WITHDRAWN 2026-08-10, by its own flip condition.**
This decision said the install-truth overlap would be resolved by merging a
superset. The investigation disproved its premise: `phase-3/install-truth`
touches only `tools/bm_project_facts.py` and
`claude/jovial-tereshkova-830231` touches only `docs/QUICKSTART.md`,
`docs/RELEASE.md` and `docs/SETUP.md`. They are FILE-DISJOINT, so no line-level
conflict between them is possible, and both are needed: one fixes the generator
that emits the install command, the other fixes the prose around it. BOTH MERGE.
This is recorded rather than deleted because the sequence is the point: the
decision was made on an assumption, the assumption was checked, and the check
changed the answer.

**B4. The `phase-c/continuity` merge is rehearsed in a scratch worktree before
it touches main.**
It is the only branch that touches `tools/write_sites.json`, the reviewed
manifest that refuses unreviewed file-writing code, and it conflicts there. Main
also currently expects code this branch carries.
ALTERNATIVE: merge directly on main and fix forward.
REJECTED because the conflict includes per-file counts that must be RE-DERIVED
by running the scanner over the merged tree, never resolved by picking a side. A
carelessly resolved security manifest is how a control gets quietly broken.
FLIP CONDITION: none. This restates the recorded decision of 2026-08-10.

**B5. The default fence mode is NOT flipped to enforced in this release.**
Founder decision D3 chose narrowing the claim over flipping the default.
Recording the consequence explicitly: after this release the shipped default
still allows unclaimed paths, and shell writes still cross fences unrefused and
are detected only afterwards. That is now STATED in `README.md` rather than
contradicted by it.
FLIP CONDITION: the founder asks for it, or an outside tester loses work to an
unfenced write.

---

## 5. THE WORK BREAKDOWN

Every task names the files it touches and ends with a runnable done-check. A
task that cannot name its files is not a task and does not appear here.

Estimates are ranges with confidence. They assume no conflict beyond those
measured in Loop 0.5.

Owner column: `LEAD` means this session does it directly. `AGENT/<tier>` means a
dispatched subagent at the named model tier, with the reason stated in its own
brief. The tier is declared, never inherited by omission.

---

### LOOP 0: foundation and plan artifacts

| ID | Task | Files | Done-check | Owner |
|---|---|---|---|---|
| 0.1 | Ground map and fetch | none | `git status --short` prints nothing; `git rev-parse HEAD origin/main` prints one SHA twice | LEAD |
| 0.2 | Claim the fence for this loop | store record `release-v310-plan` | claim prints a lifecycle uuid under the session id the HOOK reports, not a hand-made one | LEAD |
| 0.3 | This plan | `docs/plan/RELEASE-v3.1.0-PLAN.md` | file exists; every loop row names a file and a done-check | LEAD |
| 0.4 | The Gantt page | `docs/plan/RELEASE-v3.1.0-GANTT.html` | opens in a browser, light and dark both render, every ticked box carries an evidence line | LEAD |
| 0.5 | Branch conflict map | none, read-only | agent returns predicted conflicts per branch with `git status --short` empty | AGENT/sonnet |
| 0.6 | Effect-class inventory | none, read-only | agent returns every public command classified with file:line | AGENT/sonnet |
| 0.7 | Wall-clock assertion inventory | none, read-only | agent returns list A, list B, list C and a recommended mechanical rule | AGENT/sonnet |

SIZE: 2 to 3 hours, HIGH confidence.

---

### LOOP 1: one main branch

Order is fixed by MEASURED conflict data from 0.5, not by preference. Every step
ends with the FULL gate on the merged tree, run with cap headroom so a busy
machine cannot manufacture a red reading.

The gate command, used identically at every step:

```
BROTHERMODE_SESSION_CAP=99 python3 tools/test_all.py
```

The cap override is legitimate and is NOT a bypass of the machine-wide session
cap: it raises the cap for the TEST PROCESS so the liveness tests can observe
headroom. The real cap governing session spawning is unchanged.

MEASURED conflict data, from `git merge-tree --write-tree origin/main origin/<b>`:

| Branch | Ahead | Predicted conflicts |
|---|---|---|
| `feature/progress-page-template` | 3 | NONE, exit 0 |
| `claude/jovial-tereshkova-830231` | 2 | CHECKSUMS only |
| `claude/practical-kowalevski-471524` | 4 | CHECKSUMS only |
| `claude/reverent-bhaskara-2c96c9` | 9 | CHECKSUMS only |
| `fix/system-projects-excluded-from-project-counts` | 1 | CHECKSUMS only |
| `phase-6/findings-ledger` | 3 | CHECKSUMS only |
| `phase-3/install-truth` | 3 | CHECKSUMS, `tools/bm_project_facts.py` |
| `claude/laughing-engelbart-4ba095` | 5 | CHECKSUMS, `tools/test_bm_bash_audit.py` |
| `phase-5/progress-view` | 7 | CHECKSUMS, `tools/test_bm_store.py` |
| `claude/charming-goldwasser-6d8423` | 2 | 6 files including `tools/bm_store.py` and `tools/bm_bash_audit.py` |
| `phase-c/continuity` | 7 | 5 files including `tools/write_sites.json` and an add/add on `tools/bm_continue.py` |

`CHECKSUMS.sha256` is GENERATED. It conflicts on all eleven and is never
hand-merged: it is regenerated after the merge, and regenerated once more, last,
in step 7.1.

| ID | Task | Branch | Done-check | Owner |
|---|---|---|---|---|
| 1.1 | Tag and delete the three contained branches | `fix/hookperf-projection-determinism`, `fix/stranded-adopted-recovery`, `relay7/ci-doctor-fix` | `git branch -r` count drops by 3; each archive tag resolves with `git rev-parse` | LEAD |
| 1.2 | Rehearse `phase-c/continuity` in a scratch worktree, re-deriving `write_sites.json` with the scanner | scratch copy only | `python3 tools/test_brothermode_cli.py` in the scratch copy goes from 11 failures to OK. If it does not, STOP: the tests were landed ahead of the implementation and that is a separate defect | LEAD |
| 1.3 | Merge `phase-c/continuity` | as above | full gate ALL GREEN on the merged tree | LEAD |
| 1.4 | Merge the bash-audit family, three branches, gated once | `claude/laughing-engelbart-4ba095`, `claude/charming-goldwasser-6d8423`, `fix/system-projects-excluded-from-project-counts` | full gate ALL GREEN; and `bash scripts/verify-install.sh` exits 0 AFTER a synthetic alert is raised | LEAD |
| 1.5 | Merge `claude/practical-kowalevski-471524`, write-on-help | as above | full gate ALL GREEN; `bm_store dashboard --help` changes zero bytes | LEAD |
| 1.6 | Merge `claude/reverent-bhaskara-2c96c9`, the design amendment | as above | full gate ALL GREEN. MUST land before 1.7 | LEAD |
| 1.7 | Merge `phase-5/progress-view` and `feature/progress-page-template` together | as above | full gate ALL GREEN; the generated progress page renders | LEAD |
| 1.8 | Merge BOTH install-truth branches (disjoint, per B3) | `phase-3/install-truth`, `claude/jovial-tereshkova-830231` | full gate ALL GREEN; `python3 tools/test_bm_docs.py` OK | LEAD |
| 1.9 | Merge `phase-6/findings-ledger` | as above | full gate ALL GREEN | LEAD |
| 1.10 | Tag and delete all eleven merged branches | remote refs | `git branch -r \| grep -v HEAD` returns `origin/main` alone | LEAD |

SIZE: 1 to 2 attended days, MEDIUM-HIGH confidence.

UNVERIFIED and named as such: whether the branches conflict with EACH OTHER.
0.5 measured each against main only. Four branches touch `tools/bm_store.py` and
three touch the bash-audit pair, so pairwise collisions are possible. The
sequential order plus a gate after each is what surfaces them one at a time
instead of all at once.

RISK: step 1.3 touches session spawning, the blast radius of the 8 August
runaway. It gets read line by line, not skimmed.

---

### LOOP 2: effect classes (closes Class F)

| ID | Task | Files | Done-check | Owner |
|---|---|---|---|---|
| 2.1 | Write the registry: five classes, one declaration per public command | `tools/bm_effects.py` (new) | importing it prints the full command count; a command missing from it is an error, not a default | LEAD designs, AGENT/sonnet fills |
| 2.2 | Write the purity test RED FIRST, so it fails against today's code | `tools/test_bm_effects.py` (new) | the test FAILS naming at least `bm_threads dashboard --help`, and that failure output is quoted before any fix is written | AGENT/sonnet |
| 2.3 | Route every `pure_read` command through `ReadOnlyStore` | `tools/bm_project.py`, `tools/bm_learn.py`, `tools/bm_docs.py`, `tools/bm_threads.py`, `tools/bm_sentinel.py`, `tools/bm_fence_hook.py` | `python3 tools/test_bm_effects.py` OK, run AFTER the last edit | AGENT/sonnet |
| 2.4 | Central pre-dispatch help gate, so `--help` never reaches a command body | `tools/bm_threads.py` plus any module the inventory names | `--help` on every module changes zero bytes, asserted by 2.2's test | AGENT/sonnet |
| 2.5 | Reclassify `brothermode_cli update` as `external_write`, and say so in its help | `tools/brothermode_cli.py` | its help text names the network call; the registry agrees | LEAD |
| 2.6 | Independent refute pass over 2.1 to 2.5 | none, read-only | the reviewer names a command the registry misclassifies, or states plainly that it could not | AGENT/opus |

SIZE: 1 to 1.5 days, MEDIUM confidence. Variance is in how many commands the
inventory finds; the fix per command is small.

GATE: nothing here merges until 2.2's test has been seen RED and then GREEN, in
that order, with both outputs quoted.

---

### LOOP 3: wall-clock lint (closes Class A)

| ID | Task | Files | Done-check | Owner |
|---|---|---|---|---|
| 3.1 | Write the lint as an AST walker with an explicit benchmark allow list | `tools/bm_lint_walltime.py` (new) | against a fixture holding one known-bad and one known-good pattern, it flags exactly the bad one | AGENT/sonnet |
| 3.2 | Calibrate BOTH ways against real code | `tools/test_bm_lint_walltime.py` (new) | it flags every entry on inventory list A, and flags NOTHING on list B. Both directions asserted | AGENT/sonnet |
| 3.3 | Run it tree-wide and fix or visibly exempt every hit | whatever files it names | `python3 tools/bm_lint_walltime.py tools/ scripts/` exits 0 | AGENT/sonnet |
| 3.4 | Wire it into CI as a BLOCKING step | `.github/workflows/tests.yml` | the workflow names the lint, and a deliberately reintroduced bad line fails the job | LEAD |
| 3.5 | Add it to the local gate | `tools/test_all.py` | `python3 tools/test_all.py` includes the lint in its suite count | LEAD |

SIZE: half a day to 1 day, MEDIUM-HIGH confidence.

CALIBRATION RULE, and it decides whether this lint survives contact: a lint with
false positives gets disabled by the first person it annoys. 3.2's both-ways
calibration is not optional and the loop does not close without it.

---

### LOOP 4: truth repairs (closes two live Class C instances)

| ID | Task | Files | Done-check | Owner |
|---|---|---|---|---|
| 4.1 | Release the stuck fence on README.md | store record `unit-u-phase3-install-truth` | the fence hook allows a write to README.md | LEAD |
| 4.2 | Narrow the single-writer claim to what ships | `README.md` near line 48, `SKILL.md` near line 120 | the sentence states: claimed paths refused, unclaimed paths allowed by default, shell writes audited not blocked. `python3 tools/test_bm_docs.py` OK | LEAD |
| 4.3 | Remove or resolve every citation of the non-existent `V3-FREEZE-2026-08-07.md` | `tools/brothermode_cli.py`, `product.identity.json`, `tools/write_sites.json`, `tools/test_bm_e2e_pins.py`, `tools/test_all.py`, `tools/test_bm.py`, `tools/test_brothermode_cli.py` | `grep -rn "V3-FREEZE-2026-08-07" . --exclude-dir=.git` returns nothing outside handover archives | AGENT/sonnet |
| 4.4 | Correct the findings-ledger row that marks this class FIXED | `docs/evidence/final-close/FINDINGS-LEDGER.md` | the row reads OPEN with today's evidence, or a new dated ledger records the correction | LEAD |
| 4.5 | Widen the docs drift suite: a security verb with no nearby test reference fails | `tools/test_bm_docs.py` | reintroducing "refuses" with no test citation fails the suite | AGENT/sonnet |

SIZE: half a day, HIGH confidence, except 4.5 which is MEDIUM because the
false-positive surface on English prose is real.

---

### LOOP 5: live deny canary (closes Class D)

| ID | Task | Files | Done-check | Owner |
|---|---|---|---|---|
| 5.1 | Write the canary: claim a throwaway path, attempt a write through the REAL hook path, assert refusal, release | `tools/bm_controller.py` near `_unattended_fence_mode` | the canary returns PROVEN on Claude Code with the hook installed | LEAD |
| 5.2 | Make its outcomes distinct: PROVEN, NOT-PROVEN, HOOK-ABSENT | same | all three states reachable in tests, each asserted separately | LEAD |
| 5.3 | Refuse the `verified` autonomy label unless the canary returns PROVEN | `tools/bm_controller.py` | `python3 tools/test_bm_controller.py` OK, including a new test that forces NOT-PROVEN and asserts refusal | LEAD |
| 5.4 | Enter the canary through the RUNTIME's own path, not by calling the function | `tools/test_bm_controller.py` | at least one test invokes it as a real process, with real stdin and a real environment | LEAD |
| 5.5 | State the Codex position honestly in the runtime docs | `docs/RUNTIMES.md`, `docs/KNOWN-LIMITS.md` | the page says Codex exec PreToolUse is MEASURED unsupported, not "unverified until you rehearse it" | LEAD |

SIZE: half a day to 1 day, MEDIUM confidence.

WHY 5.4 IS ITS OWN ROW: this project already shipped nine green tests that all
called a function directly while the defect lived one level upstream, in the
code path the runtime actually enters. For any behaviour a runtime invokes, at
least one test must invoke it the way the runtime does.

---

### LOOP 6: cross-family audit

| ID | Task | Files | Done-check | Owner |
|---|---|---|---|---|
| 6.1 | Confirm Codex is alive, record its version | none | `codex exec "reply with exactly: CODEX_ALIVE"` returns `CODEX_ALIVE` at exit 0; `codex --version` recorded beside it | LEAD |
| 6.2 | Run a read-only Codex audit on the fully merged tree | none | raw output saved VERBATIM to `docs/evidence/v3.1.0/codex-audit-2026-08-10.md` | LEAD drives Codex |
| 6.3 | Triage every finding: FIXED, PUBLISHED as a limit, or OPEN with a reason | `docs/evidence/v3.1.0/audit-ledger.md` | every finding carries a disposition, and every FIXED row cites a file read fresh, never a commit message alone | AGENT/opus |
| 6.4 | Fix every CRITICAL and HIGH, or publish it as a known limit | varies by finding | zero unresolved CRITICAL or HIGH, and the count is quoted | LEAD |

SIZE: half a day plus whatever the findings cost. LOW confidence on the total,
because an audit's output size is not predictable. That is the point of running
one.

BLOCKING RULE, per D8: an unresolved CRITICAL or HIGH blocks the TAG. It does
not block the merges.

---

### LOOP 7: release v3.1.0

| ID | Task | Files | Done-check | Owner |
|---|---|---|---|---|
| 7.1 | Regenerate the checksum manifest LAST, after every other edit, with new files staged first | `CHECKSUMS.sha256` | `bash scripts/verify-install.sh` exits 0, nothing missing and nothing extra | LEAD |
| 7.2 | Set the release version in all three places | `VERSION`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | all three read `3.1.0`; the release-truth suite passes | LEAD |
| 7.3 | Update the changelog from real commits | `CHANGELOG.md` | every entry maps to a commit on main | LEAD |
| 7.4 | Full gate ALL GREEN on the exact commit to be tagged | none | `BROTHERMODE_SESSION_CAP=99 python3 tools/test_all.py` prints ALL GREEN at exit 0, with the SHA recorded beside it | LEAD |
| 7.5 | CI agrees on that same commit | `.github/workflows/` | the GitHub run for that exact SHA is green. A CI result belongs to ONE commit | LEAD |
| 7.6 | FOUNDER GATE: cut and push the tag | `v3.1.0` | founder confirms in the moment, then `git tag -a` and `git push origin v3.1.0`, verified with `git ls-remote --tags` | FOUNDER, then LEAD |

SIZE: 2 to 4 hours, HIGH confidence, assuming 7.4 is green on the first run.

FOUNDER GATE, unconditional: a tag is a release. It is not cut without an
explicit yes in the moment, whatever this plan says.

---

## 6. SEQUENCING AND LANES

At most two lanes at once, one loop per lane, and a loop closes before the next
opens in that lane. Closing means three things: the done-check was run after the
last edit and quoted, every change recorded as needed in another file was
applied by name, and the evidence was filed.

```
LANE A: the tree              LANE B: the machinery
------------------------------------------------------
             LOOP 0  foundation, both lanes wait
                      |
   LOOP 1  one main        LOOP 3  wall-clock lint
        |                       |
   LOOP 2  effect classes   LOOP 4  truth repairs
        |                       |
        +------> LOOP 5  live deny canary <------
                      |
              LOOP 6  cross-family audit
                      |
              LOOP 7  release        FOUNDER GATE
```

Why Loop 3 and Loop 4 sit in the other lane: neither touches the files Loop 1
merges. Loop 3 writes two new files plus the CI workflow. Loop 4 writes README,
SKILL and the docs suite. The only overlaps are `tools/write_sites.json` and
`CHECKSUMS.sha256`, both GENERATED, so both lanes regenerate rather than
hand-merge, and the final regeneration happens once, last, in 7.1.

Why Loop 5 waits for both lanes: it edits `tools/bm_controller.py`, and Loop 1
merges branches that touch neighbouring machinery. Running it earlier would put
two writers near one file.

---

## 7. THE PARKING LOT: what is deliberately NOT in this release

Each item serves the north star. None is dropped. All are deferred by founder
decision D5, and they are named here so the deferral is a decision on the record
rather than a silence.

| Item | North star objective it serves | Why not now |
|---|---|---|
| Work governor owning budget, leases, concurrency, retries | bounded autonomy | Needs the trustworthy gate this release builds |
| Runtime capability probe with a signed receipt and three modes | independent proof | Loop 5's canary is its first brick; the rest follows |
| Acceptance contract frozen before implementation | verified deliverable | New surface, not a defect fix |
| Independent verifier with an information boundary | independent proof | Practised by hand today; automating it is a program |
| Convergence engine that appends tasks rather than reporting gaps | verified deliverable | Depends on acceptance contracts |
| Reconciler for stranded state | recoverable state | Depends on leases |
| Preview lane: boot in worktree, E2E, screenshots | verified deliverable | Largest single item in the brief |
| Cockpit generated from ledger events | review-ready | Loop 1.7 lands the generator; the event model is next |
| Memory retrieval evaluation on a labelled corpus | verified deliverable | Explicitly gated on the corpus existing |
| Growing the benchmark past its current tasks | the whole north star | Real calendar work, and the `reset-token` task's hidden test is known broken |
| Ten external builders, thirty external work items | external proof | Needs people and calendar, not code |

---

## 8. THE RISKS I AM ACTUALLY WORRIED ABOUT

Bad news first, stated before the work rather than after it.

1. **The gate takes minutes and Loop 1 runs it eight times.** If a merge goes red
   the cost of bisecting is another gate run per hypothesis. MITIGATION: the
   scratch rehearsal in 1.2 catches the merge most likely to go red before it
   lands.

2. **`tools/write_sites.json` is a security manifest with a conflict in it.**
   Resolving it by picking a side silently weakens the control. MITIGATION: it
   is re-derived by running the scanner, and the resolution is read by an
   independent reviewer before the merge lands.

3. **Four branches touch `tools/bm_store.py` and three touch the bash-audit
   pair.** Pairwise conflicts between them are UNMEASURED. MITIGATION: strictly
   sequential merges with a gate after each, so a collision surfaces alone.

4. **The purity test cannot be airtight.** A command that writes only under a
   condition the test does not trigger will still pass. MITIGATION: the test is
   a FLOOR, not a proof, and this plan says so rather than claiming otherwise.
   The registry's real value is that a new command cannot be added silently.

5. **An audit's findings are unbounded.** Loop 6 could return three findings or
   thirty. MITIGATION: only CRITICAL and HIGH block the tag; the rest is
   published as a known limit, which is this project's existing honest pattern.

6. **This session could run out of context before Loop 7.** MITIGATION: the
   handover is raised while there is still room to write it properly, and every
   closed loop files its evidence on disk immediately rather than at the end.

---

## 9. WHAT THIS PLAN DOES NOT KNOW

Stated because leaving it unsaid would be the failure to disclose this project
names.

- Whether the eleven branches conflict with EACH OTHER. 0.5 measured each against
  main only.
- Whether merging `phase-c/continuity` actually turns the eleven currently
  failing CLI tests green. Nobody has run it. Step 1.2 exists to find out before
  it touches main.
- How many commands the effect-class inventory will find. The registry's size is
  unknown until 0.6 returns.
- Whether the Codex audit will find something that changes the release scope. By
  construction it might, which is why it runs before the tag and not after.

---

# REPLAN, 2026-08-10 evening, written against `main` at 88b79d2

This section SUPERSEDES sections 5 and 6 above for sequencing. Those are left
as written, because the difference between what was planned and what the
measurement forced is the useful record.

## What the original plan got wrong, and it was the biggest item in it

LOOP 1 was eleven gated merges over one to two attended days. It became ZERO
merges and about three hours, because merging each branch in a throwaway
worktree and diffing the result against main showed main already held the
outcome of all fourteen. Four of them would have made main WORSE. The plan was
not merely over-sized; its central assumption was false, and only measurement
found that. An independent reviewer on the strongest tier was then briefed to
destroy the finding and refuted none of it.

The lesson worth carrying: a merge plan built from branch NAMES and commit
SUBJECTS is a guess. `git merge-tree --write-tree` against the target, then a
diff of the result, is the measurement. It costs minutes.

## Where the program actually stands

| Loop | State | Evidence |
|---|---|---|
| 0 foundation | CLOSED | plan, page, three inventories |
| 1 one main branch | CLOSED | `git ls-remote --heads origin` returns 1; 14 archive tags pushed before any delete |
| 3 wall-clock lint | CLOSED | lint blocking in CI; `bm_lint_walltime.py tools/ scripts/` exit 0 |
| P progress-page check | CLOSED, added on founder directive tonight | runs at every session start, fails open, proven byte-pure |
| 4 truth repairs | 2 of 5 | stuck README fence released; decision records now ship |
| 2 effect classes | IN FLIGHT | registry plus purity test landing RED first, by design |
| 5 live deny canary | NOT STARTED | |
| 6 cross-family audit | NOT STARTED | |
| 7 release tag | NOT STARTED, founder gate | |

Gate at 88b79d2: `test_all: 2918 tests across 29 suites, 9 skipped, 307.8s
wall. ALL GREEN`, exit 0, clean tree.

## The honest question for tonight, and my recommendation

Four items remain before a tag is defensible. Three are safe to do tonight.
ONE IS NOT, and saying so is the point of this section.

SAFE TONIGHT:
- Loop 2, effect classes. Its inventory is done, the fixes are constructor
  swaps to an existing `ReadOnlyStore`, and a purity test proves each one.
- Loop 4's remaining three. Documentation and a test widening, all reversible.
- Loop 6, the Codex audit. Read-only by construction, and it runs against
  whatever tree exists when it starts.

NOT SAFE TONIGHT, and this is a recommendation against a choice the founder
already made:
- Loop 5, the live deny canary. It edits `tools/bm_controller.py`, the
  unattended-run preflight. That is the exact mechanism behind the 8 August
  runaway, in which forty sessions and 6.4 million output tokens ran unattended
  because a stop condition existed in prose and not in code. Editing that
  preflight late at night, at the end of a long session, to ship the same
  night, is the shape of the incident rather than the cure for it. The defect
  it closes is real but it is DISCLOSED and BOUNDED today: the founder's own
  recorded decision of 2026-08-10 was warn-and-allow, and the relay brake plus
  the machine-wide session cap bound the blast radius independently.

RECOMMENDATION: tag `v3.1.0` tonight WITHOUT Loop 5, and publish the
unattended-preflight gap in `docs/limits/CURRENT.md` as a named known limit
with its flip condition, exactly as this project already does with every other
limit it has not closed. Loop 5 opens the next session, attended, as its own
first item.

ALTERNATIVE CONSIDERED: do Loop 5 tonight anyway, since the founder chose the
stronger option when shown the cost. REJECTED for tonight only, not on the
merits: the decision to build it stands, only its timing moves. A control
built tired, on the one file whose failure mode is unattended runaway, is worse
than a disclosed gap.

FLIP CONDITION: the founder says ship it tonight. Then it is built, and it gets
the full gate plus an independent refute pass before the tag, and the tag waits
for both however late that is.

## Sequencing for tonight

Two lanes, as always, and the tag is last.

```
LANE A                          LANE B
Loop 2 registry, RED            Loop 4 remaining three
Loop 2 fixes, GREEN                     |
        |                               |
        +--------- full gate -----------+
                    |
            Loop 6 Codex audit
                    |
            triage: zero unresolved CRITICAL or HIGH
                    |
            Loop 7 tag            FOUNDER GATE
```

SIZE, ranges with confidence, assuming no new defect class appears:
- Loop 2 to green: 1 to 2 hours, MEDIUM confidence. Variance is in how many
  commands the completeness test discovers that nobody has classified.
- Loop 4 remaining: 45 to 90 minutes, HIGH confidence.
- Loop 6 audit plus triage: 1 to 3 hours, LOW confidence, because an audit's
  output size is not predictable. That is the point of running one.
- Loop 7: 30 to 45 minutes, HIGH confidence, assuming the gate is green first
  time.

TOTAL: 3.5 to 7 hours of work. The LOW-confidence item is the audit, and it is
the one that could push a tag past tonight. If it does, the honest move is to
tag tomorrow rather than to tag around it.

## What still will not be true after tonight, whatever happens

Stated here so the tag does not imply it. No BrotherMode capability has reached
external verification. Nobody has counted whether this product makes work
better, faster or more reliable than working without it. Ten outside builders
and thirty externally attempted work items need people and calendar, not code.
Until that exists, the defensible claim remains the narrow one: this is the
agent layer that publishes the defects its own checks found in itself.

## FOUNDER OVERRIDE, 2026-08-10 evening, recorded at the moment it was taken

The recommendation immediately above was to tag tonight WITHOUT Loop 5 and
publish the unattended-preflight gap as a known limit. The founder was shown
that recommendation with its reasoning, including the comparison to the 8
August incident, and chose the OTHER option: BUILD LOOP 5 TONIGHT, AND TAG
AFTER IT PASSES.

That is now the plan. The recommendation is left above rather than deleted,
because a recommendation quietly removed after it was overruled is how a
project loses the ability to tell whether its advice was any good.

CONSEQUENCES ACCEPTED, stated so they are not discovered later:
- Tonight probably does not end with a tag. The founder was told this in the
  option text and chose it anyway.
- Loop 5 gets the FULL treatment its risk deserves, not a fast version: the
  complete gate on the merged tree, plus an independent refute pass on the
  strongest tier before the tag, and the tag waits for both however late.
- The founder also confirmed that an unresolved CRITICAL or HIGH from the Codex
  audit HOLDS the tag, even if that means tagging tomorrow.

WHAT WOULD HAVE CHANGED MY RECOMMENDATION, recorded because it is the useful
part: if the canary could be built without touching the unattended preflight
itself, the timing objection would mostly disappear. It cannot; the whole point
is to replace what that preflight checks.
