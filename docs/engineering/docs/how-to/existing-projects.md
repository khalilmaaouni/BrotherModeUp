# Use BrotherMode in an Existing Project

Use BrotherMode around an existing codebase without replacing the repository's engineering process, test stack, architecture, or project documentation.

## When to Use This

- bug fixes in an established repository;
- features in a mature service;
- controlled refactors;
- multi-session work where context loss is expensive;
- parallel Claude work where file collisions matter.

## Prerequisites

- BrotherMode installed and `/brothermode:doctor` has no `FAIL` checks;
- the repository's normal build/test instructions are known;
- you have a bounded change to make.

## Step 1: Open Claude Code at the Repository Root

Start from the real project root so BrotherMode reads and writes the correct project records.

Do not create a second artificial repository just for BrotherMode.

## Step 2: Start the Bounded Change

Describe the outcome and the most important constraint in one command:

```text
/brothermode:start Fix duplicate invoice exports without changing the CSV schema or existing API behavior.
```

For an existing codebase, good goals normally include:

- what must change;
- what must not change;
- the affected user/system outcome;
- any known hard boundary.

Avoid embedding a full implementation plan in the goal. Let the project/code evidence determine the implementation.

## Step 3: Verify BrotherMode Understood the Work

Run:

```text
/brothermode:status
```

Check:

- Goal is correct.
- Direction does not contradict the repository's existing architecture.
- Risk reflects the real blast radius.
- Evidence is empty/limited if no checks have run yet.

If the status is wrong, correct it now. Do not compensate later with a hand-edited generated file.

## Step 4: Select One Ready Unit

Run:

```text
/brothermode:next
```

The next action should be small enough to verify and should respect dependencies.

For large changes, repeat the loop rather than asking one task to carry the entire migration.

## Step 5: Use the Repository's Own Engineering Rules

BrotherMode does not replace the existing project's:

- architecture rules;
- coding conventions;
- branch policy;
- test runner;
- linting;
- CI requirements;
- review policy.

Run the project's real commands. Examples only:

```bash
pytest
npm test
make test
./gradlew test
```

The correct command is whatever this repository actually uses.

## Step 6: Review the Task

Run:

```text
/brothermode:review <task-id>
```

If the task is not ready, fix it and re-run both the project checks and BrotherMode review.

## Step 7: Re-check Project State

Run:

```text
/brothermode:status
```

This catches drift between what one chat says happened and what the BrotherMode records actually contain.

## Step 8: Deliver

When the bounded change is complete:

```text
/brothermode:deliver
```

Confirm `DELIVERY-PACKET.md` matches the actual diff and verification evidence.

## Parallel Work

If multiple Claude sessions operate on the same repository:

- give each session a bounded unit of work;
- let BrotherMode claims/fences coordinate supported writes;
- do not bypass ownership refusal because another session appears idle;
- re-scope tasks when two units need the same file.

BrotherMode is coordination, not an operating-system sandbox. A hostile local process can still write to your files.

## What You Get

You keep the existing repository structure and engineering process, plus:

- durable BrotherMode project state;
- a generated project brief;
- current status and next-action selection;
- evidence-backed review;
- write-coordination for supported Claude Code write paths;
- a delivery packet at the end.
