# M17: the orchestrator wrote three files with no fence, while an agent was live

Status: CURRENT as of 2026-08-06. Found by the Haiku drift watchdog on its first
run, which is the run it was added for.

## WHAT HAPPENED

Plain language: the rule is one writer per file, and a writer says which files it
owns BEFORE it starts. The orchestrator wrote the fence lines for its three
subagents, dispatched them, and then edited three files of its own without
writing a fence line for itself.

The files were `SKILL.md`, `references/delegation.md`, `references/mistakes.md`
and `tools/test_bm_docs.py`. A Builder agent was live at the same time under
FENCE B (docs/FEEDBACK.md and .github/ISSUE_TEMPLATE/).

Nothing collided. That is luck, not design: the orchestrator happened to add
`docs/FEEDBACK.md` to the dash guard in `tools/test_bm_docs.py` while the agent
that owned `docs/FEEDBACK.md` was still writing it.

## HOW IT WAS FOUND

Twice, independently, which is the part worth keeping.

1. The Builder agent under FENCE B reported it, unprompted, in its own return:
   it observed `tools/test_bm_docs.py` change underneath its task, confirmed it
   had not touched that file, checked the diff, correctly identified the change
   as another writer's, left it alone per the fence rule, and flagged it for the
   founder. That is exactly the behaviour the fence law asks for from a worker
   who finds a foreign write.
2. The Haiku drift watchdog, on its first run, answering the question "do any
   commits touch files that no fence lists".

## THE EVIDENCE

From the drift audit at
`docs/program/absolute-lead/evidence/L10/DRIFT-AUDIT-1.md`, question 4: four
files in commit `7fe6b2b` appear in no fence in the wave 17 registry block of
`STATE.md`.

From the Builder agent's own return, verbatim:

```
One anomaly to flag: git status shows tools/test_bm_docs.py modified, which is
outside Fence B and outside anything I touched (I never opened it with
Edit/Write, only Read/Bash). Diff shows a concurrent change adding
docs/FEEDBACK.md ... i.e. another session in this shared repo edited that file.
Per the fence rule I left it untouched.
```

## HOW IT WAS FIXED

The finding is accepted rather than argued away, and the rule below is added to
`references/fences.md` so the next orchestrator does not have to rediscover it.

The audit also raised a fifth item that is REJECTED with its reason, recorded
here so the rejection is visible rather than silent: it counted the files in
commit `75bb1b7` as outside the wave 17 fences. That commit predates wave 17, so
the registry it was compared against did not exist when it landed. A watchdog
comparing against a registry that did not yet exist will always find drift, and
that is a property of the question rather than of the work.

## THE RULE THIS PRODUCES

The orchestrator is a writer like any other. When ANY agent is live, the
orchestrator's own files get a fence line too, written before its first edit,
disjoint from every dispatched fence. "I am the one who writes the registry" is
the reason to be in it, not an exemption from it.

## WAS IT CAUGHT BEFORE OR AFTER IT COULD HURT A USER

Before, and no collision occurred. The value here is not the damage avoided, it
is that two independent mechanisms caught the same lapse in the same hour: a
worker that reported a foreign write instead of overwriting it, and a cheap
watchdog whose entire job is to check the orchestrator rather than the code. The
orchestrator did not catch itself, which is the argument for both.
