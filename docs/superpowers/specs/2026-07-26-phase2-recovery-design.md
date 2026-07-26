# Phase 2: recovery, ratified design (2026-07-26)

Scope: replace tools/bm_autosave.sh with tools/bm_autosave.py, and make the
"your work is saved" promise verifiable instead of assumed. Every defect below
was reproduced by executing the current script (evidence in
~/Documents/BrotherModeV2-planning/DECISION-BRIEF.md section 2).

Why this phase matters most: autosave is the component a founder trusts when
everything else has already gone wrong. A backup that can silently be empty, or
that deletes files on restore, is worse than no backup, because it replaces
caution with false confidence.

## Confirmed defects this phase must close

| Ref | Reproduced behavior | Consequence |
|---|---|---|
| FA | Two git worktrees share one ref; the second snapshot replaces the first | The first worktree's work is unrecoverable |
| FC | A tracked .env is excluded from the snapshot, and the documented recover command then DELETES it from the working tree | Destructive restore, confirmed by execution |
| FD | After a deliberate return to a clean tree, the ref still points at discarded WIP | Recovery offers work the founder already rejected |
| FE | A failed git add is ignored; an EMPTY tree is committed and replaces a good snapshot | Total silent loss of the safety net |
| FI | AUTOSAVE_EVERY of 0 or a non-number crashes the hook with exit 1 | Breaks the never-block-the-session promise |
| F2b | Invoked from a subdirectory, the snapshot silently omits root-level changes | The "entire working tree" claim is false |
| J | The next session prints "your files are autosaved" without checking that a snapshot exists | An honesty-gate failure: the claim is unearned |

## Design

1. PYTHON, NOT SHELL. Windows support is ratified scope and shell scripts do not
   run there. bm_autosave.py uses subprocess to call git (git is the only
   external binary; SECURITY.md's no-network claim is preserved because every
   call is local, and the new network gate test must be extended to allow
   subprocess in THIS module by name while still banning network modules).
   Note: this is a deliberate, documented exception to the no-subprocess rule,
   recorded in SECURITY.md in the same change, not a silent widening.
2. ONE ROOT. Resolve git rev-parse --show-toplevel before anything else; every
   git call runs with -C <toplevel>. Refuse (exit 0, warn) when there is no
   repository, since advisory surfaces fail open.
3. NAMESPACED REFS. refs/brothermode/autosave/<worktree_id>/<session_id>/<stamp>
   plus a per-worktree latest pointer. worktree_id is a short hash of the
   worktree path from git rev-parse --git-common-dir, so linked worktrees never
   collide (FA).
4. EVERY RETURN CODE CHECKED. git add, write-tree, commit-tree and update-ref
   each have their status inspected; any non-zero aborts the snapshot WITHOUT
   touching the existing latest pointer (FE). The empty tree sha
   (4b825dc642cb6eb9a060e54bf8d69288fbee4904) is refused explicitly as a
   belt-and-braces check.
5. EXCLUSIONS ARE ADDITIVE, NEVER SUBTRACTIVE. The temporary index starts from
   HEAD (git read-tree HEAD), then working-tree changes are applied, so a
   tracked file that is deliberately not re-added still exists in the snapshot at
   its committed content (FC). Secret-shaped paths are excluded from UPDATES,
   never removed from the tree.
6. RECOVERY IS NON-DESTRUCTIVE BY CONSTRUCTION. The recover command creates a
   NEW git worktree at a temporary path from the snapshot and prints its
   location. It never writes into the live working tree. The old in-place
   git restore command is deleted, not documented with a warning (FC).
7. CLEAN TREE CLEARS THE POINTER. When the working tree matches HEAD, the latest
   pointer is updated to reflect that (or cleared), so a stale WIP snapshot can
   never present itself as current (FD).
8. RETENTION. Keep the last N snapshots per worktree (default 10) plus latest;
   prune older ones by deleting their refs so git can eventually collect them.
   Never prune the only snapshot.
9. RECEIPTS. Every successful snapshot writes a row into the store's
   autosave_receipts table (schema already shipped in Phase 1) recording
   worktree id, session id, snapshot sha, tree sha, source HEAD, captured count,
   excluded count, and timestamp. The compact hint prints "your files are
   autosaved" ONLY when a receipt exists for THIS worktree from THIS session,
   and otherwise prints what actually happened (J).
10. CONFIGURATION CANNOT CRASH. Every environment variable is parsed
    defensively: a non-numeric or zero interval falls back to the default with
    one warning line, and the process exits 0 no matter what (FI). A test asserts
    exit 0 for: unset, 0, negative, non-numeric, and absurdly large values.

## Honest scope limits, stated in the docs rather than discovered later

- git add -A does not capture ignored files or uncommitted content inside nested
  repositories and submodules. The README and SECURITY.md wording changes from
  "entire working tree" to exactly what is captured, with the exclusions named.
- The snapshot is local only and is never pushed. That remains gated by the
  no-network test.

## Done-check for this phase

1. python3 tools/test_bm_autosave.py green, containing one calibrated test per
   row of the defect table above (reinject the old behavior, prove the right
   test fails).
2. The V1 shell script is REMOVED in the same change as its replacement lands,
   with hook wiring updated in docs/SETUP.md, so two autosave paths never coexist.
3. python3 tools/test_bm.py green (the network gate updated for the documented
   subprocess exception).
4. A manual founder-legible check documented in one line: dirty a file, trigger a
   snapshot, run recover, and see the file in a separate folder while the live
   folder is untouched.
