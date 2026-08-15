Status: LIVE. Written 2026-08-16 during an unattended overnight run, founder
asleep, hard stop 07:00 JST. Read this before touching either repository.
No em or en dashes.

# Handover: the north star push, successor session

## The one line

BrotherModeUp's work is committed and pushed. The open work is in the SIBLING
repository: BrotherSBE pull request 48 is blocked by six red checks that
reduce to one root cause, and that cause is diagnosed with the commands
quoted below.

## BrotherModeUp state, and exactly what is proven about it

Two commits, both pushed, both confirmed against the remote by comparing
HEAD to @{u} after the push.

    586a20d  the passport producer fixes and the two repository hazards
    13814a6  the board refresh and two ledger entries

WHAT IS PROVEN, and about which commit. This distinction is the point.

586a20d carries a full-gate verdict, run on a COMMITTED tree after the last
edit:

    test_all: 3257 tests across 37 suites, 5 skipped, 1624.7s wall. ALL GREEN

13814a6 carries THREE TARGETED CHECKS ONLY, not a full gate:

    test_bm_docs.py       Ran 230 tests    OK (skipped=1)
    scripts/doctor.py     10 of 12 proven, 2 skipped, 0 failed
    bm_progress_check.py  progress page: current at docs/plan/NORTH-STAR-PUSH-BOARD.html

Do NOT quote 586a20d's ALL GREEN beside 13814a6. A full gate over the final
state, including this pack, is the last thing this session runs; if its
verdict is not recorded in 06-CLOSE-REPORT.md then it did not finish, and
13814a6 is UNVERIFIED by a full gate. That is a real gap, stated rather than
papered over.

All four inherited BrotherSBE task declarations are closed. `sbe task list`
reports "no open tasks". Each was closed as FORCED with a written disposition
naming what it covered, which is never read as clean, and that is correct:
three paths (.gitignore, SECURITY.md, pyproject.toml) were written under no
declaration at all.

## BrotherSBE pull request 48: the whole diagnosis

DO NOT force-merge. DO NOT weaken a check. DO NOT touch branch protection:
`enforce_admins` is true, so even --admin does not bypass it, and lowering it
is a founder action in a browser. The founder was shown the state and chose
"fix them to green first" over a force-merge.

SIX RED CHECKS, ONE ROOT CAUSE. Five `gates` jobs (macos and ubuntu on 3.9
and 3.x, plus gates-windows) all report the identical line:

    STRICT: 1 design check(s) failed; exiting nonzero to block the merge.

and `consumer-checks` reports:

    INVALID  check:contract-compatibility  api-or-event-contract
    verdict: BLOCKED

They are the same failure. The contract-compatibility check's registered
command in .sbe/checks.yml is:

    python3 -m unittest tools/test_sbe.py tools/test_sbe_interop.py

and test_sbe.py's single failing test,
`TestExemptionAddressing.test_this_repository_passes_its_own_root_scan_with_the_pedagogy_waived`,
runs the same design check the gates jobs run directly. Reproduced in a
detached worktree at the pull request head:

    Ran 134 tests in 32.064s
    FAILED (failures=1)

THE ACTUAL DEFECT:

    artifacts  FAIL  tier T3 requires 01, 02, 03, 04, 05, 06, 07, 08;
    missing: 01-purpose.md, 02-process.md, 03-adr.md, 04-technology-map.md,
    05-data-model.md, 06-diagrams.md, 07-verification.md, 08-behaviour.md;
    examined design/release-blockers

IT IS NOT THE PULL REQUEST'S DEFECT, and this matters for how it is
described. `design/release-blockers/00-intake.json` came from commit ec77b63
and is NOT in the pull request's diff: `git diff --stat origin/main...HEAD --
design/release-blockers/` returns nothing. On main the same check reports:

    artifacts  NO-DATA  00-intake.json has no valid tier (got None)

and main exits 0. The pull request corrected the tier computation to follow
blast radius, which made a permanently mute check able to speak, and the
first thing it said was true. That is the SECOND instance in one night of a
control that could only ever stay silent; the first was BrotherMode's own
`check_install_identity`, which SKIPs forever because the documented install
writes no identity stamp.

WHY THIS INTAKE IS THE ONLY ONE LIKE IT: every other dossier (field-book T2,
lifecycle-blockers T2, final-release-program T3, team-operating-model T3)
carries an explicit `tier` key. release-blockers carries none, while its own
notes claim "the tier is declared here rather than left for the policy engine
to infer". The note describes a declaration the file does not make.

THE FIX IN FLIGHT when this was written: a strongest-tier agent writing the 8
artifacts into
/Users/khalil.maaouni/Documents/BrotherSBE/design/release-blockers/ plus
adding `"tier": "T3"` to the intake, grounded in the five shipped subsystems
the intake names (the write boundary and Stop reconciler, the evidence trust
vocabulary, the required-evidence policy engine, the registered check
registry, the ownership rules). Template: design/final-release-program, a
passing T3, 708 lines across its 8 files.

IF THAT OUTPUT IS NOT ON DISK, the work is unstarted and yours. Check
`ls ~/Documents/BrotherSBE/design/release-blockers/`. If it IS on disk,
DO NOT trust it unread: the brief forbade inventing rationale, and whether it
obeyed is the reviewing session's job to establish, not to assume.

DONE-CHECKS, both must pass, run from /Users/khalil.maaouni/Documents/BrotherSBE:

    python3 tools/sbe_design.py --strict .
    python3 -m unittest tools/test_sbe.py tools/test_sbe_interop.py

## Traps in BrotherSBE that have already cost time

Handed over by the BrotherSBE session that stopped at its context limit. Each
was verified here rather than accepted.

1. THE WORKING TREE LIES. Verify in a detached worktree, never in the
   checkout: `git worktree add --detach /tmp/v HEAD`. That session measured
   545 evals passing with 1 unit failure in its working tree, and 543 passing
   with 4 unit failures at the same commit in a clean copy.
2. Run `sh scripts/checksums.sh CHECKSUMS.sha256` AFTER `git add`, never
   before. That mistake cost them two commits.
3. Before any BrotherSBE commit run
   `python3 -m unittest tools.test_sbe.TestNoPrivateNameShips`. A client name
   is in that repository's history and the check has already caught one
   reaching a tracked file.
4. NEVER push BrotherSBE `main` or `backup/local-main-2026-08-15`. A client
   name is in 70 commit subjects. That is why pull request 48 is one squashed
   commit; publishing the real history needs the subjects rewritten, which is
   a founder decision.
5. Do NOT force-close BrotherSBE's six open registry tasks. A forced close
   writes a decision package that the next close reports as an undeclared
   path, which forces another close. The loop is the defect, documented in
   docs/plans/2026-08-15-fortnight-to-product-grade.md section 5b.
6. Do NOT revert their .gitignore additions.

## Pull request 47

Superseded, verified here rather than taken on trust:

    git diff --stat origin/feature/change-passport-seam \
        origin/feature/fortnight-plan-and-floor-audit \
        -- tools/sbe_passport.py docs/specs/

returns nothing, so the passport work is byte-identical in both. The branches
differ only by 12 files that are 48's additional plan documents. Merge 48,
close 47 as superseded.

## What the founder decided, so it is not re-litigated

1. Land on main at every green gate in BrotherModeUp, rather than branch and
   pull request.
2. Bitbucket is BLOCKED, not unverified, while that workspace is over its
   5-user limit. Work around it; do not retry pushes hoping they land.
3. Keep going past the context stop line by chaining a fresh session.
4. Do not merge the red pull requests; fix them to green first.
5. Both token stops waived; the 07:00 JST clock is the brake. The spend-guard
   hook was NOT edited, deliberately. If it refuses, that is a machine control
   doing its job: stop, write the handover, notify. Do not bypass it.

## Still open, named rather than softened

- BrotherSBE pull request 48 not green, not merged. Pull request 47 not
  closed.
- W2, shipping the passport consumer into the installed plugin, sits behind
  that merge. `sbe_passport.py` is in the BrotherSBE source and absent from
  the installed plugin's tools directory, verified by listing it.
- M22 is an OPEN defect, filed not patched: nothing either product ships
  writes an ignore rule into a consumer repository, so `.brothermode/` and
  `.sbe/` land there neither tracked nor ignored. Ours carries the founder's
  recorded decisions with their alternatives.
- The seam reads 4 of 5 fields carried in BrotherModeUp with a deposit
  present, and 2 of 5 in BrotherSBE with none. Quote it as a pair with both
  trees named, never as a property of the seam.
