"""Tests for the notification API.

The n8n workflow is the only writer, so these tests fake the orchestrator and
the database: what is asserted is the HTTP contract, the ownership rule
(``user_id`` always comes from the caller) and the error propagation.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import api.notifications as notifications_module
from api.deps import get_current_user
from api.main import app

client = TestClient(app)

USER_ID = "715ae2b7-2591-45ac-96a9-b1dc37423055"
NOTIFICATION_ID = "8eac3993-efa0-4880-a202-e06a46abc098"


class FakeOrchestrator:
    """Stands in for the n8n call and records what was sent."""

    def __init__(self, success=True, error=None, response=None):
        self.success = success
        self.error = error
        self.response = response or {
            "id": NOTIFICATION_ID,
            "user_id": USER_ID,
            "message": "تذكير بالاجتماع",
            "type": "reminder",
            "read": False,
        }
        self.calls = []

    async def route_to_n8n(self, user_id, payload):
        self.calls.append({"user_id": user_id, "payload": payload})
        return SimpleNamespace(
            success=self.success,
            error=self.error,
            tool_results=[{"workflow": "notify-webhook", "response": self.response}],
        )


class FakeDB:
    def __init__(self):
        self.calls = []
        self.existing = {NOTIFICATION_ID}

    async def list_notifications(self, user_id, unread_only=False, limit=50, offset=0):
        self.calls.append(
            {
                "user_id": user_id,
                "unread_only": unread_only,
                "limit": limit,
                "offset": offset,
            }
        )
        return [{"id": NOTIFICATION_ID, "message": "m", "read": False}]

    async def mark_notification_read(self, notification_id, user_id):
        return notification_id in self.existing and user_id == USER_ID


@pytest.fixture
def as_user():
    app.dependency_overrides[get_current_user] = lambda: {
        "id": USER_ID,
        "username": "demo",
        "role": "user",
    }
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def fake_orchestrator(monkeypatch):
    fake = FakeOrchestrator()
    monkeypatch.setattr(notifications_module, "get_orchestrator", lambda: fake)
    return fake


@pytest.fixture
def fake_db(monkeypatch):
    db = FakeDB()
    monkeypatch.setattr(notifications_module, "get_db_manager", lambda: db)
    return db


def test_notify_stores_through_the_workflow(as_user, fake_orchestrator):
    res = client.post(
        "/notify",
        json={"message": "تذكير بالاجتماع", "type": "reminder"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["notification"]["id"] == NOTIFICATION_ID

    call = fake_orchestrator.calls[0]
    assert call["user_id"] == USER_ID
    assert call["payload"] == {
        "message": "تذكير بالاجتماع",
        "type": "reminder",
        "channel": "in_app",
    }


def test_notify_rejection_is_reported_as_400(as_user, monkeypatch):
    fake = FakeOrchestrator(
        success=False,
        error="user_id does not reference an existing user",
    )
    monkeypatch.setattr(notifications_module, "get_orchestrator", lambda: fake)

    res = client.post("/notify", json={"message": "hello"})
    assert res.status_code == 400
    assert res.json()["detail"] == "user_id does not reference an existing user"


def test_notify_rejects_an_anonymous_user(monkeypatch):
    app.dependency_overrides[get_current_user] = lambda: {"id": "local"}
    fake = FakeOrchestrator()
    monkeypatch.setattr(notifications_module, "get_orchestrator", lambda: fake)
    try:
        res = client.post("/notify", json={"message": "hello"})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert res.status_code == 400
    assert "UUID" in res.json()["detail"]
    assert fake.calls == []


def test_notify_validates_the_message(as_user, fake_orchestrator):
    res = client.post("/notify", json={"message": ""})
    assert res.status_code == 422
    assert fake_orchestrator.calls == []


def test_list_returns_the_callers_notifications(as_user, fake_db):
    res = client.get("/notifications")
    assert res.status_code == 200
    body = res.json()
    assert body["count"] == 1
    assert body["notifications"][0]["id"] == NOTIFICATION_ID
    assert fake_db.calls[0]["user_id"] == USER_ID


def test_list_passes_the_unread_filter(as_user, fake_db):
    res = client.get("/notifications?unread_only=true&limit=10&offset=5")
    assert res.status_code == 200
    call = fake_db.calls[0]
    assert call["unread_only"] is True
    assert call["limit"] == 10
    assert call["offset"] == 5


def test_mark_read_updates_the_row(as_user, fake_db):
    res = client.patch(f"/notifications/{NOTIFICATION_ID}/read")
    assert res.status_code == 200
    assert res.json() == {"success": True, "id": NOTIFICATION_ID}


def test_mark_read_returns_404_for_an_unknown_row(as_user, fake_db):
    res = client.patch("/notifications/00000000-0000-0000-0000-000000000000/read")
    assert res.status_code == 404
