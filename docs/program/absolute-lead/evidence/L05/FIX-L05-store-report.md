# FIX-L05 store report, Writer D: the store and the vocabulary

Design: docs/program/absolute-lead/DESIGN-visual-surface.md, sections 6, 7,
9.2, 11, 12.1, 13.1 and 13.3 (the section 16 "Writer D" set).
Date: 2026-08-05. Tree: /Users/khalil.maaouni/Documents/BrotherModeUp.

Files this writer changed, and nothing else:

    tools/bm_store.py            schema 17, the views table, six refusals
    tools/test_bm_store.py       five new classes, one exempt entry, one pin
    tools/test_bm_project.py     the pinned purge dict only
    tools/bm_visual.py           NEW, 2399 lines, the vocabulary
    tools/test_bm_visual.py      NEW, 45 tests in 11 classes
    docs/program/absolute-lead/evidence/L05/RED-D.txt
    docs/program/absolute-lead/evidence/L05/FIX-L05-store-report.md

---

## SIGNATURES (gate 2, D to E)

Everything below is copied from the landed code, not from the design. Where
the landed shape differs from the design's own wording, the difference is
stated in this section and again in section "Deviations, with the reason".

`tools/bm_visual.py` is a LIBRARY: no main, no CLI, no store constructor of
its own, no file write, no print. Import it the way every other tool imports
a sibling:

    bv = _load("bm_visual")     # spec_from_file_location off tools/
    bv.bs                       # the bm_store module bm_visual loaded
    bv.bl                       # the bm_lead module bm_visual loaded

Use `bv.bs` and `bv.bl` when a refusal this module can raise must be caught
by the same class object, exactly as tools/test_bm_lead.py documents.

### The one reader, and the five builders

    def visual_facts(store, project_id, now=None):

Returns a dict. This is the ONLY function here that reads the store for the
drawings, and every builder below is pure over its result.

    {
      "project_id":   str,
      "goal":         str, the founder's own outcome sentence, or ""
      "run_state":    str, the controller run state, or "" when no run
      "run_sentence": str, that state in plain words (bl.RUN_STATE_PLAIN)
      "stage":        str, one of PIPELINE_STAGES, the one that is NOW
      "units":        [{"unit_id", "label", "status", "lane"}]
      "gates":        [{"name", "status", "detail"}]
      "gates_total":  int,
      "gates_passed": int,
      "owners":       [{"owner": str, "items": [{"label", "status"}]}]
      "decision":     the highest stakes open key decision ROW, or None
      "counts":       [{"label", "value", "limit", "sentence"}]
      "spend":        store.spend_totals(project_id), unchanged
      "newest_at":    str, the newest row timestamp read, or ""
    }

`newest_at` is what the page's "Built from records up to ..." line should
print. It is a property of the rows, never of the clock.

    def diagram_pipeline(facts):   -> Diagram          (never None)
    def diagram_gates(facts):      -> Diagram or None  (None: no gates yet)
    def diagram_lanes(facts):      -> Diagram or None  (None: one owner)
    def diagram_fork(facts):       -> Diagram or None  (None: no open key
                                                        decision)
    def counts_rows(facts):        -> Diagram          (never None)

A None means "there is nothing to draw here"; the page renders its designed
empty state for that section instead. `diagram_lanes` returns None whenever
fewer than two owners hold an open item, which is the design's own rule that
a lane map is drawn only when ownership is the important question.

### The diagram model

    def Diagram(shape, nodes, edges, title, desc, caption):
    diagram = Diagram          # both names, one function

Returns a plain dict:

    {"shape": str, "nodes": [node], "edges": [edge],
     "title": str, "desc": str, "caption": str}

    def node(node_id, label, status, token="", detail="", lane=""):
      -> {"id", "label", "status", "token", "detail", "lane"}
      counts_rows additionally sets "value" (int or None) and
      "limit" (int or None) on its nodes.

    def edge(src, dst, label=""):   -> {"from", "to", "label"}

Diagram raises ValueError for: a shape outside SHAPES; a node whose status
is outside STATUS_LEXICON; a node whose label does not CONTAIN its own
status word; any cap in CAPS exceeded (outcomes checked before nodes on a
fork); an edge naming a node that is not in the drawing.

    SHAPES = ("pipeline", "gates", "lanes", "fork", "counts")
    CAPS = {"pipeline": {"nodes": 7, "edges": 6, "lanes": 0, "outcomes": 0},
            "gates":    {"nodes": 9, "edges": 8, "lanes": 0, "outcomes": 0},
            "lanes":    {"nodes": 9, "edges": 12, "lanes": 4, "outcomes": 0},
            "fork":     {"nodes": 4, "edges": 3, "lanes": 0, "outcomes": 3},
            "counts":   {"nodes": 6, "edges": 0, "lanes": 0, "outcomes": 0}}
    STATUS_LEXICON = ("NOW", "complete", "waiting", "passed", "failing",
                      "not run", "BLOCKED", "working", "open", "chosen",
                      "counted", "NEEDS YOU", "AT RISK", "FOR INFO",
                      "SETTLED")
    PIPELINE_STAGES = ("Set up", "Understand", "Plan", "Build", "Check",
                       "Deliver")

    def diagram_for(question):   -> one of SHAPES, or "" for anything else

### The two emitters

    def to_svg(diagram):   -> str

One COMPLETE `<figure class="bm-figure">` element containing an
`<svg role="img" viewBox=... aria-labelledby=... aria-describedby=...>` with
a `<title>` and a `<desc>`, followed by a `<figcaption>`. E embeds this
string as-is; do not wrap it in a second figure. It carries NO colour
attribute of any kind (no fill=, stroke=, style=, and no "#" at all): every
colour is a class defined in THEME_CSS. No xmlns is emitted, because it is
inline SVG inside an HTML document.

The `counts` shape emits, per row that has a limit, a
`<g role="progressbar" aria-valuemin aria-valuemax aria-valuenow
aria-valuetext="4 of 7 gates passed">`. That is why there is no separate
HTML-bars function: the progressbar semantics are already in the figure.
Counts is not one of the four drawings the per-page cap counts.

    def to_text(diagram):   -> str

The terminal form: title, body, caption. ASCII only, guaranteed by an
encode-with-backslashreplace pass, so a Windows console cannot produce
mojibake.

### The insight box

    INSIGHT_SLOTS = ("CLAIM", "BECAUSE", "INSTEAD OF", "CHANGES IF",
                     "CONFIDENCE", "YOUR MOVE")

    def insight_box_slots(insight, ic=False):
      -> ((label, value), ...) exactly six pairs, in INSIGHT_SLOTS order

    def render_insight_box(insight, medium, ic=False):   -> str
      medium "text": a multi line ASCII block
      medium "html": one <section class="bm-insight"> element

`insight` is an insights ROW as the store returns it (raw=True), i.e. it
needs claim, evidence, evidence_class, alternatives, flip_condition,
confidence, confidence_basis, subject, kind. `ic=True` appends the trace tag
`[i:<insight_id>]` to the CLAIM slot.

Slot 6 is `bl.HANDBACK_OPTION_TEXT`, byte equal, always last.
A REASONED row renders the label "my reasoning, not verified:", the class
token, the literal words "not tested", and NO rung bar in either medium
(`RUNG_BAR_CLASS = "bm-rung-bar"` is absent from the html; no RUNG_MARKS
value appears in the text).

### The alert ladder

    RUNGS = ("NEEDS YOU", "AT RISK", "FOR INFO", "SETTLED")
    RUNG_DELIVERY = {"NEEDS YOU": ("interrupt", "alert", 1),
                     "AT RISK":   ("polite", "status", 3),
                     "FOR INFO":  ("silent", "", 6),
                     "SETTLED":   ("silent", "", None)}
    RUNG_MARKS = {"NEEDS YOU": "[!!]", "AT RISK": "[! ]",
                  "FOR INFO": "[ i]", "SETTLED": "[  ]"}
    RUNG_TOKEN = {"NEEDS YOU": "needs-you", "AT RISK": "at-risk",
                  "FOR INFO": "for-info", "SETTLED": ""}
    ALERT_KINDS, RUNG_FOR_KIND      closed sets, guarded at import
    ALERT_FIELDS = ("rung", "kind", "subject", "row_id", "message",
                    "action", "at", "more", "repeats")
    STALE_DISPATCH_SECONDS = 1800

    def alert(rung, kind, subject, row_id, message, action="", at=""):
      -> a dict with exactly ALERT_FIELDS

    def alerts_now(store, project_id, now=None, consented=True):
      -> [alert], ordered by rung then by kind, deduplicated on
         (rung, kind, subject, row_id), and capped per rung.
         "more" on the last alert of a rung counts what was not shown.
         "repeats" counts collapsed duplicates.

      consented=False returns EXACTLY one NEEDS YOU consent alert and
      touches nothing, so the doorway can call it with store=None.

    def alerts_for_chat(alerts):   -> the subset one chat message may carry
                                      (at most two distinct rungs)

    def render_alert(alert_row, medium):   -> str
      medium "html": <div class="bm-alert bm-needs-you" role="alert">...
      SETTLED carries NO role attribute and no colour class.

### The stylesheet

    THEME_CSS   str, CSS TEXT with no <style> element around it.

E owns the `<style>` tag. The block defines `:root` variables, then a
`@media (prefers-color-scheme: dark)` block, then
`:root[data-theme="light"]` and `:root[data-theme="dark"]` overrides AFTER
the media query so the viewer's toggle wins in both directions. Token names
are `--bm-<token>` for every key of TOKENS_LIGHT / TOKENS_DARK (identical
key sets). Every class the emitters use has a rule here, and
tools/test_bm_visual.py asserts that in both directions.

    TOKENS_LIGHT, TOKENS_DARK   {token: "#RRGGBB"}, same keys
    TOKEN_FLOORS                ((theme, fg, bg, floor), ...) measured pairs
    def relative_luminance(hexstr):   -> float
    def contrast_ratio(a, b):         -> float, UNROUNDED

### The failure surface

    REFUSAL_HELP        {reason_code: (context, hint, next_action)}
                        127 entries, one per code tools/bm_store.py can emit
    FAILURE_BLOCK_PARTS = ("What I was doing", "What happened", "Why",
                           "What you can do", "What remains safe")
    EXPANDER_LABEL = "show me exactly what happened"

    def failure_block(reason_code, attempted, raw, medium="text"):   -> str
      Raises KeyError for a code with no entry.
      medium "html": one <section class="bm-failure"> with exactly one
      <details>, which is the only place a raw log may appear.

### The router and the escapers

    SURFACES = ("S1", "S2", "S3", "S4")
    MUST_ACT_KINDS = ("open-key-decision", "failed-gate", "consent-missing",
                      "founder-step", "budget-ceiling")
    ASKED_KINDS = ("status-answer", "next-answer", "explain-answer")
    STATE_KINDS = ("progress", "pipeline-state", "gate-ladder",
                   "pen-holder", "insight-history", "timeline",
                   "handback-offer")

    def surface_for(item):   -> ("S4","S3","S1") | ("S3",) | ("S1","S2")
                                | ("S1",); raises ValueError otherwise
    def xml_escape(text):    -> str, escapes & < > " '
    def _flat(text, limit=48):   -> a label safe inside a drawn node

### Store surface, schema 17 (tools/bm_store.py)

    SCHEMA_VERSION = 17
    VIEW_KINDS  = ("PROJECT_VIEW", "DEVELOPER_BRIEF")
    VIEW_FIELDS = ("kind", "rel_path", "fingerprint", "artifact_url",
                   "published_at", "subject")

    Store.record_view(self, project_id, view, actor)
      -> {"view_id": str, "kind": str, "fingerprint": str}
    Store.list_views(self, project_id, kind=None, limit=None, raw=False)
      -> [row], newest first
    Store.latest_view(self, project_id, kind, raw=False)
      -> row or None            (kind is POSITIONAL and required)

    ReadOnlyStore gets list_views and latest_view. It does NOT get
    record_view, deliberately.

### Every new refusal reason, and what raises it

| Code | Raised by | When |
|---|---|---|
| `not-found` | `Store.record_view` | the project row does not exist (V1) |
| `bad-view-kind` | `Store.record_view` | kind outside VIEW_KINDS (V2) |
| `path-escape` | `bs.safe_project_path`, called by `record_view` | rel_path is empty, absolute, traversing, symlinked or hardlinked (V3) |
| `bad-fingerprint` | `Store.record_view` | not exactly 12 lowercase hex characters (V4) |
| `bad-artifact-url` | `Store.record_view` | non empty and not an https URL (V5) |
| `unknown-field` | `Store.record_view` | a key outside VIEW_FIELDS (V6) |

All six are `bs.OwnershipRefused` with `.reason` set to the code above, and
all six write nothing. One ValueError remains in `record_view`, for `view`
not being a dict at all: that is a caller type error, never shown to a
founder. `Store.list_views` raises ValueError for a kind outside VIEW_KINDS.

New ValueErrors in `bm_visual` (none of them is a founder-facing refusal;
each is a caller error a test catches):

| Raised by | When |
|---|---|
| `Diagram` | unknown shape, status outside the lexicon, status not in the label, a cap exceeded, an edge naming a missing node |
| `insight_box_slots` and `render_insight_box` | any of the six slots would be empty, naming the slot |
| `render_insight_box`, `render_alert`, `failure_block` | medium outside ("text", "html") |
| `alert` | rung outside RUNGS, kind outside ALERT_KINDS, or a kind whose rung disagrees |
| `surface_for` | an item kind that matches no branch |
| `relative_luminance` | a colour that is not six hex digits |
| `failure_block` | KeyError (not ValueError) for a reason code with no rewrite |

---

## Per section: landed or blocked

| Design section | Item | State |
|---|---|---|
| 11.1, 11.2 | `SCHEMA_VERSION` 16 to 17 | landed |
| 11.2 | `_TABLES_VIEW`, `_TABLES_V17`, `_TABLES_BY_VERSION[17]` | landed |
| 11.2 | `_VIEW_DDL`, `_VIEW_INDEX_DDL`, their statement lists | landed |
| 11.2 | `_migrate_16_to_17`, `_MIGRATIONS[16]`, `_ensure_schema`, `_ensure_indexes` | landed |
| 11.2 | `Store.record_view` and its six refusals | landed |
| 11.2 | `Store.latest_view`, `Store.list_views` | landed |
| 11.2 | `ReadOnlyStore` pass throughs | landed, TWO not three (see deviations) |
| 11.2 | `Store.purge_project` gains one delete and the `views` key | landed |
| 11.2 | `_DUMP_SAFE_COLUMNS`: rel_path and artifact_url withheld | landed, proven by a dump |
| 11.3 | the pinned purge dict gains `"views": 0` (two pins, not one) | landed |
| 6.1 | the insight box, six slots, no optional slot | landed |
| 6.2 | the four rungs, delivery first, `alerts_now` | landed |
| 6.3 | one NEEDS YOU, two rungs per chat message, no promotion by age, dedupe key | landed |
| 6.4 | the evidence class marking, REASONED double marked | landed |
| 6.5 | the ASCII terminal rendering | landed |
| 7.1 to 7.5 | the five shapes and their builders | landed |
| 7.6 | `diagram_for`, the closed mapping; mermaid deferred | landed (no `to_mermaid`, as the design directs) |
| 7.7 | `_flat`, XML escaping, deterministic geometry | landed |
| 9.2 | `REFUSAL_HELP` (127 entries) and `failure_block` | landed |
| 12.1 | every symbol in the inventory | landed, plus `visual_facts`, `alert`, `alerts_for_chat`, `node`, `edge`, `insight_box_slots`, `xml_escape` (see deviations) |
| 13.1 | 11 classes, 45 tests | landed, all green |
| 13.3 | 5 classes, 16 tests | landed, all green |

Nothing in the Writer D set is blocked.

---

## Deviations from the design, each with its reason

1. **The builders take `visual_facts(...)`, not `bl.collect_status(...)`.**
   Section 12.1 writes their signature as `(collected_status) -> Diagram`.
   `bl.collect_status` returns `{"fields": [(label, value, [extra lines])],
   ...}`, which is RENDERED founder prose (verified by reading
   tools/bm_lead.py:765 to 872). Building a picture out of it would mean
   parsing sentences, and the drawing would break the day a label is
   reworded. So `visual_facts` reads the same rows through the store's own
   public accessors and returns primitives, and the five builders are pure
   over that. This is not a second collector for the eight status fields:
   bm_visual never re-derives Goal, Direction, Progress, Time remaining,
   Decision needed, Risk, Evidence or Next step. Those stay bl's, and the
   page must keep reading them from bl.

2. **`alerts_now` takes `consented`.** Section 6.2 lists "consent not
   given" as a NEEDS YOU condition, but consent is not a row: it lives in
   the setup config, and any caller holding an open store handle has
   consent by construction. The parameter lets the doorway call
   `alerts_now(None, None, consented=False)` at minute zero with no store
   at all, which is the only way that condition can ever be true.

3. **V1's reason code is `not-found`, not `unknown-project`.** The store
   uses `not-found` at 27 sites for exactly this condition, including
   `record_insight`'s own R15. A 128th code meaning what `not-found`
   already means would fork a convention rather than extend one.

4. **V6 is an `OwnershipRefused`, where the ledger's R16 is a
   `ValueError`.** A page renderer must rewrite every refusal into a
   founder-facing block keyed by reason code (L-S9); a bare ValueError
   carries no code and would reach the founder as raw Python. So the
   unknown-key check is written out rather than delegated to
   `_lead_fields`.

5. **`ReadOnlyStore` gets TWO pass throughs, not three.** Section 11.2 says
   three, and names `record_view`, `latest_view`, `list_views`.
   `record_view` is a WRITE and must never exist on a read-only handle;
   the L04 block immediately above says exactly that about `record_insight`
   and `record_briefing`. Adding it would have been a defect.

6. **"a forecast whose range no longer contains the remaining work"
   (section 6.2, AT RISK) landed as kind `budget-drift`: the spend verdict
   is `soft-stop` while at least one step is not accepted.** The forecasts
   table holds `minimum_duration`, `likely_duration`, `maximum_duration`
   and the token ranges as PROSE columns, so "the range no longer contains
   the work" is not computable without parsing sentences, which is exactly
   what this design forbids elsewhere. The landed query is the same
   intent expressed as something the rows can answer, and it names the
   number of unaccepted steps in its own message.

7. **The counts shape carries `role="progressbar"` inside the SVG**, rather
   than being emitted as separate HTML divs. One emitter, no duplicate
   rendering path, and ARIA roles are valid on inline SVG elements.
   Section 4.5's requirement (progressbar plus aria-valuetext carrying the
   real sentence) is met inside `to_svg`.

8. **Seven symbols exist beyond the section 12.1 inventory**, all of them
   named in the SIGNATURES section above: `visual_facts` (reason 1),
   `alert` and `alerts_for_chat` (the constructor that enforces the closed
   kind set, and the two rung cap of section 6.3 rule 2), `node` and `edge`
   (so a caller cannot hand-build a malformed node), `insight_box_slots`
   (one extraction shared by both media, which is what makes "identical
   across media" checkable), and `xml_escape` (one escaper, used by the
   page too).

---

## Migration proof: an existing store still opens and migrates

`TestSchema17IsAdditive.test_migration_from_a_real_schema16_fixture_survives_every_row`
builds a REAL store (a project, a signed contract, one insight, one
briefing), reverts it to look like schema 16 by dropping the schema-17
tables and setting `meta.schema_version` to 16, re-opens it, and asserts:

* `meta.schema_version` is now 17;
* `projects`, `autonomy_contracts`, `insights` and `briefings` are byte
  identical before and after, row for row, dict for dict;
* `views` exists and holds zero rows (no backfill);
* no quarantine file appeared, so a healthy schema-16 store MIGRATES rather
  than being set aside.

Two sibling tests hold the rest of the additive law:
`test_the_fresh_and_migrated_paths_produce_identical_table_info` proves a
store born at 17 and a store migrated to 17 have identical `PRAGMA
table_info`, and `test_the_schema16_table_list_is_unchanged` proves the new
table did not leak backwards into `_TABLES_BY_VERSION[16]`.

Run out of the suite, verbatim:

```
$ cd /Users/khalil.maaouni/Documents/BrotherModeUp/tools
$ python3 -m unittest test_bm_store.TestSchema17IsAdditive
....
----------------------------------------------------------------------
Ran 4 tests in 0.115s

OK
```

---

## Guards that fired, and what was done at the class

Four fired. Every one was correct and every one was fixed at the class
rather than narrowed.

1. **The raw `execute()` router** (tools/test_bm_store.py:1017). It caught
   `_migrate_16_to_17`. Fixed by adding an exempt entry WITH a written
   reason, the same sentence `_migrate_15_to_16` carries: a migration runs
   inside the caller's BEGIN EXCLUSIVE, so a CREATE TABLE failing
   mid-migration must roll the caller's transaction back rather than move
   the founder's store aside.

2. **The pinned purge dict, TWICE.** The design names
   tools/test_bm_project.py:1353. There is a SECOND pin at
   tools/test_bm_store.py:14933 (`TestPurgeProject`), and it turned red the
   moment `purge_project` started removing views. Both now carry
   `"views": 0` with the reason, and the non-zero case is
   `TestViewPurgeLeavesNoOrphans`.

3. **The pre-write gate** (tools/test_bm.py `TestPreWriteGate`).
   tools/bm_visual.py has ZERO write sites by that scanner's own patterns,
   verified by running them over the file, so tools/write_sites.json needs
   no entry and was not touched. That file is outside this writer's set and
   stays outside it.

4. **My own class-coverage check, added after LOOKING at a rendered page.**
   The status "not run" was emitting `class="bm-not run"`, which a browser
   reads as two classes, one of them called "run", and "NOW" was emitting
   `class="bm-NOW"` against a rule written `.bm-now`. Fixed with a `_slug`
   helper, and the check that found it is now an assertion inside
   `TestColourIsNeverAlone`, comparing every class the markup uses against
   every class THEME_CSS defines.

---

## DONE CHECK, quoted verbatim

Run from /Users/khalil.maaouni/Documents/BrotherModeUp after the last edit:

```
$ for c in tools/test_bm_visual.py tools/test_bm_store.py \
    tools/test_bm_project.py; do out=$(python3 "$c" 2>&1); code=$?; \
    echo "python3 $c -> exit $code | $(echo "$out" | \
    grep -E '^(Ran|OK|FAILED)' | tr '\n' ' ')"; done
python3 tools/test_bm_visual.py -> exit 0 | Ran 45 tests in 0.574s OK
python3 tools/test_bm_store.py -> exit 0 | Ran 976 tests in 30.237s OK
python3 tools/test_bm_project.py -> exit 0 | Ran 40 tests in 15.200s OK
```

Counts against the pre-change baseline, measured on the untouched tree
before any edit:

| Suite | Before | After | Change |
|---|---|---|---|
| tools/test_bm_store.py | 960 | 976 | +16, no test removed |
| tools/test_bm_project.py | 40 | 40 | unchanged, one pinned dict widened |
| tools/test_bm_visual.py | did not exist | 45 | +45 |

No suite's count dropped.

Failing-first evidence:
docs/program/absolute-lead/evidence/L05/RED-D.txt, three labelled blocks
(visual, store, purge pin) captured against the untouched tree. All 11
visual classes and all 5 store classes appear there with at least one
failure or error; the visual suite was 45 failures out of 45.

---

## What I could not close, with the reason

1. **tools/pyproject.toml does not name `bm_visual`, so
   `tools/test_bm.py::TestP17PackagingManifestMatchesTheRepository::
   test_every_shipping_tool_is_in_py_modules` is RED.** Verbatim:

   ```
   FAIL: test_every_shipping_tool_is_in_py_modules
   AssertionError: Items in the second set but not the first:
   'bm_visual' : these tools ship in tools/ but pyproject.toml would not
   install them, so a pipx or pip install is missing them: ['bm_visual']
   ```

   `pyproject.toml` is Writer E's file (design section 16), and section
   12.3 already assigns him the change: `"bm_view"` and `"bm_visual"` in
   `py-modules`, plus `bm-view = "bm_view:cli"` in `[project.scripts]`.
   Minimal remedy, for E: add `"bm_visual"` to the `py-modules` array in
   the same change that adds `"bm_view"`. I did not touch the file, and
   no other test in that class fails.

2. **tools/test_all.py does not list `test_bm_visual.py` in `SUITES`, and
   .github/workflows/tests.yml has no step for it.** Both files are Writer
   E's (design 12.3 and 16). Until he lands them the new suite is not in
   the gate or in CI. Minimal remedy, for E: add `"test_bm_visual.py"` to
   `SUITES` after `test_bm_lead.py`, and one workflow step per new suite.

3. **tools/test_bm_docs.py's `TestNoDashes` does not yet name
   tools/bm_visual.py or tools/test_bm_visual.py.** That file is Writer
   F's, and his in-tree comment says the lander of the four L05 tools files
   adds their lines. I cannot edit it under the single-writer law. Both my
   files are verified dash free AND fully ASCII (`sorted({c for c in src if
   ord(c) > 127})` is empty for both), so adding the two lines will pass.
   The ASCII fixture in `TestNoNonAsciiInTerminalOutput` writes every
   hostile character as an escape (the escape form, for example `u"\u2014"`) for exactly
   this reason.

4. **No pixel check of a rendered page.** The browser preview would not
   open a file:// page outside the project and the navigate call timed out
   at 300 seconds; rather than write a preview into the repository to work
   around it, the visual verification is structural, which is what section
   13.0 asks for: every figure is parsed with a real XML parser, every
   class used is compared against every class defined, every token pair is
   re-measured against its WCAG floor, and both text forms were read by
   hand. The page itself is Writer E's deliverable and the pixel look
   belongs with it.

5. **`published_at` is stored as free text and is not validated as a
   timestamp.** The design does not ask for it, and the store has no
   generic timestamp validator for a caller-supplied value; noting it so
   nobody assumes it is checked.

6. **Not run by this writer, by instruction:** tools/test_all.py, and the
   full tools/test_bm.py, tools/test_bm_docs.py, tools/test_bm_consent.py
   and tools/test_bm_controller.py suites. I did run tools/test_bm_schema.py
   (20 tests, OK), tools/test_bm_sentinel.py (87 tests, OK) and
   tools/test_bm_lead.py (77 tests, OK) as a collision check on the schema
   bump, and the two tools/test_bm.py classes that could plausibly react to
   a new module (`TestPreWriteGate`, 11 of 12 green, and the packaging
   class, whose one failure is item 1 above).
