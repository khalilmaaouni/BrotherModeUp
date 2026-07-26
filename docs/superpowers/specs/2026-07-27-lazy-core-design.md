# Design: the lazy core, and closing the rest of the audit

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
