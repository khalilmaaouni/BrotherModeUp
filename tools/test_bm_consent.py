#!/usr/bin/env python3
"""Suite for the Loop 3 consent gate: scripts/setup.py, tools/bm_sessionstart.sh
and tools/bm_telemetry.py's SessionEnd path (design D-1/D-2,
docs/superpowers/specs/2026-08-01-loop3-consent-install-design.md).

Every test here runs the real files as real subprocesses (sh for the hook
script, python3 for the two CLIs) against a FAKE HOME, and often a fake
BROTHERME_CONFIG path too, under a temporary directory. Nothing in this file
writes to the real ~/.brotherme or the real ~/BrotherModeVault, and nothing
imports scripts/setup.py or tools/bm_telemetry.py into this process, for the
same reason tools/test_install.py does not import scripts/install.py: a gate
that is only ever exercised in-process is not exercised at the layer a
founder's terminal actually uses.

THE ONE TEST THAT MATTERS MOST: sessionstart pre-consent creates ZERO files
anywhere under a fresh HOME and a fresh project root. That is the review's
go/no-go row this whole loop exists to flip, so it is asserted by walking
both trees before and after, not by trusting stdout.

Python 3.9, standard library only.

No em or en dashes anywhere in this file, its comments, or its output.
"""

import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SESSIONSTART = os.path.join(HERE, "bm_sessionstart.sh")
TELEMETRY = os.path.join(HERE, "bm_telemetry.py")
SETUP = os.path.join(ROOT, "scripts", "setup.py")
DIGEST = os.path.join(ROOT, "DIGEST.md")

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2
EXIT_REFUSED = 4

SETUP_SENTENCE = "python3 scripts/setup.py"


def _clean_env(home):
    """A base environment for every subprocess in this file: real os.environ
    with HOME pointed at a throwaway directory and every project-state or
    fence override that could leak from THIS session's own environment
    stripped, so a test can never accidentally pass by inheriting the real
    checkout's live store or fence state.

    PYTHONDONTWRITEBYTECODE=1 matters here specifically: macOS's own
    /usr/bin/python3 stub caches compiled bytecode under
    ~/Library/Caches/com.apple.python/... keyed off HOME, which is not this
    project writing anything but would still show up as a stray file under
    our fake HOME and defeat the "creates ZERO files" assertions below."""
    env = dict(os.environ)
    env["HOME"] = home
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for k in ("BROTHERMODE_VAULT", "BROTHERMODE_ROOT", "BROTHERME_CONFIG",
              "BM_FENCE_STRICT", "BM_FENCE_SESSION_ID", "CLAUDE_SESSION_ID"):
        env.pop(k, None)
    return env


def _files_under(root):
    """Every file path under root, relative to root, sorted. Directories are
    not counted on their own (an empty mkdir is not a content write), but any
    file inside one is."""
    found = []
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            found.append(os.path.relpath(os.path.join(dirpath, f), root))
    return sorted(found)


def _read_text(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


def _write_consented_config(path, vault, mode="clone"):
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    with io.open(path, "w", encoding="utf-8") as fh:
        json.dump({
            "setup_complete": True,
            "vault_path": vault,
            "privacy_notice_version": "2026-08-01",
            "installation_mode": mode,
            "security_mode": "standard",
        }, fh)


class SessionStartPreConsentCase(unittest.TestCase):
    """(a) sessionstart pre-consent writes nothing at all, anywhere."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="bm-consent-sessionstart-")
        self.home = os.path.join(self.tmp, "home")
        self.project = os.path.join(self.tmp, "project")
        os.makedirs(self.home)
        os.makedirs(self.project)
        self.env = _clean_env(self.home)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_sessionstart(self, payload="{}"):
        return subprocess.run(
            ["sh", SESSIONSTART], cwd=self.project, env=self.env, input=payload,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, timeout=120)

    def test_no_config_creates_zero_files_and_names_the_setup_command(self):
        before_home = _files_under(self.home)
        before_project = _files_under(self.project)
        r = self.run_sessionstart()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(SETUP_SENTENCE, r.stdout)
        # Exactly one line of output: no digest, no nags, no store health.
        self.assertEqual(len([ln for ln in r.stdout.splitlines() if ln.strip()]), 1,
                         "pre-consent sessionstart printed more than the one "
                         "sentence: %r" % r.stdout)
        self.assertEqual(_files_under(self.home), before_home,
                         "sessionstart wrote a file under HOME before consent")
        self.assertEqual(_files_under(self.project), before_project,
                         "sessionstart wrote a file under the project root "
                         "before consent")

    def test_setup_complete_false_is_treated_the_same_as_absent(self):
        cfg_path = os.path.join(self.home, ".brotherme", "config.json")
        os.makedirs(os.path.dirname(cfg_path))
        with io.open(cfg_path, "w", encoding="utf-8") as fh:
            json.dump({"setup_complete": False}, fh)
        before_home = _files_under(self.home)
        r = self.run_sessionstart()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(SETUP_SENTENCE, r.stdout)
        self.assertEqual(_files_under(self.home), before_home,
                         "sessionstart wrote a file under HOME with "
                         "setup_complete: false")

    def test_a_broken_config_fails_closed_the_same_way(self):
        cfg_path = os.path.join(self.home, ".brotherme", "config.json")
        os.makedirs(os.path.dirname(cfg_path))
        with io.open(cfg_path, "w", encoding="utf-8") as fh:
            fh.write("{ not valid json")
        r = self.run_sessionstart()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(SETUP_SENTENCE, r.stdout)


class SessionStartPostConsentCase(unittest.TestCase):
    """(e) once consented, sessionstart behaves as it did before this loop."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="bm-consent-sessionstart-after-")
        self.home = os.path.join(self.tmp, "home")
        self.project = os.path.join(self.tmp, "project")
        os.makedirs(self.home)
        os.makedirs(self.project)
        self.env = _clean_env(self.home)
        _write_consented_config(
            os.path.join(self.home, ".brotherme", "config.json"),
            os.path.join(self.home, "BrotherModeVault"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_consented_sessionstart_still_prints_the_digest(self):
        digest_first_line = _read_text(DIGEST).splitlines()[0]
        r = subprocess.run(
            ["sh", SESSIONSTART], cwd=self.project, env=self.env, input="{}",
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("setup is not complete", r.stdout)
        self.assertIn(digest_first_line, r.stdout,
                      "consented sessionstart no longer prints DIGEST.md, a "
                      "regression in the smoke path this gate must not touch")


class TelemetrySessionEndCase(unittest.TestCase):
    """(b) SessionEnd writes no ledger line before consent, and does once
    consented (so the gate is proven to be the reason, not a broken harness)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="bm-consent-telemetry-")
        self.home = os.path.join(self.tmp, "home")
        self.project = os.path.join(self.tmp, "project")
        os.makedirs(self.home)
        os.makedirs(self.project)
        self.vault = os.path.join(self.home, "BrotherModeVault")
        self.env = _clean_env(self.home)
        self.env["BROTHERMODE_VAULT"] = self.vault
        self.ledger = os.path.join(self.vault, "99-System", "telemetry", "outcomes.jsonl")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_transcript(self, session_id):
        """A transcript that clears the activity floor (>=5 api messages,
        >=1 tool call) on its own, so a suppressed ledger line proves the
        CONSENT gate fired, not the unrelated activity-floor refusal."""
        path = os.path.join(self.tmp, "%s.jsonl" % session_id)
        lines = [json.dumps({"type": "user", "timestamp": "2026-08-01T00:00:00Z",
                             "message": {"content": "hello"}})]
        for i in range(5):
            msg = {"id": "msg-%d" % i, "model": "claude-test",
                   "usage": {"input_tokens": 10, "output_tokens": 20},
                   "content": [{"type": "text", "text": "ok"}]}
            if i == 0:
                msg["content"].append(
                    {"type": "tool_use", "name": "Read", "input": {"file_path": "x.py"}})
            lines.append(json.dumps({"type": "assistant",
                                     "timestamp": "2026-08-01T00:00:0%dZ" % (i + 1),
                                     "message": msg}))
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        return path

    def run_outcomes_append(self, session_id):
        transcript = self._make_transcript(session_id)
        payload = json.dumps({"transcript_path": transcript, "session_id": session_id,
                              "cwd": self.project, "reason": "test"})
        return subprocess.run(
            [sys.executable, TELEMETRY, "outcomes-append"], cwd=self.project,
            env=self.env, input=payload, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, universal_newlines=True, timeout=120)

    def test_pre_consent_writes_no_ledger_line(self):
        self.assertFalse(os.path.exists(self.ledger))
        r = self.run_outcomes_append("sess-pre-consent")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(SETUP_SENTENCE, r.stdout)
        self.assertFalse(os.path.exists(self.ledger),
                         "SessionEnd wrote a ledger line before consent")

    def test_post_consent_writes_the_ledger_line_as_before(self):
        """Calibration: proves the harness and the transcript shape actually
        produce a write once consent is granted, so the test above is
        evidence of the gate, not of a transcript that never qualified."""
        _write_consented_config(
            os.path.join(self.home, ".brotherme", "config.json"), self.vault)
        r = self.run_outcomes_append("sess-post-consent")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("recorded", r.stdout)
        self.assertTrue(os.path.isfile(self.ledger))
        rows = [json.loads(ln) for ln in _read_text(self.ledger).splitlines()
                if ln.strip()]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["session_id"], "sess-post-consent")


class SetupShowCase(unittest.TestCase):
    """(d) --show is truthful on both sides, and never writes."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="bm-consent-show-")
        self.home = os.path.join(self.tmp, "home")
        os.makedirs(self.home)
        self.config = os.path.join(self.tmp, "cfgdir", "config.json")
        self.vault = os.path.join(self.tmp, "MyVault")
        self.env = _clean_env(self.home)
        self.env["BROTHERME_CONFIG"] = self.config

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_setup(self, *args):
        return subprocess.run(
            [sys.executable, SETUP] + list(args), cwd=self.tmp, env=self.env,
            input="", stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, timeout=300)

    def test_show_before_setup_is_honest_and_writes_nothing(self):
        r = self.run_setup("--show")
        self.assertEqual(r.returncode, EXIT_OK, r.stdout + r.stderr)
        self.assertIn("NOT SET UP", r.stdout)
        self.assertFalse(os.path.exists(self.config))

    def test_show_after_setup_reports_the_real_values(self):
        r0 = self.run_setup("--vault", self.vault, "--mode", "plugin", "--accept-notice")
        self.assertEqual(r0.returncode, EXIT_OK, r0.stdout + r0.stderr)
        r1 = self.run_setup("--show")
        self.assertEqual(r1.returncode, EXIT_OK, r1.stdout + r1.stderr)
        self.assertIn("SETUP COMPLETE", r1.stdout)
        self.assertIn(self.vault, r1.stdout)
        self.assertIn("plugin", r1.stdout)


class SetupFlagModeCase(unittest.TestCase):
    """(c) flag-mode setup writes a 0600/0700 config and runs doctor.
    (f) refuses to clobber an already-consented config without --reconfigure."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="bm-consent-setup-")
        self.home = os.path.join(self.tmp, "home")
        os.makedirs(self.home)
        self.config = os.path.join(self.tmp, "cfgdir", "config.json")
        self.vault = os.path.join(self.tmp, "MyVault")
        self.env = _clean_env(self.home)
        self.env["BROTHERME_CONFIG"] = self.config

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_setup(self, *args, **kw):
        stdin = kw.pop("input", "")
        return subprocess.run(
            [sys.executable, SETUP] + list(args), cwd=self.tmp, env=self.env,
            input=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, timeout=300)

    def test_flag_mode_writes_0600_0700_config_and_runs_doctor(self):
        r = self.run_setup("--vault", self.vault, "--mode", "clone", "--accept-notice")
        self.assertEqual(r.returncode, EXIT_OK, r.stdout + r.stderr)
        self.assertTrue(os.path.isfile(self.config))
        self.assertEqual(stat.S_IMODE(os.stat(self.config).st_mode), 0o600)
        cfg_dir = os.path.dirname(self.config)
        self.assertEqual(stat.S_IMODE(os.stat(cfg_dir).st_mode), 0o700)
        cfg = json.loads(_read_text(self.config))
        self.assertIs(cfg["setup_complete"], True)
        self.assertEqual(cfg["vault_path"], self.vault)
        self.assertEqual(cfg["installation_mode"], "clone")
        self.assertEqual(cfg["security_mode"], "standard")
        self.assertIn("privacy_notice_version", cfg)
        self.assertIn("doctor", r.stdout.lower(),
                      "flag-mode setup did not run or report doctor")
        self.assertFalse(os.path.exists(self.vault),
                         "setup touched the vault directory itself")

    def test_flag_mode_requires_all_three_flags_together(self):
        r = self.run_setup("--vault", self.vault)
        self.assertEqual(r.returncode, EXIT_USAGE, r.stdout + r.stderr)
        self.assertFalse(os.path.exists(self.config))

    def test_no_tty_no_flags_is_a_usage_refusal_not_a_hang(self):
        r = self.run_setup()
        self.assertEqual(r.returncode, EXIT_USAGE, r.stdout + r.stderr)
        self.assertFalse(os.path.exists(self.config))

    def test_refuses_to_overwrite_a_consented_config_without_reconfigure(self):
        r0 = self.run_setup("--vault", self.vault, "--mode", "clone", "--accept-notice")
        self.assertEqual(r0.returncode, EXIT_OK, r0.stdout + r0.stderr)
        before = _read_text(self.config)

        other_vault = os.path.join(self.tmp, "OtherVault")
        r1 = self.run_setup("--vault", other_vault, "--mode", "plugin", "--accept-notice")
        self.assertEqual(r1.returncode, EXIT_REFUSED, r1.stdout + r1.stderr)
        after = _read_text(self.config)
        self.assertEqual(before, after,
                         "a refused setup run still rewrote the config")

        r2 = self.run_setup("--vault", other_vault, "--mode", "plugin",
                            "--accept-notice", "--reconfigure")
        self.assertEqual(r2.returncode, EXIT_OK, r2.stdout + r2.stderr)
        cfg = json.loads(_read_text(self.config))
        self.assertEqual(cfg["vault_path"], other_vault)
        self.assertEqual(cfg["installation_mode"], "plugin")

    def test_a_config_that_was_never_completed_is_not_protected(self):
        """setup_complete: false is not "an existing consented config": the
        refusal in D-2 protects a founder's YES, not a half-finished file."""
        os.makedirs(os.path.dirname(self.config))
        with io.open(self.config, "w", encoding="utf-8") as fh:
            json.dump({"setup_complete": False}, fh)
        r = self.run_setup("--vault", self.vault, "--mode", "clone", "--accept-notice")
        self.assertEqual(r.returncode, EXIT_OK, r.stdout + r.stderr)
        cfg = json.loads(_read_text(self.config))
        self.assertIs(cfg["setup_complete"], True)


class SetupConsentStateProbeCase(unittest.TestCase):
    """The cheap exit-code probe bm_sessionstart.sh calls."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="bm-consent-probe-")
        self.home = os.path.join(self.tmp, "home")
        os.makedirs(self.home)
        self.config = os.path.join(self.tmp, "cfgdir", "config.json")
        self.env = _clean_env(self.home)
        self.env["BROTHERME_CONFIG"] = self.config

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _probe(self):
        return subprocess.run(
            [sys.executable, SETUP, "--consent-state"], cwd=self.tmp, env=self.env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, timeout=60)

    def test_absent_config_is_exit_1_and_silent(self):
        r = self._probe()
        self.assertEqual(r.returncode, EXIT_FAILED)
        self.assertEqual(r.stdout, "")

    def test_consented_config_is_exit_0(self):
        _write_consented_config(self.config, os.path.join(self.home, "Vault"))
        r = self._probe()
        self.assertEqual(r.returncode, EXIT_OK)

    def test_setup_complete_false_is_exit_1(self):
        os.makedirs(os.path.dirname(self.config))
        with io.open(self.config, "w", encoding="utf-8") as fh:
            json.dump({"setup_complete": False}, fh)
        r = self._probe()
        self.assertEqual(r.returncode, EXIT_FAILED)


if __name__ == "__main__":
    unittest.main(verbosity=1)
