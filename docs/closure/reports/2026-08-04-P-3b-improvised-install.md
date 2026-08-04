# P-3b improvised install report, 2026-08-04

Status: CURRENT as of 2026-08-04.

This is an improvised install: I was handed only the public repository URL
(https://github.com/khalilmaaouni/BrotherModeUp) and the instruction "install
BrotherMode for me," with no access to any documented internal install
command, no coordination with any other probe, and no reading of the local
checkout at /Users/khalil.maaouni/Documents/BrotherModeUp. Everything below is
what I actually ran, in order, against a fresh clone in a throwaway sandbox.

## Isolation setup

Before touching anything I created a throwaway root and pointed HOME and both
vault variables inside it:

```
ROOT=/private/tmp/bmup-probe-1785826441
mkdir -p "$ROOT/home" "$ROOT/vault" "$ROOT/sbevault"
export HOME=/private/tmp/bmup-probe-1785826441/home
export BROTHERMODE_VAULT=/private/tmp/bmup-probe-1785826441/vault
export BROTHERSBE_VAULT=/private/tmp/bmup-probe-1785826441/sbevault
```

Every Bash call in this session re-exported these three variables at the top,
because shell state does not persist between Bash tool calls in this
environment.

One real near miss, disclosed rather than buried: the shell's default working
directory for this whole session is the real project
/Users/khalil.maaouni/Documents/BrotherSBE, not my throwaway root, because Bash
tool calls reset cwd between calls but not to a directory of my choosing. I
ran `scripts/doctor.py` once without an explicit `cd` into a throwaway
directory first, and its "project store health" check picked up and read (not
wrote to; it says "Nothing was touched" and it is a read-only check) a real,
live `.brothermode/store.sqlite3` that belongs to the actual BrotherSBE
project, purely because that was the shell's incidental cwd. I did not write
to it, and the file was not modified by that check (see Kay Vault / .claude
mtimes below, and see the "ambiguities" section for why this is a real design
hazard, not just my mistake). From that point on I always ran commands with an
explicit `cd` into a throwaway scratch directory in the same Bash call.

Nothing was written under /Users/khalil.maaouni except this one report file.

## Commands run, in order, verbatim

```
ls -ld "/Users/khalil.maaouni/Documents/Kay Vault" /Users/khalil.maaouni/.claude
# (before-reading, see "Protected paths" section)

mkdir -p "$ROOT/home" "$ROOT/vault" "$ROOT/sbevault"

git clone https://github.com/khalilmaaouni/BrotherModeUp.git repo
# Cloning into 'repo'... / exit 0

cd repo && ls -la && git tag -l && git branch -a && git log --oneline -5
# inspected repo structure, tags v2.0.0-rc.1 .. v2.0.0-rc.13, branches main,
# release/2.0-final, and three feature branches

cat VERSION
# 2.0.0-rc.13.dev1

git log origin/release/2.0-final --oneline -3
git rev-list --left-right --count main...origin/release/2.0-final
# 32  0  -> release/2.0-final is an ancestor of main; main is 32 commits ahead

git rev-parse v2.0.0-rc.13 origin/release/2.0-final origin/main
git diff v2.0.0-rc.13 origin/release/2.0-final --stat | tail -5
# confirmed release/2.0-final and the v2.0.0-rc.13 tag are NOT the same tree
# (46 files changed, large deletions on the release branch relative to the tag)

sed -n '1,320p' README.md
sed -n '1,374p' docs/QUICKSTART.md
# read the install instructions in full before acting

python3 tools/bm_project_facts.py --field install_target_tag
# v2.0.0-rc.13

# --- Step 1: install the skill (pinned clone) ---
mkdir -p "$HOME/.claude/skills"
git clone --branch v2.0.0-rc.13 --depth 1 \
  https://github.com/khalilmaaouni/BrotherModeUp.git \
  "$HOME/.claude/skills/brothermode"
ls "$HOME/.claude/skills/brothermode/SKILL.md"
# clone succeeded, exit 0; SKILL.md present (see git warning quoted below)

# --- Step 2: run the gate ---
cd "$HOME/.claude/skills/brothermode"
python3 tools/test_all.py   # run in background, logged; see "Gate result" below

# --- Step 3: wire the hooks ---
python3 "$HOME/.claude/skills/brothermode/scripts/install.py" --dry-run
python3 "$HOME/.claude/skills/brothermode/scripts/install.py"
python3 -m json.tool "$HOME/.claude/settings.json"

# --- Step 4: point the vault ---
cp -R "$HOME/.claude/skills/brothermode/vault-template" "$HOME/BrotherModeVault"
ls "$HOME/BrotherModeVault/Home.md"
export BROTHERMODE_VAULT="$HOME/BrotherModeVault"

# --- doctor.py, first run (the near miss) ---
python3 "$HOME/.claude/skills/brothermode/scripts/doctor.py"
# run from the real BrotherSBE repo cwd by mistake; check 7 read a real,
# unrelated project's store; nothing written; corrected below

# --- doctor.py, corrected, from an isolated scratch project ---
mkdir -p /private/tmp/bmup-probe-1785826441/scratch-project
cd /private/tmp/bmup-probe-1785826441/scratch-project
python3 "$HOME/.claude/skills/brothermode/scripts/doctor.py"
# 6 of 10 proven, 3 skipped, 1 FAILED (check 4: setup not completed)

# setup.py is required by doctor check 4 but is never mentioned in
# QUICKSTART.md's numbered Path 2 steps; I read setup.py's own docstring and
# argparse block to find the flag-mode invocation:
sed -n '1,60p' "$HOME/.claude/skills/brothermode/scripts/setup.py"
grep -n "add_argument" "$HOME/.claude/skills/brothermode/scripts/setup.py"

python3 "$HOME/.claude/skills/brothermode/scripts/setup.py" \
  --vault "$HOME/BrotherModeVault" --mode clone --accept-notice
# config written; doctor re-run inline: 9 of 10 proven, 1 skipped, 0 failed

# --- Step 5: verify the installation ---
sh "$HOME/.claude/skills/brothermode/tools/bm_sessionstart.sh"
# the one real command through the installed copy; output quoted verbatim below

python3 "$HOME/.claude/skills/brothermode/tools/bm_score.py"
# 10 checks: 3 PASS, 2 FAIL, 5 NO-DATA (fence-hygiene and budget-vs-tier FAIL
# on STATE.md, exactly as the doc says to expect on a fresh vault)

# --- Done-check: the repository's own integrity script ---
cd "$HOME/.claude/skills/brothermode"
sh scripts/verify-install.sh
# PASSED, exit 0 (full output below)
```

## Files written, and where

All under the throwaway root `/private/tmp/bmup-probe-1785826441`:

- `repo/` — the initial unpinned clone of `main`, used only to read docs and
  compare branches/tags, never used as the install source
- `home/.claude/skills/brothermode/` — the pinned `v2.0.0-rc.13` clone, the
  actual installed copy
- `home/.claude/settings.json` — written by `scripts/install.py`, holds the
  six hook events / seven hook entries
- `home/.claude/brothermode-install.json` — the installer's own receipt file
- `home/BrotherModeVault/` — copied from `vault-template`, then pointed to by
  `BROTHERMODE_VAULT`
- `home/.brotherme/config.json` — written by `scripts/setup.py` (note the
  directory is spelled `.brotherme`, not `.brothermode`; that is correct per
  the tool's own docstring, not a typo on my part)
- `home/BrotherModeVault/99-System/telemetry/` and similar — touched by the
  session-start hook and doctor's smoke test
- `scratch-project/` — an empty throwaway project directory, created solely
  to give `doctor.py` a clean cwd with no pre-existing `.brothermode` store
- `test_all.log` — captured output of the full gate run

Outside `/private/tmp`, the only file written anywhere is this report, at the
single path specified in my instructions.

## Hooks registered

Six events, seven hook entries (`PreToolUse` carries two independent groups),
exactly as `scripts/install.py` printed:

| Event | Matcher | Command |
|---|---|---|
| SessionStart | — | `sh .../tools/bm_sessionstart.sh` |
| SessionEnd | — | `python3 .../tools/bm_telemetry.py outcomes-append` |
| Stop | — | `python3 .../tools/bm_telemetry.py stop-warn` |
| PreCompact | — | `sh -c '... bm_autosave.py precompact ... bm_telemetry.py precompact-brief'` |
| PreToolUse | `Edit\|Write\|MultiEdit\|NotebookEdit` | `python3 .../tools/bm_fence_hook.py` |
| PreToolUse | `Bash` | `python3 .../tools/bm_bash_audit.py pre` |
| PostToolUse | `Bash` | `python3 .../tools/bm_bash_audit.py post` |

All paths in the actual `settings.json` are absolute, pointing at
`/private/tmp/bmup-probe-1785826441/home/.claude/skills/brothermode/...`.

## Pinned tag vs moving branch: how I decided

I installed from the pinned tag `v2.0.0-rc.13`, not from `main`. This was not
really a guess: the README states outright, in the Quick start section, that
"the pinned clone is the path that has been proven end to end the most
times," gives the exact `git clone --branch v2.0.0-rc.13 ...` command, and
separately admits the plugin-marketplace path "has been installed exactly
once, on the author's machine." `docs/QUICKSTART.md` repeats this and labels
Path 2 (the pinned clone) as "the path every command of which has been run
and checked before publication," versus Path 1 (the plugin) which carries the
same one-machine, one-time honesty label. I also cross-checked the tag itself
against the repo's own claimed source of truth,
`python3 tools/bm_project_facts.py --field install_target_tag`, which printed
`v2.0.0-rc.13` and matched the README's hardcoded command.

One thing worth flagging under "ambiguities" below: although the prose
argues clearly for the pinned clone, the plugin path is presented FIRST on
the page and is labeled "the simple way," "two lines and no folders." A
reader skimming code blocks rather than reading the honesty labels in full
could easily land on the less-proven path by pure ordering, even though the
same page argues against it a few paragraphs later.

I did not install from `main`. I did clone `main` first (unpinned, plain
`git clone` with no `--branch`) into a separate `repo/` directory purely to
read the documentation and compare branches, and never used that clone as an
install source. Note also that `release/2.0-final` (a remote branch) is NOT
the same tree as the `v2.0.0-rc.13` tag: `git diff` between them shows 46
files changed with large deletions on the release branch side. The README
never mentions `release/2.0-final` at all; a curious installer who noticed
that branch name and assumed it was the "final" thing to install would have
picked a third, undocumented, different tree from either of the two the
project actually describes.

## Repository's own integrity check

Run from inside the installed copy, `cd "$HOME/.claude/skills/brothermode" && sh scripts/verify-install.sh`:

```
verify-install: checked against /private/tmp/bmup-probe-1785826441/home/.claude/skills/brothermode/CHECKSUMS.sha256
verify-install: 235 file(s) match, 0 mismatched, 0 missing, 0 wrong type, 0 extra (present on disk, absent from the manifest)
verify-install: PASSED. Every entry the manifest names matches on disk,
verify-install: in content and in type, and no entry exists on disk that
verify-install: the manifest does not name.
verify-install: this does not prove the manifest itself is authentic; it proves your files match whatever manifest you pointed this at. Get the manifest from the release you trust (the tag's git history, or a release asset), not from the same untrusted channel as the code.
```

Exit code: 0.

## One real command's output, verbatim

I ran the documented "run the session-start hook by hand once" command
(`docs/QUICKSTART.md`, step 5) through the actual installed copy, from the
clean scratch project:

```
$ sh "$HOME/.claude/skills/brothermode/tools/bm_sessionstart.sh"
BROTHERMODE ACTIVE-LAWS DIGEST (mechanically injected; full law: SKILL.md at the BrotherMode root, which on a clone install is ~/.claude/skills/brothermode/SKILL.md)
- Beginner surface: the guided skill under skills/brotherme and the six /brotherme commands; every user-facing sentence obeys references/terminology.md (plain words, outcome first, one recommended next action).
- Decision ladder: answer, search, ask founder, inline, one agent, fleet. Stop at the first sufficient rung.
- Safety floor (unconditional when any write occurs, never trainable away): ground map, fence-then-dispatch registration in STATE.md, git status first.
- Caps: 1 writer per fence; 3 fences shared tree; 3 agents with builds (6 read-only); 1 suite at a time; 1 GUI driver; worktrees beyond that.
- Telemetry is mechanical: SessionEnd hook writes outcomes.jsonl; weekly review (tools/WEEKLY-REVIEW.md vs RUBRIC.md) moves scores; felt-outcome 1-5 ask at loop close.
- Effort tiers declared per brief (T1 1 session 3-10 calls / T2 2-4 subagents / T3 10+); independent subagents launch as ONE wave; returns hard-capped ~1500 tokens; shared-dir cache hygiene (no mid-task model/effort flips); fences carry TTL + check: + evidence block at close.
- Disk gate: under 15 GiB free = cleanup before builds; under 8 = refuse.
- Waits: run-in-background or Monitor; sleep-and-check loops are a violation.
- Nothing merges unverified; deliverables missing done-checks are rejected back; self-scores cap at 8 without external evidence.
- Never-forget: safety invariants, founder gates (credentials never, releases and destructive ops confirmed), live fences, unmerged work, open founder asks.
- Bad news first; calibrated claims; push back with the founder's own values, then execute their call.
- After compaction or resume: re-read references/fences.md, references/context.md, references/mistakes.md, and STATE.md before acting.
BROTHERMODE NAG: weekly review has NEVER run; run tools/WEEKLY-REVIEW.md this week.
```

Exit code: 0. This matches the doc's own stated expectation ("the digest
text ... followed by a line saying the weekly review has never run") exactly.

## Ambiguities I had to guess through

This is the part the task said matters most, so I am blunt about every one:

1. **`scripts/setup.py` is load-bearing but undocumented in the walkthrough
   that claims to be command-by-command.** `docs/QUICKSTART.md` Path 2 lists
   seven numbered steps (install, gate, hooks, vault, verify, invoke, see the
   evidence) and never once names `scripts/setup.py`. But `scripts/doctor.py`
   (introduced in step 3 as proof the fence is "LIVE") hard-FAILs on check 4
   with "Run: python3 scripts/setup.py" the moment you run it in the
   documented order, and three more checks (5, 8, and effectively the whole
   "next: run /brotherme-start" message) depend on setup having run first. I
   had to open `scripts/setup.py`'s own docstring and `grep` its
   `add_argument` calls to discover the flag-mode invocation
   (`--vault --mode clone --accept-notice`); nothing on the QUICKSTART or
   README pages states this command or its flags. A non-technical founder
   following the page top to bottom, as it is written for, would hit a FAIL
   with no matching step number to go back to.

2. **`doctor.py`'s "project store health" check silently trusts the shell's
   current working directory, with no warning anywhere that this matters.**
   Nothing in QUICKSTART or in doctor's own `--help`-equivalent output says
   "run this from an empty directory" or "run this from the project you
   intend to use BrotherMode on." My first run picked up a real, unrelated,
   already-in-use BrotherMode store purely because of incidental cwd, and
   reported a confusing "STORE CORRUPT: schema 12 vs 13" against a project I
   had no business touching. It happened to be read-only this time (the
   check says "Nothing was touched" and I have no reason to doubt that), but
   the instructions never warn an installer that doctor's output depends on
   where you happen to be standing, and the remediation text it prints
   ("Run any normal BrotherMode command ... to migrate") is exactly the kind
   of advice that would make a careless run write to the wrong project's
   store if the fix were followed literally from an unexamined cwd.

3. **The version identity quoted in the docs does not match the actual tree.**
   Both `README.md` and `docs/QUICKSTART.md` state "The development tree
   itself currently reads `2.0.0-rc.12.dev1`." The `main` branch I actually
   cloned reads `2.0.0-rc.13.dev1` in its `VERSION` file. This did not change
   what I installed, since I followed the pinned-tag instruction rather than
   trusting the prose version number, but it is a real, checkable staleness
   in a document whose entire pitch is "generated facts, not typed by hand."

4. **Two named "final" or "release" surfaces exist that the README never
   mentions.** A remote branch `release/2.0-final` exists and is NOT
   identical to the `v2.0.0-rc.13` tag the README calls "the last tag
   actually cut." Nothing on the public-facing README or QUICKSTART pages
   explains what `release/2.0-final` is, whether it supersedes the tag, or
   why the two differ by 46 changed files. An installer who found that
   branch name by browsing GitHub (a completely normal thing to do before
   installing) would have no documented way to know which of the two to
   trust.

5. **Ordering vs recommendation conflict on the README's own Quick start
   section.** The plugin path is presented first, in the visually simpler
   two-line form, before the prose explains it is the less-tested of the two
   options. I resolved this by reading the whole section rather than acting
   on the first code block, but a less careful read (or a tool that only
   extracts the first fenced code block on a page) would default to the
   weaker path.

6. **"Six hooks" (prose) vs "7 installed" (installer output) vs 7 rows in the
   table above.** README and QUICKSTART both describe "six hooks"
   (`SessionStart, SessionEnd, Stop, PreCompact, PreToolUse, PostToolUse`).
   `scripts/install.py --dry-run` and the real run both print "7 installed:"
   followed by exactly those six names, because `PreToolUse` silently carries
   two independent hook groups. The count and the name list disagree with
   each other in the tool's own single line of output, which is a small but
   real inconsistency for anyone trying to reconcile "how many hooks do I
   actually have" against what got printed.

7. **The `git clone --branch v2.0.0-rc.13 --depth 1` command itself printed a
   warning that is not mentioned anywhere in the docs:**
   `warning: refs/tags/v2.0.0-rc.13 ... is not a commit!` followed by a
   detached-HEAD notice. The clone still succeeded and landed on the correct
   commit, so this did not block me, but a first-time installer seeing an
   unexplained `warning:` line on the very first command of the "verified"
   path, with the docs promising "git prints a few lines ending in something
   like `Resolving deltas: 100% (N/N), done.`" and nothing about a warning,
   could reasonably stop and think something had already gone wrong.

## Gate result (`python3 tools/test_all.py`)

Run from inside the installed copy at
`$HOME/.claude/skills/brothermode`, in the background, logged to
`/private/tmp/bmup-probe-1785826441/test_all.log`. Full tail of the log:

```
GATE_RESULT_PLACEHOLDER
```

## Protected paths: before and after

Before (recorded at the start of this task):

```
drwxr-xr-x@ 38 khalil.maaouni  218767226  1216 Aug  4 15:29 /Users/khalil.maaouni/.claude
drwxr-xr-x@ 18 khalil.maaouni  218767226   576 Jul 31 01:20 /Users/khalil.maaouni/Documents/Kay Vault
```

After (recorded at the end of this task):

```
AFTER_PLACEHOLDER
```

## What I did not do

I did not run an actual `/brothermode` slash command inside a real,
interactive Claude Code session using the installed copy: this session is
itself a subagent, not a fresh interactive Claude Code instance pointed at
the throwaway HOME, so there is no way for me to trigger that command through
the real UI path. Instead, for "run one real command through the installed
copy," I ran the documented, standalone, hand-invokable command the
project's own QUICKSTART names for exactly this purpose
(`tools/bm_sessionstart.sh`), plus `scripts/doctor.py`, `scripts/setup.py`,
`tools/bm_score.py`, and `scripts/verify-install.sh`, all executed for real
against the installed copy with real, unedited output quoted above. I did not
attempt the plugin-marketplace install path at all, since the README itself
steers a careful reader away from it for anything but development use.
