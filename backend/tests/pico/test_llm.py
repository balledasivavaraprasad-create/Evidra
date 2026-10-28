"""Unit tests for optional LLM PICO extractor with offset validation and fallback (C05)."""
from app.gateway.adapter import MockModelAdapter
from app.gateway.protocol import GatewayErrorCode, GatewayRequest, GatewayResponse
from app.pico.llm import LLMPicoExtractor, find_quote_offsets


def test_find_quote_offsets_multiple_and_single():
    text = "Metformin was compared to placebo. Another placebo group received diet."
    offsets = find_quote_offsets(text, "placebo")
    assert len(offsets) == 2
    assert text[offsets[0][0] : offsets[0][1]] == "placebo"
    assert text[offsets[1][0] : offsets[1][1]] == "placebo"


def test_llm_extractor_disabled_falls_back_to_rules():
    """When gateway is disabled, LLMPicoExtractor seamlessly uses rule extractor."""
    mock_gateway = MockModelAdapter(enabled=False)
    extractor = LLMPicoExtractor(gateway=mock_gateway)

    text = "A randomized trial of metformin versus placebo in adults with type 2 diabetes measuring HbA1c."
    res = extractor.extract_from_text(text, record_revision_id="rec-01")

    assert res is not None
    assert res.record_revision_id == "rec-01"
    # Rule extractor extracts intervention/comparator/outcome/population
    assert res.has_intervention is True
    assert res.has_comparator is True
    assert res.has_population is True


def test_llm_extractor_valid_spans_extracted():
    """Valid LLM response with exact quotes and offsets builds valid PicoResult."""
    text = "Adults with type 2 diabetes were randomized to metformin or placebo."
    canned = {
        "spans": [
            {
                "label": "P",
                "quote": "Adults with type 2 diabetes",
                "start_cp": 0,
                "end_cp": 27,
            },
            {
                "label": "I",
                "quote": "metformin",
                "start_cp": 47,
                "end_cp": 56,
            },
            {
                "label": "C",
                "quote": "placebo",
                "start_cp": 60,
                "end_cp": 67,
            },
        ]
    }
    mock_gateway = MockModelAdapter(enabled=True, canned_response=canned)
    extractor = LLMPicoExtractor(gateway=mock_gateway, model_alias="mock-research-model")

    res = extractor.extract_from_text(text, record_revision_id="rec-02")
    assert len(res.spans) == 3
    assert res.has_population is True
    assert res.has_intervention is True
    assert res.has_comparator is True
    for s in res.spans:
        assert text[s.start_cp : s.end_cp] == s.quote
        assert s.provenance == "llm:mock-research-model"


def test_llm_extractor_forged_quote_rejected_and_falls_back():
    """Hallucinated quote not present in abstract is rejected; rules fall back."""
    text = "Trial of insulin glargine in diabetic patients."
    canned = {
        "spans": [
            {
                "label": "I",
                "quote": "FABRICATED_DRUG_NAME_NOT_IN_TEXT",
                "start_cp": 0,
                "end_cp": 10,
            }
        ]
    }
    mock_gateway = MockModelAdapter(enabled=True, canned_response=canned)
    extractor = LLMPicoExtractor(gateway=mock_gateway)

    res = extractor.extract_from_text(text, record_revision_id="rec-03")
    # All LLM spans were invalid, so fallback rule extractor was used
    for s in res.spans:
        assert s.quote != "FABRICATED_DRUG_NAME_NOT_IN_TEXT"


def test_llm_extractor_resolves_unique_quote_when_offsets_missing():
    """If quote appears uniquely in text, missing offsets are automatically resolved."""
    text = "Patients received dapagliflozin daily."
    quote = "dapagliflozin"
    expected_start = text.index(quote)
    expected_end = expected_start + len(quote)

    canned = {
        "spans": [
            {
                "label": "I",
                "quote": quote,
                "start_cp": None,
                "end_cp": None,
            }
        ]
    }
    mock_gateway = MockModelAdapter(enabled=True, canned_response=canned)
    extractor = LLMPicoExtractor(gateway=mock_gateway)

    res = extractor.extract_from_text(text, record_revision_id="rec-04")
    assert len(res.spans) == 1
    assert res.spans[0].start_cp == expected_start
    assert res.spans[0].end_cp == expected_end
    assert text[res.spans[0].start_cp : res.spans[0].end_cp] == quote


def test_llm_extractor_gateway_error_uses_rule_fallback():
    """Rate limit or network error triggers clean rule-based fallback without throwing."""
    mock_gateway = MockModelAdapter(
        enabled=True,
        force_error_code=GatewayErrorCode.RATE_LIMITED,
    )
    extractor = LLMPicoExtractor(gateway=mock_gateway)

    text = "Evaluating metformin in type 2 diabetes mellitus versus placebo."
    res = extractor.extract_from_text(text, record_revision_id="rec-05")
    assert res is not None
    assert res.has_intervention is True  # extracted by rule fallback


class StatefulRepairMockGateway(MockModelAdapter):
    """Simulates an initial flawed response followed by a repaired response."""

    def __init__(self, first_resp: dict, second_resp: dict) -> None:
        super().__init__(enabled=True)
        self.first_resp = first_resp
        self.second_resp = second_resp
        self.call_count = 0

    def invoke(self, request: GatewayRequest) -> GatewayResponse:
        self.call_count += 1
        data = self.first_resp if self.call_count == 1 else self.second_resp
        return GatewayResponse(
            success=True,
            data=data,
            tokens_consumed=100,
        )


def test_llm_extractor_repair_flow():
    """Extractor attempts at most one repair when initial quotes have ambiguity or invalid labels."""
    text = "Patients in group A received placebo, while group B also received placebo."
    # Quote "placebo" appears twice, but initial response had invalid label "INVALID_XYZ"
    flawed = {
        "spans": [
            {
                "label": "INVALID_XYZ",
                "quote": "placebo",
                "start_cp": 30,
                "end_cp": 37,
            }
        ]
    }
    repaired = {
        "spans": [
            {
                "label": "C",
                "quote": "placebo",
                "start_cp": 29,
                "end_cp": 36,
            }
        ]
    }

    mock_gateway = StatefulRepairMockGateway(first_resp=flawed, second_resp=repaired)
    extractor = LLMPicoExtractor(gateway=mock_gateway)

    res = extractor.extract_from_text(text, record_revision_id="rec-06")
    assert mock_gateway.call_count == 2  # initial + repair
    assert len(res.spans) == 1
    assert res.spans[0].quote == "placebo"
    assert res.spans[0].start_cp == 29
    assert res.spans[0].end_cp == 36
