# Changelog

## 2026-07-29 v2.0.0-rc.3: V2 becomes the public product, by founder decision

The founder decided, recorded the same day: ship V2 as a release candidate now.
The repository root previously showed the pre-V2 product; after this release the
default branch carries V2, so the clone command in the README installs what the
README describes. The STABLE claim still waits for the real dogfood window and an
independent audit; this is a release candidate and says so.

What changed in this cut:

- `v2` merged into `main` (fast forward; pre-merge main preserved in a backup
  branch). One product, one branch, one README.
- `CHECKSUMS.sha256` regenerated at the tagged commit. The post-audit baseline
  (docs/POST-AUDIT-BASELINE-2026-07-29.md) records that the previous manifest
  had drifted 12 commits behind the tree and the verifier correctly refused it.
- The post-audit execution plan and its frozen baseline ship in `docs/`, with
  founder decisions recorded inline: Model A approval receipts chosen, four new
  loops ratified (cross-runtime adapters, packaging, ecosystem launch kit,
  external beta evidence).
- Everything in the rc.2 entry below (the correction memory, 598-test gate)
  is included unchanged.

## 2026-07-29 (still v2.0.0-rc.2, no version bump): a founder-approved correction memory, documented honestly

No version bump: a release is founder-gated (`docs/RELEASE.md`), and this
entry is documentation plus a working feature, not a release decision. Test
count went from 419 (2 skipped) to 598 (2 skipped), all green, run with
`python3 tools/test_all.py`.

What actually changed for you:

- You can now capture a correction, approve it into a rule yourself, and ask
  what rules apply to a piece of work with the reason shown. Approval is
  founder-only: nothing in this system, including the parts that watch for
  corrections automatically, can approve its own candidate. Plain-language
  walkthrough with real, hand-run command output: `docs/CORRECTION-LEARNING.md`.
- Correction capture now understands English, French and Japanese phrasing,
  and a long correction is excerpted with the omitted character count
  recorded, instead of the old English-only, 400-character filter that
  silently dropped a founder's French corrections and long ones alike.
- Approving a rule that plainly reverses a live one is refused unless you
  override it, and the override is recorded rather than silent. A conflict
  the detector cannot see (a phrasing it does not recognise as a reversal)
  can be declared by hand and counts exactly as much downstream.
- The store can now say, for a given piece of work, which rules were
  retrieved, shown, followed, ignored, and why, and can link a rule to a
  piece of rework or an escaped defect it failed to prevent. A correction
  round on that grading (found the same way every serious defect in this
  project has been found: driving the real CLI against a throwaway store
  while the suite stayed green) fixed the same outcome being counted twice,
  a rule being blamed for work it was never part of, and rework being
  miscounted as the founder repeating an instruction he only said once.
  `docs/NOT-FINALIZED.md` item 20 has the detail.
- The secret scrubber used to miss a secret glued to a word character on
  either side (an API key immediately after an underscore, for example), and
  every JSON-emitting learning command now withholds a founder's raw text and
  evidence excerpts through one shared rule, rather than a rule a particular
  command could forget to apply. `docs/NOT-FINALIZED.md` item 15 has the
  detail.

What is deliberately unbuilt, and stays that way until its stated reopening
condition:

- **Loops 9 and 10 were never built, by the founder's own ratified decision**
  (`docs/superpowers/specs/2026-07-28-correction-learning-program.md`, section
  3.1): evaluation partitions (Loop 9) and generated knowledge views (Loop 10)
  would both be measuring or generating over a corpus of maybe twenty to forty
  rules belonging to one person, too small for either to produce a number that
  can support a decision. Building the machinery anyway would make an
  unsupportable number look rigorous, which is exactly the failure this
  program's own principle forbids. Loop 9 reopens when the rule corpus is
  large enough for a partition to decide anything; Loop 10 reopens when
  hand-curating `docs/knowledge/LESSONS.md` and `TOOLBOX.md` actually becomes
  the bottleneck.
- **Loop 11B, the optional automatic-retrieval hook, is gated on the real
  dogfood window, not built.** The skill-driven retrieval that already ships
  (Stage A, Loop 11A) has to prove itself in real use first; a hook that
  pushes the wrong rule into every prompt is worse than the opt-in retrieval
  shipping today.

Still true and the single most important line in this entry: **this system has
never run on a real day of the founder's actual work.** Every count above came
from a test suite or a hand-driven probe against a throwaway store. That is
`docs/NOT-FINALIZED.md` item 1, and it stays UNPROVEN, ranked the highest-harm
open item in the whole project, until Loop 14a (a real dogfood window) closes
it. No amount of further testing can close it.

Also still true: Windows behaviour is asserted by continuous integration only;
no Windows machine has ever run this code by hand. And `docs/NOT-FINALIZED.md`
item 12, an independent second-model adversarial re-audit, remains open. The
privacy and security fixes in this wave (the secret scrubber, withholding raw
text) do NOT close item 12: they were written and verified by the same model
family that built the feature they review, which is exactly the blind spot an
independent re-audit exists to catch. A different model family has never
looked at this code.

## 2026-07-27 (v2.0.0-rc.2): the external audit closed, and rc.1 withdrawn

A second external adversarial audit returned NO-GO on rc.1: 8 release blockers
and 9 high-risk defects. All 17 are now closed, and CI is green on Linux, macOS
and Windows across both supported Python versions with the recovery suite
included, which rc.1 never was.

WITHDRAWN: do not install `v2.0.0-rc.1`. Its tag points at a commit that FAILED
on Windows, and the branch then moved 14 commits past it while the VERSION file
still read `2.0.0-rc.1`. An immutable tag and a moving branch claimed one
identity while holding different code. That is the defect this entry exists to
close, and it is worse than an ordinary bug: a version number is the promise that
two people naming it are discussing the same bytes.

What actually changed for a user:

- Your recovery tool no longer lies to you. It used to print "your files are
  autosaved" whenever this session had EVER snapshotted; it now verifies the
  snapshot still resolves and says plainly when your newest work may not be
  captured. It has a third answer that claims nothing when the truth is unknown.
- Files can no longer be written outside your project through a symlink. One
  containment funnel now covers STATE.md, its backups, thread directories and the
  project server, which previously had four separate holes.
- The project server can no longer be tricked into copying another project's
  database and answering with its contents.
- The install verifier now catches a planted symlink backdoor it used to pass.
- A read-only health check can no longer move your database.
- The store refuses to open where git could commit it, so raw objectives and
  decisions cannot be published by a routine `git add -A`.
- A thread whose NAME looked secret-shaped used to become permanently unreachable
  with its fence stranded. Identity now comes from the table, not a redacted view.
- The CLI no longer guesses between two threads with the same name; it refuses
  and lists them.
- The single-writer promise has a mechanical gate for the first time: a
  PreToolUse hook that blocks a write outside an active claim. It is shipped but
  NOT installed by default, because it sits in front of every edit.

Still true and stated rather than buried: this has never run on a real project,
Bash writes are not gated by the hook, session identity is harder to forge but
not unforgeable, recovered work is owner-only on POSIX only, and handovers are
serialized by a lock rather than stored transactionally. `docs/KNOWN-LIMITS.md`
carries the full list.

## 2026-07-26 (later still): the final gate's two blockers, closed structurally

A four-lens final gate aimed at the code from the entry below found two release
blockers and three further gates, all reproduced by hand before this entry's
fixes were written (`docs/superpowers/specs/2026-07-26-final-blockers.md`).
This entry closes all of them. No version bump: still `2.0.0-rc.1`.

**BLOCKER 1, the worst finding: the server documented as read-only moved the
founder's database.** One `bm_status` call against a store whose header bytes
had been corrupted quarantined it, renaming `store.sqlite3` aside and
reporting `isError: false`; a HEALTHY store's own read-only open also created
`-shm`/`-wal` sidecars that were not there before. Reproduced, then fixed
structurally rather than by a stronger promise: `mcp/bm_mcp_server.py` now
copies `.brothermode/` and `STATE.md` into a private temporary directory
before every tool runs, and deletes the copy afterward, success or failure
alike. Proven against the real server: a corrupted store's directory listing
(names and content hashes) is byte-identical before and after all four tools
are called, and a healthy store with its sidecars removed gains none back. A
read-only sqlite URI was considered and rejected on purpose, to avoid
reopening the exact `%`-path defect this project's own GATE A (fix-round 6)
already closed.

**BLOCKER 2, security: `verify-install.sh` reported PASSED with a planted
backdoor present.** It only ever asked whether every file the manifest NAMES
matches on disk, so a file that was ADDED (`tools/bm_helper.py`, containing a
shell-out) was invisible to it. Reproduced (88 hashes, plant, still PASSED at
exit 0), then fixed: the script now also enumerates the installed tree and
fails, naming the file, when anything exists on disk that the manifest does
not name. Verified against a clean tracked-file copy of this repository
(PASSED, 0 extra) and the same copy with the backdoor planted (FAILED, exit 1,
`EXTRA: tools/bm_helper.py`).

**GATE 3: the server leaked founder text every other exit redacts.**
`bm_store.verify()` returns raw, unredacted rows (it is an invariant checker,
not a rendering funnel), and the server used to print its problem strings
straight through; a secret-shaped record name reached a client here
unredacted while the CLI showed `[REDACTED]` for the same value. Fixed: every
founder-typed value this server returns now passes through
`bm_store._protect_text`, the exact function the CLI's own output funnel
uses. The round-7 output-funnel structural scan, previously scoped to
`bm_store.py` alone, is now also applied to `mcp/bm_mcp_server.py`
(`tools/test_bm.py`), together with a calibrated test that reproduces the
secret-leak precondition and asserts the live secret never reaches the tool's
returned text. Not widened further: `bm_threads.py`, `bm_autosave.py`,
`bm_telemetry.py`, and `bm_score.py` were never brought under this funnel
discipline and are outside this fix's scope; stated here rather than silently
skipped.

**GATE 4: `project_root` was not authoritative.** A relative path resolved
against the SERVER PROCESS's own working directory, and `BROTHERMODE_ROOT`
silently overrode an explicit argument, so a call naming one project could
answer with a different project's record. Fixed: `project_root` must now be
an absolute path (a relative one is refused outright), the server never
consults `BROTHERMODE_ROOT`, and every tool prints the project root it
actually resolved as the first line of its own output. Verified: with
`BROTHERMODE_ROOT` pointed at one project, an absolute `project_root` naming
a second project answers correctly about the second project, with its root
printed; a relative `project_root` is refused with `isError: true`.

**GATE 5: `checksums.sh` silently dropped any git-quoted path.** A tracked
path containing a quote, a backslash, or a non-ASCII character is printed
quoted by plain `git ls-files`, is not a real path on disk, and the manifest
loop skipped it with no message at exit 0. Fixed: the manifest is now built
from `git ls-files -z` (null-delimited, never quoted), and the script fails
loudly, naming the file, if any listed path is not a regular file on disk.
Verified in a throwaway repository with a file named containing both a quote
and an accented character: the old approach silently hashed 3 of 4 tracked
files; the fixed script hashes all 4, and correctly fails loudly when a
tracked file is genuinely missing from disk.

**SOFT 6: the decisions filter compared against the REDACTED name.**
Filtering `bm_decisions` by a record's real name returned a false "no
decisions recorded" whenever that name happened to look secret-shaped,
indistinguishable from a project that genuinely recorded none. Fixed: the
filter now matches against the record's real name, read from a second,
separately-opened raw dump used only to compute matching identifiers; only
those identifiers, never the raw name, reach the tool's returned (still
redacted) text. Verified: filtering by a secret-shaped name now returns its
decision instead of a false negative.

`docs/RELEASE.md` and this file both now describe the two-directional
`verify-install.sh` check accurately; the previous wording promised the
behavior BLOCKER 2 found missing.

## 2026-07-26 (v2.0.0-rc.1): the first tagged version, release discipline, and an honest ledger of what shipped today

This is the first version of this project to carry a version number
(`VERSION`, `2.0.0-rc.1`) and, once the founder-gated tagging step in
`docs/RELEASE.md` actually runs, the first tagged release. Read
`docs/RELEASE.md` for why it is `2.0.0-rc.1` and not a bare `2.0.0`: the
storage engine changed underneath every command (a major bump), but this has
never run on a real project and CI has never executed once (`docs/KNOWN-LIMITS.md`),
so it ships as a release candidate rather than a claim of proven stability.

**What changed for you, if you install this today:**

- **The storage engine is now the thing every tool actually uses.**
  `tools/bm_store.py` (a SQLite-backed store) is imported by
  `bm_autosave.py`, `bm_sessionstart.sh`, `bm_telemetry.py`, and
  `bm_threads.py`. `bm_registry.py`, the old JSON registry, is deleted
  outright, not kept as a shim. If your own scripts imported
  `bm_registry.py` directly, that import will now fail; nothing in this
  project does that any more.
- **A recovery path for the new engine.** The autosave/recovery mechanism was
  rebuilt against the store rather than the old registry, with a real,
  test-covered recovery flow instead of a manual sqlite surgery.
- **Two security fixes, both re-verified today.** A recovered autosave
  worktree used to come back world-readable (`drwxr-xr-x`); it now comes
  back owner-only (`drwx------`). Turning thread mode off and resuming a
  thread later from a different session used to be wrongly refused; it now
  succeeds and transfers ownership correctly. Both are described in full,
  with the exact reproduction steps, in `docs/KNOWN-LIMITS.md`.
- **Several features were removed, not just refactored.** Checkpoint clash
  detection has no equivalent in the new engine and is gone. The 320-line
  generative test bound to the old registry was deleted along with it; a
  store-level replacement is being built separately and is not part of this
  release. Neither removal is quietly absorbed into "cleanup" language:
  they are feature losses, named as such in `docs/REMAINING.md`.
- **Release discipline exists for the first time.** `scripts/checksums.sh`
  generates a SHA256 manifest of every git-tracked file; `scripts/verify-install.sh`
  checks an installed copy against that manifest and names anything that
  differs. This is the direct answer to a problem the original external
  audit called the weakest link in the whole design: the install
  instruction clones a git ref into a location whose code then runs
  automatically on every Claude Code session, with previously no way to
  confirm what actually landed on disk.
- **A guided path to the memory setup**, `docs/OBSIDIAN.md`: what the vault
  is, how to install Obsidian, how to point it at the vault, and how to work
  with the same vault using nothing but a plain text editor. Obsidian
  previously appeared nowhere outside a design document.
- **A minimal, read-only MCP server**, `mcp/`, so a session can ask what
  work is active, what fences are live, what decisions were recorded, and
  whether the store is healthy, without reading files directly. It is
  read-only by construction (it only opens `bm_store.ReadOnlyStore` or calls
  `bm_store.verify()`) and implements the subset of the Model Context
  Protocol a read-only query tool actually needs, not the full
  specification; `mcp/README.md` states exactly what was and was not
  verified.

**What is still open, so nobody mistakes this for finished:**

- **One confirmed defect remains.** A refused `adopt` attempt (one session
  tries to take over another session's live, active thread without the
  explicit override, and is correctly told no) still permanently writes an
  "Adopted from dead/stalled thread" block into `STATE.md` anyway. The
  refusal itself is correct; the side effect it leaves behind is misleading.
  See `docs/KNOWN-LIMITS.md` for the exact reproduction.
- **Never run on a real project.** Every claim in this release rests on test
  suites and adversarial review, not on a week of real founder work going
  through the V2 store.
- **CI has never executed.** The workflow is configured for Linux, macOS,
  and Windows; nothing has been pushed to trigger it, so the first real push
  is also the first real test of that configuration.
- **Windows is designed for, not proven.** Windows behavior was proxied by
  substituting the path module and platform identifier, which caught one
  real defect but is not the same as running on Windows.
- **The self-learning mechanism (Section 8 loops) is designed, not built.**
  The redesign is approved and written up; nothing implements it yet, and
  the old scorecard still prints at least one number (`collisions=0, baton
  drops=0`) that cannot move because nothing behind it is measured.

No test count is restated here. The previous entry claimed 116; this session
could not re-run `tools/test_bm.py` to confirm that number still holds
(other work landed in `tools/` in parallel with this entry being written),
and `docs/KNOWN-LIMITS.md` already warns that any test count in this
repository is a claim to re-verify, not a certificate. State the actual
number the next time this file is edited, taken from a command run in that
same session, not copied forward from here.

---

## 2026-07-26: handover delivery gets an owner, and the pattern gets a stop

A reviewer found that the retry marker added in the previous entry was keyed on
the thread NAME, and a thread name is reusable. Reproduced: adopt "payments",
start "payments" again for new work, adopt again, and the second lifecycle's
handover was silently discarded while the tool printed "Nothing is duplicated".

The fix is not another marker. Delivering a handover into the project
`STATE.md` now has exactly ONE owner, `deliver_handover`, used by both `absorb`
and `adopt`:

- **Identity is per lifecycle, not per name.** Every record carries a
  `lifecycle` number, incremented when a closed id is reused, so a second
  `payments` thread has its own delivery identity.
- **The proof of delivery lives inside the delivered text**, as a
  `<!-- brothermode-handover:id#n -->` tag, not in a side file. A separate
  marker can survive content a crash destroyed, which is the worse direction;
  a tag cannot outlive the bytes it is written with.
- **The append is durable.** `durable_append` flushes and fsyncs before
  returning, so a crash cannot leave a delivery proof more durable than the
  handover it vouches for.
- **`absorb` is now idempotent too.** It appended and then saved the registry;
  if the save failed, the retry appended the same handover again. It now
  recognises its own tag.

**The part that matters most.** Four cross-cutting concerns in this project have
now followed the identical arc: locking, redaction, durable writes, and handover
delivery were each implemented per call site, diverged, and were unified into a
primitive only after someone found the divergence. A fifth was always going to
happen, because nothing stopped the next call site improvising.

So this release adds the stop, not just the primitive: a test asserts that
`durable_append` has exactly one caller and that no other code appends a
handover by hand. A future writer that invents its own delivery fails the suite
instead of shipping and waiting to be caught.

116 tests.

---

## 2026-07-26: durable writes, closed as a class rather than case by case

The previous three entries each fixed one reported instance of the same defect.
This entry closes the class, by audit rather than by report.

**Crash atomicity.** State was written with a plain truncating `open(path, "w")`,
so a crash, a full disk or a killed process between truncate and write could
leave `registry.json` or `thread-mode.json` empty. An empty registry reads as
"no work in progress", which would let a second writer claim files someone is
already editing. There is now ONE primitive, `bm_telemetry.atomic_write`: temp
file in the same directory, flush, fsync, `os.replace`, then fsync the
directory. The registry and every thread file go through it. Proven: a failed
write leaves the previous file byte-identical and no temp file behind.

**Idempotent adoption.** `adopt` has three writes and can fail between any two,
so a retry is expected. A marker records that the handover already reached
`STATE.md`, and a retry resumes the unfinished steps instead of appending the
handover a second time. Proven by forcing a mid-transaction failure and retrying.

**The audit.** Rather than wait for the next report, every durable write in
`tools/` was enumerated and checked for a discarded return value. That found ten
more instances the reviews had not reached: `claim`, `decide` and `set_digest`
all reported success without checking their save; `start` ignored all four
thread-file writes and its mode write; `on`, `checkpoint`, `send` and
`attribute` the same. All now report honestly, and `start` releases its fence
when its files cannot be written so no paths stay claimed by a thread that does
not exist. The audit was repeated until two consecutive rounds turned up nothing
new; the four remaining unchecked calls are documented as deliberate.

One consequence worth knowing: because replacement is now atomic, a read-only
target FILE no longer blocks a write (rename needs directory permission, not
file permission). Tests that simulate a failed write make the DIRECTORY
read-only instead.

113 tests.

---

## 2026-07-26: a failed write can no longer be reported as success

The concurrency work was done, so the next review looked at failure paths and
found the worst remaining case. `adopt` ignored the return value of every write
it made and always printed success. With an unwritable project `STATE.md`:

- the handover never landed,
- the registry record was closed anyway, so `off` would never drain it,
- the thread was marked adopted,
- and the command printed "Nothing is orphaned".

Total silent context loss, reported as a clean adoption. Reproduced before the
fix, and the message was exactly that.

`adopt` now writes the handover FIRST, so a failure there changes nothing and
the thread stays adoptable, then checks every subsequent write and names the
exact partial state if one fails. `off` checks its final mode-file write for the
same reason. `bm_registry.close()` was returning True regardless of whether its
save reached disk, which would have made adopt's new check meaningless; it now
returns what the save did.

This is the same defect this project already fixed once inside `absorb()`, where
the bug had moved one call later. It is the third appearance of the class.

110 tests.

---

## 2026-07-26 (final): the off transition is now atomic

A follow-up review found a real transactional race between `start` and `off`,
and it also corrected a mistake in the previous entry.

`off` drained the registry OUTSIDE the mode lock and only took that lock
afterwards. A `start` running concurrently could be granted in the gap, so its
record stayed ACTIVE while the mode file recorded the thread as parked, and its
digest was never absorbed. That is silent context loss, the exact thing thread
mode exists to prevent. Reproduced before fixing: **28 of 30 trials**. After:
**0 of 40**.

`off` and `adopt` are now each ONE mode-locked transaction, and `start`
rechecks the mode inside the lock so a start that queued behind an `off` refuses
instead of creating a thread nobody will drain.

The previous entry claimed holding the mode lock across `absorb` would invert
the lock order and risk deadlock. That was wrong. `cmd_start` calls
`reg.claim()` INSIDE the mode lock, so the order has always been mode then
registry, and `off` now matches it rather than inverting it. The wrong comment
had been used to justify leaving the gap open.

The concurrency test now asserts STATE, not only liveness: an OFF system must
hold no active persistent record, and every thread in the mode file must have a
record. It runs repeatedly, because a race that reproduces sometimes proves
nothing when it happens to pass once.

108 tests.

---

## 2026-07-26 (later still): one lock for the whole system

A follow-up review found the locking fix from the previous entry was applied in
one place and not the others. Three silent paths remained, all confirmed by
reading the code before changing it.

- `bm_threads.py` carried its OWN mode-file lock that swallowed every failure,
  so on a platform without `fcntl` the registry warned that coordination was
  degraded while thread-mode updates raced on quietly. Two half-truths instead
  of one behaviour.
- `bm_registry.with_lock` proceeded unlocked and silent when the lock directory
  could not be created, and again when the lock file could not be opened.

Locking is now a single primitive, `bm_registry.locked_call`, used by both
files. Every way it can fail to acquire still runs the work, because never-block
outranks coordination, and every one of them warns once per process.

Found while fixing this, and not in the review: three of the four writes to
`thread-mode.json` were not locked at all. Only thread creation was. The one
that mattered was `off` racing a `start`, which loses a thread. All four are now
inside the lock, in a consistent registry-then-mode order so the two locks
cannot deadlock against each other. That ordering is covered by a test that runs
four starts and two offs at once and fails on a hang.

107 tests.

---

## 2026-07-26 (later): the CI gate could pass on a crashed checker

Three findings from an external source review, each confirmed by running the
code before it was changed.

- **`bm_score.py --strict` exited 0 when the checker itself crashed.** The
  top-level handler caught every exception and exited 0, so any bug inside the
  checker turned into a green build that had verified nothing. Reproduced by
  injecting a crash and watching `--strict` report success. Strict mode now
  exits nonzero and says the checker failed; local runs still degrade quietly,
  because never-block is a promise to the session, not to CI.
- **Missing file locking was silent.** `fcntl` is POSIX only, so on Windows the
  registry ran with no lock at all while callers believed concurrent claims were
  serialized. Work still proceeds, but it now says once per process that
  coordination is degraded. Tested by shadowing `fcntl` with a module that
  refuses to import.
- **The collision claim was stronger than the code.** The README said collisions
  "stop being possible". They do not: the guarantee is exactly as good as the
  declaration, and a file an agent never declared is not protected. Both the
  README and the design doc now say that plainly.

104 tests.

---

## 2026-07-26: one work record for threads and fences

BrotherMode was keeping two separate records of the same fact. Threads lived in
`thread-mode.json`. Single-writer fences lived as prose inside `STATE.md`. Both
answered the question "who owns this file right now", and nothing stopped them
from answering it differently.

This release makes them one object. A thread and a fence are now the same
record, and `lifetime` (persistent or ephemeral) is the only thing that tells
them apart.

The practical effect: because a record's declared files are a real list instead
of a sentence, an overlap between two claims is now **computed and refused by
name**. Before, the registry could only be read by a human who happened to
check. That was the single largest hole in the single-writer law, and closing
it is the point of this release.

---

## What existed before

Everything below already worked and still works. This release did not remove
any of it.

### The law

- `SKILL.md`: 16 numbered sections covering classification, role assignment,
  the delegation ladder, token budgets, fences, research doctrine, circuit
  breakers, self-improvement loops, context hygiene, honesty, founder gates,
  memory, a known-mistakes ledger, the founder model, and scoring.
- `DIGEST.md`: a short compression of the law, injected at session start so the
  rules survive a context loss.
- `RUBRIC.md`: the frozen scoring rubric the weekly review grades against.
- `STATE.template.md`: the per-project state file, copied into your own repos.

### The tools

- `bm_telemetry.py`: session outcomes, the scorecard, felt-outcome ratings,
  review marks, session-start nags, stop warnings, registry and fence linting,
  write-ahead intent, the pre-compaction resume brief, the compaction hint, the
  update check, team handoff export, correction purging, prediction audit,
  speed stats, and deduplication.
- `bm_threads.py`: persistent feature threads with a chief orchestrator.
  Commands `recommend`, `on`, `start`, `checkpoint`, `send`, `dashboard`,
  `off`, `adopt`. Nothing ever flips mode automatically, the active-thread cap
  is enforced, and switching off is lossless.
- `bm_score.py`: the nine rubric metrics, with a `--strict` mode for CI.
- `bm_autosave.py`: snapshots the whole tree, including untracked files, into a
  private local git ref before every context compaction. Never pushes, and
  excludes secret-shaped files.
- `bm_sessionstart.sh`: injects the active-laws digest at session start.
- `WEEKLY-REVIEW.md`: the weekly scoring and amendment ritual.

### The safety properties

- No network calls, no analytics, no account, no server.
- Redaction of secret-shaped text before it reaches disk.
- Owner-only permissions on the files that carry your words.
- Founder gates: credentials are never typed, destructive actions are confirmed.

### Test coverage at that point

12 tests.

---

## What was added

### A new module: `tools/bm_registry.py`

The single owner of the work record and of the three operations that are
genuinely hard to get right.

| Function | What it does |
|---|---|
| `claim` | Registers work. Refuses when declared files overlap another active record, and names the record it collided with |
| `paths_overlap` | Computes overlap across exact paths, nested directories, globs, and absolute versus relative forms of the same file |
| `decide` | Records a decision under a topic tag and raises a clash when another live record already decided that topic |
| `set_digest` | Keeps an always-current handover, so nothing depends on a thread still being alive |
| `absorb` | Drains every digest into your project `STATE.md`, then parks records rather than deleting them |
| `close` | Releases a record and its file claim |
| `render` | Regenerates the human-readable view of the registry |
| `unguarded_count` | Reports when a record is guarding fewer paths than it declared |

The record itself carries: an id, a lifetime, an owner, an objective, a real
file list, an effort tier, a lease with a time to live, a state, a done-check,
an evidence block, tagged decisions, a digest, attributed spend, and a schema
version so a later change can migrate rather than break.

### A pre-write redaction gate

`tools/write_sites.json` plus a test that inventories every write site in
`tools/`. When a write site is added or removed, the test fails and a human has
to decide whether the new one needs redaction.

Be clear about what this is: a **review-forcing inventory, not proof**. It
cannot see inside a call graph. Its value is that it makes a new write site
impossible to add silently.

### Spend attribution

`bm_telemetry.py attribute` adds a session's output tokens to a specific
record, so a token budget becomes measured rather than advisory. Cross-process
locking is proven: forty concurrent attributions produce exactly the expected
total with no lost updates.

### Documentation

- `docs/BrotherMode-One-Page.pdf`: a single designed sheet covering purpose,
  target user, philosophy, all 16 laws, features, and how to use it well.
- `docs/one-pager.src.html`: the source that generates it, so the sheet can be
  regenerated and audited instead of trusted as an opaque binary.
- The design spec and implementation plan for this release, under
  `docs/superpowers/`.

---

## What changed in existing tools

- `bm_threads.py` keeps exactly the same eight commands. Nothing new appears on
  the surface. Underneath, claim, decide, absorb, and render are delegated to
  the registry instead of reimplemented, and its duplicate copy of the
  redaction fallback is gone.
- `bm_telemetry.py` gained the `attribute` subcommand. Three code paths that
  wrote text to disk without redaction were fixed. Rating and review files are
  now owner-only.
- `SECURITY.md` had two claims that had stopped being true and are now
  corrected: the registry writes inside your project directory as well as your
  vault, and the audit line count is now checked by a test so it cannot rot
  again unnoticed.

---

## Fixed

Three Critical defects, each found by adversarial review, reproduced before the
fix and again after it.

1. **Two writers could be granted the same file.** Overlap detection did not
   match an absolute path against a relative one, so the same file written two
   different ways looked like two different files.
2. **A corrupt path entry silently destroyed a handover.** One malformed value
   made the drain throw. The digest never reached `STATE.md`, it failed
   quietly, and it failed identically on every retry.
3. **Thread adoption wrote text to disk unredacted.** Adopting a stalled thread
   copied its notes into your project `STATE.md` with no redaction, and the
   autosave then committed that file into a git ref.

Also fixed: `off` reported success when a handover had actually failed; `adopt`
never closed its registry record, so digests duplicated and file claims were
never released; a race at the thread cap could leave an invisible orphan
record; the redactor masked only the first line of a private key and let the
key body through; and note files were world-readable.

---

## Known limits

Stated here rather than left for you to discover.

- The pre-write gate cannot see non-Python files, `pathlib.write_text`,
  `json.dump(fh)`, `print(file=fh)`, or a read-one-file-then-append-to-another
  shape. It stops the problem growing. It does not retire what already exists.
- Clash detection matches topic tags. Two records making incompatible decisions
  under different topic names will not be caught.
- Overlap detection still under-blocks on symlinks and on unicode paths that
  differ only by normalization form.
- `off` drains every active record regardless of lifetime. Correct today,
  because threads are the only producer. A test fails the moment that stops
  being true.
- `bm_threads.py` grew from 470 to 540 lines. The design intended it to shrink,
  because logic moved out to the registry. The defensive guards and honest
  error reporting added back more than the move removed.
- **None of this has run on a real project yet.** Every claim here rests on
  tests, adversarial review, and simulated lifecycles.

A review on 2026-08-08 decides whether ephemeral fences migrate into the
registry, the migration is deferred with a stated reason, or the design is
reverted for not having moved the signals it named.

---

## Verifying this release yourself

```bash
python3 tools/test_bm.py
```

102 tests, up from 12.

CI runs the same suite on Linux. One test in the first cut of this release was
platform dependent (it relied on Python overflowing its stack at a given JSON
nesting depth, which macOS did and Linux did not) and it failed the public
build. It is split into two tests that each assert something true on every
platform, and the stderr warning path now has deterministic coverage it did not
have before.

Then watch the central behavior work, in a throwaway directory:

```bash
python3 tools/bm_threads.py on
python3 tools/bm_threads.py start pay "wire the webhook" --files api/pay.py
python3 tools/bm_threads.py start pay2 "second writer" --files api/pay.py
```

The second claim is refused by name and creates nothing at all.

Then confirm secrets do not reach disk:

```bash
python3 tools/bm_threads.py checkpoint pay --decision "use key AKIAIOSFODNN7EXAMPLE" --topic auth
grep -r "AKIAIOSFODNN7EXAMPLE" threads/
```

The grep finds nothing. The registry holds `[REDACTED]` in its place.
