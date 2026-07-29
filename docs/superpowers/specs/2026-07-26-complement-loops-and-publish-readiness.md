# The complement loops, and what is missing before this can be published

**HISTORICAL DOCUMENT, dated 2026-07-26. Do not read it as current state.** It is a dated working record: the plan, the verdicts, the blockers and the numbers in it belong to that day and were not updated afterwards. Items it calls open may since have been closed. Superseded by `README.md` and `docs/KNOWN-LIMITS.md` for status, `docs/NOT-FINALIZED.md` for the defect register, `CHANGELOG.md` for what changed since, and `python3 tools/bm_project_facts.py` for version, release tag, hook events and suites.

Status: DESIGN, awaiting founder approval. Supersedes the framing (not the audit) in
2026-07-26-self-learning-redesign.md. Date 2026-07-26.

## 1. The founder's correction, and why it is right

I audited the learning loop, found most of it was theatre, and proposed retreating to
"memory plus gates" because improvement is statistically undecidable at solo volume.
The founder rejected the retreat and named a better target: the system should get to
know THEM better (habits, preferences, nature) and complement them properly.

That reframe resolves the exact problem the research raised, and it is worth stating
precisely because it changes what we build.

The published evidence says self-correction fails WITHOUT AN EXTERNAL SIGNAL: reasoning
accuracy fell from 75.9 to 74.7 percent over two self-correction rounds, and a
commonsense benchmark collapsed from 75.8 to 38.1 (Huang et al, ICLR 2024). It also
says self-correction WORKS when trained against a verifiable reward (SCoRe, +15.6
points on MATH). The missing ingredient in our loop was never the loop. It was the
absence of ground truth.

The founder IS the ground truth. Modeling them is supervised learning from a teacher,
not a system grading its own homework. And it is tractable at n=1 in a way that
session metrics are not: detecting a 20 percent spend improvement needs roughly 1,121
sessions per arm, but a single correction is a discrete labelled fact that can be
applied immediately and checked on the next task.

So the learning target moves. It is the founder model, not the scorecard. Every metric
either serves that target or gets deleted.

## 2. The four complement loops

Each loop names: the signal, where it comes from, what changes because of it, and how
we would know it is working. A loop without all four is decoration.

### Loop 1: CORRECTION (the highest-value signal, and the only true teacher)

Signal: the founder says something is wrong, or redirects the work.
Source: their messages, verbatim.
What changes: the correction is logged same day with its context, distilled into a law
that names the underlying REASON (so future sessions generalize the taste instead of
memorizing the rule), and pre-applied to the next relevant task.
How we know it works: the same correction is not needed twice. A repeat correction on
a settled point is a loop failure and is logged as one.
Cadence: immediate, never batched to a weekly review.
Mechanical part: the capture must not depend on a session choosing to write prose at
close time, which is where the current pipeline fails (4 captured rows against 13
laws that were hand-written directly).

### Loop 2: TASTE (revealed preference, not stated preference)

Signal: which option the founder picks when given real choices, and what they change
in delivered work.
Source: decision briefs (the pick), and edits to delivered artefacts (the diff between
what was delivered and what they kept).
What changes: work arrives PRE-SHAPED to known taste, so the founder spends their
attention on judgment rather than on repeating themselves.
How we know it works: the amount they have to change on arrival goes down. That is
observable per artefact and does not need a large sample.
Known trap, and it is the interesting one: stated preference and revealed preference
diverge. What someone asks for and what they keep are different data. When they
conflict, the kept version wins and the divergence is recorded.

### Loop 3: CALIBRATION (does the model actually predict them)

Signal: a prediction of the founder's choice, sealed BEFORE the recommendation is
formed, scored only when prediction and recommendation DIVERGED.
Why only divergent cases: an agreement case measures nothing except that I recommended
what I predicted. Scoring those rewards telling the founder what they want to hear,
which is exactly the failure mode a founder model is supposed to prevent.
What changes: a wrong prediction updates the model; a right one on a divergent call is
real evidence the model has content.
How we know it works: divergent-case hit rate, plus a challenge counter. A quarter
with zero challenges raised is a red flag on the duty to push back, not harmony.
Current state, honestly: one scored prediction, self-labelled as an agreement case, so
the current number means nothing.

### Loop 4: COMPLEMENT (the division of labour, and the genuinely new one)

Signal: what the founder wants to own versus what they want handled, and where their
attention is scarce or expensive.
Source: what they delegate without instruction, what they always take back, what they
ask to be shown versus what they ask to be decided.
What changes: the system stops asking about things they have shown they do not want to
decide, and stops deciding things they have shown they want to hold. It covers what
they are not interested in and defers where they are strong.
How we know it works: fewer questions asked that they did not need to answer, and
fewer decisions taken that they wanted to make. Both are countable from the transcript.
Why this is the hard one: it is the difference between an assistant and a colleague,
and it is the loop nobody usually builds, because it requires admitting the system
should sometimes stay out of the way.

## 3. What connects the loops (the part that is currently missing)

Today we have three artefacts and no wiring: the founder model, the lessons file, and
the tool registry. Nothing READS them at the start of work, so they are filing rather
than memory. That is the single most important gap in this whole delivery.

The wiring, stated as a contract:
- SESSION START reads, in this order: the founder model (taste and division of labour
  for THIS kind of work), the lessons file for the defect classes touching this area,
  and the tool registry for any tool about to be used. Reading is a query, never a
  tour: only what this task needs.
- DURING work, a correction is captured the moment it arrives, not at close.
- SESSION CLOSE writes back exactly three things and no more: any correction with its
  distilled law, any new lesson AT THE CLASS LEVEL (never an incident), and any tool
  recipe that was verified by use.
- The registers are capped and append-only in shape: a new entry merges with or
  displaces an existing one rather than accreting, because the measured failure of
  wholesale rewriting (accuracy collapsing from 66.7 to 57.1 in one step) and the
  measured failure of unbounded buffers are both real.

## 4. What is missing before this can be published, ranked by risk

1. THE ENGINE IS CONNECTED TO NOTHING. The V2 store is hardened and unused; the tools
   that actually run still use the old registries with every original defect. Until
   Phase 3 rewires them, publishing means shipping a beautiful component nobody's
   session touches.
2. THE RECOVERY SYSTEM IS STILL THE BROKEN ONE. Phase 2 is designed, not built. The
   autosave that a founder would reach for on their worst day can still publish an
   empty snapshot over a good one and can delete a tracked file on restore. This is
   the highest actual-harm gap.
3. CONTINUOUS INTEGRATION HAS NEVER RUN. It is configured for three platforms and
   pinned, and untested, because nothing has been pushed. The first push is its first
   real test.
4. WINDOWS IS DESIGNED FOR, NOT PROVEN. Ratified scope, verified only by substituting
   the platform's path behavior locally.
5. NO RELEASE DISCIPLINE. The install instruction clones a mutable main branch into a
   location whose code auto-runs on every session. For a tool that reads transcripts
   and runs hooks, that is the weakest link in the whole design: it needs tagged,
   immutable releases with checksums.
6. THE LAW FILE DOES NOT YET CONTAIN ANY OF THIS. SKILL.md has not been updated with
   the method spine, the register wiring, or the complement loops. Until it is, none
   of this binds a session.
7. NO ONBOARDING PATH. A new user has no first-run that proves it works, no vault
   setup, no Obsidian path, no ten-minute quickstart.
8. THE PRIVATE MIRROR IS UNSYNCED and the public branch is unpushed.

## 5. Sequencing recommendation

Do them in harm order, not in tidiness order: Phase 2 recovery FIRST (it protects real
work today), then Phase 3 rewiring (which makes the engine actually used and deletes
1,668 lines of the old tools), then the law update and register wiring (which makes
the learning real rather than filed), then release discipline and onboarding (which
makes it publishable), and only then Windows verification and the method-spine polish.

The counter-argument, stated because it is real: publishing earlier with honest limits
would get outside eyes on it sooner, and outside eyes have found more real defects in
this project than any internal pass. A middle path is to publish the branch and the
documentation now, clearly marked as unreleased, while keeping the installable release
tag for after Phase 3.
