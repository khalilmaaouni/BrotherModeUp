# Known limits, stated plainly (2026-07-26)

What this project does NOT do, has NOT proven, or has only partly checked. This
file exists because an unstated gap is a failure even when it is small, and because
the single most useful thing a handover can contain is the list of things the last
person was not sure about.

## The biggest one: the new engine is not connected to anything yet

`tools/bm_store.py` is built, hardened across eight rounds, and covered by a suite
that has been mutation-tested. It is also **not used by any other file in this
project**. The tools that actually run on the founder's machine today
(`bm_threads.py`, `bm_registry.py`) still use the old JSON registries with every
defect the original audit found. Phase 3 is what rewires them.

Practical consequence: every operating restriction from the original audit still
applies to daily work right now. Run commands from the repository root, do not
reuse a thread name, avoid glob fences, do not run two worktrees of one repo in
parallel sessions, and never restore an autosave snapshot in place without
inspecting it first in a separate worktree.

## Never run on a real project

Unchanged from the previous handover, and it is the honest headline. Everything
here rests on tests, adversarial execution, and simulated lifecycles. No day of
real founder work has yet been done through the V2 store.

## Continuous integration has never executed

The workflow is configured for Linux, macOS, and Windows across two Python
versions, and the action versions are pinned to verified commit hashes. None of it
has run, because nothing has been pushed yet. The first push is also the first
real test of that configuration, and it may well fail.

## Windows is designed for, not proven

No Windows machine was available. Windows behavior was proxied by substituting the
Windows path module and forcing the platform identifier, which caught a real defect
(directory containment silently failing there) but is not the same as running.
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

## The self-learning mechanism is designed, not built

The audit of it is in `docs/superpowers/specs/2026-07-26-self-learning-redesign.md`
and it is unflattering: a hardcoded metric that can never move, five of nine scored
metrics with no mechanical number, thirteen law amendments against one weekly
review, and ratings the graded party could write itself. The redesign is approved
but not implemented. Until it is, do not cite the scorecard as evidence of
anything.

## What was checked by class rather than individually

The original external audit contained 63 findings. Twenty-two were reproduced by
execution. The remainder were triaged into phases by class rather than each being
re-proven. If one of them matters to a decision, re-verify it rather than trusting
this file.
