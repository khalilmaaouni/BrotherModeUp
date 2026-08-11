# Overnight delivery, roadmap, and horizon, with collaboration

Status: CURRENT

Written 2026-08-11 night. This file is the authority for tonight's run. It
supersedes the schedule in `V3-FINAL-2026-08-12.md` and inherits everything
else from it unchanged.

Owner: Khalil Maaouni. Written to disk deliberately, at the moment the
conversation holding it grew long, so that a session rollover cannot destroy
the decisions in it. Anything a later session needs is here, not in a chat log.

---

## 0. The north star, restated because every item below must serve it

**From intent to verified delivery.** Work moves from a clear request to a
result a second person can check, with context that survives sessions,
handovers and reviewers. Every backlog item below names which objective it
serves. Anything that cannot goes to the parking lot in section 8, never
straight into the plan.

The collaboration objective, which is new tonight and which the previous plans
did not carry: **a change must be able to pass from one person to another
without the receiver redoing the work.** That is the objective the whole
team tranche serves.

---

## 1. The thirty two decisions taken tonight

Taken through the question interface on 2026-08-11 night, before the founder
slept. Recorded here because a decision discovered later in a summary is a
correction-class failure.

### The four rulings that were blocking finished work

| # | Decision | Chosen | Consequence |
|---|---|---|---|
| D11 | What the team installs | Tagged `v3.2.0`, install rehearsed | The release path runs tonight |
| D12 | The verify skill | Routing name, no folder of its own | Canonical count stays nine; ruling B5 untouched; brand identity file untouched |
| D13 | External security review bar | Internal team is not the public small-team persona; bar does not apply to them, stays in force for outside teams | Team rollout proceeds; `SECURITY.md` keeps stating the review is missing |
| D14 | The three defects | Fix the two in this repository tonight; the sibling's belongs to its own release | Scope stays in one repository overnight |

### The overnight envelope

| # | Decision | Chosen | Consequence |
|---|---|---|---|
| D15 | The release gate | **OVERRIDE.** Founder pre-authorised the tag and publish tonight | See the override note below |
| D16 | Hard stop | **OVERRIDE.** 08:00 instead of the standing 07:00 | See the override note below |
| D17 | Token ceiling | 300k output, no new dispatches at 240k | Stated before the run, per the spend laws |
| D18 | Model tiers | Sonnet for scoped work, Haiku for mechanical, nothing stronger | Matches the standing unattended-tier law |
| D19 | If the battery goes red | Keep working until green, **bounded by D16 and D17** | See the reconciliation below |
| D20 | Install rehearsal | On the live setup, **sequenced last with a backup** | See the sequencing note below |

**OVERRIDE NOTE, D15.** The founder's own law makes tagging and publishing a
hard founder gate, added after the 8 August runaway. He waived it for this one
tag, knowingly. What it costs: the single human checkpoint between a green test
run and a published artefact is absent tonight. What preserves safety in its
place: the tag is cut only from a commit whose full battery reported ALL GREEN
with exit 0, on a clean tree, with the commit hash recorded beside the verdict.
**Flip condition:** if any part of the release path is red at the ceiling or the
deadline, this authorisation is treated as not granted, nothing is tagged, and
the state is reverted to the last green commit.

**OVERRIDE NOTE, D16.** The standing law hard-stops unattended chains at 07:00.
Extended to 08:00 for this run only, to leave room for a second battery run if
the first is red. **Flip condition:** this extension does not renew. A future
run wanting it asks again.

**RECONCILIATION, D19.** "Keep working until green" is unbounded on its own,
which is the exact shape that produced the August runaway. It is bounded here
by the founder's own other two answers: the 300k ceiling and the 08:00 stop.
Reaching either while red means revert to the last green commit and do not tag.
This reading is the only one under which all three answers hold at once, and it
was stated to the founder before he slept rather than decided quietly here.

**SEQUENCING NOTE, D20.** Installing the new version over the live setup
mid-run would replace the hook files constraining this very run, including the
spend guard. So the live install is the LAST step, after the tag, with
`~/.claude` snapshotted first so a single command restores it. The founder gets
what he asked for, proven on the real machine, without the run rewriting its own
brakes at three in the morning.

### Collaboration and rollout

| # | Decision | Chosen |
|---|---|---|
| D21 | Who installs tomorrow | Two champions only, on a throwaway repository. Phase 0 |
| D22 | What travels between people | The handover pack, committed to the repository |
| D23 | Where the shared record lives | In each work repository, under version control |
| D24 | Shared progress page | Yes, one per repository, committed, refreshed at each closed loop |
| D25 | Naming in public documents | Generic role words only. No company, no teammate names |
| D26 | Public adoption guide | Yes, ships as a public document |
| D27 | Public roadmap | Publish the horizon with honest not-built markers |
| D28 | Champion artefacts | Install card, nine-step loop page, first-day script, daily note file. All four |

### Cadence

| # | Decision | Chosen |
|---|---|---|
| D29 | Sprint length | One week, anchored to the weekly review |
| D30 | Sprint boundary | Monday morning review, sprint starts the same day |
| D31 | Release cadence | Once per sprint, on the boundary, only if fully green |
| D32 | Backlog ordering | Proposed ranked, founder approves at the Monday review |

### The sibling product

| # | Decision | Chosen |
|---|---|---|
| D33 | Sibling version | Reinstall to 3.0.0 and verify its command runs |
| D34 | Version pairing | Independent versions, one install card naming both |
| D35 | Session split | This session, sequentially, main product first |
| D36 | The shared object | Two records naming the same change identifier. No shared database |

### Board

| # | Decision | Chosen |
|---|---|---|
| D37 | Board scope | Both products and the team rollout, one page |
| D38 | The two charts | Short: tonight to 09:00 in hour blocks. Long: the quarter in week blocks |
| D39 | Work breakdown depth | Task level, each naming its files and its check |
| D40 | Board access | Committed in the repository and published to one stable link |
| D41 | Pilot repository | A fresh throwaway repository made for the pilot |
| D42 | Morning pack | All four: status page, board, champions' pack, sprint plan |

---

## 2. Where it actually stands, with evidence

Content work for the release landed before this session began. The full battery
ran at commit `61bd980` and reported `3020 tests across 32 suites, 5 skipped,
628.3s wall. ALL GREEN`, exit 0, tree clean afterwards.

Tonight's own work so far:

| Item | State | Evidence |
|---|---|---|
| Defect: record creation leaves the health check red | **FIXED**, committed `9f3c825` | Regression test written first and shown failing with the exact doctor string; after the fix `test_bm_store.py` Ran 1027 tests OK, `test_brothermode_cli.py` Ran 85 tests OK, `doctor` 0 failed; end to end, `apply --new-record` created record `41dffd2f` and doctor stayed at 0 failed |
| Baton open half | **DONE** | `handover-ack` acknowledged `d406eabd` |
| Defect: fence registry read as a live list | NOT STARTED | next item |
| Verify as a routing name | NOT STARTED | |
| Team pack and adoption guide | NOT STARTED | |
| Roadmap, sprints, board | IN PROGRESS, this file is part of it | |
| VERSION, changelog, checksums, battery, tag | NOT STARTED | |
| Sibling reinstall, live install | NOT STARTED | |

Two corrections worth carrying forward, because both were reported wrongly
first:

- `handover-ack` is a verb on `bm_store.py`, not on `bm_handover.py`. `detect`
  printed the right command; it was run against the wrong tool. Not a product
  defect.
- The handover claimed a store checkpoint clears the stale view. It is not the
  checkpoint specifically. **Any** store operation that re-renders the view
  clears it, which is why the fix belongs to the mutation rather than to a
  particular verb.

One genuine sharp edge found tonight and not yet fixed: **every shell
invocation of `bm_store.py` mints its own session id, so a fence claimed from
the command line without `--session` can never afterwards be parked by another
command-line call.** The way out is adopt, then park, in that order, and it
requires `--adopt-from-live-session` because the one-shot session still reads as
live. This cost four refused commands tonight. Filed as R1-4 in section 6.

---

## 3. The order of tonight's run, riskiest first

Sequential, one writer. The reason for the order is that a sequential run
cannot absorb a late failure by borrowing another lane's slack, so whatever can
genuinely stay red goes first, while the de-scope contingency is still usable.

| Step | Work | Files | Done-check |
|---|---|---|---|
| 1 | Record creation leaves the view stale | `tools/bm_store.py`, `tools/test_bm_store.py` | **DONE**, see section 2 |
| 2 | Fence registry read as a live list | `tools/bm_fence_hook.py` and its test | Its own suite exit 0, plus a hook run naming a real claim |
| 3 | Verify becomes a routing name | the guided skill and its docs assertions | `tools/test_bm_docs.py` exit 0 |
| 4 | Public adoption guide, generic | `docs/TEAM-ADOPTION.md` | `test_bm_docs.py` exit 0, dash scan finds nothing |
| 5 | Champion pack, four artefacts | `docs/team/` | same |
| 6 | Roadmap and sprints | this file plus `docs/plan/SPRINTS.md` | dash scan, and every item names its objective |
| 7 | Board rebuilt | `docs/plan/COMMAND-CENTER.html` | opens, both charts present, every ticked box quotes output |
| 8 | Version and changelog | `VERSION`, `CHANGELOG.md` | `cat VERSION` reads 3.2.0; no changelog line names a capability that does not exist |
| 9 | Manifest | `CHECKSUMS.sha256` | `git add -A` FIRST, then `sh scripts/checksums.sh`, then doctor check 9 PASS, then `verify-install.sh` PASSED with 0 extra |
| 10 | The battery, once, clean tree | none | last line ALL GREEN, exit file 0, commit hash recorded |
| 11 | Tag and publish | none | `gh release view v3.2.0` shows it published and its tag matches `git rev-parse v3.2.0` |
| 12 | Sibling reinstall | none | its command runs and reports 3.0.0 |
| 13 | Live install, backup first | none | new version reports itself, doctor passes on it |

Two rules that cost real time and are not optional. Clear `$TMPDIR/gate.exit`
before launching the battery, because that directory survives between sessions
and a stale sentinel is read as tonight's verdict, failing toward green. And
write no tracked file while the battery runs, not even the board, or it refuses
to report green even when every suite passes.

---

## 4. The collaboration architecture, which is the new part

The previous plans treated this product as governing one person's session and
stopped there. The team objective needs one more thing, and exactly one:

**The unit that crosses between people is the handover pack, and it lives in
the repository the work lives in.**

Why that and not a shared database. A shared store means a sync layer, conflict
rules, hosting, auth, and a migration for every existing record. That is the
single most expensive item on the horizon and it is deliberately not attempted
now. The pack costs nothing new: it already exists, it already refuses to close
on hollow claims, and it refused its own author twice on its first real use.
Committing it to the repository gives it distribution, history, and review for
free, because those are things git already does.

The evolution path, so this decision is not mistaken for a permanent ceiling:

- **Now.** Pack in the repository. Two records, one in each product, naming the
  same change identifier. Either product still works alone.
- **R1.** The link between the two records becomes checkable by a command
  rather than by eye. Adoption costs a joining person nothing.
- **R2.** Memory built. Connectors arrive, each a separately versioned surface
  with its own auth failure modes, which is where a single release process
  stops being sufficient.
- **R3.** Multi-repository records and a portfolio view. This is the first
  tranche needing a migration story for existing records, which is why it is
  not planned in loop detail yet.

The boundary between the two products, restated because it is the thing people
get wrong: **this product governs one person's session; the sibling governs one
change's passage between people. They meet at exactly one object, the change
about to be handed over.** Using both is not twice the work.

---

## 5. Short, mid and long range

**SHORT, tonight to 09:00.** Section 3, thirteen steps. The exit condition is a
published version, an install proven on a real machine, and a pack a champion
can follow without asking anyone.

**MID, sprints one to four, the next month.** One week each, Monday to Monday,
one release per sprint on the boundary and only if fully green.

| Sprint | Theme | Exit condition |
|---|---|---|
| 1 | Phase 0 survives contact | Both tools run together for a full working day with no conflict, and the version is written down. Daily notes exist |
| 2 | Phase 1, three real changes | Each champion can explain the whole loop from memory in under two minutes |
| 3 | Zero-tax adoption | A person who was not a champion completes a governed change alone, without either champion's help. This is the first exit gate that is a person rather than a test |
| 4 | The link becomes checkable | A command answers "show me the session work behind this change" and its answer is verified, not asserted |

**LONG, the quarter.** R1 then R2 then R3 as in section 4, each entered only
when the previous exit checklist passes, never because a date arrived.

---

## 6. Work breakdown, to task level

Everything below names its files and its check. An item that cannot is not a
plan step and stays in the parking lot.

### Tonight, R0
Steps 1 to 13 in section 3. Not repeated here.

### Sprint 1, R1 candidates, ranked

| Id | Item | Objective served | Files | Check |
|---|---|---|---|---|
| R1-1 | Fence registry stops being an append-only log read as a live list | verified delivery | `tools/bm_fence_hook.py`, `STATE.md` render | hook run naming a real claim, its own suite exit 0 |
| R1-2 | The two records name one change identifier | collaboration | both products' record creation | a command resolves one from the other |
| R1-3 | Adoption costs a joining person nothing | collaboration | install path, first-run surface | a person who has never used it completes a change alone |
| R1-4 | Command-line fences can be parked without adoption gymnastics | verified delivery | `tools/bm_store.py` session handling | claim then park from two separate shell calls, no refusal |
| R1-5 | Memory architecture designed and ratified, not built | context survives | design document only | a ratified decision record with two rejected alternatives |

### Parking lot, items that cannot yet name their objective

- A shared hosted store. Named as expensive, not yet named as necessary.
- A seventh public command. The surface consolidated inward tonight on purpose.
- Runtime ports beyond what `docs/RUNTIMES.md` already marks verified.

---

## 7. Sprint and update cycle

- **Monday, 60 minutes.** Read the week's notes oldest first with no discussion,
  count minutes lost, count what the tools caught, discuss only what appeared
  more than once, change exactly one thing, write the decision and what would
  reverse it, name who is blocked.
- **Exactly one change per week.** Change five things and a bad week teaches
  nothing. Change one and the cause is known.
- **A check earns the right to block** only when it has caught something real at
  least once, the notes have gone quiet about it, and it applies to the riskiest
  paths. It loses that right the same day it blocks somebody wrongly.
- **Release on the boundary, only if green.** A sprint that ends red does not
  release, and that is a reportable outcome rather than a failure.
- **Backlog** is proposed ranked, with each item naming its objective, and
  approved at the Monday review.

---

## 8. What needs a human hand, enumerated before the unattended stretch

Per the standing law that a blocker raised at hour one is a question and the
same blocker at hour six is a gap in the report:

1. GitHub private vulnerability reporting is a settings click that has not been
   made. `SECURITY.md` names it as outstanding rather than claiming it is done.
   Does not block tonight.
2. Creating the throwaway pilot repository, if it is to live under the founder's
   own account.
3. Nothing else in tonight's path needs him.
