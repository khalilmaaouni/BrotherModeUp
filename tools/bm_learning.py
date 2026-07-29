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


# ---------------------------------------------------------------------------
# Loop 6: duplicates, contradictions and supersession.
#
# WHAT THESE FUNCTIONS MAY AND MAY NOT CLAIM
#   Everything here is deterministic and lexical, the same honesty the retrieval
#   ranker holds itself to. There is no embedding, no similarity model, and no
#   attempt to understand what a rule means. So:
#     * a DUPLICATE is detected when two rules say nearly the same words in the
#       same scope, which is the case that actually floods a review queue;
#     * a CONTRADICTION is detected only when two rules in the same scope give
#       OPPOSITE polarity instructions about the same subject ("always push
#       through the desktop app" against "never push through the desktop app").
#       That is the shape a founder's own reversal takes, and it is the one
#       shape a lexical comparison can be trusted on. It is judged on how much
#       of the SHORTER action the longer one also names, so padding one side
#       with an ordinary founder clause does not hide the reversal, and the
#       trigger wording does not have to match for it to count.
#   "Use tabs" against "use spaces" is a real contradiction and this code will
#   NOT find it. That gap is why `link a contradicts b` exists as a founder
#   command: the founder can always declare a conflict the detector cannot see,
#   and a declared conflict counts exactly as much as a detected one everywhere
#   downstream. Nothing here ever RESOLVES a conflict; resolution is a founder
#   act, and these functions only ever describe.
# ---------------------------------------------------------------------------

RELATIONS = ("duplicate_of", "contradicts", "supersedes",
             "derived_from", "supports", "applies_to")

# Polarity markers, English and French. A rule whose action carries one of these
# forbids something; a rule with none of them requires something. Deliberately
# small: a longer list starts flipping the polarity of ordinary prose, and a
# wrongly flipped polarity manufactures a contradiction that blocks an approval.
_NEGATORS = frozenset((
    "never", "not", "no", "dont", "don", "avoid", "stop", "without", "refuse",
    "jamais", "pas", "aucun", "sans", "arrete", "cesse",
))

# The mirror of _NEGATORS: words that assert an instruction rather than negate
# it. They carry no subject of their own, so they are removed alongside the
# negators when two actions are compared. Without this, "always push through the
# desktop app" kept the token "always" while "never push through the desktop
# app" lost "never", the two subjects came out different sizes, and the very
# comparison _content_tokens exists to make was skewed by the polarity words it
# was supposed to cancel out.
_AFFIRMERS = frozenset(("always", "toujours"))

_POLARITY_MARKERS = _NEGATORS | _AFFIRMERS

# Phrases that INTENSIFY an instruction while containing a negation word.
# "always run the tests, no exceptions" is the founder agreeing with himself
# more loudly, not forbidding anything, and reading "no" there flipped the rule
# to 'forbid' and manufactured a contradiction against a rule that plainly
# agreed with it. Stripped before polarity is read, never after.
_INTENSIFIERS = re.compile(
    r"\b(?:no|without)\s+(?:exceptions?|fail)\b"
    r"|\bno\s+matter\s+what\b"
    r"|\bsans\s+(?:exceptions?|faute)\b"
    r"|\baucune\s+exception\b", re.I)

ACTION_RELATIONS = ("identical", "near_duplicate", "incompatible",
                    "narrowing", "not_comparable")

# Named thresholds rather than numbers buried in a condition, because invariant
# L9 says every decision has to be able to explain itself, and "0.85" inside an
# if statement explains nothing.
NEAR_DUPLICATE_FLOOR = 0.85
INCOMPATIBLE_FLOOR = 0.5
NARROWING_FLOOR = 0.5
TRIGGER_OVERLAP_FLOOR = 0.3

# A reversal is judged by how much of the SHORTER action the longer one also
# names, not by symmetric overlap. Symmetric overlap punishes length: padding
# "never push through the desktop app" with an ordinary founder clause dropped
# the score under INCOMPATIBLE_FLOOR and the reversal stopped being seen at all,
# which is the silent accumulation the Loop 6 done gate forbids.
SUBJECT_CONTAINMENT_FLOOR = 0.8

# A one-word subject can be contained in anything, so a single shared token
# would start flagging "never commit" against "always commit the lock file after
# every build", which is a narrowing and not a reversal.
MIN_SUBJECT_TOKENS = 2

CONFLICT_VERDICTS = ("duplicate", "contradiction", "narrowing", "unrelated")


def _without_intensifiers(text):
    """Text with intensifier phrases removed. See _INTENSIFIERS."""
    return _INTENSIFIERS.sub(" ", text or "")


def polarity(text):
    """'forbid' or 'require'. See _NEGATORS on why the marker list is small."""
    toks = set(tokenize(_without_intensifiers(text)))
    return "forbid" if toks & _NEGATORS else "require"


def _content_tokens(text):
    """Tokens with polarity markers removed, so "always use X" and "never use X"
    compare as the SAME subject with opposite polarity rather than as two
    different subjects."""
    return set(tokenize(_without_intensifiers(text))) - _POLARITY_MARKERS


def _jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / float(len(a | b))


def subject_containment(a, b):
    """How much of the SHORTER action's subject the longer one also names.

    0.0 to 1.0, and deliberately asymmetric in what it divides by: a founder who
    restates one side of a reversal at greater length is still talking about the
    same thing, and a symmetric score reads that extra length as a different
    subject."""
    ta = _content_tokens(a)
    tb = _content_tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / float(min(len(ta), len(tb)))


def direct_reversal(a, b):
    """Are these two actions the SAME instruction with opposite polarity?

    This is the one shape a lexical comparison can be trusted on, and it is the
    shape the docs promise is caught: "always push through the desktop app"
    against "never push through the desktop app", however either side is padded
    and however differently the two triggers were phrased."""
    if polarity(a) == polarity(b):
        return False
    ta = _content_tokens(a)
    tb = _content_tokens(b)
    if min(len(ta), len(tb)) < MIN_SUBJECT_TOKENS:
        return False
    return subject_containment(a, b) >= SUBJECT_CONTAINMENT_FLOOR


def scope_relation(a_type, a_key, b_type, b_key):
    """How A's scope relates to B's: same, broader, narrower or disjoint.

    Containment between two NON-global scopes is not inferred. This store holds
    no map saying artifact 'executive-update' lives inside project 'Tonari', so
    claiming one narrows the other would be a guess, and a guess here decides
    whether an approval is blocked. Unknown containment reports 'disjoint',
    which coexists rather than blocks."""
    ak = normalize_text(a_key).lower()
    bk = normalize_text(b_key).lower()
    if a_type == b_type:
        if a_type == "global":
            return "same"
        return "same" if ak == bk else "disjoint"
    if a_type == "global":
        return "broader"
    if b_type == "global":
        return "narrower"
    return "disjoint"


def action_relation(a, b):
    """One of ACTION_RELATIONS, describing two rule actions against each other."""
    na = normalize_text(a).lower()
    nb = normalize_text(b).lower()
    if not na or not nb:
        return "not_comparable"
    if na == nb:
        return "identical"
    ta = _content_tokens(a)
    tb = _content_tokens(b)
    if not ta or not tb:
        return "not_comparable"
    overlap = _jaccard(ta, tb)
    if polarity(a) != polarity(b):
        if overlap >= INCOMPATIBLE_FLOOR or direct_reversal(a, b):
            return "incompatible"
        return "not_comparable"
    if overlap >= NEAR_DUPLICATE_FLOOR:
        return "near_duplicate"
    if (ta < tb or tb < ta) and overlap >= NARROWING_FLOOR:
        return "narrowing"
    return "not_comparable"


def conflict_verdict(a, b):
    """Compare two rule dicts and say, with its working shown, what they are to
    each other.

    Only rules in the SAME scope can reach 'contradiction'. A narrower rule
    beside a broader one is how a founder legitimately says "in general do X,
    but here do Y", and blocking that would make the scope system useless. It
    reports 'narrowing' instead, which is visible and never blocks.

    The trigger-overlap floor is a tie breaker, NOT a veto. Triggers are free
    text and the founder routinely phrases the same situation two ways
    ("pushing to github" and "publishing commits upstream"). When the two
    actions are a direct reversal of each other, that disagreement is real
    whatever words the triggers used, so the floor is bypassed and said to be
    bypassed in the reasons."""
    scope = scope_relation(a["scope_type"], a.get("scope_key", ""),
                           b["scope_type"], b.get("scope_key", ""))
    trig = _jaccard(set(tokenize(a.get("trigger_text", ""))),
                    set(tokenize(b.get("trigger_text", ""))))
    act = action_relation(a.get("action_text", ""), b.get("action_text", ""))
    reversal = direct_reversal(a.get("action_text", ""), b.get("action_text", ""))
    trigger_note = ""
    verdict = "unrelated"
    if scope == "same":
        if act in ("identical", "near_duplicate") and trig >= TRIGGER_OVERLAP_FLOOR:
            verdict = "duplicate"
        elif act == "incompatible" and (trig >= TRIGGER_OVERLAP_FLOOR or reversal):
            verdict = "contradiction"
            if trig < TRIGGER_OVERLAP_FLOOR:
                trigger_note = (" (below the floor and not required: the actions "
                                "are a direct reversal)")
        elif act == "narrowing":
            verdict = "narrowing"
    elif scope in ("broader", "narrower"):
        if act in ("identical", "near_duplicate", "incompatible", "narrowing"):
            verdict = "narrowing"
    return {
        "verdict": verdict,
        "scope_relation": scope,
        "trigger_overlap": round(trig, 3),
        "action_relation": act,
        "direct_reversal": reversal,
        "subject_containment": round(subject_containment(
            a.get("action_text", ""), b.get("action_text", "")), 3),
        "reasons": ["scope %s" % scope,
                    "trigger overlap %.2f%s" % (trig, trigger_note),
                    "actions %s" % act],
    }


def _supersedes_adjacency(edges):
    adj = {}
    for pair in edges:
        adj.setdefault(pair[0], set()).add(pair[1])
    return adj


def supersession_cycle(edges, new_from, new_to):
    """Would adding "new_from supersedes new_to" close a loop?

    A supersession cycle means every rule in it claims to replace another one
    that eventually replaces it, so no version of that instruction is current.
    The state machine alone does not prevent this: an already superseded rule
    can still be named as the SUCCESSOR of a third rule, which is exactly how a
    three-rule loop forms."""
    if new_from == new_to:
        return True
    adj = _supersedes_adjacency(edges)
    adj.setdefault(new_from, set()).add(new_to)
    seen = set()
    stack = [new_to]
    while stack:
        node = stack.pop()
        if node == new_from:
            return True
        if node in seen:
            continue
        seen.add(node)
        stack.extend(adj.get(node, ()))
    return False


def supersession_cycles(edges):
    """Every rule uuid that sits on a supersedes cycle, sorted.

    The integrity checker needs to find loops that ALREADY exist, for instance
    in a store written by an older build that had no cycle guard, which the
    pre-insert check above cannot tell it."""
    adj = _supersedes_adjacency(edges)
    on_cycle = set()
    for start in list(adj):
        seen = set()
        stack = list(adj.get(start, ()))
        while stack:
            node = stack.pop()
            if node == start:
                on_cycle.add(start)
                break
            if node in seen:
                continue
            seen.add(node)
            stack.extend(adj.get(node, ()))
    return sorted(on_cycle)


# ---------------------------------------------------------------------------
# Loop 7: the application lifecycle, in pure form.
#
# Storing rules answers "what did the founder say". It does not answer "was the
# right rule surfaced, and was it followed". Those are the questions an
# application row exists for, and the three functions below are the only places
# that DECIDE anything about them. They take facts and return a judgement, with
# no clock, no database and no file, so the judgement can be tested directly
# and cannot quietly depend on when it ran.
#
# The rule that governs all of it: a classification is refused when the
# evidence is missing. "not_decidable" is a first-class answer here, not a
# failure of the classifier, because a confident wrong label is worse than an
# honest gap on data the founder will act on.
# ---------------------------------------------------------------------------

DISPOSITIONS = ("followed", "ignored", "not_relevant", "unknown")

APPLICATION_OUTCOMES = ("pending", "accepted", "rework", "escaped_defect",
                        "corrected_again", "not_decidable")

# Outcomes that mean the work had to be done again or reached the founder
# broken. Following a rule into one of these is what makes a rule suspect.
NEGATIVE_OUTCOMES = ("rework", "escaped_defect", "corrected_again")

FAILURE_CLASSES = ("retrieval_miss", "compliance_failure", "bad_rule",
                   "scope_error", "not_decidable")

# Rule types where ignoring the rule is a decision the founder is entitled to
# see a reason for. A skipped communication PREFERENCE is a small thing; a
# skipped safety procedure or a skipped decision right is not, and neither is
# anything the founder marked severity 'gate'.
SUBSTANTIAL_RULE_TYPES = ("safety", "procedure", "decision_right")


def disposition_needs_reason(disposition, severity, rule_type):
    """True when recording this disposition requires a stated reason.

    Only 'ignored' can require one. Following a rule needs no defence, and
    'not_relevant' is itself the reason (it says the retrieval was wrong, which
    is graded as a scope error rather than as a compliance failure)."""
    if disposition != "ignored":
        return False
    return severity == "gate" or rule_type in SUBSTANTIAL_RULE_TYPES


def classify_application(disposition, shown_to_model, outcome):
    """Grade ONE recorded application. Returns (class_or_None, reason).

    None means nothing failed, which is a different statement from
    'not_decidable' and is kept separate on purpose: a rule that was followed
    into an accepted outcome is a success, while a rule that was followed with
    no outcome recorded yet is simply not gradeable.

    retrieval_miss is not decidable from a single row (a row that exists is by
    definition not a miss), so it is produced by the store, which can compare
    what was recorded against what was retrievable at the time."""
    shown = bool(shown_to_model)
    if disposition not in DISPOSITIONS:
        return ("not_decidable", "disposition %r is not one this build knows"
                % (disposition,))
    if outcome not in APPLICATION_OUTCOMES:
        return ("not_decidable", "outcome %r is not one this build knows"
                % (outcome,))
    if disposition == "unknown":
        return ("not_decidable",
                "no disposition was recorded at task close, so whether the rule "
                "was followed is unknown rather than negative")
    if disposition == "ignored":
        if not shown:
            return ("not_decidable",
                    "recorded as ignored but never shown to the acting model, so "
                    "there was nothing to comply with")
        return ("compliance_failure",
                "the rule was retrieved, shown and ignored")
    if disposition == "not_relevant":
        return ("scope_error",
                "the rule was retrieved for a task it did not apply to, so its "
                "scope is wider than the situation it belongs to")
    if outcome in NEGATIVE_OUTCOMES:
        return ("bad_rule",
                "the rule was followed and the work still ended in %s" % outcome)
    if outcome == "accepted":
        return (None, "followed, and the outcome was accepted")
    return ("not_decidable",
            "followed, but no outcome has been recorded against it yet")


# The task signals that make retrieval proportionate. Named rather than
# free-form so a caller cannot invent a signal that nothing grades.
RETRIEVAL_SIGNALS = ("communication_artifact", "architecture_decision",
                     "multi_file_change", "risky_operation", "prior_correction")

_SIGNAL_REASONS = {
    "communication_artifact": "the founder will read or reuse the artifact",
    "architecture_decision": "it is an architecture or design decision",
    "multi_file_change": "it changes more than one file",
    "risky_operation": "it is a risky or irreversible operation",
    "prior_correction": "a correction has landed in this area before",
}


def retrieval_advised(signals=None, gate_rules_exist=False):
    """Should this task retrieve founder rules before it starts?

    The proportionality rule, made mechanical: retrieval on a one-line obvious
    edit is ceremony, and ceremony is what makes a founder stop reading. So the
    default is NO, and a named signal turns it on. The single exception is a
    live gate rule, because a safety gate is exactly the thing that must appear
    when the person did not think to ask for it.

    Returns a decision the caller can print. It records NOTHING: deciding not
    to retrieve must never manufacture an application row, or the outcome data
    fills up with tasks that never happened."""
    signals = signals or {}
    unknown = sorted(k for k in signals if k not in RETRIEVAL_SIGNALS)
    fired = [s for s in RETRIEVAL_SIGNALS if signals.get(s)]
    reasons = [_SIGNAL_REASONS[s] for s in fired]
    if fired:
        return {"advised": True, "signals": fired, "reasons": reasons,
                "unknown_signals": unknown}
    if gate_rules_exist:
        return {"advised": True, "signals": [],
                "reasons": ["a founder gate rule is live, and a gate applies "
                            "even to a small task"],
                "unknown_signals": unknown}
    return {"advised": False, "signals": [],
            "reasons": ["no substantial signal fired, so retrieval here would "
                        "be ceremony rather than care"],
            "unknown_signals": unknown}


# ---------------------------------------------------------------------------
# Loop 8: grading a correction that came back.
#
# The whole program's claim is that BrotherMode learns. The only way to tell
# learning from storage growth is to look at what happened AFTER a rule
# existed: work redone, a defect that reached the founder, or the same
# correction said twice. Those three are external evidence. The session being
# graded cannot write any of them about itself in a way that flatters it,
# because each one is anchored to a work record, an artifact, or the founder's
# own words.
#
# These functions decide, and nothing else here does. No clock, no database,
# no file, so the judgement is testable on its own and cannot drift with when
# it ran.
# ---------------------------------------------------------------------------

# What each miss class says about the RULE itself, and therefore which way the
# evidence points. A rule that was never retrieved, or was retrieved and
# skipped, is not a bad rule: the founder saying it again is evidence he still
# wants it, so that is SUPPORT. A rule that was followed and the correction
# came back anyway is the opposite, and so is one retrieved into work it was
# then judged irrelevant to.
REPEATED_CORRECTION_POLARITY = {
    "retrieval_miss": "support",
    "compliance_failure": "support",
    "bad_rule": "contradict",
    "scope_error": "contradict",
    "not_decidable": "neutral",
}


def classify_repeated_correction(applications, links_known):
    """Why did a rule that already existed fail to prevent this correction?

    Returns (class, reason, polarity). `applications` are the recorded
    applications of that rule in the work the correction is about, each a dict
    carrying 'disposition' and 'shown_to_model'. `links_known` says whether
    the correction names a session or a work record at all.

    The ordering is deliberate and is the point of the whole function:
    'followed' outranks everything, because a rule that was obeyed and did not
    work is the only case where the RULE is the problem. Getting that order
    wrong would blame the rule for every failure to retrieve it, and the
    founder would end up editing text that was already correct."""
    if not links_known:
        return ("not_decidable",
                "this correction names neither a session nor a work record, so "
                "what was retrieved when it happened cannot be established",
                REPEATED_CORRECTION_POLARITY["not_decidable"])
    rows = list(applications or [])
    if not rows:
        return ("retrieval_miss",
                "the rule was live when this work ran and no application of it "
                "was recorded, so it never reached the acting model",
                REPEATED_CORRECTION_POLARITY["retrieval_miss"])
    followed = [r for r in rows if r.get("disposition") == "followed"]
    ignored = [r for r in rows if r.get("disposition") == "ignored"
               and bool(r.get("shown_to_model"))]
    irrelevant = [r for r in rows if r.get("disposition") == "not_relevant"]
    if followed:
        return ("bad_rule",
                "the rule was followed in %d recorded application(s) and the "
                "work went wrong anyway, so the rule as written did not "
                "prevent it" % len(followed),
                REPEATED_CORRECTION_POLARITY["bad_rule"])
    if ignored:
        return ("compliance_failure",
                "the rule was shown in %d recorded application(s) and skipped, "
                "and the work it applied to went wrong" % len(ignored),
                REPEATED_CORRECTION_POLARITY["compliance_failure"])
    if irrelevant:
        return ("scope_error",
                "the rule was retrieved for this work and marked not relevant, "
                "yet the failure it covers happened here, so its scope does "
                "not match where it is actually needed",
                REPEATED_CORRECTION_POLARITY["scope_error"])
    return ("not_decidable",
            "%d application(s) exist but none carries a usable disposition, so "
            "whether the rule was followed cannot be read from what was "
            "recorded" % len(rows),
            REPEATED_CORRECTION_POLARITY["not_decidable"])


# Units a review window may be written in. Months and years are deliberately
# absent: they are not fixed numbers of days, and a window that silently means
# something different in February is a reporting bug waiting to happen.
WINDOW_UNITS = (("d", 1.0), ("w", 7.0), ("h", 1.0 / 24.0))


def parse_window_days(text):
    """A window like '30d', '2w' or '48h' into days. Returns (days, error).

    A bare number means days. Anything else returns (None, message) rather
    than a default, because a window silently reinterpreted is a report about
    a different period than the one asked for."""
    raw = normalize_text(text or "")
    if not raw:
        return (None, "no window given")
    body, factor = raw, 1.0
    for suffix, mult in WINDOW_UNITS:
        if raw.lower().endswith(suffix):
            body, factor = raw[:-1], mult
            break
    try:
        value = float(body)
    except ValueError:
        return (None, "cannot read %r as a window; use a number of days or a "
                      "suffix from %s (for example 30d)"
                      % (text, ", ".join(s for s, _ in WINDOW_UNITS)))
    if value <= 0:
        return (None, "a window must be positive, got %r" % (text,))
    return (value * factor, "")
