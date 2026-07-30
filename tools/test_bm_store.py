#!/usr/bin/env python3
"""Regression tests for tools/bm_store.py, the BrotherMode V2 engine core.
Standard library only. Run: python3 tools/test_bm_store.py

Every test here is self-contained under tempfile.TemporaryDirectory() and
never touches this repo's own files, BROTHERMODE_ROOT, or the real home
directory. The calibrated_* tests each reproduce one confirmed V1 defect
(named inline, see docs/superpowers/specs/2026-07-26-brothermode-v2-design.md)
and assert that V2 refuses what V1 silently allowed.
"""
import ast
import datetime
import gc
import glob
import hashlib
import io
import json
import ntpath
import os
import pathlib
import random
import re
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time
import unicodedata
import unittest
import uuid
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))

import importlib.util
_spec = importlib.util.spec_from_file_location("bm_store", os.path.join(HERE, "bm_store.py"))
bs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bs)
sys.modules["bm_store"] = bs

# LOOP 2, 2026-07-30. Loaded read-only, for exactly one purpose: the
# enumeration test discovers every rule-altering command from bm_learn's OWN
# COMMANDS table rather than a hand-typed list. bm_learn.py loads its own
# bm_store.py by path (bm_learn._load), so `bl.bs` is a SEPARATE module
# instance from `bs` above; every exception assertion in this file still goes
# through THIS module's `bs.OwnershipRefused`, never bl's, and the tests below
# call store methods directly rather than bl's CLI functions for that reason.
_bl_spec = importlib.util.spec_from_file_location("bm_learn", os.path.join(HERE, "bm_learn.py"))
bl = importlib.util.module_from_spec(_bl_spec)
_bl_spec.loader.exec_module(bl)
sys.modules["bm_learn"] = bl

# The rule-shaping arguments a receipt is fingerprinted over. Kept next to the
# helper that uses them so a new shaping argument this list forgets shows up as
# a receipt that never matches, loudly, rather than as a receipt that silently
# covers less than the founder was shown.
_RECEIPT_SHAPE = ("trigger", "action", "because", "domain", "scope_type",
                  "scope_key", "rule_type", "severity",
                  "atomicity_override", "conflict_override")

# The fields an EDIT receipt is fingerprinted over, same discipline (FIX ROUND
# P3): rewriting a rule's injectable text is the same act as creating it.
_EDIT_SHAPE = ("trigger", "action", "because", "domain")


def _edited(store, prefix, expected_version, **kw):
    """Edit a rule the way the product now does: through a real, minted,
    one-time EDIT receipt. Every edit in this suite goes through here for the
    reason _approved exists."""
    rec = store.mint_edit_receipt(
        prefix, expected_version,
        founder_response="the founder answered yes to this edit, in a test",
        **{k: v for k, v in kw.items() if k in _EDIT_SHAPE})
    return store.edit_learning_rule(prefix, expected_version,
                                    receipt=rec["token"], **kw)


def _approved(store, prefix, **kw):
    """Approve a candidate the way the product now does: through a real,
    minted, one-time approval receipt (post-audit LOOP 3, Model A).

    EVERY approval in this suite goes through here, and that is the point. If
    the tests could still call approve_learning_candidate directly with no
    receipt, a hundred of them would keep passing against a door the product no
    longer has, and the suite would be measuring a dead code path.

    The receipt is minted with the SAME shaping arguments the approval will use,
    because a receipt is bound to the exact rule text the founder was shown. A
    test that wants the mismatch case mints its own receipt on purpose."""
    rec = store.mint_approval_receipt(
        prefix, founder_response="the founder answered yes, in a test",
        **{k: v for k, v in kw.items() if k in _RECEIPT_SHAPE})
    return store.approve_learning_candidate(prefix, receipt=rec["token"], **kw)


def _state_changed(store, prefix, target, reason="", successor_prefix=None,
                   receipt_kind=None):
    """Move a rule the way the product now does (LOOP 2, 2026-07-30): through
    a real, minted, one-time state-change receipt, for supersede, deprecate
    and forget. Every one of those three in this suite that is not itself
    testing the gate goes through here, for the same reason _approved and
    _edited exist: a test that could still call change_learning_rule_state
    directly with no receipt would keep passing against a door the product
    no longer has.

    receipt_kind defaults from STATE_CHANGE_GATE_KIND (the same default the
    store itself uses), so a caller only overrides it to reach
    resolve_learning_conflict's own 'resolve-conflict' kind through this same
    underlying move."""
    kind = receipt_kind or bs.STATE_CHANGE_GATE_KIND.get(target, target)
    successor_uuid = (store.get_learning_rule(successor_prefix)["rule_uuid"]
                      if successor_prefix else "")
    rec = store.mint_state_change_receipt(
        kind, prefix, founder_response="the founder answered yes, in a test",
        content_parts=(target, successor_uuid, reason))
    return store.change_learning_rule_state(
        prefix, target, reason=reason, successor_prefix=successor_prefix,
        receipt=rec["token"], receipt_kind=kind)


def _conflict_resolved(store, loser_prefix, other_prefix, how, reason=""):
    """resolve_learning_conflict the way the product now does (LOOP 2,
    2026-07-30): through a real, minted, one-time 'resolve-conflict'
    receipt, for all three resolutions (superseded, contradicted,
    deprecated). This is the loop's headline case: before this, a conflict
    against an approved GATE rule could be stood down with no receipt at
    all."""
    other_uuid = store.get_learning_rule(other_prefix)["rule_uuid"]
    rec = store.mint_state_change_receipt(
        "resolve-conflict", loser_prefix,
        founder_response="the founder answered yes, in a test",
        content_parts=(how, other_uuid, reason))
    return store.resolve_learning_conflict(
        loser_prefix, other_prefix, how, reason=reason, receipt=rec["token"])


# Two tests below need a module to be GENUINELY absent, not merely patched to
# None, because only a real failed import exercises _load_redact()'s own
# exception path. Until the P9 fix round they got that by renaming
# tools/bm_telemetry.py aside inside THIS checkout and putting it back in a
# finally. That mutated the working tree for the length of the test, and:
#   1. Any other process reading the checkout in that window (a second gate
#      run, an editor, a build) saw a repository missing a production module
#      and failed for a reason unrelated to the code under test (reproduced
#      2026-07-27).
#   2. A finally clause does not survive SIGKILL, and tools/test_all.py now
#      kills a suite that exceeds its timeout. A timeout landing inside the
#      window DELETED tools/bm_telemetry.py from the working tree and left
#      bm_telemetry.py.moved-for-test behind, after which the rest of the gate
#      ran against a broken checkout and reported ordinary failures
#      (reproduced 2026-07-29).
# The absence is now staged in a throwaway copy instead. Nothing in this
# checkout is renamed, moved or removed by any test, so there is no window to
# guard, no lock to hold, and no state for a kill to strand.
def _tools_mirror_without(case, *omit):
    """A private copy of the shipping modules in tools/, minus the named ones.
    Returns its path. Import bm_store from HERE and it finds bm_telemetry.py
    next to it; import the copy and it genuinely cannot, which is the whole
    point. Test suites are not copied: nothing under test imports them, and
    they are the bulk of the directory."""
    mirror = tempfile.mkdtemp(prefix="bm-tools-without-")
    case.addCleanup(shutil.rmtree, mirror, True)
    for name in sorted(os.listdir(HERE)):
        if not name.endswith(".py") or name.startswith("test_"):
            continue
        if name in omit:
            continue
        shutil.copy2(os.path.join(HERE, name), os.path.join(mirror, name))
    for name in omit:
        # Real assertions, not `assert`: python -O strips the bare statement,
        # and a mirror that silently still contains the module would make the
        # test below prove nothing.
        case.assertFalse(os.path.exists(os.path.join(mirror, name)),
                         "%s must be absent from the mirror" % name)
        case.assertTrue(os.path.exists(os.path.join(HERE, name)),
                        "%s must still be present in this checkout" % name)
    return mirror


def _run_cli(args, cwd, env=None, script=None):
    """Invoke the CLI as a subprocess, always with BROTHERMODE_ROOT scrubbed
    from the child's environment so ambient developer state (this repo's own
    checkout, a shell export left over from another task) can never leak
    into a test that is trying to prove something about root resolution or
    exit codes. `script` points the run at a copy of bm_store.py somewhere
    else, which is how a test proves behavior with a sibling module missing
    without touching this checkout."""
    e = dict(os.environ)
    e.pop("BROTHERMODE_ROOT", None)
    if env:
        e.update(env)
    return subprocess.run(
        [sys.executable, script or os.path.join(HERE, "bm_store.py")] + args,
        cwd=cwd, capture_output=True, text=True, env=e)

def _scan_for_forbidden_output_calls(lines):
    """Shared by the round-7 output-funnel structural test and its
    calibration companion: any non-comment line containing a bare print(),
    sys.stdout.write, sys.stderr.write, or an equivalent .stdout.write /
    .stderr.write. Comment lines (stripped content starting with '#') are
    skipped so this can never be tripped by the funnel's own explanatory
    comments, which name these exact forbidden patterns on purpose.

    The lookbehind on print( was added on 2026-07-29 by Loop 7, which called
    bm_learning.task_fingerprint() and was reported as a bare print, because
    "task_fingerprint(" ends in the six characters "print(". The scan is
    STRICTER after the change, not looser: a call is only a print when the
    name STARTS there, so print(...) at the start of a line, after whitespace,
    after a bracket or after a comma is still caught, and the calibration
    companion below proves it on a reinjected defect."""
    pat = re.compile(r"(?<![0-9A-Za-z_.])print\(|sys\.stdout\.write|"
                     r"sys\.stderr\.write|\.stdout\.write|\.stderr\.write")
    return [i for i, line in enumerate(lines, 1)
            if not line.lstrip().startswith("#") and pat.search(line)]


def _sha256_file(path):
    """Content fingerprint used by the finding-7 tests to prove a file was
    not moved AND not rewritten. Existence alone is too weak: a store that
    was quarantined and then recreated empty at the same path also exists."""
    h = hashlib.sha256()
    with io.open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# Sink calls that OPEN or WRITE a path. Shared by the finding-2B structural
# test and its calibration companion below.
_PATH_SINKS = ("open", "io.open", "_atomic_write_text", "_write_generated_file",
               "os.makedirs", "os.replace", "os.rename", "os.remove", "os.unlink",
               "os.rmdir", "shutil.copy2", "shutil.copyfile", "shutil.move",
               "shutil.rmtree")
_ROOT_ARG_NAMES = ("root", "project_root")


def _dotted_call_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted_call_name(node.value)
        return (base + "." + node.attr) if base else node.attr
    return ""


def _looks_like_project_root(node):
    """The expressions this codebase uses to mean "the project root":
    a bare `root`/`project_root` parameter, or any `.root` attribute
    (`self.root`, `store.root`)."""
    if isinstance(node, ast.Name):
        return node.id in _ROOT_ARG_NAMES
    if isinstance(node, ast.Attribute):
        return node.attr == "root"
    return False


def _scan_root_path_sites(source, filename="bm_store.py"):
    """Returns (root_joins, concat_sinks) for one Python source string.

    root_joins:   os.path.join(<project root>, ...) call sites, which must be
                  safe_project_path(...) instead.
    concat_sinks: a write/open sink handed a path built by string
                  concatenation, the shape that produced the STATE.md.bak
                  write the funnel would otherwise never see.

    Each entry is (lineno, enclosing qualified function name)."""
    tree = ast.parse(source, filename=filename)
    root_joins, concat_sinks = [], []

    class _Visitor(ast.NodeVisitor):
        def __init__(self):
            self.class_stack = []
            self.func_stack = ["<module>"]
            self.taint_stack = [set()]

        def visit_ClassDef(self, node):
            self.class_stack.append(node.name)
            self.generic_visit(node)
            self.class_stack.pop()

        def visit_FunctionDef(self, node):
            qualified = ("%s.%s" % (self.class_stack[-1], node.name)
                         if self.class_stack else node.name)
            tainted = set()
            for sub in ast.walk(node):
                if (isinstance(sub, ast.Assign)
                        and isinstance(sub.value, ast.BinOp)
                        and isinstance(sub.value.op, ast.Add)):
                    for target in sub.targets:
                        if isinstance(target, ast.Name):
                            tainted.add(target.id)
            self.func_stack.append(qualified)
            self.taint_stack.append(tainted)
            self.generic_visit(node)
            self.taint_stack.pop()
            self.func_stack.pop()

        def visit_Call(self, node):
            name = _dotted_call_name(node.func)
            enclosing = self.func_stack[-1]
            if (name == "os.path.join" and node.args
                    and _looks_like_project_root(node.args[0])):
                root_joins.append((node.lineno, enclosing))
            if name in _PATH_SINKS and node.args:
                first = node.args[0]
                concatenated = (isinstance(first, ast.BinOp)
                                and isinstance(first.op, ast.Add))
                from_concat = (isinstance(first, ast.Name)
                               and first.id in self.taint_stack[-1])
                if concatenated or from_concat:
                    concat_sinks.append((node.lineno, enclosing))
            self.generic_visit(node)

    _Visitor().visit(tree)
    return root_joins, concat_sinks

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
        # Fix-round 8: asserts the SPECIFIC message each case is rejected
        # with, not just "some ValueError": a plain assertRaises(ValueError)
        # survives deleting the actual guard for one case as long as a
        # DIFFERENT, unrelated check happens to also raise ValueError for
        # the same input.
        with self.assertRaisesRegex(ValueError, r"may not be '\.\.'"):
            bs.valid_name("..")
        with self.assertRaisesRegex(ValueError, r"may not be '\.'"):
            bs.valid_name(".")
        with self.assertRaisesRegex(ValueError, r"reserved character"):
            bs.valid_name("a/b")

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
        # Fix-round 8: transition() always echoes back the SAME
        # lifecycle_uuid it was called with (that comparison passes by
        # construction, not because resume did anything), so this asserts
        # what actually changes instead: the state transition itself, the
        # version increment, and that the change is independently visible
        # via a fresh get() rather than only in the value transition()
        # happened to return.
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                rec = store.claim("thing", "ephemeral", "obj", [])
                parked = store.transition(rec.lifecycle_uuid, rec.version, "parked")
                self.assertEqual(parked.state, "parked")
                resumed = store.transition(parked.lifecycle_uuid, parked.version, "active")
                self.assertEqual(resumed.state, "active")
                self.assertEqual(resumed.version, parked.version + 1)
                refetched = store.get(rec.lifecycle_uuid)
                self.assertEqual(refetched.state, "active")
                self.assertEqual(refetched.version, resumed.version)
            finally:
                store.close()

    def test_calibrated_11_locked_database_refuses_without_quarantine(self):
        # Amended 2026-07-26: the first draft quarantined on ANY
        # sqlite3.DatabaseError, and a busy/locked database (OperationalError,
        # a DatabaseError subclass) got renamed out from under a concurrent
        # writer, which is itself data loss. A tiny busy_timeout_ms makes the
        # "database is locked" failure near-instant instead of a real 5s wait.
        #
        # Fix-round 8: CRITICAL A made Store.__init__ read-only-verify an
        # EXISTING store's schema instead of always running DDL, and WAL
        # mode's readers do not block on another connection's write lock
        # (BEGIN EXCLUSIVE included) the way a write does; bare construction
        # under an external lock now succeeds. The contention this guards
        # against is real writers (two `claim` invocations), so the busy
        # check moved from open time to the first actual write.
        with tempfile.TemporaryDirectory() as d:
            store0 = bs.Store(d)
            store0.close()
            path = bs.store_path(d)
            locker = sqlite3.connect(path, timeout=0, isolation_level=None)
            locker.execute("BEGIN EXCLUSIVE")
            try:
                store = bs.Store(d, busy_timeout_ms=50)
                try:
                    with self.assertRaises(bs.OwnershipRefused) as ctx:
                        store.claim("thing", "ephemeral", "obj", [])
                    self.assertEqual(ctx.exception.reason, "db-busy")
                finally:
                    store.close()
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
            bs.init_project(d).close()
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

    def test_calibrated_unicode_normalization_folds_where_the_fs_folds(self):
        """Regression, fix-round 2026-07-29. macOS APFS and HFS+ are
        normalization INSENSITIVE: 'src/café.py' (NFD) and
        'src/café.py' (NFC) are one inode and two different Python
        strings, so a claim stored in one spelling did not overlap a write in
        the other and the fence hook allowed a foreign session through its
        default path. Linux is normalization sensitive, where the two really
        are different files, so it is deliberately left alone."""
        nfd = unicodedata.normalize("NFD", "src/café_日本.py")
        nfc = unicodedata.normalize("NFC", "src/café_日本.py")
        self.assertNotEqual(nfd, nfc, "the two spellings must differ as text")
        for platform_name in ("darwin", "win32"):
            with mock.patch.object(bs.sys, "platform", platform_name):
                self.assertTrue(bs.paths_overlap(nfd, nfc), platform_name)
                self.assertTrue(bs.paths_overlap(nfc, nfd), platform_name)
        with mock.patch.object(bs.sys, "platform", "linux"):
            self.assertFalse(bs.paths_overlap(nfd, nfc))
        # Restore half: folding normalization must not make unrelated paths
        # overlap.
        with mock.patch.object(bs.sys, "platform", "darwin"):
            self.assertFalse(bs.paths_overlap(nfc, "src/other.py"))

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
            # --raw, not the default dump: LOOP 11 made ordinary dump
            # WITHHOLD founder prose (objectives included), so the assertion
            # about WHICH objective survived the collision has to read the
            # store authoritatively. The default view is asserted separately
            # in TestExportWithholdingPolicy.
            r3 = _run_cli(["dump", "--raw"], d)
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

    def test_structural_gate4_bare_execute_sites_are_all_named_exceptions(self):
        # Redesigned fix-round 8 (was a magic count of 15: fragile, since it
        # changes innocently whenever an exempt function gains or loses a
        # line, and would silently accept a genuinely NEW unrouted call
        # site as long as the total happened to still match). Asserts the
        # actual PROPERTY instead, via a real AST parse (not a line-text
        # regex, which cannot tell which function a line lives in): every
        # bare .execute()/.executescript() call site must live inside one
        # of this CLOSED, named set, each exempt for a stated reason. A new
        # call site anywhere else fails with its own enclosing function
        # name, which is the actual signal a reviewer needs.
        exempt = {
            "_exec": "the one routing point itself",
            "Store.__init__": "runs before the connection is confirmed "
                               "healthy enough to trust _exec's quarantine path",
            "ReadOnlyStore.__init__": "same as Store.__init__",
            "_connect_read_only": "the one place a read-only connection is "
                                   "opened, before self.conn exists",
            "Store._ensure_schema": "runs only inside that same protected "
                                     "open-time try block (brand new file)",
            "Store._verify_schema_or_raise": "same protected open-time try "
                                              "block (fix-round 8, CRITICAL A, existing file)",
            "Store._ensure_indexes": "same protected open-time try block, run right "
                                      "after schema creation/verification on EVERY open "
                                      "(prerelease fix round, the transitions index)",
            "Store._migrate_from": "correction-learning Loop 1. Owns its own "
                                    "BEGIN EXCLUSIVE / COMMIT / ROLLBACK and runs "
                                    "inside the same protected open-time try block; "
                                    "routing transaction control through _exec would "
                                    "put _exec's quarantine path inside the very "
                                    "transaction it would then be unable to roll back",
            "_migrate_1_to_2": "correction-learning Loop 1. Pure additive DDL, same "
                                "category as Store._ensure_schema above, executed "
                                "inside the caller's exclusive transaction",
            "_migrate_2_to_3": "post-audit LOOP 3 (approval receipts). Pure "
                                "additive DDL, identical category to "
                                "_migrate_1_to_2, executed inside the caller's "
                                "exclusive transaction",
            "_migrate_3_to_4": "post-audit LOOP P6 (retrieval runs). Additive "
                                "DDL plus ONE guarded ADD COLUMN, executed "
                                "inside the caller's exclusive transaction; "
                                "the PRAGMA it reads is schema introspection, "
                                "the same category as _text_columns below",
            "Store._transaction": "ROLLBACK during cleanup must never mask "
                                   "the exception already being handled",
            "_quarantine_record_count": "reads an ALREADY quarantined file, "
                                         "not the live store",
            "_text_columns": "PRAGMA table_info is schema introspection, not data access",
            "_fts5_probe": "post-audit LOOP P7. Asks whether this SQLite can "
                            "build an FTS5 table at all, in temp; a build "
                            "without the module raises OperationalError, and "
                            "_exec would read that as structural damage and "
                            "quarantine a HEALTHY store over an optional "
                            "capability being absent",
            "Store._fts_exec": "post-audit LOOP P7 fix round. The ONE routing "
                                "point for statements against the INDEX table, "
                                "and not being _exec is the entire point: _exec "
                                "reads 'no such table: learning_rule_fts' as "
                                "structural damage and quarantines the store, "
                                "which destroyed a healthy database, the "
                                "approval in flight and every rule in it over an "
                                "OPTIONAL accelerator. Errors come back as "
                                "sqlite3.Error and every caller here switches "
                                "the fast path to lexical. Statements against "
                                "the REAL tables still go through _exec",
            "_migrate_4_to_5": "a schema migration step, run INSIDE the "
                               "caller's BEGIN EXCLUSIVE. _exec quarantines "
                               "on DatabaseError, which is exactly wrong "
                               "here: a CREATE TABLE failing mid-migration "
                               "must roll the caller's transaction back, not "
                               "move the founder's store aside. Same "
                               "exemption and same reason as every other "
                               "_migrate_*_to_* above",
            "_migrate_5_to_6": "a schema migration step, run INSIDE the "
                               "caller's BEGIN EXCLUSIVE. Same exemption and "
                               "same reason as every other _migrate_*_to_* "
                               "above: a DROP INDEX or CREATE INDEX failing "
                               "mid-migration must roll the caller's "
                               "transaction back, not move the founder's "
                               "store aside",
            "_migrate_6_to_7": "a schema migration step, run INSIDE the "
                               "caller's BEGIN EXCLUSIVE. Same exemption and "
                               "same reason as every other _migrate_*_to_* "
                               "above: a CREATE TABLE failing mid-migration "
                               "must roll the caller's transaction back, not "
                               "move the founder's store aside",
            "_migrate_7_to_8": "a schema migration step, run INSIDE the "
                               "caller's BEGIN EXCLUSIVE. Same exemption and "
                               "same reason as every other _migrate_*_to_* "
                               "above: an ALTER TABLE ADD COLUMN failing "
                               "mid-migration must roll the caller's "
                               "transaction back, not move the founder's store "
                               "aside. The PRAGMA table_info probe beside it is "
                               "schema introspection rather than data access, "
                               "and routing it through _exec would read 'no "
                               "such table' on a store that never reached "
                               "schema 7 as structural damage",
            "_undelivered_handover_rows": "one sqlite_master probe asking "
                                          "whether the handovers table exists "
                                          "at all (LOOP P12). Routing it "
                                          "through _exec would turn 'no such "
                                          "table' on a pre-schema-5 store "
                                          "into structural damage and "
                                          "QUARANTINE a healthy store to "
                                          "render a section. The real SELECT "
                                          "right after it does go through "
                                          "_exec",
            "_migrate_8_to_9": "a schema migration step, run INSIDE the "
                               "caller's BEGIN EXCLUSIVE (LOOP 2, the generic "
                               "state-change receipt table). Same exemption "
                               "and same reason as every other "
                               "_migrate_*_to_* above: a CREATE TABLE failing "
                               "mid-migration must roll the caller's "
                               "transaction back, not move the founder's "
                               "store aside",
            "_migrate_9_to_10": "a schema migration step, run INSIDE the "
                                "caller's BEGIN EXCLUSIVE (LOOP 3, "
                                "learning_applications.presentation and "
                                ".action_reached). Same exemption and same "
                                "reason as _migrate_7_to_8: an ALTER TABLE ADD "
                                "COLUMN failing mid-migration must roll the "
                                "caller's transaction back, not move the "
                                "founder's store aside, and the PRAGMA "
                                "table_info probe beside it is schema "
                                "introspection rather than data access",
            "_migrate_10_to_11": "a schema migration step, run INSIDE the "
                                 "caller's BEGIN EXCLUSIVE (LOOP 4, "
                                 "learning_retrieval_membership and "
                                 "provisional_records). Same exemption and "
                                 "same reason as _migrate_8_to_9: a CREATE "
                                 "TABLE failing mid-migration must roll the "
                                 "caller's transaction back, not move the "
                                 "founder's store aside",
        }
        with io.open(os.path.join(HERE, "bm_store.py"), encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename="bm_store.py")
        offenders = []

        class _Visitor(ast.NodeVisitor):
            def __init__(self):
                self.class_stack = []
                self.func_stack = ["<module>"]

            def visit_ClassDef(self, node):
                self.class_stack.append(node.name)
                self.generic_visit(node)
                self.class_stack.pop()

            def visit_FunctionDef(self, node):
                qualified = ("%s.%s" % (self.class_stack[-1], node.name)
                             if self.class_stack else node.name)
                self.func_stack.append(qualified)
                self.generic_visit(node)
                self.func_stack.pop()

            def visit_Call(self, node):
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr in ("execute", "executescript"):
                    enclosing = self.func_stack[-1]
                    if enclosing not in exempt:
                        offenders.append((node.lineno, enclosing))
                self.generic_visit(node)

        _Visitor().visit(tree)
        self.assertEqual(offenders, [],
                          "raw execute()/executescript() call site(s) outside the exempt "
                          "set (line, enclosing function): %s; route through _exec, or add "
                          "the enclosing function to `exempt` above with a stated reason"
                          % offenders)

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
        #
        # CRITICAL B (fix-round 8, from an independent test-mutation audit):
        # this test used to assert only that the quarantine DIRECTORY
        # exists (which os.makedirs creates before anything is moved into
        # it) and that the SOURCE path is gone (which a plain delete
        # satisfies exactly as well as a real move). Two mutations survived
        # it: replacing a move with a delete, and quarantining only the
        # sidecars while unlinking the main store. Asserting CONTENT
        # equality for the quarantined file, for the main store and each
        # sidecar, closes both: neither mutation can produce a file at the
        # destination holding the correct pre-quarantine bytes.
        main_bytes = b"garbage, not a database, corrupting the main file 0123456789"
        wal_bytes = b"wal sidecar bytes, pretend records live here"
        shm_bytes = b"shm sidecar bytes"
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            store.close()
            path = bs.store_path(d)
            with io.open(path + "-wal", "wb") as f:
                f.write(wal_bytes)
            with io.open(path + "-shm", "wb") as f:
                f.write(shm_bytes)
            with io.open(path, "wb") as f:
                f.write(main_bytes)
            with self.assertRaises(bs.StoreCorrupt) as ctx:
                bs.Store(d)
            qdir = ctx.exception.quarantine_path
            self.assertTrue(os.path.isdir(qdir))
            with io.open(os.path.join(qdir, "store.sqlite3"), "rb") as f:
                self.assertEqual(f.read(), main_bytes)
            with io.open(os.path.join(qdir, "store.sqlite3-wal"), "rb") as f:
                self.assertEqual(f.read(), wal_bytes)
            # -shm is the one exception to exact content equality: opening
            # ANY connection against this corrupt main file fails inside
            # sqlite3 itself, at "PRAGMA journal_mode=WAL", before a single
            # line of this module's code runs; verified directly that this
            # failed PRAGMA still reinitializes the -shm shared-memory
            # region as a side effect (resized from this test's 18 seed
            # bytes to a real 32768-byte page), independent of anything
            # _quarantine_and_raise does. -shm is documented by sqlite
            # itself as a locking/coordination structure, not a log of
            # real records the way -wal is, so existence (it was quarantined
            # at all, not left behind) is the honest, achievable guarantee
            # here; test_calibrated_gateC_sidecars_preserved_even_when_
            # close_deletes_them below covers exact -shm content preservation
            # for the scenario where that IS achievable (corruption detected
            # on an already-open connection, not at a fresh connect).
            self.assertTrue(os.path.exists(os.path.join(qdir, "store.sqlite3-shm")))
            self.assertFalse(os.path.exists(path + "-wal"))
            self.assertFalse(os.path.exists(path + "-shm"))
            self.assertFalse(os.path.exists(path))

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
        # Updated fix-round 6 (SOFT E): adopting a record that is currently
        # ACTIVE under a different, live session now requires the explicit
        # adopt_from_live_session=True; this test's "dead-session" claim is
        # still ACTIVE (never parked), so it needs the flag to pass.
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                rec = store.claim("thing", "ephemeral", "obj", [], session_id="dead-session")
                adopted = store.transition(rec.lifecycle_uuid, rec.version, "adopted",
                                            session_id="rescuer", adopt_from_live_session=True)
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

    # -- BLOCKER 2 (release-blockers spec, 2026-07-26) ----------------------

    def test_calibrated_blocker2_resume_from_a_different_session_succeeds_after_park(self):
        # THE reproduced bug: monday `off` (which parks a persistent
        # record) says "resumable"; tuesday `resume` from a DIFFERENT
        # session used to be refused 'not-owner', because park() never
        # clears session_id and the OLD guard compared it unconditionally.
        # OWNERSHIP GUARDS ONLY ACTIVE RECORDS: a parked record has no live
        # writer, so ANY session may resume it and becomes its owner in the
        # same transition.
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                rec = store.claim("thing", "persistent", "obj", [], session_id="monday")
                parked = store.transition(rec.lifecycle_uuid, rec.version, "parked",
                                           session_id="monday")
                self.assertEqual(parked.session_id, "monday",
                                 "park must not clear the last owner's session_id "
                                 "(that is the very column resume must tolerate "
                                 "disagreeing with)")
                resumed = store.transition(parked.lifecycle_uuid, parked.version, "active",
                                            session_id="tuesday")
                self.assertEqual(resumed.state, "active")
                self.assertEqual(resumed.session_id, "tuesday",
                                 "the resuming session must become the new owner "
                                 "in the same transition")
            finally:
                store.close()

    def test_calibrated_blocker2_active_records_still_guard_park_and_complete(self):
        # The fix must not overcorrect: an ACTIVE record (a live writer)
        # must still refuse park/complete from a different session, exactly
        # as test_calibrated_soft10_cross_session_park_refused already
        # proves for park; this adds the same check for complete.
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                rec = store.claim("thing", "ephemeral", "obj", [], session_id="owner")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.transition(rec.lifecycle_uuid, rec.version, "complete",
                                      session_id="attacker", evidence="tests pass")
                self.assertEqual(ctx.exception.reason, "not-owner")
                still = store.get(rec.lifecycle_uuid)
                self.assertEqual(still.state, "active")
            finally:
                store.close()

    def test_calibrated_blocker2_reinjecting_the_unconditional_guard_breaks_resume(self):
        # CALIBRATION: reinject the OLD, unconditional shape (the guard
        # applies regardless of current state) onto the real PRODUCT
        # symbol _ownership_guard_applies, and confirm the SAME
        # resume-after-park-by-a-different-session now reproduces the
        # reported defect (refused 'not-owner'); if this assertion fails,
        # the test above is not calibrated to the defect it claims to catch.
        original = bs._ownership_guard_applies
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                rec = store.claim("thing", "persistent", "obj", [], session_id="monday")
                parked = store.transition(rec.lifecycle_uuid, rec.version, "parked",
                                           session_id="monday")
                bs._ownership_guard_applies = lambda current_state: True
                try:
                    with self.assertRaises(bs.OwnershipRefused) as ctx:
                        store.transition(parked.lifecycle_uuid, parked.version, "active",
                                          session_id="tuesday")
                    self.assertEqual(
                        ctx.exception.reason, "not-owner",
                        "REINJECTION CHECK: the old, unconditional ownership guard "
                        "must refuse this legitimate cross-session resume the same "
                        "way BLOCKER 2 was reported")
                finally:
                    bs._ownership_guard_applies = original
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
                bs.write_state_view(d)
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

# ---------------------------------------------------------------------------
# Fix round 4 (2026-07-26): an honesty defect. After a truncation-quarantine,
# the next command silently created a fresh store and reported "healthy"
# seconds after total data loss; a read-only diagnostic in a fresh directory
# created the very store.sqlite3 (plus -wal/-shm) it claimed to be checking.
# ---------------------------------------------------------------------------

class TestFixRound4Honesty(unittest.TestCase):
    # Amended for FINDING 7 (2026-07-26): these three tests used a read-only
    # `verify` to CREATE the quarantine they then reason about, which is the
    # very behavior finding 7 confirmed as a defect (the SessionStart hook
    # runs `verify` automatically, so a transient disk or permission error
    # was enough to move a healthy database). The honesty contract each test
    # exists for is unchanged and every original assertion is still here;
    # only the step that produces the quarantine moved to a WRITABLE
    # command, which is the one thing allowed to move a file. Each test also
    # gained the new guarantee: the read-only pass leaves the store exactly
    # where it was.
    def test_calibrated_second_verify_after_quarantine_never_says_healthy(self):
        with tempfile.TemporaryDirectory() as d:
            _run_cli(["init"], d)
            r_claim = _run_cli(["claim", "k", "--lifetime", "persistent",
                                "--objective", "IMPORTANT WORK", "--files", "k.py"], d)
            self.assertEqual(r_claim.returncode, 0, r_claim.stdout + r_claim.stderr)
            path = bs.store_path(d)
            with io.open(path, "wb"):
                pass  # truncate to 0 bytes
            truncated_digest = _sha256_file(path)
            r1 = _run_cli(["verify"], d)
            self.assertEqual(r1.returncode, 1, r1.stdout + r1.stderr)
            self.assertIn("CORRUPT", r1.stdout)
            # FINDING 7: verify REPORTS, it never moves. The file it just
            # called corrupt is still exactly where it was.
            self.assertEqual(glob.glob(path + ".quarantine-*"), [],
                              "a read-only verify must never quarantine")
            self.assertEqual(_sha256_file(path), truncated_digest)
            r2 = _run_cli(["verify"], d)
            self.assertNotEqual(r2.returncode, 0, r2.stdout + r2.stderr)
            self.assertNotIn("healthy", r2.stdout)
            # A WRITABLE command is what actually quarantines it.
            r_write = _run_cli(["claim", "k2", "--lifetime", "ephemeral",
                                "--objective", "o"], d)
            self.assertNotEqual(r_write.returncode, 0, r_write.stdout + r_write.stderr)
            qdirs = glob.glob(path + ".quarantine-*")
            self.assertEqual(len(qdirs), 1)
            r2 = _run_cli(["verify"], d)
            self.assertNotEqual(r2.returncode, 0, r2.stdout + r2.stderr)
            self.assertNotIn("healthy", r2.stdout)
            # SOFT F (fix-round 6, 2026-07-26): the pre-dispatch quarantine
            # warning that names the directory now goes to stderr, so
            # stdout (the payload stream) stays parseable.
            self.assertIn(os.path.basename(qdirs[0]), r2.stderr,
                          "verify must name the quarantine directory")

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
            # FINDING 7: a WRITABLE command triggers the quarantine now.
            # `verify` used to be what triggered it, and a read-only
            # diagnostic moving the founder's database is the defect.
            _run_cli(["claim", "k2", "--lifetime", "ephemeral", "--objective", "o"], d)
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

    def test_warning_printed_for_every_command_while_unacknowledged(self):
        with tempfile.TemporaryDirectory() as d:
            _run_cli(["init"], d)
            _run_cli(["claim", "k", "--lifetime", "ephemeral", "--objective", "obj"], d)
            path = bs.store_path(d)
            with io.open(path, "wb"):
                pass
            # FINDING 7: quarantining is a write, so a writable command is
            # what produces the outstanding quarantine this warning is about.
            _run_cli(["claim", "k2", "--lifetime", "ephemeral", "--objective", "o"], d)
            self.assertEqual(len(glob.glob(path + ".quarantine-*")), 1)
            r = _run_cli(["verify"], d)
            # SOFT F (fix-round 6, 2026-07-26): warnings go to stderr now,
            # so stdout stays a clean payload stream.
            self.assertIn("WARNING", r.stderr)
            self.assertIn("quarantine", r.stderr.lower())
            self.assertNotIn("WARNING", r.stdout)

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
            # --raw: claims.path is founder-supplied and is withheld by the
            # LOOP 11 export policy, so the fence content is read
            # authoritatively here. The count assertion below works either way.
            r_dump1 = _run_cli(["dump", "--raw"], d)
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

    def test_calibrated_gateB_quarantine_target_collision_refused(self):
        # The quarantine target is safe by construction (os.makedirs
        # exist_ok=False): pre-create something at the exact path a
        # deterministic quarantine would use and confirm it is never
        # written through.
        #
        # GATE H (fix-round 6, 2026-07-26): the sentinel MUST be named
        # store.sqlite3, the REAL basename os.replace(self.path, dst) uses.
        # The prior version of this test named it "PRIOR", a name
        # os.replace never targets, so the test stayed green even with
        # exist_ok flipped to True: the real overwrite risk was never
        # exercised. Checking CONTENT survival, not just file existence, is
        # what actually distinguishes "refused before touching it" from
        # "overwritten with different bytes".
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            path = store.path
            fixed_now = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
            fixed_uuid = uuid.UUID(int=0)
            qdir = path + ".quarantine-" + fixed_now.strftime("%Y%m%dT%H%M%S%f") + "-" + fixed_uuid.hex[:8]
            os.makedirs(qdir)
            sentinel = os.path.join(qdir, "store.sqlite3")
            sentinel_bytes = b"PRIOR QUARANTINE CONTENTS, MUST SURVIVE"
            with io.open(sentinel, "wb") as f:
                f.write(sentinel_bytes)
            with mock.patch.object(bs, "datetime") as dt_mock, \
                 mock.patch.object(bs.uuid, "uuid4", return_value=fixed_uuid):
                dt_mock.datetime.now.return_value = fixed_now
                dt_mock.timezone = datetime.timezone
                with self.assertRaises(bs.StoreCorrupt):
                    store._quarantine_and_raise(sqlite3.DatabaseError("simulated"))
            # Binary read: if the guard regresses, the sentinel is
            # overwritten with real (binary) sqlite bytes, and comparing as
            # bytes gives a clean assertion failure instead of a
            # UnicodeDecodeError burying the actual defect.
            with io.open(sentinel, "rb") as f:
                self.assertEqual(f.read(), sentinel_bytes,
                                  "must survive the collision untouched, not be overwritten")

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
            # SOFT F (fix-round 6, 2026-07-26): the --raw notice is a
            # warning, so it goes to stderr; stdout must be pure JSON.
            self.assertIn("cleartext", r_raw.stderr.lower())
            json.loads(r_raw.stdout)

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
            bs.write_state_view(d)
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

# ---------------------------------------------------------------------------
# Fix round 6 (2026-07-26): GATE A (percent sign opens another project's
# database), GATE B (bracket/star hides quarantine), GATE C (default dump
# leaks note/text/evidence/check_cmd/owner), GATE D (objective wiped by a
# tier-only reclaim, the SAME class as round 5's files bug, left open), SOFT
# E (adopt bypasses not-owner), SOFT F (warnings on stdout break JSON), SOFT
# G (gitdir pointer unvalidated).
# ---------------------------------------------------------------------------

class TestFixRound6(unittest.TestCase):
    # -- GATE A -------------------------------------------------------

    def test_calibrated_gateA_percent_sign_path_never_leaks_across_projects(self):
        # VERIFIED BY ORCHESTRATOR: standing inside p%41, dump/dashboard
        # used to return pA's record because the read-only sqlite URI
        # percent-decoded the path to a different file.
        with tempfile.TemporaryDirectory() as base:
            pa = os.path.join(base, "pA")
            ppercent = os.path.join(base, "p%41")
            os.makedirs(pa)
            os.makedirs(ppercent)
            sa = bs.Store(pa)
            sa.claim("victimwork", "ephemeral", "PRIVATE-PROJECT-A-OBJECTIVE", [])
            sa.close()
            sp = bs.Store(ppercent)
            sp.claim("ownwork", "ephemeral", "own-objective", [])
            sp.close()
            ro = bs.ReadOnlyStore(ppercent)
            try:
                data = ro.dump(raw=True)
            finally:
                ro.close()
            names = [r["name"] for r in data["records"]]
            self.assertEqual(names, ["ownwork"])
            view = bs.render_state_md(ppercent)
            self.assertNotIn("PRIVATE-PROJECT-A-OBJECTIVE", view)
            bs.write_state_view(ppercent)
            self.assertEqual(bs.verify(ppercent), [])

    def test_calibrated_gateA_query_only_actually_refuses_a_write(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            store.claim("k", "ephemeral", "obj", [])
            store.close()
            ro = bs.ReadOnlyStore(d)
            try:
                with self.assertRaises(sqlite3.OperationalError):
                    ro.conn.execute("INSERT INTO meta (key, value) VALUES ('x','y')")
            finally:
                ro.close()

    # -- GATE B -------------------------------------------------------

    def test_calibrated_gateB_bracket_path_quarantine_still_visible(self):
        with tempfile.TemporaryDirectory() as base:
            proj = os.path.join(base, "p[1]")
            os.makedirs(proj)
            store = bs.Store(proj)
            store.claim("k", "ephemeral", "obj", [])
            path = store.path
            store.close()
            with io.open(path, "wb"):
                pass
            with self.assertRaises(bs.StoreCorrupt):
                bs.Store(proj)
            found = bs._unacknowledged_quarantine_dirs(proj)
            self.assertEqual(len(found), 1)

    # -- GATE C (structural) --------------------------------------------

    def test_structural_gateC_every_text_column_redacted_by_default(self):
        # Enumerates EVERY text column from the LIVE schema (not a
        # hand-maintained list), plants a secret directly via SQL in every
        # row of every table (bypassing the public API, which cannot reach
        # every column, e.g. created_at), and asserts the default dump
        # shows none of them, while a safe-listed column stays readable.
        secret = "sk-test1234567890abcdef"
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                rec = store.claim("thing", "ephemeral", "obj", ["a.py"], session_id="s1")
                store.decide(rec.lifecycle_uuid, rec.version, "t", "x")
                store.checkpoint(rec.lifecycle_uuid, rec.version + 1, "next")
                store.send(rec.lifecycle_uuid, "directive")
                conn = store.conn
                conn.execute("BEGIN IMMEDIATE")
                conn.execute(
                    "INSERT INTO autosave_receipts (worktree_id, session_id, snapshot_sha, "
                    "tree_sha, source_head, captured_count, excluded_count, created_at) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    ("wt1", "s1", "a" * 40, "b" * 40, "c" * 40, 0, 0, bs.now_iso()))
                conn.execute("COMMIT")
                mutated_cols_by_table = {}
                for t in bs._TABLES:
                    cols = bs._text_columns(conn, t)
                    rowcount = conn.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0]
                    mutated = []
                    if rowcount and cols:
                        pk_cols = {r["name"] for r in
                                   conn.execute("PRAGMA table_info(%s)" % t).fetchall() if r["pk"]}
                        for col in cols:
                            # Primary-key columns cannot be blindly set to
                            # the SAME value across every row without
                            # violating uniqueness or referential
                            # integrity; they are exactly the
                            # identifier-shaped columns already in
                            # _DUMP_SAFE_COLUMNS by construction. A CHECK
                            # constraint (state/lifetime enums) makes an
                            # UPDATE to an arbitrary secret raise
                            # IntegrityError too: caught and skipped, since
                            # a column the schema itself refuses to hold an
                            # arbitrary string in has nothing to redact.
                            if col in pk_cols:
                                continue
                            conn.execute("BEGIN IMMEDIATE")
                            try:
                                conn.execute("UPDATE %s SET %s=?" % (t, col), (secret,))
                            except sqlite3.IntegrityError:
                                conn.execute("ROLLBACK")
                                continue
                            conn.execute("COMMIT")
                            mutated.append(col)
                    mutated_cols_by_table[t] = mutated
                dumped = store.dump()
            finally:
                store.close()
            offenders, safe_checked = [], []
            for t, cols in mutated_cols_by_table.items():
                for row in dumped[t]:
                    for col in cols:
                        if (t, col) in bs._DUMP_SAFE_COLUMNS:
                            safe_checked.append((t, col))
                            continue
                        if row.get(col) == secret:
                            offenders.append((t, col))
            self.assertEqual(offenders, [],
                              "these text columns leaked the secret unredacted: %s" % offenders)
            self.assertGreater(len(safe_checked), 0, "sanity: the safe-column set must be non-empty")

    # -- GATE D (structural) --------------------------------------------

    def test_calibrated_gateD_reclaim_omitting_objective_preserves_it(self):
        # VERIFIED BY ORCHESTRATOR reproduction: reclaim with only --tier.
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                store.claim("thing", "ephemeral", "important objective", [],
                            session_id="s1")
                updated = store.claim("thing", "ephemeral", session_id="s1", tier="T2")
                self.assertEqual(updated.objective, "important objective")
            finally:
                store.close()

    def test_structural_gateD_every_updatable_field_preserved_when_omitted(self):
        # Enumerates Store.UPDATABLE_SCALAR_FIELDS directly: a field added
        # there without _reclaim_active also treating it as None-preserves
        # fails this test.
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                seed = {"objective": "seed-objective", "owner": "seed-owner",
                        "tier": "seed-tier", "check_cmd": "seed-check"}
                self.assertEqual(set(seed), set(bs.Store.UPDATABLE_SCALAR_FIELDS),
                                  "test seed must cover exactly the declared updatable fields")
                store.claim("thing", "ephemeral", session_id="s1", **seed)
                for omitted in bs.Store.UPDATABLE_SCALAR_FIELDS:
                    kwargs = dict(seed)
                    kwargs.pop(omitted)
                    updated = store.claim("thing", "ephemeral", session_id="s1", **kwargs)
                    self.assertEqual(getattr(updated, omitted), seed[omitted],
                                      "omitting --%s must have left it untouched" % omitted)
            finally:
                store.close()

    # -- SOFT E -------------------------------------------------------

    def test_calibrated_soft_e_adopt_live_session_requires_explicit_flag(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                rec = store.claim("thing", "ephemeral", "obj", [], session_id="owner")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.transition(rec.lifecycle_uuid, rec.version, "adopted",
                                      session_id="attacker")
                self.assertEqual(ctx.exception.reason, "live-session-adopt-blocked")
                still = store.get(rec.lifecycle_uuid)
                self.assertEqual(still.state, "active")
                self.assertEqual(still.session_id, "owner")
                adopted = store.transition(rec.lifecycle_uuid, rec.version, "adopted",
                                            session_id="attacker", adopt_from_live_session=True)
                self.assertEqual(adopted.state, "adopted")
                self.assertIn("displaced", adopted_note_of(store, adopted.lifecycle_uuid))
            finally:
                store.close()

    # -- SOFT F -------------------------------------------------------

    def test_soft_f_dump_stdout_is_valid_json_with_quarantine_warning_outstanding(self):
        # A live, healthy store CAN coexist with a DORMANT, unacknowledged
        # quarantine directory left over from an earlier, already-resolved
        # incident: quarantine detection matches by name only, it does not
        # know or care whether that directory is still "blocking" anything
        # for the CURRENT store. Simulated directly (a real second
        # corruption cycle would first require init --acknowledge-quarantine
        # anyway, which would acknowledge it and defeat the scenario).
        with tempfile.TemporaryDirectory() as d:
            _run_cli(["init"], d)
            _run_cli(["claim", "k", "--lifetime", "ephemeral", "--objective", "obj"], d)
            leftover = bs.store_path(d) + ".quarantine-20260101T000000000000-deadbeef"
            os.makedirs(leftover)
            with io.open(os.path.join(leftover, "store.sqlite3"), "wb") as f:
                f.write(b"leftover corrupt bytes from an earlier incident")
            r = _run_cli(["dump"], d)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            data = json.loads(r.stdout)  # must not raise
            self.assertEqual([rec["name"] for rec in data["records"]], ["k"])
            self.assertIn("quarantine", r.stderr.lower())

    # -- SOFT G -------------------------------------------------------

    def test_calibrated_soft_g_crafted_gitdir_refused_creates_nothing(self):
        with tempfile.TemporaryDirectory() as base:
            proj = os.path.join(base, "proj")
            os.makedirs(proj)
            victim = os.path.join(base, "victim")
            with io.open(os.path.join(proj, ".git"), "w", encoding="utf-8") as f:
                f.write("gitdir: %s\n" % victim)
            with self.assertRaises(bs.OwnershipRefused) as ctx:
                bs.Store(proj)
            self.assertEqual(ctx.exception.reason, "path-escape")
            self.assertFalse(os.path.exists(victim))

def adopted_note_of(store, lifecycle_uuid):
    row = store.conn.execute(
        "SELECT note FROM transitions WHERE lifecycle_uuid=? AND to_state='adopted' "
        "ORDER BY id DESC LIMIT 1", (lifecycle_uuid,)).fetchone()
    return row["note"] if row else ""

def _make_pre_soft_e_transition(bs_module):
    """Builds the pre-SOFT-E transition() method: identical to the current
    one except the adopted branch never checks for a live session at all."""
    def old_transition(self, lifecycle_uuid, expected_version, to_state,
                        session_id="", note="", evidence="", adopt_from_live_session=False):
        if to_state not in bs_module._LEGAL_MOVES:
            raise ValueError("unknown target state %r" % (to_state,))
        if to_state == "complete" and not (evidence or "").strip():
            raise bs_module.OwnershipRefused("missing-evidence", "x")
        allowed_from = bs_module._LEGAL_MOVES[to_state]
        with self._transaction() as conn:
            row = bs_module._exec(self, "SELECT * FROM records WHERE lifecycle_uuid=?",
                                   (lifecycle_uuid,)).fetchone()
            if row is None or row["version"] != expected_version or row["state"] not in allowed_from:
                raise bs_module.StaleIdentity("stale")
            if to_state != "adopted" and row["session_id"] and row["session_id"] != (session_id or ""):
                raise bs_module.OwnershipRefused("not-owner", "x")
            ts = bs_module.now_iso()
            bs_module._exec(self,
                "UPDATE records SET state=?, version=version+1, updated_at=?, session_id=? "
                "WHERE lifecycle_uuid=? AND version=? AND state=?",
                (to_state, ts, session_id or row["session_id"], lifecycle_uuid,
                 expected_version, row["state"]))
            bs_module._exec(self,
                "INSERT INTO transitions (lifecycle_uuid, from_state, to_state, session_id, "
                "note, at) VALUES (?,?,?,?,?,?)",
                (lifecycle_uuid, row["state"], to_state, session_id or "", note or "", ts))
            return self._record_by_uuid(conn, lifecycle_uuid)
    return old_transition

class TestFixRound7(unittest.TestCase):
    # -- THE OUTPUT FUNNEL: structural guards -------------------------

    def test_structural_round7_no_print_or_raw_stream_write_anywhere(self):
        # THE OUTPUT FUNNEL: every byte this module sends to stdout or
        # stderr must go through a named funnel function (_out, _warn,
        # _out_prerendered, _out_unprotected), never a bare print()/
        # sys.stdout.write()/sys.stderr.write(). See the calibration
        # companion below for proof this scan is not vacuous.
        with io.open(os.path.join(HERE, "bm_store.py"), encoding="utf-8") as f:
            lines = f.readlines()
        hits = _scan_for_forbidden_output_calls(lines)
        self.assertEqual(hits, [],
                          "bare print()/stream.write() call site(s) found outside a "
                          "comment, at line(s): %s" % hits)

    def test_calibrated_round7_structural_scan_detects_a_reintroduced_print(self):
        # Calibrates the structural test above against the exact detection
        # function it uses, on a SYNTHETIC snippet rather than mutating the
        # real source file mid test-run: proves the scan genuinely catches
        # the defect class this round closed (a bare print() bypassing the
        # funnel), and that it leaves a funneled call site alone.
        bad_source = ["def cmd_example(argv):\n", "    print('leaked: ' + argv[0])\n"]
        self.assertEqual(_scan_for_forbidden_output_calls(bad_source), [2])
        good_source = ["def cmd_example(argv):\n", "    _out('safe: ' + argv[0])\n"]
        self.assertEqual(_scan_for_forbidden_output_calls(good_source), [])
        # Every shape the lookbehind must still catch, and the two it must
        # not, listed rather than trusted: an identifier that merely ENDS in
        # print is not a print call.
        for line in ("print('x')\n", "    print('x')\n", "  foo(print('x'))\n",
                     "  f(a, print('x'))\n", "  sys.stdout.write('x')\n"):
            self.assertEqual(_scan_for_forbidden_output_calls([line]), [1], line)
        for line in ("    fp = L.task_fingerprint(query)\n",
                     "    n = footprint(x)\n"):
            self.assertEqual(_scan_for_forbidden_output_calls([line]), [], line)

    def test_structural_round7_file_writes_of_rendered_text_go_through_the_funnel(self):
        # The only function allowed to write a RENDERED string to disk is
        # _write_generated_file (THE FILE FUNNEL). The one other call site,
        # write_state_view's own pre-rewrite backup, writes back EXISTING
        # bytes already on disk verbatim, never a newly rendered string:
        # the safety net GATE A exists to guarantee, not content this
        # module is emitting, so redacting a true backup would defeat its
        # purpose. If this count changes, a new file-write call site was
        # added without routing it through the funnel; update deliberately.
        with io.open(os.path.join(HERE, "bm_store.py"), encoding="utf-8") as f:
            lines = f.readlines()
        call_sites = [i for i, line in enumerate(lines, 1)
                      if "_atomic_write_text(" in line and not line.lstrip().startswith("def ")]
        self.assertEqual(len(call_sites), 2,
                          "_atomic_write_text call sites changed (now at lines %s); route "
                          "any new one through _write_generated_file or update deliberately"
                          % call_sites)

    def test_structural_round7_out_prerendered_restricted_to_named_call_sites(self):
        with io.open(os.path.join(HERE, "bm_store.py"), encoding="utf-8") as f:
            lines = f.readlines()
        call_sites = [i for i, line in enumerate(lines, 1)
                      if "_out_prerendered(" in line and not line.lstrip().startswith(("def ", "#"))]
        self.assertEqual(len(call_sites), 1,
                          "_out_prerendered call sites changed (now at lines %s); review "
                          "and update this count deliberately" % call_sites)

    def test_structural_round7_out_unprotected_restricted_to_named_call_sites(self):
        with io.open(os.path.join(HERE, "bm_store.py"), encoding="utf-8") as f:
            lines = f.readlines()
        call_sites = [i for i, line in enumerate(lines, 1)
                      if "_out_unprotected(" in line and not line.lstrip().startswith(("def ", "#"))]
        self.assertEqual(len(call_sites), 3,
                          "_out_unprotected call sites changed (now at lines %s); review "
                          "and update this count deliberately" % call_sites)

    # -- funnel behavior: the multi-line corruption regression --------

    def test_calibrated_round7_dashboard_and_dump_survive_the_funnel_intact(self):
        # THE OUTPUT FUNNEL's own blanket _sanitize_for_display, applied to
        # an already-ASSEMBLED multi-line document, was a real regression
        # introduced and caught within this same fix round: it escapes a
        # document's OWN structural newlines (and JSON's indentation) as if
        # they were founder-typed control-character injection, which is
        # exactly backwards. cmd_dashboard/cmd_dump route around it via
        # _out_prerendered/_out_unprotected; this proves both CLI paths
        # still produce intact, parseable output.
        with tempfile.TemporaryDirectory() as d:
            r = _run_cli(["init"], d)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = _run_cli(["claim", "thing", "--lifetime", "ephemeral", "--objective", "obj"], d)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r_dash = _run_cli(["dashboard"], d)
            self.assertEqual(r_dash.returncode, 0, r_dash.stdout + r_dash.stderr)
            self.assertIn("\n", r_dash.stdout)
            self.assertNotIn("\\x0a", r_dash.stdout)
            self.assertIn(bs._STATE_BEGIN, r_dash.stdout)
            r_dump = _run_cli(["dump"], d)
            self.assertEqual(r_dump.returncode, 0, r_dump.stdout + r_dump.stderr)
            parsed = json.loads(r_dump.stdout)  # must not raise
            self.assertEqual(parsed["records"][0]["name"], "thing")
            r3 = _run_cli([], d)
            self.assertNotIn("\\x0a", r3.stdout)
            self.assertIn("\n", r3.stdout)

    # -- funnel behavior: record names redacted everywhere -------------

    def test_calibrated_round7_record_name_redacted_everywhere(self):
        secret_name = "AKIAIOSFODNN7EXAMPLE"
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                rec = store.claim(secret_name, "ephemeral", "", [])
                digest = store.render_digest(rec.lifecycle_uuid)
            finally:
                store.close()
            view = bs.render_state_md(d)
            self.assertNotIn(secret_name, view)
            self.assertIn("[REDACTED]", view)
            self.assertIn(rec.lifecycle_uuid[:8], view,
                          "the lifecycle uuid prefix must still identify the record once "
                          "its name is redacted")
            self.assertNotIn(secret_name, digest)
            self.assertIn("[REDACTED]", digest)
            ro = bs.ReadOnlyStore(d)
            try:
                data_default = ro.dump()
                data_raw = ro.dump(raw=True)
            finally:
                ro.close()
            self.assertNotIn(secret_name, json.dumps(data_default),
                              "dump()'s default mode must redact the name like every "
                              "other founder-typed field")
            self.assertIn(secret_name, json.dumps(data_raw),
                          "dump(raw=True) remains the explicit, named escape hatch")
            r = _run_cli(["dashboard"], d)
            self.assertNotIn(secret_name, r.stdout)

    def test_calibrated_round7_dump_name_reinject_old_safe_columns_would_leak(self):
        secret_name = "AKIAIOSFODNN7EXAMPLE"
        old_safe_columns = frozenset(
            set(bs._DUMP_SAFE_COLUMNS) | {("records", "name")})
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                store.claim(secret_name, "ephemeral", "obj", [])
            finally:
                store.close()
            ro = bs.ReadOnlyStore(d)
            try:
                with mock.patch.object(bs, "_DUMP_SAFE_COLUMNS", old_safe_columns):
                    old_data = ro.dump()
                new_data = ro.dump()
            finally:
                ro.close()
            self.assertIn(secret_name, json.dumps(old_data),
                          "reinjected pre-round-7 allowlist (records.name treated as "
                          "structurally safe) must leak the secret-shaped name")
            self.assertNotIn(secret_name, json.dumps(new_data))

    # -- funnel behavior: single-line CLI exits (--session, verify, path) -

    def test_calibrated_round7_cli_session_echo_redacted(self):
        secret_session = "password=hunter2"
        with tempfile.TemporaryDirectory() as d:
            r = _run_cli(["init"], d)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = _run_cli(["claim", "thing", "--lifetime", "ephemeral", "--objective", "obj",
                          "--session", secret_session], d)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertNotIn(secret_session, r.stdout)
            self.assertIn("[REDACTED]", r.stdout)

    def test_calibrated_round7_cli_verify_problem_redacted(self):
        secret_name = "AKIAIOSFODNN7EXAMPLE"
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                rec = store.claim(secret_name, "persistent", "obj", [])
                store.transition(rec.lifecycle_uuid, rec.version, "parked")
                store.conn.execute("BEGIN IMMEDIATE")
                store.conn.execute("DELETE FROM transitions")
                store.conn.execute("COMMIT")
            finally:
                store.close()
            r = _run_cli(["verify"], d)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertNotIn(secret_name, r.stdout)
            self.assertIn("[REDACTED]", r.stdout)

    def test_calibrated_round7_cli_path_escape_message_redacted(self):
        secret = "password=hunter2"
        with tempfile.TemporaryDirectory() as d:
            real_dir = os.path.join(d, "elsewhere-" + secret)
            os.makedirs(real_dir)
            os.symlink(real_dir, os.path.join(d, ".brothermode"))
            r = _run_cli(["verify"], d)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertNotIn(secret, r.stdout)
            self.assertIn("[REDACTED]", r.stdout)

    # -- GATE A: a generated view must never destroy human prose ------

    def test_calibrated_gateA_damaged_markers_refuse_before_destroying_notes(self):
        # VERIFIED BY ORCHESTRATOR reproduction: render, hand-edit the way
        # a human would (delete the closing END marker line, add personal
        # notes), then render again. Fixed by failing closed the moment
        # the marker count stops being exactly (0,0) or (1,1): the notes
        # must never be touched, not merely "eventually" recovered.
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                store.claim("thing", "ephemeral", "obj", [])
            finally:
                store.close()
            bs.write_state_view(d)
            path = os.path.join(d, "STATE.md")
            with io.open(path, encoding="utf-8") as f:
                rendered = f.read()
            damaged = (rendered.replace(bs._STATE_END, "")
                       + "## My notes\nCALL BOB ABOUT THE CONTRACT\n")
            with io.open(path, "w", encoding="utf-8") as f:
                f.write(damaged)
            with self.assertRaises(bs.OwnershipRefused) as ctx:
                bs.write_state_view(d)
            self.assertEqual(ctx.exception.reason, "view-markers-damaged")
            with io.open(path, encoding="utf-8") as f:
                after = f.read()
            self.assertEqual(after, damaged, "a refusal must leave the file byte-for-byte untouched")
            self.assertIn("CALL BOB ABOUT THE CONTRACT", after)

    def test_calibrated_gateA_backup_saved_before_a_normal_rewrite(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                store.claim("thing", "ephemeral", "obj", [])
            finally:
                store.close()
            bs.write_state_view(d)
            path = os.path.join(d, "STATE.md")
            with io.open(path, encoding="utf-8") as f:
                first = f.read()
            with mock.patch.object(bs, "_warn") as warn_mock:
                bs.write_state_view(d)
            backups = glob.glob(path + ".bak-*")
            self.assertEqual(len(backups), 1, "exactly one backup on a normal re-render")
            with io.open(backups[0], encoding="utf-8") as f:
                backed_up = f.read()
            self.assertEqual(backed_up, first, "the backup must hold the PREVIOUS content verbatim")
            # Compare against each ARGUMENT, not str(call): str() of a mock call
            # renders through repr, which doubles every backslash, so a Windows
            # path can never match itself. POSIX paths contain no backslashes,
            # which is the only reason this passed everywhere else.
            reported = [str(arg) for call in warn_mock.call_args_list for arg in call.args]
            # Compare the BASENAME, not the full path. Two Windows-only reasons,
            # both of which have now failed CI once each:
            #   1. str() of a mock call renders through repr and doubles every
            #      backslash, so a Windows path never matches itself. That is why
            #      this reads call.args rather than str(call).
            #   2. The containment funnel resolves paths, and Windows hands out
            #      the 8.3 short form (C:\Users\RUNNER~1\...) where realpath
            #      returns the long form (C:\Users\runneradmin\...). Same
            #      directory, two spellings, so a full-path substring test fails
            #      even though the correct file was reported.
            # The basename carries the microsecond stamp, so it is still specific
            # to THIS backup and the assertion keeps its meaning: the tool must
            # name the backup it just wrote.
            wanted = os.path.basename(backups[0])
            self.assertTrue(any(wanted in msg for msg in reported),
                             "the backup file must be reported on stderr; wanted %r, got %r"
                             % (wanted, reported))

    # -- D5 (fence sweep, 2026-07-30): STATE.md.bak-* must not breed --------
    # Reproduced again on 2026-07-30 at STATE.md.bak-20260730T055214435189:
    # every render wrote another backup and nothing ever removed one, seven
    # accumulated in fifteen minutes on one machine, and the autosave
    # warning then listed all of them.

    def test_d5_old_backups_are_pruned_beyond_the_keep_count(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                store.claim("thing", "ephemeral", "obj", [])
            finally:
                store.close()
            bs.write_state_view(d)  # first render: nothing to back up yet
            path = os.path.join(d, "STATE.md")
            for _ in range(bs._STATE_BACKUP_KEEP + 3):
                bs.write_state_view(d)
            backups = sorted(glob.glob(path + ".bak-*"))
            self.assertEqual(
                len(backups), bs._STATE_BACKUP_KEEP,
                "must keep exactly the %d most recent backups, found %d: %s"
                % (bs._STATE_BACKUP_KEEP, len(backups), backups))

    def test_d5_pruning_never_touches_a_file_outside_its_own_exact_pattern(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                store.claim("thing", "ephemeral", "obj", [])
            finally:
                store.close()
            bs.write_state_view(d)
            # A decoy that LOOKS like a backup but is not the exact shape
            # this code itself produces (a human note, or a file from some
            # other tool) -- must never be a deletion candidate.
            decoy = os.path.join(d, "STATE.md.bak-not-a-real-stamp")
            with io.open(decoy, "w", encoding="utf-8") as f:
                f.write("human note, not a real backup\n")
            for _ in range(bs._STATE_BACKUP_KEEP + 3):
                bs.write_state_view(d)
            self.assertTrue(os.path.exists(decoy),
                             "a file not matching the exact STATE.md.bak-<timestamp> "
                             "pattern must never be pruned")
            backups = [n for n in os.listdir(d) if bs._STATE_BACKUP_RE.match(n)]
            self.assertEqual(len(backups), bs._STATE_BACKUP_KEEP)

    def test_d5_prune_logs_each_deletion_at_the_deletion(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                store.claim("thing", "ephemeral", "obj", [])
            finally:
                store.close()
            bs.write_state_view(d)
            for _ in range(bs._STATE_BACKUP_KEEP):
                bs.write_state_view(d)
            # One more render must prune exactly the oldest backup and log
            # it at the moment of that deletion, never batched at the end.
            with mock.patch.object(bs, "_warn") as warn_mock:
                bs.write_state_view(d)
            reported = [str(arg) for call in warn_mock.call_args_list for arg in call.args]
            self.assertTrue(any("pruned old backup" in msg for msg in reported),
                             "each deletion must be logged at the point it happens: %s"
                             % reported)

    def test_calibrated_reinjecting_a_no_op_prune_lets_backups_accumulate_without_bound(self):
        # CALIBRATION: reinject a no-op onto the real PRODUCT symbol
        # _prune_old_state_backups, in-process, so the patch is scoped to
        # this test. Confirms backups accumulate past _STATE_BACKUP_KEEP
        # again -- the exact D5 defect shape -- proving the real call from
        # write_state_view is what enforces the cap.
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                store.claim("thing", "ephemeral", "obj", [])
            finally:
                store.close()
            bs.write_state_view(d)
            path = os.path.join(d, "STATE.md")
            with mock.patch.object(bs, "_prune_old_state_backups", lambda root: None):
                for _ in range(bs._STATE_BACKUP_KEEP + 3):
                    bs.write_state_view(d)
            backups = glob.glob(path + ".bak-*")
            self.assertGreater(
                len(backups), bs._STATE_BACKUP_KEEP,
                "REINJECTION CHECK: with pruning disabled, backups must accumulate "
                "past the cap again (the exact D5 defect shape), proving "
                "_prune_old_state_backups is what enforces it")

    # -- GATE B: the fail-closed redaction promise must actually hold -

    def test_calibrated_gateB_genuinely_absent_bm_telemetry_refuses_state_view(self):
        # "Test with bm_telemetry.py genuinely absent", not merely _REDACT
        # patched to None: only a real, fresh import proves _load_redact()'s
        # own exception-handling path degrades the same way a pre-cleared
        # _REDACT does.
        # The absence is staged in a throwaway copy of tools/, never by moving
        # anything in this checkout. See _tools_mirror_without.
        mirror = _tools_mirror_without(self, "bm_telemetry.py")
        spec = importlib.util.spec_from_file_location(
            "bm_store_gateB_no_telemetry", os.path.join(mirror, "bm_store.py"))
        fresh = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fresh)
        self.assertIsNone(fresh._REDACT, "sanity: a fresh import must fail to load redact")
        with tempfile.TemporaryDirectory() as d:
            store = fresh.Store(d)
            try:
                # Every optional field empty: the exact GATE B scenario,
                # since the pre-fix code only called redact_text() when
                # an optional field happened to be non-empty.
                store.claim("thing", "ephemeral", "", [])
            finally:
                store.close()
            with self.assertRaises(fresh.RedactionUnavailable):
                fresh.write_state_view(d)
            self.assertFalse(os.path.exists(os.path.join(d, "STATE.md")),
                              "a genuinely absent redactor must write NOTHING")

    # -- GATE C: quarantine must not destroy what it promises to preserve -

    def test_calibrated_gateC_sidecars_preserved_even_when_close_deletes_them(self):
        """GATE C (fix-round 7): guards against a newer bundled SQLite
        (3.53.1, shipped with a recent Python 3.13) whose Connection.close()
        deletes stale -wal/-shm sidecar files as part of its own cleanup.
        This machine's installed SQLite does not reproduce that on its own
        (the pre-fix ordering already passes
        test_calibrated_gate5_sidecars_are_quarantined_too here), so
        close() is replaced with a fake that deletes the sidecars as a side
        effect, deterministically simulating the version-dependent behavior
        without depending on which SQLite is actually installed."""
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            path = store.path
            real_conn = store.conn
            # Release the live connection BEFORE writing the sidecars. In WAL
            # mode SQLite keeps -shm memory-mapped, and Windows refuses a second
            # write handle on a mapped file (OSError [Errno 22]) where POSIX
            # allows it. This test's subject is what close() does to sidecars
            # that already exist, so writing them after the handle is released
            # preserves the intent and works on every platform.
            real_conn.close()
            with io.open(path + "-wal", "wb") as f:
                f.write(b"wal sidecar bytes, pretend records live here")
            with io.open(path + "-shm", "wb") as f:
                f.write(b"shm sidecar bytes")

            class _DestructiveCloseConn(object):
                def close(self_inner):
                    for suffix in ("-wal", "-shm"):
                        try:
                            os.remove(path + suffix)
                        except OSError:
                            pass

            store.conn = _DestructiveCloseConn()
            try:
                with self.assertRaises(bs.StoreCorrupt) as ctx:
                    store._quarantine_and_raise(sqlite3.DatabaseError("simulated corruption"))
            finally:
                real_conn.close()
            qdir = ctx.exception.quarantine_path
            self.assertTrue(os.path.isdir(qdir))
            with io.open(os.path.join(qdir, "store.sqlite3-wal"), "rb") as f:
                self.assertEqual(f.read(), b"wal sidecar bytes, pretend records live here")
            with io.open(os.path.join(qdir, "store.sqlite3-shm"), "rb") as f:
                self.assertEqual(f.read(), b"shm sidecar bytes")
            self.assertFalse(os.path.exists(path + "-wal"))
            self.assertFalse(os.path.exists(path + "-shm"))

    # -- SOFT D: a hardlink bypasses a symlink-only containment check -

    def test_calibrated_softD_hardlinked_store_file_refused(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            store.close()
            path = store.path
            os.link(path, os.path.join(d, "leak.sqlite3"))
            with self.assertRaises(bs.OwnershipRefused) as ctx:
                bs.Store(d)
            self.assertEqual(ctx.exception.reason, "path-escape")
            self.assertIn("hard link", str(ctx.exception).lower())

    # -- SOFT E: an oversized single decision must truncate, not vanish -

    def test_calibrated_softE_oversized_single_decision_is_truncated_not_dropped(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                rec = store.claim("thing", "ephemeral", "obj", [])
                huge = "x" * 2000  # exceeds the 1200-char decisions_new budget alone
                store.decide(rec.lifecycle_uuid, rec.version, "topic", huge)
                digest = store.render_digest(rec.lifecycle_uuid)
            finally:
                store.close()
            self.assertIn("(truncated)", digest)
            self.assertIn("x" * 50, digest, "the beginning of the oversized decision must survive")
            self.assertNotIn(huge, digest, "the full 2000-char decision must not fit whole")


class TestFixRound8(unittest.TestCase):
    # -- CRITICAL A: schema must be verified, never blindly recreated -

    def test_calibrated_criticalA_dropped_table_reopen_refuses_not_grants(self):
        # VERIFIED BY ORCHESTRATOR reproduction: claim alpha on api/pay.py,
        # drop the claims table, claim beta on the same path -> GRANTED at
        # exit 0, verify -> healthy. _ensure_schema's CREATE TABLE IF NOT
        # EXISTS ran unconditionally on every open and silently recreated
        # the dropped table empty instead of catching it.
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            store.claim("alpha", "ephemeral", "obj", ["api/pay.py"], session_id="s1")
            store.conn.execute("BEGIN IMMEDIATE")
            store.conn.execute("DROP TABLE claims")
            store.conn.execute("COMMIT")
            store.close()
            with self.assertRaises(bs.StoreCorrupt) as ctx:
                bs.Store(d)
            self.assertIn("claims", str(ctx.exception))
            self.assertIsNotNone(ctx.exception.quarantine_path)
            self.assertTrue(os.path.isdir(ctx.exception.quarantine_path))

    def test_calibrated_criticalA_cli_reproduction_claim_beta_refused(self):
        # The coordinator's exact CLI-level reproduction, end to end.
        with tempfile.TemporaryDirectory() as d:
            _run_cli(["init"], d)
            r1 = _run_cli(["claim", "alpha", "--lifetime", "ephemeral",
                          "--objective", "o", "--files", "api/pay.py"], d)
            self.assertEqual(r1.returncode, 0, r1.stdout + r1.stderr)
            store = bs.Store(d)
            store.conn.execute("BEGIN IMMEDIATE")
            store.conn.execute("DROP TABLE claims")
            store.conn.execute("COMMIT")
            store.close()
            r2 = _run_cli(["claim", "beta", "--lifetime", "ephemeral",
                          "--objective", "o", "--files", "api/pay.py"], d)
            self.assertNotEqual(r2.returncode, 0,
                                 "claim beta on the same file after a dropped table must "
                                 "NOT be granted at exit 0")
            r3 = _run_cli(["verify"], d)
            self.assertNotEqual(r3.returncode, 0,
                                 "verify must not report healthy against a quarantined store")

    def test_calibrated_criticalA_wrong_schema_version_quarantines(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            store.claim("thing", "ephemeral", "obj", [])
            store.conn.execute("BEGIN IMMEDIATE")
            store.conn.execute("UPDATE meta SET value='999' WHERE key='schema_version'")
            store.conn.execute("COMMIT")
            store.close()
            with self.assertRaises(bs.StoreCorrupt) as ctx:
                bs.Store(d)
            self.assertIn("schema_version", str(ctx.exception))

    def test_calibrated_criticalA_readonlystore_also_refuses_dropped_table(self):
        # The schema door is not writer-only: a diagnostic (dashboard,
        # dump, verify) opened against a damaged existing store must also
        # quarantine rather than report a healthy, half-real store.
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            store.claim("alpha", "ephemeral", "obj", ["api/pay.py"])
            store.conn.execute("BEGIN IMMEDIATE")
            store.conn.execute("DROP TABLE digests")
            store.conn.execute("COMMIT")
            store.close()
            with self.assertRaises(bs.StoreCorrupt):
                bs.ReadOnlyStore(d)

    def test_calibrated_criticalA_healthy_store_reopens_without_quarantine(self):
        # Sanity/regression guard: schema verification must not be a
        # false-positive trap for the ordinary, unmodified case.
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            rec = store.claim("thing", "ephemeral", "obj", [])
            store.close()
            store2 = bs.Store(d)
            try:
                refetched = store2.get(rec.lifecycle_uuid)
                self.assertEqual(refetched.name, "thing")
            finally:
                store2.close()
            self.assertEqual(glob.glob(bs.store_path(d) + ".quarantine-*"), [])

    # -- IMPORTANT: OperationalError classification --------------------

    def test_calibrated_important_missing_table_operational_error_quarantines(self):
        # Every OperationalError used to print "busy or locked, wait and
        # retry", so a missing table (an OperationalError, not a transient
        # one) gave advice that can never work and hid CRITICAL A's own
        # class of defect behind a comforting, wrong message.
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            rec = store.claim("thing", "ephemeral", "obj", [])
            store.conn.execute("BEGIN IMMEDIATE")
            store.conn.execute("DROP TABLE decisions")
            store.conn.execute("COMMIT")
            with self.assertRaises(bs.StoreCorrupt) as ctx:
                store.decide(rec.lifecycle_uuid, rec.version, "t", "x")
            self.assertNotIn("busy", str(ctx.exception).lower())

    def test_calibrated_important_busy_lock_still_says_busy_not_corrupt(self):
        # The transient case must still get the honest, ACTIONABLE advice:
        # this is the regression guard for the classification split itself.
        with tempfile.TemporaryDirectory() as d:
            store0 = bs.Store(d)
            store0.close()
            path = bs.store_path(d)
            locker = sqlite3.connect(path, timeout=0, isolation_level=None)
            locker.execute("BEGIN EXCLUSIVE")
            try:
                store = bs.Store(d, busy_timeout_ms=50)
                try:
                    with self.assertRaises(bs.OwnershipRefused) as ctx:
                        store.claim("thing", "ephemeral", "obj", [])
                    self.assertEqual(ctx.exception.reason, "db-busy")
                finally:
                    store.close()
            finally:
                locker.execute("ROLLBACK")
                # Windows keeps the temp directory locked until every handle
                # on the db file is gone, this deliberate locker included.
                # The sibling test at the top of this file already closes its
                # locker; this one did not, and POSIX hid the difference.
                locker.close()

    # -- IMPORTANT: checkpoint/decide must echo the new version ---------

    def test_calibrated_important_checkpoint_and_decide_report_new_version(self):
        # checkpoint and decide bumped the record's version but returned
        # only a decision/digest seq number, never the new version, so the
        # founder's very next command (which needs --version) failed
        # stale-identity against the version it was never told about.
        with tempfile.TemporaryDirectory() as d:
            r = _run_cli(["init"], d)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = _run_cli(["claim", "thing", "--lifetime", "ephemeral", "--objective", "o"], d)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            uuid1 = re.search(r"lifecycle ([0-9a-f]+)", r.stdout).group(1)
            r_cp = _run_cli(["checkpoint", uuid1, "--version", "1", "--next", "n"], d)
            self.assertEqual(r_cp.returncode, 0, r_cp.stdout + r_cp.stderr)
            self.assertIn("version 2", r_cp.stdout)
            r_dec = _run_cli(["decide", uuid1, "--version", "2", "--topic", "t", "--text", "x"], d)
            self.assertEqual(r_dec.returncode, 0, r_dec.stdout + r_dec.stderr)
            self.assertIn("version 3", r_dec.stdout)
            # The version just printed must actually work for the next call.
            r_cp2 = _run_cli(["checkpoint", uuid1, "--version", "3", "--next", "n2"], d)
            self.assertEqual(r_cp2.returncode, 0, r_cp2.stdout + r_cp2.stderr)

    # ttl_hours was deleted in the prerelease fix round: the law promised a
    # fence past its TTL is treated as released, and nothing anywhere
    # expired anything (a claim with a TTL of 0.36 seconds still blocked a
    # second claim a second later, VERIFIED BY ORCHESTRATOR). The column,
    # CLEAR_TTL_HOURS, the CLI --ttl-hours flag, and the reclaim branch are
    # all gone; the two tests that exercised clearing it
    # (test_calibrated_important_ttl_hours_can_be_cleared_on_reclaim,
    # test_calibrated_important_cli_ttl_hours_flag_with_no_value_clears)
    # are deleted with the feature, not left testing a symbol that no
    # longer exists.

    # -- IMPORTANT: verify's view check must not pass vacuously --------

    def test_calibrated_important_verify_view_check_is_not_vacuous_on_short_names(self):
        # A substring test ("name in rendered") is satisfied vacuously by
        # any short name that happens to occur inside OTHER rendered text
        # (state words, punctuation); checking the lifecycle uuid prefix
        # instead cannot false-positive that way.
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                store.claim("a", "ephemeral", "obj", [])
            finally:
                store.close()
            bs.write_state_view(d)
            self.assertEqual(bs.verify(d), [])

    def test_calibrated_important_verify_view_check_still_catches_a_real_gap(self):
        # GATE B (prerelease fix round): verify's view check must read the
        # file ON DISK, not a fresh render computed from the same live rows
        # it just read (that comparison can never disagree with itself,
        # which is why the old check caught nothing). Writing a STALE, real
        # STATE.md directly, with no mention of this record at all, is what
        # a genuinely out-of-date file looks like; only a check that opens
        # the real file can catch it.
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                store.claim("thing", "ephemeral", "obj", [])
            finally:
                store.close()
            stale = "%s\nNo records.\n%s\n" % (bs._STATE_BEGIN, bs._STATE_END)
            with io.open(os.path.join(d, "STATE.md"), "w", encoding="utf-8") as f:
                f.write(stale)
            problems = bs.verify(d)
            self.assertTrue(any("does not appear" in p for p in problems), problems)

    def test_calibrated_gate_b_view_check_reads_the_real_file(self):
        # GATE B (prerelease fix round): reproduces the exact executed
        # scenario the fix-round writeup names: deleting STATE.md entirely
        # left verify() reporting healthy. Then CALIBRATES it by reinjecting
        # the old, tautological shape (re-render fresh and compare a live
        # document against itself) onto the exact PRODUCT symbol verify()
        # calls, and confirms the SAME missing-file scenario is now missed.
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                store.claim("thing", "ephemeral", "obj", [])
            finally:
                store.close()
            bs.write_state_view(d)
            os.remove(os.path.join(d, "STATE.md"))
            problems = bs.verify(d)
            self.assertTrue(any("STATE.md does not exist" in p for p in problems), problems)

            original = bs._verify_view_reflects_active_records

            def _old_tautological_check(store, root):
                rendered = bs.render_state_md(root)
                probs = []
                for r in bs._exec(store,
                        "SELECT lifecycle_uuid, name FROM records WHERE state='active'").fetchall():
                    if r["lifecycle_uuid"][:8] not in rendered:
                        probs.append(
                            "active record %r (%s) does not appear in the generated "
                            "STATE.md view" % (r["name"], r["lifecycle_uuid"][:8]))
                return probs

            bs._verify_view_reflects_active_records = _old_tautological_check
            try:
                problems2 = bs.verify(d)  # STATE.md is STILL deleted from disk
                self.assertEqual(
                    problems2, [],
                    "REINJECTION CHECK: the old tautological check (re-render fresh "
                    "and compare it against itself) must report healthy even though "
                    "STATE.md is missing from disk entirely (this is GATE B); if "
                    "this assertion fails, the test is not calibrated")
            finally:
                bs._verify_view_reflects_active_records = original


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

class TestConnectionLifecycle(unittest.TestCase):
    """The Windows CI defect this class guards against (GitHub Actions run
    18, commit 7c2e0ec, job 'store (windows-latest, 3.x)'): a Store's
    sqlite3 connection left open when its containing directory was removed
    raised PermissionError: [WinError 32] on Windows, because Windows locks
    an open file handle against deletion. POSIX (macOS, Linux) enforces no
    such lock, so os.unlink/shutil.rmtree silently succeed there even with
    the exact same leak; that is why every macOS/Linux CI leg passed and
    only Windows caught it. Establishing scope for this fix-round: a grep
    for every Store(/ReadOnlyStore( construction site across bm_store.py,
    bm_autosave.py, and their three test files found 12 real leak sites
    (11 direct bs.init_project(...) calls whose returned Store was
    discarded unclosed, one inside the product CLI command cmd_init
    itself), plus one exception-path leak in the random-sequence generator
    (TestStoreInvariantsUnderRandomSequences._run_sequence) whose
    store.close() sat after the loop and was skipped whenever a mid-loop
    AssertionError fired, which its own two calibration tests deliberately
    trigger. Every dropped connection this class checks used the raw
    sqlite3.Connection ProgrammingError it raises once truly closed, not a
    filesystem check, precisely because that is the ONE assertion capable
    of failing on every platform including this one."""

    def test_calibrated_store_context_manager_closes_on_normal_exit(self):
        d = tempfile.mkdtemp()
        try:
            with bs.Store(d) as store:
                raw_conn = store.conn
                store.claim("thing", "ephemeral", "obj", [])
            # CALIBRATION: raw_conn is the actual sqlite3.Connection,
            # captured before __exit__ runs. sqlite3 only raises
            # ProgrammingError here once the OS-level handle behind it is
            # genuinely released; if close() ever regresses to a no-op (the
            # exact leak class this fix-round exists for), raw_conn stays
            # usable and this assertion fails, on every platform, not only
            # Windows.
            with self.assertRaises(sqlite3.ProgrammingError):
                raw_conn.execute("SELECT 1")
            self.assertIsNone(store.conn,
                               "Store.__exit__ must null self.conn, not just close it")
            # The literal Windows failure shape from the CI log:
            # tempfile.TemporaryDirectory cleanup calls os.unlink on every
            # file, store.sqlite3 included. POSIX allows this regardless of
            # the leak (see the class docstring above), so this line cannot
            # fail on this platform, but it is exactly the operation that
            # raised PermissionError in the CI log, and it must keep
            # working now that the connection really is closed.
            shutil.rmtree(d)
            self.assertFalse(os.path.exists(d))
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_calibrated_store_context_manager_closes_when_the_body_raises(self):
        # _run_sequence (TestStoreInvariantsUnderRandomSequences) proved
        # this exact gap for real: its store.close() used to sit AFTER the
        # loop, so an AssertionError raised mid-loop (precisely what that
        # class's own calibration tests deliberately trigger) skipped it
        # and leaked. A context manager closes on the way out regardless of
        # how the block exits, which is the whole reason to prefer it over
        # a bare call at the end of a function body.
        d = tempfile.mkdtemp()
        try:
            raw_conn = [None]
            with self.assertRaises(ValueError):
                with bs.Store(d) as store:
                    raw_conn[0] = store.conn
                    raise ValueError("simulated failure inside the with-block")
            with self.assertRaises(sqlite3.ProgrammingError):
                raw_conn[0].execute("SELECT 1")
            shutil.rmtree(d)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_calibrated_readonly_store_context_manager_closes_on_normal_exit(self):
        d = tempfile.mkdtemp()
        try:
            bs.init_project(d).close()
            with bs.ReadOnlyStore(d) as store:
                raw_conn = store.conn
            with self.assertRaises(sqlite3.ProgrammingError):
                raw_conn.execute("SELECT 1")
            self.assertIsNone(store.conn)
            shutil.rmtree(d)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_close_is_idempotent(self):
        # A caller cannot always tell whether an earlier try/finally already
        # closed a store (e.g. a shared helper called from more than one
        # cleanup path); a second close() must be a harmless no-op, not a
        # crash on an already-None connection.
        d = tempfile.mkdtemp()
        try:
            store = bs.Store(d)
            store.close()
            store.close()
            self.assertIsNone(store.conn)
        finally:
            shutil.rmtree(d, ignore_errors=True)

class TestTransitionsIndexOnOpen(unittest.TestCase):
    """The measured optimization's other half (prerelease fix round): the
    transitions index must be created on EVERY open, not only inside
    _DDL, because a DDL-only index is a silent no-op for a store that
    already existed before the index was added (_ensure_schema, the only
    thing that runs _DDL, only runs for a BRAND NEW file)."""

    def test_index_recreated_on_reopen_of_a_pre_existing_store(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            store.claim("thing", "ephemeral", "obj", [])
            store.close()
            # Simulate a store that predates the index.
            older = bs.Store(d)
            older.conn.execute("DROP INDEX IF EXISTS transitions_lifecycle_uuid_idx")
            older.close()
            reopened = bs.Store(d)
            try:
                names = {r["name"] for r in reopened.conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='index'").fetchall()}
                self.assertIn("transitions_lifecycle_uuid_idx", names,
                              "opening an EXISTING store must (re)create the index, "
                              "not only a brand-new one")
            finally:
                reopened.close()

    def test_calibrated_ddl_only_index_is_a_silent_noop_on_existing_store(self):
        # CALIBRATION: reinject the old, DDL-only shape by neutralizing the
        # PRODUCT method _ensure_indexes, drop the index from an already
        # existing store, and confirm the calibrated check now fails: the
        # index stays gone on the next open, exactly the trap the reviewer
        # proved (adding an index to the DDL alone is a silent no-op on an
        # existing store, because schema creation does not run there).
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            store.claim("thing", "ephemeral", "obj", [])
            store.close()
            original = bs.Store._ensure_indexes
            bs.Store._ensure_indexes = lambda self: None
            try:
                older = bs.Store(d)
                older.conn.execute("DROP INDEX IF EXISTS transitions_lifecycle_uuid_idx")
                older.close()
                reopened = bs.Store(d)
                try:
                    names = {r["name"] for r in reopened.conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='index'").fetchall()}
                    self.assertNotIn(
                        "transitions_lifecycle_uuid_idx", names,
                        "REINJECTION CHECK: with _ensure_indexes neutralized, "
                        "opening an EXISTING store must never recreate a dropped "
                        "index (this is the DDL-only trap); if this assertion "
                        "fails, the test is not calibrated")
                finally:
                    reopened.close()
            finally:
                bs.Store._ensure_indexes = original

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
        # This exercises the compare-and-swap GUARANTEE (checkpoint's own
        # UPDATE ... WHERE version=? matching zero rows), not a separate
        # earlier pre-check: checkpoint() has no standalone "does the
        # version match" comparison before it touches the database.
        # version + 1 (ahead, not behind) still proves the same guarantee
        # catches a mismatch in either direction.
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

class TestGateDDigestFilesSection(unittest.TestCase):
    """GATE D (prerelease fix round): render_digest's '## Files' section
    used to be built from the free-text files_note alone, so a record
    actively holding a live fence rendered "Files: (none)" the moment
    nobody had typed a files_note on a checkpoint: the one field a
    resuming session most needs."""

    def test_files_section_shows_the_real_fence_with_no_files_note(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                rec = store.claim("thing", "ephemeral", "obj",
                                   ["api/pay.py", "api/webhook.py"])
                digest = store.render_digest(rec.lifecycle_uuid)
                self.assertIn("api/pay.py", digest)
                self.assertIn("api/webhook.py", digest)
                self.assertNotIn("## Files\n\n(none)", digest,
                                  "a record holding a live fence must never render "
                                  "Files: (none)")

                # CALIBRATION: reinject the old, notes-only shape by patching
                # the PRODUCT method Store._digest_files_block back to reading
                # files_note alone, and confirm the calibrated check now
                # fails for the GATE D reason: a record with a real fence and
                # no typed files_note renders "(none)".
                original = bs.Store._digest_files_block

                def _old_notes_only(self, lifecycle_uuid, digest_row):
                    text = digest_row["files_note"] if digest_row else ""
                    return text or "(none)"

                bs.Store._digest_files_block = _old_notes_only
                try:
                    digest2 = store.render_digest(rec.lifecycle_uuid)
                    self.assertNotIn(
                        "api/pay.py", digest2,
                        "REINJECTION CHECK: the old notes-only Files section must "
                        "omit the real fence entirely (this is GATE D); if this "
                        "assertion fails, the test is not calibrated")
                    self.assertIn("(none)", digest2)
                finally:
                    bs.Store._digest_files_block = original
            finally:
                store.close()

    def test_files_section_also_shows_a_typed_files_note(self):
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                rec = store.claim("thing", "ephemeral", "obj", ["api/pay.py"])
                store.checkpoint(rec.lifecycle_uuid, rec.version, "next",
                                  files_note="watch the webhook retry path")
                digest = store.render_digest(rec.lifecycle_uuid)
                self.assertIn("api/pay.py", digest)
                self.assertIn("watch the webhook retry path", digest)
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
                              "directives", "transitions", "autosave_receipts"):
                    self.assertIn(table, data)
                    self.assertIsInstance(data[table], list)
                self.assertEqual(len(data["records"]), 1)
                self.assertEqual(len(data["claims"]), 1)
                self.assertEqual(len(data["decisions"]), 1)
                json.dumps(data)  # must be JSON-serializable end to end
            finally:
                store.close()

    def test_dump_never_prints_a_digest(self):
        """FIX ROUND P3. redact_text is pattern based and a hex digest matches
        no pattern, so `bm_store.py dump` printed founder_response_hash and
        nonce_hash verbatim. Reproduced 2026-07-29 against a throwaway store:
        sha256(normalize_text("oui")) recovered the founder's literal answer
        from the dumped digest with a ten-word wordlist. dump is the command
        whose own docstring calls it what a founder pipes into a file or an
        issue, so no digest may appear in it at all."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                c = store.capture_learning_candidate(
                    "explicit_correction", "never force push to main",
                    trigger="pushing to main", action="never force push to main",
                    scope_type="global")
                _approved(store, c["candidate_uuid"], founder_ref="he said oui",
                          severity="gate")
                text = json.dumps(store.dump())
                self.assertNotIn(
                    hashlib.sha256(b"oui").hexdigest(), text)
                for hexish in re.findall(r"[0-9a-f]{64}", text):
                    self.fail("dump printed a 64-hex digest: %s" % hexish)
                self.assertIn("-char digest", text)
                # --raw is the named escape hatch and still returns everything.
                raw = json.dumps(store.dump(raw=True))
                self.assertTrue(re.search(r"[0-9a-f]{64}", raw))


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

    # -- GATE C (prerelease fix round): a missing dependency must never --
    # -- report committed work as failed --------------------------------

    def test_calibrated_prerelease_gateC_missing_telemetry_commits_and_reports_cleanly(self):
        # GATE C (prerelease fix round, distinct from the fix-round-5 GATE C
        # above): with bm_telemetry.py GENUINELY absent (a real missing file
        # in a throwaway copy of tools/, the same pattern
        # test_calibrated_gateB_genuinely_absent_bm_telemetry_refuses_state_view
        # uses, not merely _REDACT patched
        # to None), a claim used to COMMIT and then the CLI exited with an
        # UNCAUGHT RedactionUnavailable from inside main()'s own
        # OwnershipRefused handler (it tried to print "refused (...)",
        # which itself calls redact_text() on the very message it is
        # printing), reporting an already-committed success as though the
        # command had crashed. The fix must report exit 1 (an environment
        # problem), never exit 2 ("refused", implying nothing happened) and
        # never an uncaught traceback, and the record must have actually
        # committed, verified independently below through the REAL bm_store in
        # this checkout, which never lost its telemetry module.
        mirror = _tools_mirror_without(self, "bm_telemetry.py")
        crippled_cli = os.path.join(mirror, "bm_store.py")
        with tempfile.TemporaryDirectory() as d:
            # `init` itself prints a confirmation through the same redacted
            # funnel, so it degrades exactly like `claim` does; both are
            # exercised so the fix is proven general, not special-cased to
            # one command.
            r_init = _run_cli(["init"], d, script=crippled_cli)
            r_claim = _run_cli(
                ["claim", "thing", "--lifetime", "ephemeral", "--objective", "obj",
                 "--session", "s1"], d, script=crippled_cli)
            for label, r in (("init", r_init), ("claim", r_claim)):
                self.assertNotIn("Traceback", r.stderr,
                                  "%s: an uncaught exception leaked past main(): %s"
                                  % (label, r.stderr))
                self.assertNotEqual(
                    r.returncode, 2,
                    "%s: work that already committed must never be reported with "
                    "the 'refused' exit code: %s" % (label, r.stdout + r.stderr))
                self.assertEqual(
                    r.returncode, 1,
                    "%s: a broken redactor is an environment problem (exit 1), not "
                    "a business refusal (exit 2) or a silent success (exit 0), for "
                    "work that already committed: %s" % (label, r.stdout + r.stderr))
            # Independently verify, with the REAL telemetry restored, that
            # both the store and the claim actually committed despite the
            # degraded reports above.
            store = bs.ReadOnlyStore(d)
            try:
                names = [r["name"] for r in store.dump()["records"]]
            finally:
                store.close()
            self.assertIn("thing", names,
                          "the claim must have committed even though printing its "
                          "confirmation could not be redacted")

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
            bs.write_state_view(d)
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
                    "version, created_at, updated_at) VALUES "
                    "(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    ("deadbeefcafe", "two", "ephemeral", "active", "obj2", "", "s2",
                     "", "", "", 1, ts, ts))
                conn.execute(
                    "INSERT INTO claims (lifecycle_uuid, path) VALUES (?,?)",
                    ("deadbeefcafe", "a/b.py"))
                conn.execute("COMMIT")
            finally:
                store.close()
            problems = bs.verify(d)
            self.assertTrue(any("overlap" in p for p in problems), problems)

    def test_verify_scrubs_a_path_shaped_record_name_in_its_own_problems(self):
        """LOOP 5: verify() problem strings embed records.name and
        claims.path RAW, both scrub-only columns under export_column. This
        is the 'corrupted-store verify output' canary check the plan's
        attack prompt names explicitly: an invariant violation must not be
        the one path that leaks a founder-typed name or path unmasked."""
        canary_path = "/Users/jane.doe/Clients/CANARY-Acme-secret"
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                store.claim("one", "ephemeral", "obj", ["a/b.py"], session_id="s1")
                conn = store.conn
                conn.execute("BEGIN IMMEDIATE")
                ts = bs.now_iso()
                conn.execute(
                    "INSERT INTO records (lifecycle_uuid, name, lifetime, state, "
                    "objective, owner, session_id, tier, check_cmd, evidence, "
                    "version, created_at, updated_at) VALUES "
                    "(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    ("deadbeefcafe", canary_path, "ephemeral", "active", "obj2",
                     "", "s2", "", "", "", 1, ts, ts))
                conn.execute(
                    "INSERT INTO claims (lifecycle_uuid, path) VALUES (?,?)",
                    ("deadbeefcafe", "a/b.py"))
                conn.execute("COMMIT")
            finally:
                store.close()
            problems = bs.verify(d)
            self.assertTrue(any("overlap" in p for p in problems), problems)
            for p in problems:
                self.assertNotIn(canary_path, p,
                                 "verify() leaked a path-shaped record name "
                                 "unmasked: %r" % p)
                self.assertNotIn("Clients/CANARY-Acme-secret", p)

    # -- GATE 4 (release-blockers spec, 2026-07-26) --------------------

    def test_gate4_missing_state_md_remedy_names_an_absolute_resolvable_path(self):
        # This project is installed once and used FROM other projects'
        # roots, so a hardcoded RELATIVE "tools/bm_store.py" in a printed
        # remedy names a path that does not exist at the affected root at
        # all. The remedy must name THIS file's own absolute path instead
        # (the same shape bm_autosave.py's recover nudge already uses).
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                store.claim("thing", "ephemeral", "obj", [])
            finally:
                store.close()
            problems = bs.verify(d)
            self.assertTrue(any("STATE.md does not exist" in p for p in problems), problems)
            remedy = next(p for p in problems if "STATE.md does not exist" in p)
            named_path = remedy.split("run `python3 ", 1)[1].split(" dashboard`", 1)[0]
            self.assertTrue(os.path.isabs(named_path),
                             "the remedy's own command must be runnable regardless of "
                             "the caller's cwd or which project's root triggered it: %r"
                             % remedy)
            self.assertTrue(os.path.exists(named_path), remedy)
            self.assertEqual(os.path.realpath(named_path),
                              os.path.realpath(os.path.join(HERE, "bm_store.py")))

class TestInitProject(unittest.TestCase):
    def test_init_creates_store_and_appends_git_exclude(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, ".git", "info"))
            bs.init_project(d).close()
            self.assertTrue(os.path.exists(bs.store_path(d)))
            exclude_path = os.path.join(d, ".git", "info", "exclude")
            with io.open(exclude_path, encoding="utf-8") as f:
                content = f.read()
            for wanted in (".brothermode/", "threads/", "STATE.md"):
                self.assertIn(wanted, content)
            bs.init_project(d).close()  # idempotent
            with io.open(exclude_path, encoding="utf-8") as f:
                content2 = f.read()
            self.assertEqual(content2.count(".brothermode/"), 1)

    def test_init_without_git_dir_does_not_create_exclude(self):
        with tempfile.TemporaryDirectory() as d:
            bs.init_project(d).close()
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
            bs.init_project(d).close()
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

    # -- BLOCKER 2 (release-blockers spec, 2026-07-26): dashboard surfaces owner --

    def test_blocker2_dashboard_surfaces_the_owning_session(self):
        # Reproduced: the owning session id appeared ZERO times in the
        # dashboard (and zero times in any thread file), so a human could
        # not tell who held a record without dumping the database.
        with tempfile.TemporaryDirectory() as d:
            _run_cli(["init"], d)
            _run_cli(["claim", "thing", "--lifetime", "ephemeral", "--objective", "obj",
                      "--session", "holder-session-42"], d)
            r = _run_cli(["dashboard"], d)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("holder-session-42", r.stdout,
                          "the owning session id must be visible in the dashboard")
            self.assertIn("owner-session:", r.stdout)

    # -- GATE 5 (release-blockers spec, 2026-07-26): unknown flags refused --

    def test_gate5_claim_refuses_an_unrecognized_flag(self):
        with tempfile.TemporaryDirectory() as d:
            _run_cli(["init"], d)
            r = _run_cli(["claim", "thing", "--lifetime", "ephemeral",
                          "--objectve", "typo'd flag name"], d)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("unrecognized flag", r.stdout)
            r_dump = _run_cli(["dump"], d)
            data = json.loads(r_dump.stdout)
            self.assertEqual(data["records"], [],
                              "a refused claim must create nothing, not a half-formed record")

    def test_gate5_transition_refuses_an_unrecognized_flag(self):
        with tempfile.TemporaryDirectory() as d:
            _run_cli(["init"], d)
            _run_cli(["claim", "thing", "--lifetime", "ephemeral", "--objective", "obj",
                      "--session", "s1"], d)
            r_dump = _run_cli(["dump"], d)
            luid = json.loads(r_dump.stdout)["records"][0]["lifecycle_uuid"]
            ver = json.loads(r_dump.stdout)["records"][0]["version"]
            r = _run_cli(["park", luid, "--version", str(ver), "--sesion", "s1"], d)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("unrecognized flag", r.stdout)
            still = json.loads(_run_cli(["dump"], d).stdout)["records"][0]
            self.assertEqual(still["state"], "active",
                             "a refused park (typo'd --session) must change nothing")

    def test_calibrated_gate5_reinjecting_a_permissive_flag_check_lets_typos_through(self):
        # CALIBRATION: reinject a no-op onto the real PRODUCT symbol
        # _reject_unknown_flags, and confirm the SAME typo'd flag is now
        # silently accepted (in-process, so the patch is scoped to this
        # test and cannot leak across the subprocess boundary).
        original = bs._reject_unknown_flags
        with tempfile.TemporaryDirectory() as d:
            bs.init_project(d).close()
            with mock.patch.object(bs, "_reject_unknown_flags", lambda *a, **k: None):
                with mock.patch.object(bs, "require_root", lambda *a, **k: (d, "test")):
                    bs.cmd_claim(["thing", "--lifetime", "ephemeral",
                                  "--objectve", "typo'd flag name", "--session", "s1"])
            store = bs.Store(d)
            try:
                data = store.dump()
            finally:
                store.close()
            self.assertEqual(
                len(data["records"]), 1,
                "REINJECTION CHECK: with flag validation disabled, the typo'd "
                "--objectve must still silently create a record (the exact GATE 5 "
                "defect shape), proving the real check above is what refuses it")
            self.assertEqual(data["records"][0]["objective"], "",
                             "the typo'd flag's value must never have reached 'objective'")


# -- D1/D2/D4 (fence sweep, 2026-07-30): a flag in the positional slot ------

class TestFenceSweepPositionalFlagRefusal(unittest.TestCase):
    """D1/D2: `cmd_claim` read `name = argv[0]` BEFORE any flag was
    recognized as a flag, so `claim --help` (argv == ["--help"]) claimed a
    record literally named "--help", and `claim --objective X --files a.py`
    (no positional name at all) claimed one named "--objective". Neither
    ever reached `_reject_unknown_flags`, which only inspects argv[1:].

    SAME-CLASS SWEEP: every other `cmd_*` reading `<name> = argv[0]` right
    after an `if not argv:` usage check had the identical hole --
    `_cmd_transition` (shared by park/resume/complete/adopt, reading
    lifecycle_uuid), cmd_checkpoint, and cmd_decide. All four are fixed by
    the same `_require_positional` helper, so `park --version 3` no longer
    treats "--version" as the lifecycle_uuid either.

    D4 (piggybacked here since it touches the SAME usage lines this class
    already exercises): `--handover "<heading>"` is accepted by every
    _cmd_transition command but appeared in none of their usage text."""

    def test_claim_help_flag_is_refused_not_claimed_as_a_name(self):
        with tempfile.TemporaryDirectory() as d:
            _run_cli(["init"], d)
            r = _run_cli(["claim", "--help"], d)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("usage: claim", r.stdout)
            data = json.loads(_run_cli(["dump"], d).stdout)
            self.assertEqual(data["records"], [],
                              "'--help' must never become a claimed record name")

    def test_claim_with_only_flags_and_no_name_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            _run_cli(["init"], d)
            r = _run_cli(["claim", "--objective", "X", "--files", "a.py"], d)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("usage: claim", r.stdout)
            data = json.loads(_run_cli(["dump"], d).stdout)
            self.assertEqual(data["records"], [],
                              "'--objective' must never become a claimed record name")

    def test_park_with_a_flag_in_the_uuid_slot_is_refused(self):
        # --bogus-flag, not --version, is the one deliberately in argv[0]'s
        # place: _cmd_transition's OWN "--version is required" branch also
        # reprints this same usage text, so a bogus flag that additionally
        # left --version genuinely missing would pass for the wrong reason
        # (masking exactly the D1/D2-class hole this test exists to catch).
        # --bogus-flag together with a real --version 1 isolates the ONE
        # thing under test: argv[0] itself being a flag.
        with tempfile.TemporaryDirectory() as d:
            _run_cli(["init"], d)
            _run_cli(["claim", "thing", "--lifetime", "ephemeral",
                      "--objective", "obj", "--session", "s1"], d)
            r = _run_cli(["park", "--bogus-flag", "--version", "1", "--session", "s1"], d)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("usage: park", r.stdout)
            still = json.loads(_run_cli(["dump"], d).stdout)["records"][0]
            self.assertEqual(still["state"], "active",
                             "a refused park (no lifecycle_uuid) must change nothing")

    def test_checkpoint_with_a_flag_in_the_uuid_slot_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            _run_cli(["init"], d)
            _run_cli(["claim", "thing", "--lifetime", "ephemeral",
                      "--objective", "obj", "--session", "s1"], d)
            r = _run_cli(["checkpoint", "--next", "wire it up"], d)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("usage: checkpoint", r.stdout)
            data = json.loads(_run_cli(["dump"], d).stdout)
            self.assertEqual(data.get("digests", []), [],
                              "a refused checkpoint (no lifecycle_uuid) must record nothing")

    def test_decide_with_a_flag_in_the_uuid_slot_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            _run_cli(["init"], d)
            _run_cli(["claim", "thing", "--lifetime", "ephemeral",
                      "--objective", "obj", "--session", "s1"], d)
            r = _run_cli(["decide", "--topic", "t", "--text", "x"], d)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("usage: decide", r.stdout)
            data = json.loads(_run_cli(["dump"], d).stdout)
            self.assertEqual(data.get("decisions", []), [],
                              "a refused decide (no lifecycle_uuid) must record nothing")

    # -- D4: --handover documented in the usage line that accepts it --------

    def test_park_resume_complete_adopt_usage_documents_handover(self):
        with tempfile.TemporaryDirectory() as d:
            _run_cli(["init"], d)
            for cmd in ("park", "resume", "complete", "adopt"):
                r = _run_cli([cmd], d)
                self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
                self.assertIn("--handover", r.stdout,
                             "%s usage must document --handover" % cmd)

    # -- CALIBRATION -----------------------------------------------------

    def test_calibrated_reinjecting_the_pre_fix_positional_read_lets_claim_and_park_steal_a_flag(self):
        # CALIBRATION: reinject the pre-fix shape onto the real PRODUCT
        # symbol `_require_positional` (shared by claim, park/resume/
        # complete/adopt, checkpoint and decide): the ONLY thing missing is
        # the check that argv[0] is not itself a flag. In-process, so the
        # patch is scoped to this test and cannot leak across the
        # subprocess boundary the other tests above use.
        def _broken_require_positional(argv, print_usage):
            if not argv:
                print_usage()
                sys.exit(2)
            return argv[0]  # THE BUG: no argv[0].startswith("-") check

        original = bs._require_positional
        with tempfile.TemporaryDirectory() as d:
            bs.init_project(d).close()
            with mock.patch.object(bs, "_require_positional", _broken_require_positional):
                with mock.patch.object(bs, "require_root", lambda *a, **k: (d, "test")):
                    bs.cmd_claim(["--help"])
            store = bs.Store(d)
            try:
                data = store.dump()
            finally:
                store.close()
            self.assertEqual(
                len(data["records"]), 1,
                "REINJECTION CHECK: with the positional-flag check removed, "
                "'claim --help' must still silently claim a record named "
                "'--help' (the exact D1/D2 defect shape), proving the real "
                "check in _require_positional is what refuses it")
            self.assertEqual(data["records"][0]["name"], "--help")
        self.assertIs(bs._require_positional, original,
                      "the patch must not leak past its own `with` block")


# ---------------------------------------------------------------------------
# The restored generative test (prerelease fix round). The V1 registry had a
# 320-line generative property test (git a5c27e2) that ran random CLI
# operation sequences and checked seven numbered invariants after every
# step; it was deleted with bm_registry.py itself (c9e3540) because it was
# bound to the V1 JSON-registry shape. It historically found a real defect
# nobody had written down (start stamping a blank template over a live
# digest), and that same commit's own lesson is the one this class exists to
# honor: "CALIBRATION MATTERS MORE THAN THE TEST" - the first V1 generator
# picked operations uniformly at random and exercised almost nothing, and
# reinjecting two known bugs did not make it fire. A generative test that
# cannot fire is worse than none.
#
# This is a STATE MACHINE against the STORE directly (the Python API, not
# the CLI, since the V1 defect this replaces was store-shaped, not CLI-
# shaped), the same reason the V1 rewrite gave: picking legal moves that
# ACTUALLY apply to the model's current belief about each name, with a
# smaller chance of a deliberately illegal one so refuse-don't-guess is
# exercised too. Biased toward REUSE-AFTER-CLOSE and RESTART-WHILE-LIVE by
# closing and reopening a fresh Store handle onto the SAME root a good
# fraction of every step, including with an ACTIVE record mid-life and no
# intervening park/complete: exactly the moment a process restart (a crash,
# a new CLI invocation) actually happens in the real world.
# ---------------------------------------------------------------------------

class TestStoreInvariantsUnderRandomSequences(unittest.TestCase):
    NAMES = ("alpha", "beta")
    # A SMALL shared pool so two different names have a real chance of
    # claiming the SAME path: without this, "no two active claims overlap"
    # can never be violated no matter what is broken, since alpha and beta
    # would never contend for the same file.
    PATHS = ("api/pay.py", "api/webhook.py")

    def _check_invariants(self, store, seed, step, model):
        where = "seed=%d step=%d" % (seed, step)
        rows = store.conn.execute("SELECT * FROM records").fetchall()
        active_rows = [r for r in rows if r["state"] == "active"]

        # At most one ACTIVE record per name (the DB's own UNIQUE INDEX
        # already enforces this; checked again here as a model-level
        # invariant so a reinjected defect that bypasses the DB layer
        # entirely, such as _admit neutralized, is still caught).
        names_seen = {}
        for r in active_rows:
            self.assertNotIn(r["name"], names_seen,
                "%s: two ACTIVE records share name %r (%s and %s)"
                % (where, r["name"], names_seen.get(r["name"]), r["lifecycle_uuid"]))
            names_seen[r["name"]] = r["lifecycle_uuid"]

        # No two ACTIVE claims overlap.
        active_claims = store.conn.execute(
            "SELECT c.lifecycle_uuid AS lifecycle_uuid, c.path AS path FROM claims c "
            "JOIN records r ON r.lifecycle_uuid = c.lifecycle_uuid "
            "WHERE r.state='active'").fetchall()
        for i in range(len(active_claims)):
            for j in range(i + 1, len(active_claims)):
                a, b = active_claims[i], active_claims[j]
                if a["lifecycle_uuid"] == b["lifecycle_uuid"]:
                    continue
                self.assertFalse(
                    bs.paths_overlap(a["path"], b["path"]),
                    "%s: active claims overlap: %s vs %s" % (where, a["path"], b["path"]))

        # Every record's stored state matches its latest transition (or has
        # none and is still active, the just-claimed case).
        for r in rows:
            last = store.conn.execute(
                "SELECT to_state FROM transitions WHERE lifecycle_uuid=? ORDER BY id DESC LIMIT 1",
                (r["lifecycle_uuid"],)).fetchone()
            if last is None:
                self.assertEqual(r["state"], "active",
                    "%s: record %s has no transitions row but is not active"
                    % (where, r["lifecycle_uuid"]))
            else:
                self.assertEqual(last["to_state"], r["state"],
                    "%s: record %s is %r but its latest transition recorded %r"
                    % (where, r["lifecycle_uuid"], r["state"], last["to_state"]))

        # The model's own belief about each name must never point at a
        # lifecycle the store itself has lost track of.
        for name, cur in model.items():
            if cur is None:
                continue
            fresh = store.get(cur["uuid"])
            self.assertIsNotNone(
                fresh, "%s: model believes %s/%s exists but the store has no "
                "such record" % (where, name, cur["uuid"]))

    def _run_sequence(self, seed, steps=50):
        rng = random.Random(seed)
        with tempfile.TemporaryDirectory() as d:
            bs.init_project(d).close()
            store = bs.Store(d)
            # try/finally, not a bare store.close() after the loop (fix-
            # round: found while establishing this leak's real scope): the
            # two calibration tests below deliberately drive _check_
            # invariants to raise AssertionError mid-loop, and a bare close()
            # placed after the loop is skipped entirely when that exception
            # propagates, leaking the handle every time the generator does
            # exactly what it is calibrated to do.
            try:
                model = {n: None for n in self.NAMES}
                for step in range(steps):
                    # REUSE-AFTER-CLOSE / RESTART-WHILE-LIVE bias: close and
                    # reopen a FRESH Store handle onto the SAME root, whether
                    # or not a record is currently ACTIVE (deliberately not
                    # parked or completed first).
                    if rng.random() < 0.25:
                        store.close()
                        store = bs.Store(d)

                    name = rng.choice(self.NAMES)
                    cur = model[name]
                    enabled = ["claim"]
                    if cur is not None:
                        if cur["state"] == "active":
                            enabled += ["park", "park", "complete", "checkpoint",
                                        "checkpoint", "decide"]
                        elif cur["state"] == "parked":
                            enabled += ["resume", "resume"]
                    # A smaller chance of a move that does NOT apply to the
                    # model's current belief, so refuse-don't-guess is
                    # exercised on illegal input too, not only ever-legal
                    # sequences.
                    op = (rng.choice(enabled) if rng.random() > 0.15
                          else rng.choice(["claim", "park", "resume", "complete",
                                           "checkpoint", "decide"]))
                    path = rng.choice(self.PATHS)

                    try:
                        if op == "claim":
                            rec = store.claim(name, "ephemeral", "step %d" % step,
                                               [path], session_id="s1")
                            model[name] = {"uuid": rec.lifecycle_uuid,
                                           "version": rec.version, "state": rec.state}
                        elif op == "park" and cur is not None:
                            rec = store.transition(cur["uuid"], cur["version"], "parked",
                                                    session_id="s1")
                            model[name] = {"uuid": rec.lifecycle_uuid,
                                           "version": rec.version, "state": rec.state}
                        elif op == "resume" and cur is not None:
                            rec = store.transition(cur["uuid"], cur["version"], "active",
                                                    session_id="s1")
                            model[name] = {"uuid": rec.lifecycle_uuid,
                                           "version": rec.version, "state": rec.state}
                        elif op == "complete" and cur is not None:
                            store.transition(cur["uuid"], cur["version"], "complete",
                                              session_id="s1", evidence="ok")
                            # Completed is terminal for this model slot: the
                            # next claim() under the same name starts a brand
                            # new lifecycle, exactly like a real resumed
                            # project.
                            model[name] = None
                        elif op == "checkpoint" and cur is not None:
                            store.checkpoint(cur["uuid"], cur["version"], "next %d" % step)
                            model[name]["version"] = cur["version"] + 1
                        elif op == "decide" and cur is not None:
                            store.decide(cur["uuid"], cur["version"], "topic", "text %d" % step)
                            model[name]["version"] = cur["version"] + 1
                    except (bs.OwnershipRefused, bs.StaleIdentity, ValueError):
                        # A deliberately illegal move, or a legal one that
                        # lost a race against the model's own drifted belief
                        # (an overlap refusal from the shared PATHS pool,
                        # most commonly): refusing is correct, not a test
                        # failure. Re-sync the model from the store's OWN
                        # truth rather than trust what this loop assumed.
                        if cur is not None:
                            fresh = store.get(cur["uuid"])
                            model[name] = ({"uuid": fresh.lifecycle_uuid,
                                            "version": fresh.version, "state": fresh.state}
                                           if fresh is not None else None)

                    self._check_invariants(store, seed, step, model)
            finally:
                store.close()

    def test_random_sequences_hold_invariants(self):
        for seed in range(6):
            self._run_sequence(seed)

    # -- calibration: the generator must actually be ABLE to fire --------

    def test_calibrated_generator_catches_admit_bypassed(self):
        # Reinject a real, historical defect (GATE A, fix-round 3: resume
        # bypassed the SAME admission gate claim() runs, walking straight
        # over another session's fence) by neutralizing the PRODUCT method
        # _admit entirely, and confirm the generator's own overlap
        # invariant fires on at least one seed. If it does not, the
        # generator is decoration, not a test (the V1 lesson this class
        # exists to honor).
        original = bs.Store._admit
        bs.Store._admit = lambda self, *a, **kw: None
        try:
            fired = False
            for seed in range(6):
                try:
                    self._run_sequence(seed)
                except AssertionError:
                    fired = True
                    break
            self.assertTrue(
                fired, "REINJECTION CHECK: with Store._admit neutralized, at least "
                "one seed must produce two active records claiming the same path "
                "(this is the admission-gate class of defect); if this assertion "
                "fails, the generator is not calibrated")
        finally:
            bs.Store._admit = original

    def test_calibrated_generator_catches_find_overlap_bypassed(self):
        # A second, independent known defect: the lower-level detection
        # function _find_overlap itself neutralized (rather than the
        # admission gate that calls it), so no admission path anywhere can
        # see a real conflict. A different product symbol than the test
        # above, proving the generator's overlap invariant is not
        # accidentally tied to one specific patch point.
        original = bs.Store._find_overlap
        bs.Store._find_overlap = lambda self, *a, **kw: None
        try:
            fired = False
            for seed in range(6):
                try:
                    self._run_sequence(seed)
                except AssertionError:
                    fired = True
                    break
            self.assertTrue(
                fired, "REINJECTION CHECK: with Store._find_overlap neutralized, at "
                "least one seed must produce two active records claiming the same "
                "path; if this assertion fails, the generator is not calibrated")
        finally:
            bs.Store._find_overlap = original


# ---------------------------------------------------------------------------
# FINDING 2B (CONFIRMED by execution): generated-file writes were not
# contained. With STATE.md symlinked at an external file, write_state_view
# read the TARGET's bytes and saved them as <root>/STATE.md.bak-<stamp>, an
# ordinary in-repo file a routine `git add -A` then commits.
# ---------------------------------------------------------------------------

class TestFinding2BPathContainment(unittest.TestCase):
    def test_calibrated_finding2b_symlinked_state_md_refused_not_copied(self):
        # The executed reproduction, as a test. Reinjecting the old line
        # (`path = os.path.join(root, "STATE.md")`) makes this fail with
        # "OwnershipRefused not raised", and the assertions below then show
        # the external content sitting in an in-repo STATE.md.bak-* file.
        outside = tempfile.mkdtemp()
        try:
            secret_path = os.path.join(outside, "private-notes.md")
            secret = "PRIVATE CONTENT THAT LIVES OUTSIDE THE PROJECT"
            with io.open(secret_path, "w", encoding="utf-8") as f:
                f.write(secret)
            with tempfile.TemporaryDirectory() as d:
                with bs.Store(d) as store:
                    store.claim("thing", "ephemeral", "obj", [])
                os.symlink(secret_path, os.path.join(d, "STATE.md"))
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    bs.write_state_view(d)
                self.assertEqual(ctx.exception.reason, "path-escape")
                strays = sorted(n for n in os.listdir(d)
                                if n.startswith("STATE.md.bak-"))
                self.assertEqual(strays, [],
                                  "an in-repo backup of a symlink target is exactly the "
                                  "file `git add -A` commits; found: %s" % strays)
                with io.open(secret_path, encoding="utf-8") as f:
                    self.assertEqual(f.read(), secret,
                                      "the external file must be left untouched")
        finally:
            shutil.rmtree(outside, ignore_errors=True)

    def test_finding2b_symlinked_parent_directory_is_refused_too(self):
        # A symlinked LEAF is not the only shape: <root>/threads -> outside
        # makes every path under it an escape while the leaf itself looks
        # like an ordinary new file. The funnel checks each existing
        # component, not just the last one.
        outside = tempfile.mkdtemp()
        try:
            target = os.path.join(outside, "elsewhere")
            os.makedirs(target)
            with tempfile.TemporaryDirectory() as d:
                os.symlink(target, os.path.join(d, "threads"))
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    bs.safe_project_path(d, "threads", "note.md")
                self.assertEqual(ctx.exception.reason, "path-escape")
        finally:
            shutil.rmtree(outside, ignore_errors=True)

    def test_finding2b_traversal_and_absolute_components_refused(self):
        with tempfile.TemporaryDirectory() as d:
            for parts in ((os.pardir, "escape.md"),
                          ("threads", os.pardir, os.pardir, "escape.md")):
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    bs.safe_project_path(d, *parts)
                self.assertEqual(ctx.exception.reason, "path-escape")
            absolute = os.path.join(os.sep, "etc", "passwd")
            with self.assertRaises(bs.OwnershipRefused) as ctx:
                bs.safe_project_path(d, absolute)
            self.assertEqual(ctx.exception.reason, "path-escape",
                              "os.path.join silently lets an absolute component win "
                              "over the root, so it must be refused explicitly")

    def test_finding2b_ordinary_nested_paths_are_allowed(self):
        # The false-positive guard, and it is not hypothetical: a POSIX
        # DIRECTORY always reports st_nlink >= 2 ('.' plus its parent's
        # entry), so running the hardlink check over directory components
        # would refuse every legitimate path on this platform.
        with tempfile.TemporaryDirectory() as d:
            real_root = os.path.realpath(d)
            os.makedirs(os.path.join(d, "threads", "sub"))
            expected = os.path.join(real_root, "threads", "sub", "note.md")
            self.assertEqual(bs.safe_project_path(d, "threads", "sub", "note.md"),
                             expected)
            with io.open(expected, "w", encoding="utf-8") as f:
                f.write("ordinary content")
            self.assertEqual(bs.safe_project_path(d, "threads", "sub", "note.md"),
                             expected, "an existing plain file must still be allowed")
            self.assertEqual(bs.safe_project_path(d, "STATE.md"),
                             os.path.join(real_root, "STATE.md"),
                             "a path that does not exist yet cannot be an escape")

    def test_finding2b_hardlinked_leaf_is_refused(self):
        # The threat a symlink check cannot see (SOFT D's reasoning, applied
        # to generated files): a second, git-visible name sharing the inode.
        with tempfile.TemporaryDirectory() as d:
            leaf = os.path.join(os.path.realpath(d), "STATE.md")
            with io.open(leaf, "w", encoding="utf-8") as f:
                f.write("content")
            os.link(leaf, os.path.join(os.path.realpath(d), "STATE-alias.md"))
            with self.assertRaises(bs.OwnershipRefused) as ctx:
                bs.safe_project_path(d, "STATE.md")
            self.assertEqual(ctx.exception.reason, "path-escape")

    def test_finding2b_write_state_view_still_works_normally(self):
        # Containment must not cost the ordinary path: a real render, a real
        # human-prose backup, and a real splice still happen.
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                store.claim("thing", "ephemeral", "obj", [])
            bs.write_state_view(d)
            state = os.path.join(d, "STATE.md")
            self.assertTrue(os.path.isfile(state))
            with io.open(state, encoding="utf-8") as f:
                first = f.read()
            self.assertIn(bs._STATE_BEGIN, first)
            bs.write_state_view(d)
            strays = [n for n in os.listdir(d) if n.startswith("STATE.md.bak-")]
            self.assertEqual(len(strays), 1,
                              "the second render must still back the previous file up")

    def test_structural_finding2b_root_paths_go_through_safe_project_path(self):
        """Stops call site N+1, which is the whole point.

        This project has already learned that hand-fixing N call sites leaves
        site N+1 open: the database-handle leak (CI run 18, commit 7c2e0ec)
        fixed twelve sites by hand, and the thirteenth, written by someone who
        never read the fix, would have leaked exactly the same way. Finding 2B
        is the same shape one layer down: write_state_view's STATE.md read was
        one of several bare os.path.join(root, ...) sites, and repairing only
        the one that was reproduced would leave the next generated file
        (a handover, a thread note, a report) free to be written through a
        symlink again. So the rule is asserted, not the instances.

        TWO RULES, both derived from the confirmed defect:
          1. os.path.join(<project root>, ...) anywhere in bm_store.py, since
             every root-relative path must be built by safe_project_path.
          2. a write/open sink handed a path built by string concatenation,
             which is how the STATE.md.bak-<stamp> name was assembled: it
             never touched os.path.join at all, so rule 1 alone would have
             missed the exact line that leaked the bytes.

        BLIND SPOTS, stated rather than overclaimed. This rule does NOT catch:
          * a root passed under a name it does not recognize (a local
            rebound as `base`, `d`, `where`); it recognizes `root`,
            `project_root` and any `.root` attribute, which is what this
            codebase actually writes;
          * a path built with pathlib, os.sep.join, or an f-string;
          * concatenation laundered through a helper function before it
            reaches the sink (the taint check is per function, single
            assignment deep, with no cross-function data flow);
          * a caller in another module. bm_threads.py and bm_autosave.py
            build their own root-relative paths and are outside this file's
            scan; safe_project_path is public precisely so they can adopt
            it, and their own suites should assert the same rule.
        """
        exempt_joins = {
            "store_dir": "the store's own directory, which is already run "
                          "through _refuse_if_symlink_escape and "
                          "_refuse_if_hardlinked explicitly by both "
                          "Store.__init__ and ReadOnlyStore.__init__ before "
                          "anything is opened or written",
            # Renamed from _resolve_git_common_dir on 2026-07-27 (finding 5),
            # which now delegates to this. Same single exemption, same stated
            # reason, same two call sites: the function was split to return
            # the per-worktree gitdir (which holds the index) alongside the
            # common dir (which holds info/exclude), not to widen anything.
            "_resolve_git_dirs": "git's own administrative directory, "
                                  "which legitimately lives OUTSIDE the "
                                  "project root in a worktree, so an "
                                  "inside-the-root funnel would refuse a "
                                  "valid checkout; it has its own "
                                  "validation (SOFT G, "
                                  "_looks_like_git_admin_dir)",
        }
        exempt_concat_sinks = {
            "Store._quarantine_and_raise": "the quarantine directory is built "
                                            "from the ALREADY contained store "
                                            "path and is safe by construction: "
                                            "os.makedirs(exist_ok=False) means "
                                            "anything already sitting at that "
                                            "name, a symlink included, raises "
                                            "instead of being written through",
        }
        with io.open(os.path.join(HERE, "bm_store.py"), encoding="utf-8") as f:
            source = f.read()
        root_joins, concat_sinks = _scan_root_path_sites(source)
        bad_joins = [(ln, fn) for ln, fn in root_joins if fn not in exempt_joins]
        bad_sinks = [(ln, fn) for ln, fn in concat_sinks if fn not in exempt_concat_sinks]
        self.assertEqual(bad_joins, [],
                          "os.path.join(<project root>, ...) call site(s) (line, "
                          "enclosing function): %s. Build the path with "
                          "safe_project_path(root, ...) instead, or add the enclosing "
                          "function to `exempt_joins` above with a stated reason."
                          % bad_joins)
        self.assertEqual(bad_sinks, [],
                          "write/open call site(s) handed a concatenated path (line, "
                          "enclosing function): %s. This is the STATE.md.bak-<stamp> "
                          "shape from finding 2B; push the name back through "
                          "safe_project_path(root, name) instead of concatenating onto "
                          "an existing path, or add the enclosing function to "
                          "`exempt_concat_sinks` above with a stated reason."
                          % bad_sinks)

    def test_structural_finding2b_scanner_actually_catches_the_old_code(self):
        # Calibration for the rule above: a check that has never been seen to
        # fail is decoration. Both halves of the ORIGINAL defect are fed back
        # in as source text and must be flagged; the repaired shape must not.
        old_code = (
            "def write_state_view(root):\n"
            "    path = os.path.join(root, 'STATE.md')\n"
            "    with open(path) as f:\n"
            "        existing = f.read()\n"
            "    backup_path = path + '.bak-' + stamp\n"
            "    _atomic_write_text(backup_path, existing)\n")
        old_joins, old_sinks = _scan_root_path_sites(old_code, "old.py")
        self.assertEqual([fn for _ln, fn in old_joins], ["write_state_view"],
                          "the reinjected os.path.join(root, ...) must be flagged")
        self.assertEqual([fn for _ln, fn in old_sinks], ["write_state_view"],
                          "the reinjected concatenated backup path must be flagged")
        new_code = (
            "def write_state_view(root):\n"
            "    path = safe_project_path(root, 'STATE.md')\n"
            "    with open(path) as f:\n"
            "        existing = f.read()\n"
            "    backup_path = safe_project_path(root, 'STATE.md.bak-' + stamp)\n"
            "    _atomic_write_text(backup_path, existing)\n")
        self.assertEqual(_scan_root_path_sites(new_code, "new.py"), ([], []),
                          "the repaired shape must not be flagged, or the rule is "
                          "unusable and will simply be deleted by the next person")


# ---------------------------------------------------------------------------
# FINDING 7 (CONFIRMED): a read-only health check could MOVE the real
# database. ReadOnlyStore reused Store's quarantine verbatim, and everything
# outside a two-string busy allowlist was ASSUMED to be corruption, so the
# SessionStart hook's automatic `verify` could quarantine a healthy store on
# a transient disk, permission or network-volume error.
# ---------------------------------------------------------------------------

class TestFinding7ReadOnlyNeverMoves(unittest.TestCase):
    class _BoomConnection(object):
        """A connection whose every statement fails the way a bad disk does.
        A plain mock is not enough here: the code under test also closes the
        connection, and the test asserts that close actually happened."""

        def __init__(self, error):
            self.error = error
            self.closed = False

        def execute(self, *args, **kwargs):
            raise self.error

        def close(self):
            self.closed = True

    def _seeded_project(self, d):
        with bs.Store(d) as store:
            store.claim("k", "persistent", "IMPORTANT WORK", ["k.py"])
        return bs.store_path(d)

    def test_calibrated_finding7_readonly_never_moves_on_disk_io_error(self):
        # The SessionStart scenario: `verify` runs automatically, the disk
        # hiccups, and the founder's database must still be exactly where it
        # was, byte for byte. Reinjecting the old delegation
        # (`return Store._quarantine_and_raise(self, cause)`) fails this on
        # the sha256 comparison, because the file is gone from that path.
        with tempfile.TemporaryDirectory() as d:
            path = self._seeded_project(d)
            before = _sha256_file(path)
            boom = self._BoomConnection(sqlite3.OperationalError("disk I/O error"))
            with mock.patch.object(bs, "_connect_read_only", return_value=boom):
                with self.assertRaises(bs.StoreCorrupt) as ctx:
                    bs.ReadOnlyStore(d)
            # The file evidence FIRST, deliberately: it is the assertion this
            # test exists for, so a future regression leads with "the bytes
            # moved" rather than with a wording mismatch.
            self.assertTrue(os.path.isfile(path),
                            "the store must still be at its original path")
            self.assertEqual(_sha256_file(path), before,
                              "a read-only diagnostic must leave the database byte for "
                              "byte identical")
            self.assertEqual(glob.glob(path + ".quarantine-*"), [],
                              "a read-only diagnostic must never create a quarantine")
            message = str(ctx.exception)
            self.assertIn("READ-ONLY", message)
            self.assertIn("nothing", message.lower())
            self.assertTrue(boom.closed,
                            "the read-only path must still close its handle, or it "
                            "recreates the Windows leak while fixing this")

    def test_calibrated_finding7_readonly_never_moves_even_real_corruption(self):
        # Even when the file IS genuinely damaged, the read-only path only
        # reports it. Quarantining is a write, and this class has no write
        # authority; the writable open right after proves the capability was
        # not lost, only moved to where it belongs.
        garbage = b"not a real sqlite database, just garbage bytes 1234567890"
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(bs.store_dir(d))
            path = bs.store_path(d)
            with io.open(path, "wb") as f:
                f.write(garbage)
            before = _sha256_file(path)
            with self.assertRaises(bs.StoreCorrupt) as ctx:
                bs.ReadOnlyStore(d)
            self.assertIsNone(ctx.exception.quarantine_path)
            self.assertEqual(_sha256_file(path), before)
            self.assertEqual(glob.glob(path + ".quarantine-*"), [])
            with self.assertRaises(bs.StoreCorrupt) as ctx2:
                bs.Store(d)
            self.assertTrue(ctx2.exception.quarantine_path,
                            "a WRITABLE open must still quarantine real corruption")
            self.assertFalse(os.path.exists(path))

    def test_structural_finding7_readonly_cannot_reach_the_mover(self):
        # Bound to WRITE AUTHORITY, not to a boolean somebody has to
        # remember: ReadOnlyStore does not inherit from Store, so once the
        # explicit delegation is gone there is no path to the mover at all.
        # Patching the mover proves it is never entered, and the patch also
        # removes its raise, so a reinjected delegation fails this test twice.
        self.assertIsNot(bs.ReadOnlyStore._quarantine_and_raise,
                         bs.Store._quarantine_and_raise,
                         "ReadOnlyStore must OVERRIDE the quarantine entry point, "
                         "not reuse the writable store's mover")
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(bs.store_dir(d))
            with io.open(bs.store_path(d), "wb") as f:
                f.write(b"not a real sqlite database, just garbage bytes 1234567890")
            with mock.patch.object(bs.Store, "_quarantine_and_raise") as mover:
                with self.assertRaises(bs.StoreCorrupt):
                    bs.ReadOnlyStore(d)
                self.assertEqual(mover.call_count, 0,
                                  "a read-only store reached the code that moves the "
                                  "founder's database")

    def test_calibrated_finding7_writable_disk_io_error_reports_without_moving(self):
        # The other half: even WITH write authority, an error that does not
        # name corruption is an environment problem, not a verdict on the
        # file. Reinjecting the old rule (quarantine every non-busy
        # OperationalError) fails this on the sha256 comparison.
        with tempfile.TemporaryDirectory() as d:
            path = self._seeded_project(d)
            before = _sha256_file(path)
            store = bs.Store(d)
            try:
                real_conn = store.conn
                boom = self._BoomConnection(sqlite3.OperationalError("disk I/O error"))
                store.conn = boom
                with self.assertRaises(bs.StoreCorrupt) as ctx:
                    bs._exec(store, "SELECT value FROM meta WHERE key='schema_version'")
                self.assertIsNone(ctx.exception.quarantine_path)
            finally:
                store.conn = None
                store.close()
                real_conn.close()
            self.assertEqual(_sha256_file(path), before,
                              "a disk I/O error is not evidence the file is damaged; "
                              "the store must be byte for byte identical")
            self.assertEqual(glob.glob(path + ".quarantine-*"), [])
            self.assertIn("nothing was moved", str(ctx.exception))

    def test_finding7_writable_still_quarantines_named_corruption(self):
        # Regression guard for the classification itself: the capability must
        # survive the narrowing, or this fix has simply disabled quarantine.
        for cause in (sqlite3.DatabaseError("database disk image is malformed"),
                      sqlite3.DatabaseError("file is not a database"),
                      sqlite3.OperationalError("no such table: claims")):
            with tempfile.TemporaryDirectory() as d:
                store = bs.Store(d)
                try:
                    with self.assertRaises(bs.StoreCorrupt) as ctx:
                        store._quarantine_and_raise(cause)
                    self.assertTrue(ctx.exception.quarantine_path,
                                    "%r must still quarantine" % (cause,))
                    self.assertTrue(os.path.isdir(ctx.exception.quarantine_path))
                finally:
                    store.close()

    def test_finding7_classifier_names_both_sides_of_the_line(self):
        # The written-down rule, asserted rather than described in a comment
        # nobody re-reads. Left column moves the file; right column never does.
        quarantines = (
            sqlite3.DatabaseError("file is not a database"),
            sqlite3.DatabaseError("database disk image is malformed"),
            sqlite3.OperationalError("no such table: claims"),
            sqlite3.OperationalError("no such column: lifecycle_uuid"),
            ValueError("store file exists but is zero bytes"),
        )
        reports_only = (
            sqlite3.OperationalError("disk I/O error"),
            sqlite3.OperationalError("unable to open database file"),
            sqlite3.OperationalError("attempt to write a readonly database"),
            sqlite3.OperationalError("database or disk is full"),
            sqlite3.OperationalError("not authorized"),
            sqlite3.OperationalError("database is locked"),
            sqlite3.OperationalError("database is busy"),
            sqlite3.ProgrammingError("Cannot operate on a closed database."),
        )
        for cause in quarantines:
            self.assertTrue(bs._quarantine_is_warranted(cause),
                            "%s(%s) is evidence the FILE is damaged and must still "
                            "quarantine" % (type(cause).__name__, cause))
        for cause in reports_only:
            self.assertFalse(bs._quarantine_is_warranted(cause),
                             "%s(%s) is an environment problem, not a verdict on the "
                             "file; it must never move the founder's database"
                             % (type(cause).__name__, cause))


def _git_env():
    """A git environment with the developer's own global and system config
    NEUTRALIZED. Every cross-check below compares this module's answer with
    real git's answer, and a global core.excludesFile on the machine
    running the suite would make git ignore things this module deliberately
    does not read (see _gitignore_sources), turning a correct comparison
    into a machine-dependent one."""
    return dict(os.environ,
                GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t.com",
                GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t.com",
                GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull,
                GIT_CONFIG_NOSYSTEM="1")


def _git(repo, *args):
    """Decode git's output as UTF-8 EXPLICITLY, never at the machine's locale.

    text=True alone decodes with locale.getpreferredencoding(), which is UTF-8 on
    macOS and Linux and a legacy code page on Windows. Git stores path bytes in
    the index as UTF-8, and bm_store's index parser reads them as UTF-8, so a
    locale-decoded expectation disagreed with a correct parser on Windows only:
    the same filename came back as 'unicode-\ufffd\u4e2d.txt' from the parser and
    'unicode-é\ufffd\xad.txt' from git, and the cross-check failed on four green
    POSIX legs' blind side.

    The parser was right and the test was wrong, which is the important half: the
    shipped code needed no change. surrogateescape rather than strict, because a
    path that genuinely is not valid UTF-8 should surface as a comparison
    mismatch here, not as a decode crash that hides which path caused it."""
    return subprocess.run(["git", "-C", repo] + list(args),
                          capture_output=True, text=True,
                          encoding="utf-8", errors="surrogateescape",
                          env=_git_env())


def _have_git():
    try:
        return subprocess.run(["git", "--version"],
                              capture_output=True).returncode == 0
    except OSError:
        return False


_HAVE_GIT = _have_git()


@unittest.skipUnless(_HAVE_GIT, "git is not installed")
class TestFinding5GitContainment(unittest.TestCase):
    """FINDING 5 (HIGH), external audit 2026-07-27: the raw store holds
    founder objectives, decisions, digests and directives in CLEARTEXT, and
    everything keeping it out of git was a best-effort WRITE to
    .git/info/exclude that was never CHECKED. An exclude rule does not
    untrack an already-tracked file, and the store opened happily when the
    write failed, so a repository that already tracked
    .brothermode/store.sqlite3 committed the founder's raw data on the next
    routine `git add -A`.

    Every test here uses a throwaway git repository under the system temp
    directory. None of them touches this repo, BROTHERMODE_ROOT, or the
    real home directory, and _git_env neutralizes the developer's own git
    config so the cross-checks compare code against git, not against one
    machine's settings."""

    def _repo(self, base, name="repo"):
        repo = os.path.join(base, name)
        os.makedirs(repo)
        r = _git(repo, "init", "-q")
        self.assertEqual(r.returncode, 0, r.stderr)
        return repo

    def _check_ignore(self, repo, rel):
        """Real git's answer for one path: True, False, or a failed test."""
        r = _git(repo, "check-ignore", "-q", "--", rel)
        self.assertIn(r.returncode, (0, 1),
                      "git check-ignore errored (rc=%s): %s" % (r.returncode, r.stderr))
        return r.returncode == 0

    # -- the confirmed defect, reproduced ---------------------------------

    def test_calibrated_finding5_already_tracked_store_is_refused(self):
        """THE REPRODUCTION. A store created before git existed here, then
        swept into the index by an ordinary `git add -A`, is exactly the
        shape the audit describes: every exclude line present and correct
        afterwards, and the raw database staged anyway."""
        with tempfile.TemporaryDirectory() as base:
            repo = os.path.join(base, "repo")
            os.makedirs(repo)
            with bs.Store(repo) as store:      # no git here yet
                store.claim("payments", "ephemeral", "founder objective text", [])
            self.assertEqual(_git(repo, "init", "-q").returncode, 0)
            self.assertEqual(_git(repo, "add", "-A").returncode, 0)

            # The harm itself, asserted before the fix is asserted: git is
            # now tracking the cleartext store.
            tracked = _git(repo, "ls-files").stdout.split()
            self.assertIn(".brothermode/store.sqlite3", tracked, tracked)

            with self.assertRaises(bs.OwnershipRefused) as ctx:
                bs.Store(repo)
            self.assertEqual(ctx.exception.reason, "git-tracked-store")
            msg = str(ctx.exception)
            self.assertIn("rm --cached", msg)
            self.assertIn(".brothermode", msg)

    def test_finding5_untracking_makes_the_refusal_go_away(self):
        """The remediation the refusal names has to actually work, or the
        message is a dead end dressed up as help."""
        with tempfile.TemporaryDirectory() as base:
            repo = os.path.join(base, "repo")
            os.makedirs(repo)
            with bs.Store(repo) as store:
                store.claim("payments", "ephemeral", "obj", [])
            _git(repo, "init", "-q")
            _git(repo, "add", "-A")
            with self.assertRaises(bs.OwnershipRefused):
                bs.Store(repo)
            r = _git(repo, "rm", "--cached", "-r", "--ignore-unmatch", "-q",
                     "--", ".brothermode")
            self.assertEqual(r.returncode, 0, r.stderr)
            with bs.Store(repo) as store:      # must open cleanly now
                self.assertEqual(len(store.identity_by_name("payments")), 1)

    def test_calibrated_finding5_failed_exclude_write_is_refused(self):
        """The second half of the finding: the exclude write is best effort
        and swallows OSError, so a read-only or otherwise unwritable
        .git/info/exclude left the store open and totally unprotected. The
        write failing is simulated by neutralizing it, which is precisely
        what its own except OSError branch does today."""
        with tempfile.TemporaryDirectory() as base:
            repo = self._repo(base)
            with mock.patch.object(bs, "_ensure_git_excludes", lambda root: None):
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    bs.Store(repo)
            self.assertEqual(ctx.exception.reason, "git-exposed-store")
            # Cross-check: real git agrees the store would not be ignored.
            self.assertFalse(self._check_ignore(repo, ".brothermode/store.sqlite3"))

    def test_finding5_negating_gitignore_rule_beats_the_exclude_write(self):
        """A rule this module WROTE is not a rule git OBEYS. .gitignore
        outranks info/exclude, so a re-including pattern silently undoes
        the containment, which is the case a write-only implementation can
        never see."""
        with tempfile.TemporaryDirectory() as base:
            repo = self._repo(base)
            with io.open(os.path.join(repo, ".gitignore"), "w", encoding="utf-8") as f:
                f.write("!.brothermode/\n")
            with self.assertRaises(bs.OwnershipRefused) as ctx:
                bs.Store(repo)
            self.assertEqual(ctx.exception.reason, "git-exposed-store")
            self.assertFalse(self._check_ignore(repo, ".brothermode/store.sqlite3"))

    def test_finding5_store_in_a_subdirectory_of_a_repo_is_refused(self):
        """_ensure_git_excludes only looks at <root>/.git, so a marker in a
        SUBDIRECTORY of a repository gets no exclude file written at all,
        and `git add -A` from the top commits the store with nothing
        objecting. The check walks up instead of looking only where the
        exclude file would have gone."""
        with tempfile.TemporaryDirectory() as base:
            repo = self._repo(base)
            sub = os.path.join(repo, "sub")
            os.makedirs(sub)
            with self.assertRaises(bs.OwnershipRefused) as ctx:
                bs.Store(sub)
            self.assertEqual(ctx.exception.reason, "git-exposed-store")
            self.assertFalse(self._check_ignore(repo, "sub/.brothermode/store.sqlite3"))

    def test_finding5_readonly_diagnostics_refuse_too(self):
        """A diagnostic that reports a healthy store while git is
        committing its cleartext contents is the fix-round 4 failure shape
        again. Refusing is not writing: nothing is moved, renamed or
        created, and the refusal message IS the diagnosis."""
        with tempfile.TemporaryDirectory() as base:
            repo = os.path.join(base, "repo")
            os.makedirs(repo)
            with bs.Store(repo) as store:
                store.claim("payments", "ephemeral", "obj", [])
            _git(repo, "init", "-q")
            _git(repo, "add", "-A")
            before = _sha256_file(os.path.join(repo, ".brothermode", "store.sqlite3"))
            with self.assertRaises(bs.OwnershipRefused) as ctx:
                bs.ReadOnlyStore(repo)
            self.assertEqual(ctx.exception.reason, "git-tracked-store")
            # Refusing must stay non-destructive: same path, same bytes.
            self.assertEqual(
                _sha256_file(os.path.join(repo, ".brothermode", "store.sqlite3")),
                before)

    def test_finding5_refusal_message_survives_the_output_funnel(self):
        """The CLI's output funnel escapes every C0 control character, so a
        refusal carrying a newline reaches the founder as a literal \\x0a
        with the remediation command buried in it. Measured once, in a real
        /tmp repository, and locked here."""
        with tempfile.TemporaryDirectory() as base:
            repo = os.path.join(base, "repo")
            os.makedirs(repo)
            with bs.Store(repo) as store:
                store.claim("payments", "ephemeral", "obj", [])
            _git(repo, "init", "-q")
            _git(repo, "add", "-A")
            with self.assertRaises(bs.OwnershipRefused) as ctx:
                bs.Store(repo)
            msg = str(ctx.exception)
            self.assertNotIn("\n", msg)
            self.assertEqual(msg, bs._sanitize_for_display(msg))

    def test_finding5_unparseable_index_refuses_rather_than_assuming(self):
        with tempfile.TemporaryDirectory() as base:
            repo = self._repo(base)
            with bs.Store(repo) as store:
                store.claim("thing", "ephemeral", "obj", [])
            with io.open(os.path.join(repo, ".git", "index"), "wb") as f:
                f.write(b"NOTANINDEX" + os.urandom(64))
            with self.assertRaises(bs.OwnershipRefused) as ctx:
                bs.Store(repo)
            self.assertEqual(ctx.exception.reason, "git-state-unknown")

    def test_finding5_missing_index_is_not_unknown(self):
        """A repository with no index tracks nothing. That is a real
        answer, not an unknown one, or every `git init` would refuse."""
        with tempfile.TemporaryDirectory() as base:
            repo = self._repo(base)
            self.assertFalse(os.path.exists(os.path.join(repo, ".git", "index")))
            with bs.Store(repo) as store:
                store.claim("thing", "ephemeral", "obj", [])

    # -- the healthy cases must stay healthy -------------------------------

    def test_finding5_healthy_repo_opens_and_git_confirms_it_is_ignored(self):
        with tempfile.TemporaryDirectory() as base:
            repo = self._repo(base)
            with bs.Store(repo) as store:
                store.claim("thing", "ephemeral", "obj", [])
            self.assertTrue(self._check_ignore(repo, ".brothermode/store.sqlite3"))
            self.assertTrue(self._check_ignore(repo, ".brothermode/store.sqlite3-wal"))
            r = _git(repo, "status", "--porcelain")
            self.assertNotIn(".brothermode", r.stdout, r.stdout)

    def test_finding5_no_git_anywhere_is_not_a_refusal(self):
        with tempfile.TemporaryDirectory() as base:
            plain = os.path.join(base, "plain")
            os.makedirs(plain)
            with mock.patch.object(bs, "_enclosing_git_context",
                                    return_value=(None, None, None)):
                with bs.Store(plain) as store:
                    store.claim("thing", "ephemeral", "obj", [])

    def test_finding5_escape_hatch_opens_a_tracked_store_and_warns(self):
        with tempfile.TemporaryDirectory() as base:
            repo = os.path.join(base, "repo")
            os.makedirs(repo)
            with bs.Store(repo) as store:
                store.claim("payments", "ephemeral", "obj", [])
            _git(repo, "init", "-q")
            _git(repo, "add", "-A")
            captured = io.StringIO()
            with mock.patch.dict(os.environ, {bs.SKIP_GIT_CONTAINMENT_ENV: "1"}), \
                 mock.patch.object(sys, "stderr", captured):
                with bs.Store(repo) as store:
                    self.assertEqual(len(store.identity_by_name("payments")), 1)
            self.assertIn(bs.SKIP_GIT_CONTAINMENT_ENV, captured.getvalue())
            self.assertIn("SKIPPED", captured.getvalue())

    # -- the two parsers, cross-checked against real git -------------------

    def test_finding5_index_parser_agrees_with_git_ls_files(self):
        with tempfile.TemporaryDirectory() as base:
            repo = self._repo(base)
            # The long name is sized to the PLATFORM, not to a constant.
            # Windows enforces MAX_PATH at 260 characters unless long paths are
            # explicitly enabled, and the CI temp directory already spends about
            # 50 of those, so a flat 200-character name made `git add -A` die
            # with exit 128 on both Windows legs while every POSIX leg passed.
            # The point of this fixture is that the index parser reads a
            # variable-length path correctly, and that is exercised by any name
            # comfortably longer than the short ones beside it, so shortening it
            # on Windows costs the test nothing.
            budget = 240 - len(repo) if os.name == "nt" else 200
            long_name = "z" * max(20, min(200, budget)) + ".txt"
            names = ["a.txt", "dir/b.txt", "dir/deeper/c d.txt",
                     long_name, "unicode-é中.txt"]
            for rel in names:
                path = os.path.join(repo, *rel.split("/"))
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with io.open(path, "w", encoding="utf-8") as f:
                    f.write("x\n")
            # Carry git's own stderr into the assertion. The previous version
            # asserted only on the return code, so a failure read "128 != 0" and
            # named neither the cause nor the file, which cost a full CI round
            # to diagnose from the outside.
            added = _git(repo, "add", "-A")
            self.assertEqual(
                added.returncode, 0,
                "git add failed (rc=%s). stderr: %s" % (added.returncode,
                                                         (added.stderr or "").strip()))
            # -z, because plain `ls-files` C-quotes any path outside ASCII
            # and the comparison would be against git's DISPLAY form rather
            # than against the bytes actually in the index.
            expected = sorted(p for p in _git(repo, "ls-files", "-z").stdout.split("\0") if p)
            parsed = bs._git_index_tracked_paths(os.path.join(repo, ".git", "index"))
            self.assertIsNotNone(parsed, "the index should have parsed")
            self.assertEqual(sorted(parsed), expected)

    def test_finding5_index_parser_handles_index_version_4(self):
        """Version 4 stores paths prefix-compressed with a varint and no
        padding. A parser that only knows v2/v3 would either return the
        wrong paths or refuse every store in a repo configured this way."""
        with tempfile.TemporaryDirectory() as base:
            repo = self._repo(base)
            for rel in ("dir/aaa.txt", "dir/aab.txt", "dir/deeper/aac.txt"):
                path = os.path.join(repo, *rel.split("/"))
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with io.open(path, "w", encoding="utf-8") as f:
                    f.write("x\n")
            self.assertEqual(_git(repo, "add", "-A").returncode, 0)
            r = _git(repo, "update-index", "--index-version", "4")
            if r.returncode != 0:
                self.skipTest("this git cannot write a version 4 index: %s" % r.stderr)
            with io.open(os.path.join(repo, ".git", "index"), "rb") as f:
                self.assertEqual(int.from_bytes(f.read(8)[4:8], "big"), 4,
                                  "sanity: the index must really be version 4")
            expected = sorted(p for p in _git(repo, "ls-files", "-z").stdout.split("\0") if p)
            parsed = bs._git_index_tracked_paths(os.path.join(repo, ".git", "index"))
            self.assertEqual(sorted(parsed or []), expected)

    def test_finding5_ignore_matcher_agrees_with_git_check_ignore(self):
        """The gitignore subset this module implements, compared case by
        case against real git rather than against its author's belief about
        real git. Any disagreement here is a bug in _git_ignore_decision,
        including a disagreement that would let it call an exposed store
        contained."""
        cases = [
            # (.gitignore body, path, is_dir)
            (".brothermode/\n", ".brothermode/store.sqlite3", False),
            (".brothermode/\n!.brothermode/\n", ".brothermode/store.sqlite3", False),
            ("/.brothermode/\n", "sub/.brothermode/store.sqlite3", False),
            (".brothermode\n", "sub/.brothermode/store.sqlite3", False),
            ("**/.brothermode/\n", "a/b/.brothermode/store.sqlite3", False),
            ("a/**/c\n", "a/b/c", False),
            ("a/**/c\n", "a/c", False),
            ("*.sqlite3\n", ".brothermode/store.sqlite3", False),
            ("*.sqlite3\n!store.sqlite3\n", ".brothermode/store.sqlite3", False),
            ("store.sqlite?\n", ".brothermode/store.sqlite3", False),
            ("store.sqlite[0-9]\n", ".brothermode/store.sqlite3", False),
            ("nothing-matches\n", ".brothermode/store.sqlite3", False),
            ("sub/\n", "sub/.brothermode/store.sqlite3", False),
            ("# a comment\n\n.brothermode/\n", ".brothermode/store.sqlite3", False),
        ]
        for i, (body, rel, is_dir) in enumerate(cases):
            with tempfile.TemporaryDirectory() as base:
                repo = self._repo(base, name="repo%d" % i)
                with io.open(os.path.join(repo, ".gitignore"), "w", encoding="utf-8") as f:
                    f.write(body)
                git_says = self._check_ignore(repo, rel)
                gitdir = os.path.join(repo, ".git")
                ours = bs._git_ignore_decision(repo, gitdir, rel, is_dir)
                self.assertEqual(
                    ours, git_says,
                    "gitignore %r vs path %r: git says ignored=%s, this module "
                    "says %r" % (body, rel, git_says, ours))

    def test_finding5_unreadable_ignore_file_is_unknown_not_ignored(self):
        with tempfile.TemporaryDirectory() as base:
            repo = self._repo(base)
            with mock.patch.object(bs, "_read_gitignore_rules", return_value=None):
                self.assertIsNone(
                    bs._git_ignore_decision(repo, os.path.join(repo, ".git"),
                                            ".brothermode/store.sqlite3", False))

    def test_finding5_worktree_index_is_the_per_worktree_one(self):
        """In a linked worktree the index and info/exclude live in
        DIFFERENT directories. Reading the shared common dir's index would
        answer the tracked question for another worktree entirely."""
        with tempfile.TemporaryDirectory() as base:
            main = os.path.join(base, "main")
            wt = os.path.join(base, "wt")
            os.makedirs(main)
            for cmd in (["init", "-q"], ["commit", "-q", "--allow-empty", "-m", "i"]):
                self.assertEqual(_git(main, *cmd).returncode, 0)
            r = _git(main, "worktree", "add", "-q", wt, "-b", "feature")
            self.assertEqual(r.returncode, 0, r.stderr)
            gitdir, common = bs._resolve_git_dirs(wt)
            self.assertNotEqual(os.path.realpath(gitdir), os.path.realpath(common))
            self.assertTrue(os.path.isfile(os.path.join(gitdir, "index")))
            self.assertEqual(os.path.realpath(common),
                              os.path.realpath(os.path.join(main, ".git")))
            with bs.Store(wt) as store:        # must still open cleanly
                store.claim("thing", "ephemeral", "obj", [])

    def test_finding5_module_still_declares_and_keeps_no_subprocess(self):
        """The subprocess question, decided in code rather than in prose:
        git state is read by PARSING git's own files, so the module keeps
        the no-subprocess property that SECURITY.md publishes, that
        test_bm.py enforces per file, and that bm_telemetry.py explicitly
        relies on when it loads this module by path. If a future round ever
        does reach for subprocess here, this fails first and forces the
        docstring, SECURITY.md and test_bm.py to be corrected in the same
        change."""
        with io.open(os.path.join(HERE, "bm_store.py"), encoding="utf-8") as f:
            source = f.read()
        offenders = [i for i, line in enumerate(source.splitlines(), 1)
                     if re.match(r"^\s*(?:import|from)\s+subprocess\b", line)]
        self.assertEqual(offenders, [], "bm_store.py imports subprocess at line(s) %s, "
                                        "but its docstring, SECURITY.md and test_bm.py "
                                        "all still claim it does not" % offenders)
        self.assertIn("No network, no subprocess", source)


class TestFinding11NestedRepoBoundary(unittest.TestCase):
    """FINDING 11 (MEDIUM): resolve_root prefers ANY ancestor .brothermode
    marker over a NEARER .git boundary, so a nested repository silently
    attaches to a different parent project's store. That precedence is
    DELIBERATE (it is the F2 / F42 / F2b fix, stopping a vendored
    submodule's .git from shadowing the real root), so the fix is an opt-in
    check that REFUSES the ambiguity, never a reordering."""

    def _clean_env(self):
        env = mock.patch.dict(os.environ, {}, clear=False)
        env.start()
        os.environ.pop("BROTHERMODE_ROOT", None)
        self.addCleanup(env.stop)

    def test_calibrated_finding11_nested_repo_refuses_instead_of_attaching(self):
        with tempfile.TemporaryDirectory() as d:
            self._clean_env()
            os.makedirs(os.path.join(d, ".brothermode"))
            nested = os.path.join(d, "vendor", "sub")
            os.makedirs(os.path.join(nested, ".git"))
            with self.assertRaises(bs.OwnershipRefused) as ctx:
                bs.resolve_root(start=nested, refuse_past_git_boundary=True)
            self.assertEqual(ctx.exception.reason, "root-ambiguous")
            msg = str(ctx.exception)
            self.assertIn("BROTHERMODE_ROOT", msg)
            self.assertIn(os.path.realpath(nested), msg)
            self.assertIn(os.path.realpath(d), msg)

    def test_finding11_default_still_prefers_the_marker(self):
        """The F2 / F42 / F2b guarantee, asserted right beside its new
        neighbour: the default is unchanged, so no existing caller starts
        resolving a different root."""
        with tempfile.TemporaryDirectory() as d:
            self._clean_env()
            os.makedirs(os.path.join(d, ".brothermode"))
            nested = os.path.join(d, "vendor", "sub")
            os.makedirs(os.path.join(nested, ".git"))
            root, source = bs.resolve_root(start=nested)
            self.assertEqual(os.path.realpath(root), os.path.realpath(d))
            self.assertEqual(source, "marker")

    def test_finding11_marker_at_the_git_root_is_not_ambiguous(self):
        with tempfile.TemporaryDirectory() as d:
            self._clean_env()
            os.makedirs(os.path.join(d, ".brothermode"))
            os.makedirs(os.path.join(d, ".git"))
            sub = os.path.join(d, "a", "b")
            os.makedirs(sub)
            root, source = bs.resolve_root(start=sub, refuse_past_git_boundary=True)
            self.assertEqual(os.path.realpath(root), os.path.realpath(d))
            self.assertEqual(source, "marker")

    def test_finding11_git_above_the_marker_is_not_ambiguous(self):
        """Only a NEARER .git disagrees. One further up is not a second
        answer: the marker is still the innermost anchor."""
        with tempfile.TemporaryDirectory() as d:
            self._clean_env()
            os.makedirs(os.path.join(d, ".git"))
            inner = os.path.join(d, "inner")
            os.makedirs(os.path.join(inner, ".brothermode"))
            root, source = bs.resolve_root(start=inner, refuse_past_git_boundary=True)
            self.assertEqual(os.path.realpath(root), os.path.realpath(inner))
            self.assertEqual(source, "marker")

    def test_finding11_explicit_env_root_is_exempt(self):
        """BROTHERMODE_ROOT is the answer the refusal asks for, so it
        cannot itself be refused, or the remedy is another dead end."""
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, ".brothermode"))
            nested = os.path.join(d, "vendor", "sub")
            os.makedirs(os.path.join(nested, ".git"))
            with mock.patch.dict(os.environ, {"BROTHERMODE_ROOT": d}):
                root, source = bs.resolve_root(start=nested,
                                                refuse_past_git_boundary=True)
            self.assertEqual(os.path.realpath(root), os.path.realpath(d))
            self.assertEqual(source, "env")

    def test_finding11_require_root_passes_the_flag_through(self):
        with tempfile.TemporaryDirectory() as d:
            self._clean_env()
            os.makedirs(os.path.join(d, ".brothermode"))
            nested = os.path.join(d, "vendor", "sub")
            os.makedirs(os.path.join(nested, ".git"))
            root, source = bs.require_root(start=nested)
            self.assertEqual(os.path.realpath(root), os.path.realpath(d))
            with self.assertRaises(bs.OwnershipRefused) as ctx:
                bs.require_root(start=nested, refuse_past_git_boundary=True)
            self.assertEqual(ctx.exception.reason, "root-ambiguous")


class TestIdentityByName(unittest.TestCase):
    """The lookup bm_threads.py needs. Its _find_record resolves names
    through store.dump(), which is a PRESENTATION view: GATE C's
    default-deny redaction rewrites records.name along with every other
    free-text column, so a thread whose NAME trips the redactor is stored
    correctly and can then never be found again, with its fence stranded
    active forever."""

    # The structural metadata this API is allowed to return, and nothing
    # else. Asserted as an exact set so a future column cannot be added to
    # the SELECT without someone deciding, on purpose, that it is not free
    # text.
    EXPECTED_KEYS = {"lifecycle_uuid", "lifetime", "state", "version",
                     "session_id", "created_at", "updated_at"}

    def test_calibrated_name_that_redaction_rewrites_is_still_findable(self):
        with tempfile.TemporaryDirectory() as d:
            secret_shaped = "AKIAIOSFODNN7EXAMPLE"
            self.assertEqual(bs.valid_name(secret_shaped), secret_shaped,
                              "sanity: this really is a legal record name")
            self.assertNotEqual(bs.redact_text(secret_shaped), secret_shaped,
                                "sanity: this really does trip the redactor")
            with bs.Store(d) as store:
                rec = store.claim(secret_shaped, "ephemeral", "obj", [])
                # THE DEFECT: the presentation view has lost the name, so a
                # name-based lookup through dump() can never match it.
                dumped = [r["name"] for r in store.dump()["records"]]
                self.assertNotIn(secret_shaped, dumped, dumped)
                # THE FIX: identity resolution does not go through display.
                rows = store.identity_by_name(secret_shaped)
                self.assertEqual([r["lifecycle_uuid"] for r in rows],
                                  [rec.lifecycle_uuid])

    def test_returns_structural_metadata_only(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                store.claim("payments", "ephemeral", "a secret objective",
                            [], owner="sonnet", tier="t2",
                            check_cmd="pytest -k secret")
                rows = store.identity_by_name("payments")
            self.assertEqual(len(rows), 1)
            self.assertEqual(set(rows[0]), self.EXPECTED_KEYS)
            blob = json.dumps(rows)
            for free_text in ("a secret objective", "sonnet", "t2", "pytest -k secret",
                              "payments"):
                self.assertNotIn(free_text, blob, blob)

    def test_exact_match_only(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                store.claim("payments", "ephemeral", "obj", [])
                self.assertEqual(store.identity_by_name("payment"), [])
                self.assertEqual(store.identity_by_name("payments2"), [])
                self.assertEqual(store.identity_by_name("PAYMENTS"), [])
                self.assertEqual(store.identity_by_name(""), [])
                self.assertEqual(len(store.identity_by_name("payments")), 1)

    def test_returns_every_match_newest_first(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                first = store.claim("payments", "ephemeral", "obj", [])
                store.transition(first.lifecycle_uuid, first.version, "complete",
                                  evidence="suite green")
                second = store.claim("payments", "ephemeral", "obj", [])
                rows = store.identity_by_name("payments")
                self.assertEqual(len(rows), 2)
                self.assertEqual({r["lifecycle_uuid"] for r in rows},
                                  {first.lifecycle_uuid, second.lifecycle_uuid})
                self.assertGreaterEqual(rows[0]["updated_at"], rows[1]["updated_at"])
                self.assertEqual([r["version"] for r in rows],
                                  [r["version"] for r in rows])

    def test_read_only_store_exposes_it_too(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rec = store.claim("payments", "ephemeral", "obj", [])
            with bs.ReadOnlyStore(d) as ro:
                rows = ro.identity_by_name("payments")
            self.assertEqual([r["lifecycle_uuid"] for r in rows], [rec.lifecycle_uuid])
            self.assertEqual(set(rows[0]), self.EXPECTED_KEYS)


def tearDownModule():
    """BACKSTOP for the Windows leak class (CI run 18, commit 7c2e0ec, job
    'store (windows-latest, 3.x)'). The primary check is per-test, in
    _LeakCheckingResult below; read that docstring for why end-of-run alone is
    too weak to have caught the original defect. This still earns its place: it
    is the only check that runs under `python -m unittest`, and it catches a
    store opened outside any test (a module or class fixture).

    That round fixed twelve known call sites by hand. Twelve hand-fixed sites
    are not a fixed class: this file alone constructs a store 158 times, and
    site 159 will be written by someone who never read the fix. So instead of
    an allowlist of known-good sites, which rots the moment anyone adds a
    test, both checks assert the invariant itself: no store is left open.

    gc.collect() first, deliberately. A store nobody references any more has
    already had its sqlite connection closed by CPython's finalizer, so it
    holds no OS handle and cannot lock a file on any platform; reporting it
    would be a false alarm. What is left after a collection is a store that is
    still REFERENCED and still open, which is precisely the condition that
    raised PermissionError on Windows.

    This fails on macOS and Linux too. That matters more than it sounds: the
    original defect was invisible on both for months because POSIX lets you
    delete a file that still has an open handle, so the only signal was a
    platform most contributors never run.
    """
    gc.collect()
    still_open = list(bs._UNCLOSED) or list(bs._OPEN_STORES)
    if still_open:
        paths = sorted(set(getattr(s, "path", "<unknown>") for s in still_open))
        raise AssertionError(
            "%d store connection(s) were still open when the suite ended, which "
            "is the leak class that failed Windows CI run 18. Close every store "
            "(prefer 'with bs.Store(d) as store:' so it closes even when the "
            "body raises). Still-open store path(s): %s"
            % (len(still_open), ", ".join(paths)))


class _LeakCheckingResult(unittest.TextTestResult):
    """Fails the individual test that leaks, at the moment it leaks.

    A module-level check was tried first and rejected, because it would not
    have caught the original defect. The Windows failure happened INSIDE a
    test: the store was constructed under `with tempfile.TemporaryDirectory()`
    and the directory cleanup ran while the store local was still in scope. By
    the end of the suite that store is long collected, so an end-of-run
    assertion sees a clean set and reports success. Checking after each test is
    what actually reproduces the window in which Windows failed.

    The leaked stores are closed here after being reported. Without that, one
    leak would fail every remaining test in the run and bury its own cause.
    """

    def startTest(self, test):
        # Each test starts from a clean slate, so a failure names the test that
        # actually leaked rather than the first one to run after it.
        bs._TRACK_UNCLOSED = True
        bs._UNCLOSED.clear()
        super(_LeakCheckingResult, self).startTest(test)

    def stopTest(self, test):
        still_open = list(bs._UNCLOSED)
        if still_open:
            paths = sorted(set(getattr(s, "path", "<unknown>") for s in still_open))
            for s in still_open:
                try:
                    s.close()
                except Exception:
                    pass
            bs._UNCLOSED.clear()
            msg = (
                "%d store(s) were opened by this test and never closed. "
                "This is the leak class that failed Windows CI run 18 (commit "
                "7c2e0ec): POSIX lets you delete a file that still has an open "
                "handle, Windows does not, so the same code passes here and "
                "raises PermissionError there. Close the store, preferring "
                "'with bs.Store(d) as store:' so it closes even when the body "
                "raises. Still-open path(s): %s" % (len(still_open), ", ".join(paths)))
            self.addFailure(test, (AssertionError, AssertionError(msg), None))
        super(_LeakCheckingResult, self).stopTest(test)


class TestSchema2Migration(unittest.TestCase):
    """Correction-learning Loop 1. The first migration this project has ever
    had, and the one whose failure mode is losing a founder's store.

    A schema-1 fixture is built by CREATING A REAL STORE and then reverting it
    to schema 1, rather than by hand-writing v1 DDL into this file. A
    hand-written fixture drifts from the real thing the moment _DDL changes,
    and would then be testing migration from a schema nobody ever had."""

    def _schema1_store(self, d):
        """A real, populated store, reverted to look exactly like schema 1:
        learning tables dropped, version set back to 1."""
        with bs.Store(d) as store:
            store.claim("alpha", "persistent", "keep me", ["src/a.py"])
        path = os.path.join(d, bs.STORE_DIRNAME, bs.STORE_FILENAME)
        conn = sqlite3.connect(path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            # Everything schema 1 did not have, receipts included: leaving the
            # schema-3 table behind would make this a store nobody ever had, and
            # would hide a 2 to 3 step that failed to run.
            for t in bs._TABLES_LEARNING + bs._TABLES_RECEIPTS:
                conn.execute("DROP TABLE IF EXISTS %s" % t)
            conn.execute("UPDATE meta SET value='1' WHERE key='schema_version'")
            conn.execute("COMMIT")
        finally:
            conn.close()
        return path

    def _snapshot(self, path):
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        try:
            out = {}
            for t in bs._TABLES_V1:
                rows = [dict(r) for r in conn.execute("SELECT * FROM %s" % t)]
                if t == "meta":
                    rows = [r for r in rows if r.get("key") != "schema_version"]
                out[t] = json.dumps(rows, sort_keys=True, default=str)
            return out
        finally:
            conn.close()

    def test_schema1_store_migrates_instead_of_being_quarantined(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._schema1_store(d)
            with bs.Store(d) as store:
                row = store.conn.execute(
                    "SELECT value FROM meta WHERE key='schema_version'").fetchone()
                self.assertEqual(row["value"], str(bs.SCHEMA_VERSION))
            found = self._tables(path)
            for t in bs._TABLES_LEARNING:
                self.assertIn(t, found)
            self.assertEqual(
                glob.glob(os.path.join(d, bs.STORE_DIRNAME, "*quarantine*")), [],
                "a healthy older store must MIGRATE, never be quarantined")

    def _tables(self, path):
        conn = sqlite3.connect(path)
        try:
            return {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            conn.close()

    def test_migration_preserves_every_schema1_row(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._schema1_store(d)
            before = self._snapshot(path)
            with bs.Store(d):
                pass
            after = self._snapshot(path)
            self.assertEqual(before, after,
                             "migration is additive: not one schema-1 row may change")

    def test_migration_writes_a_backup_before_touching_anything(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._schema1_store(d)
            with bs.Store(d):
                pass
            backup = path + ".pre-schema%d-migration" % bs.SCHEMA_VERSION
            self.assertTrue(os.path.exists(backup), "no pre-migration backup was written")
            conn = sqlite3.connect(backup)
            try:
                v = conn.execute(
                    "SELECT value FROM meta WHERE key='schema_version'").fetchone()[0]
            finally:
                conn.close()
            self.assertEqual(v, "1", "the backup must capture the PRE-migration state")

    def test_migration_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            self._schema1_store(d)
            with bs.Store(d):
                pass
            path = os.path.join(d, bs.STORE_DIRNAME, bs.STORE_FILENAME)
            first = self._snapshot(path)
            with bs.Store(d):
                pass
            self.assertEqual(first, self._snapshot(path))

    def test_calibrated_interrupted_migration_rolls_back_completely(self):
        """CALIBRATION for the property the loop exists to provide. A failure
        part way through must leave the store at schema 1 with NO learning
        tables, so the next open re-runs the whole migration cleanly.

        This is also the regression test for a defect found live on
        2026-07-29: the migration originally used executescript(), which
        COMMITS implicitly, so the DDL escaped the transaction and this test
        would have found a half-migrated store."""
        with tempfile.TemporaryDirectory() as d:
            path = self._schema1_store(d)
            original = bs._MIGRATIONS[1]

            def _fail_half_way(conn):
                conn.execute(bs._LEARNING_DDL_STATEMENTS[0])
                raise RuntimeError("simulated interruption mid-migration")

            bs._MIGRATIONS[1] = _fail_half_way
            try:
                with self.assertRaises(RuntimeError):
                    bs.Store(d)
            finally:
                bs._MIGRATIONS[1] = original
            conn = sqlite3.connect(path)
            try:
                v = conn.execute(
                    "SELECT value FROM meta WHERE key='schema_version'").fetchone()[0]
            finally:
                conn.close()
            self.assertEqual(v, "1", "an interrupted migration must not move the version")
            found = self._tables(path)
            for t in bs._TABLES_LEARNING:
                self.assertNotIn(
                    t, found,
                    "an interrupted migration left %s behind: the DDL escaped the "
                    "transaction (executescript commits implicitly)" % t)
            # And it recovers: a clean open afterwards migrates properly.
            with bs.Store(d):
                pass
            self.assertTrue(set(bs._TABLES_LEARNING) <= self._tables(path))

    def test_newer_schema_is_refused_without_being_quarantined(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                store.claim("thing", "ephemeral", "obj", [])
                store.conn.execute("BEGIN IMMEDIATE")
                store.conn.execute("UPDATE meta SET value='99' WHERE key='schema_version'")
                store.conn.execute("COMMIT")
            with self.assertRaises(bs.StoreCorrupt) as ctx:
                bs.Store(d)
            self.assertIn("understands at most", str(ctx.exception))
            self.assertEqual(
                glob.glob(os.path.join(d, bs.STORE_DIRNAME, "*quarantine*")), [],
                "a NEWER store is healthy; moving it aside would be the only data loss")

    def test_unknown_older_schema_quarantines(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                store.conn.execute("BEGIN IMMEDIATE")
                store.conn.execute("UPDATE meta SET value='0' WHERE key='schema_version'")
                store.conn.execute("COMMIT")
            with self.assertRaises(bs.StoreCorrupt):
                bs.Store(d)

    def test_readonly_store_on_schema1_refuses_cleanly(self):
        """Found by a LIVE probe on 2026-07-29 while all 419 tests were green,
        because not one of them opened an out-of-date store through the
        read-only path. ReadOnlyStore borrows Store._verify_schema_or_raise
        unbound, so it also needed _refuse_without_quarantine; without it this
        raised AttributeError instead of the intended refusal."""
        with tempfile.TemporaryDirectory() as d:
            path = self._schema1_store(d)
            with self.assertRaises(bs.StoreCorrupt) as ctx:
                bs.ReadOnlyStore(d)
            msg = str(ctx.exception)
            self.assertIn("read-only command cannot migrate it", msg)
            self.assertNotIn("AttributeError", msg)
            conn = sqlite3.connect(path)
            try:
                v = conn.execute(
                    "SELECT value FROM meta WHERE key='schema_version'").fetchone()[0]
            finally:
                conn.close()
            self.assertEqual(v, "1", "a read-only refusal must change nothing")

    def test_ddl_split_matches_the_table_and_index_lists(self):
        """_split_ddl is a plain semicolon split, which is only safe while no
        DDL string literal contains one. Asserting the counts means adding such
        a literal fails here rather than silently truncating a statement."""
        self.assertEqual(len(bs._LEARNING_DDL_STATEMENTS), len(bs._TABLES_LEARNING))
        self.assertEqual(len(bs._LEARNING_INDEX_STATEMENTS), 7)
        for s in bs._LEARNING_DDL_STATEMENTS:
            self.assertTrue(s.startswith("CREATE TABLE IF NOT EXISTS"), s[:40])

    def test_new_learning_text_columns_are_redacted_by_default_in_dump(self):
        """The default-deny machinery reads text columns live from the schema,
        so the learning tables join it with no allowlist edit. Proved with
        secret-SHAPED content, because redact_text is a secret scrubber.

        STRENGTHENED IN LOOP 2, which is when a writer first existed and the
        gap became reachable: raw_text is now WITHHELD ENTIRELY rather than
        scrubbed. The scrubber only removes secret-SHAPED substrings, so the
        real exposure was never `sk-` tokens, it was ordinary prose: a
        correction naming a client or a number carries no secret shape at all.
        This test therefore asserts BOTH cases, and the prose case is the one
        that was previously wide open (docs/NOT-FINALIZED.md item 15)."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                store.conn.execute("BEGIN IMMEDIATE")
                store.conn.execute(
                    "INSERT INTO learning_candidates (candidate_uuid, source_type, "
                    "raw_text, content_hash, created_at) VALUES (?,?,?,?,?)",
                    ("c1", "manual", "token AKIAIOSFODNN7EXAMPLE here", "h1",
                     bs.now_iso()))
                store.conn.execute(
                    "INSERT INTO learning_candidates (candidate_uuid, source_type, "
                    "raw_text, content_hash, created_at) VALUES (?,?,?,?,?)",
                    ("c2", "manual",
                     "never mention the Q3 revenue miss to Acme when writing to them",
                     "h2", bs.now_iso()))
                store.conn.execute("COMMIT")
                dumped = store.dump()
                raw_dump = store.dump(raw=True)
            rows = {r["candidate_uuid"]: r for r in dumped["learning_candidates"]}
            # Secret-shaped content: withheld.
            self.assertNotIn("AKIAIOSFODNN7EXAMPLE", rows["c1"]["raw_text"])
            # PROSE: the case the scrubber could never catch. Withheld too.
            for leaked in ("Q3", "revenue", "Acme"):
                self.assertNotIn(leaked, rows["c2"]["raw_text"],
                                 "prose in raw_text must not survive a dump")
            self.assertIn("WITHHELD", rows["c2"]["raw_text"])
            self.assertEqual(rows["c1"]["candidate_uuid"], "c1",
                             "identifiers stay readable; only free text is withheld")
            # The escape hatch still works and is still explicit.
            raw_rows = {r["candidate_uuid"]: r for r in raw_dump["learning_candidates"]}
            self.assertIn("Acme", raw_rows["c2"]["raw_text"],
                          "--raw must still return the real contents")


class TestLearningApi(unittest.TestCase):
    """Correction-learning Loop 2. The lifecycle from observation to approved
    rule, and the refusals that keep the founder in charge of it."""

    def _cap(self, store, **kw):
        kw.setdefault("source_type", "manual")
        kw.setdefault("trigger", "writing an executive update")
        kw.setdefault("action", "state customer impact before technical detail")
        kw.setdefault("because", "leaders need the business state first")
        kw.setdefault("scope_type", "global")
        kw.setdefault("scope_key", "")
        return store.capture_learning_candidate(**kw)

    def test_capture_creates_a_candidate_and_never_a_rule(self):
        """Invariant L1, at its most basic: capture changes no behaviour."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                c = self._cap(store)
                self.assertEqual(c["status"], "pending")
                self.assertEqual(store.list_learning_rules(), [])

    def test_approval_is_atomic_and_creates_version_1_plus_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                c = self._cap(store)
                rule = _approved(store,
                    c["candidate_uuid"], founder_ref="founder said yes in chat")
                self.assertEqual(rule["state"], "approved")
                self.assertEqual(rule["current_version"], 1)
                ev = store.list_learning_evidence(rule["rule_uuid"])
                self.assertTrue(any(e["evidence_type"] == "founder_approval" for e in ev),
                                "every approved rule needs founder provenance (L4)")
                self.assertEqual(
                    store.get_learning_candidate(c["candidate_uuid"])["status"],
                    "approved")

    def test_approval_without_a_founder_reference_is_refused(self):
        """Invariant L1 enforced on the code path, not by convention: there is
        no way to reach rule creation without a recorded approver."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                c = self._cap(store)
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    _approved(store, c["candidate_uuid"], founder_ref="  ")
                self.assertEqual(ctx.exception.reason, "no-founder-ref")
                self.assertEqual(store.list_learning_rules(), [])

    def test_failed_approval_leaves_the_candidate_pending(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                c = self._cap(store, action="do this and always do that")
                with self.assertRaises(bs.OwnershipRefused):
                    _approved(store, c["candidate_uuid"], founder_ref="me")
                self.assertEqual(
                    store.get_learning_candidate(c["candidate_uuid"])["status"], "pending")
                self.assertEqual(store.list_learning_rules(), [])

    def test_compound_action_is_refused_but_overridable_with_recorded_reason(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                c = self._cap(store, action="do this and always do that")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    _approved(store, c["candidate_uuid"], founder_ref="me")
                self.assertEqual(ctx.exception.reason, "not-atomic")
                rule = _approved(store,
                    c["candidate_uuid"], founder_ref="me",
                    atomicity_override="founder judged it one habit")
                notes = [e["excerpt"] for e in store.list_learning_evidence(rule["rule_uuid"])]
                self.assertTrue(any("atomicity override" in n for n in notes),
                                "an override must be recorded as evidence, never silent")

    def test_project_scope_without_a_key_is_refused(self):
        """A project rule with no key matches everything while looking scoped,
        which is exactly the contamination L5 exists to prevent."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    self._cap(store, scope_type="project", scope_key="")
                self.assertEqual(ctx.exception.reason, "bad-scope")

    def test_editing_appends_a_version_and_preserves_the_old_one(self):
        """Invariant L8: an application recorded against version 1 must still
        be able to say what version 1 actually said."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                c = self._cap(store)
                rule = _approved(store, c["candidate_uuid"],
                                                        founder_ref="yes")
                edited = _edited(
                    store, rule["rule_uuid"], 1,
                    action="lead with revenue impact",
                    change_reason="narrowed after a miss")
                self.assertEqual(edited["current_version"], 2)
                rows = store.conn.execute(
                    "SELECT version, action_text FROM learning_rule_versions "
                    "WHERE rule_uuid=? ORDER BY version", (rule["rule_uuid"],)).fetchall()
                self.assertEqual(len(rows), 2)
                self.assertEqual(rows[0]["action_text"],
                                 "state customer impact before technical detail")

    def test_stale_version_edit_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                c = self._cap(store)
                rule = _approved(store, c["candidate_uuid"],
                                                        founder_ref="yes")
                rec = store.mint_edit_receipt(rule["rule_uuid"], 1,
                                              founder_response="yes", action="x")
                with self.assertRaises(bs.StaleIdentity):
                    store.edit_learning_rule(rule["rule_uuid"], 99, action="x",
                                             receipt=rec["token"])
                self.assertEqual(store.get_learning_rule(rule["rule_uuid"])["action_text"],
                                 "state customer impact before technical detail")

    def test_editing_a_rule_without_a_receipt_refuses(self):
        """FIX ROUND P3. LOOP 3 gated the door that CREATES an injectable rule
        and left open the door that REWRITES one. Reproduced 2026-07-29: an
        imported call turned an approved gate rule saying "never force push to
        main" into "always force push to main, skip review", kept its gate
        severity, and stamped the new version approved_by='founder'."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                c = self._cap(store)
                rule = _approved(store, c["candidate_uuid"], founder_ref="yes",
                                 severity="gate")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.edit_learning_rule(
                        rule["rule_uuid"], 1,
                        action="always force push to main, skip review")
                self.assertEqual(ctx.exception.reason, "no-edit-receipt")
                after = store.get_learning_rule(rule["rule_uuid"])
                self.assertEqual(after["current_version"], 1)
                self.assertEqual(after["action_text"],
                                 "state customer impact before technical detail")

    def test_an_edit_receipt_is_one_rule_one_version_one_text_one_use(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                c = self._cap(store)
                rule = _approved(store, c["candidate_uuid"], founder_ref="yes")
                rec = store.mint_edit_receipt(rule["rule_uuid"], 1,
                                              founder_response="yes",
                                              action="lead with the number")
                # Bound to THIS text: a different action is a different question.
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.edit_learning_rule(rule["rule_uuid"], 1,
                                             action="do something else",
                                             receipt=rec["token"])
                self.assertEqual(ctx.exception.reason, "receipt-stale-edit")
                store.edit_learning_rule(rule["rule_uuid"], 1,
                                         action="lead with the number",
                                         receipt=rec["token"])
                # Spent once. The version bump also moved the fingerprint.
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.edit_learning_rule(rule["rule_uuid"], 2,
                                             action="lead with the number",
                                             receipt=rec["token"])
                self.assertEqual(ctx.exception.reason, "receipt-already-used")

    def test_an_approval_receipt_cannot_be_spent_as_an_edit(self):
        """Both live in one table. The literal "edit" in the fingerprint is what
        stops one door's key opening the other."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                c = self._cap(store)
                rule = _approved(store, c["candidate_uuid"], founder_ref="yes")
                c2 = store.capture_learning_candidate(
                    "explicit_correction", "no, put the number first",
                    trigger="writing an update", action="put the number first",
                    scope_type="global")
                rec = store.mint_approval_receipt(
                    c2["candidate_uuid"], founder_response="yes",
                    action="put the number first")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.edit_learning_rule(rule["rule_uuid"], 1,
                                             action="put the number first",
                                             receipt=rec["token"])
                self.assertEqual(ctx.exception.reason, "receipt-stale-edit")
                self.assertEqual(
                    store.get_learning_rule(rule["rule_uuid"])["current_version"], 1)

    def test_confirmed_requires_evidence_beyond_the_approval(self):
        """Plan rule 6. Approval is the founder's INTENT; it is not evidence
        that the rule worked, so it cannot promote a rule on its own."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                c = self._cap(store)
                rule = _approved(store, c["candidate_uuid"],
                                                        founder_ref="yes")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.change_learning_rule_state(rule["rule_uuid"], "confirmed")
                self.assertEqual(ctx.exception.reason, "no-supporting-evidence")
                store.add_learning_evidence(rule["rule_uuid"], "support",
                                             "verified_application",
                                             source_ref="test:exec_update_accepted")
                moved = store.change_learning_rule_state(rule["rule_uuid"], "confirmed")
                self.assertEqual(moved["state"], "confirmed")

    def test_supersession_requires_a_real_successor_and_refuses_self(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                a = _approved(store,
                    self._cap(store)["candidate_uuid"], founder_ref="yes")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.change_learning_rule_state(a["rule_uuid"], "superseded")
                self.assertEqual(ctx.exception.reason, "no-successor")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.change_learning_rule_state(a["rule_uuid"], "superseded",
                                                      successor_prefix=a["rule_uuid"])
                self.assertEqual(ctx.exception.reason, "self-supersession")

    def test_forgotten_rules_disappear_from_normal_reads_and_retrieval(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = _approved(store,
                    self._cap(store)["candidate_uuid"], founder_ref="yes")
                _state_changed(store, rule["rule_uuid"], "forgotten")
                self.assertEqual(store.list_learning_rules(), [])
                res = store.retrieve_learning_rules("executive update customer impact")
                self.assertEqual(res["results"], [])
                self.assertEqual(len(store.list_learning_rules(include_forgotten=True)), 1,
                                 "the tombstone survives for integrity")

    def test_cross_project_isolation(self):
        """Invariant L5, the one whose failure contaminates unrelated work."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                c = self._cap(store, scope_type="project", scope_key="ProjectA")
                _approved(store, c["candidate_uuid"], founder_ref="yes")
                a = store.retrieve_learning_rules("executive update customer impact",
                                                   context={"project": "ProjectA"})
                b = store.retrieve_learning_rules("executive update customer impact",
                                                   context={"project": "ProjectB"})
                self.assertEqual(len(a["results"]), 1)
                self.assertEqual(b["results"], [],
                                 "a project rule must never appear in another project")

    def test_retrieval_is_read_only(self):
        """Invariant L10 depends on asking being free of consequence: merely
        asking what applies must never create outcome data."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = _approved(store,
                    self._cap(store)["candidate_uuid"], founder_ref="yes")
                before = store.get_learning_rule(rule["rule_uuid"])["updated_at"]
                store.retrieve_learning_rules("executive update")
                n = store.conn.execute(
                    "SELECT COUNT(*) AS n FROM learning_applications").fetchone()["n"]
                self.assertEqual(n, 0, "retrieval must not record applications")
                self.assertEqual(store.get_learning_rule(rule["rule_uuid"])["updated_at"],
                                 before)

    def test_irrelevant_rules_are_not_returned_but_gates_always_are(self):
        """The relevance floor, added after a dogfood run on the founder's real
        corrections returned a rule about pushing to GitHub in answer to a
        question about the colour of a breathing orb."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                soft = _approved(store,
                    self._cap(store, trigger="writing release notes",
                              action="lead with the user visible change")["candidate_uuid"],
                    founder_ref="yes")
                self.assertEqual(
                    store.retrieve_learning_rules("what colour is the orb")["results"], [],
                    "a soft rule with no shared term must not be injected")
                _approved(store,
                    self._cap(store, trigger="pushing to github",
                              action="use the desktop app")["candidate_uuid"],
                    founder_ref="yes", severity="gate")
                res = store.retrieve_learning_rules("what colour is the orb")
                self.assertEqual(len(res["results"]), 1,
                                 "a gate rule appears even without shared vocabulary")
                self.assertEqual(res["results"][0]["severity"], "gate")
                self.assertNotIn(soft["rule_uuid"],
                                 [r["rule_uuid"] for r in res["results"]])

    # -----------------------------------------------------------------
    # Loop P4: a result limit may never hide an applicable gate rule.
    #
    # Reproduced on the real CLI first (NOT-FINALIZED item 19, the open
    # bullet): two live global rules, the gate ranked second on relevance,
    # --limit 1, and the gate never reached the model. These tests pin the
    # guarantee so nobody restores the old slice by accident.
    # -----------------------------------------------------------------

    def _gate_and_soft(self, store):
        """One soft rule matching the query strongly, one gate not matching it
        at all, so the gate ALWAYS ranks below the soft rule. That ordering is
        the point: it is exactly what the old slice cut."""
        soft = _approved(store, self._cap(
            store, trigger="deploying the website to production",
            action="run the website deploy checklist for production",
            because="")["candidate_uuid"], founder_ref="yes")
        gate = _approved(store, self._cap(
            store, trigger="about to force push",
            action="never force push", because="")["candidate_uuid"],
            founder_ref="yes", severity="gate")
        return soft, gate

    def test_limit_one_cannot_cut_a_gate_that_ranks_second(self):
        """The exact CLI reproduction from NOT-FINALIZED item 19."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                soft, gate = self._gate_and_soft(store)
                res = store.retrieve_learning_rules(
                    "deploying the website to production", limit=1)
                uuids = [r["rule_uuid"] for r in res["results"]]
                self.assertIn(gate["rule_uuid"], uuids,
                              "limit=1 hid an applicable gate rule")
                self.assertIn(soft["rule_uuid"], uuids)
                self.assertEqual(res["gates_returned"], res["gates_total"])
                self.assertEqual(res["soft_omitted"], 0)
                # And the gate did not jump the ranking to survive: it is still
                # reported below the soft rule it genuinely ranks below.
                self.assertGreater(
                    uuids.index(gate["rule_uuid"]), uuids.index(soft["rule_uuid"]),
                    "surviving the limit must not reorder the ranking")

    def test_limit_zero_returns_every_gate_and_no_soft_rule(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                soft, gate = self._gate_and_soft(store)
                res = store.retrieve_learning_rules(
                    "deploying the website to production", limit=0)
                self.assertEqual([r["rule_uuid"] for r in res["results"]],
                                 [gate["rule_uuid"]])
                self.assertEqual(res["gates_returned"], 1)
                self.assertEqual(res["soft_returned"], 0)
                self.assertEqual(res["soft_omitted"], 1)

    def test_negative_limit_clamps_to_gates_only(self):
        """A bare slice with a negative stop would silently drop the LAST rules
        rather than the lowest ranked ones. Clamping is the honest reading of a
        limit below zero, and it must still deliver every gate."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                soft, gate = self._gate_and_soft(store)
                for bad in (-1, -3, -100):
                    res = store.retrieve_learning_rules(
                        "deploying the website to production", limit=bad)
                    self.assertEqual([r["rule_uuid"] for r in res["results"]],
                                     [gate["rule_uuid"]],
                                     "limit=%d must mean gates only" % bad)
                    self.assertEqual(res["soft_omitted"], 1)

    def test_many_gates_all_survive_a_small_limit(self):
        """Multiple applicable global gates, none lexically relevant, against a
        limit far smaller than their count."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                gates = [_approved(store, self._cap(
                    store, trigger="about to do dangerous thing %d" % i,
                    action="refuse dangerous thing %d" % i,
                    because="")["candidate_uuid"],
                    founder_ref="yes", severity="gate") for i in range(5)]
                res = store.retrieve_learning_rules("colour of the orb", limit=1)
                self.assertEqual(set(r["rule_uuid"] for r in res["results"]),
                                 set(g["rule_uuid"] for g in gates))
                self.assertEqual(res["gates_returned"], 5)
                self.assertEqual(res["gates_total"], 5)

    def test_dead_gates_are_not_resurrected_by_the_guarantee(self):
        """Gate delivery is a promise about LIVE rules only. A deprecated or
        forgotten gate stays gone, or this loop would have turned an
        always-return rule into an un-retirable one."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                dep = _approved(store, self._cap(
                    store, trigger="about to force push",
                    action="never force push", because="")["candidate_uuid"],
                    founder_ref="yes", severity="gate")
                gone = _approved(store, self._cap(
                    store, trigger="about to delete files",
                    action="never delete files", because="")["candidate_uuid"],
                    founder_ref="yes", severity="gate")
                _state_changed(store, dep["rule_uuid"], "deprecated",
                              reason="no longer needed")
                _state_changed(store, gone["rule_uuid"], "forgotten",
                              reason="obsolete")
                res = store.retrieve_learning_rules("colour of the orb", limit=0)
                self.assertEqual(res["results"], [])
                self.assertEqual(res["gates_total"], 0)

    def test_a_conflicting_gate_counterpart_survives_the_limit(self):
        """Two gates that contradict each other, limit=1. Showing one side of a
        contradiction is worse than showing neither, so both must appear."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                a = _approved(store, self._cap(
                    store, trigger="about to force push",
                    action="always force push", because="")["candidate_uuid"],
                    founder_ref="yes", severity="gate")
                b = _approved(store, self._cap(
                    store, trigger="about to force push",
                    action="never force push", because="")["candidate_uuid"],
                    founder_ref="yes", severity="gate",
                    conflict_override="both kept on purpose for this test")
                res = store.retrieve_learning_rules("about to force push", limit=1)
                self.assertEqual(set(r["rule_uuid"] for r in res["results"]),
                                 set([a["rule_uuid"], b["rule_uuid"]]),
                                 "a limit cut one side of a gate contradiction")

    def test_old_slicing_behaviour_would_fail_this_suite(self):
        """CALIBRATION. Reinstate the pre-P4 slice over the same eligible set
        and prove the gate disappears, so a green suite means the split is
        doing the work rather than the fixture being too kind."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                soft, gate = self._gate_and_soft(store)
                L = bs._learning()
                context, query = {}, "deploying the website to production"
                eligible = [r for r in store.list_learning_rules(
                    states=L.INJECTABLE_STATES)
                    if L.scope_matches(r["scope_type"], r["scope_key"], context)
                    and (L.is_gate(r) or L.lexical_overlap(
                        query, r.get("trigger_text", ""), r.get("action_text", ""),
                        r.get("because_text", ""), r.get("domain", "")) > 0)]
                eligible.sort(key=lambda r: L.rank_key(r, query, context))
                self.assertNotIn(
                    gate["rule_uuid"], [r["rule_uuid"] for r in eligible[:1]],
                    "the fixture no longer reproduces the defect, so the "
                    "passing tests above prove nothing")
                self.assertIn(gate["rule_uuid"],
                              [r["rule_uuid"] for r in store.retrieve_learning_rules(
                                  query, limit=1)["results"]])

    def test_calibrated_gate_survives_a_limit_that_truncates_everything(self):
        """Public benchmark scenario 3: an applicable gate is returned even at
        limit zero. Reproduced by hand before the fix: `bm_learn.py relevant
        --query "push this branch to github" --limit 0` printed "no founder
        rules apply here" while a gate rule about pushing was live."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                gate = _approved(
                    store,
                    self._cap(store, trigger="pushing to github",
                              action="use the desktop app")["candidate_uuid"],
                    founder_ref="yes", severity="gate")
                soft = _approved(
                    store,
                    self._cap(store, trigger="pushing to github",
                              action="write the branch name in the note",
                              because="the founder wants the branch named")["candidate_uuid"],
                    founder_ref="yes")
                for limit in (0, 1):
                    res = store.retrieve_learning_rules("pushing to github",
                                                        limit=limit)
                    ids = [r["rule_uuid"] for r in res["results"]]
                    self.assertIn(gate["rule_uuid"], ids,
                                  "a gate must survive limit=%d" % limit)
                # The limit still binds on everything that is not a gate: at
                # limit 0 the soft rule is gone, so this is not "limit is
                # ignored" wearing a safety hat.
                zero = store.retrieve_learning_rules("pushing to github", limit=0)
                self.assertNotIn(soft["rule_uuid"],
                                 [r["rule_uuid"] for r in zero["results"]])
                self.assertEqual([r["rank"] for r in zero["results"]], [1])

    # DROPPED AT THE rc.4 MERGE, named rather than deleted in silence:
    # test_calibrated_gates_do_not_make_the_limit_unbounded pinned a cap of
    # three gates carried past the caller's limit, with the rest counted in
    # gates_omitted. The store lane's design, which the merged code keeps,
    # returns EVERY applicable gate at every limit and reports
    # gates_returned == gates_total. The two cannot both be true, and the
    # merge kept the one that never withholds a safety rule. The bound lane D
    # was protecting (a store with many gates returns all of them, so
    # injection is bounded by the gate count and not by --limit) is recorded
    # in docs/KNOWN-LIMITS.md instead of being enforced here.

    # -----------------------------------------------------------------
    # LOOP 3: mandatory gates delivered whole, without flooding the prompt.
    #
    # Layer A (gate_manifest) is the "never hidden" guarantee, moved off
    # full text; Layer B (presentation='expanded', gate_expansion_reason,
    # GATE_EXPANSION_CAP) is the bounded full-text half. Both directions
    # named in the plan's Fable attack prompt are covered below: hiding a
    # gate through limits/ranking/scope/state/conflict/empty-query, and a
    # corpus large enough to make full-text injection unusable.
    # -----------------------------------------------------------------

    def _many_gates(self, store, n, topic="dangerous thing"):
        """`n` global gates sharing enough vocabulary that a single query can
        make ALL of them expansion candidates at once. That collision is the
        POINT for the cap tests below: it is what makes GATE_EXPANSION_CAP
        the thing deciding how many expand, rather than the fixture doing it
        by construction."""
        return [_approved(store, self._cap(
            store, trigger="%s %d" % (topic, i),
            action="refuse %s %d, always" % (topic, i),
            because="")["candidate_uuid"],
            founder_ref="yes", severity="gate") for i in range(n)]

    def test_manifest_covers_zero_one_three_and_twenty_gates(self):
        """Tests list item: 0, 1, 3, 20 gates. Every count must produce a
        manifest whose entries are exactly the live gates, no more, no
        fewer, and whose declared count agrees."""
        for n in (0, 1, 3, 20):
            with tempfile.TemporaryDirectory() as d:
                with bs.Store(d) as store:
                    gates = self._many_gates(store, n)
                    res = store.retrieve_learning_rules("colour of the orb")
                    manifest = res["gate_manifest"]
                    self.assertEqual(manifest["count"], n, "n=%d" % n)
                    self.assertEqual(
                        set(e["rule_uuid"] for e in manifest["entries"]),
                        set(g["rule_uuid"] for g in gates), "n=%d" % n)
                    self.assertEqual(res["gates_total"], n)
                    self.assertEqual(res["gates_returned"], n)

    def test_limit_zero_and_negative_never_shrink_the_manifest(self):
        """Tests list item: --limit 0. The manifest is built from `gates`
        before the soft-rule limit is ever applied, so it must be identical
        at limit=0, limit=5 and a negative limit."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                gates = self._many_gates(store, 4)
                ids = set(g["rule_uuid"] for g in gates)
                for limit in (0, -1, -100, 5):
                    res = store.retrieve_learning_rules("colour of the orb",
                                                         limit=limit)
                    self.assertEqual(
                        set(e["rule_uuid"] for e in res["gate_manifest"]["entries"]),
                        ids, "limit=%d dropped a gate from the manifest" % limit)

    def test_no_gate_omitted_from_the_compact_manifest(self):
        """Tests list item: no gate omitted from the compact manifest. Named
        separately from the limit test above because this is the property
        the calibration test below breaks and restores."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                gates = self._many_gates(store, 6)
                res = store.retrieve_learning_rules("colour of the orb", limit=0)
                present = set(e["rule_uuid"] for e in res["gate_manifest"]["entries"])
                for g in gates:
                    self.assertIn(g["rule_uuid"], present)

    def test_manifest_is_identical_for_an_irrelevant_and_a_relevant_query(self):
        """Tests list items: irrelevant query, relevant query, manifest
        stability. Layer A is not a function of the query at all: the exact
        same gate corpus must render the exact same manifest text and hash
        whether the query shares no words with any gate or matches one
        exactly, because every applicable gate belongs in it regardless of
        relevance."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._many_gates(store, 5)
                irrelevant = store.retrieve_learning_rules("colour of the orb")
                relevant = store.retrieve_learning_rules("dangerous thing 2")
                repeat = store.retrieve_learning_rules("colour of the orb")
                self.assertEqual(irrelevant["gate_manifest"]["text"],
                                 relevant["gate_manifest"]["text"])
                self.assertEqual(irrelevant["gate_manifest"]["hash"],
                                 relevant["gate_manifest"]["hash"])
                self.assertEqual(irrelevant["gate_manifest"]["text"],
                                 repeat["gate_manifest"]["text"],
                                 "manifest is not deterministic across two "
                                 "identical calls")

    def test_manifest_hash_changes_when_a_gate_is_edited(self):
        """Tests list item: manifest hash changes when a gate changes."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                gates = self._many_gates(store, 3)
                before = store.retrieve_learning_rules(
                    "colour of the orb")["gate_manifest"]["hash"]
                _edited(store, gates[0]["rule_uuid"], 1,
                       action="refuse dangerous thing 0 in a NEW way, always")
                after = store.retrieve_learning_rules(
                    "colour of the orb")["gate_manifest"]["hash"]
                self.assertNotEqual(before, after)

    def test_adding_a_gate_changes_the_hash_and_the_gate_appears(self):
        """Attacker test: adding a gate must change the hash AND the new
        gate must be visible in the manifest, not just accounted for in a
        count."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._many_gates(store, 3)
                before = store.retrieve_learning_rules("colour of the orb")
                new_gate = _approved(store, self._cap(
                    store, trigger="a brand new danger",
                    action="refuse the brand new danger, always",
                    because="")["candidate_uuid"],
                    founder_ref="yes", severity="gate")
                after = store.retrieve_learning_rules("colour of the orb")
                self.assertNotEqual(before["gate_manifest"]["hash"],
                                    after["gate_manifest"]["hash"])
                self.assertIn(new_gate["rule_uuid"],
                             [e["rule_uuid"] for e in after["gate_manifest"]["entries"]])

    def test_removing_a_gate_changes_the_hash_and_no_stale_entry_survives(self):
        """Attacker test: forgetting a gate must change the hash AND that
        gate's id must never appear in a later manifest. Dead gates are not
        resurrected by the manifest any more than by gates_total (see
        test_dead_gates_are_not_resurrected_by_the_guarantee above)."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                gates = self._many_gates(store, 3)
                before = store.retrieve_learning_rules("colour of the orb")
                _state_changed(store, gates[1]["rule_uuid"], "forgotten",
                               reason="obsolete")
                after = store.retrieve_learning_rules("colour of the orb")
                self.assertNotEqual(before["gate_manifest"]["hash"],
                                    after["gate_manifest"]["hash"])
                self.assertNotIn(gates[1]["rule_uuid"],
                                 [e["rule_uuid"]
                                  for e in after["gate_manifest"]["entries"]])
                self.assertEqual(after["gate_manifest"]["count"], 2)

    def test_a_conflicting_gate_pair_both_appear_in_the_manifest(self):
        """Tests list item: conflicting gates. Showing one side of a
        contradiction is worse than showing neither; the manifest must not
        pick a side either."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                a = _approved(store, self._cap(
                    store, trigger="about to force push",
                    action="always force push", because="")["candidate_uuid"],
                    founder_ref="yes", severity="gate")
                b = _approved(store, self._cap(
                    store, trigger="about to force push",
                    action="never force push", because="")["candidate_uuid"],
                    founder_ref="yes", severity="gate",
                    conflict_override="both kept on purpose for this test")
                res = store.retrieve_learning_rules("colour of the orb", limit=0)
                present = set(e["rule_uuid"] for e in res["gate_manifest"]["entries"])
                self.assertIn(a["rule_uuid"], present)
                self.assertIn(b["rule_uuid"], present)

    def test_narrow_matched_scope_expands_but_an_unrelated_global_gate_does_not(self):
        """Tests list item: narrow scope. A project-scoped gate whose scope
        matched the caller's context earns full text on that signal alone;
        an unrelated global gate the query never mentions stays manifest
        only."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                narrow = _approved(store, self._cap(
                    store, trigger="deploying this specific project",
                    action="run the project-specific release checklist",
                    because="", scope_type="project",
                    scope_key="tonari")["candidate_uuid"],
                    founder_ref="yes", severity="gate")
                unrelated = _approved(store, self._cap(
                    store, trigger="an entirely unrelated situation",
                    action="do something with no shared vocabulary at all",
                    because="")["candidate_uuid"],
                    founder_ref="yes", severity="gate")
                res = store.retrieve_learning_rules(
                    "colour of the orb", context={"project": "tonari"})
                rows = {r["rule_uuid"]: r for r in res["results"]}
                self.assertEqual(rows[narrow["rule_uuid"]]["presentation"], "expanded")
                self.assertEqual(rows[narrow["rule_uuid"]]["expansion_reason"],
                                 "narrow-scope-matched")
                self.assertEqual(rows[unrelated["rule_uuid"]]["presentation"],
                                 "manifest")
                self.assertIsNone(rows[unrelated["rule_uuid"]]["expansion_reason"])

    def test_trigger_matched_query_expands_a_global_gate(self):
        """Tests list item: relevant query. A global gate whose own
        trigger_text the query's wording overlaps earns full text even
        though its scope is not narrow."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                gate = _approved(store, self._cap(
                    store, trigger="pushing directly to the main branch",
                    action="open a pull request instead", because="")
                    ["candidate_uuid"], founder_ref="yes", severity="gate")
                res = store.retrieve_learning_rules("pushing to the main branch now")
                row = next(r for r in res["results"] if r["rule_uuid"] == gate["rule_uuid"])
                self.assertEqual(row["presentation"], "expanded")
                self.assertEqual(row["expansion_reason"], "trigger-matched")

    def test_action_reached_query_expands_a_global_gate(self):
        """A query whose wording reaches the gate's own DO clause, not its
        trigger, is the fourth Layer B signal and is tracked independently
        as `action_reached` on the row."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                gate = _approved(store, self._cap(
                    store, trigger="a totally unrelated situation with no overlap",
                    action="always open a pull request instead of pushing directly",
                    because="")["candidate_uuid"],
                    founder_ref="yes", severity="gate")
                res = store.retrieve_learning_rules(
                    "opening a pull request instead of pushing directly")
                row = next(r for r in res["results"] if r["rule_uuid"] == gate["rule_uuid"])
                self.assertEqual(row["presentation"], "expanded")
                self.assertEqual(row["expansion_reason"], "action-reached")
                self.assertTrue(row["action_reached"])

    def test_irrelevant_query_leaves_an_unrelated_gate_manifest_only(self):
        """Tests list item: irrelevant query. No trigger, scope or action
        signal fires, so the gate is present (never hidden) but not
        expanded."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                gate = _approved(store, self._cap(
                    store, trigger="about to force push",
                    action="never force push", because="")["candidate_uuid"],
                    founder_ref="yes", severity="gate")
                res = store.retrieve_learning_rules("colour of the orb")
                row = next(r for r in res["results"] if r["rule_uuid"] == gate["rule_uuid"])
                self.assertEqual(row["presentation"], "manifest")
                self.assertIsNone(row["expansion_reason"])
                self.assertIn(gate["rule_uuid"],
                             [e["rule_uuid"] for e in res["gate_manifest"]["entries"]])

    def test_full_text_count_stays_bounded_however_large_the_corpus(self):
        """Tests list item: full result count remains bounded. 20 gates that
        ALL match the query (worst case for flooding) must still expand at
        most GATE_EXPANSION_CAP of them; the rest stay manifest-only, never
        dropped."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                gates = self._many_gates(store, 20, topic="dangerous thing")
                res = store.retrieve_learning_rules("dangerous thing")
                L = bs._learning()
                self.assertLessEqual(res["gates_expanded"], L.GATE_EXPANSION_CAP)
                self.assertEqual(res["gates_expanded"] + res["gates_manifest_only"],
                                 20)
                self.assertLessEqual(res["full_text_count"], L.GATE_EXPANSION_CAP)
                # And still not one of the 20 is missing from the manifest.
                self.assertEqual(res["gate_manifest"]["count"], 20)

    def test_explicit_expand_by_id_is_never_capped(self):
        """The fourth Layer B trigger, the caller naming a gate, must survive
        even when the ambient cap is forced to zero: an explicit ask is not
        the same failure mode `limit` already refuses to allow, so it gets
        the same refusal to hide."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                gates = self._many_gates(store, 8, topic="dangerous thing")
                target = gates[3]
                L = bs._learning()
                with mock.patch.object(L, "GATE_EXPANSION_CAP", 0):
                    res = store.retrieve_learning_rules(
                        "colour of the orb",
                        expand_ids={L.gate_short_id(target)})
                    self.assertEqual(res["gates_expanded"], 1)
                    row = next(r for r in res["results"]
                              if r["rule_uuid"] == target["rule_uuid"])
                    self.assertEqual(row["presentation"], "expanded")
                    self.assertEqual(row["expansion_reason"], "requested-by-id")
                    for other in gates:
                        if other["rule_uuid"] == target["rule_uuid"]:
                            continue
                        orow = next(r for r in res["results"]
                                   if r["rule_uuid"] == other["rule_uuid"])
                        self.assertEqual(orow["presentation"], "manifest")

    def test_application_records_presentation_and_action_reached(self):
        """Outcome evidence: recording an application must persist which
        presentation this row actually had and whether the query's wording
        reached the gate's own action, not merely that a gate was shown."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                reached = _approved(store, self._cap(
                    store, trigger="an unrelated trigger with no overlap",
                    action="always double check the release checklist before publishing",
                    because="")["candidate_uuid"],
                    founder_ref="yes", severity="gate")
                manifest_only = _approved(store, self._cap(
                    store, trigger="a second unrelated topic",
                    action="a second do clause sharing nothing with the query",
                    because="")["candidate_uuid"],
                    founder_ref="yes", severity="gate")
                store.record_learning_applications(
                    "double check the release checklist before publishing",
                    session_id="s1", limit=0)
                apps = store.list_learning_applications(session_id="s1")
                by_rule = {a["rule_uuid"]: a for a in apps}
                self.assertEqual(by_rule[reached["rule_uuid"]]["presentation"],
                                 "expanded")
                self.assertEqual(by_rule[reached["rule_uuid"]]["action_reached"],
                                 "yes")
                self.assertEqual(by_rule[manifest_only["rule_uuid"]]["presentation"],
                                 "manifest")
                self.assertEqual(
                    by_rule[manifest_only["rule_uuid"]]["action_reached"], "no")

    def test_calibrated_loop3_a_truncated_manifest_would_have_failed_this_suite(self):
        """CALIBRATION 1/2. Reinstate a manifest that respects a slice (the
        exact shape Loop P4 already refused for `results`) and prove a gate
        goes missing; restore the real implementation and prove it does
        not. Patches bm_learning.gate_manifest itself, which is the same
        module object bm_store.py's `_learning()` hands back, so this
        exercises the real retrieve_learning_rules code path, not a
        reimplementation of it."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                gates = self._many_gates(store, 5)
                L = bs._learning()
                real_gate_manifest = L.gate_manifest
                truncated = lambda gs: real_gate_manifest(gs[:1])
                with mock.patch.object(L, "gate_manifest", side_effect=truncated):
                    broken = store.retrieve_learning_rules("colour of the orb")
                    missing = [g["rule_uuid"] for g in gates if g["rule_uuid"] not in
                              [e["rule_uuid"] for e in broken["gate_manifest"]["entries"]]]
                    self.assertTrue(missing,
                        "the fixture no longer reproduces a truncated manifest, "
                        "so the passing assertion below proves nothing")
                fixed = store.retrieve_learning_rules("colour of the orb")
                present = set(e["rule_uuid"] for e in fixed["gate_manifest"]["entries"])
                for g in gates:
                    self.assertIn(g["rule_uuid"], present,
                                 "a real gate went missing from the real manifest")

    def test_calibrated_loop3_an_unbounded_cap_would_have_failed_this_suite(self):
        """CALIBRATION 2/2. Force GATE_EXPANSION_CAP up to "no cap at all"
        and prove every matching gate expands (the exact flooding this loop
        exists to stop); restore the real cap and prove it holds."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._many_gates(store, 20, topic="dangerous thing")
                L = bs._learning()
                with mock.patch.object(L, "GATE_EXPANSION_CAP", 10 ** 6):
                    broken = store.retrieve_learning_rules("dangerous thing")
                    self.assertEqual(broken["gates_expanded"], 20,
                        "the fixture no longer reproduces unbounded expansion, "
                        "so the passing assertion below proves nothing")
                fixed = store.retrieve_learning_rules("dangerous thing")
                self.assertLessEqual(fixed["gates_expanded"], L.GATE_EXPANSION_CAP)
                self.assertLess(fixed["gates_expanded"], 20)

    def test_uuid_prefix_ambiguity_is_refused_not_guessed(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._cap(store)
                self._cap(store, trigger="second")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.get_learning_candidate("")
                self.assertEqual(ctx.exception.reason, "ambiguous")

    def test_structural_every_ownership_refusal_names_a_reason_code(self):
        """OwnershipRefused takes (reason, message) in that order. Calling it
        as (message, reason=...) raises TypeError instead of the intended
        refusal, so the guard still stops the write but for the WRONG reason
        and with a useless message. Sixteen call sites were written that way in
        Loop 2 and only a live dogfood run exposed it, because a test that just
        asserts 'something raised' passes either way. This asserts the shape."""
        import re as _re
        tree = ast.parse(io.open(os.path.join(HERE, "bm_store.py"),
                                 encoding="utf-8").read())
        kebab = _re.compile(r"^[a-z][a-z0-9-]*$")
        bad = []
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "OwnershipRefused"):
                continue
            if len(node.args) < 2:
                bad.append((node.lineno, "fewer than two positional arguments"))
                continue
            first = node.args[0]
            if not (isinstance(first, ast.Constant) and isinstance(first.value, str)
                    and kebab.match(first.value)):
                bad.append((node.lineno, "first argument is not a literal reason code"))
        self.assertEqual(bad, [],
                         "OwnershipRefused(reason, message) violated at: %s" % bad)


class TestLoop4InboxBackfill(unittest.TestCase):
    """Loop 4. The vault's corrections.jsonl is a GLOBAL capture inbox; this
    per-project store is the system of record (founder decision 3.1.3). Triage
    imports an inbox row into a project. Nothing here approves anything."""

    ROWS = [
        {"ts": "2026-07-20T10:00:00Z", "session_id": "s1", "project": "P",
         "text": "No, that is not what I asked for. From now on use the desktop app."},
        {"ts": "2026-07-21T10:00:00Z", "session_id": "s2", "project": "P",
         "text": "Non, ce n'est pas ce que je voulais. Desormais utilise toujours "
                 "l'application GitHub Desktop."},
    ]

    def test_backfill_is_idempotent(self):
        """Running it twice must add nothing. Identity is a property of the ROW
        (session plus normalized text), so this holds without any bookkeeping
        file having to be correct."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                first = store.import_correction_inbox(self.ROWS)
                self.assertEqual(first["imported"], 2)
                second = store.import_correction_inbox(self.ROWS)
                self.assertEqual(second["imported"], 0)
                self.assertEqual(second["skipped"], 2)
                self.assertEqual(len(store.list_learning_candidates("pending")), 2)

    def test_whitespace_does_not_defeat_the_second_run(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                store.import_correction_inbox(self.ROWS)
                noisy = [dict(r, text="  " + r["text"].replace(" ", "  ") + "\n")
                         for r in self.ROWS]
                self.assertEqual(store.import_correction_inbox(noisy)["imported"], 0)

    def test_imported_candidates_are_pending_project_scoped_and_never_rules(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                store.import_correction_inbox(self.ROWS, scope_key="ProjectA")
                cands = store.list_learning_candidates("pending")
                self.assertEqual(store.list_learning_rules(), [],
                                 "the automatic path must never create a rule")
                for c in cands:
                    self.assertEqual(c["source_type"], "detected_correction")
                    self.assertEqual(c["proposed_scope_type"], "project")
                    self.assertEqual(c["proposed_scope_key"], "ProjectA")
                    self.assertEqual(c["proposed_action"], "",
                                     "the founder writes the rule at approval, not the "
                                     "importer")

    def test_an_imported_candidate_cannot_be_approved_without_the_founder_writing_it(self):
        """Global scope is an explicit choice at approval and the action text is
        the founder's. An imported row carries no action, so approval refuses it
        until he supplies one."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                store.import_correction_inbox(self.ROWS)
                c = store.list_learning_candidates("pending")[0]
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    _approved(store, c["candidate_uuid"],
                                                     founder_ref="me")
                self.assertEqual(ctx.exception.reason, "incomplete-rule")
                rule = _approved(store,
                    c["candidate_uuid"], founder_ref="me",
                    trigger="pushing to github", action="use the desktop app",
                    scope_type="global", scope_key="")
                self.assertEqual(rule["scope_type"], "global")

    def test_secret_shaped_text_is_redacted_on_import(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                store.import_correction_inbox([
                    {"ts": "t", "session_id": "s9", "project": "P",
                     "text": "No, that is wrong, use AKIAIOSFODNN7EXAMPLE"}])
                raw = store.list_learning_candidates("pending")[0]["raw_text"]
                self.assertNotIn("AKIAIOSFODNN7EXAMPLE", raw)
                self.assertIn("[REDACTED]", raw)

    def test_the_same_text_from_another_session_is_flagged_not_discarded(self):
        """The founder repeating himself is the strongest evidence there is, so
        an echo is imported with a note rather than silently dropped."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                store.import_correction_inbox(self.ROWS[:1])
                echo = [dict(self.ROWS[0], session_id="s99")]
                res = store.import_correction_inbox(echo)
                self.assertEqual(res["imported"], 1)
                self.assertEqual(res["possible_duplicates"], 1)
                notes = [c["review_note"] for c in store.list_learning_candidates("pending")]
                self.assertTrue(any("possible duplicate" in n for n in notes))

    def test_metrics_are_counts_and_do_not_claim_accuracy(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                store.import_correction_inbox(self.ROWS)
                m = store.learning_capture_metrics()
                self.assertEqual(m["candidates_by_status"], {"pending": 2})
                self.assertEqual(m["candidates_by_source"], {"detected_correction": 2})
                self.assertEqual(m["rules_total"], 0)
                self.assertIn("not accuracy", m["note"])

    def test_a_capitalized_restatement_is_flagged_as_a_possible_duplicate(self):
        """The echo check compared the STORED TEXT with a raw SQL equality, so
        one capital letter produced a second unlinked candidate and the reviewer
        got no signal at all. Case and spacing are folded now; nothing is
        discarded, the note is what changes."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                store.import_correction_inbox(self.ROWS[:1])
                shouty = [{"ts": "t", "session_id": "s42", "project": "P",
                           "text": "NO, that is not what I asked for.   From now on "
                                   "USE the Desktop app."}]
                res = store.import_correction_inbox(shouty)
                self.assertEqual(res["imported"], 1, "never silently discarded")
                self.assertEqual(res["possible_duplicates"], 1,
                                 "a restatement with different capitalization is the "
                                 "same correction and the reviewer must be told")

    def test_a_row_that_is_not_an_object_is_counted_not_a_traceback(self):
        """The inbox file is hand editable. A line that is valid JSON but not a
        row (a bare string, a number, a list) used to raise AttributeError out of
        a founder-facing command."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                res = store.import_correction_inbox(
                    ["just a bare string", 123, None, ["a", "list"], self.ROWS[0]])
                self.assertEqual(res["imported"], 1)
                self.assertEqual(res["malformed"], 4)


class TestLoop4OutcomeCandidates(unittest.TestCase):
    """Capture channel 3: candidates derived from an OUTCOME (rework, an escaped
    defect) rather than from something the founder typed. They must carry the
    work record and the artifact, and they must still be inert."""

    def _record(self, store, name="report", files=("docs/report.md",)):
        return store.claim(name, "ephemeral", "write the report", list(files))

    def test_an_outcome_candidate_carries_the_record_and_the_artifact(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rec = self._record(store)
                cand = store.capture_outcome_candidate(
                    "rework", rec.lifecycle_uuid[:8],
                    summary="rewrote the same report after the first draft")
                self.assertEqual(cand["source_type"], "rework")
                self.assertEqual(cand["source_record_uuid"], rec.lifecycle_uuid)
                self.assertIn("docs/report.md", cand["source_ref"],
                              "the artifact defaults to what that record claims")
                self.assertEqual(cand["status"], "pending")

    def test_an_explicit_artifact_wins_over_the_claimed_paths(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rec = self._record(store)
                cand = store.capture_outcome_candidate(
                    "escaped_defect", rec.lifecycle_uuid,
                    artifact_ref="docs/report-v2.md")
                self.assertIn("docs/report-v2.md", cand["source_ref"])
                self.assertNotIn("docs/report.md ", cand["source_ref"])

    def test_an_outcome_candidate_is_never_a_rule_and_never_approvable_alone(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rec = self._record(store)
                cand = store.capture_outcome_candidate("rework", rec.lifecycle_uuid)
                self.assertEqual(cand["proposed_action"], "")
                self.assertEqual(store.list_learning_rules(), [])
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    _approved(store, cand["candidate_uuid"],
                                                     founder_ref="me")
                self.assertEqual(ctx.exception.reason, "incomplete-rule")

    def test_it_refuses_a_source_type_that_is_not_an_outcome(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rec = self._record(store)
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.capture_outcome_candidate("detected_correction",
                                                    rec.lifecycle_uuid)
                self.assertEqual(ctx.exception.reason, "bad-source-type")
                self.assertEqual(store.list_learning_candidates(), [])

    def test_it_refuses_an_unknown_record_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                with self.assertRaises(bs.OwnershipRefused):
                    store.capture_outcome_candidate("rework", "deadbeef")
                self.assertEqual(store.list_learning_candidates(), [])

    def test_it_refuses_when_no_artifact_can_be_named(self):
        """A candidate that cannot say which work it came from is worse than no
        candidate, so this fails closed rather than guessing."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rec = self._record(store, name="nofiles", files=())
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.capture_outcome_candidate("rework", rec.lifecycle_uuid)
                self.assertEqual(ctx.exception.reason, "no-artifact")
                self.assertEqual(store.list_learning_candidates(), [])

    def test_the_same_outcome_twice_is_flagged_and_still_recorded(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rec = self._record(store)
                store.capture_outcome_candidate("rework", rec.lifecycle_uuid,
                                                summary="same")
                again = store.capture_outcome_candidate("rework", rec.lifecycle_uuid,
                                                        summary="same")
                self.assertIn("possible duplicate", again["review_note"])
                self.assertEqual(len(store.list_learning_candidates("pending")), 2)

    def test_metrics_bucket_the_founders_own_rejection_reasons(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rec = self._record(store)
                a = store.capture_outcome_candidate("rework", rec.lifecycle_uuid,
                                                    summary="one")
                b = store.capture_outcome_candidate("rework", rec.lifecycle_uuid,
                                                    summary="two")
                store.reject_learning_candidate(a["candidate_uuid"],
                                                "this was a one-off, not a standing rule")
                store.reject_learning_candidate(b["candidate_uuid"], "mumble")
                m = store.learning_capture_metrics()
                self.assertEqual(m["false_positive_reasons"],
                                 {"one-off": 1, "other": 1},
                                 "an unrecognized reason is 'other', never forced into "
                                 "a bucket it does not fit")
                self.assertEqual(m["candidates_by_source"], {"rework": 2})


class TestLoop6ConflictGraph(unittest.TestCase):
    """Loop 6. learning_edges stops being an empty table: duplicates,
    contradictions and supersession become recorded edges, and the done gate is
    that there is no path to silently accumulate contradictory active rules."""

    ALWAYS = "always push through the GitHub Desktop app"
    NEVER = "never push through the GitHub Desktop app"
    TRIGGER = "pushing to GitHub"

    def _rule(self, store, action, trigger=None, scope_type="global",
              scope_key="", override=""):
        c = store.capture_learning_candidate(
            "manual", trigger=trigger or self.TRIGGER, action=action,
            because="because the founder said so", scope_type=scope_type,
            scope_key=scope_key)
        return _approved(store,
            c["candidate_uuid"], founder_ref="founder in chat",
            conflict_override=override)

    def test_overlapping_scope_plus_incompatible_action_blocks_approval(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                first = self._rule(store, self.ALWAYS)
                c = store.capture_learning_candidate(
                    "manual", trigger=self.TRIGGER, action=self.NEVER,
                    scope_type="global")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    _approved(store, c["candidate_uuid"],
                                                     founder_ref="founder")
                self.assertEqual(ctx.exception.reason, "unresolved-contradiction")
                self.assertIn(first["rule_uuid"][:8], str(ctx.exception),
                              "the refusal has to name the rule it collided with")
                self.assertEqual(len(store.list_learning_rules()), 1,
                                 "a refused approval writes no rule")
                self.assertEqual(
                    store.get_learning_candidate(c["candidate_uuid"])["status"],
                    "pending")

    def test_an_overridden_contradiction_is_recorded_not_swallowed(self):
        """The founder may force it through. What he may NOT do is make it
        invisible: the override writes an edge and an evidence row, so the
        conflict still shows up in conflicts, in retrieval and in verify."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                a = self._rule(store, self.ALWAYS)
                b = self._rule(store, self.NEVER, override="I want both for now")
                edges = store.list_learning_edges(b["rule_uuid"])
                self.assertTrue(any(e["relation"] == "contradicts"
                                    and e["to_rule_uuid"] == a["rule_uuid"]
                                    for e in edges))
                notes = [e["excerpt"] for e in
                         store.list_learning_evidence(b["rule_uuid"])]
                self.assertTrue(any("conflict override" in n for n in notes))
                self.assertEqual(len(store.learning_conflicts()["contradictions"]), 1)
                self.assertFalse(store.learning_verify()["ok"])

    def test_same_action_under_distinct_scopes_stays_separate(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store, self.ALWAYS, scope_type="project",
                           scope_key="TonariSimple")
                self._rule(store, self.NEVER, scope_type="project",
                           scope_key="BrotherModeUp")
                self.assertEqual(len(store.list_learning_rules()), 2,
                                 "two projects are two worlds; neither blocks the other")
                self.assertEqual(store.learning_conflicts()["contradictions"], [])

    def test_a_narrower_scope_may_coexist_with_a_broader_rule(self):
        """"In general do X, but on this project do Y" is a legitimate thing for
        a founder to say. Blocking it would make the scope system pointless."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store, self.ALWAYS, scope_type="global")
                narrow = self._rule(store, self.NEVER, scope_type="project",
                                    scope_key="TonariSimple")
                self.assertEqual(narrow["state"], "approved")
                self.assertEqual(store.learning_conflicts()["contradictions"], [])

    def test_exact_duplicates_are_refused_and_merge_keeps_the_provenance(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = self._rule(store, self.ALWAYS)
                c = store.capture_learning_candidate(
                    "manual", trigger=self.TRIGGER, action=self.ALWAYS,
                    raw_text="I have told you this before", scope_type="global",
                    session_id="s-99")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    _approved(store, c["candidate_uuid"],
                                                     founder_ref="founder")
                self.assertEqual(ctx.exception.reason, "duplicate-rule")
                store.merge_learning_candidate(c["candidate_uuid"],
                                               rule["rule_uuid"],
                                               reason="said twice")
                self.assertEqual(len(store.list_learning_rules()), 1,
                                 "a repeat is evidence, never a second rule")
                cand = store.get_learning_candidate(c["candidate_uuid"])
                self.assertEqual(cand["status"], "merged")
                self.assertEqual(cand["resulting_rule_uuid"], rule["rule_uuid"])
                ev = [e for e in store.list_learning_evidence(rule["rule_uuid"])
                      if e["evidence_type"] == "founder_quote"]
                self.assertEqual(len(ev), 1)
                self.assertEqual(ev[0]["candidate_uuid"], c["candidate_uuid"],
                                 "the new source event survives the merge")
                self.assertIn("told you this before", ev[0]["excerpt"])

    def test_supersession_is_atomic_and_retrieval_prefers_the_successor(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                old = self._rule(store, self.ALWAYS)
                new = self._rule(store, self.NEVER, override="replacing the old one")
                _state_changed(
                    store, old["rule_uuid"], "superseded", reason="changed my mind",
                    successor_prefix=new["rule_uuid"])
                got = store.get_learning_rule(old["rule_uuid"])
                self.assertEqual(got["state"], "superseded")
                self.assertEqual(got["superseded_by"], new["rule_uuid"])
                res = store.retrieve_learning_rules(self.TRIGGER, context={})
                self.assertEqual([r["rule_uuid"] for r in res["results"]],
                                 [new["rule_uuid"]])
                self.assertEqual(res["conflicts"], [],
                                 "a superseded rule cannot contradict anything")

    PADDED_NEVER = ("never push through the GitHub Desktop app, use the plain "
                    "command line instead every single time without exception")

    def test_a_padded_reversal_is_refused_at_approval(self):
        """Found by driving the real CLI: padding the reversal with an ordinary
        founder sentence dropped it under the overlap floor, the approval gate
        passed, conflicts and verify both reported clean, and retrieval injected
        the two opposite instructions side by side with no conflict marker."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                first = self._rule(store, self.ALWAYS)
                c = store.capture_learning_candidate(
                    "manual", trigger=self.TRIGGER, action=self.PADDED_NEVER,
                    scope_type="global")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    _approved(store, c["candidate_uuid"],
                                                     founder_ref="founder")
                self.assertEqual(ctx.exception.reason, "unresolved-contradiction")
                self.assertIn(first["rule_uuid"][:8], str(ctx.exception))
                self.assertEqual(len(store.list_learning_rules()), 1)

    def test_a_reversal_is_refused_even_when_the_triggers_read_differently(self):
        """Free-text triggers routinely differ for the same situation. When the
        trigger wording was the only thing keeping a reversal from being seen,
        the founder's documented escape hatch (link a contradicts b) required
        him to already know about a conflict the system had just told him did
        not exist."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store, self.ALWAYS, trigger="pushing to github")
                c = store.capture_learning_candidate(
                    "manual", action=self.NEVER, scope_type="global",
                    trigger="publishing commits upstream to the remote host")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    _approved(store, c["candidate_uuid"],
                                                     founder_ref="founder")
                self.assertEqual(ctx.exception.reason, "unresolved-contradiction")
                forced = _approved(store,
                    c["candidate_uuid"], founder_ref="founder",
                    conflict_override="both for now")
                self.assertEqual(len(store.learning_conflicts()["contradictions"]), 1,
                                 "an overridden reversal stays visible")
                res = store.retrieve_learning_rules("pushing to github", context={})
                self.assertTrue(any(r["conflicts_with"] for r in res["results"]),
                                "retrieval has to mark the side it shows")
                self.assertTrue(res["conflicts"])
                self.assertEqual(forced["state"], "approved")

    def test_an_agreeing_rule_is_not_refused_as_a_contradiction(self):
        """A refusal that fires on rules which plainly agree is worse than no
        refusal: the founder can only get past it by overriding a conflict that
        does not exist. "no exceptions" intensifies a rule, it does not reverse
        one, so this pair is a duplicate and has to be named as one."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store, "always run the tests, no exceptions",
                           trigger="running tests")
                c = store.capture_learning_candidate(
                    "manual", trigger="running tests",
                    action="always run the tests", scope_type="global")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    _approved(store, c["candidate_uuid"],
                                                     founder_ref="founder")
                self.assertEqual(ctx.exception.reason, "duplicate-rule")

    def test_supersession_refuses_a_successor_that_cannot_speak(self):
        """The CLI prints "the successor is returned in its place from now on".
        Superseding with a rule that can never be retrieved makes that sentence
        false and silences the live instruction with nothing standing in."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                live = self._rule(store, "check optionals first",
                                  trigger="reviewing swift code")
                dead = self._rule(store, "check nullability last",
                                  trigger="reviewing kotlin code")
                _state_changed(store, dead["rule_uuid"], "forgotten",
                              reason="dropped kotlin")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.change_learning_rule_state(
                        live["rule_uuid"], "superseded", reason="replaced",
                        successor_prefix=dead["rule_uuid"])
                self.assertEqual(ctx.exception.reason, "successor-cannot-speak")
                self.assertEqual(
                    store.get_learning_rule(live["rule_uuid"])["state"], "approved",
                    "a refused supersession leaves the live rule speaking")
                self.assertEqual(store.list_learning_edges(), [])
                res = store.retrieve_learning_rules("reviewing swift code",
                                                    context={})
                self.assertEqual([r["rule_uuid"] for r in res["results"]],
                                 [live["rule_uuid"]])

    def test_verify_reports_a_successor_that_went_quiet_afterwards(self):
        """Forgetting the successor is a legal move made later, so the up-front
        refusal cannot catch it. Nothing else in the store would ever mention
        that the replaced instruction now has nothing standing in for it."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                old = self._rule(store, "check optionals first",
                                 trigger="reviewing swift code")
                new = self._rule(store, "check optionals and force unwraps",
                                 trigger="reviewing swift code",
                                 override="replacing the old one")
                _state_changed(
                    store, old["rule_uuid"], "superseded", reason="sharper wording",
                    successor_prefix=new["rule_uuid"])
                _state_changed(store, new["rule_uuid"], "forgotten",
                              reason="dropped swift")
                codes = [f["code"] for f in store.learning_verify()["findings"]]
                self.assertIn("dead-successor", codes)
                self.assertFalse(store.learning_verify()["ok"])
                self.assertIn("dead-successor", store.LEARNING_CHECKS)

    def test_cyclic_supersession_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                a = self._rule(store, "prefer short commit messages",
                               trigger="writing a commit message")
                b = self._rule(store, "prefer imperative commit messages",
                               trigger="writing a commit message")
                _state_changed(store, a["rule_uuid"], "superseded",
                              successor_prefix=b["rule_uuid"])
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.change_learning_rule_state(b["rule_uuid"], "superseded",
                                                     successor_prefix=a["rule_uuid"])
                self.assertEqual(ctx.exception.reason, "supersession-cycle")
                self.assertEqual(store.get_learning_rule(b["rule_uuid"])["state"],
                                 "approved")

    def test_self_edges_are_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                a = self._rule(store, self.ALWAYS)
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.link_learning_rules(a["rule_uuid"], a["rule_uuid"],
                                              "contradicts")
                self.assertEqual(ctx.exception.reason, "self-edge")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.change_learning_rule_state(
                        a["rule_uuid"], "superseded",
                        successor_prefix=a["rule_uuid"])
                self.assertEqual(ctx.exception.reason, "self-supersession")
                self.assertEqual(store.list_learning_edges(), [])

    def test_a_supersedes_edge_cannot_be_written_as_a_plain_link(self):
        """Otherwise a rule could claim to be replaced while still being
        injected, which is a lie the store would then keep telling."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                a = self._rule(store, self.ALWAYS)
                b = self._rule(store, "prefer short commit messages",
                               trigger="writing a commit message")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.link_learning_rules(a["rule_uuid"], b["rule_uuid"],
                                              "supersedes")
                self.assertEqual(ctx.exception.reason, "use-supersede")

    def test_a_declared_conflict_counts_even_when_words_do_not_collide(self):
        """The detector cannot see that tabs and spaces fight. The founder can,
        and what he declares is treated exactly like what was detected."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                a = self._rule(store, "indent with tabs", trigger="writing Python")
                b = self._rule(store, "indent with four spaces",
                               trigger="writing Python")
                self.assertEqual(store.learning_conflicts()["contradictions"], [],
                                 "lexical comparison honestly cannot see this one")
                store.link_learning_rules(a["rule_uuid"], b["rule_uuid"],
                                          "contradicts", note="pick one")
                pairs = store.learning_conflicts()["contradictions"]
                self.assertEqual(len(pairs), 1)
                self.assertEqual(pairs[0]["declared"], "contradicts")
                self.assertFalse(store.learning_verify()["ok"])

    def test_forgotten_and_deprecated_rules_create_no_active_conflict(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                a = self._rule(store, self.ALWAYS)
                b = self._rule(store, self.NEVER, override="both for now")
                self.assertEqual(len(store.learning_conflicts()["contradictions"]), 1)
                _state_changed(store, a["rule_uuid"], "deprecated",
                              reason="old")
                self.assertEqual(store.learning_conflicts()["contradictions"], [],
                                 "a rule that cannot be injected cannot conflict")
                _state_changed(store, a["rule_uuid"], "forgotten")
                self.assertEqual(store.learning_conflicts()["contradictions"], [])
                self.assertTrue(store.learning_verify()["ok"])

    def test_retrieval_surfaces_a_conflict_and_returns_both_sides(self):
        """The tool never picks a side. Dropping or demoting one of two
        contradictory rules would be this code deciding which of the founder's
        instructions is the real one."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                a = self._rule(store, self.ALWAYS)
                b = self._rule(store, self.NEVER, override="both for now")
                res = store.retrieve_learning_rules(self.TRIGGER, context={})
                got = set(r["rule_uuid"] for r in res["results"])
                self.assertEqual(got, {a["rule_uuid"], b["rule_uuid"]})
                self.assertEqual(len(res["conflicts"]), 1)
                for r in res["results"]:
                    self.assertTrue(r["conflicts_with"],
                                    "each side has to say it is contradicted")

    def test_conflict_output_carries_no_capture_text(self):
        """Conflict reports get read out and pasted into notes. Rule text is the
        founder's approved words; raw_text and evidence excerpts are not."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store, self.ALWAYS)
                c = store.capture_learning_candidate(
                    "manual", trigger=self.TRIGGER, action=self.NEVER,
                    raw_text="SECRETPROSE about a named client",
                    scope_type="global")
                _approved(store,
                    c["candidate_uuid"], founder_ref="founder",
                    conflict_override="both for now")
                blob = json.dumps(store.learning_conflicts())
                self.assertNotIn("SECRETPROSE", blob)
                side = store.learning_conflicts()["contradictions"][0]["a"]
                self.assertEqual(sorted(side),
                                 ["action", "rule_uuid", "scope", "severity",
                                  "state", "trigger"],
                                 "a conflict side is a closed set of display fields; "
                                 "adding one is a redaction decision")

    def test_verify_reports_a_broken_edge_and_a_missing_current_version(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                a = self._rule(store, self.ALWAYS)
                b = self._rule(store, "prefer short commit messages",
                               trigger="writing a commit message")
                store.link_learning_rules(a["rule_uuid"], b["rule_uuid"],
                                          "supports", note="related")
                self.assertTrue(store.learning_verify()["ok"])
                # Damage the store BEHIND the API, which is the only way these
                # states arise: an older build, a partial restore, a hand edit.
                store.conn.execute("PRAGMA foreign_keys=OFF")
                store.conn.execute("UPDATE learning_edges SET to_rule_uuid='gone'")
                store.conn.execute("UPDATE learning_rules SET current_version=7 "
                                   "WHERE rule_uuid=?", (a["rule_uuid"],))
                store.conn.commit()
                codes = [f["code"] for f in store.learning_verify()["findings"]]
                self.assertIn("broken-edge", codes)
                self.assertIn("missing-current-version", codes)

    def test_verify_reports_a_rule_with_no_approval_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                a = self._rule(store, self.ALWAYS)
                store.conn.execute("DELETE FROM learning_evidence WHERE rule_uuid=? "
                                   "AND evidence_type='founder_approval'",
                                   (a["rule_uuid"],))
                store.conn.commit()
                res = store.learning_verify()
                self.assertFalse(res["ok"])
                self.assertIn("no-approval-evidence",
                              [f["code"] for f in res["findings"]])

    def test_verify_names_every_check_it_ran_including_fts(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                res = store.learning_verify()
                self.assertTrue(res["ok"])
                self.assertIn("fts-drift", res["checks"])
                self.assertTrue(any("fts-drift" in n for n in res["notes"]),
                                "a check that finds nothing because there is nothing "
                                "to check has to say so, not stay silent")

    def test_resolving_a_conflict_records_why_one_rule_stood_down(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                a = self._rule(store, self.ALWAYS)
                b = self._rule(store, self.NEVER, override="both for now")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.resolve_learning_conflict(a["rule_uuid"], b["rule_uuid"],
                                                    "contradicted", reason="  ")
                self.assertEqual(ctx.exception.reason, "no-reason")
                _conflict_resolved(store, a["rule_uuid"], b["rule_uuid"],
                                   "contradicted",
                                   reason="the newer one stands")
                self.assertEqual(store.get_learning_rule(a["rule_uuid"])["state"],
                                 "contradicted")
                self.assertTrue(store.learning_verify()["ok"])
                edges = store.list_learning_edges(a["rule_uuid"])
                self.assertTrue(any("newer one stands" in e["note"] for e in edges))


class TestLoop7ApplicationLifecycle(unittest.TestCase):
    """Loop 7. learning_applications stops being an empty table.

    The done gate for this loop is one question: for a given task, which rules
    were retrieved, shown, followed, ignored, and why. Every test here is one
    part of that answer, and the classification tests deliberately include the
    cases where the honest answer is that there is not enough evidence."""

    TRIGGER = "writing an executive update"
    ACTION = "state customer impact before technical detail"

    def _rule(self, store, action=None, trigger=None, severity="soft",
              rule_type="preference", scope_type="global", scope_key=""):
        c = store.capture_learning_candidate(
            "manual", trigger=trigger or self.TRIGGER,
            action=action or self.ACTION,
            because="the founder said so", scope_type=scope_type,
            scope_key=scope_key)
        return _approved(store,
            c["candidate_uuid"], founder_ref="founder in chat",
            severity=severity, rule_type=rule_type)

    def _count(self, store):
        return store.conn.execute(
            "SELECT COUNT(*) AS n FROM learning_applications").fetchone()["n"]

    # -- recording ----------------------------------------------------

    def test_retrieval_without_recording_creates_no_rows(self):
        """The read path stays free of consequence even now that a write path
        exists next to it. Asking what applies is not applying anything."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store)
                res = store.retrieve_learning_rules("writing an executive update")
                self.assertEqual(len(res["results"]), 1)
                self.assertEqual(self._count(store), 0)
                self.assertEqual(store.list_learning_applications(), [])

    def test_recording_creates_one_row_per_returned_rule_version(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = self._rule(store)
                res = store.record_learning_applications(
                    "writing an executive update", session_id="S1")
                self.assertEqual(res["recorded"], 1)
                self.assertEqual(res["record_error"], "")
                apps = store.list_learning_applications(session_id="S1")
                self.assertEqual(len(apps), 1)
                self.assertEqual(apps[0]["rule_uuid"], rule["rule_uuid"])
                self.assertEqual(apps[0]["rule_version"], 1)
                self.assertEqual(apps[0]["retrieval_rank"], 1)
                self.assertEqual(apps[0]["shown_to_model"], 1)
                self.assertEqual(apps[0]["disposition"], "unknown")
                self.assertEqual(apps[0]["scope_match"], "global")

    def test_recording_is_idempotent_per_task_rule_version_and_session(self):
        """A model that re-reads its rules mid-task has not applied them twice.
        Without this, every re-read inflates whatever the applications table is
        later asked to measure."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store)
                first = store.record_learning_applications(
                    "writing an executive update", session_id="S1")
                second = store.record_learning_applications(
                    "writing an executive update", session_id="S1")
                self.assertEqual((first["recorded"], first["already_recorded"]), (1, 0))
                self.assertEqual((second["recorded"], second["already_recorded"]), (0, 1))
                self.assertEqual(self._count(store), 1)
                self.assertEqual(first["applications"], second["applications"])

    def test_a_second_session_records_its_own_row(self):
        """Idempotency is per session on purpose: the same rule surfaced for
        the same task in a DIFFERENT session is a second application, and
        collapsing the two would erase one of the two chances to comply."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store)
                store.record_learning_applications(
                    "writing an executive update", session_id="S1")
                store.record_learning_applications(
                    "writing an executive update", session_id="S2")
                self.assertEqual(self._count(store), 2)

    def test_a_new_rule_version_records_a_new_application(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = self._rule(store)
                store.record_learning_applications(
                    "writing an executive update", session_id="S1")
                _edited(store, rule["rule_uuid"], 1,
                        action="lead with the customer number",
                        change_reason="sharper")
                store.record_learning_applications(
                    "writing an executive update", session_id="S1")
                versions = sorted(a["rule_version"]
                                  for a in store.list_learning_applications())
                self.assertEqual(versions, [1, 2])

    def test_recording_never_breaks_a_retrieval(self):
        """A learning system that can make retrieval FAIL is worse than one
        that forgets. The rules come back whatever happens to the bookkeeping,
        and the caller is told plainly that the write did not land."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store)
                boom = bs.OwnershipRefused("db-busy", "the store is busy")

                real = bs._exec

                def failing(store_arg, sql, params=()):
                    if sql.lstrip().upper().startswith("INSERT INTO LEARNING_APPLICATIONS"):
                        raise boom
                    return real(store_arg, sql, params)

                with mock.patch.object(bs, "_exec", failing):
                    res = store.record_learning_applications(
                        "writing an executive update", session_id="S1")
                self.assertEqual(len(res["results"]), 1,
                                 "the rules must survive a failed write")
                self.assertIn("busy", res["record_error"])
                self.assertEqual(res["recorded"], 0)
                self.assertEqual(self._count(store), 0,
                                 "a failed recording leaves nothing partial behind")

    def test_a_corrupt_store_is_never_absorbed_into_record_error(self):
        """The narrow except is narrow on purpose: a damaged database is not a
        degraded write to shrug off, and hiding it behind a retrieval that
        looks successful is how a corrupt store keeps being used."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store)
                real = bs._exec

                def failing(store_arg, sql, params=()):
                    if sql.lstrip().upper().startswith("INSERT INTO LEARNING_APPLICATIONS"):
                        raise bs.StoreCorrupt("the database is damaged")
                    return real(store_arg, sql, params)

                with mock.patch.object(bs, "_exec", failing):
                    with self.assertRaises(bs.StoreCorrupt):
                        store.record_learning_applications(
                            "writing an executive update", session_id="S1")

    def test_an_unknown_work_record_is_refused_without_losing_the_rules(self):
        """Refused loudly, and NOT over the top of the answer.

        Resolving the prefix used to run before retrieval and outside the block
        that absorbs write failures, so a mistyped id raised past the whole
        call and the caller got no founder rules at all. Resolving --record is
        part of the WRITE: it fails like one, in record_error, with the rules
        intact and nothing written."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store)
                res = store.record_learning_applications(
                    "writing an executive update", session_id="S1",
                    record_prefix="deadbeef")
                self.assertTrue(res["results"],
                                "a bad --record swallowed the founder rules")
                self.assertIn("no record matches 'deadbeef'",
                              res["record_error"])
                self.assertEqual(res["record_error_kind"], "not-found")
                self.assertEqual((res["recorded"], res["linked"]), (0, 0))
                self.assertEqual(self._count(store), 0)

    def test_a_late_work_record_is_attached_to_the_application_that_exists(self):
        """The order real work happens in: retrieve the rules, THEN claim the
        work record, then re-run with --record. If the second call discarded
        the link because the row already existed, nothing anywhere could ever
        attach it, and the application would be permanently unlinked from the
        work it belongs to."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store)
                first = store.record_learning_applications(
                    "writing an executive update", session_id="S1")
                app_id = first["applications"][0]
                self.assertIsNone(
                    store.get_learning_application(app_id)["record_uuid"])
                rec = store.claim("report", "ephemeral", "write the report",
                                  ["docs/report.md"])
                second = store.record_learning_applications(
                    "writing an executive update", session_id="S1",
                    record_prefix=rec.lifecycle_uuid[:8])
                self.assertEqual(
                    (second["recorded"], second["already_recorded"],
                     second["linked"]), (0, 1, 1))
                self.assertEqual(self._count(store), 1)
                self.assertEqual(
                    store.get_learning_application(app_id)["record_uuid"],
                    rec.lifecycle_uuid)
                self.assertEqual(
                    [a["application_uuid"] for a in
                     store.list_learning_applications(
                         record_prefix=rec.lifecycle_uuid[:8])],
                    [app_id], "the row has to be findable BY that record")
                third = store.record_learning_applications(
                    "writing an executive update", session_id="S1",
                    record_prefix=rec.lifecycle_uuid[:8])
                self.assertEqual(third["linked"], 0,
                                 "attaching the same link twice links nothing")

    def test_a_second_work_record_gets_its_own_row_and_moves_nothing(self):
        """TWO UNITS OF WORK, TWO ROWS. And the first link is never touched.

        Completing a missing link is repair; changing one is rewriting history.
        The old code enforced that half by REFUSING the second work record
        outright, which protected row one and left the second unit of work with
        no row at all: exit 3 forever, and nothing that could ever answer
        "was this rule followed" for it. The key now includes the work record,
        so the second unit gets a row of its own and the first row is not a
        candidate for the update in the first place."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store)
                first = store.claim("report", "ephemeral", "write the report",
                                    ["docs/report.md"])
                res = store.record_learning_applications(
                    "writing an executive update", session_id="S1",
                    record_prefix=first.lifecycle_uuid[:8])
                app_id = res["applications"][0]
                other = store.claim("other", "ephemeral", "something else",
                                    ["docs/other.md"])
                again = store.record_learning_applications(
                    "writing an executive update", session_id="S1",
                    record_prefix=other.lifecycle_uuid[:8])
                self.assertEqual(again["record_error"], "")
                self.assertEqual((again["recorded"], again["linked"]), (1, 0))
                self.assertEqual(self._count(store), 2)
                self.assertEqual(
                    store.get_learning_application(app_id)["record_uuid"],
                    first.lifecycle_uuid,
                    "the first work record's row must be left exactly as it was")
                self.assertEqual(
                    store.get_learning_application(
                        again["applications"][0])["record_uuid"],
                    other.lifecycle_uuid)
                # And re-running for the second unit stays idempotent.
                third = store.record_learning_applications(
                    "writing an executive update", session_id="S1",
                    record_prefix=other.lifecycle_uuid[:8])
                self.assertEqual((third["recorded"], third["already_recorded"]),
                                 (0, 1))
                self.assertEqual(self._count(store), 2)

    def test_apply_with_no_record_reports_the_work_record_it_matched(self):
        """The ambiguity the fingerprint cannot resolve is DISCLOSED.

        With no record supplied the key is the old four, so an existing row may
        belong to a different unit of work worded the same way. The caller is
        told which work record that row belongs to rather than handed a bare
        already-recorded count that reads as success for the work in hand."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store)
                rec = store.claim("report", "ephemeral", "write the report",
                                  ["docs/report.md"])
                store.record_learning_applications(
                    "writing an executive update", session_id="S1",
                    record_prefix=rec.lifecycle_uuid[:8])
                bare = store.record_learning_applications(
                    "writing an executive update", session_id="S1")
                self.assertEqual(bare["already_recorded"], 1)
                self.assertEqual(bare["already_linked_records"],
                                 [rec.lifecycle_uuid])
                self.assertEqual(self._count(store), 1)

    # -- immutability -------------------------------------------------

    def test_editing_a_rule_does_not_rewrite_old_application_history(self):
        """Invariant L8, made structural rather than promised. An application
        records what the model was ACTUALLY shown; a rule edited tomorrow may
        not retroactively change what happened yesterday."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = self._rule(store)
                store.record_learning_applications(
                    "writing an executive update", session_id="S1")
                _edited(store, rule["rule_uuid"], 1,
                        action="do something else entirely",
                        change_reason="the founder changed his mind")
                apps = store.list_learning_applications(session_id="S1")
                self.assertEqual(len(apps), 1)
                self.assertEqual(apps[0]["rule_version"], 1)
                self.assertEqual(apps[0]["action_text"], self.ACTION)
                self.assertEqual(
                    store.get_learning_rule(rule["rule_uuid"])["action_text"],
                    "do something else entirely")

    def test_an_application_pointing_at_a_missing_version_is_a_verify_finding(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store)
                store.record_learning_applications(
                    "writing an executive update", session_id="S1")
                self.assertTrue(store.learning_verify()["ok"])
                with self.assertRaises(sqlite3.IntegrityError):
                    store.conn.execute(
                        "UPDATE learning_applications SET rule_version = 9")
                # The foreign key refuses it, and that is the first line of
                # defence. The integrity check below is for the store that
                # arrived damaged anyway, so the constraint is forced off to
                # build one rather than assumed unreachable.
                store.conn.execute("PRAGMA foreign_keys=OFF")
                store.conn.execute(
                    "UPDATE learning_applications SET rule_version = 9")
                store.conn.commit()
                res = store.learning_verify()
                self.assertFalse(res["ok"])
                self.assertIn("application-without-version",
                              [f["code"] for f in res["findings"]])

    # -- disposition --------------------------------------------------

    def test_ignoring_a_gate_rule_requires_a_reason(self):
        """The refusal this loop exists for. A gate quietly skipped and never
        explained is the compliance failure the whole mechanism is meant to
        make visible, and a blank reason would let it pass as bookkeeping."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store, severity="gate")
                res = store.record_learning_applications(
                    "writing an executive update", session_id="S1")
                app_id = res["applications"][0]
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.set_application_disposition(app_id, "ignored")
                self.assertEqual(ctx.exception.reason, "no-ignore-reason")
                self.assertEqual(
                    store.get_learning_application(app_id)["disposition"],
                    "unknown", "a refused disposition must change nothing")
                app = store.set_application_disposition(
                    app_id, "ignored", reason="the founder made a one off exception")
                self.assertEqual(app["disposition"], "ignored")

    def test_ignoring_a_substantial_rule_requires_a_reason(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store, rule_type="safety")
                res = store.record_learning_applications(
                    "writing an executive update", session_id="S1")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.set_application_disposition(res["applications"][0], "ignored")
                self.assertEqual(ctx.exception.reason, "no-ignore-reason")

    def test_ignoring_a_plain_preference_does_not_require_a_reason(self):
        """Proportionality applies to the refusals too. Demanding a written
        justification for skipping a soft preference is the ceremony that makes
        a founder stop using the tool."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store)
                res = store.record_learning_applications(
                    "writing an executive update", session_id="S1")
                app = store.set_application_disposition(res["applications"][0],
                                                        "ignored")
                self.assertEqual(app["disposition"], "ignored")

    def test_following_and_ignoring_land_as_evidence_on_the_rule(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = self._rule(store)
                res = store.record_learning_applications(
                    "writing an executive update", session_id="S1")
                app_id = res["applications"][0]
                store.set_application_disposition(app_id, "followed",
                                                   verification_ref="test:update")
                kinds = [(e["polarity"], e["evidence_type"])
                         for e in store.list_learning_evidence(rule["rule_uuid"])]
                self.assertIn(("support", "verified_application"), kinds)
                store.set_application_disposition(
                    app_id, "ignored", reason="one off exception")
                kinds = [(e["polarity"], e["evidence_type"])
                         for e in store.list_learning_evidence(rule["rule_uuid"])]
                self.assertIn(("contradict", "ignored_application"), kinds)

    def test_repeating_the_same_disposition_does_not_inflate_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = self._rule(store)
                res = store.record_learning_applications(
                    "writing an executive update", session_id="S1")
                app_id = res["applications"][0]
                for _ in range(3):
                    store.set_application_disposition(app_id, "followed")
                n = len([e for e in store.list_learning_evidence(rule["rule_uuid"])
                         if e["evidence_type"] == "verified_application"])
                self.assertEqual(n, 1)

    def test_flipping_a_disposition_back_and_forth_does_not_inflate_evidence(self):
        """The repeat guard only ever blocked verbatim repeats. Alternating
        followed and ignored on ONE application (the realistic "I closed that
        wrong, fix it") used to append a row per flip, so a rule with a single
        application could be handed unbounded support. That ledger is what the
        founder reads and what admits a rule to 'confirmed'."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = self._rule(store)
                res = store.record_learning_applications(
                    "writing an executive update", session_id="S1")
                app_id = res["applications"][0]
                for i in range(5):
                    store.set_application_disposition(
                        app_id, "ignored", reason="flip %d" % i)
                    store.set_application_disposition(app_id, "followed")
                kinds = [e["evidence_type"]
                         for e in store.list_learning_evidence(rule["rule_uuid"])]
                self.assertEqual(kinds.count("verified_application"), 1)
                self.assertEqual(kinds.count("ignored_application"), 0,
                                 "the losing side of a flip is a claim the "
                                 "application no longer makes")
                self.assertEqual(
                    len(store.list_learning_applications(session_id="S1")), 1)

    def test_a_disposition_that_asserts_nothing_removes_the_stale_evidence(self):
        """Reopening an application as unknown withdraws its claim. Leaving the
        old support row behind would keep counting an application that no
        longer says anything, including towards promotion to 'confirmed'."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = self._rule(store)
                res = store.record_learning_applications(
                    "writing an executive update", session_id="S1")
                app_id = res["applications"][0]
                store.set_application_disposition(app_id, "followed")
                store.set_application_disposition(app_id, "unknown")
                kinds = [e["evidence_type"]
                         for e in store.list_learning_evidence(rule["rule_uuid"])]
                self.assertEqual(kinds, ["founder_approval"])
                store.set_application_disposition(app_id, "not_relevant")
                kinds = [e["evidence_type"]
                         for e in store.list_learning_evidence(rule["rule_uuid"])]
                self.assertEqual(kinds, ["founder_approval"])

    def test_two_applications_of_one_rule_each_keep_their_own_evidence(self):
        """The dedupe is per APPLICATION, not per rule. Two genuine
        applications are two genuine pieces of evidence, and collapsing them
        would undercount a rule that really is working."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = self._rule(store)
                a = store.record_learning_applications(
                    "writing an executive update", session_id="S1")
                b = store.record_learning_applications(
                    "writing an executive update", session_id="S2")
                self.assertNotEqual(a["applications"], b["applications"])
                store.set_application_disposition(a["applications"][0], "followed")
                store.set_application_disposition(b["applications"][0], "followed")
                kinds = [e["evidence_type"]
                         for e in store.list_learning_evidence(rule["rule_uuid"])]
                self.assertEqual(kinds.count("verified_application"), 2)

    def test_an_unknown_disposition_or_outcome_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store)
                res = store.record_learning_applications(
                    "writing an executive update", session_id="S1")
                app_id = res["applications"][0]
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.set_application_disposition(app_id, "obeyed")
                self.assertEqual(ctx.exception.reason, "bad-disposition")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.set_application_disposition(app_id, "followed",
                                                       outcome="great")
                self.assertEqual(ctx.exception.reason, "bad-outcome")

    # -- classification -----------------------------------------------

    def test_the_five_failure_classes_each_have_a_fixture(self):
        """One fixture per class, in one store, so the classifier is exercised
        against a real lifecycle rather than against hand-built dicts."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                broad = self._rule(store, action="mention the deployment window",
                                   trigger="writing an executive update about deploys")
                ignored = self._rule(store, action="never send it on a friday",
                                     trigger="writing an executive update on a friday",
                                     severity="gate")
                bad = self._rule(store, action="open with a two page appendix",
                                 trigger="writing an executive update appendix")
                unknown = self._rule(store, action="use the customer name early",
                                     trigger="writing an executive update naming customers")
                missed = self._rule(store, action="attach the revenue number",
                                    trigger="writing an executive update revenue")
                query = ("writing an executive update about deploys on a friday "
                         "with an appendix naming customers and revenue")
                res = store.record_learning_applications(query, session_id="S1",
                                                          limit=5)
                self.assertEqual(res["recorded"], 5)
                by_rule = dict((a["rule_uuid"], a["application_uuid"])
                               for a in store.list_learning_applications(session_id="S1"))
                # The retrieval returned all five. The fifth then loses its
                # application row, which is what a relevance miss actually is:
                # the rule was eligible and inside the limit, and the ledger
                # cannot show it reached the model. It used to be built by
                # adding a rule afterwards and backdating it, which made
                # today's corpus bigger than the count the run recorded, and
                # that is drift the classifier now refuses to grade at all
                # (FIX ROUND P6).
                store.conn.execute(
                    "DELETE FROM learning_applications WHERE rule_uuid=?",
                    (missed["rule_uuid"],))
                store.conn.commit()
                store.set_application_disposition(
                    by_rule[broad["rule_uuid"]], "not_relevant")
                store.set_application_disposition(
                    by_rule[ignored["rule_uuid"]], "ignored",
                    reason="the founder overrode it")
                store.set_application_disposition(
                    by_rule[bad["rule_uuid"]], "followed", outcome="rework")
                # `unknown` keeps its default disposition on purpose.
                out = store.classify_learning_applications()
                got = dict((a["rule_uuid"], a["classification"])
                           for a in out["applications"])
                self.assertEqual(got[broad["rule_uuid"]], "scope_error")
                self.assertEqual(got[ignored["rule_uuid"]], "compliance_failure")
                self.assertEqual(got[bad["rule_uuid"]], "bad_rule")
                self.assertEqual(got[unknown["rule_uuid"]], "not_decidable")
                self.assertEqual(
                    [m["rule_uuid"] for m in out["retrieval_misses"]],
                    [missed["rule_uuid"]])
                for name in bs._learning().FAILURE_CLASSES:
                    self.assertIn(name, out["counts"],
                                  "every class this build knows must be counted")

    def test_a_rule_approved_after_the_task_is_not_a_retrieval_miss(self):
        """Without this the classifier blames every past task for not knowing
        today's rules, which would make the miss count meaningless."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store)
                store.record_learning_applications(
                    "writing an executive update", session_id="S1", limit=1)
                later = self._rule(store, action="keep it under one page",
                                    trigger="writing an executive update briefly")
                store.conn.execute(
                    "UPDATE learning_rules SET founder_approved_at='2099-01-01T00:00:00Z' "
                    "WHERE rule_uuid=?", (later["rule_uuid"],))
                store.conn.commit()
                out = store.classify_learning_applications()
                self.assertEqual(out["retrieval_misses"], [])

    def test_a_task_with_no_kept_text_is_not_decidable(self):
        """Missing evidence returns not_decidable rather than a guess, which is
        the whole difference between a classifier and an opinion."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store)
                # More distinct terms than a run is allowed to keep, so the
                # run stores none and nothing can be re-ranked. Since FIX ROUND
                # P6 the run keeps the task's TERMS rather than its text, so
                # "no kept text" is this case, not an empty excerpt argument.
                huge = "writing an executive update " + " ".join(
                    "term%d" % i
                    for i in range(bs._learning().MAX_QUERY_TERMS + 1))
                store.record_learning_applications(huge, session_id="S1",
                                                   task_excerpt="")
                out = store.classify_learning_applications()
                self.assertEqual(out["retrieval_misses"], [])
                self.assertEqual(len(out["not_decidable_tasks"]), 1)
                self.assertIn("no task text",
                              out["not_decidable_tasks"][0]["reason"])

    def test_ignored_but_never_shown_is_not_a_compliance_failure(self):
        L = bs._learning()
        self.assertEqual(
            L.classify_application("ignored", False, "pending")[0], "not_decidable")
        self.assertEqual(
            L.classify_application("ignored", True, "pending")[0], "compliance_failure")

    def test_followed_into_an_accepted_outcome_is_not_a_finding(self):
        L = bs._learning()
        self.assertIsNone(L.classify_application("followed", True, "accepted")[0])
        self.assertEqual(
            L.classify_application("followed", True, "pending")[0], "not_decidable")

    # -- proportionality ----------------------------------------------

    def test_the_trivial_task_bypass_is_explicit_and_records_nothing(self):
        """A task that decided not to retrieve must never appear in the outcome
        data, or the applications table fills with work that never happened."""
        L = bs._learning()
        decision = L.retrieval_advised({}, gate_rules_exist=False)
        self.assertFalse(decision["advised"])
        self.assertTrue(decision["reasons"])
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store)
                self.assertEqual(self._count(store), 0)

    def test_a_live_gate_rule_advises_retrieval_even_on_a_trivial_task(self):
        L = bs._learning()
        self.assertTrue(L.retrieval_advised({}, gate_rules_exist=True)["advised"])
        for signal in L.RETRIEVAL_SIGNALS:
            self.assertTrue(L.retrieval_advised({signal: True})["advised"], signal)

    def test_an_unknown_signal_is_named_rather_than_silently_ignored(self):
        L = bs._learning()
        out = L.retrieval_advised({"vibes": True})
        self.assertFalse(out["advised"])
        self.assertEqual(out["unknown_signals"], ["vibes"])


class TestLoop5NoVerbatimTaskExcerptByDefault(unittest.TestCase):
    """LOOP 5, the headline defect: an ordinary `apply` used to put up to 500
    characters of the founder's VERBATIM task prose into
    learning_applications.task_excerpt, unjustified and with no opt-out.
    The default is now the bounded, deduplicated search-term set; a
    verbatim, readable excerpt is available only when the caller explicitly
    passes task_excerpt (bm_learn.py's --store-excerpt)."""

    TRIGGER = "writing an executive update"
    ACTION = "state customer impact before technical detail"
    TASK = ("CANARY-TASK-PROMPT writing an executive update about "
           "/Users/j/Dev Work/memo.md")

    def _rule(self, store):
        c = store.capture_learning_candidate(
            "manual", trigger=self.TRIGGER, action=self.ACTION,
            because="the founder said so", scope_type="global", scope_key="")
        return _approved(store, c["candidate_uuid"], founder_ref="founder in chat")

    def test_default_apply_stores_no_verbatim_task_prose(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store)
                store.record_learning_applications(self.TASK, session_id="S1")
                apps = store.list_learning_applications(session_id="S1")
                self.assertEqual(len(apps), 1)
                self.assertNotIn("CANARY-TASK-PROMPT", apps[0]["task_excerpt"])
                self.assertNotIn("Dev Work", apps[0]["task_excerpt"])
                # The bounded term set is still there, so a past retrieval
                # can be re-ranked: it is a real value, not blanked out.
                self.assertTrue(apps[0]["task_excerpt"])

    def test_explicit_opt_in_still_stores_a_readable_excerpt(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store)
                store.record_learning_applications(
                    self.TASK, session_id="S1", task_excerpt=self.TASK)
                apps = store.list_learning_applications(session_id="S1")
                self.assertIn("CANARY-TASK-PROMPT", apps[0]["task_excerpt"])

    def test_calibrated_reverting_the_default_leaks_the_verbatim_task(self):
        """CALIBRATION for the headline defect: put the pre-fix default
        (excerpt = query) back and the verbatim prompt returns; restore the
        shipped default and it is gone again."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store)
                store.record_learning_applications(self.TASK, session_id="S1")
                shipped = store.list_learning_applications(session_id="S1")
                self.assertNotIn("CANARY-TASK-PROMPT", shipped[0]["task_excerpt"])

        # The calibration reverts the one line the fix changed: forcing
        # query_terms to hand back the raw text it was given, rather than
        # the tokenized term set, reproduces the pre-fix "excerpt = query"
        # behaviour without touching record_learning_applications itself.
        L = bs._learning()
        with mock.patch.object(L, "query_terms", lambda t, **k: t):
            with tempfile.TemporaryDirectory() as d:
                with bs.Store(d) as store:
                    self._rule(store)
                    store.record_learning_applications(self.TASK, session_id="S1")
                    reverted = store.list_learning_applications(session_id="S1")
                    self.assertIn("CANARY-TASK-PROMPT",
                                 reverted[0]["task_excerpt"],
                                 "REINJECTION CHECK: forcing query_terms to "
                                 "return the raw query must leak the prompt "
                                 "again, proving the default is what guards it")
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store)
                store.record_learning_applications(self.TASK, session_id="S1")
                restored = store.list_learning_applications(session_id="S1")
                self.assertNotIn("CANARY-TASK-PROMPT",
                                restored[0]["task_excerpt"])


class TestLoop8ExternalGrading(unittest.TestCase):
    """Loop 8. The difference between storage growth and learning.

    Everything before this loop can be produced by the session being graded:
    it retrieves its own rules, records its own applications, and closes them
    'followed'. These tests are about the three signals it cannot fake, and
    about the one thing they have to deliver: telling a retrieval miss from a
    compliance failure from a bad rule, because those are three different
    repairs and a single 'corrections went up' number names none of them."""

    TRIGGER = "writing an executive update"
    ACTION = "state customer impact before technical detail"

    def _rule(self, store, state=None):
        c = store.capture_learning_candidate(
            "manual", trigger=self.TRIGGER, action=self.ACTION,
            because="the board reads the first line", scope_type="global")
        rule = _approved(store,
            c["candidate_uuid"], founder_ref="founder in chat")
        if state:
            store.add_learning_evidence(rule["rule_uuid"], "support",
                                        "manual_review",
                                        excerpt="seen to work once")
            # 'settled' is reachable only through 'confirmed'; the state
            # machine refuses the shortcut, so the helper walks the path.
            for step in (("confirmed", "settled") if state == "settled"
                         else (state,)):
                rule = store.change_learning_rule_state(
                    rule["rule_uuid"], step, reason="held up in use")
        return rule

    def _record(self, store, name="exec-update", session="S1", path="notes.md"):
        return store.claim(name, lifetime="ephemeral",
                           objective="ship the executive update",
                           files=[os.path.join(store.root, path)],
                           session_id=session)

    def _repeat(self, store, session="S1", record_uuid=None, text=None):
        return store.capture_learning_candidate(
            "explicit_correction", trigger=self.TRIGGER,
            action=text or self.ACTION, because="said it again",
            scope_type="global", session_id=session, record_uuid=record_uuid)

    # -- outcome events linking back --------------------------------------

    def test_rework_links_to_the_applications_of_that_work(self):
        """The whole point of the event. Without the link it is a note that
        something went wrong; with it, the rules that were supposed to prevent
        it are named."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = self._rule(store)
                rec = self._record(store)
                res = store.record_learning_applications(
                    self.TRIGGER, session_id="S1",
                    record_prefix=rec.lifecycle_uuid)
                store.set_application_disposition(res["applications"][0],
                                                  "followed")
                ev = store.record_outcome_event(
                    "rework", rec.lifecycle_uuid, session_id="S1",
                    summary="the board sent it back")
                self.assertEqual(len(ev["linked_applications"]), 1)
                link = ev["linked_applications"][0]
                self.assertEqual(link["rule_uuid"], rule["rule_uuid"])
                self.assertEqual(link["classification"], "bad_rule")
                app = store.get_learning_application(link["application_uuid"])
                self.assertEqual(app["outcome"], "rework")
                self.assertEqual(ev["candidate"]["status"], "pending",
                                 "an outcome event is evidence for review, "
                                 "never a rule")

    def test_an_escaped_defect_links_to_the_exact_rule_version_applied(self):
        """A rule edited after the fact must not be able to rewrite which text
        was actually shown when the defect escaped."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = self._rule(store)
                rec = self._record(store)
                store.record_learning_applications(
                    self.TRIGGER, session_id="S1",
                    record_prefix=rec.lifecycle_uuid)
                _edited(store, rule["rule_uuid"], 1,
                        action="lead with the number",
                        change_reason="tightened")
                ev = store.record_outcome_event(
                    "escaped_defect", rec.lifecycle_uuid, session_id="S1",
                    defect_class="stale-doc", summary="found later")
                link = ev["linked_applications"][0]
                self.assertEqual(link["rule_version"], 1)
                self.assertEqual(store.get_learning_rule(
                    rule["rule_uuid"])["current_version"], 2)
                rows = [e for e in store.list_learning_evidence(rule["rule_uuid"])
                        if e["evidence_uuid"] == link["evidence_uuid"]]
                self.assertEqual(len(rows), 1)
                self.assertIn("rule_version=1", rows[0]["source_ref"])
                self.assertIn("defect_class=stale-doc",
                              ev["candidate"]["source_ref"])

    def test_an_outcome_with_no_applications_is_not_measured_not_zero(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store)
                rec = self._record(store)
                ev = store.record_outcome_event("rework", rec.lifecycle_uuid)
                self.assertEqual(ev["linked_applications"], [])
                self.assertTrue(any("not measured" in n for n in ev["notes"]))

    def test_recording_the_same_outcome_twice_does_not_inflate_the_evidence(self):
        """Evidence counts events, not keystrokes. Otherwise a rule could be
        argued out of 'confirmed' by reporting one rework repeatedly."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = self._rule(store)
                rec = self._record(store)
                res = store.record_learning_applications(
                    self.TRIGGER, session_id="S1",
                    record_prefix=rec.lifecycle_uuid)
                store.set_application_disposition(res["applications"][0],
                                                  "followed")
                first = store.record_outcome_event("rework",
                                                   rec.lifecycle_uuid)
                app = first["linked_applications"][0]["application_uuid"]
                before = len(store.list_learning_evidence(rule["rule_uuid"]))
                store._grade_outcome_link(first["candidate"],
                                          store.get_learning_application(app),
                                          "rework", bs.now_iso(), "rework")
                self.assertEqual(
                    len(store.list_learning_evidence(rule["rule_uuid"])), before)

    def test_the_same_outcome_command_run_twice_stays_one_event(self):
        """The test above proved the private link writer was idempotent. It
        was, and the public path went around it: record_outcome_event minted a
        FRESH candidate every run, so the dedup key (candidate, application)
        never matched and the weekly review's counts grew with keystrokes.
        Found by typing the same command twice against a real store."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store)
                rec = self._record(store)
                res = store.record_learning_applications(
                    self.TRIGGER, session_id="S1",
                    record_prefix=rec.lifecycle_uuid)
                store.set_application_disposition(
                    res["applications"][0], "ignored", reason="in a hurry")
                first = store.record_outcome_event(
                    "rework", rec.lifecycle_uuid, session_id="S1",
                    summary="the board sent it back")
                again = store.record_outcome_event(
                    "rework", rec.lifecycle_uuid, session_id="S1",
                    summary="the board sent it back")
                self.assertEqual(again["candidate_uuid"],
                                 first["candidate_uuid"])
                self.assertTrue(any("same outcome already recorded" in n
                                    for n in again["notes"]),
                                "the founder must be told his second run "
                                "wrote nothing new")
                self.assertEqual(len(store.list_learning_candidates("pending")), 1)
                out = store.learning_loop_failures()
                self.assertEqual(len(out["outcomes_linked_to_rules"]), 1)
                self.assertEqual(len(out["repeated_corrections"]), 1)
                # A genuinely different second rework says so in its own
                # words, and that one is a second event.
                third = store.record_outcome_event(
                    "rework", rec.lifecycle_uuid, session_id="S1",
                    summary="sent back a second time, for a different reason")
                self.assertNotEqual(third["candidate_uuid"],
                                    first["candidate_uuid"])

    def test_an_outcome_never_grades_a_rule_from_different_work(self):
        """Two work records in one session. An outcome on the first must not
        touch a rule that was only ever applied to the second: the report told
        the founder to edit a rule that had been obeyed correctly somewhere
        else entirely."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = self._rule(store, state="confirmed")
                mine = self._record(store)
                other = store.claim("illustrations", lifetime="ephemeral",
                                    objective="draw the onboarding art",
                                    files=[os.path.join(store.root, "b.svg")],
                                    session_id="S1")
                res = store.record_learning_applications(
                    self.TRIGGER, session_id="S1",
                    record_prefix=mine.lifecycle_uuid)
                store.set_application_disposition(
                    res["applications"][0], "followed",
                    verification_ref="test:exec_update_shape")
                ev = store.record_outcome_event(
                    "escaped_defect", other.lifecycle_uuid, session_id="S1",
                    defect_class="lint", summary="a lint error shipped")
                self.assertEqual(ev["linked_applications"], [],
                                 "the rule was never applied to that record")
                self.assertTrue(any("not measured" in n for n in ev["notes"]))
                out = store.learning_rule_outcomes(rule["rule_uuid"])
                self.assertEqual(out["repeated_corrections"], [])
                self.assertEqual(out["evidence_by_polarity"].get("contradict", 0),
                                 0)

    def test_an_application_with_no_record_yet_is_still_graded_by_session(self):
        """The backstop the record-first match must not break: an application
        recorded before the work record was claimed carries only a session,
        and refusing to grade it would report a retrieval miss for work that
        demonstrably did retrieve the rule."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store)
                rec = self._record(store)
                res = store.record_learning_applications(self.TRIGGER,
                                                          session_id="S1")
                store.set_application_disposition(
                    res["applications"][0], "followed",
                    verification_ref="test:exec_update_shape")
                ev = store.record_outcome_event(
                    "rework", rec.lifecycle_uuid, session_id="S1",
                    summary="the board sent it back")
                self.assertEqual(len(ev["linked_applications"]), 1)
                self.assertEqual(ev["linked_applications"][0]["classification"],
                                 "bad_rule")

    # -- repeated corrections ---------------------------------------------

    def test_a_repeat_against_a_settled_rule_that_was_followed_is_a_bad_rule(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = self._rule(store, state="settled")
                res = store.record_learning_applications(self.TRIGGER,
                                                          session_id="S1")
                store.set_application_disposition(res["applications"][0],
                                                  "followed")
                cand = self._repeat(store)
                out = store.detect_repeated_correction(cand["candidate_uuid"],
                                                        record=True)
                self.assertEqual(len(out["repeats"]), 1)
                self.assertEqual(out["repeats"][0]["classification"], "bad_rule")
                self.assertEqual(out["repeats"][0]["polarity"], "contradict")
                self.assertEqual(out["repeats"][0]["rule_uuid"], rule["rule_uuid"])
                app = store.get_learning_application(res["applications"][0])
                self.assertEqual(app["outcome"], "corrected_again")

    def test_a_repeat_with_no_application_of_the_rule_is_a_retrieval_miss(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store, state="confirmed")
                cand = self._repeat(store, session="S9")
                out = store.detect_repeated_correction(cand["candidate_uuid"])
                self.assertEqual(out["repeats"][0]["classification"],
                                 "retrieval_miss")
                self.assertEqual(
                    out["repeats"][0]["polarity"], "neutral",
                    "a rule nobody retrieved is not shown to be wrong, and it "
                    "is not shown to work either. It was written 'support', "
                    "and the promotion gate reads support as 'an independent "
                    "event showing the rule worked', so a rule could reach "
                    "confirmed on proof it was never retrieved. The founder "
                    "restating a preference IS support, and merge_learning_"
                    "candidate writes that row off his own words.")

    def test_a_repeat_after_the_rule_was_shown_and_skipped_is_a_compliance_failure(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store, state="confirmed")
                res = store.record_learning_applications(self.TRIGGER,
                                                          session_id="S1")
                store.set_application_disposition(res["applications"][0],
                                                  "ignored", reason="in a hurry")
                cand = self._repeat(store)
                out = store.detect_repeated_correction(cand["candidate_uuid"])
                self.assertEqual(out["repeats"][0]["classification"],
                                 "compliance_failure")

    def test_a_repeat_after_the_rule_was_called_irrelevant_is_a_scope_error(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store, state="confirmed")
                res = store.record_learning_applications(self.TRIGGER,
                                                          session_id="S1")
                store.set_application_disposition(res["applications"][0],
                                                  "not_relevant")
                cand = self._repeat(store)
                out = store.detect_repeated_correction(cand["candidate_uuid"])
                self.assertEqual(out["repeats"][0]["classification"],
                                 "scope_error")

    def test_a_repeat_with_no_session_and_no_record_is_not_decidable(self):
        """The required refusal. Blaming a rule for work that cannot be
        identified is exactly the confident wrong label this loop exists to
        avoid."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store, state="confirmed")
                store.record_learning_applications(self.TRIGGER, session_id="S1")
                cand = store.capture_learning_candidate(
                    "explicit_correction", trigger=self.TRIGGER,
                    action=self.ACTION, scope_type="global")
                out = store.detect_repeated_correction(cand["candidate_uuid"])
                self.assertEqual(out["repeats"][0]["classification"],
                                 "not_decidable")
                self.assertTrue(any("neither a session nor a work record" in n
                                    for n in out["notes"]))

    def test_an_unrelated_correction_never_blames_a_rule(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store, state="settled")
                cand = store.capture_learning_candidate(
                    "explicit_correction", trigger="choosing the orb colour",
                    action="use warm amber, not blue", scope_type="global",
                    session_id="S1")
                out = store.detect_repeated_correction(cand["candidate_uuid"],
                                                        record=True)
                self.assertEqual(out["repeats"], [])
                self.assertEqual(out["counts"], {})
                self.assertTrue(any("does not repeat" in n for n in out["notes"]))

    def test_a_repeat_of_an_approved_but_unconfirmed_rule_is_not_a_failure(self):
        """An 'approved' rule has never been independently confirmed by
        anything, so a correction repeating it is first evidence rather than a
        loop failure, and grading it as one would manufacture findings out of
        rules that were only just written."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store)
                cand = self._repeat(store)
                out = store.detect_repeated_correction(cand["candidate_uuid"])
                self.assertEqual(out["repeats"], [])
                self.assertEqual(len(out["unsettled_matches"]), 1)
                self.assertEqual(out["unsettled_matches"][0]["state"], "approved")

    def test_asking_whether_something_repeats_writes_nothing(self):
        """Same separation retrieval has. If reviewing a candidate could
        change the ledger, the act of reviewing would manufacture the evidence
        being reviewed."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = self._rule(store, state="confirmed")
                res = store.record_learning_applications(self.TRIGGER,
                                                          session_id="S1")
                store.set_application_disposition(res["applications"][0],
                                                  "followed")
                before = len(store.list_learning_evidence(rule["rule_uuid"]))
                cand = self._repeat(store)
                store.detect_repeated_correction(cand["candidate_uuid"])
                self.assertEqual(
                    len(store.list_learning_evidence(rule["rule_uuid"])), before)
                self.assertEqual(
                    store.get_learning_application(
                        res["applications"][0])["outcome"], "pending")

    def test_detection_approves_nothing_even_when_it_records(self):
        """Invariant L1 under the one mechanism that could plausibly erode it:
        automatic grading. It writes evidence and outcomes, never approval."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = self._rule(store, state="confirmed")
                store.record_learning_applications(self.TRIGGER, session_id="S1")
                cand = self._repeat(store)
                store.detect_repeated_correction(cand["candidate_uuid"],
                                                  record=True)
                self.assertEqual(
                    store.get_learning_candidate(
                        cand["candidate_uuid"])["status"], "pending")
                self.assertEqual(
                    store.get_learning_rule(rule["rule_uuid"])["state"],
                    "confirmed")

    def test_recording_a_repeat_twice_writes_one_evidence_row(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = self._rule(store, state="confirmed")
                store.record_learning_applications(self.TRIGGER, session_id="S1")
                cand = self._repeat(store)
                store.detect_repeated_correction(cand["candidate_uuid"],
                                                  record=True)
                after_one = len(store.list_learning_evidence(rule["rule_uuid"]))
                store.detect_repeated_correction(cand["candidate_uuid"],
                                                  record=True)
                self.assertEqual(
                    len(store.list_learning_evidence(rule["rule_uuid"])),
                    after_one)

    # -- the reports -------------------------------------------------------

    def test_a_rule_never_repeats_itself_through_its_own_approval(self):
        """Found by driving the CLI, not by a test. The founder_approval
        evidence row carries the candidate the rule was BORN from, so counting
        every candidate-linked evidence row reported every rule as repeating
        itself the moment it was approved."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store, state="confirmed")
                out = store.learning_loop_failures()
                self.assertEqual(out["repeated_corrections"], [])

    def test_loop_failures_counts_only_rows_that_exist(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store, state="confirmed")
                res = store.record_learning_applications(self.TRIGGER,
                                                          session_id="S1")
                store.set_application_disposition(res["applications"][0],
                                                  "ignored", reason="in a hurry")
                out = store.learning_loop_failures()
                self.assertEqual(out["counts"]["compliance_failure"], 1)
                self.assertEqual(out["counts"]["bad_rule"], 0)
                self.assertEqual(len(out["compliance_failures"]), 1)
                for name in bs._learning().FAILURE_CLASSES:
                    self.assertIn(name, out["counts"])

    def test_an_empty_window_says_not_measured_rather_than_all_clear(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store, state="confirmed")
                store.record_learning_applications(self.TRIGGER, session_id="S1")
                # A window that ended before the row was written. 0.00001 days
                # is under a second and the timestamps are second-precision, so
                # the cutoff has to be far enough back to be unambiguous and
                # still exclude a row written now.
                out = store.learning_loop_failures(window_days=-1)
                self.assertEqual(out["applications_in_window"], 0)
                self.assertTrue(any("not measured" in n for n in out["notes"]))

    def test_an_outcome_that_grades_no_rule_is_listed_separately(self):
        """Unattributed outcomes are real and are reported, never folded into
        a rule's record where they would look like evidence about it."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store, state="confirmed")
                rec = self._record(store)
                store.record_outcome_event("escaped_defect",
                                           rec.lifecycle_uuid)
                out = store.learning_loop_failures()
                self.assertEqual(len(out["unattributed_outcomes"]), 1)
                self.assertEqual(out["outcomes_linked_to_rules"], [])

    def test_an_escaped_defect_is_not_the_founder_repeating_himself(self):
        """The weekly review's line reads 'repeated settled corrections: the
        same instruction given twice'. An escaped defect is an outcome nobody
        restated, so counting it there told the founder he had said a thing
        three times when he had said it once."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store, state="settled")
                rec = self._record(store)
                res = store.record_learning_applications(
                    self.TRIGGER, session_id="S1",
                    record_prefix=rec.lifecycle_uuid)
                store.set_application_disposition(
                    res["applications"][0], "ignored", reason="in a hurry")
                store.record_outcome_event(
                    "escaped_defect", rec.lifecycle_uuid, session_id="S1",
                    defect_class="regression", summary="found after sign-off")
                out = store.learning_loop_failures()
                self.assertEqual(out["repeated_settled_corrections"], [])
                self.assertEqual(len(out["outcome_gradings"]), 1)
                self.assertEqual(out["outcome_gradings"][0]["source_type"],
                                 "escaped_defect")
                self.assertEqual(len(out["outcomes_linked_to_rules"]), 1)

    def test_a_real_repeated_correction_still_counts(self):
        """The guard above must not silence the line it is protecting."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = self._rule(store, state="settled")
                cand = self._repeat(store)
                store.detect_repeated_correction(cand["candidate_uuid"],
                                                  record=True)
                out = store.learning_loop_failures()
                self.assertEqual(
                    [r["rule_uuid"] for r in out["repeated_settled_corrections"]],
                    [rule["rule_uuid"]])
                self.assertEqual(out["outcome_gradings"], [])

    def test_a_rule_is_never_promoted_on_evidence_it_was_never_followed(self):
        """The promotion gate's own words: 'it needs at least one independent
        supporting event. Approval is the founder's intent, not evidence the
        rule worked.' A compliance failure used to be written as SUPPORT, so
        the chain retrieve, skip, rework promoted a rule to confirmed and then
        settled on proof it had never once been obeyed."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = self._rule(store)
                rec = self._record(store)
                res = store.record_learning_applications(
                    self.TRIGGER, session_id="S1",
                    record_prefix=rec.lifecycle_uuid)
                store.set_application_disposition(
                    res["applications"][0], "ignored", reason="in a hurry")
                ev = store.record_outcome_event(
                    "rework", rec.lifecycle_uuid, session_id="S1",
                    summary="the update had to be rewritten")
                # The refusal is asserted FIRST on purpose. Assert the polarity
                # first and reinjecting the defect fails here instead of on
                # the promotion, which would leave the guard that actually
                # matters unproven.
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.change_learning_rule_state(rule["rule_uuid"],
                                                     "confirmed")
                self.assertEqual(ctx.exception.reason, "no-supporting-evidence")
                link = ev["linked_applications"][0]
                self.assertEqual(link["classification"], "compliance_failure")
                self.assertEqual(link["polarity"], "neutral")

    def test_a_rule_that_was_followed_can_still_be_promoted(self):
        """The other direction of the same guard: the honest path to
        'confirmed' must stay open, or the gate would just be a wall."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = self._rule(store)
                res = store.record_learning_applications(self.TRIGGER,
                                                          session_id="S1")
                store.set_application_disposition(
                    res["applications"][0], "followed",
                    verification_ref="test:exec_update_shape")
                moved = store.change_learning_rule_state(rule["rule_uuid"],
                                                          "confirmed")
                self.assertEqual(moved["state"], "confirmed")

    def test_a_rule_nothing_ever_retrieved_is_named(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = self._rule(store)
                out = store.learning_loop_failures()
                self.assertEqual([r["rule_uuid"] for r in
                                  out["rules_never_retrieved"]],
                                 [rule["rule_uuid"]])

    def test_a_rule_always_marked_irrelevant_is_named(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = self._rule(store)
                res = store.record_learning_applications(self.TRIGGER,
                                                          session_id="S1")
                store.set_application_disposition(res["applications"][0],
                                                  "not_relevant")
                out = store.learning_loop_failures()
                self.assertEqual([r["rule_uuid"] for r in
                                  out["rules_always_not_relevant"]],
                                 [rule["rule_uuid"]])

    def test_rule_outcomes_refuses_a_rate_over_no_applications(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = self._rule(store)
                out = store.learning_rule_outcomes(rule["rule_uuid"])
                self.assertEqual(out["applications"], 0)
                self.assertEqual(out["by_disposition"], {})
                self.assertTrue(any("not measured" in n for n in out["notes"]))

    def test_rule_outcomes_reports_per_version_counts(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = self._rule(store)
                store.record_learning_applications(self.TRIGGER,
                                                    session_id="S1")
                _edited(store, rule["rule_uuid"], 1,
                        action="lead with the number",
                        change_reason="tightened")
                store.record_learning_applications("writing an executive update",
                                                    session_id="S2")
                out = store.learning_rule_outcomes(rule["rule_uuid"])
                self.assertEqual(out["applications"], 2)
                self.assertEqual(out["by_rule_version"], {"1": 1, "2": 1})

    # -- the pure classifier ----------------------------------------------

    def test_followed_outranks_every_other_class(self):
        """The ordering IS the product claim. Wrong order and the founder
        edits rule text that was already correct while the retrieval bug that
        actually caused the failure stays untouched."""
        L = bs._learning()
        rows = [{"disposition": "ignored", "shown_to_model": 1},
                {"disposition": "not_relevant", "shown_to_model": 1},
                {"disposition": "followed", "shown_to_model": 1}]
        self.assertEqual(L.classify_repeated_correction(rows, True)[0], "bad_rule")
        self.assertEqual(
            L.classify_repeated_correction(rows[:2], True)[0],
            "compliance_failure")
        self.assertEqual(
            L.classify_repeated_correction(rows[1:2], True)[0], "scope_error")
        self.assertEqual(L.classify_repeated_correction([], True)[0],
                         "retrieval_miss")
        self.assertEqual(L.classify_repeated_correction([], False)[0],
                         "not_decidable")

    def test_ignored_but_never_shown_is_not_a_compliance_failure(self):
        L = bs._learning()
        rows = [{"disposition": "ignored", "shown_to_model": 0}]
        self.assertEqual(L.classify_repeated_correction(rows, True)[0],
                         "not_decidable")

    def test_every_class_has_a_polarity_and_no_class_is_missing_one(self):
        L = bs._learning()
        self.assertEqual(sorted(L.REPEATED_CORRECTION_POLARITY),
                         sorted(L.FAILURE_CLASSES))
        for cls, pol in L.REPEATED_CORRECTION_POLARITY.items():
            self.assertIn(pol, ("support", "contradict", "neutral"), cls)

    def test_a_window_is_read_exactly_or_refused(self):
        L = bs._learning()
        self.assertEqual(L.parse_window_days("30d")[0], 30.0)
        self.assertEqual(L.parse_window_days("2w")[0], 14.0)
        self.assertEqual(L.parse_window_days("7")[0], 7.0)
        self.assertIsNone(L.parse_window_days("last month")[0])
        self.assertIsNone(L.parse_window_days("-3d")[0])
        self.assertIsNone(L.parse_window_days("")[0])


class TestPostAuditLoop3ApprovalReceipts(unittest.TestCase):
    """Post-audit LOOP 3, founder decision 2026-07-29: Model A.

    The audit finding these tests close, reproduced against HEAD d88abcc in a
    throwaway store on 2026-07-29: `bm_learn.py approve <id> --gate` with no
    --ref and no receipt exited 0 and created gate rule 61de7eb9, because the
    CLI synthesized the founder reference itself while the help text claimed
    approval refuses without one. Every test below is written so that removing
    the receipt gate makes it fail, not so that it documents what the code
    happens to do."""

    def _cap(self, store, **kw):
        kw.setdefault("source_type", "manual")
        kw.setdefault("trigger", "writing an executive update")
        kw.setdefault("action", "state customer impact before technical detail")
        kw.setdefault("because", "leaders need the business state first")
        kw.setdefault("scope_type", "global")
        kw.setdefault("scope_key", "")
        return store.capture_learning_candidate(**kw)

    def _mint(self, store, cand, **kw):
        return store.mint_approval_receipt(
            cand["candidate_uuid"],
            founder_response=kw.pop("founder_response", "yes, do that"), **kw)

    def _repending(self, store, cand):
        """Force a candidate back to pending WITHOUT going through the API.

        Needed only so the reuse and expiry tests can reach the receipt checks
        at all: approving flips the candidate to approved, and the not-pending
        refusal would otherwise fire first and the receipt check would never
        run. Reaching around the API is the point here, not a shortcut."""
        store.conn.execute("BEGIN IMMEDIATE")
        store.conn.execute(
            "UPDATE learning_candidates SET status='pending' WHERE candidate_uuid=?",
            (cand["candidate_uuid"],))
        store.conn.execute("COMMIT")

    # -- the gate itself ---------------------------------------------------

    def test_approval_without_a_receipt_refuses_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                c = self._cap(store)
                for bad in ("", "   ", None):
                    with self.assertRaises(bs.OwnershipRefused) as ctx:
                        store.approve_learning_candidate(
                            c["candidate_uuid"], founder_ref="founder in chat",
                            receipt=bad)
                    self.assertEqual(ctx.exception.reason, "no-approval-receipt")
                self.assertEqual(store.list_learning_rules(), [])
                self.assertEqual(
                    store.get_learning_candidate(c["candidate_uuid"])["status"],
                    "pending")

    def test_the_receipt_argument_has_no_usable_default(self):
        """The default exists so the refusal is a named OwnershipRefused rather
        than a TypeError, and this is what stops it becoming a bypass."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                c = self._cap(store)
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.approve_learning_candidate(c["candidate_uuid"],
                                                     founder_ref="founder")
                self.assertEqual(ctx.exception.reason, "no-approval-receipt")

    def test_a_forged_token_refuses_and_says_nothing_useful_to_a_guesser(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                c = self._cap(store)
                real = self._mint(store, c)
                # DETERMINISTIC, not probabilistic (LOOP 2, 2026-07-30): the
                # old "real['token'][:-1] + '0'" only forged a different
                # token when the real last character was not itself '0', a
                # roughly 1-in-16 flake this loop's own forged-token test was
                # named for.
                last = real["token"][-1]
                forged_token = real["token"][:-1] + ("1" if last == "0" else "0")
                for forged in ("deadbeef", real["receipt_uuid"], forged_token):
                    with self.assertRaises(bs.OwnershipRefused) as ctx:
                        store.approve_learning_candidate(
                            c["candidate_uuid"], founder_ref="f", receipt=forged)
                    self.assertEqual(ctx.exception.reason, "bad-approval-receipt")
                    self.assertNotIn(real["token"], str(ctx.exception))
                self.assertEqual(store.list_learning_rules(), [])

    def test_minting_refuses_without_an_actual_founder_answer(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                c = self._cap(store)
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.mint_approval_receipt(c["candidate_uuid"],
                                                founder_response="   ")
                self.assertEqual(ctx.exception.reason, "no-founder-response")

    # -- overrides are part of the question (FIX ROUND P3) ------------------

    def test_a_clean_receipt_cannot_be_spent_with_a_conflict_override(self):
        """Reproduced 2026-07-29: atomicity_override and conflict_override were
        approval-only parameters, absent from the fingerprint, and minting never
        mentioned a conflict. So a receipt minted for a question that said
        nothing about contradicting an approved gate rule was spent with
        --override-conflict and forced the contradicting rule in anyway."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                a = self._cap(store, trigger="pushing to main",
                              action="never force push to main")
                _approved(store, a["candidate_uuid"], founder_ref="yes",
                          severity="gate", scope_type="project",
                          scope_key="proj")
                b = self._cap(store, trigger="pushing to main",
                              action="always force push to main")
                # The question cannot even be ASKED without naming the conflict.
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.mint_approval_receipt(
                        b["candidate_uuid"], founder_response="yes",
                        trigger="pushing to main",
                        action="always force push to main",
                        scope_type="project", scope_key="proj")
                self.assertEqual(ctx.exception.reason, "unresolved-contradiction")
                # And a receipt minted for a DIFFERENT (clean) question cannot
                # be carried over to the override.
                clean = self._cap(store, trigger="writing a summary",
                                  action="lead with the number")
                rec = store.mint_approval_receipt(
                    clean["candidate_uuid"], founder_response="yes",
                    trigger="writing a summary", action="lead with the number")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.approve_learning_candidate(
                        clean["candidate_uuid"], founder_ref="f",
                        receipt=rec["token"], trigger="writing a summary",
                        action="lead with the number",
                        conflict_override="I decided it is fine")
                self.assertEqual(ctx.exception.reason, "receipt-stale-candidate")

    def test_an_override_receipt_carries_the_warning_it_was_minted_over(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                a = self._cap(store, trigger="pushing to main",
                              action="never force push to main")
                _approved(store, a["candidate_uuid"], founder_ref="yes",
                          severity="gate", scope_type="project",
                          scope_key="proj")
                b = self._cap(store, trigger="pushing to main",
                              action="always force push to main")
                rec = store.mint_approval_receipt(
                    b["candidate_uuid"], founder_response="yes I mean it",
                    trigger="pushing to main",
                    action="always force push to main",
                    scope_type="project", scope_key="proj",
                    conflict_override="he decided it is fine")
                self.assertTrue(rec["override_conflict"])
                self.assertTrue(rec["contradicts"])
                rule = store.approve_learning_candidate(
                    b["candidate_uuid"], founder_ref="f", receipt=rec["token"],
                    trigger="pushing to main",
                    action="always force push to main",
                    scope_type="project", scope_key="proj",
                    conflict_override="he decided it is fine")
                self.assertEqual(rule["action_text"], "always force push to main")

    # -- one candidate, one use, short lived --------------------------------

    def test_a_receipt_for_another_candidate_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                a = self._cap(store)
                b = self._cap(store, trigger="pushing to github",
                              action="use the desktop app")
                rec = self._mint(store, a)
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.approve_learning_candidate(
                        b["candidate_uuid"], founder_ref="f", receipt=rec["token"])
                self.assertEqual(ctx.exception.reason, "receipt-wrong-candidate")
                self.assertEqual(store.list_learning_rules(), [])

    def test_a_spent_receipt_refuses_the_second_time(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                c = self._cap(store)
                rec = self._mint(store, c)
                store.approve_learning_candidate(
                    c["candidate_uuid"], founder_ref="f", receipt=rec["token"])
                self._repending(store, c)
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.approve_learning_candidate(
                        c["candidate_uuid"], founder_ref="f", receipt=rec["token"])
                self.assertEqual(ctx.exception.reason, "receipt-already-used")
                self.assertEqual(len(store.list_learning_rules()), 1,
                                 "a replayed receipt must not create a second rule")

    def test_an_expired_receipt_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                c = self._cap(store)
                rec = self._mint(store, c)
                store.conn.execute("BEGIN IMMEDIATE")
                store.conn.execute(
                    "UPDATE learning_approval_receipts SET expires_at='2000-01-01T00:00:00Z' "
                    "WHERE receipt_uuid=?", (rec["receipt_uuid"],))
                store.conn.execute("COMMIT")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.approve_learning_candidate(
                        c["candidate_uuid"], founder_ref="f", receipt=rec["token"])
                self.assertEqual(ctx.exception.reason, "receipt-expired")
                self.assertEqual(store.list_learning_rules(), [])

    def test_the_ttl_is_clamped_and_never_extendable_by_a_caller(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                c = self._cap(store)
                for asked in (10 ** 6, "not a number", None, 0, -5):
                    rec = store.mint_approval_receipt(
                        c["candidate_uuid"], founder_response="yes",
                        ttl_seconds=asked)
                    self.assertLessEqual(rec["ttl_seconds"],
                                         bs.APPROVAL_RECEIPT_TTL_SECONDS)
                    self.assertGreaterEqual(rec["ttl_seconds"], 1)

    # -- bound to what the founder was shown -------------------------------

    def test_editing_the_candidate_after_the_question_invalidates_the_receipt(self):
        """The founder answered about the text he was shown. Change the text
        and that answer is evidence about something that no longer exists."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                c = self._cap(store)
                rec = self._mint(store, c)
                store.conn.execute("BEGIN IMMEDIATE")
                store.conn.execute(
                    "UPDATE learning_candidates SET proposed_action=? "
                    "WHERE candidate_uuid=?",
                    ("push straight to main without review", c["candidate_uuid"]))
                store.conn.execute("COMMIT")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.approve_learning_candidate(
                        c["candidate_uuid"], founder_ref="f", receipt=rec["token"])
                self.assertEqual(ctx.exception.reason, "receipt-stale-candidate")
                self.assertEqual(store.list_learning_rules(), [])

    def test_changing_the_rule_text_at_approval_invalidates_the_receipt(self):
        """The nastier half: the candidate is untouched, but approve can
        override every field of the rule on its way in."""
        cases = (
            {"trigger": "any commit at all"},
            {"action": "push straight to main"},
            {"because": "a different reason entirely"},
            {"scope_type": "project"},
            {"scope_key": "SomeOtherProject"},
            {"domain": "finance"},
            {"rule_type": "constraint"},
            {"severity": "gate"},
        )
        for override in cases:
            with tempfile.TemporaryDirectory() as d:
                with bs.Store(d) as store:
                    c = self._cap(store)
                    rec = self._mint(store, c)
                    with self.assertRaises(bs.OwnershipRefused) as ctx:
                        store.approve_learning_candidate(
                            c["candidate_uuid"], founder_ref="f",
                            receipt=rec["token"], **override)
                    self.assertEqual(ctx.exception.reason, "receipt-stale-candidate",
                                     "overriding %r escaped the fingerprint"
                                     % (sorted(override),))
                    self.assertEqual(store.list_learning_rules(), [])

    def test_a_receipt_minted_for_the_same_shape_approves(self):
        """The other side of the fingerprint: it must not refuse the honest
        case, or the whole mechanism is just a broken door."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                c = self._cap(store)
                rec = self._mint(store, c, severity="gate", domain="delivery")
                rule = store.approve_learning_candidate(
                    c["candidate_uuid"], founder_ref="founder said yes in chat",
                    receipt=rec["token"], severity="gate", domain="delivery")
                self.assertEqual(rule["state"], "approved")
                self.assertEqual(rule["severity"], "gate")

    # -- atomicity ---------------------------------------------------------

    def test_consumption_and_rule_creation_are_one_transaction(self):
        """CALIBRATION for the property the whole design rests on. If the rule
        insert fails after the receipt has been claimed, the claim must be
        rolled back too, or one founder answer would be destroyed without
        producing the rule it paid for."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                c = self._cap(store)
                rec = self._mint(store, c)
                real_exec = bs._exec

                def _boom(st, sql, *a, **kw):
                    if sql.lstrip().startswith("INSERT INTO learning_rules"):
                        raise RuntimeError("simulated failure after consumption")
                    return real_exec(st, sql, *a, **kw)

                bs._exec = _boom
                try:
                    with self.assertRaises(RuntimeError):
                        store.approve_learning_candidate(
                            c["candidate_uuid"], founder_ref="f",
                            receipt=rec["token"])
                finally:
                    bs._exec = real_exec
                self.assertEqual(store.list_learning_rules(), [])
                self.assertIsNone(
                    store.get_approval_receipt(rec["receipt_uuid"])["consumed_at"],
                    "the receipt was spent for a rule that does not exist")
                self.assertEqual(
                    store.get_learning_candidate(c["candidate_uuid"])["status"],
                    "pending")
                # And the unspent receipt still works afterwards.
                store.approve_learning_candidate(
                    c["candidate_uuid"], founder_ref="f", receipt=rec["token"])
                self.assertEqual(len(store.list_learning_rules()), 1)

    def test_a_receipt_spent_between_the_check_and_the_write_loses(self):
        """The race the conditional UPDATE exists for, and it was NOT covered
        until a calibration pass removed the rowcount guard on 2026-07-29 and
        every test still passed: the pre-transaction check catches an ordinary
        replay, so nothing was exercising the claim itself.

        The competing spend is injected rather than threaded, because a real
        thread race here is timing-dependent and would either flake or, worse,
        pass by never hitting the window. What is simulated is only the timing;
        the statement that has to win is the real one."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                c = self._cap(store)
                rec = self._mint(store, c)
                real_exec = bs._exec
                state = {"raced": False}

                def _race(st, sql, *a, **kw):
                    if (not state["raced"]
                            and sql.lstrip().startswith(
                                "UPDATE learning_approval_receipts SET consumed_at")):
                        state["raced"] = True
                        real_exec(st,
                                  "UPDATE learning_approval_receipts SET "
                                  "consumed_at='2026-07-29T00:00:00Z', "
                                  "consumed_rule_uuid='someone-else' WHERE receipt_uuid=?",
                                  (rec["receipt_uuid"],))
                    return real_exec(st, sql, *a, **kw)

                bs._exec = _race
                try:
                    with self.assertRaises(bs.OwnershipRefused) as ctx:
                        store.approve_learning_candidate(
                            c["candidate_uuid"], founder_ref="f",
                            receipt=rec["token"])
                finally:
                    bs._exec = real_exec
                self.assertTrue(state["raced"], "the race was never injected")
                self.assertEqual(ctx.exception.reason, "receipt-already-used")
                self.assertEqual(store.list_learning_rules(), [],
                                 "the loser of the race still created a rule")
                self.assertEqual(
                    store.get_learning_candidate(c["candidate_uuid"])["status"],
                    "pending")

    def test_consumption_records_the_rule_it_paid_for(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                c = self._cap(store)
                rec = self._mint(store, c)
                rule = store.approve_learning_candidate(
                    c["candidate_uuid"], founder_ref="f", receipt=rec["token"])
                spent = store.get_approval_receipt(rec["receipt_uuid"])
                self.assertIsNotNone(spent["consumed_at"])
                self.assertEqual(spent["consumed_rule_uuid"], rule["rule_uuid"])
                evidence = [e["source_ref"] for e
                            in store.list_learning_evidence(rule["rule_uuid"])]
                self.assertTrue(
                    any(rec["receipt_uuid"][:8] in (e or "") for e in evidence),
                    "provenance must name the receipt that opened the door")

    # -- the token is a secret ---------------------------------------------

    def test_the_token_is_never_stored_returned_again_or_dumped(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                c = self._cap(store)
                rec = self._mint(store, c, founder_response="yes, always do that")
                token = rec["token"]
                self.assertNotIn("nonce_hash", rec)
                self.assertNotIn("nonce_hash", store.get_approval_receipt(
                    rec["receipt_uuid"]))
                for blob in (json.dumps(store.dump(), default=str),
                             json.dumps(store.dump(raw=True), default=str)):
                    self.assertNotIn(token, blob,
                                     "the token reached a display surface")
                self.assertNotIn(
                    "yes, always do that",
                    json.dumps(store.dump(raw=True), default=str),
                    "the founder's literal answer is hashed, never stored")
            path = os.path.join(d, bs.STORE_DIRNAME, bs.STORE_FILENAME)
            with io.open(path, "rb") as f:
                self.assertNotIn(token.encode("ascii"), f.read(),
                                 "the token is in the database file")

    # -- no other way in ---------------------------------------------------

    def test_only_the_receipt_gated_path_can_insert_a_rule(self):
        """The reinjection this loop has to survive is not a clever token
        forgery, it is a second door: any other function in bm_store.py that
        inserts into learning_rules would be an approval path with no receipt
        check at all. Structural, because a behavioural test can only cover the
        doors someone remembered to look for."""
        with io.open(os.path.join(HERE, "bm_store.py"), encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename="bm_store.py")
        offenders = []

        class _V(ast.NodeVisitor):
            def __init__(self):
                self.stack = ["<module>"]

            def visit_FunctionDef(self, node):
                self.stack.append(node.name)
                self.generic_visit(node)
                self.stack.pop()

            def visit_Constant(self, node):
                if (isinstance(node.value, str)
                        and "INSERT INTO learning_rules " in node.value
                        and self.stack[-1] != "approve_learning_candidate"):
                    offenders.append((node.lineno, self.stack[-1]))
                self.generic_visit(node)

        _V().visit(tree)
        self.assertEqual(offenders, [],
                         "a rule-creating statement outside the receipt-gated "
                         "approval path: %s" % offenders)

    def test_the_cli_module_cannot_reach_approval_without_a_receipt(self):
        """bm_learn.py is the only caller, and its approve command must pass a
        receipt through rather than synthesizing one, which is exactly what it
        used to do with founder_ref."""
        with io.open(os.path.join(HERE, "bm_learn.py"), encoding="utf-8") as f:
            src = f.read()
        tree = ast.parse(src, filename="bm_learn.py")
        found = []
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "approve_learning_candidate"):
                found.append(sorted(k.arg for k in node.keywords))
        self.assertEqual(len(found), 1,
                         "expected exactly one approval call site, got %d" % len(found))
        self.assertIn("receipt", found[0],
                      "the CLI approval call site stopped passing a receipt")
        self.assertNotIn(
            "founder_ref=ref or", src,
            "the CLI must not manufacture approval evidence of any kind")


class TestPostAuditLoop3Schema3Migration(unittest.TestCase):
    """Schema 2 to 3 (approval receipts). Same discipline as
    TestSchema2Migration: the fixture is a REAL store reverted to schema 2, not
    hand-written DDL, so it cannot drift from the schema anyone actually has."""

    def _schema2_store(self, d):
        with bs.Store(d) as store:
            store.claim("alpha", "persistent", "keep me", ["src/a.py"])
            c = store.capture_learning_candidate(
                "manual", trigger="writing an executive update",
                action="state customer impact first",
                because="leaders need the business state first",
                scope_type="global", scope_key="")
            _approved(store, c["candidate_uuid"], founder_ref="approved before receipts existed")
        path = os.path.join(d, bs.STORE_DIRNAME, bs.STORE_FILENAME)
        conn = sqlite3.connect(path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            for t in bs._TABLES_RECEIPTS:
                conn.execute("DROP TABLE IF EXISTS %s" % t)
            conn.execute("UPDATE meta SET value='2' WHERE key='schema_version'")
            conn.execute("COMMIT")
        finally:
            conn.close()
        return path

    def _snapshot(self, path):
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        try:
            out = {}
            for t in bs._TABLES_V2:
                rows = [dict(r) for r in conn.execute("SELECT * FROM %s" % t)]
                if t == "meta":
                    rows = [r for r in rows if r.get("key") != "schema_version"]
                out[t] = json.dumps(rows, sort_keys=True, default=str)
            return out
        finally:
            conn.close()

    def _tables(self, path):
        conn = sqlite3.connect(path)
        try:
            return {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            conn.close()

    def test_a_schema2_store_migrates_instead_of_being_quarantined(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._schema2_store(d)
            with bs.Store(d) as store:
                self.assertEqual(
                    store.conn.execute(
                        "SELECT value FROM meta WHERE key='schema_version'"
                    ).fetchone()["value"], str(bs.SCHEMA_VERSION))
            self.assertTrue(set(bs._TABLES_RECEIPTS) <= self._tables(path))
            self.assertEqual(
                glob.glob(os.path.join(d, bs.STORE_DIRNAME, "*quarantine*")), [],
                "a healthy schema-2 store must MIGRATE, never be quarantined")

    def test_migration_preserves_every_schema2_row(self):
        """Including rules approved before receipts existed. Rewriting them to
        look receipt-backed would be the dishonest half of this change."""
        with tempfile.TemporaryDirectory() as d:
            path = self._schema2_store(d)
            before = self._snapshot(path)
            with bs.Store(d):
                pass
            self.assertEqual(before, self._snapshot(path))

    def test_migration_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._schema2_store(d)
            with bs.Store(d):
                pass
            first = self._snapshot(path)
            with bs.Store(d):
                pass
            self.assertEqual(first, self._snapshot(path))

    def test_calibrated_interrupted_migration_rolls_back_completely(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._schema2_store(d)
            original = bs._MIGRATIONS[2]

            def _fail_half_way(conn):
                conn.execute(bs._RECEIPT_DDL_STATEMENTS[0])
                raise RuntimeError("simulated interruption mid-migration")

            bs._MIGRATIONS[2] = _fail_half_way
            try:
                with self.assertRaises(RuntimeError):
                    bs.Store(d)
            finally:
                bs._MIGRATIONS[2] = original
            conn = sqlite3.connect(path)
            try:
                v = conn.execute(
                    "SELECT value FROM meta WHERE key='schema_version'").fetchone()[0]
            finally:
                conn.close()
            self.assertEqual(v, "2", "an interrupted migration must not move the version")
            for t in bs._TABLES_RECEIPTS:
                self.assertNotIn(t, self._tables(path))
            with bs.Store(d):
                pass
            self.assertTrue(set(bs._TABLES_RECEIPTS) <= self._tables(path))

    def test_receipt_ddl_split_matches_the_table_and_index_lists(self):
        self.assertEqual(len(bs._RECEIPT_DDL_STATEMENTS), len(bs._TABLES_RECEIPTS))
        self.assertEqual(len(bs._RECEIPT_INDEX_STATEMENTS), 1)


_PAST = "2000-01-01T00:00:00Z"
_FUTURE = "2099-01-01T00:00:00Z"


class TestPostAuditLoopP6RetrievalRuns(unittest.TestCase):
    """LOOP P6: a retrieval miss must have a denominator that was RECORDED.

    The gap these tests close was reproduced on the real CLI first: one global
    gate and one project-scoped rule in scope, a retrieval at limit 0, and
    classify reported no misses at all, because the retrieval context was never
    stored and was rebuilt from the scope_match of the rows that DID land."""

    TASK = "writing an executive update"

    def _rule(self, store, action, trigger=None, severity="soft",
              scope_type="global", scope_key=""):
        c = store.capture_learning_candidate(
            "manual", trigger=trigger or self.TASK, action=action,
            because="the founder said so", scope_type=scope_type,
            scope_key=scope_key)
        return _approved(store, c["candidate_uuid"], founder_ref="founder",
                         severity=severity, scope_type=scope_type,
                         scope_key=scope_key)

    def _backdate(self, store, rule, when=_PAST):
        """Make a rule unambiguously OLDER than the retrieval, in both places
        that matter: when the founder approved it, and when its current text
        was written. Backdating only the approval would leave today's wording
        being ranked against a past retrieval, which this build refuses to
        decide, so a fixture that means 'this rule existed, as written' has to
        say both halves."""
        store.conn.execute(
            "UPDATE learning_rules SET founder_approved_at=? WHERE rule_uuid=?",
            (when, rule["rule_uuid"]))
        store.conn.execute(
            "UPDATE learning_rule_versions SET created_at=? WHERE rule_uuid=?",
            (when, rule["rule_uuid"]))
        store.conn.commit()

    def _cut_fixture(self, store):
        """A gate that is always returned, and a project rule the limit cuts.

        The project rule is the one that used to be invisible: nothing
        project-scoped was returned, so the rebuilt context had no project key
        and the rule could not even be found to be missing."""
        gate = self._rule(store, "never send it on a friday", severity="gate")
        proj = self._rule(store, "name the client early",
                          scope_type="project", scope_key="Acme")
        res = store.record_learning_applications(
            self.TASK, context={"project": "Acme"}, limit=0, session_id="S1")
        return gate, proj, res

    # -- the run row itself ---------------------------------------------

    def test_the_run_stores_the_context_and_parameters_the_retrieval_used(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store, "lead with the outcome")
                res = store.record_learning_applications(
                    self.TASK, session_id="S1", limit=3,
                    context={"project": "Acme", "artifact": "exec-update",
                             "relationship": "board", "domain": "comms",
                             "tool": "bm_learn"})
                run = store.get_learning_retrieval_run(res["retrieval_uuid"])
                self.assertEqual(run["project_key"], "Acme")
                self.assertEqual(run["artifact_key"], "exec-update")
                self.assertEqual(run["relationship_key"], "board")
                self.assertEqual(run["domain_key"], "comms")
                self.assertEqual(run["tool_key"], "bm_learn")
                self.assertEqual(run["requested_limit"], 3)
                self.assertEqual(run["retrieval_mode"], res["mode"])
                self.assertEqual(run["eligible_count"], res["eligible"])
                self.assertEqual(run["returned_count"], len(res["results"]))
                self.assertEqual(run["session_id"], "S1")

    def test_the_run_stores_a_query_hash_and_never_the_raw_query(self):
        L = bs._learning()
        secret = ("writing an executive update about the ACME-INTERNAL-CODENAME "
                  "launch before the board hears it elsewhere")
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store, "lead with the outcome")
                res = store.record_learning_applications(
                    secret, session_id="S1", task_excerpt="")
                run = store.get_learning_retrieval_run(res["retrieval_uuid"])
                self.assertEqual(run["query_hash"], L.content_hash(secret))
                # The prompt is not stored. What is stored is the term set the
                # ranker reads: sorted, deduplicated, order destroyed, so the
                # sentence the founder typed cannot be read back off the row.
                self.assertEqual(run["task_excerpt"], L.query_terms(secret))
                self.assertNotIn(secret, run["task_excerpt"])
                self.assertNotIn("executive update about", run["task_excerpt"],
                                 "word order must not survive into the store")
                blob = json.dumps(store.dump(), sort_keys=True)
                self.assertNotIn("ACME-INTERNAL-CODENAME", blob,
                                 "no dump may reproduce the founder's task text")

    def test_the_stored_terms_rank_a_past_retrieval_the_way_the_query_did(self):
        """The term set is only allowed to replace the prompt because the
        ranker reads nothing else off it. This is that claim, checked."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store, "lead with the outcome")
                self._rule(store, "attach the revenue number",
                           trigger=self.TASK + " revenue")
                query = self.TASK + " with revenue, revenue and more revenue!"
                by_query = store.retrieve_learning_rules(query, limit=5)
                by_terms = store.retrieve_learning_rules(
                    bs._learning().query_terms(query), limit=5)
                self.assertEqual([r["rule_uuid"] for r in by_query["results"]],
                                 [r["rule_uuid"] for r in by_terms["results"]])
                self.assertEqual(by_query["eligible"], by_terms["eligible"])

    def test_a_task_whose_terms_were_too_many_to_keep_is_not_decidable(self):
        L = bs._learning()
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store, "lead with the outcome")
                huge = self.TASK + " " + " ".join(
                    "term%d" % i for i in range(L.MAX_QUERY_TERMS + 1))
                res = store.record_learning_applications(huge, session_id="S1",
                                                          task_excerpt="")
                run = store.get_learning_retrieval_run(res["retrieval_uuid"])
                self.assertEqual(run["task_excerpt"], "",
                                 "a truncated term set would re-rank as a "
                                 "different task, so none is kept")
                out = store.classify_learning_applications()
                self.assertEqual(out["retrieval_misses"], [])
                self.assertEqual(out["not_decidable_tasks"][0]["evidence"],
                                 "no_task_text")

    def test_a_scope_key_longer_than_a_display_line_is_stored_whole(self):
        """FIX ROUND P6, reproduced on the real CLI. validate_scope puts no
        length cap on a scope key; storing it through safe_display did, so a
        long project key came back with an ellipsis, stopped matching the rule
        it named, and the miss vanished with no not_decidable either."""
        key = "Acme" + "x" * 250
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                proj = self._rule(store, "name the client early",
                                  scope_type="project", scope_key=key)
                res = store.record_learning_applications(
                    self.TASK, context={"project": key}, limit=0,
                    session_id="S1")
                run = store.get_learning_retrieval_run(res["retrieval_uuid"])
                self.assertEqual(run["project_key"], key)
                out = store.classify_learning_applications()
                self.assertEqual([m["rule_uuid"] for m in out["retrieval_misses"]],
                                 [proj["rule_uuid"]])

    def test_calibration_a_display_capped_scope_key_loses_the_miss(self):
        key = "Acme" + "x" * 250
        L = bs._learning()
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                proj = self._rule(store, "name the client early",
                                  scope_type="project", scope_key=key)
                with mock.patch.object(L, "storage_key",
                                       lambda text: L.safe_display(text, 200)):
                    store.record_learning_applications(
                        self.TASK, context={"project": key}, limit=0,
                        session_id="S1")
                    blind = store.classify_learning_applications()
                self.assertEqual(blind["retrieval_misses"], [],
                                 "with the key truncated the rule is not even "
                                 "eligible, so the miss is invisible")
                # Restored: the same retrieval, storing the key whole, finds it.
                store.record_learning_applications(
                    self.TASK, context={"project": key}, limit=0,
                    session_id="S2")
                self.assertEqual(
                    [m["rule_uuid"]
                     for m in store.classify_learning_applications(
                         session_id="S2")["retrieval_misses"]],
                    [proj["rule_uuid"]],
                    "and it is visible again with the key stored whole")

    def test_a_retrieval_that_records_nothing_new_still_records_the_run(self):
        """A repeat IS a retrieval: it happened, it had a limit and a context.
        Dropping it would leave the ledger unable to say the rules were asked
        for a second time."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store, "lead with the outcome")
                first = store.record_learning_applications(self.TASK,
                                                           session_id="S1")
                second = store.record_learning_applications(self.TASK,
                                                            session_id="S1")
                self.assertEqual(second["recorded"], 0)
                self.assertEqual(second["already_recorded"], 1)
                self.assertNotEqual(first["retrieval_uuid"],
                                    second["retrieval_uuid"])
                self.assertEqual(
                    len(store.list_learning_retrieval_runs(session_id="S1")), 2)

    def test_a_failed_recording_leaves_no_orphan_run(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store, "lead with the outcome")
                res = store.record_learning_applications(
                    self.TASK, session_id="S1", record_prefix="deadbeef")
                self.assertEqual(res["record_error_kind"], "not-found")
                self.assertEqual(res["retrieval_uuid"], "")
                self.assertEqual(store.list_learning_retrieval_runs(), [])
                self.assertTrue(res["results"],
                                "the rules must survive a bookkeeping failure")

    # -- what the stored context now makes visible -----------------------

    def test_a_project_rule_no_project_rule_was_returned_for_is_now_found(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                gate, proj, res = self._cut_fixture(store)
                self.assertEqual(res["recorded"], 1, "only the gate is returned")
                out = store.classify_learning_applications()
                self.assertEqual([m["rule_uuid"] for m in out["retrieval_misses"]],
                                 [proj["rule_uuid"]])
                self.assertNotIn(gate["rule_uuid"],
                                 [m["rule_uuid"] for m in out["retrieval_misses"]])

    def test_calibration_the_old_no_context_design_cannot_see_that_miss(self):
        """Reinjection: put the pre-P6 design back (the retrieval context is
        not stored, so it is whatever the returned rows happened to imply) and
        the test above stops detecting anything. That is the proof the guard
        measures the fix rather than passing on its own."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                gate, proj, res = self._cut_fixture(store)
                with mock.patch.object(bs.Store, "_run_context",
                                       lambda self, run: {}):
                    blind = store.classify_learning_applications()
                self.assertEqual(blind["retrieval_misses"], [],
                                 "with the context thrown away the project rule "
                                 "is not even eligible, so the miss is invisible")
                self.assertEqual(
                    [m["rule_uuid"]
                     for m in store.classify_learning_applications()
                     ["retrieval_misses"]],
                    [proj["rule_uuid"]], "and it is visible again once restored")

    def test_a_limit_caused_miss_is_labelled_separately(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                gate, proj, res = self._cut_fixture(store)
                out = store.classify_learning_applications()
                miss = out["retrieval_misses"][0]
                self.assertEqual(miss["miss_kind"], "limit")
                self.assertEqual(miss["classification"], "retrieval_limit_miss")
                self.assertEqual(miss["requested_limit"], 0)
                self.assertEqual(miss["retrieval_uuid"], res["retrieval_uuid"])
                self.assertEqual(out["counts"]["retrieval_limit_miss"], 1)
                self.assertEqual(out["counts"]["retrieval_miss"], 0)
                self.assertIn("result limit cut it",
                              miss["classification_reason"])

    def _unrecord(self, store, rule):
        """Remove the application row for one rule the retrieval DID return.

        The fixture for a relevance miss, and it is this rather than "add a
        rule afterwards and backdate it" (FIX ROUND P6). A backdated rule makes
        today's corpus larger than the eligible count the run recorded, which
        is exactly the drift the classifier now refuses to grade, so a fixture
        built that way was asserting against invented history. A rule that WAS
        eligible, ranked inside the limit, and has no application row is the
        real shape of the class: the ledger cannot show it reached the model."""
        store.conn.execute("DELETE FROM learning_applications WHERE rule_uuid=?",
                           (rule["rule_uuid"],))
        store.conn.commit()

    def test_a_miss_inside_the_limit_stays_a_relevance_miss(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store, "lead with the outcome")
                missed = self._rule(store, "attach the revenue number",
                                    trigger=self.TASK + " revenue")
                res = store.record_learning_applications(
                    self.TASK + " revenue", session_id="S1", limit=5)
                self.assertEqual(res["recorded"], 2)
                self._unrecord(store, missed)
                out = store.classify_learning_applications()
                self.assertEqual([m["rule_uuid"] for m in out["retrieval_misses"]],
                                 [missed["rule_uuid"]])
                self.assertEqual(out["retrieval_misses"][0]["miss_kind"],
                                 "relevance")
                self.assertEqual(out["counts"]["retrieval_miss"], 1)
                self.assertEqual(out["counts"]["retrieval_limit_miss"], 0)

    def test_a_gate_is_never_written_off_as_a_limit_miss(self):
        """A gate is exempt from the limit by construction, so a gate with no
        application row is the harder finding, never the cheap one."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store, "lead with the outcome")
                gate = self._rule(store, "never send it on a friday",
                                  severity="gate")
                store.record_learning_applications(self.TASK, session_id="S1",
                                                   limit=1)
                self._unrecord(store, gate)
                out = store.classify_learning_applications()
                kinds = dict((m["rule_uuid"], m["miss_kind"])
                             for m in out["retrieval_misses"])
                self.assertEqual(kinds.get(gate["rule_uuid"]), "relevance")

    # -- one run is graded against ITS OWN rows ---------------------------

    def test_a_later_wider_retrieval_does_not_erase_the_first_ones_miss(self):
        """FIX ROUND P6, reproduced on the real CLI: limit was too low, the
        founder raised it and re-ran, and the evidence of the first miss
        disappeared because `seen` was built from every row in the session."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                gate, proj, first = self._cut_fixture(store)
                self.assertEqual(
                    store.classify_learning_applications()
                    ["counts"]["retrieval_limit_miss"], 1)
                store.record_learning_applications(
                    self.TASK, context={"project": "Acme"}, limit=5,
                    session_id="S1")
                out = store.classify_learning_applications()
                self.assertEqual(out["counts"]["retrieval_limit_miss"], 1,
                                 "the graded run still returned nothing")
                miss = out["retrieval_misses"][0]
                self.assertEqual(miss["rule_uuid"], proj["rule_uuid"])
                self.assertEqual(miss["retrieval_uuid"], first["retrieval_uuid"])
                self.assertEqual(miss["retrieval_runs"], 2)
                self.assertTrue(gate["rule_uuid"])

    def test_calibration_session_wide_seen_erases_that_miss(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                gate, proj, first = self._cut_fixture(store)
                store.record_learning_applications(
                    self.TASK, context={"project": "Acme"}, limit=5,
                    session_id="S1")
                real = bs.Store.list_learning_applications

                def blind_rows(self, **kw):
                    # The reinjected defect: every application row in the
                    # session claims to belong to the run being graded, which
                    # is what a session-wide `seen` set amounts to.
                    rows = real(self, **kw)
                    for r in rows:
                        r["retrieval_uuid"] = first["retrieval_uuid"]
                    return rows

                with mock.patch.object(bs.Store, "list_learning_applications",
                                       blind_rows):
                    blind = store.classify_learning_applications()
                self.assertEqual(blind["counts"]["retrieval_limit_miss"], 0,
                                 "rows from the later run hide the first run's "
                                 "miss, which is the defect")
                self.assertEqual(
                    store.classify_learning_applications()
                    ["counts"]["retrieval_limit_miss"], 1,
                    "and the miss is back once rows belong to their own run")

    # -- history that cannot be reconstructed is refused ------------------

    def test_a_corpus_changed_since_the_retrieval_is_not_decidable(self):
        """FIX ROUND P6, reproduced on the real CLI: deprecating an unrelated
        rule flipped a stored retrieval_limit_miss into a retrieval_miss, which
        is the difference between "your page size was too small" and "your
        ranking is wrong", on facts that did not change."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                one = self._rule(store, "cite the source for every number",
                                 trigger=self.TASK + " for investors")
                self._rule(store, "name every assumption")
                store.record_learning_applications(
                    self.TASK + " for investors", session_id="S1", limit=1)
                before = store.classify_learning_applications()
                self.assertEqual(before["counts"]["retrieval_limit_miss"], 1)
                shown = [a["rule_uuid"]
                         for a in store.list_learning_applications(session_id="S1")]
                _state_changed(
                    store, shown[0] if shown else one["rule_uuid"], "deprecated",
                    reason="no longer wanted")
                after = store.classify_learning_applications()
                self.assertEqual(after["retrieval_misses"], [])
                self.assertEqual(after["counts"]["retrieval_limit_miss"], 0)
                self.assertEqual(after["counts"]["retrieval_miss"], 0)
                self.assertIn("corpus_changed_since_retrieval",
                              [u["evidence"] for u in after["not_decidable_tasks"]])

    def test_calibration_grading_todays_corpus_flips_that_class(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store, "cite the source for every number",
                           trigger=self.TASK + " for investors")
                self._rule(store, "name every assumption")
                store.record_learning_applications(
                    self.TASK + " for investors", session_id="S1", limit=1)
                shown = [a["rule_uuid"]
                         for a in store.list_learning_applications(session_id="S1")]
                _state_changed(store, shown[0], "deprecated",
                              reason="no longer wanted")
                with mock.patch.object(
                        bs.Store, "_historical_corpus",
                        staticmethod(lambda res, run: (res["results"], ""))):
                    blind = store.classify_learning_applications()
                self.assertEqual(blind["counts"]["retrieval_miss"], 1,
                                 "today's corpus re-ranks the stored run and "
                                 "reports the opposite cause, which is the defect")
                self.assertEqual(
                    store.classify_learning_applications()["retrieval_misses"], [],
                    "and the refusal is back once the stored count rules")

    def test_the_denominator_printed_is_the_one_the_run_recorded(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                gate, proj, res = self._cut_fixture(store)
                run = store.get_learning_retrieval_run(res["retrieval_uuid"])
                miss = store.classify_learning_applications()["retrieval_misses"][0]
                self.assertIn("of the %d rule(s)" % run["eligible_count"],
                              miss["classification_reason"])
                self.assertEqual(miss["eligible_at_retrieval"],
                                 run["eligible_count"])

    # -- which run is the authority is not a coin flip ---------------------

    def test_two_runs_in_the_same_second_are_ordered_by_insertion(self):
        """created_at has one-second resolution and two retrievals of one task
        inside a second are routine. The tie used to be broken by the random
        retrieval_uuid, so which run's limit and context every miss was judged
        against changed between identical command sequences."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store, "lead with the outcome")
                first = store.record_learning_applications(self.TASK,
                                                            session_id="S1")
                second = store.record_learning_applications(self.TASK,
                                                             session_id="S1")
                store.conn.execute(
                    "UPDATE learning_retrieval_runs SET created_at='%s'" % _PAST)
                store.conn.commit()
                runs = store.list_learning_retrieval_runs(session_id="S1")
                self.assertEqual([r["retrieval_uuid"] for r in runs],
                                 [first["retrieval_uuid"],
                                  second["retrieval_uuid"]])
                self.assertEqual(
                    store._authority_run(list(reversed(runs)))["retrieval_uuid"],
                    first["retrieval_uuid"],
                    "the authority run does not depend on argument order")

    def test_calibration_a_uuid_tie_break_picks_the_wrong_authority(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._rule(store, "lead with the outcome")
                first = store.record_learning_applications(self.TASK,
                                                            session_id="S1")
                second = store.record_learning_applications(self.TASK,
                                                             session_id="S1")
                store.conn.execute(
                    "UPDATE learning_retrieval_runs SET created_at='%s'" % _PAST)
                store.conn.commit()
                runs = store.list_learning_retrieval_runs(session_id="S1")
                by_uuid = sorted(
                    runs, key=lambda r: (r["created_at"], r["retrieval_uuid"]))
                # The reinjected defect is only VISIBLE when the random uuids
                # happen to disagree with insertion order, which is the point:
                # half of all such pairs graded the wrong run.
                if by_uuid[0]["retrieval_uuid"] != first["retrieval_uuid"]:
                    self.assertEqual(by_uuid[0]["retrieval_uuid"],
                                     second["retrieval_uuid"])
                self.assertEqual(store._authority_run(runs)["retrieval_uuid"],
                                 first["retrieval_uuid"])

    # -- what it refuses to decide ---------------------------------------

    def test_a_legacy_application_row_is_reported_as_incomplete_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                gate, proj, res = self._cut_fixture(store)
                # Exactly what a store migrated from schema 3 looks like: the
                # application row survived, the run behind it never existed.
                store.conn.execute("UPDATE learning_applications "
                                   "SET retrieval_uuid=NULL")
                store.conn.execute("DELETE FROM learning_retrieval_runs")
                store.conn.commit()
                out = store.classify_learning_applications()
                self.assertEqual(out["retrieval_misses"], [])
                self.assertEqual(len(out["not_decidable_tasks"]), 1)
                self.assertEqual(out["not_decidable_tasks"][0]["evidence"],
                                 "legacy")
                self.assertIn("incomplete evidence",
                              out["not_decidable_tasks"][0]["reason"])

    def test_a_rule_rewritten_since_the_retrieval_is_not_decidable(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                one = self._rule(store, "lead with the outcome")
                two = self._rule(store, "attach the revenue number",
                                 trigger=self.TASK + " revenue")
                res = store.record_learning_applications(self.TASK,
                                                         session_id="S1",
                                                         limit=1)
                shown = set(r["rule_uuid"] for r in res["results"])
                # Whichever of the two the ranker did NOT return is the one
                # this test rewrites, so the fixture cannot depend on a tie
                # being broken one way.
                rewritten = [r for r in (one, two)
                             if r["rule_uuid"] not in shown][0]
                # Approved long ago, but its CURRENT wording was written after
                # the retrieval. Ranking today's text and calling the result a
                # historical miss would blame a rule for words it did not have.
                store.conn.execute(
                    "UPDATE learning_rules SET founder_approved_at=? "
                    "WHERE rule_uuid=?", (_PAST, rewritten["rule_uuid"]))
                store.conn.execute(
                    "UPDATE learning_rule_versions SET created_at=? "
                    "WHERE rule_uuid=?", (_FUTURE, rewritten["rule_uuid"]))
                store.conn.commit()
                out = store.classify_learning_applications()
                self.assertNotIn(rewritten["rule_uuid"],
                                 [m["rule_uuid"] for m in out["retrieval_misses"]])
                kinds = [u["evidence"] for u in out["not_decidable_tasks"]]
                self.assertIn("rule_changed_since_retrieval", kinds)

    def test_metrics_count_the_two_miss_kinds_under_their_own_names(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._cut_fixture(store)
                m = store.learning_loop_failures(window_days=None)
                self.assertEqual(m["counts"]["retrieval_limit_miss"], 1)
                self.assertEqual(m["counts"]["retrieval_miss"], 0)


class TestPostAuditLoopP6Schema4Migration(unittest.TestCase):
    """Schema 3 to 4. Same discipline as the two migration suites above: the
    fixture is a REAL store reverted to schema 3, never hand-written DDL."""

    def _schema3_store(self, d):
        with bs.Store(d) as store:
            store.claim("alpha", "persistent", "keep me", ["src/a.py"])
            c = store.capture_learning_candidate(
                "manual", trigger="writing an executive update",
                action="state customer impact first",
                because="leaders need the business state first",
                scope_type="global", scope_key="")
            _approved(store, c["candidate_uuid"], founder_ref="founder")
            store.record_learning_applications("writing an executive update",
                                               session_id="S-OLD")
        path = os.path.join(d, bs.STORE_DIRNAME, bs.STORE_FILENAME)
        conn = sqlite3.connect(path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            for t in bs._TABLES_RETRIEVAL:
                conn.execute("DROP TABLE IF EXISTS %s" % t)
            # The column goes by table rebuild rather than DROP COLUMN, which
            # needs SQLite 3.35. This project's floor is Python 3.9 and says
            # nothing about the SQLite it was built against, so the fixture
            # must not need a newer one than the product does.
            create = [s for s in bs._LEARNING_DDL_STATEMENTS
                      if "CREATE TABLE IF NOT EXISTS learning_applications" in s]
            self.assertEqual(len(create), 1)
            conn.execute("ALTER TABLE learning_applications RENAME TO la_pre_p6")
            conn.execute(create[0])
            cols = ", ".join(
                r[1] for r in conn.execute(
                    "PRAGMA table_info(learning_applications)").fetchall())
            conn.execute("INSERT INTO learning_applications (%s) "
                         "SELECT %s FROM la_pre_p6" % (cols, cols))
            conn.execute("DROP TABLE la_pre_p6")
            conn.execute("UPDATE meta SET value='3' WHERE key='schema_version'")
            conn.execute("COMMIT")
        finally:
            conn.close()
        return path

    def _snapshot(self, path):
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        try:
            out = {}
            for t in bs._TABLES_V3:
                rows = [dict(r) for r in conn.execute("SELECT * FROM %s" % t)]
                if t == "meta":
                    rows = [r for r in rows if r.get("key") != "schema_version"]
                out[t] = json.dumps(rows, sort_keys=True, default=str)
            return out
        finally:
            conn.close()

    def _tables(self, path):
        conn = sqlite3.connect(path)
        try:
            return {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            conn.close()

    def test_a_schema3_store_migrates_instead_of_being_quarantined(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._schema3_store(d)
            with bs.Store(d) as store:
                self.assertEqual(
                    store.conn.execute(
                        "SELECT value FROM meta WHERE key='schema_version'"
                    ).fetchone()["value"], str(bs.SCHEMA_VERSION))
            self.assertTrue(set(bs._TABLES_RETRIEVAL) <= self._tables(path))
            self.assertEqual(
                glob.glob(os.path.join(d, bs.STORE_DIRNAME, "*quarantine*")), [],
                "a healthy schema-3 store must MIGRATE, never be quarantined")

    def test_migration_preserves_every_schema3_row(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._schema3_store(d)
            before = self._snapshot(path)
            with bs.Store(d):
                pass
            after = self._snapshot(path)
            for table in before:
                if table == "learning_applications":
                    # The one table that gains a column, so its rows are
                    # compared field by field below rather than as JSON.
                    continue
                self.assertEqual(before[table], after[table], table)
            old = json.loads(before["learning_applications"])
            new = json.loads(after["learning_applications"])
            self.assertEqual(len(old), len(new))
            self.assertTrue(old, "the fixture must carry a real application row")
            for o, n in zip(old, new):
                for k, v in o.items():
                    self.assertEqual(n[k], v, k)

    def test_migration_invents_no_retrieval_run_for_an_older_row(self):
        """The dishonest half of this change would be manufacturing a run for
        every legacy application so the reports look complete."""
        with tempfile.TemporaryDirectory() as d:
            self._schema3_store(d)
            with bs.Store(d) as store:
                self.assertEqual(store.list_learning_retrieval_runs(), [])
                apps = store.list_learning_applications(session_id="S-OLD")
                self.assertTrue(apps)
                for a in apps:
                    self.assertIsNone(a["retrieval_uuid"])

    def test_migration_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._schema3_store(d)
            with bs.Store(d):
                pass
            first = self._snapshot(path)
            with bs.Store(d):
                pass
            self.assertEqual(first, self._snapshot(path))

    def test_calibrated_interrupted_migration_rolls_back_completely(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._schema3_store(d)
            original = bs._MIGRATIONS[3]

            def _fail_half_way(conn):
                conn.execute(bs._RETRIEVAL_RUN_DDL_STATEMENTS[0])
                raise RuntimeError("simulated interruption mid-migration")

            bs._MIGRATIONS[3] = _fail_half_way
            try:
                with self.assertRaises(RuntimeError):
                    bs.Store(d)
            finally:
                bs._MIGRATIONS[3] = original
            conn = sqlite3.connect(path)
            try:
                v = conn.execute(
                    "SELECT value FROM meta WHERE key='schema_version'").fetchone()[0]
            finally:
                conn.close()
            self.assertEqual(v, "3",
                             "an interrupted migration must not move the version")
            for t in bs._TABLES_RETRIEVAL:
                self.assertNotIn(t, self._tables(path))
            with bs.Store(d):
                pass
            self.assertTrue(set(bs._TABLES_RETRIEVAL) <= self._tables(path))

    def test_retrieval_run_ddl_split_matches_the_table_and_index_lists(self):
        self.assertEqual(len(bs._RETRIEVAL_RUN_DDL_STATEMENTS),
                         len(bs._TABLES_RETRIEVAL))
        self.assertEqual(len(bs._RETRIEVAL_RUN_INDEX_STATEMENTS), 1)


class TestPostAuditLoopP12Schema5Migration(unittest.TestCase):
    """LOOP P12: schema 4 to 5 adds the handovers table. Same three questions
    every migration in this project has to answer: does a healthy older store
    MIGRATE rather than get quarantined, does every existing row survive
    byte for byte, and does an interruption roll the whole thing back."""

    def _schema4_store(self, d):
        """A real store, built by the product, then walked BACK to schema 4 by
        dropping exactly what schema 5 adds. Same technique as the schema-3
        fixture above: build forward with the shipping code so the fixture
        cannot drift from a real store, then remove the newest layer."""
        with bs.Store(d) as store:
            rec = store.claim("payments", "persistent", objective="build payments",
                              files=["api/pay.py"], session_id="sessA")
            store.checkpoint(rec.lifecycle_uuid, rec.version, "wire the webhook")
        path = os.path.join(d, bs.STORE_DIRNAME, bs.STORE_FILENAME)
        conn = sqlite3.connect(path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            for t in bs._TABLES_HANDOVER:
                conn.execute("DROP TABLE IF EXISTS %s" % t)
            conn.execute("UPDATE meta SET value='4' WHERE key='schema_version'")
            conn.execute("COMMIT")
        finally:
            conn.close()
        return path

    def _snapshot(self, path):
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        try:
            out = {}
            for t in bs._TABLES_V4:
                rows = [dict(r) for r in conn.execute("SELECT * FROM %s" % t)]
                if t == "meta":
                    rows = [r for r in rows if r.get("key") != "schema_version"]
                out[t] = json.dumps(rows, sort_keys=True, default=str)
            return out
        finally:
            conn.close()

    def _tables(self, path):
        conn = sqlite3.connect(path)
        try:
            return {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            conn.close()

    def test_a_schema4_store_migrates_instead_of_being_quarantined(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._schema4_store(d)
            with bs.Store(d) as store:
                self.assertEqual(
                    store.conn.execute(
                        "SELECT value FROM meta WHERE key='schema_version'"
                    ).fetchone()["value"], str(bs.SCHEMA_VERSION))
            self.assertTrue(set(bs._TABLES_HANDOVER) <= self._tables(path))
            self.assertEqual(
                glob.glob(os.path.join(d, bs.STORE_DIRNAME, "*quarantine*")), [],
                "a healthy schema-4 store must MIGRATE, never be quarantined")

    def test_migration_preserves_every_schema4_row(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._schema4_store(d)
            before = self._snapshot(path)
            with bs.Store(d):
                pass
            self.assertEqual(before, self._snapshot(path))

    def test_migration_imports_no_appended_handover(self):
        """The dishonest half of this change would be scraping the handovers
        older versions appended into STATE.md and presenting them as records.
        Those are human prose with no reliable end marker; they stay put."""
        with tempfile.TemporaryDirectory() as d:
            self._schema4_store(d)
            io.open(os.path.join(d, "STATE.md"), "w", encoding="utf-8").write(
                "# Project STATE\n\n<!-- brothermode-handover:old:abc -->\n"
                "## Drained from thread mode: legacy\nkeep me\n")
            with bs.Store(d) as store:
                self.assertEqual(list(store.undelivered_handovers()), [])
            self.assertIn("keep me", io.open(
                os.path.join(d, "STATE.md"), encoding="utf-8").read())

    def test_migration_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._schema4_store(d)
            with bs.Store(d):
                pass
            first = self._snapshot(path)
            with bs.Store(d):
                pass
            self.assertEqual(first, self._snapshot(path))

    def test_calibrated_interrupted_migration_rolls_back_completely(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._schema4_store(d)
            original = bs._MIGRATIONS[4]

            def _fail_half_way(conn):
                conn.execute(bs._HANDOVER_DDL_STATEMENTS[0])
                raise RuntimeError("simulated interruption mid-migration")

            bs._MIGRATIONS[4] = _fail_half_way
            try:
                with self.assertRaises(RuntimeError):
                    bs.Store(d)
            finally:
                bs._MIGRATIONS[4] = original
            conn = sqlite3.connect(path)
            try:
                v = conn.execute(
                    "SELECT value FROM meta WHERE key='schema_version'").fetchone()[0]
            finally:
                conn.close()
            self.assertEqual(v, "4",
                             "an interrupted migration must not move the version")
            for t in bs._TABLES_HANDOVER:
                self.assertNotIn(t, self._tables(path))
            with bs.Store(d):
                pass
            self.assertTrue(set(bs._TABLES_HANDOVER) <= self._tables(path))

    def test_handover_ddl_split_matches_the_table_and_index_lists(self):
        self.assertEqual(len(bs._HANDOVER_DDL_STATEMENTS),
                         len(bs._TABLES_HANDOVER))
        self.assertEqual(len(bs._HANDOVER_INDEX_STATEMENTS), 3)

    def test_a_handover_body_is_redacted_in_dump_but_its_ids_are_not(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rec = store.claim("payments", "persistent", objective="build it",
                                  files=["api/pay.py"], session_id="sessA")
                store.checkpoint(rec.lifecycle_uuid, rec.version, "next step",
                                 decisions=[("notes", "key AKIAIOSFODNN7EXAMPLE")])
                rec = store.get(rec.lifecycle_uuid)
                store.transition(rec.lifecycle_uuid, rec.version, "parked",
                                 session_id="sessA", handover_heading="Drained: payments")
                data = store.dump()
            rows = data["handovers"]
            self.assertEqual(len(rows), 1)
            self.assertNotIn("AKIAIOSFODNN7EXAMPLE", json.dumps(rows),
                             "dump leaked a secret out of a handover body")
            self.assertEqual(rows[0]["lifecycle_uuid"], rec.lifecycle_uuid,
                             "the identifier must stay readable so a dump is usable")
            self.assertIn("WITHHELD", rows[0]["payload_fingerprint"],
                          "a digest column is withheld by name shape")


def _fts_env(on=True, forced_off=False):
    """Patch the two environment switches the fast path reads. Used as a
    context manager around a store OPEN, because the index is built (or not)
    at open time and that is exactly the decision under test."""
    env = {bs.FTS5_ENV: "1" if on else "",
           bs.FTS5_DISABLE_ENV: "1" if forced_off else ""}
    return mock.patch.dict(os.environ, env)


class TestPostAuditLoopP7Fts5(unittest.TestCase):
    """Post-audit LOOP P7: FTS5 as an OPTIONAL fast path.

    The invariant every test here defends is one sentence: lexical retrieval
    stays fully functional and honest when the index is off, absent, broken, or
    unavailable. So the tests come in pairs wherever they can: the same fixture,
    the same query, once with the index and once without, with the difference
    stated rather than assumed."""

    TRIGGER = "when pushing a branch to github"
    ACTION = "use the GitHub Desktop app"
    BECAUSE = "the house route is the app, not the command line"

    def _rule(self, store, trigger=None, action=None, severity="soft",
              because=None):
        c = store.capture_learning_candidate(
            "manual", trigger=trigger or self.TRIGGER,
            action=action or self.ACTION,
            because=because if because is not None else self.BECAUSE,
            scope_type="global", scope_key="",
            raw_text="RAWFOUNDERSOURCE the founder's actual words here")
        return _approved(store, c["candidate_uuid"],
                          founder_ref="founder in chat", severity=severity)

    def _fts_rows(self, store):
        return store.conn.execute(
            "SELECT * FROM %s" % bs._FTS_TABLE).fetchall()

    # -- off by default ------------------------------------------------

    def test_index_is_off_until_the_founder_asks_for_it(self):
        """An optional capability that arrives switched on is not optional.
        A store opened with no environment at all must have no index table,
        report lexical, and rank exactly as it did before this loop."""
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.dict(os.environ, {bs.FTS5_ENV: "",
                                              bs.FTS5_DISABLE_ENV: ""}):
                with bs.Store(d) as store:
                    self._rule(store)
                    self.assertFalse(store.fts_available())
                    self.assertIsNone(store.conn.execute(
                        "SELECT name FROM sqlite_master WHERE name=?",
                        (bs._FTS_TABLE,)).fetchone())
                    res = store.retrieve_learning_rules("pushing a branch")
                    self.assertEqual(res["mode"], "lexical")
                    self.assertEqual(res["results"][0]["why"]["mode"], "lexical")

    def test_enabling_it_builds_and_populates_the_index_at_open(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.dict(os.environ, {bs.FTS5_ENV: "",
                                              bs.FTS5_DISABLE_ENV: ""}):
                with bs.Store(d) as store:
                    self._rule(store)
            with _fts_env():
                with bs.Store(d) as store:
                    if not store.fts_available():
                        self.skipTest("this SQLite build has no FTS5 module")
                    # Populated, not merely created: an empty index would make
                    # every query miss and the relevance floor would then hide
                    # rules the lexical path finds.
                    self.assertEqual(len(self._fts_rows(store)), 1)
                    status = store.learning_index_status()
                    self.assertEqual(status["mode"], "fts5")
                    self.assertEqual(status["indexed_rows"], 1)

    # -- the measured gain, and the fallback beside it ------------------

    def test_stemmed_query_finds_a_rule_the_exact_path_cannot(self):
        """The labeled fixture, reproduced from a real CLI run: the founder
        writes 'pushed', the rule says 'pushing'. Lexical finds nothing (no
        shared token), FTS5 finds it through the porter stemmer. This is the
        only retrieval-quality claim this loop makes, and it is measured
        against BOTH modes in one test so it cannot rot into a claim about
        FTS5 alone."""
        query = "already pushed everything upstream"
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.dict(os.environ, {bs.FTS5_ENV: "",
                                              bs.FTS5_DISABLE_ENV: ""}):
                with bs.Store(d) as store:
                    self._rule(store, because="")
                    lexical = store.retrieve_learning_rules(query)
            self.assertEqual(lexical["mode"], "lexical")
            self.assertEqual(lexical["results"], [])
            with _fts_env():
                with bs.Store(d) as store:
                    if not store.fts_available():
                        self.skipTest("this SQLite build has no FTS5 module")
                    fast = store.retrieve_learning_rules(query)
            self.assertEqual(fast["mode"], "fts5")
            self.assertEqual(len(fast["results"]), 1)
            self.assertGreater(fast["results"][0]["why"]["bm25"], 0)

    def test_exact_query_returns_the_same_rules_in_both_modes(self):
        """The fallback is only complete if it returns the same rules. Same
        store, same query, both modes, compared as a set of uuids."""
        query = "pushing a branch to github"
        with tempfile.TemporaryDirectory() as d:
            with _fts_env():
                with bs.Store(d) as store:
                    self._rule(store)
                    self._rule(store, trigger="writing an executive update",
                               action="state customer impact first")
                    if not store.fts_available():
                        self.skipTest("this SQLite build has no FTS5 module")
                    fast = store.retrieve_learning_rules(query)
            with _fts_env(on=True, forced_off=True):
                with bs.Store(d) as store:
                    self.assertFalse(store.fts_available())
                    slow = store.retrieve_learning_rules(query)
            self.assertEqual(fast["mode"], "fts5")
            self.assertEqual(slow["mode"], "lexical")
            self.assertEqual([r["rule_uuid"] for r in fast["results"]],
                             [r["rule_uuid"] for r in slow["results"]])

    def test_forced_unavailable_leaves_a_built_index_untouched_and_unused(self):
        """The force-unavailable probe the plan asks for. The index still
        exists on disk; the switch alone must be enough to prove the lexical
        path is intact, with no file surgery."""
        with tempfile.TemporaryDirectory() as d:
            with _fts_env():
                with bs.Store(d) as store:
                    self._rule(store)
                    if not store.fts_available():
                        self.skipTest("this SQLite build has no FTS5 module")
            with _fts_env(on=True, forced_off=True):
                with bs.Store(d) as store:
                    self.assertFalse(store.fts_available())
                    self.assertIsNone(store._fts_scores("pushing"))
                    res = store.retrieve_learning_rules("pushing a branch")
                    self.assertEqual(res["mode"], "lexical")
                    self.assertEqual(len(res["results"]), 1)
                    # The table is still there. Disabling is not deleting.
                    self.assertIsNotNone(store.conn.execute(
                        "SELECT name FROM sqlite_master WHERE name=?",
                        (bs._FTS_TABLE,)).fetchone())

    def test_store_opens_and_retrieves_when_the_sqlite_build_has_no_fts5(self):
        """The environment the plan names last and cares about most: FTS5
        simply is not there. The probe is forced to say so."""
        with tempfile.TemporaryDirectory() as d:
            with _fts_env():
                with mock.patch.object(bs, "_fts5_probe", lambda conn: False):
                    with bs.Store(d) as store:
                        rule = self._rule(store)
                        self.assertFalse(store.fts_available())
                        res = store.retrieve_learning_rules("pushing a branch")
                        self.assertEqual(res["mode"], "lexical")
                        self.assertEqual(res["results"][0]["rule_uuid"],
                                          rule["rule_uuid"])
                        self.assertTrue(store.learning_verify()["ok"])
                        rebuilt = store.rebuild_learning_index()
                        self.assertFalse(rebuilt["ok"])
                        self.assertIn("no FTS5 module", rebuilt["reason"])

    # -- gates survive everything --------------------------------------

    def test_a_broken_index_never_costs_the_founder_a_gate(self):
        """The index is destroyed under an OPEN store, mid-session, which is
        the shape a real failure takes. The gate must still be delivered and
        the mode must stop claiming fts5 the moment it stops being true."""
        with tempfile.TemporaryDirectory() as d:
            with _fts_env():
                with bs.Store(d) as store:
                    if not store.fts_available():
                        self.skipTest("this SQLite build has no FTS5 module")
                    gate = self._rule(store, severity="gate",
                                       trigger="before any irreversible command",
                                       action="print what it will affect and ask")
                    store.conn.execute("DROP TABLE %s" % bs._FTS_TABLE)
                    res = store.retrieve_learning_rules(
                        "unrelated task about orb colours", limit=0)
                    self.assertEqual(res["mode"], "lexical")
                    self.assertEqual(res["gates_returned"], 1)
                    self.assertEqual(res["results"][0]["rule_uuid"],
                                      gate["rule_uuid"])
                    self.assertFalse(store.fts_available())

    def _quarantines(self, store):
        d = os.path.dirname(store.path)
        return sorted(n for n in os.listdir(d) if ".quarantine-" in n)

    def test_a_dropped_index_never_costs_the_founder_the_store(self):
        """P7 fix round, CRITICAL, reproduced on a real store before the fix:
        the index table was dropped mid-session, the next approval routed its
        index write through _exec, _exec read "no such table:
        learning_rule_fts" as structural damage, and _quarantine_and_raise
        MOVED store.sqlite3 aside. The approval in flight, every rule, every
        claim: gone, because an OPTIONAL accelerator lost a table.

        The `except sqlite3.Error` written around that write to keep the
        failure direction lexical could not fire, because StoreCorrupt is not
        a sqlite3.Error, which this asserts directly so the guard cannot go
        back to being decorative."""
        self.assertFalse(issubclass(bs.StoreCorrupt, sqlite3.Error))
        with tempfile.TemporaryDirectory() as d:
            with _fts_env():
                with bs.Store(d) as store:
                    if not store.fts_available():
                        self.skipTest("this SQLite build has no FTS5 module")
                    self._rule(store)
                    store.conn.execute("DROP TABLE %s" % bs._FTS_TABLE)
                    rule = self._rule(store, trigger="when the founder asks "
                                                     "for a summary",
                                      action="keep it under ten lines")
                    # The approval LANDED, the file is where it was, and the
                    # fast path took itself off instead of taking the store.
                    self.assertEqual(rule["state"], "approved")
                    self.assertFalse(store.fts_available())
                    self.assertTrue(os.path.exists(store.path))
                    self.assertEqual(self._quarantines(store), [])
                    self.assertEqual(
                        store.retrieve_learning_rules("summary")["mode"],
                        "lexical")
                    self.assertEqual(
                        len(store.list_learning_rules()), 2)

    def test_diagnostics_on_a_dropped_index_report_rather_than_quarantine(self):
        """Same fix round. learning_index_status calls itself "read only, and
        safe on a store with no index at all" and learning_fts_drift is the
        check that makes the fast path trustworthy. Both counted through
        _exec, so on a dropped index the STATUS COMMAND quarantined the store
        and the drift check then raised AttributeError on the connection it
        had just had closed underneath it. A diagnostic that destroys what it
        inspects is worse than no diagnostic."""
        with tempfile.TemporaryDirectory() as d:
            with _fts_env():
                with bs.Store(d) as store:
                    if not store.fts_available():
                        self.skipTest("this SQLite build has no FTS5 module")
                    self._rule(store)
                    store.conn.execute("DROP TABLE %s" % bs._FTS_TABLE)
                    drift = store.learning_fts_drift()
                    self.assertTrue(drift)
                    self.assertEqual(drift[0][0], "fts-drift")
                    self.assertIn("could not be read", drift[0][1])
                    status = store.learning_index_status()
                    self.assertFalse(status["available"])
                    self.assertEqual(status["mode"], "lexical")
                    self.assertIsNone(status["indexed_rows"])
                    self.assertTrue(os.path.exists(store.path))
                    self.assertEqual(self._quarantines(store), [])
                    # And the repair command still repairs, at exit 0.
                    self.assertTrue(store.rebuild_learning_index()["ok"])
                    self.assertEqual(store.learning_fts_drift(), [])

    def test_rules_written_with_the_index_off_are_reconciled_before_it_answers(self):
        """P7 fix round, MAJOR, reproduced on the real CLI. The switch is a
        per-PROCESS environment variable and _ensure_fts repopulated only when
        it had just CREATED the table, so ONE ordinary shell that approves a
        rule without the variable left the index short a row FOREVER: the next
        FTS5 run found a table, trusted it, and ranked an indexed rule sharing
        one common word above an unindexed rule with three times its exact
        overlap. With --limit the correct rule vanished entirely.

        The index is now reconciled at the point it is CONSUMED, so it cannot
        answer a query while it disagrees with the rules."""
        with tempfile.TemporaryDirectory() as d:
            with _fts_env():
                with bs.Store(d) as store:
                    if not store.fts_available():
                        self.skipTest("this SQLite build has no FTS5 module")
                    indexed = self._rule(
                        store, trigger="before pushing code to github",
                        action="always run the test suite first", because="")
            with mock.patch.dict(os.environ, {bs.FTS5_ENV: "",
                                              bs.FTS5_DISABLE_ENV: ""}):
                with bs.Store(d) as store:
                    self.assertFalse(store.fts_available())
                    unindexed = self._rule(
                        store, trigger="when writing release notes",
                        action="list every breaking change", because="")
            query = "run through the release notes and list every breaking change"
            with _fts_env():
                with bs.Store(d) as store:
                    self.assertEqual(len(self._fts_rows(store)), 1)
                    res = store.retrieve_learning_rules(query, limit=1)
                    self.assertEqual(res["mode"], "fts5")
                    self.assertEqual([r["rule_uuid"] for r in res["results"]],
                                      [unindexed["rule_uuid"]])
                    self.assertNotEqual(unindexed["rule_uuid"],
                                        indexed["rule_uuid"])
                    self.assertEqual(len(self._fts_rows(store)), 2)
                    self.assertEqual(self._drifted(store), [])

    def test_an_edit_made_with_the_index_off_cannot_answer_from_deleted_text(self):
        """The same root cause in its worst shape: the founder REPOINTS a rule
        at a different situation in a shell without the variable, and the
        stale index then injects that rule into the model's context for the
        task it no longer covers, matching on text the founder deleted, while
        the CLI explains the hit as a stem match no live word can produce.
        Reproduced on the real CLI before the fix (rule at version 2, query
        'I already pushed everything upstream', rank=1)."""
        with tempfile.TemporaryDirectory() as d:
            with _fts_env():
                with bs.Store(d) as store:
                    if not store.fts_available():
                        self.skipTest("this SQLite build has no FTS5 module")
                    rule = self._rule(store, because="")
                    stale = store.retrieve_learning_rules(
                        "already pushed everything upstream")
                    self.assertEqual([r["rule_uuid"] for r in stale["results"]],
                                      [rule["rule_uuid"]])
            with mock.patch.dict(os.environ, {bs.FTS5_ENV: "",
                                              bs.FTS5_DISABLE_ENV: ""}):
                with bs.Store(d) as store:
                    _edited(store, rule["rule_uuid"], 1,
                            trigger="reviewing a pull request",
                            action="read every hunk", because="typos hide",
                            change_type="edited",
                            change_reason="the founder repointed it")
            with _fts_env():
                with bs.Store(d) as store:
                    res = store.retrieve_learning_rules(
                        "already pushed everything upstream")
                    self.assertEqual(res["results"], [])
                    hit = store.retrieve_learning_rules("reviewing a pull request")
                    self.assertEqual([r["rule_uuid"] for r in hit["results"]],
                                      [rule["rule_uuid"]])
                    self.assertEqual(self._drifted(store), [])

    def test_a_hostile_query_cannot_raise_or_quarantine(self):
        """FTS5 reads NEAR, *, ^, - and column filters as operators. A founder
        task containing them must be a search, not a syntax error, and above
        all not a quarantined store."""
        hostile = ['github NEAR/2 "x* OR ^col:',
                   'push AND (github OR', '"unbalanced', '-*', 'col:trigger_text',
                   'rule_uuid : "x"', '\\', 'push"" OR "']
        with tempfile.TemporaryDirectory() as d:
            with _fts_env():
                with bs.Store(d) as store:
                    if not store.fts_available():
                        self.skipTest("this SQLite build has no FTS5 module")
                    self._rule(store)
                    for q in hostile:
                        res = store.retrieve_learning_rules(q)
                        self.assertIn(res["mode"], ("fts5", "lexical"))
                    # Still healthy, still fast: nothing above was allowed to
                    # switch the index off or move the file aside.
                    self.assertTrue(store.fts_available())
                    self.assertTrue(store.learning_verify()["ok"])

    def test_unicode_french_and_japanese_queries_are_searches_not_crashes(self):
        with tempfile.TemporaryDirectory() as d:
            with _fts_env():
                with bs.Store(d) as store:
                    if not store.fts_available():
                        self.skipTest("this SQLite build has no FTS5 module")
                    fr = self._rule(store,
                                     trigger="quand tu écris une révision",
                                     action="cite la source à chaque fois",
                                     because="")
                    self._rule(store, trigger="日本語のドキュメント",
                               action="敬語を使う", because="")
                    hit = store.retrieve_learning_rules("une révision à faire")
                    self.assertIn(fr["rule_uuid"],
                                  [r["rule_uuid"] for r in hit["results"]])
                    jp = store.retrieve_learning_rules("日本語のドキュメント")
                    self.assertEqual(jp["mode"], "fts5")
                    self.assertTrue(store.learning_verify()["ok"])

    # -- what must never enter the index -------------------------------

    def test_raw_founder_source_text_never_enters_the_index(self):
        """The acceptance criterion with teeth. The candidate's raw_text and
        the approval evidence excerpt both carry a marker; neither may appear
        anywhere in the index, columns or content."""
        with tempfile.TemporaryDirectory() as d:
            with _fts_env():
                with bs.Store(d) as store:
                    if not store.fts_available():
                        self.skipTest("this SQLite build has no FTS5 module")
                    self._rule(store)
                    blob = "\n".join(
                        "|".join("" if v is None else str(v) for v in row)
                        for row in self._fts_rows(store))
                    self.assertNotIn("RAWFOUNDERSOURCE", blob)
                    # And the columns themselves are the named five plus the
                    # two identifiers, so a later edit cannot widen the index
                    # without this failing.
                    cols = [r[1] for r in store.conn.execute(
                        "PRAGMA table_info(%s)" % bs._FTS_TABLE).fetchall()]
                    self.assertEqual(cols, ["rule_uuid", "rule_version"]
                                      + list(bs._FTS_TEXT_COLUMNS))

    # -- drift, and the calibration that proves the check works ---------

    def _drifted(self, store):
        return [f for f in store.learning_verify()["findings"]
                if f["code"] == "fts-drift"]

    def test_drift_is_detected_and_rebuild_restores_parity(self):
        """PASS, REINJECT, FAILS RIGHT, RESTORE, PASS, once per drift shape.
        A verify check nobody has watched fail is decoration."""
        shapes = {
            "missing": "DELETE FROM %s" % bs._FTS_TABLE,
            "text-mismatch": ("UPDATE %s SET trigger_text='tampered'"
                              % bs._FTS_TABLE),
            "stale-version": "UPDATE %s SET rule_version=99" % bs._FTS_TABLE,
        }
        with tempfile.TemporaryDirectory() as d:
            with _fts_env():
                with bs.Store(d) as store:
                    if not store.fts_available():
                        self.skipTest("this SQLite build has no FTS5 module")
                    self._rule(store)
                    self.assertEqual(self._drifted(store), [])
                    for name, sql in shapes.items():
                        store.conn.execute(sql)
                        found = self._drifted(store)
                        self.assertEqual(len(found), 1,
                                          "%s drift went undetected" % name)
                        self.assertFalse(store.learning_verify()["ok"])
                        self.assertTrue(store.rebuild_learning_index()["ok"])
                        self.assertEqual(self._drifted(store), [],
                                          "rebuild did not restore parity "
                                          "after %s" % name)
                    # The extra-row shape, which no rebuild-in-place would
                    # catch: a row for a rule that does not exist.
                    store.conn.execute(
                        "INSERT INTO %s (rule_uuid, rule_version, %s) "
                        "VALUES ('deadbeef',1,'ghost','x','','','')"
                        % (bs._FTS_TABLE, ", ".join(bs._FTS_TEXT_COLUMNS)))
                    found = self._drifted(store)
                    self.assertEqual(len(found), 1)
                    self.assertIn("no current rule version", found[0]["detail"])
                    self.assertTrue(store.rebuild_learning_index()["ok"])
                    self.assertEqual(self._drifted(store), [])

    def test_an_edit_reaches_the_index_in_the_same_transaction(self):
        """The drift shape that would otherwise be normal operation."""
        with tempfile.TemporaryDirectory() as d:
            with _fts_env():
                with bs.Store(d) as store:
                    if not store.fts_available():
                        self.skipTest("this SQLite build has no FTS5 module")
                    rule = self._rule(store)
                    _edited(store, rule["rule_uuid"], 1,
                            trigger="when publishing a release note",
                            action="run it past the founder first",
                            change_type="narrowed",
                            change_reason="the founder narrowed it")
                    self.assertEqual(self._drifted(store), [])
                    rows = self._fts_rows(store)
                    self.assertEqual(len(rows), 1)
                    self.assertEqual(rows[0]["rule_version"], 2)
                    self.assertIn("release note", rows[0]["trigger_text"])
                    hit = store.retrieve_learning_rules("publishing a release note")
                    self.assertEqual([r["rule_uuid"] for r in hit["results"]],
                                      [rule["rule_uuid"]])

    def test_verify_note_always_states_which_situation_it_was_in(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.dict(os.environ, {bs.FTS5_ENV: "",
                                              bs.FTS5_DISABLE_ENV: ""}):
                with bs.Store(d) as store:
                    res = store.learning_verify()
                    self.assertIn("fts-drift", res["checks"])
                    self.assertTrue(any("no search index is enabled" in n
                                        for n in res["notes"]))
            with _fts_env():
                with bs.Store(d) as store:
                    if not store.fts_available():
                        self.skipTest("this SQLite build has no FTS5 module")
                    self.assertTrue(any("the search index is on" in n
                                        for n in store.learning_verify()["notes"]))

    # -- the schema is not allowed to depend on any of this -------------

    def test_the_index_is_not_part_of_the_schema(self):
        with tempfile.TemporaryDirectory() as d:
            with _fts_env():
                with bs.Store(d) as store:
                    if not store.fts_available():
                        self.skipTest("this SQLite build has no FTS5 module")
                    self._rule(store)
                    path = store.path
            for tup in (bs._TABLES, bs._TABLES_LEARNING, bs._TABLES_RECEIPTS,
                        bs._TABLES_RETRIEVAL):
                self.assertNotIn(bs._FTS_TABLE, tup)
            # Deleting the index by hand costs a founder nothing but speed:
            # the store still opens, verifies and retrieves.
            conn = sqlite3.connect(path)
            conn.isolation_level = None
            conn.execute("DROP TABLE %s" % bs._FTS_TABLE)
            conn.close()
            with mock.patch.dict(os.environ, {bs.FTS5_ENV: "",
                                              bs.FTS5_DISABLE_ENV: ""}):
                with bs.Store(d) as store:
                    self.assertTrue(store.learning_verify()["ok"])
                    self.assertEqual(
                        store.retrieve_learning_rules("pushing a branch")["mode"],
                        "lexical")

    def test_env_switches_read_exactly_what_they_document(self):
        self.assertTrue(bs.fts5_requested({bs.FTS5_ENV: "1"}))
        self.assertTrue(bs.fts5_requested({bs.FTS5_ENV: " YES "}))
        self.assertFalse(bs.fts5_requested({}))
        self.assertFalse(bs.fts5_requested({bs.FTS5_ENV: "0"}))
        self.assertFalse(bs.fts5_requested({bs.FTS5_ENV: "maybe"}))
        # The safe direction wins.
        self.assertFalse(bs.fts5_requested({bs.FTS5_ENV: "1",
                                            bs.FTS5_DISABLE_ENV: "1"}))
class TestLoop11ExportWithholdingPolicy(unittest.TestCase):
    """LOOP 11 workstream A. dump() redacted by default, but redact_text is a
    secret SCRUBBER: founder PROSE has no secret shape, so an ordinary dump
    reproduced objectives, evidence, digest bodies, transition notes,
    decisions, directives and claimed paths verbatim. There is now ONE
    withholding policy (bm_store.export_column) that every export shares:
    structural columns pass, records.name and records.tier are scrubbed, and
    everything else founder-typed is withheld entirely."""

    PROSE = {
        "objective": "ACME turnaround, Q3 revenue miss, do not mention",
        "evidence": "call with Dana at ACME went badly on Tuesday",
        "note": "parked because ACME pushed the deadline again",
        "decision": "we will not tell ACME about the Q3 miss",
        "directive": "draft the ACME apology, keep the number out",
        "next_intent": "rewrite the ACME summary",
        "body": "the ACME account is the whole quarter",
    }
    ABS_PATH = "/Users/janedoe/Documents/clients/acme/plan.md"

    def _seed(self, d):
        store = bs.Store(d)
        try:
            rec = store.claim("payments", "persistent", self.PROSE["objective"],
                              ["api/pay.py"], session_id="s1")
            store.checkpoint(rec.lifecycle_uuid, rec.version,
                             self.PROSE["next_intent"], body=self.PROSE["body"])
            rec2 = store.get(rec.lifecycle_uuid)
            store.decide(rec2.lifecycle_uuid, rec2.version, "disclosure",
                         self.PROSE["decision"])
            rec3 = store.get(rec.lifecycle_uuid)
            store.send(rec3.lifecycle_uuid, self.PROSE["directive"])
            rec4 = store.get(rec.lifecycle_uuid)
            # complete, not parked: records.evidence is only written on the
            # active -> complete edge (it is the proof the work is done).
            store.transition(rec4.lifecycle_uuid, rec4.version, "complete",
                             session_id="s1", note=self.PROSE["note"],
                             evidence=self.PROSE["evidence"])
        finally:
            store.close()

    def test_default_dump_reproduces_no_founder_prose_and_no_absolute_path(self):
        with tempfile.TemporaryDirectory() as d:
            self._seed(d)
            store = bs.ReadOnlyStore(d)
            try:
                default = json.dumps(store.dump())
                raw = json.dumps(store.dump(raw=True))
            finally:
                store.close()
            for label, text in sorted(self.PROSE.items()):
                self.assertNotIn(text, default,
                                 "%s survived an ordinary dump" % label)
                self.assertIn(text, raw,
                              "--raw must still return %s verbatim" % label)
            # FIX-ROUND 11: the claimed path is RELATIVE, project-internal
            # structure and it is what the fence primitive exists to report,
            # so it is scrub-only and stays legible. An ABSOLUTE claimed path
            # is still masked (test_default_dump_masks_an_absolute_claim_path).
            self.assertIn("api/pay.py", default)
            self.assertIn("api/pay.py", raw)
            # Structural identity survives, or the export is useless.
            self.assertIn("payments", default)
            self.assertIn("complete", default)
            self.assertIn("WITHHELD", default)

    def test_default_dump_masks_an_absolute_path_in_a_scrub_only_column(self):
        # records.tier is a scrub-only column, so it is the one an ordinary
        # dump still renders and therefore the one that has to prove path
        # masking. (records.name cannot hold a path at all: valid_name
        # rejects "/", which is its own, older guard.)
        with tempfile.TemporaryDirectory() as d:
            store = bs.Store(d)
            try:
                store.claim("plan", "ephemeral", "obj", [], session_id="s1",
                            tier=self.ABS_PATH)
            finally:
                store.close()
            store = bs.ReadOnlyStore(d)
            try:
                default = json.dumps(store.dump())
                raw = json.dumps(store.dump(raw=True))
            finally:
                store.close()
            self.assertNotIn("janedoe", default)
            self.assertNotIn("acme", default)
            self.assertIn("PATH WITHHELD", default)
            self.assertIn("janedoe", raw)

    def test_calibrated_reinjecting_the_scrub_only_policy_leaks_prose(self):
        """CALIBRATION. Put the prose columns back under the pre-LOOP-11
        policy (scrub, do not withhold) and the exact reported leak returns;
        restore the shipped policy and it is gone again."""
        old_policy = frozenset(set(bs._DUMP_SCRUB_ONLY_COLUMNS) | {
            ("records", "objective"), ("records", "evidence"),
            ("digests", "body"), ("transitions", "note"),
            ("decisions", "text"), ("decisions", "topic"),
            ("digests", "next_intent"), ("directives", "text")})
        with tempfile.TemporaryDirectory() as d:
            self._seed(d)
            store = bs.ReadOnlyStore(d)
            try:
                shipped_before = json.dumps(store.dump())
                with mock.patch.object(bs, "_DUMP_SCRUB_ONLY_COLUMNS", old_policy):
                    reinjected = json.dumps(store.dump())
                shipped_after = json.dumps(store.dump())
            finally:
                store.close()
            for label, text in sorted(self.PROSE.items()):
                self.assertNotIn(text, shipped_before, label)
                self.assertIn(text, reinjected,
                              "REINJECTION CHECK: %s must leak under the old "
                              "scrub-only policy" % label)
                self.assertNotIn(text, shipped_after, label)

    def test_export_policy_scrub_only_set_stays_closed(self):
        """Growing the scrub-only set is a privacy decision, so it fails here
        rather than passing quietly. Update this list deliberately."""
        self.assertEqual(sorted(bs._DUMP_SCRUB_ONLY_COLUMNS),
                          [("claims", "path"),
                           ("records", "name"), ("records", "tier")])

    def test_export_policy_id_shaped_set_stays_closed(self):
        """Same rule for the shape-gated set: adding a column here is a
        privacy decision and must be made on purpose."""
        self.assertEqual(sorted(bs._DUMP_ID_SHAPED_COLUMNS), [
            ("autosave_receipts", "session_id"),
            ("autosave_receipts", "worktree_id"),
            ("learning_applications", "session_id"),
            ("learning_candidates", "source_session_id"),
            ("learning_evidence", "source_session_id"),
            ("records", "session_id"),
            ("transitions", "session_id"),
        ])
        # ...and no column may be in two policy sets at once.
        self.assertFalse(bs._DUMP_ID_SHAPED_COLUMNS & bs._DUMP_SAFE_COLUMNS)
        self.assertFalse(bs._DUMP_ID_SHAPED_COLUMNS
                         & bs._DUMP_SCRUB_ONLY_COLUMNS)

    def test_claim_path_is_scrub_only_not_safe(self):
        """claims.path is legible BECAUSE it is relative, and it is
        scrub-only rather than SAFE so that an absolute or secret-shaped
        value in that column is still masked/redacted on the way out. The
        store's own canonicalize_path refuses an absolute path outside the
        root before it can ever be stored (an older, separate guard), so
        this is checked at the policy function, which is where the
        defence-in-depth actually lives."""
        with self.assertRaises(bs.OwnershipRefused):
            with tempfile.TemporaryDirectory() as d:
                store = bs.Store(d)
                try:
                    store.claim("plan", "ephemeral", "obj", [self.ABS_PATH],
                                session_id="s1")
                finally:
                    store.close()
        self.assertEqual(bs.export_column("claims", "path", self.ABS_PATH),
                          bs.PATH_WITHHELD_MARKER)
        self.assertEqual(bs.export_column("claims", "path", "api/pay.py"),
                          "api/pay.py")
        self.assertIn("REDACTED",
                      bs.export_column("claims", "path",
                                       "AKIAIOSFODNN7EXAMPLE"))

    # -- FIX ROUND: caller-supplied session ids --------------------------

    SESSION_PATH = "/Users/jane.doe/Clients/Acme-Turnaround"
    SESSION_KEY = "sk-live_abcdefghijklmnopqrstuvwx"

    def _seed_session(self, d, session_id):
        store = bs.Store(d)
        try:
            rec = store.claim("payments", "ephemeral", "obj", [],
                              session_id=session_id)
            store.transition(rec.lifecycle_uuid, rec.version, "parked",
                             session_id=session_id, note="n")
        finally:
            store.close()

    def _default_dump(self, d):
        store = bs.ReadOnlyStore(d)
        try:
            return json.dumps(store.dump())
        finally:
            store.close()

    def test_caller_supplied_session_id_is_never_exported_verbatim(self):
        """--session is free text, not a machine id: a founder who passes a
        path or a key must not see it come back out of an ordinary dump."""
        for bad in (self.SESSION_PATH, self.SESSION_KEY,
                    "notes about the ACME Q3 miss"):
            with tempfile.TemporaryDirectory() as d:
                self._seed_session(d, bad)
                default = self._default_dump(d)
                self.assertNotIn(bad, default,
                                 "session_id %r survived an ordinary dump" % bad)
                self.assertIn("WITHHELD", default)

    def test_hand_typed_hyphenated_codename_is_withheld_not_exported(self):
        """LOOP 5, KNOWN-LIMITS: 'a hand-typed hyphenated codename with no
        separators passes the shape gate'. This is a human session LABEL,
        not a generated id, and must be withheld like any other founder
        text -- it merely happened to be typed without spaces."""
        codename = "acme-turnaround-q3-canary"
        self.assertFalse(bs.is_id_shaped(codename), codename)
        with tempfile.TemporaryDirectory() as d:
            self._seed_session(d, codename)
            default = self._default_dump(d)
            self.assertNotIn(codename, default,
                             "hand-typed session label %r survived an "
                             "ordinary dump" % codename)
            self.assertIn("WITHHELD", default)

    def test_generated_session_id_still_exports_so_rows_still_join(self):
        """The gate must not cost the join a dump is read for."""
        generated = bs._default_cli_session_id()
        self.assertTrue(bs.is_id_shaped(generated), generated)
        with tempfile.TemporaryDirectory() as d:
            self._seed_session(d, generated)
            default = self._default_dump(d)
            # One records row plus the two transitions a claim-then-park
            # writes: three carriers of the same session id, all still legible.
            self.assertEqual(default.count('"%s"' % generated), 3,
                             "records.session_id and transitions.session_id "
                             "must both still carry the generated id")

    def test_calibrated_reinjecting_session_id_as_safe_leaks_the_path(self):
        """CALIBRATION for the session_id fix: put session_id back in the
        SAFE set (its pre-fix home) and the reported leak returns verbatim;
        restore the shipped policy and it is gone again."""
        old_safe = frozenset(set(bs._DUMP_SAFE_COLUMNS) | {
            ("records", "session_id"), ("transitions", "session_id")})
        with tempfile.TemporaryDirectory() as d:
            self._seed_session(d, self.SESSION_PATH)
            shipped_before = self._default_dump(d)
            with mock.patch.object(bs, "_DUMP_SAFE_COLUMNS", old_safe):
                reinjected = self._default_dump(d)
            shipped_after = self._default_dump(d)
        self.assertNotIn(self.SESSION_PATH, shipped_before)
        self.assertEqual(reinjected.count(self.SESSION_PATH), 3,
                         "REINJECTION CHECK: the session_id path leak must "
                         "come back under the pre-fix safe-column policy")
        self.assertNotIn(self.SESSION_PATH, shipped_after)

    def test_calibrated_reverting_the_loose_id_shape_leaks_the_codename(self):
        """CALIBRATION for the LOOP 5 session-label fix: put the old, loose
        short-tag character class back and the hand-typed codename exports
        again; restore the shipped four-shape allowlist and it is gone."""
        old_re = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
        codename = "acme-turnaround-q3-canary"
        with tempfile.TemporaryDirectory() as d:
            self._seed_session(d, codename)
            shipped_before = self._default_dump(d)
            with mock.patch.object(bs, "_ID_SHAPED_RE", old_re):
                reinjected = self._default_dump(d)
            shipped_after = self._default_dump(d)
        self.assertNotIn(codename, shipped_before)
        self.assertIn(codename, reinjected,
                     "REINJECTION CHECK: the loose shape class must let the "
                     "hand-typed codename back out")
        self.assertNotIn(codename, shipped_after)

    # -- FIX ROUND: non-ASCII and punctuation path tails -----------------

    LEAKY_PATHS = (
        ("/Users/m\u00fcller/Kunden/Siemens-deal", "ller/Kunden"),
        ("/Users/\u5c71\u7530/\u9867\u5ba2/ACME", "\u5c71\u7530"),
        ("C:\\Users\\\u0418\u0432\u0430\u043d\u043e\u0432\\clients\\acme",
         "\u0418\u0432\u0430\u043d\u043e\u0432"),
        ("/Users/Jos\u00e9-Dupont/clients/acme-turnaround", "Dupont"),
        ("/Users/j/C++Projects/acme-secret", "++Projects"),
        ("/Users/j/proj@acme/secret", "@acme"),
        ("/Users/j/50%off-acme/deal", "%off-acme"),
        ("/home/user/clients/\u5317\u4eac-deal/notes", "\u5317\u4eac"),
    )

    def test_mask_absolute_paths_leaves_no_tail_after_a_non_ascii_component(self):
        """The pre-fix ASCII-only body class stopped at the first non-ASCII
        or punctuation byte and emitted the whole sensitive TAIL."""
        for path, leaked_fragment in self.LEAKY_PATHS:
            masked = bs.mask_absolute_paths(path)
            self.assertEqual(masked, bs.PATH_WITHHELD_MARKER,
                             "%r masked to %r" % (path, masked))
            self.assertNotIn(leaked_fragment, masked)

    def test_mask_absolute_paths_keeps_prose_and_relative_paths_intact(self):
        """The wider class must not start eating sentences."""
        self.assertEqual(bs.mask_absolute_paths("api/pay.py"), "api/pay.py")
        self.assertEqual(bs.mask_absolute_paths("and/or"), "and/or")
        self.assertEqual(bs.mask_absolute_paths("3/4 of the way"),
                          "3/4 of the way")
        self.assertEqual(bs.mask_absolute_paths("see /Users/j/x."),
                          "see " + bs.PATH_WITHHELD_MARKER + ".")
        self.assertEqual(bs.mask_absolute_paths("really/. no"), "really/. no")
        self.assertEqual(
            bs.mask_absolute_paths("the file (/Users/j/x) is gone"),
            "the file (" + bs.PATH_WITHHELD_MARKER + ") is gone")

    def test_calibrated_reinjecting_the_ascii_path_class_leaks_the_tail(self):
        """CALIBRATION for the path fix: restore the pre-fix ASCII-only
        regex and the exact reported tail leak returns."""
        old_re = re.compile(r"(?<![A-Za-z0-9_])"
                            r"(?:[A-Za-z]:[\\/]|\\\\|/)"
                            r"[A-Za-z0-9_.~\-][A-Za-z0-9_.~\-/\\]*")
        path = "/Users/m\u00fcller/Kunden/Siemens-deal"
        self.assertEqual(bs.mask_absolute_paths(path), bs.PATH_WITHHELD_MARKER)
        with mock.patch.object(bs, "_ABS_PATH_RE", old_re):
            self.assertIn("ller/Kunden/Siemens-deal",
                          bs.mask_absolute_paths(path),
                          "REINJECTION CHECK: the ASCII-only class must leak "
                          "the tail")
        self.assertEqual(bs.mask_absolute_paths(path), bs.PATH_WITHHELD_MARKER)

    def test_mask_absolute_paths_stays_linear_on_long_input(self):
        """Workstream D asks for a redaction ceiling. A 400k-character worst
        case (one enormous non-ASCII path, then path-dense prose) must stay
        far under a second: catastrophic backtracking would blow past it."""
        for big in ("/Users/" + "\u00fc" * 200000,
                    "/Users/jane/clients/acme-deal notes here " * 10000):
            start = time.time()
            bs.mask_absolute_paths(big)
            elapsed = time.time() - start
            self.assertLess(elapsed, 2.0,
                            "masking %d chars took %.2fs" % (len(big), elapsed))

    def test_export_column_is_the_one_policy_and_covers_unknown_columns(self):
        self.assertEqual(bs.export_column("records", "state", "active"), "active")
        self.assertIn("WITHHELD",
                      bs.export_column("records", "objective", "ordinary prose"))
        self.assertIn("WITHHELD",
                      bs.export_column("a_table_that_does_not_exist", "notes", "x"))
        # Empty and non-string values pass through untouched: nothing to hide.
        self.assertEqual(bs.export_column("records", "objective", ""), "")
        self.assertEqual(bs.export_column("records", "objective", 7), 7)

    def test_mask_absolute_paths_covers_posix_windows_and_unc(self):
        self.assertEqual(bs.mask_absolute_paths("/Users/jane/clients/acme"),
                          bs.PATH_WITHHELD_MARKER)
        self.assertEqual(bs.mask_absolute_paths(r"C:\Users\jane\acme.txt"),
                          bs.PATH_WITHHELD_MARKER)
        self.assertEqual(bs.mask_absolute_paths(r"\\fileserver\clients\acme"),
                          bs.PATH_WITHHELD_MARKER)
        # Relative, project-internal structure is deliberately kept.
        self.assertEqual(bs.mask_absolute_paths("api/pay.py"), "api/pay.py")
        self.assertEqual(bs.mask_absolute_paths("and/or"), "and/or")
        self.assertEqual(bs.mask_absolute_paths(""), "")
        self.assertIsNone(bs.mask_absolute_paths(None))

    # -- LOOP 5: quoted, escaped, and word-adjacent absolute paths -------

    def test_mask_absolute_paths_masks_a_quoted_path_whole_spaces_included(self):
        self.assertEqual(
            bs.mask_absolute_paths('"/Users/j/Dev Work/plan.md"'),
            '"' + bs.PATH_WITHHELD_MARKER + '"')
        self.assertEqual(
            bs.mask_absolute_paths("'/home/user/clients/beijing deal/notes'"),
            "'" + bs.PATH_WITHHELD_MARKER + "'")
        # A quoted ordinary sentence with no path prefix right after the
        # quote is not treated as a path at all.
        self.assertEqual(bs.mask_absolute_paths('"just a sentence"'),
                          '"just a sentence"')

    def test_mask_absolute_paths_masks_an_escaped_space_path_whole(self):
        self.assertEqual(
            bs.mask_absolute_paths("/Users/j/Dev\\ Work/plan.md"),
            bs.PATH_WITHHELD_MARKER)

    def test_mask_absolute_paths_masks_known_roots_glued_to_a_word(self):
        """KNOWN-LIMITS: 'an absolute path immediately preceded by an
        alphanumeric or an underscore is not masked at all'. Closed for the
        six distinctive home-directory root names."""
        self.assertEqual(
            bs.mask_absolute_paths("note/Users/jane/secret and more"),
            "note" + bs.PATH_WITHHELD_MARKER + " and more")
        self.assertEqual(
            bs.mask_absolute_paths("x/home/user/clients/acme"),
            "x" + bs.PATH_WITHHELD_MARKER)

    def test_mask_absolute_paths_two_in_one_field_both_masked(self):
        self.assertEqual(
            bs.mask_absolute_paths("/Users/j/a /Users/k/b"),
            bs.PATH_WITHHELD_MARKER + " " + bs.PATH_WITHHELD_MARKER)

    def test_mask_absolute_paths_url_false_positive_not_worsened(self):
        """Pre-existing, disclosed behaviour (not introduced by LOOP 5): a
        URL's scheme letter still collides with the drive-letter form. This
        test pins that the LOOP 5 changes did not make it WORSE (e.g. by
        dropping the drive lookbehind, which would also start eating the
        scheme itself instead of just the following colon-slash)."""
        masked = bs.mask_absolute_paths("See https://example.com/docs")
        self.assertIn("http", masked)

    def test_calibrated_reverting_known_root_lookbehind_drop_hides_the_glue(self):
        """CALIBRATION: reinstate the plain not-preceded-by-word-char
        lookbehind on the known-root form and the glued-path leak returns."""
        old_re = re.compile(
            r"(?<![A-Za-z0-9_])(?:[A-Za-z]:[\\/]|\\\\|/)"
            + bs._ABS_PATH_BODY + r"*")
        glued = "note/Users/jane/secret"
        self.assertEqual(bs.mask_absolute_paths(glued),
                         "note" + bs.PATH_WITHHELD_MARKER)
        with mock.patch.object(bs, "_ABS_PATH_RE", old_re):
            self.assertIn("Users/jane/secret", bs.mask_absolute_paths(glued),
                          "REINJECTION CHECK: the old lookbehind must leak "
                          "the glued path again")
        self.assertEqual(bs.mask_absolute_paths(glued),
                         "note" + bs.PATH_WITHHELD_MARKER)

    def test_calibrated_reverting_quote_awareness_leaks_the_space_tail(self):
        """CALIBRATION, named explicitly in the LOOP 5 brief: 'path masking
        with spaces'. Revert to a regex with no quoted-path alternative (the
        plain space-stops-the-match behaviour from before this loop), prove
        the quoted space-path canary leaks its tail, then restore and prove
        it is gone."""
        old_re = re.compile(
            r"(?:[A-Za-z]:[\\/]|\\\\|/(?:%s)(?:[\\/]%s*)?)|"
            r"(?<![A-Za-z0-9_])[A-Za-z]:[\\/]%s*|\\\\%s*|"
            r"(?<![A-Za-z0-9_])/[^\s\x00-\x1f\x7f\"'`<>|,;:()\[\]{}/\\]%s*"
            % (bs._ROOT_ALT, bs._ABS_PATH_BODY, bs._ABS_PATH_BODY,
               bs._ABS_PATH_BODY, bs._ABS_PATH_BODY))
        quoted = '"/Users/j/Dev Work/plan.md"'
        self.assertEqual(bs.mask_absolute_paths(quoted),
                         '"' + bs.PATH_WITHHELD_MARKER + '"')
        with mock.patch.object(bs, "_ABS_PATH_RE", old_re):
            reverted = bs.mask_absolute_paths(quoted)
            self.assertIn("Work/plan.md", reverted,
                          "REINJECTION CHECK: without quote-awareness the "
                          "space must cut the mask short again")
        self.assertEqual(bs.mask_absolute_paths(quoted),
                         '"' + bs.PATH_WITHHELD_MARKER + '"')

    def test_cli_dump_default_is_valid_json_and_raw_warns_about_prose(self):
        with tempfile.TemporaryDirectory() as d:
            _run_cli(["init"], d)
            self._seed(d)
            plain = _run_cli(["dump"], d)
            self.assertEqual(plain.returncode, 0, plain.stdout + plain.stderr)
            json.loads(plain.stdout)
            self.assertNotIn(self.PROSE["objective"], plain.stdout + plain.stderr)
            raw = _run_cli(["dump", "--raw"], d)
            self.assertEqual(raw.returncode, 0, raw.stdout + raw.stderr)
            json.loads(raw.stdout)  # the warning must not corrupt the JSON
            self.assertIn(self.PROSE["objective"], raw.stdout)
            self.assertIn("UNREDACTED", raw.stderr)
            self.assertIn("WITHHOLDS", raw.stderr)


class TestLoop11NoFtsTableCanHoldFounderText(unittest.TestCase):
    """LOOP 11 workstream D, last bullet. bm_learning.py documents an FTS5
    index as a FUTURE fast path. An FTS table is a second, unredacted COPY of
    whatever text is indexed, so if one ever lands it must be a deliberate
    decision with its own privacy review, not a quiet schema addition."""

    def test_the_schema_contains_no_fts_table_today(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rows = store.conn.execute(
                    "SELECT name, sql FROM sqlite_master WHERE type='table'").fetchall()
            offenders = [r["name"] for r in rows
                         if "fts" in (r["name"] or "").lower()
                         or "USING fts" in (r["sql"] or "")]
            self.assertEqual(offenders, [],
                              "an FTS table appeared: it is an unredacted second "
                              "copy of the text it indexes, so it needs its own "
                              "export-policy decision before it ships: %s" % offenders)
class TestP17InstructionTextMatchesTheInstalledLayout(unittest.TestCase):
    """P17-fix. P17 put six commands on PATH, and every refusal in this file
    still told the reader to run `python3 tools/bm_store.py ...`. There is no
    tools/ directory in a pipx, uv, or pip install, so the FIRST refusal a
    package-only user ever saw named a file that does not exist. These tests
    pin the resolution rule in both layouts, because nothing else does: no
    test covered instruction text at all before this."""

    def _fake_env(self, d, packaged):
        """A minimal venv shape: <prefix>/bin/{python3,bm-store} and a module
        either inside that prefix (packaged) or outside it (a checkout)."""
        binf = os.path.join(d, "prefix", "bin")
        os.makedirs(binf)
        py = os.path.join(binf, "python3")
        script = os.path.join(binf, "bm-store")
        for p in (py, script):
            with io.open(p, "w") as f:
                f.write("#!/bin/sh\n")
            os.chmod(p, 0o755)
        if packaged:
            site = os.path.join(d, "prefix", "lib", "python3.9", "site-packages")
        else:
            site = os.path.join(d, "checkout", "tools")
        os.makedirs(site)
        mod = os.path.join(site, "bm_store.py")
        with io.open(mod, "w") as f:
            f.write("# placeholder\n")
        return os.path.join(d, "prefix"), py, mod

    def test_a_packaged_install_is_told_the_command_that_exists(self):
        with tempfile.TemporaryDirectory() as d:
            prefix, py, mod = self._fake_env(d, packaged=True)
            with mock.patch.object(sys, "prefix", prefix), \
                    mock.patch.object(sys, "executable", py):
                self.assertEqual("bm-store", bs.invocation("bm-store", mod))

    def test_a_checkout_is_told_its_own_absolute_path(self):
        with tempfile.TemporaryDirectory() as d:
            prefix, py, mod = self._fake_env(d, packaged=False)
            with mock.patch.object(sys, "prefix", prefix), \
                    mock.patch.object(sys, "executable", py):
                # The console script exists on this machine, but it belongs to
                # a DIFFERENT environment than the file being run. Naming it
                # would point the founder at some other install's store code.
                self.assertEqual("python3 %s" % mod,
                                 bs.invocation("bm-store", mod))

    def test_a_path_with_spaces_is_quoted_so_it_can_be_pasted(self):
        with tempfile.TemporaryDirectory() as d:
            target = os.path.join(d, "my project", "bm_store.py")
            os.makedirs(os.path.dirname(target))
            out = bs.invocation("bm-store", target)
            self.assertIn("'%s'" % target, out)

    def test_the_no_root_refusal_names_a_command_that_resolves(self):
        with tempfile.TemporaryDirectory() as d:
            start = os.path.join(d, "nowhere")
            os.makedirs(start)
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("BROTHERMODE_ROOT", None)
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    bs.require_root(start)
            msg = str(ctx.exception)
            self.assertNotIn("python3 tools/bm_store.py", msg)
            self.assertIn(bs.invocation("bm-store", bs.__file__), msg)

    #: bm_fence_hook.py carries the same three hardcoded instructions
    #: (its no-store _FailOpen, its adopt line, and its claim nudge). It is
    #: a hook internal this fix round does not own, so the defect is
    #: recorded in docs/KNOWN-LIMITS.md rather than patched here by a loop
    #: with no mandate to touch it. Removing the name from this set is the
    #: whole fix once a loop owns that file.
    NOT_OWNED_BY_THIS_LOOP = frozenset(["bm_fence_hook.py"])

    def test_no_shipping_message_hardcodes_the_repo_relative_path(self):
        """The sweep, not one site. Every user-facing string in the shipping
        tools is checked, so a tenth site cannot be added the old way."""
        offenders = []
        for fn in sorted(os.listdir(HERE)):
            if not fn.endswith(".py") or fn.startswith("test_"):
                continue
            if fn in self.NOT_OWNED_BY_THIS_LOOP:
                continue
            with io.open(os.path.join(HERE, fn), encoding="utf-8") as f:
                tree = ast.parse(f.read())
            docstrings = set()
            for node in ast.walk(tree):
                if isinstance(node, (ast.Module, ast.FunctionDef,
                                     ast.AsyncFunctionDef, ast.ClassDef)):
                    body = node.body
                    if (body and isinstance(body[0], ast.Expr)
                            and isinstance(body[0].value, ast.Constant)
                            and isinstance(body[0].value.value, str)):
                        docstrings.add(id(body[0].value))
            for node in ast.walk(tree):
                if (isinstance(node, ast.Constant)
                        and isinstance(node.value, str)
                        and id(node) not in docstrings
                        and "python3 tools/bm_" in node.value):
                    offenders.append("%s:%s" % (fn, node.lineno))
        self.assertEqual(
            [], offenders,
            "these runtime strings tell the reader to run a repo-relative "
            "path that does not exist in a packaged install; resolve the "
            "command instead (bm_store.invocation): %s" % offenders)


class TestSchema7Migration(unittest.TestCase):
    """Schema 6 to 7 adds the notes table. Same shape as the schema 4 and 5
    migration suites above, and for the same reason: a healthy older store must
    MIGRATE, every existing row must survive, and an interrupted migration must
    leave the version where it was."""

    def _schema6_store(self, d):
        """A real schema-6 store, built by the real code and then stripped back:
        the fixture cannot drift from a real store, and only the newest layer is
        removed."""
        with bs.Store(d) as store:
            rec = store.claim("payments", "persistent", objective="build payments",
                              files=["api/pay.py"], session_id="sessA")
            store.checkpoint(rec.lifecycle_uuid, rec.version, "wire the webhook")
        path = os.path.join(d, bs.STORE_DIRNAME, bs.STORE_FILENAME)
        conn = sqlite3.connect(path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            for t in bs._TABLES_NOTES:
                conn.execute("DROP TABLE IF EXISTS %s" % t)
            conn.execute("UPDATE meta SET value='6' WHERE key='schema_version'")
            conn.execute("COMMIT")
        finally:
            conn.close()
        return path

    def _snapshot(self, path):
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        try:
            out = {}
            for t in bs._TABLES_V6:
                rows = [dict(r) for r in conn.execute("SELECT * FROM %s" % t)]
                if t == "meta":
                    rows = [r for r in rows if r.get("key") != "schema_version"]
                out[t] = json.dumps(rows, sort_keys=True, default=str)
            return out
        finally:
            conn.close()

    def _tables(self, path):
        conn = sqlite3.connect(path)
        try:
            return {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            conn.close()

    def test_a_schema6_store_migrates_instead_of_being_quarantined(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._schema6_store(d)
            with bs.Store(d) as store:
                self.assertEqual(
                    store.conn.execute(
                        "SELECT value FROM meta WHERE key='schema_version'"
                    ).fetchone()["value"], str(bs.SCHEMA_VERSION))
            self.assertTrue(set(bs._TABLES_NOTES) <= self._tables(path))
            self.assertEqual(
                glob.glob(os.path.join(d, bs.STORE_DIRNAME, "*quarantine*")), [],
                "a healthy schema-6 store must MIGRATE, never be quarantined")

    def test_migration_preserves_every_schema6_row(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._schema6_store(d)
            before = self._snapshot(path)
            with bs.Store(d):
                pass
            self.assertEqual(before, self._snapshot(path))

    def test_migration_invents_no_note_out_of_existing_rows(self):
        """A transition note, a checkpoint blocker and a rejected candidate all
        look a little like an alert. Importing one would put words in an
        author's mouth and could manufacture a CRITICAL alert that refuses an
        approval nobody was warned about."""
        with tempfile.TemporaryDirectory() as d:
            self._schema6_store(d)
            with bs.Store(d) as store:
                self.assertEqual(store.list_notes(), [])

    def test_migration_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._schema6_store(d)
            with bs.Store(d):
                pass
            first = self._snapshot(path)
            with bs.Store(d):
                pass
            self.assertEqual(first, self._snapshot(path))

    def test_calibrated_interrupted_migration_rolls_back_completely(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._schema6_store(d)
            original = bs._MIGRATIONS[6]

            def _fail_half_way(conn):
                conn.execute(bs._NOTES_DDL_STATEMENTS[0])
                raise RuntimeError("simulated interruption mid-migration")

            bs._MIGRATIONS[6] = _fail_half_way
            try:
                with self.assertRaises(RuntimeError):
                    bs.Store(d)
            finally:
                bs._MIGRATIONS[6] = original
            conn = sqlite3.connect(path)
            try:
                v = conn.execute(
                    "SELECT value FROM meta WHERE key='schema_version'").fetchone()[0]
            finally:
                conn.close()
            self.assertEqual(v, "6",
                             "an interrupted migration must not move the version")
            for t in bs._TABLES_NOTES:
                self.assertNotIn(t, self._tables(path))
            with bs.Store(d):
                pass
            self.assertTrue(set(bs._TABLES_NOTES) <= self._tables(path))

    def test_notes_ddl_split_matches_the_table_and_index_lists(self):
        self.assertEqual(len(bs._NOTES_DDL_STATEMENTS), len(bs._TABLES_NOTES))
        self.assertEqual(len(bs._NOTES_INDEX_STATEMENTS), 2)

    def test_a_note_body_is_withheld_in_dump_but_its_shape_is_not(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                store.add_note(kind="alert", severity="critical",
                               body="the key AKIAIOSFODNN7EXAMPLE is in here",
                               author="Dana", author_kind="human",
                               anchor_type="file", anchor_key="api/pay.py")
                data = store.dump()
            rows = data["notes"]
            self.assertEqual(len(rows), 1)
            self.assertNotIn("AKIAIOSFODNN7EXAMPLE", json.dumps(rows),
                             "dump leaked a secret out of a note body")
            self.assertNotIn("Dana", json.dumps(rows),
                             "dump leaked an author name, which is a person")
            self.assertEqual(rows[0]["kind"], "alert")
            self.assertEqual(rows[0]["severity"], "critical",
                             "the shape of a note must stay readable in a dump, "
                             "or a dump cannot show that an alert exists")


class TestAnchoredNotes(unittest.TestCase):
    """The note itself: what it refuses at the door, and what it never does."""

    def test_an_alert_needs_a_severity(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.add_note(kind="alert", body="something is wrong",
                                   author="Dana", author_kind="human",
                                   anchor_type="file", anchor_key="api/pay.py")
                self.assertEqual(ctx.exception.reason, "alert-needs-severity")

    def test_a_note_needs_an_author_and_a_body(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.add_note(kind="insight", body="x", author="  ",
                                   author_kind="human", anchor_type="file",
                                   anchor_key="api/pay.py")
                self.assertEqual(ctx.exception.reason, "no-note-author")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.add_note(kind="insight", body="   ", author="Dana",
                                   author_kind="human", anchor_type="file",
                                   anchor_key="api/pay.py")
                self.assertEqual(ctx.exception.reason, "empty-note")

    def test_a_file_anchor_is_canonical_from_any_spelling(self):
        """The anchor and a work record's claimed path must be the same string,
        or blocking_alerts compares two spellings of one file and finds
        nothing."""
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "api"))
            with bs.Store(d) as store:
                n = store.add_note(kind="risk", body="watch this",
                                   author="Dana", author_kind="human",
                                   anchor_type="file",
                                   anchor_key="api/../api/pay.py")
                self.assertEqual(n["anchor_key"], "api/pay.py")

    def test_an_anchor_outside_the_project_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.add_note(kind="risk", body="watch this",
                                   author="Dana", author_kind="human",
                                   anchor_type="file",
                                   anchor_key="../../etc/passwd")
                self.assertEqual(ctx.exception.reason, "path-escape")

    def test_resolving_keeps_the_row_and_records_what_resolved_it(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                n = store.add_note(kind="alert", severity="critical",
                                   body="the retry path double charges",
                                   author="Dana", author_kind="human",
                                   anchor_type="file", anchor_key="api/pay.py")
                # LOOP 2, 2026-07-30: this note is a CRITICAL alert, so
                # resolving it now needs a state-change receipt of its own,
                # exactly as approving or editing a rule does.
                text = "fixed in the idempotency key change"
                rec = store.mint_state_change_receipt(
                    "resolve-note", n["note_uuid"], founder_response="yes",
                    content_parts=(text,))
                done = store.resolve_note(n["note_uuid"][:8], text,
                                          receipt=rec["token"])
                self.assertIsNotNone(done["resolved_at"])
                self.assertIn("idempotency", done["resolution"])
                self.assertEqual(len(store.list_notes()), 1,
                                 "resolving must not delete the row")

    def test_there_is_no_way_to_delete_a_note_and_no_standalone_override(self):
        """Both absences are load bearing. A delete would destroy human text; a
        standalone override would be a second door into the same room with no
        receipt on it, and any importer could walk through it and then approve
        cleanly."""
        self.assertFalse(hasattr(bs.Store, "delete_note"))
        self.assertFalse(hasattr(bs.Store, "override_note"))
        with io.open(os.path.join(HERE, "bm_store.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertNotIn("DELETE FROM notes", src)


class TestCriticalAlertsRefuseAnApproval(unittest.TestCase):
    """Founder decision 7 of the 2026-07-30 spec: an unresolved critical alert
    anchored to the gate, or to any file the gate would change, REFUSES the
    approval, and the founder may override with a recorded reason.

    Every test is written so that removing the guard makes it fail. The
    calibration was run by hand as well: deleting the alerts clause from
    _approval_guards turns the first two tests red with 'OwnershipRefused not
    raised' and leaves the rest green, which is the intended failure."""

    def _seed(self, store):
        rec = store.claim("payments", "persistent", objective="build payments",
                          files=["api/pay.py"], session_id="sessA")
        cand = store.capture_learning_candidate(
            "manual", trigger="when touching payments",
            action="always run the payment tests",
            because="we shipped a refund bug", scope_type="project",
            scope_key="demo", record_uuid=rec.lifecycle_uuid)
        return rec, cand

    def _alert(self, store, **kw):
        kw.setdefault("kind", "alert")
        kw.setdefault("severity", "critical")
        kw.setdefault("body", "the retry path double charges")
        kw.setdefault("author", "Dana, backend")
        kw.setdefault("author_kind", "human")
        kw.setdefault("anchor_type", "file")
        kw.setdefault("anchor_key", "api/pay.py")
        return store.add_note(**kw)

    def _mint(self, store, cand, **kw):
        return store.mint_approval_receipt(
            cand["candidate_uuid"], founder_response="yes, do that",
            trigger="when touching payments",
            action="always run the payment tests", scope_type="project",
            scope_key="demo", **kw)

    def test_an_alert_on_a_changed_file_refuses_the_mint_and_the_approval(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "api"))
            with bs.Store(d) as store:
                _rec, cand = self._seed(store)
                note = self._alert(store)
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    self._mint(store, cand)
                self._assert_named(ctx.exception, note)
                self.assertEqual(store.list_learning_rules(), [],
                                 "a refused mint must create no rule")

    def test_an_alert_raised_after_the_question_refuses_the_approval_itself(self):
        """The case a mint-only guard would miss, and the realistic one: the
        founder answers, THEN a reviewer writes a critical alert, THEN somebody
        spends the receipt. The receipt is still valid and still fingerprints
        clean, so only a guard on the approval path itself stops this."""
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "api"))
            with bs.Store(d) as store:
                _rec, cand = self._seed(store)
                rec = self._mint(store, cand)
                note = self._alert(store)
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.approve_learning_candidate(
                        cand["candidate_uuid"], founder_ref="he said yes",
                        receipt=rec["token"], trigger="when touching payments",
                        action="always run the payment tests",
                        scope_type="project", scope_key="demo")
                self._assert_named(ctx.exception, note)
                self.assertEqual(store.list_learning_rules(), [],
                                 "a refused approval must create no rule")
                self.assertIsNone(
                    store.get_approval_receipt(rec["receipt_uuid"])["consumed_at"],
                    "a refused approval must not spend the receipt")

    def _assert_named(self, exc, note):
        self.assertEqual(exc.reason, "unresolved-critical-alert")
        self.assertIn("Dana, backend", str(exc),
                      "the refusal must name the author")
        self.assertIn("api/pay.py", str(exc),
                      "the refusal must name the anchor")
        self.assertIn(note["note_uuid"][:8], str(exc),
                      "the refusal must name the alert")

    def test_an_alert_anchored_to_the_candidate_itself_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                _rec, cand = self._seed(store)
                self._alert(store, anchor_type="candidate",
                            anchor_key=cand["candidate_uuid"][:8],
                            body="the scope is not settled")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    self._mint(store, cand)
                self.assertEqual(ctx.exception.reason, "unresolved-critical-alert")

    def test_a_resolved_alert_does_not_refuse(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "api"))
            with bs.Store(d) as store:
                _rec, cand = self._seed(store)
                note = self._alert(store)
                # LOOP 2, 2026-07-30: resolving a CRITICAL alert now needs a
                # state-change receipt of its own (see
                # TestLoop2StateChangeReceipts for the hole this closes:
                # before this, resolving one unblocked an approval with no
                # human answer anywhere).
                text = "fixed by the retry rework"
                state_rec = store.mint_state_change_receipt(
                    "resolve-note", note["note_uuid"], founder_response="yes",
                    content_parts=(text,))
                store.resolve_note(note["note_uuid"], text,
                                   receipt=state_rec["token"])
                rec = self._mint(store, cand)
                rule = store.approve_learning_candidate(
                    cand["candidate_uuid"], founder_ref="he said yes",
                    receipt=rec["token"], trigger="when touching payments",
                    action="always run the payment tests", scope_type="project",
                    scope_key="demo")
                self.assertEqual(rule["state"], "approved")

    def test_a_non_critical_alert_and_a_critical_other_kind_do_not_refuse(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "api"))
            with bs.Store(d) as store:
                _rec, cand = self._seed(store)
                self._alert(store, severity="warning")
                self._alert(store, kind="risk", severity="critical")
                rec = self._mint(store, cand)
                self.assertTrue(rec["token"],
                                "only an unresolved CRITICAL ALERT has teeth")
                self.assertEqual(rec["blocking_alerts"], [])

    def test_an_alert_on_an_unrelated_file_does_not_refuse(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "web"))
            with bs.Store(d) as store:
                _rec, cand = self._seed(store)
                self._alert(store, anchor_key="web/checkout.js")
                self.assertTrue(self._mint(store, cand)["token"])

    def test_the_override_records_a_reason_and_the_alert_stays_visible(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "api"))
            with bs.Store(d) as store:
                _rec, cand = self._seed(store)
                note = self._alert(store)
                rec = self._mint(
                    store, cand,
                    alerts_override="Dana's concern is the retry path, this "
                                    "rule is about tests")
                self.assertTrue(rec["override_alerts"])
                self.assertEqual(len(rec["blocking_alerts"]), 1)
                rule = store.approve_learning_candidate(
                    cand["candidate_uuid"], founder_ref="he said ship it",
                    receipt=rec["token"], trigger="when touching payments",
                    action="always run the payment tests", scope_type="project",
                    scope_key="demo",
                    alerts_override="Dana's concern is the retry path, this "
                                    "rule is about tests")
                self.assertEqual(rule["state"], "approved")
                after = store.get_note(note["note_uuid"])
                self.assertIsNotNone(after["overridden_at"])
                self.assertIn("retry path", after["override_reason"])
                self.assertIn("ship it", after["override_by"])
                self.assertIsNone(
                    after["resolved_at"],
                    "an override is not an answer: the alert stays unresolved")
                self.assertEqual(
                    len(store.list_notes()), 1,
                    "an overridden alert stays in the store, never deleted")
                excerpts = [e["excerpt"] for e
                            in store.list_learning_evidence(rule["rule_uuid"])]
                self.assertTrue(
                    any("critical alert override" in e for e in excerpts),
                    "the override must also be evidence against the rule: %s"
                    % excerpts)

    def test_a_receipt_minted_clean_cannot_be_spent_with_an_override(self):
        """The override is in the approval fingerprint for the same reason the
        atomicity and conflict overrides are: the founder's answer has to have
        been given about the override too."""
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "api"))
            with bs.Store(d) as store:
                _rec, cand = self._seed(store)
                rec = self._mint(store, cand)
                self._alert(store)
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.approve_learning_candidate(
                        cand["candidate_uuid"], founder_ref="he said yes",
                        receipt=rec["token"], trigger="when touching payments",
                        action="always run the payment tests",
                        scope_type="project", scope_key="demo",
                        alerts_override="I decided to proceed")
                self.assertEqual(ctx.exception.reason, "receipt-stale-candidate")
                self.assertEqual(store.list_learning_rules(), [])

    def test_the_change_set_is_the_record_claims_plus_the_artifact_scope(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "api"))
            with bs.Store(d) as store:
                rec = store.claim("payments", "persistent", objective="pay",
                                  files=["api/pay.py", "api/refund.py"],
                                  session_id="sessA")
                cand = store.capture_learning_candidate(
                    "manual", trigger="t", action="a", scope_type="artifact",
                    scope_key="api/webhook.py", record_uuid=rec.lifecycle_uuid)
                self.assertEqual(
                    sorted(store.gate_change_set(cand)),
                    ["api/pay.py", "api/refund.py", "api/webhook.py"])

    def test_a_glob_claim_still_catches_an_alert_on_a_file_inside_it(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "api"))
            with bs.Store(d) as store:
                rec = store.claim("payments", "persistent", objective="pay",
                                  files=["api/*.py"], session_id="sessA")
                cand = store.capture_learning_candidate(
                    "manual", trigger="when touching payments",
                    action="always run the payment tests", scope_type="project",
                    scope_key="demo", record_uuid=rec.lifecycle_uuid)
                self._alert(store, anchor_key="api/pay.py")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    self._mint(store, cand)
                self.assertEqual(ctx.exception.reason, "unresolved-critical-alert")

    def test_capture_accepts_a_record_prefix_rather_than_dropping_the_link(self):
        """The link is load bearing: gate_change_set reads the record's claims,
        so a silently broken link would mean an alert on a changed file quietly
        failing to refuse."""
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "api"))
            with bs.Store(d) as store:
                rec = store.claim("payments", "persistent", objective="pay",
                                  files=["api/pay.py"], session_id="sessA")
                cand = store.capture_learning_candidate(
                    "manual", trigger="t", action="a",
                    record_uuid=rec.lifecycle_uuid[:8], scope_type="project",
                    scope_key="demo")
                self.assertEqual(cand["source_record_uuid"], rec.lifecycle_uuid)
                self.assertEqual(store.gate_change_set(cand), ["api/pay.py"])
                with self.assertRaises(bs.OwnershipRefused):
                    store.capture_learning_candidate(
                        "manual", trigger="t", action="a",
                        record_uuid="deadbeef", scope_type="project",
                        scope_key="demo")

    # -- FIX ROUND, phase A. Three ways the teeth came out ----------------

    def _second_gate(self, store, rec):
        """A SECOND candidate on the same work record, so both gates would change
        the file the alert is anchored to. Different rule text, or the duplicate
        guard refuses before the alert guard is ever consulted."""
        return store.capture_learning_candidate(
            "manual", trigger="when editing the refund path",
            action="ask for a second review first",
            because="the last refund change was reverted", scope_type="project",
            scope_key="demo", record_uuid=rec.lifecycle_uuid)

    def test_an_override_at_one_gate_does_not_clear_the_alert_at_the_next(self):
        """THE DEFECT THIS FIXES. The override is written on the NOTE ROW, and
        blocking_alerts used to skip any overridden row, so one recorded founder
        override at one gate permanently disarmed a still-unresolved critical
        alert for every other gate in the project: the next approval saw no
        alert, printed no stakes line about it, asked nobody, and closed clean
        while `notes --open --severity critical` still listed it unanswered."""
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "api"))
            with bs.Store(d) as store:
                rec, cand = self._seed(store)
                other = self._second_gate(store, rec)
                note = self._alert(store)
                reason = "Dana's concern is the retry path, this rule is tests"
                token = self._mint(store, cand, alerts_override=reason)["token"]
                store.approve_learning_candidate(
                    cand["candidate_uuid"], founder_ref="he said ship it",
                    receipt=token, trigger="when touching payments",
                    action="always run the payment tests", scope_type="project",
                    scope_key="demo", alerts_override=reason)
                self.assertIsNotNone(
                    store.get_note(note["note_uuid"])["overridden_at"],
                    "the first override must still be recorded on the row")
                still = store.blocking_alerts(other)
                self.assertEqual(
                    [a["note_uuid"] for a in still], [note["note_uuid"]],
                    "an alert overridden at another gate is still unresolved, so "
                    "it must still stand in front of this one")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.mint_approval_receipt(
                        other["candidate_uuid"], founder_response="yes",
                        trigger="when editing the refund path",
                        action="ask for a second review first",
                        scope_type="project", scope_key="demo")
                self.assertEqual(ctx.exception.reason, "unresolved-critical-alert")
                self.assertIn("overridden at an earlier gate", str(ctx.exception),
                              "the refusal must explain why an alert the founder "
                              "already overrode is back")

    def test_calibrated_the_old_row_level_skip_disarms_the_second_gate(self):
        """The reinjection that proves the test above is load bearing: put the
        overridden_at skip back and the second gate mints clean."""
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "api"))
            with bs.Store(d) as store:
                rec, cand = self._seed(store)
                other = self._second_gate(store, rec)
                note = self._alert(store)
                reason = "the retry path is not what this rule is about"
                token = self._mint(store, cand, alerts_override=reason)["token"]
                store.approve_learning_candidate(
                    cand["candidate_uuid"], founder_ref="he said ship it",
                    receipt=token, trigger="when touching payments",
                    action="always run the payment tests", scope_type="project",
                    scope_key="demo", alerts_override=reason)
                original = bs.Store.blocking_alerts

                def _row_level_skip(self, candidate):
                    return [a for a in original(self, candidate)
                            if a["overridden_at"] is None]

                bs.Store.blocking_alerts = _row_level_skip
                try:
                    self.assertEqual(
                        store.blocking_alerts(other), [],
                        "the reinjected defect did NOT disarm the alert, so the "
                        "test above proves nothing")
                    minted = store.mint_approval_receipt(
                        other["candidate_uuid"], founder_response="yes",
                        trigger="when editing the refund path",
                        action="ask for a second review first",
                        scope_type="project", scope_key="demo")
                    self.assertTrue(minted["token"])
                finally:
                    bs.Store.blocking_alerts = original
                self.assertEqual(
                    [a["note_uuid"] for a in store.blocking_alerts(other)],
                    [note["note_uuid"]], "restored, the alert blocks again")

    def test_an_anchor_that_names_nothing_is_refused_at_the_door(self):
        """An alert anchored to a candidate id that names no candidate used to be
        stored open, reported as 'this REFUSES an approval anchored here', and
        refuse nothing forever: the author believed a gate was held and nothing
        was held."""
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "api"))
            with bs.Store(d) as store:
                self._seed(store)
                for atype, key in (("candidate", "deadbeefdeadbeef"),
                                   ("rule", "deadbeefdeadbeef"),
                                   ("record", "deadbeefdeadbeef")):
                    with self.assertRaises(bs.OwnershipRefused) as ctx:
                        self._alert(store, anchor_type=atype, anchor_key=key)
                    self.assertEqual(ctx.exception.reason, "anchor-not-found",
                                     "%s anchor was accepted" % atype)
                    self.assertIn("could never refuse anything", str(ctx.exception))
                self.assertEqual(store.list_notes(), [],
                                 "nothing may be written for a refused anchor")

    def test_a_typed_prefix_is_resolved_and_blankets_nobody(self):
        """The other half of the same defect: blocking_alerts matched with
        cuuid.startswith(anchor_key), so a one-character anchor refused every
        gate in the project. The prefix is now resolved at the door, exactly as
        every other uuid prefix in this project is resolved: one match, or a
        named refusal that says how many it matched."""
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "api"))
            with bs.Store(d) as store:
                rec, cand = self._seed(store)
                other = self._second_gate(store, rec)
                note = self._alert(store, anchor_type="candidate",
                                   anchor_key=cand["candidate_uuid"][:8],
                                   body="the scope is not settled")
                self.assertEqual(note["anchor_key"], cand["candidate_uuid"],
                                 "the anchor must be stored resolved, not as typed")
                self.assertEqual([a["note_uuid"] for a in store.blocking_alerts(cand)],
                                 [note["note_uuid"]])
                self.assertEqual(
                    store.blocking_alerts(other), [],
                    "one candidate's alert must not blanket another gate")
                # The blanket attempt itself: one character. Whichever way it
                # lands, it may never end up standing in front of a gate nobody
                # wrote about. Both branches are asserted because the uuids are
                # random, so which one happens is not this test's business.
                one_char = cand["candidate_uuid"][:1]
                try:
                    wide = self._alert(store, anchor_type="candidate",
                                       anchor_key=one_char, body="blanket")
                except bs.OwnershipRefused as e:
                    self.assertEqual(e.reason, "ambiguous-anchor",
                                     "a prefix naming several candidates must be "
                                     "refused, not spread across them")
                else:
                    self.assertEqual(wide["anchor_key"], cand["candidate_uuid"])
                    self.assertEqual(
                        store.blocking_alerts(other), [],
                        "a one-character anchor blanketed an unrelated gate")

    def test_an_alert_on_the_work_record_refuses_that_records_gate(self):
        """Spec 4.3 says an alert anchored to THE GATE refuses it. The gate's
        identity in the store is the work record the candidate came from, so a
        record anchor has teeth too; before this it silently had none."""
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "api"))
            with bs.Store(d) as store:
                rec, cand = self._seed(store)
                note = self._alert(store, anchor_type="record",
                                   anchor_key=rec.lifecycle_uuid[:8],
                                   body="this whole record is on hold")
                self.assertEqual(note["anchor_key"], rec.lifecycle_uuid)
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    self._mint(store, cand)
                self.assertEqual(ctx.exception.reason, "unresolved-critical-alert")
                self.assertIn("work record %s" % rec.lifecycle_uuid[:8],
                              str(ctx.exception))


class TestSchema8Migration(unittest.TestCase):
    """Schema 7 to 8: one additive column on notes (anchor_line_hash).

    Phase C of the 2026-07-30 documentation and gate-pack spec, section 6, and
    I8: additive, atomic, fixtures built from a real store, and a known older
    version migrates rather than quarantines."""

    def _schema7_store(self, d):
        """A real store with a real note, stripped back to the schema-7 shape.

        The notes table is rebuilt from bm_store's OWN phase A DDL text rather
        than from a copy typed here, so the fixture cannot drift from what a
        schema-7 store actually looked like, and the note's every other field is
        carried across so the migration is tested against a POPULATED table
        (an empty one would pass an ALTER TABLE that lost every row)."""
        with bs.Store(d) as store:
            rec = store.claim("payments", "persistent", objective="build payments",
                              files=["api/pay.py"], session_id="sessA")
            store.add_note(kind="risk", severity="warning",
                           body="the refund path has no idempotency key",
                           author="Dana", author_kind="human",
                           anchor_type="record", anchor_key=rec.lifecycle_uuid)
        path = os.path.join(d, bs.STORE_DIRNAME, bs.STORE_FILENAME)
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        try:
            keep = [dict(r) for r in conn.execute("SELECT * FROM notes")]
            self.assertTrue(keep, "the fixture must carry a real note")
            cols = [c for c in keep[0] if c != "anchor_line_hash"]
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("DROP TABLE notes")
            for statement in bs._NOTES_DDL_STATEMENTS:
                conn.execute(statement)
            for statement in bs._NOTES_INDEX_STATEMENTS:
                conn.execute(statement)
            for row in keep:
                conn.execute(
                    "INSERT INTO notes (%s) VALUES (%s)"
                    % (",".join(cols), ",".join("?" * len(cols))),
                    tuple(row[c] for c in cols))
            conn.execute("UPDATE meta SET value='7' WHERE key='schema_version'")
            conn.execute("COMMIT")
        finally:
            conn.close()
        return path

    def _columns(self, path, table):
        conn = sqlite3.connect(path)
        try:
            return {r[1] for r in conn.execute("PRAGMA table_info(%s)" % table)}
        finally:
            conn.close()

    def test_the_fixture_really_is_missing_the_column(self):
        """Calibration for every test below: if the fixture already had the
        column, all of them would pass without the migration existing."""
        with tempfile.TemporaryDirectory() as d:
            path = self._schema7_store(d)
            self.assertNotIn("anchor_line_hash", self._columns(path, "notes"))

    def test_a_schema7_store_migrates_instead_of_being_quarantined(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._schema7_store(d)
            with bs.Store(d) as store:
                self.assertEqual(
                    store.conn.execute(
                        "SELECT value FROM meta WHERE key='schema_version'"
                    ).fetchone()["value"], str(bs.SCHEMA_VERSION))
            self.assertIn("anchor_line_hash", self._columns(path, "notes"))
            self.assertEqual(
                glob.glob(os.path.join(d, bs.STORE_DIRNAME, "*quarantine*")), [],
                "a healthy schema-7 store must MIGRATE, never be quarantined")

    def test_the_migration_keeps_every_note_and_every_field(self):
        with tempfile.TemporaryDirectory() as d:
            self._schema7_store(d)
            with bs.Store(d) as store:
                notes = store.list_notes()
            self.assertEqual(len(notes), 1)
            self.assertEqual(notes[0]["body"],
                             "the refund path has no idempotency key")
            self.assertEqual(notes[0]["author"], "Dana")
            self.assertEqual(notes[0]["kind"], "risk")
            self.assertEqual(
                notes[0]["anchor_line_hash"], "",
                "an existing note must arrive with NO fingerprint. A backfilled "
                "one would claim today's line was the anchored line and destroy "
                "the only fact that could prove the line moved.")

    def test_the_migration_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            self._schema7_store(d)
            with bs.Store(d):
                pass
            with bs.Store(d) as store:
                self.assertEqual(len(store.list_notes()), 1)

    def test_a_fresh_store_has_the_column(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d):
                pass
            path = os.path.join(d, bs.STORE_DIRNAME, bs.STORE_FILENAME)
            self.assertIn("anchor_line_hash", self._columns(path, "notes"))


class TestAnchoredLinesAreReportedNeverDropped(unittest.TestCase):
    """Spec section 6: a note anchored to a line that has since moved is
    REPORTED, never silently dropped, and nothing a generator writes deletes a
    note."""

    SOURCE = ("def pay():\n    return 1\n\n\ndef refund():\n    return 2\n")

    def _project(self, d, source=None):
        os.makedirs(os.path.join(d, "api"))
        self._write(d, source or self.SOURCE)
        return bs.Store(d)

    def _write(self, d, source):
        with io.open(os.path.join(d, "api", "pay.py"), "w",
                     encoding="utf-8") as fh:
            fh.write(source)

    def _note(self, store, line=5, kind="risk"):
        return store.add_note(kind=kind, severity="warning",
                              body="the refund path has no idempotency key",
                              author="Dana", author_kind="human",
                              anchor_type="file", anchor_key="api/pay.py",
                              anchor_line=line)

    def test_an_out_of_range_line_is_refused_at_the_door(self):
        """Reproduced against a real store before this guard existed: `note
        --anchor file:api/pay.py --line 99` on a six line file was accepted,
        listed and rendered, and no command ever said the line did not exist."""
        with tempfile.TemporaryDirectory() as d:
            store = self._project(d)
            try:
                # SELF DIAGNOSING, after one unreproduced failure of this test
                # during the phase C round (nine reruns and forty runs of this
                # class did not repeat it). The refusal below can only happen if
                # the store could READ the file: an unreadable file is
                # deliberately not refused, it is stored with no fingerprint and
                # reported as unverifiable. Asserting readability first means a
                # future failure says which of the two broke instead of leaving
                # a bare "OwnershipRefused not raised" to guess at.
                self.assertEqual(len(store._anchor_lines("api/pay.py")), 6,
                                 "the store must be able to read the fixture "
                                 "file for the range check to run at all")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    self._note(store, line=99)
                self.assertEqual(ctx.exception.reason,
                                 "anchor-line-out-of-range")
                self.assertIn("6 line(s)", str(ctx.exception))
                self.assertEqual(store.list_notes(), [],
                                 "a refused note must not be stored")
            finally:
                store.close()

    def test_a_whole_file_anchor_needs_no_line_and_is_not_reported(self):
        with tempfile.TemporaryDirectory() as d:
            store = self._project(d)
            try:
                store.add_note(kind="insight", body="this module is the money path",
                               author="Dana", author_kind="human",
                               anchor_type="file", anchor_key="api/pay.py")
                self.assertEqual(store.note_anchor_reports(), [],
                                 "a note with no line has no line to have moved")
            finally:
                store.close()

    def test_an_unmoved_line_resolves(self):
        with tempfile.TemporaryDirectory() as d:
            store = self._project(d)
            try:
                self._note(store)
                found = store.note_anchor_reports()
                self.assertEqual(len(found), 1)
                self.assertEqual(found[0]["state"], "resolves")
                self.assertEqual(found[0]["now_line"], 5)
                self.assertFalse(found[0]["problem"])
            finally:
                store.close()

    def test_a_moved_line_is_reported_with_where_it_went(self):
        with tempfile.TemporaryDirectory() as d:
            store = self._project(d)
            try:
                note = self._note(store)
                self._write(d, '"""money"""\nimport json\n\n\n' + self.SOURCE)
                found = store.note_anchor_reports()
                self.assertEqual(len(found), 1)
                self.assertEqual(found[0]["state"], "moved")
                self.assertEqual(found[0]["line"], 5)
                self.assertEqual(found[0]["now_line"], 9)
                self.assertTrue(found[0]["problem"])
                self.assertIn("moved from line 5 to line 9", found[0]["why"])
                self.assertEqual(
                    [n["note_uuid"] for n in store.list_notes()],
                    [note["note_uuid"]],
                    "reporting a moved anchor must not touch the note")
            finally:
                store.close()

    def test_a_deleted_line_is_reported_gone_and_the_note_survives(self):
        with tempfile.TemporaryDirectory() as d:
            store = self._project(d)
            try:
                self._note(store)
                self._write(d, "def pay():\n    return 1\n")
                found = store.note_anchor_reports()
                self.assertEqual(found[0]["state"], "gone")
                self.assertIsNone(found[0]["now_line"])
                self.assertEqual(len(store.list_notes()), 1,
                                 "nothing deletes a note")
            finally:
                store.close()

    def test_an_unreadable_file_is_reported_not_refused(self):
        with tempfile.TemporaryDirectory() as d:
            store = self._project(d)
            try:
                self._note(store)
                os.remove(os.path.join(d, "api", "pay.py"))
                found = store.note_anchor_reports()
                self.assertEqual(found[0]["state"], "file-missing")
                self.assertTrue(found[0]["problem"])
            finally:
                store.close()

    def test_a_note_written_against_an_unreadable_file_is_kept(self):
        """The other direction: a note about a file this process cannot open is
        still a note worth keeping, stored with no fingerprint and reported as
        unverifiable rather than refused."""
        with tempfile.TemporaryDirectory() as d:
            store = self._project(d)
            try:
                note = store.add_note(
                    kind="todo", body="this file does not exist yet",
                    author="Dana", author_kind="human", anchor_type="file",
                    anchor_key="api/not_written_yet.py", anchor_line=12)
                self.assertEqual(note["anchor_line_hash"], "")
                self.assertEqual(store.note_anchor_reports()[0]["state"],
                                 "file-missing")
            finally:
                store.close()

    def test_reindentation_is_not_reported_as_a_move(self):
        with tempfile.TemporaryDirectory() as d:
            store = self._project(d)
            try:
                self._note(store, line=6)
                self._write(d, "def pay():\n    return 1\n\n\n"
                               "def refund():\n        return 2\n")
                self.assertEqual(store.note_anchor_reports()[0]["state"],
                                 "resolves")
            finally:
                store.close()

    def test_a_resolved_note_stays_resolved_and_stays_in_the_report(self):
        with tempfile.TemporaryDirectory() as d:
            store = self._project(d)
            try:
                note = self._note(store)
                store.resolve_note(note["note_uuid"][:8], "the key landed")
                self._write(d, "def pay():\n    return 1\n")
                found = store.note_anchor_reports()
                self.assertEqual(len(found), 1)
                self.assertTrue(found[0]["resolved"])
                self.assertEqual(found[0]["state"], "gone")
                self.assertEqual(store.list_notes()[0]["resolution"],
                                 "the key landed")
            finally:
                store.close()

    def test_problems_sort_in_front_of_resolving_anchors(self):
        with tempfile.TemporaryDirectory() as d:
            store = self._project(d)
            try:
                self._note(store, line=1, kind="insight")
                self._note(store, line=5)
                self._write(d, '"""money"""\n\n\n' + self.SOURCE)
                states = [f["state"] for f in store.note_anchor_reports()]
                self.assertEqual(states, ["moved", "moved"])
            finally:
                store.close()

    def test_the_fingerprint_is_withheld_from_an_ordinary_export(self):
        """I9. The fingerprint is named *_hash so export_column withholds it BY
        SHAPE, and the body a person typed is withheld by default-deny."""
        self.assertTrue(
            bs.export_column("notes", "anchor_line_hash", "a" * 64)
            .startswith("[WITHHELD:"))
        self.assertTrue(
            bs.export_column("notes", "body", "the refund path double charges")
            .startswith("[WITHHELD:"))


class TestLoop2CaptureUsageRefusal(unittest.TestCase):
    """LOOP 0 SWEEP, item D6, ORCHESTRATOR RULING (2026-07-30): `bm_learn.py
    capture` with no arguments stored an EMPTY candidate instead of printing
    usage, while the same CLI already refuses an unknown flag. Fixed at the
    CLI layer (cmd_capture), not in bm_store.capture_learning_candidate,
    which keeps its roughly thirty legitimate call shapes untouched."""

    def _run(self, root, args):
        e = dict(os.environ, BROTHERMODE_ROOT=root)
        return subprocess.run([sys.executable, os.path.join(HERE, "bm_learn.py")]
                              + args, cwd=root, env=e, capture_output=True, text=True)

    def _init(self, root):
        e = dict(os.environ, BROTHERMODE_ROOT=root)
        r = subprocess.run([sys.executable, os.path.join(HERE, "bm_store.py"), "init"],
                           cwd=root, env=e, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_capture_with_no_arguments_prints_usage_and_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as root:
            self._init(root)
            r = self._run(root, ["capture"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("usage: capture", r.stderr)
            # REPRODUCTION CHECK: the old defect stored an empty candidate at
            # exit 0. This asserts the actual store state, not just the exit
            # code, so a refusal that still wrote something would be caught.
            listed = self._run(root, ["candidates", "--json"])
            self.assertEqual(listed.returncode, 0, listed.stderr)
            self.assertEqual(json.loads(listed.stdout), [],
                             "a refused capture must create no candidate")

    def test_capture_with_only_whitespace_flags_also_refuses(self):
        """Unknown flag refusal already exists; this must match it: a
        trigger/action/because of only whitespace is the same as absent."""
        with tempfile.TemporaryDirectory() as root:
            self._init(root)
            r = self._run(root, ["capture", "--trigger", "   ", "--action", "",
                                "--because", ""])
            self.assertEqual(r.returncode, 2)
            self.assertIn("usage: capture", r.stderr)

    def test_capture_with_a_real_field_still_succeeds(self):
        with tempfile.TemporaryDirectory() as root:
            self._init(root)
            r = self._run(root, ["capture", "--scope", "global", "--trigger",
                                "pushing to main", "--action", "never force push"])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("captured", r.stdout)

    def test_calibrated_reinjecting_the_all_empty_capture_stores_an_empty_candidate(self):
        """CALIBRATION. Call the store's own capture_learning_candidate
        directly with everything empty, exactly as the CLI used to let
        through: the exact reported defect reappears (an empty candidate,
        stored, at exit 0-equivalent). This proves the guard added above is a
        CLI-layer refusal, not a change to the shared primitive: the store
        method itself still accepts an all-empty call, on purpose, because
        its own thirty call shapes are not this loop's to re-litigate."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                cand = store.capture_learning_candidate(
                    "manual", trigger="", action="", because="",
                    scope_type="global")
                self.assertEqual(cand["proposed_trigger"], "")
                self.assertEqual(cand["proposed_action"], "")
                self.assertEqual(len(store.list_learning_candidates(status=None)), 1,
                                 "REPRODUCTION: the store itself still accepts this; "
                                 "the refusal added by this loop lives in cmd_capture")


class TestSchema9Migration(unittest.TestCase):
    """Schema 8 to 9 (LOOP 2, 2026-07-30): the generic state-change receipt
    table. Same discipline as TestPostAuditLoop3Schema3Migration: the fixture
    is a REAL store reverted to schema 8, not hand-written DDL, so it cannot
    drift from the schema anyone actually has."""

    def _schema8_store(self, d):
        with bs.Store(d) as store:
            store.claim("alpha", "persistent", "keep me", ["src/a.py"])
            c = store.capture_learning_candidate(
                "manual", trigger="writing an executive update",
                action="state customer impact first",
                because="leaders need the business state first",
                scope_type="global", scope_key="")
            _approved(store, c["candidate_uuid"],
                     founder_ref="approved before this loop's table existed")
        path = os.path.join(d, bs.STORE_DIRNAME, bs.STORE_FILENAME)
        conn = sqlite3.connect(path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            for t in bs._TABLES_STATE_CHANGE_RECEIPTS:
                conn.execute("DROP TABLE IF EXISTS %s" % t)
            conn.execute("UPDATE meta SET value='8' WHERE key='schema_version'")
            conn.execute("COMMIT")
        finally:
            conn.close()
        return path

    def _snapshot(self, path):
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        try:
            out = {}
            for t in bs._TABLES_V8:
                rows = [dict(r) for r in conn.execute("SELECT * FROM %s" % t)]
                if t == "meta":
                    rows = [r for r in rows if r.get("key") != "schema_version"]
                out[t] = json.dumps(rows, sort_keys=True, default=str)
            return out
        finally:
            conn.close()

    def _tables(self, path):
        conn = sqlite3.connect(path)
        try:
            return {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            conn.close()

    def test_a_schema8_store_migrates_instead_of_being_quarantined(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._schema8_store(d)
            with bs.Store(d) as store:
                self.assertEqual(
                    store.conn.execute(
                        "SELECT value FROM meta WHERE key='schema_version'"
                    ).fetchone()["value"], str(bs.SCHEMA_VERSION))
            self.assertTrue(set(bs._TABLES_STATE_CHANGE_RECEIPTS) <= self._tables(path))
            self.assertEqual(
                glob.glob(os.path.join(d, bs.STORE_DIRNAME, "*quarantine*")), [],
                "a healthy schema-8 store must MIGRATE, never be quarantined")

    def test_migration_preserves_every_schema8_row(self):
        """Including the rule approved before this table existed. Rewriting
        it to look receipt-backed would be the dishonest half of this
        change, exactly as _migrate_2_to_3 states for its own predecessor
        rules."""
        with tempfile.TemporaryDirectory() as d:
            path = self._schema8_store(d)
            before = self._snapshot(path)
            with bs.Store(d):
                pass
            self.assertEqual(before, self._snapshot(path))

    def test_migration_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._schema8_store(d)
            with bs.Store(d):
                pass
            first = self._snapshot(path)
            with bs.Store(d):
                pass
            self.assertEqual(first, self._snapshot(path))

    def test_calibrated_interrupted_migration_rolls_back_completely(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._schema8_store(d)
            original = bs._MIGRATIONS[8]

            def _fail_half_way(conn):
                conn.execute(bs._STATE_CHANGE_RECEIPT_DDL_STATEMENTS[0])
                raise RuntimeError("simulated interruption mid-migration")

            bs._MIGRATIONS[8] = _fail_half_way
            try:
                with self.assertRaises(RuntimeError):
                    bs.Store(d)
            finally:
                bs._MIGRATIONS[8] = original
            conn = sqlite3.connect(path)
            try:
                v = conn.execute(
                    "SELECT value FROM meta WHERE key='schema_version'").fetchone()[0]
            finally:
                conn.close()
            self.assertEqual(v, "8", "an interrupted migration must not move the version")
            for t in bs._TABLES_STATE_CHANGE_RECEIPTS:
                self.assertNotIn(t, self._tables(path))
            with bs.Store(d):
                pass
            self.assertTrue(set(bs._TABLES_STATE_CHANGE_RECEIPTS) <= self._tables(path))

    def test_state_change_receipt_ddl_split_matches_the_table_and_index_lists(self):
        self.assertEqual(len(bs._STATE_CHANGE_RECEIPT_DDL_STATEMENTS),
                         len(bs._TABLES_STATE_CHANGE_RECEIPTS))
        self.assertEqual(len(bs._STATE_CHANGE_RECEIPT_INDEX_STATEMENTS), 1)

    def test_a_fresh_store_is_born_at_schema9_with_the_table_present(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self.assertEqual(
                    store.conn.execute(
                        "SELECT value FROM meta WHERE key='schema_version'"
                    ).fetchone()["value"], str(bs.SCHEMA_VERSION))
            self.assertTrue(
                set(bs._TABLES_STATE_CHANGE_RECEIPTS) <= self._tables(
                    os.path.join(d, bs.STORE_DIRNAME, bs.STORE_FILENAME)))


class TestLoop2StateChangeReceipts(unittest.TestCase):
    """LOOP 2, 2026-07-30. Five commands can alter the live rule set without
    going through approve_learning_candidate or edit_learning_rule: supersede,
    resolve-conflict, deprecate, forget, and resolving a critical alert.
    Before this loop only create and edit were receipt-gated. The most
    serious of the five holes, reproduced first below, is resolve-conflict
    standing an approved GATE rule down with no receipt at all.

    ONE generic lane (learning_state_change_receipts, mint_state_change_receipt,
    _require_state_change_receipt, _consume_state_change_receipt) serves all
    five call sites, not five bespoke checks: this project's own failure
    ledger names a cross-cutting concern implemented per call site as the
    root cause behind four separate bugs."""

    def _cap(self, store, **kw):
        kw.setdefault("source_type", "manual")
        kw.setdefault("trigger", "writing an executive update")
        kw.setdefault("action", "state customer impact before technical detail")
        kw.setdefault("because", "leaders need the business state first")
        kw.setdefault("scope_type", "global")
        kw.setdefault("scope_key", "")
        return store.capture_learning_candidate(**kw)

    def _rule(self, store, gate=False, **kw):
        founder_ref = kw.pop("founder_ref", "f")
        conflict_override = kw.pop("conflict_override", "")
        c = self._cap(store, **kw)
        return _approved(store, c["candidate_uuid"], founder_ref=founder_ref,
                         severity="gate" if gate else "soft",
                         conflict_override=conflict_override)

    def _critical_alert(self, store, **kw):
        kw.setdefault("kind", bs.BLOCKING_NOTE_KIND)
        kw.setdefault("severity", bs.BLOCKING_NOTE_SEVERITY)
        kw.setdefault("body", "the retry path double charges")
        kw.setdefault("author", "Dana, backend")
        kw.setdefault("author_kind", "human")
        kw.setdefault("anchor_type", "candidate")
        return store.add_note(**kw)

    def _reopen_rule(self, store, rule_uuid, state):
        """Force a rule back to an earlier state WITHOUT going through the
        API, exactly as TestPostAuditLoop3ApprovalReceipts._repending does
        for candidates: needed only so the reuse test can reach the receipt
        check at all. The ordinary state-transition guard would otherwise
        refuse the SECOND call before the receipt check ever ran, because the
        rule has already left the state this move requires."""
        store.conn.execute("BEGIN IMMEDIATE")
        store.conn.execute("UPDATE learning_rules SET state=? WHERE rule_uuid=?",
                           (state, rule_uuid))
        store.conn.execute("COMMIT")

    def _reopen_note(self, store, note_uuid):
        """Same technique, for the resolve-note reuse test: force resolved_at
        back to NULL without touching the receipt's own consumed_at."""
        store.conn.execute("BEGIN IMMEDIATE")
        store.conn.execute(
            "UPDATE notes SET resolved_at=NULL WHERE note_uuid=?", (note_uuid,))
        store.conn.execute("COMMIT")

    # -- missing receipt, one per command -----------------------------------

    def test_supersede_without_receipt_refuses_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                old = self._rule(store, trigger="t1", action="a1")
                new = self._rule(store, trigger="t2", action="a2")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.change_learning_rule_state(
                        old["rule_uuid"], "superseded", reason="r",
                        successor_prefix=new["rule_uuid"])
                self.assertEqual(ctx.exception.reason, "no-state-change-receipt")
                self.assertEqual(
                    store.get_learning_rule(old["rule_uuid"])["state"], "approved")

    def test_deprecate_without_receipt_refuses_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = self._rule(store)
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.change_learning_rule_state(rule["rule_uuid"], "deprecated",
                                                     reason="r")
                self.assertEqual(ctx.exception.reason, "no-state-change-receipt")
                self.assertEqual(
                    store.get_learning_rule(rule["rule_uuid"])["state"], "approved")

    def test_forget_without_receipt_refuses_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = self._rule(store)
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.change_learning_rule_state(rule["rule_uuid"], "forgotten",
                                                     reason="r")
                self.assertEqual(ctx.exception.reason, "no-state-change-receipt")
                self.assertEqual(
                    store.get_learning_rule(rule["rule_uuid"])["state"], "approved")

    def test_resolve_conflict_against_a_gate_rule_without_receipt_refuses(self):
        """THE HEADLINE CASE. Reproduced before this loop: resolve-conflict
        could stand an approved GATE rule down with no human answer anywhere,
        the most serious of the five holes this loop closed."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                gate = self._rule(store, trigger="push to main",
                                  action="never force push", gate=True)
                other = self._rule(store, trigger="push to main",
                                   action="always force push",
                                   founder_ref="f2", conflict_override="accepted for the test")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.resolve_learning_conflict(
                        gate["rule_uuid"], other["rule_uuid"], "contradicted",
                        reason="testing")
                self.assertEqual(ctx.exception.reason, "no-state-change-receipt")
                self.assertEqual(
                    store.get_learning_rule(gate["rule_uuid"])["state"], "approved",
                    "REPRODUCTION CHECK: a GATE rule must not stand down with "
                    "no receipt at all")

    def test_resolve_note_on_a_critical_alert_without_receipt_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                cand = self._cap(store)
                note = self._critical_alert(store, anchor_key=cand["candidate_uuid"])
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.resolve_note(note["note_uuid"], "fixed it")
                self.assertEqual(ctx.exception.reason, "no-state-change-receipt")
                self.assertIsNone(
                    store.get_note(note["note_uuid"])["resolved_at"],
                    "REPRODUCTION CHECK: a critical alert must not resolve "
                    "with no receipt at all")

    # -- the direct-API bypass this loop actually defends against -----------

    def test_the_store_api_cannot_skip_the_gate_by_omitting_receipt_kind(self):
        """The attack this loop defends against is shell access as the same
        OS user, calling bm_store.py directly rather than through
        bm_learn.py. A caller that simply leaves receipt_kind at its default
        must NOT get an ungated move: the gate is keyed off `target`, not off
        whether the caller happened to pass a kind."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = self._rule(store)
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.change_learning_rule_state(rule["rule_uuid"], "deprecated",
                                                     reason="bypass attempt")
                self.assertEqual(ctx.exception.reason, "no-state-change-receipt")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.change_learning_rule_state(rule["rule_uuid"], "forgotten",
                                                     reason="bypass attempt")
                self.assertEqual(ctx.exception.reason, "no-state-change-receipt")
                self.assertEqual(
                    store.get_learning_rule(rule["rule_uuid"])["state"], "approved")

    # -- successes, one per command ------------------------------------------

    def test_supersede_with_a_valid_receipt_succeeds(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                old = self._rule(store, trigger="t1", action="a1", gate=True)
                new = self._rule(store, trigger="t2", action="a2", founder_ref="f2")
                out = _state_changed(store, old["rule_uuid"], "superseded",
                                     reason="replaced", successor_prefix=new["rule_uuid"])
                self.assertEqual(out["state"], "superseded")
                self.assertEqual(out["superseded_by"], new["rule_uuid"])

    def test_deprecate_with_a_valid_receipt_succeeds(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = self._rule(store)
                out = _state_changed(store, rule["rule_uuid"], "deprecated", reason="r")
                self.assertEqual(out["state"], "deprecated")

    def test_forget_with_a_valid_receipt_succeeds(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = self._rule(store)
                out = _state_changed(store, rule["rule_uuid"], "forgotten", reason="r")
                self.assertEqual(out["state"], "forgotten")

    def test_resolve_conflict_contradicted_with_a_valid_receipt_succeeds(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                gate = self._rule(store, trigger="push to main",
                                  action="never force push", gate=True)
                other = self._rule(store, trigger="push to main",
                                   action="always force push", founder_ref="f2",
                                   conflict_override="accepted for the test")
                out = _conflict_resolved(store, gate["rule_uuid"], other["rule_uuid"],
                                         "contradicted", reason="testing")
                self.assertEqual(out["state"], "contradicted")

    def test_resolve_conflict_superseded_branch_with_a_valid_receipt_succeeds(self):
        """resolve-conflict's 'superseded' branch delegates to
        change_learning_rule_state, and must gate under its OWN kind
        ('resolve-conflict'), not 'supersede': a plain supersede receipt must
        not spend here (see the cross-kind test below)."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                old = self._rule(store, trigger="t3", action="a3")
                new = self._rule(store, trigger="t4", action="a4", founder_ref="f2")
                out = _conflict_resolved(store, old["rule_uuid"], new["rule_uuid"],
                                         "superseded", reason="rs")
                self.assertEqual(out["state"], "superseded")

    def test_resolve_note_critical_alert_with_a_valid_receipt_succeeds(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                cand = self._cap(store)
                note = self._critical_alert(store, anchor_key=cand["candidate_uuid"])
                text = "fixed it"
                rec = store.mint_state_change_receipt(
                    "resolve-note", note["note_uuid"], founder_response="yes",
                    content_parts=(text,))
                out = store.resolve_note(note["note_uuid"], text, receipt=rec["token"])
                self.assertIsNotNone(out["resolved_at"])

    # -- ordinary and non-critical notes still resolve with NO receipt -------

    def test_resolving_an_ordinary_note_needs_no_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                cand = self._cap(store)
                note = store.add_note(kind="insight", body="worth remembering",
                                      author="Dana", author_kind="human",
                                      anchor_type="candidate",
                                      anchor_key=cand["candidate_uuid"])
                out = store.resolve_note(note["note_uuid"], "noted")
                self.assertIsNotNone(out["resolved_at"])

    def test_resolving_a_non_critical_alert_needs_no_receipt(self):
        """Only kind='alert' AND severity='critical' together are a blocking
        alert (blocking_alerts filters on both). A warning-severity alert has
        no teeth and needs no receipt to resolve."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                cand = self._cap(store)
                note = self._critical_alert(store, severity="warning",
                                            anchor_key=cand["candidate_uuid"])
                out = store.resolve_note(note["note_uuid"], "downgraded, fixed")
                self.assertIsNotNone(out["resolved_at"])

    # -- reused, expired, wrong target, stale content ------------------------

    def test_a_spent_state_change_receipt_refuses_the_second_time(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = self._rule(store)
                rec = store.mint_state_change_receipt(
                    "deprecate", rule["rule_uuid"], founder_response="yes",
                    content_parts=("deprecated", "", "r"))
                store.change_learning_rule_state(
                    rule["rule_uuid"], "deprecated", reason="r",
                    receipt=rec["token"], receipt_kind="deprecate")
                self._reopen_rule(store, rule["rule_uuid"], "approved")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.change_learning_rule_state(
                        rule["rule_uuid"], "deprecated", reason="r",
                        receipt=rec["token"], receipt_kind="deprecate")
                self.assertEqual(ctx.exception.reason, "receipt-already-used")

    def test_a_spent_resolve_note_receipt_refuses_the_second_time(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                cand = self._cap(store)
                note = self._critical_alert(store, anchor_key=cand["candidate_uuid"])
                rec = store.mint_state_change_receipt(
                    "resolve-note", note["note_uuid"], founder_response="yes",
                    content_parts=("fixed",))
                store.resolve_note(note["note_uuid"], "fixed", receipt=rec["token"])
                self._reopen_note(store, note["note_uuid"])
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.resolve_note(note["note_uuid"], "fixed", receipt=rec["token"])
                self.assertEqual(ctx.exception.reason, "receipt-already-used")

    def test_an_expired_state_change_receipt_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = self._rule(store)
                rec = store.mint_state_change_receipt(
                    "forget", rule["rule_uuid"], founder_response="yes",
                    content_parts=("forgotten", "", "r"))
                store.conn.execute("BEGIN IMMEDIATE")
                store.conn.execute(
                    "UPDATE learning_state_change_receipts SET "
                    "expires_at='2000-01-01T00:00:00Z' WHERE receipt_uuid=?",
                    (rec["receipt_uuid"],))
                store.conn.execute("COMMIT")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.change_learning_rule_state(
                        rule["rule_uuid"], "forgotten", reason="r",
                        receipt=rec["token"], receipt_kind="forget")
                self.assertEqual(ctx.exception.reason, "receipt-expired")

    def test_a_receipt_for_another_rule_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                a = self._rule(store, trigger="t1", action="a1")
                b = self._rule(store, trigger="t2", action="a2", founder_ref="f2")
                rec = store.mint_state_change_receipt(
                    "deprecate", a["rule_uuid"], founder_response="yes",
                    content_parts=("deprecated", "", "r"))
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.change_learning_rule_state(
                        b["rule_uuid"], "deprecated", reason="r",
                        receipt=rec["token"], receipt_kind="deprecate")
                self.assertEqual(ctx.exception.reason, "receipt-wrong-target")
                self.assertEqual(
                    store.get_learning_rule(b["rule_uuid"])["state"], "approved")

    def test_a_receipt_is_stale_once_the_reason_changes(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = self._rule(store)
                rec = store.mint_state_change_receipt(
                    "deprecate", rule["rule_uuid"], founder_response="yes",
                    content_parts=("deprecated", "", "the original reason"))
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.change_learning_rule_state(
                        rule["rule_uuid"], "deprecated", reason="a different reason",
                        receipt=rec["token"], receipt_kind="deprecate")
                self.assertEqual(ctx.exception.reason, "receipt-stale-target")

    def test_a_resolve_conflict_receipt_is_stale_if_how_changes(self):
        """`how` is part of the content a resolve-conflict receipt binds to,
        exactly as the override flags are part of an approval receipt's
        fingerprint: a receipt minted for 'contradicted' cannot be redirected
        to 'deprecated' just because both are legal target states."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                a = self._rule(store, trigger="t1", action="a1")
                b = self._rule(store, trigger="t2", action="a2", founder_ref="f2")
                other_uuid = b["rule_uuid"]
                rec = store.mint_state_change_receipt(
                    "resolve-conflict", a["rule_uuid"], founder_response="yes",
                    content_parts=("contradicted", other_uuid, "r"))
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.resolve_learning_conflict(
                        a["rule_uuid"], b["rule_uuid"], "deprecated", reason="r",
                        receipt=rec["token"])
                self.assertEqual(ctx.exception.reason, "receipt-stale-target")

    # -- wrong kind, both directions, within the new lane --------------------

    def test_a_deprecate_receipt_cannot_spend_as_a_forget_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = self._rule(store)
                rec = store.mint_state_change_receipt(
                    "deprecate", rule["rule_uuid"], founder_response="yes",
                    content_parts=("deprecated", "", "r"))
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.change_learning_rule_state(
                        rule["rule_uuid"], "forgotten", reason="r",
                        receipt=rec["token"], receipt_kind="forget")
                self.assertEqual(ctx.exception.reason, "receipt-wrong-kind")

    def test_a_forget_receipt_cannot_spend_as_a_deprecate_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = self._rule(store)
                rec = store.mint_state_change_receipt(
                    "forget", rule["rule_uuid"], founder_response="yes",
                    content_parts=("forgotten", "", "r"))
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.change_learning_rule_state(
                        rule["rule_uuid"], "deprecated", reason="r",
                        receipt=rec["token"], receipt_kind="deprecate")
                self.assertEqual(ctx.exception.reason, "receipt-wrong-kind")

    def test_a_plain_supersede_receipt_cannot_spend_via_resolve_conflict(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                a = self._rule(store, trigger="t1", action="a1")
                b = self._rule(store, trigger="t2", action="a2", founder_ref="f2")
                rec = store.mint_state_change_receipt(
                    "supersede", a["rule_uuid"], founder_response="yes",
                    content_parts=("superseded", b["rule_uuid"], "r"))
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.resolve_learning_conflict(
                        a["rule_uuid"], b["rule_uuid"], "superseded", reason="r",
                        receipt=rec["token"])
                self.assertEqual(ctx.exception.reason, "receipt-wrong-kind")

    # -- cross-table: never interchangeable with approval or edit receipts --

    def test_a_state_change_receipt_cannot_spend_as_an_approval_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = self._rule(store)
                rec = store.mint_state_change_receipt(
                    "deprecate", rule["rule_uuid"], founder_response="yes",
                    content_parts=("deprecated", "", "r"))
                c2 = self._cap(store, trigger="t2", action="a2")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.approve_learning_candidate(
                        c2["candidate_uuid"], founder_ref="f", receipt=rec["token"])
                self.assertEqual(ctx.exception.reason, "bad-approval-receipt")

    def test_an_approval_receipt_cannot_spend_as_a_state_change_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                c = self._cap(store)
                rec = store.mint_approval_receipt(c["candidate_uuid"],
                                                  founder_response="yes")
                rule = self._rule(store, trigger="t2", action="a2", founder_ref="f2")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.change_learning_rule_state(
                        rule["rule_uuid"], "deprecated", reason="r",
                        receipt=rec["token"], receipt_kind="deprecate")
                self.assertEqual(ctx.exception.reason, "bad-state-change-receipt")

    # -- secrecy: read the bytes on disk, not the display path ---------------

    def test_the_state_change_token_is_never_stored_returned_again_or_dumped(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = self._rule(store)
                rec = store.mint_state_change_receipt(
                    "deprecate", rule["rule_uuid"],
                    founder_response="the founder's literal answer, in a test",
                    content_parts=("deprecated", "", "r"))
                token = rec["token"]
                self.assertNotIn("nonce_hash", rec)
                for blob in (json.dumps(store.dump(), default=str),
                             json.dumps(store.dump(raw=True), default=str)):
                    self.assertNotIn(token, blob,
                                     "the token reached a display surface")
                self.assertNotIn(
                    "the founder's literal answer, in a test",
                    json.dumps(store.dump(raw=True), default=str),
                    "the founder's literal answer is hashed, never stored")
                dumped_row = store.dump()["learning_state_change_receipts"][0]
                for secret_col in ("nonce_hash", "content_fingerprint",
                                   "founder_response_hash"):
                    self.assertTrue(
                        dumped_row[secret_col].startswith("[WITHHELD:"),
                        "%s leaked in an ordinary export" % secret_col)
            path = os.path.join(d, bs.STORE_DIRNAME, bs.STORE_FILENAME)
            with io.open(path, "rb") as f:
                raw_bytes = f.read()
            self.assertNotIn(token.encode("ascii"), raw_bytes,
                             "the token is in the database file")
            self.assertNotIn(b"the founder's literal answer, in a test", raw_bytes,
                             "the founder's literal answer is in the database file")

    # -- calibration: the loop's headline case -------------------------------

    def test_calibrated_resolve_conflict_gate_reproduction(self):
        """CALIBRATION for the loop's headline case. Patch away the two
        functions resolve_learning_conflict's gate depends on (simulating the
        world before this loop, where they did not exist) and the exact
        reported hole reopens: an approved GATE rule stands down against no
        receipt at all. Restore, and the SAME attempt refuses again. A green
        test that was never proven red first is not evidence (this file's own
        standing rule)."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                loser = self._rule(store, trigger="push to main",
                                   action="never force push", gate=True)
                other = self._rule(store, trigger="push to main",
                                   action="always force push", founder_ref="f2",
                                   conflict_override="accepted for the test")
                with mock.patch.object(
                        bs.Store, "_require_state_change_receipt",
                        lambda self, *a, **k: None), \
                     mock.patch.object(
                        bs.Store, "_consume_state_change_receipt",
                        lambda self, *a, **k: None):
                    out = store.resolve_learning_conflict(
                        loser["rule_uuid"], other["rule_uuid"], "contradicted",
                        reason="reproducing the hole", receipt="")
                self.assertEqual(
                    out["state"], "contradicted",
                    "REPRODUCTION: a GATE rule stood down with NO receipt at "
                    "all while the gate was patched away")
                # protection restored: the identical attempt on a fresh pair
                # of rules now refuses.
                loser2 = self._rule(store, trigger="deleting a remote branch",
                                    action="never delete the remote branch",
                                    gate=True, founder_ref="f3")
                other2 = self._rule(store, trigger="deleting a remote branch",
                                    action="always delete the remote branch",
                                    founder_ref="f4",
                                    conflict_override="accepted for the test")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.resolve_learning_conflict(
                        loser2["rule_uuid"], other2["rule_uuid"], "contradicted",
                        reason="protection restored", receipt="")
                self.assertEqual(ctx.exception.reason, "no-state-change-receipt")


class TestLoop2RuleAlteringCommandEnumeration(unittest.TestCase):
    """LOOP 2, 2026-07-30: THE MECHANICAL STOP.

    Five commands altered the live rule set with no receipt in front of them
    (supersede, resolve-conflict, deprecate, forget, resolve-note on a
    critical alert). This enumerates bm_learn's OWN command table --
    mechanically, from bl.COMMANDS, never a list retyped by hand here -- and
    asserts every single command is either proven receipt-gated below or
    carries an explicit, reasoned allowlist entry. A sixth rule-altering
    command added next year, with no gate and no allowlist entry, fails
    test_every_command_is_classified BY NAME until someone classifies it."""

    # command -> the OwnershipRefused reason its own store method raises with
    # no receipt at all. 'resolve-note' is proven separately in
    # test_resolve_note_is_gated_only_for_a_critical_alert, because its gate
    # is conditional on the note's own severity, not a bare "always refuses".
    GATED = {
        "approve": "no-approval-receipt",
        "supersede": "no-state-change-receipt",
        "resolve-conflict": "no-state-change-receipt",
        "deprecate": "no-state-change-receipt",
        "forget": "no-state-change-receipt",
        "resolve-note": None,
    }

    # command -> one-line reason it does not alter the live, injected rule
    # set and therefore needs no receipt at all. Every reason names the file
    # and, where useful, the line this was verified at.
    NOT_RULE_ALTERING = {
        "capture": "stores a raw observation as a PENDING candidate "
                   "(bm_store.capture_learning_candidate); inert until approved",
        "note": "adds a note (bm_store.add_note); notes are not injectable rule text",
        "notes": "read only (bm_store.list_notes)",
        "index-status": "read only (bm_store.learning_index_status)",
        "rebuild-index": "rebuilds the retrieval index, not rule text "
                         "(bm_store.rebuild_learning_index)",
        "outcome": "records external evidence as a pending candidate "
                  "(bm_store.capture_outcome_candidate), not a rule change",
        "inbox": "imports pending candidates (bm_store.import_correction_inbox); "
                "inert until approved",
        "metrics": "read only (bm_store.learning_capture_metrics)",
        "candidates": "read only (bm_store.list_learning_candidates)",
        "show-candidate": "read only (bm_store.get_learning_candidate)",
        "grant-approval": "mints an approval receipt; does not itself alter a rule",
        "grant-state-receipt": "mints a state-change receipt (this loop's own "
                              "mint command); does not itself alter a rule",
        "reject": "marks a candidate rejected (bm_store.reject_learning_candidate); "
                 "never touches learning_rules",
        "rules": "read only (bm_store.list_learning_rules)",
        "lookup": "read only retrieval, writes nothing ever (bm_learn.py:26)",
        "apply": "retrieves and records an application "
                "(bm_store.record_learning_applications); does not alter rule text",
        "relevant": "deprecated alias of apply/lookup (bm_learn.py cmd_relevant)",
        "applications": "read only (bm_store.list_learning_applications)",
        "disposition": "grades an application (bm_store.set_application_disposition); "
                      "does not alter rule text",
        "promote": "LOOP 4: moves a provisional WORK RECORD's own ledger flag "
                  "(bm_store.promote_provisional_record sets "
                  "provisional_records.promoted_at); touches no learning_rules "
                  "row at all",
        "cancel": "LOOP 4: moves a provisional WORK RECORD's own lifecycle "
                 "(bm_store.cancel_provisional_record transitions the record "
                 "to 'complete' and sets provisional_records.cancelled_at); "
                 "touches no learning_rules row at all",
        "classify": "classifies applications (bm_store.classify_learning_applications); "
                   "does not alter rule text",
        "should-retrieve": "read only",
        "why": "read only (bm_store.get_learning_rule plus evidence and versions)",
        "conflicts": "read only (bm_store.learning_conflicts)",
        "link": "records a non-supersedes edge (bm_store.link_learning_rules); "
               "explicitly refuses relation='supersedes' at the door "
               "(bm_store.py link_learning_rules), so it cannot silence a rule",
        "merge": "folds a duplicate candidate in as evidence only "
                "(bm_learn.py:1246, bm_store.merge_learning_candidate); does not "
                "alter any injectable rule's text",
        "confirm": "an evidence-graded lifecycle promotion "
                  "(bm_store.change_learning_rule_state target='confirmed'/'settled') "
                  "with its own no-supporting-evidence guard; does not alter text, "
                  "severity, or supersession",
        "rework": "records external evidence as a graded candidate "
                 "(bm_store.record_outcome_event), not a rule change",
        "escaped-defect": "records external evidence as a graded candidate "
                         "(bm_store.record_outcome_event), not a rule change",
        "repeat-check": "read only unless --record, which adds EVIDENCE "
                       "(bm_store.add_learning_evidence), not rule text",
        "loop-failures": "read only (bm_store.learning_loop_failures)",
        "rule-outcomes": "read only (bm_store.learning_rule_outcomes)",
        "verify": "read only diagnostic (bm_store.learning_verify)",
    }

    def _assert_every_command_classified(self, commands):
        classified = set(self.GATED) | set(self.NOT_RULE_ALTERING)
        unclassified = set(commands) - classified
        self.assertEqual(
            unclassified, set(),
            "these bm_learn commands are neither proven receipt-gated nor "
            "explicitly allowlisted as not rule-altering: %s. A sixth "
            "rule-altering command must be classified (gated, with a proven "
            "refusal reason, or allowlisted with a one-line reason) before "
            "it can ship." % sorted(unclassified))

    def test_every_command_is_classified(self):
        self._assert_every_command_classified(bl.COMMANDS)
        # The allowlist itself must not silently drift from bm_learn.py by
        # naming a command that no longer exists.
        classified = set(self.GATED) | set(self.NOT_RULE_ALTERING)
        stale = classified - set(bl.COMMANDS)
        self.assertEqual(stale, set(),
                         "classified name(s) that are not real bm_learn "
                         "commands: %s" % sorted(stale))

    def test_calibrated_enumeration_catches_an_unclassified_command(self):
        """CALIBRATION for the mechanical stop itself. A command that is
        neither proven gated nor allowlisted must fail the check BY NAME:
        add one to a COPY of the real table and confirm it fails, then
        confirm the real table (with no such gap) passes clean."""
        fake_commands = dict(bl.COMMANDS)
        fake_commands["revoke-everything"] = lambda argv: 0
        with self.assertRaises(AssertionError) as ctx:
            self._assert_every_command_classified(fake_commands)
        self.assertIn("revoke-everything", str(ctx.exception))
        # protection restored: the real table has no such gap.
        self._assert_every_command_classified(bl.COMMANDS)

    # -- a light probe per GATED entry, proving the classification true ------

    def _cap(self, store, **kw):
        kw.setdefault("source_type", "manual")
        kw.setdefault("trigger", "writing an executive update")
        kw.setdefault("action", "state customer impact before technical detail")
        kw.setdefault("because", "leaders need the business state first")
        kw.setdefault("scope_type", "global")
        kw.setdefault("scope_key", "")
        return store.capture_learning_candidate(**kw)

    def _rule(self, store, **kw):
        founder_ref = kw.pop("founder_ref", "f")
        c = self._cap(store, **kw)
        return _approved(store, c["candidate_uuid"], founder_ref=founder_ref)

    def test_approve_is_gated(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                c = self._cap(store)
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.approve_learning_candidate(
                        c["candidate_uuid"], founder_ref="f", receipt="")
                self.assertEqual(ctx.exception.reason, self.GATED["approve"])

    def test_supersede_is_gated(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                old = self._rule(store, trigger="t1", action="a1")
                new = self._rule(store, trigger="t2", action="a2", founder_ref="f2")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.change_learning_rule_state(
                        old["rule_uuid"], "superseded", successor_prefix=new["rule_uuid"])
                self.assertEqual(ctx.exception.reason, self.GATED["supersede"])

    def test_deprecate_is_gated(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = self._rule(store)
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.change_learning_rule_state(rule["rule_uuid"], "deprecated")
                self.assertEqual(ctx.exception.reason, self.GATED["deprecate"])

    def test_forget_is_gated(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = self._rule(store)
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.change_learning_rule_state(rule["rule_uuid"], "forgotten")
                self.assertEqual(ctx.exception.reason, self.GATED["forget"])

    def test_resolve_conflict_is_gated(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                a = self._rule(store, trigger="t1", action="a1")
                b = self._rule(store, trigger="t2", action="a2", founder_ref="f2")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.resolve_learning_conflict(
                        a["rule_uuid"], b["rule_uuid"], "deprecated", reason="r")
                self.assertEqual(ctx.exception.reason, self.GATED["resolve-conflict"])

    def test_resolve_note_is_gated_only_for_a_critical_alert(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                cand = self._cap(store)
                critical = store.add_note(
                    kind=bs.BLOCKING_NOTE_KIND, severity=bs.BLOCKING_NOTE_SEVERITY,
                    body="the retry path double charges", author="Dana",
                    author_kind="human", anchor_type="candidate",
                    anchor_key=cand["candidate_uuid"])
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.resolve_note(critical["note_uuid"], "fixed")
                self.assertEqual(ctx.exception.reason, "no-state-change-receipt")
                ordinary = store.add_note(
                    kind="insight", body="worth remembering", author="Dana",
                    author_kind="human", anchor_type="candidate",
                    anchor_key=cand["candidate_uuid"])
                out = store.resolve_note(ordinary["note_uuid"], "noted")
                self.assertIsNotNone(out["resolved_at"],
                                     "an ordinary note must not need a receipt")

    def test_merge_is_correctly_allowlisted_not_gated(self):
        """The brief's own example: merge folds a candidate in as evidence
        only. Proven here, not assumed: a merge call with no receipt anywhere
        in scope must succeed and must not touch any rule's text."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = self._rule(store)
                dup = self._cap(store, raw_text="told you this before",
                                trigger="writing an executive update",
                                action="state customer impact before technical detail",
                                session_id="s-99")
                out = store.merge_learning_candidate(dup["candidate_uuid"],
                                                     rule["rule_uuid"],
                                                     reason="said twice")
                self.assertEqual(out["rule_uuid"], rule["rule_uuid"])
                self.assertEqual(len(store.list_learning_rules()), 1,
                                 "a merge must not create or alter a rule")


class TestLoop2CliWiring(unittest.TestCase):
    """The store-level gate is only as good as the CLI that fronts it (LOOP
    2, 2026-07-30). Row 11 of the plan's test matrix is explicitly CLI-level:
    exit code AND the reason text on stderr, because a gate that only the
    Python API respects is not a gate Fable's shell access respects.

    Driven through the real binaries via subprocess, the same pattern
    test_bm.py's own CLI tests use, because the exit code and stderr text ARE
    the deliverable here: a script has to be able to gate on both."""

    def _run(self, root, args):
        e = dict(os.environ, BROTHERMODE_ROOT=root)
        return subprocess.run([sys.executable, os.path.join(HERE, "bm_learn.py")]
                              + args, cwd=root, env=e, capture_output=True, text=True)

    def _init(self, root):
        e = dict(os.environ, BROTHERMODE_ROOT=root)
        r = subprocess.run([sys.executable, os.path.join(HERE, "bm_store.py"), "init"],
                           cwd=root, env=e, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def _approve(self, root, trigger, action, because="because", gate=False):
        cap = self._run(root, ["capture", "--scope", "global", "--trigger", trigger,
                              "--action", action, "--because", because,
                              "--source", "manual", "--json"])
        self.assertEqual(cap.returncode, 0, cap.stderr)
        cid = json.loads(cap.stdout)["candidate_uuid"]
        g = self._run(root, ["grant-approval", cid, "--answer", "yes, do it"]
                      + (["--gate"] if gate else []) + ["--json"])
        self.assertEqual(g.returncode, 0, g.stderr)
        token = json.loads(g.stdout)["token"]
        a = self._run(root, ["approve", cid, "--receipt", token, "--ref", "test",
                            "--json"] + (["--gate"] if gate else []))
        self.assertEqual(a.returncode, 0, a.stderr)
        return json.loads(a.stdout)["rule_uuid"]

    def test_resolve_conflict_without_receipt_refuses_at_the_cli(self):
        """Row 11 equivalent for this loop's headline case: exit code AND
        the reason text on stderr, driven through the real bm_learn.py."""
        with tempfile.TemporaryDirectory() as root:
            self._init(root)
            r1 = self._approve(root, "push to main", "never force push", gate=True)
            r2 = self._approve(root, "reviewing a branch", "always allow the merge")
            r = self._run(root, ["resolve-conflict", r1, "--with", r2,
                                "--how", "contradicted", "--because", "testing"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("no-state-change-receipt", r.stderr)

    def test_supersede_round_trip_through_grant_state_receipt(self):
        """Proves the CLI glue end to end: grant-state-receipt's own
        content_parts computation must match what `supersede` computes when
        it spends the token, or this round trip would fail with
        receipt-stale-target."""
        with tempfile.TemporaryDirectory() as root:
            self._init(root)
            old = self._approve(root, "t1", "a1")
            new = self._approve(root, "t2", "a2")
            without = self._run(root, ["supersede", old, "--with", new,
                                       "--because", "replaced"])
            self.assertEqual(without.returncode, 2)
            self.assertIn("no-state-change-receipt", without.stderr)
            mint = self._run(root, ["grant-state-receipt", "supersede", old,
                                   "--with", new, "--because", "replaced",
                                   "--answer", "yes supersede it", "--json"])
            self.assertEqual(mint.returncode, 0, mint.stderr)
            token = json.loads(mint.stdout)["token"]
            spend = self._run(root, ["supersede", old, "--with", new,
                                     "--because", "replaced", "--receipt", token,
                                     "--json"])
            self.assertEqual(spend.returncode, 0, spend.stderr)
            self.assertEqual(json.loads(spend.stdout)["state"], "superseded")

    def test_forget_round_trip_through_grant_state_receipt(self):
        with tempfile.TemporaryDirectory() as root:
            self._init(root)
            rule = self._approve(root, "t3", "a3")
            without = self._run(root, ["forget", rule, "--yes"])
            self.assertEqual(without.returncode, 2)
            self.assertIn("no-state-change-receipt", without.stderr)
            mint = self._run(root, ["grant-state-receipt", "forget", rule,
                                   "--answer", "yes forget it", "--json"])
            self.assertEqual(mint.returncode, 0, mint.stderr)
            token = json.loads(mint.stdout)["token"]
            spend = self._run(root, ["forget", rule, "--yes", "--receipt", token])
            self.assertEqual(spend.returncode, 0, spend.stderr)

    def test_resolve_note_critical_alert_round_trip(self):
        with tempfile.TemporaryDirectory() as root:
            self._init(root)
            cap = self._run(root, ["capture", "--scope", "global", "--trigger", "t4",
                                  "--action", "a4", "--source", "manual", "--json"])
            self.assertEqual(cap.returncode, 0, cap.stderr)
            cid = json.loads(cap.stdout)["candidate_uuid"]
            note = self._run(root, ["note", "--kind", "alert", "--severity", "critical",
                                    "--anchor", "candidate:" + cid,
                                    "--body", "the retry path double charges",
                                    "--author", "Dana", "--json"])
            self.assertEqual(note.returncode, 0, note.stderr)
            nid = json.loads(note.stdout)["note_uuid"]
            without = self._run(root, ["resolve-note", nid, "--because", "fixed it"])
            self.assertEqual(without.returncode, 2)
            self.assertIn("no-state-change-receipt", without.stderr)
            mint = self._run(root, ["grant-state-receipt", "resolve-note", nid,
                                   "--because", "fixed it", "--answer", "yes",
                                   "--json"])
            self.assertEqual(mint.returncode, 0, mint.stderr)
            token = json.loads(mint.stdout)["token"]
            spend = self._run(root, ["resolve-note", nid, "--because", "fixed it",
                                    "--receipt", token])
            self.assertEqual(spend.returncode, 0, spend.stderr)


class TestSchema11Migration(unittest.TestCase):
    """Schema 10 to 11 (LOOP 4, 2026-07-30): learning_retrieval_membership
    and provisional_records. Same discipline as TestSchema9Migration: the
    fixture is a REAL store reverted to schema 10, not hand-written DDL, so
    it cannot drift from the schema anyone actually has."""

    def _schema10_store(self, d):
        with bs.Store(d) as store:
            store.claim("alpha", "persistent", "keep me", ["src/a.py"])
            c = store.capture_learning_candidate(
                "manual", trigger="writing an executive update",
                action="state customer impact first",
                because="leaders need the business state first",
                scope_type="global", scope_key="")
            _approved(store, c["candidate_uuid"],
                     founder_ref="approved before this loop's tables existed")
        path = os.path.join(d, bs.STORE_DIRNAME, bs.STORE_FILENAME)
        conn = sqlite3.connect(path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            for t in bs._TABLES_LOOP4:
                conn.execute("DROP TABLE IF EXISTS %s" % t)
            conn.execute("UPDATE meta SET value='10' WHERE key='schema_version'")
            conn.execute("COMMIT")
        finally:
            conn.close()
        return path

    def _snapshot(self, path):
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        try:
            out = {}
            for t in bs._TABLES_V10:
                rows = [dict(r) for r in conn.execute("SELECT * FROM %s" % t)]
                if t == "meta":
                    rows = [r for r in rows if r.get("key") != "schema_version"]
                out[t] = json.dumps(rows, sort_keys=True, default=str)
            return out
        finally:
            conn.close()

    def _tables(self, path):
        conn = sqlite3.connect(path)
        try:
            return {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            conn.close()

    def test_a_schema10_store_migrates_instead_of_being_quarantined(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._schema10_store(d)
            with bs.Store(d) as store:
                self.assertEqual(
                    store.conn.execute(
                        "SELECT value FROM meta WHERE key='schema_version'"
                    ).fetchone()["value"], str(bs.SCHEMA_VERSION))
            self.assertTrue(set(bs._TABLES_LOOP4) <= self._tables(path))
            self.assertEqual(
                glob.glob(os.path.join(d, bs.STORE_DIRNAME, "*quarantine*")), [],
                "a healthy schema-10 store must MIGRATE, never be quarantined")

    def test_migration_preserves_every_schema10_row(self):
        """Including the rule approved before these tables existed."""
        with tempfile.TemporaryDirectory() as d:
            path = self._schema10_store(d)
            before = self._snapshot(path)
            with bs.Store(d):
                pass
            self.assertEqual(before, self._snapshot(path))

    def test_migration_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._schema10_store(d)
            with bs.Store(d):
                pass
            first = self._snapshot(path)
            with bs.Store(d):
                pass
            self.assertEqual(first, self._snapshot(path))

    def test_calibrated_interrupted_migration_rolls_back_completely(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._schema10_store(d)
            original = bs._MIGRATIONS[10]

            def _fail_half_way(conn):
                conn.execute(bs._LOOP4_DDL_STATEMENTS[0])
                raise RuntimeError("simulated interruption mid-migration")

            bs._MIGRATIONS[10] = _fail_half_way
            try:
                with self.assertRaises(RuntimeError):
                    bs.Store(d)
            finally:
                bs._MIGRATIONS[10] = original
            conn = sqlite3.connect(path)
            try:
                v = conn.execute(
                    "SELECT value FROM meta WHERE key='schema_version'").fetchone()[0]
            finally:
                conn.close()
            self.assertEqual(v, "10", "an interrupted migration must not move the version")
            for t in bs._TABLES_LOOP4:
                self.assertNotIn(t, self._tables(path))
            with bs.Store(d):
                pass
            self.assertTrue(set(bs._TABLES_LOOP4) <= self._tables(path))

    def test_loop4_ddl_split_matches_the_table_list(self):
        self.assertEqual(len(bs._LOOP4_DDL_STATEMENTS), len(bs._TABLES_LOOP4))
        self.assertEqual(len(bs._LOOP4_INDEX_STATEMENTS), 1)

    def test_a_fresh_store_is_born_at_schema11_with_both_tables_present(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self.assertEqual(
                    store.conn.execute(
                        "SELECT value FROM meta WHERE key='schema_version'"
                    ).fetchone()["value"], str(bs.SCHEMA_VERSION))
            self.assertTrue(
                set(bs._TABLES_LOOP4) <= self._tables(
                    os.path.join(d, bs.STORE_DIRNAME, bs.STORE_FILENAME)))

    def test_record_uuid_did_not_become_not_null(self):
        """THE TRAP, checked mechanically: learning_applications.record_uuid
        must stay exactly as nullable as it always was. A store that
        already holds application rows with a NULL record_uuid (the
        founder's real store does) must keep opening and reading them
        without any migration attempting to rewrite that column."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                info = {r[1]: r for r in store.conn.execute(
                    "PRAGMA table_info(learning_applications)").fetchall()}
                record_uuid_col = info["record_uuid"]
                # PRAGMA table_info's notnull column is index 3: 0 means the
                # column accepts NULL.
                self.assertEqual(record_uuid_col[3], 0,
                                 "record_uuid must remain NULLable")
                # And a NULL actually stores and reads back through the real
                # API, not merely that the DDL claims to allow it: the
                # pre-loop-4 call shape (require_record_identity=False, no
                # --record) is exactly what the founder's existing NULL rows
                # came from, and it must keep working unchanged.
                c = store.capture_learning_candidate(
                    "manual", trigger="writing tests",
                    action="write a regression test", because="catch it",
                    scope_type="global", scope_key="")
                _approved(store, c["candidate_uuid"], founder_ref="ref1")
                res = store.record_learning_applications(
                    "writing tests today", session_id="s1",
                    require_record_identity=False)
                app_uuid = res["applications"][0]
                row = store.conn.execute(
                    "SELECT record_uuid FROM learning_applications "
                    "WHERE application_uuid=?", (app_uuid,)).fetchone()
                self.assertIsNone(row["record_uuid"])


class TestLoop4RetrievalMembership(unittest.TestCase):
    """LOOP 4: learning_retrieval_membership stores the exact eligible
    corpus (rule_uuid, rule_version), not only eligible_count."""

    def _approve(self, store, trigger, action, because, ref):
        c = store.capture_learning_candidate(
            "manual", trigger=trigger, action=action, because=because,
            scope_type="global", scope_key="")
        return _approved(store, c["candidate_uuid"], founder_ref=ref)

    def test_membership_recorded_for_an_eligible_rule(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule = self._approve(store, "writing tests",
                                     "write a regression test",
                                     "catch it next time", "ref1")
                res = store.record_learning_applications(
                    "writing tests today", session_id="s1",
                    new_record_name="task-x", require_record_identity=True)
                mem = store.get_retrieval_membership(res["retrieval_uuid"])
                self.assertEqual(
                    mem, {(rule["rule_uuid"], int(rule["current_version"]))})
                self.assertEqual(res["eligible"], 1)

    def test_eligible_count_still_matches_membership_size(self):
        """Backstop for the promise that eligible_count is untouched: for a
        freshly recorded run, its size and the count must agree."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                self._approve(store, "writing tests", "write a regression test",
                             "catch it next time", "ref1")
                res = store.record_learning_applications(
                    "writing tests today", session_id="s1",
                    new_record_name="task-x", require_record_identity=True)
                run = store.get_learning_retrieval_run(res["retrieval_uuid"])
                mem = store.get_retrieval_membership(res["retrieval_uuid"])
                self.assertEqual(int(run["eligible_count"]), len(mem))

    def test_identical_count_swap_reconstructs_exact_historical_corpus(self):
        """THE HEART OF THE LOOP. Swap one eligible rule for another so the
        COUNT stays identical, then prove the stored membership of the
        FIRST run still names the exact original rule, not the swapped-in
        one, and that grading the first run against TODAY's corpus (after
        the swap) would name the wrong rule."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rule1 = self._approve(store, "writing tests",
                                      "write a regression test",
                                      "catch it next time", "ref1")
                res1 = store.record_learning_applications(
                    "writing tests today", session_id="s1",
                    new_record_name="task-x", require_record_identity=True)
                run1 = res1["retrieval_uuid"]
                mem1 = store.get_retrieval_membership(run1)
                self.assertEqual(res1["eligible"], 1)
                self.assertEqual(mem1, {(rule1["rule_uuid"],
                                        int(rule1["current_version"]))})

                # THE SWAP: forget rule1, approve rule2. Eligible count for
                # an identical query is 1 both before and after.
                _state_changed(store, rule1["rule_uuid"], "forgotten",
                              reason="superseded by rule2")
                rule2 = self._approve(store, "writing tests",
                                      "add a regression test file",
                                      "catch it next time too", "ref2")

                res2 = store.record_learning_applications(
                    "writing tests today", session_id="s2",
                    new_record_name="task-y", require_record_identity=True)
                run2 = res2["retrieval_uuid"]
                mem2 = store.get_retrieval_membership(run2)

                # THE IDENTICAL-COUNT PROPERTY the loop names explicitly.
                self.assertEqual(res1["eligible"], res2["eligible"],
                                 "the swap must not change the COUNT")
                # THE RECONSTRUCTION PROPERTY: run1's stored membership
                # still names rule1, never rule2, no matter what happened
                # to the corpus since.
                self.assertEqual(mem1, {(rule1["rule_uuid"],
                                        int(rule1["current_version"]))})
                self.assertNotIn((rule2["rule_uuid"],
                                 int(rule2["current_version"])), mem1)
                # And run2's membership is the NEW corpus, not the old one:
                # the two runs' membership sets differ even though their
                # counts are identical, which is the exact case a
                # count-only ledger cannot tell apart.
                self.assertNotEqual(mem1, mem2)
                self.assertEqual(mem2, {(rule2["rule_uuid"],
                                        int(rule2["current_version"]))})
                # GRADING AGAINST TODAY'S CORPUS WOULD HAVE BEEN WRONG: rule1
                # is forgotten now, so "today's eligible set" for the same
                # query is rule2 alone, which does not contain rule1 -- the
                # rule run1 was actually graded against.
                today = store.retrieve_learning_rules(
                    "writing tests today", limit=100)
                today_membership = set(
                    (r["rule_uuid"], int(r["current_version"]))
                    for r in today["results"])
                self.assertNotEqual(
                    today_membership, mem1,
                    "grading run1 against today's corpus would be wrong: "
                    "rule1 (what run1 actually saw) is gone from it")


class TestLoop4ProvisionalRecords(unittest.TestCase):
    """LOOP 4: provisional records. Durable UUID, visible in project
    status, promotable, cancellable, linked applications preserved across
    both, and mechanically never merging with unrelated work."""

    def test_never_merge_identical_requested_names_are_distinct_records(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rec1 = store.create_provisional_record("task-x", session_id="s1")
                rec2 = store.create_provisional_record("task-x", session_id="s1")
                self.assertNotEqual(rec1.lifecycle_uuid, rec2.lifecycle_uuid)
                self.assertNotEqual(rec1.name, rec2.name)
                # Mechanical, not conventional: the one_active_per_name
                # unique index did not have to be consulted for these to
                # differ, because the stored names already do.
                rows = store.conn.execute(
                    "SELECT COUNT(*) AS c FROM records WHERE state='active' "
                    "AND lifecycle_uuid IN (?,?)",
                    (rec1.lifecycle_uuid, rec2.lifecycle_uuid)).fetchone()
                self.assertEqual(rows["c"], 2)

    def test_provisional_record_is_visible_in_project_status(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rec = store.create_provisional_record("task-x", session_id="s1")
            view = bs.render_state_md(d)
            self.assertIn(rec.lifecycle_uuid, view)
            self.assertIn("PROVISIONAL", view)

    def test_promotion_preserves_linked_applications_and_lifecycle_uuid(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                res = store.record_learning_applications(
                    "a task", session_id="s1", new_record_name="task-x",
                    require_record_identity=True)
                rec_uuid = res["new_record_uuid"]
                before = store.list_learning_applications(record_prefix=rec_uuid)
                promoted = store.promote_provisional_record(rec_uuid)
                self.assertEqual(promoted.lifecycle_uuid, rec_uuid)
                after = store.list_learning_applications(record_prefix=rec_uuid)
                self.assertEqual(
                    [a["application_uuid"] for a in before],
                    [a["application_uuid"] for a in after],
                    "promotion must not move or drop any linked application")

    def test_cancellation_preserves_linked_applications_and_closes_record(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                res = store.record_learning_applications(
                    "a task", session_id="s1", new_record_name="task-x",
                    require_record_identity=True)
                rec_uuid = res["new_record_uuid"]
                before = store.list_learning_applications(record_prefix=rec_uuid)
                store.cancel_provisional_record(rec_uuid, session_id="s1")
                after = store.list_learning_applications(record_prefix=rec_uuid)
                self.assertEqual(
                    [a["application_uuid"] for a in before],
                    [a["application_uuid"] for a in after],
                    "cancellation must not move or drop any linked application")
                self.assertEqual(store.get(rec_uuid).state, "complete")

    def test_promote_after_cancel_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rec = store.create_provisional_record("task-x", session_id="s1")
                store.cancel_provisional_record(rec.lifecycle_uuid, session_id="s1")
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.promote_provisional_record(rec.lifecycle_uuid)
                self.assertEqual(ctx.exception.reason, "already-cancelled")

    def test_cancel_after_promote_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rec = store.create_provisional_record("task-x", session_id="s1")
                store.promote_provisional_record(rec.lifecycle_uuid)
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.cancel_provisional_record(rec.lifecycle_uuid, session_id="s1")
                self.assertEqual(ctx.exception.reason, "already-promoted")

    def test_list_provisional_records_reports_every_one(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                store.create_provisional_record("task-x", session_id="s1")
                store.create_provisional_record("task-y", session_id="s1")
                self.assertEqual(len(store.list_provisional_records()), 2)


class TestLoop4ProtectLinks(unittest.TestCase):
    """LOOP 4: protect the links. Each refusal below is its own reason
    string, and relinking is checked as a structural property that already
    holds rather than a new refusal (see its own test)."""

    def test_apply_against_nonexistent_record_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                res = store.record_learning_applications(
                    "a task", session_id="s1",
                    record_prefix="deadbeef00000000000000000000000",
                    require_record_identity=True)
                self.assertEqual(res["record_error_kind"], "not-found")

    def test_apply_against_closed_record_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rec = store.create_provisional_record("task-x", session_id="s1")
                store.cancel_provisional_record(rec.lifecycle_uuid, session_id="s1")
                res = store.record_learning_applications(
                    "a task", session_id="s1", record_prefix=rec.lifecycle_uuid,
                    require_record_identity=True)
                self.assertEqual(res["record_error_kind"], "closed-record")

    def test_apply_against_unpromoted_provisional_from_other_session_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rec = store.create_provisional_record("task-x", session_id="sA")
                res = store.record_learning_applications(
                    "a task", session_id="sB", record_prefix=rec.lifecycle_uuid,
                    require_record_identity=True)
                self.assertEqual(res["record_error_kind"],
                                 "provisional-cross-session")

    def test_apply_against_own_unpromoted_provisional_same_session_succeeds(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rec = store.create_provisional_record("task-x", session_id="sA")
                res = store.record_learning_applications(
                    "a task", session_id="sA", record_prefix=rec.lifecycle_uuid,
                    require_record_identity=True)
                self.assertEqual(res["record_error"], "")

    def test_promoted_provisional_accepts_a_different_session(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                rec = store.create_provisional_record("task-x", session_id="sA")
                store.promote_provisional_record(rec.lifecycle_uuid)
                res = store.record_learning_applications(
                    "a task", session_id="sB", record_prefix=rec.lifecycle_uuid,
                    require_record_identity=True)
                self.assertEqual(res["record_error"], "")

    def test_relink_never_moves_an_existing_link_to_a_different_record(self):
        """Structural, not a new refusal: _prior_application never selects a
        row already linked to a DIFFERENT record for UPDATE, so a second
        apply for the identical task under a different --record writes its
        OWN new row instead of moving the first one's link."""
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                c = store.capture_learning_candidate(
                    "manual", trigger="writing tests",
                    action="write a regression test", because="catch it",
                    scope_type="global", scope_key="")
                _approved(store, c["candidate_uuid"], founder_ref="ref1")
                res_a = store.record_learning_applications(
                    "writing tests today", session_id="s1",
                    new_record_name="task-a", require_record_identity=True)
                rec_a = res_a["new_record_uuid"]
                app_a = res_a["applications"][0]

                rec_b = store.create_provisional_record("task-b", session_id="s1")
                res_b = store.record_learning_applications(
                    "writing tests today", session_id="s1",
                    record_prefix=rec_b.lifecycle_uuid,
                    require_record_identity=True)
                self.assertEqual(res_b["record_error"], "")
                app_b = res_b["applications"][0]

                self.assertNotEqual(app_a, app_b,
                                   "distinct work must get distinct rows")
                row_a = store.get_learning_application(app_a)
                self.assertEqual(row_a["record_uuid"], rec_a,
                                 "the first application's link must never move")
                row_b = store.get_learning_application(app_b)
                self.assertEqual(row_b["record_uuid"], rec_b.lifecycle_uuid)


class TestLoop4MandatoryIdentity(unittest.TestCase):
    """LOOP 4: `apply` on the real CLI, through subprocess, so this proves
    what the founder actually sees (message text, exit code), not only what
    the Store API returns."""

    def _run(self, root, args, extra_env=None):
        e = dict(os.environ, BROTHERMODE_ROOT=root,
                BROTHERMODE_VAULT=os.path.join(root, "vault"))
        if extra_env:
            e.update(extra_env)
        return subprocess.run([sys.executable, os.path.join(HERE, "bm_learn.py")]
                              + args, cwd=root, env=e, capture_output=True, text=True)

    def _init(self, root):
        e = dict(os.environ, BROTHERMODE_ROOT=root)
        r = subprocess.run([sys.executable, os.path.join(HERE, "bm_store.py"), "init"],
                           cwd=root, env=e, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_apply_without_identity_is_refused_and_names_three_ways_forward(self):
        with tempfile.TemporaryDirectory() as root:
            self._init(root)
            r = self._run(root, ["apply", "--query", "fix the login bug",
                                "--session", "s1"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("--record", r.stderr)
            self.assertIn("--new-record", r.stderr)
            self.assertIn(bs.ACTIVE_RECORD_ENV, r.stderr)

    def test_apply_with_record_and_new_record_both_refused(self):
        with tempfile.TemporaryDirectory() as root:
            self._init(root)
            r = self._run(root, ["apply", "--query", "fix the login bug",
                                "--session", "s1", "--record", "deadbeef",
                                "--new-record", "task-x"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("not both", r.stderr)

    def test_apply_with_new_record_succeeds_and_is_visible_in_dashboard(self):
        with tempfile.TemporaryDirectory() as root:
            self._init(root)
            r = self._run(root, ["apply", "--query", "fix the login bug",
                                "--session", "s1", "--new-record", "task-x"])
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("created provisional work record", r.stdout)
            dash = subprocess.run(
                [sys.executable, os.path.join(HERE, "bm_store.py"), "dashboard"],
                cwd=root, env=dict(os.environ, BROTHERMODE_ROOT=root),
                capture_output=True, text=True)
            self.assertIn("PROVISIONAL", dash.stdout)

    def test_apply_with_env_active_record_succeeds(self):
        with tempfile.TemporaryDirectory() as root:
            self._init(root)
            made = self._run(root, ["apply", "--query", "task one",
                                    "--session", "s1", "--new-record", "task-x"])
            self.assertEqual(made.returncode, 0, made.stdout + made.stderr)
            listed = subprocess.run(
                [sys.executable, os.path.join(HERE, "bm_store.py"), "dump"],
                cwd=root, env=dict(os.environ, BROTHERMODE_ROOT=root),
                capture_output=True, text=True)
            rec_uuid = json.loads(listed.stdout)["records"][0]["lifecycle_uuid"]
            r = self._run(root, ["apply", "--query", "task two", "--session", "s1"],
                          extra_env={"BM_ACTIVE_RECORD": rec_uuid})
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_lookup_unaffected_no_session_no_record_required(self):
        with tempfile.TemporaryDirectory() as root:
            self._init(root)
            r = self._run(root, ["lookup", "--query", "fix the login bug"])
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_lookup_new_record_flag_refused(self):
        with tempfile.TemporaryDirectory() as root:
            self._init(root)
            r = self._run(root, ["lookup", "--query", "fix the login bug",
                                "--new-record", "x"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("means nothing here", r.stderr)

    def test_two_identical_wording_tasks_one_session_get_distinct_histories(self):
        """The plan's own headline acceptance criterion (line 486)."""
        with tempfile.TemporaryDirectory() as root:
            self._init(root)
            a = self._run(root, ["apply", "--query", "fix the login bug",
                                "--session", "s1", "--new-record", "task-a"])
            b = self._run(root, ["apply", "--query", "fix the login bug",
                                "--session", "s1", "--new-record", "task-b"])
            self.assertEqual(a.returncode, 0, a.stdout + a.stderr)
            self.assertEqual(b.returncode, 0, b.stdout + b.stderr)
            listed = subprocess.run(
                [sys.executable, os.path.join(HERE, "bm_store.py"), "dump"],
                cwd=root, env=dict(os.environ, BROTHERMODE_ROOT=root),
                capture_output=True, text=True)
            uuids = {r["lifecycle_uuid"] for r in json.loads(listed.stdout)["records"]}
            self.assertEqual(len(uuids), 2,
                             "two identical-wording tasks in one session must "
                             "produce two distinct work records")


class TestLoop4Calibration(unittest.TestCase):
    """CALIBRATION for both LOOP 4 protections: revert each, prove the old
    defect reappears, restore, prove the protection holds again."""

    def test_calibrated_mandatory_identity_reverts_and_restores(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                # REVERT: require_record_identity=False is the pre-loop-4
                # call shape. A session-only apply must succeed again,
                # reproducing the defect this loop closes.
                reverted = store.record_learning_applications(
                    "a task", session_id="s1", require_record_identity=False)
                self.assertEqual(reverted.get("record_error"), "")
                # RESTORE: require_record_identity=True is what cmd_apply
                # always passes. The identical call now refuses.
                with self.assertRaises(bs.OwnershipRefused) as ctx:
                    store.record_learning_applications(
                        "a task", session_id="s1", require_record_identity=True)
                self.assertEqual(ctx.exception.reason, "no-work-identity")

    def test_calibrated_membership_swap_test_reverts_and_restores(self):
        with tempfile.TemporaryDirectory() as d:
            with bs.Store(d) as store:
                c1 = store.capture_learning_candidate(
                    "manual", trigger="writing tests",
                    action="write a regression test", because="catch it",
                    scope_type="global", scope_key="")
                rule1 = _approved(store, c1["candidate_uuid"], founder_ref="ref1")
                res1 = store.record_learning_applications(
                    "writing tests today", session_id="s1",
                    new_record_name="task-x", require_record_identity=True)
                run1 = res1["retrieval_uuid"]

                def _assert_reconstructs():
                    mem1 = store.get_retrieval_membership(run1)
                    self.assertEqual(
                        mem1, {(rule1["rule_uuid"], int(rule1["current_version"]))},
                        "stored membership must still name the original rule")

                # GREEN: membership intact, the swap test's own assertion holds.
                _assert_reconstructs()

                # REVERT: simulate the count-only, pre-loop-4 shape by
                # deleting this run's membership rows (what a store that
                # never wrote them would look like).
                store.conn.execute(
                    "DELETE FROM learning_retrieval_membership "
                    "WHERE retrieval_uuid=?", (run1,))
                store.conn.commit()
                with self.assertRaises(AssertionError):
                    _assert_reconstructs()

                # RESTORE: re-record the same retrieval, which re-populates
                # membership, and the assertion is green again.
                res1b = store.record_learning_applications(
                    "writing tests today", session_id="s1",
                    record_prefix=res1["new_record_uuid"],
                    require_record_identity=True)
                run1 = res1b["retrieval_uuid"]
                _assert_reconstructs()


if __name__ == "__main__":
    # The leak check lives in the runner, so it applies to every test without
    # each of the ~40 TestCase classes having to opt in. Running this file
    # through `python -m unittest` instead bypasses it and only tearDownModule
    # applies; `python3 tools/test_bm_store.py`, which is what CI and the docs
    # both use, gets the per-test check.
    unittest.main(
        verbosity=2,
        testRunner=unittest.TextTestRunner(verbosity=2,
                                            resultclass=_LeakCheckingResult))
