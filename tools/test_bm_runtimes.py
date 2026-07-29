#!/usr/bin/env python3
"""Suite for tools/bm_runtimes.py, the cross runtime adapter generator.

WHAT THIS SUITE IS ACTUALLY DEFENDING
  The generator's output is documentation that other people will act on. The
  failure mode is not a crash: it is a confident sentence that is false. Three
  shapes of false sentence are worth gating, and each has a test below that has
  been shown capable of failing:

    1. An INVENTED COMMAND. The adapter files tell five runtimes which
       BrotherMode commands to run. If one of those names drifts, every adapter
       teaches a command that does not exist, and the agent reading it reports
       a broken install rather than a renamed subcommand.

    2. DRIFT between the registry, the committed adapter files, and the
       capability table in docs/RUNTIMES.md. All three are generated from one
       registry precisely so they cannot disagree, which is only true while
       something checks.

    3. A CONFLATED CAPABILITY CLAIM. "This runtime has PreToolUse" and
       "BrotherMode's fence hook runs in this runtime" are different claims and
       only the first is verified anywhere but Claude Code. An adapter file that
       lost the second half of that sentence would talk a founder into wiring a
       gate that fails open while looking installed.

Python 3.9, standard library only. subprocess is used to drive the real CLI,
which is local execution, not a network call.

No em or en dashes anywhere in this file, its comments, or its output.
"""

import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RT_PATH = os.path.join(HERE, "bm_runtimes.py")

_spec = importlib.util.spec_from_file_location("bm_runtimes_under_test", RT_PATH)
rt_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rt_mod)

# Written as escapes on purpose: the no-dash rule applies to this file too, so
# the detector must not be the one place in the repository where a literal em or
# en dash lives. A grep for the character itself should find nothing, including
# here.
DASHES = (chr(0x2014), chr(0x2013))


def _run(args, cwd):
    return subprocess.run([sys.executable, RT_PATH] + list(args), cwd=cwd,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True)


def _new_project(d):
    """A throwaway project with a resolvable BrotherMode root, made the way the
    real CLI makes one rather than by hand."""
    subprocess.run(["git", "init", "-q", "."], cwd=d, check=True)
    with io.open(os.path.join(d, ".git", "info", "exclude"), "a") as f:
        f.write("/.brothermode\n")
    subprocess.run([sys.executable, os.path.join(HERE, "bm_store.py"), "init"],
                   cwd=d, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)


class TestRegistryIsStructurallySound(unittest.TestCase):

    def test_check_registry_passes_on_the_shipped_registry(self):
        rt_mod._check_registry()

    def test_no_two_runtimes_share_a_staging_filename(self):
        # Several runtimes share a DESTINATION (AGENTS.md is read by Codex,
        # Copilot and Qwen), so the staging names are the only thing keeping
        # one runtime's file from silently overwriting another's.
        names = [r["staging_name"] for r in rt_mod.RUNTIMES]
        self.assertEqual(len(names), len(set(names)), names)

    def test_every_runtime_carries_at_least_one_source_url(self):
        for r in rt_mod.RUNTIMES:
            self.assertTrue(r["sources"], "%s has no source" % r["key"])
            for label, url in r["sources"]:
                self.assertTrue(url.startswith("https://"),
                                "%s: %r is not an https URL" % (r["key"], url))
                self.assertTrue(label.strip(), "%s: source has no label" % r["key"])

    def test_hook_entries_carry_their_own_source(self):
        # The hook facts came off DIFFERENT pages than the instruction file
        # facts for every runtime that has them, so they carry their own URL
        # rather than inheriting one that does not mention hooks at all.
        for r in rt_mod.RUNTIMES:
            if r["hooks"] is None:
                continue
            label, url = r["hooks"]["source"]
            self.assertTrue(url.startswith("https://"), "%s: %r" % (r["key"], url))
            self.assertTrue(r["hooks"]["events"], "%s lists no events" % r["key"])
            self.assertTrue(r["hooks"]["config"].strip())

    def test_calibrated_check_registry_catches_a_duplicate_staging_name(self):
        # CALIBRATION: reinject the defect the guard exists for onto the real
        # product symbol, and prove the guard fails for that reason.
        original = rt_mod.RUNTIMES
        dup = dict(original[1])
        dup["key"] = "clone"
        dup["staging_name"] = original[0]["staging_name"]
        rt_mod.RUNTIMES = original + (dup,)
        try:
            with self.assertRaises(ValueError) as cm:
                rt_mod._check_registry()
            self.assertIn("same staging filename", str(cm.exception))
        finally:
            rt_mod.RUNTIMES = original
        rt_mod._check_registry()  # restored, and passing again

    def test_calibrated_check_registry_catches_an_unverified_entry_with_no_reason(self):
        original = rt_mod.RUNTIMES
        bad = dict(original[0])
        bad["key"] = "mystery"
        bad["staging_name"] = "mystery.md"
        bad["verified"] = False
        bad["reason"] = ""
        rt_mod.RUNTIMES = original + (bad,)
        try:
            with self.assertRaises(ValueError) as cm:
                rt_mod._check_registry()
            self.assertIn("states no reason", str(cm.exception))
        finally:
            rt_mod.RUNTIMES = original
        rt_mod._check_registry()


class TestNoInventedCommandNames(unittest.TestCase):
    """GUARD 1. Every BrotherMode command the adapters teach must be a real
    dispatch key in the module they name."""

    def _assert_surface_is_real(self, surface):
        missing = []
        for mod, _purpose, cmds in surface:
            src = io.open(os.path.join(HERE, mod), encoding="utf-8").read()
            for c in cmds:
                if '"%s"' % c not in src:
                    missing.append("%s: %s" % (mod, c))
        return missing

    def test_every_command_the_adapters_teach_exists_in_its_module(self):
        missing = self._assert_surface_is_real(rt_mod.CLI_SURFACE)
        self.assertEqual(
            missing, [],
            "the adapter files would teach these commands, but they are not "
            "dispatch keys in the named module: %s. Either the command was "
            "renamed (update CLI_SURFACE) or it was invented." % missing)

    def test_the_modules_the_adapters_name_all_exist(self):
        for mod, _p, _c in rt_mod.CLI_SURFACE:
            self.assertTrue(os.path.exists(os.path.join(HERE, mod)),
                            "CLI_SURFACE names %s, which does not exist" % mod)

    def test_calibrated_an_invented_command_is_caught(self):
        # CALIBRATION: put a command that does not exist into the real product
        # symbol's shape and prove the checker reports it. Without this, a
        # checker that silently found nothing would pass forever.
        fake = (("bm_store.py", "made up", ("claim", "definitely-not-a-command")),)
        missing = self._assert_surface_is_real(fake)
        self.assertEqual(missing, ["bm_store.py: definitely-not-a-command"])
        # restore is implicit (the real symbol was never mutated), so re-prove
        # the real surface still passes
        self.assertEqual(self._assert_surface_is_real(rt_mod.CLI_SURFACE), [])


class TestCommittedOutputMatchesTheRegistry(unittest.TestCase):
    """GUARD 2, the drift gate. docs/RUNTIMES.md and docs/runtimes/*.md are
    committed, so a reader sees them without running anything. That is only
    safe while they are what the generator would produce right now."""

    def test_check_passes_against_the_real_repository(self):
        r = _run(["check", "--root", ROOT], ROOT)
        self.assertEqual(r.returncode, 0,
                         "committed adapters or docs/RUNTIMES.md have drifted "
                         "from tools/bm_runtimes.py. Run `python3 "
                         "tools/bm_runtimes.py emit`.\n%s%s" % (r.stdout, r.stderr))
        self.assertIn("check OK", r.stdout)

    def test_calibrated_a_hand_edited_capability_table_is_reported_stale(self):
        # CALIBRATION: reinject the exact defect (a capability table that no
        # longer matches the registry) by making the REAL renderer produce
        # different bytes, and prove `check` names the file and exits nonzero.
        original = rt_mod.render_runtimes_doc
        rt_mod.render_runtimes_doc = lambda tp: original(tp) + "\nhand edited\n"
        try:
            code = rt_mod.cmd_check(["--root", ROOT])
        finally:
            rt_mod.render_runtimes_doc = original
        self.assertEqual(code, 1, "REINJECTION CHECK: with the renderer and the "
                                  "committed file disagreeing, check must fail")
        # RESTORE, and prove it passes again for the right reason.
        self.assertEqual(rt_mod.cmd_check(["--root", ROOT]), 0)

    def test_calibrated_a_missing_adapter_file_is_reported(self):
        original = rt_mod.RUNTIMES
        ghost = dict(original[0])
        ghost["key"] = "ghost"
        ghost["staging_name"] = "ghost.NOT-EMITTED.md"
        rt_mod.RUNTIMES = original + (ghost,)
        try:
            code = rt_mod.cmd_check(["--root", ROOT])
        finally:
            rt_mod.RUNTIMES = original
        self.assertEqual(code, 1, "REINJECTION CHECK: a registry entry with no "
                                  "committed file must be reported MISSING")
        self.assertEqual(rt_mod.cmd_check(["--root", ROOT]), 0)


class TestCapabilityClaimsStaySeparate(unittest.TestCase):
    """GUARD 3. 'has hook points' and 'BrotherMode's hooks work here' are two
    claims, and only the first is verified outside Claude Code."""

    def _render(self, r):
        return rt_mod.render_runtime_file(r, "tools")

    def test_a_runtime_with_hook_points_never_claims_brothermode_hooks_work(self):
        for r in rt_mod.RUNTIMES:
            if r["hooks"] is None:
                continue
            text = self._render(r)
            self.assertIn("UNVERIFIED", text,
                          "%s lists hook points; the file must say BrotherMode "
                          "hook compatibility is unverified" % r["key"])
            self.assertIn("docs/HOOKS.md", text,
                          "%s must point at the contract its hooks would have "
                          "to match" % r["key"])

    def test_a_runtime_without_hook_points_says_the_fence_is_advisory(self):
        for r in rt_mod.RUNTIMES:
            if r["hooks"] is not None:
                continue
            text = self._render(r)
            self.assertIn("advisory", text.lower(),
                          "%s has no hook points, so the file must not let a "
                          "reader believe the fence is enforced there" % r["key"])

    def test_every_capability_table_row_names_a_real_instruction_file(self):
        # P16 regression, and the reason this assertion is per CELL rather than
        # per row: the table cell used to be destinations[0].split(".")[0],
        # which truncates a prose sentence at the dot inside the FILENAME.
        # Copilot's cell rendered EMPTY (its path starts ".github/..."), and
        # AGENTS.md, QWEN.md and IFLOW.md all lost their extension. Every row
        # was present the whole time, so a row count test passed throughout.
        doc = rt_mod.render_runtimes_doc("tools")
        rows = {}
        for line in doc.splitlines():
            if line.startswith("| ") and line.count("|") >= 6:
                cells = [c.strip() for c in line.strip("|").split("|")]
                rows[cells[0]] = cells[1]
        for r in rt_mod.RUNTIMES:
            self.assertIn(r["title"], rows)
            cell = rows[r["title"]]
            self.assertTrue(cell, "%s has an EMPTY instruction file cell; a "
                                  "founder reads that as 'no instruction file'"
                                  % r["title"])
            self.assertIn(r["install_file"], cell,
                          "%s cell %r does not carry the registry's "
                          "install_file %r" % (r["title"], cell,
                                               r["install_file"]))
            self.assertTrue(cell.count(".md") >= 1,
                            "%s cell %r lost its file extension" % (r["title"],
                                                                    cell))

    def test_the_capability_table_has_one_row_per_runtime_plus_claude_code(self):
        doc = rt_mod.render_runtimes_doc("tools")
        for r in rt_mod.RUNTIMES:
            self.assertIn("| %s |" % r["title"], doc,
                          "%s is missing from the capability table" % r["title"])
        self.assertIn("| Claude Code |", doc,
                      "the one runtime with verified hook support must be in "
                      "the table, or the table reads as if nothing works")

    def test_every_generated_file_carries_its_source_url(self):
        for r in rt_mod.RUNTIMES:
            text = self._render(r)
            for _label, url in r["sources"]:
                self.assertIn(url, text,
                              "%s does not cite %s" % (r["key"], url))
            self.assertIn(rt_mod.VERIFIED_ON, text)

    def test_an_unverified_runtime_ships_marked_generic_with_its_reason(self):
        # No shipped runtime is unverified today, so the GENERIC path would
        # otherwise be dead code that nobody notices is broken until the first
        # time it matters.
        synth = dict(rt_mod.RUNTIMES[0])
        synth["key"] = "synthetic"
        synth["title"] = "Synthetic Runtime"
        synth["verified"] = False
        synth["reason"] = "no vendor documentation page could be opened"
        text = rt_mod.render_runtime_file(synth, "tools")
        self.assertIn("STATUS: GENERIC, NOT VERIFIED.", text)
        self.assertIn("no vendor documentation page could be opened", text)
        self.assertIn("Treat the destination below as a guess", text)

    def test_generated_output_contains_no_em_or_en_dashes(self):
        blobs = [rt_mod.render_runtimes_doc("tools")]
        blobs += [self._render(r) for r in rt_mod.RUNTIMES]
        blobs.append(io.open(RT_PATH, encoding="utf-8").read())
        for b in blobs:
            for d in DASHES:
                self.assertNotIn(d, b, "an em or en dash reached generated output")

    def test_generated_files_teach_no_flag_names(self):
        # The adapters name subcommands and tell the agent to run --help. A
        # generated "--files" that got renamed is exactly the invented flag
        # problem this project already shipped once.
        for r in rt_mod.RUNTIMES:
            text = self._render(r)
            for line in text.splitlines():
                for tok in line.split():
                    # `-->` closes the generated HTML header comments and is
                    # not a flag; a flag has a letter after the two dashes.
                    if tok.startswith("--") and len(tok) > 2 and tok[2].isalpha():
                        self.assertIn(
                            tok.strip(".,`"), ("--help", "--runtime"),
                            "%s teaches the flag %s; adapters may only name "
                            "--help and the regeneration command" % (r["key"], tok))


class TestEmitIsNonDestructiveAndRefusesCleanly(unittest.TestCase):

    def test_emit_never_writes_the_destination_paths(self):
        # The install map is advice, not an action. A generator that wrote
        # AGENTS.md at a repository root would destroy real content the first
        # time somebody ran it in a project that already had one.
        with tempfile.TemporaryDirectory() as d:
            _new_project(d)
            agents = os.path.join(d, "AGENTS.md")
            with io.open(agents, "w", encoding="utf-8") as f:
                f.write("FOUNDER CONTENT THAT MUST SURVIVE\n")
            os.makedirs(os.path.join(d, ".github"))
            copilot = os.path.join(d, ".github", "copilot-instructions.md")
            with io.open(copilot, "w", encoding="utf-8") as f:
                f.write("EXISTING COPILOT RULES\n")
            r = _run(["emit"], d)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(io.open(agents).read(),
                             "FOUNDER CONTENT THAT MUST SURVIVE\n")
            self.assertEqual(io.open(copilot).read(), "EXISTING COPILOT RULES\n")
            for rr in rt_mod.RUNTIMES:
                self.assertTrue(os.path.exists(
                    os.path.join(d, "docs", "runtimes", rr["staging_name"])))

    def test_emit_refuses_to_overwrite_a_hand_written_capability_table(self):
        # P16 regression. cmd_emit computed the capability table path from ROOT
        # unconditionally, so a founder's hand written docs/RUNTIMES.md was
        # destroyed with no backup and no warning, WHILE the banner printed
        # "an existing AGENTS.md or rules file is never clobbered".
        with tempfile.TemporaryDirectory() as d:
            _new_project(d)
            os.makedirs(os.path.join(d, "docs"))
            doc = os.path.join(d, "docs", "RUNTIMES.md")
            with io.open(doc, "w", encoding="utf-8") as f:
                f.write("FOUNDER HAND WRITTEN RUNTIMES NOTES\n")
            r = _run(["emit"], d)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("refused", r.stderr)
            self.assertEqual(io.open(doc, encoding="utf-8").read(),
                             "FOUNDER HAND WRITTEN RUNTIMES NOTES\n",
                             "the founder's file was overwritten")
            self.assertFalse(os.path.exists(os.path.join(d, "docs", "runtimes")),
                             "a refused emit must write nothing at all, not "
                             "part of the staging directory")

    def test_out_keeps_every_written_file_inside_the_named_directory(self):
        # P16 regression. --out redirected the adapter files only; the
        # capability table still went to <root>/docs/RUNTIMES.md, a file
        # OUTSIDE the directory the founder named as the scratch target.
        with tempfile.TemporaryDirectory() as d:
            _new_project(d)
            staging = os.path.join(d, "scratch")
            os.makedirs(staging)
            r = _run(["emit", "--out", staging], d)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue(os.path.exists(os.path.join(staging, "RUNTIMES.md")))
            self.assertFalse(
                os.path.exists(os.path.join(d, "docs", "RUNTIMES.md")),
                "--out must not write anything outside the named directory")
            self.assertEqual(_run(["check", "--out", staging], d).returncode, 0,
                             "check must look where emit actually wrote")

    def test_emit_is_deterministic(self):
        with tempfile.TemporaryDirectory() as d:
            _new_project(d)
            _run(["emit"], d)
            first = {}
            base = os.path.join(d, "docs", "runtimes")
            for n in sorted(os.listdir(base)):
                first[n] = io.open(os.path.join(base, n), encoding="utf-8").read()
            _run(["emit"], d)
            for n, text in first.items():
                self.assertEqual(
                    io.open(os.path.join(base, n), encoding="utf-8").read(), text,
                    "%s changed between two emits; a nondeterministic generator "
                    "makes the drift gate useless" % n)

    def test_emit_leaves_no_temp_files_behind(self):
        with tempfile.TemporaryDirectory() as d:
            _new_project(d)
            _run(["emit"], d)
            leftovers = [n for n in os.listdir(os.path.join(d, "docs", "runtimes"))
                         if n.endswith(".tmp")]
            self.assertEqual(leftovers, [])

    def test_an_unrecognized_flag_is_refused_and_nothing_is_written(self):
        with tempfile.TemporaryDirectory() as d:
            _new_project(d)
            r = _run(["emit", "--runtimes", "codex"], d)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("unrecognized flag", r.stderr)
            self.assertFalse(os.path.exists(os.path.join(d, "docs", "runtimes")))

    def test_an_unknown_runtime_is_refused_and_nothing_is_written(self):
        with tempfile.TemporaryDirectory() as d:
            _new_project(d)
            r = _run(["emit", "--runtime", "cursor"], d)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("unknown runtime", r.stderr)
            self.assertFalse(os.path.exists(os.path.join(d, "docs", "runtimes")))

    def test_a_partial_emit_does_not_rewrite_the_capability_table(self):
        # The table describes EVERY runtime. Rewriting it from a one runtime
        # emit would silently drop five rows.
        with tempfile.TemporaryDirectory() as d:
            _new_project(d)
            r = _run(["emit", "--runtime", "codex"], d)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertFalse(os.path.exists(os.path.join(d, "docs", "RUNTIMES.md")))
            self.assertIn("capability table NOT refreshed", r.stdout)

    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            _new_project(d)
            r = _run(["emit", "--dry-run"], d)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertFalse(os.path.exists(os.path.join(d, "docs", "runtimes")))
            self.assertIn("DRY RUN", r.stdout)

    def test_emit_refuses_outside_a_brothermode_project(self):
        with tempfile.TemporaryDirectory() as d:
            env_free = os.path.join(d, "nothing", "here")
            os.makedirs(env_free)
            r = subprocess.run(
                [sys.executable, RT_PATH, "emit"], cwd=env_free,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                universal_newlines=True,
                env=dict((k, v) for k, v in os.environ.items()
                         if k != "BROTHERMODE_ROOT"))
            # A tmpdir is not a git repository and has no marker, so nothing
            # anchors a project. The refusal must be explicit, not a silent
            # emit into the current directory.
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("refused", r.stderr)

    def test_root_resolution_does_not_depend_on_the_calling_subdirectory(self):
        with tempfile.TemporaryDirectory() as d:
            _new_project(d)
            sub = os.path.join(d, "a", "b")
            os.makedirs(sub)
            top = _run(["emit", "--dry-run"], d)
            nested = _run(["emit", "--dry-run"], sub)
            self.assertEqual(top.stdout.splitlines()[0],
                             nested.stdout.splitlines()[0],
                             "the resolved root must not depend on cwd")


class TestListAndHelp(unittest.TestCase):

    def test_list_json_names_every_runtime_and_its_hook_status(self):
        import json
        with tempfile.TemporaryDirectory() as d:
            r = _run(["list", "--json"], d)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            data = json.loads(r.stdout)
            self.assertEqual(len(data["runtimes"]), len(rt_mod.RUNTIMES))
            for row in data["runtimes"]:
                self.assertIn(row["brothermode_hooks"],
                              ("unverified", "not applicable"),
                              "no row may claim BrotherMode hooks are verified "
                              "outside Claude Code: %r" % row)

    def test_list_works_with_no_project_at_all(self):
        # `list` is pure registry, so it must answer from anywhere. A founder
        # evaluating BrotherMode has not run init yet.
        with tempfile.TemporaryDirectory() as d:
            r = _run(["list"], d)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("Codex", r.stdout)

    def test_help_states_the_real_default_staging_directory(self):
        # P16 regression. main() prints the module docstring verbatim as the
        # primary help surface, and that docstring said the default staging
        # directory was ".brothermode/runtimes" while DEFAULT_STAGING was
        # "docs/runtimes". Those differ in the way that matters most here:
        # .brothermode is git excluded, docs/runtimes is committed and ships.
        doc = rt_mod.__doc__ or ""
        self.assertIn(rt_mod.DEFAULT_STAGING.replace(os.sep, "/"), doc,
                      "the help text must name the directory emit actually "
                      "writes to")
        self.assertNotIn(".brothermode/runtimes", doc,
                         "the help text names a directory emit never uses")
        with tempfile.TemporaryDirectory() as d:
            r = _run(["--help"], d)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn(rt_mod.DEFAULT_STAGING.replace(os.sep, "/"), r.stdout)

    def test_unknown_command_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            r = _run(["install"], d)
            self.assertEqual(r.returncode, 2)
            self.assertIn("unknown command", r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=1)
