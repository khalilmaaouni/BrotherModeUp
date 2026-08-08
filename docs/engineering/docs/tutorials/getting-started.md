# Getting Started

Install BrotherMode and take one small development task from a recorded goal to a verified delivery. This tutorial is intentionally procedural.

## What You Will Learn

By the end you will have used the normal BrotherMode loop:

```text
DOCTOR -> START -> STATUS -> NEXT -> WORK -> REVIEW -> DELIVER
```

You will also know how to tell whether each stage succeeded.

## Prerequisites

You need:

- Claude Code;
- Git;
- Python 3.9 or newer;
- macOS, Linux, or WSL;
- a project directory you can modify.

Native Windows installation is not supported. Use WSL if you are on Windows.

## Quick Path

If BrotherMode is already installed, open Claude Code in your project and run:

```text
/brothermode:doctor
/brothermode:start Add a small, testable change to this project.
/brothermode:status
/brothermode:next
```

Do the work, then:

```text
/brothermode:review <task-id>
/brothermode:deliver
```

The rest of this tutorial explains what to verify at each point.

## Step 1: Install BrotherMode

Run once from a terminal:

```bash
claude plugin marketplace add khalilmaaouni/BrotherModeUp@v3.0.0
claude plugin install brothermode@brothermode-marketplace
```

If you previously installed the old v2 plugin identity, remove it first:

```bash
claude plugin uninstall brotherme
```

Restart Claude Code after installation.

### Verify the Install

Open Claude Code and run:

```text
/brothermode:doctor
```

Continue only when Doctor reports no `FAIL` checks.

`PASS` means the check succeeded. `SKIP` means the check had nothing meaningful to evaluate in the current environment. `SKIP` is not a failure.

If Doctor reports `FAIL`, stop here and follow the remediation it prints. Do not debug project behavior before the install itself is healthy.

## Step 2: Choose a Small Real Task

For your first run, use a real change that is small enough to review in one sitting.

Good first tasks:

- add one validation rule;
- fix one reproducible bug;
- add one CLI option;
- add one small API field;
- add one focused regression test.

Avoid a large refactor or migration for the first walkthrough. The goal of this tutorial is to learn BrotherMode's control loop, not stress every advanced feature at once.

Example goal:

```text
Add a --json option to the existing report command without changing its current text output.
```

## Step 3: Start the Work

From Claude Code in the project directory:

```text
/brothermode:start Add a --json option to the existing report command without changing its current text output.
```

BrotherMode may ask questions that materially change scope. Answer them before implementation begins.

### Verify Start

After the start flow completes:

1. `CANVAS.md` should exist in the project.
2. The recorded goal should match what you actually want.
3. The scope and first decision should not silently add unrelated work.

Run:

```text
/brothermode:status
```

Use the status output as the check. Do not trust a previous chat summary instead.

## Step 4: Read Project Status

Run:

```text
/brothermode:status
```

The default view should cover these eight fields:

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

### Verify Status

Check three things:

- `Goal` matches your requested outcome.
- `Progress` does not claim work that has not happened.
- `Evidence` does not claim checks that have not run.

If any of these are wrong, correct the project state before continuing.

## Step 5: Ask for One Next Action

Run:

```text
/brothermode:next
```

BrotherMode should recommend one ready action and explain why it is next. If a human decision blocks progress, the decision should surface instead of an implementation task.

### Verify Next

A good result has one of these shapes:

- one concrete, ready unit of work; or
- one clearly named blocking decision.

Do not treat a list of unrelated possibilities as the normal next-step result.

## Step 6: Implement Normally

Work with Claude Code normally. You do not need to run a BrotherMode command before every prompt.

During implementation:

- stay inside the recorded scope;
- let BrotherMode coordinate supported file writes;
- do not bypass a write-fence refusal;
- run the project-specific tests and checks needed for the task.

If a write is refused because another session owns the file, resolve ownership instead of forcing the write.

## Step 7: Review the Task

When the task looks complete, use the task ID BrotherMode has recorded:

```text
/brothermode:review <task-id>
```

Task IDs are generated identifiers. Read the exact ID from the `/brothermode:status` or `/brothermode:next` output and paste it as printed. Do not type an ID from memory.

The review checks the work against the definition of done and records evidence.

### Verify Review

Do not look only for reassuring language. Confirm that the review identifies the evidence behind its verdict.

If anything is not ready:

1. fix the issue;
2. run the relevant project checks again;
3. run review again with the same task ID.

The important rule is that verification must cover the latest relevant change.

## Step 8: Deliver

When the requested work is genuinely ready:

```text
/brothermode:deliver
```

### Verify Delivery

A successful delivery should create:

```text
DELIVERY-PACKET.md
```

Before handing the work to another developer or reviewer, confirm:

- the expected change exists;
- required review/checks passed;
- the evidence is not stale relative to the final relevant edit;
- `DELIVERY-PACKET.md` exists;
- anything intentionally not done is stated rather than hidden.

If delivery refuses, that is an expected guardrail. Read the missing requirement, fix it, review again, then retry delivery.

## Optional Step: Generate the Project View

Run:

```text
/brothermode:view
```

This writes:

```text
PROJECT-VIEW.html
```

Open it in a browser.

The page is a snapshot of recorded project state. It is not a live dashboard. Regenerate it when you need a fresh view.

## What You Accomplished

Your project should now contain BrotherMode-generated views such as:

```text
your-project/
├── CANVAS.md
├── PROJECT-VIEW.html       # if you ran /brothermode:view
├── DELIVERY-PACKET.md      # after successful delivery
└── ...your project files...
```

These files are generated views. Do not manually edit them to change project truth.

## The Same Loop From a Terminal, With Real Output

The walkthrough above runs inside Claude Code, where the exact wording depends on the conversation. This section is the deterministic version: an empty directory, a fixed sequence of shell commands, and the output each one actually printed when this page was written. Run it once and you will recognise every state the slash commands put your real project into.

Every output block below is a real capture, not an illustration. Paths and identifiers will differ on your machine. Task identifiers are generated hex, so substitute the one your own run prints.

### Set Up a Throwaway Project

```bash
mkdir /tmp/bm-first-run && cd /tmp/bm-first-run && git init -q .
```

### Create the Project Store

Records live in a store inside the project. Nothing else works until it exists.

```bash
bm-store init
```

```text
bm_store: initialized /tmp/bm-first-run/.brothermode/store.sqlite3 (root resolved via git)
```

If you skip this step, the next command refuses and tells you the same thing:

```text
bm_project: refused: no store exists at /tmp/bm-first-run/.brothermode/store.sqlite3; run `python3 .../bm_store.py init` to create one
```

### Record the Project

```bash
brothermode start --project-id json-report --name "json-report-option" --goal "Add a --json option to the report command without changing its text output" --user-outcome "A caller can ask the report command for machine readable output" --actor-type human --actor-name "your-name"
```

```text
started project json-report (0 task(s), no forecast)
```

Verify: `CANVAS.md` now exists in the directory.

One project lives in one folder. A second `start` in the same folder refuses on purpose:

```text
cannot start project 'X': this store already holds project 'Y'; pass --allow-second to add a second project on purpose (the beginner model is one project per folder).
```

### Read the Status

```bash
brothermode status --project-id json-report
```

```text
Goal: Add a --json option to the report command without changing its text output
Direction: not agreed yet
Progress: nothing planned yet
Time remaining: not forecast yet
  I can record one as soon as there is enough to size.
Decision needed: none
Risk: none new
Evidence: no executed evidence recorded yet
Next step: agree what I am allowed to do on your behalf
  why: the outcome is recorded, and nothing can run until you authorise it
```

This is what an honest empty state looks like. Nothing is invented to fill the fields.

### Add a Task and Ask What Is Next

```bash
bm-project task add --project-id json-report --title "Add the --json flag to report()" --actor-type human --actor-name "your-name"
```

```text
added task fc9efb8212df48bf9a08683078f0a1ef
```

A new task is not ready work yet, and `next` says so rather than inventing a recommendation:

```text
no recommended next task: 0 task(s) currently in state 'ready' for project json-report
```

Move it to `ready`, then ask again:

```bash
bm-project task transition --task-id <task-id> --to ready --reason "scoped and ready to implement" --actor-type human --actor-name "your-name"
```

```bash
brothermode next --project-id json-report
```

```text
next: fc9efb8212df48bf9a08683078f0a1ef - Add the --json flag to report()
WHY: 1 candidate(s) in state 'ready' (dependency-satisfied per the protocol's own definition of that state); picked by highest priority, then whichever was added first, as the tie break.
```

### Know the Task Lifecycle Before You Fight It

Tasks advance one state at a time. Skipping is refused by name, which is the single behaviour that surprises new users most:

```text
bm_project: refused: illegal transition for task '<id>': 'active' to 'verified'. Legal moves from 'active': blocked, awaiting review. States advance through the lifecycle in order; skipping a stage would hide which evidence and review requirements were met.
```

The order, confirmed by running it:

```text
ready -> active -> awaiting review -> verified -> accepted -> delivered -> monitored -> closed
```

`blocked` is also reachable from `active`. Delivery requires `closed`, which is why the later states are not decoration.

### Review With Evidence

```bash
brothermode review <task-id> --project-id json-report --kind command --ref "python3 -m pytest -q" --note "12 passed" --reason "tests pass after the last edit" --actor-type human --actor-name "your-name"
```

```text
reviewed task fc9efb8212df48bf9a08683078f0a1ef: evidence 49c8dded97b34970ab6f82fdea8467ac recorded, task -> verified
```

The evidence is a real record: `--ref` is the command that ran, `--note` is what it reported.

### Watch Delivery Refuse, Then Succeed

Deliver too early and the gate says exactly what is missing:

```text
cannot deliver json-report: the project has zero tasks; add at least one task before delivering.
```

```text
cannot deliver: 1 of 1 task(s) have not reached the terminal state ('closed'); pass --partial to deliver anyway, or finish those tasks first.
```

Once the task reaches `closed`:

```bash
brothermode deliver --project-id json-report
```

```text
delivered json-report: all 1 task(s) closed
```

`DELIVERY-PACKET.md` now exists, and it lists the task, its state, and the evidence recorded against it.

### Generate the View

```bash
brothermode view --project-id json-report
```

```text
The page is written: /tmp/bm-first-run/PROJECT-VIEW.html
Your records changed since the last write: yes
Published page: not published yet
```

### Clean Up

```bash
rm -rf /tmp/bm-first-run
```

Nothing outside that directory was touched, and the store lived inside it.

## Quick Reference

| Command | Purpose | Verify |
| --- | --- | --- |
| `/brothermode:doctor` | Check BrotherMode itself | No `FAIL` checks |
| `/brothermode:start <goal>` | Record a project/change | Correct goal and `CANVAS.md` |
| `/brothermode:status` | Read current state | Eight fields reflect reality |
| `/brothermode:next` | Pick next action | One ready action or blocking decision |
| `/brothermode:review <task-id>` | Verify a task | Evidence-backed pass/not-yet result |
| `/brothermode:deliver` | Package completed work | `DELIVERY-PACKET.md` or honest refusal |
| `/brothermode:view` | Generate visual snapshot | `PROJECT-VIEW.html` exists |

## Common Questions

### Do I run status and next before every prompt?

No. Run them when you need project orientation or before choosing a new unit of work.

### Do I edit CANVAS.md or DELIVERY-PACKET.md?

No. They are generated views. Change the underlying BrotherMode project state and regenerate them.

### What if review says not done?

Fix the named gap, rerun the relevant checks, then review again.

### What if deliver refuses?

Treat the refusal as the delivery gate working. It should tell you what evidence or completion condition is missing.

### What if BrotherMode looks broken?

Run:

```text
/brothermode:doctor
```

Then use [Troubleshooting](../how-to/troubleshooting.md).
