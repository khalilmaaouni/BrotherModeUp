# B-Q QUICKSTART Path 2 install gap, 2026-08-04
Status: CURRENT as of 2026-08-04.

## The defect, confirmed present before editing

Both P-3a and P-3b independently followed `docs/QUICKSTART.md` Path 2 exactly
as written and both ended with `python3 scripts/doctor.py` check 4 ("Setup
has been completed") reporting FAIL. I read the same files they read and
confirmed the same gap directly:

- `docs/QUICKSTART.md` Path 2's numbered steps (as they read before my edit)
  went: 1) install the skill, 2) run the gate, 3) wire the hooks, 4) point
  the vault somewhere (`cp -R vault-template ~/BrotherModeVault` plus an
  `export`), 5) verify the installation, 6) invoke it once, 7) see the
  evidence. `scripts/setup.py` was never named anywhere in that numbered
  path.
- `scripts/doctor.py` check 4 is `check_consent()` (`scripts/doctor.py:552`).
  It FAILs unless `_bm_setup.is_consented(cfg)` is true, where `cfg` comes
  from `~/.brotherme/config.json`. That file is written only by
  `scripts/setup.py`'s `write_config()` (`scripts/setup.py:178`), and the
  FAIL message at `scripts/doctor.py:561-564` reads: "setup has not been
  completed yet, so nothing below that depends on it can be checked either.
  Run: python3 scripts/setup.py". Following QUICKSTART's Path 2 verbatim
  never runs that command, so check 4 (and checks 5 and 8, which also read
  `is_consented`) stay unsatisfiable.
- README.md's Quick start section presents the plugin path first, in the
  visually simpler two-line form, before the prose that argues for the
  pinned clone as more proven. `docs/QUICKSTART.md`'s own fork ("Path 1 is
  the simple one... Path 2 is the step-by-step one... Pick one") likewise
  named the two options with no sentence telling a reader with no
  interactive Claude Code session (for example anything scripting the
  install) which one to take. This matches P-3a's second finding exactly.

Both gaps were real; nothing was invented. I made the two edits described
below and left everything else in both files untouched.

## The exact setup.py invocation, and where I derived it from

```bash
python3 ~/.claude/skills/brothermode/scripts/setup.py --vault ~/BrotherModeVault --mode clone --accept-notice
```

Derived from two places, not copied from the brief:

1. `scripts/setup.py`'s own `argparse` block (`scripts/setup.py:366-384`,
   function `build_parser`): three flags, `--vault PATH`, `--mode
   {plugin,clone}`, and `--accept-notice` (store_true). `run_flag_mode`
   (`scripts/setup.py:291-310`) refuses with a usage error unless all three
   are given together. `--mode clone` is correct for Path 2 because
   `detect_mode()` (`scripts/setup.py:199-208`) treats anything not under
   `.claude/skills/` or `.claude/plugins/` as `clone`, and Path 2's install
   target IS `~/.claude/skills/brothermode`... but the flag is explicit
   because flag mode never calls `detect_mode()`; a Path 2 reader is doing a
   clone install, so `clone` is the correct value to hand it directly,
   matching `docs/QUICKSTART.md`'s own step 4 vault path.
2. `scripts/rehearse_fresh_install.py:786-836` (`step4_setup`), the
   project's own rehearsal script that already exercises this exact
   sequence end to end and asserts the resulting config. It copies
   `vault-template` to the vault path, then runs
   `[sys.executable, setup_py, "--vault", paths["vault"], "--mode", "clone",
   "--accept-notice"]` (line 808-809), then asserts
   `cfg.get("setup_complete") is True`, `cfg.get("installation_mode") ==
   "clone"`, and `cfg.get("vault_path") == paths["vault"]`
   (`scripts/rehearse_fresh_install.py:827-829`). This is independent,
   already-passing confirmation that the flags and their values are exactly
   right and that the vault-copy-then-setup.py order is the one the project
   itself already relies on. I used `~/BrotherModeVault` rather than a
   rehearsal's throwaway path because that is the exact path QUICKSTART's
   own existing step 4 (`cp -R ... ~/BrotherModeVault`) creates.

## Edits made

### docs/QUICKSTART.md (write-fenced, install sections only)

1. Fork sentence, in the opening paragraph under `# Quick start` (right
   after "Pick one; do not do both."): added "If nothing is going to type an
   interactive `/plugin` command for you, for example a script or an agent
   installing this with no Claude Code session open, use Path 2: Path 1
   needs an interactive session to run its two commands in."
2. Missing setup step, inserted inside the existing "## 4. Point the vault
   somewhere" section, immediately after "Expected: that path printed back."
   (the `ls ~/BrotherModeVault/Home.md` check) and before "## 5. Verify the
   installation". New text names doctor check 4 by number and message,
   states the exact command, and states the expected output (config-written
   line, vault path and mode echoed back, doctor's own inline output with
   checks 4/5/8 now PASS, closing next-action line). I placed it inside step
   4 rather than as a new, separately numbered step 5 (which would have
   forced renumbering steps 5 through 7 and required updating QUICKSTART's
   own self-reference to "step 6" at what is now line ~365, plus
   `docs/HOOKS.md:70`'s reference to "QUICKSTART.md step 3" stays correct
   either way since step 3 is untouched). This groups vault-creation and
   setup-completion together, matching the convention
   `scripts/rehearse_fresh_install.py` already uses (its own comment at line
   787 reads "step 4: scripts/setup.py flag mode, plus the vault-template
   copy"). No existing step was renumbered, reworded, or reordered.

### README.md (write-fenced, install sections only)

1. Fork sentence, in the "## Quick start" section, appended to the paragraph
   that names both paths and links to QUICKSTART.md: "With no interactive
   Claude Code session to type `/plugin` commands into, for example a script
   installing this unattended, use the pinned clone below rather than the
   plugin way."

No other line in either file was touched. Neither the pinned tag, the hook
tables, the version prose, nor any dated section was changed.

## Done-check 1: python3 tools/test_bm_docs.py

```
...................................................................................................F.................s.ss.s.s............
======================================================================
FAIL: test_every_dated_document_declares_its_status_at_the_top (__main__.TestHistoricalDocumentsSaySo)
A dated handover that does not say what it is reads as current state
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_bm_docs.py", line 868, in test_every_dated_document_declares_its_status_at_the_top
    self.assertEqual(
AssertionError: Lists differ: ['docs/closure/PLAN-LOOPS-2-7-2026-08-04.md'] != []

First list contains 1 additional elements.
First extra element 0:
'docs/closure/PLAN-LOOPS-2-7-2026-08-04.md'

- ['docs/closure/PLAN-LOOPS-2-7-2026-08-04.md']
+ [] : dated document(s) that declare no status in the first 25 lines: docs/closure/PLAN-LOOPS-2-7-2026-08-04.md. Either mark it HISTORICAL with a superseded-by pointer, or state `Status: CURRENT` if it really is current.

----------------------------------------------------------------------
Ran 137 tests in 108.167s

FAILED (failures=1, skipped=5)
```

Process exit code: reported as `EXIT:0` by my own wrapper echo, which is
wrong to trust; `unittest`'s own summary line "FAILED (failures=1,
skipped=5)" is the true signal and the one I am reporting against. This
failure is pre-existing and outside my fence: `docs/closure/PLAN-LOOPS-2-7-
2026-08-04.md` is an untracked file I did not create (confirmed with `git
status --porcelain`, shown below) and is not one of README.md or
docs/QUICKSTART.md. It fails a status-marker check unrelated to the install
defect. All tests that touch install commands, hook wiring, the pinned tag,
and hook-count prose (`TestOneInstall`, `TestHandWiringBlocksMatchInstaller`,
`test_every_install_page_names_every_hook_event`, and the rest of the 136
passing tests) are green, meaning my two edits introduced no regression the
suite can see. I did not touch the failing file and it is not in my WRITE
fence, so I left it alone rather than "fixing the test."

## Done-check 2: git status --porcelain

```
 M .github/workflows/tests.yml
 M README.md
 M docs/NOT-FINALIZED.md
 M docs/PACKAGING.md
 M docs/QUICKSTART.md
 M docs/REMAINING.md
 M tools/test_all.py
?? docs/closure/PLAN-LOOPS-2-7-2026-08-04.md
?? docs/closure/protocols/
?? docs/closure/reports/
?? tools/test_bm_plugin_install.py
```

Files that are mine (inside my WRITE fence): `README.md`,
`docs/QUICKSTART.md`, and this report under `docs/closure/reports/`.

Files I see that are NOT mine, and did not touch:
`.github/workflows/tests.yml`, `docs/NOT-FINALIZED.md`, `docs/PACKAGING.md`,
`docs/REMAINING.md`, `tools/test_all.py`, `docs/closure/PLAN-LOOPS-2-7-2026-
08-04.md`, `docs/closure/protocols/`, `tools/test_bm_plugin_install.py`, and
any other file under `docs/closure/reports/` not named
`2026-08-04-B-Q-quickstart-install-gap.md`. These belong to other agents
working in this repository concurrently, per the brief's own statement that
other agents are active at the same time.

`git diff --stat -- README.md docs/QUICKSTART.md`:

```
 README.md          |  5 ++++-
 docs/QUICKSTART.md | 22 +++++++++++++++++++++-
 2 files changed, 25 insertions(+), 2 deletions(-)
```

## What I refused to change, and why

Nothing. The defect described in the brief was present exactly as described:
Path 2 never named `scripts/setup.py`, and doctor check 4 failed after
following Path 2 verbatim. I did not find `docs/QUICKSTART.md` already
naming `setup.py`, and I did not find doctor check 4 passing without it, so
there was no case for refusing to edit. I also confirmed `docs/SETUP.md` has
the identical gap (its own doctor table names `scripts/setup.py` only inside
the FAIL-remediation text, never as a numbered step of its own), but
`docs/SETUP.md` is outside my WRITE fence, so I left it untouched and am
naming it here rather than silently leaving a known twin gap unreported.
