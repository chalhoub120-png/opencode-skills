"""Pull required Ollama models into the Ollama server."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llm.client import OllamaClient


MODELS = [
    "qwen3:32b",
    "deepseek-r1:32b",
    "llama3.3",
]


async def pull() -> None:
    client = OllamaClient()
    try:
        for model in MODELS:
            print(f"Pulling model: {model}")
            await client.ensure_model(model)
            print(f"  -> {model} ready")
    finally:
        await client.close()
    print("All models pulled successfully.")


if __name__ == "__main__":
    asyncio.run(pull())
