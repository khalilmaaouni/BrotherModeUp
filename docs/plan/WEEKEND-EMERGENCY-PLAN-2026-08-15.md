Status: CURRENT.

# Weekend emergency plan, 2026-08-16 and 17

One page for when something breaks this weekend and the session that broke
it is gone. Written 2026-08-15, the day v3.3.0 shipped, the testers were
named, and the Bitbucket workspace decision landed. Every command here was
either run this session or comes verbatim from a page that names its own
proof; nothing is improvised. Any Claude session, and Khalil himself, can
run this top to bottom.

## The first move, whatever happened

Open a session in the repository and run these three, in order. They are
read-only and they tell you which section below applies.

    python3 tools/bm_handover.py detect
    python3 scripts/doctor.py
    git status -sb && git log --oneline -3

Healthy looks like: detect reports no unacknowledged handovers and no
dead-owner leftovers, doctor reports 11 of 11, the tree is clean at or
ahead of c1bd563. Anything else: find your case below.

## Case 1: Tung or Harry's install fails

The most likely weekend event, because nobody outside this machine has
ever run the install. Do not debug live on their machine beyond this list.

1. Ask for the exact command they ran and the full output, pasted, not
   summarized. The three known traps are already written on the card they
   have (docs/team/INSTALL-CARD.md): the brothermode command only exists
   inside a Claude Code session; an older major version must be
   uninstalled first or two hook chains fire; a stale sbe on PATH lies
   about its version.
2. Have them run /brothermode:doctor inside a session. It prints the
   remediation next to any failure; follow that, never a guess.
3. If the marketplace path fails and the transcript does not make the
   cause obvious, switch them to the pinned clone, the most proven path:

       git clone --branch v3.3.0 --depth 1 https://github.com/khalilmaaouni/BrotherModeUp.git ~/.claude/skills/brothermode

4. Whatever happened, file the transcript under
   docs/evidence/tester-pack/ in a dated file. A failed cold install is
   the most valuable evidence this project can collect this weekend; it
   is a finding, not an embarrassment.

## Case 2: the gate is red or the tree is broken

1. Read the FIRST error in the gate log, not the last. The dirty-tree
   refusal at the end of test_all is not a test failure: if every suite
   line above it says OK, the fix is committing or stashing, never
   editing code.
2. A suite genuinely red: reproduce it alone (python3 tools/<suite>.py),
   quote the first traceback, one falsifiable hypothesis, one variable
   per attempt, revert speculative edits after 2 failures.
3. Nothing recovers: the last known-good line is the v3.3.0 tag.

       git stash && git checkout v3.3.0

   proves whether the breakage is local work or the release itself. The
   release was proven green at 3156 tests this Friday; if v3.3.0 is red
   on this machine, the machine changed, not the code: check disk space
   (under 15 GiB free means cleanup before builds) and Python version.
4. NEVER: force push, move a published tag, weaken or delete a failing
   test, or hand-edit CHECKSUMS.sha256. The manifest is regenerated only
   by sh scripts/checksums.sh CHECKSUMS.sha256 after git add, never
   edited.

## Case 3: a session is stuck, looping, or spending

1. Find it before killing it: print the target first, then kill by PID.
   NEVER pkill -f by pattern; it has killed an innocent session on this
   machine before (the failure is in the ledger).

       pgrep -fl "tools/test_all.py"
       kill <the printed pid>

2. The spend guard and the machine-wide session cap are hooks and they
   are armed; a brake refusal from either is Khalil's standing
   instruction. Stop, write the handover, never restart the work by
   another route.
3. Unattended stretches this weekend follow the standing law: relay
   brake, overnight watchdog, spend guard, hard stop 07:00 JST, cheap
   tiers only while Khalil is away. No unattended run without all three
   armed; if you cannot arm them, work attended or not at all.

## Case 4: the store refuses a session

The refusal text matters. "schema-ahead: store is at schema N, this copy
understands up to M" means the INSTALLED CLONE is old, never that the
store is corrupt. The fix is syncing the clone, proven this Friday:

    git -C ~/.claude/skills/brothermode fetch --tags origin
    git -C ~/.claude/skills/brothermode checkout v3.3.0

Never downgrade the store, never delete .brothermode/, never edit
STATE.md inside its generated markers. STATE.md keeps its own 5 most
recent backups next to itself (.bak files) if prose outside the markers
was lost. Ownership refusals ("only the owning session may close") have
their exact clearing commands printed by detect; run what it prints.

## Case 5: Khalil created the Bitbucket workspace

Not an emergency, but the one planned weekend event with steps. Once the
empty repository exists with Pipelines enabled:

    git remote add bitbucket https://bitbucket.org/<workspace>/BrotherModeUp.git
    git push bitbucket main
    git push bitbucket v3.3.0

Then run both install commands from docs/BITBUCKET.md against the mirror,
quote their output into that page, quote the first Pipelines run URL, and
close the three UNVERIFIED labels. The push gates (secret scan, dash
scan, attribution scan over the pushed range) apply to the mirror push
exactly as to origin.

## The weekend's fix priority, added after the URRY review landed

The founder ordered the URRY review's lessons adapted to BrotherMode the
same evening: docs/plan/URRY-REVIEW-ADAPTATION-2026-08-15.md is that
adaptation and it is the weekend's fix lens. Its order agrees with this
plan: the Bitbucket seam first the moment the workspace exists (Case 5),
tester evidence filed the moment it arrives (Case 1), and no new blocking
gate invented in response to any complaint, because a gate in front of a
queue is not capacity. Success this weekend is measured by that page's
three numbers, not by how green the gates stay.

## What this weekend is NOT for

No new features, no re-litigating ratified decisions, no touching the
released tags, no CLAUDE.md or hook edits mid-session, nothing deleted
under ~/.claude/projects. The queue's next real item is TK6, the pipeline
exit test; it is a Monday item unless the weekend is quiet and a session
is attended. Boredom is not an emergency.

## Where everything lives

- The board: docs/plan/COMMAND-CENTER.html, delivered at every change.
- This plan: docs/plan/WEEKEND-EMERGENCY-PLAN-2026-08-15.md.
- The pack a fresh session reads first: docs/handover/2026-08-15-comparison-roadmap-bitbucket/.
- The roadmap: docs/plan/FINALIZATION-ROADMAP-2026-08-15.md.
- Evidence from testers: docs/evidence/tester-pack/.
- The vault log with this week's full trail:
  Kay Vault/10-Projects/brothermode/Sessions/2026-08-15-comparison-roadmap-bitbucket.md.
