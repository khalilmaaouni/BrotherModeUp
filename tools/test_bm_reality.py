#!/usr/bin/env python3
"""Regression tests for tools/bm_reality.py, the smallest verified-reality
record (A5, docs/NORTH-STAR-CHAIN.md's own terminal stage) and its store
counterpart, tools/bm_store.py's reality_records table (schema 21).

WHAT THIS SUITE IS ACTUALLY DEFENDING
  1. THE THREE REFUSALS, at the store layer, each proven by asserting the
     exact reason code an OwnershipRefused carries, not merely a nonzero
     exit: R1 refuses an anonymous or release-less 'accepted' row; R2
     refuses any of the other four kinds whose links_to does not name an
     EXISTING 'accepted' row; R3 refuses a 'defect' with an empty
     intent_ref. Every one of these is unreachable through
     tools/bm_reality.py's own CLI (its argument parser already refuses a
     missing --accountable/--release before the store is ever called, and
     `defect` always supplies its own intent_ref), which is precisely the
     point: the store's own refusal is the last line, not the CLI's, so
     these three are exercised by calling Store.add_reality_record
     directly, the same way a future caller other than this CLI would.
  2. THE RETURN EDGE, end to end, through the real CLI as a subprocess:
     `defect` must append a new docs/plan/QUEUE.json item (stage
     'intent', carrying provenance naming the reality record) and the
     reality row it writes must carry that exact queue item id as its own
     intent_ref, in both directions.
  3. QUEUE-FIRST, REALITY-SECOND: a queue append that fails (a malformed
     existing queue file) must leave NO reality row behind. A defect
     record pointing at a queue item that does not exist would be worse
     than no record at all.
  4. THE SCHEMA MIGRATION, proven against a REAL schema-20 store (a
     genuine store, opened and written to, then stripped back), never
     hand-written DDL, the same discipline tools/test_bm_store.py's own
     TestSchema20CapabilityReceipts uses for the schema bump immediately
     before this one.
  5. INSERT ONLY, asserted MECHANICALLY: no UPDATE or DELETE FROM
     reality_records statement exists anywhere in tools/bm_store.py's own
     source, found by searching the actual SQL shape rather than trusting
     what its docstrings claim.

Every fixture is a tempfile.TemporaryDirectory(), never the real project
store. The CLI is invoked as a real subprocess (run_cli) for the
integration-shaped tests, so its argument parsing, exit codes and stdout
are exercised exactly as a caller would see them; the three refusals are
exercised through the store's own Python API directly, for the reason
given above.

Standard library only. Run: python3 tools/test_bm_reality.py
"""
import io
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TOOL_PATH = os.path.join(HERE, "bm_reality.py")
STORE_SOURCE_PATH = os.path.join(HERE, "bm_store.py")


def run_cli(*args, **kw):
    """Invoke the CLI as a real subprocess, with BROTHERMODE_ROOT scrubbed
    so a variable set on the developer's own machine can never leak into a
    test that expects an explicit --root to decide the outcome. Every call
    site below passes --root explicitly rather than relying on cwd, the
    same discipline tools/test_bm_passport.py's own run_cli documents."""
    env = dict(os.environ)
    env.pop("BROTHERMODE_ROOT", None)
    env.update(kw.get("env_over") or {})
    return subprocess.run(
        [sys.executable, TOOL_PATH] + list(args),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        universal_newlines=True, cwd=ROOT, env=env)


def _load_bm_store_module():
    """Load bm_store.py the same way bm_reality.py itself does, so a test
    fixture can build (or inspect) a real store without shelling out to a
    second CLI. tools/test_bm_passport.py's own _load_bm_store_module is
    the template."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "bm_store_for_reality_test", STORE_SOURCE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def init_store(root):
    """A real, healthy, empty store at `root`, built through the writable
    Store directly (never the CLI): this is fixture setup, not the thing
    under test, the same distinction tools/test_bm_passport.py's own
    claim_one draws."""
    mod = _load_bm_store_module()
    store = mod.Store(root, create=True)
    store.close()


def write_queue(root, items=None):
    """A minimal, valid docs/plan/QUEUE.json at `root`, the shape
    tools/bm_idle.py's own _validate_queue requires (schema, min_depth,
    items)."""
    path = os.path.join(root, "docs", "plan", "QUEUE.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8") as handle:
        json.dump({"schema": 1, "min_depth": 1, "items": items or []},
                  handle)
    return path


def read_queue(root):
    path = os.path.join(root, "docs", "plan", "QUEUE.json")
    with io.open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _accepted_record_id(store, release_id):
    """The record_id of the 'accepted' row for `release_id`, read directly
    off the store rather than screen-scraped from `show`'s stdout: the
    integration tests below assert stdout separately, and a test that
    parses its own tool's display format to drive its next step would be
    testing that format twice over."""
    rows = store.list_reality_records(release_id=release_id, raw=True)
    for row in rows:
        if row["kind"] == "accepted":
            return row["record_id"]
    return None


class TestRoundTrip(unittest.TestCase):
    """1. accept, then show, returns the same release identity,
    accountable and passport back."""

    def test_accept_then_show_round_trips_release_identity(self):
        with tempfile.TemporaryDirectory() as d:
            init_store(d)
            accept = run_cli(
                "accept", "--release", "v1.2.3+deadbeef",
                "--accountable", "Jane Doe", "--passport",
                "a" * 64, "--root", d)
            self.assertEqual(accept.returncode, 0, accept.stderr)

            show = run_cli("show", "--release", "v1.2.3+deadbeef",
                           "--root", d)
            self.assertEqual(show.returncode, 0, show.stderr)
            self.assertIn("v1.2.3+deadbeef", show.stdout)
            self.assertIn("Jane Doe", show.stdout)
            self.assertIn("a" * 64, show.stdout)

            mod = _load_bm_store_module()
            store = mod.ReadOnlyStore(d)
            try:
                rows = store.list_reality_records(
                    release_id="v1.2.3+deadbeef", raw=True)
            finally:
                store.close()
            self.assertEqual(1, len(rows))
            self.assertEqual("accepted", rows[0]["kind"])
            self.assertEqual("v1.2.3+deadbeef", rows[0]["release_id"])
            self.assertEqual("Jane Doe", rows[0]["accountable"])
            self.assertEqual("a" * 64, rows[0]["passport_sha256"])


class TestTheThreeRefusals(unittest.TestCase):
    """2, 3, 4. R1, R2 and R3, exercised directly against
    Store.add_reality_record (see this file's own module docstring for
    why the CLI cannot reach any of the three), each asserting the exact
    reason code, not merely a raise."""

    def setUp(self):
        self.mod = _load_bm_store_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = self.tmp.name
        self.store = self.mod.Store(self.root, create=True)
        self.addCleanup(self.store.close)

    def _accept(self, release_id="v1", accountable="Khalil"):
        return self.store.add_reality_record(
            {"kind": "accepted", "release_id": release_id,
             "accountable": accountable})["record_id"]

    # -- R1: an anonymous or release-less acceptance is refused ----------

    def test_r1_accepted_with_no_accountable_is_refused(self):
        with self.assertRaises(self.mod.OwnershipRefused) as cm:
            self.store.add_reality_record(
                {"kind": "accepted", "release_id": "v1", "accountable": ""})
        self.assertEqual("unaccountable-acceptance", cm.exception.reason)

    def test_r1_accepted_with_no_release_id_is_refused(self):
        with self.assertRaises(self.mod.OwnershipRefused) as cm:
            self.store.add_reality_record(
                {"kind": "accepted", "release_id": "",
                 "accountable": "Khalil"})
        self.assertEqual("unaccountable-acceptance", cm.exception.reason)

    def test_r1_refusal_writes_nothing(self):
        try:
            self.store.add_reality_record(
                {"kind": "accepted", "release_id": "", "accountable": ""})
        except self.mod.OwnershipRefused:
            pass
        self.assertEqual([], self.store.list_reality_records(raw=True))

    # -- R2: a links_to that names no existing 'accepted' row is refused -

    def test_r2_incident_with_a_links_to_that_does_not_exist_is_refused(self):
        with self.assertRaises(self.mod.OwnershipRefused) as cm:
            self.store.add_reality_record(
                {"kind": "incident", "links_to": "no-such-record"})
        self.assertEqual("no-accepted-release", cm.exception.reason)

    def test_r2_incident_with_a_links_to_that_names_a_non_accepted_row_is_refused(self):
        accepted_id = self._accept()
        incident_id = self.store.add_reality_record(
            {"kind": "incident", "links_to": accepted_id})["record_id"]
        # An incident is itself not 'accepted', so a SECOND record trying
        # to link to the incident (rather than to the accepted row) must
        # also be refused: links_to always names an accepted row, never
        # any other reality record, chained or not.
        with self.assertRaises(self.mod.OwnershipRefused) as cm:
            self.store.add_reality_record(
                {"kind": "incident", "links_to": incident_id})
        self.assertEqual("no-accepted-release", cm.exception.reason)

    def test_r2_incident_naming_a_real_accepted_row_succeeds_and_shows_up(self):
        accepted_id = self._accept(release_id="v2")
        result = self.store.add_reality_record(
            {"kind": "incident", "links_to": accepted_id,
             "detail": "prod fire"})
        self.assertEqual("incident", result["kind"])
        self.assertEqual("v2", result["release_id"])
        rows = self.store.list_reality_records(release_id="v2", raw=True)
        kinds = sorted(r["kind"] for r in rows)
        self.assertEqual(["accepted", "incident"], kinds)

    def test_r2_refusal_writes_nothing(self):
        try:
            self.store.add_reality_record(
                {"kind": "incident", "links_to": "no-such-record"})
        except self.mod.OwnershipRefused:
            pass
        self.assertEqual([], self.store.list_reality_records(raw=True))

    # -- R3: a defect with no intent_ref is refused -----------------------

    def test_r3_defect_with_no_intent_ref_is_refused(self):
        accepted_id = self._accept(release_id="v3")
        with self.assertRaises(self.mod.OwnershipRefused) as cm:
            self.store.add_reality_record(
                {"kind": "defect", "links_to": accepted_id})
        self.assertEqual("defect-without-intent", cm.exception.reason)

    def test_r3_refusal_writes_nothing(self):
        accepted_id = self._accept(release_id="v3")
        before = self.store.list_reality_records(raw=True)
        try:
            self.store.add_reality_record(
                {"kind": "defect", "links_to": accepted_id})
        except self.mod.OwnershipRefused:
            pass
        after = self.store.list_reality_records(raw=True)
        self.assertEqual(before, after)

    # -- unrecognised kind, before any of the three above run -------------

    def test_unrecognised_kind_is_refused_naming_all_five(self):
        with self.assertRaises(self.mod.OwnershipRefused) as cm:
            self.store.add_reality_record(
                {"kind": "made-up-kind", "release_id": "v1"})
        self.assertEqual("bad-reality-kind", cm.exception.reason)
        for kind in ("accepted", "reopened", "rolled-back", "incident",
                    "defect"):
            self.assertIn(kind, str(cm.exception))


class TestTheReturnEdge(unittest.TestCase):
    """5, 6. `defect` writes docs/plan/QUEUE.json's new item BEFORE the
    reality row, both carry the other's id, and a queue write that fails
    leaves no reality row behind at all."""

    def test_defect_appends_a_queue_item_and_the_reality_row_names_it(self):
        with tempfile.TemporaryDirectory() as d:
            init_store(d)
            write_queue(d)
            accept = run_cli("accept", "--release", "v9", "--accountable",
                             "Khalil", "--root", d)
            self.assertEqual(0, accept.returncode, accept.stderr)

            mod = _load_bm_store_module()
            store = mod.ReadOnlyStore(d)
            try:
                accepted_id = _accepted_record_id(store, "v9")
            finally:
                store.close()
            self.assertIsNotNone(accepted_id)

            defect = run_cli(
                "defect", "--release-record", accepted_id, "--title",
                "found a real bug", "--files", "a.py", "b.py",
                "--root", d)
            self.assertEqual(0, defect.returncode, defect.stderr)

            queue = read_queue(d)
            self.assertEqual(1, len(queue["items"]))
            item = queue["items"][0]
            self.assertEqual("queued", item["state"])
            self.assertEqual("intent", item["stage"])
            self.assertEqual(["a.py", "b.py"], item["files"])
            self.assertTrue(item.get("provenance"),
                            "the queue item must name the reality record "
                            "it came from")

            store = mod.ReadOnlyStore(d)
            try:
                rows = store.list_reality_records(links_to=accepted_id,
                                                   raw=True)
            finally:
                store.close()
            defect_rows = [r for r in rows if r["kind"] == "defect"]
            self.assertEqual(1, len(defect_rows))
            defect_row = defect_rows[0]

            # BOTH directions of the link, structurally, not by string
            # matching stdout: the queue item's provenance names the
            # reality row's own primary key, and the reality row's
            # intent_ref names the queue item's own id.
            self.assertEqual(defect_row["record_id"], item["provenance"])
            self.assertEqual(item["id"], defect_row["intent_ref"])

    def test_queue_append_failure_leaves_no_reality_row(self):
        with tempfile.TemporaryDirectory() as d:
            init_store(d)
            # A malformed existing queue file: not valid JSON at all,
            # exactly the shape tools/bm_idle.py's own load_queue already
            # refuses. Written by hand rather than via write_queue, on
            # purpose, so the fixture is unambiguously broken.
            queue_path = os.path.join(d, "docs", "plan", "QUEUE.json")
            os.makedirs(os.path.dirname(queue_path))
            with io.open(queue_path, "w", encoding="utf-8") as handle:
                handle.write("{ this is not valid json")

            accept = run_cli("accept", "--release", "v10", "--accountable",
                             "Khalil", "--root", d)
            self.assertEqual(0, accept.returncode, accept.stderr)

            mod = _load_bm_store_module()
            store = mod.ReadOnlyStore(d)
            try:
                accepted_id = _accepted_record_id(store, "v10")
                before = store.list_reality_records(raw=True)
            finally:
                store.close()

            defect = run_cli(
                "defect", "--release-record", accepted_id, "--title",
                "should never be recorded", "--root", d)
            self.assertNotEqual(0, defect.returncode)

            store = mod.ReadOnlyStore(d)
            try:
                after = store.list_reality_records(raw=True)
            finally:
                store.close()
            # Nothing was added: the queue write failed, so the reality
            # row (which would have carried an intent_ref pointing at a
            # queue item that was never actually written) must not exist
            # either.
            self.assertEqual(len(before), len(after))
            self.assertFalse(
                any(r["kind"] == "defect" for r in after),
                "a defect record must not exist when the queue append "
                "that was supposed to create its intent failed")

            # The malformed queue file itself must survive untouched:
            # a failed append is not a license to overwrite it with
            # something else, or to leave a half-written temp file
            # renamed over it.
            with io.open(queue_path, "r", encoding="utf-8") as handle:
                self.assertEqual("{ this is not valid json", handle.read())

    def test_defect_refuses_when_the_release_record_does_not_exist(self):
        with tempfile.TemporaryDirectory() as d:
            init_store(d)
            write_queue(d)
            defect = run_cli(
                "defect", "--release-record", "no-such-record", "--title",
                "orphan defect", "--root", d)
            self.assertNotEqual(0, defect.returncode)
            queue = read_queue(d)
            self.assertEqual(
                [], queue["items"],
                "a defect naming a release record that does not exist "
                "must not touch the queue at all")


class TestSchema21RealityRecords(unittest.TestCase):
    """7. A store created at schema 20 migrates to 21 and gains the table
    with no loss; a brand new store has it. Proven against a REAL
    schema-20 store, the same discipline
    tools/test_bm_store.py's own TestSchema20CapabilityReceipts uses for
    the schema bump immediately before this one."""

    def setUp(self):
        self.mod = _load_bm_store_module()

    def _tables(self, path):
        conn = sqlite3.connect(path)
        try:
            return {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            conn.close()

    def _table_info(self, path, table):
        conn = sqlite3.connect(path)
        try:
            return [tuple(r) for r in
                    conn.execute("PRAGMA table_info(%s)" % table)]
        finally:
            conn.close()

    def _schema20_store(self, d):
        """A real, freshly initialized store, stripped back to the
        schema-20 shape: no reality_records table at all. Every OTHER
        table is left exactly as bm_store.py's own _ensure_schema built
        it, because schema 21 adds nothing else."""
        with self.mod.Store(d):
            pass
        path = os.path.join(d, self.mod.STORE_DIRNAME,
                            self.mod.STORE_FILENAME)
        conn = sqlite3.connect(path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("DROP TABLE IF EXISTS reality_records")
            conn.execute(
                "UPDATE meta SET value='20' WHERE key='schema_version'")
            conn.execute("COMMIT")
        finally:
            conn.close()
        return path

    def test_schema_version_is_at_least_21(self):
        self.assertGreaterEqual(self.mod.SCHEMA_VERSION, 21)

    def test_the_migrations_table_has_an_entry_for_schema_20(self):
        self.assertIn(20, self.mod._MIGRATIONS)
        self.assertIs(self.mod._MIGRATIONS[20], self.mod._migrate_20_to_21)

    def test_the_fixture_really_is_missing_the_table(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._schema20_store(d)
            self.assertNotIn("reality_records", self._tables(path))

    def test_an_existing_schema20_database_migrates_and_gains_the_table(self):
        with tempfile.TemporaryDirectory() as d:
            self._schema20_store(d)
            with self.mod.Store(d) as store:
                have = {r[0] for r in store.conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'")}
                self.assertIn("reality_records", have)
                version = store.conn.execute(
                    "SELECT value FROM meta WHERE key='schema_version'"
                ).fetchone()[0]
                self.assertEqual(str(self.mod.SCHEMA_VERSION), version)

    def test_migration_loses_no_row_of_any_other_table(self):
        with tempfile.TemporaryDirectory() as d:
            with self.mod.Store(d) as store:
                store.upsert_project(
                    {"project_id": "proj1", "name": "Proj",
                     "created_at": "2026-08-01T00:00:00Z",
                     "updated_at": "2026-08-01T00:00:00Z"},
                    {"actor_type": "human", "actor_name": "tester"})
            path = self._schema20_store(d)

            def project_count():
                conn = sqlite3.connect(path)
                try:
                    return conn.execute(
                        "SELECT COUNT(*) FROM projects").fetchone()[0]
                finally:
                    conn.close()

            before = project_count()
            self.assertEqual(1, before, "the fixture must carry a real row")
            with self.mod.Store(d):
                pass
            after = project_count()
            self.assertEqual(before, after)

    def test_a_brand_new_store_has_the_reality_records_table_empty(self):
        with tempfile.TemporaryDirectory() as d:
            with self.mod.Store(d):
                pass
            path = os.path.join(d, self.mod.STORE_DIRNAME,
                                self.mod.STORE_FILENAME)
            self.assertIn("reality_records", self._tables(path))
            cols = {c[1] for c in self._table_info(path, "reality_records")}
            self.assertEqual(
                cols,
                {"record_id", "kind", "release_id", "passport_sha256",
                 "accountable", "occurred_at", "recorded_at", "links_to",
                 "intent_ref", "detail", "project_id", "session_id"})
            conn = sqlite3.connect(path)
            try:
                count = conn.execute(
                    "SELECT COUNT(*) FROM reality_records").fetchone()[0]
            finally:
                conn.close()
            self.assertEqual(0, count, "no backfill, created empty")


class TestInsertOnly(unittest.TestCase):
    """8. Insert only, asserted MECHANICALLY: no UPDATE or DELETE FROM
    reality_records statement anywhere in tools/bm_store.py's own
    source, found by searching the actual SQL shape rather than trusting
    what a docstring claims. A guard that only read the module's prose
    would go green even if a later change added
    'UPDATE reality_records SET ...' beside a comment insisting the table
    is insert only; this test would go red the moment that line existed."""

    _MUTATING_SQL = re.compile(
        r'(UPDATE\s+reality_records\b|DELETE\s+FROM\s+reality_records\b)',
        re.IGNORECASE)

    def test_no_update_or_delete_statement_targets_reality_records(self):
        with io.open(STORE_SOURCE_PATH, encoding="utf-8") as handle:
            source = handle.read()
        matches = self._MUTATING_SQL.findall(source)
        self.assertEqual(
            [], matches,
            "tools/bm_store.py contains a statement that mutates or "
            "deletes a reality_records row; this table must be insert "
            "only")

    def test_store_exposes_no_update_or_delete_method_for_reality_records(self):
        mod = _load_bm_store_module()
        suspect = [name for name in dir(mod.Store)
                  if "reality" in name.lower()
                  and ("update" in name.lower()
                       or "delete" in name.lower()
                       or "remove" in name.lower()
                       or "edit" in name.lower())]
        self.assertEqual(
            [], suspect,
            "Store carries a method that looks like it mutates or "
            "removes a reality record: %s" % suspect)


class TestCLIUsageAndRefusalsAreVisible(unittest.TestCase):
    """The CLI-reachable half of R2 (an `enter` naming a nonexistent
    release record is refused, visibly, with the store's own reason
    code), plus the bare error paths a founder actually sees: missing
    required flags and an unrecognised verb."""

    def test_enter_with_a_nonexistent_release_record_is_refused_visibly(self):
        with tempfile.TemporaryDirectory() as d:
            init_store(d)
            enter = run_cli("enter", "--kind", "incident",
                            "--release-record", "no-such-record",
                            "--root", d)
            self.assertNotEqual(0, enter.returncode)
            self.assertIn("no-accepted-release", enter.stderr)

    def test_accept_missing_required_flags_is_a_usage_error(self):
        with tempfile.TemporaryDirectory() as d:
            init_store(d)
            result = run_cli("accept", "--root", d)
            self.assertEqual(2, result.returncode)

    def test_unknown_verb_is_a_usage_error(self):
        with tempfile.TemporaryDirectory() as d:
            result = run_cli("not-a-real-verb", "--root", d)
            self.assertEqual(2, result.returncode)

    def test_show_with_nothing_recorded_is_not_an_error(self):
        with tempfile.TemporaryDirectory() as d:
            init_store(d)
            result = run_cli("show", "--root", d)
            self.assertEqual(0, result.returncode)


if __name__ == "__main__":
    unittest.main()
