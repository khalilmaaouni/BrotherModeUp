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
                secret_path = os.path.join(recovered_dir, "secret.txt")
                self.assertTrue(os.path.exists(secret_path))
                if os.name == "posix":
                    # The load-bearing guarantee, asserted at full strength on
                    # the platforms where a POSIX mode actually controls access.
                    self.assertEqual(
                        mode, 0o700,
                        "recovered worktree dir must be owner-only (0700); got %04o "
                        "(BLOCKER 1: mkdtemp's 0700 must survive, never be discarded "
                        "and recreated at the process umask)" % mode)
                    self.assertIn("0700", printed,
                                  "the recovery output must state the permissions it gave "
                                  "the recovered directory")
                else:
                    # Windows does not have POSIX modes: access is governed by
                    # ACLs, and os.chmod there can only toggle a read-only bit,
                    # which _chmod_best_effort's own docstring in bm_store.py
                    # already says. Asserting 0700 here would not be a stricter
                    # test, it would be a FALSE one, and it was: adding this
                    # suite to CI (audit finding 14) failed on both Windows legs
                    # for exactly this reason while passing on all four POSIX
                    # legs.
                    #
                    # So this asserts the two things that remain true and
                    # meaningful on Windows: the recovered work is there, and
                    # the tool REPORTS the protection it actually achieved
                    # rather than claiming one it did not. The product prints
                    # the real mode, so honesty is testable even where the
                    # guarantee is not available.
                    #
                    # The gap itself is not hidden by this branch: it is written
                    # down in docs/KNOWN-LIMITS.md, because "recovered work is
                    # owner-only" is a POSIX-only promise and a Windows user
                    # relying on it would be relying on nothing.
                    self.assertRegex(
                        printed, r"0[0-7]{3}",
                        "even where the mode cannot be enforced, the recovery "
                        "output must STATE the mode actually achieved, so a "
                        "founder can see what protection this platform gave")
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
            #
            # FINDING 1 (external audit, 2026-07-27) added a SECOND,
            # independent guard on the same failure: has_receipt now
            # re-resolves the row's own snapshot_sha against the refs that
            # actually exist (_receipt_snapshot_is_live), so a surviving
            # receipt for a deleted ref answers False even with the pruner's
            # deletion neutralized. Reproducing the OLD world therefore
            # requires neutralizing BOTH halves, which is what the second
            # patch below does. This assertion is unchanged and is not
            # weakened: each guard also has its own calibrated proof, GATE
            # F's own non-calibration half above (receipts really are
            # deleted with their refs) and
            # TestCalibratedFinding1ReceiptOutlivesItsRef (the ref check
            # really is load-bearing).
            with tempfile.TemporaryDirectory() as repo2:
                _init_repo(repo2)
                _write(os.path.join(repo2, "a.txt"), "v1")
                _git(repo2, "add", "-A")
                _git(repo2, "commit", "-qm", "init")
                toplevel2 = autosave.resolve_toplevel(repo2)
                wtid2 = autosave.worktree_id_for(toplevel2)
                bs.init_project(toplevel2).close()
                original = autosave._delete_receipts_for_shas
                original_live = autosave._receipt_snapshot_is_live
                autosave._delete_receipts_for_shas = lambda *a, **kw: None
                autosave._receipt_snapshot_is_live = lambda *a, **kw: True
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
                    autosave._receipt_snapshot_is_live = original_live
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


def _repo_with_commit(base, name="repo"):
    """A scratch repo with one commit, the shape almost every test below
    starts from. Returns (repo path, toplevel, worktree_id)."""
    repo = os.path.join(base, name)
    os.makedirs(repo)
    _init_repo(repo)
    _write(os.path.join(repo, "a.txt"), "v1")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "init")
    toplevel = autosave.resolve_toplevel(repo)
    return repo, toplevel, autosave.worktree_id_for(toplevel)


def _fail_step(step):
    """A _run_git stand-in that fails one named git subcommand and passes
    everything else through, so a snapshot can be made to fail at a REAL git
    call rather than by patching the pipeline's own logic."""
    original = autosave._run_git

    def _patched(toplevel_arg, *args, **kw):
        if args and args[0] == step:
            return subprocess.CompletedProcess(args, 1, "", "simulated %s failure" % step)
        return original(toplevel_arg, *args, **kw)
    return original, _patched


class TestCalibratedFinding1FalseAssurance(unittest.TestCase):
    """FINDING 1 (external security audit, 2026-07-27), the highest-harm
    defect in the audit: the tool claimed work was safe when it was not.

    The exact sequence, reproduced here end to end:
        10:00  a snapshot succeeds and writes a receipt
        10:30  more files change
        11:00  the next PreCompact snapshot FAILS
        11:05  the session resumes; a receipt for this session still exists
               -> the old reader said "your files are autosaved", and the
                  work from 10:30 was in no snapshot at all.

    The cause was the QUESTION, not the wording: has_receipt asked whether
    this session had EVER snapshotted (historical), and the hint printed a
    present-tense safety claim from that answer. verify_recoverable asks
    whether the work is recoverable RIGHT NOW: a one-shot event that every
    attempt resets to pending, marked saved only after the ref is written
    and read back, and re-resolved to the recorded sha before any claim."""

    def _ten_thirty_eleven(self, base):
        repo, toplevel, wtid = _repo_with_commit(base)
        bs.init_project(toplevel).close()
        # 10:00 a snapshot that really succeeds.
        _write(os.path.join(repo, "wip.txt"), "first hour of work")
        first = autosave.snapshot(toplevel, "sess-1", "precompact")
        self.assertTrue(first["ok"], first)
        # 10:30 more work, not in any snapshot yet.
        _write(os.path.join(repo, "wip2.txt"), "THE SECOND HOUR, THE PART THAT MATTERS")
        return repo, toplevel, wtid, first

    def _eleven_oclock_failure(self, toplevel):
        original, patched = _fail_step("add")
        autosave._run_git = patched
        try:
            failed = autosave.snapshot(toplevel, "sess-1", "precompact")
        finally:
            autosave._run_git = original
        self.assertFalse(failed["ok"], "the 11:00 snapshot was supposed to fail")
        return failed

    def test_a_failed_attempt_revokes_the_earlier_claim(self):
        with tempfile.TemporaryDirectory() as base:
            repo, toplevel, wtid, first = self._ten_thirty_eleven(base)
            cap = io.StringIO()
            with contextlib.redirect_stderr(cap):
                self._eleven_oclock_failure(toplevel)

            # Ground truth: the 10:30 work is in NO snapshot.
            self.assertNotEqual(
                _git(toplevel, "cat-file", "-e", "%s:wip2.txt" % first["commit"]).returncode, 0,
                "the scenario is wrong: the newest work is already in the snapshot")

            # The HISTORICAL question still answers yes, exactly as it did
            # when it was the basis for the claim: the 10:00 receipt and its
            # ref both still exist. This is the false assurance, preserved
            # here as evidence rather than argued about.
            self.assertTrue(
                autosave.has_receipt(toplevel, wtid, "sess-1"),
                "the scenario is wrong: the earlier receipt must survive, or "
                "there is no false assurance to close")

            # The PRESENT-TENSE question refuses.
            verdict = autosave.verify_recoverable(toplevel, wtid, "sess-1")
            self.assertEqual(
                verdict["state"], "unverified",
                "a failed newest attempt must revoke the earlier claim: %r" % (verdict,))
            self.assertIn("FAILED", verdict["detail"])

    def test_calibrated_without_the_pending_reset_the_false_claim_returns(self):
        # CALIBRATION: the reset-to-pending before every attempt is what
        # makes a failure override an earlier success. Neutralize exactly
        # that PRODUCT function for the failing attempt (the successful one
        # ran normally first) and the tool goes straight back to reporting
        # the 10:00 snapshot as though it covered the 10:30 work.
        with tempfile.TemporaryDirectory() as base:
            repo, toplevel, wtid, first = self._ten_thirty_eleven(base)
            original = autosave.begin_snapshot_event
            autosave.begin_snapshot_event = lambda *a, **kw: None
            try:
                cap = io.StringIO()
                with contextlib.redirect_stderr(cap):
                    self._eleven_oclock_failure(toplevel)
            finally:
                autosave.begin_snapshot_event = original
            verdict = autosave.verify_recoverable(toplevel, wtid, "sess-1")
            self.assertEqual(
                verdict["state"], "verified",
                "REINJECTION CHECK: with the pending reset neutralized, a FAILED "
                "attempt must leave the previous success standing and the tool must "
                "wrongly report the work as saved (this is FINDING 1); if this "
                "assertion fails, the test is not calibrated: %r" % (verdict,))

    def test_verified_claim_names_the_ref_and_sha_it_is_claiming(self):
        with tempfile.TemporaryDirectory() as base:
            repo, toplevel, wtid = _repo_with_commit(base)
            _write(os.path.join(repo, "wip.txt"), "work")
            res = autosave.snapshot(toplevel, "sess-1", "precompact")
            self.assertTrue(res["ok"], res)
            verdict = autosave.verify_recoverable(toplevel, wtid, "sess-1")
            self.assertEqual(verdict["state"], "verified", verdict)
            self.assertEqual(verdict["ref"], res["ref"])
            self.assertEqual(verdict["sha"], res["commit"])
            self.assertTrue(verdict["captured_at"], "a claim must say when it captured")

    def test_event_is_consumed_once_so_a_later_resume_cannot_reuse_it(self):
        with tempfile.TemporaryDirectory() as base:
            repo, toplevel, wtid = _repo_with_commit(base)
            _write(os.path.join(repo, "wip.txt"), "work")
            self.assertTrue(autosave.snapshot(toplevel, "sess-1", "precompact")["ok"])
            self.assertEqual(
                autosave.verify_recoverable(toplevel, wtid, "sess-1")["state"], "verified")
            self.assertEqual(
                autosave.verify_recoverable(toplevel, wtid, "sess-1")["state"], "none",
                "the event describes ONE compaction; a second resume must not be "
                "handed the same claim again")

    def test_a_deleted_ref_is_refused_even_with_a_saved_event(self):
        with tempfile.TemporaryDirectory() as base:
            repo, toplevel, wtid = _repo_with_commit(base)
            _write(os.path.join(repo, "wip.txt"), "work")
            res = autosave.snapshot(toplevel, "sess-1", "precompact")
            self.assertTrue(res["ok"], res)
            _git(toplevel, "update-ref", "-d", res["ref"])
            verdict = autosave.verify_recoverable(toplevel, wtid, "sess-1")
            self.assertEqual(verdict["state"], "unverified", verdict)
            self.assertIn("no longer exists", verdict["detail"])

    def test_unknown_is_never_a_claim_in_either_direction(self):
        with tempfile.TemporaryDirectory() as base:
            plain = os.path.join(base, "not-a-repo")
            os.makedirs(plain)
            verdict = autosave.verify_recoverable(plain, "deadbeef", "sess-1")
            self.assertEqual(
                verdict["state"], "unknown",
                "with no readable git directory the tool must claim nothing, in "
                "either direction: %r" % (verdict,))


class TestCalibratedFinding1ReceiptOutlivesItsRef(unittest.TestCase):
    """FINDING 1, the second half: has_receipt was a bare existence probe
    (SELECT 1 ... LIMIT 1), with no read of the row's own snapshot_sha and
    no check that the snapshot still existed. Receipt deletion is
    best-effort, so any receipt that outlived its ref kept reporting safe."""

    def test_a_receipt_whose_snapshot_ref_is_gone_is_not_safety(self):
        with tempfile.TemporaryDirectory() as base:
            repo, toplevel, wtid = _repo_with_commit(base)
            bs.init_project(toplevel).close()
            _write(os.path.join(repo, "wip.txt"), "work")
            res = autosave.snapshot(toplevel, "sess-1", "precompact")
            self.assertTrue(res["ok"], res)
            self.assertTrue(autosave.has_receipt(toplevel, wtid, "sess-1"))

            # Delete the ref BEHIND the receipt, the way a hand-run
            # `git update-ref -d` or a failed best-effort cleanup would.
            _git(toplevel, "update-ref", "-d", res["ref"])
            _git(toplevel, "update-ref", "-d", autosave.latest_ref(wtid))
            store = bs.Store(toplevel, create=False)
            try:
                rows = store.conn.execute(
                    "SELECT COUNT(*) AS n FROM autosave_receipts WHERE session_id=?",
                    ("sess-1",)).fetchone()
            finally:
                store.close()
            self.assertEqual(rows["n"], 1, "the receipt row must still be there, or "
                                            "this test proves nothing")
            self.assertFalse(
                autosave.has_receipt(toplevel, wtid, "sess-1"),
                "a receipt whose snapshot ref no longer exists must not report as "
                "safety (FINDING 1)")

            # CALIBRATION: reinject the old shape by patching the PRODUCT
            # function that re-resolves the row's sha back to "trust the
            # row", and confirm the bare existence probe reports the deleted
            # snapshot as still safe.
            original = autosave._receipt_snapshot_is_live
            autosave._receipt_snapshot_is_live = lambda *a, **kw: True
            try:
                self.assertTrue(
                    autosave.has_receipt(toplevel, wtid, "sess-1"),
                    "REINJECTION CHECK: with the ref re-resolution neutralized, a "
                    "receipt for a deleted snapshot must report as safe (this is "
                    "FINDING 1); if this assertion fails, the test is not calibrated")
            finally:
                autosave._receipt_snapshot_is_live = original


class TestCalibratedFinding13LatestPointer(unittest.TestCase):
    """FINDING 13: the shared latest pointer was last-writer-wins. Both
    writes now carry the old value they expect, so a losing writer fails
    loudly instead of silently winning."""

    def test_a_clean_check_never_deletes_a_newer_pointer(self):
        with tempfile.TemporaryDirectory() as base:
            repo, toplevel, wtid = _repo_with_commit(base)
            ref = autosave.latest_ref(wtid)
            _write(os.path.join(repo, "wip.txt"), "first")
            first = autosave.snapshot(toplevel, "s1", "test")
            self.assertTrue(first["ok"], first)
            _write(os.path.join(repo, "wip.txt"), "second")
            second = autosave.snapshot(toplevel, "s1", "test")
            self.assertTrue(second["ok"], second)

            # The race, made deterministic: point latest back at the OLDER
            # snapshot, let the clean path read that value, then move latest
            # to the NEWER snapshot before the delete lands. That is exactly
            # a concurrent dirty snapshot publishing between the read and
            # the delete.
            _git(toplevel, "update-ref", ref, first["commit"])
            original = autosave._run_git
            state = {"raced": False}

            def _race(toplevel_arg, *args, **kw):
                result = original(toplevel_arg, *args, **kw)
                if not state["raced"] and args[:3] == ("rev-parse", "-q", "--verify") \
                        and args[3:4] == (ref,):
                    state["raced"] = True
                    original(toplevel_arg, "update-ref", ref, second["commit"])
                return result

            autosave._run_git = _race
            cap = io.StringIO()
            try:
                os.remove(os.path.join(repo, "wip.txt"))
                with contextlib.redirect_stderr(cap):
                    clean = autosave.snapshot(toplevel, "s1", "test")
            finally:
                autosave._run_git = original
            self.assertEqual(clean["reason"], "clean", clean)
            self.assertTrue(state["raced"], "the race never fired; the test is inert")
            self.assertEqual(
                _git(toplevel, "rev-parse", "-q", "--verify", ref).stdout.strip(),
                second["commit"],
                "a clean check deleted a pointer that a concurrent writer had just "
                "moved to a NEWER snapshot (FINDING 13)")
            self.assertIn("moved to a newer snapshot", cap.getvalue(),
                          "losing the compare-and-swap must be loud, not silent")

            # CALIBRATION: reinject last-writer-wins by patching the PRODUCT
            # function back to a delete that ignores the expected old value.
            _git(toplevel, "update-ref", ref, first["commit"])
            _write(os.path.join(repo, "wip.txt"), "third")
            self.assertTrue(autosave.snapshot(toplevel, "s1", "test")["ok"])
            _git(toplevel, "update-ref", ref, first["commit"])
            original_del = autosave._delete_ref_cas
            autosave._delete_ref_cas = lambda toplevel_a, r, expected_old: original(
                toplevel_a, "update-ref", "-d", r)
            state["raced"] = False
            autosave._run_git = _race
            try:
                os.remove(os.path.join(repo, "wip.txt"))
                with contextlib.redirect_stderr(io.StringIO()):
                    autosave.snapshot(toplevel, "s1", "test")
            finally:
                autosave._run_git = original
                autosave._delete_ref_cas = original_del
            self.assertNotEqual(
                _git(toplevel, "rev-parse", "-q", "--verify", ref).returncode, 0,
                "REINJECTION CHECK: without the expected old value, the clean check "
                "must delete the newer writer's pointer outright (this is FINDING "
                "13); if this assertion fails, the test is not calibrated")

    def test_recover_falls_back_to_the_newest_snapshot_when_latest_is_lost(self):
        with tempfile.TemporaryDirectory() as base:
            repo, toplevel, wtid = _repo_with_commit(base)
            _write(os.path.join(repo, "wip.txt"), "older work")
            older = autosave.snapshot(toplevel, "s1", "test")
            self.assertTrue(older["ok"], older)
            time.sleep(0.002)
            _write(os.path.join(repo, "wip.txt"), "THE NEWEST WORK")
            newest = autosave.snapshot(toplevel, "s1", "test")
            self.assertTrue(newest["ok"], newest)

            # The pointer is lost (a racing deleter, a botched cleanup); the
            # snapshots themselves are all still there.
            _git(toplevel, "update-ref", "-d", autosave.latest_ref(wtid))

            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                autosave.cmd_recover([repo])
            text = out.getvalue()
            self.assertIn("fell back", text, text)
            lines = [l for l in text.splitlines() if l.strip()]
            idx = next(i for i, l in enumerate(lines) if "NEW worktree at" in l)
            recovered = lines[idx + 1].strip()
            try:
                self.assertEqual(_read(os.path.join(recovered, "wip.txt")),
                                  "THE NEWEST WORK",
                                  "the fallback recovered a snapshot, but not the newest")
            finally:
                _git(toplevel, "worktree", "remove", "--force", recovered)

            # CALIBRATION: reinject the old world (no enumeration at all) by
            # neutralizing the PRODUCT fallback, and confirm recovery goes
            # back to reporting nothing found while two good snapshots sit
            # right there.
            original = autosave._fallback_snapshot
            autosave._fallback_snapshot = lambda *a, **kw: ("", "")
            try:
                out2 = io.StringIO()
                with contextlib.redirect_stdout(out2):
                    autosave.cmd_recover([repo])
                self.assertIn(
                    "no autosave found", out2.getvalue(),
                    "REINJECTION CHECK: without the enumerate-and-fall-back path, a "
                    "lost pointer must read as no autosave at all (this is FINDING "
                    "13); if this assertion fails, the test is not calibrated")
            finally:
                autosave._fallback_snapshot = original

    def test_fallback_never_resurrects_deliberately_discarded_wip(self):
        """FD and FINDING 13 meet here: the fallback must not undo the clean
        clear. A snapshot older than the recorded clean check stays
        unoffered, and recovery says so instead of silently handing back WIP
        the founder threw away."""
        with tempfile.TemporaryDirectory() as base:
            repo, toplevel, wtid = _repo_with_commit(base)
            _write(os.path.join(repo, "wip.txt"), "discarded WIP")
            self.assertTrue(autosave.snapshot(toplevel, "s1", "test")["ok"])
            os.remove(os.path.join(repo, "wip.txt"))
            self.assertEqual(autosave.snapshot(toplevel, "s1", "test")["reason"], "clean")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                autosave.cmd_recover([repo])
            text = out.getvalue()
            self.assertIn("no autosave found", text, text)
            self.assertIn("snapshot ref(s) do exist", text,
                          "an unoffered snapshot must still be listed, never hidden")


class TestFinding16Denylist(unittest.TestCase):
    """FINDING 16: the secret denylist was a frozen ten-entry list inherited
    from the deleted V1 shell script, so id_ed25519 (the modern default ssh
    key), .npmrc, .netrc, cloud credentials, kube configs, and
    service-account JSON all walked into snapshots."""

    # The pin. If this tuple changes, someone changed what autosave will
    # capture, and that is a decision a human makes deliberately, not a diff
    # that slips through. Narrowing it fails here first.
    PINNED = (
        ":(exclude,glob)**/.env", ":(exclude).env", ":(exclude,glob)**/.env.*",
        ":(exclude,glob)**/*.pem", ":(exclude,glob)**/*.key", ":(exclude,glob)**/*.p12",
        ":(exclude,glob)**/*.keystore", ":(exclude,glob)**/id_rsa", ":(exclude,glob)**/id_dsa",
        ":(exclude,glob)**/*.pfx",
        ":(exclude,glob)**/id_ecdsa", ":(exclude,glob)**/id_ecdsa_sk",
        ":(exclude,glob)**/id_ed25519", ":(exclude,glob)**/id_ed25519_sk",
        ":(exclude,glob)**/.ssh/**", ":(exclude,glob)**/.gnupg/**",
        ":(exclude,glob)**/.aws/**", ":(exclude,glob)**/.kube/**",
        ":(exclude,glob)**/.docker/**",
        ":(exclude,glob)**/.npmrc", ":(exclude,glob)**/.netrc", ":(exclude,glob)**/_netrc",
        ":(exclude,glob)**/.pgpass", ":(exclude,glob)**/.git-credentials",
        ":(exclude,glob)**/.htpasswd", ":(exclude,glob)**/.pypirc",
        ":(exclude,glob)**/credentials.json",
        ":(exclude,glob)**/*service?account*.json",
        ":(exclude,glob)**/application_default_credentials.json",
        ":(exclude,glob)**/*.p8", ":(exclude,glob)**/*.jks", ":(exclude,glob)**/*.ppk",
        ":(exclude,glob)**/*.kdbx", ":(exclude,glob)**/*.ovpn",
        ":(exclude,glob)**/*.asc", ":(exclude,glob)**/*.gpg",
        ":(exclude,glob)**/*.tfvars", ":(exclude,glob)**/secrets.yaml",
        ":(exclude,glob)**/secrets.yml",
    )
    # The original ten, listed separately so a future edit cannot drop one
    # while keeping the total plausible.
    V1_TEN = PINNED[:10]

    SECRET_FILES = (
        ".env", "sub/.env", ".env.local", "id_rsa", "id_ed25519", "sub/id_ed25519",
        ".ssh/id_ed25519", "sub/.ssh/config", ".npmrc", ".netrc", "_netrc", ".pgpass",
        ".git-credentials", ".htpasswd", ".pypirc", ".aws/credentials",
        "deep/nested/.aws/credentials", ".kube/config", ".gnupg/secring.gpg",
        "credentials.json", "service-account.json", "my-service_account-key.json",
        "a.pem", "b.key", "c.p12", "d.keystore", "e.pfx", "f.p8", "g.jks", "h.ppk",
        "i.kdbx", "j.ovpn", "k.asc", "l.gpg", "terraform.tfvars", "prod.auto.tfvars",
        "secrets.yaml", "secrets.yml", "application_default_credentials.json",
        ".docker/config.json",
    )
    KEEP_FILES = ("keep_me.txt", "src/main.py", "sub/config", "credentials/keep.py")

    def test_denylist_is_pinned_and_never_narrows(self):
        self.assertEqual(autosave.SECRET_EXCLUDE_PATHSPECS, self.PINNED,
                          "the secret denylist changed. Adding is fine; confirm "
                          "nothing was REMOVED, then update this pin deliberately.")
        for p in self.V1_TEN:
            self.assertIn(p, autosave.SECRET_EXCLUDE_PATHSPECS,
                          "%s came from the V1 shell script and must never be "
                          "dropped" % p)

    def test_no_secret_shape_enters_a_snapshot(self):
        with tempfile.TemporaryDirectory() as base:
            repo, toplevel, _wtid = _repo_with_commit(base)
            for rel in self.SECRET_FILES + self.KEEP_FILES:
                path = os.path.join(repo, rel)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                _write(path, "PAYLOAD-%s" % rel)
            with contextlib.redirect_stderr(io.StringIO()):
                res = autosave.snapshot(toplevel, "s1", "test")
            self.assertTrue(res["ok"], res)
            staged = set(_git(toplevel, "ls-tree", "-r", "--name-only",
                              res["commit"]).stdout.split())
            leaked = sorted(set(self.SECRET_FILES) & staged)
            self.assertEqual(leaked, [], "secret-shaped files entered the snapshot: %s" % leaked)
            for keep in self.KEEP_FILES:
                self.assertIn(keep, staged,
                              "%s is not a secret and must still be captured; "
                              "over-exclusion loses real work" % keep)

    def test_gitignored_files_never_enter_a_snapshot(self):
        """Layer one of the boundary: git's OWN ignore status. This was
        always true and never tested, which makes it an assumption rather
        than a guarantee."""
        with tempfile.TemporaryDirectory() as base:
            repo, toplevel, _wtid = _repo_with_commit(base)
            _write(os.path.join(repo, ".gitignore"), "local-secrets/\n*.mysecret\n")
            os.makedirs(os.path.join(repo, "local-secrets"))
            _write(os.path.join(repo, "local-secrets", "token.txt"), "TOKEN")
            _write(os.path.join(repo, "creds.mysecret"), "TOKEN")
            _write(os.path.join(repo, "wip.txt"), "real work")
            with contextlib.redirect_stderr(io.StringIO()):
                res = autosave.snapshot(toplevel, "s1", "test")
            self.assertTrue(res["ok"], res)
            staged = set(_git(toplevel, "ls-tree", "-r", "--name-only",
                              res["commit"]).stdout.split())
            self.assertNotIn("local-secrets/token.txt", staged)
            self.assertNotIn("creds.mysecret", staged)
            self.assertIn("wip.txt", staged)

    def test_founder_can_extend_the_denylist(self):
        """Layer three: no enumeration is ever complete, so the list is
        extensible at runtime."""
        with tempfile.TemporaryDirectory() as base:
            repo, toplevel, _wtid = _repo_with_commit(base)
            _write(os.path.join(repo, "house-format.secretz"), "PRIVATE")
            _write(os.path.join(repo, "wip.txt"), "real work")
            old = os.environ.get(autosave.EXTRA_EXCLUDE_ENV)
            os.environ[autosave.EXTRA_EXCLUDE_ENV] = "**/*.secretz"
            try:
                with contextlib.redirect_stderr(io.StringIO()):
                    res = autosave.snapshot(toplevel, "s1", "test")
            finally:
                if old is None:
                    os.environ.pop(autosave.EXTRA_EXCLUDE_ENV, None)
                else:
                    os.environ[autosave.EXTRA_EXCLUDE_ENV] = old
            self.assertTrue(res["ok"], res)
            staged = set(_git(toplevel, "ls-tree", "-r", "--name-only",
                              res["commit"]).stdout.split())
            self.assertNotIn("house-format.secretz", staged)
            self.assertIn("wip.txt", staged)

    def test_newly_captured_untracked_files_are_named_in_a_warning(self):
        """Enumeration can only block shapes someone thought of, so what
        DOES get captured has to be visible when it happens."""
        with tempfile.TemporaryDirectory() as base:
            repo, toplevel, _wtid = _repo_with_commit(base)
            _write(os.path.join(repo, "never-reviewed.txt"), "who knows what is in here")
            cap = io.StringIO()
            with contextlib.redirect_stderr(cap):
                res = autosave.snapshot(toplevel, "s1", "test")
            self.assertTrue(res["ok"], res)
            self.assertIn("never-reviewed.txt", cap.getvalue(),
                          "the founder must see which untracked files just entered a "
                          "snapshot: %r" % cap.getvalue())

    def test_classifier_does_not_call_every_file_secret(self):
        """The directory shapes broke the old fnmatch classifier, whose '*'
        crossed '/' and so matched everything once "**/.ssh/**" was added."""
        self.assertTrue(autosave._is_secret_shaped(".ssh/id_ed25519"))
        self.assertTrue(autosave._is_secret_shaped("a/b/.aws/credentials"))
        self.assertTrue(autosave._is_secret_shaped(".env"))
        self.assertTrue(autosave._is_secret_shaped("deep/dir/x.pem"))
        self.assertFalse(autosave._is_secret_shaped("src/main.py"))
        self.assertFalse(autosave._is_secret_shaped("sub/config"))
        self.assertFalse(autosave._is_secret_shaped("credentials/keep.py"))


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
