"""Claude API provider implementation - cloud, paid, optional for complex tasks.

Reference: claude-api skill (shared/managed-agents-core.md, cost-optimization.md,
latency-optimization.md, token-counting.md).

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

    def _get_client(self) -> Anthropic:
        """Get Anthropic client with API key from environment (not stored).

        Security: key is read from env var at call time, never stored.
        """
        import os

        api_key = os.getenv(self._api_key_env_var)
        if not api_key:
            raise ValueError(f"{self._api_key_env_var} not set in environment")
        if self._client is None:
            from anthropic import Anthropic  # Lazy import - only when Claude is used

            self._client = Anthropic(api_key=api_key)
        return self._client

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate response using Claude API.

        Security:
        - thinking_blocks are captured but NOT logged.
        - Cost estimate is checked before sending (via router).
        - API key is never included in exceptions or logs.
        """
        # From claude-api skill: use adaptive thinking for complex tasks
        thinking = None
        if request.task_type in ("reasoning", "complex", "analysis"):
            thinking = {"type": "enabled"}

        client = self._get_client()
        resp = client.messages.create(
            model=self.model,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            thinking=thinking,
            messages=[{"role": "user", "content": request.message}],
        )

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
            cost_usd=self._estimate_cost(
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

        From claude-api skill cost-optimization.md.
        """
        # Approximate Claude Opus 3.5 pricing:
        # input: $15 per 1M tokens, output: $75 per 1M tokens
        return tokens_in * 0.000015 + tokens_out * 0.000075

    def should_fallback(self, cost_estimate: float, max_cost: float = 0.10) -> bool:
        """Check if estimated cost exceeds limit - trigger fallback to Ollama.

        From claude-api skill: prevent unexpected spending.
        """
        return cost_estimate > max_cost
