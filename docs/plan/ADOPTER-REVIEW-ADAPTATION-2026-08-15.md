Status: CURRENT.

# What the adopter review changes for BrotherMode, 2026-08-15

The sibling product's adopter review produced an amendment set
(BrotherSBE, docs/adoption/2026-08-15-plan-amendment-instructions.md). The
founder ordered its lessons adapted to BrotherMode's own flows, in
BrotherMode scope only, without duplicating BrotherSBE's work. This page is
that adaptation: four items, each with its done-check, plus the explicit
list of what stays in the sibling's lane.

The insight being imported, in one sentence: a method can ship every fix
perfectly and the numbers that matter still do not move, when the real
constraint belongs to the people rather than the tooling, and gates will
happily report success while that happens.

## BM-A1. The boundary law, adapted (PROPOSED for SKILL.md)

Candidate law, recorded here exactly as it should read if the founder lands
it in the brothermode skill; until then it binds this repository's plans:

> For a flaw that belongs to the founder's capacity, the team, or the
> environment rather than to the session's own work, BrotherMode may
> measure it, reveal it at the moment of decision, remove the labour that
> feeds it, or refuse to hide it. It may not add an obligation and call
> that a fix. A rule in a prompt is not a control, and a gate in front of
> a queue is not capacity.

BrotherMode already half-lives this: the idle check refuses to count
blocked items toward queue depth because an item nobody can start cannot
rescue a night, and forecast calibration refuses to guess below its data
floor. This law names the principle those two instances share, so the next
mechanism is designed from it rather than rediscovering it.

Status: PROPOSED. Only the founder lands it in SKILL.md. Done-check:
this section exists and carries the word PROPOSED next to the SKILL.md
reference.

## BM-A2. The success scorecard: what decides whether finalization worked

Process telemetry is not success. Test counts, gate verdicts, doctor
scores, dossier and receipt counts are how work is checked, and they are
explicitly not the measure of whether BrotherMode's finalization
succeeded. The only numbers that decide it:

1. External installs, from filed transcripts. Baseline 2026-08-15: ZERO,
   single sourced from this repository's own records.
2. Cold-install outcomes from the two named testers: did the
   two-command install work first try, and what broke if not.
3. Felt-outcome scores (the 1 to 5 ask at loop close) from people other
   than the founder. Baseline: none exist.

The roadmap (docs/plan/FINALIZATION-ROADMAP-2026-08-15.md) is judged by
these three moving, and by nothing else. Done-check: the baseline zero
appears here with its date, and the roadmap names this section as its
success measure.

## BM-A3. The risk this plan must say out loud

The most likely failure of the finalization effort is that every gate goes
green, every release is tagged clean, the board is beautiful, and the
install count stays zero. If that happens the effort failed, and every
gate will say otherwise. The defence is BM-A2, and it only works if the
three numbers are read at every board refresh: the board's at-a-glance
strip carries them from today. Done-check: the risk is stated here and
the board's risk section names BM-A2 as the defence.

## BM-A4. Weekend order

The sibling's decision 6 puts the Bitbucket seam first in its weekend.
BrotherMode's weekend agrees and already says so: the one planned build
event in docs/plan/WEEKEND-EMERGENCY-PLAN-2026-08-15.md is the mirror
push and label-closing the moment the founder's workspace exists, ahead
of any queue item. TK6 stays a Monday item. Done-check: the weekend plan
and this page agree on that order.

## What stays in BrotherSBE's lane, deliberately

- The adopter-team adjustment plan amendments themselves (A1 through A9 over
  there): that plan, its parts, and its done-checks are the sibling's
  files. Nothing here edits them.
- Approval concentration (their A4): it counts signed approval trailers,
  a mechanism BrotherMode does not have and does not need; BrotherMode
  governs one person's session, where an approver distribution has no
  meaning. Building a parallel one here would be the unnecessary overlap
  the founder named.
- The five asks of the adopter team (their A5): those are decisions for that team,
  carried by the product that governs a change's passage between people.

And one rule imported verbatim from their amendment set, binding here
too: no new blocking gate is added by any of this. Every mechanism above
measures, reveals, or removes labour. A session that finds itself writing
a new refusing check to answer an adoption complaint has misread BM-A1
and must stop and ask.
