"""Memory access layer for the orchestrator.

Handles short-term conversation context and long-term memory
stored in PostgreSQL with Redis caching.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from db.models import DatabaseManager

logger = logging.getLogger(__name__)


class MemoryManager:
    """Manages user memory across conversations and projects."""

    def __init__(self, db_manager: DatabaseManager, redis_client: Any = None) -> None:
        self.db = db_manager
        self.redis = redis_client

    async def get_conversation_context(
        self,
        conversation_id: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Retrieve recent messages from a conversation."""
        try:
            rows = await self.db.get_conversation_messages(
                conversation_id=conversation_id,
                limit=limit,
            )
            return [
                {
                    "id": str(row["id"]),
                    "role": row["role"],
                    "content": row["content"],
                    "language": row["language"],
                    "agent_id": str(row["agent_id"]) if row["agent_id"] else None,
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                }
                for row in rows
            ]
        except Exception as exc:
            logger.warning("Failed to get conversation context: %s", exc)
            return []

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Retrieve user profile and preferences."""
        try:
            row = await self.db.get_user(user_id)
            if not row:
                return {}
            return {
                "id": str(row["id"]),
                "username": row["username"],
                "email": row["email"],
                "role": row["role"],
                "language_preference": row["language_preference"],
                "is_active": row["is_active"],
            }
        except Exception as exc:
            logger.warning("Failed to get user profile: %s", exc)
            return {}

    async def store_long_term_memory(
        self,
        user_id: str,
        content: str,
        memory_type: str,
        project_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None,
    ) -> str:
        """Store a long-term memory entry."""
        try:
            row = await self.db.create_memory(
                user_id=user_id,
                content=content,
                memory_type=memory_type,
                project_id=project_id,
                conversation_id=conversation_id,
                metadata=metadata or {},
                embedding=embedding,
            )
            return str(row["id"])
        except Exception as exc:
            logger.exception("Failed to store long-term memory: %s", exc)
            raise

    async def search_long_term_memory(
        self,
        user_id: str,
        query: str,
        project_id: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search long-term memory semantically."""
        try:
            rows = await self.db.search_memory(
                user_id=user_id,
                project_id=project_id,
                query=query,
                limit=limit,
            )
            return [
                {
                    "id": str(row["id"]),
                    "content": row["content"],
                    "memory_type": row["memory_type"],
                    "metadata": row["metadata"] or {},
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                }
                for row in rows
            ]
        except Exception as exc:
            logger.warning("Long-term memory search failed: %s", exc)
            return []

    async def cache_set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = 3600,
    ) -> None:
        """Cache a value in Redis with TTL."""
        if self.redis is None:
            return
        try:
            await self.redis.setex(
                key,
                ttl_seconds,
                json.dumps(value, ensure_ascii=False, default=str),
            )
        except Exception as exc:
            logger.warning("Redis cache set failed: %s", exc)

    async def cache_get(self, key: str) -> Optional[Any]:
        """Retrieve a cached value from Redis."""
        if self.redis is None:
            return None
        try:
            raw = await self.redis.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as exc:
            logger.warning("Redis cache get failed: %s", exc)
            return None
