Status: CURRENT as of 2026-08-06. The fixed pilot protocol for the first five
outside users. Ratified by the founder 2026-08-06 through decision windows.
No em or en dashes.

# The first-five pilot, fixed protocol

Five people who have never installed BrotherMode: at least two solo founders
or non-technical builders, at least two individual contributors, one more
from either group. Everyone gets the same public instructions, the same
first task, and the same nine questions. Nobody gets coached through hidden
steps: if a step needs coaching, that is a finding about the step.

## What each pilot does, in order

1. Install from the public instructions (the install section of
   docs/QUICKSTART.md), using only what the page says.
2. Run /brotherme-help and read what it prints.
3. THE FIXED FIRST TASK, about 30 minutes: start a project called
   "reading-list" whose goal is a small personal reading list page: three
   books, one paragraph each, one HTML file. Use /brotherme-start, let the
   flow guide you, and accept its recommendations unless you disagree.
4. Produce the artifact (the page) through the flow.
5. Run /brotherme-status and say aloud, in one sentence, where the project
   stands. Write that sentence down; it is measure 5.
6. Close the session mid-project on purpose.
7. Come back later (hours or a day) and resume with /brotherme-next. Do NOT
   re-explain the project; the product must remember it.
8. Run /brotherme-review or /brotherme-deliver to close the task.
9. Then use it on a small piece of YOUR OWN real work for the rest of the
   week, however you like.

## The nine measures, self-reported

1. Did the install succeed first try? If not, where exactly did it stop?
2. Minutes from starting the install to the first useful artifact.
3. How many times did you not know what to do next?
4. How many times did you have to recover by hand (delete something, start
   over, edit a file the product should have handled)?
5. Your one-sentence answer to "where does the project stand" after
   /brotherme-status, written at the time.
6. After the flow told you something was done, did you know WHAT had been
   checked? Yes or no, plus one line.
7. Did resume work without re-explaining the project? Yes or no.
8. Would you keep using it after this week? Yes or no.
9. The single biggest reason you would not.

Answers go through docs/FEEDBACK.md (the week one questionnaire carries
these nine) and failures through the GitHub issue templates, which collect
nothing automatically.

## The rules the team holds itself to

- The pilot measures the PUBLIC instructions. No hidden help. A question a
  pilot has to ask is recorded as a finding, answered once, and the answer
  goes into the page it was missing from.
- If two or more pilots fail at the same step, that step is broken: it gets
  fixed, and the pilot count for the changed flow restarts at zero.
- Raw answers and environments stay OFF the public repository. One dated,
  redacted summary lands in docs/beta/ tied to the exact commit and version
  the pilots installed, and claims are limited to what the five runs showed:
  five first-time users completed or failed this protocol under these
  recorded conditions, nothing broader.
