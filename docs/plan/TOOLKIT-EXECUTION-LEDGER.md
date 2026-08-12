# Toolkit execution ledger: every dispatch, its tier, its budget, its result

Status: CURRENT. Opened 2026-08-12 on the founder's directive to execute with
the right subagents and models, each task carrying a clear budget and result
tracking.

This file is the accountability half of the Toolkit program. The plan says
what to build; this says who built each piece, on which model tier, against
what budget, and whether the result was verified independently. One row per
dispatch, filled in when the dispatch returns, never before.

## The rules this ledger enforces

1. **Every dispatch declares its tier and its reason, in the brief itself.**
   An unstated tier is a violation, never a default. The tier appears in the
   first line of every brief and is copied here verbatim.
2. **Every dispatch declares a token ceiling before it starts.** Actual spend
   is recorded from the harness's own usage report, never estimated. Where a
   real number does not exist the cell reads "not measured".
3. **The orchestrator verifies, not the builder.** A returned delta is not
   landed until its own done-check has been re-run in the main tree by the
   orchestrator, and, where the change has a failure mode worth attacking, a
   hostile fixture the orchestrator wrote itself has been tried against it.
4. **Forecast and actual are both recorded**, through
   `tools/bm_forecast.py`, so the calibration sample keeps growing. Toolkit
   work is forecast RAW, with no fast multiplier applied, because it is new
   subsystem work and the one task that met unforeseen ground on 12 August
   ran slower than judged.

## Tier policy for this program

| Work class | Tier | Reason |
|---|---|---|
| Mechanical parsing from a verified spec, additive schema mirroring a proven pattern, registry sweeps | sonnet | The shape is decided before dispatch; the orchestrator re-runs every done-check |
| Architecture, adversarial review, judging a design, synthesis | opus (session default) | Judgement that cannot be checked mechanically |
| Bulk rename or format sweeps, if any arise | haiku | Deterministic and cheap to verify |

The orchestrator runs on the session model and does the verification itself.
No cheap-lane model ever verifies its own work or another agent's.

## Dispatch ledger

| # | Task | Tier | Budget | Actual spend | Forecast | Actual time | Verified by | Result |
|---|---|---|---|---|---|---|---|---|
| 1 | TK1 inventory: `tools/bm_toolkit.py` inventory and json verbs over plugins, skills, hooks, MCP servers, settings layers | sonnet, worktree | 80k out | **150k, 88% OVER** | 150 min raw, upper 240 | 6 min agent, ~25 min including orchestrator verification | orchestrator re-ran the suite, both verbs on the real machine, and three hostile fixtures | LANDED, GREEN, PUSHED |
| 2 | TK5a receipts: nine-field `capability_receipts` table plus criterion-linked evidence, schema 19 to 20 | sonnet, worktree | 90k out | **278k, 208% OVER** | 180 min raw, upper 300 | 19 min agent, ~35 min including orchestrator verification | orchestrator re-ran both suites and wrote four refusal probes | LANDED, GREEN, PUSHED |
| 3 | TK2 data: `tools/toolkit_conflict_classes.json`, ten classes with founder-editable severities | orchestrator, no dispatch | n/a | n/a | 20 min | 14 min | structure validated by command; no reader exists yet | WRITTEN, NOT CLOSED |

### Dispatch 3, why it was not delegated

Ten conflict classes, each carrying a real fixture measured from this
machine's own plugin cache at the moment of writing. It was not delegated
because the value is entirely in the judgement of what counts as a conflict
and how severe it is, and because the fixtures had to be re-measured rather
than recalled. A dispatch would have spent a budget to produce something the
orchestrator would have had to re-derive anyway to trust it. Recorded here so
the absence of a dispatch is a decision rather than a gap.

Measured at write time, by walking the plugin cache and the settings layers:

    Stop            7 distinct plugins
    PreToolUse      8 registrations from 7 distinct plugins, plus 2 settings commands, 10 layers total
    SessionStart   12 registrations
    multi-version   brothersbe cached at 1.0.0-rc.1 AND 1.0.0-rc.38

The PreToolUse decomposition is the interesting one: eight registrations from
seven plugins, because one plugin is cached twice. That discrepancy is itself
a finding, and it is why the class reports registrations and distinct plugins
as two different numbers rather than one.

**Why the status reads WRITTEN, NOT CLOSED.** The first draft of this row
said otherwise, and a drift check was right to challenge it. What a command
actually proved is this much and no more: the file parses as JSON, carries
ten classes, every class has all six required keys, six carry a measured
fixture, and it contains zero em or en dashes.

What no command has proved, and what a stronger word would have implied:
nothing can consume the file, because `tools/bm_toolkit.py` does not exist
yet; no test loads it; it is not committed, not in `CHECKSUMS.sha256`, and
not in the gate. A registry written before its reader exists is the PO-6
discipline running backwards, and it is tolerable here only because the
reader's brief is already written and the shape is fixed. The row closes when
TK2 consumes this file and its suite proves at least one class fires against
a fixture.

The severities are a judgement and cannot be falsified until real findings
exist. Their flip condition: a class that never fires in a month was written
for a conflict nobody has, and should be deleted rather than defended.

## Why these two ran in parallel and nothing else did

The FINISH FIRST law caps parallel work at two lanes, one loop each. These
two qualify because their file sets are disjoint: TK1 creates two new files
under `tools/`, TK5a edits the store, the schema, the store suite and the
spec document. No file appears in both fences, so the one-writer rule holds
without either agent waiting.

TK2, conflict detection, is NOT in this wave even though it is the
differentiator, because it edits `tools/bm_toolkit.py`, the same file TK1
creates. Running it now would put two writers on one file, which is the exact
failure the fence law exists to prevent. It opens the moment TK1 lands.

## Verification record

Filled in as each delta lands. A row here means the orchestrator ran the
command in the main tree after copying the delta, not that the builder
reported it.

### TK1, verified 2026-08-12

Re-run by the orchestrator in the main tree, not accepted from the report:

    $ python3 tools/test_bm_toolkit.py
    Ran 17 tests in 0.641s
    OK

    $ python3 tools/bm_toolkit.py inventory
    SUMMARY: 8 marketplaces, 69 plugins (8 not enabled), 37 skills,
             12 mcp servers, 0 unreadable surfaces.

Three hostile fixtures written by the orchestrator, none of them from the
builder's own suite:

1. One plugin at two version directories, with the two DIFFERENT hooks.json
   shapes (a nested `{"hooks": {...}}` and a flat event map). Result: two
   records, both shapes parsed, events correct per version.
2. A `.claude.json` that is not JSON at all. Result: zero MCP servers AND the
   file named in `unreadable`. It did not silently become an empty answer,
   which was the specific thing worth attacking.
3. The false-versus-null distinction, both directions. Settings unreadable
   gives `enabled: null` for every plugin (could not tell). Settings readable
   with the plugin absent from the map gives `enabled: false` (a fact).
   Conflating those is how a conflict report becomes confidently wrong, so it
   was tested from both sides rather than one.

Purity checked by measurement, not by reading the docstring: running both
verbs changed zero files under `~/.claude`.

### The budget finding, which is the important one

TK1 was dispatched with an 80k output ceiling and spent 150k, 88% over. It
was not stopped, because **the ceiling was a sentence in a brief and nothing
enforced it.** That is precisely the failure class this project already has a
law about: a rule is not a control unless a file enforces it. The brief said
"if you approach it, stop and report", which relies on an agent's own
accounting of a number it cannot see.

Recorded rather than smoothed over. Two honest options for the next dispatch,
neither taken yet because the choice is the founder's: state ceilings as
guidance and stop calling them budgets, or narrow the briefs so the work
cannot expand (this one asked for eight surfaces, an exact JSON schema and
eleven tests in one dispatch, which is three loops of work wearing one name).
The second is the more likely real cause.


### TK5a, verified 2026-08-12

Both suites re-run by the orchestrator in the main tree:

    $ python3 tools/test_bm_store.py
    Ran 1075 tests in 40.271s     (1047 before, so +28 on this loop)
    OK
    $ python3 tools/test_bm_schema.py
    Ran 20 tests in 0.001s
    OK

Four refusal probes written by the orchestrator against a real store, because
the honesty property of a receipt is what it REFUSES, not what it stores:

    invented verification_state "passed"   refused (OwnershipRefused)
    empty verification_state ""            refused
    missing capability_name                refused
    verification_state "no_data"           ACCEPTED as a first-class value
    all nine receipt fields present on read: True

The fourth is the one that matters. A capability that returned prose with
nothing runnable has to be recordable, or the schema would quietly push every
unverifiable step toward a state that overclaims.

**Disclosed gap, filed rather than fixed.** The builder reported that
`purge_project` does not delete `capability_receipts` rows, so purging a
project leaves orphaned receipts. It deliberately left that alone: that method
has exact-dict-shape tests and dry-run semantics, and widening it inside a
scoped schema change was the wrong risk. Queued as TK10 with a failing-first
test required. Recorded here because a gap somebody disclosed is worth more
than a gap somebody fixed quietly and got wrong.

## The budget finding, now with two data points

| Dispatch | Ceiling | Spent | Over by |
|---|---|---|---|
| TK1 inventory | 80k | 150k | 88 percent |
| TK5a receipts | 90k | 278k | 208 percent |

Both dispatches blew their stated ceiling and neither was stopped, because
**nothing enforces a ceiling written in a brief.** This project already has
the law: a rule is not a control unless a file enforces it and a command
proves it fired. The ledger's own rule 2, "every dispatch declares a token
ceiling before it starts", is therefore currently a stated discipline and is
labelled UNENFORCED here rather than left to read as a control.

The second data point changes the diagnosis. TK5a was the larger overrun and
also the broadest brief: a new table with fourteen columns, a migration, two
service methods, an extension to an existing accessor, redaction
classification, and a proven old-database migration test, all in one dispatch.
TK1 was the same shape of mistake at smaller scale: eight surfaces, an exact
JSON schema and eleven required tests. The pattern in both is scope, not
appetite. A brief that contains three loops of work will spend three loops of
budget however small a number is written at the top of it.

What changes for the next dispatch, and it is a scope rule rather than a
number: one table OR one command surface OR one registry sweep per dispatch,
never a set of them joined by "plus". The ceiling stays in the brief as
guidance, honestly labelled as guidance.

## Wave 1 closed, 2026-08-12

    $ python3 tools/test_all.py --artifacts "$TMPDIR/gate-artifacts"
    test_all: 3130 tests across 35 suites, 5 skipped, 748.1s wall. ALL GREEN

Exit 0 at e0341cb, tree clean, pushed and verified three ways. Doctor 11 of 11.

Three gate runs were needed and all three red verdicts were real:

1. An apostrophe inside a SUITES comment whose own text reads NO APOSTROPHE
   ANYWHERE IN THIS COMMENT, ON PURPOSE. The fact loader parses quoted spans
   with a plain quote-to-quote regex, so it swallowed real suite names. I had
   copied the warning and violated it in the same comment.
2. Three new refusal reason codes with no founder-facing rewrite. The visual
   surface refuses that by law, and it was right to: the exact refusals probed
   an hour earlier would have reached a person as raw machine codes.
3. Doctor check 7 red because the live store was a schema behind the code.
   NOT a defect: doctor is read-only, so it refuses and explains rather than
   migrating behind the founder. Recorded as decision 35 rather than patched.

Two of the three were mine, not the builders'.

## What wave 2 changes, from what wave 1 measured

The scope rule, replacing the ceiling that enforced nothing: one table OR one
command surface OR one registry sweep per dispatch, never a set joined by
"plus". Both wave-1 briefs broke that and both blew their budget in
proportion to how badly.

Next dispatch is TK2, conflict detection, and it is deliberately ONE thing:
read the inventory json and the conflict-classes file, emit verdicts. Its
severity data and its fixtures already exist, which is most of what made the
wave-1 briefs sprawl.