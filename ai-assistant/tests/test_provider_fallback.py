"""Tests for Claude -> Ollama fallback orchestration in LLMRouter.

No network: both providers are replaced with fakes.
"""

from __future__ import annotations

import asyncio

from llm.provider import LLMProviderType, LLMRequest, LLMResponse
from llm.router import LLMRouter


class _FakeClaude:
    def __init__(self, *, available: bool = True, cost: float = 0.001, error=None):
        self.available = available
        self.cost = cost
        self.error = error
        self.calls = 0

    def is_available(self) -> bool:
        return self.available

    def get_cost_estimate(self, tokens_in: int, tokens_out: int) -> float:
        return self.cost

    def should_fallback(self, cost_estimate: float, max_cost: float = 0.10) -> bool:
        return cost_estimate > max_cost

    async def generate(self, request: LLMRequest) -> LLMResponse:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return LLMResponse(
            answer="claude-answer",
            provider=LLMProviderType.CLAUDE,
            model="claude-opus-5-5",
            language=request.language,
        )


class _FakeOllama:
    def __init__(self):
        self.calls = 0

    async def generate(self, request: LLMRequest) -> LLMResponse:
        self.calls += 1
        return LLMResponse(
            answer="ollama-answer",
            provider=LLMProviderType.OLLAMA,
            model="local-model",
            language=request.language,
            cost_usd=0.0,
        )


def _wire(monkeypatch, router, claude, ollama):
    """Attach fakes and record which local model was requested."""
    models = []
    router._claude = claude

    def fake_ollama_provider(self, model):
        models.append(model)
        return ollama

    monkeypatch.setattr(LLMRouter, "_ollama_provider", fake_ollama_provider)
    return models


def test_without_api_key_uses_ollama(monkeypatch):
    router = LLMRouter()
    claude = _FakeClaude(available=False)
    ollama = _FakeOllama()
    _wire(monkeypatch, router, claude, ollama)

    result = asyncio.run(
        router.generate_with_fallback(
            LLMRequest(message="solve it", language="en", task_type="reasoning")
        )
    )

    assert result.provider == LLMProviderType.OLLAMA
    assert result.answer == "ollama-answer"
    assert result.fallback_used is False
    assert claude.calls == 0


def test_complex_english_task_uses_claude(monkeypatch):
    router = LLMRouter()
    claude = _FakeClaude()
    ollama = _FakeOllama()
    _wire(monkeypatch, router, claude, ollama)

    result = asyncio.run(
        router.generate_with_fallback(
            LLMRequest(message="solve it", language="en", task_type="reasoning")
        )
    )

    assert result.provider == LLMProviderType.CLAUDE
    assert result.answer == "claude-answer"
    assert ollama.calls == 0


def test_refusal_falls_back_to_ollama(monkeypatch):
    router = LLMRouter()
    claude = _FakeClaude(error=RuntimeError("Claude refused (category: cyber)"))
    ollama = _FakeOllama()
    _wire(monkeypatch, router, claude, ollama)

    result = asyncio.run(
        router.generate_with_fallback(
            LLMRequest(message="solve it", language="en", task_type="reasoning")
        )
    )

    assert result.provider == LLMProviderType.OLLAMA
    assert result.answer == "ollama-answer"
    assert result.fallback_used is True
    assert claude.calls == 1
    assert ollama.calls == 1


def test_cost_over_limit_uses_ollama(monkeypatch):
    router = LLMRouter()
    claude = _FakeClaude(cost=0.50)
    ollama = _FakeOllama()
    _wire(monkeypatch, router, claude, ollama)

    result = asyncio.run(
        router.generate_with_fallback(
            LLMRequest(message="solve it", language="en", task_type="reasoning")
        )
    )

    assert result.provider == LLMProviderType.OLLAMA
    assert claude.calls == 0


def test_explicit_cost_limit_skips_claude(monkeypatch):
    router = LLMRouter(claude_max_cost=0.0005)
    claude = _FakeClaude(cost=0.001)
    ollama = _FakeOllama()
    _wire(monkeypatch, router, claude, ollama)

    asyncio.run(
        router.generate_with_fallback(
            LLMRequest(message="solve it", language="en", task_type="reasoning")
        )
    )

    assert claude.calls == 0


def test_arabic_task_stays_local(monkeypatch):
    router = LLMRouter()
    claude = _FakeClaude()
    ollama = _FakeOllama()
    _wire(monkeypatch, router, claude, ollama)

    result = asyncio.run(
        router.generate_with_fallback(
            LLMRequest(message="حل المشكلة", language="ar", task_type="reasoning")
        )
    )

    assert result.provider == LLMProviderType.OLLAMA
    assert claude.calls == 0


def test_general_task_stays_local(monkeypatch):
    router = LLMRouter()
    claude = _FakeClaude()
    ollama = _FakeOllama()
    _wire(monkeypatch, router, claude, ollama)

    result = asyncio.run(
        router.generate_with_fallback(
            LLMRequest(message="hello", language="en", task_type="general")
        )
    )

    assert result.provider == LLMProviderType.OLLAMA
    assert claude.calls == 0


def test_local_model_follows_task_type(monkeypatch):
    claude = _FakeClaude(available=False)
    ollama = _FakeOllama()

    reasoning_router = LLMRouter()
    reasoning_models = _wire(monkeypatch, reasoning_router, claude, ollama)
    asyncio.run(
        reasoning_router.generate_with_fallback(
            LLMRequest(message="why", language="en", task_type="reasoning")
        )
    )

    general_router = LLMRouter()
    general_models = _wire(monkeypatch, general_router, claude, ollama)
    asyncio.run(
        general_router.generate_with_fallback(
            LLMRequest(message="hello", language="en", task_type="general")
        )
    )

    assert reasoning_models == ["deepseek-r1:14b"]
    assert general_models == ["gemma4:e2b"]


def test_unknown_task_type_does_not_crash(monkeypatch):
    router = LLMRouter()
    claude = _FakeClaude(available=False)
    ollama = _FakeOllama()
    models = _wire(monkeypatch, router, claude, ollama)

    result = asyncio.run(
        router.generate_with_fallback(
            LLMRequest(message="hi", language="en", task_type="unknown-task")
        )
    )

    assert result.provider == LLMProviderType.OLLAMA
    assert models == [router.model]
