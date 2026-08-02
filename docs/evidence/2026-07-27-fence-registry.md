# Fence registry, session 2026-07-27 (Loop 1, audit blockers)

HISTORICAL. Do not read it as current state. This was a hand-written fence registry from one session,
kept because its orchestrator note records a real law violation
(fences written after dispatch rather than before) and deleting a
self-critical record is how a lesson stops being learned. Superseded by:
the generated registry in STATE.md, which is rendered from the store.
Moved out of the repository root on 2026-08-02: a dated one-off session
artifact at top level is the first thing a stranger sees, and it is not
what this project wants to introduce itself with.

ORCHESTRATOR NOTE, recorded rather than hidden: these three fences were written
AFTER dispatch, not before. The law is fence-then-dispatch and I inverted it.
No collision resulted (the write sets are disjoint and were chosen deliberately),
but the check that would have CAUGHT a collision ran after the risk was taken.
Same class as giving two agents one file earlier today.

| Fence | Writable files | Findings | Tier | Done-check |
|---|---|---|---|---|
| L1-autosave | tools/bm_autosave.py, tools/bm_telemetry.py, tools/test_bm_autosave.py | 1, 13, 16 | T2 | python3 tools/test_bm_autosave.py ends OK |
| L1-store | tools/bm_store.py, tools/test_bm_store.py | 5, 11, + raw name lookup API | T2 | python3 tools/test_bm_store.py ends OK |
| L1-fence | tools/bm_fence_hook.py (new), tools/test_bm_fence_hook.py (new), docs/HOOKS.md | 8, 8B | T2 | python3 tools/test_bm_fence_hook.py ends OK |

Disjoint by construction. bm_store.py is READ by L1-fence and WRITTEN only by
L1-store. Cross-fence dependency declared at dispatch: L1-store adds the exact
name lookup API that a later thread-CLI fence (findings 9, 10, 12) will call.

Queued, NOT started, needs L1-store to land first:
  L2-threads: tools/bm_threads.py -> findings 9, 10, 12
  L2-release: VERSION, CHECKSUMS.sha256, docs/RELEASE.md -> finding 6
