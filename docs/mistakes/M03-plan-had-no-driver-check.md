# M03: the most powerful controller command had no ownership check

## WHAT HAPPENED

Plain language: the controller is the thing that runs autonomous work. One session
"drives" a run, and other sessions are supposed to be refused. Four commands were
guarded (`step`, `record-result`, `stop`, and takeover via `adopt`). One was not:
`plan`, the command that defines what work exists.

So a foreign session could write the whole plan of work into a run it never
started, and the legitimate driver's next `step` would dispatch that
attacker-authored work under the honest driver's own identity. The audit trail
would show the honest session doing it.

`plan` is the single most powerful mutation in the controller: it defines what
runs and it rewrites the unit graph. It was the one door left open.

## HOW IT WAS FOUND

By the same adversarial refuter as M02, driving the real command line tools as
subprocesses. The implementer's own round-1 report had disclosed that `plan` was
unguarded (section 7 of the fix report), so it was known and written down. The
refuter's contribution was to prove it was reachable and exploitable through the
shipped command line, which turned a disclosed residual into a ratified fix.

Report: `/Users/khalil.maaouni/Documents/BrotherModeUp/docs/program/absolute-lead/evidence/L09/REFUTE-auth-gaps.md`
(CONFIRMED B2, lines 183 to 210).

## THE EVIDENCE

Reproduced through the command line, from the refute report:

```
# driver sess-A begins a run, leaves it NEW
start --session-id sess-A -> run 27055... state NEW

# foreign sess-EVIL plans the whole graph on a run it never began:
plan --units-json '[{"unit_id":"evil","objective":"attacker-authored unit on a
foreign run",...,"write_scope":["src/pwned.py"]}]' --session-id sess-EVIL
   -> count=1, rc=0            # accepted, no not-driver refusal
   driver.session_id='sess-A'  state=READY

# the legitimate driver's next step DISPATCHES the attacker's unit under sess-A:
step --session-id sess-A -> controller_brief {... "unit_id": "evil",
     "objective": "attacker-authored unit on a foreign run" ...}
```

Written as a test against the unfixed tree, from
`/Users/khalil.maaouni/Documents/BrotherModeUp/docs/program/absolute-lead/evidence/L09/RED-auth.txt`
lines 634 to 646:

```
FAIL: test_a_second_session_cannot_plan_a_run_it_never_began
  File "tools/test_bm_controller.py", line 7611, in
  test_a_second_session_cannot_plan_a_run_it_never_began
    engine2.plan("p1", run["run_id"],
AssertionError: OwnershipRefused not raised
```

The two calibration twins in the same class passed on the unfixed tree, which is
what proves the rig was live: a same-driver replan (the crash-resume shape) still
worked, so the failure is the hole and not a broken fixture.

## HOW IT WAS FIXED

One line, in the same shape `step` already used. In
`/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_controller.py`:

- `_refuse_foreign_driver(run, "plan")` at tools/bm_controller.py:1438, called
  before the pause check so a foreign session learns "not yours" before it learns
  anything about the run's state.
- The guard itself is unchanged at tools/bm_controller.py:974. The other three
  doors are at tools/bm_controller.py:1640 (`step`), :1985 (`receive_result`) and
  :4330 (`stop`).

Verification after the fix:

```
$ python3 tools/test_bm_controller.py
Ran 206 tests in 29.739s

OK
```

Not fixed, deliberately, and disclosed rather than hidden: the identity being
compared is a self-asserted `--session-id` that `status --json --raw` prints in
clear. Anyone who reads it can assert it. So this guard is accountability plus an
audited takeover path (`adopt` records the handover), not cryptographic access
control. Authenticating a session id was out of scope and the founder did not
authorise adding a token layer. This is now written into
`/Users/khalil.maaouni/Documents/BrotherModeUp/docs/KNOWN-LIMITS.md` and
`docs/AUTONOMY.md`.

One door remains unguarded and is named: `check_timeouts`. It has no shipped
command line entry point today, so it is unreachable, but wiring it later would
inherit the same gap.

## THE RULE THIS PRODUCES

When you add an ownership check, enumerate every mutating entry point in the file
and guard them in the same change; the one you skip will be the one that writes
the plan everything else obeys.

## WAS IT CAUGHT BEFORE OR AFTER IT COULD HURT A USER

Before, and it never shipped: round 1 and round 2 landed in the same commit
(ac7ef87). But note the honest sequence: round 1 knew `plan` was unguarded, wrote
it down as a residual, and shipped the round anyway. A disclosed hole is still a
hole. It was closed only because an adversary was pointed at the disclosure.
