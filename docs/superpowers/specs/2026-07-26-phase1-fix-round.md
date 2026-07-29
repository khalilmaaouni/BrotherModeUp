# Phase 1 fix round, from the four-lens refutation (2026-07-26)

**HISTORICAL DOCUMENT, dated 2026-07-26. Do not read it as current state.** It is a dated working record: the plan, the verdicts, the blockers and the numbers in it belong to that day and were not updated afterwards. Items it calls open may since have been closed. Superseded by `README.md` and `docs/KNOWN-LIMITS.md` for status, `docs/NOT-FINALIZED.md` for the defect register, `CHANGELOG.md` for what changed since, and `python3 tools/bm_project_facts.py` for version, release tag, hook events and suites.

This is a spec amendment. It is the contract for the next fix round on
tools/bm_store.py and tools/test_bm_store.py. Every item below was reproduced by
executing commands, not by reading. Items marked VERIFIED BY ORCHESTRATOR were
additionally re-reproduced by hand before this file was written.

Every fix lands with a CALIBRATED test: reintroduce the defect, confirm the new
test fails for the stated reason, restore, confirm green. A fix without that
calibration is rejected back.

## GATE 1: path canonicalization is the root of four separate defects

Reproduced: `paths_overlap('db.py', 'api/../db.py')` is False (VERIFIED BY
ORCHESTRATOR); a claim from a subdirectory stores 'pay.py' while the root stores
'api/pay.py' and both win; absolute paths are stored verbatim (leaking personal
paths into dump and dashboard); `paths_overlap('.', 'api/pay.py')` is False.

Fix: ONE canonicalization function, applied at every entry point where a path
enters the store (claim, and any future API taking paths). It must:
1. Accept an optional caller cwd (default os.getcwd()); resolve the path against
   that cwd when relative, so a subdirectory caller and a root caller produce the
   same stored string.
2. Reject (OwnershipRefused reason 'path-escape') any path that resolves outside
   the canonical root, including via '..' and via symlinks (compare
   os.path.realpath of the parent chain against realpath(root)).
3. Store the result as a root-relative POSIX string with '.' and '..' segments
   resolved via posixpath.normpath. The empty result (the root itself) normalizes
   to '.' and MUST overlap everything.
4. Glob paths keep their wildcard segments but their literal prefix is
   canonicalized the same way.

## GATE 2: case folding must never rewrite separators (Windows)

Reproduced: with ntpath.normcase substituted (what os.path.normcase IS on
Windows), `paths_overlap('api', 'api/pay.py')` is False (VERIFIED BY
ORCHESTRATOR). The engine would ship broken on the platform the founder ratified.

Fix: do NOT use os.path.normcase for comparison. Case-fold with str.lower() (or
casefold) applied to the POSIX-form string, gated on platform case-insensitivity
(win32 and darwin true, otherwise false), so separators are never touched. Test
must force sys.platform for all three platforms AND substitute ntpath.normcase to
prove the module never depends on it.

## GATE 3: an empty session id must never match another empty session id

Reproduced end to end (VERIFIED BY ORCHESTRATOR): two independent CLI processes
both claim 'payments'; the second replaces the objective, deletes the first
session's claim rows, exits 0. This IS the original F3 defect back through the
CLI door.

Fix: an empty or missing session id NEVER matches an existing record's session id.
The same-session reclaim branch requires a non-empty session id equal to the
stored one. The CLI generates a stable per-process session id when --session is
absent (for example 'cli-' plus uuid4 hex), so two processes can never collide,
and prints it on refusal so a human can see who holds the fence. Refusal reason
stays 'name-active' with the holder's lifecycle uuid.

## GATE 4: corruption outside the constructor probe must still quarantine

Reproduced: damage a later page, and Store() opens fine while claim, dump and
verify raise raw sqlite3.DatabaseError; nothing is quarantined; the CLI exits 1
with a driver traceback.

Fix: route EVERY sqlite call through one internal helper that applies the ratified
failure split (OperationalError refuses 'db-busy', other DatabaseError
quarantines and raises StoreCorrupt). No bare cursor calls outside it.

## GATE 5: quarantine must not destroy the data it claims to preserve

Reproduced: (a) two quarantines inside one second collide and os.replace destroys
the first; (b) the -wal and -shm sidecars are left behind and a data-bearing WAL
is zeroed by the failed open, so the quarantined file contains none of the lost
records.

Fix: quarantine moves store.sqlite3 AND its -wal and -shm sidecars, into a
per-incident directory named store.quarantine-<UTC to microseconds>-<uuid4[:8]>,
created with os.makedirs(exist_ok=False) so a name can never be reused. Never
os.replace onto an existing path. The raised message names the directory.

## GATE 6: resume must refuse, not crash, when the name was re-taken

Reproduced: resuming a parked record whose name is now held raises raw
sqlite3.IntegrityError and exits 1 (the corruption code) where the contract says 2
(refusal).

Fix: catch IntegrityError on the unique index and raise OwnershipRefused reason
'name-active' naming the current holder. Exit code 2.

## GATE 7: the store must protect itself without waiting for init

Reproduced: any command creates .brothermode/store.sqlite3, but only init writes
the .git/info/exclude entries, so a routine `git add -A` committed a store holding
'password=hunter2' in cleartext.

Fix: creating the store directory ALSO ensures the exclude entries (same
idempotent function init uses) whenever a .git directory exists. Additionally,
chmod 0700 the .brothermode directory and 0600 the store, the sidecars, and every
quarantine artifact, best-effort inside try/except (Windows may ignore it; say so
in the docstring, do not claim what the platform will not honor).

## GATE 8: redaction must cover every emitted field, and text must not break the view

Reproduced: tier and claim paths reach STATE.md and the dashboard unredacted
(secret-shaped tokens visible); an objective containing the literal END marker
escapes the generated block and STATE.md grows an extra marker on every render.

Fix: (a) redact EVERY founder-typed field at every exit, including tier, claim
paths, check_cmd, evidence, and transition notes if they ever render; (b) before
writing generated content, neutralize any occurrence of the BEGIN and END marker
strings inside that content (replace with a visibly escaped form), and assert in a
test that N renders leave exactly one BEGIN and one END marker.

## GATE 9: the CLI must not misclassify an encoding failure as bad input

Reproduced: with a non-UTF-8 stdout, a non-ASCII name prints 'refused
(bad-input)' and exits 2 AFTER the record was already created, and a genuine
refusal crashes uncaught with exit 1. Root cause: UnicodeEncodeError is a
subclass of ValueError, so the ValueError handler swallows it.

Fix: restrict names to printable ASCII (reject control characters, including NUL,
and reject non-ASCII) with a clear reason; catch UnicodeEncodeError explicitly
BEFORE ValueError; and write CLI output through a helper that encodes with
backslashreplace so an exotic objective can never turn a success into a
misreported refusal.

## SOFT 10: cross-session park is a silent takeover path

transition() gates on state and version but not ownership, so any caller holding a
lifecycle uuid (printed by dump) can park another session's record and then claim
its name. Fix: transition refuses reason 'not-owner' when the record's session id
is non-empty and differs from the caller's, EXCEPT for the adopted transition
(adoption of a dead session is the legitimate cross-session path and stays
allowed, with the caller's session recorded in the transitions row).

## SOFT 11: one test asserts nothing

test_cli_verify_healthy_exits_zero passes even when cmd_claim is sabotaged to
create no record, because verify on an empty store is trivially healthy. Fix:
assert the record is actually present (via dump) before asserting healthy, and
calibrate by sabotaging cmd_claim.

## Out of scope for this round (tracked, not silently dropped)

- The V1 lifetime tripwire in tools/test_bm.py fails on bm_store.py's use of the
  'ephemeral' literal. The honest fix is a one-hunk exemption in that test file,
  which is outside this fence and is with the founder. DO NOT rename, split, or
  obfuscate the literal to dodge the scanner.
- Real Windows execution: proxied here via ntpath and forced sys.platform. The CI
  windows-latest leg is the real proof and runs on push.
