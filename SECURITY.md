# Security

## Reporting a vulnerability

Open a GitHub issue describing the problem and how to reproduce it. If the issue
would expose someone's data by being public, say so in one line without the
details and ask for a private channel first.

## What this software does with your data

BrotherMode makes no network calls. It has no analytics, no account, and no
server. Everything it writes goes to your vault folder, which you choose with
`BROTHERMODE_VAULT` (default `~/BrotherModeVault`). You can verify both claims
yourself; the tools are about 834 lines of standard-library Python and shell:

```bash
grep -rnE "urllib|requests|socket|http|curl|wget|subprocess" tools/
```

Two files inside the vault deserve attention:

- `99-System/telemetry/outcomes.jsonl` holds per-session counts (tokens, tool
  calls, duration) plus the basename of the working directory. No file contents,
  no prompts.
- `99-System/telemetry/corrections.jsonl` holds short excerpts **of your own
  messages** that look like corrections, so the weekly review can turn them into
  rules. Secret-shaped substrings (API keys, tokens, `password=`, private keys,
  national-ID and card shapes) are redacted before anything is written, and the
  file is created owner-only (0600). Redaction is best-effort pattern matching,
  not a guarantee. Treat the file as sensitive, keep it out of version control
  (the shipped `vault-template/.gitignore` excludes it), and purge it whenever
  you like:

```bash
python3 tools/bm_telemetry.py purge-corrections        # shows what is there
python3 tools/bm_telemetry.py purge-corrections --yes  # deletes it
```

To disable correction capture entirely, remove the `SessionEnd` hook. You lose
the automatic capture half of the learning loop; everything else keeps working.

## Scope note

This project governs how a Claude Code session behaves. It does not change what
Claude Code itself transmits to Anthropic or your chosen cloud provider. For
that, see Anthropic's own documentation on Claude Code data usage, and choose
your plan accordingly: commercial terms (Team, Enterprise, API, cloud providers)
differ materially from consumer plans.

## Verifying what you installed

This repository is unsigned and has no releases. If your organization requires
pinning, clone at a specific commit and record the hash:

```bash
git -C ~/.claude/skills/brothermode rev-parse HEAD
```
