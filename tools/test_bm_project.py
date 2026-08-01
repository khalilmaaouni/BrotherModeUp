#!/usr/bin/env python3
"""Regression tests for tools/bm_project.py (Loop 2, docs/superpowers/specs/
2026-08-01-loop2-mechanical-commands-design.md, decisions D-1 and D-4).

Every test drives tools/bm_project.py as a real SUBPROCESS against a fresh
tempfile.TemporaryDirectory() root (BROTHERMODE_ROOT), never against this
repo's own store. Row-level verification uses Store.dump(raw=True) -- the
same escape hatch test_bm_store.py's own _dump() helper documents -- rather
than either this test file's own SQL (bm_project.py's D-2 read accessors
are not that hatch: they redact through the identical export_column policy
dump() uses by default, and as of this writing carry no _DUMP_SAFE_COLUMNS
entries for the schema-12 tables at all, so a mechanical command's own
stdout cannot be used to assert an actual id or title landed correctly;
see bm_project.py's own module docstring for the full account of that gap).

Python 3.9, standard library only. Run: python3 tools/test_bm_project.py

No em or en dashes anywhere in this file, its comments, or its output.
"""
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))

_spec = importlib.util.spec_from_file_location(
    "bm_store", os.path.join(HERE, "bm_store.py"))
bs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bs)
sys.modules["bm_store"] = bs

PROJECT_CLI = os.path.join(HERE, "bm_project.py")
STORE_CLI = os.path.join(HERE, "bm_store.py")

ACTOR = ("--actor-type", "model", "--actor-name", "tester")


def _run(args, root, extra_env=None):
    """Drive bm_project.py as a real subprocess against `root`.
    BROTHERMODE_ROOT is set explicitly on top of the inherited environment
    (never scrubbed of other developer state this repo's own tests don't
    depend on), matching test_bm.py's own _run_threads-style helper."""
    e = dict(os.environ)
    e.pop("BROTHERMODE_ROOT", None)
    e["BROTHERMODE_ROOT"] = root
    if extra_env:
        e.update(extra_env)
    return subprocess.run([sys.executable, PROJECT_CLI] + list(args),
                          cwd=root, capture_output=True, text=True, env=e)


def _init(root):
    e = dict(os.environ)
    e.pop("BROTHERMODE_ROOT", None)
    e["BROTHERMODE_ROOT"] = root
    r = subprocess.run([sys.executable, STORE_CLI, "init"],
                       cwd=root, capture_output=True, text=True, env=e)
    if r.returncode != 0:
        raise AssertionError("bm_store.py init failed: %s" % r.stderr)
    return r


def _raw_dump(root):
    """The unredacted store contents, for asserting what actually landed,
    never for driving assertions about what a founder would SEE (that is
    what the CLI's own stdout is for)."""
    store = bs.Store(root, create=False)
    try:
        return store.dump(raw=True)
    finally:
        store.close()


class TestNoSQLGuard(unittest.TestCase):
    """D-1's flip condition, made executable: the moment bm_project.py
    needs a query the store does not already offer, it has become a
    second writer and must be folded back into bm_store.py."""

    def test_bm_project_never_issues_its_own_sql(self):
        # Case sensitive, matching how every real query in bm_store.py
        # itself is written (SELECT/INSERT/UPDATE/DELETE, always upper
        # case, inside a _exec(...) call). This file's own lower-case
        # 'update' (dict.update, project['updated_at']) must never trip
        # a case-INsensitive version of this same check.
        with io.open(os.path.join(HERE, "bm_project.py"),
                     encoding="utf-8") as fh:
            source = fh.read()
        hits = re.findall(r"\b(SELECT|INSERT|UPDATE|DELETE)\b", source)
        self.assertEqual(
            hits, [],
            "bm_project.py must never contain SQL keywords of its own "
            "(found %r); a query the store does not already offer means "
            "this file has become a second writer and the query belongs "
            "in bm_store.py instead (D-1's flip condition)." % hits)


class TestRefusals(unittest.TestCase):
    """The ten-state law refuses exactly in schema.transition's own words,
    never restated by this CLI, and 'done' is refused BY NAME."""

    def _task_in_planned(self, root):
        _init(root)
        r = _run(["start", "--project-id", "proj1", "--name", "Acme Rescue"]
                 + list(ACTOR), root)
        self.assertEqual(r.returncode, 0, r.stderr)
        r = _run(["task", "add", "--project-id", "proj1",
                  "--task-id", "task1", "--title", "Do the thing"]
                 + list(ACTOR), root)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_illegal_transition_refuses_with_schema_text(self):
        with tempfile.TemporaryDirectory() as root:
            self._task_in_planned(root)
            # planned -> verified skips every stage in between; legal moves
            # from planned are ('ready',) only.
            r = _run(["task", "transition", "--task-id", "task1",
                      "--to", "verified", "--reason", "skipping ahead"]
                     + list(ACTOR), root)
            self.assertEqual(r.returncode, 1)
            self.assertIn("illegal transition", r.stderr)
            self.assertIn("'planned' to 'verified'", r.stderr)
            self.assertIn("Legal moves from 'planned': ready", r.stderr)
            # Refused, so nothing moved: still planned.
            raw = _raw_dump(root)
            tasks = {t["task_id"]: t for t in raw["tasks"]}
            self.assertEqual(tasks["task1"]["status"], "planned")

    def test_done_state_is_refused_by_name(self):
        with tempfile.TemporaryDirectory() as root:
            self._task_in_planned(root)
            r = _run(["task", "transition", "--task-id", "task1",
                      "--to", "done", "--reason", "marking it done"]
                     + list(ACTOR), root)
            self.assertEqual(r.returncode, 1)
            self.assertIn("refused by name", r.stderr)
            self.assertIn("Done is not a valid state", r.stderr)
            raw = _raw_dump(root)
            tasks = {t["task_id"]: t for t in raw["tasks"]}
            self.assertEqual(tasks["task1"]["status"], "planned")

    def test_task_transition_requires_reason(self):
        with tempfile.TemporaryDirectory() as root:
            self._task_in_planned(root)
            r = _run(["task", "transition", "--task-id", "task1",
                      "--to", "ready"] + list(ACTOR), root)
            self.assertEqual(r.returncode, 2)

    def test_start_requires_actor_name(self):
        with tempfile.TemporaryDirectory() as root:
            _init(root)
            r = _run(["start", "--project-id", "proj1", "--name", "X"], root)
            self.assertEqual(r.returncode, 2)

    def test_unknown_command_is_usage_error(self):
        with tempfile.TemporaryDirectory() as root:
            _init(root)
            r = _run(["bogus"], root)
            self.assertEqual(r.returncode, 2)

    def test_status_on_unknown_project_refuses(self):
        with tempfile.TemporaryDirectory() as root:
            _init(root)
            r = _run(["status", "--project-id", "nope"], root)
            self.assertEqual(r.returncode, 1)

    def test_help_exits_zero(self):
        with tempfile.TemporaryDirectory() as root:
            r = _run(["--help"], root)
            self.assertEqual(r.returncode, 0)
            self.assertIn("commands:", r.stdout)


class TestScriptedFirstProject(unittest.TestCase):
    """D-4: the gate is executable. This drives every one of the seven
    command surfaces through subprocess against a temp root, and asserts
    rows, an attribution row per mutation, and that CANVAS.md regenerates
    byte-stable from rows."""

    def test_scripted_first_project_end_to_end(self):
        with tempfile.TemporaryDirectory() as root:
            _init(root)

            # -- start: project row, no tasks/forecast yet --------------
            r = _run(["start", "--project-id", "proj1",
                      "--name", "Acme Rescue", "--goal", "Ship the thing"]
                     + list(ACTOR) + ["--out-json"], root)
            self.assertEqual(r.returncode, 0, r.stderr)
            started = json.loads(r.stdout)
            self.assertEqual(started["project_id"], "proj1")
            self.assertEqual(started["task_ids"], [])

            # -- status: rows only, machine readable ---------------------
            r = _run(["status", "--project-id", "proj1", "--json"], root)
            self.assertEqual(r.returncode, 0, r.stderr)
            status = json.loads(r.stdout)
            self.assertEqual(status["tasks_by_state"]["planned"], [])
            self.assertIsNone(status["latest_forecast"])

            # -- task add -------------------------------------------------
            r = _run(["task", "add", "--project-id", "proj1",
                      "--task-id", "task1", "--title", "Do the thing"]
                     + list(ACTOR) + ["--out-json"], root)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(json.loads(r.stdout)["task_id"], "task1")

            # planned -> ready
            r = _run(["task", "transition", "--task-id", "task1",
                      "--to", "ready", "--reason", "deps clear"]
                     + list(ACTOR) + ["--out-json"], root)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(json.loads(r.stdout)["status"], "ready")

            # -- next: recommends the one ready task ----------------------
            r = _run(["next", "--project-id", "proj1", "--json"], root)
            self.assertEqual(r.returncode, 0, r.stderr)
            nxt = json.loads(r.stdout)
            self.assertEqual(nxt["candidate_count"], 1)
            self.assertIsNotNone(nxt["picked"])

            # task start: ready -> active
            r = _run(["task", "start", "--task-id", "task1",
                      "--reason", "beginning"]
                     + list(ACTOR) + ["--out-json"], root)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(json.loads(r.stdout)["status"], "active")

            # active -> awaiting review
            r = _run(["task", "transition", "--task-id", "task1",
                      "--to", "awaiting review", "--reason", "work done"]
                     + list(ACTOR) + ["--out-json"], root)
            self.assertEqual(r.returncode, 0, r.stderr)

            # -- review: evidence recorded, awaiting review -> verified ---
            r = _run(["review", "task1", "--project-id", "proj1",
                      "--kind", "test", "--ref", "tools/test_all.py",
                      "--reason", "checks passed"]
                     + list(ACTOR) + ["--out-json"], root)
            self.assertEqual(r.returncode, 0, r.stderr)
            review_out = json.loads(r.stdout)
            self.assertEqual(review_out["status"], "verified")
            evidence_id = review_out["evidence_id"]

            # -- deliver refuses: the task has not reached 'closed' -------
            r = _run(["deliver", "--project-id", "proj1"], root)
            self.assertEqual(r.returncode, 1)
            self.assertIn("terminal", r.stderr)

            # --partial delivers anyway
            r = _run(["deliver", "--project-id", "proj1", "--partial",
                      "--out-json"], root)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(json.loads(r.stdout)["partial"])

            # walk the rest of the lifecycle to the terminal state
            for state, reason in (
                    ("accepted", "owner approved"),
                    ("delivered", "handed off"),
                    ("monitored", "watching"),
                    ("closed", "monitoring window over")):
                r = _run(["task", "transition", "--task-id", "task1",
                          "--to", state, "--reason", reason]
                         + list(ACTOR) + ["--out-json"], root)
                self.assertEqual(r.returncode, 0, r.stderr)

            # deliver now succeeds without --partial
            r = _run(["deliver", "--project-id", "proj1", "--out-json"],
                     root)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse(json.loads(r.stdout)["partial"])

            # -- assert rows exist, via the sanctioned raw escape hatch ---
            raw = _raw_dump(root)
            projects = {p["project_id"]: p for p in raw["projects"]}
            self.assertIn("proj1", projects)
            self.assertEqual(projects["proj1"]["name"], "Acme Rescue")
            self.assertEqual(projects["proj1"]["goal"], "Ship the thing")

            tasks = {t["task_id"]: t for t in raw["tasks"]}
            self.assertIn("task1", tasks)
            self.assertEqual(tasks["task1"]["status"], "closed")
            self.assertEqual(tasks["task1"]["title"], "Do the thing")

            evidence_rows = [e for e in raw["evidence"]
                            if e["evidence_id"] == evidence_id]
            self.assertEqual(len(evidence_rows), 1)
            self.assertEqual(evidence_rows[0]["subject_type"], "task")
            self.assertEqual(evidence_rows[0]["subject_id"], "task1")
            self.assertEqual(evidence_rows[0]["kind"], "test")

            # -- an attribution row per mutation ---------------------------
            # upsert_project (1) + create_task (1) + transition_task x8
            # (ready, active, 'awaiting review', verified[via review],
            # accepted, delivered, monitored, closed) + add_evidence (1,
            # from review) = 11. deliver itself calls no Store mutation
            # method (there is none for "delivery packet generated"), so
            # it contributes none, on purpose (see bm_project.py's own
            # comment at cmd_deliver).
            attributions = [a for a in raw["attribution"]
                            if a["project_id"] == "proj1"]
            event_types = [a["event_type"] for a in attributions]
            self.assertEqual(event_types.count("project.upserted"), 1)
            self.assertEqual(event_types.count("task.created"), 1)
            self.assertEqual(event_types.count("task.transitioned"), 8)
            self.assertEqual(event_types.count("evidence.added"), 1)
            self.assertEqual(len(attributions), 11)
            for a in attributions:
                self.assertEqual(a["actor_name"], "tester")
                self.assertEqual(a["actor_type"], "model")

            # -- CANVAS.md regenerates byte-stable from rows ---------------
            # CANVAS.md is only ever (re)written by `start` (D-3): the CLI
            # calls above (task/review/deliver) never touch it, so the copy
            # on disk right now still reflects the FIRST `start` call at
            # the very top of this test, before task1 even existed. Prime
            # it against the CURRENT rows once (unasserted), THEN take the
            # two comparable snapshots, or this compares two different
            # states of the world rather than two renders of the same one.
            canvas_path = os.path.join(root, "CANVAS.md")
            r = _run(["start", "--project-id", "proj1",
                      "--name", "Acme Rescue", "--goal", "Ship the thing"]
                     + list(ACTOR) + ["--out-json"], root)
            self.assertEqual(r.returncode, 0, r.stderr)
            with io.open(canvas_path, encoding="utf-8") as fh:
                canvas1 = fh.read()
            self.assertIn("BEGIN GENERATED BROTHERMODE CANVAS", canvas1)
            self.assertIn("closed", canvas1)

            r = _run(["start", "--project-id", "proj1",
                      "--name", "Acme Rescue", "--goal", "Ship the thing"]
                     + list(ACTOR) + ["--out-json"], root)
            self.assertEqual(r.returncode, 0, r.stderr)
            with io.open(canvas_path, encoding="utf-8") as fh:
                canvas2 = fh.read()
            self.assertEqual(
                canvas1, canvas2,
                "CANVAS.md must regenerate byte-stable from the same rows")

            # And a THIRD regeneration: a two-run comparison alone would
            # have missed a real compounding bug found while building this
            # suite (each re-splice into an already-marked file grew the
            # file by one blank line, forever); this pins the fixed point.
            r = _run(["start", "--project-id", "proj1",
                      "--name", "Acme Rescue", "--goal", "Ship the thing"]
                     + list(ACTOR) + ["--out-json"], root)
            self.assertEqual(r.returncode, 0, r.stderr)
            with io.open(canvas_path, encoding="utf-8") as fh:
                canvas3 = fh.read()
            self.assertEqual(canvas2, canvas3)

            # -- human prose outside the markers survives regeneration ----
            with io.open(canvas_path, "a", encoding="utf-8") as fh:
                fh.write("\nA note a human wrote by hand.\n")
            r = _run(["start", "--project-id", "proj1",
                      "--name", "Acme Rescue", "--goal", "Ship the thing"]
                     + list(ACTOR) + ["--out-json"], root)
            self.assertEqual(r.returncode, 0, r.stderr)
            with io.open(canvas_path, encoding="utf-8") as fh:
                canvas4 = fh.read()
            self.assertIn("A note a human wrote by hand.", canvas4)
            self.assertEqual(
                canvas4.count("A note a human wrote by hand."), 1)

            # -- DELIVERY-PACKET.md exists and is a generated view --------
            packet_path = os.path.join(root, "DELIVERY-PACKET.md")
            self.assertTrue(os.path.isfile(packet_path))
            with io.open(packet_path, encoding="utf-8") as fh:
                packet = fh.read()
            self.assertIn("BEGIN GENERATED BROTHERMODE DELIVERY PACKET",
                          packet)


if __name__ == "__main__":
    unittest.main()
