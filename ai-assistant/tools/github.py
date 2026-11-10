"""GitHub tool for repository operations via GitHub REST API."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from tools.rest import RESTTool

logger = logging.getLogger(__name__)


class GitHubTool(RESTTool):
    """GitHub operations: list repos, get file, create PR, issues, etc."""

    def __init__(
        self,
        token: Optional[str] = None,
        base_url: str = "https://api.github.com",
    ) -> None:
        super().__init__(base_url=base_url)
        self.token = token or os.getenv("GITHUB_TOKEN", "")
        self._headers: Dict[str, str] = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "EnterpriseAIAssistant/1.0",
        }
        if self.token:
            self._headers["Authorization"] = f"Bearer {self.token}"

    async def execute(
        self,
        operation: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute a GitHub operation."""
        if operation == "list_repos":
            return await self._list_repos()
        if operation == "get_file":
            return await self._get_file(kwargs["owner"], kwargs["repo"], kwargs["path"])
        if operation == "create_issue":
            return await self._create_issue(kwargs["owner"], kwargs["repo"], kwargs)
        if operation == "create_pr":
            return await self._create_pr(kwargs["owner"], kwargs["repo"], kwargs)
        if operation == "search_code":
            return await self._search_code(kwargs["query"])
        raise ValueError(f"Unknown GitHub operation: {operation}")

    async def _list_repos(self) -> Dict[str, Any]:
        return await self.get("/user/repos", headers=self._headers)

    async def _get_file(self, owner: str, repo: str, path: str) -> Dict[str, Any]:
        return await self.get(f"/repos/{owner}/{repo}/contents/{path}", headers=self._headers)

    async def _create_issue(self, owner: str, repo: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        body = {
            "title": kwargs.get("title", "Issue from AI Assistant"),
            "body": kwargs.get("body", ""),
            "labels": kwargs.get("labels", []),
        }
        return await self.post(f"/repos/{owner}/{repo}/issues", json_body=body, headers=self._headers)

    async def _create_pr(self, owner: str, repo: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        body = {
            "title": kwargs.get("title", "PR from AI Assistant"),
            "body": kwargs.get("body", ""),
            "head": kwargs.get("head", ""),
            "base": kwargs.get("base", "main"),
        }
        return await self.post(f"/repos/{owner}/{repo}/pulls", json_body=body, headers=self._headers)

    async def _search_code(self, query: str) -> Dict[str, Any]:
        return await self.get(
            "/search/code",
            params={"q": query},
            headers=self._headers,
        )
