# STATE.md wave-era prose, archived verbatim 2026-08-01 (Loop 1 delete-list D1)

HISTORICAL. Superseded by the store at .brothermode/store.sqlite3 and its generated STATE.md view; nothing here is live.

Everything below is the hand-written fence bookkeeping that lived above the generated block in STATE.md from 2026-07-26 to 2026-08-01. The store superseded it; kept verbatim for history.

# BrotherMode V2 build, project state (dogfood registry, local only)

Session lease: fable5-v2-build, 2026-07-26. Orchestrator: main session (Fable 5).

## Live fences (fence then dispatch)
- store-engine (thread, V1 registry): tools/bm_store.py, tools/test_bm_store.py.
  Objective: Phase 1 engine per docs/superpowers/specs/2026-07-26-brothermode-v2-design.md.
  Writer: impl agent (sonnet), dispatched 2026-07-26. Tier T2. TTL 24h.
  check: python3 tools/test_bm_store.py passes AND python3 tools/test_bm.py stays green.

## Never-forget
- Push only via GitHub Desktop. No pushes to main; work lands on branch v2.
- Founder gates: releases, credentials. Windows support is ratified scope.

## Live fences (updated 2026-07-26, wave 2)
- store-engine (agent a9766b...): tools/bm_store.py, tools/test_bm_store.py. Fix round 3
  per docs/superpowers/specs/2026-07-26-phase1-fix-round.md. check: store suite green +
  calibration table. Tier T2. IN FLIGHT.
- ba-docs (agent, dispatched now): docs/ba/*.md ONLY (new directory). No overlap with
  tools/ or existing docs files. check: every claim traceable to the ratified spec.
- Orchestrator holds: tools/test_bm.py, tools/write_sites.json, SECURITY.md, docs/superpowers/specs/.

## Landed at green (commit fd662ad)
V1 suite 123 tests OK with the calibrated tripwire exemption; write-site inventory and
SECURITY.md posture updated. Engine files still untracked pending fix round 3.

## Live fences (wave 3, 2026-07-26, founder directive: execute all, report, then they score)
- phase2-recovery (agent, sonnet): tools/bm_autosave.py (NEW), tools/test_bm_autosave.py (NEW),
  tools/bm_autosave.sh (DELETE at the end). Objective: Phase 2 per
  docs/superpowers/specs/2026-07-26-phase2-recovery-design.md. Tier T2. TTL 6h.
  check: python3 tools/test_bm_autosave.py green AND python3 tools/test_bm.py green.
- onboarding (agent, sonnet): README.md, docs/QUICKSTART.md (NEW), docs/SETUP.md.
  Objective: a stranger productive in 10 minutes; Obsidian vault path; honest status.
  Tier T2. TTL 6h. check: a fresh-clone walkthrough executed by the agent itself.
- orchestrator holds: SKILL.md, RUBRIC.md, docs/WHITEPAPER.md, docs/knowledge/*, STATE.md.
NOTE: Phase 3 (rewiring bm_threads onto the store) is NOT dispatched this wave. It is a
large refactor of two files totaling 1,668 lines and doing it rushed at the end of a long
session is how the defects this project exists to prevent get created. Reported as
remaining, not attempted badly.

## Live fences (wave 4, 2026-07-26, founder directive: fully rewire, then review, then adversarial)
- phase3-rewire (agent, sonnet): tools/bm_threads.py, tools/bm_registry.py (DELETE),
  tools/test_bm.py. Spec: docs/superpowers/specs/2026-07-26-phase3-rewire-design.md.
  Tier T3. TTL 8h. check: all three suites green + full lifecycle walkthrough pasted +
  grep for bm_registry outside tests returns empty + line count falls.
- orchestrator holds: SKILL.md, docs/, SECURITY.md, README.md, the local skill sync.
- NOT in the rewire fence: tools/bm_store.py, tools/bm_autosave.py and their tests.
  A needed store change is REPORTED, never edited across the fence.

## Live fences (wave 5, FINAL LOOP, 2026-07-26)
- telemetry-audit (agent): tools/bm_telemetry.py, tools/test_bm.py, RUBRIC.md,
  tools/WEEKLY-REVIEW.md. Items 1 and 2 of the recommended order: the audit pass,
  deleting the metric that cannot move, and implementing the four learning loops.
  Tier T3. check: test_bm.py green + the fake metric gone + loops exercised by test.
- method-layer (agent): project-template/ (NEW), docs/INTAKE-TEMPLATE.md (NEW),
  docs/SUNSET.md (NEW). Item 3. Tier T2. check: scaffold a dummy project end to end.
- release-and-mcp (agent): CHANGELOG.md, VERSION (NEW), scripts/ (NEW), mcp/ (NEW),
  docs/RELEASE.md (NEW), docs/OBSIDIAN.md (NEW). Item 4. Tier T3.
  check: checksum script runs; MCP server starts and answers read-only queries.
- orchestrator holds: SKILL.md, STATE.md, the private-skill sync, the GUI push.

## Live fences (wave 6, correction-learning program, 2026-07-28)
Spec: docs/superpowers/specs/2026-07-28-correction-learning-program.md (founder
ratified 2026-07-28, section 3.1). Source plan kept verbatim at
docs/superpowers/plans/2026-07-28-correction-learning-source-plan.md.
- correction-learning (main session, Opus 5, SOLE WRITER, no agents dispatched):
  tools/bm_store.py, tools/bm_learn.py (NEW), tools/bm_learning.py (NEW),
  tools/test_bm_store.py, tools/test_bm_learning.py (NEW), tools/run_all_tests.py (NEW),
  tools/bm_threads.py (Loop 0.5 adopt defect ONLY), tools/bm_telemetry.py (Loop 4 only),
  docs/superpowers/specs/2026-07-28-*.md, docs/CORRECTION-LEARNING.md (NEW),
  docs/LEARNING-SCHEMA.md (NEW), docs/KNOWN-LIMITS.md, docs/NOT-FINALIZED.md, STATE.md.
  Tier T3. TTL 72h. Sequence: Loop 0, 0.5, 1, 2, 3, 5, 11A, then dogfood.
  check: python3 tools/run_all_tests.py exits 0 (all four suites serially) after
  every loop, plus each loop's own calibration table.
- Loops 9 and 10 are DEFERRED by founder decision, not forgotten. Reason published
  in the spec section 3.1.
- NOT in this fence: tools/bm_autosave.py, tools/bm_fence_hook.py and their suites.
  A needed change there is REPORTED, never edited across the fence.
- Push held for GitHub Desktop at the end. Branch v2. Never main.
- LANDED (closed 2026-07-29 by session 17a35490): loops 0, 0.5, 1, 2, 3, 5, 11A all
  committed (b5d246a, c36291b/98d3815, 6af94b8/1446eb5, 06d6806, 2cb1d3d, 33fa6c5),
  handover pack b2b352c. Evidence run 2026-07-29 after re-clone verify:
  "test_all: 445 tests across 4 suites, 2 skipped, 48.0s wall. ALL GREEN".

## Session lease (2026-07-29)
Session 17a35490 (Fable 5, orchestrator). Prior lease fable5-v2-build 2026-07-26 is
dead; its wave-6 fence closed LANDED above. Founder directive 2026-07-29: continue
handover, deploy remaining loops with a multi-agent flow, per-thread token budgets
and model tiers, link vault for private repo, keep public repo clean.

## Live fences (wave 7, Phase D + E deploy, 2026-07-29, fence then dispatch)
Spec: docs/superpowers/specs/2026-07-28-correction-learning-program.md section 4
(founder-ratified 3.1); source plan per-loop line ranges named below. Engine:
Workflow (serial implementers, parallel read-only refuters). NOTE, stated honestly:
this proceeds past the Phase C dogfood gate on the founder's directive of today;
14a stays OWED, item 1 (UNPROVEN on real founder work) stands. 11B stays GATED on
dogfood by spec. No dogfood evidence will be manufactured.
LAWS for every agent in this wave: implementation SERIAL, one writer at a time;
refuters read-only and NEVER run any test suite (module-rename collision,
NOT-FINALIZED item 10); only the active implementer runs tools/test_all.py, exactly
one at a time; commits pre-authorized on v2 ONLY (founder decision 3.1.4), one per
loop, no Co-Authored-By trailer, no em or en dashes anywhere; push held for GitHub
Desktop by the orchestrator; vault is READ-ONLY for agents except Loop 4 backfill
which WRITES only to this repo's .brothermode store after backing it up.
- loop4-capture (implementer, model opus, effort medium, budget 150k, tier T2):
  files tools/bm_telemetry.py, tools/bm_store.py, tools/bm_learn.py,
  tools/bm_learning.py, tools/test_bm*.py (not autosave/fence-hook suites),
  tools/write_sites.json, docs/NOT-FINALIZED.md (item 17 status only).
  Spec: source plan 979-1092 + program doc 3.1 decision 3. Backfill the vault inbox
  (5 rows, ~/Documents/Kay Vault/99-System/telemetry/corrections.jsonl) into the
  real store as candidates, store backed up first. check: test_all.py exit 0 quoted
  + calibration + French and >400-char corrections captured in a CLI probe.
- loop6-conflicts (implementer, opus, medium, 150k, T2): same file set.
  Spec: source plan 1225-1317. Edges table goes from unused to used.
  check: test_all.py exit 0 + learning-verify CLI probe on a throwaway store.
- loop7-lifecycle (implementer, opus, medium, 150k, T2): same file set.
  Spec: source plan 1318-1405. learning_applications goes from unused to used.
  check: test_all.py exit 0 + "was the rule followed" answerable in a CLI probe.
- loop8-grading (implementer, opus, medium, 150k, T2): same file set.
  Spec: source plan 1406-1503. check: test_all.py exit 0 + rework/escaped-defect
  linkage shown in a CLI probe.
- refuters (2 per loop, opus, high, 80k each, read-only): drive the real CLI against
  throwaway stores, adversarial inputs; verdict UPHELD or REFUTED with repro lines.
- loop12-review (3 lenses, opus, high, 100k each, read-only): secrets/redaction,
  filesystem/permissions/traversal, injection/robustness. Fixer (opus, high, 120k)
  lands confirmed findings as one commit.
- loop13-docs (implementer, sonnet, medium, 80k, T2): docs/, README.md,
  CHANGELOG.md, RUBRIC.md, tools/WEEKLY-REVIEW.md per source plan 1895-1979; release
  notes MUST name deferred 9 and 10, gated 11B, owed 14a. check: test_all.py exit 0.
- Orchestrator holds: STATE.md, SKILL.md, the vault write-back, the private-skill
  sync, every push (GitHub Desktop), the final re-run of every done-check.
- LANDED 2026-07-29, evidence (verbatim, orchestrator re-run after last edit):
  "test_all: 598 tests across 4 suites, 2 skipped, 53.5s wall. ALL GREEN" (was 445)
  Workflow w7fby18zt: 26 agents, 0 errors, 3,152,421 subagent tokens, 4.4h wall.
  Commits (authorship rewritten to Khalil Maaouni by founder window decision,
  pre-rewrite hashes preserved at refs/original): eb7753d+bdbe153 (Loop 4),
  67cb5da+4c2c8c7 (Loop 6), 7a004e3+dbfccd7 (Loop 7), 53d95e1+f375277 (Loop 8),
  97dc784 (Loop 12 security fix: Critical scrubber word-boundary bypass + 5 leak
  paths, re-verify UPHELD 0 findings), 3eeb5f7 (Loop 13 docs), 8e015c7 (SKILL.md
  law: record applications, question windows, window-approval channel).
  Every impl round REFUTED by refuters, every fix round re-verified UPHELD.
  Store: 5 inbox rows backfilled; founder decided by windows 2026-07-29: 2 global
  rules approved (3dad1a78 Desktop-push GATE, eeb754ad question-window UI), 5
  rejected with reasons (4 Tonari strays kept in inbox, 1 empty). First live
  correction processed end to end same day (18c41e2a captured and approved).
  Scans: dashes 0, private paths in diff 0, trailers 0, secret shapes all fixtures.
  OWED: 14a dogfood window (founder calendar time), 11B gated on it; push via
  GitHub Desktop; PR v2 to main HELD until dogfood (founder window decision).
  SUPERSEDED same day: see wave 8 below (founder window decision: ship V2 as RC).

## Live fences (wave 8, post-audit plan execution, 2026-07-29, fence then dispatch)
Plan: docs/BrotherMode_V2_Post_Audit_Execution_Loops.md (founder-supplied, executed
on their directive). P-loop numbering to avoid collision with correction-learning
loop numbers. Founder window decisions 2026-07-29 (recorded as approval refs):
(1) SHIP V2 AS RC NOW: Loop P1 executes, supersedes the morning hold; stable claim
still waits for dogfood (P13) and independent audit (P14). (2) New loops P16
cross-runtime adapters, P17 packaging, P18 ecosystem launch kit, P19 external beta
ALL ratified, run after P12. (3) Loop P3 approval = Model A receipts (window click
mints one-time receipt; approve refuses without it).
Applied store rule: 3dad1a78 (Desktop pushes) retrieved with --record-applications,
task 4d8152b7.
- P0-baseline (orchestrator inline, T1): docs/POST-AUDIT-BASELINE-2026-07-29.md
  (NEW), docs/BrotherMode_V2_Post_Audit_Execution_Loops.md (add), docs/NOT-FINALIZED.md
  (baseline cross-check only). One commit. check: baseline doc ties every number to
  a command run this session. Read-only auditor agent (opus) verifies contradictions.
- P1-release (orchestrator, T2, AFTER P0): merge v2 into main at the P0 commit,
  backup branch pre-merge-main-20260729 first, tag above 2.0.0-rc.2 on the tested
  commit, VERSION/CHANGELOG/docs/RELEASE.md updated on v2 BEFORE the merge, README
  root must show V2. Push main via GitHub Desktop; tag via the browser release flow
  (Desktop does not push external tags, recorded in the vault tool register).
  check: clean clone of the tag passes test_all.py; unauthenticated ls-remote shows
  main == tagged commit. Never move an existing tag.
- Wave2-learning (Workflow, serial implementers on v2, opus, 150k each; 2 refuters
  per loop opus high 80k): P3 Model A receipts, P4 gate delivery contract, P5
  lookup/apply split with mandatory recording, P6 learning_retrieval_runs schema,
  P7 FTS5 with lexical fallback. Files: tools/bm_store.py, tools/bm_learning.py,
  tools/bm_learn.py, tools/test_bm*.py, tools/write_sites.json, SKILL.md (P5 only,
  apply-not-relevant contract), docs/CORRECTION-LEARNING.md, docs/KNOWN-LIMITS.md,
  docs/NOT-FINALIZED.md, CHANGELOG.md. Same laws as wave 7: serial writers, ONE
  suite at a time via test_all.py only, refuters never run suites, no dashes, no
  trailers, commits on v2, no pushes.
- Orchestrator holds: STATE.md, branch and merge operations, every push, P16-P19
  (not started, run after P12).
- NOT STARTED, recorded so a resume cannot drop them: P2 installer, P8 fences and
  Bash boundary, P9 CI parity, P10 doc drift, P11 privacy and Windows, P12
  transactional handovers, P13 dogfood (founder calendar), P14 independent audit
  (different model family), P15 final release, P16-P19 (ratified above).
- P0 LANDED 2026-07-29: commit c3d5b20 (baseline doc + plan doc, no code).
  Gate evidence "test_all: 598 tests across 4 suites, 2 skipped, 539.7s wall.
  ALL GREEN" (539s from running beside smoke commands, process note in baseline).
  verify-install FAILED on 12-commit manifest drift, recorded, fixed in P1 by
  regenerating CHECKSUMS.sha256 (123 hashes). Read-only auditor dispatched.
- P1 PARTIAL (plan status word; remainder named at the end of this entry),
  2026-07-29: release cut d88abcc (VERSION
  2.0.0-rc.3, CHANGELOG, fresh manifest), gate re-run alone: "test_all: 598
  tests across 4 suites, 2 skipped, 151.1s wall. ALL GREEN". Old main backed up
  (branch pre-merge-main-20260729 = 60a6d0d, also an ancestor of new main so
  permanently reachable). main fast-forwarded and PUSHED via GitHub Desktop;
  verified unauthenticated: ls-remote main == v2 == d88abcc. V2 IS THE PUBLIC
  PRODUCT. Local annotated tag v2.0.0-rc.3 created at d88abcc under the
  founder's window grant. BLOCKED at tag push + release page: CLI has no
  credentials (by design), GitHub Desktop does not push external tags (tool
  register), Chrome extension not connected (2 attempts). Founder executes the
  release page, or I retry the browser channel when it reconnects. Clean-clone
  full gate from the tag PENDING until the fleet quiesces (one suite at a time).
- Wave2-learning Workflow wrbp49bvm RUNNING from HEAD d88abcc: P3 receipts,
  P4 gates, P5 apply, P6 runs, P7 fts. Serial implementers, refuters per loop.
- WAVE 8 CLOSED BY FOUNDER ("Finish now", 2026-07-29 evening). Workflow
  wrbp49bvm STOPPED mid-P3. P3 implementer's in-flight edits are PRESERVED in
  two places: left uncommitted in the tree (5 files: bm_learn.py, bm_learning.py,
  bm_store.py, test_bm.py, test_bm_store.py) and snapshotted to
  refs/brothermode/autosave (latest = 46b076d, verified by show-ref). RESUME
  PATH for the next session: Workflow resumeFromRunId wf_7986c424-7b1 with the
  persisted script (P0/P1 stages replay from cache; P3 implementer re-runs; its
  freshness check will see the dirty tree, so the resuming orchestrator must
  either let the SAME loop continue from the tree or restore-and-restart, per
  references/fences.md: tree is the truth). Do NOT run test_all.py on this tree
  expecting green: it carries half-implemented P3.
## WAVE 9 CLOSED 2026-07-30: tag published and v2 retired; RELEASE PAGE STILL OPEN
Evidence, all from commands run this session:
  ls-remote: refs/heads/main 6cc94bc; refs/tags/v2.0.0-rc.4 d785619 peeled to
    6cc94bc; NO refs/heads/v2 (retired after printing rev-list main..v2 == 0)
  clean clone of the tag: VERSION=2.0.0-rc.4;
    "test_all: 911 tests across 7 suites, 1 skipped, 84.7s wall. ALL GREEN";
    148 checksum entries OK
NOT DONE: the GitHub Release PAGE is unpublished (browser extension down; the tag
itself is live and clonable, so this is presentation only). Tag had to be created
THROUGH GitHub Desktop because an externally-made tag was confirmed not to push:
recorded for the tool register. Incident: a harness classifier outage blocked
Bash, Write, Edit, Monitor and browser tools for a stretch; on-disk git metadata
(FETCH_HEAD, push reflogs) carried verification meanwhile.

## Live fences (wave 10, documentation engine + gate packs + book, 2026-07-30)
Spec: docs/superpowers/specs/2026-07-30-documentation-and-gate-packs-design.md
(commit 91d48d8, founder-ratified through question windows 2026-07-30; eight
decisions in its section 2, thirteen invariants in section 3, I10 to I13 new).
Brainstorming skill gate satisfied: design presented, founder answered "Approved,
go". Founder ALSO ratified: critical alerts BLOCK a gate close with a recorded
override; P14 internal audit is labelled same-family and the outside review stays
open.
Build order is the founder's: A gate packs, B documentation engine, C
collaboration layer, D book. SERIAL implementers (shared store and doc files),
two adversarial refuters per phase, fix round plus independent re-verify on any
Critical or Major.
- Files in fence for phases A to C: tools/bm_store.py, tools/bm_learning.py,
  tools/bm_learn.py, NEW tools/bm_docs.py, NEW tools/bm_packs.py (names to be
  collision-checked by the implementer), tools/test_bm*.py, tools/write_sites.json,
  project-template/**, docs/KNOWN-LIMITS.md, docs/NOT-FINALIZED.md, CHANGELOG.md.
- Phase D adds: docs/book/** (new), and may not touch tools/.
- Orchestrator holds: STATE.md, SKILL.md, all pushes (GitHub Desktop), the final
  re-run of every done-check, and the vault write-back.
- NOT in fence, report instead: tools/bm_autosave.py, tools/bm_fence_hook.py.

## Live fences (wave 9, MAXIMUM POWER close-out, 2026-07-29 evening, fence then dispatch)
Founder window decisions: max-power lanes; final version 2.0.0-rc.4; close grant
for push + tag + release page + v2 retirement (after 0-unmerged proof). Goal:
finish ALL machine loops, unify under main, close the project. P13/P14/P19-run
stay open by nature and are named in the release notes.
- STORE CHAIN (main tree, v2, serial, opus impl 150k + 2 refuters 80k each):
  P3 finish (ADOPTS the killed implementer's 5-file in-tree edits; snapshot at
  refs/brothermode/autosave 46b076d), then P4, P5, P6, P7, P12. Named P3 check:
  auditor repro (approve, no ref, no receipt) MUST refuse.
- LANE A worktree ~/Documents/BrotherModeUp-laneA-install (branch
  lane/laneA-install): P2 installer, then P8 fence+Bash boundary, then P10 doc
  purge (audit queue from the vault finding, embedded in brief). Serial in-lane.
- LANE B worktree ...-laneB-ci (lane/laneB-ci): P9 CI parity.
- LANE C worktree ...-laneC-privacy (lane/laneC-privacy): P11 export
  withholding + Windows honesty.
- LANE D worktree ...-laneD-ecosystem (lane/laneD-ecosystem): P16 adapters
  (web-verified conventions), P17 packaging, P18 launch kit, P19 beta kit.
  Serial in-lane.
- LANE LAW: lanes NEVER touch CHANGELOG.md, docs/NOT-FINALIZED.md,
  docs/KNOWN-LIMITS.md, SKILL.md (register updates are RETURNED as text and
  landed by the merge step); each lane runs its own test_all.py in its OWN
  worktree only; commits on the lane branch; never push.
- MERGE (after barrier, opus high, main tree): merge lanes into v2 in declared
  order A, B, C, D, gate after each; aggregate register updates; VERSION rc.4,
  CHANGELOG, fresh checksums; final full gate.
- ORCHESTRATOR TAIL (me, founder grant recorded): ff main to final, push both
  via Desktop, tag v2.0.0-rc.4 + release page (browser or founder if extension
  still down), retire remote v2 AFTER printing the 0-unmerged proof, clean-clone
  gate from the tag, vault close, felt-outcome window.
- Orchestrator holds: STATE.md, all pushes, worktree lifecycle.

- P0 auditor RETURNED 2026-07-29: findings persisted to the vault
  (10-Projects/brothermode/Findings/p0-doc-audit-2026-07-29.md). Highest:
  approve with no --ref SUCCEEDS (bm_learn.py:274 synthesizes the reference)
  while help claims refusal. NAMED FLEET-CLOSE CHECK: re-run that exact repro
  after P3; it must REFUSE. Doc-drift queue (QUICKSTART 54-vs-144, 4-vs-5
  hooks, README adopt-defect staleness, RELEASE.md rc.2 pins, safety-grep
  false-fail) feeds P10; hook wiring gap feeds P2 and P8.

