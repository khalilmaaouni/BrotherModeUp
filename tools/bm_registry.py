#!/usr/bin/env python3
"""BrotherMode work registry: one record for every unit of claimed work.

A thread is a record with lifetime "persistent". A fence is the same record with
lifetime "ephemeral". Nothing else differs, which is the point: one source of
truth for who owns what work, so the two registries can no longer disagree.

Pure file I/O. No network, no subprocess. Every text field is redacted at the
write, so no caller can forget. Every path returns rather than raises.
"""
import copy, io, json, os, re, sys, fnmatch, posixpath, datetime, hashlib

SCHEMA = 1
REGISTRY_DIRNAME = "threads"
REGISTRY_FILE = "registry.json"
VIEW_FILE = "REGISTRY.md"
DIGEST_CAP = 4000


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def registry_dir(cwd=None):
    return os.path.join(cwd or os.getcwd(), REGISTRY_DIRNAME)


def registry_path(cwd=None):
    return os.path.join(registry_dir(cwd), REGISTRY_FILE)


_WARNED_NONATOMIC = []


def atomic_write(path, text, mode=0o644):
    """Crash-atomic whole-file replacement, borrowed from bm_telemetry so there
    is exactly ONE implementation, the same rule the redactor and the lock
    follow. A plain truncating write can leave the registry empty after a crash,
    and an empty registry reads as "no work in progress", which is the most
    dangerous thing this file can say.

    If the shared primitive cannot be loaded, fall back to a plain write and say
    so once, rather than pretending the guarantee holds."""
    try:
        import importlib.util
        here = os.path.dirname(os.path.abspath(__file__))
        spec = importlib.util.spec_from_file_location(
            "bm_telemetry_for_atomic", os.path.join(here, "bm_telemetry.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        fn = getattr(mod, "atomic_write", None)
        if fn is not None:
            return fn(path, text, mode)
        reason = "bm_telemetry.py has no atomic_write()"
    except OSError:
        # A real write failure from the primitive must propagate, not be
        # retried non-atomically: the caller decides what a failed write means.
        raise
    except Exception as e:
        reason = repr(e)
    if not _WARNED_NONATOMIC:
        _WARNED_NONATOMIC.append(True)
        print("bm_registry: WARNING: writing state NON-atomically (%s). A crash "
              "mid-write can leave a state file empty or truncated." % reason,
              file=sys.stderr)
    with io.open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return True


def durable_append(path, text):
    """Append and make the bytes durable BEFORE returning.

    A plain append returns as soon as the data is in the page cache. A crash
    then loses the handover while anything written afterwards (a marker, a
    record state change) may already be on disk, so the system believes a
    handover was delivered that no longer exists. fsync closes that window.
    Raises OSError; the caller decides what a failed handover means."""
    with io.open(path, "a", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    return True


def handover_tag(identity, body):
    """The identity of one DELIVERY: which life of which record, plus what was
    actually said.

    Two things must both be true and they pull in opposite directions. A retry
    of the SAME handover must not duplicate it, and a handover whose CONTENT has
    changed must still be delivered. Keying on the lifecycle alone gave the
    first and broke the second: after a partial failure the thread checkpointed
    new work, the retry matched the old tag, and the newer handover was silently
    discarded while the record was closed.

    So the tag carries a fingerprint of the exact bytes being delivered. Same
    life and same words is a retry; same life and different words is a new
    revision."""
    digest = hashlib.sha256((body or "").encode("utf-8")).hexdigest()[:12]
    return "<!-- brothermode-handover:%s:%s -->" % (identity, digest)


def record_payload(rec):
    """The handover CONTENT of a record, independent of how any command chooses
    to format it around the edges.

    The fingerprint must describe what is being handed over, not the prose the
    caller wrapped it in: absorb and adopt render the same digest differently,
    so hashing the rendered text made one record's handover look like two
    different ones and it was delivered twice."""
    if not isinstance(rec, dict):
        return ""
    decisions = rec.get("decisions")
    parts = [safe_str(rec.get("digest"))]
    if isinstance(decisions, list):
        for dec in decisions:
            if isinstance(dec, dict):
                parts.append("%s=%s" % (safe_str(dec.get("topic")),
                                        safe_str(dec.get("text"))))
    return "\n".join(parts)


def deliver_handover(target, identity, body, payload=None):
    """Append a handover EXACTLY once per lifecycle. The one place any handover
    reaches the project STATE.md, used by both absorb() and adopt().

    The proof of delivery is the tag INSIDE the delivered text, not a separate
    marker file, so the two can never disagree: if the content is there the
    proof is there, and if the append was lost so was the proof. A side marker
    can survive content that a crash destroyed, which is the worse direction.

    Returns "delivered", "already", or False when the write failed."""
    # Fingerprint the PAYLOAD when the caller names one, so two commands that
    # render the same handover differently still recognise each other's delivery.
    tag = handover_tag(identity, body if payload is None else payload)
    try:
        with io.open(target, encoding="utf-8", errors="replace") as f:
            existing = f.read()
    except OSError:
        existing = ""
    if tag and tag in existing:
        return "already"
    try:
        durable_append(target, body.rstrip("\n") + "\n" + tag + "\n")
    except OSError as e:
        print("bm_registry: warning: could not write the handover to %s (%s)"
              % (target, e), file=sys.stderr)
        return False
    return "delivered"


def _load_redactor():
    """Reuse bm_telemetry's pattern set so there is exactly one definition of
    what a secret looks like. Fall back to a compact inline set rather than ever
    writing text unredacted."""
    try:
        import importlib.util
        here = os.path.dirname(os.path.abspath(__file__))
        spec = importlib.util.spec_from_file_location(
            "bm_telemetry_for_registry", os.path.join(here, "bm_telemetry.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "redact"):
            return mod.redact
        reason = "bm_telemetry.py has no redact()"
    except Exception as e:
        reason = repr(e)
    # Silently weaker redaction is the wrong failure direction: say so, loudly,
    # and name what this set does NOT cover so the gap is not a surprise.
    print("bm_registry: warning: could not load the bm_telemetry redactor (%s); "
          "falling back to a reduced pattern set that does NOT cover github_pat "
          "tokens, slack tokens, JWTs, or card numbers" % reason, file=sys.stderr)
    pats = [
        re.compile(r"\b(sk|rk)[-_][A-Za-z0-9_-]{12,}", re.I),
        re.compile(r"\bgh[oprsu]_[A-Za-z0-9]{16,}"),
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        re.compile(r"\b[Bb]earer\s+[A-Za-z0-9._~+/=-]{16,}"),
        # Kept in step with bm_telemetry.SECRET_PATTERNS: a private key is a
        # block, and masking only the header line leaks the key material.
        re.compile(r"-----BEGIN[ A-Z]*PRIVATE KEY-----"
                   r"(?:[\s\S]*?-----END[ A-Z]*PRIVATE KEY-----"
                   r"|(?:\s*[A-Za-z0-9+/=]{16,})*)"),
        re.compile(r"(?i)[A-Za-z0-9_]*(?:pass(?:word|wd|phrase)?|secret|token"
                   r"|api[_-]?key|access[_-]?key|private[_-]?key|credential)s?"
                   r"\s*(?:[:=]|\s+(?:is|was)\s+)\s*\S+"),
        re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    ]

    def _fallback(text):
        n = 0
        for p in pats:
            text, k = p.subn("[REDACTED]", text)
            n += k
        return text, n
    return _fallback


_REDACT = _load_redactor()


def redact_text(t):
    """Always returns redacted text. Never returns the raw string."""
    try:
        return _REDACT(t or "")[0]
    except Exception:
        return "(redaction failed; text withheld)"


def load(cwd=None):
    """Read the registry. A missing file is an empty registry (the normal
    first-run case, no warning). An unreadable or unparsable existing file is
    also an empty registry, but prints a warning to stderr since that is a real
    degradation. An unknown schema or unknown fields are preserved rather than
    dropped."""
    raw = None
    try:
        with io.open(registry_path(cwd), encoding="utf-8", errors="replace") as f:
            raw = f.read()
    except OSError:
        raw = None
    d = {}
    if raw is not None:
        try:
            d = json.loads(raw or "{}")
        # RecursionError as well as ValueError: pathologically nested JSON blows
        # the parser's stack rather than reporting a parse error, and load() is
        # documented to never raise.
        except (ValueError, RecursionError) as e:
            print("bm_registry: warning: could not parse %s (%s); treating as empty"
                  % (registry_path(cwd), e), file=sys.stderr)
            d = {}
    if not isinstance(d, dict):
        d = {}
    d.setdefault("schema", SCHEMA)
    d.setdefault("records", {})
    if not isinstance(d["records"], dict):
        d["records"] = {}
    return d


def _redact_record_fields(rec):
    """Redact the text-bearing fields of one record in place. Defensive: a
    record, or a decision inside it, that is not a dict is skipped rather than
    raising, and only string fields are touched so files/spend/lease/state/
    lifetime/tier/id/schema are left alone."""
    if not isinstance(rec, dict):
        return
    for key in ("objective", "digest", "check", "evidence"):
        val = rec.get(key)
        if isinstance(val, str):
            rec[key] = redact_text(val)
    decisions = rec.get("decisions")
    if isinstance(decisions, list):
        for dec in decisions:
            if not isinstance(dec, dict):
                continue
            for key in ("topic", "text"):
                val = dec.get(key)
                if isinstance(val, str):
                    dec[key] = redact_text(val)


def save(d, cwd=None):
    """Write the registry. Every text-bearing field of every record is redacted
    here, at the write, so no caller of save() can forget: this is the one real
    write boundary. Redaction is idempotent, so records that were already
    redacted by new_record() are unaffected."""
    try:
        redacted = copy.deepcopy(d)
        records = redacted.get("records") if isinstance(redacted, dict) else None
        if isinstance(records, dict):
            for rec in records.values():
                _redact_record_fields(rec)
        os.makedirs(registry_dir(cwd), exist_ok=True)
        # Crash-atomic: a truncating write here can empty the registry, and an
        # empty registry reads as "no work in progress", which would let a
        # second writer claim files someone is already editing.
        atomic_write(registry_path(cwd),
                     json.dumps(redacted, indent=2, sort_keys=True) + "\n")
        return True
    # TypeError and ValueError as well as OSError: a caller that declares a file
    # as a pathlib.Path (an obvious thing to do) makes json.dumps raise, and a
    # registry helper must report that, not throw it at a work session.
    except (OSError, TypeError, ValueError) as e:
        print("bm_registry: warning: could not save %s (%s)"
              % (registry_path(cwd), e), file=sys.stderr)
        return False


_WARNED_UNLOCKED = []


def warn_unlocked(reason):
    """Report once per process that something ran without its lock.

    Once, not every call: a per-call warning on a platform that simply has no
    fcntl would bury every other message the session prints, and a warning
    nobody reads is the same as no warning.

    Public because bm_threads locks its own mode file through locked_call, and
    every degraded path in this system must speak with one voice. A second
    silent fallback elsewhere would put the founder right back where they
    started: believing writes are serialized when they are not."""
    if _WARNED_UNLOCKED:
        return
    _WARNED_UNLOCKED.append(True)
    # The reason carries a filesystem path and an OS error string, so it goes
    # through redaction like every other text this module emits. A terminal is
    # not a file, but terminals get logged, and "it is only a warning" is the
    # reasoning behind every leak this project has had to fix.
    print("bm_registry: WARNING: running WITHOUT a file lock (%s). Work still "
          "proceeds for a single session, but concurrent writes are NOT "
          "serialized: two sessions at once can lose a record or a thread. "
          "Treat coordination as degraded and avoid parallel writers here."
          % (redact_text(str(reason)),), file=sys.stderr)


def locked_call(lock_path, fn):
    """Run fn holding an exclusive lock on lock_path, or say why it could not.

    The single locking primitive for the whole system. Every way this can fail
    to acquire (no fcntl on this platform, an uncreatable directory, an
    unopenable lock file) still runs fn, because never-block outranks
    coordination, and every one of them warns, because a silent degrade is
    indistinguishable from working correctly until work is already lost."""
    lock_dir = os.path.dirname(lock_path)
    try:
        os.makedirs(lock_dir, exist_ok=True)
    except OSError as e:
        warn_unlocked("cannot create the lock directory %s (%s)" % (lock_dir, e))
        return fn()
    try:
        fh = open(lock_path, "w")
    except OSError as e:
        warn_unlocked("cannot open the lock file %s (%s)" % (lock_path, e))
        return fn()
    locked = False
    try:
        try:
            import fcntl
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            locked = True
        except Exception as e:
            # fcntl is POSIX only, so this is the Windows path.
            warn_unlocked("file locking is unavailable on this platform (%s)" % (e,))
        return fn()
    finally:
        if locked:
            try:
                import fcntl
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
        fh.close()


def with_lock(fn, cwd=None):
    """Exclusive lock around any read-modify-write of the registry. Without it,
    two concurrent claims each read the old registry and the second write wins,
    losing a record: invisible to the dashboard and skipped by absorb, which
    silently loses work."""
    return locked_call(os.path.join(registry_dir(cwd), ".registry.lock"), fn)


def _stored_files(files):
    """Coerce a declared-files argument into the list a record stores.

    Mirrors _safe_path_list on the comparison side, for the same reason: a bare
    string is ONE path, and list("api/pay.py") used to store ten single
    character fences that guard nothing. An argument that cannot be a file list
    at all records no fence rather than raising out of claim(), which must
    never block a work session."""
    if files is None:
        return []
    if isinstance(files, str):
        return [files]
    try:
        return list(files)
    except TypeError:
        return []


def new_record(rid, lifetime, objective, files, tier=None, owner=None, ttl_days=2):
    """Build a work record. lifetime is "persistent" (a thread) or "ephemeral"
    (an agent dispatch); every other field is identical between the two."""
    return {
        "schema": SCHEMA,
        "id": rid,
        "lifetime": lifetime,
        "owner": owner or "",
        "objective": redact_text(objective),
        "files": _stored_files(files),
        "tier": tier or "",
        "lease": {"claimed_at": now(), "ttl_days": ttl_days},
        "state": "active",
        "check": "",
        "evidence": "",
        "decisions": [],
        "digest": "",
        "spend": {"output_tokens": 0, "sessions": 0},
        # Which LIFE of this id this is. A thread name is reusable, so delivery
        # proof must be keyed on the lifecycle: without this, a second thread
        # called "payments" inherits the first one's handover proof and its own
        # handover is silently discarded.
        "lifecycle": 1,
    }


def _norm(p):
    """Normalize a declared path for comparison: posix separators, no leading
    ./, no trailing slash, ~ expanded to the home directory, folded to
    lowercase. A trailing slash is remembered by _is_dir_decl before
    normalization strips it.

    Case folding is deliberate: this project's own development platform (macOS)
    has a case-insensitive filesystem by default, so "API/pay.py" and
    "api/pay.py" name the same file there and must be reported as an overlap.
    On a case-sensitive filesystem (Linux) this can over-block two paths that
    are genuinely different files. Per this function's guiding principle, that
    is the acceptable direction: a false positive costs one refusal, a false
    negative costs lost work."""
    p = (p or "").strip().replace("\\", "/")
    p = posixpath.expanduser(p)
    p = posixpath.normpath(p)
    p = "" if p == "." else p
    return p.lower()


def _is_dir_decl(p):
    return (p or "").strip().endswith("/")


def _is_rooted(p):
    """True when a normalized path names a location without needing to know
    anyone's working directory."""
    return p.startswith("/")


def _needs_forms(p):
    """True when a normalized path cannot be compared literally against a plain
    project-relative declaration: it is absolute (possibly after ~ expansion),
    or it climbs out of the working directory with .. segments."""
    return _is_rooted(p) or p == ".." or p.startswith("../")


def _comparison_forms(p):
    """Every form a path may take when compared against a project-relative
    declaration, longest first.

    "/repo/api/pay.py" and "api/pay.py" are the same file whenever the working
    directory is /repo, and this module never learns the working directory of
    whoever typed the other declaration: the two lists being compared can come
    from two different sessions. So each trailing run of components is offered
    as a candidate ("repo/api/pay.py", "api/pay.py", "pay.py"). Per this
    module's guiding principle, OVER-BLOCKING IS SAFE and UNDER-BLOCKING IS A
    DATA-LOSS BUG: the cost of a spurious form match is one refusal to explain,
    the cost of a miss is two writers on one file."""
    parts = [seg for seg in p.split("/") if seg and seg != ".."]
    forms = [p] + ["/".join(parts[i:]) for i in range(len(parts))]
    out = []
    for f in forms:
        if f and f not in out:
            out.append(f)
    return out


def _one_overlaps(a, b):
    """True when two declared paths can touch the same file."""
    a_dir, b_dir = _is_dir_decl(a), _is_dir_decl(b)
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return False
    # Two absolute paths are each fully determined, so when they differ they
    # genuinely name different files: compare them literally. Otherwise expand
    # whichever side cannot be read as a project-relative path, so an absolute,
    # ~-rooted, or ..-climbing declaration still collides with the plain
    # relative form of the same file.
    if _is_rooted(na) and _is_rooted(nb):
        forms_a, forms_b = [na], [nb]
    else:
        forms_a = _comparison_forms(na) if _needs_forms(na) else [na]
        forms_b = _comparison_forms(nb) if _needs_forms(nb) else [nb]
    for fa in forms_a:
        for fb in forms_b:
            if _forms_touch(fa, fb, a_dir, b_dir):
                return True
    return False


def _forms_touch(na, nb, a_dir, b_dir):
    """The comparison itself, on two already normalized path forms."""
    if na == nb:
        return True
    # A directory declaration covers everything beneath it.
    if a_dir and (nb == na or nb.startswith(na + "/")):
        return True
    if b_dir and (na == nb or na.startswith(nb + "/")):
        return True
    # Prefix containment overlaps even without a trailing slash. A claimant who
    # declares "api" (meaning the directory, but without the trailing slash
    # that would normally mark it as one) must still conflict with a claimant
    # who declares "api/pay.py": otherwise both claims are granted and the
    # second one silently destroys the first one's work. Over-blocking here,
    # for example if "api" was truly meant as a bare file with no extension,
    # is the acceptable direction per this function's guiding principle.
    if nb.startswith(na + "/") or na.startswith(nb + "/"):
        return True
    # Glob on either side. fnmatch is not path aware: "*" crosses "/", so for
    # example "api/*.py" also matches "api/sub/pay.py", not only files that
    # sit directly inside "api/". ** is expanded to match across separators,
    # which in practice does not add reach beyond what "*" already has here.
    for pat, other in ((na, nb), (nb, na)):
        if any(ch in pat for ch in "*?["):
            if fnmatch.fnmatch(other, pat):
                return True
            if "**" in pat and fnmatch.fnmatch(other, pat.replace("**", "*")):
                return True
            if fnmatch.fnmatch(other, pat.rstrip("/") + "/*"):
                return True
    return False


def _safe_path_list(files):
    """Coerce a declared-files argument into a list of strings, defensively.
    paths_overlap is a safety function and must never raise: a bare string is
    treated as a single path rather than iterated character by character, a
    non-iterable or None becomes an empty list, and any non-string entry is
    dropped rather than guessed at."""
    if isinstance(files, str):
        return [files]
    try:
        return [f for f in files if isinstance(f, str)]
    except TypeError:
        return []


def unguarded_count(files):
    """How many declared file entries were dropped as unreadable.

    _safe_path_list drops a non-string entry rather than guessing at it, which
    keeps the safety functions from raising. That choice is deliberate but it
    UNDER-BLOCKS: a record whose files field is corrupt guards fewer paths than
    its owner believes, so a second writer can be granted a file someone is
    already editing. The alternative, treating an unreadable entry as matching
    everything, would let one corrupt record freeze every future claim, which
    breaks the never-block law. So the drop stays and the silence goes: the
    generated view marks any record that is guarding less than it declared."""
    if isinstance(files, str) or not isinstance(files, list):
        return 0
    return sum(1 for f in files if not isinstance(f, str))


def files_line(files):
    """Render a stored files field as one human-readable line, defensively.

    A record is JSON on disk, so after a hand edit or a newer schema its files
    field can hold anything. Joining it blind raised TypeError inside absorb(),
    which killed the lossless exit BEFORE STATE.md was written and lost the
    handover digest for good. Same rule as _safe_path_list: a non-list is not
    guessed at, and a non-string entry is dropped rather than crashing the one
    function whose job is to never lose work."""
    if not isinstance(files, list):
        return "(none)"
    safe = _safe_path_list(files)
    return ", ".join(safe) if safe else "(none)"


def safe_str(v):
    """Coerce a stored field to a string before it is sliced or concatenated.
    Same reason as files_line: "%s" tolerates any type, but [:200] does not."""
    if isinstance(v, str):
        return v
    return "" if v is None else str(v)


def paths_overlap(a_files, b_files):
    """Return every conflicting pair between two file lists. Empty means
    disjoint. Tolerant of a non-list argument (None, a bare string) or a list
    with non-string entries: those never raise, they are just excluded from
    consideration, because a safety function must never crash the caller."""
    hits = []
    for a in _safe_path_list(a_files):
        for b in _safe_path_list(b_files):
            if _one_overlaps(a, b):
                hits.append((a, b))
    return hits


def claim(rid, lifetime, objective, files, tier=None, owner=None, cwd=None):
    """Register work. Refuses when the declared files overlap another ACTIVE
    record, returning that record so the caller can name it. Reclaiming under
    the same id is allowed, because that is the same owner re-declaring."""
    def _do():
        d = load(cwd)
        # An unreadable entry is dropped, so this claim guards less than it was
        # asked to. The generated view says so too, but that file is gitignored
        # and nobody opens it on a normal day: warn where the human is looking.
        dropped = unguarded_count(files)
        if dropped:
            # The record id is founder-typed text, so it goes through redaction
            # like every other text this module emits. A terminal is not a file,
            # but terminals get logged, and "it is only a warning" is exactly the
            # reasoning behind every leak this project has had to fix.
            sys.stderr.write(
                "WARNING: %d declared file entry(s) for %r are unreadable and will NOT be "
                "guarded. Another writer can be granted them.\n" % (dropped, redact_text(rid)))
        for other_id, rec in d["records"].items():
            # A record that is not a dict (a corrupt or hand-edited registry
            # entry, for example a bare string) is skipped rather than raising:
            # follows the same defensive pattern as _redact_record_fields.
            if other_id == rid or not isinstance(rec, dict) or rec.get("state") != "active":
                continue
            if paths_overlap(files, rec.get("files")):
                return (False, rec)
        rec = d["records"].get(rid)
        if rec:
            closed = rec.get("state") in ("parked", "adopted", "landed", "failed-start")
            if closed:
                # A new life gets a NEWLY CONSTRUCTED record, not a partial
                # reset. Listing the fields to clear (digest, decisions, check,
                # evidence, spend, lease) has the same defect as the marker file
                # it replaced: the list rots the moment someone adds a field,
                # and the stale value then leaks into a life it never belonged
                # to. Reconstruction is correct for fields that do not exist yet.
                # Proven case: life 1's digest and decisions were delivered again
                # under life 2 as if they were that thread's work.
                try:
                    nxt = int(rec.get("lifecycle", 1)) + 1
                except (TypeError, ValueError):
                    nxt = 2
                rec = new_record(rid, lifetime, objective, files, tier, owner)
                rec["lifecycle"] = nxt
                d["records"][rid] = rec
            else:
                rec.setdefault("lifecycle", 1)
                rec["objective"] = redact_text(objective)
                rec["files"] = _stored_files(files)
                rec["state"] = "active"
                if tier:
                    rec["tier"] = tier
        else:
            d["records"][rid] = new_record(rid, lifetime, objective, files, tier, owner)
        # Report what the SAVE did. Returning True after a failed write tells
        # the caller a fence exists that is not on disk, so a second writer is
        # granted the same files: the exact collision this module prevents.
        if not save(d, cwd):
            return (False, None)
        return (True, None)
    return with_lock(_do, cwd)


def _topic_key(t):
    """Normalize a topic so "Payments API", "payments-api" and "payments_api"
    are the same topic. Matching is deliberately literal: this catches two
    records deciding the same NAMED topic, and does not attempt to understand
    that two differently named topics are semantically incompatible.

    Defensive: topics also arrive from the registry file, where a hand edit can
    leave any JSON type. A non-string topic normalizes to the empty key, which
    never clashes, rather than raising out of decide()."""
    if not isinstance(t, str):
        t = ""
    return re.sub(r"[^a-z0-9]+", "-", t.strip().lower()).strip("-")


def decide(rid, topic, text, cwd=None):
    """Record a tagged decision. Returns (True, clash_or_None). The decision is
    always recorded, even on a clash: the point is to surface the contradiction
    to the chief, not to silently drop a thread's decision."""
    def _do():
        d = load(cwd)
        rec = d["records"].get(rid)
        # A target record that is missing, or that is not a dict (a corrupt or
        # hand-edited registry entry), is reported the same way: not found,
        # rather than raising on the setdefault below.
        if not isinstance(rec, dict):
            return (False, None)
        key = _topic_key(topic)
        clash = None
        # An empty normalized topic (empty or all-punctuation) means "no
        # topic": it must never match another empty topic, so skip clash
        # detection entirely when this decision's own key is empty.
        if key:
            for other_id, other in d["records"].items():
                # A record that is not a dict (a corrupt or hand-edited
                # registry entry, for example a bare string) is skipped
                # rather than raising: follows the same defensive pattern as
                # claim().
                if other_id == rid or not isinstance(other, dict) or other.get("state") != "active":
                    continue
                decisions = other.get("decisions")
                if not isinstance(decisions, list):
                    continue
                for dec in decisions:
                    if not isinstance(dec, dict):
                        continue
                    # An empty topic on the other side is also "no topic" and
                    # must not match, even though key is non-empty here.
                    other_key = _topic_key(dec.get("topic"))
                    if other_key and other_key == key:
                        clash = {"record": other_id, "topic": dec.get("topic"),
                                 "text": dec.get("text")}
                        break
                if clash:
                    break
        # setdefault is not enough: a decisions field that exists but is not a
        # list has no append, and the decision would be lost to an
        # AttributeError. Repair it, the same way _history does in bm_threads.
        if not isinstance(rec.get("decisions"), list):
            rec["decisions"] = []
        rec["decisions"].append(
            {"topic": redact_text(topic), "text": redact_text(text), "ts": now()})
        # A decision the caller believes is recorded but that never reached disk
        # is worse than no decision: it will be made again, differently.
        if not save(d, cwd):
            return (False, clash)
        return (True, clash)
    return with_lock(_do, cwd)


def set_digest(rid, text, cwd=None):
    """Replace a record's handover digest. Kept current as work proceeds so the
    lossless exit never needs the thread to still be alive."""
    def _do():
        d = load(cwd)
        rec = d["records"].get(rid)
        # A target record that is missing, or that is not a dict (a corrupt or
        # hand-edited registry entry), is reported the same way: not found,
        # rather than raising on the item assignment below.
        if not isinstance(rec, dict):
            return False
        rec["digest"] = redact_text(text)[:DIGEST_CAP]
        # The digest IS the handover. Reporting it stored when the write failed
        # is how a lossless exit silently stops being lossless.
        return save(d, cwd)
    return with_lock(_do, cwd)


def close(rid, state="parked", cwd=None):
    """Close a record WITHOUT draining it: the caller has already taken the
    handover somewhere else (adopt writes it into the chief's STATE.md).

    Two things depend on this. A record left active is drained a second time by
    absorb(), so the same handover lands in STATE.md twice; and its files stay
    fenced by an owner that no longer exists, so later claims are refused by a
    record nobody can see. Returns True when a record was closed."""
    def _do():
        d = load(cwd)
        rec = d["records"].get(rid)
        # Same defensive rule as set_digest: a missing or non-dict record is
        # reported as not found rather than raising.
        if not isinstance(rec, dict):
            return False
        rec["state"] = state
        rec["closed_at"] = now()
        # Return what the SAVE did, not what the in-memory edit did. Returning
        # True after a failed write is the same defect this project already had
        # to fix in absorb(): the caller sees success, tells the founder the
        # record is closed, and the record is still active on disk.
        return save(d, cwd)
    return with_lock(_do, cwd)


def absorb(cwd=None):
    """Drain every active record's digest and decisions into the project's
    STATE.md and park the records. Nothing is deleted, so a parked record can be
    resumed. This is the lossless exit: it works from disk alone and never needs
    the owning session to still be alive."""
    def _do():
        d = load(cwd)
        # PER RECORD, not one combined block. Identity must describe WHAT is
        # delivered, not WHO delivered it: absorb used to tag the whole batch
        # under "absorb:<ids>" while adopt tagged the same digest under
        # "<id>#<life>", so a handover delivered by a failed `off` was delivered
        # AGAIN by a later adopt, twice in STATE.md. One record, one identity,
        # whichever command happens to drain it.
        candidates = []
        for rid in sorted(d.get("records", {})):
            rec = d["records"][rid]
            # Defensive: skip records that are not dicts.
            if not isinstance(rec, dict):
                continue
            # Skip records that are not active.
            if rec.get("state") != "active":
                continue
            lines = []
            lines.append("")
            lines.append("## Registry handover: %s (absorbed %s)" % (rid, now()))
            lines.append("Drained and parked, not deleted; this record can be resumed.")
            lines.append("")
            lines.append("### Record: %s (%s)" % (rid, rec.get("lifetime", "?")))
            lines.append("- objective: %s" % rec.get("objective", ""))
            # Defensive: a files field that is not a list, or that holds
            # non-string entries, renders as empty rather than raising here.
            lines.append("- files: %s" % files_line(rec.get("files", [])))
            # Defensive: treat decisions field as empty if not a list.
            decisions = rec.get("decisions", [])
            if isinstance(decisions, list):
                for dec in decisions:
                    # Defensive: skip decisions that are not dicts.
                    if isinstance(dec, dict):
                        lines.append("- decision [%s]: %s" % (dec.get("topic", ""), dec.get("text", "")))
            if rec.get("digest"):
                lines.append("- digest: %s" % rec["digest"])
            lines.append("")
            candidates.append((rid, rec, "\n".join(lines)))
        if not candidates:
            return []
        # Write the handover FIRST. Only once STATE.md actually has the words on
        # disk do we mutate record state and save the registry. If the write
        # fails, the records must stay active and unreported, or the context
        # they describe is gone with no signal that it ever existed.
        target = os.path.join(cwd or os.getcwd(), "STATE.md")
        # Delivered through the ONE handover primitive, the same one adopt()
        # uses. It is durable (fsync before returning) and idempotent per
        # lifecycle: if the append succeeded but the registry save below failed,
        # the retry finds its own tag and parks the records without writing the
        # handover a second time.
        # ALL OR NOTHING. Delivering per record fixed a duplicate-identity bug
        # and introduced a worse one: a record whose handover succeeded was
        # parked immediately, so when a sibling's delivery failed the registry
        # had it parked (fence RELEASED) while the mode file still showed it
        # active. Another thread could then claim its files while the dashboard
        # said it was running, and `off` reported that every record stayed
        # active, which was false.
        #
        # So deliver everything first and park nothing until all of it is on
        # disk. A retry is safe because each delivery carries its own tag and
        # recognises its earlier write.
        failures = [rid for rid, rec, body in candidates
                    if deliver_handover(target,
                                        "%s#%s" % (rid, (rec or {}).get("lifecycle", 1)),
                                        body, payload=record_payload(rec)) is False]
        if failures:
            print("bm_registry: warning: %s could not be delivered; NOTHING was "
                  "parked, every record stays ACTIVE and nothing is lost. Retry "
                  "absorb after fixing the target file."
                  % ", ".join(failures), file=sys.stderr)
            return []
        candidates = [(rid, rec) for rid, rec, body in candidates]
        out = []
        for rid, rec in candidates:
            rec["state"] = "parked"
            rec["parked_at"] = now()
            out.append((rid, rec.get("digest", "")))
        # The STATE.md append above already happened and cannot be rolled back:
        # there is no way to unwrite those lines from a plain text file. So if
        # the registry save below fails, we cannot undo the handover, only
        # report the mismatch. Leave the in-memory records parked is wrong too,
        # since disk still says active, so the caller must be told nothing was
        # absorbed: the records remain active on disk and a retry of absorb
        # after fixing permissions will duplicate this handover section.
        if not save(d, cwd):
            print("bm_registry: warning: handover was written to %s but the "
                  "registry state at %s could not be saved; records remain "
                  "ACTIVE on disk and a repeated absorb will duplicate this "
                  "handover section, fix the registry permissions before "
                  "retrying" % (target, registry_path(cwd)), file=sys.stderr)
            return []
        return out
    return with_lock(_do, cwd)


def render(cwd=None):
    """Write the generated human view of the registry. Never hand-edited: this
    file is regenerated from the structured registry, which is the source of
    truth."""
    def _do():
        d = load(cwd)
        lines = ["# Work registry (generated, do not hand-edit)",
                 "_rendered %s from %s_" % (now(), REGISTRY_FILE), ""]
        if not d.get("records"):
            lines.append("No records.")
        for rid in sorted(d.get("records", {})):
            r = d["records"][rid]
            # Defensive: skip records that are not dicts.
            if not isinstance(r, dict):
                continue
            lines.append("## %s  [%s, %s]" % (rid, r.get("state", "?"), r.get("lifetime", "?")))
            lines.append("- objective: %s" % r.get("objective", ""))
            # Defensive: a files field that is not a list, or that holds
            # non-string entries, renders as empty rather than raising here.
            lines.append("- files: %s" % files_line(r.get("files", [])))
            # An unreadable entry is dropped, not guessed at, so this record
            # guards fewer paths than it declared. Say so where a human looks.
            dropped = unguarded_count(r.get("files", []))
            if dropped:
                lines.append("- WARNING: %d declared file entry(s) unreadable and NOT guarded. "
                             "Another writer can be granted them. Fix this record's files field."
                             % dropped)
            if r.get("tier"):
                lines.append("- tier: %s" % r["tier"])
            sp = r.get("spend", {})
            if isinstance(sp, dict) and sp.get("output_tokens"):
                lines.append("- spend: %s output tokens across %s session(s)"
                             % (sp.get("output_tokens", 0), sp.get("sessions", 0)))
            # Defensive: treat decisions field as empty if not a list.
            decisions = r.get("decisions", [])
            if isinstance(decisions, list):
                for dec in decisions[-5:]:
                    # Defensive: skip decisions that are not dicts.
                    if isinstance(dec, dict):
                        lines.append("- decision [%s]: %s" % (dec.get("topic", ""), dec.get("text", "")))
            if r.get("digest"):
                # Defensive: a stored digest that is not a string cannot be
                # sliced, so coerce before truncating.
                lines.append("- next: %s" % safe_str(r["digest"])[:200])
            lines.append("")
        md = "\n".join(lines) + "\n"
        try:
            os.makedirs(registry_dir(cwd), exist_ok=True)
            atomic_write(os.path.join(registry_dir(cwd), VIEW_FILE), md)
        except OSError:
            pass
        return md
    return _do()
