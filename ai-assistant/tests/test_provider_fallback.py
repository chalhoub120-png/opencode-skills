"""Tests for local model fallback orchestration in LLMRouter.

No network: every Ollama provider is replaced with a fake.
"""

from __future__ import annotations

import asyncio

import pytest

from llm.provider import LLMProviderType, LLMRequest, LLMResponse
from llm.router import LLMRouter, TaskType


def _wire(monkeypatch, fail_models=()):
    """Replace the provider factory and record which models were requested."""
    calls = []

    class FakeOllama:
        def __init__(self, model):
            self.model = model

        async def generate(self, request):
            calls.append(self.model)
            if self.model in fail_models:
                raise RuntimeError(f"model {self.model} unavailable")
            return LLMResponse(
                answer=f"answer from {self.model}",
                provider=LLMProviderType.OLLAMA,
                model=self.model,
                language=request.language,
                cost_usd=0.0,
            )

    monkeypatch.setattr(
        LLMRouter, "_ollama_provider", lambda self, model: FakeOllama(model)
    )
    return calls


def _request(**kwargs):
    data = {"message": "hello", "language": "en", "task_type": "general"}
    data.update(kwargs)
    return LLMRequest(**data)


def test_reasoning_uses_deepseek(monkeypatch):
    calls = _wire(monkeypatch)
    result = asyncio.run(
        LLMRouter().generate_with_fallback(_request(task_type="reasoning"))
    )

    assert calls == ["deepseek-r1:14b"]
    assert result.model == "deepseek-r1:14b"
    assert result.fallback_used is False


def test_general_uses_gemma(monkeypatch):
    calls = _wire(monkeypatch)
    result = asyncio.run(LLMRouter().generate_with_fallback(_request()))

    assert calls == ["gemma4:e2b"]
    assert result.fallback_used is False


def test_arabic_reasoning_stays_on_gemma(monkeypatch):
    calls = _wire(monkeypatch)
    result = asyncio.run(
        LLMRouter().generate_with_fallback(
            _request(message="حل المشكلة", language="ar", task_type="reasoning")
        )
    )

    assert calls == ["gemma4:e2b"]
    assert result.model == "gemma4:e2b"


def test_failure_retries_with_fallback_model(monkeypatch):
    calls = _wire(monkeypatch, fail_models={"deepseek-r1:14b"})
    result = asyncio.run(
        LLMRouter().generate_with_fallback(_request(task_type="reasoning"))
    )

    assert calls == ["deepseek-r1:14b", "gemma4:e2b"]
    assert result.model == "gemma4:e2b"
    assert result.answer == "answer from gemma4:e2b"
    assert result.fallback_used is True


def test_failure_without_lighter_model_raises(monkeypatch):
    # "No lighter model" means every model in the chain has failed: a single
    # broken model is now handled by falling through to the next one.
    chain = LLMRouter().get_model_chain(TaskType.GENERAL, language="en")
    calls = _wire(monkeypatch, fail_models=set(chain))

    with pytest.raises(RuntimeError, match="unavailable"):
        asyncio.run(LLMRouter().generate_with_fallback(_request()))

    assert calls == chain


def test_unknown_task_type_routes_by_keywords(monkeypatch):
    calls = _wire(monkeypatch)
    asyncio.run(
        LLMRouter().generate_with_fallback(
            _request(message="solve this problem step by step", task_type="unknown")
        )
    )

    assert calls == ["gemma4:e2b"]

    # Auto-reasoning can be re-enabled for long messages.
    monkeypatch.setenv("ROUTING_AUTO_REASONING", "1")
    monkeypatch.setenv("ROUTING_MIN_REASONING_CHARS", "0")
    calls2 = _wire(monkeypatch)
    asyncio.run(
        LLMRouter().generate_with_fallback(
            _request(
                message="prove this theorem step by step with full reasoning",
                task_type="unknown",
            )
        )
    )
    assert calls2 == ["deepseek-r1:14b"]


def test_unknown_arabic_task_stays_local(monkeypatch):
    calls = _wire(monkeypatch)
    asyncio.run(
        LLMRouter().generate_with_fallback(
            _request(message="حل المشكلة", language="ar", task_type="unknown")
        )
    )

    assert calls == ["gemma4:e2b"]


def test_empty_task_type_falls_back_to_keywords(monkeypatch):
    calls = _wire(monkeypatch)
    asyncio.run(
        LLMRouter().generate_with_fallback(
            _request(message="solve this problem", task_type="")
        )
    )

    assert calls == ["gemma4:e2b"]
