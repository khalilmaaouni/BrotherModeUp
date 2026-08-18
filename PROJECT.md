# PROJECT.md

Project identity card, per the founder's 2026-08-10 project-boundaries directive.
Read this before hunting for any project resource. Never enumerate across
projects to find something listed here. If a fact is missing, ask the founder,
then record the answer here so it is never hunted again.

- Canonical path: ~/Documents/BrotherModeUp (written $HOME-relative on purpose:
  this file is tracked in a public repository, and the absolute form published
  the owner's account name from the identity card itself, 2026-08-18)
- Repo remote: origin https://github.com/khalilmaaouni/BrotherModeUp.git (verified with git remote -v, 2026-08-10)
- Published artifact URL: https://claude.ai/code/artifact/a9ed7de2-aa6e-48bb-bfc7-15c8867491e1
  (the progress page stable link, founder decision 2026-08-15: the north star
  push board is the one current board and is republished at every closed loop.)
  SUPERSEDES https://claude.ai/code/artifact/784c3ecc-e81d-45e1-af6e-b35c2127ebc0,
  which was the link confirmed 2026-08-10. The founder asked for the board to
  be republished onto that older URL; the publish was REFUSED because another
  session had written newer content there that this session had never seen, and
  forcing it would have discarded that session's work. The old link is left
  intact rather than overwritten blind. Whoever holds the baton next may fetch
  it, merge, and consolidate if the founder still wants the original address.
- Vault space: the memory vault's 10-Projects/brothermode folder. The vault's
  own location is per-operator and is declared by BROTHERMODE_VAULT rather than
  named here (founder decision D-B2, 2026-08-11: name the vault generically,
  which is also what an outside installer of a public tool actually has).
- Codex port spec (third-party, deliberately outside this public repo):
  ~/Documents/ChatGPT/BrotherModeUp/CODEX_PORT_AND_HYBRID_HARNESS_IMPLEMENTATION_SPEC.md
  The Lane CX documents in docs/program/codex-port/ cite it by filename only,
  which is why the path is recorded here (2026-08-11).

## Key commands

- Full gate: BROTHERMODE_SESSION_CAP=99 python3 tools/test_all.py
- Manifest, run after git add so new files are hashed: sh scripts/checksums.sh CHECKSUMS.sha256
- Install check: bash scripts/verify-install.sh
