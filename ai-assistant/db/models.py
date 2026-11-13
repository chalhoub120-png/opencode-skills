"""Database access layer for PostgreSQL using asyncpg.

Provides typed access to all tables defined in schema.sql:
users, agents, projects, conversations, messages, memories, tasks, documents, audit_logs.
"""

from __future__ import annotations

import logging
import json
import os
import hmac
import base64
import struct
import hashlib
import time
from uuid import UUID
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

try:
    import asyncpg  # type: ignore
except ImportError as exc:  # pragma: no cover - dependency check
    raise RuntimeError("asyncpg is required for database access") from exc

logger = logging.getLogger(__name__)


@dataclass
class UserRow:
    id: str
    username: str
    email: str
    role: str
    language_preference: str
    is_active: bool
    created_at: datetime


@dataclass
class ConversationRow:
    id: str
    user_id: str
    project_id: Optional[str]
    title: Optional[str]
    language: str
    created_at: datetime


@dataclass
class MessageRow:
    id: str
    conversation_id: str
    role: str
    content: str
    language: Optional[str]
    agent_id: Optional[str]
    created_at: datetime


@dataclass
class MemoryRow:
    id: str
    user_id: str
    content: str
    memory_type: str
    metadata: Dict[str, Any]
    created_at: datetime


class DatabaseManager:
    """Async PostgreSQL manager for the AI Assistant."""

    def __init__(self, database_url: Optional[str] = None) -> None:
        url = database_url or os.environ.get("DATABASE_URL")
        if not url:
            raise RuntimeError(
                "DATABASE_URL is required; configure it outside the source code."
            )
        self.database_url = url
        # asyncpg uses postgresql:// not postgresql+asyncpg://
        self._asyncpg_url = self.database_url.replace(
            "postgresql+asyncpg://", "postgresql://"
        )
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                self._asyncpg_url,
                min_size=2,
                max_size=10,
            )
            logger.info("Database pool connected")

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    @asynccontextmanager
    async def _acquire(self):
        if self._pool is None:
            await self.connect()
        assert self._pool is not None
        async with self._pool.acquire() as conn:
            yield conn

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------
    async def create_user(
        self,
        username: str,
        email: str,
        password_hash: str,
        role: str = "user",
        language_preference: str = "ar",
        api_key: Optional[str] = None,
    ) -> UserRow:
        async with self._acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO users (username, email, password_hash, role, language_preference, api_key)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id, username, email, role, language_preference, is_active, created_at
                """,
                username,
                email,
                password_hash,
                role,
                language_preference,
                api_key,
            )
        return UserRow(
            id=str(row["id"]),
            username=row["username"],
            email=row["email"],
            role=row["role"],
            language_preference=row["language_preference"],
            is_active=row["is_active"],
            created_at=row["created_at"],
        )

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        async with self._acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, username, email, role, language_preference, is_active FROM users WHERE id = $1",
                user_id,
            )
        if not row:
            return None
        return self._row_to_dict(row)

    async def get_user_by_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        async with self._acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, username, email, role, language_preference, is_active FROM users WHERE api_key = $1",
                api_key,
            )
        if not row:
            return None
        return self._row_to_dict(row)

    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Fetch a user including the password hash (login path only)."""
        async with self._acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, username, email, password_hash, role,
                       language_preference, is_active
                FROM users WHERE username = $1
                """,
                username,
            )
        if not row:
            return None
        return self._row_to_dict(row)

    async def list_users(
        self, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List users for the admin panel (never returns password hashes)."""
        async with self._acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, username, email, role, language_preference,
                       is_active, created_at
                FROM users ORDER BY created_at DESC LIMIT $1 OFFSET $2
                """,
                limit,
                offset,
            )
        return [self._row_to_dict(row) for row in rows]

    async def update_user_role(self, user_id: str, role: str) -> bool:
        """Change a user's role. Returns False when the user does not exist."""
        async with self._acquire() as conn:
            result = await conn.execute(
                "UPDATE users SET role = $2 WHERE id = $1", user_id, role
            )
        return result.endswith("1")

    async def set_user_active(self, user_id: str, is_active: bool) -> bool:
        """Activate or deactivate a user. Returns False when it does not exist."""
        async with self._acquire() as conn:
            result = await conn.execute(
                "UPDATE users SET is_active = $2 WHERE id = $1", user_id, is_active
            )
        return result.endswith("1")

    async def delete_user(self, user_id: str) -> bool:
        """Delete a user and everything that cascades from it."""
        async with self._acquire() as conn:
            result = await conn.execute("DELETE FROM users WHERE id = $1", user_id)
        return result.endswith("1")

    async def list_conversations(
        self, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List conversations with their owner for the admin panel.

        `updated_at` is the last message time, falling back to the creation
        time, so the panel can show real activity instead of a copy of
        `created_at`.
        """
        async with self._acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT c.id, c.user_id, c.project_id, c.title, c.language,
                       c.created_at,
                       COALESCE(m.last_activity, c.created_at) AS updated_at,
                       COALESCE(u.username, '') AS username,
                       COALESCE(u.email, '') AS email
                FROM conversations c
                LEFT JOIN users u ON u.id = c.user_id
                LEFT JOIN LATERAL (
                    SELECT max(created_at) AS last_activity
                    FROM messages WHERE conversation_id = c.id
                ) m ON TRUE
                ORDER BY c.created_at DESC LIMIT $1 OFFSET $2
                """,
                limit,
                offset,
            )
        return [self._row_to_dict(row) for row in rows]

    async def list_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List one user's notifications, newest first.

        n8n is the only writer; this read path never inserts rows.
        """
        async with self._acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, user_id, message, type, channel, read, metadata,
                       created_at
                FROM notifications
                WHERE user_id = $1
                  AND (NOT $2 OR read = FALSE)
                ORDER BY created_at DESC LIMIT $3 OFFSET $4
                """,
                user_id,
                unread_only,
                limit,
                offset,
            )
        return [self._row_to_dict(row) for row in rows]

    async def mark_notification_read(self, notification_id: str, user_id: str) -> bool:
        """Mark one of the user's notifications as read.

        Scoping the update by ``user_id`` stops one user from touching another
        user's rows.
        """
        async with self._acquire() as conn:
            result = await conn.execute(
                """
                UPDATE notifications SET read = TRUE
                WHERE id = $1 AND user_id = $2
                """,
                notification_id,
                user_id,
            )
        return result.endswith("1")

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and its messages."""
        async with self._acquire() as conn:
            result = await conn.execute(
                "DELETE FROM conversations WHERE id = $1", conversation_id
            )
        return result.endswith("1")

    async def get_stats(self) -> Dict[str, int]:
        """Counts for the admin dashboard."""
        async with self._acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    (SELECT count(*) FROM users)        AS users,
                    (SELECT count(*) FROM users WHERE is_active) AS active_users,
                    (SELECT count(*) FROM users WHERE role = 'admin') AS admins,
                    (SELECT count(*) FROM conversations) AS conversations,
                    (SELECT count(*) FROM messages)      AS messages,
                    (SELECT count(*) FROM memories)      AS memories,
                    (SELECT count(*) FROM documents)     AS documents,
                    (SELECT count(*) FROM audit_logs)    AS audit_logs
                """
            )
        return {key: int(row[key]) for key in row.keys()}

    # ------------------------------------------------------------------
    # Conversations
    # ------------------------------------------------------------------
    async def create_conversation(
        self,
        user_id: str,
        project_id: Optional[str] = None,
        title: Optional[str] = None,
        language: str = "ar",
    ) -> ConversationRow:
        async with self._acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO conversations (user_id, project_id, title, language)
                VALUES ($1, $2, $3, $4)
                RETURNING id, user_id, project_id, title, language, created_at
                """,
                user_id,
                project_id,
                title,
                language,
            )
        return ConversationRow(
            id=str(row["id"]),
            user_id=str(row["user_id"]),
            project_id=str(row["project_id"]) if row["project_id"] else None,
            title=row["title"],
            language=row["language"],
            created_at=row["created_at"],
        )

    async def ensure_conversation(
        self,
        conversation_id: str,
        user_id: str,
        project_id: Optional[str] = None,
        language: str = "ar",
    ) -> None:
        """Ensure conversation row exists (for IDs generated by /chat)."""
        try:
            UUID(conversation_id)
        except (ValueError, TypeError, AttributeError):
            return
        async with self._acquire() as conn:
            await conn.execute(
                """
                INSERT INTO conversations (id, user_id, project_id, title, language)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (id) DO NOTHING
                """,
                conversation_id,
                user_id,
                project_id,
                None,
                language or "ar",
            )

    async def create_conversation_message(
        self,
        conversation_id: Optional[str],
        user_id: str,
        project_id: Optional[str] = None,
        role: str = "user",
        content: str = "",
        language: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a conversation (if needed) and a message within it."""
        if conversation_id is None:
            conv = await self.create_conversation(
                user_id=user_id, project_id=project_id, language=language or "ar"
            )
            conversation_id = conv.id
        else:
            await self.ensure_conversation(
                conversation_id=conversation_id,
                user_id=user_id,
                project_id=project_id,
                language=language or "ar",
            )
        row = await self.create_message(
            conversation_id=conversation_id,
            user_id=user_id,
            project_id=project_id,
            role=role,
            content=content,
            language=language,
            agent_id=agent_id,
        )
        return {
            "id": row.id,
            "conversation_id": conversation_id,
            "role": row.role,
            "content": row.content,
            "language": row.language,
            "agent_id": row.agent_id,
            "created_at": row.created_at,
        }

    async def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        async with self._acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, user_id, project_id, title, language FROM conversations WHERE id = $1",
                conversation_id,
            )
        if not row:
            return None
        return dict(row)

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------
    async def create_message(
        self,
        conversation_id: str,
        user_id: str,
        project_id: Optional[str],
        role: str,
        content: str,
        language: Optional[str] = None,
        agent_id: Optional[str] = None,
        tool_calls: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MessageRow:
        async with self._acquire() as conn:
            # Validate agent_id is a UUID; if not, store as None (FK constraint)
            agent_uuid = None
            if agent_id is not None:
                try:
                    agent_uuid = UUID(agent_id)
                except (ValueError, AttributeError):
                    agent_uuid = None
            row = await conn.fetchrow(
                """
                INSERT INTO messages (conversation_id, role, content, language, agent_id, tool_calls, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id, conversation_id, role, content, language, agent_id, created_at
                """,
                conversation_id,
                role,
                content,
                language,
                agent_uuid,
                json.dumps(tool_calls) if tool_calls is not None else None,
                json.dumps(metadata) if metadata is not None else None,
            )
        # Store a short-term memory reference for assistant messages
        if role == "assistant":
            await self._store_message_memory(
                user_id=user_id,
                conversation_id=conversation_id,
                content=content,
                agent_id=agent_id,
            )
        return MessageRow(
            id=str(row["id"]),
            conversation_id=str(row["conversation_id"]),
            role=row["role"],
            content=row["content"],
            language=row["language"],
            agent_id=str(row["agent_id"]) if row["agent_id"] else None,
            created_at=row["created_at"],
        )

    async def _store_message_memory(
        self,
        user_id: str,
        conversation_id: str,
        content: str,
        agent_id: Optional[str],
    ) -> None:
        try:
            async with self._acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO memories (user_id, conversation_id, content, memory_type, metadata)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    user_id,
                    conversation_id,
                    content,
                    "conversation_summary",
                    json.dumps({"agent_id": agent_id}) if agent_id else None,
                )
        except Exception as exc:  # pragma: no cover - best effort
            logger.warning("Failed to store message memory: %s", exc)

    async def get_conversation_messages(
        self,
        conversation_id: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        try:
            UUID(conversation_id)
        except (ValueError, TypeError, AttributeError):
            return None
        async with self._acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, role, content, language, agent_id, created_at
                FROM messages
                WHERE conversation_id = $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                conversation_id,
                limit,
            )
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Memories
    # ------------------------------------------------------------------
    async def create_memory(
        self,
        user_id: str,
        content: str,
        memory_type: str,
        project_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        async with self._acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO memories (user_id, project_id, conversation_id, content, memory_type, metadata, embedding)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id, content, memory_type, metadata, created_at
                """,
                user_id,
                project_id,
                conversation_id,
                content,
                memory_type,
                metadata,
                embedding,
            )
        return dict(row)

    async def search_memory(
        self,
        user_id: str,
        query: str,
        project_id: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Semantic-ish memory search. Falls back to text similarity."""
        async with self._acquire() as conn:
            if project_id:
                rows = await conn.fetch(
                    """
                    SELECT id, content, memory_type, metadata, created_at
                    FROM memories
                    WHERE user_id = $1 AND project_id = $2
                      AND content ILIKE $3
                    ORDER BY created_at DESC
                    LIMIT $4
                    """,
                    user_id,
                    project_id,
                    f"%{query}%",
                    limit,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT id, content, memory_type, metadata, created_at
                    FROM memories
                    WHERE user_id = $1
                      AND content ILIKE $2
                    ORDER BY created_at DESC
                    LIMIT $3
                    """,
                    user_id,
                    f"%{query}%",
                    limit,
                )
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------
    async def create_task(
        self,
        user_id: str,
        title: str,
        description: Optional[str] = None,
        project_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        async with self._acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO tasks (user_id, project_id, conversation_id, title, description, agent_id, workflow_id)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id, title, status, created_at
                """,
                user_id,
                project_id,
                conversation_id,
                title,
                description,
                agent_id,
                workflow_id,
            )
        return dict(row)

    async def update_task_status(
        self,
        task_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        async with self._acquire() as conn:
            await conn.execute(
                """
                UPDATE tasks
                SET status = $2, result = $3, error = $4,
                    updated_at = NOW(),
                    completed_at = CASE WHEN $2 IN ('completed', 'failed', 'cancelled') THEN NOW() ELSE completed_at END
                WHERE id = $1
                """,
                task_id,
                status,
                json.dumps(result) if result is not None else None,
                error,
            )

    # ------------------------------------------------------------------
    # Documents
    # ------------------------------------------------------------------
    async def create_document(
        self,
        project_id: Optional[str],
        uploaded_by: Optional[str],
        filename: str,
        original_filename: str,
        mime_type: str,
        file_path: str,
        file_size: int,
        content_hash: str,
        language: Optional[str],
        chunk_count: int,
        qdrant_collection: Optional[str],
        metadata: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        async with self._acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO documents
                (project_id, uploaded_by, filename, original_filename, mime_type, file_path,
                 file_size, content_hash, language, chunk_count, qdrant_collection, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                RETURNING id
                """,
                project_id,
                uploaded_by,
                filename,
                original_filename,
                mime_type,
                file_path,
                file_size,
                content_hash,
                language,
                chunk_count,
                qdrant_collection,
                metadata,
            )
        return dict(row)

    # ------------------------------------------------------------------
    # Audit logs
    # ------------------------------------------------------------------
    async def write_audit_log(
        self,
        user_id: Optional[str],
        action: str,
        resource: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        async with self._acquire() as conn:
            await conn.execute(
                """
                INSERT INTO audit_logs (user_id, action, resource, resource_id, ip_address, user_agent, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                user_id,
                action,
                resource,
                resource_id,
                ip_address,
                user_agent,
                json.dumps(metadata) if metadata is not None else None,
            )

    # ------------------------------------------------------------------
    # Document permissions (access control enforced at retrieval time)
    # ------------------------------------------------------------------
    async def check_document_access(
        self,
        user_id: str,
        document_id: str,
        required_permission: str = "read",
    ) -> bool:
        """Return True if the user has the required permission on the document.

        Access rules:
        - Document owner always has all permissions.
        - Admins always have all permissions.
        - document_permissions table grants read/write/admin to specific users or roles.
        - access_level='public' grants read to all authenticated users.
        - access_level='project' grants read to members of the project.
        - access_level='private' grants read only to the owner and explicitly permitted users.
        """
        async with self._acquire() as conn:
            # Check user role
            user_role = await conn.fetchval(
                "SELECT role FROM users WHERE id = $1 AND is_active = TRUE",
                user_id,
            )
            if user_role == "admin":
                return True

            # Check ownership
            owner_id = await conn.fetchval(
                "SELECT uploaded_by FROM documents WHERE id = $1",
                document_id,
            )
            if owner_id and str(owner_id) == user_id:
                return True

            # Check access_level
            access_level = await conn.fetchval(
                "SELECT access_level FROM documents WHERE id = $1",
                document_id,
            )
            if access_level == "public" and required_permission == "read":
                return True

            # Check explicit document_permissions
            perm = await conn.fetchval(
                """
                SELECT permission FROM document_permissions
                WHERE document_id = $1
                  AND (user_id = $2 OR role = $3)
                ORDER BY
                  CASE WHEN user_id = $2 THEN 1 ELSE 2 END
                LIMIT 1
                """,
                document_id,
                user_id,
                user_role,
            )
            if perm:
                hierarchy = {"read": 1, "write": 2, "admin": 3}
                return hierarchy.get(perm, 0) >= hierarchy.get(required_permission, 0)

            return False

    async def get_accessible_document_ids(
        self,
        user_id: str,
        required_permission: str = "read",
    ) -> List[str]:
        """Return list of document IDs the user can access."""
        async with self._acquire() as conn:
            user_role = await conn.fetchval(
                "SELECT role FROM users WHERE id = $1 AND is_active = TRUE",
                user_id,
            )
            if user_role == "admin":
                rows = await conn.fetch("SELECT id FROM documents")
                return [str(r["id"]) for r in rows]

            rows = await conn.fetch(
                """
                SELECT DISTINCT d.id
                FROM documents d
                WHERE d.uploaded_by = $1
                   OR d.access_level = 'public'
                   OR EXISTS (
                     SELECT 1 FROM document_permissions dp
                     WHERE dp.document_id = d.id
                       AND (dp.user_id = $1 OR dp.role = $2)
                   )
                """,
                user_id,
                user_role,
            )
        return [str(r["id"]) for r in rows]

    async def grant_document_access(
        self,
        document_id: str,
        user_id: Optional[str],
        role: Optional[str],
        permission: str,
        granted_by: str,
    ) -> Dict[str, Any]:
        async with self._acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO document_permissions (document_id, user_id, role, permission, granted_by)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (document_id, user_id, role) DO UPDATE
                SET permission = EXCLUDED.permission, granted_by = EXCLUDED.granted_by,
                    granted_at = NOW()
                RETURNING id, document_id, user_id, role, permission, granted_at
                """,
                document_id,
                user_id,
                role,
                permission,
                granted_by,
            )
        return dict(row)

    async def revoke_document_access(
        self,
        document_id: str,
        user_id: Optional[str] = None,
        role: Optional[str] = None,
    ) -> None:
        async with self._acquire() as conn:
            await conn.execute(
                """
                DELETE FROM document_permissions
                WHERE document_id = $1
                  AND ($2 IS NULL OR user_id = $2)
                  AND ($3 IS NULL OR role = $3)
                """,
                document_id,
                user_id,
                role,
            )

    async def log_document_change(
        self,
        document_id: str,
        change_type: str,
        old_content_hash: Optional[str] = None,
        new_content_hash: Optional[str] = None,
        changed_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        async with self._acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO document_change_log
                (document_id, change_type, old_content_hash, new_content_hash, changed_by)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id, document_id, change_type, changed_at
                """,
                document_id,
                change_type,
                old_content_hash,
                new_content_hash,
                changed_by,
            )
        return dict(row)

    async def get_document_changes_since(
        self,
        since: str,
    ) -> List[Dict[str, Any]]:
        async with self._acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT dcl.id, dcl.document_id, dcl.change_type,
                       dcl.old_content_hash, dcl.new_content_hash,
                       dcl.changed_at, d.filename, d.access_level
                FROM document_change_log dcl
                JOIN documents d ON d.id = dcl.document_id
                WHERE dcl.changed_at > $1
                ORDER BY dcl.changed_at DESC
                """,
                since,
            )
        return [dict(r) for r in rows]

    @staticmethod
    def _row_to_dict(row: asyncpg.Record) -> Dict[str, Any]:
        """Convert an asyncpg Record to a JSON-safe dict (datetime -> ISO string)."""
        data: Dict[str, Any] = {}
        for key in row.keys():
            value = row[key]
            if isinstance(value, datetime):
                value = value.isoformat()
            elif isinstance(value, UUID):
                value = str(value)
            data[key] = value
        return data

    async def create_approval_request(
        self,
        user_id: str,
        action_type: str,
        target_resource: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        workflow_id: Optional[str] = None,
        risk_level: str = "medium",
        approval_level: str = "B",
    ) -> Dict[str, Any]:
        async with self._acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO approval_requests
                (user_id, workflow_id, action_type, target_resource, parameters, risk_level, approval_level)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id, status, requested_at, expires_at, risk_level, approval_level
                """,
                user_id,
                workflow_id,
                action_type,
                target_resource,
                json.dumps(parameters) if parameters is not None else None,
                risk_level,
                approval_level,
            )
        return self._row_to_dict(row)

    async def get_approval_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        async with self._acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, user_id, workflow_id, action_type, target_resource,
                       parameters, status, requested_at, expires_at, decided_at, decided_by,
                       decision_reason, risk_level, approval_level
                FROM approval_requests WHERE id = $1
                """,
                request_id,
            )
        return self._row_to_dict(row) if row else None

    async def decide_approval_request(
        self,
        request_id: str,
        decision: str,
        decided_by: str,
        reason: Optional[str] = None,
    ) -> bool:
        """decision: 'approved', 'rejected', or 'expired'"""
        if decision not in ("approved", "rejected", "expired"):
            return False
        async with self._acquire() as conn:
            result = await conn.execute(
                """
                UPDATE approval_requests
                SET status = $2, decided_at = NOW(), decided_by = $3,
                    decision_reason = $4
                WHERE id = $1 AND status = 'pending'
                """,
                request_id,
                decision,
                decided_by,
                reason,
            )
        return result == "UPDATE 1"

    # ------------------------------------------------------------------
    # TOTP verification for level D (critical) approvals
    # ------------------------------------------------------------------
    @staticmethod
    def _totp_encryption_key() -> bytes:
        """Derive a 256-bit key for TOTP-secret encryption from API_SECRET_KEY.

        HKDF-like derivation via SHA-256 with a domain-separation label, so the
        same root secret can safely key other features later.
        """
        root = os.getenv("API_SECRET_KEY", "")
        if not root:
            raise RuntimeError("API_SECRET_KEY is required to store TOTP secrets")
        return hashlib.sha256(b"totp-secret-v1:" + root.encode("utf-8")).digest()

    @classmethod
    def _encrypt_secret(cls, secret_b32: str) -> str:
        """Encrypt a base32 TOTP secret with AES-256-GCM (nonce per secret)."""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        nonce = os.urandom(12)
        ciphertext = AESGCM(cls._totp_encryption_key()).encrypt(
            nonce, secret_b32.encode("ascii"), b"totp-v1"
        )
        return "v1:{}:{}".format(
            base64.urlsafe_b64encode(nonce).decode("ascii"),
            base64.urlsafe_b64encode(ciphertext).decode("ascii"),
        )

    @classmethod
    def _decrypt_secret(cls, stored: str) -> str:
        """Decrypt a stored TOTP secret.

        Values without the ``v1:`` prefix are legacy plaintext base32 rows from
        before encryption was introduced; they are still readable so existing
        enrollments keep working, and are re-encrypted on next enrollment.
        """
        stored = (stored or "").strip()
        if not stored.startswith("v1:"):
            return stored
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        _, nonce_b64, ciphertext_b64 = stored.split(":", 2)
        nonce = base64.urlsafe_b64decode(nonce_b64)
        ciphertext = base64.urlsafe_b64decode(ciphertext_b64)
        return (
            AESGCM(cls._totp_encryption_key())
            .decrypt(nonce, ciphertext, b"totp-v1")
            .decode("ascii")
        )

    async def verify_totp(self, user_id: str, otp_code: str) -> bool:
        """Verify a TOTP code (RFC 6238) for a user. Returns True on success.

        Enforces: 6-digit numeric input, 30-second steps with +/-1 window of
        clock drift, single-use per time step (replay rejected), and lockout
        after 5 consecutive failures for 15 minutes. The row is locked with
        ``FOR UPDATE`` so concurrent guesses cannot race the attempt counter.
        """
        if not otp_code or not otp_code.isdigit() or len(otp_code) != 6:
            return False

        now_dt = datetime.now(timezone.utc)
        async with self._acquire() as conn:
            async with conn.transaction():
                token = await conn.fetchrow(
                    """
                    SELECT id, secret_enc, attempts, last_counter, locked_until
                    FROM approval_tokens
                    WHERE user_id = $1
                    FOR UPDATE
                    """,
                    user_id,
                )
                if not token:
                    return False

                locked_until = token["locked_until"]
                if locked_until is not None and locked_until > now_dt:
                    return False
                # An expired lock resets the counter, otherwise a user would be
                # locked out permanently once attempts reached the threshold.
                attempts = 0 if locked_until is not None else (token["attempts"] or 0)

                try:
                    secret = base64.b32decode(
                        self._decrypt_secret(token["secret_enc"]), casefold=True
                    )
                except Exception:
                    return False

                now_counter = int(time.time()) // 30
                matched: Optional[int] = None
                for candidate in (now_counter - 1, now_counter, now_counter + 1):
                    if hmac.compare_digest(self._totp(secret, candidate), otp_code):
                        matched = candidate
                        break

                last_counter = token["last_counter"] or 0
                if matched is None or matched <= last_counter:
                    # Wrong code, or a replay of an already-used time step.
                    new_attempts = attempts + 1
                    if new_attempts >= 5:
                        await conn.execute(
                            """
                            UPDATE approval_tokens
                            SET attempts = $2, locked_until = $3
                            WHERE user_id = $1
                            """,
                            user_id,
                            new_attempts,
                            now_dt + timedelta(minutes=15),
                        )
                    else:
                        await conn.execute(
                            """
                            UPDATE approval_tokens
                            SET attempts = $2, locked_until = NULL
                            WHERE user_id = $1
                            """,
                            user_id,
                            new_attempts,
                        )
                    return False

                await conn.execute(
                    """
                    UPDATE approval_tokens
                    SET attempts = 0, last_counter = $2, last_used_at = NOW(),
                        locked_until = NULL
                    WHERE user_id = $1
                    """,
                    user_id,
                    matched,
                )
                return True

    @staticmethod
    def _totp(secret: bytes, counter: int) -> str:
        """RFC 6238 TOTP: HMAC-SHA1 dynamic truncation -> 6-digit code."""
        msg = struct.pack(">Q", counter)
        digest = hmac.new(secret, msg, hashlib.sha1).digest()
        offset = digest[-1] & 0x0F
        binary = (
            (digest[offset] & 0x7F) << 24
            | (digest[offset + 1] & 0xFF) << 16
            | (digest[offset + 2] & 0xFF) << 8
            | (digest[offset + 3] & 0xFF)
        )
        code = binary % 1000000
        return f"{code:06d}"

    async def get_pending_approvals(
        self, user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        async with self._acquire() as conn:
            if user_id:
                rows = await conn.fetch(
                    """
                    SELECT id, user_id, workflow_id, action_type, target_resource,
                           parameters, status, requested_at
                    FROM approval_requests
                    WHERE user_id = $1 AND status = 'pending'
                    ORDER BY requested_at DESC
                    """,
                    user_id,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT id, user_id, workflow_id, action_type, target_resource,
                           parameters, status, requested_at
                    FROM approval_requests
                    WHERE status = 'pending'
                    ORDER BY requested_at DESC
                    """,
                )
        return [self._row_to_dict(r) for r in rows]

    # ------------------------------------------------------------------
    # TOTP enrollment (setup shared secret for a user)
    # ------------------------------------------------------------------
    async def enroll_totp(self, user_id: str, secret_b32: Optional[str] = None) -> str:
        """Enroll a user for TOTP. Returns the base32 secret (shown once via QR).

        The secret is stored encrypted (AES-256-GCM) in ``secret_enc``; only the
        caller of this method ever sees the plaintext value.
        """
        if secret_b32 is None:
            secret_b32 = base64.b32encode(os.urandom(20)).decode("ascii")
        try:
            base64.b32decode(secret_b32, casefold=True)
        except Exception as exc:
            raise ValueError("Invalid base32 secret") from exc

        encrypted = self._encrypt_secret(secret_b32)
        async with self._acquire() as conn:
            await conn.execute(
                """
                INSERT INTO approval_tokens (user_id, secret_enc, attempts, last_counter, locked_until, created_at, last_used_at)
                VALUES ($1, $2, 0, 0, NULL, NOW(), NULL)
                ON CONFLICT (user_id) DO UPDATE
                SET secret_enc = EXCLUDED.secret_enc,
                    attempts = 0,
                    last_counter = 0,
                    locked_until = NULL,
                    created_at = NOW(),
                    last_used_at = NULL
                """,
                user_id,
                encrypted,
            )
        return secret_b32

    # ------------------------------------------------------------------
    # Idempotency keys: exactly-once request handling
    # ------------------------------------------------------------------
    async def claim_idempotency(
        self,
        user_id: str,
        endpoint: str,
        key: str,
        request_hash: str,
    ) -> Dict[str, Any]:
        """Claim an idempotency key (IETF idempotency-key semantics).

        Returns ``{"state": str, "response": dict | None}`` where state is:
        - ``claimed``   — caller owns the key and must execute the request
        - ``replay``    — a completed response exists and must be returned as-is
        - ``in_flight`` — another request with the same key is still running
        - ``conflict``  — the key was reused with a different user or payload

        Expired keys and previously failed attempts are reclaimable, so a
        transient failure never poisons the key for 24 hours.
        """
        async with self._acquire() as conn:
            async with conn.transaction():
                inserted = await conn.fetchrow(
                    """
                    INSERT INTO idempotency_keys
                        (user_id, endpoint, key, request_hash, status, created_at, expires_at)
                    VALUES ($1, $2, $3, $4, 'running', NOW(), NOW() + INTERVAL '24 hours')
                    ON CONFLICT (key) DO NOTHING
                    RETURNING id
                    """,
                    user_id,
                    endpoint,
                    key,
                    request_hash,
                )
                if inserted is not None:
                    return {"state": "claimed", "response": None}

                existing = await conn.fetchrow(
                    """
                    SELECT user_id, request_hash, status, response, expires_at
                    FROM idempotency_keys
                    WHERE key = $1
                    FOR UPDATE
                    """,
                    key,
                )
                if existing is None:
                    # Row disappeared between INSERT and SELECT (purged).
                    return {"state": "in_flight", "response": None}

                if str(existing["user_id"]) != str(user_id):
                    return {"state": "conflict", "response": None}

                expired = existing["expires_at"] is not None and (
                    existing["expires_at"] <= datetime.now(timezone.utc)
                )
                if expired:
                    await conn.execute(
                        """
                        UPDATE idempotency_keys
                        SET request_hash = $2, status = 'running', response = NULL,
                            completed_at = NULL, created_at = NOW(),
                            expires_at = NOW() + INTERVAL '24 hours'
                        WHERE key = $1
                        """,
                        key,
                        request_hash,
                    )
                    return {"state": "claimed", "response": None}

                if existing["request_hash"] != request_hash:
                    return {"state": "conflict", "response": None}

                if existing["status"] == "completed":
                    raw = existing["response"]
                    cached = json.loads(raw) if isinstance(raw, str) else raw
                    return {"state": "replay", "response": cached}

                if existing["status"] == "failed":
                    await conn.execute(
                        """
                        UPDATE idempotency_keys
                        SET request_hash = $2, status = 'running', response = NULL,
                            completed_at = NULL, expires_at = NOW() + INTERVAL '24 hours'
                        WHERE key = $1
                        """,
                        key,
                        request_hash,
                    )
                    return {"state": "claimed", "response": None}

                return {"state": "in_flight", "response": None}

    async def complete_idempotency(
        self,
        key: str,
        response: Optional[Dict[str, Any]] = None,
        status: str = "completed",
    ) -> None:
        """Mark an idempotency key as completed or failed.

        A failed key remains reclaimable (see ``claim_idempotency``), so a
        transient error does not block a legitimate retry.
        """
        if status not in ("completed", "failed"):
            raise ValueError("status must be 'completed' or 'failed'")
        async with self._acquire() as conn:
            await conn.execute(
                """
                UPDATE idempotency_keys
                SET status = $2, completed_at = NOW(),
                    response = $3
                WHERE key = $1
                """,
                key,
                status,
                json.dumps(response) if response is not None else None,
            )

    async def get_idempotency_response(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached response for a completed idempotency key."""
        async with self._acquire() as conn:
            row = await conn.fetchrow(
                "SELECT response FROM idempotency_keys WHERE key = $1 AND status = 'completed'",
                key,
            )
        if row and row["response"]:
            return (
                json.loads(row["response"])
                if isinstance(row["response"], str)
                else row["response"]
            )
        return None

    async def purge_expired_idempotency(self) -> int:
        """Delete expired idempotency keys. Returns the number removed."""
        async with self._acquire() as conn:
            result = await conn.execute(
                "DELETE FROM idempotency_keys WHERE expires_at < NOW()"
            )
        try:
            return int(result.split()[-1])
        except (ValueError, IndexError):
            return 0

    # ------------------------------------------------------------------
    # Task executions: lease + heartbeat + bounded recovery
    # ------------------------------------------------------------------
    async def create_task_execution(
        self,
        task_id: str,
        agent_id: Optional[str],
        worker_id: str,
        idempotency_key: Optional[str],
        lease_minutes: int = 5,
    ) -> Dict[str, Any]:
        async with self._acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO task_executions
                (task_id, agent_id, worker_id, idempotency_key, status, attempt, recovery_count, lease_until, heartbeat_at, started_at)
                VALUES ($1, $2, $3, $4, 'running', 1, 0, NOW() + make_interval(mins => $5), NOW(), NOW())
                RETURNING id, task_id, agent_id, worker_id, idempotency_key, status, attempt, recovery_count, lease_until, heartbeat_at
                """,
                task_id,
                agent_id,
                worker_id,
                idempotency_key,
                lease_minutes,
            )
        return self._row_to_dict(row)

    async def heartbeat_execution(self, execution_id: str, worker_id: str) -> bool:
        """Refresh heartbeat. Returns False if execution not found or not owned by worker."""
        async with self._acquire() as conn:
            result = await conn.execute(
                """
                UPDATE task_executions
                SET heartbeat_at = NOW()
                WHERE id = $1 AND worker_id = $2 AND status IN ('running', 'recovered')
                """,
                execution_id,
                worker_id,
            )
        return result == "UPDATE 1"

    async def recover_stale_executions(
        self,
        worker_id: str,
        max_recovery_count: int = 3,
        lease_timeout_minutes: int = 5,
    ) -> List[Dict[str, Any]]:
        """Claim stale executions (lease expired) using FOR UPDATE SKIP LOCKED.
        Marks exhausted ones as abandoned. Returns recovered executions."""
        recovered: List[Dict[str, Any]] = []
        async with self._acquire() as conn:
            await conn.execute(
                """
                UPDATE task_executions
                SET status = 'abandoned', failure_reason = 'RECOVERY_LIMIT', finished_at = NOW()
                WHERE status IN ('running', 'recovered')
                  AND lease_until < NOW()
                  AND recovery_count >= $1
                """,
                max_recovery_count,
            )
            row = await conn.fetchrow(
                """
                WITH candidate AS (
                    SELECT id FROM task_executions
                    WHERE status IN ('running', 'recovered')
                      AND lease_until < NOW()
                      AND recovery_count < $1
                    ORDER BY lease_until
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                )
                UPDATE task_executions te
                SET worker_id = $2, status = 'recovered',
                    recovery_count = recovery_count + 1,
                    last_recovery_at = NOW(),
                    lease_until = NOW() + make_interval(mins => $3),
                    heartbeat_at = NOW()
                FROM candidate
                WHERE te.id = candidate.id
                RETURNING te.id, te.task_id, te.agent_id, te.worker_id, te.idempotency_key,
                          te.status, te.attempt, te.recovery_count, te.lease_until, te.heartbeat_at
                """,
                max_recovery_count,
                worker_id,
                lease_timeout_minutes,
            )
            if row:
                recovered.append(self._row_to_dict(row))
        return recovered

    async def complete_task_execution(
        self,
        execution_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        failure_reason: Optional[str] = None,
    ) -> bool:
        if status not in ("completed", "failed", "abandoned"):
            return False
        async with self._acquire() as conn:
            res = await conn.execute(
                """
                UPDATE task_executions
                SET status = $2, finished_at = NOW(),
                    result = $3, failure_reason = $4
                WHERE id = $1
                """,
                execution_id,
                status,
                json.dumps(result) if result is not None else None,
                failure_reason,
            )
        return res == "UPDATE 1"
