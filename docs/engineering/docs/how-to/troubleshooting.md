# Troubleshoot BrotherMode

Use this guide when a BrotherMode command, installation check, review, delivery, collision, project view, continuity action, or recovery path does not behave as expected.

## Start With Doctor

Run:

```text
/brothermode:doctor
```

If Doctor reports `FAIL`, fix the install issue before debugging project state.

If Doctor has no `FAIL`, continue with the relevant case below.

## BrotherMode Commands Do Not Appear

Check the terminal install:

```bash
claude plugin marketplace add khalilmaaouni/BrotherModeUp@v3.0.0
claude plugin install brothermode@brothermode-marketplace
```

Then restart Claude Code.

If an old v2 plugin is also installed, remove it:

```bash
claude plugin uninstall brotherme
```

Run Doctor again.

## Start Produced the Wrong Goal or Scope

Do not edit `CANVAS.md` by hand.

Run:

```text
/brothermode:status
```

Correct the underlying BrotherMode project state through the conversation/workflow, then regenerate the relevant view.

The generated file is not the authority.

## Status Looks Stale

Run status again:

```text
/brothermode:status
```

If you are looking at `PROJECT-VIEW.html`, regenerate it:

```text
/brothermode:view
```

The HTML page is a snapshot. An old browser tab does not refresh itself.

## Next Gives a Blocker Instead of a Task

This can be correct.

`/brothermode:next` should not invent ready work when a required decision or dependency is unresolved. Resolve the decision, then run Next again.

## A File Write Is Refused

Do not bypass the refusal immediately.

A refusal can mean another BrotherMode session owns the file.

Actions:

1. read the owner/session information in the refusal;
2. check whether both tasks truly need the same file;
3. change the work split or use the explicit takeover/release path BrotherMode offers;
4. retry only after ownership is resolved.

BrotherMode's hard prevention covers supported Claude Code write tools and specific recognized shell write shapes. Other shell writes may be detected rather than prevented.

## Review Says Not Done

Treat the review as a gate.

1. identify the missing/failing condition;
2. fix it;
3. rerun the project-specific check;
4. run review again.

```text
/brothermode:review <task-id>
```

Do not change the wording of a generated artifact to make a failing review look complete.

## Delivery Refuses

This normally means required evidence is missing, failing, or stale.

Use this loop:

```text
STATUS -> FIX -> RUN PROJECT CHECKS -> REVIEW -> DELIVER
```

If the latest relevant edit happened after the last verification, rerun the verification.

## `PROJECT-VIEW.html` Does Not Match the Current Project

Regenerate it:

```text
/brothermode:view
```

If it is still wrong, compare `/brothermode:status` with the underlying project state. The HTML is generated output, not authority.

## A Session Ended With Open Work

For engineering use of the continuity path:

```bash
brothermode continue --dry-run
```

Inspect the generated handoff and launch command.

Then, when ready:

```bash
brothermode continue
```

A `GONE` liveness result means the successor exited. `RUNNING` means the process is still alive but has not produced output yet. `SPOKE` means output arrived.

Liveness does not prove the successor understood the task.

## Recovering After a Lost Session

Run:

```bash
brothermode recover
```

BrotherMode recovery is based on compact-boundary autosave snapshots. It is not a continuous backup system. A hard crash before the next snapshot may leave nothing newer to recover.

## Native Windows

Native Windows installation is not supported. Use WSL.

## Another Agent Runtime

BrotherMode's enforcement behavior is verified on Claude Code. Do not assume the write fence fires in another runtime just because BrotherMode instructions or CLI files are present there.

## Escalation Checklist

Before filing a bug, capture:

- BrotherMode version;
- `/brothermode:doctor` result;
- command that failed/refused;
- project directory context;
- whether the issue reproduces in a fresh session;
- whether the failure is a refusal or an exception;
- relevant generated artifact, if safe to share;
- project-specific test command and result.

Do not include credentials, tokens, or secrets in a bug report.
