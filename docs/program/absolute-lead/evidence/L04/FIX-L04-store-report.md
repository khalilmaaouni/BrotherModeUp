Status: CURRENT. Writer A (the store), L04. 2026-08-05.

# FIX L04: the store. Schema 16, the insight ledger, the briefing timeline

Scope: DESIGN-L04.md sections 5, 6, 14's replay test, 15.1, 17.3, 18.1.
Files written: `tools/bm_store.py`, `tools/test_bm_store.py`,
`tools/test_bm_project.py`, and this folder. Nothing else was touched.

---

## SIGNATURES (GATE 1, Writer B reads this and does not guess)

Everything below is copied from the LANDED code, not from the design's
prose. Where the two differ, the difference is called out in the same
line. Module is `tools/bm_store.py`, imported by Writer B as `bs`.

### The two write paths

```python
def record_insight(self, project_id, insight, actor):     # bm_store.py:14852
    # returns exactly: {"insight_id": str, "kind": str, "decision_class": str}

def record_briefing(self, project_id, briefing, actor):   # bm_store.py:15016
    # returns exactly: {"briefing_id": str, "trigger": str,
    #                   "active_minutes": int}
```

`insight` and `briefing` are dicts. `actor` is the usual actor dict
(`actor_type`, `actor_name`, `session_id`); the row's `session_id`,
`actor_type` and `actor_name` columns are filled FROM it, so do not pass
them as payload keys (doing so is refusal R16).

Accepted payload keys, and nothing else:

```python
bs.INSIGHT_FIELDS = ("kind", "subject", "claim", "evidence",
                     "evidence_class", "alternatives", "flip_condition",
                     "confidence", "confidence_basis", "mutation",
                     "observed", "decision_class", "control_offered",
                     "control_taken", "supersedes", "work_record",
                     "run_id", "unit_id")

bs.BRIEFING_FIELDS = ("trigger", "active_minutes", "event_count",
                      "skipped_events", "since_briefing", "run_state",
                      "open_steps", "where_we_are", "what_changed",
                      "what_it_cost", "decision_insight", "risk_insight")
```

Required in practice: an insight always needs `kind`, `claim`,
`evidence_class` and `confidence` (the four have no default). A briefing
always needs `trigger` and `where_we_are`. Everything else defaults to
`""` for text, `0` for counters, `[]` for `alternatives`.

`alternatives` is a Python list of `{"option": str, "why_not": str}`,
EXACTLY those two keys. It goes in as a list and comes back as a list.

### The six read accessors

All six exist on `Store` AND on `ReadOnlyStore` (identical signatures,
plain pass-throughs at bm_store.py:15720 to 15741). Neither write path
exists on `ReadOnlyStore`, by design.

```python
def list_insights(self, project_id, kind=None, since=None, until=None,
                  limit=None, raw=False)                  # bm_store.py:15117
def get_insight(self, insight_id, raw=False)              # bm_store.py:15138
def list_briefings(self, project_id, since=None, until=None, limit=None,
                   raw=False)                             # bm_store.py:15147
def latest_briefing(self, project_id, raw=False)          # bm_store.py:15158
def open_key_decisions(self, project_id, raw=False)       # bm_store.py:15166
def active_minutes_since(self, project_id, since_iso, now=None)
                                                          # bm_store.py:15186
```

Return shapes and the four things the design's prose did not pin:

1. **Ordering is NEWEST FIRST on all three list accessors**
   (`created_at DESC, rowid DESC`; the rowid tie break makes two rows
   written in the same second deterministically ordered). `limit`
   therefore means "the newest N". `50-TIMELINE.md` renders briefings
   oldest first, so **Writer B reverses the list**; the store does not
   offer a direction flag, because two readers must not be able to
   disagree about which row is the latest.
2. **`since` is EXCLUSIVE, `until` is INCLUSIVE**, on every accessor that
   takes them (`created_at > since`, `created_at <= until`). That pairing
   is what lets you anchor on a row you already hold: "everything after
   the briefing I am looking at" does not hand that briefing back, and
   "everything up to this page's cut" includes the row written AT the
   cut. This is the mechanic behind the byte-stable page.
3. `get_insight` and `latest_briefing` return a **dict or None**. The
   list accessors return a **list, possibly empty**. An unknown
   project_id is an empty list, never a raise (the shipped D-2 policy for
   advisory reads).
4. `list_insights(..., kind=...)` raises `ValueError` naming the whole
   allowed set if `kind` is not in `INSIGHT_KINDS`. `limit` must be a
   non-negative int, else `ValueError`.

`open_key_decisions` returns the DECISION rows carrying a non-empty
`decision_class` that NOTHING supersedes, newest first. It applies no
stakes ordering: `DECISION_STAKES` lives in `bm_lead.py` and the sort is
Writer B's.

`active_minutes_since` returns exactly:

```python
{"active_minutes": int, "events": int, "skipped": int}
```

`since_iso` and `now` must both parse in `now_iso()`'s own format
(`"%Y-%m-%dT%H:%M:%SZ"`); either failing to parse is a `ValueError`.
`now` defaults to `now_iso()`. `now` is NOT appended to the series, so an
open-ended idle tail accrues nothing. `skipped` counts attribution rows
for that project whose timestamp does not parse; **surface a non-zero
`skipped` rather than printing a total that quietly dropped rows.**

### `raw`

Identical to the shipped split. Text output for the local terminal passes
`raw=True`; `--json` is an export and stays redacted unless `--raw` is
also given. Under `raw=False` the prose columns come back as
`"[WITHHELD: N chars of founder text]"`, and `alternatives` comes back as
that marker string rather than a list, because a marker does not parse as
JSON. Do not try to index into it.

### New module constants Writer B will want

```python
bs.INSIGHT_KINDS = ("DECISION", "CALIBRATION", "RISK", "LEARNING",
                    "HANDBACK")
bs.EVIDENCE_CLASSES = ("EXECUTED", "MEASURED", "READ", "REASONED")
bs.INSIGHT_DECISION_CLASSES = ("GATE", "RULE", "TEST", "DEFERRAL",
                               "PREFERENCE")   # already in stakes order
bs.INSIGHT_CONFIDENCE = ("low", "moderate", "high")
bs.BRIEFING_TRIGGERS = ("ACTIVE_MINUTES", "PHASE_BOUNDARY", "REQUESTED")
bs.INSIGHT_FIELDS, bs.BRIEFING_FIELDS      # above
bs.ACTIVE_GAP_CEILING_SECONDS = 300
bs.BRIEFING_ACTIVE_MINUTES = 30
bs._TABLES_LEAD = ("insights", "briefings")
bs.SCHEMA_VERSION = 16
bs.parse_iso_stamp(value)  # -> aware datetime or None, public helper
```

### Every refusal, by reason code

`OwnershipRefused` carries `.reason`. `ValueError` carries only a message;
where a test needs to distinguish, match on the quoted fragment.

`record_insight`:

| # | Condition | Raises | reason / message fragment |
|---|---|---|---|
| R16 | a key not in `INSIGHT_FIELDS` (including `insight_id`, `created_at`, `session_id`, `actor_type`, `actor_name`) | ValueError | `unknown insight field(s) <name>` |
| R1 | `kind` not in `INSIGHT_KINDS` | ValueError | `unknown kind ... (allowed: ...)` |
| R3 | `claim` empty, blank or not a string | ValueError | `an insight with no claim is narration, not an insight` |
| R2 | `evidence_class` not in `EVIDENCE_CLASSES` | ValueError | `unknown evidence_class ...` |
| R11 | `confidence` not in `INSIGHT_CONFIDENCE` | ValueError | `unknown confidence ...` |
| R8 | `decision_class` non-empty and not in `INSIGHT_DECISION_CLASSES` | ValueError | `unknown decision_class ...` |
| R10 | `alternatives` not a list of exactly `{"option": str, "why_not": str}` | ValueError | `bad-alternatives: ...` |
| (shape) | any text field given a non-string, any flag not 0 or 1 | ValueError | `<field> must be a string` / `must be 0 or 1` |
| R15 | `project_id` names no project | OwnershipRefused | `not-found` |
| R4 | `evidence_class` EXECUTED or MEASURED and `evidence` empty | OwnershipRefused | `evidence-missing` |
| R5 | `kind` CALIBRATION and `mutation` or `observed` empty | OwnershipRefused | `calibration-incomplete` |
| R6 | `kind` DECISION and `flip_condition` empty | OwnershipRefused | `no-flip-condition` |
| R7 | `decision_class` non-empty and `control_offered` != 1 | OwnershipRefused | `handback-not-offered` |
| R9 | `decision_class` non-empty and `alternatives` empty | OwnershipRefused | `no-alternative` |
| R12 | `kind` HANDBACK and `supersedes` empty | OwnershipRefused | `handback-without-decision` |
| R13 | `supersedes` names no insight / one in another project | OwnershipRefused | `not-found` / `foreign-insight` |
| R14 | `kind` HANDBACK and a HANDBACK already supersedes that decision | OwnershipRefused | `handback-already-taken` |

The order above is the order they fire, which matters only when two
conditions hold at once.

`record_briefing`:

| Condition | Raises | reason / fragment |
|---|---|---|
| a key not in `BRIEFING_FIELDS` | ValueError | `unknown briefing field(s) <name>` |
| `trigger` not in `BRIEFING_TRIGGERS` | ValueError | `unknown trigger ...` |
| `where_we_are` empty, blank or not a string | ValueError | `a briefing must say where the work stands` |
| `active_minutes`, `event_count`, `skipped_events` or `open_steps` negative, non-int, or a bool | ValueError | `<field> must be a whole number` |
| `project_id` names no project | OwnershipRefused | `not-found` |
| `since_briefing` names no briefing | OwnershipRefused | `not-found` |
| `since_briefing` names another project's briefing | OwnershipRefused | `foreign-briefing` |

Two of these are NOT in the design's section 6.2 list and are stated as
additions rather than smuggled in: the unknown-project refusal on
`record_briefing`, and the `not-found` on an unknown `since_briefing`.
Both exist because the alternative is a bare `sqlite3.IntegrityError`
(the foreign key) or a dangling pointer, and this store's own convention
is a refusal that names a reason. Both mirror R15 and R13 exactly.

### Attribution event types the two writers append

`insight.recorded` and `briefing.recorded`, each with `evidence_ref` set
to the new row's id, written inside the SAME transaction as the row.
Both therefore count as ACTIVE WORK in `active_minutes_since`.

---

## BLOCKED, and it is the first thing the orchestrator should read

Two EXISTING tests collide with this change and were **not** predicted by
DESIGN-L04 section 18. My brief says: stop on that item, record the
verbatim failure and a proposed minimal remedy, and never edit it. I have
not edited either. `python3 tools/test_bm_store.py` therefore exits 1
with exactly these two failures and nothing else.

Both live in `tools/test_bm_store.py`, which is my file, so either remedy
is a one-line patch I can apply the moment the orchestrator says so.

### BLOCKED-1. `TestFixRoundGates.test_structural_gate4_bare_execute_sites_are_all_named_exceptions`

```
FAIL: test_structural_gate4_bare_execute_sites_are_all_named_exceptions (__main__.TestFixRoundGates)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_bm_store.py", line 1003, in test_structural_gate4_bare_execute_sites_are_all_named_exceptions
    self.assertEqual(offenders, [],
AssertionError: Lists differ: [(4194, '_migrate_15_to_16'), (4196, '_migrate_15_to_16')] != []

First list contains 2 additional elements.
First extra element 0:
(4194, '_migrate_15_to_16')

- [(4194, '_migrate_15_to_16'), (4196, '_migrate_15_to_16')]
+ [] : raw execute()/executescript() call site(s) outside the exempt set (line, enclosing function): [(4194, '_migrate_15_to_16'), (4196, '_migrate_15_to_16')]; route through _exec, or add the enclosing function to `exempt` above with a stated reason
```

Why it is unavoidable rather than a code defect: `_MIGRATIONS[15]` is
called by `Store._migrate_from` as `step(conn)`, so a migration step holds
a raw connection and not a `Store`. `_exec(store, sql)` needs
`store._quarantine_and_raise`, which a bare connection does not have.
Every migration step from `_migrate_1_to_2` onward is in that same
position and every one of them carries a named exemption in this dict,
including `_migrate_14_to_15` five lines above where the new entry goes.
The test's OWN failure message prescribes the remedy.

PROPOSED MINIMAL REMEDY (add one entry to `exempt` at
tools/test_bm_store.py:971, immediately after the `_migrate_14_to_15`
entry, changing no assertion):

```python
            "_migrate_15_to_16": "a schema migration step, run INSIDE the "
                                 "caller's BEGIN EXCLUSIVE (L04, the "
                                 "insight ledger: insights, briefings). "
                                 "Same exemption and same reason as "
                                 "_migrate_14_to_15: a CREATE TABLE "
                                 "failing mid-migration must roll the "
                                 "caller's transaction back, not move the "
                                 "founder's store aside",
```

### BLOCKED-2. `TestPurgeProject.test_removes_rows_and_writes_attribution_naming_the_purge`

This is the STORE-SIDE TWIN of the pin section 18.1 names. Section 18.1
names `tools/test_bm_project.py:1353` only; the same `removed` dict is
pinned by exact equality a second time, at `tools/test_bm_store.py:14909`.
Its argument is 18.1's argument verbatim, and I did not assume that
authorised me to edit a test the design did not name.

```
FAIL: test_removes_rows_and_writes_attribution_naming_the_purge (__main__.TestPurgeProject)
AssertionError: {'dependencies': 1, ...} != {'dependencies': 1, ...}
  {'alerts': 1,
   'alerts_skipped': [],
   ...
-  'briefings': 0,
   'controller_dispatches': 0,
   'controller_runs': 0,
   'controller_units': 0,
   'cross_project_edges_removed': [],
   'dependencies': 1,
   'evidence': 2,
   'forecasts': 1,
-  'insights': 0,
   'projects': 1,
   'tasks': 2}
```

PROPOSED MINIMAL REMEDY (tools/test_bm_store.py:14924, the same two keys
section 18.1 already authorised for the project-side copy; the assertion
stays exact equality against the WHOLE dict, so nothing is loosened):

```python
                              "controller_runs": 0, "controller_units": 0,
                              "controller_dispatches": 0,
                              # L04: no ledger rows in this fixture
                              # either, so both new tables remove zero.
                              "insights": 0, "briefings": 0})
```

`TestLeadPurgeLeavesNoOrphans` (new, green) covers the NON-zero case that
neither pin covers, so coverage strictly increases once these land.

---

## Per-section table

| Section | Item | State | Where |
|---|---|---|---|
| 5.1 | `insights`, 24 columns, `supersedes` as plain TEXT with a store-level check | LANDED | bm_store.py `_LEAD_DDL` |
| 5.1 | `INSIGHT_KINDS`, `EVIDENCE_CLASSES`, `INSIGHT_DECISION_CLASSES`, `INSIGHT_CONFIDENCE`, no CHECK in the DDL | LANDED | beside the controller sets |
| 5.2 | `briefings`, 18 columns, `BRIEFING_TRIGGERS`, `run_state` and `open_steps` stored | LANDED | `_LEAD_DDL` |
| 5.3 | `SCHEMA_VERSION` 15 to 16 | LANDED | bm_store.py:81 |
| 5.3 | `_TABLES_LEAD`, `_TABLES_V16`, `_TABLES_BY_VERSION[16]` | LANDED | beside `_TABLES_V15` |
| 5.3 | `_LEAD_DDL`, `_LEAD_INDEX_DDL` and both `_split_ddl` statement lists | LANDED | beside `_CONTROLLER_DDL_STATEMENTS` |
| 5.3 | `_migrate_15_to_16`, `_MIGRATIONS[15]`, the `_ensure_schema` block, the `_ensure_indexes` block | LANDED | beside `_migrate_14_to_15` |
| 5.3 | four indexes including `insights_supersedes_idx` | LANDED | `_LEAD_INDEX_DDL` |
| 5.4 | 25 `_DUMP_SAFE_COLUMNS` entries, prose and both actor columns deliberately withheld | LANDED | end of `_DUMP_SAFE_COLUMNS` |
| 5.5 | two purge deletes, before `_write_attribution` and before the `projects` delete | LANDED | `purge_project` |
| 6.1 | `record_insight`, `record_briefing`, one transaction, attribution inside it | LANDED | bm_store.py:14852, 15016 |
| 6.2 | all sixteen insight refusals plus the briefing set | LANDED | see SIGNATURES |
| 6.3 | six read accessors, `ReadOnlyStore` pass-throughs, `raw` split | LANDED | bm_store.py:15117 to 15196, 15720 to 15741 |
| 7.1 | `active_minutes_since`, `ACTIVE_GAP_CEILING_SECONDS`, `BRIEFING_ACTIVE_MINUTES` | LANDED | bm_store.py:15186 |
| 14 | the replay test, and its verdict | LANDED, verdict NEGATIVE | see below |
| 15.1 | every row of the inventory table | LANDED | this table |
| 17.3 | nine named classes, written and run RED first | LANDED (11 classes, 52 tests) | RED-L04-store.txt |
| 18.1 | the project-side pinned `removed` dict | LANDED | test_bm_project.py:1387 |
| 18.1 twin | the store-side pinned `removed` dict | **BLOCKED** | BLOCKED-2 above |
| (unnamed) | the gate-4 exempt registry | **BLOCKED** | BLOCKED-1 above |

Two design details deliberately NOT followed to the letter, both stated:

* Section 15.1 says "`ReadOnlyStore` CHANGED, seven pass-throughs". Six
  landed, because section 6.3 names six accessors and neither write path
  may exist on a read-only class. If the seventh was meant to be a
  writer, that is a design slip and the answer is still six.
* Section 6.3 gives no ordering or `since`/`until` boundary rule. Both are
  decided here and pinned by tests; see SIGNATURES points 1 and 2.

---

## The migration proof

The design requires proof against an EXISTING store, not only a fresh
one. `TestSchema16IsAdditive` does it four ways:

1. `test_migration_from_a_real_schema15_fixture_survives_every_row`.
   The fixture is a REAL store: opened, a project written, a contract
   signed, then reverted to look like schema 15 by dropping
   `bs._TABLES_LEAD` and setting `meta.schema_version='15'`. Never
   hand-written DDL, so the fixture cannot drift from the schema anyone
   actually has. It then asserts that every `projects` and
   `autonomy_contracts` row is byte-identical before and after
   (`assertEqual(before, after)`), that both new tables exist and are
   empty, and that no quarantine directory appeared: a healthy schema-15
   store MIGRATES rather than being quarantined.
2. `test_the_fresh_and_migrated_paths_produce_identical_table_info`.
   `PRAGMA table_info` for both tables is compared between a store born
   at 16 and a store migrated to 16. Identical, which is the "one DDL
   text, two paths" rule every step from schema 4 onward states.
3. `test_the_schema15_table_list_is_unchanged`.
   `_TABLES_BY_VERSION[15] == _TABLES_V15`, neither new table appears in
   it, both appear in `[16]`, and `_TABLES_V16 == _TABLES_V15 +
   _TABLES_LEAD`. This is what keeps a schema-15 store verified against
   schema 15's OWN list before it is migrated.
4. `test_a_brand_new_store_has_both_lead_tables_empty` pins the exact
   column set of both tables and asserts zero rows: no backfill.

Additive is also true by construction: `_migrate_15_to_16` contains only
`CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS`, no ALTER,
no DROP, no UPDATE, and it walks `_split_ddl`'s statement list rather than
calling `executescript`, whose implicit COMMIT would end the caller's
`BEGIN EXCLUSIVE` underneath it.

## The purge pin, and the proof that skipping it goes red

The brief asks for verification that a new table which skips the pin turns
the suite red. It did, twice, observed rather than reasoned:

* The project-side pin went red the moment the keys were added ahead of
  the implementation (captured verbatim in RED-L04-store.txt).
* The store-side twin went red the moment `purge_project` started
  removing the two tables, WITHOUT anybody editing that test. That is the
  pin performing its designed function against a real schema change, and
  it is BLOCKED-2 above.

So the answer to "does a table that skips the pin turn the suite red" is
yes, demonstrated, and the mechanism fired in a second place the design
had not enumerated.

## The append-only proof

Three tests, and the first one is not vacuous:

* `test_structural_no_update_or_delete_names_the_ledger` parses the whole
  of bm_store.py with `ast` and fails if any string constant containing
  `insights` or `briefings` also contains `UPDATE ` or `DELETE FROM`
  outside `purge_project`. Shape copied from
  `test_structural_no_service_method_updates_an_autonomy_contract_row`.
* `test_the_guard_actually_catches_the_shape_it_bans` runs the SAME
  scanner over source that MUST be flagged and asserts it flags exactly
  the two offenders and exempts `purge_project` alone. Without this, the
  assertion above is an equality against an empty list that a broken
  scanner satisfies too.
* `test_a_correction_appends_and_leaves_the_corrected_row_untouched`
  reads the corrected row's raw bytes before and after a superseding row
  is written and asserts they are identical.
* `test_supersedes_is_written_at_insert_and_never_set_later` asserts the
  one INSERT names the column, and that the strings `UPDATE insights`,
  `UPDATE briefings` and `SET supersedes` appear nowhere in the module.

## Section 14 verdict: the controller event ledger

**VERDICT: replay from `attribution` alone does NOT work. The deferral of
`controller_events` stands, and this is its specification, in columns.**

`TestControllerEventsReplayFromAttribution` drives a real run to
DELIVERABLE_READY and then tries to reconstruct, from attribution rows
alone, what the entity rows did. Two named gaps:

1. **The run's state sequence does not reconstruct.** Every transition
   DOES leave an event (`controller.run.state_changed`, one per
   transition, asserted), so nothing is missing at the event level. What
   is missing is the state the run moved TO: the event carries
   `event_type`, `action`, `reason` and an `evidence_ref` naming the run,
   and no column of it names the target state. A replayer can COUNT the
   transitions and cannot NAME them. Specification: a `to_state` and a
   `from_state` on the run transition event.
2. **The unit's status sequence needs the entity rows to resolve.** Of
   the unit-scoped events this drive produced, only
   `controller.unit.claimed` names the unit in a column of its own.
   `controller.unit.dispatched`, `controller.dispatch.resulted` and
   `controller.dispatch.verified` name a DISPATCH id, and
   `controller.unit.done` names a CHECKPOINT ref, so resolving any of
   them back to a unit requires SELECTing `controller_dispatches`, an
   entity table. That is precisely the calibration section 17.3 asked
   for: the reconstruction cannot be shown to read events rather than
   entity rows, because it cannot. Specification: a `unit_id` column on
   every unit-scoped event.

Both tests are red-by-design if the gap closes: the day an event carries
the state or the unit, they fail and section 16.1's deferral has to be
re-decided rather than silently outlived.

Section 14 item 4 and build step 5 say this verdict is written into
`docs/KNOWN-LIMITS.md`'s L04 section either way. **That file belongs to
Writer C, so I have not touched it.** Writer C should record: replay from
attribution alone was tested and does not work; `controller_events`
becomes schema 17 in a later loop; its specification is a `to_state` and
`from_state` on run transitions and a `unit_id` on every unit-scoped
event.

## One stated exception to the fail-first rule

`TestControllerEventsReplayFromAttribution` PASSES on the untouched tree,
and section 17's preamble says a passing class is not evidence. Its
subject is not schema 16: it is the attribution stream the controller
already writes, so it can only ever run against an untouched controller.
It passing means its verdict is recorded. This is written into
RED-L04-store.txt at the point where a reader would otherwise notice the
gap. Ten of the eleven store classes, and the section 18.1 pin, are red in
that file.

---

## DONE-CHECK, verbatim, all run after the last edit

```
$ cd /Users/khalil.maaouni/Documents/BrotherModeUp/tools && python3 test_bm_store.py
----------------------------------------------------------------------
Ran 960 tests in 29.996s

FAILED (failures=2)
STORE EXIT: 1
```

The two failures are BLOCKED-1 and BLOCKED-2 above and nothing else:

```
$ python3 test_bm_store.py 2>&1 | grep -E "^(FAIL|ERROR): " | sort -u
FAIL: test_removes_rows_and_writes_attribution_naming_the_purge (__main__.TestPurgeProject)
FAIL: test_structural_gate4_bare_execute_sites_are_all_named_exceptions (__main__.TestFixRoundGates)
```

Count moved 908 to 960, so 52 tests were added and none was removed,
skipped or silenced.

```
$ cd /Users/khalil.maaouni/Documents/BrotherModeUp/tools && python3 test_bm_project.py
PROJECT EXIT: 0
........................................
----------------------------------------------------------------------
Ran 40 tests in 17.228s

OK
```

40 before, 40 after: section 18.1 changed an existing assertion rather
than adding a test.

Targeted run over the eleven new classes:

```
$ python3 -m unittest test_bm_store.TestSchema16IsAdditive \
    test_bm_store.TestRecordInsightRefusals \
    test_bm_store.TestRecordBriefingRefusals \
    test_bm_store.TestKeyDecisionCannotSkipTheHandback \
    test_bm_store.TestTheLedgerIsAppendOnly \
    test_bm_store.TestOpenKeyDecisions \
    test_bm_store.TestActiveMinutesSince \
    test_bm_store.TestLeadPurgeLeavesNoOrphans \
    test_bm_store.TestInsightsAreWithheldByDefaultInADump \
    test_bm_store.TestLeadReadAccessors \
    test_bm_store.TestControllerEventsReplayFromAttribution
----------------------------------------------------------------------
Ran 52 tests in 0.710s

OK
TARGETED EXIT: 0
```

Per class: TestSchema16IsAdditive 5, TestRecordInsightRefusals 16,
TestRecordBriefingRefusals 6, TestKeyDecisionCannotSkipTheHandback 2,
TestTheLedgerIsAppendOnly 4, TestOpenKeyDecisions 4,
TestActiveMinutesSince 4, TestLeadPurgeLeavesNoOrphans 2,
TestInsightsAreWithheldByDefaultInADump 2, TestLeadReadAccessors 5,
TestControllerEventsReplayFromAttribution 2. Total 52.

The glob allowance sweep, re-run after the last edit, unchanged and at
zero violations:

```
$ python3 -m unittest test_bm_store.TestGlobAllowancesGrantOnlyWhatTheyLiterallyMatch -v
Ran 3 tests   OK

glob allowance sweep (TestGlobAllowancesGrantOnlyWhatTheyLiterallyMatch.
                      test_no_declarable_path_names_a_file_its_contract_refuses)
  allowed spellings swept : 132
  candidate spellings     : 42
  triples checked         : 55440
  VIOLATIONS              : 0
  violations under a NON-GLOB allowance: 0
  assertGreater(triples, 20000) -> True
```

Identical to the counts the previous fix report recorded (132 / 42 /
55440 / 0 / 0), so the founder's glob rule was not touched.

`CONTROLLER_STATE_TRANSITIONS` and `AUTONOMY_FLOORS` are byte-identical to
their pre-change state:

```
$ git diff -U0 tools/bm_store.py | grep -E "^[+-]" \
    | grep -iE "CONTROLLER_STATE_TRANSITIONS|AUTONOMY_FLOORS|AUTONOMY_FLOOR_IDS"
(no output)
```

Only four lines were deleted across all three files, all intended:

```
$ git diff -U0 tools/bm_store.py tools/test_bm_store.py tools/test_bm_project.py \
    | grep "^-" | grep -v "^---"
-SCHEMA_VERSION = 15
-    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
-                      13: _TABLES_V13, 14: _TABLES_V14, 15: _TABLES_V15}
-                          "controller_runs": 0})
```

(The `now_iso` line moved to a shared `_ISO_STAMP_FORMAT` constant, which
`parse_iso_stamp` also uses so the write format and the read format cannot
drift.)

No em or en dash appears in any file I wrote: scanned, zero hits in
bm_store.py, test_bm_store.py, test_bm_project.py and RED-L04-store.txt.

---

## Not closed, with the reason

1. **BLOCKED-1 and BLOCKED-2.** Two existing tests need a one-line
   addition each. I stopped rather than edit, per the brief. Both remedies
   are written above and I can apply them in under a minute on the word.
   Until then `python3 tools/test_bm_store.py` exits 1.
2. **The section 14 verdict is not in docs/KNOWN-LIMITS.md.** That file
   is Writer C's. The verdict text is above, ready to paste.
3. **Not run, deliberately, because the brief forbade it:**
   `tools/test_all.py`, `tools/test_bm_lead.py`, `tools/test_bm_controller.py`.
   The orchestrator runs the gate.
4. **Flagged for whoever runs the full gate:** `SCHEMA_VERSION` moved to
   16, and `tools/bm_project_facts.py` derives `FACTS["schema_version"]`
   from that line, which
   `tools/test_bm_docs.py:824 test_no_active_page_states_a_different_schema_version`
   compares against every active doc page. I grepped the active docs and
   found no page stating a bare schema version at all, so I do NOT expect
   this to fire, but I did not run test_bm_docs.py (Writer C's file) to
   confirm it.
5. **Not verified by me:** anything in `tools/test_bm.py`,
   `tools/test_bm_consent.py`, `tools/test_bm_docs.py`,
   `tools/test_bm_controller.py`, `tools/test_bm_sentinel.py` or
   `tools/test_bm_autonomy.py`. Those suites build stores and a
   `SCHEMA_VERSION` bump reaches them; the design's own section 17.5 says
   so and assigns them to the gate, not to Writer A.
