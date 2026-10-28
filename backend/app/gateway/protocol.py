"""Narrow Gateway protocol and result types for bounded AI model calls (C03).

Enforces strict budget limits, typed payloads, deterministic fallback,
and fail-closed behavior when AI is unavailable or guardrails trigger.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class GatewayErrorCode(str, Enum):
    """Categorical error codes for model gateway boundaries."""

    DISABLED = "AI_DISABLED"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    TIMEOUT = "TIMEOUT"
    INJECTION_DETECTED = "PROMPT_INJECTION_DETECTED"
    SCHEMA_VIOLATION = "SCHEMA_VIOLATION"
    EXECUTION_ERROR = "EXECUTION_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    PAYLOAD_TOO_LARGE = "PAYLOAD_TOO_LARGE"
    UNAUTHORIZED_MODEL = "UNAUTHORIZED_MODEL"


@dataclass(frozen=True)
class GatewayRequest:
    """Bounded, strongly-typed request to an external or local model provider."""

    task_name: str
    model_alias: str
    prompt_context: dict[str, Any]
    max_tokens: int = 1000
    timeout_seconds: float = 10.0
    expected_schema: dict[str, Any] | None = None


@dataclass(frozen=True)
class GatewayResponse:
    """Strongly-typed response from model gateway with audit metrics."""

    success: bool
    data: dict[str, Any] | None = None
    error_code: GatewayErrorCode | None = None
    error_message: str | None = None
    tokens_consumed: int = 0
    latency_ms: float = 0.0
    fallback_used: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class ModelGatewayProtocol(Protocol):
    """Protocol for bounded AI gateways adhering to Level 1 offline invariants."""

    def invoke(self, request: GatewayRequest) -> GatewayResponse:
        """Synchronously or asynchronously execute a bounded AI request."""
        ...

    def is_enabled(self) -> bool:
        """Check whether AI provider keys and service are active and authorized."""
        ...
