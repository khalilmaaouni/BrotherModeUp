#!/usr/bin/env python3
"""Suite for scripts/install.py and scripts/uninstall.py.

Every test here runs the real CLI as a subprocess against a FAKE HOME under a
temporary directory. Nothing in this file writes to the real ~/.claude, and
nothing imports the installer into this process, because an installer that is
only ever tested in-process is not tested at the layer a founder uses it.

The cases are the attack list from the loop spec, not a happy path with
decoration: existing user hooks, malformed JSON, a prior install, a symlinked
target, spaces and non-ASCII in paths, a partially failed install, and the one
that matters most, an install that reports success while the fence hook is not
actually wired.

Python 3.9, standard library only.

No em or en dashes anywhere in this file, its comments, or its output.
"""

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
INSTALL = os.path.join(ROOT, "scripts", "install.py")
UNINSTALL = os.path.join(ROOT, "scripts", "uninstall.py")

EXIT_REFUSED = 4


class InstallerCase(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="bm-install-test-")
        self.home = os.path.join(self.tmp, "home")
        self.claude = os.path.join(self.home, ".claude")
        os.makedirs(self.claude)
        self.settings = os.path.join(self.claude, "settings.json")
        self.target = os.path.join(self.claude, "skills", "brothermode")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # --- helpers -----------------------------------------------------------

    def run_install(self, *args, **kw):
        return self._run(INSTALL, args, kw)

    def run_uninstall(self, *args, **kw):
        return self._run(UNINSTALL, args, kw)

    def _run(self, script, args, kw):
        target = kw.pop("target", self.target)
        settings = kw.pop("settings", self.settings)
        env = dict(os.environ)
        env["HOME"] = self.home
        env.pop("BROTHERMODE_VAULT", None)
        env.update(kw.pop("env", {}))
        cmd = [sys.executable, script, "--target", target,
               "--settings", settings] + list(args)
        return subprocess.run(cmd, env=env, cwd=self.tmp,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True, timeout=300)

    def write_settings(self, obj_or_text):
        text = obj_or_text if isinstance(obj_or_text, str) else \
            json.dumps(obj_or_text, indent=2)
        with io.open(self.settings, "w", encoding="utf-8") as fh:
            fh.write(text)
        return text

    def read_settings(self):
        return json.loads(self.raw_settings())

    def raw_settings(self):
        return self.read_text(self.settings)

    def read_text(self, path):
        with io.open(path, encoding="utf-8") as fh:
            return fh.read()

    def user_hook(self, marker="my-own-script.sh"):
        return {"hooks": [{"type": "command", "command": "sh /home/me/" + marker}]}

    def all_commands(self, settings, event):
        out = []
        for group in settings.get("hooks", {}).get(event, []):
            for h in group.get("hooks", []):
                out.append(h.get("command", ""))
        return out


class TestCleanInstall(InstallerCase):

    def test_wires_all_five_hooks_including_the_fence(self):
        r = self.run_install()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        s = self.read_settings()
        for event in ("SessionStart", "SessionEnd", "Stop", "PreCompact",
                      "PreToolUse"):
            self.assertIn(event, s["hooks"], "%s was not wired" % event)
            self.assertEqual(len(s["hooks"][event]), 1)

    def test_fence_hook_group_has_matcher_and_a_file_that_exists(self):
        """The failure this guards: an install that prints success while the
        PreToolUse fence is absent or points at nothing. The fence is the only
        hook that can refuse a write, so a wired-but-dead fence is the same as
        no fence while looking installed."""
        self.run_install()
        s = self.read_settings()
        group = s["hooks"]["PreToolUse"][0]
        self.assertIn("matcher", group)
        self.assertIn("Edit", group["matcher"])
        cmd = group["hooks"][0]["command"]
        self.assertEqual(group["hooks"][0].get("timeout"), 10)
        path = cmd.split("python3 ", 1)[1].strip().strip("'")
        self.assertTrue(os.path.isfile(path),
                        "the fence hook command points at %s, which is not "
                        "there" % path)

    def test_files_land_and_record_names_the_version(self):
        self.run_install()
        self.assertTrue(os.path.isfile(os.path.join(self.target, "SKILL.md")))
        self.assertTrue(os.path.isfile(
            os.path.join(self.target, "tools", "bm_fence_hook.py")))
        rec = json.loads(self.read_text(
            os.path.join(self.claude, "brothermode-install.json")))
        version = self.read_text(os.path.join(ROOT, "VERSION")).strip()
        self.assertEqual(rec["version"], version)
        self.assertEqual(rec["target"], self.target)

    def test_machine_state_is_not_copied(self):
        for name in (".git", "__pycache__", "threads"):
            self.assertFalse(os.path.exists(os.path.join(self.target, name)))
        self.run_install()
        for name in (".git", "__pycache__", "threads", ".brothermode"):
            self.assertFalse(os.path.exists(os.path.join(self.target, name)),
                             "%s was copied into the install" % name)

    def test_no_hooks_flag_leaves_settings_absent(self):
        r = self.run_install("--no-hooks")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(os.path.exists(self.settings))
        self.assertTrue(os.path.isfile(os.path.join(self.target, "SKILL.md")))


class TestRefusals(InstallerCase):

    def test_second_install_is_refused_and_changes_nothing(self):
        self.run_install()
        before = self.raw_settings()
        r = self.run_install()
        self.assertEqual(r.returncode, EXIT_REFUSED, r.stdout + r.stderr)
        self.assertIn("--upgrade", r.stderr)
        self.assertEqual(self.raw_settings(), before,
                         "a refused install still rewrote settings.json")

    def test_malformed_settings_are_refused_byte_for_byte(self):
        broken = '{\n  "hooks": {\n    "Stop": [ ,,, ]\n'
        self.write_settings(broken)
        r = self.run_install()
        self.assertEqual(r.returncode, EXIT_REFUSED, r.stdout + r.stderr)
        self.assertIn("not valid JSON", r.stderr)
        self.assertEqual(self.raw_settings(), broken,
                         "a broken settings.json was rewritten; that destroys "
                         "whatever the user was editing")

    def test_settings_whose_top_level_is_a_list_is_refused(self):
        self.write_settings("[1, 2, 3]")
        r = self.run_install()
        self.assertEqual(r.returncode, EXIT_REFUSED, r.stdout + r.stderr)
        self.assertEqual(self.raw_settings(), "[1, 2, 3]")

    def test_hooks_key_of_the_wrong_type_is_refused(self):
        raw = self.write_settings({"hooks": "please"})
        r = self.run_install()
        self.assertEqual(r.returncode, EXIT_REFUSED, r.stdout + r.stderr)
        self.assertEqual(self.raw_settings(), raw)

    def test_non_empty_foreign_target_is_refused(self):
        os.makedirs(self.target)
        with io.open(os.path.join(self.target, "important.txt"), "w") as fh:
            fh.write("mine")
        r = self.run_install()
        self.assertEqual(r.returncode, EXIT_REFUSED, r.stdout + r.stderr)
        self.assertEqual(self.read_text(os.path.join(self.target, "important.txt")),
                         "mine")


class TestUpgrade(InstallerCase):

    def test_upgrade_is_idempotent(self):
        self.run_install()
        first = self.read_settings()
        r = self.run_install("--upgrade")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        second = self.read_settings()
        self.assertEqual(first, second,
                         "re-running the installer changed the configuration")
        for event in ("SessionStart", "PreToolUse"):
            self.assertEqual(len(second["hooks"][event]), 1,
                             "%s was duplicated by the upgrade" % event)

    def test_upgrade_replaces_a_stale_entry_rather_than_stacking(self):
        stale = {"hooks": {"SessionEnd": [{"hooks": [{
            "type": "command",
            "command": "python3 " + os.path.join(self.target, "tools",
                                                 "bm_telemetry.py") + " OLD-ARG",
        }]}]}}
        self.write_settings(stale)
        r = self.run_install("--upgrade")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        cmds = self.all_commands(self.read_settings(), "SessionEnd")
        self.assertEqual(len(cmds), 1)
        self.assertNotIn("OLD-ARG", cmds[0])

    def test_a_backup_of_the_previous_settings_is_kept(self):
        self.write_settings({"model": "opus", "hooks": {}})
        self.run_install()
        backups = [n for n in os.listdir(self.claude)
                   if n.startswith("settings.json.brothermode-backup-")]
        self.assertEqual(len(backups), 1, os.listdir(self.claude))
        old = json.loads(self.read_text(os.path.join(self.claude, backups[0])))
        self.assertEqual(old["model"], "opus")


class TestUserHooksSurvive(InstallerCase):

    def test_unrelated_hooks_and_keys_survive_install_and_uninstall(self):
        original = {
            "model": "sonnet",
            "env": {"MY_VAR": "1"},
            "hooks": {
                "SessionStart": [self.user_hook("theirs-start.sh")],
                "PostToolUse": [self.user_hook("theirs-post.sh")],
            },
        }
        self.write_settings(original)
        self.assertEqual(self.run_install().returncode, 0)
        s = self.read_settings()
        self.assertEqual(s["model"], "sonnet")
        self.assertEqual(s["env"], {"MY_VAR": "1"})
        self.assertIn("theirs-start.sh", " ".join(
            self.all_commands(s, "SessionStart")))
        self.assertEqual(len(s["hooks"]["SessionStart"]), 2)
        self.assertEqual(len(s["hooks"]["PostToolUse"]), 1)

        self.assertEqual(self.run_uninstall().returncode, 0)
        after = self.read_settings()
        self.assertEqual(after["hooks"]["SessionStart"],
                         original["hooks"]["SessionStart"])
        self.assertEqual(after["hooks"]["PostToolUse"],
                         original["hooks"]["PostToolUse"])
        self.assertEqual(after["model"], "sonnet")

    def test_a_group_the_user_shares_with_us_is_never_deleted(self):
        """The destructive-merge case. If the user has put their own hook into
        the SAME matcher group as ours, removing the group would take their
        hook with it. Ownership therefore requires EVERY command in the group
        to be ours."""
        shared = {"hooks": {"Stop": [{"hooks": [
            {"type": "command",
             "command": "python3 " + os.path.join(self.target, "tools",
                                                  "bm_telemetry.py") + " stop-warn"},
            {"type": "command", "command": "sh /home/me/mine.sh"},
        ]}]}}
        self.write_settings(shared)
        self.assertEqual(self.run_install("--upgrade").returncode, 0)
        self.assertEqual(self.run_uninstall().returncode, 0)
        cmds = self.all_commands(self.read_settings(), "Stop")
        self.assertIn("sh /home/me/mine.sh", cmds,
                      "the user's hook was deleted as collateral")

    def test_a_hook_pointing_at_a_different_install_is_left_alone(self):
        other = os.path.join(self.tmp, "other-brothermode")
        foreign = {"hooks": {"Stop": [{"hooks": [{
            "type": "command",
            "command": "python3 " + os.path.join(other, "tools",
                                                 "bm_telemetry.py") + " stop-warn",
        }]}]}}
        self.write_settings(foreign)
        self.assertEqual(self.run_install().returncode, 0)
        self.assertEqual(self.run_uninstall().returncode, 0)
        cmds = self.all_commands(self.read_settings(), "Stop")
        self.assertEqual(len(cmds), 1)
        self.assertIn(other, cmds[0])


class TestOwnershipBoundaries(InstallerCase):
    """Ownership was a substring test, and every one of these got past it.

    All four were reproduced against the previous commit before this class
    existed: two installations whose paths share a prefix, an install path
    containing an apostrophe, a user hook that chains their script after ours,
    and a user script whose name contains one of our tool names."""

    def all_hook_commands(self, settings):
        out = []
        for event in settings.get("hooks", {}):
            out.extend(self.all_commands(settings, event))
        return out

    def test_an_install_sharing_a_path_prefix_is_not_claimed_as_ours(self):
        long_target = self.target + "-work"
        r = self.run_install(target=long_target)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        before = [c for c in self.all_hook_commands(self.read_settings())
                  if long_target in c]
        self.assertEqual(len(before), 5)

        r = self.run_install("--upgrade")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        after = [c for c in self.all_hook_commands(self.read_settings())
                 if long_target in c]
        self.assertEqual(len(after), 5,
                         "installing at a prefix path deleted the other "
                         "installation's hooks")

    def test_uninstall_at_a_prefix_path_removes_nothing_and_says_so(self):
        self.assertEqual(self.run_install().returncode, 0)
        raw_before = self.raw_settings()
        record = os.path.join(self.claude, "brothermode-install.json")
        self.assertTrue(os.path.exists(record))

        prefix_target = os.path.join(self.claude, "skills", "brother")
        r = self.run_uninstall(target=prefix_target)
        self.assertEqual(r.returncode, 4, r.stdout + r.stderr)
        self.assertEqual(self.raw_settings(), raw_before,
                         "a uninstall aimed at a prefix path edited settings")
        self.assertTrue(os.path.exists(record),
                        "the install record was deleted by a run that removed "
                        "no hooks")
        self.assertIn("refusing to finish", r.stderr)

    def test_an_apostrophe_in_the_install_path_survives_the_round_trip(self):
        target = os.path.join(self.tmp, "Repertoire d'installation", "brothermode")
        r = self.run_install(target=target)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(len(self.all_hook_commands(self.read_settings())), 5)

        r = self.run_uninstall(target=target)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.all_hook_commands(self.read_settings()), [],
                         "uninstall could not recognise the hooks the "
                         "installer had just written")

    def test_a_user_hook_that_chains_their_script_after_ours_is_kept(self):
        ours = "python3 " + os.path.join(self.target, "tools", "bm_fence_hook.py")
        wrapped = ours + " && python3 /home/me/my_audit.py"
        self.write_settings({"hooks": {"PreToolUse": [
            {"matcher": "Write", "hooks": [
                {"type": "command", "command": wrapped}]}]}})
        r = self.run_install("--upgrade")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("my_audit.py", " ".join(
            self.all_hook_commands(self.read_settings())),
            "the user's own auditor was deleted with the hook that wrapped ours")

    def test_a_user_script_named_like_one_of_ours_next_door_is_kept(self):
        theirs = os.path.join(self.claude, "skills", "brothermode-mine")
        os.makedirs(theirs)
        cmd = "python3 " + os.path.join(theirs, "my_bm_fence_hook.py")
        self.write_settings({"hooks": {"PreToolUse": [
            {"matcher": "Write", "hooks": [{"type": "command", "command": cmd}]}]}})
        r = self.run_install("--upgrade")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("my_bm_fence_hook.py", " ".join(
            self.all_hook_commands(self.read_settings())))


class TestSymlinkedSettings(InstallerCase):
    """A dotfile-managed settings.json is a symlink into a tracked repo."""

    def link_settings(self):
        real = os.path.join(self.tmp, "dotfiles", "claude-settings.json")
        os.makedirs(os.path.dirname(real))
        with io.open(real, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"model": "opus"}, indent=2))
        try:
            os.symlink(real, self.settings)
        except (OSError, NotImplementedError, AttributeError):
            self.skipTest("this filesystem does not support symlinks")
        return real

    def test_the_link_survives_and_the_real_file_is_what_changes(self):
        real = self.link_settings()
        r = self.run_install()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(os.path.islink(self.settings),
                        "settings.json was replaced by a regular file, "
                        "detaching it from the dotfiles repository")
        written = json.loads(self.read_text(real))
        self.assertEqual(written["model"], "opus")
        self.assertEqual(len(written.get("hooks", {})), 5)
        self.assertIn("is a symlink", r.stdout)

        r = self.run_uninstall()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(os.path.islink(self.settings))
        self.assertNotIn("hooks", json.loads(self.read_text(real)))


class TestDryRun(InstallerCase):

    def test_dry_run_writes_absolutely_nothing(self):
        raw = self.write_settings({"model": "opus"})
        r = self.run_install("--dry-run")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("dry-run", r.stdout)
        self.assertEqual(self.raw_settings(), raw)
        self.assertFalse(os.path.exists(self.target))
        self.assertEqual(
            sorted(os.listdir(self.claude)), ["settings.json"],
            "dry-run left something behind in %s" % self.claude)

    def test_dry_run_uninstall_changes_nothing(self):
        self.run_install()
        raw = self.raw_settings()
        r = self.run_uninstall("--dry-run")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.raw_settings(), raw)
        self.assertTrue(os.path.exists(
            os.path.join(self.claude, "brothermode-install.json")))


class TestUninstall(InstallerCase):

    def test_uninstall_removes_our_entries_and_the_record(self):
        self.run_install()
        r = self.run_uninstall()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        s = self.read_settings()
        self.assertEqual(s.get("hooks", {}), {})
        self.assertFalse(os.path.exists(
            os.path.join(self.claude, "brothermode-install.json")))

    def test_uninstall_leaves_the_files_unless_asked(self):
        self.run_install()
        self.run_uninstall()
        self.assertTrue(os.path.isfile(os.path.join(self.target, "SKILL.md")))

    def test_remove_files_deletes_only_a_real_checkout(self):
        self.run_install()
        self.run_uninstall("--remove-files")
        self.assertFalse(os.path.exists(self.target))

    def test_remove_files_refuses_a_directory_that_is_not_ours(self):
        os.makedirs(self.target)
        with io.open(os.path.join(self.target, "notes.txt"), "w") as fh:
            fh.write("mine")
        r = self.run_uninstall("--remove-files")
        self.assertEqual(r.returncode, EXIT_REFUSED, r.stdout + r.stderr)
        self.assertTrue(os.path.isfile(os.path.join(self.target, "notes.txt")))

    def test_the_vault_is_never_deleted_and_is_named_in_the_output(self):
        vault = os.path.join(self.home, "BrotherModeVault")
        os.makedirs(vault)
        with io.open(os.path.join(vault, "Home.md"), "w") as fh:
            fh.write("mine")
        self.run_install()
        r = self.run_uninstall("--remove-files",
                               env={"BROTHERMODE_VAULT": vault})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(os.path.isfile(os.path.join(vault, "Home.md")),
                        "the uninstaller deleted the vault")
        self.assertIn(vault, r.stdout)

    def test_uninstall_without_a_record_or_target_refuses_to_guess(self):
        self.run_install()
        os.unlink(os.path.join(self.claude, "brothermode-install.json"))
        env = dict(os.environ)
        env["HOME"] = self.home
        r = subprocess.run(
            [sys.executable, UNINSTALL, "--settings", self.settings],
            env=env, cwd=self.tmp, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, universal_newlines=True, timeout=120)
        self.assertEqual(r.returncode, EXIT_REFUSED, r.stdout + r.stderr)
        self.assertIn("--target", r.stderr)


class TestAwkwardPaths(InstallerCase):

    def test_spaces_and_non_ascii_in_the_target_path(self):
        target = os.path.join(self.tmp, "My Skills", "brothermode café")
        r = self.run_install(target=target)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        s = self.read_settings()
        cmd = s["hooks"]["PreCompact"][0]["hooks"][0]["command"]
        # The whole point of quoting: the path must survive as ONE shell word.
        self.assertIn("'", cmd)
        r2 = self.run_uninstall(target=target)
        self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)
        self.assertEqual(self.read_settings().get("hooks", {}), {})

    def test_installing_into_a_symlinked_directory_is_recognized(self):
        real = os.path.join(self.tmp, "real-install")
        link = os.path.join(self.tmp, "linked-install")
        os.makedirs(real)
        try:
            os.symlink(real, link)
        except (OSError, NotImplementedError):
            self.skipTest("this filesystem does not support symlinks")
        r = self.run_install(target=link)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(os.path.isfile(os.path.join(real, "SKILL.md")),
                        "the copy did not follow the symlink to the real dir")
        r2 = self.run_install(target=link)
        self.assertEqual(r2.returncode, EXIT_REFUSED,
                         "a second install through the symlink was not refused")

    def test_running_the_installer_from_inside_the_install_directory(self):
        """The documented path in QUICKSTART: the user already cloned into
        ~/.claude/skills/brothermode and runs the installer from there. Source
        and target are then the same place and nothing should be copied."""
        os.makedirs(os.path.dirname(self.target))
        shutil.copytree(ROOT, self.target,
                        ignore=shutil.ignore_patterns(
                            ".git", "__pycache__", ".brothermode", "threads"))
        r = subprocess.run(
            [sys.executable, os.path.join(self.target, "scripts", "install.py"),
             "--settings", self.settings],
            env=dict(os.environ, HOME=self.home), cwd=self.target,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, timeout=300)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("same directory", r.stdout)
        s = self.read_settings()
        self.assertEqual(len(s["hooks"]["PreToolUse"]), 1)
        self.assertIn(self.target, s["hooks"]["PreToolUse"][0]["hooks"][0]["command"])


class TestPartialPriorInstall(InstallerCase):

    def test_hooks_present_but_files_missing_is_refused_then_repaired(self):
        """A prior install that failed halfway: the hook entries landed, the
        directory did not. The refusal must fire (there IS a prior install),
        and --upgrade must then repair it rather than stacking duplicates."""
        self.run_install()
        shutil.rmtree(self.target)
        r = self.run_install()
        self.assertEqual(r.returncode, EXIT_REFUSED, r.stdout + r.stderr)
        r2 = self.run_install("--upgrade")
        self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)
        self.assertTrue(os.path.isfile(
            os.path.join(self.target, "tools", "bm_fence_hook.py")))
        self.assertEqual(len(self.read_settings()["hooks"]["PreToolUse"]), 1)

    def test_a_broken_install_is_reported_as_not_done(self):
        """A prior install left the directory unreadable. The installer must
        report the failure rather than printing a success summary anyway."""
        self.run_install()
        tools = os.path.join(self.target, "tools")
        os.unlink(os.path.join(tools, "bm_fence_hook.py"))
        os.chmod(tools, 0o500)
        try:
            r = self.run_install("--upgrade")
        finally:
            os.chmod(tools, 0o700)
        if r.returncode == 0:
            self.skipTest("this filesystem or user ignores directory mode 0500")
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("Still manual", r.stdout,
                         "a failed install still printed its success summary")


class TestSmokeTestItself(unittest.TestCase):
    """Calibration of the guard, not of the happy path.

    scripts/install.py only claims success after smoke_test() returns no
    problems. If smoke_test cannot FAIL, that claim is decoration, so these
    reinject the two failures it exists to catch: a hook target that is not on
    disk, and a fence hook that is on disk but does not run."""

    def setUp(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("bm_install_under_test",
                                                      INSTALL)
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)
        self.tmp = tempfile.mkdtemp(prefix="bm-smoke-calib-")
        self.tools = os.path.join(self.tmp, "tools")
        os.makedirs(self.tools)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _copy_real_tools(self):
        for name in self.mod.OWNED_TOOLS:
            shutil.copy2(os.path.join(HERE, name), os.path.join(self.tools, name))

    def test_passes_on_a_real_installation(self):
        self._copy_real_tools()
        self.assertEqual(self.mod.smoke_test(self.tmp), [])

    def test_fails_when_the_fence_hook_is_missing(self):
        self._copy_real_tools()
        os.unlink(os.path.join(self.tools, "bm_fence_hook.py"))
        problems = self.mod.smoke_test(self.tmp)
        self.assertTrue(problems)
        self.assertIn("bm_fence_hook.py", " ".join(problems))

    def test_fails_when_the_fence_hook_does_not_exit_zero(self):
        self._copy_real_tools()
        with io.open(os.path.join(self.tools, "bm_fence_hook.py"), "w",
                     encoding="utf-8") as fh:
            fh.write("import sys\nsys.stderr.write('boom\\n')\nsys.exit(1)\n")
        problems = self.mod.smoke_test(self.tmp)
        self.assertTrue(problems, "a fence hook that exits 1 was accepted")
        self.assertIn("exited 1", " ".join(problems))

    def test_passes_again_once_the_real_hook_is_restored(self):
        self._copy_real_tools()
        self.assertEqual(self.mod.smoke_test(self.tmp), [])


if __name__ == "__main__":
    unittest.main(verbosity=1)
