#!/usr/bin/env python3
"""doctor.py: is the fence hook actually ACTIVE, or only wired?

WHY THIS EXISTS
  scripts/install.py writes the PreToolUse fence entry into settings.json and
  smoke tests that the hook file runs and exits 0. Both checks pass on a fence
  that refuses nothing: the smoke test runs the hook from an empty directory,
  where it takes its documented fail-open path. So "installed" so far means
  "present and executable", not "denies a write across someone else's fence".
  That gap is exactly the shape of the headline promise, so it gets its own
  command.

WHAT IT DOES
  1. Reads settings.json and finds the PreToolUse group whose command names a
     bm_fence_hook.py. Missing group, missing entry, or a command pointing at a
     file that is not there are each reported as a PROBLEM, by name.
  2. Runs a BLOCKED-WRITE SIMULATION against the command string settings.json
     actually holds, not against a path this script reconstructs. It builds a
     throwaway project under a temporary directory, gives it its own store,
     claims one file under one session's label, then asks the wired hook to
     approve a write to that file from a DIFFERENT session. A healthy fence
     denies. Then it asks again as the owner, and a healthy fence allows,
     with output AND exit code both clean. Both halves are required: a hook
     that denied everything would pass the first check and is not a fence, it
     is a brick, and a hook that bricks by exiting 2 rather than by printing
     deny is the same brick. Every supported write tool is simulated in its
     own real input shape, so a fence that gates one of them and not the
     other three cannot report itself healthy.
  3. Says out loud that the fence FAILS OPEN, and what that means for the
     answer above.

  The simulation is harmless in the strict sense: every file it creates lives
  under a fresh mkdtemp directory that is removed at the end, it never touches
  your project, your store, or your STATE.md, and the write it simulates is
  never performed by anything. Nothing outside the temporary directory is
  read for the simulation except the hook and store code being tested.

WHAT IT CANNOT TELL YOU
  That Claude Code has loaded this settings file. A hook is read by the client
  at session start; a correct settings.json edited mid-session is not live
  until the next session. Doctor checks the file and the code, which is
  everything except the client's memory.

Python 3.9, standard library only, no network. Runs subprocesses only to
execute the wired hook command and this project's own store CLI.

No em or en dashes anywhere in this file, its comments, or its output.
"""

import argparse
import io
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

EXIT_OK = 0
EXIT_PROBLEMS = 1
EXIT_USAGE = 2
EXIT_UNSUPPORTED = 3

FENCE_BASENAME = "bm_fence_hook.py"
WRITE_TOOL_NAMES = ("Edit", "Write", "MultiEdit", "NotebookEdit")

#: The tool_input shape each simulated write tool sends, keyed by tool name.
#: The path key differs per tool (NotebookEdit carries notebook_path, not
#: file_path), and a hook that reads only one of them gates only one of them,
#: so the simulation sends each tool its own real shape rather than one shape
#: relabelled four times.
SIM_TOOL_INPUTS = {
    "Edit": lambda t: {"file_path": t, "old_string": "a", "new_string": "b"},
    "Write": lambda t: {"file_path": t, "content": "doctor simulation\n"},
    "MultiEdit": lambda t: {"file_path": t,
                            "edits": [{"old_string": "a", "new_string": "b"}]},
    "NotebookEdit": lambda t: {"notebook_path": t, "new_source": "x = 1\n"},
}

OWNER_SESSION = "bm-doctor-owner"
INTRUDER_SESSION = "bm-doctor-intruder"
SIM_REL_PATH = os.path.join("sim", "fenced.txt")


def _out(text):
    sys.stdout.write(text + "\n")


def _err(text):
    sys.stderr.write(text + "\n")


def default_settings_path():
    return os.path.join(os.path.expanduser("~"), ".claude", "settings.json")


def read_settings(path):
    """Returns (settings_dict, error_string). Never raises on bad input: an
    unreadable settings file is a finding to report, not a traceback."""
    if not os.path.exists(path):
        return None, "no settings file at %s" % path
    try:
        with io.open(path, encoding="utf-8") as fh:
            raw = fh.read()
    except (IOError, OSError) as exc:
        return None, "settings file at %s could not be read: %s" % (path, exc)
    try:
        data = json.loads(raw)
    except ValueError as exc:
        return None, ("settings file at %s is not valid JSON (%s). Claude Code "
                      "ignores it silently, so EVERY hook is off." % (path, exc))
    if not isinstance(data, dict):
        return None, "settings file at %s is JSON but not an object" % path
    return data, None


def find_fence_entries(settings):
    """Every PreToolUse hook entry whose command names a bm_fence_hook.py.

    Matched on the BASENAME of a real path inside the command, read the way a
    shell reads it, so a hook of the user's own called my_bm_fence_hook.py is
    not mistaken for ours. This mirrors install.py's ownership rule; it is
    deliberately duplicated rather than imported, because each script in this
    directory is self-contained on purpose."""
    found = []
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return found
    groups = hooks.get("PreToolUse")
    if not isinstance(groups, list):
        return found
    for group in groups:
        if not isinstance(group, dict):
            continue
        for entry in group.get("hooks", []) or []:
            if not isinstance(entry, dict):
                continue
            command = entry.get("command")
            if not isinstance(command, str):
                continue
            try:
                words = shlex.split(command)
            except ValueError:
                continue
            if any(os.path.basename(w) == FENCE_BASENAME for w in words):
                found.append((group, entry, command, words))
    return found


def matcher_covers(matcher, tool_name):
    """Does this PreToolUse matcher select tool_name? Returns True, False, or
    None when the matcher is not a usable regular expression.

    Claude Code treats the matcher as a REGEX tested against the tool name, so
    that is what this tests. It is emphatically NOT a substring test of the
    tool name in the matcher string (fix-round 2026-07-29): 'Edit' is a
    substring of both 'MultiEdit' and 'NotebookEdit', so a matcher of
    'Write|MultiEdit|NotebookEdit' passed a `tool not in matcher` check while
    leaving Edit, the primary write tool, completely ungated. Reproduced by
    running doctor against exactly that matcher: it printed OK and exited 0."""
    m = (matcher or "").strip()
    if m in ("*", ".*"):
        return True
    try:
        return re.search(m, tool_name) is not None
    except re.error:
        return None


def fence_path_in(words):
    for w in words:
        if os.path.basename(w) == FENCE_BASENAME:
            return w
    return None


def _run(cmd, cwd, env, stdin_text=None, timeout=120):
    return subprocess.run(
        cmd, cwd=cwd, env=env, input=stdin_text,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        universal_newlines=True, timeout=timeout)


def blocked_write_simulation(command_words, tools_dir):
    """Ask the WIRED hook command to judge one foreign write and one own write.

    Returns a list of problem strings; empty means the fence is live."""
    problems = []
    tmp = tempfile.mkdtemp(prefix="bm-doctor-")
    try:
        root = os.path.realpath(tmp)
        os.makedirs(os.path.join(root, "sim"))
        target = os.path.join(root, SIM_REL_PATH)
        with io.open(target, "w", encoding="utf-8") as fh:
            fh.write("doctor simulation target, deleted when doctor exits\n")

        env = dict(os.environ)
        env["BROTHERMODE_ROOT"] = root
        env.pop("BM_FENCE_STRICT", None)
        env.pop("BM_FENCE_SESSION_ID", None)

        store = os.path.join(tools_dir, "bm_store.py")
        fence = fence_path_in(command_words)
        if not os.path.isfile(store):
            return ["cannot simulate: no bm_store.py beside the wired hook "
                    "(looked for %s)" % store]

        r = _run([sys.executable, store, "init"], root, env)
        if r.returncode != 0:
            return ["cannot simulate: the store CLI could not create a "
                    "throwaway store (exit %d): %s"
                    % (r.returncode, (r.stderr or r.stdout or "").strip()[:300])]

        r = _run([sys.executable, fence, "session-label",
                  "--session-id", OWNER_SESSION], root, env, stdin_text="")
        owner_label = (r.stdout or "").strip().splitlines()[-1] if r.stdout else ""
        if r.returncode != 0 or not owner_label:
            return ["cannot simulate: the hook would not mint a session label "
                    "(exit %d): %s"
                    % (r.returncode, (r.stderr or "").strip()[:300])]

        r = _run([sys.executable, store, "claim", "bm-doctor-simulation",
                  "--lifetime", "ephemeral",
                  "--objective", "doctor blocked-write simulation",
                  "--files", SIM_REL_PATH,
                  "--session", owner_label], root, env)
        if r.returncode != 0:
            return ["cannot simulate: the throwaway claim was refused (exit "
                    "%d): %s" % (r.returncode,
                                 (r.stderr or r.stdout or "").strip()[:300])]

        def ask(session_id, tool_name):
            payload = json.dumps({
                "session_id": session_id,
                "cwd": root,
                "hook_event_name": "PreToolUse",
                "tool_name": tool_name,
                "tool_input": SIM_TOOL_INPUTS[tool_name](target),
            })
            return _run(list(command_words), root, env, stdin_text=payload)

        # Every supported write tool is simulated, not just Edit (fix-round
        # 2026-07-29). One shape per tool, because the four do not share a
        # path key, and a hook whose WRITE_TOOLS set had lost three of them
        # passed the Edit-only simulation while three tools wrote unfenced.
        for tool_name in WRITE_TOOL_NAMES:
            # Half one: a foreign session must be DENIED.
            r = ask(INTRUDER_SESSION, tool_name)
            if r.returncode != 0:
                problems.append(
                    "the wired hook exited %d on the %s simulation; it is "
                    "documented to always exit 0. stderr: %s"
                    % (r.returncode, tool_name, (r.stderr or "").strip()[:300]))
            decision = None
            text = (r.stdout or "").strip()
            if text:
                try:
                    decision = json.loads(text)
                except ValueError:
                    problems.append(
                        "the wired hook printed something that is not JSON on "
                        "the %s simulation: %s" % (tool_name, text[:200]))
            verdict = None
            if isinstance(decision, dict):
                verdict = (decision.get("hookSpecificOutput") or {}).get(
                    "permissionDecision")
            if verdict != "deny":
                problems.append(
                    "BLOCKED-WRITE SIMULATION FAILED for %s: a session that "
                    "owns nothing was allowed to write a file another session "
                    "had claimed. The hook is wired but it is not enforcing "
                    "%s. Hook stderr: %s"
                    % (tool_name, tool_name,
                       (r.stderr or "").strip()[:400] or "(none)"))

            # Half two: the OWNER must still be allowed. A hook that denies
            # everything would pass half one and would not be a fence.
            r2 = ask(OWNER_SESSION, tool_name)
            # The EXIT CODE is checked here as well as the output (fix-round
            # 2026-07-29). Claude Code's PreToolUse contract blocks a tool
            # call on exit code 2 with stderr, not only on deny JSON, so a
            # hook that emitted correct deny JSON for a foreign session and
            # exited 2 on every allowed write bricked the owner's own editing
            # while doctor printed OK and exited 0.
            if r2.returncode != 0:
                problems.append(
                    "CALIBRATION FAILED: on the owner's own %s the hook exited "
                    "%d. A non-zero exit is how a PreToolUse hook BLOCKS a "
                    "call, so this hook refuses writes it should allow even "
                    "though it printed no deny. stderr: %s"
                    % (tool_name, r2.returncode, (r2.stderr or "").strip()[:300]))
            text2 = (r2.stdout or "").strip()
            if text2:
                problems.append(
                    "CALIBRATION FAILED: the owner of the claim was refused "
                    "its own file on %s, so this hook denies writes it should "
                    "allow. Output: %s" % (tool_name, text2[:300]))

        if os.path.exists(os.path.join(root, "sim", "written-by-doctor")):
            problems.append("the simulation wrote a file it should not have")
        return problems
    except (OSError, subprocess.SubprocessError) as exc:
        return ["the simulation could not be run: %s: %s"
                % (type(exc).__name__, exc)]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def doctor(settings_path):
    """Returns (problems, notes). Both are lists of strings."""
    problems = []
    notes = []

    settings, err = read_settings(settings_path)
    if err is not None:
        return [err], notes

    entries = find_fence_entries(settings)
    if not entries:
        return (["NO FENCE HOOK IS WIRED. settings.json (%s) has no PreToolUse "
                 "entry naming %s, so nothing stands in front of a write and "
                 "the one-writer promise is a ledger, not a boundary. Fix: run "
                 "python3 scripts/install.py (or --upgrade over an existing "
                 "install), or add the block in docs/HOOKS.md by hand."
                 % (settings_path, FENCE_BASENAME)], notes)
    if len(entries) > 1:
        notes.append("%d fence entries are wired; the first one is the one "
                     "checked below." % len(entries))

    group, entry, command, words = entries[0]
    fence = fence_path_in(words)
    notes.append("fence command: %s" % command)

    matcher = group.get("matcher")
    if not isinstance(matcher, str) or not matcher.strip():
        problems.append(
            "the fence group has no matcher, so it runs on every tool call. "
            "That is wasteful rather than wrong, but it is not what install.py "
            "writes; expected %s." % "|".join(WRITE_TOOL_NAMES))
    else:
        verdicts = [(t, matcher_covers(matcher, t)) for t in WRITE_TOOL_NAMES]
        if any(v is None for _t, v in verdicts):
            problems.append(
                "the fence matcher %r is not a valid regular expression, so "
                "Claude Code cannot match any tool name against it and EVERY "
                "write tool is ungated. Expected %s."
                % (matcher, "|".join(WRITE_TOOL_NAMES)))
        else:
            missing = [t for t, v in verdicts if not v]
            if missing:
                problems.append(
                    "the fence matcher %r does not cover %s, so those write "
                    "tools are UNGATED." % (matcher, ", ".join(missing)))

    if not fence or not os.path.isfile(fence):
        return (problems + [
            "the wired fence command points at %s, which is not a file. The "
            "hook is configured and dead: Claude Code will report a hook error "
            "and continue, so writes proceed unfenced."
            % (fence or "(no path found in the command)")], notes)

    tools_dir = os.path.dirname(os.path.abspath(fence))
    problems.extend(blocked_write_simulation(words, tools_dir))
    return problems, notes


def build_parser():
    p = argparse.ArgumentParser(
        prog="doctor.py",
        description="Check that the BrotherMode fence hook is wired AND live.")
    p.add_argument("--settings", default=None,
                   help="Claude Code settings file "
                        "(default ~/.claude/settings.json)")
    return p


def main(argv):
    args = build_parser().parse_args(argv)
    if sys.version_info < (3, 9):
        _err("doctor.py: needs Python 3.9 or newer; this interpreter is %s"
             % platform.python_version())
        return EXIT_UNSUPPORTED
    settings_path = os.path.abspath(args.settings or default_settings_path())

    _out("BrotherMode doctor: fence hook")
    _out("  settings: %s" % settings_path)
    problems, notes = doctor(settings_path)
    for n in notes:
        _out("  note: %s" % n)

    if problems:
        _out("")
        _out("PROBLEMS (%d):" % len(problems))
        for p in problems:
            _out("  - %s" % p)
        _out("")
        _out("Until these are fixed, treat file ownership as a coordination "
             "ledger only: bm_store.py still refuses an overlapping CLAIM, but "
             "nothing refuses a WRITE.")
        return EXIT_PROBLEMS

    _out("  OK: for each of %s, the wired hook denied a foreign write and "
         "allowed the owner's own write, in a throwaway project that has been "
         "deleted." % ", ".join(WRITE_TOOL_NAMES))
    _out("")
    _out("What this does NOT prove, stated so it is not assumed:")
    _out("  - The fence FAILS OPEN by design (docs/HOOKS.md). A missing store, "
         "a corrupt store, a store with no active claims, or any bug in the "
         "hook allows the write and prints a line starting "
         "'bm_fence_hook: FAILING OPEN'. A hook that fails closed would brick "
         "editing, which is a worse failure than an unenforced fence, so this "
         "is a choice and not an oversight.")
    _out("  - Bash is NOT gated. Shell redirection, sed -i, tee, python -c and "
         "the rest write files without passing any hook. That is outside "
         "mechanical protection, by policy and not by accident.")
    _out("  - Claude Code loads settings at session start, so a settings file "
         "corrected during a session is live at the NEXT session, not this one.")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
