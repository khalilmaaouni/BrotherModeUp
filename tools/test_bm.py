#!/usr/bin/env python3
"""BrotherMode regression tests. Standard library only (no pip install), matching
the zero-dependency ethos of the tools. Run: python3 tools/test_bm.py

These exist because an external review found a real secret-leak in the resume
brief that a test would have caught. Each test here guards a claim the project
makes about itself: secrets are redacted, sensitive files are owner-only, project
identity does not collide, and the autosave captures untracked work non-invasively.
"""
import contextlib, glob, io, os, json, re, shutil, stat, sys, tempfile, subprocess, importlib.util

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

    def test_private_key_is_masked_as_a_block_not_just_its_header(self):
        # Finding 7: SECRET_PATTERNS matched only the -----BEGIN----- line, so
        # every line of base64 key material after it went to disk unmasked,
        # while SECURITY.md publicly claims private keys are redacted.
        key = ("-----BEGIN RSA PRIVATE KEY-----\n"
               "MIIEowIBAAKCAQEAx7Vv9kQm2bYh3JqL8sFdTnW4pRzC5aXeUgHiN0oPvBtMcSyD\n"
               "QeKlZrXfAoGBAJk2TtVuWqLmNbHcYdRxPjEgFsAoZnKUvIwCyMlBtDqSeRhXfGpO\n"
               "n0aUyLcVdMwEtIbKqPjRzXsHfGnAoWlYcTuDeMkQvBpSrZiNxJgHdFaOcVtLmEyU\n"
               "-----END RSA PRIVATE KEY-----")

        clean, n = bm.redact("here is the deploy key:\n" + key + "\nplease rotate it")
        self.assertGreater(n, 0, "no redaction fired on a private key block")
        for line in key.splitlines():
            self.assertNotIn(line, clean, "key material survived redaction: %s" % line[:20])
        self.assertNotIn("MIIEowIBAAKCAQEAx7Vv", clean, "the key body was written out verbatim")
        self.assertIn("please rotate it", clean, "redaction swallowed the surrounding prose")
        self.assertIn("here is the deploy key", clean,
                      "redaction swallowed the prose before the key")

    def test_private_key_header_alone_still_masks_what_follows_it(self):
        # The reviewer's planted secret ended at the header line, with the body
        # (or nothing) after it. A truncated block must still not leak.
        clean, n = bm.redact("-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEAx7Vv9kQm2bYh3JqL")
        self.assertGreater(n, 0)
        self.assertNotIn("MIIEowIBAAKCAQEAx7Vv9kQm2bYh3JqL", clean)

    def test_private_key_pattern_does_not_eat_ordinary_prose(self):
        clean, n = bm.redact(
            "-----BEGIN RSA PRIVATE KEY----- was pasted into the ticket yesterday "
            "and we should ask the platform team to rotate it")
        self.assertIn("ask the platform team to rotate it", clean,
                      "the private key pattern over-matched into ordinary prose")

    def test_intent_redacts_secret_but_preserves_content(self):
        with tempfile.TemporaryDirectory() as v, tempfile.TemporaryDirectory() as repo:
            env = dict(os.environ, BROTHERMODE_VAULT=v)
            r = subprocess.run(
                [sys.executable, os.path.join(HERE, "bm_telemetry.py"), "intent",
                 "next: rotate the key, because PROD_DB_PASSWORD=hunter2 leaked"],
                env=env, cwd=repo, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0)
            intent_files = glob.glob(os.path.join(v, "99-System", "telemetry", "intent-*.log"))
            self.assertEqual(len(intent_files), 1, "intent log not written")
            body = io.open(intent_files[0]).read()
            self.assertNotIn("hunter2", body, "intent log leaked the secret")
            self.assertIn("[REDACTED]", body)
            self.assertIn("rotate the key", body)
            self.assertIn("leaked", body)

    def test_rate_redacts_secret_but_preserves_content(self):
        with tempfile.TemporaryDirectory() as v, tempfile.TemporaryDirectory() as repo:
            env = dict(os.environ, BROTHERMODE_VAULT=v)
            r = subprocess.run(
                [sys.executable, os.path.join(HERE, "bm_telemetry.py"), "rate",
                 "--score", "4",
                 "--task", "rotate creds, api_key=sk-ant-api03-ABCDEFGHIJKLMNOP",
                 "--note", "found while reviewing the staging bucket"],
                env=env, cwd=repo, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0)
            ratings_path = os.path.join(v, "99-System", "telemetry", "ratings.jsonl")
            self.assertTrue(os.path.exists(ratings_path), "ratings.jsonl not written")
            body = io.open(ratings_path).read()
            self.assertNotIn("sk-ant-api03-ABCDEFGHIJKLMNOP", body, "ratings.jsonl leaked the secret")
            self.assertIn("[REDACTED]", body)
            self.assertIn("rotate creds", body)
            self.assertIn("staging bucket", body)


class TestRegistryFallbackRedactor(unittest.TestCase):
    """bm_registry falls back to its own pattern set when bm_telemetry cannot be
    loaded. That set is weaker, and weaker redaction must never be silent."""

    def _run_isolated(self, snippet):
        with tempfile.TemporaryDirectory() as d:
            shutil.copy(os.path.join(HERE, "bm_registry.py"), d)
            return subprocess.run(
                [sys.executable, "-c",
                 "import sys;sys.path.insert(0, %r);import bm_registry as r\n%s" % (d, snippet)],
                capture_output=True, text=True, cwd=d)

    def test_fallback_warns_that_it_covers_less(self):
        r = self._run_isolated("print('loaded')")
        self.assertIn("warning", r.stderr.lower(),
                      "the reduced fallback pattern set was used silently")
        for missing in ("github_pat", "slack", "JWT", "card"):
            self.assertIn(missing.lower(), r.stderr.lower(),
                          "the warning must name what it stops covering: %s" % missing)

    def test_fallback_still_masks_a_private_key_block(self):
        r = self._run_isolated(
            "print(r.redact_text('-----BEGIN RSA PRIVATE KEY-----\\n"
            "MIIEowIBAAKCAQEAx7Vv9kQm2bYh3JqL8sFdTnW4pRzC5aXeUgHiN0oPvBtMcSyD\\n"
            "-----END RSA PRIVATE KEY-----'))")
        self.assertNotIn("MIIEowIBAAKCAQEAx7Vv", r.stdout,
                         "the fallback leaked private key material")
        self.assertIn("[REDACTED]", r.stdout)


class TestFounderNoteFileModes(unittest.TestCase):
    """Finding 8: ratings.jsonl and reviews.jsonl carry founder-written note
    text, so they are as sensitive as corrections.jsonl, which is already 0600.
    atomic_append defaults to 0644 and neither caller overrode it."""

    def _mode(self, path):
        return stat.S_IMODE(os.stat(path).st_mode)

    def test_ratings_file_is_owner_only(self):
        with tempfile.TemporaryDirectory() as v, tempfile.TemporaryDirectory() as repo:
            env = dict(os.environ, BROTHERMODE_VAULT=v)
            subprocess.run([sys.executable, os.path.join(HERE, "bm_telemetry.py"), "rate",
                            "--score", "4", "--task", "ship the fence",
                            "--note", "the client contact said to keep this quiet"],
                           env=env, cwd=repo, capture_output=True, text=True)
            p = os.path.join(v, "99-System", "telemetry", "ratings.jsonl")
            self.assertTrue(os.path.exists(p), "ratings.jsonl not written")
            self.assertEqual(self._mode(p), 0o600,
                             "founder note text must be owner-only, got %o" % self._mode(p))

    def test_reviews_file_is_owner_only(self):
        with tempfile.TemporaryDirectory() as v, tempfile.TemporaryDirectory() as repo:
            env = dict(os.environ, BROTHERMODE_VAULT=v)
            subprocess.run([sys.executable, os.path.join(HERE, "bm_telemetry.py"),
                            "review-mark", "chased the client about the invoice"],
                           env=env, cwd=repo, capture_output=True, text=True)
            p = os.path.join(v, "99-System", "telemetry", "reviews.jsonl")
            self.assertTrue(os.path.exists(p), "reviews.jsonl not written")
            self.assertEqual(self._mode(p), 0o600,
                             "founder note text must be owner-only, got %o" % self._mode(p))

    def test_an_existing_world_readable_notes_file_is_tightened(self):
        # The two files already exist on this machine at 0644, and os.open only
        # applies its mode when it CREATES the file.
        with tempfile.TemporaryDirectory() as v, tempfile.TemporaryDirectory() as repo:
            teld = os.path.join(v, "99-System", "telemetry")
            os.makedirs(teld)
            p = os.path.join(teld, "reviews.jsonl")
            io.open(p, "w").write("")
            os.chmod(p, 0o644)
            env = dict(os.environ, BROTHERMODE_VAULT=v)
            subprocess.run([sys.executable, os.path.join(HERE, "bm_telemetry.py"),
                            "review-mark", "note"],
                           env=env, cwd=repo, capture_output=True, text=True)
            self.assertEqual(self._mode(p), 0o600,
                             "a pre-existing world-readable notes file must be tightened")

    def test_the_shared_ledger_is_not_tightened(self):
        # outcomes.jsonl is the shared ledger bm_score.py reads: only the
        # founder-note files change, nothing that is meant to be shared.
        self.assertEqual(bm.atomic_append.__defaults__, (0o644,),
                         "the default mode must stay 0644 for shared files")


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


class TestThreadSafety(unittest.TestCase):
    """The two defects a self-review found in thread mode, now permanent tests."""

    def _run(self, cwd, *a):
        return subprocess.run([sys.executable, os.path.join(HERE, "bm_threads.py"), *a],
                              cwd=cwd, capture_output=True, text=True)

    def test_secrets_never_reach_digest_or_absorbed_state(self):
        with tempfile.TemporaryDirectory() as d:
            io.open(os.path.join(d, "STATE.md"), "w").write("# S\n")
            self._run(d, "on"); self._run(d, "start", "pay", "build pay")
            self._run(d, "checkpoint", "pay", "--decision",
                      "used PROD_DB_PASSWORD=hunter2 to test", "--next", "rotate it")
            dig = io.open(os.path.join(d, "threads", "pay", "digest.md")).read()
            self.assertNotIn("hunter2", dig, "secret leaked into the thread digest")
            self._run(d, "off")
            st = io.open(os.path.join(d, "STATE.md")).read()
            self.assertNotIn("hunter2", st, "secret propagated into the project STATE.md")
            self.assertIn("rotate it", st, "redaction destroyed the real content")

    def test_secret_in_objective_does_not_reach_thread_files(self):
        # The registry's own copy of the objective is redacted at claim(), but
        # bm_threads.py used to write the RAW objective straight into STATE.md,
        # digest.md, and thread-mode.json. A secret pasted into a thread's
        # objective would then sit unredacted on disk and print on the dashboard.
        with tempfile.TemporaryDirectory() as d:
            io.open(os.path.join(d, "STATE.md"), "w").write("# S\n")
            self._run(d, "on")
            self._run(d, "start", "pay", "build pay using PROD_DB_PASSWORD=hunter2 now")
            state_md = io.open(os.path.join(d, "threads", "pay", "STATE.md")).read()
            digest_md = io.open(os.path.join(d, "threads", "pay", "digest.md")).read()
            mode = json.load(io.open(os.path.join(d, "threads", "thread-mode.json")))
            self.assertNotIn("hunter2", state_md, "secret leaked into the thread's STATE.md")
            self.assertNotIn("hunter2", digest_md, "secret leaked into the thread's digest.md")
            self.assertNotIn("hunter2", json.dumps(mode), "secret leaked into thread-mode.json")
            self.assertIn("[REDACTED]", state_md, "redaction destroyed the objective entirely")
            r = self._run(d, "dashboard")
            self.assertNotIn("hunter2", r.stdout, "secret leaked into the dashboard output")

    def test_dashboard_survives_a_thread_whose_objective_is_not_a_string(self):
        # The C2 defect shape in bm_threads: meta.get("objective", "")[:90]
        # raised on a hand-edited mode file, and the dashboard stopped dead
        # part-way through, hiding every thread listed after it.
        with tempfile.TemporaryDirectory() as d:
            io.open(os.path.join(d, "STATE.md"), "w").write("# S\n")
            self._run(d, "on")
            self._run(d, "start", "aaa", "first")
            self._run(d, "start", "zzz", "last")
            mp = os.path.join(d, "threads", "thread-mode.json")
            mode = json.load(io.open(mp))
            mode["threads"]["aaa"]["objective"] = 42
            io.open(mp, "w").write(json.dumps(mode))
            r = self._run(d, "dashboard")
            self.assertNotIn("swallowed error", r.stdout,
                             "the dashboard raised on a malformed objective")
            self.assertIn("zzz", r.stdout,
                          "threads after the malformed one were never printed")

    def test_dashboard_survives_a_thread_entry_that_is_not_a_dict(self):
        with tempfile.TemporaryDirectory() as d:
            io.open(os.path.join(d, "STATE.md"), "w").write("# S\n")
            self._run(d, "on")
            self._run(d, "start", "aaa", "first")
            self._run(d, "start", "zzz", "last")
            mp = os.path.join(d, "threads", "thread-mode.json")
            mode = json.load(io.open(mp))
            mode["threads"]["aaa"] = "not-a-dict"
            io.open(mp, "w").write(json.dumps(mode))
            r = self._run(d, "dashboard")
            self.assertNotIn("swallowed error", r.stdout,
                             "the dashboard raised on a non-dict thread entry")
            self.assertIn("zzz", r.stdout,
                          "threads after the malformed one were never printed")

    def test_dashboard_survives_a_mode_value_that_is_not_a_string(self):
        # Found by fuzzing the mode file: the header is the first thing printed,
        # so mode.upper() took the entire dashboard down before any thread.
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "threads"))
            io.open(os.path.join(d, "threads", "thread-mode.json"), "w").write(
                json.dumps({"mode": 5, "threads": {}}))
            r = self._run(d, "dashboard")
            self.assertNotIn("swallowed error", r.stdout,
                             "the dashboard raised on a non-string mode value")
            self.assertIn("BROTHERMODE THREADS", r.stdout)

    def test_overlap_refusal_survives_a_malformed_files_field_on_the_conflict(self):
        # The refusal message joins the conflicting record's files. A null entry
        # there raised, so the refusal never printed: the founder would see a
        # swallowed error instead of the reason their thread did not start.
        with tempfile.TemporaryDirectory() as d:
            io.open(os.path.join(d, "STATE.md"), "w").write("# S\n")
            self._run(d, "on")
            self._run(d, "start", "payments", "pay", "--files", "api/pay.py")
            rp = os.path.join(d, "threads", "registry.json")
            reg = json.load(io.open(rp))
            reg["records"]["payments"]["files"] = ["api/pay.py", None]
            io.open(rp, "w").write(json.dumps(reg))
            r = self._run(d, "start", "billing", "bill", "--files", "api/pay.py")
            self.assertNotIn("swallowed error", r.stdout,
                             "the overlap refusal raised on a malformed files field")
            self.assertIn("OVERLAP", r.stdout.upper(),
                          "the overlap must still be refused and explained")
            self.assertIn("payments", r.stdout, "the refusal must name the conflicting record")

    def test_concurrent_starts_all_register(self):
        # A thread on disk but missing from the registry is invisible to the
        # dashboard AND skipped by `off`, which would silently lose its context.
        import threading as th
        with tempfile.TemporaryDirectory() as d:
            io.open(os.path.join(d, "STATE.md"), "w").write("# S\n")
            self._run(d, "on")
            ts = [th.Thread(target=self._run, args=(d, "start", n, "obj")) for n in "abc"]
            [t.start() for t in ts]; [t.join() for t in ts]
            mode = json.load(io.open(os.path.join(d, "threads", "thread-mode.json")))
            self.assertEqual(sorted(mode["threads"]), ["a", "b", "c"],
                             "a concurrent start was lost from the registry")


class TestOffReportsHonestly(unittest.TestCase):
    def _run(self, cwd, *a, **kw):
        return subprocess.run([sys.executable, os.path.join(HERE, "bm_threads.py"), *a],
                              cwd=cwd, capture_output=True, text=True, **kw)

    def test_off_says_write_failed_and_keeps_the_thread_alive(self):
        # Finding 5: with STATE.md unwritable the registry correctly refused to
        # park anything, but `off` still flipped the mode, parked the thread and
        # printed "no digest yet (nothing to absorb)": the exact opposite of the
        # truth, on the one path where the founder most needs the truth.
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("running as root: file permissions cannot be made to block a write")
        with tempfile.TemporaryDirectory() as d:
            state_path = os.path.join(d, "STATE.md")
            io.open(state_path, "w").write("# Project STATE\n")
            self._run(d, "on")
            self._run(d, "start", "payments", "pay", "--files", "api/pay.py")
            self._run(d, "checkpoint", "payments", "--next", "wire the webhook handler")
            before = io.open(state_path).read()
            os.chmod(state_path, stat.S_IREAD)
            try:
                r = self._run(d, "off")
                if io.open(state_path).read() != before:
                    self.skipTest("could not make STATE.md unwritable in this environment")
                self.assertNotIn("nothing to absorb", r.stdout,
                                 "a FAILED handover was reported as an empty one")
                self.assertIn("WRITE FAILED", r.stdout.upper(),
                              "a failed handover must say so")
                mode = json.load(io.open(os.path.join(d, "threads", "thread-mode.json")))
                self.assertEqual(mode["mode"], "on",
                                 "mode must not flip to off when the handover failed")
                self.assertEqual(mode["threads"]["payments"]["state"], "active",
                                 "the thread must not be parked when its handover failed")
                reg = json.load(io.open(os.path.join(d, "threads", "registry.json")))
                self.assertEqual(reg["records"]["payments"]["state"], "active",
                                 "the record must stay active so a retry can still absorb it")
            finally:
                os.chmod(state_path, stat.S_IREAD | stat.S_IWRITE)

    def test_off_still_reports_a_thread_that_has_no_record_as_empty(self):
        # The other half of finding 5: "nothing to absorb" must keep meaning
        # exactly that, so the two outcomes stay distinguishable.
        with tempfile.TemporaryDirectory() as d:
            io.open(os.path.join(d, "STATE.md"), "w").write("# Project STATE\n")
            self._run(d, "on")
            self._run(d, "start", "payments", "pay", "--files", "api/pay.py")
            rp = os.path.join(d, "threads", "registry.json")
            reg = json.load(io.open(rp))
            reg["records"] = {}
            io.open(rp, "w").write(json.dumps(reg))
            r = self._run(d, "off")
            self.assertIn("nothing to absorb", r.stdout,
                          "a thread with no record is genuinely empty and must say so")
            self.assertNotIn("WRITE FAILED", r.stdout.upper(),
                             "an empty handover must not be reported as a failure")
            mode = json.load(io.open(os.path.join(d, "threads", "thread-mode.json")))
            self.assertEqual(mode["mode"], "off", "an empty handover must still turn the mode off")


    def test_off_completes_even_when_a_thread_entry_is_malformed(self):
        # Round-two sweep: off assigns into d["threads"][name], which raised on
        # a non-dict entry AFTER absorb had already drained and parked the
        # records. The mode file then never saved, so the registry said parked
        # while thread mode said ON, and the founder saw a swallowed error.
        with tempfile.TemporaryDirectory() as d:
            io.open(os.path.join(d, "STATE.md"), "w").write("# Project STATE\n")
            self._run(d, "on")
            self._run(d, "start", "payments", "pay", "--files", "api/pay.py")
            self._run(d, "checkpoint", "payments", "--next", "wire the webhook handler")
            mp = os.path.join(d, "threads", "thread-mode.json")
            mode = json.load(io.open(mp))
            mode["threads"]["ghost"] = "not-a-dict"
            io.open(mp, "w").write(json.dumps(mode))
            r = self._run(d, "off")
            self.assertNotIn("swallowed error", r.stdout,
                             "off raised on a malformed thread entry")
            self.assertIn("wire the webhook handler", io.open(os.path.join(d, "STATE.md")).read())
            mode = json.load(io.open(mp))
            self.assertEqual(mode["mode"], "off",
                             "the registry was drained but the mode file never saved")
            self.assertEqual(mode["threads"]["payments"]["state"], "parked")


class TestCapIsAtomic(unittest.TestCase):
    def test_a_cap_refused_start_leaves_no_registry_record(self):
        # Finding 6: reg.claim ran BEFORE the in-lock cap re-check, so a refused
        # start printed "CAP: not registered" and still left an active record.
        # A later claim on those files was then refused by a record the
        # dashboard never shows.
        env = dict(os.environ, BROTHERMODE_MAX_THREADS="1")
        with tempfile.TemporaryDirectory() as d:
            io.open(os.path.join(d, "STATE.md"), "w").write("# Project STATE\n")
            for a in (("on",), ("start", "payments", "pay", "--files", "api/pay.py")):
                subprocess.run([sys.executable, os.path.join(HERE, "bm_threads.py"), *a],
                               cwd=d, env=env, capture_output=True, text=True)
            r = subprocess.run([sys.executable, os.path.join(HERE, "bm_threads.py"),
                                "start", "billing", "bill", "--files", "api/bill.py"],
                               cwd=d, env=env, capture_output=True, text=True)
            self.assertIn("CAP", r.stdout, "the cap must refuse the second thread")
            reg = json.load(io.open(os.path.join(d, "threads", "registry.json")))
            self.assertNotIn("billing", reg["records"],
                             "a cap-refused start must leave no registry record behind")
            mode = json.load(io.open(os.path.join(d, "threads", "thread-mode.json")))
            self.assertNotIn("billing", mode.get("threads", {}),
                             "either the record and the thread both exist, or neither does")


class TestAdopt(unittest.TestCase):
    """adopt is a write boundary and a fence release, and used to be neither."""

    def _run(self, cwd, *a):
        return subprocess.run([sys.executable, os.path.join(HERE, "bm_threads.py"), *a],
                              cwd=cwd, capture_output=True, text=True)

    def _thread_with_secrets(self, d):
        io.open(os.path.join(d, "STATE.md"), "w").write("# Project STATE\n")
        self._run(d, "on")
        self._run(d, "start", "payments", "build payments", "--files", "api/pay.py")
        self._run(d, "checkpoint", "payments", "--next", "wire the webhook handler")
        io.open(os.path.join(d, "threads", "payments", "STATE.md"), "a").write(
            "\n## Notes\ndeploy key AKIAIOSFODNN7EXAMPLE\npassword=hunter2swordfish\n")

    def test_adopt_redacts_the_thread_text_it_appends(self):
        # Finding C3: adopt appended the thread's STATE.md and digest VERBATIM
        # into the project STATE.md, which tools/bm_autosave.sh then commits
        # into a git ref. Every sibling path in this file redacts first.
        with tempfile.TemporaryDirectory() as d:
            self._thread_with_secrets(d)
            self._run(d, "adopt", "payments")
            state = io.open(os.path.join(d, "STATE.md")).read()
            self.assertNotIn("AKIAIOSFODNN7EXAMPLE", state,
                             "adopt leaked an AWS key into the project STATE.md")
            self.assertNotIn("hunter2swordfish", state,
                             "adopt leaked a password into the project STATE.md")
            self.assertIn("[REDACTED]", state, "nothing was redacted at all")
            self.assertIn("wire the webhook handler", state,
                          "redaction destroyed the real handover content")

    def test_adopt_does_not_leave_the_digest_to_be_absorbed_twice(self):
        # Finding 4: adopt flipped the thread to adopted in thread-mode.json but
        # left the REGISTRY record active, so `off` drained the same digest
        # again and the handover appeared twice.
        with tempfile.TemporaryDirectory() as d:
            self._thread_with_secrets(d)
            self._run(d, "adopt", "payments")
            self._run(d, "off")
            state = io.open(os.path.join(d, "STATE.md")).read()
            self.assertEqual(state.count("wire the webhook handler"), 1,
                             "the adopted digest was absorbed a second time by off")

    def test_adopt_releases_the_file_fence(self):
        # Same finding, worse consequence: the record stayed active, so its
        # files stayed claimed by an owner the dashboard no longer shows.
        with tempfile.TemporaryDirectory() as d:
            self._thread_with_secrets(d)
            self._run(d, "adopt", "payments")
            reg = json.load(io.open(os.path.join(d, "threads", "registry.json")))
            self.assertNotEqual(reg["records"]["payments"]["state"], "active",
                                "the adopted record must not stay active")
            r = self._run(d, "start", "billing", "bill", "--files", "api/pay.py")
            self.assertNotIn("OVERLAP", r.stdout.upper(),
                             "an adopted thread's fence must be released")
            reg = json.load(io.open(os.path.join(d, "threads", "registry.json")))
            self.assertIn("billing", reg["records"], "the successor thread was never registered")


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

    def test_strict_exits_nonzero_when_the_checker_itself_crashes(self):
        """A crashed checker verified NOTHING, so it must not report a pass.

        The top-level handler caught every exception and exited 0 even under
        --strict, which made the CI gate worthless: any bug inside bm_score
        turned into a green build. Local runs still degrade quietly, because
        never-block is a promise to the session, not to CI."""
        with tempfile.TemporaryDirectory() as d:
            broken = os.path.join(d, "bm_score.py")
            src = io.open(os.path.join(HERE, "bm_score.py"), encoding="utf-8").read()
            src = src.replace("def main():",
                              "def main():\n    raise RuntimeError('simulated checker crash')", 1)
            io.open(broken, "w", encoding="utf-8").write(src)
            # PYTHONPATH must reach the real tools dir: bm_score imports
            # bm_telemetry as a sibling, and without this the copy dies at
            # IMPORT time with exit 1, which would make this test pass for the
            # wrong reason and prove nothing about the handler under test.
            env = dict(os.environ, BROTHERMODE_VAULT=os.path.join(d, "vault"),
                       PYTHONPATH=HERE)
            strict = subprocess.run([sys.executable, broken, "--strict"], env=env,
                                    capture_output=True, text=True)
            advisory = subprocess.run([sys.executable, broken], env=env,
                                      capture_output=True, text=True)
            self.assertEqual(strict.returncode, 1,
                             "a checker that crashed must FAIL the CI gate, not pass it")
            self.assertEqual(advisory.returncode, 0,
                             "a local advisory run must still never block")
import importlib.util as _ilu
_rspec = _ilu.spec_from_file_location("bm_registry", os.path.join(HERE, "bm_registry.py"))
_reg = _ilu.module_from_spec(_rspec)


def load_registry_module():
    """Import bm_registry fresh so it picks up the current env vars."""
    _rspec.loader.exec_module(_reg)
    return _reg


class TestRegistryStorage(unittest.TestCase):
    def test_new_record_shape_and_redaction(self):
        reg = load_registry_module()
        r = reg.new_record("payments", "persistent",
                           "build payments, the prod password is hunter2",
                           ["api/pay.py"], tier="T2", owner="sess-1")
        self.assertEqual(r["schema"], reg.SCHEMA)
        self.assertEqual(r["lifetime"], "persistent")
        self.assertEqual(r["state"], "active")
        self.assertEqual(r["files"], ["api/pay.py"])
        self.assertNotIn("hunter2", r["objective"], "objective was not redacted")
        self.assertIn("[REDACTED]", r["objective"])
        for key in ("decisions", "digest", "spend", "lease", "check", "evidence"):
            self.assertIn(key, r, "record is missing field: %s" % key)

    def test_save_and_load_roundtrip(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            data = {"schema": reg.SCHEMA, "records": {"a": reg.new_record(
                "a", "persistent", "obj", ["x.py"])}}
            self.assertTrue(reg.save(data, cwd=d))
            back = reg.load(cwd=d)
            self.assertEqual(back["records"]["a"]["objective"], "obj")

    def test_load_missing_file_returns_empty_registry(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            back = reg.load(cwd=d)
            self.assertEqual(back["schema"], reg.SCHEMA)
            self.assertEqual(back["records"], {})

    def test_save_does_not_raise_on_a_value_it_cannot_serialize(self):
        # save() caught only OSError, so a caller passing a pathlib.Path (an
        # obvious way to name a file) got a TypeError out of the library.
        import pathlib
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            try:
                ok, conflict = reg.claim("a", "persistent", "o",
                                         [pathlib.Path("x.py")], cwd=d)
            except Exception as e:
                self.fail("claim() raised on an unserializable path type: %r" % (e,))
            self.assertIsNone(conflict)
            stderr_capture = io.StringIO()
            with contextlib.redirect_stderr(stderr_capture):
                saved = reg.save({"schema": reg.SCHEMA,
                                  "records": {"a": {"files": [pathlib.Path("x.py")]}}}, cwd=d)
            self.assertFalse(saved, "an unserializable registry must report a failed save")
            self.assertTrue(stderr_capture.getvalue().strip(),
                            "a failed save must warn on stderr, never fail silently")

    def test_load_does_not_raise_on_deeply_nested_json(self):
        """load() caught only ValueError, so a pathological file raised
        RecursionError out of a function documented to never raise.

        This asserts ONLY that load survives, because that is the part that is
        true everywhere. Whether the parse actually fails at a given nesting
        depth is PLATFORM DEPENDENT: 20000 levels overflowed the stack on macOS
        and parsed cleanly on the Linux CI runner, so an earlier version of this
        test also demanded a stderr warning and passed locally while failing in
        CI. The warning is now covered by its own deterministic test below."""
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            path = reg.registry_path(cwd=d)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            io.open(path, "w").write('{"a":' * 20000 + "1" + "}" * 20000)
            try:
                with contextlib.redirect_stderr(io.StringIO()):
                    back = reg.load(cwd=d)
            except Exception as e:
                self.fail("load() raised on deeply nested JSON: %r" % (e,))
            self.assertEqual(back["records"], {},
                             "a registry that is not a usable record set must load as empty")

    def test_load_warns_on_an_unparsable_registry(self):
        """A corrupt registry must degrade to empty AND say so. Silence would
        let a session run with no fences while believing it had them.

        Uses plainly invalid JSON rather than deep nesting, so the parse fails
        identically on every platform and stack size."""
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            path = reg.registry_path(cwd=d)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            io.open(path, "w").write("{ this is not json at all")
            stderr_capture = io.StringIO()
            try:
                with contextlib.redirect_stderr(stderr_capture):
                    back = reg.load(cwd=d)
            except Exception as e:
                self.fail("load() raised on an unparsable registry: %r" % (e,))
            self.assertEqual(back["records"], {}, "an unparsable registry must load as empty")
            self.assertTrue(stderr_capture.getvalue().strip(),
                            "an unparsable registry must warn on stderr, never fail silently")

    def test_unknown_fields_and_newer_schema_do_not_crash(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            path = reg.registry_path(cwd=d)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            io.open(path, "w").write(json.dumps(
                {"schema": 99, "records": {"a": {"id": "a", "mystery": 1}}}))
            back = reg.load(cwd=d)
            self.assertIn("a", back["records"], "forward compatibility broken")


class TestRegistryOverlap(unittest.TestCase):
    def test_overlap_table(self):
        reg = load_registry_module()
        cases = [
            (["api/pay.py"], ["api/pay.py"], True, "identical path"),
            (["api/pay.py"], ["api/ship.py"], False, "different files"),
            (["api/"], ["api/pay.py"], True, "directory contains file"),
            (["api/**"], ["api/hooks/x.py"], True, "recursive glob"),
            # fnmatch is not path aware: "*" crosses "/", so this glob matches
            # a direct child too, not only files nested deeper. Do not call
            # this a "single-level glob": it is not restricted to one level.
            (["api/*.py"], ["api/pay.py"], True, "glob matches a direct child"),
            (["api/*.py"], ["web/pay.py"], False, "glob in another directory"),
            (["docs/a.md"], ["docs/b.md"], False, "siblings"),
            (["./api/pay.py"], ["api/pay.py"], True, "normalized dot prefix"),
            (["api"], ["api/pay.py"], True, "directory without trailing slash"),
            (["api/pay.py"], ["api"], True, "directory without trailing slash, reversed"),
            (["API/pay.py"], ["api/pay.py"], True, "case differs only by letter case"),
            (["api/*.py"], ["api/**"], True, "glob on both sides"),
            # Finding C1: a path pasted in absolute form names the same file as
            # the project-relative form of it. Missing this grants two writers
            # the same file, which is the data-loss case this module exists to
            # prevent, so an unresolvable form conflicts rather than passes.
            (["/repo/api/pay.py"], ["api/pay.py"], True, "absolute vs relative"),
            (["api/pay.py"], ["/repo/api/pay.py"], True, "absolute vs relative, reversed"),
            (["~/repo/api/pay.py"], ["api/pay.py"], True, "home-relative vs relative"),
            (["../repo/api/pay.py"], ["api/pay.py"], True, "parent segment vs relative"),
            (["/repo/api/"], ["api/pay.py"], True, "absolute directory contains relative file"),
            (["/repo/api/pay.py"], ["api/ship.py"], False, "absolute vs unrelated relative"),
            (["/repo/api/pay.py"], ["/other/api/pay.py"], False,
             "two absolute paths are both fully determined"),
        ]
        for a, b, expected, label in cases:
            got = bool(reg.paths_overlap(a, b))
            self.assertEqual(got, expected, "%s: %s vs %s" % (label, a, b))

    def test_directory_without_trailing_slash_overlaps_file_beneath(self):
        # Finding 1: a directory declared without a trailing slash must not be
        # invisible to collision detection, in either argument order.
        reg = load_registry_module()
        self.assertTrue(reg.paths_overlap(["api"], ["api/pay.py"]))
        self.assertTrue(reg.paths_overlap(["api/pay.py"], ["api"]))

    def test_absolute_and_relative_forms_of_one_file_conflict(self):
        # Finding C1: two threads, one of which declares the absolute path a
        # user pasted from a file manager, were both granted the same file.
        reg = load_registry_module()
        self.assertTrue(reg.paths_overlap(["/repo/api/pay.py"], ["api/pay.py"]),
                        "absolute and relative forms of one file must conflict")
        self.assertTrue(reg.paths_overlap(["api/pay.py"], ["/repo/api/pay.py"]),
                        "the conflict must hold in both argument orders")

    def test_claim_refuses_an_absolute_form_of_an_already_claimed_file(self):
        # The end-to-end consequence: the fence must hold across path forms.
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            ok, _ = reg.claim("payments", "persistent", "pay", ["api/pay.py"], cwd=d)
            self.assertTrue(ok)
            ok2, conflict = reg.claim("billing", "persistent", "bill",
                                      ["/repo/api/pay.py"], cwd=d)
            self.assertFalse(ok2, "an absolute restatement of a claimed file must be refused")
            self.assertEqual(conflict["id"], "payments")

    def test_claim_skips_non_dict_record_instead_of_raising(self):
        # Finding 2: a corrupt or hand-edited registry record that is not a
        # dict (here a bare string) must not make claim() raise. It is skipped
        # defensively, the same way _redact_record_fields skips it.
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            path = reg.registry_path(cwd=d)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            io.open(path, "w").write(json.dumps(
                {"schema": reg.SCHEMA, "records": {"bad": "not-a-dict"}}))
            try:
                ok, conflict = reg.claim("new", "persistent", "o", ["y.py"], cwd=d)
            except Exception as e:
                self.fail("claim() raised on a non-dict record: %r" % (e,))
            self.assertTrue(ok, "a non-dict record must not block an unrelated claim")
            self.assertIsNone(conflict)

    def test_case_insensitive_overlap(self):
        # Finding 3: macOS (this project's own dev platform) has a
        # case-insensitive filesystem, so paths differing only by letter case
        # name the same file and must be reported as an overlap.
        reg = load_registry_module()
        self.assertTrue(reg.paths_overlap(["API/pay.py"], ["api/pay.py"]))

    def test_glob_on_both_sides(self):
        reg = load_registry_module()
        self.assertTrue(reg.paths_overlap(["api/*.py"], ["api/**"]))

    def test_paths_overlap_never_raises_on_bad_input(self):
        # paths_overlap is a safety function: empty lists, an empty-string
        # entry, a non-list argument, and non-string entries must never raise.
        reg = load_registry_module()
        try:
            self.assertEqual(reg.paths_overlap([], ["api/pay.py"]), [])
            self.assertEqual(reg.paths_overlap([""], ["api/pay.py"]), [])
            self.assertEqual(reg.paths_overlap(None, ["api/pay.py"]), [])
            self.assertTrue(reg.paths_overlap([123, "api/pay.py"], ["api/pay.py"]))
        except Exception as e:
            self.fail("paths_overlap() raised on defensive input: %r" % (e,))

    def test_claim_does_not_raise_on_a_files_argument_that_is_not_iterable(self):
        # Same family as the C2 sweep, on the argument side: paths_overlap
        # tolerates any files argument, then list(files) raised two lines later,
        # out of the function that is supposed to never block a work session.
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            try:
                ok, conflict = reg.claim("a", "persistent", "o", 5, cwd=d)
            except Exception as e:
                self.fail("claim() raised on a non-iterable files argument: %r" % (e,))
            self.assertTrue(ok)
            self.assertEqual(reg.load(cwd=d)["records"]["a"]["files"], [],
                             "an unusable files argument must record no fence, not a guess")

    def test_claim_treats_a_bare_string_files_argument_as_one_path(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            reg.claim("a", "persistent", "o", "api/pay.py", cwd=d)
            self.assertEqual(reg.load(cwd=d)["records"]["a"]["files"], ["api/pay.py"],
                             "a bare string must not be exploded character by character")
            ok, conflict = reg.claim("b", "persistent", "o", ["api/pay.py"], cwd=d)
            self.assertFalse(ok, "the fence from a bare-string claim must still hold")

    def test_claim_grants_then_refuses_conflict(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            ok, conflict = reg.claim("payments", "persistent", "pay",
                                     ["api/pay.py"], cwd=d)
            self.assertTrue(ok)
            self.assertIsNone(conflict)
            ok2, conflict2 = reg.claim("billing", "persistent", "bill",
                                       ["api/pay.py"], cwd=d)
            self.assertFalse(ok2, "a colliding claim must be refused")
            self.assertIsNotNone(conflict2)
            self.assertEqual(conflict2["id"], "payments",
                             "refusal must name the conflicting record")

    def test_claim_allows_disjoint_and_ignores_parked(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            reg.claim("a", "persistent", "a", ["api/a.py"], cwd=d)
            ok, _ = reg.claim("b", "persistent", "b", ["api/b.py"], cwd=d)
            self.assertTrue(ok, "disjoint claims must both be granted")
            data = reg.load(cwd=d)
            data["records"]["a"]["state"] = "parked"
            reg.save(data, cwd=d)
            ok2, _ = reg.claim("c", "persistent", "c", ["api/a.py"], cwd=d)
            self.assertTrue(ok2, "a parked record must not block a new claim")

    def test_reclaim_by_same_id_is_allowed(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            reg.claim("a", "persistent", "a", ["api/a.py"], cwd=d)
            ok, _ = reg.claim("a", "persistent", "a again", ["api/a.py"], cwd=d)
            self.assertTrue(ok, "a record must be able to reclaim its own files")


class TestRegistryClash(unittest.TestCase):
    def _two_records(self, reg, d):
        reg.claim("payments", "persistent", "pay", ["api/pay.py"], cwd=d)
        reg.claim("billing", "persistent", "bill", ["api/bill.py"], cwd=d)

    def test_same_topic_in_another_record_clashes(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            self._two_records(reg, d)
            ok, clash = reg.decide("payments", "payments-api", "use Stripe", cwd=d)
            self.assertTrue(ok)
            self.assertIsNone(clash)
            ok2, clash2 = reg.decide("billing", "payments-api", "use Adyen", cwd=d)
            self.assertIsNotNone(clash2, "a second record deciding the same topic must clash")
            self.assertEqual(clash2["record"], "payments")
            self.assertIn("Stripe", clash2["text"], "the clash must show the prior decision")

    def test_different_topics_stay_silent(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            self._two_records(reg, d)
            reg.decide("payments", "payments-api", "use Stripe", cwd=d)
            ok, clash = reg.decide("billing", "invoice-format", "use PDF", cwd=d)
            self.assertTrue(ok)
            self.assertIsNone(clash, "unrelated topics must not clash")

    def test_record_revising_its_own_topic_does_not_self_clash(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            self._two_records(reg, d)
            reg.decide("payments", "payments-api", "use Stripe", cwd=d)
            ok, clash = reg.decide("payments", "payments-api", "use Stripe Connect", cwd=d)
            self.assertTrue(ok)
            self.assertIsNone(clash, "a record must be free to revise its own decision")

    def test_topic_matching_ignores_case_and_spacing(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            self._two_records(reg, d)
            reg.decide("payments", "Payments API", "use Stripe", cwd=d)
            _, clash = reg.decide("billing", "payments-api", "use Adyen", cwd=d)
            self.assertIsNotNone(clash, "topic matching must normalize case and separators")

    def test_decision_and_digest_are_redacted(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            reg.claim("payments", "persistent", "pay", ["api/pay.py"], cwd=d)
            reg.decide("payments", "creds", "the prod password is hunter2", cwd=d)
            reg.set_digest("payments", "digest with token sk-ant-api03-ABCDEFGHIJKLMNOP", cwd=d)
            blob = io.open(reg.registry_path(cwd=d)).read()
            self.assertNotIn("hunter2", blob, "decision leaked a secret into the registry")
            self.assertNotIn("sk-ant-api03-ABCDEFGHIJKLMNOP", blob, "digest leaked a secret")

    def test_non_dict_other_record_does_not_raise_on_decide(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            reg.claim("payments", "persistent", "pay", ["api/pay.py"], cwd=d)
            data = reg.load(cwd=d)
            data["records"]["corrupt"] = "not a dict"
            reg.save(data, cwd=d)
            ok, clash = reg.decide("payments", "payments-api", "use Stripe", cwd=d)
            self.assertTrue(ok, "a corrupt sibling record must not block recording a decision")
            self.assertIsNone(clash)

    def test_non_list_decisions_field_does_not_raise_on_decide(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            self._two_records(reg, d)
            data = reg.load(cwd=d)
            data["records"]["billing"]["decisions"] = "not a list"
            reg.save(data, cwd=d)
            ok, clash = reg.decide("payments", "payments-api", "use Stripe", cwd=d)
            self.assertTrue(ok, "a non-list decisions field must not raise")
            self.assertIsNone(clash)

    def test_non_dict_decision_entry_does_not_raise_on_decide(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            self._two_records(reg, d)
            data = reg.load(cwd=d)
            data["records"]["billing"]["decisions"] = ["not a dict"]
            reg.save(data, cwd=d)
            ok, clash = reg.decide("payments", "payments-api", "use Stripe", cwd=d)
            self.assertTrue(ok, "a non-dict decision entry must not raise")
            self.assertIsNone(clash)

    def test_non_list_decisions_field_on_the_TARGET_record_does_not_raise(self):
        # The sibling test above malforms the OTHER record, which only the clash
        # scan reads. Malforming the target's own field hit setdefault().append
        # instead, so the decision was lost with an AttributeError.
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            self._two_records(reg, d)
            data = reg.load(cwd=d)
            data["records"]["payments"]["decisions"] = "not a list"
            reg.save(data, cwd=d)
            try:
                ok, clash = reg.decide("payments", "payments-api", "use Stripe", cwd=d)
            except Exception as e:
                self.fail("decide() raised on a malformed decisions field of its own "
                          "target record: %r" % (e,))
            self.assertTrue(ok)
            decisions = reg.load(cwd=d)["records"]["payments"]["decisions"]
            self.assertEqual([x["text"] for x in decisions], ["use Stripe"],
                             "the decision must still be recorded, on a repaired list")

    def test_set_digest_on_non_dict_target_record_does_not_raise(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            data = reg.load(cwd=d)
            data["records"]["corrupt"] = "not a dict"
            reg.save(data, cwd=d)
            ok = reg.set_digest("corrupt", "some digest text", cwd=d)
            self.assertFalse(ok, "a non-dict target record must be reported as not found, not raise")

    def test_decide_on_non_dict_target_record_does_not_raise(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            data = reg.load(cwd=d)
            data["records"]["corrupt"] = "not a dict"
            reg.save(data, cwd=d)
            ok, clash = reg.decide("corrupt", "payments-api", "use Stripe", cwd=d)
            self.assertFalse(ok, "a non-dict target record must be reported as not found, not raise")
            self.assertIsNone(clash)

    def test_decide_survives_a_stored_topic_that_is_not_a_string(self):
        # Same defect shape as C2, found by sweeping for it: _topic_key called
        # .strip() on whatever the registry happened to hold, so one decision
        # stored with a numeric topic made every later decide() raise.
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            self._two_records(reg, d)
            data = reg.load(cwd=d)
            data["records"]["billing"]["decisions"] = [{"topic": 5, "text": "x"}]
            reg.save(data, cwd=d)
            try:
                ok, clash = reg.decide("payments", "payments-api", "use Stripe", cwd=d)
            except Exception as e:
                self.fail("decide() raised on a non-string stored topic: %r" % (e,))
            self.assertTrue(ok, "the decision must still be recorded")
            self.assertIsNone(clash, "an unreadable stored topic must not be reported as a clash")

    def test_empty_topic_decision_is_recorded_but_never_clashes(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            self._two_records(reg, d)
            # A decision with no topic at all normalizes to the empty key.
            reg.decide("billing", "", "housekeeping note", cwd=d)
            # A second, unrelated topic-less decision must not clash with it.
            ok, clash = reg.decide("payments", "!!!", "another housekeeping note", cwd=d)
            self.assertTrue(ok)
            self.assertIsNone(clash, "empty-topic decisions must never clash with each other")
            data = reg.load(cwd=d)
            self.assertEqual(len(data["records"]["billing"]["decisions"]), 1,
                              "the empty-topic decision must still be recorded")
            self.assertEqual(len(data["records"]["payments"]["decisions"]), 1,
                              "the punctuation-only topic decision must still be recorded")


class TestRegistryAbsorbAndView(unittest.TestCase):
    def test_absorb_is_lossless_and_parks(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            io.open(os.path.join(d, "STATE.md"), "w").write("# Project STATE\n")
            reg.claim("payments", "persistent", "pay", ["api/pay.py"], cwd=d)
            reg.decide("payments", "payments-api", "chose Stripe", cwd=d)
            reg.set_digest("payments", "next: wire the webhook handler", cwd=d)
            absorbed = reg.absorb(cwd=d)
            self.assertEqual([a[0] for a in absorbed], ["payments"])
            state = io.open(os.path.join(d, "STATE.md")).read()
            self.assertIn("wire the webhook handler", state, "digest was not absorbed")
            self.assertIn("chose Stripe", state, "decisions were not absorbed")
            data = reg.load(cwd=d)
            self.assertEqual(data["records"]["payments"]["state"], "parked")

    def test_absorb_creates_state_file_when_missing(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            reg.claim("a", "persistent", "a", ["x.py"], cwd=d)
            reg.set_digest("a", "important next step", cwd=d)
            reg.absorb(cwd=d)
            self.assertTrue(os.path.exists(os.path.join(d, "STATE.md")),
                            "absorb must not drop context when STATE.md is absent")
            self.assertIn("important next step",
                          io.open(os.path.join(d, "STATE.md")).read())

    def test_render_writes_human_view(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            reg.claim("payments", "persistent", "build payments",
                      ["api/pay.py"], tier="T2", cwd=d)
            md = reg.render(cwd=d)
            view = os.path.join(d, "threads", "REGISTRY.md")
            self.assertTrue(os.path.exists(view), "REGISTRY.md was not written")
            body = io.open(view).read()
            self.assertIn("payments", body)
            self.assertIn("api/pay.py", body)
            self.assertIn("generated", body.lower(),
                          "the view must say it is generated, never hand-edited")
            self.assertEqual(md, body)

    def test_security_md_line_count_claim_is_still_true(self):
        """SECURITY.md tells the reader how much code they have to audit, and
        publishes the command that produces the figure. That number rotted twice
        in one day, which makes the document contradict its own command: worse
        than saying nothing in a file whose whole point is verifiability. So the
        claim is gated rather than trusted. Tolerance is wide on purpose; this
        catches drift, it does not police every commit."""
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sec = os.path.join(root, "SECURITY.md")
        if not os.path.exists(sec):
            self.skipTest("SECURITY.md not present")
        text = io.open(sec, encoding="utf-8").read()
        m = re.search(r"tools are about ([\d,]+) lines", text)
        self.assertIsNotNone(m, "SECURITY.md no longer states a line count to check")
        claimed = int(m.group(1).replace(",", ""))
        actual = 0
        for dirpath, _dirs, names in os.walk(os.path.join(root, "tools")):
            for n in names:
                if n.endswith(".py") or n.endswith(".sh"):
                    with io.open(os.path.join(dirpath, n), encoding="utf-8", errors="replace") as f:
                        actual += sum(1 for _ in f)
        drift = abs(actual - claimed) / float(max(actual, 1))
        self.assertLess(drift, 0.15,
                        "SECURITY.md claims about %d lines but the tools are %d. "
                        "Update the figure in SECURITY.md." % (claimed, actual))

    def test_missing_fcntl_degrades_loudly_and_still_works(self):
        """fcntl is POSIX only, so on Windows there is no lock. Continuing is
        right (never block a session) but doing it silently was not: the caller
        believes concurrent claims are serialized when they are not, and a lost
        record is invisible by definition. Simulated by shadowing fcntl with a
        module that refuses to import, which is what Windows looks like here."""
        with tempfile.TemporaryDirectory() as d:
            shadow = os.path.join(d, "shadow")
            os.makedirs(shadow)
            io.open(os.path.join(shadow, "fcntl.py"), "w").write(
                "raise ImportError('no fcntl on this platform (simulated)')\n")
            work = os.path.join(d, "work")
            os.makedirs(work)
            env = dict(os.environ, PYTHONPATH=shadow)
            script = (
                "import sys, os\n"
                "sys.path.insert(0, %r)\n"
                "import bm_registry as r\n"
                "ok, _ = r.claim('pay', 'persistent', 'x', ['api/pay.py'], cwd=os.getcwd())\n"
                "print('CLAIM_OK' if ok else 'CLAIM_FAILED')\n" % HERE)
            r = subprocess.run([sys.executable, "-c", script], env=env, cwd=work,
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, "a missing lock must never crash the session")
            self.assertIn("CLAIM_OK", r.stdout, "work must still proceed without a lock")
            self.assertIn("locking is unavailable", r.stderr,
                          "degraded coordination must be reported, never silent")

    def test_every_degraded_lock_path_warns_and_still_runs(self):
        """There are three ways to fail to acquire the lock, and ALL of them used
        to be silent in at least one caller. A silent degrade is worse than no
        lock at all, because it is indistinguishable from working correctly
        until work has already been lost. Each path must run the work anyway
        (never-block) and each must say so."""
        reg = load_registry_module()
        cases = []

        # 1. lock file cannot be opened: the lock PATH is a directory.
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "lockdir", ".registry.lock"))
            cap = io.StringIO()
            with contextlib.redirect_stderr(cap):
                out = reg.locked_call(os.path.join(d, "lockdir", ".registry.lock"),
                                      lambda: "ran")
            cases.append(("unopenable lock file", out, cap.getvalue()))

        # 2. lock directory cannot be created: a FILE sits where the dir must go.
        with tempfile.TemporaryDirectory() as d:
            io.open(os.path.join(d, "blocked"), "w").write("i am a file\n")
            reg._WARNED_UNLOCKED[:] = []
            cap = io.StringIO()
            with contextlib.redirect_stderr(cap):
                out = reg.locked_call(os.path.join(d, "blocked", "x.lock"),
                                      lambda: "ran")
            cases.append(("uncreatable lock dir", out, cap.getvalue()))

        for label, out, err in cases:
            self.assertEqual(out, "ran", "%s must still run the work" % label)
            self.assertIn("WITHOUT a file lock", err,
                          "%s must warn, never degrade silently" % label)

    def test_concurrent_starts_and_offs_do_not_deadlock(self):
        """`off` takes the REGISTRY lock (via absorb) and then the MODE lock, and
        `start` takes them in that same order. Holding the mode lock across
        absorb would invert it, and two concurrent commands could then wait on
        each other forever. A deadlock is worse than the lost update the lock
        exists to prevent, because the session hangs with no error at all."""
        import threading
        threads_dir = os.path.join(HERE, "bm_threads.py")
        with tempfile.TemporaryDirectory() as d:
            subprocess.run([sys.executable, threads_dir, "on"], cwd=d,
                           capture_output=True, timeout=30)
            outcomes = []

            def run(args, tag):
                try:
                    r = subprocess.run([sys.executable, threads_dir] + args, cwd=d,
                                       capture_output=True, text=True, timeout=30)
                    outcomes.append((tag, r.returncode))
                except subprocess.TimeoutExpired:
                    outcomes.append((tag, "DEADLOCK"))

            workers = []
            for i in range(4):
                workers.append(threading.Thread(target=run, args=(
                    ["start", "t%d" % i, "obj", "--files", "f%d.py" % i], "start%d" % i)))
            for i in range(2):
                workers.append(threading.Thread(target=run, args=(["off"], "off%d" % i)))
            for w in workers:
                w.start()
            for w in workers:
                w.join()

            stuck = [t for t, rc in outcomes if rc == "DEADLOCK"]
            self.assertEqual(stuck, [], "commands deadlocked on the two locks: %s" % stuck)
            nonzero = [(t, rc) for t, rc in outcomes if rc != 0]
            self.assertEqual(nonzero, [], "every path must exit 0: %s" % nonzero)
            # The mode file must still be readable JSON, not a half-written mess.
            mode = os.path.join(d, "threads", "thread-mode.json")
            if os.path.exists(mode):
                json.load(io.open(mode, encoding="utf-8"))

    def test_off_and_start_leave_a_transactionally_consistent_state(self):
        """The two files must agree after a concurrent start and off.

        The earlier version of `off` drained the registry OUTSIDE the mode lock,
        so a `start` granted in the gap created an ACTIVE record while the mode
        file recorded the thread as parked, and that record's digest was never
        absorbed: silent context loss, which is the one thing thread mode exists
        to prevent. Measured at 28 of 30 trials before the fix, 0 of 40 after.

        Repeated, because a race that reproduces sometimes proves nothing when
        it happens to pass once. Asserts STATE, not just liveness and valid JSON:
        an OFF system must hold no active persistent record."""
        import threading
        tool = os.path.join(HERE, "bm_threads.py")
        trials = 12
        inconsistent, hangs = [], []
        with tempfile.TemporaryDirectory() as base:
            for trial in range(trials):
                d = os.path.join(base, "t%d" % trial)
                os.makedirs(d)
                subprocess.run([sys.executable, tool, "on"], cwd=d,
                               capture_output=True, timeout=30)
                subprocess.run([sys.executable, tool, "start", "seed", "seed obj",
                                "--files", "seed.py"], cwd=d,
                               capture_output=True, timeout=30)

                def run(args, tag):
                    try:
                        subprocess.run([sys.executable, tool] + args, cwd=d,
                                       capture_output=True, timeout=30)
                    except subprocess.TimeoutExpired:
                        hangs.append(tag)

                workers = [
                    threading.Thread(target=run, args=(
                        ["start", "late", "late obj", "--files", "late.py"], "start")),
                    threading.Thread(target=run, args=(["off"], "off")),
                ]
                for w in workers:
                    w.start()
                for w in workers:
                    w.join()

                mode_p = os.path.join(d, "threads", "thread-mode.json")
                reg_p = os.path.join(d, "threads", "registry.json")
                if not (os.path.exists(mode_p) and os.path.exists(reg_p)):
                    continue
                mode = json.load(io.open(mode_p, encoding="utf-8"))
                reg = json.load(io.open(reg_p, encoding="utf-8"))
                records = reg.get("records") or {}
                if mode.get("mode") == "off":
                    still_active = [rid for rid, rec in records.items()
                                    if isinstance(rec, dict)
                                    and rec.get("state") == "active"
                                    and rec.get("lifetime") == "persistent"]
                    if still_active:
                        inconsistent.append((trial, still_active))
                # Every thread the mode file knows must exist in the registry:
                # a thread with no record can never be drained.
                for tname, meta in (mode.get("threads") or {}).items():
                    if isinstance(meta, dict) and tname not in records:
                        inconsistent.append((trial, "thread %s has no record" % tname))

            self.assertEqual(hangs, [], "commands deadlocked: %s" % hangs)
            self.assertEqual(inconsistent, [],
                             "mode file and registry disagreed after a concurrent "
                             "start/off, which means a digest was never absorbed: %s"
                             % inconsistent)

    def test_thread_mode_lock_uses_the_one_registry_primitive(self):
        """bm_threads used to carry its OWN mode-file lock that swallowed every
        failure, so on a platform without fcntl the registry warned while
        thread-mode updates raced on quietly: two half-truths instead of one
        behaviour. It must now delegate to the single primitive."""
        src = io.open(os.path.join(HERE, "bm_threads.py"), encoding="utf-8").read()
        self.assertIn("locked_call", src,
                      "the mode lock must delegate to bm_registry.locked_call")
        self.assertNotIn("fcntl.flock", src,
                         "bm_threads must not hold a second, separate lock implementation")

    def test_view_warns_when_a_record_guards_less_than_it_declared(self):
        """An unreadable files entry is DROPPED, never guessed at, so the record
        guards fewer paths than its owner thinks and a second writer can be
        granted one of them. Dropping is the right call (the alternative freezes
        every future claim behind one corrupt record) but it must not be silent.
        This test fails the moment the generated view stops saying so."""
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            reg.claim("pay", "persistent", "pay", ["api/pay.py"], cwd=d)
            data = reg.load(cwd=d)
            data["records"]["pay"]["files"] = ["api/pay.py", None, 42]
            reg.save(data, cwd=d)
            body = reg.render(cwd=d)
            self.assertIn("api/pay.py", body, "the readable path must still render")
            self.assertIn("WARNING", body,
                          "a record guarding less than it declared must say so")
            self.assertIn("2", body, "the count of unguarded entries must be shown")

    def test_unguarded_count_counts_only_unreadable_entries(self):
        reg = load_registry_module()
        self.assertEqual(reg.unguarded_count(["a.py", "b.py"]), 0)
        self.assertEqual(reg.unguarded_count(["a.py", None, 42]), 2)
        self.assertEqual(reg.unguarded_count("a.py"), 0, "a bare string is one path")
        self.assertEqual(reg.unguarded_count(None), 0, "a missing field is not a corrupt one")

    def test_absorb_on_non_dict_record_does_not_raise(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            io.open(os.path.join(d, "STATE.md"), "w").write("# Project STATE\n")
            reg.claim("good", "persistent", "good", ["x.py"], cwd=d)
            reg.set_digest("good", "good digest", cwd=d)
            data = reg.load(cwd=d)
            data["records"]["bad"] = "not-a-dict"
            reg.save(data, cwd=d)
            try:
                absorbed = reg.absorb(cwd=d)
            except Exception as e:
                self.fail("absorb() raised on a non-dict record: %r" % (e,))
            self.assertEqual([a[0] for a in absorbed], ["good"], "non-dict record must be skipped")
            state = io.open(os.path.join(d, "STATE.md")).read()
            self.assertIn("good digest", state, "good record digest was not absorbed")

    def test_absorb_on_decisions_not_list_does_not_raise(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            io.open(os.path.join(d, "STATE.md"), "w").write("# Project STATE\n")
            reg.claim("a", "persistent", "a", ["x.py"], cwd=d)
            reg.set_digest("a", "digest a", cwd=d)
            data = reg.load(cwd=d)
            data["records"]["a"]["decisions"] = "not-a-list"
            reg.save(data, cwd=d)
            try:
                absorbed = reg.absorb(cwd=d)
            except Exception as e:
                self.fail("absorb() raised on decisions not being a list: %r" % (e,))
            state = io.open(os.path.join(d, "STATE.md")).read()
            self.assertIn("digest a", state, "digest was not absorbed when decisions field was malformed")

    def test_absorb_on_completely_empty_registry_does_not_raise(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            io.open(os.path.join(d, "STATE.md"), "w").write("# Project STATE\n")
            try:
                absorbed = reg.absorb(cwd=d)
            except Exception as e:
                self.fail("absorb() raised on an empty registry: %r" % (e,))
            self.assertEqual(absorbed, [], "empty registry must return empty absorption list")

    def test_render_on_non_dict_record_does_not_raise(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            reg.claim("good", "persistent", "good", ["x.py"], cwd=d)
            data = reg.load(cwd=d)
            data["records"]["bad"] = "not-a-dict"
            reg.save(data, cwd=d)
            try:
                md = reg.render(cwd=d)
            except Exception as e:
                self.fail("render() raised on a non-dict record: %r" % (e,))
            self.assertIn("good", md, "good record was not rendered")

    def test_render_on_decisions_not_list_does_not_raise(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            reg.claim("a", "persistent", "a", ["x.py"], cwd=d)
            reg.decide("a", "topic", "decision", cwd=d)
            data = reg.load(cwd=d)
            data["records"]["a"]["decisions"] = "not-a-list"
            reg.save(data, cwd=d)
            try:
                md = reg.render(cwd=d)
            except Exception as e:
                self.fail("render() raised on decisions not being a list: %r" % (e,))
            self.assertIn("a", md, "record was not rendered when decisions field was malformed")

    def test_absorb_leaves_records_active_when_state_write_fails(self):
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("running as root: file permissions cannot be made to block a write")
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            state_path = os.path.join(d, "STATE.md")
            io.open(state_path, "w").write("# Project STATE\n")
            reg.claim("payments", "persistent", "pay", ["api/pay.py"], cwd=d)
            reg.set_digest("payments", "next: wire the webhook handler", cwd=d)
            before = io.open(state_path).read()
            os.chmod(state_path, stat.S_IREAD)
            try:
                try:
                    absorbed = reg.absorb(cwd=d)
                except Exception as e:
                    self.fail("absorb() raised when STATE.md could not be written: %r" % (e,))
                after = io.open(state_path).read()
                if after != before:
                    self.skipTest("could not make STATE.md unwritable in this environment")
                self.assertEqual(absorbed, [],
                                 "a failed handover write must never be reported as absorbed")
                data = reg.load(cwd=d)
                self.assertEqual(data["records"]["payments"]["state"], "active",
                                 "record must stay active when the handover write failed, "
                                 "or the work is lost silently")
            finally:
                os.chmod(state_path, stat.S_IREAD | stat.S_IWRITE)

    def test_absorb_returns_empty_and_warns_when_registry_save_fails(self):
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("running as root: file permissions cannot be made to block a write")
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            state_path = os.path.join(d, "STATE.md")
            io.open(state_path, "w").write("# Project STATE\n")
            reg.claim("payments", "persistent", "pay", ["api/pay.py"], cwd=d)
            reg.set_digest("payments", "next: wire the webhook handler", cwd=d)
            reg_path = reg.registry_path(cwd=d)
            before_registry = io.open(reg_path).read()
            os.chmod(reg_path, stat.S_IREAD)
            try:
                stderr_capture = io.StringIO()
                try:
                    with contextlib.redirect_stderr(stderr_capture):
                        absorbed = reg.absorb(cwd=d)
                except Exception as e:
                    self.fail("absorb() raised when the registry could not be saved: %r" % (e,))
                after_registry = io.open(reg_path).read()
                if after_registry != before_registry:
                    self.skipTest("could not make registry.json unwritable in this environment")
                self.assertEqual(absorbed, [],
                                 "a failed registry save must never be reported as absorbed, "
                                 "the state change did not persist")
                self.assertTrue(stderr_capture.getvalue().strip(),
                                 "a failed registry save must print a warning to stderr")
                state = io.open(state_path).read()
                self.assertIn("wire the webhook handler", state,
                              "the handover was already written to STATE.md before the save "
                              "attempt and that write cannot be undone")
                # The registry file is still readable with S_IREAD, so load() works
                # fine while it remains write-blocked.
                data = reg.load(cwd=d)
                self.assertEqual(data["records"]["payments"]["state"], "active",
                                 "record must stay active on disk when the registry save "
                                 "failed, or a repeated absorb would duplicate the handover")
            finally:
                os.chmod(reg_path, stat.S_IREAD | stat.S_IWRITE)

    def _seed(self, reg, d, rec):
        path = reg.registry_path(cwd=d)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        io.open(path, "w").write(json.dumps({"schema": reg.SCHEMA, "records": {"a": rec}}))

    def test_absorb_survives_a_non_string_entry_in_the_files_list(self):
        # Finding C2: ", ".join(files) raised TypeError on a null entry, so
        # absorb() died BEFORE writing STATE.md and the handover digest was
        # gone. Every later `off` failed the same way. The list itself was a
        # list, so the isinstance(files, list) guard never fired.
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            self._seed(reg, d, {"id": "a", "state": "active", "lifetime": "persistent",
                                "files": [None], "digest": "next: wire the webhook",
                                "decisions": []})
            try:
                absorbed = reg.absorb(cwd=d)
            except Exception as e:
                self.fail("absorb() raised on a non-string files entry: %r" % (e,))
            self.assertEqual([x[0] for x in absorbed], ["a"],
                             "the record must still be drained and parked")
            state_path = os.path.join(d, "STATE.md")
            self.assertTrue(os.path.exists(state_path),
                            "absorb never created STATE.md, so the digest was lost")
            self.assertIn("wire the webhook", io.open(state_path).read(),
                          "the digest must reach STATE.md despite the malformed files list")

    def test_render_survives_a_non_string_entry_in_the_files_list(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            self._seed(reg, d, {"id": "a", "state": "active", "files": [None, "api/pay.py"],
                                "digest": "next: wire the webhook"})
            try:
                md = reg.render(cwd=d)
            except Exception as e:
                self.fail("render() raised on a non-string files entry: %r" % (e,))
            self.assertIn("api/pay.py", md, "the readable entries must still be rendered")

    def test_render_survives_a_digest_that_is_not_a_string(self):
        # Same defect shape one line further down: r["digest"][:200] on an int.
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            self._seed(reg, d, {"id": "a", "state": "active", "files": [], "digest": 123})
            try:
                md = reg.render(cwd=d)
            except Exception as e:
                self.fail("render() raised on a non-string digest: %r" % (e,))
            self.assertIn("123", md, "the digest value must still be shown")

    def test_absorb_survives_a_files_field_that_is_not_iterable(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            self._seed(reg, d, {"id": "a", "state": "active", "files": 7,
                                "digest": "next: wire the webhook"})
            try:
                reg.absorb(cwd=d)
            except Exception as e:
                self.fail("absorb() raised on a non-iterable files field: %r" % (e,))
            self.assertIn("wire the webhook", io.open(os.path.join(d, "STATE.md")).read())

    def test_files_field_as_string_is_not_exploded_character_by_character(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            io.open(os.path.join(d, "STATE.md"), "w").write("# Project STATE\n")
            reg.claim("a", "persistent", "a", ["x.py"], cwd=d)
            reg.set_digest("a", "digest a", cwd=d)
            data = reg.load(cwd=d)
            data["records"]["a"]["files"] = "api/pay.py"
            reg.save(data, cwd=d)

            try:
                absorbed = reg.absorb(cwd=d)
            except Exception as e:
                self.fail("absorb() raised when files field was a bare string: %r" % (e,))
            self.assertEqual([a[0] for a in absorbed], ["a"])
            state = io.open(os.path.join(d, "STATE.md")).read()
            self.assertNotIn("a, p, i", state, "files string was exploded character by character in absorb")
            self.assertIn("(none)", state, "a non-list files field should render as empty, not exploded")

            try:
                md = reg.render(cwd=d)
            except Exception as e:
                self.fail("render() raised when files field was a bare string: %r" % (e,))
            self.assertNotIn("a, p, i", md, "files string was exploded character by character in render")
            self.assertIn("(none)", md, "a non-list files field should render as empty, not exploded")


class TestRegistryConcurrency(unittest.TestCase):
    def test_parallel_disjoint_claims_all_register(self):
        reg = load_registry_module()
        import threading as _th
        with tempfile.TemporaryDirectory() as d:
            def claim(n):
                reg.claim(n, "persistent", "obj " + n, ["api/%s.py" % n], cwd=d)
            ts = [_th.Thread(target=claim, args=(n,)) for n in ("a", "b", "c", "dee", "e")]
            [t.start() for t in ts]
            [t.join() for t in ts]
            data = reg.load(cwd=d)
            self.assertEqual(sorted(data["records"]), ["a", "b", "c", "dee", "e"],
                             "a concurrent claim was lost from the registry")

    def test_parallel_conflicting_claims_only_one_wins(self):
        reg = load_registry_module()
        import threading as _th
        with tempfile.TemporaryDirectory() as d:
            results = []
            def claim(n):
                ok, _ = reg.claim(n, "persistent", "obj", ["api/shared.py"], cwd=d)
                results.append(ok)
            ts = [_th.Thread(target=claim, args=(n,)) for n in ("a", "b", "c")]
            [t.start() for t in ts]
            [t.join() for t in ts]
            self.assertEqual(sum(1 for r in results if r), 1,
                             "exactly one claim on the same file may be granted")


class TestThreadsUseRegistry(unittest.TestCase):
    def _run(self, cwd, *a):
        return subprocess.run([sys.executable, os.path.join(HERE, "bm_threads.py"), *a],
                              cwd=cwd, capture_output=True, text=True)

    def test_start_registers_a_record_with_files(self):
        with tempfile.TemporaryDirectory() as d:
            io.open(os.path.join(d, "STATE.md"), "w").write("# S\n")
            self._run(d, "on")
            self._run(d, "start", "payments", "build payments", "--files", "api/pay.py")
            reg = json.load(io.open(os.path.join(d, "threads", "registry.json")))
            self.assertIn("payments", reg["records"], "start did not create a work record")
            self.assertEqual(reg["records"]["payments"]["files"], ["api/pay.py"])

    def test_start_refuses_an_overlapping_thread(self):
        with tempfile.TemporaryDirectory() as d:
            io.open(os.path.join(d, "STATE.md"), "w").write("# S\n")
            self._run(d, "on")
            self._run(d, "start", "payments", "pay", "--files", "api/pay.py")
            r = self._run(d, "start", "billing", "bill", "--files", "api/pay.py")
            self.assertIn("OVERLAP", r.stdout.upper(),
                          "an overlapping thread must be refused and say so")
            self.assertIn("payments", r.stdout, "the refusal must name the conflicting record")

    def test_checkpoint_topic_clash_is_reported(self):
        with tempfile.TemporaryDirectory() as d:
            io.open(os.path.join(d, "STATE.md"), "w").write("# S\n")
            self._run(d, "on")
            self._run(d, "start", "payments", "pay", "--files", "api/pay.py")
            self._run(d, "start", "billing", "bill", "--files", "api/bill.py")
            self._run(d, "checkpoint", "payments", "--topic", "payments-api",
                      "--decision", "use Stripe")
            r = self._run(d, "checkpoint", "billing", "--topic", "payments-api",
                          "--decision", "use Adyen")
            self.assertIn("CLASH", r.stdout.upper(), "a cross-thread clash must be reported")
            self.assertIn("payments", r.stdout)

    def test_off_absorbs_through_the_registry(self):
        with tempfile.TemporaryDirectory() as d:
            io.open(os.path.join(d, "STATE.md"), "w").write("# S\n")
            self._run(d, "on")
            self._run(d, "start", "payments", "pay", "--files", "api/pay.py")
            self._run(d, "checkpoint", "payments", "--topic", "api",
                      "--decision", "chose Stripe", "--next", "wire webhook")
            self._run(d, "off")
            state = io.open(os.path.join(d, "STATE.md")).read()
            self.assertIn("chose Stripe", state)
            self.assertIn("wire webhook", state)
            reg = json.load(io.open(os.path.join(d, "threads", "registry.json")))
            self.assertEqual(reg["records"]["payments"]["state"], "parked")


class TestSpendAttribution(unittest.TestCase):
    def test_attribute_accumulates_spend_on_the_record(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            reg.claim("payments", "persistent", "pay", ["api/pay.py"], cwd=d)
            for tokens in ("1500", "2500"):
                subprocess.run([sys.executable, os.path.join(HERE, "bm_telemetry.py"),
                                "attribute", "payments", tokens],
                               cwd=d, capture_output=True, text=True)
            data = reg.load(cwd=d)
            spend = data["records"]["payments"]["spend"]
            self.assertEqual(spend["output_tokens"], 4000)
            self.assertEqual(spend["sessions"], 2)

    def test_attribute_on_unknown_record_is_silent_and_exits_zero(self):
        # Strengthened: exit 0 alone also passes against an implementation that
        # invents the record, or that crashes and gets swallowed. Assert the
        # actual behaviour: nothing is created, and nothing is thrown.
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            reg.claim("payments", "persistent", "pay", ["api/pay.py"], cwd=d)
            before = io.open(reg.registry_path(cwd=d)).read()
            r = subprocess.run([sys.executable, os.path.join(HERE, "bm_telemetry.py"),
                                "attribute", "ghost", "100"],
                               cwd=d, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, "telemetry must never block work")
            self.assertNotIn("Traceback", r.stderr, "attribute raised on an unknown record")
            data = reg.load(cwd=d)
            self.assertNotIn("ghost", data["records"],
                             "attributing to an unknown record must not invent one")
            self.assertEqual(io.open(reg.registry_path(cwd=d)).read(), before,
                             "an unknown record must leave the registry byte for byte unchanged")

    def test_attribute_with_non_integer_tokens_does_not_raise_and_exits_zero(self):
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run([sys.executable, os.path.join(HERE, "bm_telemetry.py"),
                                "attribute", "test", "not_an_int"],
                               cwd=d, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, "telemetry must never raise on bad input")

    def test_attribute_with_spend_field_not_dict_does_not_crash(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            reg.claim("payments", "persistent", "pay", ["api/pay.py"], cwd=d)
            data = reg.load(cwd=d)
            data["records"]["payments"]["spend"] = "not_a_dict"
            reg.save(data, cwd=d)
            r = subprocess.run([sys.executable, os.path.join(HERE, "bm_telemetry.py"),
                                "attribute", "payments", "100"],
                               cwd=d, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, "telemetry must not crash on malformed spend")

    def test_attribute_on_non_dict_record_does_not_raise_and_exits_zero(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            reg.claim("good", "persistent", "good", ["x.py"], cwd=d)
            data = reg.load(cwd=d)
            data["records"]["bad"] = "not_a_dict"
            reg.save(data, cwd=d)
            r = subprocess.run([sys.executable, os.path.join(HERE, "bm_telemetry.py"),
                                "attribute", "bad", "100"],
                               cwd=d, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, "attribute on non-dict record must exit 0")

    def test_attribute_rejects_negative_token_count(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            reg.claim("payments", "persistent", "pay", ["api/pay.py"], cwd=d)
            data_before = reg.load(cwd=d)
            spend_before = data_before["records"]["payments"]["spend"]
            r = subprocess.run([sys.executable, os.path.join(HERE, "bm_telemetry.py"),
                                "attribute", "payments", "-50000"],
                               cwd=d, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, "attribute must exit 0")
            self.assertIn("negative", r.stdout.lower(), "error must mention negative")
            data_after = reg.load(cwd=d)
            spend_after = data_after["records"]["payments"]["spend"]
            self.assertEqual(spend_after["output_tokens"], spend_before["output_tokens"],
                            "spend must not change when token count is rejected")

    def test_attribute_accepts_zero_token_count(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            reg.claim("payments", "persistent", "pay", ["api/pay.py"], cwd=d)
            r = subprocess.run([sys.executable, os.path.join(HERE, "bm_telemetry.py"),
                                "attribute", "payments", "0"],
                               cwd=d, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, "attribute must exit 0")
            data = reg.load(cwd=d)
            spend = data["records"]["payments"]["spend"]
            self.assertEqual(spend["sessions"], 1, "session count must increment for zero token count")


class TestLifetimeTripwire(unittest.TestCase):
    """cmd_off drains EVERY active record, whatever its lifetime.

    That is correct TODAY only because threads are the only producer of
    records, so every record is lifetime "persistent" and draining it into
    STATE.md is exactly right. It stops being correct the moment an ephemeral
    single-writer fence becomes a record: `off` would then drain and park a
    fence belonging to a dispatch that is still running, releasing a file to a
    second writer. The ledger recorded that as prose, and prose is not a
    tripwire. These two tests are.

    REVIEW 2026-08-08 (ephemeral fence migration): when that migration lands,
    these tests fail on purpose. Do not delete them and do not relax them.
    Teach cmd_off to select by lifetime first, then rewrite them to assert the
    selection.
    """

    def _run(self, cwd, *a):
        return subprocess.run([sys.executable, os.path.join(HERE, "bm_threads.py"), *a],
                              cwd=cwd, capture_output=True, text=True)

    def test_off_only_ever_sees_persistent_records(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            io.open(os.path.join(d, "STATE.md"), "w").write("# Project STATE\n")
            self._run(d, "on")
            self._run(d, "start", "payments", "pay", "--files", "api/pay.py")
            self._run(d, "start", "billing", "bill", "--files", "api/bill.py")
            self._run(d, "checkpoint", "payments", "--next", "wire the webhook handler")
            self._run(d, "off")
            for rid, rec in reg.load(cwd=d)["records"].items():
                self.assertEqual(
                    rec.get("lifetime"), "persistent",
                    "record %r has lifetime %r at `off`. cmd_off drains every active "
                    "record regardless of lifetime, which silently releases an "
                    "ephemeral fence that is still in use. See the 2026-08-08 "
                    "ephemeral fence migration review before changing this test."
                    % (rid, rec.get("lifetime")))

    def test_no_tool_creates_a_non_persistent_record(self):
        # The reason the assertion above can hold: nothing in tools/ asks for
        # any other lifetime. Comments and docstrings describe "ephemeral", so
        # only executable lines count.
        offenders = []
        for fn in sorted(os.listdir(HERE)):
            if not fn.endswith(".py") or fn.startswith("test_"):
                continue
            in_doc = False
            for i, line in enumerate(io.open(os.path.join(HERE, fn), encoding="utf-8"), 1):
                stripped = line.strip()
                if stripped.count('"""') % 2:
                    in_doc = not in_doc
                    continue
                if in_doc or stripped.startswith("#"):
                    continue
                if '"ephemeral"' in line or "'ephemeral'" in line:
                    offenders.append("%s:%d" % (fn, i))
        self.assertEqual(offenders, [],
                         "a tool now creates a non-persistent record (%s). cmd_off "
                         "drains every active record regardless of lifetime: make it "
                         "select by lifetime first. See the 2026-08-08 ephemeral fence "
                         "migration review." % ", ".join(offenders))


class TestPreWriteGate(unittest.TestCase):
    """Every place in tools/ that writes a file must be a REVIEWED place.

    This does not prove redaction. It proves that a NEW write site cannot appear
    without someone deciding whether it needs redaction, which is the gap that
    let the same secret-leak bug ship three times in one week.
    """
    WRITE_PATTERNS = (r'open\([^)]*["\']w["\']', r'os\.open\(', r'\.write\(')

    def _sites(self):
        found = {}
        for fn in sorted(os.listdir(HERE)):
            if not fn.endswith(".py") or fn.startswith("test_"):
                continue
            src = io.open(os.path.join(HERE, fn), encoding="utf-8").read().splitlines()
            hits = []
            for i, line in enumerate(src, 1):
                if line.strip().startswith("#"):
                    continue
                for pat in self.WRITE_PATTERNS:
                    if re.search(pat, line):
                        hits.append(i)
                        break
            if hits:
                found[fn] = len(hits)
        return found

    def test_no_unreviewed_write_sites(self):
        manifest_path = os.path.join(HERE, "write_sites.json")
        self.assertTrue(os.path.exists(manifest_path),
                        "write_sites.json is missing; it is the reviewed inventory")
        manifest = json.load(io.open(manifest_path))["reviewed"]
        actual = self._sites()
        # Strengthened: the loop below only ever looked at files that still
        # write, so an empty scanner (a broken _sites, a renamed tool) passed
        # this test while proving nothing at all. Both directions must match.
        self.assertTrue(actual, "the write-site scanner found nothing; it is broken")
        for fn in sorted(manifest):
            self.assertIn(fn, actual,
                          "%s is in the reviewed inventory but no longer writes any "
                          "file. If it was renamed or its writes moved, update "
                          "tools/write_sites.json to match." % fn)
        for fn, count in sorted(actual.items()):
            self.assertIn(fn, manifest,
                          "%s writes files but is not in the reviewed inventory. "
                          "Review whether every text it writes passes through "
                          "redaction, then add it to tools/write_sites.json." % fn)
            self.assertEqual(
                count, manifest[fn],
                "%s has %d write sites but %d were reviewed. A write site was "
                "added or removed: confirm it redacts user or model text, then "
                "update tools/write_sites.json." % (fn, count, manifest[fn]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
