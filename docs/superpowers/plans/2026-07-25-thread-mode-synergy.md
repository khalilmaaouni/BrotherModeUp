# Thread Mode and Core Unification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace BrotherMode's two half-registries (prose fences in `STATE.md`, JSON threads in `thread-mode.json`) with one structured work record, so overlap detection, decision clashes, and per-record spend become mechanical instead of remembered.

**Architecture:** A new `tools/bm_registry.py` owns the record type and the three hard operations (claim with overlap refusal, decide with clash detection, absorb for the lossless exit) plus a generated human view. `tools/bm_threads.py` becomes a thin client that keeps thread lifecycle and mailboxes but delegates registry work. `tools/bm_telemetry.py` gains one small function that attributes session spend to a record id. A new test enforces that every text-writing site in `tools/` has been reviewed for redaction.

**Tech Stack:** Python 3 standard library only (`json`, `os`, `re`, `fnmatch`, `posixpath`, `fcntl`, `datetime`, `unittest`). No third-party packages, no network, no subprocess inside the registry.

## Global Constraints

Copied verbatim from the spec; every task inherits these.

- Never block: a registry failure degrades to a printed warning; every path exits 0.
- Redact at the write: every text-bearing field passes through redaction before it touches disk, inside the registry, so no caller can forget.
- Lock every read-modify-write: file locking around registry mutation, with the active-record cap re-checked inside the lock.
- Lossless exit: digests stay current, so `absorb` never requires the thread to still be alive.
- Two modes: overlap refusal is advisory locally and strict in CI.
- Versioned schema: the record carries a schema version so a later change migrates rather than breaks.
- No em dashes or en dashes in any code comment, docstring, commit message, or document.
- Threads only: ephemeral agent fences are NOT migrated in this plan. Named review date 2026-08-08.
- Test command for every task: `python3 tools/test_bm.py` run from the repository root.
- All work happens in `~/Documents/brothermode-public`. The private copy at `~/.claude/skills/brothermode` is synced in Task 8, never edited directly before then.

---

### Task 1: Registry storage with schema, locking, and redaction

**Files:**
- Create: `tools/bm_registry.py`
- Test: `tools/test_bm.py` (append a new test class)

**Interfaces:**
- Consumes: `tools/bm_telemetry.py::redact(text) -> (clean_text, count)`
- Produces:
  - `SCHEMA = 1`
  - `registry_path(cwd=None) -> str`
  - `load(cwd=None) -> dict` shaped `{"schema": 1, "records": {}}`
  - `save(d, cwd=None) -> bool`
  - `with_lock(fn, cwd=None) -> any` (runs `fn()` holding an exclusive lock)
  - `redact_text(t) -> str`
  - `new_record(rid, lifetime, objective, files, tier=None, owner=None, ttl_days=2) -> dict`

- [ ] **Step 1: Write the failing test**

Append to `tools/test_bm.py`, immediately before the line `if __name__ == "__main__":`

```python
import importlib.util as _ilu
_rspec = _ilu.spec_from_file_location("bm_registry", os.path.join(HERE, "bm_registry.py"))
_reg = _ilu.module_from_spec(_rspec)


def load_registry_module():
    """Import bm_registry fresh so it picks up the current env vars."""
    _rspec.loader.exec_module(_reg)
    return _reg


class TestRegistryStorage(unittest.TestCase):
    def test_new_record_shape_and_redaction(self):
        reg = load_registry_module()
        r = reg.new_record("payments", "persistent",
                           "build payments, the prod password is hunter2",
                           ["api/pay.py"], tier="T2", owner="sess-1")
        self.assertEqual(r["schema"], reg.SCHEMA)
        self.assertEqual(r["lifetime"], "persistent")
        self.assertEqual(r["state"], "active")
        self.assertEqual(r["files"], ["api/pay.py"])
        self.assertNotIn("hunter2", r["objective"], "objective was not redacted")
        self.assertIn("[REDACTED]", r["objective"])
        for key in ("decisions", "digest", "spend", "lease", "check", "evidence"):
            self.assertIn(key, r, "record is missing field: %s" % key)

    def test_save_and_load_roundtrip(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            data = {"schema": reg.SCHEMA, "records": {"a": reg.new_record(
                "a", "persistent", "obj", ["x.py"])}}
            self.assertTrue(reg.save(data, cwd=d))
            back = reg.load(cwd=d)
            self.assertEqual(back["records"]["a"]["objective"], "obj")

    def test_load_missing_file_returns_empty_registry(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            back = reg.load(cwd=d)
            self.assertEqual(back["schema"], reg.SCHEMA)
            self.assertEqual(back["records"], {})

    def test_unknown_fields_and_newer_schema_do_not_crash(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            path = reg.registry_path(cwd=d)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            io.open(path, "w").write(json.dumps(
                {"schema": 99, "records": {"a": {"id": "a", "mystery": 1}}}))
            back = reg.load(cwd=d)
            self.assertIn("a", back["records"], "forward compatibility broken")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 tools/test_bm.py TestRegistryStorage -v`
Expected: FAIL with `FileNotFoundError` or `ModuleNotFoundError` for `bm_registry.py`

- [ ] **Step 3: Write minimal implementation**

Create `tools/bm_registry.py`:

```python
#!/usr/bin/env python3
"""BrotherMode work registry: one record for every unit of claimed work.

A thread is a record with lifetime "persistent". A fence is the same record with
lifetime "ephemeral". Nothing else differs, which is the point: one source of
truth for who owns what work, so the two registries can no longer disagree.

Pure file I/O. No network, no subprocess. Every text field is redacted at the
write, so no caller can forget. Every path returns rather than raises.
"""
import io, json, os, re, sys, fnmatch, posixpath, datetime

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
    except Exception:
        pass
    pats = [
        re.compile(r"\b(sk|rk)[-_][A-Za-z0-9_-]{12,}", re.I),
        re.compile(r"\bgh[oprsu]_[A-Za-z0-9]{16,}"),
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        re.compile(r"\b[Bb]earer\s+[A-Za-z0-9._~+/=-]{16,}"),
        re.compile(r"-----BEGIN[ A-Z]*PRIVATE KEY-----"),
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
    """Read the registry. A missing or unreadable file is an empty registry, and
    an unknown schema or unknown fields are preserved rather than dropped."""
    try:
        raw = io.open(registry_path(cwd), encoding="utf-8", errors="replace").read()
        d = json.loads(raw or "{}")
    except (OSError, ValueError):
        d = {}
    if not isinstance(d, dict):
        d = {}
    d.setdefault("schema", SCHEMA)
    d.setdefault("records", {})
    if not isinstance(d["records"], dict):
        d["records"] = {}
    return d


def save(d, cwd=None):
    try:
        os.makedirs(registry_dir(cwd), exist_ok=True)
        with io.open(registry_path(cwd), "w", encoding="utf-8") as f:
            f.write(json.dumps(d, indent=2, sort_keys=True) + "\n")
        return True
    except OSError:
        return False


def with_lock(fn, cwd=None):
    """Exclusive lock around any read-modify-write. Without it, two concurrent
    claims each read the old registry and the second write wins, losing a record:
    invisible to the dashboard and skipped by absorb, which silently loses work."""
    try:
        os.makedirs(registry_dir(cwd), exist_ok=True)
    except OSError:
        return fn()
    fh = None
    try:
        fh = open(os.path.join(registry_dir(cwd), ".registry.lock"), "w")
        try:
            import fcntl
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        except Exception:
            pass
        return fn()
    finally:
        if fh is not None:
            try:
                import fcntl
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
            fh.close()


def new_record(rid, lifetime, objective, files, tier=None, owner=None, ttl_days=2):
    """Build a work record. lifetime is "persistent" (a thread) or "ephemeral"
    (an agent dispatch); every other field is identical between the two."""
    return {
        "schema": SCHEMA,
        "id": rid,
        "lifetime": lifetime,
        "owner": owner or "",
        "objective": redact_text(objective),
        "files": list(files or []),
        "tier": tier or "",
        "lease": {"claimed_at": now(), "ttl_days": ttl_days},
        "state": "active",
        "check": "",
        "evidence": "",
        "decisions": [],
        "digest": "",
        "spend": {"output_tokens": 0, "sessions": 0},
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 tools/test_bm.py TestRegistryStorage -v`
Expected: PASS, 4 tests

- [ ] **Step 5: Commit**

```bash
git add tools/bm_registry.py tools/test_bm.py
git commit -m "Registry: record schema, locked storage, redaction at the write"
```

---

### Task 2: Overlap detection and claim refusal

**Files:**
- Modify: `tools/bm_registry.py` (append functions)
- Test: `tools/test_bm.py` (append a new test class)

**Interfaces:**
- Consumes: `load`, `save`, `with_lock`, `new_record` from Task 1
- Produces:
  - `paths_overlap(a_files, b_files) -> list[tuple[str, str]]` (empty list means disjoint)
  - `claim(rid, lifetime, objective, files, tier=None, owner=None, cwd=None) -> (bool, dict|None)` where the second element is the conflicting record when refused

- [ ] **Step 1: Write the failing test**

Append to `tools/test_bm.py` before `if __name__ == "__main__":`

```python
class TestRegistryOverlap(unittest.TestCase):
    def test_overlap_table(self):
        reg = load_registry_module()
        cases = [
            (["api/pay.py"], ["api/pay.py"], True, "identical path"),
            (["api/pay.py"], ["api/ship.py"], False, "different files"),
            (["api/"], ["api/pay.py"], True, "directory contains file"),
            (["api/**"], ["api/hooks/x.py"], True, "recursive glob"),
            (["api/*.py"], ["api/pay.py"], True, "single-level glob"),
            (["api/*.py"], ["web/pay.py"], False, "glob in another directory"),
            (["docs/a.md"], ["docs/b.md"], False, "siblings"),
            (["./api/pay.py"], ["api/pay.py"], True, "normalized dot prefix"),
        ]
        for a, b, expected, label in cases:
            got = bool(reg.paths_overlap(a, b))
            self.assertEqual(got, expected, "%s: %s vs %s" % (label, a, b))

    def test_claim_grants_then_refuses_conflict(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            ok, conflict = reg.claim("payments", "persistent", "pay",
                                     ["api/pay.py"], cwd=d)
            self.assertTrue(ok)
            self.assertIsNone(conflict)
            ok2, conflict2 = reg.claim("billing", "persistent", "bill",
                                       ["api/pay.py"], cwd=d)
            self.assertFalse(ok2, "a colliding claim must be refused")
            self.assertIsNotNone(conflict2)
            self.assertEqual(conflict2["id"], "payments",
                             "refusal must name the conflicting record")

    def test_claim_allows_disjoint_and_ignores_parked(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            reg.claim("a", "persistent", "a", ["api/a.py"], cwd=d)
            ok, _ = reg.claim("b", "persistent", "b", ["api/b.py"], cwd=d)
            self.assertTrue(ok, "disjoint claims must both be granted")
            data = reg.load(cwd=d)
            data["records"]["a"]["state"] = "parked"
            reg.save(data, cwd=d)
            ok2, _ = reg.claim("c", "persistent", "c", ["api/a.py"], cwd=d)
            self.assertTrue(ok2, "a parked record must not block a new claim")

    def test_reclaim_by_same_id_is_allowed(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            reg.claim("a", "persistent", "a", ["api/a.py"], cwd=d)
            ok, _ = reg.claim("a", "persistent", "a again", ["api/a.py"], cwd=d)
            self.assertTrue(ok, "a record must be able to reclaim its own files")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 tools/test_bm.py TestRegistryOverlap -v`
Expected: FAIL with `AttributeError: module 'bm_registry' has no attribute 'paths_overlap'`

- [ ] **Step 3: Write minimal implementation**

Append to `tools/bm_registry.py`:

```python
def _norm(p):
    """Normalize a declared path for comparison: posix separators, no leading
    ./, no trailing slash. A trailing slash is remembered by _is_dir_decl."""
    p = (p or "").strip().replace("\\", "/")
    p = posixpath.normpath(p)
    return "" if p == "." else p


def _is_dir_decl(p):
    return (p or "").strip().endswith("/")


def _one_overlaps(a, b):
    """True when two declared paths can touch the same file."""
    a_dir, b_dir = _is_dir_decl(a), _is_dir_decl(b)
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    # A directory declaration covers everything beneath it.
    if a_dir and (nb == na or nb.startswith(na + "/")):
        return True
    if b_dir and (na == nb or na.startswith(nb + "/")):
        return True
    # Glob on either side. ** is expanded to match across separators.
    for pat, other in ((na, nb), (nb, na)):
        if any(ch in pat for ch in "*?["):
            if fnmatch.fnmatch(other, pat):
                return True
            if "**" in pat and fnmatch.fnmatch(other, pat.replace("**", "*")):
                return True
            if fnmatch.fnmatch(other, pat.rstrip("/") + "/*"):
                return True
    return False


def paths_overlap(a_files, b_files):
    """Return every conflicting pair between two file lists. Empty means disjoint."""
    hits = []
    for a in (a_files or []):
        for b in (b_files or []):
            if _one_overlaps(a, b):
                hits.append((a, b))
    return hits


def claim(rid, lifetime, objective, files, tier=None, owner=None, cwd=None):
    """Register work. Refuses when the declared files overlap another ACTIVE
    record, returning that record so the caller can name it. Reclaiming under
    the same id is allowed, because that is the same owner re-declaring."""
    def _do():
        d = load(cwd)
        for other_id, rec in d["records"].items():
            if other_id == rid or rec.get("state") != "active":
                continue
            if paths_overlap(files, rec.get("files")):
                return (False, rec)
        rec = d["records"].get(rid)
        if rec:
            rec["objective"] = redact_text(objective)
            rec["files"] = list(files or [])
            rec["state"] = "active"
            if tier:
                rec["tier"] = tier
        else:
            d["records"][rid] = new_record(rid, lifetime, objective, files, tier, owner)
        save(d, cwd)
        return (True, None)
    return with_lock(_do, cwd)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 tools/test_bm.py TestRegistryOverlap -v`
Expected: PASS, 4 tests

- [ ] **Step 5: Commit**

```bash
git add tools/bm_registry.py tools/test_bm.py
git commit -m "Registry: mechanical path-overlap detection and claim refusal"
```

---

### Task 3: Tagged decisions and clash detection

**Files:**
- Modify: `tools/bm_registry.py` (append functions)
- Test: `tools/test_bm.py` (append a new test class)

**Interfaces:**
- Consumes: `load`, `save`, `with_lock`, `redact_text` from Task 1
- Produces:
  - `decide(rid, topic, text, cwd=None) -> (bool, dict|None)` where the second element is `{"record": other_id, "topic": t, "text": prior_text}` when a clash is found
  - `set_digest(rid, text, cwd=None) -> bool`

- [ ] **Step 1: Write the failing test**

Append to `tools/test_bm.py` before `if __name__ == "__main__":`

```python
class TestRegistryClash(unittest.TestCase):
    def _two_records(self, reg, d):
        reg.claim("payments", "persistent", "pay", ["api/pay.py"], cwd=d)
        reg.claim("billing", "persistent", "bill", ["api/bill.py"], cwd=d)

    def test_same_topic_in_another_record_clashes(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            self._two_records(reg, d)
            ok, clash = reg.decide("payments", "payments-api", "use Stripe", cwd=d)
            self.assertTrue(ok)
            self.assertIsNone(clash)
            ok2, clash2 = reg.decide("billing", "payments-api", "use Adyen", cwd=d)
            self.assertIsNotNone(clash2, "a second record deciding the same topic must clash")
            self.assertEqual(clash2["record"], "payments")
            self.assertIn("Stripe", clash2["text"], "the clash must show the prior decision")

    def test_different_topics_stay_silent(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            self._two_records(reg, d)
            reg.decide("payments", "payments-api", "use Stripe", cwd=d)
            ok, clash = reg.decide("billing", "invoice-format", "use PDF", cwd=d)
            self.assertTrue(ok)
            self.assertIsNone(clash, "unrelated topics must not clash")

    def test_record_revising_its_own_topic_does_not_self_clash(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            self._two_records(reg, d)
            reg.decide("payments", "payments-api", "use Stripe", cwd=d)
            ok, clash = reg.decide("payments", "payments-api", "use Stripe Connect", cwd=d)
            self.assertTrue(ok)
            self.assertIsNone(clash, "a record must be free to revise its own decision")

    def test_topic_matching_ignores_case_and_spacing(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            self._two_records(reg, d)
            reg.decide("payments", "Payments API", "use Stripe", cwd=d)
            _, clash = reg.decide("billing", "payments-api", "use Adyen", cwd=d)
            self.assertIsNotNone(clash, "topic matching must normalize case and separators")

    def test_decision_and_digest_are_redacted(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            reg.claim("payments", "persistent", "pay", ["api/pay.py"], cwd=d)
            reg.decide("payments", "creds", "the prod password is hunter2", cwd=d)
            reg.set_digest("payments", "digest with token sk-ant-api03-ABCDEFGHIJKLMNOP", cwd=d)
            blob = io.open(reg.registry_path(cwd=d)).read()
            self.assertNotIn("hunter2", blob, "decision leaked a secret into the registry")
            self.assertNotIn("sk-ant-api03-ABCDEFGHIJKLMNOP", blob, "digest leaked a secret")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 tools/test_bm.py TestRegistryClash -v`
Expected: FAIL with `AttributeError: module 'bm_registry' has no attribute 'decide'`

- [ ] **Step 3: Write minimal implementation**

Append to `tools/bm_registry.py`:

```python
def _topic_key(t):
    """Normalize a topic so "Payments API", "payments-api" and "payments_api"
    are the same topic. Matching is deliberately literal: this catches two
    records deciding the same NAMED topic, and does not attempt to understand
    that two differently named topics are semantically incompatible."""
    return re.sub(r"[^a-z0-9]+", "-", (t or "").strip().lower()).strip("-")


def decide(rid, topic, text, cwd=None):
    """Record a tagged decision. Returns (True, clash_or_None). The decision is
    always recorded, even on a clash: the point is to surface the contradiction
    to the chief, not to silently drop a thread's decision."""
    def _do():
        d = load(cwd)
        rec = d["records"].get(rid)
        if rec is None:
            return (False, None)
        key = _topic_key(topic)
        clash = None
        for other_id, other in d["records"].items():
            if other_id == rid or other.get("state") != "active":
                continue
            for dec in other.get("decisions", []):
                if _topic_key(dec.get("topic")) == key:
                    clash = {"record": other_id, "topic": dec.get("topic"),
                             "text": dec.get("text")}
                    break
            if clash:
                break
        rec.setdefault("decisions", []).append(
            {"topic": redact_text(topic), "text": redact_text(text), "ts": now()})
        save(d, cwd)
        return (True, clash)
    return with_lock(_do, cwd)


def set_digest(rid, text, cwd=None):
    """Replace a record's handover digest. Kept current as work proceeds so the
    lossless exit never needs the thread to still be alive."""
    def _do():
        d = load(cwd)
        rec = d["records"].get(rid)
        if rec is None:
            return False
        rec["digest"] = redact_text(text)[:DIGEST_CAP]
        save(d, cwd)
        return True
    return with_lock(_do, cwd)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 tools/test_bm.py TestRegistryClash -v`
Expected: PASS, 5 tests

- [ ] **Step 5: Commit**

```bash
git add tools/bm_registry.py tools/test_bm.py
git commit -m "Registry: tagged decisions with mechanical clash detection"
```

---

### Task 4: Absorb for the lossless exit, and the rendered human view

**Files:**
- Modify: `tools/bm_registry.py` (append functions)
- Test: `tools/test_bm.py` (append a new test class)

**Interfaces:**
- Consumes: `load`, `save`, `with_lock` from Task 1
- Produces:
  - `absorb(cwd=None) -> list[tuple[str, str]]` list of `(record_id, digest)` and appends them to `<cwd>/STATE.md`, marking each active record `parked`
  - `render(cwd=None) -> str` writes `threads/REGISTRY.md` and returns the markdown

- [ ] **Step 1: Write the failing test**

Append to `tools/test_bm.py` before `if __name__ == "__main__":`

```python
class TestRegistryAbsorbAndView(unittest.TestCase):
    def test_absorb_is_lossless_and_parks(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            io.open(os.path.join(d, "STATE.md"), "w").write("# Project STATE\n")
            reg.claim("payments", "persistent", "pay", ["api/pay.py"], cwd=d)
            reg.decide("payments", "payments-api", "chose Stripe", cwd=d)
            reg.set_digest("payments", "next: wire the webhook handler", cwd=d)
            absorbed = reg.absorb(cwd=d)
            self.assertEqual([a[0] for a in absorbed], ["payments"])
            state = io.open(os.path.join(d, "STATE.md")).read()
            self.assertIn("wire the webhook handler", state, "digest was not absorbed")
            self.assertIn("chose Stripe", state, "decisions were not absorbed")
            data = reg.load(cwd=d)
            self.assertEqual(data["records"]["payments"]["state"], "parked")

    def test_absorb_creates_state_file_when_missing(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            reg.claim("a", "persistent", "a", ["x.py"], cwd=d)
            reg.set_digest("a", "important next step", cwd=d)
            reg.absorb(cwd=d)
            self.assertTrue(os.path.exists(os.path.join(d, "STATE.md")),
                            "absorb must not drop context when STATE.md is absent")
            self.assertIn("important next step",
                          io.open(os.path.join(d, "STATE.md")).read())

    def test_render_writes_human_view(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            reg.claim("payments", "persistent", "build payments",
                      ["api/pay.py"], tier="T2", cwd=d)
            md = reg.render(cwd=d)
            view = os.path.join(d, "threads", "REGISTRY.md")
            self.assertTrue(os.path.exists(view), "REGISTRY.md was not written")
            body = io.open(view).read()
            self.assertIn("payments", body)
            self.assertIn("api/pay.py", body)
            self.assertIn("generated", body.lower(),
                          "the view must say it is generated, never hand-edited")
            self.assertEqual(md, body)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 tools/test_bm.py TestRegistryAbsorbAndView -v`
Expected: FAIL with `AttributeError: module 'bm_registry' has no attribute 'absorb'`

- [ ] **Step 3: Write minimal implementation**

Append to `tools/bm_registry.py`:

```python
def absorb(cwd=None):
    """Drain every active record's digest and decisions into the project's
    STATE.md and park the records. Nothing is deleted, so a parked record can be
    resumed. This is the lossless exit: it works from disk alone and never needs
    the owning session to still be alive."""
    def _do():
        d = load(cwd)
        out, lines = [], []
        lines.append("")
        lines.append("## Registry handover (absorbed %s)" % now())
        lines.append("Work records were drained and parked. Nothing was deleted; each")
        lines.append("record below can be resumed. Continue from these without re-exploring.")
        lines.append("")
        for rid in sorted(d["records"]):
            rec = d["records"][rid]
            if rec.get("state") != "active":
                continue
            lines.append("### Record: %s (%s)" % (rid, rec.get("lifetime", "?")))
            lines.append("- objective: %s" % rec.get("objective", ""))
            lines.append("- files: %s" % ", ".join(rec.get("files", []) or ["(none)"]))
            for dec in rec.get("decisions", []):
                lines.append("- decision [%s]: %s" % (dec.get("topic", ""), dec.get("text", "")))
            if rec.get("digest"):
                lines.append("- digest: %s" % rec["digest"])
            lines.append("")
            out.append((rid, rec.get("digest", "")))
            rec["state"] = "parked"
            rec["parked_at"] = now()
        if out:
            target = os.path.join(cwd or os.getcwd(), "STATE.md")
            try:
                with io.open(target, "a", encoding="utf-8") as f:
                    f.write("\n".join(lines) + "\n")
            except OSError:
                pass
            save(d, cwd)
        return out
    return with_lock(_do, cwd)


def render(cwd=None):
    """Write the generated human view of the registry. Never hand-edited: this
    file is regenerated from the structured registry, which is the source of
    truth."""
    d = load(cwd)
    lines = ["# Work registry (generated, do not hand-edit)",
             "_rendered %s from %s_" % (now(), REGISTRY_FILE), ""]
    if not d["records"]:
        lines.append("No records.")
    for rid in sorted(d["records"]):
        r = d["records"][rid]
        lines.append("## %s  [%s, %s]" % (rid, r.get("state", "?"), r.get("lifetime", "?")))
        lines.append("- objective: %s" % r.get("objective", ""))
        lines.append("- files: %s" % ", ".join(r.get("files", []) or ["(none)"]))
        if r.get("tier"):
            lines.append("- tier: %s" % r["tier"])
        sp = r.get("spend", {})
        if sp.get("output_tokens"):
            lines.append("- spend: %s output tokens across %s session(s)"
                         % (sp.get("output_tokens", 0), sp.get("sessions", 0)))
        for dec in r.get("decisions", [])[-5:]:
            lines.append("- decision [%s]: %s" % (dec.get("topic", ""), dec.get("text", "")))
        if r.get("digest"):
            lines.append("- next: %s" % r["digest"][:200])
        lines.append("")
    md = "\n".join(lines) + "\n"
    try:
        os.makedirs(registry_dir(cwd), exist_ok=True)
        with io.open(os.path.join(registry_dir(cwd), VIEW_FILE), "w", encoding="utf-8") as f:
            f.write(md)
    except OSError:
        pass
    return md
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 tools/test_bm.py TestRegistryAbsorbAndView -v`
Expected: PASS, 3 tests

- [ ] **Step 5: Commit**

```bash
git add tools/bm_registry.py tools/test_bm.py
git commit -m "Registry: lossless absorb and the generated human view"
```

---

### Task 5: Concurrency proof for the registry

**Files:**
- Test: `tools/test_bm.py` (append a new test class)

**Interfaces:**
- Consumes: `claim` from Task 2
- Produces: nothing new; this task proves an existing guarantee

This task exists because the identical defect already shipped once in `bm_threads.py`: concurrent registrations were lost, which would have made `absorb` skip records and silently lose work.

- [ ] **Step 1: Write the failing test**

Append to `tools/test_bm.py` before `if __name__ == "__main__":`

```python
class TestRegistryConcurrency(unittest.TestCase):
    def test_parallel_disjoint_claims_all_register(self):
        reg = load_registry_module()
        import threading as _th
        with tempfile.TemporaryDirectory() as d:
            def claim(n):
                reg.claim(n, "persistent", "obj " + n, ["api/%s.py" % n], cwd=d)
            ts = [_th.Thread(target=claim, args=(n,)) for n in ("a", "b", "c", "dee", "e")]
            [t.start() for t in ts]
            [t.join() for t in ts]
            data = reg.load(cwd=d)
            self.assertEqual(sorted(data["records"]), ["a", "b", "c", "dee", "e"],
                             "a concurrent claim was lost from the registry")

    def test_parallel_conflicting_claims_only_one_wins(self):
        reg = load_registry_module()
        import threading as _th
        with tempfile.TemporaryDirectory() as d:
            results = []
            def claim(n):
                ok, _ = reg.claim(n, "persistent", "obj", ["api/shared.py"], cwd=d)
                results.append(ok)
            ts = [_th.Thread(target=claim, args=(n,)) for n in ("a", "b", "c")]
            [t.start() for t in ts]
            [t.join() for t in ts]
            self.assertEqual(sum(1 for r in results if r), 1,
                             "exactly one claim on the same file may be granted")
```

- [ ] **Step 2: Run test to verify it fails or passes**

Run: `python3 tools/test_bm.py TestRegistryConcurrency -v`
Expected: PASS if Task 1's lock is correct. If it FAILS, the lock is wrong and must be fixed before continuing; do not weaken the test.

- [ ] **Step 3: Fix only if failing**

If the second test fails, the read and the write are not both inside the lock. Confirm that `claim`'s inner `_do` calls `load` INSIDE the function passed to `with_lock`, never before it.

- [ ] **Step 4: Run the whole suite**

Run: `python3 tools/test_bm.py`
Expected: PASS, all tests

- [ ] **Step 5: Commit**

```bash
git add tools/test_bm.py
git commit -m "Registry: concurrency tests for lost claims and conflicting claims"
```

---

### Task 6: bm_threads delegates to the registry

**Files:**
- Modify: `tools/bm_threads.py:238-283` (`cmd_start`), `tools/bm_threads.py:284-331` (`cmd_checkpoint`), `tools/bm_threads.py:376-414` (`cmd_off`), `tools/bm_threads.py:347-375` (`cmd_dashboard`)
- Test: `tools/test_bm.py` (append a new test class)

**Interfaces:**
- Consumes: `claim`, `decide`, `set_digest`, `absorb`, `render` from Tasks 2 to 4
- Produces: no new public functions; existing commands gain registry behavior

Thread mode keeps its mailboxes and lifecycle. It stops owning overlap, clash, and absorb logic.

- [ ] **Step 1: Write the failing test**

Append to `tools/test_bm.py` before `if __name__ == "__main__":`

```python
class TestThreadsUseRegistry(unittest.TestCase):
    def _run(self, cwd, *a):
        return subprocess.run([sys.executable, os.path.join(HERE, "bm_threads.py"), *a],
                              cwd=cwd, capture_output=True, text=True)

    def test_start_registers_a_record_with_files(self):
        with tempfile.TemporaryDirectory() as d:
            io.open(os.path.join(d, "STATE.md"), "w").write("# S\n")
            self._run(d, "on")
            self._run(d, "start", "payments", "build payments", "--files", "api/pay.py")
            reg = json.load(io.open(os.path.join(d, "threads", "registry.json")))
            self.assertIn("payments", reg["records"], "start did not create a work record")
            self.assertEqual(reg["records"]["payments"]["files"], ["api/pay.py"])

    def test_start_refuses_an_overlapping_thread(self):
        with tempfile.TemporaryDirectory() as d:
            io.open(os.path.join(d, "STATE.md"), "w").write("# S\n")
            self._run(d, "on")
            self._run(d, "start", "payments", "pay", "--files", "api/pay.py")
            r = self._run(d, "start", "billing", "bill", "--files", "api/pay.py")
            self.assertIn("OVERLAP", r.stdout.upper(),
                          "an overlapping thread must be refused and say so")
            self.assertIn("payments", r.stdout, "the refusal must name the conflicting record")

    def test_checkpoint_topic_clash_is_reported(self):
        with tempfile.TemporaryDirectory() as d:
            io.open(os.path.join(d, "STATE.md"), "w").write("# S\n")
            self._run(d, "on")
            self._run(d, "start", "payments", "pay", "--files", "api/pay.py")
            self._run(d, "start", "billing", "bill", "--files", "api/bill.py")
            self._run(d, "checkpoint", "payments", "--topic", "payments-api",
                      "--decision", "use Stripe")
            r = self._run(d, "checkpoint", "billing", "--topic", "payments-api",
                          "--decision", "use Adyen")
            self.assertIn("CLASH", r.stdout.upper(), "a cross-thread clash must be reported")
            self.assertIn("payments", r.stdout)

    def test_off_absorbs_through_the_registry(self):
        with tempfile.TemporaryDirectory() as d:
            io.open(os.path.join(d, "STATE.md"), "w").write("# S\n")
            self._run(d, "on")
            self._run(d, "start", "payments", "pay", "--files", "api/pay.py")
            self._run(d, "checkpoint", "payments", "--topic", "api",
                      "--decision", "chose Stripe", "--next", "wire webhook")
            self._run(d, "off")
            state = io.open(os.path.join(d, "STATE.md")).read()
            self.assertIn("chose Stripe", state)
            self.assertIn("wire webhook", state)
            reg = json.load(io.open(os.path.join(d, "threads", "registry.json")))
            self.assertEqual(reg["records"]["payments"]["state"], "parked")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 tools/test_bm.py TestThreadsUseRegistry -v`
Expected: FAIL, because `start` does not accept `--files` and writes no `registry.json`

- [ ] **Step 3: Write the implementation**

In `tools/bm_threads.py`, add this import block immediately after the existing `import io, json, os, re, sys, datetime` line:

```python
def _registry():
    """Load the registry module by path so bm_threads works from any cwd."""
    import importlib.util
    here = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location(
        "bm_registry_for_threads", os.path.join(here, "bm_registry.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
```

In `cmd_start`, parse a `--files` list and claim before creating any files. Replace the body between the cap check and the `write(os.path.join(base, "STATE.md"), ...)` call with:

```python
    files = []
    if "--files" in argv:
        i = argv.index("--files")
        files = [a for a in argv[i + 1:] if not a.startswith("--")]
        objective = " ".join(argv[1:i]).strip() or "(objective not stated)"
    reg = _registry()
    ok, conflict = reg.claim(name, "persistent", objective, files, tier="T2")
    if not ok:
        print("OVERLAP: '%s' declares files already claimed by record '%s' (%s)."
              % (name, conflict.get("id"), ", ".join(conflict.get("files", []))))
        print("  Park or narrow that record first; two writers on one file is the "
              "one thing the single-writer law forbids.")
        return
```

In `cmd_checkpoint`, after computing `dec` and before writing the digest, add:

```python
    topic = ""
    if "--topic" in argv:
        ti = argv.index("--topic")
        topic = argv[ti + 1] if len(argv) > ti + 1 else ""
    if dec and topic:
        reg = _registry()
        _, clash = reg.decide(name, topic, dec)
        if clash:
            print("CLASH on topic '%s': record '%s' already decided: %s"
                  % (topic, clash["record"], clash["text"]))
            print("  Both decisions are recorded. Reconcile before building further.")
```

At the end of `cmd_checkpoint`, after the digest file is written, mirror it into the registry:

```python
    _registry().set_digest(name, "\n".join(body)[:DIGEST_CAP])
```

In `cmd_off`, replace the digest-collection loop with a call to the registry, keeping the existing printed summary:

```python
    absorbed = [rid for rid, _ in _registry().absorb()]
```

In `cmd_dashboard`, after printing the threads, add:

```python
    _registry().render()
    print("\n  generated view: %s/REGISTRY.md" % THREADS_DIRNAME)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 tools/test_bm.py TestThreadsUseRegistry -v`
Then: `python3 tools/test_bm.py`
Expected: PASS, all tests including the pre-existing thread tests

- [ ] **Step 5: Commit**

```bash
git add tools/bm_threads.py tools/test_bm.py
git commit -m "Threads: delegate claim, decide, absorb, and render to the registry"
```

---

### Task 7: Attribute session spend to a record

**Files:**
- Modify: `tools/bm_telemetry.py` (append one function and one dispatch line)
- Test: `tools/test_bm.py` (append a new test class)

**Interfaces:**
- Consumes: `load`, `save`, `with_lock` from Task 1
- Produces: `bm_telemetry.py` subcommand `attribute <record_id> <output_tokens>`

This is what gives the revert gate its numbers.

- [ ] **Step 1: Write the failing test**

Append to `tools/test_bm.py` before `if __name__ == "__main__":`

```python
class TestSpendAttribution(unittest.TestCase):
    def test_attribute_accumulates_spend_on_the_record(self):
        reg = load_registry_module()
        with tempfile.TemporaryDirectory() as d:
            reg.claim("payments", "persistent", "pay", ["api/pay.py"], cwd=d)
            for tokens in ("1500", "2500"):
                subprocess.run([sys.executable, os.path.join(HERE, "bm_telemetry.py"),
                                "attribute", "payments", tokens],
                               cwd=d, capture_output=True, text=True)
            data = reg.load(cwd=d)
            spend = data["records"]["payments"]["spend"]
            self.assertEqual(spend["output_tokens"], 4000)
            self.assertEqual(spend["sessions"], 2)

    def test_attribute_on_unknown_record_is_silent_and_exits_zero(self):
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run([sys.executable, os.path.join(HERE, "bm_telemetry.py"),
                                "attribute", "ghost", "100"],
                               cwd=d, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, "telemetry must never block work")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 tools/test_bm.py TestSpendAttribution -v`
Expected: FAIL, spend stays at 0 because the subcommand does not exist

- [ ] **Step 3: Write minimal implementation**

Append to `tools/bm_telemetry.py`, immediately before `def main():`

```python
def cmd_attribute(argv):
    """Attribute a session's output tokens to a work record, so per-record spend
    can be compared against the pre-thread baseline. Pure file I/O through the
    registry module; this function adds no network and no subprocess."""
    if len(argv) < 2:
        print("usage: attribute <record_id> <output_tokens>")
        return
    rid = argv[0]
    try:
        tokens = int(argv[1])
    except ValueError:
        print("attribute: token count must be an integer")
        return
    try:
        import importlib.util
        here = os.path.dirname(os.path.abspath(__file__))
        spec = importlib.util.spec_from_file_location(
            "bm_registry_for_telemetry", os.path.join(here, "bm_registry.py"))
        reg = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(reg)
    except Exception:
        return

    def _do():
        d = reg.load()
        rec = d["records"].get(rid)
        if rec is None:
            return False
        sp = rec.setdefault("spend", {"output_tokens": 0, "sessions": 0})
        sp["output_tokens"] = sp.get("output_tokens", 0) + tokens
        sp["sessions"] = sp.get("sessions", 0) + 1
        reg.save(d)
        return True
    if reg.with_lock(_do):
        print("attributed %d output tokens to record '%s'" % (tokens, rid))
```

In `main()`, add this branch immediately before the `elif cmd == "purge-corrections":` line:

```python
        elif cmd == "attribute":
            cmd_attribute(argv)
```

Add to the module docstring, immediately before the `purge-corrections` line:

```
  attribute         Adds a session's output tokens to a work record's spend, so
                    per-record cost can be compared against the baseline.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 tools/test_bm.py TestSpendAttribution -v`
Expected: PASS, 2 tests

- [ ] **Step 5: Commit**

```bash
git add tools/bm_telemetry.py tools/test_bm.py
git commit -m "Telemetry: attribute session spend to a work record"
```

---

### Task 8: The pre-write redaction gate, and sync to the private skill

**Files:**
- Create: `tools/write_sites.json`
- Test: `tools/test_bm.py` (append a new test class)
- Modify: `~/.claude/skills/brothermode/tools/` (copy of the four tool files)

**Interfaces:**
- Consumes: nothing
- Produces: a CI-enforced inventory of every text-writing site in `tools/`

Be honest about what this is: it is a review-forcing inventory, not dataflow proof. It cannot know whether a given write carries user text. It CAN guarantee that a new write site is never added without a human deciding whether it needs redaction, which is exactly the gap that let the same secret-leak bug ship three times.

- [ ] **Step 1: Write the failing test**

Append to `tools/test_bm.py` before `if __name__ == "__main__":`

```python
class TestPreWriteGate(unittest.TestCase):
    """Every place in tools/ that writes a file must be a REVIEWED place.

    This does not prove redaction. It proves that a NEW write site cannot appear
    without someone deciding whether it needs redaction, which is the gap that
    let the same secret-leak bug ship three times in one week.
    """
    WRITE_PATTERNS = (r'open\([^)]*["\']w["\']', r'os\.open\(', r'\.write\(')

    def _sites(self):
        found = {}
        for fn in sorted(os.listdir(HERE)):
            if not fn.endswith(".py") or fn.startswith("test_"):
                continue
            src = io.open(os.path.join(HERE, fn), encoding="utf-8").read().splitlines()
            hits = []
            for i, line in enumerate(src, 1):
                if line.strip().startswith("#"):
                    continue
                for pat in self.WRITE_PATTERNS:
                    if re.search(pat, line):
                        hits.append(i)
                        break
            if hits:
                found[fn] = len(hits)
        return found

    def test_no_unreviewed_write_sites(self):
        manifest_path = os.path.join(HERE, "write_sites.json")
        self.assertTrue(os.path.exists(manifest_path),
                        "write_sites.json is missing; it is the reviewed inventory")
        manifest = json.load(io.open(manifest_path))["reviewed"]
        actual = self._sites()
        for fn, count in sorted(actual.items()):
            self.assertIn(fn, manifest,
                          "%s writes files but is not in the reviewed inventory. "
                          "Review whether every text it writes passes through "
                          "redaction, then add it to tools/write_sites.json." % fn)
            self.assertEqual(
                count, manifest[fn],
                "%s has %d write sites but %d were reviewed. A write site was "
                "added or removed: confirm it redacts user or model text, then "
                "update tools/write_sites.json." % (fn, count, manifest[fn]))
```

Add `import re` to the imports at the top of `tools/test_bm.py` if it is not already present.

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 tools/test_bm.py TestPreWriteGate -v`
Expected: FAIL with "write_sites.json is missing"

- [ ] **Step 3: Generate the manifest and write it**

Run this to produce the current counts:

```bash
python3 - <<'PY'
import io, os, json, re
HERE = "tools"
pats = (r'open\([^)]*["\']w["\']', r'os\.open\(', r'\.write\(')
found = {}
for fn in sorted(os.listdir(HERE)):
    if not fn.endswith(".py") or fn.startswith("test_"):
        continue
    hits = 0
    for line in io.open(os.path.join(HERE, fn), encoding="utf-8").read().splitlines():
        if line.strip().startswith("#"):
            continue
        if any(re.search(p, line) for p in pats):
            hits += 1
    if hits:
        found[fn] = hits
io.open(os.path.join(HERE, "write_sites.json"), "w").write(json.dumps(
    {"_comment": "Reviewed write sites. If this test fails, a write site was "
                 "added or removed. Confirm the new site redacts any user or "
                 "model text before updating these counts.",
     "reviewed": found}, indent=2, sort_keys=True) + "\n")
print(json.dumps(found, indent=2))
PY
```

Then read each reported file and confirm by inspection that every site writing user or model text passes through `redact` or `redact_text`. Fix any that does not before continuing.

- [ ] **Step 4: Run the whole suite**

Run: `python3 tools/test_bm.py`
Expected: PASS, all tests

- [ ] **Step 5: Sync the private skill and commit both**

```bash
cp tools/bm_registry.py tools/bm_threads.py tools/bm_telemetry.py \
   tools/test_bm.py tools/write_sites.json \
   ~/.claude/skills/brothermode/tools/
cd ~/.claude/skills/brothermode && python3 - <<'PY'
import io
p = "tools/bm_telemetry.py"
s = io.open(p).read()
old = 'VAULT = os.environ.get("BROTHERMODE_VAULT", os.path.expanduser("~/BrotherModeVault"))'
new = 'VAULT = os.environ.get("BROTHERMODE_VAULT", "/path/to/your/vault")'
assert s.count(old) == 1, "vault line not found; re-point it by hand"
io.open(p, "w").write(s.replace(old, new))
print("private vault re-pointed")
PY
python3 tools/test_bm.py
git add tools/ && git commit -m "Sync registry unification into the live skill"
cd ~/Documents/brothermode-public
git add tools/write_sites.json tools/test_bm.py
git commit -m "Add the pre-write redaction gate: a reviewed inventory of write sites"
```

---

## Self-Review

**Spec coverage.** Every spec section maps to a task: the work record to Task 1; overlap detection and claim refusal to Task 2; tagged decisions and clash detection to Task 3; the lossless absorb and the generated view to Task 4; the concurrency invariant to Task 5; thread delegation and the thinner `bm_threads.py` to Task 6; per-record spend for the revert gate to Task 7; the pre-write gate and the private sync to Task 8. Two spec items are deliberately NOT tasks and are recorded here so their absence is a decision rather than an oversight: ephemeral fence migration is out of scope until the 2026-08-08 review, and the strict-versus-advisory CI split already exists in `bm_score.py` and needs no new work.

**Placeholder scan.** No TBD, TODO, "similar to Task N", or "add error handling" instructions. Every code step contains the code.

**Type consistency.** `claim`, `decide`, `set_digest`, `absorb`, `render`, `paths_overlap`, `load`, `save`, `with_lock`, `new_record`, and `registry_path` are named identically in their defining task and in every task that consumes them. `claim` and `decide` both return a two-tuple; `absorb` returns a list of two-tuples; `render` returns a string. The record field names in Task 1 (`decisions`, `digest`, `spend`, `lease`, `check`, `evidence`, `files`, `tier`, `state`, `lifetime`) are the same names read in Tasks 4, 6, and 7.

**Known gap, stated rather than hidden.** Task 6 shows targeted replacements inside four existing functions rather than full rewritten function bodies. The implementer must read the surrounding function before editing. This is a deliberate tradeoff to avoid a plan that restates 200 lines of unchanged code, and it is the one place where the implementer needs the file open beside the plan.
