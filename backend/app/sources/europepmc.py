"""Europe PMC REST API adapter for literature search and core record retrieval."""
import hashlib
import time
from datetime import UTC, datetime
from typing import Any

import httpx

from app.contracts.enums import JobState, SourceNamespace
from app.contracts.models import (
    RecordRevisionResponse,
    SearchExecutionResponse,
)
from app.settings import settings

EUROPEPMC_SEARCH_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

# Shared rate limiter
_last_epmc_request = 0.0


def _epmc_rate_limit():
    global _last_epmc_request
    now = time.time()
    elapsed = now - _last_epmc_request
    if elapsed < 0.25:
        time.sleep(0.25 - elapsed)
    _last_epmc_request = time.time()


def compute_content_hash(title: str, abstract: str | None) -> str:
    """Compute SHA-256 fingerprint over title and normalized abstract text."""
    combined = f"{title.strip()}\n{abstract.strip() if abstract else ''}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


class EuropePMCAdapter:
    """Adapter implementing Europe PMC REST API search and cursor pagination."""

    source = SourceNamespace.EUROPEPMC

    def __init__(self, http_client: httpx.Client | None = None):
        self.client = http_client or httpx.Client(timeout=httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0))

    def search_count(
        self,
        query_version_id: str,
        exact_query: str,
        synonym_expansion: bool = False,
        cap: int | None = None,
    ) -> SearchExecutionResponse:
        """Query Europe PMC for total hit count matching query."""
        if settings.ci_offline or settings.source_mode == "fixture" or settings.app_env == "test":
            from app.sources.fixture import get_fixture_search_count
            return get_fixture_search_count(
                query_version_id,
                SourceNamespace.EUROPEPMC,
                exact_query,
                cap,
                synonym_expansion=synonym_expansion,
            )

        params = {
            "query": exact_query,
            "format": "json",
            "pageSize": 1,
            "resultType": "lite",
            "synonym": "true" if synonym_expansion else "false",
        }

        _epmc_rate_limit()
        response = self.client.get(EUROPEPMC_SEARCH_URL, params=params)
        response.raise_for_status()

        data = response.json()
        hit_count = int(data.get("hitCount", 0))
        raw_hash = hashlib.sha256(response.content).hexdigest()

        return SearchExecutionResponse(
            id=f"exec-epmc-{hashlib.sha256((query_version_id + exact_query).encode()).hexdigest()[:16]}",
            query_version_id=query_version_id,
            source=SourceNamespace.EUROPEPMC,
            exact_query=exact_query,
            synonym_setting=synonym_expansion,
            hit_count=hit_count,
            counted_at=datetime.now(UTC),
            status=JobState.SUCCEEDED,
            partial=False,
            cap=cap,
            raw_hash=raw_hash,
        )

    def fetch_page(
        self,
        exact_query: str,
        cursor: str = "*",
        page_size: int = 50,
        synonym_expansion: bool = False,
    ) -> tuple[list[RecordRevisionResponse], str | None]:
        """Fetch a single page of core records with cursorMark progression. Returns (records, next_cursor)."""
        if settings.ci_offline or settings.source_mode == "fixture" or settings.app_env == "test":
            from app.sources.fixture import get_fixture_page
            return get_fixture_page(SourceNamespace.EUROPEPMC, cursor, page_size)

        params = {
            "query": exact_query,
            "format": "json",
            "resultType": "core",
            "pageSize": min(page_size, 100),
            "cursorMark": cursor,
            "synonym": "true" if synonym_expansion else "false",
        }

        _epmc_rate_limit()
        response = self.client.get(EUROPEPMC_SEARCH_URL, params=params)
        if response.status_code == 429:
            # Propagate rate limit with header
            retry_after = response.headers.get("Retry-After", "10")
            raise httpx.HTTPStatusError(
                f"Europe PMC rate limit 429; retry after {retry_after}s",
                request=response.request,
                response=response,
            )
        response.raise_for_status()

        data = response.json()
        next_cursor = data.get("nextCursorMark")
        result_list = data.get("resultList", {}).get("result", [])

        # Avoid cursor loops
        if next_cursor == cursor or not result_list:
            next_cursor = None

        records = parse_europepmc_results(result_list)
        return records, next_cursor


def parse_europepmc_results(items: list[dict[str, Any]]) -> list[RecordRevisionResponse]:
    """Parse Europe PMC core search results into normalized RecordRevisionResponse objects."""
    records: list[RecordRevisionResponse] = []

    for item in items:
        source_ns = (item.get("source") or "epmc").lower()
        external_id = item.get("id") or item.get("pmid") or item.get("pmcid")
        if not external_id:
            continue

        raw_title = item.get("title") or "Untitled Record"
        title = raw_title.strip()
        if title.endswith("."):
            title = title[:-1].strip()

        abstract_text = item.get("abstractText")
        doi = (item.get("doi") or "").lower() or None
        pmid = item.get("pmid")

        # Authors
        authors = []
        author_string = item.get("authorString")
        if author_string:
            authors = [a.strip() for a in author_string.split(",") if a.strip()]

        # Year
        pub_year = item.get("pubYear")
        year: int | None = None
        if pub_year:
            try:
                year = int(pub_year)
            except ValueError:
                pass

        # Journal / Book
        journal_info = item.get("journalInfo") or {}
        journal = journal_info.get("journal", {}).get("title") or item.get("bookOrReportDetails", {}).get("publisher")
        pages = item.get("pageInfo")

        # Languages
        languages = []
        lang = item.get("language")
        if lang:
            languages = [lang]

        # Pub types
        pub_types = item.get("pubTypeList", {}).get("pubType", [])
        if isinstance(pub_types, str):
            pub_types = [pub_types]

        content_hash = compute_content_hash(title, abstract_text)

        rec = RecordRevisionResponse(
            id=f"rev-epmc-{source_ns}-{external_id}",
            source_record_id=f"src-epmc-{source_ns}-{external_id}",
            source=SourceNamespace.EUROPEPMC,
            source_namespace=source_ns,
            external_id=str(external_id),
            content_hash=content_hash,
            title=title,
            abstract_text=abstract_text,
            structured_sections=None,
            authors=authors,
            year=year,
            journal=journal,
            pages=pages,
            language=languages,
            publication_types=pub_types,
            doi=doi,
            pmid=pmid,
            metadata_json={"raw_source": "europepmc_core", "citedByCount": item.get("citedByCount")},
            fetched_at=datetime.now(UTC),
        )
        records.append(rec)

    return records
