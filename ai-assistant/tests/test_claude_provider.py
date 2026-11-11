"""Tests for the Claude API provider.

No network calls: the Anthropic client is replaced with a fake object so the
request shape (model id, thinking, effort, sampling params) can be asserted.
"""

from __future__ import annotations

import asyncio

from llm.claude_provider import (
    INPUT_USD_PER_MTOK,
    OUTPUT_USD_PER_MTOK,
    ClaudeProvider,
)
from llm.provider import LLMProviderType, LLMRequest

FAKE_KEY = "test-key-not-real"


class _Block:
    def __init__(self, type_: str, **fields):
        self.type = type_
        self.__dict__.update(fields)

    def model_dump(self):
        return {"type": self.type}


class _Usage:
    def __init__(self, input_tokens: int, output_tokens: int):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class _StopDetails:
    def __init__(self, category: str):
        self.category = category


class _Response:
    def __init__(
        self,
        content,
        stop_reason: str = "end_turn",
        stop_details=None,
        input_tokens: int = 100,
        output_tokens: int = 50,
    ):
        self.content = content
        self.stop_reason = stop_reason
        self.stop_details = stop_details
        self.usage = _Usage(input_tokens, output_tokens)


class _Messages:
    def __init__(self, response: _Response):
        self.response = response
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class _Client:
    def __init__(self, response: _Response):
        self.messages = _Messages(response)


def _provider_with(response: _Response, monkeypatch) -> ClaudeProvider:
    monkeypatch.setenv("ANTHROPIC_API_KEY", FAKE_KEY)
    provider = ClaudeProvider()
    provider._client = _Client(response)
    return provider


def test_default_model_is_current_opus():
    assert ClaudeProvider().get_model_name() == "claude-opus-5-5"


def test_generate_uses_adaptive_thinking_without_sampling_params(monkeypatch):
    response = _Response([_Block("text", text="hello")])
    provider = _provider_with(response, monkeypatch)

    result = asyncio.run(provider.generate(LLMRequest(message="hi")))

    call = provider._client.messages.calls[0]
    assert call["model"] == "claude-opus-5-5"
    assert call["thinking"] == {"type": "adaptive"}
    assert "temperature" not in call
    assert "top_p" not in call
    assert "top_k" not in call
    assert result.answer == "hello"
    assert result.provider == LLMProviderType.CLAUDE


def test_reasoning_task_uses_high_effort(monkeypatch):
    provider = _provider_with(_Response([_Block("text", text="ok")]), monkeypatch)

    asyncio.run(provider.generate(LLMRequest(message="solve", task_type="reasoning")))

    assert provider._client.messages.calls[0]["output_config"] == {"effort": "high"}


def test_general_task_uses_medium_effort(monkeypatch):
    provider = _provider_with(_Response([_Block("text", text="ok")]), monkeypatch)

    asyncio.run(provider.generate(LLMRequest(message="hi", task_type="general")))

    assert provider._client.messages.calls[0]["output_config"] == {"effort": "medium"}


def test_cost_estimate_uses_opus_55_pricing():
    provider = ClaudeProvider()
    expected = INPUT_USD_PER_MTOK + OUTPUT_USD_PER_MTOK
    assert provider.get_cost_estimate(1_000_000, 1_000_000) == expected == 24.0
    assert provider.get_cost_estimate(100, 50) == 0.0014


def test_response_cost_matches_token_usage(monkeypatch):
    provider = _provider_with(
        _Response([_Block("text", text="ok")], input_tokens=100, output_tokens=50),
        monkeypatch,
    )

    result = asyncio.run(provider.generate(LLMRequest(message="hi")))

    assert result.tokens_used == 150
    assert result.cost_usd == 0.0014


def test_thinking_blocks_are_captured(monkeypatch):
    response = _Response(
        [
            _Block("thinking", thinking="reasoning..."),
            _Block("text", text="answer"),
        ]
    )
    provider = _provider_with(response, monkeypatch)

    result = asyncio.run(provider.generate(LLMRequest(message="hi")))

    assert result.thinking_blocks == [{"type": "thinking"}]
    assert result.answer == "answer"


def test_refusal_raises_without_leaking_api_key(monkeypatch):
    response = _Response([], stop_reason="refusal", stop_details=_StopDetails("cyber"))
    provider = _provider_with(response, monkeypatch)

    try:
        asyncio.run(provider.generate(LLMRequest(message="hi")))
    except RuntimeError as exc:
        message = str(exc)
        assert "refused" in message
        assert "cyber" in message
        assert FAKE_KEY not in message
    else:
        raise AssertionError("refusal must raise so the caller can fall back")


def test_is_available_follows_env_var(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert ClaudeProvider().is_available() is False

    monkeypatch.setenv("ANTHROPIC_API_KEY", FAKE_KEY)
    assert ClaudeProvider().is_available() is True


def test_should_fallback_above_limit():
    provider = ClaudeProvider()
    assert provider.should_fallback(0.05) is False
    assert provider.should_fallback(0.11) is True
