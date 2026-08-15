# BrotherMode: The Integrity System Between Human Intent and AI Delivery

> **Stop thinking of BrotherMode as a better workflow around Claude Code. Build it as the integrity system between human intent and AI delivery.**

This document is repository-platform independent and is intended to live at the root of a BrotherMode repository hosted on **GitHub**, **Bitbucket**, or **Azure Repos / Azure Git**.

---

## 1. Product Thesis

BrotherMode is not another coding agent.

BrotherMode is not a replacement for Claude Code, Codex, Cursor, Cline, GitHub Copilot, BMAD, Superpowers, Spec Kit, OpenSpec, or other agent frameworks.

BrotherMode is the **delivery-control and integrity layer** that sits between:

**Human Intent → AI Execution → Verified Delivery**

Its job is to ensure that serious AI-assisted work:

- preserves the original intent
- survives session loss and interruption
- prevents conflicting ownership on supported writes
- exposes degraded safety instead of hiding it
- links acceptance criteria to current evidence
- refuses verified delivery when the delivery contract is not satisfied
- records what was checked, what remains unproven, and what was waived
- produces a delivery artifact that can be reviewed without reconstructing the entire conversation

The product does not win because it has more agents.

It wins because **the word “delivered” has a precise meaning**.

---

## 2. Category

### Primary category

**Integrity system for AI delivery**

### Launch positioning

**The delivery-control layer for serious AI-agent work**

### Current runtime positioning

**The reliability and delivery-control layer for serious Claude Code work**

Claude Code is the first fully verified runtime.

Cross-runtime support must always be described by measured capability level, never by implication.

---

## 3. Core Promise

BrotherMode should guarantee, on the surfaces it explicitly supports:

### Intent integrity

The original outcome, scope, constraints, non-goals, risks, acceptance criteria, and human gates remain durable throughout the work.

### Execution integrity

Work is identified, ownership is explicit, conflicting ownership is prevented where enforceable, and unsupported paths are disclosed.

### State integrity

A dead session does not erase the project state, current decisions, ownership, evidence, or next intent.

### Evidence integrity

Evidence is attached to the exact acceptance criterion it proves and becomes stale when relevant work changes.

### Delivery integrity

BrotherMode does not mark work as verified merely because the agent says it is done.

A verified delivery exists only when the delivery contract is satisfied.

---

## 4. The Delivery Transaction

Treat every substantial piece of delegated AI work as a **delivery transaction**.

The lifecycle is:

```text
INTENT
  ↓
CONTRACT
  ↓
RISK CLASSIFICATION
  ↓
PLAN / WORK GRAPH
  ↓
RESOURCE CLAIMS
  ↓
EXECUTION
  ↓
EVIDENCE
  ↓
FALSIFICATION / REVIEW
  ↓
DELIVERY GATE
  ↓
DELIVERY MANIFEST
  ↓
HUMAN ACCEPTANCE
  ↓
CONFIRMED DELIVERY
```

BrotherMode owns the transitions.

Agents perform the work.

External tools provide capabilities.

Git stores the change history.

CI runs machine checks.

BrotherMode decides whether the work satisfies the delivery contract.

---

## 5. The Delivery Contract

Every substantial project or work item must begin with a durable contract.

Minimum fields:

```yaml
outcome:
scope:
non_goals:
constraints:
acceptance_criteria:
risks:
kill_criteria:
human_gates:
time_ceiling:
spend_ceiling:
required_evidence:
```

The contract must be machine-readable and human-readable.

### Contract rule

No work can reach **VERIFIED DELIVERY** without an active contract.

### Contract amendments

If the scope changes, the contract is amended explicitly.

Do not silently rewrite history.

Record:

- what changed
- why
- who approved it
- which acceptance criteria changed
- which previous evidence became stale

---

## 6. Resource Ownership

File-level ownership is the first enforceable resource type, not the final model.

BrotherMode should evolve toward claims such as:

```text
file:src/payments.py
directory:src/billing/
module:billing
database:customers
api:/checkout
migration:2026_08_recurring_billing
release:v4
```

Every claim should have:

- work identity
- owner
- resource
- start time
- current lifecycle state
- transfer history
- enforcement level

### Enforcement levels

BrotherMode must never blur these states:

**ENFORCED**  
The operation can be prevented before it happens.

**DETECTED**  
The operation cannot reliably be prevented, but BrotherMode can detect it afterward.

**UNOBSERVED**  
BrotherMode cannot reliably see or control the operation.

This distinction is part of the product.

It is not an implementation detail.

---

## 7. Evidence Graph

BrotherMode should not store a flat list of tests.

It should maintain an evidence graph:

```text
Acceptance Criterion
        ↓
Required Verification
        ↓
Evidence Receipt
        ↓
Relevant Resources
        ↓
Current Revision
```

Each acceptance criterion gets a stable ID.

Example:

```yaml
criterion_id: AC-004
statement: Existing subscriptions continue charging unchanged
risk: high
required_evidence:
  - regression_test
  - migration_rehearsal
  - independent_review
```

Each evidence receipt records:

```yaml
criterion_id:
command_or_method:
executor:
runtime:
timestamp:
commit:
relevant_files:
result:
artifact_hash:
verification_status:
```

---

## 8. Evidence Freshness

Evidence should become stale only when relevant work invalidates it.

Example:

```text
AC-004 depends on:
  src/billing.py
  src/stripe_client.py
  tests/test_existing_subscriptions.py
```

A README edit should not invalidate AC-004.

A change to `src/stripe_client.py` should.

BrotherMode should maintain:

```text
resource → acceptance criterion → evidence
```

This allows precise re-verification instead of rerunning everything.

---

## 9. Risk-Adaptive Verification

Not every task deserves the same governance cost.

BrotherMode should classify work by risk.

### LOW

Examples:

- copy changes
- documentation fixes
- low-impact refactoring

Possible evidence:

- direct inspection
- targeted tests

### MEDIUM

Examples:

- product behavior changes
- ordinary application logic
- API modifications

Possible evidence:

- deterministic tests
- integration checks
- fresh-context review

### HIGH

Examples:

- authentication
- payments
- destructive migrations
- authorization
- data integrity

Possible evidence:

- deterministic checks
- rollback rehearsal
- independent agent review
- CI evidence
- explicit human gate

### CRITICAL

Examples:

- irreversible production operations
- security-sensitive changes
- major data migrations

Possible requirements:

- independent review
- human approval
- explicit rollback proof
- production gate outside BrotherMode

BrotherMode should apply **the minimum sufficient control**, not maximum bureaucracy.

---

## 10. Adversarial Verification

Review should not ask only:

> Does this look correct?

BrotherMode should ask:

> **What would make this delivery false?**

For every important acceptance criterion, produce at least one falsification attempt.

Example:

```text
Claim:
Existing subscriptions remain unaffected.

Falsification:
Load an existing subscription fixture created before the migration,
run the new billing path, and compare charge schedule and invoice state.
```

Verification becomes:

```text
claim → evidence → falsification → verdict
```

This should become one of BrotherMode's defining behaviors.

---

## 11. Delivery as a State Transition

`deliver` is not a report command.

It is a control-plane state transition.

Before a delivery can become VERIFIED:

- the delivery contract exists
- required acceptance criteria exist
- all required evidence is present
- relevant evidence is fresh
- conflicting ownership is resolved
- required reviews are complete
- required human gates are satisfied
- degraded safety is disclosed
- known omissions are classified
- the delivery manifest can be generated

Possible delivery states:

```text
NOT_READY
READY_FOR_REVIEW
VERIFICATION_FAILED
VERIFIED
DELIVERED_WITH_WAIVER
DELIVERED
CONFIRMED
REOPENED
```

A waiver must never silently become VERIFIED.

---

## 12. Delivery Manifest

Every delivery should produce a human-readable and machine-readable manifest.

Suggested machine form:

```yaml
brothermode_delivery:
  version:
  delivery_id:
  contract_version:
  repository:
  commit:
  outcome:
  criteria:
  evidence:
  waivers:
  unresolved_risks:
  capabilities_used:
  safety_coverage:
  delivered_at:
  accepted_by:
  manifest_hash:
```

The manifest should bind together:

- contract
- acceptance criteria
- revision
- evidence
- waivers
- capability provenance
- unresolved risk
- delivery state

This becomes the portable proof of what BrotherMode means by delivered.

---

## 13. Tamper-Evident Receipts

Important state transitions should be hashable and traceable.

Examples:

- contract created
- contract amended
- resource claimed
- claim transferred
- verification recorded
- evidence invalidated
- waiver approved
- delivery committed
- delivery reopened

BrotherMode does not need blockchain.

A local append-only receipt chain with hashes is sufficient.

The goal is simple:

> A delivery record should be difficult to rewrite accidentally without detection.

---

## 14. Transactional Handover

A handover is ownership transfer.

It should behave atomically.

### Prepare

The current session records:

- current intent
- current contract version
- work completed
- open work
- active claims
- evidence state
- blockers
- next recommended action

### Verify

BrotherMode checks that the handover is complete enough to adopt.

### Adopt

The successor explicitly adopts the baton.

### Transfer

Ownership moves.

No state where:

- predecessor believes it transferred
- successor did not receive it
- claims are ambiguous
- evidence disappears

The handover is either transferred or not transferred.

---

## 15. Safety Coverage

Do not claim operating-system containment unless BrotherMode actually provides it.

Instead publish a safety coverage state.

Example:

```text
Write Control
  ENFORCED: 91%
  DETECTED: 6%
  UNOBSERVED: 3%
```

If an unobserved or detected write affects a resource tied to current evidence:

1. mark the affected evidence stale
2. disclose the degraded coverage
3. require re-verification before verified delivery

Honesty becomes part of the moat.

---

## 16. Toolkit as a Controlled Supply Chain

Toolkit is not the product moat.

Toolkit is the capability supply chain feeding the delivery system.

BrotherMode may use:

- Superpowers
- BMAD
- Spec Kit
- OpenSpec
- MCP servers
- CLIs
- specialist skills
- other coding agents
- testing frameworks
- security scanners

For every external capability, record:

```yaml
name:
publisher:
version:
source:
permissions:
network_access:
read_scope:
write_scope:
selected_for:
result_claimed:
result_verified:
retention_decision:
```

External capabilities can improve execution.

They must never weaken the delivery contract.

---

## 17. Learning Moat

BrotherMode should learn from **delivery outcomes**, not merely prompt history.

Track:

- which verification methods prevented reopenings
- which risks produced failures
- which estimates were inaccurate
- which capabilities worked
- which capabilities created rework
- where users issued waivers
- which acceptance criteria were frequently under-specified
- which resources repeatedly caused conflicts
- which deliveries reopened within seven days

Over time BrotherMode should be able to say:

> For work like this in this repository, these verification methods historically matter.

That is a compounding moat.

---

## 18. User Experience

The internal system can be deep.

The visible experience must remain simple.

### `start`

BrotherMode should inspect before interrogating.

It should automatically understand as much as possible from:

- repository structure
- Git state
- tests
- CI
- existing instructions
- active BrotherMode state
- installed capabilities
- relevant historical decisions

Then ask only questions whose answers materially change the contract.

The ideal confirmation screen:

```text
Outcome
What we are building.

Scope
What will change.

Non-goals
What will not change.

Acceptance
How success will be proven.

Risks
What could go wrong.

Human gates
Where execution must stop for approval.
```

Then:

```text
Confirm contract? [yes / amend]
```

---

## 19. `status`

`status` should answer five questions:

1. What are we trying to achieve?
2. Where are we now?
3. What is blocked or unsafe?
4. What remains unproven?
5. What should happen next?

Everything else is drill-down.

---

## 20. `review`

`review` should produce:

```text
CRITERION
CLAIM
CURRENT EVIDENCE
FALSIFICATION ATTEMPT
VERDICT
NEXT ACTION
```

Bad news first.

No confidence theater.

---

## 21. `deliver`

`deliver` should answer:

```text
OUTCOME
DELIVERY STATE
CONTRACT VERSION
WHAT CHANGED
WHAT WAS PROVEN
WHAT IS UNPROVEN
WHAT WAS WAIVED
WHAT REMAINS
SAFETY COVERAGE
DELIVERY MANIFEST HASH
```

If the contract is not satisfied:

```text
DELIVERY REFUSED
```

with exact reasons.

---

## 22. Control-Plane Semantics

Diagnostic commands should remain available even when state is damaged.

Examples:

- status
- doctor
- recover
- inspect

But enforcement commands must return machine-readable refusal when a state transition fails.

Examples:

- claim
- transfer
- verify
- handover-close
- deliver

CI and external automation must be able to distinguish:

```text
verified
```

from:

```text
verification refused
```

---

## 23. Repository Host Independence

BrotherMode should treat the Git hosting platform as an adapter.

Core integrity semantics must remain identical on:

- GitHub
- Bitbucket
- Azure Repos / Azure Git
- local Git
- future supported Git hosts

The host can provide:

- pull requests
- CI pipelines
- branch protections
- repository metadata
- issue integration

But the BrotherMode delivery contract and evidence model must not depend on one vendor.

---

## 24. GitHub Integration

BrotherMode should eventually expose the same delivery manifest to GitHub CI and pull requests.

Recommended integration model:

```text
BrotherMode local/session work
        ↓
Delivery Manifest
        ↓
GitHub Actions validation
        ↓
PR status: BrotherMode Verified / Refused
```

The GitHub adapter must validate the manifest.

It should not independently redefine BrotherMode's integrity rules.

---

## 25. Bitbucket Integration

The Bitbucket adapter should follow the same architecture:

```text
BrotherMode local/session work
        ↓
Delivery Manifest
        ↓
Bitbucket Pipelines validation
        ↓
PR / branch delivery status
```

No Bitbucket-specific semantics should leak into the core delivery model.

---

## 26. Azure Repos / Azure Git Integration

The Azure adapter should follow the same architecture:

```text
BrotherMode local/session work
        ↓
Delivery Manifest
        ↓
Azure Pipelines validation
        ↓
Pull request / policy status
```

Azure-specific pipeline and repository APIs belong in adapters.

The BrotherMode contract, evidence, ownership, and delivery state machine remain platform independent.

---

## 27. Public Standard

Long term, define an open:

# Verified Delivery Protocol

The protocol should specify:

- delivery contracts
- acceptance criteria
- work identity
- resource claims
- evidence receipts
- evidence freshness
- safety coverage
- waivers
- handovers
- delivery manifests
- confirmation and reopen semantics

Other tools should be able to produce BrotherMode-compatible receipts.

BrotherMode should become the reference implementation and validator.

The strongest category position is not:

> We have the best workflow.

It is:

> We define what verified AI delivery means.

---

## 28. DeliveryBench

Create a public adversarial benchmark for long-running AI delivery.

Scenarios should include:

### Session loss

Kill the agent mid-task.

Can the next session continue correctly?

### Conflicting workers

Two workers attempt overlapping changes.

Does the system detect or prevent the conflict?

### Stale evidence

Run tests successfully.

Change relevant code.

Does the system still claim verified?

### Irrelevant evidence

Provide a passing test that does not actually prove the acceptance criterion.

Does the system detect the mismatch?

### Incomplete handover

Transfer work without critical context.

Can the successor mistakenly proceed?

### Shell bypass

Modify a governed resource through a path outside the preferred editing tool.

Does the system disclose the safety gap and invalidate proof?

### Scope mutation

Change the requested outcome midway.

Does the system preserve contract history?

### Self-review failure

Have the implementing agent review its own work.

Does high-risk policy require independent review?

### Store failure

Damage project state.

Can BrotherMode recover without silently inventing state?

The benchmark should measure:

- silent false-completion rate
- state-loss rate
- conflict rate
- reopen rate
- recovery success
- unnecessary refusal rate
- added time
- added token cost
- human interventions

---

## 29. North Star

The product should optimize for:

# Confirmed External Verified Deliveries per Week

A delivery should count only when:

- a real external user uses BrotherMode
- on real work
- with a real contract
- across a meaningful session or execution boundary
- with current criterion-linked evidence
- with a real delivery manifest
- accepted by the user
- not materially reopened within the confirmation window

Tests, commits, tool calls, stars, agents, and tokens are not the north star.

---

## 30. What BrotherMode Should Not Become

Do not become:

- another coding agent
- another IDE
- another swarm framework
- another model router
- another generic project-management tool
- another prompt library
- another agent marketplace
- another cloud runtime
- another enterprise approval platform

Those systems can integrate with BrotherMode.

BrotherMode should own:

- intent integrity
- work identity
- ownership integrity
- state durability
- evidence integrity
- handover integrity
- delivery integrity

Everything else should be an adapter or external capability.

---

## 31. Build Priority

### P0 — Complete the delivery kernel

1. Delivery Contract
2. stable acceptance-criterion IDs
3. criterion-linked evidence
4. evidence freshness and invalidation
5. delivery state machine
6. delivery manifest
7. explicit waiver semantics

### P1 — Complete control and continuity

8. transactional handover
9. resource-claim lifecycle
10. safety-coverage reporting
11. risk-adaptive verification
12. independent / adversarial review
13. shared BrotherMode / BrotherSBE `change_id`
14. Change Envelope and receiver acknowledgment

### P2 — Make the integrity portable

15. CI validator
16. GitHub adapter
17. Bitbucket adapter
18. Azure Repos adapter
19. tamper-evident receipts
20. BrotherSBE import/export compatibility contract
21. cross-person handover and local adoption bridge

### P3 — Build the compounding moat

22. outcome-based learning
23. verification effectiveness history
24. repository-specific risk patterns
25. capability performance history
26. estimate calibration
27. reopen and handoff outcomes shared with BrotherSBE
28. team-level change integrity graph

### P4 — Define the category

29. Verified Delivery Protocol
30. DeliveryBench
31. external behavioral studies
32. independent security and reliability review
33. BrotherMode + BrotherSBE startup operating benchmark

---


## 32. BrotherMode + BrotherSBE: One Integrity System Across One Person and a Team

BrotherMode and BrotherSBE should be designed as two compatible control planes over the same delivery lifecycle.

The boundary must remain simple:

> **BrotherMode governs one person's execution. BrotherSBE governs one change's passage between people.**

This is already the correct operating boundary documented in `docs/WORKING-WITH-BROTHERSBE.md`.

The strategic goal is not to merge the products.

The goal is to make the handoff between them so precise that a user experiences one continuous integrity system.

```text
Human Intent
    ↓
BrotherMode
Individual execution integrity
    ↓
Verified Work Package
    ↓
BrotherSBE
Cross-person change integrity
    ↓
Review / Routing / Team Handoff
    ↓
Repository Host
GitHub / Bitbucket / Azure Repos
    ↓
Merge / Release / Deployment
```

BrotherMode remains excellent for one accountable operator.

BrotherSBE becomes the coordination layer when responsibility crosses a human boundary.

---

## 33. The Shared Seam: One Change Identity

Deep compatibility starts with one shared identifier.

BrotherMode and BrotherSBE should never create unrelated identities for the same change.

Every substantial change should receive a stable:

```yaml
change_id:
```

Example:

```yaml
change_id: CHG-2026-0042
```

That ID follows the work through:

```text
Delivery Contract
Work records
Resource claims
Evidence receipts
Handover
BrotherSBE impact analysis
Review routing
Pull request
Delivery Manifest
Acceptance
Reopen
```

The result is one trace:

```text
Intent
  ↓
CHG-2026-0042
  ↓
Execution
  ↓
Evidence
  ↓
Team Review
  ↓
Delivery
```

No translation table.

No duplicate project identifiers.

No manual reconciliation.

### Compatibility rule

BrotherMode owns the detailed execution state.

BrotherSBE owns the cross-person routing and change state.

Both reference the same `change_id`.

Neither silently copies the other's source of truth.

---

## 34. The Change Envelope

When BrotherMode hands work to BrotherSBE, it should produce one portable **Change Envelope**.

This should be generated from BrotherMode records, not rewritten by the user.

Suggested structure:

```yaml
change_envelope:
  schema_version:
  change_id:
  project_id:
  repository:
  base_revision:
  head_revision:

  outcome:
  contract_version:
  scope:
  non_goals:

  risk:
    brothermode_risk:
    known_risks:
    safety_coverage:

  ownership:
    resources_touched:
    active_claims:
    released_claims:

  acceptance:
    criteria_total:
    proven:
    stale:
    unproven:
    waived:

  evidence:
    delivery_manifest:
    receipts:
    independent_reviews:

  handoff:
    sender:
    intended_receiver:
    status:
    next_action:

  provenance:
    capabilities_used:
    runtime:
    brothermode_version:

  integrity:
    envelope_hash:
```

BrotherSBE consumes this envelope.

It should not ask the engineer to type the same outcome, risk, evidence, or changed-resource information again when BrotherMode already has it.

### Principle

> **Enter truth once. Reuse it everywhere.**

That is essential for a 12 to 15 person startup.

If team governance creates duplicate administration, people will route around it.

---

## 35. Individual Contributor Workflow

For an individual contributor, BrotherMode remains the primary experience.

BrotherSBE should appear only when the work crosses a meaningful external boundary.

### Normal solo flow

```text
1. Intent
2. BrotherMode Delivery Contract
3. Risk classification
4. Work plan
5. Resource claims
6. Implementation
7. Criterion-linked evidence
8. Adversarial verification where required
9. BrotherMode Delivery Manifest
10. Delivery
```

For work that remains entirely personal and low-risk, BrotherSBE may never be needed.

That is a feature.

### BrotherSBE activates when one of these happens

- another person must review the change
- another person becomes responsible for the next step
- another function consumes the changed contract
- the change affects another team's owned surface
- the risk tier requires specialist review
- the work is being handed off
- the change enters a shared release or approval path

Then the flow becomes:

```text
BrotherMode
   ↓
Change Envelope
   ↓
BrotherSBE impact / routing
   ↓
Reviewer or receiver
```

### Individual contributor experience

The user should not feel that they are "switching project-management systems."

They should feel:

> My private execution record has become a team-ready change package.

That is the correct transition.

---

## 36. Startup Workflow: 12 to 15 People

BrotherMode + BrotherSBE should be especially strong for a small startup because this is the stage where teams need control but cannot afford enterprise process overhead.

The target team may include:

```text
Founder / CTO
Product lead
Design
Backend engineers
Frontend engineers
Mobile engineers
Data / AI engineers
Platform / DevOps
QA or rotating reviewers
```

Not every person needs the same tool surface.

### Operating model

Each technical individual contributor runs their own BrotherMode-controlled work.

BrotherSBE coordinates the changes when they cross people.

```text
Engineer A
BrotherMode Session
      \
       \
Engineer B ---- BrotherMode Session
         \       |
          \      |
           BrotherSBE
          Change Layer
          /     |     \
         /      |      \
Reviewer     Tech Lead   Engineer C
                         BrotherMode
```

There is no requirement for several people to share one BrotherMode session.

There is no requirement for a central BrotherMode account.

There is no requirement for BrotherMode to become Jira.

### Team rule

> **One accountable operator per BrotherMode execution context. One shared BrotherSBE change identity when responsibility crosses people.**

This preserves BrotherMode's single-writer discipline while enabling a real startup team to operate across many concurrent changes.

---

## 37. Startup Change Flow

A normal startup feature might look like this:

```text
Product intent
    ↓
Technical owner creates / confirms change identity
    ↓
BrotherMode Delivery Contract
    ↓
Work decomposes into individually accountable execution units
    ↓
Each IC runs BrotherMode for their unit
    ↓
Each unit produces current evidence
    ↓
BrotherMode exports Change Envelope
    ↓
BrotherSBE evaluates impact and routing
    ↓
Required reviewers receive the exact evidence state
    ↓
Review / acknowledgment
    ↓
Repository PR
    ↓
CI
    ↓
BrotherMode / BrotherSBE integrity checks
    ↓
Merge
    ↓
Release
```

### Example

Feature:

```text
Add recurring billing.
```

The work may cross:

```text
Backend
Frontend
Data
Finance reporting
Deployment
```

BrotherMode controls each person's execution.

BrotherSBE controls how the overall change crosses those ownership boundaries.

Backend does not need to understand the frontend session history.

Frontend does not need to reconstruct backend reasoning from chat.

The receiving person gets:

- what changed
- why
- what contract is affected
- which evidence exists
- what is stale
- what is unmeasured
- what they now own
- what they are expected to review

That is the startup-scale value proposition.

---

## 38. No Duplicate Governance

The biggest design risk is creating two systems that both attempt to manage:

- planning
- risk
- evidence
- status
- ownership
- approval

That would destroy the experience.

The responsibility boundary must remain explicit.

| Concern | BrotherMode | BrotherSBE |
|---|---|---|
| Human intent | Owns execution contract | References relevant contract |
| Individual plan | Owns | Does not reproduce |
| Session state | Owns | Does not own |
| File/resource claims inside one execution context | Owns | Reads summary when relevant |
| Current criterion evidence | Owns | Consumes receipts |
| Evidence freshness | Owns | Treats BrotherMode verdict as input |
| Cross-person impact | Supplies touched resources | Owns routing/impact interpretation |
| Reviewer requirement | Can request independent review | Owns cross-person routing policy |
| Handover package | Produces | Routes and records passage |
| Receiver acknowledgment | Records local adoption when applicable | Owns cross-person acknowledgment |
| Team change state | Does not become team PM | Owns change passage |
| Merge/deploy | Does not perform by default | Does not perform by default |
| Git host | Adapter | Adapter |

### Rule

If BrotherSBE can derive a fact from a signed or hashed BrotherMode artifact, it should derive it.

If BrotherMode does not need a team fact to safely execute the local work, it should not duplicate it.

---

## 39. The BrotherMode → BrotherSBE Compatibility Contract

The two products should eventually publish a versioned compatibility contract.

Example:

```yaml
brothers_protocol:
  version: 1

  identifiers:
    change_id: required
    project_id: optional
    work_id: required_for_substantial_work

  brothermode_exports:
    delivery_contract: required
    change_envelope: required
    delivery_manifest: when_available
    evidence_receipts: required
    safety_coverage: required

  brothersbe_returns:
    impact_verdict:
    measured_gaps:
    proposed_risk_floor:
    review_route:
    receiver_acknowledgment:
    team_gate_state:

  shared_rules:
    no_data_is_not_pass: true
    waiver_is_not_verification: true
    sender_owns_until_receiver_accepts: true
    evidence_must_remain_traceable: true
```

This protocol should be repository-host independent.

GitHub, Bitbucket, and Azure Repos are transports.

The semantics remain the same.

---

## 40. NO-DATA Must Mean the Same Thing Everywhere

One of the strongest existing BrotherSBE behaviors is that an unmeasured surface can produce `NO-DATA` rather than pretending it passed.

BrotherMode should use the same philosophy.

Across both products:

```text
PASS
FAIL
NO-DATA
STALE
WAIVED
UNSUPPORTED
```

must have stable meanings.

### Shared trust rule

```text
NO-DATA != PASS
WAIVED != VERIFIED
UNSUPPORTED != CLEAN
STALE != CURRENT
```

A startup should be able to learn these semantics once.

The same words should mean the same thing in:

- BrotherMode status
- BrotherMode review
- BrotherMode Delivery Manifest
- BrotherSBE impact
- BrotherSBE routing
- pull request checks
- CI
- delivery pages

This consistency is a moat.

---

## 41. Cross-Person Handover

Current BrotherMode guidance already contains the right ownership principle:

> Until the receiver confirms they have taken the handover, the sender still owns it.

Deep BrotherSBE integration should make that mechanical.

Target lifecycle:

```text
PREPARED
    ↓
OFFERED
    ↓
RECEIVED
    ↓
ACCEPTED
    ↓
TRANSFERRED
```

Or:

```text
PREPARED
    ↓
REJECTED
```

No ambiguous middle state.

### Transfer rule

Ownership cannot disappear between people.

If the receiver never accepts:

```text
sender remains accountable
```

If the receiver accepts:

```text
the change record names the new accountable owner
```

BrotherMode can then adopt the corresponding execution unit locally for that receiver.

This creates a clean bridge:

```text
BrotherSBE team transfer
        ↓
BrotherMode local adoption
```

---

## 42. Review Without Reconstructing the Project

For a startup, reviewer attention is scarce.

The BrotherMode + BrotherSBE combination should optimize for reviewer minutes.

A reviewer should receive one compact review packet:

```text
CHANGE
Why this exists

IMPACT
What other owned surfaces may be affected

RISK
What can go wrong

CONTRACT
What must remain true

DIFF
What changed

EVIDENCE
What has actually been proven

GAPS
What is stale / NO-DATA / unsupported

FALSIFICATION
What was tried to disprove the claims

ROUTE
Why this reviewer was selected

DECISION
Approve / request change / redirect / accept handoff
```

The reviewer should not need:

- the original Claude conversation
- the implementer's memory
- a manually written status summary
- five dashboards
- a meeting to discover what changed

This is where the two-product system can become dramatically better than ordinary startup workflow.

---

## 43. Multi-Change Startup Coordination

BrotherSBE should coordinate changes.

BrotherMode should coordinate execution units.

This permits a startup to run many changes concurrently without introducing shared mutable BrotherMode state.

Example:

```text
CHG-101 Checkout
  BM work A - backend
  BM work B - frontend

CHG-102 Recommendation model
  BM work C - data
  BM work D - API

CHG-103 Pricing page
  BM work E - frontend
```

BrotherSBE sees:

```text
CHG-101
CHG-102
CHG-103
```

Each person sees only the BrotherMode execution context they are accountable for.

The team lead sees change passage, risk, dependencies, evidence gaps, and reviewer load.

This creates scale without turning BrotherMode into a multi-user project-management platform.

---

## 44. Team-Level Integrity Graph

Long term, the shared change identity allows a lightweight team integrity graph:

```text
Intent
  ↓
Change
  ├── Work Unit A
  │     ├── Resources
  │     └── Evidence
  │
  ├── Work Unit B
  │     ├── Resources
  │     └── Evidence
  │
  ├── Impact
  ├── Reviewers
  ├── Handovers
  └── Delivery
```

BrotherMode owns the work-unit depth.

BrotherSBE owns the change-level edges.

This graph can answer:

- Which active changes touch billing?
- Which change has stale evidence?
- Which work unit is still owned by a dead session?
- Which change is waiting for another person?
- Which reviewer is required?
- Which cross-team dependency is unmeasured?
- Which delivered change reopened?
- Which acceptance criterion has no current proof?

That is enough coordination for a 12 to 15 person startup without recreating enterprise project management.

---

## 45. GitHub, Bitbucket, and Azure Repos Team Integration

The BrotherMode + BrotherSBE model must behave identically across Git hosts.

### GitHub

```text
BrotherMode Work
    ↓
Change Envelope
    ↓
BrotherSBE
    ↓
Pull Request
    ↓
GitHub Actions
    ↓
Integrity Status
```

### Bitbucket

```text
BrotherMode Work
    ↓
Change Envelope
    ↓
BrotherSBE
    ↓
Pull Request
    ↓
Bitbucket Pipelines
    ↓
Integrity Status
```

### Azure Repos

```text
BrotherMode Work
    ↓
Change Envelope
    ↓
BrotherSBE
    ↓
Pull Request
    ↓
Azure Pipelines / Policies
    ↓
Integrity Status
```

The Git host should never become the source of truth for BrotherMode's delivery semantics.

The host displays and enforces the result.

BrotherMode and BrotherSBE define what the result means.

---

## 46. Compatibility Features to Build

Deep compatibility should be delivered as a small number of strong primitives.

### P0

1. Shared `change_id`
2. Change Envelope schema
3. BrotherMode export of criterion-linked evidence
4. BrotherSBE import without duplicate intake
5. Stable shared verdict vocabulary
6. Receiver acknowledgment linked to `change_id`

### P1

7. BrotherSBE routing receipts linked into BrotherMode Delivery Manifest
8. Cross-person handover state machine
9. BrotherMode local `adopt` flow from an accepted BrotherSBE handoff
10. Risk-tier reconciliation rules
11. Cross-product schema/version compatibility check
12. Git-host-neutral PR metadata adapter

### P2

13. Team integrity view built from change envelopes, not a new central database
14. Reviewer workload and pending-handoff view
15. Cross-change resource collision warnings
16. Change dependency graph
17. Reopen feedback flowing back into BrotherMode learning
18. CI validation of BrotherMode + BrotherSBE integrity chain

### P3

19. Organization policy packs
20. Repository-specific routing history
21. Risk calibration from real reopen data
22. Team-level DeliveryBench scenarios

---

## 47. Startup Modes

The products should expose two conceptual operating modes without becoming two separate codebases.

### Solo Mode

```text
BrotherMode = primary
BrotherSBE = optional boundary tool
```

Optimized for:

- individual contributor
- solo founder
- maintainer
- consultant
- fractional CTO

### Startup Mode

```text
BrotherMode = execution plane per person
BrotherSBE = change coordination plane
```

Optimized for:

- 2 to 15 technical contributors
- founder-led engineering teams
- small product companies
- small agencies
- AI-native startups

This is a strong upper boundary for the initial team product.

Do not immediately expand toward hundreds of users, enterprise permissions, organizational charts, or centralized workflow administration.

Win the 12 to 15 person startup first.

---

## 48. What Startup Mode Should Feel Like

The product should remove meetings and reconstruction work, not add administration.

A founder or tech lead should be able to ask:

```text
What is actually ready?
```

and see:

```text
3 changes VERIFIED
1 waiting for reviewer
1 has STALE evidence
1 is NO-DATA on downstream impact
1 handoff has not been accepted
```

An engineer should be able to ask:

```text
What do I own?
```

and see only the relevant work.

A reviewer should be able to ask:

```text
Why am I reviewing this?
```

and receive the exact route, impact, contract, evidence, and known gaps.

A new receiver should be able to ask:

```text
What am I taking over?
```

and get enough durable state to continue without a meeting.

That is the target experience.

---

## 49. The Combined Moat

BrotherMode alone creates:

**execution integrity**

BrotherSBE creates:

**change-passage integrity**

Together they create:

# Delivery Integrity Across People

That combination is substantially more defensible than either:

- an agent workflow
- a project-management system
- a spec framework
- a swarm framework
- a code-review tool

The combined system can preserve integrity across:

```text
human intent
    ↓
one agent session
    ↓
multiple sessions
    ↓
one individual contributor
    ↓
another individual contributor
    ↓
review
    ↓
repository host
    ↓
delivery
```

The strategic principle becomes:

> **BrotherMode makes one person's AI work trustworthy. BrotherSBE keeps that trust intact when the work crosses people.**

For a solo operator, BrotherMode stands on its own.

For a 12 to 15 person startup, BrotherMode plus BrotherSBE becomes a lightweight operating system for verified delivery without requiring a heavyweight central management platform.


## 50. Final Product Principle

Every future feature should answer one question:

> **Does this make the path from human intent to verified AI delivery more trustworthy, more resumable, more controllable, or easier to understand?**

If not, it does not belong in BrotherMode core.

The final strategic rule is:

> **Stop thinking of BrotherMode as a better workflow around Claude Code. Build it as the integrity system between human intent and AI delivery.**

Claude Code is one worker.

GitHub, Bitbucket, and Azure Repos are repository hosts.

CI systems are check runners.

External skills and agents are capabilities.

**BrotherMode owns the delivery contract.**

**BrotherSBE owns the integrity of that change as responsibility passes between people.**

Together they preserve one chain of trust from individual execution to team delivery.

And when BrotherMode says:

> **Verified Delivery**

that statement must have a precise, inspectable, machine-checkable meaning.
