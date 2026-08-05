Status: CURRENT. Fable design, 2026-08-05. Implementation loop L05 of the
absolute-lead program (the visual surface). Nothing here is built yet. This
design starts after DESIGN-L04.md lands, and section 0.1 states why that
ordering is load bearing rather than a preference.

# DESIGN visual surface: the live project view, the first fifteen minutes, the insight box, the alert ladder, the drawn vocabulary, and the visible handback

Target tree: /Users/khalil.maaouni/Documents/BrotherModeUp

Files this design authorises a writer to change, and nothing else:

    tools/bm_visual.py                    (NEW)
    tools/bm_view.py                      (NEW)
    tools/test_bm_visual.py               (NEW)
    tools/test_bm_view.py                 (NEW)
    tools/bm_store.py
    tools/test_bm_store.py
    tools/test_bm_project.py              (the pinned purge dict only)
    tools/test_bm_consent.py
    tools/test_bm_docs.py
    tools/test_all.py
    hooks/hooks.json
    pyproject.toml
    .github/workflows/tests.yml
    capabilities.status.json
    README.md                             (generated block only, via bm-docs)
    docs/ROADMAP.md                       (generated block only, via bm-docs)
    docs/KNOWN-LIMITS.md
    SECURITY.md
    references/visual-surface.md          (NEW)
    references/terminology.md
    references/status-view.md
    skills/brotherme/SKILL.md
    commands/brotherme-view.md            (NEW)
    commands/brotherme-help.md
    commands/brotherme-start.md
    commands/brotherme-status.md
    commands/brotherme-handback.md
    docs/program/absolute-lead/evidence/L05/   (NEW folder, section 13)

Not in the list, and deliberately: tools/bm_lead.py, tools/bm_controller.py,
tools/bm_project.py, tools/bm_docs.py, tools/bm_autonomy.py,
tools/bm_telemetry.py, scripts/setup.py. Section 0 says why each stays shut.

Inputs read in full before writing this:
docs/program/absolute-lead/research/visual-surface/LENS-A-agent-tools.md,
LENS-B-onboarding.md, LENS-C-visual-language.md, LENS-D-claude-surface.md,
docs/program/absolute-lead/DESIGN-insight-ledger-and-handback.md,
docs/program/absolute-lead/DESIGN-L04.md sections 3, 4, 7, 9 and 11 (plus 0, 1,
2, 15, 17, 19 and 20 for the conventions this copies),
docs/program/absolute-lead/evidence/L03/DESIGN-round4.md (as the model for
rigour), references/status-view.md, references/terminology.md,
references/kickoff.md, skills/brotherme/SKILL.md, CANVAS.md, hooks/hooks.json,
commands/brotherme-help.md, and the points of tools/bm_store.py,
tools/bm_docs.py and tools/bm_project.py that this design names.

Every line reference below is to the CURRENT working tree, verified by reading
it, not by memory. Every research citation names the lens and its section, and
every lens claim carries its own evidence marker there.

---

## 0. What this design does not touch, and the one ordering that matters

### 0.1 It starts after L04, and it edits none of L04's code

DESIGN-L04.md is being built right now and its Writer B owns `tools/bm_lead.py`.
This design opens **no L04 code file**. It imports from `bm_lead` and it edits
nothing in it. That is not politeness, it is the same law that makes the store
the single source of truth: L04 section 4.1 establishes one collector and two
renderers, and this design adds a **third renderer over the same collector**
rather than a second collector. A view that collected its own rows would be a
second truth, and the whole product is built on refusing that.

Concretely, `tools/bm_view.py` calls, and never reimplements:

    bl.collect_status(store, project_id)          L04 section 3.4, 15.2
    bl.collect_briefing(store, project_id, prev)  L04 section 7.3, 15.2
    bl.next_action(store, project_id)             L04 section 3.6
    bl.render_decision_card(insight, ic=False)    L04 section 9.3
    bl.evidence_label(evidence_class)             L04 section 4.4
    bl.render_forecast_lines(forecast)            L04 section 3.7
    bl.HANDBACK_OPTION_TEXT                       L04 section 9.1
    bl.DECISION_STAKES                            L04 section 3.4
    bl.PACK_PAGES, bl.HANDOVER_ROOT               L04 section 11.1

An ast guard in `tools/test_bm_view.py` fails the build if `bm_view.py` defines
any function whose name begins `collect_`, or if it imports `sqlite3`, or if it
contains a SQL shaped literal. The shape is copied from
tools/test_bm_controller.py:97, the same guard L04 section 3.1 applies to
bm_lead.py.

L04 section 4.1's fixture asserts that every shared field value is byte
identical between the founder render and the IC render. Section 13.2 below
extends that fixture to the HTML render: same collector, three renderers, one
set of values.

**Where L04 actually stands in the tree today, verified by reading it rather
than assumed.** L04's store half has landed: `SCHEMA_VERSION` is 16
(tools/bm_store.py:81), `record_insight` exists (14852), and so do
`latest_briefing` (15158), `open_key_decisions` (15166) and
`active_minutes_since` (15186). L04's surface half has not:
`tools/bm_lead.py` is not in the tree (`ls tools/`). So this design's schema
step is 16 to 17, which is what section 11 says, and the only thing gate 0
in section 16 is waiting on is L04's Writer B.

### 0.2 What else stays shut, and why

1. **tools/bm_docs.py.** It already generates `Documentation/` including
   mermaid diagrams (tools/bm_docs.py:2251, 2293, 2386, 2443, 2499, 2527). This
   design draws its own pictures from its own model and does not enter that
   file. Section 7.6 states why the mermaid emitter is deferred rather than
   wired into bm_docs.
2. **tools/bm_project.py.** `render_canvas` (468) states the byte stability
   rule this design obeys (section 4.6). It is read, never edited.
3. **scripts/setup.py and tools/bm_telemetry.py.** The consent gate's shape is
   copied, never modified, exactly as L04 section 0.4 requires.
   `scripts/setup.py:142` `is_consented` is the definition, and it does not
   move because a new program depends on it.
4. **The five safety floors, one store, one canonical integrator, one writer
   per file.** Unchanged.
5. **`CONTROLLER_STATE_TRANSITIONS` and `AUTONOMY_FLOORS`.** Read only, as in
   L04 sections 0.1 and 0.2.

---

## 1. Coverage table

### 1.1 The founder's own phrases

| The founder said | One line answer | Section |
|---|---|---|
| "the GUI is weak" | four surfaces, each with one job, and a stated rule for choosing; anything with no job is cut | 3 |
| "onboarding and handholding are hard" | a scripted first fifteen minutes with three commands, a visible result per step, and designed empty states | 5 |
| "documentation and problem solving are not visual" | help is generated into the page it belongs to, and every failure becomes a five part block, never a log | 9 |
| "HTML artifacts to the side" | one live project view, written to disk first and published second, updating in place at one stored URL | 4 |
| "process flows and graphs in the chat" | five drawn shapes in the page; in the Claude Code terminal the chat gets the text form plus one link, because the terminal cannot render a picture (LENS-D section 3, verified negative) | 3.4, 7 |
| "recurrent insight boxes" | one six slot box, rendered from one ledger row, appearing on a cadence the ledger already owns | 6.1 |
| "key alerts that keep him engaged" | a four rung ladder where exactly one rung interrupts, delivered by a hook with no model in the loop | 6.2 |
| "fully understanding what is happening" | every claim carries its evidence class, and reasoning is labelled as reasoning in every surface | 6.4 |
| "giving him the hand to take over" | a standing panel that is present whether or not a decision is open, plus the developer brief as a rendered page | 8 |

### 1.2 The non negotiable constraints

| Constraint | How it is met | Section |
|---|---|---|
| self contained artifacts, no network at render time | one file, inline CSS, inline SVG, no script tags of any kind in the first build | 4.5 |
| standard library Python only, no daemon, no server | `html.parser`, `hashlib`, `xml.sax.saxutils`, `json`, `os`, `re`; freshness comes from regeneration, never from polling | 4.3, 11 |
| every view generated from store rows | no collector of its own, no hand maintained file, ast guarded | 0.1, 2 L-S1 |
| CANVAS.md and STATE.md precedent | one write funnel, whole file generated, no render clock, byte stable | 4.6 |
| nothing renders or writes before setup consent | one store constructor, consent computed before the command dispatch, zero files under HOME or the project before consent | 11.4 |
| one recommended next action per response | the page prints `bl.next_action`'s single triple and nothing else; a second action is a test failure | 4.2, 13.2 |
| estimates as ranges with confidence | every duration and budget on the page comes from `bl.render_forecast_lines`; no arithmetic on a forecast anywhere in the new modules | 4.2 |
| plain language per the terminology map | the founder render passes the same lexicon test L04 applies; the register gains its rows before the words are used | 12.3, 13.2 |
| an insight with no executed evidence is reasoning, not fact | the REASONED prefix is applied by the renderer, and the box additionally prints "not tested" beside the class token | 6.4 |

---

## 2. The nine laws this design adds

Everything below is an application of one of these. A writer unsure what to do
in a case this document did not enumerate applies these in order.

* **L-S1 Generated, never authored.** Every pixel, word, number, node and bar
  on any surface is a pure function of store rows read through L04's collectors.
  There is no hand written picture and no hand maintained page, for the same
  reason CANVAS.md is generated (tools/bm_project.py:468 to 476).
* **L-S2 The file is the product, the published page is an enhancement.**
  `bm-view render` always writes the local file and always succeeds. Publishing
  is a separate act that can fail, and its failure never removes a surface from
  the founder. LENS-D section 2.10 lists five independent gates that can make
  publishing unavailable, and LENS-A W9 says the durable surface must be a file.
* **L-S3 Two levels, and one expander.** The chat is level one. The page is
  level two. Inside the page exactly one depth of disclosure is permitted, and
  a nested one is a test failure (LENS-C section 1.6, citing NN/g's finding
  that designs beyond two levels typically have low usability).
* **L-S4 Colour is the third carrier.** Every status is recoverable from a word
  first, a non colour mark second, and colour third. The SVG carries no colour
  of its own; all colour lives in one stylesheet block, so the test that
  deletes that block and asserts every status is still readable is trivial
  rather than aspirational (WCAG 1.4.1 level A, LENS-C section 3.2).
* **L-S5 One vocabulary, two renderings.** The same five shapes, four rungs and
  one box render as plain ASCII text in the terminal and as styled HTML in the
  page. A concept that works in only one of the two does not enter the
  vocabulary (LENS-C L-V4).
* **L-S6 Alerts are derived, never stored.** There is no alerts table. There is
  one pure function over rows. A stored alert is a lie the moment its condition
  clears (LENS-C section 5.5).
* **L-S7 Only the top rung interrupts.** Everything below it is available, not
  thrown (AHRQ, LENS-C section 2.1). No rung is ever promoted by age.
* **L-S8 The page is honest about being a snapshot.** It states the newest
  record it was built from and its content fingerprint, never its own render
  clock, so it is byte stable and still visibly stale (section 4.6).
* **L-S9 A refusal never reaches the founder unrewritten.** Every reason code
  the engine can emit has a founder facing counterpart in one map, and a test
  enumerates the codes and fails on a missing entry (LENS-B rule 7, clig.dev).

---

## 3. THE SURFACE MAP

### 3.1 The four surfaces that exist

| # | Surface | What it IS, mechanically | Its one job | Always available |
|---|---|---|---|---|
| S1 | **the generated file** `PROJECT-VIEW.html` at the project root | a single self contained HTML file written through `bs.write_generated_document` (tools/bm_store.py:16708) | to be the durable, diffable, committable answer to "where does this project stand", readable with no plan, no login and no network | yes |
| S2 | **the published page** (the Artifact) | S1's bytes published by Claude's `Artifact` tool to one private URL, updated in place | to be the thing the founder keeps open in a browser beside the terminal while work runs | no, five gates, LENS-D 2.10 |
| S3 | **the terminal text** | ASCII blocks printed into the chat by the coordinator or by a hook | to answer the question the founder just asked, in the place he asked it, and to carry the one recommended next action | yes |
| S4 | **the native harness dialogs** | `AskUserQuestion` for decisions, hook `systemMessage` plus `terminalSequence` for the top alert rung | to make the founder ACT: a decision he must answer, an alert he must not miss | yes for hooks, yes for questions |

### 3.2 What is cut, and the reason each has no job

* **Inline widgets and custom visuals in chat.** LENS-D section 3 is a verified
  negative for Claude Code: the feature is scoped to "chats on Claude web and
  desktop apps only" plus Cowork, and no such page exists in the Claude Code
  documentation index. Designing the primary experience on it would put the
  founder's core loop on a capability his surface does not have.
* **A status line.** A plugin cannot install the main `statusLine`; plugin
  `settings.json` supports only `agent` and `subagentStatusLine` (LENS-D
  section 6, verified negative). A surface BrotherMode cannot install is not a
  surface BrotherMode ships. Section 14.1 keeps it as a proposal the founder can
  accept into his own settings.
* **A background monitor for freshness.** Monitors are experimental,
  interactive CLI only, and unsandboxed at hook trust level (LENS-D section 4).
  A freshness mechanism that is experimental is not load bearing. Section 14.2.
* **Live streaming panes (shell, editor, browser, cursor video).** LENS-A W1:
  no daemon, no server, and an artifact has no network at render time, so
  nothing can stream into it. Worse, a shell pane is a log, and the founder
  cannot read logs and should never have to.
* **Screenshots or video of a running application as proof.** LENS-A W7:
  BrotherMode does not run the user's application and has no browser. Promising
  visual proof it cannot produce would be the single most damaging over claim
  available here. The substitute is the evidence block in section 6.1 slot 2.
* **A token or cost meter as the headline.** LENS-A W6: it measures the machine,
  not the work. Spend appears in the counts row (D5) and never in an alert.
* **A second page.** An artifact is a single page and relative links do not
  resolve (LENS-D section 2.2). Everything is one page with in page anchors.

### 3.3 The rule for choosing a surface

One function, `surface_for(item)`, and it is a first match router so two runs on
the same rows always agree. It is enforced by a test that drives every item kind
and asserts the surface chosen.

1. **The founder must act before anything can move.** An open key decision, a
   failed hard gate, consent not given, a founder step with a floor id, a budget
   ceiling reached. Goes to **S4**, plus one line in **S3**, plus a pinned panel
   in **S1**. Never only in the page: a page he has not opened is not a channel.
2. **The founder asked a question in the chat just now.** Goes to **S3**, in the
   shape references/status-view.md:8 to 16 fixes, with one link line to the page
   when the page holds more.
3. **The item is state rather than an ask, and it is worth returning to.**
   Progress, the pipeline, the gate ladder, who holds the pen, the insight
   history, the timeline, the standing handback offer. Goes to **S1**, and to
   **S2** when publishing is available.
4. **The item is a picture.** Goes to **S1** only. In the terminal it renders as
   its text form (section 7.5), which is not a downgrade in information: LENS-C
   section 5.8 fixes what the text form of each shape must carry.
5. **Anything left over is not shown.** An item that matches no branch has no
   job, and the test asserts the router raises rather than defaulting, so a new
   item kind cannot slip in as noise.

### 3.4 The honest answer to "graphs in the chat"

The founder asked for process flows and graphs **in the chat**. In the Claude
Code CLI that is not available: there is no inline widget surface (LENS-D
section 3), and Claude Code does not render images into the terminal for the
user (LENS-D section 6, verified negative on the Read tool's image behaviour).

What this design gives him instead, and it is stated in these words in
`commands/brotherme-view.md` so the product never over claims:

* the picture lives one click away in a page that updates in place while he
  works, which is the closest shipped analogue in the whole survey (LENS-A T1,
  the Claude Code agent view, and LENS-D section 2.5, republish is live for
  anyone with the page open);
* the chat carries the same facts as text on the same turn, so nothing is
  hidden behind the click (L-S5);
* if he works in the Claude desktop Chat tab or in Cowork rather than the CLI,
  inline visuals may additionally be available there. That is a fact about his
  surface, not a change to what BrotherMode builds, and it changes no file in
  section 12.

---

## 4. THE LIVE PROJECT VIEW

### 4.1 What it is

One page, `PROJECT-VIEW.html`, at the project root beside `CANVAS.md`, written
by `bm-view render`. It is the founder's standing answer to "where does this
project stand", and it is the only page this design creates. LENS-A T14 is the
reason there is exactly one: Copilot Workspace built a bespoke four stage
surface and the standalone product did not persist, while its successor hangs
everything on artifacts that already existed. Here the pre existing artifacts
are the store rows, and every section is a projection of them.

### 4.2 What it shows, in this order

`VIEW_SECTIONS` is a module tuple of
`(anchor_id, heading, renderer_name, empty_state_key)`, copying the shape of
tools/bm_docs.py:139's `FILES`, so "every section" is enumerable data a test
iterates rather than a list somebody keeps in sync by hand.

| # | Anchor | What it holds | Source |
|---|---|---|---|
| 1 | `#header` | the outcome in the founder's words, one sentence of where the work stands, the setup progress counter, the newest record time, the content fingerprint | `bl.collect_status` header fields, section 4.6 |
| 2 | `#needs-you` | the single top rung alert, pinned, `role="alert"`; or the standing sentence that nothing is waiting on him | `alerts_now`, section 6.2 |
| 3 | `#next-step` | exactly one recommended next action, its WHY line, and the exact command | `bl.next_action`, L04 section 3.6 |
| 4 | `#pipeline` | D1, the drawn pipeline | section 7.1 |
| 5 | `#counts` | D5, the count rows: gates passed of total, spend against ceiling, findings by rung | section 7.5 |
| 6 | `#decisions` | the open key decisions, highest stakes first, each as a card ending in the handback line, each with D4 drawn beside it | `bl.render_decision_card`, section 7.4, 8.1 |
| 7 | `#insights` | the insight boxes, newest first, six slots each | section 6.1 |
| 8 | `#gates` | D2, the gate ladder | section 7.2 |
| 9 | `#lanes` | D3, who holds the pen | section 7.3 |
| 10 | `#timeline` | every briefing in order, oldest first, so the run replays forwards | `Store.list_briefings`, L04 section 11.1 |
| 11 | `#your-move` | the standing handback panel, present whether or not a decision is open | section 8 |
| 12 | `#help` | what this page is, what it cannot do, and the honest limits, generated from one map | section 9.3 |

Rules that bite on this list:

* Section 3 prints exactly one action. A test counts the elements carrying
  `data-bm-next-step` and asserts the count is 1 on every fixture.
* Sections 4, 6, 8 and 9 carry the four drawings. That is the per page cap
  (LENS-C section 5.3) reached exactly, so a sixth shape cannot be added without
  deleting one.
* Every duration or budget in sections 1, 3, 5 and 10 is emitted by
  `bl.render_forecast_lines`. A structural test asserts no format string in
  `bm_view.py` or `bm_visual.py` contains a bare "hours" or "days", copying
  L04 section 3.7's rule.

### 4.3 How it updates, stated honestly

There are exactly three ways the page changes, and none of them is the page
doing anything by itself.

1. **On command.** `bm-view render --project-id ID` rewrites the file. The
   coordinator runs it; `/brotherme-view` is the founder facing wrapper.
2. **On the Stop hook.** One new hook entry runs `bm-view render --if-stale`,
   which recomputes the fingerprint and rewrites the file only when it changed.
   This is LENS-D section 5 path 1, the verified premise that a hook can
   regenerate a file. A hook **cannot** publish: hooks are shell commands with
   no access to Claude's tools (LENS-D section 5, verified negative).
3. **On republish, by Claude.** Publishing requires the `Artifact` tool, which
   only the model holds. `bm-view render` prints one line naming the stored URL
   and whether the bytes changed; `skills/brotherme/SKILL.md` carries the
   standing instruction to republish to that URL when they did. LENS-D section
   5 path 2 is explicit that this is a request and not a guarantee: Claude
   decides. The design therefore never says the page is live. It says the page
   is a snapshot and prints what it is a snapshot of.

What is NOT possible, stated so nobody designs on it later: the published page
cannot read the store at view time. Connector calls are limited to claude.ai
connectors, require Claude Code v2.1.209 or later, and local MCP servers are
explicitly excluded (LENS-D section 2.7). The store is local. So freshness comes
from republishing, forever, and any design that assumes polling is wrong.

The stored URL is not optional plumbing. LENS-D section 2.5: "Without the URL, a
new session always creates a new artifact rather than updating an existing one."
Without persistence the founder accumulates a graveyard of one shot pages, so
the URL is a store row (section 11).

### 4.4 What it looks like when a project has barely started

This is the highest traffic teaching surface in a tool that starts from nothing
(LENS-B section 1.4), and it is the part that did not exist before.

**Every section with zero rows renders a designed empty state. A section that
renders blank is a defect** (LENS-B rule 1). `EMPTY_STATES` is a module dict
keyed by `empty_state_key`, and each entry has exactly four fields, following
Carbon's anatomy and content rules as reported in LENS-B section 1.4:

    title      a positive statement about what will be here
    body       one sentence, at most 140 characters, saying what fills it
    action     one action, in verb plus noun form
    command    the exact command that action runs

Mechanical rules, each a test in section 13:

1. Exactly one action per empty state. Two is a failure (LENS-B rule 2, from
   Carbon's rule against covering multiple options in one empty state).
2. The title contains none of the words "no", "none", "nothing", "empty".
   That is the positive statement rule made checkable.
3. The command names a command that is currently offered to this founder. During
   the first fifteen minutes that set is three commands (section 5.3), so an
   empty state cannot teach a command the founder has not met (LENS-B rule 4).
4. No empty state uses a left column term from references/terminology.md:10 to
   34 (LENS-B rule 3).
5. Loading, error and genuinely empty are three different states and each has
   its own text (LENS-B section 1.4, guideline 1). "Error" here means the store
   refused or the project id is unknown, and it renders as the section 9.2
   block, not as an empty state.

The header on a barely started project reads, verbatim in shape:

    Outcome        "a booking page my customers can actually use"
    Where we are   Your project records exist. Nothing has been planned yet.
    Setup          2 of 8
    Built from     records up to 2026-08-05 14:02, fingerprint 9f2c1a7b4d03

**The setup counter counts real rows only** (LENS-B rule 11). The eight are
detected, never asserted:

    1  an outcome is recorded            projects.goal is non empty
    2  your project records exist        the project row exists
    3  a direction is agreed             a DECISION insight, or a live contract
    4  the work is planned               at least one task or unit row
    5  a first piece is accepted         a DONE unit, or an accepted task
    6  a check ran and passed            an insight with evidence_class EXECUTED
    7  a catch-up is on record           a briefings row
    8  a delivery packet exists          the deliver artefact on disk

At the end of minute 4 of the first run, one and two are true, so the counter
reads 2 of 8. That is the honest form of the endowed progress effect (LENS-B
section 1.9): the advancement is genuine, the reframing from "not begun" to
"undertaken and incomplete" is obtained, and nothing is invented.

### 4.5 How the page is built, mechanically

* One file. Inline `<style>`, inline `<svg>`. **No `<script>` element at all in
  the first build**, and a test asserts the string `<script` does not appear.
  Interactivity is `<details>` and `:target`, both of which are CSS and HTML.
  This is stricter than the platform requires (inline JS is allowed, LENS-D
  section 2.2) and it buys three things: the page cannot break, the token cost
  is lower (LENS-D section 7 warns a styled page is more token intensive than
  the same content as terminal text), and the structural test has no runtime to
  simulate.
* No external request of any kind, which the CSP would block anyway (LENS-D
  section 2.2). No fonts, no images, no data URI images. Drawings are inline SVG.
* Both themes, through `prefers-color-scheme` plus a `data-theme` override on
  the root so the viewer's toggle wins in both directions (LENS-D section 2.4).
* Every wide element (the drawings, the tables) sits in its own
  `overflow-x: auto` container. The page body never scrolls sideways.
* Every drawing is a `<figure>` containing an `<svg role="img">` with a
  `<title>` and a `<desc>` referenced by `aria-labelledby` and
  `aria-describedby`, plus a `<figcaption>` stating the same content in prose a
  sighted non expert can read without decoding the picture (W3C complex images,
  LENS-C section 3.4). The prose is not duplicate cost. It is the thing that
  makes the picture optional.
* Count bars use `role="progressbar"` with `aria-valuetext` carrying the real
  sentence ("4 of 7 gates passed"), because a percentage would not be a truthful
  representation (LENS-C section 3.5).
* The colour tokens are exactly LENS-C section 5.6's measured table, both
  themes, and section 13.1 re-runs that computation in the suite.

### 4.6 Byte stability and honest staleness, reconciled

These two pull against each other and the reconciliation is a real decision.

`render_canvas`'s docstring (tools/bm_project.py:468 to 476) forbids a "generated
at" line, because it would make two back to back regenerations of an unchanged
project differ by nothing but the clock. LENS-C section 5.9 wants the page to
state when it was generated so a stale tab is visibly stale.

The page therefore states **two things that are properties of the data, not of
the clock**:

* `Built from records up to <the newest row timestamp it read>`, and
* `fingerprint <the first 12 hex of sha256 over the rendered body>`.

Both are pure functions of the rows. Two regenerations with no intervening write
produce identical bytes, so the D-4 rule holds. A tab open on an older
fingerprint is visibly older, so the staleness rule holds. The fingerprint is
also what `--if-stale` compares, so the same value serves three purposes and
there is nothing extra to keep in sync.

---

## 5. THE FIRST FIFTEEN MINUTES

Times are targets for a founder who has never used this, working from an empty
folder in Claude Code. Every choice cites its evidence. Where this design
departs from LENS-B, section 5.2 says so and gives the reason.

### 5.1 Minute by minute

**Minute 0 to 1. The doorway. Zero writes, and it is TEXT.**

The founder types `/brotherme-start "<goal>"` or `/brotherme-help`. Whatever he
types, he gets one block in the chat (S3) and one question. Nothing is written
to disk.

The doorway block obeys Carbon's empty state anatomy (LENS-B section 1.4): a
title written as a positive statement, one short body, ONE primary action, one
secondary link. It answers only the three questions a founder has at minute
zero: what will happen, what it will cost in time and money as a range, and what
he will have to decide.

What is deliberately absent: the command list, and the words fence, gate,
dispatch, work record, store, ledger and sentinel (LENS-B rule 3). Those are
reference material and a tutorial is not the place for them (Diataxis, LENS-B
section 1.7).

**Minute 1 to 4. The goal, in his own words, one question at a time.**

references/kickoff.md's existing rule already matches minimise choice: ask only
the questions whose answers change scope, one decision at a time, recommended
option first. Two additions:

* Every question travels through `AskUserQuestion` (S4), which is a native,
  mouse clickable, non prose decision surface (LENS-D section 6). Chat text
  carries evidence and context, never the option list, which is
  references/kickoff.md:61 to 63 already.
* Scoping context is gathered here, before any working session, which is
  Superhuman's move of putting discovery into a pre session survey rather than
  into the session (LENS-B section 1.9).

**Minute 4. Consent, and the first write.**

The store is initialised. One plain sentence about what it did.

Then, and only then, **the first visual appears**: `bm-view render` writes
`PROJECT-VIEW.html`, and the founder is offered the page. The setup counter
reads 2 of 8 (section 4.4).

The consent sentence must disclose one thing the founder cannot otherwise know:
republishing an already approved artifact does not prompt again (LENS-D section
2.5). So the page will update silently after the first approval. That is the
desired behaviour and it must be said at consent time, not discovered.

**Minute 4 to 9. One real unit of work, end to end, with a visible object.**

This is Stripe's move (LENS-B section 1.9): not a description of what
BrotherMode will do, but the smallest genuine piece of the founder's actual
project, run to completion, with the resulting artefact shown. He should be able
to point at something that exists and say that came from the thing I said five
minutes ago.

**Minute 9 to 13. The page replaces the wall of text.**

Every section with no rows renders its empty state with its own learning cue and
its own single action (section 4.4). The founder learns the shape of the product
by seeing the outline of what will fill it, which is NN/g's guideline 2 and
Datadog's worked example (LENS-B section 1.4).

The pipeline (D1) renders with the current stage marked and unreached stages
visibly idle. This satisfies Atlassian's rule that you never reference something
the viewer cannot see (LENS-B section 1.5) and it answers the founder's wish for
process flows without adding a diagram anyone maintains.

**Minute 13 to 15. The first catch-up, and the first handback offer.**

L04 section 7.2 fires a briefing on ACTIVE_MINUTES or on PHASE_BOUNDARY. For a
first run the thirty minute clock is too late by construction, because
Superhuman's entire activation window is thirty minutes (LENS-B section 1.9).
The PHASE_BOUNDARY trigger already covers this: going from no run to a run is a
boundary, and so is a founder step opening (L04 section 7.2 item 2). So the
first catch-up fires at the first phase boundary **with no change to L04**, and
this design records that as the reason the rule is already right rather than
asking for a new trigger.

The handback line appears at the first key decision with the stable wording
L04 section 9.1 fixes, and the standing panel (section 8) is on the page from
the first render.

### 5.2 Where this design departs from LENS-B, and why

**LENS-B puts an artifact at minute 0.** It says: "Whatever they type, one
artifact opens and one question is asked in chat. Nothing is written to disk."

That is not possible. Publishing an artifact requires Claude to write the page
to a file in the project first ("Claude writes the page to an HTML or Markdown
file in your project, then publishes it", LENS-D section 2.9), and that local
write is a `Write` tool call which the artifact permission prompt does **not**
cover. So a minute zero artifact is a write before consent, which is the one
thing this product may never do.

The doorway is therefore a terminal block, not a page. Nothing else in LENS-B's
sequence moves. The teaching content, the anatomy, the absent command list and
the three questions it answers are unchanged; only the medium changes, and it
changes to the one medium that is always available anyway (S3).

### 5.3 Training wheels: three commands, then triggers

The single highest value change in the whole onboarding evidence, and it is
content and sequencing, not engineering (LENS-B section 1.2: 26 and 21 percent
faster on task, 69 and 21 percent more facts learned, and the benefit surviving
the restriction's removal, reported by NN/g from Carroll's studies).

The repository ships fourteen command files today (`ls commands/`). During the
first fifteen minutes **three are offered**: `/brotherme-start`,
`/brotherme-status`, `/brotherme-next`. The other eleven are not disabled and
not hidden. They are not offered, and each surfaces at the moment its trigger
occurs:

| Command | Surfaces when |
|---|---|
| `/brotherme-decisions` | the first key decision is recorded |
| `/brotherme-handback` | the first key decision is recorded (in the same breath) |
| `/brotherme-view` | the first render exists, which is minute 4 |
| `/brotherme-brief` | the first catch-up is written |
| `/brotherme-review` | there is work to review |
| `/brotherme-deliver` | there is something to deliver |
| `/brotherme-handover-pack` | a second human is mentioned, or a handback is taken |
| `/brotherme-update` | never during the first run |
| `/brotherme-stop`, `/brotherme-auto`, `/brotherme-auto-status` | only in the flows that own them |

`commands/brotherme-help.md` today lists nine commands in one paragraph plus two
more in the same sentence. That paragraph is the wall LENS-B section 1.4 indicts
through Carbon's rule against covering multiple options at once. The change:
help asks one question first, and the full list moves behind the reference
answer. The honesty content in that file (what is verified, the export and purge
promises) is reference and explanation, and it stays reachable, one answer away,
rather than at minute zero.

### 5.4 The twelve first run rules, as gates

LENS-B Part 4 states twelve testable propositions. All twelve are adopted. Nine
are enforced by tests in section 13.2 (rules 1 to 7, 11, 12). Three are enforced
by content review of the command files because they govern chat text a test
cannot see (rules 8, 9, 10), and rule 10 is satisfied by L04's existing
PHASE_BOUNDARY trigger as section 5.1 explains.

---

## 6. THE INSIGHT BOX AND THE ALERT LADDER

### 6.1 The insight box: one shape, six slots, no optional slot

The box renders exactly one `insights` row (L04 section 5.1). It has six slots
in this order and none is optional. A five slot rendering is a test failure, not
a shorter box, because the missing slot is always CHANGES IF and that is the
slot that makes the claim falsifiable (LENS-C section 5.7).

    1  CLAIM        one sentence, the thing now believed          insights.claim
    2  BECAUSE      the evidence, with its class as a word        evidence, evidence_class
    3  INSTEAD OF   the alternative considered, and why not       alternatives
    4  CHANGES IF   the flip condition, in plain language         flip_condition
    5  CONFIDENCE   high, moderate or low, with its basis         confidence, confidence_basis
    6  YOUR MOVE    the handback line, always present, always last control_offered

Slot 6 is `bl.HANDBACK_OPTION_TEXT`, byte equal, never paraphrased.

**When it fires.** The box has one cadence and it belongs to the ledger, not to
this design: the half hour catch-up (L04 section 7) carries the newest DECISION
in "What I decided" and the newest open RISK in "What I am unsure of". This
design adds the rendering, not a second clock.

* **In chat (S3):** at most **one** box per response, the newest insight created
  after the previous briefing's `created_at`. "Already shown" therefore needs no
  new state: the briefing row is the marker, and derived state cannot go stale
  (L-S6).
* **In the page (S1):** every insight, newest first, `#insights`, six slots
  each, with the older ones inside the one permitted `<details>` depth (L-S3).

**The anti fatigue rule for boxes**, and it is one sentence: an insight never
carries a rung above FOR INFO on its own. If the same fact needs action, an
alert is emitted separately and points at the insight; the insight is not
promoted. Duplicating one fact as an alert and an independent box is exactly the
noise Google SRE's chapter warns about (LENS-C sections 2.2 and 5.7).

### 6.2 The alert ladder: four rungs, one interrupts

A rung is defined by **delivery behaviour first**, then by name, then by
appearance (LENS-C section 2.5, where MDN's `role="alert"` gives the ladder a
mechanical rather than a stylistic definition).

| Rung | Means | Delivery | Where | ARIA | Cap |
|---|---|---|---|---|---|
| **NEEDS YOU** | work is stopped until a human acts; names one action and one actor | interrupts: hook `systemMessage` plus `terminalSequence` on Stop, one line in chat, pinned at the top of the page | S4, S3, S1 | `role="alert"` | at most ONE on screen; a second queues |
| **AT RISK** | nothing is stopped, but something is likely to stop or to be wrong; names what would settle it | polite: appears in the next catch-up and in the page | S3 (catch-up only), S1 | `role="status"` | at most 3 shown, the rest counted |
| **FOR INFO** | true, worth knowing, requires nothing | silent: page only, plus a count line in chat | S1 | none | listed to 6, then counted |
| **SETTLED** | a thing that was open is now closed, with the evidence that closed it | silent and deliberately low contrast | S1 | none | no cap, collapsed by default |

**What distinguishes the rungs, mechanically.** `alerts_now(store, project_id,
now)` is a pure, ordered, deduplicated, capped function over rows that already
exist. There is no alerts table (L-S6). The rung is a query, never a feeling
(Google SRE: rules that generate alerts for humans should be simple to
understand and represent a clear failure, and "seems a bit weird" is never a
reason, LENS-C section 2.2).

    NEEDS YOU  =  consent not given
               |  an open key decision (Store.open_key_decisions, L04 6.3)
               |  an open founder step whose floor is in AUTONOMY_FLOOR_IDS
                    (tools/bm_store.py:3344)
               |  an unresolved alert row with requires_human true
                    (Store.list_alerts, tools/bm_store.py:12506)
               |  spend at or above a contract ceiling (Store.spend_totals,
                    tools/bm_store.py:13431)

    AT RISK    =  an open RISK insight nothing supersedes
               |  an open dispatch older than DEFAULT_DISPATCH_TIMEOUT_SECONDS
               |  a forecast whose range no longer contains the remaining work
               |  a non zero skipped-row count from active_minutes_since
                    (L04 section 7.1 requires that count be disclosed)

    FOR INFO   =  counts: gates passed of total, spend against ceiling,
                  findings by rung, units accepted of planned

    SETTLED    =  a decision superseded by a later DECISION or by a HANDBACK,
                  a gate that moved from failing to passing, a resolved alert

If a condition cannot be expressed as such a query, it is not an alert.

### 6.3 The four anti fatigue rules

1. **Only NEEDS YOU interrupts.** Directly from AHRQ: make only high level
   alerts interruptive (LENS-C section 2.1). Everything below the top rung is
   available, not thrown.
2. **One NEEDS YOU at a time, and at most two rungs in any chat message.** From
   GitHub's one or two per article cap and MDN's warning that several alerts at
   once create bad user experiences (LENS-C sections 2.3 and 2.5). A second
   NEEDS YOU queues behind the first and is counted, not shown.
3. **No promotion by age.** An AT RISK does not become a NEEDS YOU because it
   was ignored. It becomes NEEDS YOU only when its blocking condition becomes
   true. Time based escalation is the classic manufacture of noise.
4. **One interrupt per catch-up window, per cause.** The dedupe key is
   `(rung, kind, subject, row_id)`. A key already interrupted since the previous
   briefing's `created_at` is suppressed and counted, not re-thrown. This is
   derived from rows exactly like the rest, so there is no read state to get
   wrong.

And one negative rule: **SETTLED is quiet and uncoloured.** From GOV.UK's task
list change, which moved completed items to plain black text so colour draws the
eye to what still needs action (LENS-C section 3.7). Do not paint the done
things green. Spend the colour budget on the work.

The ladder has no fifth rung. Adding one requires deleting one. There is no TIP
and no CAUTION: a tip is documentation and belongs in `#help` (LENS-C section
5.4, following MDN, which dropped exactly those and runs fine).

### 6.4 The evidence class marking

One function already exists for this, `bl.evidence_label` (L04 section 4.4), and
this design adds no second vocabulary.

| evidence_class | Founder facing prefix | Rendered in the box as |
|---|---|---|
| EXECUTED | `verified by command:` | class token `EXECUTED`, plus the command |
| MEASURED | `measured:` | class token `MEASURED`, plus the number observed |
| READ | `verified by inspection:` | class token `READ`, plus the file and line |
| REASONED | `my reasoning, not verified:` | class token `REASONED, not tested`, muted ink, no rung bar |

Three hard rules:

1. **The prefix is applied by the renderer, never by the author**, so a REASONED
   claim cannot reach any surface without it (L04 law L4).
2. **REASONED never renders as settled.** In addition to the prefix, the box
   prints the literal words "not tested" beside the class token and drops the
   rung bar entirely (LENS-C section 5.7 rule 1). Two independent markings,
   because this is the founder's own non negotiable.
3. **REASONED can never be the Evidence field of a status view.** L04 section
   3.4 already routes Evidence to the newest EXECUTED or MEASURED insight and
   says "no executed evidence recorded yet" when there is none, never dressed up
   as a read. The page uses the same collector, so it inherits this rather than
   re-deciding it.

### 6.5 The terminal rendering, which must work with zero styling

ASCII only. No box drawing characters, no emoji. The repository runs a Windows
CI job (.github/workflows/tests.yml:179), and non ASCII in terminal output is a
class of failure this project has already paid for. Four non colour channels
survive: the WORD, the marker, the indent, and (in HTML only) the bar weight and
style.

    [!!] NEEDS YOU  Setup consent not given. Nothing has been written yet.
         Say "go ahead" to create the project files, or "not yet".

    [! ] AT RISK    The retry test has failed 3 of 9 runs.
         A 20 run repeat would settle whether it is the race or the fixture.

    [ i] FOR INFO   4 gates passed of 7. Budget 18k of 40k tokens.

    [  ] SETTLED    The mutation calibration is closed. 0 of 61 tests went red.

An insight box in chat, in full:

    [ i] FOR INFO   INSIGHT, calibration

      The retry test was decorative. It passed with the retry logic deleted.
      BECAUSE      measured: I deleted the retry branch in a scratch copy and
                   ran the suite, 0 of 61 tests went red.  [MEASURED]
      INSTEAD OF   Leaving it and adding a second test. Rejected: two tests
                   that both pass on broken code are worse than one.
      CHANGES IF   A test fails against that mutation. Then the coverage is
                   real and this insight is wrong.
      CONFIDENCE   High, because it is a measurement and it repeats.
      YOUR MOVE    Hand this back to me: I take this decision and the work
                   under it, and BrotherMode records where it stopped and
                   what it would have done.

That reads correctly in a monochrome terminal, in a screen reader, and pasted
into an email, which is L-S5 doing its job.

---

## 7. THE DIAGRAM VOCABULARY

Five shapes. Nothing else is ever drawn. Every one is generatable from store
rows by standard library Python, and every one exists because a specific founder
question has no other good answer.

**One model, two emitters.** `bm_visual.py` builds a `Diagram` (a plain dict
with `shape`, `nodes`, `edges`, `title`, `desc`, `caption`), and two functions
render it: `to_svg(diagram, theme)` for the page and `to_text(diagram)` for the
terminal. `shape` must be one of the five names; a sixth raises at construction.
That is how the ban is enforced by code rather than by prose, which is LENS-C's
own point that bans enforced by prose get broken in month three by someone with
a really good reason for a pie chart.

### 7.1 D1, the pipeline. "Where are we?"

    Question   Where are we?
    Shape      3 to 7 stages in one line, left to right, exactly one marked NOW
    Rows       the controller run state, the phase, unit statuses
    Surfaces   page (drawn), chat (one text line)
    Caps       7 stages, 7 nodes, 6 edges

The current stage is marked three ways: the word NOW in its label, a heavier
stroke, and a different fill. That is L-S4 inside a single node. Completed
stages carry the word "complete", unreached ones carry "waiting".

### 7.2 D2, the gate ladder. "What has to be true before this ships?"

    Question   Why is this not shipped yet?
    Shape      one column, the ordered gates, each with passed, failing or not run
    Rows       gate results for the current unit, open founder steps with a floor
    Surfaces   page (drawn), chat (the count line only)
    Caps       9 nodes, 8 edges

A failing gate is the only node permitted the stop colour, and it carries the
word BLOCKED next to it. When there are more gates than the cap, the generator
**aggregates and says so in the caption**: "3 of 14 gates shown, the 3 that are
not passing" (LENS-C section 5.3). It never shrinks the font.

### 7.3 D3, the lane map. "Who holds the pen?"

    Question   Who owns this step right now?
    Shape      2 to 4 lanes, one per owner, single direction throughout
    Rows       work record ownership, open dispatches, open founder steps
    Surfaces   page (drawn), chat (one sentence)
    Caps       4 lanes, 9 nodes, 12 edges

Drawn only when ownership is the important question, which is mermaid's own
criterion for a swimlane (LENS-C section 1.4). When every open item has the same
owner, the section renders its empty state instead, which reads: "You hold the
pen on everything open right now."

### 7.4 D4, the decision fork. "You are being asked something."

    Question   What are you deciding, and what happens either way?
    Shape      one question node, two or three outcomes, the last always the handback
    Rows       one open key decision plus the insight row behind it
    Surfaces   page (drawn plus real controls), chat (lettered options via AskUserQuestion)
    Caps       4 nodes, 3 edges, 3 outcomes of which one is the handback

**The handback branch is always present, always last, always the emphasised
node.** L04 section 9.3 already makes a key decision without a handback
unwritable at the store level; this makes it undrawable too, and section 13.2
asserts it on every one of the five decision classes.

### 7.5 D5, the count row. "How much, against what limit?"

    Question   How much, against what limit?
    Shape      labelled bars with the raw numbers written on them
    Rows       gate results, spend totals against both ceilings, findings by rung
    Surfaces   page (HTML bars with progressbar semantics), chat (text bars)
    Caps       6 rows

Not a drawing, so it does not count against the four per page cap. In the page
each bar carries `role="progressbar"` and `aria-valuetext="4 of 7 gates
passed"`, and the number is printed inside the bar, so the bar is decoration and
the number is the content (LENS-C section 3.5).

Chat form, which must be as informative as the page form:

    Gates      passed 4 of 7   [####----]
    Budget     18k of 40k tokens, 26 of 90 minutes
    Findings   needs you 1, at risk 3, for info 6

### 7.6 The rule that decides which shape, and the ban list

`diagram_for(question)` is a closed mapping, not a judgement:

| If the founder's question is | Draw |
|---|---|
| where are we, how far along | D1 |
| why is this not done, what is blocking | D2 |
| who is doing what, who owns this | D3 |
| what am I being asked | D4 |
| how much, against what limit | D5 |
| anything else | nothing |

Banned, with the reason, adopted verbatim in effect from LENS-C section 5.1:
sankey (experimental, and this product has no flow magnitude question), gantt
(implies dated commitments this product cannot honour), pie (angle comparison is
the weakest encoding available), mindmap and timeline (author shapes, not reader
shapes), class, entity relationship and sequence (they describe code and data
models, which the founder explicitly does not read), quadrant, xychart and radar
(no store row behind them, so any use would be hand authored and would violate
L-S1), fork, join and concurrency separators (UML machinery with no meaning to
an untrained reader).

**Mermaid is deferred, with the reason.** LENS-D section 2.3 is a split verdict:
the `Artifact` tool contract in that session states artifacts render mermaid
natively, but the string does not appear on the Claude Code artifacts page nor
anywhere in the bundled skills payload, and no published page corroborates it.
Inline SVG is unambiguously supported. So the page draws SVG. A `to_mermaid`
emitter is not built in this design because it would have no consumer: the one
place mermaid already ships is `Documentation/`, generated by tools/bm_docs.py,
which section 0.2 keeps shut. The model exists, so adding the emitter later is
one function and one test, not a redesign.

### 7.7 Wording and escaping rules for anything drawn

* Node labels are noun phrases plus a status word, never sentences and never
  identifiers. "Build, NOW", not "wr_8813 in_progress".
* Every label carries its status as a WORD, never as colour alone and never as a
  bare glyph (WCAG 1.4.1, level A).
* Labels go on the drawing, not in a separate key, because matching the same
  colour in two distant places is extremely difficult (Colour Universal Design,
  LENS-C section 3.3).
* Prose that introduces a drawing never says "the red one". It names the thing
  and its position (same source).
* Record ids, hashes and paths are permitted in the page's text and never inside
  a drawn node.
* Labels are sanitised by `_flat`, copied in shape from tools/bm_docs.py:283 to
  292, and then XML escaped through `xml.sax.saxutils.escape`. That file's own
  comment records why this is not theoretical: a record called "-h" exists in
  this project's store, created by a probe that took a help flag as a name.
* SVG geometry is computed from character counts at a fixed advance width, never
  measured, so output is deterministic on every platform.

---

## 8. THE HANDBACK, MADE VISIBLE

### 8.1 The standing offer, as a surface

L04 makes the handback unavoidable in the data (a key decision that offers no
handback cannot be written, section 9.3) and unavoidable in the decision card
(always the last option). This design makes it **unavoidable on screen, whether
or not a decision is open**.

`#your-move` is a permanent section of the page. It has two states, both
generated:

**When a key decision is open:** the decision card, the drawn fork (D4) with the
handback as the emphasised terminal node, and one control per option. The
handback control is not a link and not a form: it is a **copy as prompt**
control, which is Anthropic's own documented pattern for handing a page result
back into a session (LENS-D section 2.8). It reveals, inside the one permitted
`<details>`, the exact text to paste:

    /brotherme-handback

    Take back: <the decision subject>
    Decision id: <insight_id>
    Why: <the founder types this>

**When no decision is open:** the same panel, with the standing sentence and the
same command, plus one line of what taking it would do right now. The wording of
the offer itself is `bl.HANDBACK_OPTION_TEXT`, byte equal in both states, and a
test asserts the string appears in every rendered page regardless of fixture.

This matters because LENS-A T8 is explicit that the take over affordance needs a
control and a promise about what survives, not an invitation. The promise
sentence, generated from L04 section 9.4's five acts in plain words:

    Nothing is lost. Your authorisation is paused so no further automatic work
    can start, the work in progress is parked with a note about what to do next,
    what BrotherMode would have chosen is recorded, and a page for whoever picks
    it up is written.

### 8.2 The developer brief as a rendered page

L04 section 10 generates `Handover/HANDBACK-<id>.md`, eight sections, from rows,
with the cut that makes it reproduce byte for byte a week later. This design
adds one HTML rendering of **the same eight sections from the same rows**,
written to `Handover/HANDBACK-<id>.html`.

It is not a prettier duplicate, and the test that keeps it honest is stated as a
requirement rather than a hope:
`test_the_html_brief_carries_every_section_and_every_trace_tag_of_the_md`
asserts that the set of section headings and the set of trace tags in the HTML
equal those in the markdown. If the markdown gains a section, the HTML goes red.

What the HTML adds over the markdown, and it is only presentation:

* the eight sections as a numbered, anchored reading order;
* the decision that was in front of us drawn as D4, so the road not taken is a
  picture and not a paragraph;
* the files (section 5 of the brief) as a plain list with the write scope of any
  unit that is not done, in one `overflow-x` container;
* the reproduction (section 6) as a copy as prompt block, so the developer has a
  command to run rather than a description of one;
* the evidence class label beside every claim, with REASONED carrying "not
  tested" (section 6.4).

The brief page is published the same way as the project view, on request, and
its URL is stored under `kind = 'DEVELOPER_BRIEF'` (section 11.2). The handover
pack's `60-HANDBACKS.md` is untouched: L04 already asserts the standalone brief
and the pack section are the same bytes, and adding a third representation that
is a projection of the first keeps that property intact.

---

## 9. HELP AT THE POINT OF NEED

### 9.1 The Diataxis cut

Today the tutorial, the how to, the reference and the explanation are mixed
together in `commands/brotherme-help.md` and the README (LENS-B section 1.7).
The split, and each half has an owner:

| Mode | Where it lives | Owner |
|---|---|---|
| **Tutorial** | the first fifteen minutes, section 5, one path, no alternatives, must work every time | `commands/brotherme-start.md` |
| **How to** | what `/brotherme-next` answers, task by task | `commands/brotherme-next.md` |
| **Reference** | the live project view and the handover pack, generated from rows, never hand written | `bm-view`, `bm-lead handover-pack` |
| **Explanation** | the deep tour, opt in, never on the first run | `skills/brotherme/SKILL.md:42` |

`skills/brotherme/SKILL.md:42` already describes a deep tour that builds ONE
HTML artifact. That instruction is rewritten to point at the generated page
instead of at a page the model composes freehand, which converts the most
expensive and least reliable surface in the product into a projection of rows.
Its existing honest limit at line 44 (a project with no record gets a static
tour, and the page says which one it is showing) is kept and is now enforced by
the empty states in section 4.4.

### 9.2 The moment something fails

Triggers are detectable from the store and the session with no daemon and no new
dependency (LENS-B section 3):

* a mechanical command refused;
* the same command failing twice with the same error;
* a decision open with no founder input for N minutes;
* a gate failing;
* the same manual action taken three times (Atlassian's inflection point).

On any trigger, **no log is printed**. The founder cannot read logs and should
never have to. What is emitted is the five part block, which is the same
structure clig.dev, Elm's compiler errors and NN/g's ninth heuristic all
converge on (LENS-B section 1.8):

    1  one line of context: what was being attempted, in the founder's words
    2  the actual thing, shown as it happened
    3  one hint naming the cause in plain language, not the system's terms
    4  one suggested next action, phrased as something the founder can say
    5  ONE expander, "show me exactly what happened", revealing the raw output

Rules:

* Part 5 is the only place a raw log may ever appear, in any surface. It is pull,
  not push (NN/g heuristic 10).
* It is also the one permitted `<details>` depth in the page (L-S3), so a raw
  log cannot be nested inside another expander.
* The four sections of an error card in references/kickoff.md:70 to 84 (What
  happened, Impact, Recommended action, What remains safe) are the shape parts 1
  to 4 take when the failure reaches the founder as a card rather than as a
  block. They are not a competing format: part 3 is "What happened" plus
  "Impact", part 4 is "Recommended action", and "What remains safe" is mandatory
  in both.

**Every refusal is rewritten.** `REFUSAL_HELP` is one module dict in
`bm_visual.py`, keyed by the reason code strings the store emits, valued by
`(context, hint, next_action)`. `bm-view explain <reason_code>` prints one, and
the block above is assembled from it. The test enumerates the reason codes the
store can emit (L04 section 6.2 gives sixteen for the insight write path alone,
each with a reason code) and fails on any code with no entry. That is L-S9 made
mechanical rather than aspirational, and it is LENS-B rule 7.

### 9.3 Help inside the page, contextual and generated

`#help` is generated from one map, `SECTION_HELP`, keyed by the same
`anchor_id` values as `VIEW_SECTIONS`, so a new section cannot ship without its
help line. Three rules:

1. **Pull, not push.** Each section carries a one line "what this is" under its
   heading, always visible, never a modal. Anything longer sits in `#help`
   behind an in page anchor, which is the same level, not a third.
2. **Never reference something not on screen.** Atlassian's rule (LENS-B section
   1.5): a help line may name only elements present in the rendered page. The
   test asserts every anchor referenced from a help line exists in the document.
3. **No tour, no coach marks, no overlay.** They are dramatically overused, they
   are justified mainly for a genuinely novel interaction paradigm, and
   explicitly not for new users signing up (LENS-B section 1.5). The one
   defensible trigger, Atlassian's inflection point, is section 9.2's fifth
   trigger and it fires from observed behaviour, not from a timer.

---

## 10. WHAT THIS DOES NOT DO

Drawn from LENS-D, and every entry is a limit the founder should be able to read
in `docs/KNOWN-LIMITS.md` in these words.

1. **The page is not live.** It is a snapshot. It cannot read your project
   records when you open it. Freshness comes from the page being written again,
   which happens on command and when a session stops, and from Claude
   republishing it, which is a request and not a guarantee (LENS-D sections 2.7
   and 5).
2. **The published page may be unavailable to you entirely.** Publishing needs a
   Pro, Max, Team or Enterprise plan, a session signed in with `/login`, the
   Anthropic API as the model provider, an organisation without CMEK, HIPAA or
   Zero Data Retention, and Claude Code 2.1.183 or later. It is off by default in
   Agent SDK, GitHub Action and MCP server contexts. Sessions using an API key,
   a gateway token or a cloud provider credential cannot publish at all (LENS-D
   section 2.10). When any of these fails, you still get the file on disk, and
   the command says which one you got.
3. **The page holds no state.** Nothing you do on it is saved. There is no
   storage capability in Claude Code artifacts; the roster measured on this
   machine is `downloads` and `mcp` only (LENS-D section 2.6). This is a
   feature: it makes it impossible for the view to become a second truth.
4. **Nothing on the page can act on your project.** There is no path from a
   button back into the running session. Handback is a copy as prompt control
   and a paste, which keeps you in the loop by construction (LENS-D section 2.8).
5. **There are no pictures in the chat in the Claude Code CLI.** Section 3.4.
6. **BrotherMode cannot install the status line or the clickable footer links.**
   Those are your settings, not a plugin's (LENS-D section 6). Section 14 offers
   both as a one line change you make.
7. **BrotherMode cannot show you your application running.** It does not run it,
   has no browser, and will not claim otherwise (LENS-A W7).
8. **Mermaid rendering inside a Claude Code artifact is unconfirmed** and this
   design does not rely on it (section 7.6).
9. **`SendUserFile` to your phone needs Remote Control connected or a managed
   cloud session** (LENS-D section 7), so the page reaching you when you are away
   is not promised.
10. **Two smaller unknowns, recorded rather than hidden.** Whether
    `ReportFindings` can be driven outside code review, which would be the only
    native structured list renderer in the harness; and what content types
    `MessageDisplay.displayContent` accepts, which is the only hook that alters
    rendered output (LENS-D section 10). Neither is used by this design, and
    both are listed in section 14 as probes worth five minutes each.

---

## 11. THE STORE SURFACE: SCHEMA 17

### 11.1 Why a table at all

Exactly one fact must survive a session: the URL of the published page, per
project and per kind. Without it, "a new session always creates a new artifact
rather than updating an existing one" (LENS-D section 2.5), and the founder
accumulates dead pages. The fingerprint is stored beside it so `--if-stale` and
"do we need to republish" are the same comparison.

### 11.2 The `views` table

    views                   (schema 17, additive)
      view_id               immutable
      created_at
      project_id
      kind                  PROJECT_VIEW | DEVELOPER_BRIEF
      rel_path              the generated file, relative to the project root
      fingerprint           12 hex characters of sha256 over the rendered body
      artifact_url          the published URL, or empty
      published_at          when it was last published, or empty
      subject               the handback insight_id for a brief, else empty
      session_id, actor

Append only, exactly like `insights` (L04 law L2): no `UPDATE` and no `DELETE`
outside `purge_project`, proven by an ast guard copied from
tools/test_bm_store.py:16246. `latest_view(project_id, kind)` returns the newest
row. A republish appends.

New store members, all in `tools/bm_store.py`:

| Symbol | Note |
|---|---|
| `SCHEMA_VERSION` | 16 to 17, line 81 |
| `VIEW_KINDS`, `VIEW_FIELDS` | module tuples |
| `_TABLES_V17`, `_TABLES_BY_VERSION` | additive, beside the L04 entries |
| `_VIEW_DDL`, `_VIEW_INDEX_DDL` | beside the L04 DDL constants |
| `_migrate_16_to_17` | additive, one table and one index |
| `Store.record_view` | `(project_id, view, actor) -> {'view_id','kind','fingerprint'}` |
| `Store.latest_view` | `(project_id, kind, raw=False) -> dict or None` |
| `Store.list_views` | `(project_id, kind=None, limit=None, raw=False)` |
| `ReadOnlyStore` | three pass throughs |
| `Store.purge_project` | one delete, one `removed` key `"views"` |
| `_DUMP_SAFE_COLUMNS` | `rel_path` and `artifact_url` withheld as length markers; ids, kind and fingerprint whole |

Six refusals on `record_view`, each with a reason code and each writing nothing:

    V1  unknown-project        the project row does not exist
    V2  bad-view-kind          kind is not in VIEW_KINDS
    V3  path-escape            rel_path does not resolve inside the project root
                               through bs.safe_project_path (tools/bm_store.py:5072)
    V4  bad-fingerprint        not exactly 12 lowercase hex characters
    V5  bad-artifact-url       non empty and not an https URL
    V6  unknown-field          a key outside VIEW_FIELDS

### 11.3 The purge pin

`tools/test_bm_project.py:1353`'s pinned `removed` dict gains `"views": 0`, and
`TestViewPurgeLeavesNoOrphans` adds the non zero case. The dict is pinned by
exact equality precisely so a schema that adds a purged table without adding its
key turns the test red. Adding the key is the pin performing its designed
function, and coverage strictly increases.

### 11.4 The consent door

`bm_view.py` copies L04 section 8.4's construction exactly: `_store_or_refuse`
is the ONLY store constructor in the file, it refuses without consent, and
`main` computes consent before dispatching the `COMMANDS` dict. A writer who
forgets a check cannot obtain a store handle at all.

Additionally, and this is specific to a renderer: **no file is written before
consent either.** `bm-view render` writes nothing, publishes nothing and creates
no directory until `is_consented` is true. `TestConsentIsTheOnlyDoorForTheView`
runs every subcommand with `HOME` pointed at a fresh directory and asserts zero
files appear under `HOME` and under the project.

`tools/test_bm_consent.py:471`'s
`test_no_wired_command_of_any_module_writes_before_consent` goes red the moment
hooks.json names `bm-view` and the module has no gate. That RED is the failing
first evidence for this half of the design (section 15 step 1).

---

## 12. INVENTORY

### 12.1 tools/bm_visual.py (NEW), the vocabulary

| Symbol | Note |
|---|---|
| `TOKENS_LIGHT`, `TOKENS_DARK` | LENS-C section 5.6's measured tables, verbatim |
| `RUNGS` | `("NEEDS YOU", "AT RISK", "FOR INFO", "SETTLED")`, ordered |
| `RUNG_DELIVERY` | rung to `("interrupt"\|"polite"\|"silent", aria_role_or_empty, cap)` |
| `STATUS_LEXICON` | the closed set of status words any surface may print |
| `SHAPES` | `("pipeline", "gates", "lanes", "fork", "counts")` |
| `CAPS` | per shape node, edge and lane maxima, LENS-C section 5.3 |
| `Diagram` | `diagram(shape, nodes, edges, title, desc, caption)`, validates against `SHAPES` and `CAPS` or raises |
| `diagram_pipeline`, `diagram_gates`, `diagram_lanes`, `diagram_fork`, `counts_rows` | `(collected_status) -> Diagram`, pure, no store access |
| `diagram_for(question_kind)` | the closed mapping of section 7.6 |
| `to_svg(diagram)`, `to_text(diagram)` | the two emitters; `to_svg` emits no colour |
| `_flat(text, limit)` | label sanitiser, shape from tools/bm_docs.py:283 to 292 |
| `render_insight_box(insight, medium, ic=False)` | six slots, medium in `("text","html")` |
| `render_alert(alert, medium)` | the four rung renderings |
| `alerts_now(store, project_id, now)` | pure, ordered, deduplicated, capped |
| `surface_for(item)` | section 3.3's first match router |
| `REFUSAL_HELP` | reason code to `(context, hint, next_action)` |
| `failure_block(reason_code, attempted, raw)` | the five part block |
| `contrast_ratio(a, b)`, `relative_luminance(hex)` | the WCAG functions, used by the token test |
| `THEME_CSS` | the one stylesheet block, both themes, the only colour in the product |

### 12.2 tools/bm_view.py (NEW), the page and the CLI

| Symbol | Note |
|---|---|
| `COMMANDS` | five entries; read only inside `main` |
| `main(argv)`, `cli()` | shapes copied from tools/bm_project.py:1529 and 1555 |
| `_out`, `_err`, `_parse`, `_require`, `_print_json`, `_root`, `_actor` | copied from tools/bm_project.py:215 to 322 |
| `ConsentMissing`, `_consent_state()`, `_store_or_refuse(kv, write)` | section 11.4 |
| `VIEW_SECTIONS` | the twelve tuples of section 4.2, shape from tools/bm_docs.py:139 |
| `EMPTY_STATES` | one entry per section, four fields each, section 4.4 |
| `SECTION_HELP` | one entry per section, section 9.3 |
| `SETUP_MILESTONES` | the eight detectors of section 4.4 |
| `render_page(status, alerts, insights, briefings, decisions)` | the whole document, pure |
| `fingerprint(body)` | first 12 hex of sha256 |
| `render_developer_brief_html(store, handback_insight)` | section 8.2 |
| `cmd_render`, `cmd_url`, `cmd_doorway`, `cmd_explain`, `cmd_brief_page` | `(argv) -> int` |

`bm-view` subcommands:

    bm-view render      --project-id ID [--if-stale] [--out PATH] [--json]
    bm-view url         --project-id ID [--kind K] [--set URL] [--json]
    bm-view doorway     [--json]
    bm-view explain     --reason CODE [--json]
    bm-view brief-page  --project-id ID --insight-id ID [--json]

`doorway` writes nothing and needs no store, which is what makes it usable at
minute zero (section 5.1). It is the only subcommand exempt from the consent
gate, and the test asserts it writes zero files.

### 12.3 Non code files

| File | Change |
|---|---|
| `commands/brotherme-view.md` | NEW. Runs `bm-view render`, states in plain words that the page is a snapshot, names the three ways it updates, and carries the section 3.4 sentence about pictures in the chat |
| `commands/brotherme-help.md` | CHANGED. The nine command paragraph becomes one question plus a reference answer, section 5.3. The honesty content moves into the reference answer unchanged |
| `commands/brotherme-start.md` | CHANGED. The doorway block at minute zero, the consent sentence including the silent republish disclosure, and the first render at minute 4 |
| `commands/brotherme-status.md` | CHANGED. One line offering the page, after the eight fields, never before them |
| `commands/brotherme-handback.md` | CHANGED. Names the copy as prompt control and the brief page |
| `skills/brotherme/SKILL.md` | CHANGED. Line 42's deep tour builds from `bm-view render` instead of composing a page freehand; the stored URL is read and republished to; line 44's honest limit is kept |
| `references/visual-surface.md` | NEW. The register file for this vocabulary: the four surfaces and the choosing rule, the five shapes and their caps, the four rungs and their delivery, the six slots, the empty state anatomy, and the two level rule. Every user facing surface must obey it, and section 13 tests it |
| `references/terminology.md` | CHANGED. Five new rows BEFORE the words may appear anywhere, per its own law at lines 53 to 55: live project view, insight box, alert rung, empty state, fingerprint |
| `references/status-view.md` | CHANGED. One short paragraph saying the eight fields are unchanged and that the page is the same eight fields plus what the page adds, never a different status |
| `capabilities.status.json` | CHANGED. Four rows: `live-project-view`, `visual-onboarding`, `alert-ladder`, `visible-handback`, each naming a path that exists |
| `README.md`, `docs/ROADMAP.md` | CHANGED, generated blocks only, by running bm-docs |
| `docs/KNOWN-LIMITS.md` | CHANGED. One new dated section carrying section 10 verbatim in plain words |
| `SECURITY.md` | CHANGED. One paragraph: what the published page contains, that it is a private URL on claude.ai, that publishing is permission gated on first publish and silent afterwards, and that the local file is the primary artefact |
| `hooks/hooks.json` | CHANGED. Two Stop entries: `bm-view render --if-stale`, and `bm-view alert --tick` which is the only JSON emitting hook on that event |
| `pyproject.toml` | CHANGED. `bm-view = "bm_view:cli"` in `[project.scripts]`, `"bm_view"` and `"bm_visual"` in `py-modules`. Both mandatory: tools/test_bm.py:5409 and 5417 fail if the shipping tools and that list disagree |
| `.github/workflows/tests.yml` | CHANGED. Two steps, one per new suite. Mandatory: tools/test_all.py:48 and 473 enforce that every suite in `SUITES` has a step |
| `tools/test_all.py` | CHANGED. `"test_bm_visual.py"` and `"test_bm_view.py"` added to `SUITES`, after `test_bm_lead.py` |

---

## 13. TEST PLAN

Every class below is NEW. Every one is written FIRST, run against the untouched
tree, and its failure captured to
`docs/program/absolute-lead/evidence/L05/RED-L05-tests.txt` in four labelled
blocks (visual, view, store, consent) with per class failure and error counts. A
class that PASSES on the untouched tree is not evidence and must be rewritten
until it reproduces the gap it claims.

### 13.0 How you test a generated visual

Not by pixels. Three mechanisms, all standard library, and each one is stated
here because "test the HTML" otherwise degrades into asserting substrings.

1. **Parse, do not grep.** `tools/test_bm_view.py` ships one small
   `html.parser.HTMLParser` subclass, `Doc`, that builds a tree of
   `(tag, attrs, text, children)`. Every assertion is a query against that tree:
   `doc.by_id("needs-you")`, `doc.all("figure")`, `doc.attr_values("role")`,
   `doc.text_of("#next-step")`. A substring assertion on raw HTML is banned in
   this suite and an ast guard in `test_bm_view.py` fails on
   `assertIn(<string literal>, html)`.
2. **Content assertions are set equalities against rows, in both directions.**
   Copied from `test_every_register_entry_reaches_the_page`
   (tools/test_bm_docs.py:3795 to 3805), whose docstring states the principle:
   the render could agree with itself and still drop a row. Forward: the set of
   row ids the store says belongs in a section equals the set of trace tags
   found there. Backward: every trace tag on the page resolves to a row of the
   matching kind.
3. **Structural invariants are computed, not eyeballed.** Node counts, edge
   counts, `<details>` nesting depth, the count of elements carrying
   `data-bm-next-step`, the absence of `<script`, the presence of `<title>` and
   `<desc>` inside every `<svg role="img">`, and the contrast ratio of every
   token pair.

### 13.1 tools/test_bm_visual.py

| Class | Tests | Failing first evidence it must produce |
|---|---|---|
| `TestContrastTokens` | 3 | Re-runs the WCAG computation over `TOKENS_LIGHT` and `TOKENS_DARK`; every pair clears its floor (4.5:1 text, 3:1 non text) with no rounding; plus the two sanity assertions, 21.0 for black on white and 4.54 for #767676 on white, so a broken formula cannot pass silently. The light `settled` rule on its own tint clears by 0.07 and has no margin, so this test is the thing that stops a future tweak from failing WCAG quietly |
| `TestColourIsNeverAlone` | 4 | `THEME_CSS` removed from a rendered page, every status still recoverable; every status bearing element carries a word from `STATUS_LEXICON`; `to_svg` output contains no `fill=`, `stroke=` or `style=` attribute carrying a colour; the four rungs are distinguishable with the stylesheet gone |
| `TestDiagramCaps` | 6 | One per shape: exceeding the node, edge or lane cap raises at construction; a seventh pipeline stage aggregates and the caption says so; `Diagram` with a shape outside `SHAPES` raises |
| `TestDiagramEscaping` | 4 | Labels containing `<`, `&`, `"`, `'`, a leading dash, and the word `end` survive both emitters intact and produce parseable output; a record named `-h` renders as a label and not as syntax |
| `TestSvgAccessibilityPair` | 3 | Every `to_svg` output has `role="img"`, a non empty `<title>` and a non empty `<desc>`, wired by `aria-labelledby` and `aria-describedby`; the caption text is non empty and differs from the title |
| `TestAlertsNowIsDerivedAndCapped` | 8 | Never more than one NEEDS YOU; never more than two rungs for one chat message; a cleared condition removes its alert with no dismissal call; the dedupe key suppresses a repeat within the window and counts it; an AT RISK never promotes by age no matter how old; ordering is stable across two calls on the same rows; a condition not expressible as a query cannot produce an alert; SETTLED carries no colour token |
| `TestInsightBoxHasSixSlots` | 5 | Every slot non empty in both media; a five slot render fails; slot 6 is byte equal to `bl.HANDBACK_OPTION_TEXT`; a REASONED row renders the prefix AND the words "not tested"; a REASONED row carries no rung bar |
| `TestSurfaceRouter` | 6 | One per branch of section 3.3, plus: an unknown item kind raises rather than defaulting |
| `TestEveryRefusalIsRewritten` | 2 | Every reason code the store can emit has a `REFUSAL_HELP` entry, enumerated from the store module rather than from a hand list; `failure_block` output has all five parts and exactly one expander |
| `TestTextAndHtmlCarryTheSameFacts` | 3 | For each shape, the set of status words in `to_text` equals the set in `to_svg`; the insight box's six slot values are identical across media; a count row's numbers are identical |
| `TestNoNonAsciiInTerminalOutput` | 1 | Every string any `medium="text"` path can emit is ASCII only, so a Windows terminal cannot produce mojibake |

### 13.2 tools/test_bm_view.py

| Class | Tests | Failing first evidence |
|---|---|---|
| `TestConsentIsTheOnlyDoorForTheView` | 5 | Five ast assertions of the one door pattern, plus: with `HOME` fresh, every subcommand except `doorway` creates zero files; `doorway` creates zero files too and needs no store |
| `TestEverySectionRenders` | 4 | `VIEW_SECTIONS` has twelve entries; every one appears in the document by anchor; a section that renders blank fails; the anchors are unique |
| `TestEmptyStatesAreDesigned` | 6 | Every `empty_state_key` has an `EMPTY_STATES` entry; exactly one action each; no title contains no, none, nothing or empty; no body exceeds 140 characters; no left column term of references/terminology.md appears in any of them; every action command is in the offered set |
| `TestExactlyOneNextActionOnThePage` | 3 | Exactly one element carries `data-bm-next-step` on every fixture including the empty project; the text is byte equal to `bl.next_action`'s triple; a second action anywhere in the document fails |
| `TestTheHandbackIsAlwaysVisible` | 4 | `bl.HANDBACK_OPTION_TEXT` appears in every rendered page, decision open or not; the fork drawing's last outcome is the handback for all five decision classes; the copy as prompt block names the decision id; `#your-move` exists in the empty project fixture |
| `TestTwoLevelsAndOneExpander` | 3 | No `<details>` contains another `<details>`; the raw output expander is the only one carrying a log; the count of distinct disclosure depths is at most one |
| `TestSelfContained` | 5 | The string `<script` does not appear; no `src=`, `href="http`, `@import` or `url(` referencing an external host; no data URI image; the rendered size is under 16 MiB on a large fixture; every wide element sits in an `overflow-x` container |
| `TestThemeAware` | 3 | Both `prefers-color-scheme` blocks exist; `:root[data-theme="dark"]` and `:root[data-theme="light"]` overrides exist and come after the media query; every token used in the document is defined in both themes |
| `TestPageTracesToRows` | 6 | Forward and backward set equality per section; a REASONED row's line carries the prefix; no number appears that the store does not hold; a claim with no trace tag fails |
| `TestByteStableAndHonestlyStale` | 4 | Two renders with no intervening write are byte identical; no render clock appears anywhere in the document; the fingerprint changes when a row changes and not otherwise; the newest record time shown equals the newest row read |
| `TestThreeRenderersOneCollector` | 3 | Every field the founder text render, the IC text render and the HTML render share carries a byte identical value; extends L04's S2 fixture rather than duplicating it; the HTML render calls no collector of its own (ast) |
| `TestTheHtmlBriefMatchesTheMarkdown` | 3 | Section headings set equality with `Handover/HANDBACK-<id>.md`; trace tag set equality; adding a section to the markdown turns this red |
| `TestPlainLanguageHoldsOnThePage` | 2 | No left column term of references/terminology.md:10 to 34 appears in the founder facing page; the IC page is allowed to contain them |
| `TestFirstFifteenMinutes` | 5 | A behavioural fixture from an empty folder: at most three commands are offered before the first unit completes; the doorway writes nothing; the first render happens after consent and not before; the setup counter reads 2 of 8 at minute 4 and every increment traces to a row; the whole path runs to completion with no branch and no unscripted question |
| `TestNoSQLGuardAndNoSecondCollector` | 2 | No SQL shaped literal and no `sqlite3` import in either new module; no function named `collect_*` in `bm_view.py` |
| `TestAlertHookEmitsWellFormedJson` | 3 | `bm-view alert --tick` prints one JSON object with `systemMessage` when a NEEDS YOU exists and nothing when none does; `terminalSequence` is a single ASCII BEL and is omitted when `BROTHERMODE_NO_BELL=1`; it is the only JSON emitting Stop hook |

### 13.3 tools/test_bm_store.py

| Class | Tests | Failing first evidence |
|---|---|---|
| `TestSchema17IsAdditive` | 4 | A schema 16 store migrates to 17 with the table present and every schema 16 row intact; a fresh store has it too; both paths produce identical `PRAGMA table_info`; `_TABLES_BY_VERSION[16]` is unchanged |
| `TestRecordViewRefusals` | 6 | One per refusal V1 to V6, each asserting the reason code and that nothing was written |
| `TestViewsAreAppendOnly` | 2 | An ast guard failing if any `UPDATE` or `DELETE FROM` names `views` outside `purge_project`; a republish appends rather than edits |
| `TestViewPurgeLeavesNoOrphans` | 2 | Shape copied from `TestControllerPurgeLeavesNoOrphans` (tools/test_bm_store.py:17375); zero rows survive |
| `TestViewPathsAreContained` | 2 | `rel_path` outside the project root refuses through `bs.safe_project_path` (tools/bm_store.py:5072); a symlinked path refuses the same way |

### 13.4 tools/test_bm_consent.py and tools/test_bm_docs.py

| Class or test | Change | Evidence |
|---|---|---|
| `test_no_wired_command_of_any_module_writes_before_consent` (471) | none | goes RED the moment hooks.json names bm-view and the module has no gate. This is the section 11.4 failing first evidence |
| `test_every_hook_wired_telemetry_command_checks_consent` (569, as widened by L04 section 18.2) | none | the widened version covers bm_view.py automatically and goes RED against an ungated module |
| `TestCapabilityRegisterIsHonest` (tools/test_bm_docs.py:3686) | none | the four new rows must satisfy it; a row naming a path that does not exist goes red at 3566 to 3574 |
| `TestNoDashes` (tools/test_bm_docs.py:4769) | CHANGED | the target list gains tools/bm_visual.py, tools/bm_view.py, tools/test_bm_visual.py, tools/test_bm_view.py and references/visual-surface.md |

### 13.5 The done check

After the last edit, in this order, with the command and the last lines of its
output pasted into the fix report:

```
cd /Users/khalil.maaouni/Documents/BrotherModeUp/tools && python3 test_bm_store.py
cd /Users/khalil.maaouni/Documents/BrotherModeUp/tools && python3 test_bm_visual.py
cd /Users/khalil.maaouni/Documents/BrotherModeUp/tools && python3 test_bm_view.py
cd /Users/khalil.maaouni/Documents/BrotherModeUp/tools && python3 test_bm_lead.py
cd /Users/khalil.maaouni/Documents/BrotherModeUp/tools && python3 test_bm_project.py
cd /Users/khalil.maaouni/Documents/BrotherModeUp/tools && python3 test_bm_consent.py
cd /Users/khalil.maaouni/Documents/BrotherModeUp/tools && python3 test_bm_docs.py
cd /Users/khalil.maaouni/Documents/BrotherModeUp && python3 tools/test_bm_controller.py
cd /Users/khalil.maaouni/Documents/BrotherModeUp && python3 tools/test_bm.py
cd /Users/khalil.maaouni/Documents/BrotherModeUp && python3 tools/test_all.py
```

`test_bm_lead.py` is not optional even though no L04 file is edited: this design
imports its collectors, so a signature change breaks the page. `test_bm.py` is
not optional: it holds the no network claim (1130) and the py-modules contract
(5409, 5417). `test_all.py` last, because it holds the CI inventory check (48, 473).
No suite's count may DROP. A drop is a deleted test and is a failure of this
change, not a result.

---

## 14. PROPOSALS AWAITING A FOUNDER GO AHEAD

Each of these is buildable and none is in section 15's build order, because each
one changes something that belongs to the founder rather than to the plugin. The
decided default for every one is **not shipped**, so nothing here blocks the
build.

1. **A status line script.** BrotherMode can ship the script but cannot install
   it: plugin `settings.json` supports only `agent` and `subagentStatusLine`
   (LENS-D section 6). A one line status line reading "gates 4 of 7, decision
   waiting" would put the top rung in front of him permanently. It needs him to
   paste one key into his own settings. Size: 1 to 2 hours assuming the script
   reads only `bm-view render --json` output.
2. **`footerLinksRegexes`.** A user setting (v2.1.181 or later) that turns
   matching text in Claude Code output into clickable links (LENS-D section 6).
   With it, every decision id and every trace tag in the transcript becomes one
   click into the page. Same shape of decision: his settings, his choice.
   Size: under an hour.
3. **A background monitor for freshness.** `monitors/monitors.json` would let a
   store change ask Claude to republish without a Stop hook. It is experimental,
   interactive CLI only, and unsandboxed at hook trust level (LENS-D section 4).
   Not shipped, and it would only shorten the gap between a change and a
   republish, which the Stop hook already covers.
4. **Two five minute probes.** Whether `ReportFindings` can be driven outside
   code review, which would give the harness's only native structured list
   renderer a second use; and what content types `MessageDisplay.displayContent`
   accepts. Both are LENS-D section 10 items. Neither is used by this design.
5. **A `## Design system` block in the project CLAUDE.md.** Verified to make
   Claude authored artifacts adopt a project palette (LENS-D section 2.4).
   Deliberately not adopted: every page this design produces is generated with
   its own measured tokens, so the block would only affect pages Claude composes
   freehand, which section 9.1 removes.

---

## 15. SIZE ESTIMATES, AS RANGES WITH THEIR ASSUMPTIONS

Ranges, never points, per references/forecasting.md. A working session is the
unit this program already estimates in (DESIGN-insight-ledger-and-handback.md
uses the same unit).

| Part | Range | Confidence | Assumption that would move it |
|---|---|---|---|
| A. Schema 17, the `views` table, refusals, purge pin (section 11) | 0.5 to 1 session | high | Assumes L04's schema 16 has landed, so this is a second additive migration on a path already exercised. If L04 has not landed, this cannot start at all |
| B. `bm_visual.py`: tokens, rungs, `alerts_now`, the insight box, the refusal map (sections 6, 9.2) | 1 to 2 sessions | moderate | Assumes `alerts_now` can be written entirely against existing accessors. If any rung needs a query the store cannot answer today, this grows by the accessor |
| C. `bm_visual.py`: the diagram model and the two emitters (section 7) | 1 to 2 sessions | moderate | Assumes deterministic SVG layout from character counts is good enough at these caps (7 stages, 9 nodes). If labels need real measurement, this is the part that grows, and the fallback is a fixed width label with an ellipsis |
| D. `bm_view.py`: the page, the twelve sections, the empty states, the fingerprint (section 4) | 1.5 to 3 sessions | moderate | Assumes `bl.collect_status` returns everything the header and the counts need. Its exact return shape is fixed by L04 section 3.4 but not yet written, so gate 1 in section 17 exists |
| E. The first fifteen minutes: the doorway, the command files, the skill rewrite (section 5) | 1 to 2 sessions | moderate | Assumes this is content and sequencing, not engineering, which LENS-B section 1.2 argues. If the behavioural fixture shows the three command restriction leaves people unable to find review or deliver later, the surfacing triggers need rework and this grows |
| F. The handback made visible: the panel, the copy as prompt control, the brief page (section 8) | 0.5 to 1 session | high | Assumes L04's `render_developer_brief` exists and returns the whole page as text, so the HTML render is a second projection of the same rows |
| G. Help at the point of need: `REFUSAL_HELP`, `SECTION_HELP`, `bm-view explain` (section 9) | 0.5 to 1.5 sessions | low | The only low confidence entry. The range depends entirely on how many distinct reason codes the store can emit, which is enumerable but not yet enumerated. L04 gives sixteen for one write path alone, so the true count across the store is the number to measure before committing |
| H. The suites: 63 tests across four files (section 13) | 1.5 to 3 sessions | moderate | Assumes the `Doc` parser is small (under 80 lines). Written first, so this cost is paid before any of A to G |
| I. The register, the disclosure, the capability rows (section 12.3) | 0.5 to 1 session | high | Same shape as L04's Writer C, which is a known quantity |
| **Total** | **8 to 16.5 sessions** | **moderate** | The dominant uncertainty is D and G together. If `collect_status` turns out to need widening, D moves to the top of its range and adds a dependency on L04's writer, which is the one thing this design has tried hardest to avoid |

Buildable today versus proposal: **A to I are all buildable today**, subject only
to L04 landing first. Section 14 is the complete list of what is a proposal, and
none of it is on the critical path.

---

## 16. WRITER SPLIT

One writer per file is law here, so the three sets below are disjoint. No file
appears twice, and none of them appears in L04's three sets either, except the
five files L04 also touches, which is why section 17's gate 0 exists.

### Writer D: the store and the vocabulary

    tools/bm_store.py
    tools/test_bm_store.py
    tools/test_bm_project.py
    tools/bm_visual.py
    tools/test_bm_visual.py

Sections 6, 7, 9.2, 11, 12.1, 13.1, 13.3. Deliverable: schema 17 migrates and is
additive, the six refusals hold, the views table is provably append only and
purges clean, the vocabulary exists with measured tokens, five shapes, four
rungs, one box, one derived alert function and one refusal map. Done check:
`python3 test_bm_store.py`, `python3 test_bm_project.py` and
`python3 test_bm_visual.py` all green, counts no lower than before.

### Writer E: the page and the CLI

    tools/bm_view.py
    tools/test_bm_view.py
    tools/test_bm_consent.py
    tools/test_all.py
    hooks/hooks.json
    pyproject.toml
    .github/workflows/tests.yml

Sections 3, 4, 8, 9.3, 11.4, 12.2, 13.2, 13.4's consent half. Deliverable: the
five subcommands, the one door, the twelve sections, the empty states, the
fingerprint, the handback panel, the brief page, both hook entries. Done check:
`python3 test_bm_view.py`, `python3 test_bm_consent.py` and
`python3 tools/test_bm.py` all green.

### Writer F: the register, the onboarding copy and the disclosure

    references/visual-surface.md
    references/terminology.md
    references/status-view.md
    skills/brotherme/SKILL.md
    commands/brotherme-view.md
    commands/brotherme-help.md
    commands/brotherme-start.md
    commands/brotherme-status.md
    commands/brotherme-handback.md
    capabilities.status.json
    README.md
    docs/ROADMAP.md
    docs/KNOWN-LIMITS.md
    SECURITY.md
    tools/test_bm_docs.py
    docs/program/absolute-lead/evidence/L05/

Sections 5, 10, 12.3, 13.4's docs half. Deliverable: the register describes the
vocabulary, the terminology map carries every new word before it is used, the
first fifteen minutes is written into the command files, the honest limits are
disclosed in both required places, and the capability register tells the truth.
Done check: `python3 tools/test_bm_docs.py` green.

### Ordering and the three gates

* **Gate 0, L04 to everyone.** L04's store half has already landed (section 0.1
  names the five symbols and their lines), so writer D is unblocked on schema 17
  today. Writer E does not start until `tools/bm_lead.py` exists with the nine
  symbols section 0.1 names and L04's suites are green. The eight files this
  design shares with L04 (`bm_store.py`, `test_bm_store.py`,
  `test_bm_project.py`, `test_bm_consent.py`, `test_all.py`, `hooks/hooks.json`,
  `pyproject.toml` and the workflow) are handed over, not shared: L04's writers
  are finished with them before D and E open them.
* **Gate 1, L04's writer B to writer E.** B posts the exact return shape of
  `collect_status` and `collect_briefing`. E does not guess them. This is the
  single highest risk in the whole plan (section 15, part D).
* **Gate 2, D to E.** D posts the signatures of `render_page`'s inputs from
  `bm_visual.py`: `Diagram`, `alerts_now`, `render_insight_box`, `THEME_CSS`.
  E calls them and does not reimplement them.
* **Gate 3, E to F.** F's capability rows name `tools/bm_view.py`,
  `tools/bm_visual.py` and their suites as evidence, and
  tools/test_bm_docs.py:3566 to 3574 fails if a named path is not in the tree.
  So F writes every other file first and lands `capabilities.status.json` plus
  the two bm-docs regenerations LAST.

D and F start together at gate 0. E starts at gates 1 and 2. No two writers
touch a shared file at any point, so no worktree isolation is needed beyond the
ordinary one branch discipline.

---

## 17. BUILD ORDER

Each step ends with a runnable check. Do not start a step until the previous
check passes.

1. **RED first.** Write every new class of section 13 against the untouched
   tree. Add the two `bm-view` lines to hooks.json with NO gate in a stub
   `bm_view.py`, so tools/test_bm_consent.py:471 reproduces the pre consent
   write. Capture everything to
   `docs/program/absolute-lead/evidence/L05/RED-L05-tests.txt`. Check: every new
   class appears there with at least one failure or error, and 471 is among them.
2. **PROBE 0, before anything is built on it.** Run one publish of a five line
   HTML file and record, in
   `docs/program/absolute-lead/evidence/L05/PROBE-0-artifact.md`: whether the
   `Artifact` tool is available in the founder's session at all, his plan, his
   authentication method and his model provider (LENS-D section 2.10 names all
   five gates). The result changes nothing in this design, because the local file
   is primary by L-S2, but it decides whether the page reaches him as a URL or
   only as a file, and that sentence belongs in his onboarding copy. Check: the
   file exists and names all five gate values.
3. **Store, schema 17.** `SCHEMA_VERSION`, the DDL constants, the table tuples,
   `_migrate_16_to_17`, `_MIGRATIONS`, `_ensure_schema`, `_ensure_indexes`,
   `_DUMP_SAFE_COLUMNS`. Check: `TestSchema17IsAdditive` green.
4. **Store, the write path and the purge.** `record_view`, the six refusals,
   `latest_view`, `list_views`, the `ReadOnlyStore` pass throughs, the purge
   delete, the pinned dict. Check: `TestRecordViewRefusals`,
   `TestViewsAreAppendOnly`, `TestViewPurgeLeavesNoOrphans`,
   `TestViewPathsAreContained` green, and `python3 test_bm_project.py` fully
   green.
5. **Vocabulary, the tokens and the ladder.** `TOKENS_LIGHT`, `TOKENS_DARK`,
   `THEME_CSS`, `RUNGS`, `RUNG_DELIVERY`, `STATUS_LEXICON`, `alerts_now`,
   `render_alert`, `render_insight_box`, `surface_for`. Check:
   `TestContrastTokens`, `TestColourIsNeverAlone`,
   `TestAlertsNowIsDerivedAndCapped`, `TestInsightBoxHasSixSlots`,
   `TestSurfaceRouter`, `TestNoNonAsciiInTerminalOutput` green.
6. **Vocabulary, the drawings.** `SHAPES`, `CAPS`, `Diagram`, the five builders,
   `diagram_for`, `_flat`, `to_svg`, `to_text`. Check: `TestDiagramCaps`,
   `TestDiagramEscaping`, `TestSvgAccessibilityPair`,
   `TestTextAndHtmlCarryTheSameFacts` green.
7. **Vocabulary, the failure surface.** `REFUSAL_HELP` and `failure_block`,
   with the reason codes enumerated from the store module rather than by hand.
   Check: `TestEveryRefusalIsRewritten` green, and
   `python3 test_bm_visual.py` fully green.
8. **View, the door.** `main`, `COMMANDS`, `_consent_state`, `_store_or_refuse`,
   the plumbing copied from bm_project.py, both hooks.json lines, pyproject.toml,
   the two CI steps, `SUITES`. Check: `TestConsentIsTheOnlyDoorForTheView` green
   and tools/test_bm_consent.py:471 back to green.
9. **View, the page.** `VIEW_SECTIONS`, `EMPTY_STATES`, `SECTION_HELP`,
   `SETUP_MILESTONES`, `render_page`, `fingerprint`, `cmd_render`, `cmd_url`.
   Check: `TestEverySectionRenders`, `TestEmptyStatesAreDesigned`,
   `TestExactlyOneNextActionOnThePage`, `TestTwoLevelsAndOneExpander`,
   `TestSelfContained`, `TestThemeAware`, `TestPageTracesToRows`,
   `TestByteStableAndHonestlyStale`, `TestThreeRenderersOneCollector` green.
10. **View, the handback made visible.** The `#your-move` panel, the copy as
    prompt control, `render_developer_brief_html`, `cmd_brief_page`. Check:
    `TestTheHandbackIsAlwaysVisible` and `TestTheHtmlBriefMatchesTheMarkdown`
    green.
11. **View, the doorway and the alert hook.** `cmd_doorway`, `cmd_explain`, and
    the alert tick. Check: `TestAlertHookEmitsWellFormedJson` green and
    `python3 test_bm_view.py` fully green.
12. **The first fifteen minutes, as content.** The five command files, the skill
    rewrite, `references/visual-surface.md`, and the terminology rows BEFORE the
    words appear anywhere. Check: `TestFirstFifteenMinutes` and
    `TestPlainLanguageHoldsOnThePage` green.
13. **Register and disclosure.** Writer F's remaining set, with
    `capabilities.status.json` and the two bm-docs regenerations last (gate 3).
    Check: `python3 tools/test_bm_docs.py` green.
14. **The whole gate.** The ten commands of section 13.5, in order, all green,
    no count lower than before.
15. **Hostile re-read.** `git status`, `git diff --stat`, then re-read every hunk
    for leftover debug prints, half applied renames, and any TODO, stub or
    placeholder. Confirm no em or en dash entered any file. Confirm no L04 code
    file was opened. Confirm `CONTROLLER_STATE_TRANSITIONS` and
    `AUTONOMY_FLOORS` are byte identical to their pre change state.

---

## OPEN QUESTIONS

None.

Every phrase in the founder's complaint is answered above with a stated
mechanic, and section 1.1 maps each one to its section. The three places where
the research and the platform disagreed are decided rather than deferred: the
minute zero artifact becomes a terminal doorway because a page is a write before
consent (section 5.2); mermaid is deferred in favour of inline SVG because its
rendering inside a Claude Code artifact is unconfirmed and SVG is not (section
7.6); and "graphs in the chat" is answered with the honest CLI behaviour plus
the one click page, because inline visuals are a verified negative for Claude
Code (section 3.4). The five things that would otherwise be founder decisions
are recorded in section 14 with a decided default of not shipped, so none of
them blocks a writer, and each remains a one line change if he wants it.
