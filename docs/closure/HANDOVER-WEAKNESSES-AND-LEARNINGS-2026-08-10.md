# Handover: what is actually weak, and how to fix it

Status: CURRENT. Written 2026-08-10 against `main` at `1148618`, for the
session that takes BrotherMode from "works" to "first in its category".
No em or en dashes anywhere.

This is not a status report. It is the list of things that will keep going
wrong until something structural changes, each with WHY it happens and HOW to
close it. Every weakness below was hit for real in the last few days, not
imagined.

---

## PART 1: THE SEVEN STRUCTURAL WEAKNESSES

Ordered by how much damage they do, not by effort.

---

### W1. Tests that measure the MACHINE, not the code

**What happens.** A test asserts wall-clock time, a session count, a process
count, or some other fact about the computer it runs on. It then fails on a
busy laptop while the code is perfectly correct.

**Evidence this is structural, not a one-off.** It has now been found and
fixed at least six separate times: the C-11 timing flake (2026-08-04), two
earlier stopwatch tests before it, the doctor test in `b3227ed`, the
successor-liveness tests fixed today, and three more that an independent Codex
audit named on 2026-08-10 with file and line
(`test_bm_fence_hook.py` Cost at 50 ms, `test_bm.py` redaction ceiling at 10 s,
`test_bm_store.py` mask-paths at 2 s). Six instances of one shape is a design
problem, not bad luck.

**Why it keeps happening.** Writing `assert elapsed < 2.0` is the obvious way
to express "this should be fast", and it is wrong every time. The correct
expression is almost always a RATIO between two input sizes, because load
scales both measurements and cancels, while an absolute ceiling only measures
the machine.

**Why it is the worst one on this list.** It makes every other result
ambiguous. When the gate goes red, nobody can tell a real regression from a
busy machine, so people learn to re-run rather than read. A gate that trains
people to ignore it is worse than no gate, because it costs the same and
protects nothing.

**How to fix it, in order of preference.**
1. Assert the SHAPE: a ratio between two input sizes, using the MINIMUM of N
   samples per size, because noise can only add latency, never remove it.
   `tools/test_bm.py`, class `TestLoop12RedactionIsLinearInInputSize`, is the
   worked example already in the tree. Copy it.
2. Assert deterministic operation counts or complexity instrumentation.
3. Last resort: keep an absolute ceiling but SKIP with a stated reason when
   the machine is contended. Never fail.

**Make it structural, which is the actual ask.** Add a lint that fails CI when
a test file contains an absolute wall-clock assertion outside an approved
benchmark module. Until a machine refuses this pattern, a human will keep
writing it.

**Calibration is mandatory and it is the part that gets skipped.** After
converting any timing test, reinject the slow behaviour and watch the test go
RED, then restore and watch it go green. A test nobody has seen fail is not
evidence.

---

### W2. Claims that outrun the code, including in items marked CLOSED

**What happens.** A document, a README line, or a closure-register entry
asserts a guarantee the code does not provide.

**Evidence, three instances in one week.**
- C-01 is recorded CLOSED with the claim that enforced mode denies all nine
  failure conditions "because every one of them funnels through `_FailOpen` or
  the blanket catch". It denied eight. A payload the hook could not parse
  returned ALLOW even under enforcement, because that branch sits UPSTREAM of
  both handlers. Fixed 2026-08-10 in `fcdd22e`.
- `README.md:48` claims every write is pre-claimed and conflicting writers are
  refused. The shipped default allows unclaimed paths entirely.
- `docs/NOT-FINALIZED.md` item 2 says shell writes are ungated and that fixing
  it "needs a design, not a patch". That design landed on 2026-08-04.

**Why it happens.** A claim is written when the intent is formed, and the code
lands later, narrower. Nothing re-reads the claim afterwards. The closure
entry is written by the same session that did the work, at the moment it feels
finished, which is the worst possible moment for accuracy.

**How to fix it.**
1. Every guarantee sentence in a shipped document names the test that proves
   it. A guarantee with no named test is downgraded to a description.
2. Extend the existing docs drift suite to fail when a security-shaped verb
   (refuses, prevents, blocks, guarantees, enforces) appears without a test
   reference nearby. The suite already does something close for install
   commands; widen it.
3. A closure entry may not be written by the session that did the work. Cheap,
   unpopular, and it would have caught C-01.

---

### W3. Controls that verify a STRING rather than a BEHAVIOUR

**What happens.** A safety check reads a configuration value and treats its
presence as proof that a mechanism is working.

**The live instance.** `tools/bm_controller.py`, `_unattended_fence_mode`
proves the write fence is on by checking that `BM_FENCE_MODE` equals
`"enforced"`. It never checks the hook fires. Under Codex the hook never fires
at all, so an unattended run can satisfy all seven preconditions with zero
enforcement. Found by the Codex audit, 2026-08-10, still OPEN.

**Why this one deserves its own entry.** This project's first law is that a
rule in a prompt is not a control. This is the same failure one level up: a
control that checks a declaration rather than an effect. It is inside the gate
that guards unattended runs, which is the exact mechanism that produced the 8
August runaway.

**How to fix it.** Before an unattended run starts, EXERCISE the hook: send it
a payload it cannot parse and require a refusal. No refusal, no unattended run,
whatever the variable says.

**Founder decision, 2026-08-10, recorded because it went against the
recommendation.** Asked whether to refuse or warn, the founder chose warn and
allow. The argument against, made once: the same file already REFUSES an
unattended start when the fence is merely advisory, on the grounds that nobody
is awake to read a warning. So the file will answer the same question two ways,
refusing when protection is weak and permitting when it is absent.
FLIP CONDITION: if any unattended run is later found to have written across a
fence on a runtime where this probe warned, it becomes a refusal.

---

### W4. Read-only commands that write

**What happens.** A command that presents as informational performs a write.

**Evidence it recurs.** `bm_store dashboard --help` was found writing and
fixed. The Codex audit then found the SAME defect in `bm_threads.py`, plus five
more: `bm_learn lookup` (promises "Writes NOTHING, ever", opens a writable
store and can migrate the database), `bm_docs tier`, `bm_sentinel list` and
`stats`, `bm_fence_hook whoami` (creates a token file), and
`brothermode_cli update` (makes an outbound network call while labelled
read-only). Fixing instances did not stop the class.

**Why it matters more here than in most projects.** The product's entire claim
is that it is an assurance layer. An assurance layer with ambiguous side
effects of its own cannot be trusted to report on anything else.

**How to fix it, and the founder has already approved this shape.** Every
public command declares one effect class: `pure_read`, `ledger_write`,
`project_write`, `external_write`, `destructive_external_action`. Then ONE test
snapshots the working tree and hashes the store, runs every command declared
`pure_read`, and fails if anything changed. That test makes the seventh
instance impossible rather than findable.

---

### W5. Tests that enter BELOW the thing that is broken

**What happens.** A test suite calls an internal function directly, so a defect
in the entry point above it is invisible.

**The instance, and it is instructive.** Every test in
`EnforcedModeFailsClosed` calls `decide()` directly. The C-01 fail-open lives
in `cmd_hook`, which is upstream of `decide()`. Nine tests, all green, all
blind to it, for six days.

**Why it happens.** Testing the inner function is easier, faster and feels more
focused. It is also testing the part that already works.

**How to fix it.** For any behaviour a RUNTIME invokes, at least one test must
invoke it the way the runtime does: the real process, real stdin, real
environment. Slower, and it is the only kind that can see an entry-point bug.

---

### W6. Vacuous passes

**What happens.** A test passes for a reason unrelated to what it claims to
prove.

**The instance, found in passing today.**
`test_below_the_cap_a_successor_is_still_spawned` was passing because a
refusal also exits 0. It asserted success and got success, from a code path
that had refused to do the thing being tested.

**How to fix it.** Any test asserting that something HAPPENED must assert a
positive artifact of it happening: a row written, a file created, a specific
line in output. Exit code 0 is not evidence that work occurred, only that
nothing crashed.

**Sweep for it.** Grep the suites for tests whose only assertion is an exit
code or a non-exception, and give each one a positive artifact to check.

---

### W7. Records that go stale, and a fence nobody can release

**What happens.** State written by one session is read as current days later
when it is not.

**Instances.** `docs/PACKAGING.md` claims six console scripts and nine modules;
it is twelve and seventeen. `docs/NOT-FINALIZED.md` item 2, above. A branch
analysis written this morning was stale by the afternoon.

**The sharpest instance, and it is a real defect.** `README.md` is held by an
active claim owned by session `18a183a9`, which is not a `bm1-` derived label,
so per `docs/HOOKS.md` NO session can ever match it. That claim refuses every
writer permanently, not just foreign ones. An agent hit it today and correctly
refused to work around it. It still holds `README.md`, `docs/QUICKSTART.md`,
`docs/SETUP.md` and `tools/test_bm_docs.py`.

**How to fix.**
1. Release the stuck claim: `python3 tools/bm_store.py adopt
   f689425b3ff144efbaacb19d65018e5b --version 1 --session <yours>`. This
   session was refused permission to run it.
2. Then add the guard: a claim whose owner label can never be matched is an
   UNRELEASABLE fence. The store should refuse to create one, and the doctor
   should report any that exist.
3. Generate `CURRENT-LIMITS.md` from the live register rather than maintaining
   prose, so staleness becomes impossible rather than merely discouraged.

---

## PART 2: THE FIVE LEARNINGS WORTH KEEPING

---

### L1. Cross-model review finds what same-model review cannot

Codex, a different model family, audited this repository and returned twelve
findings with file and line, including two criticals. One of them led directly
to a live fail-open in a control marked CLOSED. Three separate Claude sessions
had reviewed that area and missed it.

**Act on this.** Make cross-model review a product feature, not a one-off:
route high-risk verification to a different model family by default. It is
cheap, it is available today (Codex has credits again as of 2026-08-10, which
closes register item X-01's blocker), and it demonstrably works.

### L2. A probe that cannot reach the defect measures nothing

The C-11 calibration measured 4.0x, concluded "this pattern is not quadratic",
and was wrong. Its probe text was a run of letters, which the pattern's own
lookbehind makes unreachable. No input of that shape could ever have shown the
defect. Underscores reproduced it at 15.8x immediately.

**The rule.** Before writing down "X is not there", show the instrument can
detect X when it IS there. A negative result from an instrument of unproven
sensitivity is NO-DATA, never a finding.

### L3. Absence of a record is not absence of the event

Twice this week a document asserted something had never happened when it had:
four documents said the tool had never been used for real while the founder
used it daily, and a session claimed nobody had installed via the plugin path
when what had actually been established was that no record of it existed.

**The rule.** "I found no record of X" and "X did not happen" are different
sentences. Write the first one.

### L4. The README is the installer

The founder's team installs BrotherMode by pasting the repository link into
their own AI assistant and asking it to work out the steps. So the installer is
not a script and not the plugin manifest: it is the README, interpreted by a
language model.

**Consequence.** README clarity is install RELIABILITY, not documentation
quality. An ambiguous sentence is a production defect, because different models
resolve ambiguity differently and each teammate gets whatever theirs decided.

**Nobody has ever watched this happen.** Hand a fresh agent nothing but the
repository URL and a throwaway HOME, tell it to install BrotherMode, and read
what it actually does. Three times, because one success is not a reliable path.
This is the highest-value untested thing in the product.

### L5. Testers are not builders, and the roadmap must stop conflating them

The founder's colleagues test; he alone builds. The north-star brief's Loop 10
asks for ten external BUILDERS, and that rung will stay empty. Loop 8's
first-run study is achievable with testers and should be pulled forward.

---

## PART 3: WHAT TO DO FIRST, AND WHY THAT ORDER

1. **Finish W1.** One lane is already running on the three Codex-named timing
   tests. Until the gate is trustworthy, no result after it can be believed.
2. **W4, the effect classes.** Founder-approved, mechanically checkable, and it
   closes a class rather than an instance.
3. **W7, release the stuck fence**, then fix `README.md` with the exact edit
   already drafted and waiting in this session's record.
4. **W3, the unattended preflight**, to the founder's chosen warn-and-allow
   shape, with the flip condition recorded.
5. **L4, watch a model install it.** One hour, and it tests the path every real
   user actually takes.
6. Then the fourteen branch merges, in the order in
   `docs/closure/BRANCH-DECISIONS-2026-08-10.md`.

## WHAT IS NOT ON THIS LIST, DELIBERATELY

The ten-part assurance architecture from the north-star brief. It is the right
direction and it is not the next move: five of the seven weaknesses above are
in code that architecture would keep, and shipping a new control plane on top
of tests nobody can trust would inherit every one of them.

Fix the foundation, then build the cathedral.

## UNVERIFIED

The benchmark's `reset-token` result is not trustworthy yet: its hidden test
forces the clock by replacing `time.time` globally, and a correct
implementation using `datetime` or `time.monotonic` would evade the patch and
be marked failing. Fix the test before drawing any conclusion from that row.
