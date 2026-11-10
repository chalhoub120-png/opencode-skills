"""Role-Based Access Control (RBAC) for the AI Assistant.

Supports both role-level permissions and document-level access control.
Document-level access is enforced at retrieval time, not merely in the UI.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set

from db.models import DatabaseManager

logger = logging.getLogger(__name__)

# Role hierarchy: higher roles inherit permissions of lower roles.
# A viewer is read-only and must never inherit the "user" write permissions;
# getting this backwards is a privilege-escalation bug (CWE-269).
ROLE_HIERARCHY: Dict[str, List[str]] = {
    "viewer": [],
    "user": [],
    "developer": ["user"],
    "admin": ["developer"],
}

# Permissions by role
ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    "viewer": {
        "chat:read",
        "knowledge:read",
        "memory:read",
        "agents:read",
        "settings:read",
    },
    "user": {
        "chat:read",
        "chat:write",
        "knowledge:read",
        "memory:read",
        "memory:write",
        "tasks:read",
        "tasks:write",
        "agents:read",
        "settings:read",
    },
    "developer": {
        "chat:read",
        "chat:write",
        "knowledge:read",
        "knowledge:write",
        "memory:read",
        "memory:write",
        "tasks:read",
        "tasks:write",
        "agents:read",
        "settings:read",
        "tools:github",
        "tools:gitlab",
        "tools:postgres",
        "tools:file",
        "tools:docker",
        "tools:terminal",
        "agents:manage",
    },
    "admin": {
        "chat:read",
        "chat:write",
        "knowledge:read",
        "knowledge:write",
        "knowledge:delete",
        "memory:read",
        "memory:write",
        "memory:delete",
        "tasks:read",
        "tasks:write",
        "tasks:delete",
        "users:read",
        "users:write",
        "users:delete",
        "tools:github",
        "tools:gitlab",
        "tools:postgres",
        "tools:rest",
        "tools:file",
        "tools:docker",
        "tools:terminal",
        "agents:manage",
        "agents:read",
        "workflows:manage",
        "settings:write",
        "settings:read",
        "audit:read",
    },
}


class RBACManager:
    """Checks permissions based on user role and document access."""

    def __init__(
        self,
        enabled: bool = True,
        db_manager: Optional[DatabaseManager] = None,
    ) -> None:
        self.enabled = enabled
        self.db = db_manager

    def get_user_permissions(self, role: str) -> Set[str]:
        """Get all permissions for a role, including inherited ones."""
        permissions: Set[str] = set()
        roles_to_check = [role] + ROLE_HIERARCHY.get(role, [])
        for r in roles_to_check:
            permissions.update(ROLE_PERMISSIONS.get(r, set()))
        return permissions

    def has_permission(self, role: str, permission: str) -> bool:
        """Check if a role has a specific role-level permission."""
        if not self.enabled:
            return True
        return permission in self.get_user_permissions(role)

    def require_permission(self, role: str, permission: str) -> None:
        """Raise PermissionError if the role lacks the permission."""
        if not self.has_permission(role, permission):
            raise PermissionError(
                f"Role '{role}' does not have permission '{permission}'"
            )

    async def can_access_document(
        self,
        user_id: str,
        document_id: str,
        required_permission: str = "read",
    ) -> bool:
        """Check document-level access control.

        Enforced at retrieval time via DatabaseManager.check_document_access.
        """
        if self.db is None:
            logger.warning("DatabaseManager not configured for document access check")
            return False
        return await self.db.check_document_access(
            user_id, document_id, required_permission
        )

    async def get_accessible_documents(
        self,
        user_id: str,
        required_permission: str = "read",
    ) -> List[str]:
        """Return list of document IDs the user can access."""
        if self.db is None:
            logger.warning("DatabaseManager not configured for document access check")
            return []
        return await self.db.get_accessible_document_ids(user_id, required_permission)


# ---------------------------------------------------------------------------
# Shared instance (created lazily by dependency providers)
# ---------------------------------------------------------------------------


def get_rbac_manager(
    enabled: bool = True, db_manager: Optional[DatabaseManager] = None
) -> RBACManager:
    """Return a configured RBAC manager instance."""
    return RBACManager(enabled=enabled, db_manager=db_manager)
