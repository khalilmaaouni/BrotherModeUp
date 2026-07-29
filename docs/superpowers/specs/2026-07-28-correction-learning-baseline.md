# Loop 0: the correction-learning baseline, frozen

**HISTORICAL DOCUMENT, dated 2026-07-28. Do not read it as current state.** It is a dated working record: the plan, the verdicts, the blockers and the numbers in it belong to that day and were not updated afterwards. Items it calls open may since have been closed. Superseded by `README.md` and `docs/KNOWN-LIMITS.md` for status, `docs/NOT-FINALIZED.md` for the defect register, `CHANGELOG.md` for what changed since, and `python3 tools/bm_project_facts.py` for version, release tag, hook events and suites.

Date: 2026-07-28
Branch: v2
Commit at freeze: a379877
Platform: macOS (Darwin 25.5.0), Python 3.9.6, sqlite 3.51.0
Program: docs/superpowers/specs/2026-07-28-correction-learning-program.md

Everything below was REPRODUCED by running a command today. Nothing here is
inferred from reading code. Where a claim could not be reproduced it says so.

---

## 1. Working tree at freeze

`git status --short` returned empty. Branch `v2`, commit `a379877`
("Benchmark V1 to V2 to rc.2 against native, and the full list of what is
unfinished"). `VERSION` reads `2.0.0-rc.2`.

## 2. Test baseline

Four suites, run individually, in this order, on this machine:

```
python3 tools/test_bm.py            -> Ran 92 tests in 20.722s   OK (skipped=2)
python3 tools/test_bm_store.py      -> Ran 244 tests in 7.452s   OK
python3 tools/test_bm_autosave.py   -> Ran 34 tests in 16.413s   OK
python3 tools/test_bm_fence_hook.py -> Ran 49 tests in 1.016s    OK
```

**419 tests, 2 skipped, 0 failures, 0 errors.** This is the regression bar every
later loop must clear or exceed.

The two skips live in `test_bm.py` and are environment-dependent by design (per
docs/QUICKSTART.md): one checks for a shell-script autosave this project no
longer ships, the other needs a filesystem that can make a file read-only.

Documentation drift found: docs/QUICKSTART.md section 2 still tells a new user to
expect `Ran 54 tests`. The real number is 92. Recorded, not fixed in this loop
(Loop 0 changes no behavior); queued for Loop 13.

## 3. Network and subprocess claims

Both are mechanically enforced and both passed inside the 92-test run:

- `test_bm.py:1013 test_no_network_claim_is_mechanically_true`
- `test_bm.py:1143 test_no_unreviewed_write_sites`

The manual cross-check documented in README.md:126 remains the human path:
`grep -rn subprocess tools/*.py tools/*.sh | grep -v test_`.

## 4. Schema version 1, reproduced in a scratch project

A throwaway git repository was initialised and `bm_store.py init` run in it.
Tables present:

```
autosave_receipts, claims, decisions, digests, directives,
meta, records, sqlite_sequence, transitions
```

`meta.schema_version` = `'1'`.

**There is no migration machinery of any kind.** `_MIGRATIONS` does not exist.
`_verify_schema_or_raise` (tools/bm_store.py:1983) quarantines on ANY
`schema_version` mismatch, in either direction:

```python
if found_version != str(SCHEMA_VERSION):
    self._quarantine_and_raise(...)
```

Therefore bumping the constant to `2` before a migration branch exists would
quarantine every live store on next open. Loop 1 must add the migration route
before the constant moves. This is invariant L16 in the program document.

Blast radius if it goes wrong: exactly one live store on this machine,
`/Users/khalil.maaouni/Documents/BrotherModeUp/.brothermode/store.sqlite3`.
It will be backed up before Loop 1's first real run.

## 5. Full lifecycle, exercised end to end

In the scratch project, one record was driven through every state. Verbatim
results:

```
claim      -> claimed 'baseline-probe' as lifecycle 1a15bb8a...ab68 (version 1)
checkpoint -> checkpoint 1 recorded for 1a15bb8a...ab68 (version 2)
park       -> parked: 'baseline-probe' is now parked at version 3
resume     -> active: 'baseline-probe' is now active at version 4
complete   -> complete: 'baseline-probe' is now complete at version 5
verify     -> verify: healthy, 0 problem(s)
dump       -> full JSON export, all nine tables
```

The optimistic-concurrency guard was also proved live, by accident and then on
purpose. Passing a version that did not match produced:

```
refused (stale-identity): expected version 2 in a state that allows -> parked;
found version 1 state 'active'
```

Fail-closed, named error, non-zero exit. This is the exact behaviour the learning
API must inherit for `edit_learning_rule` and `approve_learning_candidate`.

### 5.1 A minor CLI defect found while doing this

`python3 tools/bm_store.py claim --help` does not print help. It CLAIMS a record
literally named `--help`:

```
claimed '--help' as lifecycle 11783c30... (version 1, session cli-10f1dde7...)
```

Out of scope for this program (it is in `claim`, not in the learning CLI), but
recorded because the source plan's Loop 3 CLI contract requires that unknown
flags exit non-zero and name the flag. The new `bm_learn.py` must not copy this
pattern from its sibling. Logged to docs/NOT-FINALIZED.md as a new open item.

## 6. Dump redaction: what it actually does, which is less than the plan assumes

This is the most consequential finding of Loop 0.

The mechanism is real and well built. `Store.dump()` reads TEXT-affinity columns
live from `PRAGMA table_info` and passes every column NOT in `_DUMP_SAFE_COLUMNS`
through `redact_text`. A new text column is therefore covered the moment it
exists, with no allowlist edit required. That part is exactly as advertised.

But `redact_text` is a **secret scrubber, not a redactor**. Probed directly:

```
'loop0 baseline probe'                    -> 'loop0 baseline probe'
'my key is sk-abc123def456ghi789jkl012'   -> 'my key is [REDACTED]'
'AKIAIOSFODNN7EXAMPLE'                    -> '[REDACTED]'
'password=hunter2'                        -> '[REDACTED]'
'Bearer eyJhbGciOiJIUzI1NiJ9.abc.def'     -> '[REDACTED]'
'/Users/khalil.maaouni/secret/path.md'    -> '/Users/khalil.maaouni/secret/path.md'
```

Ordinary prose passes through unchanged. Absolute filesystem paths pass through
unchanged. Confirmed against a real dump: `records.evidence`, `records.objective`,
`digests.body` and `transitions.note` all appeared verbatim in default (non-raw)
dump output.

**Why this matters for correction learning.** The plan's invariant L14 says every
new text field is "redacted from diagnostic dumps," and Loop 12's threat model
item 1 is "founder writes a secret inside a correction." A learning candidate's
`raw_text` will hold a verbatim founder message. A correction such as

> never mention the Q3 revenue miss when writing to that investor

contains no secret-shaped token, so it would appear in full in any `dump` the
founder pipes into a file or an issue. The existing mechanism does not catch it,
and no test would fail.

Consequences, folded into the program:

1. Loop 1's redaction test must inject SECRET-SHAPED content to prove scrubbing,
   and separately prove PROSE handling for the new sensitive columns. A test that
   only checks `sk-` is scrubbed would pass while the real risk walks through.
2. `learning_candidates.raw_text` and `learning_evidence.excerpt` need treatment
   stronger than the scrubber: excluded from `dump` entirely, or truncated to a
   bounded excerpt behind the explicit `--show-source` flag the plan already
   requires for CLI display.
3. Loop 12's security decision "any export excludes project paths" is currently
   false for `dump`, since absolute paths survive. Restate as a known limit or
   fix it in Loop 12, but do not inherit it silently.

## 7. The current correction pipeline, reproduced

Five founder-shaped messages were fed to `scan_corrections` against an isolated
scratch vault. **Two were captured. Three were dropped.**

Captured:

```json
{"ts":"...","session_id":"loop0-sid","project":"bm-baseline",
 "text":"No, that is wrong. Always use the customer impact first in an exec update."}
{"ts":"...","session_id":"loop0-sid","project":"bm-baseline",
 "text":"I said tu, not vous, in the French copy. From now on use tu."}
```

Dropped, silently, with no record that anything was skipped:

- An ordinary question. Correct behaviour.
- A 4,000-character message ending "never do that again". Dropped by the
  `len(txt) > 400` cap at bm_telemetry.py:324. A long correction is often the
  most considered one, and it is exactly the one this loses.
- **A French correction**: `"Non, ce n est pas ce que je voulais. Utilise
  toujours le tutoiement."` Dropped because `CORRECTION_RE`
  (bm_telemetry.py:110) is English-only. The founder works in French and ships a
  French-localised product, so this is not a hypothetical gap.

Other measured properties:

- File: `$BROTHERMODE_VAULT/99-System/telemetry/corrections.jsonl`, mode `0600`.
- **Global across every project**, not per project.
- Cap of 5 candidates per session (bm_telemetry.py:322).
- Dedup on `(session_id, text)` guards repeated SessionEnd firing.
- Stored shape is four fields: `ts`, `session_id`, `project`, `text`. No trigger,
  no action, no reason, no scope, no state, no link to a work record.

### 7.1 Proof that a candidate is only a candidate

Grepping every consumer of `CORRECTIONS` across `tools/`:

- `bm_score.py:103` counts them.
- `bm_telemetry.py` counts them, dedups them, prints them in the weekly review,
  and `purge-corrections` deletes them.

Nothing reads a correction to change behaviour. `bm_sessionstart.sh` does not
inject them. `SKILL.md` does not consult them. So the source plan's premise is
confirmed by measurement rather than by assertion: **this is a cheap capture
signal with a human at the end of it, not a learning pipeline.**

## 8. What Loop 0 did NOT do

- No production behaviour changed. No test was added or altered.
- Windows behaviour was not observed. No Windows machine is available here; CI is
  the only evidence and it remains second-hand.
- The four suites were run SEQUENTIALLY and individually. They cannot safely run
  concurrently (docs/NOT-FINALIZED.md item 10) and no serial runner exists yet.
  Loop 0.5 adds one.
- The two existing skips were not investigated.
- Findings 16 to 63 of the first audit remain triaged by class, never
  individually re-proven. Unchanged by this loop.

## 9. Regression comparison points for later loops

| Measure | Value at freeze |
|---|---|
| Tests passing | 419 (2 skipped) |
| Suites | 4 |
| `SCHEMA_VERSION` | 1 |
| Store tables | 8 (plus `sqlite_sequence`) |
| Production modules under `tools/` | 6 |
| Correction candidate fields | 4 |
| Correction capture recall, 5-message probe | 2 of 5 |
| Correction languages supported | English only |
| Correction max length | 400 characters |
| Correction storage | one global vault JSONL, mode 0600 |
| Rules that change behaviour | 0 |
