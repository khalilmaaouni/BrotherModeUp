#!/bin/sh
# verify-install.sh: does an installed copy of this repository match a
# published checksum manifest, byte for byte?
#
# This is the direct answer to "how do I know what I installed". The
# install instruction (docs/RELEASE.md, README.md) clones a git ref into
# ~/.claude/skills/brothermode, and that code then runs automatically on
# every Claude Code session via hooks. A manifest you cannot check against
# is not a security control, it is a claim; this script is the check.
#
# POSIX sh only, no bashisms, same portability intent as checksums.sh: run
# directly under both bash and dash to confirm neither rejects it. Uses no
# git commands itself, on purpose: it only ever reads the manifest and
# re-hashes the files it names, so it works identically on a plain
# directory copy (no .git present) and on a real clone.
#
# Usage:
#   scripts/verify-install.sh [manifest-file] [installed-dir]
#
#   manifest-file  defaults to <installed-dir>/CHECKSUMS.sha256
#   installed-dir  defaults to this script's own parent repository root
#
# Typical use: you cloned a tagged release into
# ~/.claude/skills/brothermode. The release ships CHECKSUMS.sha256 at the
# repository root (docs/RELEASE.md, step "cut the release", explains how a
# maintainer produces it with checksums.sh). Run this with no arguments
# from inside that clone, or point it at any two directories explicitly:
#
#   scripts/verify-install.sh
#   scripts/verify-install.sh /path/to/CHECKSUMS.sha256 ~/.claude/skills/brothermode

set -e

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
DEFAULT_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)

TARGET="${2:-$DEFAULT_ROOT}"
MANIFEST="${1:-$TARGET/CHECKSUMS.sha256}"

if [ ! -f "$MANIFEST" ]; then
    echo "verify-install: no manifest found at $MANIFEST" >&2
    echo "verify-install: a maintainer generates one with scripts/checksums.sh" \
         "as part of cutting a release (see docs/RELEASE.md); if this repo" \
         "predates that (no tagged release exists yet as of this writing)," \
         "there is nothing to verify against." >&2
    exit 2
fi

if command -v sha256sum >/dev/null 2>&1; then
    hash_file() { sha256sum "$1" | cut -c1-64; }
elif command -v shasum >/dev/null 2>&1; then
    hash_file() { shasum -a 256 "$1" | cut -c1-64; }
else
    echo "verify-install: neither sha256sum nor shasum is on PATH; cannot check anything" >&2
    exit 1
fi

WORKDIR=$(mktemp -d 2>/dev/null || echo "/tmp/bm-verify-install-work.$$")
mkdir -p "$WORKDIR"
trap 'rm -rf "$WORKDIR"' EXIT INT TERM

OK=0
MISMATCHED=0
MISSING=0
TYPESWAPPED=0
: > "$WORKDIR/manifest_paths"

# Manifest lines are "<64 hex chars><two spaces><path>", the format both
# sha256sum and shasum -a 256 produce. Splitting by fixed column position
# (not by whitespace) is deliberate: a path may itself contain spaces, and
# field-splitting would cut it apart.
while IFS= read -r line; do
    [ -z "$line" ] && continue
    expected=$(printf '%s' "$line" | cut -c1-64)
    path=$(printf '%s' "$line" | cut -c67-)
    [ -z "$path" ] && continue
    printf '%s\n' "$path" >> "$WORKDIR/manifest_paths"
    full="$TARGET/$path"
    # FINDING 4 (2026-07-27): check the entry TYPE, by lstat, before hashing
    # anything. scripts/checksums.sh refuses to manifest anything that is not
    # a regular file, so every path named here is attested to BE a regular
    # file; that is the manifest's type claim and this is where it is
    # enforced. It matters because `-f` follows symlinks: a regular file
    # swapped on disk for a symlink pointing at an attacker's copy of the
    # same bytes used to hash equal and be reported as a match. `-L` is the
    # only test that sees the link rather than its target, so it goes first,
    # and a broken symlink (where -e is false) is caught here too rather than
    # being misreported as merely MISSING.
    if [ -L "$full" ]; then
        echo "TYPESWAP:  $path (a symlink on disk, but the manifest attests a regular file)"
        TYPESWAPPED=$((TYPESWAPPED + 1))
        continue
    fi
    if [ ! -e "$full" ]; then
        echo "MISSING:   $path"
        MISSING=$((MISSING + 1))
        continue
    fi
    if [ ! -f "$full" ]; then
        echo "TYPESWAP:  $path (not a regular file on disk, but the manifest attests one)"
        TYPESWAPPED=$((TYPESWAPPED + 1))
        continue
    fi
    actual=$(hash_file "$full")
    if [ "$actual" = "$expected" ]; then
        OK=$((OK + 1))
    else
        echo "MISMATCH:  $path"
        MISMATCHED=$((MISMATCHED + 1))
    fi
done < "$MANIFEST"

# Second direction of the check. The loop above only asks "does every file
# the manifest NAMES match on disk", which never notices a file that was
# ADDED (an extra file is neither a MISMATCH nor a MISSING), so this script
# used to report PASSED with a planted extra file still present; see
# docs/superpowers/specs/2026-07-26-final-blockers.md, BLOCKER 2, for the
# reproduction that motivated this second pass. It asks the other
# direction instead: does every file that actually EXISTS on disk appear
# in the manifest. The exclusion list below is the same one
# scripts/checksums.sh already applies when it cannot use git (kept in
# sync by comment in both files, since each script is self-contained POSIX
# sh with no shared file to hold this list once): machine state and
# generated files this project's own .gitignore already keeps out of what
# git tracks, so their absence from the manifest is expected, not an added
# file. Stated limit: if $TARGET itself contains a character `find -path`
# treats as glob syntax (*, ?, [ ]), the exclusions below can under- or
# over-match; named here rather than silently assumed correct.
MANIFEST_ABS=$(cd "$(dirname "$MANIFEST")" && pwd)/$(basename "$MANIFEST")
MANIFEST_REL=$(printf '%s\n' "$MANIFEST_ABS" | sed "s|^$TARGET/||")

#
# FINDING 4 (2026-07-27): this enumeration used to say `-type f`, and that
# one flag was a hole straight through the whole check. POSIX find without
# -L does not follow symlinks, so a symlink is -type l and NEVER matches
# -type f: an unmanifested symlink was invisible to this loop, and invisible
# to the manifest loop above too, because the manifest by definition never
# named it. The attack that exercised it: plant tools/json.py as a symlink to
# an attacker-controlled file, and this script prints PASSED and exits 0,
# while every session hook that runs `python3 tools/bm_telemetry.py` loads
# the attacker's module first, because Python puts the script's own directory
# at the front of sys.path and shadowing the standard library from there is
# trivial. Reproduced end to end before the fix (exit 0, nothing reported).
#
# `! -type d` is the fix: it enumerates EVERY non-directory entry, which is
# regular files, symlinks (including symlinks that point at directories,
# which are type l and not type d), devices, FIFOs and sockets. Real
# directories are the only thing left out, and a real directory is inert
# here: it holds no bytes of its own, nothing executes it, and anything
# inside it is enumerated on its own account. The excluded roots are now
# also matched as bare names, not only as "<root>/*" prefixes, because a
# symlink NAMED .brothermode or threads was previously skipped for free by
# -type f and would otherwise walk right back in through the exclusion list.
# find is not asked to descend through any link (no -L, deliberately), so
# nothing below a planted link is traversed or trusted.
find "$TARGET" ! -type d \
    ! -path "$TARGET/.git" \
    ! -path "$TARGET/.git/*" \
    ! -path "$TARGET/.brothermode" \
    ! -path "$TARGET/.brothermode/*" \
    ! -path '*/__pycache__/*' \
    ! -path "$TARGET/threads" \
    ! -path "$TARGET/threads/*" \
    ! -path "$TARGET/.superpowers" \
    ! -path "$TARGET/.superpowers/*" \
    ! -path "$TARGET/Documentation" \
    ! -path "$TARGET/Documentation/*" \
    ! -path "$TARGET/.claude" \
    ! -path "$TARGET/.claude/*" \
    ! -name '.DS_Store' \
    ! -name '*.bak*' \
    ! -name 'STATE.md' \
    > "$WORKDIR/installed_raw"

EXTRA=0
while IFS= read -r full; do
    [ -z "$full" ] && continue
    rel=$(printf '%s\n' "$full" | sed "s|^$TARGET/||")
    [ "$rel" = "$MANIFEST_REL" ] && continue
    if grep -q -x -F "$rel" "$WORKDIR/manifest_paths"; then
        continue
    fi
    # Name the type, by lstat, so the report distinguishes an unexpected but
    # ordinary file from a planted link or device. -L comes first for the
    # usual reason: it is the only test that reports on the entry rather than
    # on whatever the entry points at.
    if [ -L "$full" ]; then
        echo "EXTRA (symlink): $rel"
    elif [ -f "$full" ]; then
        echo "EXTRA:     $rel"
    else
        echo "EXTRA (irregular): $rel"
    fi
    EXTRA=$((EXTRA + 1))
done < "$WORKDIR/installed_raw"

echo ""
echo "verify-install: checked against $MANIFEST"
echo "verify-install: $OK file(s) match, $MISMATCHED mismatched, $MISSING missing, $TYPESWAPPED wrong type, $EXTRA extra (present on disk, absent from the manifest)"

if [ "$MISMATCHED" -gt 0 ] || [ "$MISSING" -gt 0 ] || [ "$TYPESWAPPED" -gt 0 ] || [ "$EXTRA" -gt 0 ]; then
    echo "verify-install: FAILED. Do not trust this installed copy until you" \
         "understand why the entries above differ from the published manifest." >&2
    if [ "$EXTRA" -gt 0 ]; then
        echo "verify-install: an EXTRA entry is exactly the shape of a" \
             "planted backdoor: it runs automatically along with everything" \
             "else in this installation, and the manifest says nothing" \
             "about it because nothing here declared it. A symlink is the" \
             "sharpest version of that: it can drop attacker-controlled code" \
             "into a directory that is already on Python's import path." >&2
    fi
    if [ "$TYPESWAPPED" -gt 0 ]; then
        echo "verify-install: a TYPESWAP entry means the manifest attests a" \
             "regular file at that path but something else is there now," \
             "typically a symlink pointing somewhere outside this install." \
             "Content hashes cannot catch that on their own, because the hash" \
             "of a link's target can be made to match perfectly." >&2
    fi
    exit 1
fi

echo "verify-install: PASSED. Every entry the manifest names matches on disk,"
echo "verify-install: in content and in type, and no entry exists on disk that"
echo "verify-install: the manifest does not name."
echo "verify-install: this does not prove the manifest itself is authentic;" \
     "it proves your files match whatever manifest you pointed this at. Get" \
     "the manifest from the release you trust (the tag's git history, or a" \
     "release asset), not from the same untrusted channel as the code."
