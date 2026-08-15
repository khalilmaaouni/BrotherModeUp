#!/usr/bin/env python3
"""The change passport, producer half: what BrotherMode deposits at the seam.

WHAT THE SEAM IS. The change passport is the single crossing between
execution provenance and assurance (docs/specs/2026-08-15-change-passport-
seam.md in the BrotherSBE repository is the contract). BrotherMode produces
one, BrotherSBE consumes one, and it never travels back. This tool is the
producing end and the only place BrotherMode writes passport data.

THE TWO FIELDS THIS TOOL OWNS. Execution provenance owns exactly two of the
five fields the chain names, because only execution can see them:

  whoDidIt              the session and the claims it holds, plus the
                         accountable person by name (never a role)
  whereItCameFrom        the development method, named and not judged

A third field rides along because execution is also the only side that
knows what IT left undone, which assurance has no way to see:

  whatWasNotEstablished  gaps this producer itself hit while assembling the
                         deposit (a missing store, an unlabeled session, an
                         accountable person nobody named)

DIRECTION OF TRAVEL. This tool writes <root>/.sbe/passport.json and reads
NOTHING under .sbe/: no tasks.json, no evidence/, no existing passport.json.
Reaching across the seam to fill a field is the exact failure the seam
exists to prevent. Its only inputs are tools/bm_store.py's own store (read
only, never STATE.md, which is a generated view and not truth), `git config
user.name`, and the --accountable / --method flags.

A HOLLOW VALUE IS NOT A VALUE. An empty string, a whitespace-only string, an
empty list, or null all read as absence on the consuming side. A field this
tool cannot establish honestly is OMITTED from the deposit, never padded
with an empty placeholder to look filled, and the omission is explained on
stdout.

NOT A GATE. This tool reports and deposits, it never blocks on what it
FINDS: a store it could not read, a session nobody labeled and an
accountable person nobody named are all exit 0 with the gap written into
field 4, never a refusal. Three exits, stated exactly, because a tool whose
own documentation misreports its exit codes is the same overclaim this
product exists to catch:

  0  a deposit was written, whatever it could and could not establish
  1  the deposit itself could not be written to disk (the one case where
     running this tool and getting nothing is itself the finding)
  2  a usage error, or the NO-DATA verdict where no project root could be
     resolved at all, which is not a finding about a change but a failure
     to find a change to report on

Python floor is 3.9: no match statements, no `X | Y` annotations. Standard
library only, mirroring every other tool in this directory.

Run it with --help for the usage line, which resolves the command to the
layout the reader actually installed rather than naming a tools/ directory
a packaged install does not have.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

#: Fixed by the contract: the producer always deposits here unless --out
#: names a different path (used by this tool's own tests so they never
#: touch a real .sbe/ directory).
DEPOSIT_REL = os.path.join(".sbe", "passport.json")

#: Named and not judged, per the contract. Always true of anything this
#: tool produces a deposit for, so it is never hollow and never guessed;
#: --method overrides it when a session ran a different flow on top.
DEFAULT_METHOD = "BrotherMode"


# ---------------------------------------------------------------------------
# Root resolution. Honors --root when given; otherwise borrows bm_store's
# resolve_root() purely for that lookup. Mirrors tools/bm_idle.py's
# resolve_project_root() exactly, since that file is this tool's structural
# template.
# ---------------------------------------------------------------------------

def _load_bm_store():
    """Load bm_store.py by PATH: this tool is invoked with an arbitrary
    cwd, and a plain `import bm_store` would depend on whichever sys.path
    the caller happened to have. Never raises: an unimportable module
    degrades to an explicit reason string, not a crash."""
    try:
        import importlib.util
        path = os.path.join(HERE, "bm_store.py")
        spec = importlib.util.spec_from_file_location(
            "bm_store_for_passport", path)
        if spec is None or spec.loader is None:
            return None, "could not build an import spec for bm_store.py"
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod, None
    except Exception as exc:
        return None, "%s: %s" % (type(exc).__name__, exc)


def resolve_project_root(explicit_root):
    """Return (root, None) or (None, reason). `explicit_root` (--root)
    always wins and is checked directly against the filesystem; nothing
    else here reads bm_store at all in that case. Otherwise
    bm_store.resolve_root() is borrowed, which returns a (path, source)
    TUPLE that must be unpacked."""
    if explicit_root:
        candidate = os.path.realpath(os.path.expanduser(explicit_root))
        if not os.path.isdir(candidate):
            return None, "no such directory: %s" % candidate
        return candidate, None
    mod, err = _load_bm_store()
    if mod is None:
        return None, ("could not load bm_store.py to resolve the project "
                      "root (%s); pass --root explicitly" % err)
    root, _source = mod.resolve_root()
    if not root:
        return None, ("nothing anchors a BrotherMode project here (no "
                      "BROTHERMODE_ROOT, no marker directory, no git repo "
                      "found); pass --root explicitly")
    return root, None


# ---------------------------------------------------------------------------
# Hollow-value detection. Matches the consuming side's own definition
# (BrotherSBE tools/sbe_onepager.py's answered()) exactly: '' and None carry
# nothing, 0 and False are real answers, an empty list/dict carries nothing.
# Defined here rather than imported, because the producer never reads a
# BrotherSBE file at runtime; matching the CONTRACT'S definition by hand is
# the whole point of a seam.
# ---------------------------------------------------------------------------

def _answered(value):
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, (list, tuple, dict)):
        return len(value) > 0
    return True


# ---------------------------------------------------------------------------
# whoDidIt: the store's own active records and claims, never STATE.md.
# ---------------------------------------------------------------------------

def _store_snapshot(root):
    """Return (state, payload, store_path). state is one of 'absent',
    'unreadable', 'ok'. payload is a plain-English reason for 'absent' and
    'unreadable', or the dict from Store.dump(raw=True) for 'ok'.
    store_path is bm_store's own path for the store file when it could be
    computed, else None. Never raises: every exception this store can throw
    on open or on dump is caught and turned into 'unreadable' rather than
    left to crash this tool."""
    mod, err = _load_bm_store()
    if mod is None:
        return "unreadable", "bm_store.py could not be loaded (%s)" % err, None
    store_path = mod.store_path(root)
    try:
        store = mod.ReadOnlyStore(root)
    except mod.OwnershipRefused as e:
        if e.reason == "no-store":
            return "absent", "no BrotherMode store at %s" % store_path, store_path
        return ("unreadable",
                "the BrotherMode store at %s could not be opened: %s"
                % (store_path, e), store_path)
    except mod.StoreCorrupt as e:
        return ("unreadable",
                "the BrotherMode store at %s is corrupt: %s" % (store_path, e),
                store_path)
    except Exception as e:
        return ("unreadable",
                "the BrotherMode store at %s could not be opened: %s: %s"
                % (store_path, type(e).__name__, e), store_path)
    try:
        dump = store.dump(raw=True)
    except Exception as e:
        return ("unreadable",
                "the BrotherMode store at %s could not be read: %s: %s"
                % (store_path, type(e).__name__, e), store_path)
    finally:
        try:
            store.close()
        except Exception:
            pass
    return "ok", dump, store_path


def _session_claim_lines(dump):
    """Return (lines, total_files, skipped_records).

    One line per distinct session holding an ACTIVE record, each naming the
    files claimed across every active record that session holds. Sorted by
    session label so output is deterministic run to run.

    The two extra return values exist because of what this function DOES NOT
    read, which an adversarial review found could produce a confidently wrong
    field 2 with a clean field 4. `records.state` is one of active, parked,
    complete or adopted, and only active is read here. A session deposits at
    CLOSE, which is exactly when its own record is most likely already
    complete or parked, so a deposit assembled from active claims alone can
    name a concurrent, unrelated session as the author and say nothing was
    missing. Counting the skipped records here is what lets build_deposit say
    so in field 4 rather than stay silent. Same reason for the file total: a
    session line reading "0 files" is not provenance, and the caller cannot
    see that from the formatted strings."""
    records = dump.get("records") or []
    claims = dump.get("claims") or []
    files_by_uuid = {}
    for c in claims:
        u = c.get("lifecycle_uuid")
        files_by_uuid[u] = files_by_uuid.get(u, 0) + 1

    totals = {}  # session label -> [file_count, record_count]
    skipped = 0
    for r in records:
        if r.get("state") != "active":
            skipped += 1
            continue
        sid = (r.get("session_id") or "").strip()
        label = sid if sid else "(no session id recorded)"
        entry = totals.setdefault(label, [0, 0])
        entry[0] += files_by_uuid.get(r.get("lifecycle_uuid"), 0)
        entry[1] += 1

    lines = []
    total_files = 0
    for label in sorted(totals):
        n_files, n_records = totals[label]
        total_files += n_files
        lines.append(
            "session %s, holding claims on %d file%s across %d record%s"
            % (label, n_files, "" if n_files == 1 else "s",
               n_records, "" if n_records == 1 else "s"))
    return lines, total_files, skipped


def _unlabeled_active_count(dump):
    records = dump.get("records") or []
    return sum(1 for r in records
              if r.get("state") == "active"
              and not (r.get("session_id") or "").strip())


# ---------------------------------------------------------------------------
# The accountable person: a real source only. A store field never carries a
# person's name (records.owner is a ROLE, e.g. "builder", which is exactly
# what this field exists to replace), so the two honest sources are an
# explicit --accountable flag and `git config user.name`. Neither found
# means the field is omitted, not guessed.
# ---------------------------------------------------------------------------

def _git_user_name(root):
    try:
        result = subprocess.run(
            ["git", "-C", root, "config", "user.name"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    name = result.stdout.strip()
    return name or None


def _accountable_line(root, explicit):
    """Return (line_or_None, gap_reason_or_None).

    A name taken from git STILL carries a gap reason, which is the whole
    point of field 4. `git config user.name` resolves the machine's global
    identity: it answers who owns this laptop, not who is accountable for
    THIS change, and it answers even when `root` is not a repository at all.
    Naming it without saying where it came from is the same overclaim as an
    empty field 4 on a store that could not be read."""
    if explicit and explicit.strip():
        return "accountable: %s" % explicit.strip(), None
    name = _git_user_name(root)
    if name:
        return ("accountable: %s" % name,
                "the accountable person was INFERRED from `git config "
                "user.name` at %s, which resolves the machine's global git "
                "identity; nobody stated an accountable person for this "
                "change (no --accountable flag was given)" % root)
    return None, (
        "the accountable person could not be established: no --accountable "
        "flag was given and `git config user.name` returned nothing at %s"
        % root)


# ---------------------------------------------------------------------------
# Assembling the deposit.
# ---------------------------------------------------------------------------

def build_deposit(root, accountable_flag, method_flag):
    """Return (deposit_dict, not_established_lines, notes_for_stdout)."""
    state, payload, store_path = _store_snapshot(root)

    session_lines = []
    not_established = []
    if state == "ok":
        session_lines, total_files, skipped = _session_claim_lines(payload)
        if not session_lines:
            not_established.append(
                "no active claim was found in the BrotherMode store at %s, "
                "so this producer cannot say which session or files this "
                "change belongs to" % store_path)
        if skipped:
            not_established.append(
                "%d record(s) in the BrotherMode store are not active "
                "(complete, parked or adopted) and were NOT read, so a "
                "session whose record already closed does not appear above; "
                "only claims active at the moment this deposit was written "
                "were read" % skipped)
        if session_lines and total_files == 0:
            not_established.append(
                "the active record(s) claim no files at all, so this deposit "
                "can name the session but cannot say which files the change "
                "touched")
        unlabeled = _unlabeled_active_count(payload)
        if unlabeled:
            not_established.append(
                "%d active record(s) in the BrotherMode store carry no "
                "session id, so their claims cannot be attributed to a "
                "session" % unlabeled)
    elif state == "absent":
        not_established.append(
            "%s, so session and claim history for this change could not be "
            "established" % payload)
    else:
        not_established.append(
            "%s, so session and claim history for this change could not be "
            "read" % payload)

    accountable_line, accountable_gap = _accountable_line(root, accountable_flag)
    if accountable_gap:
        not_established.append(accountable_gap)

    who_did_it = list(session_lines)
    if accountable_line:
        who_did_it.append(accountable_line)

    # Always true of this tool, never fabricated: it is a structural limit
    # of what an execution-side deposit can attest to, and it is the reason
    # whatWasNotEstablished can never legitimately read as empty even on a
    # perfectly healthy store.
    not_established.append(
        "this deposit reports BrotherMode's own store only (session ids "
        "and claimed files); it does not know whether the work was "
        "reviewed, tested, or verified, which is assurance's job to "
        "establish, not execution's")

    method = method_flag.strip() if (method_flag and method_flag.strip()) else DEFAULT_METHOD

    deposit = {}
    if _answered(who_did_it):
        deposit["whoDidIt"] = who_did_it
    if _answered(method):
        deposit["whereItCameFrom"] = method
    if _answered(not_established):
        deposit["whatWasNotEstablished"] = not_established

    notes = ["store: %s%s" % (state, "" if state == "ok" else " (%s)" % payload)]
    for field in ("whoDidIt", "whereItCameFrom", "whatWasNotEstablished"):
        notes.append("%s: %s" % (field, "carried" if field in deposit
                                        else "NOT established, omitted"))
    return deposit, not_established, notes


# ---------------------------------------------------------------------------
# CLI.
# ---------------------------------------------------------------------------

def _usage():
    """The command a reader can actually paste, in the layout they have.

    P17 put the shipping commands on PATH, so a hardcoded
    `python3 tools/bm_passport.py` names a directory a packaged install does
    not have. Resolved through bm_store.invocation(), the same resolver
    tools/bm_handover.py and tools/bm_docs.py use, and swept for by
    test_bm_store.py's TestP17InstructionTextMatchesTheInstalledLayout.
    Degrades to this module's own absolute path, which is correct from any
    cwd, when bm_store cannot be loaded: a usage string is not worth a
    traceback."""
    cmd = None
    mod, _err = _load_bm_store()
    if mod is not None:
        try:
            cmd = mod.invocation("bm_passport.py", __file__)
        except Exception:
            cmd = None
    if not cmd:
        cmd = "python3 %s" % os.path.abspath(__file__)
    return ("Usage: %s [--root DIR] [--out PATH]\n"
            "         [--accountable NAME] [--method TEXT]\n\n"
            "Writes the change passport's producer deposit at <root>/%s.\n"
            "Exit 0 when a deposit was written, whatever it could and could "
            "not\nestablish. Exit 1 when the deposit itself could not be "
            "written.\nExit 2 for a usage error, and for a NO-DATA verdict "
            "where no project\nroot could be resolved at all, which is not a "
            "finding about a change\nbut a failure to find one." % (
                cmd, DEPOSIT_REL))


def _parse_argv(argv):
    """Return (root, out, accountable, method, error). `error` set to
    'help' means print usage and exit 0; any other string means a plain
    usage failure (exit 2)."""
    args = list(argv)
    root = None
    out = None
    accountable = None
    method = None
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--help", "-h"):
            return None, None, None, None, "help"
        # An EMPTY value for the two path flags is refused rather than
        # treated as absent. `--out "$OUT"` with an unset variable used to
        # fall back to the project's real .sbe/passport.json, so a caller
        # scripting a throwaway deposit silently wrote over the live one.
        # The two text flags keep degrading quietly: an empty --accountable
        # omits the field, which is honest, and an empty --method takes the
        # default. Only the flags that decide WHERE bytes land are strict.
        if arg == "--root":
            if i + 1 >= len(args):
                return None, None, None, None, "bm_passport: --root requires a value"
            if not args[i + 1].strip():
                return None, None, None, None, (
                    "bm_passport: --root was given an empty value; omit the "
                    "flag to resolve the project root automatically")
            root = args[i + 1]
            i += 2
        elif arg == "--out":
            if i + 1 >= len(args):
                return None, None, None, None, "bm_passport: --out requires a value"
            if not args[i + 1].strip():
                return None, None, None, None, (
                    "bm_passport: --out was given an empty value; omit the "
                    "flag to write the deposit at <root>/%s" % DEPOSIT_REL)
            out = args[i + 1]
            i += 2
        elif arg == "--accountable":
            if i + 1 >= len(args):
                return None, None, None, None, "bm_passport: --accountable requires a value"
            accountable = args[i + 1]
            i += 2
        elif arg == "--method":
            if i + 1 >= len(args):
                return None, None, None, None, "bm_passport: --method requires a value"
            method = args[i + 1]
            i += 2
        else:
            return None, None, None, None, "bm_passport: unknown argument: %s" % arg
    return root, out, accountable, method, None


def _run(argv):
    root_arg, out_arg, accountable_arg, method_arg, err = _parse_argv(argv)
    if err == "help":
        sys.stdout.write(_usage() + "\n")
        return 0
    if err:
        sys.stderr.write(err + "\n")
        sys.stderr.write(_usage() + "\n")
        return 2

    root, reason = resolve_project_root(root_arg)
    if root is None:
        sys.stdout.write("NO-DATA: %s\n" % reason)
        return 2

    deposit, _not_established, notes = build_deposit(root, accountable_arg, method_arg)
    out_path = out_arg or os.path.join(root, DEPOSIT_REL)

    # Written to a temp file and moved into place, the same idiom as
    # tools/bm_docs.py and nine other tools here. Truncating the real path
    # first means a failure mid-write leaves a half-written deposit, and the
    # consumer classifies a truncated deposit as CORRUPT rather than absent,
    # which is a worse answer than never having written one.
    try:
        parent = os.path.dirname(os.path.abspath(out_path))
        if parent and not os.path.isdir(parent):
            os.makedirs(parent)
        tmp_path = out_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(deposit, fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp_path, out_path)
    except OSError as e:
        sys.stderr.write("bm-passport: could not write %s (%s)\n" % (out_path, e))
        return 1

    sys.stdout.write("deposit written: %s\n" % out_path)
    for line in notes:
        sys.stdout.write(line + "\n")
    return 0


def main(argv):
    try:
        return _run(argv)
    except Exception as exc:
        sys.stdout.write("NO-DATA: %s: %s\n" % (type(exc).__name__, exc))
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
