# First real plugin install: 2026-07-31, author's machine, local marketplace

Status: CURRENT (evidence record; superseded only by a later install evidence file)

Founder-approved one-time test. Scope of the claim this file supports: the
plugin path has been installed ONCE, on the machine this project is built on,
from a LOCAL copy of the repository (not from GitHub), at branch
feature/beginner-first commit 499d4fa. Nothing more.

## Commands run and verbatim results

    claude plugin marketplace add /Users/.../BrotherModeUp
    ✔ Successfully added marketplace: brotherme-marketplace (declared in user settings)

    claude plugin install brotherme@brotherme-marketplace
    ✔ Successfully installed plugin: brotherme@brotherme-marketplace (scope: user)

    claude plugin list (excerpt)
    ❯ brotherme@brotherme-marketplace / Version: 2.0.0-rc.9 / Scope: user / Status: ✔ enabled

    claude plugin details brotherme (inventory excerpt)
    Skills (7)  brotherme, brotherme-deliver, brotherme-help, brotherme-next, brotherme-review, brotherme-start, brotherme-status
    Hooks (5)  SessionStart, SessionEnd, Stop, PreCompact, PreToolUse
    Projected always-on cost: ~227 tok

    claude plugin uninstall brotherme
    ✔ Successfully uninstalled plugin: brotherme (scope: user)

    claude plugin marketplace remove brotherme-marketplace
    ✔ Successfully removed marketplace: brotherme-marketplace

    claude plugin validate .   (run before install, same commit)
    ✔ Validation passed

## Two defects the test surfaced, both real

1. Name collision: while the plugin was installed, a development copy at
   ~/.claude/skills/brothermode whose manifest carried the same name was
   refused loading ("the name is already taken by an installed plugin").
   Fixed the same day by renaming the development copy's manifest.
2. Double wiring: the plugin auto-wires the same five hook events that
   scripts/install.py wires into settings.json, so a machine carrying both
   runs every hook twice while the plugin is installed. Recorded in
   docs/KNOWN-LIMITS.md; pick one wiring, not both.

## What this does NOT prove

No install from GitHub. No install on any other machine. No fresh-machine
first-run. The Loop 1 exit gate (five first-time users unaided) is untouched
by this file.
