# DRAFT, not posted

**Status: DRAFT. Nobody has posted this.** The founder posts it, or does not.
Nothing in this repository may submit it, and no agent should treat this file
as permission to publish anything anywhere.

Claim strength is bounded by the approved positioning in
`docs/BrotherMode_V2_Post_Audit_Execution_Loops.md`. The forbidden claims are
listed at the bottom. Do not upgrade a line without evidence to match it.

---

## Name

BrotherMode

## Tagline (60 characters)

```
Make AI work recoverable and accountable, on your disk
```

Alternates:

```
Founder-approved rules and one writer per file, all local
Local memory and safety rails for founders working with AI
```

## Description (260 characters)

```
A local operating system for solo founders working with AI. Corrections become
rules only when you approve them, work is fenced one writer per file, and
outcomes are graded with evidence. Python standard library, no network, one
sqlite file you can delete.
```

## First comment (the maker comment)

I am a solo founder, not an engineer. Two things kept happening: the assistant
lost work when its context ran out, and I gave it the same correction again and
again.

BrotherMode is my answer, and it is deliberately small. Python 3.9, standard
library only, no network calls, no API keys, no accounts, no daemon. One sqlite
file inside your project holds everything. Deleting the folder is the uninstall,
and a scenario in the public benchmark checks that claim mechanically.

What it does:

1. You correct the assistant. That correction becomes a PENDING candidate.
2. It becomes a rule only when you approve it, by hand, with a reason recorded.
   No automatic process can approve anything, by design, permanently.
3. Before substantial work, rules are retrieved for the task, with the matched
   words shown. Retrieval is lexical word matching and says so in its output.
4. Work is claimed with a file fence. A second session's edit to a fenced file
   is denied, and the denial names the record, the owner, and the command that
   would move the fence deliberately.
5. Outcomes are graded: retrieved, followed, and "did the work still go wrong"
   are three separate questions. Where there is no evidence, the tool prints
   NOT MEASURED instead of a comfortable zero.

There is a public benchmark of thirteen scenarios, published with inputs and
expected outputs rather than a score:

```
python3 scripts/benchmark.py
```

Writing it found a real defect: a result limit could silence a safety rule.
That is scenario 3, with its reproduction command in the docs.

**What I am not claiming.** It does not stop you repeating yourself, it tells
you why a repeat happened. It does not improve itself: every rule went through
my approval. There is no statistical learning here, because one person's twenty
to forty rules is not a dataset. And the biggest gap is written down as open
item 1 in the repo: this has not yet run through a real working day of my own
work. Everything green today is a test suite, a benchmark, or a scripted probe.

Honest limits: `docs/KNOWN-LIMITS.md`. Five minute walkthrough: `docs/DEMO.md`.
I would rather hear where a claim is too strong than hear that it looks nice.

## Assets checklist for the founder

- Gallery image 1: the deny message from `docs/DEMO.md` step 5, as a terminal
  screenshot. It is the single most legible thing this project does.
- Gallery image 2: `python3 scripts/benchmark.py --quiet` output, all thirteen
  lines visible.
- Gallery image 3: the capture then approve pair, showing "nothing changes
  until you approve it".
- Do not build a demo video that shows behaviour the code does not have.

## Forbidden claims, repeated so they cannot be lost

It never repeats mistakes. It autonomously improves itself. Founder identity is
cryptographically guaranteed. Every shell write is mechanically fenced. Windows
owner-only privacy. Production readiness beyond the tested user and platform
scope.
