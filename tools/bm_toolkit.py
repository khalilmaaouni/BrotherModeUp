#!/usr/bin/env python3
"""Enumerate what capability is installed on this machine, mechanically.

WHY THIS EXISTS
  BrotherMode's Toolkit is a capability BROKER, not a marketplace (see
  docs/plan/TOOLKIT-PLAN-2026-08-12.md section 3, function F1). No command
  today answers "what capability is installed on this machine" across
  plugins, skills, hooks, settings layers and MCP servers at once. Claude
  Code enumerates plugins one at a time (`claude plugin details`) but never
  aggregates across them, and never covers skills, settings layers or CLIs.
  This tool is that aggregation, read straight from artifacts: plugin
  manifests, hooks.json files, settings.json, the skills directory, and
  .claude.json. What a tool registers is observable without running it.

THE CONTRACT
  Four verbs. `inventory` (human readable, the default) and `json` (one
  JSON object, schema 1, for later loops such as conflict detection to
  consume rather than re-parse). See the top-level JSON shape in the plan
  brief; `build_inventory()` below is the single place that shape is built.
  `conflicts` (human readable) reads that same inventory plus a table of
  conflict classes and emits verdicts, per docs/plan/TOOLKIT-PLAN-2026-08-12.md
  section F2. `capabilities` (human readable) reads that same inventory and
  emits capability records, per section F3 and section 4 below.

CAPABILITY RECORDS (F3, section 4 of the plan)
  A capability record's reach is DECLARED, never measured by running
  anything: it is read from the same artifacts `build_inventory()` already
  parses (a plugin manifest, its hooks.json, a skill's hooks.json, the
  mcpServers key of .claude.json). Every DERIVED record names the exact
  artifact paths it was built from in its `source_files` list, which is
  never empty: the capability's own directory is always the first entry,
  because a directory existing is itself an artifact, and the manifest or
  hooks.json paths are appended when they were actually read.

  A record can also be HAND-ASSERTED: typed by a human into an optional
  override file (tools/toolkit_capability_overrides.json next to this
  file, or an explicit --overrides PATH) for a capability this inventory
  cannot derive from artifacts on its own, such as an external CLI. A
  hand-asserted record carries `hand_asserted: true`, an empty
  `source_files` (nothing was read to build it), and is rendered under its
  own visibly separate heading with a [HAND-ASSERTED] marker on every line,
  in `json` output and in the human-readable `capabilities` report alike,
  so it can never be mistaken for something the inventory derived. The
  override file is optional the same way the conflict classes override is:
  absent is silence, not an error; present and malformed is refused BY
  NAME (path and reason printed) and the run falls back to zero overrides,
  never classless-versus-crash, matching decision 34's shape for conflict
  classes.

  No persistence: a capability record is built fresh from the inventory at
  read time, on every run, and is never written to the store. The plan's
  F3 done-check ("a record is DERIVED from artifacts; a hand-asserted
  record is visibly marked") holds without a schema change, because the
  inventory this file already reads IS the artifact evidence; storing a
  second copy would just be a cache with its own staleness to manage.

CONFLICT CLASSES (F2)
  Ten classes, defined once in DEFAULT_CONFLICT_CLASSES below (decision 34:
  the shipped defaults live IN this file as a module constant, so a
  packaged install is never classless). tools/toolkit_conflict_classes.json
  next to this file is an OPTIONAL override: present and valid, it replaces
  the defaults entirely; present and malformed, it is refused BY NAME (the
  path and the reason are printed) and the defaults are used instead;
  absent, that is not an error, only silence, same as every other optional
  surface in this file.

  Each class carries a `detect` description and a `threshold`. A class this
  module knows how to check mechanically against the inventory fires when
  its measured count reaches `threshold`, at the severity the class (or its
  override) declares: info, warn, or fail, and nothing else. A class this
  module has no mechanical detector for reports NO-DATA, named, rather than
  going silent: silence would read as "checked, found nothing," which is
  not true of a surface this file never looked at.

  Every surface that cannot be read (permission error, not-a-directory,
  invalid JSON) is appended to `unreadable` with its path and reason; it
  never crashes the run and never silently vanishes. Absence is NOT
  unreadable: a marketplaces cache directory, a skills directory, or an
  enabledPlugins/mcpServers key that simply does not exist reports zero
  items, not an error, because "nothing here" is a real, readable answer.

  If EVERY one of the four core surfaces (marketplaces cache, user
  settings.json, skills directory, .claude.json) could not be read, the
  tool prints a line starting with the literal "NO-DATA:" and exits 2.
  Otherwise: 0 read something, 2 could not tell at all. There is no exit 1
  in this verb; nothing here is a failure verdict, only an inventory.

EFFECT CLASS: pure_read
  This tool writes NOT ONE BYTE anywhere, ever: no file writes, no
  directories created, no store touched. It never constructs a writable
  bm_store.Store (doing so is itself a write). bm_store is loaded only to
  borrow its resolve_root() for best-effort --root resolution, and that
  call is wrapped so a failure there degrades to os.getcwd(), never a
  crash and never a write.

BE SILENT-SAFE
  Any unexpected exception anywhere in this module is caught by `main` and
  reported as NO-DATA at exit 2, carrying the exception's type and
  message, rather than raising.

Python 3.9, standard library only. No network. No subprocess.
No em or en dashes anywhere in this file or its output.

Usage:
  python3 tools/bm_toolkit.py inventory    [--home PATH] [--root PATH]
  python3 tools/bm_toolkit.py json         [--home PATH] [--root PATH]
  python3 tools/bm_toolkit.py conflicts    [--home PATH] [--root PATH] [--classes PATH]
  python3 tools/bm_toolkit.py capabilities [--home PATH] [--root PATH] [--overrides PATH]

`inventory` is also the default when no verb is given. `--classes` overrides
the conflict class table for `conflicts` only; `--overrides` names the
hand-asserted capability record file for `capabilities` only; every other
verb ignores whichever of the two it is not given.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

_VERBS = ("inventory", "json", "conflicts", "capabilities")


# ---------------------------------------------------------------------------
# Root resolution (best effort only; see module docstring). Mirrors the
# --root pattern in tools/bm_progress_check.py and tools/bm_idle.py, but a
# failure here never aborts the run: the project root only feeds the
# project/project-local settings_layers rows, never the home-anchored
# surfaces that make up the bulk of the inventory.
# ---------------------------------------------------------------------------

def _load_bm_store():
    """Load bm_store.py by PATH, the same shape the sibling tools use: this
    tool is invoked with an arbitrary cwd, and a plain `import bm_store`
    would depend on whichever sys.path the caller happened to have. Never
    raises: an unimportable module degrades to (None, reason)."""
    try:
        import importlib.util
        path = os.path.join(HERE, "bm_store.py")
        spec = importlib.util.spec_from_file_location(
            "bm_store_for_toolkit", path)
        if spec is None or spec.loader is None:
            return None, "could not build an import spec for bm_store.py"
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod, None
    except Exception as exc:
        return None, "%s: %s" % (type(exc).__name__, exc)


def resolve_home(explicit_home):
    """Return (home, None) or (None, reason). `explicit_home` (--home)
    always wins; otherwise the real user home. Unlike root, a bad home is
    fatal: nearly every surface this tool reads lives under it."""
    raw = explicit_home if explicit_home else "~"
    candidate = os.path.realpath(os.path.expanduser(raw))
    if not os.path.isdir(candidate):
        return None, "no such directory: %s" % candidate
    return candidate, None


def resolve_root(explicit_root):
    """Return a best-effort project root, always a string, never raising.
    An explicit --root is used as given (even if it turns out not to
    exist; the settings_layers rows built from it will just report
    exists=False, which is itself a true answer). Otherwise bm_store's
    resolve_root() is borrowed; any failure there falls back to cwd."""
    if explicit_root:
        return os.path.realpath(os.path.expanduser(explicit_root))
    mod, _err = _load_bm_store()
    if mod is not None:
        try:
            root, _source = mod.resolve_root()
            if root:
                return root
        except Exception:
            pass
    return os.getcwd()


# ---------------------------------------------------------------------------
# Pure filesystem helpers shared by every surface below.
# ---------------------------------------------------------------------------

def _is_safe_child(home_real, path):
    """True if the symlink at `path` resolves to somewhere inside
    `home_real`. Used to refuse walking a symlink that escapes home."""
    try:
        target_real = os.path.realpath(path)
    except OSError:
        return False
    return target_real == home_real or target_real.startswith(home_real + os.sep)


def _list_dir_entries(dir_path, home_real, unreadable):
    """Return the sorted list of (name, full_path) directory children of
    `dir_path`, or None if `dir_path` itself could not be listed (recorded
    into `unreadable`). A symlinked child that escapes home_real is
    skipped and recorded rather than followed. Non-directory children are
    silently skipped: this walks capability directories, not files."""
    try:
        names = sorted(os.listdir(dir_path))
    except OSError as exc:
        unreadable.append({"path": dir_path,
                            "reason": "%s: %s" % (type(exc).__name__, exc)})
        return None
    result = []
    for name in names:
        full = os.path.join(dir_path, name)
        if os.path.islink(full) and not _is_safe_child(home_real, full):
            unreadable.append({"path": full,
                                "reason": "symlink escapes home directory, skipped"})
            continue
        if os.path.isdir(full):
            result.append((name, full))
    return result


def _safe_listdir(dir_path, home_real, unreadable):
    """(entries, ok). entries is always a list, never None. A directory
    that simply does not exist is a valid empty answer (ok=True, zero
    items): absence is not unreadable. ok is False only when the path
    exists but could not be listed (permission error, not a directory)."""
    if not os.path.exists(dir_path):
        return [], True
    entries = _list_dir_entries(dir_path, home_real, unreadable)
    if entries is None:
        return [], False
    return entries, True


def _describe_unreadable_file(path):
    """Reason string for a path that was expected to be a readable file
    but is not: distinguishes "never existed" from "exists as something
    else" (a directory, most commonly), so the unreadable entry is honest
    about what was actually found on disk."""
    if not os.path.exists(path):
        return "missing file"
    return "not a regular file"


def _read_json_file(path):
    """(data, None) or (None, reason). The only place this module opens a
    JSON file; every surface below goes through here."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle), None
    except FileNotFoundError:
        return None, "missing file"
    except (OSError, ValueError) as exc:
        return None, "%s: %s" % (type(exc).__name__, exc)


def _parse_hook_events(hooks_path, unreadable):
    """The SET (sorted list) of capitalised event names a hooks.json file
    registers, or [] if the file is absent (not an error: hooks are
    optional). The top level is either the event map directly, or an
    object with a "hooks" key holding it; only capitalised keys count as
    event names, per the plan brief's exact list (SessionStart,
    PreToolUse, and so on). A malformed file is recorded into
    `unreadable` and treated as zero events, never a crash."""
    if not os.path.isfile(hooks_path):
        return []
    data, err = _read_json_file(hooks_path)
    if err:
        unreadable.append({"path": hooks_path, "reason": err})
        return []
    if not isinstance(data, dict):
        unreadable.append({"path": hooks_path,
                            "reason": "hooks.json root is not a JSON object"})
        return []
    event_map = data.get("hooks") if isinstance(data.get("hooks"), dict) else data
    events = sorted(
        key for key in event_map.keys()
        if isinstance(key, str) and key[:1].isupper()
    )
    return events


# ---------------------------------------------------------------------------
# The surfaces. Each returns its slice of the inventory plus appends any
# read failures to the shared `unreadable` list. None of these raise: a
# failure inside one surface degrades that surface, never the whole run.
# ---------------------------------------------------------------------------

def _collect_plugins(home, home_real, unreadable):
    """(marketplaces, plugins, ok). ok is False only if the marketplaces
    cache directory itself exists but could not be listed."""
    cache_dir = os.path.join(home, ".claude", "plugins", "cache")
    marketplace_entries, ok = _safe_listdir(cache_dir, home_real, unreadable)

    marketplaces = []
    plugins = []
    for mkt_name, mkt_path in marketplace_entries:
        plugin_entries, _ok = _safe_listdir(mkt_path, home_real, unreadable)
        marketplaces.append({"name": mkt_name, "plugin_count": len(plugin_entries)})

        for plugin_name, plugin_path in plugin_entries:
            version_entries, _ok = _safe_listdir(plugin_path, home_real, unreadable)
            for version_name, version_path in version_entries:
                manifest_path = os.path.join(
                    version_path, ".claude-plugin", "plugin.json")
                manifest_present = os.path.isfile(manifest_path)
                manifest_data = None
                if manifest_present:
                    manifest_data, m_err = _read_json_file(manifest_path)
                    if m_err:
                        unreadable.append({"path": manifest_path, "reason": m_err})
                    if not isinstance(manifest_data, dict):
                        manifest_data = None

                name = (manifest_data or {}).get("name") or plugin_name
                version = (manifest_data or {}).get("version") or version_name
                description = (manifest_data or {}).get("description") \
                    if manifest_data else None
                hooks_path = os.path.join(version_path, "hooks", "hooks.json")
                hook_events = _parse_hook_events(hooks_path, unreadable)

                plugins.append({
                    "name": name,
                    "marketplace": mkt_name,
                    "version": version,
                    "path": version_path,
                    "enabled": None,  # filled in by _apply_enabled() below
                    "hook_events": hook_events,
                    "manifest_present": manifest_present,
                    "description": description,
                })
    return marketplaces, plugins, ok


def _collect_skills(home, home_real, unreadable):
    """(skills, ok). ok is False only if the skills directory itself
    exists but could not be listed."""
    skills_dir = os.path.join(home, ".claude", "skills")
    entries, ok = _safe_listdir(skills_dir, home_real, unreadable)
    skills = []
    for skill_name, skill_path in entries:
        has_skill_md = os.path.isfile(os.path.join(skill_path, "SKILL.md"))
        hooks_path = os.path.join(skill_path, "hooks", "hooks.json")
        hook_events = _parse_hook_events(hooks_path, unreadable)
        skills.append({
            "name": skill_name,
            "path": skill_path,
            "has_skill_md": has_skill_md,
            "hook_events": hook_events,
        })
    return skills, ok


def _collect_mcp_servers(home, unreadable):
    """(mcp_servers, ok). Only `mcpServers`' KEYS are kept; the rest of
    .claude.json is discarded immediately, since that file is large and
    carries unrelated keys (module docstring, hard constraint). A missing
    or unparsable file is unreadable (ok=False); a valid file that simply
    lacks the mcpServers key is zero servers, not an error."""
    path = os.path.join(home, ".claude.json")
    if not os.path.isfile(path):
        unreadable.append({"path": path,
                            "reason": _describe_unreadable_file(path)})
        return [], False
    data, err = _read_json_file(path)
    if err:
        unreadable.append({"path": path, "reason": err})
        return [], False
    servers_map = data.get("mcpServers") if isinstance(data, dict) else None
    data = None  # drop the rest of the parsed file now that the key is taken
    if isinstance(servers_map, dict):
        return [{"name": key} for key in sorted(servers_map.keys())], True
    return [], True


def _load_user_settings(home, unreadable):
    """(settings_data_or_None, ok). settings_data is None whenever the
    file could not be read at all (missing or invalid), which is exactly
    the condition under which plugin `enabled` must report null rather
    than false, per the contract."""
    path = os.path.join(home, ".claude", "settings.json")
    if not os.path.isfile(path):
        unreadable.append({"path": path,
                            "reason": _describe_unreadable_file(path)})
        return None, False
    data, err = _read_json_file(path)
    if err:
        unreadable.append({"path": path, "reason": err})
        return None, False
    return data, True


def _apply_enabled(plugins, settings_data):
    """Fill each plugin's "enabled" field in place. null (None) means
    settings.json could not be read at all (could-not-tell); false means
    it WAS read and the plugin's "<name>@<marketplace>" key is simply
    absent from enabledPlugins (a fact). These two are never conflated."""
    if settings_data is None:
        for plugin in plugins:
            plugin["enabled"] = None
        return
    enabled_map = settings_data.get("enabledPlugins")
    if not isinstance(enabled_map, dict):
        enabled_map = {}
    for plugin in plugins:
        key = "%s@%s" % (plugin["name"], plugin["marketplace"])
        plugin["enabled"] = bool(enabled_map.get(key, False))


def _user_hook_commands(settings_data):
    """{event: count of hook commands}, read from user settings.json's
    "hooks" key, shape {event: [ {..., "hooks": [ {"command": ...}, ...] },
    ...]}. Empty dict if settings_data is None or carries no hooks key."""
    counts = {}
    if not isinstance(settings_data, dict):
        return counts
    hooks_key = settings_data.get("hooks")
    if not isinstance(hooks_key, dict):
        return counts
    for event, matchers in hooks_key.items():
        if not isinstance(matchers, list):
            continue
        count = 0
        for matcher in matchers:
            if isinstance(matcher, dict) and isinstance(matcher.get("hooks"), list):
                count += len(matcher["hooks"])
        counts[event] = count
    return counts


def _settings_layers(home, root):
    user_path = os.path.join(home, ".claude", "settings.json")
    project_path = os.path.join(root, ".claude", "settings.json")
    project_local_path = os.path.join(root, ".claude", "settings.local.json")
    return [
        {"path": user_path, "kind": "user", "exists": os.path.isfile(user_path)},
        {"path": project_path, "kind": "project",
         "exists": os.path.isfile(project_path)},
        {"path": project_local_path, "kind": "project-local",
         "exists": os.path.isfile(project_local_path)},
    ]


# ---------------------------------------------------------------------------
# Assembly.
# ---------------------------------------------------------------------------

def build_inventory(home, root):
    """(data, overall_ok). `data` always has every documented top-level
    key, even when overall_ok is False, so a caller can still inspect
    `unreadable` for the reasons. overall_ok is False only when all four
    core surfaces (marketplaces cache, user settings.json, skills
    directory, .claude.json) could not be read; a missing-but-legitimately-
    empty surface never counts against it."""
    home_real = os.path.realpath(home)
    unreadable = []

    marketplaces, plugins, ok_marketplaces = _collect_plugins(
        home, home_real, unreadable)
    skills, ok_skills = _collect_skills(home, home_real, unreadable)
    mcp_servers, ok_mcp = _collect_mcp_servers(home, unreadable)
    settings_data, ok_settings = _load_user_settings(home, unreadable)

    _apply_enabled(plugins, settings_data)
    user_hook_commands = _user_hook_commands(settings_data)
    settings_layers = _settings_layers(home, root)

    data = {
        "schema": 1,
        "home": home,
        "root": root,
        "marketplaces": marketplaces,
        "plugins": plugins,
        "skills": skills,
        "mcp_servers": mcp_servers,
        "settings_layers": settings_layers,
        "user_hook_commands": user_hook_commands,
        "unreadable": unreadable,
    }
    overall_ok = ok_marketplaces or ok_settings or ok_skills or ok_mcp
    return data, overall_ok


# ---------------------------------------------------------------------------
# Human readable rendering for the `inventory` verb.
# ---------------------------------------------------------------------------

def render_inventory(data):
    lines = []

    marketplaces = data["marketplaces"]
    lines.append("MARKETPLACES (%d)" % len(marketplaces))
    for mkt in marketplaces:
        lines.append("  %s (%d plugins)" % (mkt["name"], mkt["plugin_count"]))

    plugins = data["plugins"]
    lines.append("")
    lines.append("PLUGINS (%d)" % len(plugins))
    for plugin in plugins:
        if plugin["enabled"] is True:
            status = "ENABLED"
        elif plugin["enabled"] is False:
            status = "NOT-ENABLED"
        else:
            status = "ENABLED-UNKNOWN"
        events = ",".join(plugin["hook_events"]) if plugin["hook_events"] else "none"
        lines.append("  %s @ %s v%s [%s] hooks: %s" % (
            plugin["name"], plugin["marketplace"], plugin["version"],
            status, events))

    skills = data["skills"]
    lines.append("")
    lines.append("SKILLS (%d)" % len(skills))
    for skill in skills:
        md = "has SKILL.md" if skill["has_skill_md"] else "no SKILL.md"
        events = ",".join(skill["hook_events"]) if skill["hook_events"] else "none"
        lines.append("  %s [%s] hooks: %s" % (skill["name"], md, events))

    mcp_servers = data["mcp_servers"]
    lines.append("")
    lines.append("MCP SERVERS (%d)" % len(mcp_servers))
    for server in mcp_servers:
        lines.append("  %s" % server["name"])

    lines.append("")
    lines.append("SETTINGS LAYERS")
    for layer in data["settings_layers"]:
        state = "present" if layer["exists"] else "absent"
        lines.append("  %s: %s [%s]" % (layer["kind"], layer["path"], state))
    hook_counts = data["user_hook_commands"]
    if hook_counts:
        counts_text = ", ".join(
            "%s=%d" % (event, hook_counts[event]) for event in sorted(hook_counts))
    else:
        counts_text = "none"
    lines.append("  user hook commands: %s" % counts_text)

    unreadable = data["unreadable"]
    lines.append("")
    lines.append("UNREADABLE (%d)" % len(unreadable))
    for entry in unreadable:
        lines.append("  %s: %s" % (entry["path"], entry["reason"]))

    not_enabled = sum(1 for p in plugins if p["enabled"] is False)
    lines.append("")
    lines.append(
        "SUMMARY: %d marketplaces, %d plugins (%d not enabled), %d skills, "
        "%d mcp servers, %d unreadable surfaces." % (
            len(marketplaces), len(plugins), not_enabled, len(skills),
            len(mcp_servers), len(unreadable)))

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Conflict detection (F2). See the module docstring's CONFLICT CLASSES
# section for the override contract. The default table below is the exact
# content of tools/toolkit_conflict_classes.json, embedded as JSON text and
# parsed once at import time: decision 34 requires the shipped defaults to
# live IN this file, and parsing the real JSON text (rather than hand
# transcribing it into a Python literal) is the one way to guarantee the
# two never drift apart by a typo.
# ---------------------------------------------------------------------------

_DEFAULT_CONFLICT_CLASSES_JSON = r"""
{
  "schema": 1,
  "_comment": "The conflict classes tools/bm_toolkit.py checks for, their severities, and a real fixture for each. FOUNDER-EDITABLE BY DESIGN (decision 6 of the toolkit ratification): severity is a judgement about how a particular team works, not a property of the code, so it lives here where a change is a one-line diff rather than an edit to a checker. Three severities and nothing else: info, warn, fail. A class whose surface cannot be read reports NO-DATA and is never silently omitted, because a check that cannot tell must not read as a pass. Every fixture below was MEASURED on the founder's machine on 2026-08-12 by walking ~/.claude/plugins/cache/*/*/*/hooks/hooks.json and ~/.claude/settings.json; none is invented, and a fixture that stops reproducing is a finding about the machine rather than a reason to delete the class.",
  "severities": {
    "info": "Worth knowing. Two capabilities overlap in a way that is usually deliberate.",
    "warn": "Worth acting on. Two capabilities can produce different answers to the same question, and nothing decides which wins.",
    "fail": "Worth stopping for. Two capabilities claim the same authority over state, so one of them is silently losing."
  },
  "classes": [
    {
      "id": "multi-stop-hook",
      "title": "More than one capability registers a Stop hook",
      "severity": "warn",
      "why": "A Stop hook decides what happens when the model tries to finish. Several of them run, in an order nothing here documents, and each may block, warn, or rewrite the ending. A user who sees one of them fire has no way to know which capability spoke.",
      "detect": "count distinct plugins whose hooks.json declares the Stop event",
      "threshold": 2,
      "fixture_2026_08_12": {
        "count": 7,
        "members": ["brotherme@brotherme-marketplace", "brothersbe@brothersbe", "hookify@claude-plugins-official", "ralph-loop@claude-plugins-official", "security-guidance@claude-plugins-official", "slop-gate@claude-community", "ultrapowers@claude-community"]
      },
      "remedy_shape": "claude plugin disable <plugin>@<marketplace>, for the ones whose Stop behaviour you do not want"
    },
    {
      "id": "multi-pretooluse-blocker",
      "title": "More than one capability can refuse a tool call",
      "severity": "warn",
      "why": "A PreToolUse hook can block. When several can, a refusal arrives with no indication of which one refused, and two of them disagreeing is undefined behaviour rather than a decision. This is the class where the machine-wide settings layer matters as much as the plugins: the founder's own spend guard and session cap sit here too, and they are meant to.",
      "detect": "count plugin registrations of PreToolUse, plus hook commands under PreToolUse in every settings layer, and report the two counts separately",
      "threshold": 2,
      "fixture_2026_08_12": {
        "plugin_registrations": 8,
        "distinct_plugins": 7,
        "settings_commands": 2,
        "total_layers": 10,
        "note": "8 registrations from 7 distinct plugins because brothersbe is cached at two versions; the 2 settings commands are the founder's spend guard and session cap, which are deliberate"
      },
      "remedy_shape": "read the layers in order and decide which are deliberate; the settings-layer ones usually are"
    },
    {
      "id": "multi-version-cached",
      "title": "One capability is present at more than one version",
      "severity": "fail",
      "why": "Version is part of identity. Two versions of one plugin cached together means any statement about what that plugin does is ambiguous, and a capability record describing one of them does not describe the other. This is the class behind the failure where a command line tool ran two major versions behind what was installed, and the missing command was reported as a product defect when it was an install defect.",
      "detect": "group cached plugin directories by marketplace and plugin name; more than one version directory is a finding",
      "threshold": 2,
      "fixture_2026_08_12": {
        "count": 1,
        "members": ["brothersbe@brothersbe at 1.0.0-rc.1 and 1.0.0-rc.38"]
      },
      "remedy_shape": "remove the stale version directory, or reinstall to pin one"
    },
    {
      "id": "multi-memory-authority",
      "title": "More than one capability claims to be the memory",
      "severity": "fail",
      "why": "Two systems that both believe they hold the session's history will disagree, and nothing arbitrates. Worse, at least one known memory plugin documents assuming exclusive hook access, so its correctness depends on being alone. BrotherMode's own position is settled: the store is the sole authority for delivery state and the Obsidian vault is the knowledge backbone, so any other memory system is a guest that must be routed read-only.",
      "detect": "capabilities registering three or more of SessionStart, UserPromptSubmit, PostToolUse, Stop, SessionEnd AND declaring a persistent store of their own",
      "threshold": 2,
      "known_members": ["claude-mem registers five hooks and keeps its own SQLite through a local worker service, and its documentation assumes exclusive hook access", "claude-cortex writes into the same per-project memory directory tree the harness's own auto-memory uses"],
      "fixture_2026_08_12": {
        "count": 0,
        "note": "neither is installed on this machine today; the class ships with named members so it fires the day one arrives, rather than being written after the collision"
      },
      "remedy_shape": "pick one authority for delivery state and route the others read-only"
    },
    {
      "id": "state-namespace-collision",
      "title": "Two capabilities own overlapping project state directories",
      "severity": "warn",
      "why": "A capability that owns a directory of project state expects to be the only writer of it. Two of them in one repository produce a state file whose history has two authors and no merge rule.",
      "detect": "compare each installed capability's declared state namespace against the others and against the project tree",
      "threshold": 2,
      "known_namespaces": {
        "gsd": ".planning/ holding STATE.md, ROADMAP.md, REQUIREMENTS.md, plus .gsd-backups/",
        "arc": ".arc/log.md and docs/arc/",
        "compound-engineering": "docs/solutions/ and docs/plans/, relocatable",
        "brothermode": ".brothermode/ and STATE.md",
        "bmad": "UNCONFIRMED, which is why the route to it ships disabled until a repository-tree read settles it"
      },
      "remedy_shape": "relocate the movable one, or scope one capability to a different project"
    },
    {
      "id": "definition-of-done-collision",
      "title": "More than one capability defines when work is finished",
      "severity": "warn",
      "why": "This is the one that matters most to a delivery product, because it is the question BrotherMode exists to answer. Several installed capabilities carry their own completion rule, and a user following two of them can satisfy one while failing the other. BrotherMode's position is settled and is not a compromise: its own rerun after the last edit closes the work, and every other definition is recorded as claimed output.",
      "detect": "count capabilities shipping a completion or verification gate",
      "threshold": 2,
      "fixture_2026_08_12": {
        "count": 5,
        "members": ["superpowers verification-before-completion", "ultrapowers verification-before-completion", "brothermode definition-of-done", "brothersbe evidence receipts", "slop-gate premature-completion detection"]
      },
      "remedy_shape": "none needed inside BrotherMode: its rerun is the closing authority and the others are recorded, not obeyed. The finding exists so a user knows why two tools disagree."
    },
    {
      "id": "duplicate-planning-workflow",
      "title": "Several capabilities offer a planning workflow",
      "severity": "info",
      "why": "Overlap here is usually deliberate and often useful; a person picks the planner that fits the work. It is info rather than warn because nothing breaks, and the cost is only a user wondering which to use.",
      "detect": "count capabilities exposing a plan or spec authoring command",
      "threshold": 3,
      "fixture_2026_08_12": {
        "count": 5,
        "members": ["superpowers writing-plans", "ultrapowers planner", "ultraplan", "mattpocock to-spec", "feature-dev"]
      },
      "remedy_shape": "none; the routing table names which one a task class prefers"
    },
    {
      "id": "installed-not-enabled",
      "title": "A capability is cached but not enabled",
      "severity": "info",
      "why": "Its files are on disk and its hooks are not running. Harmless, and worth reporting because it is the most common explanation for a capability that somebody believes is active and is not.",
      "detect": "a cached plugin directory whose name@marketplace is absent from enabledPlugins in the user settings",
      "threshold": 1,
      "remedy_shape": "claude plugin enable <plugin>@<marketplace>, or remove the cache directory"
    },
    {
      "id": "scope-split",
      "title": "The same capability is configured at more than one scope",
      "severity": "warn",
      "why": "A capability enabled globally and configured per project can behave differently depending on which directory a session started in, which is the hardest class of surprise to diagnose because the tool is behaving correctly in both.",
      "detect": "compare capability presence across the user settings layer, the project settings layer, and the project local layer",
      "threshold": 2,
      "remedy_shape": "pick one scope; state which in the project README so a new person does not rediscover it"
    },
    {
      "id": "undeclared-network-or-credential-reach",
      "title": "A capability reaches the network or a credential without saying so",
      "severity": "fail",
      "why": "Two proven incidents on this machine: a local proxy defaulted to listening on every network interface with no authentication when its token was empty, which was the default; and a token-saving hook returned allow on everything it wrapped, which would have auto-approved reading any file including private keys and environment files. Neither was a bug. Each was a tool behaving as documented, trusted more than it had earned.",
      "detect": "static scan of a capability's own scripts for network and credential-shaped references, compared against what its capability record declares",
      "threshold": 1,
      "limits": "DECLARED reach only. This class reads what a capability's files say, never what a running process does. It cannot see syscalls, traffic, or reads that leave no artifact, and any claim otherwise about this checker is wrong.",
      "remedy_shape": "declare the reach in the capability record, or quarantine the capability until somebody does"
    }
  ]
}
"""

DEFAULT_CONFLICT_DATA = json.loads(_DEFAULT_CONFLICT_CLASSES_JSON)
DEFAULT_CONFLICT_CLASSES = DEFAULT_CONFLICT_DATA["classes"]

_REQUIRED_CLASS_KEYS = ("id", "title", "severity", "detect", "threshold")
_VALID_SEVERITIES = ("info", "warn", "fail")


def _validate_classes_shape(data):
    """(True, None) or (False, reason). Checked before an override JSON is
    trusted: a malformed override must be refused BY NAME, never trusted
    half-parsed and never silently substituted for a class this module
    knows how to render."""
    if not isinstance(data, dict):
        return False, "root is not a JSON object"
    classes = data.get("classes")
    if not isinstance(classes, list) or not classes:
        return False, '"classes" key is missing or not a non-empty list'
    for entry in classes:
        if not isinstance(entry, dict):
            return False, "a classes entry is not a JSON object"
        missing = [key for key in _REQUIRED_CLASS_KEYS if key not in entry]
        if missing:
            return False, "classes entry %r missing keys: %s" % (
                entry.get("id", "?"), ", ".join(missing))
        if entry["severity"] not in _VALID_SEVERITIES:
            return False, "classes entry %s has unknown severity %r" % (
                entry["id"], entry["severity"])
    return True, None


def load_conflict_classes(explicit_path):
    """(classes, source, override_error). `source` is "default" or the path
    actually used. An explicit --classes path that is missing or malformed
    is refused BY NAME: `override_error` names the path and the reason, and
    `classes` still falls back to DEFAULT_CONFLICT_CLASSES so the run never
    goes classless (decision 34). The shipped override path
    (tools/toolkit_conflict_classes.json next to this file) is optional:
    its plain absence, with no explicit --classes given, is not an error,
    only silence, same as every other optional surface in this module."""
    path = explicit_path or os.path.join(HERE, "toolkit_conflict_classes.json")
    if not os.path.isfile(path):
        if explicit_path:
            return DEFAULT_CONFLICT_CLASSES, "default", "%s: missing file" % path
        return DEFAULT_CONFLICT_CLASSES, "default", None
    data, err = _read_json_file(path)
    if err:
        return DEFAULT_CONFLICT_CLASSES, "default", "%s: %s" % (path, err)
    ok, reason = _validate_classes_shape(data)
    if not ok:
        return DEFAULT_CONFLICT_CLASSES, "default", "%s: %s" % (path, reason)
    return data["classes"], path, None


# --- per-class detectors ----------------------------------------------------
# Each detector takes (inventory_data, class_def) and returns
# (count, detail, ok, reason). ok=False means the surface this class needs
# could not be read (NO-DATA for this class alone, never the whole run);
# `reason` names why. A class id with no entry in CLASS_DETECTORS below has
# no mechanical detector at all (its `detect` field needs an artifact this
# module does not inventory, e.g. a static code scan or cross-repository
# state), which is also reported as NO-DATA, named, rather than dropped.

def _detect_multi_stop_hook(data, cls):
    members = sorted(set(
        "%s@%s" % (p["name"], p["marketplace"])
        for p in data["plugins"] if "Stop" in p["hook_events"]))
    return len(members), {"members": members}, True, None


def _detect_multi_pretooluse_blocker(data, cls):
    registrants = [p for p in data["plugins"] if "PreToolUse" in p["hook_events"]]
    plugin_registrations = len(registrants)
    distinct_plugins = len(set(p["name"] for p in registrants))
    settings_commands = data["user_hook_commands"].get("PreToolUse", 0)
    detail = {
        "plugin_registrations": plugin_registrations,
        "distinct_plugins": distinct_plugins,
        "settings_commands": settings_commands,
        "members": sorted(set(
            "%s@%s" % (p["name"], p["marketplace"]) for p in registrants)),
    }
    return plugin_registrations + settings_commands, detail, True, None


def _detect_multi_version_cached(data, cls):
    # `count` here is the WORST offender's version count (max versions
    # cached for any one plugin), not the number of offending plugins: the
    # class's own detect text ("more than one version directory is a
    # finding") and its 2026-08-12 fixture (one offending plugin, severity
    # fail, no "wait for a second one" language) both treat a single
    # two-version plugin as already worth firing. Any offender therefore
    # has at least 2 versions, so it reaches threshold 2 the moment it
    # exists, matching that intent.
    groups = {}
    for p in data["plugins"]:
        groups.setdefault((p["marketplace"], p["name"]), []).append(p["version"])
    members = []
    worst = 0
    for (mkt, name), versions in sorted(groups.items()):
        if len(versions) > 1:
            members.append("%s@%s at %s" % (name, mkt, " and ".join(sorted(versions))))
            worst = max(worst, len(versions))
    return worst, {"members": members}, True, None


def _detect_installed_not_enabled(data, cls):
    members = sorted(
        "%s@%s" % (p["name"], p["marketplace"])
        for p in data["plugins"] if p["enabled"] is False)
    return len(members), {"members": members}, True, None


# ponytail: multi-memory-authority's own `detect` text needs "declaring a
# persistent store of their own", which no surface in this inventory
# records (nothing here reads what a plugin's code does with disk). A
# hook-event-breadth stand-in was tried and dropped: on the real machine it
# threw FAIL on five plugins that keep no store at all, and a wrong FAIL at
# "worth stopping for" severity is worse than an honest NO-DATA. It falls
# through to the no-detector path below on purpose. Upgrade path: TK3
# capability records, if they end up declaring storage explicitly.

CLASS_DETECTORS = {
    "multi-stop-hook": _detect_multi_stop_hook,
    "multi-pretooluse-blocker": _detect_multi_pretooluse_blocker,
    "multi-version-cached": _detect_multi_version_cached,
    "installed-not-enabled": _detect_installed_not_enabled,
}


def build_conflicts(inventory_data, classes):
    """[result, ...], one per class in `classes`, in the given order.
    Each result: {id, title, severity, status, count, threshold, detail,
    reason}. status is one of "fired" (count >= threshold), "clear" (count
    < threshold), or "no_data" (reason names why: either the detector
    itself could not read its surface, or this class has no detector)."""
    results = []
    for cls in classes:
        detector = CLASS_DETECTORS.get(cls.get("id"))
        if detector is None:
            results.append({
                "id": cls.get("id"), "title": cls.get("title"),
                "severity": cls.get("severity"), "status": "no_data",
                "count": None, "threshold": cls.get("threshold"),
                "detail": None,
                "reason": "no mechanical detector for this class; detect: %s"
                          % cls.get("detect", "(not stated)"),
            })
            continue
        count, detail, ok, reason = detector(inventory_data, cls)
        if not ok:
            results.append({
                "id": cls.get("id"), "title": cls.get("title"),
                "severity": cls.get("severity"), "status": "no_data",
                "count": None, "threshold": cls.get("threshold"),
                "detail": None, "reason": reason,
            })
            continue
        threshold = cls.get("threshold", 1)
        status = "fired" if count >= threshold else "clear"
        results.append({
            "id": cls.get("id"), "title": cls.get("title"),
            "severity": cls.get("severity"), "status": status,
            "count": count, "threshold": threshold,
            "detail": detail, "reason": None,
        })
    return results


def render_conflicts(results):
    fired = [r for r in results if r["status"] == "fired"]
    clear = [r for r in results if r["status"] == "clear"]
    no_data = [r for r in results if r["status"] == "no_data"]

    lines = []
    lines.append("CONFLICTS FOUND (%d)" % len(fired))
    for r in fired:
        lines.append("  [%s] %s: %s (count=%s threshold=%s)" % (
            r["severity"].upper(), r["id"], r["title"], r["count"], r["threshold"]))
        members = (r["detail"] or {}).get("members") or []
        for member in members:
            lines.append("    - %s" % member)

    lines.append("")
    lines.append("NO-DATA (%d)" % len(no_data))
    for r in no_data:
        lines.append("  %s: %s" % (r["id"], r["reason"]))

    lines.append("")
    lines.append("CLEAR (%d)" % len(clear))
    for r in clear:
        lines.append("  %s (count=%s threshold=%s)" % (
            r["id"], r["count"], r["threshold"]))

    lines.append("")
    lines.append(
        "SUMMARY: %d classes checked, %d fired, %d clear, %d no-data." % (
            len(results), len(fired), len(clear), len(no_data)))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Capability records (F3). See the module docstring's CAPABILITY RECORDS
# section for the shape and the derived-versus-hand-asserted contract.
# ---------------------------------------------------------------------------

_REQUIRED_OVERRIDE_KEYS = ("name", "kind")


def _validate_overrides_shape(data):
    """(True, None) or (False, reason). Checked before an override JSON is
    trusted, same discipline as _validate_classes_shape: a malformed
    override must be refused BY NAME, never trusted half-parsed."""
    if not isinstance(data, dict):
        return False, "root is not a JSON object"
    entries = data.get("records")
    if not isinstance(entries, list):
        return False, '"records" key is missing or not a list'
    for entry in entries:
        if not isinstance(entry, dict):
            return False, "a records entry is not a JSON object"
        missing = [key for key in _REQUIRED_OVERRIDE_KEYS if key not in entry]
        if missing:
            return False, "records entry %r missing keys: %s" % (
                entry.get("name", "?"), ", ".join(missing))
    return True, None


def load_capability_overrides(explicit_path):
    """(overrides, source, override_error). `overrides` is the raw list of
    dicts a human typed into tools/toolkit_capability_overrides.json (or an
    explicit --overrides path): hand-asserted capability claims for
    something this inventory cannot derive from artifacts on its own.
    Unlike conflict classes there is no shipped default table here: a
    hand-asserted record only exists when a human wrote one, so plain
    absence (no explicit path given, the shipped path missing) is silence,
    not an error, same as every other optional surface in this module. An
    explicit --overrides path that is missing or malformed is refused BY
    NAME and the run falls back to zero overrides, never crashes and never
    trusts a half-parsed file."""
    path = explicit_path or os.path.join(
        HERE, "toolkit_capability_overrides.json")
    if not os.path.isfile(path):
        if explicit_path:
            return [], "default", "%s: missing file" % path
        return [], "default", None
    data, err = _read_json_file(path)
    if err:
        return [], "default", "%s: %s" % (path, err)
    ok, reason = _validate_overrides_shape(data)
    if not ok:
        return [], "default", "%s: %s" % (path, reason)
    return data["records"], path, None


def build_capability_records(data, overrides):
    """[record, ...]: one DERIVED record per plugin, per skill, per MCP
    server in `data` (built straight from the same fields build_inventory
    already parsed, no new artifact reads), followed by one HAND-ASSERTED
    record per entry in `overrides`. Each record: {id, kind, name,
    marketplace, version, declared_reach, source_files, hand_asserted}.
    `source_files` for a derived record is never empty: the capability's
    own directory (or, for an MCP server, .claude.json) is always first.
    `source_files` for a hand-asserted record is always empty: nothing was
    read to build it, which is exactly what hand-asserted means."""
    records = []

    for p in data["plugins"]:
        source_files = [p["path"]]
        if p["manifest_present"]:
            source_files.append(
                os.path.join(p["path"], ".claude-plugin", "plugin.json"))
        hooks_path = os.path.join(p["path"], "hooks", "hooks.json")
        if os.path.isfile(hooks_path):
            source_files.append(hooks_path)
        records.append({
            "id": "%s@%s" % (p["name"], p["marketplace"]),
            "kind": "plugin",
            "name": p["name"],
            "marketplace": p["marketplace"],
            "version": p["version"],
            "declared_reach": {"hook_events": p["hook_events"]},
            "source_files": source_files,
            "hand_asserted": False,
        })

    for s in data["skills"]:
        source_files = [s["path"]]
        if s["has_skill_md"]:
            source_files.append(os.path.join(s["path"], "SKILL.md"))
        hooks_path = os.path.join(s["path"], "hooks", "hooks.json")
        if os.path.isfile(hooks_path):
            source_files.append(hooks_path)
        records.append({
            "id": "skill:%s" % s["name"],
            "kind": "skill",
            "name": s["name"],
            "marketplace": None,
            "version": None,
            "declared_reach": {"hook_events": s["hook_events"]},
            "source_files": source_files,
            "hand_asserted": False,
        })

    if data["mcp_servers"]:
        mcp_source = os.path.join(data["home"], ".claude.json")
        for m in data["mcp_servers"]:
            records.append({
                "id": "mcp:%s" % m["name"],
                "kind": "mcp_server",
                "name": m["name"],
                "marketplace": None,
                "version": None,
                "declared_reach": {"registered": True},
                "source_files": [mcp_source],
                "hand_asserted": False,
            })

    for entry in overrides:
        kind = entry.get("kind")
        name = entry.get("name")
        records.append({
            "id": entry.get("id") or "%s:%s" % (kind, name),
            "kind": kind,
            "name": name,
            "marketplace": entry.get("marketplace"),
            "version": entry.get("version"),
            "declared_reach": entry.get("declared_reach") or {},
            "source_files": [],
            "hand_asserted": True,
        })

    return records


def render_capabilities(records):
    def _reach_text(record):
        reach = record["declared_reach"] or {}
        if not reach:
            return "none"
        return ", ".join(
            "%s=%s" % (key, reach[key]) for key in sorted(reach))

    derived = [r for r in records if not r["hand_asserted"]]
    hand_asserted = [r for r in records if r["hand_asserted"]]

    lines = []
    lines.append("DERIVED CAPABILITY RECORDS (%d)" % len(derived))
    for r in derived:
        lines.append("  %s [%s] declared_reach: %s" % (
            r["id"], r["kind"], _reach_text(r)))
        lines.append("    source: %s" % ", ".join(r["source_files"]))

    lines.append("")
    lines.append("HAND-ASSERTED CAPABILITY RECORDS (%d)" % len(hand_asserted))
    for r in hand_asserted:
        lines.append("  [HAND-ASSERTED] %s [%s] declared_reach: %s" % (
            r["id"], r["kind"], _reach_text(r)))

    lines.append("")
    lines.append(
        "SUMMARY: %d records, %d derived, %d hand-asserted." % (
            len(records), len(derived), len(hand_asserted)))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI.
# ---------------------------------------------------------------------------

def _parse_argv(argv):
    """Return (verb, home, root, classes, overrides, error). `error` set
    means stop and report a plain usage failure (exit 2, no "NO-DATA:"
    prefix: that prefix is reserved for "could not determine the verdict",
    not "bad arguments"). `classes` (--classes PATH) is only consumed by
    the `conflicts` verb; `overrides` (--overrides PATH) is only consumed
    by the `capabilities` verb; every other verb accepts and ignores
    whichever of the two it is not given, the same as it would any other
    unused-but-recognised flag."""
    args = list(argv)
    verb = "inventory"
    if args and not args[0].startswith("--"):
        verb = args.pop(0)
    if verb not in _VERBS:
        return None, None, None, None, None, "bm_toolkit: unknown verb: %s" % verb

    home = None
    root = None
    classes = None
    overrides = None
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--home":
            if i + 1 >= len(args):
                return None, None, None, None, None, "bm_toolkit: --home requires a value"
            home = args[i + 1]
            i += 2
        elif arg == "--root":
            if i + 1 >= len(args):
                return None, None, None, None, None, "bm_toolkit: --root requires a value"
            root = args[i + 1]
            i += 2
        elif arg == "--classes":
            if i + 1 >= len(args):
                return None, None, None, None, None, "bm_toolkit: --classes requires a value"
            classes = args[i + 1]
            i += 2
        elif arg == "--overrides":
            if i + 1 >= len(args):
                return None, None, None, None, None, "bm_toolkit: --overrides requires a value"
            overrides = args[i + 1]
            i += 2
        else:
            return None, None, None, None, None, "bm_toolkit: unknown argument: %s" % arg
    return verb, home, root, classes, overrides, None


def _run(argv):
    """The real body of main, split out so `main` can wrap the whole thing
    in one try/except and guarantee NO-DATA on any unexpected exception."""
    verb, home_arg, root_arg, classes_arg, overrides_arg, err = _parse_argv(argv)
    if err:
        sys.stderr.write(err + "\n")
        return 2

    home, reason = resolve_home(home_arg)
    if home is None:
        sys.stdout.write("NO-DATA: %s\n" % reason)
        return 2
    root = resolve_root(root_arg)

    data, overall_ok = build_inventory(home, root)
    if not overall_ok:
        sys.stdout.write(
            "NO-DATA: every capability surface under %s was unreadable\n"
            % home)
        return 2

    if verb == "json":
        sys.stdout.write(json.dumps(data) + "\n")
    elif verb == "conflicts":
        classes, _source, override_error = load_conflict_classes(classes_arg)
        results = build_conflicts(data, classes)
        out = []
        if override_error:
            out.append(
                "OVERRIDE REFUSED: %s (using shipped default classes)"
                % override_error)
            out.append("")
        out.append(render_conflicts(results))
        sys.stdout.write("\n".join(out) + "\n")
    elif verb == "capabilities":
        overrides, _source, override_error = load_capability_overrides(
            overrides_arg)
        records = build_capability_records(data, overrides)
        out = []
        if override_error:
            out.append(
                "OVERRIDE REFUSED: %s (using zero hand-asserted records)"
                % override_error)
            out.append("")
        out.append(render_capabilities(records))
        sys.stdout.write("\n".join(out) + "\n")
    else:
        sys.stdout.write(render_inventory(data) + "\n")
    return 0


def main(argv):
    try:
        return _run(argv)
    except Exception as exc:
        sys.stdout.write("NO-DATA: %s: %s\n" % (type(exc).__name__, exc))
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
