# Quick start

A literal, ten-minute path from nothing installed to seeing this thing do
something real. Every command below was run, as written, in a scratch copy of
this repository before this page was published. Where a step takes longer than
a few seconds, the real timing is stated so you know whether to wait or worry.

If a command's output does not match what is described here, stop and compare
carefully before continuing: a mismatch usually means a path is wrong, not that
something is broken.

## 1. Install the skill

```bash
git clone https://github.com/khalilmaaouni/BrotherModeUp.git ~/.claude/skills/brothermode
```

Expected: git prints a few lines ending in something like `Resolving deltas:
100% (N/N), done.` The path matters: Claude Code looks for skills under
`~/.claude/skills/`, and the scripts in this repo resolve their own location
from there, so the clone IS the installation. Verify it landed:

```bash
ls ~/.claude/skills/brothermode/SKILL.md
```

Expected: that exact path printed back. If you get "No such file or
directory", the clone did not finish or landed somewhere else.

## 2. Run the tests, to prove it works on your machine

```bash
cd ~/.claude/skills/brothermode
python3 tools/test_bm.py
```

Expected: `Ran 54 tests in <some number of seconds>` followed by `OK
(skipped=2)`. Measured 2026-07-26 on an ordinary laptop: about nine seconds,
not minutes. (An earlier version of this page said 124 tests, one skip, and
four to five minutes; that was true before this project's Phase 3 rewire
deleted the old registry module and its tests along with it, 2026-07-26. If
your run shows the old numbers, you have an older copy of this repository.)
The two skips are both environment-dependent, not failures: one is a check
for a shell-script autosave version this project no longer ships, the other
needs a filesystem that supports making a file read-only, which not every
sandbox does. If you see any line starting `FAIL` or `ERROR`, stop here:
something about your Python or platform does not match what this project
expects, and installing the rest is not worth doing until that is
understood.

## 3. Wire the hooks

This step makes the parts that must never be forgotten (telemetry, the
pre-compaction safety snapshot) run automatically instead of depending on the
model remembering to run them. One command does it:

```bash
python3 ~/.claude/skills/brothermode/scripts/install.py --dry-run
python3 ~/.claude/skills/brothermode/scripts/install.py
```

Run the `--dry-run` first. It prints every change and writes nothing, so you
see what is about to happen to your `settings.json` before it happens.

Expected from the real run: a list of five hooks (`SessionStart`, `SessionEnd`,
`Stop`, `PreCompact`, `PreToolUse`), a line naming the backup of your previous
settings, and a closing line reading `smoke: the fence hook ran end to end and
exited 0`. That last line is the point. The installer re-reads what it wrote
and actually executes the one hook that can refuse a write, so "installed"
means checked rather than attempted.

Five, not the four an earlier version of this page listed: `PreToolUse` is the
fence hook (`docs/HOOKS.md`), which was documented but was in no install
instruction, so the fence shipped off unless you wired it yourself.

What the installer will NOT do: overwrite an existing BrotherMode installation
(it refuses and tells you to pass `--upgrade`), rewrite a `settings.json` that
is not valid JSON (it refuses and points at the parse error rather than
throwing away what you were editing), or remove a hook of your own. An entry
counts as BrotherMode's only when every command in it names this
installation's own `tools/bm_*` files.

Check the result is valid JSON. The installer already did this and refuses to
report success otherwise, but run it once yourself so you know the command:

```bash
python3 -m json.tool ~/.claude/settings.json
```

Expected: the file prints back, reformatted, with no error.

To remove the wiring later:

```bash
python3 ~/.claude/skills/brothermode/scripts/uninstall.py
```

It removes only the entries it installed, leaves the files in place unless you
pass `--remove-files`, and never touches your vault.

### If you would rather wire it by hand

The installer writes the equivalent of the block below, plus the `PreToolUse`
fence entry from `docs/HOOKS.md`. Merge it into any hooks you already have. Use
the absolute path to your checkout rather than `~`: the installer writes
absolute, shell-quoted paths precisely because a home directory containing a
space breaks the unquoted form.

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

A `json.decoder.JSONDecodeError` from the check above means a comma or brace is
wrong; fix it before starting Claude Code, or Claude Code will simply ignore
the broken hooks block and every hook is off with nothing saying so. That
silent failure is the whole reason the installer exists. See `docs/SETUP.md`
for what each hook actually costs you when it fails.

## 4. Point the vault somewhere

The vault is a plain folder of markdown and JSONL files that holds this
project's memory: session logs, telemetry, and (if you use it) the founder
model. Nothing here talks to a server; it is just files on your disk.

```bash
cp -R ~/.claude/skills/brothermode/vault-template ~/BrotherModeVault
export BROTHERMODE_VAULT="$HOME/BrotherModeVault"
```

Add the `export` line to your shell profile (`~/.zshrc` or `~/.bashrc`) so it
survives a restart, or set it in the `env` block of `~/.claude/settings.json`
instead. Verify the copy landed:

```bash
ls ~/BrotherModeVault/Home.md
```

Expected: that path printed back.

## 5. Verify the installation

```bash
python3 ~/.claude/skills/brothermode/tools/bm_score.py
```

Expected on a fresh vault: ten checks, most saying `NO-DATA` (correct: you
have no history yet, and this tool refuses to invent one), a few saying
`PASS`, and a closing line reading `10 checks: N PASS, N FAIL, N NO-DATA. LLM
judge scores only the residue.` One check, `budget-vs-tier`, can show a `FAIL`
that names `STATE.md`: that specific failure is about THIS repository's own
internal working file (the one its authors use to build it), not about
anything you have done, and it does not affect the vault, the hooks, or your
project. Also run the session-start hook by hand once, to see what a new
session will actually be shown:

```bash
sh ~/.claude/skills/brothermode/tools/bm_sessionstart.sh
```

Expected: the digest text (about twelve lines summarizing the active laws),
followed by a line saying the weekly review has never run. That nag is a
to-do, not an error: you have not had a first week yet.

## 6. Invoke it once, on one real task

Open Claude Code in any project, and type:

```
/brothermode read this project's README and tell me the three biggest risks
```

Pick a real, small task like this one: it needs to read at least one file and
think for more than one turn, because the telemetry hook only records a
session that did some real work (fewer than 5 model turns or zero tool calls
and nothing is written, on purpose, so the ledger cannot be padded with
trivial sessions). Let the session run to a natural end.

## 7. See the evidence

```bash
tail -1 "$BROTHERMODE_VAULT/99-System/telemetry/outcomes.jsonl"
```

Expected: one line of JSON ending in the session's token counts, tool call
count, and model name, for example a `tool_calls` field of 1 or more and a
`models` field naming what you used. That line is written by the `SessionEnd`
hook, not by the model narrating that it happened, which is the whole point:
this is proof the mechanism ran, not a claim that it did. If the file does not
exist or the line is missing, the most common cause is a session too short to
clear the activity floor in step 6, or the hooks block from step 3 not having
been picked up (Claude Code reads hook configuration at startup, so a session
already running when you edited `settings.json` will not have it).

## What you have now

The five hooks running automatically, a vault of your own, and one proof that
the telemetry mechanism works end to end. What you do NOT yet have from this
alone: a history (that takes real weeks of use), a felt-outcome rating trend,
or a weekly review (`tools/WEEKLY-REVIEW.md`, run it once your first week of
real sessions has landed). Read `../README.md`'s status section and
`KNOWN-LIMITS.md` before deciding how much to lean on anything described here
as more proven than it is.
