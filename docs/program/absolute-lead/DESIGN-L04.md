Status: CURRENT. Fable design, 2026-08-05. Implementation loop L04 of the
absolute-lead program (founder mode and IC mode). Nothing here is built yet.

# DESIGN L04: founder mode, IC mode, the insight ledger, the handback, and the shipped watchdog

Target tree: /Users/khalil.maaouni/Documents/BrotherModeUp

Files this design authorises a writer to change, and nothing else:

    tools/bm_store.py
    tools/bm_lead.py                      (NEW)
    tools/test_bm_store.py
    tools/test_bm_lead.py                 (NEW)
    tools/test_bm_project.py              (the pinned purge dict only)
    tools/test_bm_consent.py
    tools/test_bm_docs.py
    tools/test_all.py
    tools/write_sites.json                (only if the audit log requires it)
    hooks/hooks.json
    pyproject.toml
    .github/workflows/tests.yml
    capabilities.status.json
    README.md                             (generated block only, via bm-docs)
    docs/ROADMAP.md                       (generated block only, via bm-docs)
    docs/AUTONOMY.md                      (one stale sentence, section 13.3)
    docs/KNOWN-LIMITS.md
    SECURITY.md
    references/status-view.md
    references/terminology.md
    commands/brotherme-brief.md           (NEW)
    commands/brotherme-decisions.md       (NEW)
    commands/brotherme-handback.md        (NEW)
    commands/brotherme-handover-pack.md   (NEW)
    commands/brotherme-status.md
    commands/brotherme-next.md
    commands/brotherme-help.md
    commands/brotherme-start.md
    docs/program/absolute-lead/evidence/L04/   (NEW folder, section 17)

Not in the list, and deliberately: tools/bm_controller.py, tools/bm_project.py,
tools/bm_autonomy.py, tools/bm_telemetry.py, scripts/setup.py. Section 2 law L6
and section 15.5 say why each stays shut.

Inputs read in full before writing this:
docs/program/absolute-lead/DESIGN-insight-ledger-and-handback.md,
docs/program/mirrorforge/FABLE-MIRRORFORGE-HARMONIZATION-REVIEW.md,
docs/program/absolute-lead/evidence/L03/DESIGN-round4.md,
references/status-view.md, references/terminology.md, references/kickoff.md,
references/forecasting.md, references/pulse.md, references/honesty.md,
references/founder-model.md, all eleven files under commands/,
hooks/hooks.json, pyproject.toml, capabilities.status.json,
product.identity.json, and every point of tools/bm_store.py,
tools/bm_controller.py, tools/bm_project.py, tools/bm_docs.py,
tools/test_bm_consent.py, tools/test_bm_docs.py and tools/test_bm.py that this
design names.

Every line reference below is to the CURRENT working tree, verified by reading
it, not by memory.

---

## 0. What this design does not touch

These hold today. No section below changes their behaviour, and a writer who
finds themselves editing them has misread this document.

1. **`CONTROLLER_STATE_TRANSITIONS`** (tools/bm_store.py:3072 to 3095) is not
   widened, not narrowed, and not edited. Section 3.4 READS it and section 17.1
   proves at import time that the plain-language map covers every key. No run
   state move is made by anything this design adds.
2. **`AUTONOMY_FLOORS`** (tools/bm_store.py:3142 to 3155) gains no sixth entry.
   Section 9.2 READS `AUTONOMY_FLOOR_IDS` (3154) to detect one class of key
   decision. The founder-facing closed set is unchanged.
3. **The controller engine.** `ControllerEngine` (tools/bm_controller.py:881),
   `step` (1566), `_finish` (1303 to 1332), `check_timeouts` (2229) and every
   `cmd_*` between 4591 and 5007 are untouched. Section 15.5 gives the reason.
4. **The consent gate's existing programs.** `scripts/setup.py`'s
   `config_path` (112 to 116), `read_config` (119 to 139), `is_consented`
   (142 to 147) and `write_config` (178 to 196) are read, never edited.
   `tools/bm_telemetry.py`'s `_consented` (514 to 526) is copied in shape, not
   modified. `tools/bm_sessionstart.sh`'s gate (18 to 21) stays exactly as it
   is.
5. **`purge_project`'s attribution policy** (tools/bm_store.py:11749, the
   docstring at 11770 to 11777). The new tables are deleted the same way every
   other project-scoped table is, and the attribution trail is still only
   appended to, never touched.
6. **The five safety floors, the signed contract, one store, one canonical
   integrator, one writer per file.** The harmonization review's
   non-negotiables (docs/program/mirrorforge/FABLE-MIRRORFORGE-HARMONIZATION-REVIEW.md:77
   to 82) carry forward unchanged.

---

## 1. Coverage table: every requirement, and where it is satisfied

| Requirement | One line | Satisfied in |
|---|---|---|
| R1 command surface | what a founder types, what it prints, advanced view, every command file named | 3, 4, 15.3 |
| R1a one recommended next action | exactly one, mechanically | 3.4, 3.6 |
| R1b estimates as ranges with confidence | never a point, per references/forecasting.md | 3.4, 3.7 |
| R1c plain language per the terminology map | new terms get rows before they may appear | 4.4, 15.3 |
| R2 the insights table, schema 16 | full column list, additive | 5.1, 5.3 |
| R2a the purge entry | both new tables pinned, red by design if skipped | 5.5, 18.1 |
| R2b the service-layer write path | one method, no SQL elsewhere | 6.1 |
| R2c its refusals | fourteen, each with a reason code | 6.2 |
| R3 the half-hour briefing trigger | ACTIVE work defined mechanically | 7.1, 7.2 |
| R3a what it contains | six lines, each sourced from rows | 7.3 |
| R3b where it renders | stdout, the Stop hook, 50-TIMELINE.md | 7.4 |
| R3c what it does when nothing happened | it refuses to manufacture a briefing | 7.5 |
| R4 handback mechanics end to end | five acts, in one fixed order | 9.4 |
| R4a the developer brief | eight sections, generated from rows | 10 |
| R4b how a handback is recorded | append-only, what the system would have chosen | 9.5 |
| R5 the handover pack | seven pages, what each traces to | 11.1 |
| R5a the docs-truth test | forward and backward, both directions | 11.3 |
| R6 seven conversation shapes | named, with what each fixture asserts | 12 |
| R7a MirrorForge BM-A29 capability truth | six new register rows, two stale claims corrected | 13 |
| R7b MirrorForge MF-L02 event ledger | DEFERRED, with the test that decides it | 14 |
| R8 IC mode | what it is, how it differs, what a developer sees | 4 |
| F1 watchdog ON BY DEFAULT | shipped, always on after consent | 8.1, 8.2 |
| F2 activates only after the setup consent gate | one door, AST-proven, hook-inventory-proven | 8.3, 8.4 |
| F3 pre-consent write structurally impossible | not merely absent | 8.4 |
| F4 disclosed in SECURITY.md and KNOWN-LIMITS.md | exact sections named | 8.6 |
| F5 handback on every key decision, always last | a store refusal, not a rendering convention | 9.3 |
| F6 key decision defined mechanically | four detected, one declared and marked as such | 9.2 |
| F7 evidence_class, REASONED never settled fact | enforced in the renderer and in the pack | 5.2, 4.4 |
| C1 schema 16, additive | no existing table changes | 5.3, 15.4 |
| C2 CONTROLLER_STATE_TRANSITIONS and AUTONOMY_FLOORS not widened | read only | 0.1, 0.2 |
| C3 one writer per file | three disjoint writer sets | 19 |
| C4 every artifact generated from rows | CANVAS.md and STATE.md precedent followed | 11.2 |
| C5 no em or en dashes | the shipped dash test extended | 17.5, 18.6 |

Nothing in the brief is left unmapped. Section 16 lists what this design
deliberately does not close and why.

---

## 2. The seven laws this design adds

Everything below is an application of one of these. A writer unsure what to do
in a case this document did not enumerate applies these in order.

* **L1 The ledger cites the store, it never replaces it.** An insight is a
  claim ABOUT rows. Where an insight and a row disagree, the row wins and the
  disagreement is itself appended as a RISK insight. No reader of a generated
  page is ever shown a number the store does not hold.
* **L2 The ledger is append-only.** No `UPDATE` and no `DELETE` touches
  `insights` or `briefings` anywhere except `purge_project`. A correction is a
  new row whose `supersedes` names the row it corrects. This is the same law
  `autonomy_contracts` already lives under (tools/bm_store.py:12518 to 12520)
  and it is proven the same way, by an ast guard.
* **L3 A key decision that offers no handback cannot be written.** The
  handback is a store-level refusal on the write path (section 6.2, refusal
  R7), not a courtesy in a renderer. An author who forgets it gets an
  `OwnershipRefused`, not a quiet omission.
* **L4 REASONED is never rendered as settled fact.** `evidence_class` maps
  onto references/honesty.md:9 to 11's four calibration labels through one
  function, and REASONED renders with a fixed prefix in every surface. A claim
  with no prefix cannot exist, because the prefix is applied by the renderer,
  not by the author.
* **L5 Nothing writes before consent, and the door is the only way in.** The
  module that ships the watchdog constructs its store in exactly one function,
  and that function refuses without consent. A writer who forgets the check
  cannot obtain a store handle at all.
* **L6 The judgement stays out of the engine.** The controller records what
  happened; the coordinator records why. Insights are written through the new
  CLI, never by `tools/bm_controller.py`. This is why section 0.3 holds and why
  the writer split in section 19 is clean.
* **L7 A generated page carries the id of every row it renders.** Every claim
  line ends in a trace tag. That is what makes the docs-truth test in section
  11.3 able to run backwards as well as forwards.

---

## 3. Founder mode: the command surface

### 3.1 The new module

**`tools/bm_lead.py`**, console script `bm-lead`, is the founder surface. It is
a THIN CLI over `tools/bm_store.py`'s service methods and read accessors, in
exactly the sense `tools/bm_autonomy.py:14 to 19` and
`tools/bm_controller.py:18 to 31` state as house law: it issues no SQL of its
own, and a `TestNoSQLGuard` copied from tools/test_bm_controller.py:97 fails
the build if a SQL-shaped literal or a `sqlite3` import ever appears in it.

The file to mirror for plumbing is **tools/bm_project.py**: `_out` (215),
`_err` (219), `_root` (223), `_parse` (235), `_actor` (295 to 316),
`_ACTOR_FLAGS` (319), `_print_json` (322), the `COMMANDS` dict shape (1515 to
1526), `main` (1529) and `cli` (1555). Copy those shapes verbatim. Do not
invent a second flag parser.

It imports no module banned by tools/test_bm.py:1130's
`test_no_network_claim_is_mechanically_true`: no `subprocess`, no `asyncio`, no
`urllib`, no `socket`. Section 8.2 explains why the watchdog needs none of
them, and section 18.6 records that this test does not change.

### 3.2 The three commands a founder types

    bm-lead outcome    --project-id ID [--set "<what you want>"] [--ic] [--json]
    bm-lead status     --project-id ID [--ic] [--advanced] [--json]
    bm-lead decisions  --project-id ID [--ic] [--json]

That is the whole founder surface: one outcome command, one status, one
decision queue. Everything else is machinery, and section 3.3 lists it.

`outcome --set` writes the outcome through `Store.upsert_project`
(tools/bm_store.py:11385), the same method `bm_project.py`'s `cmd_start` (612)
uses, so there is exactly one writer of a project row and it is the store.
`outcome` with no `--set` prints where the work stands in two lines and then
the ONE recommended next action. `outcome` never signs a contract, never opens
a controller run and never dispatches anything: those are founder-gated or
belong to `bm-controller`, and duplicating them here would make a second
driver.

`status` prints the eight fields of references/status-view.md:8 to 16, in that
order, generated from rows. This is the design's largest single improvement
over what ships today: commands/brotherme-status.md:7 currently asks the MODEL
to translate `bm_project.py status` into those eight fields, which puts a
language model between the founder and the truth. After L04 the eight fields
are computed, and the model reads them out.

`decisions` prints the open key decisions, highest stakes first, each as a
decision card in the shape of references/kickoff.md:42 to 54, each ending in
the handback option (section 9.3).

### 3.3 The machinery commands, which the coordinator runs

    bm-lead brief         --project-id ID [--ic] [--json]
    bm-lead insight       --project-id ID --kind K --subject S --claim C ...
    bm-lead handback      --project-id ID --decision-id ID --why "..."
    bm-lead handover-pack --project-id ID [--out DIR]
    bm-lead watchdog      --tick [--project-id ID]

`watchdog --tick` is the hook entry point (section 8). The other four are
things a coordinator or an analyst runs. All nine subcommands live in one
`COMMANDS` dict, and `main` gates the whole dict (section 8.4).

### 3.4 What `status` prints, field by field, and where each field comes from

Every field is computed from rows. Where a field cannot be computed, it says so
rather than guessing, per references/honesty.md:8 to 12.

| Field | Source | When absent |
|---|---|---|
| Goal | `Store.get_project(project_id)["goal"]` (tools/bm_store.py:12001). If a live contract exists and its `outcome` differs, print the goal and append a RISK line naming the disagreement (law L1). | "no outcome recorded yet"; next action is `bm-lead outcome --set` |
| Direction | the newest DECISION insight's `claim`; else the live contract's `done_definition` from `Store.latest_contract` (13005); else the project's `phase` | "not agreed yet" |
| Progress | if a controller run exists, DONE units over total units from `Store.list_units(run_id)` (14378), as "4 of 9 steps accepted"; else tasks by state, as "4 of 9 tasks accepted" | "nothing planned yet" |
| Time remaining | `Store.latest_forecast` (12088), rendered as a range with confidence and the next reforecast event, exactly `bm_project.py`'s `_forecast_lines` (708 to 729) does | "not forecast yet"; next action is to record one. A point is never emitted (references/forecasting.md:16) |
| Decision needed | `Store.open_key_decisions` (section 6.3). If one or more, the highest-stakes one travels as a decision card, never as prose (references/status-view.md:26 to 27) | "none" |
| Risk | open RISK insights created since the previous briefing, plus unresolved alerts with `requires_human` true from `Store.list_alerts(resolved=False)` (12103) | "none new" |
| Evidence | the newest insight whose `evidence_class` is EXECUTED or MEASURED, rendered as its `evidence` field with the label from section 4.4 | "no executed evidence recorded yet" (never dressed up as a read) |
| Next step | section 3.6's router, exactly one line | never absent |

Stakes order for "highest stakes first": `GATE`, `RULE`, `TEST`, `DEFERRAL`,
`PREFERENCE`, then newest first inside a class. That order is a module tuple,
`DECISION_STAKES`, so the sort is data and the fixtures can assert it.

### 3.5 The advanced view

`--advanced` adds exactly the nine items references/status-view.md:43 to 51
enumerates: task ids, runtime and model identifiers, token input and output
details, worktree paths, commands that were run, raw test output, hook
evidence, store verification, receipt fingerprints. It is per request and never
sticky: a later `status` with no flag returns to the eight fields. Fixture S2
(section 12) asserts exactly that.

`--ic` is a different thing and section 4 defines it.

### 3.6 Exactly one recommended next action

`next_action(store, project_id)` returns one `(text, why, command)` triple. It
is a first-match router over rows, in this fixed order, so two runs on the same
rows always agree:

1. An open key decision exists, and the highest-stakes one names a floor id
   from `AUTONOMY_FLOOR_IDS` (tools/bm_store.py:3154): the action is to answer
   that decision. Nothing else can move.
2. An open founder step exists (`Store.list_human_steps(project_id,
   resolved=False)`, tools/bm_store.py:13081): the action is that step's
   `what`, in plain words, with its click path.
3. An open key decision exists: answer it.
4. A controller run exists and its state is DELIVERABLE_READY: accept the work.
5. A controller run exists with an open dispatch: the action is to finish and
   record the work in flight.
6. No live contract, but an outcome is recorded: agree the authorisation.
7. No outcome recorded: state the outcome.
8. Everything above is empty: continue the newest ready task from
   `Store.list_tasks(project_id, status="ready")`, ranked exactly as
   `bm_project.py`'s `cmd_next` (832 to 873) ranks it.
9. Nothing at all: "nothing is waiting on you" plus what would create work.

Every branch prints one action and one WHY line, matching `cmd_next`'s shipped
shape at bm_project.py:868 to 872. A second action is never printed.
`test_exactly_one_next_action_in_every_branch` (section 17.2) drives all nine
branches and asserts each response contains exactly one line beginning
`Next step:`.

### 3.7 Estimates

Every duration or budget `bm-lead` emits comes from a forecast row and is
rendered by one function, `render_forecast_lines`, whose output shape is copied
from bm_project.py:708 to 729. There is no arithmetic on top of a forecast
anywhere in bm_lead.py, and a structural test asserts that no format string in
the module contains a bare "hours" or "days" outside that function. A bare date
or bare number is never emitted (references/forecasting.md:16).

---

## 4. IC mode

### 4.1 What it is

IC mode is the same rows rendered for the person doing the engineering rather
than for the founder. It is not a second data path and not a second document:
`status`, `decisions` and `brief` each have one collector and two renderers,
and the collector is shared. That is what keeps founder mode and IC mode from
drifting: a fixture (S2, section 12) asserts that every field value in the IC
render is byte-identical to the founder render's value for the fields they
share.

### 4.2 How it differs from founder mode

| Founder mode | IC mode adds |
|---|---|
| eight fields, plain wording | the same eight, plus the block below |
| "only one worker edits a file at a time" | the fence's lifecycle uuid and its state |
| "4 of 9 steps accepted" | unit ids and their statuses, the run id, the `stop_reason` enum |
| "about 25k to 45k tokens of model work" | raw token and minute totals from `Store.spend_totals` (tools/bm_store.py:13028) against both ceilings |
| a claim with its calibration label | the raw `evidence_class`, the `insight_id`, and the exact `evidence` command string |
| "a decision is waiting" | the `decision_class` and WHICH of the five triggers in section 9.2 fired, and for PREFERENCE, that it was declared rather than detected |
| "your authorisation" | the contract id, its revision, and its state |
| nothing | the open dispatch ids and their ages against `DEFAULT_DISPATCH_TIMEOUT_SECONDS` (tools/bm_controller.py:860) |
| nothing | the active-minutes count and the event count behind the briefing clock (section 7.1) |

### 4.3 How it is selected, and why that is honest

Two ways, both explicit: the `--ic` flag, and the environment variable
`BROTHERMODE_VIEW=ic` (the env prefix product.identity.json:15 to 18 already
declares). references/status-view.md:53 says the advanced view is "per request,
never sticky by assumption". The environment variable is sticky, so it would
break that rule if it were left silent. It does not, because:

* every IC render ends with one footer line naming the switch that turned it on
  and how to turn it off, so the mode is never assumed and never invisible; and
* references/status-view.md gains a short "IC mode" section saying exactly
  this. That register file is in this design's allowed set (section 15.3) for
  that reason: a mode that the register does not describe is a mode that
  violates it.

`--ic` and `--advanced` compose. `--ic` implies nothing about `--advanced`:
`--advanced` is the founder's per-request peek at machinery, `--ic` is the
engineer's standing view, and a fixture asserts they are independent.

### 4.4 evidence_class in each mode, and the REASONED rule

One function, `evidence_label(evidence_class)`, maps the four classes onto the
four calibration labels references/honesty.md:9 to 11 already defines. There is
no second vocabulary.

| evidence_class | Founder-mode prefix | IC-mode suffix |
|---|---|---|
| EXECUTED | `verified by command:` | ` [EXECUTED <the command>]` |
| MEASURED | `measured:` | ` [MEASURED <the number observed>]` |
| READ | `verified by inspection:` | ` [READ <the file and line>]` |
| REASONED | `my reasoning, not verified:` | ` [REASONED]` |

The REASONED prefix is applied by the renderer, never by the author, so a
REASONED claim cannot reach any surface without it. Three tests hold this: a
unit test on `evidence_label`; a fixture (S7) asserting the prefix in the
founder render; and a docs-truth assertion (section 11.3) that no line in any
generated page carries a REASONED trace tag without the prefix. That is the
executable form of the founder decision that REASONED may never be presented as
settled fact, and of law L19's own rule that a verdict naming no executed
falsification is NO-DATA rather than a finding.

---

## 5. Schema 16

### 5.1 The `insights` table

```sql
CREATE TABLE IF NOT EXISTS insights (
  insight_id       TEXT PRIMARY KEY,
  project_id       TEXT NOT NULL REFERENCES projects(project_id),
  created_at       TEXT NOT NULL,
  kind             TEXT NOT NULL,
  subject          TEXT NOT NULL,
  claim            TEXT NOT NULL,
  evidence         TEXT NOT NULL DEFAULT '',
  evidence_class   TEXT NOT NULL,
  alternatives     TEXT NOT NULL DEFAULT '[]',
  flip_condition   TEXT NOT NULL DEFAULT '',
  confidence       TEXT NOT NULL,
  confidence_basis TEXT NOT NULL DEFAULT '',
  mutation         TEXT NOT NULL DEFAULT '',
  observed         TEXT NOT NULL DEFAULT '',
  decision_class   TEXT NOT NULL DEFAULT '',
  control_offered  INTEGER NOT NULL DEFAULT 0,
  control_taken    INTEGER NOT NULL DEFAULT 0,
  supersedes       TEXT NOT NULL DEFAULT '',
  work_record      TEXT NOT NULL DEFAULT '',
  run_id           TEXT NOT NULL DEFAULT '',
  unit_id          TEXT NOT NULL DEFAULT '',
  session_id       TEXT NOT NULL DEFAULT '',
  actor_type       TEXT NOT NULL DEFAULT '',
  actor_name       TEXT NOT NULL DEFAULT ''
);
```

Five differences from the founder design's sketch
(DESIGN-insight-ledger-and-handback.md:38 to 52), each with its reason:

1. **`supersedes` replaces a forward pointer.** The sketch has `control_taken`
   as a field on the decision row, which would need an `UPDATE` when a handback
   is taken later. That breaks append-only. Instead a HANDBACK row carries
   `supersedes` naming the decision it answers, written at insert time.
   `control_taken` survives as a column and is 1 on the HANDBACK row itself,
   0 everywhere else. "Was the handback taken on decision X" is answered by
   "does a HANDBACK row exist whose supersedes is X", which is a query, not a
   mutation. `supersedes` is a plain TEXT column with a store-level existence
   check, NOT a self-referencing foreign key, because AZ F-A4's lesson
   (DESIGN-round4.md:80) is that a colliding id must refuse with a reason code,
   never raise `sqlite3.IntegrityError`, and because a self-FK complicates the
   purge in section 5.5 for no gain.
2. **`mutation` and `observed` are their own columns.** The founder design
   requires every CALIBRATION insight to carry the mutation it applied and the
   count it observed (DESIGN-insight-ledger-and-handback.md:132 to 133). Buried
   inside free-text `evidence` that rule is unenforceable; as columns it is
   refusal R5 in section 6.2.
3. **`decision_class` is new.** It carries which of the five key-decision
   triggers fired (section 9.2), so the handback rule (law L3) is a mechanical
   condition on a column rather than a judgement at the call site.
4. **`confidence_basis` is split out of `confidence`.** The sketch says
   "calibrated, with the basis". Two columns make "state the basis" checkable.
5. **`run_id` and `unit_id` join `work_record`.** The sketch has one link to
   the work identity. The controller's own identity is a run and a unit, and
   00-SITUATION.md needs to group by them.

Closed sets, as module tuples beside the existing ones at tools/bm_store.py:3127
to 3155:

```python
INSIGHT_KINDS = ("DECISION", "CALIBRATION", "RISK", "LEARNING", "HANDBACK")
EVIDENCE_CLASSES = ("EXECUTED", "MEASURED", "READ", "REASONED")
INSIGHT_DECISION_CLASSES = ("GATE", "RULE", "TEST", "DEFERRAL", "PREFERENCE")
INSIGHT_CONFIDENCE = ("low", "moderate", "high")
```

No `CHECK` constraint is written into the DDL for any of them. The store's own
convention is a refusal with a reason code naming the whole allowed set (see
`_autonomy_enum`, referenced at tools/bm_store.py:3125 to 3126), and a CHECK
would produce a bare `sqlite3.IntegrityError` instead.

### 5.2 The `briefings` table

```sql
CREATE TABLE IF NOT EXISTS briefings (
  briefing_id      TEXT PRIMARY KEY,
  project_id       TEXT NOT NULL REFERENCES projects(project_id),
  created_at       TEXT NOT NULL,
  trigger          TEXT NOT NULL,
  active_minutes   INTEGER NOT NULL DEFAULT 0,
  event_count      INTEGER NOT NULL DEFAULT 0,
  skipped_events   INTEGER NOT NULL DEFAULT 0,
  since_briefing   TEXT NOT NULL DEFAULT '',
  run_state        TEXT NOT NULL DEFAULT '',
  open_steps       INTEGER NOT NULL DEFAULT 0,
  where_we_are     TEXT NOT NULL,
  what_changed     TEXT NOT NULL DEFAULT '',
  what_it_cost     TEXT NOT NULL DEFAULT '',
  decision_insight TEXT NOT NULL DEFAULT '',
  risk_insight     TEXT NOT NULL DEFAULT '',
  session_id       TEXT NOT NULL DEFAULT '',
  actor_type       TEXT NOT NULL DEFAULT '',
  actor_name       TEXT NOT NULL DEFAULT ''
);

BRIEFING_TRIGGERS = ("ACTIVE_MINUTES", "PHASE_BOUNDARY", "REQUESTED")
```

**Why a second table rather than a sixth `kind`.** An insight makes a CLAIM and
carries an `evidence_class`; that pair is the whole point of the ledger's
honesty. A briefing makes no claim: it is a timestamped record of what the
founder was shown and of the measurement that made it due. Forcing it into
`insights` would require rows with an empty claim and a meaningless evidence
class, which is precisely the narration the schema exists to make visible
(DESIGN-insight-ledger-and-handback.md:133 to 135). Two tables, one schema
step, one migration.

`run_state` and `open_steps` are stored so the phase-boundary trigger in
section 7.2 is a comparison against the previous row rather than against
remembered state. That is law L4 of the controller design (DESIGN-round4.md:126
to 128) applied here: derived facts are recomputed, and the thing they are
recomputed against is a row.

There is no rendered-text column beyond the five the briefing prints, and there
is no render timestamp, for the same reason `render_canvas`
(tools/bm_project.py:468 to 476) carries none: a regenerated page must be byte
stable from the same rows.

### 5.3 The migration

Copy the shape of `_migrate_14_to_15` (tools/bm_store.py:3834 to 3858) exactly.

```python
_TABLES_LEAD = ("insights", "briefings")
_TABLES_V16 = _TABLES_V15 + _TABLES_LEAD
```

placed beside `_TABLES_CONTROLLER` (tools/bm_store.py:1982 to 1983) and
`_TABLES_V15` (1985), with the same explanatory comment shape. Then:

* `SCHEMA_VERSION = 16` at tools/bm_store.py:81.
* `_TABLES_BY_VERSION` (1987 to 1991) gains `16: _TABLES_V16`.
* `_LEAD_DDL` and `_LEAD_INDEX_DDL` as text constants after `_split_ddl`
  (2144) exists, beside `_CONTROLLER_DDL` (2989) and `_CONTROLLER_INDEX_DDL`
  (3051), with `_LEAD_DDL_STATEMENTS = _split_ddl(_LEAD_DDL)` and
  `_LEAD_INDEX_STATEMENTS = _split_ddl(_LEAD_INDEX_DDL)` beside
  `_CONTROLLER_DDL_STATEMENTS` (3060).
* `_migrate_15_to_16(conn)` beside `_migrate_14_to_15` (3834), body identical
  in shape: two `for statement in ...: conn.execute(statement)` loops. It uses
  `_split_ddl` rather than `executescript` for the reason 2144 gives: an
  implicit COMMIT would break the caller's `BEGIN EXCLUSIVE`.
* `_MIGRATIONS` (3861 to 3876) gains `15: _migrate_15_to_16,`.
* `_ensure_schema` gains an `if SCHEMA_VERSION >= 16:` block calling
  `_migrate_15_to_16(self.conn)`, immediately after the schema-15 block at
  tools/bm_store.py:5733 to 5738 and before the `meta` seeding at 5739.
* `_ensure_indexes` (5749) gains `if SCHEMA_VERSION >= 16:
  self.conn.executescript(_LEAD_INDEX_DDL)` after the last existing guard.

Indexes:

```sql
CREATE INDEX IF NOT EXISTS insights_project_created_idx
  ON insights(project_id, created_at);
CREATE INDEX IF NOT EXISTS insights_project_kind_idx
  ON insights(project_id, kind);
CREATE INDEX IF NOT EXISTS insights_supersedes_idx
  ON insights(supersedes);
CREATE INDEX IF NOT EXISTS briefings_project_created_idx
  ON briefings(project_id, created_at);
```

`insights_supersedes_idx` is not decoration: `open_key_decisions` (section 6.3)
is an anti-join against it and runs on every `status`.

**Why additive schema 16 rather than JSON inside an existing table.** Four
mechanical reasons, not taste. The purge pin in section 5.5 needs a table name.
The `REFERENCES projects(project_id)` foreign key is what makes an orphan
impossible. The append-only ast guard in section 17.3 matches on table names in
SQL literals. And the docs-truth test in section 11.3 needs to enumerate rows,
which a JSON blob cannot do without a second parser. Schema 15 is taken by the
controller (tools/bm_store.py:81), so additive changes start at 16, exactly as
docs/program/mirrorforge/FABLE-MIRRORFORGE-HARMONIZATION-REVIEW.md:65 to 67
requires.

### 5.4 Redaction

`_DUMP_SAFE_COLUMNS` (tools/bm_store.py:4362, consulted at 4323 and 4606) is
withhold-by-default: an unlisted column comes back as a length marker. The new
tables therefore need entries, and the decision about WHICH columns is a
privacy decision, taken here:

Listed as safe (identifiers, enums, counters and timestamps only):

    ("insights", "insight_id"), ("insights", "project_id"),
    ("insights", "created_at"), ("insights", "kind"),
    ("insights", "evidence_class"), ("insights", "decision_class"),
    ("insights", "confidence"), ("insights", "control_offered"),
    ("insights", "control_taken"), ("insights", "supersedes"),
    ("insights", "work_record"), ("insights", "run_id"),
    ("insights", "unit_id"),
    ("briefings", "briefing_id"), ("briefings", "project_id"),
    ("briefings", "created_at"), ("briefings", "trigger"),
    ("briefings", "active_minutes"), ("briefings", "event_count"),
    ("briefings", "skipped_events"), ("briefings", "since_briefing"),
    ("briefings", "run_state"), ("briefings", "open_steps"),
    ("briefings", "decision_insight"), ("briefings", "risk_insight")

Deliberately NOT listed, so they stay withheld: `subject`, `claim`,
`evidence`, `alternatives`, `flip_condition`, `confidence_basis`, `mutation`,
`observed`, `where_we_are`, `what_changed`, `what_it_cost`, and both actor
columns. Those are founder and project content. This is the same accounting the
`notes` block at tools/bm_store.py makes for `author`, `anchor_key`, `body`,
`resolution` and `override_reason`, and the comment beside the new block says
so in the same words: a dump shows that a decision exists and withholds what it
says.

### 5.5 The purge entry

`purge_project` (tools/bm_store.py:11749) gains two deletes, inserted between
the autonomy block that ends at 11963 and the `_write_attribution` call at
11965, so both new tables go before the `projects` delete at 11973:

```python
removed["insights"] = _exec(
    self, "DELETE FROM insights WHERE project_id=?",
    (project_id,)).rowcount
removed["briefings"] = _exec(
    self, "DELETE FROM briefings WHERE project_id=?",
    (project_id,)).rowcount
```

Order between the two is free (neither references the other), and both are
after the controller and autonomy deletes purely for readability. `supersedes`
is not a foreign key (section 5.1), so a single statement removing a whole
project's chain cannot trip a per-row check.

This is the entry the founder design calls out
(DESIGN-insight-ledger-and-handback.md:139 to 141), and it is red-by-design
because tools/test_bm_project.py:1365 to 1389 pins the WHOLE `removed` dict by
exact equality, with the comment at 1384 to 1386 saying exactly why. A schema
16 that adds these tables and skips the pin turns that test red on the next
run. Section 18.1 records the pin's new contents.

---

## 6. The service layer

### 6.1 The write path

Two methods on `Store` (tools/bm_store.py:5515), both following the transaction
and attribution shape of `open_run` (13281 to 13347), both taking a dict the
way `upsert_project` (11385) does, because a twenty-four column row does not
belong in a positional signature:

```python
def record_insight(self, project_id, insight, actor):
    """Append ONE row to the insight ledger. Returns
    {'insight_id', 'kind', 'decision_class'}.

    `insight` is a dict; every key of INSIGHT_FIELDS is accepted and
    nothing else (an unknown key is a refusal, not a silent drop, so a
    typo in a column name fails loudly the way the walk-edge guard at
    tools/bm_controller.py:261 to 266 fails loudly).

    APPEND ONLY. This module contains no UPDATE and no DELETE against
    insights outside purge_project, the same law autonomy_contracts lives
    under (tools/bm_store.py:12518 to 12520), proven the same way by an
    ast guard (tools/test_bm_store.py:16226's shape)."""

def record_briefing(self, project_id, briefing, actor):
    """Append ONE row to the briefing timeline. Returns
    {'briefing_id', 'trigger', 'active_minutes'}. Same append-only law."""
```

Both open `self._transaction()` (the `BEGIN IMMEDIATE` at tools/bm_store.py:6564),
validate before any write, `INSERT`, then call `self._write_attribution(...)`
(11343) inside the SAME transaction with event types `insight.recorded` and
`briefing.recorded`, and return a small dict. `created_at` comes from
`now_iso()` (255). `session_id`, `actor_type` and `actor_name` are filled from
the `actor` dict exactly as `_write_attribution` does at 11354 to 11369.

No other module issues SQL against either table. `bm_lead.py`'s
`TestNoSQLGuard` (section 17.2) proves it.

### 6.2 The refusals

`ValueError` for a malformed argument the caller controls, `OwnershipRefused`
with a kebab-case reason code for a well-formed input the store's own rules
refuse. That is the convention `open_run` (tools/bm_store.py:13300 to 13330)
sets and `test_structural_every_ownership_refusal_names_a_reason_code`
(tools/test_bm_store.py:6906) enforces.

| # | Condition | Raises |
|---|---|---|
| R1 | `kind` not in `INSIGHT_KINDS` | `ValueError` naming the whole set |
| R2 | `evidence_class` not in `EVIDENCE_CLASSES` | `ValueError` naming the whole set |
| R3 | `claim` empty or not a string | `ValueError`, "an insight with no claim is narration, not an insight" |
| R4 | `evidence_class` is EXECUTED or MEASURED and `evidence` is empty | `OwnershipRefused('evidence-missing')` |
| R5 | `kind` is CALIBRATION and `mutation` or `observed` is empty | `OwnershipRefused('calibration-incomplete')`, "a calibration must name the control it broke and the count it observed" |
| R6 | `kind` is DECISION and `flip_condition` is empty | `OwnershipRefused('no-flip-condition')`, "a decision nothing could change is not a decision" |
| R7 | `decision_class` is non-empty and `control_offered` is not 1 | `OwnershipRefused('handback-not-offered')`. **This is law L3.** |
| R8 | `decision_class` non-empty and not in `INSIGHT_DECISION_CLASSES` | `ValueError` |
| R9 | `decision_class` non-empty and `alternatives` is an empty list | `OwnershipRefused('no-alternative')`, "the road not taken is the point of a key decision". Ordinary DECISION rows may have none. |
| R10 | `alternatives` is not a JSON-serialisable list of `{"option": str, "why_not": str}` | `ValueError('bad-alternatives')` |
| R11 | `confidence` not in `INSIGHT_CONFIDENCE` | `ValueError` |
| R12 | `kind` is HANDBACK and `supersedes` is empty | `OwnershipRefused('handback-without-decision')` |
| R13 | `supersedes` names no insight, or names one in another project | `OwnershipRefused('not-found')` / `OwnershipRefused('foreign-insight')`, the shape `_refuse_foreign_run` (tools/bm_store.py, used by `claim_unit` at 13931) already uses |
| R14 | `kind` is HANDBACK and a HANDBACK row already supersedes that decision | `OwnershipRefused('handback-already-taken')` |
| R15 | `project_id` names no project | `OwnershipRefused('not-found')`, refused before the foreign key can raise |
| R16 | an unknown key appears in the `insight` dict | `ValueError` naming the key |

For `record_briefing`: `trigger` not in `BRIEFING_TRIGGERS` is a `ValueError`;
`active_minutes` negative or not an int is a `ValueError`; `since_briefing`
naming a briefing of another project is `OwnershipRefused('foreign-briefing')`;
`where_we_are` empty is a `ValueError`.

R7 deserves its own sentence, because it is the mechanism the founder decision
asks for. The founder design proposed wiring the handback into a
decision-window helper "so it cannot be omitted by an author who forgets"
(DESIGN-insight-ledger-and-handback.md:147 to 149). A helper can be bypassed by
writing the row directly. A refusal in the store cannot: there is no other way
to write the row. That is strictly stronger, and it is why the render-side test
in section 17.2 is a second belt rather than the only one.

### 6.3 The read accessors

On `Store`, with matching pass-throughs on `ReadOnlyStore` (tools/bm_store.py:14646,
beside `get_run`'s pass-through at 14888):

```python
def list_insights(self, project_id, kind=None, since=None, until=None,
                  limit=None, raw=False)
def get_insight(self, insight_id, raw=False)
def list_briefings(self, project_id, since=None, until=None, limit=None,
                   raw=False)
def latest_briefing(self, project_id, raw=False)
def open_key_decisions(self, project_id, raw=False)
def active_minutes_since(self, project_id, since_iso, now=None)
```

`open_key_decisions` returns DECISION insights with a non-empty
`decision_class` for which NO other insight names them in `supersedes`. That is
the whole definition of "open": a decision leaves the queue when something
supersedes it, whether that something is a HANDBACK row (the founder took
control) or a later DECISION row (the founder picked an option and the
coordinator recorded the pick). No status column, no `UPDATE`, no second truth.

`until` exists on both list accessors because every generated page filters rows
by `created_at <= <the page's cut>` (section 11.2), which is what makes a
regenerated handback brief byte-identical a week later.

`active_minutes_since` is section 7.1.

`raw` follows the shipped split exactly: text output is local display and
passes `raw=True`, `--json` is the export surface and stays redacted unless
`--raw` is also given (tools/bm_project.py:738 to 741).

---

## 7. The active-work clock and the half-hour briefing

### 7.1 What "active work" means, mechanically

The founder design says the cadence is "thirty minutes of ACTIVE work" and
names this as the one part with no precedent in the toolchain, and the one
thing that would move the estimate if it needed real process supervision
(DESIGN-insight-ledger-and-handback.md:72 to 74 and 159 to 161). It does not
need process supervision. It needs a sum over timestamps, and the timestamps
already exist.

```python
ACTIVE_GAP_CEILING_SECONDS = 300
BRIEFING_ACTIVE_MINUTES = 30

def active_minutes_since(self, project_id, since_iso, now=None):
    """How many minutes of ACTIVE work this project has accumulated since
    `since_iso`. Returns {'active_minutes': int, 'events': int,
    'skipped': int}.

    The activity signal is the attribution table (tools/bm_store.py:2700
    to 2716), which every mutating service method appends to through
    _write_attribution (11343). An attribution row exists BECAUSE work
    happened, which is what makes it a work signal and not a clock.

    Let T be [since_iso] followed by every attribution timestamp for this
    project in (since_iso, now], ascending. Active seconds is the sum over
    consecutive pairs of min(gap, ACTIVE_GAP_CEILING_SECONDS). `now` is
    NOT appended to T: an open-ended idle stretch at the end accrues
    nothing, so a session that stops working stops accruing immediately.

    A row whose timestamp does not parse in now_iso()'s own format
    ("%Y-%m-%dT%H:%M:%SZ", 255) is skipped and counted in 'skipped', never
    guessed at; the briefing discloses a non-zero skipped count rather
    than presenting a total that quietly dropped rows."""
```

The ceiling is the whole mechanism, so its value is argued rather than picked.
At 300 seconds, a session emitting an event every thirty seconds reaches thirty
active minutes in about thirty wall-clock minutes, which is the founder's
cadence. A session emitting one event per hour accrues five minutes per event
and needs six hours to earn a briefing, which is the "an idle session does not
spam" half. A session that goes quiet for two hours while genuinely busy cannot
exist, because the work it is doing writes attribution rows. Both halves of
DESIGN-insight-ledger-and-handback.md:72 to 74 fall out of one constant, and
the constant is a module-level name so a fixture can lower it and drive the
whole clock deterministically without sleeping.

### 7.2 What triggers a briefing

```python
def briefing_due(store, project_id, now):
    """(due, trigger, stats, previous_briefing_row_or_None)."""
```

In this order, first match wins:

1. **ACTIVE_MINUTES.** `active_minutes_since(project_id, previous.created_at)`
   is at least `BRIEFING_ACTIVE_MINUTES`. With no previous briefing, the
   baseline is the project row's `created_at`.
2. **PHASE_BOUNDARY.** The controller run's `state` from
   `Store.get_run(project_id)` (tools/bm_store.py:14365) differs from
   `previous.run_state`, OR the count of open founder steps from
   `Store.list_human_steps(project_id, resolved=False)` (13081) differs from
   `previous.open_steps`. Going from no run to a run is a boundary; so is a
   founder step opening or closing. This is why both columns are stored
   (section 5.2).
3. **Not due.** Everything else.

`REQUESTED` is never returned by `briefing_due`: it is the trigger
`bm-lead brief` writes when a human asked, and section 7.5 covers the case
where a human asks and nothing has happened.

### 7.3 What a briefing contains

Six lines, at most, exactly the founder design's shape
(DESIGN-insight-ledger-and-handback.md:64 to 71). Each is computed by
`collect_briefing(store, project_id, previous)` and rendered by
`render_briefing(row, ic=False)`.

| Line | Source | Rule |
|---|---|---|
| Where we are | run state through `RUN_STATE_PLAIN`, else the project phase | one sentence, outcome first |
| What changed | attribution event types since `previous.created_at`, collapsed by type with counts, plus the newest EXECUTED or MEASURED insight's `evidence` | if nothing changed, this line is the only content and section 7.5 applies |
| What it cost | `Store.spend_totals` (13028) against the live contract's two ceilings, plus the forecast range for what remains | measured spend is a fact and prints as a number; anything remaining is a range with confidence |
| What I decided | the newest DECISION insight since `previous.created_at`, its first alternative and its flip condition | carries its calibration label from section 4.4 |
| What I am unsure of | the newest open RISK insight and its `flip_condition` as "what would settle it" | omitted only when there is genuinely none, and then it says so |
| Your options | `HANDBACK_OPTION_TEXT` | **always present, always last** |

`RUN_STATE_PLAIN` is a module dict in bm_lead.py mapping every key of
`bs.CONTROLLER_STATE_TRANSITIONS` (tools/bm_store.py:3072 to 3095) to one plain
sentence. An import-time guard raises if any key is missing, copying the shape
of the walk-edge guard at tools/bm_controller.py:261 to 266. That is how a
future controller state cannot silently render as a raw enum in front of a
founder.

The briefing obeys references/pulse.md's anti-noise rules
(pulse.md:74 to 80): one cause, one line; no raw stack trace; user impact
before technical cause; one recommended action.

### 7.4 Where it renders

Three places, one renderer:

1. `bm-lead brief` prints it to stdout.
2. `bm-lead watchdog --tick` prints it to stdout when it is due, which the Stop
   hook surfaces to the founder (section 8).
3. `50-TIMELINE.md` in the handover pack renders every stored briefing in
   order, so a reader can replay the run (section 11.1).

All three call `render_briefing`. The row is written once, by whichever of 1 or
2 found it due, and the other two read it. Two callers cannot double-write,
because `record_briefing` is called only from `_emit_briefing`, which takes the
store's write lock through `self._transaction()` and re-checks
`briefing_due` inside it. A test drives two `watchdog --tick` calls back to
back and asserts exactly one row appears.

### 7.5 What it does when nothing happened

This is a design decision, not an edge case, because the wrong answer here is a
timeline full of empty rows that nobody trusts.

* An ACTIVE_MINUTES briefing cannot be empty: thirty active minutes require at
  least six activity events by construction (section 7.1).
* A PHASE_BOUNDARY briefing cannot be empty: the boundary is the change.
* A REQUESTED briefing CAN be empty, and when it is, **`bm-lead brief` writes
  no row.** It prints one line naming the briefing that still stands, its age
  through the shape of `_elapsed_since` (tools/bm_autonomy.py:331), the standing
  next action from section 3.6, and the handback line. When there has never
  been a briefing at all, it says that instead and names what would produce
  one.

The rule in one sentence, and it is the sentence the fixture asserts: the
system does not manufacture a briefing to look busy; it names the one that
still stands. Fixture S6 (section 12) drives exactly this and asserts
`list_briefings` returns the same count before and after.

---

## 8. The watchdog, shipped

### 8.1 What it is, and what it cannot be

Founder decision, 2026-08-05: the watchdog ships ON BY DEFAULT, activates only
after the setup consent gate, and is disclosed in SECURITY.md and
docs/KNOWN-LIMITS.md.

It cannot be a daemon. Three independent reasons, all mechanical:

1. `tools/test_bm.py:1130`'s `test_no_network_claim_is_mechanically_true` bans
   `import subprocess` and `import asyncio` in every non-test file under
   tools/, with exactly two named per-file exceptions (`bm_autosave.py` and
   `bm_controller.py`, tools/test_bm.py:1150 to 1158). A third exception would
   have to be argued into SECURITY.md, and the argument would be "so we can run
   a background process", which is the opposite of the claim that section
   defends.
2. docs/program/mirrorforge/FABLE-MIRRORFORGE-HARMONIZATION-REVIEW.md:71 to 72
   already ruled on the adjacent question: metering tool calls is the right
   goal but "the mechanism must not add a daemon".
3. A daemon would be a scheduler that writes, which is precisely the thing the
   pre-consent law is about. Not having one is not a limitation here; it is the
   safety property.

So the watchdog is **a due-check on a tick the product already has.** The tick
is the Stop hook, which fires once per model turn. `briefing_due` is a few row
reads and a sum; when it is not due, nothing is written and nothing is printed.

### 8.2 The wiring

`hooks/hooks.json`'s Stop entry (27 to 38) currently runs one program. It gains
a second on the same line, in the shape the PreCompact line (39 to 50) already
uses for two programs:

```json
"command": "sh -c 'p=$(cat); printf %s \"$p\" | python3 \"${CLAUDE_PLUGIN_ROOT}/tools/bm_telemetry.py\" stop-warn; printf %s \"$p\" | python3 \"${CLAUDE_PLUGIN_ROOT}/tools/bm_lead.py\" watchdog --tick'",
"timeout": 30,
```

The timeout rises from 15 to 30 because the line now runs two programs,
matching PreCompact's 60 for its two.

This is the exact hook line whose two-program shape produced this project's own
recorded incident: an earlier consent fix gated the FIRST program on a line and
missed the SECOND, and `bm_telemetry.py precompact-brief` wrote the founder's
last message verbatim into the vault before anyone had said yes
(tools/test_bm_consent.py:288 to 307, disclosed in SECURITY.md:270 to 282).
Section 8.4 is written against that incident specifically.

### 8.3 What a tick does

```
1. Read the consent state. Not consented: print nothing, write nothing,
   exit 0. This is the FIRST statement of main(), before the COMMANDS
   lookup (section 8.4).
2. Resolve the project. No store, no project, or more than one project and
   no --project-id: print nothing, exit 0. A hook is never a place to ask
   a question.
3. briefing_due(...). Not due: print nothing, write nothing, exit 0.
4. Due: record_briefing(...) once, then print render_briefing(row).
5. Any exception from step 2, 3 or 4: print nothing, exit 0. A watchdog
   that breaks a founder's turn is worse than a watchdog that misses a
   briefing, which is the same fail-open posture bm_fence_hook.py's
   _FailOpen takes.
```

Steps 2, 3 and 5 are why "on by default" is not "noisy by default": the common
case writes nothing and prints nothing.

### 8.4 Making a pre-consent write structurally impossible

The founder decision is explicit that the pre-consent law has been broken twice
and that absence of a write is not enough. Here is what exists today and why it
is not enough, then what this design adds.

**Today.** Five programs each carry their own local `_consented()` wrapper
(`tools/bm_telemetry.py:514 to 526`, `tools/bm_autosave.py:1472 to 1486`,
`tools/bm_bash_audit.py:185 to 196`, `scripts/doctor.py:552 to 566`,
`tools/bm_sessionstart.sh:18`). Each must be CALLED, correctly, as the first
line of every function that writes. The project's own fix for the scatter was
not a choke point; it was an inventory test,
`test_every_hook_wired_telemetry_command_checks_consent`
(tools/test_bm_consent.py:569), which parses hooks.json and greps each
hook-wired `bm_telemetry.py` command body for a `_consented()` call. That test
covers exactly one module. A new module inherits none of it.

**Four mechanisms, layered, and the first one is the structural one.**

1. **One door.** `tools/bm_lead.py` constructs a store in exactly one function:

   ```python
   def _store_or_refuse(kv, write):
       """The ONLY constructor of bs.Store and bs.ReadOnlyStore in this
       file. Raises ConsentMissing when scripts/setup.py's is_consented is
       False. Every subcommand obtains its handle here or does not have
       one."""
   ```

   Consent is read by loading `scripts/setup.py` BY PATH and calling its
   `read_config` (112 to 139) and `is_consented` (142 to 147), copying
   `bm_telemetry.py`'s `_load_bm_setup` / `_get_bm_setup` / `_consented`
   (482 to 526) verbatim in shape. There is no second definition of what
   consent means.

2. **The door is guarded at the entry point.** `main(argv)` computes the
   consent state ONCE, before the `COMMANDS` lookup, and refuses the whole
   dispatch when it is False, printing the shipped sentence
   `"bm_lead: setup is not complete yet; run: python3 scripts/setup.py"`
   for a human-invoked command and printing NOTHING for `watchdog`.

3. **An ast guard proves both.** `TestConsentIsTheOnlyDoor`
   (tools/test_bm_lead.py) parses tools/bm_lead.py with `ast` and fails if any
   of these is false:

   * `bs.Store(` and `bs.ReadOnlyStore(` each appear in exactly one function,
     and that function is `_store_or_refuse`;
   * no call to `open` or `io.open` anywhere in the file has a mode argument
     containing `w`, `a` or `x` (the handover pack writes through
     `bs.write_generated_document`, tools/bm_store.py:15866, which is reached
     only from a function holding a handle from `_store_or_refuse`);
   * `os.makedirs`, `os.replace` and `shutil` appear nowhere;
   * the first statement in `main`'s body after argv normalisation is the
     consent computation, and the `COMMANDS` subscript appears textually after
     it;
   * `COMMANDS` is read in exactly one function, `main`.

   This is the same technique as `TestNoSQLGuard`
   (tools/test_bm_controller.py:97), which the project already trusts to hold a
   house law across a five thousand line file.

4. **The hook inventory test is widened from one module to all of them.**
   `test_every_hook_wired_telemetry_command_checks_consent`
   (tools/test_bm_consent.py:569) becomes
   `test_every_hook_wired_command_of_every_module_checks_consent`: it parses
   `hooks/hooks.json`, extracts every `<module>.py <subcommand>` pair on every
   hook line whatever the module, and asserts each names a consent check.
   Section 18.2 records why the rename and the widening are a strengthening.

Two shipped tests then cover the new program for free, and they are the
failing-first evidence for this whole section:
`test_no_wired_command_of_any_module_writes_before_consent`
(tools/test_bm_consent.py:471) already drives EVERY command string in
hooks.json against a fresh HOME and asserts no file appears in either tree, and
`test_calibrated_a_wired_command_that_never_ran_is_not_a_pass` (550) already
guards that assertion against vacuity. Add the watchdog to hooks.json with no
gate in bm_lead.py and 471 goes red. That is the RED this section must produce.

### 8.5 The one thing this does not claim

The watchdog is gated on consent. `tools/bm_store.py` and `tools/bm_project.py`
are not, and never were: a human who types `python3 tools/bm_project.py start`
before running setup writes rows today. That is not a regression this design
introduces and not a defect it closes. The pre-consent law as SECURITY.md:260
to 282 states it is about UNATTENDED writes, which is what a hook is. Section
16.3 records the observation so it is not mistaken for a claim.

### 8.6 Disclosure

**SECURITY.md**, inside the Threat model section's consent-config asset
paragraph (260 to 282), which already enumerates the gated set. That
enumeration currently reads "the gated set is `bm_sessionstart.sh`,
`bm_autosave.py`, the Bash audit's two phases, and all three hook-wired
`bm_telemetry.py` commands". It gains `bm_lead.py watchdog`, and one new
sentence naming what the watchdog does on a tick, what it writes when it is due
(one briefing row), and that it writes nothing at all when it is not. The
sentence about a test reading `hooks/hooks.json` stays true and gets stronger,
because section 8.4 mechanism 4 widens exactly that test.

**docs/KNOWN-LIMITS.md**, a new dated section
`## L04: what founder mode, the ledger and the watchdog do NOT do (2026-08-05)`,
in the format of the existing entries (see the entry at 345 to 355 for the
shape). It records, at minimum: that the watchdog is a due-check on the Stop
hook and therefore cannot fire in a session that never stops; that
`ACTIVE_GAP_CEILING_SECONDS` is a chosen constant and not derived from measured
history; that the ledger records the coordinator's judgement and the store
remains the truth; that section 16's deferrals stand; and the section 8.5
observation.

---

## 9. Key decisions and the handback

### 9.1 The option, and its stable wording

```python
HANDBACK_OPTION_TEXT = (
    "Hand this back to me: I take this decision and the work under it, and "
    "BrotherMode records where it stopped and what it would have done.")
```

Verbatim from the founder design
(DESIGN-insight-ledger-and-handback.md:81 to 83). It is a module constant so
that a test can assert byte equality, and so that changing the wording is a
visible diff on a founder-facing promise rather than a paraphrase somebody
improved.

### 9.2 What makes a decision a key decision, mechanically

The founder design's five triggers
(DESIGN-insight-ledger-and-handback.md:91 to 97), each with the row it is
detected from. `key_decision_class(store, project_id, context)` returns `''` or
one of the five, first match wins, in stakes order.

| Class | Trigger | Detected from |
|---|---|---|
| `GATE` | touches a hard gate or a safety floor | the pending action's floor id is in `AUTONOMY_FLOOR_IDS` (tools/bm_store.py:3154), or `Store.list_human_steps(project_id, resolved=False)` (13081) returns a row whose `floor` is non-empty and whose `blocks` names this work |
| `RULE` | changes a rule the founder approved | the action would write a new `autonomy_contracts` revision, that is, it calls `Store.set_contract_state` (12611) or a re-sign, so `Store.latest_contract(project_id)["revision"]` (13005) would move |
| `TEST` | supersedes or retires a test | any path in the unit's `write_scope` (`controller_units.write_scope`, tools/bm_store.py:3016) has a basename beginning `test_` or lies under a `tests/` segment |
| `DEFERRAL` | defers a finding rather than closing it | a unit's status is SKIPPED or BLOCKED in `Store.list_units(run_id)` (14378), or `Store.list_interruptions(project_id, answered=False)` (13067) is non-empty |
| `PREFERENCE` | chooses between designs whose flip condition is founder preference | **declared**, never detected: `bm-lead insight --decision-class PREFERENCE` |

PREFERENCE is the one honest human-judgement entry, and the ledger says so on
that row: every render of a PREFERENCE decision prints
`declared by the coordinator, not detected from the records`, in founder mode
and in IC mode alike. That sentence is emitted by `render_decision_card`, not by
the author, for the same reason the REASONED prefix is (law L4).

### 9.3 The option is a store refusal, not a rendering convention

Refusal R7 (section 6.2): an insight with a non-empty `decision_class` and
`control_offered` not equal to 1 cannot be written. Combined with
`open_key_decisions` reading only rows with a non-empty `decision_class`, the
consequence is total: every decision that reaches the founder queue offered the
handback, because a decision that did not could not be recorded.

The renderer carries the second belt. `render_decision_card(insight, ic=False)`
is the ONLY function in bm_lead.py that emits the string `"Decision needed:"`
(an ast guard asserts this), and it always appends `HANDBACK_OPTION_TEXT` as
the last option line. The card's shape is references/kickoff.md:42 to 54:
recommended option first with its Why, each alternative with its Tradeoff on
one line, two to four options of which the last is always the handback.

`test_every_key_decision_card_ends_in_the_handback_option` drives every row in
a planted ledger of all five decision classes and asserts the last option line
of each rendered card is byte-equal to `HANDBACK_OPTION_TEXT`. A decision
window rendered without it is a test failure, exactly as the founder design
requires (DESIGN-insight-ledger-and-handback.md:149).

### 9.4 Taking it: five acts, in one fixed order

`bm-lead handback --project-id ID --decision-id INSIGHT_ID --why "<text>"`.
The order below is load-bearing and the reason for each position is stated.

**Act 1: pause the authorisation.**
`Store.set_contract_state(project_id, "paused", changed_by, reason,
session_id, actor)` (tools/bm_store.py:12611). `live` to `paused` is already a
legal move (`AUTONOMY_STATE_TRANSITIONS`, tools/bm_store.py:3160 to 3165) and
it is reversible, which is the whole point: `paused` moves back to `live`.

This is FIRST because it is the act that makes further autonomous work
impossible. Every dispatch route passes through one gate against the live
contract (DESIGN-round4.md:126 to 128, law L5), and `open_run` refuses
`'no-live-contract'` unless the latest contract is live
(tools/bm_store.py:13320 to 13330). Pausing therefore closes the window before
anything else in this sequence runs. No controller state is moved, no
`CONTROLLER_STATE_TRANSITIONS` entry is used, and `bm-lead` never becomes a
second controller driver, which is what AZ F-A7 (DESIGN-round4.md:1606 to 1618)
warns against.

**Act 2: write the evidence block as a checkpoint.**
`Store.checkpoint(fence_uuid, expected_version, next_intent=<what the
developer should do next>, blockers=<the open question>, body=<the evidence
block>)` (tools/bm_store.py:10980), where `fence_uuid` is
`Store.get_run(project_id)["fence_uuid"]`, the lifecycle uuid of the
controller's own work record.

The evidence block goes in `body`, NOT in the transition's `evidence`
argument, and this is the single most likely place for a writer to lose data:
`transition` keeps the passed `evidence` only when moving to `complete`
(`new_evidence = evidence if to_state == "complete" else row["evidence"]`,
tools/bm_store.py:10844), so evidence passed on a park is silently discarded.

**Act 3: park the work record.**
`Store.transition(fence_uuid, expected_version + 1, to_state="parked",
session_id=..., note=<the handback note>)` (tools/bm_store.py:10723). Parking
is what releases the fence: `transition`'s own docstring says a parked record
has no live writer by definition and any session may resume it, which is
exactly the state a developer taking over needs. `active` to `parked` is a
legal move under `_LEGAL_MOVES` (tools/bm_store.py:4635 to 4640).

**Act 4: append the HANDBACK insight.**
`Store.record_insight(project_id, {...}, actor)` with `kind="HANDBACK"`,
`supersedes=<the decision insight_id>`, `control_offered=1`,
`control_taken=1`, and:

* `claim` = what the system WOULD have chosen, in one sentence;
* `alternatives` = what else it weighed and why not, copied forward from the
  decision row so the two rows cannot drift;
* `flip_condition` = what would have changed that choice;
* `evidence` and `evidence_class` = carried forward from the decision row, so a
  handback on a REASONED decision is visibly a handback on reasoning;
* `confidence` and `confidence_basis` = carried forward;
* `subject` = the decision's subject.

Refusal R14 makes a second handback on the same decision impossible.

**Act 5: generate the developer brief.** Section 10.

If any act after Act 1 fails, the command reports an error card
(references/kickoff.md:70 to 84: What happened, Impact, Recommended action,
What remains safe) and states plainly that the authorisation is paused and the
remaining acts did not run. It does NOT attempt to un-pause: reversing a safety
act on an error path is how a half-failed handback becomes a running robot.

### 9.5 What a later reader sees

The founder decision requires that a handback record what the system WOULD have
chosen and why. A reader has, from rows alone and with no code access:

* the DECISION row: the situation, its alternatives, its flip condition, its
  evidence and evidence class, its decision class, and that control was
  offered;
* the HANDBACK row superseding it: the choice not taken, carried forward
  verbatim, plus `control_taken = 1` and the founder's `--why`;
* the contract revision `set_contract_state` appended, which timestamps when
  autonomous work stopped;
* the `digests` row carrying the next intent, and the `transitions` row
  carrying the park;
* `60-HANDBACKS.md`, which renders all of the above with trace tags.

Nothing was edited and nothing was deleted, so "what it would have done" is a
row, not a recollection.

### 9.6 What handback does not do

It does not cancel open dispatches. A unit in flight when control changes hands
stays in flight, and the developer brief lists those dispatch ids under "work
that was in flight when control was handed back", with their ages. Cancelling
them would mean writing controller state from outside the controller, which
section 0.3 forbids. Disclosing them costs a paragraph and loses nothing.

---

## 10. The developer brief

`render_developer_brief(store, handback_insight)` returns the whole page. It is
generated from rows filtered by `created_at <= handback_insight.created_at`
(section 11.2), so regenerating it a week later reproduces it byte for byte.

Eight sections, in this order:

1. **What you are taking over.** The outcome, the done definition, and the one
   sentence of where the work stands. From the project row and the contract.
2. **The decision that was in front of us.** The DECISION row rendered as a
   card, including its alternatives and flip condition.
3. **What BrotherMode would have chosen, and why.** The HANDBACK row's `claim`,
   with its calibration label from section 4.4 and, when REASONED, the prefix.
4. **The open question.** The `blockers` text from the checkpoint written in
   Act 2.
5. **The files.** The work record's claimed paths, plus the write scope of any
   unit that is not DONE.
6. **The reproduction.** Every done-check command from the units in play, and
   the newest EXECUTED insight's `evidence` string, so a developer has a
   command to run rather than a description of one.
7. **Work that was in flight.** Open dispatch ids with their ages (section
   9.6), or "none".
8. **Where to pick up.** The `next_intent` from Act 2's checkpoint, and the
   exact command to resume: `bm-autonomy resume` to return the contract to live
   (tools/bm_autonomy.py:756), then `bm-controller start` with the same
   controller id.

Written to `Handover/HANDBACK-<insight_id first 8 hex>.md` through
`bs.write_generated_document` (tools/bm_store.py:15866). The same function
renders section 60's per-handback block in the pack, and
`test_the_standalone_brief_and_the_pack_section_are_the_same_bytes` asserts the
two are identical, which is what stops the pack and the brief from ever telling
a developer two different stories.

---

## 11. The handover pack

### 11.1 The pages, and what each traces to

`bm-lead handover-pack --project-id ID [--out DIR]` writes into `Handover/` at
the project root (`HANDOVER_ROOT = "Handover"`, mirroring bm_docs.py's
`DOC_ROOT = "Documentation"` at tools/bm_docs.py:119), through
`bs.safe_project_path` (tools/bm_store.py:4701) and
`bs.write_generated_document` (15866).

| Page | Rows it renders | Ordering |
|---|---|---|
| `00-SITUATION.md` | `projects`, `autonomy_contracts` (latest), `autonomy_spend` totals, `controller_runs`, `controller_units` counted by status, `forecasts` (latest), open `alerts`, open `autonomy_human_steps` | fixed section order |
| `10-DECISIONS.md` | `insights` where kind is DECISION | newest first, grouped by `subject` |
| `20-RISKS.md` | `insights` where kind is RISK and nothing supersedes them | newest first |
| `30-CALIBRATIONS.md` | `insights` where kind is CALIBRATION, each with its `mutation` and `observed` | newest first |
| `40-LEARNINGS.md` | `insights` where kind is LEARNING | newest first |
| `50-TIMELINE.md` | `briefings` | oldest first, so a reader replays the run forwards |
| `60-HANDBACKS.md` | `insights` where kind is HANDBACK, each with the DECISION row it supersedes, each followed by its developer brief block (section 10) | newest first |

`PACK_PAGES` is a module tuple of `(relative_path, renderer_name,
one_line_description)`, copying the shape of bm_docs.py's `FILES` (139 to 170),
so "every page" is enumerable data that a test can iterate rather than a list
somebody keeps in sync by hand.

Every page carries its evidence class per claim (the founder design's
requirement at DESIGN-insight-ledger-and-handback.md:114 to 116), because
`render_claim_line` applies the section 4.4 label to every claim on every page.

### 11.2 The generation convention this copies

From the shipped precedent, and each choice named:

* **Whole-file generated, not marker-spliced.** The pack is a generated FOLDER,
  like `Documentation/`, not a mixed page like `CANVAS.md`. So it uses
  `bs.write_generated_document(path, text)` the way bm_docs.py's
  `Generator.write` does (tools/bm_docs.py:1813 to 1868, the call at 1833), and
  human blocks are preserved by that funnel's own
  `protect_human_blocks=True` (tools/bm_store.py:15824). It does NOT copy
  bm_project.py's `_splice_generated` / `_write_generated` (339 to 411), which
  exists for files that carry hand-written prose outside a marker pair. One
  funnel, no duplicated splice logic, no second marker convention.
* **Atomic, single writer.** `write_generated_document` routes through
  `_write_generated_file` (15824) and the atomic temp-file-then-replace path,
  which is the project's one write funnel.
* **No render timestamp anywhere.** `render_canvas`'s docstring
  (tools/bm_project.py:468 to 476) states the rule: a "generated at" line would
  make two back-to-back regenerations of an unchanged project differ by nothing
  but the clock. The pack obeys it.
* **A cut, so the past stays the past.** Every renderer takes `until`, and the
  pack passes `until=now`. The developer brief passes
  `until=<its handback's created_at>`. This is what makes a brief written in
  August still reproduce in September.
* **Trace tags.** Every claim line ends in `[i:<insight_id>]` or
  `[b:<briefing_id>]` (law L7). The audience for this pack is business analysts
  and project leads, and traceability is the whole product for that reader, so
  references/terminology.md gains a row for "trace tag" rather than the tags
  being smuggled past the map.

### 11.3 The docs-truth test

`TestHandoverPackTracesToRows` (tools/test_bm_lead.py). The strongest shipped
precedent is `test_every_register_entry_reaches_the_page`
(tools/test_bm_docs.py:3795 to 3805), whose docstring states the principle this
copies: "The render could agree with itself and still drop a row."

Both directions, because either alone is a hole:

* **Forward, nothing is dropped.** For each of the seven pages, the set of row
  ids the store says belongs on that page equals the set of trace tags found on
  it. Asserted as a set equality with the missing ids named in the failure
  message, exactly as 3795 does.
* **Backward, nothing is invented.** Every trace tag on every page resolves to
  a row through `get_insight` or a briefing lookup, and the row's `kind`
  matches the page it appears on. A page cannot state something no row holds.
* **REASONED is never bare.** Every line carrying a trace tag whose row has
  `evidence_class` REASONED also carries the section 4.4 prefix.
* **Byte stable.** Generating twice with no intervening write produces
  identical bytes (D-4, the `render_canvas` rule above).
* **The cut holds.** Insert a new insight, regenerate the developer brief for
  an older handback, and assert the bytes did not change.

---

## 12. The seven conversation shapes, as behavioral fixtures

Each shape drives the real `bm-lead` CLI against a throwaway store, writes its
transcript to `docs/program/absolute-lead/evidence/L04/S<n>-<NAME>.json`, and
asserts on the transcript. That is the shipped fixture pattern:
`TestEndToEndE4` (tools/test_bm_controller.py:1975) regenerates
`docs/program/absolute-lead/evidence/L03/E4-endtoend.json` on every run by its
own documented design. All seven live in one class per shape in
tools/test_bm_lead.py.

Three of the seven are mandated by the founder design's own fixture list
(DESIGN-insight-ledger-and-handback.md:150 to 151): a run that offers handback
and is refused, one that is taken, and one where the ledger contradicts the
store. Those are S5, S4 and S7.

| # | Name | The conversation | What the fixture asserts |
|---|---|---|---|
| S1 | `COLD_START` | a founder with no project says what they want | `outcome --set` writes exactly one project row; the response contains exactly one line beginning `Next step:`; every duration and budget appears as a range with a confidence (no bare number, references/forecasting.md:16); no left-column term from references/terminology.md:10 to 25 appears anywhere in the output; the recommended next action is branch 7 then 6 of section 3.6 |
| S2 | `STATUS_MID_RUN` | the founder asks where things stand while work is in flight | `status` prints exactly the eight fields of references/status-view.md:8 to 16, in order, and nothing else; none of the nine advanced items (43 to 51) appears; `--advanced` adds them; a following bare `status` drops them again (advanced is not sticky, 53); `--ic` and `--advanced` are independent; every field shared between the founder render and the IC render has a byte-identical value |
| S3 | `DECISION_REQUIRED` | a key decision is open | `decisions` renders a card in references/kickoff.md:42 to 54's shape: recommended first with its Why, each alternative with its Tradeoff, two to four options; the LAST option line is byte-equal to `HANDBACK_OPTION_TEXT`; the card carries its calibration label; a PREFERENCE decision also prints "declared by the coordinator, not detected from the records"; the queue is ordered by `DECISION_STAKES` |
| S4 | `HANDBACK_TAKEN` | the founder hands control back | after `handback`: the contract state is `paused` and its revision moved by one; a `digests` row carries the next intent; the work record is `parked` and its claims no longer bind; exactly one HANDBACK insight exists, superseding the decision, carrying what the system would have chosen; the developer brief file exists and contains all eight sections of section 10; a second `handback` on the same decision refuses `'handback-already-taken'`; the decision has left `open_key_decisions` |
| S5 | `HANDBACK_REFUSED` | the founder picks the recommended option instead | a new DECISION insight supersedes the open one; NO handback row exists; `control_offered` is still 1 on the original row, which is not edited (its `updated` bytes are unchanged, proving append-only); the contract is still `live`; the decision has left `open_key_decisions`; work continues, so the next action is not the decision |
| S6 | `QUIET_STRETCH` | two hours pass with nothing happening | `watchdog --tick` writes nothing and prints nothing; `list_briefings` count is unchanged before and after; active minutes are below `BRIEFING_ACTIVE_MINUTES`; `brief` names the briefing that still stands with its age and writes no row; when there has never been a briefing, it says so and names what would produce one |
| S7 | `BAD_NEWS` | an insight's claim disagrees with a store row, and the founder must be told | the store's value is what `status` prints (law L1); a RISK insight recording the disagreement is appended; the contradicted insight is neither edited nor deleted; the report uses the error-card shape of references/kickoff.md:70 to 84, all four sections in order, impact before cause; the RISK is reported first, before any other content (references/honesty.md:8 to 9); a REASONED claim in the same output carries its prefix |

S7 folds two things the register already treats as one act: a contradiction is
bad news, and bad news is reported to a founder as an error card. Keeping them
apart would have produced an eighth fixture asserting the card format with no
situation attached to it.

Every fixture uses an injected clock and a lowered `ACTIVE_GAP_CEILING_SECONDS`
where timing matters, so none of them sleeps.

---

## 13. MirrorForge BM-A29: capability-register truth

`capabilities.status.json` holds eighteen entries and none of them names the
autonomy contract, the controller, the ledger, founder mode or the watchdog.
The harmonization review assigns the fix to one unit of the L04 train
(docs/program/mirrorforge/FABLE-MIRRORFORGE-HARMONIZATION-REVIEW.md:41), and
the source register records it as BM-A29
(docs/evidence/2026-08-05-mirrorforge-source-program.md:145).

### 13.1 The six rows added

The legal states are `certified`, `beta`, `experimental`, `unsupported`
(tools/test_bm_docs.py:3529 to 3531), every entry needs a non-empty `id`,
`title`, `state` and `evidence` (3555 to 3558), and the evidence must name a
path that exists in the tree (3566 to 3574).

| id | state | Why that state |
|---|---|---|
| `autonomy-contract` | `beta` | the layer ships with its own suite and page, but docs/KNOWN-LIMITS.md:906 records open items and no external use exists. Evidence: tools/bm_autonomy.py, tools/test_bm_autonomy.py, docs/AUTONOMY.md |
| `full-auto-controller` | `beta` | schema 15, an end-to-end killed-and-resumed fixture and a large suite, against docs/KNOWN-LIMITS.md:962's own list of what it does not yet do. Not `experimental`, because `experimental` in this register means "not measured" and this is measured. Not `certified`, because no external pilot exists. Evidence: tools/bm_controller.py, tools/test_bm_controller.py, docs/FULL-AUTO.md |
| `decision-record-and-briefing` | `beta` | schema 16, the ledger and the half-hour briefing, with the seven fixtures. Evidence: tools/bm_lead.py, tools/test_bm_lead.py, docs/program/absolute-lead/DESIGN-insight-ledger-and-handback.md |
| `handing-control-back` | `beta` | offered on every key decision and enforced by a store refusal. Evidence: tools/bm_lead.py, tools/test_bm_lead.py |
| `half-hour-watchdog` | `beta` | on by default after consent, a due-check on the Stop hook, not a daemon. Evidence: hooks/hooks.json, tools/test_bm_consent.py, SECURITY.md |
| `analyst-handover-pack` | `beta` | seven generated pages with a two-direction docs-truth test. Evidence: tools/bm_lead.py, tools/test_bm_lead.py |

No row is `certified`, and that is the honest answer: `certified` in this
register carries cross-platform CI evidence or a shipped refusal test, and none
of these has an external pilot. The register keeps at least one row in each of
the four states, so `test_the_register_states_what_is_not_promised`
(tools/test_bm_docs.py:3707) still passes; it asserts presence of each state,
not a count, so adding six `beta` rows moves nothing.

`updated` at capabilities.status.json:3 moves to the landing date.

### 13.2 The generated blocks

README.md's block and docs/ROADMAP.md's block are regenerated by running
`python3 tools/bm_docs.py capability-status --write` (tools/bm_docs.py:3387) and
`python3 tools/bm_docs.py roadmap-status --write` (3392). They are never hand
edited. Both are then covered by the shipped
`test_every_register_entry_reaches_the_page` pair
(tools/test_bm_docs.py:3795 and 3988), which fails if any new row reaches
neither page.

### 13.3 The two stale claims this corrects

1. **docs/AUTONOMY.md:11** says the controller loop is "U2, not yet built". It
   is built, and docs/FULL-AUTO.md dated the same day describes it. One
   sentence changes. This is inside the capability-truth unit because a
   register that says `beta` while the page says "not built" is the same lag
   BM-A29 names.
2. **README.md** matches nothing for `autonomy`, `Full-Auto`, `bm-controller`
   or `bm-autonomy` today, because its capability table renders only from the
   register. Section 13.1's rows fix that by construction, through 13.2, with
   no hand edit to README prose.

---

## 14. MirrorForge MF-L02: the controller event ledger, DEFERRED

The harmonization review folds MirrorForge's L02 into the L04 train as "its own
fenced unit: append-only controller_events table, additive schema step, replay
test" (docs/program/mirrorforge/FABLE-MIRRORFORGE-HARMONIZATION-REVIEW.md:42).
This design defers the TABLE and lands the TEST that decides whether the table
is needed at all. The reasons, in the order that matters.

**1. The store already has an append-only controller event stream.** The
`attribution` table (tools/bm_store.py:2700 to 2716) is written by
`_write_attribution` (11343) from inside every controller service method's own
transaction: `controller.run.opened` (13344), `controller.unit.claimed`
(inside `claim_unit`, 13931), and one per every other move. It is insert-only,
`purge_project` never touches it except to append (11770 to 11777), and it
carries actor, session and timestamp. A `controller_events` table would be a
SECOND record of the same events, which is exactly the failure the insight
ledger's own refusal section forbids
(DESIGN-insight-ledger-and-handback.md:118 to 125) and which this design
restates as law L1.

**2. The stated need is replay, and replay is testable against what exists.**
So L04 lands `TestControllerEventsReplayFromAttribution`
(tools/test_bm_store.py): drive a controller run to DELIVERABLE_READY, then
reconstruct the run's state sequence and each unit's status sequence from the
`attribution` rows alone, and assert the reconstruction equals the sequence the
rows in `controller_runs` and `controller_units` actually took. That test has
exactly two outcomes and both are useful. Green: replay works, the table is
redundant, and the deferral was correct. Red: it names precisely which
transition leaves no event, which is the specification for the table, sized in
columns rather than in adjectives.

**3. Scope.** L04 already lands two tables, a migration, a new shipped module,
a hook wiring, seven generated pages, seven behavioral fixtures, a widened
consent inventory and six register rows. The review's own instruction is to
fold the MirrorForge units in "where they fit without bloating the train"
(FABLE-MIRRORFORGE-HARMONIZATION-REVIEW.md:60 to 62). A third table plus a
replay engine does not fit; a replay test does, and it costs one class.

**4. What would flip this.** If the replay test goes red on a transition that
matters, `controller_events` becomes schema 17 in the next loop, with the red
output as its specification. That is recorded in docs/KNOWN-LIMITS.md in the
same words, per section 16's rule.

BM-A29 (section 13) is the other half of the fold and it is NOT deferred: it is
cheap, it is real, and the review calls it so at line 34.

---

## 15. Inventory

### 15.1 tools/bm_store.py

| Symbol | Change | Signature or note |
|---|---|---|
| `SCHEMA_VERSION` | CHANGED | 15 to 16, line 81 |
| `INSIGHT_KINDS`, `EVIDENCE_CLASSES`, `INSIGHT_DECISION_CLASSES`, `INSIGHT_CONFIDENCE`, `BRIEFING_TRIGGERS` | NEW | module tuples, section 5.1 and 5.2 |
| `ACTIVE_GAP_CEILING_SECONDS`, `BRIEFING_ACTIVE_MINUTES` | NEW | module ints, section 7.1 |
| `INSIGHT_FIELDS`, `BRIEFING_FIELDS` | NEW | module tuples, the accepted dict keys (refusal R16) |
| `_TABLES_LEAD`, `_TABLES_V16` | NEW | beside 1982 to 1985 |
| `_TABLES_BY_VERSION` | CHANGED | gains `16: _TABLES_V16`, 1987 to 1991 |
| `_LEAD_DDL`, `_LEAD_DDL_STATEMENTS`, `_LEAD_INDEX_DDL`, `_LEAD_INDEX_STATEMENTS` | NEW | beside 2989 to 3060 |
| `_migrate_15_to_16` | NEW | `(conn)`, beside 3834 |
| `_MIGRATIONS` | CHANGED | gains `15: _migrate_15_to_16`, 3861 to 3876 |
| `Store._ensure_schema` | CHANGED | one `if SCHEMA_VERSION >= 16:` block after 5738 |
| `Store._ensure_indexes` | CHANGED | one guarded `executescript` at the end of 5749's body |
| `_DUMP_SAFE_COLUMNS` | CHANGED | twenty-five entries added, section 5.4, at 4362 |
| `Store.record_insight` | NEW | `(self, project_id, insight, actor) -> {'insight_id','kind','decision_class'}` |
| `Store.record_briefing` | NEW | `(self, project_id, briefing, actor) -> {'briefing_id','trigger','active_minutes'}` |
| `Store.list_insights` | NEW | `(self, project_id, kind=None, since=None, until=None, limit=None, raw=False)` |
| `Store.get_insight` | NEW | `(self, insight_id, raw=False) -> dict or None` |
| `Store.list_briefings` | NEW | `(self, project_id, since=None, until=None, limit=None, raw=False)` |
| `Store.latest_briefing` | NEW | `(self, project_id, raw=False) -> dict or None` |
| `Store.open_key_decisions` | NEW | `(self, project_id, raw=False) -> [dict]`, the anti-join of section 6.3 |
| `Store.active_minutes_since` | NEW | `(self, project_id, since_iso, now=None) -> {'active_minutes','events','skipped'}` |
| `ReadOnlyStore` | CHANGED | seven pass-throughs, beside 14888 |
| `Store.purge_project` | CHANGED | two deletes and two `removed` keys, between 11963 and 11965 |

### 15.2 tools/bm_lead.py (NEW)

| Symbol | Note |
|---|---|
| `COMMANDS` | nine entries, section 3.2 and 3.3; read only inside `main` |
| `main(argv)`, `cli()` | shapes copied from tools/bm_project.py:1529 and 1555; consent computed before the dispatch |
| `_out`, `_err`, `_parse`, `_require`, `_print_json`, `_root`, `_actor`, `_ACTOR_FLAGS` | copied from tools/bm_project.py:215 to 322 |
| `ConsentMissing` | module exception |
| `_consent_state()` | loads scripts/setup.py by path, shape of tools/bm_telemetry.py:482 to 526 |
| `_store_or_refuse(kv, write)` | the ONLY store constructor in the file (section 8.4) |
| `HANDBACK_OPTION_TEXT` | section 9.1 |
| `DECISION_STAKES` | `("GATE","RULE","TEST","DEFERRAL","PREFERENCE")` |
| `RUN_STATE_PLAIN` plus its import-time guard | section 7.3, guard shape from tools/bm_controller.py:261 to 266 |
| `evidence_label(evidence_class)` | section 4.4 |
| `render_claim_line(insight, ic=False)` | applies the label and the trace tag |
| `render_forecast_lines(forecast)` | shape from tools/bm_project.py:708 to 729 |
| `render_status(view, ic=False, advanced=False)` | the eight fields |
| `render_decision_card(insight, ic=False)` | the ONLY emitter of `"Decision needed:"` |
| `render_briefing(row, ic=False)` | the six lines |
| `render_developer_brief(store, handback_insight)` | section 10 |
| `collect_status(store, project_id)` | one collector, two renderers |
| `collect_briefing(store, project_id, previous)` | one collector, three consumers |
| `next_action(store, project_id)` | `-> (text, why, command)`, the nine-branch router |
| `key_decision_class(store, project_id, context)` | `-> '' or one of DECISION_STAKES` |
| `briefing_due(store, project_id, now)` | `-> (due, trigger, stats, previous)` |
| `_emit_briefing(store, project_id, trigger, stats, previous, actor)` | the only caller of `record_briefing` |
| `HANDOVER_ROOT`, `PACK_PAGES` | section 11.1, shape from tools/bm_docs.py:119 and 139 |
| `render_pack_page(store, project_id, rel, until)` | one renderer per page, dispatched from `PACK_PAGES` |
| `write_pack(store, project_id, root, until)` | writes through `bs.write_generated_document` |
| `cmd_outcome`, `cmd_status`, `cmd_decisions`, `cmd_brief`, `cmd_insight`, `cmd_handback`, `cmd_handover_pack`, `cmd_watchdog` | `(argv) -> int` |

### 15.3 Non-code files

| File | Change |
|---|---|
| `commands/brotherme-decisions.md` | NEW. Runs `bm-lead decisions`, renders each card through references/kickoff.md, states that the handback option is always available |
| `commands/brotherme-handback.md` | NEW. Runs `bm-lead handback`, explains in plain language what taking it does (the five acts, without the machinery words) and that nothing is lost |
| `commands/brotherme-brief.md` | NEW. Runs `bm-lead brief`, states the quiet-stretch behaviour of section 7.5 |
| `commands/brotherme-handover-pack.md` | NEW. Runs `bm-lead handover-pack`, names the seven pages and their audience |
| `commands/brotherme-status.md` | CHANGED. Runs `bm-lead status` and reads the eight fields out; `bm_project.py status` moves to the advanced paragraph. The current line 7 instruction to TRANSLATE into the eight fields is removed, because they are now computed |
| `commands/brotherme-next.md` | CHANGED. The recommended action comes from `bm-lead status`'s Next step field; when a decision is blocking, it travels as a card carrying the handback line |
| `commands/brotherme-start.md` | CHANGED. Records the outcome with `bm-lead outcome --set` before the guided kickoff continues, so there is one outcome command |
| `commands/brotherme-help.md` | CHANGED. Line 10's "seven things they can say" becomes nine, adding `/brotherme-decisions` and `/brotherme-handback`, plus one sentence naming `/brotherme-brief` and `/brotherme-handover-pack` as the two the coordinator normally runs. The count in that sentence must equal the list |
| `references/terminology.md` | CHANGED. Eight new rows, added BEFORE the terms may appear anywhere, per its own law at 38 to 40: insight ledger, evidence class, briefing, handback, active minutes, watchdog, handover pack, trace tag. Each row states the same fact in plain words, per rule 1 at 29 to 31 |
| `references/status-view.md` | CHANGED. One short "IC mode" section (section 4.3), stating that IC mode is explicit, that it always names the switch that turned it on, and that the default view is unchanged |
| `capabilities.status.json` | CHANGED. Six rows, section 13.1, and `updated` |
| `README.md`, `docs/ROADMAP.md` | CHANGED, generated blocks only, by running bm-docs (section 13.2) |
| `docs/AUTONOMY.md` | CHANGED, one stale sentence at line 11 (section 13.3) |
| `SECURITY.md` | CHANGED, the consent-config asset paragraph at 260 to 282 (section 8.6) |
| `docs/KNOWN-LIMITS.md` | CHANGED, one new dated section (section 8.6 and 16) |
| `hooks/hooks.json` | CHANGED, the Stop line (section 8.2) |
| `pyproject.toml` | CHANGED, `bm-lead = "bm_lead:cli"` in `[project.scripts]` (66 to 80) and `"bm_lead"` in `py-modules` (94 to 113). Both are mandatory: tools/test_bm.py:5409 and 5417 fail if the shipping tools and that list disagree |
| `.github/workflows/tests.yml` | CHANGED, one step running `python3 tools/test_bm_lead.py`. Mandatory: tools/test_all.py:49 enforces that every suite in `SUITES` has a step in that workflow |
| `tools/test_all.py` | CHANGED, `"test_bm_lead.py"` added to `SUITES` (83 to 163), placed after `test_bm_controller.py`, with the same no-apostrophe comment rule the surrounding entries carry |

### 15.4 Schema

`SCHEMA_VERSION` moves 15 to 16 (tools/bm_store.py:81). Two tables and four
indexes are added. **Additive only: no existing table gains, loses or changes a
column, and no existing index is dropped or redefined.** That is the same
promise `_migrate_14_to_15`'s docstring makes (tools/bm_store.py:3834 to 3845)
and it is checked the same way, by `_TABLES_BY_VERSION` (1987 to 1991) carrying
a full table list per version so a schema-15 store is still verified against
schema 15's list before it is migrated.

The migration itself is one function of two loops, run inside `_migrate_from`'s
single `BEGIN EXCLUSIVE` (tools/bm_store.py:6305 to 6359), which backs the file
up first and bumps `meta.schema_version` last.

### 15.5 The files this design deliberately does not open, and why

* **tools/bm_controller.py.** Law L6. The controller records what happened;
  insights record why. Every fact the briefing needs is already an
  `attribution` row the controller writes today, so making the engine write
  insights would put judgement inside a mechanical loop and would put a third
  writer into a file that just came through seven refutation rounds.
* **tools/bm_project.py.** `bm-lead status` READS the project rows
  `bm_project.py` writes; it duplicates no write. Leaving the file shut keeps
  the writer split in section 19 disjoint and keeps `cmd_start`'s guided flow
  exactly where the founder already knows to find it.
* **tools/bm_autonomy.py.** Handback calls `Store.set_contract_state` directly
  (section 9.4 Act 1), the same store method `bm-autonomy pause`
  (tools/bm_autonomy.py:752) calls. Two CLIs over one service method is the
  shipped pattern; a CLI calling another CLI would need `subprocess`, which
  section 8.1 forbids.
* **tools/bm_telemetry.py and scripts/setup.py.** The consent gate's shape is
  copied, never edited (section 0.4). Editing the definition of consent while
  adding a program that depends on it is how the last two incidents happened.

---

## 16. Deferred, with the reason for each

Each is disclosed in docs/KNOWN-LIMITS.md in the same words.

### 16.1 The `controller_events` table

Section 14. The replay test lands; the table waits for that test's verdict.

### 16.2 The watchdog cannot fire in a session that never stops

The tick is the Stop hook, so a single model turn running for two hours emits
no briefing until it ends. Closing this means a tick inside a tool-use hook
(PostToolUse fires often enough), which would run the due-check on every Bash
command in every session, for a briefing that is due at most twice an hour.
That trade is a measurement this design has not made. Recommendation for a
later loop: measure the due-check's cost against a real store first, then
decide. Until then, `bm-lead brief` is the manual path and it is one command.

### 16.3 The store and project CLIs are not consent gated

Section 8.5. A human typing `python3 tools/bm_project.py start` before setup
writes rows today, and this design does not change that. It is recorded so the
watchdog's gate is not read as a claim about the whole toolchain.

### 16.4 `ACTIVE_GAP_CEILING_SECONDS` is chosen, not measured

Five minutes is argued in section 7.1 from the two behaviours the founder
design names, and it is a module constant so it can be moved. It is not derived
from measured session history, because none is recorded. Stated in
KNOWN-LIMITS.md in exactly those words, matching the honesty
`DEFAULT_DISPATCH_TIMEOUT_SECONDS`'s own comment shows
(tools/bm_controller.py:855 to 859: "Thirty minutes, not derived from any
measurement in this repository").

### 16.5 The pack renders one project

`handover-pack` takes one `--project-id`. A store holding several projects
generates several packs, into `Handover/` for the single-project case and
`Handover-<project_id>/` otherwise, mirroring `_canvas_filename`'s rule
(tools/bm_project.py:420 to 431). Cross-project rollup is not offered and is
not implied anywhere on the pages.

---

## 17. Test plan

Every class below is NEW. Every one is written FIRST, run against the UNTOUCHED
tree, and its failure captured to

`docs/program/absolute-lead/evidence/L04/RED-L04-tests.txt`

in four labelled blocks (store, lead, consent, docs) with per-class failure and
error counts. A class that PASSES on the untouched tree is not evidence and
must be rewritten until it reproduces the gap it claims.

### 17.1 tools/test_bm_lead.py, the surface

| Class | Tests | Failing-first evidence it must produce |
|---|---|---|
| `TestConsentIsTheOnlyDoor` | 6 | The five ast assertions of section 8.4 mechanism 3, plus: with `HOME` pointing at a fresh directory, `bm-lead watchdog --tick` and every other subcommand create zero files under HOME and under the project. Today the module does not exist, so all six error on import; after the first skeleton lands they must fail on the assertion, not on the import |
| `TestTheEightFieldsAreComputedNotNarrated` | 5 | `status` emits exactly the eight fields of references/status-view.md:8 to 16 in order; a ninth line is a failure; each absent field says so rather than being omitted; `--advanced` adds exactly the nine items of 43 to 51; a following bare `status` drops them |
| `TestExactlyOneNextAction` | 9 | One test per branch of section 3.6, each asserting exactly one line begins `Next step:` and that the branch chosen is the expected one |
| `TestRangesNeverPoints` | 3 | Every duration and budget in `status`, `outcome` and `brief` matches a range-with-confidence shape; a planted forecast row with only a likely value renders as a range with the unknown ends marked, never as a bare number |
| `TestPlainLanguageHoldsInFounderMode` | 2 | No left-column term of references/terminology.md:10 to 25 appears in any founder-mode output across all nine subcommands; the same drive with `--ic` is allowed to contain them |
| `TestRunStatePlainCoversEveryState` | 2 | The import-time guard raises when a key of `bs.CONTROLLER_STATE_TRANSITIONS` has no plain sentence, proven by monkeypatching a state in; and the shipped map covers all fifteen keys |
| `TestEveryKeyDecisionCardEndsInTheHandbackOption` | 3 | All five decision classes rendered; the last option line is byte-equal to `HANDBACK_OPTION_TEXT` in every one; an ast assertion that `render_decision_card` is the only emitter of `"Decision needed:"` |
| `TestReasonedIsNeverBare` | 3 | `evidence_label` maps all four classes; a REASONED claim renders with its prefix in `status`, `brief` and every pack page; removing the prefix from the renderer turns all three red |
| `TestICModeAndFounderModeShareOneCollector` | 3 | Every shared field value is byte-identical between the two renders; `--ic` and `--advanced` are independent; the IC footer names the switch |

### 17.2 tools/test_bm_lead.py, the machinery

| Class | Tests | Failing-first evidence |
|---|---|---|
| `TestTheActiveWorkClock` | 6 | A dense event series reaches thirty active minutes in about thirty wall minutes; a sparse one does not; an open-ended idle tail accrues nothing; an unparseable timestamp is skipped and counted; zero events gives zero; the ceiling is honoured exactly at the boundary |
| `TestBriefingDue` | 5 | ACTIVE_MINUTES fires at the threshold and not before; PHASE_BOUNDARY fires on a run-state change and on an open-step count change; neither fires twice for one boundary; the first-ever briefing baselines on the project row |
| `TestOneBriefingPerDueWindow` | 2 | Two `watchdog --tick` calls back to back write exactly one row; a concurrent second caller inside the transaction sees the row and writes nothing |
| `TestQuietStretchWritesNothing` | 3 | Section 7.5, all three cases |
| `TestHandbackTakesFiveActsInOrder` | 6 | Contract paused before the park; the evidence block lands in the checkpoint `body` and NOT in the transition `evidence` (a test that plants a marker string and asserts which row holds it, which is the section 9.4 Act 2 trap); the record is parked; the HANDBACK row supersedes the decision; the brief exists; a failure injected into Act 3 leaves the contract paused and reports an error card |
| `TestHandbackIsIdempotentlyRefused` | 2 | `'handback-already-taken'`; and a handback naming a decision of another project refuses `'foreign-insight'` |
| `TestTheDeveloperBriefIsComplete` | 3 | All eight sections of section 10 present; open dispatches listed with ages; the standalone brief and the `60-HANDBACKS.md` section are the same bytes |
| `TestHandoverPackTracesToRows` | 6 | Section 11.3, both directions plus REASONED, byte stability and the cut |
| `TestNoSQLGuard` | 1 | Shape copied from tools/test_bm_controller.py:97: no SQL-shaped literal and no `sqlite3` import in tools/bm_lead.py |
| `TestSevenConversationShapes` | 7 | Section 12, one test per shape, each writing its fixture artifact under `docs/program/absolute-lead/evidence/L04/` |

### 17.3 tools/test_bm_store.py

| Class | Tests | Failing-first evidence |
|---|---|---|
| `TestSchema16IsAdditive` | 4 | A schema-15 store migrates to 16 with both tables present and every schema-15 row intact; a fresh store has them too; the two paths produce identical `PRAGMA table_info` output; `_TABLES_BY_VERSION[15]` is unchanged |
| `TestRecordInsightRefusals` | 16 | One per refusal R1 to R16 of section 6.2, each asserting the reason code and that NOTHING was written |
| `TestKeyDecisionCannotSkipTheHandback` | 2 | R7 fires for all five decision classes; a `decision_class` of `''` with `control_offered` 0 is accepted, so the rule is narrow and not a blanket |
| `TestTheLedgerIsAppendOnly` | 3 | An ast guard, shape copied from `test_structural_no_service_method_updates_an_autonomy_contract_row` (tools/test_bm_store.py:16226), failing if any `UPDATE` or `DELETE FROM` names `insights` or `briefings` outside `purge_project`; plus a behavioural test that a correction appends rather than edits; plus one that `supersedes` is written at insert and never later |
| `TestOpenKeyDecisions` | 4 | A decision with nothing superseding it is open; superseded by a HANDBACK it is closed; superseded by a later DECISION it is closed; a non-key DECISION never appears |
| `TestActiveMinutesSince` | 4 | The store-side half of the clock, including the skipped-row count |
| `TestLeadPurgeLeavesNoOrphans` | 2 | Shape copied from `TestControllerPurgeLeavesNoOrphans` (tools/test_bm_store.py:17355), iterating `bs._TABLES_LEAD`; zero rows survive a purge in either table |
| `TestInsightsAreWithheldByDefaultInADump` | 2 | `claim`, `subject`, `evidence` and the actor columns come back as length markers; the identifier and enum columns come back whole (section 5.4) |
| `TestControllerEventsReplayFromAttribution` | 2 | Section 14. A driven run's state sequence and per-unit status sequence reconstruct from `attribution` alone; the calibration half asserts the reconstruction genuinely reads events and not the entity rows |

### 17.4 tools/test_bm_consent.py and tools/test_bm_docs.py

| Class or test | Change | Evidence |
|---|---|---|
| `test_no_wired_command_of_any_module_writes_before_consent` (471) | none | goes RED the moment hooks.json names the watchdog and bm_lead.py has no gate. This is the section 8 failing-first evidence |
| `test_every_hook_wired_telemetry_command_checks_consent` (569) | RENAMED and WIDENED, section 18.2 | the widened version goes RED against an ungated bm_lead.py |
| `TestCapabilityRegisterIsHonest` (tools/test_bm_docs.py:3686) | none | the six new rows must satisfy it; a row naming a path that does not exist goes red at 3566 to 3574 |
| `TestGeneratedCapabilityStatusBlock` (3747), `TestGeneratedRoadmapStatusBlock` (3956) | none | both go RED after capabilities.status.json changes and before bm-docs regenerates the two blocks. That RED is expected and is the reason 13.2 exists |
| `TestNoDashes` (4754) | CHANGED, section 18.6 | the target list gains tools/bm_lead.py and tools/test_bm_lead.py |

### 17.5 The done-check

After the last edit, in this order, with the command and the last lines of its
output pasted into the fix report:

```
cd /Users/khalil.maaouni/Documents/BrotherModeUp/tools && python3 test_bm_store.py
cd /Users/khalil.maaouni/Documents/BrotherModeUp/tools && python3 test_bm_lead.py
cd /Users/khalil.maaouni/Documents/BrotherModeUp/tools && python3 test_bm_project.py
cd /Users/khalil.maaouni/Documents/BrotherModeUp/tools && python3 test_bm_consent.py
cd /Users/khalil.maaouni/Documents/BrotherModeUp/tools && python3 test_bm_docs.py
cd /Users/khalil.maaouni/Documents/BrotherModeUp && python3 tools/test_bm_controller.py
cd /Users/khalil.maaouni/Documents/BrotherModeUp && python3 tools/test_bm.py
cd /Users/khalil.maaouni/Documents/BrotherModeUp && python3 tools/test_all.py
```

`test_bm_controller.py` is not optional even though no controller file is
edited: this design bumps `SCHEMA_VERSION`, and the controller suite builds
stores. `test_bm.py` is not optional either: it holds the no-network claim
(1130) and the py-modules contract (5409, 5417), both of which this change
touches. `test_all.py` last, because it holds the CI inventory check (49).

Expected counts: no suite's count may DROP. A drop is a deleted test and is a
failure of this change, not a result.

### 17.6 One test-shape rule

Any new test that needs a bm_lead branch which CATCHES a store refusal must
build its store from `bl.bs`, not from its own independent load of bm_store,
and must say why in its docstring, exactly as tools/test_bm_controller.py:1937
to 1945 does. Two branches catch: `cmd_handback`'s Act-3 failure path and
`cmd_insight`'s refusal reporting.

---

## 18. MIGRATION: existing tests whose expectations move

Six items. Every one is named with the exact assertion that moves and the
argument for why the replacement is not weaker. Nothing else in any suite
changes.

### 18.1 `tools/test_bm_project.py:1353` `test_purge_with_confirm_removes_rows_attribution_trail_survives`

The pinned `removed` dict at 1365 to 1389 gains two keys, `"insights": 0` and
`"briefings": 0`, in the fixture's own no-rows case.

Why this is honest: the dict is pinned by exact equality precisely so that a
schema which adds a purged table without adding its key turns this test red.
The test's own comment says so at 1384 to 1386. Adding the keys is the pin
performing its designed function, and the assertion remains exact equality
against the WHOLE dict, so nothing is loosened. `TestLeadPurgeLeavesNoOrphans`
(section 17.3) adds the non-zero case the fixture does not cover, so coverage
strictly increases.

### 18.2 `tools/test_bm_consent.py:569` `test_every_hook_wired_telemetry_command_checks_consent`

Renamed to `test_every_hook_wired_command_of_every_module_checks_consent` and
widened from "every `bm_telemetry.py` subcommand named in hooks.json" to "every
`<module>.py <subcommand>` pair on every hook line, whatever the module".

Why this is a strengthening and not a weakening: every assertion it makes today
about `bm_telemetry.py` survives verbatim, because `bm_telemetry.py`'s commands
are a subset of the widened set. What it gains is exactly the class of defect
this project has already suffered twice: a hook line whose SECOND program was
never gated (tools/test_bm_consent.py:288 to 307). The rename is required, not
cosmetic: leaving the word `telemetry` in the name of a test that now governs
every module would make the name a false description of the law, which is the
same failure mode SECURITY.md:279 to 282 records in prose.

`tools/bm_fence_hook.py` stays an explicit, named exemption inside the widened
test, carrying the reason SECURITY.md:270 to 274 already gives (ownership proof
must exist before the hook can refuse anyone). Encoding the exemption in the
test with its reason is stronger than the current situation, where the
exemption exists only in prose.

### 18.3 `tools/test_bm_docs.py` capability classes

`TestCapabilityRegisterIsHonest` (3686) and its seven tests: **no assertion
changes.** They iterate whatever rows exist, and
`test_the_register_states_what_is_not_promised` (3707) asserts each of the four
states is PRESENT, not how many rows carry it, so six new `beta` rows move
nothing.

`TestGeneratedCapabilityStatusBlock` (3747) and `TestGeneratedRoadmapStatusBlock`
(3956): **no assertion changes**, but both go red between the register edit and
the bm-docs regeneration. That red is the tests working: they exist to catch a
register row that reaches no page. Section 20's build order runs the
regeneration in the same step as the register edit so the red never leaves the
step.

### 18.4 `tools/test_all.py` `SUITES` and the CI inventory

`SUITES` (83 to 163) gains `"test_bm_lead.py"`. That immediately requires a
matching step in `.github/workflows/tests.yml`, because test_all.py:49 enforces
the inventory in both directions. Both edits land together or the gate is red.
No assertion is weakened; one suite joins the gate.

### 18.5 `tools/test_bm.py:5409` and `:5417`, the py-modules contract

`test_every_shipping_tool_is_in_py_modules` and
`test_py_modules_names_nothing_that_does_not_exist` need no edit, and they are
named here because they FAIL if pyproject.toml is not updated in the same
change as tools/bm_lead.py. They are the mechanism that makes adding a module a
decision rather than an accident, and this design lets them do their job rather
than working around them.

### 18.6 `tools/test_bm_docs.py:4754` `TestNoDashes`

The target list at 4758 to 4762 gains `tools/bm_lead.py` and
`tools/test_bm_lead.py`. Why this is honest: the list is an enumeration of the
files the rule governs, and a new shipped tool in the same family that the rule
does not govern would be a hole in a copy rule the founder has stated as
absolute. Adding files to a ban makes it stricter.

### 18.7 Tests verified against the new design and NOT changed

Named because "no change" is a claim that has to be checked, not assumed.

* **`tools/test_bm.py:1130` `test_no_network_claim_is_mechanically_true`.** No
  change, and no third file joins the `allowed` dict at 1150 to 1158.
  `tools/bm_lead.py` imports none of the ten banned modules; the watchdog is a
  due-check on an existing hook tick (section 8.1), not a process.
* **`tools/test_bm_store.py:16226`
  `test_structural_no_service_method_updates_an_autonomy_contract_row`.** No
  change. Handback Act 1 calls `set_contract_state` (12611), which APPENDS
  revision N+1; it issues no `UPDATE` against `autonomy_contracts`.
* **`tools/test_bm_controller.py:1975` `TestEndToEndE4`.** No assertion
  changes. Nothing in this design writes controller rows or moves a run state,
  and `E4-endtoend.json` keys on `final_state`, `duplicate_work_count`,
  `open_human_steps` and per-unit statuses, none of which moves.
* **`tools/test_bm_docs.py:3578` `TestProductIdentityIsOneRecord`.** No change.
  `product.identity.json` is untouched, and `bm-lead` already matches its
  declared `bm-` command prefix (product.identity.json:9 to 14).
* **`tools/test_bm_store.py:17355` `TestControllerPurgeLeavesNoOrphans`** and
  **`:16291` `TestAutonomyPurgeLeavesNoOrphans`.** No change. A sibling class
  is added for the new tables; neither existing class iterates the new tuple.

### 18.8 Collisions

**None.** No change above weakens an assertion. The two that come closest are
18.1 and 18.2, and both are the shipped guard mechanisms performing exactly the
function their own comments say they exist for. A writer who finds a SEVENTH
existing test needing a change must stop and report it rather than editing it,
because this list is the whole set this design predicts.

---

## 19. WRITER SPLIT

One writer per file is law here, so the three sets below are disjoint. No file
appears twice.

### Writer A: the store

    tools/bm_store.py
    tools/test_bm_store.py
    tools/test_bm_project.py

Sections 5, 6, 14's replay test, 15.1, 17.3, 18.1. Deliverable: schema 16
migrates and is additive, both write paths refuse correctly, the ledger is
provably append-only, the purge pins both tables, and the replay verdict is
recorded. Done-check: `python3 test_bm_store.py` and `python3
test_bm_project.py` both green, counts no lower than before.

### Writer B: the lead surface

    tools/bm_lead.py
    tools/test_bm_lead.py
    tools/test_bm_consent.py
    tools/test_all.py
    hooks/hooks.json
    pyproject.toml
    .github/workflows/tests.yml

Sections 3, 4, 7, 8, 9, 10, 11, 12, 15.2, 17.1, 17.2, 17.4's consent half,
18.2, 18.4, 18.5. Deliverable: the nine subcommands, the one door, the
watchdog wired and gated, the seven fixtures. Done-check: `python3
test_bm_lead.py`, `python3 test_bm_consent.py` and `python3 tools/test_bm.py`
all green.

### Writer C: the register and the disclosure

    capabilities.status.json
    README.md
    docs/ROADMAP.md
    docs/AUTONOMY.md
    SECURITY.md
    docs/KNOWN-LIMITS.md
    references/status-view.md
    references/terminology.md
    commands/brotherme-brief.md
    commands/brotherme-decisions.md
    commands/brotherme-handback.md
    commands/brotherme-handover-pack.md
    commands/brotherme-status.md
    commands/brotherme-next.md
    commands/brotherme-help.md
    commands/brotherme-start.md
    tools/test_bm_docs.py
    docs/program/absolute-lead/evidence/L04/ (the RED file and the reports)

Sections 8.6, 13, 15.3, 16, 17.4's docs half, 18.3, 18.6. Deliverable: the
register tells the truth about six capabilities, both generated blocks are
regenerated by bm-docs, the watchdog is disclosed in both required places, the
terminology map carries every new term, and the command surface is documented.
Done-check: `python3 tools/test_bm_docs.py` green.

### Ordering and the two gates between writers

A and C start together. B starts when A's `record_insight`, `record_briefing`
and the six read accessors exist and A's suite is green, because B calls them.

Two gates, both one-way and both cheap:

* **Gate 1, A to B.** A posts the exact signatures it landed. B does not guess
  them.
* **Gate 2, B to C.** C's capability rows for `decision-record-and-briefing`,
  `handing-control-back`, `half-hour-watchdog` and `analyst-handover-pack` name
  `tools/bm_lead.py` and `tools/test_bm_lead.py` as evidence, and
  tools/test_bm_docs.py:3566 to 3574 fails if a named path is not in the tree.
  So C writes every other file first and lands `capabilities.status.json` plus
  the two bm-docs regenerations LAST, after B's files exist. C's four
  command files and both reference files have no such dependency and land
  first.

No two writers touch a shared file at any point, so no worktree isolation is
needed beyond the ordinary one-branch discipline.

---

## 20. Build order

Each step ends with a runnable check. Do not start a step until the previous
check passes.

1. **RED first.** Write every new class of section 17 against the untouched
   tree. Add the watchdog line to hooks.json with NO gate in a stub
   bm_lead.py, so tools/test_bm_consent.py:471 reproduces the pre-consent write
   the founder decision names. Capture everything to
   `docs/program/absolute-lead/evidence/L04/RED-L04-tests.txt`. Check: every
   new class appears there with at least one failure or error, and 471 is
   among them.
2. **Store, schema.** `SCHEMA_VERSION`, the two DDL constants, the table
   tuples, `_migrate_15_to_16`, `_MIGRATIONS`, `_ensure_schema`,
   `_ensure_indexes`, `_DUMP_SAFE_COLUMNS`. Check:
   `TestSchema16IsAdditive` green.
3. **Store, write paths.** `record_insight`, `record_briefing` and all sixteen
   refusals. Check: `TestRecordInsightRefusals` and
   `TestKeyDecisionCannotSkipTheHandback` green.
4. **Store, reads and purge.** The six accessors, `active_minutes_since`, the
   `ReadOnlyStore` pass-throughs, the purge deletes, the pinned dict. Check:
   `python3 test_bm_store.py` and `python3 test_bm_project.py` fully green.
5. **Store, the replay verdict.** `TestControllerEventsReplayFromAttribution`.
   Check: it runs, and its verdict is written into
   docs/KNOWN-LIMITS.md's L04 section either way (section 14 item 4).
6. **Lead, the door.** `main`, `COMMANDS`, `_consent_state`,
   `_store_or_refuse`, the plumbing copied from bm_project.py, the hooks.json
   line, pyproject.toml, the CI step, `SUITES`. Check:
   `TestConsentIsTheOnlyDoor` green and tools/test_bm_consent.py:471 back to
   green.
7. **Lead, the renderers.** `evidence_label`, `render_claim_line`,
   `render_forecast_lines`, `RUN_STATE_PLAIN` and its guard,
   `render_decision_card`, `render_status`, `render_briefing`. Check:
   `TestReasonedIsNeverBare`, `TestEveryKeyDecisionCardEndsInTheHandbackOption`,
   `TestRunStatePlainCoversEveryState` green.
8. **Lead, the collectors and the router.** `collect_status`,
   `collect_briefing`, `next_action`, `key_decision_class`, then `cmd_outcome`,
   `cmd_status`, `cmd_decisions`, `cmd_insight`. Check:
   `TestTheEightFieldsAreComputedNotNarrated`, `TestExactlyOneNextAction`,
   `TestRangesNeverPoints`, `TestPlainLanguageHoldsInFounderMode`,
   `TestICModeAndFounderModeShareOneCollector` green.
9. **Lead, the clock and the watchdog.** `briefing_due`, `_emit_briefing`,
   `cmd_brief`, `cmd_watchdog`. Check: `TestTheActiveWorkClock`,
   `TestBriefingDue`, `TestOneBriefingPerDueWindow`,
   `TestQuietStretchWritesNothing` green.
10. **Lead, the handback.** `cmd_handback` and `render_developer_brief`.
    Check: `TestHandbackTakesFiveActsInOrder`,
    `TestHandbackIsIdempotentlyRefused`, `TestTheDeveloperBriefIsComplete`
    green.
11. **Lead, the pack.** `PACK_PAGES`, `render_pack_page`, `write_pack`,
    `cmd_handover_pack`. Check: `TestHandoverPackTracesToRows` green, both
    directions.
12. **Lead, the fixtures.** All seven shapes, writing their artifacts. Check:
    `TestSevenConversationShapes` green and seven files exist under
    docs/program/absolute-lead/evidence/L04/.
13. **Register and disclosure.** Writer C's whole set, with
    capabilities.status.json and the two bm-docs regenerations last (gate 2).
    Check: `python3 tools/test_bm_docs.py` green.
14. **The whole gate.** The eight commands of section 17.5, in order, all
    green, no count lower than before.
15. **Hostile re-read.** `git status`, `git diff --stat`, then re-read every
    hunk for leftover debug prints, half-applied renames, and any TODO, stub or
    placeholder. Confirm no em or en dash entered any file. Confirm
    `CONTROLLER_STATE_TRANSITIONS` and `AUTONOMY_FLOORS` are byte-identical to
    their pre-change state.

---

## OPEN QUESTIONS

None.

Every requirement in the brief is resolved above with a stated mechanic. The
five founder decisions are implemented rather than reinterpreted: the watchdog
ships on by default (section 8.1) and cannot write before consent by
construction rather than by discipline (8.4); the handback is present on every
key decision because a key decision that omits it cannot be recorded (6.2 R7);
and REASONED is prefixed by the renderer rather than by the author (4.4).

The two decisions this design took on its own initiative are stated as
decisions, with their reasons, so the orchestrator can reverse either without
reading the rest: the controller event ledger is deferred and the test that
decides it lands instead (section 14), and the founder-facing eight-field view
becomes computed rather than model-narrated (section 3.2). Neither is a
question, because both have a stated default and a stated cost.

The five findings this design does not close are recorded in section 16 with
their reasons and their disclosure destination, not left as questions. Section
18.8 records that no existing assertion is weakened; the two migrations that
change test bodies, 18.1 and 18.2, are the shipped guard mechanisms doing
exactly what their own comments say they exist to do.
