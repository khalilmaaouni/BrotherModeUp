# Release evidence, 2.0.0-rc.6

Status: CURRENT as of 2026-07-31.

Every claim here names the immutable identifier it rests on. Where a thing was not
executed, it says so instead of leaving the gap for a reader to discover.

## Identity

| Fact | Value |
|---|---|
| Tag | `v2.0.0-rc.6`, annotated |
| Tag object | `1c30d7877bb61dde05e41913c494aacfada0ffb2` |
| Commit | `ea006c0ab05e18945df140fce82ad7715242300f` |
| Branch | `main`, remote equals local at cut time (`0 0` ahead/behind) |
| `VERSION` | `2.0.0-rc.6` |
| `pyproject.toml` | `2.0.0rc6` (PEP 440 spelling of the same release) |
| Checksum manifest | 156 entries, regenerated last, after every other edit |
| Supersedes | `v2.0.0-rc.5`, WITHDRAWN the same day (see below) |

## Local gate, run after the last edit

```
python3 tools/test_all.py
test_all: 1194 tests across 7 suites, 1 skipped, 321.9s wall. ALL GREEN
exit 0
```

Run with the tag already published, so the release-truth tests that SKIP while no
tag exists were ACTIVE for this run. That is why the skip count is 1 rather than the
4 seen on the release-cut commit itself.

## Clean install from the published tag

```
git clone --branch v2.0.0-rc.6 --depth 1 https://github.com/khalilmaaouni/BrotherModeUp.git
cat VERSION                  -> 2.0.0-rc.6
sh scripts/verify-install.sh -> PASSED
```

`verify-install` reports every manifest entry matching on disk in content and type,
and no file on disk that the manifest does not name. Executed against a fresh clone
of the public tag, not against the working tree.

## GitHub Actions, the honest state: PARTIALLY RED

Run `30560704272` for commit `ea006c0`, workflow `tests`.

| Job | Result |
|---|---|
| `gate` (the serial full gate, ubuntu) | **success** |
| `suite (ubuntu-latest)` | success |
| `suite (macos-latest)` | success |
| `store (ubuntu-latest, 3.9 and 3.x)` | success |
| `store (macos-latest, 3.9 and 3.x)` | success |
| `store (windows-latest, 3.9)` | **FAILURE** |
| `store (windows-latest, 3.x)` | **FAILURE** |

**The Windows store legs fail.** Checked in three runs, the same two legs red in all
three: `30511349840` (commit `2611236`), `30558980744` (`f66e48f`), `30560704272`
(`ea006c0`), spanning 2026-07-30T03:30Z to 2026-07-31T16:16Z. Earlier runs were not
inspected, so "always" is not claimed; three consecutive runs is what was checked.
The earliest of the three predates the 2026-07-31 work, so this is a pre-existing
defect and not a regression introduced by the first-rank loops.

**The cause is not yet known, and guessing it here would be worse than saying so.**
The public annotations carry only `Process completed with exit code 1`. The run log
would name the failing test, but downloading it needs an authenticated `gh`, and
credentials in this project are founder-only, so the machine able to fix the defect
cannot currently read the reason.

**What changed because of that.** `.github/run_with_annotations.py` now wraps the
Windows-covered suites. It re-emits unittest `FAIL:` and `ERROR:` headers as GitHub
annotations, and a public repository serves annotations to an anonymous caller, so
the NEXT red run names its own failing tests with no login. Verified locally on both
paths: silent with exit 0 on a passing suite, and on a seeded failing suite it
emitted one annotation per failing test and forwarded exit 1 unchanged.

## What this release does NOT prove

- **Windows is not green.** Any claim that CI passes on three platforms is false as
  of this cut, and the two documents that said so have been corrected rather than
  left standing.
- **Failure-artifact behaviour has not been demonstrated** by deliberately breaking
  a build on a temporary branch. Loop 6 asks for that and it has not been done.
- **No dogfood window.** Loop 7 is untouched: BrotherMode has never run across the
  founder's real work for 20 working days or 100 substantial tasks.
- **No outside-family audit.** Everything was reviewed by the same model family that
  wrote it.
- **No external beta.** No outside founder has installed this.
- **No published benchmark** for this cut.

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
