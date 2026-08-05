Document status: CURRENT Fable review, 2026-08-05. Governs how the MirrorForge
program (archived at docs/evidence/2026-08-05-mirrorforge-source-program.md,
SHA256 7264b5ba...8f074c) is harmonized with the in-flight absolute-lead
program. Founder directive 2026-08-05: harmonize with Fable planning and
judgement; founder pre-sleep answers bind night scope.

# Fable review: harmonizing MirrorForge with the running program

## Verdict

ADOPT AS THE STRATEGIC MAP, EXECUTE INCREMENTALLY. MirrorForge is accepted as
the direction: transactional execution, typed coordination, evidence-typed
research, calibrated simulation, offline workflow search. It is NOT started as
a second parallel program tonight. Its early loops are folded into the train
that is already moving, because the two programs overlap more than the source
document knows.

## The fact the source document is missing

MirrorForge was written against main at 4d79b77 and states (register BM-A04,
BM-A07, BM-A05, section 25 L03) that BrotherMode has no durable work-unit
state machine, no leases, no controller. The working tree ALREADY carries L03:
schema 15, controller run and unit and dispatch tables, a controller engine
(tools/bm_controller.py) with fences claimed before dispatch, per-unit gate
checks against the signed schema-14 contract, checkpointing, an E4
killed-and-resumed end-to-end fixture, and 45 behavioral tests. Tonight's
refutation round 2 (evidence/L03/REFUTATION-2-fixes.md) is closing exactly the
class MirrorForge names Critical in BM-A02: authorization check and effect are
not atomic. The F2 fixes land single-revision dispatch stamping and
containment (not overlap) path authorization.

Consequence: MirrorForge's L00 baseline table is stale on arrival. Its
register rows BM-A01, BM-A02, BM-A04 are partially or fully closed by the L03
train; BM-A29 (capability register lag) is real and cheap; the rest stand.

## Loop mapping (MirrorForge number to running program)

| MirrorForge | Running program | Disposition |
|---|---|---|
| L00 freeze baseline | This review plus the L03 landing evidence | CLOSED by this file once L03 lands; the frozen baseline is the landed SHA, not 4d79b77 |
| L01 product truth, capability states | Absolute-lead identity contract (bdfab45, fc6486d) | FOLD: one unit in the L04 train updates capabilities.status.json for the autonomy contract and controller (BM-A29) |
| L02 event ledger | Not built | FOLD into L04 train as its own fenced unit: append-only controller_events table, additive schema step, replay test |
| L03 U2 controller, transactional graph | STAGED L03 plus tonight's fix rounds | IN FLIGHT tonight; lands first |
| L04 mailboxes, leases, adoption | Store fences and adoption exist; typed mailboxes do not | DEFER code; the store's fence, adopt, and handover lanes already carry the safety half; mailboxes join the 2.1 design review |
| L05 dependency waves | Controller waves exist (select_ready_units); read and write set scheduling partial | DEFER refinement to 2.1 |
| L06 to L15 (ForgeGraph, quorum, WorldLab, tournament, debate, mutation studio, router, sizing, ForgeLab) | Not built | FOUNDER DAYLIGHT REVIEW: each needs scope, spend, and product decisions the founder has not yet answered; several import research machinery that must not enter the small-core toolchain without an explicit decision |
| L16 Founder Mode integration | Handover L04 (founder mode, IC mode, watchdog) | THIS IS THE SAME LOOP; the running program's L04 proceeds tonight per the founder's answer, and MirrorForge's founder-surface requirements join its spec |
| L17 benchmark | Handover L17 | UNCHANGED, later |
| L18 external pilots | Handover L18 | UNCHANGED, the honest blocker on any leadership claim |

## What executes tonight, in order

1. L03-FIX round 3 (in flight): fix writer closing REFUTATION-2's eight
   reproduced breaks, then a FRESH refuter; loop until STANDS (founder
   pre-authorized the loop).
2. L03 landing train: full gate, manifest last, commit to main, GitHub
   Desktop push, CI read. One branch stays the law.
3. L04 train, scoped: founder mode and IC mode surfaces per the handover,
   PLUS the two folded MirrorForge units (BM-A29 capability truth, event
   ledger) where they fit without bloating the train, PLUS the watchdog as a
   shipped feature, ON BY DEFAULT activating only after the setup consent
   gate (founder answer 2026-08-05, reconciliation stated in chat).

## What is refused or corrected in the source program

- Schema numbering: section 20 proposes schema 15 to 17; schema 15 is TAKEN
  by the landed controller tables. MirrorForge additions start at 16.
- Loop numbering: MirrorForge L-numbers collide with the handover's; the
  running program's numbering governs the evidence tree; MirrorForge numbers
  appear only with the MF- prefix from now on.
- "Meter tool calls mechanically" (BM-A03): correct goal, but the mechanism
  must not add a daemon; it joins the L04 design space, not tonight.
- Nothing in the source document waives any founder gate, and its own
  section 1 says so; the five safety floors and the signed contract remain
  above every MirrorForge component.

## Non-negotiables carried forward unchanged

One store, one canonical integrator, one writer per file, simulations never
become facts, majority agreement is never proof, validators do not edit,
workflow search cannot touch safety operators, score changes require retained
evidence, no leadership claim before MF-L17 and L18 evidence exists.
