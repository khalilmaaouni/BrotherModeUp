# FIX L06: the Codex apply_patch fence matcher

Date: 2026-08-06. Files changed: `tools/bm_fence_hook.py`, `tools/test_bm_fence_hook.py`. Evidence: this file, `RED-matcher.txt` beside it. Nothing else was written: no hook wiring, no docs, no store, no git operations.

## What landed

Under the Codex CLI every file write reaches hooks as `tool_name` `Bash` whose `tool_input.command` holds an apply_patch heredoc, so the fence hook exited 0 in silence on every write. The hook now gates that one Bash shape:

1. `decide()` accepts `tool_name` `Bash` alongside the structured write tools. The first thing the Bash branch does is a substring test for `*** Begin Patch`; a command without it returns immediately, before any identity, store, or root work, exactly as silent and cheap as before Bash was matched at all. This branch runs in front of every shell command once the matcher widens, so the fast path out is the design center.
2. A new parser, `extract_patch_targets(command)`, reads the envelope grammar captured off the real Codex 0.146 session on 2026-08-05: `*** Add File: <path>`, `*** Update File: <path>`, `*** Delete File: <path>`, and a rename's `*** Move to: <path>` (the move TARGET is a written path and is checked).
3. Every extracted path then flows through the SAME code path the Edit tools use: same `canonical_target()` resolution against the project root and payload cwd, same `paths_overlap()` fence comparison, same foreign-owner deny naming the path, the record, the owner label, and the takeover command, same `BM_FENCE_STRICT` claim-before-edit tightening, same fail-open discipline. There is no second fence implementation; the Bash branch only produces `raw_targets` and hands off.
4. An envelope with no readable file directive is DENIED, not failed open: the write is real, its targets are unknowable, and a fence that shrugs at an unparseable write is the silent no-op this matcher exists to end. The deny is a literal string (`_UNREADABLE_PATCH_REASON`), quotes no payload content, and is emitted with the existing deny shape on stdout, exit 0.

The decision is complete at PreToolUse time by construction, which matches the measurement that apply_patch fires PreToolUse and never PostToolUse under Codex.

## Grammar cases and the chosen behavior for each ambiguous shape

| Shape | Behavior | Why |
| --- | --- | --- |
| Well formed envelope, one or more directives | Each path fence-checked through the shared Edit path; any foreign-owned path denies the whole call naming that path | The core case, from the captured payload |
| `*** Move to: <path>` | Target treated as a written path and checked | A rename onto a fenced file is a write to it |
| Multi-file patch, only a later file fenced | Denied, naming the fenced file, not the first | Paths are checked in input order; the deny names the first DENIED path |
| No `*** Begin Patch` substring anywhere | Silent allow, immediate, before identity or store work | A plain shell command is not the fence's business; performance matters |
| Marker only mid-line (for example `grep "*** Begin Patch" notes.md`) | Silent allow. DOCUMENTED CHOICE: an envelope is recognized only when the marker OPENS a line (leading whitespace stripped) | apply_patch is itself a line-based parser, so a marker buried mid-line can never reach a real write; denying it would fence the founder off from searching their own notes. Tested both in the parser and end to end |
| Heredoc that is not apply_patch | Not matched (no marker), silent allow | Tested |
| `echo apply_patch` | Not matched, silent allow | The word alone is not an envelope. Tested |
| Begin without End, directives readable | The readable directives are checked; the parseable part is authoritative | Founder rule: treat what IS parseable as authoritative |
| Begin without End, nothing readable | Denied as unreadable | Nothing parseable while the envelope is present |
| Directive outside the Begin/End pair | Checked anyway | It still names a file the patch intends to touch |
| Empty directive path (`*** Add File: ` and nothing) | Skipped as unreadable; if it was the only directive, the whole envelope is denied as unreadable | An empty path certifies nothing |
| Leading whitespace before a marker or directive | Stripped before matching | Widens what gets checked, never narrows it; real apply_patch would refuse the indented line anyway |
| Duplicate directive paths | De-duplicated, input order kept | Mirrors `extract_targets` |
| Non-ASCII directive path | Parsed and fenced; fixture written as backslash-u escapes | Same canonicalization as the Edit path |
| Unreadable envelope in a directory with no store or root | Still denied. DELIBERATE: the unreadable deny is unconditional and runs before store or root resolution, per the brief's instruction that the fence must not shrug | The only shape that can hit this is a malformed apply_patch invocation, which was not going to apply cleanly anyway; recorded here so the choice is visible |
| Bash payload whose `tool_input` is not an object, or whose `command` is missing or not a string | Silent allow, same as before this change | There is nothing to read; the pre-change behavior for Bash was silence, and no regression is introduced |
| Envelope present, directives readable, but the payload carries no `session_id` | Exactly what the Edit path does: advisory fails open LOUDLY (`no verifiable identity` on stderr), enforced mode denies | Same code path, same discipline; see the open item below |

## WIRING DELTA FOR THE ORCHESTRATOR

The matcher string the fence hook's PreToolUse wiring needs is, exactly:

```
Edit|Write|MultiEdit|NotebookEdit|Bash
```

The live copies of the old string found in the checkout (none edited by this task):

- `hooks/hooks.json` line 53 (`"matcher"`)
- `scripts/install.py` line 83 (`FENCE_MATCHER`)
- `docs/HOOKS.md` line 120 (the documented settings.json block; lines 315 and 536 also discuss the old matcher in prose)
- `docs/SETUP.md` line 142 and `docs/QUICKSTART.md` line 272 (the copy-paste blocks)

Also pinned in tests, which will fail the moment the wiring widens unless updated in the same change: `tools/test_bm_consent.py` lines 1017 and 1164, `tools/test_install.py` line 838 (default argument), `tools/test_bm_docs.py` line 252 (asserts the old string appears in docs). `tools/test_bm_runtimes.py` line 912 describes the old behavior in prose. Historical records under `docs/closure/` and `docs/evidence/` quote the old matcher and should stay as they are; they are records of measurements, not wiring.

One wiring caveat from the same Codex measurement, restated: under Codex, `${CLAUDE_PLUGIN_ROOT}` expands to empty, so a hand-installed Codex hooks file needs absolute paths (docs/RUNTIMES.md).

## WRITE SITES DELTA

None. The change adds no file write, so `tools/bm_fence_hook.py` stays at its reviewed count of 7 in `tools/write_sites.json`, untouched. Verified after the change:

```
$ python3 tools/test_bm.py TestPreWriteGate
Ran 2 tests in 0.160s

OK
```

## Done-check, verbatim

Suite before the change (untouched hook, before the new tests):

```
$ python3 tools/test_bm_fence_hook.py
Ran 62 tests in 1.769s

OK
```

RED, new tests against the untouched hook (full output in `RED-matcher.txt` beside this file):

```
$ python3 tools/test_bm_fence_hook.py CodexApplyPatch
Ran 20 tests in 0.394s

FAILED (failures=11, errors=3)
EXIT: 1
```

Suite after the change, run after the last edit:

```
$ python3 tools/test_bm_fence_hook.py
Ran 82 tests in 2.368s

OK
EXIT: 0
```

62 before, 82 after; no existing test was removed or weakened, and the count did not drop.

In-process demonstration: the captured payload fed through the hook's main entry (`python3 tools/bm_fence_hook.py`, JSON on stdin, in a throwaway project whose store holds `probe_written_by_codex.txt` under another session's fence). Exit code 0, stderr empty, stdout verbatim:

```
{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "BrotherMode fence: probe_written_by_codex.txt is inside the fence of the active record probe (lifecycle 97783531910c43f1878d9a9ca6838fe9, version 1), which is owned by session bm1-af0ab0070b557f09d31ddd53. This session is bm1-c3efacab86d5eaa545f981ff, so it is not the writer for that path. Claimed as: probe_written_by_codex.txt.\nOne writer per file is structural, not advisory: do not edit across the fence. Report the needed change to the owner instead. To take the fence over deliberately, run:\n  python3 tools/bm_store.py adopt 97783531910c43f1878d9a9ca6838fe9 --version 1 --session bm1-c3efacab86d5eaa545f981ff --adopt-from-live-session\nthen re-claim the paths you need with `bm_store.py claim ... --session bm1-c3efacab86d5eaa545f981ff`."}}
```

The deny shape is byte-for-byte the existing contract object; no new output shape was introduced.

## What could not be closed, with reasons

1. THE CAPTURED PAYLOAD CARRIES NO session_id. The three-key capture (`tool_name`, `tool_input`, `tool_use_id`) has no session identity and no cwd. Fed verbatim, the hook does exactly what it does for an Edit with no session id, because the same code path decides both: advisory fails open LOUDLY (`no verifiable identity` on stderr), enforced mode denies with the literal no-session-id reason. This is tested (`test_captured_payload_verbatim_shape_without_session_id`) rather than hidden. What it means: if Codex truly sends nothing but these three keys, the ownership deny cannot fire in advisory mode, and the working configurations are either a fuller Codex payload (docs/RUNTIMES.md says payloads are Claude shaped, which implies session_id is present and the capture in the brief was trimmed) or `BM_FENCE_MODE=enforced` on the Codex side. The orchestrator should confirm from the Lane C captures which fields Codex actually sends beside tool_input before wiring; that decision was not mine to make and could not be measured here without running Codex.
2. NO LIVE CODEX REHEARSAL. The deny is proven in process and through the real executable entry, but not through a live codex-cli session, because the wiring change that would let Codex reach this hook is explicitly the orchestrator's to land. The enforcement primitive itself was already proven live on 2026-08-05.
3. ARBITRARY SHELL REMAINS UNGATED, unchanged. This closes the one Bash shape that is a structured write in a Bash costume; `python3 -c "open(...)"` and friends remain the stated gap in docs/HOOKS.md. The WRITE_TOOLS comment in the hook now states both halves.
4. DOCS NOT UPDATED. docs/HOOKS.md, docs/RUNTIMES.md, SETUP and QUICKSTART still describe the pre-L06 behavior. Out of this task's write scope; they belong in the orchestrator's wiring change, together with the four matcher copies and the test pins listed above.
5. THE UNREADABLE-ENVELOPE DENY IS UNCONDITIONAL, including in a directory that is not a BrotherMode project. Deliberate, per the brief, and narrow (only a malformed apply_patch invocation can reach it), but it is the one place this hook can now refuse before resolving a root, and it is recorded here so nobody has to discover it.
6. STRICT MODE NOW COVERS apply_patch TARGETS. A consequence of sharing the Edit code path: with `BM_FENCE_STRICT` set, an unclaimed apply_patch path is refused claim-first, same as an unclaimed Edit. This is the consistent reading of one shared fence, stated here because nobody asked for it by name.

---

## REFUTE ROUND 2 FIXES

An adversarial refuter attacked the round-1 matcher and confirmed three FALSE-denies (the bypass half held: every heredoc-delimiter, path-spelling and rename attack that tried to slip a fenced write past the fence still DENIED). Full attack report: `docs/program/absolute-lead/evidence/L06/REFUTE-fence-matcher.md`. All three false-denies share ONE root cause: the round-1 matcher was a pure textual line scan. It stripped leading whitespace before testing a line for a directive, and it entered the apply_patch branch on the mere SUBSTRING of the envelope marker, with no notion of which program runs or where a heredoc ends. The fix replaces the text scan with a small heredoc-aware parser (`apply_patch_bodies`, `_find_heredoc_ops`, `_command_word`) plus a column-0 body parser (`extract_patch_targets` rewritten). Standard library only, no new imports (hand-written, no `re`), Python 3.9, ASCII, no dashes.

### FD-1: an apply_patch hunk CONTEXT line is content, not a directive

- BEFORE: ` *** Update File: src/secret.py` (leading space) inside a hunk of a patch that only writes the unfenced `notes.md` was stripped to `*** Update File: src/secret.py` and harvested as a directive, so the hook DENIED, naming a file the patch never touches.
- FIX: in `extract_patch_targets`, a line beginning with a space, `+` or `-` is hunk body (context / added / removed) and is skipped; leading whitespace is no longer stripped, so a directive is matched at column 0 only.
- AFTER: the same command ALLOWS (its real target, `notes.md`, is unfenced). A genuine column-0 `*** Update File: src/secret.py` to the fenced file still DENIES. Tests: `test_fd1_context_line_quoting_a_directive_is_not_a_write`, `test_fd1_real_column_zero_directive_to_fenced_file_still_denies`, `test_fd1_added_and_removed_lines_are_not_directives`.

### FD-2: a non-apply_patch heredoc (cat / tee) that quotes the grammar

- BEFORE: `cat > howto.md <<'EOF' ... *** Update File: src/app.py ... EOF` writes a doc with cat and never invokes apply_patch, but the substring `*** Begin Patch` alone put the hook into the patch branch and it DENIED `src/app.py`.
- FIX: the hook now parses the heredoc that carries the envelope and treats it as a write only when the command that OWNS that heredoc is apply_patch. `_command_word` finds the program word of the simple command nearest the `<<` operator (skipping leading `NAME=value` env assignments, honoring pipelines and separators); `apply_patch_bodies` returns only bodies fed to apply_patch.
- AFTER: both the exact refuter reproduction and a harder variant whose body literally contains the token `apply_patch` (so a naive substring-on-apply_patch gate would still misfire) ALLOW. Tests: `test_fd2a_cat_heredoc_documenting_the_grammar_is_not_a_write`, `test_fd2b_non_apply_patch_heredoc_whose_body_names_apply_patch`.

### FD-3: a git-commit heredoc whose message documents the grammar

- BEFORE: `git commit -F - <<'EOF' ... *** Begin Patch ... EOF` writes no file at all, yet the marker substring made the hook DENY `src/app.py`.
- FIX: same as FD-2. The heredoc is owned by `git`, not apply_patch, so it yields no bodies and is allowed.
- AFTER: ALLOWS. Test: `test_fd3_git_commit_heredoc_writes_no_file_and_is_allowed`.

### Regression floor kept (section 3 of the refute report)

Every genuine fenced apply_patch write the refuter confirmed still DENIED must still DENY, and each now has a test: real `apply_patch <<'PATCH'` heredoc; the tab-stripping `<<-'PATCH'` with tab-indented directives (the fix strips leading TABS for `<<-` specifically, so the directive is at column 0 as the shell would present it, which is exactly why "do not strip whitespace" had to become "strip tabs only for `<<-`"); an env-assignment prefix `FOO=bar apply_patch`; unquoted `<<PATCH` and double-quoted `<<"PATCH"` delimiters; an apply_patch heredoc downstream of a pipe; the unreadable-envelope deny; and the owner's own patch allowed. Tests: `test_apply_patch_heredoc_still_denies_the_fenced_write`, `test_dash_heredoc_with_tab_indented_directives_still_denies`, `test_env_assignment_prefix_before_apply_patch_still_denies`, `test_unquoted_and_double_quoted_delimiters_still_deny`, `test_apply_patch_owned_heredoc_in_a_pipeline_still_denies`, `test_unreadable_apply_patch_heredoc_still_denies`, `test_owner_may_run_a_real_apply_patch_heredoc`.

One deliberate narrowing that falls out of the FD-1 fix and is NOT a regression: a space-indented directive inside a plain `<<` heredoc (no dash) now ALLOWS rather than DENIES. That is correct: bash does not strip spaces for `<<`, so apply_patch receives the line space-indented and treats it as hunk context, i.e. it would not write that file as a directive either. Refusing it was the same false-deny class as FD-1. There is no test asserting the old space-indented DENY, so nothing in the floor breaks.

### SUS-1 disposition: recorded residual, not swallowed

`printf '*** Begin Patch\n*** Update File: src/app.py\n...' | apply_patch` (the `\n` are printf backslash escapes, so the whole thing is one physical line with no heredoc) is ALLOWED by the fix, because there is no heredoc body to read. Disposition: RECORDED AS A NAMED RESIDUAL, not extended, for the reasons the refuter gave and I concur with. (1) It is a hand-crafted evasion, not what codex-cli emits: Codex emits the heredoc form, which IS gated. (2) It sits inside the arbitrary-shell gap docs/HOOKS.md and this report (open item 3) already declare open; a shell can always write a file some way the fence cannot parse, and `printf | apply_patch` is one such way. (3) Extending to un-escape printf format strings and detect stdin pipes would add real false-positive risk (any `printf '...apply_patch...' | mail`) for a shape no measured runtime produces. It is pinned by `test_sus1_printf_piped_to_apply_patch_is_a_recorded_residual`, which asserts the ALLOW and is written as the tripwire that fires if the arbitrary-shell gap is ever closed. If the orchestrator wants the pipe form gated, that is a scoped follow-up, not a silent hole.

### Done-check, round 2, verbatim

RED (round-2 tests against the untouched round-1 hook, appended in `RED-matcher.txt`):

```
$ python3 tools/test_bm_fence_hook.py CodexApplyPatchRefuteRound2
Ran 14 tests in 0.284s

FAILED (failures=4)
EXIT: 1
```

The four failures were exactly FD-1, FD-2a, FD-2b, FD-3, each observed DENYing where it must ALLOW; the ten floor-guard tests passed on the old hook already.

AFTER the fix:

```
$ python3 tools/test_bm_fence_hook.py CodexApplyPatchRefuteRound2
Ran 14 tests in 0.455s

OK

$ python3 tools/test_bm_fence_hook.py
Ran 96 tests in 4.652s

OK
```

82 before round 2, 96 after (14 added, none dropped, none weakened). Write-site guard still green at the pinned count of 7 (`python3 tools/test_bm.py TestPreWriteGate` -> `Ran 2 tests ... OK`); the fix adds no file write. Fence-hook structural guard green (`python3 tools/test_bm_fence_hook.py Structural` -> `Ran 4 tests ... OK`): still no em or en dashes, still exactly one stdout writer, still ReadOnlyStore only.

End-to-end through the real hook executable, in a throwaway `mktemp -d` project with `src/app.py` and `src/secret.py` fenced to another session (never the repo store):

```
case                                                       want   got    ok
FD-1 context line quoting fenced src/secret.py (writes not ALLOW  ALLOW  PASS
FD-2a cat heredoc documenting the grammar                  ALLOW  ALLOW  PASS
FD-2b cat heredoc whose body names apply_patch             ALLOW  ALLOW  PASS
FD-3 git commit heredoc documenting the grammar            ALLOW  ALLOW  PASS
FLOOR genuine fenced apply_patch heredoc to src/app.py     DENY   DENY   PASS
ALL PASS
```

### Round-2 residuals

- SUS-1 as above: the `printf | apply_patch` stdin-pipe form is an allowed, named residual under the open arbitrary-shell gap.
- The heredoc parser is a pragmatic bash reader, not a full shell grammar. It handles the operator forms, quoting, `<<-` tab stripping, env-assignment prefixes, pipelines and separators that the attacks and the real Codex payload use. Exotic constructs (command substitution that assembles the word `apply_patch`, a heredoc word built from a variable) are not modeled; all such gaps fail toward ALLOW (a missed gate inside the already-declared arbitrary-shell gap), never toward a false DENY, so they cannot re-open the false-deny class this round closed.
- The WIRING DELTA and WRITE SITES DELTA above are unchanged by round 2: the matcher string the orchestrator must land is still `Edit|Write|MultiEdit|NotebookEdit|Bash`, and the reviewed write-site count for `tools/bm_fence_hook.py` is still 7.
