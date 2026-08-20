# Cross-family debate: the control-integrity unit, night of 2026-08-21

Status: CURRENT
Date: 2026-08-21
Reviewer: codex-cli 0.146.0, model gpt-5.6-sol, reasoning effort high, sandbox
read-only. A DIFFERENT model family from the one that wrote the code, which is
the entire point of running it: this family's own blind spots cannot review
themselves.
Commits under review: a9098a4 (M19), fe19375 (M17), b06e17f (M18 and the M15
measurement). All three were ALL GREEN on the full gate before this ran.
Verdict returned: NOT READY. 8 BLOCKER, 5 MAJOR, 3 MINOR.

HOW TO READ THIS FILE, and it matters. What follows is the reviewer's verbatim
answer, and it is a set of HYPOTHESES, not established facts. This estate has a
recorded failure in which a vivid reviewer report reached the founder inside an
hour with nobody reproducing it, and six later attempts to reproduce it all
failed. So every finding below was sent to a separate reproduction pass whose
only job is to execute each claim and report REPRODUCED, NOT REPRODUCED, or
PARTIAL with the commands that settle it. Findings that reproduce become queue
items. Findings that do not reproduce are recorded as not reproduced, here,
rather than quietly dropped.

Two of the findings are regressions introduced by the very commits that close
this unit, and one of those had been reviewed by hand and cleared. That is this
unit's own failure family (a control reporting on a dimension it never looked
at) reappearing inside the fix for it, which is worth more than the item count.

The reviewer's brief asked it specifically to attack five classes this family
under-weights: environment inheritance, shell quoting, locale decode, SQLite
transactions, and two-process contention.

Home paths below are masked to the tilde form, per this project's convention
for anything that can reach a public surface.

## The reviewer's verbatim answer

Status: CURRENT
Verdict: NOT READY

1. M18 examines the conventional install directory, not the hook actually wired  
   File/function: [scripts/migrate_install.py](~/Documents/BrotherModeUp/scripts/migrate_install.py:243), `detect`, `_clone_fence_present`, `_schema_gap_message`, `build_plan`.  
   Concrete failure scenario: settings wires `/opt/old/tools/bm_fence_hook.py` beside schema-20 `bm_store.py`, while `~/.claude/skills/brothermode` contains schema 21. Detection retains only a boolean, then checks the latter directory and prints `NOTHING TO DO`; the actual schema-20 hook fails open against a schema-21 store.  
   Severity: BLOCKER.

2. M18 never reads the schema of the store the hook must open  
   File/function: [scripts/migrate_install.py](~/Documents/BrotherModeUp/scripts/migrate_install.py:179), `_schema_gap_message`.  
   Concrete failure scenario: checkout and wired source both declare schema 21, but the real store is schema 20 or 22. `wired_version >= current_version` returns no gap and `build_plan` prints `NOTHING TO DO`; `ReadOnlyStore` refuses either a behind or ahead schema and the hook cannot reach a verdict. Comparing source constants is not a liveness check.  
   Severity: BLOCKER.

3. M17 silently skips the real store unless doctor starts at the exact project root  
   File/function: [scripts/doctor.py](~/Documents/BrotherModeUp/scripts/doctor.py:293), `blocked_write_simulation`.  
   Concrete failure scenario: run `python3 ../scripts/doctor.py` from `repo/docs`, with the real store at `repo/.brothermode/store.sqlite3` and a stale wired hook. `real_root = os.getcwd()` searches `repo/docs/.brothermode`, finds nothing, the self-consistent throwaway test passes, and the fence check reports PASS.  
   Severity: BLOCKER.

4. A malformed store path is interpreted as “no store to inspect”  
   File/function: [scripts/doctor.py](~/Documents/BrotherModeUp/scripts/doctor.py:423), `blocked_write_simulation`.  
   Concrete failure scenario: `.brothermode/store.sqlite3` is a directory, dangling symlink, or unstatable entry. `os.path.isfile` returns false, so the real-store check is omitted; the actual hook takes its `no-store` fail-open path while doctor reports the fence PASS.  
   Severity: BLOCKER.

5. M17 tests the real store under the wrong interpreter  
   File/function: [scripts/doctor.py](~/Documents/BrotherModeUp/scripts/doctor.py:428), `blocked_write_simulation`.  
   Concrete failure scenario: settings wires `/usr/bin/python3`, but doctor runs inside a virtualenv. The wired interpreter can process the `/tmp` throwaway yet lacks permission to read the real store under macOS protected Documents; the virtualenv’s `sys.executable` can read it. Real verification passes under the virtualenv, doctor reports PASS, and the actual wired hook fails open.  
   Severity: BLOCKER.

6. Doctor does not execute the wired command with shell semantics  
   File/function: [scripts/doctor.py](~/Documents/BrotherModeUp/scripts/doctor.py:226), `find_fence_entries`, `_run`, `blocked_write_simulation`.  
   Concrete failure scenario: the configured shell command is `python3 '/path/bm_fence_hook.py' --doctor >/dev/null`. Doctor uses `shlex.split` and executes an argument list; `--doctor` makes the hook accept the remaining arguments and doctor captures deny JSON. The real harness shell redirects that JSON to `/dev/null`; exit 0 carries no deny decision, so writes proceed while doctor reports PASS.  
   Severity: BLOCKER.

7. M19 mutates the durable pack after the ceremony requires it committed  
   File/function: [tools/bm_handover.py](~/Documents/BrotherModeUp/tools/bm_handover.py:1642), `cmd_zip`; `cmd_verify_close`.  
   Concrete failure scenario: skeleton copies board A, the pack is committed as required by the checked-in ceremony, the live board becomes B, then zip overwrites the pack copy with B. `verify-close` sees that the filename is tracked and that the zip matches the now-dirty working-tree pack, so it reports PASS; git still durably contains board A.  
   Severity: BLOCKER.

8. M19 follows a destination symlink before applying its containment gate  
   File/function: [tools/bm_handover.py](~/Documents/BrotherModeUp/tools/bm_handover.py:1676), `cmd_zip`.  
   Concrete failure scenario: `pack/GANTT.html` is a symlink to an external file. `shutil.copy2` follows and overwrites that external target before `_pack_files_for_zip` calls `_safe_pack_file` and refuses the symlink. A read/package command has already damaged an out-of-scope file.  
   Severity: BLOCKER.

9. M19 does not reconcile board deletion or candidate changes  
   File/function: [tools/bm_handover.py](~/Documents/BrotherModeUp/tools/bm_handover.py:220), `_board_source`, `cmd_zip`.  
   Concrete failure scenario: skeleton copies fallback `COMMAND-CENTER.html`; before zip, `GANTT.html` appears. Zip adds GANTT but leaves the stale COMMAND-CENTER and the generated read-me still directs the recipient to it. If the board disappears entirely, `board_abs is None` and the old copy is archived unchanged.  
   Severity: MAJOR.

10. M18’s text parser can certify a runtime version that is not real  
    File/function: [scripts/migrate_install.py](~/Documents/BrotherModeUp/scripts/migrate_install.py:159), `_schema_version_of`, `_schema_gap_message`.  
    Concrete failure scenario: a valid foreign module contains `if False: SCHEMA_VERSION = 999` before its actual `SCHEMA_VERSION = 20`. The parser returns 999 and `build_plan` prints `NOTHING TO DO`, although importing the module would yield 20 and fail against schema 21. Separately, `realpath` catches symlink/self execution, but not two paths hardlinked to the same inode; that arrangement remains self-referential.  
    Severity: MAJOR.

11. Concurrent store activity produces a definitive but false schema diagnosis  
    File/function: [scripts/doctor.py](~/Documents/BrotherModeUp/scripts/doctor.py:411), `blocked_write_simulation`; `tools/bm_store.py`, `verify`.  
    Concrete failure scenario: another process commits a park operation, then doctor reads the updated database before that process regenerates `STATE.md`. `verify` reports view drift, and M17 rewrites every nonzero result as “wired hook cannot read this store; upgrade it; fence fails open.” The hook may be healthy; the claimed cause and remediation are false. WAL makes ordinary concurrent reads safe, but does not make database and `STATE.md` one transaction. Stale WAL, mid-migration, or unsupported locking similarly fail toward FAIL, not PASS; a newer migration committed immediately after verification can still leave a stale PASS.  
    Severity: MAJOR.

12. Explicit UTF-8 decoding is not enough when the child emits in its locale  
    File/function: [scripts/migrate_install.py](~/Documents/BrotherModeUp/scripts/migrate_install.py:276), `_install_dry_run_preview`, `main`; [scripts/doctor.py](~/Documents/BrotherModeUp/scripts/doctor.py:286), `_run`.  
    Concrete failure scenario: under a non-UTF-8 locale, `install.py` emits a home path containing `é` in the locale encoding while migrate_install decodes as UTF-8. `UnicodeDecodeError` is not caught; on `--apply`, this happens after `shutil.rmtree`, leaving the install removed. Doctor’s locale-decoded calls can likewise throw when the wired interpreter emits UTF-8; the CLI wrapper converts that to fence FAIL, not PASS. M18’s two install subprocesses specify UTF-8; M17’s init, session-label, claim, hook-query, and real-verify calls do not. No locale-corruption route to a false PASS was found in the JSON verdict itself because its decision keys are ASCII.  
    Severity: MAJOR.

13. M17’s “read-only” subprocesses may write outside the temporary project  
    File/function: [scripts/doctor.py](~/Documents/BrotherModeUp/scripts/doctor.py:309), `blocked_write_simulation`.  
    Concrete failure scenario: `PYTHONDONTWRITEBYTECODE` is unset and the installed tools directory is writable with no current cache. Loading sibling modules can create or refresh `__pycache__` beside the installed hook, contradicting the claim that nothing outside the temporary directory is written. `HOME`, `PATH`, virtualenv variables, and `PYTHONPATH` are all inherited from the doctor shell, which may not be the harness environment; a dotted home-directory name itself is harmless.  
    Severity: MINOR.

14. The regression suite is green without covering the decisive M18 property  
    File/function: [tools/test_bm.py](~/Documents/BrotherModeUp/tools/test_bm.py:5798), `TestM1MigrateInstallScript`; [tools/test_bm_handover.py](~/Documents/BrotherModeUp/tools/test_bm_handover.py:1200), `TestZip`.  
    Concrete failure scenario: both M18 tests create source trees but no schema-ahead SQLite store, despite `QUEUE.json` requiring one. They also wire only the same `skill_dir` that `_schema_gap_message` assumes. Therefore the wrong-wired-path and real-store-behind/ahead scenarios above remain green. M19’s test has no git repository, candidate switch, deletion, or symlink destination, so the post-commit and path failures also remain green. The narrow M19 and M17 assertions were not already true in their parent commits; M18’s source-version assertion was new, but it passes for a weaker reason than the claimed “hook can reach a verdict against the real store.”  
    Severity: MAJOR.

15. Ordinary spaces, quotes, newlines, and the dotted home name do not independently break path transport  
    File/function: `scripts/install.py`, `_q`; `scripts/doctor.py`, `find_fence_entries`; `scripts/migrate_install.py`, subprocess call sites.  
    Concrete failure scenario: NO-DATA. Installer-generated commands use `shlex.quote`, doctor reverses that with `shlex.split`, and subprocess paths are passed as argument lists. No separate false PASS was found for these literal path shapes. Symlink, wrong-target, shell-operator, and file-versus-directory failures are covered above.  
    Severity: MINOR.

16. M15’s no-defect conclusion is adequately discriminated  
    File/function: [docs/evidence/night-2026-08-21-m15-parked-record.md](~/Documents/BrotherModeUp/docs/evidence/night-2026-08-21-m15-parked-record.md:19), measurement; `tools/bm_fence_hook.py`, `cmd_query`, `decide`, `active_claims`.  
    Concrete failure scenario: NO-DATA. The exact parked target was denied before parking and allowed afterward, while a second active target was denied at the same moment, under both byte-identical hook/store copies, with no fail-open warning. Claim removal during park would still mean PARKED is treated as dead. The evidence does not prove which interpreter or environment a live harness wires, but it is sufficient for the narrower state-semantics question asked by M15.  
    Severity: MINOR.
