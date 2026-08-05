# The default status view

LOAD WHEN: the user asks how the project is going, a status is due at a phase boundary, or you are about to report progress in any form.

## The default view: exactly these eight fields, in this order

```text
Goal
Direction
Progress
Time remaining
Decision needed
Risk
Evidence
Next step
```

Rules for filling them in:

- Goal: the outcome in the user's own words, one line.
- Direction: the approach currently agreed, one line.
- Progress: accepted work over planned work, in plain units ("4 of 9 tasks
  accepted"), never percentages of effort you cannot measure.
- Time remaining: always a range with confidence, never a point date
  (references/forecasting.md governs the format).
- Decision needed: the one decision waiting on the user, or "none". If there
  is one, it travels as a decision card (references/kickoff.md), not prose.
- Risk: only risks whose severity changed or that need a decision. No
  standing worry list.
- Evidence: what proves the progress claim, in plain words ("the booking test
  suite passed after the last change"). Name the check, not the log.
- Next step: exactly one recommended next action.

Every word obeys the terminology map (references/terminology.md): no fences,
records, worktrees, tokens as raw counts, or hook names in this view.

## The advanced view: only on explicit request

Only when the user explicitly asks for advanced detail (for example "show me
the advanced view", "show the machinery", "which model did this") may these
appear:

- task IDs;
- runtime and model identifiers;
- token input and output details;
- worktree paths;
- commands that were run;
- raw test output;
- hook evidence;
- store verification;
- receipt fingerprints.

None of these ever appear in the default view. Advanced is per request: the
next default status returns to the eight fields above.

## IC mode: the same records, read by the person doing the engineering

IC mode is not a second status and not a second set of records. It is the same
eight fields above, from the same collector, rendered for an engineer: the
lifecycle identifier behind the file claim, unit ids and the run's own state,
raw token and minute totals against both ceilings, the evidence class and the
exact command behind a claim, which trigger made a decision a key decision, the
contract id with its revision and state, open dispatch ids with their ages, and
the counts behind the catch-up clock. Every field the two views share carries
the same value in both, because there is one collector and two renderers.

Three rules, and the first one is what keeps this honest:

- **It is always explicit.** Two switches turn it on and nothing else does: the
  `--ic` flag on the command, and the environment variable
  `BROTHERMODE_VIEW=ic`. The flag is per request. The variable is sticky, which
  is why the next rule exists.
- **Every IC render names the switch that turned it on**, in one footer line,
  with how to turn it off. A sticky mode that does not say it is on is a mode
  the reader did not choose, which is the rule at the end of the advanced-view
  section above read for a standing setting rather than one request.
- **The default view is unchanged.** With neither switch set, what prints is
  the eight fields at the top of this page, in plain wording, and nothing else.
  IC mode and the advanced view are independent: `--ic` turns on no advanced
  item, `--advanced` turns on no IC block, and asking for one never implies the
  other.

## The page is this view, not a second status

The live project view (`PROJECT-VIEW.html`, written by `bm-view render`) does
not introduce a second status. Its header and its next step are the same eight
fields above, from the same collector, so a field that reads one way in the
chat cannot read another way on the page. What the page ADDS is what a page is
good at and a terminal is not: the drawings, the history of what was learned,
the timeline of catch-ups, the standing offer to take the work back, and the
short note in every section nothing has filled in yet. What it never does is
answer the eight questions differently. If the page and this view ever disagree
on a shared field, the page is the defect. The rules of this page (plain
wording, ranges with confidence, exactly one recommended next action, advanced
detail only on request) bind the page exactly as they bind the terminal, and
`references/visual-surface.md` is the register for the parts that exist only
there.
