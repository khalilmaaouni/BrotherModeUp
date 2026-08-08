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
