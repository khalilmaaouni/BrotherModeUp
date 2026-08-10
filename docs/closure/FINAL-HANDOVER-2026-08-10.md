# BrotherMode: the complete handover

Status: CURRENT. Written 2026-08-10 for the session that takes this to a public
first release. No em or en dashes anywhere.

This is the whole picture: what went wrong, why it went wrong, what was done
about it, and what to do next. It is written to be read by somebody who was not
here, and it does not flatter the project.

---

# PART 1: THE MISTAKES, AND WHAT EACH ONE TAUGHT

Every entry is a real incident with a date. They are grouped by CLASS, because
the classes are the useful unit: fixing an instance never stopped the class
recurring, and that is the single most important observation in this document.

---

## CLASS A: Tests that measure the MACHINE instead of the code

**How many times it happened: at least seven.**

| Date | Instance | How it surfaced |
|---|---|---|
| 2026-07-31 | Two bare stopwatch tests, "assertLess(elapsed, 2.0)" | Failed on a machine running five sessions while the code was unchanged |
| 2026-08-04 | C-11 timing flake, `test_quadratic_blowup_is_gone` | Failed one CI leg of eleven, passed on an unchanged re-run |
| 2026-08-08 | Doctor test asserting a fact about its host, fixed in `b3227ed` | Found during a review |
| 2026-08-10 | Successor-liveness tests, failing when 3 sessions are live | Found by an independent reviewer, proven A/B/A |
| 2026-08-10 | Fence cost test, 50 ms ceiling | Found by an independent Codex audit |
| 2026-08-10 | Redaction ceiling, 10 s | Same audit |
| 2026-08-10 | Path masking, 2 s | Same audit |

**Why it keeps happening.** `assert elapsed < 2.0` is the obvious way to write
"this should be fast" and it is wrong every time. It measures the computer.

**What it costs.** It makes every other result ambiguous. When the gate is red
nobody can tell a regression from a busy laptop, so people re-run instead of
reading. A gate that trains people to ignore it protects nothing.

**The fix that works.** Assert the SHAPE: a ratio between two input sizes, using
the MINIMUM of N samples per size, because noise only ever adds latency. Or
assert deterministic operation counts, which cannot be moved by load at all.

**The fix that would stop the class.** A lint that fails CI when a test file
contains an absolute wall-clock assertion outside an approved benchmark module.
NOT YET BUILT. Until a machine refuses the pattern, humans keep writing it.

---

## CLASS B: A probe that cannot reach the defect

**2026-08-04, C-11.** A calibration test reinjected a quadratic pattern,
measured 4.0x where a quadratic gives 16x, and concluded the pattern was not
quadratic. It was. The probe text was a run of LETTERS, and the pattern opens
with `(?<![A-Za-z0-9])`, so every offset inside a letter run is rejected before
any backtracking can happen: two starting positions in the whole string, linear
by construction. No input of that shape could ever have shown the defect.
Underscores reproduced it at 15.8x immediately.

**2026-08-10, independently.** A different agent, converting a different test,
found the SAME trap: the redaction test's filler was letters and digits, so its
quadratic was also unreachable. Two separate discoveries of one pattern is how
you know it is a class.

**The law, now written in `references/mistakes.md`.** Before writing down "X is
not there", show the instrument can detect X when it IS there. A negative result
from an instrument of unproven sensitivity is NO-DATA, never a finding.

**Why it is dangerous beyond tests.** The first session did not just fail to
find the defect. It wrote its conclusion down as a property of the CODE rather
than a limit of the PROBE, and that sentence would have been read as settled by
everyone after.

---

## CLASS C: Claims that outrun the code

| Date | Claim | Reality |
|---|---|---|
| 2026-08-03 | C-01 CLOSED: enforced mode denies all nine failure conditions | It denied eight. A payload the hook could not parse returned ALLOW, because that branch is UPSTREAM of both handlers. Live for six days. Fixed 2026-08-10 |
| ongoing | `README.md:48`: every write is pre-claimed, conflicting writers refused | The shipped default allows unclaimed paths entirely |
| ongoing | `NOT-FINALIZED.md` item 2: shell writes ungated, "needs a design not a patch" | That design landed 2026-08-04 |
| ongoing | `SECURITY.md`: makes no network calls | True until the benchmark landed, which invokes an AI agent. Scoped honestly 2026-08-10 |
| ongoing | `PACKAGING.md`: six console scripts, nine modules | Twelve and seventeen |

**Why it happens.** A claim is written when the intent forms; the code lands
later and narrower; nothing re-reads the claim. Closure entries are written by
the session that did the work, at the moment it feels finished, which is the
worst possible moment for accuracy.

**What to build.** Every guarantee sentence names the test that proves it. Widen
the existing docs drift suite to fail when a security verb (refuses, prevents,
blocks, guarantees, enforces) appears with no test reference nearby. And a
closure entry should not be written by the session that did the work.

---

## CLASS D: Controls that verify a STRING rather than a BEHAVIOUR

**2026-08-10, still open.** `_unattended_fence_mode` in `bm_controller.py`
proves the write fence is on by checking `BM_FENCE_MODE == "enforced"`. It never
checks the hook fires. Under Codex the hook never fires at all, so an unattended
run passes all seven safety preconditions with zero enforcement.

**Why this one is the sharpest in the document.** The project's founding law is
that a rule in a prompt is not a control. This is the same failure one level up,
inside the gate that guards unattended runs, which is the exact mechanism that
produced the 8 August runaway.

**Founder decision, 2026-08-10, against recommendation.** Warn and allow rather
than refuse. Recorded with its flip condition: if any unattended run is later
found to have written across a fence where this probe warned, it becomes a
refusal.

---

## CLASS E: The 8 August runaway

The largest single incident. Measured, not recalled: forty sessions, 6,331
turns, roughly 6.4M output tokens and 1.69B cache-read tokens in ten hours, peak
fifteen concurrent against a declared cap of nine. Three sessions died holding
work.

**Root cause in one sentence.** The stop conditions existed in prose and not in
code.

**What was done.** A relay brake that refuses a session's own next spawn on
depth, deadline or blown ceiling. A machine-wide cap of 3, enforced by a hook.
Two pre-authorising bypass rules deleted, and the watchdog and five relay
prompts moved to a disarmed folder with the reason on top.

**What is still true.** Class D above means the preflight guarding unattended
runs can still be satisfied without enforcement. The brake and cap bound the
blast radius; they do not close that hole.

---

## CLASS F: Read-only commands that write

`bm_store dashboard --help` was found writing and fixed. An independent Codex
audit then found the SAME defect in `bm_threads.py`, plus five more: `bm_learn
lookup` (promises "Writes NOTHING, ever", opens a writable store and can migrate
the database), `bm_docs tier`, `bm_sentinel list` and `stats`, `bm_fence_hook
whoami` (creates a token file), `brothermode_cli update` (outbound network while
labelled read-only).

**Why it matters here more than elsewhere.** The product claims to be an
assurance layer. An assurance layer with ambiguous side effects of its own
cannot be trusted to report on anything.

**The fix, founder-approved, NOT YET BUILT.** Every public command declares one
effect class. One test snapshots the tree, hashes the store, runs every
`pure_read` command and fails if anything changed.

---

## CLASS G: Tests that enter below the break, and vacuous passes

**Entering below.** Every test in `EnforcedModeFailsClosed` calls `decide()`
directly. The C-01 fail-open lives in `cmd_hook`, upstream of it. Nine tests,
all green, all blind, for six days. **Rule:** for any behaviour a RUNTIME
invokes, at least one test must invoke it the way the runtime does: real
process, real stdin, real environment.

**Vacuous passes.** `test_below_the_cap_a_successor_is_still_spawned` passed
because a refusal also exits 0. It asserted success and got success, from a code
path that had refused to do the thing. **Rule:** a test asserting that something
HAPPENED must assert a positive artifact of it happening. Exit code 0 means
nothing crashed, not that work occurred.

---

## CLASS H: Process failures, recorded because they cost real time

- **A CI result belongs to ONE COMMIT.** A handover quoted a green run beside a
  newer SHA while that commit's run was still in progress. The green belonged to
  a commit two earlier. It turned out true, and it was unearned when written.
- **A GUI button label is a SAMPLE, not a property.** A screenshot said Fetch; by
  the time the click landed it was Push. The push was wanted, which is the only
  reason this is a near-miss.
- **HOME isolation is not vault isolation.** A probe with HOME overridden still
  wrote a synthetic row into the real vault, because `BROTHERMODE_VAULT` is
  exported ambient and wins.
- **Build output in the repo broke the integrity checker.** A packaging test
  built in tree, leaving artifacts that made `verify-install.sh` report 26 EXTRA
  files, a state its own output calls the shape of a planted backdoor. Both
  files were gitignored, so `git status` looked clean the whole time.
- **`.gitignore` hides a file from version control, not from a checksum manifest
  that walks the filesystem.** That is why the two worst invisible defects of
  2026-08-04 were both gitignored files.
- **An approved spec violated a law already written down.** C-02's spec would
  have refused shell commands in every directory on the machine. The law existed
  in `references/mistakes.md` from the previous occurrence. The written law did
  not prevent it; an agent reading the code did, by refusing to apply its own
  spec.
- **A fence that can never be released.** `README.md` is held by a claim owned by
  a session id that is not a `bm1-` derived label, so no session can ever match
  it. It refuses every writer permanently. Still open.

---

# PART 2: WHAT WENT RIGHT, AND WHY IT IS THE PRODUCT

## The product refused its own author, twice

The fence hook blocked this session's edit to `bm_controller.py`, correctly,
naming the owner, the files and the three ways to release it. Separately, the
docs drift suite caught a stale install command and a pinned test count in a
document I was writing.

That is the thing worth selling. Not that it works, but that it stopped somebody
who had every reason and every permission to proceed.

## Cross-model review found what same-model review could not

Codex, a different model family, audited the repository and returned twelve
findings with file and line, including two criticals. One led directly to the
C-01 fail-open that three Claude sessions had reviewed and missed.

**This should become a product feature.** Route high-risk verification to a
different model family by default. It is cheap, available today, and
demonstrably works.

## Agents refusing to proceed

Two agents this session stopped rather than guessing: one refused to apply an
approved spec that would have refused shell commands machine-wide, one refused
to work around a fence and an unrelated red gate. Both were right. Briefs that
make refusing safe and expected produce better work than briefs that demand
completion.

---

# PART 3: WHERE THINGS ACTUALLY STAND

## Verified today, by command

- Fence suite 104 tests, store suite 1025, main suite 280, CLI suite 84: all OK
- The outcome benchmark exists, is calibrated red-then-green, and has run
- `verify-install.sh` PASSES with nothing missing or extra
- Codex is alive again, which closes register item X-01's payment blocker

## Open, honestly

- **Fifteen remote branches**, fourteen holding unmerged work. Analysis with
  containment proofs in `BRANCH-DECISIONS-2026-08-10.md`
- **The unattended preflight** (Class D) still checks a string
- **Effect classes** (Class F) approved and not built
- **The README overclaim** documented in KNOWN-LIMITS but not fixed in README,
  because of the unreleasable fence
- **`v3.0.0` tagged, main 44 commits past it.** Version now correctly reads a
  development identity
- **No measurement of whether the product helps.** Real daily use exists. Counted
  projects, failure rates and a comparison against working without it do not

---

# PART 4: WHAT TO DO NEXT, IN ORDER, AND WHY THAT ORDER

1. **Release the stuck fence, then fix the README claim.** One command, then the
   edit already drafted. It is the most-read file in the repository and it
   currently promises more than ships.
2. **Effect classes (Class F).** Founder-approved, mechanically checkable,
   closes a class rather than an instance.
3. **The unattended preflight (Class D)**, to the chosen warn-and-allow shape.
4. **The wall-clock lint (Class A).** The only thing that stops the most
   frequent defect in this document's history from recurring an eighth time.
5. **Watch a model install it.** The team installs by handing the repository
   link to their own assistant, so the README IS the installer and its clarity
   is install reliability. Nobody has ever watched this happen. One hour.
6. **Merge the fourteen branches** in the recorded order, gating each.
7. **Grow the benchmark to ten tasks** and publish the result labelled as what
   it is.

## What is deliberately NOT next

The ten-part assurance architecture from the north-star brief. It is the right
direction and the wrong move today: five of the eight weakness classes above
live in code that architecture would keep, and a new control plane built on
tests nobody can trust inherits every one of them.

Fix the foundation, then build the cathedral.

---

# PART 5: THE POSITIONING, EARNED RATHER THAN CLAIMED

The honest category claim, today:

> BrotherMode is the only agent layer that has published the defects its own
> checks found in itself.

That is defensible right now, because this document exists. What is NOT
defensible yet, and should not be claimed until measured: that it makes work
better, faster or more reliable than working without it. Nobody has counted.

The gap between those two sentences is the entire remaining product risk, and it
closes with measurement, not with more features.

## UNVERIFIED

The benchmark's `reset-token` result is not trustworthy: its hidden test forces
the clock by replacing `time.time` globally, and a correct implementation using
`datetime` or `time.monotonic` would evade the patch and be marked failing. Fix
the test before drawing any conclusion from that row.
