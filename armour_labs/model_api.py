"""Minimal JSON chat clients for model-backed benchmarks.

The clients intentionally read credentials from environment variables at call
time. API keys should never be committed, written to benchmark artifacts, or
passed on command lines.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_ANTHROPIC_BASE_URL = "https://api.anthropic.com/v1"
ANTHROPIC_VERSION = "2023-06-01"
SUPPORTED_PROVIDERS = ("openai-compatible", "gemini", "anthropic")
TRANSIENT_HTTP_STATUS_CODES = {408, 409, 425, 429, 500, 502, 503, 504}
DEFAULT_RETRY_ATTEMPTS = 3


class ModelApiError(RuntimeError):
    pass


@dataclass(frozen=True)
class ModelConfig:
    provider: str
    model: str
    base_url: str
    api_key_env: str

    @classmethod
    def from_env(
        cls,
        provider: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ) -> "ModelConfig":
        selected_provider = (provider or os.environ.get("ARMOUR_MODEL_PROVIDER") or _autodetect_provider()).strip().lower()
        if selected_provider in {"openai", "openai-compatible"}:
            selected_model = model or os.environ.get("OPENAI_MODEL", "")
            if not selected_model:
                raise ModelApiError("Set OPENAI_MODEL or pass --model for real OpenAI-compatible calls.")
            return cls(
                provider="openai-compatible",
                model=selected_model,
                base_url=(base_url or os.environ.get("OPENAI_BASE_URL") or DEFAULT_OPENAI_BASE_URL).rstrip("/"),
                api_key_env="OPENAI_API_KEY",
            )

        if selected_provider == "gemini":
            selected_model = model or os.environ.get("GEMINI_MODEL", "")
            if not selected_model:
                raise ModelApiError("Set GEMINI_MODEL or pass --model for real Gemini calls.")
            return cls(
                provider="gemini",
                model=selected_model,
                base_url=(base_url or os.environ.get("GEMINI_BASE_URL") or DEFAULT_GEMINI_BASE_URL).rstrip("/"),
                api_key_env="GEMINI_API_KEY",
            )

        if selected_provider == "anthropic":
            selected_model = model or os.environ.get("ANTHROPIC_MODEL", "")
            if not selected_model:
                raise ModelApiError("Set ANTHROPIC_MODEL or pass --model for real Anthropic calls.")
            return cls(
                provider="anthropic",
                model=selected_model,
                base_url=(base_url or os.environ.get("ANTHROPIC_BASE_URL") or DEFAULT_ANTHROPIC_BASE_URL).rstrip("/"),
                api_key_env="ANTHROPIC_API_KEY",
            )

        raise ModelApiError(f"Unsupported model provider: {selected_provider}")

    def api_key(self) -> str:
        value = os.environ.get(self.api_key_env, "")
        if not value:
            raise ModelApiError(f"Set {self.api_key_env} for real model calls.")
        return value


def build_json_client(config: ModelConfig) -> "OpenAICompatibleClient | GeminiClient | AnthropicClient":
    if config.provider == "gemini":
        return GeminiClient(config)
    if config.provider == "anthropic":
        return AnthropicClient(config)
    if config.provider == "openai-compatible":
        return OpenAICompatibleClient(config)
    raise ModelApiError(f"Unsupported model provider: {config.provider}")


class OpenAICompatibleClient:
    def __init__(self, config: ModelConfig, timeout: int = 60) -> None:
        self.config = config
        self.timeout = timeout

    def complete_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        body = _post_json(
            f"{self.config.base_url}/chat/completions",
            payload,
            {
                "Authorization": f"Bearer {self.config.api_key()}",
                "Content-Type": "application/json",
            },
            timeout=self.timeout,
            secrets=[self.config.api_key()],
        )
        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ModelApiError(f"Model response did not contain chat content: {_safe_body(body)}") from exc
        return _parse_json_object(content, body)


class GeminiClient:
    def __init__(self, config: ModelConfig, timeout: int = 60) -> None:
        self.config = config
        self.timeout = timeout

    def complete_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"{system_prompt}\n\n{user_prompt}"}],
                }
            ],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
            },
        }
        model_name = self.config.model.removeprefix("models/")
        endpoint = f"{self.config.base_url}/models/{urllib.parse.quote(model_name, safe='')}:generateContent"
        body = _post_json(
            endpoint,
            payload,
            {
                "Content-Type": "application/json",
                "x-goog-api-key": self.config.api_key(),
            },
            timeout=self.timeout,
            secrets=[self.config.api_key()],
        )
        return _parse_json_object(_gemini_text(body), body)


class AnthropicClient:
    def __init__(self, config: ModelConfig, timeout: int = 60) -> None:
        self.config = config
        self.timeout = timeout

    def complete_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        payload = {
            "model": self.config.model,
            "max_tokens": 4096,
            "temperature": 0,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        body = _post_json(
            f"{self.config.base_url}/messages",
            payload,
            {
                "Content-Type": "application/json",
                "x-api-key": self.config.api_key(),
                "anthropic-version": ANTHROPIC_VERSION,
            },
            timeout=self.timeout,
            secrets=[self.config.api_key()],
        )
        return _parse_json_object(_anthropic_text(body), body)


def _autodetect_provider() -> str:
    if (
        os.environ.get("ANTHROPIC_API_KEY")
        and not os.environ.get("GEMINI_API_KEY")
        and not os.environ.get("OPENAI_API_KEY")
    ):
        return "anthropic"
    if os.environ.get("GEMINI_API_KEY") and not os.environ.get("OPENAI_API_KEY"):
        return "gemini"
    return "openai-compatible"


def _post_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: int,
    secrets: list[str],
) -> dict[str, Any]:
    payload_bytes = json.dumps(payload).encode("utf-8")
    raw = ""
    for attempt in range(1, DEFAULT_RETRY_ATTEMPTS + 1):
        request = urllib.request.Request(
            url,
            data=payload_bytes,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
            break
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            if exc.code in TRANSIENT_HTTP_STATUS_CODES and attempt < DEFAULT_RETRY_ATTEMPTS:
                _sleep_before_retry(attempt)
                continue
            raise ModelApiError(f"Model API HTTP {exc.code}: {_redact(detail, secrets)}") from exc
        except urllib.error.URLError as exc:
            if attempt < DEFAULT_RETRY_ATTEMPTS:
                _sleep_before_retry(attempt)
                continue
            raise ModelApiError(f"Model API connection failed: {_redact(str(exc), secrets)}") from exc

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ModelApiError(f"Model API returned non-JSON response: {_redact(raw[:500], secrets)}") from exc
    if not isinstance(parsed, dict):
        raise ModelApiError("Model API returned a non-object JSON response.")
    return parsed


def _sleep_before_retry(attempt: int) -> None:
    time.sleep(min(2 ** (attempt - 1), 5))


def _gemini_text(body: dict[str, Any]) -> str:
    try:
        parts = body["candidates"][0]["content"]["parts"]
        return "\n".join(str(part["text"]) for part in parts if "text" in part)
    except (KeyError, IndexError, TypeError) as exc:
        raise ModelApiError(f"Gemini response did not contain text content: {_safe_body(body)}") from exc


def _anthropic_text(body: dict[str, Any]) -> str:
    try:
        blocks = body["content"]
        text_blocks = [str(block["text"]) for block in blocks if block.get("type") == "text" and "text" in block]
    except (KeyError, TypeError) as exc:
        raise ModelApiError(f"Anthropic response did not contain text content: {_safe_body(body)}") from exc
    if not text_blocks:
        raise ModelApiError(f"Anthropic response did not contain text content: {_safe_body(body)}")
    return "\n".join(text_blocks)


def _parse_json_object(content: str, original_body: dict[str, Any]) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    if not text.startswith("{"):
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ModelApiError(f"Model response was not valid JSON: {_safe_body(original_body)}") from exc
    if not isinstance(parsed, dict):
        raise ModelApiError("Model response JSON must be an object.")
    return parsed


def _safe_body(body: dict[str, Any]) -> str:
    return json.dumps(body, sort_keys=True)[:1000]


def _redact(text: str, secrets: list[str]) -> str:
    redacted = text
    for secret in secrets:
        if secret:
            redacted = redacted.replace(secret, "<redacted>")
    return redacted
