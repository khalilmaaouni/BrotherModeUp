#!/usr/bin/env python3
"""Pure functions for correction learning: normalization, hashing, atomicity,
scope rules, tokenizing and ranking.

WHY THIS FILE IS SEPARATE FROM bm_store.py
  bm_store.py is the ONLY writer of the database and its job is transactions.
  Everything here is a pure function: same input, same output, no connection, no
  clock, no filesystem. Keeping them apart means the interesting decisions (is
  this rule atomic? does this scope match? which rule ranks first?) can be tested
  exhaustively without a database, and the store stays readable as a store.

WHY THIS FILE IS SEPARATE FROM bm_learn.py
  bm_learn.py is the founder's command line. A CLI that also owns the semantics
  ends up with its rules only reachable by spawning a process.

RETRIEVAL MODE, STATED PLAINLY: this module implements DETERMINISTIC LEXICAL
matching only. The source plan also asks for an optional FTS5 index probed at
runtime; that is NOT built yet. Retrieval therefore reports its mode as
"lexical" always, and no code anywhere claims BM25 or full-text ranking. The
plan's requirement that diagnostics name the mode is met by naming the only mode
that exists. When FTS5 lands, it becomes the fast path and this stays the
degraded one, tested against the same fixtures.

Python 3.9, standard library only. No network. No subprocess. Writes no files.

No em or en dashes anywhere in this file, its comments, or its output.
"""

import hashlib
import re
import unicodedata

SCOPE_TYPES = ("global", "project", "domain", "artifact", "relationship", "tool")

# Ordered MOST specific first. Retrieval uses the index as the primary sort key,
# so this tuple IS the precedence rule rather than a comment describing one.
SCOPE_SPECIFICITY = ("relationship", "artifact", "tool", "domain", "project", "global")

RULE_STATES = ("approved", "confirmed", "settled", "contradicted",
               "deprecated", "superseded", "forgotten")

# States eligible for automatic injection. Deliberately excludes contradicted
# (an unresolved conflict must not speak), deprecated, superseded and forgotten.
INJECTABLE_STATES = ("settled", "confirmed", "approved")

CANDIDATE_STATUSES = ("pending", "under_review", "approved", "merged", "split",
                      "rejected", "expired")

RETRIEVAL_MODE = "lexical"

_LEGAL_STATE_MOVES = {
    "approved": ("confirmed", "contradicted", "deprecated", "superseded", "forgotten"),
    "confirmed": ("settled", "contradicted", "deprecated", "superseded", "forgotten"),
    "settled": ("contradicted", "deprecated", "superseded", "forgotten"),
    "contradicted": ("approved", "confirmed", "deprecated", "superseded", "forgotten"),
    "deprecated": ("approved", "forgotten"),
    "superseded": ("forgotten",),
    "forgotten": (),
}

_WS = re.compile(r"\s+")


def normalize_text(text):
    """Collapse whitespace and normalize Unicode WITHOUT changing meaning.

    NFC, not NFKD: NFKD would fold typographic characters into ASCII lookalikes
    and quietly rewrite what the founder actually typed. Case is preserved for
    display; callers that want case-insensitive comparison lower the RESULT, so
    the stored text and the comparison key never diverge."""
    if not text:
        return ""
    return _WS.sub(" ", unicodedata.normalize("NFC", text)).strip()


def content_hash(*parts):
    """Stable fingerprint over normalized, lowercased parts.

    Used to spot an EXACT repeat, never as an identity: two candidates with the
    same hash in different scopes are two different pieces of evidence, which is
    why the schema carries no unique index on this column."""
    joined = " ".join(normalize_text(p).lower() for p in parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


# A compound correction carries more than one instruction. Splitting it is the
# founder's call, never the parser's, so these only ever RAISE A FLAG.
_COMPOUND_PATTERNS = (
    (re.compile(r"\band always\b", re.I), "contains 'and always', which usually joins two rules"),
    (re.compile(r"\band never\b", re.I), "contains 'and never', which usually joins two rules"),
    (re.compile(r";"), "contains a semicolon, which usually separates two instructions"),
    (re.compile(r"^\s*[-*]\s+.*\n\s*[-*]\s+", re.M), "contains a bulleted list"),
)


def atomicity_problems(action_text):
    """Reasons this action looks like MORE THAN ONE rule. Empty list means it
    looks atomic.

    Advisory at capture and blocking at approval, because a compound rule can
    never be graded: when the outcome is bad you cannot tell which half was
    wrong. The founder can override at approval with a stated reason, and that
    override is recorded as evidence rather than swallowed as a silent bypass."""
    text = normalize_text(action_text)
    if not text:
        return ["action is empty"]
    return [why for pattern, why in _COMPOUND_PATTERNS if pattern.search(text)]


def validate_scope(scope_type, scope_key):
    """Return an error string, or None when the scope is usable.

    Every scope except global REQUIRES a key. A project-scoped rule with no key
    would match everything, which is the contamination that invariant L5 exists
    to prevent, and it would do it while looking correctly scoped."""
    if scope_type not in SCOPE_TYPES:
        return "unknown scope type %r (known: %s)" % (scope_type, ", ".join(SCOPE_TYPES))
    if scope_type != "global" and not normalize_text(scope_key):
        return "scope type %r requires a scope key; only 'global' may omit one" % scope_type
    return None


_TOKEN = re.compile(r"[^\W_]+", re.UNICODE)

# Deliberately tiny and English-only. A large stop list starts discarding real
# signal in other languages, and this founder works in French as well.
_STOP = frozenset(("the", "a", "an", "and", "or", "of", "to", "in", "on", "for",
                   "is", "are", "be", "it", "this", "that", "with", "when"))


def tokenize(text):
    """Lowercased word tokens, Unicode-aware so accented French text tokenizes
    the same way English does."""
    return [t for t in (m.group(0).lower() for m in _TOKEN.finditer(text or ""))
            if t and t not in _STOP]


def lexical_overlap(query, *fields):
    """Fraction of query tokens present in the rule's text, 0.0 to 1.0.

    Plain overlap rather than a tuned score on purpose: an unexplainable number
    is exactly what invariant L9 forbids. This is the only relevance signal that
    exists today; see the module docstring on FTS5."""
    q = set(tokenize(query))
    if not q:
        return 0.0
    haystack = set()
    for f in fields:
        haystack.update(tokenize(f))
    return len(q & haystack) / float(len(q))


def scope_matches(rule_scope_type, rule_scope_key, context):
    """Is a rule ELIGIBLE for this task context?

    `context` maps scope type to key, e.g. {"project": "TonariSimple",
    "artifact": "executive-update"}. Global always matches. Every other scope
    matches only when the context supplies that exact key, compared on the
    normalized lowercase form so "Executive-Update" and "executive-update" are
    the same artifact. A context that does not mention a scope type at all can
    never match a rule of that type: absence is not a wildcard."""
    if rule_scope_type == "global":
        return True
    supplied = (context or {}).get(rule_scope_type)
    if not supplied:
        return False
    return normalize_text(supplied).lower() == normalize_text(rule_scope_key).lower()


def rank_key(rule, query, context=None):
    """Sort key for retrieval. Lower sorts FIRST.

    Lexicographic over NAMED components rather than one blended score, so every
    result can explain its own position (invariant L9). Order:
      1. scope specificity, most specific first;
      2. rule state, settled before confirmed before approved;
      3. lexical relevance, higher first;
      4. rule_uuid, purely so the order is stable and reproducible."""
    spec = SCOPE_SPECIFICITY.index(rule["scope_type"]) \
        if rule["scope_type"] in SCOPE_SPECIFICITY else len(SCOPE_SPECIFICITY)
    state = INJECTABLE_STATES.index(rule["state"]) \
        if rule["state"] in INJECTABLE_STATES else len(INJECTABLE_STATES)
    relevance = lexical_overlap(query, rule.get("trigger_text", ""),
                                rule.get("action_text", ""),
                                rule.get("because_text", ""),
                                rule.get("domain", ""),
                                rule.get("scope_key", ""))
    return (spec, state, -relevance, rule.get("rule_uuid", ""))


def explain_rank(rule, query, context=None):
    """The human-readable reason a rule was selected, built from the SAME
    values rank_key sorts on. Derived from one source so the explanation cannot
    drift from the ordering it claims to describe."""
    matched = sorted(set(tokenize(query)) &
                     set(tokenize("%s %s" % (rule.get("trigger_text", ""),
                                             rule.get("action_text", "")))))
    scope = rule["scope_type"]
    if scope != "global":
        scope = "%s:%s" % (scope, rule.get("scope_key", ""))
    return {
        "scope": scope,
        "state": rule["state"],
        "mode": RETRIEVAL_MODE,
        "matched_terms": matched,
        "relevance": round(lexical_overlap(query, rule.get("trigger_text", ""),
                                           rule.get("action_text", "")), 3),
    }


def state_transition_error(current, target):
    """Error string for an illegal rule state move, or None when it is legal."""
    if current not in _LEGAL_STATE_MOVES:
        return "unknown current state %r" % (current,)
    if target not in RULE_STATES:
        return "unknown target state %r (known: %s)" % (target, ", ".join(RULE_STATES))
    if target not in _LEGAL_STATE_MOVES[current]:
        legal = _LEGAL_STATE_MOVES[current]
        return "cannot move a rule from %r to %r (legal from %r: %s)" % (
            current, target, current, ", ".join(legal) if legal else "nothing")
    return None


_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def safe_display(text, limit=200):
    """One-line, control-character-free, length-capped text for CLI and injected
    output.

    Control characters are stripped rather than escaped because the risk is
    structural: a newline or a carriage return inside a rule's action can forge
    what looks like an entire additional rule block in injected context or in a
    list of results. Stripping removes the capability; escaping only makes it
    visible."""
    flat = _WS.sub(" ", _CONTROL.sub("", text or "")).strip()
    if len(flat) <= limit:
        return flat
    return flat[:limit - 3].rstrip() + "..."


def task_fingerprint(text):
    """A short, stable, NON-REVERSIBLE handle for a task.

    Applications need to recognise "this same kind of task came back" without
    the store accumulating a copy of every prompt the founder ever typed. A
    hash prefix does that; the full text stays where it already was."""
    return content_hash(text)[:16]
