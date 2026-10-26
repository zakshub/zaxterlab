"""Provider-neutral model interfaces and completion contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from zaxterlab.contracts.types import TokenUsage, ToolCall


@dataclass
class CompletionRequest:
    """Standardized request envelope for model inference."""

    system_prompt: str
    prompt: str
    tools: list[dict[str, Any]] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    temperature: float = 0.0


@dataclass
class CompletionResponse:
    """Standardized response envelope from a model provider."""

    text: str
    plan: Optional[str] = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    is_final: bool = False
    evaluation: Optional[str] = None
    token_usage: TokenUsage = field(default_factory=TokenUsage)


class ModelProvider(ABC):
    """Abstract base class for provider-neutral model inference."""

    @abstractmethod
    def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Execute a completion request synchronously."""
        pass

    @abstractmethod
    def get_cost_estimate(self, request: CompletionRequest) -> float:
        """Calculate estimated cost in USD. Must return 0.0 for free/local tiers."""
        pass
