#!/usr/bin/env python3
"""BrotherMode correction learning: the founder's command line.

WHAT THIS IS FOR
  You correct me. That correction should survive the session, apply when it is
  relevant, and never change my behaviour until YOU said so. This command line
  is the only path from "you said something" to "it is a rule", and every step
  of it is yours.

THE FIVE SEPARATE QUESTIONS, KEPT SEPARATE ON PURPOSE
  Most systems collapse these into one claim that the assistant "learned":
    1. capture       did you correct me, and what exactly did you say
    2. interpretation what narrow trigger and action does that evidence support
    3. approval      did you approve that interpretation as a rule
    4. application   was the rule retrieved and followed when it mattered
    5. outcome       did following it help
  This tool keeps them auditable, so "it learned" is never a claim you have to
  take on trust.

WHAT THIS FILE MAY NOT DO
  It never writes the database directly. Every mutation goes through
  bm_store.py, which stays the single writer. It performs no network access and
  spawns no subprocess.

APPROVAL IS DELIBERATELY MANUAL
  There is no --auto, no daemon, and no hook that can approve anything. The
  approve command requires you to run it and to supply a reference recorded as
  evidence. A background process cannot promote a candidate even by accident,
  because the code path that creates rules refuses without that reference.

RETRIEVAL MODE: lexical only today. No FTS5 index is built yet, and no output
here claims full-text or BM25 ranking. `relevant` prints the mode it used.

Python 3.9, standard library only.

No em or en dashes anywhere in this file, its comments, or its output.
"""

import importlib.util
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    """Load a sibling module by PATH, the same way bm_telemetry loads bm_store:
    this file is invoked from arbitrary working directories and must not depend
    on whatever sys.path the caller happened to have."""
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bs = _load("bm_store")
L = _load("bm_learning")


def _telemetry():
    """bm_telemetry owns the vault's corrections.jsonl inbox: its path, its
    permissions and its parser. Loaded lazily and by path so this file never
    reimplements the vault layout and then drifts from it. READ ONLY from here:
    no command in this CLI writes, moves or truncates that file."""
    return _load("bm_telemetry")


def _out(msg=""):
    sys.stdout.write("%s\n" % msg)


def _err(msg):
    sys.stderr.write("%s\n" % msg)


def _parse(argv, known, wants_value=()):
    """Flags into a dict, REFUSING anything unrecognized.

    An unknown flag exits non-zero and names itself. The sibling `bm_store.py
    claim --help` treats an unknown flag as a record name and silently claims
    something called "--help" (NOT-FINALIZED item 16); this file deliberately
    does not inherit that behaviour."""
    positional, kv, i = [], {}, 0
    while i < len(argv):
        tok = argv[i]
        if tok.startswith("--"):
            name = tok[2:]
            if name not in known:
                _err("bm_learn: unrecognized flag --%s (recognized: %s)"
                     % (name, ", ".join("--" + k for k in sorted(known))))
                sys.exit(2)
            if name in wants_value:
                if i + 1 >= len(argv):
                    _err("bm_learn: --%s needs a value" % name)
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


def _root():
    """require_root returns (root, source), not a bare path. Unpacked in ONE
    place so a caller cannot pass the tuple into a path function; doing exactly
    that raised "expected str, bytes or os.PathLike object, not tuple" on the
    first live run of this file."""
    root, _source = bs.require_root()
    return root


def _store(create=False):
    return bs.Store(_root(), create=create)


def _ctx(kv):
    """Task context for scope matching. The project defaults to the resolved
    project root's own name, so a project rule is scoped to where you actually
    are rather than to a string you had to remember to type."""
    ctx = {"project": os.path.basename(_root())}
    for key in ("project", "domain", "artifact", "relationship", "tool"):
        if kv.get(key):
            ctx[key] = kv[key]
    return ctx


def _rule_line(r):
    return "  %s  [%s%s, %s%s] v%d" % (
        r["rule_uuid"][:8],
        r["scope_type"],
        "" if r["scope_type"] == "global" else ":" + r["scope_key"],
        r["state"],
        ", gate" if r.get("severity") == "gate" else "",
        r["current_version"])


def cmd_capture(argv):
    pos, kv = _parse(argv, {"trigger", "action", "because", "domain", "scope",
                            "scope-key", "source", "session", "raw", "json"},
                     wants_value=("trigger", "action", "because", "domain",
                                  "scope", "scope-key", "source", "session", "raw"))
    scope = kv.get("scope", "project")
    scope_key = kv.get("scope-key")
    if scope_key is None and scope == "project":
        scope_key = os.path.basename(_root())
    store = _store()
    try:
        cand = store.capture_learning_candidate(
            kv.get("source", "explicit_correction"),
            raw_text=kv.get("raw", ""), trigger=kv.get("trigger", ""),
            action=kv.get("action", ""), because=kv.get("because", ""),
            domain=kv.get("domain", ""), scope_type=scope,
            scope_key=scope_key or "", session_id=kv.get("session", ""))
    finally:
        store.close()
    if kv.get("json"):
        _out(json.dumps(cand, indent=2, sort_keys=True))
        return 0
    _out("captured %s (pending, nothing changes until you approve it)"
         % cand["candidate_uuid"][:8])
    problems = L.atomicity_problems(cand["proposed_action"])
    if problems:
        _out("  heads up, this looks like more than one rule: %s" % "; ".join(problems))
        _out("  approval will refuse it unless you split it or pass --override-reason")
    return 0


def cmd_candidates(argv):
    pos, kv = _parse(argv, {"status", "json"}, wants_value=("status",))
    store = _store()
    try:
        rows = store.list_learning_candidates(kv.get("status", "pending"))
    finally:
        store.close()
    if kv.get("json"):
        _out(json.dumps(rows, indent=2, sort_keys=True))
        return 0
    if not rows:
        _out("no candidates with that status")
        return 0
    for c in rows:
        _out("  %s  [%s%s]  %s" % (
            c["candidate_uuid"][:8], c["proposed_scope_type"],
            "" if c["proposed_scope_type"] == "global" else ":" + c["proposed_scope_key"],
            c["status"]))
        if c["proposed_trigger"]:
            _out("     When: %s" % L.safe_display(c["proposed_trigger"], 100))
            _out("     Do  : %s" % L.safe_display(c["proposed_action"], 100))
        if c["raw_text"]:
            # The raw founder quote is NOT printed by default. It is the most
            # sensitive thing in the store and the least necessary for triage.
            _out("     source: %d chars captured, %d redactions (--show-source to read)"
                 % (len(c["raw_text"]), c["redaction_count"]))
    _out("")
    _out("%d candidate(s). Approve with: bm_learn.py approve <id> --because \"...\"" % len(rows))
    return 0


def cmd_show_candidate(argv):
    pos, kv = _parse(argv, {"show-source", "json"})
    if not pos:
        _err("usage: show-candidate <id> [--show-source] [--json]")
        return 2
    store = _store()
    try:
        c = store.get_learning_candidate(pos[0])
    finally:
        store.close()
    if kv.get("json"):
        if not kv.get("show-source"):
            c = dict(c)
            c["raw_text"] = "[withheld: pass --show-source]"
        _out(json.dumps(c, indent=2, sort_keys=True))
        return 0
    _out("candidate %s" % c["candidate_uuid"])
    for label, key in (("status", "status"), ("source", "source_type"),
                       ("scope", "proposed_scope_type"), ("trigger", "proposed_trigger"),
                       ("action", "proposed_action"), ("because", "proposed_because")):
        _out("  %-8s %s" % (label, L.safe_display(str(c[key]), 300)))
    if kv.get("show-source"):
        _out("  WARNING: the following is your own verbatim text, secrets scrubbed but")
        _out("           prose intact. Do not paste it somewhere public.")
        _out("  source   %s" % L.safe_display(c["raw_text"], 2000))
    else:
        _out("  source   %d chars withheld (--show-source to read)" % len(c["raw_text"] or ""))
    return 0


def cmd_approve(argv):
    pos, kv = _parse(argv, {"trigger", "action", "because", "domain", "scope",
                            "scope-key", "type", "gate", "override-reason",
                            "override-conflict", "ref", "json"},
                     wants_value=("trigger", "action", "because", "domain", "scope",
                                  "scope-key", "type", "override-reason",
                                  "override-conflict", "ref"))
    if not pos:
        _err("usage: approve <candidate-id> [--trigger ...] [--action ...] "
             "[--because ...] [--scope global|project|domain|artifact|relationship|tool] "
             "[--scope-key ...] [--gate] [--ref \"why you approved\"]")
        return 2
    # The invocation itself IS the founder act. Recording it as the default
    # reference keeps approval attributable without inventing an identity.
    ref = kv.get("ref") or ("bm_learn.py approve, run by the founder at %s" % bs.now_iso())
    store = _store()
    try:
        rule = store.approve_learning_candidate(
            pos[0], founder_ref=ref, trigger=kv.get("trigger"),
            action=kv.get("action"), because=kv.get("because"),
            domain=kv.get("domain"), scope_type=kv.get("scope"),
            scope_key=kv.get("scope-key"),
            rule_type=kv.get("type", "preference"),
            severity="gate" if kv.get("gate") else "soft",
            atomicity_override=kv.get("override-reason", ""),
            conflict_override=kv.get("override-conflict", ""))
    finally:
        store.close()
    if kv.get("json"):
        _out(json.dumps(rule, indent=2, sort_keys=True))
        return 0
    _out("approved as rule %s" % rule["rule_uuid"][:8])
    _out(_rule_line(rule))
    _out("     When: %s" % L.safe_display(rule["trigger_text"], 160))
    _out("     Do  : %s" % L.safe_display(rule["action_text"], 160))
    return 0


def cmd_reject(argv):
    pos, kv = _parse(argv, {"because"}, wants_value=("because",))
    if not pos or not kv.get("because"):
        _err("usage: reject <candidate-id> --because \"why not\"")
        return 2
    store = _store()
    try:
        c = store.reject_learning_candidate(pos[0], kv["because"])
    finally:
        store.close()
    _out("rejected %s. The reason is kept, so the same suggestion does not keep "
         "coming back." % c["candidate_uuid"][:8])
    return 0


def cmd_rules(argv):
    pos, kv = _parse(argv, {"json", "all"})
    store = _store()
    try:
        rows = store.list_learning_rules(include_forgotten=bool(kv.get("all")))
    finally:
        store.close()
    if kv.get("json"):
        _out(json.dumps(rows, indent=2, sort_keys=True))
        return 0
    if not rows:
        _out("no approved rules yet")
        return 0
    for r in rows:
        _out(_rule_line(r))
        _out("     When: %s" % L.safe_display(r["trigger_text"], 120))
        _out("     Do  : %s" % L.safe_display(r["action_text"], 120))
    _out("")
    _out("%d rule(s)." % len(rows))
    return 0


def cmd_relevant(argv):
    """Loop 5's founder-facing surface. READ ONLY: asking what applies records
    nothing, so the outcome data can never be polluted by mere curiosity."""
    pos, kv = _parse(argv, {"query", "project", "domain", "artifact",
                            "relationship", "tool", "limit", "json"},
                     wants_value=("query", "project", "domain", "artifact",
                                  "relationship", "tool", "limit"))
    query = kv.get("query") or " ".join(pos)
    if not query.strip():
        _err("usage: relevant --query \"what you are about to do\" [--artifact ...] [--limit N]")
        return 2
    try:
        limit = int(kv.get("limit", 5))
    except ValueError:
        _err("bm_learn: --limit needs a whole number")
        return 2
    store = _store()
    try:
        res = store.retrieve_learning_rules(query, context=_ctx(kv), limit=limit)
    finally:
        store.close()
    if kv.get("json"):
        _out(json.dumps(res, indent=2, sort_keys=True))
        return 0
    if not res["results"]:
        _out("no founder rules apply here (%d in scope, none matched; mode=%s)"
             % (res["eligible"], res["mode"]))
        return 0
    _out("RELEVANT FOUNDER RULES (mode=%s)" % res["mode"])
    for r in res["results"]:
        why = r["why"]
        _out("")
        _out("  %s  rank=%d" % (r["rule_uuid"][:8], r["rank"]))
        _out("  Scope: %s     State: %s%s" % (
            why["scope"], why["state"], "     GATE" if r.get("severity") == "gate" else ""))
        _out("  When : %s" % L.safe_display(r["trigger_text"], 160))
        _out("  Do   : %s" % L.safe_display(r["action_text"], 160))
        if r.get("because_text"):
            _out("  Why  : %s" % L.safe_display(r["because_text"], 160))
        _out("  Match: terms %s, relevance %s"
             % (why["matched_terms"] or "(none, shown because it is a gate)",
                why["relevance"]))
        if r.get("conflicts_with"):
            _out("  CONFLICT: contradicts %s. Both are live; see below."
                 % ", ".join(u[:8] for u in r["conflicts_with"]))
    if res.get("conflicts"):
        # Surfaced, not resolved. Silently dropping one side would be this tool
        # deciding which of your instructions is the real one, and it does not
        # get to make that call.
        _out("")
        _out("UNRESOLVED CONFLICT (%d). Two of your rules disagree, so neither is "
             "authoritative until you say which stands." % len(res["conflicts"]))
        for p in res["conflicts"]:
            _out("")
            _pair_block(p)
        _out("")
        _out("Decide with: bm_learn.py resolve-conflict <rule> --with <other> "
             "--how superseded|contradicted|deprecated --because \"...\"")
    _out("")
    _out("Constitution overrides learned rules. %d omitted." % res["omitted"])
    return 0


def cmd_forget(argv):
    pos, kv = _parse(argv, {"yes", "because"}, wants_value=("because",))
    if not pos:
        _err("usage: forget <rule-id> --yes")
        return 2
    if not kv.get("yes"):
        _err("forget removes a rule from every future retrieval. Re-run with --yes "
             "if that is what you want.")
        return 2
    store = _store()
    try:
        r = store.change_learning_rule_state(pos[0], "forgotten",
                                              reason=kv.get("because", ""))
    finally:
        store.close()
    _out("forgotten %s. It will not be retrieved again. A tombstone remains so "
         "past applications stay honest." % r["rule_uuid"][:8])
    return 0


def cmd_deprecate(argv):
    pos, kv = _parse(argv, {"because"}, wants_value=("because",))
    if not pos:
        _err("usage: deprecate <rule-id> --because \"...\"")
        return 2
    store = _store()
    try:
        r = store.change_learning_rule_state(pos[0], "deprecated",
                                              reason=kv.get("because", ""))
    finally:
        store.close()
    _out("deprecated %s (kept for history, not retrieved)" % r["rule_uuid"][:8])
    return 0


def cmd_why(argv):
    pos, kv = _parse(argv, {"json"})
    if not pos:
        _err("usage: why <rule-id>")
        return 2
    store = _store()
    try:
        rule = store.get_learning_rule(pos[0])
        ev = store.list_learning_evidence(rule["rule_uuid"])
        versions = [dict(r) for r in store.conn.execute(
            "SELECT version, change_type, change_reason, created_at "
            "FROM learning_rule_versions WHERE rule_uuid=? ORDER BY version",
            (rule["rule_uuid"],)).fetchall()]
    finally:
        store.close()
    if kv.get("json"):
        _out(json.dumps({"rule": rule, "evidence": ev, "versions": versions},
                        indent=2, sort_keys=True))
        return 0
    _out("rule %s" % rule["rule_uuid"])
    _out(_rule_line(rule))
    _out("  When: %s" % L.safe_display(rule["trigger_text"], 200))
    _out("  Do  : %s" % L.safe_display(rule["action_text"], 200))
    _out("  Why : %s" % L.safe_display(rule["because_text"], 200))
    _out("")
    _out("  versions:")
    for v in versions:
        _out("    v%d  %s  %s" % (v["version"], v["change_type"],
                                   L.safe_display(v["change_reason"], 80)))
    _out("  evidence (%d):" % len(ev))
    for e in ev:
        _out("    %s %s  %s" % (e["polarity"], e["evidence_type"],
                                 L.safe_display(e["source_ref"], 70)))
    return 0


def cmd_inbox(argv):
    """Show, and on request import, the GLOBAL correction capture inbox.

    The inbox is one file shared by every project on this machine. This store is
    the system of record for THIS project. Importing is triage: an inbox row
    becomes a pending candidate here, scoped to this project, and it stays
    pending until you approve it. Nothing is approved, and the inbox file itself
    is only ever read."""
    pos, kv = _parse(argv, {"file", "backfill", "json"}, wants_value=("file",))
    bt = _telemetry()
    path = kv.get("file") or bt.CORRECTIONS
    if not os.path.isfile(path):
        _out("no correction inbox at %s (nothing captured yet)" % path)
        return 0
    rows, bad = bt.read_jsonl(path, report_bad=True)
    # read_jsonl returns any valid JSON VALUE, so a hand-edited line holding a
    # bare string or a number parses fine and is not a row. Counted and named,
    # never a traceback in the founder's face.
    malformed = sum(1 for r in rows if not isinstance(r, dict))
    rows = [r for r in rows if isinstance(r, dict)]
    if not kv.get("backfill"):
        store = _store()
        try:
            known = {c["content_hash"] for c in store.list_learning_candidates(status=None)
                     if c["source_type"] == "detected_correction"}
        finally:
            store.close()
        new = [r for r in rows
               if L.inbox_identity(r.get("session_id", ""), r.get("text", ""))
               not in known]
        if kv.get("json"):
            _out(json.dumps({"path": path, "rows": len(rows), "not_yet_imported": len(new),
                             "unparsable_lines": bad, "malformed_rows": malformed},
                            indent=2, sort_keys=True))
            return 0
        _out("inbox %s" % path)
        _out("  %d row(s), %d not yet imported into this project" % (len(rows), len(new)))
        if malformed:
            _out("  %d line(s) parsed but were not a row object; skipped" % malformed)
        if bad:
            _out("  %d line(s) could not be parsed (line numbers %s); the text is not "
                 "printed because it is yours" % (len(bad), bad))
        for r in new:
            _out("  %s  %s  %s" % (r.get("ts", "?")[:19], r.get("project", "?"),
                                    L.safe_display(r.get("text", ""), 90)))
        _out("")
        _out("import them with: bm_learn.py inbox --backfill (nothing is approved)")
        return 0
    store = _store()
    try:
        res = store.import_correction_inbox(rows, source_label=os.path.basename(path))
    finally:
        store.close()
    if kv.get("json"):
        _out(json.dumps(res, indent=2, sort_keys=True))
        return 0
    _out("imported %d candidate(s), skipped %d already present"
         % (res["imported"], res["skipped"]))
    bad_shape = malformed + res.get("malformed", 0)
    if bad_shape:
        _out("  %d line(s) parsed but were not a row object; skipped" % bad_shape)
    if res["possible_duplicates"]:
        _out("  %d flagged as a possible duplicate of an earlier candidate; the note "
             "is on the candidate, nothing was discarded" % res["possible_duplicates"])
    _out("All pending. Review with: bm_learn.py candidates")
    return 0


def cmd_outcome(argv):
    """Capture channel 3: a candidate derived from an OUTCOME, not from words.

    You redid the same artifact, or a defect escaped a record you had already
    completed. That is evidence some preference was not followed, so it becomes
    a pending candidate carrying the work record and the artifact it is about.
    It is still only a candidate: the action text is empty, so it cannot become
    a rule until you write one at approval.

    usage: outcome <record-id> --kind rework|escaped_defect
                   [--artifact PATH] [--note "what happened"]
    The artifact defaults to the paths that record claims."""
    pos, kv = _parse(argv, {"kind", "artifact", "note", "session", "scope-key", "json"},
                     wants_value=("kind", "artifact", "note", "session", "scope-key"))
    if not pos:
        _err("usage: outcome <record-id> --kind rework|escaped_defect "
             "[--artifact PATH] [--note \"what happened\"]")
        return 2
    store = _store()
    try:
        cand = store.capture_outcome_candidate(
            kv.get("kind", "rework"), pos[0], artifact_ref=kv.get("artifact", ""),
            summary=kv.get("note", ""), session_id=kv.get("session", ""),
            scope_key=kv.get("scope-key"))
    finally:
        store.close()
    if kv.get("json"):
        _out(json.dumps(cand, indent=2, sort_keys=True))
        return 0
    _out("captured %s from %s (pending, nothing changes until you approve it)"
         % (cand["candidate_uuid"][:8], cand["source_type"]))
    _out("  %s" % L.safe_display(cand["source_ref"], 160))
    if cand["review_note"]:
        _out("  %s" % L.safe_display(cand["review_note"], 160))
    return 0


def cmd_metrics(argv):
    """Descriptive capture volumes. Deliberately NOT called accuracy."""
    pos, kv = _parse(argv, {"json"})
    store = _store()
    try:
        m = store.learning_capture_metrics()
    finally:
        store.close()
    if kv.get("json"):
        _out(json.dumps(m, indent=2, sort_keys=True))
        return 0
    _out("capture metrics (descriptive counts, not accuracy)")
    _out("  candidates by status: %s" % (m["candidates_by_status"] or "none"))
    _out("  candidates by source: %s" % (m["candidates_by_source"] or "none"))
    _out("  possible duplicates flagged: %d" % m["possible_duplicates"])
    _out("  false positive reasons: %s" % (m["false_positive_reasons"] or "none rejected yet"))
    _out("  approved rules: %d" % m["rules_total"])
    _out("")
    _out("There is no labelled review set, so none of these is a precision or a")
    _out("recall number, and none of them should be read as one.")
    return 0


def _pair_block(p):
    """One conflicting pair, printed the same way everywhere it appears.

    Only the two rules' own trigger and action text reaches this function; the
    store's _conflict_side already dropped every capture excerpt and source
    reference, so a conflict report can be read out or pasted somewhere without
    carrying the founder's verbatim words with it."""
    _out("  %s  vs  %s      (%s)" % (
        p["a"]["rule_uuid"][:8], p["b"]["rule_uuid"][:8],
        "you declared this" if p["declared"] else "detected: " + ", ".join(p["reasons"])))
    for side in ("a", "b"):
        s = p[side]
        _out("    %s  [%s, %s]" % (s["rule_uuid"][:8], s["scope"], s["state"]))
        _out("       When: %s" % L.safe_display(s["trigger"], 140))
        _out("       Do  : %s" % L.safe_display(s["action"], 140))


def cmd_conflicts(argv):
    """What currently disagrees with what. Reports, never resolves."""
    pos, kv = _parse(argv, {"json"})
    store = _store()
    try:
        res = store.learning_conflicts()
    finally:
        store.close()
    if kv.get("json"):
        _out(json.dumps(res, indent=2, sort_keys=True))
        return 0
    if not res["contradictions"] and not res["duplicates"]:
        _out("no conflicts between the rules that can currently speak")
        return 0
    if res["contradictions"]:
        _out("CONTRADICTIONS (%d). Both rules are live, so both would be injected."
             % len(res["contradictions"]))
        for p in res["contradictions"]:
            _out("")
            _pair_block(p)
        _out("")
        _out("Resolve one with: bm_learn.py resolve-conflict <rule> --with <other> "
             "--how superseded|contradicted|deprecated --because \"...\"")
    if res["duplicates"]:
        _out("")
        _out("POSSIBLE DUPLICATES (%d)" % len(res["duplicates"]))
        for p in res["duplicates"]:
            _out("")
            _pair_block(p)
    return 0


def cmd_link(argv):
    """Record a relationship the detector cannot see.

    The lexical detector finds a reversal ("always X" against "never X"). It
    cannot find that "use tabs" and "use spaces" fight. You can, so you can say
    so, and a declared conflict counts exactly as much as a detected one."""
    pos, kv = _parse(argv, {"because", "json"}, wants_value=("because",))
    if len(pos) != 3:
        _err("usage: link <rule-a> <relation> <rule-b> --because \"...\"")
        _err("relations: %s" % ", ".join(r for r in L.RELATIONS if r != "supersedes"))
        _err("supersession is its own command, because it changes state: supersede")
        return 2
    store = _store()
    try:
        edge = store.link_learning_rules(pos[0], pos[2], pos[1],
                                          note=kv.get("because", ""))
    finally:
        store.close()
    if kv.get("json"):
        _out(json.dumps(edge, indent=2, sort_keys=True))
        return 0
    _out("recorded: %s %s %s" % (edge["from_rule_uuid"][:8], edge["relation"],
                                  edge["to_rule_uuid"][:8]))
    if edge["relation"] == "contradicts":
        _out("Both rules are still live. Run conflicts to see it, and "
             "resolve-conflict when you decide which one stands.")
    return 0


def cmd_merge(argv):
    """Fold a duplicate candidate into the rule it repeats."""
    pos, kv = _parse(argv, {"into", "because", "json"},
                     wants_value=("into", "because"))
    if not pos or not kv.get("into"):
        _err("usage: merge <candidate-id> --into <rule-id> --because \"...\"")
        return 2
    store = _store()
    try:
        rule = store.merge_learning_candidate(pos[0], kv["into"],
                                               reason=kv.get("because", ""))
    finally:
        store.close()
    if kv.get("json"):
        _out(json.dumps(rule, indent=2, sort_keys=True))
        return 0
    _out("merged into rule %s. No second rule was created, and the candidate is "
         "kept as supporting evidence on that rule." % rule["rule_uuid"][:8])
    return 0


def cmd_supersede(argv):
    """Replace an old rule with a newer one, in one step."""
    pos, kv = _parse(argv, {"with", "because", "json"},
                     wants_value=("with", "because"))
    if not pos or not kv.get("with"):
        _err("usage: supersede <old-rule> --with <new-rule> --because \"...\"")
        return 2
    store = _store()
    try:
        old = store.change_learning_rule_state(
            pos[0], "superseded", reason=kv.get("because", ""),
            successor_prefix=kv["with"])
    finally:
        store.close()
    if kv.get("json"):
        _out(json.dumps(old, indent=2, sort_keys=True))
        return 0
    _out("%s is superseded. It is no longer retrieved; the successor is returned "
         "in its place from now on." % old["rule_uuid"][:8])
    return 0


def cmd_resolve_conflict(argv):
    """Stand one rule down so a conflict stops being live.

    You choose which one. This command records the choice and the reason; it
    has no opinion about which rule was right."""
    pos, kv = _parse(argv, {"with", "how", "because", "json"},
                     wants_value=("with", "how", "because"))
    if not pos or not kv.get("with") or not kv.get("how"):
        _err("usage: resolve-conflict <rule> --with <other-rule> "
             "--how superseded|contradicted|deprecated --because \"...\"")
        _err("the rule you name is the one that stands down")
        return 2
    store = _store()
    try:
        r = store.resolve_learning_conflict(pos[0], kv["with"], kv["how"],
                                             reason=kv.get("because", ""))
    finally:
        store.close()
    if kv.get("json"):
        _out(json.dumps(r, indent=2, sort_keys=True))
        return 0
    _out("%s is now %s. It stops being injected; the record of why stays."
         % (r["rule_uuid"][:8], r["state"]))
    return 0


def cmd_verify(argv):
    """Integrity of the learning tables, with an exit code a script can read.

    0 clean, 1 findings, 2 the command itself could not run. That is the whole
    contract, and it is why this prints a count even when it is zero."""
    pos, kv = _parse(argv, {"json"})
    store = _store()
    try:
        res = store.learning_verify()
    finally:
        store.close()
    if kv.get("json"):
        _out(json.dumps(res, indent=2, sort_keys=True))
        return 0 if res["ok"] else 1
    _out("learning-verify: %d rule(s), %d edge(s), %d check(s) run"
         % (res["rules"], res["edges"], len(res["checks"])))
    for note in res["notes"]:
        _out("  note: %s" % note)
    if res["ok"]:
        _out("  no findings")
        return 0
    _out("  %d finding(s):" % len(res["findings"]))
    for f in res["findings"]:
        _out("    %-28s %s" % (f["code"], L.safe_display(f["detail"], 160)))
    return 1


COMMANDS = {
    "capture": cmd_capture,
    "outcome": cmd_outcome,
    "inbox": cmd_inbox,
    "metrics": cmd_metrics,
    "candidates": cmd_candidates,
    "show-candidate": cmd_show_candidate,
    "approve": cmd_approve,
    "reject": cmd_reject,
    "rules": cmd_rules,
    "relevant": cmd_relevant,
    "why": cmd_why,
    "deprecate": cmd_deprecate,
    "forget": cmd_forget,
    "conflicts": cmd_conflicts,
    "link": cmd_link,
    "merge": cmd_merge,
    "supersede": cmd_supersede,
    "resolve-conflict": cmd_resolve_conflict,
    "verify": cmd_verify,
}


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        _out(__doc__.strip())
        _out("")
        _out("commands: %s" % ", ".join(sorted(COMMANDS)))
        return 0
    cmd = argv[0]
    if cmd not in COMMANDS:
        _err("bm_learn: unknown command %r (known: %s)"
             % (cmd, ", ".join(sorted(COMMANDS))))
        return 2
    try:
        return COMMANDS[cmd](argv[1:])
    except bs.OwnershipRefused as e:
        # Fail CLOSED and say which rule refused, so the next step is obvious
        # rather than a guess. Matches bm_threads.py's failure policy.
        _err("refused (%s): %s" % (e.reason, e))
        return 2
    except bs.StaleIdentity as e:
        _err("refused (stale-identity): %s" % e)
        return 2
    except bs.BMStoreError as e:
        _err("bm_learn: %s" % e)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
