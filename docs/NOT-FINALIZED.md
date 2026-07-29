# Everything we did NOT finalize, 2026-07-27

The complete list, ordered by how much harm it can do. Nothing is omitted for
being embarrassing; an unstated gap is the failure this file exists to prevent.

Status words mean exactly one thing each:
- **OPEN**: known, reproduced, not fixed.
- **PARTIAL**: something landed, but not what the requirement asked for.
- **UNPROVEN**: believed correct, never demonstrated.
- **DEFERRED**: deliberately not done, with the reason.

---

## 1. Never run on a real day of your work. UNPROVEN. Highest harm.

Everything in this repository rests on test suites, adversarial review and
simulated lifecycles. Not one hour of real founder work has gone through the V2
store. Every score, including the good ones, inherits that caveat.

No amount of further test-writing closes this. Only using it does.

## 2. Bash writes are not gated by the fence hook. OPEN.

The PreToolUse hook sees Edit, Write and NotebookEdit. A file written through a
shell command goes straight around it. So "one writer per file" holds for the
tools the hook can see and not for the shell.

Why not fixed: gating Bash means parsing arbitrary shell to decide which paths a
command will touch, which is either unreliable or so strict it blocks ordinary
work. It needs a design, not a patch.

## 3. Session identity is harder to forge, not unforgeable. PARTIAL.

Was: the owning value was printed in plaintext into the file every session reads,
so the ownership check compared a public value against itself.

Now: a per-session secret, stored owner-only, with only a hash on the claim.
Copying the label from STATE.md gains an attacker nothing (proven).

Still: any process running as your user can read the token file and impersonate
fully. Perfect unforgeability is not reachable on one machine, one user, no
network. Documented in docs/HOOKS.md rather than overclaimed.

## 4. Handovers are lock-serialized, not transactional. PARTIAL.

The audit asked for handovers stored in the database and rendered into the view,
so nothing appends to a generated file. What landed is a lock plus a read-back
that verifies the write survived, with two honest new outcomes (busy, lost).

The follow-up shape is recorded in the code: a handovers table with a uniqueness
constraint, a store API inserting inside the same transaction as the park or
adopt, and rendering inside the generated markers. After that lands, the lock and
the append path delete entirely.

## 5. The adopt defect. REFUTED and CLOSED, 2026-07-28. This entry was stale.

Was recorded as: a refused adoption attempt still writes a permanent "Adopted
from dead/stalled thread" handover block into STATE.md, having survived two
audits and a full remediation session.

**It does not. It was already fixed, and this file had not caught up.** Found by
the correction-learning Loop 0.5, which reproduced the scenario rather than
trusting either the code comments or this entry.

Reproduced in a scratch project: session A holds `alpha` live; session B runs
`adopt alpha --session sessionB` without the override. Result:

```
ADOPT REFUSED (live-session-adopt-blocked): lifecycle af66631b... is ACTIVE
under a different, live session 'sessionA'; adopting it requires explicit
adopt_from_live_session=True
exit=2
```

STATE.md contained no "Adopted from" block afterwards, and `alpha` remained
active under sessionA at version 1, untouched.

The fix is the GATE 3 ordering change in `_adopt_core` (tools/bm_threads.py:1109):
the store transition happens FIRST, so a refusal raises before anything can be
written into STATE.md. It is covered by
`test_bm.py:779 test_adopt_without_the_flag_is_refused_and_changes_nothing`,
which asserts STATE.md is byte-for-byte unchanged, and it is CALIBRATED at
test_bm.py:813, where `_adopt_core` is monkeypatched back to the old
deliver-then-transition order to prove the test fails for the intended reason.

Lesson recorded rather than just the fact: a status file that is updated by hand
drifts from the code it describes, and a stale OPEN is not harmless. It cost this
program a planned remediation loop, and had nobody re-reproduced it, the "fix"
would have been a second fix layered on a working one.

## 6. Recovered work is owner-only on POSIX only. OPEN.

The guarantee rests on a 0700 file mode. Windows governs access by ACLs, where
chmod can only toggle a read-only bit, and this project does not set an ACL. On a
shared Windows machine, treat recovered work as readable by other local accounts.

Found only because the recovery suite entered CI today. Closing it needs a real
Windows ACL call, not a softer assertion.

## 7. The lazy core missed its own target. PARTIAL, measured.

Target was under 400 always-on tokens. Achieved 1,490, down from 10,407. A 7.0x
cut that misses the goal by 1,090.

What remains is the triage, the safety floor and thirteen routing rows. Getting
under 400 means cutting routes or the floor, and neither is worth the saving.

Not re-baselined. The target stands and is unmet.

## 8. The lazy core is UNPROVEN in the way that matters.

Nothing yet demonstrates that a session actually LOADS the right reference when it
should. The risk named in the design is silent degradation: the dimensions this
project wins are exactly the ones that decay quietly if a file is never read.

The planned guard, a Stop hook that flags when depth was warranted but never
loaded, is NOT built.

## 9. Three scoring checks are red. OPEN.

`prediction-seals` (3 sealed against a target of 5), plus two cadence checks.
These accrue over time rather than being fixable in one session. They are process
hygiene, not code defects.

Related and worth naming: this gate FAILS locally and PASSES in CI, because CI has
no vault so the checks return NO-DATA. A gate that cannot fail where it runs is
not really gating anything.

## 10. The suites cannot be run concurrently. OPEN, now mitigated but not fixed.

They rename a module aside mid-run, so two at once break each other. Reproduced
2026-07-27: the fence hook suite failed once under contention and passed on re-run.

MITIGATION, 2026-07-28 (correction-learning Loop 0.5): `tools/test_all.py` runs
all four suites SERIALLY, one subprocess each, and returns a single exit code.
This makes the safe path the easy path and gives every loop close one quotable
gate command instead of four remembered ones. It also REFUSES to run when a
`test_*.py` file exists on disk but is not in its `SUITES` list, so a new suite
cannot silently escape the gate.

That is a mitigation, not a fix. The underlying design defect is unchanged: the
suites still rename a module aside, so running `test_all.py` twice at once, or
running it alongside a bare suite invocation, will still break. Fixing it
properly means removing the module-rename technique from the suites themselves,
which is a change to test architecture and not to a runner.

Calibrated 2026-07-28, both directions proved:
- a deliberately failing suite added to `SUITES` produced `1 SUITE(S) FAILED`,
  exit 1;
- the same suite present on disk but NOT in `SUITES` produced
  `REFUSING to run ... not in the gate`, exit 2.
Restored afterwards: 419 tests across 4 suites, 2 skipped, ALL GREEN, exit 0.

Not in CI. CI deliberately splits the suites across platform legs to produce
per-platform evidence, and `test_all.py` is the LOCAL loop-close gate. Wiring it
into CI is a Loop 13 option, not done here.

Related, and your own observation from tonight, recorded as a hypothesis rather
than a finding because it is not yet measured: when the machine slows down, token
spend goes up. Plausible mechanism is that contention makes suites take ten times
longer (test_bm went from 20 seconds to 202), which produces timeouts, re-runs and
flakes, each costing a full diagnostic round.

## 11. Phase 3, the public install, is DEFERRED.

Not started, by your own sequencing decision: blockers first, and nothing public
ships a nice install for an unsafe tool. Setup and immediate usefulness therefore
barely moved (6.8 to 7.0) and that is deliberate rather than a miss.

Remaining: a one-command installer, hooks written by the installer rather than by
hand, and a Windows-native hook dispatcher, since the documented install path is
still shell-dependent.

## 12. The independent re-audit was never run. DEFERRED.

The plan's Loop 0 was a closing adversarial pass against all 17 findings plus the
comparison dimensions, ideally with a second model family, since refuters from one
family share one family's blind spots.

It did not run. So "all 17 closed" rests on MY verification of the fixes plus CI,
not on an independent adversary re-attacking them. That is weaker evidence than
the finding of each defect, which came from an outside auditor.

## 13. Orchestration practice did not improve, only the outcome did.

Fences were written AFTER dispatch three times. Two agents were given the same
file under an "add-only" fence, which is not a safe concurrency primitive on a
text file. No collision resulted, because the write sets happened to be disjoint.

Scored flat rather than up, because scoring a lucky outcome is how a scorecard
becomes flattery.

## 14. Findings 16 to 63 of the FIRST audit were triaged by class.

Never individually re-proven. Stated in the limits file so nobody mistakes triage
for verification. Unchanged this session.

## 15. `dump` redaction is a secret scrubber, not a redactor. OPEN. Found 2026-07-28.

Added by the correction-learning Loop 0 baseline, which probed `redact_text`
directly rather than trusting the docstring.

The default-deny plumbing is genuinely good: every TEXT column not in
`_DUMP_SAFE_COLUMNS` is read live from the schema and passed through the
scrubber, so a new column is covered the moment it exists. But the scrubber
removes secret-SHAPED substrings only (`sk-`, `AKIA`, `password=`, `Bearer`).
Ordinary prose and absolute filesystem paths pass through untouched, and were
observed verbatim in real non-raw dump output for `records.evidence`,
`records.objective`, `digests.body` and `transitions.note`.

Why it matters now: correction learning will store verbatim founder messages. A
correction naming a client, a number, or a person carries no secret-shaped token
and would be dumped in full. SECURITY.md's export posture needs to say this
plainly, and the learning schema's raw-text columns need stronger treatment than
the scrubber.

Evidence: docs/superpowers/specs/2026-07-28-correction-learning-baseline.md section 6.

Status after Loop 1 (2026-07-29): the learning tables exist and their free-text
columns ARE covered by the default-deny scrubber, proved with secret-shaped
content in test_bm_store.py. The prose gap is unchanged and still OPEN. It is
not yet REACHABLE, because no writer for those tables exists: nothing can put a
founder's sentence into the store today. Withholding raw_text and evidence
excerpts from dump entirely lands with the writer in Loop 2, which is the first
moment the gap becomes real.

## 16. `bm_store.py claim --help` claims a record named `--help`. OPEN. Found 2026-07-28.

Reproduced: `python3 tools/bm_store.py claim --help` prints
`claimed '--help' as lifecycle 11783c30...`. Unknown and help flags are treated
as a record name instead of exiting non-zero. Small, cosmetic in isolation, and
recorded because the new learning CLI must NOT copy the pattern from its sibling.

## 17. The English-only, 400-character correction filter. CLOSED 2026-07-29 (Loop 4).

Measured, not estimated: of five founder-shaped messages, two were captured. A
4,000-character correction was dropped by the length cap, and a FRENCH correction
was dropped by the English-only regex, both silently. The founder works in French.

Closed by Loop 4. Detection moved into `bm_learning.detect_correction`, which
runs English, French and Japanese phrase packs (the old English regex survives
inside the English pack, so nothing that used to be captured stopped being
captured), and length now EXCERPTS with the omitted character count recorded
instead of dropping. Proved through the real SessionEnd CLI, not only in tests: a
French, a Japanese and a 6,000-character correction were all captured in one run,
while a question ("why didn't you use the desktop app?") was not.

Still true, and stated rather than implied:

- The packs are starter phrase lists, not language understanding. A correction
  phrased in a way no pack knows is still missed, and the honest name for that
  is a recall gap. `bm_learn.py capture` covers any language by hand.
- The negative filters (question, brainstorming, changed business decision) are
  four named fixtures, not a measured false-positive rate. There is no labelled
  review set, so `bm_learn.py metrics` reports counts and refuses to call them
  accuracy.
- Nothing measures recall on a real day of the founder's work yet. That is item
  1, and it stays open.

### 17b. What Loop 4 owed the plan and did not build. OPEN, added 2026-07-29.

Item 17 above is the FILTER, and the filter is closed. The plan's Loop 4 asked
for more than the filter, and the first pass shipped without saying which parts
were missing. The correction round built three of them and left one open. Stated
here so nobody reads "Loop 4 closed" as "Loop 4 complete":

- BUILT: capture channel 3 (outcome-derived candidates). `bm_learn.py outcome`
  and `Store.capture_outcome_candidate` create `rework` and `escaped_defect`
  candidates carrying the work record and the artifact, and refuse when either
  cannot be named.
- BUILT: transcript pairing. Every correction row now carries a HASH of the
  assistant response it answers, a bounded redacted excerpt of it, and the
  artifact paths touched near it. The whole response is never persisted.
- BUILT: false positive reason categories in `bm_learn.py metrics`, bucketed
  from the founder's own rejection reason, with "other" for anything the buckets
  do not fit.
- OPEN: channel 3 is not a DETECTOR. Nothing watches the record stream and
  decides on its own that a piece of work was rework or that a defect escaped a
  completed record. Something that noticed has to run the command. Automatic
  outcome detection is unbuilt, on purpose, because a wrong automatic verdict
  about "this was rework" is review cost the founder did not ask for.
- OPEN: the correction row does not carry the current work record. The plan says
  "current work record if known" and telemetry does not resolve one, so it is
  not written. The record travels with channel 3 candidates instead.

---

## 18. What Loop 6 built, and what its conflict detector cannot see. Added 2026-07-29.

`learning_edges` went from an existing but unwritten table to the record of how
rules relate. Approval now REFUSES to create a second injectable rule that
contradicts a live one, retrieval SURFACES a conflict instead of quietly
choosing a side, and `bm_learn.py verify` reports integrity findings with an
exit code a script can gate on (0 clean, 1 findings, 2 could not run).

What is honestly limited, and why each limit was chosen rather than missed:

- OPEN, by design: detection is LEXICAL. It finds a reversal of the same
  instruction ("always push through the desktop app" against "never push
  through the desktop app"), which is the shape a founder's own change of mind
  takes, whichever side is padded with ordinary extra words and however
  differently the two triggers are phrased. Both of those hid a live reversal
  until the correction round below. It does NOT find "indent with tabs" against
  "indent with four spaces".
  There is a test asserting that blind spot rather than hoping about it, and
  `bm_learn.py link a contradicts b` exists so the founder can declare any
  conflict the detector cannot see. A declared conflict counts exactly as much
  as a detected one everywhere downstream.
- OPEN: containment between two non-global scopes is not inferred. Nothing in
  the store says artifact `executive-update` lives inside project `Tonari`, so
  two different non-global scopes report as disjoint and coexist. Guessing here
  would decide whether an approval is blocked, on no evidence.
- OPEN: of the plan's four founder resolutions, three are commands (supersede,
  mark contradicted, deprecate). "Narrow one scope" is not, because
  `edit_learning_rule` edits a rule's TEXT and cannot move its scope. Narrowing
  a scope today means approving a new, narrower rule and standing the broad one
  down.
- The conflict scan is pairwise over injectable rules, O(n squared). That is
  tens of rows on a real store. If it ever stops being tens the fix is an index,
  not a silent cap on how many conflicts get reported.
- The override is not a loophole and is not silent: forcing an approval past a
  contradiction writes both an evidence row and a `contradicts` edge, so the
  pair keeps showing up in `conflicts`, in `relevant`, and as a `verify`
  finding until the founder resolves it.

### Correction round, 2026-07-29: four ways the done gate leaked

Found by driving the real CLI against a throwaway store while all four suites
were green, which is the same way every serious defect in this project has been
found. All four are fixed and each carries a calibrated regression test.

1. **A padded reversal was invisible.** The reversal was scored on symmetric
   token overlap, which punishes length: adding one ordinary founder clause to
   "never push through the desktop app" dropped the score under the floor, the
   pair came back `not_comparable`, and approval, `conflicts`, `verify` and
   `relevant` all reported clean while two opposite instructions sat in the
   injectable set. Now judged on how much of the SHORTER action the longer one
   also names (`SUBJECT_CONTAINMENT_FLOOR`).
2. **A differently phrased trigger was a veto.** `TRIGGER_OVERLAP_FLOOR` could
   downgrade an exact reversal to `unrelated` whenever the founder phrased the
   two triggers differently, which free text routinely is. The floor is now a
   tie breaker, bypassed for a direct reversal, and the verdict says in its
   reasons that it was bypassed.
3. **"no exceptions" flipped a rule's polarity.** The bare word "no" made
   "always run the tests, no exceptions" read as FORBID, so a rule that plainly
   agreed with an existing one was refused as a contradiction the founder could
   only pass by overriding a conflict that did not exist. Intensifier phrases
   ("no exceptions", "without fail", "sans faute") are now stripped before
   polarity is read. That pair is now correctly reported as a duplicate.
4. **Supersession accepted a successor that could not speak.** Any existing rule
   was accepted, including a forgotten or deprecated one, so the live
   instruction went silent while the CLI printed "the successor is returned in
   its place from now on". Refused now (`successor-cannot-speak`), and because a
   successor can also go quiet afterwards, `verify` gained a `dead-successor`
   check for stores where that already happened.

NEW and open, stated rather than discovered later: fix 2 makes the detector
stricter, so two GLOBAL rules that reverse each other while genuinely addressing
different situations ("when writing Python never use tabs" against "when writing
Makefiles always use tabs") are now refused at approval. That is the intended
trade: the founder narrows one scope, or overrides with a stated reason that is
recorded as an edge. It does mean the refusal fires more often than it did.

---

## 19. What Loop 7 built, and what it still cannot see. Added 2026-07-29.

`learning_applications` stopped being an empty table. Retrieval can now record
one row per rule version surfaced for a task, the founder closes each row with
followed, ignored, not relevant or unknown, and `bm_learn.py classify` grades
what happened into the plan's five classes. The done gate holds: for a given
task the store can say which rules were retrieved, shown, followed, ignored,
and why.

What is NOT closed, stated here rather than discovered later:

- OPEN: the retrieval CONTEXT is not stored, only the scope each rule matched
  on. So the miss check reconstructs the context from the scopes that WERE
  recorded, and a project rule missed by a task where no project-scoped rule
  was recorded stays invisible. That undercounts misses, which is the safe
  direction, but it is an undercount and not a clean number.
- A rule that was eligible and fell below the caller's result limit counts as a
  retrieval miss, with the rank named in the finding. That is deliberate (it
  did not reach the acting model, which is what the class means) and it does
  mean the miss count also measures a limit set too low. Read the rank before
  reading the count.
- OPEN, found by probing the real CLI while the suite was green: a GATE rule
  can be cut off by the result limit. The relevance floor exempts gates, so a
  gate is always ELIGIBLE, but ranking still orders by scope, state and
  relevance, so a more wordy match can outrank it. Reproduced with two global
  rules and `--limit 1`: the gate ranked second and never reached the model,
  and `classify` reported it as a retrieval miss. Not fixed here because
  promoting gates to the top of the ranking changes Loop 5 retrieval order and
  is the founder's call, not this loop's. Until it is decided, do not run
  retrieval with a limit of 1 in a store that has gate rules.
- OPEN: `SKILL.md` and `DIGEST.md` were not updated by this loop, because the
  session that built it was not authorised to edit either file. SKILL.md
  already requires retrieval before substantial work and already requires
  naming applied rule IDs (Loop 11A), so the law is not wrong, but it does not
  yet mention `--record-applications`, `disposition` or `should-retrieve`.
  Until it does, recording depends on somebody remembering the flag.
- UNPROVEN: nothing here has graded a real day of work. Every application row
  that exists was created by a test or by a probe against a throwaway store,
  so the same caveat as item 1 applies to every count this loop can produce.
- The proportionality classifier takes NAMED signals from its caller and does
  not infer them. It cannot look at a task and decide the task is trivial; it
  can only report what it was told, plus the one thing it checks itself, which
  is whether a live gate rule exists.

---

## What is genuinely finished

All 17 findings of the second audit are closed in code, with CI green on Linux,
macOS and Windows across both supported Python versions, and the recovery suite
running on all three for the first time. `v2.0.0-rc.2` is tagged from a green
commit, `rc.1` withdrawn. The telemetry split is merged and its cause fixed.

That is a real amount of ground. It is also, by the count above, fifteen open
items away from being a finished product: seventeen numbered items, of which
only 5 (refuted) and 17 (closed by Loop 4) are done, plus 17b which Loop 4's own
correction round opened and left open. The word "fourteen" stood here until
2026-07-29 and was already stale when items 15 to 17 were added, which is its own
small lesson about counts written by hand.
