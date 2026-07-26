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

# Import bm_store as a module regardless of cwd, the same shape used above for
# bm_telemetry and the same shape test_bm_store.py uses for itself. Phase 3
# (ratified spec 2026-07-26-phase3-rewire-design.md) wired bm_threads.py onto
# this store; bm_registry.py is deleted. Every test below that needs to
# inspect a record's real state reads it from here, never from a hand-parsed
# JSON file, because there is no JSON file that holds ownership truth anymore.
_store_spec = importlib.util.spec_from_file_location("bm_store", os.path.join(HERE, "bm_store.py"))
bs = importlib.util.module_from_spec(_store_spec)
_store_spec.loader.exec_module(bs)
sys.modules["bm_store"] = bs

def _run_threads(args, cwd, env=None):
    """Invoke bm_threads.py as a subprocess, always with BROTHERMODE_ROOT
    scrubbed from the child's environment (matching test_bm_store.py's own
    _run_cli), so ambient developer state can never leak into a test that is
    trying to prove something about root resolution or refusal behaviour."""
    e = dict(os.environ)
    e.pop("BROTHERMODE_ROOT", None)
    if env:
        e.update(env)
    return subprocess.run(
        [sys.executable, os.path.join(HERE, "bm_threads.py")] + list(args),
        cwd=cwd, capture_output=True, text=True, env=e)


def _dump(root):
    store = bs.Store(root, create=False)
    try:
        return store.dump()
    finally:
        store.close()


def _record(root, name, states=None):
    """The store's record for `name` (optionally restricted to a set of
    states), most-recently-updated first, or None. A thin test helper
    mirroring bm_threads._find_record, written independently so a bug in
    that function cannot also hide from the test meant to catch it."""
    data = _dump(root)
    matches = [r for r in data["records"] if r["name"] == name]
    if states:
        matches = [r for r in matches if r["state"] in states]
    if not matches:
        return None
    matches.sort(key=lambda r: r["updated_at"], reverse=True)
    return matches[0]


def _claims(root, lifecycle_uuid):
    data = _dump(root)
    return sorted(c["path"] for c in data["claims"] if c["lifecycle_uuid"] == lifecycle_uuid)


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


class TestCompactHintHonesty(unittest.TestCase):
    """GATE E (fix-round 2026-07-26): compact-hint used to print "Your files
    are autosaved" UNCONDITIONALLY on every compaction resume, and named
    tools/bm_autosave.sh, which Phase 2 deleted. Fixed: the claim prints
    only when bm_autosave.has_receipt finds a real receipt for this
    worktree and session; otherwise an honest alternative names the
    command that actually exists (bm_autosave.py, not the deleted .sh).

    Two cases run the real CLI end to end as a subprocess (a receipt
    written by the real bm_autosave.py, and a store with none); the third
    patches the cached _BM_AUTOSAVE reference bm_telemetry itself loaded at
    import time (the PRODUCT symbol, not a local stand-in) to simulate
    bm_autosave.py being unavailable, since deleting or renaming the real
    file would cross this change's own fence."""

    def _git_repo(self, path):
        def git(*a):
            r = subprocess.run(["git", "-C", path] + list(a), capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, "git %s failed: %s" % (" ".join(a), r.stderr))
            return r
        git("init", "-q")
        git("config", "user.email", "t@t.t")
        git("config", "user.name", "t")
        io.open(os.path.join(path, "tracked.txt"), "w").write("v1")
        git("add", "-A")
        git("commit", "-qm", "init")

    def _init_store(self, repo, env):
        r = subprocess.run([sys.executable, os.path.join(HERE, "bm_store.py"), "init"],
                            cwd=repo, env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, "bm_store init failed: %s" % (r.stdout + r.stderr))

    def _compact_hint(self, repo, session_id, env):
        payload = json.dumps({"source": "compact", "cwd": repo, "session_id": session_id})
        return subprocess.run(
            [sys.executable, os.path.join(HERE, "bm_telemetry.py"), "compact-hint"],
            input=payload, cwd=repo, env=env, capture_output=True, text=True)

    def test_claims_safety_only_when_a_real_receipt_exists(self):
        with tempfile.TemporaryDirectory() as repo, tempfile.TemporaryDirectory() as v:
            env = dict(os.environ, BROTHERMODE_VAULT=v)
            env.pop("BROTHERMODE_ROOT", None)
            self._git_repo(repo)
            self._init_store(repo, env)
            # A snapshot of a working tree that matches HEAD writes no
            # receipt at all (nothing to save); dirty the tree first so
            # bm_autosave.py actually has something to capture.
            io.open(os.path.join(repo, "wip.txt"), "w").write("work in progress")
            snap = subprocess.run(
                [sys.executable, os.path.join(HERE, "bm_autosave.py"), "precompact"],
                input=json.dumps({"cwd": repo, "session_id": "sess-1"}),
                cwd=repo, env=env, capture_output=True, text=True)
            self.assertEqual(snap.returncode, 0, "bm_autosave precompact failed: %s"
                              % (snap.stdout + snap.stderr))
            r = self._compact_hint(repo, "sess-1", env)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("Your files are autosaved", r.stdout,
                          "a real receipt exists; the claim must be printed")
            self.assertIn("bm_autosave.py recover", r.stdout,
                          "must name the recovery command that actually exists")
            self.assertNotIn("bm_autosave.sh", r.stdout,
                             "must never name the deleted shell script")

    def test_no_claim_when_no_receipt_matches_this_session(self):
        with tempfile.TemporaryDirectory() as repo, tempfile.TemporaryDirectory() as v:
            env = dict(os.environ, BROTHERMODE_VAULT=v)
            env.pop("BROTHERMODE_ROOT", None)
            self._git_repo(repo)
            self._init_store(repo, env)
            # No snapshot was ever taken, so no receipt exists for any session.
            r = self._compact_hint(repo, "sess-never-saved", env)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertNotIn("Your files are autosaved", r.stdout,
                             "must not claim safety when no receipt was found")
            self.assertIn("No autosave snapshot receipt was found", r.stdout)
            self.assertIn("bm_autosave.py recover", r.stdout,
                          "must still name the recovery command that exists")
            self.assertNotIn("bm_autosave.sh", r.stdout)

    def test_no_claim_and_no_crash_when_bm_autosave_is_unavailable(self):
        old_mod, old_err = bm._BM_AUTOSAVE, bm._BM_AUTOSAVE_LOAD_ERROR
        bm._BM_AUTOSAVE = None
        bm._BM_AUTOSAVE_LOAD_ERROR = "simulated: bm_autosave.py unavailable"
        old_stdin, old_stdout = sys.stdin, sys.stdout
        try:
            sys.stdin = io.StringIO(json.dumps(
                {"source": "compact", "cwd": "/tmp", "session_id": "s1"}))
            sys.stdout = captured = io.StringIO()
            bm.cmd_compact_hint()  # must never raise
        finally:
            sys.stdin, sys.stdout = old_stdin, old_stdout
            bm._BM_AUTOSAVE, bm._BM_AUTOSAVE_LOAD_ERROR = old_mod, old_err
        out = captured.getvalue()
        self.assertNotIn("Your files are autosaved", out,
                         "must not claim safety when bm_autosave could not be loaded")
        self.assertIn("simulated: bm_autosave.py unavailable", out)
        self.assertNotIn("bm_autosave.sh", out)


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
    OFF mid-project is LOSSLESS (the founder's hard requirement). Recalibrated
    for Phase 3: ownership lives in the store, so every assertion below reads
    the store's real state instead of a hand-parsed registry.json."""

    def _run(self, cwd, *args):
        return _run_threads(args, cwd)

    def test_recommend_never_flips_mode(self):
        with tempfile.TemporaryDirectory() as d:
            r = self._run(d, "recommend", "5")
            self.assertIn("RECOMMENDATION", r.stdout)
            self.assertFalse(os.path.exists(os.path.join(d, "threads", "thread-mode.json")),
                             "recommend must never flip or create mode state")
            self.assertFalse(os.path.exists(os.path.join(d, ".brothermode")),
                             "recommend must never create a store either")

    def test_cap_is_enforced(self):
        # Recalibrated: V1 read BROTHERMODE_MAX_THREADS to shrink the cap for
        # a fast test. bm_store.MAX_ACTIVE_PERSISTENT (3) is a fixed module
        # constant with no env override (a store-level capability gap flagged
        # in the implementer's report), so this exercises the real cap.
        with tempfile.TemporaryDirectory() as d:
            self._run(d, "on")
            for n in ("a", "b", "c"):
                self._run(d, "start", n, "obj " + n, "--files", "api/%s.py" % n)
            r = self._run(d, "start", "dee", "one too many", "--files", "api/dee.py")
            self.assertEqual(r.returncode, 2)
            self.assertIn("refused (cap)", r.stdout)

    def test_off_is_lossless_and_parks(self):
        with tempfile.TemporaryDirectory() as d:
            self._run(d, "on")
            self._run(d, "start", "payments", "build payments", "--files", "api/pay.py")
            self._run(d, "checkpoint", "payments", "--decision", "chose Stripe",
                      "--topic", "payments-api", "--next", "wire webhook")
            r = self._run(d, "off")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            state = io.open(os.path.join(d, "STATE.md")).read()
            self.assertIn("chose Stripe", state, "decision lost when thread mode was turned off")
            self.assertIn("wire webhook", state, "next intent lost when thread mode was turned off")
            self.assertTrue(
                os.path.isdir(os.path.join(d, "threads"))
                and any(n.startswith("payments-") for n in os.listdir(os.path.join(d, "threads"))),
                "thread directory was deleted; it must stay resumable")
            rec = _record(d, "payments")
            self.assertEqual(rec["state"], "parked")

    def test_adopt_absorbs_a_dead_thread(self):
        with tempfile.TemporaryDirectory() as d:
            self._run(d, "on")
            self._run(d, "start", "search", "build search", "--files", "api/search.py")
            self._run(d, "checkpoint", "search", "--decision", "use trigram index",
                      "--topic", "search-impl")
            # --adopt-from-live-session: `start` and `adopt` each generate
            # their own session id here, so the store's live-session-adopt
            # gate (new in V2, see TestLiveSessionAdoptGate) always applies;
            # this is the founder deliberately confirming the takeover.
            r = self._run(d, "adopt", "search", "--adopt-from-live-session")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            state = io.open(os.path.join(d, "STATE.md")).read()
            self.assertIn("use trigram index", state, "adopted thread's context was orphaned")


class TestThreadSafety(unittest.TestCase):
    """The two defects a self-review found in thread mode, still true after
    Phase 3: secrets must never reach a file on disk unredacted."""

    def _run(self, cwd, *a):
        return _run_threads(a, cwd)

    def _thread_dir_name(self, d, prefix):
        return [n for n in os.listdir(os.path.join(d, "threads")) if n.startswith(prefix)][0]

    def test_secrets_never_reach_digest_or_absorbed_state(self):
        with tempfile.TemporaryDirectory() as d:
            self._run(d, "on")
            self._run(d, "start", "pay", "build pay", "--files", "api/pay.py")
            self._run(d, "checkpoint", "pay", "--decision",
                      "used PROD_DB_PASSWORD=hunter2 to test", "--topic", "creds",
                      "--next", "rotate it")
            tdir = self._thread_dir_name(d, "pay-")
            dig = io.open(os.path.join(d, "threads", tdir, "digest.md")).read()
            self.assertNotIn("hunter2", dig, "secret leaked into the thread digest")
            self._run(d, "off")
            st = io.open(os.path.join(d, "STATE.md")).read()
            self.assertNotIn("hunter2", st, "secret propagated into the project STATE.md")
            self.assertIn("rotate it", st, "redaction destroyed the real content")

    def test_secret_in_objective_does_not_reach_thread_files(self):
        # Finding: bm_threads.py's OWN thread-local STATE.md scaffold used to
        # embed the raw objective (fixed during this rewire, before this test
        # was written against it); the digest.md view was always safe because
        # it comes from bm_store.render_digest, which redacts internally.
        with tempfile.TemporaryDirectory() as d:
            self._run(d, "on")
            self._run(d, "start", "pay", "build pay using PROD_DB_PASSWORD=hunter2 now",
                      "--files", "api/pay.py")
            tdir = self._thread_dir_name(d, "pay-")
            base = os.path.join(d, "threads", tdir)
            state_md = io.open(os.path.join(base, "STATE.md")).read()
            digest_md = io.open(os.path.join(base, "digest.md")).read()
            mode = json.load(io.open(os.path.join(d, "threads", "thread-mode.json")))
            self.assertNotIn("hunter2", state_md, "secret leaked into the thread's STATE.md")
            self.assertNotIn("hunter2", digest_md, "secret leaked into the thread's digest.md")
            self.assertNotIn("hunter2", json.dumps(mode),
                             "secret leaked into thread-mode.json (it must hold no ownership "
                             "data at all in the new architecture)")
            self.assertIn("[REDACTED]", state_md, "redaction destroyed the objective entirely")
            r = self._run(d, "dashboard")
            self.assertNotIn("hunter2", r.stdout, "secret leaked into the dashboard output")

    def test_dashboard_survives_a_mode_value_that_is_not_a_string(self):
        # The rest of V1's dashboard-survives-malformed-input sweep
        # (a thread entry that is not a dict, an objective that is not a
        # string) is structurally closed now: the mode file no longer has a
        # "threads" map or per-thread objective at all, so that shape of
        # corruption cannot occur. The mode VALUE itself can still be
        # hand-edited to something odd, so that one case is kept.
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "threads"))
            io.open(os.path.join(d, "threads", "thread-mode.json"), "w").write(
                json.dumps({"mode": 5}))
            r = self._run(d, "dashboard")
            self.assertNotIn("Traceback", r.stderr,
                             "the dashboard raised on a non-string mode value")
            self.assertIn("BROTHERMODE THREADS", r.stdout)

    def test_concurrent_starts_all_register(self):
        # A thread invisible to the store is invisible to the dashboard AND
        # skipped by `off`, which would silently lose its context. The
        # store's own BEGIN IMMEDIATE serializes the writes; this proves the
        # CLI wrapper does not reintroduce a race on top of that guarantee.
        import threading as th
        with tempfile.TemporaryDirectory() as d:
            self._run(d, "on")
            ts = [th.Thread(target=self._run, args=(d, "start", n, "obj",
                                                      "--files", "api/%s.py" % n))
                  for n in "abc"]
            [t.start() for t in ts]
            [t.join() for t in ts]
            data = _dump(d)
            names = sorted(r["name"] for r in data["records"] if r["state"] == "active")
            self.assertEqual(names, ["a", "b", "c"], "a concurrent start was lost from the store")


class TestOffReportsHonestly(unittest.TestCase):
    def _run(self, cwd, *a):
        return _run_threads(a, cwd)

    def test_off_says_incomplete_and_keeps_the_thread_alive(self):
        # Finding 5 (V1): with STATE.md unwritable the registry correctly
        # refused to park anything, but `off` still flipped the mode and
        # reported "nothing to absorb": the exact opposite of the truth. The
        # new `off` must name the failure and refuse to flip the mode.
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("running as root: file permissions cannot be made to block a write")
        with tempfile.TemporaryDirectory() as d:
            self._run(d, "on")
            self._run(d, "start", "payments", "pay", "--files", "api/pay.py")
            self._run(d, "checkpoint", "payments", "--next", "wire the webhook handler")
            state_path = os.path.join(d, "STATE.md")
            io.open(state_path, "w").write("# Project STATE\n")
            before = io.open(state_path).read()
            os.chmod(state_path, stat.S_IREAD)
            try:
                r = self._run(d, "off")
                if io.open(state_path).read() != before:
                    self.skipTest("could not make STATE.md unwritable in this environment")
                self.assertEqual(r.returncode, 2, r.stdout)
                self.assertIn("HANDOVER INCOMPLETE", r.stdout)
                mode = json.load(io.open(os.path.join(d, "threads", "thread-mode.json")))
                self.assertEqual(mode["mode"], "on",
                                 "mode must not flip to off when the handover failed")
                rec = _record(d, "payments")
                self.assertEqual(rec["state"], "active",
                                 "the record must stay active so a retry can still absorb it")
            finally:
                os.chmod(state_path, stat.S_IREAD | stat.S_IWRITE)

    def test_off_reports_nothing_to_absorb_when_no_active_persistent_records_exist(self):
        # The other half of V1's finding 5: "nothing to absorb" must keep
        # meaning exactly that, so the two outcomes stay distinguishable.
        with tempfile.TemporaryDirectory() as d:
            self._run(d, "on")
            r = self._run(d, "off")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("nothing to absorb", r.stdout)
            mode = json.load(io.open(os.path.join(d, "threads", "thread-mode.json")))
            self.assertEqual(mode["mode"], "off")

    def test_off_survives_a_malformed_mode_file(self):
        with tempfile.TemporaryDirectory() as d:
            self._run(d, "on")
            self._run(d, "start", "payments", "pay", "--files", "api/pay.py")
            self._run(d, "checkpoint", "payments", "--next", "wire the webhook handler")
            mp = os.path.join(d, "threads", "thread-mode.json")
            mode = json.load(io.open(mp))
            mode["history"] = "not-a-list"
            mode["some_stray_hand_edited_key"] = {"whatever": True}
            io.open(mp, "w").write(json.dumps(mode))
            r = self._run(d, "off")
            self.assertNotIn("Traceback", r.stderr, "off raised on a malformed mode file")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("wire the webhook handler", io.open(os.path.join(d, "STATE.md")).read())


class TestCapIsAtomic(unittest.TestCase):
    def test_a_cap_refused_start_leaves_no_store_record(self):
        # Finding 6 (V1): a refused start left an active record behind
        # anyway, so a later claim on those files was refused by a record
        # the dashboard never showed. claim() and _admit() together make
        # this atomic in the store now; this proves it end to end through
        # the CLI.
        with tempfile.TemporaryDirectory() as d:
            _run_threads(["on"], d)
            for n in ("a", "b", "c"):
                _run_threads(["start", n, "obj", "--files", "api/%s.py" % n], d)
            r = _run_threads(["start", "dee", "one too many", "--files", "api/dee.py"], d)
            self.assertIn("refused (cap)", r.stdout)
            self.assertIsNone(_record(d, "dee"),
                             "a cap-refused start must leave no store record behind")


class TestAdopt(unittest.TestCase):
    """adopt is a write boundary and a fence release, and used to be neither."""

    def _run(self, cwd, *a):
        return _run_threads(a, cwd)

    # NOTE on --adopt-from-live-session, found while writing these tests:
    # bm_store.transition() refuses ('live-session-adopt-blocked') to move an
    # ACTIVE record to 'adopted' when the caller's session differs from the
    # one on file, unless adopt_from_live_session=True is passed explicitly.
    # `start` and `adopt` here each get their own freshly-generated session
    # id (no --session given), so they always differ, and the flag is
    # required for every one of these tests, not an edge case. This is the
    # store's OWN fail-closed design working as intended (adopting a record
    # that is still ACTIVE under a different, live session is a takeover
    # dressed as adoption); bm_threads.py must not default the flag to True,
    # or it would silently defeat that gate. See TestLiveSessionAdoptGate.

    def test_adopt_redacts_the_handover_it_delivers(self):
        # V1's adopt appended the thread's own hand-written STATE.md snippet
        # verbatim alongside the digest. V2's adopt delivers ONLY the store's
        # structured render_digest (objective/next-intent/blockers/files/
        # decisions), never arbitrary thread-local prose: a deliberate scope
        # reduction (see the implementer's report) that also means there is
        # exactly one redaction boundary to keep correct, not two. Any secret
        # that reaches STATE.md at all can only have arrived through a
        # checkpoint decision, so that is what this test drives through.
        with tempfile.TemporaryDirectory() as d:
            self._run(d, "on")
            self._run(d, "start", "payments", "build payments", "--files", "api/pay.py")
            self._run(d, "checkpoint", "payments", "--next", "wire the webhook handler",
                      "--topic", "notes",
                      "--decision", "deploy key AKIAIOSFODNN7EXAMPLE password=hunter2swordfish")
            r = self._run(d, "adopt", "payments", "--adopt-from-live-session")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            state = io.open(os.path.join(d, "STATE.md")).read()
            self.assertNotIn("AKIAIOSFODNN7EXAMPLE", state, "adopt leaked an AWS key into STATE.md")
            self.assertNotIn("hunter2swordfish", state, "adopt leaked a password into STATE.md")
            self.assertIn("[REDACTED]", state, "nothing was redacted at all")
            self.assertIn("wire the webhook handler", state,
                          "redaction destroyed the real handover content")

    def test_adopt_does_not_leave_the_digest_to_be_absorbed_twice(self):
        # Finding 4 (V1): adopt flipped the thread but left the record
        # active, so `off` drained the same digest again. adopted is a
        # terminal state `off` never selects (it only ever selects active
        # persistent records), so this is closed structurally now.
        #
        # Asserts the DELIVERY TAG count, not a raw text count: STATE.md's
        # generated dashboard block (refreshed by both `adopt` and `off`)
        # legitimately repeats a record's "next intent" text as part of its
        # always-current view, which is not a duplicate delivery. Counting
        # tags is what V1's own most rigorous property test (I2) did for the
        # same reason.
        with tempfile.TemporaryDirectory() as d:
            self._run(d, "on")
            self._run(d, "start", "payments", "build payments", "--files", "api/pay.py")
            self._run(d, "checkpoint", "payments", "--next", "wire the webhook handler")
            r = self._run(d, "adopt", "payments", "--adopt-from-live-session")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self._run(d, "off")
            state = io.open(os.path.join(d, "STATE.md")).read()
            tags = re.findall(r"brothermode-handover:[^\s>]+", state)
            self.assertEqual(len(tags), len(set(tags)),
                             "the adopted digest was delivered more than once: %s" % tags)
            self.assertIn("wire the webhook handler", state)

    def test_adopt_releases_the_file_fence(self):
        with tempfile.TemporaryDirectory() as d:
            self._run(d, "on")
            self._run(d, "start", "payments", "build payments", "--files", "api/pay.py")
            r = self._run(d, "adopt", "payments", "--adopt-from-live-session")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            rec = _record(d, "payments")
            self.assertNotEqual(rec["state"], "active", "the adopted record must not stay active")
            r = self._run(d, "start", "billing", "bill", "--files", "api/pay.py")
            self.assertNotIn("overlap", r.stdout.lower(),
                             "an adopted thread's fence must be released")
            self.assertIsNotNone(_record(d, "billing", states=("active",)),
                                 "the successor thread was never registered")


class TestLiveSessionAdoptGate(unittest.TestCase):
    """New in V2: adopting a record that is still ACTIVE under a different,
    live session now requires an explicit --adopt-from-live-session, and is
    refused (not silently forced) without it. V1 had no such gate at all; it
    let ANY adopt succeed regardless of whether the original session might
    still be running, which is a takeover dressed as adoption."""

    def test_adopt_without_the_flag_is_refused_and_changes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            _run_threads(["on"], d)
            _run_threads(["start", "payments", "build payments", "--files", "api/pay.py",
                         "--session", "sessA"], d)
            r = _run_threads(["adopt", "payments"], d)
            self.assertEqual(r.returncode, 2)
            self.assertIn("ADOPT REFUSED (live-session-adopt-blocked)", r.stdout)
            rec = _record(d, "payments", states=("active",))
            self.assertIsNotNone(rec, "a refused adopt must leave the record exactly as it was")
            self.assertEqual(rec["session_id"], "sessA")

    def test_adopt_with_the_flag_displaces_the_live_session(self):
        with tempfile.TemporaryDirectory() as d:
            _run_threads(["on"], d)
            _run_threads(["start", "payments", "build payments", "--files", "api/pay.py",
                         "--session", "sessA"], d)
            r = _run_threads(["adopt", "payments", "--adopt-from-live-session"], d)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(_record(d, "payments")["state"], "adopted")


class TestSecondSessionCannotTakeOver(unittest.TestCase):
    """THE reason this rewire exists: a second session must be REFUSED by
    name, never silently handed the fence a first session already holds. V1
    had no test for this because V1 had no defense against it (F3: a
    reusable name as identity, silent takeover on re-claim)."""

    def test_second_session_refused_on_live_name(self):
        with tempfile.TemporaryDirectory() as d:
            _run_threads(["on"], d)
            r1 = _run_threads(["start", "payments", "build payments",
                               "--files", "api/pay.py", "--session", "sessA"], d)
            self.assertEqual(r1.returncode, 0, r1.stdout + r1.stderr)
            r2 = _run_threads(["start", "payments", "steal it",
                               "--files", "api/pay.py", "--session", "sessB"], d)
            self.assertEqual(r2.returncode, 2,
                             "a second session must be refused, not silently granted")
            self.assertIn("refused (name-active)", r2.stdout)
            rec = _record(d, "payments", states=("active",))
            self.assertIsNotNone(rec)
            self.assertEqual(rec["session_id"], "sessA",
                             "ownership must still belong to the first session")
            self.assertEqual(rec["objective"], "build payments",
                             "the second session's objective must never have landed")


class TestParkResumeComplete(unittest.TestCase):
    """resume/park/complete are the store verbs V1 never had."""

    def test_park_resume_complete_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            _run_threads(["on"], d)
            _run_threads(["start", "alpha", "obj", "--files", "api/a.py", "--session", "s1"], d)
            r = _run_threads(["park", "alpha", "--session", "s1"], d)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(_record(d, "alpha")["state"], "parked")
            r = _run_threads(["resume", "alpha", "--session", "s1"], d)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(_record(d, "alpha")["state"], "active")
            _run_threads(["checkpoint", "alpha", "--next", "ready"], d)
            r = _run_threads(["complete", "alpha", "--session", "s1",
                              "--evidence", "tests pass: 12/12"], d)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(_record(d, "alpha")["state"], "complete")

    def test_park_refused_for_the_wrong_session(self):
        with tempfile.TemporaryDirectory() as d:
            _run_threads(["on"], d)
            _run_threads(["start", "alpha", "obj", "--files", "api/a.py", "--session", "s1"], d)
            r = _run_threads(["park", "alpha", "--session", "s2"], d)
            self.assertEqual(r.returncode, 2)
            self.assertIn("refused", r.stdout)
            self.assertEqual(_record(d, "alpha")["state"], "active",
                             "the wrong session must never be able to park someone else's thread")


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


class TestProjectSecurityClaims(unittest.TestCase):
    """Two project-wide gates that happen to have originally lived inside a
    registry-focused test class; they are not about the registry at all
    (they scan every module under tools/), so they moved here rather than
    being deleted with the class around them."""

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

    def test_no_network_claim_is_mechanically_true(self):
        """SECURITY.md's headline privacy claim ("makes no network calls") was
        published with a grep the reader was expected to run by hand, which
        means the claim rotted the moment nobody ran it. The line-count claim
        beside it has been gated since it drifted twice in one day; the claim
        that actually protects the founder's data was not. It is now.

        Shipping modules only: the test files themselves may import subprocess
        to drive the CLI they are testing, which is local execution, not a
        network call, and is what makes the CLI testable at all."""
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        tools = os.path.join(root, "tools")
        banned = ("urllib", "http", "socket", "requests", "ftplib", "smtplib",
                  "telnetlib", "xmlrpc", "subprocess", "asyncio")
        pattern = re.compile(
            r"^\s*(?:import|from)\s+(%s)\b" % "|".join(banned))
        offenders = []
        # ONE named exception, and it is documented in SECURITY.md rather than
        # hidden here: bm_autosave.py drives git, which is an external binary, so
        # it must import subprocess. Every call it makes is local (no remote, no
        # push, enforced by the shell-and-git half of this test below plus its own
        # suite). The exception is per FILE and per MODULE NAME, so a second file
        # cannot quietly inherit it, and subprocess remains banned everywhere else.
        allowed = {"bm_autosave.py": {"subprocess"}}
        for n in sorted(os.listdir(tools)):
            if not n.endswith(".py") or n.startswith("test_"):
                continue
            for i, line in enumerate(
                    io.open(os.path.join(tools, n), encoding="utf-8"), 1):
                m = pattern.match(line)
                if m and m.group(1) not in allowed.get(n, ()):
                    offenders.append("%s:%d imports %s" % (n, i, m.group(1)))
        self.assertEqual(
            offenders, [],
            "SECURITY.md claims BrotherMode makes no network calls and that the "
            "tools run no subprocess, but %s. Either remove the import or "
            "correct SECURITY.md; do not leave the document claiming more than "
            "the code delivers." % ", ".join(offenders))

        # The shell half of the claim: the autosave runs git locally and must
        # never reach a remote. A pushing autosave would send the founder's
        # entire working tree, untracked files included, somewhere it was never
        # promised to go.
        net_cmds = re.compile(r"(?<![\w-])(curl|wget|nc|ssh|scp)\s")
        push = re.compile(r"git\s+(?:-C\s+\S+\s+)?(?:push|fetch|pull|clone|remote)\b")
        shell_offenders = []
        for n in sorted(os.listdir(tools)):
            if not n.endswith(".sh"):
                continue
            for i, line in enumerate(
                    io.open(os.path.join(tools, n), encoding="utf-8"), 1):
                code = line.split("#", 1)[0]
                if net_cmds.search(code) or push.search(code):
                    shell_offenders.append("%s:%d" % (n, i))
        self.assertEqual(
            shell_offenders, [],
            "a shell tool now reaches the network or a git remote (%s). "
            "SECURITY.md promises the autosave is local only and never pushes."
            % ", ".join(shell_offenders))


class TestThreadsUseStore(unittest.TestCase):
    """Ported from TestThreadsUseRegistry: the same behavioural claims,
    re-verified against the store the CLI now actually writes to. The
    cross-record topic-clash test that used to live here is deleted, not
    ported: bm_store.decide() is a per-lifecycle append-only primitive with
    no cross-record awareness, and the ratified command mapping does not
    name clash detection as a store concern. This is a real feature
    reduction, reported in the implementer's report, not an oversight."""

    def _run(self, cwd, *a):
        return _run_threads(a, cwd)

    def test_start_registers_a_record_with_files(self):
        with tempfile.TemporaryDirectory() as d:
            self._run(d, "on")
            self._run(d, "start", "payments", "build payments", "--files", "api/pay.py")
            rec = _record(d, "payments", states=("active",))
            self.assertIsNotNone(rec, "start did not create a work record")
            self.assertEqual(_claims(d, rec["lifecycle_uuid"]), ["api/pay.py"])

    def test_start_refuses_an_overlapping_thread(self):
        with tempfile.TemporaryDirectory() as d:
            self._run(d, "on")
            self._run(d, "start", "payments", "pay", "--files", "api/pay.py")
            r = self._run(d, "start", "billing", "bill", "--files", "api/pay.py")
            self.assertEqual(r.returncode, 2)
            self.assertIn("refused (overlap)", r.stdout)
            self.assertIn("payments", r.stdout, "the refusal must name the conflicting record")

    def test_off_absorbs_through_the_store(self):
        with tempfile.TemporaryDirectory() as d:
            self._run(d, "on")
            self._run(d, "start", "payments", "pay", "--files", "api/pay.py")
            self._run(d, "checkpoint", "payments", "--topic", "api",
                      "--decision", "chose Stripe", "--next", "wire webhook")
            self._run(d, "off")
            state = io.open(os.path.join(d, "STATE.md")).read()
            self.assertIn("chose Stripe", state)
            self.assertIn("wire webhook", state)
            self.assertEqual(_record(d, "payments")["state"], "parked")


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


class TestHonestReportingUnderFailure(unittest.TestCase):
    """I6, recalibrated. bm_threads.py now wraps a store where every mutation
    is already its own atomic transaction, so the honesty surface that
    matters at THIS layer is narrower than V1's: does the CLI wrapper ever
    turn a genuine store success into a reported failure, or silently eat a
    local VIEW-file failure (a mailbox regeneration) as if the underlying
    store write had failed too? Each test patches exactly one function in an
    in-process import of bm_threads.py, the same calibration V1's own I6
    suite used: permissions fail the FIRST write in a command and never
    reach the one under test, so the injection has to be this precise."""

    def _mod(self, tag):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "bm_threads_honesty_%s" % tag, os.path.join(HERE, "bm_threads.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    @contextlib.contextmanager
    def _in(self, d):
        old = os.getcwd()
        os.chdir(d)
        try:
            yield
        finally:
            os.chdir(old)

    def test_start_reports_failure_when_thread_files_cannot_be_written(self):
        with tempfile.TemporaryDirectory() as d:
            mod = self._mod("start")
            with self._in(d):
                with contextlib.redirect_stdout(io.StringIO()):
                    mod.cmd_on([])
                mod._atomic_write = lambda path, text: False
                buf = io.StringIO()
                try:
                    with contextlib.redirect_stdout(buf):
                        mod.cmd_start(["alpha", "obj", "--files", "api/a.py"])
                except SystemExit as e:
                    self.assertEqual(e.code, 2)
                out = buf.getvalue()
            self.assertNotIn("created at", out,
                             "reported the thread created while its files could not be written")
            self.assertIn("START FAILED", out)
            # And honestly: the store record itself must still exist (claim()
            # is its own atomic transaction, a separate boundary from the
            # local mailbox files, and the message says exactly that).
            rec = _record(d, "alpha", states=("active",))
            self.assertIsNotNone(rec, "the store record must not vanish just because "
                                 "the local mailbox files failed to write")

    def test_checkpoint_warns_but_does_not_lie_when_the_digest_view_write_fails(self):
        with tempfile.TemporaryDirectory() as d:
            mod = self._mod("checkpoint")
            with self._in(d):
                with contextlib.redirect_stdout(io.StringIO()):
                    mod.cmd_on([])
                    mod.cmd_start(["alpha", "obj", "--files", "api/a.py"])
                mod._atomic_write = lambda path, text: False
                out_buf, err_buf = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(out_buf), contextlib.redirect_stderr(err_buf):
                    mod.cmd_checkpoint(["alpha", "--next", "next: LIETOKEN"])
                out, err = out_buf.getvalue(), err_buf.getvalue()
            # The STORE write really did succeed (checkpoint() is its own
            # transaction), so reporting it recorded is honest, not a lie...
            self.assertIn("checkpoint", out)
            self.assertIn("recorded", out)
            # ...but the view that failed to refresh must be named, not silent.
            self.assertIn("digest.md", err)
            digests = json.dumps(_dump(d)["digests"])
            self.assertIn("LIETOKEN", digests,
                          "the checkpoint really must be in the store even though the "
                          "local digest.md view failed to refresh")

    def test_off_never_reports_success_when_the_mode_write_fails(self):
        with tempfile.TemporaryDirectory() as d:
            mod = self._mod("off")
            with self._in(d):
                with contextlib.redirect_stdout(io.StringIO()):
                    mod.cmd_on([])
                mod._save_mode = lambda root, d: False
                buf = io.StringIO()
                try:
                    with contextlib.redirect_stdout(buf):
                        mod.cmd_off([])
                except SystemExit:
                    pass
                out = buf.getvalue()
            self.assertNotIn("thread mode OFF (drained", out,
                             "I6: reported OFF while the mode write failed")


class TestPartialOffAtomicity(unittest.TestCase):
    """I8, recalibrated: one thread's handover succeeds, a sibling's fails.
    The failing one must stay ACTIVE and fenced; the succeeding one must
    still be parked, and `off` must say so honestly rather than report every
    record as untouched when some of them really were drained (V1's own
    off-outside-the-lock race produced exactly this shape of lie, measured
    at 28 of 30 trials before it was fixed)."""

    def _mod(self, tag):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "bm_threads_partial_%s" % tag, os.path.join(HERE, "bm_threads.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_a_partial_off_parks_the_survivor_and_holds_the_failure(self):
        with tempfile.TemporaryDirectory() as d:
            mod = self._mod("partial")
            old = os.getcwd()
            os.chdir(d)
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    mod.cmd_on([])
                    mod.cmd_start(["alpha", "a", "--files", "api/a.py"])
                    mod.cmd_start(["beta", "b", "--files", "api/b.py"])
                    mod.cmd_checkpoint(["alpha", "--next", "next: A"])
                    mod.cmd_checkpoint(["beta", "--next", "next: B"])
                real = mod._deliver_handover_once

                def beta_fails(root, store, lifecycle_uuid, heading):
                    if "beta" in heading:
                        return False
                    return real(root, store, lifecycle_uuid, heading)
                mod._deliver_handover_once = beta_fails
                try:
                    with contextlib.redirect_stdout(io.StringIO()), \
                         contextlib.redirect_stderr(io.StringIO()):
                        try:
                            mod.cmd_off([])
                        except SystemExit:
                            pass
                finally:
                    mod._deliver_handover_once = real
            finally:
                os.chdir(old)
            self.assertEqual(_record(d, "alpha")["state"], "parked",
                             "the sibling whose handover succeeded must still be parked")
            self.assertEqual(_record(d, "beta")["state"], "active",
                             "beta's fence must stay held since its handover failed")
            mode = json.load(io.open(os.path.join(d, "threads", "thread-mode.json")))
            self.assertEqual(mode["mode"], "on",
                             "mode must stay ON while any active persistent record remains")


class TestReclaimPreservesWorkingFiles(unittest.TestCase):
    """I9, recalibrated: V1 allowed re-running `start` on any live thread by
    name alone. V2's claim() only allows an in-place update ("reclaim") when
    the SAME session re-declares the SAME active name; a different session
    is refused (TestSecondSessionCannotTakeOver). This proves the legitimate
    reclaim path still never stamps a blank template over a working plan,
    chief directives, or an advancement history that already exist."""

    def test_restarting_with_the_same_session_preserves_every_working_file(self):
        with tempfile.TemporaryDirectory() as d:
            _run_threads(["on"], d)
            _run_threads(["start", "alpha", "objective", "--files", "api/a.py",
                         "--session", "s1"], d)
            tdir = [n for n in os.listdir(os.path.join(d, "threads")) if n.startswith("alpha-")][0]
            base = os.path.join(d, "threads", tdir)
            marks = {"STATE.md": "MY-WORKING-PLAN", "inbox.md": "CHIEF-DIRECTIVE",
                     "outbox.md": "ADVANCEMENT-LOG", "digest.md": "HANDOVER-CONTENT"}
            before = {}
            for fname, mark in marks.items():
                with io.open(os.path.join(base, fname), "a", encoding="utf-8") as fh:
                    fh.write("\n%s\n" % mark)
                before[fname] = io.open(os.path.join(base, fname), encoding="utf-8").read()
            r = _run_threads(["start", "alpha", "different objective", "--files", "api/a.py",
                              "--session", "s1"], d)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for fname, mark in marks.items():
                after = io.open(os.path.join(base, fname), encoding="utf-8").read()
                self.assertEqual(after, before[fname],
                                 "reclaiming 'alpha' changed %s and lost %s" % (fname, mark))


class TestArchitecturalGuards(unittest.TestCase):
    """Structural checks that stay true by construction, not by discipline
    someone has to remember."""

    def test_bm_threads_has_no_bm_registry_reference(self):
        # Scoped to this rewire's own fence (bm_threads.py, and bm_registry.py's
        # deletion): bm_store.py is OUTSIDE that fence and is deliberately not
        # asserted on here. bm_store.py's own module docstring names
        # "bm_registry.py" several times as HISTORICAL, purely explanatory
        # prose (why the store replaced it), which is legitimate and not this
        # test's concern.
        #
        # bm_telemetry.py's `attribute` command USED TO still load
        # bm_registry.py by path at runtime, a real, currently-broken
        # cross-fence dependency once the file was gone (it accumulated
        # spend onto a dict-shaped registry.json record that bm_store.py's
        # sqlite schema has no equivalent of at all). Fix-round 2026-07-26
        # deleted the command rather than port it: nothing in the repo
        # called it except historical design docs, and no test exercised its
        # success path, so a silent no-op was strictly worse than removing
        # it. Asserted here now that it is this test's concern again.
        self.assertFalse(os.path.exists(os.path.join(HERE, "bm_registry.py")),
                         "bm_registry.py must be deleted, not merely unreferenced")
        src = io.open(os.path.join(HERE, "bm_threads.py"), encoding="utf-8").read()
        self.assertNotIn("bm_registry", src,
                         "bm_threads.py must not reference the deleted bm_registry module")
        # bm_telemetry.py, unlike bm_threads.py, is allowed the same kind of
        # HISTORICAL prose mention bm_store.py's docstring carries (explaining
        # why `attribute` was deleted rather than ported); what must actually
        # be gone is the runtime load, so this checks for the exact spec name
        # the deleted code used rather than banning the bare word.
        tel_src = io.open(os.path.join(HERE, "bm_telemetry.py"), encoding="utf-8").read()
        self.assertNotIn("bm_registry_for_telemetry", tel_src,
                         "bm_telemetry.py must not load bm_registry.py by path at runtime "
                         "(the `attribute` command was deleted, not ported, fix-round 2026-07-26)")
        self.assertNotIn("def cmd_attribute", tel_src,
                         "cmd_attribute was deleted (fix-round 2026-07-26); it must not come back "
                         "without a store-backed spend concept to port it onto")

    def test_handover_delivery_has_exactly_one_owner(self):
        # THE ARCHITECTURAL GUARD, carried over from V1's own version of this
        # test: delivering a handover into the project STATE.md may happen in
        # exactly one place, so a new writer that appends its own fails here
        # rather than shipping and waiting to be caught.
        src = io.open(os.path.join(HERE, "bm_threads.py"), encoding="utf-8").read()
        callers = [ln.strip() for ln in src.splitlines() if 'io.open(state_path, "a"' in ln]
        self.assertEqual(len(callers), 1,
                         "exactly one function may append to the project STATE.md "
                         "(_deliver_handover_once); found: %s" % callers)

    def test_root_resolution_is_independent_of_the_calling_subdirectory(self):
        # Closes the "working directory as identity" defect for thread
        # mode's OWN files too, not only for ownership: a command run from a
        # subdirectory must resolve the SAME project root as one run from
        # the top.
        with tempfile.TemporaryDirectory() as d:
            _run_threads(["on"], d)
            sub = os.path.join(d, "some", "nested", "subdir")
            os.makedirs(sub)
            top = _run_threads(["dashboard"], d)
            nested = _run_threads(["dashboard"], sub)
            top_line = [l for l in top.stdout.splitlines() if l.startswith("BROTHERMODE THREADS")][0]
            nested_line = [l for l in nested.stdout.splitlines()
                           if l.startswith("BROTHERMODE THREADS")][0]
            self.assertEqual(top_line, nested_line,
                             "the resolved root must not depend on the calling subdirectory")
            self.assertIn(os.path.realpath(d), nested_line)


class TestCliSequencesNeverRaiseOrLeaveDoubleActiveThreads(unittest.TestCase):
    """A narrower answer to the same testing defect V1's giant random-sequence
    generator targeted, rescoped for Phase 3.

    V1's version asserted content-level invariants (I1-I9 in the old,
    now-retired INVARIANTS.md) against the exact shape of registry.json and
    thread-mode.json, several of which describe files or a policy ("every
    path exits 0") that no longer exist: ownership operations now FAIL
    CLOSED on purpose (a live design decision, not an oversight this test
    would be catching). Losslessness, single-writer, crash-atomicity, and
    exactly-once delivery are the STORE's job now and are exercised
    adversarially by test_bm_store.py's own 182 tests, including its own
    concurrency coverage.

    What is still this module's own job, and what nothing else isolates on
    its own, is that the thin CLI WRAPPER never turns a store refusal into
    an unhandled traceback, and that a completed `off` never leaves the
    system internally inconsistent (mode says off, a persistent record
    still says active). This is intentionally SMALLER in scope than the
    320-line generator it replaces; see the implementer's report for why a
    full port was not attempted."""

    OPS = ("start", "checkpoint", "park", "resume", "complete", "adopt", "send", "off")

    def test_short_random_sequences_stay_honest(self):
        import random
        for seed in range(6):
            self._run_sequence(seed)

    def _run_sequence(self, seed, steps=14):
        import random
        rng = random.Random(seed)
        names = ["alpha", "beta"]
        with tempfile.TemporaryDirectory() as d:
            _run_threads(["on"], d)
            for step in range(steps):
                name = rng.choice(names)
                rec = _record(d, name)
                op = rng.choice(self.OPS)
                args = {
                    "start": ["start", name, "objective %d" % step, "--files",
                              "api/%s_%d.py" % (name, rng.randint(0, 1)), "--session", "s1"],
                    "checkpoint": ["checkpoint", name, "--next", "next: T%d" % step],
                    "park": ["park", name, "--session", "s1"],
                    "resume": ["resume", name, "--session", "s1"],
                    "complete": ["complete", name, "--session", "s1", "--evidence", "ok"],
                    "adopt": ["adopt", name],
                    "send": ["send", name, "a directive"],
                    "off": ["off"],
                }[op]
                r = _run_threads(args, d)
                where = "seed=%d step=%d op=%s rec=%r" % (seed, step, op, rec)
                self.assertNotIn("Traceback", r.stderr, "unhandled exception (%s): %s" % (where, r.stderr))
                self.assertIn(r.returncode, (0, 2),
                              "exit code must be 0 (ok) or 2 (a clean, named refusal), "
                              "never anything else (%s): %d" % (where, r.returncode))
                if op == "off" and r.returncode == 0:
                    mode = json.load(io.open(os.path.join(d, "threads", "thread-mode.json")))
                    if mode.get("mode") == "off":
                        data = _dump(d)
                        still_active = [x["name"] for x in data["records"]
                                       if x["state"] == "active" and x["lifetime"] == "persistent"]
                        self.assertEqual(still_active, [],
                                         "off reported success (%s) but left an active "
                                         "persistent record: %s" % (where, still_active))


if __name__ == "__main__":
    unittest.main(verbosity=2)
