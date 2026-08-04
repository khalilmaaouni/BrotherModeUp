# B-3 plugin install build report, 2026-08-04

Status: CURRENT

Builder agent B-3, Loop 3. Implemented the spec at
`docs/closure/reports/2026-08-04-N-3-plugin-install-test-spec.md` exactly as
written, with one implementation fix discovered while proving the suite
actually passes (below). Nothing in the spec was found wrong or refused.

## Files touched (all within the fenced WRITE list, all five permitted paths)

1. `/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_bm_plugin_install.py` (NEW)
   Three test classes: `TestPluginManifestsAgreeWithTheTree` (6 tests, runs
   unconditionally, no `claude` binary needed), `TestPluginInstallFromATempCopy`
   (10 tests, skips at `setUpClass` when no `claude` binary is on PATH),
   `TestPluginUninstallLeavesNoTrace` (2 tests, same skip rule). 18 tests
   total.
2. `/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_all.py`
   Added exactly one SUITES entry, `"test_bm_plugin_install.py"`, immediately
   after `"test_bm_packaging_install.py"` and before `"test_bm.py"`, with a
   comment carrying no apostrophe or quote character. No other line in this
   file was touched.
3. `/Users/khalil.maaouni/Documents/BrotherModeUp/.github/workflows/tests.yml`
   Added one step, "Run the plugin install suite", to the `suite` job,
   immediately after the existing "Run the packaging install suite" step,
   mirroring its shape exactly.
4. `/Users/khalil.maaouni/Documents/BrotherModeUp/docs/closure/protocols/2026-08-04-improvised-readme-install-protocol.md` (NEW)
   Opens with the title line and `Status: CURRENT` within the first 25 lines
   (confirmed against the exact regex `tools/test_bm_docs.py` uses,
   `^Status:\s*CURRENT\b`, read before writing). States plainly that the
   observation has never been run under controlled conditions and names the
   record path convention (`docs/evidence/YYYY-MM-DD-improvised-readme-install-run-N.md`)
   where the first real run should land.
5. `/Users/khalil.maaouni/Documents/BrotherModeUp/docs/closure/reports/2026-08-04-B-3-plugin-install-build.md` (this file, NEW)

## The one implementation fix, found and corrected before declaring done

Spec test 5 of class B (`test_the_installed_hooks_agree_with_hooks_json_field_by_field`)
says to compare each `command` field "AFTER replacing `${CLAUDE_PLUGIN_ROOT}`
with the respective root on each side, so the two are comparable." My first
draft substituted the token with `ROOT` on the expected side and
`install_path` on the installed side, then compared the two resulting
strings directly. That failed on the very first run: `ROOT` and
`install_path` are different absolute paths by construction (the plugin
installs into `$HOME/.claude/plugins/cache/...`, never into `ROOT`), so
direct string equality could never pass, on any run, for any of the six
non-trivial hook groups. Fixed by normalizing each side's own root back out
to a shared placeholder (`<PLUGIN_ROOT>`) after the substitution, so the
comparison catches a real divergence (a different tool, a dropped flag, a
different subcommand) while treating the unavoidable root-path difference as
equal. Re-ran after the fix; it passes.

## Done-check, run after the last edit

Command (verbatim, exactly as specified):

    python3 tools/test_bm_plugin_install.py

Verbatim tail of the run:

    ..................
    ----------------------------------------------------------------------
    Ran 18 tests in 36.623s

    OK

Exit code: 0.

A `claude` binary (2.1.207) is present on this machine, so class B and class
C ran for real rather than skipping: the suite drove `claude plugin
validate`, `marketplace add`, `install`, `list --json`, `details`,
`uninstall -y` and `marketplace remove` against a throwaway copy of the tree
under a throwaway HOME, twice (once per install cycle: class B's own cycle,
then class C's separate cycle). Isolation was checked directly, not just
trusted: after the full run, `claude plugin list --json` against the REAL
`HOME` (no override) was inspected and contains no `brotherme` entry, so
nothing leaked into the founder's real Claude configuration during this
build.

## git status --porcelain, run after the last edit

Full output:

    M .github/workflows/tests.yml
    M README.md
    M docs/NOT-FINALIZED.md
    M docs/PACKAGING.md
    M docs/QUICKSTART.md
    M docs/REMAINING.md
    M tools/test_all.py
    ?? docs/closure/PLAN-LOOPS-2-7-2026-08-04.md
    ?? docs/closure/protocols/
    ?? docs/closure/reports/
    ?? tools/test_bm_plugin_install.py

**Mine (the four fenced paths plus this report, all inside the paths listed
above):** `.github/workflows/tests.yml`, `tools/test_all.py`,
`tools/test_bm_plugin_install.py` (new, inside `?? tools/`... entry is
actually the file itself since it is untracked),
`docs/closure/protocols/` (new directory, holds the one new protocol
document), and `docs/closure/reports/` (this report lands inside that
already-untracked directory, alongside other agents' pre-existing report
files).

**Not mine, other agents' concurrent work, not touched by me:**
`README.md`, `docs/NOT-FINALIZED.md`, `docs/PACKAGING.md`,
`docs/QUICKSTART.md`, `docs/REMAINING.md`,
`docs/closure/PLAN-LOOPS-2-7-2026-08-04.md`. `docs/PACKAGING.md` was
observed changing mid-run (see below); the others were seen modified in
`git status` but were not inspected further since they are outside this
fence.

## A live finding from running the suite twice, not a defect in the suite

The first run of `test_the_source_tree_is_unchanged_by_the_whole_install_cycle`
failed, reporting `docs/PACKAGING.md` as changed between the pre-cycle and
post-cycle fingerprint of `ROOT`. This was not a bug in the test or in the
install cycle: another agent working concurrently in this same checkout
edited `docs/PACKAGING.md` (40 lines added) while my suite was mid-run, which
`git status --porcelain` still shows as `M docs/PACKAGING.md` right now. The
test correctly detected a real mutation of `ROOT` during its run; the
mutation's source was a different writer, not this suite or the plugin
install cycle. Re-running once that edit had settled passed clean. Flagging
this as a known limitation rather than fixing it: `TestPluginInstallFromATempCopy`
and `TestPluginUninstallLeavesNoTrace`, as specified, fingerprint the entire
`ROOT` tree before and after their own cycle, so on a machine where another
process is actively writing to the same checkout at the same moment, this
test can report a false positive that has nothing to do with the plugin
install path. The spec's own single-agent live run would never have hit
this, since nothing else was writing to the tree at the time.

## What I refused, and why

Nothing. The spec was followed as written; the one fix above was a
correction to my own first draft against the spec's stated intent ("so the
two are comparable"), not a deviation from the spec itself.

## Known issue, out of fence, not touched

Per the brief: `tools/test_bm_packaging_install.py`'s "reports SKIPPED
rather than failing red" claim in the SUITES comment is flagged as
unverified/likely wrong by the spec, and is outside this fence. Not
inspected or changed here.
