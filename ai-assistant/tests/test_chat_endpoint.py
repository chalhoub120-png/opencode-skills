"""HTTP tests for /chat and /chat/stream.

The app is exercised in-process with FastAPI's TestClient; every Ollama call
is replaced with a fake, so no server and no network are required.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from llm.client import OllamaClient
from llm.provider import LLMProviderType, LLMResponse
from llm.router import LLMRouter, app

client = TestClient(app)


def _fake_providers(monkeypatch, fail_models=()):
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


def test_chat_honours_reasoning_task(monkeypatch):
    calls = _fake_providers(monkeypatch)
    res = client.post(
        "/chat",
        json={
            "message": "why is the sky blue",
            "language": "en",
            "task_type": "reasoning",
        },
    )

    body = res.json()
    assert res.status_code == 200
    assert body["success"] is True
    assert body["model"] == "deepseek-r1:14b"
    assert body["fallback_used"] is False
    assert calls == ["deepseek-r1:14b"]


def test_chat_routes_unknown_task_by_keywords(monkeypatch):
    calls = _fake_providers(monkeypatch)
    body = client.post(
        "/chat",
        json={"message": "solve this problem", "language": "en", "task_type": "nope"},
    ).json()

    assert body["success"] is True
    assert calls == ["gemma4:e2b"]


def test_chat_reports_fallback(monkeypatch):
    calls = _fake_providers(monkeypatch, fail_models={"deepseek-r1:14b"})
    body = client.post(
        "/chat",
        json={"message": "why", "language": "en", "task_type": "reasoning"},
    ).json()

    assert body["success"] is True
    assert body["model"] == "gemma4:e2b"
    assert body["fallback_used"] is True
    assert calls == ["deepseek-r1:14b", "gemma4:e2b"]


def test_chat_returns_error_when_all_models_fail(monkeypatch):
    _fake_providers(monkeypatch, fail_models={"gemma4:e2b"})
    body = client.post(
        "/chat", json={"message": "hello", "language": "en", "task_type": "general"}
    ).json()

    assert body["success"] is False
    assert body["fallback_used"] is False
    assert "unavailable" in body["answer"]


def _fake_stream(monkeypatch, tokens=("Hel", "lo")):
    async def fake_chat_stream(self, model, messages, temperature=0.3, max_tokens=None):
        for token in tokens:
            yield ("content", token)

    monkeypatch.setattr(OllamaClient, "chat_stream", fake_chat_stream)


def test_stream_emits_metadata_tokens_and_done(monkeypatch):
    _fake_providers(monkeypatch)
    _fake_stream(monkeypatch)

    res = client.post(
        "/chat/stream",
        json={"message": "why", "language": "en", "task_type": "reasoning"},
    )

    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/event-stream")
    text = res.text
    assert '"model": "deepseek-r1:14b"' in text
    assert '"task_type": "reasoning"' in text
    assert '"content": "Hel"' in text
    assert '"content": "lo"' in text
    assert text.rstrip().endswith("data: [DONE]")


def test_stream_uses_arabic_model_for_arabic(monkeypatch):
    _fake_providers(monkeypatch)
    _fake_stream(monkeypatch)

    text = client.post(
        "/chat/stream",
        json={"message": "حل المشكلة", "language": "ar", "task_type": "reasoning"},
    ).text

    assert '"model": "gemma4:e2b"' in text


def test_stream_falls_back_when_model_fails(monkeypatch):
    _fake_providers(monkeypatch)

    async def failing_stream(self, model, messages, temperature=0.3, max_tokens=None):
        raise RuntimeError("connection refused")
        yield  # pragma: no cover - keeps this an async generator

    monkeypatch.setattr(OllamaClient, "chat_stream", failing_stream)

    text = client.post(
        "/chat/stream",
        json={"message": "why", "language": "en", "task_type": "reasoning"},
    ).text

    assert '"fallback_model": "gemma4:e2b"' in text
    assert "answer from gemma4:e2b" in text
    assert text.rstrip().endswith("data: [DONE]")


def test_stream_errors_when_no_lighter_model(monkeypatch):
    _fake_providers(monkeypatch, fail_models={"gemma4:e2b"})

    async def failing_stream(self, model, messages, temperature=0.3, max_tokens=None):
        raise RuntimeError("connection refused")
        yield  # pragma: no cover

    monkeypatch.setattr(OllamaClient, "chat_stream", failing_stream)

    text = client.post(
        "/chat/stream",
        json={"message": "hello", "language": "en", "task_type": "general"},
    ).text

    assert '"error"' in text
    assert text.rstrip().endswith("data: [DONE]")
