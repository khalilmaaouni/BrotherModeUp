Status: CURRENT.

# Integrity-system vision: intake, 2026-08-15

The founder delivered a 2041-line product vision
(BROTHERMODE-INTEGRITY-SYSTEM(1).md, in Downloads; copy it into the repo
before working from it) and ordered its enhancements folded into the long
range plan, adapted for individual contributors and 2 to 15 person
startups, with seamless BrotherMode and BrotherSBE workflow integration as
the end state. This page is the intake and first-pass mapping, written at
the end of a long session; the full adaptation is the NEXT session's first
lane and must not be done from this summary alone: read the source.

## First-pass mapping, this session's read of sections 1 to 28

Already shipped in some form, needs alignment not invention: the thesis
(delivery-control layer; our README already carries "verified delivery
layer" per PRODUCT-DIRECTION.md), resource ownership and enforcement
levels (fences), state integrity across dead sessions (store, ceremony),
transactional handover prepare/verify/adopt/transfer (bm_handover verbs),
receipts (capability_receipts, TK5a/TK11), toolkit as controlled supply
chain (TK1 to TK4 landed), host independence (docs/BITBUCKET.md landed
2026-08-15; GitHub native).

Genuinely NEW, the long-range candidates to size and sequence:

1. Delivery contract as a first-class object with amendments (sections 5,
   11): acceptance criteria bound at start, delivery refused while
   unsatisfied. Nearest existing seam: outcome contract columns (R1.1)
   and definition-of-done.
2. Evidence graph with FRESHNESS (sections 7, 8): evidence linked to the
   exact criterion it proves, going stale when relevant work changes.
   Nearest seam: criterion-linked receipts from TK5a; freshness is new.
3. Risk-adaptive verification tiers LOW to CRITICAL (section 9) and
   adversarial verification (section 10). Nearest seam: PO-5
   falsification briefs; the tiering is new and must obey BM-A1 (no new
   blocking gate without founder decision).
4. Delivery manifest and tamper-evident receipts (sections 12, 13).
   Nearest seam: CHECKSUMS.sha256 and the evidence packet planned in TK6.
5. Azure Repos as a third host (section 26): OVERTAKEN 2026-08-16, the
   founder removed Azure from the target the day after this intake
   (PRODUCT-DIRECTION.md amendment); the dormant page and CI file exist
   and nothing further is scheduled.
6. Public standard and DeliveryBench (sections 27, 28): category-defining
   moves; founder-gated scope decisions.

## The founder's fit constraints, binding on the adaptation

Individual contributors and 2 to 15 person startups: every mechanism must
pass the labour test imported in the the adopter team adaptation (it removes more
typing than it adds, or it gets cut), and the boundary law (measure,
reveal, remove labour; never add an obligation and call it a fix).
Seamless BrotherMode and BrotherSBE integration: BrotherMode governs one
person's session, BrotherSBE governs a change's passage between people;
the delivery contract and evidence graph are the natural shared objects
and must be designed ONCE, not twice; O11 (parity read) is the natural
first step and sits queued.

## Second source document, same evening

The founder delivered a second framework the same night:
docs/vision/STARTUP-10-10-WBS-2026-08-15.md (1876 lines), an
implementation blueprint pairing BrotherMode and BrotherSBE explicitly:
a Fable execution contract with separation of duties, a model routing
policy by risk tier, an agent catalog with permission rules, canonical
shared data objects (Change, Evidence record, Risk finding, Policy
decision), and a twelve-part WBS running from the change contract through
the evidence ledger, risk and policy engines, a provider-neutral VCS
contract with GitHub, Bitbucket and Azure integrations, to a cross-repo
collision graph and human review routing.

First-pass read: this and the integrity-system document describe ONE
program from two angles (the vision and its WBS). The founder's binding
constraint applies doubly: complementarity, never duplication. The
canonical data objects are the exact place the two products must share
one definition (BrotherMode already holds change ownership, receipts and
evidence in schema 20; BrotherSBE holds intake, gates and approvals), so
the adaptation designs those objects ONCE with a named owner per object
and a consumer contract for the sibling. The VCS contract section maps
directly onto docs/BITBUCKET.md's pattern, extended to Azure. The model
routing and agent catalog sections largely restate laws this repository
already enforces (tier per brief, one writer per file); the adaptation
imports only their deltas, never a parallel copy.

## Next session's order

1. Both source documents are under git in docs/vision/ (done 2026-08-15).
2. Read both end to end against docs/plan/FINALIZATION-ROADMAP-2026-08-15.md
   and PRODUCT-DIRECTION.md; PRODUCT-DIRECTION.md is the authority and any
   conflict goes to the founder through question windows, never resolved
   silently.
3. Produce ONE long-range plan amendment covering both: phases 6 plus for
   the roadmap, each new mechanism named with its nearest existing seam,
   its labour test, its owner (BrotherMode or BrotherSBE, never both), and
   the sibling's consumer contract where the object is shared.
4. Founder ratifies through question windows before any build starts.
