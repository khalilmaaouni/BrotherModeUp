# The single-writer law, fences, and the harness

LOAD WHEN: a writing agent is about to be dispatched, or files could be touched by more than one writer at once.

(Extracted verbatim from SKILL.md section 5; see SKILL.md for the full law.)

## 5. The single-writer law, fences, and the harness
One writer per file, ever. FENCE THEN DISPATCH, never the reverse: the fence line
is written to STATE.md BEFORE the agent launches and carries the FIVE-FIELD
CONTRACT (objective, output format, tool guidance, boundaries, termination
condition) plus files, agent id, session id, timestamp (fences acquire in one
consistent file order; there is deliberately NO time-based expiry, because a law
promising a lease that expires while no code expires anything is worse than no law:
a fence is released by an explicit park, complete, adopt, or transfer, and a dead
session's fence is ADOPTED at close by the orchestrator, never by a clock),
declared tier, and check: a runnable done-check on the outcome plus, for agentic
work, process assertions (max tool calls, required call order, no failed actions)
so a tier overrun or a skipped step is caught mechanically at the boundary rather
than at close-time review (adopted from the eval assertions of Vercel's eve agent framework). A fence
CLOSES only with an
evidence block inline in the registry: the exact command run and its last lines.
The new fence must be disjoint; overlap means queue, never parallel. Every writer brief
includes a mechanical pre-write step: compare its fence files' mtimes against its
dispatch timestamp and abort on any foreign write. STATE.md itself carries a session
lease (session id plus heartbeat); a session finding a fresh foreign lease goes
read-only on the registry and coordinates through appends. Worktree landings re-run
the suite gate on the MERGED tree before the merge is recorded. Read-only
agents run freely. After any agent kill (session limit, error): the tree keeps its
edits; assess git status first; resume the same agent by id, or the session by the
session id on its fence line: NEVER respawn fresh while a transcript exists
(respawn redoes the exploration and loses state). At close the orchestrator
enumerates dead leases and ADOPTS or reassigns their unlanded fence work same session
(unlanded work once sat dropped for a day after its agent died). A fence line flips to LANDED in the
landing commit itself, never later: stale registries breed false conflicts.
The harness that prevents rework, contradiction, and noise: the fence registry lives
in STATE.md and is updated at every dispatch and landing; specs are the single source
of truth and agents POINT at them (path plus line range), never restate them, because
restatement is where contradictions breed; return contracts per the section 4 hard
cap so noise dies at the boundary; the orchestrator owns the final
gate: agents self-gate, but nothing merges until their claims are verified against
the actual files, and a deliverable arriving without its done-check satisfied is
rejected back to its agent with the gap named, never quietly patched or accepted.
Every rejection states the improvement path; no work is left broken without one.

