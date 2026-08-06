# From nothing to one working command, with its pinned test

This walks a contributor through adding exactly one new thing: a command a
user can invoke, backed by a real tool, checked by a real test that is
calibrated (proven able to fail) before it is trusted to pass. Every shape
used below is copied from a file that already exists in this repository,
named at each step. The full tool and test source below were written to a
scratch copy and actually run against this repository's own
`capabilities.status.json` before this document was written; the command
output quoted is the real output of that run, not a guess.

Per `EXTENSION-CONTRACT.md` in this same folder: a new command belongs on a
stable surface (`commands/*.md` calling a tool in `tools/`), never as a
schema change to the store or a second hook payload parser.

## 0. What we are building

A beginner-facing command, `/brotherme-capabilities`, that lists only the
capabilities this project has actually proven, by reading
`capabilities.status.json` and printing the rows whose `state` is
`"certified"`. It never invents a claim; it refuses plainly if the register
is missing or malformed, the same way `tools/bm_project_facts.py` refuses
rather than guesses (see its `FactError` class).

Three files, each mirroring an existing sibling:

| New file | Mirrors | Confirmed by |
|---|---|---|
| `tools/bm_capabilities.py` | `tools/bm_project_facts.py` (reads a fact file, raises `FactError` rather than guessing) | read in full |
| `tools/test_bm_capabilities.py` | `tools/test_bm_ledger.py` (subprocess-driven test class, calibrated refusal tests) | read in full |
| `commands/brotherme-capabilities.md` | `commands/brotherme-status.md` (frontmatter, outcome-first prose, names the exact command it runs) | read in full |

## 1. Read the sibling before writing anything

Before writing `tools/bm_capabilities.py`, `tools/bm_project_facts.py` was
read start to finish. The pattern it sets, and that the new tool follows:

- A short module docstring stating WHY THIS EXISTS, in the same voice as the
  rest of the tree (no em or en dashes, plain sentences).
- A `FactError` exception, raised, never a bare `sys.exit` or a swallowed
  exception, so a caller (a test, or another tool) can catch a well-typed
  failure instead of parsing stderr text.
- Reads via plain file I/O only. No network, no subprocess, matching the
  stated contract at the top of `tools/bm_project_facts.py`: "Python 3.9,
  standard library only. No network, no subprocess."
- A `main(argv)` function separate from the fact-reading function, so the
  fact-reading function (`certified_capabilities` below, mirroring `facts()`
  in the sibling) can be imported and tested directly, not only through a
  subprocess.

## 2. Write the tool: `tools/bm_capabilities.py`

```python
#!/usr/bin/env python3
"""Print the certified capabilities of BrotherMode, in plain language.

WHY THIS EXISTS
  capabilities.status.json is the register a page must agree with before it
  claims anything (see its own "source_of_truth" field). This tool reads
  that file and prints only the rows whose state is "certified", so a
  beginner-facing surface can list what is proven without anyone hand-typing
  a claim the register does not back.

Python 3.9, standard library only. No network, no subprocess.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


class FactError(Exception):
    """A fact could not be read from the tree. Never guessed, always raised."""


def certified_capabilities(root=ROOT):
    path = os.path.join(root, "capabilities.status.json")
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (IOError, OSError, ValueError) as exc:
        # ValueError catches json.JSONDecodeError too, so a malformed file
        # refuses the same way a missing one does, rather than a raw
        # traceback reaching the user.
        raise FactError("cannot read %s: %s" % (path, exc))
    rows = data.get("capabilities")
    if not isinstance(rows, list):
        raise FactError("%s: no capabilities list" % path)
    out = []
    for row in rows:
        if row.get("state") == "certified":
            cap_id, title = row.get("id"), row.get("title")
            if cap_id is None or title is None:
                raise FactError(
                    "%s: a certified row is missing id or title: %r"
                    % (path, row))
            out.append((cap_id, title))
    return out


def main(argv):
    root = argv[1] if len(argv) > 1 else ROOT
    try:
        rows = certified_capabilities(root)
    except FactError as exc:
        print("cannot list capabilities: %s" % exc, file=sys.stderr)
        return 1
    if not rows:
        print("no certified capabilities recorded")
        return 0
    for cap_id, title in rows:
        print("- %s: %s" % (cap_id, title))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

This file would land at `tools/bm_capabilities.py` in a real change. This
tutorial's tool and test were verified from a scratch copy against this
repository's real `capabilities.status.json`, read only; a contributor
writes them at `tools/bm_capabilities.py`, `tools/test_bm_capabilities.py`,
and `commands/brotherme-capabilities.md`. Run from the repository root, with
no argument, the tool defaults to it:

```
$ python3 tools/bm_capabilities.py
- single-writer-enforcement: Single writer per file for supported write tools, refused by a hook; other writes detected, not contained
- durable-store-and-recovery: Durable local store that survives a crash and can be recovered
- evidence-discipline: Current pages are held to the facts read out of the tree
- guided-beginner-flow: Guided beginner flow on Claude Code
- ci-macos-and-linux: Continuous integration on macOS and Linux
- telemetry-with-consent: Session telemetry recorded only after the user consents
- plugin-packaging: Two-command plugin install through Claude Code's own plugin manager
```

That is dated evidence, the real output of a run against this repository's
`capabilities.status.json` on 2026-08-06: the rows whose state was
`certified` that day (the file also carries `beta`, `experimental`, and
`unsupported` rows this tool correctly leaves out). The count moves as
capabilities change; run the command yourself rather than trusting this
number.

## 3. Write the pinned test first, calibrated

"Pinned" here means the test is committed alongside the tool, added to
`SUITES` in `tools/test_all.py` (see step 5), and never run only by hand.
"Calibrated" means each refusal path is exercised by an input built to break
it, matching `references/definition-of-done.md` point 7: "A calibration
proves the test can fail for the intended defect." The shape below mirrors
`tools/test_bm_ledger.py`: a `unittest.TestCase`, a `run()` helper that
shells out to the real tool as a subprocess so the test proves what a user
actually gets on stdout, and `setUp`/`tearDown` using a temp directory so no
test touches the repository's own `capabilities.status.json`.

```python
"""bm_capabilities.py prints only certified rows, and refuses cleanly when
the register is missing or malformed. Calibrated: each refusal test breaks
the input first and checks the tool reports it rather than crashing or
printing nothing silently.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "bm_capabilities.py")


def run(root):
    out = subprocess.run([sys.executable, TOOL, root],
                          capture_output=True, text=True, timeout=30)
    return out.returncode, out.stdout + out.stderr


class TestCertifiedCapabilities(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bm-capabilities-test-")
        self.path = os.path.join(self.root, "capabilities.status.json")

    def write(self, rows):
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump({"capabilities": rows}, fh)

    def test_only_certified_rows_are_printed(self):
        self.write([
            {"id": "a", "title": "Proven thing", "state": "certified"},
            {"id": "b", "title": "Planned thing", "state": "experimental"},
        ])
        code, text = run(self.root)
        self.assertEqual(code, 0, text)
        self.assertIn("Proven thing", text)
        self.assertNotIn("Planned thing", text)

    def test_no_certified_rows_says_so_plainly(self):
        self.write([{"id": "a", "title": "Planned thing", "state": "experimental"}])
        code, text = run(self.root)
        self.assertEqual(code, 0, text)
        self.assertIn("no certified capabilities recorded", text)

    def test_a_missing_register_is_refused_not_crashed(self):
        # Calibration: no capabilities.status.json written at all.
        code, text = run(self.root)
        self.assertEqual(code, 1, text)
        self.assertIn("cannot list capabilities", text)

    def test_a_malformed_register_is_refused_not_crashed(self):
        # Calibration: valid JSON, but capabilities is not a list.
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump({"capabilities": "not-a-list"}, fh)
        code, text = run(self.root)
        self.assertEqual(code, 1, text)
        self.assertIn("no capabilities list", text)

    def test_invalid_json_is_refused_not_crashed(self):
        # Calibration: the register file exists but is not valid JSON.
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write("{not valid json")
        code, text = run(self.root)
        self.assertEqual(code, 1, text)
        self.assertIn("cannot list capabilities", text)

    def test_a_certified_row_missing_a_key_is_refused_not_crashed(self):
        # Calibration: a certified row with no title.
        self.write([{"id": "a", "state": "certified"}])
        code, text = run(self.root)
        self.assertEqual(code, 1, text)
        self.assertIn("cannot list capabilities", text)


if __name__ == "__main__":
    unittest.main()
```

This file would land at `tools/test_bm_capabilities.py`. It was verified the
same way, from the scratch copy, dated evidence of a run on 2026-08-06:

```
$ python3 -m unittest test_bm_capabilities -v
test_a_certified_row_missing_a_key_is_refused_not_crashed (test_bm_capabilities.TestCertifiedCapabilities) ... ok
test_a_malformed_register_is_refused_not_crashed (test_bm_capabilities.TestCertifiedCapabilities) ... ok
test_a_missing_register_is_refused_not_crashed (test_bm_capabilities.TestCertifiedCapabilities) ... ok
test_invalid_json_is_refused_not_crashed (test_bm_capabilities.TestCertifiedCapabilities) ... ok
test_no_certified_rows_says_so_plainly (test_bm_capabilities.TestCertifiedCapabilities) ... ok
test_only_certified_rows_are_printed (test_bm_capabilities.TestCertifiedCapabilities) ... ok

----------------------------------------------------------------------
Ran 6 tests in 0.119s

OK
```

Notice the four calibration tests (`test_a_missing_register_is_refused_not_crashed`,
`test_a_malformed_register_is_refused_not_crashed`,
`test_invalid_json_is_refused_not_crashed`, and
`test_a_certified_row_missing_a_key_is_refused_not_crashed`) each break the
input in one specific way before asserting the tool's exact refusal
behavior. That is the check that the test can fail for the intended defect:
comment out the `isinstance(rows, list)` guard in the tool and
`test_a_malformed_register_is_refused_not_crashed` stops passing; drop the
`ValueError` from the tool's `except` clause and
`test_invalid_json_is_refused_not_crashed` stops passing with a clean
refusal (the tool crashes with a raw traceback instead); drop the
`cap_id is None or title is None` guard and
`test_a_certified_row_missing_a_key_is_refused_not_crashed` stops passing
the same way. Each of those is what makes its test worth keeping.

## 4. Write the command: `commands/brotherme-capabilities.md`

Mirroring the frontmatter and prose shape of `commands/brotherme-status.md`
exactly (one `description` line, then plain-language prose naming the exact
mechanical command and where its output comes from):

```markdown
---
description: List what BrotherMode has actually proven, in plain language
---

Outcome to produce: the short, current list of capabilities this project has
proven today, never a claim from memory of this conversation.

Run the mechanical command `python3 tools/bm_capabilities.py` from the
BrotherME install folder (a plugin install runs it from the plugin's own
root, a clone install runs it from `~/.claude/skills/brothermode`) and read
its output back to the user exactly as printed. Never add a capability to
the answer that the command did not print, and never soften "no certified
capabilities recorded" into a claim that something is coming: that sentence
is the honest answer when the register holds none.

For everything this project has NOT proven yet, and why, point to
`docs/KNOWN-LIMITS.md` rather than reading `capabilities.status.json`'s
`beta`, `experimental`, and `unsupported` rows aloud; those rows exist so a
page can be checked against them, not so this command narrates all four
states by default.
```

This file would land at `commands/brotherme-capabilities.md`.

## 5. Wire it into the gate

Four mechanical steps this repository requires before a new test counts as
run at all, each confirmed by reading the file it changes. Skipping any one
of them leaves the gate red for the next person, not just for you:

1. Add `"test_bm_capabilities.py"` to the `SUITES` tuple in
   `tools/test_all.py`. `tools/test_all.py` itself checks for exactly this
   omission: a `test_*.py` file that exists but is not listed in `SUITES` is
   "reported loudly rather than skipped."
2. Add `"bm_capabilities"` to the `py-modules` array in `pyproject.toml`.
   `tools/test_bm.py::test_every_shipping_tool_is_in_py_modules` fails any
   tool that ships in `tools/` but is missing from that array, because a
   pip or pipx install would then silently not carry it.
3. Add `"commands/brotherme-capabilities.md"` to the pinned list inside
   `tools/test_bm.py::test_exactly_seven_brotherme_commands_ship`, with one
   sentence in that test saying why the shipped set grew. That test's own
   comment asks for exactly this: "every growth of the set costs somebody a
   sentence here rather than landing quietly." Its name is out of date on
   purpose and stays that way; what it checks is the pinned list of file
   names, and a command file nobody added there fails the build even though
   it exists on disk and works correctly.
4. Add a step to `.github/workflows/tests.yml` that runs
   `python3 tools/test_bm_capabilities.py`, an actual interpreter
   invocation, not an echo. `tools/test_all.py`'s own inventory check
   refuses to run anything, exit code 2, when a suite is in `SUITES` but no
   CI step executes it ("these suites are in the local gate but are never
   run by CI"), so skipping this step blocks the entire gate, not only the
   new suite.
5. Run the project's real gate command, copied verbatim from
   `tools/bm_project_facts.py`'s own `GATE_COMMAND` constant, never invented:

   ```
   python3 tools/test_all.py
   ```

   The expected verdict, also read from that same file rather than assumed,
   is `GATE_EXPECTATION = "ALL GREEN"`.

## 6. What still has to happen for this to be a real change

This tutorial verified the tool and its test in isolation, from a scratch
copy, against this repository's real `capabilities.status.json`, read only.
It did not:

- Place the three files at their real repository paths: `tools/bm_capabilities.py`,
  `tools/test_bm_capabilities.py`, and `commands/brotherme-capabilities.md`.
- Perform any of the four steps in section 5 against the real tree (add the
  suite to `SUITES`, add the module to `py-modules`, add the command name to
  the pinned list in `tools/test_bm.py::test_exactly_seven_brotherme_commands_ship`,
  add the CI step to `.github/workflows/tests.yml`), or run the full gate
  (`python3 tools/test_all.py`) against the whole tree. Only the one new
  test file was run, in isolation.
- Run `tools/test_bm_docs.py`, which is the suite that would catch a command
  file whose prose drifts from the facts this project allows it to state
  (see `EXTENSION-CONTRACT.md`, point 1).
- Get review against `references/definition-of-done.md` in full; this
  tutorial only walks steps 6, 7, and 8 of that fifteen-point list
  (tests added at the right level, a calibration proving the test can fail,
  verification run after the final edit).

A contributor finishing this for real closes each of those before calling it
done, per `references/definition-of-done.md`.
