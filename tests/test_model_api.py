from __future__ import annotations

import json
import urllib.error
import unittest
from io import BytesIO
from unittest.mock import patch

from armour_labs.model_api import AnthropicClient, GeminiClient, ModelConfig, OpenAICompatibleClient, build_json_client


class FakeResponse:
    def __init__(self, body: dict[str, object]) -> None:
        self.body = body

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.body).encode("utf-8")


class ModelApiTests(unittest.TestCase):
    def test_openai_config_reads_provider_specific_env(self) -> None:
        with patch.dict("os.environ", {"OPENAI_MODEL": "test-model"}, clear=True):
            config = ModelConfig.from_env(provider="openai-compatible")
        self.assertEqual(config.provider, "openai-compatible")
        self.assertEqual(config.model, "test-model")
        self.assertEqual(config.api_key_env, "OPENAI_API_KEY")

    def test_gemini_config_reads_provider_specific_env(self) -> None:
        with patch.dict("os.environ", {"GEMINI_MODEL": "gemini-test"}, clear=True):
            config = ModelConfig.from_env(provider="gemini")
        self.assertEqual(config.provider, "gemini")
        self.assertEqual(config.model, "gemini-test")
        self.assertEqual(config.api_key_env, "GEMINI_API_KEY")

    def test_anthropic_config_reads_provider_specific_env(self) -> None:
        with patch.dict("os.environ", {"ANTHROPIC_MODEL": "claude-test"}, clear=True):
            config = ModelConfig.from_env(provider="anthropic")
        self.assertEqual(config.provider, "anthropic")
        self.assertEqual(config.model, "claude-test")
        self.assertEqual(config.api_key_env, "ANTHROPIC_API_KEY")

    def test_build_json_client_dispatches_provider(self) -> None:
        openai_config = ModelConfig(
            provider="openai-compatible",
            model="test",
            base_url="https://example.test/v1",
            api_key_env="OPENAI_API_KEY",
        )
        gemini_config = ModelConfig(
            provider="gemini",
            model="test",
            base_url="https://example.test/v1beta",
            api_key_env="GEMINI_API_KEY",
        )
        anthropic_config = ModelConfig(
            provider="anthropic",
            model="test",
            base_url="https://example.test/v1",
            api_key_env="ANTHROPIC_API_KEY",
        )
        self.assertIsInstance(build_json_client(openai_config), OpenAICompatibleClient)
        self.assertIsInstance(build_json_client(gemini_config), GeminiClient)
        self.assertIsInstance(build_json_client(anthropic_config), AnthropicClient)

    def test_openai_client_parses_json_content(self) -> None:
        seen: dict[str, object] = {}

        def fake_urlopen(request: object, timeout: int) -> FakeResponse:
            seen["request"] = request
            seen["timeout"] = timeout
            return FakeResponse({"choices": [{"message": {"content": "{\"ok\": true}"}}]})

        config = ModelConfig(
            provider="openai-compatible",
            model="test",
            base_url="https://example.test/v1",
            api_key_env="OPENAI_API_KEY",
        )
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-secret"}, clear=True):
            with patch("urllib.request.urlopen", fake_urlopen):
                result = OpenAICompatibleClient(config, timeout=3).complete_json("system", "user")
        request = seen["request"]
        self.assertEqual(result, {"ok": True})
        self.assertNotIn("test-secret", request.full_url)
        self.assertEqual(seen["timeout"], 3)

    def test_gemini_client_uses_header_key_and_parses_text(self) -> None:
        seen: dict[str, object] = {}

        def fake_urlopen(request: object, timeout: int) -> FakeResponse:
            seen["request"] = request
            return FakeResponse(
                {
                    "candidates": [
                        {"content": {"parts": [{"text": "```json\n{\"ok\": true}\n```"}]}}
                    ]
                }
            )

        config = ModelConfig(
            provider="gemini",
            model="models/gemini-test",
            base_url="https://example.test/v1beta",
            api_key_env="GEMINI_API_KEY",
        )
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-secret"}, clear=True):
            with patch("urllib.request.urlopen", fake_urlopen):
                result = GeminiClient(config).complete_json("system", "user")
        request = seen["request"]
        self.assertEqual(result, {"ok": True})
        self.assertNotIn("test-secret", request.full_url)

    def test_gemini_client_retries_transient_http_error(self) -> None:
        attempts = 0

        def fake_urlopen(request: object, timeout: int) -> FakeResponse:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise urllib.error.HTTPError(
                    url=request.full_url,
                    code=503,
                    msg="Service Unavailable",
                    hdrs=None,
                    fp=BytesIO(b'{"error":"busy"}'),
                )
            return FakeResponse(
                {
                    "candidates": [
                        {"content": {"parts": [{"text": "{\"ok\": true}"}]}}
                    ]
                }
            )

        config = ModelConfig(
            provider="gemini",
            model="gemini-test",
            base_url="https://example.test/v1beta",
            api_key_env="GEMINI_API_KEY",
        )
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-secret"}, clear=True):
            with patch("urllib.request.urlopen", fake_urlopen):
                with patch("armour_labs.model_api.time.sleep"):
                    result = GeminiClient(config).complete_json("system", "user")
        self.assertEqual(result, {"ok": True})
        self.assertEqual(attempts, 2)

    def test_anthropic_client_uses_header_key_and_parses_text(self) -> None:
        seen: dict[str, object] = {}

        def fake_urlopen(request: object, timeout: int) -> FakeResponse:
            seen["request"] = request
            seen["timeout"] = timeout
            return FakeResponse({"content": [{"type": "text", "text": "{\"ok\": true}"}]})

        config = ModelConfig(
            provider="anthropic",
            model="claude-test",
            base_url="https://example.test/v1",
            api_key_env="ANTHROPIC_API_KEY",
        )
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-secret"}, clear=True):
            with patch("urllib.request.urlopen", fake_urlopen):
                result = AnthropicClient(config, timeout=3).complete_json("system", "user")
        request = seen["request"]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(result, {"ok": True})
        self.assertEqual(payload["system"], "system")
        self.assertEqual(payload["messages"][0]["role"], "user")
        self.assertIn("anthropic-version", {key.lower() for key in request.headers})
        self.assertNotIn("test-secret", request.full_url)
        self.assertEqual(seen["timeout"], 3)


if __name__ == "__main__":
    unittest.main()
