"""Direct approved-provider HTTPX adapter and protocol-compatible mock adapter (C05)."""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import httpx

from app.gateway.protocol import (
    GatewayErrorCode,
    GatewayRequest,
    GatewayResponse,
    ModelGatewayProtocol,
)
from app.gateway.sanitizer import detect_prompt_injection
from app.settings import settings

logger = logging.getLogger(__name__)

ALLOWLISTED_TASKS: set[str] = {
    "pico_extraction",
    "screening_explanation",
    "corpus_qa",
    "keyword_synonyms",
}

ALLOWLISTED_MODELS: set[str] = {
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-2.5-flash",
    "gemini-3.8-flash",
    "gpt-4o-mini",
    "mock-research-model",
}

MOCK_MODEL = "mock-research-model"

MAX_PROMPT_CHARS = 50_000
MAX_MAX_TOKENS = 4_000


def _strip_code_fence(text: str) -> str:
    """Providers often wrap JSON in a ```json fence; the JSON inside is what we validate."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[1] if "\n" in stripped else ""
        if stripped.rstrip().endswith("```"):
            stripped = stripped.rstrip()[:-3]
    return stripped.strip()


class HTTPXModelAdapter(ModelGatewayProtocol):
    """Secure, policy-enforced HTTPX adapter connecting to approved model endpoints.
    
    Invariants:
    - Server-side credentials only (never sent to client).
    - Enforces timeout, max payload size, allowlisted tasks and models.
    - Max 1 bounded retry on transient 5xx/429; no fallback to unapproved providers.
    - AI outage or policy failure fails closed, enabling deterministic rules fallback.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        default_model: str = "mock-research-model",
        max_daily_budget_tokens: int = 50_000,
        enforce_llm_flag: bool = True,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        # An explicit argument wins, then the process environment, then settings (which also
        # read the repo-root .env.local). The key is only ever sent to the provider.
        self.base_url = (base_url or os.environ.get("LLM_BASE_URL") or settings.llm_base_url).rstrip("/")
        self.api_key = api_key or os.environ.get("LLM_API_KEY") or settings.llm_api_key or ""
        self.default_model = default_model
        self.max_daily_budget_tokens = max_daily_budget_tokens
        self.enforce_llm_flag = enforce_llm_flag
        self._tokens_used = 0
        self._transport = transport

    def is_enabled(self) -> bool:
        """Check whether LLM requests are permitted by environment policy and credentials."""
        if self.enforce_llm_flag:
            env_value = os.environ.get("LLM_ENABLED")
            llm_enabled = (
                env_value.lower() in ("true", "1", "yes") if env_value is not None else bool(settings.llm_enabled)
            )
            if not llm_enabled:
                return False
        # Enabled by flag: a real provider also needs its key. With no key AI is reported disabled.
        return bool(self.api_key or "mock" in self.base_url)

    def get_remaining_budget(self) -> int:
        return max(0, self.max_daily_budget_tokens - self._tokens_used)

    def invoke(self, request: GatewayRequest) -> GatewayResponse:
        """Execute request under strict budget, security guardrails, and network boundaries."""
        start_time = time.perf_counter()

        # 1. Availability check
        if not self.is_enabled():
            return GatewayResponse(
                success=False,
                error_code=GatewayErrorCode.DISABLED,
                error_message="AI features are disabled by policy or missing credentials. Rules and manual review active.",
                fallback_used=True,
                latency_ms=(time.perf_counter() - start_time) * 1000,
            )

        # 2. Allowlisted task check
        if request.task_name not in ALLOWLISTED_TASKS:
            return GatewayResponse(
                success=False,
                error_code=GatewayErrorCode.EXECUTION_ERROR,
                error_message=f"Unauthorized AI task '{request.task_name}'. Allowed: {sorted(ALLOWLISTED_TASKS)}",
                fallback_used=True,
                latency_ms=(time.perf_counter() - start_time) * 1000,
            )

        # 3. Allowlisted model check
        model_name = request.model_alias or self.default_model
        if model_name not in ALLOWLISTED_MODELS:
            return GatewayResponse(
                success=False,
                error_code=GatewayErrorCode.UNAUTHORIZED_MODEL,
                error_message=f"Unauthorized model '{model_name}'. Allowed: {sorted(ALLOWLISTED_MODELS)}",
                fallback_used=True,
                latency_ms=(time.perf_counter() - start_time) * 1000,
            )

        # 4. Payload size check
        serialized_context = json.dumps(request.prompt_context)
        if len(serialized_context) > MAX_PROMPT_CHARS:
            return GatewayResponse(
                success=False,
                error_code=GatewayErrorCode.PAYLOAD_TOO_LARGE,
                error_message=f"Prompt context size ({len(serialized_context)} chars) exceeds maximum allowed ({MAX_PROMPT_CHARS}).",
                fallback_used=True,
                latency_ms=(time.perf_counter() - start_time) * 1000,
            )

        # 5. Token budget reservation check
        requested_tokens = min(request.max_tokens, MAX_MAX_TOKENS)
        if self._tokens_used + requested_tokens > self.max_daily_budget_tokens:
            return GatewayResponse(
                success=False,
                error_code=GatewayErrorCode.BUDGET_EXCEEDED,
                error_message=f"Budget exceeded. Used {self._tokens_used}/{self.max_daily_budget_tokens} tokens.",
                fallback_used=True,
                latency_ms=(time.perf_counter() - start_time) * 1000,
            )

        # 6. Prompt injection guardrail
        is_suspicious, desc = detect_prompt_injection(serialized_context)
        if is_suspicious:
            logger.warning("Gateway: Blocked prompt injection pattern: %s", desc)
            return GatewayResponse(
                success=False,
                error_code=GatewayErrorCode.INJECTION_DETECTED,
                error_message=f"Suspicious prompt pattern rejected: {desc}",
                fallback_used=True,
                latency_ms=(time.perf_counter() - start_time) * 1000,
            )

        # 6b. The mock model is for tests: never send it to a real endpoint
        if model_name == MOCK_MODEL and "mock" not in self.base_url and self._transport is None:
            return GatewayResponse(
                success=False,
                error_code=GatewayErrorCode.UNAUTHORIZED_MODEL,
                error_message="The mock model cannot be used with a real endpoint. Set LLM_MODEL_ALIAS to an approved model.",
                fallback_used=True,
                latency_ms=(time.perf_counter() - start_time) * 1000,
            )

        # 7. Outbound HTTP dispatch with at most 1 retry
        endpoint = f"{self.base_url}/chat/completions"
        # The key goes in the header only; it is never logged or returned in an error message
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": f"Task: {request.task_name}. Output valid JSON strictly conforming to schema."},
                {"role": "user", "content": serialized_context},
            ],
            "max_tokens": requested_tokens,
            "temperature": 0.0,  # Zero temperature for deterministic extraction
        }

        attempts = 0
        last_error_code = GatewayErrorCode.EXECUTION_ERROR
        last_error_msg = "Unknown error"

        while attempts < 2:
            attempts += 1
            try:
                with httpx.Client(timeout=request.timeout_seconds, transport=self._transport) as client:
                    resp = client.post(endpoint, headers=headers, json=body)

                if resp.status_code == 200:
                    data = resp.json()
                    # Extract message content
                    content_str = data["choices"][0]["message"]["content"]
                    usage = data.get("usage", {})
                    tokens_used = usage.get("total_tokens", requested_tokens)
                    self._tokens_used += tokens_used

                    # Parse JSON content
                    try:
                        parsed_payload = json.loads(_strip_code_fence(content_str))
                    except (json.JSONDecodeError, ValueError, TypeError) as json_err:
                        return GatewayResponse(
                            success=False,
                            error_code=GatewayErrorCode.SCHEMA_VIOLATION,
                            error_message=f"Model output is not valid JSON: {json_err}",
                            fallback_used=True,
                            latency_ms=(time.perf_counter() - start_time) * 1000,
                        )

                    return GatewayResponse(
                        success=True,
                        data=parsed_payload,
                        tokens_consumed=tokens_used,
                        latency_ms=(time.perf_counter() - start_time) * 1000,
                        metadata={"model": model_name, "attempts": attempts},
                    )

                elif resp.status_code == 429:
                    last_error_code = GatewayErrorCode.RATE_LIMITED
                    last_error_msg = f"Rate limited by provider (HTTP 429): {resp.text[:200]}"
                    if attempts < 2:
                        time.sleep(0.5)
                        continue

                elif resp.status_code >= 500:
                    last_error_code = GatewayErrorCode.PROVIDER_ERROR
                    last_error_msg = f"Provider server error (HTTP {resp.status_code}): {resp.text[:200]}"
                    if attempts < 2:
                        time.sleep(0.5)
                        continue

                else:
                    return GatewayResponse(
                        success=False,
                        error_code=GatewayErrorCode.EXECUTION_ERROR,
                        error_message=f"HTTP {resp.status_code}: {resp.text[:200]}",
                        fallback_used=True,
                        latency_ms=(time.perf_counter() - start_time) * 1000,
                    )

            except httpx.TimeoutException:
                last_error_code = GatewayErrorCode.TIMEOUT
                last_error_msg = f"Request timed out after {request.timeout_seconds}s"
            except (httpx.RequestError, OSError, RuntimeError) as exc:
                last_error_code = GatewayErrorCode.EXECUTION_ERROR
                last_error_msg = f"Connection failure: {exc}"

        return GatewayResponse(
            success=False,
            error_code=last_error_code,
            error_message=last_error_msg,
            fallback_used=True,
            latency_ms=(time.perf_counter() - start_time) * 1000,
        )


class MockModelAdapter(ModelGatewayProtocol):
    """Protocol-compatible deterministic mock adapter for testing."""

    def __init__(
        self,
        enabled: bool = True,
        max_daily_budget_tokens: int = 50_000,
        canned_response: dict[str, Any] | None = None,
        force_error_code: GatewayErrorCode | None = None,
    ) -> None:
        self.enabled = enabled
        self.max_daily_budget_tokens = max_daily_budget_tokens
        self.canned_response = canned_response
        self.force_error_code = force_error_code
        self._tokens_used = 0

    def is_enabled(self) -> bool:
        return self.enabled

    def invoke(self, request: GatewayRequest) -> GatewayResponse:
        start_time = time.perf_counter()

        if not self.enabled:
            return GatewayResponse(
                success=False,
                error_code=GatewayErrorCode.DISABLED,
                error_message="Mock adapter disabled.",
                fallback_used=True,
                latency_ms=(time.perf_counter() - start_time) * 1000,
            )

        if self.force_error_code:
            return GatewayResponse(
                success=False,
                error_code=self.force_error_code,
                error_message=f"Simulated error: {self.force_error_code.value}",
                fallback_used=True,
                latency_ms=(time.perf_counter() - start_time) * 1000,
            )

        # Check prompt injection
        is_suspicious, desc = detect_prompt_injection(json.dumps(request.prompt_context))
        if is_suspicious:
            return GatewayResponse(
                success=False,
                error_code=GatewayErrorCode.INJECTION_DETECTED,
                error_message=f"Suspicious pattern detected: {desc}",
                fallback_used=True,
                latency_ms=(time.perf_counter() - start_time) * 1000,
            )

        # Check task
        if request.task_name not in ALLOWLISTED_TASKS:
            return GatewayResponse(
                success=False,
                error_code=GatewayErrorCode.EXECUTION_ERROR,
                error_message="Unauthorized task",
                fallback_used=True,
                latency_ms=(time.perf_counter() - start_time) * 1000,
            )

        tokens = min(request.max_tokens, 150)
        self._tokens_used += tokens

        response_data = self.canned_response or {"status": "ok", "mock_extracted": True}
        return GatewayResponse(
            success=True,
            data=response_data,
            tokens_consumed=tokens,
            latency_ms=(time.perf_counter() - start_time) * 1000,
            metadata={"mock": True},
        )
