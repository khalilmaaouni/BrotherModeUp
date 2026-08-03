# Loop 6 design: security and privacy closure

Status: CURRENT. Written 2026-08-01 by the orchestrator. Program gate:
threat model explicit; detection demonstrated.

## What already exists (verified in-tree today)

- Tightening option: BM_FENCE_STRICT (bm_fence_hook.py) denies
  writes to paths no active record fences; documented at
  docs/HOOKS.md:257. CORRECTED 2026-08-03 (closure item C-03): this line
  originally called it a "fail-closed option", which it is not and never
  was. It is read AFTER every fail-open path, so it is a complete no-op on
  a store with no active claims, and it changes nothing about what happens
  when the fence cannot be checked at all. The genuine fail-closed switch
  is BM_FENCE_MODE=enforced, added under C-01 on the same date.
- Declared-path shell writes: scripts/bm_shell.py, the wrapper for
  unavoidable shell writes, already tested in tools/test_install.py.
- Consent-first disclosure: landed in Loop 3 (setup.py notice, zero
  writes pre-consent, proven by suite).
- The known limit, stated for months: the fence hook does NOT gate Bash;
  a shell redirect can cross a fence invisibly.

## Decisions

D-1. BASH-WRITE DETECTION, not prevention (prevention is impossible
     without gating Bash, and gating Bash breaks the tool's contract;
     the honest posture is detect-and-alert): a PostToolUse hook for
     Bash, tools/bm_bash_audit.py. On PreToolUse it snapshots
     (mtime, size, sha256) of every path fenced by ACTIVE records; on
     PostToolUse it re-hashes and, for any fenced path changed by a
     session that does not own the fence, raises a real alert row
     (severity high, category fence-breach, requires_human true)
     through the service layer, plus one plain stderr sentence. The
     snapshot lives under .brothermode/, consent-gated like every hook
     write. Fail-open with the reason printed, same policy as the fence
     hook, and the alert is the demonstration the gate demands.
D-2. THREAT MODEL EXPLICIT: SECURITY.md gains a section enumerating
     assets (the store, the vault, consent config, settings.json,
     generated views), trust boundaries (hooks run as the user;
     subagents share the tree; MCP is read-only), the attacks the
     design answers (cross-fence writes via editor tools: blocked;
     via Bash: detected by D-1; secret exfiltration through exports:
     scrub lanes; stale-manifest tampering: doctor check 9), and the
     attacks it explicitly does NOT answer (a malicious process with
     the user's own privileges, supply-chain compromise of Python
     itself), each with one sentence on why that is out of scope.
D-3. EXPORT AND DELETION: bm_project.py gains export (writes one JSON
     file of every row the store holds for a project, redacted by
     default, --raw for the owner) and purge (deletes a project's rows
     through the service layer after typed confirmation, attribution
     row recording the purge, vault untouched). Uninstall already
     removes hooks and consent; KNOWN-LIMITS rows updated same-change.
D-4. DETECTION DEMONSTRATED, mechanically: a test drives a real
     cross-fence Bash write in a temp root (echo into a fenced file
     from a foreign session id) and asserts the high-severity alert row
     appears with the breach path masked per export policy; a second
     test proves the owner's own Bash write raises nothing.

## Work packages

WP-G: bm_bash_audit.py + hooks wiring (hooks/hooks.json, scripts/
      install.py OWNED_TOOLS) + tests + docs (HOOKS.md, SECURITY.md
      D-2 section, KNOWN-LIMITS flips).
WP-H: export and purge subcommands + tests + docs.
Refuters fold into the Loop 6 wave after both land.

## Out of scope

Gating Bash. Windows hook legs. Runtime adapters (Loop 7).
