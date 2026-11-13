"""Authentication and administration endpoints.

The chat UI (chatbox-ai) proxies ``/api/auth/*`` and ``/api/admin/*`` here, so
users and conversations live in exactly one place: this PostgreSQL database.
The Express server only forwards requests and never holds credentials.

Every admin route is guarded by RBAC (``users:read`` / ``users:write`` /
``users:delete``), so a non-admin caller gets 403 instead of the data.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.deps import get_current_user, get_db_manager
from security.passwords import hash_password, verify_password
from security.rbac import RBACManager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin"])

# Roles accepted by the users table CHECK constraint.
VALID_ROLES = ("admin", "developer", "user", "viewer")


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=128)
    password: str = Field(..., min_length=1, max_length=256)


class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=128)
    email: str = Field(..., min_length=3, max_length=256)
    password: str = Field(..., min_length=8, max_length=256)
    role: str = Field(default="user")
    language_preference: str = Field(default="ar")


class RoleRequest(BaseModel):
    role: str = Field(..., min_length=1, max_length=32)


def _rbac() -> RBACManager:
    return RBACManager(enabled=True)


def _require(user: Dict[str, Any], permission: str) -> None:
    """Raise 403 unless the user's role carries the permission."""
    role = str(user.get("role") or "viewer")
    if not RBACManager(enabled=True).has_permission(role, permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{role}' is not allowed to perform this action.",
        )


async def _require_admin(
    user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Guard for every /admin route."""
    _require(user, "users:read")
    return user


def _public_user(user: Dict[str, Any]) -> Dict[str, Any]:
    """Strip secrets before a user leaves the server."""
    return {
        "id": str(user.get("id")),
        "username": user.get("username"),
        "email": user.get("email"),
        "role": user.get("role"),
        "language_preference": user.get("language_preference"),
        "is_active": user.get("is_active"),
        "created_at": user.get("created_at"),
    }


# ----------------------------------------------------------------------
# Authentication
# ----------------------------------------------------------------------
@router.post("/auth/login")
async def login(payload: LoginRequest):
    """Exchange a username and password for an access token."""
    from security.auth import AuthManager

    db = get_db_manager()
    try:
        record = await db.get_user_by_username(payload.username)
    except Exception as exc:  # noqa: BLE001 - never leak the DB error
        logger.error("Login lookup failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The user store is unavailable.",
        ) from exc

    # Same error for an unknown user and a wrong password: do not reveal
    # which usernames exist.
    if not record or not verify_password(payload.password, record.get("password_hash")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )
    if not record.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is disabled.",
        )

    try:
        manager = AuthManager(db)
    except Exception as exc:  # noqa: BLE001 - a broken env must be explicit
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured correctly.",
        ) from exc

    token = manager.create_access_token(
        user_id=str(record["id"]), role=str(record.get("role") or "user")
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": manager.access_token_expire_minutes * 60,
        "user": _public_user(record),
    }


@router.get("/auth/me")
async def me(user: Dict[str, Any] = Depends(get_current_user)):
    """Return the profile of the authenticated caller."""
    return {"user": _public_user(user)}


# ----------------------------------------------------------------------
# Administration
# ----------------------------------------------------------------------
@router.get("/admin/stats")
async def admin_stats(user: Dict[str, Any] = Depends(_require_admin)):
    """Counts for the admin dashboard (flat shape, as the panel expects)."""
    db = get_db_manager()
    try:
        stats = await db.get_stats()
    except Exception as exc:  # noqa: BLE001 - report, do not crash
        logger.error("Admin stats query failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The database is unavailable.",
        ) from exc
    return stats


@router.get("/admin/users")
async def admin_list_users(
    limit: int = 50,
    offset: int = 0,
    user: Dict[str, Any] = Depends(_require_admin),
):
    """List users (password hashes are never returned)."""
    _require(user, "users:read")
    db = get_db_manager()
    try:
        rows = await db.list_users(limit=min(limit, 200), offset=max(offset, 0))
    except Exception as exc:  # noqa: BLE001 - report, do not crash
        logger.error("Admin user list failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The database is unavailable.",
        ) from exc
    return rows


def _isoformat(value: Any) -> Any:
    """Serialize a timestamp that may already be a string.

    asyncpg returns ``datetime`` for ``timestamptz``, but a driver or test
    double may hand back an ISO string. Both must serialize identically.
    """
    return value.isoformat() if isinstance(value, datetime) else value


@router.post("/admin/users", status_code=status.HTTP_201_CREATED)
async def admin_create_user(
    payload: CreateUserRequest,
    user: Dict[str, Any] = Depends(_require_admin),
):
    """Create a user."""
    _require(user, "users:write")
    if payload.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"role must be one of {', '.join(VALID_ROLES)}",
        )
    if payload.language_preference not in ("ar", "en"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="language_preference must be 'ar' or 'en'",
        )

    db = get_db_manager()
    try:
        created = await db.create_user(
            username=payload.username,
            email=payload.email,
            password_hash=hash_password(payload.password),
            role=payload.role,
            language_preference=payload.language_preference,
        )
    except Exception as exc:  # noqa: BLE001 - a unique violation is expected
        logger.warning("Admin create user failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That username or email is already taken.",
        ) from exc

    return {
        "user": {
            "id": created.id,
            "username": created.username,
            "email": created.email,
            "role": created.role,
            "language_preference": created.language_preference,
            "is_active": created.is_active,
            "created_at": _isoformat(created.created_at),
        }
    }


@router.patch("/admin/users/{user_id}/role")
async def admin_update_role(
    user_id: str,
    payload: RoleRequest,
    user: Dict[str, Any] = Depends(_require_admin),
):
    """Change a user's role."""
    _require(user, "users:write")
    if payload.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"role must be one of {', '.join(VALID_ROLES)}",
        )
    if str(user.get("id")) == str(user_id) and payload.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot remove your own admin role.",
        )

    db = get_db_manager()
    try:
        updated = await db.update_user_role(user_id, payload.role)
    except Exception as exc:  # noqa: BLE001 - report, do not crash
        logger.error("Admin role update failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The database is unavailable.",
        ) from exc
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )
    return {"id": user_id, "role": payload.role}


@router.delete("/admin/users/{user_id}")
async def admin_delete_user(
    user_id: str,
    user: Dict[str, Any] = Depends(_require_admin),
):
    """Delete a user."""
    _require(user, "users:delete")
    if str(user.get("id")) == str(user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account.",
        )

    db = get_db_manager()
    try:
        deleted = await db.delete_user(user_id)
    except Exception as exc:  # noqa: BLE001 - report, do not crash
        logger.error("Admin user delete failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The database is unavailable.",
        ) from exc
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )
    return {"deleted": user_id}


@router.get("/admin/conversations")
async def admin_list_conversations(
    limit: int = 50,
    offset: int = 0,
    user: Dict[str, Any] = Depends(_require_admin),
):
    """List conversations with their owner."""
    _require(user, "audit:read")
    db = get_db_manager()
    try:
        rows = await db.list_conversations(limit=min(limit, 200), offset=max(offset, 0))
    except Exception as exc:  # noqa: BLE001 - report, do not crash
        logger.error("Admin conversation list failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The database is unavailable.",
        ) from exc
    return rows


@router.delete("/admin/conversations/{conversation_id}")
async def admin_delete_conversation(
    conversation_id: str,
    user: Dict[str, Any] = Depends(_require_admin),
):
    """Delete a conversation and its messages."""
    _require(user, "tasks:delete")
    db = get_db_manager()
    try:
        deleted = await db.delete_conversation(conversation_id)
    except Exception as exc:  # noqa: BLE001 - report, do not crash
        logger.error("Admin conversation delete failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The database is unavailable.",
        ) from exc
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found."
        )
    return {"deleted": conversation_id}
