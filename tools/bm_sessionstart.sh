#!/bin/sh
# BrotherMode SessionStart: digest + mechanical nags. MUST always exit 0.
# Output is injected into session context (10k char cap; we stay far under).
# Resolve the skill directory from this script's own location, so the repo
# works wherever it is cloned.
DIR="$(cd "$(dirname "$0")/.." && pwd)"
# Capture the hook JSON from stdin ONCE so we can both ignore it (digest/nags)
# and replay it to the compaction hint below.
PAYLOAD="$(cat 2>/dev/null)"

# Consent gate (Loop 3 design D-1): before any write or store command below,
# check consent via scripts/setup.py's cheap --consent-state probe (exit 0
# consented, non-zero otherwise: absent config, setup_complete false, or a
# broken config all read the same way here, fail closed). Not consented means
# this script prints exactly one plain sentence and exits 0 having written
# nothing at all: no digest, no telemetry, no store verify. scripts/setup.py
# is the ONLY place that creates ~/.brotherme/config.json.
if ! python3 "$DIR/scripts/setup.py" --consent-state >/dev/null 2>&1; then
  echo "BrotherMode setup is not complete yet; run: python3 scripts/setup.py"
  exit 0
fi

cat "$DIR/DIGEST.md" 2>/dev/null
python3 "$DIR/tools/bm_telemetry.py" startup-nags 2>/dev/null
# PROGRESS PAGE OWED (founder directive 2026-08-10). The founder's progress
# page is how a non-engineer sees where a project stands, and sessions kept
# building it and never showing it, so it had to be asked for. This prints one
# line ONLY when a plan exists and the page is missing or older than that plan;
# it is silent otherwise, because a nag that fires every session stops being
# read. Silent on exit 0 (nothing owed) and on exit 2 (could not tell, which is
# reported by the tool itself when it is a real NO-DATA rather than a missing
# file). The `|| true` and the 2>/dev/null are deliberate and this script's own
# header says why: SessionStart MUST always exit 0, so a tool that is absent on
# an older install, or that somehow crashes, can never take a session down with
# it. That is a fail-open by choice: this check exists to remove the excuse of
# not having noticed, never to become a new way for a session to die.
python3 "$DIR/tools/bm_progress_check.py" status 2>/dev/null || true
python3 "$DIR/tools/bm_telemetry.py" check-update 2>/dev/null
# If this session resumed from a compaction, point it at the autosave.
printf '%s' "$PAYLOAD" | python3 "$DIR/tools/bm_telemetry.py" compact-hint 2>/dev/null
# Store health: silent when healthy or when no store exists yet (verify's own
# "no-root"/"no-store" refusals), printed whenever there is something real to
# see (an unacknowledged quarantine, corruption, or anything else verify or
# bm_store.py's own pre-command warning reports), so a lost database is never
# a session's whole SessionStart output being nothing.
# "refused (schema-" is matched too (2026-08-04): a store one schema behind or
# ahead of this BrotherMode stopped being reported as STORE CORRUPT that day,
# which is the truth, but it is still something the founder has to act on (one
# writable command migrates it). Without this alternative the fix would have
# traded a scary visible message for an accurate invisible one.
STORE_HEALTH="$(python3 "$DIR/tools/bm_store.py" verify 2>&1)"; printf '%s\n' "$STORE_HEALTH" | grep -Eq 'problem\(s\) found|STORE CORRUPT|refused \(schema-|WARNING|unexpected error|db-busy|stale-identity|Traceback' && printf '%s\n' "$STORE_HEALTH"
exit 0
