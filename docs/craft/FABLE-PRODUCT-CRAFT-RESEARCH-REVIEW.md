# Fable pre-implementation review: the Product Craft Upgrade

Status: CURRENT. Written 2026-08-02 by Fable 5 (session 02f14e48, work record
e33a240d). This is the mandatory review the source document demands in its
section 18 before any implementation. Source document archived byte-identical at
docs/evidence/2026-08-02-product-craft-source-plan.md (body SHA256
a1303e4fc4d27e20c35d9bfe701d48348ac0473e1009a494717868c55118ea32).

Ground truth for every claim below: branch release/2.0-final at commit
502871da8967b08a945b6b2e76dc571786986813 (the future main; the release-closure
program lands there) and main at 4e9626d. Method: six parallel read-only
inspections, each claim pinned to a file and line or a command and its output,
followed by an adversarial refutation pass on this review's own load-bearing
calls. The release branch was moving while this review ran; facts are pinned to
the commit above, and anything decided at implementation time must be re-derived
against the tree that exists then.

---

## A. VERDICT

REVISE.

Not STOP: nothing in the plan weakens BrotherME beyond repair, and most of its
architecture is approved unchanged in section F. Not GO, for two reasons that
are each sufficient on their own:

1. The plan's foundational assumption is only partly true. It assumes the
   release-closure program is implemented and stable. At the pinned commit,
   Loops 0 through 6 are closed with evidence, but the program was still in
   flight the night of this review: Loop 7 closed by audit only mid-review
   (its machinery had substantially shipped at the pin), Loop 8 is open with
   three of seven validation rows evidenced and the dogfood clock unset, and
   Loop 9 with the founder's tag remains ahead. The feature freeze in
   docs/RELEASE.md rule 6 is in effect, where landing means merging to main
   or to release/2.0-final: a change that closes no named blocker does not
   land until the program ends. Product Craft closes no named blocker, and
   that includes this review's own two documents, symmetrically: their branch
   may publish and its pull request may open, but it merges only after the
   program ends or by an explicit recorded founder decision.

2. The plan is already MCP-first for its major providers (its own matrix
   names Figma MCP, Mobbin MCP, Higgsfield MCP and the shadcn MCP), but it
   still specifies a Python adapter wrapper layer around them (its sections
   8.3 and 8.8) inside a repository whose declared invariant is zero
   dependencies, where any future dependency is a deliberate founder
   decision. That wrapper layer would be dead weight or a second integration
   surface next to the runtime MCP servers that already exist. Section D
   removes it as a recommendation with reasons; section F replaces it with a
   provenance contract.

REVISE becomes GO without a further review round when the three start
conditions in section G are met and the amendments in section J are folded into
the source document. The design direction itself (governed lifecycle, one
authority, three directions, vertical slice first, render review, localization
context graph) is sound and compatible with every BrotherME law.

---

## B. CURRENT ARCHITECTURE CHECK

Each assumption the plan makes, with verdict and evidence.

1. "The Final Release Closure Plan has already been implemented; release truth,
   one SQLite authority, atomic project service, executable lifecycle,
   consent-first setup, security boundaries, runtime adapters, evidence, and
   release validation are stable."
   PARTLY VERIFIED. Loops 0 to 6 closed: release identity and freeze (commit
   8b98bbb, VERSION 2.0.0-rc.12.dev1, rc.10 and rc.11 superseded never tagged),
   state unification to schema 12 (tools/bm_store.py:76), mechanical beginner
   commands surviving 12 refuter findings, consent-first install with a real
   fresh-home rehearsal (docs/evidence/2026-08-01-fresh-home-rehearsal.md),
   task and delivery spine, forecasts and alerts with a numbers-trace-to-rows
   test, security closure with Bash-write detection. Latest full gate:
   test_all 1383 tests across 12 suites ALL GREEN at commit 3f688e6.
   NOT YET TRUE for three of the nine claimed properties at the pin: runtime
   adapters were substantially shipped but Loop 7 was not yet closed
   (tools/bm_runtimes.py, its conformance suite inside test_all and the
   docs/runtimes/ adapters existed and gated at the pin; the closure by audit
   came one commit later), validation evidence (Loop 8) had provable rows but
   no ledger and no dogfood start (Founder Report 3 says the calendar gate
   starts when the founder runs his first real project, and no evidence file
   records a start), and release validation (Loop 9) had not begun; VERSION
   still carries a development identity and no tag exists. The branch had a
   published upstream but stood 27 commits unpushed past
   origin/release/2.0-final at review time.

   Dated addendum, later the same night: while this review was being written,
   the parallel release session closed Loop 7 by audit (commit 7663861: the
   runtime registry, conformance suite and instruction adapters already
   shipped and gate inside test_all; the speculative foreign-runtime adapter
   package was deliberately not built because capturing foreign payloads
   needs founder-owned installs and authentication) and wrote Loop 8's honest
   inventory (commit 225ada5: three of the seven validation rows machine
   provable and done, four founder-only: dogfood, outside installs, the
   non-technical user, and the reforecast deferred until the dogfood clock
   starts). Loop 8 stays OPEN by its own ledger; Loop 9 and the tag remain
   ahead. Note the rhyme: the release program's Loop 7 refused its
   speculative adapter package for the same reason section D.1 of this review
   refuses the craft one. Both programs now hold the same line: the repo
   records and verifies; runtimes integrate.

2. One authoritative SQLite store with a service layer, extensible without a
   second source of truth.
   VERIFIED. bm_store.py declares itself the only writer of
   .brothermode/store.sqlite3 (bm_store.py:22-25); STATE.md, CANVAS.md and
   DELIVERY-PACKET.md are generated views (write_state_view bm_store.py:11244,
   _splice_generated bm_project.py:324). Every project mutation writes its
   entity row plus an attribution row in one transaction (_write_attribution
   bm_store.py:9866, BEGIN IMMEDIATE at :5087, used by nine service methods).
   The migration chain is additive with a backup first and the version bump
   last (_MIGRATIONS :2526, _migrate_from :4836-4895); the v11 to v12 step
   added eight tables in exactly the shape craft tables would use, so craft
   records land as _migrate_12_to_13. attribution.event_type is free text, so
   craft events need no enum change (brotherme/core/schema.py:314).

3. The laws the plan's section 4 cites (triage, founder rules retrieval,
   beginner contract, safety floor, routing table, founder gates, invariants,
   honest reporting).
   VERIFIED, all eight, at the pinned tree: SKILL.md:23-38 (triage),
   SKILL.md:40-118 (bm_learn apply with mandatory work identity),
   SKILL.md:120-136 (beginner contract), SKILL.md:138-151 (safety floor),
   SKILL.md:153-179 (19-row routing table matching 19 references/ files, each
   opening with a LOAD WHEN line), references/machine.md:35-45 (founder
   gates), INVARIANTS.md I1 losslessness, I2 exactly once, I3 lifecycle
   isolation, I5 single writer, I6 honest reporting, asserted by a calibrated
   state-machine test (10 of 10 reinjected defects caught).

4. The repository can render, screenshot, or visually verify anything.
   FALSE. The repo is pure Python standard library by declared invariant
   (pyproject.toml: no dependencies), 41 Python files, zero JavaScript, zero
   package.json, zero Playwright, Storybook, axe, or screenshot code. The
   word render in code means markdown generation. Every rendered-evidence
   promise in the craft plan therefore depends on the RUNTIME (Claude Code
   browser, Playwright MCP, simulator tools), not on repo code, and
   docs/RUNTIMES.md already states the honest ladder: Claude Code is the one
   verified runtime; everything else is advisory. Craft render evidence must
   carry the same per-machine capability labels.

5. Providers (Figma, Mobbin, Higgsfield, DeepL, Playwright) integrate through
   repo adapter classes.
   PARTLY TRUE as the plan writes it. The plan is itself MCP-first for the
   major providers; what does not hold is the need for a repo-side Python
   wrapper layer around them. On the machine this review ran on, Figma,
   Playwright, Chrome DevTools, Higgsfield and DeepL are already connected as
   MCP servers in the runtime. The repo's job is records, laws, provenance
   and evidence; the truly API-based providers (fal, Runway, TMS platforms)
   are deferred with their waves. See D.1 and F.4.

6. The founder keeps using one public entry, /brotherme goal, and learns no
   new vocabulary.
   PARTLY VERIFIED. There is no bare /brotherme command file; the entry is the
   beginner skill (model-invoked) plus /brotherme-start goal. The intent holds:
   the seven commands are thin wrappers entering named flows of the beginner
   skill, and a craft flow extends that surface with zero new vocabulary
   (commands/ inspected; skills/brotherme/SKILL.md routes by intent).

7. SKILL.md and INVARIANTS.md exist as reviewable law surfaces.
   VERIFIED. Both present at the pin; INVARIANTS.md carries the machine-checked
   invariant list this plan must not weaken.

---

## C. LAW COMPATIBILITY

- Triage. Compatible. The plan's SIMPLE versus COMPLEX craft split (section
  4.1) maps one to one onto SKILL.md's triage; a one-token fix takes the
  shortest path, a new product is COMPLEX. No change needed.
- Founder rules. Compatible. Craft work retrieves rules through the recorded
  bm_learn apply path with a work identity, like all substantial work. This
  review itself ran it (retrieval run b637a9d9; gate 3dad1a78 GitHub Desktop
  push, rule eeb754ad question windows, both honored).
- Founder gates. Compatible and extended. Direction selection, brand approval,
  paid providers, likeness media and final delivery are founder gates wired
  through question windows (rule eeb754ad). Approvals should reuse the store's
  receipt-gated approval lane pattern that already guards rule promotion, so a
  craft approval is a row with a receipt, not a sentence in a transcript.
- Beginner contract. Compatible. Craft responses obey outcome-first, one next
  action, ranges with confidence, and the terminology map. Every new
  user-facing craft term needs a references/terminology.md row BEFORE first
  use; that file says so itself.
- Safety floor. Compatible. Craft writes ride the same ground map, fence,
  single-writer and verify-after-last-edit floor. Parallel visual work uses
  worktrees exactly as the plan says.
- Losslessness. Compatible by construction if and only if craft state lives in
  the store and markdown stays a generated view. The plan already commits to
  this; section F.5 makes the generated-view pattern concrete.
- Exactly once. Compatible. Retried provider operations deduplicate by content
  hash inside the store's one-transaction service pattern; changed content
  creates a new version through supersession linkage, which the store already
  models for learning rules.
- Lifecycle isolation. Compatible. INVARIANTS.md I3 already states it; craft
  records carry project and lifecycle identity and rejected directions stay
  rejected. The mapping document (brief C1) must show the isolation column on
  every new table, and the check extends to REUSED tables: the generic
  evidence and notes tables carry no project or lifecycle column of their
  own, so isolation there is by join through the subject, and each reuse
  decision names the column or join path that enforces I3, stated never
  assumed.
- Single writer. Compatible. One task owns a screen or component file; the
  fence hook enforces file-level claims on Claude Code and fails open with a
  reason elsewhere, per the existing honest limitation.
- Honest reporting. Compatible and sharpened by section I: no rendered-support
  claim without a stored render after the final relevant change, and every
  render claim carries its runtime capability label.
- Failed-write safety. Compatible. The migration mechanism backs up first;
  generated views splice between markers with a .bak; craft file writes follow
  the same pattern.
- Load on demand. Compatible. Craft references are LOAD WHEN files plus router
  rows, the documented pattern. Section D.8 cuts the count from nine to five.
- Failure degradation (the plan's own law 3.7, checked here because deleting
  the adapter classes also deletes their health probes). Compatible without
  probes: a provider failure is detected by the failing tool call at the
  moment of use, recorded as an alert row plus a blocked state on the
  affected task through the existing service operations, and degraded to the
  manual path (reference capture and evidence without the provider). The
  law's four outcomes (mark blocked, manual fallback, preserve state, report
  the limitation) map one to one onto alerts, task states, the store's
  transactional writes, and honest reporting.

---

## D. REMOVE OR DEFER

D.1 REMOVE the Python provider adapter package (section 8.3's adapters/
directory: figma.py, mobbin.py, registry.py, storybook.py, playwright.py,
chromatic.py, motion.py, rive.py, higgsfield.py, fal.py, runway.py,
localization_tms.py). The plan is already MCP-first for its major providers;
this cut removes the Python wrapper layer around those MCP servers, which
arrive in the runtime with their own auth, consent and update cycles, and it
defers the truly API-based providers (fal, Runway, TMS) with their waves.
The repo is stdlib-only by invariant, and the invariant's own wording makes
any future dependency a decision the founder makes on purpose
(pyproject.toml: "the dependency list stays empty and any future addition is
a decision the founder makes on purpose"), so this removal is a strong
recommendation with reasons, not a rule the plan breaks; the founder could
approve a dependency, and this review recommends against it. Replacement in
F.4: one provider provenance contract (store rows plus a references file),
zero provider client code. This is the single largest scope cut and it
removes the plan's largest dependency and maintenance risk.

D.2 DEFER the five implementation kits (kits/web, expo, ios, android,
flutter). Version one ships two reference lanes: a web lane and a native
review lane. Kits become real only when a real product project demands one.

D.3 DEFER all TMS adapters (Lokalise, Phrase, Crowdin, Tolgee). The
Localization Context Graph, glossary and screenshot-linked review live in the
store. DeepL exists as a runtime MCP on this machine for machine-draft
translation, labeled machine draft per the plan's own locale maturity ladder.

D.4 DEFER Chromatic and Percy. Rendered comparison comes from the runtime
Playwright or browser tools; evidence lands as store rows plus files under the
evidence policy in E.3.

D.5 DEFER Rive, GSAP, Lottie, Spline and all 3D. The version one motion ladder
stops at level 3 (Motion or native declarative animation). Higher rungs return
with the deferred media wave.

D.6 DEFER media generation execution (Higgsfield, fal, Runway flows). KEEP the
media provenance, consent, rights and cost record in the version one schema,
so any manually produced or generated asset is governed from day one. The
Higgsfield MCP is already connected on this machine; using it through the
governance records requires no adapter code.

D.7 COLLAPSE the eleven proposed craft tables pending the C1 mapping document.
The store already has generic evidence (subject_type, subject_id, kind, ref),
alerts, forecasts, decisions, notes and attribution. The mapping document
decides table by table: reuse, extend, or create. Expected outcome is four to
six net-new tables, not eleven. This mirrors release-closure amendment A3:
integration, not reinvention, and no table created twice. Two walls the
mapping document must respect, found by this review's own refuters: the
notes table's kind and anchor_type columns are closed CHECK lists that
SQLite cannot alter, so notes reuse is bounded by the existing enum values
and a new craft kind means a new table or additive columns, never an
in-place enum edit; and the generic evidence table carries none of the
section I fields (commit, environment, viewport, theme, locale, state,
hash) and no dedup key, so craft visual evidence classifies as EXTEND with
additive columns plus net-new dedup logic, not plain reuse.

D.8 REDUCE the reference surface from nine files to five: craft-director,
craft-research, design-system (brand folds in), platform-design, and
localization. visual-review folds into craft-director's review loop; motion
and creative-media references arrive with their deferred waves. Nine internal
coordinator skills become zero; the craft director is a reference file, not a
skill tree.

D.9 DEFER Storybook integration until a product project that uses components
exists. BrotherModeUp itself has no frontend; forcing Storybook into version
one would manufacture a surface with no consumer.

---

## E. MISSING CAPABILITIES

E.1 Sequencing with the live release-closure program. The plan's assumption
line hides the real dependency. Section G states the start conditions
explicitly; nothing in the craft program may land on the release line before
the program ends, and the next version's name may appear nowhere (RELEASE.md
version law rule 1).

E.2 Runtime capability detection and labeling. Which machine has which MCP
server decides which evidence is producible. This is NEW craft machinery,
inspired by the honesty pattern of docs/RUNTIMES.md rather than an extension
of it (that file covers instruction files, store CLI and hooks per runtime
and never mentions MCP). Concretely: at diagnosis time the session attempts
to reach each craft-relevant tool surface (browser, Playwright, simulator,
Figma, DeepL, Higgsfield) through the runtime's own tool discovery, records
the result as capability rows in the store (exact table decided by C1),
attaches the label to every piece of rendered evidence, and re-verifies per
session and per machine, because connections change between sessions.

E.3 Evidence storage policy. Screenshots are binaries; a repo that accumulates
render matrices in git bloats fast. Policy: store rows carry hashes,
environment and the pass or fail verdict; image files live under
docs/evidence/craft/ with a per-loop budget (indicative: low tens of files,
tens of kilobytes each, decided in C1), and bulk matrices stay outside git in
the project workspace with their hashes recorded. A craft table absent from
the redaction column lists must fail closed on export, same as every other
table.

E.4 SBE design dossier. The founder's SBE discipline classifies this program
T2 to T3. The source document plus this review constitute the dossier
(purpose, process, architecture, data, expression, verification); the
mechanical SBE design checks run against the C1 mapping document when it
exists, and the result is disclosed either way.

E.5 Dogfood synergy, sequential not simultaneous. Release Loop 8 needs the
founder's real project over seven calendar days, and by the ratified
program's amendment A2 that dogfood runs DURING the release program, while
craft implementation starts only after it ends; the two windows cannot
overlap under this review's own start conditions. The synergy that remains
is real: pick a dogfood project whose product can BECOME the craft program's
first validation product, so the same real work feeds both ledgers in
sequence. Any true overlap (craft loops running during the dogfood window on
a quarantined branch) exists only as a founder-gated exception recorded as a
decision row.

E.6 Baseline before targets. The section 49 scorecard states targets with no
baseline measurement step. The first craft project records the baseline; the
scorecard compares against it, not against hope.

E.7 Store hygiene for founder prose. Craft rows will carry brand theses and
audience truths, which are the founder's private thinking. The existing
export redaction funnel must classify every new column before the first
export, and session-label withholding applies unchanged.

---

## F. ARCHITECTURE DECISION RECORD

F.1 Optional capability pack: APPROVED, reshaped. The pack is reference files
plus store records plus service operations, not a parallel Python subsystem.
Whether any brotherme/craft/ package exists at all is decided by the C1
mapping document; the default is no new package.

F.2 One public entry, no new vocabulary: APPROVED, with the corrected premise
that the entry is the beginner skill and /brotherme-start. Craft becomes a
flow, not a command.

F.3 Existing SQLite authority: APPROVED and mandatory. bm_store.py remains the
only writer; craft markdown is generated views.

F.4 Provider adapters: REJECTED as Python classes. REPLACED by the provider
provenance contract: every provider interaction records source, URI, retrieval
date, version, license note, input hash, output hash, transformation,
approving human, linked task and final usage as store rows. The capability
labels are the plan's own section 8.9 vocabulary, retained (verified,
verified_with_limits, documentation_verified, experimental, unavailable);
what changes is the attachment point: they attach to the machine and runtime
rather than to a provider integration, live as store rows (table decided by
C1), are assigned at diagnosis time and re-verified per session. Provider
output remains untrusted input, exactly as the plan says.

F.5 Generated views: APPROVED. DESIGN.md and the design/ views imitate
write_state_view and _splice_generated: markers, backup, redaction funnel,
rebuildable from the store byte-stable.

F.6 Three-direction law: APPROVED for complex new visual work, with the
anti-pattern gate (no three palette variants). Founder selection through
question windows; rejected directions preserved as rejected.

F.7 Vertical-slice-first: APPROVED. It is the strongest rework control in the
plan and it matches how this repo already works (prove one seam, then expand).

F.8 Render-review loop: APPROVED with runtime capability labels per E.2. No
customer-facing screen accepted from source inspection alone, where a render
capability exists; where it does not, the limitation is stated, never papered
over.

F.9 Localization Context Graph: APPROVED, store-backed, no TMS. Message
records carry meaning, tone, constraints, screenshot linkage and maturity
labels; high-risk content keeps its human gate.

F.10 Fable plans and reviews, lower models execute: APPROVED. It is the
release program's separation of duties applied to craft; the writer and the
final reviewer are never the same execution context.

---

## G. REORDERED LOOPS AND START CONDITIONS

Start conditions for implementation (all three, no exceptions):

1. The release-closure program has ended: Loop 9 closed and the founder has
   tagged and published 2.0.0, or the founder explicitly amends the freeze in
   a recorded decision.
2. The founder has approved the craft scope (the D cuts and the loop order
   below) through question windows.
3. The C1 mapping document exists and Fable has accepted it.

What may happen before the start conditions, applying the freeze
symmetrically (landing means merging to main or release/2.0-final): exactly
two craft artifacts exist before the start conditions are met, C0 (this
review and its archived source) and C1 (the mapping document), both docs
only, both quarantined on their own branch, neither merging until the
program ends or the founder records a decision to merge earlier. The
founder's scope answer and vault notes are the only other pre-start
activity. Nothing else, and no craft code.

The reordered loops (C for craft):

- C0. This review, the founder scope decision, and the archived source. Done
  when the founder answers the scope questions. Docs only.
- C1. Mapping document: every proposed record against the existing store
  (reuse, extend, create), the evidence storage policy made concrete, the
  redaction classification for every new column, the SBE checks run against
  it. No code.
- C2. Craft records and service operations: the 12 to 13 migration, service
  methods with attribution, generated views, invariant tests including
  interrupted migration, duplicate reference, superseded direction, lifecycle
  leak, malformed payload, export redaction.
- C3. Router and progressive loading: craft diagnosis in the beginner flows,
  five reference files with LOAD WHEN lines and router rows, terminology rows,
  token-economy checks (the trivial path loads nothing).
- C4. Research and reference engine: manual and URL reference capture with the
  provenance contract, reference analysis template, anti-reference handling.
  Runtime MCPs (Figma, Mobbin if connected) are sources, recorded not wrapped.
- C5. Journeys, information architecture and state completeness: journey and
  screen records, the required-state matrix, validation that no critical
  journey omits failure and recovery.
- C6. Three directions and founder selection: direction packets with rendered
  evidence where the runtime allows, Fable recommendation, founder gate.
- C7. Design system foundation: tokens (DTCG-compatible where practical),
  typography and color checks, one token authority, drift tests.
- C8. Vertical slice with visual evidence: one complete journey slice on the
  chosen product, rendered matrix, accessibility and performance checks by
  runtime capability, the last cheap direction-change point.
- C9. Localization: context graph, glossary, pseudolocale and expansion
  checks, machine-draft lane labeled, human gate for high-risk content.
- C10. Expansion by reviewed waves with drift detection.
- C11. Motion and media wave (the D.5 and D.6 deferrals return here, ladder
  and delight budget intact).
- C12. Dogfood, validation products, final adversarial craft review
  (docs/craft/FABLE-FINAL-CRAFT-REVIEW.md), release gates.

Parallelization: C3 reference authoring lanes after the route design is fixed;
C4 research sources in one read-only wave; locale lanes in C9 after source
freeze; everything touching bm_store.py stays single-writer serial.

---

## H. FIRST SIX IMPLEMENTATION BRIEFS

Compressed to the fields that gate execution. Every brief inherits: founder
rules retrieved through the recorded path with this program's work record;
fence then dispatch; suite green after the last edit; no em or en dashes in
user-facing text; terminology rows before new user-facing words.

Brief C1, mapping document.
User value: craft state that can never fork the store.
Failure closed: eleven speculative tables becoming a second truth.
Reads: tools/bm_store.py, brotherme/core/schema.py, the archived source plan,
this review. Writes: docs/craft/2026-XX-craft-state-mapping.md only.
Forbidden: all code.
Checks: every plan record named with a reuse, extend or create decision and
its isolation and redaction columns; SBE design checks run and their verdict
quoted; Fable acceptance recorded.
Rollback: delete the document. Range: 0.5 to 1 day, 30k to 80k tokens,
confidence medium.

Brief C2, records and service.
User value: durable craft decisions surviving restart, compaction and outage.
Failure closed: craft facts living in markdown or transcripts.
Reads: the C1 mapping. Writes: tools/bm_store.py (one additive migration 12 to
13 exactly as _migrate_11_to_12), tools/bm_project.py (service wrappers),
tools/test_bm_store.py, tools/test_bm_project.py. Forbidden: commands/,
skills/, references/.
Checks: migration from a real pre-13 backup passes; interrupted migration
leaves the prior version intact; duplicate and supersession tests; export
redaction fails closed on unclassified columns; full suite green.
Rollback: restore the pre-migration backup the mechanism itself creates.
Range: 1.5 to 3 days, 120k to 300k tokens, confidence medium after C1.

Brief C3, router and references.
User value: craft appears when valuable, invisible when not.
Failure closed: token bloat on trivial tasks; a second command vocabulary.
Reads: skills/brotherme/SKILL.md, SKILL.md routing table,
references/terminology.md. Writes: five new references/craft files, router
rows in SKILL.md, flow mentions in skills/brotherme/SKILL.md, terminology
rows, tools/test_bm.py wiring assertions. Forbidden: tools/bm_store.py.
Checks: routing test proves the trivial path loads no craft reference; each
new file opens with LOAD WHEN; drift test between table and files stays green.
Rollback: revert the reference files and rows. Range: 1 to 2 days, 60k to
160k tokens, confidence medium.

Brief C4, research and reference engine.
User value: design grounded in evidence, not template memory.
Failure closed: invented conventions and uncredited copying.
Writes: reference capture operations (C2 surface), the analysis template in
references/craft-research.md, provenance rows. Forbidden: any HTTP client
code.
Checks: a reference without source, license note and applicability analysis
is refused; untrusted-instruction test (a reference cannot instruct); works
with zero connected providers.
Range: 1 to 2 days, 80k to 200k tokens, confidence medium.

Brief C5, journeys and states.
User value: the product works before it is styled.
Failure closed: happy-path-only screens.
Writes: journey and screen records with the state matrix, validation that
flags missing failure, recovery, empty and permission states.
Checks: seeded incomplete journey is caught; primary journey explainable in
one minute from the generated view.
Range: 1 to 2 days, 80k to 200k tokens, confidence medium.

Brief C6, three directions.
User value: a founder choice between real alternatives, not one default.
Failure closed: generic AI sameness; unapproved direction implemented.
Writes: direction records and packets; rendered samples where the runtime
capability exists, labeled.
Checks: difference criteria across at least five axes verified; anti-pattern
gate applied; founder selection recorded as a receipted approval row;
implementation refuses to start against an unapproved direction (test).
Range: 1.5 to 4 days, 150k to 450k tokens, confidence low to medium.

---

## I. QUALITY GATES AS OBSERVABLE EVIDENCE

Every gate is a stored row plus a command, never a sentence.

- Usefulness gate: primary task completion evidence row linked to a journey
  record; unresolved dead ends counted by the state-matrix validation.
- Direction gate: approved thesis row, three direction rows with packets,
  founder receipt, anti-trait list present.
- Component gate: per-component record with states, accessibility and
  localization behavior fields non-empty, tests named, provenance complete.
- Responsive and tablet gate: viewport matrix rows with renders after the
  final relevant change, runtime label attached.
- Accessibility gate: automated check output stored where the runtime provides
  it; manual findings as alert rows resolved before acceptance; text scale and
  reduced motion in the required-state matrix.
- Localization gate: every production message has a context record; dynamic
  message tests; glossary respected; screenshot-linked review rows for launch
  locales; high-risk approvals receipted.
- Motion gate (wave C11): MotionSpec row per motion, reduced-motion behavior
  recorded, performance note present.
- Media gate: provenance, consent, rights, cost and approval fields complete
  on every media row, version one onward (D.6).
- Visual evidence gate: evidence rows carry commit, environment, viewport,
  theme, locale, state and hash; claims without a post-final-change render are
  refused by the same discipline that refuses done without a verifying
  command.
- Release gate: the final adversarial craft review returns GO with zero
  Critical or High findings, and the founder accepts.

---

## J. FINAL AMENDMENTS TO THE SOURCE DOCUMENT

PC-A1. Replace the assumption line with the verified status (B.1) and add the
three start conditions of section G. Craft implementation begins after the
release-closure program ends; only C0 and C1, docs only and branch
quarantined, may exist beside it.

PC-A2. Delete the adapter package (8.3 adapters/, 8.8 CraftProvider). Insert
the provider provenance contract (F.4) and runtime capability labels (E.2).
Providers are runtime MCP servers; the repo records, it does not integrate.

PC-A3. Insert a mapping-first law for storage (D.7): the C1 document decides
reuse, extend or create per record; expected four to six net-new tables landed
as one additive migration in the existing chain. Every reuse decision names
its lifecycle-isolation column or join path; notes reuse is bounded by its
closed CHECK lists; evidence extends with the section I columns and a dedup
key.

PC-A4. Reduce references from nine to five (D.8); no internal skill tree; the
craft director is a reference file.

PC-A5. Replace the five kits with two reference lanes (D.2).

PC-A6. Move motion beyond ladder level 3, and all media generation execution,
to a second wave (D.5, D.6); keep media governance records in version one.

PC-A7. Remove TMS adapters (D.3); localization context lives in the store;
machine-draft translation through a runtime MCP where connected, labeled.

PC-A8. Add the evidence storage policy (E.3) and the redaction classification
requirement (E.7).

PC-A9. Add the SBE dossier mapping (E.4).

PC-A10. Add dogfood synergy (E.5) and the baseline measurement step (E.6).

PC-A11. Correct the entry premise: the public surface is the beginner skill
plus /brotherme-start; craft is a flow of it (B.6, F.2).

PC-A12. The plan's file map (section 43) is replaced by repo conventions:
flat tools/ modules, flat references/ files, docs/craft/ for dossiers,
docs/evidence/craft/ for evidence, per the C1 mapping.

---

## What this review did not verify, stated plainly

- The SBE mechanical design checks did not run against this review; they run
  against the C1 mapping document when it exists (E.4).
- Provider MCP availability was observed as connected servers in one session
  on one machine; none was conformance-tested for craft use.
- The 1383-test gate is the release program's evidence at commit 3f688e6,
  quoted, not re-run by this session; this review's own branch carries a
  docs-only change gated by its own suite run at landing time.
- The release branch continued moving while this review was written; every
  pinned fact holds at 502871da and must be re-derived at C1 time.
- The refutation pass on this review ran with three adversarial lenses
  (verdict and freeze reading, adapter rejection, storage and citations):
  fourteen objections were sustained (three high, four medium, seven low)
  and every one is folded into the text above; twenty six spot-checked
  citations held, including the two load-bearing ones (the migration
  mechanism really does back up first and roll back whole on interruption,
  and attribution.event_type really is free text). The REVISE verdict
  itself was attacked from both directions and survived on the second
  reason alone. Details in the vault session log for 2026-08-02.
