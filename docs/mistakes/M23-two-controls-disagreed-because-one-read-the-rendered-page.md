Status: OPEN defect, demonstrated 2026-08-16 with both controls' own output.
Not a historical record: it blocked a real documentation fix the same night and
nothing has changed it since. No em or en dashes.

# M23: two controls disagreed about who holds a fence, because one read the rendered page

## What happened

Two different sessions, minutes apart, were refused an edit to a documentation
file by the write guard. The second refusal named its own source:

    BrotherSBE fence (L13, one writer per file): docs/SETUP.md is inside the
    file scope of a LIVE fence in .../STATE.md, opened by agent install-truth
    ... as sole writer for session f5aac5ba.

The store was then asked directly, through its own CLI rather than a second
parser (`python3 tools/bm_store.py dashboard`). It holds two active records:

    controller-v3-finalization   owner-session 18a183a9                files: (none)
    northstar-plan-2026-08-15    owner-session opus5-2026-08-15-plan   files: (none)

Neither is that session. Neither claims a single file. And `bm_store.py`'s own
module docstring states the rule that makes this the authority: "Nothing else
in this project is allowed to be the source of truth for who owns what work."

STATE.md is what `bm_store.py` RENDERS. Its own header says so: "anything
inside them is overwritten on the next render."

So the guard refuses writers on the strength of a generated page, while the
database that generates it holds no such claim.

## Why it is worse than a stale fence, and this is the actual finding

Its remediation is self-contradictory. The hook offers three ways out, and TWO
of them instruct the caller to hand-edit STATE.md: append an evidence block to
the fence line, or append ADOPTED and write a new fence line naming your
session. Both mean writing into a generated view that the next render
overwrites, in a project whose store contract exists precisely to stop that.

A session obeying the guard is told to do the thing the store forbids.
A session obeying the store is told it is writing across a live fence.
There is no correct action available inside the two rules as written.

That is the difference between a stale claim, which is an annoyance, and this,
which is a rule conflict with no legal move.

## What was NOT established, deliberately

Whether session f5aac5ba ever existed, whether that fence was ever live, and
how the line reached STATE.md. Nobody went looking with a grep. Re-deriving a
control's state with a second parser is the recorded incident of 2026-08-10,
where a fence-closing grep reported zero while the hook saw four. The store was
asked, the hook was allowed to refuse, and both answers are quoted rather than
reconciled by a third parser written on the spot.

## What was done

Nothing was written across the fence and STATE.md was not hand-edited. The
edit that triggered it, correcting `docs/SETUP.md` line 79, which still claims
"the clone is the installation" after the same false sentence was corrected
elsewhere, is left UNMADE and recorded as owed.

That is the right trade and it is worth stating as a rule rather than as a
one-off choice: a blocked fix with both controls quoted is worth more than a
landed fix that required bypassing a guard. The same instinct, on the same
night, stopped a session from editing a check's own worked-example fixture to
turn a red pull request green.

## The related gap, disclosed by the session it caught

The guard refuses `Edit`. It does not gate `Bash`. A session folded a patch
with `git apply` through the shell, crossed the same fence unrefused, and only
discovered the fence when its NEXT `Edit` was blocked. That gap is already
written in this product's own limits page. It now has an incident and a commit
behind it rather than only a sentence.

## Status of a control

The conflict itself is UNFIXED and is queue item O23, previously framed as a
design preference ("the assurance product should ask the store instead of
parsing the generated view"). It is no longer a preference: it is demonstrated,
and it blocks work.

The fix is that the side reading fences asks the store through its API. The
harder half, and the one to design deliberately rather than patch, is what a
guard should do when its two sources disagree. Refusing on the union of both is
what happened here and it produced an unsatisfiable instruction. Refusing on
the store alone is correct only if the store is genuinely complete. Saying
NO-DATA and naming the disagreement is the shape both products already use
everywhere else, and is the recommendation on record.
