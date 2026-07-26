# Lessons, organized by defect class

Read this BEFORE writing code, not after. Organized by CLASS, never by incident,
because the most expensive recurring failure in this project is fixing the reported
instance and leaving the class alive to reappear in a new costume.

Format per class: what it looks like, why it happens (the mechanism, not the
story), the mechanical stop that now catches it, and dated appearances newest
first, capped at five. A sixth appearance replaces the oldest and increments the
counter, so frequency survives without the file growing forever. The cap exists
because an uncapped lessons file stops being read, which is the documented failure
mode of unbounded reflection buffers.

Status is OPEN (no mechanical stop yet) or CLOSED (a stop exists and has been
calibrated by reinjecting the defect and watching the right check fail).

---

## Success reported on a write that was never checked

STATUS: CLOSED (5 appearances)

What it looks like: an operation returns success, prints a confident message, and
the thing it claimed to do did not happen. The caller proceeds on a lie.

Why it happens: a return value is discarded, or a loop skips an entry it cannot
handle. The skip version is the dangerous one, because the rule "propagate what the
write returned" is blind to it: nothing was returned, an item was simply passed
over.

Mechanical stop: every loop that turns caller input into stored data must be TOTAL
(each entry either becomes stored data or raises), enforced by structural tests
asserting the coercion function is total and that no silent continue exists in the
decision loop. Ownership operations propagate write results.

Appearances:
- 2026-07-26 V2 claim() silently dropped any non-string file entry (a Path object
  being the obvious caller mistake) and returned a success record holding nothing;
  the next writer was then granted the file it was meant to fence.
- 2026-07-26 the same shape in checkpoint's decisions loop, found by auditing the
  class rather than the reported instance.
- 2026-07-25 V1 adopt ignored all three of its writes, so with an unwritable state
  file the handover never landed, the record was closed so drain would never see
  it, and the command printed that nothing was orphaned.
- 2026-07-24 two earlier V1 instances (registry save, telemetry append).

---

## Fix the instance, leave the class

STATUS: CLOSED (4 appearances)

What it looks like: a defect is fixed exactly where it was reported. The identical
defect in a sibling field, a sibling path, or a sibling call site ships untouched
and is found one round later at full cost.

Why it happens: the report names an instance, and a fix that satisfies the report
feels complete. Nobody asked what else has this shape.

Mechanical stop: every fix ends with a sweep over the whole class plus a STRUCTURAL
test that enumerates the class from the code or schema itself, so the next member
joins the test automatically instead of relying on memory.

Appearances:
- 2026-07-26 the not-supplied-versus-empty rule was applied to file claims and left
  open for the objective, which a later update then silently erased.
- 2026-07-26 redaction was fixed for the fields someone listed, leaving notes,
  evidence, command and owner in cleartext; fixed properly by inverting to
  default-deny with a test that reads the schema itself.
- 2026-07-26 the containment check covered the directory but not the file inside
  it, then not the hardlink either.
- 2026-07-24 the four cross-cutting concerns (locking, redaction, durable writes,
  handover delivery) each diverged per call site before being unified.

---

## The verifier was itself unverified

STATUS: CLOSED (3 appearances)

What it looks like: a check, test, or review harness produces confident, detailed
output that is worthless, because the thing it examined was stale, mocked, or not
the product at all.

Why it happens: verification infrastructure is treated as scaffolding rather than
as code, so it gets none of the discipline the product gets.

Mechanical stop: every dispatched review brief carries a FRESHNESS ASSERTION the
agent must run and quote back before testing anything. Generated prompts are
dry-run before a fleet is spent on them. A reinjection test must patch the PRODUCT
symbol, never a local copy of the old code.

Appearances:
- 2026-07-26 fifteen tests named as calibrated defined their own copy of the
  pre-fix function and asserted the copy misbehaved, so none could fail from a
  regression in shipped code. They inflated the calibrated count while protecting
  nothing.
- 2026-07-26 a four-agent review fleet spent a full round on a sandbox three
  commits stale, because a reused directory made the copy nest inside the old one.
  Detected only because the agents quoted a test count that did not match reality.
- 2026-07-26 a test asserting the quarantine directory exists passed while
  mutations that DELETED the damaged data survived, because the directory is
  created before anything is moved into it.

---

## A claim of health that nothing checked

STATUS: CLOSED (3 appearances)

What it looks like: the tool tells the founder everything is fine at the exact
moment it is not, because the reassuring message is printed unconditionally rather
than earned by a check.

Why it happens: the message is written at the call site of the happy path, and the
failure path is somewhere else.

Mechanical stop: the word healthy may only be printed when a store was opened,
read, and found consistent with no unacknowledged quarantine. Safety claims print
only when a receipt proves the thing they claim.

Appearances:
- 2026-07-26 after a quarantine, the next health check silently created a fresh
  empty store and reported healthy, seconds after every record was lost.
- 2026-07-26 a read-only diagnostic in an uninitialized directory printed healthy
  and created the database it claimed to be inspecting.
- 2026-07-25 the compaction hint printed that files were autosaved without checking
  that any snapshot existed.

---

## Escaping a grammar instead of deleting it

STATUS: CLOSED (2 appearances)

What it looks like: a string is handed to a subsystem that treats certain
characters as syntax, and the fix is to escape one more character. The next
unescaped character is a new bug of the same family.

Why it happens: escaping addresses the symptom at the boundary; the decision to use
a grammar at all is what created the family.

Mechanical stop: prefer an interface with no grammar. Plain path plus a read-only
flag instead of a URI. Directory listing plus prefix match instead of a glob.

Appearances:
- 2026-07-26 a percent sign in a project path made every read-only command open a
  DIFFERENT project's database and report it healthy.
- 2026-07-26 brackets in a project path made an outstanding data-loss quarantine
  invisible to the guard that exists to catch it.

---

## Silent repair of damaged state

STATUS: OPEN (1 appearance, fix contracted in round 8)

What it looks like: damaged state is quietly reconstructed as empty and reported as
normal, so the loss is invisible and the guarantees built on that state evaporate.

Why it happens: create-if-missing semantics cannot distinguish never-existed from
was-destroyed, and a version stamp gets read but never compared.

Mechanical stop: PENDING. Contracted: run schema creation only when the file did
not exist, verify every expected table and the schema version on an existing store,
quarantine on mismatch.

Appearances:
- 2026-07-26 dropping one table caused it to be rebuilt empty, after which two
  sessions fenced the same file and the health check reported healthy.

---

## Trusting the file you are about to rewrite

STATUS: CLOSED (1 appearance)

What it looks like: a generated file is rewritten based on markers inside it, and a
human edit to those markers causes the human's own writing to be destroyed.

Why it happens: the injection guard was aimed at content arriving from the system,
while content already in the file was trusted.

Mechanical stop: refuse to rewrite a file whose marker structure is not exactly
what was written; back up before any rewrite that would remove human bytes.

Appearances:
- 2026-07-26 deleting one marker line and adding personal notes caused every byte
  of those notes to be destroyed on the second render, with no warning and no
  backup.

---

## Concurrency assumed rather than enforced

STATUS: CLOSED (2 appearances)

What it looks like: a guarantee holds on the path someone tested and is bypassable
through a second door nobody guarded.

Why it happens: the check lives at one call site instead of in a primitive that all
paths must pass through.

Mechanical stop: one admission function called by every path that can make a record
active, with a structural test asserting it stays single and that both callers use
it.

Appearances:
- 2026-07-26 resume walked straight over another session's fence, so the store
  created the overlap its own verifier then reported.
- 2026-07-26 an empty session identifier matched another empty one, letting an
  unrelated process silently seize an active fence through the command line.

---

## Process lessons (not code defects)

- Adversarial reviewers verify what you point them at. Two of the worst defects in
  this build were found by wandering, not by the fleet: chasing an ugly warning,
  and checking exit codes nobody asked about. Attention coverage is not code
  coverage.
- An independent code review found a Critical that six adversarial rounds missed,
  because it was aimed at the contract and the architecture rather than at
  execution edges. Different aim finds different defects; running both is not
  redundancy.
- Convergence is measurable and worth tracking: gate defects per round ran 9, then
  4, then 2, then 2, with findings narrowing from structural to injection edges.
  A round that finds nothing new is only meaningful if the previous rounds found
  something real.
- A specification written by the orchestrator can itself be the defect. Two items
  in this build were my authoring errors, not implementation errors, and both were
  found only because reviewers were explicitly told the spec might be wrong.
