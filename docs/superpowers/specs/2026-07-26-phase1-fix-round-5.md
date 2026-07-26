# Phase 1 fix round 5 (2026-07-26)

From refute round 4 (fresh code confirmed: all four lenses quoted "Ran 139 tests, OK"
before testing). The calibration lens returned CLEAN: every calibrated test failed
correctly under its reinjected defect. Two gates and five soft items remain.

## GATE A: a reclaim without files silently empties the fence (VERIFIED BY ORCHESTRATOR)

Reproduced:

    claim alpha --objective "ship payments" --session s1 --files api/pay.py api/refund.py
    claims: ['api/pay.py', 'api/refund.py']
    claim alpha --objective "revised objective" --session s1        (no --files)
    claimed 'alpha' ... (version 2, session s1)      exit 0
    claims now: []                                   <-- the fence is gone
    claim beta --files api/pay.py --session s2       -> GRANTED

Updating an objective silently drops every file the record was protecting, and reports
success. This is the same silent-success class as rounds 2 and 4, now in the reclaim
path: the caller said nothing about files, so the code decided that meant "no files".

Fix: distinguish "not supplied" from "supplied as empty". files=None (the CLI omitting
--files) LEAVES the existing claims untouched. files=[] (an explicit empty list) is a
deliberate release and is allowed. Both the API default and the CLI must express this;
the CLI needs an explicit way to say "release my files" (for example --files with no
values, or --release-files), and it must be impossible to release them by accident.
Calibrated test: reclaim without files preserves the fence; another session is still
refused afterwards.

## GATE B: only the store DIRECTORY is containment-checked, not the store FILE

A symlinked .brothermode is correctly refused 'path-escape', but a symlinked
.brothermode/store.sqlite3 is never checked, so the raw database is written outside the
project (reproduced: committed into git via docs/leak.sqlite3 carrying a secret).

Fix: apply the same realpath containment rule to the store file, its sidecars, and the
quarantine target, not just the directory. Test with a symlinked store file.

## GATE C (reclassified from soft, and it is my authoring error): dump prints raw secrets

cmd_dump prints every objective, decision, and digest unredacted. A test asserts this
deliberately, because MY round-2 instruction said "dump is the raw export". The design
spec says redaction applies at every exit, so the spec and my instruction disagree, and
the spec wins.

Resolution: dump redacts BY DEFAULT like every other exit. Raw export requires an
explicit `--raw` flag whose help text says it prints secrets in cleartext. Update the
test that asserted the old behavior (this is a corrected model, not a weakened test:
record the reason in the test's docstring). The reason default-raw is wrong: dump is
exactly what a founder pipes into a file, a paste, or an issue.

## SOFT D: newline injection forges records in the generated view

Marker strings are neutralized but newlines are not, so an objective or claim path
containing newlines fabricates a complete counterfeit record block inside STATE.md,
indistinguishable from a real one, while verify reports healthy. Fix: in generated
views, collapse or escape newlines (and other line-structure characters) in every
founder-typed field. Test: a forged block does not appear.

## SOFT E: terminal control characters reach the terminal

An objective containing ANSI escapes reaches the dashboard verbatim and can erase
another record's line on a real terminal ("HIJACKED: no other work exists" reproduced).
valid_name already rejects non-printable characters; free-text fields have no equivalent
gate. Fix: strip or escape control characters in every emitted field.

## SOFT F: the corruption message names a command that refuses to run

StoreCorrupt says to run `bm_store.py init`, but init now refuses without
--acknowledge-quarantine, so following the printed instruction fails. Fix the message to
name the command that actually works, and add a test asserting the recovery instruction
is executable (a message-versus-behavior test, since this class of drift is invisible to
normal assertions).

## SOFT G: overlap refusals print claim paths unredacted

The same path string is redacted in the dashboard and printed raw in the overlap refusal.
Fix: route it through the same redaction, keeping enough of the path to be actionable.

## Note on convergence

Gate counts by round: 9, then 4, then 2. Findings are narrowing from structural defects
to injection and consistency edges, which is the expected shape. The bar stays two
CONSECUTIVE clean rounds against identical code.
