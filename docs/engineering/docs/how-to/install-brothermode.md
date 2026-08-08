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

## Scripted and CI Installs

The plugin path expects a person at a keyboard. For a provisioning script, a container image, or a machine that must not be surprised, drive the installer directly from a checkout and read its exit code.

Installer flags, taken from `scripts/install.py --help`:

| Flag | Effect |
| --- | --- |
| `--target <path>` | Where the installed copy lives. Default `~/.claude/skills/brothermode` |
| `--settings <path>` | Which Claude Code settings file gets the hook wiring. Default `~/.claude/settings.json` |
| `--upgrade` | Allow overwriting an existing install and rewiring the hook entries it already owns |
| `--dry-run` | Print every change that would be made and write nothing |
| `--no-hooks` | Install files only and leave the settings file untouched |

A safe provisioning sequence:

```bash
python3 scripts/install.py --dry-run
python3 scripts/install.py --upgrade
python3 scripts/doctor.py
```

Notes that matter in an automated context:

- Without `--upgrade`, an existing install is refused rather than overwritten, and nothing is changed.
- The settings file is backed up before it is modified.
- `--no-hooks` genuinely skips the settings write. Nothing is wired, so nothing is enforced.
- Native Windows is refused by design with an explanatory message. Use WSL.
- Python older than 3.9 is refused.
- After writing files, the installer runs its own smoke test and reports `NOT DONE` if that fails. Treat a `NOT DONE` as a failed install even though files exist.

## Environment Variables

Useful when scripting, testing, or pointing commands at a project from elsewhere. Each was read from its use site in the source.

| Variable | Controls | Default when unset |
| --- | --- | --- |
| `BROTHERMODE_ROOT` | Which project root and store the commands resolve to, instead of walking up from the working directory | Walks up from the working directory |
| `BROTHERMODE_VAULT` | Where the memory vault lives | `~/BrotherModeVault` |
| `BROTHERME_CONFIG` | Path to the setup config file | `~/.brotherme/config.json` |
| `BROTHERMODE_AUTOSAVE` | Turns the autosave snapshot hook on. Any non-empty value enables it | Off |
| `BROTHERMODE_AUTOSAVE_EVERY` | Tool calls between autosave snapshots | `20` |
| `BROTHERMODE_AUTOSAVE_RETAIN` | How many snapshots are kept before pruning | `10` |
| `BROTHERMODE_VIEW` | Set to `ic` for the engineering view of status output | Plain view |
| `BROTHERMODE_NO_BELL` | Set to `1` to suppress the terminal bell on an alert | Bell fires |
| `BROTHERMODE_SKIP_GIT_CONTAINMENT` | Skips the guard that refuses to leave the records file somewhere Git would commit it | Guard runs |
| `BM_FENCE_MODE` | Set to `advisory` to downgrade write-fence refusals to warnings | Enforced |

Setting `BM_FENCE_MODE=advisory` removes a protection. Do it knowingly, not to make an error message go away.

## What Lands on Disk

The installer copies the checkout into the target directory, excluding version control data, local records, caches, and machine state. The top level of a healthy install looks like this:

```text
~/.claude/skills/brothermode/
├── SKILL.md, README.md, VERSION, CHANGELOG.md, LICENSE
├── CHECKSUMS.sha256, pyproject.toml
├── agents/
├── commands/
├── docs/
├── hooks/
├── references/
├── scripts/
├── skills/
├── tools/
└── vault-template/
```

Two quick disk-level checks:

```bash
cat ~/.claude/skills/brothermode/VERSION
```

```bash
sh ~/.claude/skills/brothermode/scripts/verify-install.sh
```

The second re-hashes the installed files against the shipped manifest, which is a stronger statement than "the command ran".

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
