Status: CURRENT. Founder direction, 2026-08-15.

# The chain: human intent to verified reality

This is the north star for everything both products do and how they do it.
It was given by the founder on 2026-08-15 and it is authoritative. Where an
earlier document conflicts, this one wins and the conflict is named here
rather than resolved silently.

    HUMAN INTENT
         |
         v
    DEVELOPMENT METHOD        Claude native | GSD | BMAD | Superpowers
         |
         v
    BROTHERMODE               execution provenance
         |
         v
    CHANGE PASSPORT
         |
         v
    BROTHERSBE                behaviour, business impact, risk, required
         |                    proof, evidence integrity, accountability,
         |                    release readiness, production observation
         v
    HUMAN DECISION
         |
         v
    RELEASE
         |
         v
    VERIFIED REALITY

## What each stage owns, and who may not touch it

HUMAN INTENT. A person wants something. This is the only stage no software
may originate. Everything downstream exists to carry it faithfully or to
report honestly that it could not.

DEVELOPMENT METHOD. How the work gets done: Claude native, GSD, BMAD,
Superpowers, or whatever comes next. DELIBERATELY INTERCHANGEABLE. Neither
product owns a method, competes with one, or requires one. A team that
already has a way of working keeps it. This extends the assurance product's
existing rule (it owns assurance and borrows execution) one level upward:
the method is borrowed too.

BROTHERMODE. Execution provenance: what actually happened while the work was
being done. Who wrote which file, in which session, under which claim, with
which verification run after which edit, and what was left unfinished. Not
process compliance. Not a method. The record of execution as it really
occurred, including the parts that went badly.

CHANGE PASSPORT. The one object that travels from execution to assurance,
and the ONLY interface between the two products. This is the anti-duplication
rule made concrete: one seam, one object, one direction of travel. A passport
carries what was done, by whom, under what claim, with what evidence, and
what the executing side knows it did NOT establish.

BROTHERSBE. Eight concerns, listed by the founder, in his order:

    behaviour               what the software must do under stated conditions
    business impact         what it is worth and what it costs to get wrong
    risk                    how bad failure is, which decides ceremony
    required proof          what must be shown before this may proceed
    evidence integrity      whether the proof is real, current, and traceable
    accountability          who decided, who reviewed, who owns the result
    release readiness       whether this may go, stated as a judgement
    production observation  what it did once it was actually running

HUMAN DECISION. A person decides to release, or not. This node is
UNCONDITIONAL and no automation may remove it, shorten it to a rubber stamp,
or pre-approve it. The system's job is to make the decision cheap and
well-informed, never to make it unnecessary.

RELEASE. The change reaches the world.

VERIFIED REALITY. Whether it actually worked, observed rather than asserted.
This is the terminal state of the chain, and it is deliberately NOT "the gate
went green". A green gate is a claim about proof. Verified reality is a claim
about the world.

## The two rules this chain imposes on everything

RULE ONE, THE HUMAN LOOP IS NEVER OPTIMISED AWAY. Humans stay in the loop at
four points: the intent that starts the chain, any forcing condition where
guessing is the danger, the release decision, and the acceptance that closes
it. A change to either product that removes, bypasses, or silently
pre-answers one of those four is refused, whatever it saves. The system may
make a human decision faster, better informed, or better packaged. It may
never make it disappear.

The mechanism for re-entering the loop mid-flight already exists as of today:
`tools/bm_escalate.py` and `docs/ESCALATION.md`. When the work is stuck, that
tool converts the stuck state into a named decision for a person, with a
recommendation and a default action. It is the chain's back edge to HUMAN
DECISION, and it is the reason "always keep humans in the loop" is a
mechanism here rather than an intention.

RULE TWO, EVERY ITEM OF WORK NAMES ITS STAGE. Backlog items, plans and
proposals name the stage of this chain they serve. An item that cannot name
one goes to the parking lot rather than the backlog, which is the existing
order-of-work law with this chain supplying the objectives it refers to.

## Where the products actually stand against this chain, today

Checked against code read on 2026-08-15, not against intentions.

| Stage | State | What exists |
|---|---|---|
| Human intent | PARTIAL | No clarify or discussion step is enforced anywhere (problem P3). Intent arrives, and nothing records that it was explored. |
| Development method | GOOD | Both products are method-neutral by design, and the assurance side states it as law. |
| Execution provenance | GOOD, with one hole | Claims, fences, sessions, verification after last edit, handover packs. The one-writer control is INERT in the assurance repository (hole H9). |
| Change passport | DOES NOT EXIST | This is the largest structural gap in the chain. See below. |
| Behaviour | SHIPPED 2026-08-15 | The behaviour table, required from tier T1 up, with a check refusing four ways to fake it. |
| Business impact | DOES NOT EXIST | Nothing anywhere records what a change is worth or what getting it wrong costs. |
| Risk | SHIPPED | Tier from five intake answers, and the additive-versus-breaking split landed today. |
| Required proof | SHIPPED | The verification plan, tier-required artifacts, the four hard gates. |
| Evidence integrity | PARTIAL | Evidence binds to a commit, and provenance (who produced it) does not exist yet (problem P6). |
| Accountability | PARTIAL | Approval needs a verified signed trailer; reviewer load is invisible (hole H7). |
| Release readiness | DOES NOT EXIST | There is no readiness judgement. A green gate is being read as one, which is exactly the failure the review's closing finding named. |
| Production observation | DOES NOT EXIST | Nothing is observed after release. No deployed ref, no outcome, no reopen (holes H3, H5). |
| Human decision | PARTIAL | Escalation to a human shipped today. There is no acceptance record and no accepted state (hole H2). |
| Release | NOT OURS | The host does this. Both products stop at the pull request by design. |
| Verified reality | DOES NOT EXIST | Nothing computes whether anything worked. The agreed success measure cannot even be recomputed (hole H1). |

## The convergence worth noticing

Nine holes were found today by walking the lifecycle and asking what has no
tool at all, before this chain arrived. Five of the nine were one hole seen
five times: the system is complete up to the merge and blind after it.

This chain names that same hole from the other direction. Its last four
stages, release readiness, production observation, human decision and
verified reality, are exactly the four that do not exist. The gaps are not
scattered debt. They are the unbuilt half of the founder's own model, and
they were found independently within an hour of each other.

Mapping, so nothing is filed twice:

    H1 measurement           -> verified reality
    H2 acceptance            -> human decision
    H3 deployment binding    -> production observation
    H4 defect intake         -> the return edge, verified reality to intent
    H5 post-merge outcomes   -> verified reality
    H6 discovered work       -> intent re-entering mid-chain
    H7 reviewer load         -> accountability
    H8 duration              -> business impact
    H9 inert fence control   -> execution provenance

## The change passport, defined, because a seam nobody has defined gets built twice

It does not exist yet. Defining it now costs nothing and prevents the two
products from growing two half-versions of it. A passport carries exactly
five things and no more:

1. WHAT WAS DONE: the change identity, its diff range, and the files it
   touched.
2. WHO DID IT: the sessions and agents that wrote, the claims they held, and
   the human accountable.
3. WHAT WAS RUN: the verifications executed after the last edit, with their
   results and where they came from.
4. WHAT WAS NOT ESTABLISHED: the executing side's own honest list of what it
   did not check. This field is mandatory and may not be empty, because a
   passport that claims nothing is unexamined is the lie the whole chain
   exists to prevent.
5. WHERE IT CAME FROM: the method used, named but not judged.

The passport is produced by BrotherMode and consumed by BrotherSBE. It never
travels back. Anything the assurance side needs that the passport does not
carry is a defect in the passport, not a reason for the assurance side to
reach into execution state.

## Relationship to the existing north stars, stated rather than assumed

This chain does not replace the ratified metric. BrotherMode's north star
remains "every serious AI-assisted task ends in a resumable, review-ready,
evidence-backed delivery", measured as Confirmed External Verified Deliveries
per Week, and its ninth condition (not reopened for material rework within
seven days) is already a VERIFIED REALITY test written before this chain
existed. The assurance product's five owned things all sit inside the eight
concerns above.

What the chain adds is the SHAPE: which stage each thing belongs to, that the
method layer is interchangeable, that the passport is the only seam, and that
the chain ends in observed reality rather than in a verdict. Where the older
documents describe outcomes, this one describes the path, and the path is
what a backlog item has to name.

## What is enforced, and what is not, stated plainly

ENFORCED today: nothing in this file. It is a direction document, and a
direction document is not a control.

The nearest thing to enforcement that exists is the order-of-work law, which
says an addition that cannot name its objective goes to the parking lot, and
that law is human discipline as well.

NOT BUILT, and named so it is not mistaken for done: a check that every queued
item names a stage of this chain. Its home is `tools/bm_idle.py`, the module
that already reads and validates `docs/plan/QUEUE.json`, because a second
reader of that file would be a second parser of one format, which this project
has been burned by before. Until that check exists, this rule is discipline.
