# M16: a writer recorded the delta another file needed, and nobody applied it

## WHAT HAPPENED

Plain language: writers in this system are fenced. A writer may only edit the files
it was granted, so when its work creates an obligation in somebody else's file, it
writes that obligation down as a "delta for the orchestrator" and stops.

The benchmark harness writer did exactly that. It created two new files and
recorded that neither is covered by the no-dashes copy rule, with the exact one line
change needed. That change was never applied. The two files sit outside the guard
today.

Consequence: `scripts/benchmark_comparative.py` and `docs/BENCHMARK-COMPARATIVE.md`
are clean of em and en dashes right now, verified below, but nothing stops the next
edit from putting one in. The founder's copy rule is unenforced on two of the
night's new files.

## HOW IT WAS FOUND

By me, in this task, comparing the deltas recorded in the build report against the
current state of the target file.

## THE EVIDENCE

The recorded delta, from
`/Users/khalil.maaouni/Documents/BrotherModeUp/docs/program/absolute-lead/evidence/BENCH/HARNESS-BUILD-REPORT.md`,
section "Deltas other files need (recorded, NOT applied ...)", item 1:

```
1. `tools/test_bm_docs.py`, class `TestNoDashes`, method
   `test_no_em_or_en_dash_in_the_active_pages_or_this_toolchain` (targets
   list at approximately line 4774): neither new file is covered by the
   dash guard today, because `docs/BENCHMARK-COMPARATIVE.md` is not in
   `ACTIVE_DOCS` and `scripts/` is not scanned. Exact delta: append
   `os.path.join("scripts", "benchmark_comparative.py")` and
   `os.path.join("docs", "BENCHMARK-COMPARATIVE.md")` to that `targets`
   list. Both files pass the scan today; the delta pins them.
```

The current state of the guard, verified in this task:

```
$ grep -rn "benchmark_comparative" tools/test_bm_docs.py
(no output, exit 1)
```

The target list at
`/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_bm_docs.py:4774` to 4783
contains ten entries and neither of the two benchmark files is among them.

The files are clean today, which is why this is a gap and not a live breach:

```
$ LC_ALL=C grep -c $'\xe2\x80\x94\|\xe2\x80\x93' scripts/benchmark_comparative.py \
    docs/BENCHMARK-COMPARATIVE.md
docs/BENCHMARK-COMPARATIVE.md:0
scripts/benchmark_comparative.py:0
```

Note the second recorded delta in the same report (a one line cross-reference from
`docs/BENCHMARK.md` to the new comparative protocol) was marked optional and was
also not applied. I did not check whether it matters.

## HOW IT WAS FIXED

NOT FIXED. This is open at HEAD (c1d7a47). The remedy is the two lines the writer
already specified, appended to the targets list at tools/test_bm_docs.py:4783,
followed by `python3 tools/test_bm_docs.py`.

Wider context, because it is the same root cause: the benchmark harness itself was
built, frozen and committed (745e2d7) but never run, because a fresh headless
Claude session is not signed in. The evidence directory
`docs/program/absolute-lead/evidence/BENCH/` contains exactly one file, the build
report, and no run artifacts, verified with `ls`. So the founder-ordered loop
delivered the harness and not the numbers.

## THE RULE THIS PRODUCES

A delta recorded for somebody else is not done until somebody applies it: the
orchestrator collects every "delta for you" line from every writer report into one
list and closes each one by name before the loop is called finished.

## WAS IT CAUGHT BEFORE OR AFTER IT COULD HURT A USER

Neither, and that is the point: it is still open. No user is harmed by an unenforced
copy rule today, because both files are clean. The failure is that a writer did the
honest thing, wrote down exactly what somebody else had to do, and the handoff
dropped it silently. Every other mistake in this folder was caught by a guard or a
refuter; this one is here only because somebody went back and read the reports.
