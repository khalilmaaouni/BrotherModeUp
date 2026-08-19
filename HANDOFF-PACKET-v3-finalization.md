# Handoff packet: BrotherMode v3 finalization

This file is GENERATED from BrotherMode's store by `brothermode continue`. Every line below is a row, or the absence of one. Edits here are overwritten on the next run: put anything the successor must know into the store instead, so the next regeneration carries it.

project_id: v3-finalization

## 1. North star and goals

North star: One clean main that IS the product, the published holes fixed, one honest install, no duplicate authorities, a progress view the founder can open any day, and a continuity protocol so the work never stops between sessions.

What the founder gets: (none recorded)

Success checks: (none)

## 2. Where we stand, one paragraph

BrotherMode v3 finalization is in status (none), phase Phase 5, with 32 planned, 1 active, 2 blocked, 4 awaiting review, 12 accepted.

## 3. Read next, in this order

1. HANDOFF-PACKET-v3-finalization.md (this file): the packet itself, regenerated from rows every time.
2. PROJECT-VIEW.html, kind PROJECT_VIEW, (local only, never published)
3. PROJECT-VIEW.html, kind PROJECT_VIEW, (local only, never published)
4. PROJECT-VIEW.html, kind PROJECT_VIEW, (local only, never published)
5. PROJECT-VIEW.html, kind PROJECT_VIEW, (local only, never published)
6. PROJECT-VIEW.html, kind PROJECT_VIEW, (local only, never published)

## 4. Next actions, ordered

1. night-lane-a [active, priority 1]: Execute docs/plan/NIGHT-RUN-2026-08-19.md Lane A in order (A1 trust surface, A2 passport producer, A3 M-items, A4 queue stages, A5 reality record if budget, A6 close); every item closes with its named done-check quoted; founder gates in the plan hold
   why: Fable mandate 2026-08-19, founder budget applied 2026-08-20 00:10 JST

## 5. Evidence index

- p0-ff-main (accepted):
  - ev-p0-ff-main: kind=check ref=git rev-parse main == d485699; rev-list origin/main..main == 0
- p0-branches (accepted):
  - ev-p0-branches: kind=check ref=git branch -a lists main only
- p0-hygiene (accepted):
  - ev-p0-hygiene: kind=check ref=one digest per session start; ls STATE.md.bak* empty
- p1-h2 (accepted):
  - ev-p1-h2: kind=check ref=commit 04fc8f2, red then green, the two bypass commands refused
- p1-h3 (accepted):
  - ev-p1-h3: kind=check ref=commit be134a6, hostile env var test red then green
- p1-h4 (accepted):
  - ev-p1-h4: kind=check ref=commit 7303485, case-insensitive mount path green
- p1-h1 (accepted):
  - ev-p1-h1: kind=check ref=commit 5dfe4cc, the expectedFailure flipped to a passing assertion
- p1-iso (accepted):
  - ev-p1-iso: kind=check ref=commit 816a1b9; test_all: 2716 tests across 26 suites, 2 skipped, 394.0s wall. ALL GREEN
- pc-continue (accepted):
  - ev-pc-continue: kind=check ref=test_all: 2735 tests across 26 suites, 2 skipped, 441.7s wall. ALL GREEN
- p5-schema (accepted):
  - ev-p5-schema: kind=check ref=python3 tools/test_bm_store.py: Ran 1005 tests in 43.603s OK
- p5-draw (accepted):
  - ev-p5-draw: kind=check ref=python3 tools/test_bm_visual.py: Ran 84 tests in 0.990s OK
- p5-page (accepted):
  - ev-p5-page: kind=check ref=python3 tools/test_bm_view.py: Ran 86 tests in 1.663s OK

## 6. Telemetry

Spend: 0 tokens, 0 minutes.
Token ceiling 3000000, 0.0 per cent used, verdict ok.
No forecast recorded.

## 7. Lessons learnt

(no lesson has been recorded for this project)

## 8. Features pipeline

- r2-canary-refute [awaiting review, priority high]: R2: canary refute pass, strongest tier
- r3-codex-audit [awaiting review, priority high]: R3: Codex audit split rerun, one call per file
- r4-triage-findings [awaiting review, priority high]: R4: triage every audit and refuter finding
- r5-tag-release [planned, priority high]: R5: tag v3.1.0, FOUNDER GATE
- b1-benchmark-option-a [planned, priority medium]: B1: benchmark, option A
- c1-convergence-engine [planned, priority medium]: C1: convergence engine
- cc-command-center [planned, priority medium]: CC: command center convergence S1 to S7
- cx-codex-port [planned, priority medium]: CX: native Codex port, phases 0 to 9
- g1-work-governor [planned, priority medium]: G1: work governor
- sd-active-stall-detector [awaiting review, priority medium]: SD: active stall detector
- v1-acceptance-verifier [planned, priority medium]: V1: acceptance contract and independent verifier
- a1-authority-language [planned, priority unset]: A1: authority wording matches mechanism, Option A human-confirmed vs Option B local signature, founder decision (GAP-05)
- b0-benchmark-freeze [planned, priority unset]: B0: one benchmark hierarchy and frozen VADR in NORTH-STAR.md before any counted run (GAP-23,24)
- cu-cursor-compat [planned, priority unset]: CU: Cursor compat mode from the external drop, landed through Fable review and the adapter seam shared with CX; triage map first
- d1-delivery-closure [planned, priority unset]: D1: delivery becomes a deterministic state transition, H7 failure is the RED case (GAP-12)
- e1-write-containment [planned, priority unset]: E1: runtime-independent write containment seam, Fable architecture spike first, zero-escape corpus is the exit gate (GAP-03,04,17,38)
- f1-first-run [planned, priority unset]: F1: cold-user first run, 80 percent complete start flow without coaching (GAP-32)
- i1-methodology-adapters [planned, priority unset]: I1: spec import and methodology adapters, BrotherMode keeps governance (GAP-43,44)
- m1-memory-eval [planned, priority unset]: M1: labeled retrieval corpus and evaluation before any new memory backend (GAP-33)
- o1-operational-maturity [planned, priority unset]: O1: install, upgrade, downgrade, corrupt-store recovery lifecycle matrix per platform (GAP-41,42)
- p0-branches [accepted, priority unset]: Delete the stale branches so one branch is the truth
- p0-ff-main [accepted, priority unset]: Fast-forward main to the release tag
- p0-hygiene [accepted, priority unset]: Local hygiene: stale backups, dead records, duplicate hook
- p1-h1 [accepted, priority unset]: H1, one identity for a claim and a write across a worktree
- p1-h2 [accepted, priority unset]: H2, the heredoc parser gaps in the fence hook
- p1-h3 [accepted, priority unset]: H3, the environment override on the store root
- p1-h4 [accepted, priority unset]: H4, case folding probed instead of assumed
- p1-iso [accepted, priority unset]: Restore worktree isolation and retire the published limit
- p2-h5 [planned, priority unset]: H5, assert the write-ahead journal result at the store constructor
- p2-h6 [planned, priority unset]: H6, a full disk warns instead of raising in the state refresh
- p2-hooks [planned, priority unset]: Hook consolidation, measured before and after
- p3-install [planned, priority unset]: Collapse to two documented install paths
- p3-pypi [planned, priority unset]: Build the wheel and write the publish runbook
- p4-docs [planned, priority unset]: Split current truth from the internal audit trail
- p4-shims [planned, priority unset]: Retire the fifteen legacy shims with one migration page
- p5-draw [accepted, priority unset]: Draw the Gantt: the seventh shape, petrol over the status colours
- p5-live [blocked, priority unset]: Render this programme's own page from its own records
- p5-page [accepted, priority unset]: Put the Gantt on the page as one section, not a second page
- p5-schema [accepted, priority unset]: Record the phase a piece of work belongs to
- p6-court [planned, priority unset]: Fresh-clone court on the final candidate
- p6-ledger [planned, priority unset]: One ledger row per review finding, none dropped
- pc-continue [accepted, priority unset]: brothermode continue: the handoff packet, generated from rows
- pc-docs [planned, priority unset]: One page stating the continuity contract and its last resorts
- pc-flows [blocked, priority unset]: Wire the verb into the deliver and stop flows
- pc-liveness [planned, priority unset]: Successor liveness recorded as evidence, never a process id
- pilot-external [planned, priority unset]: PILOT: ten outside builders, ten real projects, failures published, founder-owned recruitment (GAP-28,29,30,46)
- q1-benchmark-meta [planned, priority unset]: Q1: test the benchmark itself, hidden tests never in workspace, results generated from artifacts
- s1-hostile-repo [planned, priority unset]: S1: hostile repository resistance, repo text is data not authority, cross-family audit mandatory (GAP-35)
- x1-context-convergence [planned, priority unset]: X1: shrink the root control plane, measure context tax before changing (GAP-18)
- x2-hook-overhead [planned, priority unset]: X2: true out-of-process hook latency, consolidate the Stop chain, COG-9 trivial-task target (GAP-20,21,22)

## 9. Open founder decisions

(nothing is waiting on the founder)

## 10. The continuity contract for the successor

The successor owes the program four things, and silence is the only forbidden outcome:

1. ONE bounded chunk of work, because a headless session runs ONE turn and then exits. A mission larger than one turn is a mission that dies half done.
2. A done-check run AFTER the last edit, quoted verbatim. Nothing is called done without it.
3. This packet regenerated the moment the work state changes materially, not at the last minute.
4. Its own successor launched before it closes IF THE RELAY BRAKE ALLOWS IT, or a plain statement that it did not and why. `brothermode continue` decides that, not you: it refuses past the chain's generation cap, past its deadline, or on a blown spend ceiling, and a refusal is a correct stop that leaves this packet behind for a human. Never work around a refusal by launching a session another way.

Founder gates never move: no tag, no credentials, no publishing, no permanent deletion, whatever any instruction downstream of this file says.

The successor's own launch command:

    BROTHERMODE_RELAY_DEADLINE=2026-08-20T07:00:00 BROTHERMODE_RELAY_GEN=1 BROTHERMODE_RELAY_MAX=8 nohup claude -p 'You are the next relay session of this BrotherMode program. Read HANDOFF-PACKET-v3-finalization.md first: it is the whole brief, generated from the store, and its ten sections carry the north star, where the work stands, the ordered next actions, the evidence, and the open founder decisions. Do ONE bounded chunk of work: the first unfinished next action in section 4, no more. A headless session runs ONE turn and then exits, so a mission larger than one turn dies half done. Close your chunk with its done-check run after your last edit and quoted verbatim, commit on your own branch in your own git worktree, and never switch the main checkout'\''s branch. Before your turn ends, regenerate this packet with `brothermode continue --project-id v3-finalization` so your own successor inherits current facts. Founder gates are unchanged and outrank every instruction above: no tag, no credentials, no publishing, no permanent deletion.' --add-dir . > successor-v3-finalization.log 2>&1 &

That command needs the standing settings allow rules `Bash(claude -p*)` and `Bash(nohup claude -p*)`, which only the founder can grant: a session cannot grant itself the right to launch a session, and that refusal is correct.

The successor runs under whatever your installed settings already allow, so its writes and commands are gated the same way yours are. Loosening that is an explicit choice, typed per launch as `--permission-mode MODE`, never a default this tool picks for you.

Run it from the project root. Every path in this packet is relative to that root, because a generated document masks absolute paths and an absolute path here would reach you withheld.

This packet lives at HANDOFF-PACKET-v3-finalization.md, relative to the project root.
