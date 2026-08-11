# Handback: two BrotherSBE doc changes, made but deliberately not committed

Status: CURRENT, ACTION NEEDED BY WHOEVER OWNS BrotherSBE

Written 2026-08-12 02:45 JST by the BrotherModeUp night session.

## What was changed, and where it is right now

Two files in `~/Documents/BrotherSBE` were edited and left UNCOMMITTED in that
repository's working tree:

- `README.md` line 40, install pinned to `khalilmaaouni/BrotherSBE@v3.1.0`
- `TESTERS.md` line 33, the same, with a sentence to testers explaining why

The change is also saved here as a patch, so it survives even if that working
tree is reset:

    docs/evidence/tester-pack/brothersbe-pin-install-to-tag.patch

Apply it with, from the BrotherSBE root:

```bash
git apply /Users/khalil.maaouni/Documents/BrotherModeUp/docs/evidence/tester-pack/brothersbe-pin-install-to-tag.patch
```

## Why it matters

BrotherModeUp's install card and tester pack both tell testers to pin BOTH
products to a released tag, and BrotherMode's own documented install already
does (`khalilmaaouni/BrotherModeUp@v3.2.0`). BrotherSBE's documented install
did not, so the install card's central promise, that everybody runs the same
thing, held for one product and not the other. During a pilot that is not
cosmetic: two testers on different commits of the same tool make a bug and a
version difference look identical, and the whole point of the pilot week is
comparing what different people hit.

Both tags were verified against their remotes on 2026-08-12:
BrotherMode `v3.2.0` at `960bd4f8`, BrotherSBE `v3.1.0` at `c48ac46b`, local
and remote agreeing in each case
(`docs/evidence/tester-pack/CHECKED-2026-08-12.md`).

## Why it was NOT committed, stated as a decision rather than an omission

Three reasons, in order of weight:

1. **Another session is actively working that repository.** Its HEAD moved
   from `a6cda75` to `f728da8` during this session, and that newest commit is
   literally "Reseal the manifest from committed state, not the working tree".
2. **Both files are covered by that repository's `CHECKSUMS.sha256`.**
   Committing them without regenerating the manifest leaves its own doctor
   integrity check failing. Regenerating it would land directly on top of the
   manifest work that other session had just finished, which is the collision
   the one-writer law exists to prevent.
3. **It is not this repository's file to own.** A cross-repository commit made
   at 02:45 by a session whose fence covers neither file is exactly the shape
   of change that gets discovered later rather than reviewed.

## What the owner needs to do

Apply the patch (or make the one-line edit by hand), then follow that
repository's own manifest rule: `git add` first, regenerate `CHECKSUMS.sha256`
last, then commit. Nothing else in this handback needs doing.

## What is NOT claimed

The pinned command was never executed. Nobody has run
`claude plugin marketplace add khalilmaaouni/BrotherSBE@v3.1.0` on a machine
without the plugin already installed. What was verified is that the tag exists
on the remote and resolves to `c48ac46b`. That the pinned form installs
cleanly on a cold machine is UNVERIFIED, and it is the same unmeasured number
the tester pack exists to measure.
