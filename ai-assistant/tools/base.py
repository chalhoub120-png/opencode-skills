"""Base class for all tools used by agents and the orchestrator."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """Base tool interface."""

    def __init__(self, name: str, description: str) -> None:
        self.name = name
        self.description = description

    @abstractmethod
    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        """Execute the tool with given parameters."""

    def validate_params(self, params: Dict[str, Any], required: List[str]) -> None:
        """Validate that required parameters are present."""
        missing = [k for k in required if k not in params or params[k] is None]
        if missing:
            raise ValueError(f"Missing required parameters: {', '.join(missing)}")
