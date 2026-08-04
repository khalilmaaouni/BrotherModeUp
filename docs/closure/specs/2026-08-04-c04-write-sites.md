# Implementation spec: c04-write-sites

Status: CURRENT. Produced 2026-08-04 by a read-only designer agent
against main at 5d9d0ea. The orchestrator applies these by hand; the
agent wrote nothing into the repository itself. Where the agent ran
probes, it did so in a throwaway /tmp copy with its own HOME.

## Summary

Generating test: tools/test_bm.py:1197-1249, TestPreWriteGate.test_no_unreviewed_write_sites, backed by tools/write_sites.json. WRITE_PATTERNS = (open(...w...), os.open(, .write()); _sites() runs os.listdir(HERE) non-recursively, i.e. tools/ only, skipping test_*.py.

Verified the register's claim via grep across every candidate construct in tools/, scripts/, mcp/, brotherme/, cross-checked with a read-only /tmp probe reproducing the exact scan algorithm against the live untouched repo:
- Construct widening alone (os.replace, shutil.{copy2,copyfile,copytree,move,rmtree}, os.mkdir/makedirs, os.unlink/remove, os.chmod), scope still tools/: 48 new raw hits across the 11 already-writing reviewed files (bm_learn/project/sentinel untouched). One of 48 is a docstring mention (bm_store.py:5125), not a real call, so 47 real new sites: exactly the register's figure. tools/ total becomes 116 (was 68).
- Scope widening alone (old 3 patterns) to scripts/+mcp/+brotherme/: scripts/ 20 hits/7 files, mcp/ 1, brotherme/ 0.
- Both widened together: tools/ 116, mcp/ 5, scripts/ 71 (7 files), brotherme/ 0. Total 192 sites/22 files, up from 68/14.

Read the actual line content for all 48 tools/, 5 mcp/, and all 71 scripts/ hits. Every new tools/mcp site is scaffolding around an already-reviewed write (temp-replace, mkdir-before-write, cleanup, chmod, or a verbatim copy/rmtree of the founder's own files); every scripts/ site writes structural config JSON, install-manifest backups, hardcoded benchmark narration, or throwaway rehearsal fixtures, none of it founder or model prose.

Given scale, recommending 2 stages, each landing scanner code plus manifest together so the suite never goes red:
Stage 1 (specified below, probe-verified): widen WRITE_PATTERNS to 8 constructs, widen SCAN_ROOTS to tools/+mcp/+brotherme/. 121 sites, 15 files.
Stage 2 (deferred, findings supplied): add scripts/ to SCAN_ROOTS, 71 sites/7 files, characterization ready to transcribe into the established voice.

Extra finding beyond the register's list: tools/bm_store.py:3689 append-mode open() misses the 'w'-only pattern (no live gap today); flagged as an optional 9th construct, not bundled so the numbers reconcile exactly with "roughly forty-seven."

Adversarial test: test_widened_scope_catches_a_smuggled_site plants an os.replace-only file inside a temp 'scripts'-shaped directory and asserts the shared gate comparison refuses it unreviewed; probe-verified.

## Risks

Stage 1 (exact code given) closes construct-widening for tools/ and scope-widening for mcp/ and brotherme/, but scripts/ (7 files, 71 sites) stays unreviewed by this gate until Stage 2, so C-04 is not fully closed by Stage 1 alone; the register names all four directories. Extra construct gap found beyond the register's list, not bundled in: tools/bm_store.py:3689 opens append mode ('a'), which the 'w'-only pattern misses as its own line (not a live blind spot today, its .write() calls two lines down are already caught); left out so the numbers reconcile exactly with the register's "roughly forty-seven." Did not execute the real test suite (read-only constraint); validated via an isolated /tmp probe reproducing the algorithm against the untouched repo, cross-checked against manual greps. Orchestrator should still run the real suite after applying. Manifest key format change (bare filename to repo-relative path) is breaking for any other reader of write_sites.json; grepped the whole repo and found only tools/test_bm.py and historical doc mentions, nothing else programmatic.

## Uncertain, stated rather than implied

Whether Stage 2 (scripts/) should land now or wait: I read every one of its 71 sites' actual content and found nothing resembling founder or model prose reaching a file unredacted, so remaining work is mostly transcribing findings into the established narrative voice, not fresh investigation; staged per the explicit scale instruction, but reasonable to fold in immediately instead. Whether shutil.move belongs in WRITE_PATTERNS given zero current sites is a judgment call; included as a zero-cost forward safeguard alongside os.replace's siblings, could be dropped without changing any count. Did not verify beyond one grep pass whether any CI/packaging step other than tools/test_bm.py is sensitive to the key-format migration; worth a final check immediately before landing.

## Changes, in the order the agent says to apply them

### 1. tools/test_bm.py

Anchor: class TestPreWriteGate(unittest.TestCase):

Why: Widens both halves: construct set (adds os.replace, shutil's write functions, os.mkdir/makedirs, os.unlink/remove, os.chmod) and scope (os.walk over tools/, mcp/, brotherme/; scripts/ deferred to Stage 2). Manifest keys become repo-relative paths since a bare filename is no longer unique across directories. Verified via a read-only /tmp probe reproducing this exact algorithm against the live repo: found 121 sites across 15 files, matching the proposed manifest exactly; adversarial-test logic independently probe-confirmed to detect the plant and raise AssertionError.

Current:

```
class TestPreWriteGate(unittest.TestCase):
    """Every place in tools/ that writes a file must be a REVIEWED place.

    This does not prove redaction. It proves that a NEW write site cannot appear
    without someone deciding whether it needs redaction, which is the gap that
    let the same secret-leak bug ship three times in one week.
    """
    WRITE_PATTERNS = (r'open\([^)]*["\']w["\']', r'os\.open\(', r'\.write\(')

    def _sites(self):
        found = {}
        for fn in sorted(os.listdir(HERE)):
            if not fn.endswith(".py") or fn.startswith("test_"):
                continue
            src = io.open(os.path.join(HERE, fn), encoding="utf-8").read().splitlines()
            hits = []
            for i, line in enumerate(src, 1):
                if line.strip().startswith("#"):
                    continue
                for pat in self.WRITE_PATTERNS:
                    if re.search(pat, line):
                        hits.append(i)
                        break
            if hits:
                found[fn] = len(hits)
        return found

    def test_no_unreviewed_write_sites(self):
        manifest_path = os.path.join(HERE, "write_sites.json")
        self.assertTrue(os.path.exists(manifest_path),
                        "write_sites.json is missing; it is the reviewed inventory")
        manifest = json.load(io.open(manifest_path))["reviewed"]
        actual = self._sites()
        # Strengthened: the loop below only ever looked at files that still
        # write, so an empty scanner (a broken _sites, a renamed tool) passed
        # this test while proving nothing at all. Both directions must match.
        self.assertTrue(actual, "the write-site scanner found nothing; it is broken")
        for fn in sorted(manifest):
            self.assertIn(fn, actual,
                          "%s is in the reviewed inventory but no longer writes any "
                          "file. If it was renamed or its writes moved, update "
                          "tools/write_sites.json to match." % fn)
        for fn, count in sorted(actual.items()):
            self.assertIn(fn, manifest,
                          "%s writes files but is not in the reviewed inventory. "
                          "Review whether every text it writes passes through "
                          "redaction, then add it to tools/write_sites.json." % fn)
            self.assertEqual(
                count, manifest[fn],
                "%s has %d write sites but %d were reviewed. A write site was "
                "added or removed: confirm it redacts user or model text, then "
                "update tools/write_sites.json." % (fn, count, manifest[fn]))
```

Replacement:

```
class TestPreWriteGate(unittest.TestCase):
    """Every place in tools/, mcp/ and brotherme/ (scripts/ joins once its own
    sites get the same review, see write_sites.json) that writes, replaces,
    copies, removes or chmods a file must be a REVIEWED place. Proves a new
    write site cannot appear unreviewed, the gap that let a secret leak ship
    three times in one week.

    Widened for C-04: old scanner matched only open(...'w'...), os.open( and
    .write(), only inside tools/. Missed os.replace, shutil's write
    functions, os.mkdir/makedirs, os.unlink/remove and os.chmod inside files
    already reviewed, and never scanned scripts/, mcp/, brotherme/.
    """

    WRITE_PATTERNS = (
        r'open\([^)]*["\']w["\']',
        r'os\.open\(',
        r'\.write\(',
        r'os\.replace\(',
        r'shutil\.(copy2?|copyfile|copytree|move|rmtree)\(',
        r'os\.(mkdir|makedirs)\(',
        r'os\.(unlink|remove)\(',
        r'os\.chmod\(',
    )

    #: Repo root, one level above tools/.
    ROOT = os.path.dirname(HERE)

    #: Directories this gate is responsible for, relative to ROOT. "scripts"
    #: joins this once its own files get the same per-file review as the
    #: ones below; it stays out on purpose, not by oversight.
    SCAN_ROOTS = ("tools", "mcp", "brotherme")

    #: Never descended into: caches and build metadata, not reviewable source.
    EXCLUDED_DIRS = {"__pycache__"}

    def _iter_py_files(self, base, root_rel):
        root_abs = os.path.join(base, root_rel)
        for dirpath, dirnames, filenames in os.walk(root_abs):
            dirnames[:] = sorted(
                d for d in dirnames
                if d not in self.EXCLUDED_DIRS
                and not d.startswith(".")
                and not d.endswith(".egg-info"))
            for fn in sorted(filenames):
                if fn.endswith(".py") and not fn.startswith("test_"):
                    yield os.path.join(dirpath, fn)

    def _sites(self, base=None, scan_roots=None):
        base = self.ROOT if base is None else base
        scan_roots = self.SCAN_ROOTS if scan_roots is None else scan_roots
        found = {}
        for root_rel in scan_roots:
            for path in self._iter_py_files(base, root_rel):
                key = os.path.relpath(path, base).replace(os.sep, "/")
                src = io.open(path, encoding="utf-8").read().splitlines()
                hits = []
                for i, line in enumerate(src, 1):
                    if line.strip().startswith("#"):
                        continue
                    for pat in self.WRITE_PATTERNS:
                        if re.search(pat, line):
                            hits.append(i)
                            break
                if hits:
                    found[key] = len(hits)
        return found

    def _assert_matches_manifest(self, actual, manifest):
        """Shared by test_no_unreviewed_write_sites and the adversarial test
        below, so the adversarial test exercises the REAL gate, not a copy."""
        self.assertTrue(actual, "the write-site scanner found nothing; it is broken")
        for key in sorted(manifest):
            self.assertIn(key, actual,
                          "%s is in the reviewed inventory but no longer writes any "
                          "file. If it was renamed or its writes moved, update "
                          "tools/write_sites.json to match." % key)
        for key, count in sorted(actual.items()):
            self.assertIn(key, manifest,
                          "%s writes files but is not in the reviewed inventory. "
                          "Review whether every text it writes passes through "
                          "redaction, then add it to tools/write_sites.json." % key)
            self.assertEqual(
                count, manifest[key],
                "%s has %d write sites but %d were reviewed. A write site was "
                "added or removed: confirm it redacts user or model text, then "
                "update tools/write_sites.json." % (key, count, manifest[key]))

    def test_no_unreviewed_write_sites(self):
        manifest_path = os.path.join(HERE, "write_sites.json")
        self.assertTrue(os.path.exists(manifest_path),
                        "write_sites.json is missing; it is the reviewed inventory")
        manifest = json.load(io.open(manifest_path))["reviewed"]
        actual = self._sites()
        self._assert_matches_manifest(actual, manifest)

    def test_widened_scope_catches_a_smuggled_site(self):
        """C-04 adversarial test. Pre-widening, os.replace and any directory
        outside tools/ were BOTH invisible at once. Plant a throwaway file
        writing only via os.replace inside a directory named "scripts" under
        an isolated temp root, never touching the real repo, and confirm the
        SAME comparison the real gate runs refuses it unreviewed."""
        with tempfile.TemporaryDirectory() as d:
            root = os.path.realpath(d)
            planted_dir = os.path.join(root, "scripts")
            os.makedirs(planted_dir)
            planted = os.path.join(planted_dir, "bm_smuggled_write.py")
            with io.open(planted, "w", encoding="utf-8") as f:
                f.write("import os\n\n\ndef rotate(tmp, path):\n"
                        "    os.replace(tmp, path)\n")

            found = self._sites(base=root, scan_roots=("scripts",))

            self.assertIn("scripts/bm_smuggled_write.py", found,
                          "the widened scanner missed an os.replace site "
                          "inside a scripts-shaped directory; the C-04 fix "
                          "regressed")
            self.assertEqual(found["scripts/bm_smuggled_write.py"], 1)

            with self.assertRaises(AssertionError):
                self._assert_matches_manifest(found, manifest={})
```

### 2. tools/write_sites.json

Anchor: "reviewed": {

Why: Every count was measured against the widened WRITE_PATTERNS on the real files (read-only) and cross-checked with manual greps per construct per file. bm_learn/project/sentinel counts are unchanged (already fully caught by the old 3 patterns) but need the tools/ prefix for the key migration. mcp/bm_mcp_server.py is new: 5 sites, none writing new founder or model text (detail in the companion _comment change). scripts/ is intentionally absent, see Stage 2 in the summary.

Current:

```
  "reviewed": {
    "bm_autosave.py": 9,
    "bm_fence_hook.py": 5,
    "bm_learn.py": 2,
    "bm_runtimes.py": 4,
    "bm_store.py": 6,
    "bm_telemetry.py": 15,
    "bm_threads.py": 7,
    "bm_packs.py": 2,
    "bm_docs.py": 3,
    "bm_docs_export.py": 4,
    "bm_ledger.py": 2,
    "bm_project.py": 4,
    "bm_bash_audit.py": 3,
    "bm_sentinel.py": 2
  }
}
```

Replacement:

```
  "reviewed": {
    "tools/bm_autosave.py": 19,
    "tools/bm_fence_hook.py": 7,
    "tools/bm_learn.py": 2,
    "tools/bm_runtimes.py": 6,
    "tools/bm_store.py": 16,
    "tools/bm_telemetry.py": 27,
    "tools/bm_threads.py": 10,
    "tools/bm_packs.py": 3,
    "tools/bm_docs.py": 4,
    "tools/bm_docs_export.py": 5,
    "tools/bm_ledger.py": 3,
    "tools/bm_project.py": 4,
    "tools/bm_bash_audit.py": 8,
    "tools/bm_sentinel.py": 2,
    "mcp/bm_mcp_server.py": 5
  }
}
```

### 3. tools/write_sites.json

Anchor: Adding write side scrubbing here would have diverged from every other table on the strength of a rule imported from a different context.

Why: The manifest's own convention is one evolving narrative naming the exact construct, file and why its content needs no redaction, not just a number. This addendum follows that for the 47 new tools/ sites and 5 new mcp/ sites, citing the exact evidence read, and records what is deferred (scripts/, matching Stage 2).

Current:

```
Adding write side scrubbing here would have diverged from every other table on the strength of a rule imported from a different context.
```

Replacement:

```
Adding write side scrubbing here would have diverged from every other table on the strength of a rule imported from a different context. C-04 (closure register) widened this gate: WRITE_PATTERNS gained os.replace(, four shutil write functions (copy2, copyfile, copytree, rmtree; move is included for a future caller, unused today), os.mkdir/os.makedirs, os.unlink/os.remove and os.chmod, and the scan widened from tools/ alone to tools/, mcp/ and brotherme/ (scripts/ is staged separately, below). Manifest keys are now paths relative to the repository root, tools/bm_store.py rather than bm_store.py, because a bare filename stopped being unambiguous the moment a second directory joined the scan. Every one of the 47 new sites inside the 14 files already reviewed above was read line by line, not accepted on the scanner's new count, and every one is scaffolding around a write whose CONTENT this comment already reviewed: os.replace is the atomic-swap half of a temp-file-then-replace primitive whose write half was already counted (bm_autosave.py, bm_bash_audit.py, bm_runtimes.py, bm_telemetry.py, bm_threads.py, and bm_store.py's two store-file swaps); os.makedirs/os.mkdir creates a directory ahead of an already-reviewed write and carries no text of its own; os.remove/os.unlink deletes a temp file, a lock, a stale quarantine entry or a corrections file the tool itself created, never reading the deleted content back; os.chmod tightens permissions on a file or directory this project already owns; shutil.copy2/copyfile duplicate an EXISTING file's bytes verbatim (bm_store.py's store migration, bm_telemetry.py's corrections backup) rather than writing anything newly composed. bm_store.py's count carries one hit that is not a call at all: its own line near 5125 is a docstring sentence mentioning 'os.makedirs(exist_ok=' in prose, the same class of non-call site bm_docs.py's 'gen.write()' entry above already established as counted-but-explained rather than a scanner bug. mcp/bm_mcp_server.py entered the inventory in the same change, five sites, all inside _snapshot_for_reading and _remove_snapshot: shutil.copytree and shutil.copy2 duplicate the founder's OWN already-existing store directory and STATE.md into a throwaway read-only snapshot (FINDING 3, symlinks=True so a planted link is copied as a link, never dereferenced), shutil.rmtree removes that same throwaway copy in a finally block with failure reported rather than swallowed (FINDING 3c), a docstring line mentions 'shutil.rmtree(..., ignore_errors=True)' in prose the same way bm_store.py's does, and the one output funnel is stream.write(text) inside _raw_write, matching bm_store.py's own single-writer convention by name on purpose. None of the five writes new founder or model text. brotherme/ joined SCAN_ROOTS in the same change with nothing to add here: zero write sites today, kept in scope so a future one cannot land unreviewed. scripts/ is NOT in SCAN_ROOTS yet: seven files, seventy-one sites by this scanner's count (benchmark.py 15, install.py 15, rehearse_fresh_install.py 18, setup.py 9, doctor.py 6, uninstall.py 5, bm_shell.py 3), every one read for this closure item and none found writing founder or model prose, but the directory is new terrain for this gate and earns its own dated paragraph here rather than a rushed bulk add, so it is a follow-up change.
```

## Tests

### tools/test_bm.py :: TestPreWriteGate.test_no_unreviewed_write_sites

Existing test, now exercising the widened WRITE_PATTERNS (8 constructs) and widened SCAN_ROOTS (tools/, mcp/, brotherme/, recursive via os.walk). Asserts both directions: every manifest key still corresponds to a file that still writes, and every file the scanner finds writing is present with a matching count. Probe-verified against the real repo: returns 121 sites across 15 files (14 in tools/, 1 in mcp/: bm_autosave.py 19, bm_bash_audit.py 8, bm_docs.py 4, bm_docs_export.py 5, bm_fence_hook.py 7, bm_learn.py 2, bm_ledger.py 3, bm_packs.py 3, bm_project.py 4, bm_runtimes.py 6, bm_sentinel.py 2, bm_store.py 16, bm_telemetry.py 27, bm_threads.py 10, mcp/bm_mcp_server.py 5), matching the proposed manifest exactly.

### tools/test_bm.py :: TestPreWriteGate.test_widened_scope_catches_a_smuggled_site

New adversarial test. Plants a throwaway .py file in a temp directory named 'scripts' whose only write construct is os.replace(tmp, path), never touching the real repo. Asserts self._sites(base=root, scan_roots=('scripts',)) finds exactly one site at 'scripts/bm_smuggled_write.py', then asserts self._assert_matches_manifest(found, manifest={}) raises AssertionError since that site is absent from an empty manifest. Probe-verified: found the plant with count 1 and raised AssertionError with the expected 'not in the reviewed inventory' message.
