# M09: a test count was written into the capability register

## WHAT HAPPENED

Plain language: BrotherMe keeps a register of what it claims it can do, and what
proves each claim. That register is the single source for a block of text that gets
generated into README.md. A number like "993 tests" was written into one of those
evidence sentences. The repo has a rule against exactly that, because a test count
changes the day anyone adds a test, and a page that quotes yesterday's count is a
page that lies today. The guard refused it.

IMPORTANT HONESTY NOTE: this incident is reported by the orchestrator of the night
and I could not find it recorded anywhere in the repository or in git history,
which is expected, because a guard that refuses a change before it is committed
leaves no trace. So the incident itself is UNVERIFIED by me. Everything below about
the mechanism is verified by commands I ran in this task.

## HOW IT WAS FOUND

By `TestNoStaleCurrentNumbers.test_no_active_document_pins_a_test_count` at
`/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_bm_docs.py:191` (class at
tools/test_bm_docs.py:184).

The path from the register to the guard, verified:

1. `render_capability_status` at
   `/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_docs.py:1406` puts each
   register entry's `evidence` field verbatim into a table cell, at
   tools/bm_docs.py:1439.
2. That block is generated into README.md, and README.md is the first entry in
   `ACTIVE_DOCS` at tools/test_bm_docs.py:72.
3. The guard scans every active document line by line for three count patterns.

So the number never had to be typed into README.md by hand. Typing it into the
register was enough to put it there.

## THE EVIDENCE

The guard's own patterns and message, verbatim from tools/test_bm_docs.py:184 to
205:

```python
class TestNoStaleCurrentNumbers(unittest.TestCase):
    COUNT_PATTERNS = (
        re.compile(r"Ran\s+\d+\s+tests"),
        re.compile(r"\b\d+\s+tests\b"),
        re.compile(r"exactly\s+\d+\s+tests?", re.IGNORECASE),
    )
    ...
        "an active page pins a test count (%s). Counts move with every test "
        "that lands; say to run %s and expect %s instead, and keep exact "
        "counts in dated evidence."
```

I ran those three patterns against three candidate sentences in a scratch script
to confirm the guard bites on the shape in question and not on a clean sentence:

```
$ python3 guard_probe.py
REFUSED | proven by tools/test_bm_store.py (993 tests, all green) | ['\\b\\d+\\s+tests\\b']
REFUSED | Ran 2442 tests in 352.2s | ['Ran\\s+\\d+\\s+tests', '\\b\\d+\\s+tests\\b']
allowed | proven by tools/test_bm_store.py | []
```

And the current state of the tree is clean of pinned counts in active pages,
verified now:

```
$ grep -n "993\|2442\|2370\|Ran [0-9]* tests" README.md docs/*.md capabilities.status.json
docs/BENCHMARK-2026-07-26.md:60:Expect `Ran 189 tests` and `OK` (measured 2026-07-26; ...
docs/NOT-FINALIZED.md:1075:... `Ran 660 tests ... OK` all three
```

Both survivors are dated evidence pages, not active pages, which is exactly where
the rule says exact counts belong.

## HOW IT WAS FIXED

The count was removed from the register entry and the sentence was rewritten to
name the suite that proves the claim instead of quoting its size. Every evidence
field in
`/Users/khalil.maaouni/Documents/BrotherModeUp/capabilities.status.json` today
names files and behaviours, and none of them names a number of tests, which I
verified with the grep above.

The exact numbers still exist, in the two places the rule allows: the commit
message (`test_all: 2442 tests across 20 suites, 6 skipped, 352.2s wall. ALL
GREEN`, in commit ac7ef87) and the dated evidence files under
`docs/program/absolute-lead/evidence/`.

## THE RULE THIS PRODUCES

Never write a count that moves (tests, files, lines) into a page or a register that
claims to be current; name the command and the expectation instead, and keep exact
numbers in dated evidence and commit messages where they are timestamped.

## WAS IT CAUGHT BEFORE OR AFTER IT COULD HURT A USER

Before, by a guard, and it never reached a commit. Which is also why it left no
trace, which is why this file has to say UNVERIFIED next to the incident itself.
The mechanism that would have caught it is verified and live.
