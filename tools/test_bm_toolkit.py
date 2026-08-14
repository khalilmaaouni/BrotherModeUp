#!/usr/bin/env python3
"""Regression tests for tools/bm_toolkit.py, the capability inventory (F1
of docs/plan/TOOLKIT-PLAN-2026-08-12.md). Every fixture is a
tempfile.TemporaryDirectory() built to look like a `~/.claude` tree; the
real ~/.claude is NEVER read in a test, only in the orchestrator's separate
real-machine done-check commands.

Standard library only. Run: python3 tools/test_bm_toolkit.py
"""
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TOOL_PATH = os.path.join(HERE, "bm_toolkit.py")


def run_cli(*args):
    """Invoke the CLI as a real subprocess, with BROTHERMODE_ROOT scrubbed
    so a variable set on the developer's own machine can never leak into a
    test that expects an explicit --root to decide the outcome."""
    env = dict(os.environ)
    env.pop("BROTHERMODE_ROOT", None)
    return subprocess.run(
        [sys.executable, TOOL_PATH] + list(args),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        universal_newlines=True, cwd=ROOT, env=env)


def write_json(path, obj):
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)
    with io.open(path, "w", encoding="utf-8") as handle:
        json.dump(obj, handle)
    return path


def write_text(path, content="placeholder\n"):
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)
    with io.open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    return path


def make_plugin(home, marketplace, plugin_name, version, manifest=None,
                 hooks=None):
    """Build <home>/.claude/plugins/cache/<marketplace>/<plugin_name>/
    <version>/, optionally with a plugin.json manifest and a hooks.json.
    Returns the version directory path."""
    version_dir = os.path.join(
        home, ".claude", "plugins", "cache", marketplace, plugin_name, version)
    os.makedirs(version_dir, exist_ok=True)
    if manifest is not None:
        write_json(os.path.join(version_dir, ".claude-plugin", "plugin.json"),
                    manifest)
    if hooks is not None:
        write_json(os.path.join(version_dir, "hooks", "hooks.json"), hooks)
    return version_dir


def make_skill(home, skill_name, with_skill_md=True, hooks=None):
    skill_dir = os.path.join(home, ".claude", "skills", skill_name)
    os.makedirs(skill_dir, exist_ok=True)
    if with_skill_md:
        write_text(os.path.join(skill_dir, "SKILL.md"), "# %s\n" % skill_name)
    if hooks is not None:
        write_json(os.path.join(skill_dir, "hooks", "hooks.json"), hooks)
    return skill_dir


def write_user_settings(home, obj):
    return write_json(os.path.join(home, ".claude", "settings.json"), obj)


def write_claude_json(home, obj):
    return write_json(os.path.join(home, ".claude.json"), obj)


def minimal_home(tmp):
    """A home with just enough valid, empty surfaces that tests focused on
    one surface do not accidentally trip the all-unreadable NO-DATA case.
    Marketplaces cache and skills dirs are left absent (a valid empty
    answer); settings.json and .claude.json are written as valid, minimal
    files."""
    write_user_settings(tmp, {"enabledPlugins": {}})
    write_claude_json(tmp, {"mcpServers": {}})
    return tmp


class InventoryEnumerationTests(unittest.TestCase):
    """Test 1: a fixture home with 2 marketplaces and 3 plugins is fully
    enumerated (marketplace count, plugin count, per plugin fields)."""

    def test_two_marketplaces_three_plugins_fully_enumerated(self):
        with tempfile.TemporaryDirectory() as tmp:
            minimal_home(tmp)
            make_plugin(tmp, "alpha-market", "pluginA", "1.0.0",
                        manifest={"name": "pluginA", "version": "1.0.0"})
            make_plugin(tmp, "alpha-market", "pluginB", "2.0.0",
                        manifest={"name": "pluginB", "version": "2.0.0"})
            make_plugin(tmp, "beta-market", "pluginC", "0.1.0",
                        manifest={"name": "pluginC", "version": "0.1.0"})
            result = run_cli("json", "--home", tmp, "--root", tmp)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(len(data["marketplaces"]), 2)
        self.assertEqual(len(data["plugins"]), 3)
        names = sorted(p["name"] for p in data["plugins"])
        self.assertEqual(names, ["pluginA", "pluginB", "pluginC"])
        by_mkt = {m["name"]: m["plugin_count"] for m in data["marketplaces"]}
        self.assertEqual(by_mkt["alpha-market"], 2)
        self.assertEqual(by_mkt["beta-market"], 1)


class SameNameTwoVersionsTests(unittest.TestCase):
    """Test 2: the SAME plugin at two version directories yields TWO
    plugin records, not one (the real brothersbe 1.0.0-rc.1 / rc.38
    fixture named in the plan)."""

    def test_same_plugin_two_versions_yields_two_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            minimal_home(tmp)
            make_plugin(tmp, "brothersbe-market", "brothersbe", "1.0.0-rc.1",
                        manifest={"name": "brothersbe", "version": "1.0.0-rc.1"})
            make_plugin(tmp, "brothersbe-market", "brothersbe", "1.0.0-rc.38",
                        manifest={"name": "brothersbe", "version": "1.0.0-rc.38"})
            result = run_cli("json", "--home", tmp, "--root", tmp)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        data = json.loads(result.stdout)
        versions = sorted(p["version"] for p in data["plugins"])
        self.assertEqual(versions, ["1.0.0-rc.1", "1.0.0-rc.38"])
        self.assertEqual(len(data["plugins"]), 2)


class ManifestAbsentTests(unittest.TestCase):
    """Test 3: a plugin whose manifest is absent still yields a record,
    with manifest_present false and the version taken from the directory
    name."""

    def test_missing_manifest_falls_back_to_directory_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            minimal_home(tmp)
            make_plugin(tmp, "gamma-market", "no-manifest-plugin", "3.2.1")
            result = run_cli("json", "--home", tmp, "--root", tmp)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(len(data["plugins"]), 1)
        plugin = data["plugins"][0]
        self.assertFalse(plugin["manifest_present"])
        self.assertEqual(plugin["version"], "3.2.1")
        self.assertEqual(plugin["name"], "no-manifest-plugin")
        self.assertIsNone(plugin["description"])


class HookEventShapeTests(unittest.TestCase):
    """Test 4: hook events are collected from both the top-level-map shape
    and the {"hooks": {...}} wrapper shape, and non-capitalised keys are
    ignored."""

    def test_top_level_map_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            minimal_home(tmp)
            make_plugin(tmp, "mkt", "plug-flat", "1.0.0",
                        hooks={"SessionStart": [], "PreToolUse": [],
                               "description": "not an event"})
            result = run_cli("json", "--home", tmp, "--root", tmp)
        data = json.loads(result.stdout)
        events = data["plugins"][0]["hook_events"]
        self.assertEqual(sorted(events), ["PreToolUse", "SessionStart"])

    def test_wrapped_hooks_key_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            minimal_home(tmp)
            make_plugin(tmp, "mkt", "plug-wrapped", "1.0.0",
                        hooks={"hooks": {"Stop": [], "SubagentStop": []}})
            result = run_cli("json", "--home", tmp, "--root", tmp)
        data = json.loads(result.stdout)
        events = data["plugins"][0]["hook_events"]
        self.assertEqual(sorted(events), ["Stop", "SubagentStop"])


class EnabledPluginsTests(unittest.TestCase):
    """Test 5: a plugin absent from enabledPlugins reports enabled false;
    when settings.json is unreadable every plugin reports enabled null.
    null and false must never be conflated."""

    def test_absent_from_enabled_map_is_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_user_settings(tmp, {"enabledPlugins": {"other@mkt": True}})
            write_claude_json(tmp, {"mcpServers": {}})
            make_plugin(tmp, "mkt", "unenabled-plugin", "1.0.0",
                        manifest={"name": "unenabled-plugin", "version": "1.0.0"})
            result = run_cli("json", "--home", tmp, "--root", tmp)
        data = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIs(data["plugins"][0]["enabled"], False)

    def test_present_and_true_in_enabled_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_user_settings(
                tmp, {"enabledPlugins": {"enabled-plugin@mkt": True}})
            write_claude_json(tmp, {"mcpServers": {}})
            make_plugin(tmp, "mkt", "enabled-plugin", "1.0.0",
                        manifest={"name": "enabled-plugin", "version": "1.0.0"})
            result = run_cli("json", "--home", tmp, "--root", tmp)
        data = json.loads(result.stdout)
        self.assertIs(data["plugins"][0]["enabled"], True)

    def test_settings_json_unreadable_gives_null_for_every_plugin(self):
        with tempfile.TemporaryDirectory() as tmp:
            # settings.json deliberately corrupt; other 3 surfaces valid so
            # this is not the all-unreadable NO-DATA case.
            write_text(os.path.join(tmp, ".claude", "settings.json"),
                       "{ not json")
            write_claude_json(tmp, {"mcpServers": {}})
            make_plugin(tmp, "mkt", "some-plugin", "1.0.0",
                        manifest={"name": "some-plugin", "version": "1.0.0"})
            result = run_cli("json", "--home", tmp, "--root", tmp)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertIsNone(data["plugins"][0]["enabled"])
        reasons = [u["path"] for u in data["unreadable"]]
        self.assertTrue(any("settings.json" in p for p in reasons))


class SkillsTests(unittest.TestCase):
    """Test 6: skills with and without SKILL.md; a skill carrying its own
    hooks.json contributes hook events."""

    def test_skills_with_and_without_skill_md_and_own_hooks(self):
        with tempfile.TemporaryDirectory() as tmp:
            minimal_home(tmp)
            make_skill(tmp, "brothermode", with_skill_md=True,
                       hooks={"SessionStart": [], "Stop": []})
            make_skill(tmp, "no-doc-skill", with_skill_md=False)
            result = run_cli("json", "--home", tmp, "--root", tmp)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(len(data["skills"]), 2)
        by_name = {s["name"]: s for s in data["skills"]}
        self.assertTrue(by_name["brothermode"]["has_skill_md"])
        self.assertEqual(sorted(by_name["brothermode"]["hook_events"]),
                          ["SessionStart", "Stop"])
        self.assertFalse(by_name["no-doc-skill"]["has_skill_md"])
        self.assertEqual(by_name["no-doc-skill"]["hook_events"], [])


class McpServersTests(unittest.TestCase):
    """Test 7: mcpServers absent yields zero servers and NOT an error."""

    def test_mcp_servers_key_absent_is_zero_not_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_user_settings(tmp, {"enabledPlugins": {}})
            write_claude_json(tmp, {"someOtherKey": "irrelevant"})
            result = run_cli("json", "--home", tmp, "--root", tmp)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["mcp_servers"], [])
        paths = [u["path"] for u in data["unreadable"]]
        self.assertFalse(any(".claude.json" in p for p in paths))

    def test_mcp_servers_present_are_enumerated_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_user_settings(tmp, {"enabledPlugins": {}})
            write_claude_json(tmp, {"mcpServers": {"figma": {}, "perplexity": {}}})
            result = run_cli("json", "--home", tmp, "--root", tmp)
        data = json.loads(result.stdout)
        names = sorted(s["name"] for s in data["mcp_servers"])
        self.assertEqual(names, ["figma", "perplexity"])


class UnreadableJsonTests(unittest.TestCase):
    """Test 8: an unreadable JSON file (a corrupt plugin manifest) lands in
    unreadable with a reason and does not crash the run."""

    def test_corrupt_manifest_is_unreadable_not_a_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            minimal_home(tmp)
            version_dir = make_plugin(tmp, "mkt", "broken-plugin", "1.0.0")
            write_text(
                os.path.join(version_dir, ".claude-plugin", "plugin.json"),
                "{ this is not valid json")
            result = run_cli("json", "--home", tmp, "--root", tmp)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(len(data["plugins"]), 1)
        # manifest present on disk but unparsable: falls back to directory
        # evidence, same as the absent case, and is named in unreadable.
        self.assertEqual(data["plugins"][0]["version"], "1.0.0")
        reasons = [u["path"] for u in data["unreadable"]]
        self.assertTrue(any("plugin.json" in p for p in reasons))


class NoDataTests(unittest.TestCase):
    """Test 9: every one of the four core surfaces unreadable gives
    NO-DATA at exit 2."""

    def test_every_surface_unreadable_is_no_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            # marketplaces cache dir: a FILE where a directory is expected
            cache_path = os.path.join(tmp, ".claude", "plugins", "cache")
            write_text(cache_path, "not a directory\n")
            # settings.json: a DIRECTORY where a file is expected
            os.makedirs(os.path.join(tmp, ".claude", "settings.json"))
            # skills dir: a FILE where a directory is expected
            write_text(os.path.join(tmp, ".claude", "skills"), "nope\n")
            # .claude.json: missing entirely (never written)
            result = run_cli("json", "--home", tmp, "--root", tmp)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertTrue(result.stdout.startswith("NO-DATA:"), result.stdout)

    def test_bad_home_is_no_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            bogus = os.path.join(tmp, "does-not-exist-at-all")
            result = run_cli("json", "--home", bogus)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertTrue(result.stdout.startswith("NO-DATA:"), result.stdout)


class JsonShapeTests(unittest.TestCase):
    """Test 10: json output parses and carries every documented top-level
    key."""

    def test_json_output_has_every_documented_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            minimal_home(tmp)
            result = run_cli("json", "--home", tmp, "--root", tmp)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        data = json.loads(result.stdout)
        expected_keys = {
            "schema", "home", "root", "marketplaces", "plugins", "skills",
            "mcp_servers", "settings_layers", "user_hook_commands",
            "unreadable",
        }
        self.assertEqual(set(data.keys()), expected_keys)
        self.assertEqual(data["schema"], 1)


class InventoryVerbTests(unittest.TestCase):
    """The `inventory` verb (default verb) renders a human readable report
    grouped by surface, with counts, and is default when no verb given."""

    def test_inventory_is_default_verb_and_lists_a_plugin(self):
        with tempfile.TemporaryDirectory() as tmp:
            minimal_home(tmp)
            make_plugin(tmp, "mkt", "shown-plugin", "1.0.0",
                        manifest={"name": "shown-plugin", "version": "1.0.0"})
            result = run_cli("--home", tmp, "--root", tmp)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("MARKETPLACES (1)", result.stdout)
        self.assertIn("PLUGINS (1)", result.stdout)
        self.assertIn("shown-plugin @ mkt v1.0.0", result.stdout)
        self.assertIn("NOT-ENABLED", result.stdout)
        self.assertIn("SUMMARY:", result.stdout)


class PurityTests(unittest.TestCase):
    """Test 11: purity. Running both verbs against a fixture changes zero
    bytes under it."""

    def test_tree_unchanged_after_both_verbs(self):
        with tempfile.TemporaryDirectory() as tmp:
            minimal_home(tmp)
            make_plugin(tmp, "mkt", "plug", "1.0.0",
                        manifest={"name": "plug", "version": "1.0.0"},
                        hooks={"SessionStart": []})
            make_skill(tmp, "a-skill")

            def snapshot():
                out = {}
                for dirpath, dirnames, filenames in os.walk(tmp):
                    dirnames.sort()
                    for name in sorted(filenames):
                        path = os.path.join(dirpath, name)
                        out[os.path.relpath(path, tmp)] = os.path.getmtime(path)
                return out

            before = snapshot()
            run_cli("inventory", "--home", tmp, "--root", tmp)
            run_cli("json", "--home", tmp, "--root", tmp)
            after = snapshot()
        self.assertEqual(before, after,
                         "bm_toolkit.py changed the tree it inspected; this "
                         "tool must be provably read-only")


class ConflictsFixturesFoundTests(unittest.TestCase):
    """Test 12: the `conflicts` verb finds the 7 Stop-hook registrants and
    the dual-version plugin fixture (docs/plan/TOOLKIT-PLAN-2026-08-12.md
    section F2, measured 2026-08-12) by itself, from a synthetic inventory
    built to match that measurement exactly."""

    def test_seven_stop_hooks_and_dual_version_plugin_fire(self):
        with tempfile.TemporaryDirectory() as tmp:
            minimal_home(tmp)
            stop_hooks = {"Stop": []}
            make_plugin(tmp, "brotherme-marketplace", "brotherme", "1.0.0",
                        manifest={"name": "brotherme"}, hooks=stop_hooks)
            make_plugin(tmp, "brothersbe", "brothersbe", "1.0.0-rc.1",
                        manifest={"name": "brothersbe"}, hooks=stop_hooks)
            make_plugin(tmp, "brothersbe", "brothersbe", "1.0.0-rc.38",
                        manifest={"name": "brothersbe"}, hooks=stop_hooks)
            make_plugin(tmp, "claude-plugins-official", "hookify", "1.0.0",
                        manifest={"name": "hookify"}, hooks=stop_hooks)
            make_plugin(tmp, "claude-plugins-official", "ralph-loop", "1.0.0",
                        manifest={"name": "ralph-loop"}, hooks=stop_hooks)
            make_plugin(tmp, "claude-plugins-official", "security-guidance",
                        "1.0.0", manifest={"name": "security-guidance"},
                        hooks=stop_hooks)
            make_plugin(tmp, "claude-community", "slop-gate", "1.0.0",
                        manifest={"name": "slop-gate"}, hooks=stop_hooks)
            make_plugin(tmp, "claude-community", "ultrapowers", "1.0.0",
                        manifest={"name": "ultrapowers"}, hooks=stop_hooks)
            result = run_cli("conflicts", "--home", tmp, "--root", tmp)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        out = result.stdout
        self.assertIn(
            "[WARN] multi-stop-hook: More than one capability registers a "
            "Stop hook (count=7 threshold=2)", out)
        self.assertIn("brotherme@brotherme-marketplace", out)
        self.assertIn(
            "[FAIL] multi-version-cached: One capability is present at more "
            "than one version (count=2 threshold=2)", out)
        self.assertIn(
            "brothersbe@brothersbe at 1.0.0-rc.1 and 1.0.0-rc.38", out)


class ConflictsInstalledNotEnabledTests(unittest.TestCase):
    """Test 13: installed-not-enabled fires on a cached-but-not-enabled
    plugin, naming it by name@marketplace."""

    def test_cached_not_enabled_plugin_is_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            minimal_home(tmp)
            make_plugin(tmp, "mkt", "dormant-plugin", "1.0.0",
                        manifest={"name": "dormant-plugin"})
            result = run_cli("conflicts", "--home", tmp, "--root", tmp)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[INFO] installed-not-enabled", result.stdout)
        self.assertIn("dormant-plugin@mkt", result.stdout)


class ConflictsNoDataOnUnreadableSurfaceTests(unittest.TestCase):
    """Test 14: `conflicts` fails NO-DATA the same way `json` and
    `inventory` do when every core surface is unreadable; the conflict
    layer never gets a chance to paper over an inventory that could not be
    built."""

    def test_every_surface_unreadable_is_no_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = os.path.join(tmp, ".claude", "plugins", "cache")
            write_text(cache_path, "not a directory\n")
            os.makedirs(os.path.join(tmp, ".claude", "settings.json"))
            write_text(os.path.join(tmp, ".claude", "skills"), "nope\n")
            result = run_cli("conflicts", "--home", tmp, "--root", tmp)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertTrue(result.stdout.startswith("NO-DATA:"), result.stdout)


class ConflictsNoDetectorIsNamedNoDataTests(unittest.TestCase):
    """Test 15: a class with no mechanical detector (its `detect` surface
    is not part of the inventory) is reported as NO-DATA, named by id and
    reason, never dropped and never read as a silent pass."""

    def test_class_without_a_detector_is_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            minimal_home(tmp)
            result = run_cli("conflicts", "--home", tmp, "--root", tmp)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(
            "duplicate-planning-workflow: no mechanical detector for this "
            "class", result.stdout)


class ConflictsClassesOverrideTests(unittest.TestCase):
    """Test 16: a valid --classes JSON file REPLACES the shipped default
    table entirely (decision 34: the defaults are a fallback, not a
    floor), so only the override's own classes appear in the report."""

    def test_valid_override_replaces_default_classes(self):
        with tempfile.TemporaryDirectory() as tmp:
            minimal_home(tmp)
            make_plugin(tmp, "mkt", "dormant-plugin", "1.0.0",
                        manifest={"name": "dormant-plugin"})
            override_path = write_json(os.path.join(tmp, "custom-classes.json"), {
                "classes": [{
                    "id": "installed-not-enabled",
                    "title": "CUSTOM OVERRIDE TITLE MARKER",
                    "severity": "warn",
                    "detect": "test override",
                    "threshold": 1,
                }],
            })
            result = run_cli("conflicts", "--home", tmp, "--root", tmp,
                              "--classes", override_path)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("CUSTOM OVERRIDE TITLE MARKER", result.stdout)
        self.assertNotIn("multi-stop-hook", result.stdout)
        self.assertNotIn("OVERRIDE REFUSED", result.stdout)


class ConflictsMalformedOverrideRefusedTests(unittest.TestCase):
    """Test 17: a --classes file that is malformed JSON, or valid JSON with
    the wrong shape, is refused BY NAME (path and reason printed) and the
    run falls back to the shipped default classes rather than crashing or
    going classless."""

    def test_invalid_json_syntax_is_refused_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            minimal_home(tmp)
            bad_path = write_text(os.path.join(tmp, "broken.json"),
                                   "{ not valid json")
            result = run_cli("conflicts", "--home", tmp, "--root", tmp,
                              "--classes", bad_path)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OVERRIDE REFUSED:", result.stdout)
        self.assertIn(bad_path, result.stdout)
        # fallback to defaults: multi-stop-hook still shows up (clear, since
        # this fixture has no plugins), proving the run did not go classless.
        self.assertIn("multi-stop-hook (count=0 threshold=2)", result.stdout)

    def test_wrong_shape_json_is_refused_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            minimal_home(tmp)
            wrong_shape_path = write_json(
                os.path.join(tmp, "wrong-shape.json"), {"not_classes": []})
            result = run_cli("conflicts", "--home", tmp, "--root", tmp,
                              "--classes", wrong_shape_path)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OVERRIDE REFUSED:", result.stdout)
        self.assertIn(wrong_shape_path, result.stdout)
        self.assertIn("multi-stop-hook (count=0 threshold=2)", result.stdout)

    def test_missing_explicit_classes_path_is_refused_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            minimal_home(tmp)
            missing_path = os.path.join(tmp, "does-not-exist.json")
            result = run_cli("conflicts", "--home", tmp, "--root", tmp,
                              "--classes", missing_path)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OVERRIDE REFUSED:", result.stdout)
        self.assertIn(missing_path, result.stdout)


if __name__ == "__main__":
    unittest.main()
