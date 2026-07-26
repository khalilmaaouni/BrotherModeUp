# BrotherMode V2, business analyst and process documentation pack

This is the index of the pack. It is for the founder (a non-engineer) first,
and for any engineer who needs to hand this project to another human safely.
Read `ARCHITECTURE.md` first, then the rest in whatever order matches your
question. Nothing here is invented: every statement is traced back to one of
the five source documents listed at the bottom of this file.

## What is in this pack, and when to read it

| File | Read this when | Who it is mainly for |
|---|---|---|
| `ARCHITECTURE.md` | You want the one-page map of the whole system before touching anything else. Also holds the phase roadmap and a list of open questions found while writing this pack. | Founder, first-time reader, anyone doing a handover |
| `REQUIREMENTS.md` | You need to check whether V2 does what it was ratified to do, or you are reviewing a fix before it lands. | Founder approving scope, engineer implementing or reviewing a fix |
| `PROCESS.md` | You want to see how a real work session actually flows, step by step, including what happens when a session dies mid-task. | Founder learning how the tool behaves, engineer onboarding |
| `DATA-MODEL.md` | You are deciding what BrotherMode is allowed to hold, reviewing a privacy claim, or debugging what a table is for. | Founder reviewing privacy, engineer touching the database |
| `QA-GATES.md` | You are about to merge a change, or you want proof a quality claim is actually enforced somewhere. | Engineer merging code, founder auditing the "tested" claim |

## Status of the system this pack describes, stated plainly

As of 2026-07-26, BrotherMode V2 is MID-BUILD. Phase 1 (the engine core,
`tools/bm_store.py` plus `tools/test_bm_store.py`) is being actively written
and fixed. Nothing in this pack should be read as "this is finished." Where a
capability belongs to a later phase, it is marked "planned (Phase N)."

## Sources of truth for this pack

1. `docs/superpowers/specs/2026-07-26-brothermode-v2-design.md`, the ratified V2 design
2. `docs/superpowers/specs/2026-07-26-phase1-fix-round.md`, the required fixes from adversarial execution
3. `SKILL.md`, the 16 laws
4. `SECURITY.md`, `INVARIANTS.md`, `README.md`
5. `tools/bm_store.py`, read once for orientation only, as it stood on 2026-07-26; the spec wins wherever it and the code disagreed at that moment (see the open questions in `ARCHITECTURE.md`)
