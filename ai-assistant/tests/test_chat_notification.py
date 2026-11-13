"""The text chat path must persist explicit notification requests.

``/chat`` used to call the model directly, so a notification asked for in the
chat UI never reached the ``notifications`` table. These tests pin the branch
that fixes it, and pin that ordinary questions still go to the model.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import api.deps as deps_module
from api.deps import get_current_user  # noqa: F401 - imported for symmetry
from llm.router import app
from security.chat_auth import get_optional_user

client = TestClient(app)

USER_ID = "715ae2b7-2591-45ac-96a9-b1dc37423055"
NOTIFICATION_ID = "4974a973-d3d3-4cc7-ac23-437628047620"


class FakeOrchestrator:
    def __init__(self, success=True, error=None):
        self.success = success
        self.error = error
        self.calls = []

    async def route_to_n8n(self, user_id, payload):
        self.calls.append({"user_id": user_id, "payload": payload})
        return SimpleNamespace(
            success=self.success,
            error=self.error,
            tool_results=[
                {
                    "workflow": "notify-webhook",
                    "response": {
                        "id": NOTIFICATION_ID,
                        "user_id": user_id,
                        "message": payload["message"],
                        "type": payload["type"],
                        "read": False,
                    },
                }
            ],
        )


@pytest.fixture
def as_uuid_user():
    app.dependency_overrides[get_optional_user] = lambda: {
        "id": USER_ID,
        "username": "demo",
    }
    yield
    app.dependency_overrides.pop(get_optional_user, None)


def _forbid_model(monkeypatch):
    """Fail loudly if the chat path falls through to a model."""

    def _boom(self, request):
        raise AssertionError("the model must not be called")

    monkeypatch.setattr("llm.router.LLMRouter.generate_with_fallback", _boom)


def test_chat_persists_a_notification_request(as_uuid_user, monkeypatch):
    fake = FakeOrchestrator()
    monkeypatch.setattr(deps_module, "get_orchestrator", lambda: fake)
    _forbid_model(monkeypatch)

    res = client.post(
        "/chat",
        json={"message": "سجّل تنبيه في قاعدة البيانات للاجتماع", "language": "ar"},
    )

    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["model"] == "n8n"
    assert body["notification"]["id"] == NOTIFICATION_ID
    assert fake.calls[0]["user_id"] == USER_ID
    assert fake.calls[0]["payload"]["type"] == "notification"


def test_chat_reports_a_rejected_notification(as_uuid_user, monkeypatch):
    fake = FakeOrchestrator(
        success=False,
        error="user_id does not reference an existing user",
    )
    monkeypatch.setattr(deps_module, "get_orchestrator", lambda: fake)
    _forbid_model(monkeypatch)

    res = client.post(
        "/chat",
        json={"message": "أرسل إشعارًا بالاجتماع", "language": "ar"},
    )

    assert res.status_code == 200
    body = res.json()
    assert body["success"] is False
    assert "existing user" in body["answer"]


def test_chat_does_not_hijack_a_plain_question(as_uuid_user, monkeypatch):
    fake = FakeOrchestrator()
    monkeypatch.setattr(deps_module, "get_orchestrator", lambda: fake)

    from llm.provider import LLMProviderType, LLMResponse

    class FakeOllama:
        def __init__(self, model):
            self.model = model

        async def generate(self, request):
            return LLMResponse(
                answer="webhook هو نقطة نهاية تستقبل طلبات HTTP.",
                provider=LLMProviderType.OLLAMA,
                model=self.model,
                language=request.language,
                cost_usd=0.0,
            )

    monkeypatch.setattr(
        "llm.router.LLMRouter._ollama_provider", lambda self, model: FakeOllama(model)
    )

    res = client.post(
        "/chat",
        json={"message": "ما هو webhook وكيف يعمل؟", "language": "ar"},
    )

    assert res.status_code == 200
    assert res.json()["model"] != "n8n"
    assert fake.calls == []


def test_anonymous_chat_cannot_create_a_notification(monkeypatch):
    app.dependency_overrides[get_optional_user] = lambda: {"id": "local"}
    fake = FakeOrchestrator()
    monkeypatch.setattr(deps_module, "get_orchestrator", lambda: fake)

    class FakeOllama:
        def __init__(self, model):
            self.model = model

        async def generate(self, request):
            from llm.provider import LLMProviderType, LLMResponse

            return LLMResponse(
                answer="ok",
                provider=LLMProviderType.OLLAMA,
                model=self.model,
                language=request.language,
                cost_usd=0.0,
            )

    monkeypatch.setattr(
        "llm.router.LLMRouter._ollama_provider", lambda self, model: FakeOllama(model)
    )
    try:
        res = client.post(
            "/chat",
            json={"message": "سجّل تنبيه في قاعدة البيانات", "language": "ar"},
        )
    finally:
        app.dependency_overrides.pop(get_optional_user, None)

    assert res.status_code == 200
    assert fake.calls == []
