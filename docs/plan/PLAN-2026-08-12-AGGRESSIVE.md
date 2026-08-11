# The aggressive replan: short range, week range, long range

Status: CURRENT. Supersedes the schedule in `REPLAN-2026-08-12.md` section 3
and the windows in `LONG-RANGE-PLAN-2026-08-11.md`. Every objective, decision
and override in those files still stands; only the timing model and the queue
change.

Written 2026-08-12 01:30 JST, after the founder scored the previous plan
**3 out of 10** and said the forecasting is bad because the work always
finishes earlier than planned, and that a night spent on that plan would have
idled.

---

## 1. The outcome first

Two things ship tonight that did not exist before: a **measured** forecasting
system that corrects itself from history rather than from judgement, and an
**idle check** that mechanically refuses to let a session sit still while work
is queued. Everything else in this file is the plan those two make honest.

The one recommended next action for the founder in the morning: read section 2,
because it is the part that changes how every future estimate is produced, and
it is the part that would have prevented last night.

---

## 2. Why the estimates were wrong, and the model that replaces them

### The evidence

| Task | Forecast | Actual | Ratio | Basis |
|---|---|---|---|---|
| Tag cut and pushed | by 02:00 | 00:27 | 4.4x fast | judged |
| Install rehearsed | by 04:00 | 00:45 | 5.0x fast | judged |
| Whole release path | 8 hours | ~90 minutes | 5.3x fast | judged |
| Full battery | 10 to 20 min | 12.5 min | accurate | measured |

Four points. Every judged estimate was wrong by four to five times, all in one
direction. The single measured estimate was right. That is not noise, it is a
systematic bias with an obvious correction.

### The root cause, stated precisely

Judged estimates were sized in "how long would a careful person take". That is
the wrong unit for two separate reasons, and they pull in opposite directions,
which is why nobody caught it:

1. An agent does not type, does not context-switch, does not tire. On
   well-specified work it is roughly four times faster than the human unit.
2. An agent pays full price for every wrong turn. On badly specified work it
   is SLOWER than the human unit, because a human notices the wrong turn
   sooner.

So the multiplier is not a property of the task size. It is a property of **how
well specified the task is**. A task whose files and done-check are named runs
at 4x. A task that has to be figured out first runs at 1x or worse.

### The two-clock model, binding from now on

Every estimate is split into two clocks before a number is stated:

| Clock | What it covers | Calibration |
|---|---|---|
| **Agent clock** | Work an agent does alone: code, tests, docs, analysis, packaging, review | Divide the human-unit instinct by the measured multiplier (currently 4.4, n=3) |
| **Wall clock** | Anything that needs real elapsed time or another person: a pilot day, a team running for a week, a founder gate, a CI queue, a release soak | Compresses by exactly zero. Never multiplied |

A plan that states one number for a mixed task is wrong by construction. The
old long-range plan gave R1 a four day window; the agent-clock part of R1 is
about five hours and the wall-clock part is a founder gate. Those are not the
same four days, and calling them four days hid which one was actually binding.

**The corollary that matters for the roadmap:** once agent-clock work is
divided by four, almost every remaining window is wall-clock bound. The
schedule stops being about how fast the code gets written and starts being
about how fast people can look at it. That is the honest aggressive plan: not
"we go four times faster", but "the code is no longer the constraint, so stop
scheduling as if it were".

### Enforcement, stated plainly

This section is prose, and prose is not a control. The control is
`tools/bm_forecast.py`, built tonight, which:

- records every forecast with its basis (judged or measured) and its clock;
- records the actual at close;
- computes the multiplier from real history and refuses to invent one when
  history is too thin (NO-DATA, never a pass, never a made-up number);
- fails a check when a forecast was made and no actual was ever recorded
  against it, which is the failure mode that let this bias survive.

Seeded with the four rows above, so it is calibrated from the first run rather
than after a month of collecting.

---

## 3. Short range: tonight, 01:30 to 07:00 JST

Hard stop 07:00 JST per the overnight law. Nine loops, ordered, each
independently startable, none needing a founder answer. Forecasts below are
agent-clock and already divided by 4.4.

| # | Loop | Files | Done-check | Agent clock |
|---|---|---|---|---|
| L1 | This plan and the machine-readable queue | `docs/plan/PLAN-2026-08-12-AGGRESSIVE.md`, `docs/plan/QUEUE.json` | both files exist, `python3 -c "import json;json.load(open('docs/plan/QUEUE.json'))"` exits 0 | 15 min |
| L2 | Forecast telemetry tool, tests first | `tools/bm_forecast.py`, `tools/test_bm_forecast.py` | `python3 tools/test_bm_forecast.py` exits 0 | 35 min |
| L3 | Idle check tool, tests first | `tools/bm_idle.py`, `tools/test_bm_idle.py` | `python3 tools/test_bm_idle.py` exits 0 | 30 min |
| L4 | Register both in the gate and the write inventory | `tools/test_all.py`, `tools/write_sites.json`, `.github/workflows/tests.yml`, `pyproject.toml` | the inventory check inside `test_all.py` names neither tool as missing | 15 min |
| L5 | Tester package, both products, one bundle | `docs/team/TESTER-PACK.md`, `docs/team/INSTALL-CARD.md`, BrotherSBE side | a person with neither product installed can follow it to a first green check | 40 min |
| L6 | Progress page under the absolute structure | `docs/plan/GANTT.html` | opens in front of the founder, two charts, every tick carries quoted output | 30 min |
| L7 | Full battery at the final tree | none | `tools/test_all.py` exits 0, quoted | 13 min measured |
| L8 | Push, close pack, verify-close | `docs/handover/2026-08-12-*` | `bm_handover.py verify-close` prints PASS | 20 min |
| L9 | Overflow, never runs dry | see `QUEUE.json` | per item | remainder |

**Total committed agent clock: about 3 hours 20 minutes against 5 hours 30
minutes available.** The gap is deliberate and is the whole lesson of last
night: the overflow queue in `QUEUE.json` holds seventeen further items, which
is more than double the remaining time at the measured rate. Running out of
queue is now a reported defect, not a quiet stop.

**Reforecast triggers tonight:** the battery goes red; a tool needs a second
design pass; the BrotherSBE side turns out to need a release rather than a
document. Any of those and the actual gets recorded against the forecast
before the next loop opens.

---

## 4. Week range: 12 to 18 August

The sprint cadence in `SPRINTS-2026-08-12.md` is unchanged: one week, turning
Monday, one release per boundary and only if green, both products reviewing
together and versioning independently.

What changes is the content, because the agent-clock work that filled the old
Sprint 1 is finished or finishes tonight.

| Day | Committed | Clock | Why this day |
|---|---|---|---|
| Tue 12 | Tonight's nine loops land. Tester pack published to the team channel | agent | Already in flight |
| Tue 12 to Wed 13 | First two testers install from the pack, cold, on their own machines | **wall** | This cannot be compressed. It is the first real measurement of the first-run experience, which has never been measured |
| Wed 13 | R1.1 outcome contract columns and R1.2 criterion-linked verification | agent, about 2 hours | Both are well specified in the long-range WBS, so both run at the fast rate |
| Thu 14 | R1.3 ceremony opening half wired, R1.5 prose fence retirement | agent, about 2 hours | Same |
| Thu 14 | Tester feedback folded, defects filed with reproductions | agent, bounded by what the testers actually hit | Depends on the wall-clock item above |
| Fri 15 | R1.6 surface consolidation, R1 closing checklist, battery green | agent, about 90 min | |
| Fri 15 | **v3.3.0 cut, founder gate** | **wall** | A release is a founder decision. It waits for him, not for the code |
| Sat 16 to Sun 17 | Soak. Nobody works. The testers keep using it | **wall** | The only way to find what a weekend of real use finds |
| Mon 18 | Weekly review, sixty minutes, exactly one process change, sprint turns | **wall** | Fixed by the cadence |

**The honest week-range statement:** every piece of code committed above is
about six hours of agent clock. The week is seven days long because of the
four wall-clock rows, not because of the code. If the founder wants the week
to go faster, the lever is the tester schedule and the gate, not the build.

**Week overflow, chosen in advance so it is not chosen while tired:** R2.1
toolkit inventory, the memory architecture design document, the connector
model design document, the booklet refresh. Any Thursday that finishes early
starts the first of these rather than idling.

---

## 5. Long range: 12 August to 30 September

The tranches are unchanged. The windows are re-cut under the two-clock model,
which moves every date earlier and, more usefully, says which constraint is
actually binding in each one.

| Tranche | Old window | New window | Agent clock | What actually binds it |
|---|---|---|---|---|
| R1 "PROVE" v3.3.0 | 13 to 16 Aug | **13 to 15 Aug** | ~6 h | The founder gate on Friday and the tester feedback loop |
| R2 "TOOLKIT MVP" v3.4.0 | 17 to 26 Aug | **18 to 22 Aug** | ~10 h | Trust decisions on third-party tools, which are founder calls, one batch |
| R3 "TRUST AND PILOT" v3.5.0 | 27 Aug to 5 Sep | **25 Aug to 1 Sep** | ~8 h | The pilot itself. A pilot week is a week. Nothing compresses it |
| R4 "EVIDENCE RERANK" | 6 Sep onward | **2 Sep onward** | continuous | Evidence arriving from real use |

Two structural changes to how the roadmap is run, both consequences of the
model rather than opinions:

1. **Design documents move ahead of build work inside every tranche.** The
   memory architecture, the toolkit broker and the connector model are named
   in the horizon and defined nowhere. They are agent-clock work, so they are
   cheap now and expensive later once code assumes an undefined shape. R1
   carries all three even though they belong to R2 and R3, because the cost
   of writing them early is roughly two hours and the cost of writing them
   late is a refactor.
2. **Every tranche carries its own overflow queue**, chosen at tranche start.
   A tranche that finishes its committed work with days left pulls from its
   own overflow, not from whatever is nearest.

**What could make this wrong.** The new windows assume the tester loop starts
Tuesday and that the founder is available for one gate per week. If either
slips, everything downstream slips by the same amount, because the binding
constraint is wall clock and wall clock does not catch up. This is stated as
the flip condition rather than hidden as a risk.

**Confidence:** medium on agent-clock figures, because they now rest on four
measured points rather than none, and n=4 is thin. Low on wall-clock figures,
because no tester has ever run this cold and the first-run duration has never
been measured. That single unmeasured number is the largest uncertainty in
this plan, and tonight's tester pack exists to make it measurable this week.

---

## 6. What tonight changes about the process itself

Three things, each with the file that enforces it, per the standing rule that
a limit which cannot name its enforcement is written down as unenforced.

| Change | Enforced by | Proof it fires |
|---|---|---|
| Every forecast records its basis and gets an actual recorded against it | `tools/bm_forecast.py check` | An open forecast with no actual makes the check exit 1 and names it |
| A plan cannot leave the machine idle | `tools/bm_idle.py check` | An empty or shallow queue makes the check exit 1 and prints the depth |
| Both run inside the gate rather than when somebody remembers | `tools/test_all.py` SUITES | The gate's own inventory check fails when a suite file exists and is not registered |

Stated plainly and without softening: the two-clock model in section 2 is
prose and enforces nothing by itself. What the tools enforce is that the
numbers get recorded and compared, which is the thing whose absence let a 4x
bias survive four separate estimates in one night.
