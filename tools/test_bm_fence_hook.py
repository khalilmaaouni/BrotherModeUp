#!/usr/bin/env python3
"""Regression tests for tools/bm_fence_hook.py, the PreToolUse fence gate.
Standard library only. Run: python3 tools/test_bm_fence_hook.py

Same discipline as tools/test_bm_store.py: every test is self-contained under
tempfile.TemporaryDirectory(), scrubs BROTHERMODE_ROOT out of its own
environment and out of every subprocess it spawns, and never touches this
repo's own files, the real store, or the real home directory.

The calibrated_* tests each prove one property the fence would be worthless
without, stated as the thing that must NOT happen:
  1. a write to a path THIS session owns must not be blocked;
  2. a write to a path ANOTHER live record owns must not be allowed, and the
     refusal must name the owner and the exact takeover command;
  3. presenting another session's PUBLIC label as your own must not grant
     ownership, whether you pass it on the wire or write it into the store;
  4. a broken, missing or empty store must not turn into a refusal, because
     this hook sits in front of every edit the founder makes.
"""
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unicodedata
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK_PATH = os.path.join(HERE, "bm_fence_hook.py")
STORE_PATH = os.path.join(HERE, "bm_store.py")
DOCS_PATH = os.path.join(os.path.dirname(HERE), "docs", "HOOKS.md")

import importlib.util

_spec = importlib.util.spec_from_file_location("bm_store", STORE_PATH)
bs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bs)
sys.modules["bm_store"] = bs

_hspec = importlib.util.spec_from_file_location("bm_fence_hook", HOOK_PATH)
fh = importlib.util.module_from_spec(_hspec)
_hspec.loader.exec_module(fh)
sys.modules["bm_fence_hook"] = fh


def _clean_env(extra=None):
    """A child environment with every ambient BrotherMode variable removed,
    so a shell export left over from another task can never decide the
    outcome of a test that is trying to prove something about root
    resolution, identity, or strict mode."""
    e = dict(os.environ)
    for k in ("BROTHERMODE_ROOT", "BM_FENCE_STRICT", "BM_FENCE_SESSION_ID"):
        e.pop(k, None)
    if extra:
        e.update(extra)
    return e


def payload(session_id, cwd, tool_name="Edit", tool_input=None, **kw):
    """A PreToolUse payload shaped exactly as the hooks documentation shows
    it (read 2026-07-27): session_id, cwd, hook_event_name, tool_name,
    tool_input, tool_use_id. Tests that need a MALFORMED payload build it by
    deleting from this, so the well-formed shape lives in exactly one place."""
    p = {
        "session_id": session_id,
        "transcript_path": os.path.join(cwd, "transcript.jsonl"),
        "cwd": cwd,
        "permission_mode": "default",
        "hook_event_name": "PreToolUse",
        "tool_name": tool_name,
        "tool_input": tool_input if tool_input is not None else {
            "file_path": "src/app.py", "old_string": "a", "new_string": "b"},
        "tool_use_id": "toolu_01TEST",
    }
    p.update(kw)
    return p


class FenceHookBase(unittest.TestCase):
    """A throwaway project with a store, a src/ tree, and two sessions."""

    VICTIM = "sess-owner-0001"
    OTHER = "sess-other-0002"

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        # realpath up front: on macOS /var and /tmp are symlinks, and every
        # comparison in the hook is against a realpath'd root.
        self.root = os.path.realpath(self._tmp.name)
        os.makedirs(os.path.join(self.root, ".git"))
        os.makedirs(os.path.join(self.root, "src"))
        for name in ("app.py", "other.py"):
            with io.open(os.path.join(self.root, "src", name), "w",
                         encoding="utf-8") as f:
                f.write("# %s\n" % name)
        with bs.Store(self.root) as store:
            pass
        self._env_patch = mock.patch.dict(
            os.environ, {}, clear=False)
        self._env_patch.start()
        for k in ("BROTHERMODE_ROOT", "BM_FENCE_STRICT", "BM_FENCE_SESSION_ID"):
            os.environ.pop(k, None)

    def tearDown(self):
        self._env_patch.stop()
        self._tmp.cleanup()

    # -- helpers ---------------------------------------------------------

    def label(self, session_id):
        return fh.session_label(self.root, session_id)

    def claim(self, name, files, session_id_label, lifetime="ephemeral"):
        with bs.Store(self.root, create=False) as store:
            rec = store.claim(name, lifetime, objective="test fence",
                              files=files, session_id=session_id_label)
        # The CLI refreshes the generated view after every mutation; the
        # Python API does not, and the identity tests below assert on what a
        # human actually reads out of STATE.md.
        bs.write_state_view(self.root)
        return rec

    def decide(self, p):
        """Run the decision in process. Returns (decision, stderr_notes)."""
        return fh.decide(p)

    def run_hook(self, p, env=None, cwd=None):
        """Run the hook exactly as Claude Code would: a bare command with a
        JSON payload on stdin. Returns the CompletedProcess."""
        return subprocess.run(
            [sys.executable, HOOK_PATH],
            input=json.dumps(p), text=True, capture_output=True,
            cwd=cwd or self.root, env=_clean_env(env))

    def assertAllowed(self, decision, notes=None):
        self.assertIsNone(
            decision,
            "expected no decision (allow); got a deny: %r" % (decision,))

    def assertDenied(self, decision):
        self.assertIsNotNone(decision, "expected a deny; got allow")
        self.assertEqual(
            decision["hookSpecificOutput"]["permissionDecision"], "deny")
        return decision["hookSpecificOutput"]["permissionDecisionReason"]


# ---------------------------------------------------------------------------
# Calibration 1 and 2: the fence allows its owner and refuses everyone else.
# ---------------------------------------------------------------------------

class CalibratedOwnership(FenceHookBase):

    def test_calibrated_1_owner_may_write_its_own_claim(self):
        mine = self.label(self.VICTIM)
        self.claim("api", ["src/app.py"], mine)
        decision, notes = self.decide(payload(self.VICTIM, self.root))
        self.assertAllowed(decision)
        self.assertEqual(notes, [], "the owner's write must not print a "
                                    "fail-open warning: %r" % (notes,))

    def test_calibrated_2_foreign_record_is_denied_and_named(self):
        mine = self.label(self.VICTIM)
        rec = self.claim("api", ["src/app.py"], mine)
        decision, _notes = self.decide(payload(self.OTHER, self.root))
        reason = self.assertDenied(decision)
        # The refusal must be actionable: WHICH record, WHICH owner, and the
        # exact command that moves the fence. A deny that says only "no" sends
        # the reader back to guessing, which is how fences get bypassed.
        self.assertIn("api", reason)
        self.assertIn(rec.lifecycle_uuid, reason)
        self.assertIn(mine, reason)
        self.assertIn(self.label(self.OTHER), reason)
        self.assertIn("adopt %s --version %s" % (rec.lifecycle_uuid, rec.version),
                      reason)
        self.assertIn("--adopt-from-live-session", reason)

    def test_unclaimed_path_is_allowed_by_default(self):
        self.claim("api", ["src/app.py"], self.label(self.VICTIM))
        p = payload(self.OTHER, self.root,
                    tool_input={"file_path": "src/other.py"})
        decision, _n = self.decide(p)
        self.assertAllowed(decision)

    def test_parked_record_does_not_fence(self):
        """Only ACTIVE records hold a fence: this is the same rule the store
        applies when admitting a claim, and the two must not diverge."""
        mine = self.label(self.VICTIM)
        rec = self.claim("api", ["src/app.py"], mine)
        with bs.Store(self.root, create=False) as store:
            store.transition(rec.lifecycle_uuid, rec.version, "parked",
                             session_id=mine)
        decision, notes = self.decide(payload(self.OTHER, self.root))
        self.assertAllowed(decision)
        # Zero ACTIVE claims left, so this is the loud fail-open, not a
        # silent allow.
        self.assertTrue(any("no active claims" in n for n in notes), notes)


# ---------------------------------------------------------------------------
# Calibration 3: identity (audit finding 8B).
# ---------------------------------------------------------------------------

class CalibratedIdentity(FenceHookBase):

    def test_calibrated_3a_public_label_presented_as_session_id_gains_nothing(self):
        """The exact forgery the old design could not survive: the owning
        value was printed in plaintext into STATE.md, which every session
        reads, so the guard compared a public value against itself. Here the
        forger reads the label out of STATE.md and presents it as their own
        session id. The hook derives the label from the TOKEN this process
        could open, never from the string it was handed, so the forger gets a
        third, unrelated label and is refused."""
        mine = self.label(self.VICTIM)
        self.claim("api", ["src/app.py"], mine)
        state = io.open(os.path.join(self.root, "STATE.md"),
                        encoding="utf-8").read()
        self.assertIn(mine, state, "the public label must be visible to humans")
        decision, _n = self.decide(payload(mine, self.root))
        reason = self.assertDenied(decision)
        self.assertNotIn("This session is %s," % mine, reason)

    def test_calibrated_3b_claiming_under_a_stolen_label_gains_nothing(self):
        """The store-side version of the same forgery: the attacker does not
        pass the label on the wire, they write it into the store as the owner
        of their OWN claim. It still buys nothing, because ownership is
        checked against the attacker's own derived label at write time."""
        victim_label = self.label(self.VICTIM)
        self.claim("stolen", ["src/other.py"], victim_label)
        p = payload(self.OTHER, self.root,
                    tool_input={"file_path": "src/other.py"})
        decision, _n = self.decide(p)
        reason = self.assertDenied(decision)
        self.assertIn(victim_label, reason)

    def test_label_is_stable_for_a_session_and_distinct_across_sessions(self):
        a1 = self.label(self.VICTIM)
        a2 = self.label(self.VICTIM)
        b = self.label(self.OTHER)
        self.assertEqual(a1, a2)
        self.assertNotEqual(a1, b)
        self.assertTrue(a1.startswith("bm1-"), a1)

    def test_token_is_never_printed_by_any_command(self):
        token = fh.ensure_token(self.root, self.VICTIM)
        label = fh.label_for_token(token)
        self.claim("api", ["src/app.py"], label)
        state = io.open(os.path.join(self.root, "STATE.md"),
                        encoding="utf-8").read()
        self.assertNotIn(token, state)
        r = subprocess.run([sys.executable, HOOK_PATH, "whoami",
                            "--session-id", self.VICTIM],
                           capture_output=True, text=True, cwd=self.root,
                           env=_clean_env())
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn(token, r.stdout)
        self.assertNotIn(token, r.stderr)
        self.assertIn(label, r.stdout)
        # And the deny message, the one string that reaches the model.
        decision, _n = self.decide(payload(self.OTHER, self.root))
        reason = self.assertDenied(decision)
        self.assertNotIn(token, reason)
        self.assertNotIn(fh.ensure_token(self.root, self.OTHER), reason)

    def test_label_cannot_be_derived_without_the_token(self):
        """A one-way hash, asserted as a property rather than assumed: the
        label must not be a function of the session id alone, or every reader
        of a session id could compute the owner's label and the token would
        be decoration."""
        token = fh.ensure_token(self.root, self.VICTIM)
        label = fh.label_for_token(token)
        os.remove(fh.token_path(self.root, self.VICTIM))
        self.assertNotEqual(fh.session_label(self.root, self.VICTIM), label,
                            "a fresh token must yield a different label")

    @unittest.skipIf(sys.platform == "win32",
                     "POSIX mode bits; on Windows os.chmod only toggles the "
                     "read-only bit and the ACL is the real protection")
    def test_token_file_is_owner_only_on_posix(self):
        fh.ensure_token(self.root, self.VICTIM)
        p = fh.token_path(self.root, self.VICTIM)
        self.assertEqual(stat.S_IMODE(os.stat(p).st_mode), 0o600)
        d = fh.fence_dir(self.root)
        self.assertEqual(stat.S_IMODE(os.stat(d).st_mode), 0o700)

    def test_missing_session_id_fails_open(self):
        self.claim("api", ["src/app.py"], self.label(self.VICTIM))
        p = payload(self.VICTIM, self.root)
        del p["session_id"]
        decision, notes = self.decide(p)
        self.assertAllowed(decision)
        self.assertTrue(any("no verifiable identity" in n for n in notes), notes)


# ---------------------------------------------------------------------------
# Calibration 4: fail open, loudly, on every broken-store condition.
# ---------------------------------------------------------------------------

class CalibratedFailOpen(FenceHookBase):

    def _assert_fails_open(self, decision, notes, fragment):
        self.assertAllowed(decision)
        self.assertTrue(notes, "a fail-open must be LOUD; stderr was empty")
        joined = " ".join(notes)
        self.assertIn("FAILING OPEN", joined)
        self.assertIn(fragment, joined)

    def test_calibrated_4_store_deleted_mid_session_fails_open(self):
        self.claim("api", ["src/app.py"], self.label(self.VICTIM))
        for suffix in ("", "-wal", "-shm"):
            p = bs.store_path(self.root) + suffix
            if os.path.exists(p):
                os.remove(p)
        decision, notes = self.decide(payload(self.OTHER, self.root))
        self._assert_fails_open(decision, notes, "no store at")

    def test_zero_byte_store_fails_open(self):
        self.claim("api", ["src/app.py"], self.label(self.VICTIM))
        with io.open(bs.store_path(self.root), "w", encoding="utf-8") as f:
            f.write("")
        decision, notes = self.decide(payload(self.OTHER, self.root))
        self._assert_fails_open(decision, notes, "could not be opened read-only")

    def test_garbage_store_fails_open(self):
        self.claim("api", ["src/app.py"], self.label(self.VICTIM))
        with io.open(bs.store_path(self.root), "w", encoding="utf-8") as f:
            f.write("this is not a sqlite database, not even a little bit")
        decision, notes = self.decide(payload(self.OTHER, self.root))
        self.assertAllowed(decision)
        self.assertTrue(any("FAILING OPEN" in n for n in notes), notes)

    def test_no_claims_at_all_fails_open(self):
        decision, notes = self.decide(payload(self.OTHER, self.root))
        self._assert_fails_open(decision, notes, "no active claims")

    def test_no_project_root_fails_open(self):
        outside = os.path.realpath(tempfile.mkdtemp())
        try:
            p = payload(self.OTHER, outside)
            decision, notes = self.decide(p)
            self._assert_fails_open(decision, notes, "no BrotherMode project root")
        finally:
            shutil.rmtree(outside, ignore_errors=True)

    def test_malformed_payload_fails_open(self):
        self.claim("api", ["src/app.py"], self.label(self.VICTIM))
        for bad in (None, [], "string", 42):
            decision, notes = self.decide(bad)
            self.assertAllowed(decision)
            self.assertTrue(any("FAILING OPEN" in n for n in notes), (bad, notes))

    def test_write_tool_with_no_path_fails_open(self):
        self.claim("api", ["src/app.py"], self.label(self.VICTIM))
        p = payload(self.OTHER, self.root, tool_input={"content": "x"})
        decision, notes = self.decide(p)
        self._assert_fails_open(decision, notes, "no target path found")

    def test_unimportable_store_module_fails_open(self):
        self.claim("api", ["src/app.py"], self.label(self.VICTIM))
        with mock.patch.object(fh, "_load_store_module", return_value=None):
            decision, notes = self.decide(payload(self.OTHER, self.root))
        self._assert_fails_open(decision, notes, "could not be imported")

    def test_unexpected_exception_fails_open(self):
        """The blanket catch, asserted rather than assumed. An unforeseen bug
        in this hook must never become a refusal in front of the founder."""
        self.claim("api", ["src/app.py"], self.label(self.VICTIM))
        def boom(root):
            raise RuntimeError("simulated internal defect")
        with mock.patch.object(fh, "active_claims", boom):
            decision, notes = self.decide(payload(self.OTHER, self.root))
        self.assertAllowed(decision)
        joined = " ".join(notes)
        self.assertIn("FAILING OPEN after an unexpected error", joined)
        self.assertIn("simulated internal defect", joined)

    def test_broken_store_fails_open_through_the_real_process_too(self):
        """The in-process assertions above prove decide(); this proves the
        whole executable, because a fail-open that only holds when called as a
        function is not the thing installed in front of the founder's edits."""
        self.claim("api", ["src/app.py"], self.label(self.VICTIM))
        os.remove(bs.store_path(self.root))
        r = self.run_hook(payload(self.OTHER, self.root))
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout, "", "fail-open must emit NO decision JSON")
        self.assertIn("FAILING OPEN", r.stderr)


# ---------------------------------------------------------------------------
# Path canonicalization: a comparison on unresolved strings is no fence.
# ---------------------------------------------------------------------------

class EnforcedModeFailsClosed(FenceHookBase):
    """C-01 (2026-08-03). An adversarial probe found that EVERY failure path in
    this hook produced an allow: nine conditions each let a write through
    another session's active fence with exit 0, and BM_FENCE_STRICT could not
    help because it is read after all of them and is a no-op on a zero-claims
    store. BM_FENCE_MODE=enforced makes those same conditions refuse.

    Every test here asserts BOTH directions on the same condition: deny under
    enforced, allow under the default. The second half is the important one.
    It is what stops a later change from quietly making fail-closed the
    default for people who never asked for it, which this project decided
    against on purpose."""

    def _both_ways(self, break_it, fragment=None):
        """Apply break_it(), then assert deny in enforced and allow by default."""
        break_it()
        p = payload(self.OTHER, self.root)
        with mock.patch.dict(os.environ, {"BM_FENCE_MODE": "enforced"}):
            decision, notes = self.decide(p)
        reason = self.assertDenied(decision)
        self.assertIn("enforced mode", reason)
        self.assertTrue(any("FAILING CLOSED" in n for n in notes), notes)
        if fragment is not None:
            self.assertIn(fragment, " ".join(notes))
        with mock.patch.dict(os.environ, {"BM_FENCE_MODE": ""}):
            decision2, notes2 = self.decide(p)
        self.assertAllowed(decision2)
        self.assertTrue(any("FAILING OPEN" in n for n in notes2), notes2)

    def _remove_store(self):
        for suffix in ("", "-wal", "-shm"):
            p = bs.store_path(self.root) + suffix
            if os.path.exists(p):
                os.remove(p)

    def test_store_missing_denies_when_enforced(self):
        self.claim("api", ["src/app.py"], self.label(self.VICTIM))
        self._both_ways(self._remove_store, "no store at")

    def test_store_zero_bytes_denies_when_enforced(self):
        self.claim("api", ["src/app.py"], self.label(self.VICTIM))

        def blank():
            with io.open(bs.store_path(self.root), "w", encoding="utf-8") as f:
                f.write("")
        self._both_ways(blank)

    def test_store_corrupt_denies_when_enforced(self):
        self.claim("api", ["src/app.py"], self.label(self.VICTIM))

        def garbage():
            with io.open(bs.store_path(self.root), "w", encoding="utf-8") as f:
                f.write("this is not a sqlite database, not even a little bit")
        self._both_ways(garbage)

    def test_zero_active_claims_denies_when_enforced(self):
        """The state a FRESH project sits in, and the one the probe called the
        worst of the nine: with no active claims the fence allowed everything,
        and BM_FENCE_STRICT short-circuited before it could tighten anything."""
        self._both_ways(lambda: None, "no active claims")

    def test_no_project_root_denies_when_enforced(self):
        outside = os.path.realpath(tempfile.mkdtemp())
        try:
            p = payload(self.OTHER, outside)
            with mock.patch.dict(os.environ, {"BM_FENCE_MODE": "enforced"}):
                decision, notes = self.decide(p)
            self.assertIn("enforced mode", self.assertDenied(decision))
            with mock.patch.dict(os.environ, {"BM_FENCE_MODE": ""}):
                decision2, _ = self.decide(p)
            self.assertAllowed(decision2)
        finally:
            shutil.rmtree(outside, ignore_errors=True)

    def test_malformed_payloads_deny_when_enforced(self):
        """The five shapes the probe drove, each its own allow before this."""
        self.claim("api", ["src/app.py"], self.label(self.VICTIM))
        good = payload(self.OTHER, self.root)
        shapes = [
            ("not an object", []),
            ("tool_input not an object",
             dict(good, tool_input="nope")),
            ("no session_id",
             {k: v for k, v in good.items() if k != "session_id"}),
            ("no target path",
             dict(good, tool_input={})),
            ("unrecognized path key",
             dict(good, tool_input={"some_future_key": "src/app.py"})),
        ]
        for name, shape in shapes:
            with mock.patch.dict(os.environ, {"BM_FENCE_MODE": "enforced"}):
                decision, _ = self.decide(shape)
            self.assertIsNotNone(
                decision,
                "enforced mode allowed a malformed payload (%s)" % name)
            with mock.patch.dict(os.environ, {"BM_FENCE_MODE": ""}):
                decision2, _ = self.decide(shape)
            self.assertIsNone(
                decision2,
                "default mode must still allow a malformed payload (%s)" % name)

    def test_internal_exception_denies_when_enforced(self):
        """The blanket catch: in advisory it turns any bug in this file into an
        allow, which is deliberate. Somebody who asked for fail-closed has said
        they would rather be stopped by that bug than wave a write through."""
        self.claim("api", ["src/app.py"], self.label(self.VICTIM))
        p = payload(self.OTHER, self.root)
        boom = mock.patch.object(
            fh, "session_label", side_effect=RuntimeError("seeded"))
        with mock.patch.dict(os.environ, {"BM_FENCE_MODE": "enforced"}), boom:
            decision, notes = self.decide(p)
        self.assertIn("enforced mode", self.assertDenied(decision))
        self.assertTrue(any("FAILING CLOSED" in n for n in notes), notes)
        with mock.patch.dict(os.environ, {"BM_FENCE_MODE": ""}), mock.patch.object(
                fh, "session_label", side_effect=RuntimeError("seeded")):
            decision2, _ = self.decide(p)
        self.assertAllowed(decision2)

    def test_owner_is_still_allowed_when_enforced(self):
        """Enforcement must not break the happy path: the session that HOLDS
        the claim still writes freely."""
        owner = self.label(self.VICTIM)
        self.claim("api", ["src/app.py"], owner)
        p = payload(self.VICTIM, self.root)
        with mock.patch.dict(os.environ, {"BM_FENCE_MODE": "enforced"}):
            decision, _ = self.decide(p)
        self.assertAllowed(decision)

    def test_mode_value_is_exact_and_case_insensitive(self):
        self.assertTrue(fh.enforced_mode({"BM_FENCE_MODE": "enforced"}))
        self.assertTrue(fh.enforced_mode({"BM_FENCE_MODE": " ENFORCED "}))
        self.assertFalse(fh.enforced_mode({"BM_FENCE_MODE": "advisory"}))
        self.assertFalse(fh.enforced_mode({"BM_FENCE_MODE": "1"}))
        self.assertFalse(fh.enforced_mode({"BM_FENCE_MODE": ""}))
        self.assertFalse(fh.enforced_mode({}))


class Canonicalization(FenceHookBase):

    def setUp(self):
        FenceHookBase.setUp(self)
        self.mine = self.label(self.VICTIM)
        self.claim("api", ["src/app.py"], self.mine)

    def _denied(self, raw, cwd=None):
        p = payload(self.OTHER, cwd or self.root, tool_input={"file_path": raw})
        decision, notes = self.decide(p)
        self.assertIsNotNone(
            decision,
            "path %r reached the fenced file but was ALLOWED (notes: %r)"
            % (raw, notes))

    def test_dot_dot_traversal_is_resolved(self):
        self._denied("src/../src/app.py")
        self._denied("./src/./app.py")

    def test_absolute_path_is_resolved(self):
        self._denied(os.path.join(self.root, "src", "app.py"))

    def test_relative_path_from_a_subdirectory_is_resolved(self):
        self._denied("app.py", cwd=os.path.join(self.root, "src"))

    @unittest.skipIf(not hasattr(os, "symlink") or sys.platform == "win32",
                     "symlink creation needs privileges on Windows")
    def test_symlinked_path_is_resolved(self):
        link = os.path.join(self.root, "link.py")
        os.symlink(os.path.join(self.root, "src", "app.py"), link)
        self._denied("link.py")
        linkdir = os.path.join(self.root, "srclink")
        os.symlink(os.path.join(self.root, "src"), linkdir)
        self._denied("srclink/app.py")

    def test_path_outside_the_root_is_allowed(self):
        outside = os.path.realpath(tempfile.mkdtemp())
        try:
            p = payload(self.OTHER, self.root,
                        tool_input={"file_path": os.path.join(outside, "x.py")})
            decision, _n = self.decide(p)
            self.assertAllowed(decision)
        finally:
            shutil.rmtree(outside, ignore_errors=True)

    def test_directory_claim_covers_its_children(self):
        with bs.Store(self.root, create=False) as store:
            rec = store.claim("api", "ephemeral", files=["src"],
                              session_id=self.mine)
        self._denied("src/other.py")
        self._denied("src/deeper/new_file.py")

    def test_glob_claim_covers_a_concrete_file(self):
        with bs.Store(self.root, create=False) as store:
            store.claim("api", "ephemeral", files=["src/*.py"],
                        session_id=self.mine)
        self._denied("src/other.py")

    @unittest.skipIf(sys.platform not in ("darwin", "win32"),
                     "only normalization-insensitive filesystems fold NFC "
                     "and NFD onto one inode")
    def test_calibrated_unicode_normalization_is_not_a_bypass(self):
        """Regression, fix-round 2026-07-29, reproduced end to end before the
        fix: 'src/cafe.py' with an accented e claimed in NFC was ONE inode
        with the same name in NFD and TWO different strings, so a foreign
        session Editing the NFD spelling found covering=[], foreign=[], and
        the hook returned no decision, which is ALLOW. Appending through the
        NFD path really did add a line to the NFC-claimed file. That is a
        supported-tool bypass, not an arbitrary-shell limit."""
        nfc = unicodedata.normalize("NFC", "src/café_日本.py")
        nfd = unicodedata.normalize("NFD", "src/café_日本.py")
        self.assertNotEqual(nfc, nfd)
        with io.open(os.path.join(self.root, nfc), "w",
                     encoding="utf-8") as f:
            f.write("ORIG\n")
        with bs.Store(self.root, create=False) as store:
            store.claim("uni", "ephemeral", files=[nfc],
                        session_id=self.mine)
        for spelling in (nfc, nfd):
            decision, notes = self.decide(
                payload(self.OTHER, self.root,
                        tool_input={"file_path": spelling}))
            self.assertIsNotNone(
                decision,
                "%r was ALLOWED across the fence (notes: %r)"
                % (spelling, notes))
        # Restore half: the OWNER is still allowed either spelling, so the
        # fix denies the intruder without bricking the writer.
        for spelling in (nfc, nfd):
            decision, notes = self.decide(
                payload(self.VICTIM, self.root,
                        tool_input={"file_path": spelling}))
            self.assertIsNone(decision, notes)

    def test_a_file_that_does_not_exist_yet_is_still_fenced(self):
        """Write creates files. A fence that only worked on existing paths
        would be bypassed by creating the file first."""
        with bs.Store(self.root, create=False) as store:
            store.claim("api", "ephemeral", files=["src"], session_id=self.mine)
        p = payload(self.OTHER, self.root, tool_name="Write",
                    tool_input={"file_path": "src/brand_new.py", "content": "x"})
        decision, _n = self.decide(p)
        self.assertIsNotNone(decision)


# ---------------------------------------------------------------------------
# Tool surface.
# ---------------------------------------------------------------------------

class ToolSurface(FenceHookBase):

    def setUp(self):
        FenceHookBase.setUp(self)
        self.mine = self.label(self.VICTIM)
        self.claim("api", ["src"], self.mine)

    def test_non_write_tools_pass_through_silently(self):
        for tool in ("Read", "Grep", "Glob", "Bash", "WebFetch", "Task"):
            p = payload(self.OTHER, self.root, tool_name=tool,
                        tool_input={"file_path": "src/app.py"})
            decision, notes = self.decide(p)
            self.assertAllowed(decision)
            self.assertEqual(notes, [],
                             "%s must pass through with no stderr noise" % tool)

    def test_every_write_tool_is_gated(self):
        cases = {
            "Edit": {"file_path": "src/app.py"},
            "Write": {"file_path": "src/app.py", "content": "x"},
            "MultiEdit": {"file_path": "src/app.py", "edits": [{"old_string": "a"}]},
            "NotebookEdit": {"notebook_path": "src/nb.ipynb", "new_source": "x"},
        }
        for tool, ti in cases.items():
            p = payload(self.OTHER, self.root, tool_name=tool, tool_input=ti)
            decision, notes = self.decide(p)
            self.assertIsNotNone(decision, "%s was not gated (%r)" % (tool, notes))

    def test_nested_per_edit_paths_are_extracted(self):
        """A MultiEdit-shaped payload whose per-edit entries carry their own
        file_path must not be reduced to the top-level path alone: the fence
        would then be bypassed by putting the fenced file in edits[1]."""
        p = payload(self.OTHER, self.root, tool_name="MultiEdit",
                    tool_input={"file_path": "README.md",
                                "edits": [{"file_path": "src/app.py",
                                           "old_string": "a", "new_string": "b"}]})
        decision, _n = self.decide(p)
        self.assertIsNotNone(decision)

    def test_extract_targets_is_bounded(self):
        """A hostile payload must not make the hook recurse or scan forever:
        it runs in front of EVERY edit."""
        deep = {"file_path": "a.py"}
        node = deep
        for _ in range(200):
            node = {"nested": node}
        got = fh.extract_targets(node)
        self.assertEqual(got, [], "depth must be bounded")
        wide = {"edits": [{"file_path": "f%d.py" % i} for i in range(500)]}
        self.assertLessEqual(len(fh.extract_targets(wide)), 64)


# ---------------------------------------------------------------------------
# Strict mode (opt in): claim before edit.
# ---------------------------------------------------------------------------

class StrictMode(FenceHookBase):

    def test_strict_mode_denies_an_unclaimed_path(self):
        self.claim("api", ["src/app.py"], self.label(self.VICTIM))
        p = payload(self.VICTIM, self.root, tool_input={"file_path": "src/other.py"})
        with mock.patch.dict(os.environ, {"BM_FENCE_STRICT": "1"}):
            decision, _n = self.decide(p)
        reason = self.assertDenied(decision)
        self.assertIn("strict mode", reason)
        self.assertIn("claim", reason)

    def test_strict_mode_still_allows_the_owner(self):
        self.claim("api", ["src/app.py"], self.label(self.VICTIM))
        with mock.patch.dict(os.environ, {"BM_FENCE_STRICT": "1"}):
            decision, _n = self.decide(payload(self.VICTIM, self.root))
        self.assertAllowed(decision)

    def test_strict_mode_cannot_override_the_fail_open(self):
        """Strict mode is a tightening, never a way to turn a broken store
        into a refusal: the fail-open rule outranks it."""
        with mock.patch.dict(os.environ, {"BM_FENCE_STRICT": "1"}):
            decision, notes = self.decide(payload(self.VICTIM, self.root))
        self.assertAllowed(decision)
        self.assertTrue(any("no active claims" in n for n in notes), notes)

    def test_strict_mode_is_off_by_default(self):
        self.claim("api", ["src/app.py"], self.label(self.VICTIM))
        p = payload(self.VICTIM, self.root, tool_input={"file_path": "src/other.py"})
        decision, _n = self.decide(p)
        self.assertAllowed(decision)


# ---------------------------------------------------------------------------
# The wire protocol: stdout is the decision channel and nothing else.
# ---------------------------------------------------------------------------

class WireProtocol(FenceHookBase):

    def test_deny_shape_matches_the_documented_contract(self):
        """Field for field against the PreToolUse decision-control block in
        https://code.claude.com/docs/en/hooks, read 2026-07-27. A hook that
        emits a nearly-right object is silently ignored, which is a fence
        that reports success it did not earn."""
        self.claim("api", ["src/app.py"], self.label(self.VICTIM))
        r = self.run_hook(payload(self.OTHER, self.root))
        self.assertEqual(r.returncode, 0,
                         "deny is exit 0 with JSON on stdout, never exit 2")
        obj = json.loads(r.stdout)
        self.assertEqual(list(obj.keys()), ["hookSpecificOutput"])
        hso = obj["hookSpecificOutput"]
        self.assertEqual(hso["hookEventName"], "PreToolUse")
        self.assertEqual(hso["permissionDecision"], "deny")
        self.assertIsInstance(hso["permissionDecisionReason"], str)
        self.assertTrue(hso["permissionDecisionReason"].strip())
        self.assertEqual(sorted(hso.keys()),
                         ["hookEventName", "permissionDecision",
                          "permissionDecisionReason"])

    def test_allow_emits_nothing_on_stdout(self):
        self.claim("api", ["src/app.py"], self.label(self.VICTIM))
        r = self.run_hook(payload(self.VICTIM, self.root))
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout, "")

    def test_stdout_is_never_polluted_by_diagnostics(self):
        r = self.run_hook(payload(self.VICTIM, self.root))
        self.assertEqual(r.stdout, "")
        self.assertIn("FAILING OPEN", r.stderr)

    def test_empty_and_invalid_stdin_fail_open(self):
        for raw in ("", "   ", "not json", "{", "[1,2,3"):
            r = subprocess.run([sys.executable, HOOK_PATH], input=raw, text=True,
                               capture_output=True, cwd=self.root,
                               env=_clean_env())
            self.assertEqual(r.returncode, 0, raw)
            self.assertEqual(r.stdout, "", raw)
            self.assertIn("FAILING OPEN", r.stderr, raw)

    def test_session_label_subcommand_reads_every_documented_source(self):
        want = self.label(self.VICTIM)
        r = subprocess.run([sys.executable, HOOK_PATH, "session-label",
                            "--session-id", self.VICTIM],
                           capture_output=True, text=True, cwd=self.root,
                           env=_clean_env())
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), want)
        r = subprocess.run([sys.executable, HOOK_PATH, "session-label"],
                           capture_output=True, text=True, cwd=self.root,
                           env=_clean_env({"BM_FENCE_SESSION_ID": self.VICTIM}))
        self.assertEqual(r.stdout.strip(), want)
        r = subprocess.run([sys.executable, HOOK_PATH, "session-label"],
                           input=json.dumps({"session_id": self.VICTIM}),
                           text=True, capture_output=True, cwd=self.root,
                           env=_clean_env())
        self.assertEqual(r.stdout.strip(), want)

    def test_session_label_refuses_rather_than_inventing_an_identity(self):
        r = subprocess.run([sys.executable, HOOK_PATH, "session-label"],
                           input="", text=True, capture_output=True,
                           cwd=self.root, env=_clean_env())
        self.assertEqual(r.returncode, 2)
        self.assertEqual(r.stdout, "")
        self.assertIn("no session id", r.stderr)

    def test_unknown_subcommand_refuses(self):
        r = subprocess.run([sys.executable, HOOK_PATH, "wat"], input="{}",
                           text=True, capture_output=True, cwd=self.root,
                           env=_clean_env())
        self.assertEqual(r.returncode, 2)
        self.assertIn("unknown command", r.stderr)


# ---------------------------------------------------------------------------
# Cost: this runs before EVERY edit.
# ---------------------------------------------------------------------------

class Cost(FenceHookBase):

    def test_decision_is_cheap_with_a_realistic_fence(self):
        import time
        mine = self.label(self.VICTIM)
        with bs.Store(self.root, create=False) as store:
            for i in range(20):
                store.claim("rec%d" % i, "ephemeral",
                            files=["area%d/*.py" % i], session_id=mine)
        p = payload(self.OTHER, self.root,
                    tool_input={"file_path": "src/app.py"})
        self.decide(p)
        t0 = time.perf_counter()
        for _ in range(50):
            self.decide(p)
        per_call_ms = (time.perf_counter() - t0) / 50 * 1000.0
        self.assertLess(per_call_ms, 50.0,
                        "decide() took %.2f ms per call with 20 active "
                        "records; it runs in front of every edit" % per_call_ms)


# ---------------------------------------------------------------------------
# Structural rules this repo enforces on itself.
# ---------------------------------------------------------------------------

class Structural(unittest.TestCase):

    FILES = (HOOK_PATH, os.path.abspath(__file__), DOCS_PATH)

    def test_no_em_or_en_dashes_anywhere(self):
        # Built from code points, never written literally: a test that
        # contained the characters it forbids would fail on itself.
        forbidden = {"em dash": chr(0x2014), "en dash": chr(0x2013)}
        for path in self.FILES:
            if not os.path.exists(path):
                continue
            text = io.open(path, encoding="utf-8").read()
            for i, line in enumerate(text.splitlines(), 1):
                for label, ch in forbidden.items():
                    self.assertNotIn(ch, line, "%s at %s:%d" % (label, path, i))

    def test_stdout_has_exactly_one_writer(self):
        """The decision channel discipline, enforced structurally rather than
        by memory: a bare print() added later would silently corrupt the hook
        protocol by putting non-JSON on stdout."""
        lines = io.open(HOOK_PATH, encoding="utf-8").read().splitlines()
        pat = re.compile(r"\bprint\(|sys\.stdout\.write")
        hits = [i for i, l in enumerate(lines, 1)
                if not l.lstrip().startswith("#") and pat.search(l)]
        self.assertEqual(
            len(hits), 1,
            "expected exactly one stdout writer (inside _out); found %d at "
            "lines %s" % (len(hits), hits))

    def test_docs_hooks_md_exists_and_states_the_residual_limit(self):
        self.assertTrue(os.path.exists(DOCS_PATH),
                        "docs/HOOKS.md must document installation")
        text = io.open(DOCS_PATH, encoding="utf-8").read()
        for fragment in ("PreToolUse", "permissionDecision", "settings.json",
                         "determined local attacker", "bm_store.py"):
            self.assertIn(fragment, text,
                          "docs/HOOKS.md must mention %r" % fragment)
        lower = text.lower()
        # The two claims a reader must not have to infer: the fail-open policy,
        # and the honest residual limit on identity.
        self.assertIn("fail open", lower)
        self.assertIn("any process running as this user can read the token",
                      lower)

    def test_the_hook_never_opens_the_store_writably(self):
        """A gate that runs in front of every edit must have no authority to
        change what it is reading. Constructing bs.Store() would give this
        file the quarantine path, which can MOVE the founder's database on a
        transient disk error; ReadOnlyStore has no route to that code at all.
        Enforced structurally so a later edit cannot reintroduce it quietly."""
        text = io.open(HOOK_PATH, encoding="utf-8").read()
        lines = [l for l in text.splitlines()
                 if not l.lstrip().startswith("#")]
        body = "\n".join(lines)
        self.assertIn("ReadOnlyStore", body)
        self.assertNotIn(".Store(", body,
                         "the fence hook must never construct a writable Store")
        for writer in ("init_project(", "write_state_view(", "_atomic_write_text("):
            self.assertNotIn(writer, body,
                             "the fence hook must not call %s" % writer)


class _LeakCheckingResult(unittest.TextTestResult):
    """Same mechanical stop tools/test_bm_store.py uses: a store opened and
    never closed passes on POSIX and fails on Windows, where an open handle
    blocks the directory removal. The hook opens a ReadOnlyStore on every
    single decision, so this is exactly the file that must not leak."""

    def startTest(self, test):
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
            self.addFailure(test, (AssertionError, AssertionError(
                "%d store(s) were opened by this test and never closed "
                "(Windows-only failure class). Path(s): %s"
                % (len(still_open), ", ".join(paths))), None))
        super(_LeakCheckingResult, self).stopTest(test)


if __name__ == "__main__":
    unittest.main(
        verbosity=2,
        testRunner=unittest.TextTestRunner(verbosity=2,
                                           resultclass=_LeakCheckingResult))
