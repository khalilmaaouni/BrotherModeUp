#!/usr/bin/env python3
"""Print the project facts that documentation is allowed to state, as JSON.

WHY THIS EXISTS
  Documentation kept carrying facts that had already moved: a test count from
  three loops ago, a hook count from before the fence hook was wired, a release
  tag from the previous candidate. Every one of those numbers already exists
  somewhere in the code or in a one-line file. This tool reads them from there,
  so a page can be checked against the tree instead of against someone's memory.

WHAT IT DELIBERATELY DOES NOT PRINT
  A total test count. It changes on every test that lands, which makes every
  page that quotes it wrong within a day, and a reader who sees a mismatch
  cannot tell a stale page from a broken install. The gate command and its
  expected verdict are printed instead: run it, expect ALL GREEN. Exact counts
  belong in dated release evidence (CHANGELOG.md, the dated baseline files),
  where the date says what the number was true of.

WHERE EACH FACT COMES FROM
  version, release_tag        VERSION (one line)
  schema_version              tools/bm_store.py, SCHEMA_VERSION
  test_suites, suite files    tools/test_all.py, the SUITES tuple
  hook_events, hook_count     scripts/install.py, HOOK_EVENTS
  supported_python_floor      scripts/install.py, its version_info guard
  retrieval_modes             probed in tools/bm_store.py and tools/bm_learning.py
  default_branch              declared below; git cannot be asked without a
                              subprocess, and shipping tools run none

Python 3.9, standard library only. No network, no subprocess. Reads files,
writes none. No em or en dashes anywhere in this file or its output.

Usage:
  python3 tools/bm_project_facts.py            # JSON on stdout
  python3 tools/bm_project_facts.py --field version
"""

import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# The branch a fresh clone lands on. Declared, not measured: asking git would
# need a subprocess, which every shipping tool in tools/ is banned from. If the
# default branch ever changes, this line changes with it and the documentation
# consistency suite (tools/test_bm_docs.py) fails until the pages agree.
DEFAULT_BRANCH = "main"

# The one command this project gates on, and the verdict a healthy run ends on.
GATE_COMMAND = "python3 tools/test_all.py"
GATE_EXPECTATION = "ALL GREEN"


class FactError(Exception):
    """A fact could not be read from the tree. Never guessed, always raised."""


def _read(path):
    try:
        with io.open(path, encoding="utf-8") as fh:
            return fh.read()
    except (IOError, OSError) as exc:
        raise FactError("cannot read %s: %s" % (path, exc))


def _search(pattern, text, path, what):
    m = re.search(pattern, text, re.MULTILINE)
    if not m:
        raise FactError(
            "%s no longer states %s in the form this tool reads (%s). "
            "Fix the pattern here rather than hand-writing the fact into a page."
            % (path, what, pattern))
    return m


def _tuple_strings(text, name, path):
    """Return the string literals of a top level NAME = ( ... ) tuple."""
    m = _search(r"^%s\s*=\s*\(" % re.escape(name), text, path, name)
    depth, i = 0, m.end() - 1
    while i < len(text):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                break
        i += 1
    if depth != 0:
        raise FactError("%s: unbalanced parentheses after %s" % (path, name))
    items = re.findall(r'["\']([^"\']+)["\']', text[m.end():i])
    if not items:
        raise FactError("%s: %s holds no string entries" % (path, name))
    return items


def facts(root=ROOT):
    tools = os.path.join(root, "tools")
    scripts = os.path.join(root, "scripts")

    version = _read(os.path.join(root, "VERSION")).strip()
    if not version:
        raise FactError("VERSION is empty")

    store_src = _read(os.path.join(tools, "bm_store.py"))
    schema = int(_search(r"^SCHEMA_VERSION\s*=\s*(\d+)", store_src,
                         "tools/bm_store.py", "SCHEMA_VERSION").group(1))

    all_src = _read(os.path.join(tools, "test_all.py"))
    suites = _tuple_strings(all_src, "SUITES", "tools/test_all.py")

    install_src = _read(os.path.join(scripts, "install.py"))
    hooks = _tuple_strings(install_src, "HOOK_EVENTS", "scripts/install.py")
    floor = _search(r"sys\.version_info\s*<\s*\((\d+),\s*(\d+)\)", install_src,
                    "scripts/install.py", "a Python floor guard")
    python_floor = "%s.%s" % (floor.group(1), floor.group(2))

    # Retrieval is lexical today. fts5 counts as available only when the store
    # actually creates the virtual table, never because a docstring mentions it
    # as a plan: tools/bm_learning.py discusses FTS5 as future work, and a
    # keyword probe over prose would advertise a mode nobody built.
    modes = ["lexical"]
    if re.search(r"USING\s+fts5", store_src, re.IGNORECASE):
        modes.append("fts5")

    return {
        "version": version,
        "release_tag": "v" + version,
        "schema_version": schema,
        "test_suites": len(suites),
        "test_suite_files": suites,
        "gate_command": GATE_COMMAND,
        "gate_expectation": GATE_EXPECTATION,
        "hook_count": len(hooks),
        "hook_events": hooks,
        "retrieval_modes": modes,
        "supported_python_floor": python_floor,
        "default_branch": DEFAULT_BRANCH,
    }


def main(argv):
    field = None
    if argv:
        if argv[0] != "--field" or len(argv) != 2:
            print("usage: bm_project_facts.py [--field NAME]", file=sys.stderr)
            return 2
        field = argv[1]
    try:
        data = facts()
    except FactError as exc:
        print("bm_project_facts: %s" % exc, file=sys.stderr)
        return 2
    if field is None:
        print(json.dumps(data, indent=2, sort_keys=True))
        return 0
    if field not in data:
        print("bm_project_facts: no such fact %r; known: %s"
              % (field, ", ".join(sorted(data))), file=sys.stderr)
        return 2
    value = data[field]
    print(value if not isinstance(value, list) else " ".join(map(str, value)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
