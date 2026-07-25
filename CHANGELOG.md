# Changelog

## 2026-07-26: one work record for threads and fences

BrotherMode was keeping two separate records of the same fact. Threads lived in
`thread-mode.json`. Single-writer fences lived as prose inside `STATE.md`. Both
answered the question "who owns this file right now", and nothing stopped them
from answering it differently.

This release makes them one object. A thread and a fence are now the same
record, and `lifetime` (persistent or ephemeral) is the only thing that tells
them apart.

The practical effect: because a record's declared files are a real list instead
of a sentence, an overlap between two claims is now **computed and refused by
name**. Before, the registry could only be read by a human who happened to
check. That was the single largest hole in the single-writer law, and closing
it is the point of this release.

---

## What existed before

Everything below already worked and still works. This release did not remove
any of it.

### The law

- `SKILL.md`: 16 numbered sections covering classification, role assignment,
  the delegation ladder, token budgets, fences, research doctrine, circuit
  breakers, self-improvement loops, context hygiene, honesty, founder gates,
  memory, a known-mistakes ledger, the founder model, and scoring.
- `DIGEST.md`: a short compression of the law, injected at session start so the
  rules survive a context loss.
- `RUBRIC.md`: the frozen scoring rubric the weekly review grades against.
- `STATE.template.md`: the per-project state file, copied into your own repos.

### The tools

- `bm_telemetry.py`: session outcomes, the scorecard, felt-outcome ratings,
  review marks, session-start nags, stop warnings, registry and fence linting,
  write-ahead intent, the pre-compaction resume brief, the compaction hint, the
  update check, team handoff export, correction purging, prediction audit,
  speed stats, and deduplication.
- `bm_threads.py`: persistent feature threads with a chief orchestrator.
  Commands `recommend`, `on`, `start`, `checkpoint`, `send`, `dashboard`,
  `off`, `adopt`. Nothing ever flips mode automatically, the active-thread cap
  is enforced, and switching off is lossless.
- `bm_score.py`: the nine rubric metrics, with a `--strict` mode for CI.
- `bm_autosave.sh`: snapshots the whole tree, including untracked files, into a
  private local git ref before every context compaction. Never pushes, and
  excludes secret-shaped files.
- `bm_sessionstart.sh`: injects the active-laws digest at session start.
- `WEEKLY-REVIEW.md`: the weekly scoring and amendment ritual.

### The safety properties

- No network calls, no analytics, no account, no server.
- Redaction of secret-shaped text before it reaches disk.
- Owner-only permissions on the files that carry your words.
- Founder gates: credentials are never typed, destructive actions are confirmed.

### Test coverage at that point

12 tests.

---

## What was added

### A new module: `tools/bm_registry.py`

The single owner of the work record and of the three operations that are
genuinely hard to get right.

| Function | What it does |
|---|---|
| `claim` | Registers work. Refuses when declared files overlap another active record, and names the record it collided with |
| `paths_overlap` | Computes overlap across exact paths, nested directories, globs, and absolute versus relative forms of the same file |
| `decide` | Records a decision under a topic tag and raises a clash when another live record already decided that topic |
| `set_digest` | Keeps an always-current handover, so nothing depends on a thread still being alive |
| `absorb` | Drains every digest into your project `STATE.md`, then parks records rather than deleting them |
| `close` | Releases a record and its file claim |
| `render` | Regenerates the human-readable view of the registry |
| `unguarded_count` | Reports when a record is guarding fewer paths than it declared |

The record itself carries: an id, a lifetime, an owner, an objective, a real
file list, an effort tier, a lease with a time to live, a state, a done-check,
an evidence block, tagged decisions, a digest, attributed spend, and a schema
version so a later change can migrate rather than break.

### A pre-write redaction gate

`tools/write_sites.json` plus a test that inventories every write site in
`tools/`. When a write site is added or removed, the test fails and a human has
to decide whether the new one needs redaction.

Be clear about what this is: a **review-forcing inventory, not proof**. It
cannot see inside a call graph. Its value is that it makes a new write site
impossible to add silently.

### Spend attribution

`bm_telemetry.py attribute` adds a session's output tokens to a specific
record, so a token budget becomes measured rather than advisory. Cross-process
locking is proven: forty concurrent attributions produce exactly the expected
total with no lost updates.

### Documentation

- `docs/BrotherMode-One-Page.pdf`: a single designed sheet covering purpose,
  target user, philosophy, all 16 laws, features, and how to use it well.
- `docs/one-pager.src.html`: the source that generates it, so the sheet can be
  regenerated and audited instead of trusted as an opaque binary.
- The design spec and implementation plan for this release, under
  `docs/superpowers/`.

---

## What changed in existing tools

- `bm_threads.py` keeps exactly the same eight commands. Nothing new appears on
  the surface. Underneath, claim, decide, absorb, and render are delegated to
  the registry instead of reimplemented, and its duplicate copy of the
  redaction fallback is gone.
- `bm_telemetry.py` gained the `attribute` subcommand. Three code paths that
  wrote text to disk without redaction were fixed. Rating and review files are
  now owner-only.
- `SECURITY.md` had two claims that had stopped being true and are now
  corrected: the registry writes inside your project directory as well as your
  vault, and the audit line count is now checked by a test so it cannot rot
  again unnoticed.

---

## Fixed

Three Critical defects, each found by adversarial review, reproduced before the
fix and again after it.

1. **Two writers could be granted the same file.** Overlap detection did not
   match an absolute path against a relative one, so the same file written two
   different ways looked like two different files.
2. **A corrupt path entry silently destroyed a handover.** One malformed value
   made the drain throw. The digest never reached `STATE.md`, it failed
   quietly, and it failed identically on every retry.
3. **Thread adoption wrote text to disk unredacted.** Adopting a stalled thread
   copied its notes into your project `STATE.md` with no redaction, and the
   autosave then committed that file into a git ref.

Also fixed: `off` reported success when a handover had actually failed; `adopt`
never closed its registry record, so digests duplicated and file claims were
never released; a race at the thread cap could leave an invisible orphan
record; the redactor masked only the first line of a private key and let the
key body through; and note files were world-readable.

---

## Known limits

Stated here rather than left for you to discover.

- The pre-write gate cannot see non-Python files, `pathlib.write_text`,
  `json.dump(fh)`, `print(file=fh)`, or a read-one-file-then-append-to-another
  shape. It stops the problem growing. It does not retire what already exists.
- Clash detection matches topic tags. Two records making incompatible decisions
  under different topic names will not be caught.
- Overlap detection still under-blocks on symlinks and on unicode paths that
  differ only by normalization form.
- `off` drains every active record regardless of lifetime. Correct today,
  because threads are the only producer. A test fails the moment that stops
  being true.
- `bm_threads.py` grew from 470 to 540 lines. The design intended it to shrink,
  because logic moved out to the registry. The defensive guards and honest
  error reporting added back more than the move removed.
- **None of this has run on a real project yet.** Every claim here rests on
  tests, adversarial review, and simulated lifecycles.

A review on 2026-08-08 decides whether ephemeral fences migrate into the
registry, the migration is deferred with a stated reason, or the design is
reverted for not having moved the signals it named.

---

## Verifying this release yourself

```bash
python3 tools/test_bm.py
```

101 tests, up from 12.

Then watch the central behavior work, in a throwaway directory:

```bash
python3 tools/bm_threads.py on
python3 tools/bm_threads.py start pay "wire the webhook" --files api/pay.py
python3 tools/bm_threads.py start pay2 "second writer" --files api/pay.py
```

The second claim is refused by name and creates nothing at all.

Then confirm secrets do not reach disk:

```bash
python3 tools/bm_threads.py checkpoint pay --decision "use key AKIAIOSFODNN7EXAMPLE" --topic auth
grep -r "AKIAIOSFODNN7EXAMPLE" threads/
```

The grep finds nothing. The registry holds `[REDACTED]` in its place.
