# DRAFT, not posted

**Status: DRAFT. Nobody has posted this. The founder posts it, or does not.**
Nothing in this repository may submit it, and no agent should treat this file
as permission to publish anything anywhere.

Every claim below is bounded by the approved positioning in
`docs/BrotherMode_V2_Post_Audit_Execution_Loops.md` and by the do-not-claim
list reproduced at the bottom of this file. If a line here is stronger than
the evidence, the line is wrong, not the evidence.

---

## Title (80 char limit on HN)

```
Show HN: BrotherMode, a local operating system for solo founders using AI
```

Alternates, same claim strength:

```
Show HN: Make AI work recoverable and accountable, on your own disk
Show HN: One writer per file, founder-approved rules, all local, no network
```

## Body

Hi HN. I am a solo founder, not an engineer by training, and I built this
because two things kept happening: the assistant lost work when its context
filled up, and I gave it the same correction over and over.

BrotherMode is a local system that tries to make AI work recoverable,
accountable, and able to retain founder-approved corrections with traceable
applications and outcomes. It is Python 3.9, standard library only. No network
calls, no API keys, no daemon, no Node, no Docker. One sqlite file inside your
project holds all of it, and deleting that file is the uninstall.

Three things it actually does:

**One writer per file.** Work is claimed as a record with a file fence. A
PreToolUse hook denies a second session's edit to a fenced file, and the denial
names the record, the owner, and the exact command to take the fence over on
purpose. The session identity is a token the process had to be able to open,
not a string it can claim, because the earlier version compared a public value
against itself.

**Corrections become rules only when you approve them.** Capture writes a
pending candidate. Approval is a command you run, with a reference recorded as
evidence. No hook, daemon, or automatic detector can promote anything, ever.
Retrieval then tells you which rules apply to a task and which words matched.
Retrieval is lexical word overlap and labels itself `mode=lexical` in its own
output: it is not semantic search and it does not claim to be.

**Outcomes are graded, separately from intent.** Whether a rule was retrieved,
whether it was followed, and whether the work still went wrong are three
different questions, kept separate. A rule that was shown and skipped grades as
a compliance failure; a rule that was followed into rework grades as a bad
rule. When a metric has no evidence behind it, the tool prints NOT MEASURED
rather than a zero that would read as a clean bill of health.

There is a public benchmark: thirteen scenarios ratified before the code was
written, published with inputs and expected outputs rather than a score, each
runnable on its own:

```
python3 scripts/benchmark.py
```

It builds a throwaway git repo per scenario and drives the real CLI. Writing
it found a real defect: a result limit could silence a safety rule. Scenario 3
is that defect, with the reproduction command in the doc.

### What I am not claiming

- It does not "never repeat mistakes". It can tell you why a correction
  repeated, which is a different and smaller claim.
- It does not improve itself. Every rule went through a human approval.
- No statistical learning. One person has twenty to forty rules. There is no
  dataset here and the project says so instead of building a validation split
  over eight cases.
- Not production ready beyond the tested user and platform scope. Every
  Windows claim comes from CI, never from a machine on my desk.
- The largest honest gap, and it is in the repo as open item 1: this has not
  run through a real working day yet. Everything green is a test suite, a
  benchmark, or a scripted probe. Only real use closes it, and no amount of
  further testing can.

Known limits: `docs/KNOWN-LIMITS.md`. Things built but not finished:
`docs/NOT-FINALIZED.md`. Five minute walkthrough: `docs/DEMO.md`.

I would especially like to be told where a claim here is stronger than what the
code actually does.

## Notes for the founder before posting

- Post as Show HN, weekday morning US Eastern. Be in the thread for the first
  two hours; a Show HN with an absent author dies.
- Have the repo link ready and public first. Check `docs/RELEASE.md`.
- When someone finds a defect, the honest answer is the repro command, not a
  defence.
- Do not upgrade any wording above without evidence to match. The list of
  claims this project forbids is in the plan and is repeated here:
  it never repeats mistakes; it autonomously improves itself; founder identity
  is cryptographically guaranteed; every shell write is mechanically fenced;
  Windows owner-only privacy; production readiness beyond the tested user and
  platform scope.
