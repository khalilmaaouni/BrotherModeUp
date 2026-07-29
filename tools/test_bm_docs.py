#!/usr/bin/env python3
"""Documentation consistency tests. Run: python3 tools/test_bm_docs.py

WHY THIS SUITE EXISTS
  Loop 10 of the post-audit plan: active documentation kept carrying facts that
  had already moved. A quickstart told installers to expect a test count that
  was 90 tests out of date, and then told them a mismatch meant a broken
  install. Install pages listed four hooks while five shipped, so the fence,
  the one hook that can refuse a write, was off on every hand-wired install.
  A README declared a defect open that had been closed two days earlier.

  Every one of those was reproducible by reading a file, which means a test can
  catch it. This suite compares the pages against tools/bm_project_facts.py,
  which reads the facts out of the tree instead of out of someone's memory.

WHAT IT DELIBERATELY DOES NOT DO
  It does not require documentation to quote a test count correctly. It
  requires active pages not to quote one at all: counts move with every test
  that lands, and a page pinned to one trains readers to distrust the page.
  Exact counts stay in dated evidence (CHANGELOG.md, the dated files under
  docs/ and its subdirectories), which this suite treats as historical and
  leaves alone, checking only that they say so at the top.

Standard library only. Python 3.9. Reads files, writes none.
No em or en dashes anywhere in this file or its output.
"""
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FACTS_PATH = os.path.join(HERE, "bm_project_facts.py")

_spec = importlib.util.spec_from_file_location("bm_project_facts", FACTS_PATH)
bpf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bpf)
FACTS = bpf.facts()

# Pages a new installer reads as CURRENT state. Anything not listed here is
# either dated evidence (checked separately, below) or a register with its own
# rules (docs/NOT-FINALIZED.md carries dated numbers on purpose).
ACTIVE_DOCS = (
    "README.md",
    "SKILL.md",
    os.path.join("docs", "QUICKSTART.md"),
    os.path.join("docs", "SETUP.md"),
    os.path.join("docs", "RELEASE.md"),
    os.path.join("docs", "HOOKS.md"),
    os.path.join("docs", "HOW-IT-WORKS.md"),
    os.path.join("docs", "CORRECTION-LEARNING.md"),
    os.path.join("docs", "KNOWN-LIMITS.md"),
)

# The three install pages. Every one of them must describe the same install.
INSTALL_DOCS = ("README.md", os.path.join("docs", "QUICKSTART.md"),
                os.path.join("docs", "SETUP.md"))

# A file under docs/ whose NAME carries a date is dated evidence by convention.
# The scan is recursive: the design specs and plans live in subdirectories, and
# README links straight into one of them, so a marker check that only read the
# top level left the linked page reading as current state.
DATED_NAME = re.compile(r"\d{4}-\d{2}-\d{2}.*\.md$")

# A version claim about the tree the reader is holding, as opposed to a mention
# of an older release in a history section. Only the current-state phrasings.
VERSION_TOKEN = r"[`'\"]?v?(\d+\.\d+\.\d+(?:-[0-9A-Za-z.]+)?)"
VERSION_CLAIM = re.compile(
    r"(?:you are (?:installing|running|on)|"
    r"this (?:is|release is|version is|tree is)|"
    r"the current (?:version|release|candidate|tag)(?: is)?|"
    r"current(?:ly)? at|"
    r"the version (?:is|here is))"
    r"(?:\s+(?:version|release|tag|candidate))?\s+" + VERSION_TOKEN,
    re.IGNORECASE)

NUMBER_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
                6: "six", 7: "seven", 8: "eight"}


def read(rel):
    with io.open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def dated_docs():
    """Every dated document under docs/, at any depth, repo-relative."""
    out = []
    for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, "docs")):
        for name in sorted(filenames):
            if DATED_NAME.search(name):
                out.append(os.path.relpath(os.path.join(dirpath, name), ROOT))
    return sorted(out)


class TestGeneratedFacts(unittest.TestCase):
    def test_the_tool_runs_and_prints_the_facts_docs_rely_on(self):
        r = subprocess.run([sys.executable, FACTS_PATH],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           universal_newlines=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads(r.stdout)
        for key in ("version", "release_tag", "schema_version", "hook_count",
                    "hook_events", "test_suites", "test_suite_files",
                    "gate_command", "supported_python_floor", "default_branch",
                    "retrieval_modes"):
            self.assertIn(key, data)
        self.assertEqual(data["release_tag"], "v" + data["version"])
        self.assertEqual(data["hook_count"], len(data["hook_events"]))
        self.assertEqual(data["test_suites"], len(data["test_suite_files"]))

    def test_it_reports_only_retrieval_modes_the_code_builds(self):
        """bm_learning.py discusses FTS5 as future work. A page that advertised
        it because a docstring mentioned it would be selling a mode nobody
        wrote, so the probe requires the virtual table, not the word."""
        store = read(os.path.join("tools", "bm_store.py"))
        built = bool(re.search(r"USING\s+fts5", store, re.IGNORECASE))
        self.assertEqual("fts5" in FACTS["retrieval_modes"], built)
        self.assertIn("lexical", FACTS["retrieval_modes"])

    def test_every_named_suite_file_exists(self):
        for name in FACTS["test_suite_files"]:
            self.assertTrue(os.path.exists(os.path.join(HERE, name)), name)


class TestNoStaleCurrentNumbers(unittest.TestCase):
    COUNT_PATTERNS = (
        re.compile(r"Ran\s+\d+\s+tests"),
        re.compile(r"\b\d+\s+tests\b"),
        re.compile(r"exactly\s+\d+\s+tests?", re.IGNORECASE),
    )

    def test_no_active_document_pins_a_test_count(self):
        offenders = []
        for rel in ACTIVE_DOCS:
            for i, line in enumerate(read(rel).split("\n"), 1):
                for pat in self.COUNT_PATTERNS:
                    if pat.search(line):
                        offenders.append("%s:%d %s" % (rel, i, line.strip()[:90]))
                        break
        self.assertEqual(
            offenders, [],
            "an active page pins a test count (%s). Counts move with every test "
            "that lands; say to run %s and expect %s instead, and keep exact "
            "counts in dated evidence."
            % ("; ".join(offenders), FACTS["gate_command"],
               FACTS["gate_expectation"]))

    def test_no_active_document_states_a_wrong_hook_count(self):
        """Catches the phrasings that actually went stale, without banning the
        legitimate 'the other four hooks' in docs/HOOKS.md, which counts the
        four non-fence hooks and is correct."""
        current = NUMBER_WORDS[FACTS["hook_count"]]
        # Plural only, and never the singular "the one hook that can refuse a
        # write", which is a description of the fence rather than a count.
        shapes = (r"wire the (\w+) hooks\b", r"through (\w+) hooks\b",
                  r"\bthe (\w+) hooks\b", r"(\w+) hook entries\b",
                  r"a list of (\w+) hooks\b")
        offenders = []
        for rel in ACTIVE_DOCS:
            text = read(rel)
            for shape in shapes:
                for m in re.finditer(shape, text):
                    word = m.group(1).lower()
                    if word in NUMBER_WORDS.values() and word != current:
                        offenders.append("%s: %r" % (rel, m.group(0)))
        self.assertEqual(
            offenders, [],
            "a page states a hook count that is not %d (%s). scripts/install.py "
            "HOOK_EVENTS is the source; run bm_project_facts.py --field "
            "hook_events." % (FACTS["hook_count"], "; ".join(offenders)))

    def test_every_install_page_names_every_hook_event(self):
        """The fence shipped OFF for anyone wiring by hand because PreToolUse
        was in docs/HOOKS.md and in no install page. Naming the event is the
        minimum; leaving one out is how that happened."""
        missing = []
        for rel in INSTALL_DOCS:
            text = read(rel)
            for event in FACTS["hook_events"]:
                if event not in text:
                    missing.append("%s: %s" % (rel, event))
        self.assertEqual(missing, [], "install page omits a hook event: %s"
                         % "; ".join(missing))

    def test_the_hand_wiring_blocks_actually_wire_the_fence(self):
        """Naming the event in prose is not wiring it. The JSON block a reader
        copies has to contain the fence command and its matcher."""
        for rel in (os.path.join("docs", "QUICKSTART.md"),
                    os.path.join("docs", "SETUP.md")):
            text = read(rel)
            self.assertIn("bm_fence_hook.py", text,
                          "%s: the copy-paste hook block has no fence command" % rel)
            self.assertIn("Edit|Write|MultiEdit|NotebookEdit", text,
                          "%s: the fence entry has no matcher, so writes through "
                          "the unlisted tools are ungated" % rel)


class TestOneInstall(unittest.TestCase):
    CLONE = re.compile(r"^git clone .*BrotherModeUp\.git.*$", re.MULTILINE)

    def test_the_plain_install_command_is_identical_everywhere(self):
        seen = {}
        for rel in INSTALL_DOCS:
            for line in self.CLONE.findall(read(rel)):
                if "--branch" in line:
                    continue
                seen.setdefault(line.strip(), []).append(rel)
        self.assertEqual(
            len(seen), 1,
            "the install pages disagree about the clone command: %s"
            % json.dumps(seen, indent=2, sort_keys=True))

    def test_the_pinned_install_uses_the_current_release_tag(self):
        text = read(os.path.join("docs", "RELEASE.md"))
        pinned = [l for l in self.CLONE.findall(text) if "--branch" in l]
        self.assertTrue(pinned, "docs/RELEASE.md no longer shows a pinned clone")
        for line in pinned:
            tag = re.search(r"--branch\s+(\S+)", line).group(1)
            self.assertEqual(
                tag, FACTS["release_tag"],
                "docs/RELEASE.md pins %s but VERSION says the current release "
                "is %s" % (tag, FACTS["release_tag"]))

    def test_no_active_page_sends_an_installer_to_a_non_default_branch(self):
        offenders = []
        for rel in ACTIVE_DOCS:
            for m in re.finditer(r"git clone[^\n]*--branch\s+(\S+)", read(rel)):
                ref = m.group(1)
                if ref != FACTS["release_tag"] and ref != FACTS["default_branch"]:
                    offenders.append("%s: %s" % (rel, ref))
        self.assertEqual(offenders, [],
                         "a page clones a branch that is neither the default "
                         "branch (%s) nor the current tag (%s): %s"
                         % (FACTS["default_branch"], FACTS["release_tag"],
                            "; ".join(offenders)))


class TestVersionAndSchemaAgree(unittest.TestCase):
    def test_release_md_states_the_current_version(self):
        text = read(os.path.join("docs", "RELEASE.md"))
        self.assertIn(FACTS["version"], text,
                      "docs/RELEASE.md never names the current version %s"
                      % FACTS["version"])

    def test_no_active_page_claims_a_version_other_than_the_current_one(self):
        """The defect this suite was written after was docs/RELEASE.md pinning
        rc.2 while VERSION said rc.3. Asserting that RELEASE.md CONTAINS the
        current version does not catch it: a page can name the current version
        in one paragraph and claim a stale one in the next. This forbids the
        claim itself, on every active page.

        It matches current-state phrasings only ("you are installing X", "the
        current release is X"). A history section that names an older tag
        ("v2.0.0-rc.1 IS withdrawn") is dated evidence and stays legal, which
        is why the pattern is anchored to the claim and not to the number."""
        offenders = []
        for rel in ACTIVE_DOCS:
            for i, line in enumerate(read(rel).split("\n"), 1):
                for m in VERSION_CLAIM.finditer(line):
                    if m.group(1) != FACTS["version"]:
                        offenders.append("%s:%d %s" % (rel, i, m.group(0)))
        self.assertEqual(
            offenders, [],
            "an active page claims a version other than %s (%s). VERSION is the "
            "source; run python3 tools/bm_project_facts.py --field version, or "
            "delegate the sentence to it."
            % (FACTS["version"], "; ".join(offenders)))

    def test_no_active_page_states_a_different_schema_version(self):
        offenders = []
        pat = re.compile(r"schema[_ ]version[^\d\n]{0,12}(\d+)", re.IGNORECASE)
        for rel in ACTIVE_DOCS:
            for m in pat.finditer(read(rel)):
                if int(m.group(1)) != FACTS["schema_version"]:
                    offenders.append("%s: %s" % (rel, m.group(0)))
        self.assertEqual(offenders, [],
                         "a page states a schema version other than %d: %s"
                         % (FACTS["schema_version"], "; ".join(offenders)))

    def test_no_active_page_states_a_different_python_floor(self):
        offenders = []
        pat = re.compile(r"Python\s+3\.(\d+)\s+or newer", re.IGNORECASE)
        for rel in ACTIVE_DOCS:
            for m in pat.finditer(read(rel)):
                if "3." + m.group(1) != FACTS["supported_python_floor"]:
                    offenders.append("%s: %s" % (rel, m.group(0)))
        self.assertEqual(offenders, [],
                         "a page states a Python floor other than %s: %s"
                         % (FACTS["supported_python_floor"], "; ".join(offenders)))


class TestHistoricalDocumentsSaySo(unittest.TestCase):
    def test_every_dated_document_is_marked_historical_at_the_top(self):
        """A dated handover that does not say it is historical reads as current
        state to anyone who lands on it, which is how a two-day-old branch name
        and a stale test count get treated as today's truth. Recursive on
        purpose: README links into docs/superpowers/specs/, where a spec opens
        with a DO NOT PUBLISH verdict that was resolved days ago."""
        offenders = []
        for rel in dated_docs():
            head = "\n".join(read(rel).split("\n")[:25])
            if "HISTORICAL" not in head:
                offenders.append(rel)
        self.assertEqual(
            offenders, [],
            "dated document(s) with no HISTORICAL marker in the first 25 lines: "
            "%s. Add the marker and a superseded-by pointer, or the page reads "
            "as current state." % ", ".join(offenders))

    def test_the_marker_carries_a_superseded_by_pointer(self):
        offenders = []
        for rel in dated_docs():
            head = "\n".join(read(rel).split("\n")[:25])
            if "HISTORICAL" in head and "uperseded by" not in head:
                offenders.append(rel)
        self.assertEqual(offenders, [],
                         "marked historical but names nothing to read instead: %s"
                         % ", ".join(offenders))


class TestNoDashes(unittest.TestCase):
    """The project's own copy rule, enforced on the files this suite governs."""

    def test_no_em_or_en_dash_in_the_active_pages_or_this_toolchain(self):
        offenders = []
        targets = list(ACTIVE_DOCS) + [os.path.join("tools", "bm_project_facts.py"),
                                       os.path.join("tools", "test_bm_docs.py")]
        for rel in targets:
            for i, line in enumerate(read(rel).split("\n"), 1):
                if "\u2013" in line or "\u2014" in line:
                    offenders.append("%s:%d" % (rel, i))
        self.assertEqual(offenders, [], "em or en dash found at %s"
                         % ", ".join(offenders))


if __name__ == "__main__":
    unittest.main(verbosity=1)
