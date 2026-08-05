Status: CURRENT. Writer B (the lead surface), L04. 2026-08-05.

# FIX L04: the lead surface. Founder mode, IC mode, the watchdog, the handback

Scope: DESIGN-L04.md sections 3, 4, 7, 8, 9, 10, 11, 12, 15.2, 17.1, 17.2,
17.4's consent half, 18.2, 18.4 and 18.5.

Files written, and only these:

* `tools/bm_lead.py` (new)
* `tools/test_bm_lead.py` (new, 19 classes, 77 tests)
* `tools/test_bm_consent.py` (one test renamed and widened, two added)
* `tools/test_all.py` (`SUITES` gains one entry)
* `hooks/hooks.json` (the Stop line)
* `pyproject.toml` (one console script, one py-module)
* `.github/workflows/tests.yml` (one step)
* `docs/program/absolute-lead/evidence/L04/RED-L04-lead.txt`
* `docs/program/absolute-lead/evidence/L04/S1..S7-*.json` (the seven fixtures)
* this report

Nothing else was touched. `tools/bm_store.py`, `tools/test_bm_store.py`,
`tools/test_bm_project.py`, `tools/test_bm_docs.py`,
`capabilities.status.json` and everything under `commands/`, `references/`
and `docs/` outside this evidence folder belong to Writers A and C. Each
was read, none was written.

---

## 0. The two things to read first

Bad news first, per `references/honesty.md`.

### 0.1 The done-check on `tools/test_bm.py` is NOT DONE, for two reasons, and neither file is mine

`python3 tools/test_bm.py` exits 1 with exactly two failures. One of them
existed before I made any edit; the other is a guard doing its job against
a file no writer in section 19 owns. Both remedies are one line each and
both are written out below (section 5).

### 0.2 The founder decision is implemented and proven, and it is proven twice

The watchdog ships ON BY DEFAULT on the Stop hook, and nothing writes
before setup consent. That is proven structurally (an ast guard over
`tools/bm_lead.py`) and behaviourally (every subcommand driven as a real
subprocess in a fresh HOME, both trees walked before and after). Section 2
has the proof output. The RED that came first is in `RED-L04-lead.txt`, and
the important half of it is that the SHIPPED test
`test_no_wired_command_of_any_module_writes_before_consent`, which nobody
edited, went red the moment `hooks/hooks.json` named the watchdog.

---

## 1. Per-section table

| Section | What it asks for | State | Where |
|---|---|---|---|
| 3.1 | `tools/bm_lead.py`, a thin CLI, no SQL of its own, none of the ten banned imports | LANDED | `TestNoSQLGuard`; plumbing copied from `tools/bm_project.py` |
| 3.2 | `outcome`, `status`, `decisions` | LANDED | `cmd_outcome`, `cmd_status`, `cmd_decisions` |
| 3.3 | `brief`, `insight`, `handback`, `handover-pack`, `watchdog --tick`, one `COMMANDS` dict | LANDED | `COMMANDS`, eight entries (see the note on "nine" in section 4) |
| 3.4 | the eight fields, each computed or saying it cannot be | LANDED | `collect_status`; `TestTheEightFieldsAreComputedNotNarrated` |
| 3.5 | `--advanced` adds exactly the nine items, per request, never sticky | LANDED | `ADVANCED_ITEMS`, `_advanced_block` |
| 3.6 | exactly one recommended next action, nine branches, first match wins | LANDED | `_next_action_branch`, `next_action`; `TestExactlyOneNextAction`, one test per branch |
| 3.7 | estimates as ranges, one formatting function, no arithmetic on a forecast | LANDED | `render_forecast_lines`, `render_forecast_range`; structural test in `TestRangesNeverPoints` |
| 4.1, 4.2 | IC mode: one collector, two renderers, the extra block | LANDED | `_engineering_block`; `TestICModeAndFounderModeShareOneCollector` |
| 4.3 | `--ic` and `BROTHERMODE_VIEW=ic`, always explicit, footer names the switch | LANDED | `_view_flags`, `IC_FOOTER_FLAG`, `IC_FOOTER_ENV` |
| 4.4 | four calibration labels, REASONED prefixed by the renderer | LANDED | `evidence_label`, `render_claim_text`, `render_claim_line`; `TestReasonedIsNeverBare` |
| 7.1 | the active-work clock | LANDED (store side is Writer A's) | `TestTheActiveWorkClock` drives `active_minutes_since` through `bl.bs` |
| 7.2 | `briefing_due`, ACTIVE_MINUTES then PHASE_BOUNDARY then not due | LANDED | `briefing_due`; `TestBriefingDue` |
| 7.3 | six lines, `RUN_STATE_PLAIN` plus its import-time guard | LANDED | `render_briefing`, `_check_run_state_plain`; `TestRunStatePlainCoversEveryState` |
| 7.4 | three places, one renderer, one row per due window | LANDED | `_emit_briefing` is the only caller of `record_briefing`; `TestOneBriefingPerDueWindow` |
| 7.5 | the quiet stretch writes no row and names the one that stands | LANDED | `_print_standing_briefing`; `TestQuietStretchWritesNothing`, all three cases |
| 8.1, 8.2 | the watchdog is a due-check on the Stop hook, not a daemon; the hook line | LANDED | `hooks/hooks.json` Stop line, two programs, timeout 15 to 30 |
| 8.3 | what a tick does, fail-open at every step | LANDED | `cmd_watchdog` |
| 8.4 mech 1 | ONE DOOR: `_store_or_refuse` is the only store constructor | LANDED | `TestConsentIsTheOnlyDoor` |
| 8.4 mech 2 | `main` computes consent once, before the `COMMANDS` lookup, refuses the whole dispatch | LANDED | `main`; ast assertion on the two line numbers |
| 8.4 mech 3 | the five ast assertions | LANDED, with ONE STATED DEVIATION | section 3 below |
| 8.4 mech 4 | the hook inventory widened from one module to all of them | LANDED | `test_every_hook_wired_command_of_every_module_checks_consent` |
| 9.1 | `HANDBACK_OPTION_TEXT` verbatim, as a module constant | LANDED | byte-equality asserted in three tests |
| 9.2 | `key_decision_class`, four detected and PREFERENCE declared | LANDED | `key_decision_class`; the declared note is emitted by the renderer |
| 9.3 | the option is a store refusal plus a renderer belt | LANDED | `render_decision_card` is the only emitter of `Decision needed:` (ast) |
| 9.4 | five acts, in one fixed order, with the Act 2 trap | LANDED | `cmd_handback`; `TestHandbackTakesFiveActsInOrder`, six tests |
| 9.6 | work in flight is disclosed, never cancelled | LANDED | brief section 7, with ages |
| 10 | the developer brief, eight sections, byte stable from its own cut | LANDED | `render_developer_brief`, `DEVELOPER_BRIEF_SECTIONS` |
| 11.1, 11.2 | seven pages, `PACK_PAGES`, one funnel, no render timestamp, trace tags | LANDED | `write_pack`, `render_pack_page` |
| 11.3 | the docs-truth test, both directions, plus REASONED, byte stability and the cut | LANDED | `TestHandoverPackTracesToRows`, six tests |
| 12 | the seven conversation shapes, each writing its artifact | LANDED | `TestSevenConversationShapes`; `S1..S7-*.json` |
| 15.2 | every symbol of the inventory table | LANDED | with two named additions: `_next_action_branch` and `render_claim_text` (section 4) |
| 17.1, 17.2 | every named class, written FIRST and RED first | LANDED | `RED-L04-lead.txt`, per-class counts |
| 17.4 consent half | 471 goes red then green; 569 renamed and widened | LANDED | section 2 |
| 18.2 | the rename and the widening | LANDED | section 3 below |
| 18.4 | `SUITES` gains the suite, and the CI step lands with it | LANDED | `tools/test_all.py`, `.github/workflows/tests.yml` |
| 18.5 | the py-modules contract | LANDED | `pyproject.toml`, both lists |
| (unnamed) | `tools/write_sites.json` needs an entry for the new module | **BLOCKED** | section 5, BLOCKED-1 |
| (unnamed) | `tools/test_bm.py`'s pinned command set | **BLOCKED**, pre-existing | section 5, BLOCKED-2 |

---

## 2. The consent proof

### 2.1 The RED that came first

`RED-L04-lead.txt` block 2, verbatim in that file. The important line:

```
FAIL: test_no_wired_command_of_any_module_writes_before_consent
AssertionError: 2 != 0 : Stop: sh -c '... | python3 ".../tools/bm_lead.py" watchdog --tick' exited 2
```

That test is SHIPPED and was not edited. It went red the moment
`hooks/hooks.json` named the watchdog, which is the failing-first evidence
DESIGN-L04 section 8.4 asks for.

### 2.2 The zero-files proof, run after the last edit

Every subcommand, a fresh HOME with no consent record, a fresh empty
project root, both trees walked before and after:

```
HOME files before: 0
project files before: 0
outcome          exit=1 HOME_files=0 project_files=0 stdout=bm_lead: setup is not complete yet; run: python3 scripts/setup.py
status           exit=1 HOME_files=0 project_files=0 stdout=bm_lead: setup is not complete yet; run: python3 scripts/setup.py
decisions        exit=1 HOME_files=0 project_files=0 stdout=bm_lead: setup is not complete yet; run: python3 scripts/setup.py
brief            exit=1 HOME_files=0 project_files=0 stdout=bm_lead: setup is not complete yet; run: python3 scripts/setup.py
insight          exit=1 HOME_files=0 project_files=0 stdout=bm_lead: setup is not complete yet; run: python3 scripts/setup.py
handback         exit=1 HOME_files=0 project_files=0 stdout=bm_lead: setup is not complete yet; run: python3 scripts/setup.py
handover-pack    exit=1 HOME_files=0 project_files=0 stdout=bm_lead: setup is not complete yet; run: python3 scripts/setup.py
watchdog         exit=0 HOME_files=0 project_files=0 stdout=
outcome --set    exit=1 HOME_files=0 project_files=0 stdout=bm_lead: setup is not complete yet; run: python3 scripts/setup.py
HOME files after: 0
project files after: 0
vault directory exists: no
```

The watchdog exits 0 and prints NOTHING, on stdout and on stderr. Every
human-invoked command prints the shipped sentence and exits 1. The same
nine drives run inside the suite as
`TestConsentIsTheOnlyDoor.test_every_subcommand_in_a_fresh_home_creates_zero_files`,
which asserts the file lists are empty rather than reading a count.

### 2.3 The structural half

`TestConsentIsTheOnlyDoor` parses `tools/bm_lead.py` with `ast` and asserts:

1. `bs.Store(` and `bs.ReadOnlyStore(` appear in exactly one function, and
   it is `_store_or_refuse`. A second store constructor anywhere in the
   file fails this test. The assertion also refuses to pass vacuously: it
   fails first if the file constructs no store at all.
2. No `open(...)` call anywhere has a mode containing `w`, `a` or `x`.
3. `os.replace` and `shutil` appear nowhere.
4. `main()` calls `_consent_state()` at a line number strictly LOWER than
   its `COMMANDS[...]` subscript.
5. `COMMANDS` is read in exactly one function, `main`.

Consent itself is not defined in `bm_lead.py`. `_consent_state` loads
`scripts/setup.py` by path and calls its own `read_config` and
`is_consented`, copying `tools/bm_telemetry.py`'s
`_load_bm_setup` / `_get_bm_setup` / `_consented` in shape. The module
object is cached; the CONFIG is not, because `read_config` consults the
environment on every call.

---

## 3. The one stated deviation, and why it is stated rather than smuggled

DESIGN-L04 section 8.4 mechanism 3 asks the ast guard to assert that
`os.makedirs` appears NOWHERE in `tools/bm_lead.py`. That cannot hold
together with section 11.1, and the conflict is in the shipped code rather
than in my reading of it: `bs.write_generated_document`'s own docstring
says "The directory must exist; this creates nothing", the handover pack is
a generated FOLDER, and the store offers no public directory-creating
helper (grepped: `store_dir`, `safe_project_path` and
`write_generated_document` all create nothing).

What landed instead, and it is the same law one step narrower rather than a
narrower law:

* `os.replace` and `shutil` appear nowhere, exactly as written.
* `os.makedirs` appears in exactly ONE function, `_ensure_pack_dir`, and
  the test additionally asserts that function's FIRST PARAMETER is named
  `store`. So the only directory-creating call in the file is unreachable
  without a handle that `_store_or_refuse` returned, which is precisely the
  reachability argument the design already makes for
  `write_generated_document` in the same sentence.

If the orchestrator prefers the design read strictly, the alternative is to
refuse `handover-pack` when `Handover/` does not already exist, which
trades a real founder-facing failure for a wording match. I did not take
it, and I did not use `os.mkdir` to make the literal word disappear from
the file, because that would be narrowing the guard rather than fixing at
the class.

### 3.1 The widening of the consent inventory (18.2), and why it is a strengthening

`test_every_hook_wired_telemetry_command_checks_consent` became
`test_every_hook_wired_command_of_every_module_checks_consent`. Every
assertion it made about `bm_telemetry.py` survives verbatim, because that
module's commands are a subset of the widened set, and the test asserts
that explicitly (`assertIn("bm_telemetry.py", modules)`) so the widening
cannot silently stop covering what the narrow version covered.

Three additions beyond the design's wording, all stated:

* `CONSENT_EXEMPT_MODULES` encodes `bm_fence_hook.py` WITH its reason, as
  section 18.2 asks. The exemption used to exist only in prose.
* `CONSENT_GATE_BY_MODULE` declares, per module, WHERE the gate lives:
  `per-command` (the four telemetry-era modules) or `one-door`
  (`bm_lead.py`). The one-door branch is checked as a gate, not as a
  mention: `main()` must name the call AND must do so before it subscripts
  its dispatch table. A module wired into `hooks.json` with no entry is
  reported.
* Two new tests: a vacuous-pass calibration (an undeclared module, and a
  gate placed after the lookup, both shown to be reported), and
  `test_every_hook_wired_module_is_classified`, which fails when a new hook
  line names a module nobody has classified.

`MIN_WIRED_PROGRAMS` moved 8 to 9, because the Stop line now runs two
programs like the PreCompact line does. Raising a floor is the only
direction that number is allowed to move, and the stale comment beside it
was corrected in the same edit.

---

## 4. The subcommands, and what a founder sees

DESIGN-L04 says "nine subcommands" and its own two lists enumerate EIGHT
(three in section 3.2, five in section 3.3). I shipped the eight the design
names rather than inventing a ninth. The ninth founder-visible action is
`outcome --set`, which is a different act from a bare `outcome`, and that
is how the count reaches nine in front of a founder. Stated here rather
than silently reconciled.

| Subcommand | One line on what a founder sees |
|---|---|
| `outcome` | Two lines saying where the work stands (the outcome and the progress), then one recommended next action with its why and the exact command. With `--set` it records the outcome first and then prints the same three lines. |
| `status` | Exactly the eight fields, in order, in plain words, each computed from records or saying plainly that it cannot be computed yet. `--advanced` adds the nine machinery items and is dropped again by the next plain status. |
| `decisions` | One card per open decision, highest stakes first: the recommended option with its Why, each alternative with its Tradeoff, and a last option line that is always "Hand this back to me". When nothing is open it says so and gives the standing next step. |
| `brief` | A short catch-up in six lines, ending in the handback option. When nothing has happened it names the catch-up that still stands, with its age, and writes no new record. |
| `insight` | One line confirming what was recorded. With `--report-card` it renders the four-section error card instead, impact before cause, which is how bad news reaches a founder. |
| `handback` | Four plain lines: this is yours now, the authorisation is paused, what I would have chosen is written down, and where to read it. On a failure after the pause it prints the error card and says the authorisation stays paused on purpose. |
| `handover-pack` | A count and a one-line description of each of the seven pages, plus the promise that regenerating them changes nothing unless the records changed. |
| `watchdog --tick` | Nothing at all, in the ordinary case. When a catch-up is due it prints exactly the same six lines `brief` prints. Before setup it prints nothing and writes nothing. |

Two symbols beyond the section 15.2 inventory, both named rather than
slipped in:

* `_next_action_branch(store, project_id) -> (branch_id, text, why, command)`.
  `next_action` is the three-value form the design names and is a thin
  wrapper over it. The branch id exists so a fixture can assert WHICH of
  the nine branches fired instead of guessing from the wording.
* `render_claim_text(insight, ic=False)`, which is `render_claim_line`
  without the trace tag. `references/terminology.md`'s new "trace tag" row
  says the record id is not shown in the default status view, so the
  default view calls this and the handover pages call `render_claim_line`.

---

## 5. BLOCKED, both outside my allowed set

### BLOCKED-1. `tools/write_sites.json` has no entry for the new module

`python3 tools/test_bm.py`, `TestPreWriteGate.test_no_unreviewed_write_sites`:

```
FAIL: test_no_unreviewed_write_sites (__main__.TestPreWriteGate)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_bm.py", line 1330, in test_no_unreviewed_write_sites
    self._assert_matches_manifest(actual, manifest)
  File "/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_bm.py", line 1314, in _assert_matches_manifest
    self.assertIn(key, manifest,
AssertionError: 'tools/bm_lead.py' not found in {'tools/bm_autosave.py': 19, ...,
'tools/bm_autonomy.py': 2, 'tools/bm_controller.py': 2} : tools/bm_lead.py writes
files but is not in the reviewed inventory. Review whether every text it writes
passes through redaction, then add it to tools/write_sites.json.
```

This is the third of the three guards the brief predicted, and it is the
guard doing its job. It is UNAVOIDABLE for any new module under `tools/`:
the scanner's `\.write\(` pattern matches `sys.stdout.write` and
`sys.stderr.write`, so `_out` and `_err` alone put a file on the list.
`tools/bm_autonomy.py` and `tools/bm_controller.py` carry exactly 2 for the
same two lines.

The three sites in `tools/bm_lead.py`, listed so the review the test asks
for is on the record:

```
line  155  sys.stdout.write("%s\n" % msg)      # _out, terminal only
line  159  sys.stderr.write("%s\n" % msg)      # _err, terminal only
line 1163  os.makedirs(path)                   # _ensure_pack_dir, section 3
```

Redaction review, which is what the test is actually asking for: every FILE
this module writes goes through `bs.write_generated_document`, the one
funnel, which runs the redactor over the whole text and refuses to write at
all when the redactor is unavailable. There is no second write path: the
ast guard in `TestConsentIsTheOnlyDoor` asserts no `open(..., "w")` and no
`os.replace` anywhere in the file. The two `.write(` hits are the terminal,
not a file.

PROPOSED MINIMAL REMEDY, one line in `tools/write_sites.json`, beside the
`tools/bm_controller.py` entry:

```json
    "tools/bm_lead.py": 3,
```

I did not apply it: `tools/write_sites.json` is not in my allowed set, and
DESIGN-L04 section 19 assigns it to no writer at all (it appears in the
design's authorised file list at line 18 with the note "only if the audit
log requires it", which is now true).

### BLOCKED-2. `tools/test_bm.py:5680` `test_exactly_seven_brotherme_commands_ship`

PRE-EXISTING. This was already red before I made any edit, and Writer C
reported it in their section 0.2: the four new command files under
`commands/` turn the pinned command set red. It is repeated here only so
whoever runs the gate does not read it as mine.

```
FAIL: test_exactly_seven_brotherme_commands_ship (__main__.TestTheSeventhCommandAndTheDeepTourAreWired)
AssertionError: ... the shipped command set drifted from the ten this release
documents (seven beginner plus three controller)
```

Remedy: four names added to the pinned list, keeping exact equality over
the whole set. `tools/test_bm.py` is in no writer's allowed set.

---

## 6. DONE-CHECK, verbatim, all run after the last edit

```
$ cd /Users/khalil.maaouni/Documents/BrotherModeUp/tools && python3 test_bm_lead.py
.............................................................................
----------------------------------------------------------------------
Ran 77 tests in 47.345s

OK
LEAD EXIT: 0
```

```
$ cd /Users/khalil.maaouni/Documents/BrotherModeUp/tools && python3 test_bm_consent.py
..........................................
----------------------------------------------------------------------
Ran 42 tests in 34.030s

OK
CONSENT EXIT: 0
```

40 tests before, 42 after: one test was renamed and widened in place, and
two were added. No test was removed, skipped or silenced.

```
$ cd /Users/khalil.maaouni/Documents/BrotherModeUp && python3 tools/test_bm.py
FAIL: test_no_unreviewed_write_sites (__main__.TestPreWriteGate)
FAIL: test_exactly_seven_brotherme_commands_ship (__main__.TestTheSeventhCommandAndTheDeepTourAreWired)
Ran 276 tests in 117.521s
FAILED (failures=2, skipped=1)
```

**NOT DONE on this one**, and the two failures are exactly BLOCKED-1 and
BLOCKED-2 and nothing else. 276 before, 276 after: no test in that suite
was added or removed.

The zero-files-before-consent proof output is section 2.2 above.

The copy rule, swept after the last edit over every file I wrote:

```
files checked: 15
em or en dash offenders: []
```

The seven fixture artifacts exist and are regenerated on every run of the
suite, by design, the same way `E4-endtoend.json` is:

```
S1-COLD_START.json        S2-STATUS_MID_RUN.json   S3-DECISION_REQUIRED.json
S4-HANDBACK_TAKEN.json    S5-HANDBACK_REFUSED.json S6-QUIET_STRETCH.json
S7-BAD_NEWS.json
```

Not run, deliberately, because the brief forbade it: `tools/test_all.py`,
the store suite and the controller suite. The orchestrator runs the gate.

---

## 7. Three decisions taken inside the implementation, each with its reason

Named because a decision nobody records is a decision nobody can reverse.

1. **Act 3 parks the work record under the RECORD'S OWN owning session,
   not the session that typed the command.** The store's ownership guard
   refuses a move on an ACTIVE record from any other session, which is
   right: it stops a second live writer stealing work. A handback is not
   that. It is the founder stopping the work and releasing it, and a
   founder types it from a fresh terminal every time. The alternative the
   store offers is adoption with `adopt_from_live_session=True`, which is a
   takeover dressed up as a handback. Nothing is stolen: the authorisation
   was already paused in Act 1, so no further work can run, and the
   transition note records who actually asked. Reproduced first as a
   failing test, which is how it was found.

2. **`handover-pack` opens a WRITABLE handle.** It writes seven pages into
   the project, so "read only" was never true of it, and one of those pages
   renders the developer brief, which reads the work record's handover
   payload. That read lives on `Store` and not on `ReadOnlyStore`. With a
   read-only handle the pack's copy of that page silently lost three
   sections while the standalone copy kept them, which the
   same-bytes test caught. The `except` around that read was also narrowed
   from bare `Exception` to `bs.BMStoreError` in the same fix: a store
   refusal is a fact about the records and belongs on the page, an
   `AttributeError` is a fact about this file and must be loud.

3. **Branch 1 of the next-action router keys on the decision CLASS, not on
   words in the decision's prose.** The first version matched floor ids
   inside the subject and claim, and a test caught it: "the payment
   approach" contains the floor id "payment", so an ordinary pricing
   decision was reported to the founder as a safety floor. `GATE` is the
   class `key_decision_class` returns for exactly the floor case and
   `DECISION_STAKES` sorts it first, so the class is the honest signal.

---

## 8. What I did NOT verify, and what is unverified in what I did

Stated plainly rather than left to be inferred.

1. **`tools/test_all.py`, the store suite and the controller suite were not
   run**, per the brief. `SUITES` gained an entry and the CI workflow gained
   the matching step, and `tools/test_all.py:49` enforces that inventory in
   both directions, but I did not execute the gate that checks it.
2. **`tools/test_bm_docs.py` was not run.** Writer C's done-check covers it
   and reported it red for an unrelated reason (a bare repository slug in
   prose in three untracked pages).
3. **The packaged install path is unexercised.** `tools/bm_lead.py` finds
   `scripts/setup.py` at `os.path.dirname(os.path.dirname(__file__))`,
   copied verbatim from `tools/bm_telemetry.py`. In a pip or pipx install
   the flat modules land in site-packages and that path does not exist, so
   `_consent_state()` fails CLOSED and the installed `bm-lead` prints the
   setup sentence and exits 1. That is the same behaviour
   `tools/bm_telemetry.py` already has and it is not a regression this
   change introduces, but `tools/test_bm_packaging_install.py` (not run by
   me; it only checks for a traceback on stderr) will see that exit code.
   Worth a later loop; not closed here.
4. **The developer brief's cut is not total.** Every insight and briefing
   the brief renders is filtered by `created_at <= the handback's own
   timestamp`, and dispatch ages are measured against that same cut, so the
   test that inserts a later record and regenerates gets identical bytes.
   The CHECKPOINT it quotes is the LATEST digest for that work record,
   because the store offers no digest-at-a-cut read. A checkpoint written
   after a handback would therefore change an older brief. No path in this
   loop writes one, and closing it properly means a store accessor, which
   is Writer A's file.
5. **The "no bare hours or days outside `render_forecast_lines`" structural
   test exempts a second function, `_elapsed`, with its reason in the test's
   own docstring.** `_elapsed` renders a MEASURED age between two recorded
   timestamps and reads no forecast; `references/forecasting.md`'s law is
   about estimates. That exemption is stated in the test rather than
   assumed, and `_elapsed`'s two parameters are both timestamps.
6. **`TestRangesNeverPoints`'s structural half currently passes trivially**,
   because no format string in the module names a duration unit at all
   (every duration comes out of a forecast row). It is a guard against
   future drift rather than a reproduction of a defect, and it is labelled
   as one here rather than counted as evidence.
7. **The seven fixture artifacts are regenerated on every run**, so they
   show as modified after any run of the suite. Every value in them is read
   back out of the live records the test just drove, which is what makes
   them evidence rather than golden files.
