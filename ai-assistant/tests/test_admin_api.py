"""Tests for the authentication and administration endpoints.

These are the endpoints the chatbox-ai admin panel calls. The panel expects
a specific payload shape (a bare array for the lists, flat stats, a `user`
object for the profile), so the shapes are asserted here.
"""

from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

import api.admin as admin_module
from api.deps import get_current_user
from api.main import app
from security.passwords import hash_password

client = TestClient(app)

ADMIN_ID = "11111111-1111-1111-1111-111111111111"
VIEWER_ID = "22222222-2222-2222-2222-222222222222"
CONVERSATION_ID = "33333333-3333-3333-3333-333333333333"

ADMIN_USER = {
    "id": ADMIN_ID,
    "username": "admin",
    "email": "admin@example.com",
    "role": "admin",
    "language_preference": "ar",
    "is_active": True,
    "created_at": "2026-01-01T00:00:00+00:00",
}

VIEWER_USER = {
    **ADMIN_USER,
    "id": VIEWER_ID,
    "username": "viewer",
    "email": "viewer@example.com",
    "role": "viewer",
}

# One hash for the whole session: PBKDF2 is deliberately slow.
PASSWORD_HASH = hash_password("correct-horse-battery")


class UserRecord:
    """Mimics the UserRow dataclass the real DatabaseManager returns."""

    def __init__(
        self,
        id,
        username,
        email,
        role,
        language_preference,
        is_active,
        created_at,
    ):
        self.id = id
        self.username = username
        self.email = email
        self.role = role
        self.language_preference = language_preference
        self.is_active = is_active
        self.created_at = created_at


class FakeDB:
    """A minimal stand-in for DatabaseManager."""

    def __init__(self) -> None:
        self.users = [dict(ADMIN_USER), dict(VIEWER_USER)]
        self.conversations = [
            {
                "id": CONVERSATION_ID,
                "user_id": ADMIN_ID,
                "title": "First chat",
                "username": "admin",
                "email": "admin@example.com",
                "created_at": "2026-01-02T10:00:00+00:00",
                "updated_at": "2026-01-03T10:00:00+00:00",
            }
        ]
        self.created: list[dict] = []

    async def get_user_by_username(self, username):
        for user in self.users:
            if user["username"] == username:
                return {**user, "password_hash": PASSWORD_HASH}
        return None

    async def get_stats(self):
        return {
            "users": len(self.users),
            "active_users": len(self.users),
            "admins": 1,
            "conversations": len(self.conversations),
            "messages": 12,
            "memories": 0,
            "documents": 0,
            "audit_logs": 0,
        }

    async def list_users(self, limit=50, offset=0):
        return [dict(u) for u in self.users[offset : offset + limit]]

    async def list_conversations(self, limit=50, offset=0):
        return [dict(c) for c in self.conversations[offset : offset + limit]]

    async def update_user_role(self, user_id, role):
        for user in self.users:
            if user["id"] == user_id:
                user["role"] = role
                return True
        return False

    async def delete_user(self, user_id):
        before = len(self.users)
        self.users = [u for u in self.users if u["id"] != user_id]
        return len(self.users) != before

    async def delete_conversation(self, conversation_id):
        before = len(self.conversations)
        self.conversations = [
            c for c in self.conversations if c["id"] != conversation_id
        ]
        return len(self.conversations) != before

    async def create_user(
        self,
        username,
        email,
        password_hash,
        role="user",
        language_preference="ar",
        api_key=None,
    ):
        record = UserRecord(
            id="44444444-4444-4444-4444-444444444444",
            username=username,
            email=email,
            role=role,
            language_preference=language_preference,
            is_active=True,
            created_at="2026-02-01T00:00:00+00:00",
        )
        self.users.append(record)
        self.created.append(record)
        return record


@pytest.fixture
def fake_db(monkeypatch):
    db = FakeDB()
    monkeypatch.setattr(admin_module, "get_db_manager", lambda: db)
    return db


@pytest.fixture
def as_admin():
    app.dependency_overrides[get_current_user] = lambda: dict(ADMIN_USER)
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def as_viewer():
    app.dependency_overrides[get_current_user] = lambda: dict(VIEWER_USER)
    yield
    app.dependency_overrides.pop(get_current_user, None)


# ----------------------------------------------------------------------
# Authentication
# ----------------------------------------------------------------------
def test_login_returns_a_token_and_the_user(fake_db, monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 40)

    res = client.post(
        "/auth/login", json={"username": "admin", "password": "correct-horse-battery"}
    )

    assert res.status_code == 200
    body = res.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    # The panel reads data.user.role right after logging in.
    assert body["user"]["role"] == "admin"
    assert body["user"]["username"] == "admin"


def test_login_rejects_a_wrong_password(fake_db, monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 40)

    res = client.post(
        "/auth/login", json={"username": "admin", "password": "wrong-password"}
    )

    assert res.status_code == 401


def test_login_does_not_reveal_whether_the_user_exists(fake_db, monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 40)

    known = client.post(
        "/auth/login", json={"username": "admin", "password": "wrong-password"}
    )
    unknown = client.post(
        "/auth/login", json={"username": "nobody", "password": "wrong-password"}
    )

    assert known.status_code == unknown.status_code == 401
    assert known.json()["detail"] == unknown.json()["detail"]


def test_auth_me_returns_the_user_object(as_admin):
    res = client.get("/auth/me")

    assert res.status_code == 200
    assert res.json()["user"]["role"] == "admin"


# ----------------------------------------------------------------------
# Administration
# ----------------------------------------------------------------------
def test_admin_stats_is_flat(as_admin, fake_db):
    res = client.get("/admin/stats")

    assert res.status_code == 200
    body = res.json()
    # The panel reads data.users / data.conversations / data.messages /
    # data.admins directly.
    assert body["users"] == 2
    assert body["conversations"] == 1
    assert body["messages"] == 12
    assert body["admins"] == 1


def test_admin_users_is_a_bare_array(as_admin, fake_db):
    res = client.get("/admin/users")

    assert res.status_code == 200
    body = res.json()
    assert isinstance(body, list)
    assert body[0]["username"] == "admin"
    # Password hashes must never leave the server.
    assert "password_hash" not in body[0]


def test_admin_conversations_is_a_bare_array(as_admin, fake_db):
    res = client.get("/admin/conversations")

    assert res.status_code == 200
    body = res.json()
    assert isinstance(body, list)
    assert body[0]["username"] == "admin"
    assert body[0]["updated_at"]


def test_viewer_cannot_reach_the_admin_routes(as_viewer, fake_db):
    res = client.get("/admin/users")

    assert res.status_code == 403


def test_admin_can_change_a_role(as_admin, fake_db):
    res = client.patch(f"/admin/users/{VIEWER_ID}/role", json={"role": "developer"})

    assert res.status_code == 200
    assert res.json()["role"] == "developer"
    assert fake_db.users[1]["role"] == "developer"


def test_admin_cannot_change_the_role_to_an_unknown_one(as_admin, fake_db):
    res = client.patch(f"/admin/users/{VIEWER_ID}/role", json={"role": "root"})

    assert res.status_code == 422


def test_admin_cannot_demote_themselves(as_admin, fake_db):
    res = client.patch(f"/admin/users/{ADMIN_ID}/role", json={"role": "user"})

    assert res.status_code == 400


def test_admin_cannot_delete_themselves(as_admin, fake_db):
    res = client.delete(f"/admin/users/{ADMIN_ID}")

    assert res.status_code == 400


def test_admin_can_delete_a_user(as_admin, fake_db):
    res = client.delete(f"/admin/users/{VIEWER_ID}")

    assert res.status_code == 200
    assert len(fake_db.users) == 1


def test_admin_can_delete_a_conversation(as_admin, fake_db):
    res = client.delete(f"/admin/conversations/{CONVERSATION_ID}")

    assert res.status_code == 200
    assert fake_db.conversations == []


def test_admin_can_create_a_user(as_admin, fake_db):
    res = client.post(
        "/admin/users",
        json={
            "username": "newbie",
            "email": "newbie@example.com",
            "password": "another-long-password",
            "role": "user",
        },
    )

    assert res.status_code == 201
    assert res.json()["user"]["username"] == "newbie"
    assert len(fake_db.users) == 3
