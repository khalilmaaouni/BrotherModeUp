# M01: the Codex fence refused three kinds of honest work

## WHAT HAPPENED

Plain language: the guard that stops two AI sessions from editing the same file at
once was taught to read the Codex tool's write format. The first version was too
eager. It refused three completely legitimate commands, because each of them
merely *mentioned* the Codex write format in its text. Nothing was being written
to a protected file in any of the three cases.

The three false refusals (called false denies below):

1. A patch to an unfenced file whose unchanged context line quoted a directive.
   The line ` *** Update File: src/secret.py` has a leading space, which is patch
   grammar for "this line is content, not an instruction". The old matcher
   stripped the space and read it as an instruction.
2. A `cat > howto.md` heredoc documenting the format. This writes a doc with
   `cat` and never invokes the patch tool at all.
3. A `git commit -F -` heredoc whose commit message documents the format. This
   command writes no file whatsoever.

Why this mattered more here than anywhere else: this repository's own docs, tests,
hook source and evidence files are full of that grammar as text. A Codex agent
doing documentation or test work in this repo would have hit the false refusal
routinely, not rarely.

Technical detail: the round-1 matcher was a plain text line scan. It entered the
patch branch on the mere substring `*** Begin Patch` anywhere in the command, and
it stripped leading whitespace before testing a line for a directive. It had no
idea which program was being run, where a heredoc ended, or whether a
directive-shaped line was a real directive or body content.

## HOW IT WAS FOUND

By an independent adversarial refuter (a separate agent whose only job was to
break the claim, not to confirm it), driving the real hook executable in a
throwaway project under `mktemp -d`. Not by the implementer, and not by the
existing suite: the round-1 suite was 82 tests and all green when this was found.

The refuter's calibration rule is why the finding is trustworthy: every allow that
would be a hole was shown beside a known-bad that was refused in the same rig, and
every false deny was shown beside a benign twin command that was allowed.

Report: `/Users/khalil.maaouni/Documents/BrotherModeUp/docs/program/absolute-lead/evidence/L06/REFUTE-fence-matcher.md`
(verdict at line 7: REFUTED, 3 confirmed false denies).

## THE EVIDENCE

The four round-2 tests, run against the untouched round-1 hook. From
`/Users/khalil.maaouni/Documents/BrotherModeUp/docs/program/absolute-lead/evidence/L06/RED-matcher.txt`
lines 180 to 270:

```
L06 refute round 2. 2026-08-06 01:35:02
Command: python3 tools/test_bm_fence_hook.py CodexApplyPatchRefuteRound2

FAIL: test_fd1_context_line_quoting_a_directive_is_not_a_write
FAIL: test_fd2a_cat_heredoc_documenting_the_grammar_is_not_a_write
FAIL: test_fd2b_non_apply_patch_heredoc_whose_body_names_apply_patch
FAIL: test_fd3_git_commit_heredoc_writes_no_file_and_is_allowed

Ran 14 tests in 0.284s

FAILED (failures=4)
EXIT: 1
```

The failing assertion in each case, verbatim (FD-1 shown, the other three are the
same shape):

```
AssertionError: ... is not None : expected no decision (allow); got a deny:
'BrotherMode fence: src/secret.py is inside the fence of the active record
secret ... This session is bm1-8f83df18b6fcd5c1e10ddbe8, so it is not the
writer for that path.'
```

The other ten tests in the same class (the regression floor: every genuine fenced
write that must still be refused) already passed against the round-1 hook, so the
bypass half of the claim was never broken. Only the false-deny half was.

## HOW IT WAS FIXED

The text scan was replaced with a small heredoc-aware parser plus a column-0
directive parser. All in `/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_fence_hook.py`:

- `apply_patch_bodies` at tools/bm_fence_hook.py:527 returns only the heredoc
  bodies actually fed to `apply_patch`.
- `_find_heredoc_ops` at tools/bm_fence_hook.py:476 finds heredoc operators and
  their boundaries.
- `_command_word` at tools/bm_fence_hook.py:453 finds the program word of the
  simple command that owns the heredoc, skipping `NAME=value` env assignments and
  honouring pipelines and separators. This is what makes `cat` and `git` heredocs
  stop being treated as patch writes.
- `extract_patch_targets` at tools/bm_fence_hook.py:407 was rewritten: a line
  starting with a space, `+` or `-` is patch body and is skipped, and leading
  whitespace is no longer stripped, so a directive is matched at column 0 only.
  Tabs are stripped only for the `<<-` heredoc form, because that is exactly what
  the shell itself does.

After the fix, same command:

```
Ran 14 tests in 0.455s

OK

$ python3 tools/test_bm_fence_hook.py
Ran 96 tests in 4.652s

OK
```

62 tests before this work, 82 after round 1, 96 after round 2. No test was
removed or weakened.

One residual was recorded rather than closed: `printf '...' | apply_patch` (one
physical line, no heredoc) is still allowed, and it is pinned by
`test_sus1_printf_piped_to_apply_patch_is_a_recorded_residual` as a deliberate
tripwire. It sits inside the arbitrary-shell gap the docs already declare open.

## THE RULE THIS PRODUCES

A guard that decides from text alone will refuse honest work: parse the structure
the tool actually uses (which program runs, where the quoted block ends, which
column a directive starts in) before you refuse anything.

## WAS IT CAUGHT BEFORE OR AFTER IT COULD HURT A USER

Before. The round-1 matcher was never released: the false denies were found and
fixed inside the same commit (ac7ef87), and no version with them reached a user.
Caveat worth stating: they were also not caught by the implementer's own 82 green
tests. It took a separate adversary to find them, which is the only reason this
was before and not after.
