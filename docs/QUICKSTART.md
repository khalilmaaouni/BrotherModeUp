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
model remembering to run them. Open `~/.claude/settings.json` (create it if it
does not exist) and add this `hooks` block, merging it into any hooks you
already have:

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

That is four hooks, not three (an earlier version of this project's docs said
three; see `docs/SETUP.md` for what each one actually costs you if it fails).
Check the file is valid JSON before you trust it:

```bash
python3 -m json.tool ~/.claude/settings.json
```

Expected: the file prints back, reformatted, with no error. A `json.decoder.
JSONDecodeError` means a comma or brace is wrong; fix it before starting
Claude Code, or Claude Code will simply ignore the broken hooks block.

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

The four hooks running automatically, a vault of your own, and one proof that
the telemetry mechanism works end to end. What you do NOT yet have from this
alone: a history (that takes real weeks of use), a felt-outcome rating trend,
or a weekly review (`tools/WEEKLY-REVIEW.md`, run it once your first week of
real sessions has landed). Read `../README.md`'s status section and
`KNOWN-LIMITS.md` before deciding how much to lean on anything described here
as more proven than it is.
