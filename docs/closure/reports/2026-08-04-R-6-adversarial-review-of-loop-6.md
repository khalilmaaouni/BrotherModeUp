# Adversarial review of Loop 6, and the generalization wave it forced, R-6, 2026-08-04

Status: CURRENT as of 2026-08-04.

The handover left Loop 6 fixed but unreviewed. This report records the review
(two independent refuters, per the plan of record) and the fix wave the review
forced. Full working transcripts live with the session that ran them; every
claim below names the command that produced it, and each was re-run by the
orchestrator rather than trusted from a pasted line.

## Review setup

- Reviewer A (correctness lens): verify each of the eleven N-6 fixes is real,
  calibrated against a pre-fix tree assembled OUTSIDE the repository with
  `git archive 2327746` plus `git show ebc11e8:tools/bm_telemetry.py`, so the
  post-fix tests could be shown failing on pre-fix code.
- Reviewer B (adversarial lens): try to REFUTE the closure with crafted
  inputs, run against a COPY of bm_telemetry.py in a scratch directory with
  HOME and BROTHERMODE_VAULT pinned there, never against a real store.
- Neither reviewer edited anything: `git status --porcelain` empty at start
  and end of both sessions, at HEAD 717b0ae.

## Verdicts

Reviewer A: all eleven N-6 findings CONFIRMED-FIXED. Twelve of the fourteen
new tests fail on the pre-fix tree (the two that do not are consent-gate
tests whose defect predates the pre-fix snapshot, explained in the session
report). The suite read `Ran 256 tests`, `OK`, exit 0.

Reviewer B: closure REFUTED. Eleven real fixes, but the generalization step
was never taken. Nine new findings, two of them reproducing the headline
catastrophe exactly:

| # | Severity | Defect |
|---|---|---|
| 1 | Critical | sub_out_tokens, cache_read, cache_write, duration_h read raw; a null in any collapses scorecard, speed or startup-nags |
| 2 | Critical | a valid-JSON non-object ledger line (bare null, number, string, array) collapses five commands including both repair commands |
| 3 | High | the blanket never-block handler amplifies any such defect into a one-line total loss |
| 4 | Medium | measured counted key presence, not a real numeric value |
| 5 | Medium | rows with unreadable timestamps silently vanish from window math |
| 6 | Medium | future-dated rows counted in scorecard undisclosed (speed disclosed, scorecard did not) |
| 7 | Medium | present-but-unusable token fields silently coerced to zero |
| 8 | Medium | scorecard averaged ratings the write path is built to refuse (boolean, negative, out of range, fractional) |
| 9 | Low | duration_h silently zeroed on unparseable transcript timestamps |

The strongest reproduction: one ledger line containing the four characters
`null` disabled scorecard, speed, startup-nags, migrate and dedup, all at
exit 0, ledger bytes unchanged.

## What landed, commit 00b54bf

Findings 1, 2, 4, 5, 6, 7 and 8 fixed test-first: nineteen new tests, each
shown failing before its fix. `tools/test_bm.py` moved from 256 to 275 tests.
One deviation, judged and disclosed: read_jsonl could not be narrowed in
place because tools/bm_learn.py legitimately counts non-object lines, so
bm_telemetry gained read_records() (objects only) while read_jsonl kept its
contract for its other callers.

Deferred by design, registered in docs/NOT-FINALIZED.md entries 25 to 29:
the blanket handler itself (finding 3; per-metric isolation is a refactor
and a founder call), duration_h write-side zeroing (finding 9), the two
Loop 6 suggestions that previously lived only in the dated B-6 report, the
consent-inventory gap for commands wired from tools/bm_sessionstart.sh, and
the read_jsonl into read_records split.

## The corruption-message fix, commit cafe1da

The handover's open item 6 (a schema skew reported as STORE CORRUPT) was
specced by a read-only investigator and landed test-first in the same wave:
the two structurally-healthy refusals now raise OwnershipRefused with
literal reason codes (schema-behind, schema-ahead), exit 2 instead of 1,
and STORE CORRUPT is reserved for genuine damage. The session-start
surfacing grep gained the refused (schema- alternative so the refusal stays
visible. The previously uncovered bm_threads dashboard path turned out to
swallow the old exception entirely at exit 0; it now has a test.
`tools/test_bm_store.py` moved to 703 tests, `tools/test_bm.py` to 276.

## Verification after the last edit in this wave

- python3 tools/test_bm_store.py: Ran 703 tests, OK, exit 0.
- python3 tools/test_bm.py: Ran 276 tests, OK, exit 0.
- python3 tools/test_bm_docs.py: Ran 137 tests, OK, exit 0.
- The full serial gate result for this tree is recorded in the commit that
  regenerates the manifest, run after that commit's last edit.

## What this review did not cover, stated plainly

Reviewer B's own not-checked list stands: parse_transcript was not attacked
with a malformed transcript, concurrency and torn-line scenarios were not
exercised, file-permission tightening was not verified, the 34 other files
in tools/ got only a grep-level sweep, and reachability of a null through a
real writer path rests on a parity argument with the field the project
already accepted as reachable. scripts/doctor.py still reports FAIL, in
better words, for a healthy schema-skewed store (NOT-FINALIZED entry 30).
