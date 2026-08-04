# The authoritative findings list for tools/bm_telemetry.py, N-6 telemetry audit, 2026-08-04

Status: CURRENT as of 2026-08-04.

This file replaces the instruction to "enumerate the thirteen findings from the audit
document". No such document exists in the tree. `docs/REMAINING.md` item 1 says "roughly
thirteen of the original audit's findings live in it", and that sentence is the only
source of the number: it is an estimate, not an enumeration. What item 1 actually
enumerates is three findings, and all three are verified fixed below. The list here was
built by reading all 1,995 lines of the file and probing it, and the count is what the
evidence produced, not what the handover remembered.

Every finding below was reproduced against the real, unmodified
`/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_telemetry.py`. Every line number
was confirmed with grep, never typed from memory.

Probe isolation: every probe pinned `HOME`, `BROTHERMODE_VAULT` and `BROTHERSBE_VAULT` to
throwaway paths under `/private/tmp/n6-telemetry`, re-exported in each Bash call. Both
real stores were checked afterwards and are untouched: `/Users/khalil.maaouni/Documents/Kay
Vault` has the same mtime as before the session (1785428435), and
`find /Users/khalil.maaouni/BrotherModeVault -newermt "2026-08-04 15:50"` returns nothing.

## Leads verified, not findings

These three are the leads this brief carried in. Each is FIXED. Per the probe-sensitivity
law, each fixed verdict is backed by a reinjection: the defect was put back into a
throwaway copy under `/private/tmp` and the same probe was rerun, to prove the probe can
see the defect when it is present.

**Lead (a), project identity computed from the current folder. FIXED.**
`_project_of` at line 1465 resolves the project root via `_resolve_root_quiet`;
`_legacy_project_of` at line 1452 is the stated legacy fallback. Probe: run `intent` from
three folders of one project and count the identity files produced.

    real file:            1 distinct identity file for 3 folders
      intent-proj-7fb5d2.log
    reinjected defect (_project_of returns _legacy_project_of):
      intent-deep-bd964b.log
      intent-docs-dda718.log
      intent-proj-7fb5d2.log
                          3 distinct identity files for 3 folders

The probe detects the defect when present and does not fire on the real file. See finding
4 for the condition under which this fix silently stops holding.

**Lead (b), the hardcoded "collisions=0, baton drops=0" literal. FIXED, and the number
genuinely moves.** `_coordination_collisions` at line 859 reads `bm_store.verify()`. The
literal survives only inside that function's explanatory comment at line 862 and nowhere
else in any .py file. A comment claiming a metric moves is not evidence that it moves, so
the probe forced the invariant the metric counts. The store's `claim` command refuses an
overlapping claim, so the overlap was written straight into the sqlite, which is the state
`verify()` exists to catch:

    no overlap:      7 coordination : ... collisions=0 (bm_store.verify() at ...)
    forced overlap:  7 coordination : ... collisions=1 (bm_store.verify() at ...)
    reinjected literal, same forced overlap:
                     7 coordination : floor gate; collisions=0, baton drops=0

The number moved 0 to 1 on real data and could not move on the reinjected copy. See
finding 5 for how it can silently stop moving.

**Lead (c), malformed ledger lines silently discarded by a maintenance rewrite. FIXED.**
`read_jsonl` at line 791 reports bad line numbers, `atomic_backup` at line 820 copies raw
bytes, and `cmd_migrate` (line 686) and `cmd_dedup` (lines 744 to 748) both report. Probe:
run `migrate` over a ledger whose middle line is truncated, then ask whether the corrupt
evidence is still recoverable.

    real file:  migrate: 1 malformed line(s) ... the exact original bytes are preserved
                at ...outcomes.jsonl.bak-migrate20260804, nothing was deleted.
                PROBE RESULT: preserved
    reinjected pre-fix backup (re-serialize parsed rows) with the report removed:
                migrate: 2 lines, 0 migrated to schema 2, count ok (2)
                PROBE RESULT: LOST

The probe detects the defect when present. Findings 2 and 3 are the parts of this class
the fix did not reach.

## Findings

### 1. A single JSON null in a token field destroys the entire scorecard

A ledger row that parses as valid JSON but carries `null` (or a string) where a token
count belongs makes `fld` at line 123 return that value unchanged, `out7` at line 897
raise TypeError, and the blanket handler at line 1990 swallow it. The founder gets one
cryptic line instead of all nine metrics. `read_jsonl`'s malformed-line reporting cannot
help: the row parses fine, so it is never counted as bad.

Evidence: `tools/bm_telemetry.py:123`, `:897`, `:1990`. Probe, two ledger rows, the second
with `"gen_ai.usage.output_tokens":null`:

    $ bm_telemetry.py scorecard
    bm_telemetry: swallowed error (never blocks): TypeError("unsupported operand
      type(s) for +: 'NoneType' and 'int'")
    EXIT=0
    # control, same ledger with null replaced by 0:
    BROTHERMODE SCORECARD  (mechanical fields computed; ...)
    ledger: 2 sessions, 2 last 7d, 1k out last 7d, ...

Disposition: FIX. Test that would fail without it: write a ledger with one null token
field, run `scorecard`, assert stdout contains "BROTHERMODE SCORECARD" and does not
contain "swallowed error".

Covering test file: `tools/test_bm.py` (confirmed present with ls). Note that `grep -c -i
scorecard tools/test_bm.py` returns 0, so no test drives the scorecard at all today.

Blast radius: small and local. Coerce non-numeric values to 0 inside `fld`, or make the
numeric sums defensive. One function, no callers change.

### 2. Malformed lines in signals.jsonl are silently excluded, and excluded from the malformed-line warning itself

`cmd_scorecard` reads five ledgers. Four are read with `report_bad=True` and feed the
WARNING line. `signals` at line 892 is read without it. A corrupt signals line therefore
lowers the rework and escaped-defect counts, which feed metric 4 (alignment) and metric 6
(honesty), and the warning that exists to disclose exactly this says nothing.

Evidence: `tools/bm_telemetry.py:892` against `:887`, `:889`, `:890`, `:891`. Probe, three
signal lines with the middle one truncated:

    ledger: ... 1 rework signal(s), 1 escaped defect(s)     <- no WARNING printed
    # control, same three lines all well formed:
    ledger: ... 2 rework signal(s), 1 escaped defect(s)
    # contrast, the identical corruption in corrections.jsonl:
    WARNING: 1 malformed ledger line(s) could not be parsed ... corrections=1

The honesty metric loses a count without saying so, which is the failure mode the
honesty metric is for.

Disposition: FIX. Test that would fail without it: corrupt one line of signals.jsonl, run
`scorecard`, assert the WARNING line appears and names signals.

Covering test file: `tools/test_bm.py` (confirmed present with ls).

Blast radius: one line, plus widening the WARNING format string. No behaviour changes for
a clean store.

### 3. `speed` and `startup-nags` report numbers with no malformed-line disclosure at all

The fix for lead (c) landed on `scorecard`, `migrate` and `dedup`. `cmd_speed` (line 774)
and `cmd_startup_nags` (line 1124) both call `read_jsonl(LEDGER)` without `report_bad`, so
they publish session counts, span-hours and token sums computed over a silently reduced
ledger. The same file read by two commands produces one warning and one confident silence.

Evidence: `tools/bm_telemetry.py:774` and `:1124`. Probe, one ledger of three rows with
the middle one truncated, all three commands run against it:

    $ bm_telemetry.py speed
      last 7d : 2 sessions, 3.0 span-h, 3k out, 0 recorded runs -> no runs recorded
    $ bm_telemetry.py startup-nags
    BROTHERMODE SPEND: last 24h 3k out tokens across 2 sessions.
    $ bm_telemetry.py scorecard
    WARNING: 1 malformed ledger line(s) could not be parsed ... ledger=1 ...

Disposition: FIX. Test that would fail without it: corrupt one ledger line, run `speed`
and `startup-nags`, assert each names the dropped line count.

Covering test file: `tools/test_bm.py` (confirmed present with ls).

Blast radius: two call sites plus one print each. Contained.

### 4. The project-identity fix silently reverts to the pre-fix defect whenever bm_store.py cannot be loaded

`_resolve_root_quiet` at line 1438 returns `(None, None)` on any exception, and
`_project_of` at line 1477 then falls back to `_legacy_project_of`, which is the exact
per-folder formula the 2026-07-26 round removed. Nothing is printed.
`_migration_pointer` cannot catch it either, because it returns early when the legacy and
new identities are equal, and under this fallback they always are. `_vault_project_name`
(line 1483) and `_coordination_collisions` (line 859) degrade through the same helper.

This matters because it is a silent degradation in a file whose own law is that
degradation must be labelled: `scan_corrections` marks its degraded rows `degraded: true`
and records the reason, and the docstring at line 506 to 509 states that the honest form
of never blocking is a labelled degradation, not a silent one.

Evidence: `tools/bm_telemetry.py:1438`, `:1477`, `:1483`. Probe: a copy of `tools/`
whose `bm_telemetry.py` is byte-identical to the repo copy (verified with `cmp`), with
only the sibling `bm_store.py` made unimportable:

    bm_telemetry.py identical to repo copy: YES
    $ intent from 3 folders of one project
      stdout: intent logged   (x3, no warning on stdout or stderr)
      intent-deep-bd964b.log
      intent-docs-dda718.log
      intent-proj-7fb5d2.log
    PROBE RESULT: 3 distinct identity files for 3 folders

That is the same output as the reinjected-defect run in lead (a), produced by unmodified
code.

Disposition: FIX. Test that would fail without it: point the loader at an unimportable
bm_store, call `_project_of` twice from two subfolders of one project, assert the
identities match or that a degradation notice was emitted.

Covering test file: `tools/test_bm.py` (confirmed present with ls).

Blast radius: contained, but it needs a decision on which way to degrade. Emitting a
labelled notice is the smaller change and matches the file's existing pattern. This does
not require splitting the file.

### 5. The coordination metric is coupled to bm_store.verify()'s prose, so a wording edit silently restores a permanent zero

Line 883 counts problems with `p.startswith("active claims overlap")`. That string is
built in `tools/bm_store.py:12093`. Rewording that message, an ordinary edit with no
apparent contract, drops the count to 0 while `verify()` still reports the problem. The
honest `NOT MEASURED` branch is not reached: it only fires when the module or the root
cannot be resolved, never on prose drift, so the scorecard prints a confident
`collisions=0` beside a real, currently-detected collision. That is the unmovable number
of the original finding returning through the back door.

Evidence: `tools/bm_telemetry.py:883` against `tools/bm_store.py:12093`. Probe: a copy
whose `bm_telemetry.py` is byte-identical to the repo copy (verified with `cmp`), with only
the message in `bm_store.py` reworded, run against a store holding a real forced overlap:

    bm_telemetry.py byte-identical to repo: YES
    $ bm_store.py verify
    verify: 1 problem(s) found:
      - overlapping active claims: 'writerA' (efd867f5) path 'shared.py' vs 'writerB' ...
    $ bm_telemetry.py scorecard
    7 coordination  : floor gate; collisions=0 (bm_store.verify() at ...)

Compare the lead (b) transcript above, where the unmodified pair reports `collisions=1` on
the same store.

Disposition: FIX. Test that would fail without it: assert that the prefix
`bm_telemetry.py` matches is the one `bm_store.py` actually produces, by generating a real
overlap and asserting the count is non-zero, so a rewording breaks the test rather than
the metric.

Covering test file: `tools/test_bm.py` (confirmed present with ls).

Blast radius: small if the fix is a shared constant or a structured problem code in
`bm_store.py`. Touching `bm_store.py` puts a second file in scope, so keep the change to
exporting the prefix rather than reshaping `verify()`'s return type.

### 6. Correction capture silently drops everything past eight per session, and keeps the oldest

`CORRECTION_CAP_PER_SESSION = 8` at line 464 and the `break` at line 528 stop capture at
eight, with no record that more existed. Because the loop breaks rather than keeping a
window, the messages retained are the EARLIEST eight, so the founder's most recent
corrections in a long session are the ones lost. The printed summary reports the number
captured as though it were the number found.

This sits directly against the docstring at lines 491 to 504, which records that the Loop
4 redesign was driven by corrections being dropped SILENTLY and states that "length no
longer drops anything". The length cap was removed; the count cap still drops, still
silently.

Evidence: `tools/bm_telemetry.py:464`, `:528`. Probe: a synthetic transcript with twelve
distinct founder corrections, driven through `outcomes-append` with consent granted in a
throwaway HOME:

    bm_telemetry: recorded sess-cap (0k out, 12 tools, 0.2h, 8 correction candidates)
    corrections actually captured: 8 of 12 sent
    which survived: Correction number 1 2 3 4 5 6 7 8
    (nothing in stdout indicates four were dropped)

Disposition: FIX. Test that would fail without it: feed twelve corrections, assert the
printed line discloses the cap and the number not captured.

Covering test file: `tools/test_bm.py` (confirmed present with ls). Note that
`grep -c -i -E "CORRECTION_CAP|correction cap|cap_per_session" tools/test_bm.py` returns 0,
so the cap is untested today.

Blast radius: small. Disclosing the drop is a print change. Changing WHICH eight are kept
is a behaviour change and should be decided separately from the disclosure.

### 7. The handover export truncates the vault silently, mid-line, at 6000 characters

`_read_head` at line 1835 caps at 6000 characters by default and adds no marker.
`cmd_handoff` uses it for Overview.md and Open-Items.md at that default, for the latest
session log at 4000, and for OUTCOMES.md at 20000. The resulting file tells the teammate
it is "a snapshot, not the living record" but never that it is cut. Anything past the cap
is invisible to the recipient and to the founder reviewing before sharing.

Evidence: `tools/bm_telemetry.py:1835` and the `cmd_handoff` call sites. Probe: an
Overview.md of 13,240 bytes with a load-bearing line at the end:

    $ bm_telemetry.py handoff acme
    handoff written (secret-redacted): .../handoff-acme.md
    review it before sharing; it is a snapshot, redaction is best-effort.
    contains the fact at the end of Overview.md: 0
    says anywhere that it truncated:            0
    last line as shipped:  Line 0137            <- cut mid-line

Disposition: FIX. Test that would fail without it: hand off a project whose Overview.md
exceeds the cap, assert the output contains an explicit truncation marker naming the
omitted character count, in the style `_response_digest` at line 221 already uses.

Covering test file: `tools/test_bm.py` (confirmed present with ls, and it already contains
handoff tests).

Blast radius: small. `_read_head` gains a marker and its four callers inherit it.

### 8. fence-lint shows at most eight live fences and does not say how many it hid

Line 1295 prints `hits[:8]`. This is the command whose stated job, in its own docstring at
line 1248, is that "no writer launches into an occupied file set". With more than eight
live fences, the ninth onward are not shown and no count is printed, so a dispatcher
reading the output can conclude a file set is free when a fence over it exists.

Evidence: `tools/bm_telemetry.py:1295`. Probe: a STATE.md with twelve live
store-rendered records under `## active`:

    LIVE FENCES (fence-then-dispatch; overlap means queue):
      STATE.md: - writer01 ... owner-session: s01
      ... through writer08 ...
    fences actually shown: 8 of 12

Disposition: FIX. Test that would fail without it: render more than eight live fences,
assert the output states the total or the number suppressed.

Covering test file: `tools/test_bm.py` (confirmed present with ls). This path already has
coverage to extend: `test_fence_lint_sees_a_live_store_rendered_claim` at
`tools/test_bm.py:5940`. It asserts that a live record is seen, never how many are shown,
which is why the cap slipped past it.

Blast radius: one print. Trivial.

### 9. Two vault-writing commands have no command-level consent gate, and the guard test built to prevent this cannot see them

`cmd_check_update` creates the vault telemetry directory at line 1389 and writes
`installed-skill-version`. `cmd_intent` writes a per-project log through
`atomic_append_text`. Neither calls `_consented()`. Both materialize the vault in a
stranger's home before setup has run.

Today they are protected only because `tools/bm_sessionstart.sh` checks consent at line 18
before invoking them at lines 24 and 25. That is a gate on the hook line, and this file's
own docstring at lines 1586 to 1588 records why that placement is wrong: the PreCompact
line runs two programs off one payload, the earlier fix gated the first, "which is
precisely why the gate belongs on the command rather than on the hook line".

The guard built to stop the class reopening has the same shape of blind spot as the escape
it was built for. `docs/KNOWN-LIMITS.md` lines 746 to 748 state that an inventory test
"reads hooks/hooks.json and fails if any hook-wired bm_telemetry.py command lacks a consent
check". `check-update` and `startup-nags` are wired from `bm_sessionstart.sh`, not from
`hooks/hooks.json`, so the inventory never enumerates them.
`grep -rn "check-update\|startup-nags" tools/test_bm.py tools/test_bm_consent.py` returns
nothing at all.

Evidence: `tools/bm_telemetry.py:1344`, `:1389`, `:1544`; `tools/bm_sessionstart.sh:18`,
`:24`, `:25`; `tools/test_bm_consent.py:50`, `:569`. Probe: a fresh HOME with no consent
config, vault pinned to a path that does not exist:

    consent config present? NO      vault exists before? NO
    $ stop-warn      (gated)   -> vault created: NO
    $ check-update   (ungated) -> vault created: YES
                                  wrote: .../99-System/telemetry/installed-skill-version
    $ intent "..."   (ungated) -> wrote: .../99-System/telemetry/intent-...-641d04.log

Disposition: FIX. Test that would fail without it: extend the inventory to every
bm_telemetry.py command invoked anywhere in the shipped hook surface, `hooks/hooks.json`
and `tools/bm_sessionstart.sh` both, and assert each checks consent.

Covering test file: `tools/test_bm_consent.py` (confirmed present with ls).

Blast radius: two `_consented()` calls plus widening one test's input set. Note that
`intent` is also invoked by hand by a founder, so gating it changes an interactive command's
behaviour before setup; that is the intended outcome but worth naming.

### 10. A future-dated session vanishes from both speed windows while the scorecard still counts it

`cmd_speed` at line 776 filters with `lo <= (age_days(...) or 999) < hi`. A row whose
timestamp is ahead of the clock yields a negative age, which fails `0 <= age` and also
fails the prior-window test, so the row appears in neither window and nothing says so.
`cmd_scorecard` at line 896 uses `<= 7` with no lower bound and counts the same row. Two
commands reading one file disagree about how many sessions it holds.

Evidence: `tools/bm_telemetry.py:776` and `:896`. Probe: two rows, one two hours old and
one timestamped two hours in the future:

    $ bm_telemetry.py speed
      last 7d : 1 sessions, 1.0 span-h, 1k out, ...
      prior 7d: 0 sessions, 0.0 span-h, 0k out, ...
      (the 5000-token, 5.0h future-dated session is in neither window)
    $ bm_telemetry.py scorecard
    ledger: 2 sessions, 2 last 7d, 6k out last 7d, ...

Reachability, stated plainly: this needs clock skew, a hand-edited timestamp, or a
restored backup from a machine whose clock was ahead. It is not an everyday path.

Disposition: FIX. Test that would fail without it: write a future-dated row, assert
`speed` either counts it or names it as excluded.

Covering test file: `tools/test_bm.py` (confirmed present with ls).

Blast radius: one comparison, or one disclosure line. Small.

### 11. The scorecard prints the Python literal None where it has no rating data

Line 908 leaves `avg_rating` as `None` when there are no attributed ratings, and line 937
formats it with `%s`, so the alignment metric reads `avg=None`. Metric 9 on line 954
handles the identical situation correctly and prints `no data`. This is the smallest
finding here and it is included because it is the same class the file is otherwise strict
about: a slot that should read as absent instead reads as a value.

Evidence: `tools/bm_telemetry.py:908`, `:937`, against `:954`. Observed verbatim in the
finding 2 probe output:

    4 alignment     : ratings=0 avg=None (unattributed=0, never averaged), ...
    9 cache economy : warm-read ratio 7d=no data (...)

Disposition: FIX. Test that would fail without it: run `scorecard` with no attributed
ratings, assert the output does not contain the string `avg=None`.

Covering test file: `tools/test_bm.py` (confirmed present with ls).

Blast radius: one format expression. Trivial.

## What was checked and produced nothing, stated so it is not mistaken for unexamined

- The falsy-zero trap in `(age_days(...) or 999)` looked like a defect on reading: an age
  of exactly 0.0 is falsy and becomes 999. It was probed and is NOT reported as a finding,
  because it is unreachable. `age_days` returns 0.0 only when the current time matches a
  second-precision timestamp to the microsecond: 414,086 attempts in 3 seconds produced 0
  hits. Reporting it would be exactly the alibi-by-weak-evidence this project's records
  warn about, run in reverse. Finding 10 is the reachable half of that same expression.
- `docs/KNOWN-LIMITS.md` and `docs/NOT-FINALIZED.md` were searched for every finding above
  before it was written down, so that nothing deliberate is reported as a defect. There
  are zero hits in either file for the correction cap, the handoff truncation, fence-lint,
  signals.jsonl, the 6000-character head, or the collision count. None of these eleven is
  a declared limit.
- `outcomes.jsonl` is written at mode 0644 while ratings, corrections and signals are
  0600. This is deliberate and documented in the file at lines 191 to 195, so it is not a
  finding.

## Scope guard

No finding above requires splitting `tools/bm_telemetry.py`. Every proposed fix is local
to one function or one print statement, except finding 5, whose smallest correct fix
exports a prefix constant from `tools/bm_store.py`. No founder decision on a split is being
requested, and none should be inferred from this report.

## Not covered by this audit

- `docs/BrotherMode_V2_Post_Audit_Execution_Loops.md` exists (confirmed with ls, 1,920
  lines) and was not read in full; it was not needed to construct this list, which is built
  from the code.
- `tools/test_bm.py` is 6,055 lines and was searched by keyword rather than read end to
  end, so the coverage counts quoted per finding are grep results, not a reading of every
  test.
- `python3 tools/test_all.py` was NOT run; the orchestrator owns it. No claim here depends
  on a suite result.
- The four responsibilities were audited from the source and from behavioural probes. Rare
  concurrency behaviour (two SessionEnd hooks appending at the same instant) was not
  probed.

## Done-check

Confirmation 1, dispositions. Eleven findings, eleven dispositions, each exactly one of
the two permitted words. All eleven are FIX. Zero are LIMIT. No third option appears.

Confirmation 2, covering test files. Every FIX names a test file confirmed present with
ls, in this session:

    -rw-r--r--  333664 Aug  4 14:07 tools/test_bm.py
    -rw-r--r--   56937 Aug  4 08:48 tools/test_bm_consent.py

Findings 1 through 8, 10 and 11 name `tools/test_bm.py`. Finding 9 names
`tools/test_bm_consent.py`. Both exist.

Total findings: 11.
