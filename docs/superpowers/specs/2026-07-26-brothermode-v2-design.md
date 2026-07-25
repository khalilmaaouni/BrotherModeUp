# BrotherMode V2 design, ratified 2026-07-26

Status: RATIFIED by the founder on 2026-07-26 (all recommendations accepted, one
override: Windows must be supported, not declared unsupported). The verified defect
evidence behind every decision here lives in
~/Documents/BrotherModeV2-planning/DECISION-BRIEF.md (22 audit claims reproduced by
execution: 21 confirmed, 1 partial, 0 refuted).

## The four decisions (each kills a defect class, not an instance)

1. ONE CANONICAL ROOT. Every operation resolves the project root once and derives
   every path, identity, and snapshot from it. Never os.getcwd() as an anchor.
2. ONE TRANSACTIONAL STORE. sqlite3 (Python standard library, WAL mode) is the only
   authority on work records. STATE.md, dashboards, and handovers are GENERATED
   views. Prose is never ownership.
3. ONE IMMUTABLE IDENTITY. Every record has a lifecycle uuid that is never reused.
   Every mutation carries lifecycle uuid plus expected version and fails when stale
   (optimistic concurrency). Names are labels, not identities.
4. TWO FAILURE POLICIES, EXPLICIT. Advisory surfaces (telemetry, hints, nags) fail
   open and never block. Ownership, lifecycle, and recovery mutations fail CLOSED:
   corrupt state is quarantined and refused, never silently replaced; a missing lock
   or stale identity refuses the mutation with a named reason.

Windows requirement (founder override): everything in V2 must run on Windows, macOS,
and Linux. Concretely: no fcntl, no POSIX-only calls, no shell scripts as load-bearing
components (ports to Python in Phase 2), pathlib plus os.path.normcase for path
comparison (Windows and macOS are case-insensitive), os.replace for atomic renames,
chmod treated as best-effort, CI matrix ubuntu-latest, macos-latest, windows-latest.

## Phase 1 contract: tools/bm_store.py plus tools/test_bm_store.py

New module, standard library only, no network, no subprocess (root resolution walks
the filesystem instead of calling git). Python 3.9 compatible. House style: header
comment stating the one job, docstrings explain WHY, no em or en dashes anywhere.

### Root resolution (fixes confirmed defects F2, F42, F2b class)

resolve_root(start=None) returns (root_path, source) where source is one of
"env", "marker", "git". Order:
1. BROTHERMODE_ROOT env var, if set and is a directory (realpath applied).
2. Walk up from start (default cwd) to filesystem root: first directory containing
   .brothermode/ (marker dir) wins.
3. Same walk: first directory containing .git (dir OR file, so worktrees work).
4. None. Ownership operations REFUSE with reason "no-root": the CLI tells the user
   to run `init` or set BROTHERMODE_ROOT. Advisory callers may fall back to cwd but
   must say so.
The store lives at <root>/.brothermode/store.sqlite3. init creates .brothermode/
and the schema, and appends .brothermode/, threads/, STATE.md to .git/info/exclude
when a .git directory exists and the entries are absent (fixes audit finding 30
without touching the user's .gitignore).

### Schema (DDL, schema_version 1)

PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000; PRAGMA foreign_keys=ON.

meta(key TEXT PRIMARY KEY, value TEXT)                 -- schema_version, project_uuid, created_at
records(
  lifecycle_uuid TEXT PRIMARY KEY,                     -- uuid4 hex, never reused
  name TEXT NOT NULL,                                  -- human label, reusable across lifecycles
  lifetime TEXT NOT NULL CHECK(lifetime IN ('persistent','ephemeral')),
  state TEXT NOT NULL CHECK(state IN ('active','parked','complete','adopted')),
  objective TEXT NOT NULL DEFAULT '',
  owner TEXT NOT NULL DEFAULT '',
  session_id TEXT NOT NULL DEFAULT '',
  tier TEXT NOT NULL DEFAULT '',
  check_cmd TEXT NOT NULL DEFAULT '',                  -- the runnable done-check
  evidence TEXT NOT NULL DEFAULT '',                   -- filled at complete
  ttl_hours REAL,                                      -- NULL means no lease expiry
  version INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL   -- UTC ISO 8601
);
CREATE UNIQUE INDEX one_active_per_name ON records(name) WHERE state='active';
claims(lifecycle_uuid REFERENCES records ON DELETE CASCADE, path TEXT NOT NULL,
       is_glob INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(lifecycle_uuid, path))
decisions(lifecycle_uuid REFERENCES records, seq INTEGER, topic TEXT, text TEXT,
          created_at TEXT, PRIMARY KEY(lifecycle_uuid, seq))
digests(lifecycle_uuid REFERENCES records, seq INTEGER, next_intent TEXT,
        blockers TEXT, files_note TEXT, body TEXT, created_at TEXT,
        PRIMARY KEY(lifecycle_uuid, seq))
directives(lifecycle_uuid REFERENCES records, seq INTEGER, text TEXT,
           created_at TEXT, delivered_at TEXT, PRIMARY KEY(lifecycle_uuid, seq))
deliveries(payload_sha256 TEXT PRIMARY KEY,            -- full 64 hex chars (fixes F13)
           lifecycle_uuid TEXT NOT NULL, target TEXT NOT NULL, delivered_at TEXT NOT NULL)
transitions(id INTEGER PRIMARY KEY AUTOINCREMENT, lifecycle_uuid TEXT NOT NULL,
            from_state TEXT, to_state TEXT NOT NULL, session_id TEXT NOT NULL DEFAULT '',
            note TEXT NOT NULL DEFAULT '', at TEXT NOT NULL)
autosave_receipts(id INTEGER PRIMARY KEY AUTOINCREMENT, worktree_id TEXT NOT NULL,
            session_id TEXT NOT NULL, snapshot_sha TEXT NOT NULL, tree_sha TEXT NOT NULL,
            source_head TEXT NOT NULL, captured_count INTEGER NOT NULL,
            excluded_count INTEGER NOT NULL, created_at TEXT NOT NULL)
            -- written by Phase 2; schema ships now so Phase 2 needs no migration

### Name validation (fixes F4)

valid_name(n): reject empty, '.', '..', names starting with '.', names containing
any of / \\ : ? * " < > | or whitespace, names longer than 60 chars. Invalid names
raise ValueError with the reason; NO silent normalization (a-b collision class dies).
Per-lifecycle working directories (used from Phase 3 on) are
threads/<name>-<lifecycle_uuid[:8]>/ so a new lifecycle can never inherit an old
lifecycle's files (fixes F14).

### Overlap semantics (fixes F1, F2, F11)

All claim paths are stored relative to root (normalize: strip leading ./, collapse
separators to /, apply os.path.normcase for comparison only). paths_overlap(a, b):
- exact match after normcase: conflict.
- directory containment: a equal to or a path-prefix of b at a separator boundary,
  either direction: conflict.
- glob involved (either side contains * ? [ ): CONSERVATIVE. Compute each side's
  literal directory prefix (everything before the first wildcard's containing
  segment). If one literal prefix is equal to or contains the other at a separator
  boundary, conflict. Two globs only escape conflict when their literal prefixes are
  provably disjoint directories. api/*.py vs api/pay.* MUST conflict.
claim() checks the union of every ACTIVE record's claims inside the same
transaction that inserts the new record, and refuses with the conflicting record's
name, lifecycle uuid, and the overlapping pair of paths.

### API (all mutations inside one transaction, all timestamps UTC)

Store(root) constructor opens or creates the db; on sqlite3.DatabaseError during
open or any read: QUARANTINE: close, rename store.sqlite3 to
store.sqlite3.quarantine-<UTCstamp>, raise StoreCorrupt telling the user the
quarantine path and the recover command. Never auto-recreate over damage (fixes F9).

claim(name, lifetime, objective, files, owner='', session_id='', tier='',
      check_cmd='', ttl_hours=None) -> Record
  Refuses (OwnershipRefused, reason codes): 'invalid-name', 'overlap' (with
  details), 'name-active' when an ACTIVE record already holds this name and the
  caller's session_id does not match that record's session_id (fixes F3: no silent
  takeover; the error names resume/transfer as the paths forward), 'cap' when the
  active persistent count is already 3.
transition(lifecycle_uuid, expected_version, to_state, session_id='', note='',
           evidence='') -> Record
  Legal moves: active->parked (park), parked->active (resume), active->complete
  (requires check_cmd evidence text non-empty), active->adopted, parked->adopted.
  UPDATE ... WHERE lifecycle_uuid=? AND version=? AND state=?; zero rows updated
  raises StaleIdentity naming current state and version (fixes F5, F6, F7, F8
  class). Every transition also inserts a transitions row in the same transaction.
checkpoint(lifecycle_uuid, expected_version, next_intent, blockers='', files_note='',
           body='', decisions=None) -> digest seq
  Refused unless state == 'active' (StaleIdentity otherwise). Decisions appended
  atomically with the digest row (fixes audit finding 19).
decide(lifecycle_uuid, expected_version, topic, text) -> seq
send(lifecycle_uuid, text) -> seq          # directive into an ACTIVE record only
handover_payload(lifecycle_uuid) -> dict   # objective, files, owner, tier, check,
  evidence, latest digest sections, ALL decisions; fingerprint =
  sha256(canonical json).hexdigest() FULL 64 (fixes F13)
render_digest(lifecycle_uuid) -> str per-section budgets, priority order:
  header (lifecycle, objective) 400 chars, next_intent 900, blockers 600,
  files_note 600, newest decisions 1200, older decisions 300. Each section
  truncates ITSELF with an explicit '(truncated)' marker; next intent can never be
  displaced by decisions (fixes F12).
render_state_md(root) -> str               # the generated human view, and
write_state_view(root) writes it to STATE.md between BEGIN/END GENERATED markers,
  preserving any human prose outside the markers.
dump() -> dict                             # full JSON export of every table
verify(root) -> list[str]                  # machine invariants: one active per
  name, no overlapping active claims, every active record reachable in the view,
  transitions consistent with states. Empty list means healthy. This replaces the
  one-directional I8 (fixes F15): the store IS both directions.

### CLI (python3 tools/bm_store.py <cmd>)

init, claim, park, resume, complete, adopt, checkpoint, decide, dashboard, dump,
verify. Exit 0 on success, 2 on refusal (with the reason code on stdout), 1 on
corruption/unexpected. Refusals are one clear sentence plus the command that would
be legal next. No color, ASCII only.

### Required tests (tools/test_bm_store.py, unittest, no fixtures on the real repo)

Behavior tests, one per API promise above, PLUS these CALIBRATED reinjection tests,
each asserting V2 refuses what V1 allowed (V1 evidence in the decision brief):
1. claim same name from a different session while active: refused 'name-active'
   (V1 silently replaced the fence, F3).
2. two Store instances opened from root and from a subdir of root resolve the SAME
   db file and the second claim on the same path is refused (V1 minted two
   registries, F2).
3. name '..' and '.' and 'a/b' raise ValueError (V1 wrote to project root, F4).
4. paths_overlap('api/*.py','api/pay.*') is a conflict (V1 said no conflict, F11).
5. 20 long decisions then render_digest: '## Next intent' content present and
   intact (V1 cut it entirely, F12).
6. two payloads differing ONLY in objective produce different fingerprints (V1
   collided and dropped the second handover, F13).
7. checkpoint against a parked record: StaleIdentity (V1 wrote into parked records
   after off, F5/F6).
8. corrupt db bytes: opening quarantines and raises; the damaged file still exists
   at the quarantine path; a fresh init then works (V1 overwrote corruption, F9).
9. stale version number on transition: StaleIdentity, record unchanged (new
   optimistic-concurrency guarantee).
10. resume of a parked record restores 'active' and the SAME lifecycle_uuid (V1
    had no resume at all, F8).
Plus Windows-safety unit checks runnable on any platform: no fcntl import anywhere
in the module (assert via reading the source), path comparison uses normcase (two
claims differing only by case conflict).

### Explicitly OUT of Phase 1 (do not build)

Autosave (Phase 2). Porting bm_threads/bm_telemetry onto the store, adopt/transfer
UX, drain/off flows (Phase 3). Scaffold, docs generators, SKILL.md v2 laws
(Phase 4). MCP server, onboarding, CI matrix, release engineering (Phase 5).
Migration tooling from V1 registries: NOT NEEDED, nothing real ever ran on V1
(handover 00-START-HERE), a clean break is ratified.

## Phase roadmap (each phase separately gated, per the ratified brief)

1. Engine core (this spec): store, root, identity, failure policies, verify.
2. Recovery: bm_autosave.py (Python port, per-worktree-per-session refs, receipts
   into autosave_receipts, retention, recover-into-separate-worktree only).
3. Command surface: thread mode UX rebuilt on the store; off/adopt/drain
   transactional; generated STATE.md everywhere; bm_threads.py becomes a thin CLI
   over bm_store.
4. Method layer: project scaffold (README, INTAKE, ARCHITECTURE, docs pack,
   decisions/), simplicity law, problem-first intake, handover generator.
5. Product: Windows validation, CI matrix, onboarding (Obsidian default, Mem0
   optional adapter off by default), tagged v2.0.0 release with checksums, public
   and private repo sync script.
6. Dogfood evidence and the 2026-08-08 review record (the store IS the ephemeral
   fence migration; record outcome 1 with the measured signals).
