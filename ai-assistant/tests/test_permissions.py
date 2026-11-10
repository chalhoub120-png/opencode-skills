"""Document permission enforcement tests.

Tests that users cannot retrieve documents they don't have access to,
and that access control is enforced at retrieval time (not just UI).
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from security.rbac import RBACManager
from db.models import DatabaseManager


# ---------------------------------------------------------------------------
# RBAC document access tests (mock-based)
# ---------------------------------------------------------------------------

class FakeDB:
    """Fake database for testing permission logic without PostgreSQL."""

    def __init__(self) -> None:
        self.users: Dict[str, Dict[str, Any]] = {
            "user-1": {"id": "user-1", "role": "user", "is_active": True},
            "user-2": {"id": "user-2", "role": "user", "is_active": True},
            "admin-1": {"id": "admin-1", "role": "admin", "is_active": True},
        }
        self.documents: Dict[str, Dict[str, Any]] = {
            "doc-public": {
                "id": "doc-public",
                "uploaded_by": "user-1",
                "access_level": "public",
            },
            "doc-private-user1": {
                "id": "doc-private-user1",
                "uploaded_by": "user-1",
                "access_level": "private",
            },
            "doc-project": {
                "id": "doc-project",
                "uploaded_by": "user-1",
                "access_level": "project",
            },
        }
        self.permissions: List[Dict[str, Any]] = []

    async def check_document_access(
        self,
        user_id: str,
        document_id: str,
        required_permission: str = "read",
    ) -> bool:
        user = self.users.get(user_id)
        if not user:
            return False
        if user["role"] == "admin":
            return True

        doc = self.documents.get(document_id)
        if not doc:
            return False

        # Owner always has access
        if doc["uploaded_by"] == user_id:
            return True

        # Public read access
        if doc["access_level"] == "public" and required_permission == "read":
            return True

        # Explicit permissions
        for perm in self.permissions:
            if perm["document_id"] == document_id:
                if perm.get("user_id") == user_id or perm.get("role") == user["role"]:
                    hierarchy = {"read": 1, "write": 2, "admin": 3}
                    return hierarchy.get(perm["permission"], 0) >= hierarchy.get(
                        required_permission, 0
                    )

        return False

    async def grant_document_access(
        self,
        document_id: str,
        user_id: Optional[str],
        role: Optional[str],
        permission: str,
        granted_by: str,
    ) -> Dict[str, Any]:
        self.permissions.append({
            "document_id": document_id,
            "user_id": user_id,
            "role": role,
            "permission": permission,
            "granted_by": granted_by,
        })
        return {"id": "perm-001", "document_id": document_id, "permission": permission}

    async def revoke_document_access(
        self,
        document_id: str,
        user_id: Optional[str] = None,
        role: Optional[str] = None,
    ) -> None:
        self.permissions = [
            p for p in self.permissions
            if not (p["document_id"] == document_id
                    and (user_id is None or p.get("user_id") == user_id)
                    and (role is None or p.get("role") == role))
        ]

    async def get_accessible_document_ids(
        self,
        user_id: str,
        required_permission: str = "read",
    ) -> List[str]:
        accessible = []
        for doc_id, doc in self.documents.items():
            if await self.check_document_access(user_id, doc_id, required_permission):
                accessible.append(doc_id)
        return accessible


class FakeRBAC(RBACManager):
    """RBAC with fake DB for testing."""

    def __init__(self) -> None:
        super().__init__(enabled=True, db_manager=FakeDB())  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_admin_can_access_all_documents():
    rbac = FakeRBAC()
    result = asyncio.run(rbac.can_access_document("admin-1", "doc-private-user1", "read"))
    assert result is True, "Admin should access any document"


def test_owner_can_access_own_document():
    rbac = FakeRBAC()
    result = asyncio.run(rbac.can_access_document("user-1", "doc-private-user1", "read"))
    assert result is True, "Owner should access their own document"


def test_other_user_cannot_access_private_document():
    rbac = FakeRBAC()
    result = asyncio.run(rbac.can_access_document("user-2", "doc-private-user1", "read"))
    assert result is False, "Non-owner should not access private document"


def test_public_document_accessible_to_all():
    rbac = FakeRBAC()
    result = asyncio.run(rbac.can_access_document("user-2", "doc-public", "read"))
    assert result is True, "Public document should be readable by all"


def test_get_accessible_documents_filters_correctly():
    rbac = FakeRBAC()
    accessible = asyncio.run(rbac.get_accessible_documents("user-2", "read"))
    assert "doc-public" in accessible, "user-2 should see public document"
    assert "doc-private-user1" not in accessible, (
        "user-2 should not see user-1's private document"
    )


def test_granted_permission_allows_access():
    rbac = FakeRBAC()
    db = rbac.db  # type: ignore[attr-defined]
    # Grant user-2 read access to user-1's private document
    asyncio.run(
        db.grant_document_access(
            document_id="doc-private-user1",
            user_id="user-2",
            role=None,
            permission="read",
            granted_by="user-1",
        )
    )
    result = asyncio.run(rbac.can_access_document("user-2", "doc-private-user1", "read"))
    assert result is True, "Granted read permission should allow access"


def test_revoked_permission_denies_access():
    rbac = FakeRBAC()
    db = rbac.db  # type: ignore[attr-defined]
    # First grant
    asyncio.run(
        db.grant_document_access(
            document_id="doc-private-user1",
            user_id="user-2",
            role=None,
            permission="read",
            granted_by="user-1",
        )
    )
    # Then revoke
    asyncio.run(db.revoke_document_access(document_id="doc-private-user1", user_id="user-2"))
    result = asyncio.run(rbac.can_access_document("user-2", "doc-private-user1", "read"))
    assert result is False, "Revoked permission should deny access"


if __name__ == "__main__":
    tests = [
        test_admin_can_access_all_documents,
        test_owner_can_access_own_document,
        test_other_user_cannot_access_private_document,
        test_public_document_accessible_to_all,
        test_get_accessible_documents_filters_correctly,
        test_granted_permission_allows_access,
        test_revoked_permission_denies_access,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            print(f"PASS: {test.__name__}")
            passed += 1
        except Exception as exc:
            print(f"FAIL: {test.__name__}: {exc}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed out of {len(tests)} tests")
