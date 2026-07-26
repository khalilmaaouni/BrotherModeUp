# Phase 3: rewire the running tools onto the store

Status: RATIFIED by founder directive 2026-07-26 ("fully rewire the skill"). This is
the riskiest change in the project, and the spec says why in advance rather than
discovering it in the middle.

## Why this is the change that matters

The V2 store is hardened across eight rounds and connected to NOTHING. The tools a
session actually runs (`bm_threads.py`, via `bm_registry.py`) still use the two JSON
registries with every defect the original audit found: prose and JSON as two sources of
ownership truth, a reusable name as identity, silent takeover on re-claim, corrupt state
replaced with clean state, and a working directory as the anchor. Until this lands, all
the hardening protects a component in waiting.

## The shape: thin CLI over one store

`bm_threads.py` keeps its command surface (the words a session types) and loses its
storage. Every ownership and lifecycle operation goes to `bm_store`. `bm_registry.py` is
DELETED, not shimmed: a shim would leave two code paths alive, which is the exact defect
class this project keeps paying for.

Mapping, and it must be explicit so nothing is improvised:

| Thread command | Store call |
|---|---|
| `on` / `off` | mode state stays a small local file; `off` DRAINS by iterating active persistent records and calling the store's handover render, then transitions each to parked in one transaction per record |
| `start <name>` | `claim(name, lifetime='persistent', ...)` with the caller's session id, so a second session is refused by name instead of silently taking over |
| `checkpoint <name>` | `checkpoint(lifecycle_uuid, expected_version, ...)`, resolving name to the ACTIVE record's uuid, refusing when the record is not active |
| `decide <name>` | `decide(...)` with the same resolution and version discipline |
| `send <name>` | `send(...)` on an ACTIVE record only |
| `dashboard` | `render_state_md` / the store's dashboard view, so what the chief sees is what recovery will drain |
| `adopt <name>` | `transition(..., 'adopted')` with the live-session flag rule already in the store |
| new: `resume`, `park`, `complete` | the store verbs that V1 never had |

Thread working files (`inbox.md`, `outbox.md`, `digest.md`) stay on disk, because
mailboxes are for humans to read, but they move to a per-lifecycle directory
(`threads/<name>-<lifecycle-prefix>/`) so a new lifecycle can never inherit the previous
one's files. The store remains the only authority on ownership; the files are views and
mailboxes.

## The test strategy, decided up front

`tools/test_bm.py` has 124 tests, and many test V1 internals that are about to stop
existing. The rule, so this does not become a quiet weakening of the suite:

1. A test that asserts a V1 IMPLEMENTATION detail (a JSON key, a registry file path, a
   lock filename) is DELETED, and the report names it.
2. A test that asserts an INVARIANT (single writer, no overlapping active claims, off is
   lossless, adopt reports honestly, a partial write is reported) is PORTED to the new
   path and must still pass. If porting it is impossible, that is a finding to report,
   not a licence to delete it.
3. Every ported invariant test gets re-CALIBRATED: reinject the defect it guards against
   in the NEW code and confirm the right test fails. A ported test that cannot be made
   to fail is decoration and must be fixed or reported.
4. The final report states three counts: deleted, ported, and newly written, with the
   reason for every deletion.

## Non-negotiable constraints

- Python 3.9, standard library only, no fcntl, cross-platform. No em or en dashes.
- The mode file may keep JSON, because it is a single boolean-ish switch and not
  ownership. Everything about who owns what lives in the store.
- `bm_store.py` and `bm_autosave.py` are NOT in this fence. If the rewire needs a change
  in the store, STOP and report it rather than editing across the fence.
- Backward compatibility with existing V1 registry files is NOT required. Nothing real
  ever ran on V1 (see docs/KNOWN-LIMITS.md), so a clean break is ratified. A found V1
  registry is reported to the user with a one-line pointer, never silently migrated.
- The line count must FALL. V1 registry plus threads is 1,668 lines; the thin CLI should
  be a fraction of that. The security document carries a public commitment that this
  number comes down, so report the before and after.

## Done-check

1. `python3 tools/test_bm.py` green, with the three counts reported.
2. `python3 tools/test_bm_store.py` and `python3 tools/test_bm_autosave.py` still green
   and untouched.
3. A full lifecycle walkthrough executed end to end by the implementer, pasted verbatim:
   `on`, `start`, `checkpoint`, `dashboard`, `park`, `resume`, `complete`, `off`, plus a
   second session refused on a live name.
4. `grep -rn "bm_registry" tools/ | grep -v test_` returns nothing.
