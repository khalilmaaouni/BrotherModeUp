#!/usr/bin/env python3
"""rehearse_fresh_install.py: the fresh-HOME install rehearsal, run for real.

WHY THIS EXISTS (Loop 3 design D-6, docs/superpowers/specs/2026-08-01-
loop3-consent-install-design.md, work package WP-F)
  The program gate is "fresh-machine install without developer help". This
  file is the one scripted rehearsal of that gate on this machine: it drives
  the CLONE-path story end to end, exactly as docs/QUICKSTART.md and
  docs/SETUP.md tell a stranger to do it, inside temporary directories with
  HOME and BROTHERME_CONFIG overridden so the real HOME and the real
  ~/.claude are never touched.

WHAT "CLONE" MEANS HERE, DISCLOSED
  Step 1 copies this repository's working tree into a fake
  ~/.claude/skills/brothermode instead of running `git clone`. That is a
  disclosed stand-in, not the real command: the docs' own clone step pulls a
  tagged release over the network from GitHub, and running that here would
  test GitHub and the network, not this machine's install code. The copy
  excludes .git, .brothermode, and node_modules, the same exclusion list
  scripts/checksums.sh and scripts/verify-install.sh already use for the same
  reason. Every other step below runs the actual project scripts against the
  fake HOME: scripts/install.py, scripts/setup.py, scripts/doctor.py,
  tools/bm_project.py, and scripts/uninstall.py, none of them simulated.

THE SEVEN STEPS
  1. copy (stands in for git clone) into fakehome/.claude/skills/brothermode
  2. python3 tools/test_all.py from the copy (skippable with --skip-gate for
     time; the default runs it)
  3. scripts/install.py, dry-run then real, against a fake settings.json
  4. scripts/setup.py flag mode consent, plus the vault-template copy
     docs/SETUP.md Step 3 documents (needed for doctor's vault check to have
     a real directory to check)
  5. scripts/doctor.py --json: fence, consent, vault, duplicate_install and
     settings_json checks are asserted; checksums is recorded as-is, not
     asserted, because this is a live development tree and CHECKSUMS.sha256
     was cut against a clean release commit, not this moment's working copy
  6. one project through tools/bm_project.py in a fresh project directory
     under the fake HOME: start, task add, several task state moves, a
     review call, status, next, deliver --partial
  7. scripts/uninstall.py --remove-consent, then three assertions: the hook
     entries are gone from settings.json, the consent config file is gone,
     and a byte-for-byte vault file manifest (taken right after the vault is
     created in step 4) is unchanged

WHAT THIS DOES NOT PROVE (named here, restated in the evidence file)
  One physical machine, the author's own environment, no second machine, no
  naive user (that is Loop 8's outside-install list), and the plugin path is
  not exercised at all here (this rehearsal is the clone path only).

Python 3.9, standard library only. No em or en dashes anywhere in this file,
its comments, or its output.
"""

import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

EXIT_OK = 0
EXIT_FAILED = 1

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

COPY_EXCLUDE_NAMES = {".git", ".brothermode", "node_modules"}

STEP_TITLES = (
    "copy (clone stand-in) into fakehome/.claude/skills/brothermode",
    "python3 tools/test_all.py from the copy",
    "scripts/install.py against the fake settings.json",
    "scripts/setup.py flag mode consent, plus the vault-template copy",
    "scripts/doctor.py --json checks",
    "one project through tools/bm_project.py",
    "scripts/uninstall.py --remove-consent",
)


def _out(text):
    sys.stdout.write(text + "\n")
    sys.stdout.flush()


class Result(object):
    """One numbered step's outcome plus the detail lines printed under it."""

    def __init__(self, n, title):
        self.n = n
        self.title = title
        self.ok = False
        self.lines = []

    def note(self, text):
        for line in text.splitlines():
            self.lines.append("    " + line)

    def passed(self, summary):
        self.ok = True
        self.lines.insert(0, "    " + summary)

    def failed(self, summary):
        self.ok = False
        self.lines.insert(0, "    " + summary)

    def emit(self):
        _out("[%d/7] %s: %s" % (self.n, self.title, "PASS" if self.ok else "FAIL"))
        for line in self.lines:
            _out(line)


class Proc(object):
    """A uniform stand-in for subprocess.CompletedProcess, including the two
    failure shapes (timeout, could not start) that never raise past here, so
    every step below can read .returncode/.stdout/.stderr without a
    try/except of its own."""

    def __init__(self, returncode, stdout, stderr):
        self.returncode = returncode
        self.stdout = stdout or ""
        self.stderr = stderr or ""


def run(cmd, cwd=None, env=None, timeout=None, input_text=None):
    try:
        r = subprocess.run(
            cmd, cwd=cwd, env=env, timeout=timeout, input=input_text,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True)
        return Proc(r.returncode, r.stdout, r.stderr)
    except subprocess.TimeoutExpired as exc:
        return Proc(None, exc.stdout or "",
                    (exc.stderr or "") + "\nTIMEOUT after %s seconds" % timeout)
    except OSError as exc:
        return Proc(None, "", "could not start %s: %s" % (cmd, exc))


def shortcmd(cmd):
    return " ".join(cmd)


# ---------------------------------------------------------------------------
# paths and environment
# ---------------------------------------------------------------------------

def build_paths(tmp_root):
    fake_home = os.path.join(tmp_root, "fakehome")
    return {
        "tmp_root": tmp_root,
        "fake_home": fake_home,
        "target": os.path.join(fake_home, ".claude", "skills", "brothermode"),
        "settings": os.path.join(fake_home, ".claude", "settings.json"),
        "config": os.path.join(fake_home, ".brotherme", "config.json"),
        "vault": os.path.join(fake_home, "BrotherModeVault"),
        "project": os.path.join(fake_home, "projects", "fresh-home-demo"),
    }


def build_env(paths):
    """A copy of the real environment with HOME and BROTHERME_CONFIG pointed
    at the fake HOME, and every other BrotherMode-recognized environment
    variable this shell might already carry (BROTHERMODE_VAULT,
    BROTHERMODE_ROOT, BROTHERMODE_REGISTRIES) stripped out, so nothing about
    the real machine's own dogfood install leaks into the rehearsal."""
    env = dict(os.environ)
    for key in ("BROTHERMODE_VAULT", "BROTHERMODE_ROOT",
                "BROTHERMODE_REGISTRIES", "BROTHERME_CONFIG"):
        env.pop(key, None)
    env["HOME"] = paths["fake_home"]
    env["BROTHERME_CONFIG"] = paths["config"]
    return env


# ---------------------------------------------------------------------------
# step 1: copy stands in for git clone
# ---------------------------------------------------------------------------

def copytree_excluding(src, dst, exclude_names):
    os.makedirs(dst, exist_ok=True)
    count = 0
    for root, dirs, files in os.walk(src):
        dirs[:] = sorted(d for d in dirs if d not in exclude_names)
        rel = os.path.relpath(root, src)
        target_dir = dst if rel == "." else os.path.join(dst, rel)
        os.makedirs(target_dir, exist_ok=True)
        for f in sorted(files):
            if f in exclude_names:
                continue
            src_f = os.path.join(root, f)
            if os.path.islink(src_f):
                continue
            shutil.copy2(src_f, os.path.join(target_dir, f))
            count += 1
    return count


def step1_clone(paths, result):
    try:
        n = copytree_excluding(REPO_ROOT, paths["target"], COPY_EXCLUDE_NAMES)
    except OSError as exc:
        result.failed("copy failed: %s" % exc)
        return False
    marker = os.path.join(paths["target"], "SKILL.md")
    version = os.path.join(paths["target"], "VERSION")
    if not os.path.isfile(marker) or not os.path.isfile(version):
        result.failed("copy step wrote %d file(s) but SKILL.md or VERSION is "
                      "missing at %s" % (n, paths["target"]))
        return False
    # The source path starts under the operator's real HOME; the evidence
    # file this output lands in is committed, so the home prefix is masked
    # here at the source, the same policy mask_absolute_paths applies to
    # every exported store column.
    masked_root = REPO_ROOT
    real_home = os.path.expanduser("~")
    if masked_root.startswith(real_home):
        masked_root = "/Users/..." + masked_root[len(real_home):]
    result.passed(
        "%d files copied from %s to %s" % (n, masked_root, paths["target"]))
    result.note("disclosed deviation: this is a plain recursive copy, not "
               "git clone. It excludes %s, the same list "
               "scripts/checksums.sh and scripts/verify-install.sh use."
               % ", ".join(sorted(COPY_EXCLUDE_NAMES)))
    result.note("present at target: SKILL.md, VERSION")
    return True


# ---------------------------------------------------------------------------
# step 2: the gate
# ---------------------------------------------------------------------------

def step2_gate(paths, env, skip_gate, result):
    if skip_gate:
        result.passed("skipped with --skip-gate, a disclosed deviation from "
                      "the default; the default runs this suite")
        return True
    test_all = os.path.join(paths["target"], "tools", "test_all.py")
    cmd = [sys.executable, test_all]
    started = time.time()
    r = run(cmd, cwd=paths["target"], env=env, timeout=1800)
    elapsed = time.time() - started
    ok = (r.returncode == 0 and "ALL GREEN" in r.stdout)
    result.note("command: %s (cwd=%s)" % (shortcmd(cmd), paths["target"]))
    result.note("elapsed: %.1fs, exit code: %s" % (elapsed, r.returncode))
    for line in r.stdout.strip().splitlines():
        result.note(line)
    if r.stderr.strip():
        result.note("stderr: " + r.stderr.strip()[:2000])
    if ok:
        result.passed("exit code 0, ALL GREEN in the output")
    else:
        result.failed("exit code %s, ALL GREEN not found in the output"
                      % r.returncode)
    return ok


# ---------------------------------------------------------------------------
# step 3: scripts/install.py
# ---------------------------------------------------------------------------

def step3_install(paths, env, result):
    install_py = os.path.join(paths["target"], "scripts", "install.py")
    dry_cmd = [sys.executable, install_py, "--target", paths["target"],
              "--settings", paths["settings"], "--dry-run"]
    real_cmd = [sys.executable, install_py, "--target", paths["target"],
               "--settings", paths["settings"]]
    r_dry = run(dry_cmd, env=env, timeout=120)
    result.note("command: %s" % shortcmd(dry_cmd))
    result.note("dry-run exit code: %s" % r_dry.returncode)
    if r_dry.returncode != 0:
        result.note("dry-run stdout: " + r_dry.stdout.strip()[:2000])
        result.note("dry-run stderr: " + r_dry.stderr.strip()[:2000])
        result.failed("dry-run exit code was not 0")
        return False
    r_real = run(real_cmd, env=env, timeout=120)
    result.note("command: %s" % shortcmd(real_cmd))
    result.note("real-run exit code: %s" % r_real.returncode)
    for line in r_real.stdout.strip().splitlines():
        result.note(line)
    if r_real.stderr.strip():
        result.note("stderr: " + r_real.stderr.strip()[:2000])
    smoke_line_present = "fence hook ran end to end and exited 0" in r_real.stdout
    settings_written = os.path.isfile(paths["settings"])
    if r_real.returncode == 0 and smoke_line_present and settings_written:
        result.passed(
            "exit code 0, five hooks wired into %s, smoke line present"
            % paths["settings"])
        return True
    result.failed("exit code %s, smoke line present: %s, settings written: %s"
                  % (r_real.returncode, smoke_line_present, settings_written))
    return False


# ---------------------------------------------------------------------------
# step 4: scripts/setup.py flag mode, plus the vault-template copy
# ---------------------------------------------------------------------------

def step4_setup(paths, env, result):
    vault_template = os.path.join(paths["target"], "vault-template")
    try:
        n = copytree_excluding(vault_template, paths["vault"], set())
    except OSError as exc:
        result.failed("could not copy vault-template to %s: %s"
                      % (paths["vault"], exc))
        return False
    home_md = os.path.join(paths["vault"], "Home.md")
    if not os.path.isfile(home_md):
        result.failed("vault-template copy wrote %d file(s) but Home.md is "
                      "missing at %s" % (n, paths["vault"]))
        return False
    result.note("vault-template copied to %s (%d files), mirroring "
               "docs/SETUP.md Step 3, so the doctor vault check below has a "
               "real directory to look at" % (paths["vault"], n))

    setup_py = os.path.join(paths["target"], "scripts", "setup.py")
    cmd = [sys.executable, setup_py, "--vault", paths["vault"],
          "--mode", "clone", "--accept-notice"]
    r = run(cmd, env=env, timeout=300)
    result.note("command: %s" % shortcmd(cmd))
    result.note("exit code: %s" % r.returncode)
    for line in r.stdout.strip().splitlines()[:20]:
        result.note(line)
    if r.stderr.strip():
        result.note("stderr: " + r.stderr.strip()[:1000])

    if r.returncode != 0 or not os.path.isfile(paths["config"]):
        result.failed("exit code %s, config file present: %s"
                      % (r.returncode, os.path.isfile(paths["config"])))
        return False
    try:
        cfg = json.loads(io.open(paths["config"], encoding="utf-8").read())
    except (IOError, OSError, ValueError) as exc:
        result.failed("could not read %s after setup: %s" % (paths["config"], exc))
        return False
    fields_match = (cfg.get("setup_complete") is True
                    and cfg.get("installation_mode") == "clone"
                    and cfg.get("vault_path") == paths["vault"])
    if not fields_match:
        result.failed("config at %s does not hold the expected fields: %r"
                      % (paths["config"], cfg))
        return False
    result.passed("config at %s: setup_complete True, installation_mode "
                 "clone, vault_path %s" % (paths["config"], paths["vault"]))
    return True


# ---------------------------------------------------------------------------
# step 5: scripts/doctor.py --json
# ---------------------------------------------------------------------------

REQUIRED_PASS_KEYS = ("fence", "consent", "vault", "duplicate_install",
                      "settings_json")


def step5_doctor(paths, env, result):
    doctor_py = os.path.join(paths["target"], "scripts", "doctor.py")
    cmd = [sys.executable, doctor_py, "--settings", paths["settings"], "--json"]
    r = run(cmd, cwd=paths["fake_home"], env=env, timeout=300)
    result.note("command: %s (cwd=%s)" % (shortcmd(cmd), paths["fake_home"]))
    result.note("exit code: %s" % r.returncode)
    try:
        payload = json.loads(r.stdout)
    except ValueError as exc:
        result.note("stdout: " + r.stdout.strip()[:2000])
        result.note("stderr: " + r.stderr.strip()[:2000])
        result.failed("stdout was not valid JSON (%s)" % exc)
        return False
    by_key = {c["key"]: c for c in payload.get("checks", [])}
    for key in ("fence", "version", "runtime", "consent", "vault",
               "duplicate_install", "store", "mode_wiring", "checksums",
               "settings_json"):
        c = by_key.get(key)
        if c is None:
            result.note("no entry in the JSON for check: %s" % key)
            continue
        first_line = (c.get("message") or "").splitlines()[0] if c.get("message") else ""
        result.note("%-18s %-4s %s" % (key, c.get("status"), first_line[:140]))

    unmet = [k for k in REQUIRED_PASS_KEYS
            if by_key.get(k, {}).get("status") != "PASS"]
    checksums_status = by_key.get("checksums", {}).get("status")
    result.note("checksums status recorded as-is: %s (a live development "
               "tree, not a clean checked-out release, so CHECKSUMS.sha256 "
               "disagreeing is expected here; this key is not in the "
               "asserted set)" % checksums_status)
    if unmet:
        result.failed("status was not PASS for: %s" % ", ".join(unmet))
        return False
    result.passed("status PASS for: %s" % ", ".join(REQUIRED_PASS_KEYS))
    return True


# ---------------------------------------------------------------------------
# step 6: one project through tools/bm_project.py
# ---------------------------------------------------------------------------

PROJECT_ID = "fresh-home-demo"
ACTOR_NAME = "Fresh Home Rehearsal"


def _bm(paths, name):
    return [sys.executable, os.path.join(paths["target"], "tools", name)]


def _run_cli(cmd, cwd, env, result, label):
    r = run(cmd, cwd=cwd, env=env, timeout=120)
    result.note("%s: %s" % (label, shortcmd(cmd)))
    result.note("  exit code: %s" % r.returncode)
    out = r.stdout.strip()
    if out:
        for line in out.splitlines()[:10]:
            result.note("  " + line)
    if r.returncode != 0 and r.stderr.strip():
        result.note("  stderr: " + r.stderr.strip()[:1000])
    return r


def step6_project(paths, env, result):
    project_dir = paths["project"]
    os.makedirs(project_dir, exist_ok=True)
    actor_flags = ["--actor-type", "human", "--actor-name", ACTOR_NAME]

    r = _run_cli(_bm(paths, "bm_store.py") + ["init"], project_dir, env,
                result, "init")
    if r.returncode != 0:
        result.failed("bm_store.py init exit code was not 0")
        return False

    r = _run_cli(
        _bm(paths, "bm_project.py")
        + ["start", "--project-id", PROJECT_ID, "--name", "Fresh Home Demo",
           "--goal", "exercise the Loop 2 CLI from a fresh project directory",
           "--out-json"] + actor_flags,
        project_dir, env, result, "start")
    if r.returncode != 0:
        result.failed("start exit code was not 0")
        return False

    r = _run_cli(
        _bm(paths, "bm_project.py")
        + ["task", "add", "--project-id", PROJECT_ID,
           "--title", "Write the welcome note", "--out-json"] + actor_flags,
        project_dir, env, result, "task add")
    if r.returncode != 0:
        result.failed("task add exit code was not 0")
        return False
    try:
        task_id = json.loads(r.stdout).get("task_id")
    except ValueError:
        task_id = None
    if not task_id:
        result.failed("task add did not print a task_id in --out-json output")
        return False
    result.note("task_id: %s" % task_id)

    # Three of the ten canonical lifecycle states, each a legal forward move
    # per brotherme/core/schema.py LEGAL_TRANSITIONS. The forbidden state
    # named 'done' never appears, by design of the protocol itself.
    transitions = (
        ("ready", "no blocking dependencies"),
        ("active", "starting the drafting"),
        ("awaiting review", "handed off for a second look"),
    )
    for to_state, reason in transitions:
        r = _run_cli(
            _bm(paths, "bm_project.py")
            + ["task", "transition", "--task-id", task_id, "--to", to_state,
               "--reason", reason, "--out-json"] + actor_flags,
            project_dir, env, result, "task transition to %s" % to_state)
        if r.returncode != 0:
            result.failed("task transition to %r exit code was not 0"
                          % to_state)
            return False

    r = _run_cli(
        _bm(paths, "bm_project.py")
        + ["review", task_id, "--project-id", PROJECT_ID, "--kind", "manual",
           "--note", "second pair of eyes on the note text",
           "--reason", "hand check of the note text against the brief",
           "--out-json"] + actor_flags,
        project_dir, env, result, "review")
    if r.returncode != 0:
        result.failed("review exit code was not 0")
        return False

    r = _run_cli(
        _bm(paths, "bm_project.py") + ["status", "--project-id", PROJECT_ID],
        project_dir, env, result, "status")
    if r.returncode != 0:
        result.failed("status exit code was not 0")
        return False

    r = _run_cli(
        _bm(paths, "bm_project.py") + ["next", "--project-id", PROJECT_ID],
        project_dir, env, result, "next")
    if r.returncode != 0:
        result.failed("next exit code was not 0")
        return False

    r = _run_cli(
        _bm(paths, "bm_project.py")
        + ["deliver", "--project-id", PROJECT_ID, "--partial", "--out-json"],
        project_dir, env, result, "deliver --partial")
    if r.returncode != 0:
        result.failed("deliver --partial exit code was not 0")
        return False

    canvas = os.path.join(project_dir, "CANVAS.md")
    packet = os.path.join(project_dir, "DELIVERY-PACKET.md")
    store = os.path.join(project_dir, ".brothermode", "store.sqlite3")
    missing = [p for p in (canvas, packet, store) if not os.path.isfile(p)]
    if missing:
        result.failed("path(s) not found where documented: %s"
                      % ", ".join(missing))
        return False
    result.note("CANVAS.md: %s" % canvas)
    result.note("DELIVERY-PACKET.md: %s" % packet)
    result.note("store: %s" % store)
    result.passed("nine CLI calls all returned exit code 0; CANVAS.md, "
                 "DELIVERY-PACKET.md and the store are present at the "
                 "documented paths")
    return True


# ---------------------------------------------------------------------------
# step 7: scripts/uninstall.py --remove-consent
# ---------------------------------------------------------------------------

def _vault_manifest(vault_dir):
    out = {}
    for root, _dirs, files in os.walk(vault_dir):
        for f in files:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, vault_dir)
            try:
                out[rel] = os.path.getsize(full)
            except OSError:
                out[rel] = None
    return out


def step7_uninstall(paths, env, before_manifest, result):
    uninstall_py = os.path.join(paths["target"], "scripts", "uninstall.py")
    cmd = [sys.executable, uninstall_py, "--settings", paths["settings"],
          "--remove-consent"]
    r = run(cmd, env=env, timeout=120)
    result.note("command: %s" % shortcmd(cmd))
    result.note("exit code: %s" % r.returncode)
    for line in r.stdout.strip().splitlines():
        result.note(line)
    if r.stderr.strip():
        result.note("stderr: " + r.stderr.strip()[:1000])
    if r.returncode != 0:
        result.failed("uninstall.py exit code was not 0")
        return False

    try:
        settings_text = io.open(paths["settings"], encoding="utf-8").read()
    except (IOError, OSError) as exc:
        result.failed("could not re-read %s after uninstall: %s"
                      % (paths["settings"], exc))
        return False
    hooks_gone = paths["target"] not in settings_text
    consent_gone = not os.path.isfile(paths["config"])
    after_manifest = _vault_manifest(paths["vault"])
    vault_untouched = (after_manifest == before_manifest)

    result.note("hooks_gone=%s (settings.json no longer names %s)"
               % (hooks_gone, paths["target"]))
    result.note("consent_gone=%s (%s does not exist)"
               % (consent_gone, paths["config"]))
    result.note("vault_untouched=%s (%d file(s) before, %d after, byte-size "
               "manifest identical: %s)" % (vault_untouched,
                                             len(before_manifest),
                                             len(after_manifest),
                                             vault_untouched))

    if hooks_gone and consent_gone and vault_untouched:
        result.passed("hooks_gone, consent_gone, vault_untouched all true")
        return True
    result.failed("hooks_gone=%s consent_gone=%s vault_untouched=%s"
                 % (hooks_gone, consent_gone, vault_untouched))
    return False


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def build_parser():
    p = argparse.ArgumentParser(
        prog="rehearse_fresh_install.py",
        description="Fresh-HOME clone-path install rehearsal (Loop 3 design "
                    "D-6). Never touches the real HOME or the real "
                    "~/.claude.")
    p.add_argument("--skip-gate", action="store_true",
                   help="skip step 2 (python3 tools/test_all.py from the "
                        "copy) for time; the default runs it")
    p.add_argument("--keep", action="store_true",
                   help="do not delete the temporary directories on exit "
                        "(for inspecting a failure)")
    return p


def main(argv):
    args = build_parser().parse_args(argv)
    tmp_root = tempfile.mkdtemp(prefix="bm-rehearsal-")
    paths = build_paths(tmp_root)
    env = build_env(paths)

    _out("rehearse_fresh_install.py: fresh-HOME clone-path rehearsal")
    _out("  temp root: %s" % tmp_root)
    _out("  fake HOME: %s" % paths["fake_home"])
    _out("  gate: %s" % ("SKIPPED (--skip-gate)" if args.skip_gate else "RUN"))
    _out("")

    results = []
    overall_ok = True
    vault_manifest_before = None

    try:
        r1 = Result(1, STEP_TITLES[0])
        ok1 = step1_clone(paths, r1)
        results.append(r1)
        overall_ok = overall_ok and ok1
        r1.emit()
        if not ok1:
            raise SystemExit  # nothing downstream can proceed without the copy

        r2 = Result(2, STEP_TITLES[1])
        ok2 = step2_gate(paths, env, args.skip_gate, r2)
        results.append(r2)
        overall_ok = overall_ok and ok2
        r2.emit()

        r3 = Result(3, STEP_TITLES[2])
        ok3 = step3_install(paths, env, r3)
        results.append(r3)
        overall_ok = overall_ok and ok3
        r3.emit()

        r4 = Result(4, STEP_TITLES[3])
        ok4 = step4_setup(paths, env, r4)
        results.append(r4)
        overall_ok = overall_ok and ok4
        r4.emit()
        if ok4 and os.path.isdir(paths["vault"]):
            vault_manifest_before = _vault_manifest(paths["vault"])

        r5 = Result(5, STEP_TITLES[4])
        ok5 = step5_doctor(paths, env, r5)
        results.append(r5)
        overall_ok = overall_ok and ok5
        r5.emit()

        r6 = Result(6, STEP_TITLES[5])
        ok6 = step6_project(paths, env, r6)
        results.append(r6)
        overall_ok = overall_ok and ok6
        r6.emit()

        r7 = Result(7, STEP_TITLES[6])
        if vault_manifest_before is None:
            r7.failed("step 4 produced no vault manifest to compare against")
            ok7 = False
        else:
            ok7 = step7_uninstall(paths, env, vault_manifest_before, r7)
        results.append(r7)
        overall_ok = overall_ok and ok7
        r7.emit()
    except SystemExit:
        pass
    finally:
        if args.keep:
            _out("")
            _out("--keep given: leaving %s in place." % tmp_root)
        else:
            shutil.rmtree(tmp_root, ignore_errors=True)

    _out("")
    passed = sum(1 for r in results if r.ok)
    all_seven_pass = overall_ok and len(results) == len(STEP_TITLES)
    _out("rehearse_fresh_install.py: %d/%d step(s) PASS. %s"
        % (passed, len(STEP_TITLES),
           "ALL GREEN" if all_seven_pass else "NOT ALL GREEN"))
    return EXIT_OK if all_seven_pass else EXIT_FAILED


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
