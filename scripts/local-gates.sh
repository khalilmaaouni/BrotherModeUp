#!/bin/bash
# Run this repository's real gate locally and report the result to GitHub as a
# commit status. The sibling of the same script in BrotherSBE, deliberately.
#
# WHY. GitHub Actions is disabled across this estate by founder law of
# 2026-08-16, after an eleven job matrix across macOS and Windows consumed a
# free month of minutes in two weeks. The verification never needed a cloud.
# Only the REPORTING of it did. This runs the gate where it always ran and
# posts what it observed.
#
# THE GATE IS THIS PROJECT'S OWN, not a copy of one. CLAUDE.md documents
# `python3 tools/test_all.py` as the full battery, 8 to 13 minutes, and warns
# that backgrounding it as a harness task dies at exit 144 with no verdict.
# This script runs it in the foreground and waits, which is the shape that
# works.
#
# USAGE
#   scripts/local-gates.sh            run the gate, post the status
#   scripts/local-gates.sh --no-post  run the gate, report locally only
#
# EXIT 0 only when the battery itself exited 0 AND printed its ALL GREEN line.
set -u
set -o pipefail

cd "$(dirname "$0")/.." || exit 2
REPO="khalilmaaouni/BrotherModeUp"
POST=1
[ "${1:-}" = "--no-post" ] && POST=0

# Tracked modifications only: untracked files do not change what the commit
# under test contains. A battery run against a tree still being edited
# produces confident wrong signals, which this project has recorded happening
# four times in one night.
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  echo "REFUSED: tracked files are modified. Nothing ran and nothing was posted."
  exit 2
fi
SHA="$(git rev-parse HEAD)"
LOG="${TMPDIR:-/tmp}/bm-local-gates-${SHA:0:12}.log"

# One suite at a time is a standing cap in this project, and two batteries in
# one tree produce false failures in both.
if pgrep -f "tools/test_all.py" > /dev/null 2>&1; then
  echo "REFUSED: a battery is already running in this tree. One suite at a time."
  exit 2
fi

echo "gate: python3 tools/test_all.py"
echo "sha:  $SHA"
echo "log:  $LOG"
START=$SECONDS
BROTHERMODE_SESSION_CAP=99 python3 tools/test_all.py > "$LOG" 2>&1
CODE=$?
DURATION=$((SECONDS - START))

# Two conditions, not one. An exit code alone has been wrong here before: the
# battery refuses to report green when a suite writes into the checkout, and
# that refusal is a nonzero exit with every suite passing. Requiring the
# ALL GREEN line as well means the status says what the battery said.
GREEN=0
grep -q "ALL GREEN" "$LOG" && GREEN=1
SUMMARY="$(grep -E '^test_all: [0-9]+ tests' "$LOG" | tail -1 | cut -c1-90)"
[ -z "$SUMMARY" ] && SUMMARY="no summary line found in the log"

if [ "$CODE" -eq 0 ] && [ "$GREEN" -eq 1 ]; then
  STATE="success"
  DESC="${SUMMARY}, ${DURATION}s, $(uname -sm), run locally"
  echo "RESULT: green. $SUMMARY"
else
  STATE="failure"
  DESC="exit ${CODE}, ALL GREEN line present=${GREEN}. ${SUMMARY}"
  echo "RESULT: NOT green. exit $CODE, ALL GREEN present=$GREEN"
fi

if [ "$(git rev-parse HEAD)" != "$SHA" ]; then
  echo "REFUSED to post: HEAD moved during the run. The result describes $SHA."
  exit 2
fi
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  echo "REFUSED to post: the run modified tracked files, so the result no"
  echo "longer describes a committed state."
  exit 2
fi

if [ "$POST" = 0 ]; then
  echo "(--no-post) nothing sent to GitHub."
  [ "$STATE" = "success" ]
  exit $?
fi

gh api -X POST "repos/$REPO/statuses/$SHA" \
  -f state="$STATE" -f context="local-gates" -f description="$DESC" > /dev/null \
  && echo "posted local-gates=$STATE against $SHA" \
  || { echo "POST FAILED: the result above still stands, it just was not reported."; exit 2; }

[ "$STATE" = "success" ]
