"""Terminal command execution tool with safety controls."""

from __future__ import annotations

import asyncio
import logging
import os
import re
import shlex
from typing import Any, Dict, List, Optional

from tools.base import BaseTool

logger = logging.getLogger(__name__)

# Commands the agent is allowed to run. Anything else is denied by default.
# Override with TERMINAL_ALLOWED_COMMANDS="git,python,..." when a project needs more.
# SECURITY: docker/docker-compose deliberately REMOVED - agent must never reach the daemon.
DEFAULT_ALLOWED_COMMANDS = (
    "git",
    "python",
    "python3",
    "pip",
    "pip3",
    "uv",
    "pytest",
    "ruff",
    "mypy",
    "node",
    "npm",
    "npx",
    "make",
    "go",
    "cargo",
    "rustc",
    "ls",
    "dir",
    "cat",
    "type",
    "head",
    "tail",
    "wc",
    "grep",
    "findstr",
    "pwd",
    "echo",
    "mkdir",
    "cp",
    "mv",
)

# Rejected outright: shell chaining/redirection, privilege escalation, traversal, docker daemon.
FORBIDDEN_PATTERNS = (
    r"[;&|`$<>]",
    r"\bsudo\b",
    r"\bsu\b",
    r"\brunas\b",
    r"\.\./",
    r"\bdocker\b",
    r"\bdocker\.sock\b",
)

# Commands that must never be allowed even if env tries to add them.
HARD_DENY_COMMANDS = {"docker", "docker-compose"}


class TerminalTool(BaseTool):
    """Execute terminal commands within safety constraints."""

    def __init__(self, work_dir: Optional[str] = None, timeout: float = 60.0) -> None:
        super().__init__("terminal_command", "Execute shell commands safely")
        # Default to a dedicated sandbox dir, never the container root (/app).
        sandbox_default = os.getenv(
            "TERMINAL_WORKDIR", os.getenv("FILE_TOOL_BASE_DIR", "sandbox")
        )
        self.work_dir = work_dir or sandbox_default
        self.timeout = timeout
        configured = os.getenv("TERMINAL_ALLOWED_COMMANDS", "")
        allowed = {
            item.strip().lower() for item in configured.split(",") if item.strip()
        } or set(DEFAULT_ALLOWED_COMMANDS)
        # Hard deny: never allow docker daemon access even if env tries to add it.
        allowed.discard("docker")
        allowed.discard("docker-compose")
        self.allowed_commands = allowed

    def _validate(self, command: str) -> Optional[str]:
        """Return an error message when the command is not allowed."""
        if not command or not command.strip():
            return "Empty command"
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, command):
                return "Command contains forbidden characters or patterns"
        try:
            parts = shlex.split(command)
        except ValueError:
            return "Malformed command"
        if not parts:
            return "Empty command"
        executable = os.path.basename(parts[0]).lower()
        if executable not in self.allowed_commands:
            return f"Command '{executable}' is not allowed"
        return None

    async def execute(
        self,
        command: str,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Execute a terminal command."""
        problem = self._validate(command)
        if problem:
            return {"error": problem}

        timeout = timeout or self.timeout
        try:
            proc = await asyncio.create_subprocess_exec(
                *shlex.split(command),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.work_dir,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                return {"error": f"Command timed out after {timeout}s"}

            return {
                "returncode": proc.returncode,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
            }
        except Exception as exc:
            logger.exception("Terminal command failed")
            return {"error": str(exc)}
