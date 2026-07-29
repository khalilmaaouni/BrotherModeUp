# Everything we did NOT finalize, 2026-07-27

The complete list, ordered by how much harm it can do. Nothing is omitted for
being embarrassing; an unstated gap is the failure this file exists to prevent.

Status words mean exactly one thing each:
- **OPEN**: known, reproduced, not fixed.
- **PARTIAL**: something landed, but not what the requirement asked for.
- **UNPROVEN**: believed correct, never demonstrated.
- **DEFERRED**: deliberately not done, with the reason.

---

## P7 (found in passing, NOT this loop's code): the loop-close gate flakes 1 run in 16. OPEN.

`test_bm_store.py::TestPostAuditLoop3ApprovalReceipts::
test_a_forged_token_refuses_and_says_nothing_useful_to_a_guesser` forges a token
as `real["token"][:-1] + "0"`. The token is hex, so once every sixteen runs the
last character IS already "0", the forged token is the real one, the approval
succeeds and the test fails with "OwnershipRefused not raised". Observed twice
while running the gate for Loop P7, both times on a tree whose only changes were
elsewhere, and both times green on the next run.

It is a defect in the test, not in the receipts: the fix is to forge a character
that cannot collide, for example flipping the last character between "0" and "1"
based on what it already is. Left untouched here deliberately, because that file
region belongs to another loop and a green-looking gate is worth less than an
honest note. Anyone reading a single red run of that test should re-run before
believing it. OPEN.

## P7: the FTS5 fast path ships DISABLED by default. DEFERRED, deliberately.

The loop's plan calls FTS5 a fast path; this build makes it opt in
(`BROTHERMODE_FTS5=1`). The project rule that an optional capability ships
disabled and falls back to the standard library won, and it won for a reason
that outlives the rule: FTS5's tokenizer decides what counts as a word and its
BM25 is a number the founder cannot re-derive by hand, so it should not arrive
by surprise in a tool whose selling point is explainable retrieval. The cost is
that the measured retrieval gain is not on by default. DEFERRED.

## P7: the retrieval gain is measured on ONE labelled fixture. PARTIAL.

The improvement claim rests on the stemming case, reproduced on the real CLI
both ways round: a rule written about "pushing", a task that says "pushed",
found under fts5 and not under lexical. That is a demonstration, not a
benchmark. No labelled corpus of founder rules with graded relevance exists yet,
so "FTS5 improves measured retrieval" is true of the fixture and unproven at
scale. PARTIAL.

## P7: index maintenance covers approval and edit, not every future write. UNPROVEN in general.

Rule text can only enter the store through approval and through edit, and both
write the index row in their own transaction. A state change (forget, supersede,
deprecate) does not touch the index because it does not touch the text, and
state is filtered before ranking. That reasoning is correct today and is not
enforced by anything mechanical: a future write site that inserts a rule version
without calling `_fts_write_rule` would drift, and only `verify` would catch it.
UNPROVEN, and now less costly: since the fix round of 2026-07-29 the index is
reconciled against the rules at the point retrieval consumes it, so a write site
that forgets `_fts_write_rule` costs one rewrite of the index rather than wrong
answers. Naming the omission is still `verify`'s job, and the mechanical
enforcement is still missing.

## P6: the run stored the founder's prompt by default. CLOSED by fix round P6.

The first version defaulted the run's excerpt to the query itself, so an
ordinary `apply` wrote up to 500 characters of verbatim task text into
`learning_retrieval_runs`. It now stores the task's TERMS instead: sorted,
deduplicated, stopword-free, order destroyed, secret-scrubbed, and capped at
`bm_learning.MAX_QUERY_TERMS` (a task above the cap stores none and is refused
as `no_task_text`). The set is what the ranker reads, so measurement is
unchanged, and the sentence cannot be read back off the row.

Still open on the same subject: `learning_applications.task_excerpt` has kept
the query by default since Loop 7 and was NOT changed here, because that column
predates this loop and other paths read it. The prompt therefore still lives in
the store, in that table, on the default `apply` path. OPEN.

## P6: a task's vocabulary is still stored, even though its prose is not. OPEN.

The term set is not the prompt, and it is not nothing either: it names the words
the founder used. It is enough to tell that a task mentioned a customer, a
codename or a person. Anyone with read access to the sqlite file sees that list.
Refusing to store terms at all would make every retrieval that returned nothing
permanently `not_decidable`, which is the measurement this loop exists to
provide, so the trade was taken deliberately rather than by default.

## P6: `retrieval_uuid` is nullable forever, so "legacy" is a permanent state. DEFERRED.

Nothing forces an application row to carry a run, and nothing ever will for the
rows that already exist. A later round could refuse to write an application
without one, making the column effectively required for new rows while the old
ones stay legacy. Not done here: that is a second migration and this loop
already owns one.

## P5-fix: `apply` discloses the two-units-of-work ambiguity, it does not resolve it. PARTIAL.

With `--record`, each unit of work gets its own application row and the earlier
collapse is closed. WITHOUT `--record`, two pieces of work in one session that
share task wording still share a row; `apply` now names the work record that row
belongs to and says it cannot tell them apart, and still exits 0. Making
`--record` mandatory for `apply` was considered and NOT done in this round: it
would break the documented retrieve-then-claim order that P5's own linking
behaviour depends on. OPEN for the next round on this path.

## P5-fix: the fixes were verified through `apply`, not through the alias. UNPROVEN.

`relevant --record-applications` calls the same
`Store.record_learning_applications`, so it inherits every store-side fix in
this round, and `relevant` WITHOUT the flag still records nothing at all, which
is the deprecated behaviour it is kept for. Neither statement was re-tested
against the alias in this round beyond the existing deprecation test. Believed
correct, not demonstrated.

## Loop P5: `relevant` is deprecated but not removed. DEFERRED, by design.

The alias is kept so existing scripts and docs do not break silently, and it
prints a deprecation line to stderr on every run. It still honours the old
opt-in `--record-applications` contract, so a caller who keeps using it keeps
the old hole. Removal is scheduled for the next major version and is NOT done.

The narrative docs still show `relevant` in their examples; see
`docs/KNOWN-LIMITS.md`. PARTIAL.

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

Status after Loop 12 (2026-07-29): the scrubber itself was broken in the way
this entry did not suspect, and it is now fixed. Every vendor pattern was
anchored with `\b`, and Python counts `_` as a word character, so any secret
with a word character in front of it never matched: `OPENAI_KEY_sk-live_...`,
`AWSKEY_AKIA...`, `GITHUB_ghp_...`, `nid_123-45-6789`. Those went to sqlite and
to `corrections.jsonl` in cleartext while `redaction_count` recorded 0. The
boundary is now "letters and digits bind, separators do not". Separately, the
same pattern list was quadratic on long input and a 20 KB inbox row cost 75
seconds of CPU; the key=value prefix is now bounded and 32 KB redacts in
milliseconds.

Also closed by Loop 12: the withholding claim in the entry above was true of
`dump` and `show-candidate --json` but NOT of `candidates --json` or
`why --json`, which printed `raw_text` and `learning_evidence.excerpt` in full
with no flag. There is now ONE definition of the rule (`_withhold_source` in
bm_learn.py) used by every JSON command. And the fields BESIDE `raw_text`
(trigger, action, reason, domain, scope key, approval reference, override
reason) are now scrubbed on the way in, at capture, at approval and at edit;
previously only `raw_text` was.

The PROSE gap this entry opened with is UNCHANGED and still OPEN for
`records.evidence`, `records.objective`, `digests.body` and `transitions.note`.
A scrubber that now matches its own documented token shapes is still not a
redactor of ordinary sentences.

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
- OPEN (fix round P3, 2026-07-29): `edit_learning_rule` now requires its own
  one-time founder receipt, minted by `Store.mint_edit_receipt`. Neither has a
  CLI command, so the only caller is imported code and the suite. That is the
  same reach it had before the gate, so nothing a founder could do is lost, but
  a founder who wants to reword a rule still cannot do it from the command line
  and has to approve a replacement and stand the old one down. The CLI pair
  (`grant-edit`, `edit`) is deliberately NOT in this fix round: adding founder
  surface is a design decision, not a fix.
- OPEN (fix round P3): an edit receipt hangs off the rule's SOURCE CANDIDATE,
  because that is what the receipts table's foreign key points at. A rule whose
  source candidate has been deleted cannot be edited at all
  (`no-source-candidate`). Correct as a refusal, but it means "editable" quietly
  depends on a row nobody thinks of as part of the rule.
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
- CLOSED 2026-07-29 by loop P4, after re-reproducing it on the real CLI. Was:
  a GATE rule could be cut off by the result limit. The relevance floor
  exempted gates, so a gate was always ELIGIBLE, but ranking still ordered by
  scope, state and relevance, so a wordier match could outrank it. Reproduced
  again with two global rules and `--limit 1`: the gate ranked second and
  never reached the model. Fixed structurally rather than by promoting gates
  in the ranking, which would have changed Loop 5's retrieval order and is the
  founder's call: the limit now applies to soft rules only, so every
  applicable live gate is returned and the ranking is untouched. Diagnostics
  `gates_returned`, `gates_total`, `soft_returned` and `soft_omitted` make the
  two statements separable, and the CLI prints them as two sentences. The
  previous advice, do not retrieve with a limit of 1 when gate rules exist, is
  withdrawn; `--limit 0` now means gates only rather than nothing.
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

## 20. What Loop 8 built, and what its correction round fixed. Added 2026-07-29.

Before this loop, `learning_applications` could record that a rule was shown and
followed or ignored, but nothing connected that to whether the work actually
went well. Loop 8 adds the other half: `bm_learn.py outcome` lets you say "this
record had to be redone" (rework) or "a defect escaped a record you already
called done" (escaped defect), `bm_learn.py loop-failures` reports counted
classes over a time window, and `bm_learn.py rule-outcomes` / `repeat-check`
answer "what happened after this rule was shown" and "did I already tell you
this" for one rule or one candidate.

Commit `3e3a60f` built the grading. Commit `9cff643`, a correction round found
by driving the real CLI against a throwaway store while the suite stayed green
(the same method that found every other serious defect in this project), fixed
three ways the first pass would have misled the founder:

1. **The same outcome, reported twice, minted two candidates.** Running
   `bm_learn.py outcome` again for the same rework, or a hook firing twice,
   grew the weekly review's counts with keystrokes rather than with new events.
   Fixed: a pending candidate with the same content hash, source and reference
   is now reused instead of duplicated, and the CLI says so
   (`reused_existing`). A genuinely different rework, described in different
   words, still gets its own candidate.
2. **An outcome could blame a rule for work it was never part of.** Matching an
   application to a piece of work used to accept either "same work record" OR
   "same session", combined with OR. A session can hold more than one piece of
   work, so an outcome on record A could grade every rule applied to record B
   in the same session as well. Fixed: when the outcome names a record, only
   applications naming that same record count (or, for an application recorded
   before it had a record link yet, the session as a backstop). An application
   naming a different record is not in this work, whatever session it shares.
3. **Rework and escaped defects were counted as the founder repeating himself.**
   The "repeated settled corrections" line is supposed to answer "did I have to
   say this twice", and outcome-derived candidates were folding into that count,
   which told the founder he had restated an instruction when nobody had said
   anything twice. Fixed: outcome gradings are now reported on their own line
   (`outcome_gradings`) and never counted as a repeated correction.

What is still honestly open, stated rather than discovered later:

- OPEN: channel 3 (rework, escaped defect) still has no automatic detector.
  Somebody has to notice and run `bm_learn.py outcome` by hand. This was
  already open after Loop 4 (item 17b) and Loop 8 does not close it, on the
  same reasoning: a wrong automatic verdict about "this was rework" is review
  cost the founder did not ask for.
- OPEN: grading degrades to the session-only match whenever an application has
  no work record yet (recorded before the record was claimed). That match is
  honestly weaker than a record match, and the loop-failures output does not
  currently flag which of its counts came from the weaker path.
- UNPROVEN: every grading in this loop was created by a test or by the probe
  above, against a throwaway store. Nothing here has graded a real day of the
  founder's work. The same caveat as item 1 applies to every count Loop 8 can
  produce.
- `SECURITY.md`'s line-count claim was re-measured after this loop (about
  27,130 lines of standard-library Python and shell, most of the growth being
  test code) but that is a size claim, not a security review; Loop 12, not
  Loop 8, is the security pass, and item 12 below still applies to it.

---

## 21. Approval receipts landed in code; three documents still describe the old flow. OPEN. Added 2026-07-29.

Post-audit LOOP 3 (Model A) closed the audit finding in `tools/bm_learn.py`,
`tools/bm_learning.py` and `tools/bm_store.py`: approval now requires a
one-time receipt, and the CLI no longer synthesizes the evidence it used to
invent. The repro that produced gate rule 61de7eb9 at exit 0 against d88abcc
now refuses with `no-approval-receipt` and creates nothing.

What is NOT done, and it is wording rather than mechanism:

- `README.md` line 109 and `docs/CORRECTION-LEARNING.md` line 179 both say
  approval is "founder-only". That was already a stronger claim than the code
  supported, and it is still stronger than Model A supports: the mechanism
  proves an answer was given about this exact candidate, once, recently. It
  does not prove who gave it. Those lines need to say so, and the two-step
  `grant-approval` then `approve` flow needs its walkthrough.
- `SECURITY.md` does not yet describe the receipt token as a secret with the
  handling rules the code enforces (shown once, never stored, never logged,
  fifteen-minute life).

The loop plan assigns these three files to the Documentation Agent, so this
loop deliberately did not edit them. Until it does, the shipped documentation
overstates the guarantee, and `docs/KNOWN-LIMITS.md` carries the honest version.

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
