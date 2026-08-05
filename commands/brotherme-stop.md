---
description: Stop the Full-Auto controller run right now, draining in-flight work and releasing every held claim
---

Outcome to produce: the controller run for this project is stopped, cleanly, with the user told exactly what state it landed in.

Enter the Full-Auto stop flow. This is the kill switch on the RUN itself (distinct from pausing or revoking the underlying autonomy contract, which is `bm-autonomy pause` or `bm-autonomy revoke`, a separate act the user may also want).

Run the mechanical command `python3 tools/bm_controller.py stop --project <id> --controller-id <the same id the run was started or resumed with> --actor-name <the user's name>`; never answer from memory of this conversation about what state the run was in. This command never fails hard: if there is no run at all, or it already reached a terminal state, it says so and does nothing further. Otherwise it drains any in-flight unit (recording whatever result had already arrived, never inventing one), releases every fence it held, and reports the state it moved from and to.

Tell the user plainly what happened and, if any unit was left mid-flight when the stop landed, name it: nothing is lost, but that unit will need a fresh dispatch the next time the run resumes.
