# Finishing the adopter team's issues: task plan, assignments, and the start prompt

Status: CURRENT. Written 2026-08-17. Mark HISTORICAL when the open items below
close or a later plan supersedes it.

NAMING: this page uses ROLES only (the adopter team, the analyst lead, the QC
lead). Both product repositories are PUBLIC. No client name, no reviewer's
personal name, and no company context may appear in any file, path, commit
subject, or artifact produced from this plan. The only name permitted is the
owner's own.

## TASK 0, BLOCKING EVERYTHING PUBLIC: the history decision

The working tree of this repository was scrubbed clean of the adopter team's
name, six reviewers' personal names, an internal change name and a third party
product name on 2026-08-17 (commits 38c859b and merge 97e5fd3). Verified: 0
content hits and 0 path hits, whole-word, across tracked and untracked files,
with the English word "hurry" deliberately preserved as proof the scan did not
overreach.

GIT HISTORY IS STILL EXPOSED. Roughly 196 further occurrences live in the
objects of a PUBLIC repository and are readable with `git log` on any clone.
Deleting a file does not remove it. The owner's standing rule says the route for
history is a CLEAN EXTRACTION of the shippable part into a fresh repository,
never a scrub of this one, because a rewrite leaves the deleted commits
resolvable on the machine that performed it.

THE FIRST SESSION DOES NOT DECIDE THIS. It ASKS, in one question window, and
does not push anything client-adjacent until answered. Options to put to the
owner: leave history and accept it, extract the shippable engine into a fresh
public repository and make these private, or rewrite history knowing the vault
records that route as having failed here before
([[a-clone-that-still-holds-the-objects-you-deleted]]).

## The open items, thirteen of them

Extracted from `docs/plan/ADOPTER-TEAM-PROBLEMS-AND-SOLUTIONS-2026-08-15.md`
(the primary source, cited below as PS), cross-checked against
`docs/plan/DELIVERY-VS-FEEDBACK-2026-08-16.md` and
`docs/plan/PROBLEMS-2026-08-16.md`.

RE-EXTRACT BEFORE TRUSTING THIS TABLE. It was produced by one reader pass and
the statuses were true at 2026-08-17. A session starting later runs the same
extraction again rather than believing a list it did not verify.

| id | what the adopter team raised | tool | size | north star stage |
|---|---|---|---|---|
| ship-to-reviewers | they reviewed a build generations behind source; the two heaviest fixes exist in source and not on the public remote | SBE | T1 | release |
| p14-sol2-green-scope | a green gate under-represents what was not examined; unexamined classes should print as NO-DATA by name | SBE | T1 | evidence integrity |
| p6-receipt-provenance | a hand-written success receipt passes as well as a real one; nothing records where evidence came from | SBE | T1 | evidence integrity |
| p11-prove-rename | the step named PROVE checks paperwork completeness, not the work, and they assumed otherwise | SBE | T1 | release readiness |
| p2-ba-guide-wrong | the guide misdescribes how their analysts work: they hand over a full specification, not conversations | SBE | T1 | human intent |
| p5-stale-status | status returned stale output after clearing a session; NOT REPRODUCED | SBE | T1 | unclear |
| escalation-finish | stuck detection is built here but one registration is missing and it writes founder text into its ledger | both | T1 here, T2 to port | execution provenance |
| p3-clarify-enforcement | discussion before planning is an instruction, not a control; nothing refuses or flags its absence | SBE | T2 | human intent into intake |
| p7-owed-checks | evidence with one check passes as green as evidence with all of them | SBE | T2 | required proof |
| p4-decisions-harvest | the decisions table stays empty while decisions land in commits and notes | SBE | T2 | accountability |
| p1-windows-first-run | setup fails for a non-developer on Windows; no installer puts the command on PATH | both | T2 | chain entry |
| p12-bitbucket-sbe-leg | they work on Bitbucket; the sibling's approval and pipeline steps are still worded for one host | SBE | T2 | the seam, release |
| p10-p13-requirement-drift | nothing handles a requirement changing: no design version, no supersession, no staleness clock | both | T3 | evidence integrity |

ALREADY FINALIZED, do not redo: p8-tier-split (4912bd8), p9-behaviour-table and
p14-testkit (in source, awaiting ship-to-reviewers), the BrotherMode half of
p12, p5's next-command half, p6's commit binding, escalation core.

## Assignments, by tier and model

The rule this follows: strongest tier for architecture, adversarial review,
judging and synthesis; middle tier for scoped implementation from a settled
spec; cheap tier for mechanical bulk with a deterministic done check. Every
brief stands alone, names its exact read and write paths, and ends with one
runnable done check. Never two writers on one file.

| lane | tasks | agent type | model | why this tier |
|---|---|---|---|---|
| A, the honesty seam | p14-sol2-green-scope, p6-receipt-provenance, p7-owed-checks | builder | sonnet | the shape is settled in PS; these are scoped edits to sbe_gate.py with failing-first tests |
| B, intent and control | p3-clarify-enforcement, p4-decisions-harvest | navigator to design, then builder to implement | fable to design, sonnet to build | both introduce NEW STATE and a refusal path; getting the state model wrong is expensive, the code after it is not |
| C, cross platform | p1-windows-first-run, p12-bitbucket-sbe-leg | builder | sonnet | port an existing pattern (docs/BITBUCKET.md) rather than invent one |
| D, the hard one | p10-p13-requirement-drift | navigator only, first | fable | a staleness clock, supersession links and an index is a data model decision; no code until the model is written and reviewed |
| E, documentation | p2-ba-guide-wrong, p11-prove-rename | fast-worker | haiku | wording changes against a stated target, mechanically checkable |
| F, adversarial | every lane's output before it merges | reviewer | fable | briefed to REFUTE: run the attack, report what broke, or state COULD NOT BREAK |
| G, waiting on people | p5-stale-status, p2's sign-off, p12's certification | none, owner action | n/a | needs exact repro steps from a reviewer, the analyst lead's written agreement, and a workspace only the owner can unblock |

Sequencing: lane A first (three T1 items, all in one file, highest value per
hour and they close the honesty complaint the adopter team led with). Lanes B and
C in parallel, at most two lanes live at once. Lane D designs while A merges and
does not write code in this session. Lane E any time. Lane F gates every merge.

## The collaboration seam, which this work must not break

Per `docs/NORTH-STAR-CHAIN.md`: human intent, then whichever development method
the team already uses, then BrotherMode for EXECUTION PROVENANCE, then the CHANGE
PASSPORT as the only seam between the two products, then the sibling's eight
concerns, then HUMAN DECISION, release, and verified reality. The chain ends in
observed reality, never in a green verdict.

Two consequences for this plan. Every task above names the stage it serves, and a
task that cannot is parked rather than started. And the four points where a person
decides (intent, a forcing condition, release, acceptance) may not be removed,
bypassed or pre-answered by anything built here: p3 and p7 in particular add
refusals, and a refusal that cannot be overridden by a named human with a
recorded reason is a defect, not a feature.

## Known limits this plan inherits

- Both repositories are PUBLIC and their history carries client names. Task 0.
- Linux has NO automatic coverage. Deferred to pre-release by owner decision of
  2026-08-17; a Lima ephemeral appliance is the chosen route and is not built.
  Windows is a written protocol a person follows, `docs/WINDOWS-CHECK.md`.
- The Bitbucket certification leg is BLOCKED: the workspace is read-only past its
  user limit and only the owner can free a seat. Not retryable.
- BrotherSBE main was frozen by a repository ruleset requiring five status checks
  that can never report. The corrected payload is at
  `~/Documents/BrotherArchive/rulesets/brothersbe-main-protection.FIXED.json`
  and applying it is an owner action.

## THE START PROMPT, paste this into a new session

    /brothermode
    
    Priority: finish the adopter team's outstanding issues on BrotherMode and
    BrotherSBE. Read this pack first, in this order: 06-CLOSE-REPORT.md, then
    07-THE-PLAN-AND-START-PROMPT.md, then 01-HANDOVER.md. Acknowledge what you
    adopt before starting.
    
    Both repositories are PUBLIC. No client name, no reviewer's personal name and
    no company context may appear in any file, path, commit subject or artifact.
    Use roles. The working tree was scrubbed on 2026-08-17; git history was NOT,
    and that is task 0.
    
    TASK 0, before any push: ask me the history question in the plan's task 0,
    through the question UI, one window. Do not push anything client-adjacent
    until I answer.
    
    Then re-extract the open issues yourself from
    docs/plan/ADOPTER-TEAM-PROBLEMS-AND-SOLUTIONS-2026-08-15.md rather than
    trusting the plan's table, and tell me where it disagrees.
    
    Then work lane A (the three honesty-seam items in the sibling's gate tool),
    using the tier assignments in the plan. Fable designs and reviews, sonnet
    implements, haiku does documentation bulk. Every lane's output goes through an
    adversarial reviewer briefed to REFUTE before it merges.
    
    Rules that cost us before, do not relearn them: a green from a script you
    wrote is worthless until you have tried to make it lie; git push --dry-run
    cannot see branch protection or rulesets; check load average before any
    battery, and both runners now refuse above four times the core count; never
    write a tracked file while a battery runs; a killed run is not a verdict.
    
    Deliver the progress page in front of me at every closed loop, and one zip at
    the close, never loose files.
