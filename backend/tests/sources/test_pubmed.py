"""Unit and adapter tests for PubMed source adapter and E-Utilities parser."""

from app.contracts.enums import BooleanOperator, SourceNamespace
from app.contracts.models import QueryASTNode
from app.sources.pubmed import PubMedAdapter, compute_content_hash, parse_pubmed_xml
from app.sources.translator import build_pubmed_query

SAMPLE_PUBMED_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE PubmedArticleSet PUBLIC "-//NLM//DTD PubMedArticle, 1st January 2024//EN" "https://dtd.nlm.nih.gov/ncbi/pubmed/out/pubmed_240101.dtd">
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation Status="MEDLINE">
      <PMID Version="1">38100100</PMID>
      <Article PubModel="Print-Electronic">
        <Journal>
          <JournalIssue>
            <PubDate>
              <Year>2024</Year>
              <Month>Feb</Month>
            </PubDate>
          </JournalIssue>
          <Title>Diabetes Care</Title>
        </Journal>
        <ArticleTitle>Comparative efficacy of metformin in adults with type 2 diabetes.</ArticleTitle>
        <Pagination>
          <MedlinePgn>245-253</MedlinePgn>
        </Pagination>
        <Abstract>
          <AbstractText Label="OBJECTIVE">To evaluate glycemic control under metformin monotherapy.</AbstractText>
          <AbstractText Label="METHODS">A double-blind randomized clinical trial was performed.</AbstractText>
          <AbstractText Label="RESULTS">Metformin reduced HbA1c by 1.1% compared with placebo.</AbstractText>
        </Abstract>
        <AuthorList CompleteYN="Y">
          <Author ValidYN="Y">
            <LastName>Smith</LastName>
            <ForeName>John</ForeName>
          </Author>
          <Author ValidYN="Y">
            <CollectiveName>The MET-Study Investigators</CollectiveName>
          </Author>
        </AuthorList>
        <Language>eng</Language>
        <PublicationTypeList>
          <PublicationType>Randomized Controlled Trial</PublicationType>
        </PublicationTypeList>
        <ELocationID EIdType="doi" ValidYN="Y">10.2337/dc23-0100</ELocationID>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>
"""


def test_pubmed_query_translation():
    """Verify recursive AST translation into PubMed query syntax."""
    ast = QueryASTNode(
        operator=BooleanOperator.AND,
        children=[
            QueryASTNode(term="metformin"),
            QueryASTNode(
                operator=BooleanOperator.OR,
                children=[
                    QueryASTNode(term="type 2 diabetes"),
                    QueryASTNode(term="T2D"),
                ],
            ),
        ],
    )
    query = build_pubmed_query(ast, start_date="2020", end_date="2024")
    assert '"metformin"[Title/Abstract]' in query
    assert '("type 2 diabetes"[Title/Abstract] OR "T2D"[Title/Abstract])' in query
    assert '"2020"[Date - Publication]' in query
    assert '"2024"[Date - Publication]' in query


def test_parse_pubmed_xml_structured_abstract():
    """Verify safe XML parsing of structured sections, collective authors, and DOIs."""
    records = parse_pubmed_xml(SAMPLE_PUBMED_XML)
    assert len(records) == 1
    rec = records[0]

    assert rec.external_id == "38100100"
    assert rec.pmid == "38100100"
    assert rec.doi == "10.2337/dc23-0100"
    assert rec.year == 2024
    assert rec.journal == "Diabetes Care"
    assert rec.pages == "245-253"
    assert rec.language == ["eng"]
    assert rec.publication_types == ["Randomized Controlled Trial"]

    # Authors should have both individual and collective names
    assert "Smith John" in rec.authors
    assert "The MET-Study Investigators" in rec.authors

    # Structured sections
    assert rec.abstract_text is not None
    assert "OBJECTIVE: To evaluate glycemic control" in rec.abstract_text
    assert "METHODS: A double-blind" in rec.abstract_text
    assert rec.structured_sections is not None
    assert len(rec.structured_sections) == 3
    assert rec.structured_sections[0].label == "OBJECTIVE"


def test_pubmed_content_hash_deterministic():
    """Verify identical title and abstract produce identical SHA-256 hash."""
    h1 = compute_content_hash("Title A", "Abstract text here.")
    h2 = compute_content_hash("Title A", "Abstract text here.")
    assert h1 == h2
    assert len(h1) == 64


def test_pubmed_adapter_fixture_count():
    """Verify PubMedAdapter count acquisition in fixture mode."""
    adapter = PubMedAdapter()
    res = adapter.search_count(
        query_version_id="q-v1",
        exact_query='"metformin"[Title/Abstract]',
        cap=100,
    )
    assert res.source == SourceNamespace.PUBMED
    assert res.hit_count > 0
    assert res.exact_query == '"metformin"[Title/Abstract]'
