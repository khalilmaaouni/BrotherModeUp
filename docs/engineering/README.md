# BrotherMode

BrotherMode is a Claude Code reliability layer for development work. It keeps project state durable, coordinates file ownership, records verification evidence, and refuses delivery when required checks are missing.

This README is the engineering entry point. If you want the product story and visual explanation, read the booklet after you have completed the first workflow.

## Start Using BrotherMode

**Prerequisites:** Claude Code, Git, Python 3.9+, and macOS/Linux or WSL. Native Windows installation is not supported.

Install the current stable plugin once from a terminal:

```bash
claude plugin marketplace add khalilmaaouni/BrotherModeUp@v3.0.0
claude plugin install brothermode@brothermode-marketplace
```

Restart Claude Code, open it in your project folder, then run:

```text
/brothermode:doctor
```

Proceed only when Doctor reports no `FAIL` checks.

Then start real work:

```text
/brothermode:start <what you want to build or change>
```

The normal engineering loop is:

```text
START -> STATUS -> NEXT -> WORK -> REVIEW -> FIX IF NEEDED -> REVIEW -> DELIVER
```

Commands:

```text
/brothermode:start <goal>
/brothermode:status
/brothermode:next
/brothermode:review <task-id>
/brothermode:deliver
```

**[Run the complete first-project tutorial ->](docs/tutorials/getting-started.md)**

**[See the full workflow map ->](docs/reference/workflow-map.md)**

## Daily Workflow

| Step | Command | Run it when | Verify before continuing |
| --- | --- | --- | --- |
| 0 | `/brothermode:doctor` | After install/update or when BrotherMode looks unhealthy | No `FAIL` checks |
| 1 | `/brothermode:start <goal>` | Once when beginning a project or bounded change | Goal is correct and `CANVAS.md` exists |
| 2 | `/brothermode:status` | Start of a session, after major progress, or when uncertain | Status reflects the real goal, progress, risk, evidence, and next step |
| 3 | `/brothermode:next` | Before choosing the next unit of work | One ready action or one blocking decision is returned |
| 4 | Work with Claude normally | While implementing | Stay inside the agreed scope and respect write-fence refusals |
| 5 | `/brothermode:review <task-id>` | When a task looks finished | Review records evidence and reports pass/not-yet honestly |
| 6 | Fix and review again | When review reports a gap | Required checks pass after the latest relevant edit |
| 7 | `/brothermode:deliver` | When the requested work is actually ready to hand over | `DELIVERY-PACKET.md` is created, or delivery refuses with a concrete reason |

For the exact success criteria at each gate, use **[Verification Reference](docs/reference/verification.md)**.

## What Files Matter

BrotherMode keeps project state in its own records. The files below are generated views of those records:

| File | Purpose | Edit manually? |
| --- | --- | --- |
| `CANVAS.md` | Project brief and agreed direction | No |
| `PROJECT-VIEW.html` | Snapshot of current project status and progress | No |
| `DELIVERY-PACKET.md` | Delivery summary and verification evidence | No |
| Handoff packet | Context for the next session when work continues | No |

If a generated file is wrong, correct the underlying project state through BrotherMode and regenerate it. Do not edit the generated file to make the project look complete.

## Common Engineering Actions

| Need | Use |
| --- | --- |
| Check the install | `/brothermode:doctor` |
| Start a project/change | `/brothermode:start <goal>` |
| Know current state | `/brothermode:status` |
| Pick one next action | `/brothermode:next` |
| Verify a task | `/brothermode:review <task-id>` |
| Generate visual status | `/brothermode:view` |
| Package verified work | `/brothermode:deliver` |
| Check for a release | `/brothermode:update` |
| Get contextual help | `/brothermode:help` |

See **[Command Reference](docs/reference/commands.md)** for behavior, outputs, and failure cases.

## Documentation

- **[Getting Started](docs/tutorials/getting-started.md)**: install BrotherMode and complete one small project end to end.
- **[Workflow Map](docs/reference/workflow-map.md)**: understand the command order, optional paths, and generated outputs.
- **[Command Reference](docs/reference/commands.md)**: exact purpose, timing, outputs, and verification for each public command.
- **[Verification Reference](docs/reference/verification.md)**: what must be true before moving to the next stage.
- **[Install and Update](docs/how-to/install-brothermode.md)**: stable install, development checkout, update, and uninstall.
- **[Existing Projects](docs/how-to/existing-projects.md)**: adopt BrotherMode in an established repository without rewriting the project structure.
- **[Troubleshooting](docs/how-to/troubleshooting.md)**: diagnose install, state, review, delivery, collision, view, and recovery problems.
- **[How BrotherMode Works](docs/explanation/how-brothermode-works.md)**: state, fences, evidence, generated views, continuity, and limits.
- **[Team Adoption Checklist](docs/team/adoption-checklist.md)**: a controlled engineering pilot for a development team.
- **Booklet**: `docs/book/brothermode-solo-builder-booklet.html` remains the long-form visual explanation. It is not the first-run operating guide.

## Engineering Rules to Remember

1. Start from a recorded goal, not an assumed one.
2. Read status from BrotherMode records, not from chat memory.
3. Use one recommended next action at a time.
4. Respect file-ownership refusals. Do not bypass them to save time.
5. A task is not done because the code looks done. Review it.
6. Verification must be fresh enough to cover the latest relevant change.
7. Delivery is a gate. A refusal is a result, not a crash.
8. Generated views are not the source of truth.
9. Recovery is not a continuous backup service.
10. BrotherMode enforcement is verified for Claude Code. Do not assume the same enforcement in another agent runtime.

## Getting Help

If you do not know what to run next:

```text
/brothermode:help
```

If you think BrotherMode itself is broken:

```text
/brothermode:doctor
```

If a project action is refusing, read the refusal first. The refusal normally names the missing evidence, ownership conflict, or required action.
