"""Tests for the optional authentication on the chat path.

The chat endpoints must keep working on a laptop with no database and no
secrets, so authentication is environment driven. These tests pin that
contract so a change cannot silently open or close the API.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from llm.provider import LLMProviderType, LLMResponse
from llm.router import LLMRouter, app
from security import chat_auth

client = TestClient(app)


def _fake_providers(monkeypatch):
    """Replace the Ollama provider so no model call is made."""

    class FakeOllama:
        def __init__(self, model):
            self.model = model

        async def generate(self, request):
            return LLMResponse(
                answer="ok",
                provider=LLMProviderType.OLLAMA,
                model=self.model,
                language=request.language,
                cost_usd=0.0,
            )

    monkeypatch.setattr(
        LLMRouter, "_ollama_provider", lambda self, model: FakeOllama(model)
    )


def test_auth_is_off_in_auto_mode_without_secrets(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "auto")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    assert chat_auth.auth_enabled() is False


def test_auth_is_on_in_auto_mode_with_secrets(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "auto")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@127.0.0.1:5432/db")
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 40)
    assert chat_auth.auth_enabled() is True


def test_auth_enabled_flag_overrides_auto_detection(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "false")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@127.0.0.1:5432/db")
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 40)
    assert chat_auth.auth_enabled() is False

    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    assert chat_auth.auth_enabled() is True


def test_chat_works_without_credentials_when_auth_is_off(monkeypatch):
    _fake_providers(monkeypatch)
    monkeypatch.setenv("AUTH_ENABLED", "false")

    res = client.post("/chat", json={"message": "hi", "language": "en"})

    assert res.status_code == 200
    assert res.json()["success"] is True


def test_chat_rejects_unauthenticated_requests_when_auth_is_on(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 40)
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@127.0.0.1:1/db")

    res = client.post("/chat", json={"message": "hi", "language": "en"})

    assert res.status_code == 401


def test_local_user_carries_a_role(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "false")
    monkeypatch.setenv("DEFAULT_ROLE", "admin")
    user = chat_auth.local_user()
    assert user["role"] == "admin"
    assert user["id"] == "local"
