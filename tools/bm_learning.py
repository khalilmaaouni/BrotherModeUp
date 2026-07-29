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


# ---------------------------------------------------------------------------
# Loop 4: correction candidate DETECTION.
#
# What this closes, measured rather than assumed (docs/NOT-FINALIZED.md item
# 17): the shipped filter was one English regex with a hard 400-character cap,
# and of five real founder messages it captured two. A French correction and a
# long correction were dropped SILENTLY. The founder works in French, so an
# English-only filter is not a small gap, it is most of his corrections.
#
# Two rules govern everything below.
#   1. A phrase pack produces CANDIDATES, never rules. A false positive costs
#      one line in a review queue. A false negative costs a correction that the
#      system will never see again, so the packs lean towards capture.
#   2. Length never drops a message. A long correction is EXCERPTED with the
#      omission stated in the row, so a reviewer always knows something was
#      cut. Silence is the defect; truncation with a marker is not.
# ---------------------------------------------------------------------------

# Bounded excerpt budget for a captured correction. Larger than the old 400 so
# a real paragraph survives intact, small enough that the inbox never becomes a
# copy of the founder's transcript.
CORRECTION_EXCERPT_LIMIT = 1200

# (family, label, pattern). The family matters: an interrogative message that
# only trips "negation" is a question, while one that trips "instruction" is a
# standing order phrased as a question. See suppression_reasons.
_PACK_EN = (
    # The shipped regex, preserved verbatim as ONE feature rather than replaced,
    # so nothing that was captured before stops being captured now.
    ("negation", "legacy-en-regex", re.compile(
        r"\b(no[,.]? (that|this|the)|not what i|wrong|you did not|you didn'?t|not even"
        r"|i said|stop doing|never do|always use|from now on|instead of|do better)\b",
        re.I)),
    ("replacement", "asked-for-x-not-y", re.compile(
        r"\bi (?:asked|wanted|said)\b[^.!?]{0,120}\bnot\b", re.I)),
    ("instruction", "memory-instruction", re.compile(
        r"\b(remember (?:that|to)?|from now on|going forward|never (?:again )?"
        r"(?:do|use|write|say)|always (?:do|use|write|say)|please stop)\b", re.I)),
    ("negation", "not-what-i-meant", re.compile(
        r"\b(that'?s not (?:it|right|what)|not (?:like )?that|you missed|you ignored)\b",
        re.I)),
)

_PACK_FR = (
    ("negation", "fr-negation", re.compile(
        r"(ce n'?est pas (?:ce que|ça|cela|bon)|c'?est faux|tu n'?as pas"
        r"|ce n'?est pas ce que je|pas du tout ça)", re.I)),
    ("replacement", "fr-asked-for-x-not-y", re.compile(
        r"(j'?ai (?:demandé|dit)|je t'?ai (?:demandé|dit))[^.!?]{0,120}\bpas\b", re.I)),
    ("instruction", "fr-memory-instruction", re.compile(
        r"(désormais|dorénavant|à partir de maintenant|arrête de|arrete de"
        r"|ne (?:fais|mets|écris|ecris|utilise) (?:plus |jamais)"
        r"|(?:utilise|fais|mets|écris|ecris) toujours"
        r"|il faut toujours|rappelle-toi|souviens-toi|au lieu de)", re.I)),
)

# Japanese has no word boundaries, so every pattern here is a plain substring
# and \b is deliberately absent. Starter phrases only, each one backed by a
# test, per the plan's language section.
_PACK_JA = (
    ("negation", "ja-negation", re.compile(
        r"(違います|違う|そうじゃない|そうではない|間違って(?:います|いる)|ではありません)")),
    ("instruction", "ja-memory-instruction", re.compile(
        r"(今後は|これからは|次からは|必ず|覚えておいて|やめてください|しないでください)")),
)

PHRASE_PACKS = (("en", _PACK_EN), ("fr", _PACK_FR), ("ja", _PACK_JA))

# Structural markers that the message is QUOTED law rather than a correction.
# Deliberately structural, not topical: "from now on, follow SKILL.md" is a real
# founder correction that mentions a document, and a topical filter would eat it.
_QUOTE_LINE = re.compile(r"^\s*>")
_QUOTE_ATTRIBUTION = re.compile(
    r"^\s*(?:the\s+)?(?:skill|law|rule|constitution|spec|SKILL\.md|CLAUDE\.md)\s+"
    r"(?:says|states|reads)\b", re.I)
_FENCE = re.compile(r"```")

_BRAINSTORM = re.compile(
    r"^\s*(what if|maybe we|should we|could we|i wonder|how about"
    r"|et si |peut-?[eê]tre |on pourrait )", re.I)
_BUSINESS_CHANGE = re.compile(
    r"(we (?:have )?(?:decided|changed our mind)|new plan is|the client changed"
    r"|on a chang[ée] d'avis|nouveau plan)", re.I)


def quotation_reasons(text):
    """Reasons this message is QUOTED text rather than the founder correcting.

    Structural only. A subagent pasting the constitution back into a message
    trips these; the founder typing a correction that happens to name a
    document does not."""
    raw = text or ""
    lines = [ln for ln in raw.splitlines() if ln.strip()]
    reasons = []
    if lines and all(_QUOTE_LINE.match(ln) for ln in lines):
        reasons.append("every line is a blockquote")
    if _QUOTE_ATTRIBUTION.match(raw):
        reasons.append("the message opens by attributing the text to a document")
    if len(_FENCE.findall(raw)) >= 2:
        inside = sum(len(part) for part in raw.split("```")[1::2])
        if inside >= 0.6 * len(raw):
            reasons.append("the message is mostly a fenced code block")
    return reasons


def suppression_reasons(text, families):
    """Reasons a phrase hit should NOT become a candidate.

    `families` are the signal families that matched. The interrogative rule is
    the load-bearing one: "why didn't you use the desktop app?" trips the
    negation family and is a question, not a standing preference. The same
    sentence carrying an instruction family ("from now on use the desktop app,
    ok?") is a correction wearing a question mark, and is kept."""
    norm = normalize_text(text)
    reasons = []
    if norm.endswith("?") and "instruction" not in families and "replacement" not in families:
        reasons.append("reads as a question, not a standing instruction")
    if _BRAINSTORM.search(norm):
        reasons.append("reads as brainstorming, not a correction")
    if _BUSINESS_CHANGE.search(norm):
        reasons.append("reads as a changed decision, not a permanent preference")
    return reasons


def bounded_excerpt(text, limit=CORRECTION_EXCERPT_LIMIT):
    """(excerpt, truncated). Long text is CUT WITH A MARKER, never dropped.

    Head and tail are both kept because a correction usually states the problem
    at the start and the instruction at the end, and keeping only the head was
    how the old cap turned a 4,000 character correction into nothing at all."""
    norm = normalize_text(text)
    if len(norm) <= limit:
        return norm, False
    marker = " [... %d characters omitted ...] "
    head = (limit * 2) // 3
    tail = limit - head - len(marker % len(norm))
    if tail < 0:
        tail = 0
    omitted = len(norm) - head - tail
    cut = norm[:head] + (marker % omitted)
    if tail:
        cut += norm[len(norm) - tail:]
    return cut, True


def detect_correction(text, limit=CORRECTION_EXCERPT_LIMIT):
    """None, or a description of why this founder message looks like a
    correction.

    Unicode-safe and language-agnostic at the boundary: nothing here assumes
    ASCII, and every pack is optional. Explicit capture (bm_learn.py capture)
    covers a language no pack knows yet, so a missing pack is a recall gap to
    close and never a wall the founder cannot get past."""
    norm = normalize_text(text)
    if not norm:
        return None
    hits = []
    for lang, pack in PHRASE_PACKS:
        for family, label, pattern in pack:
            if pattern.search(norm):
                hits.append((lang, family, label))
    if not hits:
        return None
    if quotation_reasons(text):
        return None
    families = set(h[1] for h in hits)
    if suppression_reasons(norm, families):
        return None
    excerpt, truncated = bounded_excerpt(norm, limit)
    langs = []
    for lang, _family, _label in hits:
        if lang not in langs:
            langs.append(lang)
    return {
        "lang": langs[0],
        "languages": langs,
        "signals": ["%s:%s" % (lang, label) for lang, _family, label in hits],
        "families": sorted(families),
        "excerpt": excerpt,
        "truncated": truncated,
        "original_length": len(norm),
    }


def inbox_identity(session_id, text):
    """The identity of ONE captured correction inbox row.

    Backfill must be safe to run any number of times, so identity has to be a
    property of the row itself and not of when it was imported. Session plus
    normalized text is exactly what the vault file already deduplicates on, so
    the store and the inbox agree on what "the same row" means."""
    return content_hash("correction-inbox", session_id or "", text or "")


def text_echo_key(text):
    """The key that answers "have I seen these WORDS before, from anywhere".

    Separate from inbox_identity on purpose: identity is session scoped, an
    echo is not. Case and whitespace are folded (content_hash normalizes and
    lowercases), because the founder restating a correction with sentence
    capitalization is the same correction and the reviewer needs to be told so.
    A raw SQL equality on the stored text was the defect this replaces: one
    capital letter defeated it and the reviewer got no signal at all."""
    return content_hash("correction-echo", text or "")


# Why a rejected candidate was not a rule. Descriptive categories over the
# founder's OWN stated reason, never an inference about what he meant: an
# unmatched reason is "other" rather than being forced into a bucket. The
# categories exist so the capture channels can be tuned against real review
# cost; they are counts, not an accuracy measurement.
_FP_CATEGORIES = (
    ("not-a-correction", re.compile(
        r"(?i)\bnot a (?:correction|rule|preference)\b|\bjust (?:a )?(?:question|asking)\b"
        r"|\bbrainstorm|\bthinking out loud\b|\bdiscussion\b")),
    ("one-off", re.compile(
        r"(?i)\bone[- ]off\b|\bjust (?:this|that) once\b|\bonly (?:this|that) time\b"
        r"|\bthis case only\b|\btemporar")),
    ("duplicate", re.compile(r"(?i)\bduplicate\b|\balready (?:have|a rule|captured|covered)\b"
                             r"|\bsame as\b|\bredundant\b")),
    ("wrong-scope", re.compile(r"(?i)\bwrong (?:scope|project|repo)\b|\bother project\b"
                               r"|\bnot global\b|\bproject specific\b")),
    ("superseded", re.compile(r"(?i)\bchanged my mind\b|\bno longer\b|\bsupersed|\boutdated\b"
                              r"|\bout of date\b")),
    ("noise", re.compile(r"(?i)\bnoise\b|\bfalse positive\b|\bgarbage\b|\bmisdetect")),
)

FALSE_POSITIVE_CATEGORIES = tuple(name for name, _pat in _FP_CATEGORIES) + ("other",)


def false_positive_category(reason):
    """Bucket a rejection reason. Always returns one of FALSE_POSITIVE_CATEGORIES.

    First match wins and the order is fixed, so the same reason always lands in
    the same bucket. An empty or unrecognized reason is "other", which is the
    honest answer when the founder's words do not say which kind it was."""
    norm = normalize_text(reason)
    if not norm:
        return "other"
    for name, pat in _FP_CATEGORIES:
        if pat.search(norm):
            return name
    return "other"
