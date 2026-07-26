# Pre-release fix round: close the loops that already have both ends

From the optimization, computer-science, and synergy review of 2026-07-26, plus one
defect the orchestrator reproduced and fixed immediately. Founder directive: full
review, then a rigorous adversarial check, then release.

The synergy lens's verdict is the frame for this round: this is one hardened component
and two neighbours, not yet one system. Most of what follows connects ends that already
exist, or DELETES surface that has no consumer. Very little of it adds anything.

## Already fixed by the orchestrator before this round (do not redo)

RETENTION PRUNED THE NEWEST SNAPSHOT. Snapshot refs were sorted as whole strings, so the
session id outranked the timestamp and a session whose id sorted early was treated as the
oldest work in the project. Reproduced: ten snapshots from one session, then the newest
from another, and the pruner deleted THE NEWEST while keeping all ten older ones. Fixed
by sorting on the stamp alone and verified: the newest snapshot survives with its content
intact. A calibrated test for this is still MISSING and is item A below.

## GATE A: a calibrated test for the retention defect

Reinject the whole-refname sort and confirm the right test fails. Two sessions, ten
snapshots from the one whose id sorts LATE, one newer snapshot from the one that sorts
EARLY, then prune and assert the newest ref survives with its content.

## GATE B: verify's STATE.md check never opens STATE.md

verify() re-renders the view from the rows it just read and asserts each active uuid
appears in that string, which is a tautology. Executed: deleting STATE.md entirely, and
overwriting it with garbage, both leave verify reporting healthy. Fix: read the file and
search its generated block, treating an absent file as a problem. If drift detection is
out of scope, DELETE the sixteen-line loop rather than keep a check that cannot fail.

## GATE C: a missing dependency commits the work and then reports failure

With bm_telemetry.py absent, a claim COMMITS and the CLI then exits 1 with an uncaught
RedactionUnavailable, so the user is told the operation failed while the record exists.
Fix: catch it before OwnershipRefused, degrade the report to fixed text the way _warn
already does, and never let the reporting path change the outcome of committed work.

## GATE D: the handover says "Files: (none)" for a record holding a live fence

render_digest builds its Files section from a free-text note and never reads the claims
table, while the state view and the handover payload both read the real paths. A
handover that omits the fence is the one field a resuming session most needs.

## GATE E: the compaction hint claims safety it never checked, and names a deleted file

The hint prints "Your files are autosaved" unconditionally on every compaction resume,
and points at bm_autosave.sh, which Phase 2 deleted. bm_autosave.has_receipt exists for
exactly this check and nothing calls it. Fix: print the recovery line only when a receipt
matches this worktree and session, and name the command that exists. This is the same
honesty defect the Phase 2 spec named and it is still live in the telemetry tool.

## GATE F: a receipt outlives the snapshot that made it true

Reproduced: thirteen sessions, retention ten, and the pruned session's receipt row
survives, so has_receipt reports safety for work whose ref is gone. Fix: delete the
receipt rows for refs the pruner deletes, in the same call.

## The optimization, measured (8x, and it DELETES rules)

paths_overlap re-normalizes both sides on every call although both arrive canonical.
Measured: verify at 1000 active claims falls from 1621.6 ms to 202.4 ms, and building
500 records falls from 10381 ms to 2460 ms. The change splits it into a coverage key
plus a prefix comparison, which removes two of its three rules. Net thirteen lines added
for eight times the speed and less logic. Take it.

Add the transitions index, and note the trap the reviewer proved: adding an index to the
DDL alone is a silent no-op on an existing store, because schema creation does not run
there. It must also be executed on open, which is idempotent and measured at 0.006 ms.

## Deletions, all with no consumer (this is the simplicity dividend)

- ttl_hours: the law promises a fence past its TTL is treated as released, and nothing
  anywhere expires anything. Executed: a claim with a TTL of 0.36 seconds still blocks a
  second claim a second later. Delete the column, the sentinel, the CLI flag, and the
  reclaim branch, and STRIKE THE CLAUSE FROM THE LAW in the same change, because a law
  that describes behavior the code does not have is worse than no law.
- the deliveries table and the handover fingerprint: no writer, and the limits document
  already committed that Phase 3 would either write it or it would be deleted.
- claims.is_glob: written on every insert, read back, and never consulted.
- SECRET_GLOBS in the autosave: a hand-copied second spelling of the pathspec list,
  provably derivable from it in one line.
- _atomic_write_text: a weaker duplicate of bm_telemetry.atomic_write (no directory
  fsync, catches only OSError). Delegate to the owner and delete sixteen lines.

## Wiring, cheap and high value

- write_state_view has ZERO callers, so the human-readable status file is never
  regenerated. Call it from the dashboard and after each mutating command.
- The state view prints an eight-character prefix and no version, while every mutating
  command needs the full identifier and the version. Print both, so a human can act on
  what they read.
- The autosave writes its receipt with hand-written SQL on the store's connection,
  bypassing the one function that separates a busy database from a corrupt one. Give the
  store a method and call it.
- has_receipt opens a WRITABLE store to answer a read question, which can create the
  thing it claims to check. Use the read-only class.
- A snapshot can write its receipt into ANOTHER project's store when the root variable
  points elsewhere. Warn and skip when the resolved root is not the snapshot's tree.
- Session start surfaces nothing about store health, not even an unacknowledged
  quarantine. One line, silent unless there is a real problem.

## Restore what the rewire cost

The generative property test was deleted with the V1 registry it was bound to. It
historically found a defect nobody had written down, so a store-level replacement is
owed: random legal operation sequences against the store, asserting the invariants after
every step, biased toward reuse-after-close and restart-while-live. Calibrate it by
reinjecting two known defects and confirming it fires.
