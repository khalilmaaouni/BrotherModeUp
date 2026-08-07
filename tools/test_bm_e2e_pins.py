#!/usr/bin/env python3
"""tools/test_bm_e2e_pins.py: pins for scripts/bench_e2e_lifecycle.py (FENCE
V10, BrotherModeUp-handovers/v3/WAVE-CD-BRIEFS.md, agent e2e-canary).

WHAT THIS IS
  A deterministic, `claude`-binary-free pin suite: it imports
  scripts/bench_e2e_lifecycle.py BY PATH and asserts its STEP_NAMES,
  NINE_CANONICAL_SKILLS, DELIVER_REFUSAL_MARKER and V2_TAG stay exactly
  what the live canary needs them to be, without ever running the live
  canary itself (which needs a real `claude` binary, a real `git clone`,
  and several seconds of real subprocess work). This is the fast,
  always-green half of the pair; `python3 scripts/bench_e2e_lifecycle.py`
  is the slow, real half. This file is registered wherever the ORCHESTRATOR
  wires suite discovery; the live canary stays unregistered on purpose (a
  machine with no `claude` binary must not turn a suite red for a reason
  outside its control), matching how tools/test_all.py never runs
  scripts/benchmark_comparative.py's own probe_installed directly either.

WHAT EACH PIN PROTECTS AGAINST
  - STEP_NAMES: a step added, removed, reordered or renamed in the live
    canary without a matching, deliberate edit here. The count is pinned
    (eighteen) and so is the exact wording of the negative-path step and
    the migration-instruction step, the two steps the FENCE V10 brief
    names by name. A regression test also pins the exact ordering bug
    this suite's own construction hit once for real (a task seeded
    before the project row it references existed, an sqlite3
    IntegrityError): 'brothermode_cli start' must precede 'ready-state
    task seeded', which must precede 'brothermode_cli status'.
  - NINE_CANONICAL_SKILLS: drift from the actual public skill surface.
    Cross-checked against the real skills/ directory tree minus
    V3-FREEZE-2026-08-07.md ruling B5's own hidden-skill list, and
    against docs/brand/IDENTITY-CONTRACT.md's own canonical-skill line,
    never retyped as a third, independent guess.
  - DELIVER_REFUSAL_MARKER: drift from tools/bm_project.py's own refusal
    wording. Cross-checked by grepping that file's actual source for the
    marker, so a wording change there breaks THIS test before it can
    silently break the live canary's own assertion.
  - V2_TAG / V2_PLUGIN_NAME / V2_EXPECTED_VERSION: the upgrade leg's
    pinned historical release must still exist as a real, resolvable git
    tag in this repository, and that tag's own plugin.json must still
    name the plugin identity the live canary expects to install.
  - no live `claude -p` session: the FENCE V10 brief is explicit that
    this canary "drives the CLI boundary and the plugin CLI, staying
    deterministic" and that live claude -p turns are not required beyond
    what scripts/benchmark_comparative.py's probe_installed already
    proves. This test greps the live canary's own source and fails if a
    headless-prompt invocation of the claude binary (-p / --print) is
    ever added to it.

Python 3.9, standard library only. No `claude` binary anywhere in this
file. `git` is used read-only (rev-parse, show) and every test that needs
it skips, never fails, when no `git` binary is on PATH, matching this
project's own posture for an absent optional precondition.

No em or en dashes anywhere in this file or its output.
"""

import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LIFECYCLE_PY = os.path.join(ROOT, "scripts", "bench_e2e_lifecycle.py")
BM_PROJECT_PY = os.path.join(ROOT, "tools", "bm_project.py")
IDENTITY_CONTRACT = os.path.join(ROOT, "docs", "brand", "IDENTITY-CONTRACT.md")

EXPECTED_STEP_COUNT = 18

_LIFECYCLE_MODULE = None


def _lifecycle_module():
    """scripts/bench_e2e_lifecycle.py, imported once by PATH and cached:
    the same importlib.util.spec_from_file_location technique
    tools/test_bm_plugin_install.py already uses for scripts/install.py,
    reused here so this suite reads the SAME constants the live canary
    itself defines, never a second, independently retyped copy of them."""
    global _LIFECYCLE_MODULE
    if _LIFECYCLE_MODULE is None:
        spec = importlib.util.spec_from_file_location(
            "bm_e2e_pins_lifecycle", LIFECYCLE_PY)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _LIFECYCLE_MODULE = mod
    return _LIFECYCLE_MODULE


def _read(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


_ADJACENT_STRING_LITERALS = re.compile(r'"\s*\n\s*"')


def _concat_adjacent_string_literals(text):
    """A crude but sufficient approximation of Python's own adjacent
    string-literal concatenation, applied to raw SOURCE TEXT rather than a
    parsed AST: collapses a closing double-quote, the whitespace (newline
    plus indentation) between two adjacent string literals, and the
    following opening double-quote, into nothing. tools/bm_project.py
    spells its deliver refusal as two literals across two lines (each one
    independently readable, but only continuous once Python concatenates
    them at compile time); this lets a plain substring search find the
    marker the way the RUNTIME string actually reads, without executing
    or evaluating any of that file's code."""
    return _ADJACENT_STRING_LITERALS.sub("", text)


def _skill_root_entries():
    skills_root = os.path.join(ROOT, "skills")
    return sorted(d for d in os.listdir(skills_root)
                 if os.path.isdir(os.path.join(skills_root, d)))


class TestTheLiveCanaryFileExists(unittest.TestCase):
    """Runs unconditionally: no `claude` binary, no network, no install.
    Also the guarantee that this suite always runs at least a handful of
    real tests even on a machine with nothing else installed, the same
    posture tools/test_bm_plugin_install.py's own class A documents."""

    def test_the_file_exists_and_imports_cleanly(self):
        self.assertTrue(os.path.isfile(LIFECYCLE_PY), LIFECYCLE_PY)
        mod = _lifecycle_module()
        for attr in ("STEP_NAMES", "TOTAL_STEPS", "NINE_CANONICAL_SKILLS",
                    "DELIVER_REFUSAL_MARKER", "V2_TAG", "V2_PLUGIN_NAME",
                    "V2_MARKETPLACE_NAME", "V2_PLUGIN_SPEC",
                    "V2_EXPECTED_VERSION", "run_lifecycle", "main"):
            self.assertTrue(hasattr(mod, attr),
                           "scripts/bench_e2e_lifecycle.py has no %s" % attr)


class TestStepListIsPinned(unittest.TestCase):
    def test_step_count(self):
        mod = _lifecycle_module()
        self.assertEqual(EXPECTED_STEP_COUNT, len(mod.STEP_NAMES),
                         mod.STEP_NAMES)
        self.assertEqual(mod.TOTAL_STEPS, len(mod.STEP_NAMES))

    def test_step_names_are_unique(self):
        mod = _lifecycle_module()
        self.assertEqual(
            len(mod.STEP_NAMES), len(set(mod.STEP_NAMES)),
            "STEP_NAMES has a duplicate entry: %r" % (mod.STEP_NAMES,))

    def test_the_migration_instruction_step_is_named_exactly(self):
        """The FENCE V10 brief's own words: 'document the uninstall-v2-
        first instruction the canary encodes.' Pinned verbatim so a
        rewording here is a deliberate edit, not an accident."""
        mod = _lifecycle_module()
        self.assertIn(
            "v2 uninstalled first (documented migration instruction: "
            "uninstall v2, then install v3)", mod.STEP_NAMES)

    def test_the_negative_deliver_step_is_named_exactly(self):
        """The FENCE V10 brief's own words: 'prove incomplete evidence
        blocks deliver (negative path, expect the refusal).'"""
        mod = _lifecycle_module()
        self.assertIn(
            "brothermode_cli deliver refused (incomplete evidence blocks "
            "delivery)", mod.STEP_NAMES)

    def test_start_precedes_task_seeding_precedes_status(self):
        """Regression pin for the exact bug this file's own construction
        hit once for real: seeding a task before the project row it
        references existed raised sqlite3.IntegrityError (FOREIGN KEY
        constraint failed) out of tools/bm_store.py's create_task. 'start'
        must run before the task it seeds can reference a project, and
        the seeded task must exist before 'status'/'next' read it back."""
        mod = _lifecycle_module()
        names = mod.STEP_NAMES
        self.assertIn("brothermode_cli start", names)
        self.assertIn("ready-state task seeded", names)
        self.assertIn("brothermode_cli status", names)
        i_start = names.index("brothermode_cli start")
        i_seed = names.index("ready-state task seeded")
        i_status = names.index("brothermode_cli status")
        self.assertLess(i_start, i_seed,
                        "start must run before the task it seeds can "
                        "reference a project (regression: sqlite3 "
                        "IntegrityError, FOREIGN KEY constraint failed)")
        self.assertLess(i_seed, i_status,
                        "the task must be seeded before status/next read "
                        "it back")

    def test_uninstall_v2_step_precedes_v3_install_step(self):
        """Ruling B4 (V3-FREEZE-2026-08-07.md): uninstall v2 BEFORE
        installing v3, so the two plugins' hooks are never both wired."""
        mod = _lifecycle_module()
        names = mod.STEP_NAMES
        i_v2_un = next(i for i, n in enumerate(names)
                      if n.startswith("v2 uninstalled first"))
        i_v3_in = next(i for i, n in enumerate(names)
                      if n == "v3 installed the shipped way")
        self.assertLess(
            i_v2_un, i_v3_in,
            "ruling B4's migration instruction (uninstall v2, THEN "
            "install v3) must be encoded in that order")

    def test_single_hook_chain_step_follows_the_v3_install(self):
        mod = _lifecycle_module()
        names = mod.STEP_NAMES
        i_v3_in = names.index("v3 installed the shipped way")
        i_single = next(i for i, n in enumerate(names)
                       if n.startswith("single hook chain proven"))
        self.assertLess(i_v3_in, i_single)


class TestNineCanonicalSkillsIsPinned(unittest.TestCase):
    def test_nine_entries_no_more_no_less(self):
        mod = _lifecycle_module()
        self.assertEqual(9, len(mod.NINE_CANONICAL_SKILLS),
                         mod.NINE_CANONICAL_SKILLS)

    def test_matches_the_skills_directory_minus_the_hidden_set(self):
        """V3-FREEZE-2026-08-07.md ruling B5: the public surface is the
        nine canonical skills; the full-auto trio (auto, auto-status,
        stop), the founder-mode quartet (brief, decisions, handback,
        handover-pack), and brotherme itself are hidden internal skills,
        preserved on disk but off the public slash surface. This test
        derives the expected nine STRUCTURALLY from skills/ rather than
        retyping a second independent list, so a skill added or removed
        from disk without a matching edit here fails loudly."""
        hidden = {"auto", "auto-status", "stop",
                 "brief", "decisions", "handback", "handover-pack",
                 "brotherme"}
        entries = set(_skill_root_entries())
        expected = tuple(sorted(entries - hidden))
        mod = _lifecycle_module()
        self.assertEqual(
            expected, tuple(sorted(mod.NINE_CANONICAL_SKILLS)),
            "skills/ minus the ruling B5 hidden set is %s, but "
            "NINE_CANONICAL_SKILLS is %s"
            % (expected, tuple(sorted(mod.NINE_CANONICAL_SKILLS))))

    def test_matches_the_identity_contract_doc(self):
        self.assertTrue(os.path.isfile(IDENTITY_CONTRACT), IDENTITY_CONTRACT)
        text = _read(IDENTITY_CONTRACT)
        self.assertIn("nine v3 canonical skills", text,
                      "docs/brand/IDENTITY-CONTRACT.md no longer names "
                      "'nine v3 canonical skills'; section 8 may have "
                      "been reworded")
        mod = _lifecycle_module()
        missing = [name for name in mod.NINE_CANONICAL_SKILLS
                  if (":%s" % name) not in text]
        self.assertEqual(
            [], missing,
            "docs/brand/IDENTITY-CONTRACT.md's own canonical-skill line "
            "is missing %s (or the doc's ':name' wording changed)"
            % missing)


class TestDeliverRefusalMarkerIsPinned(unittest.TestCase):
    def test_marker_is_a_substring_of_bm_projects_own_refusal_text(self):
        self.assertTrue(os.path.isfile(BM_PROJECT_PY), BM_PROJECT_PY)
        text = _concat_adjacent_string_literals(_read(BM_PROJECT_PY))
        mod = _lifecycle_module()
        self.assertIn(
            mod.DELIVER_REFUSAL_MARKER, text,
            "tools/bm_project.py no longer contains the exact refusal "
            "substring %r the live canary keys its negative-path "
            "assertion on; cmd_deliver's non-terminal-task refusal text "
            "may have been reworded" % mod.DELIVER_REFUSAL_MARKER)


class TestUpgradeLegTagIsPinned(unittest.TestCase):
    """Read-only `git` calls only (rev-parse, show); skips, never fails,
    when no `git` binary is on PATH, matching scripts/benchmark_comparative
    .py's own _git helper's posture for the same absent precondition."""

    def _git(self, *args):
        if shutil.which("git") is None:
            raise unittest.SkipTest("no git binary on PATH")
        return subprocess.run(["git"] + list(args), cwd=ROOT,
                             capture_output=True, text=True, timeout=30)

    def test_v2_tag_exists_and_resolves(self):
        mod = _lifecycle_module()
        r = self._git("rev-parse", "--verify", "refs/tags/%s" % mod.V2_TAG)
        self.assertEqual(
            0, r.returncode,
            "git tag %r does not resolve in this repository: %s"
            % (mod.V2_TAG, r.stdout + r.stderr))

    def test_v2_tags_own_manifest_matches_the_pinned_identity(self):
        mod = _lifecycle_module()
        r = self._git("show",
                      "%s:.claude-plugin/plugin.json" % mod.V2_TAG)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        try:
            manifest = json.loads(r.stdout)
        except ValueError as exc:
            self.fail("git show %s:.claude-plugin/plugin.json is not "
                     "valid JSON: %s" % (mod.V2_TAG, exc))
        self.assertEqual(mod.V2_PLUGIN_NAME, manifest.get("name"), manifest)
        self.assertEqual(mod.V2_EXPECTED_VERSION, manifest.get("version"),
                         manifest)
        self.assertEqual(
            mod.V2_PLUGIN_SPEC,
            "%s@%s" % (mod.V2_PLUGIN_NAME, mod.V2_MARKETPLACE_NAME))


class TestNoLiveClaudePromptSession(unittest.TestCase):
    """The FENCE V10 brief's own words: 'Live claude -p turns are NOT
    required beyond what probe_installed already proves; the lifecycle
    canary drives the CLI boundary and the plugin CLI, staying
    deterministic.' This test pins that scope decision structurally: the
    live canary's own source must never invoke the claude binary with a
    headless-prompt flag (-p / --print)."""

    HEADLESS_PROMPT_FLAG = re.compile(r'["\']-p["\']|--print\b')

    def test_the_live_canary_never_invokes_claude_dash_p(self):
        text = _read(LIFECYCLE_PY)
        offenders = [ln.strip() for ln in text.splitlines()
                    if self.HEADLESS_PROMPT_FLAG.search(ln)]
        self.assertEqual(
            [], offenders,
            "scripts/bench_e2e_lifecycle.py invokes claude with a "
            "headless-prompt flag, which the FENCE V10 brief says this "
            "canary must not do (that proof already exists in "
            "scripts/benchmark_comparative.py's probe_installed): %s"
            % offenders)


if __name__ == "__main__":
    unittest.main()
