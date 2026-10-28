"""Budget enforcement and bounded fallback model gateway implementation (C03).

Provides deterministic fallback and guarantees zero model expenditures
when LLM features are disabled or budgets are exhausted.
"""
from __future__ import annotations

import logging
import os
import time

from app.gateway.protocol import (
    GatewayErrorCode,
    GatewayRequest,
    GatewayResponse,
    ModelGatewayProtocol,
)
from app.gateway.sanitizer import detect_prompt_injection

logger = logging.getLogger(__name__)


class BoundedModelGateway(ModelGatewayProtocol):
    """Secure, budget-capped model gateway honoring Level 1 offline mode."""

    def __init__(
        self,
        max_daily_budget_tokens: int = 50_000,
        enforce_llm_flag: bool = True,
    ):
        self.max_daily_budget_tokens = max_daily_budget_tokens
        self.enforce_llm_flag = enforce_llm_flag
        self._tokens_used = 0

    def is_enabled(self) -> bool:
        """Check whether LLM requests are permitted by environment policy."""
        if self.enforce_llm_flag:
            llm_enabled = os.environ.get("LLM_ENABLED", "false").lower() in ("true", "1", "yes")
            if not llm_enabled:
                return False
        return True

    def get_remaining_budget(self) -> int:
        return max(0, self.max_daily_budget_tokens - self._tokens_used)

    def invoke(self, request: GatewayRequest) -> GatewayResponse:
        """Execute request under strict budget, injection, and availability constraints."""
        start_time = time.perf_counter()

        # 1. Check availability
        if not self.is_enabled():
            logger.info("Gateway: AI disabled by policy. Yielding deterministic fallback.")
            return GatewayResponse(
                success=False,
                error_code=GatewayErrorCode.DISABLED,
                error_message="AI features are disabled (LLM_ENABLED=false). Rules and manual review active.",
                fallback_used=True,
                latency_ms=(time.perf_counter() - start_time) * 1000,
            )

        # 2. Check budget
        if self._tokens_used + request.max_tokens > self.max_daily_budget_tokens:
            logger.warning("Gateway: Daily token budget exceeded (%d / %d)", self._tokens_used, self.max_daily_budget_tokens)
            return GatewayResponse(
                success=False,
                error_code=GatewayErrorCode.BUDGET_EXCEEDED,
                error_message=f"Token budget exhausted ({self._tokens_used}/{self.max_daily_budget_tokens})",
                fallback_used=True,
                latency_ms=(time.perf_counter() - start_time) * 1000,
            )

        # 3. Check for prompt injection in untrusted context
        context_str = str(request.prompt_context)
        is_inj, pattern = detect_prompt_injection(context_str)
        if is_inj:
            logger.warning("Gateway: Blocked prompt injection in context: %s", pattern)
            return GatewayResponse(
                success=False,
                error_code=GatewayErrorCode.INJECTION_DETECTED,
                error_message=f"Security guardrail rejected prompt injection attempt: {pattern}",
                fallback_used=True,
                latency_ms=(time.perf_counter() - start_time) * 1000,
            )

        # 4. Safe offline execution mock/simulation
        self._tokens_used += min(request.max_tokens, 50)
        return GatewayResponse(
            success=True,
            data={"status": "completed", "task": request.task_name},
            tokens_consumed=50,
            latency_ms=(time.perf_counter() - start_time) * 1000,
            fallback_used=False,
        )
