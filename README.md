# BrotherMode

## What this is

BrotherMode is a Claude Code skill: a written set of working rules (`SKILL.md`)
plus a small toolchain of Python and shell scripts, that you install once and
that then shapes how an AI coding session behaves every time you invoke it.
Instead of a model that waits for instructions and reports whatever sounds
good, it is asked to behave like a colleague: map the situation before
touching anything, say what it is doing and why in plain language, keep a
written record of decisions and in-progress work so a crash or a restart does
not lose the thread, and report bad news as soon as it is known rather than
burying it in a summary. A machine-run hook, not the model itself, records
what actually happened in each session (tokens spent, tools used, time taken),
because a model reporting on its own performance is not evidence.

## Who it is for

A solo founder or an individual doing the work of several roles at once, using
Claude Code as a working partner. It is built to scale down to one person on
purpose, not up to a team or an organization: there is no shared server, no
account system, and no multi-user coordination layer. If you are working with
a small team, the project supports occasionally handing a project to a
teammate (`bm_telemetry.py handoff`), but running this as a control plane for
several people at once is not what it is for.

## What it actually does for you

- Gives every session a starting posture: map what is already true (git
  status, what else is mid-flight) before writing anything.
- Keeps one writer per file at a time. Before any part of a session starts
  writing to a set of files, that claim is written down first, so two
  parallel efforts cannot silently overwrite each other's work.
- Writes a resumable record of decisions and open work to a plain folder on
  your disk (the vault), so a session that gets killed, or a context
  compaction, can pick up from a file instead of from a memory that is gone.
- Records real numbers about what a session cost (tokens, tool calls, time)
  through a mechanical hook rather than through the model's own account of
  itself, so a weekly review has something honest to look at.
- Asks the model to say when it disagrees with you, using your own stated
  values as the standard, before it goes along with a call it has reason to
  think is wrong.
- Snapshots your working tree to a private local git reference right before
  Claude Code compacts its context (the point where a session tends to lose
  track of what it was doing), so unsaved and untracked work has a recovery
  path.

## Quick start

The full, copy-pasteable, ten-minute path, with the expected output of every
command, is [`docs/QUICKSTART.md`](docs/QUICKSTART.md). The short version:

```bash
git clone https://github.com/khalilmaaouni/BrotherModeUp.git ~/.claude/skills/brothermode
```

Then follow `docs/QUICKSTART.md` (or the longer reference, `docs/SETUP.md`) to
run the tests, wire the four hooks, and point a vault folder somewhere on your
disk. Invoke with `/brothermode` at the start of a sizable task.

## Status: read this before trusting anything above

This project is under active rebuild (a "V2" rewrite of its storage engine),
and the honest state of that rebuild matters more than anything else on this
page. The full, current list is
[`docs/KNOWN-LIMITS.md`](docs/KNOWN-LIMITS.md); the points that matter most:

- **The new V2 storage engine is now wired into the tools you run (Phase 3,
  landed 2026-07-26), and the old registry is deleted.** `tools/bm_store.py`
  is imported by `tools/bm_autosave.py`, `tools/bm_sessionstart.sh`,
  `tools/bm_telemetry.py`, and `tools/bm_threads.py`: 43 references across
  those four production files, measured the same day with `grep -rn
  "bm_store" tools/*.py tools/*.sh | grep -v "bm_store.py:" | grep -v
  "test_bm_store.py:"` (61 lines if you count the two test files too).
  `bm_registry.py` no longer exists in this repository. If your copy still
  shows the old "not wired in" wording or still has `bm_registry.py`, you
  have an older clone; re-run the command above rather than trust either
  version of this paragraph.
- **The rewiring surfaced five real defects on 2026-07-26; four are fixed as
  of this page's last check, one is not.** All five are written up in
  `docs/superpowers/specs/2026-07-26-release-blockers.md`. Re-verified by
  direct execution, same day, after the fixes landed: a recovered autosave
  snapshot now comes back owner-only (`drwx------`) on POSIX (on Windows the
  mode call is best-effort and the guarantee is your user profile's access
  control, not ours), turning thread mode off
  and resuming a thread later from a different session now succeeds instead
  of being wrongly refused, `verify` no longer reports a false problem after
  a thread command, and both CLIs now reject an unrecognized flag instead of
  silently ignoring it. **Still open, confirmed by direct execution just
  now:** a refused adoption attempt (one session tries to adopt another's
  live, active thread without the explicit override, and is correctly
  told no) still permanently writes an "Adopted from dead/stalled thread"
  handover into `STATE.md` anyway, which is misleading regardless of the
  refusal. Code changes on this project's own timeline, sometimes within
  the same hour; re-run the reproduction steps in the spec above rather
  than trust either this paragraph or the spec's own dates once more time
  has passed.
- **This has not been used on a real project yet.** Everything behind the
  claims in this repository rests on its own test suites and adversarial
  review, not on a week of someone's actual work going through it.
  Continuous integration runs on three platforms and is GREEN as of
  2026-07-27 (commit `ba4eca2`, all eight jobs, both Windows legs included).
  Getting there is worth one line of history: an earlier version of this
  README claimed CI had never executed, which was false and unchecked; it had
  run 18 times, and the run against the first tagged release FAILED on Windows
  for a real handle leak. See `docs/KNOWN-LIMITS.md` for the arc and for what
  is now guarded mechanically.
- **A founder-approved correction memory now exists (`tools/bm_learn.py`).**
  You can capture a correction, approve it into a rule, retrieve which rules
  apply to a piece of work with the reason shown, and grade whether a rule
  actually prevented rework or a defect. Approval is founder-only, always: no
  part of this system, automatic capture included, can approve its own
  candidate. Plain-language walkthrough with real command output:
  [`docs/CORRECTION-LEARNING.md`](docs/CORRECTION-LEARNING.md). The single
  most important honest gap: **it has never run on a real day of your work
  yet, only on tests and scripted probes.** That is the highest-harm open item
  in `docs/NOT-FINALIZED.md` (item 1) and stays open until a real dogfood
  window closes it.

Do not read anything in this README as implying otherwise. If a claim below
and a claim in `KNOWN-LIMITS.md` seem to disagree, the limits file is the one
to believe.

## Verify the safety claims yourself

This project claims it makes no network calls and keeps your data on your own
disk. Do not take that on faith; it is checkable in under a minute:

```bash
cd ~/.claude/skills/brothermode
grep -rnE "urllib|requests|socket|http|curl|wget" tools/*.py tools/*.sh | grep -v "^tools/test_"
```

Expected: no output. (The `test_` files are excluded because they deliberately
contain these words in fixture data and in the test that checks the OTHER
files never do; run the grep without that filter and you will see exactly
that test data, not a real network call. The one thing that does shell out at
all is the autosave mechanism, and it only ever calls local `git`, never a
network command; `grep -rn subprocess tools/*.py tools/*.sh | grep -v test_`
shows exactly where.)

To check the tools do what they claim mechanically (secret redaction,
owner-only file permissions on POSIX, no silent overwrite between two
writers), run
the test suites yourself rather than trusting this page:

```bash
python3 tools/test_bm.py         # the tools that actually run today
python3 tools/test_bm_store.py   # the store engine underneath them (see Status)
```

Measured 2026-07-29, after the correction-learning loops landed: the first
prints `Ran 144 tests` and ends `OK (skipped=2)` (one skip is a check for a
shell-script autosave version this project no longer ships, the other is a
file-permission test this sandbox does not support); the second prints
`Ran 371 tests` and ends `OK`. If your numbers differ, treat that as a real
signal something changed, not a typo on this page; re-measure rather than
assume the page is stale. These two commands are a fraction of the full gate;
`python3 tools/test_all.py` runs all four suites (`test_bm.py`,
`test_bm_store.py`, `test_bm_autosave.py`, `test_bm_fence_hook.py`) serially
with one exit code and is the command this project actually gates on.

## Uninstall

Two different things get removed: the skill itself, and whatever it wrote
inside each project you used it in. Doing only the first leaves real files,
including the one file `SECURITY.md` calls sensitive, behind.

**The skill:**

```bash
rm -rf ~/.claude/skills/brothermode
```

Then remove the four hook entries you added to `~/.claude/settings.json`
(`docs/SETUP.md` lists them).

**Per project.** Measured 2026-07-26 by actually installing, using, and then
removing this skill in a scratch project: for every project where you ran
it, it leaves behind

- `.brothermode/store.sqlite3` (plus `-wal` and `-shm` sidecar files while a
  session is open). This is the file `SECURITY.md` calls the raw sensitive
  artifact: your objectives, decisions, and directives as you typed them,
  before redaction.
- `threads/`, including `threads/thread-mode.json` and a
  `threads/<name>-<id>/` folder (`STATE.md`, `inbox.md`, `outbox.md`,
  `digest.md`) for every thread you ever started, completed or not.
- `STATE.md` at your project root, plus one `STATE.md.bak-<timestamp>` file
  for every time it was regenerated (it is backed up before every rewrite,
  by design, so these accumulate).
- Local git refs under `refs/brothermode/autosave/...`, written by the
  PreCompact hook. These live inside `.git` and are not touched by deleting
  any of the files above.
- Three lines in that project's `.git/info/exclude` (`.brothermode/`,
  `threads/`, `STATE.md`), added by `bm_store.py init` so none of the above
  is committed by accident. Harmless to leave, but they are this project's
  lines, not git's own.

To remove all of it, run this from the project root (run `git status` first
if you want to see what is there before it goes; none of this touches your
own tracked files):

```bash
git for-each-ref --format='%(refname)' refs/brothermode | \
  while read -r ref; do git update-ref -d "$ref"; done
rm -rf .brothermode threads STATE.md STATE.md.bak-*
grep -vxE '\.brothermode/|threads/|STATE\.md' .git/info/exclude \
  > .git/info/exclude.tmp && mv .git/info/exclude.tmp .git/info/exclude
```

Verified 2026-07-26 in a scratch project: after those three commands plus
deleting the skill folder, `git status` reports a clean working tree with no
BrotherMode trace, and `git for-each-ref` shows no `refs/brothermode/*`
entries left.

Your vault (default `~/BrotherModeVault`) is a separate, ordinary folder:
none of the above touches it, and it is yours to keep or delete on its own,
per project or entirely.

## What is in the box

| File | What it does |
|---|---|
| `SKILL.md` | The law: numbered sections covering classification, delegation, fences, budgets, research, honesty, memory, scoring |
| `DIGEST.md` | A short compression of the law, injected at every session start so the rules survive context loss |
| `RUBRIC.md` | A template for the metrics a weekly review scores against |
| `STATE.template.md` | The running state file format: fences, decisions, the never-forget list |
| `tools/bm_telemetry.py` | The mechanical half of the learning loop: session telemetry, corrections capture, scorecard, nags |
| `tools/bm_score.py` | Code-graded weekly checks, so an LLM judge only scores what code cannot decide |
| `tools/bm_sessionstart.sh` | Session-start hook: injects the digest, overdue-review nags, and a recovery pointer after a compaction |
| `tools/bm_autosave.py` | On the PreCompact hook, snapshots your whole working tree (untracked files included) to a private local git reference. Never pushes. `recover` restores it |
| `tools/bm_threads.py` | Thread mode (opt-in): one persistent thread per key feature, plus a dashboard. Reversible mid-project |
| `tools/test_bm.py` | Regression tests for the tools that run today. Standard library only. Run `python3 tools/test_bm.py` |
| `tools/bm_store.py`, `tools/test_bm_store.py` | The V2 storage engine and its tests. Wired into the tools above since Phase 3 (2026-07-26); see Status for the defects that wiring surfaced |
| `tools/bm_learn.py` | The founder-facing correction-learning CLI: capture, approve, retrieve, grade. No direct database access, no automatic approval |
| `tools/bm_learning.py` | Pure helper functions the CLI and store share: normalization, hashing, ranking. No database, clock, or file access |
| `tools/test_all.py` | Runs all four test suites serially with one exit code. The actual gate; read this before running any single suite by hand |
| `tools/WEEKLY-REVIEW.md` | The weekly self-review procedure |
| `docs/QUICKSTART.md` | The literal ten-minute path, with expected output at every step |
| `docs/SETUP.md` | The fuller installation and hooks reference |
| `docs/HOW-IT-WORKS.md` | The mechanics of the tools that run today, explained exactly |
| `docs/CORRECTION-LEARNING.md` | The correction-learning system in plain language, with real command output and honest limits |
| `docs/KNOWN-LIMITS.md` | What is not proven yet. Read this before the rest |
| `docs/NOT-FINALIZED.md` | The numbered defect and limits register, status words defined at the top |
| `docs/BrotherMode-Design-Document.pdf` | The whitepaper: philosophy, the code, data flow and cost |
| `CHANGELOG.md` | What changed release to release, and the known limits of each addition |
| `vault-template/` | A ready-made memory vault folder: copy it and start working |

## What is deliberately not here

A distributed lock service, multi-machine coordination, or an
organization-wide governance layer. That is on purpose: those serve a
different kind of user than the one this project is built for, and adding
them would cost the simplicity that makes this useful for one person. Your
memory (session logs, findings, telemetry) lives in a vault folder outside
this repository, on your own disk, and this repository never commits to it;
you copy `vault-template/` once and what grows inside your copy stays yours.

## Requirements

- Claude Code (CLI or desktop app) with skills enabled
- Python 3, standard library only, no packages to install
- git

## License

MIT. Use it, fork it, rewrite the law to fit how you work. `RUBRIC.md` ships
as a template on purpose: measure your own baselines before freezing it.

Created by Khalil Maaouni.
