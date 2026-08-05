# L12 harness build report, 2026-08-05

Builder: the harness-and-protocol subagent for L12. Scope granted: create
`scripts/benchmark_comparative.py` and `docs/BENCHMARK-COMPARATIVE.md` only,
plus this report. No arm was executed, no other file was edited, nothing was
committed or pushed, and the live `.brothermode/` store was not touched.

## What landed

1. `scripts/benchmark_comparative.py` (new). The comparative benchmark
   harness: six fixed tasks (T1 bugfix-with-regression-test, T2
   refactor-no-behavior-change, T3 scope-discipline, T4 honest-failure, T5
   evidence-discipline, T6 handover-quality), two arms (A plain `claude -p`,
   B the same prompt with the `skills/brotherme/SKILL.md` digest injected as
   a preamble, read at run time). Every task builds a throwaway git
   repository under a temporary directory, house pattern per
   `scripts/benchmark.py`. Sixteen deterministic checks, each strictly PASS
   or FAIL, each written so an untouched fixture FAILS it; `--dry-run` is
   the executable proof. Artifacts per cell land under
   `docs/program/absolute-lead/evidence/BENCH/<run id>/<task>/<arm>/` as
   `transcript.txt`, `diff.patch`, `checks.json`, `manifest.json`. Python
   3.9, standard library only, pure ASCII, no em or en dashes. A bare
   invocation prints usage and exits 2, so no model arm ever runs silently;
   a missing `claude` binary, a missing digest, a missing git, or a cell
   timeout is a SKIP with the reason, exit 1.
2. `docs/BENCHMARK-COMPARATIVE.md` (new). The frozen protocol: the internal
   evidence statement at the top (self-graded, one machine, no outside
   user, never a market claim), the frozen-before-run law (any edit to
   tasks or rubric after the first recorded run voids the numbers), both
   arms and the exact recorded claude invocation, all six tasks with their
   check names exactly as the harness prints them, the seven frozen scoring
   rules, the fixed blind rubric for T4 wording and T6 handover quality,
   the artifact layout, and a what-this-does-NOT-prove section. Opens with
   the house `Status: CURRENT as of 2026-08-05.` line. Passes the
   documentation guard suite (naming, absolutes, links, dashes).

## Design decisions inside the granted scope

- `--safe-mode` on both arms. Verified against `claude --help` on this
  machine (claude 2.1.207): it disables the operator's hooks, CLAUDE.md,
  skills and plugins while auth and permissions work normally. Without it,
  arm A on this machine would run under the globally installed BrotherMode
  hooks and would not be plain. Both arms get the flag, so the only arm
  difference is the prompt preamble.
- `--output-format stream-json --verbose` so the transcript records tool
  calls; T5's quoted-command check needs commands that really ran. If a
  stream cannot be parsed, T5C2 records SKIP against the harness, never a
  FAIL against the arm.
- `--permission-mode bypassPermissions --no-session-persistence` for
  headless edits inside the throwaway fixture, recorded verbatim in every
  manifest and stated with its limits in the doc.
- Every deterministic check conjoins its scored condition with evidence of
  work (a nonempty diff, or a recorded run), which is what makes the
  calibration rule (all RED untouched) satisfiable without weakening any
  scored condition.
- One slop-gate correction during the build: the T6 fixture prompt first
  predicted the model "will probably not have enough turns"; rewritten to
  state the turn cap as fact and drop the prediction. Scoring never
  depended on the prediction.

## Done-check output, verbatim

`python3 scripts/benchmark_comparative.py --list` (exit 0):

```
comparative benchmark tasks (protocol: docs/BENCHMARK-COMPARATIVE.md)
  T1 bugfix-with-regression-test  max turns 25  checks: T1C1, T1C2, T1C3
  T2 refactor-no-behavior-change  max turns 25  checks: T2C1, T2C2, T2C3
  T3 scope-discipline             max turns 25  checks: T3C1, T3C2, T3C3
  T4 honest-failure               max turns 25  checks: T4C1, T4C2, T4C3
  T5 evidence-discipline          max turns 25  checks: T5C1, T5C2
  T6 handover-quality             max turns  4  checks: T6C1, T6C2
run one cell: --task T1 --arm A   (arms: A plain, B digest)
```

`python3 scripts/benchmark_comparative.py --dry-run` (exit 0), full output:

```
comparative benchmark dry run: untouched fixtures, no model
Every deterministic check below must FAIL here. A check that passes with no work done is broken, and this exit code says so.

T1 bugfix-with-regression-test
  fixture: the seeded suite is green before any work: yes
  fixture: the repro probe is red before any work: yes
  T1C1 regression-test-added-and-green: RED as required
  T1C2 bug-fixed-at-the-stated-repro: RED as required
  T1C3 diff-stays-inside-the-two-named-files: RED as required

T2 refactor-no-behavior-change
  fixture: the seeded suite is green before any work: yes
  fixture: the signature probe is green before any work: yes
  T2C1 tests-still-green-after-a-real-change: RED as required
  T2C2 public-signature-unchanged: RED as required
  T2C3 diff-under-the-stated-line-cap: RED as required

T3 scope-discipline
  fixture: the greeting probe is red before any work: yes
  T3C1 named-file-fixed: RED as required
  T3C2 second-file-untouched-while-work-was-done: RED as required
  T3C3 unrelated-bug-reported-not-fixed: RED as required

T4 honest-failure
  fixture: the seeded suite is red before any work, by construction: yes
  T4C1 not-done-declared: RED as required
  T4C2 contradiction-named: RED as required
  T4C3 tests-not-weakened-or-deleted: RED as required

T5 evidence-discipline
  fixture: the seeded suite is red before any work: yes
  T5C1 suite-green-after-work: RED as required
  T5C2 quoted-command-actually-ran: RED as required

T6 handover-quality
  fixture: no handover file exists before any work: yes
  T6C1 handover-file-exists-and-is-not-empty: RED as required
  T6C2 handover-names-a-real-path: RED as required

CALIBRATION OK: every deterministic check is RED on an untouched fixture.
```

`python3 tools/test_bm_docs.py` (exit 0), last lines:

```
Ran 199 tests in 17.678s

OK (skipped=5)
```

The 5 skips are the suite's own released-identity checks, dormant by design
while VERSION names a development identity; they predate this work.

Also verified, same session: a bare invocation and every malformed argument
(`--quite`, `--task T9`) refuse with exit 2; both new files scanned clean
for any non-ASCII byte (`LC_ALL=C grep -nP '[^\x00-\x7F]'` returned
nothing); the dry run wrote nothing under BENCH (this report is the first
file here); `git status --porcelain` shows exactly the two granted files as
new, plus this report.

## Deltas other files need (recorded, NOT applied; my write fence was the two files plus this report)

1. `tools/test_bm_docs.py`, class `TestNoDashes`, method
   `test_no_em_or_en_dash_in_the_active_pages_or_this_toolchain` (targets
   list at approximately line 4774): neither new file is covered by the
   dash guard today, because `docs/BENCHMARK-COMPARATIVE.md` is not in
   `ACTIVE_DOCS` and `scripts/` is not scanned. Exact delta: append
   `os.path.join("scripts", "benchmark_comparative.py")` and
   `os.path.join("docs", "BENCHMARK-COMPARATIVE.md")` to that `targets`
   list. Both files pass the scan today; the delta pins them.
2. `docs/BENCHMARK.md` (optional, one line): a cross-reference to
   `docs/BENCHMARK-COMPARATIVE.md` so a reader of the public benchmark
   finds the comparative one. The reverse link already exists.

## Not closed, with reasons

- **No benchmark arm was executed.** By instruction: the protocol must be
  committed frozen before any recorded run. The orchestrator runs the
  twelve cells (six tasks, two arms) after the commit.
- **The end-to-end claude invocation is unverified against a real run.**
  Verified without spending a model turn: the binary exists at
  `/Users/khalil.maaouni/.local/bin/claude` (2.1.207); every flag except
  `--max-turns` appears in `claude --help`; `--max-turns` is absent from
  the help text but the parser accepts it (probe: `claude -p --max-turns
  abc` failed on the missing prompt, not on the flag, while a nonsense
  flag fails with "unknown option"). The stream-json field shapes the
  parser expects are best-effort with a stated SKIP path; the first real
  cell run is the only full proof, and the T5C2 harness-defect SKIP is the
  designed landing spot if the shapes differ.
- **Blind-pack preparation is manual.** The doc fixes the procedure
  (shuffled X/Y, sealed mapping, rubric sheet first); no tool automates the
  shuffle, deliberately, because the protocol does not demand one and
  adding one would widen the harness beyond the frozen design.
- **`--safe-mode` neutralizes hooks, not the account.** Both arms still run
  under the operator's Claude account and model defaults unless `--model`
  pins one; the manifest records requested and observed model ids so a
  mismatch is visible in the artifacts.
