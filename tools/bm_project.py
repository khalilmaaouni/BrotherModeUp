#!/usr/bin/env python3
"""bm_project.py: the mechanical command line for the seven beginner
commands (Loop 2, docs/superpowers/specs/2026-08-01-loop2-mechanical-
commands-design.md, decisions D-1 and D-4).

WHAT THIS IS
  A THIN CLI over tools/bm_store.py's Store service methods (upsert_project,
  create_task, transition_task, add_forecast, add_evidence) and its D-2 read
  accessors (get_project, list_projects, list_tasks, get_task,
  list_forecasts, latest_forecast, list_alerts, list_evidence,
  list_attribution). This file never issues SQL of its own: the flip
  condition in D-1 is exactly that, and the moment this file needs a query
  the store does not already offer, it has become a second writer and must
  be folded back into bm_store.py instead of growing one here. A structural
  guard test (tools/test_bm_project.py) greps this file's own source for
  the four SQL write and read statement keywords (case sensitive, the way
  every real query in bm_store.py itself is written) and fails the build
  if any appear.

WHAT THIS IS NOT
  Not a second store, not a second writer, not a place that reimplements
  the ten-state lifecycle law: every transition goes through
  Store.transition_task, which calls schema.transition(), which is the one
  place that law is enforced. This file only ever reports what that
  function decided, in its own words.

SUBCOMMANDS
  start                  create the project row, optional first tasks and
                          first forecast, regenerate CANVAS.md; refuses a
                          SECOND project in one root unless --allow-second
                          (see ONE PROJECT PER FOLDER below)
  status                 project, open tasks by state, latest forecast,
                          unresolved alerts (read accessors only)
  next                   the single recommended next task, with why
  task add                thin wrapper over create_task
  task start               convenience: transition a task to 'active'
  task transition          general transition, --reason required; refuses
                          exactly in schema.transition's own words (the
                          state named 'done' is refused by name)
  review <task_id>        records evidence and transitions the task, in
                          ONE atomic Store.review_task call (C1, release-
                          closure loop2 refuter fixes): a transition the
                          ten-state law refuses leaves no evidence behind
                          either
  deliver                 generate DELIVERY-PACKET.md from rows; refuses
                          a project with zero tasks outright, and refuses
                          when any task is short of the terminal state
                          ('closed') unless --partial

WHY create=False EVERYWHERE
  Matching bm_store.py's own CLI convention (its cmd_claim and every other
  command besides init): "only init creates a store" only means something
  if every other path refuses instead of quietly creating one. Run
  `python3 tools/bm_store.py init` first.

ONE PROJECT PER FOLDER (the beginner model; C5, release-closure loop2
refuter fixes)
  A root holds ONE project's CANVAS.md and ONE DELIVERY-PACKET.md by
  default: that is the beginner model this whole file is built around, and
  it is also what keeps those two generated views unambiguous (start and
  deliver regenerate them from "the project in this root", not from a
  project_id a founder has to remember to keep straight). `start` refuses
  to create a SECOND, different project_id in a root that already holds
  one, naming the existing project id in its refusal, unless
  --allow-second is passed on purpose. Re-running `start` on the SAME
  project_id (an update) is never a "second project" and is never
  refused. Once a root genuinely holds more than one project,
  _canvas_filename/_packet_filename switch every further start/deliver in
  that root to a project-scoped name (CANVAS-<project_id>.md,
  DELIVERY-PACKET-<project_id>.md) so a second project's generated views
  can never silently overwrite the first's.

RAW LOCAL DISPLAY VERSUS REDACTED EXPORT (loop2 redaction-policy fix)
  The D-2 accessors redact through the SAME export_column policy dump()
  uses, and _DUMP_SAFE_COLUMNS in bm_store.py now lists identifiers,
  schema enums, timestamps and other machine labels for the schema-12
  tables (projects, tasks, forecasts, dependencies, attribution, alerts,
  evidence, runtime_runs), the same discipline every other exported table
  already had. Every founder-typed prose column (name, title, goal,
  message, reason, note, and the rest) still stays withheld by default:
  that part of the policy is unchanged and is not what this file works
  around.

  What this file adds is WHERE raw=True is used. Human-readable terminal
  output (status, next, review, deliver) and the two generated documents
  (CANVAS.md, DELIVERY-PACKET.md) all read through the accessors with
  raw=True: local display and a locally generated document for the data's
  own owner are not an export, so there is nothing to withhold from the
  founder reading their own project on their own machine. --json output is
  the actual export surface and stays REDACTED BY DEFAULT, exactly like
  bm_store.py's own dump; pass --raw to see it unredacted, the same named,
  explicit escape hatch dump --raw already uses. Generated documents still
  pass through bs.write_generated_document before they touch disk, whose
  redact_text funnel is the FINAL guard: raw=True decides what this file
  is willing to try to show, redact_text decides what a secret-shaped
  string is allowed to survive as, and the two are independent layers on
  purpose (a task title that happens to contain something secret-shaped is
  still caught there even though raw=True populated the content).

Python 3.9, standard library only. No network. No subprocess.

No em or en dashes anywhere in this file, its comments, or its output.
"""

import importlib.util
import io
import json
import os
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    """Load a sibling module by PATH, the exact technique tools/bm_learn.py
    uses for bm_store.py: this file is invoked from arbitrary working
    directories and must not depend on whatever sys.path the caller
    happened to have."""
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(HERE, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bs = _load("bm_store")
# THE SAME schema module OBJECT bm_store.py's own service methods raise
# against, not a second independent load of brotherme/core/schema.py.
# importlib.util.module_from_spec + exec_module never registers a module
# under sys.modules on its own, so two independent loads of the identical
# file produce two DIFFERENT SchemaError classes with the same name; an
# `except S.SchemaError` written against a second load would never catch
# what Store.transition_task actually raises (isinstance/except match by
# class identity, not by name). bs._schema() is bm_store.py's own cached
# loader (it is what every one of its Store methods calls S = _schema()
# against), so reusing it here is the only way this file's exception
# handling and this file's S.STATES stay the exact same objects the store
# itself uses. Confirmed by reproduction: an independent second load let
# `task transition ... --to done` raise past main()'s handler entirely.
S = bs._schema()

# The one place "finished for good" is named in this codebase (schema.py's
# own transition() error text says "(none, terminal)" for exactly this
# state, and only this state: it is the sole entry in LEGAL_TRANSITIONS
# whose tuple is empty). deliver's non-terminal check reuses that same,
# single definition of "done" rather than inventing a second one.
TERMINAL_STATE = "closed"

# No enum constrains Task.priority (schema.py carries no ENUMS entry for
# it); this is a judgment call, documented here rather than silently
# assumed. Known words rank in the order a founder would expect; anything
# else (a number, empty, a withheld marker) sorts after all of them and
# ties are broken alphabetically for a deterministic, repeatable order.
_PRIORITY_RANK = {"critical": 0, "high": 1, "medium": 2, "normal": 2, "low": 3}


def _priority_key(value):
    v = (value or "").strip().lower()
    return (_PRIORITY_RANK.get(v, 99), v)


def _out(msg=""):
    sys.stdout.write("%s\n" % msg)


def _err(msg):
    sys.stderr.write("%s\n" % msg)


def _root():
    root, _source = bs.require_root()
    return root


def _store():
    # Matching bm_store.py's own CLI convention (its cmd_claim and every
    # command besides init): only `bm_store.py init` may pass create=True.
    # Every command here refuses 'no-store' instead, naming the fix.
    return bs.Store(_root(), create=False)


def _parse(argv, known, wants_value=()):
    """Flags into (positional, kv), refusing anything unrecognized. The
    same shape tools/bm_learn.py's own _parse uses, copied rather than
    imported (bm_learn.py is a sibling CLI, not a library this file should
    depend on for its own argument handling)."""
    positional, kv, i = [], {}, 0
    while i < len(argv):
        tok = argv[i]
        if tok.startswith("--"):
            name = tok[2:]
            if name not in known:
                _err("bm_project: unrecognized flag --%s (recognized: %s)"
                     % (name, ", ".join("--" + k for k in sorted(known))))
                sys.exit(2)
            if name in wants_value:
                if i + 1 >= len(argv):
                    _err("bm_project: --%s needs a value" % name)
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


def _csv(value):
    """'a, b ,c' -> ['a', 'b', 'c']. None or '' -> []."""
    if not value:
        return []
    return [p.strip() for p in value.split(",") if p.strip()]


def _require(kv, name, usage):
    val = kv.get(name)
    if not val:
        _err(usage)
        _err("bm_project: --%s is required" % name)
        sys.exit(2)
    return val


def _actor(kv, usage):
    """Build the actor dict every mutating subcommand passes to the store,
    so attribution is a real record of who or what acted, not a guess.
    actor_type is restricted to human|model on this CLI's own surface
    (schema.py's AttributionEvent also allows hook|automation, but this
    tool is invoked directly by a person or by a model runtime, never as a
    hook); actor_name has no sensible default, so it is required."""
    actor_type = kv.get("actor-type", "model")
    if actor_type not in ("human", "model"):
        _err(usage)
        _err("bm_project: --actor-type must be 'human' or 'model', got %r"
             % actor_type)
        sys.exit(2)
    actor_name = _require(kv, "actor-name", usage)
    # A fresh, unguessable id per process when --session-id is omitted,
    # matching bm_store.py's own _default_cli_session_id() (GATE 3: two
    # independent invocations that both omitted it must never collide on
    # an empty string). Inlined rather than calling that private function
    # across the module boundary; the shape is a one-liner.
    session_id = kv.get("session-id") or ("cli-" + uuid.uuid4().hex)
    return {"actor_type": actor_type, "actor_name": actor_name,
            "session_id": session_id}


_ACTOR_FLAGS = ("actor-type", "actor-name", "session-id")


def _print_json(obj):
    _out(json.dumps(obj, indent=2, sort_keys=True))


# ---------------------------------------------------------------------------
# Generated-view marker splice (D-3: "marker comments like STATE.md uses").
# This mirrors bm_store.py's write_state_view technique (BEGIN/END markers,
# refuse on a damaged marker pair, splice the generated block back in place,
# preserve any human prose outside the markers verbatim), through the same
# public file funnel bm_docs.py and bm_packs.py already use
# (bs.write_generated_document), rather than reinventing atomic-write or
# reaching into bm_store's private _write_generated_file. It does not
# reproduce write_state_view's STATE.md.bak-* backup rotation: that is a
# disclosed simplification (see this file's own module docstring / this
# work package's return), not an oversight.
# ---------------------------------------------------------------------------

def _splice_generated(existing_text, generated_block, begin, end):
    """Return the full file text with `generated_block` (a string that
    itself starts with `begin`, ends with `end`, and carries NO trailing
    newline of its own) spliced between the markers in `existing_text`,
    preserving everything outside them, INCLUDING whatever whitespace
    followed the old END marker. Refuses (raises bs.OwnershipRefused) on a
    damaged marker pair (found counts other than (0, 0) or (1, 1)), the
    identical GATE A rule write_state_view enforces, so a corrupted file
    is never guessed at.

    D-4 requires this to regenerate byte-stable from the same rows, which
    means it must be a FIXED POINT: splicing the identical block into its
    own prior output must reproduce that output exactly, not grow it.
    generated_block deliberately carries no trailing newline so that,
    once spliced, the ONE trailing newline in the file is the `post` text
    already captured from the existing file, never a second one stacked
    on top of it. (An earlier version appended a trailing newline to
    generated_block AND kept the file's own trailing newline in `post`,
    so every re-splice into an already-spliced file grew one more blank
    line forever; reproduced directly against bm_store.py's own
    write_state_view too, which carries the identical pattern; that one
    is outside this file's allowed set and is reported, not patched,
    here.)"""
    begin_count = existing_text.count(begin)
    end_count = existing_text.count(end)
    if (begin_count, end_count) not in ((0, 0), (1, 1)):
        raise bs.OwnershipRefused(
            "view-markers-damaged",
            "the generated file has a damaged marker pair (found %d BEGIN "
            "marker(s) and %d END marker(s); a healthy file has exactly "
            "one of each, or neither). Refusing to write it: repair by "
            "hand so there is exactly one '%s' line followed by exactly "
            "one '%s' line, or remove both and let this command add a "
            "fresh block. Nothing was changed."
            % (begin_count, end_count, begin, end))
    if begin_count == 1:
        pre, rest = existing_text.split(begin, 1)
        _mid, post = rest.split(end, 1)
        return pre + generated_block + post
    if existing_text:
        sep = "" if existing_text.endswith("\n\n") else (
            "\n" if existing_text.endswith("\n") else "\n\n")
        return existing_text + sep + generated_block + "\n"
    return generated_block + "\n"


def _write_generated(root, filename, generated_block, begin, end):
    """Read `filename` under `root` if present, splice `generated_block` in
    between the markers, and write it back through the shared file funnel.
    Advisory: a RedactionUnavailable from the write funnel is reported on
    stderr but never raised past this point, matching bm_store.py's own
    _refresh_state_view policy ("the mutation this call follows has
    already committed by the time this runs; a view-refresh failure must
    never be reported as though the mutation itself failed"). A damaged
    marker pair (bs.OwnershipRefused) is reported the same way: the row
    data is safe in the store either way, and re-running any mutating
    command tries the regeneration again."""
    path = bs.safe_project_path(root, filename)
    try:
        with io.open(path, encoding="utf-8", errors="replace") as fh:
            existing = fh.read()
    except OSError:
        existing = ""
    try:
        new_text = _splice_generated(existing, generated_block, begin, end)
        bs.write_generated_document(path, new_text)
    except bs.RedactionUnavailable as e:
        _err("bm_project: could not regenerate %s (%s); the command above "
             "still committed. Fix the redactor, then re-run any mutating "
             "command to regenerate it." % (filename, e))
    except bs.OwnershipRefused as e:
        _err("bm_project: could not regenerate %s (%s: %s); the command "
             "above still committed." % (filename, e.reason, e))


CANVAS_BEGIN = "<!-- BEGIN GENERATED BROTHERMODE CANVAS (edit outside these markers only) -->"
CANVAS_END = "<!-- END GENERATED BROTHERMODE CANVAS -->"
DELIVERY_BEGIN = "<!-- BEGIN GENERATED BROTHERMODE DELIVERY PACKET (edit outside these markers only) -->"
DELIVERY_END = "<!-- END GENERATED BROTHERMODE DELIVERY PACKET -->"


def _canvas_filename(store, project_id):
    """CANVAS.md, unless the store holds more than one project (C5,
    release-closure loop2 refuter fixes). This file's own module
    docstring documents the beginner model as ONE PROJECT PER FOLDER, so
    the plain name is what every ordinary caller sees. The moment a
    second project exists (only reachable through `start
    --allow-second`), a shared, plain CANVAS.md would silently belong to
    whichever project last ran a mutating command, so every project gets
    its own file from that point on."""
    if len(store.list_projects()) > 1:
        return "CANVAS-%s.md" % project_id
    return "CANVAS.md"


def _packet_filename(store, project_id):
    """DELIVERY-PACKET.md, or a per-project name once a second project
    exists. Same reasoning as _canvas_filename above."""
    if len(store.list_projects()) > 1:
        return "DELIVERY-PACKET-%s.md" % project_id
    return "DELIVERY-PACKET.md"


def _fmt_list(value):
    """A LIST_FIELDS value as the accessor actually returned it: a real
    list once redaction allows it to decode, or (today, by default) the
    withheld marker string it still is when it cannot. Never assumes
    either shape."""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) if value else "(none)"
    return str(value) if value else "(none)"


def _tasks_by_state(store, project_id, raw=False):
    """{state: [task, ...]} for every one of the ten lifecycle states, in
    schema.STATES order, using ONLY list_tasks(project_id, status=state):
    one call per known state name rather than reading the (possibly
    withheld) status column back out of a generic list_tasks(project_id)
    call. This is what lets state-based logic (open-task counts, the
    'ready' pool next draws from, deliver's terminal check) stay correct
    regardless of redaction, because the state being grouped by is the
    query parameter this file already knows, never a value read back from
    a possibly-withheld column. `raw` passes straight through to
    list_tasks: True for the local-display and generated-document callers,
    False (the default) for anything building a redacted --json export."""
    return {state: store.list_tasks(project_id, status=state, raw=raw)
            for state in S.STATES}


def render_canvas(store, project_id):
    """The project canvas as a GENERATED view, built ONLY from rows read
    through the D-2 accessors, read raw=True: CANVAS.md is a document
    generated for the project's own owner, not an export (see this file's
    module docstring), and still passes through bs.write_generated_document
    before it touches disk, whose redact_text funnel is the final guard.
    Deliberately carries no timestamp of its own render time: D-4 requires
    this to regenerate byte-stable from the same rows, and a "generated at"
    line would make two back-to-back regenerations of the identical
    project differ by nothing but the clock."""
    project = store.get_project(project_id, raw=True)
    lines = [CANVAS_BEGIN, ""]
    if project is None:
        lines.append("No project %r." % project_id)
        lines.append("")
        lines.append(CANVAS_END)
        return "\n".join(lines)
    lines.append("# Project Canvas: %s" % project.get("name"))
    lines.append("")
    lines.append("project_id: %s" % project.get("project_id"))
    lines.append("status: %s" % (project.get("status") or "(none)"))
    lines.append("phase: %s" % (project.get("phase") or "(none)"))
    lines.append("")
    lines.append("## Outcome")
    lines.append(project.get("goal") or "(none)")
    lines.append("")
    lines.append("## User")
    lines.append(project.get("user_outcome") or "(none)")
    lines.append("")
    lines.append("## Included")
    lines.append(_fmt_list(project.get("scope_in")))
    lines.append("")
    lines.append("## Not included")
    lines.append(_fmt_list(project.get("scope_out")))
    lines.append("")
    lines.append("## Success checks")
    lines.append(_fmt_list(project.get("success_criteria")))
    lines.append("")
    lines.append("## Main risks")
    lines.append(_fmt_list(project.get("risks")))
    lines.append("")
    lines.append("## Tasks by state")
    by_state = _tasks_by_state(store, project_id, raw=True)
    for state in S.STATES:
        tasks = by_state[state]
        if not tasks:
            continue
        lines.append("- %s (%d):" % (state, len(tasks)))
        for t in tasks:
            lines.append("  - %s: %s" % (t.get("task_id"), t.get("title")))
    lines.append("")
    lines.append("## Latest forecast")
    forecast = store.latest_forecast(project_id, raw=True)
    if forecast is None:
        lines.append("(none yet)")
    else:
        lines.append(
            "%s to %s, confidence %s (assumptions: %s)"
            % (forecast.get("minimum_duration") or "?",
               forecast.get("maximum_duration") or "?",
               forecast.get("confidence"),
               _fmt_list(forecast.get("assumptions"))))
    lines.append("")
    lines.append(CANVAS_END)
    return "\n".join(lines)


def render_delivery_packet(store, project_id):
    """The delivery packet as a GENERATED view: project, tasks with their
    evidence, forecasts, attribution summary, all from rows only, read
    raw=True for the same reason render_canvas above is: a document
    generated for the project's own owner is not an export, and still
    passes through bs.write_generated_document's redact_text funnel as the
    final guard before it touches disk."""
    project = store.get_project(project_id, raw=True)
    lines = [DELIVERY_BEGIN, ""]
    if project is None:
        lines.append("No project %r." % project_id)
        lines.append("")
        lines.append(DELIVERY_END)
        return "\n".join(lines)
    lines.append("# Delivery Packet: %s" % project.get("name"))
    lines.append("")
    lines.append("project_id: %s" % project.get("project_id"))
    lines.append("")
    lines.append("## Tasks")
    by_state = _tasks_by_state(store, project_id, raw=True)
    for state in S.STATES:
        for t in by_state[state]:
            lines.append("### %s (%s)" % (t.get("task_id"), state))
            lines.append(t.get("title") or "(no title)")
            evidence = store.list_evidence("task", t.get("task_id"), raw=True)
            if evidence:
                for ev in evidence:
                    lines.append("  - evidence %s: kind=%s ref=%s"
                                 % (ev.get("evidence_id"), ev.get("kind"),
                                    ev.get("ref")))
            else:
                lines.append("  - (no evidence recorded)")
    lines.append("")
    lines.append("## Forecasts")
    forecasts = store.list_forecasts(project_id, raw=True)
    if not forecasts:
        lines.append("(none recorded)")
    for f in forecasts:
        lines.append("- %s: confidence %s, %s to %s"
                     % (f.get("forecast_id"), f.get("confidence"),
                        f.get("minimum_duration") or "?",
                        f.get("maximum_duration") or "?"))
    lines.append("")
    lines.append("## Attribution summary")
    attributions = store.list_attribution(project_id, limit=50, raw=True)
    if not attributions:
        lines.append("(none recorded)")
    for a in attributions:
        lines.append("- %s: %s by %s (%s)"
                     % (a.get("timestamp"), a.get("event_type"),
                        a.get("actor_name"), a.get("actor_type")))
    lines.append("")
    lines.append(DELIVERY_END)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# start
# ---------------------------------------------------------------------------

_START_FLAGS = (
    "project-id", "name", "goal", "user-outcome", "project-type",
    "primary-persona", "experience-level", "status", "phase", "scope-in",
    "scope-out", "success-criteria", "assumptions", "unknowns", "risks",
    "json", "out-json", "allow-second") + _ACTOR_FLAGS


def _start_usage():
    return ("usage: start --project-id ID --name NAME [--goal G] "
            "[--user-outcome U] [--project-type T] [--primary-persona P] "
            "[--experience-level E] [--status S] [--phase PH] "
            "[--scope-in a,b] [--scope-out a,b] [--success-criteria a,b] "
            "[--assumptions a,b] [--unknowns a,b] [--risks a,b] "
            "[--json PATH] [--actor-type human|model] --actor-name NAME "
            "[--session-id SID] [--out-json] [--allow-second]")


def cmd_start(argv):
    _pos, kv = _parse(argv, _START_FLAGS, wants_value=(
        "project-id", "name", "goal", "user-outcome", "project-type",
        "primary-persona", "experience-level", "status", "phase",
        "scope-in", "scope-out", "success-criteria", "assumptions",
        "unknowns", "risks", "json") + _ACTOR_FLAGS)
    usage = _start_usage()
    project_id = _require(kv, "project-id", usage)
    name = _require(kv, "name", usage)
    actor = _actor(kv, usage)
    payload = {}
    if kv.get("json"):
        try:
            with io.open(kv["json"], encoding="utf-8") as fh:
                payload = json.load(fh)
        except (OSError, ValueError) as e:
            _err("bm_project: could not read --json payload %r: %s"
                 % (kv["json"], e))
            return 2
        if not isinstance(payload, dict):
            _err("bm_project: --json payload must be a JSON object")
            return 2
    now = bs.now_iso()
    project = dict(payload.get("project") or {})
    project.update({"project_id": project_id, "name": name,
                    "created_at": now, "updated_at": now})
    for flag, field in (
            ("goal", "goal"), ("user-outcome", "user_outcome"),
            ("project-type", "project_type"),
            ("primary-persona", "primary_persona"),
            ("experience-level", "experience_level"),
            ("status", "status"), ("phase", "phase")):
        if kv.get(flag):
            project[field] = kv[flag]
    for flag, field in (
            ("scope-in", "scope_in"), ("scope-out", "scope_out"),
            ("success-criteria", "success_criteria"),
            ("assumptions", "assumptions"), ("unknowns", "unknowns"),
            ("risks", "risks")):
        if kv.get(flag):
            project[field] = _csv(kv[flag])
    store = _store()
    try:
        # C5 (release-closure loop2 refuter fixes): one project per root
        # is the beginner model (see this file's own module docstring).
        # Two DIFFERENT projects sharing a root would each regenerate the
        # same CANVAS.md / DELIVERY-PACKET.md in turn, silently belonging
        # to whichever project last ran a mutating command. Re-running
        # start on the SAME project_id (an update) is not a second
        # project and is never refused here.
        others = [p for p in store.list_projects()
                  if p.get("project_id") != project_id]
        if others and not kv.get("allow-second"):
            _err("cannot start project %r: this store already holds "
                 "project %r; pass --allow-second to add a second "
                 "project on purpose (the beginner model is one project "
                 "per folder)."
                 % (project_id, others[0].get("project_id")))
            return 1
        store.upsert_project(project, actor)
        task_ids = []
        for task in payload.get("tasks") or []:
            t = dict(task)
            t.setdefault("task_id", uuid.uuid4().hex)
            t.setdefault("project_id", project_id)
            t.setdefault("status", "planned")
            store.create_task(t, actor)
            task_ids.append(t["task_id"])
        forecast_id = None
        if payload.get("forecast"):
            f = dict(payload["forecast"])
            f.setdefault("forecast_id", uuid.uuid4().hex)
            f.setdefault("project_id", project_id)
            f.setdefault("confidence", "medium")
            f.setdefault("created_at", now)
            store.add_forecast(f, actor)
            forecast_id = f["forecast_id"]
        _write_generated(_root(), _canvas_filename(store, project_id),
                         render_canvas(store, project_id),
                         CANVAS_BEGIN, CANVAS_END)
    finally:
        store.close()
    if kv.get("out-json"):
        _print_json({"project_id": project_id, "task_ids": task_ids,
                     "forecast_id": forecast_id})
        return 0
    _out("started project %s (%d task(s), %s)"
         % (project_id, len(task_ids),
            "1 forecast" if forecast_id else "no forecast"))
    return 0


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

def cmd_status(argv):
    _pos, kv = _parse(argv, ("project-id", "json", "raw"),
                       wants_value=("project-id",))
    usage = "usage: status --project-id ID [--json] [--raw]"
    project_id = _require(kv, "project-id", usage)
    # Text output is local display (raw=True, always: see the module
    # docstring). --json is the export surface and stays redacted unless
    # --raw is also given, exactly like bm_store.py's own dump --raw.
    want_raw = True if not kv.get("json") else bool(kv.get("raw"))
    store = _store()
    try:
        project = store.get_project(project_id, raw=want_raw)
        if project is None:
            _err("bm_project: no project %r" % project_id)
            return 1
        by_state = _tasks_by_state(store, project_id, raw=want_raw)
        forecast = store.latest_forecast(project_id, raw=want_raw)
        alerts = store.list_alerts(resolved=False, raw=want_raw)
    finally:
        store.close()
    if kv.get("json"):
        _print_json({
            "project": project,
            "tasks_by_state": by_state,
            "latest_forecast": forecast,
            "unresolved_alerts": alerts,
        })
        return 0
    _out("project %s: %s" % (project.get("project_id"), project.get("name")))
    _out("status=%s phase=%s" % (project.get("status") or "(none)",
                                 project.get("phase") or "(none)"))
    _out("open tasks by state:")
    open_total = 0
    for state in S.STATES:
        if state == TERMINAL_STATE:
            continue
        n = len(by_state[state])
        if n:
            _out("  %s: %d" % (state, n))
            open_total += n
    if not open_total:
        _out("  (none open)")
    closed = len(by_state[TERMINAL_STATE])
    if closed:
        _out("closed: %d" % closed)
    if forecast is None:
        _out("latest forecast: (none)")
    else:
        _out("latest forecast: %s, confidence %s"
             % (forecast.get("forecast_id"), forecast.get("confidence")))
    _out("unresolved alerts (store-wide; alerts carry no project_id): %d"
         % len(alerts))
    for a in alerts:
        _out("  - %s [%s] %s" % (a.get("alert_id"), a.get("severity"),
                                 a.get("message")))
    return 0


# ---------------------------------------------------------------------------
# next
# ---------------------------------------------------------------------------

def cmd_next(argv):
    _pos, kv = _parse(argv, ("project-id", "json", "raw"),
                       wants_value=("project-id",))
    usage = "usage: next --project-id ID [--json] [--raw]"
    project_id = _require(kv, "project-id", usage)
    # Same raw/json split cmd_status uses: text output is local display
    # (always raw=True); --json is the export surface and stays redacted
    # unless --raw is also given. See this file's module docstring.
    want_raw = True if not kv.get("json") else bool(kv.get("raw"))
    store = _store()
    try:
        # 'ready' means, in the canonical protocol's own words (section 1,
        # state 2), "everything the task depends on is satisfied; it can be
        # picked up." Filtering on that state via the query parameter (not
        # by reading depends_on or status back out of a row) is what keeps
        # this correct regardless of redaction.
        candidates = store.list_tasks(project_id, status="ready", raw=want_raw)
    finally:
        store.close()
    # C6 (release-closure loop2 refuter fixes): tasks carry no created_at,
    # so "earliest created" was never a real comparison this code could
    # make -- it was task_id order, a random hex uuid with no relationship
    # to when the task was added. list_tasks itself now orders by sqlite's
    # own rowid (insertion order, see its docstring), and Python's sorted()
    # is stable, so ties below keep that insertion order: the tie break
    # actually performed is "priority, then whichever was added first",
    # which is exactly what the WHY text below now says.
    ranked = sorted(candidates, key=lambda t: _priority_key(t.get("priority")))
    picked = ranked[0] if ranked else None
    if kv.get("json"):
        _print_json({"candidate_count": len(candidates), "picked": picked})
        return 0
    if picked is None:
        _out("no recommended next task: 0 task(s) currently in state "
             "'ready' for project %s" % project_id)
        return 0
    _out("next: %s - %s" % (picked.get("task_id"), picked.get("title")))
    _out("WHY: %d candidate(s) in state 'ready' (dependency-satisfied per "
         "the protocol's own definition of that state); picked by highest "
         "priority, then whichever was added first, as the tie break."
         % len(candidates))
    return 0


# ---------------------------------------------------------------------------
# task add / task start / task transition
# ---------------------------------------------------------------------------

_TASK_ADD_FLAGS = (
    "project-id", "task-id", "title", "user-value", "reason", "priority",
    "depends-on", "status", "assigned-human", "assigned-runtime",
    "assigned-model-profile", "assignment-reason", "json",
    "out-json") + _ACTOR_FLAGS


def _task_add_usage():
    return ("usage: task add --project-id ID --title T [--task-id ID] "
            "[--user-value V] [--reason R] [--priority P] "
            "[--depends-on id,id] [--status S(default planned)] "
            "[--assigned-human H] [--assigned-runtime R] "
            "[--assigned-model-profile M] [--assignment-reason R] "
            "[--json PATH] [--actor-type human|model] --actor-name NAME "
            "[--session-id SID] [--out-json]")


def cmd_task_add(argv):
    _pos, kv = _parse(argv, _TASK_ADD_FLAGS, wants_value=(
        "project-id", "task-id", "title", "user-value", "reason",
        "priority", "depends-on", "status", "assigned-human",
        "assigned-runtime", "assigned-model-profile", "assignment-reason",
        "json") + _ACTOR_FLAGS)
    usage = _task_add_usage()
    project_id = _require(kv, "project-id", usage)
    actor = _actor(kv, usage)
    task = {}
    if kv.get("json"):
        try:
            with io.open(kv["json"], encoding="utf-8") as fh:
                task = json.load(fh)
        except (OSError, ValueError) as e:
            _err("bm_project: could not read --json payload %r: %s"
                 % (kv["json"], e))
            return 2
        if not isinstance(task, dict):
            _err("bm_project: --json payload must be a JSON object")
            return 2
        task = dict(task)
    title = kv.get("title") or task.get("title")
    if not title:
        _err(usage)
        _err("bm_project: --title is required (or provide it via --json)")
        return 2
    task["title"] = title
    task["project_id"] = project_id
    task.setdefault("task_id", kv.get("task-id") or uuid.uuid4().hex)
    task["status"] = kv.get("status") or task.get("status") or "planned"
    for flag, field in (
            ("user-value", "user_value"), ("reason", "reason"),
            ("priority", "priority"), ("assigned-human", "assigned_human"),
            ("assigned-runtime", "assigned_runtime"),
            ("assigned-model-profile", "assigned_model_profile"),
            ("assignment-reason", "assignment_reason")):
        if kv.get(flag):
            task[field] = kv[flag]
    if kv.get("depends-on"):
        task["depends_on"] = _csv(kv["depends-on"])
    store = _store()
    try:
        task_id = store.create_task(task, actor)
    finally:
        store.close()
    if kv.get("out-json"):
        _print_json({"task_id": task_id})
        return 0
    _out("added task %s" % task_id)
    return 0


_TASK_TRANSITION_FLAGS = ("task-id", "to", "reason", "json",
                          "out-json") + _ACTOR_FLAGS


def cmd_task_transition(argv):
    _pos, kv = _parse(argv, _TASK_TRANSITION_FLAGS, wants_value=(
        "task-id", "to", "reason") + _ACTOR_FLAGS)
    usage = ("usage: task transition --task-id ID --to STATE --reason R "
             "[--actor-type human|model] --actor-name NAME "
             "[--session-id SID] [--out-json]")
    task_id = _require(kv, "task-id", usage)
    new_status = _require(kv, "to", usage)
    reason = _require(kv, "reason", usage)
    actor = _actor(kv, usage)
    store = _store()
    try:
        status = store.transition_task(task_id, new_status, reason, actor)
    finally:
        store.close()
    if kv.get("out-json"):
        _print_json({"task_id": task_id, "status": status})
        return 0
    _out("task %s -> %s" % (task_id, status))
    return 0


def cmd_task_start(argv):
    """Convenience sugar: begin work on a task. transition_task itself
    decides legality (ready->active or blocked->active are the only legal
    arrivals at 'active'); this wrapper only fixes the destination."""
    _pos, kv = _parse(argv, ("task-id", "reason", "out-json") + _ACTOR_FLAGS,
                      wants_value=("task-id", "reason") + _ACTOR_FLAGS)
    usage = ("usage: task start --task-id ID --reason R "
             "[--actor-type human|model] --actor-name NAME "
             "[--session-id SID] [--out-json]")
    task_id = _require(kv, "task-id", usage)
    reason = _require(kv, "reason", usage)
    actor = _actor(kv, usage)
    store = _store()
    try:
        status = store.transition_task(task_id, "active", reason, actor)
    finally:
        store.close()
    if kv.get("out-json"):
        _print_json({"task_id": task_id, "status": status})
        return 0
    _out("task %s -> %s" % (task_id, status))
    return 0


TASK_COMMANDS = {
    "add": cmd_task_add,
    "start": cmd_task_start,
    "transition": cmd_task_transition,
}


def cmd_task(argv):
    if not argv or argv[0] not in TASK_COMMANDS:
        _err("usage: task <add|start|transition> ... "
             "(known: %s)" % ", ".join(sorted(TASK_COMMANDS)))
        return 2
    return TASK_COMMANDS[argv[0]](argv[1:])


# ---------------------------------------------------------------------------
# review
# ---------------------------------------------------------------------------

_REVIEW_FLAGS = ("project-id", "kind", "ref", "note", "to", "reason",
                 "out-json") + _ACTOR_FLAGS


def cmd_review(argv):
    pos, kv = _parse(argv, _REVIEW_FLAGS, wants_value=(
        "project-id", "kind", "ref", "note", "to", "reason") + _ACTOR_FLAGS)
    usage = ("usage: review <task_id> --project-id ID [--kind K] [--ref R] "
             "[--note N] [--to STATE(default verified)] --reason R "
             "[--actor-type human|model] --actor-name NAME "
             "[--session-id SID] [--out-json]")
    if not pos:
        _err(usage)
        _err("bm_project: review needs a task id")
        return 2
    task_id = pos[0]
    project_id = _require(kv, "project-id", usage)
    reason = _require(kv, "reason", usage)
    actor = _actor(kv, usage)
    new_status = kv.get("to") or "verified"
    evidence = {
        "evidence_id": uuid.uuid4().hex,
        "subject_type": "task",
        "subject_id": task_id,
        "kind": kv.get("kind") or "",
        "ref": kv.get("ref") or "",
        "note": kv.get("note") or "",
        "created_at": bs.now_iso(),
    }
    store = _store()
    try:
        # ONE composite call (C1, release-closure loop2 refuter fixes):
        # review_task files the evidence AND runs the transition in a
        # SINGLE store transaction, so a transition schema.transition()
        # refuses leaves no orphan evidence row behind. This used to be
        # two separate calls (add_evidence, then transition_task), each
        # its own transaction, so a refused transition still left the
        # evidence from the first call sitting on disk.
        evidence_id, status = store.review_task(
            task_id, project_id, evidence, new_status, reason, actor)
    finally:
        store.close()
    if kv.get("out-json"):
        _print_json({"task_id": task_id, "evidence_id": evidence_id,
                     "status": status})
        return 0
    _out("reviewed task %s: evidence %s recorded, task -> %s"
         % (task_id, evidence_id, status))
    return 0


# ---------------------------------------------------------------------------
# deliver
# ---------------------------------------------------------------------------

def cmd_deliver(argv):
    _pos, kv = _parse(argv, ("project-id", "partial", "out-json"),
                       wants_value=("project-id",))
    usage = "usage: deliver --project-id ID [--partial] [--out-json]"
    project_id = _require(kv, "project-id", usage)
    store = _store()
    try:
        project = store.get_project(project_id)
        if project is None:
            _err("bm_project: no project %r" % project_id)
            return 1
        total = len(store.list_tasks(project_id))
        if total == 0:
            # C4 (release-closure loop2 refuter fixes): --partial means
            # "some tasks are not yet closed", not "there is nothing to
            # deliver at all". A project with zero tasks refuses either
            # way, so an empty delivery packet can never pass as a real
            # one just because --partial was on the command line.
            _err("cannot deliver %s: the project has zero tasks; add at "
                 "least one task before delivering." % project_id)
            return 1
        closed = len(store.list_tasks(project_id, status=TERMINAL_STATE))
        non_terminal = total - closed
        if non_terminal > 0 and not kv.get("partial"):
            _err("cannot deliver: %d of %d task(s) have not reached the "
                 "terminal state (%r); pass --partial to deliver anyway, "
                 "or finish those tasks first."
                 % (non_terminal, total, TERMINAL_STATE))
            return 1
        text = render_delivery_packet(store, project_id)
        _write_generated(_root(), _packet_filename(store, project_id), text,
                         DELIVERY_BEGIN, DELIVERY_END)
    finally:
        store.close()
    if kv.get("out-json"):
        _print_json({"project_id": project_id, "total_tasks": total,
                     "closed_tasks": closed, "partial": bool(non_terminal)})
        return 0
    if non_terminal:
        _out("delivered %s PARTIALLY: %d of %d task(s) not yet closed"
             % (project_id, non_terminal, total))
    else:
        _out("delivered %s: all %d task(s) closed" % (project_id, total))
    return 0


# ---------------------------------------------------------------------------
# dispatch
# ---------------------------------------------------------------------------

COMMANDS = {
    "start": cmd_start,
    "status": cmd_status,
    "next": cmd_next,
    "task": cmd_task,
    "review": cmd_review,
    "deliver": cmd_deliver,
}


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        _out(__doc__.strip())
        _out("")
        _out("commands: %s" % ", ".join(sorted(COMMANDS)))
        return 0
    cmd = argv[0]
    if cmd not in COMMANDS:
        _err("bm_project: unknown command %r (known: %s)"
             % (cmd, ", ".join(sorted(COMMANDS))))
        return 2
    try:
        return COMMANDS[cmd](argv[1:])
    except S.SchemaError as e:
        # The ten-state law refusing a move, or an invalid shape: reported
        # in schema.transition's OWN words, never restated here, and
        # counted as a refusal (exit 1), not a usage error.
        _err("bm_project: refused: %s" % e)
        return 1
    except bs.BMStoreError as e:
        # Covers OwnershipRefused and StaleIdentity: not-found, illegal
        # evidence, already-resolved, no-store, and the like.
        _err("bm_project: refused: %s" % e)
        return 1


def cli():
    """Console-script entry point; see bm_learn.py's cli() for why this
    exists beside main() rather than duplicating the sys.exit(main(...))
    line: a packaging entry point must take no arguments."""
    sys.exit(main(sys.argv[1:]))


if __name__ == "__main__":
    cli()
