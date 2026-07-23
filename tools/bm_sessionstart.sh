#!/bin/sh
# BrotherMode SessionStart: digest + mechanical nags. MUST always exit 0.
# Output is injected into session context (10k char cap; we stay far under).
# Resolve the skill directory from this script's own location, so the repo
# works wherever it is cloned.
DIR="$(cd "$(dirname "$0")/.." && pwd)"
cat "$DIR/DIGEST.md" 2>/dev/null
python3 "$DIR/tools/bm_telemetry.py" startup-nags 2>/dev/null
exit 0
