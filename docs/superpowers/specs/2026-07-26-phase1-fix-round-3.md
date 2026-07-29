# Phase 1 fix round 3 (2026-07-26)

**HISTORICAL DOCUMENT, dated 2026-07-26. Do not read it as current state.** It is a dated working record: the plan, the verdicts, the blockers and the numbers in it belong to that day and were not updated afterwards. Items it calls open may since have been closed. Superseded by `README.md` and `docs/KNOWN-LIMITS.md` for status, `docs/NOT-FINALIZED.md` for the defect register, `CHANGELOG.md` for what changed since, and `python3 tools/bm_project_facts.py` for version, release tag, hook events and suites.

From refute round 3 (the first round run against genuinely current code; round 2 was
void because the fleet tested a stale copy). Items A and B were re-reproduced by the
orchestrator by hand before this file was written.

## GATE A: transition() enforces none of claim()'s invariants (VERIFIED BY ORCHESTRATOR)

Reproduced:

    claim alpha --files api/pay.py --session sessA   -> version 1
    park <alpha> --version 1 --session sessA         -> parked at version 2
    claim beta  --files api/pay.py --session sessB   -> granted (correct: alpha parked)
    resume <alpha> --version 2 --session sessA       -> ACTIVE at version 3, exit 0
    verify                                           -> 1 problem: active claims overlap
                                                        'alpha' vs 'beta' on api/pay.py

The store created the corruption its own verify() then reports. Same root cause makes
the 3-active-persistent cap bypassable by parking and resuming.

Fix: parked -> active must re-run EVERY admission check claim() runs, inside the same
transaction: overlap against all other active records, the active-persistent cap, and
the name-uniqueness constraint (already handled as GATE 6 last round, keep it). On
conflict, refuse with the existing reason codes ('overlap', 'cap', 'name-active') and
leave the record parked. Structural test: assert the admission checks live in ONE
function called by both claim() and the resume path, so a third caller cannot diverge
(this is the project's cross-cutting-concern law: a primitive plus a mechanical stop).

## GATE B: a zero-length database is treated as healthy and silently recreated (VERIFIED BY ORCHESTRATOR)

Reproduced:

    claim keeper ... -> lifecycle 040df155..., db 77824 bytes
    : > .brothermode/store.sqlite3        (truncate to 0, sidecars still present)
    dashboard -> "No records.", exit 0
    ls .brothermode/ -> store.sqlite3, -shm, -wal. NO quarantine directory.

Every record is gone, the tool reports health, and the spec promise "never auto-recreate
over damage" is broken. sqlite accepts a zero-byte file as a valid empty database, so
the corruption never raises DatabaseError and never reaches the quarantine path.
Truncation to 100 or 4096 bytes DOES quarantine correctly, which is what hid this.

Fix: an EXISTING store file of zero length is corruption, not an empty database.
Quarantine it (with its sidecars, per the existing per-incident directory scheme) and
raise StoreCorrupt. Creation stays legal: a store being created for the first time must
end its constructor with a schema present, so a zero-byte file never persists as a valid
state. Calibrated test: truncate to 0 with records present, assert StoreCorrupt, assert
the quarantine directory exists and holds the truncated file, assert a fresh init then
works.

## GATE C: inside a git worktree, the exclude entries are never written

.git is a FILE in a worktree (it contains a gitdir: pointer), and the exclude writer
returns early when .git is not a directory, so nothing is excluded and `git add -A`
stages the raw store. resolve_root deliberately supports worktrees, so this is a real
supported path, and SECURITY.md promises the exclude entries protect it.

Fix: when .git is a file, read its gitdir: pointer and write the exclude entries into
that directory's info/exclude (creating info/ if absent). Test with a real
`git worktree add`, asserting `git status --porcelain` does not list .brothermode/.

## GATE D: the store directory itself is not symlink-checked

Claim paths are symlink-checked and refused as 'path-escape', but .brothermode is not,
so a repository carrying `.brothermode -> docs` (or -> ../shared) writes the raw
sensitive store outside the project root, defeating the exclude line, and chmods the
link target.

Fix: apply the same containment rule the claim paths already use. If .brothermode
exists and its realpath is not <root>/.brothermode, refuse with 'path-escape' naming
both paths, and never chmod a path that failed the check. Calibrated test with a
symlinked .brothermode.

## SOFT E: render_digest omits the objective

The spec's budget list starts "header (lifecycle, objective) 400 chars", but the
rendered header carries lifecycle, name, state, and lifetime only, so a resuming session
reads a handover that never says what the work is for. Fix and test for the sentinel.

## SOFT F: a re-claim silently ignores a lifetime change

A same-session reclaim asking for a different lifetime keeps the old one and returns a
Record reporting the old value as though the request was honored. Choose ONE and test
it: honor the change, or refuse with a named reason. Do not silently discard the
argument (this is the same silent-success class as last round).

## SOFT G: one calibrated test calibrates nothing

test_calibrated_gate9_unicode_encode_error_is_a_value_error_subclass asserts only that
UnicodeEncodeError subclasses ValueError, a permanent CPython fact with no reference to
the product, so no defect can ever make it fail. Either make it exercise the actual
main() classification path, or delete it and keep the sibling tests that do. A test that
cannot fail is decoration, and this file's own header promises otherwise.

Credit where due: the calibration lens mutation-tested all 54 calibrated tests and every
other one failed correctly when its defect was reinjected. That is a real result and it
is why this single gap is worth closing rather than shrugging at.
