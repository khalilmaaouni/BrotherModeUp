# Closure register

Status: CURRENT. Opened 2026-08-02 at `c5ceccc`. Built from
`docs/closure/BASELINE.md`. An item closes only when its acceptance test AND
its adversarial test both pass, never on a code change alone.

`machine-closable` means it can be closed with code and tests on this machine
today: no outside human, no paid credits, no calendar time.

---

## C-01 The enforcement boundary never fails closed

- Severity: **CRITICAL** (security control bypass, protocol Laws 4 and 5)
- Metric: security and privacy
- Claim tested: that the fence hook protects one writer per file.
- Reproduction: export `c5ceccc` to a throwaway tree with its own `HOME`, create
  an active foreign claim, then drive the hook under nine failure conditions.
  All nine allow the write with exit 0.
- Root cause: every error path raises `_FailOpen`, and `BM_FENCE_STRICT` is read
  after all of them, so no code path can deny on failure. A zero-claims store
  short-circuits before strict is consulted.
- Impact: the protection the product is named for is absent in exactly the states
  where it matters, including a fresh project.
- Required change: a real fail-closed mode. Deny when the store is missing,
  corrupt, unreadable, when the payload is malformed, when identity is
  underivable, and when an internal exception is raised; make strict mode
  effective on a zero-claims store.
- Acceptance: each of the nine conditions returns a deny in fail-closed mode, and
  the existing allow behavior is unchanged in advisory mode.
- Adversarial test: the same nine conditions, plus a tenth that removes the hook
  mid-session, asserted to deny rather than allow.
- machine-closable: **yes**
- Status: **CLOSED 2026-08-03.** `BM_FENCE_MODE=enforced` added to
  `tools/bm_fence_hook.py`. Both exception handlers in `decide()` now return a
  deny in enforced mode, which covers all nine conditions at once because every
  one of them funnels through `_FailOpen` or the blanket catch. Default
  behaviour is byte-for-byte unchanged, which was the founder's decision.
  `EnforcedModeFailsClosed` in `tools/test_bm_fence_hook.py` carries nine tests,
  and each asserts BOTH directions on its condition: deny under enforced, allow
  under the default, so a later change cannot quietly make fail-closed the
  default. Fence suite 50 tests to 59, all green.

## C-02 One ungated shell command disables enforcement

- Severity: **CRITICAL** (protocol Law 5, no hidden mutation path)
- Metric: security and privacy
- Claim tested: that enforcement covers supported mutation paths.
- Reproduction: with a proven DENY in place, `rm -f .brothermode/store.sqlite3`
  through Bash, then repeat the same edit: it becomes ALLOW. Five mutation forms
  (redirection, `sed -i`, `tee`, `python3 -c`, `git checkout`) each wrote a file
  under an active foreign fence with no hook consulted, silently, no stderr.
- Root cause: enforcement state lives inside the tree that the ungated channel
  can write, and Bash is not gated.
- Impact: any agent or user with shell access can disable the boundary in one
  command, leaving no trace.
- Required change: per Gate 2, either contain shell writes or, in fail-closed
  mode, refuse unrestricted Bash and allow only a reviewed read-only set. At
  minimum, move or protect the enforcement state so a shell write cannot
  silently erase it, and make the audit hook's detection non-silent.
- Acceptance: in fail-closed mode the store cannot be removed through the
  supported shell path without a recorded refusal or a recorded alert.
- Adversarial test: the exact chained sequence above, asserted to fail.
- machine-closable: **partly** (refusal and alerting yes; OS-level sandboxing no)
- Status: OPEN

## C-03 Three documents overstate the boundary, one inverts it

- Severity: **HIGH** (protocol anti-gaming rule 5: advisory described as enforcement)
- Metric: security and privacy
- Claim tested: that documentation language matches the proven boundary.
- Reproduction: `SKILL.md:146` states the hook blocks a write outside an active
  claim; an unclaimed in-project path is allowed by default, so the sentence
  inverts the real rule. Two `HOOKS.md` sentences promise strict denies any
  uncovered in-project path, false on a zero-claims store. An in-tree design
  document with CURRENT status calls `BM_FENCE_STRICT` a fail-closed option.
- Root cause: the documents describe the intended design, not the shipped one.
- Impact: a reader trusts a boundary that is not there.
- Required change: make all three sentences exactly true, or close C-01 and C-02
  so they become true. Correcting prose alone is only acceptable where the
  capability is honestly narrowed, never as a substitute for closing C-01.
- Acceptance: every security sentence is traceable to a passing adversarial test.
- Adversarial test: a docs test that fails if a security claim names a guarantee
  no test proves.
- machine-closable: **yes**
- Status: **CLOSED 2026-08-03.** All three corrected. `SKILL.md` now says the
  hook refuses a write to a file ANOTHER active claim covers, states that an
  unclaimed path is allowed by default, names both opt-in switches, and says
  plainly that a shell write crosses a fence unrefused. `docs/HOOKS.md` gains a
  paragraph saying outright that strict mode is a no-op on a zero-claims store,
  plus an enforced-mode section. The Loop 6 design spec no longer calls
  `BM_FENCE_STRICT` a fail-closed option, and says why that was wrong.

## C-04 The write-site manifest is partial but presented as complete

- Severity: **HIGH** (Gate 1 exit criterion: every write site mapped)
- Metric: workflow and traceability
- Reproduction: the generating test matches only `open(w)`, `os.open(` and
  `.write()`; about forty-seven sites using `os.replace`, `shutil`, `mkdir`,
  `unlink`, `chmod` in the same reviewed files are absent. The scan is
  hard-scoped to `tools/`, so `scripts/` and `mcp/` are unreviewed.
- Required change: widen the scanner's construct set and its scope, then
  re-review the newly surfaced sites.
- Acceptance: the manifest names every mutation construct in `tools/`,
  `scripts/`, `mcp/` and `brotherme/`, and the test fails when a new one appears.
- Adversarial test: add an `os.replace` write in an unreviewed directory and
  assert the gate catches it.
- machine-closable: **yes**
- Status: OPEN

## C-05 Most of the suite has never run on the declared Python floor

- Severity: **HIGH** (portability; protocol anti-gaming rule 12)
- Reproduction: only three of thirteen test files execute under 3.9 in CI; the
  rest run under `3.x`, currently 3.14.6.
- Required change: run the full suite on the declared floor, or narrow the
  declared floor to what is tested.
- Acceptance: the CI matrix covers every suite on the lowest supported version.
- Adversarial test: introduce a syntax construct unavailable on the floor and
  assert CI fails.
- machine-closable: **yes**
- Status: **CLOSED 2026-08-03.** The `suite` job gains the same two-value python
  axis the `store` job already used, so all twelve real suites now run on the
  declared 3.9 floor as well as on current Python. The `gate` job stays on `3.x`
  deliberately: it runs `test_all.py`, the orchestrator, which has no test
  methods of its own, and the twelve suites it spawns are already covered on
  3.9 by the other two jobs. Verified first by running all ten affected suites
  locally under 3.9.6; every one passed, so this was a CI wiring gap, not a
  compatibility one.

## C-06 Pip-installed copies are missing most of the CLI

- Severity: **HIGH** (operational maturity)
- Reproduction: `bm_project.py` (eighteen subcommands), `bm_ledger.py` and
  `bm_project_facts.py` have no console script; `scripts/` ships nothing.
- Required change: declare the packages and entry points, or state plainly that
  the clone install is the only supported path.
- Acceptance: a pip install into a clean environment exposes every documented
  command, or the documentation stops promising them.
- Adversarial test: install into a fresh virtualenv and invoke each documented
  command.
- machine-closable: **yes**
- Status: OPEN

## C-07 The two install paths produce different hook configurations

- Severity: **MEDIUM**
- Reproduction: `hooks.json` sets timeouts and status messages for
  `SessionStart` and `SessionEnd`; `scripts/install.py` omits both.
- Required change: one generator, or a test asserting the two agree field by field.
- Acceptance: a test compares both and fails on any divergence.
- machine-closable: **yes**
- Status: **CLOSED 2026-08-03.** `scripts/install.py` now carries the same
  timeout and statusMessage as `hooks/hooks.json` on every group, and
  `TestHooksJsonAgreesWithInstaller` in `tools/test_install.py` compares them
  field by field. Proven red first: it named all eleven mismatches before the
  fix. Installer suite 70 tests to 71, all green.

## C-08 STATE.md is not byte-stable

- Severity: **MEDIUM** (protocol Law 3)
- Reproduction: the renderer embeds a fresh timestamp per render, so identical
  source state produces different bytes.
- Required change: derive the timestamp from the state being rendered, or exclude
  it from the stability contract explicitly.
- Acceptance: two renders with unchanged state are byte-identical.
- machine-closable: **yes**
- Status: **CLOSED 2026-08-03.** `render_state_md` no longer stamps a render
  time. The existing stability test had been FREEZING the clock to work around
  this, so it could never have caught it; the freeze is gone and it now runs
  live. A second test guards the property directly and earned its place: with
  the timestamp reintroduced to calibrate, the stability test still passed
  because three renders landed inside one second, and only the direct test
  failed.

## C-09 Quarantine directory permissions

- Severity: **MEDIUM**
- Reproduction: quarantine files are 0600, the directory containing them is never
  `chmod`'d, unlike `.brothermode/` at 0700.
- machine-closable: **yes**
- Status: **CLOSED 2026-08-03.** The quarantine directory now gets 0700 through
  the same `_chmod_best_effort` helper the store directory uses, asserted in
  `test_calibrated_8_corrupt_db_quarantines_and_recovers` on POSIX.

## C-10 CI push trigger names a branch that does not exist

- Severity: **MEDIUM**
- Reproduction: `tests.yml` triggers on `[main, v2]`; `v2` exists nowhere, so
  release branches get no push-triggered run.
- machine-closable: **yes**
- Status: **CLOSED 2026-08-03.** The push trigger is now `[ main, "release/**" ]`,
  so release branches get push-triggered runs instead of relying on pull
  requests alone.

## Not machine-closable, and therefore not scoreable today

These are open by definition until external evidence exists. Naming them here so
no scorecard can quietly omit them.

- **X-01 Second runtime conformance.** Codex is authenticated but out of credits;
  adding credits is a payment and permanently the founder's. Alert
  `65921a00` already records it.
- **X-02 External user study.** Needs participants who did not build this.
- **X-03 Benchmark corpus.** Thirty projects, five users, three operating
  systems, two runtimes.
- **X-04 Sustained dogfood.** Thirty days of calendar time; the clock has not
  started.
- **X-05 Ecosystem thresholds.** Twenty-five active users, five contributors,
  two maintainers able to release.
- **X-06 Fault-injection reliability.** The protocol asks for 10,000 sequences;
  zero have been run, so no reliability figure exists to report.

## C-11 A timing test flakes on one CI leg, and its own reasoning says it cannot

- Severity: **MEDIUM** (verification integrity: a flaky gate teaches people to
  re-run rather than to read)
- Metric: verification integrity
- Claim tested: that `test_quadratic_blowup_is_gone` in `tools/test_bm.py`
  cannot be moved by machine load.
- Reproduction: CI run 30818827958 on `7995a10`, job `suite (macos-latest,
  3.x)`, failed on `assertLess(large / small, 8.0)` while the same test passed
  on the three other legs of the same commit. Re-running only that leg passed
  with no code change, which is what separates a flake from a regression.
- Root cause: the test takes ONE sample per input size. Its own comment argues
  a ratio is immune to load because "both timings are taken under whatever
  load is present so contention cancels", and that holds only when the noise
  is the SAME on both samples. A single scheduling stall landing on the larger
  measurement inflates the ratio on its own, and `small` is floored at 0.001,
  so the denominator cannot grow to absorb it.
- Impact: a red release gate that is not a defect. This project's own records
  already carry two entries about stopwatch tests measuring the machine; this
  is the same family in a form that survived the last cleanup because a ratio
  looked immune.
- Required change: take several samples per size and compare the MINIMUM of
  each, which is the standard estimator for a microbenchmark because it is the
  sample least contaminated by noise. A quadratic redactor still shows roughly
  16x on minimums, so the defect-detection property is unchanged.
- Acceptance: the reinjected quadratic redactor still fails the test, and the
  test passes on a deliberately loaded machine.
- Adversarial test: reinject the quadratic redactor the existing comment
  describes and assert the test still fails.
- machine-closable: **yes**
- Status: OPEN
