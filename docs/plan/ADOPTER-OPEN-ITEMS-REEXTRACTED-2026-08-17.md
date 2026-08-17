Status: CURRENT. Written 2026-08-17. Supersedes the thirteen-item table in
`docs/handover/2026-08-17-adopter-feedback-finish/07-THE-PLAN-AND-START-PROMPT.md`
for the purpose of counting what is open. That plan's LANE and TIER assignments
still stand except where noted below.

# The adopter team's open items, re-extracted from the primary source

NAMING: both product repositories are PUBLIC. This page uses ROLES only (the
adopter team, the analyst lead, the engineering lead, the delivery lead, the QC
lead, the non-developer reviewer, the senior reviewer). No client name, no
reviewer's personal name and no company context appears here or in anything
produced from it.

Primary source: `docs/plan/ADOPTER-TEAM-PROBLEMS-AND-SOLUTIONS-2026-08-15.md`
(cited as PS with a line number). Re-extracted by a second reader on 2026-08-17
because the plan's own table carried the instruction "RE-EXTRACT BEFORE TRUSTING
THIS TABLE". Every status line below was checked against code read today, with
the command quoted. Where a claim could not be checked it says so.

## Why this page exists: the plan counted thirteen, the source carries more

The plan's table covered only the RAISED problems, P1 to P14. The same source
document then runs its own gap hunt and produces nine further findings, H1 to
H9, each with a named owner, a smallest close and a runnable check (PS 709 to
818). None was in the plan's table. PS 709 states the reason it matters: the
fourteen "share one weakness: every one was RAISED", which makes the list a good
sample of the visible failures and a poor sample of the silent ones.

Count: 13 in the plan, plus 9 H-findings, plus one half of P5 the plan dropped,
is 23. Two of the nine (H2, H6) sit adjacent to items already in the table and
are not covered by them.

## The five disagreements with the plan's table

D-A. THE NINE H-FINDINGS ARE MISSING ENTIRELY. Listed below with owners.

D-B. THE SEQUENCING CONTRADICTS THE SOURCE'S OWN ORDER. PS 990 makes the H1
baseline item 0, "before anything else lands", because "this is minutes of work
and it is the only thing here that cannot be done later". The plan sequences
lane A first and never schedules H1. PARTLY MOOT ON INSPECTION: the five
baseline VALUES are already recorded at PS 65 (41 waiting on development, 22 on
test resource, 23 on the QC lead, 11 in Testing, 48 with a TBD end date), so the
before-picture is on record. What is missing is the ability to RECOMPUTE them,
which needs a tracker export the owner must supply. Reclassified from urgent to
BLOCKED ON OWNER, and it is an ask rather than a task.

D-C. H9 IS A LIVE CONTROL FAILURE AND WORSE THAN WRITTEN. PS 801 says the
sibling's one-writer hook refuses to enforce "about twenty times in a row".
Asked directly on 2026-08-17, in the sibling repository:

    python3 tools/sbe_fence_hook.py fences | grep -c "no readable"
    35

So BrotherSBE's single-writer protection enforces nothing in its own tree, while
its STATE.md reads as though 35 writers hold claims. Every line is a legacy
fence from July. The hook fails open by design, which is correct; the registry
has rotted. PS 818 records that this was found by ASKING the control rather than
grepping for fences, and that a grep would have returned the opposite
conclusion.

D-D. THE PLAN CONTRADICTS ITSELF ON LANE A's SIZE. Its table sizes
`p7-owed-checks` T2; its sequencing paragraph calls lane A "three T1 items, all
in one file". Checked: the reverse direction is absent from `tools/sbe_gate.py`,
and adding it means the gate must begin reading artifact 08's Proof column,
which is new reading rather than an edit. T2 is the honest size. Lane A is two
T1 items and one T2, plus a precondition (below).

D-E. P5 IS TWO ITEMS AND THE PLAN CARRIES ONLY THE BLOCKED HALF. Parking
`p5-stale-status` as NOT REPRODUCED pending a reviewer's exact steps is correct
(PS 256). P5's other half is separate, unblocked and small: a wall of text on
return to an old session, fixed by a short form default with the long form
behind an explicit flag, which PS 265 notes is "BrotherMode's own status-view
rule, already written, not yet applied to the sibling". Checked:
`src/brothersbe/status.py` exists and no `--long`, `--short` or `--brief` flag
exists anywhere in the sibling's status path. Added below as
`p5-wall-of-text`.

## Where the plan is right and the source is stale

THE ESCALATION REGISTRATIONS. The source says two contradictory things: PS 945
claims "four registrations out of six", PS 1003 claims the registration "is NOT
applied" at all. The plan says one registration is missing, and the plan is
correct. All six deltas listed at the end of `docs/ESCALATION.md` were checked
individually on 2026-08-17:

    tools/write_sites.json      "tools/bm_escalate.py": 3   APPLIED
    tools/bm_effects.py         REGISTRY entry              ABSENT
    pyproject.toml              module list                 APPLIED
    .github/workflows/tests.yml test invocation             APPLIED
    tools/test_all.py           SUITES entry                APPLIED
    CHECKSUMS.sha256            regenerated                 APPLIED

The missing one is `tools/bm_effects.py`. No suite goes red over it for the
reason PS 946 gives: the effects registry validates the entries it HAS, so an
undeclared module is silent rather than failing.

## Two ratified amendments the plan's table drops

Both change what may be shipped, so they are preconditions rather than notes.

D2 (PS 952). P3's refusal ships BEHIND AN ESTATE SWITCH, defaulting to report,
because the sibling's ratified direction is paved road, not forced road, and the
pipeline reports rather than blocks. The plan's table says only that nothing
flags its absence, and briefs lane B to add a refusal.

D4 (PS 969). None of P3's gate, P6's strict mode or P7's failure may ship
without an exception path carrying an OWNER and an EXPIRY DATE. The plan's prose
gets the human-override half and drops the expiry.

D4 IS A PRECONDITION ON TWO OF LANE A's THREE ITEMS, and it is nearly satisfied
by reuse rather than invention. `.sbe-exempt` already exists and is already
hardened (a zero-byte file no longer waives everything, `tools/sbe_design.py:23`
and `:3031`), and `parse_exemption` at `tools/sbe_design.py:3022` accepts
`checks:` and `reason:`. It carries no owner and no expiry. So the precondition
is two fields on one existing parser, serving all three new refusals at once,
rather than three separate exception mechanisms. Filed below as `A0-exception-
owner-expiry`.

## The open items

Size is the source's own tier vocabulary. Stage is the north star stage from
`docs/NORTH-STAR-CHAIN.md`; an item that cannot name one is parked rather than
started.

### Carried from the plan's table, unchanged

| id | tool | size | stage | evidence it is open |
|---|---|---|---|---|
| ship-to-reviewers | SBE | T1 | release | PS 39, the public tag carries the version string and neither of the two answers; needs a push and a new number, both owner decisions |
| p14-sol2-green-scope | SBE | T1 | evidence integrity | no unexamined-class reporting in `tools/sbe_gate.py` (grep for unexamined, regression, cross-device: no hits) |
| p6-receipt-provenance | SBE | T1 | evidence integrity | no provenance, producer or run-url field in `tools/sbe_gate.py`; commit binding exists, origin does not |
| p11-prove-rename | SBE | T1 | release readiness | PS 496, documentation both halves |
| p2-ba-guide-wrong | SBE | T1 | human intent | PS 131; close needs the analyst lead's written agreement |
| escalation-finish | both | T1 here, T2 to port | execution provenance | one registration absent, `tools/bm_effects.py` |
| p3-clarify-enforcement | SBE | T2 | human intent into intake | PS 163, nothing outside scratch worktrees; SHIPS BEHIND AN ESTATE SWITCH per D2 |
| p7-owed-checks | SBE | T2 (not T1) | required proof | reverse direction absent from `tools/sbe_gate.py`; forward direction landed 2026-08-15 |
| p4-decisions-harvest | SBE | T2 | accountability | PS 205, the table is empty while decisions land in commits |
| p1-windows-first-run | both | T2 | chain entry | PS 92, no installer puts the command on PATH |
| p12-bitbucket-sbe-leg | SBE | T2 | the seam, release | PS 526, sibling approval and pipeline steps still worded for one host |
| p10-p13-requirement-drift | both | T3 | evidence integrity | PS 456, no design version, no supersession link, no staleness clock |

### Parked on a person, not startable here

| id | tool | why it is parked |
|---|---|---|
| p5-stale-status | SBE | NOT REPRODUCED; needs one reviewer's exact commands and both status outputs, then a re-test on the current version |
| p2-sign-off | SBE | the analyst lead's written agreement to the revised page |
| p12-certification | SBE | the test workspace is read-only past its user limit; BLOCKED, not retryable, and only the owner can free a seat |
| H1-queue-baseline | reveal only | needs a tracker export; the five values are already recorded at PS 65 |

### Added by this re-extraction

| id | tool | size | stage | what it is |
|---|---|---|---|---|
| A0-exception-owner-expiry | SBE | T1 | required proof | owner and expiry on `.sbe-exempt`, satisfying D4 for all three new refusals at once; precondition on p6 and p7 |
| p5-wall-of-text | SBE | T1 | human intent | short form default, long form behind a flag, porting the parent's status-view rule to the sibling |
| H2-accepted-state | SBE | T2 | verified reality | no acceptance record, no accepting party, no status line; the chain ends at a green gate and a merge |
| H3-deployed-ref-drift | SBE | T2 | verified reality | evidence binds to a commit, never to what is running; this is how the review happened against a build generations behind, and PS 51 says it produced every error in that document |
| H4-defect-origin | SBE | T2 | human intent | intake has no origin field, so a bug fix must be described as new work and carries no link to the behaviour that failed |
| H5-post-merge-outcome | SBE | T2 | verified reality | no reopen, rollback, escaped defect or emergency fix recorded against the change that caused it, so the tier split ships with no way to measure whether it classifies better |
| H6-requirement-found-in-build | SBE | T2 | evidence integrity | a behaviour row added after a sheet was generated leaves that sheet one case short with nothing saying so; the opposite direction from P10 |
| H7-reviewer-concentration | reveal only | T1 | accountability | the reviewer route selects by capability and prints no count of what that person already holds |
| H8-opened-closed-pair | SBE | T1 | release readiness | no duration recorded for any tier, so the whole tier-cost argument has no measurement on either side |
| H9-fence-registry-rot | SBE | T1 | execution provenance | 35 unenforceable fence lines; the one-writer control protects nothing in its own tree. Measured above |

## The pattern worth keeping in front of the owner

PS 830 names it and it is the reason the nine H-findings are not a tidy-up list:
H1, H2, H3, H5 and H8 are one hole seen five times. The system is complete up to
the merge and blind after it. Everything it knows is about whether a change was
PROVEN; almost nothing it knows is about whether the change WORKED. The north
star ends in observed reality, so that blindness sits exactly where the north
star lives.

## What was already finalized, do not redo

p8-tier-split (`4912bd8`), p9-behaviour-table and p14-testkit (in source,
awaiting ship-to-reviewers), the BrotherMode half of p12, p5's next-command
half, p6's commit binding, p7's forward direction, and the escalation core
(`tools/bm_escalate.py`, its tests, and five of six registrations).
