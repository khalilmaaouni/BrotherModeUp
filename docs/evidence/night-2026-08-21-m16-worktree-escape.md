# M16, worktree root resolution: does the escape still happen by default

Status: CURRENT. Recorded 2026-08-21, night session, measurement only, no
fix attempted. HEAD at measurement time: `adf7fa6` on `main`.

THE QUESTION: is M16 (docs/plan/QUEUE.json, state "queued") actually still
open, given that tonight's run brief said a now-merged branch "holds the
ceremony change, the stale-board fix, and M16"?

VERDICT: M16 REPRODUCES by default. A bm_ tool invoked from inside a git
worktree nested under a main checkout, with BROTHERMODE_ROOT unset, resolves
root to the MAIN checkout's marker and reads/writes that store, exactly as
M16 describes. Nothing in the current tree closes it; the run brief's
"holds... M16" meant the branch holds the queue ENTRY for M16 (it was added
to the board that evening), not a fix for it. The mechanism that could
refuse this exists in code and is opt-in everywhere; every production caller
relies on the escaping default.

## THE CONTRADICTION, RESOLVED

`git log --oneline --all --grep=M16` returns five commits. Two touch code
(`153392e`, `c423307`); both touch only board/documentation files
(`docs/handover/2026-08-20-ceremony-close/GANTT.html`, `docs/plan/GANTT.html`,
`CHECKSUMS.sha256`). `153392e`'s own commit message says it plainly:

```
$ git log -1 --format="%B" 153392e
...
Two of the cut debate's four blockers were already closed by direct attack;
the other two are disclosed in the CHANGELOG and queued as R1 and R2. This
session's board row claiming four open was the inaccurate one, so their
version was restored as the base and only the genuinely new evening content
was added on top: the ceremony change, the stale-board fix, the install
currency finding, the worktree escape queued as M16, and the two decisions
recorded this evening.
```

That is the source of tonight's brief. "Holds... M16" is this commit
carrying the fact that M16 was QUEUED, into the merged board. It says
"queued as M16" in its own words. The other three M16-grep hits
(`a6e3c97`, `8543e8a`, `e7210b7`) are unrelated: they match on an
unconnected "M16" substring inside a founder-laws encoding commit, not this
queue item. None of the five modifies `tools/bm_store.py` or
`tools/bm_fence_hook.py`.

`docs/plan/QUEUE.json` line 1411 confirms directly:

```
$ sed -n '1411,1424p' docs/plan/QUEUE.json
  {
   "id": "M16",
   "title": "a bm_ tool run from inside a git worktree walks UP and finds the
   MAIN checkout's .brothermode marker...",
   "state": "queued",
   "stage": "provenance",
   ...
```

## CALLER INVENTORY

`tools/bm_store.py:335` defines `resolve_root(start=None,
refuse_past_git_boundary=False, env_must_contain_start=False)`. The refusal
branch (raises `OwnershipRefused("root-ambiguous", ...)` when a marker sits
above a nearer `.git`) only fires when the caller explicitly passes
`refuse_past_git_boundary=True`. A repo-wide scan of `tools/*.py` and
`scripts/*.py` (regex on real call sites, docstring mentions excluded and
verified by hand) found:

| category | files | pass `refuse_past_git_boundary=True`? |
|---|---|---|
| `bm_store.py` itself (11 internal call sites in its own CLI verbs) | 1 | No, all default False |
| write-protection fence hook | `bm_fence_hook.py` (3 call sites) | No, all default False |
| `require_root()` callers | `bm_project`, `bm_learn`, `bm_docs_export`, `bm_packs`, `bm_lead`, `bm_sentinel`, `bm_autonomy`, `bm_handover`, `bm_view`, `bm_controller`, `bm_continue`, `bm_docs`, `bm_threads` | No, 0 of 13 |
| `resolve_root()` callers | `bm_stall`, `bm_autosave`, `bm_bash_audit`, `bm_runtimes`, `bm_passport`, `bm_idle`, `bm_progress_check`, `bm_toolkit`, `bm_telemetry`, `bm_forecast`, `bm_reality`, `bm_statusline`, `scripts/bm_shell` | No, 0 of 13 |
| independent reimplementation, structurally cannot opt in | `bm_escalate.py` (own `resolve_root(start=None)`, same marker-beats-git order, no `refuse_past_git_boundary` parameter exists at all) | N/A |
| **production total** | **29 files** | **0 pass True** |
| opt-in exercised at all | `tools/test_bm_store.py`, 5 call sites | Yes, but test-only, wired to nothing |

`grep -rn "refuse_past_git_boundary=True" tools/ scripts/ --include="*.py"`
returns exactly those 5 lines, all in `tools/test_bm_store.py`. Zero
production call sites anywhere in `tools/` or `scripts/` pass it. The
mechanism is proven correct in isolation by its own test file and used by
nobody.

`scripts/doctor.py:439` mentions `resolve_root()` in a docstring sentence
about precedence; it does not call it and is not counted above.

## THE MEASUREMENT

Method: rather than probe the live, in-use `/Users/khalil.maaouni/Documents/BrotherModeUp`
store while another session's gate was running against it (a real risk:
`ReadOnlyStore` can quarantine a store it judges corrupt, and a live
concurrent writer is exactly the condition that produces false corruption
reads), a throwaway clone of this repository was made under `/private/tmp`,
carrying the identical `tools/bm_store.py` at the same commit. This
reproduces the exact mechanism (same code, same marker-vs-git precedence)
without any possibility of touching the real project's store. The real
repository was never written to; `git status`, HEAD, and `git worktree list`
in `/Users/khalil.maaouni/Documents/BrotherModeUp` were confirmed identical
before and after.

```
$ git clone --no-hardlinks --quiet /Users/khalil.maaouni/Documents/BrotherModeUp \
    m16-fixture/m16-main
$ cd m16-fixture/m16-main && python3 tools/bm_store.py init
bm_store: initialized .../m16-fixture/m16-main/.brothermode/store.sqlite3 (root resolved via git)
```

FIRST ATTEMPT, and why it is in this record: a worktree created as a SIBLING
of `m16-main` (`git worktree add ../m16-worktree`) did NOT reproduce the
escape; `init` from inside it resolved via "git" to itself. That is correct:
walking UP from a sibling never passes through `m16-main` at all, because a
sibling is not an ancestor. The real incident, and this project's own
convention for spawning agent worktrees, nests the worktree INSIDE the main
checkout (`git worktree list` on the real repo shows seven live worktrees at
`.claude/worktrees/agent-*`, each a subdirectory of the checkout it belongs
to). The fixture was rebuilt to match that nesting, since nesting, not
"being a worktree" in the abstract, is what puts the main checkout's marker
in the walk-up chain:

```
$ cd m16-fixture/m16-main
$ git worktree add -b m16probe-nested-branch wt-holder/m16probe HEAD
$ ls wt-holder/m16probe/.brothermode
ls: wt-holder/m16probe/.brothermode: No such file or directory
$ file wt-holder/m16probe/.git
wt-holder/m16probe/.git: ASCII text        # gitdir: pointer, confirms real worktree
```

DEFAULT RUN, cwd inside the nested worktree, `BROTHERMODE_ROOT` unset:

```
$ cd m16-fixture/m16-main/wt-holder/m16probe
$ unset BROTHERMODE_ROOT
$ python3 tools/bm_store.py init
bm_store: initialized .../m16-fixture/m16-main/.brothermode/store.sqlite3 (root resolved via marker)
```

Root resolved to the MAIN checkout (`m16-main`), not the worktree it was run
from. Source reported: "marker". This is the defect, reproduced.

A second, purely read-only run (fresh worktree, never touched by any prior
write, so nothing it does can be explained by leftover state) confirms it
without creating anything:

```
$ git worktree add -b m16probe-readonly-branch wt-holder/m16probe-readonly HEAD
$ cd wt-holder/m16probe-readonly
$ ls .brothermode
ls: .brothermode: No such file or directory
$ python3 tools/bm_store.py dump | sed -n '36,48p'
    { "key": "schema_version", "value": "21" },
    { "key": "project_uuid", "value": "8b65887da9fa4bb9839bc08683e52178" },
    { "key": "created_at", "value": "2026-08-20T19:30:18Z" }
$ ls .brothermode
ls: .brothermode: No such file or directory   # dump created nothing locally
```

`project_uuid` and `created_at` are set once, at `init`, and never rewritten.
Both values are byte-identical to `m16-main`'s own store, confirmed by
`dump`ing `m16-main` directly first and diffing the two JSON outputs (62
lines each; the only differences before this second worktree existed were
those two fields, because they are the two fields distinguishing separately
created stores). `dump` uses `require_root()` (the same escaping default)
and `ReadOnlyStore`, which the code documents as never creating a store; the
worktree carries no `.brothermode` before or after. The tool run from inside
the worktree read the main checkout's data, not the worktree's, and touched
nothing locally to do it.

## THE CONTROL

Same cwd (the worktree), same command, only `BROTHERMODE_ROOT` changed. This
is what proves the instrument discriminates rather than always printing the
same answer.

Write-flavored control, on the first worktree:

```
$ cd m16-fixture/m16-main/wt-holder/m16probe
$ export BROTHERMODE_ROOT="$PWD"
$ python3 tools/bm_store.py init
bm_store: initialized .../wt-holder/m16probe/.brothermode/store.sqlite3 (root resolved via env)
$ ls .brothermode
store.sqlite3        # the worktree now genuinely has its own store
```

Read-only control, on the untouched second worktree (still carries no store
of its own, so the honest answer is refusal, not a silent fall-through to
main):

```
$ cd m16-fixture/m16-main/wt-holder/m16probe-readonly
$ export BROTHERMODE_ROOT="$PWD"
$ python3 tools/bm_store.py dump
refused (no-store): no store exists at .../wt-holder/m16probe-readonly/.brothermode/store.sqlite3;
run `python3 .../wt-holder/m16probe-readonly/tools/bm_store.py init` to create one
exit=2
$ ls .brothermode
ls: .brothermode: No such file or directory
```

Source flips from "marker" (default, escapes to `m16-main`) to "env" (root
pins to the worktree) with nothing else changed. The second control shows
the env path does not silently fall back to the escaping default either: it
refuses, naming the worktree's own path. Both directions discriminate
cleanly.

Cleanup: both worktrees removed with `git worktree remove --force` (force
only because they held no changes of their own, not to override a real
refusal); both exited 0; `git worktree list` on `m16-main` afterward shows
only `m16-main` itself. The throwaway clone lives under
`/private/tmp/.../scratchpad/m16-fixture/` and was never inside the real
repository.

## GIT HISTORY CHECK

```
$ git log --oneline --all --grep=M16
153392e The board merges the evening onto the closing session's own, instead of over it
c423307 The ceremony carries its own next prompt, and stops shipping a board three days stale
a6e3c97 Encode the four laws the founder ratified, in the skill and its references
8543e8a Encode the four laws the founder ratified, in the skill and its references
e7210b7 Encode the four laws the founder ratified, in the skill and its references

$ git log -S refuse_past_git_boundary --oneline
783875f Prove the branches were already merged, and build the machine that refuses the oldest defect
997ec00 Close the four fence-core holes H1 to H4, restore worktree isolation (#18)
a28e5f5 Land the brothermode CLI boundary: thin dispatch, byte-identical contracts, H1 reproduced
1077bdc Close the recovery lie, the git-exposed store, and the unenforced fence
```

All four `refuse_past_git_boundary` commits predate M16 by ten to twelve
days (`997ec00` and `a28e5f5` are 2026-08-08, `1077bdc` is 2026-07-27,
`783875f` is 2026-08-10; M16 entered the queue on 2026-08-20 via `c423307`).
They built the OPT-IN parameter itself, for a DIFFERENT, earlier bug class
(H1 to H4, "restore worktree isolation"). None of them wired any production
caller to pass `True`, which is exactly what the still-empty grep for
`refuse_past_git_boundary=True` outside test files shows tonight. Nothing in
git history closes M16; the parameter it would need already existed before
M16 was even filed, unused then and unused now.

## WHAT WOULD CHANGE THIS VERDICT

A commit that does one of: (a) flips `resolve_root`'s default to
`refuse_past_git_boundary=True` or an equivalent worktree-boundary check
that fires without opt-in, (b) threads `refuse_past_git_boundary=True` (or
a new default-on isolation check) through `require_root()` and every one of
the 29 production call sites named above, or (c) gives `bm_escalate.py` its
own boundary check since it cannot inherit one from `bm_store.py`. Any of
those, followed by re-running the exact DEFAULT RUN above and observing
either a refusal naming `BROTHERMODE_ROOT` or a root resolved inside the
worktree instead of the main checkout, would move this to M16 IS CLOSED. A
partial landing naming which of the 29 callers were converted and which
remain would move it to M16 IS PARTIALLY CLOSED.
