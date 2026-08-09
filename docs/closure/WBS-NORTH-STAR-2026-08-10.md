# Work breakdown: north star to shipped, 2026-08-10

Status: CURRENT. Written against `main` at `6210ddb`, 15 remote branches.
Source: `BROTHERMODE_NORTH_STAR_ADVERSARIAL_BENCHMARK_AND_FABLE_FINALIZATION_BRIEF.md`
(founder, 2026-08-10), reconciled against what the repository actually contains
today. No em or en dashes.

**North star, from the brief:** from intent to a verified, review-ready
deliverable with bounded autonomy, independent proof, and recoverable state.

**Read this first.** Every line below is either MEASURED (a command was run and
its output is quoted) or PROPOSED (from the brief, not yet verified against the
code). They are labelled. Nothing here claims a capability ships.

---

## S0. STATE CHANGE FOUND TODAY, and it reopens a lane the register calls closed

**MEASURED: Codex is alive.** `codex exec "reply with exactly: CODEX_ALIVE"`
returned `CODEX_ALIVE` at exit 0, 10,093 tokens.

The closure register records X-01 (second runtime conformance) as blocked
because "Codex is authenticated but out of credits; adding credits is a payment
and permanently the founder's". That blocker is GONE. Every Codex-dependent
item in the brief is now executable, including the cross-runtime capability
probe (brief 3.4), cross-model verification (brief 5.x, Loop 5 option B), and
the second-runtime leg of the benchmark.

ACTION: correct X-01 in `docs/closure/CLOSURE_REGISTER.md` to say the credits
blocker cleared on 2026-08-10, and that what remains is the CONFORMANCE WORK,
not the payment.

---

## S1. THE BENCHMARK IS THE P0, AND IT IS UNRUN

The founder states it directly: the comparative harness is on CI and the
benchmark itself is completely UNRUN. That matches the brief's own verdict that
the external-proof row is the important one and is empty.

**MEASURED:** the only benchmark-shaped code in the tree is
`tools/bm_hookbench.py` and its test. That is a HOOK microbenchmark. It is NOT
the comparative outcome benchmark the brief specifies. UNVERIFIED whether any
CI job runs a comparative harness; the founder says one exists, and this
document does not contradict him, it flags that the tree does not obviously
show it and the next session must locate it before building a second one.

### W1.1 Locate or build the comparative harness
- Find the CI job the founder refers to. If it exists, name the workflow file
  and what it runs. If it does not, that is itself the finding.
- Deliverable: one command that runs N tasks across M systems and emits
  machine-comparable output.
- Done-check: the corpus runs TWICE from identical snapshots and produces
  mechanically comparable output. That is the brief's own Loop 1 acceptance
  gate and it is a good one, because it catches a harness that is not
  deterministic before any result is trusted.

### W1.2 The corpus
- Brief specifies minimum 30 tasks, recommended comparison against vanilla
  Claude Code, Superpowers, Spec Kit, GSD, Cline.
- SIZING, range with confidence: building a 30-task corpus that two people
  would score the same way is 3 to 6 working days, MEDIUM confidence. The
  variance is in task definition, not in code.
- RECOMMENDATION: start with the brief's option A (10 tasks, BrotherMode versus
  vanilla Claude Code). It is explicitly called "fast but weak", and weak
  evidence that exists beats strong evidence that does not. Publish it AS
  option A, labelled, and grow it.

### W1.3 VADR definition
- Brief section 1.1 gives fifteen conditions for a work item to count.
- Deliverable: `docs/NORTH-STAR.md` carrying VADR, the counter-metrics table,
  and the go/no-go targets.
- WARNING, and this is the trap: VADR is computable ONLY if the fifteen
  conditions are each mechanically checkable. Several are not today (condition
  10, "the independent verifier reviewed from a fresh context", has no
  machine record). Write the definition WITH a column naming what checks each
  condition, and mark the ones that are currently human-asserted. A metric
  whose inputs are opinions is a story.

---

## S2. THE FIFTEEN BRANCHES, which block "one main branch"

MEASURED today: 15 remote branches, 14 besides main. Full analysis with
containment proofs is in `docs/closure/BRANCH-DECISIONS-2026-08-10.md`.

Corrected merge order, after the reviewer refuted the original premise:

| # | Work | Branch | Note |
|---|---|---|---|
| 1 | Session-cap test purity | none yet | See S3. Blocks trusting every gate below it. |
| 2 | Continuity, `brothermode continue` | `phase-c/continuity` | Conflicts in `write_sites.json`; resolve by RE-RUNNING the scanner, never by picking a side. |
| 3 | Bash-audit alert path | `claude/laughing-engelbart-4ba095`, `claude/charming-goldwasser-6d8423`, `fix/system-projects-excluded-from-project-counts` | One says a first alert breaks `verify` FOREVER. |
| 4 | Read-only purity | `claude/practical-kowalevski-471524` | `dashboard --help` performed a write. Brief 3.8 makes this a whole class. |
| 5 | Design amendment | `claude/reverent-bhaskara-2c96c9` | Must land BEFORE or WITH the Gantt work it authorises. |
| 6 | Progress view | `phase-5/progress-view` + `feature/progress-page-template` | The cockpit. Brief 3.14 wants it generated from state, not hand-kept. |
| 7 | Install truth | `phase-3/install-truth`, `claude/jovial-tereshkova-830231` | Overlapping; check which supersedes. |
| 8 | Findings ledger | `phase-6/findings-ledger` | |

Each merge closes with a full gate on the MERGED tree before the next opens.

---

## S3. THE GATE POISONS ITSELF. FIX THIS BEFORE TRUSTING ANY RESULT.

**MEASURED by an independent Opus reviewer, A/B/A at one commit, clean tree:**

```
RUN A default        FAILED (failures=6, errors=5)
RUN B CAP=99         OK          (Ran 82 tests)
RUN C default        FAILED (failures=6, errors=5)
```

The liveness tests in `tools/test_brothermode_cli.py` assert a fact about the
HOST: they fail when 3 Claude sessions are live against the machine-wide cap of
3. So the gate manufactures its own failure whenever the founder's team is
working, and "ALL GREEN" is unreachable at exactly the times it matters.

This is the brief's section 3.9 concern (meta-observability) and it is the same
class as the doctor test fixed in `b3227ed` and the C-11 timing flake.

FIX, same shape as the one already applied: the tests state their precondition
and SKIP when the cap is saturated, naming why. Alternatively the gate reserves
cap headroom. Either way the failure must distinguish a code defect from a busy
machine.

Done-check: run the suite with 3 sessions live and get a SKIP with a stated
reason, not a failure.

---

## S4. THE VERSION IDENTITY IS AMBIGUOUS RIGHT NOW

**MEASURED:** `v3.0.0` is tagged at `d4856997`. `main` is 44 commits past it.
`VERSION` reads `3.0.0`, `release_tag` reports `v3.0.0`, `is_development` is
False.

So an immutable tag and a moving branch both claim to be `3.0.0` while holding
materially different code. That is the exact condition that withdrew
`v2.0.0-rc.1`, live in the repository today.

FIX: bump `VERSION` to a development identity so main stops claiming the
released name. Five minutes. Then the next tag is honest.

---

## S5. ISSUES FROM THE BRIEF NOT YET IN ANY BACKLOG

These are PROPOSED. None is verified against the code yet, and several may
already be partly built. Each needs a probe before it becomes a task.

| ID | Brief | Item | First probe |
|---|---|---|---|
| N1 | 3.1, Loop 2 | One Work Governor owning budget, leases, concurrency, retries, convergence rounds | What do the relay brake and session cap already cover? |
| N2 | 3.2, Loop 4 | Work item durable, session disposable: leases, heartbeats, expiry, orphan detector | `phase-c/continuity` may be most of this |
| N3 | 3.3, Loop 3 | Isolation first, file fence second: worktree per writing worker | Does any code create worktrees today? |
| N4 | 3.4, Loop 3 | Runtime capability probe with a signed receipt, and three modes: verified auto, guided, unsupported | `tools/bm_runtimes.py` exists; how far does it go? |
| N5 | 3.5, Loop 5 | Acceptance contract frozen before implementation, classified by testability | Nothing obvious in tree |
| N6 | 3.6, Loop 5 | Independent verifier with an information boundary, not a persona | Partially practised by hand today |
| N7 | 3.7, Loop 6 | Convergence engine that appends tasks rather than reporting gaps | Not in tree |
| N8 | 3.8 | Command effect classes: pure_read, ledger_write, project_write, external_write, destructive | Directly testable, high value, small |
| N9 | 3.9 | Live hook self-inspection with marker probes, refuse verified auto if a hook cannot be shown alive | High value given the hook projection defect already found |
| N10 | 3.10 | Reconciler that detects stranded state BEFORE a human goes looking | Brief gives 12 detection cases |
| N11 | 3.11, Loop 9 | Memory retrieval evaluated on a labelled corpus before any new backend | Explicitly "do not add vector search because competitors have memory" |
| N12 | 3.12, Loop 7 | Preview lane: boot in worktree, E2E, screenshots, console errors, teardown | |
| N13 | 3.13, Loop 8 | First-run simplicity: one path, start work verify deliver | |
| N14 | 3.14 | Cockpit generated from ledger events, not a decorative Gantt | Ties to S2 item 6 |
| N15 | 3.15 | Split three audiences: current user truth, engineering truth, historical evidence. Generate `CURRENT-LIMITS.md` | Cheap, high comprehension value |

**N8 and N9 are the two I would take first** of this set. Both are small, both
are mechanically checkable, and both close defect classes this repository has
already been bitten by once. That is the best evidence a fix is worth its cost.

---

## S6. WHAT IS NOT DOABLE BY WRITING CODE

Unchanged from the register, and the brief agrees: ten external builders, thirty
externally attempted work items, eight of ten first-run completions without
help. These need people and calendar time. They are the reason a public 2.0-
grade claim cannot be made from this chair, whatever the code does.

---

## SEQUENCING, and the reason for it

1. **S3, the self-poisoning gate.** Nothing below can be trusted while a red
   reading is ambiguous.
2. **S4, version identity.** Five minutes, closes a live honesty hole.
3. **S2, the branch merges** in the stated order, gating each.
4. **N8 and N9**, the two small mechanical wins.
5. **S1, the benchmark**, starting at option A rather than waiting for 30 tasks.
6. Everything else, sized properly, after the above.

## HONEST SIZING

Items 1 to 4 above: 1 to 2 attended days, MEDIUM-HIGH confidence, assuming the
merges do not surface new conflicts beyond the one already found.

Item 5 at option A scale: 2 to 4 days, MEDIUM confidence.

The full brief including Loop 10: WEEKS, LOW confidence on any date, because it
depends on recruiting outside builders.

UNVERIFIED throughout this document: every S5 row. They come from the brief and
have not been checked against the code. Probing them is the first task of
whoever takes S5, and any of them may turn out already built.
