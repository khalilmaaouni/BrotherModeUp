# Memory architecture: design, not build

Status: CURRENT

Q1 of `docs/plan/REPLAN-2026-08-12.md`. The R1 tranche's stated deliverable is
"the memory architecture is designed and ratified but not built." This is that
design. **Nothing here is implemented.** It is written so the founder can
reject it cheaply, which is the whole point of designing before building.

---

## 1. The problem, stated from what actually breaks

Not "sessions forget things." That is too vague to design against. Four
specific failures, all observed in this repository's own records:

1. **A fact learned at 23:00 was wrong in the handover written at 22:25.** The
   prior pack said a store checkpoint clears a stale view. It is not the
   checkpoint; any operation that re-renders clears it. The wrong version was
   written down, travelled forward, and cost a session real time chasing it.
2. **A defect described in a handover did not reproduce at all.** A session
   was told to fix something that works. Descriptions decay and nothing marks
   them as stale.
3. **A guard existed for a problem and could not fire.** `_hook_derived_session_id()`
   was written to prevent exactly the lockout that happened four times in one
   night, and it depended on an environment variable nobody sets. **The memory
   of the fix existed; the memory that it does not work did not.**
4. **The same class of mistake recurred across sessions.** Four process rules
   (PO-7 to PO-10) were earned in one night, and at least two of them had
   plausibly been learned before and lost.

The pattern in all four: **the system remembers claims, and does not remember
whether they are still true.** That is the actual design problem, and it is
different from storage.

## 2. What a memory has to be, to fix those

A memory is not a note. It is a claim with three things attached:

- **Its evidence.** The command that produced it and that output. A claim with
  no evidence is a rumour and is stored as one, visibly.
- **Its expiry condition.** Not a date. The observable thing that would make
  it false: a file changing, a test starting to pass, a version moving. A
  claim that cannot state what would falsify it is an opinion, and opinions
  are allowed but are labelled.
- **Its blast radius.** Which files, commands or areas it governs, so
  retrieval can be scoped rather than dumping everything.

Failure 3 above is the argument for the expiry condition specifically. "The
lockout is fixed" was true when written and false by the time it mattered, and
nothing could tell.

## 3. Criteria for choosing between designs

In priority order, because they conflict:

1. **A stale memory must be detectable mechanically**, not by a person
   remembering to re-read it.
2. **Retrieval must be scoped**, or every session pays the cost of everything
   ever learned.
3. **It must survive with no service running.** This product's whole position
   is that your records are files you own.
4. **It must be inspectable by a person** with no tool, because that is the
   fallback when the tool is broken.
5. **Adding a memory must cost near zero** at the moment of learning, or
   nobody does it while tired, which is exactly when the learning happens.

## 4. Alternative A, REJECTED: a semantic index over past sessions

Embed session transcripts and handover packs; retrieve by similarity.

**Why it is attractive:** zero authoring cost, criterion 5 perfectly. Nothing
to write down; it just remembers.

**Why it is rejected:** it fails criterion 1 completely, and criterion 1 is
first for a reason. A similarity index cannot tell a true claim from one that
was true in July. All four observed failures are staleness failures, so this
optimises the one axis that was never the problem while making the real one
worse: it would have retrieved the wrong checkpoint explanation with high
confidence, because it was written confidently. It also fails criterion 3
(needs a model or a service) and criterion 4 (a vector is not inspectable).

**What would flip it:** if staleness were solved separately, this becomes a
good *discovery* layer on top. It is a bad *truth* layer.

## 5. Alternative B, REJECTED: an append-only markdown log read at session start

What largely exists today: session logs, a failures index, handover packs.

**Why it is attractive:** criteria 3 and 4 perfectly, and it is already built.

**Why it is rejected:** it fails criterion 1 and criterion 2 together, and the
failure mode is the one already observed. The log grows without bound, so
session start either reads all of it (unaffordable, and the reason context
runs out) or reads the newest few (which is how a correction written in
August loses to a confident claim written in July). Failure 1 above happened
inside exactly this design.

There is a sharper version of this argument. This repository already contains
an append-only structure that a hook reads as a live registry, and about
twenty-five of its lines carry no readable scope. **Append-only logs decay
into narrative.** Narrative is good for people and useless for a check.

**What would flip it:** nothing at the scale of one person for one week. It is
genuinely fine there, which is why it survived this long.

## 6. The design, RECOMMENDED: typed claims in the existing store, with declared expiry

Memories become rows in the transactional store that already exists, alongside
work records and claims. Not a new subsystem.

**Shape.** Each memory carries: the claim in one sentence; its kind (fact,
rule, defect, limit); the evidence (command plus output, or a commit hash);
its scope (paths, commands or areas); its expiry condition, expressed as a
runnable check; and its state, which is one of `holds`, `stale`, or
`unverifiable`.

**How staleness becomes mechanical, which is the whole point.** The expiry
condition is a command. A sweep runs it and moves the memory to `stale` when
it stops agreeing. `tools/bm_stall.py` already does exactly this shape of
sweep over fences and records, and it is the proof that this is cheap: it
reports findings and names the clearing command beside each. Memory becomes a
third thing that sweep covers. **A memory nothing can falsify is stored as
`unverifiable` and says so at retrieval**, which is the honest version of an
opinion rather than a banned one.

**How retrieval stays scoped.** By the scope field, matched against what the
session is about to touch, the same way `bm_learn.py apply` already matches
rules against a query and records that they were surfaced. That mechanism is
built, tested and in daily use; this reuses it rather than inventing a second
one.

**How authoring stays near-free.** The moment a check runs and its output is
quoted is the moment a memory can be written, because both the evidence and
the expiry condition are already on screen. The founder's tick contract
already forces that output to exist. So the cost is one command at a point
where the work is already done, not a separate act of writing things down.

**How a person reads it with no tool.** The generated view, exactly as
`STATE.md` is generated today: the store is the truth, the markdown is a
rendering. This preserves criterion 4 without reintroducing the append-only
decay of Alternative B, because the rendering is regenerated rather than
appended.

### Consequences, including the ones I do not like

- **The store grows a responsibility it did not have.** It is currently about
  ownership. This makes it about ownership and knowledge. That is a real
  widening and the argument against it is honest: one subsystem with two jobs
  is how subsystems get confusing.
- **Expiry conditions will be written lazily.** Some will be `true`, which is
  worthless. The mitigation is that `unverifiable` is a visible state rather
  than a silent default, so laziness is countable.
- **A sweep that runs commands is a security surface.** Expiry checks are
  arbitrary commands from a store. They must be founder-visible and never run
  in an unattended context without the same brakes as any other unattended
  work.
- **This does nothing for cross-repository memory.** Deliberately. That is R3
  and it needs a migration story.

### Flip condition, stated so this is falsifiable

**If, after one month, more than half of stored memories are `unverifiable`,
this design has failed** and Alternative B is the honest answer, because a
memory system whose distinguishing feature is unused is just a log with
ceremony.

Second flip: if the sweep's runtime exceeds the session-start budget, scope
matching has to move ahead of the sweep, which is a different design.

## 7. What is NOT decided here, and needs the founder

1. **Does a memory ever cross from this product's store into the vault, or are
   they separate for good?** The vault is his and is not per-project; the
   store is per-project and is the product's. Today a fact can live in both,
   which the memory protocol already forbids in principle and nothing enforces.
2. **Does a memory travel between people in the handover pack?** If yes, the
   pack gains a memories file. If no, team knowledge stays oral, which
   contradicts the collaboration objective.
3. **Ratification.** The R1 exit condition is that this is *ratified*, not
   merely written. That is his signature, not mine.

## 8. Done-check for this document

Not a build check, because nothing was built. This document is complete when a
reader can state, without asking: what was rejected and why (two designs,
sections 4 and 5), what would flip the recommendation (section 6), and what
still needs a founder decision (section 7). All three are present.
