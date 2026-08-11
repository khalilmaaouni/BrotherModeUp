# One change, two records: design, not build

Status: CURRENT

Q4 of `docs/plan/REPLAN-2026-08-12.md`, and the collaboration promise made
concrete. Founder decision D36 chose two records naming the same change
identifier, over one merged record and over leaving them unlinked. This
designs that. **Nothing here is implemented.**

---

## 1. The problem

Two products meet at exactly one object: the change being handed to somebody
else. This product governs one person's session. The sibling governs that
change's passage between people.

Today nobody can answer the first question a reviewer asks: **"show me the
session work behind this change."** Not because the data is missing, but
because no shared name exists. Each product has a complete record and neither
knows the other's.

Two consequences already visible. Evidence about one change sits in two places
with no way to line it up, so a reviewer either takes it on trust or redoes
the work, which is precisely what the north star forbids. And when a session
hands over, the pack describes the session and not the change, so the
receiving person gets "what I was doing" rather than "what this change needs".

## 2. Criteria

1. **Either product keeps working alone.** Neither may require the other. This
   is not negotiable: most users of each will never install the other.
2. **No shared database, no service, no sync.** D36 and the horizon both. The
   shared store is R3 and needs a migration story.
3. **The link is checkable by a command**, not by a person eyeballing two
   screens. An unverifiable link is worth roughly nothing.
4. **Creating the link costs approximately one command.**
5. **A broken or half-made link is a stated state**, never a silent absence.

## 3. Alternative A, REJECTED: one product writes into the other's store

The session product writes a row into the change product's database.

**Why it is attractive:** exactly one identifier exists, so they cannot
disagree.

**Why it is rejected:** it fails criterion 1 and criterion 2 together, and it
breaks the single-writer law this product enforces on everything else. Two
processes writing one store is the exact class of failure the transactional
store was built to end, and reintroducing it across a product boundary, where
neither side can see the other's locks, is worse than the original.

## 4. Alternative B, REJECTED: derive the identifier from the git branch

Both products key off the branch name.

**Why it is attractive:** free, no new field, and a branch is already the unit
a change travels on.

**Why it is rejected:** it fails criterion 5 in a way that is hard to detect.
Branches are renamed, rebased, deleted after merge, and reused. The link would
be strongest while the change is in flight and would vanish exactly when the
reviewer needs it, after merge. A worked change would end with no traceable
link and nothing would report that, because the absence looks identical to
"never linked".

**What would flip it:** if branches were immutable and permanent. They are the
opposite.

## 5. The design, RECOMMENDED: a change id minted once, carried by both, resolved by a command

**The identifier.** A `change-id`: an opaque, permanent, non-reused string,
the same shape as the lifecycle identifiers this product's store already
mints. Permanence is the property that matters, because it is the one branches
lack.

**Who mints it.** Whichever product touches the change first, which in the
nine-step loop is the intake step, so usually the sibling. The other adopts
it. **Neither may mint a second one for a change that already has one**, and
that is the invariant a check enforces.

**Where it lives.** A field on each product's own record, in its own store.
Nothing is shared but the string itself. Either product with no `change-id`
set behaves exactly as it does today, which is criterion 1 satisfied by
construction rather than by care.

**How it is created.** One command, taking the id from the other side, and
this is the one-command cost in criterion 4. When a session starts work on an
existing change, it adopts the id. When it starts something new, it mints one.

**How it is checked, which is criterion 3 and the part with teeth.** A
resolver command takes a `change-id` and reports what each side holds: the
session work, its evidence, its fences, and the change's tier, its reviews,
its proof. Three honest outcomes, using the vocabulary already established
here:

- `linked`: both sides hold the id and both records resolve.
- `half-linked`: one side holds it and the other does not. **A stated state,
  named with which side is missing.** This is the common real case, because
  one product is often installed before the other, and it must not read as
  broken.
- `unlinked`: neither. Not an error. Most work is one person's and needs no
  link at all.

**What travels between people.** The handover pack gains the `change-id`, so
the pack stops describing only a session and starts naming the change. That is
the smallest edit that turns the pack from a session artefact into a
collaboration artefact, and D22 already put the pack in the repository where
the receiving person will find it.

### Consequences

- **Two records can drift.** Nothing stops one side being updated and the
  other not. The resolver reports what each holds and does not reconcile them,
  because reconciliation across two independent stores is the shared-database
  problem wearing a different hat.
- **The id is only as good as its adoption.** Somebody must pass it across.
  `half-linked` exists so that failure is visible and countable rather than
  silent.
- **This does nothing across repositories.** Deliberately, again. R3.

### Flip condition

**If in practice the resolver almost always returns `half-linked`, the
one-command adoption is too expensive** and the id should be derived at intake
and pushed rather than pulled, which is a different design.

Second flip: if teams turn out to want one record after all, this becomes a
migration into a shared record and the `change-id` is exactly the key that
migration would need. **Nothing here forecloses R3; it supplies its join key.**

## 6. What needs the founder

1. **Which side mints, when both could?** This design says first-toucher and
   expects that to be intake, but a team could reasonably want the session
   product to always mint.
2. **Does an unlinked change ever get refused?** Recommendation is never,
   because refusing would violate criterion 1.
3. **Does the `change-id` appear in commit messages?** It would make the link
   survive outside both tools entirely, which is the most durable option and
   also the most intrusive.

## 7. Done-check

Complete when a reader can state the two rejected designs and why, the three
resolver outcomes and that the middle one is a normal state, what would flip
it, and what needs deciding. All four present.
