# FIX: the eleven platform-blind assumptions, closed or disclosed

Answers `docs/program/absolute-lead/evidence/AUDIT-windows-blind-assumptions.md`
(F1 to F11). Executed evidence is in
`docs/program/absolute-lead/evidence/RED-windows-blind.txt`, which carries the
probe transcript, the sweeps and the suite runs verbatim.

Machine: darwin 25.5.0, Python 3.9.6, 2026-08-05.
Repository: `/Users/khalil.maaouni/Documents/BrotherModeUp`, working tree at
`bdb3920` plus the orchestrator's `_git_prefix` fix and this loop's changes.

## 0. The one sentence that governs every Windows claim below

**I cannot run Windows, and nothing in this report was executed on Windows.**
Every Windows statement here is exactly one of three things, and each is labelled
where it appears:

- **MEASURED (lexical).** The SHIPPED function called on this Mac with
  `sys.platform` forced to `"win32"`, or `ntpath` and `shlex` called directly.
  `_quote_path_for_local_shell`, `shlex` and `ntpath` are pure Python, so this is
  an exact measurement of Windows LEXICAL semantics. It says nothing about
  syscalls and nothing about what `cmd.exe` then does with the string.
- **REASONED from a named rule.** Documented behaviour of `cmd.exe`, of
  `os.chmod` on Windows, or of `ntpath.expanduser`, with the source named. Not a
  measurement.
- **UNVERIFIED LOCALLY, CI IS THE INSTRUMENT.** Everything about a real Windows
  runner: PATH contents, syscall results, exit codes. The next push is the
  experiment.

The audit's own section 6 made the same disclosure and this report keeps it,
because the failure this loop exists to remove is a green reading that was never
actually asked of the platform it claims to cover.

## 1. Per-finding table

| # | verdict | where | what changed |
|---|---|---|---|
| F1 | **closed** | `tools/bm_controller.py:746` (orchestrator), `tools/test_bm_controller.py:6951` (this loop) | root cause fixed in the product; the assertion now reads through the same helper the composition site uses, so it is right whatever the runner's temp path looks like |
| F2 | **closed by the root-cause fix**, verified, see section 2 | `tools/test_bm_controller.py:6993` | no test change needed |
| F3 | **closed by the root-cause fix**, verified, see section 2 | `tools/test_bm_controller.py:7083` | no test change needed; F9's change additionally makes its rollback leg deterministic instead of accidental |
| F4 | **closed** | `tools/test_bm_controller.py:6901`, helper at `:6780` | payload moved to a file, both paths quoted through the project's helper; no branch, no skip |
| F5 | **closed** | `tools/test_bm_controller.py:6918` | same helper, same shape |
| F6 | **disclosed** (measured guard, named skip) | `tools/test_bm_store.py:19520`, helper at `:19437` | the denial is now MEASURED before it is relied on; where it does not work the test says exactly what it stops proving |
| F7 | **disclosed** (measured guard, named skip) | `tools/test_bm_controller.py:7321`, helper at `:7262` | same helper, same wording |
| F8 | **closed** | `tools/test_bm_controller.py:6242` | `USERPROFILE` set and popped alongside `HOME`, so the guard is real on both platforms |
| F9 | **closed** for the four test literals; **disclosed** for one product default | `tools/test_bm_controller.py:6203` and three call sites | `true` and `false` replaced by two shared constants built from `sys.executable`; the product's own `or "true"` default (`tools/bm_controller.py:3180`) is disclosed, not changed |
| F10 | **disclosed** (privilege guard, not a platform skip) | `tools/test_bm_store.py:17554` | `os.symlink` wrapped so a lost privilege names itself instead of erroring out of a setup line |
| F11 | **closed**, priority LOW and recorded as such | `tools/test_bm_runtimes.py:853` | split first, substitute after; Windows never runs this suite, and the comment says so |

Nothing is **blocked**. No existing assertion collided with a fix, so the STOP
rule was never reached.

## 2. F2 and F3: is the orchestrator's single product fix enough

**Asked, not assumed. Verdict: yes for both, and here is the reasoning chain with
the measured step marked.**

The rollback command has two halves and the fix touched one of them:

```
git --git-dir=<A> --work-tree=<B> restore -- <paths>
       \_______________________/              \____/
        _git_prefix, FIXED                     still shlex.quote
        (bm_controller.py:746)                 (bm_controller.py:3647)
```

**Step 1, MEASURED (lexical).** With `sys.platform` forced to `"win32"`, the
fixed `_git_prefix` emits no single quotes at all for an ordinary Windows path,
where the old code emitted two pairs:

```
OLD: git --git-dir='C:\Users\RUNNER~1\...\P\.git' --work-tree='C:\Users\RUNNER~1\...\P' restore -- a.py
NEW: git --git-dir=C:\Users\RUNNER~1\...\P\.git --work-tree=C:\Users\RUNNER~1\...\P restore -- a.py
OLD contains a single quote: True
NEW contains a single quote: False
```

**Step 2, MEASURED (lexical).** Both tests use `write_scope=["a.py"]`, so the
half that was NOT fixed contributes nothing: `_pathspec_literal("a.py")` returns
`a.py` unchanged (no leading colon), and `shlex.quote("a.py")` returns `a.py`
bare on every platform. Measured for each entry those tests actually declare:

```
shlex.quote('a.py')           = 'a.py'            Windows-safe: True
shlex.quote('out.txt')        = 'out.txt'         Windows-safe: True
shlex.quote('src/app/main.py')= 'src/app/main.py' Windows-safe: True
shlex.quote('my file.py')     = "'my file.py'"    Windows-safe: False   <- not used by any test
```

**Step 3, REASONED from a named rule.** `cmd.exe` does not treat `'` as a quote
character, and neither does the MSVCRT argument parser `git.exe` uses. That is
the audit's mechanism and this repository's own recorded 2026-07-31 finding
(`tools/test_bm_store.py:11318`). With no quotes left in the string, the
mechanism has nothing to act on.

**Step 4, UNVERIFIED LOCALLY, CI IS THE INSTRUMENT.** That `git.exe` then finds
the repository, restores `P/a.py` and leaves `Q/a.py` alone on a real Windows
runner. The equivalent end to end IS executed on POSIX every run, and it passes
(both tests are in the 191 green below).

So:

- **F2 (`test_the_named_repository_beats_an_unstripped_variable`): closed by the
  root-cause fix, no further change needed.**
- **F3 (`test_record_result_rolls_back_in_its_own_project_only`): closed by the
  root-cause fix, no further change needed.** F9's change strengthens it as a
  side effect: its rollback leg used to be reached because `false` exits non-zero
  *if it resolves at all*, and now it is reached because a Python interpreter
  exits 1 deterministically.

**One thing the fix does NOT close, and it is a product hole rather than a test
one.** `tools/bm_controller.py:3647` still applies `shlex.quote` to each
write-scope entry. An entry containing a space comes back POSIX single-quoted and
breaks the same way under `cmd.exe`. No test declares such an entry, so CI is not
affected; the failure direction is the safe one (a non-zero exit is the
dirty-write-scope warning path, so the founder is told rather than silently
misled). The remedy is one line, the same swap `_git_prefix` just took:

```python
bs._quote_path_for_local_shell(_pathspec_literal(p))   # instead of shlex.quote(...)
```

It is byte-identical on POSIX (the helper IS `shlex.quote` there, measured), so
it is zero-risk for the green legs. I did not apply it: it is a product change
outside the audit's eleven findings and outside what this loop was asked to
close, and the orchestrator owns that call. It is written into
`docs/KNOWN-LIMITS.md`.

## 3. Per-finding detail

### F1, closed, plus one hardening the audit did not ask for

The product fix was already in the tree. What I added is at the assertion, and
the reason is measured rather than stylistic. The bare-path assertion the audit
expected to become correct is correct **only while the runner's temporary
directory happens to contain no whitespace and no `cmd.exe` metacharacter**:

```
root C:\Users\RUNNER~1\AppData\Local\Temp\tmp8x1\P   test-as-was assertIn -> True
root C:\Users\runneradmin\My Projects\tmp8x1\P       test-as-was assertIn -> False
root C:\R&D\tmp8x1\P                                 test-as-was assertIn -> False
```

(MEASURED, lexical.) GitHub's own Windows temp path has neither, so the audit's
expectation holds on today's image. A test that is right by accident of the
runner image is the exact defect class this audit was called to remove, so the
assertion now goes through `bs._quote_path_for_local_shell`, which is what the
composition site itself calls. No branch. On POSIX the helper IS `shlex.quote`,
measured identical, so both lines are byte for byte what they were, and the
property asserted is unchanged: the command names the realpath'd project root as
its git dir and work tree.

### F4 and F5, closed, no branch and no skip

The audit's minimal fix, taken as written. `_env_dump_command(tmp, expression)`
writes the probe script into the same throwaway directory and composes
`"<python> <script>"` with both paths quoted through
`bs._quote_path_for_local_shell`. That removes the `-c` payload from the quoting
question entirely and leaves the thing under test intact: it is still one
founder-shaped shell command string handed to the real `SubprocessCheckRunner`.

MEASURED (lexical), Windows branch:

```
OLD: 'C:\hostedtoolcache\windows\Python\3.9.13\x64\python.exe' -c 'import json, os, sys; ...'
NEW: C:\hostedtoolcache\windows\Python\3.9.13\x64\python.exe C:\Users\RUNNER~1\...\env_dump.py
OLD first token starts with a quote character: True
NEW first token starts with a quote character: False
```

Executed on this Mac, the new form: exit code 0, stdout parsed as a JSON list of
57 names.

REASONED: `subprocess` with `shell=True` on Windows runs
`cmd.exe /c "<command>"`; with more than two quote characters present, `cmd`'s
documented rule 2 strips the first quote and the last quote on the line, leaving
the command intact. UNVERIFIED LOCALLY.

### F6 and F7, disclosed with a measured guard rather than a platform skip

`os.chmod(dir, 0o500)` cannot make a directory non-writable on Windows. Python's
own documentation: only the read-only flag is settable and "all other bits are
ignored" (https://docs.python.org/3/library/os.html#os.chmod). Both tests
therefore ran their whole body against an ordinary writable directory there and
passed while proving nothing.

I did **not** make this a `skipIf(os.name == "nt")`. Each test now calls
`_directory_write_denial_works(directory)`, which chmods, tries to create a probe
file, removes it, restores mode 0o700, and returns what actually happened. Three
reasons it is a measurement and not a platform name:

1. it stops guessing on behalf of a platform nobody here can run;
2. it catches the same vacuous pass on a POSIX machine running the suite as root,
   where 0o500 is also ignored, which the audit did not raise and which is real;
3. it starts proving the property again by itself on any platform where the
   denial ever begins to work, with no edit.

Where it skips, the message states exactly what is lost: nothing then proves that
a read-only diagnostic (F6) or the shipped `status` command (F7) survives a store
directory it cannot write, so a regression reintroducing a read-write connection
would be caught on POSIX only. It also states what still runs there: the sibling
tests that prove no sidecar is created in a WRITABLE directory and that the
read-only connection refuses a write.

MEASURED on this Mac: the denial works (`PermissionError [Errno 13]`), euid
1598639508, so **both test bodies run in full here and the skip does not fire on
any POSIX leg**. On Windows it will fire. That is a loss of a vacuous pass, not a
loss of coverage.

Considered and rejected: blocking the WAL sidecar names by creating DIRECTORIES
called `<db>-wal` and `<db>-shm`, which would deny the write on every platform
including Windows. It is the strongest available answer and it may well be right,
but whether SQLite's Windows VFS then still opens the database read-only cannot
be established without a Windows runner, and getting it wrong turns a currently
green leg red. Proposed as a follow-up rather than smuggled into a
make-CI-green loop.

### F8, closed

`ntpath.expanduser` reads `USERPROFILE`, then `HOMEDRIVE` plus `HOMEPATH`, and
consults `HOME` only on POSIX. MEASURED:

```
posixpath.expanduser('~') with HOME only       : /throwaway/home
ntpath.expanduser('~')    with HOME only       : ~            <- guard inert
ntpath.expanduser('~')    with USERPROFILE set : C:\throwaway\home
```

`_cli_env` now pops and sets `USERPROFILE` alongside `HOME`. Nothing in
`bm_store.py` or `bm_controller.py` calls `expanduser` today (grepped, zero hits),
so no test was failing over this; the fix makes the docstring's safety claim true
on both platforms instead of on one.

### F9, closed for the tests, disclosed for the product

`true` and `false` are POSIX shell builtins. `cmd.exe` has neither and there is no
`true.exe` in `System32`; they resolve on a GitHub-hosted Windows runner only
because that image puts Git for Windows' `usr/bin` on PATH, which the audit
flagged as single-sourced and which I did not independently confirm. I did not
try to confirm it, because the fix removes the dependency rather than betting on
it.

Two shared constants replace four literals:

```python
_DONE_CHECK_PASSES = "%s -c pass" % bs._quote_path_for_local_shell(sys.executable)
_DONE_CHECK_FAILS  = '%s -c "raise SystemExit(1)"' % bs._quote_path_for_local_shell(sys.executable)
```

Executed on this Mac: exit 0 and exit 1 respectively. The interpreter running the
suite is the one dependency that cannot be missing. MEASURED (lexical) Windows
spelling: `C:\hostedtoolcache\...\python.exe -c pass`, bare, because that path has
no whitespace and no metacharacter. REASONED: `cmd`'s rule 2 leaves the
double-quoted failing payload intact. UNVERIFIED LOCALLY.

**Disclosed and NOT changed:** `tools/bm_controller.py:3180` defaults an empty
`done_check` to the literal string `"true"`, so the shipped product carries the
same POSIX assumption for any unit that declares no done-check. Changing it
changes shipped behaviour for every such unit, which is a founder-visible
semantic change rather than a test fix. Written into `docs/KNOWN-LIMITS.md`.

### F10, disclosed with a privilege guard

Kept green, not churned, exactly as instructed. `os.symlink` is now called through
`_symlink_or_skip`, which skips with a named reason if the call raises. The guard
is on the PRIVILEGE, not on `sys.platform`, deliberately unlike the sibling
convention at `tools/test_bm_fence_hook.py:610`: the current runner grants
`SeCreateSymbolicLinkPrivilege` (measured by CI run 30980039674, where both tests
passed on both Windows legs), and that real coverage must keep running. What this
buys is the loud failure the brief asked for: without it, a runner image that
stops granting the privilege raises `OSError [WinError 1314]` out of a SETUP
line, which unittest reports as an ERROR in a test about path escapes, naming
neither symlinks nor privilege.

### F11, closed, priority LOW and the reason recorded in the code

`shlex.split` is POSIX-mode by default, so substituting a Windows checkout root
BEFORE splitting fed it a string full of backslashes and ate every one of them.
MEASURED:

```
ROOT 'C:\a\b\checkout'
  OLD argv: ['python3', 'C:abcheckout/tools/bm_store.py', 'init']
  NEW argv: ['python3', 'C:\\a\\b\\checkout/tools/bm_store.py', 'init']
```

Fixed by splitting first and substituting into each argv element, because the
printed line carries only the `<checkout>` placeholder, which has nothing shlex
can misread. No branch. The comment in the code records that this is LOW priority
and why: the `suite` job that runs this file is ubuntu and macos only, so the
line has never had a Windows reader, and it becomes a push blocker only if this
suite ever joins the `store` job.

## 4. Done-check, run after the last edit

Commands quoted verbatim, output verbatim, all on this Mac:

```
$ python3 tools/test_bm_controller.py    ->  Ran 191 tests   OK   (exit 0)
$ python3 tools/test_bm_store.py         ->  Ran 908 tests   OK   (exit 0)
$ python3 tools/test_bm_runtimes.py      ->  Ran 59 tests    OK   (exit 0)
```

Identical test counts to the baseline taken before the first edit (191 / 908 /
59), so nothing was added, removed, skipped or silenced on this platform.

The glob allowance rule was not touched, and its sweep was re-run after the last
edit:

```
glob allowance sweep (TestGlobAllowancesGrantOnlyWhatTheyLiterallyMatch.
                      test_no_declarable_path_names_a_file_its_contract_refuses)
  allowed spellings swept : 132
  candidate spellings     : 42
  triples checked         : 55440
  VIOLATIONS              : 0
  violations under a NON-GLOB allowance: 0
  assertGreater(triples, 20000) -> True
  assertEqual(non-glob violations, []) -> True

$ python3 -m unittest test_bm_store.TestGlobAllowancesGrantOnlyWhatTheyLiterallyMatch -v
  Ran 3 tests   OK
```

The companion write-scope spelling sweep, also re-run, also unchanged:

```
  checked=2954 accepted=422 violations=0
```

`tools/bm_store.py` was not modified in this loop at all, so no rule it holds
could have moved.

Two suites outside the brief's done-check were run as insurance against a
structural gate, because both scan the files I edited:
`python3 tools/test_bm.py` -> `OK (skipped=1)`, `python3 tools/test_bm_docs.py`
-> `Ran 199 tests, OK (skipped=5)`. `tools/test_all.py` was NOT run, as
instructed.

## 5. Files changed

- `tools/test_bm_controller.py`: F1 assertion, F4, F5, F7, F8, F9. One unused
  `import shlex` removed, because the last use of it went with F4 and F5.
- `tools/test_bm_store.py`: F6, F10. (The colon-fix hunk in this file's diff is
  the orchestrator's pre-existing uncommitted change, untouched.)
- `tools/test_bm_runtimes.py`: F11.
- `docs/KNOWN-LIMITS.md`: one new section carrying the four standing gaps and the
  two disclosed product observations.
- `docs/program/absolute-lead/evidence/RED-windows-blind.txt`: the executed
  evidence.
- `tools/bm_controller.py`: NOT changed by this loop. The diff it carries is the
  orchestrator's `_git_prefix` fix.

`docs/program/absolute-lead/evidence/L03/E4-endtoend.json` also shows as modified.
That is not an edit: `TestEndToEndE4` regenerates it on every run by design and
its own docstring says so, and the only bytes that differ are four uuid4
`checkpoint_ref` values minted by this run's store.

## 6. What I did not do, and what could still go wrong

- **I never ran anything on Windows.** Restated here because it is the single
  largest caveat on this report. The five red findings were red by lexical
  argument and are green by lexical argument; the instrument that settles them is
  the next CI run.
- **I did not verify that `true.exe` is or is not on the `windows-latest` PATH.**
  The fix removes the dependency instead, so the question stopped mattering, and
  the audit's single-sourced claim about it is neither confirmed nor relied on.
- **I did not change `tools/bm_controller.py:3647`** (`shlex.quote` on write-scope
  entries) or **`:3180`** (the `or "true"` done-check default). Both are real
  Windows-facing product holes of the same class, both are disclosed above and in
  `docs/KNOWN-LIMITS.md`, and both have a stated one-line or founder-decision
  remedy.
- **I did not add the stronger Windows-real variant of F6 and F7** (blocking the
  sidecar names with directories). Rejected for this loop because it cannot be
  verified without a Windows runner and its failure mode is turning a green leg
  red.
- **I did not read all 7233 lines of `tools/test_bm_controller.py`.** I read the
  eleven sites named by the audit, the helpers they use, and the CLI section
  around them. The audit's own coverage caveat therefore still stands unchanged:
  a platform assumption hidden in the in-process engine section, which contains
  none of the scanned tokens, would have been missed by both of us.
- **Residual risk on the two new skips.** If Windows CI reports a skip for the F6
  and F7 tests where the founder expected a pass, that is this change working as
  designed, not a regression. The tests stopped claiming something they never
  proved there.
