#!/usr/bin/env python3
"""install.py: wire BrotherMode into Claude Code without hand-editing JSON.

WHY THIS EXISTS
  The documented install was "clone the repo, then open ~/.claude/settings.json
  and merge this block of JSON by hand". That instruction fails in the two ways
  hand-edited JSON always fails: a user with existing hooks either loses them to
  a paste-over or gives up, and a user who mistypes a comma gets a settings file
  Claude Code silently ignores, so every hook is off and nothing says so. The
  fence hook (PreToolUse) is the sharpest case: it is the only hook that can
  REFUSE a write, and an install that quietly omits it leaves the headline
  one-writer-per-file promise unenforced while looking installed.

WHAT IT GUARANTEES
  1. It never deletes a hook entry it did not write. A hook entry is ours only
     if EVERY filesystem path in its command, read the way a shell reads it and
     not by substring, is one of this installation's own tools/bm_* files. An
     unrelated SessionStart hook of yours therefore survives install, upgrade
     and uninstall untouched; so does a hook of yours that chains your script
     after ours, and so does a second BrotherMode installation whose path
     merely begins with the same characters as this one's.
  2. It refuses rather than overwrites. An existing BrotherMode install, or
     BrotherMode hook entries already in settings, stops the run unless
     --upgrade is passed explicitly.
  3. It refuses rather than repairs. A settings.json that is not valid JSON is
     never rewritten, because rewriting it would destroy whatever the user was
     halfway through typing. It is reported with the parser's own line and
     column.
  4. It backs up settings.json before every write, to
     settings.json.brothermode-backup-<timestamp>.
  5. It re-reads and re-parses what it wrote, then runs a smoke test, before
     claiming success. "Installed" here means "checked after the fact", not
     "the write call did not raise".

WHAT IT DOES NOT DO
  It does not create your vault, does not set BROTHERMODE_VAULT, and does not
  edit ~/.claude/CLAUDE.md. Those are printed as remaining manual steps at the
  end rather than done silently, because two of them are choices about where
  your own data lives and the third is a file whose contents this project has
  no business rewriting.

Python 3.9, standard library only, no network. Runs subprocesses only for the
smoke test, and only against the interpreter running this script.

No em or en dashes anywhere in this file, its comments, or its output.
"""

import argparse
import errno
import io
import json
import os
import platform
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2
EXIT_UNSUPPORTED = 3
EXIT_REFUSED = 4

# The six hook events this project installs. SessionStart, SessionEnd, Stop
# and PreCompact are the four documented in docs/SETUP.md; PreToolUse is the
# fence hook (docs/HOOKS.md); PostToolUse and a second PreToolUse group (below)
# are the Bash-write DETECTION pair, tools/bm_bash_audit.py (Loop 6 D-1).
#
# A1 fix (loop6 refuter findings, 2026-08-01): this used to stop at
# PreToolUse, five events, one group each. The Bash-audit pair was wired into
# the Claude Code plugin manifest (hooks/hooks.json) the day it shipped, but
# NOT into this clone-install path, so a founder who cloned the repo and ran
# this installer got the fence hook but never got Bash-write detection, with
# nothing telling them so. hook_groups() below now wires BOTH halves here
# too: PreToolUse carries the fence group AND a second, independent Bash
# group, and PostToolUse carries the Bash group's other half.
HOOK_EVENTS = ("SessionStart", "SessionEnd", "Stop", "PreCompact",
               "PreToolUse", "PostToolUse")

FENCE_MATCHER = "Edit|Write|MultiEdit|NotebookEdit|Bash"
FENCE_TIMEOUT = 10
BASH_AUDIT_MATCHER = "Bash"
BASH_AUDIT_PRE_TIMEOUT = 10
BASH_AUDIT_POST_TIMEOUT = 15

# Every tool basename a hook command of ours may name. Ownership of a hook entry
# is decided by (this installation's path) plus (one of these names), so a hook
# of the user's own that happens to live near the install is not claimed by us.
OWNED_TOOLS = (
    "bm_sessionstart.sh",
    "bm_telemetry.py",
    "bm_autosave.py",
    "bm_fence_hook.py",
    # Loop 6 WP-G (2026-08-01), wired on THIS path since the A1 fix above:
    # tools/bm_bash_audit.py, the PreToolUse/PostToolUse Bash-write
    # detection pair.
    "bm_bash_audit.py",
    # L04 (2026-08-05): tools/bm_lead.py, the second program in the Stop
    # group (the watchdog due-check). It MUST be here, and the test that
    # caught its absence is the reason to say why rather than just add it:
    # command_is_ours is deliberately asymmetric, so a command naming ANY
    # path this list does not own is never removed, on the grounds that
    # leaving one of our entries behind costs a duplicate hook while
    # removing one of the user's costs them work they cannot get back.
    # Chaining a new tool into an existing hook command therefore breaks
    # UNINSTALL rather than install, and it breaks it silently: the entry
    # simply stops being recognised as ours and stays in the user's
    # settings pointing at files that are no longer on disk.
    "bm_lead.py",
    # L05 (2026-08-06): tools/bm_view.py, the third and fourth programs in
    # the Stop group (the page rewrite-if-stale and the alert tick). Same
    # law as bm_lead.py above: the Stop command names it, so uninstall must
    # own it or the whole Stop entry stops being recognised as ours.
    "bm_view.py",
)

# Mirrors the fallback exclusion list in scripts/checksums.sh and
# scripts/verify-install.sh. Kept in sync by comment in all three, because each
# is self-contained on purpose and there is no shared file to hold it once.
COPY_EXCLUDE_NAMES = (
    ".git", ".brothermode", "__pycache__", "threads", ".superpowers",
    ".DS_Store", "STATE.md",
)

RECORD_NAME = "brothermode-install.json"


def _out(text):
    sys.stdout.write(text + "\n")


def _err(text):
    sys.stderr.write(text + "\n")


def _q(path):
    """Shell-quote a path for embedding in a hook command string.

    Load-bearing, not decorative: a home directory with a space in it (common on
    macOS) or a non-ASCII character (common everywhere outside en_US) produced a
    hook command that the shell split into two arguments, so the hook failed at
    every session start with a file-not-found nobody read."""
    return shlex.quote(path)


def hook_commands(target):
    """The exact command string for every hook entry this project wires,
    built from an absolute target and keyed by a short label rather than by
    event: since the A1 fix, PreToolUse carries TWO independent commands
    (the fence hook and the Bash-audit pre phase), so "one command per
    event" is no longer true and the key has to say which command.

    The PreCompact command runs two tools off one stdin payload, which needs a
    shell; it is assembled as an inner script and then quoted as a single
    argument to `sh -c`, so quoting survives one nesting level rather than being
    hand-escaped and hoped over."""
    tools = os.path.join(target, "tools")
    autosave = os.path.join(tools, "bm_autosave.py")
    telemetry = os.path.join(tools, "bm_telemetry.py")
    bash_audit = os.path.join(tools, "bm_bash_audit.py")
    lead = os.path.join(tools, "bm_lead.py")
    view = os.path.join(tools, "bm_view.py")
    inner = (
        'p=$(cat); printf %s "$p" | python3 ' + _q(autosave) + ' precompact; '
        'printf %s "$p" | python3 ' + _q(telemetry) + ' precompact-brief'
    )
    # L04: Stop runs TWO programs off one stdin payload, so it takes the same
    # inner-script-then-sh-c shape PreCompact already uses rather than a second
    # hand-escaped spelling. The second program is the watchdog due-check, which
    # ships ON BY DEFAULT by founder decision and writes nothing before consent
    # (it is a due-check, not a daemon).
    # WHY THIS EDIT EXISTS AT ALL, recorded because the guard is the only reason
    # it was caught: hooks/hooks.json and this function are two hand-maintained
    # copies of one wiring, and L04 changed only the first. A user installing
    # through this script would have got NO watchdog while the plugin manifest
    # promised one, which would have made "on by default" false for exactly the
    # people who never read the manifest.
    # L05: two further programs on the same payload, the page rewrite (silent
    # unless the fingerprint moved) and the alert tick (at most one NEEDS YOU
    # object per tick). Same four-copy law as the L04 note above: hooks.json
    # moved first and this function must move in the same change.
    stop_inner = (
        'p=$(cat); printf %s "$p" | python3 ' + _q(telemetry) + ' stop-warn; '
        'printf %s "$p" | python3 ' + _q(lead) + ' watchdog --tick; '
        'printf %s "$p" | python3 ' + _q(view) + ' render --if-stale; '
        'printf %s "$p" | python3 ' + _q(view) + ' alert --tick'
    )
    return {
        "SessionStart": "sh " + _q(os.path.join(tools, "bm_sessionstart.sh")),
        "SessionEnd": "python3 " + _q(telemetry) + " outcomes-append",
        "Stop": "sh -c " + _q(stop_inner),
        "PreCompact": "sh -c " + _q(inner),
        "PreToolUse": "python3 " + _q(os.path.join(tools, "bm_fence_hook.py")),
        "PreToolUse-bash-audit": "python3 " + _q(bash_audit) + " pre",
        "PostToolUse-bash-audit": "python3 " + _q(bash_audit) + " post",
    }


def hook_groups(target):
    """Every matcher-group this project wires, keyed by event, each value a
    LIST of groups (Claude Code's own shape for hooks.<event>).

    A1 fix (loop6 refuter findings): every event but PreToolUse wires
    exactly one group. PreToolUse wires TWO: the fence group, which can
    refuse an Edit/Write/MultiEdit/NotebookEdit call before it happens, and
    a second, independent Bash-matcher group for tools/bm_bash_audit.py's
    pre phase, which cannot refuse anything (Bash is absent from the fence
    hook's own WRITE_TOOLS by design; see that file's own docstring for
    why) but snapshots every fenced file so a later Bash write across a
    fence can be DETECTED. PostToolUse wires the Bash-audit pair's other
    half, the post phase that does the detecting."""
    cmds = hook_commands(target)

    def _group(matcher, command, timeout, status_message):
        entry = {"type": "command", "command": command}
        if timeout is not None:
            entry["timeout"] = timeout
        if status_message is not None:
            entry["statusMessage"] = status_message
        group = {"hooks": [entry]}
        if matcher is not None:
            group["matcher"] = matcher
        return group

    # C-07 (2026-08-03): every timeout and statusMessage below must match
    # hooks/hooks.json exactly, because those two files are the two documented
    # install paths and a reader following either one is entitled to the same
    # installation. They had drifted: this helper set no statusMessage at all
    # and no timeout on the first four events, so a plugin install and a clone
    # install produced measurably different configurations and nothing
    # compared them. tools/test_install.py's TestHooksJsonAgreesWithInstaller
    # now fails on any divergence, field by field.
    return {
        "SessionStart": [_group(None, cmds["SessionStart"], 30,
                                "Loading your project memory")],
        "SessionEnd": [_group(None, cmds["SessionEnd"], 30,
                              "Saving the session record")],
        # 15 to 30 with L04: the group now runs two programs rather than one.
        "Stop": [_group(None, cmds["Stop"], 30,
                        "Checking for unfinished work")],
        "PreCompact": [_group(
            None, cmds["PreCompact"], 60,
            "Saving your work before the context is condensed")],
        "PreToolUse": [
            _group(FENCE_MATCHER, cmds["PreToolUse"], FENCE_TIMEOUT,
                   "Checking that only one worker edits this file"),
            _group(BASH_AUDIT_MATCHER, cmds["PreToolUse-bash-audit"],
                   BASH_AUDIT_PRE_TIMEOUT,
                   "Noting the fenced files before this shell command runs"),
        ],
        "PostToolUse": [
            _group(BASH_AUDIT_MATCHER, cmds["PostToolUse-bash-audit"],
                   BASH_AUDIT_POST_TIMEOUT,
                   "Checking whether that shell command crossed a fence"),
        ],
    }


def command_path_tokens(command):
    """Every path-like argument in a hook command, with shell quoting undone.

    Ownership used to be decided by asking whether the target path appeared as a
    SUBSTRING of the command text. Four separate ways that deleted other
    people's hooks, all reproduced:

      1. Prefix collision. Target /x/brothermode "matched" a second
         installation at /x/brothermode2, so upgrading or uninstalling the
         short one silently unwired the long one. Two checkouts side by side is
         this project's own working layout, not an exotic case.
      2. Its own quoting defeated it. hook_commands() shell-quotes the path, so
         an install under "Repertoire d'installation" produced a command in
         which the raw target is NOT a substring. The installer then failed to
         recognise hooks it had written itself one command earlier, and
         uninstall reported "nothing to unwire" while leaving all five wired.
      3. A user hook that WRAPS ours (ours && their own script, one command)
         contained our path, so the whole entry, their script included, was
         deleted as ours.
      4. A user script named my_bm_fence_hook.py in a sibling directory matched
         both halves of the old test by substring and was deleted.

    So read the command the way a shell reads it instead of the way grep does:
    split it into arguments, step one level into `sh -c <script>` (our
    PreCompact command is exactly that shape), and return the arguments that
    look like filesystem paths. Returns None when the command cannot be parsed
    (unbalanced quotes), which callers treat as "not ours": an entry we cannot
    read is an entry we must not delete."""
    if not isinstance(command, str):
        return None
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    out = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok == "-c" and i + 1 < len(tokens):
            # The next argument is a shell script, not a path. Split it once
            # more so the paths inside it are seen; do not recurse further,
            # because a nested -c inside a script is not a shape we write and
            # guessing at it would widen ownership rather than narrow it.
            try:
                inner = shlex.split(tokens[i + 1])
            except ValueError:
                return None
            out.extend(t for t in inner if os.sep in t)
            i += 2
            continue
        if os.sep in tok:
            out.append(tok)
        i += 1
    return out


def command_is_ours(command, target):
    """Does this hook command belong to a BrotherMode installation at target?

    Deliberately narrow, and now narrow in the way it always claimed to be.
    Every path the command names must be one of this installation's own
    tools/bm_* files: same directory (exact, not prefix) and a basename in
    OWNED_TOOLS. One foreign path anywhere in the command, such as a user's own
    script chained after ours, and the entry is not ours and is never removed.
    That asymmetry is on purpose: the cost of leaving one of our entries behind
    is a duplicate hook, and the cost of removing one of theirs is work they
    cannot get back."""
    paths = command_path_tokens(command)
    if not paths:
        return False
    if not target:
        return False
    owned_dirs = set()
    for root in (os.path.abspath(target), os.path.realpath(target)):
        if root:
            owned_dirs.add(os.path.join(os.path.normpath(root), "tools"))
    for p in paths:
        norm = os.path.normpath(p)
        if not os.path.isabs(norm):
            # A relative path in a hook command is resolved against whatever
            # directory Claude Code happens to run it from, so it cannot be
            # proven to be ours. Leave it alone.
            return False
        if os.path.dirname(norm) not in owned_dirs:
            return False
        if os.path.basename(norm) not in OWNED_TOOLS:
            return False
    return True


def group_is_ours(group, target):
    """A matcher-group is ours only if EVERY command inside it is ours.

    A group the user has added their own hook to is left completely alone. This
    is the destructive-merge case: a naive "does any command match" test would
    delete the user's hook as collateral when it happens to share a group with
    ours."""
    if not isinstance(group, dict):
        return False
    hooks = group.get("hooks")
    if not isinstance(hooks, list) or not hooks:
        return False
    for h in hooks:
        if not isinstance(h, dict) or not command_is_ours(h.get("command"), target):
            return False
    return True


def find_existing_hooks(settings, target):
    """Every (event, index) currently held by a BrotherMode install at target."""
    found = []
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return found
    for event, groups in hooks.items():
        if not isinstance(groups, list):
            continue
        for i, group in enumerate(groups):
            if group_is_ours(group, target):
                found.append((event, i))
    return found


def merge_hooks(settings, target):
    """Return (new_settings, removed, added). Pure: does not touch the input."""
    new = json.loads(json.dumps(settings))
    hooks = new.get("hooks")
    if not isinstance(hooks, dict):
        if "hooks" in new:
            raise ValueError(
                "settings.json has a 'hooks' key that is not a JSON object "
                "(found %s). Refusing to replace it: fix or remove it by hand "
                "first." % type(hooks).__name__)
        hooks = {}
        new["hooks"] = hooks

    removed = 0
    for event in list(hooks.keys()):
        groups = hooks.get(event)
        if not isinstance(groups, list):
            continue
        kept = [g for g in groups if not group_is_ours(g, target)]
        removed += len(groups) - len(kept)
        if kept:
            hooks[event] = kept
        elif groups:
            # The event list existed only for us. Drop the empty key rather than
            # leaving "SessionEnd": [] behind, which reads as a configured hook.
            del hooks[event]

    groups_to_add = hook_groups(target)
    added = 0
    for event in HOOK_EVENTS:
        existing = hooks.get(event)
        if existing is None:
            hooks[event] = []
        elif not isinstance(existing, list):
            raise ValueError(
                "settings.json has hooks.%s set to a %s, not a list. Refusing "
                "to replace it." % (event, type(existing).__name__))
        # A1 fix: groups_to_add[event] is now a LIST (PreToolUse carries
        # two of our own groups, the rest carry one), so every group in it
        # is appended, not the single dict a pre-fix caller would expect.
        for group in groups_to_add[event]:
            hooks[event].append(group)
            added += 1
    return new, removed, added


def read_settings(path):
    """(settings_dict, raw_text_or_None). Refuses on anything it cannot merge."""
    if not os.path.exists(path):
        return {}, None
    if os.path.isdir(path):
        raise ValueError("%s is a directory, not a settings file" % path)
    try:
        raw = io.open(path, encoding="utf-8").read()
    except (IOError, OSError) as exc:
        raise ValueError("cannot read %s: %s" % (path, exc))
    if raw.strip() == "":
        return {}, raw
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise ValueError(
            "%s is not valid JSON: %s\n"
            "Refusing to rewrite it. Rewriting a broken settings file would "
            "throw away whatever you were in the middle of editing, and this "
            "installer cannot tell a typo from a deliberate half-finished "
            "change. Fix the file (python3 -m json.tool %s points at the same "
            "spot), then run this again." % (path, exc, _q(path)))
    if not isinstance(data, dict):
        raise ValueError(
            "%s parses as JSON but its top level is a %s, not an object. "
            "Refusing to replace it." % (path, type(data).__name__))
    return data, raw


def resolve_settings_link(path):
    """The real file behind settings.json, or path itself when it is not a link.

    Dotfile managers (stow, chezmoi, a hand-made ln -s) leave
    ~/.claude/settings.json as a symlink into a tracked repository. The atomic
    write below is os.replace onto the path, which REPLACES the link with a
    regular file: the tracked file kept the pre-install content, the hooks
    landed in a new untracked file, and the backup was written next to the link
    rather than next to the real file. Nothing said so, and uninstall could not
    put the link back. Resolve first, and the link survives while the file it
    points at is the one that changes."""
    try:
        if os.path.islink(path):
            return os.path.realpath(path)
    except OSError:
        pass
    return path


def write_settings(path, settings, raw_before, dry_run):
    """Back up, write atomically, then re-read and re-parse. Returns backup path."""
    if dry_run:
        return None
    path = resolve_settings_link(path)
    parent = os.path.dirname(os.path.abspath(path)) or "."
    try:
        os.makedirs(parent)
    except OSError as exc:
        if exc.errno != errno.EEXIST:
            raise
    backup = None
    if raw_before is not None:
        backup = "%s.brothermode-backup-%s" % (path, time.strftime("%Y%m%dT%H%M%S"))
        with io.open(backup, "w", encoding="utf-8") as fh:
            fh.write(raw_before)
    text = json.dumps(settings, indent=2, sort_keys=False) + "\n"
    fd, tmp = tempfile.mkstemp(dir=parent, prefix=".bm-settings-")
    try:
        with io.open(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    # Re-read from disk. The claim "your settings are valid JSON" is worth
    # nothing if it describes the object in memory rather than the bytes on
    # disk, which is where Claude Code will read it from.
    verify = io.open(path, encoding="utf-8").read()
    json.loads(verify)
    return backup


def _ignore_names(_dirpath, names):
    out = set()
    for n in names:
        if n in COPY_EXCLUDE_NAMES or n.startswith(".bak") or ".bak" in n:
            out.add(n)
    return out


def copy_tree(source, target, dry_run):
    """Copy the checkout into target. Never deletes anything already there.

    Stated limit, printed to the user on upgrade rather than buried here: this
    adds and overwrites, it does not prune. A file that existed in an older
    version and was deleted upstream stays behind. scripts/verify-install.sh
    reports exactly those as EXTRA, which is why the summary points at it."""
    copied = 0
    for dirpath, dirnames, filenames in os.walk(source):
        rel = os.path.relpath(dirpath, source)
        rel = "" if rel == "." else rel
        skip = _ignore_names(dirpath, dirnames)
        dirnames[:] = [d for d in dirnames if d not in skip]
        dest_dir = os.path.join(target, rel) if rel else target
        if not dry_run:
            try:
                os.makedirs(dest_dir)
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise
        for fn in filenames:
            if _ignore_names(dirpath, [fn]):
                continue
            src = os.path.join(dirpath, fn)
            if os.path.islink(src):
                # Same refusal as scripts/checksums.sh, for the same reason: a
                # symlink in a shipped tree is a defect or an attack, and an
                # installer is the wrong place to guess which.
                raise ValueError(
                    "%s is a symlink. Refusing to install a tree containing "
                    "symlinks (see scripts/checksums.sh for why)." % src)
            if not dry_run:
                shutil.copy2(src, os.path.join(dest_dir, fn))
            copied += 1
    return copied


def looks_like_brothermode(path):
    return all(os.path.exists(os.path.join(path, n))
               for n in ("SKILL.md", "VERSION", os.path.join("tools", "bm_store.py")))


def read_version(root):
    try:
        return io.open(os.path.join(root, "VERSION"), encoding="utf-8").read().strip()
    except (IOError, OSError):
        return "unknown"


def smoke_test(target):
    """Prove the installed copy actually runs before calling the install done.

    Two checks, both non-mutating and both against the installed copy rather
    than the source:

    1. Every file a hook command names exists. An install that wired a hook to a
       path that is not there is the exact failure mode this whole script is
       for, and it is silent at runtime because hooks fail quietly.
    2. The fence hook runs end to end on a real payload, from a throwaway
       directory, and exits 0. This is the one hook that can refuse a write, so
       "the file is present" is not enough: it has to execute. Run from a temp
       cwd so it finds no project root and takes its documented fail-open path,
       which means it writes nothing anywhere."""
    problems = []
    tools = os.path.join(target, "tools")
    for name in OWNED_TOOLS:
        p = os.path.join(tools, name)
        if not os.path.isfile(p):
            problems.append("missing: %s" % p)
    if problems:
        return problems

    fence = os.path.join(tools, "bm_fence_hook.py")
    tmpdir = tempfile.mkdtemp(prefix="bm-install-smoke-")
    try:
        payload = json.dumps({
            "session_id": "bm-install-smoke",
            "cwd": tmpdir,
            "hook_event_name": "PreToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": os.path.join(tmpdir, "nothing")},
        })
        try:
            proc = subprocess.run(
                [sys.executable, fence],
                cwd=tmpdir, input=payload, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, universal_newlines=True, timeout=60)
        except (OSError, subprocess.SubprocessError) as exc:
            return ["the fence hook could not be run: %s" % exc]
        if proc.returncode != 0:
            problems.append(
                "the fence hook exited %d; it is documented to always exit 0. "
                "stderr: %s" % (proc.returncode, (proc.stderr or "").strip()[:400]))
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    return problems


def write_record(path, data, dry_run):
    if dry_run:
        return
    parent = os.path.dirname(os.path.abspath(path)) or "."
    try:
        os.makedirs(parent)
    except OSError as exc:
        if exc.errno != errno.EEXIST:
            raise
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(data, indent=2, sort_keys=True) + "\n")


def default_settings_path():
    return os.path.join(os.path.expanduser("~"), ".claude", "settings.json")


def default_target():
    return os.path.join(os.path.expanduser("~"), ".claude", "skills", "brothermode")


def check_platform(argv_name):
    if os.name == "nt":
        _err(
            "%s: refusing to install on Windows.\n"
            "This is a refusal, not a crash, and the reason is specific: the "
            "hook commands this installer writes are POSIX shell. SessionStart "
            "runs `sh <path>/tools/bm_sessionstart.sh` and PreCompact runs "
            "`sh -c` with a pipeline, and neither cmd.exe nor PowerShell will "
            "run them. Two of the six wired events (SessionStart, PreCompact) "
            "would be wired and silently dead.\n"
            "Working paths on Windows: install inside WSL (a real POSIX shell, "
            "and Claude Code runs there), or wire the python3-only hooks "
            "(SessionEnd, Stop, the PreToolUse fence, and the Bash-audit "
            "PreToolUse/PostToolUse pair) by hand per docs/HOOKS.md and accept "
            "that SessionStart and PreCompact are off.\n"
            "Platform seen: %s." % (argv_name, platform.platform()))
        return EXIT_UNSUPPORTED
    if sys.version_info < (3, 9):
        _err("%s: needs Python 3.9 or newer; this interpreter is %s"
             % (argv_name, platform.python_version()))
        return EXIT_UNSUPPORTED
    return None


def build_parser():
    p = argparse.ArgumentParser(
        prog="install.py",
        description="Install BrotherMode and wire its Claude Code hooks.")
    p.add_argument("--target", default=None,
                   help="where the skill lives (default ~/.claude/skills/brothermode)")
    p.add_argument("--settings", default=None,
                   help="Claude Code settings file (default ~/.claude/settings.json)")
    p.add_argument("--upgrade", action="store_true",
                   help="allow overwriting an existing BrotherMode install and "
                        "rewiring hook entries it already owns")
    p.add_argument("--dry-run", action="store_true",
                   help="print every change that would be made and write nothing")
    p.add_argument("--no-hooks", action="store_true",
                   help="install files only, leave settings.json untouched")
    return p


def main(argv):
    args = build_parser().parse_args(argv)
    bad = check_platform("install.py")
    if bad is not None:
        return bad

    dry = args.dry_run
    prefix = "[dry-run] " if dry else ""
    source = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if not looks_like_brothermode(source):
        _err("install.py: %s does not look like a BrotherMode checkout "
             "(SKILL.md, VERSION and tools/bm_store.py must all be present)."
             % source)
        return EXIT_FAILED

    target = os.path.abspath(args.target or default_target())
    settings_path = os.path.abspath(args.settings or default_settings_path())
    record_path = os.path.join(os.path.dirname(settings_path), RECORD_NAME)
    version = read_version(source)

    # realpath on both sides, so a symlinked install directory is recognized as
    # the same place rather than copied onto itself.
    in_place = os.path.exists(target) and \
        os.path.realpath(source) == os.path.realpath(target)

    try:
        settings, raw_before = read_settings(settings_path)
    except ValueError as exc:
        _err("install.py: %s" % exc)
        return EXIT_REFUSED

    existing_hooks = find_existing_hooks(settings, target)
    target_populated = os.path.isdir(target) and bool(os.listdir(target))
    prior_install = os.path.exists(record_path) or \
        (target_populated and looks_like_brothermode(target))

    if not args.upgrade:
        reasons = []
        if prior_install and not in_place:
            reasons.append(
                "a BrotherMode installation already exists at %s (version %s)"
                % (target, read_version(target)))
        elif prior_install and in_place and os.path.exists(record_path):
            reasons.append("this checkout was already installed (record: %s)"
                           % record_path)
        elif target_populated and not in_place:
            reasons.append(
                "%s already exists and is not empty, and does not look like a "
                "BrotherMode checkout" % target)
        if existing_hooks:
            reasons.append(
                "settings.json already has %d BrotherMode hook entry(ies): %s"
                % (len(existing_hooks),
                   ", ".join("%s[%d]" % (e, i) for e, i in existing_hooks)))
        if reasons:
            _err("install.py: refusing to overwrite an existing installation.")
            for r in reasons:
                _err("  - %s" % r)
            _err("Nothing has been changed. Re-run with --upgrade if that is "
                 "what you want; run with --upgrade --dry-run first to see "
                 "exactly what it would do.")
            return EXIT_REFUSED

    _out("%sBrotherMode %s" % (prefix, version))
    _out("%s  source:   %s" % (prefix, source))
    _out("%s  target:   %s%s" % (prefix, target,
                                 " (already there, no copy needed)" if in_place else ""))
    _out("%s  settings: %s" % (prefix, settings_path))

    # --- files
    if in_place:
        _out("%sfiles: source and target are the same directory; nothing copied."
             % prefix)
    else:
        try:
            n = copy_tree(source, target, dry)
        except (ValueError, IOError, OSError) as exc:
            _err("install.py: copying the tree failed: %s" % exc)
            return EXIT_FAILED
        _out("%sfiles: %d file(s) %s %s"
             % (prefix, n, "would be copied to" if dry else "copied to", target))
        if args.upgrade and target_populated:
            _out("%sfiles: an upgrade ADDS and OVERWRITES; it never deletes. A "
                 "file removed upstream since your last install is still there. "
                 "scripts/verify-install.sh reports those as EXTRA." % prefix)

    # --- hooks
    if args.no_hooks:
        _out("%shooks: skipped (--no-hooks). Nothing is wired; see docs/SETUP.md."
             % prefix)
        removed = added = 0
        backup = None
    else:
        try:
            new_settings, removed, added = merge_hooks(settings, target)
        except ValueError as exc:
            _err("install.py: %s" % exc)
            return EXIT_REFUSED
        try:
            backup = write_settings(settings_path, new_settings, raw_before, dry)
        except (ValueError, IOError, OSError) as exc:
            _err("install.py: writing %s failed: %s" % (settings_path, exc))
            return EXIT_FAILED
        real_settings = resolve_settings_link(settings_path)
        if real_settings != settings_path:
            _out("%shooks: %s is a symlink; the file it points at (%s) is what "
                 "%s edited, and the link is left as it was."
                 % (prefix, settings_path, real_settings,
                    "would be" if dry else "was"))
        _out("%shooks: %d BrotherMode entry(ies) replaced, %d installed: %s"
             % (prefix, removed, added, ", ".join(HOOK_EVENTS)))
        if backup:
            _out("%shooks: previous settings backed up to %s" % (prefix, backup))
        _out("%shooks: every hook entry not owned by BrotherMode was left in "
             "place, in order." % prefix)

    # --- record
    record = {
        "version": version,
        "source": source,
        "target": target,
        "settings": settings_path,
        "installed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "hooks": [] if args.no_hooks else list(HOOK_EVENTS),
        "installer": "scripts/install.py",
    }
    try:
        write_record(record_path, record, dry)
    except (IOError, OSError) as exc:
        _err("install.py: could not write the install record %s: %s"
             % (record_path, exc))
        return EXIT_FAILED
    _out("%srecord: %s" % (prefix, record_path))

    # --- smoke test
    if dry:
        _out("%ssmoke: skipped; nothing was written to test." % prefix)
    else:
        problems = smoke_test(target)
        if problems:
            _err("install.py: NOT DONE. The files were written but the smoke "
                 "test failed, so do not treat this as installed:")
            for p in problems:
                _err("  - %s" % p)
            if not args.no_hooks and backup:
                _err("Your previous settings.json is at %s." % backup)
            return EXIT_FAILED
        _out("smoke: the fence hook ran end to end and exited 0; every file a "
             "hook command names exists.")
        _out("smoke: this proves the hook RUNS, not that it REFUSES. For that, "
             "run: python3 %s --settings %s"
             % (os.path.join(target, "scripts", "doctor.py"), settings_path))

    _out("")
    _out("%sInstalled:" % prefix)
    if not args.no_hooks:
        # A1 fix: PreToolUse now carries two groups and needs its matcher
        # named to tell them apart, so this prints one line per GROUP
        # rather than assuming one command per event.
        for event in HOOK_EVENTS:
            for group in hook_groups(target)[event]:
                matcher = group.get("matcher")
                label = "%s[%s]" % (event, matcher) if matcher else event
                _out("  %-28s %s" % (label, group["hooks"][0]["command"]))
    _out("")
    _out("Still manual, on purpose:")
    _out("  1. Your vault. cp -R %s ~/BrotherModeVault, then export "
         "BROTHERMODE_VAULT=\"$HOME/BrotherModeVault\" in your shell profile. "
         "This installer never creates or moves a vault, and never deletes one."
         % os.path.join(target, "vault-template"))
    _out("  2. The /brothermode trigger line in ~/.claude/CLAUDE.md "
         "(docs/SETUP.md, step 1). That file is yours; nothing here rewrites it.")
    _out("  3. Verify what you installed: sh %s"
         % os.path.join(target, "scripts", "verify-install.sh"))
    _out("  4. Restart Claude Code. Hook configuration is read at startup, so a "
         "session already running does not have these.")
    if dry:
        _out("")
        _out("[dry-run] Nothing above was written.")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
