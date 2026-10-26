"""Unit tests for ModelProvider interface and MockProvider."""

import unittest
from zaxterlab.contracts.types import TokenUsage, ToolCall
from zaxterlab.models.base import CompletionRequest, CompletionResponse
from zaxterlab.models.mock import MockProvider


class TestModelProviders(unittest.TestCase):
    def test_mock_provider_default(self):
        provider = MockProvider()
        req = CompletionRequest(
            system_prompt="System instructions",
            prompt="Hello world",
        )
        self.assertEqual(provider.get_cost_estimate(req), 0.0)

        resp = provider.complete(req)
        self.assertTrue(resp.is_final)
        self.assertEqual(resp.token_usage.estimated_cost_usd, 0.0)
        self.assertGreater(resp.token_usage.total_tokens, 0)
        self.assertEqual(len(provider.call_history), 1)

    def test_mock_provider_scripted_responses(self):
        scripted = [
            CompletionResponse(
                text="Step 1 response",
                plan="Inspect files",
                tool_calls=[ToolCall(call_id="c1", tool_name="list_dir")],
                is_final=False,
                token_usage=TokenUsage(10, 10, 20, 0.0),
            ),
            CompletionResponse(
                text="Step 2 response",
                plan="Finished task",
                tool_calls=[],
                is_final=True,
                token_usage=TokenUsage(15, 15, 30, 0.0),
            ),
        ]
        provider = MockProvider(responses=scripted)

        req1 = CompletionRequest(system_prompt="s", prompt="p1")
        resp1 = provider.complete(req1)
        self.assertFalse(resp1.is_final)
        self.assertEqual(resp1.tool_calls[0].tool_name, "list_dir")

        req2 = CompletionRequest(system_prompt="s", prompt="p2")
        resp2 = provider.complete(req2)
        self.assertTrue(resp2.is_final)
        self.assertEqual(resp2.plan, "Finished task")

    def test_mock_provider_simulated_cost(self):
        provider = MockProvider(simulated_cost_usd=0.015)
        req = CompletionRequest(system_prompt="s", prompt="p")
        self.assertEqual(provider.get_cost_estimate(req), 0.015)

        resp = provider.complete(req)
        self.assertEqual(resp.token_usage.estimated_cost_usd, 0.015)


if __name__ == "__main__":
    unittest.main()
