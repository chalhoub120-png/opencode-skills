"""Abstract base class for LLM providers.

This module defines the unified interface for all LLM providers
(Ollama, Claude API, etc.) to prevent code duplication and conflicts.
All code is in English. User-facing languages (Arabic, Lebanese, English)
are handled in the dashboard UI layer via LABELS.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional, List
from pydantic import BaseModel


class LLMProviderType(str, Enum):
    """Supported LLM provider types."""

    OLLAMA = "ollama"
    CLAUDE = "claude"


class LLMRequest(BaseModel):
    """Standardized request to any LLM provider."""

    message: str
    language: str = "en"
    task_type: str = "general"
    temperature: float = 0.7
    max_tokens: int = 4096
    thinking: Optional[Dict[str, Any]] = None
    use_claude_only: bool = False
    request_id: Optional[str] = None


class LLMResponse(BaseModel):
    """Standardized response from any LLM provider."""

    answer: str
    provider: str
    model: str
    language: str
    tokens_used: Optional[int] = None
    cost_usd: Optional[float] = None
    thinking_blocks: Optional[List[Dict]] = None
    fallback_used: bool = False
    request_id: Optional[str] = None


class BaseLLMProvider(ABC):
    """Abstract base class for all LLM providers.

    Implements the provider abstraction layer to ensure:
    - Single provider selection per request (no mixing)
    - Unified response format
    - Secure API key handling (no key storage as object attributes)
    - Cost estimation before sending
    """

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a response from the LLM."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available."""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Get the model name."""
        pass

    @abstractmethod
    def get_cost_estimate(self, tokens_in: int, tokens_out: int) -> float:
        """Estimate cost in USD for given token counts."""
        pass
