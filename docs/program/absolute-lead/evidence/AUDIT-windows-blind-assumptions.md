# AUDIT: platform-blind test assumptions in the tests added by 5afc895, 1e40b8e, 947a793, bdb3920

**FINDINGS: 11** (5 that turn a Windows leg red deterministically, 3 that pass while proving
nothing, 2 environment-dependent, 1 in a suite Windows never runs). All five red ones are in
`tools/test_bm_controller.py`, which **has never executed on a Windows runner even once**.

Audited on macOS 15 (darwin 25.5.0), Python 3.9.6, against
`/Users/khalil.maaouni/Documents/BrotherModeUp` at HEAD `bdb3920` plus the uncommitted change to
`tools/test_bm_store.py`. Date: 2026-08-05.

---

## 0. The single most important fact, and it changes the whole priority order

CI run `30980039674` (the failing push of bdb3920) is readable without a login. Both Windows legs
failed at the FIRST step of the `store` job, and GitHub stops a job at its first failing step, so
every later step was never started:

```
X store (windows-latest, 3.x) in 8m42s (ID 92222321464)
  ✓ Configure git (the recovery suite commits to a throwaway repo)
  X Run V2 store tests
  - Run the project CLI suite
  - Run the autonomy contract CLI suite
  - Run the controller suite
  - Run the recovery suite
```

and the annotation names exactly one failing test, the one already fixed in the working tree:

```
failure: tools/test_bm_store.py failed :: ERROR: test_literal_entries_are_accepted_exactly_as_before
         (__main__.TestWriteScopeEntriesAreNotGitPathspecs.test_literal_entries_are_accepted_exactly_as_before)
```

Two consequences, both measured rather than assumed:

1. **The rest of `tools/test_bm_store.py` is proven green on Windows.** One test errored, not a
   class, not a file. Every other new store test in this range, including the two `os.symlink`
   calls, the `os.chmod(dir, 0o500)` test and the 2954-spelling property sweep, ran on both Windows
   legs and passed. That retires most of the candidate list.
2. **`tools/test_bm_controller.py` has never run on Windows.** `gh run list` shows only one CI run
   between 4d79b77 and now: 5afc895, 1e40b8e, 947a793 and bdb3920 were pushed together, and the
   "Run the controller suite" step (added by 5afc895) was skipped on both Windows legs because the
   store step aborted the job first. 7233 new lines of test, of which the last ~1070 drive real
   subprocesses and real git, have zero Windows evidence behind them.

So the remaining Windows exposure in this range is almost entirely one file.

---

## 1. What the CI config actually runs on Windows

`.github/workflows/tests.yml`, three jobs:

| job | platforms | suites |
|---|---|---|
| `suite` | ubuntu, macos (python 3.9 and 3.x) | `test_bm.py`, `bm_score.py --strict`, `test_bm_autosave.py`, `test_bm_fence_hook.py`, `test_bm_docs.py`, `test_install.py`, **`test_bm_runtimes.py`**, `test_bm_ledger.py`, `test_bm_schema.py`, `test_bm_sentinel.py`, `test_bm_consent.py`, `test_bm_bash_audit.py`, `test_bm_packaging_install.py`, `test_bm_plugin_install.py` |
| `gate` | ubuntu only | `test_all.py` |
| `store` | ubuntu, macos, **windows** (python 3.9 and 3.x) | `test_bm_store.py`, `test_bm_project.py`, `test_bm_autonomy.py`, **`test_bm_controller.py`**, `test_bm_autosave.py` |

Windows runs exactly five suites, in that order, and stops at the first failure.
**`tools/test_bm_runtimes.py` never runs on Windows**, so a finding there is low priority and is
reported as such. Of the three files in the brief, two are on the Windows path
(`test_bm_store.py`, `test_bm_controller.py`) and one is not (`test_bm_runtimes.py`).

---

## 2. Findings, ordered by likelihood of turning CI red

| # | file:line | class | assumption | Windows outcome | confidence |
|---|---|---|---|---|---|
| F1 | `tools/test_bm_controller.py:6876`, `:6878` | 5, process/shell quoting | the composed rollback contains `--git-dir=<path>` unquoted | **FAIL**, deterministic, no subprocess involved | executed probe |
| F2 | `tools/test_bm_controller.py:6916` (assert `:6923`) | 5, shell quoting | POSIX single quotes survive `shell=True` | **FAIL**, git cannot find the repo, P is never restored | executed probe + repo's own recorded precedent |
| F3 | `tools/test_bm_controller.py:7004` | 5, shell quoting | the shipped `record-result` rollback works under `cmd.exe` | **FAIL**, same root cause, end to end | executed probe |
| F4 | `tools/test_bm_controller.py:6829`, `:6830` (assert `:6837`) | 5, shell quoting | `shlex.quote` produces a runnable command | **FAIL**, exit code is not 0 | executed probe |
| F5 | `tools/test_bm_controller.py:6850`, `:6851` (assert `:6856`) | 5, shell quoting | same | **FAIL**, exit code is not 0 | executed probe |
| F6 | `tools/test_bm_store.py:19439` | 4, POSIX file modes | `os.chmod(dir, 0o500)` makes a directory non-writable | **PASSES, proves nothing** | Python docs + CI-measured green |
| F7 | `tools/test_bm_controller.py:7205` | 4, POSIX file modes | same | **PASSES, proves nothing** (never yet run) | Python docs |
| F8 | `tools/test_bm_controller.py:6203` | 6, home directory | setting `HOME` redirects the home directory | guard is **inert**, no assertion breaks | Python `ntpath.expanduser` rule |
| F9 | `tools/test_bm_controller.py:6185`, `:6245`, `:6266`, `:6968` | 5, POSIX-only commands | `true` and `false` are commands | probably passes today by accident of the runner image | UNVERIFIED |
| F10 | `tools/test_bm_store.py:17583`, `:18006` | 4, symlink privilege | `os.symlink` always succeeds | **passed on this runner**, depends on runner privilege | CI-measured green |
| F11 | `tools/test_bm_runtimes.py:837` | 5, shell quoting | `shlex.split` parses a path containing the checkout root | would break, but **Windows never runs this suite** | executed probe (same mechanism as F4) |

---

## 3. Per-finding detail

### F1 (RED, deterministic). `tools/test_bm_controller.py:6876-6878`

```python
root = os.path.realpath(p)
self.assertIn("--git-dir=%s" % os.path.join(root, ".git"), command)
self.assertIn("--work-tree=%s" % root, command)
```

`command` comes from `bm_controller.py::_git_prefix` (`tools/bm_controller.py:735-736`):

```python
return "git --git-dir=%s --work-tree=%s " % (shlex.quote(marker), shlex.quote(root))
```

**Why it differs on Windows.** `shlex.quote` implements POSIX shell quoting only. A Windows path is
full of backslashes, and a backslash is outside shlex's safe character set, so the whole path comes
back wrapped in single quotes. The test then looks for `--git-dir=C:\...` inside a string that
actually reads `--git-dir='C:\...'`, and the substring is not there.

This is not a new lesson for this project. `tools/test_bm_store.py:11318` records the same defect
found by CI on Windows on 2026-07-31, and `tools/bm_store.py:108` exists specifically to replace
`shlex.quote` for exactly this reason. The new controller code reintroduced the pattern the store
already retired.

**Effect.** Test FAILURE (a wrong verdict on POSIX would be impossible; on Windows the assertion is
simply false). No subprocess is involved, so there is no environmental uncertainty at all.

**Probe (executed on this Mac):**

```
$ python3 -c "import shlex; ..."
  shlex.quote('C:\\a\\b\\.git') = "'C:\\a\\b\\.git'"
  composed command       : "git --git-dir='C:\\a\\b\\.git' --work-tree='C:\\a\\b' "
  test asserts substring : '--git-dir=C:\\a\\b\\.git'
  assertIn would pass?   : False
```

**Minimal fix, in the style this repo already uses.** Fix the PRODUCT, not the test: in
`tools/bm_controller.py:735-736`, swap `shlex.quote` for the helper the project built for this,
`bs._quote_path_for_local_shell`. It returns `shlex.quote(path)` unchanged on POSIX
(`tools/bm_store.py:161`) and on Windows quotes with double quotes and only when the path contains
whitespace or a `cmd.exe` metacharacter. With that change the assertion at `:6876` becomes correct
on BOTH platforms with no branch in the test, which is better than branching:

```
_quote_path_for_local_shell (win branch) -> git --git-dir=C:\Users\...\P\.git --work-tree=C:\Users\...\P restore -- a.py
   assertIn('--git-dir=C:\Users\...\P\.git')  passes: True
   assertIn('--work-tree=C:\Users\...\P')     passes: True
POSIX branch is unchanged: shlex.quote('/tmp/x/P/.git') = /tmp/x/P/.git
```

Only if the founder wants the product left alone should the test branch instead, and in that case
the Windows branch must assert the double-quoted form rather than skip.

### F2 (RED, deterministic). `tools/test_bm_controller.py:6916`, assertion at `:6923`

```python
subprocess.run(command, shell=True, cwd=p, capture_output=True, text=True, env=env)
...
self.assertEqual(_read(os.path.join(p, "a.py")), _COMMITTED)
```

**Why it differs on Windows.** `shell=True` on Windows runs `cmd.exe /c "<command>"`, and `cmd.exe`
does not treat `'` as a quote character; neither does the MSVCRT argument parser that `git.exe`
uses. `git` therefore receives `--git-dir='C:\...\.git'` with the quotes as literal filename
characters, fails to find a repository, exits non-zero, and restores nothing. `P/a.py` is still
`_WORKER_EDIT`, so the assertion at `:6923` fails.

The assertion at `:6918` (Q untouched) would pass, but it would pass for the wrong reason: nothing
ran at all. That is the exact failure shape this test class was written to detect, so a green
reading of `:6918` alone would be a false negative.

**Effect.** Test FAILURE.

**Minimal fix.** Same product fix as F1. Once `_git_prefix` quotes for the local shell, the composed
command runs under `cmd.exe` and both halves of this test mean what they say.

### F3 (RED, deterministic). `tools/test_bm_controller.py:7004`

`test_record_result_rolls_back_in_its_own_project_only` drives the shipped
`bm-controller record-result` against a real repository P with a `done_check` of `"false"` and
`done_check_expect_exit: 0`, so the rollback leg is taken on every platform (whether `false`
resolves or not, the exit code is not 0). The rollback command is composed by the same
`_git_prefix`, so it carries the same POSIX single quotes into `cmd.exe` and restores nothing.
`assertEqual(_read(os.path.join(p, "a.py")), _COMMITTED)` at `:7004` fails.

**Effect.** Test FAILURE, and worse, it is the end-to-end proof for a DATA DESTRUCTION finding, so
it is the one test in this file whose silence costs the most.

**Minimal fix.** Same product fix as F1. No test change needed.

### F4 and F5 (RED, deterministic). `tools/test_bm_controller.py:6829-6830` and `:6850-6851`

```python
dump = ("%s -c %s" % (shlex.quote(sys.executable),
                      shlex.quote("import json, os, sys; ...")))
...
outcome = bc.SubprocessCheckRunner().run(dump, cwd=tmp)
self.assertEqual(outcome["exit_code"], 0, outcome["stderr"])
```

**Why it differs on Windows.** Two independent breakages in one string. `sys.executable` is
`C:\hostedtoolcache\windows\Python\3.9.13\x64\python.exe`, which `shlex.quote` wraps in single
quotes, so `cmd.exe` looks for a program whose name literally starts with `'`. And the `-c` payload
is single-quoted, which `cmd.exe` passes through verbatim, so even a correctly named interpreter
would receive `'import` as its first token. Either alone makes `exit_code` non-zero.

**Probe (executed):**

```
shlex.quote('C:\\hostedtoolcache\\windows\\Python\\3.9.13\\x64\\python.exe')
  = "'C:\\hostedtoolcache\\windows\\Python\\3.9.13\\x64\\python.exe'"
```

**Effect.** Test FAILURE at the first assertion in each test.

**Minimal fix, in the project's style.** Do not shell-quote a multi-token payload at all. Write the
probe script to a file inside the throwaway `tmp` directory and compose
`"%s %s" % (bs._quote_path_for_local_shell(sys.executable), bs._quote_path_for_local_shell(script_path))`.
That removes the `-c` payload from the quoting problem entirely and keeps the command a real
founder-shaped `done_check` string, which is the thing under test. The `HOME` half of `:6858`
already guards itself with `if needed in os.environ`, so it needs no change.

### F6 (WRONG VERDICT, not red). `tools/test_bm_store.py:19439`

```python
os.chmod(directory, 0o500)
```

in `test_a_read_only_open_in_a_non_writable_directory_neither_creates_nor_raises`.

**Why it differs on Windows.** The Python documentation for `os.chmod` states: "Although Windows
supports `chmod()`, you can only set the file's read-only flag with it (via the `stat.S_IWRITE` and
`stat.S_IREAD` constants or a corresponding integer value). All other bits are ignored."
(https://docs.python.org/3/library/os.html#os.chmod). For a directory the read-only attribute does
not stop writes inside it, so `0o500` does not make the store directory non-writable. The test then
opens a store in an ordinary writable directory and asserts that nothing was created, which the
fixed code does anyway.

**Effect.** No error. The test PASSES on Windows (measured: it is not in the CI annotation list for
run 30980039674) and proves nothing there. This is the sharp half of a HIGH finding losing its
sharpness on one third of the matrix, silently.

**Minimal fix.** Branch and assert the correct behaviour on each platform rather than skip. On
POSIX keep the chmod. On Windows the equivalent "cannot create a sidecar here" condition is a
directory ACL denial, which needs `icacls` and is not stdlib. The honest middle is to keep the
POSIX branch as the real proof and, on Windows, assert the property that IS reachable there: open
the store read-only while a second handle holds the database, and assert no `-wal` or `-shm`
appears. If the founder judges that too weak, then a `skipIf(os.name == "nt")` with a one-line
reason is acceptable HERE, and what it gives up is stated plainly: on Windows nothing proves that a
read-only diagnostic survives a directory it cannot write, so a regression that reintroduces the
read-write `sqlite3.connect` would be caught on POSIX only.

### F7 (WRONG VERDICT, not red). `tools/test_bm_controller.py:7205`

`os.chmod(store_dir, 0o500)` in `test_status_against_a_non_writable_store_directory_still_reports`.
Identical mechanism and identical fix to F6. This one has never run on Windows, so it has not even
had the chance to pass vacuously yet.

### F8 (INERT GUARD, not red). `tools/test_bm_controller.py:6203`

```python
e["HOME"] = home
```

with the docstring at `:6190-6194` claiming "nothing this section runs can touch the real founder's
home directory or vault".

**Why it differs on Windows.** `ntpath.expanduser` resolves `~` from `USERPROFILE` first, then
`HOMEDRIVE` plus `HOMEPATH`, and only consults `HOME` on POSIX. Setting `HOME` alone therefore
redirects nothing on Windows.

**Effect.** No test fails, because neither `tools/bm_store.py` nor `tools/bm_controller.py` reads
`HOME` or calls `expanduser` (grepped: zero hits). The guard is currently protecting against
something the product does not do. It is reported because the comment asserts a safety property the
code does not deliver on one platform, and a future caller that does use `expanduser` would inherit
a false sense of isolation.

**Minimal fix.** Set `USERPROFILE` alongside `HOME` in `_cli_env`, and pop it in the same loop:

```python
for key in ("BROTHERMODE_ROOT", "BROTHERMODE_VAULT", "HOME", "USERPROFILE"):
    e.pop(key, None)
...
e["HOME"] = home
e["USERPROFILE"] = home
```

### F9 (LATENT, UNVERIFIED). `tools/test_bm_controller.py:6185`, `:6245`, `:6266`, `:6968`

`_UNIT_ONE` uses `"done_check": "true"` with `done_check_expect_exit: 0`; `_cli_sign` and
`_cli_begin` pass `--done-definition true`; `test_record_result_rolls_back_in_its_own_project_only`
uses `"done_check": "false"`. These strings are executed for real by
`SubprocessCheckRunner.run` (`tools/bm_controller.py:261-266`, `shell=True`) whenever a CLI test
reaches `record-result` or `complete`, for example
`test_start_begins_then_resumes_and_completes_with_no_duplicate_work` at `:6337-6343`
(`assertIn("unit u1 accepted", recorded.stdout)`).

**Why it differs on Windows.** `true` and `false` are not `cmd.exe` builtins and there is no
`true.exe` in `System32`. They resolve on a GitHub-hosted Windows runner only because
`C:\Program Files\Git\usr\bin` is placed on PATH by the runner image, which also notes that these
Git-for-Windows Unix tools are slated to be replaced
(https://github.com/actions/virtual-environments/issues/1525). That is a property of the runner
image, not of Windows and not of anything this repository controls.

**Effect.** UNVERIFIED. If `true.exe` resolves, the tests pass. If it ever stops resolving,
every CLI test that reaches a done-check flips to a rejected unit, and the failure will look like a
controller bug rather than a shell-portability one. I could not execute this: I have no Windows
runner.

**Minimal fix.** Replace the POSIX builtins with a command that exists on every platform this
matrix runs and that the project already depends on, for example
`"%s -c pass" % bs._quote_path_for_local_shell(sys.executable)` for the success case and
`"%s -c \"raise SystemExit(1)\"" % ...` for the failure case, or simply `cd .` (a builtin in both
`sh` and `cmd.exe`, exit 0) and `cd nonexistent-dir` (non-zero in both). Whichever is chosen, one
shared constant in the test module rather than four literals.

### F10 (ENVIRONMENT-DEPENDENT, measured green). `tools/test_bm_store.py:17583`, `:18006`

```python
os.symlink(outside, os.path.join(d, "escape"))
os.symlink(outside, os.path.join(d, "src", "app"))
```

**Why it differs on Windows.** Creating a symbolic link needs `SeCreateSymbolicLinkPrivilege`,
which an unprivileged process lacks unless Developer Mode is on and the caller passes
`SYMBOLIC_LINK_FLAG_ALLOW_UNPRIVILEGED_CREATE`; CPython has a long-standing open issue about
passing that flag (bpo-33946, migrated to GitHub issue 78127). Failure would be
`OSError [WinError 1314]` out of the setup line, which is an ERROR rather than a FAIL.

**Effect measured, not assumed:** both tests RAN on both Windows legs in CI run 30980039674 and
PASSED, because the annotation for that run names exactly one failing test and it is not either of
these. The current GitHub Windows runner therefore does grant the privilege. This is reported
anyway because the project's own convention elsewhere does not trust it:
`tools/test_bm_fence_hook.py:610` reads
`@unittest.skipIf(not hasattr(os, "symlink") or sys.platform == "win32", ...)`.

**Minimal fix, and deliberately NOT a `skipIf`.** Guard on the privilege rather than on the
platform, so the real assertion still runs wherever the privilege exists:

```python
try:
    os.symlink(outside, os.path.join(d, "escape"))
except OSError as exc:                       # Windows without the symlink privilege
    self.skipTest("symlink creation unavailable here: %s" % exc)
```

That keeps the Windows coverage the runner currently gives, and degrades to a named skip only on a
machine that genuinely cannot create the link. What the degraded case gives up: on such a machine
nothing proves that `_resolve_against_root` refuses a symlink escape, and the sibling assertions
about `..` escapes still run.

### F11 (LOW: Windows never runs this suite). `tools/test_bm_runtimes.py:837`

```python
argv = shlex.split(line.replace(rt_mod.CHECKOUT_TOKEN, ROOT))
```

`shlex.split` is POSIX-mode by default, so every backslash in a Windows `ROOT` is eaten as an escape
and `argv` is wrong. Same root cause as F4.

**Effect.** Would be a FAILURE, but `tools/test_bm_runtimes.py` runs only in the `suite` job, which
is ubuntu and macos. This is correctly out of the Windows blast radius today. It becomes a
push-blocker the day anyone adds this suite to the `store` job.

Checked and clean in the same file: `tools/bm_runtimes.py:685` and `:694` already normalise with
`.replace(os.sep, "/")`, so the rendered-path assertions at `:561` and `:573` are platform-safe.

---

## 4. Candidates I checked and cleared, with the evidence

These looked like the same class and are NOT findings. Stating them is part of the job.

**The colon fix currently in the working tree is correct, and its reason code is the right one.**
`tools/test_bm_store.py:18638-18667` asserts `bs.OwnershipRefused` with reason `path-escape` on
Windows. I reproduced the exact mechanism with `ntpath` on macOS: the resolver's realpath fallback
rejoins the trailing components, and `ntpath.join` treats any component whose second character is a
colon as a drive specifier and discards everything before it, so the path lands on drive `a:` and
`relpath` cannot express it against `C:`.

```
ntpath.splitdrive('a:b.py')                 = ('a:', 'b.py')
ntpath.join(r'C:\root', 'src', 'a:b.py')    = 'a:b.py'
ntpath.relpath('a:b.py', r'C:\root')        -> ValueError: path is on mount 'a:', start on mount 'C:'
```

`tools/bm_store.py:729-732` catches exactly that `ValueError` and raises `path-escape`. The fix
asserts the reason the code really produces.

**The 2954-spelling property sweep at `tools/test_bm_store.py:18703` survives Windows.** I ran it
for real on macOS and then again through a Windows model built on `ntpath` plus a modelled
`_getfinalpathname_nonstrict` walk-up:

```
POSIX (executed on this Mac):       checked=2954 accepted=422 violations=0
WINDOWS MODEL (ntpath semantics):   checked=2954 accepted=387 violations=0
  assertGreater(checked, 2000) -> True
  assertGreater(accepted, 100) -> True
  assertEqual(violations, [])  -> []
```

Both thresholds hold with room to spare, and the CI run confirms it: this test passed on both
Windows legs.

**`literal_scope_entry("src/a:b.py")` at `tools/test_bm_store.py:18789` is platform-independent.**
It is a purely lexical call (no filesystem), and `_is_absolute_scope` plus `ntpath.isabs` both
return False for that string, so it returns the input unchanged everywhere. Confirmed green on
Windows in CI.

**`_ABSOLUTE_SCOPE_SPELLINGS` and `_PATHSPEC_SCOPE_SPELLINGS`** (`tools/test_bm_store.py:18425-18453`)
including `"C:/Windows"`, `"C:\\Windows"`, `"c:"` and `"\\\\srv\\share"` refuse identically on every
platform, because `tools/bm_store.py:861-874` implements the drive and UNC rules itself instead of
delegating to `os.path.isabs`. Confirmed green on Windows in CI.

**No new test creates a Windows-illegal filename.** I swept every string literal on an added line
that appears in an `os.path.join` / `os.makedirs` / `open` / `_write` / `write_scope` /
`allowed_paths` context across all four changed test files, checking for reserved device names
(`CON`, `PRN`, `AUX`, `NUL`, `COM1`-`COM9`, `LPT1`-`LPT9`, with or without extension), trailing
dots or spaces, and the characters `< > : " | ? *`. Every hit was a message string or a glob
pattern the test deliberately expects to be REFUSED, never a name written to disk. Zero real
findings.

**No timing or ordering assumption.** Every timeout test in `tools/test_bm_controller.py`
(`:512`, `:531`, `:1664-1713`, `:2159-2169`) advances an injected fake clock with
`clock["now"] + datetime.timedelta(seconds=120)`. There is no `time.sleep`, no thread, and no wall
clock anywhere in the added lines, so a slower Windows runner cannot change any verdict.

**No line-ending assumption.** No added test compares exact file bytes, opens in binary mode, or
sets `newline=`. Every file write in the new tests goes through
`io.open(path, "w", encoding="utf-8")`.

**No unlink-or-rename of an open file.** `tools/test_bm_store.py:19408` and
`tools/test_bm_controller.py:7196` both remove sidecars only after the owning `Store` context
manager has closed, or after the CLI subprocess has exited.

**`tools/test_bm_project.py`** contributes 12 added lines in this range, all of them three new
dictionary keys (`controller_dispatches`, `controller_units`, `controller_runs`) in a purge-count
assertion. Nothing platform-dependent.

---

## 5. Product-side observations found on the way (not test bugs, flagged not fixed)

1. **`tools/bm_controller.py:735-736` is a shipped Windows defect, not only a test problem.** The
   rollback command a real Windows founder gets is
   `git --git-dir='C:\...' --work-tree='C:\...' restore -- <paths>`, which `cmd.exe` and PowerShell
   both refuse, so the second of the two independent defences against CROSS-FAMILY finding 3 does
   not exist on Windows. The fix is the one-line swap to `bs._quote_path_for_local_shell` described
   under F1.
2. **`tools/bm_controller.py:3636`** applies `shlex.quote` to each write-scope entry. Entries are
   validated relative POSIX paths, so most come back bare, but any entry containing a space is
   single-quoted and breaks the same way. No new test exercises it on Windows.
3. **A cross-platform authorisation divergence in the write-scope gate, found by the Windows
   model.** Because `ntpath.join` swallows everything before a drive-qualified component, the
   Windows model accepts spellings the POSIX gate refuses, and stores them as something wider:

   ```
   './:/C:'   posix = REFUSED pathspec-write-scope    win = accepted, stored as '.'   (the whole project root)
   'a/C:'     posix = accepted, stored as 'a/C:'      win = accepted, stored as 'a'
   './a:b'    posix = REFUSED absolute-write-scope    win = REFUSED path-escape
   ```

   142 of the 2954 swept spellings resolve differently. The `'./:/C:'` row is the one worth a
   founder decision: on Windows a declaration that reads as git pathspec magic is stored as the
   project root, which is the widest fence and the widest `git restore --` this engine can compose.
   This is a MODEL result from `ntpath` lexical semantics, not a measured Windows run, and it is
   about the PRODUCT rather than about any test. It deserves its own round rather than a patch
   inside this audit.

---

## 6. What I did not check

- **I never executed anything on Windows.** Every Windows claim above is one of: (a) measured from
  CI run `30980039674` and its public annotations, (b) executed on macOS against `ntpath` and
  `shlex`, which are pure-Python and give exact Windows LEXICAL semantics but not syscall
  behaviour, or (c) explicitly labelled UNVERIFIED. The realpath walk-up in section 4's Windows
  model is a model of `ntpath._getfinalpathname_nonstrict`, not a call to it.
- **F9 is unverified.** I did not confirm that `true.exe` and `false.exe` are present in
  `C:\Program Files\Git\usr\bin` on the current `windows-latest` image. The PATH claim rests on a
  single source (actions/virtual-environments issue 1525) and is labelled as single-sourced here.
- **I did not run `tools/test_all.py`**, as instructed. The only commands I ran against this
  repository were read-only `git`, read-only `gh`, and Python probes in throwaway
  `tempfile.TemporaryDirectory()` roots outside the repo. No repository file was modified except
  this report.
- **I did not read all 7233 added lines of `tools/test_bm_controller.py` end to end.** I scanned
  every added line with pattern classes for all eight categories in the brief and then read the
  surrounding code for every hit. The in-process engine section (roughly `:270` to `:6160`) uses
  `FakeWorker` and `FakeCheckRunner` throughout, so its command strings are never executed; that is
  a structural argument, not a line-by-line read, and a platform assumption hidden in a section with
  none of the scanned tokens would have been missed.
- **I did not audit `tools/test_bm_autonomy.py` or `tools/test_bm_autosave.py`.** Neither changed in
  4d79b77..HEAD, and both ran green on Windows at 4d79b77.
- **I did not audit the historical suite**, per the brief.
- **I did not verify the exact `cmd.exe` exit code** for an unresolvable command (1 versus 9009).
  It does not matter to any finding: every assertion involved requires exit code 0.
- **I did not attempt to reproduce F2, F3 or F9 by installing a Windows environment.** The three
  deterministic ones (F1, F4, F5) are proven by executed probes; F2 and F3 rest on the additional
  step that `cmd.exe` does not honour single quotes, which is corroborated by this repository's own
  recorded 2026-07-31 finding at `tools/test_bm_store.py:11318-11322` but which I did not execute.
