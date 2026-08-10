Status: CURRENT

# Phase 0 baseline: source commit, environment, gate evidence

Source: `CODEX_PORT_AND_HYBRID_HARNESS_IMPLEMENTATION_SPEC.md` section 13 Phase 0
(tasks 1 to 2, 6), corrected by `docs/plan/PROGRAM-PLAN-2026-08-10.md` Lane CX:
the baseline pins the current commit, never `c36bd00` (the spec's own audit
commit), and the test count is re-derived here rather than copied from the
spec's stale 2,918 figure (the program plan states that number belongs to two
older commits and `test_bm_effects.py` alone added 10 tests since).

## Source commit

Command: `git rev-parse HEAD`, run in this worktree at task start.

```
27a971961c0e79a7018f1203a429bbdc390e3201
```

## Python version

Command: `python3 --version`.

```
Python 3.13.14
```

## Operating system

Command: `uname -srm`.

```
Darwin 25.5.0 arm64
```

## Plugin version

`VERSION`:

```
3.0.1.dev1
```

`.claude-plugin/plugin.json` `"version"` field:

```
3.0.1.dev1
```

Both agree.

## Schema version

Command: `grep -n "SCHEMA_VERSION =" tools/bm_store.py`.

```
tools/bm_store.py:81:SCHEMA_VERSION = 18
```

## Full-gate evidence

Sentinel checked: `/private/tmp/claude-1598639508/-Users-khalil-maaouni-Documents-BrotherModeUp/11cfa3fc-4175-4237-936b-e66e6106af0c/scratchpad/gate-27a9719.done`

The sentinel did not exist when this document was first drafted (the gate was
mid-run, 21 of 30 suites reported). It appeared while this task was still in
progress. `git rev-parse HEAD` was re-checked at that point and still reads
`27a971961c0e79a7018f1203a429bbdc390e3201`, the same commit this baseline
pins, so the verdict below binds to this one SHA.

`.done` file content: `0` (the gate process's exit code).

Last two lines of `gate-27a9719.log` (line 33 is blank, line 34 is the
summary):

```
test_all: 2949 tests across 30 suites, 9 skipped, 421.6s wall. ALL GREEN
```

This re-derived count, 2,949 tests across 30 suites with 9 skips, differs
from the spec's own stated gate ("2,918-test/29-suite baseline") exactly as
`docs/plan/PROGRAM-PLAN-2026-08-10.md` Lane CX warned it would: the spec's
number belongs to an older commit, and `test_bm_effects.py` (10 tests, listed
in the log as `running test_bm_effects.py OK 10 tests 6.6s`) is new in this
tree, plus other suite growth accounts for the rest of the delta. The
30-suite count matches the spec exactly; the skip count (9) also matches.

## Architecture decision record (Phase 0 task 6)

Decision: BrotherMode ships two generated packages, a Claude Code plugin and a
Codex plugin, both built from one host-neutral core (`tools/`, `brotherme/`),
never from two independently maintained trees. Rationale: a shared core with
per-host adapters (`agents/`, `commands/`, `skills/`, `hooks/`, `mcp/`) keeps
the single-writer fence, the store schema, and the scoring logic identical
across runtimes, so a fix lands once instead of twice. Alternative
"rename-in-place" (turn the existing Claude tree into the Codex tree by
renaming Claude-specific files) is rejected: it destroys the Claude package
the moment Codex support lands, with no way to run both packages side by side
to catch regressions, which is exactly the double-loading and drift risk this
decision exists to avoid. Alternative "fork" (copy the repo and diverge a
Codex-only fork) is rejected for the same reason in the other direction: two
copies of identical core logic drift the moment either fork receives a fix
the other does not. Flip condition: this decision reverses only if the Codex
plugin loader is proven to accept the repo root layout directly, the same
layout Claude Code's own plugin loader already accepts, making a second
generated package unnecessary.
