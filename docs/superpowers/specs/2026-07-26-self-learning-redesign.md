# The self-learning mechanism: what the evidence says, and the redesign

Status: DESIGN, awaiting founder approval. Nothing here is implemented.
Date: 2026-07-26. Method: four parallel lenses (two reading published research and
opening the actual papers, two auditing our own code and real telemetry data).

## 1. What the published research actually measures

Every claim below was taken from a page an agent opened, with the measured result.

- Self-correction WITHOUT an external signal makes reasoning WORSE, not better.
  Huang et al., ICLR 2024 (arxiv.org/abs/2310.01798): GSM8K 75.9 to 75.1 to 74.7
  percent across two self-correction rounds; CommonSenseQA collapsed 75.8 to 38.1.
  Models flip right answers to wrong more often than they fix real errors.
- The same models correct an error presented as someone else's, and fail on the
  identical error framed as their own prior output (the self-correction illusion).
- Self-correction DOES work when trained against a verifiable, non-model reward
  (DeepMind SCoRe, arxiv.org/abs/2409.12917: +15.6 percent MATH). The working
  ingredient was ground truth, not self-judgment. We have no such reward.
- Constitutional AI works because the constitution is HUMAN-WRITTEN and IMMUTABLE
  to the acting model, and the judge is a SEPARATE model (arxiv.org/abs/2212.08073).
- Automated prompt optimizers (OPRO, DSPy) accept a change only if it beats a
  HELD-OUT validation set the change was not written against.
- Self-consuming loops degrade: models trained on their own output drift toward a
  narrow, artifact-biased distribution (arxiv.org/abs/2307.01850). A loop that
  rewrites its own laws from its own transcripts is structurally the same shape.
- Tolerated small rule-bending GENERALIZES to the model editing its own reward
  (Anthropic, arxiv.org/abs/2406.10162). A lenient self-grade is not a small thing
  in a system that edits its own rules.
- LLM judges show measurable self-preference bias (arxiv.org/abs/2410.21819).
  Deterministic checks should own every criterion a command can decide.
- Incremental deltas beat wholesale rewrites: a monolithic rewrite baseline
  collapsed from 66.7 to 57.1 percent accuracy in ONE step (ACE,
  arxiv.org/abs/2510.04618). Our vault practice of summarizing files down is that
  shape.

## 2. What our loop actually does today (audited against real data)

- A scorecard line is a hardcoded string: "collisions=0, baton drops=0" is printed
  verbatim every run with no variables behind it. It can never move.
- Roughly 5 of the 9 rubric metrics have no mechanical number at all; they say
  "judged at weekly review".
- The weekly review has run ONCE, ever (reviews.jsonl: 1 row). Against that, 13
  law amendments have landed. The rule that says an amendment must be reverted if
  it did not move its named signal has therefore fired ZERO times.
- Ratings: 14 rows, three of them fractional (3.7, 3.8, 2.5). A human answering
  "1 to 5" cannot produce 3.7. The graded agent can call the rating command itself.
- The prediction ledger scores 1 prediction, and that one is self-labeled as an
  agreement case, which by our own rule carries no signal. The DIVERGED concept
  exists in prose and in no code path.
- Mechanical correction capture: 4 rows across 25 sessions, behind a 13-phrase
  English regex, while most real laws were hand-written into the founder model
  directly. The pipeline described in the law is not the pipeline in use.
- The law file grew 44.6 percent in five days. Its own size cap has no enforcer.
- Statistically: at 24 sessions per week with a spend variance this high, detecting
  a 20 percent improvement needs roughly 1,121 sessions per arm, about 40 weeks.
  Every "trending down over 3 reviews" metric is currently unfalsifiable noise.
- The ledger has 19 fields and not one of them is an outcome. Everything measured
  is bookkeeping about the work, not the work.

Blunt summary: we built a measurement system that mostly measures whether it was
filled in.

## 3. The redesign, in one sentence

Delete the theatre, keep three signals that cannot be faked by the party being
graded, and make law changes provable rather than self-asserted.

### 3.1 Three real signals (replacing nine partly-fictional ones)

1. REWORK: the founder sent a deliverable back, or the next session redoes the
   same artifact. Mechanically derivable from the next session's transcript and
   git history. This is the closest thing to ground truth we have.
2. ESCAPED DEFECT: a later session finds a defect in work a previous session
   declared green. Also mechanically derivable, and it is exactly what happened
   nine times today.
3. FELT OUTCOME, with provenance: the founder's own rating, stored with their
   verbatim reply and the session id it came from. Integers only. Rows without
   provenance are reported separately as unattributed, never averaged in.

Everything else becomes descriptive telemetry (spend, duration, agents), reported
but never scored, and explicitly labeled NOT DECIDABLE at this volume where that
is statistically true. Honest labeling is the point: a number nobody can act on is
worse than no number, because it buys unearned confidence.

### 3.2 Law changes become gated, following Constitutional AI and DSPy

- The constitution is founder-owned. A session may PROPOSE an amendment; it may
  not land one. Landing requires the founder's explicit approval, which is already
  how the good amendments actually happened.
- A mechanical pre-commit check in the skill repo refuses any law commit that does
  not: name the signal it intends to move, cite a review entry newer than the
  previous law commit, name the text it displaces (or justify adding), and keep
  the file under its stated size cap. The cap gets an enforcer instead of a wish.
- Held-out validation, DSPy style: an amendment is checked against a small suite of
  recorded past situations it was NOT written against, before it lands.

### 3.3 Judge economy, following the bias evidence

- A deterministic check owns every criterion a command can decide. An LLM judge is
  spent only where no command can decide it.
- Refuters run in a fresh context AND on claims selected by a script, not by the
  judge's choice, and only on claims with a machine-checkable counterpart.
- The graded party never writes its own outcome rows.

### 3.4 Fresh data, against the self-consuming failure mode

The loop must train on signals from OUTSIDE itself: founder corrections, rework,
escaped defects, and real-world outcomes. Self-audits are for finding bugs, not for
grading the system. Today the ratio is inverted: 4 external correction rows against
13 self-sourced amendments.

## 4. What this costs

Small. Deleting metrics is free. The three signals are derivable from data already
captured. The pre-commit check is roughly fifty lines. The expensive part is
cultural: fewer numbers, and the remaining ones can say "we do not know".

## 5. The knowledge layer (founder requests, 2026-07-26)

Three requests arrived mid-design: fold the Superpowers method skills into the core
flow, turn accumulated lessons into a durable artefact, and grow real expertise in
the external tools we use. They are not three features. They are three registers of
ONE thing, and the research above already tells us its shape: a retrievable,
verified knowledge base that agents READ BEFORE acting and WRITE ONLY AFTER
verifying, grown by append rather than rewrite.

Why one thing and not three: Voyager's result (3.3x more items, milestones up to
15.3x faster, transfers to a new world) came from a growing library of VERIFIED,
RETRIEVABLE procedures. Reflexion's gain (HumanEval 80.1 to 91.0) came from a
CAPPED buffer of verbal lessons reused as context. ACE's gain came from
INCREMENTAL DELTAS, because the rewrite baseline collapsed 66.7 to 57.1 in a single
step. Generative Agents showed retrieval must be SCORED (recency, importance,
relevance), because a flat log fails to surface what matters. Same mechanics, three
kinds of content.

### 5.1 Register one: LESSONS (the wisdom artefact)

One file, `docs/knowledge/LESSONS.md`, organized by DEFECT CLASS rather than by
incident, because the recurring finding of this whole build is that fixing the
instance leaves the class alive. Each entry:

    ## <class name>
    What it looks like: one line
    Why it happens: one line (the mechanism, not the story)
    Mechanical stop: the test, grep, or gate that now catches it
    Appearances: dated one-liners, newest first, capped at 5
    Status: OPEN (no mechanical stop yet) or CLOSED (stop exists and is calibrated)

The cap is the Reflexion lesson: an uncapped buffer stops being read. A sixth
appearance replaces the oldest and increments a counter, so frequency survives
without the file growing forever. Today's build alone seeds this with real classes:
success reported on an unchecked write, fix the instance and leave the class, a
verifier that was itself unverified, not-supplied treated as empty, path grammar
that can be escaped, and a claim of health nobody checked.

### 5.2 Register two: TOOLBOX (tool expertise that compounds)

One file, `docs/knowledge/TOOLBOX.md`, one entry per external tool actually used,
written only after a use that was verified:

    ## <tool name>
    What it is for: one line
    Verified invocation: the exact command or call shape that worked, dated
    Gotchas: each one costing a real failure, dated
    Do not use it for: where it looked right and was not
    Last verified: date, and against which version

Rules that keep it honest and small: an entry is created only after a VERIFIED use
(not after reading docs about it), every recipe carries the date and version it was
verified against, and a recipe older than 90 days is marked STALE rather than
trusted, because version-sensitive facts are the single most common source of
invented flags. Before using a tool a session checks this file first; after a
verified use, it appends the delta. This is Voyager's skill library with the
staleness discipline that the research on version drift demands.

### 5.3 Register three: METHOD (the Superpowers spine, wired into the flow)

The three method skills the founder named map cleanly onto the phase flow already
in use, and the value is in their MECHANICS, not their names. An extraction pass is
running to capture those mechanics faithfully rather than from memory; the design
here fixes only the wiring:

- BRAINSTORM before any creative or structural work, with its hard gate: no
  implementation until a design exists and the founder has approved it. This is the
  same gate as the decision-brief rule already in the law, so they merge rather
  than stack.
- DEEP RESEARCH before any decision that turns on facts that can change (versions,
  prices, platform behavior, what is state of the art), with sources opened and
  cited, not recalled.
- CODE REVIEW before any merge, dispatched with the reviewer receiving crafted
  context and a git range rather than the session's history, so the reviewer judges
  the work product and not the author's reasoning.

Parallel-agent dispatch keeps its current shape (one wave, disjoint fences, a
runnable done-check per brief), with one addition proven necessary today: every
dispatched brief carries a mechanical FRESHNESS ASSERTION the agent must run and
quote back, because a fleet once spent a full round on a stale copy and reported
confident findings about code three commits old.

Ordering in a build, stated once so it stops being improvised: brainstorm, then
research what the design turns on, then plan, then implement behind fences, then
deterministic gates, then adversarial review, then code review, then merge, then
write back to the three registers. The registers are read at the START of the next
build, which is the only thing that makes any of it learning rather than filing.

### 5.4 What keeps this from becoming its own theatre

Every register has a mechanical check, or it does not ship:
- LESSONS: a class marked CLOSED must name a test, grep, or gate, and that
  reference must resolve. A CLOSED class whose stop does not exist fails the check.
- TOOLBOX: entries carry a verification date; the check reports how many are stale.
- METHOD: the gates are already mechanical (a design file exists, a review ran, the
  suite is green), so the check is that the artefact exists, not that someone says
  it happened.

## 6. The honest counter-argument

At solo-founder volume, no statistical learning loop can work. The correct posture
may be to stop calling this learning at all and call it what it is: a memory system
plus a set of gates, where improvement comes from the founder's corrections and
from defects found by adversarial execution, not from a self-improving mechanism.
That reframing is not a defeat. It is the difference between a system that improves
and a system that performs improvement.
