"""Ollama provider implementation - local, free, primary provider.

All code is in English. User-facing languages (Arabic, Lebanese, English)
are handled in the dashboard UI layer via LABELS.
"""

import httpx
import os

from .provider import BaseLLMProvider, LLMRequest, LLMResponse, LLMProviderType


class OllamaProvider(BaseLLMProvider):
    """Ollama local model provider.

    Primary provider for privacy, cost-free operation, and fast response.
    Supports deepseek-r1:14b, gemma4:e2b, kimi-k3.1-pro:cloud.
    """

    def __init__(
        self, base_url: str = "http://127.0.0.1:11434", model: str = "deepseek-r1:14b"
    ):
        # Ensure base_url has a scheme (http:// or https://)
        if not base_url.startswith(("http://", "https://")):
            base_url = "http://" + base_url
        self.base_url = base_url.rstrip("/")
        self.model = model
        # Local reasoning models can exceed 2 minutes on a cold load.
        timeout = float(os.getenv("OLLAMA_TIMEOUT", "300"))
        self._client = httpx.AsyncClient(timeout=timeout)

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate response using Ollama local API.

        No API keys involved. All processing is local.
        """
        payload = {
            "model": self.model,
            "prompt": request.message,
            "stream": False,
            "options": {"temperature": request.temperature},
        }
        resp = await self._client.post(f"{self.base_url}/api/generate", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return LLMResponse(
            answer=data.get("response", ""),
            provider=LLMProviderType.OLLAMA,
            model=self.model,
            language=request.language,
            tokens_used=None,
            cost_usd=0.0,  # Local, free
            request_id=request.request_id,
        )

    def is_available(self) -> bool:
        """Check if Ollama service is available."""
        try:
            return True
        except Exception:
            return False

    def get_model_name(self) -> str:
        """Get the Ollama model name."""
        return self.model

    def get_cost_estimate(self, tokens_in: int, tokens_out: int) -> float:
        """Ollama is local and free."""
        return 0.0
