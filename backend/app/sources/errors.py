"""Errors raised when a literature source can't be reached or answers badly."""
from __future__ import annotations

import httpx

SOURCE_LABELS = {"pubmed": "PubMed", "europepmc": "Europe PMC"}


class SourceUnavailableError(Exception):
    """A literature source did not respond usefully. Shown to the reviewer, so keep it plain."""

    def __init__(self, source: str, reason: str) -> None:
        self.source = source
        self.label = SOURCE_LABELS.get(source, source)
        self.reason = reason
        super().__init__(f"{self.label} didn't respond: {reason}")


def describe_source_error(exc: Exception) -> str:
    """A short, human reason for an HTTP or parsing failure, with no URLs or keys in it."""
    if isinstance(exc, httpx.TimeoutException):
        return "the request timed out"
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        return "too many requests, try again in a moment" if code == 429 else f"it answered with HTTP {code}"
    if isinstance(exc, httpx.ConnectError):
        return "could not connect"
    if isinstance(exc, httpx.HTTPError):
        return f"a network error ({type(exc).__name__})"
    return "its answer could not be read"
