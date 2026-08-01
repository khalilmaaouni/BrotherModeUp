# D2 deletion record, 2026-08-01

Status: CURRENT. Written by the orchestrator the hour the deletion
happened, because two of the deleted files were never git-tracked and
honesty demands the loss be named, not implied.

Deleted under Loop 1 delete-list D2 (mapping doc, ratified program,
founder-directed autonomous run):

- threads/registry.json: V1 thread registry, zero live code readers at
  deletion time (grep evidence in the mapping doc). Never tracked
  (.gitignore line 6 covers threads/). Known content, captured in the
  session transcript before deletion: mode "on" since 2026-07-25T22:47:57Z,
  one thread "store-engine" (objective: Phase 1 build tools/bm_store.py
  per the 2026-07-26 V2 design spec, state active, started 2026-07-25).
- threads/store-engine/: wave-1 scratch directory (STATE.md, digest.md,
  inbox.md, outbox.md). Never tracked. Contents NOT captured before
  deletion; what they held is superseded by the store, the committed
  specs, and the vault session logs, but the bytes are gone. This is a
  real, bounded loss and it is stated here rather than smoothed over.

Kept: threads/thread-mode.json (live MODE_FILE of bm_threads.py) and its
lock files.

Process note for the ledger: the builder's brief asked for git rm so
history would preserve the files; both paths turned out untracked, so
the builder plain-deleted, which the brief allowed but which preserved
nothing. The durable lesson (archive untracked files into docs/evidence
BEFORE any delete-list execution, as was done for STATE.md's prose under
D1) belongs in the known-mistakes ledger.
