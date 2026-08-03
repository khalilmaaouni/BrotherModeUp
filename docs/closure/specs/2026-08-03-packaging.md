# Implementation spec: packaging

Status: CURRENT. Produced 2026-08-03 by a read-only designer agent
against commit 75dda42. The orchestrator applies these by hand; the
agent wrote nothing into the repository itself.

## Summary

C-06 (HIGH), reproduced by building the real wheel in an isolated /tmp venv. tools/*.py with cmd_+main(): bm_store, bm_threads, bm_telemetry, bm_learn, bm_packs, bm_docs, bm_docs_export, bm_runtimes, bm_autosave, bm_fence_hook, bm_bash_audit, bm_project (18 subcommands), bm_ledger. pyproject.toml wires 9; bm_project.py and bm_ledger.py wire nothing, confirmed by installing the built wheel: only 9 bm-* scripts land on PATH. bm_autosave/bm_fence_hook/bm_bash_audit correctly have none (hook design). brotherme/core/schema.py: confirmed absent from the wheel; missing key is `packages` (only py-modules + package-dir exist). Adding packages plus a package-dir entry ships it (verified) but is not sufficient alone: bm_store.py's _schema() path only matches the git-checkout layout, still threw FileNotFoundError in a flat install after packaging was fixed. Verified a fallback fix: 4 targeted test files plus the P17 packaging suite green, and a real installed bm-project start/status ran end to end. bm_project_facts.py has no cmd_ dispatch and reads VERSION plus other tools' raw source via the same broken path pattern, none of which a wheel ships; recommend option (b), do not wire it (verified naive wiring crashes on first run). C-07 (MEDIUM): tabulated every event from both files. hooks.json sets timeout+statusMessage on all 7 groups; install.py's shared _group() helper sets neither for SessionStart/SessionEnd/Stop/PreCompact, and sets timeout only (matching) for the 3 PreToolUse/PostToolUse groups. Proved by running install.py against a throwaway HOME and diffing output: exactly 11 mismatches. Wrote the adversarial test, confirmed it fails on the real repo (same 11 lines) and passes against a patched scratch install.py. Belongs in tools/test_install.py, new class after TestCleanInstall. Full table in the changes entries. Real repo untouched throughout (git status/diff empty).

## Risks

The _schema() fix is a real code change beyond pyproject.toml and is REQUIRED for C-06's invoke-each-documented-command criterion: wiring bm-project without it ships a command that exists on PATH but crashes on first real use. bm_project_facts.py has the same bug class but is intentionally left unfixed here since the recommendation is not to package it; if the founder wants it packaged instead, that is materially larger (shipping VERSION and other tools' source as data, or rewriting how it reads facts) and should be scoped separately. Building pyproject.toml only succeeds with modern setuptools/pip; this machine's system pip (21.2.4) silently mis-builds, a pre-existing trap already documented in docs/PACKAGING.md, not introduced by this change. Nothing here was tested on Windows or Linux, only macOS.

## Uncertain, stated rather than implied

bm-project-facts: verified it cannot be a console script as written (reads VERSION and other tools' raw source via a repo-root-relative path); recommend option (b) with a short reason near py-modules or in the header comment, exact wording not drafted. docs/PACKAGING.md is already stale independent of this item (says six console scripts, already nine before any change here); flagged but out of scope, not in the changes list since the register did not assign it. Did not check whether docs/HOOKS.md, docs/SETUP.md, or skills/commands/*.md need updates for the new console scripts; left untouched since they invoke python3 tools/bm_project.py by relative path, which stays valid regardless. For C-07, did not check scripts/uninstall.py, scripts/doctor.py, or scripts/verify-install.sh for their own copies of this data; register named only hooks.json vs install.py. Matched the existing single-line inline-table TOML style for package-dir; did not run a separate TOML linter beyond the real setuptools build itself.

## Changes

### pyproject.toml

Anchor: [project.scripts]
bm-store = "bm_store:main"

Why: bm_project.py (18 subcommands, its own cli() already exists, docstring says Console-script entry point, never wired) and bm_ledger.py (main(argv=None), already zero-arg callable) are the two tools the register names as missing. Verified end to end: fresh-venv pip install exposes both, bm-project start/status ran (exit 0, real output), and the P17 packaging suite (10 cases) passed unmodified. bm-project-facts deliberately excluded, see uncertain.

Current:

```
[project.scripts]
bm-store = "bm_store:main"
bm-threads = "bm_threads:main"
bm-telemetry = "bm_telemetry:main"
bm-learn = "bm_learn:cli"
bm-packs = "bm_packs:cli"
bm-docs = "bm_docs:cli"
bm-docs-export = "bm_docs_export:cli"
bm-runtimes = "bm_runtimes:cli"
bm-score = "bm_score:cli"
```

Replacement:

```
[project.scripts]
bm-store = "bm_store:main"
bm-threads = "bm_threads:main"
bm-telemetry = "bm_telemetry:main"
bm-learn = "bm_learn:cli"
bm-packs = "bm_packs:cli"
bm-docs = "bm_docs:cli"
bm-docs-export = "bm_docs_export:cli"
bm-runtimes = "bm_runtimes:cli"
bm-score = "bm_score:cli"
bm-project = "bm_project:cli"
bm-ledger = "bm_ledger:main"
```

### pyproject.toml

Anchor: [tool.setuptools]
package-dir = { "" = "tools" }

Why: Precise missing key behind the brotherme/core/schema.py claim. Without a package-dir entry for brotherme, declaring packages alone makes setuptools look under tools/brotherme, which does not exist, instead of the real ./brotherme. Verified by building the wheel with and without this line.

Current:

```
[tool.setuptools]
package-dir = { "" = "tools" }
```

Replacement:

```
[tool.setuptools]
# "" (the root) maps to tools/, where every flat py-module below lives.
# brotherme is a real package (brotherme/, brotherme/core/) that sits next
# to tools/ at the repo root, not inside it, so it needs its own mapping;
# without this second entry setuptools looks for it at tools/brotherme and
# finds nothing (reproduced: built wheel lists brotherme/ zero times
# without this line, three times with it).
package-dir = { "" = "tools", "brotherme" = "brotherme" }
```

### pyproject.toml

Anchor:     "bm_ledger",
]
include-package-data = false

Why: The actual declare-the-packages half of C-06. Confirmed empirically: current pyproject.toml (no packages key, no packages.find) builds a wheel with zero brotherme/ entries; adding this line ships brotherme/core/schema.py for real.

Current:

```
    "bm_ledger",
]
include-package-data = false
```

Replacement:

```
    "bm_ledger",
]
# brotherme/core/schema.py is library code tools/bm_store.py loads by path
# (see _schema() there); without this the wheel/sdist never contain it and
# every packaged command touching a project/task/forecast/alert fails at
# runtime with FileNotFoundError. Verified in the built wheel's file list.
packages = ["brotherme", "brotherme.core"]
include-package-data = false
```

### tools/bm_store.py

Anchor: def _schema():

Why: REQUIRED companion fix, not optional. Shipping schema.py is necessary but not sufficient: in a flat pip install bm_store.py sits one directory shallower than in the git checkout, so the old two-dirname-up path landed above site-packages and every Store method touching a project/task/forecast/alert (16 call sites) threw FileNotFoundError at runtime, reproduced directly in an installed venv. Verified fix: 4 targeted test files all green against a patched scratch copy, plus a real installed bm-project start/status ran end to end.

Current:

```
    global _SCHEMA_MOD
    if _SCHEMA_MOD is None:
        import importlib.util
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "brotherme", "core", "schema.py")
        spec = importlib.util.spec_from_file_location(
            "brotherme_core_schema", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _SCHEMA_MOD = mod
    return _SCHEMA_MOD
```

Replacement:

```
    global _SCHEMA_MOD
    if _SCHEMA_MOD is None:
        import importlib.util
        here = os.path.dirname(os.path.abspath(__file__))
        # Two layouts to support, checked in this order:
        #  1. flat pip/pipx install: this file and the brotherme/ package
        #     both land directly in site-packages, so brotherme/core is a
        #     sibling of this file's own directory.
        #  2. git checkout: this file lives in <repo>/tools/, brotherme/
        #     is a sibling of tools/ one level up.
        for candidate_root in (here, os.path.dirname(here)):
            path = os.path.join(candidate_root, "brotherme", "core", "schema.py")
            if os.path.exists(path):
                break
        spec = importlib.util.spec_from_file_location(
            "brotherme_core_schema", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _SCHEMA_MOD = mod
    return _SCHEMA_MOD
```

### tools/test_install.py

Anchor: DOCTOR = os.path.join(ROOT, "scripts", "doctor.py")
SHELL = os.path.join(ROOT, "scripts", "bm_shell.py")

Why: Mirrors the HOOKS_JSON_PATH pattern already used in tools/test_bm_bash_audit.py, reusing this file's own ROOT constant. Needed by the new test class below.

Current:

```
DOCTOR = os.path.join(ROOT, "scripts", "doctor.py")
SHELL = os.path.join(ROOT, "scripts", "bm_shell.py")
```

Replacement:

```
DOCTOR = os.path.join(ROOT, "scripts", "doctor.py")
SHELL = os.path.join(ROOT, "scripts", "bm_shell.py")
HOOKS_JSON_PATH = os.path.join(ROOT, "hooks", "hooks.json")
```

### tools/test_install.py

Anchor:         self.assertTrue(os.path.isfile(os.path.join(self.target, "SKILL.md")))


class TestRefusals(InstallerCase):

Why: The adversarial test the register asks for (fails on any divergence). Reuses TestCleanInstall's own run_install()/read_settings() round trip. Proven both directions: run against the real repo today it fails with exactly 11 mismatches matching the hand tabulation; run against a scratch install.py patched to supply matching values, it passes. Reads hooks.json's own values as expected, never a third hardcoded copy, so it stays correct whether the fix is per-event constants or a shared generator.

Current:

```
        self.assertTrue(os.path.isfile(os.path.join(self.target, "SKILL.md")))


class TestRefusals(InstallerCase):
```

Replacement:

```
        self.assertTrue(os.path.isfile(os.path.join(self.target, "SKILL.md")))


class TestHooksJsonAgreesWithInstaller(InstallerCase):
    # C-07: hooks/hooks.json and scripts/install.py's hook_groups() are two
    # hand-maintained copies of the same hook wiring. hooks.json sets an
    # explicit timeout and statusMessage on every group; install.py's
    # shared _group() helper never set statusMessage anywhere, and never
    # set timeout on SessionStart, SessionEnd, Stop or PreCompact. Same
    # drift class as the P17 packaging suite in tools/test_bm.py guards
    # for pyproject.toml: compare field by field instead of trusting them
    # to agree.

    def _manifest_groups(self):
        with io.open(HOOKS_JSON_PATH, encoding='utf-8') as fh:
            return json.load(fh)['hooks']

    def test_every_group_agrees_on_timeout_and_statusMessage(self):
        r = self.run_install()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        installed = self.read_settings()['hooks']
        manifest = self._manifest_groups()
        mismatches = []
        for event, groups in manifest.items():
            installed_groups = installed.get(event, [])
            for want in groups:
                matcher = want.get('matcher')
                got = next((g for g in installed_groups
                            if g.get('matcher') == matcher), None)
                if got is None:
                    mismatches.append(
                        '%s[%s]: hooks.json wires this group; the '
                        'installed settings.json has no matching group'
                        % (event, matcher))
                    continue
                want_entry = want['hooks'][0]
                got_entry = got['hooks'][0]
                for field in ('timeout', 'statusMessage'):
                    w = want_entry.get(field)
                    g = got_entry.get(field)
                    if w != g:
                        mismatches.append(
                            '%s[%s].%s: hooks.json=%r, installer=%r'
                            % (event, matcher, field, w, g))
        self.assertEqual([], mismatches, '\n'.join(mismatches))


class TestRefusals(InstallerCase):
```

## Tests

### tools/test_install.py :: TestHooksJsonAgreesWithInstaller.test_every_group_agrees_on_timeout_and_statusMessage

Runs real scripts/install.py against a throwaway HOME, reads hooks/hooks.json, and for every (event,matcher) group asserts the installed settings.json group's timeout and statusMessage match the manifest's. Fails today (11 named mismatches, verified); passes once install.py agrees (verified against a patched scratch copy). Full event table (matcher: hooks.json timeout,statusMessage / install.py timeout,statusMessage): SessionStart none: 30,'Loading your project memory' / unset,unset. SessionEnd none: 30,'Saving the session record' / unset,unset. Stop none: 15,'Checking for unfinished work' / unset,unset. PreCompact none: 60,'Saving your work before the context is condensed' / unset,unset. PreToolUse fence-matcher: 10,'Checking that only one worker edits this file' / 10,unset. PreToolUse Bash: 10,'Noting the fenced files before this shell command runs' / 10,unset. PostToolUse Bash: 15,'Checking whether that shell command crossed a fence' / 15,unset.

### tools/test_bm.py :: TestP17PackagingManifestMatchesTheRepository (existing, all 10 cases)

Re-run unmodified against the proposed pyproject.toml text; 10/10 passed, including the zero-arg-callable signature check that would catch a bad bm-project-facts wiring, confirming bm-project=bm_project:cli and bm-ledger=bm_ledger:main are safe.

### tools/test_bm_store.py, test_bm_schema.py, test_bm_project.py, test_bm_ledger.py :: existing suites, re-run unmodified against the patched _schema()

699/699, 20/20, 40/40, 15/15 respectively, green against a scratch copy with the two-candidate _schema() fallback, confirming the companion fix regresses nothing in either layout.
