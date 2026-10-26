"""Deterministic offline mock model provider for tests and hermetic execution."""

from __future__ import annotations

from typing import Callable, Optional

from zaxterlab.contracts.types import TokenUsage, ToolCall
from zaxterlab.models.base import CompletionRequest, CompletionResponse, ModelProvider


class MockProvider(ModelProvider):
    """Deterministic, zero-cost, offline model provider."""

    def __init__(
        self,
        responses: Optional[list[CompletionResponse]] = None,
        responder: Optional[Callable[[CompletionRequest], CompletionResponse]] = None,
        simulated_cost_usd: float = 0.0,
    ) -> None:
        self.responses = list(responses) if responses else []
        self.responder = responder
        self.simulated_cost_usd = simulated_cost_usd
        self.call_history: list[CompletionRequest] = []

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        self.call_history.append(request)

        if self.responder:
            resp = self.responder(request)
            if self.simulated_cost_usd > 0.0 and resp.token_usage.estimated_cost_usd == 0.0:
                resp.token_usage.estimated_cost_usd = self.simulated_cost_usd
            return resp

        if self.responses:
            resp = self.responses.pop(0)
            if self.simulated_cost_usd > 0.0 and resp.token_usage.estimated_cost_usd == 0.0:
                resp.token_usage.estimated_cost_usd = self.simulated_cost_usd
            return resp

        # Default fallback response: deterministic completion
        return CompletionResponse(
            text=f"Processed prompt: {request.prompt[:60]}...",
            plan="Default plan: inspect and verify",
            tool_calls=[],
            is_final=True,
            evaluation="Task completed via mock fallback.",
            token_usage=TokenUsage(
                prompt_tokens=10,
                completion_tokens=15,
                total_tokens=25,
                estimated_cost_usd=self.simulated_cost_usd,
            ),
        )

    def get_cost_estimate(self, request: CompletionRequest) -> float:
        return self.simulated_cost_usd
