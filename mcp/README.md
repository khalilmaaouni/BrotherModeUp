# The read-only project server

What it is for: letting any session ask what is happening in a project without reading
files. What work is active, which files are fenced to whom, what decisions were recorded,
and whether the store is healthy.

## It is READ ONLY, and how that is actually enforced

The first version of this document said this server "is READ ONLY by construction"
because it opens the store through `bm_store.ReadOnlyStore`. That claim was proven false
(final-blockers spec 2026-07-26): a healthy store's own `ReadOnlyStore` open creates
`-shm`/`-wal` sidecars that were not there a moment before, and a CORRUPTED store's open
quarantines it, moving the founder's `store.sqlite3` aside into a quarantine directory and
reporting `isError: false`, because that quarantine behavior is correct for a writer and
catastrophic for a reader. One `bm_status` call against a corrupted store was enough to
make the founder's database disappear from its own path.

The fix is not a stronger version of the same claim; it removes the founder's real files
from the blast radius entirely. Every tool first copies `.brothermode/` and `STATE.md`
from the real project root into a fresh, private temporary directory, runs every
`bm_store.py` call against that copy, and deletes the copy before returning, success or
failure alike. Whatever `bm_store.py`'s own corruption handling, schema checks, or sidecar
creation do, they now do it to bytes that are not the founder's. A genuinely read-only
sqlite URI (`mode=ro`/`immutable=1`) was considered and rejected: `bm_store.py`'s own GATE
A (fix-round 6, 2026-07-26) already found and closed a real defect where a `%` in a
project path made a URI-based open silently read a different file, and reusing a URI here
to solve a different problem risked reopening that exact class.

Proven with two kinds of test:

- A structural scan (`tools/test_bm.py`) plus a calibrated reproduction confirm the
  redaction gap (below) is closed against the real `bm_status` function.
- The copy-first mechanism itself, the root-resolution fix, and the decisions name filter
  were verified by hand against the running server: corrupt a store, call every tool,
  confirm the real `.brothermode` directory is byte-identical before and after; remove a
  healthy store's sidecars, call every tool, confirm none reappear; set
  `BROTHERMODE_ROOT` to one project and pass an absolute `project_root` naming a
  different one, confirm the second project answers with its own root printed. These are
  not (yet) committed as an automated suite of their own; say so here rather than imply
  otherwise.

Every founder-typed value this server returns -- a record name, an objective, a tier, a
claim path, a decision's topic or text, and every `bm_store.verify()` problem line (which
carries no redaction of its own; it is an invariant checker, not a rendering funnel) --
passes through `bm_store._protect_text`, the exact function `bm_store.py`'s own CLI uses.
Before this fix, a `verify()` problem naming a secret-shaped record reached a client here
completely unredacted while the CLI showed `[REDACTED]` for the identical value.

## Verified working, and how it was proven

Executed on 2026-07-26 against a real project with one active record, after the fixes
above landed:

    printf '%s\n' \
      '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"t","version":"1"}}}' \
      '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
      '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"bm_fences","arguments":{"project_root":"/path/to/project"}}}' \
      | python3 mcp/bm_mcp_server.py

Real output from that run:

    project root: /path/to/project (found via marker)
    - api/pay.py claimed by pay (28d923ce)

and from `bm_status`:

    project root: /path/to/project (found via marker)
    healthy: yes (0 problems)

Every tool now names the project root it actually resolved as its own first line, so a
root substitution (see GATE 4 below) can never be silent.

## The four tools

- `bm_status`: the project root, how it was found, and whether the store is healthy.
- `bm_active_work`: what is currently active, with its objective.
- `bm_fences`: which file is claimed by which record, so a second writer can be refused
  before it starts rather than after a collision.
- `bm_decisions`: the recorded decisions, so a new session can read why rather than guess.
  Filtering by `record_name` compares against the record's REAL name, never an
  already-redacted one, so filtering by a name that happens to look secret-shaped still
  finds its decisions instead of a false "no decisions recorded".

Every tool REQUIRES `project_root`, and it MUST be an absolute path (GATE 4,
final-blockers spec 2026-07-26): a relative path is refused outright rather than resolved
against this server process's own working directory (which a caller neither sets nor
sees), and the `BROTHERMODE_ROOT` environment variable is never consulted, so an ambient
value set for one project can never silently answer a call that named a different one.
This is the exact class of defect that once made one project's call return another
project's record.

## Registering it

Add it as a stdio server in your client's configuration, pointing at the absolute path:

    python3 /absolute/path/to/mcp/bm_mcp_server.py

It speaks one JSON message per line on standard input and output, implements the
initialize handshake, the initialized notification, ping, tools/list and tools/call, and
nothing else. No resources, no prompts, no network.

## What it honestly does not do yet

- No write operations, ever, to the founder's real files, and that is now enforced by
  never opening them for anything but a read into a private, discarded copy (see above),
  not merely by which class of `bm_store.py` object this file calls.
- No multi-project view: one call, one project root.
- No crash-safe snapshot: copying `.brothermode/` while another process is actively
  writing to it (WAL mode) is a best-effort "hot copy", not a transactionally guaranteed
  one. A snapshot taken mid-write can itself read back as busy or corrupted on the COPY;
  this server reports that honestly rather than retrying silently, and it never touches
  the real store either way.
- Partially exercised by an automated test suite. `tools/test_bm.py` covers the output
  redaction funnel end to end against the real `bm_status` function. The copy-first
  read-only mechanism, the root-resolution fix, and the decisions name filter were
  verified by hand against the running server (see above), not by a committed automated
  test; said here rather than implied otherwise.
- Not tested on Windows.
