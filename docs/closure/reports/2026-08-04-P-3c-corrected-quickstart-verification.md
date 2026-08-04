# P-3c corrected QUICKSTART verification, 2026-08-04

Status: CURRENT as of 2026-08-04.

## Deciding answer

Yes, on the corrected run from the correct neutral directory, doctor reports ZERO failed checks.

Verbatim summary line, final doctor run, exit code 0:

```
9 of 10 proven, 1 skipped, 0 failed.
All 10 checks passed (SKIP is not a failure unless --strict; see the reason printed next to it).
```

Check 7 (project store health) is the one SKIP, and SKIP is documented as not a failure: "SKIP: no project store at /private/tmp/bm-probe-p3c/neutral/.brothermode/store.sqlite3 under the current directory."

This clean result took two attempts. The first attempt was contaminated by an isolation mistake on my part (full account below, under "Isolation incident"), not by anything wrong with the page. Once corrected, the page's Path 2, followed verbatim with the one instructed exception below, leaves doctor at zero failures.

## Isolation incident (read this before the rest)

The Bash tool's working directory did not persist between my separate tool calls in this run, contrary to what I expected. A `cd "$ROOT/neutral"` issued in one call did not carry into the next call; cwd reset to this session's actual working directory, `/Users/khalil.maaouni/Documents/BrotherSBE`, a real project of the founder's with its own `.brothermode/store.sqlite3`.

Concretely: my first "pre-vault" doctor.py run correctly ran from the throwaway neutral directory because I put the `cd` and the `python3` call in the same shell invocation, and it correctly reported check 7 as SKIP (no store there). My next few calls (`cp -R` vault-template, `ls`, `python3 scripts/setup.py ...`) did not repeat the `cd`, on the wrong assumption that cwd would still be the neutral directory. `setup.py` runs an embedded doctor check as part of its own output, and that embedded check 7 read `/Users/khalil.maaouni/Documents/BrotherSBE/.brothermode/store.sqlite3`, the founder's real project store, and reported "STORE CORRUPT: store is at schema 12 and this BrotherMode is at 13." Doctor's own text says this check is read-only and "Nothing was touched" regarding migration.

I checked the real damage directly:

```
ls -la /Users/khalil.maaouni/Documents/BrotherSBE/.brothermode/
-rw-------  store.sqlite3                          Aug  2 17:50  (unchanged)
-rw-------  store.sqlite3-shm                       Aug  4 16:26  (touched today)
-rw-------  store.sqlite3-wal                        Aug  2 17:50  (unchanged)
-rw-------  store.sqlite3.pre-schema11-migration      Aug  1 10:12  (unchanged)
-rw-------  store.sqlite3.pre-schema12-migration      Aug  2 12:22  (unchanged)
```

The main database file and the WAL file are unchanged; only the `-shm` shared-memory sidecar's mtime changed, a known side effect of merely opening a SQLite WAL database for a read, not a data write. `.brothermode/` is excluded from git via `.git/info/exclude` (`git check-ignore -v .brothermode` confirms this), so this did not touch any tracked file and produced no git diff. I did not attempt to "fix" the mtime afterward; doing so would just be another unrequested write, and the safer path was full disclosure plus getting a clean re-run from the correct directory.

After discovering this, I redid every remaining cwd-sensitive command with the `cd` and the command in the same Bash invocation, never relying on cwd persisting across calls again. The deciding-question doctor run quoted above is from that corrected sequence, verified with `pwd` printed inline immediately before the check.

`ls -ld` of the two protected paths, before and after this entire session, both unchanged (same size and mtime both times), confirming neither was touched:

Before:
```
drwxr-xr-x@ 18 khalil.maaouni  218767226  576 Jul 31 01:20 /Users/khalil.maaouni/Documents/Kay Vault
drwxr-xr-x@ 38 khalil.maaouni  218767226  1216 Aug  4 15:29 /Users/khalil.maaouni/.claude
```
After:
```
drwxr-xr-x@ 18 khalil.maaouni  218767226  576 Jul 31 01:20 /Users/khalil.maaouni/Documents/Kay Vault
drwxr-xr-x@ 38 khalil.maaouni  218767226  1216 Aug  4 15:29 /Users/khalil.maaouni/.claude
```

## Setup

Throwaway root: `/private/tmp/bm-probe-p3c`. In every Bash call from that point on I re-exported:

```bash
export ROOT=/private/tmp/bm-probe-p3c
export HOME="$ROOT/home"
export BROTHERMODE_VAULT="$ROOT/home/BrotherModeVault"
export BROTHERSBE_VAULT="$ROOT/home/BrotherSBEVault"
```

`BROTHERMODE_VAULT` was pre-set to the same path the page's own step 4 later creates (`$HOME/BrotherModeVault`), which is itself inside the throwaway `HOME`, so it stayed consistent throughout. `BROTHERSBE_VAULT` was set to a throwaway path as a safety net; nothing in this page's Path 2 reads it.

## Which path I followed, and the one instructed deviation

The page's own opening section says to use Path 2 "if nothing is going to type an interactive `/plugin` command for you, for example a script or an agent installing this with no Claude Code session open." I am exactly that case, so I followed Path 2 start to finish, in order, as written.

One exception, ordered by the task brief itself, not a choice I made: the brief's "OTHER CONSTRAINTS" explicitly says "Do not run `python3 tools/test_all.py`." Path 2 step 2 instructs exactly that command as the gate. I did not run it. This is a deliberate, instructed skip, not something the page told me to skip, and I record it here so the gap is visible rather than silently absorbed into "ALL GREEN" language I never earned.

## Every command run, in order, verbatim, including failures

```bash
# throwaway root
mkdir -p "$ROOT/home" "$ROOT/bmvault-unused" "$ROOT/bsbevault-unused" "$ROOT/neutral"

# Step 1: clone (Path 2 step 1)
git clone --branch v2.0.0-rc.13 --depth 1 https://github.com/khalilmaaouni/BrotherModeUp.git "$HOME/.claude/skills/brothermode"
# exit 0. Output included a warning line not mentioned by the page:
#   "warning: refs/tags/v2.0.0-rc.13 <sha> is not a commit!" then a detached-HEAD notice.
# This is normal git behavior for an annotated tag object and is benign, but the page's
# "Expected" text ("git prints a few lines ending in ... Resolving deltas: 100% (N/N), done.")
# did not match: no "Resolving deltas" line appeared in my output at all (see finding below).

ls "$HOME/.claude/skills/brothermode/SKILL.md"
# exit 0, path printed back exactly as expected.

# Step 2: SKIPPED PER TASK BRIEF, NOT PER THE PAGE.
# python3 tools/test_all.py -- not run, see "one instructed deviation" above.

# Step 3: wire the hooks (Path 2 step 3)
python3 "$HOME/.claude/skills/brothermode/scripts/install.py" --dry-run
# exit 0, matched expected shape (6 event names, 7 hook entries, smoke skipped as dry-run).

python3 "$HOME/.claude/skills/brothermode/scripts/install.py"
# exit 0. Real run. See findings below on two mismatches against the page's "Expected" text.

python3 -m json.tool "$HOME/.claude/settings.json"
# exit 0, file printed back reformatted, no error.

# first doctor.py run, correctly from neutral (cd and python3 in the same call)
cd "$ROOT/neutral" && python3 "$HOME/.claude/skills/brothermode/scripts/doctor.py"
# exit 1 (expected pre-vault/setup): 6 PASS, 3 SKIP, 1 FAIL (check 4, "setup has been
# completed"). See finding below: the page says checks 4, 5, 8 SKIP at this point; check 4
# actually FAILs, not SKIPs.

# Step 4: point the vault (Path 2 step 4)
cp -R "$HOME/.claude/skills/brothermode/vault-template" "$HOME/BrotherModeVault"
# exit 0
ls "$HOME/BrotherModeVault/Home.md"
# exit 0, path printed back exactly as expected.

python3 "$HOME/.claude/skills/brothermode/scripts/setup.py" --vault "$HOME/BrotherModeVault" --mode clone --accept-notice
# exit 0. "setup: config written to .../.brotherme/config.json" as expected, vault path and
# mode printed back, doctor printed inline. THIS CALL IS THE ISOLATION INCIDENT: no cd was
# given, cwd was the real BrotherSBE repo, so the embedded doctor's check 7 read that repo's
# real .brothermode/store.sqlite3 and reported FAIL ("STORE CORRUPT: schema 12 vs 13").
# That FAIL is not a finding about this page or this install; it is contamination from my
# own directory mistake. Full account above under "Isolation incident."

# confirm the incident, read-only
ls -la /Users/khalil.maaouni/Documents/BrotherSBE/.brothermode/
git status --short --ignored=matching | grep -i brothermode
git check-ignore -v .brothermode

# corrected, final doctor.py run: cd and the command in the same invocation this time
cd "$ROOT/neutral" && pwd && python3 "$HOME/.claude/skills/brothermode/scripts/doctor.py"
# exit 0. THIS IS THE RUN THE DECIDING ANSWER IS TAKEN FROM: 9 PASS, 1 SKIP (check 7, no
# store here, correctly), 0 FAIL. "All 10 checks passed."

# Step 5: verify the installation (Path 2 step 5)
cd "$ROOT/neutral" && pwd && python3 "$HOME/.claude/skills/brothermode/tools/bm_score.py"
# exit 0. Matched the page's expected shape: mostly NO-DATA, some PASS, a FAIL naming
# STATE.md. See finding below: the page says only one check (budget-vs-tier) can FAIL on
# STATE.md; my output had two (fence-hygiene and budget-vs-tier), both naming STATE.md.

cd "$ROOT/neutral" && sh "$HOME/.claude/skills/brothermode/tools/bm_sessionstart.sh"
# BLOCKED. The Claude Code auto-mode classifier in this session denied the action outright
# ("Blocked by classifier"), on both the first attempt and a retry. I did not attempt to
# work around this. This step could not be verified in this run; it is a limitation of my
# sandbox, not a finding about the page.

# Additional, orchestrator-requested checks, not from the page itself:
cd "$HOME/.claude/skills/brothermode" && pwd && sh scripts/verify-install.sh
# exit 0. "verify-install: PASSED. ... 235 file(s) match, 0 mismatched, 0 missing,
# 0 wrong type, 0 extra."

cd "$HOME/.claude/skills/brothermode" && pwd && python3 tools/bm_project_facts.py --field install_target_tag
# exit 0, output: v2.0.0-rc.13. This is the "one real command run through the installed
# copy" requested by the brief; its output (v2.0.0-rc.13) matches the tag actually cloned
# in step 1, confirming the page's own claim that this field, not a hand-typed tag, drives
# the clone command.

# Path 2 steps 6 and 7, attempted as far as literally possible:
ls -la "$BROTHERMODE_VAULT/99-System/telemetry/"
tail -1 "$BROTHERMODE_VAULT/99-System/telemetry/outcomes.jsonl"
# exit 1, "No such file or directory". Expected, given step 6 could not be performed (see
# "Ambiguities" below): the page itself says this is the most common cause of a missing
# line, "a session too short to clear the activity floor in step 6."
```

## Ambiguities I had to resolve, and the reading I chose

1. **Path 2 step 6 requires an interactive Claude Code session** ("Open Claude Code in any project, and type: `/brothermode ...`"). This directly contradicts the page's own stated reason for choosing Path 2 in the first place: "If nothing is going to type an interactive `/plugin` command for you ... use Path 2." I am a non-interactive Bash-driven probe with no way to open a fresh interactive Claude Code session inside the throwaway HOME and type a slash command into it. I did not fabricate this step or its output. I recorded it as not performed, and I let step 7 run anyway to show the honest, expected consequence (missing file), which itself matches the page's own documented failure mode for a skipped step 6. I read this as a finding about the page, not something the brief told me to solve: Path 2 promises no interactive session is needed, but its own last content step requires one.

2. **"Run the project's own health check ... from a neutral directory."** I read "neutral" as: not inside the installed copy itself, and not inside any real project directory on this machine. I used a bare empty directory (`$ROOT/neutral`) created solely for this purpose, containing no prior BrotherMode state of any kind.

3. **"One real command run through the installed copy with its output quoted."** The brief did not name a specific command. I chose `python3 tools/bm_project_facts.py --field install_target_tag`, because the page itself names this exact command as the source of truth for the clone tag in step 1, so running it closes the loop: it lets me confirm the tag I actually cloned (`v2.0.0-rc.13`) is the same one the installed copy's own tooling says it should be.

## Findings against the page's stated expectations (beyond the isolation incident)

- **Clone output, step 1**: the page's "Expected" text says git output ends in something like `Resolving deltas: 100% (N/N), done.` My clone's output had no such line at all; it ended in the detached-HEAD advisory text after the annotated-tag warning. This may be a `--depth 1` / git-version difference rather than a defect, but it does not match what the page describes.
- **Real install.py run, step 3**: the page's "Expected" text lists three things: the six-hook list, "a line naming the backup of your previous settings," and a closing line reading exactly `smoke: the fence hook ran end to end and exited 0`. My actual output had no line anywhere naming a settings backup (there was nothing to back up on a fresh throwaway HOME, which the page does not qualify), and the smoke line was not the closing line of the output — it was followed by a second smoke-related line and then the full "Installed:" and "Still manual" sections.
- **Pre-setup doctor.py, step 3's own verification**: the page says "Checks 4, 5 and 8 SKIP until setup has run ... that is expected on a machine that just finished Step 3 above." My run showed check 4 ("setup has been completed") as FAIL, not SKIP, with checks 5 and 8 correctly SKIP. The page's wording implies all three SKIP at this stage; one of the three actually FAILs.
- **bm_score.py, step 5**: the page says "One check, `budget-vs-tier`, can show a `FAIL` that names `STATE.md`." My run showed two checks failing and naming STATE.md: `fence-hygiene` and `budget-vs-tier`. The page names only one.
- **doctor.py's printed settings path is redacted**: every doctor.py run displayed `settings: /Users/.../.claude/settings.json` and similar `/Users/.../` redactions inside PASS/FAIL lines, rather than the real throwaway path. This did not affect correctness of the verdicts, just noting it as a display quirk, not a page-accuracy finding.

## verify-install.sh result

```
verify-install: checked against /private/tmp/bm-probe-p3c/home/.claude/skills/brothermode/CHECKSUMS.sha256
verify-install: 235 file(s) match, 0 mismatched, 0 missing, 0 wrong type, 0 extra (present on disk, absent from the manifest)
verify-install: PASSED. Every entry the manifest names matches on disk,
verify-install: in content and in type, and no entry exists on disk that
verify-install: the manifest does not name.
verify-install: this does not prove the manifest itself is authentic; it proves your files match whatever manifest you pointed this at. Get the manifest from the release you trust (the tag's git history, or a release asset), not from the same untrusted channel as the code.
```

Exit code: 0.

## One real command through the installed copy

```
$ cd /private/tmp/bm-probe-p3c/home/.claude/skills/brothermode && python3 tools/bm_project_facts.py --field install_target_tag
v2.0.0-rc.13
```

Exit code: 0. Matches the tag used in the step-1 clone command, confirming the page's claim that this field drives that command rather than a hand-typed value.

## Summary of what is and is not verified

- Verified with a command run after the fact: clone, install.py dry-run and real run, settings.json validity, vault copy and Home.md presence, setup.py, the corrected doctor.py run (0 FAIL), bm_score.py, verify-install.sh, and the bm_project_facts.py check.
- Not verified, and not fabricated: bm_sessionstart.sh (blocked by the sandbox classifier, both attempts), Path 2 step 6 (needs an interactive Claude Code session I do not have), and by extension step 7's real content (only the expected-missing-file path was confirmed, not a populated telemetry line).
- Self-reported incident: an isolation mistake on my part (cwd not persisting across separate Bash calls) let one command run against the founder's real BrotherSBE project directory instead of the throwaway neutral directory, touching the mtime of `.brothermode/store.sqlite3-shm` there (a SQLite WAL sidecar file, not the database itself) with no data write and no git-visible change. Corrected for the rest of the run by putting `cd` and the command in the same shell invocation every time afterward.
