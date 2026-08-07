# Hook performance evidence (FENCE V7, v3 gap-closure)

Status: CURRENT. Written by the hook-performance-engineer fence
(WAVE-B-BRIEFS.md, "FENCE V7"). No em or en dashes anywhere in this file.

Headline, stated before the detail so it cannot be missed: **no change was
made to hooks/hooks.json.** This fence's mission asked for at least a 40
percent median reduction on the Bash and Stop chains. The actual, measured,
honestly-arrived-at number is that no safe reduction was applicable within
this fence's ownership, and the best achievable reduction this file could
quantify (as a projection, not an applied change) is roughly 10 to 14
percent, well short of the target. The reasons, and the exact tests that
block a larger change, are below, verified mechanically by
`tools/test_bm_hookperf.py::TestBlockersAreReal` on every run rather than
asserted as prose that can go stale.

## Method

Two measurement instruments, deliberately different in what they can see:

- **`tools/bm_hookbench.py`** (pre-existing, not owned or modified by this
  fence): measures each hook program IN PROCESS via `runpy.run_path`,
  because `tools/test_bm.py` bans `import subprocess` in shipping modules
  under `tools/`. It cannot fork a real process, so it reports every number
  as a measured LOWER BOUND and explicitly cannot measure bare interpreter
  startup or the SessionStart shell script at all. Its own page is
  `docs/PERFORMANCE.md`, last generated 2026-08-07 and untouched by this
  fence.
- **`tools/test_bm_hookperf.py`** (new, this fence): a TEST file, which
  `tools/test_bm.py`'s subprocess ban exempts by name
  (`test_no_network_claim_is_mechanically_true`: "the test files themselves
  may import subprocess to drive the CLI they are testing"). It spawns the
  REAL `sh`/`python3` processes `hooks/hooks.json` wires, through the same
  `shell=True` real-process pattern `tools/test_bm_consent.py` already uses
  to drive every wired command, timed with a monotonic clock around the
  real fork and exec.

Both run inside `bm_hookbench.py`'s own `Sandbox()`: a throwaway HOME,
vault, project, store and one active fence claim, built and torn down per
measurement run, validated to make the fence do real work (refuse a foreign
session, allow the owner) before a single timing is taken. Neither touches
this machine's real store, vault or home.

Repetitions: **10 counted, after 1 discarded as warmup**, per action, per
run. The warmup exists because the first call compiles and imports; a real
install pays that once, not per call. Every figure below is a median with
its spread beside it, never a single sample, produced by
`tools/test_bm_hookperf.py --measure --reps 10`.

## The machine

| Fact | Value |
|---|---|
| Platform | `macOS-26.5.2-arm64-arm-64bit` |
| Architecture | `arm64` |
| Logical CPUs | 8 |
| Interpreter | CPython 3.9.6 |
| Claude Code | 2.1.223 (Claude Code) |
| Load average when this run started | 3.82, 3.40, 3.35 |
| Measured | 2026-08-08 |

Bare interpreter startup (`python3 -c pass`, real subprocess, the fork,
exec and CPython bootstrap only, no BrotherMode code): median **14.83 ms**
(min 14.09, p90 15.15, max 16.41, 10 samples). This is
`bm_hookbench.py`'s own "Bare interpreter startup per hook process" NOT
MEASURED entry, filled in with a real number for the first time.

## Current per-event process fan-out, read from hooks/hooks.json

The mission's first requirement, done before any change was even
considered: count the processes each hook event spawns, from the manifest,
on this machine.

| Event | Matcher | Command strings | Real processes per invocation |
|---|---|---|---|
| SessionStart | any | 1 | 1 (the `sh` wrapper; see below for what runs inside it) |
| SessionEnd | any | 1 | 1 |
| Stop | any | 1 | **10**: outer `sh` + `cat` (stdin capture) + 4x(`printf` \| `python3`) |
| PreCompact | any | 1 | **6**: outer `sh` + `cat` + 2x(`printf` \| `python3`) |
| PreToolUse | `Edit\|Write\|MultiEdit\|NotebookEdit\|Bash` | 1 | 1 |
| PreToolUse | `Bash` | 1 | 1 (fires ALONGSIDE the group above on a Bash call: 2 processes total for PreToolUse on Bash) |
| PostToolUse | `Bash` | 1 | 1 |

The Stop and PreCompact counts are derived by
`tools/test_bm_hookperf.py::count_real_processes`, a small text-based
counter restricted to the two shapes this manifest actually uses (a bare
command, or `sh -c 'stmt; stmt; ...'` where each statement is either
`p=$(cat)` or a `printf ... | python3 ...` pipe: every pipeline stage forks
in a POSIX shell even when the left side, `printf`, is a builtin). Pinned
by `TestManifestFanoutStatic.test_the_stop_chain_is_counted_as_ten_real_
processes` and its PreCompact sibling, so a future shape change to these two
commands is caught there rather than silently changing the claim on this
page.

**SessionStart's own internal fan-out is not counted in the table above**
because `hooks/hooks.json` wires it as a single `sh` invocation of
`tools/bm_sessionstart.sh`, and that script (owned by a different lane, not
this fence; read here, not modified) is itself a multi-process chain in its
consented path, derived by reading the file:

```
sh (the wrapper hooks.json invokes)
  cat            (capture stdin payload once)
  python3        (scripts/setup.py --consent-state, the consent gate)
  [only if consented, all of the below also run:]
  cat            (DIGEST.md)
  python3        (bm_telemetry.py startup-nags)
  python3        (bm_telemetry.py check-update)
  printf | python3   (bm_telemetry.py compact-hint, 2 processes)
  python3        (bm_store.py verify)
  printf | grep      (store-health check, 2 processes)
  [+1 more printf, conditionally, only if grep finds a problem]
```

That is **at least 11 real OS processes** in the common (consented,
healthy-store) path, before this fence's measurement even starts timing the
SessionStart action as a whole. `bm_hookbench.py`'s own docs list "The
SessionStart hook" as entirely unmeasured for exactly the reason this
count exists to state plainly: it is a shell script, bm_hookbench.py
executes Python in process, and a shell script cannot be run without
spawning a process. This finding is documented here from reading the
script; it is not independently verified against a process tracer
(`dtrace`/`strace`), and the file itself is outside this fence's ownership
(it lives in `tools/`, wired by `hooks/hooks.json`'s SessionStart line but
not a "dispatch script" this fence's ownership text covers, since it
already existed and this fence did not create or rename it).

## Real, whole-chain wall-clock cost (measured, current wiring, unchanged)

| Action | Real processes | Chain median ms | p90 ms | max ms |
|---|---|---|---|---|
| One SessionStart event | >=11 internal + 1 wrapper | 279.03 | 286.00 | 299.89 |
| One Edit/Write/MultiEdit/NotebookEdit tool call | 1 | 56.65 | 57.86 | 58.88 |
| One Bash tool call | 3 | 154.14 | 156.75 | 158.99 |
| One Stop event | 10 | 265.95 | 269.34 | 270.71 |
| One PreCompact event | 6 | 120.59 | 122.97 | 126.51 |
| One SessionEnd event | 1 | 56.05 | 57.21 | 68.83 |

Per-command breakdown for the two multi-command actions:

- **Bash tool call**: PreToolUse (fence group) 33.66 ms, PreToolUse (Bash
  audit pre) 62.27 ms, PostToolUse (Bash audit post) 58.37 ms; sums to
  154.30 ms against a chain median of 154.14 ms (the two can differ
  slightly; see `bm_hookbench.py`'s own note that the median of the sum is
  not the sum of the medians).

All calls exited 0, none timed out, across every repetition of every
action (`tools/test_bm_hookperf.py`'s own `TestRealChainMeasurement.
test_every_real_command_exited_zero_and_did_not_time_out`).

### Why these numbers read faster than `docs/PERFORMANCE.md`

`docs/PERFORMANCE.md` (bm_hookbench.py, in-process, 2026-08-07) reports the
Stop chain at a median of **853.36 ms**; this file's real, whole-process
measurement of the identical, unchanged Stop chain reads **265.95 ms**, a
little under a third of that. This was investigated rather than reported
uncritically, because a real measurement reading FASTER than an in-process
approximation is the opposite of what the LOWER BOUND framing on
`docs/PERFORMANCE.md` would predict. The cause: `bm_hookbench.py`'s
`Sandbox` sets `sys.dont_write_bytecode = True` so its own measurement never
writes a `.pyc` into this repository, which means every one of its
in-process calls recompiles every imported module from source, on every
single repetition, by design. A real `python3 tools/bm_telemetry.py`
subprocess in a checkout that already has bytecode cached from earlier
work (this one has run several other test suites this session) pays no
such compile cost, and reuses the cache the way a real installed session
would after its first use. Neither figure is wrong: `docs/PERFORMANCE.md`
measures a cold, never-cached worst case, and this page measures a warm,
steady-state one. They are not addable or directly comparable, and this
page does not attempt to reconcile them into one number.

## Why no consolidation was applied

Investigated and mechanically re-verified by
`tools/test_bm_hookperf.py::TestBlockersAreReal`, current as of this run:

1. **`tools/test_bm_consent.py`**:
   `TelemetryEveryHookProgramPreConsentCase` declares
   `MIN_WIRED_COMMAND_STRINGS = 7` and `MIN_WIRED_PROGRAMS = 11`, in its own
   words a floor that "is only allowed to move up." Live count, read fresh
   from `hooks/hooks.json` on this run: **exactly 7 command strings and
   exactly 11 programs. Headroom: zero.** Any edit that removes or merges a
   wired `python3`/`sh` invocation drops one of these counts and fails
   `test_no_wired_command_of_any_module_writes_before_consent`.
2. **`tools/test_bm_hookbench.py`**:
   `test_the_stop_event_chains_four_programs_under_one_shared_timeout`
   requires the Stop event to wire at least 2 programs, read fresh from
   `hooks/hooks.json` by that suite's own parser, which recognizes only
   `tools/`- and `scripts/`-prefixed invocations. A consolidating dispatch
   script placed anywhere, including inside `hooks/` (this fence's own
   directory), would not even register as a program to that parser and
   would report 0, not merely fewer.
3. **The "four-copy law"**: `scripts/install.py`'s `hook_commands()`
   function documents itself, in its own comments (lines near 176 and 229),
   as a hand-maintained duplicate of `hooks/hooks.json`'s wiring that "must
   move in the same change," after a real incident where it drifted and
   silently shipped a clone install missing a hook the plugin manifest
   promised. `tools/test_bm_docs.py::TestHandWiringBlocksMatchInstaller`
   parses the hand-wiring JSON blocks in `docs/QUICKSTART.md` and
   `docs/SETUP.md` and compares them, command text included, against
   `scripts/install.py`'s `hook_groups()`. None of `scripts/install.py`,
   `docs/QUICKSTART.md`, or `docs/SETUP.md` are in this fence's ownership.

None of `tools/test_bm_consent.py`, `tools/test_bm_hookbench.py`,
`tools/test_bm_docs.py`, `scripts/install.py`, `docs/QUICKSTART.md`, or
`docs/SETUP.md` are owned by FENCE V7 (sole writer of: `hooks/`, this file,
and `tools/test_bm_hookperf.py`). Editing `hooks/hooks.json` in a way that
trips any of the above would be a single-writer fence violation as well as
a regression in a currently-green, unrelated-owner test suite. Both
`tools/test_bm_consent.py` and `tools/test_bm_hookbench.py` were run
unmodified before any investigation began and are green except one
pre-existing, unrelated failure (`DoctorTenChecksCase.
test_duplicate_install_fixture_fails_naming_both`, about duplicate-install
detection, nothing to do with hooks; not caused by, or fixed by, this
fence).

### Independent refutation attempt

Per this project's own verification discipline (never trust a single
pass's finding on something this consequential), an independent read-only
reviewer was asked specifically to try to break the "no safe consolidation"
conclusion above. Result: **CONFIRMED**, with one narrower finding added.
The reviewer found a shell-wrapper-only rewrite of the Stop and PreCompact
`sh -c` scripts (replacing each `printf ... | python3 ...` pipe with an
input redirect placed before the command word, avoiding the extra forked
pipe stage while keeping every `python3 tools/bm_X.py ARGS` invocation
byte-identical in the manifest) that passes all of items 1 and 2 above,
because it changes zero wired programs and zero command strings. Quantified
by process count: Stop would go from 10 to 8 real processes (20 percent
fewer), PreCompact would stay at 6 (a `mktemp` and an `rm` replace the two
processes the rewrite saves). This was NOT applied by this fence, for two
reasons beyond simply falling short of the 40 percent target: it still
leaves `scripts/install.py` and the two docs pages textually diverged from
`hooks/hooks.json` (item 3 above, the exact drift class that has already
shipped a real incident once), and a stronger variant that reaches a larger
reduction on Stop requires editing `tools/bm_hookbench.py`'s command parser
(also outside this fence). The reviewer additionally confirmed the Bash
chain has no safe reduction at all: the only structural option (dropping
`Bash` from the fence hook's matcher) is not behavior-preserving (it would
stop gating a real Bash shape the fence hook's own docstring names,
`apply_patch` heredoc envelopes) and independently fails
`tools/test_install.py` and `tools/test_bm_plugin_install.py`'s group
matching.

The reviewer also found two blockers this fence had not identified, both
worth surfacing even though they do not change the "no code change" outcome
here:

- **`tools/test_all.py`** maintains its own `SUITES` registry and its
  `_inventory_gate` REFUSES (exit 2, before running anything) if a
  `test_*.py` file exists on disk that is not listed there, or is listed
  there but absent from `.github/workflows/tests.yml`. Creating
  `tools/test_bm_hookperf.py` (this fence's explicit mandate) will trip
  this refusal the moment `tools/test_all.py` is next run, until `SUITES`
  and the CI workflow are both updated to include it. Neither file is
  owned by this fence.
- **`CHECKSUMS.sha256`** records a hash of `hooks/hooks.json` (and other
  tracked files), checked by `scripts/prepush-check.sh` before a push is
  allowed. This fence made no change to `hooks/hooks.json`'s bytes, so this
  specific file is unaffected by this fence's work, but any FUTURE fence
  that does change `hooks/hooks.json` will also need to regenerate
  `CHECKSUMS.sha256`, which is likewise outside a hooks-focused fence's
  ownership as scoped here.

## Projected consolidation (not applied; arithmetic only)

Since no wiring change was safe to make, this section is a PROJECTION, not
a second real measurement of an applied change. It estimates what paying
the fork/exec/interpreter-bootstrap cost ONCE per event, instead of once
per program, would save, using only real-subprocess-measured numbers taken
in the same regime as the "real, whole-chain" table above (see the warning
in the previous section about why `docs/PERFORMANCE.md`'s in-process
figures cannot be substituted into this arithmetic; an earlier draft of the
measurement tool tried exactly that and produced a projection LARGER than
the real chain it was meant to be smaller than, which is how this
methodological difference was caught before publication).

Formula: `projected = sum(each program's own real standalone median) -
(count - 1) * bare_interpreter_startup_median`. Every program was
additionally measured on its own, real subprocess, wrapper bypassed
(`python3 <path> <args>` fed the same payload), 10 repetitions, 1 warmup,
same run as the table above.

| Chain | Programs collapsed | Real chain median ms | Projected ms | Reduction |
|---|---|---|---|---|
| Stop | 4 -> 1 | 265.95 | 228.88 | **13.94%** |
| PreCompact | 2 -> 1 | 120.59 | 104.61 | **13.25%** |
| Bash (PreToolUse portion only; PostToolUse cannot join, see below) | 2 -> 1 | 154.14 | 137.92 | **10.52%** |

**Target was 40 percent median reduction on the Bash and Stop chains. The
actual, measured, projected number is 13.94 percent on Stop and 10.52
percent on the PreToolUse portion of Bash. Neither clears the target.**
This is published as the actual result per this fence's own instruction:
"if actual improvement is lower, publish the actual result... never tune
the benchmark to create a better claim."

The Bash projection covers only PreToolUse's two groups (fence hook, Bash
audit pre): PostToolUse (Bash audit post) fires after the real Bash tool
call has already run and cannot share a process with anything that ran
before it, no matter how the wiring changes, so it is carried into the
projected total unchanged, at its own real measured value (58.37 ms).

This projection is a conservative lower bound on the likely benefit of a
real consolidation, not an upper one: a real single process could also
share warm imports across its calls within that one process (`bm_store.py`
alone is 17 thousand lines per `bm_hookbench.py`'s own docstring, and every
one of Stop's four programs imports it), which this projection does not
credit, because nothing measured here actually shares those imports. A
real implementation could plausibly do better than 14 percent; this file
does not claim a number it did not measure.

## Fail-open/fail-closed and blocking-vs-async policy

Preserved exactly, trivially, because `hooks/hooks.json` was not edited.
Ruling H5 (V3-FREEZE-2026-08-07.md) is restated here for the record this
fence was asked to keep it against: the PreToolUse fence deny and the
consent gate stay blocking and synchronous; PreCompact autosave is
correctness-bearing and may never go async; the PostToolUse bash audit is
informational detection; the status line is a command, not a hook. No
change in this fence touches any of that, since no change was made to the
wiring at all.

## Correctness checks executed

- `bm_hookbench.py`'s `Sandbox._validate()`: proves the fence refuses a
  foreign session and allows the owning session before any timing is taken
  (run implicitly, once per `Sandbox()` entry, by both `measure_real()` and
  `measure_standalone_programs()`).
- Every real command's exit code and timeout status, every repetition,
  every action: all exited 0, none timed out
  (`TestRealChainMeasurement.test_every_real_command_exited_zero_and_did_
  not_time_out`).
- The three blockers above, re-derived against the live files, not trusted
  as prose (`TestBlockersAreReal`, three tests, one per blocker).
- The repository-write hygiene check: a before/after directory snapshot
  across `.`, `tools`, `docs`, `hooks`, `scripts` proves this measurement
  process wrote nothing into the checkout
  (`TestRealChainMeasurement.test_the_run_wrote_nothing_into_this_
  repository`).
- `python3 tools/test_bm.py`, `python3 tools/test_bm_consent.py`, and
  `python3 tools/test_bm_hookbench.py` were run unmodified before any
  measurement work began, to establish that this fence's investigation
  started from a green baseline (one pre-existing, unrelated failure noted
  above).

## What is NOT measured here

- **Real Claude Code invocation overhead beyond the shell/python spawn.**
  This file spawns the exact command strings `hooks/hooks.json` wires,
  through a real shell, the same way `tools/test_bm_consent.py` already
  does; it does not measure whatever IPC or process-management overhead
  Claude Code's own hook-invocation machinery adds on top of that, which
  would need instrumentation inside Claude Code itself.
- **Concurrent load.** Every measurement here is one process at a time, in
  a throwaway sandbox; nothing here says what these numbers look like under
  a machine running several sessions at once, the same limitation
  `bm_hookbench.py`'s own NOT MEASURED section states about lock
  contention.
- **A steady-state measurement on a machine with cold bytecode caches.**
  This run benefited from `.pyc` caches already populated by earlier work
  in this session (see the section above explaining why these numbers read
  faster than `docs/PERFORMANCE.md`). A machine's very first session after
  install would pay compile costs this run did not, closer to (though not
  identical to, since that scenario still uses real processes rather than
  bm_hookbench.py's forced in-process recompilation) the `docs/PERFORMANCE.
  md` figures.
- **`strace`/`dtrace`-verified process counts for `tools/bm_sessionstart.sh`
  and the count_real_processes() static counter.** Both are derived by
  reading source text (the manifest's own JSON for the latter, the shell
  script for the former), not by tracing real kernel process creation.
  `count_real_processes()` is pinned by a regression test against the two
  known current shapes; a shape it does not recognize raises rather than
  guesses.
- **Reproducibility band.** `bm_hookbench.py` states and enforces a 2.0x
  band via `--compare`; this file states a wider 3.0x band (real process
  spawn carries more OS-scheduler variance on top of everything
  `bm_hookbench.py`'s figures already carry) but does not implement a
  `--compare` mode to enforce it, so treat 3.0x as a stated expectation,
  not a mechanically checked one.

## Reproducing this

```
python3 tools/test_bm_hookperf.py                          # the regression suite
python3 tools/test_bm_hookperf.py --measure --reps 10 --json   # this page's numbers, on stdout
python3 tools/test_bm_hookperf.py --measure --reps 10 --out somefile.json
```

Run from the BrotherMode root. Every command above works entirely inside a
throwaway sandbox and touches none of this machine's real store, vault or
home.

## Recommendation for a future coordinated fence

A real reduction toward the 40 percent target needs a SINGLE change that
touches, together, in one fence with all four files in its ownership:
`hooks/hooks.json`, `scripts/install.py` (`hook_commands()`/
`hook_groups()`), `docs/QUICKSTART.md`, `docs/SETUP.md`, and updates to the
floor constants in `tools/test_bm_consent.py`
(`MIN_WIRED_COMMAND_STRINGS`, `MIN_WIRED_PROGRAMS`,
`CONSENT_GATE_BY_MODULE`) and the pinned assertion in
`tools/test_bm_hookbench.py`
(`test_the_stop_event_chains_four_programs_under_one_shared_timeout`).
Whoever owns that fence should also add `tools/test_bm_hookperf.py` to
`tools/test_all.py`'s `SUITES` and to
`.github/workflows/tests.yml` (both are currently unlisted, which will make
`tools/test_all.py` refuse to run at all until fixed), and regenerate
`CHECKSUMS.sha256` after any edit to `hooks/hooks.json`. Given the honestly
projected 10 to 14 percent (not 40 percent) benefit from full
consolidation of Stop and PreCompact, and roughly 20 percent for a
narrower, lower-risk shell-wrapper-only rewrite of the same two chains
(quantified above), the size of that coordinated effort should be weighed
against the size of the actual win before it is scheduled.
