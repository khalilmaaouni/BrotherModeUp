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


class TestNoDashes(unittest.TestCase):
    """The project's own copy rule, enforced on the files this suite governs."""

    def test_no_em_or_en_dash_in_the_active_pages_or_this_toolchain(self):
        offenders = []
        targets = list(ACTIVE_DOCS) + [os.path.join("tools", "bm_project_facts.py"),
                                       os.path.join("tools", "bm_packs.py"),
                                       os.path.join("tools", "test_bm_docs.py")]
        for rel in targets:
            for i, line in enumerate(read(rel).split("\n"), 1):
                if "\u2013" in line or "\u2014" in line:
                    offenders.append("%s:%d" % (rel, i))
        self.assertEqual(offenders, [], "em or en dash found at %s"
                         % ", ".join(offenders))


if __name__ == "__main__":
    unittest.main(verbosity=1)
