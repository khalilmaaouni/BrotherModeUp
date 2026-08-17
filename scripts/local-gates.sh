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

# --- refuse a tree carrying an interpreter poison ---------------------------
# The tracked-file guard above cannot see this class, because the files are
# UNTRACKED and it deliberately ignores untracked files. Demonstrated on the
# sibling repository 2026-08-17, not reasoned about: a sitecustomize.py holding
# `os._exit(0)`, anywhere Python will import it from, makes every python3
# process exit 0 before running a line of the code under test. The measurement
# was zero bytes of output and exit 0 from a suite that normally prints and
# passes. Python imports sitecustomize and usercustomize automatically at
# startup, and a .pth file in a site directory executes any line beginning
# `import`, so all three are refused here rather than merely stripped from the
# environment: PYTHONPATH is stripped below, but a poison file sitting in the
# CHECKOUT ITSELF is on sys.path regardless of PYTHONPATH.
POISON="$(find . -maxdepth 2 \( -name sitecustomize.py -o -name usercustomize.py -o -name '*.pth' \) \
          -not -path './.git/*' 2>/dev/null | head -5)"
if [ -n "$POISON" ]; then
  echo "REFUSED: the tree carries interpreter startup files, which run before"
  echo "any code under test and can force a green battery:"
  echo "$POISON" | sed 's/^/  /'
  echo "Remove them, or if one is legitimate, name it in scripts/gates.env's"
  echo "comments and narrow this check deliberately."
  exit 2
fi

# --- build the battery's environment from a committed file ------------------
# DECLARED, NOT INHERITED. Until 2026-08-17 this ran with whatever the invoking
# shell held, so the verdict of the required status was a function of (commit,
# operator) and nothing recorded the operator half. scripts/gates.env carries
# the whole policy and its reasoning. PATH, HOME, TMPDIR and the locale are
# inherited on purpose and recorded in the receipt: they identify the machine,
# which this design declares rather than reproduces.
ENV_FILE="scripts/gates.env"
if [ ! -f "$ENV_FILE" ]; then
  echo "REFUSED: $ENV_FILE is missing, so the battery's environment is undeclared."
  echo "A verdict from an undeclared environment is a fact about this shell, not"
  echo "about the commit."
  exit 2
fi
GATE_ENV=(PATH="$PATH" HOME="$HOME" TMPDIR="${TMPDIR:-/tmp}" LANG="${LANG:-en_US.UTF-8}")
DECLARED=0
while IFS= read -r kv || [ -n "$kv" ]; do
  case "$kv" in ''|\#*) continue;; esac
  case "$kv" in *=*) ;; *) echo "REFUSED: $ENV_FILE line is not KEY=VALUE: $kv"; exit 2;; esac
  GATE_ENV+=("$kv")
  DECLARED=$((DECLARED + 1))
done < "$ENV_FILE"
STRIPPED=$(( $(env | grep -c .) - 4 ))
[ "$STRIPPED" -lt 0 ] && STRIPPED=0
ENV_SHA="$(shasum -a 256 "$ENV_FILE" | cut -d' ' -f1)"

echo "gate: python3 tools/test_all.py"
echo "sha:  $SHA"
echo "log:  $LOG"
echo "env:  $DECLARED declared from $ENV_FILE, 4 inherited (PATH HOME TMPDIR LANG), ~$STRIPPED stripped"
START=$SECONDS
env -i "${GATE_ENV[@]}" python3 tools/test_all.py > "$LOG" 2>&1
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

# --- durable receipt -----------------------------------------------------
# Founder decision 2026-08-17. Actions kept public permanent logs; a temp file
# does not. The receipt travels with the code, so a green status from months
# ago can still be examined, and a forged status is visible by the receipt it
# does not have. Written on pass AND fail: a gate that only records its wins
# is a worse record than none.
mkdir -p evidence/gates
cat > "evidence/gates/${SHA:0:12}.txt" <<RECEIPT
sha:        $SHA
result:     $STATE
summary:    $SUMMARY
exit:       $CODE
all_green:  $GREEN
duration_s: $DURATION
host:       $(uname -sm)
python:     $(python3 -V 2>&1)
env_file:   $ENV_FILE sha256=$ENV_SHA
env_declared: $DECLARED variable(s) from that file
env_inherited: PATH HOME TMPDIR LANG
env_stripped: ~$STRIPPED ambient variable(s) removed before the battery ran
ran_by:     local gate runner, scripts/local-gates.sh
ran_at:     $(date -u +%Y-%m-%dT%H:%M:%SZ)
RECEIPT
echo "receipt: evidence/gates/${SHA:0:12}.txt"

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
