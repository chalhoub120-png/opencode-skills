"""File management tool: read, write, list, delete files within a sandbox directory."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.base import BaseTool

logger = logging.getLogger(__name__)


class FileTool(BaseTool):
    """Sandboxed file operations."""

    def __init__(self, base_dir: Optional[str] = None) -> None:
        super().__init__("file_management", "Read, write, list, and delete files")
        # Sandbox to a dedicated subfolder by default (not CWD root).
        self.base_dir = Path(
            base_dir or os.getenv("FILE_TOOL_BASE_DIR", "sandbox")
        ).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve(self, path: str) -> Path:
        """Resolve a path within the base directory and prevent traversal."""
        target = (self.base_dir / path).resolve()
        if self.base_dir not in target.parents and target != self.base_dir:
            raise PermissionError(f"Path escapes sandbox: {path}")
        return target

    async def execute(
        self,
        operation: str,
        path: str,
        content: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a file operation."""
        target = self._resolve(path)
        if operation == "read":
            if not target.exists():
                return {"error": f"File not found: {path}"}
            return {"content": target.read_text(encoding="utf-8")}
        if operation == "write":
            if content is None:
                return {"error": "content is required for write operation"}
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return {"status": "written", "path": str(target)}
        if operation == "list":
            if not target.exists() or not target.is_dir():
                return {"error": f"Directory not found: {path}"}
            entries = []
            for child in sorted(target.iterdir()):
                entries.append(
                    {
                        "name": child.name,
                        "is_dir": child.is_dir(),
                        "size": child.stat().st_size if child.is_file() else None,
                    }
                )
            return {"entries": entries}
        if operation == "delete":
            if not target.exists():
                return {"error": f"File not found: {path}"}
            target.unlink()
            return {"status": "deleted", "path": str(target)}
        return {"error": f"Unknown operation: {operation}"}
