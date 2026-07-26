#!/usr/bin/env python3
"""bm_mcp_server.py: a minimal, read-only Model Context Protocol server for
one BrotherMode project's store.

WHAT THIS FILE WILL NEVER DO, stated once here so it never needs restating
at a call site: it will never write to a store, delete anything, transition
a record between states, claim a fence, park, resume, complete, adopt,
checkpoint, decide, or send a directive. Every database access in this file
goes through exactly two entry points from `tools/bm_store.py`:
`bm_store.ReadOnlyStore` (which refuses to create a store that does not
already exist, and enforces `PRAGMA query_only=ON` on its connection) and
`bm_store.verify()` (which itself only opens a `ReadOnlyStore`). This file
adds no database connection code of its own, invents no new query logic
beyond simple in-memory filtering of what `ReadOnlyStore.dump()` already
returns, and calls no `Store` (the writable class) anywhere.

WHAT THIS SERVER ANSWERS, matching the four questions ratified for the
read-only project server: what work is active, what fences (claimed file
paths) are live, what decisions were recorded, and whether the store is
healthy. Four tools, one each: bm_status, bm_active_work, bm_fences,
bm_decisions.

HONESTY ABOUT SCOPE. This implements the subset of the Model Context
Protocol (2025-06-18) a read-only query tool over stdio actually needs:
the `initialize` handshake, the `notifications/initialized` notification,
`ping`, `tools/list`, and `tools/call`. It does NOT implement resources,
prompts, sampling, elicitation, roots, pagination cursors, or any
`listChanged` notification (the tool list here is fixed at process start
and never changes, so there is nothing to notify about). This is a
deliberate, minimal cut, not an accidental gap; `mcp/README.md` says so
again and states plainly what has and has not been verified end to end
with a real MCP client.

Standard library only: json, os, sys, importlib.util. No MCP SDK, no
network library, no subprocess. The stdio transport this implements is
exactly what the spec defines it to be: newline-delimited JSON-RPC 2.0
messages on stdin/stdout, UTF-8, one message per line, nothing else ever
written to stdout. Confirmed against
https://modelcontextprotocol.io/specification/2025-06-18/basic/transports
and the adjoining lifecycle and tools pages on 2026-07-26; this header
records that check rather than asking a reader to trust an unstated memory
of the spec.
"""

import importlib.util
import json
import os
import sys

PROTOCOL_VERSION = "2025-06-18"
SERVER_NAME = "brothermode-project-readonly"
SERVER_VERSION = "0.1.0"  # this server's own version, independent of VERSION
# at the repository root: it was built today, has not been adversarially
# reviewed the way the rest of this project has, and a shared version
# number would overstate how proven it is.

_HERE = os.path.dirname(os.path.abspath(__file__))
_BM_STORE_PATH = os.path.normpath(os.path.join(_HERE, "..", "tools", "bm_store.py"))


def _load_bm_store():
    """Dynamic load by path, mirroring bm_store.py's own `_load_redact` /
    `_load_atomic_write` pattern (same file, search for either name) rather
    than inventing a new loading convention: this project's established way
    of pulling in a sibling tool module regardless of the caller's cwd or
    whether `tools/` is on sys.path."""
    try:
        spec = importlib.util.spec_from_file_location("bm_store_for_mcp", _BM_STORE_PATH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod, None
    except Exception as e:
        return None, repr(e)


bm_store, _BM_STORE_LOAD_ERROR = _load_bm_store()


class ToolError(Exception):
    """A tool-level failure to report back as isError: true (bad input, no
    project found, store unreadable), distinct from a protocol-level
    JSON-RPC error (unknown method, unknown tool name, malformed request)."""


def _log(message):
    """Every diagnostic line goes to stderr, never stdout: the spec
    requires the server MUST NOT write anything to stdout that is not a
    valid MCP message, and a stray print() would corrupt the stream for
    every message after it."""
    sys.stderr.write("bm_mcp_server: %s\n" % message)
    sys.stderr.flush()


def _require_bm_store():
    if bm_store is None:
        raise ToolError(
            "tools/bm_store.py could not be loaded (%s); this server has "
            "nothing to query without it." % _BM_STORE_LOAD_ERROR)


def _resolve_root(arguments):
    """Resolve a project root exactly the way the bm_store.py CLI does,
    reusing bm_store.resolve_root rather than reimplementing root-finding:
    BROTHERMODE_ROOT wins if set, then the nearest .brothermode marker
    walking up from project_root, then the nearest .git. project_root is a
    required argument on every tool here (never the server process's own
    cwd, which is whatever the MCP client happened to launch it from and is
    not guaranteed to have anything to do with the project a session is
    actually working in)."""
    _require_bm_store()
    project_root = arguments.get("project_root")
    if not project_root or not isinstance(project_root, str):
        raise ToolError("project_root (a non-empty string path) is required")
    start = os.path.abspath(os.path.expanduser(project_root))
    root, source = bm_store.resolve_root(start=start)
    if root is None:
        raise ToolError(
            "no BrotherMode project found at or above %r (checked "
            "BROTHERMODE_ROOT, then .brothermode markers, then .git)" % project_root)
    return root, source


def _dump_store(root):
    """Open read-only, dump every table with default-deny redaction
    (raw=False, the only mode this server ever uses), close. Reused by
    every tool below except bm_status, which calls bm_store.verify()
    instead since it needs invariant checks, not row contents."""
    store = bm_store.ReadOnlyStore(root)
    try:
        return store.dump(raw=False)
    finally:
        store.close()


# ---------------------------------------------------------------------------
# The four tools.
# ---------------------------------------------------------------------------

def tool_bm_status(arguments):
    root, source = _resolve_root(arguments)
    lines = ["project root: %s (found via %s)" % (root, source)]
    store_file = bm_store.store_path(root)
    if not os.path.isfile(store_file):
        lines.append("no store exists at %s yet" % store_file)
        lines.append("healthy: nothing to check (no store)")
        return "\n".join(lines)
    try:
        problems = bm_store.verify(root)
    except bm_store.OwnershipRefused as e:
        lines.append("could not open the store: %s: %s" % (e.reason, e))
        return "\n".join(lines)
    except bm_store.StoreCorrupt as e:
        lines.append("store is corrupt: %s" % e)
        if e.quarantine_path:
            lines.append("quarantined at: %s" % e.quarantine_path)
        return "\n".join(lines)
    if not problems:
        lines.append("healthy: yes (0 problems)")
    else:
        lines.append("healthy: no (%d problem(s)):" % len(problems))
        for p in problems:
            lines.append("  - %s" % p)
    return "\n".join(lines)


_VALID_STATES = ("active", "parked", "complete", "adopted")


def tool_bm_active_work(arguments):
    root, _source = _resolve_root(arguments)
    state = arguments.get("state", "active")
    if state != "all" and state not in _VALID_STATES:
        raise ToolError(
            "state must be one of %s or 'all', got %r"
            % (_VALID_STATES, state))
    data = _dump_store(root)
    records = data["records"]
    if state != "all":
        records = [r for r in records if r["state"] == state]
    if not records:
        return "no records in state %r at %s" % (state, root)
    records = sorted(records, key=lambda r: (r["state"], r["name"] or "", r["lifecycle_uuid"]))
    lines = []
    for r in records:
        lines.append(
            "- %s (%s, v%s, %s, state=%s) tier=%s objective=%s"
            % (r["name"] or "(unnamed)", r["lifecycle_uuid"][:8], r["version"],
               r["lifetime"], r["state"], r["tier"] or "(none)",
               r["objective"] or "(none)"))
    return "\n".join(lines)


def tool_bm_fences(arguments):
    root, _source = _resolve_root(arguments)
    data = _dump_store(root)
    active_by_uuid = {r["lifecycle_uuid"]: r for r in data["records"] if r["state"] == "active"}
    fences = [c for c in data["claims"] if c["lifecycle_uuid"] in active_by_uuid]
    if not fences:
        return "no active fences at %s" % root
    fences = sorted(fences, key=lambda c: (c["path"] or "", c["lifecycle_uuid"]))
    lines = []
    for c in fences:
        r = active_by_uuid[c["lifecycle_uuid"]]
        lines.append(
            "- %s claimed by %s (%s)"
            % (c["path"], r["name"] or "(unnamed)", c["lifecycle_uuid"][:8]))
    return "\n".join(lines)


def tool_bm_decisions(arguments):
    root, _source = _resolve_root(arguments)
    limit = arguments.get("limit", 20)
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        raise ToolError("limit must be an integer, got %r" % (limit,))
    if limit <= 0:
        raise ToolError("limit must be a positive integer, got %d" % limit)
    record_name = arguments.get("record_name")
    data = _dump_store(root)
    by_uuid = {r["lifecycle_uuid"]: r for r in data["records"]}
    decisions = data["decisions"]
    if record_name:
        decisions = [
            d for d in decisions
            if by_uuid.get(d["lifecycle_uuid"], {}).get("name") == record_name
        ]
    decisions = sorted(decisions, key=lambda d: d["created_at"], reverse=True)[:limit]
    if not decisions:
        return "no decisions recorded at %s" % root
    lines = []
    for d in decisions:
        r = by_uuid.get(d["lifecycle_uuid"], {})
        lines.append(
            "- [%s] %s (%s) topic=%s: %s"
            % (d["created_at"], r.get("name") or "(unknown record)",
               d["lifecycle_uuid"][:8], d["topic"] or "(no topic)",
               d["text"] or "(empty)"))
    return "\n".join(lines)


TOOLS = [
    {
        "name": "bm_status",
        "description": (
            "Report whether the BrotherMode store at a project is healthy: "
            "whether a store exists yet, bm_store.py verify() problems "
            "(an empty list means healthy), and store corruption or "
            "ownership refusals if opening it fails. Read-only: opens the "
            "store via bm_store.ReadOnlyStore, never creates one."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root": {
                    "type": "string",
                    "description": (
                        "A path at or inside the BrotherMode project to "
                        "check. Resolved exactly like the bm_store.py CLI: "
                        "the BROTHERMODE_ROOT environment variable wins if "
                        "set, otherwise the nearest .brothermode marker "
                        "walking up from this path, otherwise the nearest "
                        ".git."
                    ),
                }
            },
            "required": ["project_root"],
        },
    },
    {
        "name": "bm_active_work",
        "description": (
            "List records (fenced units of work) in a project's store, "
            "filtered by state. Every founder-typed field (name, "
            "objective, tier) passes through the same default-deny "
            "redaction bm_store.py dump uses; there is no raw/unredacted "
            "mode in this server."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root": {
                    "type": "string",
                    "description": "Same resolution rule as bm_status.",
                },
                "state": {
                    "type": "string",
                    "enum": ["active", "parked", "complete", "adopted", "all"],
                    "description": "Which state to list. Defaults to active.",
                },
            },
            "required": ["project_root"],
        },
    },
    {
        "name": "bm_fences",
        "description": (
            "List the file paths currently fenced by active records (the "
            "one-writer-per-path boundary while a record is active). Paths "
            "pass through the same redaction as bm_store.py dump."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root": {
                    "type": "string",
                    "description": "Same resolution rule as bm_status.",
                }
            },
            "required": ["project_root"],
        },
    },
    {
        "name": "bm_decisions",
        "description": (
            "List recorded decisions (topic and text), most recent first. "
            "Topic and text pass through the same redaction as bm_store.py "
            "dump."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root": {
                    "type": "string",
                    "description": "Same resolution rule as bm_status.",
                },
                "record_name": {
                    "type": "string",
                    "description": (
                        "Optional: only decisions belonging to the record "
                        "with exactly this pre-redaction name."
                    ),
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of decisions to return. Defaults to 20.",
                },
            },
            "required": ["project_root"],
        },
    },
]

TOOL_HANDLERS = {
    "bm_status": tool_bm_status,
    "bm_active_work": tool_bm_active_work,
    "bm_fences": tool_bm_fences,
    "bm_decisions": tool_bm_decisions,
}


# ---------------------------------------------------------------------------
# JSON-RPC 2.0 over stdio: newline-delimited, UTF-8, one message per line,
# nothing else ever written to stdout (spec requirement, restated in the
# module docstring). json.dumps() without indent= never emits a literal
# embedded newline inside the line it produces (control characters inside
# string values are escaped, e.g. "\n"), which is what "messages MUST NOT
# contain embedded newlines" requires.
# ---------------------------------------------------------------------------

def _send(obj):
    sys.stdout.write(json.dumps(obj, sort_keys=True))
    sys.stdout.write("\n")
    sys.stdout.flush()


def _result(id_, result):
    return {"jsonrpc": "2.0", "id": id_, "result": result}


def _error(id_, code, message, data=None):
    err = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": id_, "error": err}


def handle_initialize(msg):
    params = msg.get("params") or {}
    requested = params.get("protocolVersion")
    # This server supports exactly one protocol version. Per spec: if the
    # server supports the requested version, echo it back; otherwise
    # respond with a version it does support. There is only ever one
    # option here, so both branches send the same thing.
    version_to_send = PROTOCOL_VERSION
    if requested != PROTOCOL_VERSION:
        _log("client requested protocolVersion %r; this server only speaks "
             "%r and is answering with that" % (requested, PROTOCOL_VERSION))
    return _result(msg["id"], {
        "protocolVersion": version_to_send,
        "capabilities": {"tools": {}},
        "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        "instructions": (
            "Read-only BrotherMode project queries. Every tool takes a "
            "project_root path. This server never writes, deletes, or "
            "transitions anything in the store it reads."
        ),
    })


def handle_ping(msg):
    return _result(msg["id"], {})


def handle_tools_list(msg):
    return _result(msg["id"], {"tools": TOOLS})


def handle_tools_call(msg):
    params = msg.get("params") or {}
    name = params.get("name")
    arguments = params.get("arguments") or {}
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        return _error(msg["id"], -32602, "Unknown tool: %r" % (name,))
    try:
        text = handler(arguments)
    except ToolError as e:
        return _result(msg["id"], {
            "content": [{"type": "text", "text": str(e)}],
            "isError": True,
        })
    except Exception as e:  # a bug here must still answer the protocol, not crash the process
        _log("tool %r raised an unexpected exception: %r" % (name, e))
        return _result(msg["id"], {
            "content": [{"type": "text", "text": "internal error: %r" % (e,)}],
            "isError": True,
        })
    return _result(msg["id"], {
        "content": [{"type": "text", "text": text}],
        "isError": False,
    })


_METHODS = {
    "initialize": handle_initialize,
    "ping": handle_ping,
    "tools/list": handle_tools_list,
    "tools/call": handle_tools_call,
}


def _handle_line(line):
    """Parse and dispatch one JSON-RPC message. Returns the response dict
    to send, or None when nothing should be sent (a notification, or a
    known-but-response-free method)."""
    try:
        msg = json.loads(line)
    except ValueError as e:
        return _error(None, -32700, "Parse error: %s" % e)
    if not isinstance(msg, dict):
        return _error(None, -32600, "Invalid Request: top-level JSON must be an object")
    method = msg.get("method")
    has_id = "id" in msg
    if method == "notifications/initialized":
        return None  # notification: no response, nothing to initialize (stateless server)
    handler = _METHODS.get(method)
    if handler is None:
        if has_id:
            return _error(msg.get("id"), -32601, "Method not found: %r" % (method,))
        return None  # unknown notification: ignore, never respond to a notification
    if not has_id:
        # A request-shaped method arriving as a notification (no id): per
        # JSON-RPC, notifications never get a reply, even from a method
        # that would normally answer. Log it and move on.
        _log("received %r with no id (notification); no response is sent" % method)
        return None
    return handler(msg)


def main():
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        response = _handle_line(line)
        if response is not None:
            _send(response)
    return 0


if __name__ == "__main__":
    sys.exit(main())
