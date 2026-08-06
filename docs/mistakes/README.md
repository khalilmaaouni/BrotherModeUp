Status: CURRENT as of 2026-08-06.
These sixteen records were imported into the repository on 2026-08-06 from the handover pack of the 2026-08-05 run, unchanged.
The paths inside these files were correct at the time of writing and line numbers may have moved since.
A future session reads this directory before working in an area named here.

# Mistakes of the overnight run, 2026-08-05 into 2026-08-06

Sixteen mistakes, each in its own file, each with the same six headings: what
happened, how it was found, the evidence, how it was fixed, the rule it produces,
and whether it was caught before or after it could hurt a user.

This folder exists so the next session does not repeat them. It is deliberately not
a success report. Every claim in these files was checked against the repository at
`/Users/khalil.maaouni/Documents/BrotherModeUp` on 2026-08-06 by running a command,
and anything I could not check says UNVERIFIED next to the claim itself.

## Read these three first

- M02, an authorisation floor that missed a file with the same power as the one it
  named. The closest call of the night.
- M06, the night's own flagship feature would have made every user's integrity
  check fail. Found by running the product on itself, not by a test.
- M12, checks that ran against a tree that was still being edited. The only failure
  here that prints OK while being worthless.

## The list

| # | File | One line |
|---|------|----------|
| M01 | `M01-codex-fence-refused-honest-work.md` | The new Codex fence refused three legitimate commands (a patch context line, a `cat` heredoc, a `git commit` message) because each merely quoted the patch grammar. |
| M02 | `M02-settings-local-json-slipped-the-safety-floor.md` | The floor that makes the permission machinery un-writable named `.claude/settings.json` and missed `.claude/settings.local.json`, and a refuter drove that gap to a dispatched write. |
| M03 | `M03-plan-had-no-driver-check.md` | The controller's most powerful command, `plan`, had no ownership check, so a foreign session could write the work plan that the honest driver then dispatched. |
| M04 | `M04-finished-run-accepted-a-stranger-result.md` | The ownership check on results was skipped once a run was finished, so any session could record a late outcome on somebody else's stopped run. |
| M05 | `M05-second-project-page-broke-the-integrity-check.md` | The integrity scripts excluded `CANVAS.md` but not the multi-project or delivery-packet names, so a user with two projects was told their install was tampered with. |
| M06 | `M06-the-same-gap-again-for-the-new-page.md` | The same class again, fourteen minutes later, for the page the night itself shipped: rendering it made `verify-install` fail with an EXTRA file. |
| M07 | `M07-packaging-mirror-not-updated-with-the-installer.md` | The installer's exclusion list grew and the packaging suite's mirror of it did not, caught by the guard that exists for that and fixed by amending the commit. |
| M08 | `M08-new-refusals-had-no-plain-language-twice.md` | New refusal codes landed with no founder-facing rewrite, twice in one night, both times refused by a guard that reads the store's source rather than a hand list. |
| M09 | `M09-a-test-count-was-written-into-the-capability-register.md` | A test count was written into the capability register, which generates into README.md, and the no-stale-numbers guard refused it. The incident is UNVERIFIED (a pre-commit refusal leaves no trace); the mechanism is verified. |
| M10 | `M10-a-red-pin-was-left-for-another-writer.md` | A writer landed a file that turned a pinned guard red in a file it was not allowed to edit, and left the red behind with a written remedy. |
| M11 | `M11-copy-rule-collided-with-a-hostile-test-fixture.md` | The no-dashes copy rule and a test that must contain dashes could not both hold; the fix changed how the test spells its data instead of weakening the rule. |
| M12 | `M12-checks-run-against-a-tree-that-was-still-moving.md` | Checks were run while files were still landing, so the results described a tree that no longer existed. One instance verified, one reported and UNVERIFIED. |
| M13 | `M13-a-test-rewrites-a-tracked-file-and-broke-the-manifest.md` | A test regenerates a tracked evidence file, so running the suite invalidates the signed checksum manifest. Three of five commits were amended because of it, and it drifted again live during the writing of this folder. Class still open. |
| M14 | `M14-the-founder-report-cites-a-commit-that-does-not-exist.md` | The morning report handed to the founder cites commit `af375ee`, which was amended away and exists on no other machine. Reached the founder uncorrected. |
| M15 | `M15-a-status-word-became-a-broken-css-class.md` | A status word pasted straight into a CSS class produced `class="bm-not run"` and `class="bm-NOW"`, found by rendering the page and looking at it. |
| M16 | `M16-a-recorded-delta-was-never-applied.md` | A writer recorded the exact change another file needed and nobody applied it, so two of the night's new files sit outside the copy rule. STILL OPEN at HEAD. |

## What is still open out of this folder

- M13, the class fix (manifest versus the self-rewriting evidence file). Only the
  per-instance repair was done, three times, by hand. NOTE FOR WHOEVER OPENS THE
  REPOSITORY NEXT: at the time this folder was written the working tree was dirty
  for `docs/program/absolute-lead/evidence/L03/E4-endtoend.json`, because a
  concurrent process ran the controller suite at 09:31 on 2026-08-06. That is
  expected behaviour, not tampering. Check `git status` first, and read M13.
- M16, both recorded deltas from the benchmark harness build report.
- M03's residual, disclosed and deliberate: driver identity is a self-asserted,
  publicly readable session id, so the ownership guard is accountability rather
  than access control.
- M01's residual, pinned by a test: `printf '...' | apply_patch` is still allowed,
  inside the arbitrary-shell gap the docs already declare open.
- M14's second claim: no full-suite gate is recorded on HEAD (c1d7a47). The last
  recorded full gate is on ac7ef87. Re-run the gate before quoting a test count.

## Where the underlying evidence lives

All paths under `/Users/khalil.maaouni/Documents/BrotherModeUp`:

- `docs/program/absolute-lead/evidence/L06/` REFUTE and FIX reports plus
  `RED-matcher.txt` for M01.
- `docs/program/absolute-lead/evidence/L09/` REFUTE and FIX reports plus
  `RED-auth.txt` for M02, M03, M04.
- `docs/program/absolute-lead/evidence/L05/` the three writer reports and
  `RED-D.txt`, `RED-E.txt`, `RED-F.txt` for M10, M11, M12, M15.
- `docs/program/absolute-lead/evidence/BENCH/HARNESS-BUILD-REPORT.md` for M16.
- `git log`, `git reflog` and `git diff` between the amended and final commits for
  M05, M06, M07, M13, M14. The reflog is local to the machine the run happened on
  and will not survive a fresh clone, so the amend evidence is quoted verbatim
  inside the files rather than left as a command to re-run.
