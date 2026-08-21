Status: CURRENT. Written 2026-08-22 02:4x JST by the planning session (fence label
bm1-a4ba8509, record overnight-plan-session0bb03d4d), which wrote no product code.
Supersedes, for the purpose of ordering the next unattended run, the ordered work
list in docs/handover/2026-08-21-reachability-round/07-NEXT-SESSION-PROMPT.md.
That list's chosen round (M22, M18, M26) is NOT cancelled: it moves behind the
team's items by the founder's 2026-08-22 instruction, recorded below as decision
OV-1 with its flip condition.

# The overnight WBS, 2026-08-22: the team's remaining complaints first

NAMING: both product repositories are PUBLIC. Roles only (the adopter team, the
analyst lead, the engineering lead, the delivery lead, the QC lead, the
non-developer reviewer, the senior reviewer). No client name, no person's name.

## 1. Where we stand, verified tonight against code, not against a plan

Heads read at planning time: this repository `abcda6d` (main, clean, pushed);
the sibling `12d54fa` (main, 150 commits ahead of its `origin/main` at
`1742d71` of 2026-08-18; every commit mirrored on a backup branch, three of the
newest not yet). Newest PUBLIC tag in the sibling: `v3.2.0`, both local and
remote (`git tag --sort=-creatordate | head -1`, `git ls-remote --tags origin`).

THE ONE SENTENCE THAT MATTERS: seven of the fourteen problems the team raised
are closed in the sibling's source, and not one of those fixes has reached the
team, because nothing newer than v3.2.0 has been tagged and the tag is blocked
behind a red gate battery, a history decision, and a branch ruleset. Finishing
the team's list therefore has a critical path that no amount of overnight
coding shortens on its own (section 3).

### The team's items, one row each, status as measured 2026-08-22

Legend: CLOSED means landed in source with the commit named, NOT shipped.
PARTIAL names the missing half. OPEN quotes the absence check. NO-DATA means the
check could not reach a verdict. Commands were run by a read-only scout at
`12d54fa` and re-read by the planning session; the decisive output is quoted.

| id | raised by | tool | status | evidence (command, decisive output) | landed |
|---|---|---|---|---|---|
| ship-to-reviewers | the whole team (they reviewed a build generations behind source) | SBE | OPEN | newest tag v3.2.0 local and remote; `git rev-list --count origin/main..HEAD` = 150 | - |
| p14-sol2-green-scope | the analyst lead, the QC lead | SBE | CLOSED | `tools/sbe_gate.py:2076` UNEXAMINED_CLASSES tuple, `:2266` prints them into the report | 8873730 |
| p6-receipt-provenance | the engineering lead | SBE | CLOSED | `tools/sbe_gate.py:112` imports producer_class from sbe_passport.py; 5 test files cover it | 0340115 |
| p7-owed-checks (reverse) | the engineering lead | SBE | CLOSED | `gate_proof` reads BEHAVIOUR_TABLE and RAN_RECEIPT, FAILs on a Proof cell citing a check no receipt records | 0340115 |
| A0 / D4 exception owner and expiry | precondition on p6, p7, p3 | SBE | CLOSED in SBE source; the queue row D4 here still reads queued | `tools/sbe_design.py:3172-3177` `_owner_expiry` refuses an exemption naming only one of owner: and expires: | 25d7128 |
| p11-prove-rename | the delivery lead | SBE | CLOSED | `src/brothersbe/cli.py:1234-1250` `_cmd_verify` docstring states what converge actually checks at T2 and above | 44ef6d9 |
| p8-tier-split | the senior reviewer | SBE | CLOSED (2026-08-15) | recorded in the re-extraction as finalized | 4912bd8 |
| p9-behaviour-table, p14-testkit | the analyst lead | SBE | CLOSED in source | recorded in the re-extraction as finalized, awaiting ship-to-reviewers | - |
| escalation-finish | the founder's own ask | BM | CLOSED | `tools/bm_effects.py:623` carries the bm_escalate.py entry; `python3 tools/test_bm_effects.py` prints `Ran 10 tests ... OK` (run 2026-08-22) | 15c7864 |
| p12-bitbucket-sbe-leg | the whole team | SBE | PARTIAL | bitbucket-pipelines.yml, bbprverify.py, bbstatus.py, prverify.py all exist (both legs coded); `grep -n 'read-only\|UNVERIFIED' docs/BITBUCKET.md` = 0, the doc does not state that the live run is blocked by the seat limit | - |
| H5-post-merge-outcome | the gap hunt | SBE | PARTIAL | `src/brothersbe/lifecycle.py:457-458,545,549` rollback and incident fields feed reduce_verified_reality; `grep -n 'def.*rollback\|def.*incident' src/brothersbe/cli.py` = 0, nothing writes them | - |
| H9-fence-registry-rot | the gap hunt | SBE | PARTIAL | `python3 tools/sbe_fence_hook.py fences`: 77 lines, 15 "no readable" (35 on 2026-08-17), 60 enforceable | - |
| reality-command (the sibling's chosen round) | the product's own promise | SBE | PARTIAL | `sbe --help` has no reality verb; reduce_verified_reality has 0 callers outside lifecycle.py and its test | - |
| p5-wall-of-text | the non-developer reviewer | SBE | OPEN | `python3 bin/sbe status --help`: flags are --cwd, --team, --base, --json; no short or long form | - |
| p3-clarify-enforcement | the analyst lead | SBE | OPEN | `grep -rn 'discussion\|clarif' src/brothersbe tools/*.py`: 0 real hits (two unrelated comments) | - |
| p4-decisions-harvest | the engineering lead, the senior reviewer | SBE | OPEN | `grep -n 'def ' src/brothersbe/decisions.py`: no harvest or collect function; record_from_run reads only a live run's own text | - |
| H7-reviewer-concentration | the gap hunt | SBE | OPEN | `grep -n 'concentration\|holds\|count' src/brothersbe/reviewroute.py`: no count of holdings | - |
| H8-opened-closed-pair | the gap hunt | SBE | OPEN | `grep -n 'opened_at\|closed_at' src/brothersbe/*.py` = 0; only per-command durations in evidence.py | - |
| H4-defect-origin | the gap hunt | SBE | OPEN | `grep -n '\borigin\b' tools/sbe_intake.py` = 0 | - |
| H2-accepted-state | the gap hunt (B1 in the sibling's day plan) | SBE | OPEN | `grep -n 'acceptingParty\|accepted_by\|acceptedBy' src/brothersbe/*.py` = 0; only a predeclared-behaviour bool | - |
| H6-requirement-found-in-build | the gap hunt | SBE | OPEN | stale and supersede hits are all approval staleness (bbstatus.py, book.py, handover.py), none about a sheet | - |
| H3-deployed-ref-drift | the gap hunt | SBE | OPEN | `grep -n 'deployed\|running_ref' src/brothersbe/observation.py` = 0; contracts bind to headCommit only | - |
| p10-p13-requirement-drift | the engineering lead, the analyst lead | both | OPEN, T3 | `grep -n 'design_version\|supersedes' src/brothersbe/*.py tools/sbe_design.py` = 0 | - |
| p1-windows-first-run | the non-developer reviewer | both | BM: decided, refused by design (docs/KNOWN-LIMITS.md:102, WSL is the path). SBE: the Windows round sits in pull requests 50 and 55, both OPEN and conflicted (`gh pr view`, 2026-08-22) | - |
| C2, C3, C4 (the Windows and publish round) | the engineer who tested | SBE | OPEN, unlanded | pull requests 50, 55, 56 all state OPEN, mergedAt null | - |
| p2-ba-guide-wrong | the analyst lead | SBE | NO-DATA | `find docs -iname '*analyst*'` and `grep -rln 'full specification' docs/*.md` both return nothing; no dedicated guide file located, so fixed or unfixed cannot be judged without locating the text the complaint quotes | - |
| p5-stale-status | the senior reviewer | SBE | PARKED | NOT REPRODUCED; needs one reviewer's exact commands and both outputs | - |
| p12-certification | the whole team | SBE | BLOCKED | the test workspace is read-only past its seat limit; only the owner can free a seat | - |
| H1-queue-baseline | the delivery lead | reveal only | BLOCKED | needs a tracker export the owner must supply; the five values are on record | - |

### The sibling's gate battery, the thing the tag waits on

Six suites red at `ad1767c`, re-measured there after the last fix landed and not
re-measured since (the sibling's day plan, lines 234 to 300): `tools/test_sbe.py`
(1, the private-name HISTORY test, no edit can reach it), `tools/test_sbe_book.py`
(1, possibly environmental: needs the `claude` CLI on PATH), `tools/test_sbe_interop.py`
(3, self-consistency drifts), `tools/test_sbe_sandbox.py` (2, stale quoted CLI output),
`tools/test_sbe_discover.py` (1, names `tools/sbe_sessionstart.sh` which does not
exist), `tools/test_stall_detector.py` (1, reads this machine's disk instead of the
fixture's). Four of the six are in the canonical gate list. The sibling's live board
adds seven eval regressions and reads: the battery stops at command 4 of 52.

## 2. Which north star stage each item serves

ship-to-reviewers: release. p5, p3, p2, H4, H6: human intent. p4, H7: accountability.
p6, p7, p14, D4, p12 docs: evidence integrity and required proof. H2: human decision.
H3: production observation. H5, H8, reality-command, H1: verified reality. p10/p13:
evidence integrity. An item that cannot name a stage is parked, not started.

## 3. The critical path: nothing reaches the team until three things happen

1. The sibling's gate battery is green, or every remaining red is WAIVED BY NAME
   with an owner and an expiry (the sibling's own exception rule, D4). Tonight's
   fix band is scoped in section 4, item S1. The private-name history failure is
   NOT fixable by code: it is founder decision SBE-1 below.
2. Main is pushed past the branch ruleset, which wants the local-gates status
   posted. No cloud compute is involved; Actions stay off.
3. A new tag is cut and the two lead reviewers receive the note naming P9 and P14.
   The tag is the founder's hand (gate G6 of the sibling's program). The run
   prepares everything up to that hand and stops.

Without step 3, every closed row above stays invisible to the team, which is why
the fix band outranks every new feature tonight, including the rounds both
repositories had chosen before this instruction.

## 4. The work breakdown, in priority order

One unattended session, opened in the sibling's canonical path, because that is
where every code item on the team's list lives. This repository's lane is small
and is section 4c. Two lanes at most, FINISH FIRST, one writer per file, three
writers concurrent at most in disjoint fences, every writer in a pinned worktree
returning a delta the orchestrator re-verifies in the main tree.

Tier legend, per the consumption cap: the orchestrator (strongest tier) briefs,
judges, drift-checks, re-runs every done-check in the main tree, and never
bulk-writes. Writers: sonnet, effort high (brothersbe:implementation-worker or
brothermode:builder). Scouts: haiku (brothermode:fast-worker is pinned medium,
which is inside the cap). Nothing above effort high: the brothermode:navigator
and :reviewer definitions pin xhigh and are NOT used unless the founder
readjusts in his own words. The cross-family gate is `codex exec --sandbox
read-only`, which is not a Claude tier and is run once per band close.

Forecast basis: `python3 tools/bm_forecast.py calibrate` prints
`clock=agent basis=judged n=14 median=2.24` (the board's correction) and
`clock=any basis=any n=17 median=1.39`. Estimates below are AGENT minutes as
briefed; the actual-minutes range applies both multipliers. Wall time assumes
two to three writers in parallel and adds the orchestrator's own gates.

### 4a. Lane S, the sibling: MUST, in this order

| # | item | what closes it | files (sibling) | writer | est agent min | done-check, run by the orchestrator in the main tree after the last edit |
|---|---|---|---|---|---|---|
| S0 | open | detect live sessions by commits, records and processes (a board refresh and seven open tasks were live at 23:55 on 2026-08-21); read the 2026-08-21 pack; registry lanes opened; base sha pinned; budget read from ~/.claude/spend-guard.json | none | orchestrator | 20 | `git rev-parse HEAD` equals `git ls-remote origin refs/heads/backup/main-unpushed-2026-08-19` or the difference is named before any write |
| S1a | fix band: discover | the session-start hook test names a file that exists | tools/test_sbe_discover.py, or the missing shell wrapper | sonnet | 15 | `python3 tools/test_sbe_discover.py` prints OK; the pre-fix assertion quoted red first |
| S1b | fix band: interop | three self-consistency drifts (the documented CLI command list, 8 guarantee sections against 7 expected, a renamed test) | tools/test_sbe_interop.py, docs/INTEROPERABILITY.md, src/brothersbe/cli.py | sonnet | 45 | `python3 tools/test_sbe_interop.py` OK; each of the three quoted red then green |
| S1c | fix band: sandbox | re-run the walkthrough and re-quote real CLI output; never edit prose toward a remembered output | tools/test_sbe_sandbox.py, the sandbox walkthrough doc | sonnet | 45 | `python3 tools/test_sbe_sandbox.py` OK; the doc's quoted block matches a fresh run |
| S1d | fix band: stall detector | the test becomes hermetic (fixture disk, not the machine's); the two disk floors (8 GiB pre-seal, 15 GiB in the detector) reconciled to one, recorded as a decision | tools/test_stall_detector.py, tools/stall_detector.py | sonnet | 45 | `python3 tools/test_stall_detector.py` OK on a machine with under 15 GiB free (this one has 12) |
| S1e | fix band: the seven eval regressions | each regression either fixed or waived by name with owner and expiry | evals/, per the regression list the battery prints | sonnet | 90 | `python3 evals/run_evals.py --strict` prints 0 regressions, or names each waived one |
| S1f | fix band: book | NOT fixed tonight: the suite needs the `claude` CLI on PATH, which this machine lacks; recorded as NO-DATA environmental, never as a bug and never as green | none | orchestrator | 0 | the battery log names it NO-DATA with the reason |
| S1g | fix band: the history test | NOT fixable by code; waits on founder decision SBE-1; the battery either carries it as the one named red or as a named waiver once he decides | none | orchestrator | 0 | the battery log names it and the decision it waits on |
| S2 | p5-wall-of-text | `sbe status` prints a short form by default, the long form behind one flag; porting this repository's status-view rule | src/brothersbe/status.py (single holder rule: one lane), src/brothersbe/cli.py | sonnet | 45 | short form under 25 lines on the sibling's own repo; `--long` (or the chosen name) prints today's output byte for byte; status suite OK |
| S3 | H7-reviewer-concentration | the route prints, beside each chosen reviewer, the count of open changes that person already holds | src/brothersbe/reviewroute.py, its test | sonnet | 45 | route three changes to one reviewer, the third prints a count of three (the queue's own done_check) |
| S4 | H8-opened-closed-pair | every change records opened-at and closed-at; a report prints median duration per tier or NO-DATA | src/brothersbe/lifecycle.py (one lane at a time), contracts if the schema grows, tests | sonnet | 60 | a fixture prints a median duration for T1 and NO-DATA for T3 |
| S5 | H5 writer | a CLI verb records a rollback, a reopen, an escaped defect or an incident against the change that caused it, feeding the existing reducer fields; no second copy of reducer logic | src/brothersbe/cli.py, src/brothersbe/lifecycle.py, tests | sonnet | 45 | a fixture of six closed changes prints the tier against outcome table, four prints NO-DATA |
| S6 | H9 finish | the 15 remaining "no readable" lines cleared with a written disposition each, none deleted silently | STATE.md (the sibling's), .sbe/ registry | sonnet | 30 | `python3 tools/sbe_fence_hook.py fences \| grep -c 'no readable'` prints 0, and one after a malformed line is added |
| S7 | p12 docs gap | docs/BITBUCKET.md states, by name, that the live Bitbucket run is blocked by the seat limit and is NO-DATA until a seat is freed | docs/BITBUCKET.md | haiku | 15 | `grep -n 'seat' docs/BITBUCKET.md` hits, and the doc-consistency suite OK |
| S8 | p2 BA guide, draft only | locate the text the complaint quotes (PS 131 of the problems document), draft the corrected page describing analysts handing over a full specification; sign-off stays with the analyst lead | the located guide file | haiku | 30 | the file is named with its line, the draft exists, and the close report says SIGN-OFF PENDING |

MUST subtotal: 530 agent minutes briefed. Actual: 740 to 1190 agent minutes.
Wall with two to three writers and the orchestrator's gates: 6 to 9 hours.

### 4b. Lane S, SHOULD, only after every MUST row is closed and re-verified

| # | item | shape decided in the problems document | files | writer | est | done-check |
|---|---|---|---|---|---|---|
| S9 | p3-clarify-enforcement | a detector for discussion-before-planning, shipping BEHIND AN ESTATE SWITCH that defaults to report, never refuse (amendment D2); every refusal path has an owner and expiry exception (D4, already in source) | tools/sbe_intake.py, the estate switch file, tests | sonnet | 120 | an intake with no recorded discussion REPORTS the absence by name in default mode and refuses only with the switch on |
| S10 | p4-decisions-harvest | decisions harvested from commit subjects and notes into the decisions record, each with its source | src/brothersbe/decisions.py, tests | sonnet | 90 | a fixture repo with three decision-shaped commits fills three rows naming their shas |
| S11 | H4-defect-origin | intake gains an origin field; a defect intake naming a regression row proceeds at T1, one naming none refuses and prints what is missing | tools/sbe_intake.py, contracts, tests | sonnet | 90 | the queue's own done_check |
| S12 | H2-accepted-state (B1) | an acceptance record: who accepted, when, against which passport and assurance result; hollow refused; queryable | src/brothersbe/lifecycle.py, contracts, cli, tests | sonnet | 120 | an all-green change reports acceptance NO-DATA; reports accepted once a record naming who and when exists |
| S13 | H6-requirement-found-in-build | a behaviour row added after a sheet was generated marks that sheet stale naming the new id | tools/sbe_design.py, tests | sonnet | 90 | add a row after generating, the sheet reports stale naming the new id |
| S14 | H3-deployed-ref-drift | evidence carries a deployed ref distinct from the evidence commit; status prints DRIFT naming both | src/brothersbe/observation.py, contracts, tests | sonnet | 120 | set a deployed ref one commit behind, status prints DRIFT naming both refs |

SHOULD subtotal: 630 agent minutes briefed, 880 to 1410 actual, another 7 to 11
hours of wall. Not one night's work on top of MUST; stated so nobody reads the
table as a promise.

### 4c. Lane M, this repository, second lane, small

| # | item | what | files | writer | est | done-check |
|---|---|---|---|---|---|---|
| M-a | queue reconciliation | run the done_check of D4, H9, H5 and escalation-finish against the sibling's source as measured above, move each queue row to the state its OWN check proves, quote the run; no row moves on a plan document's word | docs/plan/QUEUE.json | orchestrator | 30 | `python3 tools/bm_idle.py check` quotes the new depth; every moved row carries the quoted output |
| M-b | p1 decision recorded | the Windows position (refused by design, WSL is the path) recorded as a decision with its flip condition (a non-developer tester on Windows without WSL) rather than left as an open complaint | the store decision, docs/KNOWN-LIMITS.md if the wording lags | orchestrator | 15 | the store's decision listing shows it |
| M-c | the chosen round, M22 then M18 then M26 | unchanged from docs/handover/2026-08-21-reachability-round/07-NEXT-SESSION-PROMPT.md | scripts/migrate_install.py, tools/test_bm.py | sonnet | 180 | that prompt's own three done-checks, plus the mutation run it names |
| M-d | M20 | doctor runs the wired hook command with shell semantics | scripts/doctor.py, tools/test_bm.py | sonnet | 90 | the queue's done_check |

M-a and M-b are bookkeeping the overnight run does at its close if Lane S leaves
budget; M-c and M-d are NOT team items and wait for the next attended session
unless the founder says otherwise (decision OV-1).

### 4d. Not tonight, by name, with the reason

- p10 and p13 (requirement drift, T3): a data model decision (design version,
  supersession link, staleness clock). Navigator-only design first, and the
  navigator tier sits above the cap tonight. Next attended session.
- reality-command (the sibling's chosen round) and M22/M18/M26 (this repository's
  chosen round): behind the team's list by OV-1.
- M30 worktree reconciliation, break-glass records, any deletion: founder gates,
  nothing deleted unattended.
- H1, p5-stale-status, p12-certification, p2 sign-off: parked on a person.

## 5. What each window buys, so the choice is real

- Launched now (about 02:50 JST) to the 07:00 JST hard stop, about 4 hours:
  S0, S1a to S1d, S2, S6, S7, and the ceremony. Confidence medium. S1e, S3, S4,
  S5, S8 do not fit.
- Launched Saturday 22:00 JST to 07:00 JST, 9 hours: every MUST row, at the
  optimistic end also S3 and S4. Confidence medium-low; the band H history says
  the fix band is the one item whose size is unknowable until it runs.
- Either way the tag, the note to the reviewers, the history decision and the
  seat are the founder's, and the run stops at each.

## 6. Founder gates and what the run does if he says nothing

| gate | default if silent | recommended |
|---|---|---|
| Budget. The baseline is 800,000 output tokens per session (~/.claude/spend-guard.json, `default` block); precedents 8,000,000 (2026-08-20 night) and 10,000,000 (2026-08-21 night), each with an `until` at 07:00 JST | the run starts at the baseline and STOPS at the brake with a handover; it never raises its own ceiling | 8,000,000 until 07:00 JST, written into the sibling's project block with `until` |
| SBE-1, the nine already-public objects carrying two private terms | the history test stays the one named red; nothing tonight is blocked by it except the push to main | accept and record the flip condition (a clean extraction if a third exposure appears), because the objects are already public and a rewrite has its own recorded failure class |
| SBE-2, authorize the fix band for the six red suites before any seal | the band does not open; the run takes S2, S6, S7 and the SHOULD items instead, and the tag stays blocked | authorize; it is the critical path |
| SBE-3, which scorecard invocation the seal quotes | `--strict` is quoted and the three FAILs named as known debt | the same |
| SBE-4, the push skill's weak private-terms scan | the run uses the product's own list and scans newly reachable blobs, as the 2026-08-21 night did; the skill file outside the repository is untouched | say the word and the skill is corrected in a following attended session |
| The board's account. The stable link in PROJECT.md (bf99e884) answers "not found" to this account; the sibling found on 2026-08-21 that boards published from different accounts cannot be updated across accounts | the board travels as its HTML file in the pack's zip and no second artifact is minted | open the link from the account that published it, or name this account as the board's owner and the next close republishes from it and PROJECT.md records the new link |
| The tag and the note to the two lead reviewers | prepared, never cut | his hand, in the morning |
| Bitbucket seat and credential | the leg stays NO-DATA by name | his hand, any time before the seal |

## 7. Decisions taken by this planning session

- OV-1. The team's remaining items outrank both repositories' previously chosen
  rounds (M22/M18/M26 here; the reality command in the sibling). Founder
  instruction 2026-08-22. Flip condition: he names either round again in his
  own words, or every MUST row closes with budget and clock left.
- OV-2. The overnight session opens in the sibling's canonical path, not here,
  because every code item on the team's list lives there; this repository's
  lane is bookkeeping. Flip condition: the founder wants two sessions.
- OV-3. No tier above effort high is dispatched tonight. The navigator and
  reviewer definitions pin xhigh; the cross-family Codex gate covers the
  adversarial read instead. Flip condition: the founder readjusts the cap in his
  own words. Stated for the record: this planning session's one scout ran as
  the navigator type with a sonnet override, which kept the definition's xhigh
  effort; that is above the cap and is reported, not hidden.
- OV-4. Nothing is deleted, no tag is cut, no Release object is published, no
  Bitbucket seat is touched, no workflow file is written, Actions stay off.

## 8. The rules that bind every dispatch, each bought once

Pin the base sha inside the writer's own worktree and commit before the final
report. A fence registered in the main tree does not reach the worktree (the
sibling's `.sbe/tasks.json` is gitignored): tell the writer to open its own lane
there and that this is expected. A worker's green is a claim: re-run every
done-check in the main tree and quote that run. Mutation-prove every new guard.
Scans are per range, each its own command with its exit read (`grep -c` exits 1
on a clean tree). NO-DATA is never a pass and never a block. Check for other
writers before starting a gate, not only before editing. A close pack is not a
stop signal. Read exit codes directly, never through a pipe. Hard stop 07:00
JST; the ceremony is reserved 45 minutes before it.
