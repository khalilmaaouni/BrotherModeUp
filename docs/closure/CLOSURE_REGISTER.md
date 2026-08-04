# Closure register

Status: CURRENT. Opened 2026-08-02 at `c5ceccc`. Built from
`docs/closure/BASELINE.md`. An item closes only when its acceptance test AND
its adversarial test both pass, never on a code change alone.

`machine-closable` means it can be closed with code and tests on this machine
today: no outside human, no paid credits, no calendar time.

ALL ELEVEN machine-closable items (C-01 to C-11) are CLOSED as of 2026-08-04.
The gate that covers the last four of them, run after the last edit:
`test_all: 1518 tests across 14 suites, 6 skipped, 209.6s wall. ALL GREEN`,
exit 0. Two of those closures are narrowings rather than complete fixes and
say so in their own entries: C-02 ships refusal and alerting but not
containment, and carries a deliberate fail-open when the store module cannot
be imported; C-06 leaves `bm_project_facts.py` and `scripts/` unwired on
purpose. What remains open is X-01 to X-06 below, and none of it is closable
by engineering: it needs credits, outside participants, or calendar time.
That is the honest reason a 9 out of 10 still cannot be claimed today.

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
- Status: **CLOSED 2026-08-04, as the partly it was always scoped to be.** Both
  halves landed. REFUSE: `BM_FENCE_MODE=enforced` makes `tools/bm_bash_audit.py`
  return a deny for an obvious destructive command aimed at the store or the
  fence directory, before the consent gate so a half-installed machine is still
  covered. ALERT: `.brothermode/store.sqlite3` was never a CLAIMED path, which
  is why the Bash audit never looked at it and the bypass was silent; a control
  snapshot now covers the enforcement state itself, and `_raise_breach_alert`
  announces the detection BEFORE it tries to record it, because a detection
  whose store has just been deleted was previously announced by nothing.
  `EnforcedModeRefusesStoreDestruction` in `tools/test_bm_bash_audit.py` carries
  one test per mutation form the reproduction above used (redirection, `sed -i`,
  `tee`, `python3 -c`, `git checkout`, plus `rm`, the fence directory, and
  `git clean -xfd` which names no BrotherMode path and deletes it anyway). Each
  asserts BOTH directions: refused under enforced, allowed by default. Fence
  suite 16 tests to 30.
  THREE THINGS THIS DOES NOT DO, stated here rather than left to the reader.
  (1) Full containment needs an operating-system sandbox and is explicitly out
  of scope, unchanged. (2) The matcher is LITERAL, not a shell parser: a path
  assembled at runtime, held in a variable, or sitting inside a script file the
  hook never reads is not caught. (3) A deliberate fail-open sits inside the
  fail-closed feature: when `tools/bm_store.py` cannot be imported at all, the
  project check cannot run and NOTHING is refused, so anyone who can break that
  import can disable the refusal. That was chosen because the only alternative
  refuses every Bash command in every directory on the machine, this hook being
  installed user-globally. `SECURITY.md` and `docs/KNOWN-LIMITS.md` say all
  three in those words.
  PROCESS NOTE, kept because it is the more useful record. The approved spec's
  own change 8 refused BEFORE resolving a project root, which is exactly the
  machine-wide defect `references/mistakes.md` already had a law about from the
  last time it happened. The implementing agent stopped and refused to apply it
  rather than shipping it, and the corrected change added the root check plus
  `test_the_refusal_stays_inert_outside_a_brothermode_project_even_when_enforced`
  so the defect cannot return. A written law did not prevent it; a second pair
  of eyes did.

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
- Status: **CLOSED 2026-08-04.** `TestPreWriteGate` in `tools/test_bm.py` now
  matches eight constructs instead of three (adding `os.replace`, four `shutil`
  write functions, `os.mkdir`/`os.makedirs`, `os.unlink`/`os.remove`,
  `os.chmod`) and walks all four directories the acceptance names: `tools/`,
  `scripts/`, `mcp/` and `brotherme/`. Manifest keys became repository-relative
  paths, because a bare filename stopped being unambiguous the moment a second
  directory joined the scan. `tools/write_sites.json` goes from 68 sites across
  14 files to 193 across 22, and every newly surfaced site was read line by
  line rather than accepted on the scanner's count. None writes founder or
  model text without redaction: every one is scaffolding around an
  already-reviewed write (the atomic-swap half of a temp-file-then-replace, a
  directory created ahead of a reviewed write, a temp file the tool itself
  created being deleted, a permission tightened, or a verbatim byte copy of an
  existing file), or structural config in `scripts/`.
  The adversarial test, `test_widened_scope_catches_a_smuggled_site`, plants a
  file writing only via `os.replace` inside a `scripts`-shaped directory under
  an isolated temp root and asserts the SAME comparison the real gate runs
  refuses it. It shares that comparison with the real test rather than copying
  it, so the adversarial test cannot drift into passing against a mock.
  SCOPE NOTE: the implementation spec recommended deferring `scripts/` to a
  second stage. It was not deferred, because this item's acceptance names all
  four directories and shipping three of four would have left C-04 open while
  reading as closed. The counts were also re-measured against the finished tree
  rather than transcribed from the spec, which caught one real drift:
  `bm_bash_audit.py` is 9 sites, not the spec's 8, because C-02 landed a new
  `sys.stdout.write` in `_refuse` after the spec was written.

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
- Status: **CLOSED 2026-08-04.** `pyproject.toml` declares twelve console
  scripts where it declared nine, adding `bm-project`, `bm-ledger` and
  `bm-sentinel`. The sentinel was the one the earlier spec could not have
  known about: it merged into `main` after that spec was written and carried
  the identical gap, documented as a command line in two documents and wired
  to nothing. Packaging also gained the `brotherme` package mapping and the
  `brotherme/core/schema.py` data file, without which a packaged
  `bm-project` crashed at import time with a `FileNotFoundError`, and
  `tools/bm_store.py`'s `_schema()` gained a second candidate path so it
  resolves in both the checkout layout and the flat installed layout.
  The register's own adversarial test is now executable rather than a
  description: `tools/test_bm_packaging_install.py` builds a real wheel,
  installs it into a throwaway virtualenv, and invokes every declared console
  script, including a live `bm-store` / `bm-project` / `bm-ledger` /
  `bm-sentinel` workflow. It is registered in `tools/test_all.py` and in the
  CI `suite` job. It is the only suite needing network egress, and it SKIPs
  rather than fails when pip cannot reach an index, so an offline runner
  reports a skip instead of a red build.
  DELIBERATELY STILL UNWIRED, so this is a narrowing and not a silent gap:
  `tools/bm_project_facts.py` cannot be a console script as written, because
  it reads `VERSION`, `tools/test_all.py`'s source and `scripts/install.py`'s
  source, none of which ship in a wheel. `scripts/` ships nothing, unchanged.
  `docs/PACKAGING.md` is independently stale on its own counts and is NOT
  fixed here; it is named so the next reader does not trust it.
  INCIDENT DURING VERIFICATION, recorded because the mechanism generalises: a
  probe running with `HOME` overridden to a throwaway directory still wrote one
  synthetic row into the operator's real memory vault, because `BROTHERMODE_VAULT`
  is exported ambient and takes precedence over `HOME`. The row was removed on
  the founder's decision and the test now pins every redirecting variable.
  `references/mistakes.md` carries it as a law: HOME isolation is not vault
  isolation.

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
- **X-04 Sustained dogfood.** CORRECTED 2026-08-03: the clock had started and
  nobody had written it down. The founder reports weeks of his own daily use
  plus other people using it on their own machines, installed by pointing them
  at this repository. That is real use, and this register had been recording
  the opposite. What remains missing is the MEASUREMENT rather than the usage:
  counted projects, recorded failures and rework, and a comparison against
  working without the tool. Real use does not become a graded outcome by being
  real, and this line will not claim the second from the first.
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
- Status: **CLOSED 2026-08-04.** The FLAKE was closed first: `_time()` in `tools/test_bm.py` returns the MINIMUM of five samples per size instead of one, which is the standard microbenchmark estimator because noise can only add latency, never remove it. Both timing tests share that helper, so both are corrected by one change.
  The ADVERSARIAL half is now closed too, and the route to it is the part worth keeping. This item previously read PARTLY CLOSED, because a calibration test had been written and then REMOVED: reinjecting the pre-Loop-12 unbounded key-value pattern onto `bm.SECRET_PATTERNS[8]` produced a 4.0x ratio, which is linear, and the note left behind concluded that the pattern "is not quadratic on a run of one repeated character".
  THAT CONCLUSION WAS WRONG, and the pattern was quadratic all along. The probe text was `"x " + "B" * n`, a run of LETTERS. The pattern opens with the boundary lookbehind `(?<![A-Za-z0-9])`, so inside a run of letters every offset except the first is preceded by an alphanumeric and is rejected before any backtracking can happen: two starting positions in the entire string, linear by construction, and NO input of that shape could ever have exhibited the defect. A run of UNDERSCORES clears that lookbehind at every offset while still being consumed by the `[A-Za-z0-9_]*` that follows, giving n starting positions each scanning n characters. The sibling test `test_a_run_of_underscores_does_not_blow_up_either` had been saying so in its own first sentence the whole time.
  Measured on the underscore input, minimum of five samples per size, 1000 and 4000 characters: unbounded 0.0263s and 0.4160s, a 15.8x ratio; the shipped bounded pattern 0.0023s and 0.0093s, a 4.1x ratio. The 15.8x agrees with the 15.6x this file's own older comment records, which is corroboration rather than coincidence, because that figure was measured on underscores too. Sizes are 1000 and 4000 rather than 8000 and 32000 to keep the test near 2s instead of near 130s, since quadratic cost rises fast and the ratio is what is asserted, not the absolute time.
  `test_calibrated_reinjecting_the_unbounded_pattern_reproduces_the_blowup` carries it, alongside `test_calibration_reinjection_is_reverted_afterwards` so a leaked monkeypatch fails by name rather than surfacing as an unrelated flake downstream. The calibration was shown able to FAIL, not merely observed passing: with the reinjection disabled it goes red at 4.4x with a message naming the cause, and it was restored and re-run green afterwards. The acceptance's other clause holds as well, the class passing under deliberate CPU load (load average 6.47, 4.844s).
  THE LESSON, now a law in `references/mistakes.md`: a probe that cannot reach the defect measures nothing, and its silence reads exactly like an all-clear. A negative result from an instrument of unproven sensitivity is NO-DATA, never a finding. Withdrawing the test rather than shipping a green one that proved nothing was still the right call at the time. The error was writing the conclusion down as a property of the code instead of as a limit of the probe.
