# M08: new refusal codes reached the founder with no plain language, twice

## WHAT HAPPENED

Plain language: when BrotherMe refuses to do something, it raises an internal code
like `no-write-scope`. The founder must never see that code raw. Every code has to
have a founder-facing rewrite: what we were doing, what went wrong, what to do
next.

The authorisation work added new refusal codes to the store. The plain-language map
was not updated at the same time, so the new codes had no rewrite. This happened
twice in the same night: once when the first round added four codes, and again
when the second round (the fix for the refuter's findings) added a fifth.

Both times the visual suite refused the change.

## HOW IT WAS FOUND

By a guard, both times: `TestEveryRefusalIsRewritten` at
`/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_bm_visual.py:872`.

What makes this guard work is that it does not hold a hand written list of codes.
It parses the store's own source with the `ast` module and collects every code the
store can actually raise, at
`/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_bm_visual.py:80`
(`_store_reason_codes`). A hand list would go stale the day somebody adds a
refusal, which is the failure this guard exists to prevent (its own docstring says
so at tools/test_bm_visual.py:81 to 84).

## THE EVIDENCE

The assertion that fires, verbatim from tools/test_bm_visual.py:876 to 888:

```python
codes = _store_reason_codes()
self.assertGreater(len(codes), 100,
                   "the scanner found almost nothing, so it is "
                   "broken rather than the map being complete")
missing = sorted(codes - set(bv.REFUSAL_HELP))
self.assertEqual(missing, [],
                 "reason code(s) with no founder facing rewrite: %s"
                 % (missing,))
extra = sorted(set(bv.REFUSAL_HELP) - codes)
self.assertEqual(extra, [],
                 "REFUSAL_HELP names code(s) the store cannot emit, "
                 "so they are dead entries: %s" % (extra,))
```

It refuses in both directions: a code with no rewrite, and a rewrite for a code
that no longer exists.

The repair, `git show ac7ef87 -- tools/bm_visual.py`, five entries added under one
comment:

```
+    # L09 (2026-08-06): the authorisation narrowings landed four new codes.
+    "no-run": (...)
+    "run-terminal": (...)
+    "path-is-floor": (...)
+    "write-scope-is-floor": (...)
+    "no-write-scope": (...)
```

The comment says four and the block contains five. That mismatch is consistent
with a second wave, and the two rounds line up with it: `no-run` and `run-terminal`
are the round-1 takeover refusals (named in the L09 fix report at lines 135 to
136), `path-is-floor` and `no-write-scope` are the other two round-1 narrowings
(raised at tools/bm_store.py:13234 and :13259), and `write-scope-is-floor` is the
refusal introduced by the round-2 plan-time floor fix (raised at
tools/bm_store.py:14433, described in the fix report's FIX A2 section). The comment
above them was written in round 1 and not updated in round 2.

Current anchors: `REFUSAL_HELP` starts at
`/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_visual.py:1764`, and the
five entries sit at tools/bm_visual.py:2153, 2157, 2162, 2167 and 2173.

## HOW IT WAS FIXED

Five entries added to `REFUSAL_HELP`, each a three part tuple (what we were doing,
what went wrong, what you can do), each written in founder language with no command
line flags in it. The guard also refuses an entry containing `--`, because that
reads like a command and not like a sentence (assertion at
tools/test_bm_visual.py:895).

One entry verbatim, read at tools/bm_visual.py:2173:

```
"no-write-scope": (
    "signing the work authorisation",
    "the authorisation grants writing work but does not say where "
    "writing is allowed",
    "Name the folders the work may touch, or grant only read-only "
    "work."),
```

Both suites green afterwards, from the commit's evidence block: `test_all: 2442
tests across 20 suites, 6 skipped, 352.2s wall. ALL GREEN`.

## THE RULE THIS PRODUCES

A new refusal code is not landed until its founder-facing rewrite lands in the same
edit; if you added a `raise` this session, run the visual suite before you call the
change done.

## WAS IT CAUGHT BEFORE OR AFTER IT COULD HURT A USER

Before, both times, by a guard that reads the source rather than a list somebody
maintains. This is the cheapest failure in the folder and the one that repeated
most, which says something about how easily a cross-file obligation is forgotten
when the work is happening in a different file.
