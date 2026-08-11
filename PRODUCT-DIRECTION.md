# BrotherMode Product Direction for Fable

Status: FOUNDER DIRECTION

Purpose: Re-scope and finalize BrotherMode around a clear market position, a measurable north star, a small independent core, and a Toolkit Mode that composes trusted external skills, MCP servers, CLIs, and agent runtimes instead of duplicating them.

Recommended repository location: `PRODUCT-DIRECTION.md` at the repository root.

Once committed, this document should be read before any roadmap change, architecture decision, new public command, runtime adapter, plugin, skill, MCP server, or autonomous capability is approved.

---

## 1. The decision

BrotherMode is not another coding agent.

BrotherMode is not a replacement for Claude Code, Cursor, Codex, Cline, GitHub Copilot, OpenHands, Superpowers, GSD, BMAD, Spec Kit, OpenSpec, or the growing Agent Skills ecosystem.

BrotherMode is the layer that makes serious AI-assisted work:

- Durable across sessions
- Controlled while it is being executed
- Composable with the best available expertise
- Recoverable after interruption
- Reviewable before acceptance
- Evidence-backed before delivery

BrotherMode should own the delivery contract.

Other products can own the model, editor, planning methodology, domain expertise, cloud runtime, code intelligence, deployment system, issue tracker, sandbox, or specialist workflow.

The product wins when it uses those capabilities well and still preserves the one thing they do not jointly guarantee:

> The original intent survives the work and reaches a verified, review-ready delivery.

---

## 2. Final positioning

### Category

**Verified delivery layer for AI agents**

### Current launch positioning

**The reliability layer for serious Claude Code work**

Claude Code remains the first fully supported runtime because this is where BrotherMode's lifecycle hooks and enforcement have been behaviorally verified.

Cross-runtime support must be described by exact capability level, never by a generic claim that BrotherMode works the same everywhere.

### One-line positioning

> BrotherMode is the verified delivery layer for serious AI-agent work. It preserves intent, controls execution, assembles the best available skills and tools, and requires evidence before delivery.

### Final tagline

> **From intent to verified delivery.**

### Supporting message

> Resume the work. Control the execution. Prove the result.

### The enemy

The enemy is not another product.

The enemy is AI work that looks complete but cannot be trusted, resumed, explained, or handed over.

BrotherMode exists to prevent or expose three failures:

1. **Forgotten**: the agent loses the goal, constraints, decisions, or next intent.
2. **Conflicted**: two workers change overlapping work without controlled ownership.
3. **Unproven**: the agent claims completion without current, meaningful acceptance evidence.

---

## 3. The north star

### Long-term product north star

> Every serious AI-assisted task ends in a resumable, review-ready, evidence-backed delivery.

### Primary north-star metric

> **Confirmed External Verified Deliveries per Week**

Abbreviation: **CEVD/W**

The word `External` is mandatory during the current phase. Founder dogfooding, simulated projects, fixture runs, test suites, benchmark scenarios, and projects completed only on the founder's machine do not count.

### A delivery counts only when

1. A non-founder user runs BrotherMode on a real repository or real deliverable.
2. The task is substantial enough to justify a delivery protocol.
3. A written outcome and acceptance contract exist before implementation finishes.
4. The work crosses at least one real boundary, such as a second session, compaction, interruption, worker handoff, or parallel workstream.
5. Ownership conflicts are resolved or proven absent on the supported surface.
6. Required acceptance checks run after the final relevant change.
7. The delivery packet names what was delivered, what was checked, what was not checked, and what remains.
8. The user accepts the delivery.
9. The delivery is not reopened for material rework within seven days.

### Delivery states

- **Provisional verified delivery**: accepted at delivery time.
- **Confirmed verified delivery**: no material reopen within seven days.

Only confirmed deliveries count in CEVD/W.

### Quality guardrails

The north star must never be increased by lowering standards. Track these beside it:

- Seven-day material reopen rate
- Lost-state incidents
- Recovery success rate
- Silent supported-path conflict count
- False-refusal rate
- Hook failure and fail-open rate
- Acceptance checks later judged insufficient
- Time from install to first visible value
- Time from project start to first verified delivery
- Human decisions required per delivery
- Additional elapsed time and model cost versus baseline
- Data-lifecycle or privacy incidents

### Metrics that are not the north star

Do not optimize the product around:

- GitHub stars
- Installs
- Sessions
- Agents spawned
- Tokens processed
- Test count
- Lines of code
- Skills installed
- MCP servers connected
- Tool calls
- Files claimed
- Delivery packets generated
- Time spent autonomously

Activity is not delivery.

---

## 4. Who BrotherMode works for

### Primary persona

**The technical solo founder, senior solo builder, or maintainer using AI agents on serious multi-session work.**

This person:

- Is accountable for the final outcome
- Already uses Claude Code or another serious coding agent
- Works on production repositories or reusable technical artifacts
- Runs multi-file and multi-session tasks
- Sometimes uses parallel workers or multiple agent sessions
- Has experienced context loss, stale evidence, rework, or conflicting edits
- Understands Git and can use a terminal
- Values dependable delivery more than the fastest first draft
- Wants local ownership and inspectable records

Their job to be done is:

> Let me delegate serious work to AI without repeatedly explaining the project, losing decisions, colliding with another worker, or accepting a false claim of completion.

### Secondary persona

**The AI-native maintainer, agency lead, fractional CTO, or technical project owner working across several repositories.**

This person needs repeatable handovers, client-ready delivery evidence, clear project separation, and reliable recovery. They still represent one accountable operator, not a large multi-user control plane.

### Later persona

**The privacy-sensitive individual contributor or small technical team.**

This persona becomes a priority only after BrotherMode has a stronger threat model, private vulnerability reporting, simpler data purge, and external security review.

### Anti-personas

BrotherMode is not currently for:

- A no-code user who wants an instant website or app
- A casual user making a one-line reversible edit
- A user unwilling to use Git or a terminal
- A team seeking shared accounts, role-based access, approvals, and enterprise project management
- A buyer seeking the best model, editor, or cloud coding runtime
- A user wanting GitHub-native background delegation with no local environment
- A user expecting full operating-system containment
- A user expecting autonomous production deployment without a human gate
- A team that only needs a planning methodology or TDD workflow

Disqualifying the wrong user is a product strength.

---

## 5. What BrotherMode must own independently

These are the core capabilities. BrotherMode must provide them independently because they define the product promise.

### 5.1 Outcome contract

BrotherMode owns the durable statement of:

- Desired outcome
- Scope
- Constraints
- Acceptance criteria
- Risks
- Human gates
- Spending and time ceilings
- Kill criteria
- Explicit non-goals

External specifications can be imported, but BrotherMode must normalize them into its own delivery contract.

### 5.2 Durable project state

BrotherMode owns the record of:

- Current goal
- Decisions and reasons
- Active work
- Next intent
- Claims and ownership
- Open risks
- Acceptance status
- Evidence
- Handover state
- Delivery state

The state must survive chat loss, compaction, session death, and runtime changes.

### 5.3 Work identity and ownership

BrotherMode owns:

- One identity per substantial unit of work
- Explicit ownership of claimed paths
- Conflict detection on the supported surface
- Transfer, park, adopt, resume, and close semantics
- Exact disclosure of what is prevented, detected, advisory, or unsupported

### 5.4 Authorization and autonomy boundaries

BrotherMode owns:

- What an autonomous worker is allowed to do
- Write scope
- Read scope
- Time ceiling
- Spend ceiling
- Session and chain-depth ceilings
- Human approval gates
- Stop and revoke behavior
- Visible degraded-safety state

No external skill, plugin, MCP server, CLI, or runtime may weaken these boundaries.

### 5.5 Verification contract

BrotherMode owns the connection between:

- Acceptance criterion
- Risk or failure mode
- Verification method
- Command or inspection
- Result
- Time and sequence relative to the last change
- Known omissions
- Independent review when the risk requires it

Freshness is necessary but not sufficient. A check that ran after the final edit can still be the wrong check.

BrotherMode must therefore evolve from:

> A command ran after the final edit.

To:

> Every acceptance criterion has meaningful current evidence, and the delivery says what remains unproven.

### 5.6 Recovery, handover, and delivery

BrotherMode owns:

- Safe recovery after interruption
- A successor-readable handover
- A clear FINISHED or UNFINISHED state
- A delivery packet
- A record of what was intentionally not done
- A single recommended next action when unfinished

### 5.7 Capability provenance

Toolkit Mode makes capability provenance part of the core.

BrotherMode must know:

- Which external skill, plugin, MCP server, CLI, or runtime was used
- Who published it
- Which version or commit was used
- What permissions it required
- Whether it used the network
- What it could read and write
- Which task it was selected for
- Whether it succeeded
- Which evidence it produced
- Whether it should be retained, disabled, removed, or preferred later

### 5.8 Evidence normalization

External tools can return different outputs. BrotherMode must normalize them into a common receipt model:

- Work packet
- Executor identity
- Capability versions
- Artifacts changed
- Claimed result
- Raw evidence location
- Independent verification result
- Exceptions and omissions

This is how BrotherMode remains the delivery layer without becoming the executor of everything.

---

## 6. What BrotherMode should not rebuild

BrotherMode should connect to these capabilities rather than copy them.

| Capability | Preferred owner |
|---|---|
| Frontier model intelligence | Claude, OpenAI, Google, or another model provider |
| Code editor and diff UX | Cursor, VS Code, JetBrains, Claude Code, or another editor |
| Test-driven development methodology | Superpowers or another specialist skill |
| Product and architecture methodology | GSD, BMAD, Spec Kit, OpenSpec, or another framework |
| Issue tracking and collaboration | GitHub, Jira, Linear, or equivalent through MCP or CLI |
| Code hosting and review | GitHub, GitLab, or equivalent |
| Cloud execution | Copilot coding agent, Cursor background agents, OpenHands, or another executor |
| Model-provider choice | Cline, OpenHands, or the host runtime |
| Deployment and hosting | Netlify, Vercel, cloud providers, or project-specific tools |
| Code intelligence | LSP servers and language-specific plugins |
| Full sandboxing | Containers, worktrees, hosted runners, or specialized runtimes |
| Domain expertise | Trusted Agent Skills and specialist plugins |
| Data and SaaS connectivity | MCP servers or official CLIs |
| Multi-user enterprise control plane | Existing project-management and identity systems |

The rule is:

> Own the contract. Reuse the capability.

---

## 7. Product architecture

BrotherMode should be organized into four layers.

```text
Upstream intent, specifications, issues, and constraints
                         |
                         v
                 BrotherMode Core
      outcome contract, state, ownership, authority,
       verification, recovery, handover, delivery
                         |
                         v
                 Toolkit Broker
      Agent Skills, plugins, MCP servers, CLIs,
         runtime workers, LSPs, specialist tools
                         |
                         v
         Downstream execution and external systems
       code, PRs, documents, tests, deployments, data
                         |
                         v
                Evidence returns to Core
```

### 7.1 Core

Core stays small, runtime-neutral where possible, and independently testable.

It contains:

- Store
- Outcome contract
- Work records
- Claims
- Authorization
- Verification contract
- Evidence ledger
- Recovery and handover
- Delivery packet
- Capability provenance
- Policy and stop controls

### 7.2 Runtime adapters

A runtime adapter only answers:

- How does this runtime receive the BrotherMode law?
- How does it receive a work packet?
- Which lifecycle hooks actually fire?
- Which writes can be refused?
- How does it return artifacts and evidence?

An adapter must not create a second control plane.

Runtime support levels must be explicit:

1. **Verified runtime**: BrotherMode hooks and core controls have passed a live behavioral canary.
2. **Compatible executor**: receives work and returns evidence, but some controls are advisory or external.
3. **Instruction-only runtime**: can read the law and use the CLI, with no enforcement claim.
4. **Unsupported**: no maintained integration.

Claude Code remains the verified runtime.

### 7.3 Toolkit Broker

Toolkit Mode discovers, evaluates, composes, installs, invokes, measures, and retires external capabilities.

It is a broker, not a marketplace and not a new agent runtime.

### 7.4 Evidence adapters

Evidence adapters translate external results into the BrotherMode verification contract.

Examples:

- A GitHub pull request becomes an artifact plus review status.
- A test CLI produces a verification receipt.
- A deployment platform returns a preview URL and build status.
- A design tool returns an exported artifact and review checklist.
- A specialist skill returns a report that still requires independent acceptance against the original outcome.

---

## 8. Toolkit Mode

### 8.1 Purpose

Toolkit Mode gives BrotherMode the expertise it does not own.

It should answer:

> What existing capability can help complete this task safely and well, and how do we prove that it helped?

Toolkit Mode must not become an excuse to install everything, create uncontrolled dependencies, or let third-party instructions override BrotherMode's laws.

### 8.2 The Toolkit loop

Use the following five-stage model:

> **Find. Trust. Compose. Prove. Learn.**

#### Find

Search in this order:

1. Capabilities already installed and proven in this project
2. Capabilities already installed for the user
3. BrotherMode core capabilities
4. Official host-runtime plugins and official MCP integrations
5. Trusted, allowlisted publishers
6. Community skills with inspectable source
7. A thin adapter around an existing CLI or API
8. New BrotherMode code only when the capability is part of the independent core

The search must stop when the minimum sufficient capability set is found.

#### Trust

Before activation, inspect:

- Publisher and source repository
- Official or community status
- Version or immutable commit
- License
- Install scope
- Files read and written
- Network access
- Credentials required
- MCP tools exposed
- Bundled scripts or binaries
- Hooks and lifecycle effects
- Transitive dependencies
- Known security findings
- Uninstall and cleanup behavior

A skill description, MCP annotation, plugin manifest, or publisher claim is not proof. Treat it as untrusted metadata until the source or behavior is inspected.

#### Compose

Select the smallest toolkit required for the task.

A typical composition can include:

- One procedural skill
- One or more MCP servers for external systems
- One deterministic CLI
- One executor runtime
- One independent verifier

Do not install multiple overlapping capabilities unless the task explicitly requires comparison or independent review.

#### Prove

Every external capability must produce or contribute to evidence against the BrotherMode acceptance contract.

BrotherMode reruns or independently checks what matters. It does not accept the external capability's self-report as final proof.

#### Learn

Record:

- Task type
- Capability used
- Version
- Why it was selected
- Inputs and boundaries
- Outcome
- Verification result
- Failure or rework
- Cost and time
- User correction
- Whether it should be preferred next time

Learning means better selection and better recipes. It does not mean silently rewriting core safety rules.

### 8.3 Capability maturity states

Every external capability should move through explicit states:

1. **Discovered**: metadata found, not inspected.
2. **Inspected**: source, permissions, and provenance reviewed.
3. **Sandboxed**: run in an isolated or throwaway environment.
4. **Task-proven**: succeeded once on a real task with independent verification.
5. **Project-trusted**: succeeded repeatedly in one project.
6. **Preferred**: repeatedly successful across relevant tasks and approved for automatic recommendation.
7. **Blocked**: unsafe, misleading, incompatible, or repeatedly ineffective.

No capability becomes preferred because it is famous, highly starred, or widely installed. Reputation is a discovery signal, not a verification result.

### 8.4 Trust tiers

#### Tier 0: BrotherMode core

- Independently maintained
- Fully covered by BrotherMode's own gates
- Required for the central promise

#### Tier 1: Official vendor capability

Examples include an official host-runtime marketplace, official MCP server, official CLI, or official Agent Skill.

Toolkit Mode may recommend these automatically.

Installation still requires a visible authorization unless the user has granted a bounded task-level policy allowing Tier 1 local installs.

#### Tier 2: Curated trusted publisher

- Known publisher
- Inspectable source
- Pinned version
- Compatible license
- Reviewed permission surface
- Prior task evidence

Toolkit Mode may propose installation and can auto-install only under an explicit project policy.

#### Tier 3: Community capability

- Inspectable but not pre-trusted
- Manual approval required
- Sandbox required before project use
- Local scope only
- No automatic credential access

#### Tier 4: Unknown or opaque capability

- No autonomous installation
- No execution on a real project
- May be analyzed in isolation

### 8.5 Installation policy

Default rules:

- Prefer local or project scope, not user-global scope.
- Pin a version, release, or commit.
- Record checksums and provenance.
- Show the permission summary before installation.
- Never request secrets through model-visible text.
- Use host-native credential and OAuth flows.
- Test in a throwaway environment first where practical.
- Disable or remove task-specific capabilities after delivery unless retention is justified.
- Record all persistent changes to settings and plugin state.
- Provide one cleanup command that reverses the installation.

### 8.6 Autonomous installation policy

Autonomous downloading is a goal, but it must be staged.

#### Toolkit MVP

- Discover installed skills, plugins, MCP servers, and CLIs
- Recommend the minimum toolkit
- Inspect provenance and permissions
- Install from official or allowlisted sources only
- Require one visible approval for the toolkit plan
- Use local scope by default
- Pin version or commit
- Record the capability manifest
- Verify installation
- Use the capability
- Remove or disable it after the task when it was task-specific

#### Later autonomous mode

Automatic installation without a per-install prompt is allowed only when:

- The user has signed a bounded project policy
- The source is Tier 1 or approved Tier 2
- The install is local or project scoped
- No new credential class is introduced
- No safety hook is added or changed
- The capability stays within the task's read and write scope
- The version is pinned
- A rollback is prepared first
- The installation is recorded visibly

Community capabilities never become auto-installable based only on popularity.

### 8.7 Becoming more expert over time

BrotherMode should learn expertise in three layers.

#### Layer 1: Capability memory

Remember which skills, tools, MCP servers, and CLIs work well for which tasks.

#### Layer 2: Proven recipes

Record small compositions that worked, such as:

- Spec Kit plan + Superpowers TDD + pytest + GitHub PR
- Figma MCP + frontend skill + Playwright + screenshot review
- Data-analysis skill + database MCP + notebook CLI + validation query

A recipe references external capabilities. It does not copy their implementation.

#### Layer 3: Promoted local skill

Create a persistent BrotherMode-owned skill only when:

1. The workflow has succeeded at least three times.
2. The need is not already solved by a maintained external skill.
3. The workflow is specific to the user, project, or BrotherMode core.
4. A human approves its promotion.
5. Its permissions and dependencies are explicit.
6. It has a test or reproducible done-check.

Before this threshold, keep the workflow as a task-local recipe.

### 8.8 Upstream and downstream behavior

#### Upstream

When an external skill or plugin has a general defect:

- Reproduce it
- Preserve evidence
- Open an issue or patch upstream
- Avoid maintaining a permanent fork unless the upstream path is unavailable or the project needs an urgent bounded fix

#### Downstream

When BrotherMode needs to adapt an external capability:

- Build the thinnest possible wrapper
- Keep the external capability as the source of expertise
- Translate inputs into its expected form
- Translate outputs into BrotherMode receipts
- Do not copy its internal workflow into BrotherMode

This is how BrotherMode complements the ecosystem instead of consuming it.

---

## 9. MCP direction

### 9.1 What MCP is for

MCP is a standard transport for tools, resources, prompts, and structured interactions.

For BrotherMode, MCP should provide:

- Access to external systems and data
- A portable way for other runtimes to read BrotherMode state
- Structured tool discovery
- Standard schemas for inputs and outputs

MCP is not BrotherMode's orchestration engine and not its safety boundary.

### 9.2 BrotherMode as an MCP server

The existing read-only project server is the correct foundation.

Near-term MCP server scope:

- Project status
- Active work
- Claims and owners
- Decisions
- Outcome contract
- Acceptance criteria
- Evidence summary
- Handover state
- Delivery packet location
- Store health

Do not expand immediately into a broad write-capable MCP server.

Write operations should enter only after:

- The read-only surface has automated end-to-end coverage
- Project-root containment is proven
- Authorization is explicit
- Each mutation maps to an existing BrotherMode core command
- The user can see which server requested the action
- Sensitive credentials never enter the model context
- A rollback or compensating action exists

Potential later write tools:

- Claim work
- Record a decision
- Attach external evidence
- Request verification
- Submit a handover

These should be thin protocol adapters over core commands, not parallel implementations.

### 9.3 BrotherMode as an MCP client

Do not build a new general MCP host when the active runtime already supports MCP.

Toolkit Mode should:

- Discover host-configured MCP servers
- Inspect their tools and scopes
- Recommend the minimum relevant server
- Generate or update project-local MCP configuration when approved
- Call tools through the host runtime
- Normalize returned results into BrotherMode evidence

Build an internal MCP client only for a narrow capability that cannot be reached through the host and directly blocks a verified delivery.

### 9.4 MCP safety rules

- Treat tool descriptions and annotations as untrusted metadata.
- Require explicit consent for operations with external effects.
- Keep credentials out of prompts, skills, and BrotherMode records.
- Prefer OAuth and vendor-native credential flows.
- Bind authorization to the intended server and project.
- Do not pass one service's token through another MCP server.
- Record which MCP server and tool produced each receipt.
- Re-verify critical results outside the producing tool where possible.

---

## 10. CLI direction

CLIs are the lowest-common-denominator integration surface for deterministic local actions.

BrotherMode should prefer a mature CLI when:

- It is official or well maintained
- Its behavior is scriptable
- It can run non-interactively
- Its exit codes are meaningful
- Its output can be captured
- Its version can be pinned or reported
- Its side effects are understood

A CLI adapter should define:

- Detection command
- Version command
- Required credentials
- Read and write effects
- Working directory requirements
- Expected exit codes
- Output parser
- Timeout
- Cleanup behavior
- Verification strategy

Do not create a new wrapper command when the original CLI can already be called safely and its output can be normalized directly.

---

## 11. Agent Skills direction

Agent Skills are the preferred format for reusable procedural expertise.

BrotherMode should use the open skill format rather than creating a private competing format.

A skill is procedural knowledge. MCP is external capability and data. A CLI is deterministic local execution. A runtime is the agent environment. BrotherMode composes all four under one delivery contract.

### Rules

- Prefer portable `SKILL.md` skills.
- Keep skills focused and progressively disclosed.
- Load only the skills relevant to the task.
- Do not bundle broad global instructions into every session.
- Inspect bundled scripts before use.
- Respect the declared compatibility and license.
- Record the installed source and version.
- Never let a skill override BrotherMode's core gates.
- Prefer an external maintained skill over a BrotherMode duplicate.
- Promote task-local recipes into persistent skills only after repeated proof.

---

## 12. Public product surface

The public experience should stay small even if the internal engine remains rich.

Recommended user-facing surface:

1. `/brothermode:start`
2. `/brothermode:status`
3. `/brothermode:toolkit`
4. `/brothermode:verify`
5. `/brothermode:deliver`
6. `/brothermode:doctor`

Everything else should be:

- An internal subcommand
- An advanced CLI
- A hidden specialist skill
- A generated action from the status page

Do not add a seventh public command without removing, merging, or clearly proving why the existing six cannot carry the behavior.

The user should not need to understand the internal store, controller, ledger, sentinel, handover engine, runtime adapter, capability registry, or effect classes to complete a verified delivery.

---

## 13. Feature-sprawl control

### 13.1 Entry test for every roadmap item

No item enters active development until Fable answers all of these:

1. Which core promise does this serve?
2. How will it increase CEVD/W or reduce a named quality guardrail?
3. Is the capability already present in the repository?
4. Does a trusted external skill, MCP server, CLI, plugin, or runtime already solve it?
5. Why is a thin adapter insufficient?
6. What is the smallest vertical slice?
7. What evidence will show that it worked?
8. What is the kill criterion?
9. What is the removal or rollback path?
10. Which existing surface will be deleted, merged, or left unchanged?

If the item cannot answer questions 1 and 2, it goes to the parking lot.

If an external capability answers question 4, BrotherMode builds only the integration seam.

### 13.2 Reuse-before-build sequence

Fable must use this order:

1. Verify whether it already exists.
2. Reuse an installed capability.
3. Use an official plugin, skill, MCP server, or CLI.
4. Use an approved external capability.
5. Build a thin adapter.
6. Build new BrotherMode core code only when the capability is essential to the product promise.

### 13.3 Scope budget

For the finalization phase:

- One active core milestone
- One active Toolkit milestone
- One external-pilot lane
- Maximum two implementation lanes at once
- No new runtime adapter unless a pilot is blocked by runtime choice
- No new public command
- No new database subsystem unless required by the verification or capability-provenance contract

### 13.4 Evidence before expansion

A capability cannot expand to a second runtime, second installation mode, or second public surface before the first path has:

- One working end-to-end test
- One live canary
- One external user
- One documented failure and recovery path
- A cleanup or uninstall path

---

## 14. What to build now

The goal is a small, credible, externally usable release, not a complete vision.

### P0: Product authority and freeze

1. Commit this document as `PRODUCT-DIRECTION.md`.
2. Make the skill and roadmap point to it as the product authority.
3. Freeze all new capabilities for one review pass.
4. Classify every open item as:
   - Core release blocker
   - Toolkit MVP
   - External pilot blocker
   - Backlog
   - Non-goal
5. Check whether every supposed gap already exists before estimating it.
6. Close, merge, or park duplicate roadmap items.

Done when:

- Every active item maps to this document.
- Nothing active exists only because it is interesting or nearly finished.

### P1: One clean verified-delivery path

Finalize one end-to-end Claude Code path:

1. Start from a plain-language outcome.
2. Produce an outcome and acceptance contract.
3. Create durable work identity.
4. Claim write scope.
5. Execute through one or more sessions.
6. Recover correctly after an interruption.
7. Run criterion-linked verification after final changes.
8. Produce a delivery packet.
9. Reopen the project from the packet and state.

Done when:

- A new external user can complete the flow without reading internal documentation.
- The public experience uses the small command surface.
- The delivery packet clearly distinguishes verified, unverified, and excluded work.

### P2: Verification contract

Implement the minimum schema and flow connecting:

- Acceptance criterion
- Verification method
- Evidence
- Freshness
- Coverage explanation
- Known omission
- Final verdict

Do not build a general testing framework.

Use existing test runners, review skills, browser tools, CLIs, and MCP integrations.

BrotherMode owns only the contract and the receipt.

### P3: Toolkit MVP

Build only this first slice:

1. Inventory installed skills, plugins, MCP servers, CLIs, and runtime capabilities.
2. Match the task to required capabilities.
3. Prefer already installed capabilities.
4. Recommend the minimum toolkit.
5. Inspect source, version, license, permissions, network, credentials, and effects.
6. Install only official or allowlisted capabilities.
7. Use local scope by default.
8. Record provenance.
9. Verify installation in a throwaway or controlled path.
10. Execute the task.
11. Record outcome and evidence.
12. Disable or remove task-specific additions after delivery.

Do not build community-wide autonomous discovery, a BrotherMode marketplace, or automatic skill generation in the MVP.

### P4: Data lifecycle and trust

Before external promotion:

- One command shows every BrotherMode data location.
- One dry-run command shows what uninstall or purge will remove.
- Full project purge is proven.
- Full machine cleanup is documented.
- Plugin and Toolkit additions are reversible.
- Sensitive data never appears in public examples.
- Public repository paths are synthetic.
- Private vulnerability reporting is enabled.
- Security support and supported versions are stated.

### P5: External pilot

Recruit at least five qualified users.

Required pilot tasks:

- One multi-session task
- One forced interruption and recovery
- One parallel or ownership-sensitive task
- One Toolkit-assisted task
- One verified delivery
- One cleanup, disable, or uninstall check

Do not wait for a perfect benchmark before the pilot. The pilot is the evidence the project currently lacks.

### P6: Measurement

Measure:

- Confirmed external verified deliveries
- Time to first value
- Time to delivery
- Reopen rate
- Recovery success
- Conflicts caught and missed
- False refusals
- Toolkit recommendation acceptance
- Capability success by version
- Added time and cost
- User corrections

Do not build dashboards before the rows exist.

---

## 15. What goes to backlog

### Next, after five external users or twenty verified deliveries

- Automatic Tier 1 and approved Tier 2 local installs under a signed project policy
- GitHub pull-request evidence publishing
- Capability effectiveness scoring
- Proven recipe recommendations
- First external executor adapter selected by actual pilot demand
- Upstream issue and patch workflow for failed external skills
- Write-capable MCP tools over existing core mutations
- Independent verifier role for higher-risk work
- Improved fast path for small tasks

### Later

- Wider community skill discovery
- Automated sandboxing for unknown skills
- Signature and attestation support
- Multi-runtime behavioral certification
- Cursor, Codex, Cline, Copilot, and OpenHands worker adapters
- Cross-project capability memory
- Team-shared capability policies
- Visual Toolkit management UI
- Semantic capability search
- Automated promotion of repeated recipes for human approval
- Hosted optional services
- Multi-user coordination

### Park indefinitely unless external evidence changes the decision

- New internal planning methodology
- New internal TDD framework
- New code editor
- New model router
- New deployment platform
- New issue tracker
- General cloud execution platform
- General operating-system sandbox
- BrotherMode-owned clone of popular skills
- A broad public skill marketplace
- Enterprise project management and role-based access
- Autonomous modification of core safety rules
- Production deployment without an explicit human gate

---

## 16. Definition of finalization

BrotherMode is ready for a proof-led public release when:

### Positioning

- The README leads with the final positioning and tagline.
- The primary persona is named.
- Anti-personas are explicit.
- Claude Code is identified as the verified launch runtime.
- Other runtimes carry exact support labels.

### Product

- One clean start-to-deliver path works.
- The public surface is small.
- Simple tasks use a fast path.
- Complex tasks produce an outcome contract.
- Recovery is demonstrated.
- Claimed-file conflict behavior is accurately stated.
- Verification is criterion-linked.
- Delivery produces a portable packet.

### Toolkit

- Installed capabilities can be inventoried.
- Toolkit plans are minimal and inspectable.
- Official capabilities can be installed with provenance.
- Installation scope and permissions are visible.
- Task-specific additions can be cleaned up.
- External capability outputs become BrotherMode evidence.

### Trust

- Private vulnerability reporting exists.
- Data locations are visible.
- Purge and uninstall are proven.
- No personal paths or private names remain in public examples.
- No cross-runtime enforcement claim runs ahead of evidence.
- No unattended autonomy runs beyond proven stop controls.

### External proof

- At least five external users
- At least twenty substantial deliveries
- At least ten confirmed verified deliveries
- At least five real recovery or multi-session events
- At least five ownership-sensitive or parallel events
- Zero material state loss
- Zero silent conflict on the supported refused path
- Published failures and limitations

---

## 17. Fable operating instructions

Fable must treat these as binding product-development rules.

### Rule 1: Start from the delivery gap

Before writing code, state which verified-delivery failure the change prevents or which external-delivery metric it improves.

### Rule 2: Check before building

Inspect the current repository and installed ecosystem first. Several planned gaps have already turned out to be built or not worth building. Repeat that check for every item.

### Rule 3: Core or connector

Every capability must be classified as:

- BrotherMode core
- External capability
- Thin connector
- Backlog
- Non-goal

Do not allow a middle category called useful.

### Rule 4: Minimum sufficient toolkit

Use the fewest external capabilities needed. More skills and tools create more permissions, more instructions, more failure modes, and more context.

### Rule 5: No silent acquisition

Never download, install, enable, or retain a capability without a recorded source, version, scope, permission summary, and rollback path.

### Rule 6: No external capability can weaken the core

External skills, tools, MCP servers, or executors may narrow how work is done. They may not weaken ownership, authorization, evidence, privacy, or stop controls.

### Rule 7: Evidence returns to BrotherMode

The task is not complete because an external capability says it succeeded. Translate its output into a receipt and verify it against the acceptance contract.

### Rule 8: Upstream before fork

When an external capability is broadly wrong, contribute evidence or a fix upstream before creating a permanent BrotherMode fork.

### Rule 9: Learn selection, not uncontrolled behavior

Improve which capability is chosen and which recipe is recommended. Do not silently mutate core law or create persistent self-authored skills after one success.

### Rule 10: One vertical slice at a time

Complete one path from intent to verified delivery before expanding horizontally.

### Rule 11: External proof outranks internal elegance

A feature that helps an outside user complete a verified delivery outranks a cleaner internal graph, broader runtime matrix, larger dashboard, or more advanced autonomous controller.

### Rule 12: Delete or park to make room

Every meaningful new active item must either replace an existing active item or state why the total active scope does not increase.

---

## 18. Immediate execution plan for Fable

### Step 1: Establish authority

- Add this file at the repository root.
- Link it from `SKILL.md`, `README.md`, and the current roadmap.
- State that conflicting product-scope guidance is superseded.

### Step 2: Reclassify the current roadmap

Produce one table with:

- Item
- Existing implementation found
- Product layer
- North-star contribution
- External alternative checked
- Decision: now, next, backlog, remove
- Done-check
- Kill criterion

Do not implement during this pass.

### Step 3: Freeze runtime expansion

- Claude Code remains the verified runtime.
- Keep other adapters experimental or advisory.
- Do not complete another runtime port until a real pilot requires it.
- Preserve existing experimental work without letting it drive the release scope.

### Step 4: Finish the core vertical slice

Prioritize:

1. Outcome and acceptance contract
2. Durable state
3. Claims and ownership
4. Recovery
5. Criterion-linked verification
6. Delivery packet
7. Simple public commands
8. Data lifecycle

### Step 5: Build Toolkit inventory, not the whole vision

The first Toolkit release only needs:

- Inventory
- Capability matching
- Trust inspection
- Minimal toolkit proposal
- Official or allowlisted installation
- Provenance ledger
- Execution receipt
- Cleanup

### Step 6: Pilot immediately

Once the vertical slice and Toolkit MVP pass their gates, place them in front of external users. Do not add another major capability first.

### Step 7: Let evidence reorder the roadmap

After the first five external users, rerank everything based on:

- What blocked a verified delivery
- What users bypassed
- What users repeatedly asked for
- What caused rework
- Which external capabilities worked
- Which runtime demand was real

---

## 19. Copy-paste directive to Fable

```text
Fable, treat PRODUCT-DIRECTION.md as the product authority for BrotherMode.

Your objective is not to expand the product. Your objective is to finalize the smallest credible system that takes a serious task from intent to a confirmed verified delivery for an external user.

BrotherMode owns the outcome contract, durable state, work ownership, authorization boundaries, verification contract, recovery, handover, delivery packet, and capability provenance.

BrotherMode does not rebuild specialist skills, planning methods, editors, model runtimes, issue trackers, deployment platforms, code intelligence, sandboxes, or domain tools when maintained external capabilities exist.

Toolkit Mode must follow Find, Trust, Compose, Prove, Learn. It should prefer installed capabilities, then official or allowlisted skills, plugins, MCP servers, and CLIs. Every acquired capability needs source, version, permissions, scope, rollback, and a recorded task outcome. Use local scope by default. Do not auto-install unknown community code. No external capability may weaken BrotherMode's gates.

Before starting any roadmap item:
1. Verify whether it is already built.
2. Map it to the north star, Confirmed External Verified Deliveries per Week.
3. Check for an existing external capability.
4. Choose the smallest vertical slice.
5. Define evidence and a kill criterion.
6. Park it if it does not directly unblock an external verified delivery or protect a core promise.

Freeze new runtime expansion. Claude Code remains the verified launch runtime. Preserve experimental adapters but do not let them define the release.

Now produce a reduced roadmap with only four lanes:
1. Core verified-delivery path
2. Toolkit MVP
3. Trust and data lifecycle
4. External pilot and measurement

Everything else goes to next, later, or non-goal.

Do not write implementation code until the reclassification table is complete and duplicate or already-built items are removed.
```

---

## 20. Research and repository basis

This direction is grounded in the current BrotherMode repository and the relevant open integration standards.

### BrotherMode repository

- `README.md`
- `SKILL.md`
- `docs/market/CATEGORY.md`
- `docs/ECOSYSTEM.md`
- `docs/ROADMAP.md`
- `docs/RUNTIMES.md`
- `docs/KNOWN-LIMITS.md`
- `docs/plan/ROADMAP-RANKED-2026-08-11.md`
- `mcp/README.md`
- `capabilities.status.json`
- `hooks/hooks.json`

### External standards and official documentation

- Agent Skills specification: <https://agentskills.io/specification>
- Model Context Protocol specification: <https://modelcontextprotocol.io/specification/2025-11-25>
- MCP architecture: <https://modelcontextprotocol.io/docs/learn/architecture>
- Claude Code plugins: <https://code.claude.com/docs/en/plugins>
- Claude Code plugin reference: <https://code.claude.com/docs/en/plugins-reference>
- Claude Code plugin discovery and installation: <https://code.claude.com/docs/en/discover-plugins>
- Claude Code MCP integration: <https://code.claude.com/docs/en/mcp>

The official Claude plugin documentation explicitly warns users to trust plugins carefully because plugins can bundle skills, scripts, hooks, MCP servers, and other software. The official MCP specification likewise treats tool metadata as untrusted and emphasizes explicit user consent, data control, and authorization. Toolkit Mode must preserve those boundaries rather than hiding installation behind autonomy.

---

# Final summary

## What BrotherMode is

A verified delivery layer for serious AI-agent work.

## Tagline

**From intent to verified delivery.**

## Who it serves

Technical solo founders, senior builders, maintainers, and small technical leaders accountable for substantial multi-session work.

## What it owns

Intent, state, ownership, authority, verification, recovery, provenance, handover, and delivery.

## What it integrates

Skills, plugins, MCP servers, CLIs, coding agents, external systems, and specialist workflows.

## Toolkit Mode

**Find. Trust. Compose. Prove. Learn.**

## North-star metric

**Confirmed External Verified Deliveries per Week.**

## Immediate priority

Finish one external-user-ready Claude Code delivery path and the minimum Toolkit broker required to use existing expertise safely.

## Product rule

> Own the contract. Reuse the capability.
