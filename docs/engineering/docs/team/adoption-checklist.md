# Team Adoption Checklist

Use this checklist to evaluate BrotherMode as an engineering tool before asking the whole development team to use it.

The pilot intentionally tests the basic workflow first. Do not start by evaluating every advanced feature.

## Pilot Scope

Choose:

- 2 to 4 developers;
- 2 to 3 real but low-risk repositories/tasks;
- Claude Code as the runtime;
- one released BrotherMode version for the pilot;
- a fixed feedback period, for example one week.

## Developer Onboarding Test

Each developer should complete this without help from the BrotherMode author:

```text
1. install
2. /brothermode:doctor
3. /brothermode:start <real small task>
4. /brothermode:status
5. /brothermode:next
6. implement
7. /brothermode:review <task-id>
8. fix if needed
9. /brothermode:deliver
```

Pass criteria:

- developer can identify the next command without asking the author;
- developer can explain what `CANVAS.md` is;
- developer can explain the difference between Status and View;
- developer can explain why Review can refuse completion;
- developer can explain why Deliver can refuse;
- Doctor gives actionable remediation when something is wrong.

## Engineering Scenarios to Test

### Scenario A: Normal single-session change

Goal: confirm the happy path is understandable.

Measure:

- time to first successful Start;
- number of unclear commands;
- number of times developer asks "what do I do next?";
- whether Review catches anything useful;
- whether delivery packet matches reality.

### Scenario B: Two sessions touch the same file

Goal: validate coordination behavior.

Expected:

- supported conflicting write is refused;
- refusal identifies the ownership problem;
- developer does not need to inspect internal store files to understand it;
- team can resolve ownership without bypassing the safety mechanism.

### Scenario C: Review after final edit

Goal: validate evidence freshness behavior.

Expected:

- final edit invalidates the assumption that old evidence is sufficient;
- developer reruns the needed check;
- review/delivery does not quietly rely on stale proof.

### Scenario D: Delivery with missing evidence

Goal: validate false-success resistance.

Expected:

- delivery refuses;
- refusal tells the developer what remains;
- no `DELIVERY-PACKET.md` claims ready when the gate is unmet.

### Scenario E: New session continuation

Goal: test whether durable state reduces re-explanation.

Expected:

- new session can read current project state from BrotherMode;
- developer does not need to paste the previous entire conversation;
- if testing `brothermode continue`, dry-run creates a useful handoff before launch.

## Feedback Questions

Ask developers concrete questions:

1. At any point, did you not know which command to run next?
2. Did any command name or output surprise you?
3. Did Status match the project as you understood it?
4. Did Next recommend something you considered wrong or premature?
5. Did a fence refusal explain enough to resolve the conflict?
6. Did Review identify useful evidence or merely repeat what Claude had said?
7. Did Delivery make the handoff clearer?
8. Which step felt like overhead with no reliability benefit?
9. Which internal term appeared before you needed to know it?
10. Would you choose BrotherMode for a week-long multi-session task? Why or why not?

## Pilot Exit Criteria

Do not declare team-ready until:

- [ ] every pilot developer can complete the basic loop from the docs alone;
- [ ] installation health is reproducible;
- [ ] at least one real refusal path has been tested;
- [ ] at least one review failure and recovery loop has been tested;
- [ ] at least one successful delivery packet has been produced;
- [ ] known limitations are understood by the team;
- [ ] the README no longer needs the BrotherMode author to interpret it.

## What Not to Benchmark First

Do not make the first team evaluation about:

- marketing language;
- long-term autonomy vision;
- number of agents;
- benchmark rankings;
- advanced controller features;
- every hidden/internal command.

First prove that a developer can install, start, orient, work, review, and deliver confidently.
