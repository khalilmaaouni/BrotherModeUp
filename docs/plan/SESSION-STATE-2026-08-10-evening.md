# Session state, 2026-08-10 late evening

Status: CURRENT. Rewritten mid-flight. Session
6bf23670-87d2-40b0-a728-4896d4db9031. No em or en dashes.

Every claim below is labelled with what actually proves it. Where a loop is not
closed, it says so, because in this project a loop closes only when the full
gate has run on a committed tree after the last edit.

## Main, and the last verdict actually bound to it

`c36bd00`, pushed. Full gate ALL GREEN on that exact commit, clean tree:
`test_all: 2918 tests across 29 suites, 9 skipped, 559.8s wall. ALL GREEN`,
exit 0. HEAD was re-checked after the run and had not moved.

## THE TREE IS DIRTY, and the gate would fail on it right now

Read this before running anything. The failure is expected rather than
alarming: `tools/test_bm_effects.py` exists but is not in `SUITES`, and
`test_all.py` refuses a test file it does not know about.

In the tree, uncommitted:
- `tools/bm_effects.py`, `tools/test_bm_effects.py`: the effect-class registry
  and its purity tests. RED ON PURPOSE.
- `tools/bm_controller.py`, `tools/test_bm_controller.py`: the live deny canary.
- `tools/write_sites.json`: bm_controller 2 to 3, bm_effects added at 2.
- `pyproject.toml`: bm_effects added to py-modules.

## Loop 5, the live deny canary: BUILT AND ITS OWN SUITE PASSES. NOT CLOSED.

PROVEN, by a command this session ran after the last edit:
`python3 tools/test_bm_controller.py` reports `Ran 257 tests ... OK`.
PROVEN, by reading the file rather than the agent's report: the honesty
boundary is present in the docstring and states that a pass proves the hook
binary refuses WHEN RUN and cannot prove the runtime will invoke it.
`TestTheFenceCanaryNeverOverclaimsRuntimeEnforcement` scans the real docstring
and messages against a banned-phrase list.

NOT PROVEN, and this is why the loop is not closed: it has not passed the FULL
gate, it is uncommitted, and CI has not seen it.

Founder context: the founder overrode a recommendation to defer this to the next
session and chose to build it tonight, accepting that tonight may not end with a
tag.

## Loop 2, effect classes: RED, and the red is the deliverable. NOT CLOSED.

THE IMPORTANT FINDING OF THE NIGHT, and it was a correction to this session's
own design. The purity method originally specified COULD NOT SEE THE DEFECT. A
before-and-after snapshot of a throwaway tree returns byte-identical even for
commands that open a writable Store, because sqlite auto-checkpoints and removes
the -wal and -shm files on clean close, `_ensure_git_excludes` is idempotent,
and a pure SELECT leaves the file unchanged. The subagent reported this rather
than forcing a match.

THE REACHABLE CONDITION, found by hand and PROVEN before being written into a
test: a store that is BEHIND. `Store.__init__` calls
`_verify_schema_or_raise(migrate=True)`, so a documented read-only command
MIGRATES an out-of-date database. Evidence: a store forced to schema_version 17
was handed to `bm_project.py status --project-id nosuch`; it exited 1 having
found no such project, and the database came back at schema_version 18 with a
different md5. Both the version and the file hash were compared.

Worth recording: THREE earlier probes of mine failed to reach this defect and
each returned a null I could have written down as a finding. That is the same
class the finding itself is about.

`TestPurityUnderAStoreThatIsBehind` encodes the condition and re-downgrades the
store before EVERY command. Without that reset only the first offender is
caught, because a migrated store cannot be migrated again. That single fix took
it from 1 offender to 3.

Offenders as measured, with a dispatched agent fixing them at the time of
writing:
- `bm_docs.py tier`
- `bm_project.py alert list`
- `bm_threads.py recommend`
- `bm_threads.py dashboard`, failing two further ways: it never parses argv so
  `--help` falls into the body, and it rewrites STATE.md via
  `_refresh_root_view`.

## What the successor does next, in order

1. Take the fix agent's result and VERIFY IT by running
   `python3 tools/test_bm_effects.py` rather than believing the report.
2. Apply the deltas it names outside its fence, likely `write_sites.json`.
3. Register `test_bm_effects.py` in `SUITES` in `tools/test_all.py` and add a CI
   step. NO APOSTROPHE in that comment; the fact loader parses the tuple quote
   to quote.
4. Regenerate `CHECKSUMS.sha256` LAST, after `git add`, with
   `sh scripts/checksums.sh CHECKSUMS.sha256`, never by redirecting stdout.
5. Full gate on a COMMITTED clean tree:
   `BROTHERMODE_SESSION_CAP=99 python3 tools/test_all.py`. Only then are Loops 2
   and 5 closed.
6. Loop 4's last item: widen the docs drift suite so a security verb with no
   nearby test reference fails.
7. Loop 6, the Codex audit, then triage. The founder confirmed an unresolved
   CRITICAL or HIGH HOLDS the tag.
8. Loop 7, the tag. FOUNDER GATE, not cut without an explicit yes.

## Approved, specced, NOT started: the control dashboard

`docs/superpowers/specs/2026-08-10-project-control-dashboard-design.md`,
committed. The founder approved the design and scheduled the build AFTER the
tag. Core finding: the dashboard already exists as generated
`PROJECT-VIEW.html`, and the hand-kept Gantt is a second renderer that gets
deleted on convergence. The founder separately asked for the page design to be
locked as a standard; colour is already one source in `bm_visual.py`, so the
drift is in layout, and the addendum locks one skeleton.

## The gap found FIVE times today and still not fixed

Stale fences from dead sessions block writers forever: README.md, SKILL.md
twice, the findings ledger, and the README narrowing itself. Each was cleared by
hand. Nothing sweeps for a fence whose owner can never return. No owner, belongs
in the next program.

## Live fences held by this session

`release-v310-plan`, `readme-claim-narrowing`, `effect-classes-registry`,
`live-deny-canary`, `dashboard-spec`, plus the adopted `FENCE L3b` in STATE.md.

## Watchdog, armed 2026-08-10 late evening on founder instruction

READ-ONLY, and that is a deliberate override rather than an omission. The
overnight-watchdog skill carries a clause saying an idle tick should resume
unblocked work. The founder's recorded decision of 2026-08-09, taken after the 8
August runaway, makes this watchdog read-only and explicitly overrides that
clause. The tick prompt says so in its own words, so a future session reading
only the prompt cannot reintroduce the behaviour by following the skill.

Armed:
- Cron job `61f6f103`, twice hourly at minutes 13 and 43. Dispatches ONE haiku
  agent (cheap tier, mechanical fact-gathering, no judgement) to gather git
  state, the progress-page verdict, load and disk, then the orchestrator writes
  a report under 12 lines. Carries a STALL RULE (same item in flight across
  three ticks with no commit is reported STALLED, never retried) and a HARD STOP
  at 07:00 local.
- Persistent monitor `b5pusgfev`, polling for foreign commits on origin/main
  every 60 seconds. A foreign commit means stop writers and coordinate, never
  overwrite.

LIMITATION, stated because it decides whether the founder can rely on it: BOTH
are SESSION-ONLY. They live in this Claude session's memory, are written to no
file, and DIE THE MOMENT THIS SESSION ENDS. A successor session must re-arm them
and this file is where it learns that. Nothing on disk enforces their existence.

## Agents in flight at the time of writing

- ReadOnlyStore routing for the three migrating commands plus the dashboard
  help gate. Fence `effect-classes-registry` covers the registry; the fix agent
  owns bm_docs.py, bm_project.py, bm_threads.py.
- The security-verb drift check, Loop 4's last item. Fence
  `security-verb-drift`, owns tools/test_bm_docs.py only, and is briefed to
  REPORT the pages it flags rather than edit them, so the detector's evidence
  survives.

---

## CLOSURE, 2026-08-10 late. LOOPS 2 AND 5 ARE CLOSED.

Not "the suites pass". CLOSED, by the only thing that counts here: the full gate
on a COMMITTED, clean tree, with HEAD re-checked afterwards and unmoved.

```
test_all: 2944 tests across 30 suites, 9 skipped, 622.5s wall. ALL GREEN
exit 0, at commit 1c6fcf4, pushed, local equals upstream
```

Suite count went 29 to 30 and test count 2918 to 2944, which is the effect-class
suite arriving rather than an existing suite growing.

WHAT CLOSED:
- Loop 2, effect classes. Three commands documented as read accessors stopped
  migrating a database that was behind: `bm_project.py alert list` and
  `bm_threads.py recommend` now open ReadOnlyStore, and
  `bm_threads.py dashboard` checks `--help` before doing any work and no longer
  rewrites STATE.md. `bm_docs.py tier` is CORRECTED rather than fixed: its
  docstring said "Writes nothing", which was false, and it is now declared
  ledger_write, the true class. Making it genuinely read-only needs three
  pure-read methods added to ReadOnlyStore and that is named in both files as
  open work.
- Loop 5, the live deny canary, with its founder-facing rewrite landed in
  bm_visual.py.

WHAT DID NOT LAND, as a recorded decision rather than a silent skip: the
security-verb drift check. Its agent returned an honest "not ready to gate CI"
with 167 true positives concentrated in dense reference pages that cite their
proving test once per section rather than once per sentence. Landing it would
have turned the gate red for 167 pre-existing claims unrelated to this release.
FLIP CONDITION: the 167 are triaged, or the check learns to read a citation at
section scope. The finding is real and worth acting on.

A SIXTH stale fence was closed to get here, on tools/bm_visual.py, and STATE.md
held TWO copies of that fence line so marking the first left the second still
refusing. Identical to the SKILL.md trap earlier today.

## UNEXPLAINED FILE, not touched

`docs/plan/COMMAND-CENTER.html`, 22993 bytes, timestamped 2026-08-10 21:54,
untracked. THIS SESSION DID NOT CREATE IT. It is left exactly as found, under
the never-lose-work rule: it may be another session's or an agent worktree's
output. Do not delete it without knowing what it is. Its existence is the reason
`git status` is not empty at handover.

## REMAINING

Loop 6, the Codex cross-family audit, then triage. Loop 7, the tag, founder
gate. Both untouched.
