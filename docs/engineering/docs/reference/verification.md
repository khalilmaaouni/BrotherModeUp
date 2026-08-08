# Verification Reference

This page defines the practical acceptance gate after each BrotherMode stage. Use it when a developer asks, "How do I know this worked?"

## Gate 0: Install Health

Run:

```text
/brothermode:doctor
```

Pass condition:

- no `FAIL` checks.

Do not diagnose project workflow problems until this gate is clean.

## Gate 1: Project Start

Run:

```text
/brothermode:start <goal>
/brothermode:status
```

Pass conditions:

- `CANVAS.md` exists;
- status `Goal` matches the requested outcome;
- scope does not include unrelated work;
- unresolved decisions are visible rather than silently assumed.

## Gate 2: Current State

Run:

```text
/brothermode:status
```

Pass conditions:

- all eight default fields are present;
- progress matches recorded work;
- risk is not hidden;
- evidence does not claim checks that have not run;
- the next step is plausible from the current state.

## Gate 3: Next Work Selection

Run:

```text
/brothermode:next
```

Pass conditions:

- exactly one primary next action is recommended;
- the reason is visible;
- prerequisites/dependencies are satisfied;
- if a human decision blocks work, the decision appears instead of a fake ready task.

## Gate 4: Implementation

BrotherMode does not replace project-specific engineering checks.

Run the repository's normal validation, for example:

```bash
pytest
npm test
npm run lint
make test
```

Use the checks appropriate to the project. Do not invent a generic BrotherMode test as a substitute for the codebase's own acceptance conditions.

Pass conditions:

- requested behavior works;
- regression coverage is appropriate;
- unrelated behavior remains intact;
- work remains inside agreed scope.

## Gate 5: Task Review

Run:

```text
/brothermode:review <task-id>
```

Pass conditions:

- definition-of-done checks are evaluated;
- evidence identifies what actually ran or exists;
- failures remain failures;
- missing checks remain missing;
- verification is refreshed after relevant fixes.

If not ready:

```text
FIX -> rerun project checks -> REVIEW AGAIN
```

## Gate 6: Delivery

Run:

```text
/brothermode:deliver
```

Pass conditions:

- `DELIVERY-PACKET.md` is generated;
- claims in the packet match actual delivered work;
- required checks are represented;
- checks cover the latest relevant change;
- omitted work/known limitations are visible.

A refusal is a failed gate, not a tool crash. Resolve the named condition and retry.

## Gate 7: Visual Snapshot

Run:

```text
/brothermode:view
```

Pass conditions:

- `PROJECT-VIEW.html` exists;
- it opens locally;
- it reflects the current recorded state;
- users understand it is a snapshot rather than a live control surface.

## Gate 8: Session Continuity

For engineering/testing of the continuity path:

```bash
brothermode continue --dry-run
```

Pass conditions:

- a handoff packet is generated from records;
- a successor launch command is printed;
- nothing is launched in dry-run mode.

For a real continuation:

```bash
brothermode continue
```

BrotherMode records liveness as `SPOKE`, `RUNNING`, or `GONE`.

- `SPOKE`: output arrived;
- `RUNNING`: process is still alive but has not emitted output yet;
- `GONE`: process exited before establishing liveness.

Liveness does not prove the successor understood the work.

## Gate 9: Recovery

Run only when recovery is needed:

```bash
brothermode recover
```

Pass condition depends on an available compact-boundary autosave snapshot.

Do not treat a lack of recoverable material as evidence of corruption. BrotherMode recovery is not continuous backup.

## Delivery Checklist

Before calling a BrotherMode project/change complete:

- [ ] install healthy;
- [ ] goal correct;
- [ ] scope correct;
- [ ] task selected from current state;
- [ ] project-specific tests/checks executed;
- [ ] review completed after the latest relevant fix;
- [ ] no unresolved review gap hidden;
- [ ] delivery packet generated;
- [ ] known limitations recorded;
- [ ] open work handed over if the session is ending.
