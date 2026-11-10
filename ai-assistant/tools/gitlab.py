"""GitLab tool for repository operations via GitLab REST API."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from tools.rest import RESTTool

logger = logging.getLogger(__name__)


class GitLabTool(RESTTool):
    """GitLab operations: list projects, get file, create merge request, issues."""

    def __init__(
        self,
        token: Optional[str] = None,
        base_url: str = "https://gitlab.com/api/v4",
    ) -> None:
        super().__init__(base_url=base_url)
        self.token = token or os.getenv("GITLAB_TOKEN", "")
        self._headers: Dict[str, str] = {}
        if self.token:
            self._headers["PRIVATE-TOKEN"] = self.token

    async def execute(
        self,
        operation: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        if operation == "list_projects":
            return await self.get("/projects", headers=self._headers)
        if operation == "get_file":
            return await self._get_file(kwargs["project_id"], kwargs["file_path"])
        if operation == "create_issue":
            return await self._create_issue(kwargs["project_id"], kwargs)
        if operation == "create_mr":
            return await self._create_merge_request(kwargs["project_id"], kwargs)
        raise ValueError(f"Unknown GitLab operation: {operation}")

    async def _get_file(self, project_id: str, file_path: str) -> Dict[str, Any]:
        import urllib.parse
        encoded = urllib.parse.quote(file_path, safe="")
        return await self.get(f"/projects/{project_id}/repository/files/{encoded}", headers=self._headers)

    async def _create_issue(self, project_id: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        body = {
            "title": kwargs.get("title", "Issue from AI Assistant"),
            "description": kwargs.get("body", ""),
            "labels": kwargs.get("labels", []),
        }
        return await self.post(f"/projects/{project_id}/issues", json_body=body, headers=self._headers)

    async def _create_merge_request(self, project_id: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        body = {
            "title": kwargs.get("title", "MR from AI Assistant"),
            "description": kwargs.get("body", ""),
            "source_branch": kwargs.get("source_branch", ""),
            "target_branch": kwargs.get("target_branch", "main"),
        }
        return await self.post(f"/projects/{project_id}/merge_requests", json_body=body, headers=self._headers)
