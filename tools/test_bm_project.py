#!/usr/bin/env python3
"""Regression tests for tools/bm_project.py (Loop 2, docs/superpowers/specs/
2026-08-01-loop2-mechanical-commands-design.md, decisions D-1 and D-4).

Every test drives tools/bm_project.py as a real SUBPROCESS against a fresh
tempfile.TemporaryDirectory() root (BROTHERMODE_ROOT), never against this
repo's own store. Row-level verification of the STORED bytes uses
Store.dump(raw=True) -- the same escape hatch test_bm_store.py's own
_dump() helper documents -- rather than this test file's own SQL. That is
a separate thing from what the CLI's own stdout can now assert: since the
loop2 redaction-policy fix, human-readable text output (status, next) and
--raw JSON read through the D-2 accessors with raw=True, so a task id and
title landing correctly in a mechanical command's own words IS something
TestLoop2RedactionPolicy below asserts directly against stdout, not only
against the raw dump. See bm_project.py's own module docstring for the
full account of what raw=True covers and what --json without --raw still
withholds.

Python 3.9, standard library only. Run: python3 tools/test_bm_project.py

No em or en dashes anywhere in this file, its comments, or its output.
"""
import ast
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


def _docstring_constant_ids(tree):
    """id() of every ast.Constant node ast.get_docstring would return the
    value of: the first statement of a Module/FunctionDef/
    AsyncFunctionDef/ClassDef body, when it is a bare string expression.
    Docstrings are prose a human reads, never an argument any code
    executes, and this file's own module docstring legitimately uses
    ordinary English words ('an update', 'select only the questions
    that...') a blind scan cannot tell apart from SQL. Comments need no
    equivalent exclusion: Python's own tokenizer discards them before the
    AST exists, so they were never a node a walk could visit in the first
    place."""
    ids = set()
    doc_holders = (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                   ast.ClassDef)
    for node in ast.walk(tree):
        if isinstance(node, doc_holders) and node.body:
            first = node.body[0]
            if (isinstance(first, ast.Expr)
                    and isinstance(first.value, ast.Constant)
                    and isinstance(first.value.value, str)):
                ids.add(id(first.value))
    return ids


class TestNoSQLGuard(unittest.TestCase):
    """D-1's flip condition, made executable: the moment bm_project.py
    needs a query the store does not already offer, it has become a
    second writer and must be folded back into bm_store.py.

    C7 (release-closure loop2 refuter fixes, from the PLAUSIBLE set,
    fixed anyway): the original guard was `re.findall(r"\\b(SELECT|
    INSERT|UPDATE|DELETE)\\b", source)` over the file's RAW TEXT,
    uppercase only. Two trivial bypasses evaded it without anything
    exotic: write the query in lowercase (`"select * from tasks"` is
    legal SQL and never matches an uppercase-only pattern), or split one
    keyword across two adjacent string literals (`"SEL" "ECT"` -- Python
    joins those into a single string at parse time, but they are never
    ONE contiguous word in the raw source a regex reads). Making the old
    pattern merely case-insensitive reopens the false positive its own
    comment already warned about (this file's legitimate lowercase
    `dict.update()` and `project['updated_at']`), and, proven below,
    trips on ordinary English prose in this file's own docstrings ("an
    update", "select only the questions..."). The fix is a smaller
    haystack, not a smarter pattern: parse the file with `ast` and check
    only STRING LITERAL VALUES (ast.Constant, case insensitive) for the
    keyword, excluding docstrings. Adjacent string-literal concatenation
    is already ONE Constant node with the joined value by the time
    ast.parse returns, which closes that bypass for free; a bare Python
    identifier like `update` or `updated_at` is a Name/Attribute node,
    never a string constant, so it is never even examined."""

    _SQL_RE = re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE|PRAGMA)\b",
                         re.IGNORECASE)

    def test_bm_project_never_issues_its_own_sql(self):
        with io.open(os.path.join(HERE, "bm_project.py"),
                     encoding="utf-8") as fh:
            source = fh.read()
        tree = ast.parse(source, filename="bm_project.py")
        skip = _docstring_constant_ids(tree)
        hits = []
        for node in ast.walk(tree):
            if (isinstance(node, ast.Constant)
                    and isinstance(node.value, str)
                    and id(node) not in skip
                    and self._SQL_RE.search(node.value)):
                hits.append((node.lineno, node.value))
        self.assertEqual(
            hits, [],
            "bm_project.py must never contain a string literal shaped "
            "like SQL (found %r); a query the store does not already "
            "offer means this file has become a second writer and the "
            "query belongs in bm_store.py instead (D-1's flip "
            "condition)." % hits)

    def test_bm_project_never_imports_sqlite3(self):
        """Even a keyword-free query needs something able to run it.
        This file has no legitimate reason to import sqlite3 directly:
        every query it needs already goes through bs, the loaded
        bm_store module, and its Store service methods."""
        with io.open(os.path.join(HERE, "bm_project.py"),
                     encoding="utf-8") as fh:
            source = fh.read()
        tree = ast.parse(source, filename="bm_project.py")
        offenders = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                offenders.extend(a.name for a in node.names
                                 if a.name.split(".")[0] == "sqlite3")
            elif isinstance(node, ast.ImportFrom):
                if (node.module or "").split(".")[0] == "sqlite3":
                    offenders.append(node.module)
        self.assertEqual(
            offenders, [],
            "bm_project.py must never import sqlite3 directly (found "
            "%r); every query it needs already goes through bs, the "
            "loaded bm_store module." % offenders)

    def test_calibrated_old_guard_missed_a_lowercase_or_split_bypass(self):
        """CALIBRATION. Reproduces the pre-fix guard's own logic against a
        synthetic snippet standing in for what a change to bm_project.py
        could slip in, proving it would have said nothing was wrong, then
        proves the current AST-based guard catches both bypasses in the
        same snippet."""
        bypass_snippet = (
            'query = "sel" "ect * from tasks"\n'   # adjacent-literal split
            'other = "update tasks set status=?"\n'  # lowercase, whole word
        )
        old_style_hits = re.findall(
            r"\b(SELECT|INSERT|UPDATE|DELETE)\b", bypass_snippet)
        self.assertEqual(
            old_style_hits, [],
            "calibration sanity: the OLD guard must find nothing in this "
            "snippet, or it does not actually demonstrate the bypass")
        tree = ast.parse(bypass_snippet)
        hits = [n.value for n in ast.walk(tree)
               if isinstance(n, ast.Constant) and isinstance(n.value, str)
               and self._SQL_RE.search(n.value)]
        self.assertEqual(
            len(hits), 2,
            "the AST-based guard must catch both the split literal and "
            "the lowercase keyword the old regex missed (got %r)" % hits)


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


class TestReleaseClosureLoop2RefuterFixes(unittest.TestCase):
    """Regression coverage for the twelve confirmed loop2-refuter
    findings this file's own correctness fixes (C1-C6) touch. Each test
    below fails against the pre-fix code and passes against the fix."""

    def _started(self, root, project_id="proj1", name="Acme Rescue",
                extra=()):
        _init(root)
        r = _run(["start", "--project-id", project_id, "--name", name]
                 + list(extra) + list(ACTOR), root)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_review_refused_transition_leaves_no_orphan_evidence(self):
        """C1: review used to call add_evidence and transition_task as
        two SEPARATE transactions, so a refused transition still left the
        evidence from the first call sitting on disk. review_task now
        runs both in ONE transaction."""
        with tempfile.TemporaryDirectory() as root:
            self._started(root)
            r = _run(["task", "add", "--project-id", "proj1",
                      "--task-id", "task1", "--title", "Do the thing"]
                     + list(ACTOR), root)
            self.assertEqual(r.returncode, 0, r.stderr)
            # review defaults --to verified; legal moves from 'planned'
            # are ('ready',) only, so this is refused.
            r = _run(["review", "task1", "--project-id", "proj1",
                      "--kind", "test", "--ref", "x", "--reason", "trying"]
                     + list(ACTOR), root)
            self.assertEqual(r.returncode, 1)
            raw = _raw_dump(root)
            self.assertEqual(
                [e for e in raw["evidence"] if e["subject_id"] == "task1"],
                [], "a refused review transition must write no evidence row")

    def test_review_refuses_evidence_for_a_nonexistent_task(self):
        """C2: add_evidence used to validate nothing about its subject.
        Reviewing a task id that names nothing used to insert an evidence
        row for it anyway (the transition call that came after was what
        actually failed), leaving an orphan evidence row for a subject
        that never existed."""
        with tempfile.TemporaryDirectory() as root:
            self._started(root)
            r = _run(["review", "nope", "--project-id", "proj1",
                      "--reason", "trying"] + list(ACTOR), root)
            self.assertEqual(r.returncode, 1)
            raw = _raw_dump(root)
            self.assertEqual(
                [e for e in raw["evidence"] if e["subject_id"] == "nope"],
                [], "evidence for a nonexistent subject must never be "
                    "written")

    def test_review_refuses_evidence_when_project_id_mismatches_the_tasks_own_project(self):
        """C3: evidence carries no project_id column of its own; without
        a cross-check, evidence for a task in one project could be filed
        under a different project's id."""
        with tempfile.TemporaryDirectory() as root:
            self._started(root)
            self._started(root, project_id="proj2", name="Other",
                          extra=("--allow-second",))
            r = _run(["task", "add", "--project-id", "proj2",
                      "--task-id", "task2", "--title", "Do the other thing"]
                     + list(ACTOR), root)
            self.assertEqual(r.returncode, 0, r.stderr)
            # task2 belongs to proj2; review claims proj1.
            r = _run(["review", "task2", "--project-id", "proj1",
                      "--reason", "trying"] + list(ACTOR), root)
            self.assertEqual(r.returncode, 1)
            raw = _raw_dump(root)
            self.assertEqual(
                [e for e in raw["evidence"] if e["subject_id"] == "task2"],
                [], "a project-mismatched review must write no evidence "
                    "row")

    def test_deliver_refuses_a_project_with_zero_tasks_even_with_partial(self):
        """C4: deliver used to succeed on a project with zero tasks
        (0 non-terminal out of 0 total looks, wrongly, like nothing is
        outstanding); --partial must not override this."""
        with tempfile.TemporaryDirectory() as root:
            self._started(root)
            r = _run(["deliver", "--project-id", "proj1"], root)
            self.assertEqual(r.returncode, 1)
            self.assertIn("zero tasks", r.stderr)
            r = _run(["deliver", "--project-id", "proj1", "--partial"], root)
            self.assertEqual(r.returncode, 1)
            self.assertIn("zero tasks", r.stderr)

    def test_start_refuses_a_second_project_without_allow_second(self):
        """C5: two different project_ids sharing one root would clobber
        CANVAS.md and the delivery packet in turn."""
        with tempfile.TemporaryDirectory() as root:
            self._started(root)
            r = _run(["start", "--project-id", "proj2", "--name", "Other"]
                     + list(ACTOR), root)
            self.assertEqual(r.returncode, 1)
            self.assertIn("proj1", r.stderr)
            # Re-running start on the SAME project_id is an update, never
            # "a second project", and is never refused.
            r = _run(["start", "--project-id", "proj1", "--name",
                      "Acme Rescue"] + list(ACTOR), root)
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_start_allow_second_switches_canvas_and_packet_to_project_scoped_names(self):
        """C5: once a root genuinely holds more than one project,
        CANVAS.md/DELIVERY-PACKET.md must not be shared filenames."""
        with tempfile.TemporaryDirectory() as root:
            self._started(root)
            self.assertTrue(os.path.isfile(os.path.join(root, "CANVAS.md")))
            self._started(root, project_id="proj2", name="Other",
                          extra=("--allow-second",))
            self.assertTrue(
                os.path.isfile(os.path.join(root, "CANVAS-proj2.md")),
                "a second project's canvas must not clobber CANVAS.md")
            r = _run(["task", "add", "--project-id", "proj2",
                      "--task-id", "task2", "--title", "Do the other thing"]
                     + list(ACTOR), root)
            self.assertEqual(r.returncode, 0, r.stderr)
            r = _run(["deliver", "--project-id", "proj2", "--partial"], root)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(
                os.path.isfile(
                    os.path.join(root, "DELIVERY-PACKET-proj2.md")),
                "a second project's delivery packet must not clobber "
                "DELIVERY-PACKET.md")

    def test_next_ties_on_priority_by_insertion_order_not_task_id(self):
        """C6: tasks carry no created_at; the tie break used to be
        task_id order (a random hex uuid), which next's own WHY text
        misdescribed as 'earliest created'. Task ids below are chosen so
        alphabetical order would pick the WRONG one: 'zzz...' is added
        FIRST but sorts LAST alphabetically."""
        with tempfile.TemporaryDirectory() as root:
            self._started(root)
            for task_id, title in (("zzz-added-first", "First in"),
                                   ("aaa-added-second", "Second in")):
                r = _run(["task", "add", "--project-id", "proj1",
                          "--task-id", task_id, "--title", title]
                         + list(ACTOR), root)
                self.assertEqual(r.returncode, 0, r.stderr)
                r = _run(["task", "transition", "--task-id", task_id,
                          "--to", "ready", "--reason", "deps clear"]
                         + list(ACTOR), root)
                self.assertEqual(r.returncode, 0, r.stderr)

            r = _run(["next", "--project-id", "proj1", "--json"], root)
            self.assertEqual(r.returncode, 0, r.stderr)
            nxt = json.loads(r.stdout)
            self.assertEqual(
                nxt["picked"]["task_id"], "zzz-added-first",
                "same priority (both blank): the tie break must be "
                "insertion order, not task_id order")

            r = _run(["next", "--project-id", "proj1"], root)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("added first", r.stdout)
            self.assertNotIn("earliest created", r.stdout)


class TestLoop2RedactionPolicy(unittest.TestCase):
    """The loop2 redaction-policy fix, asserted against the CLI's own
    stdout rather than the raw dump escape hatch: _DUMP_SAFE_COLUMNS now
    lists identifiers, enums and timestamps for the schema-12 tables, and
    this file's human-readable text output (status, next) reads through
    raw=True (local display is not an export; see bm_project.py's own
    module docstring), so a task id and a title can finally be named in a
    mechanical command's own words. --json without --raw stays on the
    OTHER side of that line: it is the export surface, and prose still
    comes back withheld there by default, exactly like bm_store.py's own
    dump."""

    def _seeded_project(self, root):
        _init(root)
        r = _run(["start", "--project-id", "proj1",
                  "--name", "Acme Rescue", "--goal", "Ship the thing"]
                 + list(ACTOR) + ["--out-json"], root)
        self.assertEqual(r.returncode, 0, r.stderr)
        r = _run(["task", "add", "--project-id", "proj1",
                  "--task-id", "task1", "--title", "Fix the leaky pipe"]
                 + list(ACTOR) + ["--out-json"], root)
        self.assertEqual(r.returncode, 0, r.stderr)
        r = _run(["task", "transition", "--task-id", "task1",
                  "--to", "ready", "--reason", "deps clear"]
                 + list(ACTOR) + ["--out-json"], root)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_status_and_next_text_output_name_ids_and_titles_via_raw(self):
        with tempfile.TemporaryDirectory() as root:
            self._seeded_project(root)

            r = _run(["status", "--project-id", "proj1"], root)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("proj1", r.stdout)
            self.assertIn("Acme Rescue", r.stdout)

            r = _run(["next", "--project-id", "proj1"], root)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("task1", r.stdout)
            self.assertIn("Fix the leaky pipe", r.stdout)

    def test_json_without_raw_keeps_prose_withheld_raw_reveals_it(self):
        with tempfile.TemporaryDirectory() as root:
            self._seeded_project(root)

            r = _run(["status", "--project-id", "proj1", "--json"], root)
            self.assertEqual(r.returncode, 0, r.stderr)
            status = json.loads(r.stdout)
            self.assertEqual(status["project"]["project_id"], "proj1")
            self.assertTrue(
                status["project"]["name"].startswith("[WITHHELD"),
                status["project"])
            self.assertNotIn("Acme Rescue", r.stdout)

            r = _run(["status", "--project-id", "proj1", "--json", "--raw"],
                     root)
            self.assertEqual(r.returncode, 0, r.stderr)
            status_raw = json.loads(r.stdout)
            self.assertEqual(status_raw["project"]["name"], "Acme Rescue")

            r = _run(["next", "--project-id", "proj1", "--json"], root)
            self.assertEqual(r.returncode, 0, r.stderr)
            nxt = json.loads(r.stdout)
            self.assertEqual(nxt["picked"]["task_id"], "task1")
            self.assertTrue(
                nxt["picked"]["title"].startswith("[WITHHELD"),
                nxt["picked"])
            self.assertNotIn("Fix the leaky pipe", r.stdout)

            r = _run(["next", "--project-id", "proj1", "--json", "--raw"],
                     root)
            self.assertEqual(r.returncode, 0, r.stderr)
            nxt_raw = json.loads(r.stdout)
            self.assertEqual(nxt_raw["picked"]["title"], "Fix the leaky pipe")


if __name__ == "__main__":
    unittest.main()
