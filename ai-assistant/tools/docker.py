"""Docker control tool for container and image management."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from tools.base import BaseTool

logger = logging.getLogger(__name__)


class DockerTool(BaseTool):
    """Docker operations DISABLED by policy (no daemon access from agent path).

    The agent /dev path must never reach the Docker daemon: a mounted
    /var/run/docker.sock is effectively host-root. All operations return an
    error until a separate, network-isolated executor service (no secrets, no
    host mounts, non-root, resource limits) is provisioned and reviewed.
    """

    def __init__(
        self,
        docker_host: Optional[str] = None,
        use_cli: bool = True,
    ) -> None:
        super().__init__("docker_control", "Docker daemon access disabled by policy")
        self.docker_host = docker_host or os.getenv("DOCKER_HOST", "")
        self.use_cli = use_cli

    async def execute(
        self,
        operation: str,
        **kwargs: "Any",
    ) -> "Dict[str, Any]":
        """Blocked: returns error until isolated executor exists."""
        logger.warning(
            "DockerTool blocked operation=%s (policy: no daemon access)", operation
        )
        return {
            "error": (
                "docker control is disabled by policy: agent /dev must not reach the "
                "Docker daemon. Provision a separate isolated executor service."
            )
        }
