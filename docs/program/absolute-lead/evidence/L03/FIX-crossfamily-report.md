# FIX report, CROSS-FAMILY refuter, controller side

Writer: the controller-side fixer for the cross-family findings in
`/Users/khalil.maaouni/Documents/BrotherModeUp-handovers/2026-08-05-codex-crossfamily-findings.md`.

Files written this round: `tools/bm_controller.py`,
`tools/test_bm_controller.py`, this report, and
`docs/program/absolute-lead/evidence/L03/RED-crossfamily.txt`. Nothing
else. `tools/bm_store.py`, `tools/test_bm_store.py`,
`docs/KNOWN-LIMITS.md` and `docs/FULL-AUTO.md` belong to another writer
this round and were neither read for editing nor touched.

---

## 1. PER-FINDING TABLE

| # | Severity | What it was | Verdict | Where |
|---|---|---|---|---|
| 1 | HIGH | Unvalidated string `retry_ceiling` crashes failure handling | **HANDED BACK** (store side, another writer owns `tools/bm_store.py`) | `bm_store.py:13604`, `:13990` |
| 2 | MEDIUM | Non-dict worker results bypass malformed-result rejection | **CLOSED** | `bm_controller.py` `_handle_worker_result` |
| 3 | HIGH, data destruction | Inherited git environment redirects the rollback outside the contract root | **CLOSED**, two independent defences | `bm_controller.py` `_sanitised_env`, `_git_prefix`, `_rollback_plan` |
| 4 | HIGH | `ReadOnlyStore` opens SQLite read-write before `query_only` | **HANDED BACK** (store side) | `bm_store.py:14257` |
| 5 | MEDIUM | Concurrent replanning resurrects and dispatches a removed unit | **HANDED BACK** (the fix named is `claim_unit`'s missing `status='READY'` predicate, in `bm_store.py:13792`) | `bm_controller.py:1566`, `bm_store.py:13792` |
| 6 | MEDIUM | Concurrent verification overwrites a terminal dispatch verdict | **HANDED BACK** (store side) | `bm_store.py:13926` |

Findings 1, 4, 5 and 6 are NOT mine this round and nothing about them was
changed. Finding 5 has a controller-side anchor (`bm_controller.py:1566`,
the stale `READY` selection), but the refuter's own remedy is the store's
conditional update, so splitting it across two writers in one round would
have produced two half-fixes; it goes back whole.

### Finding 2, what changed

`_handle_worker_result` read `result.get("status")` on its first line,
before the malformed-result branch below it. Reproduced for four shapes
before the fix (probe run in-process against a throwaway store):

```
payload=None    -> RAISED AttributeError: 'NoneType' object has no attribute 'get'
   unit status=DISPATCHED retry=0 run=EXECUTING   dispatches=['DISPATCHED']
payload=['a']   -> RAISED AttributeError: 'list' object has no attribute 'get'
payload='text'  -> RAISED AttributeError: 'str' object has no attribute 'get'
payload=7       -> RAISED AttributeError: 'int' object has no attribute 'get'
```

The shape question now comes first (`shapeless = not isinstance(result,
dict)`), the status read is guarded by it, and the existing malformed
branch takes `shapeless` as a first disjunct so a non-dict result reaches
the SAME recorded rejection any other malformed result reaches. The two
reads inside that branch are guarded as well, so nothing dereferences a
non-dict at any point.

Measured equivalence, after the fix, against the `{"status": "malformed"}`
baseline: dispatch `REJECTED` with verdict `malformed worker output`, unit
back to `READY` with `retry_count` 1, run back to `READY`. The tests assert
against the baseline rather than against hard-coded words, so a future
change to the malformed path cannot leave the non-dict path behind.

Five tests, `TestCrossFamilyF2NonDictWorkerResult`: four shapes plus a
structural one that pins the ORDER (the first `isinstance(result, ...)`
must precede the first read of `result` inside that method), which is what
makes every shape that is not one of the four safe too.

`CONTROLLER_STATE_TRANSITIONS` and `STOP_REASONS` were not widened.

---

## 2. HOW THE GIT ENVIRONMENT VARIABLES WERE ENUMERATED

Not from memory, and not from the brief's list. Three sources on this
machine, git 2.50.1 (Apple Git-155), darwin, Python 3.9.6:

1. **`man git`**, the `ENVIRONMENT VARIABLES` section, extracted with
   `awk '/^ENVIRONMENT VARIABLES/,/^DISCUSSION|^FURTHER DOCUMENTATION/'`
   and `grep -oE '\bGIT_[A-Z0-9_]+'`: **72 names**.
2. **`man git-config`**, whose environment section carries the config
   family the git(1) page does not: **73 names**.
3. **`strings` over the shipped git binary** (`$(git --exec-path)/git`),
   matched against `^GIT_[A-Z0-9_]+$`: **168 names**.

Union: **205 distinct `GIT_` names.**

The interesting part is the disagreement between them. Thirteen of the
fourteen names I would call "redirection class" appear in git(1)'s own
ENVIRONMENT VARIABLES section NOWHERE:

```
  MISSING from git(1): GIT_CONFIG            GIT_CONFIG_COUNT
  MISSING from git(1): GIT_CONFIG_PARAMETERS GIT_ATTR_GLOBAL
  MISSING from git(1): GIT_ATTR_SYSTEM       GIT_GRAFT_FILE
  MISSING from git(1): GIT_SHALLOW_FILE      GIT_QUARANTINE_PATH
  MISSING from git(1): GIT_IMPLICIT_WORK_TREE GIT_EXEC_PATH
  MISSING from git(1): GIT_TEMPLATE_DIR      GIT_REPLACE_REF_BASE
  MISSING from git(1): GIT_PREFIX
  in git(1):           GIT_ALTERNATE_OBJECT_DIRECTORIES
```

That is the whole argument for the rule that shipped. A hand-kept list
built from the primary document would have shipped with those thirteen
holes in it, and `GIT_CONFIG_COUNT` plus `GIT_CONFIG_KEY_n` /
`GIT_CONFIG_VALUE_n` are numbered, so they cannot be listed by name at all.
So **the shipped rule is a PREFIX rule**: `_sanitised_env()` removes every
name beginning with `GIT_` from the child environment, which covers all 205
names today and every name git adds later.

The brief's twelve are a strict subset and are asserted by name in
`test_the_documented_redirection_names_are_all_covered`, together with
seventeen more from the enumeration, so the evidence is a test rather than
this paragraph.

**What the prefix rule costs, stated rather than buried.** A command that
RELIED on an inherited `GIT_AUTHOR_NAME`, `GIT_COMMITTER_EMAIL`,
`GIT_SSH_COMMAND`, `GIT_PAGER` or a `GIT_TRACE*` now sees git's own
configured defaults instead. For this product that is the correct
direction (a done_check that needs an ambient git identity behaves
differently for every founder who runs it), but it is a real behaviour
change and it is the entire known cost. Everything that is not `GIT_` is
passed through untouched, and
`test_the_environment_a_legitimate_command_needs_survives` pins that
`PATH` and `HOME` still reach the child, because an empty environment
would break every real done_check for reasons that have nothing to do with
safety.

---

## 3. THE P AND Q PROOF

### The reproduction, before the fix

The orchestrator's sequence, run by hand first (git 2.50.1, two throwaway
repos, `a.py` committed in both, an uncommitted edit in Q):

```
$ cd P && GIT_DIR=../Q/.git GIT_WORK_TREE=../Q git restore -- a.py
exit=0
Q/a.py now: orig            <- the founder's uncommitted edit is gone
```

Exit 0 is the sharp end: the engine reads a zero exit as a clean rollback,
so no dirty-write-scope warning is queued and no founder step names it.

### The same sequence as tests, failing first

Every failure below is verbatim from
`docs/program/absolute-lead/evidence/L03/RED-crossfamily.txt`, captured
BEFORE any change to `tools/bm_controller.py`:

```
FAIL: test_the_orchestrators_P_and_Q_sequence_leaves_Q_untouched
AssertionError: 'committed\n' != 'FOUNDER EDIT\n'
 : the rollback destroyed an uncommitted edit in an UNRELATED repository:
   git honoured the inherited GIT_DIR and GIT_WORK_TREE over cwd, and exit
   0 made the engine read that as a successful rollback

FAIL: test_record_result_rolls_back_in_its_own_project_only
AssertionError: 'committed\n' != 'FOUNDER EDIT\n'
 : the shipped record-result destroyed an uncommitted edit in an unrelated
   repository: dispatch c7f31c5f0ab4467786ec3ecf6ca00445 rejected; the unit
   re-queues for one retry or escalates, per the circuit breaker

FAIL: test_every_redirecting_variable_is_stripped_from_the_child
AssertionError: Lists differ: ['GIT_ALTERNATE_OBJECT_DIRECTORIES', ...] != []
First list contains 30 additional elements.

FAIL: test_the_only_subprocess_site_passes_an_explicit_environment
AssertionError: 'env' not found in ['capture_output', 'cwd', 'shell', 'text']

FAIL: test_the_rollback_names_its_repository_when_there_is_one
AssertionError: '--git-dir=/private/var/.../P/.git' not found in
                'git restore -- a.py'

FAIL: test_the_named_repository_beats_an_unstripped_variable
AssertionError: 'committed\n' != 'FOUNDER EDIT\n'
```

The second one is the one that matters most: that is the SHIPPED
`bm-controller record-result` command, driven as a real subprocess with
`GIT_DIR` and `GIT_WORK_TREE` pointing at Q, destroying Q's uncommitted
edit. The finding is reachable from a shipped command, not only from the
runner.

### The fix, two defences that do not share a failure point

1. **`_sanitised_env()`**, applied at the ONE subprocess site
   (`SubprocessCheckRunner.run`). Every command this engine runs (the
   done_check, the verifier, the rollback, the founder's whole
   done-definition) starts in an environment with the whole `GIT_` class
   removed. It is total by construction rather than by discipline: the
   engine has exactly one subprocess primitive, pinned structurally by
   `_execution_primitive_offences`, so a command site added later inherits
   the sanitised environment without anyone remembering to ask for it.
2. **`_git_prefix()`**, applied where the rollback is composed. When the
   project root IS a repository root, the command names it:
   `git --git-dir=<root>/.git --work-tree=<root> restore -- <paths>`. A
   command-line `--git-dir`/`--work-tree` beats the environment, verified
   against real git, so a variable that somehow survived defence 1 still
   cannot move this command.

`test_the_named_repository_beats_an_unstripped_variable` proves defence 2
with defence 1 deliberately switched off: it takes the command
`_rollback_plan` composed and hands it to a raw `subprocess.run` carrying
the FULL poisoned environment. Q survives, P is restored. If the two
defences ever collapse into one, that test is what notices.

**The conditional half of defence 2, and why it is conditional.** A
repository that is not at the project root is one this engine cannot name,
and guessing at an ancestor would be a worse answer than git's own
discovery (a BrotherMode project nested inside a monorepo is a legitimate
and supported layout). So with no `.git` at the root the command stays byte
for byte the one this engine has always composed, discovery from cwd
answers exactly as before, and defence 1 is what protects that case. Both
branches are pinned:
`test_the_rollback_names_its_repository_when_there_is_one` and
`test_the_rollback_keeps_its_plain_shape_with_no_repository_to_name`. The
second one also explains why no existing fixture in the suite moved: every
one of them runs against a `tempfile.TemporaryDirectory()` that is not a
repository, so they still see `git restore -- a.py` exactly as they always
did.

A `.git` FILE (a linked worktree, a submodule) is named the same way as a
`.git` directory: git 2.50.1 follows the `gitdir:` indirection through
`--git-dir`, verified in a real linked worktree created with
`git worktree add`. A root whose `.git` is neither makes git exit non-zero,
which IS the dirty-write-scope warning path, so the founder hears about it
rather than the engine silently restoring elsewhere.

---

## 4. THE WIDER QUESTION, ANSWERED HONESTLY

**What the unit's model-authored `done_check` and `verifier` still
inherit.** Everything in the invoking process's environment except names
beginning with `GIT_`. In practice that is `PATH`, `HOME`, `SHELL`,
`TMPDIR`, `USER`, `LANG`, `TERM`, the founder's language and toolchain
variables (`PYTHONPATH`, `VIRTUAL_ENV`, `NODE_OPTIONS`, `JAVA_HOME`, ...),
`XDG_*`, the dynamic-loader variables (`DYLD_*` on darwin, `LD_PRELOAD` and
`LD_LIBRARY_PATH` on Linux), and whatever else the shell exported. They
still run with `shell=True`, with the project root as cwd.

**Can any of them redirect a write outside the project?** Two separate
answers, and only one of them is about the environment.

* **For a git command inside a model-authored check: no longer, as far as
  I could measure.** The `GIT_` class is gone, and I tested the obvious
  non-`GIT_` route as well. A poisoned `HOME` whose `.gitconfig` sets
  `[core] worktree = <other repo>` does NOT redirect `git restore`: run in
  P with `GIT_DIR` and `GIT_WORK_TREE` unset and `HOME` pointing at that
  config, git restored `P/a.py` and left Q's `FOUNDER EDIT` untouched,
  exit 0. git honours `core.worktree` only from the per-repository config.
  I did not sweep every config key that a poisoned `HOME` could set, so
  the honest scope of that claim is `core.worktree` and `git restore`.
* **For the command as a whole: yes, trivially, and no environment rule can
  change that.** A model-authored `done_check` is an arbitrary shell
  string. `rm -rf ~/Documents`, `python3 -c "open('/etc/x','w')"` and
  `cd ../other-repo && git reset --hard` all need no environment variable
  at all. **A general fix is not possible without breaking legitimate
  commands**, and I want that stated in the plainest words available: an
  environment strict enough to bound an arbitrary shell string would have
  to remove `PATH` and `HOME`, at which point almost every real done_check
  ("pytest", "npm test", "swift build") stops working for reasons that
  have nothing to do with safety.

**So what the environment fix actually buys, precisely.** It closes the
class where the ENGINE'S OWN composed command, `git restore --`, the one
piece of destructive text this file writes itself, is silently redirected.
That was the finding, and it is closed twice over. It also removes one
accidental-redirect class from model-authored checks (a `git` invocation
inside a done_check that would have honoured an inherited `GIT_DIR` now
acts on the project it is standing in). It does NOT bound what a
model-authored command can do, and it never could. What bounds those is the
authorisation gate in front of every command (`_run_command`), the risk
classes and allowed paths in the founder's contract, the write-scope
refusals, and the founder reading the unit graph. That boundary is
unchanged by this round, and I am not claiming it moved.

---

## 5. DONE-CHECK, VERBATIM, RUN AFTER THE LAST EDIT

```
### python3 tools/test_bm_controller.py
----------------------------------------------------------------------
Ran 183 tests in 13.361s

OK
EXIT=0
### python3 tools/test_bm.py
Ran 276 tests in 46.108s
OK (skipped=1)
EXIT=0
### targeted
python3 -m unittest test_bm_controller.TestCrossFamilyF2NonDictWorkerResult \
    test_bm_controller.TestCrossFamilyF3InheritedGitEnvironment \
    test_bm_controller.TestCrossFamilyF3ShippedRecordResultCannotBeRedirected
----------------------------------------------------------------------
Ran 14 tests in 1.706s

OK
EXIT=0
```

`tools/test_all.py` and the store suite were NOT run, per the brief.

**No existing test was edited, weakened or deleted.** No collision
occurred: the full controller suite was green on the first run after the
fix, all 183 tests, which includes every fixture that asserts the literal
string `git restore -- a.py` (they run against non-repository temp roots,
so the composed command they see is unchanged) and every structural guard
(`_execution_primitive_offences`, the pinned import list, `_R7_COMMAND_SITES`,
`TestNoSQLGuard`). `_R7_COMMAND_SITES` did not move: no command site was
added or removed this round.

**SECURITY.md was NOT edited.** Its line-count guard does not trip:

```
$ find tools -name "*.py" -o -name "*.sh" | xargs wc -l | tail -1
   93182 total
```

against the 91,100 the document claims, a drift of 2.2 percent, well
inside the 15 percent the guard enforces, and
`test_bm.TestProjectSecurityClaims` passes. Per the brief, the file is left
alone.

---

## 6. WHAT I DID NOT DO, AND WHAT I FOUND IN PASSING

* **Findings 1, 4, 5 and 6 are handed back to the orchestrator**, untouched
  and unverified by me. I did not read `tools/bm_store.py` for editing and
  I make no claim about any of them.
* **`tools/bm_autosave.py` has the SAME class of exposure and I did not fix
  it** (not my file this round). `_git()` at `tools/bm_autosave.py:250`
  builds `e = dict(os.environ)` and runs
  `subprocess.run(["git", "-C", toplevel] + args, env=e)`. `git -C` does
  NOT beat `GIT_DIR`. Measured:

  ```
  plain:    git -C P rev-parse --show-toplevel                          -> .../P
  poisoned: GIT_DIR=.../Q/.git GIT_WORK_TREE=.../Q git -C P rev-parse ... -> .../Q
  ```

  The controller never reaches that file (it loads `bm_store` and nothing
  else), so this is not a controller finding, but it is the same shape and
  it should be closed the same way. A background task chip carrying the
  reproduction and the fix has been raised for it.
* **Every OTHER tool that shells out** was not audited. I checked which
  files import `subprocess` and stopped there.
* **Windows and Linux.** Everything was measured on darwin, Python 3.9.6,
  git 2.50.1 (Apple Git-155). Git's environment precedence is not platform
  specific, but the exact exit codes and the `.git`-file indirection were
  observed on this machine only.
* **The `GIT_` prefix rule was not tested against a founder whose real
  workflow depends on an exported `GIT_AUTHOR_*`.** The cost is disclosed
  in section 2 and in the constant's own comment; incidence was not
  measured.
* **Concurrency.** Every test here is single process except the CLI one,
  where `bm-controller` itself is the second process. Two controllers
  stepping the same project at once was not exercised, which is also where
  findings 5 and 6 live.
* **The store's own view of the composed rollback command** was not
  re-examined. `_rollback_plan`'s output is not persisted; it is composed,
  gated and run, so no stored row changed shape this round.
