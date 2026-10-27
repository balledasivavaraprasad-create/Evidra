"""PubMed E-Utilities adapter for live and fixture search and record retrieval."""
import hashlib
import re
import time
from datetime import UTC, datetime

import defusedxml.ElementTree as ET
import httpx

from app.contracts.enums import JobState, SourceNamespace
from app.contracts.models import (
    RecordRevisionResponse,
    SearchExecutionResponse,
    StructuredSection,
)
from app.settings import settings

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
TOOL_NAME = "EvidraReviewEngine"
CONTACT_EMAIL = "evidra-review@example.org"

# Shared rate limiter (minimum 350ms between requests = < 3 req/sec)
_last_request_time = 0.0


def _rate_limit_pause():
    global _last_request_time
    now = time.time()
    elapsed = now - _last_request_time
    if elapsed < 0.35:
        time.sleep(0.35 - elapsed)
    _last_request_time = time.time()


def compute_content_hash(title: str, abstract: str | None) -> str:
    """Compute SHA-256 fingerprint over title and normalized abstract text."""
    combined = f"{title.strip()}\n{abstract.strip() if abstract else ''}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


class PubMedAdapter:
    """Adapter implementing PubMed E-Utilities ESearch and EFetch protocols."""

    source = SourceNamespace.PUBMED

    def __init__(self, http_client: httpx.Client | None = None):
        self.client = http_client or httpx.Client(timeout=httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0))

    def search_count(
        self,
        query_version_id: str,
        exact_query: str,
        cap: int | None = None,
    ) -> SearchExecutionResponse:
        """Query ESearch for total hit count matching exact query string."""
        if settings.ci_offline or settings.source_mode == "fixture" or settings.app_env == "test":
            from app.sources.fixture import get_fixture_search_count
            return get_fixture_search_count(query_version_id, SourceNamespace.PUBMED, exact_query, cap)

        params = {
            "db": "pubmed",
            "term": exact_query,
            "retmode": "json",
            "rettype": "count",
            "tool": TOOL_NAME,
            "email": CONTACT_EMAIL,
        }

        _rate_limit_pause()
        response = self.client.get(ESEARCH_URL, params=params)
        response.raise_for_status()

        data = response.json()
        esearchresult = data.get("esearchresult", {})
        count_str = esearchresult.get("count", "0")
        hit_count = int(count_str)

        raw_hash = hashlib.sha256(response.content).hexdigest()

        return SearchExecutionResponse(
            id=f"exec-pubmed-{hashlib.sha256((query_version_id + exact_query).encode()).hexdigest()[:16]}",
            query_version_id=query_version_id,
            source=SourceNamespace.PUBMED,
            exact_query=exact_query,
            synonym_setting=False,
            hit_count=hit_count,
            counted_at=datetime.now(UTC),
            status=JobState.SUCCEEDED,
            partial=False,
            cap=cap,
            raw_hash=raw_hash,
        )

    def fetch_ids_for_execution(
        self,
        exact_query: str,
        retmax: int = 200,
        retstart: int = 0,
    ) -> list[str]:
        """Fetch PMIDs list for a search execution."""
        if settings.ci_offline or settings.source_mode == "fixture" or settings.app_env == "test":
            from app.sources.fixture import get_fixture_ids
            return get_fixture_ids(SourceNamespace.PUBMED, retmax, retstart)

        params = {
            "db": "pubmed",
            "term": exact_query,
            "retmode": "json",
            "retmax": retmax,
            "retstart": retstart,
            "sort": "pub_date",
            "tool": TOOL_NAME,
            "email": CONTACT_EMAIL,
        }

        _rate_limit_pause()
        response = self.client.get(ESEARCH_URL, params=params)
        response.raise_for_status()

        data = response.json()
        return data.get("esearchresult", {}).get("idlist", [])

    def fetch_records_by_pmids(
        self,
        pmids: list[str],
    ) -> list[RecordRevisionResponse]:
        """Fetch XML record revisions for given PMIDs using EFetch and defusedxml."""
        if not pmids:
            return []

        if settings.ci_offline or settings.source_mode == "fixture" or settings.app_env == "test":
            from app.sources.fixture import get_fixture_records
            return get_fixture_records(SourceNamespace.PUBMED, pmids)

        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "tool": TOOL_NAME,
            "email": CONTACT_EMAIL,
        }

        _rate_limit_pause()
        response = self.client.get(EFETCH_URL, params=params)
        response.raise_for_status()

        return parse_pubmed_xml(response.content)


def parse_pubmed_xml(xml_bytes: bytes) -> list[RecordRevisionResponse]:
    """Parse PubMed XML safely using defusedxml into normalized RecordRevisionResponse objects."""
    root = ET.fromstring(xml_bytes)
    articles = root.findall(".//PubmedArticle")
    records: list[RecordRevisionResponse] = []

    for article in articles:
        citation = article.find("MedlineCitation")
        if citation is None:
            continue

        pmid_elem = citation.find("PMID")
        pmid = pmid_elem.text.strip() if pmid_elem is not None and pmid_elem.text else None
        if not pmid:
            continue

        art_elem = citation.find("Article")
        if art_elem is None:
            continue

        # Title
        title_elem = art_elem.find("ArticleTitle")
        title = "".join(title_elem.itertext()).strip() if title_elem is not None else "Untitled Record"
        if title.endswith("."):
            title = title[:-1].strip()

        # Abstract assembly (handle structured vs unstructured)
        abstract_elem = art_elem.find("Abstract")
        abstract_text: str | None = None
        structured_sections: list[StructuredSection] | None = None

        if abstract_elem is not None:
            sections = []
            section_models = []
            for text_elem in abstract_elem.findall("AbstractText"):
                sec_text = "".join(text_elem.itertext()).strip()
                label = text_elem.get("Label")
                if label:
                    sections.append(f"{label}: {sec_text}")
                    section_models.append(StructuredSection(label=label, text=sec_text))
                else:
                    sections.append(sec_text)

            if sections:
                abstract_text = "\n\n".join(sections)
            if section_models:
                structured_sections = section_models

        # Authors
        authors = []
        author_list = art_elem.find("AuthorList")
        if author_list is not None:
            for auth in author_list.findall("Author"):
                col = auth.find("CollectiveName")
                if col is not None and col.text:
                    authors.append(col.text.strip())
                    continue
                last = auth.find("LastName")
                fore = auth.find("ForeName")
                if fore is None:
                    fore = auth.find("Initials")
                last_str = last.text.strip() if last is not None and last.text else ""
                fore_str = fore.text.strip() if fore is not None and fore.text else ""
                full_name = f"{last_str} {fore_str}".strip()
                if full_name:
                    authors.append(full_name)

        # Journal and Year
        journal_elem = art_elem.find("Journal")
        journal_title = None
        year: int | None = None
        if journal_elem is not None:
            jt = journal_elem.find("Title")
            if jt is None:
                jt = journal_elem.find("ISOAbbreviation")
            if jt is not None and jt.text:
                journal_title = jt.text.strip()

            pub_date = journal_elem.find(".//PubDate")
            if pub_date is not None:
                yr_elem = pub_date.find("Year")
                if yr_elem is not None and yr_elem.text:
                    try:
                        year = int(yr_elem.text.strip())
                    except ValueError:
                        pass
                elif pub_date.find("MedlineDate") is not None:
                    med_date = pub_date.find("MedlineDate").text or ""
                    m = re.search(r"\b(19\d\d|20\d\d)\b", med_date)
                    if m:
                        year = int(m.group(1))

        # Pages / Pagination
        pages = None
        pagination = art_elem.find(".//Pagination/MedlinePgn")
        if pagination is not None and pagination.text:
            pages = pagination.text.strip()

        # Languages
        languages = []
        for lang_elem in art_elem.findall("Language"):
            if lang_elem.text:
                languages.append(lang_elem.text.strip())

        # Publication types
        pub_types = []
        for pt_elem in art_elem.findall(".//PublicationTypeList/PublicationType"):
            if pt_elem.text:
                pub_types.append(pt_elem.text.strip())

        # DOI extraction
        doi = None
        for eloc in art_elem.findall("ELocationID"):
            if eloc.get("EIdType") == "doi" and eloc.text:
                doi = eloc.text.strip().lower()
                break
        if not doi:
            for art_id in article.findall(".//PubmedData/ArticleIdList/ArticleId"):
                if art_id.get("IdType") == "doi" and art_id.text:
                    doi = art_id.text.strip().lower()
                    break

        content_hash = compute_content_hash(title, abstract_text)

        record = RecordRevisionResponse(
            id=f"rev-pubmed-{pmid}",
            source_record_id=f"src-pubmed-{pmid}",
            source=SourceNamespace.PUBMED,
            source_namespace="pubmed",
            external_id=pmid,
            content_hash=content_hash,
            title=title,
            abstract_text=abstract_text,
            structured_sections=structured_sections,
            authors=authors,
            year=year,
            journal=journal_title,
            pages=pages,
            language=languages,
            publication_types=pub_types,
            doi=doi,
            pmid=pmid,
            metadata_json={"raw_source": "pubmed_efetch"},
            fetched_at=datetime.now(UTC),
        )
        records.append(record)

    return records
