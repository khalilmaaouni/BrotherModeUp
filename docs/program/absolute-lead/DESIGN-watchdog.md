# DESIGN: the drift watchdog, with a cadence the audited party cannot suppress

Status: DRAFT for the loop after the v2.1.0 tag. Written 2026-08-06 from a
design panel (three independent philosophies, three judging lenses, one
adversary) plus the founder's decisions of the same day. No em or en dashes.

## GOAL

The founder must be able to leave the machine and come back to a short ordered
list of every place his AI colleague drifted from the plan or claimed something
it had not proved. He reads that list on his own clock. Nothing waits for him,
nothing is lost because he was asleep, and nothing stops while he is away.

WHAT IT IS NOT FOR. It is not a test runner, not a code reviewer, and not a
second opinion on the work. It audits the ACCOUNT of the work: did what was
claimed happen, was it checked, was it in the plan, and was it declared. The
first real run of this idea, on 2026-08-06, caught two genuine lapses by the
orchestrator (recorded as M17) and correctly rejected one of its own five
findings as not real. That is the shape of the job.

North star objective: number 4, nothing dropped silently, including by the
orchestrator itself.

## THE FINDING THAT DECIDED THE ARCHITECTURE

The panel scored 1 to 1 to 1: work-shaped cadence, tier-proportional cadence and
risk-adaptive cadence each won exactly one judging lens. No philosophy
dominated, so the design is a composite. What broke the tie was the adversary,
which found one defect from two sides:

**An auditor whose schedule the audited party controls is not an auditor.**

Every natural work signal (a unit closing, a fence closing, a claim row, a
commit) is written BY the orchestrator being audited. A cadence derived from
those signals is therefore quietest exactly when behaviour is worst. Concretely,
using M17, a real recorded case: an orchestrator that writes outside a fence
produces no fence close, so no work event, so no check, so nothing notices that
it wrote outside a fence. No malice is required. Batching unit closes to the end
of a run buys silence across the whole middle of it.

The second face of the same defect: a ten hour unattended controller run is ONE
tool call inside ONE model turn, so a cadence that ticks per turn fires ZERO
times across that entire run, which is precisely when nobody is watching.

Therefore the cadence needs at least one trigger that nothing the orchestrator
writes can suppress, and one trigger that fires from inside a long-running
process.

## ARCHITECTURE

### The cadence, first match wins, in this order

Shaped like `briefing_due` in `tools/bm_lead.py`, evaluated at a boundary, never
by a timer, because BrotherMode runs nothing in the background.

1. **FLOOR, non-suppressible.** The Stop hook has fired K times since the last
   drift row, counted from HOOK FIRINGS rather than from any store row the
   orchestrator writes. No amount of non-compliance can hold it off. This rule
   exists solely to defeat the suppression attack and it is why the design works
   at all. Proposed constant `DRIFT_TURN_FLOOR`.
2. **IN-RUN, defeats the long-turn blind spot.** The controller calls the same
   due-check from inside its own unit loop: a live process already writing rows,
   so this adds no daemon and no timer, and a ten hour run becomes audited from
   the inside rather than not at all.
3. **WORK-SHAPED, the natural sync with task length.** N units of work have
   closed since the last drift row. This is what makes a one line edit cost one
   cheap check while a long run costs many, with no hand-tuned threshold. It is
   a good trigger, and per the finding above it is never trusted alone.
4. **RISK-ADAPTIVE.** After a confirmed finding the thresholds for rules 1 and 3
   tighten; while the run stays clean they relax back toward their defaults,
   bounded in both directions. Audit harder right after trouble.
5. **TIER-PROPORTIONAL DEPTH.** The declared effort tier (T1, T2, T3 in
   `references/delegation.md`) sets the DEPTH and budget of a check rather than
   its frequency. T1 gets the mechanical checks only; T3 earns the full set.
   Separately, a task that overruns its own declared tier is itself a finding.

### Scope: deterministic checks decide, a model only fills the gap

The deterministic checks run first and the record names which one answered. A
model judgement is consulted only where no command can decide the question, and
never as a substitute for one that could.

DECIDED BY COMMAND, no model: does every commit map to a planned item; does
every claim of done, fixed, works, green or passed carry a command in the same
message; is every dispatch tier-declared; was every fence written before its
agent; did any commit touch a file no fence names; is any quoted number stated
as measured now rather than copied forward; did any task overrun its declared
tier.

NEEDS A MODEL, cheapest tier only: does the stated reason for a decision match
what was actually done. That is the one question no command answers, and it runs
only at the depths rules 2 and 5 permit.

### Where state lives

Store rows, append only, one row per finding, never a second source of truth.
Each carries what was checked, the drift, its evidence (a command, a commit, a
file line), a severity, and two timestamps, found and answered. A row with no
answered timestamp is OPEN. Proposed tables `drift_findings` and `drift_ticks`.

## THE FIVE ANSWERS

**ROLE.** Audit the account of the work, not the work. Cheap, read-only, always
on, never in the way.

**SCOPE.** Seven checks decided by command plus one decided by a model, with
depth set by the declared tier. Scope scales with task size because the
work-shaped trigger fires more often on bigger tasks, not because anybody tuned
a number.

**CHECK TIMING.** The five-rule ladder above, first match wins. The floor rule
is the one that cannot be gamed; every other rule is optimisation on top of it.

**REPORT NATURE.** One finding is a row plus a single line naming the drift and
its evidence. A batch is ordered by severity and capped the way the alert ladder
is capped (`RUNGS` and `RUNG_DELIVERY` in `tools/bm_visual.py`), and beyond the
cap it states the remaining count rather than dropping the tail silently.

**NEXT ACTION.** Founder present: the orchestrator answers each OPEN finding by
name at the next loop close, one of three ways, recorded on the row: FIXED with
the commit, ACCEPTED AS A DECISION with a flip condition, or NOT A REAL FINDING
with the reason. Founder away: nothing waits. Findings accumulate and the whole
OPEN set plays back on his first turn back, ordered by severity, once.

## THE FIVE ADVERSARY DEFECTS, AND WHAT CLOSES EACH

Every one was found against the leading design before anything was built. The
four marked VERIFIED were re-checked against the source by the orchestrator
rather than taken from the agent that reported them.

| Defect | Closed by |
|---|---|
| VERIFIED: `tools/test_bm.py:1153` bans `import subprocess` in non-test files under `tools/`, allowing it only in `bm_autosave.py` and `bm_controller.py`, with the comment that it "remains banned everywhere else". `bm_lead.py` is not exempt, so the watchdog cannot shell out to git | Source tree facts from `os.stat` plus `hashlib`, both standard library, never from git |
| A finding survives a compaction but the OBLIGATION to answer it does not, because it reaches the orchestrator only as hook output that PreCompact discards | `tools/bm_sessionstart.sh` prints the open finding ids, in the same shape as the nags it already prints |
| VERIFIED: `Store.active_minutes_since` (`tools/bm_store.py:15617`) runs `SELECT timestamp FROM attribution WHERE project_id=?` with no time bound in SQL and filters by date in Python afterwards, so it reads every attribution row for the project on every call, inside a 30 second hook budget already shared by four programs | Bound the query by time in SQL, and add a minimum interval so ticks cannot fire on every turn |
| VERIFIED: the store takes `busy_timeout_ms=5000` (`tools/bm_store.py:6130`), so a watchdog write can make a controller write refuse `db-busy`, and can eat the shared hook budget so the founder's alert rendering is killed. The observer degrades the observation | The tick is READ ONLY; its row write defers to the next uncontended tick, with a short busy timeout and exit 0 on contention |
| The cadence can be suppressed by the party being audited | Rule 1, the non-suppressible turn floor, plus rule 2 inside the controller loop |

VERIFIED separately: the new command must be named `drift`, not `watchdog`,
because `cmd_watchdog` already exists at `tools/bm_lead.py:1963` and the Stop
hook in `hooks/hooks.json` already calls `bm_lead.py watchdog --tick`.

## PLAN

1. `tools/bm_store.py`: add `drift_findings` and `drift_ticks` at the next
   schema version, plus record and query methods including the open versus
   answered query. DONE-CHECK: `python3 tools/test_bm_store.py` exits 0.
2. `tools/bm_lead.py`: add `drift_due` in the shape of `briefing_due`, and a
   `drift` subcommand. DONE-CHECK: `python3 tools/test_bm_lead.py` exits 0.
3. `tools/bm_controller.py`: call the due-check from the unit loop so a long run
   is audited from inside. DONE-CHECK: `python3 tools/test_bm_controller.py`
   exits 0.
4. `tools/bm_visual.py`: two new alert kinds for an open finding and its
   playback, each mapped to a rung. DONE-CHECK: `python3 tools/test_bm_visual.py`
   exits 0.
5. `tools/bm_sessionstart.sh`: print open finding ids so the answer obligation
   survives a compaction. DONE-CHECK: `python3 tools/test_bm_consent.py` exits 0
   and nothing writes before consent.
6. Wire it on by default after the consent gate, with a capability register row
   stating honestly what is verified and what is not. DONE-CHECK: `python3
   tools/test_bm_docs.py` exits 0.
7. Full gate. DONE-CHECK: `python3 tools/test_all.py` exits 0 AND `git status
   --porcelain` is empty afterwards.

## WHAT THIS DESIGN GIVES UP

- The floor rule means a quiet stretch still costs an occasional cheap check.
  That is the price of a trigger nobody can suppress, and it is worth paying.
- Pure work-shaped cadence would be cheaper on a well behaved run. Rejected
  because it is quietest exactly when behaviour is worst.
- Pure tier-proportional cadence would be simpler to explain. Kept only for
  DEPTH, because a declared tier is itself written by the audited party.
- A single very long turn outside the controller is still less well covered than
  a normal one. Rule 2 closes this for controller runs, which is the case that
  matters. The documentation must say so rather than imply full coverage.

## UNVERIFIED IN THIS DESIGN

Stated plainly, because a design that hides its assumptions is a plan to be
surprised. That a size and mtime hash is sufficient in practice for the tree
facts; that the controller unit loop has a clean call site for the tick; and
that the two new alert kinds slot into `alerts_now` without disturbing its
deduplication. All three are implementation risks for the agent that builds
step 1 to settle, not findings.
