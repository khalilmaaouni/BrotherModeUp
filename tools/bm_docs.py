#!/usr/bin/env python3
"""BrotherMode documentation engine: the folder a stranger can read.

WHAT THIS IS FOR
  BrotherMode records more about a project than any document it produces. This
  writes the documents, almost entirely from what is already recorded, into a
  numbered folder whose reading order is unambiguous:

      Documentation/
        00-START-HERE.md
        10-business/     BA-SUMMARY REQUIREMENTS WBS SCHEDULE
        20-technical/    ARCHITECTURE DATA-MODEL PROCESS-DIAGRAMS
                         DEPENDENCIES CODE-MAP WHITEPAPER
        30-decisions/    INDEX.md and the D-<n>-<slug>.md packs
        40-handover/     HANDOVER.md RUNBOOK.md
        90-generated/    facts.json

  Phase B of docs/superpowers/specs/2026-07-30-documentation-and-gate-packs
  -design.md, section 5.

THREE SOURCES, IN COST ORDER (section 5.2)
  PROJECTION, free. Store rows rendered directly: the work breakdown from work
  records and their claims, the schedule from records plus the dependency graph
  their overlapping claims imply (a mermaid gantt plus a critical path computed
  by longest path over that graph), the decision index from candidates, rules,
  receipts and recorded decisions, notes and lineage inline.

  INTROSPECTION, free. The repository and the store's own schema read as they
  are: a mermaid entity diagram built by introspecting sqlite, an import graph
  built by parsing the imports, a module inventory and a test inventory.

  NARRATIVE, last and least. Assembled from recorded fields, never invented, and
  cached against a hash of exactly those fields (I12), so unchanged facts do not
  regenerate a paragraph.

THE FOUR RULES THIS FILE LIVES BY
  I10, GENERATED OUTPUT NEVER DESTROYS HUMAN TEXT. Every document ends with a
  human block, and anything a human writes between the markers is carried
  through every regeneration byte for byte. The suite proves it with a
  deliberately destructive variant that must fail.

  I12, PROSE IS CACHED AGAINST FACTS. Every narrative block records the hash of
  the facts it describes. On regeneration a block whose hash still matches is
  reused verbatim and its writer is never called at all, which is what makes
  "unchanged facts do not regenerate" a measurable claim rather than a hope.

  I13, TIERS RAISE ONLY. The tier is chosen from measured signals, and the
  choice plus the signals that made it are printed and written into START-HERE.
  An automatic decision may only increase depth: the last tier is remembered in
  facts.json and acts as a floor. Lowering takes --tier, which is a founder
  saying so out loud.

  DETERMINISM. Two regenerations in a row are byte identical. No generation
  timestamp reaches a document body, every list is sorted, and every scan skips
  the Documentation folder itself, because a generator that reads its own output
  churns forever and every review then opens on a diff that means nothing.

WHAT THIS FILE MAY NOT DO
  It never writes the store: bm_store.py stays the single writer, and every file
  it produces goes through bm_store.write_generated_document, the one funnel that
  redacts before anything reaches disk and protects the human blocks. No network,
  no subprocess. It never imports the optional exporter (section 5.6): that lives
  in bm_docs_export.py with its own command, so the mandatory path cannot acquire
  an optional dependency by accident.

WHAT IT DELIBERATELY DOES NOT DO
  It writes no narrative the store did not record. Where a field is empty the
  document says the field is empty and names the command that would fill it. A
  generator that invents a rationale puts words in the founder's mouth.

  It quotes no candidate raw text. That is the most sensitive column in the
  store and it is withheld here exactly as `bm_learn.py show-candidate` withholds
  it.

Python 3.9, standard library only.

No em or en dashes anywhere in this file, its comments, or its output.

Usage:
  python3 tools/bm_docs.py tier                 # the signals and the decision
  python3 tools/bm_docs.py generate             # write the folder
  python3 tools/bm_docs.py generate --tier 3    # override, may lower
  python3 tools/bm_docs.py facts --json         # the projected facts
"""

import datetime
import hashlib
import importlib.util
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    """Load a sibling module by PATH, the same way bm_packs.py does: this file
    is invoked from arbitrary working directories and must not depend on
    whatever sys.path the caller happened to have."""
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bs = _load("bm_store")
L = _load("bm_learning")

# The folder, and the numbered layout of section 5.1. Numbered so a stranger's
# reading order is unambiguous rather than alphabetical by accident.
DOC_ROOT = "Documentation"

# (relative path, minimum tier, one line saying what it is). ONE list, read by
# the renderer, by START-HERE, by the CLI report and by the suite: a document
# that goes missing shows up as a missing file rather than as a page nobody
# notices is gone.
#
# DIVERGENCE FROM THE SPEC, recorded rather than smoothed over: section 5.1
# lists BA-SUMMARY.md in the layout and section 5.3's tier table does not place
# it in any tier, and the tier table names a "whitepaper" that the layout does
# not place in a directory. BA-SUMMARY is emitted at tier 2 beside REQUIREMENTS
# (it is the business narrative those requirements belong to) and the whitepaper
# is emitted at tier 3 as 20-technical/WHITEPAPER.md.
# IN READING ORDER, which is why the directories are numbered: a stranger opens
# them top to bottom. The tier column says which of them exist at which depth,
# and it is deliberately NOT the sort key, because sorting by tier would present
# a reader with 00, then 30, then 40, then back to 10.
FILES = (
    ("00-START-HERE.md", 1,
     "the reading order, the tier and the signals that chose it"),
    ("10-business/BA-SUMMARY.md", 2,
     "what the project is trying to do, in business language"),
    ("10-business/REQUIREMENTS.md", 2,
     "the objectives and the standing rules that constrain them"),
    ("10-business/WBS.md", 2,
     "the work breakdown, projected from the work records"),
    ("10-business/SCHEDULE.md", 2,
     "a gantt of the recorded work plus its critical path"),
    ("20-technical/ARCHITECTURE.md", 2,
     "the shape of the code, by module and by layer"),
    ("20-technical/DATA-MODEL.md", 2,
     "an entity diagram introspected from the live schema"),
    ("20-technical/PROCESS-DIAGRAMS.md", 3,
     "the recorded lifecycle of a work record, as a state diagram"),
    ("20-technical/DEPENDENCIES.md", 2,
     "the import graph, parsed from the source"),
    ("20-technical/CODE-MAP.md", 3,
     "every module and every test file, with sizes"),
    ("20-technical/WHITEPAPER.md", 3,
     "the long-form account of why this project is built this way"),
    ("30-decisions/INDEX.md", 1,
     "every decision, its state, and the pack that reviews it"),
    ("40-handover/HANDOVER.md", 1,
     "everything a human with no AI needs to take this over"),
    ("40-handover/RUNBOOK.md", 2,
     "how to run it, how to test it, how to recover it"),
    ("90-generated/facts.json", 1,
     "the machine-readable facts every page above was projected from"),
)

TIERS = {1: "lean", 2: "standard", 3: "full"}

# The human block markers come from bm_store, which owns them because the file
# funnel has to see them to protect what is between them (I10). One definition,
# so this file and the funnel can never disagree about where human text begins.
HUMAN_BEGIN = bs.HUMAN_BLOCK_BEGIN
HUMAN_END = bs.HUMAN_BLOCK_END

# The narrative cache record (I12). Written by the generator, read back by the
# generator. Without a recorded hash there is nothing for a changed fact to
# disagree with, so the cache would either never reuse or never refresh.
_PROSE_OPEN = re.compile(
    r"^<!-- bm-prose: id=(?P<id>[a-z0-9-]+) sha256=(?P<sha>[0-9a-f]{64}) -->$")
_PROSE_CLOSE = "<!-- bm-prose:end -->"

_SKIP_DIRS = frozenset((".git", ".brothermode", "node_modules", "__pycache__",
                        ".venv", "venv", ".mypy_cache", ".pytest_cache",
                        ".tox", "dist", "build", ".eggs", DOC_ROOT))
# A file bigger than this is data, not source. Bounded so `generate` stays a
# command a founder runs at a gate rather than a batch job.
_MAX_SOURCE_BYTES = 400000
# How many rows any one table in any one document lists in full. The COUNT is
# always exact; this caps the listing so one busy area does not produce a
# hundred-line section nobody reads.
_MAX_LISTED = 40

_DEF_RE = re.compile(r"^(\s*)(def|class)\s+([A-Za-z_][A-Za-z0-9_]*)")
_IMPORT_RE = re.compile(
    r"^\s*(?:import\s+(?P<plain>[A-Za-z_][\w.]*(?:\s*,\s*[A-Za-z_][\w.]*)*)"
    r"|from\s+(?P<mod>[A-Za-z_.][\w.]*)\s+import\s+(?P<names>[\w,\s*()]+))")
_TEST_RE = re.compile(r"^\s*def\s+(test_[A-Za-z0-9_]*)")


class DocsError(Exception):
    """A refusal with a reason a human can act on. Carries `reason` in the same
    shape bm_store.OwnershipRefused and bm_packs.PackError do, so the CLI prints
    all three alike."""

    def __init__(self, reason, message):
        Exception.__init__(self, message)
        self.reason = reason


def _out(msg=""):
    sys.stdout.write("%s\n" % msg)


def _err(msg):
    sys.stderr.write("%s\n" % msg)


def _parse(argv, known, wants_value=()):
    """Flags into a dict, REFUSING anything unrecognized, exactly as
    bm_learn.py and bm_packs.py do."""
    positional, kv, i = [], {}, 0
    while i < len(argv):
        tok = argv[i]
        if tok.startswith("--"):
            name = tok[2:]
            if name not in known:
                _err("bm_docs: unrecognized flag --%s (recognized: %s)"
                     % (name, ", ".join("--" + k for k in sorted(known))))
                sys.exit(2)
            if name in wants_value:
                if i + 1 >= len(argv):
                    _err("bm_docs: --%s needs a value" % name)
                    sys.exit(2)
                kv[name] = argv[i + 1]
                i += 2
                continue
            kv[name] = True
            i += 1
            continue
        positional.append(tok)
        i += 1
    return positional, kv


def _d(text, limit=300):
    """Every store-derived string that reaches a document passes through here:
    control characters stripped, length capped. A newline inside an objective
    could otherwise forge a markdown heading, and a heading is structure these
    documents are writing on purpose."""
    return L.safe_display(text or "", limit)


def _cell(text, limit=120):
    """_d, plus the two characters a markdown table treats as syntax."""
    return _d(text, limit).replace("|", "/").replace("\n", " ")


def _flat(text, limit=80):
    """A label safe inside a mermaid node or a gantt row, where a colon, a comma,
    a quote or a bracket is syntax."""
    flat = re.sub(r"[:,\"'\[\]{}()<>#;|]", " ", _d(text, limit)).strip()
    # A LEADING dash or dot is stripped too. A gantt row whose task name starts
    # with a dash reads as syntax to the renderer rather than as a label, and a
    # record called "-h" is not hypothetical: this project's own store has one,
    # created by a probe that took a help flag as a record name.
    flat = flat.lstrip("-.=*+ ").strip()
    return flat or "unnamed"


def _rows(store, sql, params=()):
    """Every read this file makes goes through bm_store._exec, which is the one
    place a busy database becomes a named refusal and a damaged one becomes a
    quarantine (I6). A private name reached across a module boundary is a cost,
    and it is the smaller cost: a bare store.conn.execute here would be a second
    error policy for the same connection."""
    return [dict(r) for r in bs._exec(store, sql, params).fetchall()]


# ---------------------------------------------------------------------------
# Reading an existing document: human blocks (I10) and prose cache (I12).
# ---------------------------------------------------------------------------

def read_existing(path):
    """Parse an existing document for the two things regeneration must not lose.

    Returns {"human": [str, ...], "prose": {id: {"sha": str, "body": str}}} and
    never raises on a malformed file: an unparseable document is regenerated,
    and the human blocks are recovered by marker scan, which is the one part
    that must survive a file somebody hand-edited.

    THE HUMAN MARKERS ARE READ FIRST, AND A PROSE MARKER IS ONLY READ OUTSIDE
    THEM. This is the lesson bm_packs.read_existing learned the expensive way:
    a reviewer who pastes a generated header into the block the file TELLS them
    to write in must not thereby reconfigure the generator. Inside a human block
    every line is prose, including one that looks like machine configuration.

    A second begin marker inside a block is CONTENT, not a nested block, for the
    same reason: resetting the buffer on it drops every line written before it.
    """
    out = {"human": [], "prose": {}}
    if not os.path.isfile(path):
        return out
    with io.open(path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    inside_human = False
    human_buf = []
    prose_id = None
    prose_sha = ""
    prose_buf = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped == HUMAN_BEGIN and not inside_human:
            inside_human = True
            human_buf = []
            continue
        if stripped == HUMAN_END and inside_human:
            inside_human = False
            out["human"].append("\n".join(human_buf))
            human_buf = []
            continue
        if inside_human:
            human_buf.append(line)
            continue
        if prose_id is not None:
            if stripped == _PROSE_CLOSE:
                out["prose"][prose_id] = {"sha": prose_sha,
                                          "body": "\n".join(prose_buf)}
                prose_id, prose_sha, prose_buf = None, "", []
            else:
                prose_buf.append(line)
            continue
        m = _PROSE_OPEN.match(stripped)
        if m:
            prose_id = m.group("id")
            prose_sha = m.group("sha")
            prose_buf = []
    if inside_human and human_buf:
        # An unterminated human block. KEPT, because losing a paragraph because
        # somebody forgot the closing marker is exactly the destruction I10
        # forbids. The regenerated file closes it.
        out["human"].append("\n".join(human_buf))
    # An unterminated prose block is DROPPED, which is the opposite decision and
    # the right one: a half-written cache record cannot be trusted to describe
    # the facts its hash claims, and the cost of dropping it is that the block
    # gets written again.
    return out


def _neutralize_prose_markers(body):
    """A narrative body may not contain the cache markers. Nothing generated
    here would, but a recorded field it quotes could, and a forged close marker
    would truncate the cache record and silently swallow the rest of the page."""
    return body.replace("bm-prose:", "bm-prose ")


# ---------------------------------------------------------------------------
# Time, and why almost none of it reaches a document.
# ---------------------------------------------------------------------------

def _parse_iso(value):
    """A store timestamp into a datetime, or None. Never raises: a document is
    not worth a traceback over a row somebody hand-edited."""
    try:
        return datetime.datetime.strptime((value or "").strip(),
                                          "%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, TypeError):
        return None


def _days_between(start, end):
    a, b = _parse_iso(start), _parse_iso(end)
    if a is None or b is None or b < a:
        return 1
    return max(1, (b - a).days)


def _date_only(value):
    dt = _parse_iso(value)
    if dt is None:
        return "1970-01-01"
    return dt.strftime("%Y-%m-%d")


def _span_bucket(days):
    """The recorded activity span, in buckets.

    Measured from the FIRST recorded row to the LAST, never to the wall clock.
    Age measured against now would change a signal, and therefore possibly a
    tier, and therefore the bytes of START-HERE, on a day when nothing about the
    project changed at all. That is exactly the churn determinism forbids."""
    if days is None:
        return "nothing recorded yet"
    if days < 7:
        return "under a week of recorded activity"
    if days < 31:
        return "one to four weeks of recorded activity"
    if days < 93:
        return "one to three months of recorded activity"
    return "over three months of recorded activity"


# ---------------------------------------------------------------------------
# The critical path: a pure longest-path over a weighted DAG.
# ---------------------------------------------------------------------------

def critical_path(weights, edges):
    """The longest path through a weighted directed acyclic graph.

    `weights` maps node id to a positive number. `edges` is an iterable of
    (from, to) pairs. Returns (path, total) where path is the list of node ids
    in order and total is the summed weight.

    Longest path by SUMMED NODE WEIGHT, which is what a critical path is: the
    chain of work whose durations add up to the earliest possible finish. Ties
    break on the node id so the answer is deterministic rather than dictionary
    ordered.

    A cycle RAISES. A schedule with a cycle has no critical path, and the useful
    thing to do with an impossible graph is to name it: silently dropping an edge
    would publish a shorter path as if it were the answer."""
    nodes = sorted(weights)
    known = set(nodes)
    incoming = dict((n, 0) for n in nodes)
    forward = dict((n, []) for n in nodes)
    seen_edges = set()
    for a, b in edges:
        if a not in known or b not in known or (a, b) in seen_edges or a == b:
            continue
        seen_edges.add((a, b))
        forward[a].append(b)
        incoming[b] += 1
    order = []
    ready = sorted(n for n in nodes if incoming[n] == 0)
    while ready:
        n = ready.pop(0)
        order.append(n)
        for m in sorted(forward[n]):
            incoming[m] -= 1
            if incoming[m] == 0:
                ready.append(m)
                ready.sort()
    if len(order) != len(nodes):
        stuck = sorted(n for n in nodes if n not in set(order))
        raise DocsError(
            "schedule-cycle",
            "the work dependency graph has a cycle through %s, so it has no "
            "critical path. A cycle means two records each wait for the other; "
            "look at their claimed files." % ", ".join(stuck))
    best = dict((n, (0, [])) for n in nodes)
    for n in order:
        total, path = best[n]
        total += weights[n]
        path = path + [n]
        best[n] = (total, path)
        for m in sorted(forward[n]):
            if (total, path) > best[m]:
                best[m] = (total, path)
    if not nodes:
        return [], 0
    # The winner is the largest total, with the node id as the final tiebreak.
    # Spelled out as a loop rather than a key function so the ordering is
    # obvious: a critical path that changes between two runs of the same graph
    # would break the determinism this engine promises.
    winner = None
    for n in nodes:
        if winner is None or (best[n][0], n) > (best[winner][0], winner):
            winner = n
    return best[winner][1], best[winner][0]


# ---------------------------------------------------------------------------
# Projection: store rows into facts.
# ---------------------------------------------------------------------------

def work_items(store):
    """Every work record, oldest first, with its claims, decisions and digests.

    Oldest first because a work breakdown is a history: the order the work was
    claimed in is the order a reader needs it in."""
    out = []
    for rec in _rows(store, "SELECT * FROM records ORDER BY created_at, "
                            "lifecycle_uuid"):
        uuid = rec["lifecycle_uuid"]
        claims = [r["path"] for r in _rows(
            store, "SELECT path FROM claims WHERE lifecycle_uuid=? "
                   "ORDER BY path", (uuid,))]
        decisions = _rows(
            store, "SELECT seq, topic, text, created_at FROM decisions "
                   "WHERE lifecycle_uuid=? ORDER BY seq", (uuid,))
        digests = _rows(
            store, "SELECT seq, next_intent, blockers, files_note, created_at "
                   "FROM digests WHERE lifecycle_uuid=? ORDER BY seq", (uuid,))
        transitions = _rows(
            store, "SELECT from_state, to_state, note, at FROM transitions "
                   "WHERE lifecycle_uuid=? ORDER BY id", (uuid,))
        out.append({
            "id": uuid,
            "short": uuid[:8],
            "name": rec["name"],
            "lifetime": rec["lifetime"],
            "state": rec["state"],
            "objective": rec["objective"],
            "owner": rec["owner"],
            "tier": rec["tier"],
            "check_cmd": rec["check_cmd"],
            "evidence": rec["evidence"],
            "created_at": rec["created_at"],
            "updated_at": rec["updated_at"],
            "files": claims,
            "decisions": decisions,
            "digests": digests,
            "transitions": transitions,
        })
    return out


def work_graph(root, items):
    """The work dependency graph, DERIVED rather than declared.

    BrotherMode serializes overlapping work by law: two records may not hold the
    same file at once, so a record that claims a path an earlier record also
    claims could only run after it. That is the dependency, and it is a fact
    about the recorded claims rather than a guess about intent. Edges therefore
    run strictly forward in creation order, which is also why the graph cannot
    contain a cycle.

    Weight is the recorded elapsed days of the record, minimum one, so a record
    opened and closed the same day still occupies a day on the chart."""
    nodes = []
    for item in items:
        nodes.append({
            "id": item["short"],
            "name": item["name"],
            "state": item["state"],
            "start": _date_only(item["created_at"]),
            "days": _days_between(item["created_at"], item["updated_at"]),
        })
    edges = []
    for i, earlier in enumerate(items):
        for later in items[i + 1:]:
            shared = sorted(set(
                "%s and %s" % (a, b)
                for a in earlier["files"] for b in later["files"]
                if bs.paths_overlap(a, b)))
            if shared:
                edges.append([earlier["short"], later["short"], shared[0]])
    weights = dict((n["id"], n["days"]) for n in nodes)
    path, total = critical_path(weights, [(a, b) for a, b, _why in edges])
    return {"nodes": nodes, "edges": edges, "critical_path": path,
            "critical_days": total}


def decision_rows(store, root):
    """Every decision a reader might need to review, from all four places the
    store keeps one, plus the pack on disk that reviews it if there is one."""
    packs = {}
    directory = os.path.join(root, DOC_ROOT, "30-decisions")
    if os.path.isdir(directory):
        for name in sorted(os.listdir(directory)):
            m = re.match(r"^D-(\d+)-.*\.md$", name)
            if m:
                packs[int(m.group(1))] = "30-decisions/" + name
    out = []
    cands = _rows(store, "SELECT * FROM learning_candidates "
                         "ORDER BY created_at, candidate_uuid")
    for i, cand in enumerate(cands, 1):
        receipts = _rows(
            store, "SELECT issued_at, consumed_at FROM "
                   "learning_approval_receipts WHERE candidate_uuid=? "
                   "ORDER BY issued_at", (cand["candidate_uuid"],))
        out.append({
            "index": i,
            "kind": "candidate",
            "id": cand["candidate_uuid"][:8],
            "title": cand["proposed_action"] or "(no action recorded)",
            "trigger": cand["proposed_trigger"],
            "because": cand["proposed_because"],
            "scope": L.safe_scope(cand["proposed_scope_type"],
                                  cand["proposed_scope_key"]),
            "status": cand["status"],
            "created_at": cand["created_at"],
            "source_type": cand["source_type"],
            "record": (cand["source_record_uuid"] or "")[:8],
            "rule": (cand["resulting_rule_uuid"] or "")[:8],
            "receipts": len(receipts),
            "pack": packs.get(i, ""),
        })
    # THE STORE'S OWN LISTER, not a SELECT of my own. A rule's text lives in
    # learning_rule_versions and only the CURRENT version is the rule, so a
    # plain SELECT over learning_rules returns rows with no trigger and no
    # action at all: reproduced against this project's own store, which raised
    # KeyError('action_text') on the first real run while the suite was green.
    # This lister also excludes forgotten rules at the lowest level, which is a
    # policy no caller should be re-implementing.
    for rule in sorted(store.list_learning_rules(),
                       key=lambda r: (r["created_at"], r["rule_uuid"])):
        out.append({
            "index": 0,
            "kind": "rule",
            "id": rule["rule_uuid"][:8],
            "title": rule["action_text"] or "(no action recorded)",
            "trigger": rule["trigger_text"],
            "because": rule["because_text"],
            "scope": L.safe_scope(rule["scope_type"], rule["scope_key"]),
            "status": rule["state"],
            "created_at": rule["created_at"],
            "source_type": "approved rule",
            "record": "",
            "rule": rule["rule_uuid"][:8],
            "receipts": 0,
            "pack": "",
        })
    return out


def note_rows(store):
    out = []
    for n in store.list_notes():
        where = "%s:%s" % (n["anchor_type"], _cell(n["anchor_key"], 80))
        if n["anchor_line"]:
            where += ":%d" % n["anchor_line"]
        state = "open"
        if n["resolved_at"]:
            state = "resolved"
        if n["overridden_at"]:
            state += ", overridden"
        out.append({
            "id": n["note_uuid"][:8],
            "kind": n["kind"],
            "severity": n["severity"],
            "author": n["author"],
            "author_kind": n["author_kind"],
            "anchor": where,
            "state": state,
            "created_at": n["created_at"],
            "body": n["body"],
            "resolution": n["resolution"],
            "override_by": n["override_by"],
            "override_reason": n["override_reason"],
        })
    return out


def lineage(store, items, decisions, notes):
    """Everything that touched a decision, in order, with authors.

    A query, not a stored field (spec section 6). Every event carries the
    timestamp the store recorded and the author the store recorded, so a chain
    with no author reads as a chain with no author rather than as mine."""
    out = {}
    by_note_anchor = {}
    for n in notes:
        atype, _, akey = n["anchor"].partition(":")
        key = akey.split(":")[0]
        by_note_anchor.setdefault((atype, key), []).append(n)
    for row in decisions:
        if row["kind"] != "candidate":
            continue
        events = [{
            "at": row["created_at"],
            "who": "captured from %s" % row["source_type"],
            "what": "candidate %s recorded" % row["id"],
        }]
        for n in by_note_anchor.get(("candidate", row["id"]), []):
            events.append({
                "at": n["created_at"],
                "who": "%s (%s)" % (n["author"] or "unnamed", n["author_kind"]),
                "what": "%s%s: %s" % (n["kind"],
                                      " [%s]" % n["severity"] if n["severity"]
                                      else "", n["body"]),
            })
        if row["receipts"]:
            events.append({"at": row["created_at"], "who": "the founder",
                           "what": "%d approval receipt(s) minted"
                                   % row["receipts"]})
        if row["rule"]:
            events.append({"at": row["created_at"], "who": "the store",
                           "what": "became rule %s" % row["rule"]})
        events.sort(key=lambda e: (e["at"], e["what"]))
        out[row["id"]] = events
    for item in items:
        for dec in item["decisions"]:
            key = "%s#%d" % (item["short"], dec["seq"])
            out[key] = [{
                "at": dec["created_at"],
                "who": item["owner"] or "unrecorded owner",
                "what": "%s: %s" % (dec["topic"] or "untitled", dec["text"]),
            }]
    return out


# ---------------------------------------------------------------------------
# Introspection: the repository and the live schema.
# ---------------------------------------------------------------------------

def _source_files(root, suffixes=(".py",)):
    """Every source file under root, repo-relative and sorted.

    The Documentation folder is skipped by _SKIP_DIRS, and that is not tidiness:
    a generator that reads its own output produces a different answer on every
    run, so regeneration churns and the determinism claim dies."""
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames
                             if d not in _SKIP_DIRS and not d.startswith("."))
        for name in sorted(filenames):
            if not name.endswith(suffixes):
                continue
            full = os.path.join(dirpath, name)
            try:
                if os.path.getsize(full) > _MAX_SOURCE_BYTES:
                    continue
            except OSError:
                continue
            out.append(os.path.relpath(full, root).replace("\\", "/"))
    return sorted(out)


def _read_text(root, rel):
    try:
        with io.open(os.path.join(root, rel), encoding="utf-8",
                     errors="replace") as fh:
            return fh.read()
    except OSError as exc:
        # Reported, never swallowed: a file the scan could not read is a hole in
        # the inventory and the document says so.
        return "# unreadable: %s\n" % exc


def module_inventory(root):
    """Every module and every test file, with what a reader needs to choose one
    to open: how big it is, what it defines, and its first docstring line."""
    modules, tests = [], []
    for rel in _source_files(root):
        text = _read_text(root, rel)
        lines = text.split("\n")
        defs, classes, top = 0, 0, []
        for line in lines:
            m = _DEF_RE.match(line)
            if not m:
                continue
            if m.group(2) == "class":
                classes += 1
            else:
                defs += 1
            if not m.group(1):
                top.append(m.group(3))
        doc = ""
        m = re.search(r'^\s*(?:"""|\'\'\')(.*)$', text, re.MULTILINE)
        if m:
            doc = m.group(1).strip().strip('"').strip("'")
        entry = {"path": rel, "lines": len(lines), "defs": defs,
                 "classes": classes, "doc": doc,
                 "top_level": sorted(top)[:12]}
        base = rel.rsplit("/", 1)[-1]
        if base.startswith("test_") or base.endswith("_test.py"):
            entry["tests"] = len(_TEST_RE.findall(text))
            tests.append(entry)
        else:
            modules.append(entry)
    return {"modules": modules, "tests": tests}


def _import_targets(line):
    """The dotted names one import line could be referring to, best first.

    `from a import b` MEANS a.b when b is a module, and that is the common shape
    of a package importing its own sibling. An earlier version of this scan read
    only the part after `from`, so `from app import pay` inside app/checkout.py
    resolved to the package `app`, found no file called that, and filed the whole
    thing under external dependencies: the one edge the diagram existed to draw
    was the one it dropped. Reproduced on a fixture with exactly those two files.

    Returns (candidates, head) where head is the top level name to count as
    external if no candidate resolves to a file in the tree."""
    m = _IMPORT_RE.match(line)
    if not m:
        return [], ""
    plain = m.group("plain")
    if plain:
        names = [n.strip() for n in plain.split(",") if n.strip()]
        return names, (names[0].split(".")[0] if names else "")
    mod = (m.group("mod") or "").strip()
    tail = re.sub(r"[()*]", " ", m.group("names") or "")
    leaves = [n.strip() for n in tail.split(",") if n.strip()]
    bare = mod.strip(".")
    if not bare:
        # A relative import with no module part (`from . import x`). The leaf is
        # the only name there is, and it names a sibling module.
        return leaves, ""
    return ["%s.%s" % (bare, leaf) for leaf in leaves] + [bare], \
        bare.split(".")[0]


def import_graph(root):
    """The import graph, parsed from the source.

    Only edges BETWEEN modules of this project are kept. A dependency on the
    standard library is real and is not a shape a reader needs a diagram of; an
    edge to a module that is not in the tree would also be an edge to a node the
    diagram cannot draw."""
    files = _source_files(root)
    local = {}
    for rel in files:
        local[rel[:-3].replace("/", ".")] = rel
        local.setdefault(rel.rsplit("/", 1)[-1][:-3], rel)
    edges, external = [], {}
    seen = set()
    for rel in files:
        for line in _read_text(root, rel).split("\n"):
            candidates, head = _import_targets(line)
            if not candidates:
                continue
            target = None
            for name in candidates:
                target = local.get(name) or local.get(name.split(".")[0])
                if target is not None:
                    break
            if target is None:
                if head:
                    external[head] = external.get(head, 0) + 1
                continue
            if target == rel:
                continue
            key = (rel, target)
            if key in seen:
                continue
            seen.add(key)
            edges.append([rel, target])
    # A module loaded by absolute path rather than by import name is invisible
    # to any import scan, and this project loads its siblings exactly that way
    # on purpose (a hostile sys.path must not be able to shadow bm_store). So the
    # loader is read too, and the document says which edges came from which
    # source rather than presenting a partial graph as complete.
    loader_edges = []
    for rel in files:
        text = _read_text(root, rel)
        for name in sorted(set(re.findall(r'_load\(\s*["\']([\w.]+)["\']\s*\)',
                                          text))):
            target = local.get(name)
            if target and target != rel and [rel, target] not in edges:
                loader_edges.append([rel, target])
    return {"nodes": files, "edges": sorted(edges),
            "loader_edges": sorted(loader_edges),
            "external": dict(sorted(external.items()))}


def data_model(store):
    """An entity model INTROSPECTED from the live schema.

    Read from sqlite_master and PRAGMA rather than from the DDL string in
    bm_store.py, because the question a reader has is what the database on this
    machine actually contains, including whatever a migration did to it."""
    tables = []
    for row in _rows(store, "SELECT name FROM sqlite_master WHERE type='table' "
                            "AND name NOT LIKE 'sqlite_%' ORDER BY name"):
        name = row["name"]
        if not re.match(r"^[A-Za-z0-9_]+$", name):
            # A table name that is not an identifier cannot be interpolated into
            # a PRAGMA, and PRAGMA takes no parameters. Reported rather than
            # skipped in silence.
            tables.append({"name": _cell(name), "columns": [],
                           "foreign_keys": [],
                           "note": "name is not a plain identifier; not "
                                   "introspected"})
            continue
        columns = []
        for col in _rows(store, "PRAGMA table_info(%s)" % name):
            columns.append({"name": col["name"], "type": col["type"] or "TEXT",
                            "notnull": bool(col["notnull"]),
                            "pk": bool(col["pk"])})
        fks = []
        for fk in _rows(store, "PRAGMA foreign_key_list(%s)" % name):
            fks.append({"column": fk["from"], "table": fk["table"],
                        "to": fk["to"]})
        tables.append({"name": name, "columns": columns,
                       "foreign_keys": sorted(
                           fks, key=lambda f: (f["table"], f["column"])),
                       "note": ""})
    return {"tables": tables}


def lifecycle_states(store):
    """The recorded lifecycle of a work record: the states the schema allows and
    the transitions this store has actually seen."""
    states = []
    for row in _rows(store, "SELECT sql FROM sqlite_master WHERE type='table' "
                            "AND name='records'"):
        m = re.search(r"state\s+TEXT[^,]*?CHECK\(state\s+IN\s*\(([^)]*)\)",
                      row["sql"] or "", re.IGNORECASE | re.DOTALL)
        if m:
            states = re.findall(r"'([a-z_]+)'", m.group(1))
    seen = _rows(store, "SELECT from_state, to_state, COUNT(*) AS n FROM "
                        "transitions GROUP BY from_state, to_state "
                        "ORDER BY from_state, to_state")
    return {"states": states,
            "observed": [{"from": r["from_state"] or "", "to": r["to_state"],
                          "count": r["n"]} for r in seen]}


def gate_command(root):
    """The command that proves this project works, DISCOVERED in the tree.

    Ordered by how much the project itself declares. Nothing is invented: when
    nothing is found the documents say nothing was found and tell the reader
    that the project does not declare a check command, which is a finding."""
    checks = (
        ("tools/test_all.py", "python3 tools/test_all.py",
         "the project ships a single gate script"),
        ("Makefile", "make test", "the Makefile declares a test target"),
        ("package.json", "npm test", "package.json declares a test script"),
        ("pytest.ini", "python3 -m pytest", "pytest is configured"),
        ("tox.ini", "python3 -m tox", "tox is configured"),
    )
    for rel, cmd, why in checks:
        full = os.path.join(root, rel)
        if not os.path.isfile(full):
            continue
        text = _read_text(root, rel)
        if rel == "Makefile" and not re.search(r"^test\s*:", text, re.M):
            continue
        if rel == "package.json" and '"test"' not in text:
            continue
        return {"command": cmd, "why": why}
    if _source_files(root):
        for rel in _source_files(root):
            base = rel.rsplit("/", 1)[-1]
            if base.startswith("test_"):
                return {"command": "python3 -m unittest discover",
                        "why": "test_*.py files exist but no runner is declared"}
    return {"command": "", "why": "this project declares no test command"}


# ---------------------------------------------------------------------------
# Signals and the tier (section 5.3, I13).
# ---------------------------------------------------------------------------

def signals(root, store, items, decisions, notes, inventory):
    contributors = set()
    for item in items:
        if (item["owner"] or "").strip():
            contributors.add(item["owner"].strip())
    for n in notes:
        if (n["author"] or "").strip() and n["author_kind"] == "human":
            contributors.add(n["author"].strip())
    stamps = sorted([i["created_at"] for i in items]
                    + [i["updated_at"] for i in items]
                    + [n["created_at"] for n in notes])
    span = _days_between(stamps[0], stamps[-1]) if len(stamps) > 1 else None
    gates = len(_rows(store, "SELECT receipt_uuid FROM "
                             "learning_approval_receipts"))
    risk = len([n for n in notes
                if n["kind"] in ("alert", "risk") and n["state"] == "open"])
    tracked = tracked_files(root)
    return {
        "tracked_files": tracked["count"],
        "tracked_files_source": tracked["source"],
        "contributors": len(contributors),
        "contributor_names": sorted(contributors),
        "work_records": len(items),
        "recorded_decisions": len([d for d in decisions
                                   if d["kind"] == "candidate"]),
        "gates": gates,
        "open_risk_flags": risk,
        "modules": len(inventory["modules"]),
        "test_files": len(inventory["tests"]),
        "activity_span": _span_bucket(span),
    }


def tracked_files(root):
    """How many files this project tracks.

    Git's index is read directly when it is there, because that is the number a
    contributor means, and because asking git would take a subprocess this file
    is not allowed to run (I3). Otherwise the source scan is used and the
    document says which of the two answered."""
    index = os.path.join(root, ".git", "index")
    why = "there is no readable git index"
    if os.path.isfile(index):
        paths = None
        try:
            paths = bs._git_index_tracked_paths(index)
        except Exception as exc:
            # Deliberately broad, and deliberately NOT silent. This parses a
            # binary format git owns, so anything it raises is the reason the
            # count came from somewhere else, and the page names that reason
            # rather than presenting a fallback as the real number.
            why = "the git index could not be read (%s)" % type(exc).__name__
        if paths:
            return {"count": len(paths), "source": "the git index"}
        if paths is not None:
            why = "the git index lists no path"
    scanned = _source_files(root, (".py", ".md", ".sh", ".json", ".toml",
                                   ".yml", ".yaml", ".txt", ".cfg", ".ini"))
    return {"count": len(scanned),
            "source": "a scan of the tree, because %s" % why}


def choose_tier(sig, floor=0, explicit=None):
    """The tier, the signals that chose it, and the reason, per section 5.3.

    Raise-only (I13). `floor` is the tier the last generation recorded, so an
    automatic decision can move up and can never move down: documentation that
    quietly got thinner is documentation a reader cannot trust to still contain
    what they read last week. `explicit` is a founder passing --tier, which is
    the one way down and is recorded as such."""
    reasons = []
    tier = 1
    for test, why in (
            (sig["tracked_files"] >= 25,
             "%d tracked files, which is past the 25 a single-file fix has"
             % sig["tracked_files"]),
            (sig["work_records"] >= 2,
             "%d work records, so more than one thread of work exists"
             % sig["work_records"]),
            (sig["gates"] >= 1,
             "%d recorded gate(s), so decisions have been put to a human"
             % sig["gates"]),
            (sig["recorded_decisions"] >= 3,
             "%d recorded decisions" % sig["recorded_decisions"])):
        if test:
            tier = max(tier, 2)
            reasons.append("tier 2 because %s" % why)
    for test, why in (
            (sig["contributors"] >= 2,
             "%d distinct contributors, so this is not one person's memory"
             % sig["contributors"]),
            (sig["tracked_files"] >= 200,
             "%d tracked files" % sig["tracked_files"]),
            (sig["gates"] >= 5,
             "%d recorded gates" % sig["gates"]),
            (sig["open_risk_flags"] >= 1,
             "%d open risk flag(s) in the store" % sig["open_risk_flags"]),
            (sig["activity_span"].startswith("over three months"),
             "over three months of recorded activity, so this is long lived")):
        if test:
            tier = max(tier, 3)
            reasons.append("tier 3 because %s" % why)
    if not reasons:
        reasons.append("tier 1 because no signal reached the tier 2 threshold: "
                       "%d tracked files, %d work records, %d gates, %d "
                       "recorded decisions"
                       % (sig["tracked_files"], sig["work_records"],
                          sig["gates"], sig["recorded_decisions"]))
    source = "automatic"
    if floor and floor > tier:
        reasons.append(
            "held at tier %d because the previous generation recorded tier %d "
            "and an automatic decision may only raise depth (I13); pass "
            "--tier %d to lower it on purpose" % (floor, floor, tier))
        tier = floor
        source = "automatic, held at the recorded floor"
    if explicit is not None:
        if explicit < tier:
            reasons.append("lowered to tier %d by an explicit --tier %d, which "
                           "is the only way documentation depth goes down"
                           % (explicit, explicit))
        elif explicit > tier:
            reasons.append("raised to tier %d by an explicit --tier %d"
                           % (explicit, explicit))
        else:
            reasons.append("confirmed at tier %d by an explicit --tier %d"
                           % (explicit, explicit))
        tier = explicit
        source = "explicit --tier"
    return {"tier": tier, "name": TIERS[tier], "reasons": reasons,
            "source": source}


def recorded_floor(root):
    """The tier the last generation wrote, or 0. Read from the generated
    facts.json, which is the engine's own output and therefore the one place a
    floor can live without a schema change."""
    path = os.path.join(root, DOC_ROOT, "90-generated", "facts.json")
    if not os.path.isfile(path):
        return 0
    try:
        with io.open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (ValueError, OSError):
        return 0
    tier = data.get("tier")
    return tier if isinstance(tier, int) and tier in TIERS else 0


# ---------------------------------------------------------------------------
# The generator.
# ---------------------------------------------------------------------------

class Generator(object):
    """One generation pass over one project.

    Holds the facts, the tier, and the prior contents of the file currently
    being written, which is what makes human preservation (I10) and the
    narrative cache (I12) possible at all."""

    def __init__(self, root, store, explicit_tier=None):
        self.root = root
        self.store = store
        self.items = work_items(store)
        self.decisions = decision_rows(store, root)
        self.notes = note_rows(store)
        self.inventory = module_inventory(root)
        self.graph = work_graph(root, self.items)
        self.imports = import_graph(root)
        self.model = data_model(store)
        self.lifecycle = lifecycle_states(store)
        self.gate = gate_command(root)
        self.signals = signals(root, store, self.items, self.decisions,
                               self.notes, self.inventory)
        self.floor = recorded_floor(root)
        self.decision = choose_tier(self.signals, floor=self.floor,
                                    explicit=explicit_tier)
        self.tier = self.decision["tier"]
        self.facts = self._facts()
        self.prior = {"human": [], "prose": {}}
        self.reused = 0
        self.regenerated = 0
        self.preserved = 0

    # -- facts -----------------------------------------------------------

    def _facts(self):
        """The machine-readable facts every page is projected from.

        NO GENERATION TIMESTAMP. Every value here comes from a store row or from
        a file on disk, so two runs a minute apart produce the same bytes. A
        "generated_at" field would make every regeneration a diff."""
        return {
            "layout_version": 1,
            "project_name": os.path.basename(self.root.rstrip(os.sep)),
            "tier": self.tier,
            "tier_name": TIERS[self.tier],
            "tier_source": self.decision["source"],
            "tier_reasons": self.decision["reasons"],
            "signals": self.signals,
            "gate": self.gate,
            "work_items": self.items,
            "schedule": self.graph,
            "decisions": self.decisions,
            "notes": self.notes,
            "lineage": lineage(self.store, self.items, self.decisions,
                               self.notes),
            "modules": self.inventory["modules"],
            "tests": self.inventory["tests"],
            "imports": self.imports,
            "data_model": self.model,
            "lifecycle": self.lifecycle,
            "emitted": [rel for rel, tier, _what in FILES if tier <= self.tier],
        }

    def fact_hash(self, keys):
        subset = {}
        for key in keys:
            subset[key] = self.facts.get(key)
        blob = json.dumps(subset, sort_keys=True, separators=(",", ":"),
                          default=str)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    # -- narrative, cached against facts (I12) ---------------------------

    def prose(self, pid, keys, writer):
        """A narrative block, regenerated ONLY when the facts it describes moved.

        `writer` is a callable and is NOT called on a cache hit. That is the
        difference between a cache and a comment: a version that always wrote the
        paragraph and then compared it would satisfy the letter of I12 and pay
        the whole cost it exists to avoid, and no test could tell the two apart.
        """
        sha = self.fact_hash(keys)
        record = self.prior["prose"].get(pid)
        if record is not None and record["sha"] == sha:
            self.reused += 1
            body = record["body"]
        else:
            self.regenerated += 1
            body = _neutralize_prose_markers(writer())
        out = ["<!-- bm-prose: id=%s sha256=%s -->" % (pid, sha)]
        out.extend(body.split("\n"))
        out.append(_PROSE_CLOSE)
        return out

    # -- files -----------------------------------------------------------

    def emitted(self):
        return [(rel, tier, what) for rel, tier, what in FILES
                if tier <= self.tier]

    def path_for(self, rel):
        return bs.safe_project_path(self.root, DOC_ROOT, *rel.split("/"))

    def stale(self):
        """Pages a DEEPER tier once wrote that this tier does not maintain.

        Named rather than deleted. Two reasons, and the second is the binding
        one: a generator that removes files can remove a paragraph a human wrote
        inside one (I10 forbids exactly that), and a page silently left behind
        with no warning is a page a reader trusts as current. So both risks are
        answered by saying so out loud, here and in START-HERE."""
        out = []
        for rel, tier, _what in FILES:
            if tier <= self.tier:
                continue
            if os.path.isfile(self.path_for(rel)):
                out.append(rel)
        return out

    def write(self):
        """Every emitted file, through the one funnel. Returns a report."""
        written = []
        for rel, _tier, _what in self.emitted():
            path = self.path_for(rel)
            self.prior = read_existing(path)
            if rel.endswith(".json"):
                text = json.dumps(self.facts, indent=2, sort_keys=True,
                                  default=str) + "\n"
            else:
                text = self.render(rel)
            directory = os.path.dirname(path)
            if not os.path.isdir(directory):
                os.makedirs(directory)
            # Checked BEFORE the write, on the text about to be written, so the
            # reported line numbers are line numbers in the file on disk. The
            # funnel carries a human block through verbatim (I10); this is how a
            # human hears that their own paragraph holds something secret shaped
            # instead of finding it quietly rewritten.
            hits = bs.human_block_secret_hits(text)
            bs.write_generated_document(path, text)
            written.append({"path": DOC_ROOT + "/" + rel,
                            "human_blocks": len(self.prior["human"]),
                            "secret_shaped_human_lines": hits})
            self.preserved += len(self.prior["human"])
        return {"tier": self.tier, "tier_name": TIERS[self.tier],
                "tier_source": self.decision["source"],
                "tier_reasons": self.decision["reasons"],
                "signals": self.signals, "files": written,
                "stale_from_a_deeper_tier": self.stale(),
                "prose_reused": self.reused,
                "prose_regenerated": self.regenerated,
                "human_blocks_preserved": self.preserved,
                "critical_path": self.graph["critical_path"],
                "critical_days": self.graph["critical_days"]}

    def render(self, rel):
        renderer = getattr(self, "_doc_" + re.sub(r"[^a-z0-9]+", "_",
                                                  rel.lower()))
        lines = [
            "<!-- GENERATED by tools/bm_docs.py. Regenerate rather than "
            "hand-edit, except inside the human markers, which are preserved "
            "verbatim. -->",
            "",
        ]
        lines.extend(renderer())
        lines.extend(self._human_section())
        return "\n".join(lines).rstrip("\n") + "\n"

    def _human_section(self):
        out = ["## Human notes, preserved verbatim", "",
               "Anything between the two markers survives every regeneration "
               "untouched. Write here rather than anywhere else in this file.",
               ""]
        blocks = self.prior["human"] or [""]
        for block in blocks:
            out.append(HUMAN_BEGIN)
            if block:
                out.extend(block.split("\n"))
            out.append(HUMAN_END)
            out.append("")
        return out

    def _regen(self):
        cmd = self.command()
        return ("Regenerate with `%s generate`. Every fact below is projected "
                "from the store or read from the files as they are on disk."
                % cmd)

    def command(self):
        """The command a reader can paste. Relative when this tool lives inside
        the project being documented, which is the common case for a repository
        that carries its own toolchain, and absolute otherwise. Never a home
        directory written into a committed document by accident."""
        here = os.path.abspath(__file__)
        root = os.path.abspath(self.root)
        if here.startswith(root + os.sep):
            return "python3 %s" % os.path.relpath(here, root).replace("\\", "/")
        return bs.invocation("bm_docs.py", __file__)

    # -- 00-START-HERE ---------------------------------------------------

    def _doc_00_start_here_md(self):
        w = []
        w.append("# Start here: %s" % _d(self.facts["project_name"], 80))
        w.append("")
        w.append("This folder is generated from what BrotherMode recorded about "
                 "this project plus what is in the files right now. %s"
                 % self._regen())
        w.append("")
        w.append("## The tier this folder is written at")
        w.append("")
        w.append("**Tier %d (%s)**, chosen %s."
                 % (self.tier, TIERS[self.tier], self.decision["source"]))
        w.append("")
        for reason in self.decision["reasons"]:
            w.append("- %s" % reason)
        w.append("")
        w.append("Depth moves up on its own and never down on its own (I13). "
                 "To go down, say so: `%s generate --tier 1`." % self.command())
        w.append("")
        w.append("## The signals that measured it")
        w.append("")
        w.append("| Signal | Value |")
        w.append("| --- | --- |")
        for label, key in (
                ("Tracked files", "tracked_files"),
                ("Counted from", "tracked_files_source"),
                ("Distinct contributors", "contributors"),
                ("Work records", "work_records"),
                ("Recorded decisions", "recorded_decisions"),
                ("Recorded gates", "gates"),
                ("Open risk flags", "open_risk_flags"),
                ("Modules", "modules"),
                ("Test files", "test_files"),
                ("Recorded activity", "activity_span")):
            w.append("| %s | %s |" % (label, _cell(str(self.signals[key]))))
        w.append("")
        if self.signals["contributor_names"]:
            w.append("Contributors the store names: %s."
                     % ", ".join("`%s`" % _cell(n, 60)
                                 for n in self.signals["contributor_names"]))
            w.append("")
        w.append("## Reading order")
        w.append("")
        w.append("| # | File | What it is |")
        w.append("| --- | --- | --- |")
        for i, (rel, _tier, what) in enumerate(self.emitted(), 1):
            w.append("| %d | `%s` | %s |" % (i, rel, what))
        w.append("")
        held = [rel for rel, tier, _w in FILES if tier > self.tier]
        if held:
            w.append("Not written at this tier: %s. They arrive if the signals "
                     "raise the tier, or immediately with `%s generate --tier "
                     "3`." % (", ".join("`%s`" % r for r in held),
                              self.command()))
            w.append("")
        stale = self.stale()
        if stale:
            w.append("**Left behind by a deeper tier and NO LONGER "
                     "MAINTAINED:** %s. A generator here deletes nothing, "
                     "because a file may hold a paragraph a human wrote and "
                     "this project does not destroy those. Read them as "
                     "history, or remove them yourself once you have taken out "
                     "anything you want to keep."
                     % ", ".join("`%s`" % r for r in stale))
            w.append("")
        w.append("## What is generated and what is yours")
        w.append("")
        w.append("Everything outside the human markers is rewritten on every "
                 "run. Everything between them is carried through byte for "
                 "byte, in every file, including this one. That is an invariant "
                 "with a test behind it, not a convention.")
        w.append("")
        return w

    # -- 10-business -----------------------------------------------------

    def _doc_10_business_ba_summary_md(self):
        w = ["# What this project is trying to do", ""]
        w.extend(self.prose(
            "ba-summary", ("project_name", "work_items", "signals", "gate"),
            self._write_ba_summary))
        w.append("")
        w.append("## The work as the store records it")
        w.append("")
        if not self.items:
            w.append("No work record exists yet, so there is nothing to "
                     "summarize. A record is how work becomes visible: "
                     "`bm_store.py claim <name> persistent --objective "
                     "\"<what you are doing>\"`.")
            w.append("")
            return w
        w.append("| Record | State | Objective |")
        w.append("| --- | --- | --- |")
        for item in self.items[:_MAX_LISTED]:
            w.append("| `%s` %s | %s | %s |"
                     % (item["short"], _cell(item["name"], 40), item["state"],
                        _cell(item["objective"], 160) or "(none recorded)"))
        if len(self.items) > _MAX_LISTED:
            w.append("")
            w.append("... and %d more." % (len(self.items) - _MAX_LISTED))
        w.append("")
        return w

    def _write_ba_summary(self):
        states = {}
        for item in self.items:
            states[item["state"]] = states.get(item["state"], 0) + 1
        parts = []
        if not self.items:
            parts.append(
                "The store holds no work record for this project yet, so there "
                "is no recorded objective to summarize. This paragraph will "
                "say something once work is claimed, and until then the honest "
                "answer is that nothing was recorded.")
        else:
            parts.append(
                "%s has %d recorded work record(s): %s."
                % (_d(self.facts["project_name"], 60), len(self.items),
                   ", ".join("%d %s" % (n, s)
                             for s, n in sorted(states.items()))))
            objectives = [i for i in self.items if (i["objective"] or "").strip()]
            if objectives:
                parts.append(
                    "The objectives on those records are what this project said "
                    "it was for, in its own words, and they are quoted in the "
                    "table below rather than paraphrased.")
            else:
                parts.append(
                    "NONE of those records carries an objective. A record with "
                    "no objective cannot be reviewed later, because there is "
                    "nothing to compare the result against.")
        if self.gate["command"]:
            parts.append(
                "Whether it works is not a matter of opinion here: run `%s`, "
                "which is the command this project declares (%s)."
                % (self.gate["command"], self.gate["why"]))
        else:
            parts.append(
                "This project declares no test command, so there is no way to "
                "prove the current state from the outside. That is a finding, "
                "not a formatting problem.")
        return " ".join(parts)

    def _doc_10_business_requirements_md(self):
        w = ["# Requirements", "",
             "Two kinds, both recorded rather than gathered: what the work "
             "records say they are for, and the standing rules a human "
             "approved. %s" % self._regen(), ""]
        w.append("## Objectives, from the work records")
        w.append("")
        objectives = [i for i in self.items if (i["objective"] or "").strip()]
        if not objectives:
            w.append("- none recorded")
        for item in objectives[:_MAX_LISTED]:
            w.append("- **%s** (`%s`, %s): %s"
                     % (_d(item["name"], 60), item["short"], item["state"],
                        _d(item["objective"], 400)))
        w.append("")
        w.append("## Constraints, from approved rules")
        w.append("")
        rules = [d for d in self.decisions if d["kind"] == "rule"]
        w.append("**Approved rules: %d.**" % len(rules))
        w.append("")
        if not rules:
            w.append("- none approved, so nothing constrains the work beyond "
                     "its objectives")
        for rule in rules[:_MAX_LISTED]:
            w.append("- `%s` [%s, %s] when %s, do %s"
                     % (rule["id"], _cell(rule["scope"], 60), rule["status"],
                        _d(rule["trigger"], 160) or "(no trigger)",
                        _d(rule["title"], 200)))
        w.append("")
        w.append("## Checks the records declare")
        w.append("")
        checks = [i for i in self.items if (i["check_cmd"] or "").strip()]
        if not checks:
            w.append("- no work record declares a check command")
        for item in checks[:_MAX_LISTED]:
            w.append("- `%s` %s: `%s`" % (item["short"], _d(item["name"], 40),
                                          _d(item["check_cmd"], 200)))
        w.append("")
        return w

    def _doc_10_business_wbs_md(self):
        w = ["# Work breakdown", "",
             "Projected straight from the work records and the files each one "
             "claimed. Nothing here was typed by hand. %s" % self._regen(), ""]
        if not self.items:
            w.append("No work record exists yet, so there is no breakdown.")
            w.append("")
            return w
        w.append("| # | Record | Name | State | Files claimed | Decisions | "
                 "Checkpoints |")
        w.append("| --- | --- | --- | --- | --- | --- | --- |")
        for i, item in enumerate(self.items, 1):
            w.append("| %d | `%s` | %s | %s | %d | %d | %d |"
                     % (i, item["short"], _cell(item["name"], 40),
                        item["state"], len(item["files"]),
                        len(item["decisions"]), len(item["digests"])))
        w.append("")
        for item in self.items[:_MAX_LISTED]:
            w.append("### %d. %s (`%s`)"
                     % (self.items.index(item) + 1, _d(item["name"], 60),
                        item["short"]))
            w.append("")
            w.append("- State: %s, lifetime %s, owner %s"
                     % (item["state"], item["lifetime"],
                        _d(item["owner"], 60) or "unrecorded"))
            w.append("- Objective: %s"
                     % (_d(item["objective"], 400) or "(none recorded)"))
            w.append("- Opened %s, last touched %s"
                     % (item["created_at"], item["updated_at"]))
            if item["files"]:
                w.append("- Files it holds: %s"
                         % ", ".join("`%s`" % _cell(f, 80)
                                     for f in item["files"][:12]))
                if len(item["files"]) > 12:
                    w.append("  and %d more" % (len(item["files"]) - 12))
            else:
                w.append("- Files it holds: none, so it fences nothing and "
                         "cannot conflict with another record")
            if item["decisions"]:
                w.append("- Decisions recorded against it:")
                for dec in item["decisions"][:12]:
                    w.append("  - #%d %s: %s"
                             % (dec["seq"], _d(dec["topic"], 80) or "untitled",
                                _d(dec["text"], 300)))
            if item["digests"]:
                last = item["digests"][-1]
                w.append("- Last checkpoint intent: %s"
                         % (_d(last["next_intent"], 300) or "(none recorded)"))
                if (last["blockers"] or "").strip():
                    w.append("- Last recorded blockers: %s"
                             % _d(last["blockers"], 300))
            w.append("")
        return w

    def _doc_10_business_schedule_md(self):
        graph = self.graph
        w = ["# Schedule", "",
             "A gantt of the recorded work, and the critical path through it. "
             "%s" % self._regen(), ""]
        w.append("## How the dependencies were derived")
        w.append("")
        w.append("BrotherMode does not let two records hold the same file at "
                 "once, so a record that claims a path an earlier record also "
                 "claims could only have run after it. Every edge below is that "
                 "fact about the recorded claims. Nothing is asserted, and "
                 "because the edges run forward in creation order the graph "
                 "cannot contain a cycle.")
        w.append("")
        if not graph["nodes"]:
            w.append("No work record exists yet, so there is nothing to "
                     "schedule.")
            w.append("")
            return w
        w.append("```mermaid")
        w.append("gantt")
        w.append("  dateFormat YYYY-MM-DD")
        w.append("  title Recorded work")
        for state in sorted(set(n["state"] for n in graph["nodes"])):
            w.append("  section %s" % state)
            for node in graph["nodes"]:
                if node["state"] != state:
                    continue
                w.append("  %s :%s, %s, %dd"
                         % (_flat(node["name"], 40), node["id"], node["start"],
                            node["days"]))
        w.append("```")
        w.append("")
        w.append("## Dependencies")
        w.append("")
        w.append("**Edges: %d.**" % len(graph["edges"]))
        w.append("")
        if not graph["edges"]:
            w.append("- none: no two records claim overlapping files, so every "
                     "record could have run at any time")
        for a, b, why in graph["edges"][:_MAX_LISTED]:
            w.append("- `%s` must precede `%s`, because both claim %s"
                     % (a, b, _cell(why, 120)))
        w.append("")
        w.append("## Critical path")
        w.append("")
        w.append("Computed as the longest path by summed duration over the "
                 "graph above. It is the chain that decides the earliest "
                 "possible finish: shortening anything off it changes nothing.")
        w.append("")
        if not graph["critical_path"]:
            w.append("- no path: the graph has no nodes")
        else:
            names = dict((n["id"], n["name"]) for n in graph["nodes"])
            w.append("**%d recorded day(s) across %d record(s).**"
                     % (graph["critical_days"], len(graph["critical_path"])))
            w.append("")
            for node_id in graph["critical_path"]:
                w.append("1. `%s` %s" % (node_id, _cell(names.get(node_id, ""),
                                                        60)))
            w.append("")
            w.append("```mermaid")
            w.append("flowchart LR")
            for i, node_id in enumerate(graph["critical_path"]):
                w.append("  n%d[\"%s\"]" % (i, _flat(names.get(node_id,
                                                              node_id), 40)))
            for i in range(len(graph["critical_path"]) - 1):
                w.append("  n%d --> n%d" % (i, i + 1))
            w.append("```")
        w.append("")
        return w

    # -- 20-technical ----------------------------------------------------

    def _doc_20_technical_architecture_md(self):
        w = ["# Architecture", ""]
        w.extend(self.prose("architecture", ("modules", "imports", "gate"),
                            self._write_architecture))
        w.append("")
        w.append("## Modules by size")
        w.append("")
        w.append("| Module | Lines | Classes | Functions | What it says it is |")
        w.append("| --- | --- | --- | --- | --- |")
        ranked = sorted(self.inventory["modules"],
                        key=lambda m: (-m["lines"], m["path"]))
        for mod in ranked[:_MAX_LISTED]:
            w.append("| `%s` | %d | %d | %d | %s |"
                     % (mod["path"], mod["lines"], mod["classes"], mod["defs"],
                        _cell(mod["doc"], 90) or "(no docstring)"))
        if len(ranked) > _MAX_LISTED:
            w.append("")
            w.append("... and %d more, all listed in CODE-MAP.md at tier 3."
                     % (len(ranked) - _MAX_LISTED))
        w.append("")
        w.append("## What depends on what")
        w.append("")
        w.append("The full graph is in DEPENDENCIES.md. The modules nothing "
                 "else imports are the entry points; the ones everything "
                 "imports are the load bearing ones.")
        w.append("")
        incoming = {}
        for _a, b in self.imports["edges"] + self.imports["loader_edges"]:
            incoming[b] = incoming.get(b, 0) + 1
        if not incoming:
            w.append("- no module in this project imports another")
        for path, count in sorted(incoming.items(), key=lambda kv: (-kv[1],
                                                                   kv[0]))[:12]:
            w.append("- `%s` is depended on by %d module(s)" % (path, count))
        w.append("")
        return w

    def _write_architecture(self):
        mods = self.inventory["modules"]
        total = sum(m["lines"] for m in mods)
        parts = []
        if not mods:
            return ("No Python module was found under this project root, so "
                    "there is no code shape to describe. That is what the scan "
                    "found, not a limit of the scan: it walks every directory "
                    "except the generated folder and the usual caches.")
        biggest = sorted(mods, key=lambda m: (-m["lines"], m["path"]))[0]
        parts.append(
            "This project is %d module(s) and about %d lines of Python, "
            "excluding tests. The largest single module is `%s` at %d lines, "
            "which is where a reader looking for the centre of the system "
            "should start."
            % (len(mods), total, biggest["path"], biggest["lines"]))
        edges = len(self.imports["edges"]) + len(self.imports["loader_edges"])
        parts.append(
            "There are %d internal dependency edge(s) between those modules, "
            "%d of them found by parsing imports and %d by reading the "
            "path based loader this project uses so that a hostile sys.path "
            "cannot shadow a module."
            % (edges, len(self.imports["edges"]),
               len(self.imports["loader_edges"])))
        external = self.imports["external"]
        if external:
            top = sorted(external.items(), key=lambda kv: (-kv[1], kv[0]))[:6]
            parts.append(
                "Outside itself it imports %d distinct top level module(s), "
                "most often %s. Whether any of those is a third party "
                "dependency rather than the standard library is a question the "
                "project's own packaging answers, and this scan does not guess."
                % (len(external), ", ".join("`%s`" % n for n, _c in top)))
        return " ".join(parts)

    def _doc_20_technical_data_model_md(self):
        w = ["# Data model", "",
             "Introspected from the live schema on this machine, table by "
             "table, rather than read out of a schema definition in the source. "
             "%s" % self._regen(), ""]
        tables = self.model["tables"]
        w.append("**Tables: %d.**" % len(tables))
        w.append("")
        w.append("```mermaid")
        w.append("erDiagram")
        for table in tables:
            w.append("  %s {" % table["name"])
            for col in table["columns"][:20]:
                flags = []
                if col["pk"]:
                    flags.append("PK")
                if col["notnull"]:
                    flags.append("NOT_NULL")
                w.append("    %s %s%s"
                         % (re.sub(r"[^A-Za-z0-9_]", "_",
                                   col["type"]) or "TEXT",
                            re.sub(r"[^A-Za-z0-9_]", "_", col["name"]),
                            ' "%s"' % " ".join(flags) if flags else ""))
            w.append("  }")
        for table in tables:
            for fk in table["foreign_keys"]:
                w.append("  %s ||--o{ %s : \"%s\""
                         % (re.sub(r"[^A-Za-z0-9_]", "_", fk["table"]),
                            table["name"],
                            re.sub(r"[^A-Za-z0-9_]", "_", fk["column"])))
        w.append("```")
        w.append("")
        for table in tables:
            w.append("### `%s`" % table["name"])
            w.append("")
            if table["note"]:
                w.append(table["note"])
                w.append("")
                continue
            w.append("| Column | Type | Key | Required |")
            w.append("| --- | --- | --- | --- |")
            for col in table["columns"]:
                w.append("| `%s` | %s | %s | %s |"
                         % (_cell(col["name"], 60), _cell(col["type"], 30),
                            "primary" if col["pk"] else "",
                            "yes" if col["notnull"] else "no"))
            w.append("")
            if table["foreign_keys"]:
                for fk in table["foreign_keys"]:
                    w.append("- `%s` points at `%s.%s`"
                             % (_cell(fk["column"], 60), _cell(fk["table"], 60),
                                _cell(fk["to"] or "rowid", 60)))
                w.append("")
        return w

    def _doc_20_technical_dependencies_md(self):
        w = ["# Dependencies", "",
             "Parsed from the source. Two kinds of edge, kept apart on purpose: "
             "an ordinary import, and a module this project loads by absolute "
             "path, which no import scan can see. %s" % self._regen(), ""]
        edges = self.imports["edges"]
        loader = self.imports["loader_edges"]
        w.append("**Internal edges: %d parsed from imports, %d from the path "
                 "loader.**" % (len(edges), len(loader)))
        w.append("")
        w.append("```mermaid")
        w.append("flowchart LR")
        ids = {}
        for path in self.imports["nodes"]:
            if any(path in (a, b) for a, b in edges + loader):
                ids[path] = "m%d" % len(ids)
        for path, node in sorted(ids.items()):
            w.append("  %s[\"%s\"]" % (node, _flat(path, 60)))
        if not ids:
            w.append("  none[\"no internal dependency found\"]")
        for a, b in edges:
            if a in ids and b in ids:
                w.append("  %s --> %s" % (ids[a], ids[b]))
        for a, b in loader:
            if a in ids and b in ids:
                w.append("  %s -. loads .-> %s" % (ids[a], ids[b]))
        w.append("```")
        w.append("")
        w.append("## Every internal edge")
        w.append("")
        if not edges and not loader:
            w.append("- none found")
        for a, b in edges[:_MAX_LISTED]:
            w.append("- `%s` imports `%s`" % (a, b))
        for a, b in loader[:_MAX_LISTED]:
            w.append("- `%s` loads `%s` by path" % (a, b))
        w.append("")
        w.append("## What it reaches for outside itself")
        w.append("")
        external = self.imports["external"]
        w.append("**Distinct top level names: %d.** Whether each is the "
                 "standard library or a third party package is a packaging "
                 "question, and this scan does not guess at it."
                 % len(external))
        w.append("")
        if not external:
            w.append("- none")
        for name, count in sorted(external.items(),
                                  key=lambda kv: (-kv[1], kv[0]))[:_MAX_LISTED]:
            w.append("- `%s`, imported %d time(s)" % (_cell(name, 60), count))
        w.append("")
        return w

    def _doc_20_technical_process_diagrams_md(self):
        w = ["# Process diagrams", "",
             "The lifecycle a work record moves through, and the transitions "
             "this store has actually seen. %s" % self._regen(), ""]
        states = self.lifecycle["states"]
        observed = self.lifecycle["observed"]
        w.append("## The lifecycle the schema allows")
        w.append("")
        if not states:
            w.append("The schema does not constrain the state column, so there "
                     "is no declared lifecycle to draw.")
            w.append("")
        else:
            w.append("```mermaid")
            w.append("stateDiagram-v2")
            for state in states:
                w.append("  %s : %s" % (state, state))
            for row in observed:
                if row["from"] and row["to"]:
                    w.append("  %s --> %s : %d observed"
                             % (row["from"], row["to"], row["count"]))
                elif row["to"]:
                    w.append("  [*] --> %s : %d observed"
                             % (row["to"], row["count"]))
            w.append("```")
            w.append("")
            w.append("States the schema allows: %s."
                     % ", ".join("`%s`" % s for s in states))
            w.append("")
        w.append("## Transitions this store has recorded")
        w.append("")
        if not observed:
            w.append("- none: no record has changed state yet")
        for row in observed:
            w.append("- %s to %s: %d time(s)"
                     % ("(new)" if not row["from"] else "`%s`" % row["from"],
                        "`%s`" % row["to"], row["count"]))
        w.append("")
        w.append("## The gate a change passes through")
        w.append("")
        if self.gate["command"]:
            w.append("```mermaid")
            w.append("flowchart TD")
            w.append("  claim[\"claim the files\"] --> work[\"change them\"]")
            w.append("  work --> check[\"%s\"]" % _flat(self.gate["command"], 60))
            w.append("  check --> green[\"green: checkpoint and continue\"]")
            w.append("  check --> red[\"red: revert to the last green state\"]")
            w.append("  green --> close[\"complete the record\"]")
            w.append("```")
        else:
            w.append("This project declares no check command, so there is no "
                     "gate to draw. That is the finding.")
        w.append("")
        return w

    def _doc_20_technical_code_map_md(self):
        w = ["# Code map", "",
             "Every module and every test file the scan found, with what each "
             "defines at the top level. %s" % self._regen(), ""]
        w.append("## Modules: %d" % len(self.inventory["modules"]))
        w.append("")
        for mod in self.inventory["modules"]:
            w.append("### `%s`" % mod["path"])
            w.append("")
            w.append("%d lines, %d class(es), %d function(s). %s"
                     % (mod["lines"], mod["classes"], mod["defs"],
                        _d(mod["doc"], 200) or "No docstring."))
            w.append("")
            if mod["top_level"]:
                w.append("Top level names: %s."
                         % ", ".join("`%s`" % n for n in mod["top_level"]))
                w.append("")
        w.append("## Test files: %d" % len(self.inventory["tests"]))
        w.append("")
        if not self.inventory["tests"]:
            w.append("No test file was found. A code map with no tests in it is "
                     "a map of code nothing verifies.")
            w.append("")
        for test in self.inventory["tests"]:
            w.append("- `%s`: %d test(s) across %d lines"
                     % (test["path"], test.get("tests", 0), test["lines"]))
        w.append("")
        return w

    def _doc_20_technical_whitepaper_md(self):
        w = ["# Whitepaper", ""]
        w.extend(self.prose(
            "whitepaper",
            ("project_name", "signals", "work_items", "decisions", "modules",
             "data_model", "gate"),
            self._write_whitepaper))
        w.append("")
        w.append("## The evidence behind every claim above")
        w.append("")
        w.append("| Claim | Where it comes from |")
        w.append("| --- | --- |")
        w.append("| module and line counts | a walk of the tree, listed in "
                 "CODE-MAP.md |")
        w.append("| table and column counts | sqlite introspection, drawn in "
                 "DATA-MODEL.md |")
        w.append("| work records and their states | the records table, "
                 "projected into WBS.md |")
        w.append("| decisions and their states | the candidate and rule tables, "
                 "indexed in 30-decisions/INDEX.md |")
        w.append("| the critical path | longest path over the claim overlap "
                 "graph, shown in SCHEDULE.md |")
        w.append("")
        return w

    def _write_whitepaper(self):
        sig = self.signals
        parts = [
            "%s is %d module(s) and %d test file(s), with %d work record(s) and "
            "%d recorded decision(s) behind it."
            % (_d(self.facts["project_name"], 60), sig["modules"],
               sig["test_files"], sig["work_records"],
               sig["recorded_decisions"]),
            "The point of writing that down is that none of it is anyone's "
            "recollection: every number in this folder is either a row in a "
            "database or a file on disk, and the command that regenerates the "
            "folder is printed on every page so a reader can check rather than "
            "believe.",
        ]
        tables = self.model["tables"]
        if tables:
            columns = sum(len(t["columns"]) for t in tables)
            parts.append(
                "The state lives in %d table(s) and %d column(s), diagrammed in "
                "DATA-MODEL.md straight from the schema this machine is running "
                "rather than from a definition in the source, so a migration "
                "that landed cannot leave the diagram behind."
                % (len(tables), columns))
        if sig["open_risk_flags"]:
            parts.append(
                "There are %d open risk flag(s) in the store right now. They "
                "are listed with their authors in 30-decisions/INDEX.md, and an "
                "unresolved critical one refuses a gate close rather than "
                "appearing as a warning nobody reads."
                % sig["open_risk_flags"])
        else:
            parts.append(
                "No open risk flag stands in the store right now, which is a "
                "statement about what has been written down rather than a "
                "clean bill of health.")
        if self.gate["command"]:
            parts.append(
                "The whole of it is gated on one command, `%s`, and this "
                "project's habit is that nothing is called done until that "
                "command has been run after the last edit."
                % self.gate["command"])
        return " ".join(parts)

    # -- 30-decisions ----------------------------------------------------

    def _doc_30_decisions_index_md(self):
        w = ["# Decisions", "",
             "Every decision the store holds, and the deep dive pack that "
             "reviews it where one has been generated. %s" % self._regen(), ""]
        cands = [d for d in self.decisions if d["kind"] == "candidate"]
        rules = [d for d in self.decisions if d["kind"] == "rule"]
        w.append("**Candidates: %d. Approved rules: %d. Notes: %d.**"
                 % (len(cands), len(rules), len(self.notes)))
        w.append("")
        w.append("## Candidates and their packs")
        w.append("")
        if not cands:
            w.append("No candidate has been captured yet, so nothing is waiting "
                     "on a human.")
            w.append("")
        else:
            w.append("| D | Id | Status | Scope | Proposal | Pack |")
            w.append("| --- | --- | --- | --- | --- | --- |")
            for row in cands:
                pack = "`%s`" % row["pack"] if row["pack"] else "not generated"
                w.append("| D-%d | `%s` | %s | %s | %s | %s |"
                         % (row["index"], row["id"], row["status"],
                            _cell(row["scope"], 40), _cell(row["title"], 100),
                            pack))
            w.append("")
            w.append("A pack is generated on demand, never in advance: `%s pack "
                     "<id>` in bm_packs.py writes the eight section review an "
                     "engineer needs. `%s stakes <id>` prints the one line a "
                     "question window carries and generates nothing."
                     % (self._packs_command(), self._packs_command()))
            w.append("")
        w.append("## Approved rules")
        w.append("")
        if not rules:
            w.append("- none approved")
        for row in rules[:_MAX_LISTED]:
            w.append("- `%s` [%s, %s] when %s, do %s"
                     % (row["id"], _cell(row["scope"], 60), row["status"],
                        _d(row["trigger"], 160) or "(no trigger)",
                        _d(row["title"], 200)))
        w.append("")
        w.append("## Decisions recorded against work records")
        w.append("")
        any_dec = False
        for item in self.items:
            for dec in item["decisions"]:
                any_dec = True
                w.append("- `%s#%d` %s (%s): %s"
                         % (item["short"], dec["seq"],
                            _d(dec["topic"], 80) or "untitled",
                            dec["created_at"], _d(dec["text"], 300)))
        if not any_dec:
            w.append("- none recorded")
        w.append("")
        w.append("## Notes at their anchors")
        w.append("")
        if not self.notes:
            w.append("- none")
        for note in self.notes[:_MAX_LISTED]:
            w.append("- `%s` %s%s by %s (%s) at %s, anchored %s, %s: %s"
                     % (note["id"], note["kind"],
                        " [%s]" % note["severity"] if note["severity"] else "",
                        _d(note["author"], 60) or "unnamed",
                        note["author_kind"], note["created_at"],
                        note["anchor"], note["state"], _d(note["body"], 300)))
            if note["override_by"]:
                w.append("  - overridden by %s: %s"
                         % (_d(note["override_by"], 60),
                            _d(note["override_reason"], 200)))
        w.append("")
        w.append("## Lineage")
        w.append("")
        w.append("Everything that touched a decision, in order, with authors. "
                 "This is a query over the store, not a field anyone maintains.")
        w.append("")
        lin = self.facts["lineage"]
        if not lin:
            w.append("- nothing to trace yet")
        for key in sorted(lin):
            w.append("### `%s`" % key)
            w.append("")
            for event in lin[key]:
                w.append("- %s, %s: %s"
                         % (event["at"], _d(event["who"], 80),
                            _d(event["what"], 300)))
            w.append("")
        return w

    def _packs_command(self):
        here = os.path.abspath(os.path.join(HERE, "bm_packs.py"))
        root = os.path.abspath(self.root)
        if here.startswith(root + os.sep):
            return "python3 %s" % os.path.relpath(here, root).replace("\\", "/")
        return bs.invocation("bm_packs.py", here)

    # -- 40-handover -----------------------------------------------------

    def _doc_40_handover_handover_md(self):
        """Section 5.5. Written for a human with no AI: someone who has never
        spoken to me has to be able to pick this project up from this page."""
        w = ["# Handover", "",
             "This page is written for a person, not for a model. It assumes "
             "you have never spoken to an assistant about this project and are "
             "not going to. Everything in it is either a row this project "
             "recorded or a file you can open. %s" % self._regen(), ""]

        w.append("## 1. What this project is")
        w.append("")
        w.extend(self.prose("handover-what", ("project_name", "work_items",
                                              "modules", "gate"),
                            self._write_handover_what))
        w.append("")

        w.append("## 2. Current state, and the command that proves it")
        w.append("")
        if self.gate["command"]:
            w.append("Run this first, before you believe anything else on this "
                     "page:")
            w.append("")
            w.append("```")
            w.append(self.gate["command"])
            w.append("```")
            w.append("")
            w.append("It is the command this project declares (%s). If it does "
                     "not pass, the state below is the state somebody last "
                     "recorded and not the state you have."
                     % self.gate["why"])
        else:
            w.append("This project declares no test command, so there is "
                     "nothing you can run to prove its state. Treat every claim "
                     "below as a claim.")
        w.append("")
        evidence = [i for i in self.items if (i["evidence"] or "").strip()]
        if evidence:
            w.append("Evidence recorded on the work records:")
            w.append("")
            for item in evidence[:12]:
                w.append("- `%s` %s: %s" % (item["short"],
                                            _d(item["name"], 40),
                                            _d(item["evidence"], 300)))
            w.append("")

        for heading, states, empty in (
                ("3. What is done", ("complete", "adopted"),
                 "nothing is recorded as finished"),
                ("4. What is in flight", ("active",),
                 "nothing is recorded as active"),
                ("5. What is parked, and why", ("parked",),
                 "nothing is parked")):
            w.append("## %s" % heading)
            w.append("")
            rows = [i for i in self.items if i["state"] in states]
            if not rows:
                w.append("- %s" % empty)
            for item in rows:
                w.append("- **%s** (`%s`): %s"
                         % (_d(item["name"], 60), item["short"],
                            _d(item["objective"], 300) or "no objective "
                                                          "recorded"))
                if item["digests"]:
                    last = item["digests"][-1]
                    w.append("  - next intended step: %s"
                             % (_d(last["next_intent"], 300) or "none recorded"))
                    if (last["blockers"] or "").strip():
                        w.append("  - blockers: %s" % _d(last["blockers"], 300))
                if item["files"]:
                    w.append("  - holds: %s"
                             % ", ".join("`%s`" % _cell(f, 60)
                                         for f in item["files"][:8]))
            w.append("")

        w.append("## 6. What is not started")
        w.append("")
        pending = [d for d in self.decisions
                   if d["kind"] == "candidate"
                   and d["status"] in ("pending", "under_review")]
        if not pending:
            w.append("- no decision is waiting on a human, and no work record "
                     "exists that has not been opened. Anything not started is "
                     "therefore not written down anywhere, which is worth "
                     "knowing before you plan.")
        for row in pending:
            w.append("- decision D-%d (`%s`, %s) is waiting on a human: %s"
                     % (row["index"], row["id"], row["status"],
                        _cell(row["title"], 200)))
        w.append("")

        w.append("## 7. Where the code lives, module by module")
        w.append("")
        if not self.inventory["modules"]:
            w.append("- no module was found under this project root")
        for mod in sorted(self.inventory["modules"],
                          key=lambda m: (-m["lines"], m["path"]))[:_MAX_LISTED]:
            w.append("- `%s`, %d lines: %s"
                     % (mod["path"], mod["lines"],
                        _d(mod["doc"], 160) or "no docstring, so open it"))
        w.append("")

        w.append("## 8. How to run it and how to test it")
        w.append("")
        w.append("The runbook has the detail. The short version:")
        w.append("")
        w.append("```")
        w.append(self.gate["command"] or "# this project declares no test "
                                         "command")
        for item in self.items:
            if (item["check_cmd"] or "").strip():
                w.append("%s  # declared by record %s"
                         % (_d(item["check_cmd"], 160), item["short"]))
        w.append("```")
        w.append("")

        w.append("## 9. The known traps")
        w.append("")
        traps = [n for n in self.notes
                 if n["kind"] in ("alert", "risk", "todo", "question")]
        if not traps:
            w.append("- none written down. That is not the same as none "
                     "existing: it means nobody recorded one.")
        for note in traps[:_MAX_LISTED]:
            w.append("- %s%s by %s, %s, anchored %s: %s"
                     % (note["kind"],
                        " [%s]" % note["severity"] if note["severity"] else "",
                        _d(note["author"], 60) or "unnamed", note["state"],
                        note["anchor"], _d(note["body"], 300)))
        w.append("")
        blockers = [(i, d["blockers"]) for i in self.items
                    for d in i["digests"] if (d["blockers"] or "").strip()]
        if blockers:
            w.append("Blockers recorded at checkpoints:")
            w.append("")
            for item, text in blockers[-12:]:
                w.append("- `%s`: %s" % (item["short"], _d(text, 300)))
            w.append("")

        w.append("## 10. The open decisions, and their packs")
        w.append("")
        if not pending:
            w.append("- none open")
        for row in pending:
            w.append("- D-%d `%s`: %s" % (row["index"], row["id"],
                                          _cell(row["title"], 200)))
            w.append("  - reason recorded: %s"
                     % (_d(row["because"], 300) or "none, which is itself worth "
                                                   "asking about"))
            w.append("  - pack: %s"
                     % ("`%s`" % row["pack"] if row["pack"]
                        else "not generated; run `%s pack %s`"
                             % (self._packs_command(), row["id"])))
        w.append("")

        w.append("## 11. Who to ask")
        w.append("")
        people = sorted(set(self.signals["contributor_names"]))
        if not people:
            w.append("- the store names nobody. Owners are recorded on work "
                     "records and authors on notes, and neither carries a name "
                     "here, so there is no one this page can point you at.")
        for person in people:
            w.append("- `%s`" % _cell(person, 80))
        w.append("")
        w.append("## 12. What this page cannot tell you")
        w.append("")
        w.append("Everything here is projected from what was recorded. Work "
                 "that was never claimed, a decision taken in conversation and "
                 "never captured, and a risk somebody noticed and did not write "
                 "down are all invisible to this page, and no amount of "
                 "regeneration will make them appear.")
        w.append("")
        return w

    def _write_handover_what(self):
        parts = []
        objectives = [i for i in self.items if (i["objective"] or "").strip()]
        if objectives:
            parts.append(
                "In the words recorded on its own work records, this project "
                "exists to: %s."
                % "; ".join(_d(i["objective"], 200) for i in objectives[:4]))
        else:
            parts.append(
                "No work record carries an objective, so this project has "
                "never written down what it is for. Read the modules listed in "
                "section 7 and treat their docstrings as the closest thing to "
                "a statement of intent.")
        mods = self.inventory["modules"]
        if mods:
            parts.append(
                "Mechanically it is %d module(s) and %d test file(s)."
                % (len(mods), len(self.inventory["tests"])))
        if self.gate["command"]:
            parts.append("Its one gate is `%s`." % self.gate["command"])
        return " ".join(parts)

    def _doc_40_handover_runbook_md(self):
        w = ["# Runbook", "",
             "How to run this project, test it, and get it back to a known "
             "good state. %s" % self._regen(), ""]
        w.append("## Prove it works")
        w.append("")
        w.append("```")
        w.append(self.gate["command"] or "# no test command is declared by this "
                                         "project")
        w.append("```")
        w.append("")
        if self.gate["command"]:
            w.append("Discovered because %s. Run it after every change, and "
                     "before believing any page in this folder."
                     % self.gate["why"])
        else:
            w.append("Nothing in the tree declares a check command. Until one "
                     "exists, no change to this project can be verified by "
                     "anyone who did not make it.")
        w.append("")
        w.append("## See what BrotherMode is holding")
        w.append("")
        w.append("```")
        store_cmd = self._store_command()
        w.append("%s dashboard      # active records, at a glance" % store_cmd)
        w.append("%s verify         # is the store healthy" % store_cmd)
        w.append("%s handovers      # anything waiting to be picked up"
                 % store_cmd)
        w.append("%s generate       # rewrite this folder" % self.command())
        w.append("```")
        w.append("")
        w.append("## Regenerate this folder")
        w.append("")
        w.append("Safe to run at any time. Everything outside the human markers "
                 "is rewritten; everything inside them is preserved byte for "
                 "byte. Two runs in a row produce identical bytes, so an empty "
                 "diff after regenerating is the expected result and a non "
                 "empty one means a fact moved.")
        w.append("")
        w.append("## If the store is unhappy")
        w.append("")
        w.append("- `%s verify` names what it found rather than guessing."
                 % store_cmd)
        w.append("- A busy or locked database is a refusal, not a crash: wait "
                 "and retry.")
        w.append("- A damaged database is moved aside rather than written "
                 "over, and the refusal says where it went.")
        w.append("")
        w.append("## Roll this folder back")
        w.append("")
        w.append("Everything under `%s/` is generated output. Removing it "
                 "destroys no recorded fact and no human block that was "
                 "committed with it, and the next generate rebuilds the "
                 "generated parts." % DOC_ROOT)
        w.append("")
        w.append("```")
        w.append("git rm -r %s" % DOC_ROOT)
        w.append("```")
        w.append("")
        return w

    def _store_command(self):
        here = os.path.abspath(os.path.join(HERE, "bm_store.py"))
        root = os.path.abspath(self.root)
        if here.startswith(root + os.sep):
            return "python3 %s" % os.path.relpath(here, root).replace("\\", "/")
        return bs.invocation("bm_store.py", here)


# ---------------------------------------------------------------------------
# Commands.
# ---------------------------------------------------------------------------

def _root():
    root, _source = bs.require_root()
    return root


def _store():
    return bs.Store(_root(), create=False)


def _tier_flag(kv):
    if "tier" not in kv:
        return None
    raw = kv["tier"]
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise DocsError("bad-tier",
                        "--tier takes 1, 2 or 3; got %r" % raw)
    if value not in TIERS:
        raise DocsError("bad-tier",
                        "--tier takes 1 (lean), 2 (standard) or 3 (full); got %d"
                        % value)
    return value


def cmd_tier(argv):
    """The signals and the decision, printed. Writes nothing."""
    _pos, kv = _parse(argv, {"tier", "json"}, wants_value=("tier",))
    explicit = _tier_flag(kv)
    root = _root()
    store = _store()
    try:
        gen = Generator(root, store, explicit_tier=explicit)
        payload = {"tier": gen.tier, "tier_name": TIERS[gen.tier],
                   "tier_source": gen.decision["source"],
                   "tier_reasons": gen.decision["reasons"],
                   "recorded_floor": gen.floor,
                   "signals": gen.signals,
                   "would_emit": [rel for rel, _t, _w in gen.emitted()]}
    finally:
        store.close()
    if kv.get("json"):
        _out(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    _out("tier %d (%s), chosen %s"
         % (payload["tier"], payload["tier_name"], payload["tier_source"]))
    for reason in payload["tier_reasons"]:
        _out("  %s" % reason)
    _out("signals:")
    for key in sorted(payload["signals"]):
        _out("  %s: %s" % (key, payload["signals"][key]))
    _out("would emit %d file(s):" % len(payload["would_emit"]))
    for rel in payload["would_emit"]:
        _out("  %s/%s" % (DOC_ROOT, rel))
    return 0


def cmd_generate(argv):
    _pos, kv = _parse(argv, {"tier", "json"}, wants_value=("tier",))
    explicit = _tier_flag(kv)
    root = _root()
    store = _store()
    try:
        gen = Generator(root, store, explicit_tier=explicit)
        report = gen.write()
    finally:
        store.close()
    if kv.get("json"):
        _out(json.dumps(report, indent=2, sort_keys=True))
        return 0
    _out("wrote %d file(s) under %s at tier %d (%s), chosen %s"
         % (len(report["files"]), DOC_ROOT, report["tier"],
            report["tier_name"], report["tier_source"]))
    for reason in report["tier_reasons"]:
        _out("  %s" % reason)
    for entry in report["files"]:
        _out("  %s" % entry["path"])
    _out("  %d human block(s) preserved verbatim"
         % report["human_blocks_preserved"])
    _out("  narrative: %d block(s) reused against unchanged facts, %d "
         "regenerated" % (report["prose_reused"], report["prose_regenerated"]))
    if report["critical_path"]:
        _out("  critical path: %s (%d recorded day(s))"
             % (" -> ".join(report["critical_path"]), report["critical_days"]))
    for rel in report["stale_from_a_deeper_tier"]:
        _out("  LEFT BEHIND and no longer maintained: %s/%s. Nothing was "
             "deleted; it may hold a human block." % (DOC_ROOT, rel))
    flagged = [(e["path"], e["secret_shaped_human_lines"])
               for e in report["files"] if e["secret_shaped_human_lines"]]
    for path, lines in flagged:
        _out("  KEPT VERBATIM AND WORTH READING: %s line(s) %s inside a human "
             "block look secret shaped. Nothing was rewritten (I10)."
             % (path, ", ".join(str(i) for i in lines)))
    return 0


def cmd_facts(argv):
    """The projected facts, as JSON. The same object facts.json carries, so a
    reader can diff what a page claims against what the store holds."""
    _pos, kv = _parse(argv, {"tier", "json"}, wants_value=("tier",))
    explicit = _tier_flag(kv)
    root = _root()
    store = _store()
    try:
        gen = Generator(root, store, explicit_tier=explicit)
        payload = gen.facts
    finally:
        store.close()
    _out(json.dumps(payload, indent=2, sort_keys=True, default=str))
    return 0


COMMANDS = {"tier": cmd_tier, "generate": cmd_generate, "facts": cmd_facts}


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        _out(__doc__.strip())
        _out("")
        _out("commands: %s" % ", ".join(sorted(COMMANDS)))
        return 0
    cmd = argv[0]
    if cmd not in COMMANDS:
        _err("bm_docs: unknown command %r (known: %s)"
             % (cmd, ", ".join(sorted(COMMANDS))))
        return 2
    try:
        return COMMANDS[cmd](argv[1:])
    except DocsError as e:
        _err("refused (%s): %s" % (e.reason, e))
        return 2
    except bs.OwnershipRefused as e:
        _err("refused (%s): %s" % (e.reason, e))
        return 2
    except bs.BMStoreError as e:
        _err("bm_docs: %s" % e)
        return 2


def cli():
    """Console-script entry point for a packaged install. Must be callable with
    no arguments, so it wraps main(argv) rather than being it."""
    sys.exit(main(sys.argv[1:]))


if __name__ == "__main__":
    cli()
