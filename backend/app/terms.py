"""Shared helpers for turning PICO text into search terms (rules and database queries)."""
from __future__ import annotations

import re

# Function words only: a term made of nothing else is dropped, and they are trimmed off its ends
STOP_WORDS = frozenset(
    {
        "a", "an", "the", "of", "in", "on", "at", "to", "by", "for", "with", "without", "and", "or",
        "as", "from", "than", "versus", "vs", "among", "amongst", "who", "whom", "that", "which",
        "is", "are", "was", "were", "be", "been", "having", "have", "has", "had", "any", "all",
        "other", "another", "either", "both", "such", "using", "use", "treated", "treatment",
    }
)

# Words that say who was studied but not what condition: not worth a search clause on their own
GENERIC_PEOPLE = frozenset(
    {"patient", "patients", "adult", "adults", "people", "person", "persons", "participant", "participants",
     "subject", "subjects", "individual", "individuals", "men", "women", "children", "humans", "human"}
)

# "patients with", "adults with" ... in front of the actual condition
POPULATION_LEAD_RE = re.compile(
    r"^(?:(?:adult|adults|patient|patients|people|persons?|individuals?|participants?|subjects?|"
    r"children|men|women|elderly|older adults|humans?)\s+(?:with|having|who have|diagnosed with|suffering from|at risk of)\s+)+",
    re.IGNORECASE,
)

def keyword_pattern(keyword: str) -> re.Pattern[str]:
    """Case-insensitive whole-word / whole-phrase pattern for one keyword.

    Spaces in a phrase match any run of whitespace, and the last word may carry a plural
    "s" or "es" ("SGLT2 inhibitor" also finds "SGLT2 inhibitors"). It never matches inside a
    longer word: "placebo" does not match "nonplacebo", and "T2D" does not match "T2DM".
    """
    words = [re.escape(w) for w in keyword.strip().split()]
    body = r"\s+".join(words)
    return re.compile(rf"(?<![\w]){body}(?:e?s)?(?![\w])", re.IGNORECASE)


# Nouns that name an event ("hospitalization", "mortality"): "X hospitalization" is also written
# "hospitalization for X" or "hospitalization due to X"
EVENT_NOUNS = frozenset(
    {"hospitalization", "hospitalisation", "admission", "admissions", "mortality", "death", "deaths",
     "events", "incidence", "risk", "progression", "relapse", "recurrence"}
)

_REVERSE_RE = re.compile(r"^(?P<head>.+?)\s+(?:for|of|in|from|due\s+to)\s+(?P<tail>.+)$", re.IGNORECASE)


def keyword_variants(term: str) -> list[str]:
    """Other ways the same phrase is commonly worded, so word order doesn't hide a match.

    "hospitalization for heart failure" <-> "heart failure hospitalization", and an event noun
    last ("heart failure hospitalization") also gives "hospitalization for / due to heart failure".
    The term itself is not included.
    """
    words = term.split()
    out: list[str] = []
    reverse = _REVERSE_RE.match(term)
    if reverse:
        out.append(f"{reverse.group('tail')} {reverse.group('head')}")
    if len(words) >= 2 and words[-1].lower() in EVENT_NOUNS:
        rest = " ".join(words[:-1])
        if words[-1].lower() in {"hospitalization", "hospitalisation", "admission", "admissions"}:
            out.append(f"{words[-1]} for {rest}")
        out.append(f"{words[-1]} due to {rest}")
    return [v for v in out if v.lower() != term.lower()]


# A phrase this short is searched exactly; anything longer is a sentence and is split up
MAX_EXACT_PHRASE_WORDS = 3


def trim_stop_words(term: str) -> str:
    words = term.split()
    while words and words[0].lower() in STOP_WORDS:
        words.pop(0)
    while words and words[-1].lower() in STOP_WORDS:
        words.pop()
    return " ".join(words)


def search_phrases(term: str) -> list[str]:
    """The phrases a database should search for one term.

    A short term stays one exact phrase. A longer one (a PICO sentence such as "adults with type 2
    diabetes who were hospitalized for heart failure") is not searched as one exact phrase, which
    would match almost nothing: a leading "adults with" is dropped and the rest is cut at stop words
    into phrases that are each required.
    """
    clean = re.sub(r"\s+", " ", term).strip().strip("\"'")
    if not clean:
        return []
    body = POPULATION_LEAD_RE.sub("", clean) or clean
    if len(body.split()) <= MAX_EXACT_PHRASE_WORDS:
        return [body]

    chunks: list[str] = []
    run: list[str] = []
    for word in body.split():
        if word.lower() in STOP_WORDS:
            if run:
                chunks.append(" ".join(run))
                run = []
        else:
            run.append(word)
    if run:
        chunks.append(" ".join(run))

    specific = [c for c in chunks if not all(w.lower() in GENERIC_PEOPLE for w in c.split())]
    seen: set[str] = set()
    out: list[str] = []
    for chunk in specific or chunks:
        if chunk.lower() not in seen:
            seen.add(chunk.lower())
            out.append(chunk)
    return out or [body]
