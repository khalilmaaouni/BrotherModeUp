#!/usr/bin/env python3
"""uninstall.py: remove BrotherMode's hook wiring, and nothing else.

WHAT IT REMOVES
  Only hook entries whose command names this installation's own tools/bm_*
  files, plus the install record scripts/install.py wrote. Every other hook you
  have, and every other key in settings.json, is left exactly where it was, in
  order.

WHAT IT NEVER TOUCHES
  Your vault. Not by default, not with a flag, not with --purge. There is no
  code path in this file that deletes a vault, because a vault is months of
  your own notes and an uninstaller is the last place that decision should be
  made. It prints the vault path so you can delete it yourself if you want to.

  It also does not touch what BrotherMode wrote inside your projects: the
  per-project .brothermode/ store, thread files, STATE.md and its backups, the
  local autosave git refs, or the lines in .git/info/exclude. Those are listed
  at the end with the commands to remove them, because they live in YOUR
  repositories and a tool that reaches into those uninvited is worse than one
  that leaves litter.

  Removing the installed files themselves needs --remove-files, and even then
  it refuses unless the directory actually looks like a BrotherMode checkout.

Python 3.9, standard library only, no network, no subprocess.

No em or en dashes anywhere in this file, its comments, or its output.
"""

import argparse
import io
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import install as _install  # noqa: E402  (same directory, deliberate)

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_REFUSED = 4


def _out(text):
    sys.stdout.write(text + "\n")


def _err(text):
    sys.stderr.write(text + "\n")


def strip_hooks(settings, target):
    """Return (new_settings, removed_count). Pure."""
    new = json.loads(json.dumps(settings))
    hooks = new.get("hooks")
    if not isinstance(hooks, dict):
        return new, 0
    removed = 0
    for event in list(hooks.keys()):
        groups = hooks.get(event)
        if not isinstance(groups, list):
            continue
        kept = [g for g in groups if not _install.group_is_ours(g, target)]
        removed += len(groups) - len(kept)
        if kept:
            hooks[event] = kept
        else:
            # Only ours were here. Remove the key rather than leaving an empty
            # list, which reads as a configured but broken hook.
            del hooks[event]
    if not hooks:
        del new["hooks"]
    return new, removed


def build_parser():
    p = argparse.ArgumentParser(
        prog="uninstall.py",
        description="Remove BrotherMode hook entries. Never touches your vault.")
    p.add_argument("--target", default=None,
                   help="the install directory; read from the install record "
                        "when not given")
    p.add_argument("--settings", default=None,
                   help="Claude Code settings file (default ~/.claude/settings.json)")
    p.add_argument("--remove-files", action="store_true",
                   help="also delete the installed skill directory")
    p.add_argument("--dry-run", action="store_true",
                   help="print what would be removed and change nothing")
    return p


def main(argv):
    args = build_parser().parse_args(argv)
    dry = args.dry_run
    prefix = "[dry-run] " if dry else ""

    settings_path = os.path.abspath(args.settings or _install.default_settings_path())
    record_path = os.path.join(os.path.dirname(settings_path), _install.RECORD_NAME)

    record = None
    if os.path.exists(record_path):
        try:
            record = json.loads(io.open(record_path, encoding="utf-8").read())
        except (ValueError, IOError, OSError) as exc:
            _err("uninstall.py: the install record %s is unreadable (%s). "
                 "Pass --target explicitly." % (record_path, exc))
            record = None

    target = args.target or (record or {}).get("target")
    if not target:
        _err("uninstall.py: cannot tell which installation to remove.\n"
             "There is no install record at %s and no --target was given. "
             "Refusing to guess: guessing here means deciding on your behalf "
             "which hook entries are mine, and a wrong guess deletes yours.\n"
             "Re-run as: python3 scripts/uninstall.py --target "
             "/path/to/your/brothermode" % record_path)
        return EXIT_REFUSED
    target = os.path.abspath(target)

    try:
        settings, raw_before = _install.read_settings(settings_path)
    except ValueError as exc:
        _err("uninstall.py: %s" % exc)
        return EXIT_REFUSED

    owned = _install.find_existing_hooks(settings, target)
    _out("%starget:   %s" % (prefix, target))
    _out("%ssettings: %s" % (prefix, settings_path))

    if owned:
        for event, i in owned:
            _out("%shooks: removing %s[%d]" % (prefix, event, i))
    else:
        _out("%shooks: none found that belong to %s. Nothing to unwire."
             % (prefix, target))

    new_settings, removed = strip_hooks(settings, target)
    if removed and not dry:
        try:
            backup = _install.write_settings(
                settings_path, new_settings, raw_before, False)
        except (ValueError, IOError, OSError) as exc:
            _err("uninstall.py: writing %s failed: %s" % (settings_path, exc))
            return EXIT_FAILED
        if backup:
            _out("hooks: previous settings backed up to %s" % backup)
        _out("hooks: %d entry(ies) removed; every other hook left in place, in "
             "order." % removed)

    if os.path.exists(record_path):
        _out("%srecord: removing %s" % (prefix, record_path))
        if not dry:
            try:
                os.unlink(record_path)
            except OSError as exc:
                _err("uninstall.py: could not remove %s: %s" % (record_path, exc))
                return EXIT_FAILED

    if args.remove_files:
        if not os.path.isdir(target):
            _out("%sfiles: %s does not exist; nothing to remove." % (prefix, target))
        elif not _install.looks_like_brothermode(target):
            _err("uninstall.py: refusing to delete %s with --remove-files: it "
                 "does not look like a BrotherMode checkout (SKILL.md, VERSION "
                 "and tools/bm_store.py are not all there). Delete it yourself "
                 "if you are sure." % target)
            return EXIT_REFUSED
        else:
            _out("%sfiles: removing %s" % (prefix, target))
            if not dry:
                try:
                    shutil.rmtree(target)
                except OSError as exc:
                    _err("uninstall.py: could not remove %s: %s" % (target, exc))
                    return EXIT_FAILED
    else:
        _out("%sfiles: left in place at %s. Pass --remove-files to delete them."
             % (prefix, target))

    vault = os.environ.get("BROTHERMODE_VAULT")
    _out("")
    _out("Untouched, deliberately:")
    _out("  - Your vault%s. Nothing in this uninstaller deletes a vault, with "
         "or without a flag. Delete it yourself if you want it gone."
         % (" (%s)" % vault if vault else
            " (BROTHERMODE_VAULT is not set in this shell, so its path is not "
            "known here)"))
    _out("  - Per-project state in every repository you used it in: "
         ".brothermode/ (the sqlite store), threads/, STATE.md and STATE.md.bak*, "
         "the local autosave git refs (git for-each-ref refs/brothermode), and "
         "the /.brothermode line in .git/info/exclude. See README.md's Uninstall "
         "section for the exact removal commands.")
    _out("  - Any BROTHERMODE_* export you added to your shell profile.")
    if dry:
        _out("")
        _out("[dry-run] Nothing above was changed.")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
