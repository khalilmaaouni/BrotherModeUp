# The toolkit broker: design, not build

Status: CURRENT

Q2 of `docs/plan/REPLAN-2026-08-12.md`. `toolkit` is one of the six public
names and is marked NOT BUILT, with no stub and no placeholder folder. This
designs what it would be. **Nothing here is implemented.**

---

## 1. The problem, from failures that actually happened on this machine

Every example below is from the founder's own records, not invented.

1. **A tool was installed and was listening to the whole network.** A local
   proxy shipped with its host defaulting to `0.0.0.0` and, by its own
   settings comment, required no authentication when its token was empty,
   which was the default. Proven rather than assumed: an unauthenticated
   request from the LAN address answered with a service error rather than an
   authorisation error, meaning nothing was gating it. With a provider key
   present, anyone on the same network could have spent that quota and read
   through it.
2. **A tool that saves tokens silently granted read of anything.** A
   compression hook returns "allow" on everything it wraps, so leaving its
   file processor enabled would auto-approve reading any file, private keys
   and environment files included, with no prompt. Its documented redaction
   did not fire on that path: a 62-line environment file came back with its
   secret access key and API key in clear text.
3. **Three versions of one tool on one machine, and the one on the PATH was
   two majors behind.** Nothing noticed, and it surfaced as a missing command
   that was reported as a product defect when it was an install defect.
4. **A tool's installer offered to rewrite the global config** that carries
   the spend guard, the session cap and the fence hooks. Declining it was a
   judgement call a person made, once, from reading the flag.

The pattern: **capability arrives with trust attached by default, and the
trust is invisible until something goes wrong.** Not one of these was a bug in
the tool. Each was a tool behaving as documented, trusted more than it had
earned.

## 2. What the broker is, in one sentence

A place where a capability is declared before it is used, so that what a tool
may reach is a property of a record rather than a property of whoever
installed it.

It is not a sandbox. This product does not and will not claim operating-system
containment; that disclaimer is already on the front page and this must not
quietly contradict it.

## 3. Criteria

1. **A capability's trust is visible without running it.** Failure 1 was
   invisible until probed.
2. **Default is the lowest useful trust**, never the highest. Every failure
   above is a permissive default.
3. **Revocation is cheaper than installation.** Today removing a tool's reach
   means uninstalling it.
4. **It must not become a second permission system** competing with the
   harness's own. Two systems disagreeing is worse than one.
5. **A person can read the whole trust state on one page.**

Criterion 4 is the one that kills most designs, and it is why this is a
broker and not a gate.

## 4. Alternative A, REJECTED: intercept and police every tool call

The broker sits in front of tool execution and allows or denies.

**Why it is attractive:** it is the only design that actually stops anything.

**Why it is rejected:** it fails criterion 4 outright. The harness already has
a permission system, and tonight is the evidence that it works: a classifier
refused a write to the live setup, correctly, and I did not work around it. A
second gate would either duplicate that (two answers, drift, the exact
two-parsers problem that already cost hours here when a grep said zero and a
hook saw four) or contradict it. It also implies containment this product
explicitly does not offer, which would make the front page a lie.

**What would flip it:** owning the runtime. Not on any horizon.

## 5. Alternative B, REJECTED: a curated registry of approved tools

A vetted list; using something off-list is a finding.

**Why it is attractive:** simple, inspectable, satisfies criteria 1 and 5.

**Why it is rejected:** it fails criterion 2 in practice, because approval is
granted once per tool and never per capability. Every failure above involved
an *already approved* tool: the founder chose all four deliberately. A list
would have said yes to each. Approving a name tells you nothing about what it
reaches, and the thing that hurt was reach, not identity.

**What would flip it:** if tools were static. They are not; failure 3 is a
tool changing under a fixed name.

## 6. The design, RECOMMENDED: declared capability records with tiers and quarantine

A tool is used through a **capability record** describing what it needs, in
the same store that already holds work records and claims.

**The record carries:** what the tool is; what it reaches (network, filesystem
paths, credentials, subprocess); which tier it is in; the evidence that tier
was earned; and what would demote it.

**Three tiers, and the names mean something.**

- `quarantined`: declared, not used. New arrivals land here. Its reach is
  written down and nothing has exercised it. **This is the default**, which is
  criterion 2 satisfied structurally rather than by discipline.
- `scoped`: used, within a stated reach, with the evidence of what it was
  observed to touch. Promotion out of quarantine requires that observation,
  not an assertion.
- `trusted`: used without per-use narration, only for tools whose reach is
  read-only or fully local, and never for anything holding a credential.

**Demotion is automatic and is the important half.** A tool whose observed
reach exceeds its record drops to `quarantined` and says why. Failure 3 is the
motivating case: the version changed, so the record no longer described the
thing, so the record should stop vouching for it. Version is part of identity.

**Why this is a broker and not a gate.** It does not stop the call. It makes
the trust a fact on disk that a check can read, so `doctor` can report "two
tools are being used above their declared tier" the way it already reports a
stale manifest. **The enforcement stays where enforcement already works, in
the harness's own permission system**, and this supplies the thing that system
has no opinion about: what was supposed to be true.

Stated plainly, because the founder's own law demands it: **this is
UNENFORCED against a determined tool.** A capability record does not constrain
a process. It makes divergence visible and countable. Any document claiming
more than that about this design is wrong.

### Consequences

- **Declaring capability is work at exactly the wrong moment**, when somebody
  wants to use a new tool now. This will be skipped, and the honest mitigation
  is that undeclared use is a `doctor` finding rather than a refusal.
- **Observed reach requires observation.** Something must record what a tool
  touched, and this design does not say what. That is a real gap and it is
  named rather than hidden.
- **Three tiers will be argued about.** Fewer would be cruder; more would not
  be used.

### Flip condition

**If, after a month of use, no tool has ever been demoted, the demotion path
is not running and this is a registry with extra words**, which is Alternative
B and should be simplified into it.

## 7. What needs the founder

1. **Does `toolkit` ship as a public name before any of this exists?** It is
   currently marked NOT BUILT, which is honest. This design does not change
   that and must not be read as shipping it.
2. **Is `trusted` allowed at all**, or do all tools stay `scoped` forever? The
   argument for never having a top tier is that every failure above involved a
   tool somebody had decided to trust.
3. **Who observes reach?** Without an answer, promotion out of quarantine
   cannot be evidence-based, and the whole design degrades to Alternative B.

## 8. Done-check

Complete when a reader can state what was rejected and why, what would flip
the recommendation, what this design does NOT enforce, and what needs a
founder decision. All four are present, and the third is section 6's own
plain statement.
