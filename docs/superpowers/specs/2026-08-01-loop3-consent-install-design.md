# Loop 3 design: consent first, then install, doctor, update, uninstall

Status: CURRENT. Written 2026-08-01 by the orchestrator from the same-day
recon (file:line evidence in the scout report, reproduced where load-bearing).
Program gate: fresh-machine install without developer help. The external
review's go/no-go row "No content write before setup consent" is currently
the live NO-GO: tools/bm_sessionstart.sh writes and reads on every session
start with no consent gate (recon section 3). Loop 3 exists to flip that row.

## Decisions

D-1. CONSENT GATE, fail-closed on absence. A config file at
     ~/.brotherme/config.json (per the review's section 13.2: setup_complete,
     vault_path, privacy_notice_version, installation_mode, security_mode).
     Every hook entry point (bm_sessionstart.sh first, then the telemetry
     SessionEnd writer and the fence hook's nag surfaces) checks
     setup_complete BEFORE any write: absent or false means print one plain
     sentence naming the setup command, write NOTHING, exit 0. The fence
     hook itself stays fail-open as designed (it blocks writes, it does not
     create content), documented in the same change.
D-2. SETUP FLOW: scripts/setup.py, runnable two ways: interactive TTY
     (question by question, plain words) and flag-driven
     (--vault PATH --mode plugin|clone --accept-notice) for scripted runs
     and tests. Order per review 13.3: detect incomplete, show the privacy
     notice (what is written where: vault, project store, telemetry file),
     ask vault location with the default named, create config ONLY after
     explicit yes, then run doctor, then say what to do next. Refuses to
     re-run destructively; --show prints current consent state.
D-3. DOCTOR GROWS from fence-only to the ten-item surface (review 13.5):
     version identity (VERSION vs manifest), plugin-vs-clone duplicate hook
     detection (the recon's confirmed collision bug), python3 and git
     availability, config presence and validity, vault path writable,
     project store health (bm_store.py verify), hook wiring per
     installation_mode, CHECKSUMS.sha256 self-check. Each check prints PASS
     or a one-sentence remediation a non-engineer can follow. Exit 0 only
     when all pass; --json for machines.
D-4. UPDATE gains verification: the update command's documented flow adds
     checksum verification against CHECKSUMS.sha256 after checkout and a
     doctor re-run as the final step. No auto-update; the user runs the
     steps. Rollback documented: re-checkout the prior tag, doctor again.
D-5. UNINSTALL: scripts/uninstall.py additionally offers removal of
     ~/.brotherme/config.json (asked, never silent) and prints the honest
     plugin-path caveat (plugin hooks are not its bookkeeping). Vault is
     never touched, as today.
D-6. THE GATE, executed honestly on one machine: a scripted fresh-HOME
     rehearsal (HOME set to a temp directory, empty ~/.claude) driving:
     clone-path install per docs alone, setup consent flow, doctor all-PASS,
     one project started via the Loop 2 CLI, uninstall clean. Recorded as
     evidence with the exact commands. What this does NOT prove is labeled
     in the same file: no second physical machine, no naive users (that is
     Loop 8's outside-install list), plugin path still single-observation.

## Work packages (serial after Loop 2 lands; refuters read-only)

WP-D: consent gate + setup.py + hook entry-point checks + tests
      (new tools/test_bm_consent.py; sessionstart writes nothing
      pre-consent is THE test).
WP-E: doctor expansion + update flow verification + uninstall additions +
      tests.
WP-F: fresh-HOME rehearsal script (scripts/rehearse_fresh_install.sh or
      .py), run it, land the evidence file; docs updated same-change
      (SETUP, QUICKSTART, README, KNOWN-LIMITS rows that flip).

## Out of scope

Five naive users (Loop 8). Windows support beyond the documented refusal.
Auto-update. Telemetry content changes (Loop 6 owns export and deletion).
