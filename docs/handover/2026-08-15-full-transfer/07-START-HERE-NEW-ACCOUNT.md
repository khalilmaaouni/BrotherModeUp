Status: CURRENT. Written 2026-08-15 for a session starting on a DIFFERENT
ACCOUNT, possibly a different machine.

# Start here

You are picking up two products mid-flight. This pack is self-contained on
purpose: every document you need is inside it, not linked to a path on the
machine that wrote it. Read in this order and you will be productive in about
twenty minutes.

    07  this page                      what to do first
    10  the north star                 the shape everything serves
    11  the problems and solutions     fourteen from the pilot team, nine nobody raised
    04  next loops, prioritised        what to actually do
    06  the close report               what was finished and what was not
    12  the escalation capability      how the system asks for help
    02  learnings and mistakes         five, three of them mine
    03  rules and process fixes        what those mistakes earned
    13  the note to the reviewers      the thing waiting to be sent
    14  the queue, as data             every open item with a stage and a done-check
    15  the deltas                     three patches held rather than folded,
                                       with a README saying why each was held

Two web pages are included as files so they open with no account:
`north-star-chain.html` (the operating model) and `team-review-page.html`
(the pilot team's fourteen problems).

## What these two products are, in four sentences

BrotherMode governs one person's working session: it records what actually
happened, keeps two writers off one file, refuses a "done" that no command
proved, and hands over cleanly when a session ends.

BrotherSBE governs a change as it crosses between people: what the software
must do, how risky it is, what must be proven, whether the proof is real, who
is accountable, and what happened after release.

They meet at exactly one object, the change passport, which does not exist yet
and is specified in document 10.

Neither product performs the release, and neither may remove the point where a
human decides.

## Getting the code

Two repositories, both public:

    `github.com/khalilmaaouni/BrotherModeUp`   the orchestration product
    `github.com/khalilmaaouni/BrotherSBE`      the assurance product

The orchestration repository is fully pushed as of this pack. The assurance
repository was NOT pushed at the time of writing: see the close report, and
item one of the next loops.

## The first three commands, in this order

    git -C <orchestration repo> log --oneline -5
    git -C <orchestration repo> status --short
    python3 tools/bm_idle.py check

The third prints the queue depth and, on the line after it, every queued item
that does not yet name a stage of the north-star chain. That second line is
the health of the plan, not of the code.

## The one rule that will save you the most time

TWO OTHER SESSIONS WORKED THESE REPOSITORIES ALL DAY. Files changed underneath
this session seven times, one writer lane spent twenty minutes rebuilding work
another session had already landed, and one full twenty-two-minute test run
was corrupted by the tree moving mid-run and reported a failure in code that
was fine.

So: re-read `git status` and `git log --oneline -1` immediately before every
fold and every measurement, not only at session start. If you are about to run
the full battery, confirm the tree is clean first, and confirm it is still
clean when the battery finishes.

## What is genuinely blocked, so you do not rediscover it

- BrotherSBE was unpushed pending a founder decision on a history rewrite.
  A peer session has since rewritten the messages and verified it; the push
  itself remained founder-gated.
- `tools/bm_effects.py` in the orchestration repository sat under another
  session's live claim, so one of the escalation tool's six registrations is
  unapplied. The file's own comment explains why it must land as a pair.
- The vault referenced in document 05 is a private Obsidian vault on the
  original machine. It is NOT in this pack and you do not need it; every fact
  it holds that matters is in these documents.

## What honest looks like here, because it is the house style

Absent evidence is never a pass. A check that cannot tell you something says
NO-DATA and names what it could not see. A claim of "done" carries the command
that proved it, run after the last edit. If you find any statement in this
pack without that, treat it as unproven and say so; several statements in the
session that wrote it were refuted by its own controls and are marked where
they were made rather than quietly corrected.
