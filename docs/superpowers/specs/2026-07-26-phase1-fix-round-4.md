# Phase 1 fix round 4 (2026-07-26)

**HISTORICAL DOCUMENT, dated 2026-07-26. Do not read it as current state.** It is a dated working record: the plan, the verdicts, the blockers and the numbers in it belong to that day and were not updated afterwards. Items it calls open may since have been closed. Superseded by `README.md` and `docs/KNOWN-LIMITS.md` for status, `docs/NOT-FINALIZED.md` for the defect register, `CHANGELOG.md` for what changed since, and `python3 tools/bm_project_facts.py` for version, release tag, hook events and suites.

One defect, found by the orchestrator while checking exit codes after round 3 landed.
It is an HONESTY defect, the same class as the autosave printing "your files are
autosaved" without checking: the tool reports health it has not earned, immediately
after losing data.

## GATE: after a quarantine, the next command silently creates a fresh store and reports healthy

Reproduced (executed, orchestrator):

    init; claim k --lifetime persistent --objective "IMPORTANT WORK" --files k.py
    : > .brothermode/store.sqlite3          (truncate: a crash, or a full disk)
    verify   -> STORE CORRUPT ... quarantined to ...quarantine-2026...   (correct)
    verify   -> "verify: healthy, 0 problem(s)"   exit 0                 (WRONG)

The second command finds no store, creates an empty one, and pronounces the project
healthy seconds after every record was lost. A founder running the diagnostic twice, or
a hook running it on the next session start, is told everything is fine.

Second, smaller half of the same defect:

    (fresh directory, init NEVER run)
    verify -> "verify: healthy, 0 problem(s)" exit 0
    ls .brothermode -> store.sqlite3, -wal, -shm     (a read-only command created state)

## Required fix

1. CREATION IS EXPLICIT. Only `init` creates a store. Every other command, mutating or
   read-only, refuses when no store exists, with reason 'no-store' and the exact command
   to run. A diagnostic that creates the thing it is diagnosing cannot diagnose it.
2. READ-ONLY COMMANDS NEVER WRITE. verify, dump, and dashboard must open the database
   read-only (sqlite3 URI mode=ro) and must not create directories, files, or WAL
   sidecars. Test: run each in a fresh directory and assert nothing appeared on disk.
3. A QUARANTINE IS REMEMBERED UNTIL ACKNOWLEDGED. While any quarantine directory exists
   beside the store, every command prints a one-line warning naming the newest one and
   the record count it could not read (or "unknown" when that cannot be determined), and
   `verify` reports it as a PROBLEM (exit 2), not as health. Acknowledging is an explicit
   act: `bm_store.py init --acknowledge-quarantine` (or moving the directory away). This
   mirrors the ratified autosave receipt rule: a safety claim is printed only when
   something checked it.
4. The health vocabulary is reserved. The word "healthy" may only be printed when a store
   was opened, read, and found consistent, with no unacknowledged quarantine present.

## Required calibrated tests

- After a truncation-quarantine, a second verify exits 2 and its output does NOT contain
  "healthy"; it names the quarantine directory.
- verify, dump, and dashboard in a fresh directory each exit 2 with 'no-store' and leave
  the directory EMPTY (assert os.listdir is unchanged, including no -wal or -shm).
- init after a quarantine refuses without --acknowledge-quarantine, and succeeds with it,
  leaving the quarantine directory in place (never deleted).
- Calibrate each by reinjecting the auto-create behavior and confirming the right test
  fails for its stated reason.
