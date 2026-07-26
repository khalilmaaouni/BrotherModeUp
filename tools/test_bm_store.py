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
import pathlib
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

    def test_redaction_secret_hidden_in_views_and_in_dump_by_default(self):
        # CORRECTED MODEL (GATE C, fix-round 5, 2026-07-26): this test used
        # to assert dump() shows secrets raw, because round 2's own
        # instruction called dump "the documented raw export". That
        # instruction was an authoring error: the ratified design says
        # redaction applies at EVERY exit, and the design wins. dump() now
        # redacts by default; store.dump(raw=True) / CLI `dump --raw` is the
        # explicit, named escape hatch. This is a corrected model, not a
        # weakened test: the secret must still be reachable via --raw.
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
                dump_default = store.dump()
                dump_raw = store.dump(raw=True)
            finally:
                store.close()
            self.assertNotIn(secret, view)
            self.assertIn("[REDACTED]", view)
            self.assertNotIn(secret, digest)
            self.assertIn("[REDACTED]", digest)
            self.assertNotIn(secret, json.dumps(dump_default),
                              "dump() must redact by default, like every other exit")
            self.assertIn(secret, json.dumps(dump_raw),
                          "dump(raw=True) is the explicit, named escape hatch")
            r = _run_cli(["dashboard"], d)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertNotIn(secret, r.stdout)
            r_dump_default = _run_cli(["dump"], d)
            self.assertNotIn(secret, r_dump_default.stdout)
            r_dump_raw = _run_cli(["dump", "--raw"], d)
            self.assertIn(secret, r_dump_raw.stdout)


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
        # are _exec's own body; Store.__init__'s and ReadOnlyStore.__init__'s
        # open-time probes (which by definition run before the connection is
        # confirmed healthy enough to trust _exec's quarantine path);
        # _ensure_schema (called only from inside that same protected try
        # block); _transaction's ROLLBACK-during-cleanup (must never mask
        # the exception already being handled); and
        # _quarantine_record_count's standalone read of an ALREADY
        # quarantined file (fix-round 4), which is not the live store and
        # has nothing to route through. If this count grows, a new call
        # site was added without routing it through _exec: update this test
        # deliberately, the same way tools/write_sites.json makes a new
        # write site a conscious decision rather than a silent one.
        with io.open(os.path.join(HERE, "bm_store.py"), encoding="utf-8") as f:
            lines = f.readlines()
        bare = [i for i, line in enumerate(lines, 1)
                if re.search(r"\.execute\(|\.executescript\(", line)
                and "_exec(self" not in line and "_exec(store" not in line]
        self.assertEqual(len(bare), 13,
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
# Fix-round 2 (2026-07-26): claim() silently dropped a non-str file entry
# (pathlib.Path being the obvious case) and still reported success with a
# record holding no claims at all. checkpoint()'s decisions loop had the
# identical shape of bug.
# ---------------------------------------------------------------------------

class TestFixRound2SilentDrop(unittest.TestCase):
    def test_calibrated_pathlib_path_is_accepted_and_stored_as_string(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                rec = store.claim("t", "ephemeral", "obj",
                                   [pathlib.Path("api/pay.py")], session_id="s1")
                self.assertEqual(rec.files, ["api/pay.py"])
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.claim("other", "ephemeral", "obj", ["api/pay.py"],
                                session_id="s2")
                self.assertEqual(ctx.exception.reason, "overlap")
            finally:
                store.close()

    def test_calibrated_int_entry_raises_bad_path_and_creates_no_record(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.claim("t", "ephemeral", "obj", [123], session_id="s1")
                self.assertEqual(ctx.exception.reason, "bad-path")
                data = store.dump()
                self.assertEqual(data["records"], [], "the transaction must not have run at all")
            finally:
                store.close()

    def test_calibrated_none_entry_raises_bad_path_and_creates_no_record(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.claim("t", "ephemeral", "obj", [None], session_id="s1")
                self.assertEqual(ctx.exception.reason, "bad-path")
                self.assertEqual(store.dump()["records"], [])
            finally:
                store.close()

    def test_calibrated_mixed_valid_and_invalid_stores_neither_atomicity(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.claim("t", "ephemeral", "obj", ["ok.py", 123], session_id="s1")
                self.assertEqual(ctx.exception.reason, "bad-path")
                data = store.dump()
                self.assertEqual(data["records"], [])
                self.assertEqual(data["claims"], [])
                # A later, entirely separate claim on ok.py must be free:
                # nothing from the failed attempt survived.
                rec = store.claim("second", "ephemeral", "obj", ["ok.py"], session_id="s2")
                self.assertEqual(rec.files, ["ok.py"])
            finally:
                store.close()

    def test_calibrated_blank_only_files_list_raises_not_silently_empty(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.claim("t", "ephemeral", "obj", ["   ", ""], session_id="s1")
                self.assertEqual(ctx.exception.reason, "bad-path")
                self.assertEqual(store.dump()["records"], [])
            finally:
                store.close()

    def test_calibrated_non_iterable_files_raises_bad_path(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.claim("t", "ephemeral", "obj", 42, session_id="s1")
                self.assertEqual(ctx.exception.reason, "bad-path")
            finally:
                store.close()

    def test_calibrated_empty_files_list_stays_legal(self):
        # Rule: an empty list is a real, legal "no claims" record. Only a
        # NON-empty input that yields zero stored claims must raise.
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                rec = store.claim("t", "ephemeral", "obj", [], session_id="s1")
                self.assertEqual(rec.files, [])
            finally:
                store.close()

    def test_structural_coerce_path_entry_is_total(self):
        # Every input either returns a string or raises OwnershipRefused
        # 'bad-path'; nothing else (None, a silent skip, a different
        # exception type) is an acceptable outcome.
        for entry in ("plain.py", pathlib.Path("a/b.py"), 123, None, 3.14,
                      [], {}, object(), b"bytes.py", True):
            try:
                result = bs._coerce_path_entry(entry)
            except bs.OwnershipRefused as e:
                self.assertEqual(e.reason, "bad-path")
            else:
                self.assertIsInstance(result, str,
                                      "%r returned %r, neither a string nor a raise"
                                      % (entry, result))

    def test_calibrated_reinject_silent_drop_would_fail_every_test_above(self):
        # The calibration pattern: reproduce the OLD behavior (silently
        # filter to only str entries, like round 1's _normalize_files did)
        # and confirm each test above's core assertion would have failed.
        def old_normalize_files(files, root, cwd=None):
            if files is None:
                raw = []
            elif isinstance(files, str):
                raw = [files]
            else:
                try:
                    raw = [f for f in files if isinstance(f, str)]
                except TypeError:
                    raw = []
            out = []
            for f in raw:
                if not (f or "").strip():
                    continue
                canon = bs.canonicalize_path(root, f, cwd)
                out.append((canon, bs._has_glob(canon)))
            return out

        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                with mock.patch.object(bs, "_normalize_files", old_normalize_files):
                    # Path silently dropped: old code stores zero claims,
                    # not ['api/pay.py'], and raises nothing.
                    rec = store.claim("t", "ephemeral", "obj",
                                       [pathlib.Path("api/pay.py")], session_id="s1")
                    self.assertEqual(rec.files, [],
                                      "reinjected old code should have dropped the Path silently")
                    # A genuinely bad entry mixed with a good one: old code
                    # stores the good one alone instead of raising.
                    rec2 = store.claim("t2", "ephemeral", "obj", ["ok.py", 123],
                                        session_id="s2")
                    self.assertEqual(rec2.files, ["ok.py"],
                                      "reinjected old code should have silently dropped 123")
            finally:
                store.close()

    # -- the same audit, applied to checkpoint()'s decisions list ---------

    def test_calibrated_malformed_decision_raises_and_rolls_back_digest(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                rec = store.claim("t", "ephemeral", "obj", [])
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.checkpoint(rec.lifecycle_uuid, rec.version, "next",
                                      decisions=[{"topic": "ok", "text": "fine"}, "malformed"])
                self.assertEqual(ctx.exception.reason, "bad-decision")
                payload = store.handover_payload(rec.lifecycle_uuid)
                self.assertIsNone(payload["digest"],
                                  "the digest row must have rolled back with the bad decision")
                self.assertEqual(payload["decisions"], [],
                                  "the good decision must not survive a rolled-back transaction")
            finally:
                store.close()

    def test_structural_no_silent_continue_in_checkpoint_decisions_loop(self):
        # Structural guard, mirroring the canonicalizer totality test: the
        # decisions loop inside checkpoint() must never discard a malformed
        # entry via a bare "continue". Grep-level check so a future edit
        # cannot silently reintroduce the exact pre-fix shape.
        with io.open(os.path.join(HERE, "bm_store.py"), encoding="utf-8") as f:
            src = f.read()
        start = src.index("def checkpoint(self,")
        end = src.index("\n    def decide(self,")
        body = src[start:end]
        self.assertNotIn("else:\n                        continue", body,
                          "checkpoint()'s decisions loop must raise on a malformed "
                          "entry, never silently skip it")


# ---------------------------------------------------------------------------
# Fix round 3 (2026-07-26): GATE A (resume bypasses admission checks), GATE B
# (zero-length store treated as healthy), GATE C (worktree excludes never
# written), GATE D (.brothermode not symlink-checked), SOFT F (reclaim
# silently drops a lifetime change).
# ---------------------------------------------------------------------------

class TestFixRound3(unittest.TestCase):
    # -- GATE A -------------------------------------------------------

    def test_calibrated_gateA_resume_refuses_overlap_with_new_claimant(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                alpha = store.claim("alpha", "ephemeral", "obj", ["api/pay.py"],
                                     session_id="sessA")
                parked = store.transition(alpha.lifecycle_uuid, alpha.version, "parked",
                                           session_id="sessA")
                store.claim("beta", "ephemeral", "obj", ["api/pay.py"], session_id="sessB")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.transition(parked.lifecycle_uuid, parked.version, "active",
                                      session_id="sessA")
                self.assertEqual(ctx.exception.reason, "overlap")
                still = store.get(parked.lifecycle_uuid)
                self.assertEqual(still.state, "parked", "a refused resume must leave it parked")
                self.assertEqual(bs.verify(d), [],
                                  "the store must never create the overlap its own verify reports")
            finally:
                store.close()

    def test_calibrated_gateA_resume_refuses_persistent_cap(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                target = store.claim("p0", "persistent", "obj", [], session_id="s")
                parked = store.transition(target.lifecycle_uuid, target.version, "parked",
                                           session_id="s")
                for i in range(3):
                    store.claim("p%d" % (i + 1), "persistent", "obj", [], session_id="s")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.transition(parked.lifecycle_uuid, parked.version, "active",
                                      session_id="s")
                self.assertEqual(ctx.exception.reason, "cap")
            finally:
                store.close()

    def test_calibrated_gateA_cli_resume_refuses_and_verify_stays_clean(self):
        with tempfile.TemporaryDirectory() as d:
            _run_cli(["init"], d)
            r1 = _run_cli(["claim", "alpha", "--lifetime", "ephemeral",
                          "--objective", "obj", "--files", "api/pay.py",
                          "--session", "sessA"], d)
            uuid1 = re.search(r"lifecycle ([0-9a-f]+)", r1.stdout).group(1)
            _run_cli(["park", uuid1, "--version", "1", "--session", "sessA"], d)
            _run_cli(["claim", "beta", "--lifetime", "ephemeral", "--objective", "obj",
                      "--files", "api/pay.py", "--session", "sessB"], d)
            r_resume = _run_cli(["resume", uuid1, "--version", "2", "--session", "sessA"], d)
            self.assertEqual(r_resume.returncode, 2, r_resume.stdout + r_resume.stderr)
            self.assertIn("overlap", r_resume.stdout)
            r_verify = _run_cli(["verify"], d)
            self.assertEqual(r_verify.returncode, 0, r_verify.stdout + r_verify.stderr)

    def test_structural_one_admission_function_used_by_both_paths(self):
        with io.open(os.path.join(HERE, "bm_store.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertEqual(src.count("def _admit("), 1,
                          "exactly one admission function must exist")
        claim_start = src.index("def claim(self, name, lifetime")
        claim_end = src.index("\n    # -- transition")
        transition_start = src.index("def transition(self, lifecycle_uuid")
        transition_end = src.index("\n    # -- checkpoint")
        self.assertIn("self._admit(", src[claim_start:claim_end])
        self.assertIn("self._admit(", src[transition_start:transition_end])

    def test_calibrated_reinject_gateA_would_fail_above(self):
        # Reinject the pre-fix shape: resume skips admission entirely.
        def old_transition(self, lifecycle_uuid, expected_version, to_state,
                            session_id="", note="", evidence=""):
            if to_state not in bs._LEGAL_MOVES:
                raise ValueError("unknown target state %r" % (to_state,))
            if to_state == "complete" and not (evidence or "").strip():
                raise bs.OwnershipRefused("missing-evidence", "x")
            allowed_from = bs._LEGAL_MOVES[to_state]
            with self._transaction() as conn:
                row = bs._exec(self, "SELECT * FROM records WHERE lifecycle_uuid=?",
                                (lifecycle_uuid,)).fetchone()
                if row is None or row["version"] != expected_version or row["state"] not in allowed_from:
                    raise bs.StaleIdentity("stale")
                ts = bs.now_iso()
                bs._exec(self,
                    "UPDATE records SET state=?, version=version+1, updated_at=? "
                    "WHERE lifecycle_uuid=? AND version=? AND state=?",
                    (to_state, ts, lifecycle_uuid, expected_version, row["state"]))
                return self._record_by_uuid(conn, lifecycle_uuid)

        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                alpha = store.claim("alpha", "ephemeral", "obj", ["api/pay.py"],
                                     session_id="sessA")
                parked = store.transition(alpha.lifecycle_uuid, alpha.version, "parked",
                                           session_id="sessA")
                store.claim("beta", "ephemeral", "obj", ["api/pay.py"], session_id="sessB")
                with mock.patch.object(bs.Store, "transition", old_transition):
                    resumed = store.transition(parked.lifecycle_uuid, parked.version, "active",
                                                session_id="sessA")
                    self.assertEqual(resumed.state, "active",
                                      "reinjected old code must resume unchecked")
                self.assertNotEqual(bs.verify(d), [],
                                     "reinjected old code must leave the store corrupt, "
                                     "proving the fix's checks were doing real work")
            finally:
                store.close()

    # -- GATE B ---------------------------------------------------------

    def test_calibrated_gateB_zero_length_existing_store_quarantines(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            store.claim("keeper", "ephemeral", "obj", [])
            path = store.path
            store.close()
            self.assertGreater(os.path.getsize(path), 0)
            with io.open(path, "wb"):
                pass  # truncate to 0 bytes, sidecars (if any) untouched
            self.assertEqual(os.path.getsize(path), 0)
            with self.assertRaises(bs.StoreCorrupt) as ctx:
                bs.Store(d)
            qdir = ctx.exception.quarantine_path
            self.assertTrue(os.path.isdir(qdir))
            self.assertTrue(os.path.exists(os.path.join(qdir, "store.sqlite3")))
            store2 = bs.Store(d)  # fresh init after quarantine must work
            try:
                rec = store2.claim("again", "ephemeral", "obj", [])
                self.assertEqual(rec.state, "active")
            finally:
                store2.close()

    def test_first_time_creation_is_not_flagged_as_zero_length(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)  # must not raise: the file did not exist yet
            try:
                self.assertGreater(os.path.getsize(store.path), 0)
            finally:
                store.close()

    # -- GATE C: requires a real git worktree ----------------------------

    def _make_git_worktree(self, base):
        main = os.path.join(base, "main")
        wt = os.path.join(base, "wt")
        os.makedirs(main)
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t.com",
                   GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t.com")
        for cmd in (["git", "init", "-q"],
                    ["git", "commit", "-q", "--allow-empty", "-m", "init"]):
            subprocess.run(cmd, cwd=main, env=env, check=True,
                            capture_output=True)
        subprocess.run(["git", "worktree", "add", "-q", wt, "-b", "feature"],
                        cwd=main, env=env, check=True, capture_output=True)
        return wt

    def test_calibrated_gateC_worktree_excludes_written(self):
        with tempfile.TemporaryDirectory() as base:
            wt = self._make_git_worktree(base)
            self.assertTrue(os.path.isfile(os.path.join(wt, ".git")),
                             "sanity: .git must be a FILE in a worktree")
            store = bs.Store(wt)
            try:
                store.claim("thing", "ephemeral", "obj", [])
            finally:
                store.close()
            r = subprocess.run(["git", "status", "--porcelain"], cwd=wt,
                                capture_output=True, text=True)
            self.assertNotIn(".brothermode", r.stdout, r.stdout)

    def test_calibrated_reinject_gateC_would_fail_above(self):
        with tempfile.TemporaryDirectory() as base:
            wt = self._make_git_worktree(base)
            def old_ensure_git_excludes(root):
                git_dir = os.path.join(root, ".git")
                if not os.path.isdir(git_dir):
                    return
            with mock.patch.object(bs, "_ensure_git_excludes", old_ensure_git_excludes):
                store = bs.Store(wt)
                try:
                    store.claim("thing", "ephemeral", "obj", [])
                finally:
                    store.close()
            r = subprocess.run(["git", "status", "--porcelain"], cwd=wt,
                                capture_output=True, text=True)
            self.assertIn(".brothermode", r.stdout,
                          "reinjected old code must leave the store unexcluded")

    # -- GATE D -----------------------------------------------------------

    @unittest.skipIf(sys.platform == "win32", "symlinks need elevation on Windows")
    def test_calibrated_gateD_symlinked_brothermode_refused(self):
        with tempfile.TemporaryDirectory() as d:
            target = os.path.join(d, "docs")
            os.makedirs(target)
            os.symlink(target, os.path.join(d, ".brothermode"))
            with self.assertRaises(bs.OwnershipRefused) as ctx:
                bs.Store(d)
            self.assertEqual(ctx.exception.reason, "path-escape")

    @unittest.skipIf(sys.platform == "win32", "symlinks need elevation on Windows")
    def test_calibrated_gateD_symlink_target_never_chmodded(self):
        with tempfile.TemporaryDirectory() as d:
            target = os.path.join(d, "docs")
            os.makedirs(target)
            before = stat.S_IMODE(os.stat(target).st_mode)
            os.symlink(target, os.path.join(d, ".brothermode"))
            with self.assertRaises(bs.OwnershipRefused):
                bs.Store(d)
            after = stat.S_IMODE(os.stat(target).st_mode)
            self.assertEqual(before, after, "the symlink target must never be chmodded")

    # -- SOFT E -------------------------------------------------------

    def test_soft_e_render_digest_header_includes_objective(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                rec = store.claim("thing", "ephemeral", "ship the payments webhook", [])
                out = store.render_digest(rec.lifecycle_uuid)
                self.assertIn("ship the payments webhook", out)
            finally:
                store.close()

    # -- SOFT F -------------------------------------------------------

    def test_calibrated_soft_f_reclaim_with_different_lifetime_refused(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                store.claim("thing", "persistent", "obj", [], session_id="s1")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.claim("thing", "ephemeral", "obj2", [], session_id="s1")
                self.assertEqual(ctx.exception.reason, "lifetime-mismatch")
                still = store.get(store.conn.execute(
                    "SELECT lifecycle_uuid FROM records WHERE name='thing'").fetchone()[0])
                self.assertEqual(still.lifetime, "persistent")
                self.assertEqual(still.objective, "obj")
            finally:
                store.close()

    def test_calibrated_reinject_soft_f_would_fail_above(self):
        def old_claim_reclaim_check(active, lifetime):
            return False  # old code: never compared lifetime at all
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                rec = store.claim("thing", "persistent", "obj", [], session_id="s1")
                # Reproduce the exact pre-fix call site: _reclaim_active
                # invoked directly, bypassing the new lifetime check that
                # now lives in claim() just before it.
                row = store.conn.execute(
                    "SELECT * FROM records WHERE lifecycle_uuid=?",
                    (rec.lifecycle_uuid,)).fetchone()
                with store._transaction() as conn:
                    updated = store._reclaim_active(conn, row, "obj2", [], "", "", "", None)
                self.assertEqual(updated.lifetime, "persistent",
                                  "reinjected old path silently keeps the old lifetime "
                                  "while reporting a differently-requested claim as done")
            finally:
                store.close()


# ---------------------------------------------------------------------------
# Fix round 4 (2026-07-26): an honesty defect. After a truncation-quarantine,
# the next command silently created a fresh store and reported "healthy"
# seconds after total data loss; a read-only diagnostic in a fresh directory
# created the very store.sqlite3 (plus -wal/-shm) it claimed to be checking.
# ---------------------------------------------------------------------------

class TestFixRound4Honesty(unittest.TestCase):
    def test_calibrated_second_verify_after_quarantine_never_says_healthy(self):
        with tempfile.TemporaryDirectory() as d:
            _run_cli(["init"], d)
            r_claim = _run_cli(["claim", "k", "--lifetime", "persistent",
                                "--objective", "IMPORTANT WORK", "--files", "k.py"], d)
            self.assertEqual(r_claim.returncode, 0, r_claim.stdout + r_claim.stderr)
            path = bs.store_path(d)
            with io.open(path, "wb"):
                pass  # truncate to 0 bytes
            r1 = _run_cli(["verify"], d)
            self.assertEqual(r1.returncode, 1, r1.stdout + r1.stderr)
            self.assertIn("CORRUPT", r1.stdout)
            r2 = _run_cli(["verify"], d)
            self.assertNotEqual(r2.returncode, 0, r2.stdout + r2.stderr)
            self.assertNotIn("healthy", r2.stdout)
            qdirs = glob.glob(path + ".quarantine-*")
            self.assertEqual(len(qdirs), 1)
            self.assertIn(os.path.basename(qdirs[0]), r2.stdout,
                          "verify must name the quarantine directory")

    def test_calibrated_reinject_autocreate_would_report_healthy(self):
        # Reproduces the exact pre-fix shape: verify() opening a permissive,
        # auto-creating Store instead of ReadOnlyStore.
        def old_verify(root):
            store = bs.Store(root)
            try:
                return []
            finally:
                store.close()

        with tempfile.TemporaryDirectory() as d:
            _run_cli(["init"], d)
            _run_cli(["claim", "k", "--lifetime", "persistent",
                      "--objective", "obj", "--files", "k.py"], d)
            path = bs.store_path(d)
            with io.open(path, "wb"):
                pass
            with self.assertRaises(bs.StoreCorrupt):
                bs.verify(d)
            with mock.patch.object(bs, "verify", old_verify):
                problems = bs.verify(d)
            self.assertEqual(problems, [],
                              "reinjected old code reports healthy right after data loss")
            self.assertTrue(os.path.isfile(path),
                             "reinjected old code silently recreated the store")

    def _assert_fresh_dir_untouched(self, cmd):
        with tempfile.TemporaryDirectory() as d:
            before = sorted(os.listdir(d))
            self.assertEqual(before, [])
            r = _run_cli([cmd], d, env={"BROTHERMODE_ROOT": d})
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("no-store", r.stdout)
            after = sorted(os.listdir(d))
            self.assertEqual(after, [], "a read-only diagnostic must leave a fresh "
                              "directory completely untouched, found: %s" % after)

    def test_calibrated_verify_in_fresh_dir_refuses_and_touches_nothing(self):
        self._assert_fresh_dir_untouched("verify")

    def test_calibrated_dump_in_fresh_dir_refuses_and_touches_nothing(self):
        self._assert_fresh_dir_untouched("dump")

    def test_calibrated_dashboard_in_fresh_dir_refuses_and_touches_nothing(self):
        self._assert_fresh_dir_untouched("dashboard")

    def test_calibrated_reinject_autocreate_would_create_sidecars(self):
        # The exact pre-fix shape of render_state_md: opening a permissive,
        # auto-creating Store instead of ReadOnlyStore. Exercised directly
        # against the tempdir (never via require_root/cwd resolution, which
        # could otherwise resolve to this repo's own root by accident).
        def old_render_state_md(root):
            store = bs.Store(root)
            try:
                return "No records.\n"
            finally:
                store.close()

        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(os.listdir(d), [])
            old_render_state_md(d)
            self.assertTrue(os.path.isdir(os.path.join(d, ".brothermode")),
                             "reinjected old code must have created the store directory")
            self.assertTrue(os.path.isfile(bs.store_path(d)))

    def test_calibrated_claim_and_transition_also_refuse_no_store(self):
        with tempfile.TemporaryDirectory() as d:
            r1 = _run_cli(["claim", "k", "--lifetime", "ephemeral", "--objective", "obj"],
                          d, env={"BROTHERMODE_ROOT": d})
            self.assertEqual(r1.returncode, 2, r1.stdout + r1.stderr)
            self.assertIn("no-store", r1.stdout)
            self.assertEqual(os.listdir(d), [])

    def test_calibrated_init_refuses_without_acknowledge_then_succeeds_with_it(self):
        with tempfile.TemporaryDirectory() as d:
            _run_cli(["init"], d)
            _run_cli(["claim", "k", "--lifetime", "persistent", "--objective", "obj",
                      "--files", "k.py"], d)
            path = bs.store_path(d)
            with io.open(path, "wb"):
                pass
            _run_cli(["verify"], d)  # triggers the quarantine
            qdirs = glob.glob(path + ".quarantine-*")
            self.assertEqual(len(qdirs), 1)

            r_refused = _run_cli(["init"], d)
            self.assertEqual(r_refused.returncode, 2, r_refused.stdout + r_refused.stderr)
            self.assertIn("unacknowledged-quarantine", r_refused.stdout)
            self.assertTrue(os.path.isdir(qdirs[0]), "must not delete on a refused init")

            r_ack = _run_cli(["init", "--acknowledge-quarantine"], d)
            self.assertEqual(r_ack.returncode, 0, r_ack.stdout + r_ack.stderr)
            self.assertTrue(os.path.isdir(qdirs[0]),
                             "acknowledging must never delete the quarantine directory")
            self.assertTrue(os.path.isfile(os.path.join(qdirs[0], "ACKNOWLEDGED")))

            r_verify = _run_cli(["verify"], d)
            self.assertEqual(r_verify.returncode, 0, r_verify.stdout + r_verify.stderr)
            self.assertIn("healthy", r_verify.stdout)

    def test_calibrated_reinject_no_acknowledge_check_would_pass_healthy(self):
        def old_init_project_flow(root):
            return bs.init_project(root)

        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            store.claim("k", "ephemeral", "obj", [])
            store.close()
            path = store.path
            with io.open(path, "wb"):
                pass
            with self.assertRaises(bs.StoreCorrupt):
                bs.Store(d)
            qdirs = bs._find_quarantine_dirs(d)
            self.assertEqual(len(qdirs), 1)
            self.assertFalse(bs._is_quarantine_acknowledged(qdirs[0]))
            # Reinject: init_project alone (the pre-fix cmd_init body) never
            # checked for an unacknowledged quarantine at all.
            old_init_project_flow(d)
            self.assertEqual(bs._unacknowledged_quarantine_dirs(d), qdirs,
                              "reinjected old init must leave the quarantine "
                              "unacknowledged while still succeeding silently")

    def test_warning_printed_for_every_command_while_unacknowledged(self):
        with tempfile.TemporaryDirectory() as d:
            _run_cli(["init"], d)
            _run_cli(["claim", "k", "--lifetime", "ephemeral", "--objective", "obj"], d)
            path = bs.store_path(d)
            with io.open(path, "wb"):
                pass
            _run_cli(["verify"], d)  # quarantines
            r = _run_cli(["verify"], d)
            self.assertIn("WARNING", r.stdout)
            self.assertIn("quarantine", r.stdout.lower())


# ---------------------------------------------------------------------------
# Fix round 5 (2026-07-26): GATE A (reclaim without files silently empties
# the fence), GATE B (store FILE/sidecars not symlink-checked), GATE C
# (dump prints raw secrets by default, an authoring error corrected), SOFT D
# (newline injection forges STATE.md blocks), SOFT E (ANSI escapes reach the
# terminal), SOFT F (corruption message names a refused command), SOFT G
# (overlap refusals print claim paths unredacted).
# ---------------------------------------------------------------------------

class TestFixRound5(unittest.TestCase):
    # -- GATE A -----------------------------------------------------------

    def test_calibrated_gateA_reclaim_without_files_preserves_fence(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                store.claim("alpha", "ephemeral", "ship payments",
                            ["api/pay.py", "api/refund.py"], session_id="s1")
                updated = store.claim("alpha", "ephemeral", "revised objective",
                                       None, session_id="s1")
                self.assertEqual(sorted(updated.files), ["api/pay.py", "api/refund.py"])
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.claim("beta", "ephemeral", "obj", ["api/pay.py"], session_id="s2")
                self.assertEqual(ctx.exception.reason, "overlap")
            finally:
                store.close()

    def test_calibrated_gateA_explicit_empty_files_releases(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                store.claim("alpha", "ephemeral", "obj", ["api/pay.py"], session_id="s1")
                released = store.claim("alpha", "ephemeral", "obj2", [], session_id="s1")
                self.assertEqual(released.files, [])
                rec = store.claim("beta", "ephemeral", "obj", ["api/pay.py"], session_id="s2")
                self.assertEqual(rec.files, ["api/pay.py"])
            finally:
                store.close()

    def test_calibrated_gateA_cli_omitting_files_preserves_then_release_flag_works(self):
        with tempfile.TemporaryDirectory() as d:
            _run_cli(["init"], d)
            _run_cli(["claim", "alpha", "--lifetime", "ephemeral", "--objective", "obj",
                      "--session", "s1", "--files", "api/pay.py"], d)
            r_dump1 = _run_cli(["dump"], d)
            self.assertIn("api/pay.py", json.dumps(json.loads(r_dump1.stdout)["claims"]))
            r2 = _run_cli(["claim", "alpha", "--lifetime", "ephemeral",
                          "--objective", "revised", "--session", "s1"], d)
            self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)
            r_dump2 = _run_cli(["dump"], d)
            self.assertEqual(len(json.loads(r_dump2.stdout)["claims"]), 1,
                              "omitting --files must not have touched the fence")
            r3 = _run_cli(["claim", "alpha", "--lifetime", "ephemeral",
                          "--objective", "revised again", "--session", "s1",
                          "--release-files"], d)
            self.assertEqual(r3.returncode, 0, r3.stdout + r3.stderr)
            r_dump3 = _run_cli(["dump"], d)
            self.assertEqual(json.loads(r_dump3.stdout)["claims"], [])

    def test_calibrated_reinject_gateA_round5_would_fail_above(self):
        # The pre-fix shape lived in claim() itself (which files_supplied
        # value to pass into _reclaim_active), not in _normalize_files, so
        # the reinject replaces claim() with the pre-fix reclaim-only path:
        # files was ALWAYS normalized (None included), collapsing "not
        # supplied" into "supplied as empty".
        def old_claim(self, name, lifetime, objective, files, owner="", session_id="",
                      tier="", check_cmd="", ttl_hours=None, cwd=None):
            norm = bs._normalize_files(files, self.root, cwd)  # unconditional
            with self._transaction() as conn:
                active = bs._exec(self,
                    "SELECT * FROM records WHERE name=? AND state='active'", (name,)).fetchone()
                return self._reclaim_active(
                    conn, active, objective, norm, owner, tier, check_cmd, ttl_hours)

        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                store.claim("alpha", "ephemeral", "obj", ["api/pay.py"], session_id="s1")
                with mock.patch.object(bs.Store, "claim", old_claim):
                    updated = store.claim("alpha", "ephemeral", "revised",
                                           None, session_id="s1")
                self.assertEqual(updated.files, [],
                                  "reinjected old code must have emptied the fence")
            finally:
                store.close()

    # -- GATE B -------------------------------------------------------

    @unittest.skipIf(sys.platform == "win32", "symlinks need elevation on Windows")
    def test_calibrated_gateB_symlinked_store_file_refused(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, ".brothermode"))
            target_dir = os.path.join(d, "docs")
            os.makedirs(target_dir)
            leak_path = os.path.join(target_dir, "leak.sqlite3")
            with io.open(leak_path, "w"):
                pass
            os.symlink(leak_path, bs.store_path(d))
            with self.assertRaises(bs.OwnershipRefused) as ctx:
                bs.Store(d)
            self.assertEqual(ctx.exception.reason, "path-escape")
            self.assertEqual(os.path.getsize(leak_path), 0,
                              "the symlink target must never be written to")

    @unittest.skipIf(sys.platform == "win32", "symlinks need elevation on Windows")
    def test_calibrated_gateB_symlinked_sidecar_refused(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            store.close()
            outside = os.path.join(d, "..", "outside-wal")
            with io.open(outside, "w"):
                pass
            wal_path = bs.store_path(d) + "-wal"
            if os.path.exists(wal_path):
                os.remove(wal_path)
            os.symlink(os.path.realpath(outside), wal_path)
            with self.assertRaises(bs.OwnershipRefused) as ctx:
                bs.Store(d)
            self.assertEqual(ctx.exception.reason, "path-escape")

    @unittest.skipIf(sys.platform == "win32", "symlinks need elevation on Windows")
    def test_calibrated_reinject_gateB_would_fail_above(self):
        # Reinject the pre-fix shape: no symlink check on the store file at
        # all (this is exactly what the module looked like before GATE B,
        # since _refuse_if_symlink_escape did not exist until this round).
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, ".brothermode"))
            # leak_path deliberately does NOT exist yet: a dangling symlink,
            # so opening it for the first time creates a real file AT THE
            # TARGET, proving the escape (pre-creating it empty would trip
            # the unrelated zero-length-existing-file check instead).
            leak_path = os.path.join(d, "leak.sqlite3")
            os.symlink(leak_path, bs.store_path(d))
            with mock.patch.object(bs, "_refuse_if_symlink_escape", lambda p: None):
                store = bs.Store(d)
                store.claim("k", "ephemeral", "obj", [])
                store.close()
            self.assertGreater(os.path.getsize(leak_path), 0,
                              "reinjected old code must have written through the symlink")

    def test_calibrated_gateB_quarantine_target_collision_refused(self):
        # The quarantine target is safe by construction (os.makedirs
        # exist_ok=False): pre-create something at the exact path a
        # deterministic quarantine would use and confirm it is never
        # written through.
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            path = store.path
            fixed_now = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
            fixed_uuid = uuid.UUID(int=0)
            qdir = path + ".quarantine-" + fixed_now.strftime("%Y%m%dT%H%M%S%f") + "-" + fixed_uuid.hex[:8]
            os.makedirs(qdir)
            sentinel = os.path.join(qdir, "PRIOR")
            with io.open(sentinel, "w"):
                pass
            with mock.patch.object(bs, "datetime") as dt_mock, \
                 mock.patch.object(bs.uuid, "uuid4", return_value=fixed_uuid):
                dt_mock.datetime.now.return_value = fixed_now
                dt_mock.timezone = datetime.timezone
                with self.assertRaises(bs.StoreCorrupt):
                    store._quarantine_and_raise(sqlite3.DatabaseError("simulated"))
            self.assertTrue(os.path.isfile(sentinel), "must survive the collision")

    # -- GATE C -------------------------------------------------------

    def test_calibrated_gateC_dump_redacts_by_default_raw_flag_shows_secret(self):
        secret = "sk-test1234567890abcdef"
        with tempfile.TemporaryDirectory() as d:
            _run_cli(["init"], d)
            _run_cli(["claim", "thing", "--lifetime", "ephemeral",
                      "--objective", secret, "--session", "s1"], d)
            r_default = _run_cli(["dump"], d)
            self.assertNotIn(secret, r_default.stdout)
            r_raw = _run_cli(["dump", "--raw"], d)
            self.assertIn(secret, r_raw.stdout)
            self.assertIn("cleartext", r_raw.stdout.lower())

    def test_calibrated_reinject_gateC_would_fail_above(self):
        def old_dump(self, raw=False):
            out = {}
            for t in bs._TABLES:
                rows = bs._exec(self, "SELECT * FROM %s" % t).fetchall()
                out[t] = [dict(r) for r in rows]
            return out

        secret = "sk-test1234567890abcdef"
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                store.claim("thing", "ephemeral", secret, [])
                with mock.patch.object(bs.Store, "dump", old_dump):
                    data = store.dump()
                self.assertIn(secret, json.dumps(data),
                              "reinjected old code must show the secret by default")
            finally:
                store.close()

    # -- SOFT D -------------------------------------------------------

    def test_soft_d_newline_in_objective_cannot_forge_a_record_block(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                forged = ("nope\n\n## active\n- ghost (00000000, persistent) "
                          "[no tier]\n  objective: HIJACKED")
                store.claim("real", "ephemeral", forged, [])
                view = bs.render_state_md(d)
            finally:
                store.close()
            # The real safety property: no forged text can become its OWN
            # markdown line (a real, separate line is what makes a
            # counterfeit block indistinguishable from a genuine one). The
            # substring may still appear escaped, inline, within a single
            # real line, which is fine and expected.
            lines = view.splitlines()
            self.assertTrue(all(not line.startswith("- ghost") for line in lines),
                             "a newline forged a real, separate markdown line: %r" % lines)
            self.assertIn("\\x0a", view)
            self.assertEqual(bs.verify(d), [])

    # -- SOFT E -------------------------------------------------------

    def test_soft_e_ansi_escape_in_objective_is_neutralized(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                store.claim("thing", "ephemeral", "\x1b[2K\rHIJACKED: no other work exists", [])
                view = bs.render_state_md(d)
            finally:
                store.close()
            self.assertNotIn("\x1b", view)
            self.assertIn("\\x1b", view)

    def test_calibrated_reinject_soft_d_e_would_fail_above(self):
        def old_redacted_view_text(raw):
            return bs._neutralize_markers(bs.redact_text(raw))

        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                store.claim("thing", "ephemeral", "line1\nline2 \x1b[31mred\x1b[0m", [])
                with mock.patch.object(bs, "_redacted_view_text", old_redacted_view_text):
                    view = bs.render_state_md(d)
            finally:
                store.close()
            self.assertIn("\n  objective: line1\nline2 ", view.replace("\r", ""),
                          "reinjected old code must let a raw newline split the field")

    # -- SOFT F -------------------------------------------------------

    def test_soft_f_corruption_message_names_an_executable_recovery_command(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            store.claim("k", "ephemeral", "obj", [])
            path = store.path
            store.close()
            with io.open(path, "wb") as f:
                f.write(b"garbage, not a database, corrupting 0123456789")
            with self.assertRaises(bs.StoreCorrupt) as ctx:
                bs.Store(d)
            msg = str(ctx.exception)
            self.assertIn("init --acknowledge-quarantine", msg)
            self.assertNotIn("`python3 tools/bm_store.py init`", msg)
            # Prove it is executable: run exactly what the message says.
            r = _run_cli(["init", "--acknowledge-quarantine"], d)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    # -- SOFT G -------------------------------------------------------

    def test_soft_g_overlap_refusal_redacts_paths(self):
        secret_path = "api/sk-test1234567890abcdef.py"
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                store.claim("one", "ephemeral", "obj", [secret_path], session_id="s1")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.claim("two", "ephemeral", "obj", [secret_path], session_id="s2")
                self.assertNotIn(secret_path, str(ctx.exception))
                self.assertIn("[REDACTED]", str(ctx.exception))
            finally:
                store.close()

    def test_calibrated_reinject_soft_g_would_fail_above(self):
        def old_raise_overlap(self, conflict):
            other_name, other_uuid, pair = conflict
            raise bs.OwnershipRefused(
                "overlap", "claim overlaps active record '%s' (lifecycle %s): %r vs %r"
                % (other_name, other_uuid, pair[0], pair[1]),
                details={"lifecycle_uuid": other_uuid, "name": other_name, "paths": list(pair)})

        secret_path = "api/sk-test1234567890abcdef.py"
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                store.claim("one", "ephemeral", "obj", [secret_path], session_id="s1")
                with mock.patch.object(bs.Store, "_raise_overlap", old_raise_overlap):
                    with self.assertRaises(bs.OwnershipRefused) as ctx:
                        store.claim("two", "ephemeral", "obj", [secret_path], session_id="s2")
                self.assertIn(secret_path, str(ctx.exception),
                              "reinjected old code must print the raw path")
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

    def test_dump_raw_never_calls_redact_even_when_redactor_missing(self):
        # CORRECTED MODEL (GATE C, fix-round 5, 2026-07-26): this test used
        # to assert plain dump() never calls redact_text(), because round 2
        # made dump the one unredacted exit. dump() now redacts BY DEFAULT
        # like every other exit, so it MUST raise RedactionUnavailable when
        # the redactor is missing, the same as render_state_md/render_digest
        # (see the sibling test below). Only dump(raw=True), the explicit
        # escape hatch that skips redaction entirely, keeps the original
        # "never calls redact_text()" guarantee.
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                store.claim("thing", "ephemeral", "objective text", [])
                with mock.patch.object(bs, "_REDACT", None), \
                     mock.patch.object(bs, "_REDACT_LOAD_ERROR", "simulated failure"):
                    data = store.dump(raw=True)  # must not raise
                self.assertEqual(data["records"][0]["objective"], "objective text")
            finally:
                store.close()

    def test_calibrated_dump_default_refuses_when_redactor_missing(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                store.claim("thing", "ephemeral", "objective text", [])
                with mock.patch.object(bs, "_REDACT", None), \
                     mock.patch.object(bs, "_REDACT_LOAD_ERROR", "simulated failure"):
                    with self.assertRaises(bs.RedactionUnavailable):
                        store.dump()
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
