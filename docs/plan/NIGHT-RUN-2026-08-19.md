# Night run 2026-08-19 to 2026-08-20: the trust chain, made true

Status: CURRENT (tonight's execution plan; it becomes historical when the
morning pack's close report supersedes it).

Written 2026-08-19 23:20 JST by the Fable mandate session (44070297). This is
the execution plan the founder asked for: "Review all plan and give a night run
of 10M token plan perfected for execution to cover all my team's complaints and
beat our competition for good in our positioning."

Every "done-check" line below is an ACCEPTANCE CRITERION for a session that has
not run yet, not a claim that anything passed. Nothing in this plan is done
until a night session runs the named command after its last edit and quotes it.

AUTHORITY ORDER for every decision tonight: (1) the founder's mandate of
2026-08-19, (2) docs/NORTH-STAR-CHAIN.md, (3) PRODUCT-DIRECTION.md,
(4) BROTHERMODE_TOTAL_LEADERSHIP_STRATEGY.md (repo root, landed tonight),
(5) verified implementation reality, (6) older roadmaps. Conflicts are named,
never silently reconciled.

THE ONE OUTCOME (from the mandate, governing every item): make BrotherMode the
product serious builders trust when they delegate meaningful work to AI and
later need to know exactly what happened. Own the truth of the chain, borrow
everything else. Do not optimize for feature count, stars, or agent count.

## 0. The evidence-backed map, as of 23:15 JST tonight

Audited tonight by three read-only agents (two scoped readers, one adversarial
attacker briefed to refute) plus orchestrator spot-checks. GREEN means exists
and refuses something. AMBER means exists and can be walked past. RED means
does not exist.

| Chain stage | State | Decisive evidence |
|---|---|---|
| Human intent | AMBER | goal/scope/success recorded; pre-planning questions not kept; M8 walkthrough dead-ends before tasks |
| Development method | AMBER | routing to installed methods runs; native floor is a sentence, not a method |
| Execution provenance (BrotherMode) | AMBER, two blockers | fence hook NOT wired in this machine's settings (M1, confirmed: no bm_fence_hook entry); running copy is a stranded pre-rewrite clone with disjoint history and dead upstream (confirmed via git cat-file both directions) |
| Change Passport, producer | RED | nothing in BrotherModeUp produces one |
| Change Passport, consumer | AMBER | BrotherSBE tools/sbe_passport.py exists with 19 tests; fields 2 (who) and 5 (where from) NO-DATA in every run because the producer never delivers them |
| SBE behaviour | GREEN | sbe_design.py check_behaviour |
| SBE risk | GREEN | sbe_intake.py compute_tier |
| SBE required proof | GREEN | proof column read by sbe_testkit.py |
| SBE evidence integrity | AMBER | trust_level() labels LOCAL-ADVISORY or CI-CLAIMED; CI id spoofable via env, stated in code |
| SBE accountability | AMBER | approver recorded; nothing detects that a change NEEDED approval |
| SBE business impact | RED | intake asks yes/no; no impact statement object |
| SBE release readiness | RED | no per-change readiness verdict |
| SBE production observation | RED | nothing observes production |
| Human decision | AMBER | decision packet refuses hollow; NO acceptance record exists (H2) |
| Release | host's | v3.3.1 tagged on origin at 00bba47, VERSION 3.3.2.dev1, chain consistent |
| Verified reality | RED | no post-merge record of any kind (H1, H3, H5) |
| Return edge, reality back to intent | RED | a defect cannot be entered as a defect (H4, H6) |

Trust-surface contradictions CONFIRMED tonight by the adversarial pass, all in
scope for Gate 0:

- C1 BLOCKER. The running copy at ~/.claude/skills/brothermode shares no
  objects with the dev repo (pre-rewrite stranded clone), is 4 days stale,
  upstream-dead, newest tag v3.3.0, and carried an UNCOMMITTED founder law.
  The law text was rescued into dev SKILL.md tonight (this session).
- C2 BLOCKER. One-writer enforcement is not running where Claude Code actually
  runs: no fence hook wired in ~/.claude/settings.json. This is M1.
- C3 MAJOR. M11 was closed by prose: bm_fence_hook.py gained no query verb, no
  test pins probe-versus-hook agreement.
- C4 MAJOR. docs/RELEASE.md line 54 names install target v2.0.0-rc.9 against
  reality v3.3.1 (tools/bm_project_facts.py PUBLIC_INSTALL_TAG).
- C5 MAJOR. Tag v3.3.0 was re-pointed by the 2026-08-18 force-push; a
  pre-rewrite clone strands silently; nothing detects the stranded state and
  README's install section does not link the release check page.
- C6 MINOR. Installed BrotherSBE plugin is 3.2.0 against repo 3.2.1.

Team complaints, full inventory (the mandate says cover ALL of them):

- M-series (this machine's engineer corrections, QUEUE.json is the authority):
  M3, M9, M11-doc-half FIXED. OPEN: M1, M2, M4, M5, M6, M7, M8, M10 (its
  BLOCKED note is stale: fence F5's owning session is gone, sweep and detect
  both clean tonight).
- Adopter items still open (docs/plan/ADOPTER-OPEN-ITEMS-REEXTRACTED-2026-08-17.md):
  ship-to-reviewers, p14-sol2-green-scope, p6-receipt-provenance, p11-prove-rename,
  p2-ba-guide-wrong, escalation-finish, p3-clarify-enforcement, p7-owed-checks,
  p4-decisions-harvest, p1-windows-first-run, p12-bitbucket-sbe-leg,
  p10-p13-requirement-drift, plus A0 and p5-wall-of-text.
- North-star holes H1 to H9; H2 (acceptance record) and H9 (one-writer inert in
  the SBE estate) are scheduled tonight; H1, H3, H4, H5, H6 begin with the
  smallest verified-reality record (item A5).

## 1. What tonight optimizes, in one line each

1. Gate 0 true: a third party can audit the release surface and find no
   material contradiction (C1 to C6 closed or honestly disclosed).
2. Gate 1 stronger: every open M-item closed with a regression test.
3. Gate 2 opened: Change Passport v1 PRODUCED by BrotherMode, consumed by
   BrotherSBE, fields 2 and 5 carried for the first time, field 4 mandatory.
4. The smallest acceptance record and verified-reality record exist, so the
   chain's blind-after-merge half stops being entirely blind.
5. Positioning: claims narrowed to what is now true, which after tonight is
   more than any competitor states honestly. The public story stays
   "the execution trust layer for serious Claude Code work".

## 2. Budget, brakes, and stop conditions

- Founder budget for the run: 10,000,000 output tokens TOTAL across both
  lanes, named in the mandate. The plan's own soft stop: no NEW dispatches
  past 8,000,000 total (the standing 80 percent law); in-flight work finishes.
- Mechanical brake: the harness permission classifier REFUSED this session's
  automated write of the new grant into ~/.claude/spend-guard.json (a session
  raising spend ceilings is exactly what it watches for), and that refusal is
  honored, not routed around. A ready-to-apply grant block sits at
  ~/Documents/BrotherModeUp-handovers/2026-08-19-night-grant/ with one-line
  apply instructions; until the founder applies or explicitly approves it,
  every night session stops at the 800,000 baseline, which makes the brake a
  LAUNCH BLOCKER, named in tonight's founder questions. Target figures:
  per-session 3,000,000 hard / 1,500,000 soft; daily 19,000,000 hard for this
  repo (last night's 8.856M rolling residue plus the granted 10M), expiring
  2026-08-20T07:00+09:00. The 10M total is tracked by the run's own telemetry
  lines at every session close.
- Hard stop 07:00 JST, the founder's unattended law. Relay brake, overnight
  watchdog, spend guard: all three or no unattended work.
- Every session: open with the baton ceremony (detect, read newest pack,
  adopt or park), close with skeleton, fill, zip, verify-close, commit the
  pack, merge to main, push through the github-desktop-push gates (secret
  scan, dash scan, green tests, command verification, plus the attribution
  and private-terms scans).
- Tiers declared per brief, guidance up execution down: fast worker for
  mechanical bulk, builder for scoped implementation, reviewer for
  adversarial verify (never below the guide's grade), navigator only where
  architecture is genuinely open. Any finding that gates a push or safety
  claim gets one cross-family refutation (codex exec, read-only, report
  redirected), per the 2026-08-05 law.
- Waits are background or Monitor, never sleep-and-poll. The full gate runs
  per PO-1 (clear stale sentinel FIRST, detach, poll the process).
- NO SELF-FIRING CI. Bitbucket legs: the kmaaouni workspace is read-only
  (seat limit), so every two-host done-check runs its host-neutral script
  LOCALLY, labels the Bitbucket leg BLOCKED by name, and burns zero pipeline
  minutes. That is the documented pattern, not a defect.
- Disk gate, session caps, one suite at a time: per the active-laws digest.

## 3. Lane A: BrotherModeUp (the producer side), about 5.5M

One writer at a time in this repo, serial sessions via the continuity
protocol (python3 tools/brothermode_cli.py continue). Each item names its
stage, files, done-check, tier.

### A1. Gate 0 sweep (stage: provenance; tier: builder; ~1.0M)
Files: docs/RELEASE.md, docs/KNOWN-LIMITS.md, README.md, tools/bm_fence_hook.py,
tools/test_fence_hook*.py (or the suite that owns it), scripts/doctor.py,
docs/plan/QUEUE.json (state fields only).
- C4: RELEASE.md install-target line reads the live fact (v3.3.1 or, better,
  reads tools/bm_project_facts.py so it cannot drift again). Done-check: grep
  shows no rc.9 string; docs suite green.
- C3, the real M11: add a query verb to bm_fence_hook.py (ask the hook
  "would you allow this write" from the command line) and a test that pins
  hook-verdict equals probe-verdict on the four canonical cases. Done-check:
  new test fails on the pre-fix shape, passes at HEAD; M11 done_check in
  QUEUE.json updated to the code half.
- C5: doctor gains a stranded-install check (local tag SHA versus
  git ls-remote SHA for the pinned tag; mismatch prints the recovery command,
  network-less run prints NO-DATA, never a pass). README install section
  links docs/PUBLIC-RELEASE-CHECK-2026-08-18.md. Done-check: doctor run
  quoted with the new check visible on both paths.
- M7: the two overclaiming degrade messages state only what exists.
  Done-check: grep for the two false claims returns nothing; the suite that
  owns degrade messages is green.

### A2. Change Passport v1, producer (stage: passport; tier: builder with
reviewer verify; ~2.2M; the centerpiece)
Files: NEW schema/change-passport.v1.json, NEW tools/bm_passport.py, NEW
tools/test_bm_passport.py, docs/PASSPORT.md, SUITES registry in
tools/test_all.py (read the registry reader FIRST, PO-6).
- Schema: exactly the five conceptual fields; field 4 "what was NOT
  established" REQUIRED and non-empty (a literal none-claim is valid only
  with an attached justification string); evidence entries carry origin
  (local versus CI) and timestamps; change identity binds to commit range.
- Generator: deterministic from the store and git (two runs, same tree, byte
  identical output modulo generation timestamp field, which lives in one
  place). Reads only public record surfaces, never conversation state.
- Validator: standalone, no BrotherMode imports, runnable by a third party.
- Fixtures: one canonical filled passport, three invalid ones (hollow field
  4, missing accountable human, evidence with no origin).
- Contract test on the SBE side of the seam: generate a passport here, copy
  the FIXTURE (the file is the seam, no cross-repo imports) into the SBE
  suite in Lane B2; sbe_passport.py must report fields 2 and 5 CARRIED.
- Cross-family refutation of schema plus generator before merge, aimed at
  environment inheritance, path handling, and JSON edge cases.
- Done-check: test_bm_passport.py green; validator rejects all three invalid
  fixtures with named reasons; determinism check quoted.

### A3. Gate 1 complaints, the open M-items (stage: named per item; tier:
builder; ~1.4M)
- M2 (stage: required-proof): deliver refuses a project with no goal, no
  build evidence, no review, or prints exactly what is missing. Regression
  test: hollow project, deliver exits nonzero naming the holes.
- M4 (stage: provenance): task add --status routes through the lifecycle
  law or is refused. Test pins the refusal.
- M5 (stage: required-proof): acceptance-check linkage default-on; review
  without a criterion examined says so in the verdict. Test.
- M6 (stage: method): capability detector reads built-in classes correctly;
  no false DEGRADE for the built-ins on a clean machine. Test with a fixture
  home.
- M8 (stage: intent): the guided walkthrough continues from project brief to
  first task creation, so next never reads an empty queue on a fresh start.
  Test: scripted walkthrough leaves at least one ready task.
- M10 (stage: provenance): verify-close on a full pack runs its checks (the
  stale F5 note is cleared; fence free, confirmed tonight). Test: the pack
  fixture from 2026-08-18 gets a verdict, not NO-DATA.
- M1 code half (stage: provenance): everything scriptable lands tonight: the
  install-shape detector (skill-dir clone versus plugin install, hooks wired
  or not) and the one-command migration script, both tested against a
  fixture home. The LIVE swap of this machine's install is FOUNDER-GATED to
  morning (question put tonight), because it changes every session on the
  machine and the cache law wants it at a session boundary.

### A4. Queue hygiene and stage law (stage: intent; tier: fast worker; ~0.4M)
Files: docs/plan/QUEUE.json only.
- The 37 no-stage items each get their true stage or move to parking with a
  one-line reason (the mandate's rule: cannot name a stage, cannot sit in
  the backlog). Done-check: bm_idle.py reports 0 no-stage items, its own
  line quoted.

### A5. Smallest verified-reality record (stage: verified-reality; tier:
builder; ~0.5M, START ONLY IF the total spend is under 6.5M at open)
Files: NEW tools/bm_reality.py, store schema addition, test.
- Record: accepted release identity, who accepted, when, against which
  passport; reopen or rollback or incident entries with a link back to the
  release; a defect entered as a defect creates a new intent row with
  provenance (closes the H4 shape minimally).
- Done-check: round-trip test green, plus bm_idle accepts the new stage rows.

### A6. Lane A close (tier: builder; ~0.3M)
- Release-candidate prep for 3.3.2: VERSION, CHANGELOG, manifests, fresh-clone
  integrity check, UP TO the founder-gated tag step and no further (the
  runbook's own law; two release commits died to trees that moved past them,
  and 3.3.1 is the proof the gate works when respected).
- GANTT.html refreshed and republished to the stable artifact URL; pack
  written, zipped, verify-close verdict quoted; vault log; telemetry line
  with agents, tiers, and real token counts where they exist.

## 4. Lane B: BrotherSBE (the consumer side), about 3.0M

OWNERSHIP AMENDMENT, 23:30 JST: the founder separately granted the LIVE
BrotherSBE session its own overnight run (4,000,000 tokens until 07:00 JST,
recorded in spend-guard.json by that session through its question UI). One
writer per repo is law, so tonight that run OWNS BrotherSBE and this lane
does NOT launch beside it. The B-items below stand as the handoff list: they
run tonight only if that run closes early with budget left, and otherwise
they are the SBE side's next-morning backlog. A2's contract fixture is
self-contained in this repo either way, so nothing in Lane A waits on B.

Path: ~/Documents/BrotherSBE. One writer at a time. Its OWN plan for today,
docs/plans/2026-08-19-v1-finalize-gantt-wbs.md, wins ordering where it
conflicts with this list; name the conflict in the pack.

### B0. Ceremony and the peer's uncommitted work (~0.2M)
A live session held this repo this evening with uncommitted contracts.py
(+334/-40) and test_sbe_contracts.py (+226) plus untracked receipts. Open
with detect and the SBE laws; if that session closed cleanly, adopt what its
pack says; if the work is orphaned, run ITS OWN tests: green means commit
with a pack note naming the origin, red means park to a branch, never
discard, never land blind. Untracked .sbe/break-glass.json and
evidence/gates receipts: investigate meaning before touching.

### B1. Acceptance record, H2 (stage: accountability; tier: builder; ~0.8M)
- The missing object: who accepted, when, against which passport and which
  assurance result; refuses hollow; queryable afterwards ("who accepted
  this" has an answer). Done-check: acceptance without an accountable name
  is refused; a recorded one round-trips; both quoted from the new test.

### B2. Passport handshake (stage: passport; tier: builder; ~0.6M)
- Consume Lane A2's canonical fixture in the SBE suite: fields 2 and 5 go
  from NO-DATA to CARRIED, field 4 renders in the human decision packet as
  the attention list. Contract test lives in BOTH repos against the SAME
  fixture bytes. Done-check: both suites quote the same fixture hash.

### B3. One amber to green, by SBE's own plan (stage: evidence-integrity or
accountability; tier: builder; ~0.9M)
- Either the needed-approval detector (a change matching risk-tier rules
  with no approver recorded becomes a named finding), or the business-impact
  statement object on intake. Pick whichever docs/plans/2026-08-19 names
  first; record the choice as a decision. The CI-id spoofability stays
  DISCLOSED, not silently patched (honesty law: the label may not claim
  stronger than "CI-shaped metadata was recorded").

### B4. Lane B close (~0.3M)
- Version bump if warranted, install-cache refresh to current release
  (C6), pack, vault log, telemetry line.

## 5. Reserve and the morning surface (~1.5M reserve)

Reserve covers: gate re-runs, refutation rounds, one unplanned defect. If
untouched at 05:30 JST, spend it on A5 if skipped, then p7-owed-checks.

By 06:45 JST the last session writes the morning surface: the refreshed
progress page open in front of the founder, the handover zip, and the
founder question cards: (1) tag 3.3.2 yes or no, (2) apply the M1 install
swap with the tested script yes or no, (3) Bitbucket seats when he chooses,
(4) anything a lane parked. UNFINISHED is written as UNFINISHED.

## 6. What tonight does NOT do, recorded as decisions

- No BrotherDS work (mandate: perfect the duo first).
- No runtime expansion beyond Claude Code claims (Gate 7 is later; Cursor
  compat stays at its shipped, labeled level).
- No benchmark publication (Gate 5 needs external users; tonight only makes
  the claims it would test true). Flip: founder names pilot users.
- No Bitbucket pipeline runs (seat limit, free-tier law). Flip: founder
  frees seats.
- No live swap of this machine's BrotherMode install without the morning
  gate (C1/C2 fix is scripted and tested tonight, applied on his yes).
- The mandate itself is not retyped into the repo; the strategy document
  (same authority, richer) landed at the root tonight and this plan carries
  the mandate's deltas. Flip: founder asks for the verbatim mandate filed.

## 7. Coverage map: every complaint to its item

M1>A3+morning gate, M2>A3, M4>A3, M5>A3, M6>A3, M7>A1, M8>A3, M10>A3,
M11>A1, C4>A1, C5>A1, C6>B4, H2>B1, H4/H5 smallest form>A5,
p6-receipt-provenance>A2 (evidence origin in passport), p14-green-scope>A2
field 4, p3-clarify-enforcement>A1 (degrade honesty), p7-owed-checks>reserve,
p12-bitbucket legs>documented BLOCKED (section 2), remaining p-items and
H3/H6 to H8: NAMED as next-morning backlog, not silently dropped; they need
either the founder or daylight design time.

## 8. Launch mechanics

First Lane A session: this session's successor via the continuity tool at
close, IF the founder says go tonight AND the grant block is applied (the
two launch conditions; without the grant the first session dies at the
800,000 baseline mid-item). Lane B does not launch tonight per the section 4
ownership amendment. Watchdog armed at launch by the first night session per
the overnight-watchdog skill; status reports on its contract. If the founder
does not say go, this plan holds until he does; nothing self-fires.
