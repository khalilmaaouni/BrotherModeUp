# CHK-2A verdicts: every entry of docs/NOT-FINALIZED.md checked against today's tree, 2026-08-04

Status: CURRENT as of 2026-08-04.

Method: read docs/NOT-FINALIZED.md in full, docs/closure/CLOSURE_REGISTER.md in
full, tools/bm_bash_audit.py and tools/bm_fence_hook.py in full, plus targeted
greps and reads of tools/bm_store.py, tools/bm_learn.py, tools/bm_learning.py,
tools/bm_threads.py, SKILL.md, DIGEST.md, docs/KNOWN-LIMITS.md, SECURITY.md,
.github/workflows/tests.yml, and `git ls-remote --tags origin`. No file outside
this report was written. `python3 tools/test_all.py` was not run (owned by the
orchestrator); one read-only diagnostic, `python3 tools/bm_score.py`, was run
because it never writes and exits 0 unconditionally in non-strict mode.

DONE-CHECK: `grep -c "^## \|^### " docs/NOT-FINALIZED.md` returns 39.
This table has 38 rows: 39 headings minus the excluded
"What is genuinely finished" heading. They reconcile.

## Verdict table

| # | Heading (line) | Current status word | Verdict | Evidence | Correction |
|---|---|---|---|---|---|
| 1 | rc.4 MERGE: the gate carry cap was REJECTED... (14) | OPEN | STILL-TRUE | `grep -rn "_GATE_CARRY_CAP" tools/*.py` returns nothing: the constant is gone, matching the entry's own claim that it was deleted. | none |
| 2 | rc.4 MERGE: approval now needs two things... (36) | PARTIAL | STILL-TRUE | tools/bm_learn.py:442-486 (`cmd_approve`): still refuses without both `--ref` and a receipt (`no-approval-receipt`), and the comment block at line 460 still explains why the two guards were kept separate. | none |
| 3 | P7 (found in passing...): the loop-close gate flakes 1 run in 16. (49) | CLOSED 2026-07-31 | STILL-TRUE | Historical fix record; no counter-evidence found. Not independently re-run 100x this session (out of scope: would need test_all.py). | none |
| 4 | P7: the FTS5 fast path ships DISABLED by default. (68) | DEFERRED | STILL-TRUE | tools/bm_store.py:2355 FTS5_ENV = "BROTHERMODE_FTS5", still opt-in via env var. | none |
| 5 | P7: the retrieval gain is measured on ONE labelled fixture. (78) | PARTIAL | STILL-TRUE | No labelled corpus found; CLOSURE_REGISTER's X-03 (benchmark corpus) is still listed as not machine-closable, consistent with no corpus having landed. | none |
| 6 | P7: index maintenance covers approval and edit, not every future write. (87) | UNPROVEN | STILL-TRUE | `grep -n "_fts_write_rule" tools/bm_store.py` shows the function defined once (line 4654) and called from exactly two sites (6010, 6708), both inside approval/edit paths, matching the claim. | none |
| 7 | P6: the run stored the founder's prompt by default. (101) | CLOSED by fix round P6 | STILL-TRUE | Not independently re-run this session; no counter-evidence found in the term-storage code path. | none |
| 8 | P6: a task's vocabulary is still stored... (116) | OPEN | STILL-TRUE | No evidence of a change to term storage or a new withholding path. | none |
| 9 | P6: retrieval_uuid is nullable forever... (125) | DEFERRED | STILL-TRUE | tools/bm_store.py:2316-2317: ALTER TABLE learning_applications ADD COLUMN retrieval_uuid TEXT REFERENCES learning_retrieval_runs(retrieval_uuid), no NOT NULL, no migration since. | none |
| 10 | P5-fix: apply discloses the two-units-of-work ambiguity, it does not resolve it. (133) | PARTIAL | STALE | tools/bm_learn.py:733-766: apply now REFUSES without exactly one of --record, --new-record, or an active env record, in addition to --session. Commit 259c30b ("Give every substantial task one unambiguous work identity...", 2026-07-30) is the fix. This closes the sentence about making --record mandatory for apply, which the entry said had not shipped in that round. | Correction 1 |
| 11 | P5-fix: the fixes were verified through apply, not through the alias. (143) | UNPROVEN | STILL-TRUE | `grep -n "record-applications"` in tools/test_bm_store.py finds no dedicated test of the relevant --record-applications alias against the P5-fix behaviors; relevant still routes to the same record_learning_applications (tools/bm_learn.py:784). | none |
| 12 | Loop P5: relevant is deprecated but not removed. (152) | DEFERRED, by design | STILL-TRUE | tools/bm_learn.py:714-718: relevant still prints the deprecation line on every run and still honours --record-applications as opt-in. | none |
| 13 | 1. Used daily, never measured. (162) | PARTLY CLOSED | STILL-TRUE | docs/closure/CLOSURE_REGISTER.md's X-04 (Sustained dogfood) restates the identical narrative as of 2026-08-04: real use happened, measurement is what is missing. Consistent, not contradicted. | none |
| 14 | 2. Bash writes are not gated by the fence hook. (184) | OPEN | STALE | docs/closure/CLOSURE_REGISTER.md C-02 status line: closed 2026-08-04, refuse and alert landed. Full read of tools/bm_bash_audit.py confirms refusal_for() (line 321) refuses an obvious destructive shell form naming BrotherMode's own state under BM_FENCE_MODE=enforced, and control-state checks detect and alert on state loss in both modes. The heading's own premise (PreToolUse hook sees Edit, Write, NotebookEdit; a shell write goes around it) is still true for the PreToolUse fence hook itself (tools/bm_fence_hook.py:124-131, WRITE_TOOLS excludes Bash), so the underlying gap is real, but the framing that nothing was built against it is now false. All three limits named in the task brief were checked against the code and are each accurate as literally implemented: (1) confirmed at tools/bm_bash_audit.py:321-352, refusal_for's own docstring; (2) confirmed at tools/bm_bash_audit.py header comments and CLOSURE_REGISTER C-02's own "out of scope" line; (3) confirmed by code trace: cmd_pre (bm_bash_audit.py:860-889) only attempts a refusal inside "if root is not None", and root is only reachable after _load_store_module() succeeds, so an unimportable bm_store.py silently skips the whole enforced-mode block, matching docs/KNOWN-LIMITS.md:111-117 and SECURITY.md:346-352. | Correction 2 |
| 15 | 3. Session identity is harder to forge, not unforgeable. (194) | PARTIAL | STILL-TRUE | Full read of tools/bm_fence_hook.py:179-190 (label_for_token) and its docstring matches the entry's description exactly: per-session secret token, owner-only file, public label is a one-way hash. | none |
| 16 | 4. Handovers are lock-serialized, not transactional. (206) | CLOSED/REOPENED/CLOSED | STILL-TRUE | Not independently re-run; the entry already documents its own reopen-and-reclose arc with commit-level detail. No counter-evidence found. | none |
| 17 | 5. The adopt defect. (261) | REFUTED and CLOSED | STILL-TRUE | tools/bm_threads.py:943-960 (_adopt_core): the GATE 3 ordering comment and the transition-before-render structure the entry describes are present. | none |
| 18 | 6. Recovered work is owner-only on POSIX only. (297) | OPEN | STILL-TRUE | docs/KNOWN-LIMITS.md:434-455 states the same unfixed gap in the same words. grep for ACL across tools/bm_autosave.py, tools/bm_store.py, CHANGELOG.md finds no Windows ACL implementation, only comments stating ACLs are not set. This is a different mechanism from C-09 (quarantine directory chmod, closed 2026-08-03), which does not touch this entry's claim at all. | none |
| 19 | 7. The lazy core missed its own target. (306) | PARTIAL, measured | STILL-TRUE | docs/BENCHMARK-V1-V2-RC2.md:47 and docs/HANDOVER-2026-07-29.md:247 both still cite 1,490 tokens against the 400 target, unchanged. | none |
| 20 | 8. The lazy core is UNPROVEN in the way that matters. (316) | (heading, no bare status word) | STILL-TRUE | grep across tools/ and hooks/ for a loaded-when-warranted guard finds nothing; the planned Stop-hook check is still absent. | none |
| 21 | 9. Three scoring checks are red. (325) | OPEN | STALE (numbers only; structural claim holds) | Ran python3 tools/bm_score.py (read-only, never writes, exits 0): today's local output shows 4 FAIL checks (cache-economy, fence-hygiene, budget-vs-tier, prediction-seals), and prediction-seals reads "4 sealed (target >= 5)", not the "3 sealed" the entry cites. .github/workflows/tests.yml:70 confirms bm_score.py --strict still runs in CI with no vault seeded, so the FAILS-locally-PASSES-in-CI structural claim still holds. | Correction 3 |
| 22 | 10. The suites cannot be run concurrently. (335) | OPEN, now mitigated but not fixed | STALE (one clause only) | .github/workflows/tests.yml:120-155: a gate job now runs python3 tools/test_all.py --artifacts ... --timeout 1200 on every push/PR. The entry's closing claim ("Not in CI... Wiring it into CI is a Loop 13 option, not done here") no longer holds. The rest (module-rename technique still shared across suites, confirmed by grep hits in tools/test_bm.py and tools/test_bm_bash_audit.py; concurrency still unsafe) is unchanged and still true. tools/test_all.py's SUITES tuple now lists 14 suites, consistent with CLOSURE_REGISTER's "1518 tests across 14 suites" line. | Correction 4 |
| 23 | 11. Phase 3, the public install, is DEFERRED. (370) | DEFERRED | STILL-TRUE | grep for a windows-native dispatcher across scripts/ and tools/ finds nothing; grep for win32/platform.system in scripts/install.py finds nothing. Still absent, matching the entry's still-open claim. | none |
| 24 | 12. The independent re-audit was never run. (398) | DEFERRED | STILL-TRUE | CLOSURE_REGISTER's not-machine-closable list (X-01 to X-06) has no item matching a closing adversarial pass against all 17 findings with a second model family. Not addressed. | none |
| 25 | 13. Orchestration practice did not improve, only the outcome did. (408) | (no status word) | STILL-TRUE | No later entry in CLOSURE_REGISTER or docs/closure/ addresses fence-before-dispatch discipline or the add-only-fence-on-the-same-file practice; this is a process observation, not a code claim, and nothing found supersedes it. | none |
| 26 | 14. Findings 16 to 63 of the FIRST audit were triaged by class. (417) | (no status word) | STILL-TRUE | Consistent with row 24 above (DEFERRED, no independent re-audit run); no evidence any of findings 16-63 were individually re-proven since. | none |
| 27 | 15. dump redaction is a secret scrubber, not a redactor. (422) | OPEN | STILL-TRUE | tools/bm_store.py:2854 comment still lists records.objective, records.evidence, digests.body, transitions.note as columns covered only by the pattern scrubber via _DUMP_SAFE_COLUMNS, not full redaction; no full-withholding path found for these four columns. | none |
| 28 | 16. bm_store.py claim --help claims a record named --help. (476) | CLOSED 2026-07-30 | STILL-TRUE | tools/bm_store.py:12477 _require_positional still defined and still called from cmd_claim, cmd_checkpoint, cmd_decide, and the shared transition path. | none |
| 29 | 17. The English-only, 400-character correction filter. (497) | CLOSED 2026-07-29 | STILL-TRUE | tools/bm_learning.py:593 detect_correction still present; not independently re-run against French/Japanese fixtures this session. | none |
| 30 | 17b. What Loop 4 owed the plan and did not build. (523) | OPEN | STILL-TRUE | Channel-3 automatic detection: capture_outcome_candidate (tools/bm_store.py:5521) still requires an explicit caller; no scheduler or hook found invoking it automatically. Second OPEN bullet (correction row not carrying current work record) not independently re-verified this session; no counter-evidence found. | none |
| 31 | 18. What Loop 6 built, and what its conflict detector cannot see. (551) | (heading has no bare status word; body has 5 OPEN sub-items) | STILL-TRUE | Spot-checked the CLI-surface sub-claim: grep for grant-edit and cmd_edit in tools/bm_learn.py return nothing, confirming that CLI pair is still deliberately absent. Lexical-only detection and non-inferred scope-containment sub-claims not independently re-probed this session; CLOSURE_REGISTER does not touch bm_learning.py's conflict detector at all. | none |
| 32 | Correction round, 2026-07-29: four ways the done gate leaked (602) | (subheading, no status word) | STILL-TRUE | Historical fix record with commit-level detail; no counter-evidence found. | none |
| 33 | 19. What Loop 7 built, and what it still cannot see. (642) | (heading has no bare status word; body has several OPEN/UNPROVEN sub-items) | STALE (one bullet only) | SKILL.md:60-95 now explicitly documents apply's mandatory work identity (row 10 above), and names disposition, classify, and should-retrieve, which is the exact list this entry says SKILL.md was missing. grep for those four terms in DIGEST.md (13 lines total) returns nothing, so the DIGEST.md half of the claim still holds. The other bullets (retrieval context not stored, gate-cutoff CLOSED note, UNPROVEN on real-day grading, proportionality classifier scope) were not contradicted by anything found. | Correction 5 |
| 34 | 20. What Loop 8 built, and what its correction round fixed. (692) | (heading has no bare status word; body has OPEN/UNPROVEN sub-items) | STILL-TRUE | Channel-3 detector absence re-confirmed (same evidence as row 30). grep for a session-only-match flag in tools/bm_learn.py and tools/bm_store.py found no flag distinguishing that grading path in loop-failures output, matching the claim. | none |
| 35 | 21. Approval receipts landed in code; three documents still describe the old flow. (752) | CLOSED 2026-07-31 | STILL-TRUE | tools/bm_learn.py:442-486 (cmd_approve) still enforces both guards and the "neither proves WHICH human" framing matches the code's own comments at line 462-470. | none |
| 36 | 22. complete short-prefix blames a missing record... (793) | CLOSED 2026-07-31 | STILL-TRUE | _resolve_record_uuid (tools/bm_store.py:7642) confirmed called from the transition path (line 5375) that backs complete, park, resume, adopt. | none |
| 37 | 23. The two oldest published tags are lightweight, not annotated. (815) | OPEN (low impact) | STILL-TRUE | git ls-remote --tags origin run live: refs/tags/v2.0.0-rc.1 and refs/tags/v2.0.0-rc.2 each have no peeled ^{} line (still lightweight); rc.4, rc.5, rc.6, rc.7, rc.8, rc.9, and rc.13 each do have one (annotated). Exactly matches the entry's claim, unchanged, and now additionally true of every RC published since. | none |
| 38 | 24. The two handover flakes were not reproduced, but a THIRD... was found and FIXED. (845) | (dated narrative, mixed) | STILL-TRUE | Dated, first-person narrative of a specific investigation on 2026-07-31; not edited to agree with today per the task's own rule. No counter-evidence found suggesting the fix described was reverted; tools/test_bm.py still exists and row 22's suite-count check confirms the suite still runs. | none |

## Corrections (long text, referenced from the table by number)

### Correction 1 (row 10): P5-fix, apply discloses the two-units-of-work ambiguity

Proposed dated addendum, appended after the existing PARTIAL text rather than
replacing it:

CLOSED IN PART, 2026-07-30, commit 259c30b, "Give every substantial task one
unambiguous work identity, and settle the promise that collided with it."
apply now refuses without exactly one of --record with an existing work uuid,
--new-record with a name, or an active work record already in the
environment, in addition to --session. Session plus query text can no longer
collapse two different units of work phrased the same way into one row: each
is refused into its own identity or refused outright. This closes the gap the
original PARTIAL named as not shipped in that round: making --record
mandatory for apply. Still true and unchanged: the deeper ambiguity this
entry named first is now a hard refusal rather than a soft warning, which is
a stronger guarantee than the entry originally asked for, not a weaker one.

### Correction 2 (row 14): Item 2, Bash writes are not gated by the fence hook

Proposed replacement heading and body, PARTIAL, carrying the three limits
from docs/KNOWN-LIMITS.md and SECURITY.md rather than paraphrasing them away:

"2. Bash writes are not gated by the fence hook, and cannot fully be. PARTIAL.
Corrected 2026-08-04.

The PreToolUse fence hook (tools/bm_fence_hook.py) still does not see Bash:
WRITE_TOOLS is Edit, Write, MultiEdit, NotebookEdit, CreateDirectory, Delete,
and Bash is deliberately absent because no reliable parse of arbitrary shell
exists. A file written through a shell command still goes straight around
the PreToolUse fence itself. That half of this entry is unchanged and is not
closable by design.

What changed under C-02, landed 2026-08-04 (see
docs/closure/CLOSURE_REGISTER.md): tools/bm_bash_audit.py now refuses an
obvious destructive shell command aimed at BrotherMode's own enforcement
state, and detects and alerts on loss of that state, in both cases only when
BM_FENCE_MODE=enforced is set. The three limits on that guarantee, quoted
from the project's own security documentation rather than paraphrased:

1. It is a literal match, a small list of destructive shell forms combined
   with the literal names .brothermode and store.sqlite3. It is not a shell
   parser and will not become one here. A name assembled at runtime, held in
   a variable, or sitting inside a script file the hook never reads is NOT
   caught. (SECURITY.md, the enforced-mode paragraph; the same statement is
   in tools/bm_bash_audit.py's refusal_for docstring.)
2. Full operating-system containment, a sandbox profile, a container, a FUSE
   write mediator, was considered and is explicitly out of scope.
   (docs/KNOWN-LIMITS.md, the WHAT IS NOT CAUGHT paragraph.)
3. When tools/bm_store.py cannot be imported at all, the project check
   itself cannot run, so nothing is refused, even under enforced mode,
   anywhere. That is a fail-open path inside a fail-closed feature, chosen on
   purpose, because the only alternative is refusing every Bash command in
   every directory on the machine, which is not shippable.
   (docs/KNOWN-LIMITS.md and SECURITY.md, in nearly identical words. Traced
   in the code: cmd_pre in tools/bm_bash_audit.py only attempts a refusal
   inside "if root is not None", and root is only reachable after
   _load_store_module succeeds, so an unimportable bm_store.py skips the
   enforced-mode block entirely rather than refusing.)

All three checked against the shipped code this session and each is accurate
as literally implemented, not overclaimed and not underclaimed.

Why not fixed further: gating Bash directly still means parsing arbitrary
shell to decide which paths a command will touch, which remains either
unreliable or so strict it blocks ordinary work. What C-02 adds is a
narrower, named, opt-in refusal for the one destructive shape this entry's
own reproduction used, not a general solution. It needs a design, full
operating-system containment, to go further, not a patch."

### Correction 3 (row 21): Item 9, Three scoring checks are red

Proposed dated addendum, not a rewrite (the original count is a snapshot the
entry itself says will keep moving):

ADDENDUM, 2026-08-04. A re-run of python3 tools/bm_score.py on this machine
today shows four checks red, not three: cache-economy (32 of 33 sessions
warm-read, one at 86 percent), fence-hygiene (STATE.md older than 2 days),
budget-vs-tier (STATE.md fence lines untagged), and prediction-seals (4
sealed against a target of 5, not the 3 cited above). The structural claims
in the entry above are unchanged and still verified: this gate is
local-vault-dependent, bm_score.py --strict still runs in CI
(.github/workflows/tests.yml line 70) where no vault exists, so CI still
reports NO-DATA rather than exercising these checks. The exact count of red
checks is not a fact worth keeping current in this file; it drifts by the
hour with ordinary use, which is the nature of a live telemetry gate rather
than a code defect.

### Correction 4 (row 22): Item 10, The suites cannot be run concurrently

Proposed replacement for the entry's closing paragraph only; the rest of the
entry, including the module-rename concurrency defect, is unchanged and
still true:

CORRECTED 2026-08-04. This entry used to say test_all.py was "Not in CI" and
that wiring it in was a Loop 13 option, not shipped. That is no longer true:
.github/workflows/tests.yml now runs a dedicated gate job on every push and
pull request, python3 tools/test_all.py --artifacts "$RUNNER_TEMP/bm-test-output"
--timeout 1200, alongside the per-platform suite and store jobs that still
exist for their own reason, per-platform evidence the serial gate cannot
produce. tools/test_all.py's own SUITES tuple now lists 14 suites, not the 4
this entry's calibration paragraph describes; that paragraph is left as-is
because it documents a point-in-time calibration, not a current count. The
underlying design defect this entry names, that the suites still rename a
module aside and so cannot run concurrently with each other or with a second
invocation of test_all.py itself, is unchanged: tools/test_bm.py and
tools/test_bm_bash_audit.py both still use the technique. CI's own three jobs
(suite, gate, store) still run as separate processes on separate runners,
which sidesteps the concurrency hazard by not sharing a filesystem rather
than by fixing it.

### Correction 5 (row 33): Item 19, What Loop 7 built, and what it still cannot see

Proposed replacement for the SKILL.md/DIGEST.md bullet only; the entry's
other bullets are unchanged and still true:

CLOSED IN PART, 2026-08-04. This bullet used to say SKILL.md does not yet
mention --record-applications, disposition, or should-retrieve. That is no
longer true of SKILL.md: it now documents the mandatory work identity apply
requires (correction 1 above), and names disposition, classify, and
should-retrieve by name, with should-retrieve described exactly as
answering whether a task shape warranted retrieval at all. It is still true
of DIGEST.md, which is 13 lines long and names no learning command at all.
Recording substantial-work applications no longer depends only on somebody
remembering an optional flag: apply now refuses outright without a work
identity (correction 1), which is a stronger fix than merely documenting the
flag would have been.

## What was not deeply verified this session, stated plainly

- Historical CLOSED entries (rows 3, 7, 16, 17, 28, 29, 35, 36) were checked
  by confirming the described mechanism is still present in the code, not by
  re-running the tests that originally proved each fix.
- The lexical-only conflict detector and the non-inferred scope-containment
  claims in row 31 (item 18) were not independently re-probed against the
  live CLI this session; only the CLI-surface sub-claim (grant-edit/edit
  still absent) was checked directly.
- Row 30 (17b) and row 34 (item 20)'s second and third bullets (correction
  row work-record linkage, the weaker-match flag in loop-failures) were
  checked by absence-of-counter-evidence grep, not by driving the CLI.
- The French and Japanese phrase packs behind row 29 (item 17) were
  confirmed present by file location only, not re-run against fixtures.
