# FIX report, CROSS-FAMILY refuter, store side

Writer: the store-side fixer for findings 1, 4, 5 and 6 of
`/Users/khalil.maaouni/Documents/BrotherModeUp-handovers/2026-08-05-codex-crossfamily-findings.md`.
Findings 2 and 3 were closed by the controller-side writer in the previous
round (`FIX-crossfamily-report.md`) and nothing about them was touched.

Files written this round: `tools/bm_store.py`, `tools/test_bm_store.py`,
`tools/bm_controller.py`, `tools/test_bm_controller.py`,
`docs/KNOWN-LIMITS.md`, this report, and
`docs/program/absolute-lead/evidence/L03/RED-crossfamily-store.txt`.
Nothing else. `SECURITY.md` was NOT edited (its guard does not trip; see
section 6).

Finding 5 has an anchor on each side, so both halves landed together in
this one round, which is why `tools/bm_controller.py` is on that list: one
line of it, plus the deferral it needs.

---

## 1. PER-FINDING TABLE

| # | Severity | What it was | Verdict | Where it is now |
|---|---|---|---|---|
| 1 | HIGH | A string `retry_ceiling` stored as TEXT in a non-STRICT INTEGER column, then `1 <= "one"` out of the shipped CLI | **CLOSED at the class** | `bm_store.py` `declared_unit_number`, `UNIT_NUMBER_FIELDS`, wired into `upsert_units` |
| 4 | HIGH | `ReadOnlyStore` opened read-WRITE and set `query_only` afterwards, so it recreated WAL sidecars and failed where it could not | **CLOSED** | `bm_store.py` `_read_only_uri`, `_connect_read_only`, `_read_only_refusal` |
| 5 | MEDIUM | A claim built on a stale selection resurrected a unit a concurrent re-plan removed | **CLOSED, both halves** | `bm_store.py` `claim_unit`; `bm_controller.py` `_authorise_dispatch` |
| 6 | MEDIUM | Two concurrent verifications could overwrite a terminal verdict and roll back accepted work | **CLOSED** | `bm_store.py` `record_verification` |

Method was fail-first throughout. Every failure below is verbatim in
`docs/program/absolute-lead/evidence/L03/RED-crossfamily-store.txt`,
captured BEFORE any change to either production file: **44 labelled
failures and errors** across the seven new test classes.

### Finding 1, what changed

The refusal is at the BOUNDARY, not at the comparison, and it covers the
whole class rather than the one field the refuter named. `UNIT_NUMBER_FIELDS`
lists every numeric column of `controller_units` with the one question that
differs between them (whether an explicit null is a legal declaration), and
`declared_unit_number` refuses `bad-numeric-field` naming the field, the
type that arrived and what is required. It runs inside `upsert_units`'
existing pre-write validation loop, so nothing is written when it fires.

Two reasons it is at the boundary. First, guarding the comparison would
have left the bad value in the column for every OTHER reader, and there is
a second reader with a WORSE failure mode than the crash (see the sweep
below). Second, the store already answers declarations this way:
`declared_scope_list` for containers, `_autonomy_enum` for enums,
`sign_contract` for its ceilings, `record_dispatch` for `attempt`. The new
function is the same shape as the last two, `bool` exclusion included.

**Nothing is coerced.** `int('1')` would change a unit's `definition_hash`
for a graph the founder believes is unchanged, and a value silently
corrected is a value nobody can audit. Only a key that is PRESENT is asked
about, so an absent key still takes its documented default and a
well-typed unit hashes exactly as before
(`test_a_well_typed_graph_still_plans_exactly_as_before`).

Reachability is pinned at the shipped command, not only at the store
method: `bm-controller plan --units-json` with `"retry_ceiling": "one"`
now exits 1 naming the field, with no traceback
(`TestCrossFamilyF1ShippedPlanRefusesABadNumber`, real subprocess).

### Finding 4, what changed

`_connect_read_only` opened `sqlite3.connect(path, ...)`, which is
read-WRITE, and only then ran `PRAGMA query_only=ON`. `query_only` stops
SQL statements from writing; it does not stop the OPEN from writing, and
for a WAL database the open IS a write. Measured (probe in
`RED-crossfamily-store.txt` and reproduced as tests):

```
plain connect, WAL store, sidecars removed, writable dir
  before=[]  during=['store.sqlite3-shm', 'store.sqlite3-wal']  after=same
plain connect, same store, directory chmod 0o500
  ReadOnlyStore -> StoreCorrupt: "... could not be read as a SQLite
  database (attempt to write a readonly database)"
```

The second line is worse than the finding stated. `attempt to write a
readonly database` is not a transient-busy error, so
`ReadOnlyStore.__init__` classified it as structural damage and the shipped
`bm-controller status` reported a **perfectly healthy store as corrupt**.

The fix opens the file itself read-only through a `file:` URI, keeps
`PRAGMA query_only=ON` as a second defence that does not share a failure
mode with the first (one is enforced by the OS on the handle, the other by
sqlite on the statement), and turns the two "this directory will not let a
read-only connection do its bookkeeping" errors into a named
`store-unreadable` refusal instead of a false corruption verdict.

It is a two-rung ladder because neither sqlite read-only mode covers both
cases; section 3 has the measurements that forced that shape.

### Finding 5, what changed, and where the refuter's own remedy was wrong

Store half: `claim_unit`'s UPDATE now carries a status predicate and its
`rowcount` is checked, and it REFUSES `unit-not-claimable` rather than
no-opping, because a silent no-op leaves the caller believing it holds a
unit it does not, which is how the dispatch got written.

**The refuter proposed a literal `status='READY'` predicate. That would
have broken the product, and it was measured before shipping.**
`select_ready_units` returns units that are PENDING or READY, and its own
docstring says "the engine flips it to READY on claim via claim_unit". A
two-unit graph:

```
statuses at plan:        {'u1': 'READY', 'u2': 'PENDING'}
statuses after u1 DONE:  {'u1': 'DONE',  'u2': 'PENDING'}
select_ready_units ->    [('u2', 'PENDING')]
after claim u2:          {'u1': 'DONE',  'u2': 'CLAIMED'}
```

So `status='READY'` would refuse every dependent unit in every multi-unit
plan. The predicate shipped is the SET `select_ready_units` selects,
`('READY','PENDING')`, which still refuses SKIPPED, CLAIMED, DISPATCHED,
RESULT_IN, DONE and FAILED, and therefore still closes the finding.
`test_a_pending_unit_whose_dependencies_are_done_still_claims` is that
control, and it is what stops the predicate being narrowed later.

Controller half: `_authorise_dispatch` catches exactly
`reason == "unit-not-claimable"` (anything else re-raises), releases the
fence it claimed one call earlier, and returns `"DEFER"`, which is the
existing fence-overlap deferral: the wave reports `CONTENTION`, no retry is
burned, nothing drains. The fence release is not optional: the FILES are
claimed before the UNIT is, so a refused unit claim would otherwise leave an
active fence over the paths of a unit nobody is dispatching.

Both halves are asserted end to end against the refuter's own sequence
(`_ReplanningStore` fires a real concurrent `upsert_units` the moment
`select_ready_units` returns, then hands the engine the selection it had
already taken). Before the fix, the removed unit was not merely dispatched:
`'DONE' != 'SKIPPED'`. The engine ran it to completion.

### Finding 6, what changed

`record_verification` now refuses `already-verified` for a dispatch that
already carries a verdict, with the UPDATE conditional on the status the
transaction read and its `rowcount` checked. A repeated verdict of the SAME
shape is refused too, because "first write wins quietly" is
indistinguishable from "the second caller's check never ran". A CANCELLED
dispatch gets its own sentence and its own reason (`dispatch-cancelled`),
copied from `record_result`: telling that caller "a verdict was already
recorded" would be a false statement about a dispatch nothing ever judged.

**The predicate is "no verdict yet", not literally RESULT_IN**, and that
is deliberate rather than lax. Two shipped routes verify a dispatch that
never reached RESULT_IN (the re-await route when the live contract stops
authorising a unit in flight, and the unsafe-write-scope refusal), so a
literal RESULT_IN predicate would break both.
`test_a_dispatched_dispatch_may_still_be_verified` is that control.

The consequence the finding is actually about is walked whole in
`test_the_losers_rejection_cannot_roll_back_the_winners_work`: winner
accepts, unit goes DONE with its checkpoint, loser's rejection arrives and
is refused, unit is still DONE with `retry_count` 0 and its checkpoint
intact.

---

## 2. THE AFFINITY SWEEP

Asked mechanically, not by eye. Every numeric-affinity column was extracted
from the schema DDL by regex (**42 columns across 21 tables**), then an AST
pass over `tools/bm_store.py` and `tools/bm_controller.py` found every
`ast.Compare` and every non-`Mod` `ast.BinOp` with a `row["col"]` or
`row.get("col")` operand naming one of them, split by operator class,
because the operator decides the failure mode. Ordering comparisons raise
`TypeError`; equality comparisons return the WRONG ANSWER silently.

```
== tools/bm_store.py ==
  ORDER  (<,<=,>,>=  raises TypeError)
    14238  retry_ceiling  | new_status = "READY" if new_count <= row["retry_ceiling"] else "FAILED"
  EQUAL  (==,!=      wrong answer)
    7835   current_version | if int(expected_version) != int(rule["current_version"]):
    7905   current_version | if int(expected_version) != int(rule["current_version"]):
    10789  version         | if row is None or row["version"] != expected_version or ...
    10993  version         | if row is None or row["version"] != expected_version or ...
    11054  version         | if row is None or row["version"] != expected_version:
  ARITH  (+,-,*,/    raises TypeError)
    12590  revision        | revision = 1 if latest is None else latest["revision"] + 1
    12653  revision        | revision = latest["revision"] + 1
    14237  retry_count     | new_count = row["retry_count"] + 1

== tools/bm_controller.py ==
  ORDER
    1284   revision        | if row["revision"] <= stamped_revision:
  EQUAL
    1282   revision        | if row["revision"] == latest_revision:
    2711   revision        | elif verdict["revision"] != first_revision:
    3181   done_check_expect_exit | exit_ok = outcome["exit_code"] == unit["done_check_expect_exit"]
  ARITH
    1014   tokens          | tokens = totals["tokens"] - int(charged.get("tokens") or 0)
    1015   minutes         | minutes = totals["minutes"] - int(charged.get("minutes") or 0)
```

**Exactly TWO of these assumed affinity had coerced a CALLER's value, and
both are on `controller_units`. Both are closed by this round.**

1. `bm_store.py:14238`, `retry_ceiling`. The finding itself.
2. `bm_controller.py:3181`, `done_check_expect_exit`. **Not in the finding,
   and quieter than it.** A TEXT `"0"` never equals the integer exit code
   `0`, so a done-check that PASSED read as failed, forever: the unit burned
   both its attempts and escalated while nothing was actually wrong with it.
   No traceback, no refusal, no way to tell from the outside. The same
   boundary validation closes it, which is the argument for fixing the class
   rather than the one comparison.

Everything else in that list compares or arithmetics a value the store
itself computed, or a caller value already type-checked at its own entry
point:

- `autonomy_contracts.revision` is `1` or `previous + 1`, never a caller's.
  Both `bm_controller.py` sites at 1282/1284 read it from that chain.
- `autonomy_spend.tokens` / `minutes` are validated in `record_spend`
  (non-negative int, bool excluded), and `token_ceiling` / `minutes_ceiling`
  in `sign_contract`, so `_spend_verdict`'s division is safe.
- `controller_dispatches.attempt` is validated in `record_dispatch`;
  `controller_runs.workflow_version` in `open_run`.
- `controller_units.retry_count` is only ever written as the literal `0` or
  as an int computed here.
- `learning_rules.current_version` is already wrapped in `int()` on both
  sides at both sites.

**Listed, not fixed, with the reason:**

- `records.version` and `learning_rules.current_version` compare a CALLER's
  `expected_version` untyped (`bm_store.py:10789`, `:10993`, `:11054`). A
  wrong-typed one fails the optimistic-concurrency check and refuses
  `StaleIdentity`, so the failure direction is safe: a refusal, never a
  wrong accept. Changing it would swap one refusal for another and is
  outside these four findings.
- `controller_dispatches.contract_revision` and `done_check_exit` have no
  boundary type check, unlike `attempt` in the same method. Neither is ever
  compared or arithmetic'd (every use is `%` formatting into a message), and
  both are engine-supplied from store-computed values, so neither can
  reproduce the defect today. Proposed remedy if it is ever wanted: the same
  two-line guard `attempt` already has, in `record_dispatch` and
  `record_verification`.

### SQLite STRICT tables: considered, not used

STRICT would move this enforcement from Python into the engine, which is
strictly better as a rule. It was not used for three reasons, in order of
weight:

1. **It is not an additive migration.** SQLite cannot make an existing table
   STRICT in place; `ALTER TABLE` has no such form. Every existing store
   would need the three controller tables rebuilt (create, copy, drop,
   rename) under a `SCHEMA_VERSION` bump, on a file this project treats as
   the founder's durable record. That is a migration round of its own, not a
   line in a refutation fix.
2. **The refusal would get worse for the founder.** A STRICT violation
   raises `sqlite3.IntegrityError` with a message about a column, from
   inside a transaction. `declared_unit_number` names the unit, the field,
   the type that arrived, what is required, and states that nothing was
   written, before any row is touched. The refuter's own complaint was that
   the shipped CLI emitted a traceback; a bare IntegrityError is a smaller
   version of the same complaint.
3. **STRICT would not have caught the second site anyway.** STRICT rejects
   `"one"` for an INTEGER column, but `done_check_expect_exit` also accepts
   `"0"` under STRICT (INTEGER affinity converts a numeric-looking string
   losslessly), and `"0" == 0` is still False in Python. The wrong-answer
   half of the sweep needs the boundary check regardless.

STRICT remains the right answer for the next migration that rebuilds these
tables for another reason, and it is recorded that way in
`docs/KNOWN-LIMITS.md`.

---

## 3. WHAT WAS VERIFIED ABOUT READ-ONLY URIs, AND WHAT IT COST

All measured on this machine before anything was relied on: **Python 3.9.6,
sqlite 3.51.0, darwin 25.5.0**. `uri=True` has been in `sqlite3.connect`
since Python 3.4, so 3.9 is not in question; what needed measuring was
behaviour, not availability.

### The spelling

`pathlib.Path(path).as_uri() + "?mode=ro"`, for example
`file:///Users/.../.brothermode/store.sqlite3?mode=ro`. `as_uri()`
percent-encodes every byte outside the unreserved set, which is a TOTAL
rule rather than a list of characters to escape. That distinction is the
whole answer to GATE A.

**GATE A said "no sqlite URI, ever", and this round brings one back, so the
reasoning is stated rather than assumed.** GATE A's defect was a PARTIAL
escape: the URI in use escaped only `?` and `#` while sqlite percent-DECODES
the rest of the filename, so a project at `p%41` resolved to `pA` and every
read-only command reported another project's database as this one's. The
conclusion drawn then, that "escaping '%' too would still leave a
pattern-language bug waiting for the next special character", is right about
escaping characters one at a time and does not apply to encoding every byte.
Verified across every character class the old spelling could have got wrong,
each opening its OWN database:

```
pA -> pA      p%41 -> p%41   p[1] -> p[1]   p#q -> p#q    p?x -> p?x
p a -> p a    p'q -> p'q     pe -> pe       p+q -> p+q    p&q -> p&q
p=q -> p=q    p%2Fq -> p%2Fq
```

That is a test, not a paragraph
(`test_a_path_full_of_uri_metacharacters_still_opens_its_own_database`), and
GATE A's own existing test
(`test_calibrated_gateA_percent_sign_path_never_leaks_across_projects`)
still passes untouched, which is the independent check.

### Why it is a ladder and not one spelling

Neither read-only mode covers both cases. Measured, WAL store, sidecars
removed:

| open | writable dir | non-writable dir | creates |
|---|---|---|---|
| plain connect + `query_only` | reads | **raises** `attempt to write a readonly database` | `-wal` and `-shm` |
| `?mode=ro` | **raises** `unable to open database file` | **raises** | (cannot create the `-wal`) |
| `?mode=ro` with a `-wal` present | reads | raises without an `-shm` | `-shm` |
| `?mode=ro&immutable=1` | reads | **reads** | **nothing** |

So `mode=ro` alone would have BROKEN the shipped read-only commands against
a cleanly-closed store, which is the common case, and `immutable=1` alone
would have IGNORED the write-ahead log. The ladder is: `-wal` present means
`mode=ro`, always, so a live store is read THROUGH its log with real locks;
no `-wal` means nothing is pending, so `immutable=1` is both accurate and
the only open that touches nothing.

`test_a_pending_wal_is_read_through_and_not_ignored` is the honesty control
on that, and it matters: measured, an `immutable=1` reader opened before a
writer committed reported `None` for a row the writer had just committed. A
diagnostic that silently reported the pre-WAL state of a live store would be
the same class of lie fix-round 4 exists to prevent, so `immutable` is
confined to the case where there is provably nothing to miss.

### The race this leaves, stated rather than buried

A writer can create a `-wal` between the stat and the open. The `-wal` is
re-checked immediately after the open and the connection is thrown away and
retaken WAL-aware if one appeared, so the surviving window is a writer that
opens, commits, checkpoints AND closes inside it, which would leave that one
read seeing a file changing underneath it. That is not closed and cannot be
from this side without taking the write lock a read-only diagnostic must not
take. It is in `docs/KNOWN-LIMITS.md` in those words.

One case is now a NAMED refusal rather than a read: a store whose `-wal`
exists in a directory that forbids the `-shm`. `store-unreadable` says what
happened and how to get at the data. Reading it with `immutable=1` was
rejected deliberately, for the reason above.

---

## 4. FINDINGS IN PASSING

- **`tools/test_bm_controller.py` loads `bm_store` a SECOND time, so the
  engine's `except bs.OwnershipRefused` branches cannot fire in its
  in-process tests.** This file does `bs = _load("bm_store")` and
  `tools/bm_controller.py` does its own `bs = _load("bm_store")`, and
  `importlib` produces two distinct module objects, so `bs.OwnershipRefused`
  in the test file is a DIFFERENT class from the one the engine catches
  (`bs is bc.bs -> False`, verified). `bm_controller.py`'s own comment names
  this "the class-identity trap tools/bm_project.py documents". My first
  version of the finding-5 test built the store with the test file's `bs`,
  and the store's refusal escaped `step()` as an uncaught exception rather
  than being deferred. In PRODUCTION there is one load, so the catch works;
  the test now builds its store with `bc.bs.Store` and says why in a
  comment. **The wider consequence I did not fix: any OTHER engine-level
  `except bs.OwnershipRefused` in `bm_controller.py` is, in those tests,
  exercised only if its test builds the store the same way. The existing
  fence-overlap deferral at the same call site is the obvious one to check.**
  This is not one of my four findings and I did not audit the rest of the
  file for it.
- **The shipped `bm-controller status` reported a HEALTHY store as
  `StoreCorrupt`**, not merely "can also fail outright" as finding 4 put it.
  Recorded here because the severity of the founder-facing symptom is
  higher than the finding's own wording.
- **The refuter's proposed remedy for finding 5 would have broken every
  multi-unit plan.** See section 1. Worth carrying forward as a note about
  cross-family findings generally: the diagnosis was right and the
  prescription was not.

---

## 5. DONE-CHECK, VERBATIM, RUN AFTER THE LAST EDIT

```
### python3 tools/test_bm_store.py
Ran 908 tests in 28.636s
FAILED (failures=1)
EXIT=1
### python3 tools/test_bm_controller.py
Ran 191 tests in 15.174s
OK
EXIT=0
### python3 tools/test_bm_autonomy.py
Ran 58 tests in 24.344s
OK
EXIT=0
### glob sweep
triples 5840400
violations 0
EXIT=0
```

Targeted run over the seven new classes, **33 tests, all passing**:

```
$ python3 -m unittest \
    test_bm_store.TestCrossFamilyF1UnitNumberTypes \
    test_bm_store.TestCrossFamilyF4ReadOnlyOpensReadOnly \
    test_bm_store.TestCrossFamilyF5ClaimCannotResurrectARemovedUnit \
    test_bm_store.TestCrossFamilyF6VerdictIsAtMostOnce \
    test_bm_controller.TestCrossFamilyF5StaleSelectionIsDeferred \
    test_bm_controller.TestCrossFamilyF1ShippedPlanRefusesABadNumber \
    test_bm_controller.TestCrossFamilyF4ShippedStatusNeverWritesTheStoreDirectory
----------------------------------------------------------------------
Ran 33 tests in 2.742s

OK
```

25 of those are in the store suite (908 total, up from 883) and 8 in the
controller suite (191 total, up from 183). The glob rule the founder pinned
is untouched: **5840400 triples, 0 violations**, the same figures
`FIX-glob-rule-report.md` recorded.

`tools/test_all.py` was NOT run, per the brief.

### THE ONE FAILURE, AND WHY IT IS NOT MINE

`tools/test_bm_store.py` exits 1 on a single test:

```
FAIL: test_no_shipping_message_hardcodes_the_repo_relative_path
AssertionError: Lists differ: [] != ['bm_runtimes.py:731']
```

`tools/bm_runtimes.py` is a file this round may not write and did not write.
It carries another writer's UNCOMMITTED change in this same working tree
(`git status` shows `tools/bm_runtimes.py`, `tools/test_bm_runtimes.py`,
seven `docs/runtimes/*` files and
`docs/program/absolute-lead/evidence/RED-codex-runtime.txt` all modified or
untracked), and their new line 731 is a deliberate example string,
`"    WRONG in your own project:   python3 tools/bm_store.py dashboard"`,
which that sweep reads as a shipping instruction.

Proved by A/B, one variable, in a COPY of the live tools directory so
nothing in the real tree was touched:

```
--- A: unchanged copy of the live tree ---
+ ['bm_runtimes.py:731'] : these runtime strings tell the reader to run a
  repo-relative path that does not exist in a packaged install ...
Ran 8 tests in 0.346s
FAILED (failures=1)

--- B: same copy, ONLY tools/bm_runtimes.py reverted to HEAD ---
........
Ran 8 tests in 0.334s
OK
```

My own changes are intact in BOTH runs. **This is blocked, not closed:** it
belongs to whoever owns `tools/bm_runtimes.py`, and the remedy is theirs to
choose (add the example to that test's `NOT_OWNED_BY_THIS_LOOP` set with a
reason, or render the example through `bs.invocation` like every other
shipping string). I did not touch their file, their test, or that test's
exemption set.

### No existing test was edited, weakened or deleted

One existing test collided and was answered by changing MY code, not it.
`test_structural_gate4_bare_execute_sites_are_all_named_exceptions` holds
every bare `.execute()` site to a closed, named set, and my first draft of
the read-only fix split the open into a helper beside `_connect_read_only`,
which added two unlisted sites:

```
FAIL: test_structural_gate4_bare_execute_sites_are_all_named_exceptions
AssertionError: Lists differ:
  [(14598, '_open_read_only_uri'), (14599, '_open_read_only_uri')] != []
```

That test's own message offers "add the enclosing function to `exempt`
above with a stated reason" as a legal remedy, and I did not take it: the
whole ladder was folded back into `_connect_read_only`, which is ALREADY in
the exempt set, so the exempt set did not grow. One exempt site is a smaller
surface than two.

Two structural assertions in my own new tests also failed at first, because
the SQL they check is written across two source lines and I was matching raw
file text. `_method_source` now closes adjacent string-literal seams before
matching. Both are tests I wrote this round.

`CONTROLLER_STATE_TRANSITIONS` and `AUTONOMY_FLOORS` were not widened. No
schema change, no `SCHEMA_VERSION` bump, no DDL: every fix this round is
Python-side validation or a WHERE clause.

---

## 6. WHAT I DID NOT DO

- **`SECURITY.md` was NOT edited.** Re-measured after the last edit:

  ```
  $ find tools -name "*.py" -o -name "*.sh" | xargs wc -l | tail -1
     95130 total
  ```

  against the 91,100 the document claims at line 101, a drift of 4.4
  percent, well inside the 15 percent its guard enforces.
  `test_bm.TestProjectSecurityClaims` passes (2 tests, OK). Per the brief,
  the file is left alone. Note that this figure includes the other writer's
  uncommitted `tools/bm_runtimes.py` and `tools/test_bm_runtimes.py`
  growth as well as mine.
- **Findings 2 and 3 were not touched, read for editing, or re-verified.**
- **`tools/bm_autosave.py`'s inherited-git-environment exposure**, raised by
  the controller writer in passing, is still open. Not mine, not read.
- **Concurrency was exercised as SEQUENCES, not as threads or processes.**
  Every finding-5 and finding-6 test drives the interleaving deterministically
  in one process (the store's `BEGIN IMMEDIATE` is what makes that
  faithful: it serialises the two writers anyway, so a real second process
  reaches exactly the states these tests construct). No test starts a second
  OS process against the same store file except the CLI tests, which are
  single-writer.
- **The `immutable=1` race window is open** and stated in section 3 and in
  `docs/KNOWN-LIMITS.md`.
- **Platform.** Everything measured on darwin 25.5.0, Python 3.9.6, sqlite
  3.51.0. sqlite's read-only WAL behaviour is not documented as platform
  specific, but the sidecar creation, the `immutable=1` results and the
  non-writable-directory results were observed on this machine only. The
  non-writable-directory tests `chmod 0o500` and restore in a `finally`; run
  as root they would prove nothing, because root ignores the mode bits.
- **The rest of `tools/bm_store.py`'s 42 numeric columns** were swept for the
  defect SHAPE (section 2) but their write paths were not individually
  audited beyond the ones the sweep implicated.
- **The class-identity trap in section 4 was not audited across the whole
  controller test file.** I fixed the one test I wrote.
