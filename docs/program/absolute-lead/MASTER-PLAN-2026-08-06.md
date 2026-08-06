Status: CURRENT as of 2026-08-06. The plan of record for BrotherMode, ratified
by the founder through sixteen decision windows on 2026-08-06. Every future
session reads this page before touching the backlog. No em or en dashes.

# BROTHERMODE MASTER PLAN

This page exists because four failures were named by the founder on 2026-08-06
and confirmed against the record: no end to end vision or architecture direction
was ever written before work started, subagent fleets ran with no model tiers
and no budget, backlog items were started in the wrong order and left
unfinished, and learnings from past sessions were recorded but never absorbed.
Sections 2 through 4 are the fixes. Section 5 is the sprint that finishes the
open backlog under the new laws.

---

## 1. THE NORTH STAR

By 2026-08-20, BrotherMode is EVIDENCED and REACHABLE:

1. A stranger can install it from the public instructions and succeed, with the
   run recorded as evidence.
2. A measured number exists comparing work with BrotherMode against work
   without it (the comparative benchmark, run at last).
3. The newest work is actually shipped: v2.1.0 is tagged and the documented
   install delivers it.
4. Every founder instruction from 2026-08-05 is delivered or explicitly
   withdrawn with a recorded decision. None is silently dropped.

Primary persona: the non-engineer founder who runs a real project through an AI
team and needs plain language, one page, one recommended action, and safety
they never have to think about. Every architecture and backlog decision is
tested against this persona first.

Success measure: the independent audit of 2026-08-06 scored the product 6 of 10
and named the empty columns (evidence that it helps anyone: 3, reach: 3). This
sprint attacks exactly those two columns. Craft and honesty already score well
and get no new investment until evidence catches up.

What this deliberately excludes, so nobody relitigates it mid sprint: the
17,884 line store module is NOT refactored, Windows is NOT ported, the
documentation mass is NOT reduced, and no new capability is started. The audit
is explicit that none of these moves the score while zero outside users exist.

---

## 2. LAW 1: GOAL FIRST, THEN ARCHITECTURE, THEN PLAN

Founder rule, absolute, ratified 2026-08-06:

- No work starts without a stated goal, an architecture direction that serves
  it, and a plan whose steps name their files and done checks. In that order.
- The north star and the architecture evolution path stay visible on every
  backlog change: an addition that cannot name which north star objective it
  serves goes to the parking lot, not the backlog.
- The orchestrator (Fable) owns this framing. Subagent briefs restate the goal
  so no worker can drift from it unnoticed.

Where it is codified, all three layers, so no session can miss it:

1. The founder global CLAUDE.md (binds every session on this machine).
2. This repository: SKILL.md routing plus references, and this page as the
   plan of record, added to the after compaction re read list.
3. The product rule store, as a founder approved rule retrieved mechanically
   before substantial work (approval is the founder's hand, through the
   approval window, per the store's own receipt gate).

Codifying all three is sprint item P0 and happens on day 1.

---

## 3. LAW 2: THE SWARM RUNS ON NAMED TIERS AND A BUDGET

Ratified 2026-08-06, replacing the inherit by default habit that the
2026-08-05 run itself flagged as a failure (its item F4):

- Every dispatch brief names its TIER and the reason, in the brief itself:
  cheap tier for mechanical sweeps and inventories, middle tier for well
  scoped implementation and search, strongest tier only for architecture,
  adversarial review, judging, and final synthesis. An unstated tier is a
  violation and goes in the mistakes ledger.
- Independent subagents launch as one wave. Returns are capped near 1500
  tokens and substantial output goes to files, never to chat.
- Overnight autonomous runs carry an explicit budget in the autonomy
  contract: 8,000,000 output tokens per run, soft stop at 80 percent (no new
  dispatches, in flight work finishes), hard stop at 100 percent.
- Every fleet closes with one telemetry line: agents launched, tiers used,
  estimated tokens. The weekly review reads these lines against the rubric.
- Credential blocked deliverables are enumerated at hour zero of any
  unattended run and put to the founder before he sleeps, never discovered at
  hour six (the 2026-08-05 run lost three deliverables to exactly this).

---

## 4. LAW 3: FINISH FIRST. LAW 4: LEARNINGS ARE ABSORBED, NOT FILED

Sequencing law, ratified 2026-08-06:

- At most two lanes run in parallel, each with its own fence. One loop per
  lane. A loop CLOSES before the next opens: done check run after the last
  edit and quoted, every recorded delta applied by name, evidence filed.
- Nothing new starts while a founder answered instruction sits undelivered.
  An undelivered founder answer outranks all other work.
- Every session opens by reading the open items and closes by updating them.
- Deciding NOT to do something the founder chose is a DECISION: recorded at
  the moment it is taken, with alternatives and a flip condition, never
  discovered in a morning report.

Learnings law:

- The sixteen mistakes of the 2026-08-05 run are imported into this
  repository with their rules (sprint item P0) so the failure index, not a
  zip file outside the tree, carries them.
- The loop template gains two standing steps from those learnings: a DELTAS
  step at close (collect every "delta for you" line from every worker report
  and close each by name, which is the M16 class) and a REFUTE THE ACCOUNT
  step (point an adversary at the session's own claims, not only its code,
  which found five reporting defects in one hour on 2026-08-06).
- Gates run on a quiet tree: a suite claims the tree for its whole run, and a
  result from a run that overlapped an edit is no result at all.

---

## 5. ARCHITECTURE DIRECTION AND EVOLUTION PATH

What the architecture IS today, in five lines: one SQLite store per project
behind a single module that owns every write and refuses by named reason
codes; a resumable controller that records intent before effect; a signed
autonomy contract with six floors no contract can grant; one hook that can
refuse a write before it happens; generated views (page, canvas, briefs) that
render store rows and never hold a second truth. Zero dependencies, standard
library only.

Direction for this sprint: the architecture is FROZEN except four surgical
changes, each fixing a measured defect:

1. Land the autosave environment scrub (commit ec5f060, currently unpushed in
   a hidden worktree, the highest severity item on the machine).
2. Fix the class where a test rewrites a tracked file, which silently
   disables the product's own tamper check (audit W3, mistake M13).
3. The telemetry lock shared with the sister project's writer (founder
   approved 2026-08-06 in this channel).
4. Small guards: the unguarded controller timeout method, the two recorded
   dash guard deltas, the refusal code with no plain language entry.

Evolution path beyond the sprint, each step gated on evidence, not appetite:

| Step | What has to be true first |
|---|---|
| Split bm_store along its three natural seams (learning, controller, protocol tables), facade kept | Three or more external users exist and the suite is green on a measured baseline |
| Second runtime enforcement beyond Codex | A live rehearsal on that runtime proves the fence fires; UNVERIFIED rows are never wired |
| Windows support beyond the store layer | A Windows machine is available and a user asks for it; until then the register row is renamed to what is true |
| Performance and scale work | The store is measured at size once (50,000 rows) and the bound written into KNOWN LIMITS |

---

## 6. THE 14 DAY SPRINT, 2026-08-07 TO 2026-08-20

Two lanes, finish first, one loop per lane. Every loop runs the twelve step
shape from the 2026-08-06 handover (fence, red, build, refute, re run, gate,
manifest, verify, commit, push, read CI, close) plus the two new steps from
Law 4. Estimates are ranges with confidence; the actuals move the next
forecast.

### Lane A: SHIP (the release path)

| Days | Loop | What closes | Done check | Founder |
|---|---|---|---|---|
| D1 | P0 | Laws codified in all three layers; stale push gate superseded; 16 mistakes imported; branch caption adjudicated; dash guard deltas applied; 13 stale rows archived | test_bm_docs green; rules visible in bm_learn; store dashboard shows rows archived | Approval windows, about 15 minutes |
| D2 | A1 | ec5f060 refuted, rebased onto main, gated, pushed; telemetry lock fix landed | Full gate green after last edit; grep shows the environment scrub present on main | none |
| D3 to D4 | A2 | The test that rewrites a tracked file writes to an untracked path instead; a guard test asserts every suite leaves the tree clean; doctor compares against the git index instead of skipping on dirt | Full gate green AND git status empty afterwards, both quoted | none |
| D5 | A3 | Outside install test: both documented paths followed literally on a clean account, every divergence recorded and fixed in the same change; live Codex fence rehearsal, both directions calibrated | Evidence files exist; verify-install PASSED on the clean install; the Codex block names the file and owner | About 1 hour install, 15 minutes Codex |
| D6 | A4 | Release: full gate on a quiet tree, manifest last, verifier PASSED, push, CI read green, then the tag | CI green on the final commit | Cut and push v2.1.0, about 10 minutes |
| D7 | A5 | Deployment closeout per section 8: docs repasted, version bumped to next dev identity, fresh clone of v2.1.0 verified, the stale live install on this machine upgraded | Fresh clone verifies PASSED; doctor 10 of 10 on this machine; the schema warning at session start is gone | none |

### Amendment 1, 2026-08-06: four founder asks added after ratification

Recorded here rather than absorbed silently, because Law 1 says an addition that
cannot name its north star objective is parked rather than backlogged. The
watchdog caught the first of these landing with no plan entry, which is the
drift this clause exists to stop, and the entry below is the correction.

| Added | Serves | Where it lands |
|---|---|---|
| The installer feedback loop and one week questionnaire | Objective 1 (a stranger installs and succeeds) and objective 4 (nothing dropped silently): it is the instrument that MEASURES objective 1 | DONE, commit e4da2c1, day 1 |
| Progress reporting as a core product artifact | Objective 1 and objective 4: the founder must answer where the project stands from one place, including what is blocked and what is being done about it | Spec landed at docs/program/absolute-lead/DESIGN-progress-surface.md; BUILD deferred to the loop after the tag, see the decision below |
| The Haiku drift watchdog at every loop close | Objective 4: nothing dropped silently, including by me | DONE, day 1, first run found real drift; report at evidence/L10/DRIFT-AUDIT-1.md |
| Fast-track the v2.1.0 tag to today | Objective 3 (the newest work actually reaches people), pulled forward because the founder is sending the repository link to friends now | Lane A, day 1, replacing the day 6 slot |

DECISION TAKEN BY THE ORCHESTRATOR, founder may overrule. The progress surface
is NOT in the v2.1.0 tag. It is new code in `tools/bm_visual.py` and
`tools/bm_view.py`, the largest body of code in this repository that has never
been adversarially reviewed, and the first outside users BrotherMode has ever
had are installing this tag. Shipping untested new code into that moment is the
exact risk this plan exists to avoid. ALTERNATIVE CONSIDERED: delay the tag by a
day and include it, which the founder explicitly declined when he chose to
fast-track. FLIP CONDITION: he says he would rather wait for it. Otherwise it
ships as the next loop and reaches them through `/brotherme-update`.

ALSO PULLED FORWARD into day 1, not in the original table: closing the M13 class
(a suite rewrites a tracked file, so the product's own integrity check fails
after its own documented procedure). Original slot was lane A days 3 to 4. It
moved because the documented quickstart tells a new user to run the tests and
then the doctor, in that order, so every friend receiving this link would hit
it, and being told "do not trust this installed copy" is the worst available
first impression.

### Amendment 2, 2026-08-06 night: four founder answers, one correction, one refutation

Recorded at the moment they were taken, per Law 1 and Law 3.

Founder answers, given through decision windows in the review session of
2026-08-06 night:

1. TAG TIMING: the watchdog design amendment lands on main FIRST, then the
   founder cuts v2.1.0 on the new HEAD after the gate and CI are green. This
   supersedes the handover's instruction to tag 724b0a4 directly.
2. WATCHDOG BUILD: stays deferred until after the tag and the deployment
   closeout, as recommended. The recorded decision under Amendment 1 stands.
3. BENCHMARK: the orchestrator probes ONE cell immediately after the review
   session closes. If the nested session cannot authenticate, the exact
   unblock goes to the founder the same day.
4. STRANGER OUTREACH: drafting waits until the tag exists. The calendar cost
   of that wait is accepted by the founder.

CORRECTION to the Lane A table, found by an independent audit agent this
session: A1 is PARTIAL, not done. The autosave environment scrub and its
class closure landed (d7e2e67, 60d10b3), but the telemetry lock fix named in
the A1 row and in architecture item 3 has NOT landed: no commit after
ratification touches it, and wave 21 FENCE G, which owns tools/bm_telemetry.py,
is still live. The item stays open in Lane A rather than being marked done by
proximity.

REFUTATION RECORD: the watchdog design (DESIGN-watchdog.md) gained Amendment 1
this night after three refuters and two auditors returned nineteen findings,
sixteen reproduced against source. The two-layer split, receipts, per
observation voiding, the sidecar floor, and the calibrated registry check all
came out of that pass. The build estimate moves from one to two sessions to
two to three sessions, moderate confidence, because the amendment added a
schema table, a sidecar, and a ninth plan step.

REGISTRY CLEANUP, same night: wave 17 fences A through E marked LANDED on
their lines with their commits; wave 21 FENCE D2 closed as landed via 447b73c;
wave 20 FENCE D flagged queued-and-ready (its dependencies landed) with the
dispatch decision owed to the next session that opens lane work. The fence
hook itself refused this amendment's first write because FENCE E was still
unmarked, which is the stale-registry class firing live, and the closure
above is the remediation the hook named.

### Lane B: PROVE (the evidence path)

| Days | Loop | What closes | Done check | Founder |
|---|---|---|---|---|
| D1 | B1 | One benchmark probe cell from this authenticated environment; if the nested session cannot sign in, the exact unblock goes to the founder the same day | A real transcript and checks.json exist for the probe cell, or the blocker is named with its fix | 15 minutes only if blocked |
| D2 to D3 | B2 | The full 12 cell benchmark run; blind grade of the two judgement cells per the frozen rubric; results table filled from checks.json only; every number labeled INTERNAL EVIDENCE; an adversary argues the numbers are a harness artifact before they are believed | Artifacts exist under the BENCH evidence directory and the table cites them | none |
| D4 to D5 | B3 | The visual surface (largest unrefuted code body) gets three parallel refuters on the strongest tier: correctness, safety and privacy, failure surface; each must reproduce before reporting; one RED first fix loop after | Both view suites green with no count drop; every confirmed finding has a closing test | none |
| D6 to D7 | B4 | Stranger study launch: the founder names his people; the ask, install link (v2.1.0 once tagged), and ten minute debrief script go out | Outreach sent to at least 3 people; study protocol filed | Name the people, send the asks, about 1 hour |
| D8 to D10 | B5 | Stranger debriefs recorded verbatim as evidence; page fixes land in the same change that finds them; register gains the blocked_on field so nine beta rows collapse into one named blocker; the front door example stops promising an unmeasured capability | Debrief evidence files exist; register test green; README example maps to a certified row | Availability of the 3 people governs the calendar |
| D11 to D12 | B6 | The status line and clickable footer links, the 2026-08-05 answer 7 finally delivered: a flat JSON status surface, a fail silent script, opt in docs, tests for shape and fail silent paths | JSON shape and fail silent tests green; regex matches a real trace tag and not prose | Paste one settings block if he wants it on |
| D13 | B7 | Structural debt: the four copy hook wiring generated from one source; the controller timeout method guarded; the printf residual decided and recorded; bak and DS_Store hygiene proposed (deletion stays founder only) | Install and docs suites green; the comparison test now guards a generator | Approve or decline the deletions |
| D14 | CLOSE | Sprint close: scorecard against the rubric, telemetry review of every fleet, felt outcome question, the next horizon planned from actuals, vault log written, handover pack refreshed | Scorecard filed with evidence per line; self score capped at 8 without external evidence | 30 minute review |

Wall clock estimate for the whole sprint: 10 to 14 working days, moderate
confidence. The two calendar risks are the stranger availability (B5) and the
benchmark wall time (4 to 12 hours, unattended). Token estimate: 15 to 25
million output tokens across the sprint, low confidence, reported per fleet as
the sprint runs.

---

## 7. FOUNDER GATE SCHEDULE

Batched so each sitting is short. Total about 4 hours across two weeks,
inside the 5 plus hours per week the founder committed on 2026-08-06.

| Day | What only the founder can do | Time |
|---|---|---|
| D1 | Approval windows: the store rules (Law 1, Law 2, Law 3), the supersede of the stale push gate | 15 min |
| D1 | If the benchmark probe is blocked: one sign in | 15 min |
| D5 | The outside install test account or machine, and the Codex sign in for the live rehearsal | 75 min |
| D6 | Cut and push the v2.1.0 tag | 10 min |
| D6 to D7 | Name the stranger study people and send the asks | 60 min |
| D14 | Sprint review and the felt outcome question | 30 min |

Standing gates unchanged and absolute: credentials, payments, tags, merges,
publication, destructive operations, production actions, rule approval.

---

## 8. DEPLOYMENT PLAN FOR v2.1.0

The release is a two step act and the gap between the steps is a known trap
(the suite goes red between the tag and the doc repaste; budget for it, do not
be surprised by it).

1. Proof chain on the final commit: full gate on a quiet tree written to a
   file, manifest regenerated LAST, verifier PASSED, push, CI read green.
2. FOUNDER: `git tag -a v2.1.0 -m "BrotherMe 2.1.0"` and push the tag.
3. Same sitting: regenerate the pinned install command, repaste it into the
   three install pages, bump VERSION to the next development identity, commit,
   push, read CI green again.
4. Verify from outside: fresh clone of v2.1.0 into a clean directory,
   verify-install PASSED, doctor clean.
5. Upgrade this machine's own installs: the live clone at
   ~/.claude/skills/brothermode still runs 2.0.0-rc.12.dev1 and cannot read
   the schema 17 store, which is why every session start prints a STORE
   CORRUPT warning today. Upgrade it to v2.1.0 and re run doctor to 10 of 10.
   Then the plugin path once, so both documented paths were exercised on a
   current build.
6. The stranger study installs v2.1.0, never v2.0.0, so the study measures
   the product this plan ships.

---

## 9. METHOD GROUNDING

The laws above are not invented in a vacuum. A research pass on 2026-08-06
(sources opened and read, not remembered) grounds them in published practice:

- Kanban WIP limit research: start only as much work as you finish; limiting
  work in progress raises throughput and reveals bottlenecks
  (businessmap.io, Atlassian). This is Law 3's finish first rule.
- Reinertsen flow: sequencing by cost of delay per unit of effort beats first
  come first served, and halving batch size halves cycle time (Principles of
  Product Development Flow). This is why the sprint ships small loops that
  each close fully.
- Shape Up (Basecamp): a fixed appetite per bet and a no extensions circuit
  breaker; work not shippable inside its box is cut or rescoped at the next
  checkpoint, never silently extended. Each sprint loop carries an appetite
  and the D14 close is the betting table for the next horizon.
- Definition of done research (Scrum.org, Visual Paradigm): done must be a
  mechanical checklist, not a feeling. Every loop's done check is a command.
- Trunk based development: small changes land on the main line at least daily
  and the tree stays continuously releasable. This matches the existing push
  at every green close cadence.
- North star and RICE (Mixpanel, Intercom via LogRocket): one metric that
  reflects customer value, with a confidence term that forces "go get more
  evidence" when a number cannot be stated. Backlog additions here must name
  their north star objective for exactly this reason.
- Anthropic's multi agent engineering findings (anthropic.com/engineering):
  fleets pay 4x to 15x the tokens of a chat, so multi agent runs only when the
  task is genuinely parallel and worth it; the lead agent scales subagent
  count to task complexity; every brief carries objective, output format, and
  boundaries or workers drift and duplicate. This is Law 2's shape.
- Model routing practice (mindstudio.ai): frontier models for orchestration,
  ambiguity, and high stakes output; cheap models for bounded execution and
  extraction; routing by role, not by habit. This is the tier table in Law 2.
- Judge reliability research (sonarsource.com, adaline.ai): model judges carry
  position, verbosity, and self preference biases, so the one load bearing
  gate is always a deterministic check (a command), and refutation beats
  confirmation. Already this repository's strongest habit, now a standing
  step in every loop.

---

## 10. RISKS AND HONEST UNKNOWNS

- The benchmark's nested sessions may still refuse to sign in even from an
  authenticated environment. Flip condition: the founder runs the one command
  in his own terminal. No number is ever faked either way.
- The live Codex rehearsal may prove the fence does NOT fire under Codex's
  trust model. Then the claim is corrected, not defended; that outcome is a
  successful rehearsal too.
- The stranger study depends on people who have not yet been asked. If none
  can run before D10, B5 moves past the sprint boundary and the sprint close
  says so plainly.
- One observation remains unexplained on the record: a tracked file once
  reverted on its own after a suite run on this machine. If it recurs, that
  thread gets pulled before anything else in lane A day 3.
- Not audited: 14 undated pages under docs sit outside both documentation
  guard regimes; one audited page of that class was wrong. They get a sweep
  in B7 or an explicit deferral at sprint close.
