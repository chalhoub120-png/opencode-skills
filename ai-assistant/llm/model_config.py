"""Model routing configuration - the single source of truth for model names.

Every model name is read from the environment so a missing or partially
downloaded local model can be swapped without editing code.

Resolution order for a task's primary model (most specific first):

1. ``ARABIC_LLM_MODEL``          - Arabic and Lebanese requests.
2. ``MODEL_<TASK>_LLM``          - a single task type (``MODEL_CODING_LLM``).
3. ``REASONING_LLM_MODEL``       - reasoning tasks (legacy: ``AI_REASONING_MODEL``).
4. ``DEFAULT_LLM_MODEL``         - every other task (legacy: ``GENERAL_MODEL``).

Fallbacks use ``FALLBACK_LLM_MODEL`` and ``FALLBACK_REASONING_LLM_MODEL``.
"""

from __future__ import annotations

import os
from typing import Optional

# Built-in defaults: the two local models this project was built against.
DEFAULT_GENERAL_MODEL = "gemma4:e2b"
DEFAULT_REASONING_MODEL = "deepseek-r1:14b"

# Languages that get the Arabic-preferred model table.
ARABIC_LANGUAGES = ("ar", "lb", "arabic")


def _env(name: str) -> str:
    """Return a stripped environment value, or an empty string."""
    return os.getenv(name, "").strip()


def env_primary(task: str, language: str = "en") -> Optional[str]:
    """Environment override for a task's primary model, or None for the table."""
    if str(language or "en").lower() in ARABIC_LANGUAGES:
        arabic = _env("ARABIC_LLM_MODEL")
        if arabic:
            return arabic

    specific = _env(f"MODEL_{task.upper()}_LLM")
    if specific:
        return specific

    if task == "reasoning":
        # AI_REASONING_MODEL is the historical name; REASONING_LLM_MODEL is the
        # name published in .env.example. Both are accepted.
        return _env("AI_REASONING_MODEL") or _env("REASONING_LLM_MODEL") or None

    return _env("DEFAULT_LLM_MODEL") or _env("GENERAL_MODEL") or None


def env_fallback(task: str) -> Optional[str]:
    """Environment override for a task's fallback model, or None for the table."""
    name = (
        "FALLBACK_REASONING_LLM_MODEL" if task == "reasoning" else "FALLBACK_LLM_MODEL"
    )
    return _env(name) or None
