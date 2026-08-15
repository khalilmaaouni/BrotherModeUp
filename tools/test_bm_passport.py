#!/usr/bin/env python3
"""Regression tests for tools/bm_passport.py, the change passport's producer
half (docs/specs/2026-08-15-change-passport-seam.md in the BrotherSBE
repository is the contract this tool fills a hole in).

WHAT THIS SUITE IS ACTUALLY DEFENDING
  Three rules from the contract, each load bearing and each proven by a test
  whose guard was removed by hand to watch it go red:

  1. A hollow value is never written. An empty string, an empty list, or a
     null reads as absence on the consuming side, so a field this tool
     cannot establish honestly must be OMITTED, never padded to look
     filled.
  2. Direction of travel: this tool writes the deposit and reads NOTHING
     under .sbe/. A poisoned tasks.json sitting next to a healthy store
     must change nothing about what this tool produces.
  3. Absent, corrupt, and healthy stores are three DIFFERENT reported
     states, and none of the three ever crashes the tool.

Every fixture is a tempfile.TemporaryDirectory(), never the real project
store. The CLI is invoked as a real subprocess so its argument parsing,
exit codes, and stdout are exercised exactly as a caller would see them.

Standard library only. Run: python3 tools/test_bm_passport.py
"""
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TOOL_PATH = os.path.join(HERE, "bm_passport.py")


def run_cli(*args, **kw):
    """Invoke the CLI as a real subprocess, with BROTHERMODE_ROOT scrubbed
    so a variable set on the developer's own machine can never leak into a
    test that expects an explicit --root to decide the outcome. `env_over`
    (a dict) is merged on top when a test needs to simulate an environment
    where `git config user.name` has nothing to say."""
    env = dict(os.environ)
    env.pop("BROTHERMODE_ROOT", None)
    env.update(kw.get("env_over") or {})
    return subprocess.run(
        [sys.executable, TOOL_PATH] + list(args),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        universal_newlines=True, cwd=ROOT, env=env)


def write_text(directory, relpath, content="placeholder\n"):
    path = os.path.join(directory, relpath)
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)
    with io.open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    return path


def read_deposit(root, out=None):
    path = out or os.path.join(root, ".sbe", "passport.json")
    with io.open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_bm_store_module():
    """Load bm_store.py the same way bm_passport.py does, so a test fixture
    can build a real store without shelling out to a second CLI."""
    import importlib.util
    path = os.path.join(HERE, "bm_store.py")
    spec = importlib.util.spec_from_file_location(
        "bm_store_for_passport_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def claim_one(root, session_id="sess-abc", files=("a.py", "b.py")):
    """Build a real, healthy store at `root` carrying one active claim.
    Uses the writable Store directly (not the CLI): this is fixture setup,
    not the thing under test."""
    mod = _load_bm_store_module()
    store = mod.Store(root, create=True)
    try:
        store.claim("unit-a", "ephemeral", objective="test fixture",
                    files=list(files), owner="builder", session_id=session_id)
    finally:
        store.close()


def claim_then_park(root, name, session_id, files):
    """Add one claim and move it OUT of the active state, which is the state
    a session's own record is in at the moment it closes and deposits. Parking
    rather than completing on purpose: completing requires evidence, and this
    fixture is about the STATE the producer reads, not about evidence."""
    mod = _load_bm_store_module()
    store = mod.Store(root, create=True)
    try:
        record = store.claim(name, "ephemeral", objective="test fixture",
                             files=list(files), owner="builder",
                             session_id=session_id)
        # Record is a __slots__ object, not a dict: attribute access only.
        # session_id must be passed back: the store's ownership guard refuses
        # a cross-session move of an ACTIVE record, which is the single-writer
        # rule doing its job, so the fixture parks as the same session.
        store.transition(record.lifecycle_uuid, record.version, "parked",
                         session_id=session_id)
    finally:
        store.close()


#: An env override that makes `git config user.name` resolve to nothing,
#: without touching this worktree's own git configuration: HOME points at
#: an empty directory (no ~/.gitconfig) and the global/system config files
#: are pointed at /dev/null, so only a repo-local .git/config (which these
#: bare tempdir fixtures never have) could still answer. Applied to the
#: SUBPROCESS environment only, via subprocess.run's own `env=`, never to
#: this test runner's own environment or to any git command this file
#: itself might run.
def _no_git_identity_env(tmp):
    empty_home = os.path.join(tmp, "empty-home")
    os.makedirs(empty_home, exist_ok=True)
    return {
        "HOME": empty_home,
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
    }


class HelpAndUsageTests(unittest.TestCase):
    def test_help_prints_usage_and_exits_zero(self):
        result = run_cli("--help")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Usage: ", result.stdout)
        self.assertIn("bm_passport.py", result.stdout)
        self.assertIn("--accountable", result.stdout)

    def test_usage_never_names_the_repo_relative_path(self):
        """P17: a packaged install has no tools/ directory, so a usage line
        that says `python3 tools/bm_passport.py` names a file the reader
        does not have. This is the local half of the sweep
        test_bm_store.py's TestP17InstructionTextMatchesTheInstalledLayout
        runs over every shipping tool; kept here too so the failure lands
        in this tool's own suite rather than only in the store's."""
        result = run_cli("--help")
        self.assertNotIn("python3 tools/bm_", result.stdout)
        bogus = run_cli("--bogus")
        self.assertNotIn("python3 tools/bm_", bogus.stderr)

    def test_unknown_argument_is_a_usage_error(self):
        result = run_cli("--bogus")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("unknown argument", result.stderr)


class ThreeStoreStatesTests(unittest.TestCase):
    """Rule 3: absent, corrupt, and healthy are three DIFFERENT reported
    states, and none of them crashes (exit 0, never a traceback, never
    exit 2's NO-DATA path, since a store being absent is an ordinary,
    fully-expected outcome for this tool, not a failure to determine
    anything)."""

    def test_absent_store_is_reported_and_does_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_cli("--root", tmp, "--accountable", "Test Person")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("store: absent", result.stdout)
            deposit = read_deposit(tmp)
        self.assertIn("no BrotherMode store",
                      " ".join(deposit["whatWasNotEstablished"]))

    def test_corrupt_store_is_reported_distinctly_and_does_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_text(tmp, os.path.join(".brothermode", "store.sqlite3"),
                      "not a real sqlite file" * 5)
            result = run_cli("--root", tmp, "--accountable", "Test Person")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("store: unreadable", result.stdout)
            deposit = read_deposit(tmp)
        joined = " ".join(deposit["whatWasNotEstablished"])
        self.assertIn("could not be", joined)
        self.assertNotIn("no BrotherMode store at", joined)

    def test_healthy_store_is_reported_as_ok_and_does_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            claim_one(tmp, session_id="sess-abc", files=("a.py", "b.py"))
            result = run_cli("--root", tmp, "--accountable", "Test Person")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("store: ok", result.stdout)
            deposit = read_deposit(tmp)
        who = " ".join(deposit["whoDidIt"])
        self.assertIn("session sess-abc", who)
        self.assertIn("2 files", who)

    def test_the_three_states_are_pairwise_distinct(self):
        """Same assertion, phrased the other way: the three states must
        never collapse into each other. Guards against a rewrite that
        makes 'absent' and 'unreadable' report the identical sentence."""
        with tempfile.TemporaryDirectory() as tmp_absent, \
             tempfile.TemporaryDirectory() as tmp_corrupt, \
             tempfile.TemporaryDirectory() as tmp_healthy:
            write_text(tmp_corrupt, os.path.join(".brothermode", "store.sqlite3"),
                      "not a real sqlite file" * 5)
            claim_one(tmp_healthy)

            r_absent = run_cli("--root", tmp_absent, "--accountable", "P")
            r_corrupt = run_cli("--root", tmp_corrupt, "--accountable", "P")
            r_healthy = run_cli("--root", tmp_healthy, "--accountable", "P")

        lines = [l for r in (r_absent, r_corrupt, r_healthy)
                for l in r.stdout.splitlines() if l.startswith("store: ")]
        self.assertEqual(len(lines), 3)
        # The STATE WORD, not the whole line. Each line embeds its own
        # tempdir path, so comparing whole lines gave three distinct strings
        # even when the state words collapsed to one: the test passed for the
        # wrong reason until an adversarial review replayed it with all three
        # states set to "unreadable" and watched it stay green.
        states = [l.split("store: ", 1)[1].split()[0] for l in lines]
        self.assertEqual(len(set(states)), 3, states)
        self.assertEqual(states, ["absent", "unreadable", "ok"], states)


class HollowValueTests(unittest.TestCase):
    """Rule 1: an empty string, an empty list, or a null is never written.
    A field this tool cannot establish is OMITTED from the JSON entirely,
    for each of the three fields it owns."""

    def test_who_did_it_is_omitted_not_written_hollow_when_nothing_carries_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            # No store (so no session/claim lines) and no accountable
            # source (no --accountable, and git config is made to answer
            # nothing): whoDidIt has literally nothing to carry.
            result = run_cli("--root", tmp, env_over=_no_git_identity_env(tmp))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            deposit = read_deposit(tmp)
        self.assertNotIn("whoDidIt", deposit)
        self.assertIn("whoDidIt: NOT established, omitted", result.stdout)

    def test_where_it_came_from_is_never_hollow_even_on_whitespace_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            # A whitespace-only --method must not become a hollow deposited
            # string; the tool falls back to its honest default instead of
            # writing "   ".
            result = run_cli("--root", tmp, "--accountable", "Test Person",
                             "--method", "   ")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            deposit = read_deposit(tmp)
        self.assertIn("whereItCameFrom", deposit)
        self.assertEqual(deposit["whereItCameFrom"].strip(), deposit["whereItCameFrom"])
        self.assertNotEqual(deposit["whereItCameFrom"].strip(), "")

    def test_what_was_not_established_is_never_written_as_an_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            # The most favorable case this tool can hit: a healthy store
            # with one attributed claim and an explicit accountable name.
            # Even here, whatWasNotEstablished must carry at least the
            # tool's own always-true scope-limit line, never [].
            claim_one(tmp)
            result = run_cli("--root", tmp, "--accountable", "Test Person")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            deposit = read_deposit(tmp)
        self.assertIn("whatWasNotEstablished", deposit)
        self.assertTrue(len(deposit["whatWasNotEstablished"]) > 0)

    def test_no_field_in_the_deposit_is_ever_an_empty_or_null_value(self):
        """Belt and suspenders across ALL THREE store states, not one.

        This docstring used to claim "every state this tool can hit" while the
        body exercised exactly one (a bare root with no git identity). An
        adversarial review caught the gap: a claim of breadth with a body of
        one is the same overclaim this tool exists to report, in the suite
        that polices it."""
        for label, build in (
                ("absent", lambda d: None),
                ("corrupt", lambda d: write_text(
                    d, os.path.join(".brothermode", "store.sqlite3"),
                    "not a real sqlite file" * 5)),
                ("healthy", lambda d: claim_one(d))):
            with tempfile.TemporaryDirectory() as tmp:
                build(tmp)
                result = run_cli("--root", tmp,
                                 env_over=_no_git_identity_env(tmp))
                self.assertEqual(result.returncode, 0,
                                 "%s: %s%s" % (label, result.stdout,
                                               result.stderr))
                deposit = read_deposit(tmp)
            for key, value in deposit.items():
                self.assertNotEqual(value, "", "%s: %s is an empty string"
                                    % (label, key))
                self.assertNotEqual(value, [], "%s: %s is an empty list"
                                    % (label, key))
                self.assertIsNotNone(value, "%s: %s is null" % (label, key))

    def test_the_single_state_version_of_the_check_still_holds(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_cli("--root", tmp, env_over=_no_git_identity_env(tmp))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            deposit = read_deposit(tmp)
        for key, value in deposit.items():
            self.assertTrue(value is not None, key)
            if isinstance(value, str):
                self.assertNotEqual(value.strip(), "", key)
            if isinstance(value, list):
                self.assertGreater(len(value), 0, key)


class DirectionOfTravelTests(unittest.TestCase):
    """Rule 2: this tool writes the deposit and reads NOTHING under .sbe/.
    A poisoned tasks.json sitting next to the exact same store must not
    change one byte of what this tool produces."""

    def test_a_poisoned_sbe_tasks_json_changes_nothing_about_the_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            claim_one(tmp, session_id="sess-fixed", files=("x.py",))

            before = run_cli("--root", tmp, "--out",
                             os.path.join(tmp, "before.json"),
                             "--accountable", "Test Person")
            self.assertEqual(before.returncode, 0, before.stdout + before.stderr)
            deposit_before = read_deposit(tmp, out=os.path.join(tmp, "before.json"))

            # Poisoned on purpose: invalid JSON, so ANY read of it (even a
            # failed one that leaked into the output) would show up as a
            # difference from the "before" run.
            write_text(tmp, os.path.join(".sbe", "tasks.json"),
                      "{ this is not valid json at all !!! ")
            write_text(tmp, os.path.join(".sbe", "evidence", "fake.json"),
                      '{"command": "rm -rf /", "verdict": "PASS"}')
            write_text(tmp, os.path.join(".sbe", "passport.json"),
                      '{"whoDidIt": ["a lie planted by the assurance side"]}')

            after = run_cli("--root", tmp, "--out",
                            os.path.join(tmp, "after.json"),
                            "--accountable", "Test Person")
            self.assertEqual(after.returncode, 0, after.stdout + after.stderr)
            deposit_after = read_deposit(tmp, out=os.path.join(tmp, "after.json"))

        self.assertEqual(deposit_before, deposit_after)
        self.assertNotIn("a lie planted by the assurance side",
                         json.dumps(deposit_after))


class DepositShapeTests(unittest.TestCase):
    """The deposit keys match the contract's deposit key column exactly,
    and multiple sessions each get their own line rather than being
    merged or dropped."""

    def test_deposit_uses_the_exact_contract_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            claim_one(tmp)
            result = run_cli("--root", tmp, "--accountable", "Test Person")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            deposit = read_deposit(tmp)
        for key in deposit:
            self.assertIn(key, ("whoDidIt", "whereItCameFrom",
                                "whatWasNotEstablished"))
        # Both directions. Rejecting unexpected keys alone is not a contract
        # check: an adversarial review replayed the loop above against {} and
        # against a deposit missing whoDidIt entirely, and it passed both, so
        # a regression that dropped a field would have stayed green.
        for key in ("whoDidIt", "whereItCameFrom", "whatWasNotEstablished"):
            self.assertIn(key, deposit, deposit)

    def test_out_flag_writes_to_the_requested_path_instead_of_the_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            custom = os.path.join(tmp, "custom", "deposit.json")
            result = run_cli("--root", tmp, "--out", custom,
                             "--accountable", "Test Person")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(os.path.isfile(custom))
            self.assertFalse(os.path.isfile(
                os.path.join(tmp, ".sbe", "passport.json")))

    def test_out_path_that_cannot_be_written_is_the_one_exit_1_case(self):
        with tempfile.TemporaryDirectory() as tmp:
            # A file where a directory needs to go: os.makedirs on the
            # parent must fail with OSError (FileExistsError / NotADirectoryError).
            blocker = os.path.join(tmp, "blocker")
            write_text(tmp, "blocker", "not a directory\n")
            bad_out = os.path.join(blocker, "sub", "deposit.json")
            result = run_cli("--root", tmp, "--out", bad_out,
                             "--accountable", "Test Person")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("could not write", result.stderr)


class SilentGapTests(unittest.TestCase):
    """The regression suite for the defect an adversarial review found: a
    CONFIDENTLY WRONG field 2 beside a field 4 that says nothing is missing.

    Field 4 is the product's whole claim, the one thing no green gate can
    fake, so every way this producer can be partially blind gets a test that
    fails if the disclosure is removed. Each test asserts the SPECIFIC
    sentence, not merely that field 4 is non-empty: an unconditional scope
    line is always present, so 'field 4 has content' would pass with every
    real gap silently dropped, which is exactly how the defect survived
    fourteen passing tests."""

    def test_a_closed_record_is_named_rather_than_silently_skipped(self):
        """THE CRITICAL. Only active records are read, and a session deposits
        at CLOSE, when its own record is most likely already parked or
        complete. So the tool could name a concurrent, unrelated session as
        the author and report no gap at all."""
        with tempfile.TemporaryDirectory() as tmp:
            claim_then_park(tmp, "did-the-work", "sess-DID-THE-WORK",
                            ["x.py", "y.py"])
            claim_one(tmp, session_id="sess-OTHER-CONCURRENT",
                      files=("unrelated.py",))
            result = run_cli("--root", tmp, "--accountable", "Test Person")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            deposit = read_deposit(tmp)

        gaps = " ".join(deposit.get("whatWasNotEstablished", []))
        self.assertIn("not active", gaps, deposit)
        self.assertIn("were NOT read", gaps, deposit)
        # The other session is still named, which is honest ONLY because the
        # gap above tells the reader they are seeing active claims alone.
        self.assertIn("sess-OTHER-CONCURRENT",
                      " ".join(deposit.get("whoDidIt", [])), deposit)

    def test_a_git_derived_name_says_it_was_inferred(self):
        """`git config user.name` answers who owns the laptop, not who is
        accountable for this change, and answers even outside a repository."""
        with tempfile.TemporaryDirectory() as tmp:
            claim_one(tmp)
            result = run_cli("--root", tmp)   # no --accountable on purpose
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            deposit = read_deposit(tmp)

        gaps = " ".join(deposit.get("whatWasNotEstablished", []))
        who = " ".join(deposit.get("whoDidIt", []))
        if "accountable:" in who:
            self.assertIn("INFERRED", gaps, deposit)
            self.assertIn("git config", gaps, deposit)
        else:
            # No git identity reachable: the other honest answer, and the
            # field must then be omitted rather than padded.
            self.assertIn("could not be established", gaps, deposit)

    def test_an_explicit_accountable_name_carries_no_inference_gap(self):
        """The control for the test above. Without it, asserting the INFERRED
        sentence would still pass if the tool emitted that sentence always."""
        with tempfile.TemporaryDirectory() as tmp:
            claim_one(tmp)
            result = run_cli("--root", tmp, "--accountable", "Stated Person")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            deposit = read_deposit(tmp)

        self.assertNotIn("INFERRED",
                         " ".join(deposit.get("whatWasNotEstablished", [])))
        self.assertIn("accountable: Stated Person",
                      " ".join(deposit.get("whoDidIt", [])))

    def test_a_session_claiming_no_files_is_named_as_a_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            claim_one(tmp, session_id="sess-nofiles", files=())
            result = run_cli("--root", tmp, "--accountable", "Test Person")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            deposit = read_deposit(tmp)

        self.assertIn("claim no files at all",
                      " ".join(deposit.get("whatWasNotEstablished", [])), deposit)


class PathFlagTests(unittest.TestCase):
    """An empty value for a flag that decides WHERE bytes land is refused,
    never treated as absent. `--out "$OUT"` with an unset variable used to
    fall through to the project's real .sbe/passport.json."""

    def test_empty_out_is_refused_rather_than_writing_the_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            claim_one(tmp)
            result = run_cli("--root", tmp, "--out", "", "--accountable", "P")
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("empty value", result.stderr)
            self.assertFalse(
                os.path.isfile(os.path.join(tmp, ".sbe", "passport.json")),
                "an empty --out silently wrote the default deposit path")

    def test_empty_root_is_refused(self):
        result = run_cli("--root", "", "--accountable", "P")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("empty value", result.stderr)

    def test_an_unresolvable_root_is_exit_2_and_says_NO_DATA(self):
        """The exit 2 path, which the docstring documents and nothing asserted.

        Three exits are documented: 0 when a deposit was written whatever it
        could establish, 1 when the deposit could not be written, and 2 for a
        usage error or a root that could not be resolved at all. The last is
        not a finding about a change, it is a failure to find a change to
        report on, and reporting it as 0 would be the tool claiming it looked
        when it did not."""
        missing = os.path.join(tempfile.gettempdir(),
                               "bm-passport-no-such-dir-xyzzy")
        self.assertFalse(os.path.exists(missing))
        result = run_cli("--root", missing, "--accountable", "P")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("NO-DATA", result.stdout)

    def test_a_failed_write_leaves_the_previous_deposit_intact(self):
        """What temp-plus-replace actually buys, asserted rather than assumed.

        Writing the deposit in place truncates it first, so a failure mid-write
        leaves a half-written file that the consumer classifies as CORRUPT,
        which is a worse answer than the previous deposit or than none at all.
        The failure is injected by making the temp path unwritable (a directory
        sits where the temp FILE must go), which is the closest reachable
        analogue of a disk failure without root."""
        with tempfile.TemporaryDirectory() as tmp:
            claim_one(tmp)
            out = os.path.join(tmp, "deposit.json")

            first = run_cli("--root", tmp, "--out", out, "--accountable", "First")
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            with io.open(out, encoding="utf-8") as fh:
                before = fh.read()
            self.assertIn("First", before)

            # A directory where the temp FILE must be written: open() raises
            # IsADirectoryError, an OSError, on the temp path only.
            os.mkdir(out + ".tmp")

            second = run_cli("--root", tmp, "--out", out,
                             "--accountable", "Second")
            self.assertEqual(second.returncode, 1,
                             second.stdout + second.stderr)
            self.assertIn("could not write", second.stderr)

            with io.open(out, encoding="utf-8") as fh:
                after = fh.read()
        self.assertEqual(before, after,
                         "the failed write changed the previous deposit; "
                         "temp-plus-replace is not protecting it")
        json.loads(after)   # still parseable, so never classified CORRUPT

    def test_no_temp_file_is_left_behind_by_a_successful_write(self):
        """The deposit is written to a .tmp path and moved into place, so a
        failure mid-write cannot leave a truncated deposit the consumer would
        classify as corrupt. The move must actually happen."""
        with tempfile.TemporaryDirectory() as tmp:
            claim_one(tmp)
            out = os.path.join(tmp, "deposit.json")
            result = run_cli("--root", tmp, "--out", out, "--accountable", "P")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(os.path.isfile(out))
            self.assertFalse(os.path.isfile(out + ".tmp"))


if __name__ == "__main__":
    unittest.main()
