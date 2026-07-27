# Known-mistakes ledger (never repeat these)

LOAD WHEN: before repeating a pattern that has failed before, such as dispatching writers, resuming after a kill, or running a build.

(Extracted verbatim from SKILL.md section 13; see SKILL.md for the full law.)

## 13. Known-mistakes ledger (never repeat these)
- Two writers in one tree collide: fence first, dispatch second.
- Session limits kill agents mid-flight: edits survive; message-resume by id works
  and is first choice (proven repeatedly); when resume fails, the TREE is the truth:
  diff the fence set, distill into STATE.md, relaunch fresh from there; never
  duplicate a possibly-live writer.
- Scratchpads are wiped: durable path under home the moment a deliverable exists;
  and because disk-first is prose the DYING context cannot be trusted to run, a
  PreCompact hook (tools/bm_autosave.py) snapshots the whole tree, untracked files
  included, to refs/brothermode/autosave (local git only, never pushed) at the
  token-death moment, and `bm_autosave.py recover` restores it. A resumed session gets the THREAD back too: a PreCompact brief
  (bm_telemetry.py precompact-brief) distills the dying transcript tail, and a
  write-ahead intent line (bm_telemetry.py intent) logged BEFORE a risky action
  means death leaves a forward-looking record, not just files.
- Compilers catch what reading misses: build after every edit, even one line.
- This machine's disk fills mid-build: clear DerivedData and stale simulators before
  large builds; never let ENOSPC kill a gate run.
- Simulator limits exist (CoreAnimation video compositing crashes in sim): verify at
  the reachable layer and name the device-only remainder.
- Paths, flags, API names, and column names are never typed from memory.
- A disproven plan assumption stops the plan: rewrite before more code.
- Generated files are never hand-edited; edit sources and regenerate.
- A headline number shown before its independent second check is not a result.
- Filed models drift from their formulas: recompute totals from components.
- Refuted and by-design findings are settled: check the ledger before reopening.
- Batch scripts log each move AT the move, never at script end (a crash orphaned 5
  unlogged moves); dedup hashing skips symlinks (a link got crowned over its target).

