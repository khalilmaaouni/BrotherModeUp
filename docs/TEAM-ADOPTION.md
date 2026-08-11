# Adopting this as a small engineering team

Status: CURRENT

For a team of roughly two to fifteen people who want a change to be
finished when somebody other than its author can see that it works, without
redoing the work.

This guide is honest about one thing up front: **no team has completed this
adoption yet.** The phases below are a design, not a report. The first team
to run them should expect to find things this page does not mention, and the
weekly review exists precisely to catch them.

---

## What you are adopting, in five sentences

You keep two tools. This one governs one person's session, from the moment
they sit down until they stand up, across days. Its sibling governs one
change's passage between people. You keep whatever you already use for
writing code; those live inside one step of the loop, not around it. A change
is done when a check has run after the last edit and its output is written
next to the claim.

**The two tools do not overlap.** This one holds your goal, what you are
allowed to do, which files are yours right now, and the refusal to say done
without proof. The sibling decides how risky a change is, what design it
owes, who must review it, and whether its proof is real or missing. They meet
at exactly one object: the change you are about to hand to somebody else.

Using both is not twice the work. You use this one all day, and the sibling
at the two moments that matter: before you start writing code, and before you
ask anyone to trust the result.

---

## Where you type what

This is the mistake every new person makes, and it costs an afternoon.

**Inside your agent session**, with a slash: the commands from both plugins.
They answer there, ask you questions, and do work for you.

**In your terminal**: only the sibling's command-line program, which reads
your git diff.

**There is no terminal command for this product.** If you type its name at a
shell prompt you get "command not found". That is correct behaviour, not a
broken install. When a teammate says it is not installed, this is almost
always what they hit.

---

## The loop a change walks

Nine steps. Always the same nine. Only the amount of work inside each one
changes.

| # | Step | What it settles | Who leads |
|---|---|---|---|
| 1 | Intent | what and why | whoever wants the change |
| 2 | Clarify | what acceptance looks like | requester plus whoever will check it |
| 3 | Intake | how risky this is | engineer |
| 4 | Design | only what the risk level owes | engineer |
| 5 | Build | your own tools, unchanged | engineer |
| 6 | Review | the right eyes, not all eyes | reviewer |
| 7 | Prove | evidence, not words | whoever checks |
| 8 | Deliver | a human merges | a human |
| 9 | Learn | a rule, not a memory | everyone |

This product holds the thread across all nine, and across days, sessions and
handovers. The sibling gates four of them. Step 5, build, stays entirely
yours.

**The one rule that makes the loop worth walking:** a step is finished when a
check has run after the last edit and its output is written down next to the
claim. No output means no proof, and no proof is never a pass.

---

## What travels between people

**The handover pack, committed to the repository the work lives in.**

Not a shared database, and not a note somewhere. A folder in your repository
that the next person pulls along with the code and reads in order. It refuses
to close on hollow claims: a missing status line, a session still holding
files nobody released, evidence that says less than it appears to.

This is deliberate and it has a cost worth naming. A pack in a repository
cannot show you a live view across several repositories at once. That is a
later tranche, and it is the most expensive single thing on the roadmap
because it needs a migration story for every record that already exists.
Until then, the pack is the unit, and it is enough for a team working in a
handful of repositories.

Each repository also carries a progress page: one file, committed, that
anybody can open in a browser without an account, showing what is done with
the proof beside it. It refreshes whenever a piece of work closes.

---

## Five phases, each ending on a test rather than a date

A phase ends when its exit test passes. Never because a date arrived, and
never because people are impatient.

**Phase 0, two people.** Install both tools on a throwaway repository. Run one
edit, one deliberate conflict, and one resume after closing the session.
Confirm both plugins coexist. Write down the exact version everybody will
install.
*Exit test: both run together for a full working day with no conflict, and
the version is written somewhere the whole team can read.*

**Phase 1, three real changes, same two people.** Real work, never a toy
example. Pick three that differ: one touching an outside party, one ordinary
feature, one data or infrastructure job. Daily notes start here.
*Exit test: each of the two can explain the whole loop from memory in under
two minutes.*

**Phase 2, engineering and quality.** Everyone installs. Continuous
integration runs on pull requests and blocks nothing yet. Whoever checks the
work starts naming the proof before the code is written.
*Exit test: somebody who was not in Phase 1 completes a change alone, without
asking either of the first two for help.*

**Phase 3, the whole chain.** Requests enter through a shaped template.
Acceptance happens against stated criteria rather than by one person testing
everything themselves.
*Exit test: the queue of work waiting on a single checker has shrunk, and the
proof was named first on every higher-risk change.*

**Phase 4, selected gates turned on.** Only checks that have already caught
something real become blocking, and only on the riskiest paths first.
*Exit test: every blocking gate can point at the week it was earned.*

**Do not add people to fix a phase that is not working.** If Phase 1 is
painful, Phase 2 is painful with more people in the room.

---

## How your team decides what the process should be

You do not know the right process for your team yet. Nobody does, because it
depends on your code, your partners and your people. So do not write the
rules in advance and enforce them. Run the process, collect what actually
happens in writing every day, and let a weekly meeting change one thing at a
time, with a reason.

### The daily note, two minutes, every person

Four lines. Not a report. Written where you work.

1. What did I try to do with the tools today? One line; the task name is
   enough.
2. Where did I get stuck, and for how long? The command, the message, the
   minutes lost.
3. What did the tool catch that I would have missed? Write "nothing" when it
   is nothing. That is data too.
4. One thing I would delete from the process. Always answer this one, even
   when it feels small. This is the question that stops the process growing
   without limit.

**A week of blank notes is a finding**, not an absence of one. It means the
process is too heavy, or people have stopped believing anybody reads them.

### The weekly review, sixty minutes, same agenda every time

| # | Step | Time | Output |
|---|---|---|---|
| 1 | Read the notes out loud, oldest first, no discussion | 15 min | everybody hears the same thing |
| 2 | Count the minutes lost this week, from the notes | 5 min | one number on the board |
| 3 | Count what the tools caught | 5 min | one number on the board |
| 4 | Discuss only what appeared more than once | 15 min | a shortlist |
| 5 | Change exactly one thing | 10 min | add a check, remove a step, or turn one gate on |
| 6 | Write the decision and what would reverse it | 5 min | a note anyone can find later |
| 7 | Name who is blocked and what needs deciding above the team | 5 min | a short list |

**Why exactly one thing.** Change five and a bad week teaches you nothing.
Change one and you know what caused the difference.

**The two numbers that decide everything** are steps 2 and 3: minutes lost
against things caught. If minutes lost is high and things caught is near
zero, the process costs more than it returns, so remove something. If things
caught is high, name what would have happened had it not been caught. That is
the argument for keeping a gate when somebody complains about it. Write both
numbers every week, including the embarrassing ones. A process that cannot
show its cost cannot defend its value.

### How a check earns the right to block

All three must be true. It has caught something real at least once and you
can name it. The daily notes have gone quiet about it, meaning people
understand its output. It applies to your riskiest paths, never to the
smallest changes.

It loses that right immediately if it blocks somebody wrongly. Turn it off
the same day, say that you did, fix the cause, and bring it back next week.
**A gate nobody trusts is worse than no gate at all.**

---

## Cadence

One week per sprint, anchored to the weekly review, turning on the same
weekday every week. One release per sprint, on the boundary, and only if
everything is green. A sprint that ends red does not release, and that is a
reportable outcome rather than a failure.

---

## Honest limits

- No team has completed this adoption. The phases are a design.
- The two products version independently. Write both numbers down.
- A live view across many repositories at once does not exist yet.
- Nothing here removes the need for somebody to think. The tools refuse
  hollow claims; they do not decide whether the work was worth doing.
