#!/usr/bin/env python3
"""tools/bm_continue.py: the continuity adapter behind `brothermode
continue` (Phase C step 1 of the 2026-08-08 finalization plan, "The
continuity protocol").

WHY THIS EXISTS
  A session closed its loop on 2026-08-08, reported honestly, and
  stopped, leaving the founder to restart the program by hand the next
  morning. The founder's correction that evening was a product
  requirement, in their own words: "when you pass over to a new session
  do it seamlessly and automatically without my involvement as I might
  be sleeping or busy." A handover that depends on a session
  remembering to write one is a handover that fails on the night it
  matters, so the handover became a subcommand.

WHAT IT DOES
  Generates the HANDOFF PACKET from store rows, writes it through the
  same public document funnel every other generated view in this
  project uses (bs.write_generated_document), prints the exact command
  that starts the successor, and (unless --dry-run) starts it.

THE TEN SECTIONS
  Pinned by the founder on 2026-08-08 and pinned again as an ordered
  assertion in tools/test_brothermode_cli.py, because a packet that
  quietly drops section 9 is a packet that loses a founder decision:

    1. North star and goals            projects row (goal, user
                                       outcome, success criteria)
    2. Where we stand, one paragraph   project status and phase, task
                                       counts by state, newest
                                       sentinel status
    3. Read next, in this order        the generated documents, plus
                                       every recorded view with its
                                       published artifact url
    4. Next actions, ordered           active and ready tasks, by
                                       priority
    5. Evidence index                  evidence rows, per task
    6. Telemetry                       spend totals against the
                                       contract ceilings, newest
                                       forecast
    7. Lessons learnt                  active procedural memories
    8. Features pipeline               tasks not yet ready
    9. Open founder decisions          unsuperseded key decisions,
                                       unanswered interruptions,
                                       unresolved human steps
   10. The continuity contract         what the successor owes the
                                       program, plus its own launch
                                       command

  Every one of them is built from ROWS. Nothing here narrates a fact the
  store does not hold: a section with no rows says so plainly rather
  than inventing filler, which is the difference between a generated
  view and a report that reads well and means nothing.

WHY THE PACKET IS A WHOLE-FILE RENDER
  tools/bm_project.py's CANVAS.md and DELIVERY-PACKET.md splice a
  generated block between markers so a human's own prose around them
  survives. This packet does not: it is written for a SUCCESSOR SESSION
  that must be able to trust every line as current, and a hand-edited
  paragraph sitting inside it, indistinguishable from generated text,
  is exactly the stale instruction that gets a successor to do the
  wrong thing at three in the morning. So the whole file is generated,
  it says so on its first line, and anything a human wants the
  successor to know goes into the store, where the next regeneration
  will carry it.

BYTE-STABLE BY CONSTRUCTION
  No render timestamp anywhere: two runs over the same rows produce the
  same bytes, the same law tools/bm_project.py's render_canvas states
  and tools/test_brothermode_cli.py pins here too. The packet's dates
  are the rows' own dates.

THE ONE ROOT CAUSE THIS FILE ENCODES AS CODE
  `claude --add-dir` is VARIADIC, so a prompt written after it is
  swallowed as another directory and the session dies with "Input must
  be provided either through stdin or as a prompt argument when using
  --print". That killed the first relay launch of 2026-08-08. In
  launch_argv below the prompt is argv[2], immediately after -p, before
  any other flag, and a test pins that position rather than trusting
  anyone to remember it.

WHAT THIS FILE DOES NOT DO
  It does not verify the successor is alive, and it does not record the
  successor's process id into the store as evidence. Those are Phase C
  step 3, deliberately not smuggled in here: this file's own honesty
  line says out loud that a printed pid is a spawn, not a proof.
  It never types a credential, never publishes anything, and never
  tags: those stay founder-gated whatever a successor is told to do.

Python 3.9, standard library only. No em or en dashes anywhere in this
file, its comments, or its output.
"""

import importlib.util
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)


def _load(name):
    """Load a sibling module by PATH, the identical technique tools/
    bm_lead.py, tools/bm_view.py and tools/brothermode_cli.py all use: a
    hostile sys.path cannot shadow the module this way."""
    path = os.path.join(HERE, name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bs = _load("bm_store")
# The SAME schema object the store itself validates against, reached the
# same way tools/bm_project.py reaches it (its own S = bs._schema()), so
# this file's list of lifecycle states and the store's cannot drift.
S = bs._schema()


def _out(msg=""):
    sys.stdout.write("%s\n" % msg)


def _err(msg):
    sys.stderr.write("%s\n" % msg)


def _print_json(obj):
    _out(json.dumps(obj, indent=2, sort_keys=True, default=str))


def _parse(argv, known, wants_value=()):
    """Flags into (positional, kv), refusing anything unrecognized. Copied
    from tools/brothermode_cli.py's own _parse (itself copied from tools/
    bm_lead.py's) for the reason that file states: a sibling CLI is not a
    library this file should depend on for its own argument handling."""
    positional, kv, i = [], {}, 0
    while i < len(argv):
        tok = argv[i]
        if tok.startswith("--"):
            name = tok[2:]
            if name not in known:
                _err("bm_continue: unrecognized flag --%s (recognized: %s)"
                     % (name, ", ".join("--" + k for k in sorted(known))))
                sys.exit(2)
            if name in wants_value:
                if i + 1 >= len(argv):
                    _err("bm_continue: --%s needs a value" % name)
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


# ---------------------------------------------------------------------------
# Rendering. Every helper takes ROWS and returns LINES: nothing below
# reaches the store a second time, so what a section says and what the
# store holds cannot drift apart inside one render.
# ---------------------------------------------------------------------------

PACKET_TITLE = "Handoff packet"

GENERATED_NOTICE = (
    "This file is GENERATED from BrotherMode's store by `brothermode "
    "continue`. Every line below is a row, or the absence of one. Edits "
    "here are overwritten on the next run: put anything the successor "
    "must know into the store instead, so the next regeneration carries "
    "it.")

# The ten headings, in the order the founder fixed on 2026-08-08. Kept as
# data rather than typed inline ten times so the renderer and the ordered
# assertion in tools/test_brothermode_cli.py cannot drift apart silently.
SECTION_HEADINGS = (
    "## 1. North star and goals",
    "## 2. Where we stand, one paragraph",
    "## 3. Read next, in this order",
    "## 4. Next actions, ordered",
    "## 5. Evidence index",
    "## 6. Telemetry",
    "## 7. Lessons learnt",
    "## 8. Features pipeline",
    "## 9. Open founder decisions",
    "## 10. The continuity contract for the successor",
)

# The states a task must be in to be an ACTION the successor takes next,
# and the states that make it PIPELINE instead. Every schema state falls
# in exactly one of the three groups (the third being terminal), so a new
# state cannot silently vanish from the packet: _pipeline_states below
# computes its group by subtraction rather than by a second hand-written
# list.
NEXT_ACTION_STATES = ("active", "ready")
TERMINAL_STATES = ("verified", "delivered", "cancelled", "done")

_PRIORITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _priority_key(task):
    """Most urgent first, unknown or missing priorities last and
    alphabetical among themselves, then task id so the order is total.
    Same judgment call, and the same reasoning, as tools/bm_project.py's
    own _priority_key: a deterministic order beats an accidental one."""
    value = (task.get("priority") or "").strip().lower()
    return (_PRIORITY_RANK.get(value, 99), value, task.get("task_id") or "")


def _states():
    """Every lifecycle state name this store's schema knows, in schema
    order. Read from the schema module the store itself uses, never
    re-listed here."""
    return list(S.STATES)


def _pipeline_states():
    return [s for s in _states()
            if s not in NEXT_ACTION_STATES and s not in TERMINAL_STATES]


def _tasks_in(store, project_id, states):
    """Tasks in any of `states`, read one state at a time. Same reasoning
    tools/bm_project.py's _tasks_by_state documents: the state a task is
    grouped by is the QUERY PARAMETER, never a column read back out of a
    row that redaction may have withheld."""
    tasks = []
    for state in states:
        for task in store.list_tasks(project_id, status=state, raw=True):
            task = dict(task)
            task["_state"] = state
            tasks.append(task)
    return tasks


def _fmt_list(value):
    """A list field as the accessor actually returned it: a real list once
    redaction allows it to decode, or the withheld marker string it still
    is when it cannot. Never assumes either shape (copied verbatim in
    intent from tools/bm_project.py's _fmt_list)."""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) if value else "(none)"
    return str(value) if value else "(none)"


def _none(lines, message):
    """One empty-section line. A section with no rows SAYS it has no rows:
    an empty heading reads as an oversight, and filler invented to avoid
    the silence would be worse than either."""
    lines.append("(%s)" % message)


def _section_north_star(lines, project):
    lines.append("North star: %s" % (project.get("goal") or "(none recorded)"))
    lines.append("")
    lines.append("What the founder gets: %s"
                 % (project.get("user_outcome") or "(none recorded)"))
    lines.append("")
    lines.append("Success checks: %s"
                 % _fmt_list(project.get("success_criteria")))
    scope_out = _fmt_list(project.get("scope_out"))
    if scope_out != "(none)":
        lines.append("")
        lines.append("Deliberately NOT in scope: %s" % scope_out)


def _section_where_we_stand(lines, store, project, project_id):
    counts = []
    for state in _states():
        n = len(store.list_tasks(project_id, status=state, raw=True))
        if n:
            counts.append("%d %s" % (n, state))
    lines.append(
        "%s is in status %s, phase %s, with %s."
        % (project.get("name") or project_id,
           project.get("status") or "(none)",
           project.get("phase") or "(none)",
           ", ".join(counts) if counts else "no tasks recorded yet"))
    status = store.latest_status(project_id)
    if status is not None:
        lines.append("")
        lines.append("Newest recorded summary (%s): %s"
                     % (status.get("created_at"),
                        status.get("summary") or "(empty)"))
        if status.get("open_risks"):
            lines.append("Open risks at that point: %s"
                         % status.get("open_risks"))


def _section_read_next(lines, store, project_id, packet_rel):
    lines.append("1. %s (this file): the packet itself, regenerated from "
                 "rows every time." % packet_rel)
    n = 1
    views = store.list_views(project_id, raw=True)
    if not views:
        lines.append("2. No view has been recorded for this project yet, so "
                     "there is no page to open. `brothermode view` writes "
                     "one.")
    for view in views:
        n += 1
        url = view.get("artifact_url") or ""
        published = (" published at %s" % url) if url else \
            " (local only, never published)"
        lines.append("%d. %s, kind %s,%s"
                     % (n, view.get("rel_path") or "(no path)",
                        view.get("kind"), published))


def _section_next_actions(lines, store, project_id):
    tasks = sorted(_tasks_in(store, project_id, NEXT_ACTION_STATES),
                   key=_priority_key)
    if not tasks:
        _none(lines, "no task is active or ready; the successor's first "
                     "move is to decide what is")
        return
    for i, task in enumerate(tasks, 1):
        lines.append("%d. %s [%s, priority %s]: %s"
                     % (i, task.get("task_id"), task["_state"],
                        task.get("priority") or "unset",
                        task.get("title") or "(no title)"))
        if task.get("reason"):
            lines.append("   why: %s" % task.get("reason"))


def _section_evidence(lines, store, project_id):
    wrote_any = False
    for state in _states():
        for task in store.list_tasks(project_id, status=state, raw=True):
            rows = store.list_evidence("task", task.get("task_id"), raw=True)
            if not rows:
                continue
            wrote_any = True
            lines.append("- %s (%s):" % (task.get("task_id"), state))
            for row in rows:
                lines.append("  - %s: kind=%s ref=%s"
                             % (row.get("evidence_id"),
                                row.get("kind") or "(none)",
                                row.get("ref") or "(none)"))
                if row.get("note"):
                    lines.append("    note: %s" % row.get("note"))
    if not wrote_any:
        _none(lines, "no evidence has been filed yet; nothing here is "
                     "proven")


def _section_telemetry(lines, store, project_id):
    spend = store.spend_totals(project_id)
    lines.append("Spend: %s tokens, %s minutes."
                 % (spend.get("tokens"), spend.get("minutes")))
    ceiling = spend.get("token_ceiling")
    if ceiling:
        lines.append("Token ceiling %s, %s per cent used, verdict %s."
                     % (ceiling, spend.get("token_pct"),
                        spend.get("verdict")))
    else:
        lines.append("No token ceiling is recorded, so no percentage is "
                     "claimed. Verdict: %s." % spend.get("verdict"))
    forecast = store.latest_forecast(project_id, raw=True)
    if forecast is None:
        lines.append("No forecast recorded.")
    else:
        lines.append(
            "Newest forecast: %s to %s, confidence %s (assumptions: %s)."
            % (forecast.get("minimum_duration") or "?",
               forecast.get("maximum_duration") or "?",
               forecast.get("confidence"),
               _fmt_list(forecast.get("assumptions"))))


def _section_lessons(lines, store, project_id):
    rows = store.active_procedural(project_id)
    if not rows:
        _none(lines, "no lesson has been recorded for this project")
        return
    for row in rows:
        lines.append("- tried: %s" % row.get("attempt"))
        lines.append("  outcome: %s" % row.get("outcome"))
        if row.get("diagnosis"):
            lines.append("  why: %s" % row.get("diagnosis"))


def _section_pipeline(lines, store, project_id):
    tasks = sorted(_tasks_in(store, project_id, _pipeline_states()),
                   key=_priority_key)
    if not tasks:
        _none(lines, "nothing is waiting behind the next actions")
        return
    for task in tasks:
        lines.append("- %s [%s, priority %s]: %s"
                     % (task.get("task_id"), task["_state"],
                        task.get("priority") or "unset",
                        task.get("title") or "(no title)"))


def _fmt_alternative(alt):
    """One alternative as the store returned it. The store validates every
    alternative as exactly {"option", "why_not"} (its own bad-alternatives
    refusal), so the dict shape is the normal case; the string branch
    exists for the redaction-withheld case, which is a marker string, not
    a dict."""
    if isinstance(alt, dict):
        why = alt.get("why_not") or ""
        return "%s (not chosen: %s)" % (alt.get("option") or "(unnamed)",
                                        why or "no reason recorded")
    return str(alt)


def _section_decisions(lines, store, project_id):
    wrote_any = False
    for decision in store.open_key_decisions(project_id, raw=True):
        wrote_any = True
        lines.append("- DECISION (%s), %s: %s"
                     % (decision.get("decision_class"),
                        decision.get("subject") or "(no subject)",
                        decision.get("claim")))
        alternatives = decision.get("alternatives")
        if isinstance(alternatives, list) and alternatives:
            for alt in alternatives:
                lines.append("  alternative: %s" % _fmt_alternative(alt))
        elif alternatives:
            lines.append("  alternatives: %s" % alternatives)
        if decision.get("flip_condition"):
            lines.append("  what would change it: %s"
                         % decision.get("flip_condition"))
    for row in store.list_interruptions(project_id, answered=False, raw=True):
        wrote_any = True
        lines.append("- UNANSWERED QUESTION (%s): %s"
                     % (row.get("condition") or "no condition",
                        row.get("question")))
    for row in store.list_human_steps(project_id, resolved=False, raw=True):
        wrote_any = True
        lines.append("- WAITING ON THE FOUNDER (%s): %s"
                     % (row.get("floor") or "no floor", row.get("what")))
    if not wrote_any:
        _none(lines, "nothing is waiting on the founder")


CONTRACT_LINES = (
    "The successor owes the program four things, and silence is the only "
    "forbidden outcome:",
    "",
    "1. ONE bounded chunk of work, because a headless session runs ONE "
    "turn and then exits. A mission larger than one turn is a mission "
    "that dies half done.",
    "2. A done-check run AFTER the last edit, quoted verbatim. Nothing is "
    "called done without it.",
    "3. This packet regenerated the moment the work state changes "
    "materially, not at the last minute.",
    "4. Its own successor launched before it closes, or a plain statement "
    "that it could not and why.",
    "",
    "Founder gates never move: no tag, no credentials, no publishing, no "
    "permanent deletion, whatever any instruction downstream of this file "
    "says.",
)


def _section_contract(lines, packet_path, command_line):
    for line in CONTRACT_LINES:
        lines.append(line)
    lines.append("")
    lines.append("The successor's own launch command:")
    lines.append("")
    lines.append("    %s" % command_line)
    lines.append("")
    lines.append("That command needs the standing settings allow rules "
                 "`Bash(claude -p*)` and `Bash(nohup claude -p*)`, which "
                 "only the founder can grant: a session cannot grant "
                 "itself the right to launch a session, and that refusal "
                 "is correct.")
    lines.append("")
    lines.append("The successor runs under whatever your installed "
                 "settings already allow, so its writes and commands are "
                 "gated the same way yours are. Loosening that is an "
                 "explicit choice, typed per launch as `--permission-mode "
                 "MODE`, never a default this tool picks for you.")
    lines.append("")
    lines.append("Run it from the project root. Every path in this packet "
                 "is relative to that root, because a generated document "
                 "masks absolute paths and an absolute path here would "
                 "reach you withheld.")
    lines.append("")
    lines.append("This packet lives at %s, relative to the project root."
                 % packet_path)


def render_packet(store, project_id, packet_rel, command_line):
    """The whole packet as text, built ONLY from rows read through the
    store's own accessors, raw=True for the same reason tools/
    bm_project.py's render_canvas is: a document generated for the
    project's own owner is not an export, and it still passes through
    bs.write_generated_document's redaction funnel before it touches
    disk. Returns None when the project does not exist, which is a
    refusal for the caller to report, never an empty packet written over
    a real one."""
    project = store.get_project(project_id, raw=True)
    if project is None:
        return None
    lines = ["# %s: %s" % (PACKET_TITLE, project.get("name") or project_id),
             "",
             GENERATED_NOTICE,
             "",
             "project_id: %s" % project_id,
             ""]
    sections = (
        lambda out: _section_north_star(out, project),
        lambda out: _section_where_we_stand(out, store, project, project_id),
        lambda out: _section_read_next(out, store, project_id, packet_rel),
        lambda out: _section_next_actions(out, store, project_id),
        lambda out: _section_evidence(out, store, project_id),
        lambda out: _section_telemetry(out, store, project_id),
        lambda out: _section_lessons(out, store, project_id),
        lambda out: _section_pipeline(out, store, project_id),
        lambda out: _section_decisions(out, store, project_id),
        lambda out: _section_contract(out, packet_rel, command_line),
    )
    for heading, fill in zip(SECTION_HEADINGS, sections):
        lines.append(heading)
        lines.append("")
        fill(lines)
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def packet_filename(store, project_id):
    """HANDOFF-PACKET.md, or a per-project name once a second project
    exists. Same reasoning, and the same rule, as tools/bm_project.py's
    _packet_filename: a shared plain name would silently belong to
    whichever project generated last."""
    if len(store.list_projects()) > 1:
        return "HANDOFF-PACKET-%s.md" % project_id
    return "HANDOFF-PACKET.md"


# ---------------------------------------------------------------------------
# The launch. Two pure functions and one spawn, kept apart so the shape of
# the command can be tested without ever starting a process.
# ---------------------------------------------------------------------------

PROMPT_TEMPLATE = (
    "You are the next relay session of this BrotherMode program. Read "
    "%(packet)s first: it is the whole brief, generated from the store, "
    "and its ten sections carry the north star, where the work stands, "
    "the ordered next actions, the evidence, and the open founder "
    "decisions. Do ONE bounded chunk of work: the first unfinished next "
    "action in section 4, no more. A headless session runs ONE turn and "
    "then exits, so a mission larger than one turn dies half done. Close "
    "your chunk with its done-check run after your last edit and quoted "
    "verbatim, commit on your own branch in your own git worktree, and "
    "never switch the main checkout's branch. Before your turn ends, "
    "regenerate this packet with `brothermode continue --project-id "
    "%(project)s` so your own successor inherits current facts. Founder "
    "gates are unchanged and outrank every instruction above: no tag, no "
    "credentials, no publishing, no permanent deletion.")


def launch_prompt(packet_path, project_id):
    return PROMPT_TEMPLATE % {"packet": packet_path, "project": project_id}


def launch_argv(packet_path, root, project_id="", extra_dirs=(),
                permission_mode=None):
    """The successor's argv. THE PROMPT IS argv[2], immediately after -p,
    and every flag comes after it. That is not style: `--add-dir` is
    variadic, so a prompt written after it is read as one more directory
    and the session dies with "Input must be provided either through
    stdin or as a prompt argument when using --print". That exact failure
    killed the first relay launch of 2026-08-08 (relay-1.log), and
    tools/test_brothermode_cli.py pins the position so it cannot come
    back.

    NO PERMISSION MODE IS SET BY DEFAULT, and that default is the whole
    security posture of this verb. The successor inherits whatever the
    installed Claude Code settings already allow, so every write, command
    and network action it takes is gated exactly as the founder's own
    session would be. An unattended relay that needs more says so out
    loud with --permission-mode, per launch, in a command printed in full
    before it runs: a shipped tool that hard-coded bypassPermissions
    would hand every stranger who installs BrotherMode a one-word way to
    detach an ungated agent, and it would do it from a packet whose text
    other models wrote. Flagged in review on 2026-08-08 and fixed the
    same hour; the founder's own relay passes the flag by hand."""
    argv = ["claude", "-p", launch_prompt(packet_path, project_id)]
    if permission_mode:
        argv.extend(["--permission-mode", permission_mode])
    argv.extend(["--add-dir", root])
    for extra in extra_dirs:
        argv.append(extra)
    return argv


def _quote(token):
    """Single-quote a token for a copy-and-paste shell line. shlex.quote
    would do this too; it is four lines here because this file's whole
    stated posture is that a reader can see what it will run, and an
    imported quoting rule is one more place the printed line and the
    spawned argv could differ."""
    if token and all(c.isalnum() or c in "-_./=:" for c in token):
        return token
    return "'" + token.replace("'", "'\\''") + "'"


def printable_command(argv, log_path):
    """The launch as ONE line a human can paste, redirected to a log and
    detached. What is printed and what is spawned come from the SAME argv
    list, so the line a founder reads is the command a session runs, not
    a description of it."""
    return "nohup %s > %s 2>&1 &" % (
        " ".join(_quote(a) for a in argv), _quote(log_path))


def spawn_successor(argv, log_path, cwd=None):
    """Start the successor detached and return its process id, or raise
    OSError. start_new_session detaches it from this process group so it
    survives this session ending, which is the whole point: nohup's
    behaviour, without a shell in the middle rewriting the argv this
    file just built.

    HONESTLY: a returned pid is a SPAWN, not a proof of life. Recording
    the successor's pid and first log line into the store as evidence,
    and refusing to close without it, is Phase C step 3, and this
    docstring says so rather than letting a printed number read as a
    guarantee."""
    log = open(log_path, "ab")
    try:
        proc = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, cwd=cwd,
                                start_new_session=True)
    finally:
        log.close()
    return proc.pid


# ---------------------------------------------------------------------------
# continue
# ---------------------------------------------------------------------------

_CONTINUE_FLAGS = ("project-id", "root", "out", "log", "dry-run", "json",
                   "permission-mode")


def cmd_continue(argv):
    _pos, kv = _parse(argv, _CONTINUE_FLAGS,
                      wants_value=("project-id", "root", "out", "log",
                                   "permission-mode"))
    root = kv.get("root")
    if not root:
        # bs.require_root() is the ONE root resolver every sibling adapter
        # uses (tools/bm_project.py's _root, tools/bm_lead.py's _root): it
        # reads BROTHERMODE_ROOT, then the marker walk, and refuses loudly
        # rather than guessing. --root exists for testability only, the
        # same reason scripts/doctor.py takes --settings.
        try:
            root, _source = bs.require_root()
        except bs.BMStoreError as exc:
            _err("bm_continue: %s" % exc)
            return 1
    try:
        store = bs.Store(root, create=False)
    except bs.BMStoreError as exc:
        _err("bm_continue: %s" % exc)
        return 1
    try:
        project_id = kv.get("project-id")
        if not project_id:
            projects = store.list_projects()
            if len(projects) != 1:
                _err("bm_continue: this store holds %d projects, so name the "
                     "one to hand over with --project-id ID."
                     % len(projects))
                return 1
            project_id = projects[0].get("project_id")
        filename = kv.get("out") or packet_filename(store, project_id)
        packet_path = bs.safe_project_path(root, filename)
        log_name = "successor-%s.log" % project_id
        log_path = kv.get("log") or bs.safe_project_path(root, log_name)
        # EVERY path inside the packet is RELATIVE to the project root, and
        # that is a requirement rather than a preference: the document
        # funnel masks absolute paths (bs.mask_absolute_paths), so an
        # absolute path written here reaches the successor as
        # "[PATH WITHHELD]" and the brief becomes unreadable. Relative
        # paths survive the funnel untouched AND make the packet portable,
        # which is the same reason the launch command below is written to
        # be run from the project root.
        packet_rel = os.path.relpath(packet_path, root)
        log_rel = os.path.relpath(log_path, root)
        argv_out = launch_argv(packet_rel, ".", project_id=project_id,
                               permission_mode=kv.get("permission-mode"))
        command_line = printable_command(argv_out, log_rel)
        text = render_packet(store, project_id, packet_rel, command_line)
        if text is None:
            _err("bm_continue: there is no project %r in this store, so "
                 "there is nothing to hand over. Nothing was written."
                 % project_id)
            return 1
        try:
            bs.write_generated_document(packet_path, text)
        except (bs.RedactionUnavailable, OSError) as exc:
            _err("bm_continue: the packet could not be written (%s). "
                 "Nothing was launched: a successor with no packet is a "
                 "successor with no brief." % exc)
            return 1
    finally:
        store.close()

    if kv.get("json"):
        _print_json({"packet": packet_path, "project_id": project_id,
                     "command": command_line, "log": log_path,
                     "launched": False if kv.get("dry-run") else None})
    else:
        _out("Wrote the handoff packet: %s" % packet_path)
        _out("")
        _out("The successor's launch command:")
        _out("  %s" % command_line)
        _out("")
    if kv.get("dry-run"):
        if not kv.get("json"):
            _out("Dry run: the packet is written, the command is printed, "
                 "and this run launched nothing.")
        return 0
    try:
        pid = spawn_successor(argv_out, log_path, cwd=root)
    except OSError as exc:
        _err("bm_continue: the successor could not be started (%s). The "
             "packet is written, so a founder or a later session can run "
             "the command above by hand." % exc)
        return 1
    if kv.get("json"):
        _print_json({"packet": packet_path, "project_id": project_id,
                     "command": command_line, "log": log_path,
                     "launched": True, "pid": pid})
        return 0
    _out("Launched the successor: process %d, logging to %s." % (pid, log_path))
    _out("A process id is a spawn, not a proof of life. Read the first "
         "lines of that log before you trust the handover.")
    return 0


COMMANDS = {"continue": cmd_continue}


def main(argv):
    argv = list(argv or [])
    if not argv or argv[0] in ("-h", "--help", "help"):
        _out("bm_continue: generate the handoff packet from the store and "
             "start the next session.")
        _out("")
        _out("  continue  [--project-id ID] [--root PATH] [--out FILE] "
             "[--log PATH] [--permission-mode MODE] [--dry-run] [--json]")
        return 0
    cmd = argv[0]
    if cmd not in COMMANDS:
        _err("bm_continue: unknown command %r (known: %s)"
             % (cmd, ", ".join(sorted(COMMANDS))))
        return 2
    return COMMANDS[cmd](argv[1:])


def cli():
    sys.exit(main(sys.argv[1:]))


if __name__ == "__main__":
    cli()
