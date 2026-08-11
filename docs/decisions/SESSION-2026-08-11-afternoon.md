Status: CURRENT

# Session decisions, 2026-08-11 afternoon

Session `bm1-6ed31697927542d2dc2aab16`, the successor to the morning and
midday sessions. Decisions recorded at the moment they were taken, per the
order-of-work law. No em or en dashes.

## D-A1. The founder's waiver meets ratified decision 27

CONTEXT. The founder invoked BrotherMode with "continue work on all streams
in the right orchestration order until I come back", plus "full control over
everything including my PC, software and I waive any limitation". Ratified
decision 27 of the same day says: no unattended stretches until SD2 catches
a seeded stall end to end. SD2 is being built right now, so that condition
is not met, and the founder is leaving. The two instructions collide.

DECISION. Continue working, with the stretch bounded rather than open. What
the waiver changes: the self-imposed working ceiling is lifted for this
stretch, and both lanes run to their planned edge. What it does NOT change,
because ratified law outranks a blanket line and a conflict is surfaced
rather than silently resolved (the same boundary the 2026-08-11 02:2x
waiver was given):

- The spend guard hook and the session cap hook stay armed. A refusal from
  either is the founder's standing instruction speaking.
- Unattended dispatches run on the cheaper tiers. Lane B's builder is
  sonnet for exactly this reason, declared in its brief. The one opus
  dispatch (Lane A, SD2 slice 1) was launched while the founder was still
  at the keyboard.
- Nothing destructive, nothing irreversible, no force operations.
- Pushes happen only at a quoted green gate, direct to main per standing
  policy, with the secret scan and dash scan gates intact.

ALTERNATIVES CONSIDERED. Stop and wait for the founder's return: rejected,
because it disobeys a clear, current instruction to keep working, and the
work in flight is fenced, reversible and gated. Run everything unbounded on
the strongest tier: rejected, because the 8 August runaway is what the
spend laws were written from, and a waiver of limits is not a waiver of the
controls that make a waiver survivable.

FLIP CONDITION. The founder amends this awake, or SD2's kill-test passes
and decision 27's own condition is satisfied, at which point the conflict
dissolves on its own.

## D-A2. Lane B opens on CX Phase 1 rather than Wave 2 graph work

CONTEXT. The ratified Wave 1 lane map (decision 24) says Lane A is SD2 then
CC, Lane B is SL-quick then CX. SL-quick closed at 943c59a.

DECISION. Lane B opens CX Phase 1, scoped to spec tasks 1, 4 and 6: one
host-neutral path resolution seam, the adapter protocol definitions, and
Claude fixtures locking today's behavior. Phase 1 is a nine-task phase; the
three chosen are the ones that close inside a single loop and that every
later Codex phase depends on. The rest of Phase 1 is named, not dropped.

WHY THIS SLICE. The spec's own task 2 forbids moving code for aesthetics
and demands the wrapper prove tests still pass first, so the seam is
exactly the piece that can land without changing observable behavior.

FLIP CONDITION. If the wrapper cannot preserve a caller's observable
behavior, that caller is deferred by name rather than changed, and the
deferral list decides whether Phase 1 needs a founder decision.

## D-A3. The Codex spec lives outside the repository

FOUND. `CODEX_PORT_AND_HYBRID_HARNESS_IMPLEMENTATION_SPEC.md` is not in this
tree. It sits at `Documents/ChatGPT/BrotherModeUp/`, and the Phase 0
documents cite it by name without recording where it is, so a successor
would have hunted for it exactly as this session did.

DECISION. Record the path here and in PROJECT.md, per the project-boundary
law that a project's own resources must be findable from inside the
project. Copying the spec into the tree is NOT done: it is a third-party
document and the repository is public.
