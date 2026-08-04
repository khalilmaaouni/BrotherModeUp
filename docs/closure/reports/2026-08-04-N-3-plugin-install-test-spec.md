# Implementation spec: the plugin path install test and the improvised README install observation protocol. Loop 3, agent N-3, 2026-08-04.

Status: CURRENT

This is a design document, not an implementation. No file in the repository was
written by N-3 except this one. Every path named below was confirmed on disk
with `ls` or `find` before it was typed; the four paths marked NEW do not exist
yet and were confirmed absent the same way. Every command surface named below
was confirmed with `--help` or by running it against a throwaway HOME, never
recalled from memory.

## What was verified live before this spec was written

The full plugin route was driven end to end, non interactively, against a
throwaway HOME under the session scratchpad, from a copy of the tree rather
than from the tree. It works, which is what makes an automated test possible
at all. Verbatim results:

    claude plugin validate <copy>            rc 0, "Validation passed"
    claude plugin marketplace add <copy>     rc 0, "Successfully added marketplace: brotherme-marketplace"
    claude plugin install brotherme@brotherme-marketplace   rc 0, "(scope: user)"
    claude plugin list --json                one entry, id brotherme@brotherme-marketplace
    claude plugin uninstall brotherme -y     rc 0
    claude plugin marketplace remove brotherme-marketplace  rc 0
    claude plugin list --json                []

Facts the builder needs, all observed rather than assumed:

1. `claude plugin list --json` returns `installPath`, and on this run it was
   `$HOME/.claude/plugins/cache/brotherme-marketplace/brotherme/2.0.0-rc.13.dev1`.
   That is the ONLY supported way to locate the installed copy. Do not
   reconstruct that path by string building; read it from the JSON.
2. The installed copy is a real directory of real files, not a symlink to the
   source. `hooks/hooks.json` inside it was byte identical to the source copy.
3. `claude plugin details brotherme` prints `Hooks (6)  SessionStart,
   SessionEnd, Stop, PreCompact, PreToolUse, PostToolUse` and `Skills (8)`.
   Six is exactly the event set in `hooks/hooks.json` and in
   `scripts/install.py` HOOK_EVENTS. Eight is the seven files in `commands/`
   plus the one skill directory `plugin.json` declares.
4. `.claude-plugin/plugin.json` declares only `skills`. The six hook events are
   auto discovered from `hooks/hooks.json`. Nothing in the manifests names
   them, so the only field by field comparison possible is against
   `hooks/hooks.json` itself.
5. A from scratch environment of exactly PATH, HOME, BROTHERMODE_VAULT and
   BROTHERSBE_VAULT is sufficient for every one of those commands. Confirmed by
   running the whole cycle again with that dict and nothing else.
6. The repository working tree was unchanged by the entire cycle:
   `git status --porcelain` before and after showed the same two untracked
   entries and nothing else.

## Files the builder will create or modify

    /Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_bm_plugin_install.py
    /Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_all.py
    /Users/khalil.maaouni/Documents/BrotherModeUp/.github/workflows/tests.yml
    /Users/khalil.maaouni/Documents/BrotherModeUp/docs/closure/protocols/2026-08-04-improvised-readme-install-protocol.md

Nothing else. In particular CHECKSUMS.sha256 is NOT on this list: the test that
compares it against the tree
(`tools/test_bm_docs.py::TestReleaseTruth::test_the_checksum_manifest_matches_the_tagged_tree`,
confirmed by reading it) runs against a TAG and calls `_skip_unless_released()`
first, and `VERSION` currently reads `2.0.0-rc.13.dev1`, a development
identity, so it skips. Regenerating the manifest is a release cut obligation,
not a builder obligation, and doing it here would put the builder outside the
fence.

## Module level constants for tools/test_bm_plugin_install.py

Every one of these was confirmed to exist:

    HERE  = os.path.dirname(os.path.abspath(__file__))
    ROOT  = os.path.dirname(HERE)
    HOOKS_JSON       = os.path.join(ROOT, "hooks", "hooks.json")
    PLUGIN_JSON      = os.path.join(ROOT, ".claude-plugin", "plugin.json")
    MARKETPLACE_JSON = os.path.join(ROOT, ".claude-plugin", "marketplace.json")
    INSTALL_PY       = os.path.join(ROOT, "scripts", "install.py")
    COMMANDS_DIR     = os.path.join(ROOT, "commands")
    VERSION_FILE     = os.path.join(ROOT, "VERSION")
    PLUGIN_NAME      = "brotherme"
    MARKETPLACE_NAME = "brotherme-marketplace"
    PLUGIN_ID        = "brotherme@brotherme-marketplace"
    PLUGIN_ROOT_TOKEN = "${CLAUDE_PLUGIN_ROOT}"

Python 3.9, standard library only, no network. The suite drives subprocesses,
which is allowed because the file carries the `test_` prefix that
`tools/test_bm.py`'s no subprocess ban excludes for exactly this reason.

## Test classes and methods, with the pass and fail criterion of each

### Class A: TestPluginManifestsAgreeWithTheTree

Runs unconditionally. It needs no `claude` binary, no network and no install.
It exists for a second reason beyond its own assertions, and that reason is
load bearing: `tools/test_all.py::_run_one` marks a suite that "exited 0 but
ran 0 tests" as FAILED, and a class level `raise unittest.SkipTest` produces
exactly `Ran 0 tests`. Proved directly while writing this spec with a two test
throwaway file: class level skip printed `Ran 0 tests in 0.000s` then
`OK (skipped=1)`. So a suite whose ONLY class skips on a machine without the
CLI would turn the whole gate red on every CI runner. Class A is the guarantee
that this suite always runs at least five real tests.

1. `test_the_three_version_claims_and_the_version_file_agree`
   PASS when `plugin.json["version"]`, `marketplace.json["metadata"]["version"]`
   and the `version` of the single entry in `marketplace.json["plugins"]` are
   all equal to the stripped contents of `VERSION`. Today all four read
   `2.0.0-rc.13.dev1`, confirmed. FAIL listing each field that disagrees and
   the value it carries.

2. `test_every_skill_path_the_plugin_manifest_declares_resolves`
   PASS when every entry of `plugin.json["skills"]` (today the single value
   `./skills/brotherme`) resolves under ROOT to a directory containing
   `SKILL.md`. Confirmed present. FAIL naming the entry and the path it
   resolved to.

3. `test_the_marketplace_entry_points_at_this_repository`
   PASS when the single plugins entry has `name == PLUGIN_NAME` and
   `source == "./"`, and `marketplace.json["name"] == MARKETPLACE_NAME`. This
   is what makes `claude plugin install brotherme@brotherme-marketplace`
   resolve at all. FAIL quoting the actual values.

4. `test_the_hook_manifest_names_the_same_events_as_the_clone_installer`
   Parse HOOK_EVENTS out of `scripts/install.py` with the same top level tuple
   read `tools/bm_project_facts.py::_tuple_strings` performs, or import free
   regex of the builder's choosing, and compare it as a SET against the keys of
   `json.load(HOOKS_JSON)["hooks"]`. PASS on set equality. FAIL naming events
   present in one file and absent from the other, in both directions. Today
   both sides are the same six: SessionStart, SessionEnd, Stop, PreCompact,
   PreToolUse, PostToolUse.

5. `test_every_hook_command_in_the_manifest_names_a_file_that_exists`
   For each group in each event of `hooks/hooks.json`, take the entry command,
   replace `${CLAUDE_PLUGIN_ROOT}` with ROOT, then extract path arguments the
   way `scripts/install.py::command_path_tokens` does: `shlex.split`, and when
   a token is `-c` split the NEXT token one further level and keep the
   arguments containing `os.sep`. PASS when every extracted token is an
   existing file. FAIL naming the event, the matcher and the missing path. This
   catches a renamed tool that the manifest still points at. Today the five
   distinct tools it reaches are `tools/bm_sessionstart.sh`,
   `tools/bm_telemetry.py`, `tools/bm_autosave.py`, `tools/bm_fence_hook.py`
   and `tools/bm_bash_audit.py`, all confirmed present.

6. `test_the_copy_exclusion_list_covers_everything_the_clone_installer_excludes`
   Parse COPY_EXCLUDE_NAMES out of `scripts/install.py` (confirmed present at
   line 106, holding `.git`, `.brothermode`, `__pycache__`, `threads`,
   `.superpowers`, `.DS_Store`, `STATE.md`) and assert every name is in this
   suite's own COPY_EXCLUDE tuple. PASS on subset. FAIL naming the names the
   fixture would ship that the clone install would not. Without this the
   fixture drifts from what a real user receives the next time the installer's
   list grows.

### Class B: TestPluginInstallFromATempCopy

`setUpClass` skips with a plain reason when `shutil.which("claude")` is None,
which is the normal case on a GitHub runner. It never fails for that reason,
following `tools/test_bm_packaging_install.py`, which skips rather than fails
when its own environment precondition is missing.

`setUpClass` order, and the order matters:

  a. `cls.tree_before = _tree_fingerprint(ROOT)` FIRST, before anything else.
  b. make the temp directory, make the fake HOME, build `cls.env`.
  c. copy the tree (procedure below).
  d. run `claude plugin validate <copy>`, keep the result.
  e. run `claude plugin marketplace add <copy>`, keep the result.
  f. run `claude plugin install brotherme@brotherme-marketplace`, keep it.
  g. run `claude plugin list --json`, parse it, keep `cls.install_path`.
  h. run `claude plugin details brotherme`, keep stdout.
  i. `cls.tree_after = _tree_fingerprint(ROOT)` LAST.

`tearDownClass` runs `claude plugin uninstall brotherme -y`, then
`claude plugin marketplace remove brotherme-marketplace`, both best effort and
neither allowed to raise, then `shutil.rmtree(cls.tmp, ignore_errors=True)`.
Flags confirmed from `claude plugin uninstall --help`: `-y` is required when
stdout is not a TTY.

`_tree_fingerprint(root)` returns a dict of relative path to
`(size, mtime_ns)` for every file under root, skipping `.git` and any name in
COPY_EXCLUDE. It reads only, never writes.

1. `test_plugin_validate_passes_on_the_copied_tree`
   PASS when the validate result has returncode 0 and its stdout contains
   `Validation passed`. FAIL printing stdout and stderr. Observed verbatim
   today: `✔ Validation passed`.

2. `test_the_marketplace_is_added_and_the_plugin_installs`
   PASS when both the marketplace add and the install returned 0. FAIL printing
   both outputs.

3. `test_plugin_list_reports_the_plugin_installed_enabled_and_at_this_version`
   PASS when `claude plugin list --json` parses to a list holding exactly one
   entry whose `id` is PLUGIN_ID, whose `enabled` is True, whose `scope` is
   `user`, whose `version` equals `plugin.json["version"]`, and whose
   `installPath` starts with the fake HOME. The last clause is the isolation
   assertion: an installPath outside the fake HOME means the test wrote into
   the founder's real configuration and must go red immediately.

4. `test_the_installed_copy_carries_the_hook_manifest_byte_for_byte`
   PASS when `sha256(installPath/hooks/hooks.json)` equals
   `sha256(ROOT/hooks/hooks.json)`. FAIL printing both digests. Confirmed
   identical on the live run.

5. `test_the_installed_hooks_agree_with_hooks_json_field_by_field`
   THIS IS THE CONSTRAINT 3 TEST. It is modelled directly on
   `tools/test_install.py::TestHooksJsonAgreesWithInstaller::test_every_group_agrees_on_timeout_and_status_message`
   (read in full at lines 265 to 307): build a list of mismatch strings, then
   `self.assertEqual([], mismatches, "\n".join(mismatches))` so one run reports
   every divergence rather than the first.

   Observed side: the hooks JSON inside `installPath`. Expected side: the hooks
   JSON at ROOT. For every event, for every group, matched by
   `group.get("matcher")` and never by list index (the clone suite says why:
   index ties the test to group ORDER, which is not the contract), compare
   these fields and no others:

     - the event name itself (a group present in one and absent in the other)
     - `matcher`, including the case where one side has none
     - the number of entries in `group["hooks"]`
     - per entry, `type`
     - per entry, `command`, compared AFTER replacing `${CLAUDE_PLUGIN_ROOT}`
       with the respective root on each side, so the two are comparable
     - per entry, `timeout`
     - per entry, `statusMessage`

   PASS when the mismatch list is empty. FAIL with one line per divergence in
   the shape the clone suite already uses:
   `"%s[%s].%s: hooks.json=%r, installed=%r" % (event, matcher, field, want, got)`.
   Today the expected values are the six groups in `hooks/hooks.json`:
   SessionStart timeout 30 "Loading your project memory"; SessionEnd timeout 30
   "Saving the session record"; Stop timeout 15 "Checking for unfinished work";
   PreCompact timeout 60 "Saving your work before the context is condensed";
   PreToolUse matcher `Edit|Write|MultiEdit|NotebookEdit` timeout 10 "Checking
   that only one worker edits this file"; PreToolUse matcher `Bash` timeout 10
   "Noting the fenced files before this shell command runs"; PostToolUse
   matcher `Bash` timeout 15 "Checking whether that shell command crossed a
   fence". Do not hardcode those strings in the test; read them from the file.

6. `test_every_installed_hook_command_resolves_inside_the_installed_copy`
   Same token extraction as class A test 5, but substituting `installPath` for
   the token. PASS when every path is an existing file AND
   `os.path.realpath(path)` starts with `os.path.realpath(installPath)`. The
   containment half is the real assertion: a hook that resolves to a file
   outside the installed copy is a hook pointed at somebody else's checkout.
   FAIL naming the event, the matcher and the offending path. All five tools
   were confirmed present inside the installed copy on the live run.

7. `test_plugin_details_registers_every_event_the_clone_installer_wires`
   Parse the `Hooks (` line of the kept `claude plugin details` stdout: take
   the integer in the parentheses and the comma separated names after it,
   stopping at two or more consecutive spaces so a trailing parenthetical note
   is not swallowed (today the line ends with a note about harness only cost).
   PASS when the integer equals the number of HOOK_EVENTS parsed from
   `scripts/install.py` and the name set equals that event set. FAIL printing
   the whole line. This is the only assertion that observes what the RUNTIME
   registered rather than what a file declares, which is why it is worth the
   brittleness. If the line format ever changes the test fails loudly instead
   of passing on a regex that matched nothing, so the parse must assert it
   found the line before asserting anything about it.

8. `test_plugin_details_inventory_counts_the_commands_and_the_skill`
   PASS when the integer on the `Skills (` line equals
   `len(glob(commands/*.md)) + len(plugin.json["skills"])`. Derived, never
   hardcoded: today that is 7 plus 1 equals 8, and the CLI printed 8. FAIL
   printing the line and both counts. This is the test that would have caught
   the drift between the 2026-07-31 evidence file, which recorded seven, and
   today's eight.

9. `test_no_machine_state_reaches_the_installed_copy`
   PASS when no name in COPY_EXCLUDE exists at the top level of `installPath`.
   FAIL naming each one found. Note for the builder, because it changes what
   this test means: on the live run the marketplace source was a DIRECTORY, and
   a directory source ships whatever is in that directory, including
   `STATE.md`, the `STATE.md.bak-*` files and `threads/`, all of which are
   gitignored and therefore would NOT be present on a GitHub sourced install.
   The temp copy procedure below excludes them for exactly that reason, so the
   fixture equals what a GitHub install delivers. Without the exclusion this
   test would fail on a fixture defect rather than on a product defect, and the
   suite would be teaching the reader to ignore it.

10. `test_the_source_tree_is_unchanged_by_the_whole_install_cycle`
    PASS when `cls.tree_before == cls.tree_after`. FAIL listing the paths added,
    removed or changed. THIS IS THE CONSTRAINT 1 TEST MADE EXECUTABLE. The
    earlier packaging suite built in tree and left `build/` and an `.egg-info`
    behind; both were gitignored so `git status` read clean, and
    `scripts/verify-install.sh` then reported 26 EXTRA files, a state its own
    output calls the shape of a planted backdoor. A comment saying "we copy
    first" is a promise; this test is the check.

### Class C: TestPluginUninstallLeavesNoTrace

Its own install cycle, its own temp directory and fake HOME, same skip rule.
It exists as a separate class rather than as an eleventh method in class B
because it must run AFTER a full uninstall, and unittest orders methods
alphabetically within a class, which is not an ordering anyone should rely on.

1. `test_uninstall_then_marketplace_remove_leaves_nothing_installed`
   After `claude plugin uninstall brotherme -y` and
   `claude plugin marketplace remove brotherme-marketplace`, PASS when
   `claude plugin list --json` parses to an empty list, and
   `$HOME/.claude/settings.json` parses to an object whose `enabledPlugins` and
   `extraKnownMarketplaces` are both empty. FAIL printing the settings file.
   Both were confirmed empty after the live cycle.

2. `test_the_uninstall_never_touched_the_marketplace_source_directory`
   PASS when the fingerprint of the temp COPY is unchanged across the install
   and uninstall. FAIL naming what changed. The concern is real rather than
   theoretical: `known_marketplaces.json` records `installLocation` as the
   source directory itself, so an uninstall that decided to clean its source
   would be deleting a user directory.

## The environment pinning block

Reproduce this verbatim in `setUpClass`, and pass `env=cls.env` to EVERY
subprocess the suite spawns without exception. It is copied in shape from
`tools/test_bm_packaging_install.py` lines 98 to 105, which carries the
incident note in full.

    cls.tmp = tempfile.mkdtemp(prefix="bm_plugin_install_")
    cls.fake_home = os.path.join(cls.tmp, "home")
    os.makedirs(cls.fake_home)
    cls.env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": cls.fake_home,
        "BROTHERMODE_VAULT": os.path.join(cls.tmp, "vault"),
        "BROTHERSBE_VAULT": os.path.join(cls.tmp, "vault"),
    }

Why all three and not just HOME, stated so nobody trims it later:
`tools/bm_ledger.py` resolves its storage as
`os.environ.get("BROTHERMODE_VAULT", "~/BrotherModeVault")`, so the environment
variable WINS over HOME whenever the invoking shell has exported it, which it
has on any machine that has ever run this project's tooling. A HOME only
override was reproduced writing a live row into a real, non throwaway vault.
BROTHERSBE_VAULT is the sibling variable the same install may export. The dict
is built from scratch rather than by copying `os.environ` and overwriting
three keys, because a copy carries every other ambient variable a future tool
might read.

Two assertions make the pinning self checking rather than merely stated:
class B test 3 requires `installPath` to start with `cls.fake_home`, and a
`tearDownClass` that removes only `cls.tmp`. If the pin ever breaks, the suite
goes red on the isolation assertion before it can write anywhere real.

## The temp copy procedure

Never install from ROOT. Copy first, always, even though the plugin route was
observed to leave the tree untouched: the observation covers today's CLI, and
the test must not depend on a behaviour nobody controls.

    COPY_EXCLUDE = (".git", ".brothermode", "__pycache__", "threads",
                    ".superpowers", ".DS_Store", "STATE.md",
                    "build", "dist", "*.egg-info", "STATE.md.bak-*")

    cls.source = os.path.join(cls.tmp, "src")
    shutil.copytree(ROOT, cls.source,
                    ignore=shutil.ignore_patterns(*COPY_EXCLUDE))

Notes the builder must not lose:

- The first seven names are `scripts/install.py`'s own COPY_EXCLUDE_NAMES,
  confirmed at line 106 of that file, and class A test 6 fails if that list
  ever grows past this one.
- `build`, `dist` and `*.egg-info` are the packaging suite's exclusions and are
  kept for the same reason it keeps them.
- `STATE.md.bak-*` is added here on evidence: five such files exist at ROOT
  right now and all five landed in the installed copy on the live run. They are
  untracked, so a GitHub install would never carry them.
- `.git` is excluded because it is by far the largest thing in the tree and no
  step reads it. Measured: ROOT is 53M, the copy is 271 files.
- The copy takes well under a second on this machine, so no caching, no reuse
  between classes, and no module level fixture. One class, one copy.

## SUITES registration in tools/test_all.py

The mechanism, read rather than assumed. `_discover()` at line 479 lists every
`test_*.py` in `tools/` except `test_all.py` itself, and `_inventory_gate()` at
line 670 writes `REFUSING to run. These suites exist on disk but are not in the
gate` and returns exit 2 for anything on disk and absent from SUITES, before a
single test runs. The reverse case, a name in SUITES with no file, refuses the
same way. So adding the file without adding the tuple entry does not skip the
new suite; it hard blocks the entire gate at exit 2 with zero tests run.

Add exactly one line to the SUITES tuple, immediately after
`"test_bm_packaging_install.py"` and immediately before `"test_bm.py"`, which
puts it with the slow environment dependent suites at the end:

        "test_bm_plugin_install.py",

The comment above it, if the builder writes one, MUST CONTAIN NO APOSTROPHE AND
NO QUOTE CHARACTER OF ANY KIND. This is not style. `tools/bm_project_facts.py`
`_tuple_strings()` at line 115 extracts the SUITES entries with
`re.findall(r'["\']([^"\']+)["\']', ...)` over the raw tuple body, so a single
apostrophe in a comment inside the tuple opens a fake quoted region that
swallows real suite names, and
`tools/test_bm_docs.py::test_every_named_suite_file_exists` then fails on a
suite that does not exist. The tuple already carries two comments that say so
in their own text, at lines 94 and 110.

Downstream, `tools/bm_project_facts.py` will report `test_suites` as one higher
and list the new name in `test_suite_files`. Both are derived, so no document
needs editing: `test_the_tool_runs_and_prints_the_facts_docs_rely_on` asserts
only that the count equals the length of the list, and no active page pins a
suite count. Confirmed by reading both.

## The CI step in .github/workflows/tests.yml

The check that forces this, read rather than assumed: `_ci_inventory()` at line
450 parses the workflow into steps, ignores any step whose `if` is literally
false, and counts a suite only when a `run:` segment invokes it through a
Python interpreter. A suite merely MENTIONED, echoed, or commented out is not
counted, and `_inventory_gate()` then refuses with `These suites are in the
local gate but are never run by CI` at exit 2. The reverse, a CI step running a
suite not in SUITES, refuses as `phantom`.

Add the step to the `suite` job, immediately after the existing packaging
install step, which is the last step of that job today. That existing step is
the shape to mirror, quoted verbatim from lines 128 and 129:

      - name: Run the packaging install suite
        run: python3 tools/test_bm_packaging_install.py

The new step, in exactly that shape:

      - name: Run the plugin install suite
        run: python3 tools/test_bm_plugin_install.py

Placement consequences, all intended. The `suite` job runs the matrix
`os: [ubuntu-latest, macos-latest]` by `python: ["3.9", "3.x"]`, so the suite
runs on four legs. The `claude` binary is not present on a GitHub runner, so
class B and class C skip on all four and class A runs, which keeps the suite
green and above zero tests. The `gate` job needs no edit: it runs
`python3 tools/test_all.py`, which picks the new suite up from SUITES
automatically. Do not add the step to the `store` job, which is the Windows
carrying job: the plugin CLI has never been exercised on Windows here and
claiming that leg would be claiming evidence that does not exist.

## Observation protocol: the improvised README install

Deliverable: `docs/closure/protocols/2026-08-04-improvised-readme-install-protocol.md`.
It is a dated file under `docs/`, so it MUST carry `Status: CURRENT` at the
start of a line within its first 25 lines or
`tools/test_bm_docs.py::test_every_dated_document_declares_its_status_at_the_top`
fails. That test is recursive over `docs/`, confirmed by reading `dated_docs()`.

### What the probe agent is given, and nothing else

- The repository URL and only that: `https://github.com/khalilmaaouni/BrotherModeUp`.
  Confirmed as the `repository` and `homepage` field of `.claude-plugin/plugin.json`
  and as REPO_URL in `tools/bm_project_facts.py` line 76.
- A throwaway HOME that contains no prior Claude configuration, and the three
  vault variables pinned inside it, exactly as in the env block above.
- One sentence of task: install this and get it working.

Explicitly NOT given, and the protocol must say so in those words: the
documented install command in any form, the pinned tag, the marketplace name,
the plugin name, the README text pasted into the prompt, the existence of
`scripts/install.py`, the existence of `scripts/verify-install.sh`, and any hint
that more than one route exists. The whole value of the observation is that the
probe chooses. A probe that is told which route to take is re running the
automated test by hand.

### What must be recorded, per run

The record is a file at `docs/evidence/YYYY-MM-DD-improvised-readme-install-run-N.md`,
one per run, and it carries all seven of these:

1. Every command run, in order, with its exit code and the first line of its
   output. Including the failed ones, including the ones the probe retried, and
   including anything it ran to look around before installing. Order is part of
   the finding: a probe that read the README before running anything is a
   different result from one that guessed.
2. Every file written under the throwaway HOME. Because the HOME starts empty,
   the after state IS the answer: record a full recursive listing with sizes.
   Also record anything written outside that HOME, which is a defect if it
   happens and must be reported as one.
3. Every hook registered, from all three observation points, because they can
   disagree: `$HOME/.claude/settings.json` (what the clone installer writes),
   the `hooks/hooks.json` inside the installed plugin copy if a plugin route
   was taken, and the `Hooks (N)` line of `claude plugin details`. If the probe
   ended up with BOTH routes wired, say so loudly: that is the double wiring
   hazard recorded in `docs/evidence/2026-07-31-first-plugin-install.md` and in
   `docs/KNOWN-LIMITS.md`, and every hook then runs twice.
4. Whether it chose the pinned tag or the moving branch. Confirmed both exist:
   `git tag -l` resolves `v2.0.0-rc.13`, and `main` is the default branch. The
   answer is read from the actual command the probe ran, not inferred: a
   `git clone --branch v2.0.0-rc.13` is the pinned choice, a
   `git clone --branch main` or a bare `git clone` is the moving choice, and a
   `plugin marketplace add khalilmaaouni/BrotherModeUp` is a third answer,
   namely the moving default branch reached through the marketplace. Record
   which, and record whether the probe was aware there was a choice.
5. The verify-install result inside the installed copy: run
   `scripts/verify-install.sh` from inside whatever the probe installed, and
   record its exit code and its counts of OK, MISSING, EXTRA and MISMATCH
   verbatim. Confirmed present at `scripts/verify-install.sh` and confirmed
   shipped into a plugin install. A route that produces EXTRA files is a route
   whose own integrity check fails on first use, and that is precisely the
   finding this whole protocol is hunting.
6. Every question the probe asked, and every point where it stopped and could
   not proceed. Time or turn count to the first working `/brotherme` or
   `/brothermode` invocation.
7. A one line verdict: did an unaided reader end up with a working, verifiable
   install, yes or no, and by which route.

### Run discipline

Each run gets its own throwaway HOME and its own record file. Runs are never
merged into one document and a failed run is never deleted, since a probe that
gave up is the most informative result available. The protocol document states
that the observation has never been run under controlled conditions, and it
stays saying that until a numbered record exists next to it.

## Open items the builder should know about, not fix

- `tools/test_bm_packaging_install.py` has exactly one test class, and that
  class skips at `setUpClass` when pip cannot reach an index. Per the probe
  above, that produces `Ran 0 tests`, which `tools/test_all.py::_run_one` marks
  FAILED with `exited 0 but ran 0 tests`. The comment in SUITES at line 136
  claims it "reports SKIPPED rather than failing red", and that claim looks
  wrong. Unverified against a real offline run; flagged, not fixed, and outside
  this fence.
- `docs/closure/reports/2026-08-04-CHK-2B-packaging-counts.md` exists and its
  first 25 lines declare no status, which
  `test_every_dated_document_declares_its_status_at_the_top` refuses. It is
  another agent's file and outside this fence, but it will show up as a red
  docs suite until somebody adds a status line.
- The 2026-07-31 evidence file records `Skills (7)` and `Hooks (5)`. The live
  run today shows 8 and 6. The evidence file is honest for its own date; class B
  tests 7 and 8 are what keep the number current from now on.

## Files the builder may touch

/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_bm_plugin_install.py
/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_all.py
/Users/khalil.maaouni/Documents/BrotherModeUp/.github/workflows/tests.yml
/Users/khalil.maaouni/Documents/BrotherModeUp/docs/closure/protocols/2026-08-04-improvised-readme-install-protocol.md
