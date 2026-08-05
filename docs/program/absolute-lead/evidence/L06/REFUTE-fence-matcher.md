# REFUTE L06: adversarial attack on the Codex apply_patch fence matcher

Date: 2026-08-06. Target: `tools/bm_fence_hook.py` (the Bash / apply_patch branch in `decide()` and `extract_patch_targets`). Read-only analysis. No project file was edited, no commit made, no store touched. All probes ran in a throwaway project under `mktemp -d`, never against this repo's store.

CLAIM UNDER ATTACK: the hook correctly enforces the one-writer fence against Codex-style apply_patch writes carried inside Bash payloads, with (a) no bypass and (b) no false-deny.

VERDICT: **REFUTED (3 confirmed false-denies).** The bypass half of the claim survived every heredoc and path attack thrown at it; the false-deny half did not. The matcher scans the raw command text line by line with no awareness of which command is being invoked, no awareness of heredoc boundaries, and no awareness of apply_patch hunk-body structure, so it refuses legitimate commands that merely CONTAIN apply_patch directive text: any heredoc to any command, and any apply_patch hunk whose context lines quote a directive. In this project (whose own docs, tests, hook source and evidence files are saturated with `*** Begin Patch` / `*** Update File:` text) these false denies are not exotic, they are the common case for a Codex agent doing documentation or test work.

## The rig, and its calibration

Throwaway project under `mktemp -d`, `git init`, `bm_store.py init`, then `src/app.py` and `src/secret.py` claimed under the label of session `owner-sess` (`bm1-0aaebffe4274726e9242be2d`). Every probe payload carried a DIFFERENT session id (`attacker-sess`) and `cwd` = the rig root, fed to `python3 tools/bm_fence_hook.py` on stdin, exactly as Claude Code / Codex invoke it. Default (advisory) mode throughout.

Calibration proving the rig is live, not broken:

- KNOWN-BAD Edit of fenced `src/app.py` by attacker -> DENY (names record, owner, takeover command). PASS.
- KNOWN-BAD apply_patch `*** Update File: src/app.py` by attacker -> DENY. PASS.
- KNOWN-GOOD `ls -la` -> ALLOW, silent. PASS.

So in this rig an ALLOW of a fenced write means a real bypass, and a DENY of a benign command means a real false-deny. Every false-deny below is paired with its benign twin that ALLOWS, so the deny is attributable to the injected directive text and nothing else.

---

## 1. CONFIRMED FALSE-DENIES (3)

### FD-1: a legitimate apply_patch to an UNFENCED file is refused because a hunk CONTEXT line quotes a directive

Reproduced command (`tool_name` Bash, `command`):

```
apply_patch <<'PATCH'
*** Begin Patch
*** Update File: notes.md
@@
 *** Update File: src/secret.py
-plain notes
+z
*** End Patch
PATCH
```

`notes.md` is UNFENCED; the only real write target is `notes.md`. The line ` *** Update File: src/secret.py` has a LEADING SPACE, which is apply_patch hunk syntax for a context (unchanged) line, i.e. it is CONTENT of notes.md, not a directive. apply_patch would write it verbatim into notes.md and would never touch `src/secret.py`.

Observed hook output: DENY, `permissionDecisionReason` = "BrotherMode fence: src/secret.py is inside the fence of the active record api ... owned by session bm1-0aaebffe...". Benign twin (same patch without the context line) -> ALLOW. So the deny comes entirely from the phantom directive.

Failing logic: `extract_patch_targets`, line 404 `stripped = line.strip()`. Stripping the leading space of a hunk context line turns content into a false directive. Lines 408-414 then extract `src/secret.py` and `decide()` fences it. The docstring at lines 396-399 asserts stripping leading whitespace "can only WIDEN what gets checked ... never narrow it", treating widening as harmless. Widening is exactly what produces this false deny: a leading-space line inside a hunk is not an "indented directive that apply_patch would refuse anyway", it is a legitimate context line that apply_patch accepts as data.

### FD-2: a NON-apply_patch heredoc (here `cat`) that documents the grammar is refused

Reproduced command:

```
cat > howto.md <<'EOF'
*** Begin Patch
*** Update File: src/app.py
*** End Patch
EOF
```

This writes `howto.md` (a doc) with `cat`. It never invokes apply_patch and never touches `src/app.py`.

Observed: DENY naming `src/app.py`. Benign twin (`cat > howto.md <<'EOF'\njust docs\nEOF`) -> ALLOW.

Failing logic: `decide()`, line 670, `if not isinstance(command, str) or APPLY_PATCH_BEGIN not in command`. The ONLY qualifier to enter the apply_patch branch is the SUBSTRING presence of `*** Begin Patch`. There is no check that the command's program is `apply_patch`, and no parse of the heredoc boundary, so a `cat`/`tee`/`python - <<EOF`/`ssh host <<EOF` heredoc whose body contains the marker is treated as an apply_patch write. Lines 405-407 set `envelope_seen` from any line opening with the marker; lines 408-414 harvest the directive line.

### FD-3: a pure NON-WRITE command (git commit) whose MESSAGE documents the grammar is refused

Reproduced command:

```
git commit -F - <<'EOF'
Document apply_patch grammar

*** Begin Patch
*** Update File: src/app.py
*** End Patch
EOF
```

No file is written by this command at all (it records a commit; the message body merely documents the grammar). This is precisely the "plain non-write Bash command wrongly refused" the claim promises cannot happen.

Observed: DENY naming `src/app.py`. Same root cause as FD-2 (line 670 substring gate + line-based harvest).

Why these three matter in THIS project specifically: `docs/HOOKS.md`, `docs/RUNTIMES.md`, `tools/bm_fence_hook.py`, `tools/test_bm_fence_hook.py`, the L06 FIX report, and this very file all contain `*** Begin Patch` and `*** Update File:` text at the start of lines. A Codex agent editing or generating any of them via a heredoc, or apply_patching a file whose hunk context quotes the grammar, is falsely refused whenever the quoted path overlaps any active fence. In a multi-agent BrotherMode session that overlap is the normal state, so this is a routine break, not a corner case.

---

## 2. SUSPECTED, not cleanly reproduced

### SUS-1: `printf ... | apply_patch` slips through (matcher misses; live write unverified)

```
printf '*** Begin Patch\n*** Update File: src/app.py\n@@\n-# app.py\n+x\n*** End Patch\n' | apply_patch
```

and the variable-assembled variant

```
M='*** Begin Patch'; printf '%s\n*** Update File: src/app.py\n@@\n-# app.py\n+x\n*** End Patch\n' "$M" | apply_patch
```

Both were ALLOWED by the hook. Root cause: `command.splitlines()` (line 403) sees ONE physical line (the `\n` are backslash-n escapes inside the printf format, not real newlines), so `*** Begin Patch` and the directive are mid-line, `envelope_seen` stays False and no target is harvested. If apply_patch reads its envelope from this piped stdin, this is a genuine fence bypass of an apply_patch write. Marked SUSPECTED, not confirmed, for two honest reasons: (1) it needs a live `apply_patch` binary to prove the write actually lands, which this read-only rig has no way to run; (2) it is a hand-crafted evasion, not what codex-cli emits (Codex emits the heredoc form, which IS caught), so it sits inside the arbitrary-shell gap the FIX report already declares open (report item 3). Flagged because it defeats the matcher using the very mechanism the matcher claims to gate, so the orchestrator should decide whether the stated gap is meant to cover it.

---

## 3. Attacks the hook HANDLED CORRECTLY (so coverage is on record)

All of the following were DENIED when they reached fenced `src/app.py`/`src/secret.py`, or ALLOWED when they legitimately should be. None is a hole.

Heredoc delimiter variations (all correctly DENY the fenced write, because the parser is delimiter-agnostic and reads directive lines wherever they open a line):
- unquoted `<<PATCH`; double-quoted `<<"PATCH"`; custom delimiter `<<'EOF'`; tab-stripped `<<-'PATCH'` with tab-indented directives; space-indented body with indented closing delimiter. DENY x5.

Path spellings reaching the fenced file (all correctly DENY via `canonical_target` realpath + `paths_overlap`):
- `src/../src/app.py` (dot-dot staying in root); absolute `<root>/src/app.py`; `./src/app.py`; `src//app.py` (redundant separators); `src/app.py/` (trailing slash); `src/APP.py` (macOS case fold); `srclink/app.py` (symlinked directory component). DENY x7.
- `../escape.py` (resolves above root) -> ALLOW, correct: BrotherMode fences a project, not the machine.

Directive coverage:
- `*** Move to: src/app.py` rename onto a fenced file -> DENY. Correct.
- `*** Delete File:`, `*** Update File:`, `*** Add File:` -> each checked.
- Multi-directive patch, fenced `src/secret.py` AFTER unfenced `notes.md` -> DENY naming the FENCED file, not the first. Correct.

Body-content confusion that the `+`/`-` prefix DOES protect against (these correctly ALLOW when the real target is unfenced):
- ADDED line `+*** Add File: src/app.py` -> ALLOW (the `+` keeps it off the directive prefix).
- REMOVED line `-*** Update File: src/secret.py` -> ALLOW (the `-` keeps it off).
  (Note: the CONTEXT-line case, leading space, is NOT protected. That is FD-1.)

Mid-line marker / plain commands -> ALLOW, silent:
- `grep "*** Begin Patch" notes.md`; `echo apply_patch and *** Begin Patch is documented`; `echo '*** Update File: src/app.py' >> notes.md`. ALLOW x3. (These are the cases the FIX report designed for; they hold. FD-2/FD-3 are the cases it did not consider: a directive at the START of a heredoc-body line, which strip exposes exactly as it exposes FD-1.)

Unreadable envelope:
- `*** Begin Patch` with no readable directive -> DENY with the unreadable-patch reason, loud on stderr. Correct per design.

Env-assignment prefix on a real heredoc (`FOO=bar apply_patch <<'PATCH' ...`) -> DENY. Correct (real newlines, directive at line start).

Identity (spot-checked, not the focus): a foreign `session_id` derives a different label and is refused; the owner session ALLOWS its own patch. The owner/foreign split works through the apply_patch path.

---

## Verdict

REFUTED, 3 confirmed false-denies (FD-1 apply_patch context line; FD-2 non-apply_patch heredoc; FD-3 non-write git-commit heredoc), all three reproduced with a benign twin that allows, all three rooted in the same defect: the matcher is a purely textual line scan (`decide` line 670 substring gate; `extract_patch_targets` line 404 whitespace strip and lines 405-414 markerless harvest) with no notion of which command runs, where the heredoc ends, or whether a directive-shaped line is a real directive or hunk/heredoc content. The three hardest attacks that FAILED to refute the BYPASS half: the tab-stripped `<<-` heredoc with tab-indented directives (still denied), the symlinked-directory path component (still resolved and denied), and the macOS case-folded spelling `src/APP.py` (still denied). The one-writer fence is not bypassable by a Codex-style heredoc write; it is over-eager, refusing legitimate work whenever apply_patch grammar appears as text.
