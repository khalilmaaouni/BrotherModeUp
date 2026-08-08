# Troubleshoot BrotherMode

Use this guide when a BrotherMode command, installation check, review, delivery, collision, project view, continuity action, or recovery path does not behave as expected.

## Find the Message You Are Looking At

Search this page for the text on your screen. Every string below is quoted from the shipped source, so a partial match is enough to find your case.

| Message you see | What it means | What to do |
| --- | --- | --- |
| `refused: no store exists at .../.brothermode/store.sqlite3` | The project has no records yet | Run `bm-store init` in the project directory, then retry |
| `this store already holds project '<name>'` | One project per folder is the default model | Work in that project, or pass `--allow-second` if a second project in the same folder is genuinely wanted |
| `store is at schema N; this BrotherMode only understands up to schema M` | The records are newer than your installed copy. The store is healthy, not corrupt | Update BrotherMode. Never downgrade the store. Nothing was written |
| `store is at schema N; this BrotherMode reads schema M` | The records are older than your installed copy | Run any writing command once and the migration happens automatically |
| `refused: illegal transition for task '<id>': '<from>' to '<to>'. Legal moves from '<from>': ...` | Task states advance one step at a time, and the message names the legal moves | Move through the named state instead of skipping it |
| `cannot deliver <project>: the project has zero tasks` | Delivery has nothing to describe | Add and complete at least one task first |
| `cannot deliver: N of M task(s) have not reached the terminal state ('closed')` | The delivery gate is doing its job | Finish those tasks, or pass `--partial` deliberately |
| `no recommended next task: 0 task(s) currently in state 'ready'` | Nothing is ready, so nothing is invented | Move a task to `ready`, or resolve whatever blocks it |
| `BrotherMode is in enforced mode and refused this write because ...` | The write fence blocked a write to a file another session owns | Read the named reason, resolve ownership, then retry. `BM_FENCE_MODE=advisory` downgrades the fence to warnings, which is a deliberate loosening, not a fix |
| `bm_fence_hook: FAILING OPEN` | The fence could not evaluate the write and allowed it by design | Treat coordination as unprotected for that write and investigate the named cause |
| `BrotherMode fence: this Bash command carries an apply_patch envelope but none of its file directives could be read` | The fence cannot tell which files the command would write | Re-issue the change through the normal edit tools |
| `FAIL: setup has not been completed yet` | Install health check, setup step missing | Run `python3 scripts/setup.py` |
| `FAIL: the config has no vault_path recorded` | Install health check, memory location not configured | Run `python3 scripts/setup.py --reconfigure` |
| `FAIL: N of M listed file(s) do not match CHECKSUMS.sha256` | Installed files differ from the release manifest, often a half-finished update | Re-run the update, or restore the named files |
| `install.py: refusing to overwrite an existing installation.` | An install already exists at the target | Re-run with `--upgrade`, and with `--upgrade --dry-run` first to see the changes |
| `refusing to install on Windows.` | Native Windows is refused deliberately, not broken | Install inside WSL |
| `needs Python 3.9 or newer; this interpreter is <version>` | Interpreter too old | Use a newer Python 3 |
| `does not look like a BrotherMode checkout` | The install source is not a complete checkout | Point the installer at a full clone |
| `install.py: NOT DONE. The files were written but the smoke test failed` | Files landed, wiring did not verify | Read the listed problems. Do not treat the install as usable until they clear |

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
