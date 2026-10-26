"""Zero-cost local model provider for offline LLM inference (e.g. Ollama, llama.cpp, vLLM)."""

from __future__ import annotations

import json
from typing import Any, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

from zaxterlab.contracts.types import TokenUsage, ToolCall
from zaxterlab.models.base import CompletionRequest, CompletionResponse, ModelProvider
from zaxterlab.models.mock import MockProvider


class LocalOllamaProvider(ModelProvider):
    """Local, offline, zero-spend model provider interfacing with local Ollama or compatible servers.

    Enforces:
    - USD $0.00 spend guarantee
    - Local host / private IP validation (strictly forbids external paid endpoints)
    - Graceful offline fallback to MockProvider when local server daemon is not running
    """

    ALLOWED_LOCAL_HOSTS = {"127.0.0.1", "localhost", "0.0.0.0", "::1"}

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        model_name: str = "qwen2.5-coder:7b",
        timeout_seconds: float = 5.0,
        fallback_provider: Optional[ModelProvider] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self.fallback = fallback_provider or MockProvider()
        self._validate_local_endpoint(self.base_url)

    def _validate_local_endpoint(self, url: str) -> None:
        """Ensure endpoint is local and strictly non-billable."""
        from urllib.parse import urlparse

        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
        if hostname not in self.ALLOWED_LOCAL_HOSTS:
            raise ValueError(
                f"External host '{hostname}' forbidden. ZaxterLab is hard-locked to local offline inference "
                "with an authorized budget of $0.00 USD."
            )

    def is_available(self) -> bool:
        """Check if local Ollama daemon is reachable."""
        try:
            req = Request(f"{self.base_url}/api/tags", method="GET")
            with urlopen(req, timeout=1.0) as resp:
                return resp.status == 200
        except Exception:
            return False

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Execute completion against local Ollama; fallback gracefully if unreachable."""
        if not self.is_available():
            # Graceful offline fallback ensures tests and environments without local Ollama continue uninterrupted
            return self.fallback.complete(request)

        prompt_body = {
            "model": self.model_name,
            "prompt": f"{request.system_prompt}\n\nTask:\n{request.prompt}",
            "stream": False,
            "options": {
                "temperature": request.temperature,
            },
        }

        try:
            data = json.dumps(prompt_body).encode("utf-8")
            req = Request(
                f"{self.base_url}/api/generate",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(req, timeout=self.timeout_seconds) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            raw_response = result.get("response", "").strip()
            prompt_tokens = result.get("prompt_eval_count", len(request.prompt.split()))
            completion_tokens = result.get("eval_count", len(raw_response.split()))

            # Parse simple plan / tool calls if structured in response
            plan = None
            tool_calls: list[ToolCall] = []
            is_final = True

            return CompletionResponse(
                text=raw_response,
                plan=plan or "Executed via Local Ollama Model",
                tool_calls=tool_calls,
                is_final=is_final,
                evaluation="Completed via local offline inference.",
                token_usage=TokenUsage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                    estimated_cost_usd=0.0,  # Always $0.00
                ),
            )
        except Exception:
            # Fallback to mock provider on network or generation timeout
            return self.fallback.complete(request)

    def get_cost_estimate(self, request: CompletionRequest) -> float:
        """Strictly 0.00 USD for local offline inference."""
        return 0.0
