#!/usr/bin/env python3
"""Suite for tools/bm_handover.py: the baton ceremony tool (spec
docs/superpowers/specs/2026-08-11-baton-ceremony-design.md, sections 4 and
8, V1 through V5).

Every test drives a throwaway project root under a temporary directory, with
BROTHERMODE_ROOT pointed at it, so nothing here touches the real project's
own store or the real ~/Documents/BrotherModeUp-handovers. The zip
destination is likewise redirected per-test through
BROTHERMODE_HANDOVERS_DIR, an env override bm_handover.py itself reads at
call time (mirroring the BROTHERMODE_VAULT idiom tools/bm_autosave.py and
tools/bm_ledger.py already use).

Python 3.9, standard library only. No network.

No em or en dashes anywhere in this file, its comments, or its output.
"""

import importlib.util
import io
import os
import shutil
import sys
import tempfile
import time
import unittest
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    """Load a sibling module by PATH, the same technique tools/bm_packs.py
    and tools/bm_stall.py use for tools/bm_store.py."""
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(HERE, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_optional(name):
    """None instead of an exception, so every test in this file fails on
    its own with a message naming the missing file (the RED state before
    tools/bm_handover.py exists), rather than one collection-time error
    collapsing the whole suite."""
    try:
        return _load(name)
    except Exception:
        return None


bh = _load_optional("bm_handover")
bs = bh.bs if bh is not None else _load("bm_store")


class HandoverCase(unittest.TestCase):
    """A throwaway project root and a real bm_store.Store under it, with
    BROTHERMODE_ROOT and BROTHERMODE_HANDOVERS_DIR pointed there so nothing
    here can reach a real project or a real founder home directory."""

    ENV_KEYS = ("BROTHERMODE_ROOT", "BROTHERMODE_HANDOVERS_DIR")

    def setUp(self):
        self.assertIsNotNone(
            bh, "tools/bm_handover.py does not exist yet, so nothing in "
                "this file can run. That is the failing-first (RED) state "
                "the baton ceremony spec's section 8 asks this class to "
                "reproduce.")
        self.tmp = tempfile.mkdtemp(prefix="bm-handover-")
        self.root = os.path.join(self.tmp, "project")
        self.handovers_dir = os.path.join(self.tmp, "handovers")
        os.makedirs(self.root)
        self._env_backup = {k: os.environ.get(k) for k in self.ENV_KEYS}
        os.environ["BROTHERMODE_ROOT"] = self.root
        os.environ["BROTHERMODE_HANDOVERS_DIR"] = self.handovers_dir
        self.store = bs.Store(self.root)

    def tearDown(self):
        try:
            self.store.close()
        except Exception:
            pass
        for k, v in self._env_backup.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.tmp, ignore_errors=True)

    # -- driving the CLI in process ------------------------------------

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        real_out, real_err = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = out, err
        try:
            code = bh.main(list(argv))
        finally:
            sys.stdout, sys.stderr = real_out, real_err
        return code, out.getvalue(), err.getvalue()

    # -- seeding ----------------------------------------------------------

    def claim(self, name, session_id="test-session", files=None):
        return self.store.claim(
            name=name, lifetime="persistent",
            files=files or ["%s.py" % name], objective="carry %s" % name,
            owner="tester", session_id=session_id)

    def park(self, record, session_id="test-session"):
        return self.store.transition(
            record.lifecycle_uuid, record.version, "parked",
            session_id=session_id, note="parked by test",
            handover_heading="handing off %s" % record.name)

    def read(self, path):
        with io.open(path, encoding="utf-8") as fh:
            return fh.read()

    def write(self, path, text):
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def fill_human_block(self, path, body):
        """Replace the single human block in a generated pack page with
        `body`, the same shape a person editing the file by hand would
        produce."""
        text = self.read(path)
        begin, end = bs.HUMAN_BLOCK_BEGIN, bs.HUMAN_BLOCK_END
        pre, _, rest = text.partition(begin)
        _mid, sep, post = rest.partition(end)
        self.assertTrue(sep, "no human block found in %s" % path)
        self.write(path, pre + begin + "\n" + body + "\n" + end + post)

    def fill_pack(self, pack_dir, status_line="FINISHED: all clear."):
        """Fill every narrative slot in a freshly generated pack with real
        text, so no FILL-BY-HAND marker survives. 06-CLOSE-REPORT.md's
        block opens with `status_line`."""
        for name in bh.PACK_FILES:
            path = os.path.join(pack_dir, name)
            if name == "06-CLOSE-REPORT.md":
                self.fill_human_block(
                    path, status_line + "\nNothing else outstanding.")
            else:
                self.fill_human_block(
                    path, "Filled in by the test suite: nothing left to "
                          "say about %s." % name)


# ---------------------------------------------------------------------------
# V1 + V2: skeleton
# ---------------------------------------------------------------------------

class TestSkeleton(HandoverCase):

    def test_v1_skeleton_writes_all_seven_files_prefilled_and_marked(self):
        r1 = self.claim("fence-alpha")
        r2 = self.claim("fence-beta")
        out_dir = os.path.join(self.root, "docs", "handover", "pack1")
        code, out, err = self.run_cli(
            "skeleton", "--out", "docs/handover/pack1", "--date",
            "2026-08-11", "--slot", "pack1")
        self.assertEqual(0, code, "stdout=%r stderr=%r" % (out, err))
        for name in bh.PACK_FILES:
            path = os.path.join(out_dir, name)
            self.assertTrue(os.path.isfile(path), "missing %s" % name)
            text = self.read(path)
            self.assertIn(bh.FILL_BY_HAND, text,
                          "%s has no FILL-BY-HAND marker" % name)
        handover_text = self.read(os.path.join(out_dir, "01-HANDOVER.md"))
        self.assertIn(r1.name, handover_text)
        self.assertIn(r1.lifecycle_uuid[:8], handover_text)
        self.assertIn(r2.name, handover_text)
        self.assertIn(r2.lifecycle_uuid[:8], handover_text)

    def test_v2_rerun_over_filled_pack_preserves_human_bytes(self):
        self.claim("fence-alpha")
        out_dir = os.path.join(self.root, "docs", "handover", "pack1")
        code, _out, _err = self.run_cli(
            "skeleton", "--out", "docs/handover/pack1", "--date",
            "2026-08-11", "--slot", "pack1")
        self.assertEqual(0, code)
        target = os.path.join(out_dir, "02-LEARNINGS-AND-MISTAKES.md")
        sentinel = ("A real lesson a human wrote by hand: the fence sweep "
                    "found nothing new twice in a row before we stopped.")
        self.fill_human_block(target, sentinel)
        filled_text = self.read(target)
        self.assertNotIn(bh.FILL_BY_HAND, filled_text)
        # A second record now exists in the store, so the STRUCTURAL part of
        # every page changes on regeneration; the human paragraph must not.
        self.claim("fence-beta")
        code, _out, _err = self.run_cli(
            "skeleton", "--out", "docs/handover/pack1", "--date",
            "2026-08-11", "--slot", "pack1")
        self.assertEqual(0, code)
        regenerated = self.read(target)
        self.assertIn(sentinel, regenerated,
                      "the human paragraph did not survive regeneration (I10)")
        self.assertNotIn(bh.FILL_BY_HAND, regenerated,
                         "regeneration reintroduced the FILL-BY-HAND default "
                         "over a block a human had already filled")
        handover_text = self.read(os.path.join(out_dir, "01-HANDOVER.md"))
        self.assertIn("fence-beta", handover_text,
                      "the structural section did not pick up the new record")


# ---------------------------------------------------------------------------
# V3: verify-close
# ---------------------------------------------------------------------------

class TestVerifyClose(HandoverCase):

    def _fresh_pack(self, slot="closeit"):
        out_dir = os.path.join(self.root, "docs", "handover",
                               "2026-08-11-%s" % slot)
        code, _out, _err = self.run_cli(
            "skeleton", "--date", "2026-08-11", "--slot", slot)
        self.assertEqual(0, code)
        return out_dir

    def test_v3a_fails_on_surviving_fill_by_hand(self):
        self.claim("fence-alpha")
        pack_dir = self._fresh_pack()
        code, out, _err = self.run_cli("verify-close", "--pack", pack_dir)
        self.assertEqual(1, code)
        self.assertIn("FAIL", out)
        self.assertIn(bh.FILL_BY_HAND, out)
        self.assertIn("00-READ-ME-FIRST.md", out)

    def test_v3b_fails_on_missing_finished_or_unfinished_line(self):
        self.claim("fence-alpha")
        pack_dir = self._fresh_pack()
        self.fill_pack(pack_dir, status_line="still wrapping up, no verdict yet")
        code, out, _err = self.run_cli("verify-close", "--pack", pack_dir)
        self.assertEqual(1, code)
        self.assertIn("FAIL", out)
        self.assertIn("FINISHED", out)
        self.assertIn("UNFINISHED", out)

    def test_v3c_fails_when_pack_is_newer_than_the_newest_zip(self):
        self.claim("fence-alpha")
        pack_dir = self._fresh_pack()
        self.fill_pack(pack_dir)
        code, out, _err = self.run_cli("verify-close", "--pack", pack_dir)
        self.assertEqual(1, code, out)
        self.assertIn("FAIL", out)
        self.assertIn("zip", out.lower())

    def test_v3d_fails_when_session_still_owns_unparked_records(self):
        rec = self.claim("fence-alpha", session_id="closing-session")
        pack_dir = self._fresh_pack()
        self.fill_pack(pack_dir)
        code, _out, _err = self.run_cli("zip", "--pack", pack_dir)
        self.assertEqual(0, code)
        code, out, _err = self.run_cli(
            "verify-close", "--pack", pack_dir, "--session", "closing-session")
        self.assertEqual(1, code, out)
        self.assertIn("FAIL", out)
        self.assertIn(rec.lifecycle_uuid[:8], out)

    def test_v3e_passes_when_clean(self):
        rec = self.claim("fence-alpha", session_id="closing-session")
        pack_dir = self._fresh_pack()
        self.fill_pack(pack_dir)
        code, _out, _err = self.run_cli("zip", "--pack", pack_dir)
        self.assertEqual(0, code)
        self.park(rec, session_id="closing-session")
        code, out, _err = self.run_cli(
            "verify-close", "--pack", pack_dir, "--session", "closing-session")
        self.assertEqual(0, code, out)
        self.assertIn("PASS", out)

    def test_v3f_no_store_is_no_data_never_pass(self):
        empty_root = os.path.join(self.tmp, "no-store-project")
        os.makedirs(empty_root)
        os.environ["BROTHERMODE_ROOT"] = empty_root
        try:
            code, out, _err = self.run_cli("verify-close")
        finally:
            os.environ["BROTHERMODE_ROOT"] = self.root
        self.assertNotEqual(0, code)
        self.assertIn("NO-DATA", out)
        self.assertNotIn("PASS", out)


# ---------------------------------------------------------------------------
# V4: zip
# ---------------------------------------------------------------------------

class TestZip(HandoverCase):

    def test_v4_zip_creates_dated_zip_and_is_idempotent(self):
        self.claim("fence-alpha")
        code, _out, _err = self.run_cli(
            "skeleton", "--date", "2026-08-11", "--slot", "zipme")
        self.assertEqual(0, code)
        pack_dir = os.path.join(self.root, "docs", "handover",
                                "2026-08-11-zipme")
        code, out, _err = self.run_cli("zip", "--pack", pack_dir)
        self.assertEqual(0, code, out)
        zip_path = os.path.join(
            self.handovers_dir,
            "BrotherMode-Handover-2026-08-11-zipme.zip")
        self.assertTrue(os.path.isfile(zip_path), out)
        with zipfile.ZipFile(zip_path) as zf:
            names = set(zf.namelist())
        for pf in bh.PACK_FILES:
            self.assertTrue(
                any(n.endswith(pf) for n in names),
                "%s not found in zip entries %r" % (pf, names))
        first_mtime = os.path.getmtime(zip_path)
        time.sleep(0.05)
        code, out2, _err = self.run_cli("zip", "--pack", pack_dir)
        self.assertEqual(0, code, out2)
        self.assertIn("unchanged", out2.lower())
        self.assertEqual(first_mtime, os.path.getmtime(zip_path),
                         "an unchanged rerun rewrote the zip file")


# ---------------------------------------------------------------------------
# V5: detect
# ---------------------------------------------------------------------------

class TestDetect(HandoverCase):

    def test_v5a_empty_estate_is_stated_no_data_not_silence(self):
        code, out, _err = self.run_cli("detect")
        self.assertEqual(0, code)
        self.assertTrue(out.strip(), "detect printed nothing at all")
        self.assertIn("NO-DATA", out)

    def test_v5b_reports_dead_session_leftover_with_clearing_command(self):
        real_now_iso = bs.now_iso
        ten_hours_ago = (
            __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc)
            - __import__("datetime").timedelta(hours=10))
        bs.now_iso = lambda: ten_hours_ago.strftime(bs._ISO_STAMP_FORMAT)
        try:
            rec = self.claim("stale-fence", session_id="dead-session")
        finally:
            bs.now_iso = real_now_iso
        code, out, _err = self.run_cli("detect")
        self.assertEqual(0, code, out)
        self.assertIn(rec.lifecycle_uuid[:8], out)
        self.assertIn("adopt", out)


# ---------------------------------------------------------------------------
# Privacy: raw store text may drive a comparison, never a written page
# ---------------------------------------------------------------------------

class TestRawStoreTextNeverReachesAPage(HandoverCase):
    """Found by the orchestrator's own spot-check of the landed delta, and
    fixed RED first before that delta was committed.

    This file reads the store with dump(raw=True) on purpose: the default
    redacted dump WITHHOLDS a session id that does not match the codebase's
    own generated-id shapes, and verify-close's ownership test has to
    compare against the real value or it silently matches nothing. Taking
    the raw value is therefore right; WRITING it is not. A pack page is
    committed to git and zipped into a handover, so a hand-typed session id
    (which the store classifies as founder text precisely because it could
    be anything, an absolute path included) must be scrubbed on the way out,
    exactly as every other field from the same raw dump already is."""

    #: CALIBRATED, not guessed. The first version of this fixture embedded an
    #: absolute path, and both tests passed while the leak was still open: the
    #: write funnel's own path masking scrubbed it for an unrelated reason. A
    #: plain hand-typed value reproduces the real defect, and the store's own
    #: default dump renders exactly this value as founder text it withholds.
    HAND_TYPED = "khalil-private-note-do-not-publish"

    def test_a_hand_typed_session_id_is_scrubbed_out_of_the_pack_page(self):
        self.claim("fence-alpha", session_id=self.HAND_TYPED)
        out_dir = os.path.join(self.root, "docs", "handover", "pack1")
        code, out, err = self.run_cli(
            "skeleton", "--out", "docs/handover/pack1", "--date",
            "2026-08-11", "--slot", "pack1")
        self.assertEqual(0, code, "stdout=%r stderr=%r" % (out, err))
        page = self.read(os.path.join(out_dir, "01-HANDOVER.md"))
        self.assertNotIn(
            self.HAND_TYPED, page,
            "the raw session id reached a generated pack page unscrubbed; "
            "pack pages are committed and zipped, so founder text out of "
            "the store must pass through _scrub on the way out")

    def test_the_ownership_check_still_matches_that_same_raw_value(self):
        """The other half of the pair: scrubbing for display must not break
        the comparison the raw read exists for. A session that still owns an
        active record FAILs verify-close, scrubbed page or not."""
        self.claim("fence-alpha", session_id=self.HAND_TYPED)
        self.run_cli("skeleton", "--out", "docs/handover/pack1", "--date",
                     "2026-08-11", "--slot", "pack1")
        pack_rel = "docs/handover/pack1"
        self.fill_pack(os.path.join(self.root, pack_rel))
        code, out, err = self.run_cli(
            "verify-close", "--pack", pack_rel, "--session", self.HAND_TYPED)
        self.assertNotEqual(
            0, code,
            "verify-close passed while that session still owned an active "
            "record: stdout=%r stderr=%r" % (out, err))


if __name__ == "__main__":
    unittest.main()
