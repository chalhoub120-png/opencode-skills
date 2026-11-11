"""Claude API provider implementation - cloud, paid, optional for complex tasks.

Reference: claude-api skill (shared/models.md, python/claude-api/README.md).

API surface notes for Claude Opus 5.5 (`claude-opus-5-5`):
- Thinking is always on. `{"type": "adaptive"}` is the only supported shape;
  `{"type": "disabled"}` and `budget_tokens` both return 400. Depth is
  controlled with `output_config.effort` (default `medium` on this model).
- `temperature`, `top_p` and `top_k` return 400 on every model since
  2026-10-21, so they are never sent.

Security design:
- API key is read from environment variable at runtime only (os.getenv).
- Key is NEVER stored as an object attribute.
- Key is NEVER logged or included in error messages.
- Cost limit is checked BEFORE sending request to Claude.
- Falls back to Ollama on failure or cost limit exceeded.
- thinking_blocks are NOT logged or stored persistently.
"""

from __future__ import annotations

from .provider import BaseLLMProvider, LLMRequest, LLMResponse, LLMProviderType

# Anthropic SDK is imported lazily inside _get_client() to avoid
# hard dependency when Claude API is not configured.

# Claude Opus 5.5 pricing, USD per 1M tokens (claude-api skill, shared/models.md).
INPUT_USD_PER_MTOK = 4.00
OUTPUT_USD_PER_MTOK = 20.00

# Task types that justify the higher effort level.
_COMPLEX_TASKS = ("reasoning", "complex", "analysis")


class ClaudeProvider(BaseLLMProvider):
    """Claude API provider for complex reasoning tasks.

    Used optionally for English reasoning/complex/analysis tasks
    when Ollama is insufficient. Falls back to Ollama on failure or cost limit.
    """

    def __init__(
        self, api_key_env_var: str = "ANTHROPIC_API_KEY", model: str = "claude-opus-5-5"
    ):
        self._api_key_env_var = api_key_env_var
        self.model = model
        self._client = None  # Lazy initialization - key not stored as attribute

    def _get_client(self):
        """Get an async Anthropic client with the API key from environment.

        Security: key is read from env var at call time, never stored.
        """
        import os

        api_key = os.getenv(self._api_key_env_var)
        if not api_key:
            raise ValueError(f"{self._api_key_env_var} not set in environment")
        if self._client is None:
            from anthropic import (
                AsyncAnthropic,
            )  # Lazy import - only when Claude is used

            self._client = AsyncAnthropic(api_key=api_key)
        return self._client

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate response using Claude API.

        Security:
        - thinking_blocks are captured but NOT logged.
        - Cost estimate is checked before sending (via router).
        - API key is never included in exceptions or logs.
        """
        client = self._get_client()

        # Adaptive thinking is the only supported shape on Claude Opus 5.5.
        # Effort is the depth control; the model default is "medium".
        effort = "high" if request.task_type in _COMPLEX_TASKS else "medium"

        resp = await client.messages.create(
            model=self.model,
            max_tokens=request.max_tokens,
            thinking={"type": "adaptive"},
            output_config={"effort": effort},
            messages=[{"role": "user", "content": request.message}],
        )

        # Safety classifiers can decline a request with HTTP 200.
        # Raise so the caller can fall back to the local Ollama model.
        if resp.stop_reason == "refusal":
            stop_details = getattr(resp, "stop_details", None)
            category = getattr(stop_details, "category", None)
            raise RuntimeError(f"Claude refused the request (category: {category})")

        text = ""
        thinking_blocks = []
        for block in resp.content:
            if block.type == "text":
                text += block.text
            elif block.type == "thinking":
                thinking_blocks.append(block.model_dump())

        return LLMResponse(
            answer=text,
            provider=LLMProviderType.CLAUDE,
            model=self.model,
            language=request.language,
            tokens_used=resp.usage.input_tokens + resp.usage.output_tokens,
            cost_usd=self.get_cost_estimate(
                resp.usage.input_tokens, resp.usage.output_tokens
            ),
            thinking_blocks=thinking_blocks,
            request_id=request.request_id,
        )

    def is_available(self) -> bool:
        """Check if Claude API key is configured (without exposing the key)."""
        import os

        return bool(os.getenv(self._api_key_env_var))

    def get_model_name(self) -> str:
        """Get the Claude model name."""
        return self.model

    def get_cost_estimate(self, tokens_in: int, tokens_out: int) -> float:
        """Estimate Claude API cost in USD before sending.

        Claude Opus 5.5: $4 per 1M input tokens, $20 per 1M output tokens.
        """
        return (
            tokens_in * INPUT_USD_PER_MTOK / 1_000_000
            + tokens_out * OUTPUT_USD_PER_MTOK / 1_000_000
        )

    def should_fallback(self, cost_estimate: float, max_cost: float = 0.10) -> bool:
        """Check if estimated cost exceeds limit - trigger fallback to Ollama.

        From claude-api skill: prevent unexpected spending.
        """
        return cost_estimate > max_cost
