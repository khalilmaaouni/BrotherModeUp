# Fix report: the Codex runtime surface

Status: CURRENT. Written 2026-08-05 by the writer holding
`tools/bm_runtimes.py`, `tools/test_bm_runtimes.py`, `docs/runtimes/`,
`docs/RUNTIMES.md`, `docs/QUICKSTART.md`, `docs/SETUP.md`,
`docs/closure/CLOSURE_REGISTER.md` and this evidence folder.

Input: the four lane reports and the verdict in
`BrotherModeUp-handovers/2026-08-05-codex-lifecycle/`, read in full. Fail first
evidence, with every reproduction pasted, is beside this file in
`RED-codex-runtime.txt`.

Another writer held `tools/bm_store.py`, `tools/test_bm_store.py`,
`tools/bm_controller.py`, `tools/test_bm_controller.py`, `docs/KNOWN-LIMITS.md`
and `SECURITY.md` for the whole session. None of the six was opened for writing.
`git status` shows them modified by that writer, not by this one.

## Done check, run after the last edit

    $ python3 tools/test_bm_runtimes.py
    Ran 59 tests in 7.062s
    OK
    EXIT=0

    $ python3 tools/test_bm_docs.py
    Ran 199 tests in 17.753s
    OK (skipped=5)
    EXIT=0

    $ python3 tools/bm_runtimes.py check
    check OK: 6 adapter files and /Users/khalil.maaouni/Documents/BrotherModeUp/docs/RUNTIMES.md match the registry.
    EXIT=0

    $ python3 tools/test_bm_runtimes.py TestTheFirstRunSequenceActuallyRuns -v
    Ran 4 tests in 0.992s
    OK
    EXIT=0

    $ python3 tools/test_bm_runtimes.py -v TestEveryTaughtCommandIsRunnableFromAUsersOwnProject \
        TestCommandListsComeFromTheToolsThemselves TestTheFirstRunAdviceActuallyRuns \
        TestTheCodexHookAnswerIsTheMeasuredOne
    Ran 20 tests in 0.565s
    OK
    EXIT=0

Baseline before any edit, so the green above is a change and not a suite that
was never red: 35 tests OK in `test_bm_runtimes.py`, 199 OK in
`test_bm_docs.py`, `check` exit 0. With the first 20 guards written and the
generator NOT yet fixed: `Ran 55 tests, FAILED (failures=10, errors=9)`, exit 1.
Every failure is quoted in `RED-codex-runtime.txt`. The suite stands at 59
because round two added four more; see "Round two" below.

`tools/test_all.py`, the store suite and the controller suite were NOT run, as
instructed: another writer owns those files and the orchestrator runs the gate.

## Per item

| # | Item | Status | The evidence that decides it |
|---|---|---|---|
| 1 | The adapter's first instruction fails in a user's project | FIXED, after a correction in round two | The emitted `codex.AGENTS.md` carries 0 runnable instructions that are checkout relative (scan below), AND every command line in its ordered first run list now runs exactly as printed, in printed order, in a fresh throwaway project: 4 lines, 0 failures. The first version of this row was WRONG and is retracted; see "Round two" below. `TestTheFirstRunSequenceActuallyRuns` now executes that list on every suite run. |
| 2 | The adapter omits `bm_project.py`, and the lists have drifted | FIXED | Command lists are now generated from the tools by `ast`. Counted after the fix: bm_store tool 13 / adapter 13, bm_learn 40 / 40, bm_threads 12 / 12, bm_project 10 / 10, bm_telemetry 20 named (the tool prints no list of its own). `test_calibrated_a_tool_that_grows_a_command_makes_the_adapters_stale` fails the gate when a tool grows a command. |
| 3 | The sandbox and init trap | FIXED | Every adapter now carries a first run section that says `init` first and shows the refusal; the Codex adapter states `-s workspace-write`, verified by this writer with `codex --help` on codex-cli 0.146.0 before it was written down. |
| 4 | Three overstating lines in `docs/RUNTIMES.md` | FIXED | Line 18's promise now carries both measured caveats; the Codex CLI cell names the absolute path and the sandbox; the hooks cell is the measured answer, dated and version pinned, and says the fence does not transfer while saying the deny primitive exists. |
| 5 | No Codex install path on the pages a new user reads | FIXED | `grep -ci codex docs/QUICKSTART.md` was 0, now 10. `grep -ci codex docs/SETUP.md` was 0, now 8. Both link `RUNTIMES.md` and state the manual copy. |
| 6 | X-01 in the closure register | MOVED AND SPLIT | X-01 is out of "not machine-closable", with a PROVEN list, a DISPROVEN list and a STILL OPEN list, each citing the lane and the command. |

## Item 1, before and after

The old file, `docs/runtimes/codex.AGENTS.md` at line 33 and line 35:

    These work in any runtime that can run a shell command, which is why they
    carry no per runtime caveat. Run them from the project root. Paths below are
    relative to that root.

    `python3 tools/bm_store.py <command>` : the transactional store: ownership,
    fences, handover digests

Typed in a user's own project, that is:

    $ python3 tools/bm_store.py dashboard
    can't open file '.../redproj/tools/bm_store.py': [Errno 2] No such file or directory
    EXIT=2

The new file says which directory the path belongs to, shows the failure so an
agent recognizes it, shows an absolute example, and prefixes every command:

    Two directories are involved, and confusing them is how a first run fails.

    - THE BROTHERMODE CHECKOUT is the directory BrotherMode itself was cloned
      into. It is the ONLY place these tools exist. If you followed the install
      page it is `~/.claude/skills/brothermode`, whatever runtime you use: that
      directory name is historical and does not mean Claude Code has to be
      installed or running.
    - YOUR PROJECT is the repository you are actually working in. It has no
      `tools/` directory of its own, and it does not need one.

        WRONG in your own project:   python3 tools/bm_store.py dashboard
        what that actually gives you: can't open file '<your project>/tools/bm_store.py': [Errno 2] No such file or directory

        RIGHT (substituting your own checkout path):

            python3 /Users/you/code/brothermode/tools/bm_store.py dashboard

    `python3 <checkout>/tools/bm_store.py <command>` : the transactional store: ...

The placeholder appears only when the file is generated from INSIDE the
checkout, which is how the committed adapters are produced and how they stay
machine independent so `check` passes in any clone. When a user emits from their
own project, `tools_reference()` already returns an absolute path and the file is
literally runnable as printed; `test_an_absolute_tools_path_is_rendered_as_is`
holds that branch.

Proof that the emitted file no longer contains an instruction that fails from a
user project, run after the last regeneration:

    checkout-relative runnable instructions remaining: 0

(every `python3 ...bm_*.py` token in the emitted file, excluding the two lines
labelled WRONG and `[Errno 2]`, is absolute or carries the checkout prefix)

and the ordered list the file prescribes, extracted from the emitted file and
run VERBATIM (nothing added, nothing but `<checkout>` substituted) from a fresh
git project that is not the checkout and had never been initialized:

    $ python3 <checkout>/tools/bm_store.py init
      -> EXIT=0  bm_store: initialized .../probe2/.brothermode/store.sqlite3
    $ python3 <checkout>/tools/bm_store.py dashboard
      -> EXIT=0  <!-- BEGIN GENERATED BROTHERMODE STATE ...
    $ python3 <checkout>/tools/bm_store.py verify
      -> EXIT=0  verify: healthy, 0 problem(s)
    $ python3 <checkout>/tools/bm_project.py start --help
      -> EXIT=0  recognized flags: --actor-name, --actor-type, --allow-second, ...

    lines that failed: 0

An earlier version of this section showed `bm_project.py start --project-id
final-proof ...` and `next --project-id final-proof` here, which are commands I
composed rather than commands the file prints. That was the overclaim round two
retracts, and running the EXTRACTED list rather than a hand written one is what
replaces it.

## Round two: the correction the orchestrator caught, and the guard that replaces my word

The orchestrator ran the fixed adapter's own first run list by hand and found
that its LAST line still failed. The list ended with:

    python3 <checkout>/tools/bm_project.py start     (open a project, then `next` tells you what to work on)

which, run exactly as printed in a project with a healthy store, gives:

    usage: start --project-id ID --name NAME [--goal G] ... --actor-name NAME ...
    bm_project: --project-id is required
    EXIT=2

That is finding 1 all over again, one line further down: the block written to
stop the adapter giving instructions that cannot run, closed on an instruction
that cannot run.

**The first version of this report's item 1 row is retracted.** It said "Every
instruction it gives was run for real from a throwaway user project: init,
verify, `bm_project.py start`, `bm_project.py next`, all exit 0". That is false
for the last two. I ran them with flags I supplied myself, then wrote the row as
though I had run what the file prints. The orchestrator's diagnosis of the gap
was exactly right.

THE FIX. The ordered list now ends with:

    python3 <checkout>/tools/bm_project.py start --help   (the flags `start` needs, printed by the tool itself)

so all four lines run exactly as printed, and the reader still gets the flags,
from the tool rather than from a document. Verified after the last edit, in a
fresh throwaway project that is not the checkout and had never been initialized,
each line run verbatim with `<checkout>` substituted:

    $ python3 <checkout>/tools/bm_store.py init
      -> EXIT=0  bm_store: initialized .../probe2/.brothermode/store.sqlite3
    $ python3 <checkout>/tools/bm_store.py dashboard
      -> EXIT=0  <!-- BEGIN GENERATED BROTHERMODE STATE ...
    $ python3 <checkout>/tools/bm_store.py verify
      -> EXIT=0  verify: healthy, 0 problem(s)
    $ python3 <checkout>/tools/bm_project.py start --help
      -> EXIT=0  recognized flags: --actor-name, --actor-type, --allow-second, ...

    lines that failed: 0

WHY NOT A CONCRETE FLAG EXAMPLE, which is the other branch the orchestrator
offered. It is forbidden in adapter text by a pre-existing guard, and this loop
does not edit a passing test to make room for itself. Verbatim, from
`tools/test_bm_runtimes.py::TestCapabilityClaimsStaySeparate::test_generated_files_teach_no_flag_names`:

    if tok.startswith("--") and len(tok) > 2 and tok[2].isalpha():
        self.assertIn(
            tok.strip(".,`"), ("--help", "--runtime"),
            "%s teaches the flag %s; adapters may only name "
            "--help and the regeneration command" % (r["key"], tok))

Printing `--project-id`, `--name`, `--actor-type` or `--actor-name` in an
adapter fails that assertion, and its reasoning is sound: a flag copied into an
instruction file is a flag that goes stale, which is the same class of defect as
the rc.9 adapter teaching `bm_learn.py relevant`. So the list closes on the
command that makes the tool print its own never stale flag list, including
`--actor-type`, which is the flag the orchestrator noted is easy to get wrong.
If the founder or the orchestrator would rather have the inline example, the
remedy is to relax that guard deliberately, not as a side effect of this fix.

THE GUARD, so this is enforced rather than attested:
`TestTheFirstRunSequenceActuallyRuns` in `tools/test_bm_runtimes.py`. It
extracts every command line the generator emits into a first run block, groups
the runtimes by identical sequence (all six share one today, and a runtime that
ever diverges becomes its own group and is executed too), creates a throwaway
git project that is NOT the checkout and has never been initialized, and runs
each line in printed order with `<checkout>` substituted, asserting exit 0. Four
tests:

- `test_every_first_run_command_runs_exactly_as_printed` does the execution, and
  refuses to pass on a block shorter than four commands so it cannot pass
  vacuously;
- `test_calibrated_an_unrunnable_line_in_the_block_is_caught` reinjects the bare
  `bm_project.py start`, asserts the executor fails with the right message, then
  restores and re-runs green. Its real output, with the defect reinjected, is
  quoted verbatim in `RED-codex-runtime.txt` under RED-7;
- `test_an_excluded_command_must_carry_a_reason` holds the exclusion map, which
  is EMPTY today: every line the block prints runs offline, locally, with no
  store and no network. Anything that later cannot run in a test is excluded by
  its exact command text with a written reason, so a narrowing is a visible
  decision rather than a shrinking scan;
- `test_the_block_ends_by_pointing_at_the_tools_own_flags` holds the shape of the
  fix, so a future edit cannot quietly put the bare `start` back.

## Item 2, how the command lists are generated

Generation is real for all five tools, including the one that has no dispatch
dict. `discover_commands(path)` in `tools/bm_runtimes.py` parses the module
SOURCE with `ast`: no import, no execution, no subprocess, so discovering a
tool's surface can never run a tool's side effects. It reads two shapes, both of
which exist in this repository:

1. a module level `COMMANDS` or `_COMMANDS` dict, which covers `bm_store.py`
   (13), `bm_project.py` (10), `bm_threads.py` (12) and `bm_learn.py` (40);
2. an if/elif chain on a dispatch variable inside `main()`, which is the only
   shape `bm_telemetry.py` has (20 commands). It has no dispatch dict and prints
   no command list of its own, so nothing else could have kept it honest:
   `grep -c "COMMANDS" tools/bm_telemetry.py` returns 0.

Nothing is hand maintained. `_CLI_MODULES` carries the module name and a one
line purpose; `CLI_SURFACE` is built from it at import with the commands
discovered. `CLI_SURFACE` keeps its original three tuple shape on purpose, so
the three pre-existing tests that unpack it still pass unchanged.

`discover_deprecated(path)` marks a command whose handler declares itself
DEPRECATED in its own docstring. Today that is exactly one, `bm_learn.py
relevant`, which exits 2 with a deprecation banner and which Lane D found
surviving a version update inside a stale adapter. It renders as
`relevant (deprecated)` rather than being dropped, because a command that still
runs should still be findable. KNOWN LIMIT, stated in the code as well: this
reads the docstring only, so a command deprecated without saying so in its
docstring is not detected.

The drift guard is two tests plus the existing `check`:

- `test_the_surface_is_discovered_not_typed` asserts `CLI_SURFACE` equals what
  the modules dispatch;
- `test_every_adapter_names_every_command_its_tools_dispatch` asserts the
  rendered `commands:` line of every adapter names every discovered command;
- `test_calibrated_a_tool_that_grows_a_command_makes_the_adapters_stale` grows
  the surface the way a new subcommand would and proves `cmd_check` returns 1
  and names the stale files, then proves it returns 0 again once restored.

CONSEQUENCE THE ORCHESTRATOR SHOULD KNOW: `bm_runtimes.py check` is now coupled
to the tools. If the writer currently holding `tools/bm_store.py` lands a new
dispatch key, `check` goes STALE until `python3 tools/bm_runtimes.py emit` is
re-run. That is the gate working as designed, and it is a new way for the
release gate to go red on a change that has nothing to do with runtimes. The
remedy is one command.

## Item 3, the flag spelling, verified here rather than inherited

    $ codex --version
    codex-cli 0.146.0
    $ codex --help | grep -A4 "sandbox <SANDBOX_MODE>"
      -s, --sandbox <SANDBOX_MODE>
              Select the sandbox policy to use when executing model-generated shell commands

              [possible values: read-only, workspace-write, danger-full-access]

The adapter says `-s workspace-write` and records where that spelling came from
and on which version. The first run section is shared by every runtime, because
the trap is not Codex specific: `dashboard` and `verify` refuse on a project
that has never been initialized. Reproduced here in all three project shapes,
exit 2 each time, quoted in `RED-codex-runtime.txt`: `refused (no-store)` in a
git repository with the ignore rule, `refused (git-exposed-store)` in one
without it, `refused (no-root)` in a plain directory.

## Item 4, what the capability page says now

The CLI promise, previously "They are ordinary local processes, so they work in
any runtime that can run a shell command", now reads: the CODE is runtime
neutral and the EXPERIENCE is not, with both measured failures named, the
`[Errno 2]` from a checkout relative path and the
`PermissionError(1, 'Operation not permitted')` from Codex's default read-only
sandbox.

The Codex row:

    | OpenAI Codex CLI | `AGENTS.md` | yes, with two caveats measured on
    2026-08-05: call the tools by their absolute path in the checkout, and start
    Codex with `-s workspace-write` | yes: SessionStart, SessionEnd, PreToolUse,
    PostToolUse, and 7 more | MEASURED 2026-08-05 on codex-cli 0.146.0, and the
    answer is no. Payloads are Claude shaped and a PreToolUse deny really does
    block, so the primitive exists; but the one writer fence does not transfer,
    because every write arrives as tool_name Bash running apply_patch, so the
    Edit/Write matcher never fires. Hooks are also inert until the project is
    trusted, and SessionEnd is clamped to 3s. Do not wire them. |

The "two questions" paragraph no longer says nobody has captured a payload, and
the per runtime section carries seven measured findings with the lane report
named. `test_nothing_anywhere_claims_the_fence_works_in_codex` holds the line
that none of this reads as a working fence.

## Blocked, disclosed, or deliberately not done

1. **`list --json` still reports `brothermode_hooks: "unverified"` for Codex,
   which is now imprecise.** Changing it collides with an existing passing test
   in a file I own, and a passing test is not something this loop edits to make
   room for itself. The assertion, verbatim from
   `tools/test_bm_runtimes.py::TestListAndHelp::test_list_json_names_every_runtime_and_its_hook_status`:

       self.assertIn(row["brothermode_hooks"],
                     ("unverified", "not applicable"),
                     "no row may claim BrotherMode hooks are verified "
                     "outside Claude Code: %r" % row)

   What I did instead: added `brothermode_hooks_measured`, `measured_on`,
   `measured_runtime_version` and `requirements` to each JSON row, so a machine
   consumer gets the precise answer beside the legacy one. The ACTION implied by
   both is identical (do not wire it); the imprecision is that "unverified"
   understates the certainty. PROPOSED REMEDY for whoever owns that call: widen
   the tuple to `("unverified", "not applicable", "measured, does not
   transfer")` and set the legacy field from the registry. That is a
   strengthening, not a weakening, and it should be a deliberate decision rather
   than a side effect of this fix.
2. **The adapters still cannot show a concrete flag example**, by the existing
   guard quoted in "Round two". The ordered list runs as printed and the tool
   prints its own flags, which covers the reader; what is not available is
   `--project-id my-project --name "..." --actor-type model --actor-name ...`
   inline. Relaxing that guard is a deliberate call for whoever owns it, and I
   did not make it on their behalf.
3. **A precision correction to the brief.** The brief says Lane D "ran
   `scripts/doctor.py` ... under Codex with no Claude Code". Lane D states in its
   own words: "I never ran the `codex` binary." Its doctor run proves the
   install verifies OUTSIDE Claude Code, in a plain shell in a throwaway HOME.
   The evidence that BrotherMode commands run INSIDE Codex's tool pathway and
   sandbox is Lane B. The X-01 entry states both separately and flags the
   distinction, because "a second runtime ran it" and "an install verified with
   no Claude Code" are different claims.
4. **`CHECKSUMS.sha256` no longer matches the working tree for the files this
   loop changed.** That manifest is regenerated at release time and is outside
   this fence. `doctor.py` check 9 already reported 5 mismatching files before
   this session started (Lane A recorded it as a pre-existing condition); this
   loop adds its own changed files to that count until the manifest is
   regenerated. `tools/test_bm_docs.py`'s checksum test reads the git TAG rather
   than the working tree, which is why it is green.
5. **Only the Codex row carries a CLI caveat cell.** The absolute path caveat is
   true of every runtime, and it is stated in the paragraph directly above the
   table for all of them, but the other five rows still read a bare "yes" in that
   column. Adding a per runtime `cli_note` to the rest is a five line registry
   change and was left out to keep this loop's diff to the Codex surface.
6. **Not mine to fix, and still open** (verdict gaps 5, 6, 7, 8, 9, 11): the
   uninstaller leaving the emitted `AGENTS.md` behind, the update path never
   refreshing the adapter, the store's unreadable `PermissionError`, the update
   notifier being silent on a tag install, `BROTHERMODE_VAULT` overriding
   consent, and telemetry recording nothing under Codex. Those live in
   `scripts/uninstall.py`, `commands/brotherme-update.md`, `tools/bm_store.py`
   and `tools/bm_telemetry.py`. The first two are cheap and the emitted files
   already carry the marker line an uninstaller would key on.
7. **Not verified by me**: whether a real authenticated model obeys the adapter,
   whether Codex's hook trust grant survives editing `hooks.json`, and anything
   about the five non Codex runtimes. All three are recorded in the X-01 entry
   as open, with what each one needs.
8. **The other five adapters were regenerated** and carry the same checkout
   block, generated command lists and first run section. They were read, not
   run: no Copilot, Qwen, iFlow or Antigravity session was driven in this loop.

## Files changed

    docs/QUICKSTART.md                              +53
    docs/SETUP.md                                   +47
    docs/RUNTIMES.md                                (generated)
    docs/runtimes/*.md, all six                     (generated)
    docs/closure/CLOSURE_REGISTER.md                X-01 split and evidenced
    tools/bm_runtimes.py                            the registry and the renderer
    tools/test_bm_runtimes.py                       +24 guards, 35 existing untouched
    docs/program/absolute-lead/evidence/RED-codex-runtime.txt    fail first evidence
    docs/program/absolute-lead/evidence/FIX-codex-runtime-report.md  this file
