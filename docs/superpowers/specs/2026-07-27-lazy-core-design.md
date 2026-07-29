# Design: the lazy core, and closing the rest of the audit

**HISTORICAL DOCUMENT, dated 2026-07-27. Do not read it as current state.** It is a dated working record: the plan, the verdicts, the blockers and the numbers in it belong to that day and were not updated afterwards. Items it calls open may since have been closed. Superseded by `README.md` and `docs/KNOWN-LIMITS.md` for status, `docs/NOT-FINALIZED.md` for the defect register, `CHANGELOG.md` for what changed since, and `python3 tools/bm_project_facts.py` for version, release tag, hook events and suites.

Founder decisions taken 2026-07-27, both recorded before any code:

1. **The safety floor becomes mechanism, not prose.** Prose can be skipped by a
   model; a hook cannot. Chosen over "keep a small prose floor".
2. **Both audiences, sequenced.** Phase 1 blockers (protect the founder's own
   data), Phase 2 the lazy core (the cost paid daily), Phase 3 public install.
   Nothing public ships until Phase 1 is green.

## The framing correction this design rests on

An external comparison scored BrotherMode against native Claude Code and
concluded there is a trade: native wins simplicity, immediacy and small tasks;
V2 wins continuity, discipline and decision support.

That trade is an artifact of ONE implementation detail, not a law. `SKILL.md` is
534 lines, about 10,000 tokens, and it loads whole into every session whether the
task is a typo fix or a codebase audit. Lazy loading does not balance the trade.
It dissolves it.

Two claims in that report are also worth answering directly rather than
accepting:

- "Beat native at simplicity" is unwinnable as literally scored. A layer on top
  of Claude cannot cost less than Claude alone, because Claude alone costs zero.
  The achievable and honest target is **invisible until valuable**.
- Optimizing to another model's scorecard is precisely the anti-pattern this
  skill already encodes ("the learning target is the founder model, never this
  system's own scorecard"). The report is used here to FIND real gaps, never as
  a target function. Where a number does not move, it gets reported unmoved.

## The synergy that makes this one job instead of two

Audit finding 8 says the single-writer fence is a coordination ledger rather than
an enforcement boundary, because nothing checks a write against an active claim.

The lazy core needs exactly that check as its always-on tier.

So the `PreToolUse` ownership hook closes a critical security blocker AND is what
permits the prose to become optional. One change, two dimensions. Any plan that
treats them as separate work is doing the same thing twice.

## Architecture: three tiers

**Tier 0, always on, near zero prose cost.** Unconditional laws become hooks:

| Hook | Enforces |
|---|---|
| `PreToolUse` | blocks Edit/Write outside an active claim (finding 8) |
| `SessionStart` | injects the 8-line active-laws digest (exists today) |
| `PreCompact` | snapshot plus resume brief (exists today) |
| `SessionEnd` | mechanical telemetry (exists today) |

`SKILL.md` drops to roughly 60 lines: complexity triage plus a router table.

**Tier 1, on demand.** `references/` files loaded only when the triage calls for
them: profiles, delegation, verification, founder model, telemetry, recovery.
This is the documented Claude Code progressive-disclosure pattern, so it works
with the platform rather than against it.

**Tier 2, deep.** Fleet orchestration and adversarial review, at T3 only.

## The measurable target

**Tokens spent before the first useful action.**
Native 0. V2 today about 10,000. Target under 400 for a simple task, with full
depth still reachable when the work earns it.

Founder-legible restatement: how much does BrotherMode cost you before it helps.

## The risk, and its mechanical guard

Lazy loading can silently drop a law. The dimensions this project currently wins
(founder decision support, multi-role discipline) are exactly the ones that
degrade QUIETLY when a reference is never read. A silent degradation is worse
than a loud one because nothing reports it.

Guard: a `Stop` hook audits the finished session and flags when depth was
warranted but never loaded. Mechanical, not a promise.

Kill criterion for Phase 2: if any dimension currently won degrades, the
extraction reverts. The best version of the law is kept, not the latest.

## The loops

**Loop 1, Phase 1 blockers.** The shape that closed 12 findings on 2026-07-27:
verify by execution BEFORE fixing, disjoint fenced writers, every test calibrated
in both directions, CI on three platforms as the external judge. Ordered by harm.

Order: finding 1 (false autosave assurance) first, because it is reassurance
without truth in the subsystem that exists to protect the founder's work. Then 5
(git-tracked store), 8 and 8B (write fence plus forgeable session identity), 9
and 10 (raw name lookup, ambiguity must refuse), 11 (root containment INTO
resolve_root, never by flipping precedence, which would reopen F2/F42), 12
(handover into the transaction), 13 (ref compare-and-swap), 16 (secret denylist),
6 (release identity: withdraw rc.1, cut rc.2 from a green commit, checksums last).

**Loop 2, Phase 2 shrink.** Extract ONE reference at a time. After each, re-measure
tokens-before-first-action and re-run all suites. Revert on any degradation.

**Loop 3, Phase 3 install.** The honest test of setup is someone who has never
seen it. An agent with zero context installs from the tag into a clean directory
and reports where it got stuck. Its confusion IS the bug list.

**Loop 0, standing.** A closing adversarial fleet re-audits all 17 original
findings plus the report's dimensions, with a second model family where available,
because refuters from one family share one family's blind spots.

## Out of scope, deliberately

- Chasing the report's numbers as a target.
- Any public onboarding polish before Phase 1 is green.
- Rewriting laws that are working; Phase 2 MOVES prose, it does not rewrite it.

## Measured baseline and the extraction map (added 2026-07-27, by command)

Always-on cost today: **10,407 tokens** before the first useful action
(SKILL.md 10,062 plus the SessionStart hook 344). Target: under 400.

Per-section weight, measured rather than estimated:

| Section | Lines | ~Tokens | Tier |
|---|---:|---:|---|
| 8. Improvement loops | 100 | 1,984 | ON DEMAND (session close) |
| 3. Delegation and routing | 55 | 1,079 | ON DEMAND (T2 and above) |
| 1. Work profiles | 40 | 782 | ON DEMAND (after triage) |
| 5. Fences and harness | 38 | 736 | HOOK (tier 0 mechanism) |
| 11. Computer control | 40 | 709 | ON DEMAND |
| 14. Founder model | 35 | 682 | ON DEMAND (decision work) |
| 13. Known-mistakes ledger | 28 | 511 | ON DEMAND |
| preamble | 25 | 448 | TRIM to about 150, always on |
| 4. Token budgets | 24 | 431 | ON DEMAND (merge into delegation) |
| 15. Scoring | 22 | 420 | ON DEMAND (session close) |
| 7. Solutioning triage | 19 | 359 | ALWAYS (it is the router) |
| 10. Honesty and push-back | 20 | 341 | TRIM, partly always on |
| 12. Structured memory | 17 | 322 | ON DEMAND |
| 9. Context hygiene | 17 | 304 | ON DEMAND |
| 6. Research doctrine | 14 | 237 | ON DEMAND |
| 2. Role assignment | 8 | 122 | ON DEMAND (merge into profiles) |
| 0. Invocation sequence | 32 | 589 | BECOMES the router table |

The single most valuable observation: **section 8 is 1,984 tokens, a fifth of the
entire always-on cost, and it is needed at session CLOSE, not during work.** It
has been charged on every trivial task since it was written.

Second: section 5 (fences, 736 tokens) does not need to be prose at all once the
PreToolUse hook exists. A law that the hook enforces does not also need to be
recited into context. That is the clearest case of the whole design: mechanism
REPLACES prose rather than sitting beside it.

Proposed tier 0, target about 330 tokens:
  - who you are, and the founder communication rule (about 80)
  - the three-question complexity triage (about 100)
  - the router table: which reference to load for which situation (about 150)

Everything else becomes references/ loaded on demand:
  profiles.md, delegation.md, fences.md, verification.md, founder-model.md,
  improvement.md, recovery.md, context.md, machine.md

Kill criterion stands: extract one at a time, re-measure, re-run all suites, and
revert any extraction that degrades a dimension this project currently wins.
