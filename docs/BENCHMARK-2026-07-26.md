# Benchmark: today against yesterday's model

**HISTORICAL DOCUMENT, dated 2026-07-26. Do not read it as current state.** It is dated evidence: every number in it belongs to the day and the commit it was measured on. Superseded by `README.md` and `docs/KNOWN-LIMITS.md` for status, `docs/NOT-FINALIZED.md` for the defect register, `CHANGELOG.md` for what changed since, and `python3 tools/bm_project_facts.py` for version, release tag, hook events and suites.


The benchmark set is the external audit of version 1 at commit 60a6d0d, which scored
eight dimensions and an overall. Using its dimensions rather than inventing friendlier
ones is deliberate: a benchmark you choose after the work is not a benchmark.

Scoring rules applied to myself, from the law: a self-score caps at 8 unless external
validation is NAMED as evidence, and every claim states whether it is proven by command,
proven by inspection, or assumed.

Two columns for today, because one number would be dishonest. The V2 ENGINE is hardened.
The SYSTEM a user would install still runs the V1 tools, because the rewiring (Phase 3)
is not done. Reporting only the engine score would be the kind of flattery this project
exists to prevent.

| Dimension | V1 audit | System today | V2 engine alone | What moved it |
|---|---|---|---|---|
| Operating philosophy | 9.2 | 9.2 | n/a | Unchanged in substance, sharpened in one place: the learning target is now the founder model rather than the system's own scorecard, which is the founder's correction, not my idea |
| Engineering discipline | 8.1 | 8.5 | 8.5 | Eight rounds where every fix was reproduced by execution before it was written, fixes at class level with structural tests that enumerate the class from code or schema. External evidence: an independent code review confirmed the four ratified decisions hold in the code |
| Test discipline | 7.8 | 8.0 | 8.0 | Honest split: the V2 suite is mutation-audited, and that audit found 24 tests that could never fail, which were deleted. The count fell from 194 to 182 and the calibrated count is 104 (re-measured later the same day, 2026-07-26, after Phase 3 added thread-mode coverage: 189; see the runnable check below). External evidence: a systematic mutation audit that killed 19 tests with one broken function |
| Correctness and concurrency | 6.3 | 6.3 | 8.5 | Engine: 21 reproduced defects closed, including silent fence takeover, resume walking over another session's lock, and a percent sign in a path opening another project's database. System: UNCHANGED, because the tools that run still use the V1 registries |
| Recovery and durability | 5.8 | 8.0 | 8.0 | Rebuilt in Python and verified BY MY OWN HAND, not by report: a snapshot taken from a subfolder now captures root files, a tracked .env survives in the snapshot (the defect that deleted a real file on restore), refs are namespaced per worktree and session so two projects cannot overwrite each other's only backup, and with no store present it warns once and exits 0. 14 tests, 7 of them calibrated by reinjecting the old behavior. The in-place restore path is DELETED, not documented with a warning. Held below 9 because Windows was unverified, and CORRECTED 2026-07-26: CI has now run and FAILED on Windows for an unclosed database handle, so this row is re-opened rather than banked |
| Security and privacy | 6.6 | 8.0 | 8.0 | The no-network claim now has a mechanical gate, calibrated both ways, where before it was a command a reader was expected to run by hand. Redaction inverted to default-deny with a test that reads the schema itself. Store documented as the raw sensitive artefact |
| Production readiness | 5.9 | 6.8 | 6.8 | Moved by a quickstart an agent EXECUTED rather than described (finding three documentation defects while doing it: the hook count was wrong, a zero-failures claim was false, and the suite's real runtime is 4.5 minutes), plus a limits file, a whitepaper, and a three-platform CI matrix with pinned actions. CORRECTED 2026-07-26: CI HAS executed (18 runs) and FAILS on Windows; a tagged release now exists (v2.0.0-rc.1); the engine IS wired. Held down by the live Windows failure rather than by the absence of evidence |
| **Overall** | **7.2** | **8.0** | **8.2** | Verified by command where the numbers are counts and gates; the dimension scores are proven by inspection with external review named where it exists |

## Where the remaining gap actually is

7.2 to 8.0 on the system, and the two columns are now nearly equal, because recovery was
the one dimension where a fix reached the tools a user actually runs. The autosave was
never part of the unwired engine: it runs on a hook today, so rebuilding it improved the
real system rather than a component in waiting.

The remaining 0.2 between system and engine is Phase 3, the rewiring. Correctness at the
system level is still 6.3 and will stay there until the running tools stop using the V1
registries. That is the honest shape of it: recovery moved because it shipped, and
correctness did not because it has not.

## What would move each remaining number, concretely

- Correctness at system level to the engine's number: Phase 3 rewiring, which also
  deletes 1,668 lines of the V1 tools and should bring the size figure down.
- Production readiness above 7: CI actually running green on three platforms, and a
  tagged release with checksums replacing the current instruction to clone a moving
  branch into code that auto-runs every session.
- Test discipline above 8: an automated mutation harness in CI rather than a mutation
  audit run once by hand, so the calibration claim keeps earning after today.

## The founder-legible check, runnable in under a minute

`cd` into wherever you cloned this repository, then:

```bash
python3 tools/test_bm_store.py 2>&1 | tail -3
```

Expect `Ran 189 tests` and `OK` (measured 2026-07-26; the table above says
182, an earlier count from the same day, before more tests were added the
same day. Re-measure rather than trust either number if it drifts further).
Then this, which should print nothing at all, because it proves the tool
makes no network calls:

```bash
grep -rnE "^\s*(import|from)\s+(urllib|socket|requests)" tools/*.py
```

**Snapshot note, added later on 2026-07-26 while correcting this page:** the
rows above describing "the tools that run still use the V1 registries"
predate Phase 3, which landed later the same day and deleted
`bm_registry.py`. For the current status, including new defects the Phase 3
rewiring itself introduced, read `docs/KNOWN-LIMITS.md` rather than this
dated snapshot.
