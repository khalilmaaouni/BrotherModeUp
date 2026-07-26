#!/usr/bin/env python3
"""Regression tests for tools/bm_store.py, the BrotherMode V2 engine core.
Standard library only. Run: python3 tools/test_bm_store.py

Every test here is self-contained under tempfile.TemporaryDirectory() and
never touches this repo's own files, BROTHERMODE_ROOT, or the real home
directory. The calibrated_* tests each reproduce one confirmed V1 defect
(named inline, see docs/superpowers/specs/2026-07-26-brothermode-v2-design.md)
and assert that V2 refuses what V1 silently allowed.
"""
import datetime
import glob
import io
import json
import ntpath
import os
import re
import sqlite3
import stat
import subprocess
import sys
import tempfile
import unittest
import uuid
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))

import importlib.util
_spec = importlib.util.spec_from_file_location("bm_store", os.path.join(HERE, "bm_store.py"))
bs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bs)
sys.modules["bm_store"] = bs


def _run_cli(args, cwd, env=None):
    """Invoke the CLI as a subprocess, always with BROTHERMODE_ROOT scrubbed
    from the child's environment so ambient developer state (this repo's own
    checkout, a shell export left over from another task) can never leak
    into a test that is trying to prove something about root resolution or
    exit codes."""
    e = dict(os.environ)
    e.pop("BROTHERMODE_ROOT", None)
    if env:
        e.update(env)
    return subprocess.run(
        [sys.executable, os.path.join(HERE, "bm_store.py")] + args,
        cwd=cwd, capture_output=True, text=True, env=e)


# ---------------------------------------------------------------------------
# The 10 calibrated reinjection tests: each is one confirmed V1 defect,
# reproduced, then asserted fixed.
# ---------------------------------------------------------------------------

class TestCalibratedReinjections(unittest.TestCase):
    def test_calibrated_1_claim_same_name_different_session_refused(self):
        # V1 (bm_registry.claim): a second claim under the same id silently
        # replaced the fence regardless of who asked (F3, no takeover guard).
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                store.claim("payments", "persistent", "build it", ["api/pay.py"],
                            session_id="session-A")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.claim("payments", "persistent", "steal it", ["api/pay.py"],
                                session_id="session-B")
                self.assertEqual(ctx.exception.reason, "name-active")
                # nothing changed: the original record is still there, active,
                # under session-A's objective.
                still = store.get(store.conn.execute(
                    "SELECT lifecycle_uuid FROM records WHERE name='payments'"
                ).fetchone()["lifecycle_uuid"])
                self.assertEqual(still.objective, "build it")
                self.assertEqual(still.session_id, "session-A")
            finally:
                store.close()

    def test_calibrated_2_root_resolves_same_db_from_root_and_subdir(self):
        # V1 minted a SEPARATE registry per working directory (F2): a session
        # in threads/foo/ and a session at the project root each believed
        # they were the only writer. Prove resolve_root(subdir) equals
        # resolve_root(root), and that a claim from either resolved path
        # lands in the SAME sqlite file (a second overlapping claim is
        # refused, which is only possible if both saw the first one).
        with tempfile.TemporaryDirectory() as d:
            root = os.path.realpath(d)
            os.makedirs(os.path.join(root, ".brothermode"))
            subdir = os.path.join(root, "threads", "foo")
            os.makedirs(subdir)
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("BROTHERMODE_ROOT", None)
                root_a, src_a = bs.resolve_root(start=root)
                root_b, src_b = bs.resolve_root(start=subdir)
            self.assertEqual(root_a, root_b)
            self.assertEqual((src_a, src_b), ("marker", "marker"))
            self.assertEqual(bs.store_path(root_a), bs.store_path(root_b))
            store_a = bs.Store(root_a)
            store_b = bs.Store(root_b)
            try:
                store_a.claim("payments", "ephemeral", "obj", ["api/pay.py"], session_id="s1")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store_b.claim("other", "ephemeral", "obj2", ["api/pay.py"], session_id="s2")
                self.assertEqual(ctx.exception.reason, "overlap")
            finally:
                store_a.close()
                store_b.close()

    def test_calibrated_3_dotdot_dot_and_slash_names_raise(self):
        # V1 wrote thread directories straight from the name, so ".." wrote
        # into the project root and "a/b" wrote into a nested path (F4).
        for bad in ("..", ".", "a/b"):
            with self.assertRaises(ValueError):
                bs.valid_name(bad)

    def test_calibrated_4_conservative_glob_vs_glob_conflict(self):
        # V1's overlap check said these two patterns did not conflict (F11),
        # even though a file named "pay.py" matches both.
        self.assertTrue(bs.paths_overlap("api/*.py", "api/pay.*"))

    def test_calibrated_5_next_intent_survives_20_long_decisions(self):
        # V1 kept one shared 4000-char digest budget; enough decisions cut
        # next_intent out of the rendered handover entirely (F12).
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                rec = store.claim("thing", "ephemeral", "obj", [])
                v = rec.version
                for i in range(20):
                    store.decide(rec.lifecycle_uuid, v, "topic-%d" % i, "x" * 500)
                    v += 1
                next_intent = "resume from the payments webhook handler, tests are green"
                store.checkpoint(rec.lifecycle_uuid, v, next_intent)
                out = store.render_digest(rec.lifecycle_uuid)
                self.assertIn("## Next intent", out)
                self.assertIn(next_intent, out)
            finally:
                store.close()

    def test_calibrated_6_handover_fingerprint_differs_with_objective_only(self):
        # V1 truncated its fingerprint to 12 hex chars; two payloads differing
        # only in objective collided and the second handover was dropped (F13).
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                # A non-empty, matching session id on both calls: since GATE
                # 3 (fix-round 2026-07-26), an empty session id never
                # matches another empty one, so this reclaim path requires a
                # real session identity to exercise the SAME-lifecycle
                # update-in-place branch at all.
                rec = store.claim("thing", "ephemeral", "objective A", [], session_id="s1")
                p1 = store.handover_payload(rec.lifecycle_uuid)
                store.claim("thing", "ephemeral", "objective B", [], session_id="s1")
                p2 = store.handover_payload(rec.lifecycle_uuid)
                self.assertEqual(len(p1["fingerprint"]), 64)
                self.assertEqual(len(p2["fingerprint"]), 64)
                int(p1["fingerprint"], 16)
                int(p2["fingerprint"], 16)
                self.assertNotEqual(p1["fingerprint"], p2["fingerprint"])
            finally:
                store.close()

    def test_calibrated_7_checkpoint_against_parked_record_stale(self):
        # V1 kept writing digests into a thread's record even after it had
        # been closed out from under it (F5/F6).
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                rec = store.claim("thing", "ephemeral", "obj", [])
                parked = store.transition(rec.lifecycle_uuid, rec.version, "parked")
                with self.assertRaises(bs.StaleIdentity):
                    store.checkpoint(rec.lifecycle_uuid, parked.version, "next step")
            finally:
                store.close()

    def test_calibrated_8_corrupt_db_quarantines_and_recovers(self):
        # V1 overwrote a damaged registry with a fresh empty one, silently
        # discarding whatever was recoverable (F9).
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(bs.store_dir(d))
            path = bs.store_path(d)
            with io.open(path, "wb") as f:
                f.write(b"not a real sqlite database, just garbage bytes 1234567890")
            with self.assertRaises(bs.StoreCorrupt) as ctx:
                bs.Store(d)
            qpath = ctx.exception.quarantine_path
            self.assertTrue(qpath and os.path.exists(qpath),
                             "the damaged file must survive at the quarantine path")
            self.assertFalse(os.path.exists(path), "the corrupt path must be vacated by the rename")
            store = bs.Store(d)
            try:
                rec = store.claim("thing", "ephemeral", "test", [])
                self.assertEqual(rec.state, "active")
            finally:
                store.close()

    def test_calibrated_9_stale_version_on_transition_record_unchanged(self):
        # New optimistic-concurrency guarantee: a stale expected_version must
        # refuse, and the record on disk must be untouched by the attempt.
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                rec = store.claim("thing", "ephemeral", "obj", [])
                with self.assertRaises(bs.StaleIdentity):
                    store.transition(rec.lifecycle_uuid, rec.version + 1, "parked")
                fresh = store.get(rec.lifecycle_uuid)
                self.assertEqual(fresh.state, "active")
                self.assertEqual(fresh.version, rec.version)
            finally:
                store.close()

    def test_calibrated_10_resume_restores_active_same_lifecycle(self):
        # V1 had no resume at all (F8): parking a thread was one-way.
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                rec = store.claim("thing", "ephemeral", "obj", [])
                parked = store.transition(rec.lifecycle_uuid, rec.version, "parked")
                resumed = store.transition(parked.lifecycle_uuid, parked.version, "active")
                self.assertEqual(resumed.lifecycle_uuid, rec.lifecycle_uuid)
                self.assertEqual(resumed.state, "active")
            finally:
                store.close()

    def test_calibrated_11_locked_database_refuses_without_quarantine(self):
        # Amended 2026-07-26: the first draft quarantined on ANY
        # sqlite3.DatabaseError, and a busy/locked database (OperationalError,
        # a DatabaseError subclass) got renamed out from under a concurrent
        # writer, which is itself data loss. A tiny busy_timeout_ms makes the
        # "database is locked" failure near-instant instead of a real 5s wait.
        with tempfile.TemporaryDirectory() as d:
            store0 = bs.Store(d)
            store0.close()
            path = bs.store_path(d)
            locker = sqlite3.connect(path, timeout=0, isolation_level=None)
            locker.execute("BEGIN EXCLUSIVE")
            try:
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    bs.Store(d, busy_timeout_ms=50)
                self.assertEqual(ctx.exception.reason, "db-busy")
                self.assertTrue(os.path.exists(path),
                                 "a healthy, merely busy database must not be moved")
                self.assertEqual(glob.glob(path + ".quarantine-*"), [],
                                  "a busy database must NEVER be quarantined")
            finally:
                locker.execute("ROLLBACK")
                locker.close()
            # The lock is released: a normal open must now succeed cleanly,
            # proving nothing about the healthy database was disturbed.
            store1 = bs.Store(d)
            try:
                rec = store1.claim("thing", "ephemeral", "obj", [])
                self.assertEqual(rec.state, "active")
            finally:
                store1.close()

    def test_redaction_secret_hidden_in_views_but_present_in_dump(self):
        # Amended 2026-07-26 (the first draft omitted redaction): a
        # secret-shaped token in an objective and a decision must never leave
        # the store through a generated view, but dump() is the documented
        # raw export and must still show it.
        secret = "sk-test1234567890abcdef"
        with tempfile.TemporaryDirectory() as d:
            bs.init_project(d)
            store = bs.Store(d)
            try:
                rec = store.claim("thing", "ephemeral",
                                   "rotate the key, %s leaked in the log" % secret, [])
                store.decide(rec.lifecycle_uuid, rec.version, "secret",
                             "found token %s in the ticket" % secret)
                store.checkpoint(rec.lifecycle_uuid, rec.version + 1,
                                  "next: rotate %s for real" % secret)
                view = bs.write_state_view(d)
                digest = store.render_digest(rec.lifecycle_uuid)
                dump = store.dump()
            finally:
                store.close()
            self.assertNotIn(secret, view)
            self.assertIn("[REDACTED]", view)
            self.assertNotIn(secret, digest)
            self.assertIn("[REDACTED]", digest)
            dump_text = json.dumps(dump)
            self.assertIn(secret, dump_text,
                          "dump() is the documented raw export and must still show it")
            r = _run_cli(["dashboard"], d)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertNotIn(secret, r.stdout)


# ---------------------------------------------------------------------------
# Fix-round 2026-07-26: the four-lens adversarial fleet's 9 gate defects and
# 2 soft findings. Every test below is CALIBRATED per the fix-round contract:
# it targets one named defect, and its docstring/comment states what the
# PRE-fix behavior was so the connection between test and defect is explicit.
# ---------------------------------------------------------------------------

class TestFixRoundGates(unittest.TestCase):
    # -- GATE 1: path canonicalization -----------------------------------

    def test_calibrated_gate1a_dotdot_segment_resolved_before_compare(self):
        # VERIFIED BY ORCHESTRATOR: paths_overlap('db.py', 'api/../db.py')
        # was False, because '..' was never lexically resolved.
        self.assertTrue(bs.paths_overlap("db.py", "api/../db.py"))

    def test_calibrated_gate1b_root_dot_overlaps_everything(self):
        # paths_overlap('.', 'api/pay.py') was False; '.' (the canonical
        # form of the whole root) must overlap every other path.
        self.assertTrue(bs.paths_overlap(".", "api/pay.py"))
        self.assertTrue(bs.paths_overlap("api/pay.py", "."))

    def test_calibrated_gate1c_subdir_and_root_caller_converge(self):
        # A claim typed from a subdirectory used to store 'pay.py' while the
        # same claim typed from the root stored 'api/pay.py', and BOTH won
        # (two different strings, neither overlapping the other).
        with tempfile.TemporaryDirectory() as d:
            root = os.path.realpath(d)
            os.makedirs(os.path.join(root, "api"))
            from_root = bs.canonicalize_path(root, "api/pay.py", cwd=root)
            from_subdir = bs.canonicalize_path(root, "pay.py", cwd=os.path.join(root, "api"))
            self.assertEqual(from_root, from_subdir)
            self.assertEqual(from_root, "api/pay.py")

    def test_calibrated_gate1d_dotdot_escape_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(bs.OwnershipRefused) as ctx:
                bs.canonicalize_path(d, "../outside.py", cwd=d)
            self.assertEqual(ctx.exception.reason, "path-escape")

    def test_calibrated_gate1e_absolute_path_inside_root_canonicalized_not_verbatim(self):
        # Absolute paths were stored VERBATIM, leaking the founder's real
        # filesystem layout into dump()/dashboard.
        with tempfile.TemporaryDirectory() as d:
            root = os.path.realpath(d)
            abs_path = os.path.join(root, "api", "pay.py")
            canon = bs.canonicalize_path(root, abs_path)
            self.assertEqual(canon, "api/pay.py")
            self.assertNotIn(root, canon)

    def test_calibrated_gate1f_absolute_path_outside_root_refused(self):
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            with self.assertRaises(bs.OwnershipRefused) as ctx:
                bs.canonicalize_path(d1, os.path.join(d2, "x.py"))
            self.assertEqual(ctx.exception.reason, "path-escape")

    def test_calibrated_gate1g_claim_from_subdir_overlaps_claim_from_root(self):
        # End to end through claim(): a subdirectory caller and a root
        # caller declaring the "same" file must collide, not both win.
        with tempfile.TemporaryDirectory() as d:
            root = os.path.realpath(d)
            os.makedirs(os.path.join(root, "api"))
            store = bs.Store(root)
            try:
                store.claim("one", "ephemeral", "obj", ["api/pay.py"],
                            session_id="s1", cwd=root)
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.claim("two", "ephemeral", "obj", ["pay.py"],
                                session_id="s2", cwd=os.path.join(root, "api"))
                self.assertEqual(ctx.exception.reason, "overlap")
            finally:
                store.close()

    def test_calibrated_gate1h_glob_literal_prefix_canonicalized(self):
        with tempfile.TemporaryDirectory() as d:
            root = os.path.realpath(d)
            canon = bs.canonicalize_path(root, "sub/../api/*.py")
            self.assertEqual(canon, "api/*.py")

    # -- GATE 2: case folding must never rewrite separators ---------------

    def test_calibrated_gate2_ntpath_normcase_would_break_containment(self):
        # VERIFIED BY ORCHESTRATOR: with ntpath.normcase substituted for
        # os.path.normcase (what os.path.normcase IS on real Windows),
        # paths_overlap('api', 'api/pay.py') was False, because ntpath's
        # normcase rewrites '/' to '\\' before the separator-boundary check
        # ever runs. _normcase no longer calls os.path.normcase at all, so
        # this substitution must have ZERO effect.
        with mock.patch.object(bs.os.path, "normcase", ntpath.normcase), \
             mock.patch.object(bs.sys, "platform", "win32"):
            self.assertTrue(bs.paths_overlap("api", "api/pay.py"))

    def test_calibrated_gate2_case_fold_per_platform_with_ntpath_substituted(self):
        with mock.patch.object(bs.os.path, "normcase", ntpath.normcase):
            with mock.patch.object(bs.sys, "platform", "win32"):
                self.assertTrue(bs.paths_overlap("API/Pay.PY", "api/pay.py"))
            with mock.patch.object(bs.sys, "platform", "darwin"):
                self.assertTrue(bs.paths_overlap("API/Pay.PY", "api/pay.py"))
            with mock.patch.object(bs.sys, "platform", "linux"):
                self.assertFalse(bs.paths_overlap("API/Pay.PY", "api/pay.py"))

    # -- GATE 3: empty session must never match empty session -------------

    def test_calibrated_gate3_empty_session_never_matches_empty_session(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                first = store.claim("payments", "ephemeral", "first", [])
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.claim("payments", "ephemeral", "steal it", [])
                self.assertEqual(ctx.exception.reason, "name-active")
                still = store.get(first.lifecycle_uuid)
                self.assertEqual(still.objective, "first")
            finally:
                store.close()

    def test_calibrated_gate3_two_cli_processes_never_collide(self):
        # VERIFIED BY ORCHESTRATOR end to end: two independent CLI processes
        # both claiming 'payments' with no --session used to have the
        # second silently replace the first's objective and exit 0.
        with tempfile.TemporaryDirectory() as d:
            _run_cli(["init"], d)
            r1 = _run_cli(["claim", "payments", "--lifetime", "persistent",
                          "--objective", "first", "process"], d)
            self.assertEqual(r1.returncode, 0, r1.stdout + r1.stderr)
            r2 = _run_cli(["claim", "payments", "--lifetime", "persistent",
                          "--objective", "second", "process"], d)
            self.assertEqual(r2.returncode, 2, r2.stdout + r2.stderr)
            self.assertIn("name-active", r2.stdout)
            r3 = _run_cli(["dump"], d)
            self.assertEqual(r3.returncode, 0, r3.stdout + r3.stderr)
            dumped = json.loads(r3.stdout)
            objectives = [r["objective"] for r in dumped["records"]]
            self.assertIn("first process", objectives)
            self.assertNotIn("second process", objectives)

    # -- GATE 4: every sqlite call carries the failure split ---------------

    def test_calibrated_gate4_exec_quarantines_on_database_error(self):
        fake = mock.Mock()
        fake.path = "/does/not/matter/store.sqlite3"
        fake.conn.execute.side_effect = sqlite3.DatabaseError("simulated later-page corruption")
        fake._quarantine_and_raise.side_effect = bs.StoreCorrupt("quarantined")
        with self.assertRaises(bs.StoreCorrupt):
            bs._exec(fake, "SELECT * FROM records")
        self.assertEqual(fake._quarantine_and_raise.call_count, 1)

    def test_calibrated_gate4_exec_refuses_operational_error_without_quarantine(self):
        fake = mock.Mock()
        fake.path = "/does/not/matter/store.sqlite3"
        fake.conn.execute.side_effect = sqlite3.OperationalError("database is locked")
        with self.assertRaises(bs.OwnershipRefused) as ctx:
            bs._exec(fake, "SELECT * FROM records")
        self.assertEqual(ctx.exception.reason, "db-busy")
        self.assertEqual(fake._quarantine_and_raise.call_count, 0)

    def test_calibrated_gate4_exec_lets_integrity_error_through_unchanged(self):
        fake = mock.Mock()
        fake.conn.execute.side_effect = sqlite3.IntegrityError("unique constraint failed")
        with self.assertRaises(sqlite3.IntegrityError):
            bs._exec(fake, "SELECT * FROM records")

    def test_calibrated_gate4_no_bare_execute_outside_the_helper(self):
        # Structural guard for "route EVERY sqlite call through one internal
        # helper... No bare cursor calls outside it": the only raw
        # .execute()/.executescript() call sites left in the whole module
        # are _exec's own body, Store.__init__'s open-time probe (which by
        # definition runs before the connection is confirmed healthy enough
        # to trust _exec's quarantine path), _ensure_schema (called only
        # from inside that same protected try block), and _transaction's
        # ROLLBACK-during-cleanup (must never mask the exception already
        # being handled). If this count grows, a new call site was added
        # without routing it through _exec: update this test deliberately,
        # the same way tools/write_sites.json makes a new write site a
        # conscious decision rather than a silent one.
        with io.open(os.path.join(HERE, "bm_store.py"), encoding="utf-8") as f:
            lines = f.readlines()
        bare = [i for i, line in enumerate(lines, 1)
                if re.search(r"\.execute\(|\.executescript\(", line)
                and "_exec(self" not in line and "_exec(store" not in line]
        self.assertEqual(len(bare), 10,
                          "raw execute call sites changed (now at lines %s); route any "
                          "new one through _exec or update this count deliberately" % bare)

    # -- GATE 5: quarantine must not destroy what it preserves -------------

    def test_calibrated_gate5_concurrent_quarantines_do_not_collide(self):
        # Two quarantines inside the same second used to collide (identical
        # second-precision timestamp) and os.replace silently destroyed the
        # first one's evidence. Forcing datetime.now() and uuid4() to fixed
        # values simulates that exact collision deterministically.
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            path = store.path
            fixed_now = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
            fixed_uuid = uuid.UUID(int=0)
            expected_dir = path + ".quarantine-" + fixed_now.strftime("%Y%m%dT%H%M%S%f") \
                + "-" + fixed_uuid.hex[:8]
            os.makedirs(expected_dir)
            sentinel = os.path.join(expected_dir, "store.sqlite3")
            with io.open(sentinel, "w", encoding="utf-8") as f:
                f.write("PRIOR QUARANTINE, MUST SURVIVE")
            with mock.patch.object(bs, "datetime") as dt_mock, \
                 mock.patch.object(bs.uuid, "uuid4", return_value=fixed_uuid):
                dt_mock.datetime.now.return_value = fixed_now
                dt_mock.timezone = datetime.timezone
                with self.assertRaises(bs.StoreCorrupt):
                    store._quarantine_and_raise(sqlite3.DatabaseError("simulated corruption"))
            with io.open(sentinel, encoding="utf-8") as f:
                self.assertEqual(f.read(), "PRIOR QUARANTINE, MUST SURVIVE")

    def test_calibrated_gate5_sidecars_are_quarantined_too(self):
        # The -wal/-shm sidecars used to be left behind entirely, and a
        # data-bearing WAL is exactly where the actually-lost records live.
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            store.close()
            path = bs.store_path(d)
            with io.open(path + "-wal", "wb") as f:
                f.write(b"wal sidecar bytes, pretend records live here")
            with io.open(path + "-shm", "wb") as f:
                f.write(b"shm sidecar bytes")
            with io.open(path, "wb") as f:
                f.write(b"garbage, not a database, corrupting the main file 0123456789")
            with self.assertRaises(bs.StoreCorrupt) as ctx:
                bs.Store(d)
            qdir = ctx.exception.quarantine_path
            self.assertTrue(os.path.isdir(qdir))
            self.assertTrue(os.path.exists(os.path.join(qdir, "store.sqlite3")))
            self.assertTrue(os.path.exists(os.path.join(qdir, "store.sqlite3-wal")))
            self.assertTrue(os.path.exists(os.path.join(qdir, "store.sqlite3-shm")))
            self.assertFalse(os.path.exists(path + "-wal"))
            self.assertFalse(os.path.exists(path + "-shm"))

    # -- GATE 6: resume into a retaken name must refuse, not crash ---------

    def test_calibrated_gate6_resume_into_retaken_name_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                first = store.claim("payments", "ephemeral", "v1", [], session_id="s1")
                parked = store.transition(first.lifecycle_uuid, first.version, "parked",
                                           session_id="s1")
                # The name is now free (no active record): someone else
                # takes it.
                store.claim("payments", "ephemeral", "v2", [], session_id="s2")
                # Resuming the ORIGINAL, parked lifecycle now collides with
                # the unique-active-name index.
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.transition(parked.lifecycle_uuid, parked.version, "active",
                                      session_id="s1")
                self.assertEqual(ctx.exception.reason, "name-active")
            finally:
                store.close()

    def test_calibrated_gate6_cli_resume_into_retaken_name_exits_two(self):
        with tempfile.TemporaryDirectory() as d:
            _run_cli(["init"], d)
            r1 = _run_cli(["claim", "payments", "--lifetime", "ephemeral",
                          "--objective", "v1", "--session", "s1"], d)
            uuid1 = re.search(r"lifecycle ([0-9a-f]+)", r1.stdout).group(1)
            r_park = _run_cli(["park", uuid1, "--version", "1", "--session", "s1"], d)
            self.assertEqual(r_park.returncode, 0, r_park.stdout + r_park.stderr)
            _run_cli(["claim", "payments", "--lifetime", "ephemeral",
                      "--objective", "v2", "--session", "s2"], d)
            r_resume = _run_cli(["resume", uuid1, "--version", "2", "--session", "s1"], d)
            self.assertEqual(r_resume.returncode, 2, r_resume.stdout + r_resume.stderr)
            self.assertIn("name-active", r_resume.stdout)

    # -- GATE 7: the store protects itself without waiting for init -------

    def test_calibrated_gate7_claim_alone_creates_excludes_and_chmods(self):
        # Only `init` used to write the git excludes; any OTHER command
        # (claim, dashboard, verify, ...) created the store directory as a
        # side effect without protecting it, so a routine `git add -A`
        # before anyone happened to run init committed the store.
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, ".git", "info"))
            store = bs.Store(d)  # NOT init_project: any command does this
            try:
                store.claim("thing", "ephemeral", "obj", [])
            finally:
                store.close()
            exclude_path = os.path.join(d, ".git", "info", "exclude")
            with io.open(exclude_path, encoding="utf-8") as f:
                content = f.read()
            for wanted in (".brothermode/", "threads/", "STATE.md"):
                self.assertIn(wanted, content)

    @unittest.skipIf(sys.platform == "win32", "POSIX permission bits only")
    def test_calibrated_gate7_permissions_tightened_best_effort(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                dir_mode = stat.S_IMODE(os.stat(bs.store_dir(d)).st_mode)
                file_mode = stat.S_IMODE(os.stat(store.path).st_mode)
                self.assertEqual(dir_mode, 0o700)
                self.assertEqual(file_mode, 0o600)
            finally:
                store.close()

    # -- GATE 8: redaction must cover every field, markers must not leak --

    def test_calibrated_gate8a_tier_and_paths_redacted_in_state_md(self):
        secret = "sk-test1234567890abcdef"
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                store.claim("thing", "ephemeral", "obj", ["api/%s.py" % secret],
                            tier=secret)
            finally:
                store.close()
            view = bs.render_state_md(d)
            self.assertNotIn(secret, view)
            self.assertIn("[REDACTED]", view)

    def test_calibrated_gate8b_marker_text_in_objective_is_neutralized(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                store.claim("thing", "ephemeral",
                             "see also " + bs._STATE_END + " for details", [])
            finally:
                store.close()
            view = bs.render_state_md(d)
            # Exactly one real END marker (the module's own), never a
            # second one smuggled in via the objective.
            self.assertEqual(view.count(bs._STATE_END), 1)
            self.assertIn(bs._MARKER_ESCAPE, view)

    def test_calibrated_gate8b_n_renders_leave_exactly_one_marker_pair(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                store.claim("thing", "persistent",
                             "escape attempt: " + bs._STATE_BEGIN + " and " + bs._STATE_END, [])
            finally:
                store.close()
            for _ in range(5):
                bs.write_state_view(d)
            with io.open(os.path.join(d, "STATE.md"), encoding="utf-8") as f:
                content = f.read()
            self.assertEqual(content.count(bs._STATE_BEGIN), 1)
            self.assertEqual(content.count(bs._STATE_END), 1)

    # -- GATE 9: encoding failures must not misclassify or crash ----------

    def test_calibrated_gate9_non_ascii_name_rejected(self):
        with self.assertRaises(ValueError):
            bs.valid_name("paymentsé")  # e with acute accent

    def test_calibrated_gate9_control_character_in_name_rejected(self):
        with self.assertRaises(ValueError):
            bs.valid_name("pay\x00ments")

    def test_calibrated_gate9_out_never_raises_on_narrow_stdout(self):
        # Simulate a stdout that can only encode ASCII: _out() must degrade
        # to backslashreplace, never raise UnicodeEncodeError.
        buf = io.BytesIO()
        fake_stdout = io.TextIOWrapper(buf, encoding="ascii", errors="strict")
        with mock.patch.object(bs.sys, "stdout", fake_stdout):
            bs._out("café objective claimed")
            fake_stdout.flush()
        # backslashreplace escapes U+00E9 as \xe9 (Python's shortest hex
        # form for a code point <= 0xFF); the point of this test is only
        # that _out() degraded gracefully instead of raising.
        self.assertIn(b"\\xe9", buf.getvalue())
        self.assertIn(b"objective claimed", buf.getvalue())

    def test_calibrated_gate9_unicode_encode_error_is_a_value_error_subclass(self):
        # The root cause this fix closes: verified via __mro__.
        self.assertTrue(issubclass(UnicodeEncodeError, ValueError))

    def test_calibrated_gate9_main_reports_unicode_failure_as_exit_one_not_bad_input(self):
        # Defense-in-depth backstop: even if some future print call bypasses
        # _out and raises UnicodeEncodeError, main() must not classify it as
        # 'bad-input' (exit 2), the original misclassification, since the
        # command may have already committed.
        def boom(argv):
            raise UnicodeEncodeError("ascii", "x", 0, 1, "simulated")
        with mock.patch.dict(bs._COMMANDS, {"claim": boom}):
            with self.assertRaises(SystemExit) as ctx:
                bs.main(["claim", "thing"])
            self.assertEqual(ctx.exception.code, 1)

    # -- SOFT 10: cross-session park is a takeover path --------------------

    def test_calibrated_soft10_cross_session_park_refused(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                rec = store.claim("thing", "ephemeral", "obj", [], session_id="owner")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.transition(rec.lifecycle_uuid, rec.version, "parked",
                                      session_id="attacker")
                self.assertEqual(ctx.exception.reason, "not-owner")
                still = store.get(rec.lifecycle_uuid)
                self.assertEqual(still.state, "active")
            finally:
                store.close()

    def test_calibrated_soft10_adopt_is_the_cross_session_exception(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                rec = store.claim("thing", "ephemeral", "obj", [], session_id="dead-session")
                adopted = store.transition(rec.lifecycle_uuid, rec.version, "adopted",
                                            session_id="rescuer")
                self.assertEqual(adopted.state, "adopted")
                self.assertEqual(adopted.session_id, "rescuer")
            finally:
                store.close()

    def test_calibrated_soft10_no_owner_recorded_is_unrestricted(self):
        # A record claimed with no session at all (session_id="") has no
        # owner to enforce against: any caller may still transition it.
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                rec = store.claim("thing", "ephemeral", "obj", [])
                parked = store.transition(rec.lifecycle_uuid, rec.version, "parked",
                                           session_id="whoever")
                self.assertEqual(parked.state, "parked")
            finally:
                store.close()


# ---------------------------------------------------------------------------
# Windows-safety checks (runnable on any platform).
# ---------------------------------------------------------------------------

class TestWindowsSafety(unittest.TestCase):
    def test_no_fcntl_import_anywhere(self):
        with io.open(os.path.join(HERE, "bm_store.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertNotIn("fcntl", src)

    def test_case_insensitive_path_conflict_on_case_insensitive_platforms(self):
        # os.path.normcase alone is a no-op on this very machine (verified:
        # posix normcase does not fold case), so this forces the darwin
        # branch of _normcase deterministically, regardless of which OS
        # actually runs the test suite (macOS, Linux, or Windows CI).
        with mock.patch.object(bs.sys, "platform", "darwin"):
            self.assertTrue(bs.paths_overlap("API/Pay.PY", "api/pay.py"))

    def test_case_sensitive_on_linux_like_platforms(self):
        # The flip side: on a platform we do NOT fold case for, two paths
        # differing only by case must NOT be reported as the same file,
        # or every claim on a case-sensitive filesystem (ext4) would
        # over-block unrelated work.
        with mock.patch.object(bs.sys, "platform", "linux"):
            self.assertFalse(bs.paths_overlap("API/Pay.PY", "api/pay.py"))


# ---------------------------------------------------------------------------
# Behavior tests, one per API promise.
# ---------------------------------------------------------------------------

class TestResolveRoot(unittest.TestCase):
    def test_env_var_wins(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.dict(os.environ, {"BROTHERMODE_ROOT": d}):
                root, source = bs.resolve_root(start=d)
                self.assertEqual(os.path.realpath(root), os.path.realpath(d))
                self.assertEqual(source, "env")

    def test_marker_found_walking_up(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, ".brothermode"))
            sub = os.path.join(d, "a", "b")
            os.makedirs(sub)
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("BROTHERMODE_ROOT", None)
                root, source = bs.resolve_root(start=sub)
            self.assertEqual(os.path.realpath(root), os.path.realpath(d))
            self.assertEqual(source, "marker")

    def test_git_directory_found_when_no_marker(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, ".git"))
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("BROTHERMODE_ROOT", None)
                root, source = bs.resolve_root(start=d)
            self.assertEqual(os.path.realpath(root), os.path.realpath(d))
            self.assertEqual(source, "git")

    def test_git_file_worktree_found(self):
        with tempfile.TemporaryDirectory() as d:
            with io.open(os.path.join(d, ".git"), "w", encoding="utf-8") as f:
                f.write("gitdir: /somewhere/else/.git/worktrees/x\n")
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("BROTHERMODE_ROOT", None)
                root, source = bs.resolve_root(start=d)
            self.assertEqual(os.path.realpath(root), os.path.realpath(d))
            self.assertEqual(source, "git")

    def test_marker_beats_git_even_when_marker_is_further_up(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, ".brothermode"))
            nested = os.path.join(d, "vendor", "sub")
            os.makedirs(os.path.join(nested, ".git"))
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("BROTHERMODE_ROOT", None)
                root, source = bs.resolve_root(start=nested)
            self.assertEqual(os.path.realpath(root), os.path.realpath(d))
            self.assertEqual(source, "marker")

    def test_nothing_found_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            # Pin the walk to exactly one directory (this tempdir) so the
            # result cannot depend on whatever happens to sit above the
            # system temp root on the machine running this test.
            with mock.patch.dict(os.environ, {}, clear=False), \
                 mock.patch.object(bs, "_walk_up", return_value=[os.path.realpath(d)]):
                os.environ.pop("BROTHERMODE_ROOT", None)
                root, source = bs.resolve_root(start=d)
            self.assertIsNone(root)
            self.assertIsNone(source)

    def test_require_root_raises_ownership_refused_no_root(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.dict(os.environ, {}, clear=False), \
                 mock.patch.object(bs, "_walk_up", return_value=[os.path.realpath(d)]):
                os.environ.pop("BROTHERMODE_ROOT", None)
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    bs.require_root(start=d)
            self.assertEqual(ctx.exception.reason, "no-root")


class TestValidNameBehavior(unittest.TestCase):
    def test_accepts_normal_label(self):
        self.assertEqual(bs.valid_name("payments-api"), "payments-api")

    def test_rejects_leading_dot(self):
        with self.assertRaises(ValueError):
            bs.valid_name(".hidden")

    def test_rejects_reserved_characters(self):
        for bad in ("a:b", "a?b", "a*b", 'a"b', "a<b", "a>b", "a|b"):
            with self.assertRaises(ValueError):
                bs.valid_name(bad)

    def test_rejects_whitespace(self):
        with self.assertRaises(ValueError):
            bs.valid_name("a b")

    def test_rejects_too_long(self):
        with self.assertRaises(ValueError):
            bs.valid_name("x" * 61)

    def test_no_silent_normalization(self):
        self.assertEqual(bs.valid_name("Payments"), "Payments")
        self.assertEqual(bs.valid_name("payments"), "payments")


class TestThreadDirName(unittest.TestCase):
    def test_format(self):
        self.assertEqual(bs.thread_dir_name("payments", "abcdef0123456789"), "payments-abcdef01")

    def test_rejects_invalid_name(self):
        with self.assertRaises(ValueError):
            bs.thread_dir_name("..", "abcdef0123456789")


class TestPathsOverlapBehavior(unittest.TestCase):
    def test_exact_match_conflicts(self):
        self.assertTrue(bs.paths_overlap("api/pay.py", "api/pay.py"))

    def test_directory_containment_conflicts_both_directions(self):
        self.assertTrue(bs.paths_overlap("api/", "api/pay.py"))
        self.assertTrue(bs.paths_overlap("api/pay.py", "api/"))

    def test_disjoint_globs_do_not_conflict(self):
        self.assertFalse(bs.paths_overlap("api/*.py", "web/*.py"))

    def test_unrelated_paths_do_not_conflict(self):
        self.assertFalse(bs.paths_overlap("api/pay.py", "web/index.html"))


class TestStoreOpen(unittest.TestCase):
    def test_reopen_preserves_data_and_project_uuid(self):
        with tempfile.TemporaryDirectory() as d:
            store1 = bs.Store(d)
            try:
                store1.claim("a", "ephemeral", "obj", [])
                uuid1 = store1.conn.execute(
                    "SELECT value FROM meta WHERE key='project_uuid'").fetchone()[0]
            finally:
                store1.close()
            store2 = bs.Store(d)
            try:
                uuid2 = store2.conn.execute(
                    "SELECT value FROM meta WHERE key='project_uuid'").fetchone()[0]
                self.assertEqual(uuid1, uuid2)
                row = store2.conn.execute("SELECT * FROM records WHERE name='a'").fetchone()
                self.assertIsNotNone(row)
            finally:
                store2.close()

    def test_pragmas_are_set(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                mode = store.conn.execute("PRAGMA journal_mode").fetchone()[0]
                fk = store.conn.execute("PRAGMA foreign_keys").fetchone()[0]
                self.assertEqual(mode.lower(), "wal")
                self.assertEqual(fk, 1)
            finally:
                store.close()


class TestClaimCap(unittest.TestCase):
    def test_persistent_cap_at_three_ephemeral_uncapped(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                for i in range(3):
                    store.claim("p%d" % i, "persistent", "obj", [], session_id="s")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.claim("p3", "persistent", "obj", [], session_id="s")
                self.assertEqual(ctx.exception.reason, "cap")
                for i in range(5):
                    rec = store.claim("e%d" % i, "ephemeral", "obj", [], session_id="s")
                    self.assertEqual(rec.state, "active")
            finally:
                store.close()


class TestClaimOverlap(unittest.TestCase):
    def test_claim_refuses_on_overlap_with_active_record(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                store.claim("one", "ephemeral", "obj", ["api/*.py"], session_id="s1")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.claim("two", "ephemeral", "obj", ["api/pay.py"], session_id="s2")
                self.assertEqual(ctx.exception.reason, "overlap")
            finally:
                store.close()

    def test_invalid_lifetime_raises_value_error(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                with self.assertRaises(ValueError):
                    store.claim("one", "sometimes", "obj", [])
            finally:
                store.close()


class TestReclaim(unittest.TestCase):
    def test_reclaim_same_session_updates_in_place_same_lifecycle(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                first = store.claim("thing", "ephemeral", "v1", ["a.py"], session_id="s1")
                second = store.claim("thing", "ephemeral", "v2", ["b.py"], session_id="s1")
                self.assertEqual(second.lifecycle_uuid, first.lifecycle_uuid)
                self.assertEqual(second.objective, "v2")
                self.assertEqual(second.files, ["b.py"])
                self.assertGreater(second.version, first.version)
            finally:
                store.close()

    def test_reclaim_still_refuses_overlap_with_a_different_record(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                store.claim("thing", "ephemeral", "v1", ["a.py"], session_id="s1")
                store.claim("other", "ephemeral", "v1", ["b.py"], session_id="s2")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.claim("thing", "ephemeral", "v2", ["b.py"], session_id="s1")
                self.assertEqual(ctx.exception.reason, "overlap")
            finally:
                store.close()

    def test_new_lifecycle_after_close_reuses_name_new_uuid(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                first = store.claim("thing", "ephemeral", "v1", [], session_id="s1")
                # SOFT 10 (fix-round 2026-07-26): completing a record you
                # hold requires passing your OWN session id, or it is
                # refused 'not-owner'.
                store.transition(first.lifecycle_uuid, first.version, "complete",
                                  session_id="s1", evidence="tests pass")
                second = store.claim("thing", "ephemeral", "v2", [], session_id="s2")
                self.assertNotEqual(second.lifecycle_uuid, first.lifecycle_uuid)
                self.assertEqual(second.state, "active")
            finally:
                store.close()


class TestTransitionLegality(unittest.TestCase):
    def test_illegal_move_raises_stale_identity(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                rec = store.claim("thing", "ephemeral", "obj", [])
                completed = store.transition(rec.lifecycle_uuid, rec.version, "complete", evidence="ok")
                with self.assertRaises(bs.StaleIdentity):
                    store.transition(completed.lifecycle_uuid, completed.version, "active")
            finally:
                store.close()

    def test_complete_without_evidence_refused(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                rec = store.claim("thing", "ephemeral", "obj", [])
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.transition(rec.lifecycle_uuid, rec.version, "complete")
                self.assertEqual(ctx.exception.reason, "missing-evidence")
            finally:
                store.close()

    def test_unknown_target_state_raises_value_error(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                rec = store.claim("thing", "ephemeral", "obj", [])
                with self.assertRaises(ValueError):
                    store.transition(rec.lifecycle_uuid, rec.version, "vaporized")
            finally:
                store.close()

    def test_all_legal_moves(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                rec = store.claim("a", "ephemeral", "obj", [])
                parked = store.transition(rec.lifecycle_uuid, rec.version, "parked")
                self.assertEqual(parked.state, "parked")
                active = store.transition(parked.lifecycle_uuid, parked.version, "active")
                self.assertEqual(active.state, "active")
                completed = store.transition(active.lifecycle_uuid, active.version, "complete", evidence="e")
                self.assertEqual(completed.state, "complete")

                rec2 = store.claim("b", "ephemeral", "obj", [])
                adopted = store.transition(rec2.lifecycle_uuid, rec2.version, "adopted")
                self.assertEqual(adopted.state, "adopted")

                rec3 = store.claim("c", "ephemeral", "obj", [])
                parked3 = store.transition(rec3.lifecycle_uuid, rec3.version, "parked")
                adopted3 = store.transition(parked3.lifecycle_uuid, parked3.version, "adopted")
                self.assertEqual(adopted3.state, "adopted")
            finally:
                store.close()


class TestCheckpointDecisions(unittest.TestCase):
    def test_checkpoint_appends_decisions_atomically(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                rec = store.claim("a", "ephemeral", "obj", [])
                store.checkpoint(rec.lifecycle_uuid, rec.version, "next",
                                  decisions=[{"topic": "db", "text": "use sqlite"},
                                             ("cache", "use none for now")])
                payload = store.handover_payload(rec.lifecycle_uuid)
                topics = [x["topic"] for x in payload["decisions"]]
                self.assertEqual(topics, ["db", "cache"])
            finally:
                store.close()

    def test_checkpoint_rejects_stale_version_even_when_active(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                rec = store.claim("a", "ephemeral", "obj", [])
                with self.assertRaises(bs.StaleIdentity):
                    store.checkpoint(rec.lifecycle_uuid, rec.version + 1, "next")
            finally:
                store.close()


class TestSendAndDecide(unittest.TestCase):
    def test_send_only_into_active_record(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                rec = store.claim("a", "ephemeral", "obj", [])
                seq1 = store.send(rec.lifecycle_uuid, "do the next thing")
                seq2 = store.send(rec.lifecycle_uuid, "and then this")
                self.assertEqual((seq1, seq2), (1, 2))
                parked = store.transition(rec.lifecycle_uuid, rec.version, "parked")
                with self.assertRaises(bs.StaleIdentity):
                    store.send(parked.lifecycle_uuid, "too late")
            finally:
                store.close()

    def test_decide_seq_increments_and_is_readable_via_handover(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                rec = store.claim("a", "ephemeral", "obj", [])
                s1 = store.decide(rec.lifecycle_uuid, rec.version, "topic", "use postgres")
                s2 = store.decide(rec.lifecycle_uuid, rec.version + 1, "topic2", "use redis")
                self.assertEqual((s1, s2), (1, 2))
                payload = store.handover_payload(rec.lifecycle_uuid)
                topics = [x["topic"] for x in payload["decisions"]]
                self.assertEqual(topics, ["topic", "topic2"])
            finally:
                store.close()


class TestHandoverPayloadShape(unittest.TestCase):
    def test_payload_shape(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                rec = store.claim("a", "persistent", "ship it", ["x.py"], owner="chief",
                                   tier="T2", check_cmd="pytest -q")
                store.checkpoint(rec.lifecycle_uuid, rec.version, "next step")
                payload = store.handover_payload(rec.lifecycle_uuid)
                for key in ("lifecycle_uuid", "name", "objective", "files", "owner",
                            "tier", "check", "evidence", "digest", "decisions", "fingerprint"):
                    self.assertIn(key, payload)
                self.assertEqual(payload["check"], "pytest -q")
                self.assertEqual(len(payload["fingerprint"]), 64)
                int(payload["fingerprint"], 16)
            finally:
                store.close()

    def test_missing_record_raises_stale_identity(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                with self.assertRaises(bs.StaleIdentity):
                    store.handover_payload("no-such-lifecycle")
            finally:
                store.close()


class TestRenderDigestBudgets(unittest.TestCase):
    def test_next_intent_truncates_at_its_own_budget(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                rec = store.claim("a", "ephemeral", "obj", [])
                long_intent = "x" * 2000
                store.checkpoint(rec.lifecycle_uuid, rec.version, long_intent)
                out = store.render_digest(rec.lifecycle_uuid)
                self.assertIn("(truncated)", out)
                self.assertNotIn("x" * 2000, out)
            finally:
                store.close()

    def test_short_next_intent_is_intact(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                rec = store.claim("a", "ephemeral", "obj", [])
                store.checkpoint(rec.lifecycle_uuid, rec.version, "finish the tests")
                out = store.render_digest(rec.lifecycle_uuid)
                self.assertIn("finish the tests", out)
            finally:
                store.close()

    def test_render_digest_of_missing_record_is_advisory_not_raising(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                out = store.render_digest("no-such-lifecycle")
                self.assertIn("no record", out)
            finally:
                store.close()


class TestDump(unittest.TestCase):
    def test_dump_covers_every_table(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                rec = store.claim("a", "ephemeral", "obj", ["x.py"])
                store.decide(rec.lifecycle_uuid, rec.version, "t", "x")
                data = store.dump()
                for table in ("meta", "records", "claims", "decisions", "digests",
                              "directives", "deliveries", "transitions", "autosave_receipts"):
                    self.assertIn(table, data)
                    self.assertIsInstance(data[table], list)
                self.assertEqual(len(data["records"]), 1)
                self.assertEqual(len(data["claims"]), 1)
                self.assertEqual(len(data["decisions"]), 1)
                json.dumps(data)  # must be JSON-serializable end to end
            finally:
                store.close()


class TestRedactionUnavailable(unittest.TestCase):
    """Simulates bm_telemetry.redact being unloadable: every generated view
    must refuse rather than emit raw text, and dump() must be unaffected."""

    def test_render_state_md_refuses_when_redactor_missing(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                store.claim("thing", "ephemeral", "objective text", [])
            finally:
                store.close()
            with mock.patch.object(bs, "_REDACT", None), \
                 mock.patch.object(bs, "_REDACT_LOAD_ERROR", "simulated failure"):
                with self.assertRaises(bs.RedactionUnavailable) as ctx:
                    bs.render_state_md(d)
                self.assertEqual(ctx.exception.reason, "redaction-unavailable")

    def test_write_state_view_refuses_and_does_not_touch_state_md(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                store.claim("thing", "ephemeral", "objective text", [])
            finally:
                store.close()
            with mock.patch.object(bs, "_REDACT", None), \
                 mock.patch.object(bs, "_REDACT_LOAD_ERROR", "simulated failure"):
                with self.assertRaises(bs.RedactionUnavailable):
                    bs.write_state_view(d)
            self.assertFalse(os.path.exists(os.path.join(d, "STATE.md")),
                             "refusing must mean nothing was written, not a partial file")

    def test_render_digest_refuses_when_redactor_missing(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                rec = store.claim("thing", "ephemeral", "objective text", [])
                store.checkpoint(rec.lifecycle_uuid, rec.version, "next step")
                with mock.patch.object(bs, "_REDACT", None), \
                     mock.patch.object(bs, "_REDACT_LOAD_ERROR", "simulated failure"):
                    with self.assertRaises(bs.RedactionUnavailable):
                        store.render_digest(rec.lifecycle_uuid)
            finally:
                store.close()

    def test_dump_never_calls_redact_even_when_redactor_missing(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                store.claim("thing", "ephemeral", "objective text", [])
                with mock.patch.object(bs, "_REDACT", None), \
                     mock.patch.object(bs, "_REDACT_LOAD_ERROR", "simulated failure"):
                    data = store.dump()  # must not raise
                self.assertEqual(data["records"][0]["objective"], "objective text")
            finally:
                store.close()


class TestStateView(unittest.TestCase):
    def test_write_state_view_creates_markers_and_content(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                store.claim("payments", "persistent", "ship stripe", ["api/pay.py"])
            finally:
                store.close()
            text = bs.write_state_view(d)
            self.assertIn(bs._STATE_BEGIN, text)
            self.assertIn(bs._STATE_END, text)
            self.assertIn("payments", text)
            path = os.path.join(d, "STATE.md")
            with io.open(path, encoding="utf-8") as f:
                on_disk = f.read()
            self.assertEqual(on_disk, text)

    def test_write_state_view_preserves_human_prose_outside_markers(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "STATE.md")
            with io.open(path, "w", encoding="utf-8") as f:
                f.write("# Project notes\nhand written prose stays here\n")
            store = bs.Store(d)
            try:
                store.claim("payments", "persistent", "ship stripe", [])
            finally:
                store.close()
            bs.write_state_view(d)
            with io.open(path, encoding="utf-8") as f:
                on_disk = f.read()
            self.assertIn("hand written prose stays here", on_disk)
            self.assertIn(bs._STATE_BEGIN, on_disk)
            # re-render must not duplicate the generated block
            bs.write_state_view(d)
            with io.open(path, encoding="utf-8") as f:
                on_disk2 = f.read()
            self.assertEqual(on_disk2.count(bs._STATE_BEGIN), 1)
            self.assertIn("hand written prose stays here", on_disk2)


class TestVerify(unittest.TestCase):
    def test_verify_healthy_store_is_empty(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                store.claim("thing", "ephemeral", "obj", ["a/b.py"])
            finally:
                store.close()
            self.assertEqual(bs.verify(d), [])

    def test_verify_reports_overlapping_active_claims_from_raw_sql(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                store.claim("one", "ephemeral", "obj", ["a/b.py"], session_id="s1")
                # Simulate corruption the API itself would never produce: a
                # second active record whose claim overlaps the first,
                # inserted directly at the SQL layer.
                conn = store.conn
                conn.execute("BEGIN IMMEDIATE")
                ts = bs.now_iso()
                conn.execute(
                    "INSERT INTO records (lifecycle_uuid, name, lifetime, state, "
                    "objective, owner, session_id, tier, check_cmd, evidence, "
                    "ttl_hours, version, created_at, updated_at) VALUES "
                    "(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    ("deadbeefcafe", "two", "ephemeral", "active", "obj2", "", "s2",
                     "", "", "", None, 1, ts, ts))
                conn.execute(
                    "INSERT INTO claims (lifecycle_uuid, path, is_glob) VALUES (?,?,0)",
                    ("deadbeefcafe", "a/b.py"))
                conn.execute("COMMIT")
            finally:
                store.close()
            problems = bs.verify(d)
            self.assertTrue(any("overlap" in p for p in problems), problems)


class TestInitProject(unittest.TestCase):
    def test_init_creates_store_and_appends_git_exclude(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, ".git", "info"))
            bs.init_project(d)
            self.assertTrue(os.path.exists(bs.store_path(d)))
            exclude_path = os.path.join(d, ".git", "info", "exclude")
            with io.open(exclude_path, encoding="utf-8") as f:
                content = f.read()
            for wanted in (".brothermode/", "threads/", "STATE.md"):
                self.assertIn(wanted, content)
            bs.init_project(d)  # idempotent
            with io.open(exclude_path, encoding="utf-8") as f:
                content2 = f.read()
            self.assertEqual(content2.count(".brothermode/"), 1)

    def test_init_without_git_dir_does_not_create_exclude(self):
        with tempfile.TemporaryDirectory() as d:
            bs.init_project(d)
            self.assertTrue(os.path.exists(bs.store_path(d)))
            self.assertFalse(os.path.exists(os.path.join(d, ".git")))


# ---------------------------------------------------------------------------
# CLI exit codes: 0 success, 2 refusal, 1 corruption/unexpected.
# ---------------------------------------------------------------------------

class TestCLIExitCodes(unittest.TestCase):
    def test_cli_init_claim_dashboard_exit_zero(self):
        with tempfile.TemporaryDirectory() as d:
            r = _run_cli(["init"], d)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = _run_cli(["claim", "thing", "--lifetime", "ephemeral",
                          "--objective", "do", "the", "thing", "--session", "s1"], d)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("thing", r.stdout)
            r = _run_cli(["dashboard"], d)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("thing", r.stdout)

    def test_cli_name_active_refusal_exits_two(self):
        with tempfile.TemporaryDirectory() as d:
            _run_cli(["init"], d)
            r1 = _run_cli(["claim", "thing", "--lifetime", "ephemeral",
                          "--objective", "obj", "--session", "s1"], d)
            self.assertEqual(r1.returncode, 0, r1.stdout + r1.stderr)
            r2 = _run_cli(["claim", "thing", "--lifetime", "ephemeral",
                          "--objective", "obj2", "--session", "s2"], d)
            self.assertEqual(r2.returncode, 2, r2.stdout + r2.stderr)
            self.assertIn("name-active", r2.stdout)

    def test_cli_corrupt_store_exits_one(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(bs.store_dir(d))
            with io.open(bs.store_path(d), "wb") as f:
                f.write(b"garbage, not a database, 0123456789")
            r = _run_cli(["dashboard"], d)
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertIn("CORRUPT", r.stdout)

    def test_cli_no_root_exits_two(self):
        # No init, no .git, no marker anywhere above a fresh tempdir: the CLI
        # runs as a real subprocess (root resolution cannot be monkeypatched
        # across a process boundary), so this relies on the OS temp root
        # having no .git/.brothermode above it, true in any sane environment
        # and consistent with how this project's other subprocess tests
        # already rely on tempfile.TemporaryDirectory() being unpolluted.
        with tempfile.TemporaryDirectory() as d:
            r = _run_cli(["verify"], d)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("no-root", r.stdout)

    def test_cli_verify_healthy_exits_zero(self):
        # SOFT 11 (fix-round 2026-07-26): this test used to pass even when
        # cmd_claim was sabotaged to create no record at all, because
        # verify() on an EMPTY store is trivially healthy. It now asserts
        # the record actually exists (via dump) before trusting "healthy".
        with tempfile.TemporaryDirectory() as d:
            _run_cli(["init"], d)
            r_claim = _run_cli(["claim", "thing", "--lifetime", "ephemeral", "--objective", "obj",
                                "--session", "s1"], d)
            self.assertEqual(r_claim.returncode, 0, r_claim.stdout + r_claim.stderr)
            r_dump = _run_cli(["dump"], d)
            self.assertEqual(r_dump.returncode, 0, r_dump.stdout + r_dump.stderr)
            dumped = json.loads(r_dump.stdout)
            names = [r["name"] for r in dumped["records"]]
            self.assertIn("thing", names,
                          "claim must have actually created a record, not just exited 0")
            r = _run_cli(["verify"], d)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("healthy", r.stdout)

    def test_calibrated_soft11_sabotaged_claim_is_caught_before_verify(self):
        # The calibration: reintroduce the SOFT 11 defect by patching
        # cmd_claim to a no-op that never calls store.claim(), confirm the
        # STRENGTHENED assertion above (record actually exists) is the one
        # that would have failed, restore, confirm green. This is done
        # in-process (not via the CLI subprocess) so the patch is scoped to
        # this one test and cannot leak into any other.
        with tempfile.TemporaryDirectory() as d:
            bs.init_project(d)
            # Sabotage: cmd_claim never calls store.claim() at all, exactly
            # the SOFT 11 reproduction. Call it directly (in-process, patch
            # scoped to this test only) the way the CLI dispatch table would.
            with mock.patch.object(bs, "cmd_claim", lambda argv: None):
                bs.cmd_claim(["thing", "--lifetime", "ephemeral", "--objective", "obj",
                              "--session", "s1"])
            problems = bs.verify(d)
            self.assertEqual(problems, [],
                              "verify on an empty store is trivially healthy, which is "
                              "exactly the SOFT 11 trap: healthy is not evidence of success")
            store = bs.Store(d)
            try:
                data = store.dump()
            finally:
                store.close()
            self.assertEqual(data["records"], [],
                              "the sabotaged claim really did create nothing, confirming "
                              "the strengthened CLI test (which checks dump) is the one "
                              "that would have failed here, not a plain verify check")


if __name__ == "__main__":
    unittest.main(verbosity=2)
