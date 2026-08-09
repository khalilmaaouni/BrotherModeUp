# Independent Codex audit, 2026-08-10

Status: CURRENT. Raw output of an independent audit run by Codex (a different
model family from the one that wrote this code, which is the entire point) on
2026-08-10 against main at fcdd22e. Read-only: the auditor executed no tests,
no CLIs and no live Codex, by its own mandate, and its own gaps are named in
the WHAT I COULD NOT CHECK section at the foot.

Kept VERBATIM rather than summarised. A findings list rewritten by the party
being audited is not an independent finding any more. Its file and line
references were current at fcdd22e and will drift as the code moves; re-derive
before acting on any one of them.

First finding acted on: the fence hook's fail-open on an unparseable payload,
fixed in fcdd22e with a regression test. That defect was reached by following
this document's unattended-preflight finding, not by finding it directly.

---

FILE:LINE: [tools/bm_controller.py:4934](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_controller.py:4934), [tools/bm_controller.py:5112](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_controller.py:5112)  
The unattended preflight treats two environment strings as proof that a functioning fence exists, so Codex can pass all seven conditions while no hook will run.  
Fix: Require a runtime-specific live deny canary or categorically refuse unattended Codex exec.

SEVERITY: HIGH  
FILE:LINE: [tools/bm_runtimes.py:1015](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_runtimes.py:1015), [tools/test_bm_runtimes.py:964](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_bm_runtimes.py:964)  
The generator and tests preserve “UNVERIFIED until you rehearse it” after M19 established a measured negative, contradicting the registry and generated capability table.  
Fix: Model compatibility per event and execution surface, marking Codex exec PreToolUse as measured unsupported.

SEVERITY: MEDIUM  
FILE:LINE: [tools/bm_project.py:1355](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_project.py:1355)  
`alert list` accepts no project identifier and prints every store alert, leaking or misattributing alerts when `--allow-second` created a multi-project root.  
Fix: Store `project_id` on alerts or filter through attribution and require project scope.

## WHAT I COULD NOT CHECK

I did not execute tests, CLIs, or live Codex because they create temporary files, bytecode, databases, probes, tokens, or network traffic and would violate the read-only mandate. I could not verify newer or interactive Codex behavior beyond the repository’s recorded Codex CLI 0.146.0 measurements, nor inspect user-level installed hooks or configuration outside the repository.
tokens used
483,067
## Read-only purity

SEVERITY: HIGH  
FILE:LINE: [tools/bm_project.py:228](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_project.py:228), [tools/bm_project.py:824](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_project.py:824), [tools/bm_project.py:911](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_project.py:911)  
`status`, `next`, `forecast show`, and `alert list` use writable `Store`, whose constructor creates a filesystem probe, changes permissions/git excludes, opens WAL, migrates schemas, and creates indexes.  
Fix: Use `ReadOnlyStore` for every read-accessor command and test database, sidecar, metadata, and git-exclude byte identity.

SEVERITY: HIGH  
FILE:LINE: [tools/bm_learn.py:159](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_learn.py:159), [tools/bm_learn.py:781](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_learn.py:781), [tools/bm_learn.py:914](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_learn.py:914)  
`lookup` promises “Writes NOTHING, ever” but opens writable `Store` and can migrate the database or create/reconcile the optional FTS index.  
Fix: Add a read-store constructor and route `lookup`, `index-status`, reports, lists, and unrecorded `repeat-check` through it.

SEVERITY: MEDIUM  
FILE:LINE: [tools/bm_docs.py:3129](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_docs.py:3129), [tools/bm_docs.py:3149](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_docs.py:3149)  
`tier` says “Writes nothing” but opens the same mutating `Store`.  
Fix: Give `tier` a `ReadOnlyStore` and reserve writable construction for generation.

SEVERITY: HIGH  
FILE:LINE: [tools/bm_threads.py:871](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_threads.py:871), [tools/bm_threads.py:900](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_threads.py:900), [tools/bm_threads.py:1041](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_threads.py:1041)  
`bm_threads.py dashboard --help` ignores `--help`, runs the dashboard, and rewrites `STATE.md` through `_refresh_root_view`.  
Fix: Implement a central pre-dispatch help gate and make dashboard rendering genuinely read-only.

SEVERITY: MEDIUM  
FILE:LINE: [tools/bm_sentinel.py:390](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_sentinel.py:390), [tools/bm_sentinel.py:641](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_sentinel.py:641)  
Informational `list` and `stats` open writable `Store` and do not explicitly close it.  
Fix: Use `ReadOnlyStore` under a context manager.

SEVERITY: MEDIUM  
FILE:LINE: [tools/bm_fence_hook.py:262](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_fence_hook.py:262), [tools/bm_fence_hook.py:1076](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_fence_hook.py:1076)  
Diagnostic `whoami` calls `session-label`, which creates a secret token file and directory when absent.  
Fix: Split inspection from identity initialization and require an explicit `init-session-token` verb for creation.

SEVERITY: MEDIUM  
FILE:LINE: [tools/brothermode_cli.py:55](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/brothermode_cli.py:55), [tools/brothermode_cli.py:360](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/brothermode_cli.py:360)  
`update` is labelled read-only while spawning `git ls-remote` and making an outbound network request that may also invoke credential helpers.  
Fix: Describe it as networked, require explicit remote-check opt-in, and provide an actually offline informational path.

## Prose-only controls

SEVERITY: HIGH  
FILE:LINE: [README.md:48](/Users/khalil.maaouni/Documents/BrotherModeUp/README.md:48), [SKILL.md:120](/Users/khalil.maaouni/Documents/BrotherModeUp/SKILL.md:120)  
README claims every write is pre-claimed and conflicting writers are refused, while the actual default allows unclaimed paths and arbitrary Bash writes cross fences unrefused.  
Fix: Make strict/enforced mode the default and intercept every supported writer, or narrow the advertised guarantee.

SEVERITY: HIGH  
FILE:LINE: [README.md:68](/Users/khalil.maaouni/Documents/BrotherModeUp/README.md:68), [tools/bm_project.py:1400](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_project.py:1400)  
The delivery guarantee is prose: `deliver` checks only task state, accepts `--partial`, and verifies neither evidence recency, command success, independent reviewer identity, nor unresolved high-severity findings.  
Fix: Record write epochs and executable check receipts, then gate delivery on newer passing evidence, reviewer separation, and zero unresolved high findings.

SEVERITY: MEDIUM  
FILE:LINE: [SKILL.md:43](/Users/khalil.maaouni/Documents/BrotherModeUp/SKILL.md:43), [SKILL.md:64](/Users/khalil.maaouni/Documents/BrotherModeUp/SKILL.md:64)  
“No work” before goal/architecture/plan and the two-lane limit are prompt instructions with no tool gate.  
Fix: Persist these prerequisites and require a controller or pre-write hook to validate them before dispatch or mutation.

## Host-dependent tests

SEVERITY: MEDIUM  
FILE:LINE: [tools/test_bm_fence_hook.py:1408](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_bm_fence_hook.py:1408)  
`Cost.test_decision_is_cheap_with_a_realistic_fence` fails when host scheduling pushes real wall time above 50 ms.  
Fix: Move the ceiling to a non-blocking benchmark and unit-test deterministic operation counts.

SEVERITY: MEDIUM  
FILE:LINE: [tools/test_bm.py:5380](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_bm.py:5380)  
`test_redaction_of_a_large_input_stays_under_the_ceiling` asserts a ten-second host wall-clock budget.  
Fix: Test scaling with an injected clock or run the absolute ceiling only in an isolated benchmark job.

SEVERITY: MEDIUM  
FILE:LINE: [tools/test_bm_store.py:11536](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_bm_store.py:11536)  
`test_mask_absolute_paths_stays_linear_on_long_input` fails solely when either real-time sample exceeds two seconds.  
Fix: Replace the absolute stopwatch with deterministic complexity instrumentation.

SEVERITY: MEDIUM  
FILE:LINE: [tools/test_brothermode_cli.py:1392](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_brothermode_cli.py:1392)  
`test_a_missing_log_times_out_rather_than_raising` uses real sleeping and fails if a busy machine delays completion past five seconds.  
Fix: Inject monotonic time and sleep so timeout progression is deterministic.

## Codex compatibility

SEVERITY: CRITICAL  
FILE:LINE: [hooks/hooks.json:51](/Users/khalil.maaouni/Documents/BrotherModeUp/hooks/hooks.json:51), [docs/mistakes/M19-the-codex-fence-does-not-fire-in-exec-mode.md:27](/Users/khalil.maaouni/Documents/BrotherModeUp/docs/mistakes/M19-the-codex-fence-does-not-fire-in-exec-mode.md:27)  
Under Codex exec, one-writer refusal, strict unclaimed-write refusal, fail-closed fence mode, Bash audit, and session-cap enforcement are advisory because PreToolUse never executes; shipped lifecycle commands also use an empty `${CLAUDE_PLUGIN_ROOT}`, while telemetry cannot parse Codex transcripts.  
Fix: Ship live-tested Codex-native wiring or declare exec unsupported; only explicitly invoked store transactions and controller checks currently enforce anything.

SEVERITY: CRITICAL  
FILE:LINE: [tools/bm_controller.py:4934](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_controller.py:4934), [tools/bm_controller.py:5112](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_controller.py:5112)  
The unattended preflight treats two environment strings as proof that a functioning fence exists, so Codex can pass all seven conditions while no hook will run.  
Fix: Require a runtime-specific live deny canary or categorically refuse unattended Codex exec.

SEVERITY: HIGH  
FILE:LINE: [tools/bm_runtimes.py:1015](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_runtimes.py:1015), [tools/test_bm_runtimes.py:964](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_bm_runtimes.py:964)  
The generator and tests preserve “UNVERIFIED until you rehearse it” after M19 established a measured negative, contradicting the registry and generated capability table.  
Fix: Model compatibility per event and execution surface, marking Codex exec PreToolUse as measured unsupported.

SEVERITY: MEDIUM  
FILE:LINE: [tools/bm_project.py:1355](/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_project.py:1355)  
`alert list` accepts no project identifier and prints every store alert, leaking or misattributing alerts when `--allow-second` created a multi-project root.  
Fix: Store `project_id` on alerts or filter through attribution and require project scope.

## WHAT I COULD NOT CHECK

I did not execute tests, CLIs, or live Codex because they create temporary files, bytecode, databases, probes, tokens, or network traffic and would violate the read-only mandate. I could not verify newer or interactive Codex behavior beyond the repository’s recorded Codex CLI 0.146.0 measurements, nor inspect user-level installed hooks or configuration outside the repository.
