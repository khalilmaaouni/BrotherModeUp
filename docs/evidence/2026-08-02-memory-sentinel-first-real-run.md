# Memory Sentinel, first real run against a live store

Status: CURRENT. Recorded 2026-08-02, immediately after Phase 1 landed at
`491bfc6` on `feature/full-auto-and-codex-modes`.

This is not a test run. It is the sentinel's command line driven by hand
against a real sqlite store in a throwaway project, in the order a session
would actually hit it. Every block below is the real command and its real
output, pasted unedited. It exists because 56 passing unit tests prove the
parts behave; they do not prove the thing does its job.

Setup: `git init` in a throwaway directory, `BROTHERMODE_ROOT` pointed at it,
`bm_store.py init`, nothing else.

## 1. An empty sentinel says nothing, and that is a success

```
$ bm_sentinel.py check --project demo --trigger resume
SILENT: no memories recorded
exit=0
```

Exit 0 with no reminder. Silence is an outcome of the command, not a failure of
it, which is the whole posture of the design: Meta's ablations show the
always-inject variant loses to calibrated silence, and an uncalibrated memory
agent makes its worker actively worse.

## 2. Two things an agent learned

```
$ bm_sentinel.py remember-knowledge --project demo --kind requirement \
    --content "every push goes through GitHub Desktop, never a bare git push" --source founder
f2e2d963ebc84e5697e99b3152883425

$ bm_sentinel.py remember-procedural --project demo \
    --attempt "ran codex exec against the workspace" --outcome failed \
    --diagnosis "workspace is out of credits"
be541c4755d0410c9d82910f1d36824d
```

Both are real facts from this session: a standing founder rule, and the wall
Phase 0 actually hit.

## 3. Resume, which this project's own ledger calls its worst decay moment

```
$ bm_sentinel.py check --project demo --trigger resume
MEMORY: every push goes through GitHub Desktop, never a bare git push
WHY NOW: resume surfaces the least-recently-surfaced requirement or constraint
SOURCE: founder
exit=0
```

## 4. The case the whole thing was built for

An agent is about to retry something that already failed:

```
$ bm_sentinel.py check --project demo --trigger post_failure \
    --context "codex exec workspace credits failed again"
MEMORY: ran codex exec against the workspace
WHY NOW: prior failed attempt overlaps this failure by token match
SOURCE: workspace is out of credits
exit=0
```

It surfaced the exact prior attempt AND its diagnosis, chosen by token overlap
with the failure text. This is the second of the three failure patterns Meta
names: "observe that a command, parameter setting, or implementation path fails
and later retry a near-identical variant". It is also the pattern this project's
own ledger records costing 1.35M tokens and four hours across two dead engine
runs.

## 5. A routine check with nothing new to say

```
$ bm_sentinel.py check --project demo --trigger tool_interval
SILENT: every candidate is in cooldown
exit=0
```

Correct, and worth explaining because the reason string surprises at first
glance. Cooldown is spec branch 2, a blanket filter that runs BEFORE any
trigger-specific branch. Both memories had just been injected in the preceding
two checks, so both were inside the cooldown window and the blanket filter
answered before the tool_interval branch could. The alternative, letting a
trigger branch re-surface a memory injected moments ago, is precisely the
chatty-watcher failure the cooldown exists to prevent.

## 6. Calibration refuses to invent a number

```
$ bm_sentinel.py stats --project demo
total=4 injected=2 silent=2 useful=0 noise=0 unjudged=4 useful_ratio=NO-DATA
```

`NO-DATA`, not `0.0`. Four decisions recorded, including both silences, and no
ratio claimed because nothing has been judged yet. A ratio over zero judgements
is the exact shape of number this project refuses to print.

## 7. A typo is refused, never read as a decision to stay quiet

```
$ bm_sentinel.py check --project demo --trigger sometimes
bm_sentinel: refused. Unknown trigger 'sometimes', allowed: phase_boundary, pre_risky, post_failure, tool_interval, resume
real exit=1
```

Exit 1, a refusal. This is the fourth hard invariant and it is not pedantry: a
typo that returned silence would be indistinguishable from working software,
and the sentinel would appear to be running while doing nothing at all.

Measurement note, because the first attempt got this wrong: piping the command
into `head` reported exit 0, which is `head`'s status and not the tool's. The
exit code above was captured on its own line. That is the same
command-substitution-clobbers-exit-status failure already in this project's
ledger, reproduced by the person who wrote it down.

## What this run does NOT prove

- Nothing here exercises the sentinel inside a real agent loop. No hook calls it
  yet; that is Phase 3 work, and until then a founder must call it by hand.
- The selection policy is deterministic, so this proves the RULES fire
  correctly. It says nothing about whether the reminders are the ones a working
  agent would have wanted. That question is what the intervention ledger and its
  useful-versus-noise judgements exist to answer, over real runs, and the
  honest answer today is NO-DATA.
- One project, one session, seven commands. It is a walkthrough, not a sample.
