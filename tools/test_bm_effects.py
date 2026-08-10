#!/usr/bin/env python3
"""Tests for tools/bm_effects.py, the effect-class registry.

WHAT THIS SUITE PROVES
  1. Every REGISTRY value is one of the five declared classes (a typo in
     a class string fails loudly, not silently).
  2. declared() raises on an undeclared (module, command) pair rather
     than defaulting to anything.
  3. COMPLETENESS: every `def cmd_<name>` this suite can mechanically
     discover across every tools/bm_*.py and tools/brothermode_cli.py is
     declared in REGISTRY. A module whose dispatch is a plain if/elif
     chain rather than a lookup dict (tools/bm_ledger.py,
     tools/bm_telemetry.py, tools/bm_autosave.py) cannot be resolved to a
     verb by this mechanical scan; those commands are named as NO-DATA
     rather than silently passed over, and are not required to appear in
     REGISTRY, because inventing a verb mapping this suite cannot verify
     is exactly the kind of guess REGISTRY exists to refuse.
  4. PURITY: every command declared pure_read is run as a real
     subprocess against a real, freshly initialized throwaway project,
     and the project directory (store file, WAL/SHM sidecars, every
     generated file) must come out byte-identical. A command documented
     as read-only that actually writes fails HERE, which is the point:
     this suite exists to catch the eighth instance of that bug before
     it merges.
  5. --HELP PURITY: `<module> --help` (the bare form) for every module in
     REGISTRY, and `<module> <verb> --help` for every pure_read command
     (see TestHelpPurity's own docstring for why the verb-level form is
     also necessary to catch tools/bm_threads.py's documented "ignores
     --help entirely" defect), must both write nothing.

ISOLATION (load-bearing, read before touching this file)
  BROTHERMODE_VAULT is exported ambient on the machine this project
  usually runs on, and it WINS over HOME in every module that resolves a
  vault path. A HOME-only override does NOT isolate a subprocess from a
  real founder vault; this is the exact incident
  tools/test_bm_packaging_install.py's setUpClass documents and guards
  against, and this suite copies that pattern rather than re-deriving it:
  every subprocess here runs with a from-scratch environment that pins
  HOME, BROTHERMODE_VAULT, BROTHERSBE_VAULT and BROTHERMODE_ROOT inside
  one throwaway tempfile tree, never inheriting the invoking shell's
  environment.

No wall-clock timing assertions anywhere in this file (see
tools/bm_lint_walltime.py, which this file itself must pass clean).

Python 3.9, standard library only. Run:
  python3 tools/test_bm_effects.py
"""
import ast
import hashlib
import io
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TOOLS_DIR = HERE

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("bm_effects", os.path.join(HERE, "bm_effects.py"))
E = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(E)
sys.modules["bm_effects"] = E


# ---------------------------------------------------------------------------
# Mechanical discovery: every `def cmd_<name>` in a module, mapped to the
# verb (or verbs) a founder would type to reach it, by reading the
# module's own module-level dict-dispatch tables. Handles one level of
# nested routing (tools/bm_project.py's `task`/`forecast`/`alert` ->
# TASK_COMMANDS/FORECAST_COMMANDS/ALERT_COMMANDS), which is the only
# nested shape this codebase actually uses. A module with no such dict at
# all (an if/elif chain on sys.argv) yields nothing discoverable; every
# cmd_ function in it is reported as NO-DATA instead of being silently
# skipped.
# ---------------------------------------------------------------------------

def _own_scope_nodes(body):
    """Every descendant node reachable from `body` without crossing into a
    nested function/lambda/class, which owns its own scope. Mirrors
    tools/bm_lint_walltime.py's own `_own_scope_nodes`."""
    stack = list(body)
    out = []
    while stack:
        node = stack.pop()
        out.append(node)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.Lambda, ast.ClassDef)):
            continue
        stack.extend(ast.iter_child_nodes(node))
    return out


def _cmd_functions(tree):
    """{name: FunctionDef} for every module-level `def cmd_<x>`."""
    return {node.name: node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name.startswith("cmd_")}


def _dispatch_tables(tree, cmd_funcs):
    """{dict_var_name: {key_string: funcname}} for every module-level dict
    literal whose keys are all string constants and whose values are all
    Name references to a known `cmd_<x>` function. This is the actual
    shape every dispatch table in this codebase uses
    (COMMANDS/_COMMANDS/TASK_COMMANDS/... alike); anything else (a dict
    built with dict(), a comprehension, a value that is not a bare name)
    is not treated as a dispatch table, on purpose: guessing at a shape
    this scan cannot verify is worse than reporting NO-DATA."""
    tables = {}
    for node in tree.body:
        if not (isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict)):
            continue
        d = node.value
        if not d.keys:
            continue
        entries = {}
        ok = True
        for k, v in zip(d.keys, d.values):
            if k is None or not (isinstance(k, ast.Constant) and isinstance(k.value, str)):
                ok = False
                break
            if not (isinstance(v, ast.Name) and v.id in cmd_funcs):
                ok = False
                break
            entries[k.value] = v.id
        if not ok or not entries:
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                tables[target.id] = entries
    return tables


def _router_of(cmd_funcs, table_names):
    """{funcname: table_name} for every cmd_ function whose own body
    dispatches into one of the known tables, e.g. `TASK_COMMANDS[argv[0]]
    (argv[1:])` inside cmd_task. Matches both the inline subscript-call
    shape and the `.get(...)` shape."""
    router = {}
    for name, node in cmd_funcs.items():
        for sub in _own_scope_nodes(node.body):
            if not isinstance(sub, ast.Call):
                continue
            func = sub.func
            if (isinstance(func, ast.Subscript) and isinstance(func.value, ast.Name)
                    and func.value.id in table_names):
                router[name] = func.value.id
                break
            if (isinstance(func, ast.Attribute) and func.attr == "get"
                    and isinstance(func.value, ast.Name) and func.value.id in table_names):
                router[name] = func.value.id
                break
    return router


def _expand(table_name, tables, router_of, prefix, seen):
    """Every (verb, funcname) leaf reachable from `table_name`, expanding
    one level of nested routing into a space-joined compound verb
    ("task add"). `seen` guards against a self-referential table rather
    than looping forever; none of this codebase's real tables are
    self-referential, this is a refusal-shaped safety net, not a
    reachable path today."""
    if table_name in seen:
        return []
    seen = seen | {table_name}
    out = []
    for key in sorted(tables[table_name]):
        funcname = tables[table_name][key]
        target = router_of.get(funcname)
        if target and target in tables and target not in seen:
            out.extend(_expand(target, tables, router_of, prefix + [key], seen))
        else:
            out.append((" ".join(prefix + [key]), funcname))
    return out


def discover_module(path):
    """(discovered, no_data) for one module file.

    discovered: list of (verb, funcname) pairs resolved from this
    module's own dict-dispatch tables.
    no_data: sorted list of `cmd_<x>` function names this scan found but
    could not resolve to any verb (reported, never silently dropped)."""
    with io.open(path, encoding="utf-8") as fh:
        source = fh.read()
    tree = ast.parse(source, filename=path)
    cmd_funcs = _cmd_functions(tree)
    tables = _dispatch_tables(tree, cmd_funcs)
    router_of = _router_of(cmd_funcs, set(tables))
    consumed = set(router_of.values())
    top_level = sorted(t for t in tables if t not in consumed)
    discovered = []
    for t in top_level:
        discovered.extend(_expand(t, tables, router_of, [], set()))
    mapped = {f for _, f in discovered}
    no_data = sorted(name for name in cmd_funcs if name not in mapped)
    return discovered, no_data


def _target_files():
    """Every tools/bm_*.py plus tools/brothermode_cli.py, this suite's own
    file excluded (it is not a command module) and every test_*.py
    excluded (this is a scan of the shipped commands, not their tests)."""
    names = []
    for filename in sorted(os.listdir(TOOLS_DIR)):
        if not filename.endswith(".py") or filename.startswith("test_"):
            continue
        if filename in ("bm_effects.py",):
            continue
        if filename == "brothermode_cli.py" or filename.startswith("bm_"):
            names.append(filename)
    return names


# ---------------------------------------------------------------------------
# Test 1: every REGISTRY value is one of the five classes.
# ---------------------------------------------------------------------------

class TestRegistryClassesAreValid(unittest.TestCase):
    def test_every_registry_value_is_one_of_the_five_classes(self):
        bad = []
        for module in sorted(E.REGISTRY):
            for command in sorted(E.REGISTRY[module]):
                cls = E.REGISTRY[module][command]
                if cls not in E.CLASSES:
                    bad.append("%s %r -> %r" % (module, command, cls))
        self.assertEqual(
            [], bad,
            "REGISTRY values outside the five declared classes (%s): %s"
            % (", ".join(E.CLASSES), "; ".join(bad)))

    def test_classes_tuple_matches_the_five_constants(self):
        self.assertEqual(
            (E.PURE_READ, E.LEDGER_WRITE, E.PROJECT_WRITE, E.EXTERNAL_WRITE,
             E.DESTRUCTIVE_EXTERNAL_ACTION),
            E.CLASSES)


# ---------------------------------------------------------------------------
# Test 2: declared() raises, never defaults.
# ---------------------------------------------------------------------------

class TestDeclaredNeverDefaults(unittest.TestCase):
    def test_declared_raises_on_an_undeclared_command(self):
        with self.assertRaises(E.UndeclaredCommand):
            E.declared("bm_project.py", "this-command-does-not-exist")

    def test_declared_raises_on_an_undeclared_module(self):
        with self.assertRaises(E.UndeclaredCommand):
            E.declared("bm_this_module_does_not_exist.py", "status")

    def test_declared_returns_the_registered_class_for_a_real_pair(self):
        self.assertEqual(E.PURE_READ, E.declared("bm_project.py", "status"))
        self.assertEqual(E.LEDGER_WRITE, E.declared("bm_project.py", "start"))


# ---------------------------------------------------------------------------
# Test 3: completeness. This is the class-closing test: a new command
# cannot merge without a REGISTRY entry, because this test discovers it
# mechanically and fails, naming it, if one is missing.
# ---------------------------------------------------------------------------

class TestCompleteness(unittest.TestCase):
    def test_every_discovered_command_is_declared_in_the_registry(self):
        missing = []
        no_data_all = []
        for filename in _target_files():
            path = os.path.join(TOOLS_DIR, filename)
            discovered, no_data = discover_module(path)
            no_data_all.extend("%s:%s" % (filename, name) for name in no_data)
            registered = E.REGISTRY.get(filename, {})
            for verb, funcname in discovered:
                if verb not in registered:
                    missing.append("%s %r (-> %s)" % (filename, verb, funcname))
        message = ""
        if no_data_all:
            message += ("NO-DATA (dispatch could not be mechanically parsed "
                        "into a verb, not required in REGISTRY): %s\n"
                        % ", ".join(sorted(no_data_all)))
        if missing:
            message += ("undeclared commands (discovered but missing from "
                        "tools/bm_effects.py's REGISTRY): %s"
                        % "; ".join(sorted(missing)))
        # NO-DATA is always visible, pass or fail, per the spec's own
        # instruction not to silently pass over an unparseable module.
        sys.stderr.write(
            "bm_effects completeness: %d command(s) NO-DATA: %s\n"
            % (len(no_data_all), ", ".join(sorted(no_data_all)) or "(none)"))
        self.assertEqual([], missing, message)


# ---------------------------------------------------------------------------
# Tests 4 and 5: purity, against a real throwaway project.
# ---------------------------------------------------------------------------

def _diff_snapshots(before, after):
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    changed = sorted(k for k in (set(before) & set(after)) if before[k] != after[k])
    parts = []
    if added:
        parts.append("NEW FILE(S): %s" % ", ".join(added))
    if removed:
        parts.append("REMOVED FILE(S): %s" % ", ".join(removed))
    if changed:
        parts.append("CHANGED FILE(S): %s" % ", ".join(changed))
    return "; ".join(parts) if parts else "(no difference found)"


class _SandboxFixture(unittest.TestCase):
    """A real, freshly initialized throwaway project, built once per
    TestCase class. See this file's module docstring, ISOLATION, for why
    all four environment variables are pinned rather than only HOME."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="bm_effects_test_")
        cls.project_root = os.path.join(cls.tmp, "project")
        os.makedirs(cls.project_root)
        fake_home = os.path.join(cls.tmp, "home")
        os.makedirs(fake_home)
        vault = os.path.join(cls.tmp, "vault")
        cls.env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": fake_home,
            "BROTHERMODE_VAULT": vault,
            "BROTHERSBE_VAULT": vault,
            "BROTHERMODE_ROOT": cls.project_root,
        }
        cls.project_id = "p1"
        init = cls._run("bm_store.py", ["init"])
        if init.returncode != 0:
            raise AssertionError(
                "fixture setup: bm_store.py init failed (exit %d): %s%s"
                % (init.returncode, init.stdout, init.stderr))
        start = cls._run("bm_project.py", [
            "start", "--project-id", cls.project_id, "--name", "Test Project",
            "--actor-name", "bm-effects-test-harness"])
        if start.returncode != 0:
            raise AssertionError(
                "fixture setup: bm_project.py start failed (exit %d): %s%s"
                % (start.returncode, start.stdout, start.stderr))
        capture = cls._run("bm_learn.py", [
            "capture", "--trigger", "a founder correction",
            "--action", "do the thing this way instead", "--json"])
        if capture.returncode != 0:
            raise AssertionError(
                "fixture setup: bm_learn.py capture failed (exit %d): %s%s"
                % (capture.returncode, capture.stdout, capture.stderr))
        try:
            cls.candidate_id = json.loads(capture.stdout)["candidate_uuid"]
        except (ValueError, KeyError) as exc:
            raise AssertionError(
                "fixture setup: could not read candidate_uuid from "
                "bm_learn.py capture --json output %r: %s"
                % (capture.stdout, exc))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    @classmethod
    def _run(cls, module, argv, stdin_text=""):
        path = os.path.join(TOOLS_DIR, module)
        return subprocess.run(
            [sys.executable, path] + list(argv),
            cwd=cls.project_root, env=cls.env, input=stdin_text,
            capture_output=True, text=True, timeout=60)

    @classmethod
    def _snapshot(cls):
        """{relpath: (size, sha256)} for every file under project_root,
        the store's own WAL/SHM sidecars included: a new one appearing IS
        a write and must fail the purity check, not be filtered out."""
        out = {}
        for root, _dirs, files in os.walk(cls.project_root):
            for name in files:
                full = os.path.join(root, name)
                rel = os.path.relpath(full, cls.project_root).replace(os.sep, "/")
                try:
                    with io.open(full, "rb") as fh:
                        data = fh.read()
                except (IOError, OSError) as exc:
                    out[rel] = ("UNREADABLE:%s:%s" % (type(exc).__name__, exc), None)
                    continue
                out[rel] = (len(data), hashlib.sha256(data).hexdigest())
        return out


#: Extra argv a pure_read command needs to actually reach its own body
#: (past a required-flag usage check) rather than exit before ever
#: touching a store. Built from each command's own required-flag list,
#: read directly out of its source (see tools/bm_effects.py's REGISTRY
#: comments for the file:line evidence this suite is exercising).
#: Keyed by (module, verb); `self` below is the running _SandboxFixture
#: instance so the project id and candidate id created in setUpClass can
#: be substituted in.
def _argv_for(fixture, module, verb):
    overrides = {
        ("bm_project.py", "status"): ["status", "--project-id", fixture.project_id],
        ("bm_project.py", "next"): ["next", "--project-id", fixture.project_id],
        ("bm_project.py", "forecast show"):
            ["forecast", "show", "--project-id", fixture.project_id],
        ("brothermode_cli.py", "next"): ["next", "--project-id", fixture.project_id],
        ("bm_learn.py", "lookup"): ["lookup", "--query", "a test query"],
        ("bm_packs.py", "stakes"): ["stakes", fixture.candidate_id],
        ("bm_view.py", "explain"): ["explain", "--reason", "absolute-write-scope"],
        ("bm_lint_walltime.py", "main"):
            [os.path.join(TOOLS_DIR, "bm_lint_walltime.py")],
    }
    key = (module, verb)
    if key in overrides:
        return list(overrides[key])
    if verb == "main":
        return []
    return verb.split(" ")


class TestPurity(_SandboxFixture):
    """Test 4. Every pure_read command, run as a real subprocess against
    the real throwaway project, must leave it byte-identical. THIS IS
    WHERE THE ROOT CAUSE SURFACES: constructing a writable
    bm_store.Store is itself a write (WAL/SHM sidecars, git-excludes,
    chmod, possible migration), so any pure_read command that opens one
    instead of bm_store.ReadOnlyStore fails here, by construction, before
    a single line of its own logic runs."""

    def test_every_pure_read_command_writes_nothing(self):
        impure = []
        for module, verb in E.commands_of_class(E.PURE_READ):
            with self.subTest(module=module, verb=verb):
                argv = _argv_for(self, module, verb)
                before = self._snapshot()
                result = self._run(module, argv)
                after = self._snapshot()
                if before != after:
                    impure.append("%s %r" % (module, verb))
                self.assertEqual(
                    before, after,
                    "%s %r is declared pure_read in tools/bm_effects.py "
                    "but changed the sandbox (exit %d): %s\nstdout=%r "
                    "stderr=%r"
                    % (module, verb, result.returncode,
                       _diff_snapshots(before, after),
                       result.stdout[-1000:], result.stderr[-1000:]))
        sys.stderr.write(
            "bm_effects purity: %d pure_read command(s) actually wrote: %s\n"
            % (len(impure), ", ".join(impure) or "(none)"))


class TestHelpPurity(_SandboxFixture):
    """Test 5. `<module> --help` (bare, the literal reading of the spec)
    for every module in the registry must write nothing, and it does for
    every module here except by construction it CANNOT exercise
    tools/bm_threads.py's actual documented defect: its main() treats an
    unrecognized top-level token, including a literal "--help", as a
    plain usage request and returns before ever dispatching to a command
    (tools/bm_threads.py's own main(), the `fn is None` branch), so bare
    `bm_threads.py --help` never reaches cmd_dashboard at all. The
    documented defect is that a SUBCOMMAND ignores --help
    (tools/bm_threads.py:871-899, `dashboard` never inspects its own
    argv), which only the verb-level form below, `<module> <verb>
    --help`, can reach and therefore catch. Both forms run here so the
    suite is honest about which one is the real regression guard."""

    def test_bare_module_help_writes_nothing(self):
        impure = []
        for module in sorted(E.REGISTRY):
            with self.subTest(module=module):
                before = self._snapshot()
                result = self._run(module, ["--help"])
                after = self._snapshot()
                if before != after:
                    impure.append(module)
                self.assertEqual(
                    before, after,
                    "%s --help is not pure (exit %d): %s"
                    % (module, result.returncode, _diff_snapshots(before, after)))
        sys.stderr.write(
            "bm_effects --help purity (bare module): %d impure: %s\n"
            % (len(impure), ", ".join(impure) or "(none)"))

    def test_pure_read_command_help_writes_nothing(self):
        impure = []
        for module, verb in E.commands_of_class(E.PURE_READ):
            with self.subTest(module=module, verb=verb):
                argv = _argv_for(self, module, verb) + ["--help"]
                before = self._snapshot()
                result = self._run(module, argv)
                after = self._snapshot()
                if before != after:
                    impure.append("%s %r" % (module, verb))
                self.assertEqual(
                    before, after,
                    "%s %r --help is not pure (exit %d): %s"
                    % (module, verb, result.returncode,
                       _diff_snapshots(before, after)))
        sys.stderr.write(
            "bm_effects --help purity (verb): %d impure: %s\n"
            % (len(impure), ", ".join(impure) or "(none)"))


class TestPurityUnderAStoreThatIsBehind(unittest.TestCase):
    """The condition under which the defect is actually REACHABLE, added
    2026-08-10 after the first purity design could not see it.

    WHY THIS CLASS EXISTS, and it is the more useful half of this file.
    The purity test above snapshots a throwaway tree before and after a
    command and asserts byte equality. Against a HEALTHY store that test
    passes for every command, including the ones documented as read-only
    that open a WRITABLE Store. Measured, not assumed: sqlite auto
    checkpoints and removes the -wal and -shm files when the last
    connection closes cleanly, _ensure_git_excludes is idempotent and
    already satisfied, and a pure SELECT leaves the main database file
    byte identical. So the whole-process snapshot observes nothing.

    That is a probe that cannot reach the defect, which is a failure class
    this repository has recorded twice before, and it nearly went down as
    evidence that the commands were clean.

    The reachable condition is a store that is BEHIND. Store.__init__
    calls _verify_schema_or_raise(migrate=True), so any command that
    constructs a writable Store against an out of date database MIGRATES
    IT. Demonstrated by hand on 2026-08-10 before this test was written:
    a store forced to schema_version 17 was handed to
    `bm_project.py status --project-id nosuch`, a command documented as a
    read accessor, which exited 1 having found no such project, and the
    database came back at schema_version 18 with a different md5. A read
    only command migrated a database while failing.

    So this class is the one that gives the pure_read declaration meaning.
    It is EXPECTED TO FAIL for every command still opening a writable
    Store, and each failure names a real defect rather than a test
    artefact."""

    def _throwaway_root_behind_by_one_schema(self):
        """A real store, then forced one version back, which is the only
        state in which the migration write becomes observable."""
        root = tempfile.mkdtemp(prefix="bm-effects-behind-")
        self.addCleanup(shutil.rmtree, root, True)
        subprocess.run(["git", "init", "-q", root], check=False,
                       capture_output=True)
        home = os.path.join(root, "home"); os.makedirs(home)
        vault = os.path.join(root, "vault")
        env = {"PATH": os.environ.get("PATH", ""), "HOME": home,
               "BROTHERMODE_VAULT": vault, "BROTHERSBE_VAULT": vault,
               "BROTHERMODE_ROOT": root}
        subprocess.run([sys.executable,
                        os.path.join(TOOLS_DIR, "bm_store.py"), "init"],
                       env=env, capture_output=True, check=False)
        db = os.path.join(root, ".brothermode", "store.sqlite3")
        if not os.path.exists(db):
            self.skipTest("could not build a store here, so this is NO-DATA "
                          "rather than a pass: nothing was checked")
        conn = sqlite3.connect(db)
        try:
            current = conn.execute(
                "select value from meta where key='schema_version'").fetchone()
            conn.execute("update meta set value=? where key='schema_version'",
                         (str(int(current[0]) - 1),))
            conn.commit()
        finally:
            conn.close()
        return root, env, db

    def test_a_pure_read_command_does_not_migrate_a_store_that_is_behind(self):
        root, env, db = self._throwaway_root_behind_by_one_schema()
        def put_it_behind():
            """Re-downgrade before EVERY command, which is the difference
            between measuring all of them and measuring only the first.
            The first offender migrates the store to current, and a current
            store cannot be migrated again, so without this reset every
            later command would be measured against a state where the
            defect is unreachable and would be reported clean. A test that
            silently stops looking after its first hit is the same shape as
            the probes this file exists to replace."""
            conn = sqlite3.connect(db)
            try:
                cur = conn.execute(
                    "select value from meta where key='schema_version'"
                ).fetchone()
                conn.execute(
                    "update meta set value=? where key='schema_version'",
                    (str(int(cur[0]) - 1),))
                conn.commit()
            finally:
                conn.close()
            with io.open(db, "rb") as fh:
                return hashlib.sha256(fh.read()).hexdigest()

        offenders = []
        for module, command in E.commands_of_class(E.PURE_READ):
            before = put_it_behind()
            path = os.path.join(TOOLS_DIR, module)
            if not os.path.exists(path):
                continue
            try:
                # stdin CLOSED and a timeout, both load-bearing: at least one
                # pure_read command is a hook entry point that BLOCKS reading
                # a payload from stdin, so an inherited terminal makes this
                # test hang forever rather than fail. A hang is the worst
                # failure shape available to a gate: it reports nothing.
                subprocess.run([sys.executable, path] + command.split(),
                               env=env, capture_output=True, check=False,
                               stdin=subprocess.DEVNULL, timeout=30)
            except subprocess.TimeoutExpired:
                offenders.append("%s %s (TIMED OUT, not measured)"
                                 % (module, command))
                continue
            after = hashlib.sha256(io.open(db, "rb").read()).hexdigest()
            if after != before:
                offenders.append("%s %s" % (module, command))
                before = after
        self.assertEqual(
            offenders, [],
            "command(s) declared pure_read MIGRATED a database that was one "
            "schema version behind: %s. Constructing bm_store.Store runs "
            "_verify_schema_or_raise(migrate=True), so a read accessor that "
            "opens the writable class rewrites the store the moment it is "
            "not current. Route these through bm_store.ReadOnlyStore."
            % ", ".join(offenders))


if __name__ == "__main__":
    unittest.main()


