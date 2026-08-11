# Defect: test_bm_handover.py failed once inside the gate and will not reproduce

Status: CLOSED 2026-08-12 03:35 JST. It was never a flake.

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


---

# CLOSED: it was a real bug, and the artifacts flag found it in one run

Added 2026-08-12 03:35 JST, after the failure recurred on the next gate run.
That run carried `--artifacts`, which is the process fix this file itself
recommended an hour earlier, and it produced the assertion the first run had
swallowed:

```
FAIL: test_f9_same_content_resave_does_not_deadlock_the_ceremony
  File "tools/test_bm_handover.py", line 519, in ...
    self.assertIn("unchanged", out.lower())
AssertionError: 'unchanged' not found in 'wrote /var/.../brothermode-handover-2026-08-11-closeit.zip (7 file(s))\n'
```

## The mechanism, proven rather than reasoned

Finding F9 had already moved the zip freshness check OFF the pack
directory's mtime and ONTO the archive's bytes, on the reasoning that bytes
are content and mtimes are not. That reasoning is true of a plain file and
false of a zip. A zip entry header stores each member's modification time, so
`zf.write(path, arcname=...)` bakes the file's mtime into the archive. An
editor or formatter re-saving a file with byte-identical content still moves
that mtime, and once it crosses one of the MS-DOS format's two second
boundaries, the archive's bytes change with nothing to show for it.

Demonstrated directly, one file, contents untouched:

```
content identical, mtime +2s
hash before: f57bd6d9d8a0b6b7
hash after : 81083a89832866a1
DIFFERENT -> True
```

The existing F9 test re-saves after a `time.sleep(0.05)`, so it crosses a two
second boundary roughly one run in forty. That is why it failed twice inside
long gate runs and passed five times in a row in isolation. The hypothesis in
the section above, about a `BROTHERMODE_ROOT` restore leak at lines 278 to 282,
was WRONG. It is recorded rather than deleted, because a wrong hypothesis that
was written down is cheaper for the next person than one that was not.

## The fix

`tools/bm_handover.py` gains `_content_fingerprint`, `_pack_content_fingerprint`
and `_zip_content_fingerprint`. Both comparison sites, the idempotence branch
in `cmd_zip` and the freshness check in `verify-close`, now compare a hash of
(archive member name, member bytes) pairs, sorted, and nothing else. An archive
that cannot be read as a zip fingerprints as `None`, which never equals a real
pack, so a corrupt archive fails rather than passing by being unparseable.

## The proof

Two new tests, and the first is deliberately DETERMINISTIC where the original
was probabilistic. It moves the mtime forward by exactly two seconds with
`os.utime`, which lands a different DOS timestamp every single run:

- `test_f9b_resave_across_a_two_second_boundary_is_still_unchanged`
- `test_f9b_a_real_content_change_is_still_caught`

The second exists because making a check ignore timestamps must not make it
ignore changes. Shown failing before the fix and passing after, by stashing
only `tools/bm_handover.py`:

```
$ git stash push -- tools/bm_handover.py
$ python3 tools/test_bm_handover.py TestVerifyClose.test_f9b_resave_across_a_two_second_boundary_is_still_unchanged
Ran 1 test in 0.040s
FAILED (failures=1)

$ git stash pop
$ python3 tools/test_bm_handover.py
Ran 36 tests in 1.035s
OK
```

## What this cost, and the lesson already applied

Two full gate runs, about thirty five minutes, to recover an assertion the
first run had already produced and discarded. `--artifacts` existed the whole
time. It is now the default for any long gate run in this repository, written
into the pack's own process fixes as PF-2.

The other lesson is about the word flake. Calling it one and moving on would
have left a real defect in the tool that gates every session close, in the
exact code path a previous finding had already tried to fix once.
