#!/bin/sh
# BrotherMode SessionStart: digest + mechanical nags. MUST always exit 0.
# Output is injected into session context (10k char cap; we stay far under).
# Resolve the skill directory from this script's own location, so the repo
# works wherever it is cloned.
DIR="$(cd "$(dirname "$0")/.." && pwd)"
# Capture the hook JSON from stdin ONCE so we can both ignore it (digest/nags)
# and replay it to the compaction hint below.
PAYLOAD="$(cat 2>/dev/null)"
cat "$DIR/DIGEST.md" 2>/dev/null
python3 "$DIR/tools/bm_telemetry.py" startup-nags 2>/dev/null
python3 "$DIR/tools/bm_telemetry.py" check-update 2>/dev/null
# If this session resumed from a compaction, point it at the autosave.
printf '%s' "$PAYLOAD" | python3 "$DIR/tools/bm_telemetry.py" compact-hint 2>/dev/null
# Store health: silent when healthy or when no store exists yet (verify's own
# "no-root"/"no-store" refusals), printed whenever there is something real to
# see (an unacknowledged quarantine, corruption, or anything else verify or
# bm_store.py's own pre-command warning reports), so a lost database is never
# a session's whole SessionStart output being nothing.
STORE_HEALTH="$(python3 "$DIR/tools/bm_store.py" verify 2>&1)"; printf '%s\n' "$STORE_HEALTH" | grep -Eq 'problem\(s\) found|STORE CORRUPT|WARNING|unexpected error|db-busy|stale-identity|Traceback' && printf '%s\n' "$STORE_HEALTH"
exit 0
