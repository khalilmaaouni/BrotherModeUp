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
[`docs/KNOWN-LIMITS.md`](docs/KNOWN-LIMITS.md); the two points that matter most:

- **The new V2 storage engine is built but not wired into anything you run.**
  `tools/bm_store.py` exists, has its own test suite
  (`tools/test_bm_store.py`), and has been through several rounds of
  adversarial review. But no other file in this project imports it or calls
  it (checked directly: `grep -rn "bm_store" tools/*.py tools/*.sh` outside
  of `bm_store.py` and its own test file returns nothing). The tools that
  actually run today when you use this skill, `bm_threads.py`,
  `bm_registry.py`, `bm_telemetry.py`, are the older ones, with the
  limitations `KNOWN-LIMITS.md` describes. Rewiring them onto the new engine
  is planned future work, not something already shipped.
- **This has not been used on a real project yet.** Everything behind the
  claims in this repository rests on its own test suites and adversarial
  review, not on a week of someone's actual work going through it.
  Continuous integration has never executed against this content (the
  workflow is configured; it has not run). Windows support is designed for,
  and one real defect was caught by simulating Windows path behavior on this
  machine, but no one has run it on an actual Windows machine.

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
owner-only file permissions, no silent overwrite between two writers), run
the test suites yourself rather than trusting this page:

```bash
python3 tools/test_bm.py         # the tools that actually run today
python3 tools/test_bm_store.py   # the new engine, not yet wired in (see Status)
```

The first takes several minutes on an ordinary machine (one test deliberately
runs hundreds of real subprocess calls to stress concurrent behavior); the
second takes roughly a minute. Both should end in `OK`.

## Uninstall

```bash
rm -rf ~/.claude/skills/brothermode
```

Then remove the four hook entries you added to `~/.claude/settings.json`
(`docs/SETUP.md` lists them). Your vault (default `~/BrotherModeVault`) is a
separate, ordinary folder: nothing above touches it, and it is yours to keep
or delete on its own.

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
| `tools/bm_store.py`, `tools/test_bm_store.py` | The new V2 storage engine and its tests. Built, not yet wired into any of the tools above; see Status |
| `tools/WEEKLY-REVIEW.md` | The weekly self-review procedure |
| `docs/QUICKSTART.md` | The literal ten-minute path, with expected output at every step |
| `docs/SETUP.md` | The fuller installation and hooks reference |
| `docs/HOW-IT-WORKS.md` | The mechanics of the tools that run today, explained exactly |
| `docs/KNOWN-LIMITS.md` | What is not proven yet. Read this before the rest |
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
