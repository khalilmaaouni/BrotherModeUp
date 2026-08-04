# B-6 telemetry audit fixes for tools/bm_telemetry.py, 2026-08-04

Status: CURRENT as of 2026-08-04.

This report covers all eleven findings in
`docs/closure/reports/2026-08-04-N-6-telemetry-findings.md`, worked one at a time in
the order the spec lists them. For each finding: a test was added to `tools/test_bm.py`
first, run and shown failing against the unmodified `tools/bm_telemetry.py`, then the
smallest change that turns it green was made, then `python3 tools/test_bm.py` was run
to confirm the whole suite (not just the new test) stayed green before moving on.

Every probe and test run in this session pinned `HOME`, `BROTHERMODE_VAULT` and
`BROTHERSBE_VAULT` to throwaway paths under `/private/tmp`, re-exported in the same
Bash call as the command, per the probe-isolation instruction. Every new test that
drives the CLI as a subprocess also builds its own throwaway vault (`tempfile.TemporaryDirectory`)
and, where consent matters, its own throwaway `HOME` or `BROTHERME_CONFIG`, so none of
them can read a real founder config or vault.

## Finding 1: null token field collapses the scorecard

FIXED.

Test: `TestScorecardSurvivesANullTokenField.test_null_output_tokens_does_not_collapse_the_scorecard`

Failing output before the fix:

    AssertionError: 'BROTHERMODE SCORECARD' not found in
    'bm_telemetry: swallowed error (never blocks): TypeError("unsupported operand
    type(s) for +: \'NoneType\' and \'int\'")\n'

Passing after the fix: exit 0, stdout contains `BROTHERMODE SCORECARD` and all nine
metric lines, no `swallowed error` text.

Diff summary: `fld()` (line 123) now returns `default` when the found value is not a
real number (int/float, excluding bool), instead of returning it unchanged. One
function, no callers changed.

## Finding 2: malformed signals.jsonl lines excluded from the WARNING itself

FIXED.

Test: `TestScorecardDisclosesMalformedSignalsLines.test_malformed_signals_line_is_named_in_the_warning`

Failing output before the fix: `WARNING` was absent from scorecard's stdout even with
one truncated line in `signals.jsonl` among three.

Passing after the fix: stdout contains `WARNING: ... signals=1 ...`.

Diff summary: `cmd_scorecard` now calls `read_jsonl(SIGNALS, report_bad=True)`, adds
`len(signals_bad)` into `bad_total`, and widens the WARNING format string to include
`signals=%d`.

## Finding 3: `speed` and `startup-nags` have no malformed-line disclosure at all

FIXED.

Test: `TestSpeedAndStartupNagsDiscloseMalformedLedgerLines` (two test methods, one per
command).

Failing output before the fix: neither command's stdout contained any mention of the
one truncated line planted in a 3-row ledger.

Passing after the fix: both commands' stdout contain `1 malformed`.

Diff summary: `cmd_speed` and `cmd_startup_nags` both now call
`read_jsonl(LEDGER, report_bad=True)` instead of the bare call, and each prints one new
disclosure line when `led_bad` is non-empty. Two call sites, one print each.

## Finding 4: project-identity fix silently reverts when bm_store.py cannot load

FIXED.

Test: `TestProjectIdentityDegradesLoudlyWithoutBmStore.test_identity_fallback_prints_a_degradation_notice`

Failing output before the fix: captured stderr was empty after calling `_project_of`
twice from two subfolders with `bm._bm_store_cache` forced to `[None, "simulated..."]`.

Passing after the fix: stderr contains `bm_store.py could not be loaded`.

Diff summary: new helper `_bm_store_unavailable_notice(caller)` prints a labelled
stderr notice only when `_get_bm_store()` itself returns `None` (module unavailable),
not for the separate, documented, non-buggy case of a genuinely rootless folder.
Called from both `_project_of` and `_vault_project_name` (the two call sites the
finding's evidence names), right before their existing per-folder fallback. No
behaviour change to the fallback value itself, only that it is now labelled.

## Finding 5: coordination-collision count coupled to bm_store.verify()'s prose

FIXED, with a scope note.

The finding's own stated smallest fix is "a shared constant or a structured problem
code in `tools/bm_store.py`". That file is outside this fix's write fence (the hard,
program-enforced single-writer boundary named in the brief), so I did not touch it,
and did not improvise a change there. Instead the fix stays entirely inside
`tools/bm_telemetry.py`: `_coordination_collisions` no longer calls `bm_store.verify()`
and pattern-matches its prose at all. It now runs the same invariant verify() runs (two
ACTIVE claims whose paths overlap) directly against the store via the public
`bm_store.ReadOnlyStore` and `bm_store.paths_overlap`, both already public API surface
bm_store.py exposes, so no file outside my fence was written. This fully closes the
defect (a wording edit to verify()'s message now has zero effect on this count, better
than the constant-export design, which would still require every future prose edit to
remember to update the constant) at the cost of a different coupling: to bm_store's
SQL schema (table/column names) rather than its prose. I judge the schema to be the
more stable of the two and documented the tradeoff in the function's docstring for
whoever reviews this later.

Test: `TestCoordinationCollisionsIndependentOfVerifyWording.test_collision_count_survives_a_verify_wording_change`.
It forces a real overlap into a throwaway store via direct SQL (same technique
`test_bm_store.py`'s own `TestVerify` uses), then monkeypatches the CACHED bm_store
module object `bm_telemetry.py` itself loaded (`bm._bm_store_cache[0]`, a separate
module instance from the `bs` object `test_bm.py` imports for its own use, so patching
one cannot affect the other) so `verify()` returns reworded problem strings.

Failing output before the fix:

    AssertionError: 0 != 1 : a wording change to verify()'s prose must not
    change the collision count

Passing after the fix: `_coordination_collisions(d)` returns `(1, None)` regardless of
the reworded message.

Diff summary: `_coordination_collisions` body replaced (one function, no callers
change): instead of `bm_store.verify(root)` plus a `str.startswith` filter, it opens a
`ReadOnlyStore`, runs one SQL SELECT for active claims, and counts overlapping pairs
with `bm_store.paths_overlap`.

## Finding 6: correction capture drops past eight silently, keeps the earliest

FIXED.

Test: `TestCorrectionCapDropDiscloses.test_more_than_eight_corrections_disclose_the_drop_count`

Failing output before the fix:

    AssertionError: 8 != (8, 4) : scan_corrections must report (captured, dropped):
    8 captured of 12 distinct candidates, 4 dropped silently today

(`scan_corrections` returned the bare int `8` with no way to know 4 more existed.)

Passing after the fix: `scan_corrections(...)` returns `(8, 4)`; the 8 rows actually
written to `corrections.jsonl` are unchanged (still the earliest eight, per the
finding's own scope note that changing WHICH eight are kept is a separate decision).

Diff summary: `scan_corrections` now tracks `dropped` alongside `found`; the cap check
moved from an early `break` (nothing past it inspected) to a per-item check after the
existing dedup check, so items past the cap are still detected but not written, and
`dropped` counts them. Return value changed from `int` to `(found, dropped)`; its one
caller, `cmd_outcomes_append`, was updated to unpack both and append a disclosure
clause to its existing print line when `ndropped` is non-zero. Verified there is no
other caller of `scan_corrections` anywhere in the repo (`grep -rn scan_corrections
--include="*.py" .` outside the two files I hold shows nothing).

## Finding 7: handoff truncates at 6000 characters with no marker

FIXED.

Test: `TestHandoffDisclosesTruncation.test_an_oversized_overview_gets_a_named_truncation_marker`

Failing output before the fix: assembled handoff's Overview section ended mid-word at
exactly 6000 characters with no `characters omitted` text anywhere in the file.

Passing after the fix: the assembled handoff contains
`[...N characters omitted, truncated for this handoff snapshot]` naming the exact
omitted count.

Diff summary: `_read_head` now compares the full read length against `limit_chars` and
appends an explicit marker naming the omitted character count when it truncates,
mirroring `_response_digest`'s existing `"[...%d characters omitted]"` style. One
function; its four call sites in `cmd_handoff` (Overview.md, Open-Items.md, latest
session log, OUTCOMES.md) all inherit the fix without being touched.

## Finding 8: fence-lint shows at most eight fences, no count of how many are hidden

FIXED.

Test: `TestFenceLintDisclosesHiddenFences.test_more_than_eight_live_fences_names_the_total`
(12 ephemeral store claims over 12 distinct files, rendered into STATE.md via
`bs.write_state_view`).

Note on the test itself: my first draft asserted the bare substring `"12"` appeared in
the output, which is not a safe assertion against this output shape (the printed lines
embed random 32-hex-character lifecycle uuids, and two adjacent hex digits
coincidentally spelling "12" across 8 of them is not vanishingly unlikely) — it passed
against the pre-fix code by coincidence on the first run. I caught this by re-running
it and inspecting the raw pre-fix output directly, rewrote the assertion to the exact
structured phrase the real fix produces (`"12 live fences total"`, `"4 more not
shown"`), and reran three times to confirm it now fails reliably pre-fix.

Failing output before the fix (after the rewrite): stdout contained exactly 8 `- rec0N
(...)` lines and nothing else; neither phrase was present.

Passing after the fix: stdout contains `... 4 more not shown (12 live fences total)`.

Diff summary: `cmd_fence_lint` now prints one extra line after the `hits[:8]` loop when
`len(hits) > 8`, naming both the hidden count and the true total. One `if` block, one
print.

## Finding 9: check-update and intent have no command-level consent gate

FIXED.

Tests: `TestConsentGateOnCheckUpdateAndIntent` (three methods: no-consent for each
command, plus one confirming `intent` still works once consented).

Failing output before the fix:

    AssertionError: True is not false : check-update wrote installed-skill-version
    without consent
    AssertionError: True is not false : intent wrote into the vault without consent

Passing after the fix: with no consent config and `HOME` pinned to a throwaway
directory, neither command creates anything under the throwaway vault; `intent` prints
`bm_telemetry: setup is not complete yet; run: python3 scripts/setup.py`; with a
consented config, `intent` still writes exactly as before.

Diff summary: `cmd_check_update` gained `if not _consented(): return` as its first
statement (silent, matching `cmd_stop_warn`'s existing precedent for a hook-driven
command). `cmd_intent` gained the same check but prints the same explanatory sentence
`cmd_outcomes_append` already uses, since it is also typed by hand by a founder.
Grepped the repo for every caller of both commands (`main()`'s dispatch table and
`tools/bm_sessionstart.sh`); no other call site needed a change since both remain
callable exactly as before, just gated.

One existing test broke as a direct, foreseeable consequence and was fixed in the same
change: `TestRedaction.test_intent_redacts_secret_but_preserves_content` drove `intent`
without supplying a consent config, which is exactly the behaviour finding 9 closes.
Updated it to build a consented environment via the existing `_consented_env` helper
(the same fix shape `TestResumeBrief` already documents for `cmd_precompact_brief`'s
own earlier consent gate), with a comment pointing at this finding and at the new
no-consent tests that now cover the case that test used to accidentally cover.
Confirmed via `grep -n '"intent"' tools/test_bm.py` that this was the only other call
site.

Note per the spec: `intent` is also invoked by hand by a founder, so gating it changes
an interactive command's pre-setup behaviour; that is the intended outcome, named here
as the spec asked.

## Finding 10: a future-dated session vanishes from both speed windows

FIXED.

Test: `TestSpeedDisclosesFutureDatedSessions.test_a_future_dated_session_is_named_not_just_dropped`
(one row now, one row timestamped 5 hours in the future).

Failing output before the fix: `speed`'s stdout showed only the one current-dated
session in `last 7d`; the future-dated 5000-token session was in neither window and
nothing in the output said so.

Passing after the fix: stdout contains
`NOTE: 1 session(s) have a timestamp ahead of the clock ... excluded from both windows above.`

Diff summary: `cmd_speed` computes `future = [r for r in rows if (age_days(...) or 0) < 0]`
after the existing window printing and prints one disclosure line naming the count when
non-empty. No change to which rows land in which window (per the finding's own note
that this is not an everyday path); disclosure only.

## Finding 11: scorecard prints the Python literal `None` for a missing average

FIXED.

Test: `TestScorecardNeverPrintsAvgNone.test_no_attributed_ratings_prints_no_data_not_avg_none`

Failing output before the fix: stdout contained `avg=None` (visible directly in the
finding 2 probe's captured output too, independently: `4 alignment : ratings=0
avg=None ...`).

Passing after the fix: stdout contains `avg=no data`, never `avg=None`.

Diff summary: one new local `avg_txt = ("%.2f" % avg_rating) if avg_rating is not None
else "no data"` before the metric-4 print, matching metric 9's existing
`("%.1f%%" % ratio) if ratio is not None else "no data"` pattern exactly. The print's
format substitution changed from `avg_rating` to `avg_txt`; no other line touched.

## Done-check

    $ python3 tools/test_bm.py
    ----------------------------------------------------------------------
    Ran 256 tests in 103.434s

    OK (skipped=1)

Exit code 0 (captured via `$?` immediately after the run). 256 tests is the 242-test
baseline measured at the start of this session plus the 14 new test methods added
across the eleven findings (1: 1, 2: 1, 3: 2, 4: 1, 5: 1, 6: 1, 7: 1, 8: 1, 9: 3,
10: 1, 11: 1).

    $ git status --porcelain
     M docs/KNOWN-LIMITS.md
     M docs/NOT-FINALIZED.md
     M docs/closure/reports/2026-08-04-W-2-record-corrections.md
     M tools/bm_telemetry.py
     M tools/test_bm.py
    ?? docs/closure/HANDOVER-2026-08-04-TO-A-NEW-MACHINE.md
    ?? docs/closure/reports/2026-08-04-N-5-open-defect-triage.md

This does not name only my three fenced files. I did not write any of the other five:
`docs/KNOWN-LIMITS.md`, `docs/NOT-FINALIZED.md`,
`docs/closure/reports/2026-08-04-W-2-record-corrections.md`,
`docs/closure/HANDOVER-2026-08-04-TO-A-NEW-MACHINE.md`, and
`docs/closure/reports/2026-08-04-N-5-open-defect-triage.md` are other agents' concurrent
work in this multi-writer program, outside my fence and never opened or edited by me
this session. `git diff --stat -- tools/bm_telemetry.py tools/test_bm.py` confirms my
own scope: 2 files changed, 580 insertions(+), 21 deletions(-), both files on my WRITE
list, plus this report (new, also on my WRITE list).

## Findings attempted, fixed, not fixed

Findings attempted: 11. Findings fixed: 11. Findings not fixed: 0.

Finding 5 is fixed but with a scope deviation from the spec's own stated smallest fix,
documented above under that finding: the spec's "export a shared prefix constant from
tools/bm_store.py" was not implementable inside my write fence, so the fix stays
entirely inside tools/bm_telemetry.py via a different technique (direct SQL query
against the store instead of parsing verify()'s prose) that closes the same defect
without touching a file outside my fence.

## Suggestions (not applied, out of scope for this pass)

- `cmd_speed`'s "future-dated" disclosure (finding 10) and `cmd_scorecard`'s
  "unattributed" ratings both print `None`-adjacent honest labels in slightly
  different styles (`"no data"` vs a full sentence); a shared small helper for
  "labelled absence" text would reduce the chance of a twelfth `avg=None`-shaped bug
  appearing in a new metric later. Not done here: it would touch every metric's print
  line for a purely cosmetic consistency gain, well past what any of the eleven
  findings asked for.
- `_coordination_collisions`'s new direct-SQL implementation (finding 5) duplicates the
  overlap-pair-counting loop `tools/bm_store.py:verify()` already has. If bm_store.py
  ever comes into a future fix's write fence, moving both to share one small public
  helper in bm_store.py (e.g. `count_active_overlaps(root)`) would remove the
  duplication entirely and be a smaller, more direct fix than either the constant-export
  or the SQL-duplication path taken here.
