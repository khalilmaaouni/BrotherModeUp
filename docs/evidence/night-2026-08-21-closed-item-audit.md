# Closed-item audit: a sample of QUEUE.json's "done" state, re-checked

Status: CURRENT
Date: 2026-08-21, audit agent, read-only, BrotherModeUp repository, HEAD at
d8911c9 for the whole run (git status clean throughout)

## Why this exists

Twice tonight an item recorded CLOSED or RETIRED turned out to be open, and
both were found by accident: M14 was retired on evidence about
`bm_fence_hook.py` while M14 itself names `sbe_fence_hook.py`, a different
plugin's hook; M16 was described as held by a merged branch when that branch
had only carried the queue entry, not a fix. Both wrong verdicts had been
copied forward into later documents as settled fact. This audit re-checks a
sample of the OTHER items marked "done" in `docs/plan/QUEUE.json`, against
their own recorded `done_check`, to see whether the same failure mode
(evidence about the wrong thing, or no evidence at all, standing in for a
verdict) recurs elsewhere. It does not touch M14 or M16 themselves: both are
already `"state": "queued"` at HEAD, correctly reopened by tonight's earlier
work.

## What was audited and how the sample was chosen

`docs/plan/QUEUE.json` holds 119 items; 50 are `"state": "done"` (the task
brief estimated "roughly 47"; the exact count, read directly, is 50).
Counted with:

```
python3 -c "
import json
q = json.load(open('docs/plan/QUEUE.json'))
items = q['items']
done = [i for i in items if i.get('state') == 'done']
print('TOTAL ITEMS:', len(items)); print('DONE ITEMS:', len(done))
"
```
Output: `TOTAL ITEMS: 119` / `DONE ITEMS: 50`.

14 items were selected for full audit (10 to 15 was the target). Selection
method, in order:

1. **Recency first.** `git log --follow` on `docs/plan/QUEUE.json`, diffed
   commit by commit to find every `state` transition to `"done"`, shows the
   most recent closures cluster on 2026-08-19 through 2026-08-21, an the
   M-series items (M2 through M28) are almost all in that window. This is
   both the most recent work and, by naming ("M" for a mandate/measurement
   series), the same family that produced M14 and M16.
2. **Family match.** Per the brief's own instruction, items whose title
   names a control, a check, a hook, a gate, or a verdict were prioritized,
   because that is the family that failed twice tonight. Nearly the entire
   M-series qualifies (fence hooks, doctor checks, verify-close verdicts,
   registry reconciliation, a write-site scanner).
3. **Runnable done_check.** Only items whose `done_check` names or implies
   an actual command, test class, or reproducible fixture were selected.
   Items whose `done_check` is pure prose with no runnable command (for
   example M8's "scripted walkthrough test", not independently confirmed to
   exist before selection) or that need a founder action were left out of
   the 14, per the instruction not to pad the count with items that cannot
   be evaluated.
4. One item outside the M-series (O15) was added deliberately, to check
   whether the pattern is M-series-specific or wider, and because its
   done_check is a single, cheap, directly runnable command.

The 14: M2, M4, M6, M9, M10, M11, M12, M15, M17, M19, M25, M27, M28, O15.

## SUMMARY TABLE

| id | verdict | one-line reason |
|---|---|---|
| M2 | CONFIRMED CLOSED | hollow-delivery refusal test passes; done_check names a test class that does not exist verbatim, but the equivalent test does and is green |
| M4 | CONFIRMED CLOSED | exact named test passes |
| M6 | CONFIRMED CLOSED | both named behaviors pass |
| M9 | **STILL OPEN** | the successor-pointer mechanism the item's own title and done_check describe does not exist in the code at all; live reproduction confirms the forbidden "bare OWED" still fires today |
| M10 | CONFIRMED CLOSED | both named tests pass |
| M11 | CONFIRMED CLOSED | all 4 named cases pass; code read confirms no second implementation |
| M12 | CONFIRMED CLOSED | test drives the actually-installed BrotherSBE copy directly, not a decoy; passes |
| M15 | CONFIRMED CLOSED, with a caveat | the real question was answered rigorously, but the done_check's own stated precondition ("with M14 fixed") is false; the measurement worked anyway via a different, valid route |
| M17 | CONFIRMED CLOSED | all 5 tests pass, including the exact schema-ahead-of-installed-hook scenario named |
| M19 | CONFIRMED CLOSED | all 4 tests pass |
| M25 | CONFIRMED CLOSED | named test passes |
| M27 | CONFIRMED CLOSED | named test passes |
| M28 | CONFIRMED CLOSED, with a caveat | named test passes, but the item's own title text ("left unfixed on purpose") contradicts the landed fix |
| O15 | CONFIRMED CLOSED, with a caveat | the literal done_check ("doctor reports check 9 PASS") is true today, but check numbering has drifted since 2026-08-15 and "check 9" no longer means what O15 was filed about |

11 CONFIRMED CLOSED clean, 3 CONFIRMED CLOSED with a caveat worth flagging, 1
STILL OPEN, 0 CANNOT VERIFY (by selection: see the method above).

---

## M9 - STILL OPEN (the headline finding)

**Item text, verbatim.** Title: "the progress-page check reports OWED
forever on a page that was deliberately frozen: it compares mtimes and
cannot follow the pointer GANTT.html carries to COMMAND-CENTER.html, so
every session is told to refresh a retired record." Files:
`tools/bm_progress_check.py`. done_check: "a page carrying an explicit
successor pointer reports the successor's freshness, or reports NO-DATA
naming the pointer it could not resolve, never a bare OWED."

**What it names.** A specific mechanism: the tool must READ a pointer a
frozen page carries to its successor, and either report the successor's own
freshness or NO-DATA naming the unresolved pointer. Never a bare OWED.

**Code read.** `tools/bm_progress_check.py` is 287 lines, read in full.
`grep -n "successor\|pointer\|COMMAND-CENTER\|frozen" tools/bm_progress_check.py tools/test_bm_progress_check.py`
returns zero matches, in either file. The tool has exactly four verdicts
(NO-PLAN, CURRENT, OWED-MISSING, OWED-STALE) and one piece of real logic
beyond mtime comparison: when several files match the page-name glob at
once, it names the ones it did NOT judge (`check_status`, lines 204-220).
That logic is tagged "M9" in its own comment (line 205), and it is a real,
useful, tested fix for a different bug (silent wrong-file pass on
ambiguous matches). It contains no code path that reads a page's own text,
follows a reference to another filename, or evaluates a "successor" file's
mtime.

**Live reproduction (command run, this session, against the actual shipped
tool, no repository file touched):**

```python
import os, subprocess, sys, tempfile, io
EARLIER = 1700000000
LATER = 1700010000
with tempfile.TemporaryDirectory() as tmp:
    # Frozen page (GANTT.html), deliberately old, carrying a pointer in its
    # own text to a successor page that is actually fresh -- M9's literal
    # scenario.
    frozen = write("docs/plan/GANTT.html",
        "<html>FROZEN. See successor: docs/plan/COMMAND-CENTER.html</html>")
    stamp(frozen, EARLIER)
    successor = write("docs/plan/COMMAND-CENTER.html", "<html>the live board now</html>")
    stamp(successor, LATER)
    plan = write("docs/plan/RELEASE-PLAN.md")
    stamp(plan, EARLIER + 5000)
    r = subprocess.run([sys.executable, "tools/bm_progress_check.py",
                         "status", "--root", tmp], ...)
    print("EXIT:", r.returncode); print("STDOUT:", r.stdout.strip())
```

**Verbatim output:**
```
EXIT: 1
STDOUT: progress page: OWED (stale). docs/plan/GANTT.html (2023-11-15 07:13:20) is older than the plan docs/plan/RELEASE-PLAN.md (2023-11-15 08:36:40). Refresh the page.
STDERR:
```

This is exactly the forbidden outcome the done_check names: a bare OWED,
with the successor never consulted and no NO-DATA naming an unresolved
pointer. `COMMAND-CENTER.html` does not even match `PAGE_GLOBS` (it
contains neither "GANTT" nor "BOARD"), so even the unrelated M9
ambiguity-naming fix would never surface it as a candidate.

**Why this happened, found in the commit history (not a guess).** The
`state: done` transition landed at commit `f7aa2a0` (2026-08-19), whose
commit message says plainly: "M3 and M9 are marked done; both landed
tonight with their tests." The actual code commit is `61258fa`
("M9: the progress check stops resolving four candidate pages into one
silent pass"), whose message is honest about the substitution: "M9 as
filed was no longer reproducible... GANTT.html was rewritten on 17 August
and no longer declares itself frozen, so the OWED-forever symptom is gone.
Fixing a symptom that no longer exists would have been the easy wrong
move. The underlying defect survived the symptom... [FOUR files match the
page patterns, the check judged the newest silently]." The session then
built and shipped the ambiguity-naming fix instead, judging it the better
response to the surviving defect class.

That may have been a reasonable call at the time. The problem is
narrower and more mechanical than second-guessing the judgment: **that
reasoning lives only in the git commit message.** `docs/plan/QUEUE.json`
itself, the file `tools/bm_idle.py` reads and nothing else per its own
schema comment, still carries the ORIGINAL title and done_check verbatim,
with `"state": "done"` and no `note` or `closed_note` field at all pointing
at 61258fa or explaining the substitution. Anyone reading QUEUE.json alone,
exactly the failure mode M14 and M16 already demonstrated tonight, would
reasonably conclude the successor-pointer mechanism was built. It was not,
and the reproduction above shows the original scenario still misbehaves
today, on the current tree, the moment a page again carries a
"frozen, see successor" shape.

**Verdict: STILL OPEN.** Not because the 2026-08-19 session lied or was
careless (it was unusually transparent, in the one place nobody reads
during a depth check), but because the mechanism the item's own
machine-readable record demands does not exist, and the record carries no
trace of the honest reason why.

---

## M11 - CONFIRMED CLOSED

done_check: "python3 tools/test_bm_fence_hook.py QueryVerb green:
tools/bm_fence_hook.py ships a `query PATH [--session-id ID]` verb that
calls decide(), the same function cmd_hook() calls, and QueryVerb pins its
verdict equal to decide()'s own verdict on four cases (unclaimed path
allow, foreign claim deny, own claim allow, unreadable store fail-open with
reason printed)."

Command: `python3 -m unittest tools.test_bm_fence_hook.QueryVerb -v`

Output (tail):
```
test_a_unclaimed_path_default_mode_is_allowed ... ok
test_b_path_claimed_by_another_session_is_refused ... ok
test_c_path_claimed_by_the_asking_session_is_allowed ... ok
test_d_unreadable_fence_state_fails_open_with_reason_printed ... ok
Ran 4 tests in 1.128s
OK
```

Code read: `cmd_query` (tools/bm_fence_hook.py:1293-1358) builds a
PreToolUse-shaped payload and calls `decide(p)` directly, the same function
`cmd_hook` calls; confirmed by reading both functions, not assumed from the
docstring. This item names `tools/bm_fence_hook.py` and the evidence is
about `tools/bm_fence_hook.py`: no wrong-component mismatch.

## M17 - CONFIRMED CLOSED

done_check: "point the check at a store one schema ahead of the installed
copy and observe FAIL rather than PASS, and confirm the pre-fix code passes
the same fixture so the test is not asserting something already true."

Command: `python3 -m unittest tools.test_bm.TestM17FenceLivenessAgainstRealStore -v`

Output (tail):
```
test_real_store_ahead_of_wired_hook_fails_not_passes ... ok
test_real_store_check_uses_the_wired_interpreter_not_sys_executable ... ok
test_store_path_as_a_dangling_symlink_is_reported_not_skipped ... ok
test_store_path_as_a_directory_is_reported_not_skipped ... ok
test_subdirectory_cwd_still_finds_the_real_store ... ok
Ran 5 tests in 29.894s
OK
```

The primary test builds a REAL project store with the current
`bm_store.py` (schema N) and a REAL, working, schema-(N-1) fence-hook copy
in an isolated temp tree, wires them via a real `settings.json`, and runs
`scripts/doctor.py` as a subprocess against that fixture, asserting
`FAIL`, not `PASS`. This is the exact scenario the item names (a THROWAWAY
store can never be behind itself; this fixture is not throwaway, it is a
real schema-ahead pair), and the test both proves the fix and (per its own
docstring) proves the pre-fix code would have wrongly passed the same
fixture.

## M19 - CONFIRMED CLOSED

done_check: "zip refreshes the board copy from the live board, or
verify-close FAILS naming the drift: edit docs/plan/GANTT.html after
skeleton, run zip, and confirm the archived copy's sha256 equals the live
board's; a regression test fails on the pre-fix capture-once behaviour."

Command: `python3 -m unittest tools.test_bm_handover -k m19 -v`

Output (tail):
```
test_m19_defect_one_skeleton_refuses_a_destination_symlink_too ... ok
test_m19_defect_one_zip_refuses_a_destination_symlink_before_write ... ok
test_m19_defect_two_a_committed_pack_going_stale_is_catchable ... ok
test_m19_zip_refreshes_a_board_copy_gone_stale_since_skeleton ... ok
Ran 4 tests in 1.439s
OK
```

The primary test (`test_m19_zip_refreshes_a_board_copy_gone_stale_since_skeleton`)
runs the exact sequence the done_check names: `skeleton`, edit
`docs/plan/GANTT.html` after the pack was generated, `zip`, then asserts
the archived `GANTT.html` inside the zip matches the LIVE board's content,
not the stale captured-at-skeleton-time copy. Two further tests are
outside-review follow-ups (symlink destination refused before write) that
harden the same fix.

## M12 - CONFIRMED CLOSED

done_check: "store claims render an agent-bearing fence line the INSTALLED
sbe reconcile parses; regression test drives the installed
read_declarations and fails on the pre-fix render; peer break-glass record
deleted in the same change."

Command: `python3 -m unittest tools.test_bm_store.TestM12StateMdFenceMatchesInstalledBrotherSbeParser -v`

Output (tail):
```
test_a_path_the_store_never_claimed_stays_undeclared ... ok
test_an_active_store_claim_is_declared_not_undeclared ... ok
Ran 2 tests in 0.219s
OK
```

This is the item most structurally similar to M14's failure shape (a
BrotherMode fix whose proof depends on a SIBLING plugin's INSTALLED code),
and it was checked accordingly. The test loads
`~/.claude/plugins/cache/brothersbe/brothersbe/3.2.0/tools/sbe_session_reconcile.py`
BY PATH (`importlib.util.spec_from_file_location`), the exact install path
the M14 evidence file independently confirmed via `claude plugin list` is
the copy Claude Code actually loads (`brothersbe@brothersbe`, enabled,
v3.2.0). Neither test was skipped (a skip would print "skipped", not "ok";
the harness's `skipTest` path for "installed copy not on this machine" was
not taken). A negative control
(`test_a_path_the_store_never_claimed_stays_undeclared`) rules out a fix
that just says "declared" to everything. No wrong-component mismatch.

## M10 - CONFIRMED CLOSED

done_check: "verify-close gives a real verdict to a claimless full pack via
the env-derived session path, typo guard kept; test green at the A3
commit."

Command: `python3 -m unittest tools.test_bm_handover -k m10 -v`

Output (tail):
```
test_m10_explicit_session_flag_still_refuses_an_unknown_id ... ok
test_m10_zero_claimed_records_with_a_full_pack_gets_a_real_verdict ... ok
Ran 2 tests in 0.319s
OK
```

The item's own title carries an embedded historical note, "[BLOCKED
2026-08-19: tools/bm_handover.py is under a live fence, FENCE F5...]".
That fence's live/released status as of tonight was NOT independently
re-derived by this audit (asking STATE.md directly would be re-deriving a
control's answer instead of asking it, the exact anti-pattern this
project's own memory warns against). It does not matter for this verdict:
the code fix and its tests exist and pass on the current working tree
right now, which is the fact in question. The BLOCKED note is a stale
historical marker inside the title text, not evidence against the fix.

## M2 - CONFIRMED CLOSED (test-name mismatch in the done_check text)

done_check: "a hollow project is refused by deliver naming its holes;
test_bm_project TestDeliverRefusesHollow green at the A3 commit."

`grep -n "DeliverRefusesHollow" tools/test_bm_project.py` returns nothing:
no test or class carries that exact name. The equivalent test exists under
a different name.

Command: `python3 -m unittest tools.test_bm_project -k "hollow" -v`

Output (tail):
```
test_deliver_refuses_a_hollow_project_even_when_every_task_is_closed
  (tools.test_bm_project.TestReleaseClosureLoop2RefuterFixes...) ... ok
Ran 1 test in 3.103s
OK
```

Read in full (tools/test_bm_project.py:754-810): the test walks a task
through all ten lifecycle states to "closed" with zero evidence filed,
confirms `deliver` refuses it naming "no goal", "no build evidence", "no
review", confirms no `DELIVERY-PACKET.md` is written on refusal, and
confirms `--partial` proceeds but still discloses the same holes. This is
the exact behavior the item describes; only the specific class name in the
done_check text does not exist verbatim. Flagged because it is the same
species of small drift (a record naming something slightly different from
what actually shipped) that made M14 harder to catch, even though here the
substance is right.

## M4 - CONFIRMED CLOSED

done_check: "already fixed pre-A3: BIRTH_STATES guard in cmd_task_add with
pinned test test_a_task_cannot_be_born_past_the_start_of_the_lifecycle,
verified green 2026-08-20."

Command: `python3 -m unittest tools.test_bm_project -k "test_a_task_cannot_be_born_past_the_start_of_the_lifecycle" -v`

Output (tail):
```
test_a_task_cannot_be_born_past_the_start_of_the_lifecycle
  (tools.test_bm_project.TestRefusals...) ... ok
Ran 1 test in 2.621s
OK
```

`BIRTH_STATES = ("planned", "ready")` at tools/bm_project.py:186, enforced
at line 1158 inside `cmd_task_add`. Exact named test, exact named guard,
both present and green.

## M6 - CONFIRMED CLOSED

done_check: "render_route resolves to the native floor with RESOLVED line,
NO-DATA when siblings unconfirmed; test green at the A3 commit."

Command: `python3 -m unittest tools.test_bm_toolkit -k "native_floor" -v`

Output (tail):
```
test_absent_capability_resolves_to_the_native_floor ... ok
test_native_floor_confirmed_absent_reports_no_data_not_a_guess ... ok
Ran 2 tests in 0.153s
OK
```

`render_route` (tools/bm_toolkit.py:1351) and its "M6" comment block
(lines 1322-1398) implement exactly the two named behaviors: RESOLVED to
the native floor when confirmed present, NO-DATA (never a guess) when
absence cannot be confirmed either way.

## M25 - CONFIRMED CLOSED

done_check: "the simulation either writes nothing outside its temporary
directory or its docstring stops promising that; a regression test asserts
no new bytecode cache appears beside a fixture install."

Command: `python3 -m unittest tools.test_bm.TestM25BlockedWriteSimulationLeavesNoBytecodeCache -v`

Output (tail):
```
test_no_bytecode_cache_appears_beside_the_installed_hook ... ok
Ran 1 test in 3.943s
OK
```

`scripts/doctor.py:328` sets `env["PYTHONDONTWRITEBYTECODE"] = "1"` for the
fence-liveness simulation's subprocess calls, exactly the fix the item
names; the test plants a fixture install, unsets the var deliberately
(the opposite of the suite's own default helper), and asserts no
`__pycache__` entry appears beside the fixture hook.

## M27 - CONFIRMED CLOSED

done_check: "a file planted with open(p, \"wb\") plus writelines, and one
with shutil.copyfileobj, are both counted by the scanner; the regression
test fails on the pre-fix patterns."

Command: `python3 -m unittest tools.test_bm -k "smuggled_binary" -v`

Output (tail):
```
test_widened_scope_catches_a_smuggled_binary_write ... ok
Ran 1 test in 0.011s
OK
```

`WRITE_PATTERNS` in tools/test_bm.py:1377-1387 (the reviewed write-site
gate's own pattern list, which is what `tools/write_sites.json` is checked
against) now matches `open(p, "wb")`-shaped modes and `.writelines(`/
`shutil.copyfileobj(`; the test plants both shapes in an isolated temp
tree and confirms the real scanner (`_sites`, not a re-derived copy of it)
catches all three sites.

## M28 - CONFIRMED CLOSED (item's own title text contradicts the landed fix)

done_check: "a planted file whose open() call wraps its path in a nested
call, with no .write beside it, is counted by the scanner; the regression
test fails on the current [^)]* pattern."

Command: `python3 -m unittest tools.test_bm -k "smuggled_nested" -v`

Output (tail):
```
test_widened_scope_catches_a_smuggled_nested_paren_write ... ok
Ran 1 test in 0.024s
OK
```

The test plants `open(os.path.join(root, "state", "marker"), "w")` with no
accompanying `.write()` call, the exact shape the item names, and the
scanner catches it. `WRITE_PATTERNS[0]` in tools/test_bm.py:1378 is
`r'open\((?:[^()]|\([^()]*\))*["\'][wax][rwxabt+]{0,3}["\']'`, which
explicitly accepts one balanced, one-level-deep parenthesized group between
`open(` and the mode string; the surrounding comment (lines 1359-1374)
documents this as "Widened again for M28".

**Flag:** the item's OWN title text in `docs/plan/QUEUE.json`, read
verbatim, says: "Left unfixed on purpose because closing it means changing
how the scanner parses rather than widening a character class, and that is
restructuring." This directly contradicts what shipped: the gap WAS closed
by widening a character class (the code comment says so explicitly), and
the specific real-world site the title names,
`scripts/benchmark.py` line 116, is confirmed present in
`tools/write_sites.json` (17 reviewed sites) and matched. This is the
mirror image of the M14 problem: not evidence about the wrong component,
but a title asserting a gap that the code no longer has. A reader trusting
only the title, without running the test, would wrongly believe a
production blind spot still exists. It does not, on the evidence actually
run here, but the item's own prose is now false and nothing updated it.

## O15 - CONFIRMED CLOSED (check-numbering has drifted since this item was filed)

done_check: "python3 scripts/doctor.py reports check 9 PASS."

Command: `python3 scripts/doctor.py` (full 15-check run against this
repository's real, committed tree; git status clean throughout)

Verbatim relevant lines:
```
[9/15] project store health: PASS
  PASS: verify: healthy, 0 problem(s)
...
[11/15] CHECKSUMS.sha256 self-check: PASS
  PASS: all 1170 file(s) listed in CHECKSUMS.sha256 match.
...
13 of 15 proven, 2 skipped, 0 failed.
All 15 checks passed (SKIP is not a failure unless --strict; see the reason printed next to it).
```

Literally, today, check 9 says PASS: the done_check as written is
satisfied. **Flag:** O15's title is "Regenerate CHECKSUMS and prove doctor
check 9 passes", and its own closed_note says check 9 "reads SKIP on a
dirty tree by design and PASS on the committed tree" -- a description that
fits the CHECKSUMS self-check (SKIP-on-dirty-tree is a checksums-manifest
behavior, not a SQLite store-health behavior) far better than what is
numbered check 9 today ("project store health"). `scripts/doctor.py` has
clearly grown checks since O15 was filed on 2026-08-15 (it names 15 checks
today), and the CHECKSUMS check has been renumbered to 11. Both the
originally-intended check and the currently-numbered check 9 PASS today,
so the substance O15 cared about is genuinely fine; but the literal "check
9" pointer in a done_check is a name that silently stopped meaning what it
meant when written, the same shape of drift (a stale pointer standing in
for a live one) that made M14 easy to misjudge.

## M15 - CONFIRMED CLOSED (done_check's own stated precondition is false, the measurement still stands)

done_check: "with M14 fixed so the warnings no longer swamp the output, the
installed hook is invoked against a path covered ONLY by a parked record
and its verdict is quoted; a refusal confirms the defect and gets its own
regression test, an allow closes this item as measured and not a defect."

This audit did not re-run M15's own measurement (it requires `claim` and
`park` calls against the live store, and this audit's hard constraints
forbid parking, closing or adopting any store record). Two independent
checks were made instead:

1. **Read the existing evidence file**,
   `docs/evidence/night-2026-08-21-m15-parked-record.md` (Status: CURRENT,
   dated 2026-08-21). It claims a positive-control record (denied while
   active), parks it, and re-queries: `ALLOW` on the parked-only path,
   `DENY` on a second, still-active control record, queried at the same
   moment, on BOTH the repo copy and the installed copy of
   `bm_fence_hook.py`, with zero fail-open warnings on stderr anywhere in
   the run. It explicitly separates M14's noise (which comes from a
   DIFFERENT hook, `sbe_fence_hook.py`) from the mechanism under test, and
   sidesteps it entirely by querying `bm_fence_hook.py` directly via its
   `query` verb (the M11 fix) rather than through the live PreToolUse
   chain where `sbe_fence_hook.py` also fires.
2. **Independent static check, this session:** read
   `active_claims()` in tools/bm_fence_hook.py:893-922 directly. Its SQL is
   `... FROM claims c JOIN records r ... WHERE r.state='active'`, a literal
   filter that structurally excludes any record in `parked` state from the
   set the fence enforces. This corroborates the evidence file's finding
   by a different method (code read, not narrative).

**Flag:** the done_check's own precondition, "with M14 fixed", never
became true; M14 is still `"state": "queued"` at HEAD, with 34 real
fail-open warnings reproducing on every write via `sbe_fence_hook.py`. The
M15 evidence file's own measurement did not actually need M14 fixed: it
got a clean, unswamped signal by querying `bm_fence_hook.py` directly
(the M11 verb) instead of going through the noisy live hook chain the
original failed attempt used. The real question M15 asks (does parked read
as live) is answered, with real positive controls and a code-level cross
check. But the done_check's own words describe a precondition that is
false, which is exactly the kind of prose a later session could copy
forward unread and misjudge, the M14 pattern one degree removed.

---

## WHAT THIS SAMPLE DOES NOT COVER

- **36 of the 50 "done" items were not checked at all**: TK1, TK2, TK3,
  TK5, TK9, TK10, TK11, O1, O2, O3, O5, O7, O11, O17, O18, O19, O20, O21,
  G1, A1, A2, A3, A4, A7, A8, L1 through L8, M3, M5, M8. Nothing here says
  they are fine; they were simply not in the sample. M3, M5 and M8 in
  particular are close siblings of items audited here (M3 and M9 closed in
  the same commit; M5 and M8 share M2's "A3 commit" done_check shape) and
  are reasonable next candidates for a follow-up pass.
- **No item requiring a founder action, an external estate, or a
  since-removed condition was selected**, per instruction not to pad the
  count with unevaluable items; this sample therefore contains zero CANNOT
  VERIFY verdicts. That is a property of the selection, not a claim that
  every remaining item is checkable.
- **M10's historical FENCE F5 block was not independently re-derived.**
  Whether that fence was released cleanly, force-crossed, or is still
  technically live somewhere is not established here; only that the code
  and tests it was blocking exist and pass on the current tree.
- **No item was re-verified against the INSTALLED clone of BrotherMode
  itself** (`~/.claude/skills/brothermode`) except where a test already
  does so by construction (M12, which loads BrotherSBE's installed copy;
  M17, which builds its own fixture rather than reading the real installed
  BrotherMode copy). The M15 evidence file separately confirmed, on
  2026-08-21, that the installed BrotherMode copy is byte-identical to
  this checkout for `bm_fence_hook.py` and `bm_store.py`; that check was
  not repeated here.
- **Full-suite state was not checked.** Per hard constraint, `tools/
  test_all.py` was never run; only the individual suites and test classes
  named above were run directly. A defect that only surfaces through
  suite-level interaction (shared fixtures, ordering, the write-site gate
  running against the full tree rather than an isolated fixture) would not
  be caught by this method.
- **Nothing here re-litigates M14 or M16 themselves**; both are already
  correctly `"state": "queued"` at HEAD with their own dated evidence
  files, and this audit treats that as settled going in.
