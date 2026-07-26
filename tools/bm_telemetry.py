#!/usr/bin/env python3
"""BrotherMode telemetry: the mechanical half of the learning loop. Schema 2.

Subcommands:
  outcomes-append   SessionEnd hook target. Reads hook JSON on stdin, parses the
                    session transcript, appends ONE atomic JSONL line to the ledger
                    (schema 2: GenAI semconv token names) and scans the MAIN
                    transcript's short founder messages for correction candidates.
  migrate           One-time ledger migration to schema 2 (idempotent, temp+rename,
                    line-count recheck; never backfills absent values).
  scorecard         Renders the 9-metric dashboard from the ledger + companion files.
  rate              Records a founder felt-outcome rating. Integers 1-5 ONLY
                    (a human answering a 1-to-5 ask cannot produce a
                    fraction). --reply/--session name the PROVENANCE pair
                    (the founder's own verbatim words and the session id);
                    missing either records the rating but flags it
                    unattributed, reported separately and never averaged.
  rework            Records a REWORK signal: the founder sent a deliverable
                    back, or a later session redid the same artifact.
  escaped-defect    Records an ESCAPED DEFECT signal: a later session found
                    a defect in work an earlier session called green.
  review-mark       Records that a weekly review ran (feeds the overdue nag).
  startup-nags      One-line nags + yesterday's spend for SessionStart injection.
  stop-warn         Stop hook target, WARN ONLY (never blocks): systemMessage JSON
                    when a qualifying session has no vault session log today.
                    Cheap short-circuits only; never parses the transcript.
  registry-check    Flags fence-registry lines that look live in a stale file.
  fence-lint        Dispatch aid: prints live fences from the project's STATE.md
                    and the BROTHERMODE_REGISTRIES globs before a writer launches.
  prediction-audit  Counts sealed predictions in the founder model ledger and
                    reports alignment ONLY on the DIVERGED rows (prediction
                    and recommendation disagreed); agreement-case scoring
                    rewards flattery, so it is excluded, and a zero-diverged
                    week reports "0 scored divergent predictions" rather
                    than a ratio built on agreement.
  check-update      OFFLINE check of your installed copy: warns when an already
                    fetched update is waiting, when the copy has gone stale, and
                    once when the law itself changed under you. Reads git refs as
                    plain files: no network call, no subprocess, ever.
  intent            Write-ahead intent log. `intent "next: X, because Y"` appends
                    one line to a per-project log BEFORE a risky/long action, so a
                    death always leaves a forward-looking record (the write-ahead
                    log pattern: log the intent before the action, like a database).
                    The resume brief surfaces the last intent first.
  precompact-brief  PreCompact hook helper. Reads the hook JSON on stdin, extracts
                    the TAIL of the dying session's transcript (last instruction,
                    recent decisions, recent commands) and writes a resume brief to
                    the vault, so a resumed session recovers the THREAD, not just the
                    files the git autosave saved. Pure: reads/writes files only.
  compact-hint      SessionStart(source=compact) helper. Reads the hook JSON on
                    stdin; if the session just resumed from a compaction, checks
                    for a real autosave receipt (via bm_autosave.has_receipt)
                    before claiming safety, and prints the recovery command that
                    actually exists (bm_autosave.py, not the deleted .sh). Pure:
                    reads stdin and prints, no subprocess, no network.
  handoff           One shareable, SECRET-REDACTED markdown for handing a project
                    to a small team: overview + open items + latest session + recent
                    outcomes, assembled from the vault. Pure: reads vault files,
                    redacts, writes one file. No subprocess, no network.
  purge-corrections Deletes captured correction candidates (excerpts of your own
                    messages, secret-redacted and owner-only, but still yours to
                    delete). Shows the count first; --yes to confirm.
  speed             Wall-clock view for rubric metric 3: last 7d vs prior 7d,
                    span-hours per OUTCOMES line (labeled proxy, never invented).
  dedup             One-time cleanup of duplicate hook flushes (backup + count
                    check; keeps last flush per identical metric set).

Law: this tool NEVER blocks work. Every path exits 0. Numbers are parsed or
absent; nothing is invented. Token counts are labeled as-flushed (the transcript
may lag the final turn). Old (schema 1) and new lines are both readable: use
fld() everywhere.
"""
import json, os, sys, glob, re, datetime, hashlib, tempfile, io, shutil

# ---------------------------------------------------------------------------
# Configuration. The vault is the durable memory folder every ledger lives in.
# Default: ~/BrotherModeVault. Point BROTHERMODE_VAULT anywhere you prefer.
# Layout, created on demand by atomic_append:
#   <vault>/99-System/telemetry/outcomes.jsonl     one line per real session
#   <vault>/99-System/telemetry/ratings.jsonl      founder felt-outcome scores
#   <vault>/99-System/telemetry/reviews.jsonl      weekly review markers
#   <vault>/99-System/telemetry/corrections.jsonl  correction candidates
#   <vault>/50-Reference/founder-model.md          prediction ledger (optional)
#   <vault>/10-Projects/<name>/Sessions/*.md       human session logs
# ---------------------------------------------------------------------------
VAULT = os.environ.get("BROTHERMODE_VAULT", os.path.expanduser("~/BrotherModeVault"))
TEL_DIR = os.path.join(VAULT, "99-System", "telemetry")
LEDGER = os.path.join(TEL_DIR, "outcomes.jsonl")
RATINGS = os.path.join(TEL_DIR, "ratings.jsonl")
REVIEWS = os.path.join(TEL_DIR, "reviews.jsonl")
CORRECTIONS = os.path.join(TEL_DIR, "corrections.jsonl")
# SKILL.md section 8, fix-round 2026-07-26: the two outcome signals the
# graded party cannot fake, because each points at something checkable
# outside the grader's own say-so (a returned deliverable, a redone
# artifact, a defect a later session actually found), never a self-report.
SIGNALS = os.path.join(TEL_DIR, "signals.jsonl")
FOUNDER_MODEL = os.path.join(VAULT, "50-Reference", "founder-model.md")
SESSIONS_GLOB = os.path.join(VAULT, "10-Projects", "*", "Sessions", "*.md")

MIN_API_MSGS = 5
MIN_TOOL_CALLS = 1
STOPWARN_MIN_BYTES = 200_000   # transcript smaller than this = trivial, stay silent
# Hook self-test end_reasons: real work never uses these. Excluded from every
# aggregate so the learning loop scores on real sessions only (weekly-review
# 2026-07-20 finding: 2 smoke-test lines polluted session counts and token sums).
TEST_END_REASONS = {"simulated-test", "chained-smoke-test", "smoke-test", "test"}

OUT_KEYS = ("gen_ai.usage.output_tokens", "out_tokens")
IN_KEYS = ("gen_ai.usage.input_tokens",)
CORRECTION_RE = re.compile(
    r"\b(no[,.]? (that|this|the)|not what i|wrong|you did not|you didn'?t|not even"
    r"|i said|stop doing|never do|always use|from now on|instead of|do better)\b",
    re.I)


def fld(rec, keys, default=0):
    for k in keys:
        if k in rec:
            return rec[k]
    return default


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def atomic_write(path, text, mode=0o644):
    """Replace a file's entire contents crash-atomically.

    The plain `open(path, "w")` used everywhere else TRUNCATES first, so a
    crash, a full disk, or a killed process between truncate and write leaves
    the file empty or half-written. For a state file that is not an
    inconvenience, it is the whole registry or the whole mode file gone, and
    the tools would then read an empty object and believe there was no work.

    Write to a temp file in the SAME directory (so the rename cannot cross a
    filesystem), flush and fsync it so the bytes are really on the medium, then
    os.replace, which is atomic: a reader sees either the entire old file or
    the entire new one, never a partial one. Finally fsync the directory so the
    rename itself survives a power loss.

    Raises OSError on failure, deliberately: every caller already catches and
    reports write failures, and swallowing here would recreate the
    success-reported-on-an-unchecked-write defect this project keeps hitting.
    """
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".bm-tmp-")
    try:
        with io.open(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        # Leave no litter behind on any failure path, including KeyboardInterrupt.
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    # Best effort: the data and the rename are already durable on every
    # filesystem that matters, and some platforms refuse to fsync a directory.
    try:
        dfd = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    except OSError:
        pass
    return True


def atomic_append(path, obj, mode=0o644):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    line = (json.dumps(obj, separators=(",", ":")) + "\n").encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, mode)
    try:
        os.write(fd, line)
    finally:
        os.close(fd)
    if mode == 0o600:
        # os.open only applies its mode when it CREATES the file, so a file
        # that already exists from an earlier, laxer default would stay
        # world-readable forever. Tighten it, and only ever tighten: shared
        # files keep the 0644 default and are never touched here.
        try:
            os.chmod(path, 0o600)
        except OSError as e:
            print("bm_telemetry: warning: could not make %s owner-only (%s)"
                  % (path, e), file=sys.stderr)


def parse_transcript(path, collect_user_texts=False):
    agg = {"out": 0, "cache_w": 0, "cache_r": 0, "in": 0, "api_msgs": 0,
           "tool_calls": 0, "agent_spawns": 0, "workflow_calls": 0,
           "human_msgs": 0, "models": {}, "first_ts": None, "last_ts": None,
           "user_texts": []}
    per_msg = {}
    anon = 0
    try:
        f = open(path, "r", errors="replace")
    except OSError:
        return agg
    with f:
        for raw in f:
            try:
                o = json.loads(raw)
            except Exception:
                continue
            ts = o.get("timestamp")
            if isinstance(ts, str) and len(ts) >= 19:
                if agg["first_ts"] is None or ts < agg["first_ts"]:
                    agg["first_ts"] = ts
                if agg["last_ts"] is None or ts > agg["last_ts"]:
                    agg["last_ts"] = ts
            t = o.get("type")
            if t == "user" and not o.get("isMeta"):
                c = (o.get("message") or {}).get("content")
                txt = None
                if isinstance(c, str):
                    txt = c
                elif isinstance(c, list):
                    if not any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c):
                        txt = "\n".join(b.get("text", "") for b in c
                                        if isinstance(b, dict) and b.get("type") == "text")
                if txt and txt.strip() and "<system-reminder>" not in txt:
                    agg["human_msgs"] += 1
                    if collect_user_texts:
                        agg["user_texts"].append(txt.strip())
            if t != "assistant":
                continue
            m = o.get("message") or {}
            model = m.get("model")
            if model:
                agg["models"][model] = agg["models"].get(model, 0) + 1
            u = m.get("usage")
            if u:
                mid = m.get("id")
                if not mid:
                    mid = "anon%d" % anon
                    anon += 1
                slot = per_msg.setdefault(mid, {})
                for k in ("input_tokens", "output_tokens",
                          "cache_creation_input_tokens", "cache_read_input_tokens"):
                    v = u.get(k) or 0
                    if v > slot.get(k, 0):
                        slot[k] = v
            for b in (m.get("content") or []):
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    agg["tool_calls"] += 1
                    name = b.get("name", "")
                    if name in ("Task", "Agent"):
                        agg["agent_spawns"] += 1
                    elif name == "Workflow":
                        agg["workflow_calls"] += 1
    agg["api_msgs"] = len(per_msg)
    for s in per_msg.values():
        agg["out"] += s.get("output_tokens", 0)
        agg["in"] += s.get("input_tokens", 0)
        agg["cache_w"] += s.get("cache_creation_input_tokens", 0)
        agg["cache_r"] += s.get("cache_read_input_tokens", 0)
    return agg


# Correction candidates are excerpts of YOUR OWN messages, so they can carry
# secrets you typed. Redact secret-shaped substrings before anything is written,
# and keep the file owner-only. This is best-effort pattern matching, not a
# guarantee: treat the file as sensitive and purge it when you no longer need it
# (tools/bm_telemetry.py purge-corrections).
SECRET_PATTERNS = [
    re.compile(r"\b(sk|rk)[-_][A-Za-z0-9_-]{12,}", re.I),           # api keys
    re.compile(r"\bgh[oprsu]_[A-Za-z0-9]{16,}"),                     # github tokens
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),                            # aws key id
    re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}", re.I),             # slack
    re.compile(r"\b[Bb]earer\s+[A-Za-z0-9._~+/=-]{16,}"),
    # A private key is a BLOCK, not a line. Matching only the -----BEGIN-----
    # header left every line of base64 key material after it going to disk,
    # while SECURITY.md claims private keys are redacted. Prefer the real
    # BEGIN..END span; when there is no END marker (a truncated paste), take
    # the base64-looking lines that follow and stop there, so ordinary prose
    # after a mentioned header is never swallowed.
    re.compile(r"-----BEGIN[ A-Z]*PRIVATE KEY-----"
               r"(?:[\s\S]*?-----END[ A-Z]*PRIVATE KEY-----"
               r"|(?:\s*[A-Za-z0-9+/=]{16,})*)"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),      # jwt
    # key=value and key: value where the key names a secret
    # key=value, key: value, and the natural-language "the password is hunter2".
    # Over-redaction is deliberate here: a masked non-secret costs nothing, a
    # stored secret costs a lot.
    # Leading [A-Za-z0-9_]* so PROD_DB_PASSWORD= matches as well as password=.
    re.compile(r"(?i)[A-Za-z0-9_]*(?:pass(?:word|wd|phrase)?|secret|token"
               r"|api[_-]?key|access[_-]?key|private[_-]?key|credential)s?"
               r"\s*(?:[:=]|\s+(?:is|was)\s+)\s*\S+"),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),                          # us ssn shape
    re.compile(r"\b(?:\d[ -]?){13,16}\b"),                          # card-ish digits
]


def redact(text):
    """Mask secret-shaped substrings. Returns (clean_text, n_redactions)."""
    n = 0
    for pat in SECRET_PATTERNS:
        text, k = pat.subn("[REDACTED]", text)
        n += k
    return text, n


def scan_corrections(sid, project, user_texts):
    """Correction CANDIDATES from short founder messages in the MAIN transcript
    only (subagent transcripts quote law text and would flood this). Human filter
    at the weekly review decides what becomes law; cap 5 per session.
    Dedup guard (interim-score fix 2026-07-23): the SessionEnd hook can fire more
    than once per session; a (session_id, text) already in the file is never
    re-appended."""
    seen = {(c.get("session_id"), c.get("text")) for c in read_jsonl(CORRECTIONS)}
    found = 0
    for txt in user_texts:
        if found >= 5:
            break
        if len(txt) > 400:
            continue
        if CORRECTION_RE.search(txt):
            clean, nred = redact(txt[:400])
            if (sid, clean) in seen:
                continue
            rec = {"ts": now_iso(), "session_id": sid,
                   "project": project, "text": clean}
            if nred:
                rec["redactions"] = nred
            atomic_append(CORRECTIONS, rec, mode=0o600)
            seen.add((sid, clean))
            found += 1
    return found


def cmd_outcomes_append():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        print("bm_telemetry: no valid hook payload on stdin; nothing recorded")
        return
    tp = payload.get("transcript_path") or ""
    sid = payload.get("session_id") or "unknown"
    cwd = payload.get("cwd") or ""
    if not tp or not os.path.isfile(tp):
        print("bm_telemetry: transcript not found; nothing recorded")
        return
    main = parse_transcript(tp, collect_user_texts=True)
    sub = {"out": 0, "files": 0}
    subroot = os.path.join(os.path.dirname(tp), sid, "subagents")
    if os.path.isdir(subroot):
        for sf in glob.glob(os.path.join(subroot, "**", "*.jsonl"), recursive=True):
            sub["files"] += 1
            sa = parse_transcript(sf)
            sub["out"] += sa["out"]
    if main["api_msgs"] < MIN_API_MSGS or main["tool_calls"] < MIN_TOOL_CALLS:
        print("bm_telemetry: below activity floor (%d api msgs, %d tool calls); not recorded"
              % (main["api_msgs"], main["tool_calls"]))
        return
    project = _vault_project_name(cwd)
    hours = 0.0
    if main["first_ts"] and main["last_ts"]:
        try:
            a = datetime.datetime.fromisoformat(main["first_ts"].replace("Z", "+00:00"))
            b = datetime.datetime.fromisoformat(main["last_ts"].replace("Z", "+00:00"))
            hours = round((b - a).total_seconds() / 3600, 2)
        except Exception:
            pass
    rec = {
        "schema": 2, "ts": now_iso(), "session_id": sid, "project": project,
        "end_reason": payload.get("reason") or "",
        "gen_ai.usage.output_tokens": main["out"],
        "gen_ai.usage.input_tokens": main["in"],
        "sub_out_tokens": sub["out"],
        "cache_write": main["cache_w"], "cache_read": main["cache_r"],
        "api_msgs": main["api_msgs"], "human_msgs": main["human_msgs"],
        "tool_calls": main["tool_calls"], "agent_spawns": main["agent_spawns"],
        "workflow_calls": main["workflow_calls"], "subagent_files": sub["files"],
        "models": sorted(main["models"].keys()), "duration_h": hours,
        "token_basis": "as-flushed",
    }
    # Duplicate-flush guard (interim-score fix 2026-07-23): the SessionEnd hook
    # can fire repeatedly for one session; an identical metric set (everything
    # but ts) is the same flush and is not recorded twice. A changed metric set
    # is real progress and still appends (real_sessions keeps the last flush).
    comparable = {k: v for k, v in rec.items() if k != "ts"}
    for prev in read_jsonl(LEDGER):
        if prev.get("session_id") == sid and {k: v for k, v in prev.items() if k != "ts"} == comparable:
            print("bm_telemetry: duplicate flush for %s (identical metrics); not recorded" % sid[:8])
            return
    atomic_append(LEDGER, rec)
    ncorr = scan_corrections(sid, project, main["user_texts"])
    print("bm_telemetry: recorded %s (%dk out, %d tools, %.1fh, %d correction candidates)"
          % (sid[:8], main["out"] // 1000, main["tool_calls"], hours, ncorr))


def cmd_migrate():
    if not os.path.isfile(LEDGER):
        print("migrate: no ledger yet")
        return
    rows, bad = read_jsonl(LEDGER, report_bad=True)
    n_before = len(rows)
    changed = 0
    out = []
    for r in rows:
        if r.get("schema") != 2:
            r = dict(r)
            if "out_tokens" in r:
                r["gen_ai.usage.output_tokens"] = r.pop("out_tokens")
            r["schema"] = 2
            # input tokens were never recorded pre-schema-2: stays ABSENT, never invented
            changed += 1
        out.append(r)
    # Back up the RAW FILE (byte-exact, via atomic_backup) before the rewrite,
    # not a re-serialization of `rows`: `rows` already excludes any line that
    # failed to parse, so the old re-serialized "backup" silently excluded it
    # too, and this line-count check compared two counts that both already
    # excluded it. Copying bytes cannot lose a line no matter how it parses.
    bak = LEDGER + ".bak-migrate" + datetime.date.today().strftime("%Y%m%d")
    backed_up = atomic_backup(LEDGER, bak)
    atomic_write(LEDGER, "".join(json.dumps(r, separators=(",", ":")) + "\n" for r in out))
    n_after = len(read_jsonl(LEDGER))
    if n_after < n_before:
        print("migrate: LINE COUNT DROPPED %d->%d, restore from backup!" % (n_before, n_after))
    else:
        print("migrate: %d lines, %d migrated to schema 2, count ok (%d)"
              % (n_before, changed, n_after))
    if bad:
        print("migrate: %d malformed line(s) in the original could not be parsed "
              "(line numbers %s) and are NOT in the rewritten file; the exact "
              "original bytes are preserved at %s%s, nothing was deleted."
              % (len(bad), ",".join(str(i) for i in bad[:10]) + (",..." if len(bad) > 10 else ""),
                 bak, "" if backed_up else " (from an earlier run today)"))


def cmd_dedup():
    """One-time cleanup of duplicate hook flushes already in the files. Backup
    first, temp+rename, count check printed. Outcomes: drop rows whose metric
    set (everything but ts) matches an already-kept row for the same session,
    keeping the LAST occurrence (matches real_sessions semantics). Corrections:
    drop duplicate (session_id, text), keeping the first."""
    stamp = datetime.date.today().strftime("%Y%m%d")
    for path, keyfn, keep in (
        (LEDGER, lambda r: (r.get("session_id"),
                            json.dumps({k: v for k, v in r.items() if k != "ts"},
                                       sort_keys=True)), "last"),
        (CORRECTIONS, lambda r: (r.get("session_id"), r.get("text")), "first"),
    ):
        rows, bad = read_jsonl(path, report_bad=True)
        if not rows:
            print("dedup: %s empty or missing, skipped" % os.path.basename(path))
            continue
        if keep == "last":
            kept_rev, seen = [], set()
            for r in reversed(rows):
                k = keyfn(r)
                if k in seen:
                    continue
                seen.add(k)
                kept_rev.append(r)
            kept = list(reversed(kept_rev))
        else:
            kept, seen = [], set()
            for r in rows:
                k = keyfn(r)
                if k in seen:
                    continue
                seen.add(k)
                kept.append(r)
        if len(kept) == len(rows):
            # No rewrite happens on this branch, so the file on disk is
            # untouched: any malformed line already in it is neither lost
            # nor hidden, just still there for the next read to report.
            print("dedup: %s already clean (%d lines%s)"
                  % (os.path.basename(path), len(rows),
                     ", %d malformed line(s) left in place" % len(bad) if bad else ""))
            continue
        # Byte-exact backup BEFORE the rewrite (see atomic_backup's docstring
        # for why this replaced re-serializing read_jsonl()'s own output).
        bak = "%s.bak-dedup%s" % (path, stamp)
        backed_up = atomic_backup(path, bak)
        atomic_write(path, "".join(json.dumps(r, separators=(",", ":")) + "\n" for r in kept))
        print("dedup: %s %d -> %d lines (%d duplicate flushes dropped; backup %s)"
              % (os.path.basename(path), len(rows), len(kept),
                 len(rows) - len(kept), os.path.basename(bak)))
        if bad:
            print("dedup: %d malformed line(s) in %s could not be parsed and are NOT in "
                  "the rewritten file; the exact original bytes are preserved at %s%s."
                  % (len(bad), os.path.basename(path), bak,
                     "" if backed_up else " (from an earlier run today)"))


def outcomes_lines_in_window(min_age_d, max_age_d):
    """Dated human lines in the vault OUTCOMES ledgers (one line per recorded
    run; the closest thing to 'shipped surface' the system records)."""
    n = 0
    today = datetime.date.today()
    for path in glob.glob(os.path.join(VAULT, "10-Projects", "*", "OUTCOMES.md")):
        for line in open(path, errors="replace"):
            m = re.match(r"^(\d{4}-\d{2}-\d{2}) \|", line)
            if not m:
                continue
            try:
                age = (today - datetime.date.fromisoformat(m.group(1))).days
            except ValueError:
                continue
            if min_age_d <= age < max_age_d:
                n += 1
    return n


def cmd_speed():
    """Rubric metric 3 feed. HONEST LABELS: duration_h is the span from first to
    last message (includes idle), and OUTCOMES lines are human-recorded runs, a
    PROXY for shipped surfaces. No proxy, no number."""
    rows = real_sessions(read_jsonl(LEDGER))
    def window(lo, hi):
        w = [r for r in rows if lo <= (age_days(r.get("ts", "")) or 999) < hi]
        return {"sessions": len(w),
                "hours": round(sum(r.get("duration_h", 0) for r in w), 1),
                "outk": sum(fld(r, OUT_KEYS) + r.get("sub_out_tokens", 0) for r in w) // 1000}
    cur, prev = window(0, 7), window(7, 14)
    cur_runs, prev_runs = outcomes_lines_in_window(0, 7), outcomes_lines_in_window(7, 14)
    print("BROTHERMODE SPEED (metric 3 feed; span-hours include idle, runs are OUTCOMES lines)")
    for label, w, runs in (("last 7d ", cur, cur_runs), ("prior 7d", prev, prev_runs)):
        per = ("%.1f span-h/run" % (w["hours"] / runs)) if runs else "no runs recorded"
        print("  %s: %d sessions, %.1f span-h, %dk out, %d recorded runs -> %s"
              % (label, w["sessions"], w["hours"], w["outk"], runs, per))
    if not (cur_runs and prev_runs):
        print("  trend: NO-DATA (both windows need recorded runs; nothing is invented)")


def read_jsonl(path, report_bad=False):
    """Parse a JSONL ledger. A line that fails to parse is skipped from the
    returned rows exactly as before (a caller doing arithmetic over `rows`
    still gets clean data), but it is no longer INVISIBLE: pass
    report_bad=True to also get back the 1-based line numbers that could not
    be parsed, so a caller can COUNT and REPORT what it silently used to
    drop (docs/REMAINING.md item 1, fix-round 2026-07-26: a maintenance
    rewrite that reads with this function, then writes back only what it
    parsed, used to permanently delete a corrupt line while its own
    before/after count check stayed green, because both counts already
    excluded the dropped line). Line numbers only, never the raw text: a
    malformed line in corrections.jsonl or a resume brief can still carry
    unredacted founder text, and this module never prints founder text
    unredacted, so the caller reports a location, not content, and the
    REWRITE side of the fix is atomic_backup (byte-exact original), not a
    quarantine of individual lines here."""
    rows, bad = [], []
    if not os.path.isfile(path):
        return (rows, bad) if report_bad else rows
    for i, raw in enumerate(open(path, errors="replace"), 1):
        if not raw.strip():
            continue
        try:
            rows.append(json.loads(raw))
        except Exception:
            bad.append(i)
    return (rows, bad) if report_bad else rows


def atomic_backup(path, bak):
    """Copy path's raw bytes to bak verbatim, byte for byte, before any
    maintenance rewrite touches path. Never overwrites an existing bak (the
    FIRST snapshot from a day that ran migrate/dedup twice is the one worth
    keeping, matching the existing per-day backup naming). Returns True if a
    new backup was written, False if one already existed today.

    This exists because the OLD backup code in cmd_migrate/cmd_dedup
    rebuilt its "backup" by re-serializing read_jsonl()'s OWN PARSED OUTPUT,
    so a line that failed to parse was missing from the "backup" too, and a
    line-count check comparing two counts that both already excluded it
    could never catch the loss. Copying the file's actual bytes cannot lose
    a line no matter how the parser behaves."""
    if os.path.exists(bak):
        return False
    shutil.copyfile(path, bak)
    return True


def real_sessions(rows):
    """One row per real session: drop hook self-tests, dedup by session_id
    (last flush wins). Both the scorecard and the startup nag use this so
    'sessions' means the same thing in every output."""
    by = {}
    for r in rows:
        if r.get("end_reason") in TEST_END_REASONS:
            continue
        by[r.get("session_id", "?")] = r
    return list(by.values())


def age_days(iso):
    try:
        t = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return (datetime.datetime.now(datetime.timezone.utc) - t).total_seconds() / 86400
    except Exception:
        return None


def _coordination_collisions(cwd):
    """Real collision count for rubric metric 7 (docs/REMAINING.md item 1,
    fix-round 2026-07-26), replacing the old hardcoded literal 'collisions=0,
    baton drops=0': bm_store.verify() already computes the exact invariant a
    coordination collision IS (two ACTIVE claims whose paths overlap), so
    this reads that instead of printing an unmovable number. 'baton drops'
    has NO data source anywhere in this codebase, so that half of the old
    line is DELETED rather than replaced with a second fake number: per the
    brief, a metric nobody can act on is worse than a missing one, and
    RUBRIC.md's own evidence line already names baton drops and
    resume-vs-respawn as judged weekly from OUTCOMES incidents, not computed
    here. Returns (n, note): n is an int when a store was found and read, or
    None with a one-line reason (no bm_store module, no resolvable root, or
    no store initialized yet at that root)."""
    bm_store, err = _get_bm_store()
    if bm_store is None:
        return None, "bm_store.py unavailable (%s)" % err
    root, _source = _resolve_root_quiet(cwd)
    if root is None:
        return None, "no BrotherMode project root found from %s" % cwd
    try:
        problems = bm_store.verify(root)
    except Exception as e:
        return None, "store.verify() could not run (%r)" % (e,)
    return sum(1 for p in problems if p.startswith("active claims overlap")), None


def cmd_scorecard():
    led, led_bad = read_jsonl(LEDGER, report_bad=True)
    rows = real_sessions(led)
    ratings, ratings_bad = read_jsonl(RATINGS, report_bad=True)
    reviews, reviews_bad = read_jsonl(REVIEWS, report_bad=True)
    corrections, corr_bad = read_jsonl(CORRECTIONS, report_bad=True)
    signals = read_jsonl(SIGNALS)
    n_rework = sum(1 for s in signals if s.get("kind") == "rework")
    n_escaped = sum(1 for s in signals if s.get("kind") == "escaped-defect")
    preds = prediction_counts()
    recent = [r for r in rows if (age_days(r.get("ts", "")) or 99) <= 7]
    out7 = sum(fld(r, OUT_KEYS) + r.get("sub_out_tokens", 0) for r in recent)
    cr = sum(r.get("cache_read", 0) for r in recent)
    cw = sum(r.get("cache_write", 0) for r in recent)
    ratio = (100.0 * cr / (cr + cw)) if (cr + cw) else None
    # PROVENANCE (SKILL.md section 8, fix-round 2026-07-26): a rating with no
    # founder reply and session id attached is UNATTRIBUTED and is reported
    # separately, never folded into the average; averaging it would let the
    # system's own guess about its felt-outcome pass as the founder's own.
    scored_ratings = [x for x in ratings if isinstance(x.get("score"), (int, float))]
    attributed = [x for x in scored_ratings if x.get("attributed")]
    unattributed = [x for x in scored_ratings if not x.get("attributed")]
    avg_rating = round(sum(x["score"] for x in attributed) / len(attributed), 2) if attributed else None
    last_review = max((x.get("ts", "") for x in reviews), default=None)
    lr_age = age_days(last_review) if last_review else None
    bad_total = len(led_bad) + len(ratings_bad) + len(reviews_bad) + len(corr_bad)
    print("BROTHERMODE SCORECARD  (mechanical fields computed; judgment fields scored at weekly review)")
    if bad_total:
        print("WARNING: %d malformed ledger line(s) could not be parsed and are excluded from "
              "every count below (ledger=%d ratings=%d reviews=%d corrections=%d); the raw "
              "files are untouched, nothing was deleted (migrate/dedup preserve a byte-exact backup)."
              % (bad_total, len(led_bad), len(ratings_bad), len(reviews_bad), len(corr_bad)))
    print("ledger: %d sessions, %d last 7d, %dk out last 7d, %d correction candidates pending, "
          "%d rework signal(s), %d escaped defect(s)"
          % (len(rows), len(recent), out7 // 1000, len(corrections), n_rework, n_escaped))
    print("1 self-learning : reviews=%d, last=%s, sealed predictions=%d (10: 0 gaps 14d + 2 reviews + >=5 predictions)"
          % (len(reviews), ("%.1fd" % lr_age) if lr_age is not None else "never", preds["sealed"]))
    # FIX (fix-round 2026-07-26): this used to print len(rows), len(rows), a
    # value compared against ITSELF that can never be anything but 100 percent
    # regardless of whether tokens were actually measured, the same class of
    # theatre as the hardcoded coordination line. "measured" now means "has a
    # real input-token field", which schema-1 rows and any row migrate could
    # not backfill genuinely lack (migrate never invents that value).
    measured = sum(1 for r in rows if any(k in r for k in IN_KEYS))
    print("2 token economy : measured=%d/%d, out 7d=%dk, budget-vs-tier: bm_score check "
          "(10: 0 unmeasured + budgets enforced; trend NOT DECIDABLE at this session volume, see RUBRIC.md)"
          % (measured, len(rows), out7 // 1000))
    print("3 speed         : run 'bm_telemetry.py speed' for the raw span-hours feed; "
          "trend NOT DECIDABLE at this session volume (see RUBRIC.md), judged directionally at weekly review")
    diverged_txt = ("%d/%d" % (preds["diverged_hits"], preds["diverged_scored"])) \
        if preds["diverged_scored"] else "0 scored divergent predictions"
    print("4 alignment     : ratings=%d avg=%s (unattributed=%d, never averaged), "
          "prediction alignment (diverged only)=%s, corrections captured=%d, rework=%d, escaped-defects=%d "
          "(10: avg>=4.5 + 0 repeats 2wk)"
          % (len(attributed), avg_rating, len(unattributed), diverged_txt,
             len(corrections), n_rework, n_escaped))
    print("5 memory        : canonical=%s; registry + vault hygiene judged weekly" % LEDGER)
    print("6 honesty       : floor gate; escaped defects=%d (signals.jsonl); "
          "evidence blocks in fence closes judged weekly" % n_escaped)
    collisions, coll_note = _coordination_collisions(os.getcwd())
    if collisions is None:
        print("7 coordination  : floor gate; collisions NOT MEASURED (%s); "
              "baton drops and resume-not-respawn judged weekly from OUTCOMES incidents" % coll_note)
    else:
        print("7 coordination  : floor gate; collisions=%d (bm_store.verify() at %s); "
              "baton drops and resume-not-respawn judged weekly from OUTCOMES incidents"
              % (collisions, os.getcwd()))
    print("8 delivery      : shipped surfaces vs spend, check: fields on fences, judged weekly")
    print("9 cache economy : warm-read ratio 7d=%s (10: sustained >=90%% + zero broken-prefix incidents 2wk)"
          % (("%.1f%%" % ratio) if ratio is not None else "no data"))


def prediction_counts():
    """Parse the founder-model prediction ledger table (row shape, no leading
    pipe: date | prediction | against-case | diverged | outcome | note).
    SEALED once a real against-case (parts[2]) exists; SCORED once the
    outcome (parts[4]) is a yes/hit/no/miss verdict. DIVERGED (SKILL.md
    section 8, fix-round 2026-07-26): scoring alignment on an agreement case
    rewards telling the founder what they want to hear, so the hit rate that
    matters is counted ONLY on rows where parts[3] marks the prediction and
    the recommendation as having diverged ('yes'); a scored row with no
    diverged marker at all is counted separately (unmarked), never silently
    treated as either divergent or agreed."""
    out = {"sealed": 0, "scored": 0, "hits": 0,
           "diverged_scored": 0, "diverged_hits": 0, "unmarked": 0}
    if not os.path.isfile(FOUNDER_MODEL):
        return out
    in_ledger = False
    for line in open(FOUNDER_MODEL, errors="replace"):
        if line.startswith("## Prediction ledger"):
            in_ledger = True
            continue
        if in_ledger and line.startswith("## "):
            break
        if in_ledger and line.strip().startswith("20") and "|" in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 5 and parts[2] not in ("n/a", ""):
                out["sealed"] += 1
                if parts[4].lower().startswith(("yes", "hit", "no", "miss")):
                    out["scored"] += 1
                    hit = parts[4].lower().startswith(("yes", "hit"))
                    if hit:
                        out["hits"] += 1
                    diverged_field = parts[3].lower() if len(parts) > 3 else ""
                    if diverged_field.startswith("yes"):
                        out["diverged_scored"] += 1
                        if hit:
                            out["diverged_hits"] += 1
                    elif not diverged_field.startswith("no"):
                        out["unmarked"] += 1
    return out


def cmd_rate(argv):
    """Record a founder felt-outcome rating. INTEGERS 1-5 ONLY (SKILL.md
    section 8, fix-round 2026-07-26): a human answering a 1-to-5 ask cannot
    produce a fractional score, so a fractional value in this ledger is
    proof the system rated itself rather than the founder (three of the real
    ratings on file were fractional before this fix). --reply/--session are
    the PROVENANCE pair: the founder's own verbatim words and the session id
    the rating came from. A rating missing either is still recorded (a
    felt-outcome is worth keeping either way) but flagged attributed=false,
    and cmd_scorecard reports unattributed rows separately, never averaged."""
    score_raw, task, note, reply, session = None, "", "", "", ""
    it = iter(argv)
    for a in it:
        if a == "--score":
            score_raw = next(it, "")
        elif a == "--task":
            task = next(it, "")
        elif a == "--note":
            note = next(it, "")
        elif a == "--reply":
            reply = next(it, "")
        elif a == "--session":
            session = next(it, "")
    usage = ("usage: rate --score 1..5 --task \"...\" "
             "[--reply \"founder's verbatim words\"] [--session ID] [--note \"...\"]")
    if not score_raw:
        print(usage)
        return
    try:
        # int(), not float(): a string like "4.5" or "4/5" must REFUSE, not
        # truncate or round silently into a plausible-looking integer.
        score = int(score_raw)
    except ValueError:
        print("rate: refused, --score must be a whole number 1-5 (got %r). A founder "
              "answering a 1-to-5 ask cannot produce a fraction; a fractional score here "
              "would mean the system rated itself, not the founder." % score_raw)
        return
    if not (1 <= score <= 5):
        print(usage)
        return
    task = redact(task)[0]
    note = redact(note)[0]
    reply = redact(reply)[0]
    rec = {"ts": now_iso(), "score": score, "task": task, "note": note}
    is_attributed = bool(reply) and bool(session)
    rec["attributed"] = is_attributed
    if reply:
        rec["reply"] = reply
    if session:
        rec["session_id"] = session
    # Owner-only: the note/reply are founder-written prose, as sensitive as
    # the correction candidates in CORRECTIONS, which have been 0600 all along.
    atomic_append(RATINGS, rec, mode=0o600)
    if is_attributed:
        print("bm_telemetry: rating %d recorded for '%s' (attributed: session %s)"
              % (score, task, session[:8]))
    else:
        print("bm_telemetry: rating %d recorded for '%s' (UNATTRIBUTED: no --reply/--session; "
              "reported separately at scorecard time, never averaged in)" % (score, task))


def cmd_review_mark(argv):
    note = redact(" ".join(argv))[0]
    # Owner-only for the same reason as RATINGS above.
    atomic_append(REVIEWS, {"ts": now_iso(), "note": note}, mode=0o600)
    print("bm_telemetry: weekly review marked")


def cmd_signal(kind, argv):
    """Record a REWORK or ESCAPED DEFECT signal (SKILL.md section 8,
    fix-round 2026-07-26): the two outcome signals the graded party cannot
    fake, because each points at something checkable outside the grader's
    own say-so, a returned deliverable or a redone artifact for REWORK, a
    defect a later session actually found in work called green for ESCAPED
    DEFECT, rather than a self-report. This only RECORDS the event; it does
    not try to auto-detect it from git history or the transcript (that is
    real analysis work, out of scope for this mechanical pass), so it is
    invoked by whichever session or founder review notices the event."""
    session, task, evidence, note = "", "", "", ""
    it = iter(argv)
    for a in it:
        if a == "--session":
            session = next(it, "")
        elif a == "--task":
            task = next(it, "")
        elif a == "--evidence":
            evidence = next(it, "")
        elif a == "--note":
            note = next(it, "")
    if not session or not task:
        print("usage: %s --session ID --task \"...\" [--evidence \"...\"] [--note \"...\"]" % kind)
        return
    rec = {"ts": now_iso(), "kind": kind, "session_id": session,
           "task": redact(task)[0], "evidence": redact(evidence)[0],
           "note": redact(note)[0]}
    # Owner-only: task/evidence/note can carry founder-written prose, the
    # same sensitivity as RATINGS and CORRECTIONS above.
    atomic_append(SIGNALS, rec, mode=0o600)
    print("bm_telemetry: %s recorded for session %s" % (kind, session[:8]))


def cmd_startup_nags():
    reviews = read_jsonl(REVIEWS)
    last = max((x.get("ts", "") for x in reviews), default=None)
    a = age_days(last) if last else None
    if a is None:
        print("BROTHERMODE NAG: weekly review has NEVER run; run tools/WEEKLY-REVIEW.md this week.")
    elif a > 7:
        print("BROTHERMODE NAG: weekly review overdue (%.0f days); run tools/WEEKLY-REVIEW.md." % a)
    led = real_sessions(read_jsonl(LEDGER))
    y = [r for r in led if 0.0 <= (age_days(r.get("ts", "")) or 99) <= 1.0]
    if y:
        yk = sum(fld(r, OUT_KEYS) + r.get("sub_out_tokens", 0) for r in y)
        print("BROTHERMODE SPEND: last 24h %dk out tokens across %d sessions." % (yk // 1000, len(y)))
    recent = [r for r in led if (age_days(r.get("ts", "")) or 99) <= 2]
    if led and not recent:
        print("BROTHERMODE NAG: telemetry heartbeat silent 48h; check the SessionEnd hook.")
    # Session-log-per-active-day nag (interim-score fix 2026-07-23): same failure
    # mode as pre-hook token telemetry, same cure. A log counts by filename date
    # OR mtime date, so late backfills clear the nag. Today is exempt (in flight).
    log_days = set()
    for f in glob.glob(SESSIONS_GLOB):
        m = re.match(r"^(\d{4}-\d{2}-\d{2})", os.path.basename(f))
        if m:
            log_days.add(m.group(1))
        try:
            log_days.add(datetime.date.fromtimestamp(os.path.getmtime(f)).isoformat())
        except OSError:
            continue
    today = datetime.date.today().isoformat()
    active = {r.get("ts", "")[:10] for r in led if 0 < (age_days(r.get("ts", "")) or 99) <= 3}
    missing = sorted(d for d in active if d and d not in log_days and d != today)
    if missing:
        print("BROTHERMODE NAG: active day(s) %s have no vault session log; backfill or waive with a note."
              % ", ".join(missing))


def cmd_stop_warn():
    """Stop hook, fires EVERY assistant turn machine-wide: must be near-free.
    Short-circuits in order; NEVER parses the transcript; warn at most once per
    session via a marker file; warn-only (exit 0 cannot block)."""
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return
    sid = payload.get("session_id") or ""
    tp = payload.get("transcript_path") or ""
    if not sid or not tp:
        return
    # Marker lives under the vault, not /tmp: a predictable /tmp name on a
    # shared machine is a symlink hazard, and the vault is already ours.
    marker = os.path.join(TEL_DIR, ".stopwarn-%s" % re.sub(r"[^A-Za-z0-9_-]", "", sid))
    if os.path.exists(marker):
        return
    try:
        if os.path.getsize(tp) < STOPWARN_MIN_BYTES:
            return
    except OSError:
        return
    today = datetime.date.today()
    for f in glob.glob(SESSIONS_GLOB):
        try:
            if datetime.date.fromtimestamp(os.path.getmtime(f)) == today:
                return
        except OSError:
            continue
    try:
        os.makedirs(TEL_DIR, exist_ok=True)
        fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        os.close(fd)
    except OSError:
        return
    print(json.dumps({"systemMessage":
        "BrotherMode: substantial session, no vault session log written today. "
        "Write the log before closing (vault law), or note why it is not needed."}))


def cmd_registry_check(argv):
    paths = argv or []
    if not paths:
        print("registry-check: pass STATE.md paths to check")
        return
    for p in paths:
        if not os.path.isfile(p):
            print("%s: missing" % p)
            continue
        age = (datetime.datetime.now().timestamp() - os.path.getmtime(p)) / 86400
        live = []
        for line in open(p, errors="replace"):
            s = line.strip()
            if s.startswith("- ") and "agent" in s.lower() and "LANDED" not in s and "ADOPTED" not in s:
                live.append(s[:90])
        if live and age > 2:
            print("%s: %d live-looking fences in a %.1f-day-old file:" % (p, len(live), age))
            for l in live:
                print("   " + l)
        else:
            print("%s: clean (%d live-looking fences, %.1fd old)" % (p, len(live), age))


def cmd_fence_lint(argv):
    """PreToolUse dispatch aid: show live fences near cwd so no writer launches
    into an occupied file set. Cheap, read-only, exit 0 always. Reads the hook
    payload from stdin when no path argument is given."""
    cwd = argv[0] if argv else ""
    if not cwd and not sys.stdin.isatty():
        try:
            cwd = (json.load(sys.stdin) or {}).get("cwd", "")
        except Exception:
            cwd = ""
    cwd = cwd or os.getcwd()
    hits = []
    # The project's own STATE.md plus any registries the user declared via
    # BROTHERMODE_REGISTRIES (colon-separated glob patterns).
    pats = [os.path.join(cwd, "STATE.md")]
    pats += [p.strip() for p in os.environ.get("BROTHERMODE_REGISTRIES", "").split(":") if p.strip()]
    for pat in pats:
        for p in glob.glob(pat, recursive=True):
            for line in open(p, errors="replace"):
                s = line.strip()
                if s.startswith("- ") and "agent" in s.lower() and "LANDED" not in s and "ADOPTED" not in s:
                    tier = "" if re.search(r"\btier T[123]\b", s) else " [NO-TIER: declare T1/T2/T3]"
                    hits.append("%s: %s%s" % (os.path.basename(p), s[:100], tier))
    if hits:
        print("LIVE FENCES (fence-then-dispatch; overlap means queue):")
        for h in hits[:8]:
            print("  " + h)
    else:
        print("fence-lint: no live fences found under %s" % cwd)


# ---------------------------------------------------------------------------
# Update awareness. This skill is a LAW: when it changes, the change has to be
# read, not silently absorbed. So the notifier does two jobs: tell you an update
# exists, and tell you once when your installed law actually changed.
#
# HARD CONSTRAINT: no network call and no subprocess, ever. Both properties are
# audited and are claimed publicly in SECURITY.md. So this reads git refs as
# ordinary files and never runs git itself. The cost is that "an update exists"
# is only known after something else has fetched; the staleness warning covers
# the rest, by telling you when your copy is simply old.
# ---------------------------------------------------------------------------
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STALE_AFTER_DAYS = 30
VERSION_MARK = os.path.join(TEL_DIR, "installed-skill-version")


def _read_first_line(path):
    try:
        with open(path, "r", errors="replace") as f:
            return f.readline().strip()
    except OSError:
        return ""


def _git_ref(git_dir, ref):
    """Resolve a ref to a sha by reading files only: loose ref first, then
    packed-refs. Returns "" when the ref cannot be resolved."""
    sha = _read_first_line(os.path.join(git_dir, ref))
    if sha and not sha.startswith("ref:"):
        return sha
    packed = os.path.join(git_dir, "packed-refs")
    try:
        for line in open(packed, "r", errors="replace"):
            if line.startswith("#") or not line.strip():
                continue
            parts = line.split()
            if len(parts) == 2 and parts[1] == ref:
                return parts[0]
    except OSError:
        pass
    return ""


def cmd_check_update():
    git_dir = os.path.join(SKILL_DIR, ".git")
    if not os.path.isdir(git_dir):
        return                      # not a git install; nothing to compare
    head = _read_first_line(os.path.join(git_dir, "HEAD"))
    branch = head[5:].strip() if head.startswith("ref:") else ""
    local = _git_ref(git_dir, branch) if branch else head
    if not local:
        return
    remote = ""
    if branch.startswith("refs/heads/"):
        name = branch[len("refs/heads/"):]
        remote = _git_ref(git_dir, "refs/remotes/origin/" + name)

    # (a) an update is already fetched and waiting
    if remote and remote != local:
        # Direction is not knowable without reading git objects, so the message
        # and the command are both symmetric: left-right marks which side each
        # commit is on, and works whether you are behind, ahead, or diverged.
        print("BROTHERMODE UPDATE: installed copy (%s) and fetched origin (%s) "
              "differ. See which side each commit is on, then update:"
              % (local[:7], remote[:7]))
        print("  git -C %s log --oneline --left-right %s...%s"
              % (SKILL_DIR, local[:7], remote[:7]))
        print("  git -C %s pull    # then re-read the sections that changed" % SKILL_DIR)
    else:
        # (b) no fetched update, but the copy may simply be old
        try:
            age = (datetime.datetime.now().timestamp()
                   - os.path.getmtime(os.path.join(SKILL_DIR, "SKILL.md"))) / 86400
        except OSError:
            age = 0
        if age > STALE_AFTER_DAYS:
            print("BROTHERMODE UPDATE: your copy of the law is %d days old. Check "
                  "for updates: git -C %s pull" % (age, SKILL_DIR))

    # (c) the law changed under you since the last session that looked: say so
    # ONCE, because a changed law must be read, not silently inherited.
    known = _read_first_line(VERSION_MARK)
    if known and known != local:
        print("BROTHERMODE: the skill changed since your last session (%s -> %s). "
              "Read the diff before relying on it:" % (known[:7], local[:7]))
        print("  git -C %s log --oneline %s..%s" % (SKILL_DIR, known[:7], local[:7]))
    if known != local:
        try:
            os.makedirs(TEL_DIR, exist_ok=True)
            with open(VERSION_MARK, "w") as f:
                f.write(local + "\n")
        except OSError:
            pass


def _load_bm_store():
    """Load bm_store.py by path, the same shape _load_bm_autosave uses below
    for bm_autosave.py: works regardless of the caller's cwd, and never
    raises (returns (None, repr(exception)) instead), so every caller here
    can degrade to an honest fallback rather than crash. bm_store.py itself
    imports no subprocess (its own header states "No network, no subprocess:
    root resolution walks the filesystem directly"), so loading it keeps
    this module's own no-subprocess property intact."""
    try:
        import importlib.util
        here = os.path.dirname(os.path.abspath(__file__))
        spec = importlib.util.spec_from_file_location(
            "bm_store_for_telemetry", os.path.join(here, "bm_store.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod, None
    except Exception as e:
        return None, repr(e)


# LAZY, NOT EAGER (this is load-bearing, not a style choice): bm_store.py's
# OWN module top level eagerly loads bm_telemetry.py BY PATH to reach
# redact() (see its _load_redact/_REDACT). Assigning `_BM_STORE = _load_bm_store()`
# here at MODULE level would exec bm_store.py during THIS module's own
# import, which would exec a fresh copy of bm_telemetry.py, which (if this
# call were also eager there) would exec bm_store.py again: unbounded mutual
# recursion between the two files' import-time side effects (reproduced
# while writing this fix; the fresh copy's stack overflows within a few
# thousand frames). bm_autosave.py avoids this the same way: it defines
# _load_bm_store() but calls it ONLY from inside a function, never at its
# own module scope. This cache defers the actual load to the first RUNTIME
# call, by which point this module has already finished importing, so the
# fresh bm_telemetry copy bm_store.py loads never re-enters this file.
_bm_store_cache = []


def _get_bm_store():
    if not _bm_store_cache:
        _bm_store_cache.extend(_load_bm_store())
    return _bm_store_cache[0], _bm_store_cache[1]


def _resolve_root_quiet(cwd):
    """bm_store.resolve_root(cwd), or (None, None) on any failure (module
    missing, exception). Never raises: every caller here is an advisory
    identity/reporting path, never a gate, so a resolution failure must
    degrade to the documented fallback, not stop work."""
    bm_store, _err = _get_bm_store()
    if bm_store is None:
        return None, None
    try:
        return bm_store.resolve_root(cwd)
    except Exception:
        return None, None


def _legacy_project_of(cwd):
    """The PRE-FIX identity (fix-round 2026-07-26, docs/REMAINING.md item 1):
    hash of the raw cwd string alone, computed from the CURRENT FOLDER rather
    than the project root. Two subfolders of one project collided into two
    different identities under this formula, so one project's resume brief
    and intent log could be read as another's. Kept ONLY so _intent_path and
    _resume_path can point at files a session wrote under it before this fix
    landed (see _migration_pointer); never used to compute a NEW identity."""
    base = re.sub(r"[^A-Za-z0-9_.-]", "_", os.path.basename(cwd.rstrip("/"))) or "session"
    h = hashlib.sha1(os.path.abspath(cwd).encode("utf-8", "replace")).hexdigest()[:6]
    return "%s-%s" % (base, h)


def _project_of(cwd):
    """Project identity used to key per-project telemetry files (intent log,
    resume brief). MUST resolve the same canonical ROOT bm_store.py and
    bm_autosave.py already use (resolve_root: BROTHERMODE_ROOT, then a
    .brothermode marker, then .git, walking up from cwd) rather than the
    current folder alone, or two subfolders of one project get two different
    identities here (the exact defect fixed everywhere else; confirmed open
    2026-07-26). Falls back to _legacy_project_of(cwd) ONLY when no root can
    be resolved (a bare folder with no marker and no git), which keeps this
    working outside a BrotherMode project instead of refusing."""
    root, _source = _resolve_root_quiet(cwd)
    if root is None:
        return _legacy_project_of(cwd)
    base = re.sub(r"[^A-Za-z0-9_.-]", "_", os.path.basename(root.rstrip("/"))) or "session"
    h = hashlib.sha1(os.path.abspath(root).encode("utf-8", "replace")).hexdigest()[:6]
    return "%s-%s" % (base, h)


def _vault_project_name(cwd):
    """The human-legible project label written into LEDGER/CORRECTIONS rows
    and correlated with <vault>/10-Projects/<name> (a human-chosen folder):
    unlike _project_of, this stays a bare basename with NO hash suffix, so it
    keeps matching the vault folder name. Same class of bug as _project_of
    fixed a CURRENT-FOLDER basename here too (docs/REMAINING.md item 1's
    class sweep, fix-round 2026-07-26): a session run from a repo's root and
    one run from a subdirectory of the SAME repo used to tag their ledger
    rows with two different project labels, fragmenting one project's
    session history. Resolves the canonical root first; falls back to
    basename(cwd) only when no root can be found."""
    root, _source = _resolve_root_quiet(cwd)
    if root:
        return os.path.basename(root) or root
    return os.path.basename(cwd) or cwd


def _migration_pointer(cwd, new_identity, path_for):
    """MIGRATION (docs/REMAINING.md item 1, fix-round 2026-07-26): the
    project-identity formula changed from _legacy_project_of (keyed on the
    raw cwd) to _project_of (keyed on the resolved root), so a file written
    under the OLD identity before this fix is not automatically found by the
    new one. Rather than silently abandoning it, print a one-line pointer to
    stderr (advisory only, never blocks) whenever a file exists under the
    OLD identity but not yet under the NEW one, naming exactly where the old
    file lives. `path_for` is _intent_path_for or _resume_path_for, called
    with each identity so the check compares the SAME file kind."""
    legacy = _legacy_project_of(cwd)
    if legacy == new_identity:
        return
    old_path = path_for(legacy)
    if os.path.exists(old_path) and not os.path.exists(path_for(new_identity)):
        print("BROTHERMODE: found a pre-migration file at %s (old per-folder identity); "
              "this session now keys by project root as %s. Nothing was moved "
              "automatically; read the old file directly if you need it."
              % (old_path, new_identity), file=sys.stderr)


def _intent_path_for(identity):
    return os.path.join(TEL_DIR, "intent-%s.log" % identity)


def _intent_path(cwd):
    identity = _project_of(cwd)
    _migration_pointer(cwd, identity, _intent_path_for)
    return _intent_path_for(identity)


def cmd_intent(argv):
    """Append one write-ahead intent line. Called by the session BEFORE a risky or
    long action so that if the session dies mid-action, the intent is already on
    disk. Pure: appends to a file, nothing else."""
    text = " ".join(argv).strip()
    if not text:
        print("usage: intent \"next: <what>, because <why>\"")
        return
    text = redact(text)[0]
    atomic_append_text(_intent_path(os.getcwd()), now_iso() + "  " + text)
    print("intent logged")


def atomic_append_text(path, line):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = (line.rstrip("\n") + "\n").encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.write(fd, data)
    finally:
        os.close(fd)


def _last_intent(cwd):
    try:
        lines = [l.rstrip("\n") for l in open(_intent_path(cwd), errors="replace") if l.strip()]
        return lines[-1] if lines else ""
    except OSError:
        return ""


def _resume_path_for(identity):
    return os.path.join(TEL_DIR, "last-resume-%s.md" % identity)


def _resume_path(cwd):
    identity = _project_of(cwd)
    _migration_pointer(cwd, identity, _resume_path_for)
    return _resume_path_for(identity)


def cmd_precompact_brief():
    """Distill the dying session into a forward-looking resume brief. The git
    autosave preserves WHAT you had (files); this preserves WHERE you were and
    WHY, which is the part a resumed model would otherwise have to re-derive.
    Mechanical extraction, not synthesis: it hands the next session the raw recent
    history so the model reconstructs the thread from complete material instead of
    a stale note. Pure python: reads the transcript file, writes one markdown file;
    no subprocess, no network."""
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return
    tp = payload.get("transcript_path") or ""
    cwd = payload.get("cwd") or os.getcwd()
    if not tp or not os.path.isfile(tp):
        return
    last_user = ""
    assistant_text = []   # recent reasoning/decision snippets
    tools = []            # recent tool actions, as short descriptors
    try:
        f = open(tp, "r", errors="replace")
    except OSError:
        return
    with f:
        for raw in f:
            try:
                o = json.loads(raw)
            except Exception:
                continue
            t = o.get("type")
            m = o.get("message") or {}
            if t == "user" and not o.get("isMeta"):
                c = m.get("content")
                txt = c if isinstance(c, str) else None
                if isinstance(c, list):
                    if not any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c):
                        txt = "\n".join(b.get("text", "") for b in c
                                        if isinstance(b, dict) and b.get("type") == "text")
                if txt and txt.strip() and "<system-reminder>" not in txt:
                    last_user = txt.strip()
            elif t == "assistant":
                for b in (m.get("content") or []):
                    if not isinstance(b, dict):
                        continue
                    if b.get("type") == "text" and b.get("text", "").strip():
                        assistant_text.append(b["text"].strip())
                    elif b.get("type") == "tool_use":
                        name = b.get("name", "")
                        inp = b.get("input") or {}
                        if name == "Bash":
                            desc = "Bash: " + (inp.get("command", "")[:100])
                        elif name in ("Edit", "Write", "Read"):
                            desc = name + ": " + str(inp.get("file_path", ""))
                        else:
                            desc = name
                        tools.append(desc)
    # Keep only the recent tail of each stream, and REDACT every stream: this file
    # holds your own recent words and commands, which can carry a pasted secret, a
    # token in a command, or a customer name. Same discipline as corrections.jsonl;
    # the earlier fix there had to be applied here too (a fix in one place must be
    # grepped for everywhere with the same shape).
    assistant_text = [redact(a)[0] for a in assistant_text[-4:]]
    tools = [redact(d)[0] for d in tools[-10:]]
    last_user = redact(last_user)[0]
    last_intent = redact(_last_intent(cwd))[0]
    lines = ["# Resume brief (auto-written before compaction)",
             "",
             "A compaction just erased the working context. The git autosave holds your",
             "files (refs/brothermode/autosave); this holds the THREAD. Read it, re-read",
             "STATE.md, then continue where this leaves off.",
             "",
             "## Next intent (write-ahead: what this session was about to do)",
             (last_intent or "(no write-ahead intent was logged)"),
             "",
             "## The last thing the founder asked",
             (last_user[:600] or "(none captured)"),
             "",
             "## What was being done (recent reasoning)"]
    for a in assistant_text:
        lines.append("- " + a[:300].replace("\n", " "))
    lines.append("")
    lines.append("## Recent actions (last %d)" % len(tools))
    for d in tools:
        lines.append("- " + d)
    lines.append("")
    # Owner-only: this is sensitive recent context, like corrections.jsonl.
    try:
        os.makedirs(TEL_DIR, exist_ok=True)
        rp = _resume_path(cwd)
        fd = os.open(rp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.write(fd, ("\n".join(lines) + "\n").encode())
        finally:
            os.close(fd)
    except OSError:
        pass


def _load_bm_autosave():
    """Load bm_autosave.py by path, exactly the pattern bm_store.py uses to
    load bm_telemetry.redact (importlib.util.spec_from_file_location by
    path, so this works regardless of the caller's cwd; see bm_store.py's
    _load_redact and the module note above it). Returns (module, None) on
    success or (None, repr(exception)) on failure; never raises, so a
    caller can degrade to an honest message instead of crashing."""
    try:
        import importlib.util
        here = os.path.dirname(os.path.abspath(__file__))
        spec = importlib.util.spec_from_file_location(
            "bm_autosave_for_telemetry", os.path.join(here, "bm_autosave.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod, None
    except Exception as e:
        return None, repr(e)


# Loaded once at import time, the same shape bm_store.py caches _REDACT in:
# a (module, error) pair at module scope rather than re-imported per call.
_BM_AUTOSAVE, _BM_AUTOSAVE_LOAD_ERROR = _load_bm_autosave()


def _autosave_recovery_line(cwd, session_id):
    """GATE E, fix-round 2026-07-26: the honesty defect. The old code
    printed "Your files are autosaved" UNCONDITIONALLY, and pointed at
    tools/bm_autosave.sh, which Phase 2 deleted. Fixed: the safety claim is
    printed ONLY when bm_autosave.has_receipt finds a real receipt row for
    THIS worktree and THIS session; every other path says plainly what is
    actually known and names the command that exists
    (tools/bm_autosave.py recover), never the deleted shell script.

    Never runs git: bm_telemetry.py's HARD CONSTRAINT (see the "Update
    awareness" section above) is no subprocess, ever, so this resolves a
    project root the same file-only way bm_store.resolve_root does (walk up
    for .brothermode or .git) rather than calling bm_autosave.resolve_toplevel,
    which shells out to `git rev-parse`. In the overwhelmingly common case
    (no BROTHERMODE_ROOT override, no exotic marker placement) that root is
    identical to the git toplevel bm_autosave itself used when it wrote the
    receipt; on the rare path where the two diverge, the failure direction
    is a false "no receipt found" (never a false claim of safety), which is
    the safe side of this contract.

    Advisory only: bm_autosave missing, a failed root resolution, or any
    other exception here all degrade to an honest "not checked" message and
    this function never raises, so a resumed session is never blocked."""
    skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    recover_cmd = "python3 %s/tools/bm_autosave.py recover" % skill_dir
    unknown = ("BROTHERMODE: resumed after a compaction. Could not verify whether "
               "your files are autosaved (%s). No claim is made either way; run "
               "`%s` yourself to look for a snapshot.")
    if _BM_AUTOSAVE is None:
        return unknown % (_BM_AUTOSAVE_LOAD_ERROR, recover_cmd)
    try:
        bs = _BM_AUTOSAVE._load_bm_store()
        if bs is None:
            return unknown % ("bm_store.py could not be loaded", recover_cmd)
        root, _source = bs.resolve_root(cwd)
        if root is None:
            return unknown % ("no BrotherMode project root found from %s" % cwd, recover_cmd)
        worktree_id = _BM_AUTOSAVE.worktree_id_for(root)
        found = _BM_AUTOSAVE.has_receipt(root, worktree_id, session_id)
    except Exception as e:
        return unknown % (repr(e), recover_cmd)
    if found:
        return ("BROTHERMODE: resumed after a compaction. Your files are autosaved "
                "(run `%s`) and the thread is below. Read it, re-read STATE.md and "
                "git status, then continue." % recover_cmd)
    return ("BROTHERMODE: resumed after a compaction. No autosave snapshot receipt "
            "was found for this worktree and session. That may mean nothing was "
            "captured yet, not that work was lost; run `%s` to look for a snapshot, "
            "and re-read STATE.md and git status either way." % recover_cmd)


def cmd_compact_hint():
    """Read the SessionStart hook payload from stdin. When the session resumed
    from a context compaction (source == "compact"), the model has just lost the
    detail of what it was doing, so point it at the autosave and at STATE.md. This
    is the READ side of work-preservation; bm_autosave.py is the write side. Pure
    by design: this never runs git itself (that would break the audited
    no-subprocess property); see _autosave_recovery_line for how it checks the
    receipt without doing so. It only ever prints, never raises (GATE E)."""
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return
    if (payload or {}).get("source") != "compact":
        return
    cwd = (payload or {}).get("cwd") or os.getcwd()
    session_id = (payload or {}).get("session_id") or "unknown"
    try:
        print(_autosave_recovery_line(cwd, session_id))
    except Exception as e:
        # Absolute backstop (GATE E requirement: never block, never raise):
        # even a bug in the honesty check itself must degrade to a message
        # that claims nothing, not to the old unconditional claim.
        print("BROTHERMODE: resumed after a compaction. Could not verify whether "
              "your files are autosaved (%r). No claim is made either way." % (e,))
    # The thread: the resume brief written at the moment of death (the WHY/where),
    # which the git snapshot does not carry.
    rp = _resume_path(cwd)
    try:
        with open(rp, "r", errors="replace") as f:
            print("")
            print(f.read().strip())
    except OSError:
        pass


def _read_head(path, limit_chars=6000):
    try:
        return open(path, errors="replace").read()[:limit_chars]
    except OSError:
        return ""


def cmd_handoff(argv):
    """Assemble a single shareable markdown for the solo founder's occasional
    hand-off to a small teammate. It is teammate-facing, so EVERY section is run
    through redact() before it is written: a handoff is exactly where a stray
    secret would travel furthest. Pure python (reads vault files, writes one file);
    no subprocess, no network, preserving the audited properties."""
    projects_dir = os.path.join(VAULT, "10-Projects")
    name = argv[0] if argv else ""
    if not name:
        try:
            avail = sorted(d for d in os.listdir(projects_dir)
                           if os.path.isdir(os.path.join(projects_dir, d)))
        except OSError:
            avail = []
        print("usage: handoff <project>. available: %s" % (", ".join(avail) or "(none)"))
        return
    base = os.path.join(projects_dir, name)
    if not os.path.isdir(base):
        print("handoff: no vault project named %r under %s" % (name, projects_dir))
        return
    parts = ["# Handoff: %s" % name, "",
             "A shareable summary of this project for a teammate. Assembled from the",
             "vault and secret-redacted. It is a snapshot, not the living record.", ""]
    overview = _read_head(os.path.join(base, "Overview.md"))
    if overview:
        parts += ["## Overview", redact(overview)[0], ""]
    openitems = _read_head(os.path.join(base, "Open-Items.md"))
    if openitems:
        parts += ["## Open items", redact(openitems)[0], ""]
    # latest session log by mtime
    sessions = glob.glob(os.path.join(base, "Sessions", "*.md"))
    if sessions:
        latest = max(sessions, key=lambda f: os.path.getmtime(f))
        parts += ["## Most recent session (%s)" % os.path.basename(latest),
                  redact(_read_head(latest, 4000))[0], ""]
    # last few outcome lines
    oc = _read_head(os.path.join(base, "OUTCOMES.md"), 20000)
    if oc:
        tail = [l for l in oc.splitlines() if l.strip()][-6:]
        parts += ["## Recent outcomes", redact("\n".join(tail))[0], ""]
    out = os.path.join(os.getcwd(), "handoff-%s.md" % re.sub(r"[^A-Za-z0-9_.-]", "_", name))
    try:
        with open(out, "w") as f:
            f.write("\n".join(parts) + "\n")
        print("handoff written (secret-redacted): %s" % out)
        print("review it before sharing; it is a snapshot, redaction is best-effort.")
    except OSError as e:
        print("handoff: could not write (%r)" % (e,))


def cmd_purge_corrections(argv):
    """Delete captured correction candidates. They are excerpts of your own
    messages; purge them once the weekly review has distilled what it needs, or
    at any time. Prints exactly what it will remove before removing it."""
    rows = read_jsonl(CORRECTIONS)
    if not rows:
        print("purge-corrections: nothing to purge (%s)" % CORRECTIONS)
        return
    if "--yes" not in argv:
        print("purge-corrections: %d candidate(s) in %s" % (len(rows), CORRECTIONS))
        print("  oldest: %s   newest: %s" % (rows[0].get("ts", "?"), rows[-1].get("ts", "?")))
        print("  re-run with --yes to delete the file.")
        return
    try:
        os.remove(CORRECTIONS)
        print("purge-corrections: removed %d candidate(s) from %s" % (len(rows), CORRECTIONS))
    except OSError as e:
        print("purge-corrections: could not remove (%r)" % (e,))


def cmd_prediction_audit():
    c = prediction_counts()
    print("prediction ledger: %d sealed, %d scored (all outcomes), %d hits (all outcomes) (%s)"
          % (c["sealed"], c["scored"], c["hits"], FOUNDER_MODEL))
    if c["sealed"] == 0:
        print("AUDIT FLAG: zero sealed predictions; section 14 requires sealing BEFORE recommendations.")
    # DIVERGED-ONLY scoring (SKILL.md section 8): agreement cases carry no
    # alignment signal, so the honest audit line is "0 scored divergent
    # predictions" when none exist, never a ratio built on agreement.
    if c["diverged_scored"] == 0:
        print("prediction alignment: 0 scored divergent predictions (the honest number; "
              "scoring agreement cases rewards flattery, so they are excluded rather than "
              "folded into a ratio).")
    else:
        print("prediction alignment (diverged only): %d/%d hits"
              % (c["diverged_hits"], c["diverged_scored"]))
    if c["unmarked"]:
        print("AUDIT FLAG: %d scored prediction(s) have no diverged/agreed marker (column 4); "
              "mark each 'yes' or 'no' so alignment can be scored honestly." % c["unmarked"])


# DELETED (fix-round 2026-07-26): `attribute <record_id> <output_tokens>` used
# to load bm_registry.py by path and accumulate spend onto d["records"][rid],
# a dict-shaped registry.json record. Phase 3 deleted bm_registry.py and
# rewired ownership onto bm_store.py's sqlite schema, which has no "spend"
# column or table at all, so the command had been silently no-op'ing behind
# its own bare except (confirmed: nothing in this repo calls `attribute`
# except historical design docs, and no test exercised its success path). A
# command that silently does nothing is worse than one that does not exist,
# and porting it forward would mean inventing a spend concept the store was
# never given, which is out of scope here. Deleted rather than repaired.
def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    argv = sys.argv[2:]
    try:
        if cmd == "outcomes-append":
            cmd_outcomes_append()
        elif cmd == "migrate":
            cmd_migrate()
        elif cmd == "scorecard":
            cmd_scorecard()
        elif cmd == "rate":
            cmd_rate(argv)
        elif cmd == "review-mark":
            cmd_review_mark(argv)
        elif cmd == "rework":
            cmd_signal("rework", argv)
        elif cmd == "escaped-defect":
            cmd_signal("escaped-defect", argv)
        elif cmd == "startup-nags":
            cmd_startup_nags()
        elif cmd == "stop-warn":
            cmd_stop_warn()
        elif cmd == "registry-check":
            cmd_registry_check(argv)
        elif cmd == "fence-lint":
            cmd_fence_lint(argv)
        elif cmd == "intent":
            cmd_intent(argv)
        elif cmd == "precompact-brief":
            cmd_precompact_brief()
        elif cmd == "compact-hint":
            cmd_compact_hint()
        elif cmd == "check-update":
            cmd_check_update()
        elif cmd == "handoff":
            cmd_handoff(argv)
        elif cmd == "purge-corrections":
            cmd_purge_corrections(argv)
        elif cmd == "prediction-audit":
            cmd_prediction_audit()
        elif cmd == "speed":
            cmd_speed()
        elif cmd == "dedup":
            cmd_dedup()
        else:
            print(__doc__.strip())
    except Exception as e:
        print("bm_telemetry: swallowed error (never blocks): %r" % (e,))
    sys.exit(0)


if __name__ == "__main__":
    main()
