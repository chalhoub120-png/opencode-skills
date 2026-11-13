"""Notification endpoints backed by the real ``notifications`` table.

The n8n workflow stays the only writer: it validates the payload, checks that
the user exists and inserts the row. This router never inserts directly, so
there is exactly one place where a notification can enter the database.

- ``POST /notify``                      ask n8n to store a notification
- ``GET /notifications``                read the caller's notifications
- ``PATCH /notifications/{id}/read``    mark one of them as read
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from api.deps import get_current_user, get_db_manager, get_orchestrator

logger = logging.getLogger(__name__)

router = APIRouter(tags=["notifications"])

# The same shape the n8n workflow accepts; keeping the limits here means a
# caller gets a 422 before a network round trip.
MAX_TYPE_LENGTH = 32
MAX_CHANNEL_LENGTH = 32
MAX_MESSAGE_LENGTH = 4000


class NotificationRequest(BaseModel):
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)
    type: str = Field(default="info", max_length=MAX_TYPE_LENGTH)
    channel: str = Field(default="in_app", max_length=MAX_CHANNEL_LENGTH)


def _user_id(user: Dict[str, Any]) -> str:
    """Return the caller's UUID, or fail with a clear reason.

    The anonymous local user has the id ``local``; it cannot own a
    notification, so the API refuses instead of guessing an owner.
    """
    raw = str(user.get("id") or "")
    if not re.fullmatch(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        raw,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A signed-in user with a UUID id is required.",
        )
    try:
        return str(UUID(raw))
    except ValueError as exc:  # pragma: no cover - the regex already guarantees it
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user id is not a valid UUID.",
        ) from exc


@router.post("/notify")
async def create_notification(
    payload: NotificationRequest,
    user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Store a notification through the n8n workflow.

    ``user_id`` is taken from the authenticated caller, never from the body,
    so a request cannot write a notification for somebody else.
    """
    user_id = _user_id(user)
    result = await get_orchestrator().route_to_n8n(
        user_id=user_id,
        payload={
            "message": payload.message,
            "type": payload.type,
            "channel": payload.channel,
        },
    )
    if not result.success:
        # n8n answers with the exact validation reason; surface it unchanged.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error or "The notification was rejected.",
        )

    stored = (result.tool_results or [{}])[0].get("response", {})
    return {"success": True, "notification": stored}


@router.get("/notifications")
async def list_notifications(
    unread_only: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Read the caller's notifications, newest first."""
    user_id = _user_id(user)
    rows = await get_db_manager().list_notifications(
        user_id=user_id,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )
    return {"notifications": rows, "count": len(rows)}


@router.patch("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Mark one of the caller's notifications as read."""
    user_id = _user_id(user)
    updated = await get_db_manager().mark_notification_read(
        notification_id=notification_id,
        user_id=user_id,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )
    return {"success": True, "id": notification_id}
