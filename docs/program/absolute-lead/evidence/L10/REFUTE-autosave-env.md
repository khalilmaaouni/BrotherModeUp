# REFUTE: inherited git environment in tools/bm_autosave.py

Adversarial review of unmerged commit `ec5f060` (branch
`claude/pensive-volhard-32adc2`) against main at `75bb1b7`. Every probe ran in
`mktemp -d` throwaway repositories with HOME, BROTHERMODE_VAULT and
BROTHERSBE_VAULT pinned to throwaway paths. Nothing was written in the real
repository except this file. git version 2.50.1 (Apple Git-155).

## VERDICTS

- C1 (main is redirectable by a poisoned environment): **CONFIRMED**, and worse
  than claimed: it destroys data in the innocent repository.
- C2 (ec5f060 closes it): **CONFIRMED** for the whole `GIT_*` class, 19 of 19
  attack cases blocked, including the config-injection family.
- C3 (legitimate use still works): **CONFIRMED**, including a linked worktree
  invoked from a subdirectory.
- C4 (applies on current main, tests pass): **CONFIRMED**, cherry-pick clean,
  43 tests OK, exit 0.

## FINDINGS, worst first

### F1. HIGH, data destruction, present on main today

A poisoned environment does not merely misdirect the autosave. It deletes the
other repository's genuine snapshots and silently reports success.

Calibration first, proving the rig is not broken (plain call resolves P):

```
plain:    git -C P rev-parse --show-toplevel   ->  /private/tmp/.../P
poisoned: GIT_DIR=.../Q/.git GIT_WORK_TREE=.../Q
          git -C P rev-parse --show-toplevel   ->  /private/tmp/.../Q
```

Then main's own code path, `resolve_toplevel(P)` followed by `snapshot(...)`,
with GIT_DIR and GIT_WORK_TREE pointed at Q:

```
resolve_toplevel(P) -> /private/tmp/refute-autosave-DNLgPz/Q
snapshot result: {'ok': True, 'reason': 'precompact', 'commit': '7f79a2e0...',
                  'ref': 'refs/brothermode/autosave/bf891a94683b/sess-poison/...',
                  'latest_published': True}
=== refs in P (the repo we meant to save) ===
P: refs/heads/main
=== refs in Q (the innocent repo) ===
Q: refs/brothermode/autosave/bf891a94683b/latest
Q: refs/brothermode/autosave/bf891a94683b/sess-poison/00001785992461844123-13e49e
Q: refs/heads/main
```

P received no snapshot. Q received two refs and a `.git/brothermode`
bookkeeping directory. The return value says `ok: True`.

The destructive part is retention pruning, which runs against the poisoned
toplevel. Q was first given three genuine snapshots by its own clean autosave,
then one poisoned run aimed at P was fired with retention 1:

```
Q genuine snapshot refs BEFORE poisoned run: 4
poisoned run said: True precompact
Q genuine snapshot refs AFTER: 1
GENUINE Q SNAPSHOTS DESTROYED BY THE POISONED RUN: 4
   DELETED: refs/brothermode/autosave/bf891a94683b/q-legit-0/...
   DELETED: refs/brothermode/autosave/bf891a94683b/q-legit-1/...
   DELETED: refs/brothermode/autosave/bf891a94683b/q-legit-2/...
P autosave refs (founder's repo): []
```

Q's uncommitted working tree edit survives (autosave never checks out), so the
loss is backups plus the founder's unbacked-up work, not files on disk.

Wiring confirmed, so this is automatic, not hypothetical:
`hooks/hooks.json:39` declares `PreCompact`, and line 44 pipes the payload into
`tools/bm_autosave.py precompact`.

Sites on main: `tools/bm_autosave.py:250` (`e = dict(os.environ)`) and
`tools/bm_autosave.py:282` (a second `subprocess.run` in `resolve_toplevel`
with no env argument at all, so it inherits everything).

### F2. C2 and C3 survived every attack I could build

Against the cherry-picked fixed module, 19 cases, each run against fresh repos
P2 and Q2 and each checked on four axes: does `resolve_toplevel(P2)` still
return P2, does the snapshot succeed, does P2 get refs, does Q2 stay untouched.

```
CASE                                   top==P?    snap ok  P refs Q refs
BASELINE-clean                         True       True     2      0
GIT_DIR+GIT_WORK_TREE                  True       True     2      0
GIT_DIR only                           True       True     2      0
GIT_WORK_TREE only                     True       True     2      0
GIT_INDEX_FILE                         True       True     2      0
GIT_OBJECT_DIRECTORY                   True       True     2      0
GIT_ALTERNATE_OBJECT_DIRECTORIES       True       True     2      0
GIT_COMMON_DIR                         True       True     2      0
GIT_CEILING_DIRECTORIES                True       True     2      0
GIT_CONFIG                             True       True     2      0
GIT_CONFIG_GLOBAL                      True       True     2      0
GIT_CONFIG_COUNT+KEY_0/VALUE_0         True       True     2      0
GIT_SSH_COMMAND                        True       True     2      0
GIT_EXTERNAL_DIFF                      True       True     2      0
GIT_PAGER                              True       True     2      0
GIT_EDITOR                             True       True     2      0
GIT_ATTR_NOSYSTEM                      True       True     2      0
GIT_NAMESPACE                          True       True     2      0
GIT_DIR + GIT_NAMESPACE + GIT_CONFIG_COUNT True   True     2      0

FAILURES: 0
Q2 uncommitted edit intact: True
_sanitised_env drops: ['GIT_CONFIG_KEY_0', 'GIT_DIR', 'GIT_NAMESPACE']
_sanitised_env keeps PATH/HOME: {'PATH': '/bin', 'HOME': '/h'}
```

The BASELINE-clean row is the calibration: the same rig, no poison, produces a
working snapshot, so a green row is not the rig failing to do anything.

C3 verified on content, not only on ref counts, and in the hardest legitimate
shape (a linked worktree entered from a subdirectory):

```
linked worktree, from subdir -> toplevel: /private/tmp/.../W2
snapshot: True precompact
captured: ['sub/a.txt | 1 +']
blob: hi | LINKED WORKTREE EDIT
non-git dir -> resolve_toplevel: None
```

Commit attribution still works with no identity in the environment and no
`user.email` configured: every probe above ran with HOME pointed at an empty
throwaway directory and `commit-tree` still produced a commit.

The fixed module has exactly one process-start site and no raw environment
reaching a child:

```
$ grep -n "subprocess\.\(run\|Popen\|call\|check_output\)\|os\.system" tools/bm_autosave.py
325:        return subprocess.run(
$ grep -n "dict(os.environ)\|os.environ.copy()" tools/bm_autosave.py
(none)
```

### F3. MEDIUM. The same class is still open in scripts/

Not re-reported: `tools/bm_controller.py`, already fixed. Found by inspection,
mechanism already proven by the F1 calibration above, no separate exploit rig
built for these:

- `scripts/doctor.py:762` runs `["git", "-C", root, "status", "--porcelain"]`
  with no `env=` argument at all, so it inherits the whole environment. A
  poisoned GIT_DIR makes the release integrity check report a different
  repository's cleanliness. Read only, so misleading rather than destructive,
  but it gates a release verdict.
- `scripts/benchmark.py:73` builds `self.env = dict(os.environ)` and line 99
  runs `git -C self.root ...` with it, including fixture-building writes.
- `scripts/benchmark_comparative.py:107` runs `git -C fx ...` through `_run`
  with `env=None`, which inherits the parent environment.
- `scripts/rehearse_fresh_install.py:211` `build_env` copies the environment
  and strips only BROTHERMODE names, leaving every `GIT_` name, then uses it
  for `git init`, `add` and `commit` at lines 605 to 619.

### F4. LOW. Stated residual, not a defect in the fix

The prefix rule deliberately keeps PATH, so a shadowed `git` earlier on PATH is
executed by the fixed module:

```
PATH->fake git first       resolve_toplevel(P) -> None
fake git log: FAKE GIT CALLED: -C /tmp/.../P2 rev-parse --show-toplevel
```

This is pre-existing and universal (the hook finds `python3` by PATH too), so
it is a boundary to state, not a hole this commit opened. I tried the two
config-file redirects that do not start with `GIT_` and both were refuted:
`HOME` pointed at a `.gitconfig` carrying `core.worktree`, and
`XDG_CONFIG_HOME` pointed at the same, both resolved P2 correctly, at raw git
level and through the module.

## C4, mechanically

```
$ git clone --no-hardlinks <repo> clone && git -C clone checkout main
75bb1b7 Ratify the master plan: ...
$ git -C clone cherry-pick ec5f060
[main e2d2be7] Close the same inherited git environment in autosave
 2 files changed, 409 insertions(+), 8 deletions(-)
--- exit: 0 ---
```

No conflicts, nothing resolved by hand. Done-check in that clone:

```
$ python3 tools/test_bm_autosave.py
Ran 43 tests in 19.196s

OK
=== EXIT: 0 ===
```

## WHAT I COULD NOT CHECK

- `python3 tools/test_all.py` and `tools/test_bm.py` were out of bounds, so I
  cannot confirm the commit message's claim of 276 passing tests in test_bm.py,
  nor that the fix leaves the wider suite green.
- The commit message's enumeration claim (205 distinct `GIT_` names, thirteen
  undocumented redirectors) was not re-derived. I tested the 18 names in the
  brief plus combinations.
- I did not fire a real PreCompact in a live Claude Code session. The wiring is
  confirmed by reading `hooks/hooks.json:39` and `:44`, not by observing the
  harness fire it.
- Non-`GIT_` config redirection was tested only via `core.worktree` in a global
  config. I did not chase `include.path` chains or a system `/etc/gitconfig`.
- macOS and git 2.50.1 only. No Windows or Linux run, and Windows is ratified
  scope for this module.
- The scripts/ findings in F3 are by inspection plus the shared mechanism, not
  by a built exploit for each site.
- I did not review the 325 added test lines for quality, only that they pass.
