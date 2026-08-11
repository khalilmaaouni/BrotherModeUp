# Tester pack: both tools, one sitting

Status: CURRENT. Written 2026-08-12 for the first cold testers.

You are the first people to install these on a machine that has never had
them. That is the whole point of this week: nobody has ever measured what the
first hour is actually like, so whatever happens to you is the finding,
including the parts that go badly. Write those down especially.

About ninety minutes end to end. You can stop after Part 2 and still have
given us something useful.

---

## What you are testing

Two tools that do different jobs and are versioned separately.

| Tool | Version | What it is for |
|---|---|---|
| BrotherMode | `v3.2.0` | one person's session: holds the goal, refuses to call work done without a check that actually ran |
| BrotherSBE | `v3.1.0` | one change's passage between people: design before verification, gates that block on evidence |

Write both numbers in your first daily note. If the numbers on your machine
differ from the ones above, that is a finding, and it is the first one to
report.

---

## Part 1: install, about fifteen minutes

You need Claude Code (CLI or desktop) with skills enabled, Python 3.9 or
newer, and git. There is nothing to `pip install`.

If you have ever installed either tool before, uninstall it first. The plugin
identity changed at v3.0.0, so an old copy and a new copy are two different
plugins to Claude Code, and having both wires two hook chains at once.

**BrotherMode:**

```bash
claude plugin marketplace add khalilmaaouni/BrotherModeUp@v3.2.0
```

```bash
claude plugin install brothermode@brothermode-marketplace
```

**BrotherSBE:**

```bash
claude plugin marketplace add khalilmaaouni/BrotherSBE@v3.1.0
```

```bash
claude plugin install brothersbe@brothersbe
```

The `@v3.2.0` and `@v3.1.0` matter. They pin each install to a released tag
instead of whatever happens to be on the default branch today. Two testers on
different commits cannot tell a bug from a version difference, and that has
cost this project real time before.

### The one trap that eats afternoons

There is no `brothermode` command in your terminal. Type it at a shell prompt
and you get "command not found", and that is correct rather than broken. That
tool only exists inside a Claude Code session, typed with a slash. Its sibling
is the opposite: `sbe` really is a terminal program, so `which sbe` should
return a path.

---

## Part 2: prove the install, about ten minutes

Do not skip this. An install that looks fine and is subtly wrong is the
failure mode that wastes the most time later.

**Check one, inside a Claude Code session**, type:

```
/brothermode:doctor
```

Eleven checks. On the maintainer's machine on 2026-08-12 the last lines read:

```
11 of 11 proven, 0 skipped, 0 failed.
All 11 checks passed (SKIP is not a failure unless --strict; see the reason printed next to it).
```

A SKIP is not a failure. A FAIL prints its own remediation right next to it,
so follow that rather than guessing. Copy the whole output into your report
either way, passing or failing.

**Check two, in your terminal**, from wherever the BrotherMode files landed:

```bash
bash scripts/verify-install.sh
```

Expected shape, with the file count possibly differing from ours:

```
verify-install: 853 file(s) match, 0 mismatched, 0 missing, 0 wrong type, 0 extra
verify-install: PASSED.
```

Read the sentence it prints after passing. It says this proves your files
match the manifest you pointed it at, not that the manifest is authentic. That
is an honest limit and we would rather you knew it than felt safer than you
are.

**Check three:**

```bash
which sbe
sbe --version
```

The version must say `3.1.0`. A stale copy from an older install can sit on
your PATH for months while a newer one exists, and it will be missing commands
the documentation says exist. This was found on a maintainer's own machine,
two major versions behind, which is why it is in the pack.

---

## Part 3: the three exercises, about forty minutes

Follow [FIRST-DAY.md](FIRST-DAY.md). Do it on a throwaway repository, never on
real work, because exercise two deliberately causes a conflict and you do not
want to cause one of those on something that matters.

The three, and what each is actually testing:

1. **One edit.** Does the tool refuse to say "done" on the strength of having
   made a change, and insist on a check that ran after the last edit?
2. **One conflict.** Two sessions want the same file. Does the second one get
   refused with a reason a human can act on, or does it quietly overwrite?
3. **One resume.** Kill a session mid-work and start a new one. Does the new
   one know what the old one was holding?

Passing all three is the exit test for this phase. Failing any of them is a
better result for us than passing all three, so do not smooth over a failure.

---

## Part 4: the BrotherSBE side, about fifteen minutes

Do not make it a required check on anything yet. Start at stage 0, shadow
mode, described in that project's `docs/ROLLOUT.md`: copy
`.github/workflows/brothersbe-gates.yml` into a repository you care about and
let it report on pull requests **without blocking a merge**.

Watch a sprint of real pull requests before anybody argues about turning it
on. Every gate in that project has been proven against its own fixtures, and
nothing in that proves it behaves the same way against a codebase it has never
seen. Yours is the second data point. Read every FAIL and every WAIVED design
check in the workflow's summary step and tell us the false positive rate you
saw, because that number decides whether it can ever be a blocking gate here.

Then run, in a repository you are willing to have inspected:

```bash
sbe adopt .
```

With no `--apply` it is a dry run: it prints every proposal as a diff and
writes nothing. Send us what it proposed. It cannot flip a GitHub branch
protection setting and it does not claim it can; that stays a click somebody
with admin rights makes.

---

## What to send back

Four things, in your team channel, however roughly written.

1. **The two version numbers your machine actually reports**, not the ones at
   the top of this page.
2. **How long Part 1 and Part 2 took you**, wall clock, including the time you
   spent stuck. This is the single most valuable number in the pack, because
   nobody has ever measured it and every schedule downstream currently rests
   on a guess.
3. **Every place you had to think.** Not just errors. If you paused to work
   out what a sentence meant, that sentence is broken and we want the sentence.
4. **Anything that failed**, with the command you ran and its output pasted
   verbatim. A screenshot of an error is worth much less than the text.

Then start a daily note from
[DAILY-NOTE-TEMPLATE.md](DAILY-NOTE-TEMPLATE.md): two minutes, four lines,
every day you used either tool. Blank days count and get written as blank
rather than skipped, because the weekly review reads the blanks too.

---

## What this pack does not claim

Stated here rather than left for you to discover.

- **Nobody has run these install commands on a machine without the tools
  already on it.** The tags were verified to exist and to match their remotes
  (`docs/evidence/tester-pack/CHECKED-2026-08-12.md`), and the local install
  was verified healthy. The `claude plugin` step itself is unproven on a cold
  machine, and you are the proof. If it fails, that is the most important
  thing that happens this week.
- **The three exercises were not run end to end for this pack.** Two of them
  need two live sessions and a real conflict, which one machine cannot fake.
- **Shadow mode has never run against a repository outside these two
  projects.** There is no client estate here to run it on.
- **The timings in this document are estimates, not measurements.** Ninety
  minutes is a guess made by people who already know where everything is,
  which is exactly the kind of guess this project has recently been wrong
  about by four to five times. Report the real number and we will replace the
  guess with it.
