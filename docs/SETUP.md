# Setup

Ten minutes, three steps: install the skill, wire the hooks, create the vault. Nothing here needs admin rights or third-party packages.

For a version of this with copy-pasteable commands, expected output at every
step, and one concrete piece of evidence at the end, see `docs/QUICKSTART.md`.
This page is the reference: the full hook explanation and the first-week
checklist that QUICKSTART.md points back to.

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

## Step 2: wire the four hooks

An earlier version of this page said three hooks. That was wrong: the block
below installs four (`SessionStart`, `SessionEnd`, `Stop`, `PreCompact`),
counted directly from the JSON. Hooks make the learning loop mechanical: the
model cannot forget to write telemetry, because the model is not the one
writing it. Add to `~/.claude/settings.json` (create the file if it does not exist, or merge into your existing `hooks` block):

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
      { "hooks": [ { "type": "command", "command": "sh -c 'p=$(cat); printf %s \"$p\" | python3 ~/.claude/skills/brothermode/tools/bm_autosave.py precompact; printf %s \"$p\" | python3 ~/.claude/skills/brothermode/tools/bm_telemetry.py precompact-brief' " } ] }
    ]
  }
}
```

What each hook does, and honestly, what a FAILED hook costs you. The four
hooks do not all cost the same thing when they break, and treating them as
equivalent would be dishonest: losing a data point is not the same class of
loss as losing your ability to recover from a crash.

- **SessionStart** injects `DIGEST.md` (the 12-line law summary) plus any overdue-review nag into every new session's context.
  If this hook fails: the new session simply starts without the digest and
  nag text. Nothing is lost, nothing is recorded wrong; the session just
  begins less informed than it should.
- **SessionEnd** parses the finished session's transcript and appends one telemetry line to the ledger: tokens, tool calls, agents spawned, duration, models used. It also scans your short messages for correction candidates.
  If this hook fails: that one session's telemetry line and correction scan
  never happen. This costs you telemetry, one data point in the learning
  loop, nothing more. Your work, your files, and your vault notes are
  unaffected.
- **Stop** warns (never blocks) when a substantial session ends the day without a vault session log.
  If this hook fails: you simply do not get reminded to write a session log.
  It is advisory only; it writes nothing and protects nothing.
- **PreCompact** snapshots your working tree to a private git ref right before Claude Code compacts context (the token-death moment), so progress survives. Local git only, never pushes; recover with `python3 tools/bm_autosave.py recover`. It also writes a resume brief distilling the dying transcript (the last instruction, recent decisions, recent commands) so a resumed session recovers the thread, not just the files. Before a long or risky action you can log `python3 tools/bm_telemetry.py intent "next: X, because Y"` so a death leaves a forward-looking record. Optional: also add a `PostToolUse` hook running `bm_autosave.py tick` and set `BROTHERMODE_AUTOSAVE=1` for continuous autosave between compactions (costs a hook per tool call).
  If this hook fails: this is the one that can actually cost you something
  real. Your committed and already-saved files are never at risk either way;
  what a failed PreCompact hook costs is the EXTRA safety net: no snapshot of
  your uncommitted and untracked changes at the exact moment context gets
  compacted, and no resume brief telling the next session what you were in
  the middle of. That is recovery information, not telemetry, and it is not
  the same kind of loss: a missing telemetry line is a gap in a chart; a
  missing autosave snapshot or resume brief, hit at the wrong moment, can
  mean redoing work or re-explaining context you would otherwise have gotten
  back for free.

Every hook is built to fail silent and exit 0, so a broken hook never blocks
a session from continuing. But "never blocks" is not the same claim as "never
costs you anything": a broken `SessionEnd` costs a telemetry line; a broken
`PreCompact` can cost you recovery information at the one moment you needed
it most. Treat the two claims separately, because they are not the same
thing.

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

Expected on a fresh machine: 10 checks, mostly NO-DATA, and the closing line
"LLM judge scores only the residue." NO-DATA is correct for a system with no
history: the tools never invent numbers. You may also see one FAIL named
`budget-vs-tier` that points at `STATE.md`: this checks the skill repository's
OWN internal working file (the one its authors use to track building it), not
anything in your vault or your project, and a FAIL there does not mean your
install is broken. It is a real, checked-in inconsistency (that file's fence
lines are not all written in the single-line, tier-tagged format the checker
looks for), reported here rather than hidden.

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

## Sharing with a teammate

Working mostly alone but need to hand a project to someone occasionally? `python3 tools/bm_telemetry.py handoff <project>` assembles one shareable markdown (overview, open items, latest session, recent outcomes) from your vault, secret-redacted, so you can send context without sending your whole vault. Review it before sharing; redaction is best-effort.

## Uninstall

Remove the four hook entries from `~/.claude/settings.json` and delete
`~/.claude/skills/brothermode`. That removes the skill, but not what it wrote
inside each project you used it in: a per-project sqlite store, thread
files, `STATE.md` and its backups, local autosave git refs, and three lines
in `.git/info/exclude`. `../README.md`'s Uninstall section lists exactly
what is left and the commands to remove it, measured 2026-07-26 by actually
doing it in a scratch project. Your vault is yours either way; nothing
inside this repository ever writes to it except the files it holds.
