"""Optional AI step: extra search keywords (synonyms) for the population and intervention rules.

The model only proposes words. They are validated and shown to the reviewer as AI-suggested; they
change nothing until the reviewer saves the criteria. With AI off, or on any failure, the caller
gets no synonyms and the rules stay fully deterministic.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.gateway.adapter import HTTPXModelAdapter
from app.gateway.protocol import GatewayRequest, ModelGatewayProtocol
from app.settings import settings

MAX_SYNONYMS = 8
MAX_SYNONYM_CHARS = 60
_SAFE_TERM_RE = re.compile(r"^[\w][\w\s\-+./']*$", re.UNICODE)


@dataclass
class SynonymProvider:
    """Callable (label, keywords) -> synonyms, remembering why it produced none."""

    gateway: ModelGatewayProtocol
    model_alias: str
    problems: list[str] = field(default_factory=list)

    def __call__(self, label: str, keywords: list[str]) -> list[str]:
        response = self.gateway.invoke(
            GatewayRequest(
                task_name="keyword_synonyms",
                model_alias=self.model_alias,
                prompt_context={
                    "instruction": (
                        "List up to 8 other names, abbreviations or specific members of the same group "
                        "that a medical abstract might use for these terms. Do not repeat the given terms. "
                        'Reply as JSON: {"synonyms": ["term", ...]}.'
                    ),
                    "field": label,
                    "terms": keywords[:12],
                },
                max_tokens=1500,
                timeout_seconds=25.0,
            )
        )
        if not response.success or not isinstance(response.data, dict):
            self.problems.append(response.error_message or "The AI model gave no answer.")
            return []
        raw = response.data.get("synonyms")
        if not isinstance(raw, list):
            self.problems.append("The AI model's answer had no synonyms list.")
            return []
        known = {k.lower() for k in keywords}
        out: list[str] = []
        for item in raw:
            if not isinstance(item, str):
                continue
            term = re.sub(r"\s+", " ", item).strip()
            if (
                term
                and len(term) <= MAX_SYNONYM_CHARS
                and _SAFE_TERM_RE.match(term)
                and term.lower() not in known
                and term.lower() not in {o.lower() for o in out}
            ):
                out.append(term)
            if len(out) >= MAX_SYNONYMS:
                break
        return out


def build_synonym_provider() -> tuple[SynonymProvider | None, str | None]:
    """The provider when AI is on and configured, else (None, why not)."""
    adapter = HTTPXModelAdapter(default_model=settings.llm_model_alias)
    if not adapter.is_enabled():
        return None, None  # AI is simply off: nothing to report
    return SynonymProvider(gateway=adapter, model_alias=settings.llm_model_alias), None
