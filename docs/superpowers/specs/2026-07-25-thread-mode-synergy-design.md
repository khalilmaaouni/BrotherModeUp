# Thread mode and the core: one work record

Design spec, 2026-07-25. Status: awaiting founder approval before any implementation.

## Why this exists

Thread mode shipped as a working capability and immediately scored badly on the
thing it was supposed to prove: it barely touches BrotherMode's own laws. Measured,
not asserted, by grepping the shipped tool:

| Term in `bm_threads.py` | Occurrences |
|---|---|
| `digest` | 23 |
| `STATE.md` | 10 |
| `telemetry` | 3 |
| `fence` | 3 (prose only) |
| `tier`, `budget`, `outcomes`, `vault`, `autosave` | 0 |

So thread mode is a parallel system standing beside the constitution rather than
being part of it. Worse, it created a second registry of "who owns what work",
which directly contradicts the skill's own single-source rule: the fence registry
in `STATE.md` and the thread registry in `thread-mode.json` describe the same idea
and can disagree.

Two defects found by self-review on the day thread mode shipped make the same
point from the other side: a secret leaked into a digest (the third appearance of
that bug class in a week) and a registry race lost two of three concurrent thread
registrations. Both were possible because thread mode reimplemented, badly, things
the core already knew how to do.

## What this changes

One record type, one registry, one place where the hard logic lives.

```
work record
  id            payments
  lifetime      persistent (a thread)  |  ephemeral (an agent dispatch)
  owner         session id
  objective     one line
  files         ["api/pay.py", "api/hooks/**"]    a real list, not prose
  tier          T1 | T2 | T3
  lease         claimed_at + ttl
  state         active | parked | landed | adopted
  check         the runnable done-check
  evidence      command + last lines, filled at close
  decisions     [{topic, text, ts}]
  digest        the always-current handover
  spend         tokens attributed from telemetry
  schema        version integer
```

A thread is this record with `lifetime: persistent`. A fence is the same record
with `lifetime: ephemeral`. Nothing else differs. Everything already true of
fences becomes true of threads, and the reverse.

## What the unification buys, law by law

- **Section 5, the single-writer law.** `files` is a machine-readable list, so
  overlap between two claims is computed rather than eyeballed, and a colliding
  claim is refused with the conflicting record named. This was impossible while
  the registry was prose, and it is the largest safety gain in this design.
- **Section 3, effort tiers.** The tier lives on the record, so a T1 behaving
  like a T3 becomes visible instead of remembered.
- **Section 4, token budgets.** `spend` is attributed per record from existing
  telemetry, turning an advisory budget into a measured one.
- **Section 8, the learning loop.** Overlap refusals, decision clashes, and tier
  overruns become counted events the weekly review can score.
- **Section 15, scoring.** Plan-time tier and check sit on the same object as the
  landed evidence, so the plan-versus-landed re-score reads one record.

## Founder decisions, locked

1. **Unify.** A thread is a long-lived fence; one registry, one source of truth.
2. **Structured source, rendered view.** A machine-readable registry is the truth;
   a generated markdown view keeps it human-reviewable.
3. **Coherence by tagged decisions.** Every decision carries a topic tag; a second
   record deciding an already-decided topic raises a CLASH on the dashboard, the
   same day, deterministically, with both decisions shown side by side.
4. **Passive token accounting with a revert gate.** Spend is attributed per record
   against the pre-thread baseline. If the measured signal does not improve,
   thread mode is reverted rather than defended.
5. **Threads first, ephemeral fences later**, time-boxed (see Migration).
6. **A new module** (`bm_registry.py`) owns the registry, rather than growing an
   existing file.
7. **A pre-write redaction gate** ships with this work.

## Components

**`bm_registry.py` (new).** Owns the record type and the three operations that
are genuinely hard:

- `claim(record)` registers work and refuses on file overlap, naming the
  conflicting record.
- `decide(id, topic, text)` records a tagged decision and returns CLASH when
  another live record already decided that topic.
- `absorb()` drains digests into the project `STATE.md` for the lossless off.

It also renders the human view. It is pure file I/O: no network, no subprocess,
redaction applied at every write, every path exits 0.

**`bm_threads.py` (existing, becomes thinner).** Keeps thread lifecycle (`on`,
`off`, `start`, `checkpoint`, `send`, `dashboard`, `adopt`) and the mailbox files.
Delegates claim, decide, absorb, and render to the registry.

**`bm_telemetry.py` (one hook).** Attributes a session's spend to a record id so
the `spend` field fills itself. No other change, so its audited no-subprocess and
no-network properties stay intact.

**`threads/REGISTRY.md` (generated).** The always-current human view. Never
hand-edited, per the existing rule that generated files are edited at their source.

## Data flow

Claim, and the registry grants or refuses with the conflicting record named. Work.
Checkpoint, which redacts, updates the digest, and runs the clash check so a
contradiction surfaces on the dashboard the same day. Telemetry attributes spend
as work proceeds. Then one of three endings: land with an evidence block, park on
`off` with the digest absorbed into `STATE.md`, or be adopted by the chief if the
thread dies.

## Invariants

- **Never block.** A registry failure degrades to a printed warning; it never
  stops a work session. Every path exits 0.
- **Redact at the write.** Every text-bearing field passes through redaction
  before it touches disk, inside the registry, so no caller can forget.
- **Lock every read-modify-write.** File locking around registry mutation, with
  the active-record cap re-checked inside the lock.
- **Lossless exit.** Digests stay current, so `absorb` never requires the thread
  to still be alive.
- **Two modes.** Overlap refusal is advisory locally and strict in CI, matching
  the mode split already shipped in `bm_score.py`.
- **Versioned schema.** The record carries a schema version so a later change
  migrates rather than breaks.

## Testing

- **Overlap**, table-driven: exact path, nested directory, glob, disjoint, and
  case where one record's glob swallows another's file.
- **Clash**: two records deciding the same topic flags; different topics stay
  silent; the same record revising its own decision does not self-clash.
- **Redaction**: a secret placed in an objective, a decision, or a digest never
  reaches disk, and the surrounding real content survives.
- **Concurrency**: N parallel claims all register, and the cap holds under the
  lock.
- **Lossless off**: every digest lands in `STATE.md`, threads are parked and not
  deleted, and decisions and next intents survive verbatim.
- **Forward compatibility**: a record with an unknown field or a newer schema
  version does not crash the tools.
- **Pre-write gate**: a test counts write-shaped lines (`open(..., "w")`,
  `os.open`, `.write(`) in each `tools/*.py` file (test files excluded) and
  compares the count against a reviewed inventory in `tools/write_sites.json`.
  It fails when a count changes, which forces a human to look at the new site
  and confirm it redacts before updating the inventory. This does not prove
  redaction and is not dataflow analysis: it does not see non-`.py` files (so
  `tools/bm_autosave.sh` is outside it), and it cannot follow a shape where a
  file is read and then appended to elsewhere. It is a review-forcing
  inventory, not a proof. Even so, it is the mechanical answer to a bug class
  that appeared three times in one week and is the reason the
  learning-from-record score was a 3 out of 10.

## Migration and time-box

Threads use the structured registry immediately. Ephemeral agent fences continue
to work exactly as they do today and migrate only after threads have proven the
model on real work.

**Named review date: 2026-08-08.** On that date, one of three things happens and
is recorded: ephemeral fences migrate, the migration is deliberately deferred with
a reason, or the whole design is reverted. Two coexisting mechanisms is the exact
duplication this spec exists to end, so it is not allowed to persist unexamined.

## Revert criteria

Per the validation-gated amendment rule, this work names the signals it must move:

- **Recovery and coordination**: zero silent losses of thread context, and at
  least one overlap or clash caught that would previously have gone unnoticed.
- **Token economy**: per-project spend under thread mode compared against the
  pre-thread baseline in the existing telemetry.

If, at the 2026-08-08 review, the coordination signal shows no caught events on
real work and the token signal has not improved, thread mode and this registry are
reverted rather than defended, and the reason is recorded in the pending-amendments
note so it is not re-proposed without new evidence.

## Not in scope

Distributed locking across machines, a coordination service, multi-user identity,
and org governance. This system targets a solo founder with occasional small-team
sharing; those items serve a different user and would cost the simplicity that
makes this usable.

## Honest risks

- The record becomes the most important object in the system, so a bad schema
  decision is expensive later. Mitigated by the version field and the threads-only
  start, not eliminated.
- Path-overlap logic is easy to get subtly wrong with globs and symlinks. Mitigated
  by table-driven tests, and any uncovered case is a real defect.
- Clash detection is topic-tag matching, not semantic understanding. It catches two
  threads deciding the same named topic; it will not catch two threads making
  incompatible decisions under different topic names. Stated plainly so it is not
  mistaken for a guarantee.
- Thread mode has still never run on a real project. Everything here is reasoned
  from simulation and code inspection.

## Success criteria

The design succeeds if, at the 2026-08-08 review: no thread context has been lost;
at least one overlap or clash has been caught mechanically on real work; the token
signal is at least neutral against baseline; and `bm_threads.py` is smaller than it
is today, because logic moved to where it belongs rather than accumulating.
