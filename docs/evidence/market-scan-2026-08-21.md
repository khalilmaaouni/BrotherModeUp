Status: CURRENT. Market scan run 2026-08-21 for the strategy review session
(bm1-9564f2d6). Produced by one read-only research subagent (sonnet tier, web
access, no file writes); landed verbatim below by the orchestrator, because a
summary of a scan is its author marking his own work. Adoption numbers were
read from the GitHub API the same day unless a line says otherwise; figures
the scan could not confirm against a primary source are labeled UNVERIFIED in
place. This file feeds the 2026-08-21 command center refresh and the rollout
plan on docs/plan/GANTT.html.

# The Claude Code orchestration market, scanned 2026-08-21

## Findings

Verified via direct primary-source fetch (GitHub API `api.github.com/repos/...`
unless noted): star/fork/push data below is first-party, not blog-derived,
checked 2026-08-21.

| Name | What it is | Adoption signal | Strongest capability | Weakest gap |
|---|---|---|---|---|
| obra/superpowers | Skills framework plus dev methodology (brainstorm, plan, TDD, review) | 275,177 stars, 24,620 forks, pushed 2026-08-19 ([api.github.com/repos/obra/superpowers](https://api.github.com/repos/obra/superpowers)) | Huge community skill library (obra/superpowers-skills), cross-harness (Claude Code, Cursor, Codex) | No execution-provenance layer: no mandatory quoted done-check, no single-writer fencing, no handover ceremony between sessions. It plans and codes, it does not attest |
| ultrapowers (fork ecosystem) | Research-first fork of superpowers, adds pre-code research pipeline | Canonical fork's own star count UNVERIFIED: search only surfaced scattered unofficial forks (e.g. ennio-datatide/ultrapowers); no authoritative repo confirmed | Adds a research and verification gate superpowers lacks | Fragmented forks, no single canonical adoption number, same gap as parent on evidence trails |
| ruvnet/claude-flow ("Ruflo") | Swarm orchestrator, 60+ agent swarms, SWE-bench framed | 68,528 stars, 8,234 forks, pushed 2026-08-20 ([api.github.com/repos/ruvnet/claude-flow](https://api.github.com/repos/ruvnet/claude-flow)); rename to "Ruflo" corroborated by two secondary sources ([pasqualepillitteri.it](https://pasqualepillitteri.it/en/news/774/claude-flow-ruflo-multi-agent-orchestration-guide), [dev.to](https://dev.to/stevengonsalvez/claude-flow-the-multi-agent-swarm-orchestrator-before-it-got-a-new-name-4kd4)) but not primary-confirmed | Scale (60+ parallel agents), 170+ MCP tool integration | Throughput-optimized, not evidence-optimized: no cited done-check discipline; benchmark claims (84.8% SWE-bench, 75% cost savings) are single-sourced marketing, UNVERIFIED here |
| automazeio/ccpm | GitHub Issues plus worktrees PM system, spec to epic to issue to code | 8,347 stars, 836 forks, pushed 2026-03-18, 5 months stale as of today ([api.github.com/repos/automazeio/ccpm](https://api.github.com/repos/automazeio/ccpm)) | Traceability from spec to code via GitHub Issues | Stale maintenance; traceability is planning-side, not verification-side (no proof a merged change actually passed its check) |
| buildermethods/agent-os | Spec-driven codebase-standards injection | 5,309 stars, 826 forks, pushed 2026-05-05, 3.5 months stale ([api.github.com/repos/buildermethods/agent-os](https://api.github.com/repos/buildermethods/agent-os)) | Standards and spec consistency across agents | No multi-session or multi-agent coordination story at all |
| hesreallyhim/awesome-claude-code | Canonical curated list | 52.7k stars (opened page directly, single-sourced to the page itself) ([github.com/hesreallyhim/awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code)) | List placement is itself the discovery channel for this ecosystem | No provenance or audit-trail category exists in it today (checked, not present) |
| REMvisual/claude-handoff | Session handoff skill, closest existing thing to an evidence gate (self-validation, evidence mining) | 44 stars, 4 forks, pushed 2026-05-23 ([api.github.com/repos/REMvisual/claude-handoff](https://api.github.com/repos/REMvisual/claude-handoff)) | Only found plugin using the words evidence plus validation gate for handoffs | Trivial adoption (44 stars): the niche BrotherMode targets is empirically wide open |
| Anthropic native (Claude Code core) | Subagent forking, background agent spawns, /code-review as background subagent, cross-session SendMessage, self-hosted runners, Remote Control and cloud sessions, plugin marketplace | Confirmed via primary changelog with dated entries (2.1.212 to 2.1.238, Jul to Aug 2026) ([code.claude.com/docs/en/changelog](https://code.claude.com/docs/en/changelog)); official marketplace "250+ plugins", community catalog "2,000+" is UNVERIFIED (only found in a secondary blog aggregation, no primary count page) | Owns the substrate: forking, background execution, cross-session messaging, cloud runners are now free and native | No mandatory evidence or attestation layer on top of any of it: orchestration primitives exist, provenance discipline does not |
| Provenance and attestation research (SLSA, in-toto for AI code) | Academic and governance discourse, not a shipped Claude Code tool | No adoption number found; multiple 2026 papers and blogs describe the need (Zylos, Augment Code, Cloudsmith, arXiv 2604.05485 "Auditable Agents") but none names a competing Claude Code plugin | Frames the problem precisely: signed origin metadata, tamper-evident write-once audit trails, delegation-chain reconstruction | Entirely unimplemented in the plugin ecosystem as of this search: a real category, currently empty |

## 5 differentiation opportunities

1. Ship the mandatory quoted done-check as a first-class artifact: no
   orchestration framework surveyed (superpowers, claude-flow, CCPM, agent-os)
   enforces evidence-before-done; they orchestrate work, not proof of work.
2. Own the handover and session-continuity plus evidence intersection:
   REMvisual/claude-handoff proves demand exists but sits at 44 stars with no
   verification-gate depth; a fenced single-writer ceremony with receipts is a
   wide-open lane.
3. Build the change-passport, SLSA-style attestation seam the research
   literature (arXiv 2604.05485, Zylos governance report) describes but no
   plugin implements: first mover in a named-but-unbuilt category.
4. Target CCPM's and agent-os's staleness (5 and 3.5 months without a push)
   directly: same PM and spec-driven audience, but with active maintenance and
   audit trails they lack.
5. Solve the multi-agent attribution gap flagged by governance research (who
   verified this, delegation-chain reconstruction): claude-flow's 60-agent
   swarms and Anthropic's own background and cross-session agents make this
   worse as scale grows, not better; BrotherMode's single-writer fencing is a
   direct answer nobody else ships.

## 3 threats

1. Commoditization by the harness itself: subagent forking, background spawns,
   cross-session SendMessage, self-hosted runners, and /code-review as a
   background subagent are now native (confirmed dated changelog entries
   through 2.1.238). Anything BrotherMode built purely as "make subagents
   coordinate" is now free.
2. Superpowers' scale (275k stars, active daily pushes) makes it the default
   on-ramp for any new user searching for Claude Code skills, crowding
   discovery regardless of feature depth.
3. Marketplace list-placement risk: if Anthropic or a major aggregator
   (awesome-claude-code, 52.7k stars) ever adds a provenance or audit category
   and a competitor claims it first, BrotherMode loses the naming advantage
   even if it built the better implementation.

## Market leader, concretely

In this ecosystem, market leader is observable as: GitHub stars and forks on
the plugin repo (the primary comparison axis used by every source above, from
CCPM's 8.3k to superpowers' 275k), placement in hesreallyhim/awesome-claude-code
and the official anthropics/claude-plugins-official marketplace, and install
or adoption counts where the marketplace exposes them (the official
marketplace listing itself was found but its aggregate install-count figures
were only secondary-sourced and are UNVERIFIED here).
