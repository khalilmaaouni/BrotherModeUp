# Everything we did NOT finalize, 2026-07-27

The complete list, ordered by how much harm it can do. Nothing is omitted for
being embarrassing; an unstated gap is the failure this file exists to prevent.

Status words mean exactly one thing each:
- **OPEN**: known, reproduced, not fixed.
- **PARTIAL**: something landed, but not what the requirement asked for.
- **UNPROVEN**: believed correct, never demonstrated.
- **DEFERRED**: deliberately not done, with the reason.

---

## rc.4 MERGE: the gate carry cap was REJECTED, and what that leaves open. OPEN. Added 2026-07-29.

Two lanes fixed the same defect (a result limit could hide a safety gate) with
designs that cannot both hold. The store lane returns EVERY applicable gate at
every limit and reports `gates_returned == gates_total`. The ecosystem lane
bounded the gates carried past a caller's limit at three, counted the rest in
`gates_omitted`, and printed a warning naming the limit that shows them all.

The merge kept the design that never withholds a safety rule, deleted
`_GATE_CARRY_CAP` and the test that pinned it, and left a named comment where
that test stood in `tools/test_bm_store.py`.

WHAT THAT LEAVES OPEN, in the rejected lane's own words and reproduction: with
twelve approved gates in a store, `bm_learn.py lookup --query "what colour is
the breathing orb" --limit 1 --json` returns TWELVE results, ranks 1 to 12,
every one at relevance 0.0, and an `apply` run records twelve application rows
marked shown. Injection is therefore bounded by the number of approved gates and
not by `--limit`. That is a real cost, it was reproduced on the real CLI on
2026-07-29 (on commit `68eb4d8`), and nothing in the shipped code prevents it.
Closing it needs a design that bounds volume WITHOUT ever dropping a gate,
which neither lane wrote. OPEN.

## rc.4 MERGE: approval now needs two things, and only one of them is mechanical. PARTIAL. Added 2026-07-29.

`bm_learn.py approve` refuses without BOTH a one-time receipt (post-audit Loop
3) and a founder-written `--ref` (Loop P18-fix). Merging the lanes by letting
the receipt excuse a missing reference would have restored the hole P18-fix
closed, so neither guard was dropped.

The honest limit is unchanged by having two of them: the receipt proves that an
answer was given about this exact rule text and has not been spent, and the
reference is prose a caller types. Neither authenticates WHICH human answered.
Anyone who can run `grant-approval` can mint a receipt and type a reference.
PARTIAL.

## P7 (found in passing, NOT this loop's code): the loop-close gate flakes 1 run in 16. CLOSED 2026-07-31 (Loop 2).

`test_bm_store.py::TestPostAuditLoop3ApprovalReceipts::
test_a_forged_token_refuses_and_says_nothing_useful_to_a_guesser` forges a token
as `real["token"][:-1] + "0"`. The token is hex, so once every sixteen runs the
last character IS already "0", the forged token is the real one, the approval
succeeds and the test fails with "OwnershipRefused not raised". Observed twice
while running the gate for Loop P7, both times on a tree whose only changes were
elsewhere, and both times green on the next run.

It is a defect in the test, not in the receipts: the fix is to forge a character
that cannot collide, for example flipping the last character between "0" and "1"
based on what it already is.

CLOSED 2026-07-31 by Loop 2, using exactly that fix: the last character now flips
between "0" and "1" based on what it already is, so the forged token can never
equal the real one. Proven by running the single test 100 consecutive times with
no failure.

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

CORRECTED IN PART, 2026-08-04 (per CHK-2A row 10, docs/closure/reports/2026-08-04-CHK-2A-not-finalized-verdicts.md).
CLOSED IN PART, 2026-07-30, commit 259c30b, "Give every substantial task one
unambiguous work identity, and settle the promise that collided with it."
`apply` now refuses without exactly one of `--record` with an existing work
uuid, `--new-record` with a name, or an active work record already in the
environment, in addition to `--session` (tools/bm_learn.py:733-766). Session
plus query text can no longer collapse two different units of work phrased
the same way into one row: each is refused into its own identity or refused
outright. This closes the gap the original PARTIAL named as not shipped in
that round: making `--record` mandatory for `apply`. Still true and
unchanged: the deeper ambiguity this entry named first is now a hard refusal
rather than a soft warning, which is a stronger guarantee than the entry
originally asked for, not a weaker one.

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

## 1. Used daily, never measured. PARTLY CLOSED. Still the highest harm.

CORRECTED 2026-08-03. This item used to say that not one hour of real founder
work had gone through the V2 store and that everything rested on test suites,
adversarial review and simulated lifecycles. The founder reports the opposite:
weeks of his own daily use, and other people using it on their own machines,
installed by pointing them at this repository.

So the "never used" half is closed, and it was closed for weeks while these
documents said otherwise, which is its own lesson about where a project's truth
actually lives.

What is still open is the half that always mattered more: none of that use has
been MEASURED. No counted projects, no recorded failure or rework rate, no
observed outside participant, no comparison against working without the tool.
Every score on this page still inherits THAT caveat, and no amount of further
test-writing closes it either. Only counting does.

One consequence worth stating for anyone reading before an upgrade: those users
track `main` rather than a pinned tag, so whatever lands on `main` reaches them
on their next install.

## 2. Bash writes are not gated by the fence hook. OPEN.

The PreToolUse hook sees Edit, Write and NotebookEdit. A file written through a
shell command goes straight around it. So "one writer per file" holds for the
tools the hook can see and not for the shell.

Why not fixed: gating Bash means parsing arbitrary shell to decide which paths a
command will touch, which is either unreliable or so strict it blocks ordinary
work. It needs a design, not a patch.

CORRECTION, 2026-08-04 (per CHK-2A row 14, C-02,
docs/closure/reports/2026-08-04-CHK-2A-not-finalized-verdicts.md). The
heading's own premise is still true: the PreToolUse fence hook
(tools/bm_fence_hook.py) still does not see Bash, WRITE_TOOLS excludes it, so
a file written through a shell command still goes straight around the
PreToolUse fence itself. That half of this entry is unchanged and is not
closable by design.

What changed under C-02, landed 2026-08-04 (see
docs/closure/CLOSURE_REGISTER.md): tools/bm_bash_audit.py now refuses an
obvious destructive shell command aimed at BrotherMode's own enforcement
state, and detects and alerts on loss of that state, in both cases only when
BM_FENCE_MODE=enforced is set. The three limits on that guarantee, carried
verbatim from the project's own security documentation rather than
paraphrased:

1. It is a literal match, a small list of destructive shell forms combined
   with the literal names .brothermode and store.sqlite3. It is not a shell
   parser and will not become one here. A name assembled at runtime, held in
   a variable, or sitting inside a script file the hook never reads is NOT
   caught.
2. Full operating-system containment, a sandbox profile, a container, a FUSE
   write mediator, was considered and is explicitly out of scope.
3. When tools/bm_store.py cannot be imported at all, the project check
   itself cannot run, so nothing is refused, even under enforced mode,
   anywhere. That is a fail-open path inside a fail-closed feature, chosen on
   purpose, because the only alternative is refusing every Bash command in
   every directory on the machine, which is not shippable.

All three were checked against the shipped code by CHK-2A on 2026-08-04
(tools/bm_bash_audit.py:321-352, docs/KNOWN-LIMITS.md:111-117,
SECURITY.md:346-352) and each is accurate as literally implemented, not
overclaimed and not underclaimed.

Why not fixed further: gating Bash directly still means parsing arbitrary
shell to decide which paths a command will touch, which remains either
unreliable or so strict it blocks ordinary work. What C-02 adds is a
narrower, named, opt-in refusal for the one destructive shape this entry's
own reproduction used, not a general solution. It needs full operating-system
containment to go further, not a patch.

## 3. Session identity is harder to forge, not unforgeable. PARTIAL.

Was: the owning value was printed in plaintext into the file every session reads,
so the ownership check compared a public value against itself.

Now: a per-session secret, stored owner-only, with only a hash on the claim.
Copying the label from STATE.md gains an attacker nothing (proven).

Still: any process running as your user can read the token file and impersonate
fully. Perfect unforgeability is not reachable on one machine, one user, no
network. Documented in docs/HOOKS.md rather than overclaimed.

## 4. Handovers are lock-serialized, not transactional. CLOSED, 2026-07-29 (Loop P12), REOPENED and CLOSED AGAIN the same day (P12 fix round).

Was: the audit asked for handovers stored in the database and rendered into the
view, so nothing appends to a generated file. What had landed was a lock plus a
read-back, with two honest new outcomes (busy, lost), and the follow-up shape
written down in the code so it could not be lost.

Now: that follow-up landed in full. Schema 5 adds a `handovers` table; the row
is inserted inside the same transaction as the park or adopt; `render_state_md`
renders the undelivered ones inside the generated markers; and the lock, the
append, `_deliver_handover_once`, `_handover_tag` and `_handover_landed` are
deleted rather than shimmed. Closed only after the crash-injection tests the
plan asked for: transition-commit failure leaves no handover, handover-insert
failure leaves no transition, render failure preserves database truth, retry
after a render failure does not duplicate, refused adoption writes nothing, and
a concurrent pair serializes through the store.

The defect was reproduced first, against a real store: parked record, handover
text gone, nothing to recover it from. Two calibration tests reinject the old
shape (delivery as a separate step) and confirm both split states come back.

The fix round, the same day: that CLOSED was premature and the paragraph above
was wrong where it mattered most. The atomicity held, but the retry dedupe was
keyed on the lifecycle plus the content fingerprint across every row for all
time, and the swallow of its uniqueness error was unconditional. The
fingerprint does not cover the state, the version, the transition, the heading
or the sessions, so a record parked, acknowledged, resumed and parked again
with nothing new checkpointed produced the identical key, and the second park
committed with NO handover row at all. `handovers` reported none, STATE.md had
no section, `verify` said healthy. Adoption was hit harder, because it writes
no digest before it transitions: its handover lost the same way while STATE.md
kept rendering the earlier park's heading for a record already adopted.

Reproduced first, at the CLI, on a throwaway store, in both shapes. Schema 6
now keys the dedupe on the lifecycle, the fingerprint AND the heading, over
UNDELIVERED rows only, so an acknowledged handover cannot suppress a later one
and two different headings are two different handovers. The swallow now re-reads
for the undelivered copy that justifies it and raises rather than staying quiet
when there is none, which rolls the transition back. Three new tests, one of
which reinjects the schema-5 index and the old unconditional swallow and
confirms the loss comes straight back.

Still open, and named rather than buried: acknowledging a handover is a manual
command (`handover-ack`), so an unacknowledged one renders into STATE.md on
every regeneration until a human clears it. That is deliberate for now, because
the alternative is a render that mutates the database, but it means a founder
who ignores the section accumulates it.

Also still true, and deliberate: a second park with the SAME heading while the
first is still undelivered stores one row, not two. That is the retry dedupe
doing its job, and the text a founder reads is identical either way, but it
means that second transition has no handover row of its own and the row on
screen names the earlier one. The record always has a visible handover; the
transition-to-handover link is what is one-to-one only up to identical text.

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

ADDENDUM, 2026-08-04 (per CHK-2A row 21,
docs/closure/reports/2026-08-04-CHK-2A-not-finalized-verdicts.md). A re-run
of `python3 tools/bm_score.py` (read-only, never writes, exits 0
unconditionally in non-strict mode) on 2026-08-04 shows four checks red, not
three: cache-economy (32 of 33 sessions warm-read, one at 86 percent),
fence-hygiene (STATE.md older than 2 days), budget-vs-tier (STATE.md fence
lines untagged), and prediction-seals (4 sealed against a target of 5, not
the 3 cited above). Derivation command: `python3 tools/bm_score.py`. The
structural claims above are unchanged and still verified: this gate is
local-vault-dependent, `bm_score.py --strict` still runs in CI
(.github/workflows/tests.yml line 70) where no vault exists, so CI still
reports NO-DATA rather than exercising these checks. The exact count of red
checks is not a fact worth keeping current in this file; it drifts by the
hour with ordinary use, which is the nature of a live telemetry gate rather
than a code defect.

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

CORRECTED 2026-08-04 (per CHK-2A row 22,
docs/closure/reports/2026-08-04-CHK-2A-not-finalized-verdicts.md), replacing
only the closing claim above; the module-rename concurrency defect itself is
unchanged and still true. This entry used to say `test_all.py` was "Not in
CI" and that wiring it in was a Loop 13 option, not shipped. That is no
longer true: .github/workflows/tests.yml now runs a dedicated gate job on
every push and pull request, `python3 tools/test_all.py --artifacts
"$RUNNER_TEMP/bm-test-output" --timeout 1200`, alongside the per-platform
suite and store jobs that still exist for their own reason, per-platform
evidence the serial gate cannot produce. `tools/test_all.py`'s own `SUITES`
tuple now lists 14 suites (derived by counting the quoted `test_*.py`
entries in the `SUITES` tuple, tools/test_all.py:83), not the 4 this entry's
calibration paragraph above describes; that paragraph is left as written
because it documents a point-in-time calibration, not a current count. The
underlying design defect this entry names, that the suites still rename a
module aside and so cannot run concurrently with each other or with a second
invocation of `test_all.py` itself, is unchanged: `tools/test_bm.py` and
`tools/test_bm_bash_audit.py` both still use the technique. CI's own three
jobs (suite, gate, store) still run as separate processes on separate
runners, which sidesteps the concurrency hazard by not sharing a filesystem
rather than by fixing it.

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

CORRECTED 2026-08-01. This item said Phase 3 was not started. Part of it has since
shipped, and part of what it asked for is still genuinely open.

What shipped: a one-command installer and uninstaller, both tested, at
scripts/install.py, scripts/uninstall.py and tools/test_install.py; these write the
hooks rather than asking a founder to hand-edit settings.json, which is the specific
gap this item named. Separately, on 2026-08-01, a Claude Code plugin packaging
merged into main: .claude-plugin/plugin.json, .claude-plugin/marketplace.json,
hooks/hooks.json, skills/brotherme/ and six commands under commands/. That gives a
second, no-cloning install path alongside the tagged-clone one.

What is still honestly open: the plugin path has been installed exactly once, on
the author's own machine, from a local copy of the repository, not from GitHub (see
docs/evidence/2026-07-31-first-plugin-install.md). No install from GitHub has
happened yet, and no external user has ever installed either path. The
Windows-native hook dispatcher this item also asked for is still not built, so the
documented install path remains shell-dependent on that front.

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

## 16. `bm_store.py claim --help` claims a record named `--help`. CLOSED 2026-07-30 (Loop 0).

Reproduced: `python3 tools/bm_store.py claim --help` prints
`claimed '--help' as lifecycle 11783c30...`. Unknown and help flags are treated
as a record name instead of exiting non-zero. Small, cosmetic in isolation, and
recorded because the new learning CLI must NOT copy the pattern from its sibling.

Closed by Loop 0, and it was WIDER than this entry said. The defect was never
specific to `claim`, and it was never specific to `--help`: every command that read
`argv[0]` as a positional before rejecting unknown flags had it, so
`claim --objective "X"` created a record named `--objective` just as readily. The
sweep found four code sites covering seven commands: `cmd_claim`, `cmd_checkpoint`,
`cmd_decide`, and the shared `_cmd_transition` behind park, resume, complete and
adopt.

One helper, `_require_positional` (`tools/bm_store.py:9475`), now refuses any
`argv[0]` beginning with `-` and prints that command's own usage before the store is
touched. Calibrated: reverting the helper turns six of the seven new tests red and
errors the seventh, which is the evidence that they test the fix rather than
agreeing with it.

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

CLOSED IN PART, 2026-08-04 (per CHK-2A row 33,
docs/closure/reports/2026-08-04-CHK-2A-not-finalized-verdicts.md), replacing
only the SKILL.md/DIGEST.md bullet above; the other bullets in this item are
unchanged and still true. That bullet used to say SKILL.md does not yet
mention `--record-applications`, `disposition`, or `should-retrieve`. That is
no longer true of SKILL.md: it now documents the mandatory work identity
`apply` requires (see the row 10 correction on the P5-fix item above), and
names `disposition`, `classify`, and `should-retrieve` by name, with
`should-retrieve` described exactly as answering whether a task shape
warranted retrieval at all. It is still true of DIGEST.md, which is 13 lines
long (`wc -l DIGEST.md`) and names no learning command at all. Recording
substantial-work applications no longer depends only on somebody remembering
an optional flag: `apply` now refuses outright without a work identity
(row 10 correction), which is a stronger fix than merely documenting the
flag would have been.

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

## 21. Approval receipts landed in code; three documents still describe the old flow. CLOSED 2026-07-31.

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

CLOSED IN PART, 2026-07-30 (Loop 2). The identity overclaim is gone from the
shipped pages. Six sites were corrected, one more than the audit listed:
`README.md`, `docs/CORRECTION-LEARNING.md`, `SKILL.md`, `docs/DEMO.md`, the
`grant-approval` help text in `tools/bm_learn.py`, and a comment in
`tools/bm_store.py`. Each now states the limit the mechanism actually supports:
the receipt proves an answer was supplied for this exact proposed rule and has
not already been used, and it does NOT prove which human supplied the answer.

CLOSED 2026-07-31. `SECURITY.md` now carries "Approval and state-change
receipts are secrets": shown once, never stored, withheld from every ordinary
export, fifteen-minute clamped life, single use through a conditional UPDATE in
the same transaction as the change, and bound by fingerprint to the exact
proposal. It also states plainly what a receipt does NOT prove, so the page
cannot be read as claiming founder identity authentication.

---

## 22. `complete <short-prefix>` blames a missing record for unsupported prefix resolution. CLOSED 2026-07-31.

Reproduced twice by the orchestrator driving the real binary while the suite was
green. `bm_store.py complete 5b53b923 --version 1 ...` refuses with
`refused (stale-identity): expected version 1 in a state that allows -> complete;
found no such record`, while the record plainly exists and the full 32-character
lifecycle uuid succeeds on the identical command. Either `complete` does not
resolve prefixes while sibling commands do, or the refusal message is wrong about
the cause. The message is the worse half: it tells the caller the record does not
exist when it does. Not fixed; the session that owns `bm_store.py` next should
decide whether prefixes belong on lifecycle commands at all, and in either case
make the refusal name the real reason.

CLOSED 2026-07-31. Resolved at the CLI layer in `_cmd_transition`, which now
passes its positional through `_resolve_record_uuid` before calling
`transition()`. The concurrency primitive still demands one exact identity,
which is correct for it; the human's shorthand is expanded where the human's
shorthand arrives. An unknown or ambiguous prefix still refuses, and now names
the record it could not find. Three tests, including a calibration that drives
`transition()` with a raw prefix and confirms the original misleading refusal
still reproduces at that layer.

## 23. The two oldest published tags are lightweight, not annotated. OPEN (low impact). Found 2026-07-31, and this entry's first version was WRONG.

CORRECTED the same day, before anyone acted on it. The first version of this
entry said the local and remote tags "point at different things" and proposed
re-pointing the local ones. That was wrong, and acting on it would have
DESTROYED information. Checked rather than assumed:

    remote v2.0.0-rc.1 -> 7c2e0ec   (no ^{} line: LIGHTWEIGHT)
    local  v2.0.0-rc.1 -> tag object ea0ca74 -> commit 7c2e0ec  (ANNOTATED)
    remote v2.0.0-rc.2 -> 2aef6a4   (no ^{} line: LIGHTWEIGHT)
    local  v2.0.0-rc.2 -> tag object 09224c7 -> commit 2aef6a4  (ANNOTATED)

Both names resolve to the SAME COMMIT on both sides. `git fetch --tags` refuses
with "would clobber existing tag" because the ref points at a tag OBJECT locally
and at a COMMIT on the remote, which is a difference in representation, not in
meaning. The local copies carry more information, so re-pointing them at the
remote would lose the annotation for nothing.

THE REAL FINDING, smaller than the one first recorded: `docs/RELEASE.md` requires
release tags to be annotated ("annotated, not lightweight, as the steps below
require"), and the two OLDEST published tags do not meet that rule. `rc.4`,
`rc.6` and `rc.7` all do (each shows a `^{}` line on the remote). Impact is low:
`rc.1` is withdrawn and `rc.2` superseded, so nothing current depends on either,
and a lightweight tag still names the right commit. Left OPEN rather than fixed
because correcting it means force-updating two published refs, which is the act
this project refuses to perform on its own initiative.

The lesson is the entry itself: it was written from a fetch warning rather than
from a comparison, and the comparison took one command.

## 24. The two handover flakes were not reproduced, but a THIRD load-sensitive failure was found and FIXED. 2026-07-31.

The handover named two flakes and asked for deterministic interleaves rather than
retries. Neither could be reproduced tonight, and neither is claimed fixed.

**Handover item 9, "the store suite fails when it runs slowly."** The recorded
correlate was 71 seconds for a failing run against 12 to 13 for a passing one. The
store suite was run three times under deliberate CPU load (four busy processes),
which slowed it from about 21 seconds to about 32: `Ran 660 tests ... OK` all three
times. It also ran inside roughly fifteen full-gate runs across this session with no
occurrence. That is evidence of absence at THIS load on THIS machine, not proof the
defect is gone, and 32 seconds is well short of the 71 recorded.

**Handover item 10**, named as
`test_calibrated_without_the_lock_the_same_pair_duplicates_the_handover`, DOES NOT
EXIST in the tree under that name, and `tools/test_bm_store.py` contains no
`threading.Thread` at all, so the deliberate two-thread race it describes is not in
that suite now. Either it was renamed or removed between the handover and today.

Recorded as UNDECIDABLE rather than closed. Anyone seeing a single red run of the
store suite should re-run before believing it, and should capture the failing test
name, which the CI annotation wrapper added today now does automatically.

**A THIRD load-sensitive failure, in `test_bm.py`, WAS reproduced and IS fixed.**
Surfaced by a parallel session reporting the rc.7 gate red on a loaded machine,
then reproduced here under five busy processes: `test_bm.py` took 1023 seconds
against a normal 40 to 90, and
`TestLoop12RedactionIsLinearInInputSize.test_a_run_of_underscores_does_not_blow_up_either`
failed. Unloaded, the same class runs in 0.198 seconds.

The test was a bare stopwatch, `assertLess(self._time("_" * 32000), 2.0)`, with no
baseline, so it measured the MACHINE rather than the algorithm. It also violated the
principle its own class docstring states two lines above it: "A wall-clock budget is
a blunt instrument, so this asserts the SHAPE." Its sibling already followed that
rule and carries a comment saying its ceiling is loose "so a busy machine cannot fail
this"; this one had no such protection.

**The first fix was wrong, and calibration is what caught it.** Rewriting it in the
sibling's shape, `assertLess(large, max(small, 0.005) * 40)`, was tried and a
deliberately reinjected quadratic redactor PASSED it: a quadratic inflates the small
measurement too, so a ceiling derived from `small` rises with the very defect it
exists to catch. Measured: linear gave 0.069s and 0.193s, a 2.8x ratio; quadratic
gave 0.208s and 3.243s, a 15.6x ratio, and 3.243 still sat under its 8.3s ceiling.

The assertion is now on the RATIO itself, which no defect can inflate: 4x the input
is about 4x the work when linear and about 16x when quadratic, ceiling 8x. Calibrated
both ways (linear 2.4x passes, reinjected quadratic 8.7x fails) and confirmed green
three times under the five-process load that produced the original failure.

**The same weakness remains in the sibling `test_quadratic_blowup_is_gone`**, which
still derives its ceiling from `small`. It has not failed, and it was left alone
rather than changed on the same day its neighbour was, but it is the identical shape
and should move to a ratio next time that file is opened.

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
