# The Toolkit plan: a capability broker, not a marketplace

Status: CURRENT. Designed 2026-08-12 morning with Fable, on the founder's
directive to focus only on this. Supersedes the R2 WBS in
`LONG-RANGE-PLAN-2026-08-11.md` for scope; the tranche letters and cadence
stand. Companion decisions: `docs/design/TOOLKIT-BROKER-2026-08-12.md` (the
tiers and quarantine design) and its refutation in
`docs/evidence/design-review/REFUTE-2026-08-12.md`, whose blocking finding T1
this plan exists to answer.

---

## 1. The one sentence, and the pipeline that proves it

BrotherMode is where Claude Code work becomes a controlled delivery. The
Toolkit is the organ that extends that control over every OTHER tool on the
machine, so that the best plugin for each job does the job and BrotherMode
still owns the record of what happened.

The acceptance test is the founder's own example, run literally:

1. BrotherMode starts the work and records the intended outcome.
2. Superpowers writes the plan and implements with test-driven development.
3. Anthropic Code Review reviews the result.
4. BrotherMode reruns the acceptance checks itself, after the last edit.
5. BrotherMode delivers ONE evidence packet naming who did what, under which
   version, with what verification.

When that pipeline completes on a real change in this repository, with a
receipt for each external step, the MVP is done. Not before.

## 2. What we are NOT building, recorded as decisions

- **Not a marketplace.** Claude Code has marketplaces; this machine has eight
  of them cached right now. Rebuilding discovery is undifferentiated and
  loses to the platform owner by default.
- **Not a second permission system.** The broker design already rejected
  intercept-and-police (Alternative A) because two gates drift, and the
  harness's own permission system works. That rejection stands.
- **Not a sandbox.** The front page disclaims operating-system containment.
  Nothing here quietly contradicts it. Capability records make divergence
  VISIBLE and COUNTABLE; they do not constrain a determined process. That
  sentence survived adversarial review (finding T4) and stays.
- **Not autonomous installation.** MVP composes what is already installed,
  plus curated official plugins, plus explicit founder-approved installs.
  Autonomous discovery earns its place only after the broker proves it can
  safely compose what is present.

## 3. The five functions, and what already exists for each

### F1. Capability inventory

Know what is installed: skills, plugins, hooks, agents, MCP servers, and the
CLIs the runtime can reach, each with source and version where knowable.

**Ground truth, measured on this machine today, 2026-08-12:** 8 plugin
marketplaces cached, roughly 40 plugins, 37 user-scope skills, 17 plugins
carrying their own hook files, plus 5 machine-wide hook commands in
settings.json, plus MCP servers (Figma, Canva, Perplexity, Exa, Firecrawl,
DeepL, Miro, XcodeBuild, computer-use, browser, and more). No command today
can list this. That is R2.1, unchanged: `tools/bm_toolkit.py inventory`.

The inventory reads ARTIFACTS, never memory: plugin manifests, hooks.json
files, settings.json, the skills directory, the MCP registry. What a tool
registers is observable without running it.

### F2. Overlap and conflict detection

The founder's conflict list, checked against this machine this morning. None
of it is hypothetical:

| Conflict class | On this machine right now |
|---|---|
| Multiple Stop hooks | SEVEN plugins register Stop: brotherme, brothersbe, slop-gate, ultrapowers, hookify, ralph-loop, security-guidance |
| Multiple PreToolUse blockers | TEN layers: seven plugins plus spend guard, session cap, and fence hook |
| Multiple session-memory systems | Kay Vault hooks, harness auto-memory, the BrotherMode store, and the chatgpt-archive skill coexist |
| Duplicate planning workflows | superpowers writing-plans, ultrapowers planner, ultraplan, mattpocock to-spec, feature-dev: five ways to plan |
| Conflicting definitions of completion | superpowers and ultrapowers verification-before-completion, BrotherMode definition-of-done, BrotherSBE receipts, slop-gate premature-completion detection: five definitions |
| Global versus project scope | brothersbe cached at BOTH 1.0.0-rc.1 and 1.0.0-rc.38 simultaneously |
| Version drift on PATH | the sbe two-majors-behind incident, already in the failure ledger |
| Extra network or credential access | the 0.0.0.0 proxy and the token-saver auto-approve findings, both in the broker design's section 1 |

This function is NEW relative to the old R2 WBS and it is the
differentiator: research to date has found no ecosystem tool that does it.
Verdicts follow the house discipline: three classes (info, warn, fail),
NO-DATA when a surface cannot be read, never silence.

### F3. Capability routing

Choose the minimum sufficient existing capability for a task class. The
routing table is DATA, not prose: a versioned file the way `write_sites.json`
and the effects registry already work, where every route carries its reason
and its flip condition, and the store records which route actually ran.

Seed table, the founder's own examples: TDD to Superpowers; product strategy
to Compound Engineering or BMAD; long phase planning to GSD-class; security
check to Security Guidance; PR review to Code Review; historical recall to a
claude-mem-class memory. Routing composes with the existing decision ladder
and model-tier rules; it picks the capability, delegation picks the tier.

### F4. Evidence normalization

Every external capability's output becomes a BrotherMode receipt with nine
fields: capability and version; task; inputs; permissions; claimed output;
changed artifacts; raw evidence; independent verification; omissions.

Two hard rules. INDEPENDENT means BrotherMode reruns the acceptance check
itself after the capability returns; the capability's own green never
suffices, because a cheap-lane or external result is untrusted until a
deterministic check passes on our side. And output that cannot be normalized
is a NO-DATA receipt, never a trusted one: missing evidence is never
silently treated as success. This is R2.4 widened from executor identity to
the full nine fields.

### F5. Retention decision

After delivery, each capability used gets a decision: retained, preferred,
project-scoped, disabled, removed, or blocked. Proposals are automatic and
evidence-based (receipts from F4); ratification is the founder's, through
the same approval path learned rules already use. One demotion is automatic:
a version change under a fixed name drops the capability back to
quarantined, because the record no longer describes the thing.

## 4. The answer to refutation finding T1: who observes reach

T1 blocked ratification of the broker design because promotion out of
quarantine required an observation mechanism the design left undesigned,
without which the whole thing degrades to a registry.

The MVP answer: **observation is split into a static half and a dynamic
half, and the MVP ships the static half completely.**

- **Static reach is read from artifacts, mechanically, today.** Which hook
  events a plugin registers, which MCP servers it declares, which commands
  its manifest exposes, whether its scripts reference network calls or
  credential-shaped environment variables: all of that is in files the
  inventory already parses. A capability record built this way is DERIVED,
  not asserted, which is the structural difference from the rejected
  Alternative B. The permissions field of every receipt is labeled DECLARED
  in MVP, honestly.
- **Dynamic reach arrives through receipts.** Every routed execution
  produces an F4 receipt naming changed artifacts and verification. Receipts
  accumulate per capability, and F5 reads them. That is the observation
  stream, and it exists because routing exists; no separate monitor needs
  inventing.
- What the MVP does NOT observe, stated plainly: syscall-level behavior,
  network traffic, reads that leave no artifact. Anything claiming otherwise
  is wrong, and the UNENFORCED sentence from the broker design carries over
  verbatim.

## 5. Absorb or coordinate: four criteria and the native floor

Refined 2026-08-12 on the founder's direction: BrotherMode must not be fully
dependent on external hooks and skills for anything essential. The line is
drawn by four criteria, and a capability is absorbed into core only when it
meets ALL FOUR:

1. **Sufficient when minimal.** A thin native version genuinely covers the
   spine's need; we are not rebuilding a whole product badly.
2. **Differentiating.** Owning it strengthens the moat rather than
   duplicating a commodity.
3. **North-star-close.** It IS controlled delivery, not a method of doing
   work.
4. **Necessary.** Delivery would STOP without it on a machine where the
   external capability is absent or broken.

**The native floor law, which makes decision 11 honest.** Decision 11 says an
absent capability degrades to core with the gap named in the receipt. That
promise is only true if a native floor EXISTS for every spine step. So: every
step of the controlled-delivery spine carries a native floor that BrotherMode
owns outright; routed capabilities are UPGRADES on top of the floor, never
dependencies under it. Where a floor is missing, a thin one is built; where
an external tool would only duplicate the floor, it is coordinated, not
absorbed.

### The spine, step by step

| Spine step | Native floor, owned | Routed upgrade | Floor status |
|---|---|---|---|
| Outcome record and acceptance criteria | store: goal, scope, success criteria, kill_criteria, non_goals | BMAD or Compound Engineering product elaboration | EXISTS, schema 19 |
| Plan shape | bm_project tasks with acceptance checks; the plan law: files plus done-checks | GSD phase planning, superpowers writing-plans | EXISTS, minimal on purpose |
| Implementation method | test-first law plus the gate battery; no native TDD engine | Superpowers TDD | FLOOR IS DISCIPLINE PLUS GATES; the engine is deliberately not built (decision 22) |
| Verification | the done-check rerun after the last edit; test_all; verify-close | NEVER ROUTED | EXISTS, the sole closing authority (decision 10) |
| Review | falsification-only review brief, PO-5: attacks executed, COULD NOT BREAK or findings | Anthropic Code Review | EXISTS as discipline; BORROWED into a named core artifact in T6 |
| Security floor | secret scan, dash scan, write-site inventory, effect classes | Security Guidance depth | EXISTS |
| Evidence and delivery | nine-field receipts plus the delivery packet | NEVER ROUTED | BUILD, T5 |
| Criterion-linked verification | every check names the acceptance criterion it satisfies | none | BORROWED from GSD's essence; R1.2 is PULLED INTO this arc as part of T5, because it is the receipt's backbone |
| Memory | the store for delivery state; the Obsidian vault for knowledge | claude-mem-class recall, read-only | EXISTS; strengthened per decision 23 as its own program |
| Forecast and queue depth | bm_forecast, bm_idle | none | EXISTS since 12 August |
| The capability layer itself | inventory, conflicts, routing, retention | NEVER ROUTED; the broker is never external | BUILD, T1 to T8 |

### What we borrow: essences, not code

Four external ideas are close enough to the north star that their ESSENCE
becomes core, while the tools themselves remain coordinated:

- **From GSD:** machine-verifiable acceptance criteria per task. Absorbed as
  criterion-linked verification, folded into T5.
- **From Compound Engineering:** the compounding learning loop, where each
  delivery's lessons feed the next plan. Already native as bm_learn plus the
  vault; T7's retention receipts now feed it, closing the loop.
- **From superpowers:** verification before completion. Already this
  project's founding law; named here so the debt is acknowledged.
- **From claude-mem:** episodic session memory. Absorbed as direction into
  the vault agent-memory program (decision 23), never as their hook stack.

### What we coordinate, never absorb

TDD engines; planning elaboration (BMAD, GSD, Compound Engineering, arc);
review depth (Anthropic Code Review); security depth (Security Guidance);
research (Perplexity, Exa, Agent-Search); design and media (design plugins,
Figma, Canva, Higgsfield); hook generation (Hookify).

**Strictly last, behind the connector model (decision 24):** out-of-harness
executors: Cline, OpenHands, Cursor CLI. Each is a separately versioned
surface with its own auth failure modes. Bringing them in early would put
uncontrolled executors inside a product whose one promise is control.

## 5a. The family, and why the Toolkit is invisible

Three siblings, one spine, one capability layer:

- **BrotherMode:** one person's session becomes a controlled delivery.
- **BrotherSBE:** one change's passage between people becomes assured.
- **BrotherDS**, the future data sibling (its exact scope is the founder's
  to define): the same spine over data work, where BrotherSBE's number and
  migration gates (pinned snapshots, second derivations, reconciliation)
  already prefigure what its floor will need.

The Toolkit is the SHARED layer underneath all three: one inventory, one
conflict map, one receipt schema, one retention memory. A sibling consumes
the layer; no sibling reimplements it. When BrotherDS arrives, it inherits
routing, receipts and retention on day one instead of rebuilding them.

**The invisibility principle.** In the normal working loop the user never
runs a toolkit command and never learns broker vocabulary. Routing happens
inside start, next and review; receipts appear inside the delivery packet;
conflicts surface through doctor, the way a stale manifest already does;
retention proposals appear at review cadence. The Toolkit's entire
user-facing surface is three moments: a doctor finding, a packet appendix,
and a retention review. Zero new ceremony in the daily path, which is what
"seamless" means concretely enough to test: if a first-day user has to learn
one new command for the toolkit to work for them, this principle is broken
and that is a defect.

## 5b. The research findings, folded in

The external pass completed 2026-08-12 morning, twelve tools, every claim
carrying a page actually opened. The load-bearing results:

**The gap is confirmed by the platform's own documentation.** Claude Code
already ships `/plugin`, `claude plugin details` (per-plugin hooks, agents,
skills, MCP servers), per-plugin context-cost estimates, and an
unused-plugin flag. It performs NO cross-plugin diff and NO conflict
detection between installed plugins; confirmed absent from
code.claude.com/docs/en/discover-plugins. Consequence for F1: the inventory
BUILDS ON the harness's own per-plugin enumeration where it exists rather
than re-parsing everything, and adds what the harness does not aggregate:
skills, settings layers, CLIs, and the cross-plugin view.

**The conflict fixtures are richer than this machine alone.** claude-mem
registers FIVE hooks (SessionStart, UserPromptSubmit, PostToolUse, Stop,
SessionEnd), keeps its own SQLite through a local worker service, and
assumes exclusive hook access (github.com/thedotmack/claude-mem).
claude-cortex writes into the same memory directory tree the harness's own
auto-memory uses (github.com/matteo-stratega/claude-cortex). Hookify lands
rules on the shared PreToolUse and Stop surface with cross-plugin ordering
undocumented (anthropics/claude-code hookify README). GSD owns `.planning/`
with its own machine-verifiable acceptance criteria per task
(github.com/open-gsd/gsd-core); arc owns `.arc/` and `docs/arc/` with a
seven-phase lifecycle (github.com/howells/arc); Compound Engineering owns
`docs/solutions/` and `docs/plans/` with its own learning loop
(github.com/EveryInc/compound-engineering-plugin). Two new conflict classes
follow: STATE-NAMESPACE COLLISION and DEFINITION-OF-DONE COLLISION, each
with a named real-world fixture.

**Routing identities are now concrete.** Product strategy: Compound
Engineering (`/ce-plan`, `/ce-brainstorm`) or BMAD-METHOD (nine personas,
PRD flow; its state-file footprint is UNCONFIRMED and is checked before any
route to it is enabled). Long phase planning: GSD-class. Full-SDLC
alternative: howells/arc. Search: Higgsfield exposes a hosted MCP server at
mcp.higgsfield.ai needing no API key (higgsfield.ai/mcp); Agent-Search most
plausibly means the self-hosted SearXNG MCP bundle (brcrusoe72/agent-search).
Cursor CLI is scriptable headless (`cursor-agent -p`, JSON output, MCP
client only, ACP for external driving: cursor.com/docs/cli/headless);
OpenHands exposes REST and WebSocket APIs and consumes MCP
(docs.openhands.dev). Both stay behind the connector model per section 5.

## 6. The loops, re-cut

Each loop names files and a done-check; forecasts are agent-clock, stated
raw with the calibration caveat (n=10, median 2.24x fast, spread 0.66 to
5.33; new-subsystem work sits near the slow end of that spread, so these are
ranges, not points).

| Loop | Builds | Files | Done-check | Agent clock |
|---|---|---|---|---|
| T0 | This plan ratified through 30 founder answers | this file | every answer recorded as a decision with its flip condition | wall clock, founder |
| T1 | Inventory | tools/bm_toolkit.py (new), store tables (additive, the R1.1 pattern) | `bm_toolkit.py inventory` lists skills, plugins, hooks, MCP servers, CLIs with source and version; run against THIS machine, output quoted | 60 to 150 min |
| T2 | Conflict detection | tools/bm_toolkit.py, a conflict-classes data file | the seven-Stop-hook and ten-PreToolUse facts above are FOUND by the tool, not by hand; every class in the founder's list has a fixture | 60 to 150 min |
| T3 | Capability records with static reach | store schema, tools/bm_toolkit.py | a record is DERIVED from artifacts; a hand-asserted record is visibly marked as such | 45 to 120 min |
| T4 | Routing table plus route command | tools/toolkit_routes.json, tools/bm_toolkit.py | `bm_toolkit.py route "task description"` names the capability, the reason, and what to do if it is absent | 45 to 120 min |
| T5 | Receipt schema and normalization | tools/bm_store.py (additive), tools/bm_toolkit.py | a receipt carries all nine fields; an un-normalizable output produces a NO-DATA receipt in a test | 60 to 150 min |
| T6 | The E2E pipeline, the founder's example | none new; composition | the five-step pipeline runs on one real change; one evidence packet delivered; every external step has a receipt | 90 to 240 min |
| T7 | Retention proposals | tools/bm_toolkit.py, store | after T6, `bm_toolkit.py retention` proposes a decision per capability used, from receipts, for founder ratification | 45 to 90 min |
| T8 | Doctor and gate integration | scripts/doctor.py, tools/test_all.py, five registries per PF-3 | doctor reports undeclared-use and conflict findings; suite in the gate | 45 to 90 min |

Total committed agent clock: roughly 7 to 19 hours. The binding constraint
is T0 and ratification, which is wall clock. Overflow beyond T8 goes to the
queue, never invented mid-build.

## 7. Ratified: the thirty answers, 2026-08-12

All thirty questions were put to the founder through the question windows
and answered the same morning. The full text of each decision, with its
alternatives and flip condition, is in the store against record
`toolkit-replan` (019b6008), decisions 1 through 30. The shape:

**Twenty-seven followed the recommended option**, locking: one product with
toolkit verbs inside BrotherMode; MVP is F1 plus F2 plus F4 complete with
routing as data and retention minimal; no trusted tier; proposal-only
installs with a named graduation criterion; report-plus-fix-command conflict
handling with three founder-editable severity classes, on demand plus doctor
under a one-second session-start budget, covering Claude Code surfaces plus
CLI version drift; routes as versioned JSON with BrotherMode's rerun as the
only closing authority, absent capabilities degrading to core, routing
orthogonal to model tiers; receipts as store rows with rerun-based
independence, NO-DATA for unverifiable output, DECLARED permissions;
retention by proposal with founder ratification, a three-green-receipt bar
for preferred, per-project scope, version-change as the only auto-demotion;
inventory-then-conflicts build order; the five-step pipeline on real cargo
(O4) as the literal exit test; Toolkit starting NOW as the only active lane
with v3.3.0 still cutting Friday on already-landed R1 work; internal
dogfood first; the toolkit name kept.

**Three are founder-shaped, and they are direction, not detail:**

- **TDD (decision 22):** routed to Superpowers now, with the door
  deliberately open to a minimal native TDD core later. The flip trigger is
  proven routing friction, measured rather than felt. Nothing native is
  built until that trigger fires.
- **Memory (decision 23):** the Obsidian vault is the memory backbone.
  External memory systems are routed read-only, co-used only when necessary
  and preferred. Standing direction: strengthen the vault with agent-memory
  database capabilities of the TencentDB agent-memory kind, semantic recall
  and episodic summaries. That is its own program item, outside Toolkit MVP.
  The store remains the sole delivery-state authority.
- **External executors (decision 24):** strictly last, after everything else
  in this plan, behind the connector model. The receipt schema carries an
  executor-identity field from day one so their receipts are representable
  when they arrive.

## 8. What kills it

Carried from the broker design and now measurable: if after a month no
capability has ever been demoted and no conflict finding has ever changed
what is installed, the broker is a registry with extra words, and the honest
move is to collapse it into the inventory command and say so.
