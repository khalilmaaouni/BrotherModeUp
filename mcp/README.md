# The read-only project server

What it is for: letting any session ask what is happening in a project without reading
files. What work is active, which files are fenced to whom, what decisions were recorded,
and whether the store is healthy.

It is READ ONLY by construction. It opens the store through the read-only class, so it
cannot write, delete, or move work between states even if asked. That is the point: a
question-answering tool that can change state is not a question-answering tool.

## Verified working, and how it was proven

Executed on 2026-07-26 against a real project with one active record:

    printf '%s\n' \
      '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"t","version":"1"}}}' \
      '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
      '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"bm_fences","arguments":{"project_root":"/path/to/project"}}}' \
      | python3 mcp/bm_mcp_server.py

Real output from that run:

    - api/pay.py claimed by pay (0af16278)

and from `bm_status`:

    project root: /path/to/project (found via marker)
    healthy: yes (0 problems)

## The four tools

- `bm_status`: the project root, how it was found, and whether the store is healthy.
- `bm_active_work`: what is currently active, with its objective.
- `bm_fences`: which file is claimed by which record, so a second writer can be refused
  before it starts rather than after a collision.
- `bm_decisions`: the recorded decisions, so a new session can read why rather than guess.

Every tool REQUIRES `project_root` and refuses without it, by design: guessing which
project you meant is exactly the class of defect that made one project read another
project's database earlier in this build.

## Registering it

Add it as a stdio server in your client's configuration, pointing at the absolute path:

    python3 /absolute/path/to/mcp/bm_mcp_server.py

It speaks one JSON message per line on standard input and output, implements the
initialize handshake, the initialized notification, ping, tools/list and tools/call, and
nothing else. No resources, no prompts, no network.

## What it honestly does not do yet

- No write operations, ever, and that is permanent rather than pending.
- No multi-project view: one call, one project root.
- Not exercised by an automated test suite. It was verified by driving the protocol by
  hand, which is stated here rather than implied, so nobody reads a passing suite that
  does not exist.
- Not tested on Windows.
