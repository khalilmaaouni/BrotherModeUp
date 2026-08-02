# Full-Auto Mode, Phase 2 design (the autonomy contract and the question policy)

Status: CURRENT, and NOT YET IMPLEMENTED. Written 2026-08-02 by the
orchestrator (Fable) while the Phase 1 fleet was running. Ratified input: the
founder answered the autonomy window on 2026-08-02 choosing
reversible-everything with the five floors retained. Nothing in this document
exists in code yet: it is the design Phase 2 will be built against, and it is
deliberately held behind Phase 1's migration.

Dependency, stated up front: this phase writes to the store, and Phase 1 is
already moving `SCHEMA_VERSION` from 12 to 13. Phase 2 therefore lands as
schema 13 to 14 AFTER Phase 1 is merged and green. Building both migrations at
once against one file is exactly the two-writers collision the fence exists to
prevent.

## 1. What Full-Auto actually is

A signed, per-project contract that converts "do what you think is right" into
something a machine can check afterwards. Without the contract, autonomy is a
mood. With it, every action the run took can be compared against what was
authorised, and the comparison is a query rather than an argument.

## 2. The contract: table `autonomy_contracts` (schema 13 to 14)

| Column | Type | Notes |
|---|---|---|
| id | TEXT PRIMARY KEY | uuid4 hex |
| project_id | TEXT NOT NULL | |
| outcome | TEXT NOT NULL | what will exist when this is done |
| done_definition | TEXT NOT NULL | the checks that prove it, in plain words |
| scope_paths | TEXT NOT NULL | newline separated absolute paths the run may write |
| scope_apps | TEXT | newline separated apps it may drive; empty means none |
| token_ceiling | INTEGER | NULL means no token ceiling was set |
| minutes_ceiling | INTEGER | NULL means no time ceiling was set |
| risk_envelope | TEXT NOT NULL | newline separated pre-approved action classes |
| signed_at | TEXT NOT NULL | |
| signed_by | TEXT NOT NULL | the human who signed; never a model name |
| revoked_at | TEXT | NULL while live |
| state | TEXT NOT NULL | one of: live, paused, stopped, revoked |

A contract is never edited. A change is a new row plus a revoke of the old one,
so "what was I authorised to do at 03:00" stays answerable.

`signed_by` refuses a model name. The whole value of the row is that a human
put it there, and a contract a model signed for itself is a note, not a
mandate.

## 3. The five floors, which the contract cannot grant

These are refused at the gate no matter what the contract says, because they
are enforced above BrotherMode by the runtime and by the founder's own standing
directives:

1. Typing credentials, passwords, or 2FA codes.
2. Executing any payment or transfer of funds.
3. Creating accounts or completing a sign-in.
4. Permanent deletion, and any write to production state.
5. Publishing or releasing, unless the contract pre-signs one named artifact.

`gate-check` returns REFUSED-FLOOR for these and names which floor, always,
including when the contract's `risk_envelope` appears to list them. A contract
that tries to grant a floor is itself a finding worth reporting to the founder,
not a permission to honour.

Hitting a floor NEVER stalls the run. The item is queued with everything
prepared up to the human step, and the run continues with all work that does
not depend on it. Tonight's Codex credit wall is the worked example: the
blocker was recorded, the click path was named, and Phase 1 continued.

## 4. The question policy

An interruption is legitimate only for a forcing condition:

1. A design-changing ambiguity, where two readings lead to materially different
   work.
2. A contradiction between what the founder said and what the machine shows.
3. A hard-gate collision (one of the five floors, or a gate that cannot be
   satisfied).
4. A disproven plan assumption.

Everything else becomes a stated assumption: logged as a row, reversible, and
visible in the pulse. Non-urgent questions batch at phase boundaries.

Target: zero to three interruptions per project. The count is recorded per run
so the target is measured rather than asserted.

## 5. Circuit breakers

| Threshold | Behaviour |
|---|---|
| 80 percent of either ceiling | Stop STARTING new work; finish what is in flight; emit one pulse naming the spend and what remains |
| 100 percent of either ceiling | Stop; checkpoint every worktree; write the close record; emit the pulse |

The breaker reads the ceiling from the contract row. A contract with a NULL
ceiling has no breaker on that dimension, and `status` prints NO-DATA for it
rather than a comforting percentage of nothing.

## 6. The kill switch

`bm_autonomy.py stop --project ID` sets `state` to `stopped`. Every long-running
loop checks the state before starting a new unit of work, and the check is a
store read rather than a flag in anybody's memory. Stopping is idempotent, and
stopping an already-stopped contract is exit 0, because a founder hitting stop
twice at 3am must never get an error.

## 7. Commands: `tools/bm_autonomy.py`

| Command | Does |
|---|---|
| `sign --project ID --outcome T --done-definition T --scope-path P... [--scope-app A...] [--token-ceiling N] [--minutes-ceiling N] [--risk-class C...] --signed-by NAME` | writes the contract |
| `show --project ID` | the live contract, or "no live contract" |
| `gate-check --project ID --action-class C [--path P]` | ALLOWED, REFUSED-FLOOR with the floor named, or REFUSED-SCOPE with the path |
| `spend --project ID --tokens N --minutes N` | records spend, prints the breaker verdict |
| `status --project ID` | state, spend against ceilings, interruption count, NO-DATA where a ceiling is unset |
| `pause` / `resume` / `stop` / `revoke --project ID` | state transitions |
| `assume --project ID --text T` | records a stated assumption instead of asking |
| `interrupt --project ID --condition C --question T` | records a forcing-condition interruption; refuses a condition outside the four |

`interrupt` refusing an unrecognised condition is the mechanism that keeps the
question policy honest. Without it, "forcing condition" degrades into whatever
felt urgent.

## 8. What Phase 2 does NOT do

It does not drive anything. It is the contract, the gate, the breaker, the
switch, and the record. The loop that consults it is Phase 3 work, and keeping
them apart is what makes the gate testable without running an autonomous
session to test it.

## 9. Done-checks

```bash
cd <worktree> && python3 tools/test_bm_autonomy.py
```
```bash
cd <worktree> && python3 tools/test_bm.py
```
```bash
cd <worktree> && python3 tools/test_all.py
```

Same registration rule as Phase 1: a new suite goes into BOTH `tools/test_all.py`
SUITES and `.github/workflows/tests.yml`, or the gate fails.
