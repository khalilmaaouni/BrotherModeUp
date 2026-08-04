# W-2 record corrections: docs/NOT-FINALIZED.md, docs/PACKAGING.md, docs/REMAINING.md, 2026-08-04

Status: CURRENT as of 2026-08-04.

Agent W-2. Applied corrections from CHK-2A, CHK-2B and CHK-2C to the three
files fenced to this agent, plus one extra correction on the tag question
resolved by the orchestrator after CHK-2C's report. Every correction is an
APPENDED, dated block beneath the original text, per the project's own
anti-gaming rule: no dated entry was rewritten to agree with today.

## Corrections applied

### docs/NOT-FINALIZED.md (5 corrections, CHK-2A rows 10, 14, 21, 22, 33)

1. **Row 10 (P5-fix `apply` two-units-of-work ambiguity).** Appended a
   "CORRECTED IN PART, 2026-08-04" block after the original PARTIAL text
   (original at line 133, correction starts at line 143). Records that
   `apply` now refuses without exactly one of `--record`, `--new-record`, or
   an active work record (tools/bm_learn.py:733-766), closing the gap named
   as not shipped, per commit 259c30b.
2. **Row 14 (item 2, Bash writes are not gated by the fence hook).**
   Appended a "CORRECTION, 2026-08-04" block after the original OPEN text
   (heading at line 198, unchanged; correction starts at line 208), carrying
   the three limits VERBATIM per the task brief's judgement call 3: (1) the
   literal-matcher / not-a-shell-parser limit, (2) OS containment explicitly
   out of scope, (3) the fail-open path when `tools/bm_store.py` cannot be
   imported. CHK-2A confirmed all three against the shipped code
   (tools/bm_bash_audit.py:321-352, docs/KNOWN-LIMITS.md:111-117,
   SECURITY.md:346-352), so all three were carried as instructed.
3. **Row 21 (item 9, Three scoring checks are red).** Appended an
   "ADDENDUM, 2026-08-04" block (starts at line 390) after the original OPEN
   text. Records four checks red today, not three, with the derivation
   command `python3 tools/bm_score.py` stated inline.
4. **Row 22 (item 10, The suites cannot be run concurrently).** Appended a
   "CORRECTED 2026-08-04" block (starts at line 435) replacing only the
   closing "Not in CI" claim's currency, leaving the original paragraph in
   place above it. Records the CI gate job now running `test_all.py` and the
   `SUITES` tuple now listing 14 suites, with derivation
   (`tools/test_all.py:83`, counted entries).
5. **Row 33 (item 19, SKILL.md/DIGEST.md bullet).** Appended a
   "CLOSED IN PART, 2026-08-04" block (starts at line 783) after the
   original bullet list, noting SKILL.md now documents
   `--record-applications`/`disposition`/`should-retrieve` while DIGEST.md
   (13 lines, `wc -l DIGEST.md`) still does not.

The other 33 STILL-TRUE rows from CHK-2A were left untouched, as instructed.

### docs/PACKAGING.md (CHK-2B counts, judgement call 1 and 2 applied)

1. Appended a correction after the "six commands" list (original at line
   14, correction starts at line 18): 12 console scripts now exist,
   derivation `grep -c "^bm-" pyproject.toml` -> 12, all 12 named from
   `[project.scripts]`.
2. Appended a correction after the VERSION/PEP 440 paragraph (original at
   line 136, correction starts at line 143): `VERSION` now reads
   `2.0.0-rc.13.dev1` (`cat VERSION`), `pyproject.toml` publishes
   `2.0.0rc13.dev1` (`grep '^version = ' pyproject.toml`).
3. Appended a correction to the "seven siblings" module-count bullet
   (correction starts at line 164): 17 py-modules today, derivation
   `sed -n '92,110p' pyproject.toml` (17 entries) and `ls tools/bm_*.py |
   wc -l` -> 17.
4. Appended a correction to the "`scripts/install.py`, which does not
   exist" bullet (correction starts at line 175): the file exists,
   derivation `ls scripts/install.py`.
5. Appended a correction to the "No CI builds this" bullet (correction
   starts at line 195): a packaging install suite (C-06) now runs in CI,
   `.github/workflows/tests.yml` lines 119-129, `test_bm_packaging_install.py`.

**Judgement call 1 honored exactly as instructed.** Grepped and confirmed
the version-2.0.0rc3 mentions sit at lines 39, 40, 41 and 47 (all inside the
single dated "Verified. `uv 0.11.28` produced..." build-report sentence from
2026-07-29) and left every one of them untouched, including the "all nine
`bm_*` modules and the six console scripts" clause on line 41, which is part
of that same dated sentence rather than a current-state claim. Only the
current-state VERSION mentions at lines 136 (formerly ~127) and its neighbor
were corrected, plus the general (non-dated-build) claims at lines 14, 145
("seven siblings"), 154 (`scripts/install.py`), and 168 ("No CI builds
this"), which CHK-2B separately flagged as stale current-state text, not
historical build evidence.

### docs/REMAINING.md (CHK-2C, judgement call 4, plus the extra tag correction)

1. **Item 1 (telemetry audit pass), two corrections only, as instructed.**
   Appended a "CORRECTED 2026-08-04" block (starts at line 70) stating: the
   file is 1995 lines by `wc -l tools/bm_telemetry.py`, not 1,211; and the
   "Confirmed still open" block enumerates exactly THREE findings, not
   "roughly thirteen" (no enumerable source for "thirteen" found in the
   tree, confirmed with `grep -rniE "thirteen|13 (findings|audit)"
   docs/*.md`). Explicitly stated that dispositions for the three findings
   themselves are PENDING a separate, currently running calibrated-probe
   audit and were NOT written here, per the brief.
2. **Extra correction: the tag question (item 6's 2026-08-01 correction
   block).** Appended a "RESOLVED 2026-08-04 (orchestrator...)" block
   (starts at line 33) beneath the existing 2026-08-01 correction block,
   without editing that block. States, with `git ls-remote --tags origin`
   and `git tag -l` as the two commands: (a) rc.10, rc.11, rc.12 were never
   tagged on either side, so the local tag list is not incomplete and there
   is nothing to fetch; (b) `v2.0.0-rc.3` exists as a LOCAL tag only and is
   absent from the remote, a new defect, so pinning `v2.0.0-rc.3` cannot be
   resolved from GitHub. This replaces CHK-2C's own CANNOT-FULLY-DECIDE
   wording (which lives only in the CHK-2C report file, never in
   docs/REMAINING.md) with the resolved facts.

## Greps proving new wording present and old wording confined to dated entries

```
$ grep -n "CORRECTED IN PART, 2026-08-04 (per CHK-2A row 10" docs/NOT-FINALIZED.md
143:CORRECTED IN PART, 2026-08-04 (per CHK-2A row 10, ...)

$ grep -n "CORRECTION, 2026-08-04 (per CHK-2A row 14" docs/NOT-FINALIZED.md
208:CORRECTION, 2026-08-04 (per CHK-2A row 14, C-02, ...

$ grep -n "^## 2. Bash writes are not gated by the fence hook. OPEN." docs/NOT-FINALIZED.md
198:## 2. Bash writes are not gated by the fence hook. OPEN.
(original heading unedited, word "OPEN" preserved)

$ grep -n "ADDENDUM, 2026-08-04 (per CHK-2A row 21" docs/NOT-FINALIZED.md
390:ADDENDUM, 2026-08-04 (per CHK-2A row 21, ...

$ grep -n "\`prediction-seals\` (3 sealed against a target of 5)" docs/NOT-FINALIZED.md
382:\`prediction-seals\` (3 sealed against a target of 5), plus two cadence checks.
(original stale "3 sealed" line still readable, unedited)

$ grep -n "CORRECTED 2026-08-04 (per CHK-2A row 22" docs/NOT-FINALIZED.md
435:CORRECTED 2026-08-04 (per CHK-2A row 22, ...

$ grep -n "^Not in CI. CI deliberately splits" docs/NOT-FINALIZED.md
431:Not in CI. CI deliberately splits the suites across platform legs to produce
(original stale claim still readable, unedited)

$ grep -n "CLOSED IN PART, 2026-08-04 (per CHK-2A row 33" docs/NOT-FINALIZED.md
783:CLOSED IN PART, 2026-08-04 (per CHK-2A row 33, ...

$ grep -n "OPEN: \`SKILL.md\` and \`DIGEST.md\` were not updated" docs/NOT-FINALIZED.md
769:- OPEN: \`SKILL.md\` and \`DIGEST.md\` were not updated by this loop, ...
(original bullet still readable, unedited)

$ grep -n "CORRECTED 2026-08-04 (per CHK-2B" docs/PACKAGING.md
18:CORRECTED 2026-08-04 (per CHK-2B, ...)
143:CORRECTED 2026-08-04 (per CHK-2B, ...)
164:  CORRECTED 2026-08-04 (per CHK-2B): "seven siblings" (nine modules total)
175:  CORRECTED 2026-08-04 (per CHK-2B): this was accurate on 2026-07-29 ...
195:  CORRECTED 2026-08-04 (per CHK-2B): this was accurate on 2026-07-29 ...

$ grep -n "puts six commands on your PATH" docs/PACKAGING.md
14:\`pipx install brothermode\` puts six commands on your PATH and nothing else:
(original stale claim still readable, unedited)

$ grep -n "\`VERSION\` says \`2.0.0-rc.3\`" docs/PACKAGING.md
136:\`VERSION\` says \`2.0.0-rc.3\`. PEP 440, which every Python packaging tool
(original stale claim still readable, unedited)

$ sed -n '48,50p' docs/PACKAGING.md
Verified. \`uv 0.11.28\` produced \`brothermode-2.0.0rc3-py3-none-any.whl\`
(241718 bytes) and \`brothermode-2.0.0rc3.tar.gz\` (242451 bytes), containing
all nine \`bm_*\` modules and the six console scripts.
(dated 2026-07-29 build-report sentence, judgement call 1: left untouched)

$ grep -n "CORRECTED 2026-08-04 (per CHK-2C" docs/REMAINING.md
70:CORRECTED 2026-08-04 (per CHK-2C, ...)

$ grep -n "is 1,211 lines\|Roughly thirteen" docs/REMAINING.md
50:\`tools/bm_telemetry.py\` is 1,211 lines. It holds the corrections ledger, ...
51:ledger, the handover export, and project identity. Roughly thirteen of the original
(original stale claims still readable, unedited)

$ grep -n "RESOLVED 2026-08-04 (orchestrator" docs/REMAINING.md
33:RESOLVED 2026-08-04 (orchestrator, superseding CHK-2C's CANNOT-FULLY-DECIDE ...

$ grep -n "v2.0.0-rc.1 through v2.0.0-rc.13" docs/REMAINING.md
22:  not a nicety"). Tagged, annotated releases now exist: v2.0.0-rc.1 through v2.0.0-rc.13
(the 2026-08-01 correction block itself left unedited, appended below only)
```

`git diff --stat` for the three files confirms pure additions, no rewrites:

```
$ git diff --stat docs/NOT-FINALIZED.md docs/PACKAGING.md docs/REMAINING.md
 docs/NOT-FINALIZED.md | 109 ++++++++++++++++++++++++++++++++++++++++++++++++++
 docs/PACKAGING.md     |  40 ++++++++++++++++++
 docs/REMAINING.md     |  31 ++++++++++++++
 3 files changed, 180 insertions(+)
```

Confirmed no em or en dashes were introduced:

```
$ git diff docs/NOT-FINALIZED.md docs/PACKAGING.md docs/REMAINING.md | grep '^+' | grep -P '[\x{2013}\x{2014}]'
(no output)
```

## Done-check: `python3 tools/test_bm_docs.py`

Verbatim tail of the run:

```
...................................................................................................F.................s.ss.s.s............
======================================================================
FAIL: test_every_dated_document_declares_its_status_at_the_top (__main__.TestHistoricalDocumentsSaySo)
A dated handover that does not say what it is reads as current state
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_bm_docs.py", line 868, in test_every_dated_document_declares_its_status_at_the_top
    self.assertEqual(
AssertionError: Lists differ: ['docs/closure/PLAN-LOOPS-2-7-2026-08-04.md'] != []

First list contains 1 additional elements.
First extra element 0:
'docs/closure/PLAN-LOOPS-2-7-2026-08-04.md'

- ['docs/closure/PLAN-LOOPS-2-7-2026-08-04.md']
+ [] : dated document(s) that declare no status in the first 25 lines: docs/closure/PLAN-LOOPS-2-7-2026-08-04.md. Either mark it HISTORICAL with a superseded-by pointer, or state `Status: CURRENT` if it really is current.

----------------------------------------------------------------------
Ran 137 tests in 91.675s

FAILED (failures=1, skipped=5)
```

**This failure is red for a reason I did not cause and is not papered over
here.** `docs/closure/PLAN-LOOPS-2-7-2026-08-04.md` is an untracked file
(confirmed with `git status --porcelain`, shown as `??`, not `M`) that is
outside my three-file WRITE fence; I never read or wrote it. Confirmed with
`git status --porcelain docs/closure/PLAN-LOOPS-2-7-2026-08-04.md
docs/NOT-FINALIZED.md docs/PACKAGING.md docs/REMAINING.md`:

```
 M docs/NOT-FINALIZED.md
 M docs/PACKAGING.md
 M docs/REMAINING.md
?? docs/closure/PLAN-LOOPS-2-7-2026-08-04.md
```

None of the three files I own appear anywhere in the test's failure output.
The orchestrator owns the full gate and this file; I am flagging it plainly
rather than claiming a green run I did not produce.

## What I refused to apply, and why

- **NOT-FINALIZED.md, row 14's implied heading-word change.** CHK-2A's
  proposed correction text changes the heading word from OPEN to PARTIAL and
  adds "and cannot fully be" to the heading itself. I did not touch the
  heading: per the task's ONE RULE, a dated entry's original text (including
  its heading) is never edited to agree with today, only appended beneath.
  The heading still reads "OPEN" as originally written; the appended
  correction block states the current, more precise picture underneath it.
- **REMAINING.md item 1, the three findings' dispositions.** Explicitly not
  written, per the task brief: a separate agent is auditing them with
  calibrated probes and its verdict supersedes any reading-only judgement.
  Only the two count corrections (line count, finding count) were applied.
- **pyproject.toml's stale "13 bm_* names" comment**, which CHK-2B also
  flagged, was left alone: that file is outside my three-file WRITE fence.
- **PACKAGING.md's dated 2026-07-29 build-report sentence** (lines 39-41,
  47, the rc3 wheel/sdist verification), was left untouched per judgement
  call 1, including the "nine `bm_*` modules and six console scripts" clause
  embedded in that same sentence, since it is part of the same historical
  build record rather than a current-state claim.
