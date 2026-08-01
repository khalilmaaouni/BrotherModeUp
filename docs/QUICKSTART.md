# Quick start

Two ways in. Path 1 is the simple one: two commands typed inside Claude Code,
nothing else. Path 2 is the step-by-step one, written for technical users, and
it is the path every command of which has been run and checked before
publication. Pick one; do not do both.

## Path 1: install as a plugin (the simple way)

Honesty label, read this first: this install path has been installed exactly
once: on the author's machine on 2026-07-31, from a local copy of this
repository rather than from GitHub, with the full add, install, verify,
uninstall cycle recorded in docs/evidence/2026-07-31-first-plugin-install.md
(all seven skills and five hooks registered). Nobody has installed it from
GitHub or on any other machine yet. It
also ships more than new packaging: the guided beginner layer (the six
/brotherme commands and the guided skill) is new in this release and is
designed to load through this path; on this project's own machine a clone
carrying the plugin manifest also registered it in a live session, a single
observation and not a verified path. If anything in this path fails or looks
wrong, copy
the error into Claude Code and ask for help in plain words, or hand Path 2
below to someone technical; that path is checked command by command.

No file editing of any kind happens on this path. You will not touch
`settings.json`, you will not edit JSON, and you will not run Python by hand.
The plugin brings its own automatic wiring with it.

Open Claude Code and type these two commands, one at a time:

```
/plugin marketplace add khalilmaaouni/BrotherModeUp
```

```
/plugin install brotherme
```

If Claude Code asks which marketplace to install from, pick the one you just
added. Restart Claude Code if it tells you to. Then type:

```
/brotherme-help
```

That command explains what you have and what to do next in plain language.
When you are ready to try it on something real, type `/brotherme-start` and
describe what you want in your own words; it will guide you from there, one
decision at a time. The first time you start a project it asks where your
private project memory should live before writing anything there; if that
question is ever skipped, the automatic session records fall back to a folder
called `BrotherModeVault` in your home folder, and you can ask to move it.

To remove it later: `/plugin uninstall brotherme`.

To update later: type `/brotherme-update` and it walks you through it, or run
the two lines it wraps yourself: `/plugin marketplace update
brotherme-marketplace`, then `/plugin update brotherme`, then restart Claude
Code. That is the whole path. The rest of this page is Path 2 and applies only
if you skipped Path 1.

## Path 2: install by git clone (the verified way)

A literal, ten-minute path from nothing installed to seeing this thing do
something real. Every command below was run, as written, in a scratch copy of
this repository before this page was published. Where a step takes longer than
a few seconds, the real timing is stated so you know whether to wait or worry.

If a command's output does not match what is described here, stop and compare
carefully before continuing: a mismatch usually means a path is wrong, not that
something is broken.

## 1. Install the skill

The public default clones an immutable, tagged release, not a moving branch:
the tag is generated from the same release fact every other page reads
(`python3 tools/bm_project_facts.py --field install_target_tag`), the last
tag actually cut and known to resolve, never typed by hand, and
`tools/test_bm_docs.py` fails this page if it ever disagrees. The
development tree itself currently reads `2.0.0-rc.12.dev1`, a development
identity rather than a tagged release; `docs/RELEASE.md` explains why.

```bash
git clone --branch v2.0.0-rc.9 --depth 1 https://github.com/khalilmaaouni/BrotherModeUp.git ~/.claude/skills/brothermode
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

Working on BrotherMode's own code instead of just using it? Use the separate
development command, which tracks the moving `main` branch on purpose and
installs into its own directory so the two can never be confused:

```bash
# Development branch (changes over time)
git clone --branch main https://github.com/khalilmaaouni/BrotherModeUp.git ~/.claude/skills/brothermode-dev
```

## 2. Run the gate, to prove it works on your machine

```bash
cd ~/.claude/skills/brothermode
python3 tools/test_all.py
```

Expected: a line per suite, then a closing line reading `ALL GREEN`, and exit
code 0. Run it and expect ALL GREEN; that verdict is the check, not any
particular number of tests. It runs each suite in its own process, one at a
time, which is why it takes several minutes rather than seconds. That is the
cost of the isolation, not a hang.

A couple of skips are normal and are not failures: one is a check for a
shell-script autosave version this project no longer ships, the other needs a
filesystem that supports making a file read-only, which not every sandbox does.
A skip is reported as a skip; the gate still ends ALL GREEN.

No test count appears on this page on purpose. Counts move every time a test
lands, so a page that pins one teaches you to distrust the page instead of the
tree. If you want to know what the gate covers, `python3
tools/bm_project_facts.py` prints the suite list straight out of
`tools/test_all.py`. Dated counts, tied to the commit they were true of, live in
`../CHANGELOG.md`.

If you see any line starting `FAIL` or `ERROR`, or a closing line that is not
`ALL GREEN`, stop here: something about your Python or platform does not match
what this project expects, and installing the rest is not worth doing until that
is understood.

A single suite still runs on its own, and that is worth knowing while you are
working on one of them:

```bash
python3 tools/test_bm.py
```

One suite passing is not the gate, though. Run them one at a time if you run
them by hand: the suites rename a module aside mid-run, so two at once can
corrupt each other (`docs/NOT-FINALIZED.md` item 10), which is exactly why
`test_all.py` is serial.

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

Then prove the fence is not just wired but LIVE:

```bash
python3 ~/.claude/skills/brothermode/scripts/doctor.py
```

Expected: `OK: the wired hook denied a foreign write and allowed the owner's
own write`, followed by three lines saying what that did not prove. Doctor
builds a throwaway project in a temporary directory, claims one file under one
session, then asks the hook you actually wired to approve an edit of that file
from a different session. A healthy fence refuses. It then asks again as the
owner, because a hook that denies everything would pass the first half and
would be a brick rather than a fence. Nothing outside the temporary directory
is touched, and it is deleted when doctor exits.

Exit code 1 means the fence is not enforcing, and the output names which way it
is dead: no `PreToolUse` entry at all, an entry pointing at a file that is not
there, a matcher that leaves some write tools ungated, or a hook that runs and
refuses nothing.

To remove the wiring later:

```bash
python3 ~/.claude/skills/brothermode/scripts/uninstall.py
```

It removes only the entries it installed, leaves the files in place unless you
pass `--remove-files`, and never touches your vault.

### If you would rather wire it by hand

The installer writes the equivalent of the block below. All five entries are
here, fence included: an earlier version of this page stopped at four, which
meant anyone wiring by hand ended up with the one-writer-per-file promise
switched off and nothing saying so. Merge it into any hooks you already have.
Use the absolute path to your checkout rather than `~`: the installer writes
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
    ],
    "PreToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit|NotebookEdit",
        "hooks": [ { "type": "command", "command": "python3 ~/.claude/skills/brothermode/tools/bm_fence_hook.py", "timeout": 10 } ]
      }
    ]
  }
}
```

The `matcher` on that last entry is the list of write tools the fence gates. Drop
a tool from it and writes through that tool are ungated, which is one of the
failure modes `scripts/doctor.py` looks for.

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
