# BrotherMode beta kit

For an outside founder who agreed to run this for a few weeks on real work.
Everything here was run, as written, before this page was published. Where a
claim is unproven, it says so instead of rounding up.

Recruiting beta users is not covered here. That is the project founder's job.
This page is what you hand someone once they have said yes.

---

## 1. What you are being asked to do

Use BrotherMode on your own real work for two to four weeks, then send back one
short report a week using the template in section 5.

You are not being asked to test features, file bug reports in a tracker, or be
nice about it. The single most useful thing you can send back is the week where
it got in your way.

## 2. What this is, in one paragraph

BrotherMode is a Claude Code skill plus a handful of Python scripts. It gives a
Claude session a memory that survives the session: what you corrected, what you
approved as a standing rule, who owns which files, and what actually happened
at the end of each session. It writes plain files (markdown, JSONL, one SQLite
database) into folders on your own disk. There is no account, no server, and no
sync.

What it is NOT: an agent that runs on its own, a model, or anything that
changes its own behaviour without you approving the change. Approval is a
command you type. Nothing promotes a correction into a rule on its own.

## 3. Before you start

- macOS or Linux. Windows is untested; if you are on Windows, say so and stop
  here rather than fighting it.
- Python 3.9 or newer (`python3 --version`). Standard library only, nothing to
  pip install.
- `git`.
- Claude Code, working, with at least one real project you use daily.

Reserve about an hour. Fifteen minutes of it is install; the rest is doing one
piece of your own real work with it switched on.

## 4. Your first hour

### 0 to 15 minutes: install

Follow `docs/QUICKSTART.md` end to end. It is the only install path, it is
literal, and every command in it was executed before publication. In outline it
is: clone into `~/.claude/skills/brothermode`, run the test suite to prove it
works on your machine, add four hooks to `~/.claude/settings.json`, copy the
vault template somewhere you own, and run the score tool once.

Do not skip the test-suite step. If it does not pass on your machine, nothing
after it is worth your time, and that failure is itself the most valuable thing
you could report back on day one.

### 15 to 40 minutes: one real task

Open Claude Code in a project you actually care about and start a normal
session with `/brothermode`. Pick real work, not a toy: something that needs
several files read and more than a couple of turns. Short sessions are
deliberately ignored by the telemetry, so a throwaway session will look like
nothing happened.

Work the way you normally would. Correct the model when it is wrong, out loud,
the way you already do.

### 40 to 50 minutes: capture one correction

First, once per project, create the database corrections are written to. The
install in `docs/QUICKSTART.md` is global and does not create one, and nothing
creates it for you on first use:

```bash
cd /path/to/your/project
python3 ~/.claude/skills/brothermode/tools/bm_store.py init
```

Expected: `bm_store: initialized /path/to/your/project/.brothermode/store.sqlite3
(root resolved via git)`. It also appends `.brothermode/` to that repo's
`.git/info/exclude`, so the database stays out of your commits without touching
a tracked `.gitignore`. Running it again on a project that already has a store
is harmless; the trailing parenthetical may read `(root resolved via marker)`
the second time, which is the same outcome reached a different way.

Skip this step and the next command refuses with `refused (no-store)` and an
exit code of 2. The refusal names this exact fix, so it costs you a minute, not
a session.

When you correct something and the correction would still be true next week,
record it:

```bash
python3 ~/.claude/skills/brothermode/tools/bm_learn.py capture \
  --raw "always run the tests before saying done" \
  --source explicit_correction
```

Expected: a line like `captured 9819e3fd (pending, nothing changes until you
approve it)`, sometimes followed by a warning that what you wrote looks like
more than one rule. Then look at it:

```bash
python3 ~/.claude/skills/brothermode/tools/bm_learn.py candidates
```

Expected: your candidate, marked `pending`, and a closing line telling you the
approve command. Pending means pending. Nothing in the system behaves
differently until you run `approve` yourself with a reason.

### 50 to 60 minutes: read the limits, then stop

Read `docs/KNOWN-LIMITS.md` before you form an opinion about what this thing
can do. It is the file to believe when it disagrees with anything else,
including this page.

## 5. What to expect in the first two weeks

Honest expectations, so a surprise reads as data rather than a defect:

- **Week one will feel like overhead.** You are feeding it corrections and
  getting nothing back yet, because there is no history to retrieve from. If it
  still feels like pure overhead in week three, that is the finding, and it is
  the one this beta most needs to hear.
- **Retrieval is lexical today.** No semantic search, no ranking model. It
  matches on words. Expect it to miss a rule you phrased differently the second
  time.
- **Most measurements will read NO-DATA at first.** The tools refuse to invent
  a history you do not have. That is the intended behaviour, not a broken
  install.
- **The score tool can show FAIL lines about this repository's own internal
  working files.** Those are about the project's own build, not your work.
- **Nothing is auto-approved, ever.** If you never run `approve`, no rules
  exist, and that is a legitimate way to run the whole beta.

## 6. Weekly feedback template

Copy this into a file, fill in what you actually know, and leave anything you
did not measure blank. Blank is a real answer here and is far more useful than
a guess. The counts come out of the tools; the judgements come out of you.

Two commands will fill in most of the numbers:

```bash
python3 ~/.claude/skills/brothermode/tools/bm_learn.py metrics
python3 ~/.claude/skills/brothermode/tools/bm_learn.py loop-failures
```

```text
BROTHERMODE BETA, WEEK [n], [dates]
Machine: [macOS or Linux, version]   Python: [python3 --version]

USAGE
  Substantial tasks run with it on:
  Retrieval runs:
  Applications recorded:
  Work records linked:
  Typical rules retrieved per task:

QUALITY
  Retrievals that were relevant:
  Retrievals that were irrelevant:
  Rules you knew existed but were never retrieved:
  Times the session gate failed to deliver:
  Times a rule was retrieved and then not followed:
  Rules that turned out to be bad rules:
  Rules applied outside the scope they were meant for:
  Cases you could not decide either way:

LEARNING
  Candidates captured automatically:
  Candidates you captured by hand:
  Candidates you approved:
  Candidates you rejected, and why (by reason):
  Duplicate candidates:
  Contradictions between rules:
  Corrections you had to repeat after they were already settled:

BURDEN
  Minutes spent reviewing candidates this week:
  Minutes spent closing applications this week:
  Tasks where it felt like unnecessary ceremony (count, and one example):
  Tasks where it prevented rework or context loss (count, and one example):
  Tasks where you used recovery:

RELIABILITY
  Hook failures:
  Times the store refused a write:
  Recovery failures:
  Install or upgrade problems:
  Anything platform-specific:

TWO SENTENCES
  The worst moment this week was:
  If it disappeared tomorrow, what I would actually miss is:
```

The five headings mirror the measurement categories in the project's own
dogfood plan (`docs/BrotherMode_V2_Post_Audit_Execution_Loops.md`, Loop 13), so
your report and the project's internal numbers can be read side by side.

## 7. Privacy: your data stays on your machine

The plain version: BrotherMode writes files into folders you chose, on your own
disk. It has no server to send anything to. Nobody on the project can see your
vault, your corrections, or your sessions. The only thing that reaches the
project is what you type into the weekly report above and choose to send.

Do not take that on faith. Check it yourself in under a minute:

```bash
cd ~/.claude/skills/brothermode
grep -rnE "import (urllib|socket|http|ftplib|smtplib|requests)" tools/*.py | grep -v "^tools/test_"
```

Expected: no output at all. There is no network client imported anywhere in the
shipping tools. (Run it without the `test_` filter and you will see the test
that enforces exactly this, plus its fixture data. Some files mention `https`
inside comments as documentation links; that is why this grep matches imports
rather than the bare word `http`.)

One tool does shell out, and only to local `git`: the autosave mechanism, which
commits a snapshot of your work into your own repository so a crash or a
compaction cannot lose it. It never invokes a network command:

```bash
grep -rn "subprocess" tools/*.py tools/*.sh | grep -v "^tools/test_"
```

Expected: hits in `tools/bm_autosave.py` only, plus comment lines in other
files explaining why they do not use it.

Where your data lives, so you can inspect or delete it:

- `$BROTHERMODE_VAULT` (wherever you copied the vault template): session logs,
  telemetry JSONL, and any founder-model notes. Plain text, readable in any
  editor.
- `<your project>/.brothermode/store.sqlite3`: ownership, corrections,
  candidates, and rules for that project. One file per project.

Deleting either folder deletes that data. There is no copy anywhere else.

Two things worth knowing rather than discovering:

- Your corrections are stored as you typed them. If you paste a secret into a
  correction, it lands on your disk in a file. The tools redact known secret
  shapes, and there is a test for it, but do not treat that as a guarantee.
- The autosave commits go into your own repository, on their own refs. If you
  push that repository somewhere, check what you are pushing first.

## 8. Sending the report back

Send the filled-in template however you and the project founder already talk.
Send the numbers even when they are unflattering, and send the week you barely
used it as a week you barely used it rather than skipping it. A skipped week
reads as data loss; an honest zero reads as a finding.
