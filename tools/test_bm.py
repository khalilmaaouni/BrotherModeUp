#!/usr/bin/env python3
"""BrotherMode regression tests. Standard library only (no pip install), matching
the zero-dependency ethos of the tools. Run: python3 tools/test_bm.py

These exist because an external review found a real secret-leak in the resume
brief that a test would have caught. Each test here guards a claim the project
makes about itself: secrets are redacted, sensitive files are owner-only, project
identity does not collide, and the autosave captures untracked work non-invasively.
"""
import io, os, json, stat, sys, tempfile, subprocess, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))

# Import bm_telemetry as a module regardless of cwd.
spec = importlib.util.spec_from_file_location("bm_telemetry", os.path.join(HERE, "bm_telemetry.py"))
bm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bm)
sys.modules["bm_telemetry"] = bm

import unittest


class TestRedaction(unittest.TestCase):
    def test_secret_shapes_are_masked(self):
        cases = [
            "the prod password is hunter2",
            "PROD_DB_PASSWORD=s3cr3tvalue",
            "sk-ant-api03-ABCDEFGHIJKLMNOP",
            "Authorization: Bearer abcdef1234567890xyz",
            "ssn 123-45-6789",
        ]
        for c in cases:
            clean, n = bm.redact(c)
            self.assertGreater(n, 0, "no redaction fired on: %s" % c)
            self.assertIn("[REDACTED]", clean)
        # a benign correction must survive intact
        clean, n = bm.redact("always use the staging bucket, never production")
        self.assertEqual(n, 0)
        self.assertIn("staging bucket", clean)


class TestResumeBrief(unittest.TestCase):
    def test_brief_redacts_and_is_owner_only(self):
        with tempfile.TemporaryDirectory() as d:
            os.environ["BROTHERMODE_VAULT"] = os.path.join(d, "vault")
            # rebuild the module's paths against the temp vault
            import importlib
            importlib.reload(bm)
            repo = os.path.join(d, "acme", "backend")
            os.makedirs(repo)
            tp = os.path.join(d, "t.jsonl")
            msgs = [{"type": "user", "message": {"content": "the prod password is hunter2"}}]
            msgs += [{"type": "assistant", "message": {"content": [
                {"type": "text", "text": "using token sk-ant-api03-ABCDEFGHIJKLMNOP"},
                {"type": "tool_use", "name": "Bash",
                 "input": {"command": "curl -H 'Authorization: Bearer abcdef1234567890xyz' x"}}]}}]
            io.open(tp, "w").write("\n".join(json.dumps(m) for m in msgs))
            payload = json.dumps({"transcript_path": tp, "cwd": repo})
            old = sys.stdin
            sys.stdin = io.StringIO(payload)
            try:
                bm.cmd_precompact_brief()
            finally:
                sys.stdin = old
            teldir = os.path.join(os.environ["BROTHERMODE_VAULT"], "99-System", "telemetry")
            briefs = [f for f in os.listdir(teldir) if f.startswith("last-resume-")]
            self.assertEqual(len(briefs), 1)
            path = os.path.join(teldir, briefs[0])
            body = io.open(path).read()
            for secret in ("hunter2", "sk-ant-api03-ABCDEFGHIJKLMNOP", "abcdef1234567890xyz"):
                self.assertNotIn(secret, body, "resume brief leaked: %s" % secret)
            self.assertIn("[REDACTED]", body)
            mode = stat.S_IMODE(os.stat(path).st_mode)
            self.assertEqual(mode, 0o600, "resume brief must be owner-only, got %o" % mode)


class TestProjectIdentity(unittest.TestCase):
    def test_same_basename_different_path_no_collision(self):
        a = bm._project_of("/tmp/client-a/backend")
        b = bm._project_of("/tmp/client-b/backend")
        self.assertNotEqual(a, b, "same-basename projects collided: %s == %s" % (a, b))
        self.assertEqual(a, bm._project_of("/tmp/client-a/backend"), "identity must be stable")


class TestAutosave(unittest.TestCase):
    def test_snapshot_captures_untracked_without_touching_tree(self):
        sh = os.path.join(HERE, "bm_autosave.sh")
        if not os.path.exists(sh):
            self.skipTest("bm_autosave.sh not present")
        with tempfile.TemporaryDirectory() as repo:
            def git(*a):
                return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True)
            git("init", "-q")
            git("config", "user.email", "t@t.t"); git("config", "user.name", "t")
            io.open(os.path.join(repo, "tracked.txt"), "w").write("v1")
            git("add", "-A"); git("commit", "-qm", "init")
            io.open(os.path.join(repo, "tracked.txt"), "w").write("v2")
            io.open(os.path.join(repo, "untracked_new.txt"), "w").write("WIP-WORK")
            before = git("status", "--porcelain").stdout
            before_head = git("rev-parse", "HEAD").stdout
            vdir = tempfile.mkdtemp()
            env = dict(os.environ, BROTHERMODE_VAULT=vdir)
            subprocess.run(["sh", sh, "precompact"], input=json.dumps({"cwd": repo}),
                           text=True, env=env)
            # working tree and branch untouched
            self.assertEqual(before, git("status", "--porcelain").stdout)
            self.assertEqual(before_head, git("rev-parse", "HEAD").stdout)
            # ref created and it contains the untracked file
            ref = git("rev-parse", "-q", "--verify", "refs/brothermode/autosave")
            self.assertEqual(ref.returncode, 0, "autosave ref was not created")
            shown = git("show", "refs/brothermode/autosave:untracked_new.txt").stdout
            self.assertIn("WIP-WORK", shown, "autosave did not capture the untracked file")
            # secret-shaped files must NOT enter the snapshot
            io.open(os.path.join(repo, ".env"), "w").write("SECRET=leak")
            subprocess.run(["sh", sh, "precompact"], input=json.dumps({"cwd": repo}),
                           text=True, env=env)
            envobj = git("cat-file", "-e", "refs/brothermode/autosave:.env")
            self.assertNotEqual(envobj.returncode, 0, ".env leaked into the autosave snapshot")


class TestHandoff(unittest.TestCase):
    def test_handoff_redacts_and_preserves(self):
        with tempfile.TemporaryDirectory() as v:
            base = os.path.join(v, "10-Projects", "demo", "Sessions")
            os.makedirs(base)
            proj = os.path.dirname(base)
            io.open(os.path.join(proj, "Overview.md"), "w").write(
                "builds X. the prod password is hunter2")
            io.open(os.path.join(base, "s.md"), "w").write("used DB_PASSWORD=s3cr3t here")
            env = dict(os.environ, BROTHERMODE_VAULT=v)
            with tempfile.TemporaryDirectory() as cwd:
                r = subprocess.run([sys.executable, os.path.join(HERE, "bm_telemetry.py"),
                                    "handoff", "demo"], env=env, cwd=cwd,
                                   capture_output=True, text=True)
                out = os.path.join(cwd, "handoff-demo.md")
                self.assertTrue(os.path.exists(out), "handoff file not written")
                body = io.open(out).read()
                self.assertNotIn("hunter2", body)
                self.assertNotIn("s3cr3t", body)
                self.assertIn("builds X", body)
                self.assertIn("[REDACTED]", body)


class TestThreadMode(unittest.TestCase):
    """Thread mode's contract: nothing auto-flips, the cap holds, and switching
    OFF mid-project is LOSSLESS (the founder's hard requirement)."""

    def _run(self, cwd, *args):
        return subprocess.run([sys.executable, os.path.join(HERE, "bm_threads.py"), *args],
                              cwd=cwd, capture_output=True, text=True)

    def test_recommend_never_flips_mode(self):
        with tempfile.TemporaryDirectory() as d:
            r = self._run(d, "recommend", "5")
            self.assertIn("RECOMMENDATION", r.stdout)
            # advice only: no mode file may be created by recommending
            self.assertFalse(os.path.exists(os.path.join(d, "threads", "thread-mode.json")),
                             "recommend must never flip or create mode state")

    def test_cap_is_enforced(self):
        with tempfile.TemporaryDirectory() as d:
            self._run(d, "on")
            for n in ("a", "b", "c"):
                self._run(d, "start", n, "obj " + n)
            r = self._run(d, "start", "dee", "one too many")
            self.assertIn("CAP", r.stdout, "the 3-active cap must refuse a 4th thread")

    def test_off_is_lossless_and_parks(self):
        with tempfile.TemporaryDirectory() as d:
            io.open(os.path.join(d, "STATE.md"), "w").write("# Project STATE\n")
            self._run(d, "on")
            self._run(d, "start", "payments", "build payments")
            self._run(d, "checkpoint", "payments", "--decision", "chose Stripe",
                      "--next", "wire webhook")
            self._run(d, "off")
            state = io.open(os.path.join(d, "STATE.md")).read()
            # the expensive-to-re-derive context must survive the switch
            self.assertIn("chose Stripe", state, "decision lost when thread mode was turned off")
            self.assertIn("wire webhook", state, "next intent lost when thread mode was turned off")
            # and the thread must be parked, not deleted
            self.assertTrue(os.path.isdir(os.path.join(d, "threads", "payments")),
                            "thread directory was deleted; it must stay resumable")
            mode = json.load(io.open(os.path.join(d, "threads", "thread-mode.json")))
            self.assertEqual(mode["mode"], "off")
            self.assertEqual(mode["threads"]["payments"]["state"], "parked")

    def test_adopt_absorbs_a_dead_thread(self):
        with tempfile.TemporaryDirectory() as d:
            io.open(os.path.join(d, "STATE.md"), "w").write("# Project STATE\n")
            self._run(d, "on")
            self._run(d, "start", "search", "build search")
            self._run(d, "checkpoint", "search", "--decision", "use trigram index")
            self._run(d, "adopt", "search")
            state = io.open(os.path.join(d, "STATE.md")).read()
            self.assertIn("use trigram index", state, "adopted thread's context was orphaned")


class TestStrictMode(unittest.TestCase):
    def test_strict_exits_nonzero_on_fail(self):
        # A vault with an active session but no session log forces a FAIL check.
        import datetime
        with tempfile.TemporaryDirectory() as v:
            teld = os.path.join(v, "99-System", "telemetry")
            os.makedirs(teld)
            now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            io.open(os.path.join(teld, "outcomes.jsonl"), "w").write(
                json.dumps({"schema": 2, "ts": now, "session_id": "x", "project": "p",
                            "tool_calls": 5, "api_msgs": 9}) + "\n")
            env = dict(os.environ, BROTHERMODE_VAULT=v)
            score = os.path.join(HERE, "bm_score.py")
            strict = subprocess.run([sys.executable, score, "--strict"], env=env,
                                    capture_output=True, text=True)
            advisory = subprocess.run([sys.executable, score], env=env,
                                      capture_output=True, text=True)
            self.assertEqual(strict.returncode, 1, "--strict must exit nonzero on a FAIL")
            self.assertEqual(advisory.returncode, 0, "advisory mode must never block (exit 0)")


if __name__ == "__main__":
    unittest.main(verbosity=2)
