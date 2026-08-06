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
step 1 to settle, not findings. AMENDED BELOW: the size and mtime assumption
was refuted the same night and is superseded by the content-hash rule in
amendment section B2.

---

# AMENDMENT 1, 2026-08-06 NIGHT

Written after the design's first live exercise (DRIFT-AUDIT-1, wave 17) and a
nineteen-finding refutation of the amendment's own draft by three independent
refuters (suppression, misfire, cost) plus two auditors, sixteen findings
reproduced against source with file and line evidence. The load-bearing
decision stands: one trigger nothing the orchestrator writes can suppress,
plus one that fires from inside the controller loop. Everything below closes
holes around that spine. Where this amendment contradicts the base text above,
the amendment wins.

## A. TWO LAYERS, AND THE DISPATCH OBLIGATION THAT CANNOT BE DROPPED

The base design asks the in-process watchdog commit-shaped questions, but
bm_lead.py may never import subprocess (tools/test_bm.py bans it outside
bm_autosave.py and bm_controller.py), so it can never read a commit. The first
real audit worked only because it was a dispatched agent. Therefore:

- LAYER 1, the tick: in-process in bm_lead.py, no subprocess ever. Owns the
  five-rule cadence, every store-row check (tiers declared, fence before
  agent, claim receipt linkage, registry staleness), the tree fingerprint,
  and the EMISSION of layer 2 briefs.
- LAYER 2, the audit agent: read-only, cheapest tier that can read a diff,
  answers the commit-shaped questions and the one model question.

The refuted hole: layer 1 cannot dispatch an agent, so the ORCHESTRATOR must,
which is three suppression points (never dispatch, never relay, filter the
relay). Closure: on brief emission layer 1 writes an OPEN obligation row in
the same open-versus-answered shape as a finding. The brief names a drop-box
file path; the layer 2 agent writes its findings there; layer 1 ingests the
file directly at the next tick with os.stat plus read, no subprocess and no
orchestrator relay, validating against the schema before any row lands. A
brief with no ingested drop-box after K ticks or one founder boundary becomes
an automatic high-severity finding named audit-not-dispatched, printed by
bm_sessionstart.sh beside the open findings.

## B. AN AUDIT ON A MOVING TREE, WITHOUT THE STALL THE FIX WOULD CAUSE

B1. DRIFT-AUDIT-1 watched a file change underneath it and could only warn in
prose (the M12 class). But whole-tick voiding, the obvious fix, was refuted:
a busy run's tree moves by construction (the controller writes between units;
bm_view render writes in the same Stop chain), so voiding every observation
on any mismatch stalls every substantive audit forever, and the stall can be
provoked deliberately. Closure: void PER OBSERVATION. Each check names the
paths it read; only observations whose named paths moved are voided, the rest
land. Small files are snapshotted into memory at tick open so most checks
cannot race at all. Consecutive whole-tick voids are capped at a small N,
after which the tick records a high-severity finding named audit-starved and
the store-row-only checks, which need no tree fingerprint, run
unconditionally. A void or starved finding NEVER advances or resets the floor
counter.

B2. The size-plus-mtime fingerprint was refuted in both directions: a
same-size edit can pass unseen, and a byte-identical re-render trips a false
move that feeds the stall above. Closure: content hash for every file under a
size ceiling (store rows, registry, evidence files are all small), with
size-plus-mtime only as the cheap prefilter that decides WHEN to re-hash,
never as the verdict.

B3. The fingerprinted slice is BOUNDED and named: git-tracked source files
only, explicitly excluding .git/, .brothermode/ and every runtime data
directory. The repository holds 373 untracked files including the live store
and its wal, which a sibling hook program writes at the same boundary; an
unbounded slice would void every tick by observing its own machinery.

## C. RECEIPTS: CLAIMS BECOME AUDITABLE, AND SCOPE IS PART OF THE CHECK

DRIFT-AUDIT-1 could not tell a fresh test number from a copied one and could
not check push claims at all, because the account holds prose. Closure: one
new append-only table, gate_receipts, written by a thin wrapper AROUND a
suite or verifier invocation after its process exits, reading its exit code
and last output line. Never from inside test code: a receipt write is a store
write, deliberately invisible to the tracked-file cleanliness guard from
447b73c, and that is stated here so nobody reads the silence as a hole later.
Each receipt: type, command string, exit code, last line verbatim, wall
seconds, tree fingerprint, timestamp.

Receipts are TYPED: gate, full-suite, sub-suite, verifier, push. The refuted
hole: an untyped receipt lets a claim of repository-wide green cite a genuine
receipt for one sub-suite, passive drift with no forgery. Closure: layer 1
maps claim kinds to required receipt types; green, passed or done on the
repository requires a gate or full-suite receipt; a sub-suite receipt
satisfies only a claim scoped to that suite; the mismatch is a finding named
receipt-underscoped. The claim's OWN tree fingerprint is recorded at claim
time, so edit-then-revert after claiming is detectable. Two claims citing one
receipt across two commits is the copied-forward finding. A push claim
requires a push receipt with the three hashes (HEAD, upstream, ls-remote)
equal at verification time. Honesty bound, unchanged: a forged receipt is
active fraud and out of scope; the floor rule still fires on silence; the
capability register row says exactly this.

## D. DETECTION WITHOUT COLLATERAL DAMAGE, AND WITHOUT AN ESCAPE HATCH

The F3 incident is the constraint: a hook misread a worker's plan section as
a completion claim and the worker burned its whole output answering it. The
draft fix (discard matches under plan-like headings) was refuted twice: the
orchestrator authors the headings, so the allowlist is an escape hatch; and
commit messages have no headings at all, so there is no structure to read.

Closure, three rules:

1. AUDIENCE. The watchdog audits the orchestrator's account. Findings go to
   rows and the founder surface. No hook challenges a subagent mid-turn, and
   hook text attached to any turn is bounded to one line naming row ids.
2. DETECTION. For commit messages the deterministic check is receipt linkage:
   a message claiming done, fixed, works, green or passed must carry a
   receipt reference, and keyword hits are counted only outside quoted
   output lines. For structured documents, matches inside plan-marked
   sections are never hook-challenged and never charged to any agent, but
   they are NOT discarded: they pass to layer 2 as low-confidence candidates,
   so a claim hiding under a Plan heading surfaces in audit rather than
   vanishing.
3. ANSWERING. The obligation to answer belongs to the orchestrator, due at
   the EARLIER of the next loop close or K floor firings after the finding
   opened, K counted from the same non-suppressible Stop counter as rule 1,
   because a loop close is itself an orchestrator-written event. A finding
   open past that age escalates: the tick itself writes an escalation
   finding, so silence compounds instead of hiding. An OPEN finding replays
   at EVERY founder boundary until answered, not once.

## E. THE REGISTRY STALENESS CHECK, CALIBRATED AGAINST THE REAL REGISTRY

The idea survived review; the draft grammar did not. Refuted: QUEUED fences
(wave 20 FENCE D, wave 21 FENCE F) would be flagged though dormant by design,
and marking them LANDED would silently erase undone work, inverting the north
star objective this watchdog serves; markers live on continuation lines of a
fence BLOCK, not on the opening line; and an empty declared-file list makes
the landed-files branch vacuously true, which would flag ten provisional
rows on the first tick and bury every real finding.

Closure: the unit of inspection is the fence BLOCK, from its opening line to
the next entry or heading. QUEUED is a first-class state: exempt from both
staleness branches until dispatch, with TTL counted from the dispatched
timestamp; but a QUEUED block whose named dependency has itself landed
becomes a DIFFERENT finding, queued-and-ready-never-dispatched, which
preserves the obligation instead of erasing it. The landed-files branch
requires a non-empty file list and tests whether the fence's OWN unit landed,
not whether its files appear in anybody's landed work. PROVISIONAL records
with no files are excluded from this check and reported once, low severity,
as record-never-scoped. The parser ships calibrated against the real
STATE.md as a fixture: zero findings on the blocks known closed, one finding
on each wave 17 fence known stale the night this was written.

## F. THE FLOOR LIVES OUTSIDE THE STORE IT AUDITS

Refuted twice from two sides: the base design defers the tick's row write on
store contention, and the draft required every tick to write a row, a direct
contradiction; worse, the floor counter itself lived in the same store, so
sustained contention at Stop boundaries, which the orchestrator or any
process it starts can cause with an open write transaction against a 5000ms
busy timeout inside a shared 30 second hook budget, would freeze the floor
silently, defeating the one property the design says makes it work.

Closure: a SIDECAR under .brothermode/, an O_APPEND one-line-per-firing file
(or its own tiny database), written FIRST on every Stop firing,
unconditionally, in microseconds, before any main-store work is attempted.
The floor counts sidecar lines, which no store lock can touch. The
drift_ticks row in the main store is then attempted with its OWN short busy
timeout, tens of milliseconds, so it can never become the contention it
records; only drift_findings content defers to the next uncontended tick. A
gap between the sidecar count and the drift_ticks count IS the starvation
pattern, reported as a finding at the next uncontended tick. The tick also
opens its sidecar line before any check runs; a later tick finding an
unclosed line converts it to skip reason crashed, and two consecutive
crashes are a finding, so the house fail-open posture can no longer hide a
provoked crash.

## G. THE RISK DIAL IS NOT TURNED BY THE PARTY IT MEASURES

Refuted: rule 4 tightened on confirmed findings and relaxed while the run
stayed clean, but the only confirmation path is the orchestrator answering
its own findings, so answering everything as not-a-real-finding relaxes the
audit. Closure: thresholds tighten on RECORDED findings, the open rows, not
confirmed ones. They relax only on ticks that ran to completion and found
nothing, never on answered-away findings, and never past their defaults
before the founder has seen the playback. A streak of not-a-real-finding
answers above a small ratio is itself a deterministic layer 1 finding named
self-acquittal-pattern.

## H. COST BOUNDS, STATED AS NUMBERS

The Stop hook budget is one shared 30 seconds across four chained programs.
The tick therefore carries an explicit wall ceiling, sub-200 milliseconds
typical, short-circuits before any stat or SQL work when no cadence rule is
due, and aborts recording skip reason budget when the ceiling is hit. The
known unbounded query, Store.active_minutes_since at tools/bm_store.py:15617,
which reads every attribution row and filters in Python, gains its SQL time
bound as a PRECONDITION of plan step 1, restated here because cadence rule 2
multiplies how often that path runs and the base design had already flagged
it without assigning the fix to a step.

## AMENDED PLAN STEPS

Step 1 grows: gate_receipts (typed) beside drift_findings and drift_ticks,
the sidecar writer, and the SQL time bound on active_minutes_since. Step 2
grows: drift_due, the brief emitter with obligation rows and drop-box
ingestion, and the registry staleness parser calibrated against the real
STATE.md fixture. Step 5 grows: the sessionstart print includes voided
ticks, skip and crash streaks, sidecar-versus-ticks gaps, and unanswered
finding escalations beside the open finding ids. New step 8: the claim
detector, with fixture tests proving a plan section, a future-tense sentence
and a quoted specification do NOT match while a past-tense claim does, AND
an explicit exemption list naming the fixture file itself with its reason
written beside it, pinned by a test so removing the file without the
exemption fails, which is the M11 lesson applied in advance instead of
rediscovered mid-collision. Step 9 is the former step 7, the full gate on a
quiet tree.
