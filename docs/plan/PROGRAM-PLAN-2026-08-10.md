# BrotherMode program plan, 2026-08-10 night

Status: CURRENT. Written by session `bm1-4a167de53be0a5cce34ce046` (harness id
`11cfa3fc-4175-4237-936b-e66e6106af0c`) against `main` at `d9d8003` (run
`git rev-parse --short HEAD`; do not trust the number after the next commit).
Supersedes nothing: it EXTENDS `docs/plan/RELEASE-v3.1.0-PLAN.md`, whose
replan section remains the law for the release loops it names. No em or en
dashes anywhere in this document.

Fence: store claim `command-center-program` (lifecycle
`11297a2439ac4ecaa360e29b2b8a1302`), files: this file and
`docs/plan/COMMAND-CENTER.html`.

Inputs, each actually read this session:
- Founder north-star brief, 2026-08-10 (`BROTHERMODE_NORTH_STAR_ADVERSARIAL_BENCHMARK_AND_FABLE_FINALIZATION_BRIEF.md`, Downloads, identical md5 across all three copies)
- Evening handover pack (`docs/plan/HANDOVER-2026-08-10-evening.md` and the zip)
- Cursor Codex port spec (`CODEX_PORT_AND_HYBRID_HARNESS_IMPLEMENTATION_SPEC.md`, audited the tree at `c36bd00`)
- `docs/closure/WBS-NORTH-STAR-2026-08-10.md`, `docs/market/CATEGORY.md`, `docs/superpowers/specs/2026-08-10-project-control-dashboard-design.md`
- Three read-only scout reports this session: repo advancement inventory, competitor claim spot-check (five claims, each against a fetched page), Codex spec overlap map

---

## 1. GOAL

North star, unchanged from the founder's brief:

> From intent to a verified, review-ready deliverable with bounded autonomy,
> independent proof, and recoverable state.

Metric: VADR, verified autonomous delivery rate, with its counter-metrics
(interventions, cost, rework, recovery, false refusals, evidence
completeness). The brief's fifteen VADR conditions are the acceptance bar;
several are not yet mechanically checkable and the definition work (Loop B1
below) must mark which are still human-asserted.

Category: a verified autonomous delivery system for a solo builder
(`docs/market/CATEGORY.md` section 1). Strategic posture from the brief:
BrotherMode is the assurance control plane above capable agent runtimes, not
the largest agent framework.

## 2. THE PERSONAS, and what each one actually needs

These drive every core-or-sprawl call below. Sources:
`docs/market/CATEGORY.md` (solo builder), `README.md` (plain-language
contract), brief Loops 8 and 10 (external builders).

| Persona | Who | The need that is CORE for them |
|---|---|---|
| P1, the non-engineer founder | Describes outcomes in plain words, does not read logs, judges by looking | Bounded autonomy that cannot run away (8 August class), one recommended next action, decisions as small windows, a command center that answers "what changed, what needs me, what could bite me", and SEEING the result (preview), not reading its diff |
| P2, the solo builder | Technically capable, no second engineer behind them | The tool supplies what a reviewer would: independent verification against frozen acceptance criteria, receipts newer than the last change, recovery without archaeology |
| P3, the first-time outside builder | Installs it cold, no coaching | One path (start, work, verify, deliver), understands why it stopped when it stopped, first visible value without learning the command taxonomy, and their runtime honestly told what is enforced there (Codex included) |

## 3. WHERE THE PROGRAM STANDS, measured this session

| Item | State | Evidence, run by this session unless marked |
|---|---|---|
| v3.1.0 Loop 0, 1, 3, P | CLOSED | replan table, `RELEASE-v3.1.0-PLAN.md:531` |
| Loop 2, effect classes | LANDED at `d9d8003` | `python3 tools/test_bm_effects.py` printed `Ran 10 tests ... OK` at 21:36 this session; registry `tools/bm_effects.py:76` five classes; registered in `tools/test_all.py:201` |
| Loop 4 truth repairs | docs suite green | `python3 tools/test_bm_docs.py` printed `Ran 226 tests ... OK (skipped=5)` this session; whether 4.5's security-verb check is IN that suite is UNVERIFIED by me |
| Loop 5, live deny canary | LANDED at `d9d8003` | scout cite: `tools/bm_controller.py:5023` `_unattended_fence_canary`, absent in `d9d8003^`; NOT independently refuted yet, which the replan requires before the tag |
| Full gate at current HEAD | NOT RUN | the 2918-count belongs to `c36bd00` and `88b79d2`; no gate verdict exists for `d9d8003`. A colleague session committed `d9d8003` at 21:34 while this session ran; coordinate, do not race it |
| Push state | ahead 1 | `git branch -vv`: `main d9d8003 [origin/main: ahead 1]` |
| Loop 6 Codex audit | NOT STARTED | Codex alive per WBS S0 |
| Loop 7 tag | FOUNDER GATE | not cut without an explicit yes |
| Stale fences | LIVE EXHIBIT | `STATE.md` active list holds 15 claims; at least 9 are provisional records with no objective owned by sessions that ended days ago (judged by hand; no tool judges it, which is the point of Loop SD) |
| Watchdog | DEAD | it was session-bound and its session ended (handover section 4); re-arm is manual |

## 4. WHAT IS MISSING VERSUS THE COMPETITION, core only

Method: the brief's own teardown (section 4, written 2026-08-10), spot-checked
this session by a researcher who opened the cited pages. Verdicts are named so
a chip on the command center cannot overclaim. A gap is listed only when a
persona above needs it as a CORE function; everything else goes to
"will not build".

| Core gap | Competitor evidence, with verdict | Persona | Our answer |
|---|---|---|---|
| One deliverable-scoped governor for budget, concurrency, retries, wall clock | GSD lineage: worktree isolation VERIFIED on its page; budget ceilings and heartbeats NOT substantiated on the pages fetched, so the pressure is real but softer than the brief states | P1 | Loop G1. Our own 8 August incident is the stronger reason |
| Independent verification against a frozen acceptance contract | Superpowers two-stage review, per brief; our verifier is model-authored (`bm_autonomy.py`, scout cite), so independence is unmet TODAY | P2 | Loops V1 then C1 |
| Convergence: findings become appended tasks, bounded | Spec Kit `converge` VERIFIED: "appends them as new tasks under a Convergence section" | P2 | Loop C1 |
| Active stall and orphan detection, recovery as a product action | Cline checkpoints and worktree task cards exist but split across two products (PARTLY); our own scar is five stale fences in one day | P1, P2 | Loop SD, this plan's new feature |
| Native second runtime, honestly probed | Codex native plugin contract VERIFIED (`.codex-plugin/plugin.json`, `codex mcp-server`); our Codex state is a MEASURED enforcement failure published in `docs/RUNTIMES.md:26` | P3 | Lane CX, the Codex port |
| Preview: verify what the user sees | OpenHands and Cline browser surfaces per brief; we have NO browser or screenshot machinery in `tools/` or `scripts/` (scout grep, ABSENT) | P1 | Loop P1, after the core |
| First-run simplicity | OpenSpec one-screen model per brief | P3 | Loop F1, after CX Phase 2 informs it |
| External proof | Nobody has it FOR us; our register says the rung is empty | all | Loop B1 benchmark, then the pilot |

WILL NOT BUILD, from brief section 6, kept visible so sprawl has to argue with
a written list: a model provider, a big role catalog, hundreds of MCP tools, a
container platform (adapter only), generic vector memory without the labelled
corpus, a multi-user PM suite, autonomous production publishing, an agent that
edits its own safety contract.

## 5. THE PLAN: lanes and loops

Two lanes at most, one loop per lane, FINISH FIRST. The release closeout is
alone in front because everything else needs its green committed baseline.

```
NOW                 R: close v3.1.0 (single lane, nothing else opens)
                      R1 gate at HEAD, R2 refute pass on canary,
                      R3 Loop 6 Codex audit, R4 triage, R5 TAG (founder)
                              |
        +---------------------+----------------------+
LANE A  SD  active stall detector                    LANE B  CX Codex port
        CC  command center convergence                       phases 0 to 9
        G1  work governor                                    (Cursor spec,
        V1  acceptance contract + verifier                    corrected)
        C1  convergence engine
        B1  benchmark option A
THEN    P1 preview lane, F1 first-run, M1 memory eval, pilot
```

### Loop R: close v3.1.0. Owner: the colleague session already driving it

Folded from the replan; listed so this plan cannot be read without it.
- R1: `BROTHERMODE_SESSION_CAP=99 python3 tools/test_all.py` on committed
  `d9d8003` or later. Done-check: ALL GREEN with the SHA quoted beside it.
- R2: independent refute pass on the Loop 5 canary, strongest tier, per the
  founder override recorded in the replan. Done-check: the reviewer names a
  hole or states plainly it could not.
- R3, R4: Codex read-only audit, verbatim output filed, triage to zero
  unresolved CRITICAL or HIGH (decision D8).
- R5: tag `v3.1.0`. FOUNDER GATE, an explicit yes in the moment.

### Loop SD: the ACTIVE STALL DETECTOR, the feature this plan adds

North star objective: recoverable state. Scars that earn it: five stale
fences on 2026-08-10 alone (README.md, SKILL.md twice, findings ledger, the
narrowing work itself); the watchdog dying with its session; nine provisional
claims sitting in STATE.md right now with no living owner.

What already exists, so this builds on it instead of beside it (scout cites):
`bm_controller.py:1797` heartbeats and `:2434` orphan resume, but only INSIDE
a Full-Auto run; `bm_continue.py:801` `process_alive` and `:834`
`liveness_verdict`; adopt verbs in `bm_controller.py:4378` and
`bm_threads.py:978`. The gap: nothing sweeps the STORE's fences and claims for
dead interactive sessions, and nothing runs when no controller is running.

| ID | Step | Files | Done-check |
|---|---|---|---|
| SD1 | Liveness oracle: one function that says whether a claim's owner session can still return (pid alive, heartbeat age, session registry), with the PID-reuse caveat stated in its docstring | `tools/bm_stall.py` (new) | synthetic live and dead sessions in a tempfile store judged correctly, both directions asserted |
| SD2 | The sweep: enumerate active claims and fences, emit findings (stale fence, dead-owner provisional record, expired TTL, uncommitted work recorded to a dead session). RED FIRST against a fixture reproducing the five 2026-08-10 cases | `tools/bm_stall.py`, `tools/test_bm_stall.py` (new) | the test fails naming all five fixture cases before the sweep exists, then passes; a NO-DATA sweep (hollowed inputs) never returns PASS |
| SD3 | Purity: register the sweep as `pure_read` | `tools/bm_effects.py` | `python3 tools/test_bm_effects.py` OK after registration, proving the sweep changes zero bytes |
| SD4 | Surface at session start, fail open like the progress check | `tools/bm_sessionstart.sh` | the hook exits 0 with the tool deliberately absent; with a synthetic stale fence present, its output names it |
| SD5 | Clearing verbs: print the exact `bm_store` release or adopt command per finding, NEVER run it (dashboard decision D-3) | `tools/bm_stall.py` | a test runs the printed command and the finding clears; the sweep itself performed no write |
| SD6 | Registration in all four places, checksums last | `tools/test_all.py`, `.github/workflows/tests.yml`, `pyproject.toml`, `tools/write_sites.json`, `CHECKSUMS.sha256` | `python3 tools/test_bm.py` OK; `bash scripts/verify-install.sh` exit 0 |

Deliberately OUT of SD (recorded as a decision, flip condition named):
auto-adopt or auto-release. The sweep reports and proposes; a human or an
explicitly authorized controller acts. FLIP: if a month of reports shows the
same clearance accepted every time, propose an allow-listed auto-clear as its
own reviewed change.

SIZE: 0.5 to 1.5 days, MEDIUM-HIGH confidence. Variance is in SD1: session
liveness across interactive and headless sessions may need a heartbeat file
the store does not yet write.

### Loop CC: command center convergence

The dashboard spec's S1 to S7 (`docs/superpowers/specs/2026-08-10-...md`),
approved by the founder, scheduled after the tag. SD lands first because the
spec's check 2 (dead-owner fence) IS the stall detector; CC consumes it
instead of reimplementing it. The interim hand-kept page this session ships
(`docs/plan/COMMAND-CENTER.html`) is absorbed by the generator in S7 and then
DELETED, per decision D-1. Done-checks: as written in the spec, S1 to S7.
SIZE: 1.5 to 3 days, MEDIUM confidence (unchanged from the spec).

### Loop G1: the work governor

Brief 3.1 and Loop 2 of the brief. Unify what the inventory found scattered:
controller timeouts and retries (`bm_controller.py:905,:2258`), the signed
autonomy contract (`bm_autonomy.py:398`), the session cap
(`bm_session_cap.py:62`), the spend guard (machine hook). One policy object
per work item; per-work-item concurrency (today only the session level is
capped, scout finding). Acceptance adversaries from the brief: recursive
spawn, dead meter, absent cap hook, prose-ignoring worker, stall, retry loop,
orphan child, two controllers one work item. Done-check: every adversary stops
mechanically inside its declared bound, each as a test. SIZE: 2 to 4 days,
MEDIUM confidence.

### Loop V1: acceptance contract with an independent verifier

Brief 3.5, 3.6, Loop 5 of the brief. Freeze criteria before implementation
(the `done_definition` freeze already exists at `bm_autonomy.py:439`; what is
missing is INDEPENDENCE: today the verifier is model-authored by the same
flow, scout cite). Fresh-context verifier, information boundary, stale
evidence rejected. The Codex lane makes the cross-model verifier cheap later
(CX Phase 6's controller is the same seam). Done-check: the brief's seeded
defect matrix (weakened tests, mocked behavior, stale evidence) caught at a
pre-registered rate. SIZE: 2 to 4 days, MEDIUM confidence.

### Loop C1: convergence engine

Brief 3.7, Spec Kit's verified pattern with stronger evidence semantics:
verifier findings append tasks, bounded rounds, deterministic checks outrank
judgment. Depends on V1. Done-check: a seeded three-gap task converges without
human re-prompting, within its round ceiling. SIZE: 1 to 2 days after V1,
MEDIUM confidence.

### Loop B1: benchmark, option A first

Brief Loop 1 and WBS S1. `scripts/benchmark_comparative.py` exists with one
recorded run (2026-08-07) and a real evidence file
(`docs/evidence/benchmark-run-2026-08-10.json`, bare vs brothermode arms);
what is missing is the corpus and the blind grading, stated by the doc itself.
Build `docs/NORTH-STAR.md` with VADR and the column naming which of the
fifteen conditions is mechanically checkable today. Done-check: the corpus
runs twice from identical snapshots with mechanically comparable output.
SIZE: 2 to 4 days for option A, MEDIUM confidence.

### LANE B, Loop CX: the native Codex port. FOUNDER PRIORITY, added tonight

Source: the Cursor spec, phases 0 to 9, with these corrections from the
overlap map (each cite is the scout's, verified against the tree):
- Phase 0 pins `d9d8003` or later, not `c36bd00`, and must RE-COUNT the
  baseline: the 2918 number belongs to two older commits; `test_bm_effects.py`
  added 10 tests since.
- Phase 3 does not reinvent purity or denial proofs: it extends
  `tools/bm_effects.py` and generalizes the landed canary pattern
  (`bm_controller.py:5023`) cross-host instead of writing a Codex-only one.
- Phase 4's build gate adds the repo's own four-places registration contract
  (SUITES, CI step, py-modules, write_sites) for every new module, or the
  existing gate refuses the tree.
- Phase 6's worktree module is the SAME seam as WBS N3: whichever lands first
  owns `git worktree` creation, the other consumes it.
- Tiering, declared now so dispatch briefs inherit it deliberately: phases 0,
  4, 5 cheap tier; 2, 8 middle tier; 1, 3, 6, 7, 9 strongest tier.
- The spec's own non-negotiables stand: no fence-enforcement claim on Codex
  without a release-specific live canary, no hidden chain-of-thought as
  protocol, executor never merges or pushes, hybrid planner is Fable or Opus.

Gates are the spec's own phase gates, verbatim. START CONDITION: Loop R
closed (Phase 0 requires the clean green committed baseline). SIZE: the spec
does not date it and neither will this plan; phases 0 to 5 (native plugin
installable) 4 to 8 attended days, MEDIUM-LOW confidence; phases 6 to 9 (hybrid
harness to release candidate) 5 to 10 further days, LOW confidence. Both
ranges assume the Codex contracts behave as documented, which Phase 0 and the
canaries exist to test rather than assume.

### AFTER THE CORE: P1 preview lane, F1 first-run simplicity, M1 memory
evaluation, then the external pilot (brief Loop 10). Parked, not dropped;
each already carries its north star objective in section 7 of the release
plan's parking lot.

## 6. FOUNDER DECISIONS, answered 2026-08-10 night through the question windows

1. Plan ordering: APPROVED as written (R alone first, then SD+CC in lane A
   against CX in lane B). Alternatives shown and declined: CX jumping the
   queue, reworked lanes.
2. SD scope: SWEEP AND PROPOSE only. Auto-adopt declined for day one; the
   flip condition stands as written in Loop SD.
3. CX start: AFTER THE TAG. Immediate worktree start against a stale
   baseline declined.
4. The tag itself, when R1 to R4 are green: still open, Loop R5, an explicit
   yes in the moment, not here.

R1 note, added after the fact: the full gate ran green at `1c6fcf4`
(`test_all: 2944 tests across 30 suites, 9 skipped, 622.5s wall. ALL GREEN`,
exit 0), driven by the colleague session; this session read the sentinel and
exit code rather than the claim.

## 7. WHAT THIS PLAN DOES NOT KNOW, stated rather than implied

- Whether the colleague session's full gate at `d9d8003` is green; no verdict
  exists yet for that SHA anywhere.
- Whether Loop 4.5's security-verb check is inside the 226 green docs tests or
  was honestly dropped; the suite passing cannot distinguish those.
- Session liveness across window closes and machine sleeps (SD1's hard part)
  is designed from the store's data, not yet measured.
- Competitor rows marked PARTLY carry exactly the nuance the researcher
  found; nothing here is a hands-on trial of a competitor.
- Every size is a range with confidence, and the CX ranges are the least
  trustworthy numbers in this document.
