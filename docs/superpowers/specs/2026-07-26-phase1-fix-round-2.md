# Phase 1 fix round 2 (2026-07-26)

**HISTORICAL DOCUMENT, dated 2026-07-26. Do not read it as current state.** It is a dated working record: the plan, the verdicts, the blockers and the numbers in it belong to that day and were not updated afterwards. Items it calls open may since have been closed. Superseded by `README.md` and `docs/KNOWN-LIMITS.md` for status, `docs/NOT-FINALIZED.md` for the defect register, `CHANGELOG.md` for what changed since, and `python3 tools/bm_project_facts.py` for version, release tag, hook events and suites.

One defect, found by the orchestrator after the four-lens fleet returned, while
investigating an unrelated warning leaking from the V1 suite. It is the most
serious class this project has: a SUCCESS REPORT ON AN UNREGISTERED FENCE.

## GATE: a non-string path is silently dropped, and claim() still reports success

Reproduced (executed, orchestrator):

    s.claim('ctrl','ephemeral','obj',['api/ctrl.py'], session_id='s0')
    claims after STRING claim: ['api/ctrl.py']
    s.claim('t','ephemeral','obj',[pathlib.Path('api/pay.py')], session_id='s1')
    claims after PATH claim  : ['api/ctrl.py']        <-- nothing was added
    s.claim('other','ephemeral','obj',['api/pay.py'], session_id='s2')
    SECOND WRITER GRANTED api/pay.py: the fence was silently lost

claim() returned a Record (version 1, state active) for 't'. No exception, no
warning, no refusal. The record exists, holds NOTHING, and the file it was
supposed to protect is handed to the next writer that asks.

pathlib.Path is the single most likely wrong type a caller passes, because it is
what every modern Python caller already holds, and the V1 registry has the same
class of bug (visible as "Object of type PosixPath is not JSON serializable" in
the V1 suite output, where a save failure only warns).

## Required fix

1. Canonicalization accepts str and os.PathLike (call os.fspath), so a Path is
   handled correctly rather than dropped.
2. ANY other type, and any entry that cannot be canonicalized for any reason,
   raises OwnershipRefused with reason 'bad-path' naming the offending entry and
   its type. Silently dropping an entry from a fence is forbidden: the fence is
   the safety mechanism, and a partial fence reported as success is worse than a
   refusal (this is the project's own recorded lesson: a write whose return value
   is ignored will eventually report success it did not earn).
3. An empty files list stays legal (a record can exist without claims), but a
   NON-empty input that yields zero stored claims must raise, never return.
4. The same rule applies anywhere else user input becomes stored data.

## Required calibrated tests

- claim with [Path('api/pay.py')] stores exactly 'api/pay.py'; a second claim on
  that path from another session is refused 'name-active' or 'overlap'.
- claim with [123] or [None] raises OwnershipRefused 'bad-path' and creates NO
  record (check dump: the transaction rolled back).
- claim with ['ok.py', 123] raises and stores NEITHER path (atomicity).
- Calibrate: reinject the silent-drop behavior and confirm each test fails for
  its stated reason.
- A structural test asserting no claim-path code path can discard an entry
  without raising (for example, assert the canonicalizer is total: every input
  either returns a string or raises).
