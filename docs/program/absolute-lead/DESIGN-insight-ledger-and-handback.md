Status: CURRENT. Fable design, 2026-08-05, founder-directed. Implementation
lands in L04 (founder mode and IC mode). Nothing here is built yet.

# The Insight Ledger, the Handback Option, and the Half-Hour Briefing

Founder directive, 2026-08-05, in his words: insights like the mutation
calibration one should appear at least every 30 minutes so the developer and
the founder understand the situation and the choices made; being included in
key decisions must be a rule, with the option to give development control back
to the developer available as a choice every time; and these must be recorded
as organized handover documentation for human business analysts and project
leads.

## What is actually missing today

BrotherMode already records what happened: work records, dispatches,
interruptions, founder steps, session logs. It records almost nothing about
WHY a choice was made, and it surfaces nothing on a clock. A founder who walks
away for two hours comes back to a diff and a green suite, which tells them the
machine was busy and not what it decided or what it nearly did instead.

Three separate gaps, deliberately not merged into one feature:

1. **No decision record with alternatives.** An ADR exists for architecture,
   but the thousand smaller judgements (which finding to fix first, which test
   to supersede, which rule to defer to the founder) leave no trace of the road
   not taken.
2. **No cadence.** Everything is pull. The founder must ask.
3. **No handback.** The system asks the founder to DECIDE things. It never
   offers to stop deciding and hand the work back.

## The shape: one ledger, three surfaces

One append-only table is the truth. Everything else renders it. This is the
same law that makes the store the truth and STATE.md a generated view, and it
is why the ledger is not "a document the agent writes".

    insights                (schema 16, additive)
      insight_id            immutable
      created_at
      kind                  DECISION | CALIBRATION | RISK | LEARNING | HANDBACK
      subject               what it is about (unit, finding, rule, file)
      claim                 one sentence, the thing now believed
      evidence              the command, probe, or file that settled it
      evidence_class        EXECUTED | MEASURED | READ | REASONED
      alternatives          what else was considered, and why not
      flip_condition        what would change this decision
      confidence            calibrated, with the basis
      control_offered       whether a handback was offered here
      control_taken         whether the founder took it
      work_record           links to the existing work identity
      session_id, actor

`evidence_class` is the field that makes the ledger honest rather than
decorative. REASONED is explicitly the weakest tier and is displayed as such,
because this project's own law L19 already says a verdict that names no
executed falsification is NO-DATA rather than a finding. An insight whose
evidence_class is REASONED may never be presented as a settled fact.

### Surface 1: the half-hour briefing

A rendered block, at most six lines, emitted every thirty minutes of active
work and at every phase boundary:

    Where we are      one sentence, outcome first
    What changed      since the last briefing, with the command that proved it
    What it cost      tokens, minutes, against the ceiling
    What I decided    the newest DECISION insight, with its alternative
    What I am unsure of the newest RISK, and what would settle it
    Your options      the handback line, always present

The cadence is the founder's thirty minutes, not a fixed cron: a briefing is
due when thirty minutes of ACTIVE work have passed, so an idle session does not
spam and a busy one cannot go quiet for two hours.

### Surface 2: the handback option, on every key decision

A rule, not a courtesy. Every founder-facing decision window gains one option,
always last, always present, with stable wording:

    Hand this back to me: I take this decision and the work under it, and
    BrotherMode records where it stopped and what it would have done.

Taking it does four things, all mechanical: the current fence is closed with an
evidence block, the work record is parked with its next intent written, a
HANDBACK insight records what the system WOULD have chosen and why, and a
developer brief is generated (the files, the reproduction, the open question).
Handing back is therefore never a loss of state, which is the only way an
option like this gets used rather than feared.

"Key decision" is defined mechanically, not by feel: any decision that (a)
touches a hard gate or a safety floor, (b) changes a rule the founder approved,
(c) supersedes or retires a test, (d) defers a finding rather than closing it,
or (e) chooses between designs whose flip condition is founder preference. The
first four are detectable from the store; the fifth is declared by the
orchestrator and is the one honest human-judgement entry, and the ledger says
so on that row.

### Surface 3: the handover pack for analysts and leads

`bm-project handover-pack` generates, from the ledger and the existing records,
a folder a business analyst or project lead can read without touching code:

    00-SITUATION.md      where the project stands, in plain language
    10-DECISIONS.md      every DECISION insight, newest first, with alternatives
                         and flip conditions, grouped by subject
    20-RISKS.md          open RISK insights with what would settle each
    30-CALIBRATIONS.md   every control that was deliberately broken to prove a
                         test catches it, with the mutation and the result
    40-LEARNINGS.md      what changed in how the work is done, and why
    50-TIMELINE.md       the briefings in order, so a reader can replay the run
    60-HANDBACKS.md      every point control was offered and what happened

Each page carries its evidence class per claim, so a reader can see at a glance
which statements were executed and which were merely reasoned. The pack is
generated, never hand-written, for the same reason CANVAS.md is.

## The one thing this design refuses

It refuses to let insights become a second source of truth. An insight cites
the store; it never replaces it. If the ledger and the store disagree, the
store wins and the disagreement is itself recorded as a RISK insight. Without
that rule, a well-written insight page becomes the thing everybody reads and
nobody checks, which is precisely the failure this project already recorded
when hand-maintained prose stood in for the registry.

## Why the mutation-calibration insight is the model for all of them

The example the founder singled out earns its place because it is falsifiable:
break the control on purpose in a scratch copy, count which tests go red, and
if none do, the test was decorative. That is a measurement, not an opinion, and
it is reproducible by anyone. Every CALIBRATION insight must carry the mutation
it applied and the count it observed. An insight that cannot state what would
have proved it wrong is not an insight; it is narration, and the ledger's own
schema makes that visible through evidence_class rather than through taste.

## Implementation order, inside L04

1. Schema 16, the `insights` table, additive, with its purge entry (the purge
   dict pins every table it removes, and a new table that skips that pin turns
   the suite red by design).
2. The write path: one service method, one refusal per malformed insight, no
   direct SQL anywhere else.
3. The briefing renderer plus the active-work clock.
4. The handback option wired into the decision-window helper, so it cannot be
   omitted by an author who forgets; a decision window rendered without it is a
   test failure.
5. `handover-pack` generation, with a docs-truth test asserting every page
   traces to rows.
6. Behavioral fixtures: a run that offers handback and is refused, one that is
   taken, one where the ledger contradicts the store.

## What this costs, honestly

A range, with its assumption: two to four working sessions for a first version
that ships the table, the briefing and the handback option, assuming L04's
founder-mode surface lands first, because the briefing renders through it.
The handover pack is a further one to two sessions and can ship separately.
Confidence: moderate. The estimate would move if the briefing clock turns out
to need real process supervision rather than a timestamp comparison, which is
the one part of this that has no precedent in the current toolchain.
