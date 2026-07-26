# Toolbox: verified recipes for the tools we actually use

Read the entry BEFORE using a tool. Append after a use that was VERIFIED, never
after merely reading documentation about it. This file exists because typing a flag
or a path from memory is the single most reliable way to waste a session, and
because expertise that is not written down has to be rediscovered by whoever works
next, including a future session of me.

Rules that keep it honest and small:
- An entry is created only after a verified use, with the command that actually ran
  and the output that proved it worked.
- Every recipe carries the date and the version it was verified against.
- A recipe older than 90 days without re-verification is marked STALE and must be
  re-checked before it is trusted, because version-sensitive facts are where
  invented flags come from.
- Gotchas are only recorded when they cost a real failure. A hypothetical is not a
  gotcha.

---

## git worktree

What it is for: giving a second writer (or a reviewer) an isolated copy of a repo
so two agents cannot collide in one tree.

Verified invocation (2026-07-26, git bundled with macOS 15.5):
- `git worktree add ../wt2 -b feature` creates the tree and the branch.
- A worktree's `.git` is a FILE containing a `gitdir:` pointer, not a directory.

Gotchas, each one having cost a real failure:
- Linked worktrees SHARE refs. Two sessions writing the same ref overwrite each
  other silently, which is how one autosave snapshot destroyed another (2026-07-26).
- Code that checks `os.path.isdir('.git')` silently does nothing inside a worktree.
  This shipped as a real defect: the ignore rules protecting a sensitive database
  were never written there (2026-07-26).
- The shared `info/exclude` lives in the common directory, not per worktree.

Do not use it for: parallel implementers on the same files. Implementation fan-out
stays serial with one writer; worktrees are for isolation, not for permission to
parallelize writes.

Last verified: 2026-07-26.

---

## sqlite3 (Python standard library)

What it is for: a transactional local store, when file-plus-lock hand-rolling would
otherwise reinvent transactions badly.

Verified invocation (2026-07-26, Python 3.9.6 and 3.13.14 on macOS):
- WAL mode plus a busy timeout: `PRAGMA journal_mode=WAL`, `PRAGMA
  busy_timeout=5000`, `PRAGMA foreign_keys=ON`.
- Read-only without a URI: open the plain path and set `PRAGMA query_only=ON`.
  Verified that a write then raises OperationalError.
- Optimistic concurrency: `UPDATE ... WHERE id=? AND version=?` then check
  `rowcount`; zero rows means the caller is stale.

Gotchas, each one having cost a real failure:
- A ZERO-BYTE file is accepted as a valid empty database. It will not raise. A
  crash mid-write therefore looks exactly like a fresh start (2026-07-26).
- `sqlite3.OperationalError` is a subclass of `DatabaseError`, so a catch-all
  corruption handler will quarantine a merely BUSY database. Split them.
- URI mode percent-decodes the path. A project folder containing a percent sign
  opened a DIFFERENT project's database (2026-07-26). Prefer the plain path.
- Closing the connection can DELETE stale `-wal` and `-shm` sidecars on newer
  library builds, so anything that needs those files must copy them BEFORE closing.
- `CREATE TABLE IF NOT EXISTS` on every open silently repairs a damaged schema and
  loses its rows. Create only when the file did not exist, then validate.

Do not use it for: anything requiring cross-machine coordination. This is a local
file, and treating it as shared state over a network filesystem is not supported
here.

Last verified: 2026-07-26.

---

## GitHub Desktop (the required push path on this machine)

What it is for: every push and pull on this machine goes through the Desktop app,
visibly, per standing founder rule, never a bare command-line push as a first
resort.

Verified invocation: PENDING. This entry is created without a verified recipe
because the rule is standing, but the app has not been driven successfully in this
session yet. It will be filled with the exact click path and the verification
command the first time it is driven end to end.

Gotchas, each one having cost a real failure:
- Command-line GitHub authentication is logged out on this machine, so pull
  requests cannot be created from the terminal (recorded 2026-07-26, still true).
- A screenshot shows what a window looked like, not what happened. Verify a push by
  comparing local and remote revisions with a command, never by looking.

Last verified: NOT YET VERIFIED.

---

## Python unittest as a gate

What it is for: the mechanical gate that decides whether work is done.

Verified invocation (2026-07-26): `python3 tools/test_bm_store.py` and
`python3 tools/test_bm.py`, run from the repository root.

Gotchas, each one having cost a real failure:
- Running a suite while another agent is writing to the files it scans produces a
  FALSE red and a run 17 times slower than baseline (2026-07-26). Run suites only
  when no writer is live, or run them against a frozen snapshot copy.
- A test asserting only an exit code proves the process failed, never why. One such
  test passed for an unrelated import error while proving nothing.
- Permissions cannot fail one specific write: a read-only directory fails the FIRST
  write, so later writes are never reached. Patch the single function instead.
- With crash-atomic writes, chmod on a target FILE blocks nothing, because the
  rename needs directory permission. A test that chmods a file tests nothing.

Last verified: 2026-07-26.

---

## Parallel agent fleets (the Workflow engine)

What it is for: independent, read-only fan-out (review lenses, research angles,
searches from different directions). Never implementation fan-out.

Verified invocation (2026-07-26): a script with one phase and a `parallel()` over
lenses, each returning a strict schema, launched with per-round arguments.

Gotchas, each one having cost a real failure:
- A REUSED sandbox directory makes `cp -R repo dir/repo` nest the fresh copy inside
  the stale one, and every agent then tests old code while reporting confidently.
  Always `rm -rf` the target first, and give each round its own directory
  (2026-07-26, cost one full four-agent round).
- Therefore: every brief carries a mechanical FRESHNESS ASSERTION the agent must
  run and quote back before testing anything.
- Placeholders inside a template literal are evaluated when the literal is defined,
  not when it is used, and a backtick inside a backtick string silently breaks it.
  Dry-run generated prompts before spending a fleet on them.
- Agents verify what they are pointed at. Budget attention for wandering.

Last verified: 2026-07-26.

---

## Shell measurement (the mistakes that cost me twice in one session)

What it is for: reading a command's real result rather than an artifact of how I
piped it.

Gotchas, each one having cost a real false conclusion (2026-07-26):
- `cmd | head -1` reports HEAD's exit code, not the command's. I twice reported
  "exit=0" for operations that had correctly refused with exit 2, and once nearly
  reported a fixed defect as still broken. Use `${PIPESTATUS[0]}`, or redirect to
  a file and check `$?` before piping.
- Inferring success from a side effect is not verification. I read a backup-file
  message as proof that a resume had worked, when the resume state itself was the
  thing to check. Query the state (`dump`, the record's own state field), never
  the noise around it.
- A substring search is not a structural check. Searching a rendered document for
  injected text found it present when it was correctly escaped inside one line;
  the real question was whether it occupied its own line. Match line structure
  when structure is the property under test.

Last verified: 2026-07-26.
