# DESIGN: the progress surface, a core reporting artifact

Status: DRAFT for the loop after the v2.1.0 tag. Written 2026-08-06 by the
orchestrator (Navigator posture) so the implementation can be delegated to a
Builder from a precise spec. No em or en dashes.

## GOAL, stated before the architecture, per the law

The founder must be able to open one artifact and answer, without asking
anybody: where does this project stand, what is finished, what is next, what is
blocked, what is at risk, what are we doing about each risk, and which document
carries the detail. Today he can answer none of those from a single place.

North star objective it serves: objective 1 (a stranger can install it and
succeed) and objective 4 (no founder instruction silently dropped). A progress
surface that nobody outside can read fails the first; one that hides a dropped
item fails the second.

## ARCHITECTURE DIRECTION, and the one rule that governs it

DERIVE, NEVER STORE A SECOND TRUTH. The store already holds every input:
`projects`, `tasks`, `dependencies`, `forecasts`, `alerts`, `evidence`,
`attribution`, `insights`, `controller_units`. The progress surface computes
from those rows at render time, exactly as `alerts_now` already does, because a
stored progress figure is a lie the moment a row moves.

This is the SAME decision the alert ladder already took and it is the reason
the alert ladder cannot go stale. Reuse it rather than inventing a second
pattern.

Where it lives: INSIDE the existing project page and its text twin, not a new
surface. Founder ratified this on 2026-08-06 against a separate report command,
because two surfaces mean two things to keep true and two places to look.

## WHAT IS ADDED, precisely

1. `tools/bm_visual.py` gains ONE new shape, `timeline`, taking its place in
   the existing `SHAPES`/`CAPS` table with its own caps, and reachable from
   `diagram_for` through a new closed phrase set. It draws lanes against
   ordered periods with a progress fraction per bar. It emits NO colour
   attribute, like every other shape, so `THEME_CSS` stays the only place
   colour lives.
2. `tools/bm_visual.py` gains `progress_facts(rows)`, a pure function returning
   a flat object: per lane, the ordered items, each with state, its evidence
   reference or the literal absence of one, and its blocking dependency ids.
   Pure, no store handle, testable without a database, same as the rest of that
   module.
3. `tools/bm_view.py` gains THREE page sections to `VIEW_SECTIONS`:
   `progress` (the timeline plus done and next), `risks` (each open risk with
   its mitigation and its owner, sorted by the existing rung order), and
   `documents` (what each finished item produced, as a path). A section with no
   rows renders its designed empty state; a blank section is a defect, which is
   the rule that already governs the other twelve.
4. Risks come from `insights` of kind RISK and from `alerts_now`. A risk with
   no mitigation recorded renders the words "no mitigation recorded" rather
   than an empty cell, because an empty cell reads as safe.

## WHAT MUST NOT HAPPEN

- No new table. If a fact cannot be derived, the gap is in what the work
  records, and the fix belongs there, not in a new store of progress numbers.
- No percentage that is not defined. A progress fraction is finished items over
  planned items in that lane, stated on the page in those words, never an
  invented confidence figure.
- No date arithmetic in these modules. Every duration comes from
  `bl.render_forecast_lines`, which a shipped structural guard already
  enforces for both files.
- No second collector: `bm_view` defines no `collect_*` of its own, also
  already guarded.

## DONE-CHECK for the implementing agent

```
python3 tools/test_bm_visual.py     exits 0, no count drop
python3 tools/test_bm_view.py       exits 0, no count drop
python3 tools/test_bm_docs.py       exits 0
```
Plus a rendered page inspected by eye against a project with: zero tasks, one
task, a blocked task, a risk with no mitigation, and a non-ASCII label.

## REFUTATION, mandatory before it lands

Three refuters in parallel on the strongest tier, per the pattern that found
real defects twice out of two attempts: correctness (can the page show a number
that does not match its rows), safety (can founder prose or a path reach the
page unredacted, can a URL become a capability), and failure surface (force
every refusal it can hit and confirm each renders as a founder-facing block).
This module is the largest body of code in the repository that has never been
refuted, which is why the refutation is not optional here.
