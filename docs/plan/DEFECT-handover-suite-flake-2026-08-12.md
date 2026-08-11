# Defect: test_bm_handover.py failed once inside the gate and will not reproduce

Status: CURRENT, OPEN

Found 2026-08-12 02:26 JST, at commit `6eb5d40`.

## What happened

The full battery ran against a clean tree and reported:

```
FAILURES (1 of 34 suites):
  test_bm_handover.py: ---------------------------------------------------------------------- | Ran 34 tests in 0.809s | FAILED (failures=1)

test_all: 3057 tests across 34 suites, 5 skipped, 1055.3s wall. 1 SUITE(S) FAILED
```

Exit 1. One test of thirty four, and the gate collapses a suite's output to a
single line, so the assertion text was lost.

## What was tried, and what it showed

Run in isolation immediately afterwards, five times in a row:

```
run 1: OK
run 2: OK
run 3: OK
run 4: OK
run 5: OK
```

Thirty four tests, about 1.5 seconds each run. It will not reproduce.

The suite claims isolation and appears to have it: `tools/test_bm_handover.py`
line 7 states that nothing in it touches the real project, `setUp` builds a
`tempfile.mkdtemp` root and points `BROTHERMODE_ROOT` and
`BROTHERMODE_HANDOVERS_DIR` at it.

## The most likely cause, stated as a hypothesis rather than a finding

Two things were happening against this repository at the moment the gate ran
that suite, and either could plausibly perturb it:

1. A subagent working in a git worktree was running `bm_handover.py detect`
   and `sh tools/bm_sessionstart.sh` against the real tree, as part of the
   R1.3 wiring loop.
2. This session was claiming and rendering store records, which rewrites
   `STATE.md` and its backups.

Note the environment restore at `tools/test_bm_handover.py:278` to `282`: a
test sets `BROTHERMODE_ROOT` to an `empty_root` and restores it in what
follows. If an assertion inside that window ever raised before the restore
line, later tests in the same process would run against the wrong root. That
is a leak shape worth reading closely, and it is the first place to look.

## What is NOT claimed

The cause is unproven. This entry exists so the failure is on record with its
evidence rather than dismissed as noise, and so the next person who sees it
finds a second data point instead of starting over. It is not being called
fixed, and no test was weakened, skipped or marked expected-failure to get a
green gate.

## How to close it

Re-run the battery. If it passes with everything else unchanged, that
strengthens the flake reading and this file gains a second observation. If it
fails again on the same suite, run the gate with `--artifacts DIR`, which
writes the full output of every suite to disk, and read the actual assertion
rather than the collapsed line. That flag exists for exactly this and was not
used on the failing run, which is the practical lesson: a long gate run should
carry `--artifacts` by default, because a failure whose text is gone costs a
whole second run to recover.
