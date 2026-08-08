# How BrotherMode Works

BrotherMode adds a reliability layer around Claude Code work. It does not replace the model, the repository's tests, or a development team's engineering standards.

## The Core Loop

```text
Goal
  -> durable project state
  -> one next action
  -> coordinated implementation
  -> evidence-backed review
  -> verified delivery
```

The important design choice is that project truth is not supposed to live only in chat history.

## Durable Project State

BrotherMode records project information outside the conversation so a later command can read current state without reconstructing it from memory.

Examples of information that belongs in durable state:

- goal;
- project phase/status;
- tasks and dependencies;
- decisions;
- evidence;
- risks/alerts;
- continuation information.

`/brothermode:status` reads these records rather than treating the latest chat summary as authority.

## Generated Views

BrotherMode renders human-readable artifacts from recorded state:

```text
CANVAS.md
PROJECT-VIEW.html
DELIVERY-PACKET.md
handoff packet
```

These are outputs. They are not the database of truth.

That distinction matters because a generated file can be stale or manually corrupted. Project state should be corrected at the source and rendered again.

## File Ownership and Fences

BrotherMode coordinates supported Claude Code writes so two cooperating sessions do not silently edit the same owned file.

For supported write paths, a foreign write can be refused mechanically.

This is not a security sandbox:

- it does not isolate hostile local processes;
- not every possible shell write can be prevented;
- some shell-side changes are detected after the fact rather than blocked;
- enforcement depends on Claude Code running the hooks.

The practical engineering rule is still useful: when BrotherMode refuses a write because of ownership, resolve ownership instead of overriding the mechanism.

## Evidence and Review

BrotherMode separates "the model says it is done" from "there is evidence the task meets the definition of done."

The review flow records checks/evidence and can keep a task in a not-ready state.

BrotherMode does not know whether your test strategy itself is sufficient. A green test is evidence that the test passed, not proof that you chose the right tests.

Your engineering team still owns:

- acceptance criteria;
- test quality;
- architecture;
- security review;
- production release decision.

## Delivery Gate

`/brothermode:deliver` is intentionally later than implementation.

The product tries to prevent a common failure mode:

```text
change looks complete -> assistant says done -> nobody verifies final state
```

The desired path is:

```text
change -> project checks -> BrotherMode review -> delivery packet
```

If required evidence is missing, delivery should refuse rather than manufacture a successful handoff.

## Continuity

`brothermode continue` generates a handoff packet from records and can launch a successor session.

The continuity layer distinguishes:

- state survived;
- a process was launched;
- the process is alive;
- the successor actually understood the task.

BrotherMode can provide evidence for the middle steps. It cannot prove model comprehension from process liveness alone.

## Recovery

Recovery is based on compact-boundary autosave snapshots plus durable project state.

It is not continuous backup. A hard crash between recovery points can lose uncommitted working-tree changes from that interval.

## Visual Project View

`/brothermode:view` creates a self-contained HTML snapshot from project records.

It helps humans understand project state without reading the internal store, but it is still only a render at a point in time.

## Where BrotherMode Stops

BrotherMode does not replace:

- Git;
- CI;
- repository tests;
- code review;
- operating-system permissions;
- production deployment controls;
- architecture decision ownership;
- human product judgment.

Its role is narrower: keep Claude Code work coordinated, stateful, reviewable, and harder to falsely declare complete.
