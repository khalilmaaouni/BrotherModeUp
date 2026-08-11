# Roadmap reclassification against PRODUCT-DIRECTION.md

Status: CURRENT. Written 2026-08-11 by session eefa5a42 (v3-refocus), per
PRODUCT-DIRECTION.md section 18 step 2. This table SUPERSEDES
docs/plan/ROADMAP-RANKED-2026-08-11.md and the wave structure of
docs/plan/PROGRAM-PLAN-2026-08-10.md and PROGRAM-PLAN-2026-08-11-RATIFIED.md
as the active plan. Those files stay in place as history and their standing
rules (two-lane law, RED first, receipts over narration, spend guard) remain
law. No em or en dashes.

Evidence base: three read-only inventory sweeps run 2026-08-11 by this
session's researcher agents over commands/, tools/, scripts/, docs/, mcp/,
schema and store, each claim carrying a file path. The pattern that forced
this table: three of eleven ranked items were already built or empty when
checked, so every row below records what was FOUND, not what was felt.

## The four lanes (PRODUCT-DIRECTION.md section 19)

1. Core verified-delivery path
2. Toolkit MVP
3. Trust and data lifecycle
4. External pilot and measurement

Everything active maps to one lane. Everything else is next, later, or
non-goal.

## The table

Columns per direction step 2: item, existing implementation found, product
layer, north-star contribution (CEVD/W or named guardrail), external
alternative, decision, done-check, kill criterion.

| # | Item | Found | Layer | North star | External alt | Decision | Done-check | Kill criterion |
|---|------|-------|-------|-----------|--------------|----------|-----------|----------------|
| 1 | Adoption L1 self-contained page | BUILT: bm_view.py renders one self-contained HTML, verified 23510 bytes, zero fetched refs | Core | Time to first visible value | none needed | DONE, absorb into V3 positioning | existing test asserting zero fetched references | n/a |
| 2 | Adoption L4 routing line | BUILT: README routes three situations, docs/ECOSYSTEM.md 431 lines 47 links | Core docs | Recommendability | n/a | DONE | docs suite green | n/a |
| 3 | Adoption L3 handover paper | BUILT: docs/HANDOVER-BY-HAND.md, linked from README | Core docs | Recovery without install | n/a | DONE | file exists, linked | n/a |
| 4 | SD2 stall sentinel | PARTIAL: bm_stall.py sweep on main, wired in bm_sessionstart.sh line 40; heartbeat durability on preserved branch wip/sd2-sentinel-2026-08-11-stopped-session | Core (recovery, stop controls) | Lost-state incidents, recovery success rate | none (internal state) | NOW, R1, FOUNDER GATE: resume branch (recommended, 1618 insertions preserved) or discard | seeded stall caught end to end | if unattended autonomy stays out of scope through R3, park the durability half |
| 5 | Ceremony opening half wired | NOT BUILT: no handover or detect call in bm_sessionstart.sh; blocking fence released 2026-08-11 by this session | Core (recovery) | Recovery success rate | none | NOW, R1 | fresh session skipping detect gets a refusal, test proves it | n/a, half day |
| 6 | Verification contract slice | PARTIAL: tasks.acceptance_checks is a flat string list, evidence attaches per task not per criterion; only controller_units links objective to check result | Core (verification) | Acceptance checks judged insufficient (guardrail) | test runners stay external per direction | NOW, R1: criterion ids, evidence.criterion_id, packet renders checked vs not checked vs remaining | delivery packet shows per-criterion evidence state; migration test green | if migration risks the 3011-test suite, ship rendering half first |
| 7 | Outcome contract columns | PARTIAL: projects table has goal, scope, success_criteria, risks; NO kill_criteria, NO non_goals columns | Core (outcome contract) | Human decisions per delivery | spec kits imported, normalized by us | NOW, R1, additive columns mirroring risks JSON pattern | start CLI accepts both, CANVAS.md renders them | n/a, small |
| 8 | Toolkit MVP | MISSING mostly: no installed-capability inventory, no matcher, no trust inspection, no proposal, no cleanup; generic receipts exist (acceptance_checks, evidence) | Toolkit | CEVD/W via safe reuse of existing expertise | the ecosystem itself is the alternative, brokered not rebuilt | NOW, R2, exactly the 12-step MVP of direction P3, nothing more | inventory command lists installed skills, plugins, MCP servers, CLIs with provenance; one task completed through a recommended toolkit with receipts | if inventory alone exceeds one week, cut to Claude Code surfaces only |
| 9 | Evidence normalization 5.8 | MISSING: evidence table is generic pointer, no receipt model | Toolkit and Core seam | Evidence quality | n/a | NEXT, R2 with Toolkit receipts | receipt rows carry executor, versions, artifacts, claimed result, verification | n/a |
| 10 | Capability provenance 5.7 | PARTIAL: attribution answers who acted, not which external capability, whose, what version | Toolkit | Provenance guardrail | n/a | NEXT, R2 ledger | provenance row per acquired capability | n/a |
| 11 | Data lifecycle P4 | PARTIAL: deliver, purge exist in bm_project.py; NO dry-run flag (line 1564 area); SECURITY.md exists | Trust | Data-lifecycle incidents (guardrail) | n/a | NOW, R0 (purge dry-run AND data locations doctor check, the latter moved forward from R3 by decision D6, 2026-08-11) plus R3 completion (purge proof documentation, reporting enablement, synthetic paths sweep) | dry-run prints what would be removed, removes nothing, test proves it | n/a |
| 12 | Adoption L2 status-page-first contact | NOT BUILT | Pilot | Time from install to first visible value | none equivalent | NEXT, R3 pilot prep, kill criterion kept verbatim | page about a stranger's repo says something its owner did not know | if the page says nothing new, it dies, ratified |
| 13 | Adoption L5 measurement reader | EMPTY ON PURPOSE: views table has 7 rows, one session; every threshold NOT DECIDABLE | Pilot measurement | CEVD/W counting | n/a | LATER, R4 when pilot rows exist | reader reports thresholds against real rows | build only when rows exist, per direction P6 |
| 14 | Benchmark B1 | HARNESS BUILT: scripts/benchmark_comparative.py, docs/BENCHMARK-COMPARATIVE.md; run not executed | Pilot proof | External proof | pilot IS the evidence per direction P5 | LATER, R4 optional, behind pilot | 25-task two-arm run published | if pilot yields 10 confirmed deliveries first, benchmark is optional |
| 15 | CC generated command center | GENERATOR NOT FOUND: board is hand-maintained; bm_view.py generates a different artifact | Internal | none direct (Rule 11: external proof outranks internal elegance) | n/a | LATER, parking lot | n/a | flip: two consecutive board drift incidents |
| 16 | G1 governor, graph work, C1, D1 | NOT BUILT | Internal | none of the three gaps | n/a | LATER, parking lot, flip conditions stand | n/a | flip: real incident traces to missing governor |
| 17 | V1 cross-model verifier | NOT BUILT | Core (later) | Independent review guardrail | reviewer models exist, brokered | LATER, direction's own backlog names it after 5 users | n/a | n/a |
| 18 | Codex port CX | PHASE 0 ONLY: docs/program/codex-port/ has two baseline files | Runtime expansion | frozen per direction step 3 | Codex, Cursor reached as compatible executors through Toolkit instead | LATER: no verified-runtime port until an external adopter asks; executor adapters via Toolkit when pilot demands | n/a | flip verbatim: an outside adopter asks, or benchmark shows runtime choice blocks adoption |
| 19 | SL self-learning quick and deep | PARTIAL: records parked (sl-quick rf2-rf4, rf5-rf1) | Toolkit Learn stage | Better selection over time | n/a | LATER, folds into Toolkit Learn (direction 8.7), never silent core mutation | n/a | n/a |
| 20 | Ecosystem weekly refresh | BUILT, unarmed: docs/ECOSYSTEM-REFRESH.md, 30-day staleness gate FAILs build | Trust | Credibility guardrail | n/a | NEXT, R3, needs one founder yes (weekly token spend) | scheduled run refreshes stamp, gate stays green | n/a |
| 21 | MCP write tools | NOT BUILT, read-only server exists (mcp/bm_mcp_server.py) | Core seam | direction 9.2: only after read surface has e2e coverage | n/a | LATER | n/a | n/a |
| 22 | RF-3 prose fence retirement | STORE IS SOLE FENCE except the SBE prose fence in STATE.md, which blocked README.md TODAY with a dead owner, the exact two-parsers failure it predicts | Core hygiene | Silent conflict guardrail | n/a | NOW, R1, evidence: this session, 2026-08-11 | grep for live prose fences returns empty, hook path unaffected | n/a |
| 23 | Watchdog cron pattern | RETIRED: no cron armed anywhere, verified this session | n/a | n/a | n/a | REMOVE from plans, SD2 supersedes | crontab and CronList empty, verified | n/a |

## Non-goals restated (direction section 15, park indefinitely)

New planning methodology, new TDD framework, new editor, model router,
deployment platform, issue tracker, general cloud execution, OS sandbox,
skill clones, public marketplace, enterprise RBAC, autonomous safety-rule
modification, unattended production deployment.

## Open founder items carried forward

1. SD2: resume preserved branch or discard (R1 gate, resume recommended).
2. SKILL.md ceremony amendment: founder-owned, pending in vault.
3. Vault name in public history: decide before pilot (R3 trust sweep).
4. Weekly ecosystem refresh arming: one yes, weekly token spend (R3).
5. Machine: 4 GB regenerable caches clearable on his word (not product).
