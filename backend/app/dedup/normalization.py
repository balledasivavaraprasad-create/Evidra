"""Pure normalization functions for literature metadata and text."""
import re
import unicodedata

_DOI_PREFIX_RE = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi:)", re.IGNORECASE)
_PUNCTUATION_RE = re.compile(r"[^\w\s]", re.UNICODE)
_WHITESPACE_RE = re.compile(r"\s+")
_TRIAL_ID_RE = re.compile(r"\b(NCT\d{8}|ISRCTN\d{8}|ACTRN\d{14})\b", re.IGNORECASE)


def normalize_doi(doi: str | None) -> str | None:
    """Normalize a Digital Object Identifier string.

    Strips common URL prefixes, leading/trailing whitespace, and case-folds.
    Returns None if the resulting string is empty or invalid.
    """
    if not doi or not isinstance(doi, str):
        return None

    cleaned = doi.strip()
    cleaned = _DOI_PREFIX_RE.sub("", cleaned).strip().lower()

    # Valid DOIs start with '10.'
    if not cleaned.startswith("10.") or len(cleaned) < 7:
        return None

    return cleaned


def normalize_pmid(pmid: str | None) -> str | None:
    """Normalize a PubMed identifier string.

    Extracts numeric digits and strips leading zeros.
    Returns None if no valid digits exist.
    """
    if not pmid or not isinstance(pmid, str):
        return None

    digits = re.sub(r"\D", "", pmid.strip())
    if not digits:
        return None

    stripped = digits.lstrip("0")
    return stripped if stripped else "0"


def normalize_title(title: str | None) -> str:
    """Normalize article title for robust deterministic comparison.

    Applies Unicode NFKC normalization, removes punctuation, collapses whitespace,
    and converts to lowercase while strictly preserving semantic numbers.
    """
    if not title or not isinstance(title, str):
        return ""

    # NFKC normalizes ligatures and compatibility characters
    normalized = unicodedata.normalize("NFKC", title)

    # Remove punctuation
    stripped = _PUNCTUATION_RE.sub(" ", normalized)

    # Collapse whitespace and lowercase
    collapsed = _WHITESPACE_RE.sub(" ", stripped).strip().lower()
    return collapsed


def extract_primary_author_token(authors: list[str] | None) -> str | None:
    """Extract normalized last name token for primary (first) author."""
    if not authors or not isinstance(authors, list) or len(authors) == 0:
        return None

    first_author = authors[0].strip()
    if not first_author:
        return None

    # Common formats: "Miller AB", "Miller, A.B.", "Arthur B. Miller"
    parts = re.split(r"[,\s]+", first_author)
    if not parts:
        return None

    # Usually the first token or last token with length > 1
    for token in parts:
        clean = re.sub(r"[^\w]", "", token).lower()
        if len(clean) > 1 and not clean.endswith("."):
            return clean

    return re.sub(r"[^\w]", "", parts[0]).lower() or None


def extract_author_tokens(authors: list[str] | None) -> set[str]:
    """Extract set of all normalized author surname tokens for a paper."""
    if not authors or not isinstance(authors, list):
        return set()

    tokens = set()
    for author in authors:
        parts = re.split(r"[,\s]+", author.strip())
        for token in parts:
            clean = re.sub(r"[^\w]", "", token).lower()
            if len(clean) > 1:
                tokens.add(clean)
    return tokens


def extract_trial_registrations(text: str | None) -> list[str]:
    """Extract normalized clinical trial registry IDs from title or abstract."""
    if not text:
        return []
    matches = _TRIAL_ID_RE.findall(text)
    return sorted({m.upper() for m in matches})


def is_study_protocol_or_design(title: str) -> bool:
    """Check if title indicates a study protocol, methodology, or design report."""
    norm = normalize_title(title)
    indicators = [
        "study protocol",
        "trial protocol",
        "rationale and design",
        "study design",
        "design and rationale",
        "methodology and design",
    ]
    return any(ind in norm for ind in indicators)
