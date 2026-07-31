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
command, is [`docs/QUICKSTART.md`](docs/QUICKSTART.md). The short version.
This clones an immutable, tagged release, not a moving branch: the code that
lands in `~/.claude/skills/brothermode` then runs automatically on every
future Claude Code session through five hooks, and a moving branch feeding
auto-run code was the weakest link the original external audit named.

```bash
git clone --branch v2.0.0-rc.9 --depth 1 https://github.com/khalilmaaouni/BrotherModeUp.git ~/.claude/skills/brothermode
```

That tag is not typed by hand: it is generated from the same release fact
every other page reads (`python3 tools/bm_project_facts.py --field
release_tag`), and `tools/test_bm_docs.py` fails if this page ever disagrees
with it.

Working on BrotherMode's own code, rather than just using it? Use the
separate development command instead, which tracks the moving `main` branch
on purpose and installs into its own directory so the two can never be
confused:

```bash
# Development branch (changes over time)
git clone --branch main https://github.com/khalilmaaouni/BrotherModeUp.git ~/.claude/skills/brothermode-dev
```

Then follow `docs/QUICKSTART.md` (or the longer reference, `docs/SETUP.md`) to
run the gate, wire the hooks (one installer command does it), and point a vault
folder somewhere on your disk. Invoke with `/brothermode` at the start of a
sizable task.

Which release this is, and how many hooks get wired, are not typed by hand on
this page. Both come out of the tree:

```bash
python3 tools/bm_project_facts.py
```

It prints the current version and release tag, the storage schema version, the
hook events the installer writes (`SessionStart`, `SessionEnd`, `Stop`,
`PreCompact`, and `PreToolUse`, which is the fence that can refuse a write), the
suite files the gate runs, and the Python floor. What it deliberately does not
print is a test count, for the reason given under "Verify the safety claims
yourself" below. This is a release CANDIDATE,
not a stable release; `docs/RELEASE.md` states what promoting it to a plain
`2.0.0` would require.

## Status: read this before trusting anything above

This project is under active rebuild (a "V2" rewrite of its storage engine),
and the honest state of that rebuild matters more than anything else on this
page. The full, current list is
[`docs/KNOWN-LIMITS.md`](docs/KNOWN-LIMITS.md); the points that matter most:

- **The new V2 storage engine is now wired into the tools you run (Phase 3,
  landed 2026-07-26), and the old registry is deleted.** `tools/bm_store.py`
  is imported by `tools/bm_autosave.py`, `tools/bm_sessionstart.sh`,
  `tools/bm_telemetry.py`, and `tools/bm_threads.py`, and by the newer tools
  that landed after them. The number of references is not quoted here, because
  it moves with every commit and a stale number teaches you to distrust the
  page rather than the tree. Measure it yourself:

  ```bash
  grep -rn "bm_store" tools/*.py tools/*.sh | grep -v "bm_store.py:" | grep -v "test_bm_store.py:"
  ```

  `bm_registry.py` no longer exists in this repository. If your copy still
  shows the old "not wired in" wording or still has `bm_registry.py`, you
  have an older clone; re-run the command above rather than trust either
  version of this paragraph.
- **The rewiring surfaced five real defects on 2026-07-26. All five are now
  closed.** They are written up in the dated, historical spec
  `docs/superpowers/specs/2026-07-26-release-blockers.md`, which opens with a
  DO NOT PUBLISH verdict that was true the day it was written and is not true
  now; it carries a HISTORICAL banner saying so. Their current
  status lives in `docs/NOT-FINALIZED.md`, which is the register to believe
  over this paragraph. Four were fixed on 2026-07-26 and re-verified by direct
  execution the same day: a recovered autosave snapshot comes back owner-only
  (`drwx------`) on POSIX (on Windows the mode call is best-effort and the
  guarantee is your user profile's access control, not ours), turning thread
  mode off and resuming a thread later from a different session succeeds
  instead of being wrongly refused, `verify` no longer reports a false problem
  after a thread command, and both CLIs reject an unrecognized flag instead of
  silently ignoring it. The fifth, the adopt defect (a refused adoption still
  writing an "Adopted from dead/stalled thread" handover into `STATE.md`), was
  closed on 2026-07-28: the refusal now happens before anything is written, and
  two tests hold that ordering in place. See `docs/NOT-FINALIZED.md` item 5 for
  the reproduction and the test names. Code changes on this project's own
  timeline, sometimes within the same hour; re-run the reproduction rather than
  trust a date.
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
  actually prevented rework or a defect. Approval is human-confirmed,
  one-time receipt-gated: no part of this system, automatic capture
  included, can approve or promote its own candidate. The receipt proves an
  answer was supplied for this exact proposed rule and has not already been
  used; it does not cryptographically prove which human supplied the
  answer. Plain-language walkthrough with real command output:
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
grep -rnE "^[[:space:]]*(import|from)[[:space:]]+(urllib|http|socket|requests|ftplib|smtplib|telnetlib|xmlrpc)\b" tools/*.py
```

Expected: no output. That is the check that matters, because a network call
needs an import, and `tools/test_bm.py` enforces exactly this ban on every
shipping module in `tools/` so it cannot regress quietly.

The broader keyword sweep is worth running too, as long as you read its output
rather than expecting silence:

```bash
grep -rnE "urllib|requests|socket|http|curl|wget" tools/*.py tools/*.sh | grep -v "^tools/test_"
```

Expected today: two lines, both in `tools/bm_fence_hook.py` (around lines 19 and
427), both comments citing the URL of the Claude Code hooks documentation that
the hook implements. A documentation URL inside a comment is not a call, and
pretending the sweep comes back empty would have been the easier sentence to
write and a false one. The `test_` files are excluded because they deliberately
contain these words in fixture data and in the test that enforces the ban above.
The one thing that shells out at all is the autosave mechanism, and it only ever
calls local `git`, never a network command; `grep -rn subprocess tools/*.py
tools/*.sh | grep -v test_` shows exactly where.

To check the tools do what they claim mechanically (secret redaction,
owner-only file permissions on POSIX, no silent overwrite between two writers),
run the gate yourself rather than trusting this page:

```bash
python3 tools/test_all.py
```

Expect it to end `ALL GREEN` and exit 0. It runs every suite serially, in its
own process each, and is the command this project actually gates on. It takes
several minutes; that is the real cost of the isolation, not a hang.

No test count is quoted on this page on purpose. Counts move with every test
that lands, and a reader who sees a mismatch cannot tell a stale README from a
broken install, which is exactly backwards. If you want the suite list rather
than the count, `python3 tools/bm_project_facts.py` prints it from
`tools/test_all.py` itself. Exact counts, tied to the date and commit they were
true of, live in `CHANGELOG.md` and in the dated evidence files under `docs/`.
Individual suites still run on their own (`python3 tools/test_bm_store.py` and
so on) when you are working on one of them; a single suite passing is not the
gate.

## Uninstall

Two different things get removed: the skill itself, and whatever it wrote
inside each project you used it in. Doing only the first leaves real files,
including the one file `SECURITY.md` calls sensitive, behind.

**The skill.** Unwire the hooks first, while the files are still there: the
installer's counterpart removes only the entries it wrote, and leaves your own
hooks and your vault alone.

```bash
python3 ~/.claude/skills/brothermode/scripts/uninstall.py
rm -rf ~/.claude/skills/brothermode
```

By hand instead, remove from `~/.claude/settings.json` every entry whose command
names this installation's own `tools/bm_*` files, across every hook event this
project wires (`python3 tools/bm_project_facts.py --field hook_events` lists
them; `docs/SETUP.md` explains what each one does).

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
| `tools/bm_fence_hook.py` | The PreToolUse fence: the one hook that can REFUSE a write to a file another live session owns. Explained in `docs/HOOKS.md` |
| `tools/bm_store.py`, `tools/test_bm_store.py` | The V2 storage engine and its tests. Wired into the tools above since Phase 3 (2026-07-26); see Status for the defects that wiring surfaced |
| `tools/bm_learn.py` | The founder-facing correction-learning CLI: capture, approve, retrieve, grade. No direct database access, no automatic approval |
| `tools/bm_packs.py` | Gate deep-dive packs: on demand, writes one markdown document per decision under `Documentation/30-decisions/`, with the code quoted live from disk, the callers and tests found by search, the rollback, and the review slots. A citation that no longer resolves fails the build rather than quoting stale code |
| `tools/bm_learning.py` | Pure helper functions the CLI and store share: normalization, hashing, ranking. No database, clock, or file access |
| `tools/bm_project_facts.py` | Prints the facts documentation is allowed to state (version, release tag, schema version, hook events, suite list, Python floor), read out of the tree rather than typed into a page |
| `tools/bm_runtimes.py` | Generates the instruction file that wires BrotherMode into another AI coding runtime (Codex CLI, GitHub Copilot, Google Antigravity, Qwen Code, iFlow CLI, or a generic AGENTS.md). Each generated file carries the vendor URL its convention was read from and the date it was read |
| `tools/test_bm.py`, `tools/test_bm_autosave.py`, `tools/test_bm_fence_hook.py`, `tools/test_install.py`, `tools/test_bm_runtimes.py`, `tools/test_bm_docs.py` | The other regression suites: the running tools, the autosave and its recovery, the fence hook, the installer, the runtime adapters, and the documentation facts. Standard library only |
| `tools/test_all.py` | Runs every suite serially, one process each, with one exit code. The actual gate; read this before running any single suite by hand |
| `tools/WEEKLY-REVIEW.md` | The weekly self-review procedure |
| `scripts/install.py`, `scripts/uninstall.py` | Wire and unwire the hooks in `~/.claude/settings.json`, backing it up first, touching no hook entry they did not write |
| `scripts/doctor.py` | Proves the wired fence is LIVE: builds a throwaway project, has one session claim a file, then checks the hook refuses a foreign write and allows the owner's own |
| `docs/QUICKSTART.md` | The literal ten-minute path, with expected output at every step |
| `docs/SETUP.md` | The fuller installation and hooks reference |
| `docs/HOOKS.md` | What each hook receives, what the fence can refuse, and the exact contract it implements |
| `docs/RELEASE.md` | The release discipline: tags, checksums, and the steps a machine must refuse to take on its own |
| `docs/HOW-IT-WORKS.md` | The mechanics of the tools that run today, explained exactly |
| `docs/RUNTIMES.md`, `docs/runtimes/` | Running BrotherMode in other AI coding runtimes: the capability table (which runtime has hook points, and where BrotherMode's own hooks are verified) and the generated adapter files. Both regenerated by `tools/bm_runtimes.py` |
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
