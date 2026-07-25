#!/usr/bin/env python3
"""BrotherMode thread mode: persistent feature threads with a chief command center.

WHY THIS EXISTS
  One session that builds everything fills its context with the detail of every
  feature at once, then compacts, and coordination detail is what gets summarized
  away. Thread mode splits the work the way a small company does: one chief who
  only coordinates (so its context stays small and it almost never compacts), and
  one persistent thread per key feature that keeps its own deep domain context for
  days instead of re-learning the same architecture every morning.

THE CONTRACT (three files per thread, so coordination needs no new infrastructure)
  threads/<name>/STATE.md   the thread's own fence, plan, and next intent
  threads/<name>/inbox.md   directives INTO the thread. ONLY the chief writes here.
  threads/<name>/outbox.md  advancement OUT of the thread. ONLY the thread writes.
  threads/<name>/digest.md  the always-current handover (see REVERSIBILITY below)
  The single-writer law therefore applies to coordination itself: one writer per
  mailbox, so two threads can never scribble over each other's messages.

REVERSIBILITY IS THE POINT (founder requirement, 2026-07-24)
  Thread mode must be switchable OFF mid-project with no chaos and no lost context.
  That is only safe if the handover already exists when you flip the switch, so
  every thread keeps a cheap digest current as it works (`checkpoint`), written to
  disk, never held in context. `off` then DRAINS every digest into the project's
  root STATE.md and PARKS the threads: nothing is deleted, every thread stays
  resumable, and the chief continues solo with zero re-exploration.

INVARIANTS
  - Never blocks: every path exits 0.
  - No network. No git. Pure file I/O over the project's own threads/ directory.
  - Nothing auto-flips: `recommend` only PRINTS advice; only the founder runs
    `on` or `off`.
  - Cap of 3 active threads, enforced mechanically at `start`.
"""
import io, json, os, re, sys, datetime

_REG_MOD = None


def _registry():
    """Load bm_registry.py by path (cached) so bm_threads works from any cwd."""
    global _REG_MOD
    if _REG_MOD is None:
        import importlib.util
        here = os.path.dirname(os.path.abspath(__file__))
        spec = importlib.util.spec_from_file_location(
            "bm_registry_for_threads", os.path.join(here, "bm_registry.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _REG_MOD = mod
    return _REG_MOD


THREADS_DIRNAME = "threads"
MODE_FILE = "thread-mode.json"          # lives in threads/, records mode + history
MAX_ACTIVE = int(os.environ.get("BROTHERMODE_MAX_THREADS", "3"))
DIGEST_CAP = 4000                        # chars kept per digest: a handover, not a log


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def root(cwd=None):
    return os.path.join(cwd or os.getcwd(), THREADS_DIRNAME)


def safe_name(n):
    return re.sub(r"[^A-Za-z0-9_.-]", "-", (n or "").strip())[:60]


def read(path, cap=None):
    try:
        s = io.open(path, encoding="utf-8", errors="replace").read()
        return s[:cap] if cap else s
    except OSError:
        return ""


def write(path, text):
    """Write a file, creating parents. Returns True on success, never raises: a
    coordination file failing to write must not take down a work session."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        # Crash-atomic via the registry, which owns the primitive. This covers
        # thread-mode.json (through save_mode) and every thread file: a
        # truncating write here could empty the mode file, and an empty mode
        # file reads as "thread mode was never on", stranding live threads.
        _registry().atomic_write(path, text)
        return True
    except OSError:
        return False


def append(path, text):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with io.open(path, "a", encoding="utf-8") as f:
            f.write(text.rstrip("\n") + "\n")
        return True
    except OSError:
        return False


# REDACTION. bm_registry.py is the single owner of the redaction fallback now
# (this used to be a duplicated pattern set here); every use below calls
# _registry().redact_text(...) so a secret is caught at the write, not later.


def _with_mode_lock(fn, cwd=None):
    """Mutual exclusion around every read-modify-write of the mode file.

    Without this, two threads starting at once each read the old file and the
    second write wins, so a thread exists on disk but is missing from the
    registry: invisible to the dashboard and, worse, skipped by `off`, which
    would silently lose its context. That is the one guarantee thread mode must
    not break, so the registry update is locked, not hoped over.

    Locking is DELEGATED to bm_registry.locked_call, the one locking primitive
    in the system, for the same reason redaction was: this file used to carry
    its own copy that swallowed every failure silently, so on a platform
    without fcntl the registry warned that coordination was degraded while
    thread-mode updates raced on quietly. One primitive means one behaviour and
    one warning, instead of two half-truths.
    """
    lockpath = os.path.join(root(cwd), ".mode.lock")
    try:
        reg = _registry()
    except Exception as e:
        # The registry is how we lock AND how we warn, so if it cannot load we
        # have neither. Say so directly and still run: never block a session.
        sys.stderr.write("bm_threads: WARNING: running WITHOUT a mode-file lock "
                         "(registry unavailable: %r). Concurrent thread starts "
                         "can race.\n" % (e,))
        return fn()
    return reg.locked_call(lockpath, fn)


def load_mode(cwd=None):
    """Read the mode file. Anything unreadable, unparsable, or not a JSON object
    is an empty mode, so a hand-edited file cannot make every command raise on
    the first .get() it tries."""
    p = os.path.join(root(cwd), MODE_FILE)
    try:
        d = json.loads(read(p) or "{}")
    except Exception:
        return {}
    if not isinstance(d, dict):
        return {}
    if not isinstance(d.get("threads"), dict):
        d.pop("threads", None)
    return d


def save_mode(d, cwd=None):
    return write(os.path.join(root(cwd), MODE_FILE),
                 json.dumps(d, indent=2, sort_keys=True) + "\n")


def _history(d):
    """The mode file's history list, repaired if a hand edit left it something
    else. Appending to a non-list raised out of every command that records an
    event, which is the same defect shape as a malformed record in the
    registry: stored data must never crash a tool."""
    if not isinstance(d.get("history"), list):
        d["history"] = []
    return d["history"]


def threads(cwd=None, state=None):
    """List thread names, optionally filtered by state (active|parked)."""
    m = load_mode(cwd).get("threads", {})
    names = sorted(m)
    if state:
        # Defensive: an entry that is not a dict has no state and is never
        # counted as active, rather than raising here.
        names = [n for n in names if isinstance(m[n], dict) and m[n].get("state") == state]
    return names


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------

def cmd_recommend(argv):
    """Advice ONLY. Never flips the mode: a surprise mode change mid-project is
    exactly the disruption the founder ruled out."""
    n = 0
    try:
        n = int(argv[0])
    except (IndexError, ValueError):
        # No count given: infer from thread dirs that already exist.
        n = len(threads())
    mode = load_mode().get("mode", "off")
    if mode == "on":
        print("thread mode is already ON. `bm_threads.py off` drains and parks it.")
        return
    if n >= 3:
        print("RECOMMENDATION: %d parallel features detected or declared. Thread mode "
              "pays off at 3 or more (each thread keeps its own context, the chief "
              "stays small and stops compacting)." % n)
        print("  turn it on:  python3 tools/bm_threads.py on")
        print("  it stays off until you run that. Nothing flips by itself.")
    else:
        print("RECOMMENDATION: stay single-orchestrator (%d feature(s)). Below 3 "
              "parallel features the per-thread overhead costs more than it saves." % n)


def cmd_on(argv):
    # Read-modify-write under the lock, like every other mutation of this file.
    # Unlocked, this raced with a concurrent `start` or `off` and the loser's
    # write vanished, which is the lost-thread case the lock exists to prevent.
    def _flip():
        d = load_mode()
        if d.get("mode") == "on":
            return d.get("since", "?")
        d["mode"] = "on"
        d["since"] = now()
        d.setdefault("threads", {})
        _history(d).append({"ts": now(), "event": "on"})
        if not save_mode(d):
            return "WRITE_FAILED"
        return None
    already = _with_mode_lock(_flip)
    if already == "WRITE_FAILED":
        print("COULD NOT TURN THREAD MODE ON: thread-mode.json is not writable.")
        print("  Nothing changed. Fix that file (permissions or disk), then retry.")
        return
    if already is not None:
        print("thread mode already ON since %s" % already)
        return
    print("thread mode ON. Cap: %d active threads." % MAX_ACTIVE)
    print("  start one:  python3 tools/bm_threads.py start <feature> \"<objective>\"")
    print("  review all: python3 tools/bm_threads.py dashboard")


def cmd_start(argv):
    d = load_mode()
    if d.get("mode") != "on":
        print("thread mode is OFF. Run `on` first (nothing starts implicitly).")
        return
    name = safe_name(argv[0] if argv else "")
    if not name:
        print("usage: start <feature-name> \"<objective>\" [--files <path> ...]")
        return
    files, end = [], len(argv)
    if "--files" in argv:
        end = argv.index("--files")
        files = [a for a in argv[end + 1:] if not a.startswith("--")]
    objective = " ".join(argv[1:end]).strip() or "(objective not stated)"
    reg = _registry()
    base = os.path.join(root(), name)
    # EVERYTHING happens under the mode lock, cap check FIRST. The cap used to
    # be re-checked after the claim, so a refused start printed "not registered"
    # and still left an ACTIVE record behind: files fenced by a thread that does
    # not exist, refusing later claims in the name of an owner the dashboard
    # never shows. The outcome must be atomic: either the record and the thread
    # both exist, or neither does.
    outcome = {}
    def _register():
        # Re-read INSIDE the lock: any copy loaded before the lock may be stale.
        dd = load_mode()
        # Mode is rechecked HERE, not only before the lock. A start that queued
        # behind a concurrent `off` would otherwise wake up and create an ACTIVE
        # record and thread files in a system that is now OFF, so the record
        # would never be absorbed and its digest would be lost.
        if dd.get("mode") != "on":
            outcome["mode_off"] = True
            return False
        act = [n for n, m in dd.get("threads", {}).items()
               if isinstance(m, dict) and m.get("state") == "active"]
        if name not in act and len(act) >= MAX_ACTIVE:
            outcome["cap"] = act
            return False
        ok, conflict = reg.claim(name, "persistent", objective, files, tier="T2")
        if not ok:
            outcome["conflict"] = conflict
            return False
        # reg.claim() redacts its OWN stored copy of the objective, but that does
        # not touch these thread-local files: redact once here so STATE.md,
        # digest.md, and the mode file (and everything derived from them: the
        # dashboard, adopt, off) never hold the raw text either.
        obj = reg.redact_text(objective)
        # Every one of these is checked. A start that reports success with a
        # missing digest.md has created a thread whose handover is empty, so
        # `off` would drain nothing and the work would vanish at the exit.
        wrote = []
        wrote.append(write(os.path.join(base, "STATE.md"),
              "# Thread: %s\n\n## Objective\n%s\n\n## Fence (files this thread may write)\n"
              "(declare before writing; single-writer law applies per file)\n\n"
              "## Plan and next intent\n- next: (write the next intent BEFORE acting)\n" % (name, obj)))
        wrote.append(write(os.path.join(base, "inbox.md"),
              "# Inbox for %s\nDirectives from the chief. ONLY the chief writes here.\n\n" % name))
        wrote.append(write(os.path.join(base, "outbox.md"),
              "# Outbox from %s\nAdvancement for the chief. ONLY this thread writes here.\n\n" % name))
        # The digest exists from minute one, so an exit is lossless even immediately.
        wrote.append(write(os.path.join(base, "digest.md"),
              "# Handover digest: %s\n_updated %s_\n\n## Objective\n%s\n\n## Decisions\n(none yet)\n\n"
              "## Files touched\n(none yet)\n\n## Next intent\n(not yet stated)\n" % (name, now(), obj)))
        if not all(wrote):
            # Release the fence: a record pointing at thread files that do not
            # exist would keep those paths claimed by a thread nobody can use.
            # Return DELIBERATELY unchecked: this is best-effort cleanup on a
            # path that already reports failure to the founder, and a second
            # error message about the cleanup of a failure helps nobody.
            reg.close(name, state="failed-start")
            outcome["files_failed"] = True
            return False
        dd.setdefault("threads", {})[name] = {"state": "active", "objective": obj,
                                              "started": now()}
        _history(dd).append({"ts": now(), "event": "start", "thread": name})
        if not save_mode(dd):
            reg.close(name, state="failed-start")
            outcome["mode_failed"] = True
            return False
        return True
    if not _with_mode_lock(_register):
        conflict = outcome.get("conflict")
        if outcome.get("files_failed"):
            print("START FAILED: could not write this thread's files (permissions "
                  "or disk).")
            print("  The work record was released, so no files stay fenced by a "
                  "thread that does not exist. Nothing else changed.")
            return
        if outcome.get("mode_failed"):
            print("START FAILED: the thread files were written but thread-mode.json "
                  "could not be updated.")
            print("  The work record was released so nothing stays half-claimed. "
                  "Fix that file, then run `start` again.")
            return
        if outcome.get("mode_off"):
            print("thread mode went OFF while this start was waiting for the lock.")
            print("  Nothing was created, so nothing is stranded outside the drain.")
            print("  Run `on` again if you still want this thread.")
            return
        if conflict is not None:
            # files_line, not a bare join: the conflicting record comes off disk
            # and a malformed files field there must not swallow the refusal.
            print("OVERLAP: '%s' declares files already claimed by record '%s' (%s)."
                  % (name, conflict.get("id"), reg.files_line(conflict.get("files", []))))
            print("  Park or narrow that record first; two writers on one file is the "
                  "one thing the single-writer law forbids.")
        else:
            print("CAP: %d active threads already (%s). Park one before starting another; "
                  "your review capacity is the real constraint."
                  % (MAX_ACTIVE, ", ".join(outcome.get("cap", []))))
        print("  Nothing was created: no thread files, no work record.")
        return
    print("thread '%s' created at %s" % (name, base))
    print("  the thread session should read STATE.md + inbox.md, and write outbox.md + digest.md")


def cmd_checkpoint(argv):
    """Called BY a thread as it works. Keeps the handover digest current so that
    switching thread mode off is instant and lossless at any moment. Cheap by
    design: a few hundred characters to disk, nothing added to any context."""
    if not argv:
        print("usage: checkpoint <thread> [--topic T] [--decision X] [--files Y] [--next Z]")
        return
    name = safe_name(argv[0])
    base = os.path.join(root(), name)
    if not os.path.isdir(base):
        print("checkpoint: no thread %r (start it first)" % name)
        return
    kv, key = {}, None
    for a in argv[1:]:
        if a.startswith("--"):
            key = a[2:]
            kv[key] = []
        elif key:
            kv[key].append(a)
    reg = _registry()
    # Redact at the WRITE: a digest is absorbed into STATE.md on exit.
    dec = reg.redact_text(" ".join(kv.get("decision", [])))
    files = reg.redact_text(" ".join(kv.get("files", [])))
    nxt = reg.redact_text(" ".join(kv.get("next", [])))
    topic = reg.redact_text(" ".join(kv.get("topic", [])))
    if dec and topic:
        # Cross-record clash: two threads deciding the same topic differently
        # must be surfaced, not silently overwritten.
        _, clash = reg.decide(name, topic, dec)
        if clash:
            print("CLASH on topic '%s': record '%s' already decided: %s"
                  % (topic, clash["record"], clash["text"]))
            print("  Both decisions are recorded. Reconcile before building further.")
    cur = read(os.path.join(base, "digest.md"))
    obj = ""
    m = re.search(r"## Objective\n(.+?)\n", cur, re.S)
    if m:
        obj = m.group(1).strip()
    # Decisions accumulate (they are the expensive thing to re-derive); the rest
    # is replaced, because only the LATEST matters for a handover.
    prior = re.findall(r"^- (.+)$", cur.split("## Decisions", 1)[-1].split("##", 1)[0], re.M) if "## Decisions" in cur else []
    prior = [p for p in prior if p != "(none yet)"]
    if dec:
        prior.append("%s  (%s)" % (dec, now()[:10]))
    body = ["# Handover digest: %s" % name, "_updated %s_" % now(), "",
            "## Objective", obj or "(not stated)", "",
            "## Decisions"]
    body += ["- " + p for p in prior[-20:]] or ["(none yet)"]
    body += ["", "## Files touched", files or "(unchanged)", "",
             "## Next intent", nxt or "(not yet stated)", ""]
    digest_text = "\n".join(body)[:DIGEST_CAP]
    # The digest is the handover. Both copies are checked: the thread-local file
    # a human reads, and the registry mirror that `off` actually drains. A
    # checkpoint that reports success while the mirror never landed is how a
    # lossless exit quietly stops being lossless.
    file_ok = write(os.path.join(base, "digest.md"), digest_text)
    mirror_ok = reg.set_digest(name, digest_text)
    outbox_ok = True
    if nxt or dec:
        outbox_ok = append(os.path.join(base, "outbox.md"),
               "- %s %s%s" % (now()[:16], (dec + " | " if dec else ""), ("next: " + nxt) if nxt else ""))
    if not mirror_ok:
        print("CHECKPOINT NOT FULLY SAVED: the registry mirror of this digest could "
              "not be written, so `off` would NOT absorb this handover.")
        print("  The thread's own digest.md %s. Fix the registry file and run "
              "`checkpoint` again." % ("was written" if file_ok else "also failed"))
        return
    if not file_ok:
        print("checkpoint recorded in the registry, but this thread's digest.md "
              "could not be written.")
        print("  The handover is safe (`off` drains the registry), only the local "
              "copy is stale.")
        return
    if not outbox_ok:
        print("checkpoint saved, but the outbox line could not be written: the "
              "chief's dashboard will not show this advancement.")
        return
    print("checkpoint written for '%s'" % name)


def cmd_send(argv):
    """Chief -> thread. The ONLY writer of an inbox is the chief."""
    if len(argv) < 2:
        print("usage: send <thread> <message...>")
        return
    name = safe_name(argv[0])
    base = os.path.join(root(), name)
    if not os.path.isdir(base):
        print("send: no thread %r" % name)
        return
    if not append(os.path.join(base, "inbox.md"),
                  "- [%s] %s" % (now()[:16], _registry().redact_text(" ".join(argv[1:])))):
        print("SEND FAILED: could not write to %s's inbox." % name)
        print("  The thread has NOT received this. Fix that file, then send again.")
        return
    print("sent to '%s'" % name)


def cmd_dashboard(argv):
    """The command center: every thread's advancement on one screen, so the founder
    reviews the whole project without opening any thread."""
    d = load_mode()
    mode = d.get("mode", "off")
    tmap = d.get("threads", {})
    reg = _registry()
    # safe_str: a hand-edited mode value that is not a string has no .upper(),
    # and the header is the first thing printed, so it took the whole dashboard
    # down with it.
    print("BROTHERMODE THREADS  mode=%s  cap=%d  (%s)"
          % (reg.safe_str(mode).upper(), MAX_ACTIVE, os.getcwd()))
    if not tmap:
        print("  no threads. `recommend <n>` for advice, `on` then `start <feature>` to begin.")
        return
    for name in sorted(tmap):
        # Defensive: the mode file is JSON on disk, so an entry can be any type
        # after a hand edit. One malformed entry used to raise here and stop the
        # whole dashboard, hiding every thread listed after it.
        meta = tmap[name] if isinstance(tmap[name], dict) else {}
        base = os.path.join(root(), name)
        dg = read(os.path.join(base, "digest.md"))
        nxt = ""
        m = re.search(r"## Next intent\n(.+?)(\n|$)", dg)
        if m:
            nxt = m.group(1).strip()
        outs = [l for l in read(os.path.join(base, "outbox.md")).splitlines() if l.startswith("- ")]
        inbox_open = len([l for l in read(os.path.join(base, "inbox.md")).splitlines() if l.startswith("- ")])
        print("\n  [%s] %s" % (reg.safe_str(meta.get("state", "?")).upper(), name))
        print("      objective : %s" % (reg.safe_str(meta.get("objective", ""))[:90]))
        print("      last move : %s" % (outs[-1][2:110] if outs else "(nothing reported yet)"))
        print("      next      : %s" % (nxt[:100] or "(not stated)"))
        print("      traffic   : %d advancement(s), %d directive(s) in inbox" % (len(outs), inbox_open))
    _registry().render()  # regenerate the registry's own generated human view too
    print("\n  generated view: %s/REGISTRY.md" % THREADS_DIRNAME)
    print("\n  open one:  claude --resume <session>   |   detail: cat %s/<name>/digest.md" % THREADS_DIRNAME)


def cmd_off(argv):
    """DRAIN AND ABSORB, THEN PARK. The founder-specified exit: every thread's
    handover digest is appended into the project's root STATE.md so the chief can
    continue solo with zero re-exploration, every thread is marked parked (NOT
    deleted, so it can be resumed if thread mode is switched back on), and nothing
    in-flight is discarded."""
    target = os.path.join(os.getcwd(), "STATE.md")
    reg = _registry()
    outcome = {}

    # ONE mode-locked transaction: check the mode, drain the registry, and write
    # the mode file without ever releasing the lock in between.
    #
    # This used to drain OUTSIDE the lock, and the gap was not theoretical: a
    # `start` running concurrently was granted after absorb had already drained,
    # so its record stayed ACTIVE while the mode file recorded it as parked and
    # its digest was never absorbed. Measured at 28 of 30 trials. That is exactly
    # the lossless-exit guarantee thread mode exists to provide.
    #
    # Lock order is MODE then REGISTRY, which is the order `start` already uses:
    # cmd_start calls reg.claim() INSIDE _with_mode_lock(_register). An earlier
    # comment here claimed the opposite and used it to justify the gap. It was
    # wrong, and the ordering below is what makes holding both safe.
    def _drain_and_close():
        dd = load_mode()
        if dd.get("mode") != "on":
            outcome["already_off"] = True
            return
        names = sorted(dd.get("threads", {}))
        # Snapshot what the registry is ABOUT to drain. absorb() returns an empty
        # list both when there was nothing to absorb and when the handover write
        # failed, and those two need opposite words: reporting a failed handover
        # as "nothing to absorb" tells the founder the exact opposite of the
        # truth on the one path where the truth matters most.
        pending = sorted(rid for rid, rec in (reg.load().get("records") or {}).items()
                         if isinstance(rec, dict) and rec.get("state") == "active")
        absorbed = [rid for rid, _ in reg.absorb()]
        failed = [rid for rid in pending if rid not in absorbed]
        if failed:
            outcome["failed"] = failed
            return
        outcome["absorbed"] = absorbed
        outcome["missing"] = [n for n in names if n not in absorbed]
        for name in names:
            meta = dd["threads"].get(name)
            # Defensive: a hand-edited entry that is not an object carries no
            # state to park. Skipping it matters here more than anywhere else:
            # absorb has already drained and parked the RECORDS, so raising at
            # this point left the mode file unsaved and the halves disagreeing.
            if not isinstance(meta, dict):
                continue
            meta["state"] = "parked"
            meta["parked_at"] = now()
        dd["mode"] = "off"
        _history(dd).append({"ts": now(), "event": "off",
                             "absorbed": absorbed, "empty": outcome["missing"]})
        # Checked, not fired and forgotten. The digests are already safely in
        # STATE.md at this point, so nothing is lost either way, but reporting
        # "mode OFF" when the file still says ON would send the founder back
        # into a system whose two halves disagree.
        if not save_mode(dd):
            outcome["mode_write_failed"] = True

    _with_mode_lock(_drain_and_close)

    if outcome.get("already_off"):
        print("thread mode is already OFF.")
        return
    if outcome.get("failed"):
        print("HANDOVER WRITE FAILED: %d record(s) could not be absorbed into %s"
              % (len(outcome["failed"]), target))
        for n in outcome["failed"]:
            print("    - %s" % n)
        print("  Thread mode stays ON and every record stays ACTIVE, so nothing is lost.")
        print("  Fix that file (permissions or disk), then run `off` again.")
        return
    absorbed = outcome.get("absorbed", [])
    missing = outcome.get("missing", [])
    if outcome.get("mode_write_failed"):
        print("HANDOVER SAFE, MODE FILE NOT UPDATED: %d digest(s) were absorbed "
              "into %s, so nothing is lost, but thread-mode.json could not be "
              "written and still says ON." % (len(absorbed), target))
        print("  Fix that file (permissions or disk), then run `off` again; "
              "re-absorbing is a no-op because the records are already parked.")
        return
    print("thread mode OFF (drained and parked, nothing deleted).")
    print("  absorbed %d digest(s) via the registry into %s" % (len(absorbed), target))
    for n in absorbed:
        print("    - %s" % n)
    if missing:
        # These threads had no ACTIVE record at all, so there was genuinely
        # nothing to drain: already adopted, or never registered.
        print("  no record left (nothing to absorb): %s" % ", ".join(missing))
    print("  threads remain on disk under %s/ and are resumable." % THREADS_DIRNAME)


def cmd_adopt(argv):
    """A thread died or stalled: the chief ABSORBS its fence and reports, per the
    founder's choice, rather than silently respawning."""
    if not argv:
        print("usage: adopt <thread>")
        return
    name = safe_name(argv[0])
    base = os.path.join(root(), name)
    if not os.path.isdir(base):
        print("adopt: no thread %r" % name)
        return
    reg = _registry()
    # Redact at THIS write boundary, like every sibling path here. A thread's
    # STATE.md is hand-written by a working session and can hold anything it
    # was told; the project STATE.md it lands in is committed into a git ref by
    # tools/bm_autosave.sh, so an unredacted secret persists durably.
    # ONE mode-locked transaction, same as `off`: write the handover, close the
    # registry record, and update the mode file without releasing the lock.
    # Splitting these left a window where the record was closed but the mode
    # file still called the thread active, and a concurrent start or off could
    # act on either half of a half-applied adoption.
    # Lock order MODE then REGISTRY, matching cmd_start and cmd_off.
    outcome = {}
    target = os.path.join(os.getcwd(), "STATE.md")

    def _adopt():
        # Delivery goes through the ONE handover primitive, keyed on this
        # record's LIFECYCLE. The previous design used a marker FILE named after
        # the thread, and a thread name is reusable: starting a second
        # "payments" thread inherited the first one's marker and its handover
        # was silently discarded. The proof now lives inside the delivered text,
        # so it cannot outlive the content it vouches for.
        rec = (reg.load().get("records") or {}).get(name)
        tag = reg.handover_tag(name, (rec or {}).get("lifecycle", 1))
        dg = reg.redact_text(read(os.path.join(base, "digest.md"), DIGEST_CAP))
        st = reg.redact_text(read(os.path.join(base, "STATE.md"), 2000))
        # ORDER IS THE ATOMICITY. The handover goes first, so a failure here
        # changes nothing and the thread stays adoptable. Closing the record
        # before securing the handover was a silent total loss.
        result = reg.deliver_handover(
            target, tag,
            "\n## Adopted from dead/stalled thread '%s' (%s)\n%s\n\n"
            "<!-- thread STATE at adoption -->\n%s\n"
            % (name, now(), dg.strip(), st.strip()))
        if result is False:
            outcome["handover_failed"] = True
            return
        if result == "already":
            outcome["resumed"] = True
        # The handover is safe on disk now, so close the record. Leaving it
        # active would make absorb() drain the same digest a second time and
        # keep the files fenced by an owner that is gone.
        if not reg.close(name, state="adopted"):
            outcome["registry_failed"] = True
            return
        d = load_mode()
        # isinstance, not `in`: a malformed entry cannot be assigned into.
        if isinstance(d.get("threads", {}).get(name), dict):
            d["threads"][name]["state"] = "adopted"
            d["threads"][name]["adopted_at"] = now()
            _history(d).append({"ts": now(), "event": "adopt", "thread": name})
            if not save_mode(d):
                outcome["mode_failed"] = True
                return
        outcome["ok"] = True

    _with_mode_lock(_adopt)

    if outcome.get("handover_failed"):
        print("ADOPT FAILED: could not write the handover into %s" % target)
        print("  Nothing changed: the record is still ACTIVE and the thread is "
              "untouched, so no context was lost.")
        print("  Fix that file (permissions or disk), then run `adopt` again.")
        return
    if outcome.get("registry_failed"):
        print("ADOPT PARTIALLY APPLIED: the handover IS in %s, but the registry "
              "record could not be closed." % target)
        print("  Nothing is lost, but the record is still active, so a later "
              "`off` will absorb this same digest a second time.")
        print("  Fix the registry file, then run `adopt` again to close it.")
        return
    if outcome.get("mode_failed"):
        print("ADOPT PARTIALLY APPLIED: the handover is in %s and the record is "
              "closed, but the mode file could not be updated." % target)
        print("  Nothing is lost. The dashboard will still show this thread as "
              "active until that file is writable again.")
        print("  Re-running `adopt` is safe: the handover will not be written twice.")
        return
    if outcome.get("resumed"):
        print("adopted '%s' (resumed): the handover was already in %s from an "
              "earlier attempt, so it was NOT written again." % (name, target))
        print("  The remaining steps completed. Nothing is duplicated.")
        return
    print("adopted '%s': its digest and fence are now in the chief's STATE.md." % name)
    print("  DECIDE: respawn the thread, or continue this work solo. Nothing is orphaned.")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    argv = sys.argv[2:]
    try:
        if cmd == "recommend":
            cmd_recommend(argv)
        elif cmd == "on":
            cmd_on(argv)
        elif cmd == "off":
            cmd_off(argv)
        elif cmd == "start":
            cmd_start(argv)
        elif cmd == "checkpoint":
            cmd_checkpoint(argv)
        elif cmd == "send":
            cmd_send(argv)
        elif cmd == "dashboard":
            cmd_dashboard(argv)
        elif cmd == "adopt":
            cmd_adopt(argv)
        else:
            print(__doc__.strip())
    except Exception as e:
        # Never block work, matching every other tool in this project.
        print("bm_threads: swallowed error (never blocks): %r" % (e,))
    sys.exit(0)


if __name__ == "__main__":
    main()
