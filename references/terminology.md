# Beginner terminology map

LOAD WHEN: writing anything the user will read (chat replies, status, cards, docs), or deciding whether a word is internal machinery or plain language.

The rule (roadmap section 1): the user never needs the internal terms below to
use this product. In every user-facing sentence, use the plain wording in the
right column. The internal term may appear only when the user has explicitly
asked for the advanced view (see references/status-view.md).

| Internal term | Plain wording used in ALL user-facing output |
|---|---|
| fence, file claim | "only one worker edits a file at a time" (the mechanism is not named) |
| work record, lifecycle identifier | "task history" (never shown by default) |
| store | "your project's records" |
| retrieval run | never surfaced at all |
| receipt | "your recorded approval" |
| worktree, branch | "a separate draft workspace" |
| model routing, model tiers | "picking the right helper for the job" |
| token accounting, token budgets | "work budget", stated as token ranges with a plain gloss on first use (for example "about 25k-45k tokens of model work"); "tokens" itself is allowed in ranges, matching every status and forecast example |
| hook, hook payload | "automatic session records" (never shown by default) |
| runtime adapter | "support for other AI coding tools" |
| vault | "project memory" |
| telemetry | "session records (written by the machine, not the model)" |
| orchestrator | "coordinator" |
| triage | "sizing up the task" |

Three working rules:

1. Plain wording is not a euphemism. It must state the same fact. "Only one
   worker edits a file at a time" is the whole truth of the fence; nothing
   about the rule is weakened by saying it plainly.
2. When a user asks what a plain phrase means, explain it in one sentence,
   still without the internal term, unless they ask for the machinery itself.
3. Advanced view is opt-in per request, never sticky by assumption. After
   answering an advanced question, the next default output returns to plain
   wording.

This map is the shared vocabulary for every command, card, status view, and
document in this project. A new internal term gets a row here before it is
allowed to exist in user-facing text.
