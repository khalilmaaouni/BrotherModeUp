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

## 5. The adopt defect. OPEN, carried over from the FIRST audit.

A refused adoption attempt (one session tries to adopt another's live thread
without the override, and is correctly told no) STILL writes a permanent
"Adopted from dead/stalled thread" handover block into STATE.md. The refusal is
correct; the side effect is a lie left on disk.

This has now survived two audits and a full remediation session. It should go
first next time.

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

## 10. The suites cannot be run concurrently. OPEN.

They rename a module aside mid-run, so two at once break each other. Reproduced
tonight: the fence hook suite failed once under contention and passed on re-run.

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

## 16. `bm_store.py claim --help` claims a record named `--help`. OPEN. Found 2026-07-28.

Reproduced: `python3 tools/bm_store.py claim --help` prints
`claimed '--help' as lifecycle 11783c30...`. Unknown and help flags are treated
as a record name instead of exiting non-zero. Small, cosmetic in isolation, and
recorded because the new learning CLI must NOT copy the pattern from its sibling.

## 17. The English-only, 400-character correction filter. OPEN. Found 2026-07-28.

Measured, not estimated: of five founder-shaped messages, two were captured. A
4,000-character correction was dropped by the length cap, and a FRENCH correction
was dropped by the English-only regex, both silently. The founder works in French.

This is the gap the correction-learning program's Loop 4 exists to close, and it
is stated here so the gap is on the record even if that loop slips.

---

## What is genuinely finished

All 17 findings of the second audit are closed in code, with CI green on Linux,
macOS and Windows across both supported Python versions, and the recovery suite
running on all three for the first time. `v2.0.0-rc.2` is tagged from a green
commit, `rc.1` withdrawn. The telemetry split is merged and its cause fixed.

That is a real amount of ground. It is also, by the count above, fourteen open
items away from being a finished product.
