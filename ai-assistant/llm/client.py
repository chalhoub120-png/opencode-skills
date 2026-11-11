"""Ollama LLM client with retry, timeout, and streaming support."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Response from the Ollama LLM."""

    content: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    finish_reason: str = "stop"
    raw: Optional[Dict[str, Any]] = None


class OllamaClient:
    """Async client for Ollama chat/completions API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 120.0,
        max_retries: int = 3,
    ) -> None:
        self.base_url = base_url or os.getenv(
            "OLLAMA_BASE_URL", "http://localhost:11434"
        )
        self.timeout = timeout
        self.max_retries = max_retries
        # Keep the model resident between messages: a cold load costs ~7.5s for
        # gemma4:e2b and ~18s for deepseek-r1:14b, which dwarfs short answers.
        self.keep_alive = os.getenv("OLLAMA_KEEP_ALIVE", "30m")
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url, timeout=self.timeout
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()

    async def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> LLMResponse:
        """Send a chat completion request to Ollama."""
        client = await self._get_client()
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "keep_alive": self.keep_alive,
            "options": {
                "temperature": temperature,
            },
        }
        if max_tokens is not None:
            payload["options"]["num_predict"] = max_tokens

        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                resp = await client.post("/api/chat", json=payload)
                resp.raise_for_status()
                data = resp.json()

                message = data.get("message", {})
                content = message.get("content", "")

                return LLMResponse(
                    content=content,
                    model=model,
                    prompt_tokens=data.get("prompt_eval_count", 0),
                    completion_tokens=data.get("eval_count", 0),
                    total_tokens=(
                        data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
                    ),
                    finish_reason=data.get("done_reason", "stop"),
                    raw=data,
                )
            except (httpx.HTTPError, httpx.RequestError) as exc:
                last_error = exc
                logger.warning("Ollama chat attempt %d failed: %s", attempt + 1, exc)
                if attempt == self.max_retries - 1:
                    break
                await asyncio.sleep(1 * (attempt + 1))

        raise RuntimeError(
            f"Ollama chat failed after {self.max_retries} retries: {last_error}"
        )

    async def chat_stream(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """Stream chat completion tokens from Ollama."""
        client = await self._get_client()
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": True,
            "keep_alive": self.keep_alive,
            "options": {
                "temperature": temperature,
            },
        }
        if max_tokens is not None:
            payload["options"]["num_predict"] = max_tokens

        async with client.stream("POST", "/api/chat", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    message = data.get("message", {})
                    # deepseek-r1 (and similar) emit reasoning in `thinking`
                    # before the final `content`. Yield both so callers can show
                    # progress instead of appearing frozen for minutes.
                    thinking = message.get("thinking", "")
                    if thinking:
                        yield ("thinking", thinking)
                    content = message.get("content", "")
                    if content:
                        yield ("content", content)
                    if data.get("done", False):
                        break
                except json.JSONDecodeError:
                    continue

    async def generate(
        self,
        model: str,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Send a generate (completion) request to Ollama."""
        client = await self._get_client()
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": {
                "temperature": temperature,
            },
        }
        if max_tokens is not None:
            payload["options"]["num_predict"] = max_tokens

        resp = await client.post("/api/generate", json=payload)
        resp.raise_for_status()
        data = resp.json()

        return LLMResponse(
            content=data.get("response", ""),
            model=model,
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
            total_tokens=(data.get("prompt_eval_count", 0) + data.get("eval_count", 0)),
            finish_reason="stop",
            raw=data,
        )

    async def list_models(self) -> list[str]:
        """List available models on the Ollama server."""
        client = await self._get_client()
        resp = await client.get("/api/tags")
        resp.raise_for_status()
        data = resp.json()
        return [m["name"] for m in data.get("models", [])]

    async def ensure_model(self, model: str) -> None:
        """Ensure a model is available, pulling it if necessary."""
        available = await self.list_models()
        if any(model in m for m in available):
            return
        logger.info("Model %s not found, pulling...", model)
        client = await self._get_client()
        resp = await client.post("/api/pull", json={"name": model})
        resp.raise_for_status()
