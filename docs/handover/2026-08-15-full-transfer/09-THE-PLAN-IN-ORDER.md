Status: CURRENT. Written 2026-08-15.

# The plan, in the order it should be executed, and the architecture it serves

NOTHING IN THIS DOCUMENT IS BUILT. Every item below is future work. Each one
carries a line beginning FINISHED WHEN, which is the acceptance criterion to
aim at, never a statement that it happened. What actually happened is in the
close report (document 06) and carries the command that proved it.

Order is by value per unit of work, not by severity. Every item names its
stage of the north-star chain (document 10), the file it lands in, and its
criterion. Full data in `14-QUEUE.json`.

## The architecture this all serves, in one paragraph

Human intent enters, whatever development method the team already uses carries
it, BrotherMode records what execution actually did, one object called the
change passport crosses to BrotherSBE, assurance decides what had to be proven
and whether the proof is real, a human decides, the host releases, and the
world reports back whether it worked. The last four stages are where the
product is thinnest, and five of the nine holes found by walking the lifecycle
land there. That is not a coincidence to tidy up; it is the shape of the
remaining work.

## Phase 0, and it cannot wait

**0.1 TAKE THE BASELINE.** Stage: verified reality. Queue: H1.
The five queue numbers from the pilot team's 7 August report (41 waiting on
development, 22 on test resource, 23 on one reviewer, 11 in one tester's
column, 48 with no end date) are the agreed measure of whether any of this
worked. Nothing computes them. The sizing fix has ALREADY shipped, so part of
the before-picture is gone and more of it goes every day. Count them once,
however crudely, before anything else lands.
FINISHED WHEN: the five numbers are written down with the date they were
counted.

**0.2 SEND THE REVIEWERS THEIR BUILD.** Stage: method. Document 13 is the
note. It cannot be sent until BrotherSBE is pushed and given a NEW version
number, because the published v3.2.0 tag carries the version string and
neither the behaviour table nor the testkit. Do not re-point that tag.
FINISHED WHEN: a reviewer runs `ls tools/sbe_testkit.py
templates/dossier/08-behaviour.md` on the build they were sent and both exist.

## Phase 1, make the controls real before adding more

**1.1 M1, THE PRODUCT'S OWN HOOKS LOAD NOWHERE.** Stage: provenance.
On the install shape people actually use, BrotherMode is a directory copy
carrying a hooks manifest nothing reads. Every control claimed through a hook
or a registered agent is inert. This makes several other fixes academic, which
is why it leads this phase.
FINISHED WHEN: either the product is registered and one of its own hooks is
observed firing, or the limits page names by file which declared hooks and
agents do not load on a skill-copy install. The second half is already
written; the first is not.

**1.2 M3, THE GUIDED FLOW'S OWN HANDOFF IS BROKEN.** Stage: method.
A task is born `planned` and the next-step command reads only `ready`, so
planning never hands to work.
FINISHED WHEN: creating a task and then asking for the next step returns that
task.

**1.3 M5, ACCEPTANCE CHECKS ENFORCE NOTHING.** Stage: required proof.
The criterion link is optional, so a review naming no criterion can verify a
task whose acceptance checks were never examined.
FINISHED WHEN: a review moving a task to verified, while its acceptance checks
are non-empty and no criterion is named, is refused.

**1.4 M10 AND M9, THE TWO CONTROLS THAT MISREPORT.** Stage: provenance.
The close verifier halts at its first check, so a session with a full pack and
no claims gets no verdict at all. The progress-page check reports OWED forever
on a page that says in its own text that it was deliberately frozen.
FINISHED WHEN: each reports NO-DATA by name for the thing it cannot see, and
then continues to its remaining checks.

## Phase 2, close the gaps the pilot team actually reported

In this order: P3 discussion before planning, behind an estate switch and
defaulting to report rather than refuse; P7 the gate reading the plan it was
given; P11 renaming the paperwork step and naming the comparison command
beside it; P6 evidence provenance; P10 the staleness clock. Two of these
already exist as patches here (the `15-delta` files) and need folding rather
than building.

A PRECONDITION ON ALL THREE THAT REFUSE SOMETHING: an exception path carrying
an owner and an expiry date. Three new refusals were proposed with no escape
hatch, and the assurance product's own owned list requires exceptions to have
both.

## Phase 3, the half the system is blind to

Everything after the merge, and this is where the product becomes different
rather than better: an accepted state (H2), evidence bound to what is actually
running rather than to a commit (H3), a record of what happened after merge so
a risk tier can be compared with its real outcome (H5), and duration so the
cost of a tier has a measurement on either side (H8). Then the return edge:
a defect that can be entered as a defect (H4), and a requirement discovered
mid-build that tells somebody (H6).

## What NOT to build, recorded as decisions with flip conditions

- A UNIFIED COMMAND SURFACE across both products. Declined. FLIP WHEN a person
  runs a verb against the wrong product twice in one change, or the ported
  escalation ledger and its parent disagree about one objective. Both are
  countable and need nobody's opinion.
- A SECOND STORE OR JOURNAL beside the existing one. Declined: a parallel
  journal is a third source of truth, which is the defect it would claim to
  fix. FLIP WHEN a named failure the current store provably cannot express.
- THE NATIVE METHOD FLOOR AS DESIGNED. Two adversarial passes returned
  survives: false. Most of its parts exist and are broken or unreachable
  rather than absent, so Phase 1 is that work. Do not rebuild the design as
  drawn.

## The three patches (files beginning 15-delta), and the order to fold them

Read `15-DELTAS-README.md` first; it names why each was held rather than folded.
Fold the gate provenance and owed-checks patch FIRST, and RUN THE EVALS BEFORE
FOLDING IT: its own author predicted three eval cases would flip from pass to
NO-DATA and did not run them. Then the staleness clock, then the
unexamined-classes reporter.

## The standing measure

None of the above counts as success. The five numbers in 0.1 do. A green gate
is a claim about proof; whether the queue moved is a claim about the world,
and the whole point of the north star is that only the second one is the goal.
