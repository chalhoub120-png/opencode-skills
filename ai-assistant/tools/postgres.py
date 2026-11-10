"""PostgreSQL tool — read-only, gated by tools:postgres permission."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import asyncpg

from tools.base import BaseTool

logger = logging.getLogger(__name__)


class PostgresTool(BaseTool):
    """Execute read-only SQL queries against PostgreSQL."""

    _READ_ONLY_PREFIXES = ("select ", "with ", "show ", "explain ")

    def __init__(self, database_url: Optional[str] = None) -> None:
        super().__init__("postgres", "PostgreSQL query execution (read-only)")
        self.database_url = database_url or os.getenv(
            "DATABASE_URL", "postgresql://localhost:5432/ai"
        )
        self.database_url = self.database_url.replace(
            "postgresql+asyncpg://", "postgresql://"
        )
        self._pool: Optional[asyncpg.Pool] = None

    async def _get_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                self.database_url, min_size=1, max_size=5
            )
        return self._pool

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def execute(
        self,
        query: str,
        params: Optional[List[Any]] = None,
        fetch: bool = True,
        role: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a read-only SQL query gated by tools:postgres."""
        # Permission gate: caller must present a role holding tools:postgres.
        from security.rbac import RBACManager

        if not role or not RBACManager().has_permission(role, "tools:postgres"):
            return {"error": "Permission denied: requires tools:postgres"}
        # Read-only enforcement: only SELECT/WITH/SHOW/EXPLAIN.
        normalized = " ".join(query.strip().lower().split())
        if not normalized.startswith(self._READ_ONLY_PREFIXES):
            return {"error": "Read-only queries only"}
        pool = await self._get_pool()
        try:
            async with pool.acquire() as conn:
                if fetch:
                    rows = await conn.fetch(query, *(params or []))
                    return {
                        "rows": [dict(r) for r in rows],
                        "count": len(rows),
                    }
                else:
                    result = await conn.execute(query, *(params or []))
                    return {"result": result}
        except Exception as exc:
            logger.exception("PostgreSQL query failed")
            return {"error": str(exc)}

    async def query(
        self, query: str, params: Optional[List[Any]] = None, role: Optional[str] = None
    ) -> Dict[str, Any]:
        return await self.execute(query, params, fetch=True, role=role)

    async def execute_non_query(
        self, query: str, params: Optional[List[Any]] = None, role: Optional[str] = None
    ) -> Dict[str, Any]:
        # Non-read paths are rejected by the read-only gate in execute().
        return await self.execute(query, params, fetch=False, role=role)
