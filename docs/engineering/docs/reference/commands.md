# Command Reference

Use this page to look up BrotherMode's public operating commands. Slash commands are the normal interface inside Claude Code.

## Public Claude Code Commands

| Command | When to use | Main effect | Verify success |
| --- | --- | --- | --- |
| `/brothermode:start <goal>` | Beginning a bounded project/change | Records the project and generates `CANVAS.md` | Goal is correct; `CANVAS.md` exists |
| `/brothermode:status` | Need current orientation | Reads project records into eight fields | Goal/progress/evidence match reality |
| `/brothermode:next` | Need one next action | Selects the highest-priority ready task | One ready task or blocking decision appears |
| `/brothermode:review <task-id>` | Task looks finished | Records evidence and review transition | Pass/not-yet result is backed by checks |
| `/brothermode:deliver` | Verified work is ready for handoff | Generates `DELIVERY-PACKET.md` | Packet exists, or refusal names the unmet gate |
| `/brothermode:view` | Need a visual snapshot | Generates `PROJECT-VIEW.html` | File opens and reflects current recorded state |
| `/brothermode:doctor` | Install/update issue or routine health check | Runs install-health checks | No `FAIL` checks |
| `/brothermode:update` | Intentionally checking for a new version | Reports installed/latest version and update path | Version result is explicit; Doctor is clean after any update |
| `/brothermode:help` | Unsure which command to use | Gives contextual orientation | You leave with one clear next action |

## `/brothermode:start`

**Use when:** you are beginning a new project or one bounded change that needs its own tracked outcome.

**Input:** a plain-language goal.

```text
/brothermode:start Fix the duplicate invoice export without changing the CSV schema.
```

**Expected effects:**

- BrotherMode clarifies decisions that materially change scope.
- Project state is initialized if needed.
- The goal is recorded.
- `CANVAS.md` is generated from recorded state.

**Verify:** run `/brothermode:status` and confirm the goal and scope are correct.

## `/brothermode:status`

**Use when:** starting a session, after meaningful progress, after a decision, or whenever chat memory is no longer enough.

Default fields:

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

**Verify:** missing information should stay missing rather than being filled with a confident guess.

## `/brothermode:next`

**Use when:** you are choosing the next unit of work.

**Expected result:** one ready task chosen from project records, with a reason. If a human decision blocks progress, the decision should appear instead.

**Verify:** the recommendation is dependency-ready and still inside the recorded scope.

## `/brothermode:review <task-id>`

**Use when:** a task appears complete and you want an acceptance verdict.

```text
/brothermode:review <task-id>
```

Task IDs are generated identifiers. Copy the ID exactly as printed by `/brothermode:status` or `/brothermode:next`.

**Side effect:** review records evidence and may transition task state.

**Verify:** every claimed pass has evidence. A failing or missing check must remain visible.

## `/brothermode:deliver`

**Use when:** the requested result is actually ready to hand to another person or system.

**Expected output:**

```text
DELIVERY-PACKET.md
```

**Gate:** BrotherMode should not call the work ready when required verification is missing or stale relative to the latest relevant change.

**Verify:** inspect the packet and confirm both completed work and intentional omissions are represented.

## `/brothermode:view`

**Use when:** you want a visual project snapshot for yourself or another stakeholder.

**Expected output:**

```text
PROJECT-VIEW.html
```

The file is self-contained and represents project records at generation time. It does not update itself while open.

**Verify:** rerun the command after records change and confirm the generated snapshot changes accordingly.

## `/brothermode:doctor`

**Use when:** after installation, after update, or when BrotherMode behavior seems wrong.

Doctor reports checks as:

- `PASS`: check succeeded;
- `FAIL`: check found a problem that needs attention;
- `SKIP`: nothing meaningful could be checked in that condition.

**Verify:** no `FAIL` checks.

## `/brothermode:update`

**Use when:** you intentionally want to compare your installed version with the latest release.

The command is a report. It should not silently perform the update for you.

**Verify after updating:** restart Claude Code and run `/brothermode:doctor`.

## `/brothermode:help`

**Use when:** you know what you want to achieve but not which BrotherMode workflow to invoke.

For normal use, the important commands are still:

```text
start
status
next
review
deliver
```

## Shell CLI Boundary

BrotherMode also has a deterministic shell CLI when the console script is installed:

```text
brothermode start
brothermode status
brothermode next
brothermode review
brothermode deliver
brothermode view
brothermode doctor
brothermode recover
brothermode version
brothermode continue
brothermode update
```

The shell CLI is useful for engineering, automation, continuity, and debugging. Plugin users can use the slash commands for the normal daily path.

### `brothermode continue`

Generates a handoff packet from records and can launch a successor session.

```bash
brothermode continue --dry-run
```

Use dry-run first when testing the handoff. It generates the packet and prints the launch command without launching.

### `brothermode recover`

Attempts recovery from BrotherMode's compact-boundary autosave snapshots.

This is not continuous backup. A crash before the next available snapshot may leave no new BrotherMode recovery point.

### `brothermode version`

Prints the installed BrotherMode version.

## Generated Files Are Not Commands

Do not change project truth by editing:

```text
CANVAS.md
PROJECT-VIEW.html
DELIVERY-PACKET.md
```

These are generated views. Use BrotherMode commands to change state, then regenerate the view.
