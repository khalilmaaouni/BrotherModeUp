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
        with io.open(path, "w", encoding="utf-8") as f:
            f.write(text)
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


def load_mode(cwd=None):
    p = os.path.join(root(cwd), MODE_FILE)
    try:
        return json.loads(read(p) or "{}")
    except Exception:
        return {}


def save_mode(d, cwd=None):
    return write(os.path.join(root(cwd), MODE_FILE),
                 json.dumps(d, indent=2, sort_keys=True) + "\n")


def threads(cwd=None, state=None):
    """List thread names, optionally filtered by state (active|parked)."""
    m = load_mode(cwd).get("threads", {})
    names = sorted(m)
    if state:
        names = [n for n in names if m[n].get("state") == state]
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
    d = load_mode()
    if d.get("mode") == "on":
        print("thread mode already ON since %s" % d.get("since", "?"))
        return
    d["mode"] = "on"
    d["since"] = now()
    d.setdefault("threads", {})
    d.setdefault("history", []).append({"ts": now(), "event": "on"})
    save_mode(d)
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
        print("usage: start <feature-name> \"<objective>\"")
        return
    active = threads(state="active")
    if name not in active and len(active) >= MAX_ACTIVE:
        print("CAP: %d active threads already (%s). Park one before starting another; "
              "your review capacity is the real constraint." % (MAX_ACTIVE, ", ".join(active)))
        return
    objective = " ".join(argv[1:]).strip() or "(objective not stated)"
    base = os.path.join(root(), name)
    write(os.path.join(base, "STATE.md"),
          "# Thread: %s\n\n## Objective\n%s\n\n## Fence (files this thread may write)\n"
          "(declare before writing; single-writer law applies per file)\n\n"
          "## Plan and next intent\n- next: (write the next intent BEFORE acting)\n" % (name, objective))
    write(os.path.join(base, "inbox.md"),
          "# Inbox for %s\nDirectives from the chief. ONLY the chief writes here.\n\n" % name)
    write(os.path.join(base, "outbox.md"),
          "# Outbox from %s\nAdvancement for the chief. ONLY this thread writes here.\n\n" % name)
    # The digest exists from minute one, so an exit is lossless even immediately.
    write(os.path.join(base, "digest.md"),
          "# Handover digest: %s\n_updated %s_\n\n## Objective\n%s\n\n## Decisions\n(none yet)\n\n"
          "## Files touched\n(none yet)\n\n## Next intent\n(not yet stated)\n" % (name, now(), objective))
    d.setdefault("threads", {})[name] = {"state": "active", "objective": objective,
                                         "started": now()}
    d.setdefault("history", []).append({"ts": now(), "event": "start", "thread": name})
    save_mode(d)
    print("thread '%s' created at %s" % (name, base))
    print("  the thread session should read STATE.md + inbox.md, and write outbox.md + digest.md")


def cmd_checkpoint(argv):
    """Called BY a thread as it works. Keeps the handover digest current so that
    switching thread mode off is instant and lossless at any moment. Cheap by
    design: a few hundred characters to disk, nothing added to any context."""
    if not argv:
        print("usage: checkpoint <thread> [--decision X] [--files Y] [--next Z]")
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
    dec = " ".join(kv.get("decision", []))
    files = " ".join(kv.get("files", []))
    nxt = " ".join(kv.get("next", []))
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
    write(os.path.join(base, "digest.md"), "\n".join(body)[:DIGEST_CAP])
    if nxt or dec:
        append(os.path.join(base, "outbox.md"),
               "- %s %s%s" % (now()[:16], (dec + " | " if dec else ""), ("next: " + nxt) if nxt else ""))
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
    append(os.path.join(base, "inbox.md"), "- [%s] %s" % (now()[:16], " ".join(argv[1:])))
    print("sent to '%s'" % name)


def cmd_dashboard(argv):
    """The command center: every thread's advancement on one screen, so the founder
    reviews the whole project without opening any thread."""
    d = load_mode()
    mode = d.get("mode", "off")
    tmap = d.get("threads", {})
    print("BROTHERMODE THREADS  mode=%s  cap=%d  (%s)"
          % (mode.upper(), MAX_ACTIVE, os.getcwd()))
    if not tmap:
        print("  no threads. `recommend <n>` for advice, `on` then `start <feature>` to begin.")
        return
    for name in sorted(tmap):
        meta = tmap[name]
        base = os.path.join(root(), name)
        dg = read(os.path.join(base, "digest.md"))
        nxt = ""
        m = re.search(r"## Next intent\n(.+?)(\n|$)", dg)
        if m:
            nxt = m.group(1).strip()
        outs = [l for l in read(os.path.join(base, "outbox.md")).splitlines() if l.startswith("- ")]
        inbox_open = len([l for l in read(os.path.join(base, "inbox.md")).splitlines() if l.startswith("- ")])
        print("\n  [%s] %s" % (meta.get("state", "?").upper(), name))
        print("      objective : %s" % (meta.get("objective", "")[:90]))
        print("      last move : %s" % (outs[-1][2:110] if outs else "(nothing reported yet)"))
        print("      next      : %s" % (nxt[:100] or "(not stated)"))
        print("      traffic   : %d advancement(s), %d directive(s) in inbox" % (len(outs), inbox_open))
    print("\n  open one:  claude --resume <session>   |   detail: cat %s/<name>/digest.md" % THREADS_DIRNAME)


def cmd_off(argv):
    """DRAIN AND ABSORB, THEN PARK. The founder-specified exit: every thread's
    handover digest is appended into the project's root STATE.md so the chief can
    continue solo with zero re-exploration, every thread is marked parked (NOT
    deleted, so it can be resumed if thread mode is switched back on), and nothing
    in-flight is discarded."""
    d = load_mode()
    if d.get("mode") != "on":
        print("thread mode is already OFF.")
        return
    absorbed, missing = [], []
    lines = ["", "## Thread-mode handover (absorbed %s)" % now(),
             "Thread mode was switched off. The digests below are the accumulated context",
             "of each thread, absorbed so this session continues without re-exploring.",
             "Threads are PARKED, not deleted: `bm_threads.py on` resumes them.", ""]
    for name in sorted(d.get("threads", {})):
        dg = read(os.path.join(root(), name, "digest.md"), DIGEST_CAP)
        if dg.strip():
            lines += ["### Thread: %s" % name, dg.strip(), ""]
            absorbed.append(name)
        else:
            missing.append(name)
        d["threads"][name]["state"] = "parked"
        d["threads"][name]["parked_at"] = now()
    target = os.path.join(os.getcwd(), "STATE.md")
    ok = append(target, "\n".join(lines))
    d["mode"] = "off"
    d.setdefault("history", []).append({"ts": now(), "event": "off",
                                        "absorbed": absorbed, "empty": missing})
    save_mode(d)
    print("thread mode OFF (drained and parked, nothing deleted).")
    print("  absorbed %d digest(s) into %s%s" % (len(absorbed), target, "" if ok else " (WRITE FAILED)"))
    for n in absorbed:
        print("    - %s" % n)
    if missing:
        print("  no digest yet (nothing to absorb): %s" % ", ".join(missing))
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
    dg = read(os.path.join(base, "digest.md"), DIGEST_CAP)
    st = read(os.path.join(base, "STATE.md"), 2000)
    append(os.path.join(os.getcwd(), "STATE.md"),
           "\n## Adopted from dead/stalled thread '%s' (%s)\n%s\n\n<!-- thread STATE at adoption -->\n%s\n"
           % (name, now(), dg.strip(), st.strip()))
    d = load_mode()
    if name in d.get("threads", {}):
        d["threads"][name]["state"] = "adopted"
        d["threads"][name]["adopted_at"] = now()
        d.setdefault("history", []).append({"ts": now(), "event": "adopt", "thread": name})
        save_mode(d)
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
