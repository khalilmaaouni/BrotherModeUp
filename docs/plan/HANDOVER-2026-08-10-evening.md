# Handover, 2026-08-10 evening

Khalil, I am running out of context and handing over.

Written by session `6bf23670-87d2-40b0-a728-4896d4db9031`. No em or en dashes.

**READ THIS BEFORE ANYTHING ELSE. The working tree is DIRTY and the full gate
would FAIL on it right now.** Nothing below claims the repository is green as it
stands. Each verified row names the COMMIT its evidence belongs to, because a
gate verdict belongs to one commit and this project has already been bitten by
quoting a green run beside a newer SHA.

`main` is at `e37d36a`, pushed, local equals upstream.

---

# 1. VERIFIED, AND AT WHICH COMMIT

Every row names the command that proved it and the commit it was proved at.
None of these was re-run against the current dirty tree.

| What | Proved at | Command and output |
|---|---|---|
| One main branch | current | `git ls-remote --heads origin` returns 1. All 14 tips tagged `archive/<branch>-2026-08-10` and pushed BEFORE any delete. `archive/phase-c-continuity-2026-08-10` still resolves to `22b4c5e` |
| Full gate green | `c36bd00` | `test_all: 2918 tests across 29 suites, 9 skipped, 559.8s wall. ALL GREEN`, exit 0, clean tree, HEAD re-checked after the run and unmoved |
| Wall-clock lint blocking | `c36bd00` | `bm_lint_walltime.py tools/ scripts/` exit 0; `test_bm_lint_walltime.py` `Ran 17 tests ... OK` |
| Progress-page check | `c36bd00` | `test_bm_progress_check.py` `Ran 13 tests ... OK`. Fail-open proven: `sh tools/bm_sessionstart.sh` exits 0 with the tool deliberately absent. Byte-purity proven by hashing a throwaway tree before and after |
| README narrowed | `c36bd00` | `test_bm_docs.py` `Ran 226 tests ... OK (skipped=5)` |
| Decision records ship | `c36bd00` | in `docs/decisions/`, home paths stripped, marked historical with superseded-by pointers |
| Dashboard design specced | `c36bd00` | `docs/superpowers/specs/2026-08-10-project-control-dashboard-design.md` |
| Canary suite passes | dirty tree | `python3 tools/test_bm_controller.py` `Ran 257 tests ... OK`. THIS IS NOT A CLOSED LOOP, see 2b |

## The most important thing I learned, and it corrects my own work

The effect-class purity test I specified COULD NOT SEE THE DEFECT IT WAS BUILT
FOR. A before-and-after snapshot of a throwaway tree returns byte-identical even
for commands that open a writable store: sqlite auto-checkpoints and removes its
`-wal` and `-shm` files on clean close, `_ensure_git_excludes` is idempotent, and
a pure SELECT leaves the file unchanged. A subagent found this and reported it
instead of forcing a match.

The condition that DOES reach it is a store that is BEHIND. `Store.__init__`
calls `_verify_schema_or_raise(migrate=True)`, so a documented read-only command
MIGRATES an out-of-date database. Proven: a store forced to `schema_version 17`,
handed to `bm_project.py status --project-id nosuch`, exited 1 having found no
such project, and came back at `18` with a different md5. Both the version and
the file hash were compared.

THREE of my own probes before that returned nulls I could have recorded as
findings. That is the same defect class the finding is about, committed while
chasing it.

Fixing the test's own under-reporting then took it from ONE offender to THREE:
once the first command migrates the store, a migrated store cannot be migrated
again, so every later command was being measured where the defect was
unreachable.

---

# 2. IN FLIGHT, AND EXACTLY WHERE IT STOPPED

## 2a. Uncommitted, and why the gate fails on it

Expected, not alarming: `tools/test_bm_effects.py` exists but is not in
`SUITES`, and `test_all.py` refuses a test file it does not know about.

```
 M pyproject.toml               bm_effects added to py-modules
 M tools/bm_controller.py       the live deny canary
 M tools/test_bm_controller.py  its tests
 M tools/write_sites.json       bm_controller 2 to 3, bm_effects added at 2
?? tools/bm_effects.py          the effect-class registry
?? tools/test_bm_effects.py     its purity tests, RED ON PURPOSE
```

## 2b. Loop 5, the live deny canary: BUILT, OWN SUITE GREEN, NOT CLOSED

PROVEN: `python3 tools/test_bm_controller.py` reports `Ran 257 tests ... OK`,
run by this session after the last edit rather than taken from the agent report.
PROVEN by reading the file: the honesty boundary states a pass proves the hook
binary refuses WHEN RUN and cannot prove the runtime will invoke it, which is
the Codex gap. `TestTheFenceCanaryNeverOverclaimsRuntimeEnforcement` scans the
real docstring and messages against a banned-phrase list.

NOT PROVEN, which is exactly why it is not closed: no full gate, uncommitted,
CI has not seen it.

Context: you overrode my recommendation to defer this and chose to build it
tonight. The override is recorded in the plan with my recommendation left
visible beside it.

## 2c. Loop 2, effect classes: RED, and the red is the deliverable

`python3 tools/test_bm_effects.py` reports `Ran 10 tests`,
`FAILED (failures=3)`. Every failure is a real defect:

- `bm_docs.py tier` migrates a behind-store
- `bm_project.py alert list` migrates a behind-store
- `bm_threads.py recommend` migrates a behind-store
- `bm_threads.py dashboard` fails two further ways: it never parses argv so
  `--help` falls into the body, and it rewrites STATE.md via
  `_refresh_root_view`

An agent is routing these through `bm_store.ReadOnlyStore`
(`tools/bm_store.py:16345`). At handover its worktree showed `tools/bm_docs.py`
modified. UNVERIFIED: whether it finished, and whether it succeeded.

## 2d. Loop 4's last item

An agent is building the security-verb drift check in `tools/test_bm_docs.py`:
a security verb (refuses, prevents, blocks, guarantees, enforces) in a shipped
page with no test reference nearby should fail. Briefed to REPORT the pages it
flags rather than edit them, so the detector's evidence survives.
UNVERIFIED: whether it finished, and whether false positives are low enough to
block CI. An honest "not ready" was declared acceptable in its brief.

---

# 3. NOT STARTED

- **Loop 6, the Codex cross-family audit.** Read-only. Your decision D8 stands
  and you confirmed it again tonight: an unresolved CRITICAL or HIGH HOLDS the
  tag, even if that means tagging tomorrow.
- **Loop 7, the v3.1.0 tag.** FOUNDER GATE. Not cut without an explicit yes.
- **The control dashboard.** Specced and approved; you scheduled the build for
  after the tag. Plan in section 6.

---

# 4. LIVE FENCES, LOCKS, AND THE WATCHDOG

Held by this session in the store: `release-v310-plan`,
`readme-claim-narrowing`, `effect-classes-registry`, `live-deny-canary`,
`dashboard-spec`, `security-verb-drift`. Plus `FENCE L3b` in `STATE.md`, which
this session ADOPTED from a dead session.

## Watchdog, armed, read-only by your decision

The overnight-watchdog skill says an idle tick should resume unblocked work.
Your recorded decision of 2026-08-09, after the 8 August runaway, overrides
that. The override is written into the tick prompt itself, so a future session
reading only the prompt cannot reintroduce the behaviour by following the skill.

- Cron `61f6f103`, minutes 13 and 43 hourly. One haiku agent for mechanical
  fact-gathering, then a report under 12 lines. Stall rule, hard stop at 07:00.
- Monitor `b5pusgfev`, foreign commits on `origin/main` every 60s.

**TWO LIMITATIONS, both real.**

1. BOTH ARE SESSION-ONLY. They live in this session's memory, are written to no
   file, and DIE WHEN IT ENDS. Nothing on disk enforces them. Re-arm them first.
2. The foreign-commit monitor CANNOT TELL YOUR OWN PUSHES FROM SOMEONE ELSE'S.
   It fired on my own state commit within minutes of being armed. As built it is
   a change detector, not a foreign-change detector. Either compare the pushing
   author against this session's identity, or treat every event as "look, then
   decide". Left as found rather than quietly patched, because an alarm that
   cries wolf is worse than none and you should know which one you have.

---

# 5. THE GAP FOUND FIVE TIMES TODAY AND STILL NOT FIXED

Stale fences from dead sessions block writers permanently. Today on `README.md`,
on `SKILL.md` TWICE, on the findings ledger, and on the README narrowing itself,
where another session had claimed that exact work and died without doing it.

Each cleared by hand. Nothing sweeps for a fence whose owner can never return.
The detection is trivial (is the owning session alive?) and it keeps biting
because nobody looks. No owner. Belongs in the next program.

---

# 6. THE PLAN FOR THE DASHBOARD GANTT

Approved design:
`docs/superpowers/specs/2026-08-10-project-control-dashboard-design.md`.
Build scheduled AFTER the tag, by your decision.

## The finding that shapes the whole plan

THE DASHBOARD ALREADY EXISTS. `tools/bm_view.py render` writes
`PROJECT-VIEW.html` per project from store rows. Its `render_page()` already
accepts status, alerts, insights, briefings, decisions, facts, milestones,
tasks, progress, evidence AND gantt. `tools/bm_visual.py` already ships `gantt`
as its seventh shape with `gantt_facts()`. The generated page's headings already
include "Waiting on you", "Your next step", "Where the programme stands", "How
much, against what limit" and "What could still go wrong".

The page I hand-wrote all session is a SECOND renderer inventing its own state.
Your north-star brief names that failure: "No duplicated truth."

So this is a CONVERGENCE, not a build.

## Your four decisions

1. Converge onto the generator; the hand-kept page is deleted.
2. The strip shows what changed since you last looked, computed mechanically,
   plus ONE clearly labelled narrative slot for why a decision was taken.
3. It shows the exact command that clears each finding and never runs it.
4. The page design becomes the STANDARD for every BrotherMode project.

## Steps, each naming its files and its done-check

**S1. Checks module.** New `tools/bm_flightcheck.py`. Pure, read-only, renders
nothing. Each check declares id, severity, one plain statement, the command that
clears it, and what its empty state means. A check whose empty state would be
PASS is REFUSED at registration.
DONE-CHECK: `python3 tools/test_bm_flightcheck.py` OK, including a NO-DATA sweep
that hollows every check's inputs and asserts none ever returns PASS.

**S2. The seven checks, each earned by a real incident.** Gate bound to current
HEAD; a fence whose owning session is dead; uncommitted or unpushed work;
evidence older than the change it covers; version identity honest; unresolved
CRITICAL or HIGH; disk headroom.
DONE-CHECK: each red then green against a synthetic store in tempfile.

**S3. Strip renderer** in `tools/bm_view.py`. Four bands: since you last looked,
needs you now, watch, and the narrative slot which states its own emptiness
rather than rendering nothing.
DONE-CHECK: the four bands render from a fixed findings fixture, so layout is
asserted without depending on live state.

**S4. Last-looked timestamp** on the existing `views` row. No schema change.
Updated when the page is OPENED, not on every render, so a session regenerating
the page does not silently consume your unread changes.
DONE-CHECK: a render does not advance it; an open does.

**S5. Lock the design standard.** One skeleton emitted by the generator: title,
stamp bound to a SHA, alert cards, the strip, timeline grid, ledger sections
with an evidence line under every row, footer carrying the tick contract and
what the page does not know. Type stack fixed: Iowan Old Style display, Seravek
body, SF Mono evidence.
DONE-CHECK, two tests: no shipped HTML declares a colour literal outside
`bm_visual.TOKENS_LIGHT` and `TOKENS_DARK`; and every ledger row carries a
non-empty evidence string, which makes the tick contract structural rather than
remembered.

**S6. Registration**, or the repo refuses the tool: `SUITES` in
`tools/test_all.py`, a CI step, `py-modules` in `pyproject.toml`, and
`tools/write_sites.json` after READING its write sites. NO APOSTROPHE in the
SUITES comment; the fact loader parses that tuple quote to quote.
DONE-CHECK: `python3 tools/test_bm.py` OK.

**S7. Converge and delete.** `project-template/PROGRESS.html` regenerated
through the skeleton so a new project inherits the standard on day one, and
`docs/plan/RELEASE-v3.1.0-GANTT.html` deleted.
DONE-CHECK: `python3 tools/bm_progress_check.py status` still resolves, and the
generated page renders in light and dark.

SIZE: 1.5 to 3 days, MEDIUM confidence. Variance is entirely in S2, because some
checks need git facts that may be slow enough to move behind an explicit
refresh.

## What it will NOT do

Auto-run any command. Serve anything. Roll up across projects. Send
notifications. Add a database table.

---

# 7. WHAT THE SUCCESSOR DOES FIRST, IN ORDER

1. Re-arm the watchdog. It died with this session. Fix the foreign-commit
   monitor's self-detection while you are there.
2. Collect the two agents' results and VERIFY THEM by running the commands
   yourself. This session caught agent claims that did not survive checking, and
   one that did.
3. Apply the deltas they name outside their fences, likely `write_sites.json`.
4. Register `test_bm_effects.py` in `SUITES` and add a CI step.
5. Regenerate `CHECKSUMS.sha256` LAST, after `git add`, with
   `sh scripts/checksums.sh CHECKSUMS.sha256`, never by redirecting stdout.
6. Full gate on a COMMITTED clean tree:
   `BROTHERMODE_SESSION_CAP=99 python3 tools/test_all.py`. Only this closes
   Loops 2 and 5.
7. Loop 6, the Codex audit, then triage.
8. Loop 7, the tag, which is yours to authorise.

---

# 8. OPEN QUESTIONS AWAITING YOUR ANSWER

1. **22 of your original 30 questions were never asked.** You redirected to
   execution after 8, which was right then. They remain unasked.
2. **`git push --tags` pushed an old `v2.0.0-rc.3` tag I did not intend**, and
   two older rc tags were rejected because local and remote disagree on them.
   Untidy release history, needs a decision.
3. **Does the dashboard spec need changes** before an implementation plan is
   written? You have not reviewed it yet.

---

# 9. WHAT IS STILL NOT TRUE, WHATEVER SHIPS

No BrotherMode capability has reached external verification. Nobody has counted
whether this product makes work better, faster or more reliable than working
without it. Ten outside builders and thirty externally attempted work items need
people and calendar, not code.

The defensible claim tonight is the narrow one, and it got stronger today rather
than weaker: this is the agent layer that publishes the defects its own checks
find in itself. Today those checks refused their own author four separate times,
and the single most valuable finding of the night was that one of my own tests
could not see the defect it was written for.
