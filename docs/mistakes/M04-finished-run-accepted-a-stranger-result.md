# M04: a finished run accepted a result from a stranger session

## WHAT HAPPENED

Plain language: when a run of autonomous work is stopped, it is over. The
controller still accepted a late "here is the result of that piece of work"
message on a stopped run, from any session at all, including one that had nothing
to do with the run.

The ownership check was there, but it was written to run only while the run was
still live. On a finished (terminal) run the check was skipped entirely, so a
foreign session could record a dispatch outcome and re-queue a unit on somebody
else's finished work.

Bounded, and worth saying so: it records an outcome on a finished run, it does not
restart the run or cause new work to be dispatched. Lower severity than M02 and
M03. It is still a foreign write through a guard the code claimed covered it.

## HOW IT WAS FOUND

By the same adversarial refuter as M02 and M03. Like M03, this had been disclosed
by the implementer in the round-1 report; the refuter reproduced it through the
shipped command line, which is what moved it from a footnote to a fix.

Report: `/Users/khalil.maaouni/Documents/BrotherModeUp/docs/program/absolute-lead/evidence/L09/REFUTE-auth-gaps.md`
(CONFIRMED B3, lines 212 to 227).

## THE EVIDENCE

Reproduced through the command line, with its calibration twin first:

```
# non-terminal run, foreign sess-B (calibration): REFUSED
record-result --dispatch-id <open> --session-id sess-B -> refused: ... not-driver

# driver stops the run (STOPPED, terminal), then foreign sess-B records anyway:
record-result --dispatch-id <same> --session-id sess-B
   -> dispatch <id> rejected; the unit re-queues ...   # accepted and processed,
                                                       # no not-driver refusal
```

Written as a test against the unfixed tree, from
`/Users/khalil.maaouni/Documents/BrotherModeUp/docs/program/absolute-lead/evidence/L09/RED-auth.txt`
lines 626 to 633:

```
FAIL: test_a_foreign_session_cannot_record_a_late_result_on_a_terminal_run
  File "tools/test_bm_controller.py", line 7659, in
  test_a_foreign_session_cannot_record_a_late_result_on_a_terminal_run
    engine2.receive_result("p1", dispatch_id, "done",
AssertionError: OwnershipRefused not raised
```

The calibration twin, the run's own driver recording a late result on the same
terminal run, passed before and after, which is the behaviour that had to be
preserved: a driver whose work was in flight when `stop` landed must still be able
to record it.

## HOW IT WAS FIXED

The guard was made unconditional. In
`/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_controller.py`,
`receive_result` now calls `_refuse_foreign_driver(run, "receive_result")` at
tools/bm_controller.py:1985 regardless of run state, instead of only when the run
was not terminal.

Verification, same run as M03:

```
$ python3 tools/test_bm_controller.py
Ran 206 tests in 29.739s

OK
```

The founder-facing documentation for the closed item now reads that the guarded
doors are "step, plan, record-result and stop", and that a terminal run's late
result is refused for a foreign session and allowed only for the run's own driver.

## THE RULE THIS PRODUCES

A guard with a state condition on it is a guard with a hole in it: put the
ownership check before the state logic, and let the legitimate late case pass on
identity rather than on the run being unfinished.

## WAS IT CAUGHT BEFORE OR AFTER IT COULD HURT A USER

Before. Same commit as M02 and M03 (ac7ef87), never released with the gap. As with
M03, it was a known and disclosed residual that only got closed because somebody
was told to attack the disclosure rather than trust it.
