# BrotherMode

**A Claude skill that turns the model from a tool that waits for instructions into a colleague that owns outcomes.**

Created by Khalil Maaouni. MIT licensed. Built for [Claude Code](https://claude.com/claude-code); the ideas port to any agent harness.

## What this is

BrotherMode is not a prompt. It is an operating law: a written constitution that a Claude session loads at the start of any sizable task, plus the small mechanical toolchain that holds the session to it. The prompt tells the model what to do once. The law tells it how to work, every time, and the telemetry proves whether it actually did.

Most agent setups fail the same way. The model over-delivers ceremony on small tasks, under-verifies big ones, forgets what a killed session was doing, lets two subagents overwrite each other's files, and reports success it never earned. BrotherMode exists to close those failure modes structurally, not by hoping the model behaves.

## What is in the box

| File | What it does |
|---|---|
| `SKILL.md` | The law: 16 numbered sections (0 through 15) covering classification, delegation, fences, budgets, research, honesty, memory, scoring |
| `DIGEST.md` | A 12-line compression of the law, injected at every session start so the rules survive context loss |
| `RUBRIC.md` | A template for the 9 frozen metrics your weekly review scores against |
| `STATE.template.md` | The running state file format: fences, decisions, the never-forget list |
| `tools/bm_telemetry.py` | The mechanical half of the learning loop: session telemetry, corrections capture, scorecard, nags |
| `tools/bm_score.py` | Code-graded weekly checks, so the LLM judge only scores what code cannot decide |
| `tools/bm_sessionstart.sh` | Session-start hook: injects the digest, overdue-review nags, the offline update check, and a recovery pointer after a compaction |
| `tools/bm_autosave.sh` | Mechanical work-preservation: on the PreCompact hook it snapshots your whole working tree (untracked files included) to a private git ref so token-death never erases progress. Local git only, never pushes. `recover` restores it |
| `tools/test_bm.py` | Regression tests (stdlib only): secret redaction, owner-only files, project-identity collisions, non-invasive autosave. Run `python3 tools/test_bm.py`; CI runs them on every push |
| `tools/WEEKLY-REVIEW.md` | The 11-step weekly self-review procedure |
| `docs/HOW-IT-WORKS.md` | The full mechanics, explained exactly |
| `docs/BrotherMode-Design-Document.pdf` | The whitepaper: philosophy, all 16 laws, the code, data flow and cost, benchmarks, and a quick start. Start here if you are deciding whether to adopt |
| `docs/SETUP.md` | Installation, hooks, and first-week checklist |
| `vault-template/` | A ready-made Obsidian-compatible memory vault: copy it, open it in Obsidian, start working |

## The five ideas that carry the system

1. **Fence then dispatch.** One writer per file, ever. Before any agent launches, its file set is written to a registry on disk. Overlap means queue, never parallel. Collisions stop being possible instead of being cleaned up.
2. **The safety floor is unconditional.** Whenever anything writes, three things happen first: map the ground (git status), register the fence, keep state on disk. The learning loop is explicitly forbidden from training this away.
3. **Nothing merges unverified.** Agents self-report; the orchestrator re-runs the check against the actual files before accepting anything. A deliverable arriving without its done-check satisfied goes back with the gap named.
4. **The skill learns from measured outcomes only.** A session-end hook writes real token counts, tool calls, and durations to a ledger. Absent telemetry, a field says "not measured". Fiction is banned. A weekly review moves scores; corrections from the human become laws, each carrying the reason behind it.
5. **Honesty is a gate, not a virtue.** Bad news travels first. Every claim carries its calibration: verified by command, verified by inspection, likely, or assumed. Self-scores cap at 8; a 9 or 10 requires named external evidence.

## Read this first

[**The design document**](docs/BrotherMode-Design-Document.pdf) (36 pages) explains
the philosophy, every law, the code, exactly what data goes where, what it costs,
and when not to use this. It is written to be read by someone who has never used an
AI agent, and to be checked by someone who will read the source.

## Quick start

```bash
git clone https://github.com/khalilmaaouni/BrotherModeUp.git ~/.claude/skills/brothermode
```

Then follow `docs/SETUP.md` to wire the three hooks and create your vault. Invoke with `/brothermode` at the start of any sizable task. Total setup is under ten minutes.

## What is deliberately not here

Personal memory. The vault (session logs, findings, the founder model, telemetry ledgers) lives outside this repo, on your machine, and is never committed to it. The repo ships an empty vault-template you copy once; what grows inside your copy stays yours. This repo is the machinery. The memory is yours and stays yours.

## Requirements

- Claude Code (CLI or desktop app) with skills enabled
- Python 3 (standard library only; no packages to install)
- git

## License

MIT. Use it, fork it, rewrite the law to fit your team. The rubric is a template on purpose: ratify your own version with whoever plays the founder role, then freeze it.

Created by Khalil Maaouni.
