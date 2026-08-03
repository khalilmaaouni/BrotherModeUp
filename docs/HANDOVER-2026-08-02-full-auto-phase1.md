# Handover: Full-Auto Phase 1, the Memory Sentinel

Status: CURRENT. Written 2026-08-02 at the close of an overnight autonomous
session. Audience: the founder, and whoever picks this up next.

Branch `feature/full-auto-and-codex-modes`, head **f56448c**, working tree
clean, 18 commits ahead of `origin/release/2.0-final` (4030ca9), **not pushed**.

The one command that proves the state, run after the last edit:

```bash
cd ~/BrotherModeUp-worktrees/full-auto && python3 tools/test_all.py
```
```
test_all: 1480 tests across 13 suites, 6 skipped, 161.3s wall. ALL GREEN
```

---

## 1. What this is, in plain language

BrotherMode now has a memory that behaves like a colleague rather than a
filing cabinet. It writes down what was decided, what has already been tried
and failed, and what is still required. Then, at a handful of specific moments,
it decides whether to say one short thing or to keep quiet. Keeping quiet is
the default and is recorded as a decision with its reason, not as an absence.

The problem it solves is the one Meta measured in July 2026: an agent reads
something important, and later stops acting on it, even though the information
is still sitting right there in front of it. They call it behavioural state
decay. Our own failure records are full of it: a brief written against code
that was 24 commits stale, a team of agents spending a full round on a sandbox
three commits behind, engine runs retried after they had already failed twice.

The research is arXiv 2607.08716. The numbers that justified copying it: a
weaker model went from 37.6% to 45.9% on one benchmark and 55.0% to 61.8% on
another. The findings that shaped our design more than the headline: showing
the agent everything it remembered was WORSE than choosing one thing (61.5 vs
64.3), removing the option to stay silent was also worse (63.5 vs 64.3), and an
uncalibrated version made its worker actively worse. Knowing when not to speak
is the whole value.

---

## 2. Tasks DONE

### 2.1 Research and design

- Read the Meta paper directly. The link supplied contained only the title, so
  the source used was arXiv, cross-checked against independent reporting of the
  headline figure.
- Mined this project's own failure records and grouped them into six families,
  then mapped which the paper's approach actually covers (families 1 and 2, and
  part of 3) and which are covered by machinery we already had.
- Wrote the founder-facing proposal covering both requested modes.
  `docs/proposals/2026-08-02-full-auto-and-codex-execution-modes.md`
- Wrote the implementable Phase 1 spec, which became the single source of truth
  for three implementers who never saw each other's work.
  `docs/superpowers/specs/2026-08-02-memory-sentinel-phase1-design.md`
- Wrote the Phase 2 design (autonomy contract, circuit breaker, kill switch),
  deliberately NOT implemented. `docs/superpowers/specs/2026-08-02-full-auto-phase2-design.md`

### 2.2 Built and shipped

| What | Where | Size |
|---|---|---|
| Store schema 12 to 13, four tables, twelve methods | `tools/bm_store.py` | +566 |
| The sentinel: selector plus command line | `tools/bm_sentinel.py` | +792 (new) |
| Its test suite | `tools/test_bm_sentinel.py` | +1475 (new) |
| Suite registration, local and CI | `tools/test_all.py`, `.github/workflows/tests.yml` | +12 |
| Packaging, write-site review, manifest | `pyproject.toml`, `tools/write_sites.json`, `CHECKSUMS.sha256` | +26 |
| Doc fact correction | `docs/KNOWN-LIMITS.md` | schema pin 12 to 13 |

Totals: **14 files, 3703 insertions, 14 deletions, 18 commits.**

The four tables: **knowledge** (requirements, constraints, verified facts),
**procedural** (what was tried and what happened), **status** (the watcher's
private view, never shown to the working agent), and **interventions** (every
decision it made, including every silence, which is the calibration record).

The five moments it wakes: at a phase boundary, before a risky action, right
after a failure, every fifteen tool calls, and on resume, which our own records
show is the worst moment for forgetting.

### 2.3 Verified by hand, not only by tests

Seven commands driven against a real store, output recorded in
`docs/evidence/2026-08-02-memory-sentinel-first-real-run.md`. The case it was
built for works: asked about a failure it had seen before, it surfaced the exact
prior attempt and the diagnosis, instead of letting the work repeat it.

### 2.4 Adversarially reviewed

Fourteen agents. Five read-only lenses (security, correctness, migration, spec
conformance) plus a mutation lens with its own worktree, then refuters at high
effort whose only job was to kill each finding. 1.46M tokens, 57 minutes.

**30 findings, 0 refuted.**

The mutation lens earned the whole run. The suite was green on first
integration, which was either excellent or vacuous, and it was partly vacuous.

---

## 3. Decisions made, and why

| Decision | Chosen | Why |
|---|---|---|
| Autonomy level | Reversible-everything inside a signed scope | Founder ratified. Five floors stay with the founder permanently: credentials, payments, sign-in clicks, permanent deletes and production state, publishing. |
| Sentinel cost | Trigger points, silence-biased | Founder ratified over the paper-faithful every-step version. Roughly a tenth of the cost, and it covers the moments our records say we actually fail. |
| Selection logic | Deterministic rules, no model call | The project's own discipline is to try the mechanical check first and record which one answered. Whether a model-scored selector earns its place is a Phase 4 question the calibration ledger will settle. |
| Base branch | Cut from `origin/release/2.0-final`, not `main` | `main` is 32 commits behind. Cutting from it would have reproduced a failure already in the records. |
| Parallel writers | Three isolated worktrees, one file each | The fence hook correctly refuses cross-session writes, so a fleet in one tree would have been blocked on every write. Probed BEFORE dispatch. |
| Secrets at rest | Left as-is, deliberately | Sentinel text sits in the database in clear. So does the existing projects table, proven by probe. Redact-on-read is the house pattern; changing only the sentinel would import a rule from the wrong context. |
| Phase 2 timing | Specified, not built | It moves the schema again. Two migrations authored against one file at once is the exact collision the fence exists to prevent. |
| Push | Not pushed | Founder's explicit choice at close. |

Two spec amendments were forced by implementers who refused to comply with a
spec that was wrong, which is the behaviour the system is supposed to produce:

- **Amendment 1**: `superseded_by` existed for only one of two tables. The
  implementer stopped and reported instead of inventing a column.
- **Amendment 2**: "three lines, never more" was written as formatting and is
  actually a security property.
- **Amendment 3**: the recorded reason for silence could be false (see 5.7).

---

## 4. What is LEFT to do

### 4.1 Blocked on the founder, nothing else

1. **OpenAI credits.** `codex exec` returns `ERROR: Your workspace is out of
   credits`, reproduced twice, while `codex doctor` reports `auth is
   configured`. So it is credits, not sign-in. Adding credits is a payment and
   permanently founder-only. Recorded as alert
   `65921a009abf4ea19a9c562e0719dd7f [high]`, requires-human. Once added, the
   Codex proof reruns in under five minutes:
   ```bash
   codex exec -C ~/BrotherModeUp-worktrees/codex-probe -s workspace-write --skip-git-repo-check "Create probe_result.txt containing exactly CODEX-PROBE-OK"
   ```
2. **Consent setup**, one command, interactive:
   ```bash
   python3 ~/.claude/skills/brothermode/scripts/setup.py
   ```
3. **The push**, through GitHub Desktop per the standing rule.

### 4.2 Ready to build, nothing blocking

- **Phase 2**: autonomy contract, question policy, circuit breakers, kill
  switch. Fully specified. Schema 13 to 14, additive, with `_migrate_12_to_13`
  as the worked template. **1 to 4 hours, 20k to 60k tokens, medium
  confidence.** Assumes the migration follows the pattern Phase 1 just proved.
- **Phase 3**: Codex execution pipeline. Blocked on credits. 2 to 6 hours once
  unblocked, low confidence until the first real packet returns.
- **Phase 4**: calibration. Needs real runs. The first review is due after ten
  recorded interventions have been judged useful or noise.

### 4.3 Wiring that does not exist yet

Nothing calls the sentinel automatically. No hook invokes it, so today it is
founder-invoked only. The five trigger points are defined and implemented as a
function; connecting them to real session events is Phase 3 work.

### 4.4 Housekeeping left deliberately undone

- Three ephemeral fence claims are still open in the branch's own store
  (`sentinel-store`, `sentinel-module`, `sentinel-tests`). Their work is landed
  and merged; the claims were never closed with an evidence block. A fresh
  session should adopt or complete them rather than re-claim the same paths.
- Six extra worktrees exist under `~/BrotherModeUp-worktrees/` plus one stale
  registration inside an ephemeral scratchpad that will need
  `git worktree prune`. Nothing was deleted, per the standing keep-everything
  rule.
- The three `fleet/sentinel-*` branches are merged but have no remote.

---

## 5. Errors and problems: fix or avoid

Ten defects were found and closed. **Every fix was proven by putting the defect
back and watching the test fail**, then restoring it. Six of the ten were in
work that had already been called green.

### 5.1 A memory could forge fake records in an agent's context (SECURITY)

The reminder block is injected into a working agent's context by design, and it
was built by pasting stored text in raw. Memories are written by agents that
read web pages, files and command output, so a memory containing a line break
could invent extra lines inside a block the reading agent has every reason to
trust.

Fixed once, then found INCOMPLETE by the review: the same raw text also reached
the `list` command. Reproduced there: one stored memory printed as two lines,
the second a flawless fake record with an invented id and `kind=requirement`.

**Avoid in future:** when a fix covers one output path, grep for every other
path that prints the same data before calling it closed. The project's own
write-site gate caught this, for the eighth time in its history.

### 5.2 One project could read another project's memories (SECURITY, untested)

Removing the project filter from any of five read methods left the suite fully
green. Nothing proved isolation at all. The shipped code was correct; the gap
was that no test stood behind it.

**Avoid in future:** any per-tenant filter needs a test that writes under two
tenants and asserts the second sees nothing. Calibrate it by removing the filter
in a way that keeps the query valid, or the test fails for the wrong reason.

### 5.3 A typo'd project name silently damaged the store

Writing against a project that does not exist returned success. Every sentinel
write also files an attribution record, so the store's own health check then
reported `1 problem(s) found: attribution event ... references missing project`.

**The worst part:** the existing tests passed for exactly the same reason the
bug existed. They used a project that had never been created, so they were
exercising the broken path and calling it correct.

**Avoid in future:** when a test fixture skips a setup step that real use
requires, the tests are validating the bug. Make fixtures reflect real use.

### 5.4 Six of eight commands were never run by any test

Including the entire path where the sentinel actually surfaces a memory. Only
the silent path had ever been exercised.

**Avoid in future:** count the commands your suite actually invokes. One grep.

### 5.5 The one-reminder rule was proven on one of five paths

Four paths could each have returned two reminders with the suite green.

### 5.6 The cooldown was tested on one of two memory types

Disabling it for the memory type that records failures failed exactly one test,
the one just written, and nothing else noticed.

### 5.7 The ledger recorded a FALSE reason for its own silence

When the only relevant memory was on cooldown but an unrelated one was not, the
round fell through to a branch that found nothing and filed it as "nothing
matched". That reason is the only evidence the calibration step ever sees, so
the record would have argued for loosening the matcher when the cooldown was
responsible. The decision was right; the explanation was a lie.

**Avoid in future:** in any system that learns from its own record, a wrong
reason is a worse defect than a wrong outcome, because it teaches.

### 5.8 A verdict could be silently erased

`judge <id> unjudged` returned success and rewound a judgement, though the
command's own help text offers only `useful` or `noise`.

### 5.9 A ledger event could vanish entirely

On one failure path the command returned before writing its record, so the
sentinel could wake, choose a memory, render it, and leave no trace. Now
recorded as a silence naming the cause. **That branch is labelled UNREACHABLE
in the code**, because the update matches on id alone and still succeeds on a
retired row. It is fixed, and it is honestly marked as untested rather than
left looking covered.

### 5.10 Two stale facts broke three suites

`docs/KNOWN-LIMITS.md` still named the old schema, and the checksum manifest
was not regenerated for the new files, which made the installer's own health
check report six mismatched files.

**Avoid in future:** `checksums.sh` manifests git-TRACKED files, so the order is
always `git add` first, then generate, then commit. Getting this backwards
produced a manifest short by two entries, caught on the next run.

---

## 6. Mistakes in the process itself, not the code

These cost time and trust rather than correctness, and they are the ones most
likely to repeat.

### 6.1 Four wait loops that waited for themselves (the expensive one)

Waiting for the test suite, the loop used `pgrep -f "tools/test_all.py"`. That
searches the full command line of every process, and the waiting shell's own
command line contains that text. So it matched itself and waited forever. Four
of them ran while zero test suites did, and the finished ALL GREEN verdict sat
unread in a log for tens of minutes. The founder had to ask "Why are you stuck?"

**Fix:** match the interpreter (`pgrep -f "Python tools/test_all.py"`), use the
bracket trick (`"[t]ools/..."`), or better, do not poll for a process at all:
wait on the PID you started, or on the artifact the job produces.

### 6.2 Two more mis-measurements, same family

- Reading an exit code through a pipe reported the pipe's status, not the
  tool's, which briefly looked like a bug that was not there.
- Reading git state while a backgrounded commit chain was still in flight
  reported the commit as missing when it had landed.

**The pattern across all three:** the work was fine and the INSTRUMENT was
wrong, and each wrong reading looked more confident than the right one. When a
wait outlasts the job it waits for, suspect the wait.

### 6.3 My own test passed with the thing it tested deleted

An index test stayed green with every index removed, because SQLite quietly
creates one for the primary key. It was passing for the wrong reason. Caught by
the calibration step, not by review.

### 6.4 A test that was wrong about correct code

An attribution test failed because the store returned
`[WITHHELD: 10 chars of founder text]`. That is redact-on-read working as
designed. The test was wrong, not the code, and that behaviour now has its own
assertion so nobody relearns it.

### 6.5 A reviewer that was wrong, and was not followed

One refuter flagged a line as unsafe raw text. Three lines above it, every field
is already scrubbed. The claim held on neither the reviewed tree nor the current
one, and no action was taken on it.

---

## 7. Recommendation: how to integrate into the main build

**Do not merge to `main` directly.** `main` is 32 commits behind
`origin/release/2.0-final`, and this work is cut from the release branch.
Merging into `main` would either conflict or silently revert release work.

The recommended sequence:

1. **Review the branch first.** It is 18 commits and 3703 lines, most of it
   tests and specs. Start with the spec, then the evidence walkthrough, then
   the sentinel module.
2. **Push the branch through GitHub Desktop** (standing rule), open a pull
   request against `release/2.0-final`, NOT against `main`.
3. **Let CI run.** The suite is registered in both the local gate and the
   workflow file; test_all.py enforces that pairing, so a suite present in one
   and missing from the other fails the build.
4. **Merge into `release/2.0-final`**, where it joins the release-closure
   program already in flight. It reaches `main` when that release does.
5. **Re-run `verify-install` and `doctor` after merging**, because the checksum
   manifest is regenerated per commit and any conflict resolution invalidates
   it. Regenerate with `git add` first, then `scripts/checksums.sh`.

**Sequencing against the release-closure program:** that program's Loop 8 is
founder-gated and its tag is refused on evidence. This work moves the store
schema from 12 to 13, so anyone still running the old release cannot read a
store this branch has touched. `docs/KNOWN-LIMITS.md` already states this. If
the release tag is imminent, consider landing this AFTER the tag rather than
before, so the tagged release and the live store stay compatible for the three
outside installs Loop 8 needs.

**Do not ship Full-Auto as a feature yet.** Phase 1 is the memory. The autonomy
contract, the circuit breaker and the kill switch are Phase 2, and nothing calls
the sentinel automatically until Phase 3. Describing this as "Full-Auto mode" to
a user today would overclaim by two phases.

---

## 8. What is UNVERIFIED, stated rather than implied

- Whether the sentinel's reminders are the ones a working agent actually wanted
  is **NO-DATA**, and stays so until real runs are judged useful or noise. The
  deterministic rules firing correctly says nothing about whether they are the
  right rules.
- Its three thresholds (cooldown of 5, token overlap of 2, field cap of 600) are
  first guesses, measured against nothing.
- The unreachable branch in section 5.9 is fixed but untested, and labelled so.
- No hook wiring exists, so nothing has exercised the sentinel inside a real
  agent loop.
- The humanizer pass was never run over the founder-facing proposal.
- The Codex claims rest on one machine, one evening: the CLI version, the
  headless flags, and the credit wall. Nothing beyond that was reachable.

---

## 9. Quick reference

| Thing | Value |
|---|---|
| Branch | `feature/full-auto-and-codex-modes` |
| Head | `f56448c` |
| Base | `origin/release/2.0-final` (4030ca9) |
| Worktree | `~/BrotherModeUp-worktrees/full-auto` |
| Gate | `python3 tools/test_all.py` → 1480 tests, ALL GREEN |
| Sentinel suite | `python3 tools/test_bm_sentinel.py` → 87 tests |
| Pre-session backup | `~/BrotherMode-backups/brothermode-install-pre-upgrade-20260802.tar.gz` |
| Session log | Kay Vault, `10-Projects/brothermode/Sessions/2026-08-02-full-auto-and-codex-overnight.md` |
| New failure record | Kay Vault, `40-Failures/pgrep-wait-loop-matches-itself.md` |
| Open alert | `65921a009abf4ea19a9c562e0719dd7f` (OpenAI credits, needs a person) |
