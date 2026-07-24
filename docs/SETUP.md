# Setup

Ten minutes, three steps: install the skill, wire the hooks, create the vault. Nothing here needs admin rights or third-party packages.

## Prerequisites

- Claude Code (CLI or desktop app) with skills enabled
- Python 3 on your PATH (`python3 --version`)
- git

## Step 1: install the skill

```bash
git clone https://github.com/khalilmaaouni/BrotherModeUp.git ~/.claude/skills/brothermode
```

The path matters: Claude Code discovers skills under `~/.claude/skills/`, and the session-start script resolves its own location, so the clone is the installation. Verify:

```bash
ls ~/.claude/skills/brothermode/SKILL.md
```

Then register the trigger in your global `~/.claude/CLAUDE.md` so every session knows the skill exists:

```markdown
# brothermode
When the user types /brothermode (any casing), read and follow
~/.claude/skills/brothermode/SKILL.md before doing anything else.
```

## Step 2: wire the three hooks

Hooks make the learning loop mechanical: the model cannot forget to write telemetry, because the model is not the one writing it. Add to `~/.claude/settings.json` (create the file if it does not exist, or merge into your existing `hooks` block):

```json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [ { "type": "command", "command": "sh ~/.claude/skills/brothermode/tools/bm_sessionstart.sh" } ] }
    ],
    "SessionEnd": [
      { "hooks": [ { "type": "command", "command": "python3 ~/.claude/skills/brothermode/tools/bm_telemetry.py outcomes-append" } ] }
    ],
    "Stop": [
      { "hooks": [ { "type": "command", "command": "python3 ~/.claude/skills/brothermode/tools/bm_telemetry.py stop-warn" } ] }
    ],
    "PreCompact": [
      { "hooks": [ { "type": "command", "command": "sh -c 'p=$(cat); printf %s \"$p\" | sh ~/.claude/skills/brothermode/tools/bm_autosave.sh precompact; printf %s \"$p\" | python3 ~/.claude/skills/brothermode/tools/bm_telemetry.py precompact-brief' " } ] }
    ]
  }
}
```

What each hook does:

- **SessionStart** injects `DIGEST.md` (the 12-line law summary) plus any overdue-review nag into every new session's context.
- **SessionEnd** parses the finished session's transcript and appends one telemetry line to the ledger: tokens, tool calls, agents spawned, duration, models used. It also scans your short messages for correction candidates.
- **Stop** warns (never blocks) when a substantial session ends the day without a vault session log.
- **PreCompact** snapshots your working tree to a private git ref right before Claude Code compacts context (the token-death moment), so progress survives. Local git only, never pushes; recover with `sh tools/bm_autosave.sh recover`. It also writes a resume brief distilling the dying transcript (the last instruction, recent decisions, recent commands) so a resumed session recovers the thread, not just the files. Before a long or risky action you can log `python3 tools/bm_telemetry.py intent "next: X, because Y"` so a death leaves a forward-looking record. Optional: also add a `PostToolUse` hook running `bm_autosave.sh tick` and set `BROTHERMODE_AUTOSAVE=1` for continuous autosave between compactions (costs a hook per tool call).

Every hook is built to fail silent and exit 0. A broken hook can cost you a telemetry line; it can never cost you a work session.

## Step 3: create the vault

The vault is a plain folder of markdown notes, and the repo ships a ready-made
template with the full layout, a Home dashboard, and a one-page constitution
(AGENTS.md) that tells every session how to read and write memory:

```bash
cp -R ~/.claude/skills/brothermode/vault-template ~/BrotherModeVault
```

Open `~/BrotherModeVault` as a vault in [Obsidian](https://obsidian.md) (free).
The notes link to each other with [[wiki-links]], so Obsidian's graph view shows
how projects, failures, and decisions connect; any plain editor works too, the
links just stay as text.

To put it somewhere else, set the environment variable where Claude Code can see it (your shell profile, or the `env` block of `~/.claude/settings.json`):

```bash
export BROTHERMODE_VAULT="$HOME/path/to/your/vault"
```

Optional: if you keep per-project `STATE.md` fence registries, tell the weekly checks where they live:

```bash
export BROTHERMODE_REGISTRIES="$HOME/work/*/STATE.md"
```

Unset, those checks report NO-DATA instead of guessing.

## Verify the installation

```bash
python3 ~/.claude/skills/brothermode/tools/bm_score.py
```

Expected on a fresh machine: 10 checks, mostly NO-DATA, zero FAIL, and the closing line "LLM judge scores only the residue." NO-DATA is correct for a system with no history: the tools never invent numbers.

```bash
sh ~/.claude/skills/brothermode/tools/bm_sessionstart.sh
```

Expected: the 12-line digest, plus a nag that the weekly review has never run. That nag is your first to-do, not an error.

Then start a real session, type `/brothermode`, and give it a task. After the session ends, check that telemetry landed:

```bash
tail -1 ~/BrotherModeVault/99-System/telemetry/outcomes.jsonl
```

## Your first week

1. Copy `STATE.template.md` into your main project as `STATE.md`.
2. Read `RUBRIC.md` with whoever plays the founder role, adjust the baselines to your reality, then freeze it. A rubric that drifts cannot measure drift.
3. Work normally for a week. Let the ledger fill.
4. Run the weekly review (`tools/WEEKLY-REVIEW.md`). Your first review will be mostly NO-DATA. The second one is where the loop starts to pay.

## Uninstall

Remove the three hook entries, delete `~/.claude/skills/brothermode`, and keep or delete your vault. The vault is yours; nothing else stores state.
