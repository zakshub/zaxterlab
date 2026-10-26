"""Unit tests for LocalOllamaProvider zero-cost adapter."""

import json
import socket
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from zaxterlab.models.base import CompletionRequest, CompletionResponse
from zaxterlab.models.local import LocalOllamaProvider
from zaxterlab.models.mock import MockProvider


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class MockOllamaServer(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == "/api/tags":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"models": [{"name": "qwen2.5-coder:7b"}]}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/generate":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            resp = {
                "response": "Synthesized code implementation from local model.",
                "prompt_eval_count": 25,
                "eval_count": 40,
                "done": True,
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(resp).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


class TestLocalOllamaProvider(unittest.TestCase):
    def test_external_endpoint_rejected_by_spend_boundary(self):
        """External hosts must raise ValueError immediately."""
        with self.assertRaises(ValueError) as ctx:
            LocalOllamaProvider(base_url="https://api.openai.com/v1")
        self.assertIn("forbidden", str(ctx.exception).lower())

        with self.assertRaises(ValueError) as ctx:
            LocalOllamaProvider(base_url="https://api.anthropic.com")
        self.assertIn("forbidden", str(ctx.exception).lower())

    def test_cost_estimate_strictly_zero(self):
        """Local inference must always return $0.00 cost estimate."""
        provider = LocalOllamaProvider(base_url="http://127.0.0.1:11434")
        req = CompletionRequest(system_prompt="Test", prompt="Hello")
        cost = provider.get_cost_estimate(req)
        self.assertEqual(cost, 0.0)

    def test_fallback_when_offline(self):
        """When local server is not running, falls back cleanly to mock provider."""
        unused_port = find_free_port()
        fallback_resp = CompletionResponse(
            text="Fallback offline mock output",
            plan="Plan B",
            tool_calls=[],
            is_final=True,
            evaluation="Executed offline fallback",
        )
        mock_fallback = MockProvider(responses=[fallback_resp])
        provider = LocalOllamaProvider(
            base_url=f"http://127.0.0.1:{unused_port}",
            fallback_provider=mock_fallback,
        )

        self.assertFalse(provider.is_available())
        req = CompletionRequest(system_prompt="Test", prompt="Offline prompt")
        resp = provider.complete(req)
        self.assertEqual(resp.text, "Fallback offline mock output")
        self.assertEqual(resp.token_usage.estimated_cost_usd, 0.0)

    def test_successful_local_ollama_completion(self):
        """When local Ollama responds on 127.0.0.1, completion parses properly with $0.00 spend."""
        port = find_free_port()
        server = HTTPServer(("127.0.0.1", port), MockOllamaServer)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            provider = LocalOllamaProvider(base_url=f"http://127.0.0.1:{port}")
            self.assertTrue(provider.is_available())

            req = CompletionRequest(
                system_prompt="You are Worker 1.",
                prompt="Implement basic math function in math_utils.py",
            )
            resp = provider.complete(req)
            self.assertIn("Synthesized code", resp.text)
            self.assertEqual(resp.token_usage.estimated_cost_usd, 0.0)
            self.assertEqual(resp.token_usage.prompt_tokens, 25)
            self.assertEqual(resp.token_usage.completion_tokens, 40)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1.0)


if __name__ == "__main__":
    unittest.main()
