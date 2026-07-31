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
