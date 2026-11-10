"""Audit logging for security and action tracking."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from db.models import DatabaseManager
from security.redaction import sanitize

logger = logging.getLogger(__name__)


class AuditLogger:
    """Writes audit log entries to PostgreSQL."""

    def __init__(self, db_manager: DatabaseManager, enabled: bool = True) -> None:
        self.db = db_manager
        self.enabled = enabled

    async def log(
        self,
        user_id: str,
        action: str,
        resource: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Write an audit log entry."""
        if not self.enabled:
            logger.warning(
                "Audit logging is disabled; entry for action=%s was not written",
                action,
            )
            return
        # Recursively redact credentials before storage. Patterns target real
        # credential shapes, so ordinary prose such as "token budget" is kept.
        safe_metadata = sanitize(metadata or {})
        try:
            await self.db.write_audit_log(
                user_id=user_id,
                action=action,
                resource=resource,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=sanitize(user_agent) if user_agent else user_agent,
                metadata=safe_metadata,
            )
        except Exception as exc:
            logger.warning("Audit log write failed: %s", exc)

    async def log_security_event(
        self,
        user_id: str,
        event: str,
        detail: Dict[str, Any],
    ) -> None:
        """Log a security-specific event."""
        await self.log(
            user_id=user_id,
            action=f"security:{event}",
            resource="security",
            metadata=detail,
        )
