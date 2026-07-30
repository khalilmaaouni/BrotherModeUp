# Release evidence, 2.0.0-rc.7

Status: CURRENT as of 2026-07-31.

Every claim here names the immutable identifier it rests on. Where a thing was not
executed, it says so instead of leaving the gap for a reader to discover.

## Identity

| Fact | Value |
|---|---|
| Tag | `v2.0.0-rc.7`, annotated |
| Tag object | `48168e31f193` (annotated) |
| Commit | `d6c70b3e9e5040255512606e7d948e97d6358816` |
| Branch | `main`, remote equals local at cut time (`0 0` ahead/behind) |
| `VERSION` | `2.0.0-rc.7` |
| `pyproject.toml` | `2.0.0rc7` (PEP 440 spelling of the same release) |
| Checksum manifest | 156 entries, regenerated last, after every other edit |
| Supersedes | `v2.0.0-rc.6` (superseded, not withdrawn: sound, but tagged before the Windows fix) and `v2.0.0-rc.5` (WITHDRAWN, see below) |

## Local gate, run after the last edit

```
python3 tools/test_all.py
test_all: 1194 tests across 7 suites, 1 skipped, 321.9s wall. ALL GREEN
exit 0
```

Run with the tag already published, so the release-truth tests that SKIP while no
tag exists were ACTIVE for this run. That is why the skip count is 1 rather than the
4 seen on the release-cut commit itself.

## Clean install from the published tag, executed against rc.7

```
git clone --branch v2.0.0-rc.7 --depth 1 https://github.com/khalilmaaouni/BrotherModeUp.git
cat VERSION                  -> 2.0.0-rc.7
sh scripts/verify-install.sh -> 158 file(s) match, 0 mismatched, 0 missing,
                                0 wrong type, 0 extra
```

`verify-install` reports every manifest entry matching on disk in content and type,
and no file on disk that the manifest does not name. Executed against a fresh clone
of the public tag, not against the working tree.

## GitHub Actions: GREEN on all nine jobs, after a real defect was found and fixed

Run `30566158154` for commit `d6c70b3`, the EXACT commit `v2.0.0-rc.7` points at,
conclusion **success**. The tagged bytes and the green run are the same bytes, which
is the whole reason this cut exists. Run `30564943060` on `f751f9f` was the first
green run and carried the same nine jobs.

| Job | Result |
|---|---|
| `gate` (the serial full gate) | success |
| `suite (ubuntu-latest)`, `suite (macos-latest)` | success |
| `store (ubuntu-latest, 3.9 and 3.x)` | success |
| `store (macos-latest, 3.9 and 3.x)` | success |
| `store (windows-latest, 3.9 and 3.x)` | success |

This is the first fully green run this project has evidence for, and getting
there is the part worth reading.

**The Windows legs had been failing and nobody could see why.** Red in three
runs checked (`30511349840` on `2611236`, `30558980744` on `f66e48f`,
`30560704272` on `ea006c0`), the earliest predating this work. Public
annotations carried only `Process completed with exit code 1`; the run log names
the failing test and reading it needs an authenticated `gh`, which is
founder-only here. The machine able to fix the defect could not read its reason.

**`.github/run_with_annotations.py` closed that gap and paid for itself in one
run.** It re-emits unittest `FAIL:` and `ERROR:` headers as GitHub annotations,
which a public repository serves to an anonymous caller. Its first live run named
both failures with no credentials at all:

```
FAIL: test_gate4_missing_state_md_remedy_names_an_absolute_resolvable_path
FAIL: test_a_checkout_is_told_its_own_absolute_path
```

**They were pointing at a real defect in shipped instruction text, not at
themselves.** `invocation()` quoted every user-facing command with
`shlex.quote`, which is POSIX-only. A Windows path is full of backslashes, none
in shlex's safe set, so the path came back in SINGLE quotes and the remedy read
`python3 'C:\Users\...\bm_store.py'`, which neither cmd.exe nor PowerShell
runs. Every instruction in `bm_docs`, `bm_packs` and `bm_learn` flows through
that function, so one wrong quoting rule broke all of them on one platform.
Fixed in `_quote_path_for_local_shell`: POSIX keeps shlex, Windows gets double
quotes and only when the path contains a space.

The three tests added assert the property on EVERY platform (strip the
platform's own quoting and an absolute path must remain), so a POSIX box catches
a future regression too. One neighbouring test had been passing on Windows for
the wrong reason and is now platform-aware.

## What this release does NOT prove

- **Failure-artifact behaviour has not been demonstrated** by deliberately breaking
  a build on a temporary branch and watching the upload path. Loop 6 asks for that
  and it has not been done. What HAS been demonstrated is the annotation path, on a
  genuine failure rather than a seeded one.
- **Green today is not green forever.** Nine jobs passed on one commit. The Windows
  fix was verified by CI, not on a Windows machine here, so a Windows-specific
  regression would still be caught only after a push.
- **No dogfood window.** Loop 7 is untouched: BrotherMode has never run across the
  founder's real work for 20 working days or 100 substantial tasks.
- **No outside-family audit.** Everything was reviewed by the same model family that
  wrote it.
- **No external beta.** No outside founder has installed this.
- **No published benchmark** for this cut.

## Why rc.6 was superseded rather than kept

rc.6 is sound: its manifest describes its tree and a clean install verifies. It was
tagged at `ea006c0`, two commits before the POSIX-only shell quoting was fixed, so
the TAGGED tree still had red Windows CI while `main` went green. A release whose
tag and whose green CI run are different bytes cannot honestly point at that run as
its evidence, which is the whole reason Loop 6 exists. rc.6 is superseded, not
withdrawn: nothing in it is wrong, it is simply not the thing the evidence describes.

## The withdrawal of rc.5, recorded because it is the most useful thing here

`v2.0.0-rc.5` was tagged, pushed, and withdrawn about fifteen minutes later. Its
`CHECKSUMS.sha256` omitted eight shipped files, among them `tools/bm_docs.py`,
`tools/bm_docs_export.py` and `tools/bm_packs.py`, so `verify-install.sh` against
that tag reports three real tools as unknown files.

Cause, stated plainly: the release-cut session ran `scripts/checksums.sh` with its
output redirected to `/dev/null` instead of passing the documented output path. The
manifest was never rewritten, and that commit's message claimed it had been.

Caught by `test_the_checksum_manifest_matches_the_tagged_tree`, written the same
morning, which skipped with a stated reason while no tag existed, became mandatory
the instant a tag was pushed, failed on its first live run against a real tag, and
named all eight files. The tag object stays on the remote: withdrawal is a
statement, not a deletion.
