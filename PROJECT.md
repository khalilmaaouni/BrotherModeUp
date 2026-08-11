# PROJECT.md

Project identity card, per the founder's 2026-08-10 project-boundaries directive.
Read this before hunting for any project resource. Never enumerate across
projects to find something listed here. If a fact is missing, ask the founder,
then record the answer here so it is never hunted again.

- Canonical path: /Users/khalil.maaouni/Documents/BrotherModeUp
- Repo remote: origin https://github.com/khalilmaaouni/BrotherModeUp.git (verified with git remote -v, 2026-08-10)
- Published artifact URL: https://claude.ai/code/artifact/784c3ecc-e81d-45e1-af6e-b35c2127ebc0 (the progress page stable link, founder confirmed 2026-08-10)
- Vault space: /Users/khalil.maaouni/Documents/Kay Vault/10-Projects/brothermode
- Codex port spec (third-party, deliberately outside this public repo):
  /Users/khalil.maaouni/Documents/ChatGPT/BrotherModeUp/CODEX_PORT_AND_HYBRID_HARNESS_IMPLEMENTATION_SPEC.md
  The Lane CX documents in docs/program/codex-port/ cite it by filename only,
  which is why the path is recorded here (2026-08-11).

## Key commands

- Full gate: BROTHERMODE_SESSION_CAP=99 python3 tools/test_all.py
- Manifest, run after git add so new files are hashed: sh scripts/checksums.sh CHECKSUMS.sha256
- Install check: bash scripts/verify-install.sh
