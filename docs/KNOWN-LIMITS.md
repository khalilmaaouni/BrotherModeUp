# Known limits, stated plainly (2026-07-26)

What this project does NOT do, has NOT proven, or has only partly checked. This
file exists because an unstated gap is a failure even when it is small, and because
the single most useful thing a handover can contain is the list of things the last
person was not sure about.

## The biggest one, updated: the engine IS connected now, and that surfaced new defects

Phase 3 landed 2026-07-26: `tools/bm_store.py` is now imported by
`bm_autosave.py`, `bm_sessionstart.sh`, `bm_telemetry.py`, and `bm_threads.py`
(43 references across those four files, measured the same day), and
`bm_registry.py`, the old JSON registry, is deleted rather than shimmed. The
defects the original audit found in that registry (silent name takeover, two
registries minted for one project, a truncated fingerprint dropping a
handover) go away with the file.

They were replaced by five real defects in the rewired thread commands,
written up in `docs/superpowers/specs/2026-07-26-release-blockers.md`. This
project's code changes fast: of the five, four were already fixed by the
time this file was corrected, in the same session, some within the hour.
Each line states what was found, and what direct re-execution just before
this edit actually showed:

- **Recovered work was world-readable. FIXED, re-verified 2026-07-26.**
  `bm_autosave.py recover` used to leave its worktree `drwxr-xr-x` with
  `-rw-r--r--` files inside (reproduced independently on this machine's own
  macOS `/tmp`, not only the Linux case that found it first). Re-run just
  now: the recovered directory comes back `drwx------` and the tool prints
  the mode it achieved.
- **The reversibility promise was broken. FIXED, re-verified 2026-07-26.**
  Turning thread mode off and then resuming a thread from a different
  session used to be refused with `not-owner`, breaking the founder's
  ratified requirement that thread mode be reversible mid-project with
  every thread resumable. Re-run just now: `resume` from a different
  session on a parked thread succeeds and transfers ownership.
- **`verify` reported a false problem after any thread command. FIXED,
  re-verified 2026-07-26.** Used to report "1 problem(s) found" on an
  otherwise healthy project and name an unresolvable relative path. Re-run
  just now: `verify` reports "healthy, 0 problem(s)" after a thread `off`.
- **Neither CLI validated flag names. FIXED, re-verified 2026-07-26.**
  `start X --file f` (the wrong, singular flag) used to be accepted at exit
  0 with no fence. Re-run just now: both `bm_store.py` and `bm_threads.py`
  refuse an unrecognized flag by name at exit 2, for `start` and for
  `checkpoint`.
- **A refused adoption attempt wrote its handover into `STATE.md`. FIXED,
  re-verified 2026-07-26 by the orchestrator after this file first recorded
  it as open.** The delivery write happened before the ownership check, so a
  refusal still recorded a live thread as "Adopted from dead/stalled thread".
  The order is now transition first, deliver second. Re-run just now: a
  different session attempting `adopt` without the override exits 2, the
  checksum of `STATE.md` is IDENTICAL before and after, and the false block
  appears zero times. This entry is kept rather than deleted because the
  sequence, found open and then closed within the same session, is the
  clearest example of why this file states dates and re-verification rather
  than conclusions.

Practical consequence: all five defects the rewire introduced are now closed
and each was re-verified by direct execution rather than accepted from a
report. This project's code changes fast; re-run the
reproduction steps in the release-blockers spec yourself rather than trust
this file's dates once more time has passed. The general operating
restrictions from the original audit still apply: run commands from the
repository root, avoid glob fences, do not run two worktrees of one repo in
parallel sessions, and never restore an autosave snapshot in place without
inspecting it first in a separate worktree.

## Never run on a real project

Unchanged from the previous handover, and it is the honest headline. Everything
here rests on tests, adversarial execution, and simulated lifecycles. No day of
real founder work has yet been done through the V2 store.

## Continuous integration HAS executed, and it FAILED on Windows

CORRECTED 2026-07-26. An earlier version of this file said continuous integration
had never executed. That was FALSE and it was never checked: the workflow has run
18 times, three of them on branch v2, and the record is public in the repository's
Actions tab. Assuming instead of looking, in a project whose whole point is not
doing that, is worth recording rather than quietly fixing.

The result on the tagged release commit (run 18, commit 7c2e0ec) is FAILURE. The
job `store (windows-latest, 3.x)` exited 1; the other matrix legs were cancelled by
fail-fast, so the Windows 3.9 leg and one macOS leg remain UNKNOWN rather than
passing.

## Recovered work is owner-only on POSIX ONLY, not on Windows

Found 2026-07-27 by putting the recovery suite into CI for the first time (audit
finding 14). It failed on both Windows legs and passed on all four POSIX legs.

The guarantee "a recovered worktree, and any private untracked file inside it, is
readable only by you" rests on a POSIX file mode of 0700. Windows governs access
by ACLs instead, and there `os.chmod` can only toggle a read-only bit. So on
Windows the recovered directory inherits whatever the parent temp directory
grants, and this project does not currently set an ACL to narrow it.

What this does and does not mean:

- The tool does NOT lie about it. It prints the mode it actually achieved rather
  than the mode it wanted, so a Windows user sees the real value.
- The POSIX guarantee is unchanged and still asserted at full strength.
- A Windows user on a shared machine should treat recovered work as readable by
  other local accounts until this is closed with a real ACL call.

Not fixed yet because doing it properly needs a Windows ACL API rather than a
weaker assertion, and a security property is worth stating honestly while it is
missing rather than quietly skipping the test that revealed it.

## Windows was BROKEN, was fixed, and is now GREEN (the full arc, kept on purpose)

CORRECTED 2026-07-26. An earlier version said Windows was "designed for, not
proven". The stronger truth: it failed. Verbatim from the run:

    PermissionError: [WinError 32] The process cannot access the file because it is
    being used by another process: '...\.brothermode\store.sqlite3'

Cause: sqlite connections were opened and never closed. POSIX allows deleting a
file that still has an open handle, so every macOS and Linux leg passed and the
leak was invisible; Windows refuses, which is the only reason it surfaced. That
makes it a real API gap on every platform (a long-lived process leaked a handle per
store) that only one platform reported.

RESOLVED 2026-07-27, CI run on commit ba4eca2: all eight jobs pass, including
BOTH Windows legs (3.x and 3.9). This is the first green Windows run this
project has ever had. The fix was an idempotent close() plus context-manager
support on Store and ReadOnlyStore, twelve call sites closed, and four
Windows-only test bugs that only surfaced once the suite got far enough to run:
a mock-call string comparison that repr-doubled backslashes, a write handle
opened on a memory-mapped -shm file, and a deliberate locker connection that was
rolled back but never closed.

The arc is kept here rather than collapsed into "Windows works", because the
useful part is not the outcome. The founder OVERRODE a recommendation to declare
Windows unsupported and required it as scope. That override is the only reason
any of this was found: the defect was a real API gap on every platform (a
long-lived process leaked a database handle per store) that POSIX silently
tolerates. Narrowing the supported platforms would have hidden it, not avoided
it.

What is now guarded mechanically: every test that opens a store and does not
close it FAILS, on every platform, naming the test. That check was calibrated in
both directions before it was trusted, and enabling it immediately found ten
further undisciplined sites. Two earlier attempts at that check were discarded
for being incapable of failing, which is written up in the commit.
Symlink and hardlink tests skip on Windows entirely. Read-only database behavior,
file permission semantics, and the worktree layout are unverified there.

## Paths exercised only partly

- The backup that should be written before a status file is rewritten has not been
  exercised, because in every test the tool correctly refused before reaching it.
  Refusing is the safer behavior, but the backup code path is unproven.
- The `deliveries` table and the full-length handover fingerprint ship with no
  writer. The deduplication they exist for does not exist yet. Phase 3 owns it, and
  if Phase 3 does not write it, the table should be deleted rather than kept as
  decoration.
- `send()` takes no expected version, making directives the one mutation without
  optimistic concurrency. Phase 3 owns the directive experience.

## The test suite's honest shape

Eight rounds of adversarial review plus one independent code review plus one
systematic mutation audit. The mutation audit found that fifteen tests named as
calibrated were testing a local copy of old code rather than the product, and could
never have failed; they are being deleted and the honest count reported. Treat any
test count in this repository as a claim to be re-verified rather than a
certificate.

## The correction-learning system: built through Loop 12, never run on a real day

UPDATED 2026-07-29. The paragraph below used to say the self-learning mechanism
was designed and not implemented. That is now false and would mislead a reader
who trusted it: capture, founder approval, scoped explainable retrieval,
conflict and supersession detection, retrieval and application outcome
tracking, and rework and escaped-defect grading are all built, tested, and
were driven by hand against a real, throwaway store while writing this line.
Plain-language explanation with real command output:
`docs/CORRECTION-LEARNING.md`. Technical detail: `docs/NOT-FINALIZED.md`
sections 15, 17 through 20.

What has NOT changed, and matters more than what has:

- **Never run on a real day of the founder's work.** Every command, every
  count, every test in the whole system comes from a test suite or a scripted
  probe against a throwaway store. `docs/NOT-FINALIZED.md` item 1 stays
  UNPROVEN, ranked as the highest-harm open item in the project, until a real
  dogfood window (Loop 14a) closes it. No amount of further testing closes
  this; only using it does.
- **Approval proves an answer, not an identity. UPDATED 2026-07-29 (post-audit
  LOOP 3, Model A).** Until this date the "founder-only approval" claim was
  wording, not mechanism: `bm_learn.py approve <id>` with no arguments beyond
  the id created a rule and wrote its own approval evidence. Reproduced against
  d88abcc, gate rule 61de7eb9, exit 0. Approval now needs a one-time receipt,
  minted from a real answer, bound to one candidate and to the exact rule text
  shown, valid fifteen minutes, spendable once, consumed in the same
  transaction that creates the rule. What is still NOT true: nothing checks
  WHICH human answered. Anyone who can run `grant-approval` can mint a receipt.
  The guarantee is "an answer was given about this exact thing, once, recently",
  not "the founder gave it". Read any wording that suggests otherwise as a
  defect and report it.
- **Rules approved before 2026-07-29 carry the old, weaker provenance.** The
  schema 2 to 3 migration deliberately does not annotate or invalidate them.
  If a store predates receipts, its existing rules were approved under the
  mechanism described above as broken, and their approval evidence should be
  read that way.
- **No independent second-model review.** `docs/NOT-FINALIZED.md` item 12
  stays open. The privacy and security fixes that landed in Loop 12 (the
  secret scrubber and the withholding of raw founder text, described in item
  15) were written and verified by the same model family that built the
  feature. That is real evidence, but it is not the independent adversarial
  pass item 12 asks for.
- **Two loops of the program were deliberately not built.** Evaluation
  partitions (Loop 9) and generated knowledge views (Loop 10) are both
  unbuilt on purpose, with stated reopening conditions, because at the
  current size of one founder's rule corpus (twenty to forty rules) neither
  would produce a number large enough to support a decision. Building the
  machinery anyway would make an unsupportable number look rigorous, which
  is the exact failure this program's own principle forbids. See
  `docs/CORRECTION-LEARNING.md` for the reopening conditions.
- **The optional automatic-retrieval hook (Loop 11B) is gated on the dogfood
  window, not built yet.** The skill-driven retrieval that already ships
  (Stage A, Loop 11A) has to prove itself in real use first. A hook that
  pushes the wrong rule into every prompt is worse than the opt-in retrieval
  this project ships today.
- **The old weekly scorecard's unflattering audit is still true where it was
  never addressed.**
  `docs/superpowers/specs/2026-07-26-self-learning-redesign.md` found a
  hardcoded metric that could never move, five of nine scored metrics with no
  mechanical number, thirteen law amendments against one weekly review, and
  ratings the graded party could write itself. The correction-learning system
  now gives several of those metrics a real, row-backed number
  (`bm_learn.py loop-failures`, `bm_learn.py rule-outcomes`, see
  `docs/CORRECTION-LEARNING.md`'s scorecard section), but `RUBRIC.md` itself
  is a founder-frozen template that changes only by the founder's own
  decision, so it has not been rewritten here. Do not cite the OLD scorecard
  metric 1 as evidence of anything until the founder ratifies pointing it at
  the new commands.

## What was checked by class rather than individually

The original external audit contained 63 findings. Twenty-two were reproduced by
execution. The remainder were triaged into phases by class rather than each being
re-proven. If one of them matters to a decision, re-verify it rather than trusting
this file.
