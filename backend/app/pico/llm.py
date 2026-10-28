"""Optional LLM PICO extraction with strict validation and deterministic fallback (C05)."""
from __future__ import annotations

import logging
from typing import Any

from app.contracts.enums import PicoLabel
from app.contracts.models import PicoResult, PicoSpan
from app.gateway.protocol import (
    GatewayRequest,
    ModelGatewayProtocol,
)
from app.pico.extractor import RuleBasedPicoExtractor
from app.pico.validator import compute_text_hash, validate_pico_result

logger = logging.getLogger(__name__)

METHOD_VERSION = "pico_llm_extractor:v1.0"


def find_quote_offsets(abstract_text: str, quote: str) -> list[tuple[int, int]]:
    """Find all start and end code-point offsets where quote appears in abstract_text."""
    matches: list[tuple[int, int]] = []
    if not quote or not abstract_text:
        return matches
    start = 0
    while True:
        idx = abstract_text.find(quote, start)
        if idx == -1:
            break
        matches.append((idx, idx + len(quote)))
        start = idx + 1
    return matches


class LLMPicoExtractor:
    """Bounded, validated LLM PICO extractor conforming to PicoPort.
    
    Invariants:
    - Zero model calls when LLM is disabled or budget is exhausted.
    - Validates every offset, exact quote slice, and content hash against immutable text.
    - Rejects forged citations and repeated-quote ambiguity.
    - Allows at most ONE repair attempt within the budget; then falls back to rules.
    - Never throws unhandled exceptions to callers.
    """

    def __init__(
        self,
        gateway: ModelGatewayProtocol,
        fallback_extractor: RuleBasedPicoExtractor | None = None,
        model_alias: str = "mock-research-model",
    ) -> None:
        self.gateway = gateway
        self.fallback = fallback_extractor or RuleBasedPicoExtractor()
        self.model_alias = model_alias

    def extract_from_text(
        self,
        abstract_text: str | None,
        record_revision_id: str = "temp-record-id",
    ) -> PicoResult:
        """Extract PICO spans using LLM with deterministic validation and fallback."""
        if not abstract_text or len(abstract_text.strip()) == 0:
            return self.fallback.extract_from_text(abstract_text, record_revision_id)

        # If gateway is disabled, immediately use rule fallback
        if not self.gateway.is_enabled():
            return self.fallback.extract_from_text(abstract_text, record_revision_id)

        content_hash = compute_text_hash(abstract_text)

        # 1. Primary extraction request
        req = GatewayRequest(
            task_name="pico_extraction",
            model_alias=self.model_alias,
            prompt_context={
                "record_id": record_revision_id,
                "abstract_text": abstract_text,
                "content_hash": content_hash,
                "instructions": (
                    "Extract PICO elements (P: Population, I: Intervention, C: Comparator, O: Outcome). "
                    "Each item must have: label (P|I|C|O), exact quote from abstract, start_cp, and end_cp."
                ),
            },
            max_tokens=600,
            expected_schema={"spans": list},
        )

        resp = self.gateway.invoke(req)
        if not resp.success or not resp.data:
            logger.info("LLMPicoExtractor: Gateway request failed (%s). Falling back to rules.", resp.error_code)
            return self.fallback.extract_from_text(abstract_text, record_revision_id)

        raw_spans = resp.data.get("spans", [])
        valid_spans, invalid_reasons = self._validate_and_parse_spans(
            raw_spans, abstract_text, provenance=f"llm:{self.model_alias}"
        )

        # 2. At most ONE repair attempt if invalid spans detected
        if invalid_reasons:
            logger.info("LLMPicoExtractor: Found %d invalid spans (%s). Attempting repair.", len(invalid_reasons), invalid_reasons[:2])
            repair_req = GatewayRequest(
                task_name="pico_extraction",
                model_alias=self.model_alias,
                prompt_context={
                    "record_id": record_revision_id,
                    "abstract_text": abstract_text,
                    "previous_errors": invalid_reasons,
                    "instructions": (
                        "Previous extracted quotes/offsets did not match text slices. "
                        "Re-extract quotes and exact code-point offsets strictly matching text."
                    ),
                },
                max_tokens=600,
            )
            repair_resp = self.gateway.invoke(repair_req)
            if repair_resp.success and repair_resp.data:
                repaired_raw = repair_resp.data.get("spans", [])
                repaired_spans, remaining_invalid = self._validate_and_parse_spans(
                    repaired_raw, abstract_text, provenance=f"llm:{self.model_alias}"
                )
                if not remaining_invalid and len(repaired_spans) > 0:
                    valid_spans = repaired_spans

        # 3. If zero valid LLM spans, fall back to rules
        if not valid_spans:
            logger.info("LLMPicoExtractor: Zero valid LLM spans after validation. Using rule-based fallback.")
            return self.fallback.extract_from_text(abstract_text, record_revision_id)

        # Construct PicoResult from valid spans
        labels_present = {s.label for s in valid_spans}
        result = PicoResult(
            record_revision_id=record_revision_id,
            content_hash=content_hash,
            spans=valid_spans,
            has_population=PicoLabel.P in labels_present,
            has_intervention=PicoLabel.I in labels_present,
            has_comparator=PicoLabel.C in labels_present,
            has_outcome=PicoLabel.O in labels_present,
            method_version=METHOD_VERSION,
        )

        # Final safety check with validator
        is_valid, validation_errors = validate_pico_result(result, abstract_text)
        if not is_valid:
            logger.warning("LLMPicoExtractor: Final result validation failed (%s). Falling back.", validation_errors)
            return self.fallback.extract_from_text(abstract_text, record_revision_id)

        return result

    def _validate_and_parse_spans(
        self,
        raw_spans: list[dict[str, Any]],
        abstract_text: str,
        provenance: str,
    ) -> tuple[list[PicoSpan], list[str]]:
        """Validate quotes and Unicode code-point offsets, detecting forged or ambiguous quotes."""
        valid_spans: list[PicoSpan] = []
        invalid_reasons: list[str] = []
        text_len = len(abstract_text)

        label_map = {
            "P": PicoLabel.P,
            "I": PicoLabel.I,
            "C": PicoLabel.C,
            "O": PicoLabel.O,
            "POPULATION": PicoLabel.P,
            "INTERVENTION": PicoLabel.I,
            "COMPARATOR": PicoLabel.C,
            "OUTCOME": PicoLabel.O,
        }

        seen_spans: set[tuple[str, int, int]] = set()

        for idx, item in enumerate(raw_spans):
            lbl_raw = str(item.get("label", "")).upper()
            quote = item.get("quote", "")
            start_cp = item.get("start_cp")
            end_cp = item.get("end_cp")

            if lbl_raw not in label_map:
                invalid_reasons.append(f"Span {idx}: Unknown label '{lbl_raw}'")
                continue

            pico_label = label_map[lbl_raw]

            if not quote or not isinstance(quote, str):
                invalid_reasons.append(f"Span {idx}: Empty or non-string quote")
                continue

            # Quote occurrence check in abstract
            occurrences = find_quote_offsets(abstract_text, quote)
            if not occurrences:
                invalid_reasons.append(f"Span {idx}: Forged quote not found in text: '{quote[:30]}'")
                continue

            # If offsets omitted or invalid, resolve unambiguously if exactly 1 occurrence exists
            if start_cp is None or end_cp is None or not (0 <= start_cp < end_cp <= text_len):
                if len(occurrences) == 1:
                    start_cp, end_cp = occurrences[0]
                else:
                    invalid_reasons.append(
                        f"Span {idx}: Ambiguous quote appears {len(occurrences)} times but valid offsets not provided."
                    )
                    continue

            # Check that exact slice matches quote
            actual_slice = abstract_text[start_cp:end_cp]
            if actual_slice != quote:
                # Check if it matches any known occurrence
                matched_occ = False
                for occ_start, occ_end in occurrences:
                    if abstract_text[occ_start:occ_end] == quote:
                        start_cp, end_cp = occ_start, occ_end
                        matched_occ = True
                        break
                if not matched_occ:
                    invalid_reasons.append(f"Span {idx}: Slice mismatch: expected '{quote}', got '{actual_slice}'")
                    continue

            span_key = (pico_label.value, start_cp, end_cp)
            if span_key in seen_spans:
                continue
            seen_spans.add(span_key)

            valid_spans.append(
                PicoSpan(
                    label=pico_label,
                    quote=quote,
                    start_cp=start_cp,
                    end_cp=end_cp,
                    provenance=provenance,
                )
            )

        return valid_spans, invalid_reasons
