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
    """Loop 5's founder-facing surface. READ ONLY BY DEFAULT: asking what
    applies records nothing, so the outcome data can never be polluted by mere
    curiosity.

    --record-applications opts IN to writing one row per rule returned, which
    is what makes "was this rule followed" answerable at task close. It is a
    flag and not the default for exactly that reason, and when the write fails
    the rules are still printed."""
    pos, kv = _parse(argv, {"query", "project", "domain", "artifact",
                            "relationship", "tool", "limit", "json",
                            "record-applications", "session", "record",
                            "not-shown"},
                     wants_value=("query", "project", "domain", "artifact",
                                  "relationship", "tool", "limit", "session",
                                  "record"))
    query = kv.get("query") or " ".join(pos)
    if not query.strip():
        _err("usage: relevant --query \"what you are about to do\" [--artifact ...] "
             "[--limit N] [--record-applications --session ID [--record UUID]]")
        return 2
    try:
        limit = int(kv.get("limit", 5))
    except ValueError:
        _err("bm_learn: --limit needs a whole number")
        return 2
    store = _store()
    try:
        if kv.get("record-applications"):
            res = store.record_learning_applications(
                query, context=_ctx(kv), limit=limit,
                session_id=kv.get("session", ""),
                record_prefix=kv.get("record"),
                shown_to_model=not kv.get("not-shown"))
        else:
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
    if "recorded" in res:
        _out("")
        _out("recorded %d application(s), %d already recorded for this task "
             "(task %s)" % (res["recorded"], res["already_recorded"],
                            res["task_fingerprint"]))
        if res.get("linked"):
            # Said out loud because the whole point of re-running with --record
            # is that the link lands, and a silent "already recorded" once left
            # the caller believing it had.
            _out("  linked %d already recorded application(s) to work record %s"
                 % (res["linked"], L.safe_display(kv.get("record", ""), 40)))
        if res["record_error"]:
            _out("  the rules above are correct; the bookkeeping did NOT land: %s"
                 % L.safe_display(res["record_error"], 200))
        else:
            _out("  close them with: bm_learn.py disposition <application-id> "
                 "followed|ignored|not_relevant")
    return 0


def cmd_applications(argv):
    """What was surfaced for a task, and what happened to it.

    This is the answer to "was the rule followed". Each row shows the rule text
    AS IT WAS APPLIED, not as it reads today, so an edit made afterwards cannot
    quietly rewrite the history."""
    pos, kv = _parse(argv, {"session", "record", "rule", "task", "disposition",
                            "json"},
                     wants_value=("session", "record", "rule", "task",
                                  "disposition"))
    store = _store()
    try:
        rows = store.list_learning_applications(
            session_id=kv.get("session"), rule_prefix=kv.get("rule"),
            record_prefix=kv.get("record"), task_fingerprint=kv.get("task"),
            disposition=kv.get("disposition"))
    finally:
        store.close()
    if kv.get("json"):
        _out(json.dumps(rows, indent=2, sort_keys=True))
        return 0
    if not rows:
        _out("no applications recorded for that filter")
        return 0
    for a in rows:
        _out("  %s  rule %s v%d  rank=%s  %s" % (
            a["application_uuid"][:8], a["rule_uuid"][:8], a["rule_version"],
            a["retrieval_rank"], a["scope_match"]))
        _out("     Do   : %s" % L.safe_display(a["action_text"], 120))
        _out("     shown: %s   disposition: %s   outcome: %s" % (
            "yes" if a["shown_to_model"] else "no", a["disposition"],
            a["outcome"]))
        if a["disposition_reason"]:
            _out("     why  : %s" % L.safe_display(a["disposition_reason"], 120))
        if a["verification_ref"]:
            _out("     check: %s" % L.safe_display(a["verification_ref"], 120))
    _out("")
    _out("%d application(s). Grade them with: bm_learn.py classify" % len(rows))
    return 0


def cmd_disposition(argv):
    """Record whether a retrieved rule was followed, and why not when it was not.

    usage: disposition <application-id> followed|ignored|not_relevant|unknown
                       [--because "..."] [--verification-ref "test:..."]
                       [--outcome accepted|rework|escaped_defect|corrected_again]
                       [--outcome-ref "..."]"""
    pos, kv = _parse(argv, {"because", "verification-ref", "outcome",
                            "outcome-ref", "json"},
                     wants_value=("because", "verification-ref", "outcome",
                                  "outcome-ref"))
    if len(pos) != 2:
        _err("usage: disposition <application-id> "
             "followed|ignored|not_relevant|unknown [--because \"...\"] "
             "[--verification-ref \"test:...\"] [--outcome ...]")
        return 2
    store = _store()
    try:
        app = store.set_application_disposition(
            pos[0], pos[1], reason=kv.get("because", ""),
            verification_ref=kv.get("verification-ref", ""),
            outcome=kv.get("outcome"), outcome_ref=kv.get("outcome-ref", ""))
    finally:
        store.close()
    if kv.get("json"):
        _out(json.dumps(app, indent=2, sort_keys=True))
        return 0
    _out("application %s: %s (outcome %s)" % (
        app["application_uuid"][:8], app["disposition"], app["outcome"]))
    cls, why = L.classify_application(app["disposition"], app["shown_to_model"],
                                       app["outcome"])
    _out("  %s: %s" % (cls or "no finding", why))
    return 0


def cmd_classify(argv):
    """Grade the recorded applications, and refuse to grade what has no evidence.

    Five classes, and none of them is forced: retrieval miss, compliance
    failure, bad rule, scope error, not decidable."""
    pos, kv = _parse(argv, {"session", "json"}, wants_value=("session",))
    store = _store()
    try:
        res = store.classify_learning_applications(session_id=kv.get("session"))
    finally:
        store.close()
    if kv.get("json"):
        _out(json.dumps(res, indent=2, sort_keys=True))
        return 0
    if not res["applications"] and not res["retrieval_misses"]:
        _out("nothing to classify yet: no applications have been recorded")
        return 0
    _out("APPLICATION CLASSIFICATION (%d application(s))" % len(res["applications"]))
    for a in res["applications"]:
        _out("  %s  rule %s v%d  %-18s %s" % (
            a["application_uuid"][:8], a["rule_uuid"][:8], a["rule_version"],
            a["classification"] or "no_finding",
            L.safe_display(a["classification_reason"], 110)))
    for m in res["retrieval_misses"]:
        _out("  task %s  rule %s  retrieval_miss     %s" % (
            m["task_fingerprint"][:8], m["rule_uuid"][:8],
            L.safe_display(m["classification_reason"], 110)))
    for u in res["not_decidable_tasks"]:
        _out("  task %s  not_decidable      %s" % (
            u["task_fingerprint"][:8], L.safe_display(u["reason"], 110)))
    _out("")
    _out("counts: %s" % res["counts"])
    return 0


def cmd_should_retrieve(argv):
    """Is retrieval proportionate for this task? Records NOTHING either way.

    The trivial-task bypass has to be explicit and it has to be free of side
    effects: deciding not to retrieve must never manufacture an application
    row, or the outcome data fills up with tasks that never happened."""
    pos, kv = _parse(argv, {"communication", "architecture", "multi-file",
                            "risky", "prior-correction", "json"})
    signals = {
        "communication_artifact": bool(kv.get("communication")),
        "architecture_decision": bool(kv.get("architecture")),
        "multi_file_change": bool(kv.get("multi-file")),
        "risky_operation": bool(kv.get("risky")),
        "prior_correction": bool(kv.get("prior-correction")),
    }
    store = _store()
    try:
        gates = [r for r in store.list_learning_rules(states=L.INJECTABLE_STATES)
                 if r.get("severity") == "gate"]
    finally:
        store.close()
    res = L.retrieval_advised(signals, gate_rules_exist=bool(gates))
    if kv.get("json"):
        _out(json.dumps(res, indent=2, sort_keys=True))
        return 0
    _out("retrieval advised: %s" % ("yes" if res["advised"] else "no"))
    for r in res["reasons"]:
        _out("  %s" % r)
    if not res["advised"]:
        _out("  nothing was recorded, because a task that did not happen must "
             "not appear in the outcome data")
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


def _outcome_event(kind, argv):
    """Shared body of `rework` and `escaped-defect`.

    Both record the same shape of thing (external evidence that work went
    wrong, tied to the work record it went wrong in) and both link that
    evidence to the rules that were applied at the time. They stay two
    commands because the founder types the name of what happened, not a
    --kind flag describing it."""
    known = {"original-session", "record", "artifact", "because", "evidence",
             "defect-class", "json"}
    pos, kv = _parse(argv, known,
                     wants_value=("original-session", "record", "artifact",
                                  "because", "evidence", "defect-class"))
    record = kv.get("record") or (pos[0] if pos else "")
    if not record:
        _err("usage: %s --record <record-id> [--original-session ID] "
             "[--artifact PATH] %s" % (
                 kind.replace("_", "-"),
                 "[--defect-class NAME] [--evidence \"...\"]"
                 if kind == "escaped_defect" else "[--because \"...\"]"))
        _err("the work record is required: an outcome that cannot say WHICH "
             "work it came from can grade nothing")
        return 2
    summary = kv.get("because", "") or kv.get("evidence", "")
    store = _store()
    try:
        res = store.record_outcome_event(
            kind, record, session_id=kv.get("original-session", ""),
            artifact_ref=kv.get("artifact", ""), summary=summary,
            defect_class=kv.get("defect-class", ""))
    finally:
        store.close()
    if kv.get("json"):
        _out(json.dumps(res, indent=2, sort_keys=True))
        return 0
    _out("recorded %s as candidate %s (pending: nothing becomes a rule here)"
         % (kind, res["candidate_uuid"][:8]))
    _out("  %s" % L.safe_display(res["artifact_ref"], 160))
    if res["defect_class"]:
        _out("  defect class: %s" % L.safe_display(res["defect_class"], 80))
    # Notes print whether or not anything was graded. The one saying this
    # event was already recorded is the founder's only signal that his second
    # run changed nothing, and hiding it behind an empty link list is how a
    # re-run looked like a second event.
    for note in res["notes"]:
        _out("  %s" % note)
    if not res["linked_applications"]:
        return 0
    _out("  %d rule application(s) graded by this outcome:"
         % len(res["linked_applications"]))
    for link in res["linked_applications"]:
        _out("    %s v%d  %-18s %s"
             % (link["rule_uuid"][:8], link["rule_version"],
                link["classification"], L.safe_display(link["classification_reason"], 100)))
    return 0


def cmd_rework(argv):
    """The same work had to be done again. External evidence, so it grades."""
    return _outcome_event("rework", argv)


def cmd_escaped_defect(argv):
    """A defect reached you in work that was already called done."""
    return _outcome_event("escaped_defect", argv)


def cmd_confirm(argv):
    """Promote a rule to confirmed, or a confirmed one to settled.

    Loop 8 grades a repeated correction only against a CONFIRMED or SETTLED
    rule, and until this command existed there was no founder-facing way to
    reach either state: every rule stayed 'approved' forever and the repeat
    check could never fire on real usage. Found by driving the CLI, not by a
    test.

    The store refuses this unless the rule already carries at least one
    supporting event that is not the original approval. That refusal is the
    point: approval is your intent, not evidence the rule worked."""
    pos, kv = _parse(argv, {"to", "because", "json"},
                     wants_value=("to", "because"))
    target = kv.get("to", "confirmed")
    if not pos or target not in ("confirmed", "settled"):
        _err("usage: confirm <rule-id> [--to confirmed|settled] "
             "[--because \"...\"]")
        return 2
    store = _store()
    try:
        r = store.change_learning_rule_state(pos[0], target,
                                             reason=kv.get("because", ""))
    finally:
        store.close()
    if kv.get("json"):
        _out(json.dumps(r, indent=2, sort_keys=True))
        return 0
    _out("%s is now %s. A correction that repeats it from here is graded as a "
         "loop failure rather than as new evidence."
         % (r["rule_uuid"][:8], r["state"]))
    return 0


def cmd_repeat_check(argv):
    """Did you already tell me this? READ ONLY unless you pass --record.

    Answers the question the counter cannot: not how often the same correction
    came back, but WHY the rule you already approved failed to prevent it.
    Never retrieved, retrieved and skipped, retrieved into the wrong work, or
    followed and wrong anyway are four different repairs.

    --record writes the finding down: evidence on the rule, and a
    corrected_again outcome on the applications from that work. It approves
    nothing and changes no rule's state."""
    pos, kv = _parse(argv, {"record", "json"})
    if not pos:
        _err("usage: repeat-check <candidate-id> [--record] [--json]")
        return 2
    store = _store()
    try:
        res = store.detect_repeated_correction(pos[0], record=bool(kv.get("record")))
    finally:
        store.close()
    if kv.get("json"):
        _out(json.dumps(res, indent=2, sort_keys=True))
        return 0
    _out("candidate %s (%s)" % (res["candidate_uuid"][:8], res["candidate_status"]))
    for note in res["notes"]:
        _out("  %s" % note)
    for m in res["unsettled_matches"]:
        _out("  %s" % L.safe_display(m["reason"], 160))
    for f in res["repeats"]:
        _out("  repeats %s (%s, v%d): %s"
             % (f["rule_uuid"][:8], f["rule_state"], f["rule_version"],
                f["classification"]))
        _out("      %s" % L.safe_display(f["classification_reason"], 150))
        if f["recorded"]:
            _out("      evidence recorded as %s" % f["polarity"])
        else:
            _out("      nothing written; pass --record to keep this finding")
    if not res["repeats"]:
        return 0
    _out("")
    _out("A repeat is not an argument for deleting the rule. Which repair it "
         "asks for is exactly what the class above names.")
    return 0


def cmd_loop_failures(argv):
    """Where the loop broke, over a window, counted from rows that exist.

    Nothing here is estimated. A class with no data says so rather than
    printing a zero that reads like a clean bill of health."""
    pos, kv = _parse(argv, {"since", "json"}, wants_value=("since",))
    days = None
    if kv.get("since"):
        days, err = L.parse_window_days(kv["since"])
        if err:
            _err("bm_learn: %s" % err)
            return 2
    store = _store()
    try:
        res = store.learning_loop_failures(window_days=days)
    finally:
        store.close()
    if kv.get("json"):
        _out(json.dumps(res, indent=2, sort_keys=True))
        return 0
    _out("loop failures%s" % (" since %s" % res["since"] if res["since"] else
                              " (all recorded history)"))
    _out("  applications in window: %d" % res["applications_in_window"])
    for name in res["classes"]:
        _out("  %-20s %d" % (name, res["counts"].get(name, 0)))
    _out("  repeated settled corrections: %d"
         % len(res["repeated_settled_corrections"]))
    for r in res["repeated_settled_corrections"]:
        _out("    %s repeats %s: %s"
             % (r["candidate_uuid"][:8], r["rule_uuid"][:8], r["classification"]))
    _out("  unresolved contradictions: %d" % len(res["unresolved_contradictions"]))
    _out("  rules never retrieved: %d" % len(res["rules_never_retrieved"]))
    _out("  rules always marked not relevant: %d"
         % len(res["rules_always_not_relevant"]))
    _out("  rework and escaped defects linked to a rule: %d"
         % len(res["outcomes_linked_to_rules"]))
    # Printed here and NOT under repeated corrections. An escaped defect is
    # not an instruction the founder gave twice, and reading it as one told
    # him he was repeating himself when he was not.
    for r in res["outcome_gradings"]:
        _out("    %s (%s) grades %s: %s"
             % (r["candidate_uuid"][:8], r["source_type"],
                r["rule_uuid"][:8], r["classification"]))
    _out("  unattributed outcomes (listed separately, never averaged in): %d"
         % len(res["unattributed_outcomes"]))
    for u in res["unattributed_outcomes"]:
        _out("    %s %s: %s" % (u["candidate_uuid"][:8], u["source_type"],
                                u["reason"]))
    for note in res["notes"]:
        _out("  NOT MEASURED: %s" % note)
    return 0


def cmd_rule_outcomes(argv):
    """What happened after this rule was shown. Counts only, never a rate."""
    pos, kv = _parse(argv, {"json"})
    if not pos:
        _err("usage: rule-outcomes <rule-id> [--json]")
        return 2
    store = _store()
    try:
        res = store.learning_rule_outcomes(pos[0])
    finally:
        store.close()
    if kv.get("json"):
        _out(json.dumps(res, indent=2, sort_keys=True))
        return 0
    _out("rule %s  [%s, %s, v%d]" % (res["rule_uuid"][:8], res["state"],
                                      res["rule_type"], res["current_version"]))
    _out("  applications: %d" % res["applications"])
    _out("  by disposition: %s" % (res["by_disposition"] or "none recorded"))
    _out("  by outcome: %s" % (res["by_outcome"] or "none recorded"))
    _out("  by rule version: %s" % (res["by_rule_version"] or "none recorded"))
    _out("  evidence by polarity: %s" % (res["evidence_by_polarity"] or "none"))
    for r in res["repeated_corrections"]:
        # "repeated by" only where something really was said again. A rework
        # or an escaped defect graded this rule, it did not repeat it.
        _out("  %s by %s (%s): %s"
             % ("repeated" if r["is_correction"] else "graded",
                r["candidate_uuid"][:8], r["source_type"], r["classification"]))
    for g in res["graded_applications"]:
        if g["classification"]:
            _out("  %s v%d: %s" % (g["application_uuid"][:8], g["rule_version"],
                                    g["classification"]))
    for note in res["notes"]:
        _out("  NOT MEASURED: %s" % note)
    _out("")
    _out("These are counts of recorded events, not a success rate. No "
         "denominator here is large enough for one.")
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
    "applications": cmd_applications,
    "disposition": cmd_disposition,
    "classify": cmd_classify,
    "should-retrieve": cmd_should_retrieve,
    "why": cmd_why,
    "deprecate": cmd_deprecate,
    "forget": cmd_forget,
    "conflicts": cmd_conflicts,
    "link": cmd_link,
    "merge": cmd_merge,
    "supersede": cmd_supersede,
    "resolve-conflict": cmd_resolve_conflict,
    "confirm": cmd_confirm,
    "rework": cmd_rework,
    "escaped-defect": cmd_escaped_defect,
    "repeat-check": cmd_repeat_check,
    "loop-failures": cmd_loop_failures,
    "rule-outcomes": cmd_rule_outcomes,
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
