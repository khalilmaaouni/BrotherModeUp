# M10: a writer landed a file that turned a guard red, and left the red for somebody else

## WHAT HAPPENED

Plain language: the repository pins the exact set of shipped commands, by exact
equality. Adding a fifteenth command file turns that test red until somebody
updates the pinned list and writes down why the set grew. That is the pin's
designed cost, deliberately.

The visual surface required a new command file, `commands/brotherme-view.md`. The
writer who created it was not allowed to edit `tools/test_bm.py`, where the pin
lives. So the writer landed the command file, leaving the test suite red, wrote the
exact one line remedy into its report, and stopped.

That is defensible under a single-writer fence. It is also how a tree ends up red
for a stretch with nobody owning the fix, and it happened twice in the same loop:
the same writer also found that a copy rule and another writer's brand new test
file could not both hold (see M11), and left that one for its owner too.

## HOW IT WAS FOUND

By the pin itself,
`test_exactly_seven_brotherme_commands_ship` at
`/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_bm.py:5680`, run by the
writer against its own change before and after. The name of the test is two
families out of date on purpose, which the test's own comment explains.

## THE EVIDENCE

From `/Users/khalil.maaouni/Documents/BrotherModeUp/docs/program/absolute-lead/evidence/L05/RED-F.txt`
lines 128 to 164, before and after, verbatim:

```
BEFORE, on the untouched tree, with fourteen command files:

    $ python3 tools/test_bm.py TestTheSeventhCommandAndTheDeepTourAreWired
    Ran 8 tests in 0.004s

    OK
    exit=0

AFTER commands/brotherme-view.md exists, which design section 12.3 requires:

    FAIL: test_exactly_seven_brotherme_commands_ship
      File ".../tools/test_bm.py", line 5703, in
      test_exactly_seven_brotherme_commands_ship
        self.assertEqual(expected, found,
    AssertionError: Lists differ: [...'brotherme-update.md'] !=
    [...'brotherme-update.md', 'brotherme-view.md']

    Second list contains 1 additional elements.
    First extra element 14:
    'brotherme-view.md'

    ... the shipped command set drifted from the fourteen this release
    documents (seven beginner, three controller, four founder mode)

    FAILED (failures=1)
    exit=1
```

The writer's own framing, from
`docs/program/absolute-lead/evidence/L05/FIX-L05-docs-report.md` lines 58 to 73,
under the heading "0.2 A pinned count moved, and the pin belongs to nobody in this
loop":

```
The file was landed anyway rather than withheld, for the reason the pin's own
comment gives: the pin is doing its designed function, and every growth of the
command set is supposed to cost somebody a sentence.
```

## HOW IT WAS FIXED

The orchestrator applied the remedy the writer had specified. At
`/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_bm.py:5680` to 5710 the
pinned list now carries `"brotherme-view.md"` as its fifteenth entry, and the
comment above it carries the new clause:

```
# L05 adds one (view, the live project page), the visual surface's single
# command, so it is now fifteen.
```

The failure message was updated in the same edit to say fifteen and to name the
four families. The suite was green in commit b02756f (`test_all: 2370 tests across
20 suites, 6 skipped, 308.2s wall. ALL GREEN`).

## THE RULE THIS PRODUCES

If your change turns a guard red in a file you are not allowed to edit, the change
is not finished: write the exact remedy with its file and line into your report,
and hand the red to a named owner in the same breath, because a red left in the
tree with no owner is how a suite gets weakened by whoever trips over it next.

## WAS IT CAUGHT BEFORE OR AFTER IT COULD HURT A USER

Before, and no user could ever have been hurt by this one: the pin protects the
project's own honesty about what it ships, not the user's install. The real risk it
carries is cultural. A red suite that somebody else is supposed to fix is the exact
condition under which a future session deletes an assertion to get green.
