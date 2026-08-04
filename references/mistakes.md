# Known-mistakes ledger (never repeat these)

LOAD WHEN: before repeating a pattern that has failed before, such as dispatching writers, resuming after a kill, or running a build.

This file is the LIVE home of the ledger. It began as an extract of SKILL.md's
section 13, and that section no longer exists: the core was cut down and its
routing table now points here instead. Corrected 2026-08-02, when the stale
provenance line was found during a session whose whole subject was recording
its own errors.

## The ledger (never repeat these)
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

- Structured-output caps guessed too tight lose whole agents, and the loss is
  silent until the run dies: size them generously (an unused allowance costs
  nothing, a tight one costs the answer), give a FAILING agent its own relaxed
  schema rather than editing the shared one on resume (a shared-schema edit
  changes every cache key and re-runs work that already succeeded), and never
  let one agent's schema failure kill a fan-out its synthesis depends on. Cost
  when learned: four agents across two runs in one session, 1.3M tokens partly
  re-spent. Evidence: docs/closure/evidence/2026-08-02-wastage-and-errors.md.
- A gate run started while a fleet is in flight measures the machine, not the
  code, and dies at EXIT=143 (SIGTERM, not a test failure): check the suite lock
  AND the load AND what agents are running before starting a suite. Read the
  exit code before calling a gate red.
- Before "fixing" something that looks obviously broken, grep the requirements
  and design records for whether it is deliberate. A true fact with a wrong
  consequence bolted onto it is still a wrong finding (a .gitignore "fix" that
  contradicted requirement R-06, shipped and reverted the same hour).
- When eliminating yourself as the holder of a shared resource, cite the RECEIPT
  in your own transcript, never a probe of the resource. A refusal is one sample
  at one instant; a grant is a recorded fact. Three sessions once triangulated
  onto a wrong conclusion from one unverified premise and sent the founder a
  false alarm.
- A tag that resolves is not a tag whose tree contains what the docs promise:
  check the CONTENTS with git ls-tree, not the ref.
- Documentation suites scan the WORKING TREE, not only tracked files: an
  untracked dated draft sitting in the tree will fail a gate that has nothing to
  do with your change. Run git status before the gate, and preserve rather than
  delete whatever it finds.
- Do NOT implement from a probe's findings while a design for the same item is
  still in flight: implement, then reconcile, and expect the design to be
  better. Shipping first cost a security fix that leaked absolute paths into a
  model-visible deny reason and refused writes in every directory that was not
  a project, with a TEST asserting the wrong behaviour, which is worse than the
  bug. Two rules fell out of it: an error channel a HUMAN reads may name paths,
  an error channel a MODEL reads may not, because nothing is verified at the
  moment a refusal is produced; and when adding a mode that can refuse, the
  case with nothing to enforce must still allow, or the switch bricks every
  unrelated directory the moment it is exported.
- A new failure code, kind or branch gets a DEFAULT that fails safe, so a later
  addition that forgets to name one is refused rather than silently waved
  through the hole the mechanism was audited for.
- A GUI button's label is a SAMPLE, not a property: the app can re-render between
  the screenshot and the click. Re-read the control in the same call that clicks
  it, or click something inert first. Learned by pressing what a screenshot
  showed as "Fetch origin" and what had become "Push origin" by the time the
  click landed. The push was correct and wanted, which is the only reason this
  is a near-miss rather than an incident; the same misread on a Merge or a
  Force-push button is not recoverable.
- A CI result belongs to ONE COMMIT. Quoting a green run beside a newer SHA
  borrows an older commit's evidence for code it never tested, and it reads as
  verification to anyone who trusts the sentence. Name the commit next to the
  verdict, and if the current one has not finished, say "in progress" rather
  than reaching back one commit for a number that looks better.
