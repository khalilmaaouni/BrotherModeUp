# Install and Update BrotherMode

Use this guide to install BrotherMode for Claude Code, verify it, update it, or remove it.

## When to Use This

- first installation;
- setting up another developer machine;
- validating a team pilot;
- updating to a newer release;
- testing an unreleased checkout;
- removing BrotherMode cleanly.

## Prerequisites

- Claude Code installed and authenticated;
- Git;
- Python 3.9+;
- macOS, Linux, or WSL.

Native Windows installation is not supported.

## Stable Plugin Install

This is the default path for a development team evaluating a released version.

If an old v2 install exists:

```bash
claude plugin uninstall brotherme
```

Add the BrotherMode marketplace at the released tag:

```bash
claude plugin marketplace add khalilmaaouni/BrotherModeUp@v3.0.0
```

Install the plugin:

```bash
claude plugin install brothermode@brothermode-marketplace
```

Restart Claude Code.

### Verify the Stable Install

Inside Claude Code:

```text
/brothermode:doctor
```

Pass condition: no `FAIL` checks.

Then run:

```text
/brothermode:help
```

Confirm the BrotherMode command surface is available.

## Development Checkout

Use this only when your team is explicitly testing unreleased changes from `main`.

Keep it separate from the stable install so nobody confuses released and development behavior.

```bash
git clone --branch main https://github.com/khalilmaaouni/BrotherModeUp.git ~/.claude/skills/brothermode-dev
```

From the checkout:

```bash
cd ~/.claude/skills/brothermode-dev
python3 tools/test_all.py
```

Pass condition: the gate ends `ALL GREEN`.

Then inspect the installer before applying it:

```bash
python3 scripts/install.py --dry-run
```

If the dry run is correct:

```bash
python3 scripts/install.py
python3 scripts/doctor.py
```

Do not mix stable and development hook chains on the same Claude Code environment unless you are deliberately testing duplicate-install behavior.

## Check Version

When the packaged CLI is available:

```bash
brothermode version
```

Inside Claude Code, use:

```text
/brothermode:update
```

The update flow reports the installed version and the available release path.

## Update

Use the update command first:

```text
/brothermode:update
```

Follow the instructions it prints for your install path.

After updating:

1. restart Claude Code;
2. run `/brothermode:doctor`;
3. do not resume project work until Doctor has no `FAIL` checks.

## Uninstall

For a plugin install:

```bash
claude plugin uninstall brothermode
```

Restart Claude Code after removal.

## What You Get

A healthy install should provide:

- `/brothermode:*` public skills inside Claude Code;
- BrotherMode hooks loaded by the plugin;
- Doctor able to inspect the installation;
- normal project commands available from a project folder.

## Installation Failure Rule

If installation or Doctor fails, stop. Do not test project behavior while installation health is unresolved.
