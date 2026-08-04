# L02 close: the signed autonomy contract

Status: CURRENT as of 2026-08-05.

Loop L02 of the Absolute program (equally U1 of the unified plan) is the
mechanical autonomy contract: an immutable, signed, revision-chained record
that says what an autonomous run is allowed to do, checked before every
action, with the five safety floors ranking above it always. This closes
finding P0-01's first half (an autonomy contract that exists in code and can
be consulted); the controller that consumes it is L03.

## What landed

- Schema 13 to 14: six autonomy tables (contract revisions, assumptions,
  interruptions, spend, human steps, checkpoints), an additive
  forward-only migration `_migrate_13_to_14` following the house backup
  pattern, and the schema-behind and schema-ahead refusals extended to 14.
- Immutability by revision chain: `UNIQUE(project_id, revision)`, insert
  only, no UPDATE path. Two live contracts for one project are not merely
  refused, they are unrepresentable, and `gate-check` returns the exact
  revision it judged against, which is the staleness signal L03 needs.
- Fourteen commands in `tools/bm_autonomy.py`, a thin CLI over the store
  with the no-SQL structural guard: sign, show, gate-check, assume,
  interrupt, spend, pause, resume, stop, revoke, status, queue-human-step,
  human-steps, checkpoint.
- The five non-grantable floors rank above the contract; a floor smuggled
  through a custom or misspelled risk class is refused.
- Missing ceilings surface as NO-DATA, never a silent zero or unlimited;
  the 80 and 100 percent thresholds compute the documented stops.

## Evidence

- RED, SPEC, VERIFY, REFUTATION alongside this file record the failing
  reproduction, the decision-complete design, the command output, and the
  independent security refutation.
- Store suite `tools/test_bm_store.py`: 756 tests, OK (was 703).
- Autonomy suite `tools/test_bm_autonomy.py`: 58 tests, OK.
- Security refutation: STANDS. 95 exploit attempts across eight angles
  (authorization bypass, immutability, signer check, ceilings, migration,
  injection, purge, audit), zero bypasses. One LOW overflow nit found and
  fixed here (a spend or ceiling at or beyond the signed 64 bit maximum is
  now a clean usage refusal, exit 2, not a raw OverflowError), with two
  tests pinning it.
- Full gate result is recorded in the commit that regenerates the manifest.

## Honest limits, carried into docs/KNOWN-LIMITS.md and docs/AUTONOMY.md

- The model-cannot-sign check is a denylist of about thirty tokens. It
  catches the accidental case; a model signing as a plain human name or a
  misspelling is accepted, and a test asserts those bypasses are accepted
  so the check is never read as stronger than it is.
- `gate-check` enforces path scope only when the caller passes a path. It
  answers, it never blocks. Passing a path on every path-bearing action is
  an obligation on the controller, L03.
- A symlink created after signing is resolved at gate-check time, a TOCTOU
  window U1 does not close; closing it needs an operating-system write
  mediator, which the project records as out of scope.

## Score

Per the Absolute rubric, D2 moves toward its target on the strength of a
contract that exists and is tested (evidence level E3, deterministic tests
with failure cases). It does not reach the full-auto completeness target
until L03 ships the controller that drives it and produces an E4 end-to-end
artifact. No score is claimed beyond the evidence.
