# Phase 1 fix round 6 (2026-07-26)

**HISTORICAL DOCUMENT, dated 2026-07-26. Do not read it as current state.** It is a dated working record: the plan, the verdicts, the blockers and the numbers in it belong to that day and were not updated afterwards. Items it calls open may since have been closed. Superseded by `README.md` and `docs/KNOWN-LIMITS.md` for status, `docs/NOT-FINALIZED.md` for the defect register, `CHANGELOG.md` for what changed since, and `python3 tools/bm_project_facts.py` for version, release tag, hook events and suites.

From refute round 5 (fresh code confirmed, 156 tests quoted). Four gates, four soft.

READ THIS FIRST. Round 5 fixed "not supplied is not empty" for `files` and left the
identical bug in `objective`. That is this project's most expensive recurring failure
(fix the instance, leave the class) and it is why two of the gates below exist. Every fix
in this round must end with a SWEEP over the whole class and a STRUCTURAL test that makes
the next member of the class fail the suite instead of shipping.

## GATE A: a percent sign in the project path opens ANOTHER project's database (VERIFIED BY ORCHESTRATOR)

Reproduced: two sibling projects, pA and p%41. Standing inside p%41:

    dump      -> ['victimwork']                      (pA's record)
    dashboard -> objective: PRIVATE-PROJECT-A-OBJECTIVE   (pA's private text)

Cause: the read-only path is opened through a sqlite URI that escapes only ? and #, so
sqlite percent-decodes the rest and resolves a different file. Every read-only exit is
affected (dump, dashboard, verify, write_state_view), and verify calls the wrong store
healthy while the real one is invisible.

Fix, structurally rather than by adding % to the escape list: do not build URIs at all.
The no-store check already proves the file exists, so open the plain path with
sqlite3.connect(path) and enforce read-only with `PRAGMA query_only = ON`. That removes
the entire URI-escaping bug class instead of its current instance. Verify query_only
actually refuses a write in a test (attempt an INSERT, expect an error).
Calibrated test: two sibling projects whose names differ only by percent-encoding, each
holding a distinct record, and each command reports only its own.

## GATE B: a bracket or star in the project path disables the quarantine gate

_find_quarantine_dirs interpolates the root into glob.glob unescaped, so in a project
whose path contains [ ] * or ?, an outstanding quarantine is invisible: init silently
creates a fresh empty store over a real data loss and verify reports healthy.

Fix: stop using glob for this. List the directory with os.listdir and match by prefix.
Same reasoning as GATE A: delete the pattern language rather than escape it.
Calibrated test: a project directory literally named p[1].

## GATE C: the default dump still prints secrets, in the fields nobody listed

dump redacts objective, tier, claim paths, decisions and digests, and prints
transitions.note, directives.text, records.evidence, records.check_cmd and owner in
cleartext. The existing test only ever planted a secret in objective, which is why the
gap survived a round that was specifically about redaction.

Fix by inversion: redaction becomes DEFAULT-DENY. Enumerate the fields that are
structurally non-sensitive (ids, uuids, states, lifetimes, versions, counts, timestamps,
booleans) and redact every other text value on the way out. Adding a new text column must
therefore be redacted automatically.
Structural test: for EVERY text column in the schema, plant a secret-shaped token, run
the default dump, and assert the token does not appear. Enumerate the columns from the
schema itself so a new column joins the test automatically.

## GATE D: a reclaim that omits the objective silently erases it

The exact class fixed last round for files, left open for objective (executed: reclaim
with only --tier sets objective to empty, exit 0, unrecoverable).

Fix: apply the None-versus-empty rule to EVERY updatable field: objective, tier,
check_cmd, ttl_hours, owner. Not supplied leaves the stored value untouched; supplied
empty is a deliberate clear.
Structural test: enumerate the updatable fields, and for each, assert a reclaim that
omits it preserves the stored value. A newly added field must be added to that list or
the test fails.

## SOFT E: adopt bypasses the not-owner check

A second session cannot claim or park a live owner's record, but CAN adopt it and then
re-claim the name, in two exit-0 commands. Adoption of a genuinely dead session is
legitimate and its full UX belongs to Phase 3, so for now: require an explicit
--adopt-from-live-session flag when the target session differs from the caller's and the
record is active, print who is being displaced, and record the displacement in the
transitions note. Silent takeover is not acceptable even when the operation is legal.

## SOFT F: warnings on stdout make the export unparseable

dump writes its warnings to stdout, so a redirected export is not valid JSON.
Fix: every advisory or warning line goes to stderr; stdout carries only the payload.
Test: redirect stdout of dump and json.load it successfully while a quarantine warning is
outstanding.

## SOFT G: the gitdir pointer is still unvalidated (open since round 4)

A crafted .git file makes the tool create directories and append exclude lines at an
arbitrary path. Fix: resolve the pointer, and refuse (path-escape) unless the target
realpath contains the expected repository administration layout and is not being created
from scratch by us. Never create a directory tree at a location a .git file named.

## GATE H (calibration): a calibrated test that cannot fail

test_calibrated_gateB_quarantine_target_collision_refused stays green when
exist_ok=False is flipped to exist_ok=True, because its sentinel file is named PRIOR
rather than store.sqlite3, so it never exercises the same-basename overwrite the guard
exists to prevent. Fix the test to use the real filename and re-calibrate it.
