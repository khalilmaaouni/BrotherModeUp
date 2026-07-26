# BrotherMode V2, requirements

This file lists what the ratified V2 design and its Phase 1 fix round require,
as testable, numbered statements. It is for the founder deciding whether the
scope is right, and for anyone implementing or reviewing a fix, who should be
able to point at one line here and one line in the source spec for every
change they make.

Each requirement has an ID, a plain statement, a Given/When/Then acceptance
line, and a source citation. Requirements describe what must be true, not
whether it is already true today: Phase 1 is mid-build (see `ARCHITECTURE.md`
for the current state and the open questions found while writing this pack).
Whether a given requirement is actually enforced yet is a QA question, not a
requirements question: see `QA-GATES.md` for the calibration rule that proves
each fix before it is accepted.

Requirements are grouped by the four ratified decisions, plus a fifth group
for the founder's Windows override.

---

## Group A: Decision 1, one canonical root

Source: `docs/superpowers/specs/2026-07-26-brothermode-v2-design.md` lines 9-13 and 36-51; `docs/superpowers/specs/2026-07-26-phase1-fix-round.md` lines 12-31 (Gate 1).

**R-01. Root resolution order.**
Given the `BROTHERMODE_ROOT` environment variable is set to a real directory,
when any command resolves the project root, then that directory is used and
the source is reported as `env`.

**R-02. A marker beats a nested `.git`.**
Given a `.brothermode` marker directory exists higher up the tree and a
`.git` file or directory also exists in a subdirectory below it (for example
a vendored dependency or a submodule), when root is resolved from inside that
subdirectory, then the marker directory wins and the source is reported as
`marker`. This closes the defect class where a nested `.git` could shadow the
real project root.

**R-03. Git fallback, worktrees included.**
Given no `BROTHERMODE_ROOT` and no marker exist anywhere up the tree, when a
`.git` directory or file is found while walking up, then that directory
becomes root and the source is reported as `git`. A worktree, whose `.git` is
a file rather than a directory, resolves the same way as a normal checkout.

**R-04. No root refuses ownership operations.**
Given no environment variable, no marker, and no `.git` exist anywhere up the
tree, when an ownership operation (claim, park, resume, complete, adopt,
checkpoint, or decide) is attempted, then it is refused with reason `no-root`
and the message tells the user to run `init` or set `BROTHERMODE_ROOT`.

**R-05. `init` creates the marker and the schema.**
Given a fresh directory with no store, when `init` is run, then the
`.brothermode/` marker directory and the database schema are created.

**R-06. `init` keeps the store out of git status.**
Given a `.git` directory exists and the exclude entries are not yet present,
when `init` runs, then `.brothermode/`, `threads/`, and `STATE.md` are
appended to `.git/info/exclude` without touching the founder's own
`.gitignore`.

**R-07. Every claim path is canonicalized the same way, whichever directory it was entered from.**
Given a claim path is entered from a subdirectory of root, when it is stored,
then it is canonicalized against root into a normalized, root-relative POSIX
string identical to what a caller working from root itself would produce.

**R-08. A path that escapes the root is refused.**
Given a claim path resolves, whether through `..` segments or through a
symlink, to somewhere outside the canonical root, when a claim is attempted,
then it is refused with reason `path-escape`.

**R-09. The root itself, once canonicalized, overlaps everything.**
Given the empty path (the project root itself) is canonicalized, when it is
compared against any other claim, then it always counts as overlapping that
claim, because the empty result normalizes to `.`.

---

## Group B: Decision 2, one transactional store

Source: `docs/superpowers/specs/2026-07-26-brothermode-v2-design.md` lines 14 and 52-92 (schema) and 118-138 (API and redaction); `docs/superpowers/specs/2026-07-26-phase1-fix-round.md` Gates 4, 5, 7, 8.

**R-10. sqlite is the sole authority on ownership.**
Given anything needs to know who owns a piece of work right now, when it
looks for the answer, then it reads the sqlite database that `tools/bm_store.py`
owns, never `STATE.md` or a dashboard, both of which are generated views only.

**R-11. Schema version 1 tables exist after `init`.**
Given a fresh store, when `init` runs, then `meta`, `records`, `claims`,
`decisions`, `digests`, `directives`, `deliveries`, `transitions`, and
`autosave_receipts` all exist, matching the ratified DDL.

**R-12. One active record per name.**
Given two records could share the same name, when both would try to be
active at once, then the database itself refuses the second one, through a
unique index over active records' names.

**R-13. A busy or locked database is never quarantined.**
Given the store file is merely busy or locked (a transient condition), when
`Store()` opens it, then it refuses fail-closed with a clear retry message
and does not rename or otherwise touch the file.

**R-14. Any other unreadable database is quarantined, never silently recreated.**
Given the store file cannot be read as SQLite for any reason other than being
busy, when `Store()` opens it, then it is quarantined (renamed aside) and a
`StoreCorrupt` error is raised naming the recovery path, and it is never
recreated over the damage.

**R-15. Quarantine moves the sidecars too, and can never collide.**
Given a corrupt store is quarantined, when the quarantine happens, then
`store.sqlite3` and its `-wal` and `-shm` sidecar files move together into a
uniquely named, per-incident directory, so two quarantines in the same second
can never overwrite one another.

**R-16. Corruption discovered mid-operation quarantines the same way construction-time corruption does.**
Given the store opens fine but a later operation (claim, dump, or verify)
hits a database error deeper in the file, when that happens, then it is
quarantined through the same shared path as a corrupt open, never surfaced as
a raw, unhandled traceback.

**R-17. Every founder-typed field is redacted at every exit.**
Given any founder-typed text exists anywhere in the store (an objective, a
decision, a digest section, a note, the tier, a claim path, the check
command, or evidence text), when it leaves the store as a generated
`STATE.md` view, a rendered digest, a dashboard line, or any other output,
then it has passed through the one shared redaction function first.

**R-18. A redaction failure refuses to render rather than leaking raw text.**
Given the shared redaction function cannot be loaded, when a generated view
would otherwise be produced, then a one-line warning is printed and the
render is refused, instead of emitting unredacted text.

**R-19. Generated markers cannot be forged by founder-typed content.**
Given founder-typed content contains the literal BEGIN or END marker text
used to bound the generated block, when that content is written into a
generated view, then the occurrence is neutralized so exactly one BEGIN and
one END marker survive the render.

**R-20. `dump()` is the one documented, raw exception.**
Given a human needs the full, unredacted record for inspection or migration,
`dump()` is the only function allowed to return raw text; every other
rendering function redacts first.

**R-21. The store locks itself down, best-effort, as soon as it exists.**
Given the `.brothermode` directory and the store file exist, when they are
created, then the directory is set to owner-only and the store, its
sidecars, and any quarantine artifact are set to owner-only, best-effort,
without ever failing the operation itself if the platform will not honor it.

**R-22. The store protects itself from `git add` without waiting for `init`.**
Given any command, not only `init`, creates `.brothermode/store.sqlite3` for
the first time inside a git repository, when that happens, then the
`.git/info/exclude` entries are ensured the same idempotent way `init` does
it, so a routine `git add -A` can never commit the store by accident.

---

## Group C: Decision 3, one immutable identity

Source: `docs/superpowers/specs/2026-07-26-brothermode-v2-design.md` lines 16, 93-116, and 140-175; `docs/superpowers/specs/2026-07-26-phase1-fix-round.md` Gates 2, 3, 6, and Soft 10.

**R-23. Every record has a permanent lifecycle identity.**
Given a record is created by `claim`, when it is read again at any later
point, then its lifecycle identity has not changed, and no other record,
even one that reuses the same name, is ever given that same identity.

**R-24. Every mutation is refused if the caller's expected version is stale.**
Given a caller supplies an expected version that no longer matches the
record on disk, when `transition`, `checkpoint`, or `decide` is called, then
it is refused, naming the current state and version, and the record is left
unchanged.

**R-25. Invalid names are rejected, never silently normalized.**
Given a name is empty, is `.` or `..`, starts with a dot, contains any of
`/ \ : ? * " < > |`, contains whitespace, or is longer than 60 characters,
when `claim` is called, then it raises an error describing exactly why,
without ever renaming the input on the caller's behalf.

**R-26. Per-lifecycle working directories can never inherit an old lifecycle's files.**
Given a name is reused by a brand new lifecycle, when its working directory
is derived, then the directory name includes that lifecycle's own identity,
so a prior lifecycle under the same name can never produce the same
directory.

**R-27. Overlap detection covers exact matches, directory containment, and globs.**
Given two claimed paths are compared, when one is a directory prefix of the
other, or when both contain wildcards and their literal directory prefixes
are not provably separate, then they are treated as overlapping. A pattern
like `api/*.py` and a path like `api/pay.*` must be treated as a conflict
even though no single filename matches both.

**R-28. Case folding for comparison must never rewrite path separators.**
Given case-insensitive comparison is required on Windows and macOS, when two
paths are compared, then the case fold is applied with a plain lowercase or
casefold operation on the already-POSIX-form string, gated by platform,
rather than with the platform's own case-normalization call, because that
call is known to also rewrite separators on Windows and would make a path
inside a folder look like it does not overlap that folder.

**R-29. An empty session id never matches another empty session id.**
Given two independent processes both claim the same name with no session id
supplied, when the second one runs, then it is refused as `name-active`
rather than being treated as the first session reclaiming its own record.

**R-30. The CLI generates a stable per-process session id when none is given.**
Given `--session` is omitted on the command line, when a claim is made, then
the CLI generates and prints a stable session id so that two separate
processes can never collide, and so a human reading a refusal can see who
currently holds the fence.

**R-31. Resuming a record whose name was retaken refuses cleanly.**
Given a parked record's name has since been claimed active by someone else,
when `resume` is attempted, then it is refused with reason `name-active`,
naming the current holder, rather than crashing with an unhandled database
error.

**R-32. Only the owning session may park or complete a record, except adoption.**
Given a record's session id is not empty and differs from the caller's, when
any transition other than `adopt` is attempted, then it is refused with
reason `not-owner`. Adoption stays open across sessions on purpose, because
taking over a dead session's work is the legitimate cross-session path, and
the adopting session is recorded in the transition history.

**R-33. Persistent records are capped at three active at once.**
Given three persistent records are already active, when a fourth persistent
claim is attempted, then it is refused with reason `cap`.

**R-34. Two different payloads never collide on the same fingerprint.**
Given two handover payloads differ only in their objective text, when each
one's fingerprint is computed, then the two full 64-character fingerprints
are different, so the second handover is never silently dropped as if it
were a duplicate of the first.

---

## Group D: Decision 4, two failure policies, explicit

Source: `docs/superpowers/specs/2026-07-26-brothermode-v2-design.md` lines 19-22 and 118-138; `docs/superpowers/specs/2026-07-26-phase1-fix-round.md` Gates 4, 5, 8, 9.

**R-35. Advisory surfaces fail open.**
Given telemetry, hints, or nags encounter an error, when that happens, then
the surface degrades and the founder's actual work continues uninterrupted.

**R-36. Ownership, lifecycle, and recovery mutations fail closed.**
Given a required lock is missing, or an identity is stale, or the record's
state does not allow the requested move, when an ownership, lifecycle, or
recovery mutation is attempted, then it is refused with a named reason
rather than guessed at or silently allowed.

**R-37. Exit codes are a contract, not an implementation detail.**
Given a command finishes, when its result is reported to the shell, then
exit 0 means success, exit 2 means a named refusal with the reason on
stdout, and exit 1 means corruption or a genuinely unexpected error.

**R-38. Every refusal names the legal next step.**
Given a refusal happens, when it is printed, then the message is one clear
sentence plus the command that would be legal to run next.

**R-39. An encoding failure is never reported as a bad-input refusal.**
Given the terminal cannot encode a name or an objective (for example a
non-UTF-8 stdout), when the CLI writes its output, then it catches that
encoding failure explicitly, before the general bad-input handler, so a
record that was already created is never misreported as refused.

**R-40. Names are restricted to printable ASCII.**
Given a name contains a control character, including NUL, or any
non-ASCII character, when `claim` validates it, then it is rejected with a
clear reason before any record is written, so an encoding problem can never
turn into a corrupted or half-created record.

---

## Group E: the founder's Windows override

Source: `docs/superpowers/specs/2026-07-26-brothermode-v2-design.md` lines 24-28; `docs/superpowers/specs/2026-07-26-phase1-fix-round.md` Gate 2 and the out-of-scope note.

The founder overrode the original recommendation and required that V2 run on
Windows, macOS, and Linux, not merely on Unix-like systems.

**R-41. No POSIX-only calls.**
Given the module must run on all three platforms, when any file or locking
operation is implemented, then it avoids `fcntl` and any other call that
only exists on POSIX systems.

**R-42. No shell scripts as load-bearing V2 components.**
Given a V1 capability was implemented as a shell script, when it is needed
by V2, then it is ported to Python in Phase 2 rather than relied on as a
shell script going forward.

**R-43. Path comparison folds case without rewriting separators.**
Given Windows and macOS are case-insensitive by default, when paths are
compared, then the comparison uses a platform-gated lowercase or casefold
approach on the POSIX-form string, per R-28, never the platform's own
case-normalization call.

**R-44. File replacement is atomic on every platform.**
Given a generated view or the store file must be replaced as a whole, when
the write completes, then it uses an atomic rename that works identically on
POSIX and on Windows.

**R-45. File permission lockdown is best-effort, and never claims more than it delivers.**
Given Windows does not honor POSIX file modes the same way POSIX systems do,
when the store or its sidecars are locked down, then the attempt is wrapped
so its failure never fails the underlying operation, and the documentation
never claims a guarantee the platform will not actually honor.

**R-46. The CI matrix proves all three platforms, not just claims them.**
Given the founder's override requires real Windows support, when the test
suite runs in continuous integration, then it runs on `ubuntu-latest`,
`macos-latest`, and `windows-latest`.

**R-47. Windows behavior is proxied locally and proven for real in CI.**
Given real Windows execution is expensive to reproduce on a developer's own
machine, when the case-folding fix is tested, then the test forces each of
the three platform identifiers and substitutes the Windows-style
case-normalization function, to prove the module's own logic never depends
on it, while the actual `windows-latest` leg of the CI matrix is the real
proof that runs on every push.
