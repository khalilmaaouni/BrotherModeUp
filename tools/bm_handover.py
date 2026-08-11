#!/usr/bin/env python3
"""bm_handover.py: the baton ceremony tool.

WHAT THIS IS FOR
  docs/superpowers/specs/2026-08-11-baton-ceremony-design.md, section 4.
  Sessions die; work must not. This tool is the CLOSE half's skeleton and
  verdict, and the START half's first read: it generates a traceable pack of
  narrative files pre filled from the store, checks that a filled pack is
  actually ready to close, zips it for the founder's own archive, and (on a
  fresh session) reports what the store already knows about leftovers from
  a session that never got to close cleanly.

Four commands:
  skeleton [--out DIR] [--slot NAME] [--date YYYY-MM-DD]
      Writes the pack folder (default docs/handover/<date>-<slot>/, slot
      default "session") with the seven files this pack always carries,
      structural sections pre filled from the store, and one FILL-BY-HAND
      human block per file. Re running over a filled pack preserves every
      human byte from the "Notes" heading onward, unchanged, however many
      blocks or trailing paragraphs a person added (I10): see
      _existing_human_region / render_page. --out must be relative to the
      project root; an absolute path is refused, never silently
      reinterpreted.
  verify-close [--pack DIR] [--session ID]
      The mechanical checklist: every pack file present, non empty, and
      carrying a filled human block (FILL-BY-HAND matched case
      insensitively); a command center copy when the project has one; the
      close report's first non-empty human line a whole-word FINISHED or
      UNFINISHED; a zip whose CONTENT matches the pack right now; and no
      unparked record (any state but parked or complete) still held by the
      closing session, given by --session or, when omitted, the store's
      own notion of the current session (BM_FENCE_SESSION_ID or
      CLAUDE_SESSION_ID). NO-DATA when there is no store, no pack, or no
      session can be determined for the ownership check; never PASS in
      that case. --pack is routed through the same containment gate
      skeleton's --out uses. PASS only when every check clears; exit 0
      only on PASS.
  zip [--pack DIR]
      Packages the pack folder to
      ~/Documents/BrotherModeUp-handovers/BrotherMode-Handover-<date>-<slot>
      .zip (the directory name doubles as <date>-<slot>). Idempotent by
      content: an unchanged pack says so rather than rewriting the file.
      --pack is contained to the project root; a subdirectory in the pack,
      or a pack file that is a symlink escaping the project, is refused
      rather than silently dropped or followed.
  detect
      Read only: the newest pack and zip with their ages, unacknowledged
      handovers (from the store), and dead-owner leftovers (from
      tools/bm_stall.py's own sweep). Exit 0 always; an empty estate is
      stated, never silent.

WHAT THIS DOES NOT DO
  It never writes the store. Every store mutation the ceremony needs (park,
  handover-ack) stays in bm_store.py, exactly where the rule (section 3)
  already sends the founder. Every store READ here goes through a public
  bm_store.py or bm_stall.py function: ReadOnlyStore.dump(), bs.verify(),
  and bm_stall.sweep(). No SQL of this file's own, no network, no
  subprocess.

Python 3.9, standard library only.

No em or en dashes anywhere in this file, its comments, or its output.
"""

import hashlib
import importlib.util
import io
import os
import re
import shutil
import sys
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    """Load a sibling module by PATH, the same technique tools/bm_packs.py
    and tools/bm_stall.py use: this file is invoked from an arbitrary
    working directory and must not depend on whatever sys.path the caller
    happened to have."""
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(HERE, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bs = _load("bm_store")

HUMAN_BEGIN = bs.HUMAN_BLOCK_BEGIN
HUMAN_END = bs.HUMAN_BLOCK_END

FILL_BY_HAND = "FILL-BY-HAND"

SLOT_DEFAULT = "session"

PACK_FILES = (
    "00-READ-ME-FIRST.md",
    "01-HANDOVER.md",
    "02-LEARNINGS-AND-MISTAKES.md",
    "03-RULES-AND-PROCESS-FIXES.md",
    "04-NEXT-LOOPS-PRIORITIZED.md",
    "05-VAULT-AND-OBSIDIAN.md",
    "06-CLOSE-REPORT.md",
)

PAGE_TITLES = {
    "00-READ-ME-FIRST.md": "Read me first",
    "01-HANDOVER.md": "Handover",
    "02-LEARNINGS-AND-MISTAKES.md": "Learnings and mistakes",
    "03-RULES-AND-PROCESS-FIXES.md": "Rules and process fixes",
    "04-NEXT-LOOPS-PRIORITIZED.md": "Next loops, prioritized",
    "05-VAULT-AND-OBSIDIAN.md": "Vault and Obsidian",
    "06-CLOSE-REPORT.md": "Close report",
}

DEFAULT_HUMAN = {
    "00-READ-ME-FIRST.md": (
        FILL_BY_HAND + ": anything else the next session should know "
        "before reading further."),
    "01-HANDOVER.md": (
        FILL_BY_HAND + ": what happened this session, and what is next."),
    "02-LEARNINGS-AND-MISTAKES.md": (
        FILL_BY_HAND + ": learnings, mistakes, and near misses from this "
        "session."),
    "03-RULES-AND-PROCESS-FIXES.md": (
        FILL_BY_HAND + ": a rule or process fix this session's own mistakes "
        "surfaced, if any."),
    "04-NEXT-LOOPS-PRIORITIZED.md": (
        FILL_BY_HAND + ": the next loops, in priority order."),
    "05-VAULT-AND-OBSIDIAN.md": (
        FILL_BY_HAND + ": what changed in the memory vault this session, and "
        "its session log entry."),
    "06-CLOSE-REPORT.md": (
        FILL_BY_HAND + ": replace this whole block. The FIRST LINE must "
        "start with the exact word FINISHED, or the exact word UNFINISHED "
        "followed by exactly where the baton lies."),
}

COMMAND_CENTER_REL = ("docs", "plan", "COMMAND-CENTER.html")
COMMAND_CENTER_NAME = "COMMAND-CENTER.html"

GENERATED_NOTE = (
    "<!-- GENERATED by tools/bm_handover.py. Regenerate rather than "
    "hand-edit, except inside the human markers, which are preserved "
    "verbatim. -->")

#: The fixed heading every page's human section opens with (render_page
#: writes it verbatim). Everything from this line to end of file, on a page
#: already on disk, is the region I10 protects: not just the first human
#: block, but every byte after this heading, however many blocks or trailing
#: paragraphs a person added (report finding F8). See _existing_human_region.
NOTES_HEADING = "## Notes (human, preserved verbatim on regeneration)"

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

#: The close report's status line must open with one of these words, matched
#: whole-word (report finding F10: a prefix match let "FINISHEDNESS is a
#: myth..." through). Case sensitive on purpose: FINISHED and UNFINISHED are
#: shouted so a scanning eye cannot miss them, unlike the FILL-BY-HAND marker
#: scan below, which is deliberately case INSENSITIVE (report finding F15).
#: The asymmetry is intentional: FILL-BY-HAND is a generated label a person
#: might retype in any case without meaning anything by it; FINISHED /
#: UNFINISHED is a word this tool asks the CLOSING SESSION to shout on
#: purpose, so a differently-cased spelling is not an accidental match to
#: forgive, it is a missed instruction to catch.
_STATUS_LINE_RE = re.compile(r"^(FINISHED|UNFINISHED)\b")

PASS, FAIL, NODATA = 0, 1, 2


# ---------------------------------------------------------------------------
# Small shared helpers.
# ---------------------------------------------------------------------------

def _out(msg=""):
    sys.stdout.write("%s\n" % msg)


def _err(msg):
    sys.stderr.write("%s\n" % msg)


def _parse(argv, known, wants_value=()):
    """Flags into (positional, kv), refusing anything unrecognized. The
    same shape tools/bm_packs.py's _parse uses, minus the repeatable-flag
    case this tool never needs."""
    positional, kv, i = [], {}, 0
    while i < len(argv):
        tok = argv[i]
        if tok.startswith("--"):
            name = tok[2:]
            if name not in known:
                _err("bm_handover: unrecognized flag --%s (recognized: %s)"
                     % (name, ", ".join("--" + k for k in sorted(known))))
                sys.exit(2)
            if name in wants_value:
                if i + 1 >= len(argv):
                    _err("bm_handover: --%s needs a value" % name)
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


#: A record is still "unparked and owned" (report finding F6) in every state
#: except the two settled ones: "parked" (the session let go of it, with a
#: handover) and "complete" (finished, nothing left to hand off). Derived
#: from bs._LEGAL_MOVES, the store's own transition table (tools/bm_store.py
#: around line 5554: "parked", "active", "complete", "adopted"), rather than
#: a literal "active" restated here: that literal is exactly what let an
#: "adopted" record, equally unparked and equally owned, slip past check 4.
UNPARKED_STATES = frozenset(
    s for s in bs._LEGAL_MOVES if s not in ("parked", "complete"))


def _root():
    root, _source = bs.require_root()
    return root


def _inv():
    return bs.invocation("bm_handover.py", os.path.join(HERE, "bm_handover.py"))


def _store_inv():
    return bs.invocation("bm_store.py", os.path.join(HERE, "bm_store.py"))


def _today():
    return time.strftime("%Y-%m-%d")


def _current_session_id():
    """The store's own notion of "the session doing this", read when
    verify-close's --session flag is omitted (report finding F1). The same
    two harness env vars bm_store.py's own _hook_derived_session_id reads,
    in the same order (BM_FENCE_SESSION_ID, then CLAUDE_SESSION_ID), taken
    AS-IS rather than through that function's hook-derived bm1-<hash>
    label: deriving that label materializes a token file on disk
    (tools/bm_fence_hook.py's ensure_token), and this tool is read only
    over the store per section 4. Returns "" when neither env var is set;
    the caller decides what an undetermined session means (verify-close
    treats it as NO-DATA, never as PASS)."""
    return (os.environ.get("BM_FENCE_SESSION_ID", "").strip()
            or os.environ.get("CLAUDE_SESSION_ID", "").strip())


def _handovers_dir():
    """~/Documents/BrotherModeUp-handovers, or BROTHERMODE_HANDOVERS_DIR
    when set. Read at CALL time, not at import time, so a test that sets
    the env var after loading this module (the ordinary case for a module
    loaded once and reused across a suite) still redirects every command
    that writes here. Mirrors the BROTHERMODE_VAULT idiom tools/
    bm_autosave.py, tools/bm_telemetry.py and tools/bm_ledger.py already
    use for the same reason: a real founder path must never be the only
    spelling a test can reach."""
    return os.environ.get("BROTHERMODE_HANDOVERS_DIR",
                          os.path.expanduser("~/Documents/BrotherModeUp-handovers"))


def _scrub(value):
    """The same two-function funnel tools/bm_stall.py's own _scrub applies:
    redact_text for secret shapes, mask_absolute_paths for the founder's
    filesystem layout. Every store-derived string this file writes to a
    pack page or prints goes through here first."""
    return bs.mask_absolute_paths(bs.redact_text(value or ""))


def _out_scrubbed(msg=""):
    """_out, with absolute paths masked (report finding F14). verify-close
    and detect print verdicts the ceremony asks a session to QUOTE into a
    session log or a committed pack page, so the founder's filesystem
    layout must not ride along in a path an operator only needed to see
    on their own screen. zip's own stdout is deliberately NOT routed
    through this: the report scoped F14 to verify-close and detect only,
    and zip's message is the one place an operator needs the real path to
    go look at what was just written."""
    _out(bs.mask_absolute_paths(msg))


def _fmt_age(seconds):
    seconds = max(0.0, seconds)
    if seconds < 60:
        return "%ds" % int(seconds)
    minutes = seconds / 60.0
    if minutes < 60:
        return "%.0fm" % minutes
    hours = minutes / 60.0
    if hours < 48:
        return "%.1fh" % hours
    return "%.1fd" % (hours / 24.0)


def _dir_mtime(pack_dir):
    """The freshest mtime among the pack's own files. A plain directory
    mtime does not move when an existing file inside it is REWRITTEN in
    place (only when an entry is added or removed), and filling in a
    narrative slot is exactly that: the same seven files, rewritten.

    Every filesystem call here is a BOUNDARY READ (report finding F12): an
    unreadable directory or a file that vanishes mid-walk raises OSError,
    converted to bs.BMStoreError rather than left to crash whatever called
    this, so detect's own "exit 0 always" promise can hold even when a
    pack directory is not readable."""
    try:
        times = [os.path.getmtime(pack_dir)]
        for name in os.listdir(pack_dir):
            full = os.path.join(pack_dir, name)
            if os.path.isfile(full):
                times.append(os.path.getmtime(full))
        return max(times)
    except OSError as e:
        raise bs.BMStoreError(
            "could not read %s to compute its freshness (%s)"
            % (pack_dir, e))


def _pack_dirname(date, slot):
    return "%s-%s" % (date, slot)


def _find_newest_pack(root):
    """The most recently touched directory under docs/handover, or None.

    A candidate that cannot be read (report finding F12: a permission
    error while scoring it) is skipped rather than left to crash the
    caller: detect's own promise is exit 0 always, and this is the
    function both detect and verify-close's auto-detection share."""
    handover_root = bs.safe_project_path(root, "docs", "handover")
    if not os.path.isdir(handover_root):
        return None
    try:
        names = os.listdir(handover_root)
    except OSError:
        return None
    candidates = [os.path.join(handover_root, n) for n in names
                 if os.path.isdir(os.path.join(handover_root, n))]
    if not candidates:
        return None
    scored = []
    for c in candidates:
        try:
            scored.append((_dir_mtime(c), c))
        except bs.BMStoreError:
            continue
    if not scored:
        return None
    scored.sort(key=lambda t: t[0], reverse=True)
    return scored[0][1]


def _find_newest_zip():
    d = _handovers_dir()
    if not os.path.isdir(d):
        return None
    candidates = [os.path.join(d, n) for n in os.listdir(d)
                 if n.startswith("BrotherMode-Handover-") and n.endswith(".zip")
                 and os.path.isfile(os.path.join(d, n))]
    if not candidates:
        return None
    candidates.sort(key=os.path.getmtime, reverse=True)
    return candidates[0]


def _zip_path_for(dirname):
    return os.path.join(_handovers_dir(), "BrotherMode-Handover-%s.zip" % dirname)


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _contained_pack_dir(root, raw):
    """A --pack argument, resolved to an absolute path INSIDE root, through
    the exact same bs.safe_project_path containment gate cmd_skeleton's
    --out already runs every write through: symlink-escape and hardlink
    checks on every path component, then a final realpath check.

    verify-close and zip used to skip this entirely (plain
    os.path.abspath and nothing else), so a --pack pointed at any
    absolute directory (report findings F13, A6d), at the project root
    itself (A6e), or reached through a symlinked component, was read or
    packaged unredacted. Raises bs.OwnershipRefused('path-escape') for
    anything outside the project, exactly as skeleton already does for
    --out.

    Uses os.path.realpath, not os.path.abspath, on the incoming path: the
    project root bs.require_root() hands back is itself already resolved
    (macOS routinely symlinks /var -> /private/var), and comparing a
    resolved root against an UNresolved caller path made every legitimate
    absolute --pack look like an escape (a real regression caught by this
    file's own test suite, not a report finding). Resolving both sides is
    also what correctly catches a pack_dir reached through a symlinked
    component: it dissolves to wherever that symlink really points, and
    the containment check below judges THAT."""
    abs_raw = os.path.realpath(os.path.abspath(raw))
    real_root = os.path.realpath(root)
    rel = os.path.relpath(abs_raw, real_root)
    parts = [] if rel == os.curdir else rel.split(os.sep)
    if not parts or parts[0] == os.pardir or os.path.isabs(rel):
        raise bs.OwnershipRefused(
            "path-escape",
            "%s resolves to %s, which is not inside the project root %s "
            "(or is the project root itself, which is not a valid pack "
            "directory); refusing to read or package it"
            % (raw, abs_raw, real_root))
    return bs.safe_project_path(root, *parts)


def _safe_pack_file(root, pack_dir, name):
    """One file's path inside an already-contained pack_dir, routed
    through the same bs.safe_project_path gate as _contained_pack_dir
    itself, so a pack FILE that is a symlink escaping the project (report
    finding F5, R2b: all seven pack files replaced with symlinks to one
    decoy outside the project) is refused rather than followed."""
    real_root = os.path.realpath(root)
    rel_dir = os.path.relpath(pack_dir, real_root)
    parts = [] if rel_dir == os.curdir else rel_dir.split(os.sep)
    return bs.safe_project_path(root, *(parts + [name]))


def _pack_files_for_zip(root, pack_dir):
    """Sorted (arcname, safe_full_path) pairs for every file the zip
    should contain: the flat files directly under pack_dir, each routed
    through _safe_pack_file (F5, F13).

    A SUBDIRECTORY directly under pack_dir raises rather than being
    silently skipped (report finding F7: an evidence/ folder used to
    vanish from the zip with no word said, and its later edits never
    moved the pack's tracked freshness either). This tool zips a flat
    pack only; a subdirectory is either flattened by hand or the pack is
    generated without one."""
    entries = []
    try:
        names = sorted(os.listdir(pack_dir))
    except OSError as e:
        raise bs.BMStoreError("could not list %s (%s)" % (pack_dir, e))
    for f in names:
        full = os.path.join(pack_dir, f)
        if os.path.isdir(full):
            raise bs.OwnershipRefused(
                "pack-subdirectory",
                "%s contains a subdirectory (%s); this tool zips a FLAT "
                "pack only. Silently leaving it out of the archive is "
                "worse than refusing (report finding F7): remove it, or "
                "flatten its contents into the pack, before zipping."
                % (pack_dir, f))
        entries.append((f, _safe_pack_file(root, pack_dir, f)))
    return entries


def _zip_bytes(dirname, entries):
    """The exact bytes a zip of `entries` (as cmd_zip and verify-close's
    freshness check both build) would contain, in memory. Used to compare
    what SHOULD be in the archive against what already is, by content
    rather than by mtime (report finding F9: an unchanged pack rewritten
    with the same bytes, by an editor or formatter, nudges the directory
    mtime forward with nothing to show for it, which used to FAIL
    verify-close forever with a remedy that could never clear it)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f, full in entries:
            zf.write(full, arcname="%s/%s" % (dirname, f))
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Store reads. Every one goes through a public bm_store.py function:
# ReadOnlyStore.dump() and bs.verify(). No SQL of this file's own.
# ---------------------------------------------------------------------------

def _open_read_only(root):
    """(store, None) or (None, the OwnershipRefused it raised). Never lets
    an unreadable or absent store crash a caller: every command that needs
    NO-DATA semantics (verify-close, detect) can act on the second value
    directly."""
    try:
        return bs.ReadOnlyStore(root), None
    except bs.OwnershipRefused as e:
        return None, e


def _gather(root):
    """(data, None) or (None, the refusal). `data` carries exactly the
    structural, already-scrubbed facts a pack page or a verify-close check
    needs: records (fences), their claimed paths, unacknowledged handovers,
    decisions, and the store's own verify() problems. Every free-text field
    (record names, claim paths, handover headings, decision text) is
    scrubbed with _scrub before it leaves this function, whether it is
    about to be written to a generated file or only compared in memory: a
    pack page is exactly the kind of ungated diagnostic surface _scrub
    exists for."""
    store, refusal = _open_read_only(root)
    if store is None:
        return None, refusal
    try:
        dump = store.dump(raw=True)
    finally:
        store.close()

    records = []
    for r in dump.get("records", []):
        records.append({
            "lifecycle_uuid": r["lifecycle_uuid"],
            "name": _scrub(r.get("name")),
            "state": r.get("state"),
            # TWO FIELDS, ON PURPOSE, and the pair is the whole point of
            # reading this store raw. `session_id` is the real value, and it
            # exists so verify-close's ownership test can compare against
            # what the store actually holds: the default redacted dump
            # withholds a session id that does not match this codebase's own
            # generated-id shapes, so a comparison against it would silently
            # match nothing. `session_display` is what any PAGE prints,
            # because a pack page is committed to git and zipped into a
            # handover, and the store classifies a session id as founder text
            # precisely because it could be anything. Renderers use the
            # display field; only comparisons touch the raw one.
            #
            # The display value comes from bs.export_column, the store's OWN
            # central withholding policy, rather than from _scrub or from any
            # rule restated here: _scrub covers secret shapes and absolute
            # paths, and a plain hand-typed id is neither, so it went straight
            # onto the page. Asking the control that already owns this
            # decision is also what keeps a second copy of the policy from
            # drifting away from the first.
            "session_id": r.get("session_id") or "",
            "session_display": _scrub(
                bs.export_column("records", "session_id",
                                 r.get("session_id"))) or "",
            "version": r.get("version"),
            "created_at": r.get("created_at"),
            "updated_at": r.get("updated_at"),
        })
    records.sort(key=lambda r: (r["name"], r["lifecycle_uuid"]))

    claims_by_uuid = {}
    for c in dump.get("claims", []):
        claims_by_uuid.setdefault(c["lifecycle_uuid"], []).append(
            _scrub(c.get("path")))

    handovers = []
    for h in dump.get("handovers", []):
        if h.get("delivered_at"):
            continue
        handovers.append({
            "handover_uuid": h["handover_uuid"],
            "lifecycle_uuid": h["lifecycle_uuid"],
            "created_at": h.get("created_at"),
            # Report finding F4: this is founder-typed prose, exactly the
            # class of column export_column's default rule (5) withholds
            # entirely. _scrub alone (secret shapes, absolute paths) is
            # not that policy; it is the gap the session_id comment above
            # already names. Ask the policy first, same as session_display.
            "heading": _scrub(
                bs.export_column("handovers", "heading", h.get("heading")))
                or "",
        })
    handovers.sort(key=lambda h: h["created_at"] or "")

    decisions = []
    for d in dump.get("decisions", []):
        decisions.append({
            "lifecycle_uuid": d["lifecycle_uuid"],
            "created_at": d.get("created_at"),
            # Same reasoning as handovers.heading above (F4): decisions.topic
            # and decisions.text are founder prose export_column withholds
            # by default; route through it before _scrub, not around it.
            "topic": _scrub(
                bs.export_column("decisions", "topic", d.get("topic")))
                or "",
            "text": _scrub(
                bs.export_column("decisions", "text", d.get("text")))
                or "",
        })
    decisions.sort(key=lambda d: d["created_at"] or "")

    try:
        verify_problems = [_scrub(p) for p in bs.verify(root)]
    except bs.BMStoreError as e:
        verify_problems = ["verify() could not run: %s" % e]

    return {"records": records, "claims_by_uuid": claims_by_uuid,
            "handovers": handovers, "decisions": decisions,
            "verify_problems": verify_problems}, None


# ---------------------------------------------------------------------------
# Pack rendering. The whole human region per page (I10): _existing_human_
# region recovers everything a person already typed from the NOTES_HEADING
# onward, render_page carries it through verbatim on every regeneration.
# ---------------------------------------------------------------------------

def _existing_human_region(path):
    """(ok, region) for a pack page that may already be on disk.

    `region` is None, and `ok` True, when the file does not exist yet:
    nothing to preserve, skeleton writes a fresh default block.

    Otherwise `region` is the ENTIRE slice of the existing file from its
    NOTES_HEADING line to end of file, byte for byte, and `ok` is True:
    this is the whole region I10 protects, not just the inside of the
    first human block. Report finding F8: reconstructing only ONE block's
    inner text and rebuilding the markers around it (the old approach)
    silently destroyed a second hand-added block, text after a quoted end
    marker, a stray marker before the real begin marker, and a paragraph
    appended after the end marker, because none of those live inside "the"
    block the old reader kept. Carrying everything from the heading
    onward forward untouched cannot lose any of them, whatever shape a
    person gave that region, because it is never reparsed at all: the
    funnel's own protect_human_blocks pass (bs._write_generated_file, via
    bs._human_block_spans) is what actually keeps the marker-delimited
    lines verbatim on the way to disk; this function's only job is to not
    let the text feeding that funnel lose bytes before it gets there.

    `ok` is False (region is None) when the file exists but NOTES_HEADING
    cannot be found in it: the heading itself was deleted, or predates
    this shape. There is no safe way to tell generated structure from
    human text without that anchor, and guessing is the choice that
    destroys human bytes (I10), so the caller must refuse to write rather
    than reconcile a guess."""
    if not os.path.isfile(path):
        return True, None
    with io.open(path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    idx = text.find(NOTES_HEADING)
    if idx == -1:
        return False, None
    return True, text[idx:]


def _pack_file_blocks(text):
    """Every top-level human block's inner text, in file order, as a list
    of strings. Mirrors bs._human_block_spans's own depth-tracking rule
    exactly (a second begin marker INSIDE a block is content, not a
    nested block) rather than restating a different one: report finding
    F8's note names this divergence as the cause of the A3c loss. Tolerant
    of an unterminated trailing block, the same reasoning
    tools/bm_packs.py's read_existing applies: it runs to EOF rather than
    being treated as absent."""
    blocks = []
    depth = 0
    buf = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped == HUMAN_BEGIN and not depth:
            depth = 1
            buf = []
            continue
        if stripped == HUMAN_END and depth:
            depth = 0
            blocks.append("\n".join(buf))
            continue
        if depth:
            buf.append(line)
    if depth:
        blocks.append("\n".join(buf))
    return blocks


def _pack_file_problem(path):
    """None when a pack file passes every structural check verify-close's
    check 1 makes, or a short reason string naming exactly what is wrong
    (report findings F2, F3, F10, F15): an unreadable, empty, or blank
    file; a file with no human block at all (a deleted marker is treated
    as unfilled, not as clean: F3); an empty human block (F2); or a
    surviving FILL-BY-HAND marker, matched case INSENSITIVELY (F15: the
    marker is a generated label, not shouted text, so retyping it in
    lowercase is not a defeat of the scan)."""
    try:
        with io.open(path, "rb") as fh:
            raw = fh.read()
    except OSError as e:
        return "could not be read (%s)" % e
    if not raw:
        return "is empty (0 bytes)"
    text = raw.decode("utf-8", errors="replace")
    if not text.strip():
        return "is blank"
    blocks = _pack_file_blocks(text)
    if not blocks:
        return ("has no human block at all (a deleted marker is treated "
                "as unfilled, never as clean)")
    joined = "\n".join(blocks)
    if not joined.strip():
        return "has an empty human block"
    if FILL_BY_HAND.lower() in joined.lower():
        return "still contains %s" % FILL_BY_HAND
    return None


def _find_ledger_dir(root):
    """The bm_lead.py handover-pack directory (Handover/ or
    Handover-<project>/), if one has already been generated, so 00 can
    point at it instead of duplicating it (spec section 5)."""
    try:
        names = os.listdir(root)
    except OSError:
        return None
    for name in sorted(names):
        if (name == "Handover" or name.startswith("Handover-")) \
                and os.path.isdir(os.path.join(root, name)):
            return name
    return None


def _struct_00(ctx):
    lines = ["Read this pack in this order: %s." % ", ".join(PACK_FILES), ""]
    ledger_dir = _find_ledger_dir(ctx["root"])
    if ledger_dir:
        lines.append(
            "The seven generated ledger pages from `bm_lead.py "
            "handover-pack` already live at `%s/`; read those first for "
            "the project-level situation, decisions, risks, calibrations, "
            "learnings, timeline and handbacks. This pack does not "
            "duplicate them." % ledger_dir)
    else:
        lines.append(
            "No `bm_lead.py handover-pack` ledger directory was found "
            "under the project root (Handover/ or Handover-<project>/). "
            "Generate one with `%s handover-pack --project-id <ID>` if "
            "this project uses bm_lead.py."
            % bs.invocation("bm_lead.py", os.path.join(HERE, "bm_lead.py")))
    lines.append("")
    # Report finding F11 (secondary): this used to check whether the copy
    # was ALREADY SITTING in pack_dir, which is only true on a REGENERATION
    # over a pack that already has one; on the FIRST generation the copy is
    # made AFTER this page is rendered, so this text always said "not
    # found" on a fresh pack even when the project has a command center,
    # while the real copy landed moments later and stdout truthfully said
    # "included". Reading ctx["command_center_included"], the SAME boolean
    # cmd_skeleton uses to decide whether to make the copy at all and what
    # to tell stdout, gives this page, the copy, and stdout one shared
    # source of truth instead of three that could disagree.
    if ctx["command_center_included"]:
        lines.append("A copy of `%s`, from the moment this pack was "
                     "generated, is included as `%s`."
                     % ("/".join(COMMAND_CENTER_REL), COMMAND_CENTER_NAME))
    else:
        lines.append("No `%s` was found in the project at generation time, "
                     "so no copy is included."
                     % "/".join(COMMAND_CENTER_REL))
    lines.append("")
    return lines


def _struct_01(ctx):
    data = ctx["data"]
    lines = ["## Records (fences) as of generation", ""]
    if not data["records"]:
        lines.append("No records exist in the store.")
    for r in data["records"]:
        claims = data["claims_by_uuid"].get(r["lifecycle_uuid"], [])
        lines.append(
            "- `%s` (%s) state=%s session=%s version=%s%s"
            % (r["name"], r["lifecycle_uuid"][:8], r["state"],
               r["session_display"] or "(none)", r["version"],
               (": " + ", ".join(claims)) if claims else ""))
    lines.append("")
    lines.append("## Decisions recorded")
    lines.append("")
    if not data["decisions"]:
        lines.append("None recorded.")
    for d in data["decisions"]:
        lines.append("- `%s` %s: %s (%s)"
                     % (d["lifecycle_uuid"][:8], d["created_at"], d["topic"],
                        d["text"]))
    lines.append("")
    lines.append("## Unacknowledged handovers")
    lines.append("")
    if not data["handovers"]:
        lines.append("None outstanding.")
    for h in data["handovers"]:
        lines.append(
            "- `%s` lifecycle %s at %s: %s"
            % (h["handover_uuid"][:8], h["lifecycle_uuid"][:8],
               h["created_at"], h["heading"] or "(no heading)"))
        lines.append("  clear with: %s handover-ack --handover %s"
                     % (_store_inv(), h["handover_uuid"]))
    lines.append("")
    return lines


def _struct_02(ctx):
    return ["No structural facts are generated for this page; the store "
           "has no concept of a mistake, only of records, decisions and "
           "handovers. Everything here is written by hand.", ""]


def _struct_03(ctx):
    data = ctx["data"]
    lines = ["## bm_store.py verify() problems at generation time", ""]
    if not data["verify_problems"]:
        lines.append("None. If a process fix belongs here anyway, it is "
                     "one this session found some other way; write it in "
                     "below.")
    else:
        for p in data["verify_problems"]:
            lines.append("- %s" % p)
    lines.append("")
    return lines


def _struct_04(ctx):
    data = ctx["data"]
    lines = ["## Candidates already recorded by the store", ""]
    if not data["handovers"]:
        lines.append("No unacknowledged handover exists to seed a next "
                     "loop from; the priority order below is entirely by "
                     "hand.")
    else:
        for h in data["handovers"]:
            lines.append("- follow up on handover `%s`: %s"
                         % (h["handover_uuid"][:8],
                            h["heading"] or "(no heading)"))
    lines.append("")
    return lines


def _struct_05(ctx):
    return [
        "Update the memory vault session log to the close moment (rule step "
        "6): record what changed, what was learned, and what is open.",
        "", "This page has no store-derived section: the vault lives "
        "outside this project's own store.", ""]


def _struct_06(ctx):
    data = ctx["data"]
    lines = ["## bm_store.py verify() output at generation time", ""]
    if not data["verify_problems"]:
        lines.append("healthy, 0 problem(s).")
    else:
        lines.append("%d problem(s):" % len(data["verify_problems"]))
        for p in data["verify_problems"]:
            lines.append("- %s" % p)
    lines.append("")
    lines.append(
        "The notes block below MUST open with a line starting with the "
        "exact word FINISHED, or the exact word UNFINISHED (and, if "
        "UNFINISHED, exactly where the baton lies). verify-close checks "
        "for it and refuses to close without it.")
    lines.append("")
    return lines


STRUCT_BUILDERS = {
    "00-READ-ME-FIRST.md": _struct_00,
    "01-HANDOVER.md": _struct_01,
    "02-LEARNINGS-AND-MISTAKES.md": _struct_02,
    "03-RULES-AND-PROCESS-FIXES.md": _struct_03,
    "04-NEXT-LOOPS-PRIORITIZED.md": _struct_04,
    "05-VAULT-AND-OBSIDIAN.md": _struct_05,
    "06-CLOSE-REPORT.md": _struct_06,
}


def render_page(name, ctx, existing_region):
    """One pack page: a freshly generated header and structural section,
    followed by the human region carried through UNCHANGED from what was
    already on disk (I10), or a fresh default block on first generation.

    `existing_region` is either None (first generation: write the file's
    default block) or the entire NOTES_HEADING-to-EOF slice
    _existing_human_region already read verbatim from the prior file.
    This function never reparses that region's markers; it only decides
    whether to keep it as-is or manufacture a fresh default one (see
    _existing_human_region for why: reparsing is what used to lose human
    bytes outside the first block, report finding F8)."""
    lines = [GENERATED_NOTE, "", "# %s" % PAGE_TITLES[name], ""]
    lines.extend(STRUCT_BUILDERS[name](ctx))
    header = "\n".join(lines).rstrip("\n") + "\n"
    if existing_region is None:
        region_lines = [NOTES_HEADING, "", HUMAN_BEGIN]
        region_lines.extend(DEFAULT_HUMAN[name].split("\n"))
        region_lines.append(HUMAN_END)
        existing_region = "\n".join(region_lines)
    return header + "\n" + existing_region.rstrip("\n") + "\n"


# ---------------------------------------------------------------------------
# Commands.
# ---------------------------------------------------------------------------

def cmd_skeleton(argv):
    _pos, kv = _parse(argv, {"out", "slot", "date"},
                      wants_value=("out", "slot", "date"))
    root = _root()
    date = kv.get("date") or _today()
    if not _DATE_RE.match(date):
        _err("bm_handover: --date must be YYYY-MM-DD, got %r" % date)
        return 2
    slot = kv.get("slot") or SLOT_DEFAULT
    if kv.get("out"):
        # Report finding F16: an ABSOLUTE --out used to be silently
        # reinterpreted as relative to the project root (its leading
        # slashes just stripped), so a typo'd absolute path landed
        # somewhere the caller never named and never a word was said.
        # Refusing loudly matches how safe_project_path itself already
        # refuses an absolute PART two lines below this one; --out gets
        # the same rule before it ever reaches that function.
        if os.path.isabs(kv["out"]):
            _err("bm_handover: --out must be relative to the project "
                 "root, got the absolute path %r; refusing to silently "
                 "reinterpret it as relative" % kv["out"])
            return 2
        parts = [p for p in kv["out"].strip("/").split("/") if p]
        if not parts:
            _err("bm_handover: --out %r has no usable path component"
                 % kv["out"])
            return 2
        pack_dir = bs.safe_project_path(root, *parts)
    else:
        pack_dir = bs.safe_project_path(
            root, "docs", "handover", _pack_dirname(date, slot))
    data, refusal = _gather(root)
    if data is None:
        raise refusal
    if not os.path.isdir(pack_dir):
        os.makedirs(pack_dir)
    # Report finding F11 (secondary): decide ONCE, before any page is
    # rendered, whether the project has a command center to copy. This is
    # the single fact _struct_00's text, the actual copy below, and the
    # stdout line all now read, instead of _struct_00 checking the
    # DESTINATION (which does not have the copy yet on a first run) while
    # stdout and the copy itself checked the SOURCE.
    cc_src = bs.safe_project_path(root, *COMMAND_CENTER_REL)
    copied_cc = os.path.isfile(cc_src)
    ctx = {"root": root, "pack_dir": pack_dir, "data": data,
           "command_center_included": copied_cc}
    written = []
    for name in PACK_FILES:
        path = os.path.join(pack_dir, name)
        ok, existing_region = _existing_human_region(path)
        if not ok:
            raise bs.BMStoreError(
                "%s already exists but its %r heading is missing or was "
                "altered, so there is no safe anchor telling generated "
                "structure apart from human text in it. Guessing is the "
                "choice that destroys human bytes (I10, report finding "
                "F8), so this refuses to write it at all: restore the "
                "heading by hand, or move the file aside, then run "
                "skeleton again." % (path, NOTES_HEADING))
        text = render_page(name, ctx, existing_region)
        bs.write_generated_document(path, text)
        written.append(name)
    if copied_cc:
        shutil.copy2(cc_src, os.path.join(pack_dir, COMMAND_CENTER_NAME))
    rel = os.path.relpath(pack_dir, root)
    _out("wrote pack %s" % rel)
    _out("  %d file(s): %s" % (len(written), ", ".join(written)))
    _out("  command center copy: %s"
         % ("included" if copied_cc else "not found at %s, skipped"
                                         % "/".join(COMMAND_CENTER_REL)))
    return 0


def cmd_verify_close(argv):
    _pos, kv = _parse(argv, {"pack", "session"},
                      wants_value=("pack", "session"))
    try:
        root = _root()
    except bs.OwnershipRefused as e:
        _out_scrubbed("NO-DATA: %s" % e)
        return NODATA

    if kv.get("pack"):
        try:
            pack_dir = _contained_pack_dir(root, kv["pack"])
        except bs.OwnershipRefused as e:
            # Report findings F5, F13, R2b: --pack used to go straight to
            # os.path.abspath with no containment at all. A pack argument
            # that escapes the project is a FAIL, not a crash: this is the
            # same class of "must never crash" boundary read as F12, just
            # surfaced through the ceremony's own verdict channel instead.
            _out_scrubbed("FAIL: --pack %s" % e)
            return FAIL
    else:
        pack_dir = _find_newest_pack(root)
    if not pack_dir or not os.path.isdir(pack_dir):
        _out_scrubbed(
            "NO-DATA: no handover pack found under docs/handover (pass "
            "--pack DIR, or run `%s skeleton` first)" % _inv())
        return NODATA

    data, refusal = _gather(root)
    if data is None:
        _out_scrubbed("NO-DATA: %s" % refusal)
        return NODATA

    # Check 1: every pack file exists, is not a symlink escaping the
    # project (F5, R2b), is not empty or blank (F2), carries at least one
    # human block (F3: a deleted marker is unfilled, not clean), that
    # block is not itself empty (F2), and does not still say FILL-BY-HAND,
    # matched case insensitively (F15).
    for name in PACK_FILES:
        try:
            path = _safe_pack_file(root, pack_dir, name)
        except bs.OwnershipRefused as e:
            _out_scrubbed("FAIL: %s %s" % (name, e))
            return FAIL
        if not os.path.isfile(path):
            _out_scrubbed(
                "FAIL: %s is missing from the pack at %s" % (name, pack_dir))
            return FAIL
        problem = _pack_file_problem(path)
        if problem:
            _out_scrubbed("FAIL: %s %s" % (name, problem))
            return FAIL

    # Check 1b (F11): a copy of the command center page is part of the
    # pack, per section 3 step 1, whenever the PROJECT has one. verify-close
    # used to iterate only PACK_FILES (the seven narrative/close files) and
    # never looked for it, so a pack missing the page the rule names passed.
    cc_src = bs.safe_project_path(root, *COMMAND_CENTER_REL)
    if os.path.isfile(cc_src):
        try:
            cc_in_pack = _safe_pack_file(root, pack_dir, COMMAND_CENTER_NAME)
        except bs.OwnershipRefused as e:
            _out_scrubbed("FAIL: %s %s" % (COMMAND_CENTER_NAME, e))
            return FAIL
        if not os.path.isfile(cc_in_pack):
            _out_scrubbed(
                "FAIL: the project has %s but the pack at %s carries no "
                "%s copy; run `%s skeleton` again to refresh it"
                % ("/".join(COMMAND_CENTER_REL), pack_dir,
                   COMMAND_CENTER_NAME, _inv()))
            return FAIL

    # Check 2: 06-CLOSE-REPORT.md's FIRST human block opens, on its first
    # NON-EMPTY line, with a whole word FINISHED or UNFINISHED (F10: a
    # prior version accepted the word anywhere in the file, inside a code
    # fence, and as a prefix, not only as the block's opening line).
    close_path = _safe_pack_file(root, pack_dir, "06-CLOSE-REPORT.md")
    with io.open(close_path, encoding="utf-8", errors="replace") as fh:
        close_blocks = _pack_file_blocks(fh.read())
    first_line = ""
    if close_blocks:
        for line in close_blocks[0].split("\n"):
            if line.strip():
                first_line = line.strip()
                break
    if not _STATUS_LINE_RE.match(first_line):
        _out_scrubbed(
            "FAIL: 06-CLOSE-REPORT.md's human block must OPEN, on its "
            "first non-empty line, with a line starting with the exact "
            "word FINISHED or the exact word UNFINISHED; found %r"
            % (first_line or "(nothing)"))
        return FAIL

    # Check 3: a zip exists for this pack, and its CONTENT matches what
    # zipping the pack right now would produce (F9: content based, not
    # mtime based, so a pack re-saved with byte-identical content, which
    # moves the directory mtime but changes nothing zip would write, is
    # fresh by definition instead of FAILing forever with a remedy that
    # can never clear it).
    dirname = os.path.basename(pack_dir.rstrip("/"))
    zip_path = _zip_path_for(dirname)
    if not os.path.isfile(zip_path):
        _out_scrubbed(
            "FAIL: no zip found for this pack at %s; run `%s zip --pack "
            "%s`" % (zip_path, _inv(), pack_dir))
        return FAIL
    try:
        entries = _pack_files_for_zip(root, pack_dir)
    except bs.OwnershipRefused as e:
        _out_scrubbed("FAIL: %s" % e)
        return FAIL
    current_hash = hashlib.sha256(_zip_bytes(dirname, entries)).hexdigest()
    if current_hash != _sha256_file(zip_path):
        _out_scrubbed(
            "FAIL: the zip at %s does not match the pack's current "
            "content at %s; run `%s zip --pack %s` again"
            % (zip_path, pack_dir, _inv(), pack_dir))
        return FAIL

    # Check 4: the closing session owns no unparked record still (F6: every
    # UNPARKED_STATES member, not just "active"). Report finding F1: the
    # rule's own prescribed invocation omits --session entirely, which used
    # to skip this check outright; now it falls back to the store's own
    # notion of the current session (_current_session_id), and if THAT
    # cannot be determined either, the verdict is NO-DATA, never PASS.
    session = kv.get("session") or _current_session_id()
    if not session:
        _out_scrubbed(
            "NO-DATA: no --session was given and no session could be "
            "determined from BM_FENCE_SESSION_ID or CLAUDE_SESSION_ID; "
            "the unparked-records check cannot run without knowing which "
            "session is closing. Pass --session explicitly.")
        return NODATA
    owned = [r for r in data["records"]
            if r["state"] in UNPARKED_STATES and r["session_id"] == session]
    if owned:
        names = ", ".join(
            "%s (%s)" % (r["name"], r["lifecycle_uuid"][:8])
            for r in owned)
        _out_scrubbed("FAIL: session %s still owns %d unparked record(s): %s"
                     % (session, len(owned), names))
        return FAIL

    _out_scrubbed("PASS: %s is ready to close." % pack_dir)
    return PASS


def cmd_zip(argv):
    _pos, kv = _parse(argv, {"pack"}, wants_value=("pack",))
    root = _root()
    # Report findings F13, A6d, A6e: --pack used to go straight to
    # os.path.abspath with no containment at all, so any absolute
    # directory (an unrelated one, or the project root itself) was
    # packaged unredacted into the founder's own handovers archive.
    # Routed through the same gate cmd_skeleton's --out already uses.
    pack_dir = _contained_pack_dir(root, kv["pack"]) if kv.get("pack") \
        else _find_newest_pack(root)
    if not pack_dir or not os.path.isdir(pack_dir):
        _err("bm_handover: no pack found (pass --pack DIR, or run `%s "
             "skeleton` first)" % _inv())
        return 2

    dirname = os.path.basename(pack_dir.rstrip("/"))
    zip_path = _zip_path_for(dirname)
    zdir = os.path.dirname(zip_path)
    if not os.path.isdir(zdir):
        os.makedirs(zdir)

    # Report findings F5, F7, R2b: every listed file is routed through the
    # same containment gate (refuses a symlink escaping the project), and
    # a subdirectory is refused loudly rather than silently left out.
    entries = _pack_files_for_zip(root, pack_dir)
    data = _zip_bytes(dirname, entries)

    if os.path.isfile(zip_path) \
            and hashlib.sha256(data).hexdigest() == _sha256_file(zip_path):
        _out("zip unchanged: %s (%d file(s)), idempotent, not rewritten"
             % (zip_path, len(entries)))
        return 0

    tmp_path = zip_path + ".tmp-%d" % os.getpid()
    with open(tmp_path, "wb") as fh:
        fh.write(data)
    os.replace(tmp_path, zip_path)
    _out("wrote %s (%d file(s))" % (zip_path, len(entries)))
    return 0


def cmd_detect(argv):
    _parse(argv, set())
    try:
        root = _root()
    except bs.OwnershipRefused as e:
        _out_scrubbed("NO-DATA: %s" % e)
        return 0

    lines = []
    # Report finding F12: this whole command promises exit 0 always ("it
    # informs; the start half of the rule is what acts"), so every boundary
    # read below (a directory that exists but cannot be listed, a file
    # that vanishes mid-check) degrades to a stated line instead of an
    # uncaught traceback.
    newest_pack = _find_newest_pack(root)
    if newest_pack:
        try:
            age = _fmt_age(time.time() - _dir_mtime(newest_pack))
            lines.append("newest pack: %s (%s old)" % (newest_pack, age))
        except bs.BMStoreError as e:
            lines.append("newest pack: %s (could not read it to compute "
                         "its age: %s)" % (newest_pack, e))
    else:
        lines.append("NO-DATA: no handover pack exists yet under "
                     "docs/handover; run `%s skeleton`" % _inv())

    newest_zip = _find_newest_zip()
    if newest_zip:
        try:
            age = _fmt_age(time.time() - os.path.getmtime(newest_zip))
            lines.append("newest zip: %s (%s old)" % (newest_zip, age))
        except OSError as e:
            lines.append("newest zip: %s (could not read it to compute "
                         "its age: %s)" % (newest_zip, e))
    else:
        lines.append("NO-DATA: no handover zip exists yet at %s"
                     % _handovers_dir())

    data, refusal = _gather(root)
    if data is None:
        lines.append("NO-DATA: could not read the store (%s)" % refusal)
    else:
        if data["handovers"]:
            lines.append("unacknowledged handovers: %d" % len(data["handovers"]))
            for h in data["handovers"]:
                lines.append(
                    "  - `%s` lifecycle %s at %s: %s"
                    % (h["handover_uuid"][:8], h["lifecycle_uuid"][:8],
                       h["created_at"], h["heading"] or "(no heading)"))
                lines.append("    clear with: %s handover-ack --handover %s"
                             % (_store_inv(), h["handover_uuid"]))
        else:
            lines.append("unacknowledged handovers: none")

        stall, findings = None, None
        try:
            stall = _load("bm_stall")
        except Exception as e:
            lines.append("NO-DATA: could not load tools/bm_stall.py (%s)"
                         % e)
        if stall is not None:
            store, sweep_refusal = _open_read_only(root)
            if store is None:
                lines.append("NO-DATA: could not sweep for dead-owner "
                             "leftovers (%s)" % sweep_refusal)
            else:
                try:
                    findings = stall.sweep(bs, store)
                finally:
                    store.close()
        if findings is not None:
            if findings:
                lines.append("dead-owner leftovers: %d" % len(findings))
                for f in findings:
                    lines.append("  - [%s/%s] %s"
                                 % (f["severity"], f["kind"],
                                    f["name"] or "(unnamed)"))
                    lines.append("    %s" % f["message"])
                    for action in f["actions"]:
                        lines.append("    -> %s" % action["command"])
            else:
                lines.append("dead-owner leftovers: none")

    for line in lines:
        _out_scrubbed(line)
    return 0


COMMANDS = {"skeleton": cmd_skeleton, "verify-close": cmd_verify_close,
           "zip": cmd_zip, "detect": cmd_detect}


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        _out(__doc__.strip())
        _out("")
        _out("commands: %s" % ", ".join(sorted(COMMANDS)))
        return 0
    cmd = argv[0]
    if cmd not in COMMANDS:
        _err("bm_handover: unknown command %r (known: %s)"
             % (cmd, ", ".join(sorted(COMMANDS))))
        return 2
    try:
        return COMMANDS[cmd](argv[1:])
    except bs.OwnershipRefused as e:
        _err("refused (%s): %s" % (e.reason, e))
        return 2
    except bs.BMStoreError as e:
        _err("bm_handover: %s" % e)
        return 2


def cli():
    sys.exit(main(sys.argv[1:]))


if __name__ == "__main__":
    cli()
