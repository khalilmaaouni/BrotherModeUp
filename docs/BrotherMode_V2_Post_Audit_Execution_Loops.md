Status: HISTORICAL record. Kept as written for the period it describes; it is not a description of the current tree.

# BrotherMode V2 Post-Audit Execution Loops

## Purpose

This document is the execution plan for closing the gaps found in the 2026-07-29 post-change review of BrotherMode V2.

It is written for Claude Code Opus acting as the chief implementer, with Fable as the lead adversarial reviewer and additional sub-agents used for bounded specialist work.

The goal is not to add more features for their own sake. The goal is to make the current promises mechanically true, easy to install, hard to misuse, and supported by real evidence.

---

## Current starting point

The V2 branch already contains substantial work:

- SQLite schema version 2.
- Founder correction candidates.
- Manual rule approval.
- Immutable rule versions.
- English, French, and Japanese correction detection.
- Scoped lexical retrieval.
- Duplicate, contradiction, and supersession relationships.
- Rule application records.
- Rework and escaped-defect attribution.
- Loop-failure reporting.
- Autosave and recovery.
- File claims and a PreToolUse fence hook.
- Cross-platform CI for much of the store and recovery code.

The remaining work is mostly about closing the gap between strong architecture and a dependable public product.

The most important current gaps are:

1. The public default branch and clone command still install the older product.
2. Founder-only approval is workflow-enforced, not mechanically authenticated.
3. A gate rule can be excluded by a low retrieval result limit.
4. Application recording is optional and easy for the model to forget.
5. Retrieval context is incomplete, which undercounts retrieval misses.
6. Retrieval is lexical only.
7. The fence promise does not cover Bash writes and the fence hook is not installed in the main quick start.
8. The complete local test gate is not identical to the CI gate.
9. User-facing documentation contains stale generated facts.
10. Some ordinary prose and path data remain exportable through the general dump path.
11. Windows privacy relies on CI and POSIX-style behavior that Windows does not provide.
12. Handovers remain serialized append operations rather than transactional store records.
13. The system has not been dogfooded through a real working period.
14. A different model family has not completed an independent adversarial re-audit.

---

# 1. Operating model

## 1.1 Chief implementer

The chief implementer owns:

- The sequence of loops.
- Final file ownership decisions.
- Integration across loops.
- Test execution after the last edit.
- Release and rollback decisions.
- The final statement of what is proven and what remains unproven.

The chief does not delegate final truth. Sub-agent conclusions are inputs, not evidence by themselves.

## 1.2 Fable

Treat Fable as the lead adversarial reviewer.

Default Fable permissions:

- Read-only repository access.
- May create review notes only in a file explicitly assigned to it.
- May not modify production code unless a loop explicitly promotes Fable to writer.
- Must reproduce a claimed defect before recommending a fix.
- Must attempt to refute the done claim after implementation.
- Must report false positives and disproven concerns, not only findings.

Fable should be used at three points in every high-risk loop:

1. Before implementation: attack the current behavior.
2. After implementation: re-run the original attack.
3. At loop close: search for adjacent variants of the same defect class.

## 1.3 Specialist sub-agents

Use the following specialist roles. One physical agent may play more than one role, but never give two simultaneous writers the same file.

### Store Agent

Owns transactional schema, migrations, lifecycle state, constraints, and data integrity.

Typical files:

- `tools/bm_store.py`
- `tools/test_bm_store.py`

### Learning Agent

Owns correction detection, rule ranking, retrieval semantics, application grading, and founder-facing learning CLI behavior.

Typical files:

- `tools/bm_learning.py`
- `tools/bm_learn.py`
- Learning sections in `tools/test_bm_store.py`

### Security Agent

Owns redaction, data withholding, permissions, symlink and hardlink containment, Windows ACL behavior, and export safety.

Typical files:

- `SECURITY.md`
- `tools/bm_store.py`
- `tools/bm_telemetry.py`
- `mcp/bm_mcp_server.py`
- Security-related tests

### Hook and Fence Agent

Owns hook installation, hook contracts, supported edit tools, fence enforcement, and fail-open/fail-closed behavior.

Typical files:

- `tools/bm_fence_hook.py`
- `tools/test_bm_fence_hook.py`
- `docs/HOOKS.md`
- Installer and setup files

### CI and Release Agent

Owns branch visibility, release tags, immutable install artifacts, checksums, GitHub Actions, clean-install verification, and rollback instructions.

Typical files:

- `.github/workflows/tests.yml`
- `VERSION`
- `CHANGELOG.md`
- `docs/RELEASE.md`
- `scripts/checksums.sh`
- `scripts/verify-install.sh`

### Documentation Agent

Owns README, quick start, setup, product claims, and generated fact consistency.

Typical files:

- `README.md`
- `docs/QUICKSTART.md`
- `docs/SETUP.md`
- `docs/CORRECTION-LEARNING.md`
- `docs/KNOWN-LIMITS.md`
- `docs/NOT-FINALIZED.md`

### Dogfood Observer

Owns measurement design and daily evidence collection. It must not rewrite results to look better.

Typical files:

- `docs/dogfood/`
- `tools/WEEKLY-REVIEW.md`
- New reporting scripts only when justified by real use

---

# 2. Non-negotiable engineering rules

These rules apply to every loop.

## 2.1 One writer per file

Before dispatching any sub-agent:

1. List every file it may modify.
2. Register the claim before dispatch.
3. Refuse overlapping write sets.
4. Give Fable read-only access by default.
5. Re-check the working tree before integration.

## 2.2 Reproduce before fixing

A loop may not begin implementation until the defect or gap is demonstrated in one of these forms:

- A failing automated test.
- A hand-run CLI reproduction.
- A branch or install behavior observed directly.
- A static proof where execution is not possible.

If a documented defect cannot be reproduced, update the defect register before changing code.

## 2.3 Calibrate every load-bearing test

For every new guard:

1. Run the test with the fix and prove it passes.
2. Reinject the previous defect or disable the guard.
3. Prove the test fails for the intended reason.
4. Restore the fix.
5. Prove the test passes again.

A test that was never proven capable of failing is not release evidence.

## 2.4 No model-only evidence

The following are not sufficient proof:

- A sub-agent saying the feature works.
- A code review without execution where execution is possible.
- A README claim.
- A self-score.
- An LLM classification of correctness without external evidence.

## 2.5 Keep the core small

Do not introduce Node, Docker, PostgreSQL, a network service, an API key, or an embedding provider as a mandatory dependency.

Optional capabilities must:

- Fail back to the standard-library path.
- Be disabled by default.
- Never weaken core safety.
- Have an explicit removal path.

## 2.6 Do not hide honest limitations

Every loop must update:

- `docs/KNOWN-LIMITS.md`
- `docs/NOT-FINALIZED.md`
- `CHANGELOG.md`

when the factual status changes.

Do not close an item because code exists. Close it only when its acceptance evidence exists.

---

# 3. Standard loop protocol

Every implementation loop follows this sequence.

## Phase A: Ground truth

- Read the relevant code and tests.
- Read the current limits entry.
- Run the full gate once before edits.
- Record the branch, commit, test count, and status.
- Reproduce the problem.

## Phase B: Design

- State the invariant to make true.
- State what is deliberately out of scope.
- List schema changes, API changes, CLI changes, and migration effects.
- Identify rollback strategy.
- Assign file fences.

## Phase C: Implementation

- Implement the smallest structural fix.
- Avoid copying logic into multiple places.
- Route every store mutation through `bm_store.py`.
- Keep pure semantics in `bm_learning.py`.
- Keep CLI parsing and presentation in `bm_learn.py`.

## Phase D: Verification

- Run focused tests.
- Run the real CLI against a throwaway store.
- Run the full local gate.
- Run relevant platform checks.
- Record exact output.

## Phase E: Fable adversarial review

Ask Fable to:

- Re-run the original attack.
- Try adjacent variants.
- Inspect whether the new test can pass for the wrong reason.
- Inspect whether docs overstate the implementation.
- Inspect whether failure is fail-open or fail-closed in the correct direction.

## Phase F: Close or reopen

A loop closes only if:

- Acceptance criteria pass.
- Full gate passes after the final edit.
- Fable reports no unresolved blocker.
- Limits and changelog are accurate.
- Rollback is documented.

Otherwise mark the loop PARTIAL and name what remains.

---

# 4. Execution order

Run the loops in this order:

1. Loop 0: Freeze baseline and branch truth.
2. Loop 1: Make V2 the public product.
3. Loop 2: Repair installation and immutable release flow.
4. Loop 3: Make approval semantics mechanically honest.
5. Loop 4: Guarantee applicable gate rule delivery.
6. Loop 5: Create a mandatory recorded application path.
7. Loop 6: Persist complete retrieval-run context.
8. Loop 7: Add FTS5 with deterministic fallback.
9. Loop 8: Close fence installation and Bash-boundary claims.
10. Loop 9: Make local and CI gates equivalent.
11. Loop 10: Eliminate documentation and generated-fact drift.
12. Loop 11: Close privacy, export, and Windows protection gaps.
13. Loop 12: Move handovers into the transactional store.
14. Loop 13: Run real founder dogfooding.
15. Loop 14: Run independent adversarial audit.
16. Loop 15: Final release and public benchmark.

Loops 3 through 7 may share design discussions, but production code writes remain serial unless file ownership is completely disjoint.

---

# LOOP 0: Freeze the new baseline

## Goal

Create a trustworthy starting point before further changes.

## Why this loop exists

The repository currently contains dated files with different historical test counts and completion states. The branch and release state must be captured from execution, not inferred from the newest-looking document.

## Assigned agents

- Chief: writer for baseline document.
- Fable: read-only verifier.
- CI and Release Agent: read-only branch and tag inventory.

## File fence

Chief may write:

- `docs/POST-AUDIT-BASELINE-2026-07-29.md`
- `docs/NOT-FINALIZED.md`

No other files in this loop.

## Tasks

1. Confirm current branch and commit.
2. Confirm whether `main` and `v2` differ.
3. Confirm current default branch.
4. List tags and identify which commit each points to.
5. Run:

```bash
python3 tools/test_all.py
```

6. Run each CLI smoke path against a throwaway project:

```bash
python3 tools/bm_store.py init
python3 tools/bm_learn.py capture --trigger "writing a release note" --action "state unproven limits before claims" --because "the founder needs honest release evidence" --scope global
python3 tools/bm_learn.py candidates
python3 tools/bm_learn.py approve <candidate-id> --ref "baseline probe"
python3 tools/bm_learn.py relevant --query "write the release notes"
python3 tools/bm_learn.py verify
```

7. Run install verification from a clean temporary home directory.
8. Record all exact outputs and failures.
9. Ask Fable to identify any statement in README or Quickstart contradicted by the baseline.

## Acceptance criteria

- A single baseline file names branch, commit, version, tags, test counts, and known failures.
- Every number is tied to a command.
- Any contradiction with current docs is listed.
- No production code changes occur.

## Fable prompt

```text
You are the independent baseline auditor. Do not modify production files. Compare the current repository, branch state, tags, README, Quickstart, VERSION, CHANGELOG, and test outputs. Identify every factual contradiction. Reproduce before declaring a defect. Return BLOCKER, HIGH, MEDIUM, LOW, or REFUTED for each item.
```

---

# LOOP 1: Make V2 the public product

## Goal

Ensure a visitor opening the repository sees and installs the V2 product rather than the old main branch.

## Invariant

The default GitHub landing page, documented clone command, release tag, and installed bytes must all refer to the same product version.

## Assigned agents

- CI and Release Agent: writer.
- Documentation Agent: writer only after branch integration, on separate files.
- Fable: read-only.

## File fences

CI and Release Agent:

- Branch and release operations.
- `VERSION`
- `docs/RELEASE.md`
- `CHANGELOG.md`

Documentation Agent:

- `README.md`

No simultaneous edits to `CHANGELOG.md` and `README.md` by the same two agents without serial handoff.

## Tasks

1. Compare `main` and `v2` one final time.
2. Decide one of these paths:

Preferred:

- Merge `v2` into `main`.
- Keep `main` as the default branch.

Alternative:

- Change the default branch to `v2` temporarily.
- Still prepare a clean merge into `main` before stable release.

3. Remove all install instructions that clone an ambiguous moving default branch for stable users.
4. Create a release candidate version greater than `2.0.0-rc.2`.
5. Verify the tag points to the exact commit tested.
6. Verify the README displayed on the repository root is the V2 README.
7. Verify the clone command from a clean directory produces `tools/bm_learn.py` and schema version 2.
8. Verify `git describe`, `VERSION`, and release notes agree.

## Required tests

```bash
git clone --branch <new-tag> --depth 1 https://github.com/khalilmaaouni/BrotherModeUp.git /tmp/bm-release-test
cd /tmp/bm-release-test
cat VERSION
python3 tools/test_all.py
python3 tools/bm_learn.py --help
```

## Acceptance criteria

- Opening the root repository shows the V2 README.
- The primary install command installs V2.
- The release tag is immutable and documented.
- `VERSION`, tag, changelog, and installed code match.
- A clean clone passes the full test gate.

## Rollback

- Preserve the pre-merge main commit in a named backup branch.
- If the new release fails clean install, withdraw the release in documentation and restore the previous default branch.
- Never move an existing tag.

## Fable prompt

```text
Attack release identity. Try to find any path where two users naming the same version install different bytes, any documentation command that still gets the old branch, and any tag or VERSION disagreement. Do not accept a README statement as proof. Use clean clones and hashes.
```

---

# LOOP 2: Repair installation and immutable release flow

## Goal

Make installation one command or one guided command sequence, with automatic hook wiring, version verification, and safe uninstall.

## Invariant

A new user can install the exact released version, verify it, enable all intended hooks, and remove it without manually editing fragile JSON.

## Assigned agents

- CI and Release Agent: installer writer.
- Hook and Fence Agent: hook configuration writer.
- Documentation Agent: docs writer after installer contract freezes.
- Fable: adversarial installer tester.

## Proposed files

- `scripts/install.py`
- `scripts/uninstall.py`
- `scripts/verify-install.sh` or Python replacement
- `docs/QUICKSTART.md`
- `docs/SETUP.md`
- `docs/HOOKS.md`
- Installer tests under `tools/` or `scripts/tests/`

Prefer Python standard library for cross-platform behavior.

## Required installer behavior

1. Refuse an unclean overwrite of an existing BrotherMode installation unless `--upgrade` is explicit.
2. Record installed version and source tag.
3. Merge hook configuration without deleting unrelated user hooks.
4. Install these hooks when supported:

- SessionStart
- SessionEnd
- Stop
- PreCompact
- PreToolUse fence hook

5. Validate resulting JSON.
6. Run a smoke test.
7. Print exactly what was installed and what remains manual.
8. Support `--dry-run`.
9. Support uninstall that removes only BrotherMode-owned entries.
10. Never delete the user vault without a separate explicit command.

## Acceptance criteria

- Clean install works on Linux and macOS directly.
- Windows path is either working or explicitly refused with a precise message.
- Re-running install is idempotent.
- Existing unrelated settings remain byte-equivalent except for normalized JSON formatting if unavoidable.
- Uninstall removes only BrotherMode configuration and files.
- Clean install runs the full gate or a documented smoke subset plus checksum verification.

## Fable prompt

```text
Attack the installer as if the user already has custom hooks, malformed JSON, an older BrotherMode version, symlinked install directories, spaces and non-ASCII characters in paths, and a partially failed prior install. Look for destructive merges, ambiguous success messages, and installs that claim success without enabling the fence hook.
```

---

# LOOP 3: Make approval semantics mechanically honest

## Goal

Resolve the mismatch between the claim "founder-only approval" and the current implementation, where any process able to invoke the CLI can run `approve`.

## Decision required

Choose one of two honest models.

### Model A: Human approval receipt

Recommended if the product wants to claim mechanical founder-only approval.

A native user decision creates a one-time receipt. `approve` refuses without it.

### Model B: Manual approval gate

Recommended if implementation simplicity is preferred.

The product wording becomes:

- Automatic detection can only create candidates.
- Promotion requires an explicit invocation of the approval command.
- BrotherMode does not cryptographically prove which human or process invoked the command.

Do not claim human identity enforcement under Model B.

## Assigned agents

- Chief: chooses model.
- Learning Agent: writer.
- Security Agent: reviewer.
- Fable: attack reviewer.

## File fence

Learning Agent:

- `tools/bm_learn.py`
- Learning approval APIs in `tools/bm_store.py`
- Relevant tests

Documentation Agent later:

- `README.md`
- `docs/CORRECTION-LEARNING.md`
- `SECURITY.md`

## Model A design

Add an approval receipt with fields such as:

```text
receipt_uuid
candidate_uuid
issued_at
expires_at
nonce_hash
consumed_at
approval_choice
founder_response_hash
```

Rules:

- Receipt is short lived.
- Receipt applies to one candidate.
- Receipt can be consumed once.
- Candidate text or scope changes invalidate the receipt.
- The approval transaction consumes the receipt and creates the rule atomically.
- No receipt value is printed into ordinary logs.
- The native question UI or an explicit human-operated helper creates the receipt.

## Model B design

- Require `--ref`; remove the automatic generated founder reference.
- Rename documentation to "manual approval-gated".
- Add an explicit warning that shell access can invoke the command.
- Keep automatic capture unable to call approval through any hook.

## Required tests

For Model A:

- Approval without receipt refuses.
- Expired receipt refuses.
- Receipt for another candidate refuses.
- Reused receipt refuses.
- Candidate edit invalidates receipt.
- Approval and receipt consumption are atomic.
- Reinjected bypass is caught.

For Model B:

- Missing `--ref` refuses.
- Automatic detector code has no import or call path to approval.
- Docs never claim founder identity authentication.

## Acceptance criteria

- Code and wording describe the same guarantee.
- Fable cannot find an unacknowledged path from automatic capture to approved rule.
- Approval provenance remains immutable.

## Fable prompt

```text
Try to approve a rule without a real founder decision. Use direct CLI invocation, imported functions, forged references, replayed receipts, changed candidates, stale receipts, concurrent approval, and hook execution. Report the strongest guarantee the implementation actually supports, not the one the docs intend.
```

---

# LOOP 4: Guarantee applicable gate rule delivery

## Goal

Ensure a result limit can never hide an applicable gate rule.

## Invariant

Every applicable live gate rule is returned. The caller limit applies only to soft rules.

## Assigned agents

- Learning Agent: writer.
- Store Agent: reviewer.
- Fable: adversarial reviewer.

## File fence

- `tools/bm_learning.py`
- Retrieval section of `tools/bm_store.py`
- Relevant tests
- `docs/CORRECTION-LEARNING.md`
- `docs/KNOWN-LIMITS.md`

## Proposed retrieval contract

```text
applicable_gate_rules = all live gate rules whose scope matches
soft_candidates = relevant live soft rules whose scope matches
result = all applicable_gate_rules + top N soft_candidates
```

Decide whether `limit` means:

- Maximum soft rules only, recommended.
- Maximum total with a separate hard maximum for gates, not recommended unless gate volume is bounded and verified.

Add diagnostics:

```text
gates_returned
gates_total
soft_returned
soft_omitted
```

## Edge cases

- Multiple applicable global gates.
- A gate with zero lexical overlap.
- Conflicting gates.
- A deprecated gate.
- A superseded gate with a live successor.
- Limit zero.
- Negative limit.
- Very large gate corpus.

## Required tests

- Two rules, gate ranked second, `limit=1`: gate still returns.
- `limit=0`: all gates return, no soft rules.
- Conflicting gate counterpart is surfaced.
- Dead or non-injectable gates do not return.
- Reinstate old slicing behavior and prove the test fails.

## Acceptance criteria

- No supported limit can suppress an applicable gate.
- Output explains soft omissions separately from gate delivery.
- Current known-limit entry is closed only after CLI reproduction.

## Fable prompt

```text
Try to make an applicable gate disappear using limit values, rank ties, zero relevance, narrow scopes, conflicts, supersession, malformed state, and many higher-ranked soft rules. A clean result means every applicable gate remains visible and the output does not falsely report all rules were considered when soft rules were omitted.
```

---

# LOOP 5: Create a mandatory recorded application path

## Goal

Stop substantial work from depending on the model remembering `--record-applications`.

## Invariant

The standard substantial-work command retrieves and records applications. Read-only lookup remains available under a different command.

## Assigned agents

- Learning Agent: writer.
- Documentation Agent: later writer.
- Fable: reviewer.

## Proposed CLI split

```bash
python3 tools/bm_learn.py lookup --query "..."
python3 tools/bm_learn.py apply --query "..." --session <id> --record <work-id>
```

Contract:

- `lookup` never writes.
- `apply` always attempts to record.
- `apply` requires session identity.
- For substantial work, `apply` should require or strongly enforce a work record.
- Recording failure must not hide the retrieved rules, but must produce a loud nonzero bookkeeping status or a structured partial-success result.
- The constitution uses `apply`, not `relevant` plus an optional flag.

Backward compatibility:

- Keep `relevant` temporarily as an alias with a deprecation message.
- Remove ambiguity in the next major version.

## Required data

Every application must include:

- Retrieval-run identity.
- Rule UUID and version.
- Session identity.
- Work record UUID where available.
- Whether it was shown.
- Scope match.
- Rank and retrieval mode.

## Required tests

- `lookup` changes no database rows.
- `apply` records every returned rule version.
- Re-running `apply` is idempotent.
- Re-running after a work record is created links previously unlinked rows.
- Recording failure returns rules plus an explicit failure status.
- `SKILL.md` contains no substantial-work path that omits application recording.

## Acceptance criteria

- There is one obvious agent path for substantial work.
- An agent following `SKILL.md` cannot accidentally perform unrecorded retrieval without deviating from the command contract.
- Read-only human exploration remains available.

## Fable prompt

```text
Try to complete a substantial task while retrieving founder rules but leaving no application rows. Follow only documented instructions. Look for aliases, default flags, missing session IDs, failed writes reported as success, and re-runs that duplicate or silently lose work-record links.
```

---

# LOOP 6: Persist complete retrieval-run context

## Goal

Make retrieval misses and scope errors measurable from stored facts rather than reconstructed guesses.

## Invariant

Every recorded retrieval has a complete immutable record of the task context and retrieval parameters used at that time.

## Assigned agents

- Store Agent: schema and migration writer.
- Learning Agent: API and CLI writer after schema lands.
- Fable: migration and attribution reviewer.

## Proposed schema

Add `learning_retrieval_runs`:

```sql
CREATE TABLE learning_retrieval_runs (
  retrieval_uuid TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  record_uuid TEXT REFERENCES records(lifecycle_uuid),
  task_fingerprint TEXT NOT NULL,
  task_excerpt TEXT NOT NULL DEFAULT '',
  query_hash TEXT NOT NULL,
  project_key TEXT NOT NULL DEFAULT '',
  domain_key TEXT NOT NULL DEFAULT '',
  artifact_key TEXT NOT NULL DEFAULT '',
  relationship_key TEXT NOT NULL DEFAULT '',
  tool_key TEXT NOT NULL DEFAULT '',
  requested_limit INTEGER NOT NULL,
  retrieval_mode TEXT NOT NULL,
  eligible_count INTEGER NOT NULL,
  returned_count INTEGER NOT NULL,
  created_at TEXT NOT NULL
);
```

Add `retrieval_uuid` to `learning_applications`.

Do not store the full raw query by default. Use:

- Non-reversible query hash.
- Bounded scrubbed excerpt only when explicitly justified.

## Migration rules

- Existing application rows remain valid.
- Old rows have `retrieval_uuid` null and are reported as legacy, not silently backfilled with invented context.
- Schema migration is additive and atomic.
- A failed migration leaves the previous store untouched.

## Classification changes

Retrieval-miss calculation must compare:

- The complete stored context.
- The rule corpus and versions that existed at retrieval time where reconstructable.
- The requested limit.
- Gate delivery rules.

If historical corpus reconstruction is impossible, return `not_decidable` rather than using the current corpus as if it were historical.

## Required tests

- Project rule missed when no project rule was returned is now detected.
- Artifact and relationship scopes are preserved.
- Limit-caused miss is labeled separately.
- Legacy application row is reported as incomplete evidence.
- Migration preserves all previous rows.
- Reinjected no-context design causes the test to fail.

## Acceptance criteria

- Retrieval misses have a defensible denominator.
- Reports distinguish relevance misses, limit misses, and incomplete historical evidence.
- No raw task prompt is stored by default.

## Fable prompt

```text
Try to make the classifier blame the wrong rule or miss a rule by exploiting absent scope fields, changed rules, edited versions, low result limits, missing work records, and legacy rows. Require it to say not_decidable whenever the historical facts are insufficient.
```

---

# LOOP 7: Add FTS5 with deterministic fallback

## Goal

Improve retrieval quality while preserving local simplicity, explainability, and deterministic fallback.

## Invariant

FTS5 is an optional fast path. Lexical retrieval remains fully functional and test-equivalent when FTS5 is unavailable or unhealthy.

## Assigned agents

- Learning Agent: ranking design.
- Store Agent: FTS schema and maintenance.
- Security Agent: query and export review.
- Fable: retrieval adversary.

## Design principles

1. Probe FTS5 availability at runtime.
2. Never make FTS5 mandatory for store opening.
3. Maintain the index transactionally with rule version changes.
4. Verify index drift.
5. Expose retrieval mode in every result and application row.
6. Retain scope filtering before relevance ranking.
7. Return all applicable gates regardless of FTS result.
8. Do not add embeddings in this loop.

## Proposed FTS content

Index the current injectable rule version fields:

- Trigger text.
- Action text.
- Because text.
- Domain.
- Scope key.
- Tags when tags become real data.

Do not index:

- Raw founder corrections.
- Evidence excerpts.
- Rejected candidate source text.

## Ranking

Recommended order:

1. Gate delivery.
2. Exact scope specificity.
3. Rule state.
4. FTS BM25 score.
5. Exact lexical overlap bonus.
6. Stable UUID tie break.

Every result explanation must include named components rather than one opaque score.

## Drift handling

`bm_learn.py verify` must detect:

- Missing FTS rows.
- Extra FTS rows.
- Text mismatch between source table and index.
- Index referencing non-current versions.

Provide:

```bash
python3 tools/bm_learn.py rebuild-index
```

This command must be atomic or rebuild into a temporary index and swap.

## Required tests

- Semantic-ish phrase overlap improved through FTS stemming or tokenization.
- Exact lexical fallback works when FTS creation is forced to fail.
- FTS failure never prevents gate delivery.
- Index drift is detected.
- Rebuild restores parity.
- Raw evidence never appears in FTS tables.
- Retrieval results name `mode=fts5` or `mode=lexical` honestly.

## Acceptance criteria

- FTS5 improves measured retrieval on a labeled founder-rule fixture.
- Lexical fallback passes the same safety fixtures.
- No mandatory dependency is added.
- No raw founder transcript text is indexed.

## Fable prompt

```text
Attack FTS retrieval with stale indexes, missing rows, rule edits, deleted rules, Unicode text, punctuation, French and Japanese phrases, zero-result queries, malicious query syntax, and an environment with FTS5 unavailable. Verify the fallback is complete and that raw founder source text never enters the index.
```

---

# LOOP 8: Close fence installation and Bash-boundary claims

## Goal

Make file-ownership protection easy to enable and precisely state what it can and cannot protect.

## Invariant

All supported direct editing tools are gated by installed hooks. Unsupported shell-write behavior is either safely constrained or explicitly outside the guarantee.

## Assigned agents

- Hook and Fence Agent: writer.
- Security Agent: reviewer.
- Documentation Agent: claims writer.
- Fable: bypass reviewer.

## Workstream A: Install the fence hook

- Add PreToolUse fence hook to installer and Quickstart.
- Verify it is active after installation.
- Add a `doctor` check that performs a harmless blocked-write simulation.
- State fail-open behavior and why.

## Workstream B: Bash writes

Do not pretend arbitrary shell parsing is reliable.

Choose one or more explicit strategies:

### Strategy 1: Claim-aware shell wrapper

Provide a wrapper for high-risk generated shell writes:

```bash
bm shell --record <work-id> -- <command>
```

The wrapper requires the caller to declare affected paths before execution.

### Strategy 2: Policy restriction

The constitution prohibits using Bash for file writes when Edit or Write is available.

### Strategy 3: High-risk command detection

Warn or block a small, explicit set of obvious write operators and commands. Do not claim complete shell understanding.

Recommended combined policy:

- Use Edit/Write for ordinary file changes.
- Use declared-path shell wrapper for unavoidable generated writes.
- Treat unknown arbitrary Bash writes as outside mechanical protection.

## Required tests

- Edit without a claim is blocked.
- Edit with a claim succeeds.
- Another session's claim blocks the write.
- Fence hook missing is detected by doctor.
- Installer wires the hook.
- Shell wrapper refuses no-path execution for a write command.
- Raw Bash bypass remains documented and cannot be described as protected.

## Acceptance criteria

- Main installation enables the fence hook.
- The one-writer claim is narrowed to the supported boundary.
- No documentation says "ever" or "impossible" without qualification.
- Fable cannot bypass supported edit tools.

## Fable prompt

```text
Try to write outside a claim using every supported Claude Code edit path, NotebookEdit, symlinks, path aliases, case differences, Unicode normalization, relative paths, shell redirection, Python one-liners, sed -i, and temporary-file replace patterns. Separate true supported-boundary defects from unavoidable arbitrary-shell limits.
```

---

# LOOP 9: Make local and CI gates equivalent

## Goal

Ensure the same safety claims are tested locally and in continuous integration.

## Invariant

Every suite included in the local release gate runs in CI on every supported platform where it is meaningful.

## Assigned agents

- CI and Release Agent: workflow writer.
- Hook and Fence Agent: fence-suite reviewer.
- Fable: CI omission reviewer.

## Tasks

1. Add `tools/test_bm_fence_hook.py` to CI.
2. Decide whether CI should run `tools/test_all.py` in one serial job in addition to split platform jobs.
3. Preserve per-platform evidence.
4. Add a check that every `test_*.py` suite is represented in CI metadata.
5. Remove module-renaming behavior from tests if possible.
6. If test architecture cannot be fixed now, add an interprocess lock so two local gates cannot corrupt each other.
7. Add timeout and hung-suite diagnostics.
8. Store full test output as CI artifacts on failure.

## Required tests

- Add a temporary failing fence test and prove CI fails.
- Add an unlisted suite and prove both local and CI meta-checks refuse.
- Simulate concurrent local gate runs.
- Prove zero-test execution fails.

## Acceptance criteria

- Fence hook suite runs in CI.
- Local and CI suite inventories match.
- A suite cannot silently exist outside the gate.
- CI retains evidence from all matrix legs.
- The underlying concurrent-suite hazard is fixed or guarded with a visible remaining limit.

## Fable prompt

```text
Find any production safety claim whose test is absent from CI, any suite that can exit zero after running nothing, any cancelled matrix leg mistaken for a pass, any platform excluded without documentation, and any concurrent test behavior that corrupts repository files.
```

---

# LOOP 10: Eliminate documentation and generated-fact drift

## Goal

Stop active documentation from carrying stale test counts, versions, branch names, or status claims.

## Invariant

Facts that can be generated are generated. Historical handovers remain historical and are visibly dated.

## Assigned agents

- Documentation Agent: writer.
- CI and Release Agent: generated fact source.
- Fable: contradiction reviewer.

## Proposed generated facts file

Create a command such as:

```bash
python3 tools/bm_project_facts.py
```

It should output:

```json
{
  "version": "...",
  "schema_version": 2,
  "test_suites": 4,
  "tests_run": 598,
  "tests_skipped": 2,
  "retrieval_modes": ["lexical", "fts5"],
  "supported_python_floor": "3.9",
  "default_branch": "main",
  "release_tag": "..."
}
```

Do not make docs depend on a number that changes every test addition when a number is unnecessary.

Prefer wording such as:

- "Run the full gate and expect ALL GREEN."

instead of:

- "Expect exactly 598 tests."

Keep exact counts only in dated release evidence.

## Tasks

1. Audit README, Quickstart, Setup, Changelog, Known Limits, Not Finalized, handovers, and whitepaper source.
2. Classify each fact:

- Stable contract.
- Generated current fact.
- Dated historical fact.
- Opinion or positioning.

3. Remove stale current numbers.
4. Mark historical handovers as historical at the top.
5. Add a documentation consistency test for:

- Version.
- Schema version.
- Hook count.
- Primary install command.
- Current default branch.

## Acceptance criteria

- No active user document contains a stale test count.
- Install commands agree.
- Version references agree.
- Historical documents are not mistaken for current state.
- Fable finds no contradictory current claim.

## Fable prompt

```text
Read every user-facing document as a new installer. Identify contradictions in version, branch, hook count, test commands, feature availability, release status, platform support, and known limits. Treat a dated handover as acceptable only if it clearly says it is historical.
```

---

# LOOP 11: Close privacy, export, and Windows protection gaps

## Goal

Ensure exports and local storage match the stated privacy model across platforms.

## Invariant

Sensitive founder text is withheld by default. Platform-specific protection claims are tested and accurately scoped.

## Assigned agents

- Security Agent: writer.
- Store Agent: transactional reviewer.
- CI and Release Agent: Windows CI reviewer.
- Fable: adversarial security reviewer.

## Workstream A: General dump privacy

Current learning raw text is withheld, but ordinary prose can still pass through the general scrubber.

Review these fields at minimum:

- `records.objective`
- `records.evidence`
- `digests.body`
- `transitions.note`
- Decision text
- Directive text
- Absolute paths

Choose one of these export policies:

### Recommended default

- Withhold all founder-authored prose and absolute paths in ordinary dump output.
- Provide `--show-sensitive` or `--raw` only with a warning.
- Keep structural identifiers, states, hashes, counts, and timestamps.

Add one central withholding policy shared by all JSON and text exports.

## Workstream B: Windows ACLs

- Implement owner-only ACL handling where supported.
- If reliable ACL configuration cannot be implemented with the standard library, investigate a minimal platform-specific command only inside a clearly isolated Windows adapter.
- Do not claim owner-only recovery on Windows until tested on a real Windows host or a trusted dedicated runner.

## Workstream C: MCP read-only guarantees

- Add committed automated tests for copy-first behavior.
- Add tests proving real store bytes and sidecars remain unchanged.
- Add cleanup-failure reporting tests.
- Test Windows behavior.

## Workstream D: Secret scans

- Test vendor-shaped keys with prefixes, suffixes, underscores, punctuation, and long input.
- Add performance ceilings for redaction.
- Confirm no raw founder text enters ordinary logs or FTS tables.

## Acceptance criteria

- Default dump cannot reproduce founder prose or absolute paths.
- Raw output requires explicit opt-in and warning.
- Windows claims match actual evidence.
- MCP copy-first behavior is automated, not hand-tested only.
- Security review adds no new silent-failure path.

## Fable prompt

```text
Try to exfiltrate founder text, client names, numbers, paths, API keys, bearer tokens, database content, and another project's data through dump, JSON output, exceptions, verify findings, MCP responses, temporary copies, symlinks, hardlinks, Windows sidecars, and cleanup failures. Measure long-input redaction time and search for quadratic behavior.
```

---

# LOOP 12: Move handovers into the transactional store

## Goal

Replace lock-serialized append handovers with transactional handover records rendered into generated views.

## Invariant

A lifecycle transition and its handover are committed together or not at all.

## Assigned agents

- Store Agent: schema and transaction writer.
- Hook and Fence Agent: thread integration writer after store API lands.
- Fable: crash and retry reviewer.

## Proposed schema

```sql
CREATE TABLE handovers (
  handover_uuid TEXT PRIMARY KEY,
  lifecycle_uuid TEXT NOT NULL REFERENCES records(lifecycle_uuid),
  from_session_id TEXT NOT NULL,
  to_session_id TEXT NOT NULL DEFAULT '',
  transition_id INTEGER,
  next_intent TEXT NOT NULL DEFAULT '',
  blockers TEXT NOT NULL DEFAULT '',
  files_note TEXT NOT NULL DEFAULT '',
  body TEXT NOT NULL DEFAULT '',
  delivered_at TEXT,
  created_at TEXT NOT NULL,
  UNIQUE(lifecycle_uuid, transition_id)
);
```

## Required behavior

- Park or adopt writes transition and handover in one transaction.
- Generated `STATE.md` renders undelivered handovers.
- Delivery is idempotent.
- Retry cannot duplicate text.
- Refused adoption writes nothing.
- Crash after commit but before render is recoverable by regeneration.
- Crash before commit changes nothing.

## Migration

- Existing appended handovers remain in human prose.
- Do not parse and re-import them unless a reliable marker exists.
- New handovers use the database only.

## Required tests

- Transition commit failure leaves no handover.
- Handover insert failure leaves no transition.
- Render failure preserves database truth.
- Retry after render failure does not duplicate.
- Refused adoption changes no state and writes no handover.
- Concurrent handovers serialize through SQLite transaction.

## Acceptance criteria

- Lock and append path are deleted for new handovers.
- Store is the sole source of handover truth.
- State view can be regenerated without loss.
- Original partial status becomes CLOSED only after crash-injection tests.

## Fable prompt

```text
Attack every boundary between lifecycle transition, handover insert, generated view write, crash, retry, duplicate command, concurrent adoption, and refused adoption. Try to create a state where the record says parked but no handover exists, or a handover exists for a transition that never committed.
```

---

# LOOP 13: Real founder dogfood window

## Goal

Determine whether BrotherMode improves real work without imposing unacceptable ceremony or producing noisy learning.

## Duration

Minimum:

- 10 real working days.
- At least 30 substantial tasks.
- At least 3 different project or artifact categories.

Recommended:

- 20 working days.
- 60 substantial tasks.

## Assigned agents

- Founder: real user and final source of corrections.
- Dogfood Observer: measurement steward.
- Chief: fixes only release-blocking defects during the window.
- Fable: weekly read-only adversarial review.

## Freeze rule

Before the window starts:

- Tag the dogfood build.
- Do not add speculative features during the window.
- Fix only defects that block work, lose data, violate privacy, or invalidate the measurement.
- Record every intervention.

## Required measurements

### Usage

- Number of substantial tasks.
- Number of retrieval runs.
- Number of applications recorded.
- Number of work records linked.
- Number of rules retrieved per task.

### Quality

- Relevant retrievals.
- Irrelevant retrievals.
- Missed known rules.
- Gate delivery failures.
- Compliance failures.
- Bad-rule findings.
- Scope errors.
- Not-decidable findings.

### Learning

- Candidates automatically captured.
- Candidates manually captured.
- Candidates approved.
- Candidates rejected by category.
- Duplicate candidates.
- Contradictions.
- Repeated confirmed or settled corrections.

### Burden

- Minutes spent reviewing candidates.
- Minutes spent closing applications.
- Tasks where BrotherMode felt like unnecessary ceremony.
- Tasks where BrotherMode prevented rework or context loss.
- Tasks where recovery was used.

### Reliability

- Hook failures.
- Store refusals.
- Recovery failures.
- Installation or upgrade issues.
- Cross-platform issues.

## Daily protocol

At the end of each working day:

1. Run `bm_learn.py loop-failures`.
2. Review pending candidates.
3. Close unknown applications where evidence exists.
4. Record one short friction note.
5. Record one benefit note only if a specific event supports it.
6. Do not rewrite yesterday's data.

## Weekly review questions

- Did the founder repeat any correction that a live rule should have prevented?
- Was the rule absent, not retrieved, ignored, irrelevant, or wrong?
- Did retrieval noise cause the founder to stop reading rules?
- Did application recording get skipped?
- Did gate rules appear when needed?
- Did any rule need narrower scope?
- Did BrotherMode reduce or increase total task time?
- Did any safety mechanism prevent an actual defect?

## Success criteria

Do not require perfection. Require evidence sufficient for release claims.

Suggested release thresholds:

- At least 90 percent of substantial tasks with recorded retrieval runs.
- Zero suppressed applicable gate rules.
- Zero data-loss events.
- Zero secret exposure events.
- Every repeated correction classified with supporting evidence or marked not decidable.
- Candidate review burden remains acceptable to the founder.
- A measurable majority of retrieved soft rules are judged relevant.
- At least three concrete cases where the system prevented rework, restored context, or identified a bad rule.

## Failure criteria

Pause release if:

- Founder stops using application recording because it is too burdensome.
- More than one in three retrieved soft rules is irrelevant.
- A correction repeats without enough data to explain why.
- Any gate is omitted.
- Store or recovery causes data loss.
- Approval workflow is routinely bypassed.

## Deliverable

Create:

- `docs/dogfood/DOGFOOD-REPORT-<date>.md`

It must include raw counts, failures, exclusions, interventions, and unresolved issues.

## Fable prompt

```text
Review the dogfood data without changing it. Look for survivorship bias, missing denominators, tasks omitted after failures, counts that include scripted probes, interventions that invalidate before-and-after comparison, and claims not supported by the recorded rows. Prefer a smaller honest conclusion over a flattering one.
```

---

# LOOP 14: Independent adversarial re-audit

## Goal

Have a different model family or independent reviewer attack the release candidate without relying on the implementation team's assumptions.

## Entry conditions

- Loops 1 through 12 closed or explicitly deferred.
- Dogfood report complete.
- Release candidate tagged.
- Working tree clean.
- Full gate green.

## Reviewer constraints

The independent reviewer receives:

- Repository.
- Public documentation.
- Known limits.
- Dogfood report.
- No private explanatory conversation from the builders unless requested after initial findings.

## Required audit lenses

1. Release identity and supply chain.
2. Installation and uninstall safety.
3. Store migrations and corruption handling.
4. Approval and learning governance.
5. Retrieval correctness and gate delivery.
6. Application and outcome attribution.
7. Privacy and export behavior.
8. File ownership and shell boundaries.
9. Recovery and crash behavior.
10. Windows and platform claims.
11. Documentation truthfulness.
12. Dogfood evidence quality.

## Finding format

Every finding must contain:

```text
ID
Severity
Claim attacked
Reproduction
Observed result
Expected invariant
Affected files
Suggested fix class
Evidence confidence
```

## Resolution protocol

For each finding:

- Reproduce internally.
- Mark CONFIRMED or REFUTED.
- Fix confirmed blockers serially.
- Add calibrated regression test.
- Ask the independent reviewer to re-test the exact reproduction.

## Acceptance criteria

- No unresolved BLOCKER.
- No unresolved HIGH affecting data loss, privacy, approval, gate delivery, or release identity.
- Medium findings are documented with explicit release decisions.
- Refuted findings remain recorded.

---

# LOOP 15: Final release and public benchmark

## Goal

Publish a release whose claims are narrower than or equal to the evidence.

## Assigned agents

- Chief: final decision.
- CI and Release Agent: release writer.
- Documentation Agent: product wording.
- Fable: final claim audit.

## Final release gates

### Code

- Full local gate green after final edit.
- Full CI matrix green.
- Fence hook suite in CI.
- Clean install test green.
- Upgrade from previous release green.
- Uninstall test green.
- Checksums verified.

### Learning

- Approval semantics match documentation.
- Gate rules cannot be suppressed.
- Substantial retrieval uses recorded application path.
- Retrieval-run context is stored.
- Retrieval mode is named.
- Outcome attribution distinguishes missing evidence.

### Security

- Default exports withhold founder prose and paths.
- Raw export requires explicit opt-in.
- Secret scans green.
- MCP read-only tests green.
- Windows limitations accurately stated.

### Evidence

- Dogfood report published.
- Independent audit published or summarized.
- Known limits current.
- No claim of statistical learning without a valid dataset.

## Public benchmark suite

Create reproducible scenarios:

1. Relevant correction retrieved.
2. Irrelevant rule not retrieved.
3. Applicable gate returned despite limit zero.
4. Conflicting rules surfaced.
5. Rule edit does not rewrite past application history.
6. Retrieval miss classified from complete context.
7. Ignored gate classified as compliance failure.
8. Followed bad rule classified from rework.
9. Repeated correction classified by cause.
10. Forced compaction recovery restores files and context.
11. Conflicting file write blocked through supported edit tool.
12. Default export withholds founder prose.
13. Clean install and uninstall leave expected traces only.

Publish benchmark inputs and expected outputs. Do not publish only a score.

## Approved positioning after successful release

Use wording close to:

> BrotherMode is a local operating system for solo founders that makes AI work recoverable, accountable, and able to retain founder-approved corrections with traceable applications and outcomes.

Stronger wording is allowed only if dogfood and audit evidence supports it.

Do not claim:

- It never repeats mistakes.
- It autonomously improves itself.
- Founder identity is cryptographically guaranteed unless Loop 3 Model A is implemented.
- Every shell write is mechanically fenced.
- Windows owner-only privacy without real evidence.
- Production readiness beyond the tested user and platform scope.

## Final Fable prompt

```text
Act as a hostile buyer and technical auditor. Read only the public release assets first. List every statement that is stronger than the evidence. Then inspect the code and benchmark to determine whether each statement is supported. The release fails if any claim about approval, gate delivery, recovery, privacy, or one-writer safety is materially overstated.
```

---

# 5. Suggested agent dispatch map

The chief should avoid dispatching all agents at once. Use the following waves.

## Wave 1: Public product and release truth

Parallel, disjoint writers:

- CI and Release Agent: Loop 1 branch and version work.
- Documentation Agent: prepares a read-only contradiction report, no edits yet.
- Fable: independent public-install attack.

Then serial integration.

## Wave 2: Core learning correctness

Serial production work:

1. Loop 3 approval semantics.
2. Loop 4 gate delivery.
3. Loop 5 mandatory application path.
4. Loop 6 retrieval context.
5. Loop 7 FTS5.

Fable reviews after each loop. Do not merge all five before review.

## Wave 3: Safety and operations

Parallel only where file sets are disjoint:

- Hook and Fence Agent: Loop 8.
- CI and Release Agent: Loop 9.
- Documentation Agent: Loop 10 preparation.
- Security Agent: Loop 11 design only.

Integrate serially when shared files appear.

## Wave 4: Store lifecycle

- Store Agent owns Loop 12.
- Hook and Fence Agent integrates thread behavior after store API freezes.
- Fable runs crash and retry attacks.

## Wave 5: Evidence

- Dogfood Observer runs Loop 13.
- No speculative implementation during measurement.
- Independent reviewer runs Loop 14.
- Chief and release agents run Loop 15.

---

# 6. Copy-paste chief prompt

Use this at the start of execution:

```text
You are the chief implementer for BrotherMode V2. Execute the post-audit plan in `docs/BrotherMode_V2_Post_Audit_Execution_Loops.md` one loop at a time.

Rules:
1. Read SKILL.md, docs/KNOWN-LIMITS.md, docs/NOT-FINALIZED.md, and the current loop before editing.
2. Run `python3 tools/test_all.py` before edits and record the baseline.
3. Reproduce the current defect or gap before fixing it.
4. Register file fences before dispatching any sub-agent.
5. Use Fable as a read-only adversarial reviewer unless the loop explicitly assigns it a write file.
6. No two agents may write the same file concurrently.
7. Every load-bearing test must be calibrated by reinjecting the defect and proving the test fails for the intended reason.
8. Run focused tests, a real CLI probe against a throwaway store, and the full gate after the final edit.
9. Update Known Limits, Not Finalized, and Changelog honestly.
10. Do not begin the next loop until the current loop is CLOSED or explicitly marked PARTIAL with the remaining gap.

Start with Loop 0 only. Return:
- baseline commit and branch,
- file fences,
- reproduction evidence,
- implementation delta,
- tests and exact outputs,
- Fable findings,
- loop status,
- next loop recommendation.
```

---

# 7. Copy-paste Fable prompt

```text
You are Fable, the adversarial reviewer for BrotherMode V2.

Your default role is read-only. Do not modify production code. You may write only the review file assigned by the chief.

For the current loop:
1. Read the invariant and acceptance criteria.
2. Reproduce the original defect before reviewing the fix.
3. Attack adjacent variants of the same defect class.
4. Inspect whether the new tests can pass for the wrong reason.
5. Inspect failure direction: fail-open versus fail-closed.
6. Inspect whether documentation overstates what code enforces.
7. Report REFUTED concerns as clearly as confirmed findings.
8. Do not accept another agent's report as evidence. Run or inspect the mechanism yourself.

Return each item as:
- ID
- Severity: BLOCKER, HIGH, MEDIUM, LOW, or REFUTED
- Invariant attacked
- Exact reproduction or static proof
- Observed result
- Why it matters
- Minimum fix class
- Whether the loop may close
```

---

# 8. Copy-paste specialist prompts

## Store Agent

```text
You are the Store Agent. Your scope is transactional schema, migrations, constraints, lifecycle integrity, and store APIs. You may modify only the files explicitly fenced to you. Keep `bm_store.py` the only database writer. Use additive, atomic migrations. Never invent historical data during migration. Every failure must leave the previous state intact or produce a precise refusal. Provide focused tests and calibrated defect reinjection.
```

## Learning Agent

```text
You are the Learning Agent. Your scope is correction detection, rule semantics, retrieval, application recording, classification, and the founder-facing learning CLI. Keep pure logic in `bm_learning.py`, store mutations in `bm_store.py`, and presentation in `bm_learn.py`. Never silently approve, resolve a conflict, infer missing evidence, or call unknown data a zero. Every retrieval result must explain why it appeared and name its mode.
```

## Security Agent

```text
You are the Security Agent. Your scope is sensitive text, export withholding, redaction, containment, permissions, temporary files, MCP read-only behavior, and platform-specific privacy. Default-deny every new text field. Treat ordinary founder prose and absolute paths as sensitive, not only vendor-shaped secrets. Reproduce leakage end to end. Measure long-input behavior. Never describe Windows protection using POSIX assumptions.
```

## Hook and Fence Agent

```text
You are the Hook and Fence Agent. Your scope is hook installation, hook health, supported edit-tool enforcement, file claims, and documented shell boundaries. Do not claim arbitrary Bash parsing is complete. Make supported paths mechanically strong and unsupported paths explicitly outside the guarantee. Provide a doctor probe that proves the installed hook is active.
```

## CI and Release Agent

```text
You are the CI and Release Agent. Your scope is default branch, tags, VERSION, release notes, checksums, clean install, upgrade, uninstall, and CI coverage. An immutable tag may never move. A cancelled or missing matrix leg is not a pass. Every local suite must be represented in CI. A release is the exact tested bytes, not a branch name.
```

## Documentation Agent

```text
You are the Documentation Agent. Your scope is active user-facing truth. Do not repeat generated facts manually when they can drift. Distinguish current contract, generated current fact, dated historical evidence, and positioning. Prefer a narrower accurate claim over a stronger unsupported one. Every install command must install the product being described.
```

## Dogfood Observer

```text
You are the Dogfood Observer. You preserve evidence; you do not improve the appearance of results. Record denominators, missing data, skipped tasks, interventions, and failures. Do not mix scripted probes with real founder work. Do not call no data zero. Do not change the measurement design during the window without recording the break in comparability.
```

---

# 9. Final release checklist

## Public identity

- [ ] Default branch contains V2.
- [ ] README describes V2.
- [ ] Primary install command installs the released V2 tag.
- [ ] VERSION, tag, and changelog agree.
- [ ] Clean install verified.

## Approval and learning

- [ ] Approval guarantee is mechanically true or wording is narrowed.
- [ ] Automatic detection cannot approve.
- [ ] Gate rules cannot be suppressed by limits.
- [ ] Substantial-work retrieval records applications.
- [ ] Retrieval-run context is complete.
- [ ] Rule versions remain immutable.
- [ ] Conflicts and supersession are verified.
- [ ] FTS5 falls back cleanly to lexical mode.

## File safety and recovery

- [ ] Fence hook installed by default.
- [ ] Supported edit tools cannot write outside claims.
- [ ] Bash boundary is accurately documented.
- [ ] Autosave and recovery pass on supported platforms.
- [ ] Handovers are transactional.

## Testing

- [ ] Full local gate green.
- [ ] Full CI inventory matches local inventory.
- [ ] Fence suite runs in CI.
- [ ] Tests cannot pass after running zero cases.
- [ ] Load-bearing guards are calibrated.
- [ ] Independent audit has no unresolved blocker.

## Privacy

- [ ] Default exports withhold founder prose.
- [ ] Default exports withhold absolute paths.
- [ ] Raw export is explicit and warned.
- [ ] MCP copy-first behavior is automated in tests.
- [ ] Windows privacy claims match evidence.
- [ ] Secret scan and performance tests pass.

## Evidence

- [ ] Real dogfood window completed.
- [ ] Dogfood report includes failures and denominators.
- [ ] Public benchmark is reproducible.
- [ ] Known Limits is current.
- [ ] Not Finalized is current.
- [ ] Claims do not exceed evidence.

---

# 10. Definition of done

BrotherMode V2 is ready for a stable public claim only when all of the following are true:

1. A stranger installs the intended V2 product from the root repository without knowing which branch to choose.
2. The installed version is immutable and verifiable.
3. Automatic detection cannot silently create behavioral rules.
4. The approval guarantee says exactly what the code enforces.
5. Applicable gate rules always reach the acting model.
6. Substantial retrieval is recorded by default.
7. Retrieval misses can be measured from complete stored context.
8. Better retrieval does not add a mandatory service or dependency.
9. The fence hook is actually installed and tested.
10. Shell boundaries are honest.
11. Local and CI gates cover the same suite inventory.
12. User documentation contains no stale current facts.
13. Default exports protect founder prose and paths.
14. Handovers commit with lifecycle transitions.
15. Real founder use demonstrates the workflow is valuable and tolerable.
16. An independent adversarial reviewer fails to find an unresolved release blocker.
17. The final product claims are no stronger than the evidence.

Until then, call it a strong release candidate with category-leading architecture, not a fully proven market leader.
