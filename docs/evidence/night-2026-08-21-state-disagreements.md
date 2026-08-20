# Night of 2026-08-20 into 2026-08-21: where the prompt and the commands disagreed

Status: CURRENT
Date: 2026-08-21
Session: bm1-3989fa298b7bfbb9a5fc71f9 (night run)
Rule applied: the founder's night prompt states "If a command disagrees with a line
here, THE COMMAND WINS and the disagreement is the first thing you write down."

Four disagreements were found in the opening five minutes. Each is recorded with the
command that settled it, so a later reader does not have to re-derive any of them.

## 1. The spend grant was written as prose, never as numbers

PROMPT SAID: 10,000,000 output tokens "written into ~/.claude/spend-guard.json against
BOTH project blocks with until 2026-08-21T07:00:00+09:00".

COMMAND SAID: the BrotherModeUp block carried daily_soft_out 7,000,000 and
daily_hard_out 8,000,000, the PREVIOUS grant's figures, while a sibling key
_grant_night_2026_08_21 recorded the founder's words "10 million, same as today". The
BrotherSBE block did carry 10,000,000 / 11,000,000. So the note was appended to both
blocks and the numbers were changed in only one.

WHY IT MATTERED: the session-start guard line measured 5,549,000 output tokens across 7
sessions in the rolling 24 hours. Against an unapplied 8,000,000 daily ceiling that
left roughly 2,451,000 of headroom, which would have hard-stopped this run around
02:00 JST, several hours short of the founder's own 07:00 stop.

ACTION TAKEN: applied the figure the founder named, to the block that was missing it,
per the RAISE-NEVER-OVERRIDE law. daily_soft_out 10,000,000, daily_hard_out 11,000,000,
until unchanged at 2026-08-21T07:00:00+09:00, matching the BrotherSBE block exactly.
Per-session ceilings left untouched at 3,000,000 hard and 1,500,000 soft, because the
founder named those figures and a session does not raise its own ceiling.
Pre-change snapshot:
  ~/Documents/BrotherArchive/brothermode/spend-guard.before-night-2026-08-21-apply.json
Proving command after the edit: `python3 ~/.claude/hooks/spend_guard.py selftest`
printed OK over its grant-expiry cases.

## 2. The unmerged branch is already merged

PROMPT SAID: "A branch feature/ceremony-carries-the-next-prompt is pushed at 153392e and
NOT merged. Merging it is a judgement call."

COMMAND SAID:
  git merge-base --is-ancestor 153392e HEAD   ->   exit 0

153392e is an ancestor of tonight's main. The work is already carried. There was no
merge to judge and none was attempted.

## 3. The newest pack says M15 is closed; the queue says it is open

PACK SAID (docs/handover/2026-08-20-day3-fence-repair/07-NEXT-SESSION-PROMPT.md, under
"Decisions already made"): "M15 is answered and is NOT a defect. Do not reopen it
without new evidence."

QUEUE SAID (docs/plan/QUEUE.json, item M15): "NOT ESTABLISHED, kept as an open question
rather than a claim ... the attempt to measure it directly was swamped by M14's
fail-open warnings and returned ALLOW for both a parked-only path and an actively
fenced one, so nothing was established in either direction."

The queue is the control and the founder's night prompt agrees with it, naming M15 as a
MEASUREMENT whose acceptable answer includes NOT ESTABLISHED. Measured tonight on that
basis. This entry exists so that whoever reads the pack's decision line later knows it
was contradicted by the queue on the same night it was written.

## 4. The unattended run is armed with two mechanical controls, not three

PROMPT SAID: "UNATTENDED RUN MEANS ALL THREE ... the relay brake, the overnight
watchdog, and the spend guard above."

OBSERVED: `ls ~/.claude/hooks/` lists bm_session_cap.py, github_cost_wall.py and
spend_guard.py. There is no relay brake file, and no relay loop is running tonight, so
the control has no subject. What actually stands tonight:
  - spend guard: ARMED and verified by selftest (mechanical).
  - overnight watchdog: ARMED (twice-hourly audit job, plus a monitor on origin/main
    that reported its baseline at 1b804d68f93102501b9a87c74d408f73eecfff6b).
  - session cap hook: present (mechanical).
  - the 07:00 JST hard stop: DISCIPLINE, not a control. Nothing refuses a session that
    runs past it.
Stated rather than smoothed over, because the founder asked to be told if all three
could not be armed. The run proceeded, because two mechanical brakes plus a clock the
orchestrator honours is the honest shape of tonight, and the founder's own law is that
a rule without a file behind it says so.

## Process findings from this run, recorded as they happened

### F-N1: fence discipline covers the agents a session dispatches, not only its own hands

CAUGHT BY: the BrotherSBE scope reconciliation hook at the first stop, which named
docs/evidence/night-2026-08-21-state-disagreements.md as "outside every open task's
declared ownedPaths".

WHAT HAPPENED: this session claimed its own orchestration paths (the board and the
queue) correctly, then wrote an evidence document outside that declaration. Worse, and
undetected by the hook because the file did not exist yet, it had already dispatched a
measurement agent whose only deliverable was
docs/evidence/night-2026-08-21-m15-parked-record.md, with NO record open in either
registry for that path.

WHY IT MATTERS: the rule is read as "claim before you write", and a session that writes
only through subagents can satisfy that reading while owning nothing. The claim has to
cover every path the session CAUSES to be written, including a path that exists only in
a brief at the moment of dispatch.

CORRECTION APPLIED: night-m15-parked-measure opened in both registries over the
measurement path, and night-orchestrator-evidence opened over this file. The sbe
registry refused to amend an already-open task (it has open, close, list, fence and
check, and no amend), so the extra path went to a second task id rather than by closing
and reopening the first, whose diff postcondition would have failed on the very file
being declared. Overlap scan after the correction:
  sbe task check -> "no owned-path overlap among 7 open task(s)"

WORTH NOTING IN THE SAME BREATH: that scan prints its own limit, "it says nothing about
writers who never registered", which is the same NO-DATA discipline the M17 and M18
defects exist to restore elsewhere in this estate.
