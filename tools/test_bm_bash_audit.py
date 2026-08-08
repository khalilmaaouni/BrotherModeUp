#!/usr/bin/env python3
"""Regression tests for tools/bm_bash_audit.py, the PreToolUse/PostToolUse
Bash-write DETECTION pair (Loop 6 design D-1, docs/superpowers/specs/
2026-08-01-loop6-security-closure-design.md). Standard library only.
Run: python3 tools/test_bm_bash_audit.py

Same discipline as tools/test_bm_fence_hook.py: every test is self-contained
under tempfile.TemporaryDirectory(), scrubs BROTHERMODE_ROOT and the fence
env vars out of every subprocess it spawns, points BROTHERME_CONFIG at a
throwaway consented config (or deliberately away from one), and never
touches this repo's own files, store, or home directory.

D-4's demonstration set, one test method per letter, is the spine of this
file:
  (a) a foreign-session Bash write to a fenced path raises exactly one
      high-severity fence-breach alert row, the path readable back through
      the store, masked per export policy (no absolute machine path in it).
  (b) the fence OWNER's own Bash write raises nothing.
  (c) an unfenced path changing raises nothing.
  (d) pre-consent runs write nothing at all, proven by a tree walk before
      and after both the PreToolUse and the PostToolUse phase.
  (e) a corrupt or a missing snapshot file fails open, prints a reason,
      exits 0, and raises no alert.

C-02 (2026-08-03) adds two classes below D-4's spine:
  EnforcedModeRefusesStoreDestruction, one test per mutation form the
  closure register's reproduction used, each asserting BOTH directions on
  that form (refused under BM_FENCE_MODE=enforced INSIDE A BROTHERMODE
  PROJECT, allowed under the default, and also allowed under enforced mode
  OUTSIDE a BrotherMode project, since this hook installs at user-global
  scope and must stay inert everywhere else), and ControlStateLossIsDetected,
  which covers the silence itself: a shell command that removes the store or
  a session token used to produce no output and no alert row at all, because
  the store is not a claimed path and nothing in the hook looked at it.
"""
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK_PATH = os.path.join(HERE, "bm_bash_audit.py")
STORE_PATH = os.path.join(HERE, "bm_store.py")
FENCE_PATH = os.path.join(HERE, "bm_fence_hook.py")

import importlib.util

_spec = importlib.util.spec_from_file_location("bm_store", STORE_PATH)
bs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bs)
sys.modules["bm_store"] = bs

_fspec = importlib.util.spec_from_file_location("bm_fence_hook", FENCE_PATH)
fh = importlib.util.module_from_spec(_fspec)
_fspec.loader.exec_module(fh)
sys.modules["bm_fence_hook"] = fh

_aspec = importlib.util.spec_from_file_location("bm_bash_audit", HOOK_PATH)
ba = importlib.util.module_from_spec(_aspec)
_aspec.loader.exec_module(ba)
sys.modules["bm_bash_audit"] = ba


def _write_consented_config(path, vault_path=None):
    """Matches scripts/setup.py's write_config() schema exactly, the same
    fixture tools/test_bm_autosave.py's _write_consented_config uses: this
    hook's consent gate reads the identical config through the identical
    scripts/setup.py loader."""
    with io.open(path, "w", encoding="utf-8") as f:
        json.dump({"setup_complete": True,
                  "vault_path": vault_path or os.path.dirname(path),
                  "privacy_notice_version": "2026-08-01",
                  "installation_mode": "clone",
                  "security_mode": "standard"}, f)


class BashAuditBase(unittest.TestCase):
    """A throwaway project with a store, a src/ tree, and two sessions."""

    OWNER = "sess-owner-0001"
    OTHER = "sess-other-0002"

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        # realpath up front: on macOS /var and /tmp are symlinks, and every
        # comparison bm_bash_audit.py and bm_fence_hook.py make is against a
        # realpath'd root.
        self.root = os.path.realpath(self._tmp.name)
        os.makedirs(os.path.join(self.root, ".git"))
        os.makedirs(os.path.join(self.root, "src"))
        for name in ("mine.txt", "other.py"):
            with io.open(os.path.join(self.root, "src", name), "w",
                         encoding="utf-8") as f:
                f.write("original %s\n" % name)
        with bs.Store(self.root) as store:
            pass

        self._cfg_dir = tempfile.TemporaryDirectory()
        self.cfg_path = os.path.join(self._cfg_dir.name, "config.json")
        _write_consented_config(self.cfg_path)

        self._env_patch = mock.patch.dict(os.environ, {}, clear=False)
        self._env_patch.start()
        for k in ("BROTHERMODE_ROOT", "BM_FENCE_STRICT", "BM_FENCE_SESSION_ID",
                  "BM_FENCE_MODE"):
            os.environ.pop(k, None)
        os.environ["BROTHERME_CONFIG"] = self.cfg_path

    def tearDown(self):
        self._env_patch.stop()
        self._cfg_dir.cleanup()
        self._tmp.cleanup()

    # -- helpers ---------------------------------------------------------

    def label(self, session_id):
        return fh.session_label(self.root, session_id)

    def claim(self, name, files, session_id_label):
        with bs.Store(self.root, create=False) as store:
            rec = store.claim(name, "ephemeral", objective="bash audit test",
                              files=files, session_id=session_id_label)
        # The CLI refreshes the generated view after every mutation; the
        # Python API does not, matching test_bm_fence_hook.py's own claim().
        bs.write_state_view(self.root)
        return rec

    def write_file(self, rel_path, text):
        with io.open(os.path.join(self.root, *rel_path.split("/")), "w",
                     encoding="utf-8") as f:
            f.write(text)

    def run_hook(self, phase, session_id, tool_use_id="toolu_01TEST",
                consented=True, command="echo hi", env_extra=None,
                cwd_override=None):
        """Run bm_bash_audit.py exactly as Claude Code would: a bare
        subcommand (pre or post) with a JSON hook payload on stdin.

        `command` is the shell command the payload carries, which every test
        before C-02 left at the harmless default; `env_extra` sets variables
        for that one run (BM_FENCE_MODE, for the enforced-mode half).
        `cwd_override`, also added for C-02, lets a test claim the hook is
        running from a directory that is NOT this fixture's BrotherMode
        project, to prove the refusal stays inert there; every test before
        C-02, and every C-02 test but that one, leaves it unset and gets
        self.root exactly as before."""
        payload_cwd = cwd_override if cwd_override is not None else self.root
        payload = json.dumps({
            "session_id": session_id,
            "transcript_path": os.path.join(self.root, "transcript.jsonl"),
            "cwd": payload_cwd,
            "permission_mode": "default",
            "hook_event_name": "PreToolUse" if phase == "pre" else "PostToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": command},
            "tool_use_id": tool_use_id,
        })
        env = dict(os.environ)
        env.update(env_extra or {})
        if not consented:
            env.pop("BROTHERME_CONFIG", None)
            env["BROTHERME_CONFIG"] = os.path.join(
                self._tmp.name, "no-such-config.json")
        return subprocess.run(
            [sys.executable, HOOK_PATH, phase], input=payload, text=True,
            capture_output=True, cwd=payload_cwd, env=env)

    def alerts(self, raw=True):
        with bs.Store(self.root, create=False) as store:
            return store.list_alerts(raw=raw)

    def bash_audit_attribution(self, raw=True):
        """Every attribution row filed under this hook's own project id
        (ba.ALERT_PROJECT_ID), so a test can confirm WHO an alert was
        attributed to (A5: the actor_name on the alert.raised event),
        not merely that an alert row exists."""
        with bs.Store(self.root, create=False) as store:
            return store.list_attribution(ba.ALERT_PROJECT_ID, limit=1000,
                                          raw=raw)

    def verify(self):
        """`python3 tools/bm_store.py verify` against this fixture's store,
        run exactly as a founder runs it: the real CLI, in a subprocess,
        with the project root as cwd. A CompletedProcess, so a test can
        assert on the exit code AND the sentence, since verify says
        "healthy, 0 problem(s)" on stdout and exits 0 only when it means
        it."""
        return subprocess.run(
            [sys.executable, STORE_PATH, "verify"],
            text=True, capture_output=True, cwd=self.root)

    def projects(self, include_system=False):
        with bs.Store(self.root, create=False) as store:
            return store.list_projects(raw=True, include_system=include_system)

    def snapshot_path(self, session_id, tool_use_id):
        return ba.snapshot_path(self.root, bs, session_id, tool_use_id)

    def tree_listing(self):
        """Every relative file path under the project root, sorted. A tree
        WALK, per D-4(d)'s own wording: proves nothing new landed on disk,
        not merely that one guessed location stayed empty."""
        out = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames.sort()
            rel_dir = os.path.relpath(dirpath, self.root)
            for fn in sorted(filenames):
                out.append(os.path.normpath(os.path.join(rel_dir, fn)))
        return sorted(out)


# ---------------------------------------------------------------------------
# D-4: the demonstration set, one method per letter.
# ---------------------------------------------------------------------------

class TestD4Demonstration(BashAuditBase):

    def test_a_foreign_session_write_raises_exactly_one_alert(self):
        owner = self.label(self.OWNER)
        rec = self.claim("mine", ["src/mine.txt"], owner)

        r1 = self.run_hook("pre", self.OTHER)
        self.assertEqual(r1.returncode, 0, r1.stderr)
        self.assertEqual(r1.stdout, "", "the hook must never print to stdout")

        self.write_file("src/mine.txt", "tampered by a foreign session\n")

        r2 = self.run_hook("post", self.OTHER)
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertEqual(r2.stdout, "", "the hook must never print to stdout")
        self.assertIn("fence-breach alert was raised", r2.stderr,
                      "the required one plain stderr sentence is missing")

        rows = self.alerts(raw=True)
        self.assertEqual(len(rows), 1, rows)
        row = rows[0]
        self.assertEqual(row["severity"], "high")
        self.assertEqual(row["category"], "fence-breach")
        self.assertTrue(row["requires_human"])
        self.assertIn("src/mine.txt", row["message"])
        self.assertIn(rec.lifecycle_uuid, row["message"])
        # "masked per export policy": the message must name the fenced path
        # by its safe, root-relative form (exactly how bm_store's own
        # export policy treats claims.path, a scrub-only column) and never
        # by this test's own absolute temp-directory path, which would leak
        # this machine's real filesystem layout into a stored row.
        self.assertNotIn(self.root, row["message"],
                         "the alert message leaked the absolute project "
                         "root; the path must be masked, not verbatim")

        # A5 (loop6 refuter finding): the alert must be attributed to THIS
        # hook by name, not merely exist. Without this check, an alert
        # raised by any other actor would pass the assertions above too.
        raised = [e for e in self.bash_audit_attribution()
                  if e.get("event_type") == "alert.raised"]
        self.assertEqual(len(raised), 1, raised)
        self.assertEqual(raised[0]["actor_name"], "bm_bash_audit",
                         "the alert.raised event must name bm_bash_audit "
                         "as its actor, not be blank or attributed to "
                         "something else")

        # A non-raw read must not crash and must still carry the structural
        # (non-founder-prose) columns the export policy always shows.
        plain = self.alerts(raw=False)
        self.assertEqual(len(plain), 1)
        self.assertEqual(plain[0]["severity"], "high")
        self.assertEqual(plain[0]["category"], "fence-breach")

    def test_b_owners_own_bash_write_raises_nothing(self):
        owner = self.label(self.OWNER)
        self.claim("mine", ["src/mine.txt"], owner)

        r1 = self.run_hook("pre", self.OWNER, tool_use_id="toolu_owner")
        self.assertEqual(r1.returncode, 0, r1.stderr)

        self.write_file("src/mine.txt", "changed by the owner\n")

        r2 = self.run_hook("post", self.OWNER, tool_use_id="toolu_owner")
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertNotIn("fence-breach", r2.stderr)
        self.assertEqual(self.alerts(), [])

    def test_c_unfenced_path_change_raises_nothing(self):
        owner = self.label(self.OWNER)
        # Only src/mine.txt is fenced; src/other.py is not.
        self.claim("mine", ["src/mine.txt"], owner)

        r1 = self.run_hook("pre", self.OTHER, tool_use_id="toolu_unfenced")
        self.assertEqual(r1.returncode, 0, r1.stderr)

        self.write_file("src/other.py", "changed, but never fenced\n")

        r2 = self.run_hook("post", self.OTHER, tool_use_id="toolu_unfenced")
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertNotIn("fence-breach", r2.stderr)
        self.assertEqual(self.alerts(), [])

    def test_d_pre_consent_writes_nothing_at_all(self):
        owner = self.label(self.OWNER)
        self.claim("mine", ["src/mine.txt"], owner)

        before = self.tree_listing()
        r1 = self.run_hook("pre", self.OTHER, tool_use_id="toolu_noconsent",
                           consented=False)
        self.assertEqual(r1.returncode, 0, r1.stderr)
        self.assertIn("setup is not complete", r1.stderr)
        after_pre = self.tree_listing()
        self.assertEqual(before, after_pre,
                         "the PreToolUse phase wrote something pre-consent")
        self.assertFalse(
            os.path.isdir(os.path.join(self.root, ".brothermode", "bash-audit")),
            "a snapshot directory was created pre-consent")

        # Even a Bash write that WOULD have been a breach must not be acted
        # on: nothing was snapshotted, and post must still write nothing.
        self.write_file("src/mine.txt", "tampered while unconsented\n")
        after_write = self.tree_listing()

        r2 = self.run_hook("post", self.OTHER, tool_use_id="toolu_noconsent",
                           consented=False)
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertIn("setup is not complete", r2.stderr)
        after_post = self.tree_listing()
        self.assertEqual(after_write, after_post,
                         "the PostToolUse phase wrote something pre-consent")
        self.assertEqual(self.alerts(), [])

    def test_e_missing_snapshot_fails_open(self):
        owner = self.label(self.OWNER)
        self.claim("mine", ["src/mine.txt"], owner)

        # No "pre" ever ran for this tool_use_id, so the snapshot simply
        # does not exist.
        r = self.run_hook("post", self.OTHER, tool_use_id="toolu_never_pre")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("FAILING OPEN", r.stderr)
        self.assertIn("no snapshot was recorded", r.stderr)
        self.assertEqual(self.alerts(), [])

    def test_e_corrupt_snapshot_fails_open(self):
        owner = self.label(self.OWNER)
        self.claim("mine", ["src/mine.txt"], owner)

        r1 = self.run_hook("pre", self.OTHER, tool_use_id="toolu_corrupt")
        self.assertEqual(r1.returncode, 0, r1.stderr)
        spath = self.snapshot_path(self.OTHER, "toolu_corrupt")
        self.assertTrue(os.path.isfile(spath), "the pre phase wrote no snapshot")
        with io.open(spath, "w", encoding="utf-8") as f:
            f.write("{ this is not valid json")

        self.write_file("src/mine.txt", "tampered after corruption\n")

        r2 = self.run_hook("post", self.OTHER, tool_use_id="toolu_corrupt")
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertIn("FAILING OPEN", r2.stderr)
        self.assertEqual(self.alerts(), [])

    def test_f_store_missing_at_post_leaves_the_snapshot_for_a_retry(self):
        """A3 (loop6 refuter finding): the snapshot used to be removed
        BEFORE the comparison and before the store-existence check, so a
        post phase that could not reach the store lost its baseline with no
        way to retry. The removal must happen only after a comparison that
        actually completes; any early-return or failure path, including
        this one, must leave the snapshot exactly where it was."""
        owner = self.label(self.OWNER)
        self.claim("mine", ["src/mine.txt"], owner)

        r1 = self.run_hook("pre", self.OTHER, tool_use_id="toolu_nostore")
        self.assertEqual(r1.returncode, 0, r1.stderr)
        spath = self.snapshot_path(self.OTHER, "toolu_nostore")
        self.assertTrue(os.path.isfile(spath), "the pre phase wrote no snapshot")

        self.write_file("src/mine.txt", "tampered while the store is gone\n")

        # Renamed aside temporarily so the post phase cannot reach the
        # store, then restored. This happens entirely inside self.root (a
        # tempfile.TemporaryDirectory, never this checkout), so it is not
        # the checkout-mutation hazard tools/test_bm.py's
        # test_no_suite_renames_a_module_aside guards against.
        store_path = os.path.join(self.root, ".brothermode", "store.sqlite3")
        stashed = store_path + ".stashed-during-test"
        os.rename(store_path, stashed)
        try:
            r2 = self.run_hook("post", self.OTHER, tool_use_id="toolu_nostore")
        finally:
            os.rename(stashed, store_path)
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertIn("FAILING OPEN", r2.stderr)
        self.assertTrue(
            os.path.isfile(spath),
            "the snapshot was removed even though the store could not be "
            "reached; a retry now has nothing to compare against")


# ---------------------------------------------------------------------------
# A4 (loop6 refuter finding): age-based reaping of orphaned snapshots.
# ---------------------------------------------------------------------------

class TestSnapshotReaper(BashAuditBase):

    def test_pre_phase_reaps_snapshots_older_than_the_ttl(self):
        """An orphaned snapshot (a Bash call that was denied, a hook
        timeout, a session killed mid-call) never gets a matching
        PostToolUse, so nothing ever cleaned it up before, and each one
        holds paths plus digests of every fenced file, unbounded. The pre
        phase now reaps anything older than the stated TTL at its own
        start, best effort, and leaves a fresh snapshot from another
        session alone."""
        owner = self.label(self.OWNER)
        self.claim("mine", ["src/mine.txt"], owner)

        stale_path = self.snapshot_path("sess-stale-0000", "toolu_stale")
        os.makedirs(os.path.dirname(stale_path), exist_ok=True)
        with io.open(stale_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"schema": 1, "entries": []}))
        old = time.time() - ba.SNAPSHOT_TTL_SECONDS - 3600
        os.utime(stale_path, (old, old))

        fresh_path = self.snapshot_path("sess-fresh-0000", "toolu_fresh")
        with io.open(fresh_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"schema": 1, "entries": []}))

        r = self.run_hook("pre", self.OTHER, tool_use_id="toolu_reap_trigger")
        self.assertEqual(r.returncode, 0, r.stderr)

        self.assertFalse(os.path.isfile(stale_path),
                         "an aged, orphaned snapshot was not reaped")
        self.assertTrue(os.path.isfile(fresh_path),
                        "a fresh snapshot from another session was reaped "
                        "too; the reaper must be age-based, not blanket")


# ---------------------------------------------------------------------------
# Supplementary coverage, cheap given the fixtures above, beyond the D-4
# minimum: multiple breaches in one call, and the two output-discipline
# rules (stdout reserved, exit 0 always).
# ---------------------------------------------------------------------------

class TestSupplementary(BashAuditBase):

    def test_two_foreign_writes_in_one_call_raise_two_alerts(self):
        owner = self.label(self.OWNER)
        self.claim("mine", ["src/mine.txt"], owner)
        self.claim("theirs", ["src/other.py"], owner)

        r1 = self.run_hook("pre", self.OTHER, tool_use_id="toolu_multi")
        self.assertEqual(r1.returncode, 0, r1.stderr)
        self.write_file("src/mine.txt", "tampered one\n")
        self.write_file("src/other.py", "tampered two\n")
        r2 = self.run_hook("post", self.OTHER, tool_use_id="toolu_multi")
        self.assertEqual(r2.returncode, 0, r2.stderr)

        rows = self.alerts(raw=True)
        self.assertEqual(len(rows), 2, rows)
        paths_named = " ".join(r["message"] for r in rows)
        self.assertIn("src/mine.txt", paths_named)
        self.assertIn("src/other.py", paths_named)

    def test_a_read_only_bash_call_never_exits_nonzero(self):
        """This hook is detection, not prevention: an ordinary, harmless
        Bash call must never see a nonzero exit from either phase."""
        owner = self.label(self.OWNER)
        self.claim("mine", ["src/mine.txt"], owner)
        r1 = self.run_hook("pre", self.OTHER, tool_use_id="toolu_readonly")
        r2 = self.run_hook("post", self.OTHER, tool_use_id="toolu_readonly")
        self.assertEqual((r1.returncode, r2.returncode), (0, 0))
        self.assertEqual(self.alerts(), [])

    def test_no_active_claims_fails_open_and_writes_nothing(self):
        """No store-wide active claims at all: the same fail-open reason
        tools/bm_fence_hook.py itself gives (nothing is fenced, so there is
        nothing to check), and nothing is written."""
        before = self.tree_listing()
        r = self.run_hook("pre", self.OTHER, tool_use_id="toolu_noclaims")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("FAILING OPEN", r.stderr)
        self.assertIn("no active claims", r.stderr)
        self.assertEqual(self.tree_listing(), before)


# ---------------------------------------------------------------------------
# C-02, the ALERT half: a shell command that destroys the enforcement state
# itself used to produce no output and no row at all, because the store is
# not a claimed path and nothing here looked at it.
# ---------------------------------------------------------------------------

class ControlStateLossIsDetected(BashAuditBase):

    def test_a_removed_session_token_raises_an_alert_row(self):
        owner = self.label(self.OWNER)
        self.claim("mine", ["src/mine.txt"], owner)
        token = fh.token_path(self.root, self.OWNER)
        self.assertTrue(os.path.isfile(token), "no owner token to remove")

        r1 = self.run_hook("pre", self.OTHER, tool_use_id="toolu_token")
        self.assertEqual(r1.returncode, 0, r1.stderr)

        os.remove(token)

        r2 = self.run_hook("post", self.OTHER, tool_use_id="toolu_token")
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertEqual(r2.stdout, "", "the post phase must never print to "
                                        "stdout")
        self.assertIn("DETECTED a change to BrotherMode's own enforcement "
                      "state", r2.stderr)
        self.assertIn("fence-control-loss alert was raised", r2.stderr)

        rows = self.alerts(raw=True)
        self.assertEqual(len(rows), 1, rows)
        self.assertEqual(rows[0]["category"], "fence-control-loss")
        self.assertEqual(rows[0]["severity"], "high")
        self.assertTrue(rows[0]["requires_human"])
        self.assertNotIn(self.root, rows[0]["message"])

        raised = [e for e in self.bash_audit_attribution()
                  if e.get("event_type") == "alert.raised"]
        self.assertEqual(len(raised), 1, raised)
        self.assertEqual(raised[0]["actor_name"], "bm_bash_audit")

    def test_a_deleted_store_is_still_announced_even_though_unrecordable(self):
        """The C-02 reproduction's first command. The alert row cannot exist,
        because the thing that would hold it is what was destroyed, so the
        stderr line is the whole record and it has to be there."""
        owner = self.label(self.OWNER)
        self.claim("mine", ["src/mine.txt"], owner)

        r1 = self.run_hook("pre", self.OTHER, tool_use_id="toolu_delstore")
        self.assertEqual(r1.returncode, 0, r1.stderr)

        for suffix in ("", "-wal", "-shm"):
            p = bs.store_path(self.root) + suffix
            if os.path.exists(p):
                os.remove(p)

        r2 = self.run_hook("post", self.OTHER, tool_use_id="toolu_delstore")
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertIn("is gone after it", r2.stderr)
        self.assertIn("could NOT be recorded as an alert", r2.stderr)

    def test_ordinary_store_growth_between_the_phases_is_not_an_alert(self):
        """The coarseness is deliberate: a Bash call that runs bm_store.py is
        ordinary work, and a check that alarmed on it would be turned off."""
        owner = self.label(self.OWNER)
        self.claim("mine", ["src/mine.txt"], owner)

        r1 = self.run_hook("pre", self.OTHER, tool_use_id="toolu_growth")
        self.assertEqual(r1.returncode, 0, r1.stderr)

        self.claim("second", ["src/other.py"], owner)

        r2 = self.run_hook("post", self.OTHER, tool_use_id="toolu_growth")
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertNotIn("enforcement state", r2.stderr)
        self.assertEqual(self.alerts(), [])

    def test_a_breach_is_announced_before_it_is_recorded(self):
        """Ordering, not decoration: the detection sentence used to be
        printed only after the alert row was written, so a detection that
        could not be recorded was announced by nothing specific at all."""
        owner = self.label(self.OWNER)
        self.claim("mine", ["src/mine.txt"], owner)
        r1 = self.run_hook("pre", self.OTHER, tool_use_id="toolu_order")
        self.assertEqual(r1.returncode, 0, r1.stderr)
        self.write_file("src/mine.txt", "tampered\n")
        r2 = self.run_hook("post", self.OTHER, tool_use_id="toolu_order")
        self.assertEqual(r2.returncode, 0, r2.stderr)
        detected = r2.stderr.index("DETECTED a Bash write across a fence")
        recorded = r2.stderr.index("fence-breach alert was raised")
        self.assertLess(detected, recorded)


# ---------------------------------------------------------------------------
# 2026-08-08: the alert path leaves the store HEALTHY, not merely written to.
#
# The defect these tests exist for: ba.ALERT_PROJECT_ID was a constant nothing
# anywhere created. An alert's attribution event names a project, and
# attribution.project_id carries no REFERENCES clause on purpose (bm_store.py
# _LOOP1_DDL's comment says why), so the write succeeded and `bm_store.py
# verify` reported "attribution event <id> references missing project
# 'brothermode-bash-audit'" from then on, forever. That single problem turned
# doctor check 7 red, which turned test_brothermode_cli.py red, which turned
# test_all.py red on every machine in the repo.
#
# EVERY EXISTING TEST IN THIS FILE PASSED THROUGHOUT. They asserted the alert
# row, its severity, its category, its message and its actor, and never once
# asked whether the store was still consistent afterwards. This fixture never
# creates a project either, which is exactly the real, first-alert-on-a-fresh
# -machine case, so the bug was not merely unnoticed: it was reproduced by
# every run and inspected by none. That is the lesson of section 5.3 in
# docs/HANDOVER-2026-08-02-full-auto-phase1.md written out again, so the
# check is now the last thing the alert path is asked for: verify, clean.
# ---------------------------------------------------------------------------

class TheAlertPathLeavesTheStoreHealthy(BashAuditBase):

    def _breach(self, slug="toolu_health", claim=True):
        """One foreign-session Bash write across a fence, end to end through
        the real hook. Returns the post phase's CompletedProcess.

        claim=False reuses the fence an earlier call already made: a second
        claim on the same path is refused as an overlap, correctly, so a
        test wanting a SECOND breach across the SAME fence must not ask for
        one."""
        owner = self.label(self.OWNER)
        if claim:
            self.claim("mine-" + slug, ["src/mine.txt"], owner)
        r1 = self.run_hook("pre", self.OTHER, tool_use_id=slug)
        self.assertEqual(r1.returncode, 0, r1.stderr)
        # The content includes the slug: detection is a hash comparison, so
        # a second breach writing the SAME bytes as the first would be a
        # file that did not change and would correctly raise nothing.
        self.write_file("src/mine.txt",
                        "tampered by a foreign session (%s)\n" % slug)
        r2 = self.run_hook("post", self.OTHER, tool_use_id=slug)
        self.assertEqual(r2.returncode, 0, r2.stderr)
        return r2

    def test_the_store_starts_healthy(self):
        """The baseline, stated rather than assumed: if this fails, every
        other assertion in this class is measuring the fixture, not the
        alert path."""
        r = self.verify()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("healthy, 0 problem(s)", r.stdout)

    def test_a_breach_alert_on_a_store_with_no_project_leaves_verify_clean(self):
        r2 = self._breach()
        self.assertIn("fence-breach alert was raised", r2.stderr)
        self.assertEqual(len(self.alerts(raw=True)), 1)

        r = self.verify()
        self.assertEqual(
            r.returncode, 0,
            "raising a fence-breach alert damaged the store:\n%s%s"
            % (r.stdout, r.stderr))
        self.assertIn("healthy, 0 problem(s)", r.stdout)
        self.assertNotIn("missing project", r.stdout)

    def test_a_control_loss_alert_on_a_store_with_no_project_leaves_verify_clean(self):
        """The second alert path, which raises through the same helper. Both
        are asserted because 'the other one was fixed' is precisely how the
        first one came to be written without a project in the first place."""
        owner = self.label(self.OWNER)
        self.claim("mine", ["src/mine.txt"], owner)
        token = fh.token_path(self.root, self.OWNER)
        self.assertTrue(os.path.isfile(token), "no owner token to remove")

        r1 = self.run_hook("pre", self.OTHER, tool_use_id="toolu_ctlhealth")
        self.assertEqual(r1.returncode, 0, r1.stderr)
        os.remove(token)
        r2 = self.run_hook("post", self.OTHER, tool_use_id="toolu_ctlhealth")
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertIn("fence-control-loss alert was raised", r2.stderr)

        r = self.verify()
        self.assertEqual(
            r.returncode, 0,
            "raising a fence-control-loss alert damaged the store:\n%s%s"
            % (r.stdout, r.stderr))
        self.assertIn("healthy, 0 problem(s)", r.stdout)

    def test_the_alert_project_id_is_registered_in_the_store_module(self):
        """The two constants that have to agree. bm_store.SYSTEM_PROJECTS is
        what licenses this id to be created on demand; an id renamed on one
        side and not the other would refuse every alert this hook raises, at
        the one moment the founder most needs the record."""
        self.assertIn(ba.ALERT_PROJECT_ID, bs.SYSTEM_PROJECTS)

    def test_the_project_row_is_created_once_however_many_alerts_land(self):
        self._breach(slug="toolu_once_a")
        rows_after_one = self.projects(include_system=True)
        self._breach(slug="toolu_once_b", claim=False)
        self.assertEqual(len(self.alerts(raw=True)), 2,
                         "the second breach did not raise its own alert")
        rows_after_two = self.projects(include_system=True)
        self.assertEqual(len(rows_after_one), 1, rows_after_one)
        self.assertEqual([p["project_id"] for p in rows_after_two],
                         [ba.ALERT_PROJECT_ID])
        self.assertEqual(rows_after_one[0]["created_at"],
                         rows_after_two[0]["created_at"],
                         "the second alert re-created or overwrote the "
                         "project row instead of leaving it alone")

        r = self.verify()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("healthy, 0 problem(s)", r.stdout)

    def test_the_founders_own_project_is_still_the_only_one_after_an_alert(self):
        """The reason system projects are hidden by default, as a behaviour
        rather than a preference. One project per folder is the beginner
        model, and tools/bm_statusline.py, tools/bm_view.py, tools/bm_lead.py
        and tools/bm_project.py all resolve THE project by counting rows. If
        the row this hook creates counted, the product would answer "not
        exactly one" from the first alert onwards: a blank status line, a
        briefing hook that returns silently, and CANVAS.md written under a
        per-project name instead."""
        now = bs.now_iso()
        with bs.Store(self.root, create=False) as store:
            store.upsert_project(
                {"project_id": "founder-project", "name": "The real work",
                 "created_at": now, "updated_at": now},
                {"actor_type": "human", "actor_name": "founder"})
        self.assertEqual([p["project_id"] for p in self.projects()],
                         ["founder-project"])

        self._breach(slug="toolu_only")

        self.assertEqual(
            [p["project_id"] for p in self.projects()], ["founder-project"],
            "the alert path's own project is being counted as founder work")
        self.assertEqual(
            sorted(p["project_id"] for p in self.projects(include_system=True)),
            ["brothermode-bash-audit", "founder-project"],
            "include_system=True must still show every row; hiding is a "
            "default, not a filter nothing can turn off")

        r = self.verify()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("healthy, 0 problem(s)", r.stdout)


# ---------------------------------------------------------------------------
# C-02 (2026-08-03), the REFUSE half. One test per mutation form the closure
# register's reproduction used, each asserting BOTH directions on that form:
# refused under BM_FENCE_MODE=enforced INSIDE A BROTHERMODE PROJECT, allowed
# under the default. The second half is the important one, exactly as in
# test_bm_fence_hook.py's EnforcedModeFailsClosed: it is what stops a later
# change from quietly making fail-closed the default for people who never
# asked for it. A THIRD direction is asserted once, at the end of this class
# (test_the_refusal_stays_inert_outside_a_brothermode_project_even_when_
# enforced): this hook installs at USER-GLOBAL scope (~/.claude/settings.json),
# so an earlier draft that refused before resolving a project root would have
# refused this same command in every unrelated directory on the machine. That
# defect was caught before it shipped; this test is what stops it coming back.
# ---------------------------------------------------------------------------

class EnforcedModeRefusesStoreDestruction(BashAuditBase):

    def _both_ways(self, command, slug):
        """Refused under enforced INSIDE THIS FIXTURE'S PROJECT, allowed by
        default, on ONE command."""
        owner = self.label(self.OWNER)
        self.claim("mine-" + slug, ["src/mine.txt"], owner)

        r = self.run_hook("pre", self.OTHER, tool_use_id="toolu_enf_" + slug,
                          command=command,
                          env_extra={"BM_FENCE_MODE": "enforced"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(r.stdout.strip(),
                        "enforced mode wrote no decision to stdout, so "
                        "Claude Code would have run the command")
        decision = json.loads(r.stdout)
        out = decision["hookSpecificOutput"]
        self.assertEqual(out["hookEventName"], "PreToolUse")
        self.assertEqual(out["permissionDecision"], "deny")
        reason = out["permissionDecisionReason"]
        self.assertIn("enforced mode", reason)
        self.assertIn("REFUSING", r.stderr)
        # No snapshot was written for a call that will never run.
        self.assertFalse(
            os.path.isfile(self.snapshot_path(self.OTHER,
                                              "toolu_enf_" + slug)),
            "a refused Bash call still left a snapshot behind")

        r2 = self.run_hook("pre", self.OTHER, tool_use_id="toolu_def_" + slug,
                           command=command)
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertEqual(r2.stdout, "",
                         "the DEFAULT mode refused a Bash call; fail-closed "
                         "must stay opt-in")
        self.assertNotIn("REFUSING", r2.stderr)

    def test_rm_of_the_store_is_refused_when_enforced(self):
        """The closure register's own reproduction command, verbatim."""
        self._both_ways("rm -f .brothermode/store.sqlite3", "rm")

    def test_redirection_onto_the_store_is_refused_when_enforced(self):
        self._both_ways(": > .brothermode/store.sqlite3", "redir")

    def test_sed_i_on_the_store_is_refused_when_enforced(self):
        self._both_ways("sed -i.bak -e 's/a/b/' .brothermode/store.sqlite3",
                        "sed")

    def test_tee_onto_the_store_is_refused_when_enforced(self):
        self._both_ways("echo x | tee .brothermode/store.sqlite3", "tee")

    def test_inline_python_removing_the_store_is_refused_when_enforced(self):
        self._both_ways(
            "python3 -c \"import os; os.remove('.brothermode/store.sqlite3')\"",
            "python")

    def test_git_checkout_of_the_store_is_refused_when_enforced(self):
        self._both_ways("git checkout -- .brothermode/store.sqlite3", "git")

    def test_removing_the_fence_directory_is_refused_when_enforced(self):
        """Not the store, the other half of the enforcement state: the tokens
        that decide which session owns which record."""
        self._both_ways("rm -rf .brothermode/fence", "fencedir")

    def test_a_tree_wide_wipe_that_names_nothing_is_refused_when_enforced(self):
        """`git clean -xfd` names no BrotherMode path at all and deletes it
        anyway, because .brothermode is excluded from git. It is caught by
        the second, deliberately tiny rule rather than by name."""
        self._both_ways("git clean -xfd", "gitclean")

    def test_ordinary_commands_are_untouched_even_when_enforced(self):
        """The false-positive guard. Enforcement that stopped ordinary work
        would be removed within a day, so the refusal has to be narrow enough
        to live with: reading the directory, querying the store, and editing
        a source file all still run."""
        owner = self.label(self.OWNER)
        self.claim("mine", ["src/mine.txt"], owner)
        for i, command in enumerate((
                "echo hi",
                "git status --short",
                "ls -la .brothermode",
                "python3 tools/bm_store.py verify",
                "rm -rf build",
                "make test 2>&1 | tail -5",
                "git checkout -- src/other.py")):
            r = self.run_hook("pre", self.OTHER,
                              tool_use_id="toolu_benign_%d" % i,
                              command=command,
                              env_extra={"BM_FENCE_MODE": "enforced"})
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout, "",
                             "enforced mode refused %r, which writes nothing "
                             "BrotherMode owns" % command)

    def test_the_deny_reason_names_no_path_and_no_command_text(self):
        """Same rule bm_fence_hook.py's _FAIL_REASONS follows: the operator
        gets the detail on stderr, the model gets a category and a remedy.
        Nothing has been verified at the moment this is produced, so nothing
        justifies quoting a path or the command."""
        owner = self.label(self.OWNER)
        self.claim("mine", ["src/mine.txt"], owner)
        command = "rm -f .brothermode/store.sqlite3 && echo SECRETMARKER"
        r = self.run_hook("pre", self.OTHER, tool_use_id="toolu_literal",
                          command=command,
                          env_extra={"BM_FENCE_MODE": "enforced"})
        reason = json.loads(r.stdout)["hookSpecificOutput"][
            "permissionDecisionReason"]
        self.assertNotIn("SECRETMARKER", reason)
        self.assertNotIn(".brothermode/store.sqlite3", reason)
        self.assertNotIn(self.root, reason)
        self.assertNotIn("SECRETMARKER", r.stderr,
                         "even the operator line must not repeat the command")

    def test_an_unrecognized_mode_value_does_not_refuse(self):
        """Byte-identical to fence_mode's rule: a typo runs advisory rather
        than refusing over a missing letter."""
        owner = self.label(self.OWNER)
        self.claim("mine", ["src/mine.txt"], owner)
        r = self.run_hook("pre", self.OTHER, tool_use_id="toolu_typo",
                          command="rm -f .brothermode/store.sqlite3",
                          env_extra={"BM_FENCE_MODE": "enfoced"})
        self.assertEqual(r.stdout, "")

    def test_this_files_two_borrowed_primitives_match_the_fence_hooks(self):
        """`_enforced` and `deny_payload` are restated here rather than
        imported, so that a refusal still works when bm_fence_hook.py is the
        thing that failed. This is the test that stops the copies drifting."""
        for value in ("enforced", "ENFORCED", " enforced ", "advisory",
                      "enfoced", "", "1"):
            self.assertEqual(ba._enforced({"BM_FENCE_MODE": value}),
                             fh.enforced_mode({"BM_FENCE_MODE": value}),
                             "the two readings of BM_FENCE_MODE=%r "
                             "disagree" % value)
        self.assertEqual(ba._enforced({}), fh.enforced_mode({}))
        self.assertEqual(ba.deny_payload("because"),
                         fh.deny_payload("because"))

    def test_the_refusal_check_is_documented_as_partial(self):
        """The register's own wording: this cannot pretend to catch
        everything. A name built at runtime is the honest miss, asserted here
        so nobody later reads the feature as complete containment."""
        code, _labels, _names = ba.refusal_for(
            "d=.brother; rm -f ${d}mode/store.sqlite3", bs)
        self.assertEqual(code, "store-destruction",
                         "the literal store filename is still in that text")
        code2, _l2, _n2 = ba.refusal_for("d=.brother; rm -f ${d}mode/s*", bs)
        self.assertIsNone(code2,
                          "a name assembled at runtime is a STATED miss; if "
                          "this ever starts matching, update refusal_for's "
                          "docstring and docs/KNOWN-LIMITS.md rather than "
                          "deleting this test")

    def test_the_refusal_stays_inert_outside_a_brothermode_project_even_when_enforced(self):
        """THE CORRECTION, pinned. This hook installs at USER-GLOBAL scope
        (~/.claude/settings.json), so an earlier draft that refused BEFORE
        resolving a project root would have refused this exact command in
        every unrelated directory on the machine, not just inside a
        BrotherMode project. With BM_FENCE_MODE=enforced set, the SAME
        store-destroying command text must be ALLOWED when the hook's cwd is
        a directory that resolves to no BrotherMode project at all, and
        REFUSED when it is this fixture's own project, so the scoping check
        cannot silently regress to the unscoped behaviour."""
        command = "rm -f .brothermode/store.sqlite3"
        with tempfile.TemporaryDirectory() as outside:
            outside = os.path.realpath(outside)
            r_outside = self.run_hook(
                "pre", self.OTHER, tool_use_id="toolu_outside",
                command=command, env_extra={"BM_FENCE_MODE": "enforced"},
                cwd_override=outside)
            self.assertEqual(r_outside.returncode, 0, r_outside.stderr)
            self.assertEqual(
                r_outside.stdout, "",
                "enforced mode refused a Bash call outside any BrotherMode "
                "project; this hook installs user-globally and must stay "
                "inert everywhere that is not a BrotherMode project")
            self.assertNotIn("REFUSING", r_outside.stderr)

        owner = self.label(self.OWNER)
        self.claim("mine-scoped", ["src/mine.txt"], owner)
        r_inside = self.run_hook(
            "pre", self.OTHER, tool_use_id="toolu_inside",
            command=command, env_extra={"BM_FENCE_MODE": "enforced"})
        self.assertEqual(r_inside.returncode, 0, r_inside.stderr)
        self.assertIn("REFUSING", r_inside.stderr,
                      "the same command inside this fixture's own "
                      "BrotherMode project must still be refused")
        decision = json.loads(r_inside.stdout)
        self.assertEqual(
            decision["hookSpecificOutput"]["permissionDecision"], "deny")


# ---------------------------------------------------------------------------
# A2 (loop6 refuter finding): nothing tied this hook to its OWN wiring.
# Every test above drives bm_bash_audit.py directly as a subprocess, so
# deleting the PostToolUse block from hooks/hooks.json (or the Bash
# PreToolUse group next to it) left every test in this file green while the
# hook was never actually invoked by Claude Code. This reads the shipped
# manifest itself and asserts both entrypoints are wired with the event and
# matcher the plugin install path depends on, so a wiring deletion goes red
# here even though nothing else in this file would ever notice.
# ---------------------------------------------------------------------------

HOOKS_JSON_PATH = os.path.join(os.path.dirname(HERE), "hooks", "hooks.json")


class TestHooksJsonWiring(unittest.TestCase):

    def _load(self):
        with io.open(HOOKS_JSON_PATH, encoding="utf-8") as f:
            return json.load(f)

    def _bash_groups(self, manifest, event):
        groups = manifest.get("hooks", {}).get(event, [])
        return [g for g in groups if g.get("matcher") == "Bash"]

    def test_pre_and_post_bash_audit_entrypoints_are_both_wired(self):
        manifest = self._load()

        pre_groups = self._bash_groups(manifest, "PreToolUse")
        self.assertEqual(len(pre_groups), 1,
                         "PreToolUse must carry exactly one Bash-matcher "
                         "group for bm_bash_audit.py's pre entrypoint")
        pre_cmd = pre_groups[0]["hooks"][0]["command"]
        self.assertIn("bm_bash_audit.py", pre_cmd)
        self.assertIn(" pre", pre_cmd,
                      "the PreToolUse Bash group must invoke the pre "
                      "subcommand")

        post_groups = self._bash_groups(manifest, "PostToolUse")
        self.assertEqual(len(post_groups), 1,
                         "PostToolUse must carry exactly one Bash-matcher "
                         "group for bm_bash_audit.py's post entrypoint")
        post_cmd = post_groups[0]["hooks"][0]["command"]
        self.assertIn("bm_bash_audit.py", post_cmd)
        self.assertIn(" post", post_cmd,
                      "the PostToolUse Bash group must invoke the post "
                      "subcommand")

        # The fence group must still be present and untouched by this
        # addition: PreToolUse carries TWO independent groups, not one
        # replaced by the other.
        fence_groups = [g for g in manifest["hooks"]["PreToolUse"]
                        if g.get("matcher") != "Bash"]
        self.assertEqual(len(fence_groups), 1)
        self.assertIn("Edit", fence_groups[0].get("matcher", ""))


# ---------------------------------------------------------------------------
# Leak check: same mechanical stop tools/test_bm_fence_hook.py and
# tools/test_bm_store.py use. A store opened by THIS test process (via the
# claim()/alerts() helpers above) and never closed passes on POSIX and
# fails on Windows, where an open handle blocks the temp directory's
# removal.
# ---------------------------------------------------------------------------

class _LeakCheckingResult(unittest.TextTestResult):

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
