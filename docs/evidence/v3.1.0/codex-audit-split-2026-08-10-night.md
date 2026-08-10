# Codex cross-family audit, split per file, 2026-08-10 night

Status: CURRENT as evidence; findings are triaged in R4-TRIAGE-2026-08-11.md
and dispositions live there, never here. The em dashes below are Codex's own
output, kept verbatim because a findings list rewritten by the party being
audited is not an independent finding.

Commit audited: 134839c. Auditor: codex-cli 0.146.0, sandbox read-only, one invocation per file,
20 minute ceiling each. Output below each marker is VERBATIM from Codex;
a timeout or crash is recorded as NO-DATA for that file only.

---

## tools/bm_controller.py (exit 0, started 2026-08-10T23:56:34)

1. **CRITICAL — `tools/bm_controller.py:5084`** — The function says it “closes” the audited runtime-wiring gap, yet lines 5113–5126 correctly admit it cannot observe whether the runtime invokes or obeys the hook. On a documented Codex-exec path where PreToolUse never runs, the synthetic subprocess returns `None` (“PROVEN”), `_refuse_unless_unattended_ready` treats the condition as satisfied at line 5455, and a real write is not refused. The disclaimer is honest, but the “closes that gap” wording and pass semantics are not.

2. **HIGH — `tools/bm_controller.py:5181`** — “PROVEN” requires only `hookSpecificOutput.permissionDecision == "deny"`. It ignores the subprocess return code and does not validate `hookEventName == "PreToolUse"` or the complete runtime-consumable response shape. A nonzero process returning partial deny-shaped JSON therefore passes the canary even though a runtime may reject that hook result and allow the real write. Conversely, a nonzero process with empty stdout is mislabeled at line 5187 as a “real, demonstrated defect” rather than an inability to run and read the hook, contradicting the promised distinction between outcomes 2 and 3.

3. **HIGH — `tools/bm_controller.py:5095`** — The canary proves only that one handcrafted `Edit` payload against one relative claimed path produces deny-shaped JSON. Lines 5114–5126 and the refusal help generalize this to “the hook binary refuses a foreign write when invoked” without preserving that tool-shape limitation. A real foreign write delivered through a different path—such as an ordinary non-`apply_patch` Bash write, which the hook allows even when invoked—can proceed after this canary reports “PROVEN.”

---

## tools/bm_effects.py (exit 0, started 2026-08-11T00:00:53)

1. **HIGH — six `pure_read` entries open a writable store.** [`tools/bm_effects.py:128`](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_effects.py:128), [`:178`](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_effects.py:178), [`:253`](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_effects.py:253), [`:447`](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_effects.py:447) — `bm_project status`, `next`, and `forecast show` call `_store()` at [`bm_project.py:834`](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_project.py:834), [`:921`](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_project.py:921), and [`:1200`](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_project.py:1200); `bm_learn lookup` reaches it at [`bm_learn.py:781`](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_learn.py:781); `bm_packs stakes` at [`bm_packs.py:1086`](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_packs.py:1086); and `brothermode next` delegates to the impure project command. `Store.__init__` may modify git excludes, enable WAL, and migrate schema at [`bm_store.py:6442`](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_store.py:6442) and [`:6481`](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_store.py:6481). These are `ledger_write` until they use `ReadOnlyStore`.

2. **HIGH — `bm_fence_hook hook` can create a token file despite being `pure_read`.** [`tools/bm_effects.py:421`](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_effects.py:421) — a valid write-hook payload with active claims calls `session_label()` at [`bm_fence_hook.py:913`](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_fence_hook.py:913), which creates and writes the token at [`:308`](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_fence_hook.py:308) and [`:318`](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_fence_hook.py:318). This should match the `ledger_write` classification of `session-label`.

3. **HIGH — `brothermode doctor` is `external_write`, not `pure_read`.** [`tools/bm_effects.py:448`](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_effects.py:448) — it delegates to `scripts/doctor.py`, whose checks spawn subprocesses at [`scripts/doctor.py:267`](/Users/khalil.maaouni/Documents/BrotherModeUp/scripts/doctor.py:267) and can create a temporary project and file at [`:279`](/Users/khalil.maaouni/Documents/BrotherModeUp/scripts/doctor.py:279). The registry explicitly defines any subprocess spawn as `external_write`.

4. **HIGH — controller commands that execute checks are underclassified as `ledger_write`.** [`tools/bm_effects.py:308`](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_effects.py:308) — `start`, `step`, and `record-result` can run the subprocess-backed checker at [`bm_controller.py:307`](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_controller.py:307) through [`:1248`](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_controller.py:1248). Additionally, unattended `start`/`step` runs a real fence-canary subprocess at [`:5068`](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_controller.py:5068). Their maximum effect is `external_write`.

5. **HIGH — `brothermode recover` is `external_write`, not `project_write`.** [`tools/bm_effects.py:454`](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_effects.py:454) — it delegates to autosave recovery at [`brothermode_cli.py:291`](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/brothermode_cli.py:291), which invokes Git via subprocess and, when a snapshot exists, creates a temporary worktree at [`bm_autosave.py:1821`](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_autosave.py:1821).

6. **MEDIUM — multiple `ledger_write` commands also generate project files.** [`tools/bm_effects.py:157`](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_effects.py:157), [`:402`](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_effects.py:402) — `bm_threads off/start/checkpoint/decide/send/park/resume/complete/adopt` write `STATE.md`, inbox, digest, or outbox files; examples are [`bm_threads.py:748`](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_threads.py:748), [`:821`](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_threads.py:821), and [`:888`](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_threads.py:888). Likewise, `bm_store claim/park/resume/complete/adopt/checkpoint/decide/handover-ack` regenerate `STATE.md`, including [`bm_store.py:17922`](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_store.py:17922) and [`:18040`](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_store.py:18040). Under the registry’s own definition, these have `project_write` effects.

7. **LOW — `bm_view url` is conservatively overclassified as `project_write`.** [`tools/bm_effects.py:342`](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_effects.py:342) — without `--set` it uses `ReadOnlyStore`; with `--set` it only records a view row at [`bm_view.py:1259`](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_view.py:1259). It generates no file, so its maximum effect is `ledger_write`.

---

## tools/test_bm_effects.py (exit 0, started 2026-08-11T00:08:24)

1. **High — Behind-schema commands often exit before opening the store.** [tools/test_bm_effects.py:609](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_bm_effects.py:609) uses `command.split()` instead of `_argv_for()`. Consequently `bm_learn lookup`, `bm_packs stakes`, `bm_project status/next/forecast show`, and `brothermode_cli next` lack required arguments and exit at usage validation. Because `check=False` is used and the return code is ignored, unchanged database bytes count as success. Their correctly parameterized executions occur only in `TestPurity` against an already-current store, where migration is invisible. Reintroducing writable `Store` in these commands would therefore not fail either test.

2. **High — The reachability argument map is incomplete.** [tools/test_bm_effects.py:404](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_bm_effects.py:404) provides no arguments for `bm_autonomy`’s `gate-check/show/status`, `bm_controller status`, `bm_lead decisions/status`, or the wrapped `brothermode_cli status`. Each validates a required project identifier before opening `_read_store()`. Both purity tests therefore exercise only their usage exits, and [tools/test_bm_effects.py:440](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_bm_effects.py:440) likewise ignores those nonzero results.

3. **High — The hook’s store-reading path is unreachable.** The regular runner supplies empty stdin at [tools/test_bm_effects.py:369](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_bm_effects.py:369), while the behind-store test explicitly supplies `DEVNULL` at [tools/test_bm_effects.py:611](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_bm_effects.py:611). `bm_fence_hook hook` consequently returns on “stdin was empty” before `decide()` reaches `active_claims()` and its store constructor. A regression from `ReadOnlyStore` to writable `Store` there cannot fail these tests.

4. **Medium — The schema reset accumulates instead of restoring “one behind.”** The fixture first decrements the schema at [tools/test_bm_effects.py:565](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_bm_effects.py:565), then `put_it_behind()` decrements it again before every command at [tools/test_bm_effects.py:588](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_bm_effects.py:588). With the current 33 pure commands, the first command sees schema 16—not 17—and command 17 onward sees zero or negative, unsupported versions unless an earlier offender migrated it. Later reachable regressions therefore exercise quarantine/error handling rather than migration; they may abort at the database read instead of reaching the offender assertion, making coverage order-dependent.

---

## tools/bm_lint_walltime.py (exit 0, started 2026-08-11T00:14:40)

1. **HIGH — `tools/bm_lint_walltime.py:109`** — Timer recognition requires the exact spelling `time.time()`, `time.monotonic()`, or `time.perf_counter()`. Common aliases and string-based lookup evade it: `import time as clock`, `from time import monotonic`, `timer = time.time`, and `getattr(time, "time")()` all pass clean. Code hidden in `eval`/`exec` strings is likewise invisible.

2. **HIGH — `tools/bm_lint_walltime.py:125`, `tools/bm_lint_walltime.py:131`, `tools/bm_lint_walltime.py:165`** — A single layer of indirection defeats every other part of the rule. Examples that pass clean include `LIMIT = 5.0; assert elapsed < LIMIT`, `observed = elapsed; assert observed < 5.0`, `assert (elapsed + 0) < 5.0`, chained comparisons such as `assert 0 <= elapsed < 5.0`, and `check = self.assertLess; check(elapsed, 5.0)`. Annotated assignments are also missed because only plain `ast.Assign` is collected at line 211.

3. **MEDIUM — `tools/bm_lint_walltime.py:109`** — Deterministic fake-clock tests are wrongly flagged. For example, a test using `mock.patch("time.time", side_effect=[100.0, 102.0])` and then asserting `time.time() - started < 5.0` measures no real wall clock but is reported. Any local deterministic object bound to the name `time` with a `time`, `monotonic`, or `perf_counter` method produces the same false positive because bindings are not resolved.

4. **MEDIUM — `tools/bm_lint_walltime.py:309`** — Read and parse failures can yield a clean exit. `opened` is incremented before reading, and exceptions are printed then ignored at lines 314–324. If every discovered file is unreadable or unparsable, `opened > 0`, `violations` remains empty, and `main()` returns 0—contradicting the documented refusal behavior.
