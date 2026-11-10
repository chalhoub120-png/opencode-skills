"""Generic REST API tool for calling external endpoints."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx

from tools.base import BaseTool

logger = logging.getLogger(__name__)


class RESTTool(BaseTool):
    """Generic REST client tool."""

    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        super().__init__("rest_api", "Generic REST API caller")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()

    async def execute(
        self,
        method: str,
        path: str,
        json_body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Execute an HTTP request."""
        client = await self._get_client()
        try:
            resp = await client.request(
                method=method.upper(),
                url=path,
                json=json_body,
                params=params,
                headers=headers,
            )
            resp.raise_for_status()
            try:
                body = resp.json()
            except Exception:
                body = {"raw": resp.text}
            return {
                "status": resp.status_code,
                "body": body,
                "headers": dict(resp.headers),
            }
        except httpx.HTTPError as exc:
            logger.exception("REST request failed: %s %s", method, path)
            return {
                "status": getattr(exc.response, "status_code", None) if hasattr(exc, "response") else None,
                "error": str(exc),
            }

    async def get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        return await self.execute("GET", path, params=params, headers=headers)

    async def post(
        self,
        path: str,
        json_body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        return await self.execute("POST", path, json_body=json_body, headers=headers)

    async def put(
        self,
        path: str,
        json_body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        return await self.execute("PUT", path, json_body=json_body, headers=headers)

    async def delete(
        self,
        path: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        return await self.execute("DELETE", path, headers=headers)
