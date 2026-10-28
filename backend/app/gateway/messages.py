"""Plain-language reasons for AI failures, shown to the reviewer next to the fallback answer."""
from __future__ import annotations

import re

from app.gateway.protocol import GatewayErrorCode

_KEY_REJECTED_RE = re.compile(
    r"api key|api_key|unauthori[sz]ed|permission|forbidden|invalid.*key|HTTP (?:401|403)", re.IGNORECASE
)
_QUOTA_RE = re.compile(r"quota|rate.?limit|resource.?exhausted|too many requests|HTTP 429", re.IGNORECASE)


def describe_gateway_failure(code: GatewayErrorCode | None, message: str | None) -> str:
    """What went wrong with an AI request, in words a reviewer can act on. No keys or URLs."""
    text = message or ""
    if code == GatewayErrorCode.DISABLED:
        return "AI is turned off, or no API key is set, so this is the paper's own text rather than a model answer."
    if code == GatewayErrorCode.RATE_LIMITED or _QUOTA_RE.search(text):
        return "The AI service's quota or rate limit was reached. Wait a little and try again, or check the plan on the API key."
    if _KEY_REJECTED_RE.search(text):
        return "The AI service rejected the API key. Check that LLM_API_KEY is correct and allowed to use this model."
    if code == GatewayErrorCode.TIMEOUT:
        return "The AI service took too long to answer. Try again."
    if code == GatewayErrorCode.UNAUTHORIZED_MODEL:
        return "The configured AI model is not on the approved list."
    if code == GatewayErrorCode.SCHEMA_VIOLATION:
        return "The AI model's answer was not in the expected format, so it was not used."
    if code == GatewayErrorCode.INJECTION_DETECTED:
        return "The request was blocked because it looked like an attempt to override the assistant's instructions."
    if code == GatewayErrorCode.BUDGET_EXCEEDED:
        return "The AI budget for this session is used up."
    if code == GatewayErrorCode.PROVIDER_ERROR:
        return "The AI service had a problem on its side. Try again in a moment."
    return "The AI model couldn't answer this request."
