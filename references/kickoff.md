# Guided kickoff, decision cards, and error cards

LOAD WHEN: a new project or sizable goal is being started, a decision must be put to the user, or an error must be reported to the user.

## The kickoff flow

The goal of kickoff is one agreed direction, not a completed interview.

1. Detect before asking. Look at what is already there (project type, git
   repository, existing tests, uncommitted work) and infer the user's
   experience level from how they describe the goal. Never ask a question the
   tree can answer.
2. Scan the project context once and keep the map; do not rescan unchanged
   areas later.
3. Ask adaptive questions ONLY when the answer would change the scope or the
   solution. Everything else gets a stated assumption the user can correct.
4. One decision at a time, as a decision card (below), recommended option
   first. Never a wall of questions.
5. Present the recommended direction first; alternatives only when they are
   materially useful, never for completeness.
6. Close kickoff by writing the project brief: outcome, intended user,
   recommended direction and why, what is included, what is explicitly not,
   success checks, main risks, decisions made, decisions still open, and the
   initial forecast (format per references/forecasting.md). The canvas
   template at project-template/CANVAS.md carries these headings. Save the
   approved brief as `CANVAS.md` at the top of the user's project folder; the
   status and next-step flows read the current state from there after a
   restart.
7. The brief is the source of direction from then on. Work does not start
   until the main scope and the highest-stakes open decision are settled.

State expectations at kickoff start in forecast form: how long the definition
itself will likely take, as a range with confidence, per
references/forecasting.md.

All wording obeys references/terminology.md: plain language, no machinery.

## Decision cards

Every decision put to the user uses this shape:

```text
Decision needed: Payment approach

Recommended: Hosted checkout
Why: Lowest security burden and fastest reliable launch

Other option: Fully embedded checkout
Tradeoff: Better visual control, but more implementation and compliance work

[Use hosted checkout]
[Use embedded checkout]
[Explain more]
```

Rules:

- The recommended option always comes first, with its Why.
- Each alternative carries its Tradeoff in one line.
- 2 to 4 option buttons, one of which may be "Explain more".
- In clients with a native question UI (in Claude Code, the AskUserQuestion
  windows), the card travels through that UI, recommended option first and
  marked. Chat text carries evidence and context, never the option list.
- One card per decision, highest-stakes decision first when several queue up.

## Error cards

Every error reported to the user uses these four sections, in this order:

```text
I could not verify the payment flow.

What happened
The sandbox rejected the merchant credentials.

Impact
Checkout cannot be marked ready.

Recommended action
Add valid sandbox credentials, then I will rerun the complete payment test.

What remains safe
The booking and availability work is unchanged.
```

Rules:

- What happened / Impact / Recommended action / What remains safe, always in
  that order, always all four.
- No raw stack traces by default. The technical trace appears only under the
  advanced view (references/status-view.md).
- Explain the user impact before the technical cause.
- Offer exactly one recommended action first; alternatives only if the
  recommended one may be unavailable to the user.
- "What remains safe" is mandatory because it is the sentence that prevents
  panic; if nothing is safe, say that plainly instead.
