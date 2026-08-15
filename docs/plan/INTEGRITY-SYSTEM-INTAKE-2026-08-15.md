Status: CURRENT.

# Integrity-system vision: intake, 2026-08-15

The founder delivered a 2041-line product vision
(BROTHERMODE-INTEGRITY-SYSTEM(1).md, in Downloads; copy it into the repo
before working from it) and ordered its enhancements folded into the long
range plan, adapted for individual contributors and 12 to 15 person
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
5. Azure Repos as a third host (section 26): extend the Bitbucket page's
   pattern; engine is already host-agnostic.
6. Public standard and DeliveryBench (sections 27, 28): category-defining
   moves; founder-gated scope decisions.

## The founder's fit constraints, binding on the adaptation

Individual contributors and 12 to 15 person startups: every mechanism must
pass the labour test imported in the the adopter team adaptation (it removes more
typing than it adds, or it gets cut), and the boundary law (measure,
reveal, remove labour; never add an obligation and call it a fix).
Seamless BrotherMode and BrotherSBE integration: BrotherMode governs one
person's session, BrotherSBE governs a change's passage between people;
the delivery contract and evidence graph are the natural shared objects
and must be designed ONCE, not twice; O11 (parity read) is the natural
first step and sits queued.

## Next session's order

1. Copy the source document into docs/vision/ under git.
2. Read it end to end against docs/plan/FINALIZATION-ROADMAP-2026-08-15.md
   and PRODUCT-DIRECTION.md; PRODUCT-DIRECTION.md is the authority and any
   conflict goes to the founder through question windows, never resolved
   silently.
3. Produce the long-range plan amendment: phases 6 plus for the roadmap,
   each new mechanism named with its nearest existing seam, its labour
   test, and its BrotherSBE shared-object decision.
4. Founder ratifies through question windows before any build starts.
