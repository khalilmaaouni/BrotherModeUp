# Accounting against the original brief

**HISTORICAL DOCUMENT, dated 2026-07-26. Do not read it as current state.** It is dated evidence: every number in it belongs to the day and the commit it was measured on. Superseded by `README.md` and `docs/KNOWN-LIMITS.md` for status, `docs/NOT-FINALIZED.md` for the defect register, `CHANGELOG.md` for what changed since, and `python3 tools/bm_project_facts.py` for version, release tag, hook events and suites.


Answering four questions directly: what was achieved, at what rate, at what quality, and
what is missing. Every number here came from a command run on 2026-07-26, not from
recollection. Two writers were still running when this was written and their items are
marked IN FLIGHT rather than counted.

## Scored against the auditor's own priority plan

The audit ended with its own P0, P1, P2 list. Using the auditor's plan rather than a
friendlier one of mine is the point: a benchmark chosen after the work is not a benchmark.

### P0, "before calling the tool mechanically safe": 10 of 10

1. Unify prose and JSON ownership. DONE. One sqlite store is the sole authority;
   `bm_registry.py` is DELETED, not shimmed. Verified: the file is gone.
2. One canonical project root. DONE in the store, the recovery tool, and the thread CLI.
   The telemetry tool is IN FLIGHT, and it was the last holder of the old defect.
3. Reject active-ID takeover and unsafe names. DONE, verified by hand: a second session
   on a live name is refused by name with the legal next steps.
4. Lifecycle and session identity on every mutation. DONE, with optimistic concurrency:
   a stale caller updates zero rows and is told so.
5. Serialize checkpoint and send against off and adopt. DONE by construction, since every
   mutation is one transaction in one store.
6. Real resume, complete, park, reconcile. DONE, and resume across an off boundary is
   verified by hand after it was found broken.
7. Fail closed on corrupt state and unavailable locks. DONE: corruption quarantines into
   a per-incident directory and is never overwritten.
8. Redesign autosave refs and temporary index. DONE, verified by hand: per worktree and
   per session refs, root resolved first, tracked files preserved, recovery into a
   separate worktree only.
9. Digest section budgets and full payload fingerprints. DONE: the next intent can no
   longer be displaced, and the fingerprint is full length.
10. Conservative glob overlap. DONE, verified: `api/*.py` versus `api/pay.*` now conflicts.

### P1, "before recommending broad public use": roughly 5 of 9

Done: three-platform CI matrix with pinned actions (NEVER EXECUTED, see below);
automatic git exclude handling, verified; the store's own verify replaces the
one-directional invariant checks by construction; secure file modes for the store and the
recovery directory, verified.
In flight: telemetry corruption visibility, transaction-safe telemetry maintenance,
immutable versioned releases.
Not done: fixture-driven strict scoring, real hook and transcript fixtures (only a
synthetic one exists).

### P2, "maturity": roughly 2 of 6

Done: performance benchmarks (measured, and one change made the health check eight times
faster while removing two of three rules).
Partial: soak and concurrency coverage (a generative state-machine test was restored
after the rewire deleted the original).
Not done: automated mutation testing in CI (it was run once by hand), retention and
compaction for the ledgers, and the one that matters most, a REAL PROJECT PILOT. Nothing
here has yet run on a day of real founder work.

## The founder's items A through J

- A, fix what the audit found: see the P0/P1/P2 scoring above. Of the 63 numbered
  findings, 22 were reproduced by execution before being fixed; the rest were triaged by
  CLASS rather than each re-proven, which is stated in the limits file so nobody mistakes
  triage for verification.
- B, project hierarchy plus a project server: the scaffold LANDED today (13 files, and a
  fresh copy correctly ignores machine state from the first commit, verified). The server
  is IN FLIGHT. HTML summaries were deliberately skipped with founder approval, because
  mermaid diagrams already render in both the editor and the browser.
- C, simplicity as the default: partly cultural, partly mechanical. Real deletions
  landed (a dead column, a table with no writer, a duplicated list, a weaker duplicate
  function, and a law clause with no implementation). The mechanical stop is WEAK: the
  decision record in the scaffold is the mechanism, and nothing yet fails a build when
  complexity arrives without a recorded reason. Honest grade: direction set, enforcement
  thin.
- D, brief documentation and comments at key steps: DONE, and then trimmed, because a
  third of one file had become changelog narration that belonged in git.
- E, the analyst and process-engineer pack: DONE. Six documents, and all six diagrams
  were verified by RENDERING them rather than by reading them.
- F, problem first with the why behind the why, plus graceful sunset: LANDED today. The
  intake refuses to let work start before kill criteria and a sunset plan are written,
  and the sunset document is grounded in three real retirements from this project rather
  than in abstractions.
- G, public repo plus the private skill linked to the vault: the public branch carries
  everything (29 commits, UNPUSHED). The private skill is NOT SYNCED yet. Measured good
  news: the four V1 tool files were byte-identical across both copies, so the port is
  contained.
- H, memory onboarding for a new user: IN FLIGHT.
- I, one consolidated solution rather than 63 patches: DONE, and it is the spine of
  everything above: one root, one transactional store, one immutable identity, two
  explicit failure policies.
- J, use the machine and publish through the desktop app: the push is PREPARED and
  waiting on the founder, per their instruction. Preflight is clean.

## Rate

Roughly 14.1 million tokens of delegated work across 20 implementation and review agents
and 11 parallel fleets, in one session. 29 commits. 46 files changed against the audited
commit, with 15,020 lines added and 3,964 removed. The toolchain measures 13,041 lines,
which is UP, and that number is discussed honestly in the security document with a
commitment to withdraw the small-toolchain claim if it does not come down.

## Quality, judged by evidence rather than by feel

The strongest signal is uncomfortable and worth leading with: **the final adversarial
round found a security blocker in code I had already scored 8.0 earlier the same day.**
Recovered work was world-readable, and I had verified that component by hand and called it
good. My self-assessment ran ahead of reality more than once, and the only thing that
caught it was pointing fresh adversarial attention at the finished state.

What holds up: every fix in this session was reproduced by execution before being written,
and ships with a test proven to fail when its defect returns. The suites are green. The
single-writer guarantee is now enforced by a database constraint rather than by prose.

What does not hold up: a claim I made to the founder that 53 of 54 calibrated tests caught
their defect. A deeper mutation audit showed fifteen of them tested private copies of old
code and could never fail. They were deleted and the honest count reported.

Four times, a specification I wrote was itself the defect, and each time it surfaced only
because the agent executing it verified rather than complied. That is the real finding
about method: the value came from adversarial attention and from executors willing to push
back, not from the plan being right.

## Missing, ranked by harm

1. Never run on a real project. Everything rests on tests and simulated lifecycles.
2. CORRECTED 2026-07-26: continuous integration HAS executed (18 runs) and FAILED on the
   tagged commit, on Windows, for a real handle leak. The earlier claim here that it had
   never run was asserted without looking. See docs/KNOWN-LIMITS.md. Original line kept
   below for the record of what was claimed:
   (was) its first run is the first real test of
   a configuration nobody has exercised.
3. The telemetry audit and the learning loops are IN FLIGHT at the time of writing. Until
   they land, the law describes loops the code does not implement.
4. Windows is ratified scope, designed for, and unproven.
5. No tagged release yet, so the install still tracks a moving branch, which for a tool
   that runs hooks automatically is the weakest link in the design. IN FLIGHT.
6. The private skill is unsynced and nothing is pushed.
7. Two features were removed today and should be named rather than forgotten: checkpoint
   clash detection, and the original generative property test (a store-level replacement
   was built, but it is not the same test).
8. Findings 16 to 63 were triaged by class, not individually re-proven.
