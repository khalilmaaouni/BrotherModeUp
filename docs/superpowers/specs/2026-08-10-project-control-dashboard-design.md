# The project control dashboard

Status: CURRENT. Design approved by the founder 2026-08-10. Not yet built; the
founder scheduled implementation for after the v3.1.0 tag. No em or en dashes
anywhere in this document.

## The problem, and how it was found

The founder asked for the release Gantt to become a control dashboard for every
BrotherMode project, with a live top section carrying milestones, errors
discovered and next actions.

Exploring what to build surfaced something better: THE DASHBOARD ALREADY
EXISTS. `tools/bm_view.py render` writes `PROJECT-VIEW.html` from store rows for
any project. Its `render_page()` already accepts status, alerts, insights,
briefings, decisions, facts, milestones, tasks, progress, evidence and gantt.
`tools/bm_visual.py` already ships `gantt` as its seventh shape with a
`gantt_facts()` function. The generated page's own section headings, read off
the file, include "Waiting on you", "Your next step", "Where the programme
stands", "How far each lane has moved", "How much, against what limit", "What
could still go wrong" and "Decisions waiting for your answer".

Meanwhile `docs/plan/RELEASE-v3.1.0-GANTT.html`, hand-written across a long
session, is a SECOND renderer inventing its own state from the same underlying
truth. The founder's own north-star brief names that failure directly: "No
duplicated truth" and "Do not let multiple renderers invent state
independently."

So this design is mostly a CONVERGENCE, not a build.

## Goal

One generated dashboard per project, which can never be stale by hand, carrying
a strip at the top that answers four questions at a glance:

1. What changed since I last looked?
2. What needs me right now, and what exactly do I run?
3. What could bite me, and what clears it?
4. Why was something decided the way it was?

Question 4 is the only one a machine cannot answer, and the design treats it
differently for exactly that reason.

## Decisions taken, with their alternatives

**D-1. Converge onto the generator; delete the hand-kept page.**
ALTERNATIVE: keep both, the generated page for projects and the hand page for
this release, because the hand page carries narrative a generator cannot
produce. REJECTED: two renderers of one truth will disagree, and the
disagreement is how a status page stops being believed. The PLAN stays a
document under `docs/plan/` because a plan is prose; the DASHBOARD becomes
generated only.
FLIP CONDITION: if after one month the generated page provably cannot carry
something the founder needs, the gap is named and closed in the generator
rather than by reviving a second page.

**D-2. The strip is computed mechanically at render time, plus one narrow,
clearly labelled narrative slot.**
ALTERNATIVE A: purely mechanical, no narrative at all. REJECTED: the founder
has repeatedly needed to know WHY, for instance why a merge plan was abandoned,
and no machine produces that.
ALTERNATIVE B: mechanical and narrative as equal peers. REJECTED by this
project's own telemetry law: voluntary logging collapses. A narrative band that
degrades silently is worse than none, because a reader cannot tell which half
they are reading. The narrative slot is therefore SMALL, LABELLED, and its
absence is STATED rather than implied.

**D-3. The dashboard shows the exact command that clears each finding, and
never runs it.**
ALTERNATIVE: mark some commands safe to auto-run. DEFERRED, not rejected: it is
a per-command judgement that needs its own review, and the blast-radius law
says no page takes action on state by itself.

**D-4. The checks are derived from this project's own recorded failures.**
This is the load-bearing design decision. Generic delivery advice would be
invented; every check below is a scar with a date.

## The checks, and the incident that earns each one

| Check | Earned by |
|---|---|
| Is the last green gate bound to CURRENT HEAD? | A handover quoted a green run beside a newer SHA; the green belonged to a commit two earlier |
| Any fence whose owning session is dead? | Five found on 2026-08-10 alone, each blocking a file permanently: README.md, SKILL.md twice, the findings ledger, and the README narrowing itself |
| Uncommitted or unpushed work? | Three sessions died holding work during the 8 August runaway |
| Is any accepted evidence older than the last change to what it covers? | The project's founding rule, currently unenforced by any machine |
| Is the version identity honest, meaning no tag and branch both claiming one version while holding different code? | The two-trees ambiguity that forced the withdrawal of v2.0.0-rc.1 |
| Any unresolved CRITICAL or HIGH finding? | Founder decision D8 of 2026-08-10 |
| Disk headroom above the build floor? | The documented 15 GiB gate, after the disk reached 257 MB free on 2026-08-03 |

This list is a STARTING SET, not a closed one. A new check is added when a new
defect class is recorded, and the row names its incident.

## Architecture

Three components, each with one purpose and independently testable.

### `tools/bm_flightcheck.py`, new

Pure computation. Inputs: a read-only store handle, git facts, and filesystem
facts. Output: a list of findings. It renders nothing and writes nothing.

Each check declares, at construction:
- `id`, a stable slug
- `severity`, one of `needs_you`, `at_risk`, `for_info`, matching the status
  vocabulary the visual surface already standardised on
- `statement`, one plain sentence a non-engineer can act on
- `command`, the exact copy-pasteable command that clears it, or `None` where
  no single command does
- `empty_meaning`, what it means when this check finds nothing

A check whose `empty_meaning` would be PASS is REFUSED at registration, mirroring
the pattern already shipped in the BrotherSBE checks module. This is what stops
a check being written that can only ever look calm.

### The strip renderer, inside `tools/bm_view.py`

Renders four bands at the top of the page:
1. SINCE YOU LAST LOOKED: new milestones reached and new errors found since the
   stored timestamp.
2. NEEDS YOU NOW: findings at `needs_you`, each with its command.
3. WATCH: findings at `at_risk` and `for_info`, each with its command.
4. WHY, the narrative slot: session-written notes, explicitly labelled as
   narrative, with an explicit line when empty saying no note was written rather
   than rendering nothing.

### Last-looked timestamp

Stored on the existing `views` row. No schema change. Updated when the page is
opened through the documented path, not on every render, so a regeneration by a
session does not silently consume the founder's unread changes.

## Data flow

```
store (read-only) ---+
git facts -----------+--> bm_flightcheck.run() --> findings --> render_page(strip=findings) --> PROJECT-VIEW.html
filesystem facts ----+
```

One direction. No writes on the read path. `bm_flightcheck` is `pure_read` and
registers as such in the effect-class registry, so the purity test proves it
changes zero bytes.

## Error handling, which decides whether the page can be trusted

- Four verdicts: PASS, WARN, FAIL, NO-DATA.
- NO-DATA NEVER RENDERS AS CALM. A check that could not determine its answer
  says so, in the strip, in the reader's own words. A dashboard that looks green
  because a check silently failed is worse than no dashboard, and this project
  has already shipped a suite that reported zero tests as success.
- A crashing check renders as a FAIL carrying its exception type and message,
  never as a missing row.
- If the whole strip cannot be computed, the page renders a visible "checks
  could not run" band. It never omits the strip, because an omitted strip is
  indistinguishable from a clean one.
- The strip must never break the page. A failure in any check leaves every
  other section of the dashboard intact.

## Testing

- Each check red then green against a synthetic store built in a temporary
  directory, never against the real repository.
- A NO-DATA sweep that hollows every check's inputs and asserts that no check
  ever returns PASS on empty input. This mirrors the sweep already shipped in
  the BrotherSBE evals and it is the test that keeps the whole design honest.
- Registration refusal: a check declaring an empty state of PASS is refused, and
  a test asserts that refusal.
- Purity: `bm_flightcheck` declared `pure_read` in the effect-class registry,
  covered by that registry's purity test, which snapshots the tree and fails on
  any byte change.
- Renderer: the four bands render from a fixed findings fixture, so the layout
  is asserted without depending on live state.
- No timing assertions anywhere; `tools/bm_lint_walltime.py` blocks them in CI.

## Registration, which this repository will otherwise refuse

A new tool in `tools/` must be registered in FOUR places or the gates fail it:
`SUITES` in `tools/test_all.py`, a step in `.github/workflows/tests.yml`,
`py-modules` in `pyproject.toml`, and `tools/write_sites.json` after its write
sites have been READ rather than counted. Note the apostrophe trap: comments
inside the `SUITES` tuple must contain no apostrophe, because the fact loader
parses that tuple quote to quote.

## Deliberately not built

Each is a real idea, and none is needed for what was asked.

- Auto-running any command.
- A server or any hosted surface.
- Cross-project rollup showing every project at once.
- Notifications or alerts pushed anywhere.
- Any new database table.

## What this design does not know

- How many of the seven checks can be computed cheaply enough to run on every
  render. If any is slow, it moves behind an explicit refresh rather than
  slowing the page, and that decision gets recorded.
- Whether the `views` row is the right home for the last-looked timestamp. It is
  the cheapest place that already exists; if it turns out to carry different
  semantics, the timestamp gets its own column and this line is corrected.
- Whether deleting the hand-kept page loses anything the founder valued. The
  plan document survives, so the reasoning survives; only the second RENDERER
  goes.

---

# ADDENDUM, founder instruction 2026-08-10 evening: make the design STANDARD

> "I want to make the design standard, right now it changes all the time, I like
> the current one so make it standard for all BrotherMode project."

## Reconciling this with D-1, because they look contradictory and are not

D-1 deletes `docs/plan/RELEASE-v3.1.0-GANTT.html`. The founder likes that page's
design. Both hold at once, because they are about different things:

- The DESIGN of that page is adopted as the standard.
- The second RENDERER of that page is deleted.

One design, one renderer. What the founder liked was never the fact that a
human hand-wrote it; it was the layout, and layout is exactly what a generator
should own.

## What is already standard, and must not be rebuilt

Measured before writing this, so the addendum does not invent a problem that is
already solved:

- COLOUR is already one source. `tools/bm_visual.py` carries `TOKENS_LIGHT`
  (line 110) and `TOKENS_DARK` (line 145) under a comment naming them THE
  MEASURED COLOUR TOKENS. Nothing else may declare a colour.
- The STATUS VOCABULARY is already standard: settled, at risk, needs you, for
  info, idle, node. Every band and card uses it and no page invents a new state
  name.
- DESIGN AUTHORITY documents already exist: `docs/brand/IDENTITY-CONTRACT.md`,
  `references/visual-surface.md`, and
  `docs/program/absolute-lead/DESIGN-visual-surface.md`.

So the drift is NOT in colour. It is in LAYOUT: every page assembles its own
skeleton, which is why the founder sees the design change each time.

## The standard being locked

One page skeleton, emitted by the generator, used by every BrotherMode project:

1. TITLE and one-sentence lede saying what the page is for.
2. STAMP: a monospace block naming the commit, tree state, the gate verdict and
   the session that last wrote it. Bound to a SHA, never to a date alone.
3. ALERT CARDS: a responsive row, each card one of the status vocabulary
   states, each carrying a one-line claim and a monospace evidence line.
4. THE STRIP: the four bands specified in the body of this document.
5. TIMELINE GRID: lanes down the side, stages across, bars in the four states.
6. LEDGER SECTIONS: one per lane, each a progress meter plus rows, and every
   row carrying its evidence line in monospace directly beneath it.
7. FOOTER: the tick contract restated, plus an explicit statement of what the
   page does not know.

Type stack, fixed: Iowan Old Style for display, Seravek for body, SF Mono for
every evidence line. Light and dark both styled, with the viewer's theme toggle
winning in both directions.

## The tick contract, which is the part that makes it a control surface

A box ticks ONLY when its done-check ran after the last edit and that output is
quoted in the evidence line beside it. Percentages count ticked records, never
impressions. A row with a plan and no run stays open. This is already the
founder's standing law and the skeleton makes it structural: the renderer has
nowhere to put a tick that carries no evidence string.

## How the standard is ENFORCED, and what is not enforced

ENFORCED, by a check that runs:
- One skeleton function in the generator. A page not built through it does not
  exist, because nothing else can emit a project page.
- A test asserting no shipped HTML page declares a colour literal outside
  `bm_visual.TOKENS_LIGHT` and `TOKENS_DARK`. Colour drift becomes a failing
  test rather than a matter of taste.
- A test asserting every ledger row the renderer emits carries a non-empty
  evidence string, so the tick contract cannot be violated by construction.

NOT ENFORCED, stated plainly: nothing computes whether a layout is GOOD, and
nothing stops a future session writing a one-off HTML file by hand somewhere
outside the generator. The defence against that is D-1, one renderer, and it is
a discipline rather than a control.

## Migration

`project-template/PROGRESS.html` and any other page shape are regenerated
through the skeleton, so a new project inherits the standard on day one rather
than copying whatever the last project happened to look like.
