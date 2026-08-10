# LOOP G1: the work governor

Status: DRAFT for strongest-tier review. Written against `main` this
session; every symbol below was opened and confirmed, not recalled. No em
or en dashes anywhere in this document.

Ties to north star: `docs/plan/PROGRAM-PLAN-2026-08-10.md` section 5, Loop
G1 ("Brief 3.1 and Loop 2 of the brief. Unify what the inventory found
scattered"). WBS row: `docs/closure/WBS-NORTH-STAR-2026-08-10.md:154`, N1,
"One Work Governor owning budget, leases, concurrency, retries, convergence
rounds." North star objective it serves: bounded autonomy that cannot run
away, the direct answer to the 8 August runaway (`tools/bm_session_cap.py`
lines 7 to 21 state that incident's numbers).

House style mirrors `docs/plan/RELEASE-v3.1.0-PLAN.md` section 5: every
step names its files and ends with one runnable done-check.

## 1. What exists today, confirmed by file and line

Four limits live in four places, none aware of the other three:

| Limit | File:line | Scope | Confirmed |
|---|---|---|---|
| Per-unit retry ceiling | `tools/bm_store.py:3264` (`retry_ceiling INTEGER NOT NULL DEFAULT 1`), read at `:14758` and `:14863` inside `mark_unit_failed` | one controller unit | opened |
| Dispatch timeout | `tools/bm_controller.py:905` (`DEFAULT_DISPATCH_TIMEOUT_SECONDS = 1800`), read at `:960` into `self.dispatch_timeout_seconds` | one dispatch | opened |
| Signed contract ceilings | `tools/bm_autonomy.py:429` `cmd_sign`, `--token-ceiling` and `--minutes-ceiling` parsed by `_ceiling_flag` at `:397`, `done-definition` required at `:439` | one project's live contract | opened |
| Machine-wide session cap | `tools/bm_session_cap.py:67` (`CAP_DEFAULT = 4`), a PreToolUse hook gating `claude -p` spawns only, explicitly NOT subagent dispatch (module docstring, lines 26 to 33) | the whole machine | opened |

`tools/bm_controller.py:3574` `_reject` names the retry ceiling as "step
17, the circuit breaker" and confirms `mark_unit_failed` decides
retry-or-escalate on its own; `tools/bm_controller.py:2258`
`_handle_late_result`'s docstring is the same code path's own account of
a unit reaching its retry ceiling with nobody told. `tools/bm_controller.py:2434`
`_resume_result_in_and_orphans` is the orphan-fence resume path for a
crash between checkpoint and release; it is unit-scoped and does not read
the contract's ceilings at all.

None of these four reads any of the others. A unit can retry inside its
own ceiling while the contract's token ceiling is already spent; the
session cap has no idea a single session is burning through its dispatch
timeout in a loop; nothing today asks "how many units, of what class, are
in flight against this ONE work item, right now."

## 2. Architecture: EXTEND, do not add a parallel subsystem

G1 does not replace any of the four. Each stays the mechanism closest to
its own data (retry_ceiling stays a per-unit store column; the session cap
stays a hook because only a hook sees process spawns before they happen).
What G1 adds is the missing layer above them: one **policy object per work
item** that the other four consult and update, so a decision made in one
place is visible to the others before the next one acts.

```
today:      contract ceilings   dispatch timeout   retry ceiling   session cap
            (per project)       (per dispatch)     (per unit)      (per machine)
            each reads its own state, writes its own state, tells nobody

G1:         one GovernorPolicy row per work item (run_id), read and
            written by all four existing call sites, in
            tools/bm_governor.py (new, the seam; extends bm_autonomy's
            signed contract as its source of truth rather than
            re-deriving ceilings)
```

`tools/bm_governor.py` is new because no existing module owns "one work
item's aggregate state across all four limits"; everywhere else in this
plan prefers extension, and this file's own job is to BE the extension
point the other four call into, not a second copy of their logic.

## 3. Work breakdown

| ID | Step | Files | EXTENDS or NEW | Done-check |
|---|---|---|---|---|
| G1.1 | Define `GovernorPolicy`: one row per run_id, fields for token spend, minute spend, dispatch count, retry count, concurrency in flight, each read from the signed contract at `bm_autonomy.py:429` rather than re-typed | `tools/bm_governor.py` (new) | NEW, the seam | importing it against a fixture contract row returns a policy object whose four ceilings match the contract's own four fields, asserted field by field |
| G1.2 | `GovernorPolicy.admit(kind)`: one function every call site below asks BEFORE spending or dispatching. Returns ADMIT or the specific limit that refused, never a bare boolean | `tools/bm_governor.py` | NEW | a fixture at each ceiling (token, minute, dispatch, retry, concurrency) refused by name, one test per ceiling |
| G1.3 | Wire `_reject`'s retry path (`bm_controller.py:3574`) through `admit("retry")` before `mark_unit_failed` decides | `tools/bm_controller.py` | EXTENDS | `python3 tools/test_bm_controller.py` OK; a new test forces the governor's retry ceiling below the unit's own and asserts the governor's refusal fires first |
| G1.4 | Wire dispatch admission (`bm_controller.py:905`, `.960`) through `admit("dispatch")` before a new dispatch is recorded | `tools/bm_controller.py` | EXTENDS | same suite; a test with concurrency already at policy's cap refuses a new dispatch without touching `dispatch_timeout_seconds` |
| G1.5 | Session cap hook reads the governor's per-project concurrency alongside its own machine-wide count, so a work item at its own concurrency ceiling refuses even when the machine has headroom | `tools/bm_session_cap.py`, `tools/test_bm_session_cap.py` | EXTENDS | a synthetic policy at concurrency ceiling refuses a spawn the machine-wide count alone would allow; `python3 tools/test_bm_session_cap.py` OK with the new case added |
| G1.6 | Convergence-round ceiling: a work item cannot spawn a Loop C1 convergence round past a declared bound | `tools/bm_governor.py` | NEW field on the same policy object | a fixture at its round ceiling refuses round N+1, asserted before Loop C1 exists to consume it |
| G1.7 | One receipt per refusal, written through the store (ledger_write, registered in `tools/bm_effects.py`) so a refusal is itself durable evidence, not a log line | `tools/bm_governor.py`, `tools/bm_effects.py` | EXTENDS the registry pattern at `tools/bm_effects.py` (`REGISTRY["module.py"]["verb"]`) | `python3 tools/test_bm_effects.py` OK after registration; a refusal fixture produces one queryable receipt row |

## 4. Adversarial acceptance tests, per the north-star brief's Loop 2 set

Each adversary gets its own test in `tools/test_bm_governor.py` (new,
alongside `tools/bm_governor.py`). A test that only asserts the adversary
was logged, without asserting the mechanical stop, does not count.

| Adversary | What it tries | Mechanical stop asserted |
|---|---|---|
| Recursive spawn | a dispatched worker spawns another `claude -p` session | `bm_session_cap.py`'s existing machine-wide cap plus G1.5's per-item concurrency both refuse; test asserts the SECOND refusal specifically, since the machine cap alone already covers the first |
| Dead meter | `autonomy_spend` holds zero rows while real spend is nonzero (the exact 8 August failure, `bm_session_cap.py` lines 12 to 20) | `admit()` reads spend from the same source the contract itself was signed against, and the test forces a zero-row spend table to prove the governor does not silently pass on empty data |
| Absent cap hook | the PreToolUse hook is not installed or not wired | the governor's own `admit()` still refuses at the work-item level, independent of the hook; test removes the hook wiring and confirms the governor path alone stops the adversary |
| Prose-ignoring worker | a worker's own output claims it stayed in bounds while its actual dispatch count exceeds policy | `admit()` is asked before dispatch, never after, and never reads worker-authored text; test feeds a fabricated "I stayed under budget" string and confirms it changes nothing |
| Stall | a unit dispatched, no result, no further calls | G1.4's `dispatch_timeout_seconds` path still fires unchanged; test confirms G1's addition did not remove or delay the existing abandon path at `bm_controller.py:2434` |
| Retry loop | a unit fails and retries past what the CONTRACT (not the unit row) intends | `admit("retry")` refuses once the contract-derived ceiling is hit, even when the unit's own `retry_ceiling` column would still allow one more, per G1.3 |
| Orphan child | a dispatched worker's session dies mid-run, leaving a fence ACTIVE | unchanged path, `bm_controller.py:2434`; test confirms the governor's admission counters are decremented on the SAME resume so a dead orphan does not permanently hold concurrency |
| Two controllers, one work item | two controller processes both call `admit()` for the same run_id at once | the governor's write is a single committed store call (ledger_write through `bm_store.py`, not an in-memory counter); test runs two admits concurrently against a real store file and asserts exactly one wins when a ceiling allows only one |

## 5. Sizing

2 to 4 days, MEDIUM confidence, matching the program plan's own estimate
for Loop G1. Variance is concentrated in G1.7 (the ledger_write receipt
shape must satisfy both `bm_effects.py`'s registry test and whatever Loop
CC's command center later reads) and in the two-controllers adversary,
which needs a real concurrent store write, not two threads sharing one
Python process.

## 6. Remaining and Unverified

- Whether `bm_store.py` already serialises concurrent writes to the same
  run_id at the SQLite layer, or whether G1.7's receipt needs its own
  explicit lock, was not checked against `bm_store.py`'s transaction code
  this session; G1's two-controllers adversary test is the thing that
  will answer it, not this document.
- Whether Loop C1 (convergence engine, not yet built) will want G1.6's
  round ceiling shaped differently once it exists; this draft guesses the
  field, C1's own plan should confirm or revise it.
- `tools/test_bm_session_cap.py` exists (confirmed with `ls`); its actual
  assertions were not read, so G1.5's new case may need a different
  fixture shape than this draft assumes.
- The interaction between G1 and the live deny canary
  (`bm_controller.py:5023`) was not examined; both are refusal
  mechanisms and a founder-facing report may want them in one place, a
  question for Loop CC rather than this loop.
- No test suite was run by this draft, per the fence instruction covering
  this session; every done-check above is UNRUN and needs its own
  RED-then-GREEN pass before this loop is called built.
