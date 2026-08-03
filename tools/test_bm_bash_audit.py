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
        for k in ("BROTHERMODE_ROOT", "BM_FENCE_STRICT", "BM_FENCE_SESSION_ID"):
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
                consented=True):
        """Run bm_bash_audit.py exactly as Claude Code would: a bare
        subcommand (pre or post) with a JSON hook payload on stdin."""
        payload = json.dumps({
            "session_id": session_id,
            "transcript_path": os.path.join(self.root, "transcript.jsonl"),
            "cwd": self.root,
            "permission_mode": "default",
            "hook_event_name": "PreToolUse" if phase == "pre" else "PostToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "echo hi"},
            "tool_use_id": tool_use_id,
        })
        env = dict(os.environ)
        if not consented:
            env.pop("BROTHERME_CONFIG", None)
            env["BROTHERME_CONFIG"] = os.path.join(
                self._tmp.name, "no-such-config.json")
        return subprocess.run(
            [sys.executable, HOOK_PATH, phase], input=payload, text=True,
            capture_output=True, cwd=self.root, env=env)

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
