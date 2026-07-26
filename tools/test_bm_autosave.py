#!/usr/bin/env python3
"""Regression tests for tools/bm_autosave.py, the Phase 2 recovery rewrite
(docs/superpowers/specs/2026-07-26-phase2-recovery-design.md). Standard
library only. Run: python3 tools/test_bm_autosave.py

Every TestCalibrated* class reproduces one row of the spec's defect table.
Each proves two things in one method: the REAL product code does the right
thing today, and monkeypatching the exact PRODUCT function responsible for
that fix back to its old shape makes the SAME check fail for the SAME
reason the defect describes. The second half is the calibration proof: a
test that would pass no matter what the implementation does is not testing
anything. Every reinjection here patches a real, named function on the
imported bm_autosave module object, never a private local copy of old code
(a prior version of this project deleted 24 tests for exactly that mistake).

Every test is self-contained under tempfile.TemporaryDirectory() and never
touches this repo's own git state, BROTHERMODE_VAULT, or the real home
directory.
"""
import contextlib
import io
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))

import importlib.util
_spec = importlib.util.spec_from_file_location("bm_autosave", os.path.join(HERE, "bm_autosave.py"))
autosave = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(autosave)
sys.modules["bm_autosave"] = autosave

_spec2 = importlib.util.spec_from_file_location("bm_store", os.path.join(HERE, "bm_store.py"))
bs = importlib.util.module_from_spec(_spec2)
_spec2.loader.exec_module(bs)
sys.modules["bm_store"] = bs


def _git(repo, *args):
    return subprocess.run(["git", "-C", repo] + list(args), capture_output=True, text=True)


def _init_repo(path):
    """A throwaway scratch repo, isolated from any real developer identity
    or signing config, so a test can never hang waiting on a GPG prompt or
    pick up ambient git config from the machine running it."""
    _git(path, "init", "-q")
    _git(path, "config", "user.email", "t@t.t")
    _git(path, "config", "user.name", "t")
    _git(path, "config", "commit.gpgsign", "false")


def _write(path, text):
    with io.open(path, "w") as f:
        f.write(text)


def _read(path):
    with io.open(path) as f:
        return f.read()


def _run_precompact(cwd, session_id="s1"):
    """Drive the real hook entrypoint (not just snapshot() directly), so
    calibration tests can monkeypatch resolve_toplevel and prove the SAME
    entrypoint a hook actually calls is what breaks."""
    payload = json.dumps({"cwd": cwd, "session_id": session_id})
    old_stdin = sys.stdin
    sys.stdin = io.StringIO(payload)
    try:
        return autosave.cmd_precompact()
    finally:
        sys.stdin = old_stdin


class TestCalibratedFA(unittest.TestCase):
    """FA: two git worktrees shared one ref; the second snapshot replaced
    the first's. Fixed by namespacing every ref under a per-worktree id."""

    def test_linked_worktrees_never_collide(self):
        with tempfile.TemporaryDirectory() as base:
            main_repo = os.path.join(base, "main")
            os.makedirs(main_repo)
            _init_repo(main_repo)
            _write(os.path.join(main_repo, "tracked.txt"), "v1")
            _git(main_repo, "add", "-A")
            _git(main_repo, "commit", "-qm", "init")

            wt_path = os.path.join(base, "wt1")
            added = _git(main_repo, "worktree", "add", "-q", wt_path, "-b", "wt1branch")
            self.assertEqual(added.returncode, 0, added.stderr)

            _write(os.path.join(main_repo, "main_wip.txt"), "MAIN-WIP")
            _write(os.path.join(wt_path, "wt_wip.txt"), "WT-WIP")

            main_top = autosave.resolve_toplevel(main_repo)
            wt_top = autosave.resolve_toplevel(wt_path)
            self.assertNotEqual(main_top, wt_top)

            def latest_has(toplevel, name):
                wtid = autosave.worktree_id_for(toplevel)
                ref = autosave.latest_ref(wtid)
                sha = _git(toplevel, "rev-parse", "-q", "--verify", ref).stdout.strip()
                if not sha:
                    return False
                names = _git(toplevel, "ls-tree", "-r", "--name-only", sha).stdout
                return name in names.splitlines()

            res_main = autosave.snapshot(main_top, "s-main", "test")
            res_wt = autosave.snapshot(wt_top, "s-wt", "test")
            self.assertTrue(res_main["ok"], res_main)
            self.assertTrue(res_wt["ok"], res_wt)

            self.assertNotEqual(autosave.worktree_id_for(main_top), autosave.worktree_id_for(wt_top),
                                 "two distinct worktrees hashed to the same worktree id")
            self.assertTrue(latest_has(main_top, "main_wip.txt"),
                             "the main worktree's own snapshot lost its file")
            self.assertTrue(latest_has(wt_top, "wt_wip.txt"),
                             "the linked worktree's own snapshot lost its file")

            # CALIBRATION: reinject the old, non-namespaced shape (one ref
            # regardless of which worktree ran it) by forcing worktree_id_for
            # to a constant, and confirm the calibrated check now fails for
            # the FA reason: the second worktree's snapshot replaces the
            # first's, because they now genuinely target the same ref.
            original = autosave.worktree_id_for
            autosave.worktree_id_for = lambda toplevel: "fixed-id-for-fa-reinjection"
            try:
                res_main2 = autosave.snapshot(main_top, "s-main2", "test2")
                res_wt2 = autosave.snapshot(wt_top, "s-wt2", "test2")
                self.assertTrue(res_main2["ok"], res_main2)
                self.assertTrue(res_wt2["ok"], res_wt2)
                self.assertFalse(
                    latest_has(main_top, "main_wip.txt"),
                    "REINJECTION CHECK: with a constant worktree id, the linked "
                    "worktree's snapshot must overwrite the main worktree's "
                    "latest pointer (this is FA); if this assertion fails, the "
                    "test is not calibrated to the defect it claims to catch")
            finally:
                autosave.worktree_id_for = original


class TestCalibratedFC(unittest.TestCase):
    """FC: a tracked .env was excluded from the snapshot, and the old
    recover command then DELETED it from the working tree. Fixed by seeding
    the temp index from HEAD (additive exclusions, never subtractive) and by
    recovering into a brand new worktree that never touches the live tree."""

    def test_tracked_secret_survives_and_recovery_never_touches_live_tree(self):
        with tempfile.TemporaryDirectory() as base:
            repo = os.path.join(base, "repo")
            os.makedirs(repo)
            _init_repo(repo)
            _write(os.path.join(repo, ".env"), "SECRET=committed-value")
            _write(os.path.join(repo, "tracked.txt"), "v1")
            _git(repo, "add", "-A")
            _git(repo, "commit", "-qm", "init with tracked .env")

            _write(os.path.join(repo, "tracked.txt"), "v2")
            _write(os.path.join(repo, "untracked.txt"), "WIP")
            _write(os.path.join(repo, ".env"), "SECRET=locally-edited-should-not-leak")

            before_status = _git(repo, "status", "--porcelain").stdout
            before_env = _read(os.path.join(repo, ".env"))

            toplevel = autosave.resolve_toplevel(repo)
            res = autosave.snapshot(toplevel, "s1", "test")
            self.assertTrue(res["ok"], res)
            sha = res["commit"]

            shown = _git(toplevel, "show", "%s:.env" % sha)
            self.assertEqual(shown.returncode, 0,
                              ".env vanished from the snapshot tree instead of "
                              "surviving at its committed content (FC)")
            self.assertIn("committed-value", shown.stdout)
            self.assertNotIn("locally-edited-should-not-leak", shown.stdout)

            self.assertEqual(before_status, _git(repo, "status", "--porcelain").stdout,
                              "taking a snapshot must never touch the working tree")
            self.assertEqual(before_env, _read(os.path.join(repo, ".env")))

            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                autosave.cmd_recover([repo])
            lines = [l for l in out.getvalue().splitlines() if l.strip()]
            idx = next(i for i, l in enumerate(lines) if "NEW worktree at" in l)
            recovered_dir = lines[idx + 1].strip()
            try:
                self.assertTrue(os.path.isdir(recovered_dir), out.getvalue())
                self.assertEqual(before_status, _git(repo, "status", "--porcelain").stdout,
                                  "recovery must never write into the live working tree")
                self.assertEqual(before_env, _read(os.path.join(repo, ".env")),
                                  "recovery must never touch the live working tree")
                self.assertTrue(os.path.exists(os.path.join(repo, "untracked.txt")),
                                 "recovery deleted a live file instead of leaving it alone (FC)")
                recovered_env = _read(os.path.join(recovered_dir, ".env"))
                self.assertIn("committed-value", recovered_env)
            finally:
                _git(toplevel, "worktree", "remove", "--force", recovered_dir)

            # CALIBRATION: reinject the old, subtractive behavior (temp index
            # never seeded from HEAD) by making the read-tree step a no-op,
            # and confirm the calibrated check now fails for the FC reason:
            # the tracked, excluded file vanishes instead of surviving.
            original_run_git = autosave._run_git

            def _no_read_tree(toplevel_arg, *args, **kw):
                if args and args[0] == "read-tree":
                    return subprocess.CompletedProcess(args, 0, "", "")
                return original_run_git(toplevel_arg, *args, **kw)

            autosave._run_git = _no_read_tree
            try:
                _write(os.path.join(repo, "tracked.txt"), "v3")
                res2 = autosave.snapshot(toplevel, "s2", "test2")
                self.assertTrue(res2["ok"], res2)
                shown2 = _git(toplevel, "show", "%s:.env" % res2["commit"])
                self.assertNotEqual(
                    shown2.returncode, 0,
                    "REINJECTION CHECK: without seeding the temp index from HEAD, "
                    "the tracked-but-excluded .env must vanish from the snapshot "
                    "tree (this is FC); if this assertion fails, the test is not "
                    "calibrated to the defect it claims to catch")
            finally:
                autosave._run_git = original_run_git


class TestCalibratedBlocker1RecoveryPermissions(unittest.TestCase):
    """BLOCKER 1 (release-blockers spec, 2026-07-26, VERIFIED BY
    ORCHESTRATOR): `recover` used to mkdtemp() (0700) and then os.rmdir()
    it so `git worktree add` could "create" the path, which let git
    recreate the directory at the process umask instead (typically 0755
    under the common 022 default) -- world-readable on a shared,
    world-writable /tmp. Reproduced by hand: drwxr-xr-x on the recovered
    directory, -rw-r--r-- on an untracked private file inside it."""

    def _recover_and_get_dir(self, repo):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            autosave.cmd_recover([repo])
        text = out.getvalue()
        lines = [l for l in text.splitlines() if l.strip()]
        idx = next(i for i, l in enumerate(lines) if "NEW worktree at" in l)
        return lines[idx + 1].strip(), text

    def test_recovered_worktree_dir_is_owner_only_even_under_a_permissive_umask(self):
        with tempfile.TemporaryDirectory() as base:
            repo = os.path.join(base, "repo")
            os.makedirs(repo)
            _init_repo(repo)
            _write(os.path.join(repo, "tracked.txt"), "public")
            _git(repo, "add", "-A")
            _git(repo, "commit", "-qm", "init")
            # Untracked, uncommitted: the snapshot must have real, DIRTY
            # work to capture, or the working tree matches HEAD and (FD)
            # clears the "latest" pointer instead of setting it.
            _write(os.path.join(repo, "secret.txt"),
                   "PRIVATE draft: acquisition terms, do not share")
            toplevel = autosave.resolve_toplevel(repo)
            res = autosave.snapshot(toplevel, "s1", "test")
            self.assertTrue(res["ok"], res)

            # Simulate a shared machine's permissive default umask (022, the
            # common macOS/Linux default) so a directory git creates itself
            # (rather than one this code deliberately preserves at 0700)
            # would land at 0755 -- exactly the orchestrator's repro.
            old_umask = os.umask(0o022)
            try:
                recovered_dir, printed = self._recover_and_get_dir(repo)
            finally:
                os.umask(old_umask)
            try:
                self.assertTrue(os.path.isdir(recovered_dir), printed)
                mode = stat.S_IMODE(os.stat(recovered_dir).st_mode)
                self.assertEqual(
                    mode, 0o700,
                    "recovered worktree dir must be owner-only (0700); got %04o "
                    "(BLOCKER 1: mkdtemp's 0700 must survive, never be discarded "
                    "and recreated at the process umask)" % mode)
                secret_path = os.path.join(recovered_dir, "secret.txt")
                self.assertTrue(os.path.exists(secret_path))
                # The printed output must STATE the mode, not just achieve it.
                self.assertIn("0700", printed,
                              "the recovery output must state the permissions it gave "
                              "the recovered directory")
            finally:
                _git(toplevel, "worktree", "remove", "--force", recovered_dir)

            # CALIBRATION: reinject the OLD shape (mkdtemp, then rmdir so git
            # recreates the path itself) onto the real PRODUCT symbol
            # (_prepare_recovery_worktree_dir), and confirm the SAME
            # permissive-umask environment now reproduces the world-readable
            # directory the orchestrator found by hand.
            original_prepare = autosave._prepare_recovery_worktree_dir

            def _old_mkdtemp_then_rmdir():
                d = tempfile.mkdtemp(prefix="bm-autosave-recover-")
                try:
                    os.rmdir(d)
                except OSError:
                    pass
                return d

            autosave._prepare_recovery_worktree_dir = _old_mkdtemp_then_rmdir
            old_umask = os.umask(0o022)
            try:
                recovered_dir2, printed2 = self._recover_and_get_dir(repo)
                try:
                    mode2 = stat.S_IMODE(os.stat(recovered_dir2).st_mode)
                    self.assertNotEqual(
                        mode2, 0o700,
                        "REINJECTION CHECK: with the old mkdtemp-then-rmdir shape "
                        "restored, git must recreate the directory at the process "
                        "umask (world-readable under umask 022), reproducing "
                        "BLOCKER 1; if this assertion fails the test is not "
                        "calibrated to the defect it claims to catch")
                finally:
                    _git(toplevel, "worktree", "remove", "--force", recovered_dir2)
            finally:
                os.umask(old_umask)
                autosave._prepare_recovery_worktree_dir = original_prepare


class TestCalibratedFD(unittest.TestCase):
    """FD: after a deliberate return to a clean tree, the ref still pointed
    at discarded WIP. Fixed by clearing the latest pointer on a clean tree."""

    def test_clean_return_clears_latest_pointer(self):
        with tempfile.TemporaryDirectory() as base:
            repo = os.path.join(base, "repo")
            os.makedirs(repo)
            _init_repo(repo)
            _write(os.path.join(repo, "a.txt"), "v1")
            _git(repo, "add", "-A")
            _git(repo, "commit", "-qm", "init")
            toplevel = autosave.resolve_toplevel(repo)
            wtid = autosave.worktree_id_for(toplevel)
            ref = autosave.latest_ref(wtid)

            _write(os.path.join(repo, "wip.txt"), "WIP")
            res1 = autosave.snapshot(toplevel, "s1", "test")
            self.assertTrue(res1["ok"], res1)
            self.assertEqual(_git(toplevel, "rev-parse", "-q", "--verify", ref).returncode, 0)

            os.remove(os.path.join(repo, "wip.txt"))
            res2 = autosave.snapshot(toplevel, "s1", "test")
            self.assertEqual(res2["reason"], "clean")
            self.assertNotEqual(
                _git(toplevel, "rev-parse", "-q", "--verify", ref).returncode, 0,
                "the latest pointer still resolves after a deliberate return to a "
                "clean tree; it must be cleared, not left aimed at discarded WIP (FD)")

            # CALIBRATION: reinject the old behavior (a clean tree was a
            # silent no-op that never touched the ref) by neutralizing the
            # clearing step, and confirm the calibrated check now fails for
            # the FD reason: the stale pointer survives a clean return.
            original = autosave._clear_latest_if_present
            autosave._clear_latest_if_present = lambda *a, **kw: None
            try:
                _write(os.path.join(repo, "wip2.txt"), "WIP2")
                res3 = autosave.snapshot(toplevel, "s2", "test")
                self.assertTrue(res3["ok"], res3)
                os.remove(os.path.join(repo, "wip2.txt"))
                res4 = autosave.snapshot(toplevel, "s2", "test")
                self.assertEqual(res4["reason"], "clean")
                self.assertEqual(
                    _git(toplevel, "rev-parse", "-q", "--verify", ref).returncode, 0,
                    "REINJECTION CHECK: with the clearing step neutralized, the "
                    "latest pointer must still resolve after a clean return (this "
                    "is FD); if this assertion fails, the test is not calibrated")
            finally:
                autosave._clear_latest_if_present = original


class TestCalibratedFE(unittest.TestCase):
    """FE: a failed git add was ignored, and an empty tree replaced a good
    snapshot. Fixed by checking every return code AND, independently,
    refusing the universal empty tree sha outright."""

    def test_failed_add_aborts_without_touching_latest(self):
        with tempfile.TemporaryDirectory() as base:
            repo = os.path.join(base, "repo")
            os.makedirs(repo)
            _init_repo(repo)
            _write(os.path.join(repo, "a.txt"), "v1")
            _git(repo, "add", "-A")
            _git(repo, "commit", "-qm", "init")
            toplevel = autosave.resolve_toplevel(repo)
            wtid = autosave.worktree_id_for(toplevel)
            ref = autosave.latest_ref(wtid)

            _write(os.path.join(repo, "b.txt"), "good WIP")
            good = autosave.snapshot(toplevel, "s1", "test")
            self.assertTrue(good["ok"], good)
            good_sha = _git(toplevel, "rev-parse", "-q", "--verify", ref).stdout.strip()
            self.assertEqual(good_sha, good["commit"])

            original_run_git = autosave._run_git

            def _fail_add(toplevel_arg, *args, **kw):
                if args and args[0] == "add":
                    return subprocess.CompletedProcess(args, 1, "", "simulated add failure")
                return original_run_git(toplevel_arg, *args, **kw)

            _write(os.path.join(repo, "c.txt"), "WIP that must never be captured")
            autosave._run_git = _fail_add
            try:
                bad = autosave.snapshot(toplevel, "s1", "test")
                self.assertFalse(bad["ok"], "a failed git add must not report success")
                still_good = _git(toplevel, "rev-parse", "-q", "--verify", ref).stdout.strip()
                self.assertEqual(still_good, good_sha,
                                  "a failed git add must never touch the existing "
                                  "latest pointer (FE)")
            finally:
                autosave._run_git = original_run_git

            # CALIBRATION: reinject the old, unchecked behavior by
            # neutralizing _checked into a pass-through (the return code is
            # ignored, exactly like the old shell script), with the same
            # forced add failure. read-tree still runs for real, so the temp
            # index equals HEAD's own tree; the pipeline treats that as
            # "nothing changed" and DELETES the previously-good latest
            # pointer outright: total silent loss of the safety net (FE).
            original_checked = autosave._checked
            autosave._checked = lambda result, step: result
            autosave._run_git = _fail_add
            try:
                bad2 = autosave.snapshot(toplevel, "s1", "test")
                self.assertEqual(
                    bad2.get("reason"), "clean",
                    "REINJECTION CHECK: with return-code checking neutralized, a "
                    "failed add must be silently treated as 'nothing changed' "
                    "(this is how FE loses the safety net); if this assertion "
                    "fails, the test is not calibrated")
                self.assertNotEqual(
                    _git(toplevel, "rev-parse", "-q", "--verify", ref).returncode, 0,
                    "REINJECTION CHECK: the previously-good latest pointer must be "
                    "gone under the neutralized checker (FE: total silent loss of "
                    "the safety net); if this assertion fails, the test is not "
                    "calibrated")
            finally:
                autosave._checked = original_checked
                autosave._run_git = original_run_git

    def test_empty_tree_is_refused_explicitly(self):
        # A second, independent guard (belt-and-braces): even with no
        # patching at all, a truly empty repository must never publish the
        # universal empty tree sha as a snapshot.
        with tempfile.TemporaryDirectory() as base:
            empty_repo = os.path.join(base, "empty")
            os.makedirs(empty_repo)
            _init_repo(empty_repo)
            toplevel = autosave.resolve_toplevel(empty_repo)
            result = autosave.snapshot(toplevel, "s1", "test")
            self.assertEqual(result, {"ok": False, "reason": "empty-tree"})


class TestCalibratedFI(unittest.TestCase):
    """FI: AUTOSAVE_EVERY of 0 or a non-number crashed the hook with exit 1.
    Fixed by parsing every env var defensively, always falling back with one
    warning, and never raising."""

    def test_bad_values_fall_back_with_exactly_one_warning(self):
        cases = {"unset": None, "zero": "0", "negative": "-5",
                 "non_numeric": "abc", "absurd": "99999999999999999999"}
        old_env = os.environ.get("BROTHERMODE_AUTOSAVE_EVERY")
        try:
            for label, raw in cases.items():
                if raw is None:
                    os.environ.pop("BROTHERMODE_AUTOSAVE_EVERY", None)
                else:
                    os.environ["BROTHERMODE_AUTOSAVE_EVERY"] = raw
                cap = io.StringIO()
                with contextlib.redirect_stderr(cap):
                    n = autosave._parse_int_env(
                        "BROTHERMODE_AUTOSAVE_EVERY", autosave.DEFAULT_TICK_EVERY)
                self.assertEqual(n, autosave.DEFAULT_TICK_EVERY,
                                  "case %s did not fall back to the default" % label)
                self.assertIsInstance(n, int)
                self.assertGreater(n, 0)
                warn_lines = [l for l in cap.getvalue().splitlines() if l.strip()]
                if label == "unset":
                    self.assertEqual(warn_lines, [], "an unset var must not warn at all")
                else:
                    self.assertEqual(len(warn_lines), 1,
                                      "case %s must warn with exactly ONE line, got: %r"
                                      % (label, cap.getvalue()))
        finally:
            if old_env is None:
                os.environ.pop("BROTHERMODE_AUTOSAVE_EVERY", None)
            else:
                os.environ["BROTHERMODE_AUTOSAVE_EVERY"] = old_env

    def test_bad_config_end_to_end_tick_still_exits_0(self):
        with tempfile.TemporaryDirectory() as repo:
            _init_repo(repo)
            _write(os.path.join(repo, "a.txt"), "v1")
            _git(repo, "add", "-A")
            _git(repo, "commit", "-qm", "init")
            for raw in (None, "0", "-5", "abc", "99999999999999999999"):
                env = dict(os.environ, BROTHERMODE_AUTOSAVE="1")
                if raw is None:
                    env.pop("BROTHERMODE_AUTOSAVE_EVERY", None)
                else:
                    env["BROTHERMODE_AUTOSAVE_EVERY"] = raw
                r = subprocess.run(
                    [sys.executable, os.path.join(HERE, "bm_autosave.py"), "tick"],
                    input=json.dumps({"cwd": repo, "session_id": "fi-e2e"}),
                    text=True, capture_output=True, env=env)
                self.assertEqual(r.returncode, 0,
                                  "BROTHERMODE_AUTOSAVE_EVERY=%r must still exit 0 (FI): %s"
                                  % (raw, r.stderr))

    def test_calibrated_reinjecting_naive_parsing_crashes(self):
        # CALIBRATION: the old shell script did the unguarded equivalent of
        # `int(os.environ[name])` ($((n % TICK_EVERY)) in shell terms).
        # Patch the PRODUCT function to that naive shape and confirm the
        # calibrated check now fails for the FI reason: a non-numeric value
        # raises immediately, and a zero value is accepted and later blows
        # up the very modulo operation the tick hook depends on.
        def _naive(name, default, **kw):
            return int(os.environ.get(name, default))

        original = autosave._parse_int_env
        autosave._parse_int_env = _naive
        old_env = os.environ.get("BROTHERMODE_AUTOSAVE_EVERY")
        try:
            os.environ["BROTHERMODE_AUTOSAVE_EVERY"] = "abc"
            with self.assertRaises(
                    ValueError,
                    msg="REINJECTION CHECK: naive parsing must raise on a "
                        "non-numeric value (this is FI); if this assertion "
                        "fails, the test is not calibrated"):
                autosave._parse_int_env("BROTHERMODE_AUTOSAVE_EVERY", autosave.DEFAULT_TICK_EVERY)

            os.environ["BROTHERMODE_AUTOSAVE_EVERY"] = "0"
            n = autosave._parse_int_env("BROTHERMODE_AUTOSAVE_EVERY", autosave.DEFAULT_TICK_EVERY)
            self.assertEqual(n, 0, "naive parsing lets zero through unrejected")
            with self.assertRaises(
                    ZeroDivisionError,
                    msg="REINJECTION CHECK: AUTOSAVE_EVERY=0 must crash the tick "
                        "modulo exactly like the old shell script (FI); if this "
                        "assertion fails, the test is not calibrated"):
                5 % n
        finally:
            autosave._parse_int_env = original
            if old_env is None:
                os.environ.pop("BROTHERMODE_AUTOSAVE_EVERY", None)
            else:
                os.environ["BROTHERMODE_AUTOSAVE_EVERY"] = old_env


class TestCalibratedF2b(unittest.TestCase):
    """F2b: invoked from a subdirectory, the snapshot silently omitted
    root-level changes. Fixed by resolving the toplevel first and running
    every git call with -C <toplevel>."""

    def test_snapshot_from_subdirectory_still_covers_repo_root(self):
        with tempfile.TemporaryDirectory() as base:
            repo = os.path.join(base, "repo")
            sub = os.path.join(repo, "sub")
            os.makedirs(sub)
            _init_repo(repo)
            _write(os.path.join(repo, "root_file.txt"), "v1")
            _write(os.path.join(sub, "sub_file.txt"), "v1")
            _git(repo, "add", "-A")
            _git(repo, "commit", "-qm", "init")

            _write(os.path.join(repo, "root_file.txt"), "v2-from-subdir-run")

            result = _run_precompact(sub, "s1")
            self.assertTrue(result["ok"], result)
            shown = _git(repo, "show", "%s:root_file.txt" % result["commit"])
            self.assertEqual(shown.returncode, 0)
            self.assertIn("v2-from-subdir-run", shown.stdout,
                          "a snapshot triggered from a subdirectory omitted a "
                          "root-level change (F2b)")

            # CALIBRATION: reinject the old behavior (never resolve the true
            # toplevel; just use whatever directory the hook happened to
            # pass, like the old script's `cd "$repo"`) by making
            # resolve_toplevel an identity function, and confirm the
            # calibrated check now fails for the F2b reason: with git scoped
            # to the subdirectory, the '.' pathspec in `git add -A -- .`
            # covers only that subdirectory, so the root-level edit is
            # silently omitted.
            original = autosave.resolve_toplevel
            autosave.resolve_toplevel = lambda start_dir: start_dir
            try:
                _write(os.path.join(repo, "root_file.txt"), "v3-should-be-missed")
                result2 = _run_precompact(sub, "s2")
                # Real HEAD never advanced (commit-tree only ever wrote a
                # dangling commit reachable through the custom ref, never
                # the branch), so HEAD^{tree} is still the ORIGINAL tree.
                # With git scoped to sub/ by the broken toplevel, `add -A
                # -- .` cannot see the root-level edit at all, so the temp
                # index ends up identical to HEAD's own tree and the
                # pipeline concludes "nothing changed": the root-level
                # change is not merely stale in the snapshot, it is
                # invisible to it entirely.
                self.assertEqual(
                    result2.get("reason"), "clean",
                    "REINJECTION CHECK: with toplevel resolution neutralized, git "
                    "is scoped to the subdirectory, so a root-level edit is "
                    "invisible to `add -A -- .` and the tool wrongly concludes "
                    "nothing changed (this is F2b); if this assertion fails, the "
                    "test is not calibrated")
                head_sha = _git(repo, "rev-parse", "HEAD").stdout.strip()
                shown2 = _git(repo, "show", "%s:root_file.txt" % head_sha)
                self.assertNotIn(
                    "v3-should-be-missed", shown2.stdout,
                    "the root-level edit must be nowhere in git's view of this "
                    "'clean' snapshot, confirming it was never captured")
            finally:
                autosave.resolve_toplevel = original


class TestCalibratedJ(unittest.TestCase):
    """J: the next session printed "your files are autosaved" without
    checking that a snapshot exists. This module owns the WRITE side of the
    fix (a receipt row a reader can honestly check); the compact-hint reader
    itself lives in tools/bm_telemetry.py, out of this change's fence."""

    def test_receipt_is_the_honest_record_a_reader_would_need(self):
        with tempfile.TemporaryDirectory() as base:
            repo = os.path.join(base, "repo")
            os.makedirs(repo)
            _init_repo(repo)
            _write(os.path.join(repo, "a.txt"), "v1")
            _git(repo, "add", "-A")
            _git(repo, "commit", "-qm", "init")
            toplevel = autosave.resolve_toplevel(repo)
            wtid = autosave.worktree_id_for(toplevel)

            self.assertFalse(autosave.has_receipt(toplevel, wtid, "s1"),
                              "no store exists yet; has_receipt must be an honest "
                              "False, never a guess")

            bs.init_project(toplevel).close()
            _write(os.path.join(repo, "wip.txt"), "WIP")
            res = autosave.snapshot(toplevel, "s1", "test")
            self.assertTrue(res["ok"], res)

            self.assertTrue(autosave.has_receipt(toplevel, wtid, "s1"))
            self.assertFalse(
                autosave.has_receipt(toplevel, wtid, "s-never-ran"),
                "a session that never snapshotted must never appear to have one")

            store = bs.Store(toplevel, create=False)
            try:
                row = store.conn.execute(
                    "SELECT worktree_id, snapshot_sha, tree_sha FROM autosave_receipts "
                    "WHERE session_id=?", ("s1",)).fetchone()
            finally:
                store.close()
            self.assertIsNotNone(row, "no receipt row was written for a successful snapshot")
            self.assertEqual(row["worktree_id"], wtid)
            self.assertEqual(row["snapshot_sha"], res["commit"])
            self.assertEqual(row["tree_sha"], res["tree"])

            # CALIBRATION: reinject the old world (no receipt mechanism at
            # all) by neutralizing the writer, and confirm the calibrated
            # check now fails for the J reason: a real, successful snapshot
            # leaves nothing a reader could honestly check, which is exactly
            # why the old hint could only ever assume, never verify.
            original = autosave._write_receipt
            autosave._write_receipt = lambda *a, **kw: None
            try:
                _write(os.path.join(repo, "wip2.txt"), "WIP2")
                res2 = autosave.snapshot(toplevel, "s2", "test")
                self.assertTrue(res2["ok"], "the snapshot itself must still succeed")
                self.assertFalse(
                    autosave.has_receipt(toplevel, wtid, "s2"),
                    "REINJECTION CHECK: with receipt-writing neutralized, a real, "
                    "successful snapshot leaves no honest record (this is J's "
                    "root cause); if this assertion fails, the test is not "
                    "calibrated")
            finally:
                autosave._write_receipt = original


class TestCalibratedGateARetentionSortKey(unittest.TestCase):
    """GATE A (prerelease fix round): retention pruned the newest snapshot.
    Snapshot refs were sorted as whole strings, so the session id outranked
    the timestamp and a session whose id sorts early was treated as older
    than every snapshot from a session whose id sorts late, no matter when
    either was actually taken. Reproduced 2026-07-26: ten snapshots from
    one session, then the newest from another, and the pruner deleted THE
    NEWEST while keeping all ten older ones. Already fixed by hand (sorting
    on the stamp alone, via _snapshot_sort_key); this test is the
    calibrated proof the fix stays fixed."""

    def _two_session_scenario(self, repo, old_session, new_session):
        """Ten OLDER snapshots from a session whose id sorts LATE
        ("zzz..."), then the ONE NEWEST from a session whose id sorts
        EARLY ("aaa..."). A tiny sleep between snapshots keeps _stamp()'s
        microsecond timestamps strictly increasing, so "newest" is
        unambiguous regardless of how fast this machine runs git."""
        _init_repo(repo)
        _write(os.path.join(repo, "a.txt"), "v1")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", "init")
        toplevel = autosave.resolve_toplevel(repo)
        wtid = autosave.worktree_id_for(toplevel)
        old_env = os.environ.get("BROTHERMODE_AUTOSAVE_RETAIN")
        os.environ["BROTHERMODE_AUTOSAVE_RETAIN"] = "100"  # no auto-prune while building
        try:
            for i in range(10):
                _write(os.path.join(repo, "wip.txt"), "OLD-%d" % i)
                res = autosave.snapshot(toplevel, old_session, "old %d" % i)
                self.assertTrue(res["ok"], res)
                time.sleep(0.002)
            _write(os.path.join(repo, "marker.txt"), "THE-NEWEST-SNAPSHOT")
            newest = autosave.snapshot(toplevel, new_session, "the newest")
            self.assertTrue(newest["ok"], newest)
        finally:
            if old_env is None:
                os.environ.pop("BROTHERMODE_AUTOSAVE_RETAIN", None)
            else:
                os.environ["BROTHERMODE_AUTOSAVE_RETAIN"] = old_env
        return toplevel, wtid, newest

    def test_prune_keeps_the_newest_snapshot_regardless_of_session_id_order(self):
        with tempfile.TemporaryDirectory() as repo:
            toplevel, wtid, newest = self._two_session_scenario(
                repo, "zzz-old-session", "aaa-new-session")
            autosave._prune_old_snapshots(toplevel, wtid, retain=5)
            self.assertEqual(
                _git(toplevel, "rev-parse", "-q", "--verify", newest["ref"]).returncode, 0,
                "the newest snapshot (session 'aaa-new-session', taken LAST) was "
                "pruned even though it is the most recent work; a session id "
                "that sorts early must never be mistaken for old work")
            shown = _git(toplevel, "show", "%s:marker.txt" % newest["commit"])
            self.assertEqual(shown.returncode, 0)
            self.assertIn("THE-NEWEST-SNAPSHOT", shown.stdout,
                          "the newest snapshot survived the ref but lost its content")

            # CALIBRATION: reinject the old whole-refname sort by patching
            # the PRODUCT symbol _snapshot_sort_key back to identity, and
            # confirm the calibrated check now fails for the GATE A reason:
            # the newest snapshot (session id 'aaa...', sorts lexically
            # BEFORE 'zzz...' regardless of timestamp) is pruned as though
            # it were the oldest.
            original = autosave._snapshot_sort_key
            autosave._snapshot_sort_key = lambda ref: ref
            try:
                with tempfile.TemporaryDirectory() as repo2:
                    toplevel2, wtid2, newest2 = self._two_session_scenario(
                        repo2, "zzz-old-session", "aaa-new-session")
                    autosave._prune_old_snapshots(toplevel2, wtid2, retain=5)
                    self.assertNotEqual(
                        _git(toplevel2, "rev-parse", "-q", "--verify",
                             newest2["ref"]).returncode, 0,
                        "REINJECTION CHECK: with the whole-refname sort restored, "
                        "the newest snapshot must be pruned because its session id "
                        "sorts lexically before the older session's (this is GATE "
                        "A); if this assertion fails, the test is not calibrated")
            finally:
                autosave._snapshot_sort_key = original


class TestCalibratedGateFReceiptOutlivesPrunedSnapshot(unittest.TestCase):
    """GATE F (prerelease fix round): a receipt outlives the snapshot that
    made it true. Reproduced: thirteen sessions, retention ten, and the
    pruned session's receipt row survived, so has_receipt reported safety
    for work whose ref was gone. Fixed by deleting the receipt rows for
    refs the pruner deletes, in the same call."""

    def test_pruned_snapshots_lose_their_receipts(self):
        with tempfile.TemporaryDirectory() as repo:
            _init_repo(repo)
            _write(os.path.join(repo, "a.txt"), "v1")
            _git(repo, "add", "-A")
            _git(repo, "commit", "-qm", "init")
            toplevel = autosave.resolve_toplevel(repo)
            wtid = autosave.worktree_id_for(toplevel)
            bs.init_project(toplevel).close()
            os.environ["BROTHERMODE_AUTOSAVE_RETAIN"] = "100"
            try:
                results = []
                for i in range(13):
                    _write(os.path.join(repo, "wip.txt"), "WIP-%d" % i)
                    res = autosave.snapshot(toplevel, "s%d" % i, "step %d" % i)
                    self.assertTrue(res["ok"], res)
                    results.append(res)
                    time.sleep(0.001)
                # Every one of the thirteen sessions has an honest receipt
                # before pruning ever runs.
                for i, res in enumerate(results):
                    self.assertTrue(autosave.has_receipt(toplevel, wtid, "s%d" % i),
                                     "session s%d has no receipt before pruning" % i)

                autosave._prune_old_snapshots(toplevel, wtid, retain=10)
                r = _git(toplevel, "for-each-ref", "--format=%(refname)",
                          "%s/%s/" % (autosave.REF_NAMESPACE, wtid))
                remaining_refs = [l for l in r.stdout.splitlines()
                                   if l.strip() and not l.endswith("/latest")]
                self.assertEqual(len(remaining_refs), 10, remaining_refs)

                # The three OLDEST sessions (s0, s1, s2) were pruned: their
                # receipts must be gone too, or has_receipt keeps reporting
                # safety for work whose ref no longer exists.
                for i in range(3):
                    self.assertFalse(
                        autosave.has_receipt(toplevel, wtid, "s%d" % i),
                        "session s%d's ref was pruned but its receipt survived "
                        "(this is GATE F): has_receipt reports safety for work "
                        "that is actually gone" % i)
                for i in range(3, 13):
                    self.assertTrue(
                        autosave.has_receipt(toplevel, wtid, "s%d" % i),
                        "session s%d's ref was kept but its receipt was deleted "
                        "too eagerly" % i)
            finally:
                os.environ.pop("BROTHERMODE_AUTOSAVE_RETAIN", None)

            # CALIBRATION: reinject the old behavior (pruning never touches
            # receipts) by neutralizing the PRODUCT function
            # _delete_receipts_for_shas, and confirm the calibrated check
            # now fails for the GATE F reason: a pruned session's receipt
            # survives and has_receipt reports it as still safe.
            with tempfile.TemporaryDirectory() as repo2:
                _init_repo(repo2)
                _write(os.path.join(repo2, "a.txt"), "v1")
                _git(repo2, "add", "-A")
                _git(repo2, "commit", "-qm", "init")
                toplevel2 = autosave.resolve_toplevel(repo2)
                wtid2 = autosave.worktree_id_for(toplevel2)
                bs.init_project(toplevel2).close()
                original = autosave._delete_receipts_for_shas
                autosave._delete_receipts_for_shas = lambda *a, **kw: None
                os.environ["BROTHERMODE_AUTOSAVE_RETAIN"] = "100"
                try:
                    for i in range(13):
                        _write(os.path.join(repo2, "wip.txt"), "WIP-%d" % i)
                        res = autosave.snapshot(toplevel2, "s%d" % i, "step %d" % i)
                        self.assertTrue(res["ok"], res)
                        time.sleep(0.001)
                    autosave._prune_old_snapshots(toplevel2, wtid2, retain=10)
                    self.assertTrue(
                        autosave.has_receipt(toplevel2, wtid2, "s0"),
                        "REINJECTION CHECK: with receipt deletion neutralized, a "
                        "pruned session's receipt must still report as safe (this "
                        "is GATE F); if this assertion fails, the test is not "
                        "calibrated")
                finally:
                    autosave._delete_receipts_for_shas = original
                    os.environ.pop("BROTHERMODE_AUTOSAVE_RETAIN", None)


class TestCrossProjectReceiptGuard(unittest.TestCase):
    """Wiring item (prerelease fix round): a snapshot must never write its
    receipt into ANOTHER project's store when the resolved root points
    elsewhere (a BrotherMode marker found further up the tree than this
    snapshot's own git toplevel)."""

    def test_receipt_never_written_into_a_parent_projects_store(self):
        with tempfile.TemporaryDirectory() as base:
            # The PARENT directory is its own BrotherMode project.
            bs.init_project(base).close()
            child = os.path.join(base, "child")
            os.makedirs(child)
            _init_repo(child)
            _write(os.path.join(child, "a.txt"), "v1")
            _git(child, "add", "-A")
            _git(child, "commit", "-qm", "init")
            child_top = autosave.resolve_toplevel(child)
            self.assertEqual(os.path.realpath(child_top), os.path.realpath(child))

            # Sanity: resolve_root from the child walks UP PAST the child's
            # own .git and finds the PARENT's .brothermode marker, which is
            # exactly the scenario the guard exists for.
            resolved_root, _source = bs.resolve_root(child_top)
            self.assertEqual(os.path.realpath(resolved_root), os.path.realpath(base))

            _write(os.path.join(child, "wip.txt"), "WIP")
            cap = io.StringIO()
            with contextlib.redirect_stderr(cap):
                res = autosave.snapshot(child_top, "s1", "test")
            self.assertTrue(res["ok"], "the snapshot itself must still succeed")
            self.assertIn("another project", cap.getvalue())

            parent_store = bs.Store(base, create=False)
            try:
                rows = parent_store.conn.execute(
                    "SELECT * FROM autosave_receipts").fetchall()
            finally:
                parent_store.close()
            self.assertEqual(
                len(rows), 0,
                "the child worktree's receipt was written into the PARENT "
                "project's store instead of being refused")


class TestRetention(unittest.TestCase):
    """Requirement 8 (not itself a defect-table row): keep the last N
    snapshots per worktree, never the only one."""

    def test_keeps_last_n_per_worktree(self):
        with tempfile.TemporaryDirectory() as repo:
            _init_repo(repo)
            _write(os.path.join(repo, "a.txt"), "v1")
            _git(repo, "add", "-A")
            _git(repo, "commit", "-qm", "init")
            toplevel = autosave.resolve_toplevel(repo)
            wtid = autosave.worktree_id_for(toplevel)
            old_env = os.environ.get("BROTHERMODE_AUTOSAVE_RETAIN")
            os.environ["BROTHERMODE_AUTOSAVE_RETAIN"] = "3"
            try:
                for i in range(6):
                    _write(os.path.join(repo, "wip.txt"), "WIP-%d" % i)
                    res = autosave.snapshot(toplevel, "s1", "tick %d" % i)
                    self.assertTrue(res["ok"], res)
                prefix = "%s/%s/" % (autosave.REF_NAMESPACE, wtid)
                r = _git(toplevel, "for-each-ref", "--format=%(refname)", prefix)
                refs = [l for l in r.stdout.splitlines() if l.strip() and not l.endswith("/latest")]
                self.assertEqual(len(refs), 3, "expected retention to keep exactly 3: %s" % refs)
            finally:
                if old_env is None:
                    os.environ.pop("BROTHERMODE_AUTOSAVE_RETAIN", None)
                else:
                    os.environ["BROTHERMODE_AUTOSAVE_RETAIN"] = old_env

    def test_never_prunes_the_only_snapshot(self):
        with tempfile.TemporaryDirectory() as repo:
            _init_repo(repo)
            _write(os.path.join(repo, "a.txt"), "v1")
            _git(repo, "add", "-A")
            _git(repo, "commit", "-qm", "init")
            toplevel = autosave.resolve_toplevel(repo)
            wtid = autosave.worktree_id_for(toplevel)
            old_env = os.environ.get("BROTHERMODE_AUTOSAVE_RETAIN")
            os.environ["BROTHERMODE_AUTOSAVE_RETAIN"] = "1"
            try:
                _write(os.path.join(repo, "wip.txt"), "only WIP")
                res = autosave.snapshot(toplevel, "s1", "test")
                self.assertTrue(res["ok"], res)
                prefix = "%s/%s/" % (autosave.REF_NAMESPACE, wtid)
                r = _git(toplevel, "for-each-ref", "--format=%(refname)", prefix)
                refs = [l for l in r.stdout.splitlines() if l.strip() and not l.endswith("/latest")]
                self.assertEqual(len(refs), 1)
            finally:
                if old_env is None:
                    os.environ.pop("BROTHERMODE_AUTOSAVE_RETAIN", None)
                else:
                    os.environ["BROTHERMODE_AUTOSAVE_RETAIN"] = old_env


class TestReceiptDegradesGracefully(unittest.TestCase):
    """Requirement 9's own text: "warn once and continue" when the store is
    absent or refuses. Autosave is advisory and must never block on it."""

    def test_snapshot_still_succeeds_when_store_is_absent(self):
        with tempfile.TemporaryDirectory() as repo:
            _init_repo(repo)
            _write(os.path.join(repo, "a.txt"), "v1")
            _git(repo, "add", "-A")
            _git(repo, "commit", "-qm", "init")
            toplevel = autosave.resolve_toplevel(repo)
            # deliberately no bs.init_project(): no store exists here
            cap = io.StringIO()
            with contextlib.redirect_stderr(cap):
                _write(os.path.join(repo, "wip.txt"), "WIP")
                res = autosave.snapshot(toplevel, "s1", "test")
            self.assertTrue(res["ok"], "a missing store must never fail the snapshot itself")
            self.assertIn("no receipt", cap.getvalue())


class TestNeverBlocksOnUnexpectedError(unittest.TestCase):
    """The absolute backstop: main() always exits 0, even on an internal bug."""

    def test_main_exits_0_even_when_snapshot_raises(self):
        with tempfile.TemporaryDirectory() as repo:
            _init_repo(repo)
            _write(os.path.join(repo, "a.txt"), "v1")
            _git(repo, "add", "-A")
            _git(repo, "commit", "-qm", "init")
            original = autosave.snapshot
            autosave.snapshot = lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("boom"))
            try:
                with self.assertRaises(SystemExit) as ctx:
                    old_stdin = sys.stdin
                    sys.stdin = io.StringIO(json.dumps({"cwd": repo, "session_id": "s1"}))
                    try:
                        autosave.main(["precompact"])
                    finally:
                        sys.stdin = old_stdin
                self.assertEqual(ctx.exception.code, 0)
            finally:
                autosave.snapshot = original


if __name__ == "__main__":
    unittest.main(verbosity=2)
