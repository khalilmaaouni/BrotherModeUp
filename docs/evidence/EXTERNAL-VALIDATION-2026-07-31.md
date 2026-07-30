# External validation: checking this project's own fixes against third-party ground truth

Status: CURRENT as of 2026-07-31.

## What this is, and what it is deliberately NOT

**This is not dogfood evidence.** The execution plan's Loop 7 asks for BrotherMode
used on the founder's own real work across 20 working days or 100 substantial tasks
and at least three project types. Its purpose is to answer one question: does this
system help THIS founder on HIS work. No amount of solving problems found on the
internet can answer that, and presenting such work as dogfood would be fabricated
evidence of exactly the kind this project exists to prevent. Loop 7 remains OPEN and
untouched.

**This is a validation exercise with external ground truth**, which is a different
and weaker claim, and the strongest evidence a machine can generate about its own
work without a human in the loop: take a fix this project made on its own judgement,
find an independent authority on the same question, and check whether the fix agrees.
The value is that the answer is fixed by a third party BEFORE the check, so the
exercise can fail.

It did fail, once, which is the only reason it is worth reading.

## Method

1. Take a defect fixed earlier the same day on this project's own reasoning.
2. Find independent published authority on the same question.
3. Compare rule against rule, not impression against impression.
4. Where they disagree, treat the external source as correct until shown otherwise,
   fix, and record the disagreement rather than the agreement.

## Case 1: POSIX shell quoting used on Windows

**What this project did, on its own judgement.** The Windows continuous-integration
legs were failing. The cause was `invocation()`, which built every user-facing
command with `shlex.quote`. A Windows path came back wrapped in single quotes, so the
printed remedy read `python3 'C:\Users\...\bm_store.py'`, which neither cmd.exe nor
PowerShell will run. Fixed by quoting for the platform: POSIX keeps `shlex`, Windows
gets double quotes when the path contains a space.

**External source 1: Python's own documentation for `shlex`.**

> "The `shlex` module is only designed for Unix shells. The `quote()` function is
> not guaranteed to be correct on non-POSIX compliant shells or shells from other
> operating systems such as Windows. Executing commands quoted by this module on
> such shells can open up the possibility of a command injection vulnerability."

VERDICT: the diagnosis was correct, and the documentation states it more strongly
than this project had. Note the limit of that last sentence for this codebase:
BrotherMode PRINTS the command for a human to paste and never executes it, so the
injection wording describes a hazard this code does not itself create. The reader
holds it.

**External source 2: `mslex`, a package that exists because the standard library
declines this job, and `oslex`, which selects `mslex` on Windows and `shlex`
otherwise.** That two packages exist for this is itself evidence the failure class is
recognised rather than theoretical, and `oslex`'s select-by-platform shape is the same
shape this project arrived at independently.

`mslex`'s documented cmd rule quotes when the string matches
`[\s"^&|<>()%!]`.

**VERDICT: DISAGREEMENT. This project's fix was too narrow and the external rule was
right.** The first version quoted only on a space or a double quote. Reproduced
against real path shapes, before the second fix:

| Path | First fix returned | cmd.exe reads |
|---|---|---|
| `C:\R&D\tools\bm_store.py` | bare | `&` as a command separator |
| `C:\temp\100%\bm_store.py` | bare | `%` as a variable reference |
| `C:\a!b\bm_store.py` | bare | `!` as delayed expansion |
| `C:\Program Files (x86)\...` | quoted | correct, but only because it also has a space; its parentheses are metacharacters too |

None of those is an exotic path. `Program Files (x86)` is on essentially every
Windows machine, and it passed for the wrong reason.

**What changed.** `_quote_path_for_local_shell` now quotes on the full external
character set plus any whitespace, reimplemented rather than taken as a dependency
because this project is standard library only, with the source named in the code. The
tests encode `mslex`'s cases rather than this function's own behaviour, which is the
whole point: a test written from the implementation would have agreed with the
implementation and found nothing.

Calibrated: reinjecting the pre-fix rule leaves all three hazardous paths unquoted.

## What this exercise proves, stated narrowly

- One fix made on this project's own judgement was **directionally right and
  materially incomplete**, and an independent published rule found the gap in a
  single comparison.
- The project's stated habit ("every serious defect was found by running the real
  thing while the tests were green") now has a second edge: some defects are found by
  comparing a rule to someone else's rule, and no amount of running would have shown
  this one, because the local machine is not Windows.

## What it does NOT prove

- Nothing about whether BrotherMode helps its founder. That is Loop 7 and it is open.
- Nothing about Windows behaviour observed directly. The fix is validated against a
  documented rule and against CI, not against a Windows machine in this room.
- Nothing about the other loops. One case is one case.

## Sources

- Python `shlex` documentation, quoted above:
  https://docs.python.org/3/library/shlex.html
- `mslex`, quoting rules read from source:
  https://github.com/smoofra/mslex/blob/master/mslex/__init__.py
- `mslex` package page: https://pypi.org/project/mslex/
