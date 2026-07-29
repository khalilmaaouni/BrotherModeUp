# Phase 1 fix round 8 (2026-07-26): the review round

**HISTORICAL DOCUMENT, dated 2026-07-26. Do not read it as current state.** It is a dated working record: the plan, the verdicts, the blockers and the numbers in it belong to that day and were not updated afterwards. Items it calls open may since have been closed. Superseded by `README.md` and `docs/KNOWN-LIMITS.md` for status, `docs/NOT-FINALIZED.md` for the defect register, `CHANGELOG.md` for what changed since, and `python3 tools/bm_project_facts.py` for version, release tag, hook events and suites.

From an independent senior code review and a systematic test-mutation audit, both
run against the current branch. These found what six adversarial rounds did not,
because they were pointed at different things: the reviewer at the contract and the
architecture, the mutation audit at whether the tests can fail at all.

## CRITICAL A: a damaged schema is silently rebuilt and reported healthy (VERIFIED BY ORCHESTRATOR)

Reproduced:

    claim alpha --files api/pay.py --session s1     -> version 1
    (drop the claims table, simulating partial corruption)
    claim beta  --files api/pay.py --session s2     -> GRANTED, exit 0
    verify                                          -> healthy, 0 problem(s)

The DDL runs unconditionally on every open with CREATE TABLE IF NOT EXISTS, and the
stored schema_version is read and then discarded, never compared. So a store whose
claims table is gone is silently rebuilt empty, two sessions fence the same file,
and the health check says everything is fine. This is the F9 class and the
double-fence class re-entering through the schema door, and it breaks ratified
Decision 4 (corrupt state is quarantined and refused, never silently replaced). The
zero-byte guard covers the whole-file case; the per-table case is wide open. A
schema migration in Phase 2 or 3 is the realistic trigger.

Fix: run DDL only when the file did not exist before this open. On an existing
store, verify every expected table is present and schema_version equals the
expected value, and quarantine on mismatch. Calibrated test per failure mode:
missing table, unexpected schema_version, and a healthy store still opening
normally.

## CRITICAL B: the quarantine test does not test what it claims (mutation audit)

test_calibrated_8 asserts the quarantine DIRECTORY exists, which os.makedirs
creates before anything is moved into it, and that the original path is gone, which
deletion satisfies just as well as a rename. Two mutations survived it: replacing
the move with a delete, and quarantining only the sidecars while unlinking the main
store. Both destroy exactly the bytes the whole mechanism exists to preserve.

Fix: assert the quarantined FILE exists inside the directory and that its content
equals the pre-quarantine bytes, for the main store and each sidecar. Re-calibrate
against both surviving mutations.

## CRITICAL C: fifteen calibrated tests test a copy of the old code, not the product

Every test named test_calibrated_reinject_* defines a local copy of the pre-fix
function and then asserts that copy misbehaves. None of them can fail from a
regression in the shipped module. They inflated the calibrated count while
protecting nothing, which is precisely the calibration theatre this project has a
law against.

Fix: DELETE them. A reinjection test earns its place only by patching the PRODUCT
symbol (monkeypatching the real function on the module) so that a regression in
shipped code fails it. Where a genuine mutation test is wanted, write it against
the product symbol and prove it fails when the guard is removed. Report the honest
count afterwards: fewer real calibrated tests beats a larger fictional number.

Also fix these, each named by the audit as passing for the wrong reason:
- the dotdot name test survives deleting its own guard (the leading-dot rule
  catches it incidentally): assert the specific refusal reason, not just ValueError
- the stale-version test survives removing the pre-check (the UPDATE guard catches
  it): acceptable coupling, but say so in the docstring rather than implying the
  pre-check is what is tested
- the no-bare-execute test asserts a magic count of 15 call sites: assert the
  property (every call site is inside the helper), not the number
- the resume test asserts a value equals itself: assert what actually changed

## IMPORTANT (code review)

1. Every OperationalError is reported as "busy or locked, wait and retry", so a
   missing table prints advice that can never work and hides CRITICAL A. Classify:
   busy and locked keep that message, everything else says what actually happened.
2. checkpoint and decide bump the version but return only seq, and neither the CLI
   nor the dashboard prints it, so the founder's next command fails stale-identity.
   Print the new version everywhere it changes.
3. ttl_hours cannot be cleared: the None-versus-empty rule from round 6 was applied
   to the other updatable fields but not this one.
4. Three docstrings now contradict the code (dump described as never redacting, cwd
   described as defaulting to os.getcwd). In a file where comments are the contract,
   a wrong comment is a defect.
5. verify's view check is a substring test, so a short record name passes
   vacuously. Match the rendered line, not any occurrence.

## SPEC GAPS (mine, recorded rather than quietly patched)

- send() has no expected_version, making directives the one unversioned mutation.
  Phase 3 owns the directive UX; record the gap there rather than inventing a fix
  here.
- The deliveries table and the full-length fingerprint ship with NO writer, so the
  deduplication the fingerprint exists for does not exist yet. Phase 3 owns handover
  delivery. Either write it there or drop the table; do not leave it as decoration.
- Round 4 mandated a read-only sqlite URI and round 6 forbade URIs entirely. The
  code correctly follows round 6. Record the supersession in round 4's file so a
  future reader does not restore the defect.

## SIMPLIFICATION (founder value, and the file is now 2,682 lines)

Measured: 846 of 2,682 lines (32 percent) are comment or docstring, much of it
provenance narrating which fix round landed which change. That history lives in git
and in eight spec files already.

Do now, zero risk: strip fix-round provenance from comments, keeping the WHY and
citing the spec once per section; delete the dead conn parameter threaded through
four methods and the unused to_dict. Expected reduction: 300 to 400 lines.

Defer to Phase 3, deliberately: splitting the module (paths and root and names as
their own dependency-free unit, then store, views, CLI). Phase 3 rebuilds the
command surface anyway, so the split lands there instead of being done twice. Note
the reviewer's point that round 7's structural test would be enforceable by module
boundary rather than by source scan after the split.
