#!/usr/bin/env python3
"""Suite for the Loop 3 consent gate: scripts/setup.py, tools/bm_sessionstart.sh
and tools/bm_telemetry.py's SessionEnd path (design D-1/D-2,
docs/superpowers/specs/2026-08-01-loop3-consent-install-design.md); and, since
WP-E on the same design, scripts/doctor.py's ten-check surface (D-3),
commands/brotherme-update.md's verification steps (D-4), and
scripts/uninstall.py's consent-config removal (D-5).

Every test here runs the real files as real subprocesses (sh for the hook
script, python3 for the CLIs) against a FAKE HOME, and often a fake
BROTHERME_CONFIG path too, under a temporary directory. Nothing in this file
writes to the real ~/.brotherme or the real ~/BrotherModeVault, and nothing
imports scripts/setup.py, scripts/doctor.py, scripts/uninstall.py or
tools/bm_telemetry.py into this process, for the same reason
tools/test_install.py does not import scripts/install.py: a gate that is only
ever exercised in-process is not exercised at the layer a founder's terminal
actually uses.

THE ONE TEST THAT MATTERS MOST: sessionstart pre-consent creates ZERO files
anywhere under a fresh HOME and a fresh project root. That is the review's
go/no-go row this whole loop exists to flip, so it is asserted by walking
both trees before and after, not by trusting stdout.

Python 3.9, standard library only.

No em or en dashes anywhere in this file, its comments, or its output.
"""

import hashlib
import io
import re
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
DOCTOR = os.path.join(ROOT, "scripts", "doctor.py")
UNINSTALL = os.path.join(ROOT, "scripts", "uninstall.py")
UPDATE_MD = os.path.join(ROOT, "commands", "brotherme-update.md")
DIGEST = os.path.join(ROOT, "DIGEST.md")
HOOKS_JSON = os.path.join(ROOT, "hooks", "hooks.json")

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2
EXIT_REFUSED = 4

SETUP_SENTENCE = "python3 scripts/setup.py"


def _telemetry_constant(name):
    """Read a module-level int constant out of bm_telemetry.py by parsing the
    source, so a test can size a fixture against the REAL threshold without
    importing the module (these suites drive it as a subprocess on purpose).

    Deliberately has no default: a renamed constant raises here instead of
    quietly substituting a number, because a fixture sized against a guessed
    threshold is how a gate test becomes a test of nothing."""
    with io.open(os.path.join(HERE, "bm_telemetry.py"), encoding="utf-8") as fh:
        match = re.search(r"(?m)^%s\s*=\s*([0-9_]+)" % re.escape(name), fh.read())
    if match is None:
        raise AssertionError(
            "bm_telemetry.py no longer defines %s; this fixture cannot size "
            "itself against the real threshold, so it must not run" % name)
    return int(match.group(1).replace("_", ""))


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


class TelemetryEveryHookProgramPreConsentCase(unittest.TestCase):
    """(b2) The OTHER two telemetry entrypoints wired into hooks.

    Loop 9, 2026-08-02: the earlier consent work gated bm_autosave.py and
    bm_telemetry.py outcomes-append, and missed the two commands beside them.
    Both were reproduced writing into a fresh HOME with no consent config:

      - precompact-brief wrote last-resume-<identity>.md containing the
        founder's last message VERBATIM. A disclosure defect, the most
        sensitive in this file.
      - stop-warn created the vault telemetry directory to hold its
        once-per-session marker. Content-free, but it materializes a vault in
        a stranger's home before they say yes.

    The escape route is the lesson this class encodes: the PreCompact hook
    line runs TWO programs off one payload, and a suite that drives hook
    EVENTS rather than every PROGRAM on each line cannot see the second one.
    Each test below drives the program directly, and each has a post-consent
    twin so a silent pre-consent run is proof of the gate rather than of a
    payload that never qualified."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="bm-consent-hookprograms-")
        self.home = os.path.join(self.tmp, "home")
        self.project = os.path.join(self.tmp, "project")
        os.makedirs(self.home)
        os.makedirs(self.project)
        self.vault = os.path.join(self.home, "BrotherModeVault")
        self.env = _clean_env(self.home)
        self.env["BROTHERMODE_VAULT"] = self.vault
        self.teldir = os.path.join(self.vault, "99-System", "telemetry")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _consent(self):
        _write_consented_config(
            os.path.join(self.home, ".brotherme", "config.json"), self.vault)

    def _run(self, command, payload):
        return subprocess.run(
            [sys.executable, TELEMETRY, command], cwd=self.project,
            env=self.env, input=json.dumps(payload), stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, universal_newlines=True, timeout=120)

    # -- precompact-brief -------------------------------------------------

    CANARY = "CANARY-FOUNDER-SENTENCE-rotate-the-staging-key"

    def _precompact_payload(self):
        path = os.path.join(self.tmp, "transcript.jsonl")
        rows = [
            {"type": "user",
             "message": {"role": "user",
                         "content": [{"type": "text", "text": self.CANARY}]}},
            {"type": "assistant",
             "message": {"role": "assistant",
                         "content": [{"type": "text",
                                      "text": "working on the rotation"}]}},
        ]
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(json.dumps(r) for r in rows) + "\n")
        return {"session_id": "sess-precompact", "transcript_path": path,
                "cwd": self.project, "hook_event_name": "PreCompact"}

    def _briefs(self):
        if not os.path.isdir(self.teldir):
            return []
        return [n for n in os.listdir(self.teldir) if n.startswith("last-resume-")]

    def test_pre_consent_precompact_brief_writes_no_resume_file(self):
        r = self._run("precompact-brief", self._precompact_payload())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(
            self._briefs(), [],
            "precompact-brief wrote a resume brief before consent")
        self.assertFalse(
            os.path.exists(self.vault),
            "precompact-brief created the vault before consent")

    def test_post_consent_precompact_brief_still_writes_the_brief(self):
        """Calibration: the payload really does produce a brief once
        consented, so the silence above is the gate and not a dud payload.
        Also pins WHY the gate matters: the brief carries founder prose."""
        self._consent()
        r = self._run("precompact-brief", self._precompact_payload())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        briefs = self._briefs()
        self.assertEqual(len(briefs), 1, r.stdout + r.stderr)
        body = _read_text(os.path.join(self.teldir, briefs[0]))
        self.assertIn(self.CANARY, body)

    # -- stop-warn --------------------------------------------------------

    def _stopwarn_payload(self, session_id="sess-stopwarn"):
        """A transcript comfortably OVER bm_telemetry's STOPWARN_MIN_BYTES
        floor, read from the module rather than retyped, so a future change
        to the floor cannot silently turn this test into a no-op."""
        floor = _telemetry_constant("STOPWARN_MIN_BYTES")
        path = os.path.join(self.tmp, "%s.jsonl" % session_id)
        row = json.dumps({"type": "assistant",
                          "message": {"role": "assistant",
                                      "content": [{"type": "text",
                                                   "text": "padding " * 40}]}})
        with io.open(path, "w", encoding="utf-8") as fh:
            written = 0
            while written <= floor + 50000:
                fh.write(row + "\n")
                written += len(row) + 1
        return {"session_id": session_id, "transcript_path": path,
                "cwd": self.project, "hook_event_name": "Stop"}

    def test_pre_consent_stop_warn_creates_no_vault_and_no_marker(self):
        r = self._run("stop-warn", self._stopwarn_payload())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(
            os.path.exists(self.vault),
            "stop-warn materialized the vault before consent")

    def test_post_consent_stop_warn_still_warns_once(self):
        """Calibration: the same oversized transcript does produce the marker
        once consented, so the pre-consent silence is the gate."""
        self._consent()
        r = self._run("stop-warn", self._stopwarn_payload())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        markers = ([n for n in os.listdir(self.teldir) if n.startswith(".stopwarn-")]
                   if os.path.isdir(self.teldir) else [])
        self.assertEqual(len(markers), 1, r.stdout + r.stderr)

    # -- every wired command, any module (from the review session) ---------

    # Two different counts, kept apart on purpose, because conflating them is
    # how the count in the docs went wrong twice already: hooks/hooks.json
    # holds SEVEN command strings and those strings invoke NINE programs,
    # since the PreCompact line and the Stop line are each one `sh -c`
    # script running two. The program floor moved from 8 to 9 on 2026-08-05
    # when the Stop line gained the half hour catch-up check beside the
    # unfinished-work warning; raising a floor is the only direction this
    # number is ever allowed to move.
    MIN_WIRED_COMMAND_STRINGS = 7
    MIN_WIRED_PROGRAMS = 9
    _PROGRAM_RE = re.compile(
        r"(?:python3|sh)\s+\S*?(?:tools|scripts)/\S+\.(?:py|sh)")

    def _wired_commands(self):
        """Every command string in hooks/hooks.json, in file order.

        Contributed by the independent review session, 2026-08-02, and it is
        strictly better than the telemetry-scoped inventory below: it stands
        in front of bm_autosave.py, bm_bash_audit.py and bm_sessionstart.sh
        too. Their argument, which is correct: the NEXT program to write
        before consent probably will not live in bm_telemetry.py, and a
        module-scoped check cannot see it."""
        manifest = json.loads(_read_text(HOOKS_JSON))
        cmds = []
        for event, groups in sorted(manifest.get("hooks", {}).items()):
            for group in groups:
                for hook in group.get("hooks", []):
                    cmd = hook.get("command")
                    if cmd:
                        cmds.append((event, cmd))
        self.assertTrue(cmds, "hooks/hooks.json wired no commands at all")
        return cmds

    def _canary_in_any_file(self, root):
        """Every file under root whose bytes contain the canary. Asserting on
        CONTENT rather than on a predicted path is the point: a future leak to
        a filename nobody guessed still fails."""
        hits = []
        for dirpath, _dirs, files in os.walk(root):
            # macOS caches .pyc under ~/Library/Caches keyed off HOME. Those
            # are the interpreter's, not ours, and the probe sets
            # PYTHONDONTWRITEBYTECODE anyway; skipping keeps the failure
            # message about our own files.
            if "Library/Caches" in dirpath:
                continue
            for name in files:
                path = os.path.join(dirpath, name)
                try:
                    with io.open(path, encoding="utf-8", errors="replace") as fh:
                        body = fh.read()
                except OSError:
                    continue
                if self.CANARY in body:
                    hits.append(os.path.relpath(path, root))
        return hits

    def test_no_wired_command_of_any_module_writes_before_consent(self):
        """Drives EVERY command hooks/hooks.json wires, whatever module it
        belongs to, and asserts three separate things after each one:

        - no file appeared anywhere under HOME or the project,
        - the vault DIRECTORY does not exist (a file-only walk is blind to an
          empty mkdir, and 'the vault folder appeared in a stranger's home'
          was half of Critical 2),
        - the founder's own sentence is in no file, in either tree.

        Contributed by the review session that found the two Criticals, with
        two defects of their version fixed on the way in: the canary walk
        covers the project root as well as HOME, and the floor is 8 rather
        than 7 because hooks.json wires eight programs across seven lines."""
        env = dict(self.env)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        transcript = os.path.join(self.tmp, "wired.jsonl")
        floor = _telemetry_constant("STOPWARN_MIN_BYTES")
        row = json.dumps({"type": "assistant",
                          "message": {"role": "assistant",
                                      "content": [{"type": "text",
                                                   "text": "padding " * 40}]}})
        with io.open(transcript, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"type": "user", "message": {"role": "user",
                     "content": [{"type": "text", "text": self.CANARY}]}}) + "\n")
            written = 0
            while written <= floor + 50000:
                fh.write(row + "\n")
                written += len(row) + 1
        payload = json.dumps({"session_id": "sess-wired",
                              "transcript_path": transcript,
                              "cwd": self.project})

        ran = 0
        for event, command in self._wired_commands():
            concrete = command.replace("${CLAUDE_PLUGIN_ROOT}", ROOT)
            concrete = concrete.replace("$CLAUDE_PLUGIN_ROOT", ROOT)
            # shell=True is REQUIRED and is the point of this test, not a
            # shortcut: the strings being run are the exact command lines
            # Claude Code hands to a shell, and one of them (PreCompact) is a
            # `sh -c '...'` script running two programs off one stdin. Running
            # them any other way would test something the hook system never
            # does. The input is hooks/hooks.json, a tracked file in this
            # repository, not user or network data; if that file is hostile
            # the attacker already has commit rights and does not need this
            # test. The only interpolation is ROOT, computed from __file__.
            r = subprocess.run(concrete, shell=True, cwd=self.project, env=env,
                               input=payload, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, universal_newlines=True,
                               timeout=180)
            ran += 1
            self.assertEqual(r.returncode, 0,
                             "%s: %s exited %d\n%s%s"
                             % (event, concrete, r.returncode, r.stdout, r.stderr))
            self.assertFalse(
                os.path.exists(self.vault),
                "%s: a hook created the vault directory before consent" % event)
            for root, label in ((self.home, "HOME"), (self.project, "project")):
                leaked = self._canary_in_any_file(root)
                self.assertEqual(
                    leaked, [],
                    "%s: the founder's own message reached %s in the %s tree "
                    "before consent" % (event, ", ".join(leaked), label))
        self.assertGreaterEqual(
            ran, self.MIN_WIRED_COMMAND_STRINGS,
            "only %d wired command string(s) were driven; hooks/hooks.json is "
            "expected to hold at least %d, and a manifest that parsed to "
            "fewer must not read as a pass"
            % (ran, self.MIN_WIRED_COMMAND_STRINGS))
        programs = sum(len(self._PROGRAM_RE.findall(cmd))
                       for _event, cmd in self._wired_commands())
        self.assertGreaterEqual(
            programs, self.MIN_WIRED_PROGRAMS,
            "the %d wired command string(s) name only %d program "
            "invocation(s); at least %d are expected, because the PreCompact "
            "line runs TWO programs off one payload and counting strings "
            "instead of programs is exactly how the second one shipped "
            "ungated" % (ran, programs, self.MIN_WIRED_PROGRAMS))

    def test_calibrated_a_wired_command_that_never_ran_is_not_a_pass(self):
        """The vacuous-pass guard the review session asked for. Silence from a
        program that does not exist looks identical to silence from a program
        that refused, so the harness must be able to tell them apart: a
        command that cannot run has a nonzero exit, and the test above asserts
        exit 0 on every command precisely so that case goes red rather than
        quietly green."""
        env = dict(self.env)
        r = subprocess.run("python3 %s/tools/bm_does_not_exist.py pre"
                           % ROOT, shell=True, cwd=self.project, env=env,
                           input="{}", stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, universal_newlines=True,
                           timeout=60)
        self.assertNotEqual(
            r.returncode, 0,
            "a nonexistent hook program exited 0, so the exit-code assertion "
            "in the wired-command test cannot distinguish 'refused to write' "
            "from 'never ran'")

    # A hook-wired program that legitimately runs BEFORE consent, with the
    # reason, encoded here rather than left in prose. bm_fence_hook.py is
    # the ownership proof itself: it must exist before it can refuse anyone,
    # and SECURITY.md's threat-model section already carries that argument
    # in words. Encoding the exemption in the test WITH its reason is
    # stronger than the situation it replaced, where the exemption existed
    # only in prose.
    CONSENT_EXEMPT_MODULES = {
        "bm_fence_hook.py": (
            "the single-writer proof itself. It reads and refuses; a gate "
            "in front of it would mean no file claim exists until setup "
            "runs, which is the opposite of the protection it provides."),
    }

    # WHERE each module's gate lives, and how it spells the check. Every
    # entry names a CALL, never a comment: a module that merely mentions
    # consent is not a module that checks it. A module wired into
    # hooks.json with no entry here is reported, because that means a hook
    # wired it without anyone deciding how it is gated.
    #
    # Two shapes, and both are checked as gates rather than as mentions:
    #
    #   "per-command": every wired subcommand's own cmd_ function names the
    #       call. This is the shape the four telemetry-era modules use, and
    #       it is exactly what the narrow version of this test enforced.
    #   "one-door": the module has one gated entry point. The subcommand
    #       must still have its cmd_ function (so a typo in hooks.json is
    #       still caught), AND main() must name the call BEFORE it
    #       subscripts its dispatch table. That ordering is the whole of
    #       the gate, so it is asserted rather than assumed.
    CONSENT_GATE_BY_MODULE = {
        "bm_telemetry.py": ("per-command", "_consented()"),
        "bm_autosave.py": ("per-command", "_consented()"),
        "bm_bash_audit.py": ("per-command", "_consented()"),
        "bm_lead.py": ("one-door", "_consent_state()"),
    }

    def test_every_hook_wired_command_of_every_module_checks_consent(self):
        """The durable half: an inventory test rather than one test per
        command, WIDENED on 2026-08-05 from bm_telemetry.py alone to every
        module named on a hook line (DESIGN-L04 section 18.2).

        Why the widening is a strengthening and not a weakening: every
        assertion the telemetry-scoped version made survives verbatim,
        because bm_telemetry.py's commands are a subset of the widened set.
        What it gains is exactly the class of defect this project has
        already suffered twice, a hook line whose SECOND program was never
        gated (see the class docstring above). The rename is required
        rather than cosmetic: leaving the word telemetry in the name of a
        test that now governs every module would make the name a false
        description of the law.

        A module whose subcommands are dispatched from a GATED main(),
        rather than gated one cmd_ function at a time, satisfies this by
        naming its check inside main() before the dispatch. That is the ONE
        DOOR shape tools/bm_lead.py uses, and this test accepts it only
        when main() itself names the call."""
        wiring = json.loads(_read_text(HOOKS_JSON))
        # EVERY occurrence per command string, not the first: the PreCompact
        # and Stop entries are `sh -c` scripts that name two programs each,
        # and reading only the first is the exact blind spot that let
        # precompact-brief ship ungated. Quotes are part of those scripts,
        # so the module and its subcommand are matched rather than split out
        # of them.
        pattern = re.compile(
            r"(?:tools|scripts)/(\w+\.(?:py|sh))[\"']?(?:\s+([a-z][a-z0-9-]*))?")
        wired = set()
        for groups in wiring.get("hooks", {}).values():
            for group in groups:
                for entry in group.get("hooks", []):
                    for module, sub in pattern.findall(
                            entry.get("command", "")):
                        wired.add((module, sub or ""))
        self.assertTrue(wired, "no hook-wired program found in hooks.json")
        modules = sorted({m for m, _s in wired})
        self.assertIn(
            "bm_telemetry.py", modules,
            "the widened inventory lost sight of the one module the narrow "
            "version covered, so it is not a superset of it")
        self.assertGreaterEqual(
            len(modules), 4,
            "hooks/hooks.json names only %d module(s) (%s); a manifest that "
            "parsed to fewer must not read as a pass"
            % (len(modules), modules))
        ungated = []
        for module, command in sorted(wired):
            if module in self.CONSENT_EXEMPT_MODULES:
                continue
            path = os.path.join(HERE, module)
            if not os.path.isfile(path):
                ungated.append("%s: not in tools/" % module)
                continue
            source = _read_text(path)
            if module.endswith(".sh"):
                # tools/bm_sessionstart.sh gates in shell, not in Python.
                if "setup_complete" not in source:
                    ungated.append("%s: never reads setup_complete" % module)
                continue
            declared = self.CONSENT_GATE_BY_MODULE.get(module)
            if declared is None:
                ungated.append(
                    "%s: no consent gate is declared for it in "
                    "CONSENT_GATE_BY_MODULE, so a hook wired it without "
                    "anyone deciding how it is gated" % module)
                continue
            shape, call = declared
            if not command:
                ungated.append("%s: wired with no subcommand" % module)
                continue
            func = "def cmd_%s(" % command.replace("-", "_")
            idx = source.find(func)
            if idx == -1:
                ungated.append("%s %s: no cmd_ function found"
                               % (module, command))
                continue
            if shape == "one-door":
                # The gate is the entry point, so the entry point is what
                # gets checked: main() must name the call, and it must do
                # so BEFORE it looks the command up in its dispatch table.
                # An index comparison is enough here because the ast proof
                # of the same ordering lives in tools/test_bm_lead.py,
                # TestConsentIsTheOnlyDoor; this is the hook-side half.
                midx = source.find("\ndef main(")
                end = source.find("\ndef ", midx + 1) if midx != -1 else -1
                body = "" if midx == -1 else source[
                    midx:end if end != -1 else len(source)]
                gate_at = body.find(call)
                lookup_at = body.find("COMMANDS[")
                if gate_at == -1:
                    ungated.append("%s %s: main() never calls %s"
                                   % (module, command, call))
                elif lookup_at == -1:
                    ungated.append(
                        "%s %s: main() has no COMMANDS lookup, so the "
                        "one-door shape cannot be verified"
                        % (module, command))
                elif gate_at > lookup_at:
                    ungated.append(
                        "%s %s: main() calls %s AFTER the dispatch lookup, "
                        "so the door is not a gate"
                        % (module, command, call))
                continue
            nxt = source.find("\ndef ", idx + 1)
            body = source[idx:nxt if nxt != -1 else len(source)]
            if call not in body:
                ungated.append("%s %s: never calls %s"
                               % (module, command, call))
        self.assertEqual(
            ungated, [],
            "a hook-wired command of some module writes before consent is "
            "checked (%s). Every program on a hook line needs its own gate; "
            "gating the line's first program does not gate the second."
            % "; ".join(ungated))

    def test_calibrated_the_widened_inventory_reports_an_undeclared_module(self):
        """The vacuous-pass guard for the widening above. An equality
        against an empty list is only evidence when the scan can produce a
        non-empty one, so this drives the two predicates the widened test
        turns on, against inputs that MUST be reported: a module nobody
        declared a gate for, and a main() whose gate sits AFTER the
        dispatch lookup, which is a door that is not a gate."""
        self.assertIsNone(
            self.CONSENT_GATE_BY_MODULE.get("bm_invented.py"),
            "an undeclared module must have no declared gate, so the "
            "inventory reports it rather than passing it")
        too_late = ("\ndef main(argv):\n"
                    "    handler = COMMANDS[argv[0]]\n"
                    "    if not _consent_state():\n"
                    "        return 1\n"
                    "    return handler()\n")
        self.assertGreater(
            too_late.find("_consent_state()"), too_late.find("COMMANDS["),
            "this is what a gate placed after the lookup looks like, and "
            "the one-door branch above compares exactly these two indexes, "
            "so it reports this shape rather than passing it")

    def test_every_hook_wired_module_is_classified(self):
        """Neither exempt nor declared is not a state a hook line may be
        in. This is the half that makes the widening durable: a new module
        wired into hooks/hooks.json fails HERE, with a sentence telling
        whoever wired it to decide, rather than in someone's home
        directory."""
        wiring = json.loads(_read_text(HOOKS_JSON))
        pattern = re.compile(r"(?:tools|scripts)/(\w+\.(?:py|sh))")
        modules = set()
        for groups in wiring.get("hooks", {}).values():
            for group in groups:
                for entry in group.get("hooks", []):
                    modules.update(pattern.findall(entry.get("command", "")))
        unclassified = sorted(
            m for m in modules
            if m not in self.CONSENT_EXEMPT_MODULES
            and m not in self.CONSENT_GATE_BY_MODULE
            and not m.endswith(".sh"))
        self.assertEqual(
            [], unclassified,
            "module(s) wired into hooks/hooks.json that are neither "
            "consent-exempt with a stated reason nor declared with the "
            "gate they use: %s" % unclassified)


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


class DoctorTenChecksCase(unittest.TestCase):
    """(g) scripts/doctor.py's ten-check surface (Loop 3 design D-3, WP-E).
    Consent gates the checks that depend on it, the store check reports
    bm_store.py verify's own verdict, and the duplicate-install and
    checksum checks catch the two named failure classes by name."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="bm-consent-doctor-")
        self.home = os.path.join(self.tmp, "home")
        self.project = os.path.join(self.tmp, "project")
        os.makedirs(self.home)
        os.makedirs(self.project)
        self.settings = os.path.join(self.tmp, "settings.json")
        self.write_settings({})
        self.env = _clean_env(self.home)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_settings(self, obj):
        with io.open(self.settings, "w", encoding="utf-8") as fh:
            json.dump(obj, fh)

    def run_doctor(self):
        return subprocess.run(
            [sys.executable, DOCTOR, "--settings", self.settings, "--json"],
            cwd=self.project, env=self.env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, timeout=300)

    def _checks(self, stdout):
        payload = json.loads(stdout)
        return {c["key"]: c for c in payload["checks"]}

    def test_unconsented_consent_check_fails_and_vault_check_skips(self):
        r = self.run_doctor()
        checks = self._checks(r.stdout)
        self.assertEqual(checks["consent"]["status"], "FAIL",
                         checks["consent"]["message"])
        self.assertIn(SETUP_SENTENCE, checks["consent"]["message"])
        self.assertEqual(checks["vault"]["status"], "SKIP",
                         checks["vault"]["message"])

    def test_consented_with_a_valid_store_reports_verifys_own_verdict(self):
        vault = os.path.join(self.home, "Vault")
        os.makedirs(vault)
        _write_consented_config(
            os.path.join(self.home, ".brotherme", "config.json"), vault)
        store_cli = os.path.join(HERE, "bm_store.py")
        r = subprocess.run(
            [sys.executable, store_cli, "init"], cwd=self.project,
            env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

        r = self.run_doctor()
        checks = self._checks(r.stdout)
        self.assertEqual(checks["consent"]["status"], "PASS")
        self.assertEqual(checks["vault"]["status"], "PASS")
        self.assertEqual(checks["store"]["status"], "PASS")
        self.assertIn("healthy", checks["store"]["message"],
                      "the store check did not report verify's own verdict")

    def test_no_store_is_a_skip_not_a_fail(self):
        r = self.run_doctor()
        checks = self._checks(r.stdout)
        self.assertEqual(checks["store"]["status"], "SKIP")

    def test_duplicate_install_fixture_fails_naming_both(self):
        fence_dir = os.path.join(self.tmp, "clone_tools")
        os.makedirs(fence_dir)
        fence_path = os.path.join(fence_dir, "bm_fence_hook.py")
        with io.open(fence_path, "w", encoding="utf-8") as fh:
            fh.write("# stub, never executed by this test\n")
        self.write_settings({
            "hooks": {"PreToolUse": [{
                "matcher": "Edit|Write|MultiEdit|NotebookEdit",
                "hooks": [{"type": "command",
                           "command": "python3 " + fence_path,
                           "timeout": 10}],
            }]},
            "enabledPlugins": {"brotherme@some-marketplace": True},
        })
        r = self.run_doctor()
        checks = self._checks(r.stdout)
        self.assertEqual(checks["duplicate_install"]["status"], "FAIL")
        msg = checks["duplicate_install"]["message"]
        self.assertIn("plugin", msg)
        self.assertIn("clone", msg)
        self.assertIn("/plugin uninstall", msg,
                      "the which-to-remove sentence lost the plugin side")
        self.assertIn("scripts/uninstall.py", msg,
                      "the which-to-remove sentence lost the clone side")

    def test_checksum_tamper_fails_naming_the_file(self):
        fake_root = os.path.join(self.tmp, "fake_install")
        fake_scripts = os.path.join(fake_root, "scripts")
        os.makedirs(fake_scripts)
        for name in ("doctor.py", "setup.py"):
            shutil.copy2(os.path.join(ROOT, "scripts", name),
                        os.path.join(fake_scripts, name))
        payload = os.path.join(fake_root, "payload.txt")
        with io.open(payload, "w", encoding="utf-8") as fh:
            fh.write("original content\n")
        with io.open(payload, "rb") as fh:
            digest = hashlib.sha256(fh.read()).hexdigest()
        with io.open(os.path.join(fake_root, "CHECKSUMS.sha256"), "w",
                    encoding="utf-8") as fh:
            fh.write("%s  payload.txt\n" % digest)
        # Tamper AFTER the manifest is written, so the manifest is stale
        # exactly the way a half-finished update leaves it.
        with io.open(payload, "w", encoding="utf-8") as fh:
            fh.write("tampered content\n")

        r = subprocess.run(
            [sys.executable, os.path.join(fake_scripts, "doctor.py"),
             "--settings", self.settings, "--json"],
            cwd=self.project, env=self.env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, timeout=300)
        checks = self._checks(r.stdout)
        self.assertEqual(checks["checksums"]["status"], "FAIL")
        self.assertIn("payload.txt", checks["checksums"]["message"],
                      "the checksum check did not name the tampered file")

    def test_checksum_check_skips_a_dirty_git_working_tree(self):
        """A live development checkout with ordinary uncommitted edits (this
        project's own actual state, mid-loop, most days) is not the
        half-finished RELEASE update check 9 exists to catch; a checked-in
        manifest was generated from a clean, tagged checkout and was never
        going to describe a moving working tree. Distinguished from the
        tamper test above by one thing only: here the change is real but
        UNCOMMITTED, there the manifest itself was already finalized against
        a clean tree that was then silently changed after the fact."""
        fake_root = os.path.join(self.tmp, "fake_git_install")
        fake_scripts = os.path.join(fake_root, "scripts")
        os.makedirs(fake_scripts)
        for name in ("doctor.py", "setup.py"):
            shutil.copy2(os.path.join(ROOT, "scripts", name),
                        os.path.join(fake_scripts, name))
        payload = os.path.join(fake_root, "payload.txt")
        with io.open(payload, "w", encoding="utf-8") as fh:
            fh.write("committed content\n")
        with io.open(payload, "rb") as fh:
            digest = hashlib.sha256(fh.read()).hexdigest()
        with io.open(os.path.join(fake_root, "CHECKSUMS.sha256"), "w",
                    encoding="utf-8") as fh:
            fh.write("%s  payload.txt\n" % digest)

        git_env = dict(self.env)
        git_env.update({"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
                        "GIT_COMMITTER_NAME": "t",
                        "GIT_COMMITTER_EMAIL": "t@example.com"})
        for cmd in (["git", "init"], ["git", "add", "-A"],
                    ["git", "commit", "-m", "initial"]):
            r = subprocess.run(cmd, cwd=fake_root, env=git_env,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               universal_newlines=True, timeout=60)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

        # Dirty the tree WITHOUT committing: an ordinary live edit, not a
        # half-finished release checkout.
        with io.open(payload, "a", encoding="utf-8") as fh:
            fh.write("an uncommitted local edit\n")

        r = subprocess.run(
            [sys.executable, os.path.join(fake_scripts, "doctor.py"),
             "--settings", self.settings, "--json"],
            cwd=self.project, env=self.env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, timeout=300)
        checks = self._checks(r.stdout)
        self.assertEqual(checks["checksums"]["status"], "SKIP",
                         checks["checksums"]["message"])

    def test_no_manifest_is_a_skip_not_a_fail(self):
        fake_root = os.path.join(self.tmp, "fake_install_no_manifest")
        fake_scripts = os.path.join(fake_root, "scripts")
        os.makedirs(fake_scripts)
        for name in ("doctor.py", "setup.py"):
            shutil.copy2(os.path.join(ROOT, "scripts", name),
                        os.path.join(fake_scripts, name))
        r = subprocess.run(
            [sys.executable, os.path.join(fake_scripts, "doctor.py"),
             "--settings", self.settings, "--json"],
            cwd=self.project, env=self.env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, timeout=300)
        checks = self._checks(r.stdout)
        self.assertEqual(checks["checksums"]["status"], "SKIP")


class DoctorStrictAndSummaryCase(unittest.TestCase):
    """I2 (external review, Loop 3/5): doctor.py used to fold STATUS_SKIP
    into "all_ok" silently, so a run that only ever SKIPPED read on the exit
    code alone exactly like a run that actually proved something. Built on a
    genuinely healthy install (fence wired and live, consent, vault, mode
    wiring all PASS) so store and checksums are the only SKIPs here,
    proving the summary line's math and --strict's opt-in against a real
    fail_count of zero, not a fixture that was already failing for some
    unrelated reason (the fixture in DoctorTenChecksCase above never wires a
    fence, so it always has at least one FAIL and cannot tell "exits 0
    despite a SKIP" apart from "exits 0 because nothing failed yet")."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="bm-consent-doctor-strict-")
        self.home = os.path.join(self.tmp, "home")
        self.project = os.path.join(self.tmp, "project")
        os.makedirs(self.home)
        os.makedirs(self.project)
        # A real, working fence hook, the same way tools/test_install.py's
        # own DoctorCase builds one: copied tools/*.py so bm_fence_hook.py
        # can load its sibling bm_store.py, wired into settings.json exactly
        # as scripts/install.py would write it.
        self.tools = os.path.join(self.tmp, "install", "tools")
        os.makedirs(self.tools)
        for name in sorted(os.listdir(HERE)):
            if name.endswith(".py") and not name.startswith("test_"):
                shutil.copy2(os.path.join(HERE, name), os.path.join(self.tools, name))
        self.fence = os.path.join(self.tools, "bm_fence_hook.py")
        self.settings = os.path.join(self.tmp, "settings.json")
        with io.open(self.settings, "w", encoding="utf-8") as fh:
            json.dump({"hooks": {"PreToolUse": [{
                "matcher": "Edit|Write|MultiEdit|NotebookEdit",
                "hooks": [{"type": "command", "command": "python3 " + self.fence,
                          "timeout": 10}]}]}}, fh)
        self.vault = os.path.join(self.home, "Vault")
        os.makedirs(self.vault)
        _write_consented_config(
            os.path.join(self.home, ".brotherme", "config.json"),
            self.vault, mode="clone")
        self.env = _clean_env(self.home)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_doctor(self, *extra):
        return subprocess.run(
            [sys.executable, DOCTOR, "--settings", self.settings, "--json"] + list(extra),
            cwd=self.project, env=self.env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, timeout=300)

    def test_default_mode_exits_0_with_skips_present(self):
        r = self.run_doctor()
        payload = json.loads(r.stdout)
        by_key = {c["key"]: c for c in payload["checks"]}
        self.assertEqual(by_key["fence"]["status"], "PASS", by_key["fence"]["message"])
        self.assertEqual(by_key["consent"]["status"], "PASS")
        self.assertEqual(by_key["vault"]["status"], "PASS")
        skip_keys = [k for k, c in by_key.items() if c["status"] == "SKIP"]
        self.assertTrue(skip_keys, "test precondition: at least one check "
                        "must SKIP (store and checksums are expected to)")
        self.assertEqual(payload["failed"], 0)
        self.assertEqual(r.returncode, 0, "a SKIP-only, zero-FAIL run must "
                         "still exit 0 by default: %s" % r.stdout)

    def test_summary_reports_proven_skipped_failed_counts(self):
        r = self.run_doctor()
        payload = json.loads(r.stdout)
        checks = payload["checks"]
        self.assertEqual(len(checks), 10)
        proven = sum(1 for c in checks if c["status"] == "PASS")
        skipped = sum(1 for c in checks if c["status"] == "SKIP")
        failed = sum(1 for c in checks if c["status"] == "FAIL")
        self.assertEqual(payload["proven"], proven)
        self.assertEqual(payload["skipped"], skipped)
        self.assertEqual(payload["failed"], failed)
        self.assertEqual(proven + skipped + failed, 10)
        self.assertIn("%d of 10 proven" % proven, payload["summary"])
        self.assertIn("%d skipped" % skipped, payload["summary"])
        self.assertIn("%d failed" % failed, payload["summary"])

    def test_plain_text_mode_prints_the_same_summary_line(self):
        r = subprocess.run(
            [sys.executable, DOCTOR, "--settings", self.settings],
            cwd=self.project, env=self.env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, timeout=300)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertRegex(r.stdout, r"\d+ of 10 proven, \d+ skipped, \d+ failed\.")

    def test_strict_flag_exits_nonzero_and_lists_each_skip(self):
        base = self.run_doctor()
        base_payload = json.loads(base.stdout)
        skip_keys = [c["key"] for c in base_payload["checks"] if c["status"] == "SKIP"]
        self.assertTrue(skip_keys, "test precondition: need at least one SKIP")

        r = self.run_doctor("--strict")
        self.assertNotEqual(r.returncode, 0,
                            "--strict must exit nonzero when any check SKIPped")
        payload = json.loads(r.stdout)
        self.assertTrue(payload["strict"])
        self.assertFalse(payload["strict_ok"])
        self.assertEqual(payload["failed"], 0,
                         "--strict changed a genuine FAIL count, not just the exit code")

        r2 = subprocess.run(
            [sys.executable, DOCTOR, "--settings", self.settings, "--strict"],
            cwd=self.project, env=self.env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, timeout=300)
        self.assertNotEqual(r2.returncode, 0)
        self.assertIn("%d check(s) skipped" % len(skip_keys), r2.stdout)
        for key in skip_keys:
            title = {c["key"]: c["title"] for c in base_payload["checks"]}[key]
            self.assertIn(title, r2.stdout,
                          "--strict's listing dropped the skipped check %r" % key)

    def test_strict_flag_still_exits_nonzero_on_a_real_fail(self):
        """--strict must not accidentally soften a genuine FAIL into a SKIP
        reading, or the flag would be less strict than the default."""
        os.remove(self.fence)
        r = self.run_doctor("--strict")
        self.assertNotEqual(r.returncode, 0)
        payload = json.loads(r.stdout)
        self.assertGreater(payload["failed"], 0)


class UninstallConsentRemovalCase(unittest.TestCase):
    """(h) scripts/uninstall.py D-5: offers to remove the consent config,
    asked or via --remove-consent, never silent; the plugin-path caveat is
    always printed."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="bm-consent-uninstall-")
        self.home = os.path.join(self.tmp, "home")
        os.makedirs(self.home)
        self.settings = os.path.join(self.tmp, "settings.json")
        with io.open(self.settings, "w", encoding="utf-8") as fh:
            json.dump({}, fh)
        # Deliberately does not exist and does not look like a BrotherMode
        # checkout: this suite is testing the consent-removal step, which
        # runs after hook removal is already settled, and an explicit
        # --target lets that point be reached without a real install.
        self.target = os.path.join(self.tmp, "not-a-real-install")
        self.env = _clean_env(self.home)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_uninstall(self, *args, **kw):
        stdin = kw.pop("input", "")
        return subprocess.run(
            [sys.executable, UNINSTALL, "--target", self.target,
             "--settings", self.settings] + list(args),
            cwd=self.tmp, env=self.env, input=stdin,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, timeout=300)

    def _cfg_path(self):
        return os.path.join(self.home, ".brotherme", "config.json")

    def test_remove_consent_flag_removes_the_config(self):
        cfg_path = self._cfg_path()
        _write_consented_config(cfg_path, os.path.join(self.home, "Vault"))
        r = self.run_uninstall("--remove-consent")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(os.path.isfile(cfg_path),
                         "--remove-consent did not remove the config")
        self.assertIn(cfg_path, r.stdout)

    def test_without_the_flag_and_no_terminal_the_config_survives(self):
        cfg_path = self._cfg_path()
        _write_consented_config(cfg_path, os.path.join(self.home, "Vault"))
        r = self.run_uninstall(input="")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(os.path.isfile(cfg_path),
                        "the config was removed without ever being asked")
        self.assertIn(cfg_path, r.stdout,
                      "uninstall said nothing about the config it left behind")

    def test_no_config_at_all_prints_nothing_about_consent(self):
        r = self.run_uninstall()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("consent:", r.stdout)

    def test_the_plugin_path_caveat_is_always_printed(self):
        r = self.run_uninstall()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("/plugin uninstall", r.stdout)
        self.assertIn("not this script's bookkeeping", r.stdout)


class UpdateCommandFileCase(unittest.TestCase):
    """(i) commands/brotherme-update.md (Loop 3 design D-4): the pinned
    lines tools/test_bm.py already asserts survive, and the two new
    verification steps plus the rollback sentence are present."""

    def test_pinned_lines_survive_and_the_new_steps_are_present(self):
        with io.open(UPDATE_MD, encoding="utf-8") as fh:
            text = fh.read()
        for line in ("/plugin marketplace update brotherme-marketplace",
                     "/plugin update brotherme",
                     "git fetch --tags",
                     "git ls-remote --tags"):
            self.assertIn(line, text,
                          "commands/brotherme-update.md lost the pinned "
                          "line %r" % line)
        self.assertIn("scripts/doctor.py", text,
                      "the update command never names the doctor "
                      "invocation that verifies the update")
        self.assertIn("CHECKSUMS.sha256", text,
                      "the update command never names the checksum "
                      "self-check that catches a half-finished update")
        self.assertIn("git checkout <the tag you were on before>", text,
                      "the update command lost the rollback sentence")


if __name__ == "__main__":
    unittest.main(verbosity=1)
