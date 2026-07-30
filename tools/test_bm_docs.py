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
import contextlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FACTS_PATH = os.path.join(HERE, "bm_project_facts.py")

_spec = importlib.util.spec_from_file_location("bm_project_facts", FACTS_PATH)
bpf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bpf)
FACTS = bpf.facts()

# The eight required pack sections, read from the generator rather than retyped:
# a test that keeps its own copy of the list stops testing the order the moment
# the two disagree.
_pspec = importlib.util.spec_from_file_location(
    "bm_packs_for_docs_tests", os.path.join(HERE, "bm_packs.py"))
_bpk = importlib.util.module_from_spec(_pspec)
_pspec.loader.exec_module(_bpk)
_PACK_SECTIONS = _bpk.SECTIONS

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

# The one alternative to the HISTORICAL marker on a dated page: an explicit
# statement that the page is current. Anchored to the word Status so a passing
# mention of the word "current" in prose does not silently satisfy it.
CURRENT_STATUS = re.compile(r"^Status:\s*CURRENT\b", re.MULTILINE)

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
    def test_every_dated_document_declares_its_status_at_the_top(self):
        """A dated handover that does not say what it is reads as current state
        to anyone who lands on it, which is how a two-day-old branch name and a
        stale test count get treated as today's truth. Recursive on purpose:
        README links into docs/superpowers/specs/, where a spec opens with a DO
        NOT PUBLISH verdict that was resolved days ago.

        TWO legal declarations, not one (2026-07-30). The original rule demanded
        the HISTORICAL marker on every dated page, which left the NEWEST spec
        with no honest way to pass: commit 91d48d8 landed the current gate-pack
        spec and this suite went red, because the only way to satisfy it was to
        call a live document historical. A dated page may now instead declare
        `Status: CURRENT`, which is the true statement in that case. What stays
        forbidden, and is the whole point, is a dated page that declares
        nothing."""
        offenders = []
        for rel in dated_docs():
            head = "\n".join(read(rel).split("\n")[:25])
            if "HISTORICAL" not in head and not CURRENT_STATUS.search(head):
                offenders.append(rel)
        self.assertEqual(
            offenders, [],
            "dated document(s) that declare no status in the first 25 lines: "
            "%s. Either mark it HISTORICAL with a superseded-by pointer, or "
            "state `Status: CURRENT` if it really is current."
            % ", ".join(offenders))

    def test_the_marker_carries_a_superseded_by_pointer(self):
        offenders = []
        for rel in dated_docs():
            head = "\n".join(read(rel).split("\n")[:25])
            if "HISTORICAL" in head and "uperseded by" not in head:
                offenders.append(rel)
        self.assertEqual(offenders, [],
                         "marked historical but names nothing to read instead: %s"
                         % ", ".join(offenders))


class TestGatePacks(unittest.TestCase):
    """Phase A of docs/superpowers/specs/2026-07-30-documentation-and-gate-packs
    -design.md, section 4.4. Extends this suite rather than adding one, per
    section 8: test_all.py refuses an unregistered suite.

    Every pack here is generated by the real CLI against a real store in a
    throwaway directory. Nothing touches this repository's own files.
    """

    PACKS = os.path.join(HERE, "bm_packs.py")
    CITED = "app/pay.py"
    # The cited module, written into the fixture so a test can MOVE a line in it
    # and prove that generation fails loudly (I11).
    CITED_SOURCE = (
        "\"\"\"a tiny payments module, for the fixture\"\"\"\n"
        "\n"
        "\n"
        "def charge(amount):\n"
        "    \"\"\"take the money once\"\"\"\n"
        "    return amount\n"
        "\n"
        "\n"
        "def refund(amount):\n"
        "    return -amount\n")

    def _bs(self):
        spec = importlib.util.spec_from_file_location(
            "bm_store_for_pack_tests", os.path.join(HERE, "bm_store.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def _write(self, root, rel, text):
        full = os.path.join(root, *rel.split("/"))
        parent = os.path.dirname(full)
        if parent and not os.path.isdir(parent):
            os.makedirs(parent)
        with io.open(full, "w", encoding="utf-8") as fh:
            fh.write(text)
        return full

    def _project(self, d, with_alert=False):
        """A real store, a real work record, a real pending candidate, plus a
        caller, a test and a document so the dependency search has something
        true to find."""
        bs = self._bs()
        self._write(d, self.CITED, self.CITED_SOURCE)
        self._write(d, "app/checkout.py",
                    "from app import pay\n\n\ndef buy(n):\n    return pay.charge(n)\n")
        self._write(d, "app/test_pay.py",
                    "def test_charge():\n    from app.pay import charge\n"
                    "    assert charge(1) == 1\n")
        self._write(d, "README.md", "# demo\n\nThe money path lives in app/pay.py.\n")
        store = bs.Store(d)
        try:
            rec = store.claim("payments", "persistent", objective="build payments",
                              files=[self.CITED], session_id="sessA")
            store.decide(rec.lifecycle_uuid, rec.version, "provider",
                         "we chose the boring provider on purpose")
            cand = store.capture_learning_candidate(
                "manual", trigger="when touching the money path",
                action="always run the payment tests before committing",
                because="we shipped a double charge once", scope_type="project",
                scope_key="demo", record_uuid=rec.lifecycle_uuid)
            if with_alert:
                store.add_note(kind="alert", severity="critical",
                               body="the retry path double charges",
                               author="Dana, backend", author_kind="human",
                               anchor_type="file", anchor_key=self.CITED,
                               anchor_line=4)
        finally:
            store.close()
        return cand["candidate_uuid"][:8]

    def _run(self, d, *args):
        return subprocess.run([sys.executable, self.PACKS] + list(args),
                              cwd=d, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, universal_newlines=True)

    def _pack_text(self, d):
        directory = os.path.join(d, "Documentation", "30-decisions")
        names = sorted(f for f in os.listdir(directory) if f.endswith(".md"))
        self.assertEqual(len(names), 1, names)
        path = os.path.join(directory, names[0])
        with io.open(path, encoding="utf-8") as fh:
            return path, fh.read()

    def _generate(self, d, cid, *extra):
        r = self._run(d, "pack", cid, "--cite", "%s:4-6" % self.CITED, *extra)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    # -- 4.4, first bullet -------------------------------------------------

    def test_a_pack_carries_all_eight_sections_in_order(self):
        with tempfile.TemporaryDirectory() as d:
            cid = self._project(d)
            self._generate(d, cid)
            _path, text = self._pack_text(d)
            positions = []
            for i, title in enumerate(_PACK_SECTIONS, 1):
                heading = "## %d. %s" % (i, title)
                self.assertIn(heading, text, "missing section %s" % heading)
                positions.append(text.index(heading))
            self.assertEqual(positions, sorted(positions),
                             "the eight sections are out of order")

    def test_every_code_citation_quotes_the_lines_it_claims(self):
        with tempfile.TemporaryDirectory() as d:
            cid = self._project(d)
            self._generate(d, cid)
            _path, text = self._pack_text(d)
            source = self.CITED_SOURCE.split("\n")
            for n in (4, 5, 6):
                self.assertIn("%d  %s" % (n, source[n - 1]), text,
                              "line %d is not quoted as it is on disk" % n)
            self.assertIn("app/pay.py` lines 4 to 6", text)

    def test_the_dependency_map_is_discovered_not_asserted(self):
        with tempfile.TemporaryDirectory() as d:
            cid = self._project(d)
            self._generate(d, cid)
            _path, text = self._pack_text(d)
            self.assertIn("app/checkout.py", text, "the caller was not discovered")
            self.assertIn("app/test_pay.py", text, "the test was not discovered")
            self.assertIn("README.md", text, "the document was not discovered")
            self.assertIn("charge", text,
                          "the symbol defined in the cited lines was not searched")

    def test_the_diagram_is_a_mermaid_flowchart_of_the_affected_path(self):
        with tempfile.TemporaryDirectory() as d:
            cid = self._project(d)
            self._generate(d, cid)
            _path, text = self._pack_text(d)
            self.assertIn("```mermaid", text)
            self.assertIn("flowchart TD", text)
            self.assertIn("app/checkout.py", text.split("```mermaid")[1])

    def test_what_the_store_knows_comes_out_of_the_store(self):
        with tempfile.TemporaryDirectory() as d:
            cid = self._project(d)
            self._generate(d, cid)
            _path, text = self._pack_text(d)
            self.assertIn("boring provider", text,
                          "a prior recorded decision is missing from section 6")

    def test_regeneration_is_byte_identical(self):
        with tempfile.TemporaryDirectory() as d:
            cid = self._project(d)
            self._generate(d, cid)
            _path, first = self._pack_text(d)
            r = self._run(d, "pack", cid)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            _path, second = self._pack_text(d)
            self.assertEqual(first, second,
                             "regeneration churns the file, so every review "
                             "would show a diff that means nothing")

    # -- 4.4, second bullet: I11 calibrated ------------------------------

    def test_calibrated_moving_a_cited_line_fails_generation_loudly(self):
        with tempfile.TemporaryDirectory() as d:
            cid = self._project(d)
            self._generate(d, cid)
            _path, before = self._pack_text(d)
            # REINJECT: one inserted line, which is exactly how a citation goes
            # stale in real life.
            self._write(d, self.CITED, "# a new first line\n" + self.CITED_SOURCE)
            r = self._run(d, "pack", cid)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("citation-moved", r.stderr)
            self.assertIn("def charge(amount):", r.stderr,
                          "the refusal must name the anchor it lost")
            self.assertIn("--recite", r.stderr,
                          "the refusal must name the remedy")
            _path, after = self._pack_text(d)
            self.assertEqual(before, after,
                             "a refused generation must not touch the pack")
            # RESTORE: green again, and the same document.
            self._write(d, self.CITED, self.CITED_SOURCE)
            r = self._run(d, "pack", cid)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_a_body_change_under_a_stable_anchor_is_also_reported(self):
        """The half a line-number check alone would miss: the anchor still
        matches, and the code inside the excerpt is not what was reviewed."""
        with tempfile.TemporaryDirectory() as d:
            cid = self._project(d)
            self._generate(d, cid)
            self._write(d, self.CITED,
                        self.CITED_SOURCE.replace("    return amount",
                                                  "    return amount * 2"))
            r = self._run(d, "pack", cid)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("citation-changed", r.stderr)

    def test_a_citation_past_the_end_of_the_file_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            cid = self._project(d)
            r = self._run(d, "pack", cid, "--cite", "%s:400-410" % self.CITED)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("citation-out-of-range", r.stderr)

    def test_an_anchor_typed_from_memory_fails_on_the_first_generation(self):
        with tempfile.TemporaryDirectory() as d:
            cid = self._project(d)
            r = self._run(d, "pack", cid, "--cite",
                          "%s:4-6@def settle(amount):" % self.CITED)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("citation-moved", r.stderr)

    # -- 4.4, third bullet: alerts with teeth --------------------------

    def test_an_unresolved_critical_alert_is_named_in_the_risks_section(self):
        with tempfile.TemporaryDirectory() as d:
            cid = self._project(d, with_alert=True)
            r = self._generate(d, cid)
            self.assertIn("UNRESOLVED CRITICAL ALERT", r.stdout)
            _path, text = self._pack_text(d)
            self.assertIn("REFUSE the approval", text)
            self.assertIn("Dana, backend", text)
            self.assertIn("the retry path double charges", text)

    def test_stakes_generates_nothing_and_names_the_path_a_pack_would_take(self):
        with tempfile.TemporaryDirectory() as d:
            cid = self._project(d, with_alert=True)
            r = self._run(d, "stakes", cid)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("Documentation/30-decisions/D-1-", r.stdout)
            self.assertIn("UNRESOLVED CRITICAL ALERT", r.stdout)
            self.assertFalse(
                os.path.exists(os.path.join(d, "Documentation")),
                "stakes must generate nothing: the pack is on demand")

    def test_a_recorded_review_lands_in_the_store_and_then_in_the_pack(self):
        with tempfile.TemporaryDirectory() as d:
            cid = self._project(d)
            r = self._run(d, "review", cid, "--by", "Dana, backend",
                          "--verdict", "concerns", "--notes",
                          "read the guard and the fingerprint",
                          "--residual", "no test for the racing case")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            bs = self._bs()
            store = bs.Store(d)
            try:
                rows = store.list_notes(kinds=("review",))
            finally:
                store.close()
            self.assertEqual(len(rows), 1, "the review is not in the store")
            self._generate(d, cid)
            _path, text = self._pack_text(d)
            self.assertIn("Recorded reviews: 1", text)
            self.assertIn("no test for the racing case", text)

    def test_a_review_with_no_name_or_no_notes_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            cid = self._project(d)
            for args in (("--verdict", "approve", "--notes", "looks fine"),
                         ("--by", "Dana", "--verdict", "approve"),
                         ("--by", "Dana", "--verdict", "maybe",
                          "--notes", "looks fine")):
                r = self._run(d, "review", cid, *args)
                self.assertEqual(r.returncode, 2, r.stdout + r.stderr)

    # -- I10 calibrated: human text survives ---------------------------

    HUMAN = "Dana: I still think the retry path is the real risk here."

    def _plant_human(self, path):
        with io.open(path, encoding="utf-8") as fh:
            text = fh.read()
        marker = "<!-- bm-human:begin -->\n<!-- bm-human:end -->"
        self.assertIn(marker, text, "the pack has no empty human block to fill")
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(text.replace(
                marker,
                "<!-- bm-human:begin -->\n%s\n<!-- bm-human:end -->" % self.HUMAN,
                1))

    def test_regeneration_preserves_a_planted_human_block_verbatim(self):
        with tempfile.TemporaryDirectory() as d:
            cid = self._project(d)
            self._generate(d, cid)
            path, _text = self._pack_text(d)
            self._plant_human(path)
            r = self._run(d, "pack", cid)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            _path, text = self._pack_text(d)
            self.assertIn(self.HUMAN, text,
                          "regeneration destroyed human text, which I10 forbids")
            self.assertIn("1 human block(s) preserved", r.stdout)

    def test_calibrated_a_destructive_generator_loses_the_human_block(self):
        """The reinjection that proves the test above is load bearing. A
        generator that ignores the existing file's human blocks is exactly the
        defect I10 names, and this is what it looks like: the planted paragraph
        is gone from the regenerated document."""
        with tempfile.TemporaryDirectory() as d:
            cid = self._project(d)
            self._generate(d, cid)
            path, _text = self._pack_text(d)
            self._plant_human(path)
            spec = importlib.util.spec_from_file_location(
                "bm_packs_destructive", self.PACKS)
            bp = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(bp)
            original = bp.read_existing

            def _destructive(p):
                out = original(p)
                out["human"] = []
                return out

            bp.read_existing = _destructive
            cwd = os.getcwd()
            os.chdir(d)
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(bp.main(["pack", cid]), 0)
            finally:
                os.chdir(cwd)
                bp.read_existing = original
            _path, text = self._pack_text(d)
            self.assertNotIn(
                self.HUMAN, text,
                "the destructive variant did NOT lose the human block, so the "
                "preservation test above proves nothing")

    # -- FIX ROUND: the two ways generation still destroyed or obeyed
    # -- human text -----------------------------------------------------

    # Ordinary review prose that the SECRET SCRUBBER rewrites. This is not a
    # credential; it is how an engineer writes a handover note, and
    # bm_telemetry.redact turns "password: ask" into "[REDACTED] ".
    REDACTABLE_HUMAN = ("Dana: the DB password: ask Sam before you touch the "
                        "migration.")

    def _plant_human_text(self, path, body):
        with io.open(path, encoding="utf-8") as fh:
            text = fh.read()
        marker = "<!-- bm-human:begin -->\n<!-- bm-human:end -->"
        self.assertIn(marker, text, "the pack has no empty human block to fill")
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(text.replace(
                marker,
                "<!-- bm-human:begin -->\n%s\n<!-- bm-human:end -->" % body, 1))

    def test_regeneration_keeps_human_prose_the_redactor_would_rewrite(self):
        """THE DEFECT THIS FIXES. The pack is written through the file funnel,
        which ran the secret scrubber over the WHOLE document including the
        reinjected human blocks. The scrubber is pattern based, so a reviewer's
        sentence came back as 'the DB [REDACTED] Sam', with no warning, no copy
        anywhere, and '1 human block(s) preserved' on stdout. Convergent after
        one pass, so a later diff showed nothing."""
        with tempfile.TemporaryDirectory() as d:
            cid = self._project(d)
            self._generate(d, cid)
            path, _text = self._pack_text(d)
            self._plant_human_text(path, self.REDACTABLE_HUMAN)
            r = self._run(d, "pack", cid)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            _p, text = self._pack_text(d)
            self.assertIn(self.REDACTABLE_HUMAN, text,
                          "the funnel rewrote human prose, which I10 forbids")
            self.assertNotIn("REDACTED", text)
            self.assertIn("KEPT VERBATIM AND WORTH READING", r.stdout,
                          "preserving it silently is not enough: the founder has "
                          "to be told what it looks like")

    def test_calibrated_a_funnel_that_redacts_everything_eats_the_paragraph(self):
        """The reinjection for the test above: put whole-text redaction back and
        the reviewer's sentence is destroyed on disk."""
        with tempfile.TemporaryDirectory() as d:
            cid = self._project(d)
            self._generate(d, cid)
            path, _text = self._pack_text(d)
            self._plant_human_text(path, self.REDACTABLE_HUMAN)
            bs = self._bs()
            spec = importlib.util.spec_from_file_location(
                "bm_packs_whole_text_redact", self.PACKS)
            bp = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(bp)
            original = bp.bs._redact_outside_human_blocks
            bp.bs._redact_outside_human_blocks = (
                lambda text: bp.bs.redact_text(text or ""))
            cwd = os.getcwd()
            os.chdir(d)
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(bp.main(["pack", cid]), 0)
            finally:
                os.chdir(cwd)
                bp.bs._redact_outside_human_blocks = original
            _p, text = self._pack_text(d)
            self.assertNotIn(
                self.REDACTABLE_HUMAN, text,
                "the reinjected whole-text redaction did NOT eat the paragraph, "
                "so the test above proves nothing")
            self.assertIn("REDACTED", text)
            self.assertTrue(bs.human_block_secret_hits(text) is not None)

    CITE_IN_PROSE = ('<!-- bm-cite: path=README.md lines=1-1 sha256=%s '
                     'anchor="# demo" -->' % ("0" * 64))

    def test_a_citation_pasted_into_a_human_block_is_prose_not_configuration(self):
        """A reviewer quoting an excerpt header in the block the file TELLS them
        to write in used to add a citation to the pack. A non-resolving one
        wedged every future regeneration at exit 2, and the remedy the refusal
        printed did not work, so the only way out was editing the human block
        I10 says must be preserved. Reviewers quote code; that has to be safe."""
        with tempfile.TemporaryDirectory() as d:
            cid = self._project(d)
            self._generate(d, cid)
            path, before = self._pack_text(d)
            citations_before = before.count("<!-- bm-cite:")
            self._plant_human_text(
                path, "%s\n%s" % (self.CITE_IN_PROSE, self.HUMAN))
            r = self._run(d, "pack", cid)
            self.assertEqual(r.returncode, 0,
                             "prose wedged generation: %s" % (r.stdout + r.stderr))
            _p, after = self._pack_text(d)
            self.assertIn(self.HUMAN, after)
            self.assertIn(self.CITE_IN_PROSE, after,
                          "the pasted line is human text and stays verbatim")
            self.assertEqual(after.count("<!-- bm-cite:"),
                             citations_before + 1,
                             "a citation was adopted out of human prose")
            self.assertNotIn("README.md` lines 1 to 1", after,
                             "human prose produced a generated code excerpt")
            r2 = self._run(d, "pack", cid)
            self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)
            _p, again = self._pack_text(d)
            self.assertEqual(after, again, "regeneration is no longer idempotent")

    def test_calibrated_the_old_whole_file_scan_adopts_the_pasted_citation(self):
        """The reinjection: scan every line for a citation, as read_existing used
        to, and the pasted prose wedges the pack at exit 2."""
        with tempfile.TemporaryDirectory() as d:
            cid = self._project(d)
            self._generate(d, cid)
            path, _text = self._pack_text(d)
            self._plant_human_text(
                path, "%s\n%s" % (self.CITE_IN_PROSE, self.HUMAN))
            spec = importlib.util.spec_from_file_location(
                "bm_packs_whole_file_cite_scan", self.PACKS)
            bp = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(bp)
            original = bp.read_existing

            def _whole_file_scan(p):
                out = original(p)
                with io.open(p, encoding="utf-8") as fh:
                    for line in fh.read().split("\n"):
                        m = bp._CITE_RE.match(line.strip())
                        if m:
                            out["cites"].append({
                                "path": m.group("path"),
                                "start": int(m.group("start")),
                                "end": int(m.group("end")),
                                "sha": m.group("sha"),
                                "anchor": bp._unquote_anchor(m.group("anchor"))})
                return out

            bp.read_existing = _whole_file_scan
            cwd = os.getcwd()
            os.chdir(d)
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    with contextlib.redirect_stderr(io.StringIO()) as err:
                        code = bp.main(["pack", cid])
            finally:
                os.chdir(cwd)
                bp.read_existing = original
            self.assertEqual(code, 2,
                             "the reinjected whole-file scan did NOT adopt the "
                             "pasted citation, so the test above proves nothing")
            self.assertIn("refused (citation-", err.getvalue())

    def test_a_stray_begin_marker_inside_a_block_keeps_the_paragraph(self):
        """The old marker scan reset its buffer on a second begin marker, so
        everything written before it was dropped: a human block eaten by a line
        the human typed."""
        with tempfile.TemporaryDirectory() as d:
            cid = self._project(d)
            self._generate(d, cid)
            path, _text = self._pack_text(d)
            self._plant_human_text(
                path, "%s\n<!-- bm-human:begin -->\nDana, still here." % self.HUMAN)
            r = self._run(d, "pack", cid)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            _p, text = self._pack_text(d)
            self.assertIn(self.HUMAN, text,
                          "a stray begin marker ate the paragraph above it")
            self.assertIn("Dana, still here.", text)

    def test_the_recite_remedy_the_refusal_prints_actually_works(self):
        """I11 promises a loud refusal with a stated remedy. The remedy has to
        work: merge_citations indexed recorded rows by key but appended every
        one, and the recite loop replaced the first row matching the PATH and
        stopped, so a pack citing two ranges of one file could not be recited at
        all."""
        with tempfile.TemporaryDirectory() as d:
            cid = self._project(d)
            self._generate(d, cid)
            r = self._run(d, "pack", cid, "--cite", "%s:9-10" % self.CITED)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            source = os.path.join(d, *self.CITED.split("/"))
            with io.open(source, encoding="utf-8") as fh:
                moved = fh.read().replace("    return -amount",
                                          "    return 0 - amount")
            with io.open(source, "w", encoding="utf-8") as fh:
                fh.write(moved)
            r = self._run(d, "pack", cid)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("--recite", r.stderr)
            remedy = r.stderr.split("--recite ", 1)[1].split(" to record")[0]
            r = self._run(d, "pack", cid, "--recite", remedy)
            self.assertEqual(r.returncode, 0,
                             "the printed remedy did not work: %s"
                             % (r.stdout + r.stderr))
            _p, text = self._pack_text(d)
            self.assertIn("lines 4 to 6", text,
                          "reciting one range dropped the other citation")
            self.assertIn("lines 9 to 10", text)

    def test_two_recorded_rows_for_one_range_collapse_to_one(self):
        """The unit-level statement of the same defect, on the function itself."""
        spec = importlib.util.spec_from_file_location(
            "bm_packs_merge", self.PACKS)
        bp = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bp)
        twin = {"path": "a.py", "start": 1, "end": 1, "sha": "0" * 64,
                "anchor": "x"}
        merged = bp.merge_citations([dict(twin), dict(twin)], [], [])
        self.assertEqual(len(merged), 1)
        recited = bp.merge_citations(
            [dict(twin), dict(twin)], [],
            [{"path": "a.py", "start": 1, "end": 1, "sha": "", "anchor": "x"}])
        self.assertEqual([c["sha"] for c in recited], [""],
                         "a recite left a stale twin behind, which is what "
                         "wedged the pack forever")

    def test_the_generated_pack_carries_no_em_or_en_dash(self):
        with tempfile.TemporaryDirectory() as d:
            cid = self._project(d, with_alert=True)
            self._generate(d, cid)
            _path, text = self._pack_text(d)
            for i, line in enumerate(text.split("\n"), 1):
                for label, ch in (("en", chr(0x2013)), ("em", chr(0x2014))):
                    self.assertNotIn(ch, line,
                                     "%s dash on line %d of the pack" % (label, i))


class TestDocumentationEngine(unittest.TestCase):
    """Phase B of docs/superpowers/specs/2026-07-30-documentation-and-gate-packs
    -design.md, section 5.7. Extends this suite rather than adding one, per
    section 8: test_all.py refuses an unregistered suite.

    Every folder here is generated by the real CLI against a real store in a
    throwaway directory. Nothing touches this repository's own files.
    """

    DOCS = os.path.join(HERE, "bm_docs.py")
    EXPORT = os.path.join(HERE, "bm_docs_export.py")

    # -- fixtures ----------------------------------------------------------

    def _mod(self, name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def _bs(self):
        return self._mod("bm_store_for_docs_tests", os.path.join(HERE, "bm_store.py"))

    def _bd(self, name="bm_docs_for_docs_tests"):
        return self._mod(name, self.DOCS)

    def _write(self, root, rel, text):
        full = os.path.join(root, *rel.split("/"))
        parent = os.path.dirname(full)
        if parent and not os.path.isdir(parent):
            os.makedirs(parent)
        with io.open(full, "w", encoding="utf-8") as fh:
            fh.write(text)
        return full

    def _project(self, d, records=1, candidates=0, risk=False, second_owner=False):
        """A real store, real source files, and as much recorded work as the
        caller asked for. Every row goes in through bm_store, which is the only
        writer, exactly as a founder's would."""
        bs = self._bs()
        self._write(d, "app/pay.py",
                    '"""the money path"""\nimport json\n\n\ndef charge(n):\n'
                    "    return n\n")
        self._write(d, "app/checkout.py",
                    '"""checkout"""\nfrom app import pay\n\n\ndef buy(n):\n'
                    "    return pay.charge(n)\n")
        self._write(d, "app/test_pay.py",
                    "def test_charge():\n    from app.pay import charge\n"
                    "    assert charge(1) == 1\n")
        self._write(d, "tools/test_all.py", "# the gate\n")
        store = bs.Store(d)
        try:
            first = store.claim("payments", "persistent",
                                objective="build the money path",
                                files=["app/pay.py"], owner="Dana",
                                session_id="sessA")
            store.decide(first.lifecycle_uuid, first.version, "provider",
                         "we chose the boring provider on purpose")
            if records > 1:
                # The store REFUSES a close with no evidence, which is the
                # point of it, so the fixture supplies some rather than
                # working around the guard.
                live = store.get(first.lifecycle_uuid)
                store.transition(first.lifecycle_uuid, live.version,
                                 "complete", session_id="sessA",
                                 evidence="the payment tests passed")
                second = store.claim(
                    "refunds", "persistent", objective="build refunds",
                    files=["app/pay.py", "app/checkout.py"],
                    owner="Sam" if second_owner else "Dana", session_id="sessB")
                store.checkpoint(second.lifecycle_uuid, second.version,
                                 "wire the webhook", blockers="waiting on keys")
            for i in range(candidates):
                store.capture_learning_candidate(
                    "manual", trigger="when touching the money path %d" % i,
                    action="always run the payment tests before committing %d" % i,
                    because="we shipped a double charge once", scope_type="project",
                    scope_key="demo", record_uuid=first.lifecycle_uuid)
            if risk:
                store.add_note(kind="risk", severity="critical",
                               body="the retry path double charges",
                               author="Dana, backend", author_kind="human",
                               anchor_type="file", anchor_key="app/pay.py",
                               anchor_line=5)
        finally:
            store.close()
        return d

    def _run(self, d, *args):
        return subprocess.run([sys.executable, self.DOCS] + list(args), cwd=d,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True)

    def _generate(self, d, *extra):
        r = self._run(d, "generate", *extra)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def _read_doc(self, d, rel):
        with io.open(os.path.join(d, "Documentation", *rel.split("/")),
                     encoding="utf-8") as fh:
            return fh.read()

    def _tree(self, d):
        """Every generated file with its bytes, for a byte-identity comparison."""
        out = {}
        base = os.path.join(d, "Documentation")
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = sorted(dirnames)
            for name in sorted(filenames):
                full = os.path.join(dirpath, name)
                with io.open(full, "rb") as fh:
                    out[os.path.relpath(full, base)] = fh.read()
        return out

    # -- 5.1 layout --------------------------------------------------------

    def test_the_layout_is_the_numbered_one_the_spec_names(self):
        with tempfile.TemporaryDirectory() as d:
            self._project(d)
            self._generate(d, "--tier", "3")
            bd = self._bd()
            for rel, _tier, _what in bd.FILES:
                self.assertTrue(
                    os.path.isfile(os.path.join(d, "Documentation",
                                                *rel.split("/"))),
                    "tier 3 did not write %s" % rel)
            dirs = sorted(x for x in os.listdir(os.path.join(d, "Documentation"))
                          if os.path.isdir(os.path.join(d, "Documentation", x)))
            self.assertEqual(
                ["10-business", "20-technical", "30-decisions", "40-handover",
                 "90-generated"], dirs)

    def test_reading_order_follows_the_numbers_not_the_tier(self):
        """The numbered directories exist so a stranger reads top to bottom. A
        list sorted by tier would send them 00, 30, 40, then back to 10, which
        is exactly what the numbering is for. Within one directory the order is
        curated (architecture before its data model before its diagrams) and
        START-HERE prints it, so only the directory numbers are asserted."""
        bd = self._bd()
        numbers = []
        for rel, _tier, _what in bd.FILES:
            head = rel.split("/")[0]
            numbers.append(int(head[:2]))
        self.assertEqual(numbers, sorted(numbers),
                         "FILES leaves and re-enters a numbered directory: %s"
                         % [rel for rel, _t, _w in bd.FILES])

    # -- 5.2 projection ----------------------------------------------------

    def test_the_work_breakdown_is_projected_from_the_records(self):
        with tempfile.TemporaryDirectory() as d:
            self._project(d, records=2)
            self._generate(d, "--tier", "3")
            wbs = self._read_doc(d, "10-business/WBS.md")
            self.assertIn("payments", wbs)
            self.assertIn("refunds", wbs)
            self.assertIn("build the money path", wbs)
            self.assertIn("we chose the boring provider on purpose", wbs)
            self.assertIn("wire the webhook", wbs)

    def test_the_schedule_carries_a_gantt_and_a_derived_dependency(self):
        with tempfile.TemporaryDirectory() as d:
            self._project(d, records=2)
            self._generate(d, "--tier", "3")
            sched = self._read_doc(d, "10-business/SCHEDULE.md")
            self.assertIn("```mermaid", sched)
            self.assertIn("gantt", sched)
            self.assertIn("dateFormat YYYY-MM-DD", sched)
            self.assertIn("must precede", sched,
                          "two records claim app/pay.py, so an edge must exist")
            self.assertIn("## Critical path", sched)

    def test_the_decision_index_lists_candidates_and_their_lineage(self):
        with tempfile.TemporaryDirectory() as d:
            self._project(d, candidates=2, risk=True)
            self._generate(d, "--tier", "3")
            index = self._read_doc(d, "30-decisions/INDEX.md")
            self.assertIn("always run the payment tests before committing 0",
                          index)
            self.assertIn("## Lineage", index)
            self.assertIn("the retry path double charges", index,
                          "a note must be rendered at its anchor")
            self.assertIn("Dana, backend", index,
                          "a note must carry its author")

    def test_the_data_model_is_introspected_from_the_live_schema(self):
        with tempfile.TemporaryDirectory() as d:
            self._project(d)
            self._generate(d, "--tier", "3")
            model = self._read_doc(d, "20-technical/DATA-MODEL.md")
            self.assertIn("erDiagram", model)
            for table in ("records", "claims", "decisions", "notes",
                          "learning_candidates"):
                self.assertIn("### `%s`" % table, model,
                              "%s is in the schema but not in the diagram"
                              % table)
            self.assertIn("points at `records.lifecycle_uuid`", model,
                          "a foreign key the schema declares is not drawn")

    def test_the_dependency_graph_comes_from_the_imports(self):
        with tempfile.TemporaryDirectory() as d:
            self._project(d)
            self._generate(d, "--tier", "3")
            deps = self._read_doc(d, "20-technical/DEPENDENCIES.md")
            self.assertIn("`app/checkout.py` imports `app/pay.py`", deps)
            self.assertIn("flowchart LR", deps)

    def test_the_code_map_inventories_modules_and_tests(self):
        with tempfile.TemporaryDirectory() as d:
            self._project(d)
            self._generate(d, "--tier", "3")
            code_map = self._read_doc(d, "20-technical/CODE-MAP.md")
            self.assertIn("### `app/pay.py`", code_map)
            self.assertIn("`app/test_pay.py`: 1 test(s)", code_map)

    # -- 5.7 critical path correctness on a known graph ---------------------

    def test_the_critical_path_matches_a_hand_computed_one(self):
        """A graph with a hand-computed answer.

            a(3) -> b(1) -> d(2)
            a(3) -> c(9) -> d(2)

        By hand: a,b,d is 3+1+2 = 6 and a,c,d is 3+9+2 = 14, so the critical
        path is a,c,d at 14. A longest path that took the first branch it found,
        or that summed edges instead of node durations, would answer 6."""
        bd = self._bd()
        weights = {"a": 3, "b": 1, "c": 9, "d": 2}
        edges = [("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")]
        path, total = bd.critical_path(weights, edges)
        self.assertEqual(["a", "c", "d"], path)
        self.assertEqual(14, total)

    def test_the_critical_path_of_an_unconnected_graph_is_the_heaviest_node(self):
        bd = self._bd()
        path, total = bd.critical_path({"a": 2, "b": 7}, [])
        self.assertEqual((["b"], 7), (path, total))

    def test_a_cycle_refuses_rather_than_publishing_a_shorter_path(self):
        bd = self._bd()
        with self.assertRaises(bd.DocsError) as ctx:
            bd.critical_path({"a": 1, "b": 1}, [("a", "b"), ("b", "a")])
        self.assertEqual("schedule-cycle", ctx.exception.reason)
        self.assertIn("cycle", str(ctx.exception))

    def test_the_critical_path_is_stable_across_equal_weights(self):
        """Determinism reaches into the graph too: two runs over the same graph
        must pick the same winner, or SCHEDULE.md churns on every generation."""
        bd = self._bd()
        weights = dict((c, 1) for c in "abcdef")
        edges = [("a", "b"), ("c", "d"), ("e", "f")]
        first = bd.critical_path(weights, edges)
        second = bd.critical_path(weights, list(reversed(edges)))
        self.assertEqual(first, second)

    # -- 5.7 determinism ---------------------------------------------------

    def test_two_regenerations_in_a_row_are_byte_identical(self):
        with tempfile.TemporaryDirectory() as d:
            self._project(d, records=2, candidates=2, risk=True)
            self._generate(d, "--tier", "3")
            before = self._tree(d)
            self._generate(d, "--tier", "3")
            after = self._tree(d)
            self.assertEqual(sorted(before), sorted(after))
            changed = [k for k in before if before[k] != after[k]]
            self.assertEqual([], changed,
                             "regeneration churned these files: %s" % changed)

    def test_regeneration_is_identical_even_when_the_clock_moves(self):
        """The byte-identity test above cannot see a clock read on its own.

        MEASURED, not assumed: a `bs.now_iso()` reinjected into a document body
        passed that test, because two regenerations inside one test run land in
        the same second and the store's timestamps have second precision. So the
        clock is MOVED between the two runs here, in process, and any generation
        time read at all becomes a diff. This is the test that actually holds the
        determinism claim up."""
        with tempfile.TemporaryDirectory() as d:
            self._project(d, records=2, candidates=2, risk=True)
            self._generate(d, "--tier", "3")
            before = self._tree(d)
            bd = self._bd("bm_docs_clock_moved")
            original = bd.bs.now_iso
            bd.bs.now_iso = lambda: "2031-12-25T13:14:15Z"
            cwd = os.getcwd()
            os.chdir(d)
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(bd.main(["generate", "--tier", "3"]), 0)
            finally:
                os.chdir(cwd)
                bd.bs.now_iso = original
            after = self._tree(d)
            changed = [k for k in sorted(before) if before[k] != after[k]]
            self.assertEqual(
                [], changed,
                "moving the clock changed these files, so a generation "
                "timestamp reached a document body: %s" % changed)
            for rel in sorted(after):
                self.assertNotIn(b"2031-12-25", after[rel],
                                 "%s carries the generation clock" % rel)

    def test_no_generated_body_carries_a_generation_timestamp(self):
        """The reason determinism holds. A "generated at" line is the one field
        that guarantees a diff on every run, and it is the first thing anybody
        adds back."""
        with tempfile.TemporaryDirectory() as d:
            self._project(d)
            self._generate(d, "--tier", "3")
            for rel in sorted(self._tree(d)):
                if rel.endswith(".json"):
                    continue
                text = self._read_doc(d, rel.replace(os.sep, "/"))
                for line in text.split("\n"):
                    low = line.lower()
                    self.assertNotIn("generated at", low,
                                     "%s carries a generation timestamp" % rel)
                    self.assertNotIn("generated on", low,
                                     "%s carries a generation timestamp" % rel)

    # -- I10: human text survives -----------------------------------------

    HUMAN = "Dana: I still think the retry path is the real risk here."

    def _plant_human(self, d, rel, body=None):
        path = os.path.join(d, "Documentation", *rel.split("/"))
        with io.open(path, encoding="utf-8") as fh:
            text = fh.read()
        marker = "<!-- bm-human:begin -->\n<!-- bm-human:end -->"
        self.assertIn(marker, text, "%s has no empty human block to fill" % rel)
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(text.replace(
                marker,
                "<!-- bm-human:begin -->\n%s\n<!-- bm-human:end -->"
                % (body if body is not None else self.HUMAN), 1))

    def test_regeneration_preserves_a_planted_human_block_in_every_document(self):
        with tempfile.TemporaryDirectory() as d:
            self._project(d, records=2, candidates=2)
            self._generate(d, "--tier", "3")
            pages = [rel.replace(os.sep, "/") for rel in sorted(self._tree(d))
                     if rel.endswith(".md")]
            self.assertTrue(pages)
            for rel in pages:
                self._plant_human(d, rel)
            r = self._generate(d, "--tier", "3")
            for rel in pages:
                self.assertIn(self.HUMAN, self._read_doc(d, rel),
                              "regeneration destroyed human text in %s, which "
                              "I10 forbids" % rel)
            self.assertIn("%d human block(s) preserved verbatim" % len(pages),
                          r.stdout)

    def test_calibrated_a_destructive_generator_loses_the_human_block(self):
        """The reinjection that proves the test above is load bearing. A
        generator that ignores the existing file's human blocks is exactly the
        defect I10 names, and this is what it looks like: the planted paragraph
        is gone from the regenerated document."""
        with tempfile.TemporaryDirectory() as d:
            self._project(d)
            self._generate(d, "--tier", "3")
            self._plant_human(d, "40-handover/HANDOVER.md")
            bd = self._bd("bm_docs_destructive")
            original = bd.read_existing

            def _destructive(path):
                out = original(path)
                out["human"] = []
                return out

            bd.read_existing = _destructive
            cwd = os.getcwd()
            os.chdir(d)
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(bd.main(["generate", "--tier", "3"]), 0)
            finally:
                os.chdir(cwd)
                bd.read_existing = original
            self.assertNotIn(
                self.HUMAN, self._read_doc(d, "40-handover/HANDOVER.md"),
                "the destructive variant did NOT lose the human block, so the "
                "preservation test above proves nothing")

    REDACTABLE_HUMAN = ("Dana: the DB password: ask Sam before you touch the "
                        "migration.")

    def test_regeneration_keeps_human_prose_the_redactor_would_rewrite(self):
        """The secret scrubber is pattern based, so ordinary handover prose comes
        back mangled if it is run over a human block. The funnel exempts those
        blocks and reports them instead."""
        with tempfile.TemporaryDirectory() as d:
            self._project(d)
            self._generate(d, "--tier", "3")
            self._plant_human(d, "40-handover/HANDOVER.md",
                              body=self.REDACTABLE_HUMAN)
            r = self._generate(d, "--tier", "3")
            self.assertIn(self.REDACTABLE_HUMAN,
                          self._read_doc(d, "40-handover/HANDOVER.md"),
                          "the redactor rewrote a human paragraph")
            self.assertIn("KEPT VERBATIM AND WORTH READING", r.stdout,
                          "the founder was not told their paragraph looks "
                          "secret shaped")

    def test_a_prose_marker_pasted_into_a_human_block_is_prose(self):
        """A reviewer quoting a generated header inside the block the file tells
        them to write in must not thereby reconfigure the cache."""
        with tempfile.TemporaryDirectory() as d:
            self._project(d)
            self._generate(d, "--tier", "3")
            forged = ("Quoting what I saw: <!-- bm-prose: id=handover-what "
                      "sha256=%s -->\nthis is my own paragraph" % ("0" * 64))
            self._plant_human(d, "40-handover/HANDOVER.md", body=forged)
            self._generate(d, "--tier", "3")
            text = self._read_doc(d, "40-handover/HANDOVER.md")
            self.assertIn("this is my own paragraph", text)
            self.assertIn("Quoting what I saw", text)
            self.assertNotIn("sha256=%s" % ("0" * 64),
                             text.split("<!-- bm-human:begin -->")[0],
                             "a pasted marker was adopted as a cache record")

    def test_a_store_field_containing_the_marker_cannot_forge_a_human_block(self):
        """PROBED against a real store before it was believed either way.

        A founder objective holding the literal begin marker would, if a marker
        were matched anywhere in a line, open a fake human block: everything
        after it in the document would be exempt from redaction and would be
        carried through the next regeneration as somebody's prose. It cannot,
        for two reasons that are worth writing down because both must hold. The
        marker is matched only as a WHOLE stripped line, and every store field
        reaches a page through bm_learning.safe_display, which escapes the
        newline a field would need to start a line of its own."""
        with tempfile.TemporaryDirectory() as d:
            bs = self._bs()
            self._project(d)
            store = bs.Store(d)
            try:
                store.claim("sneaky", "persistent",
                            objective="ordinary text <!-- bm-human:begin --> "
                                      "and now I am inside a human block",
                            files=["app/ledger.py"], owner="X",
                            session_id="sessC")
            finally:
                store.close()
            self._generate(d, "--tier", "3")
            bd = self._bd()
            path = os.path.join(d, "Documentation", "10-business", "WBS.md")
            parsed = bd.read_existing(path)
            self.assertEqual(
                [""], parsed["human"],
                "a store field forged a human block: %r" % parsed["human"])
            self.assertIn("and now I am inside a human block",
                          self._read_doc(d, "10-business/WBS.md"),
                          "the objective was silently dropped instead of being "
                          "rendered as the text it is")

    # -- I12: prose is cached against facts --------------------------------

    def _prose_body(self, d, rel, pid):
        bd = self._bd()
        path = os.path.join(d, "Documentation", *rel.split("/"))
        return bd.read_existing(path)["prose"][pid]

    def _rerecord_prose_body(self, d, rel, pid, body):
        """Replace one narrative block's text AND its recorded body checksum, the
        way a legitimate re-record looks.

        A body edit ALONE is a cache miss now (a paragraph must match its own
        checksum or it is written again from the facts), so a reuse test that
        planted text without re-recording would only ever prove the integrity
        check fires. The checksum is recomputed with the engine's own helper
        rather than a second copy of the hashing rule."""
        bd = self._bd()
        path = os.path.join(d, "Documentation", *rel.split("/"))
        with io.open(path, encoding="utf-8") as fh:
            text = fh.read()
        pattern = re.compile(
            r"(<!-- bm-prose: id=%s sha256=[0-9a-f]{64}) body=[0-9a-f]{64}"
            r"( -->\n)(.*?)(\n<!-- bm-prose:end -->)" % re.escape(pid), re.S)
        m = pattern.search(text)
        self.assertIsNotNone(m, "no narrative block %s in %s" % (pid, rel))
        replacement = "%s body=%s%s%s%s" % (m.group(1), bd._body_hash(body),
                                            m.group(2), body, m.group(4))
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(text[:m.start()] + replacement + text[m.end():])
        return path

    def test_unchanged_facts_do_not_regenerate_a_narrative_block(self):
        with tempfile.TemporaryDirectory() as d:
            self._project(d, records=2, candidates=2)
            self._generate(d, "--tier", "3")
            r = self._run(d, "generate", "--tier", "3", "--json")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            report = json.loads(r.stdout)
            self.assertGreater(report["prose_reused"], 0)
            self.assertEqual(
                0, report["prose_regenerated"],
                "nothing about the facts moved, so no block should have been "
                "written again")

    def test_a_reused_block_is_the_recorded_body_not_a_fresh_one(self):
        """The decisive form of the claim. The body on disk is REPLACED and its
        checksum re-recorded, the facts are left alone, and the replacement must
        survive: a generator that rewrote the paragraph and happened to produce
        the same bytes would pass a counter test and fail this one."""
        with tempfile.TemporaryDirectory() as d:
            self._project(d)
            self._generate(d, "--tier", "3")
            rel = "40-handover/HANDOVER.md"
            before = self._prose_body(d, rel, "handover-what")
            self._rerecord_prose_body(d, rel, "handover-what",
                                      "MARKED: this body was not rewritten.")
            self._generate(d, "--tier", "3")
            after = self._prose_body(d, rel, "handover-what")
            self.assertEqual("MARKED: this body was not rewritten.",
                             after["body"])
            self.assertEqual(before["sha"], after["sha"])

    def test_a_changed_fact_does_regenerate_the_block(self):
        """The other half of I12. A cache that never refreshes is not a cache,
        it is a stale page, so the hash has to actually move something."""
        with tempfile.TemporaryDirectory() as d:
            self._project(d)
            self._generate(d, "--tier", "3")
            rel = "40-handover/HANDOVER.md"
            before = self._prose_body(d, rel, "handover-what")
            # Re-recorded, so the ONLY reason this block can be written again is
            # the fact that moves below.
            self._rerecord_prose_body(d, rel, "handover-what", "MARKED: stale.")
            # A new module changes the module count, which the handover
            # narrative describes, so its fact hash must move.
            self._write(d, "app/ledger.py", '"""the ledger"""\n\n\ndef post():\n'
                                            "    return 1\n")
            r = self._run(d, "generate", "--tier", "3", "--json")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertGreater(json.loads(r.stdout)["prose_regenerated"], 0)
            after = self._prose_body(d, rel, "handover-what")
            self.assertNotEqual(before["sha"], after["sha"],
                                "the fact hash did not move when a fact moved")
            self.assertNotIn("MARKED: stale.", after["body"])

    def test_calibrated_a_cache_that_ignores_the_hash_rewrites_everything(self):
        """The reinjection for the two tests above. A `prose` that always calls
        its writer is the defect I12 names: the edited body is gone, and the
        cost the cache exists to avoid is paid on every single run."""
        with tempfile.TemporaryDirectory() as d:
            self._project(d)
            self._generate(d, "--tier", "3")
            rel = "40-handover/HANDOVER.md"
            self._rerecord_prose_body(d, rel, "handover-what",
                                      "MARKED: this body was not rewritten.")
            bd = self._bd("bm_docs_uncached")

            def _always(self_, pid, keys, writer):
                sha = self_.fact_hash(keys)
                self_.regenerated += 1
                body = writer()
                return (["<!-- bm-prose: id=%s sha256=%s body=%s -->"
                         % (pid, sha, bd._body_hash(body))]
                        + body.split("\n") + [bd._PROSE_CLOSE])

            original = bd.Generator.prose
            bd.Generator.prose = _always
            cwd = os.getcwd()
            os.chdir(d)
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(bd.main(["generate", "--tier", "3"]), 0)
            finally:
                os.chdir(cwd)
                bd.Generator.prose = original
            after = self._prose_body(d, rel, "handover-what")
            self.assertNotEqual(
                "MARKED: this body was not rewritten.", after["body"],
                "the uncached variant did NOT rewrite the body, so the reuse "
                "tests above prove nothing")

    FALSE_SENTENCE = ("This project is fully audited and has no open risks. "
                      "Ship it.")

    def _plant_false_prose(self, d, rel, pid):
        """Swap a generated paragraph's text and leave the recorded checksums
        alone, which is what a bad merge, a stale copy or a hand edit looks
        like."""
        bd = self._bd()
        path = os.path.join(d, "Documentation", *rel.split("/"))
        with io.open(path, encoding="utf-8") as fh:
            text = fh.read()
        pattern = re.compile(
            r"(<!-- bm-prose: id=%s sha256=[0-9a-f]{64} body=[0-9a-f]{64} -->\n)"
            r"(.*?)(\n<!-- bm-prose:end -->)" % re.escape(pid), re.S)
        m = pattern.search(text)
        self.assertIsNotNone(m, "no narrative block %s in %s" % (pid, rel))
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(text[:m.start(2)] + self.FALSE_SENTENCE + text[m.end(2):])
        self.assertEqual(self.FALSE_SENTENCE,
                         bd.read_existing(path)["prose"][pid]["body"],
                         "the plant did not land")
        return path

    def test_a_generated_paragraph_swapped_under_a_valid_fact_hash_is_rewritten(self):
        """THE THIRD DEFECT THIS FIXES. The fact hash covers the FACTS, never the
        prose, so any text at all could be swapped in under a still-valid hash
        and was then reused on every later run for as long as those facts held
        still. The header of that same file, and the RUNBOOK it generates, both
        tell the reader everything outside the human markers is rewritten. So a
        false sentence planted in HANDOVER.md could not be corrected by
        regenerating, which is the integrity half of I12."""
        with tempfile.TemporaryDirectory() as d:
            self._project(d)
            self._generate(d, "--tier", "3")
            rel = "40-handover/HANDOVER.md"
            self._plant_false_prose(d, rel, "handover-what")
            r = self._run(d, "generate", "--tier", "3", "--json")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            report = json.loads(r.stdout)
            self.assertEqual(1, report["prose_rewritten_unverified"],
                             "the swap was not counted")
            self.assertNotIn(self.FALSE_SENTENCE, self._read_doc(d, rel),
                             "a planted sentence survived regeneration while the "
                             "page claims it rewrites everything outside the "
                             "human markers")

    def test_the_founder_is_told_a_block_failed_its_own_checksum(self):
        with tempfile.TemporaryDirectory() as d:
            self._project(d)
            self._generate(d, "--tier", "3")
            self._plant_false_prose(d, "40-handover/HANDOVER.md",
                                    "handover-what")
            r = self._generate(d, "--tier", "3")
            self.assertIn("REWRITTEN FROM THE FACTS", r.stdout,
                          "a paragraph was silently corrected, and a silent "
                          "correction is one nobody reviews")

    def test_a_swap_is_repaired_and_then_stays_repaired(self):
        """The repair converges: the run after the repair reuses again and the
        bytes stop moving, so the integrity check cannot become the churn the
        determinism test forbids."""
        with tempfile.TemporaryDirectory() as d:
            self._project(d)
            self._generate(d, "--tier", "3")
            clean = self._tree(d)
            self._plant_false_prose(d, "40-handover/HANDOVER.md",
                                    "handover-what")
            self._generate(d, "--tier", "3")
            repaired = self._tree(d)
            self.assertEqual(
                [], [k for k in sorted(clean) if clean[k] != repaired[k]],
                "the repair did not restore the bytes the facts produce")
            r = self._run(d, "generate", "--tier", "3", "--json")
            self.assertEqual(0, json.loads(r.stdout)["prose_regenerated"],
                             "the repaired block was written again, so the "
                             "checksum does not agree with what was written")

    def test_calibrated_a_cache_that_trusts_the_fact_hash_alone_keeps_the_swap(self):
        """The reinjection for the three tests above, and it is the old `prose`:
        a record whose FACT hash matches is reused, whatever its text now says."""
        with tempfile.TemporaryDirectory() as d:
            self._project(d)
            self._generate(d, "--tier", "3")
            rel = "40-handover/HANDOVER.md"
            self._plant_false_prose(d, rel, "handover-what")
            bd = self._bd("bm_docs_facts_only_cache")

            def _facts_only(self_, pid, keys, writer):
                sha = self_.fact_hash(keys)
                record = self_.prior["prose"].get(pid)
                if record is not None and record["sha"] == sha:
                    self_.reused += 1
                    body = record["body"]
                else:
                    self_.regenerated += 1
                    body = bd._neutralize_prose_markers(writer())
                return (["<!-- bm-prose: id=%s sha256=%s body=%s -->"
                         % (pid, sha, bd._body_hash(body))]
                        + body.split("\n") + [bd._PROSE_CLOSE])

            original = bd.Generator.prose
            bd.Generator.prose = _facts_only
            cwd = os.getcwd()
            os.chdir(d)
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(bd.main(["generate", "--tier", "3"]), 0)
            finally:
                os.chdir(cwd)
                bd.Generator.prose = original
            self.assertIn(
                self.FALSE_SENTENCE, self._read_doc(d, rel),
                "the fact-hash-only variant did NOT keep the planted sentence, "
                "so the integrity tests above prove nothing")

    def test_a_record_from_before_the_body_checksum_is_rewritten(self):
        """A folder generated by the previous version has no body= field. It must
        heal on the next run rather than be trusted forever."""
        with tempfile.TemporaryDirectory() as d:
            self._project(d)
            self._generate(d, "--tier", "3")
            stripped = 0
            for rel, _tier, _what in self._bd().FILES:
                path = os.path.join(d, "Documentation", *rel.split("/"))
                if not path.endswith(".md"):
                    continue
                with io.open(path, encoding="utf-8") as fh:
                    text = fh.read()
                old = re.sub(r"(<!-- bm-prose: id=[a-z0-9-]+ "
                             r"sha256=[0-9a-f]{64}) body=[0-9a-f]{64}( -->)",
                             r"\1\2", text)
                if old == text:
                    continue
                stripped += 1
                with io.open(path, "w", encoding="utf-8") as fh:
                    fh.write(old)
            self.assertTrue(stripped, "no body checksum to remove anywhere")
            r = self._run(d, "generate", "--tier", "3", "--json")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            report = json.loads(r.stdout)
            self.assertEqual(0, report["prose_reused"],
                             "a record with no body checksum was reused")
            self.assertGreater(report["prose_regenerated"], 0)

    # -- 5.3 tiers, and I13 -----------------------------------------------

    def _tier_json(self, d, *extra):
        r = self._run(d, "tier", "--json", *extra)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return json.loads(r.stdout)

    def test_a_small_project_gets_tier_one_with_the_reason_printed(self):
        with tempfile.TemporaryDirectory() as d:
            self._project(d)
            payload = self._tier_json(d)
            self.assertEqual(1, payload["tier"])
            self.assertEqual("lean", payload["tier_name"])
            self.assertTrue(any("tier 1 because" in reason
                                for reason in payload["tier_reasons"]),
                            payload["tier_reasons"])
            self.assertEqual(
                ["00-START-HERE.md", "30-decisions/INDEX.md",
                 "40-handover/HANDOVER.md", "90-generated/facts.json"],
                sorted(payload["would_emit"]))

    def test_recorded_decisions_raise_it_to_tier_two(self):
        with tempfile.TemporaryDirectory() as d:
            self._project(d, candidates=3)
            payload = self._tier_json(d)
            self.assertEqual(2, payload["tier"])
            self.assertTrue(any("recorded decisions" in reason
                                for reason in payload["tier_reasons"]),
                            payload["tier_reasons"])

    def test_an_open_risk_flag_raises_it_to_tier_three(self):
        with tempfile.TemporaryDirectory() as d:
            self._project(d, candidates=3, risk=True)
            payload = self._tier_json(d)
            self.assertEqual(3, payload["tier"])
            self.assertTrue(any("open risk flag" in reason
                                for reason in payload["tier_reasons"]),
                            payload["tier_reasons"])

    def test_two_contributors_raise_it_to_tier_three(self):
        with tempfile.TemporaryDirectory() as d:
            self._project(d, records=2, second_owner=True)
            payload = self._tier_json(d)
            self.assertEqual(3, payload["tier"])
            self.assertTrue(any("contributors" in reason
                                for reason in payload["tier_reasons"]),
                            payload["tier_reasons"])

    def test_the_tier_and_its_signals_are_written_into_start_here(self):
        with tempfile.TemporaryDirectory() as d:
            self._project(d, candidates=3)
            self._generate(d)
            start = self._read_doc(d, "00-START-HERE.md")
            self.assertIn("**Tier 2 (standard)**", start)
            self.assertIn("recorded decisions", start)
            self.assertIn("| Tracked files |", start)
            self.assertIn("| Recorded gates |", start)

    def test_the_tier_flag_overrides_the_measurement(self):
        with tempfile.TemporaryDirectory() as d:
            self._project(d)
            payload = self._tier_json(d, "--tier", "3")
            self.assertEqual(3, payload["tier"])
            self.assertEqual("explicit --tier", payload["tier_source"])

    def test_a_bad_tier_flag_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            self._project(d)
            r = self._run(d, "generate", "--tier", "9")
            self.assertEqual(2, r.returncode)
            self.assertIn("refused (bad-tier)", r.stderr)
            self.assertFalse(os.path.isdir(os.path.join(d, "Documentation")),
                             "a refused run still wrote something")

    def test_an_automatic_decision_never_lowers_the_tier(self):
        """I13. Depth that quietly got thinner is depth a reader cannot trust to
        still contain what they read last week."""
        with tempfile.TemporaryDirectory() as d:
            self._project(d)
            self._generate(d, "--tier", "3")
            payload = self._tier_json(d)
            self.assertEqual(3, payload["tier"])
            self.assertEqual(3, payload["recorded_floor"])
            self.assertTrue(any("may only raise depth" in reason
                                for reason in payload["tier_reasons"]),
                            payload["tier_reasons"])

    def test_lowering_takes_an_explicit_flag_and_says_so(self):
        """The fixture carries an open risk flag, so the SIGNALS measure tier 3
        and `--tier 1` is genuinely a lowering. The wording compares the flag
        against the measured tier and not against the recorded floor, because the
        floor is what the previous run wrote and comparing against it made two
        identical runs print two different reasons."""
        with tempfile.TemporaryDirectory() as d:
            self._project(d, records=2, candidates=2, risk=True)
            self._generate(d, "--tier", "3")
            r = self._generate(d, "--tier", "1")
            self.assertIn("lowered to tier 1 by an explicit --tier 1", r.stdout)
            self.assertIn("LEFT BEHIND and no longer maintained", r.stdout,
                          "a page a deeper tier wrote was neither maintained "
                          "nor named")
            start = " ".join(self._read_doc(d, "00-START-HERE.md").split())
            self.assertIn("NO LONGER MAINTAINED", start,
                          "START-HERE does not warn about the pages the deeper "
                          "tier left behind")
            self.assertIn("20-technical/WHITEPAPER.md", start)

    def test_a_lowered_tier_deletes_nothing(self):
        """A generator that removed the pages a deeper tier wrote could remove a
        paragraph a human put in one of them. It names them instead."""
        with tempfile.TemporaryDirectory() as d:
            self._project(d)
            self._generate(d, "--tier", "3")
            self._plant_human(d, "20-technical/WHITEPAPER.md")
            self._generate(d, "--tier", "1")
            self.assertIn(self.HUMAN,
                          self._read_doc(d, "20-technical/WHITEPAPER.md"),
                          "lowering the tier destroyed a human block")

    def test_calibrated_without_the_recorded_floor_the_tier_drops(self):
        """The reinjection that proves the raise-only test is load bearing: with
        the floor forgotten, the same project falls from tier 3 back to tier 1."""
        with tempfile.TemporaryDirectory() as d:
            self._project(d)
            self._generate(d, "--tier", "3")
            bd = self._bd("bm_docs_no_floor")
            original = bd.recorded_floor
            bd.recorded_floor = lambda root: 0
            cwd = os.getcwd()
            os.chdir(d)
            captured = io.StringIO()
            try:
                with contextlib.redirect_stdout(captured):
                    self.assertEqual(bd.main(["tier", "--json"]), 0)
            finally:
                os.chdir(cwd)
                bd.recorded_floor = original
            self.assertEqual(
                1, json.loads(captured.getvalue())["tier"],
                "the tier did NOT drop without the floor, so the raise-only "
                "test above proves nothing")

    def test_an_explicit_tier_above_the_measured_one_does_not_churn(self):
        """THE DEFECT THIS FIXES, found by running the real command twice.

        Run one recorded the chosen tier. Run two read it back as a floor, so
        choose_tier appended a "held at tier 3 ... (I13)" reason AND turned
        "raised to tier 3" into "confirmed at tier 3". Both strings are printed
        into START-HERE and facts.json, so the second identical run rewrote two
        files with nothing moved in the store, the code or the flag, which is
        exactly the churn section 5.7 forbids. It converged only on run three, so
        a probe against an already-converged folder saw nothing."""
        with tempfile.TemporaryDirectory() as d:
            self._project(d)
            self.assertEqual(1, self._tier_json(d)["tier"],
                             "the fixture no longer measures tier 1, so --tier 3 "
                             "is no longer above the measured tier")
            self._generate(d, "--tier", "3")
            first = self._tree(d)
            self._generate(d, "--tier", "3")
            second = self._tree(d)
            changed = [k for k in sorted(first) if first[k] != second[k]]
            self.assertEqual(
                [], changed,
                "a second identical `generate --tier 3` churned: %s" % changed)

    def test_calibrated_a_floor_in_the_explicit_path_churns(self):
        """The reinjection that proves the test above is load bearing. This is
        the old choose_tier: the floor is applied first and the explicit flag is
        compared against the held tier rather than against the measured one."""
        with tempfile.TemporaryDirectory() as d:
            self._project(d)
            bd = self._bd("bm_docs_floored_explicit")
            original = bd.choose_tier

            def _floored(sig, floor=0, explicit=None):
                auto = original(sig, floor=floor)
                if explicit is None:
                    return auto
                tier, reasons = auto["tier"], list(auto["reasons"])
                if explicit < tier:
                    reasons.append("lowered to tier %d by an explicit --tier %d"
                                   % (explicit, explicit))
                elif explicit > tier:
                    reasons.append("raised to tier %d by an explicit --tier %d"
                                   % (explicit, explicit))
                else:
                    reasons.append("confirmed at tier %d by an explicit --tier %d"
                                   % (explicit, explicit))
                return {"tier": explicit, "name": bd.TIERS[explicit],
                        "reasons": reasons, "source": "explicit --tier"}

            bd.choose_tier = _floored
            cwd = os.getcwd()
            os.chdir(d)
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(bd.main(["generate", "--tier", "3"]), 0)
                    first = self._tree(d)
                    self.assertEqual(bd.main(["generate", "--tier", "3"]), 0)
            finally:
                os.chdir(cwd)
                bd.choose_tier = original
            second = self._tree(d)
            changed = [k for k in sorted(first) if first[k] != second[k]]
            self.assertNotEqual(
                [], changed,
                "the reinjected floor did NOT churn, so the determinism test "
                "above proves nothing")

    def test_the_recorded_tier_survives_removing_the_generated_folder(self):
        """THE SECOND DEFECT THIS FIXES. The floor lived only in
        Documentation/90-generated/facts.json, the folder is generated output
        that this project's .gitignore excludes, and the RUNBOOK this engine
        writes names `git rm -r Documentation` as the rollback. Following that
        instruction erased the only copy of the floor, so the next AUTOMATIC run
        of a tier 3 project chose tier 1 with no flag passed, which is the
        lowering I13 reserves for an explicit founder flag."""
        with tempfile.TemporaryDirectory() as d:
            self._project(d)
            report = json.loads(self._run(d, "generate", "--tier", "3",
                                          "--json").stdout)
            self.assertEqual(".brothermode/docs-tier.json",
                             report["tier_recorded_at"])
            self.assertIsNone(report["tier_record_error"])
            shutil.rmtree(os.path.join(d, "Documentation"))
            payload = self._tier_json(d)
            self.assertEqual(3, payload["recorded_floor"],
                             "the floor did not survive the documented rollback")
            self.assertEqual(3, payload["tier"])
            self.assertTrue(any("may only raise depth" in reason
                                for reason in payload["tier_reasons"]),
                            payload["tier_reasons"])

    def test_calibrated_a_floor_kept_only_in_the_generated_folder_is_lost(self):
        """The reinjection for the test above, and it is the old code verbatim:
        `_floor_from_generated_facts` is what `recorded_floor` used to be."""
        with tempfile.TemporaryDirectory() as d:
            self._project(d)
            self._generate(d, "--tier", "3")
            shutil.rmtree(os.path.join(d, "Documentation"))
            bd = self._bd("bm_docs_facts_only_floor")
            original = bd.recorded_floor
            bd.recorded_floor = bd._floor_from_generated_facts
            cwd = os.getcwd()
            os.chdir(d)
            captured = io.StringIO()
            try:
                with contextlib.redirect_stdout(captured):
                    self.assertEqual(bd.main(["tier", "--json"]), 0)
            finally:
                os.chdir(cwd)
                bd.recorded_floor = original
            self.assertEqual(
                1, json.loads(captured.getvalue())["tier"],
                "the facts-only floor did NOT lose the tier, so the survival "
                "test above proves nothing")

    def test_a_damaged_tier_record_does_not_stop_a_generation(self):
        """A floor that cannot be read must cost depth, never the command. The
        signals still answer, and the run still writes."""
        with tempfile.TemporaryDirectory() as d:
            self._project(d)
            self._generate(d, "--tier", "3")
            with io.open(os.path.join(d, ".brothermode", "docs-tier.json"), "w",
                         encoding="utf-8") as fh:
                fh.write("{not json at all")
            shutil.rmtree(os.path.join(d, "Documentation"))
            payload = self._tier_json(d)
            self.assertEqual(0, payload["recorded_floor"])
            self.assertEqual(1, payload["tier"])
            self._generate(d)

    # -- 5.5 the handover -------------------------------------------------

    def test_the_handover_is_usable_by_a_human_with_no_ai(self):
        """Section 5.5 names what the page must answer. Each is a heading here,
        and the two that a reader acts on first (the command that proves the
        state, and where the code lives) must carry real content."""
        with tempfile.TemporaryDirectory() as d:
            self._project(d, records=2, candidates=2, risk=True)
            self._generate(d, "--tier", "3")
            text = self._read_doc(d, "40-handover/HANDOVER.md")
            expected = [
                "## 1. What this project is",
                "## 2. Current state, and the command that proves it",
                "## 3. What is done",
                "## 4. What is in flight",
                "## 5. What is parked, and why",
                "## 6. What is not started",
                "## 7. Where the code lives, module by module",
                "## 8. How to run it and how to test it",
                "## 9. The known traps",
                "## 10. The open decisions, and their packs",
                "## 11. Who to ask",
                "## 12. What this page cannot tell you",
            ]
            positions = []
            for heading in expected:
                self.assertIn(heading, text, "the handover is missing %s"
                              % heading)
                positions.append(text.index(heading))
            self.assertEqual(positions, sorted(positions),
                             "the handover sections are out of order")
            self.assertIn("python3 tools/test_all.py", text,
                          "the handover does not name the command that proves "
                          "the state")
            self.assertIn("`app/pay.py`", text,
                          "the handover does not say where the code lives")
            self.assertIn("the retry path double charges", text,
                          "a recorded trap is missing from the traps section")
            self.assertIn("Dana", text, "the handover names nobody to ask")

    def test_the_handover_says_so_when_there_is_no_gate_command(self):
        with tempfile.TemporaryDirectory() as d:
            self._project(d)
            # BOTH, because a tree with test_*.py in it DOES declare a runnable
            # check by convention and the engine is right to find one. The case
            # under test is a project that declares nothing at all.
            os.remove(os.path.join(d, "tools", "test_all.py"))
            os.remove(os.path.join(d, "app", "test_pay.py"))
            self._generate(d)
            text = self._read_doc(d, "40-handover/HANDOVER.md")
            self.assertIn("declares no test command", text)

    # -- 5.6 the optional exporter ----------------------------------------

    def test_the_mandatory_path_never_imports_the_exporter(self):
        """Section 5.6, enforced structurally rather than promised. An optional
        dependency reachable from the mandatory path is a dependency."""
        with io.open(self.DOCS, encoding="utf-8") as fh:
            src = fh.read()
        # The two shapes that would actually create the edge: an import
        # statement, and this project's own path loader. Prose is allowed to
        # name the module, because the docstring has to explain what it is.
        for pattern in (r"^\s*import\s+bm_docs_export",
                        r"^\s*from\s+bm_docs_export",
                        r"_load\(\s*[\"\']bm_docs_export"):
            self.assertIsNone(
                re.search(pattern, src, re.MULTILINE),
                "bm_docs.py reaches for the optional exporter (%s)" % pattern)
        # And the load-time proof, which no grep can be talked out of.
        loaded = self._bd("bm_docs_import_edge_check")
        self.assertTrue(hasattr(loaded, "Generator"))
        self.assertEqual(
            [], [n for n in sys.modules if "bm_docs_export" in n],
            "importing the generator loaded the optional exporter")

    def test_the_exporter_adds_no_dependency_and_states_what_it_cannot_do(self):
        with tempfile.TemporaryDirectory() as d:
            self._project(d)
            self._generate(d, "--tier", "3")
            r = subprocess.run([sys.executable, self.EXPORT, "export", "--json"],
                               cwd=d, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, universal_newlines=True)
            self.assertEqual(0, r.returncode, r.stdout + r.stderr)
            report = json.loads(r.stdout)
            formats = set(row["format"] for row in report["produced"]) | \
                set(row["format"] for row in report["refused"])
            self.assertEqual({"pdf", "docx", "xlsx"}, formats,
                             "every format must be accounted for either way")
            for row in report["refused"]:
                self.assertTrue(row["why"].strip(),
                                "%s was refused with no stated reason"
                                % row["format"])

    def test_absent_tooling_degrades_to_a_stated_limitation_not_a_crash(self):
        """The acceptance line in 5.7. Every backend is made absent on purpose,
        which is the state of most machines, and the exporter still exits 0 with
        a reason per format."""
        with tempfile.TemporaryDirectory() as d:
            self._project(d)
            self._generate(d, "--tier", "3")
            be = self._mod("bm_docs_export_absent", self.EXPORT)
            be._importable = lambda name: False
            report = be.export(d)
            self.assertEqual([], report["produced"])
            self.assertEqual(3, len(report["refused"]))
            for row in report["refused"]:
                self.assertIn(row["format"], row["why"],
                              "a refusal must name the format it refused")
                self.assertIn("install", row["why"],
                              "a refusal must tell the reader what would fix "
                              "it: %s" % row["why"])

    def test_a_named_format_that_cannot_be_produced_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as d:
            self._project(d)
            self._generate(d, "--tier", "3")
            r = subprocess.run([sys.executable, self.EXPORT, "export",
                                "--format", "docx"], cwd=d,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               universal_newlines=True)
            self.assertEqual(1, r.returncode, r.stdout + r.stderr)
            self.assertIn("could NOT produce docx", r.stdout)

    def test_the_exporter_report_runs_with_no_store_at_all(self):
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run([sys.executable, self.EXPORT, "report"], cwd=d,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               universal_newlines=True)
            self.assertEqual(0, r.returncode, r.stdout + r.stderr)
            self.assertIn("markdown plus mermaid is always produced", r.stdout)

    # -- copy rule ---------------------------------------------------------

    def test_the_generated_folder_carries_no_em_or_en_dash(self):
        with tempfile.TemporaryDirectory() as d:
            self._project(d, records=2, candidates=2, risk=True)
            self._generate(d, "--tier", "3")
            for rel in sorted(self._tree(d)):
                text = self._read_doc(d, rel.replace(os.sep, "/"))
                for i, line in enumerate(text.split("\n"), 1):
                    for label, ch in (("en", chr(0x2013)), ("em", chr(0x2014))):
                        self.assertNotIn(
                            ch, line,
                            "%s dash on line %d of %s" % (label, i, rel))



class TestNoDashes(unittest.TestCase):
    """The project's own copy rule, enforced on the files this suite governs."""

    def test_no_em_or_en_dash_in_the_active_pages_or_this_toolchain(self):
        offenders = []
        targets = list(ACTIVE_DOCS) + [os.path.join("tools", "bm_project_facts.py"),
                                       os.path.join("tools", "bm_packs.py"),
                                       os.path.join("tools", "bm_docs.py"),
                                       os.path.join("tools", "bm_docs_export.py"),
                                       os.path.join("tools", "test_bm_docs.py")]
        for rel in targets:
            for i, line in enumerate(read(rel).split("\n"), 1):
                if "\u2013" in line or "\u2014" in line:
                    offenders.append("%s:%d" % (rel, i))
        self.assertEqual(offenders, [], "em or en dash found at %s"
                         % ", ".join(offenders))


if __name__ == "__main__":
    unittest.main(verbosity=1)
