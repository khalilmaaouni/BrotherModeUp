#!/bin/sh
# checksums.sh: a deterministic SHA256 manifest of every shipped file.
#
# Why this exists: docs/RELEASE.md explains the security problem it answers
# ("how do I know what I installed"). The install instruction clones a git
# branch or tag into a location whose code runs automatically on every
# Claude Code session (the hooks in ~/.claude/settings.json). This script is
# the maintainer-side half of the answer: it lists every file that ships in
# a release and its SHA256 hash, in a fixed order, so the same source tree
# always produces the same manifest byte for byte. verify-install.sh is the
# user-side half: it re-hashes an installed copy and compares against a
# manifest this script produced.
#
# POSIX sh only, no bashisms: no arrays, no [[ ]], no local, no process
# substitution, no here-strings. Every construct used here (command
# substitution, case, for/while with IFS, plain shell functions) is in
# POSIX.1-2017 section 2, and this has been run directly under both bash
# and dash to confirm neither rejects it.
#
# Usage, always from the repository root:
#   scripts/checksums.sh                    # print the manifest to stdout
#   scripts/checksums.sh CHECKSUMS.sha256   # write it to that file instead
#
# "Shipped file" is defined as: every file git tracks in this repository at
# the commit being released. That is deliberate, not lazy: it is exactly
# the set of bytes a `git clone` (or `git checkout <tag>`) hands a user, so
# the manifest and the install are talking about the same tree by
# construction, and it can never drift from .gitignore because it does not
# reimplement .gitignore's rules. If this is ever run against a tree copied
# without its .git directory, it falls back to a plain filesystem walk with
# the same exclusions .gitignore already documents (STATE.md, threads/,
# __pycache__/, .DS_Store, *.bak*, .superpowers/) plus this repo's own
# machine state (.brothermode/).

set -e

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
cd "$ROOT"

OUT_FILE="$1"

# --- pick a SHA256 tool: Linux ships sha256sum, macOS ships shasum -a 256.
# Detect, never assume: a machine with coreutils installed via Homebrew can
# have both, and a minimal container can have neither.
if command -v sha256sum >/dev/null 2>&1; then
    hash_file() { sha256sum "$1"; }
elif command -v shasum >/dev/null 2>&1; then
    hash_file() { shasum -a 256 "$1"; }
else
    echo "checksums.sh: neither sha256sum nor shasum is on PATH; cannot hash anything" >&2
    exit 1
fi

WORKDIR=$(mktemp -d 2>/dev/null || echo "/tmp/bm-checksums-work.$$")
mkdir -p "$WORKDIR"
trap 'rm -rf "$WORKDIR"' EXIT INT TERM

# --- build the file list, git-tracked files preferred (see header comment).
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git ls-files > "$WORKDIR/filelist"
else
    find . -type f \
        ! -path './.git/*' \
        ! -path './.brothermode/*' \
        ! -path '*/__pycache__/*' \
        ! -path './threads/*' \
        ! -path './.superpowers/*' \
        ! -name '.DS_Store' \
        ! -name '*.bak*' \
        ! -name 'STATE.md' \
        | sed 's|^\./||' > "$WORKDIR/filelist"
fi

# Never hash the manifest into itself. OUT_FILE, when given, is documented
# above as a path relative to the repository root (the common, supported
# case); strip a leading "./" the same way the fallback file list already
# does, so a re-run after a previous release's manifest is already
# committed does not fold that file's own bytes into the new one.
if [ -n "$OUT_FILE" ]; then
    OUT_FILE_NORMALIZED=$(printf '%s' "$OUT_FILE" | sed 's|^\./||')
    grep -v -x -F "$OUT_FILE_NORMALIZED" "$WORKDIR/filelist" > "$WORKDIR/filelist.filtered" || true
    mv "$WORKDIR/filelist.filtered" "$WORKDIR/filelist"
fi

# Deterministic order regardless of the machine's locale.
LC_ALL=C sort "$WORKDIR/filelist" > "$WORKDIR/sorted"

COUNT=0
while IFS= read -r f; do
    [ -z "$f" ] && continue
    [ -f "$f" ] || continue
    hash_file "$f" >> "$WORKDIR/manifest"
    COUNT=$((COUNT + 1))
done < "$WORKDIR/sorted"

if [ -n "$OUT_FILE" ]; then
    cp "$WORKDIR/manifest" "$OUT_FILE"
    echo "checksums.sh: wrote $COUNT file hash(es) to $OUT_FILE" >&2
else
    cat "$WORKDIR/manifest"
    echo "checksums.sh: $COUNT file(s) hashed" >&2
fi
