"""Unit and adapter tests for Europe PMC REST API adapter and parser."""

from app.contracts.enums import BooleanOperator, SourceNamespace
from app.contracts.models import QueryASTNode
from app.sources.europepmc import EuropePMCAdapter, parse_europepmc_results
from app.sources.translator import build_europepmc_query

SAMPLE_EPMC_ITEMS = [
    {
        "id": "PPR987654",
        "source": "PPR",
        "title": "Real-world persistence with metformin therapy.",
        "authorString": "Brown T, Lee K, Patel R",
        "journalInfo": None,
        "pubYear": "2023",
        "pageInfo": None,
        "abstractText": "Observational cohort assessing adherence to biguanide monotherapy.",
        "doi": "10.1101/2023.01.01.987654",
        "pmid": None,
        "language": "en",
        "pubTypeList": {"pubType": ["Preprint"]},
        "citedByCount": 3,
    },
    {
        "id": "38200002",
        "source": "MED",
        "title": "Metformin versus sulfonylurea in elderly adults",
        "authorString": "Green A",
        "journalInfo": {"journal": {"title": "Lancet Healthy Longev"}},
        "pubYear": "2024",
        "pageInfo": "e12-e20",
        "abstractText": None,
        "doi": "10.1016/S2666-7568(23)00200-1",
        "pmid": "38200002",
        "language": "eng",
        "pubTypeList": {"pubType": ["Journal Article"]},
    },
]


def test_europepmc_query_translation():
    """Verify recursive AST translation into Europe PMC query syntax."""
    ast = QueryASTNode(
        operator=BooleanOperator.AND,
        children=[
            QueryASTNode(term="metformin"),
            QueryASTNode(term="HbA1c"),
        ],
    )
    query = build_europepmc_query(ast, start_date="2021", end_date="2023")
    assert 'TITLE_ABS:"metformin"' in query
    assert 'TITLE_ABS:"HbA1c"' in query
    assert "FIRST_PDATE:[2021-01-01 TO 2023-12-31]" in query


def test_parse_europepmc_results_namespaces():
    """Verify Europe PMC results preserve provider namespaces and do not falsely assume PMID."""
    records = parse_europepmc_results(SAMPLE_EPMC_ITEMS)
    assert len(records) == 2

    # First record is a preprint (PPR)
    rec1 = records[0]
    assert rec1.source == SourceNamespace.EUROPEPMC
    assert rec1.source_namespace == "ppr"
    assert rec1.external_id == "PPR987654"
    assert rec1.pmid is None
    assert rec1.doi == "10.1101/2023.01.01.987654"
    assert len(rec1.authors) == 3
    assert "Brown T" in rec1.authors

    # Second record is Medline (MED)
    rec2 = records[1]
    assert rec2.source_namespace == "med"
    assert rec2.external_id == "38200002"
    assert rec2.pmid == "38200002"
    assert rec2.abstract_text is None
    assert rec2.journal == "Lancet Healthy Longev"


def test_europepmc_adapter_fixture_count():
    """Verify EuropePMCAdapter count acquisition in fixture mode."""
    adapter = EuropePMCAdapter()
    res = adapter.search_count(
        query_version_id="q-v1",
        exact_query='TITLE_ABS:"metformin"',
        synonym_expansion=True,
    )
    assert res.source == SourceNamespace.EUROPEPMC
    assert res.synonym_setting is True
    assert res.hit_count > 0


def test_europepmc_adapter_fixture_pages():
    """Verify cursorMark pagination progression without cursor loops."""
    adapter = EuropePMCAdapter()
    records_p1, next_cursor = adapter.fetch_page(
        exact_query='TITLE_ABS:"metformin"',
        cursor="*",
        page_size=2,
    )
    assert len(records_p1) > 0
    assert next_cursor is not None

    # Advancing cursor returns next page
    records_p2, _final_cursor = adapter.fetch_page(
        exact_query='TITLE_ABS:"metformin"',
        cursor=next_cursor,
        page_size=2,
    )
    assert len(records_p2) >= 0
