"""Tests for env-driven model routing and the fallback chain.

The chain invariant is the important one: a task whose fallback equals its
primary model has no safety net, so one broken local model (a partially
downloaded Ollama blob answers 404) takes the whole endpoint down.
"""

from __future__ import annotations

import pytest

from llm.router import LLMRouter, TaskType

_MODEL_ENV_VARS = (
    "ARABIC_LLM_MODEL",
    "AI_REASONING_MODEL",
    "REASONING_LLM_MODEL",
    "DEFAULT_LLM_MODEL",
    "GENERAL_MODEL",
    "FALLBACK_LLM_MODEL",
    "FALLBACK_REASONING_LLM_MODEL",
)


@pytest.fixture(autouse=True)
def _clean_model_env(monkeypatch):
    """Remove every model override so each test starts from the defaults."""
    for name in _MODEL_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    for task in TaskType:
        monkeypatch.delenv(f"MODEL_{task.value.upper()}_LLM", raising=False)


def test_default_model_can_be_overridden_by_env(monkeypatch):
    monkeypatch.setenv("DEFAULT_LLM_MODEL", "custom-general:1b")
    router = LLMRouter()
    assert router.select_model(TaskType.GENERAL, language="en") == "custom-general:1b"
    assert router.select_model(TaskType.CODING, language="en") == "custom-general:1b"


def test_task_specific_env_wins_over_default(monkeypatch):
    monkeypatch.setenv("DEFAULT_LLM_MODEL", "custom-general:1b")
    monkeypatch.setenv("MODEL_CODING_LLM", "custom-code:7b")
    router = LLMRouter()
    assert router.select_model(TaskType.CODING, language="en") == "custom-code:7b"
    assert router.select_model(TaskType.GENERAL, language="en") == "custom-general:1b"


def test_reasoning_model_reads_both_env_names(monkeypatch):
    router = LLMRouter()
    monkeypatch.setenv("REASONING_LLM_MODEL", "reason-new:7b")
    assert router.select_model(TaskType.REASONING, language="en") == "reason-new:7b"
    monkeypatch.setenv("AI_REASONING_MODEL", "reason-legacy:7b")
    assert router.select_model(TaskType.REASONING, language="en") == "reason-legacy:7b"


def test_arabic_model_env_wins_over_task_model(monkeypatch):
    monkeypatch.setenv("MODEL_CODING_LLM", "custom-code:7b")
    monkeypatch.setenv("ARABIC_LLM_MODEL", "custom-arabic:3b")
    router = LLMRouter()
    assert router.select_model(TaskType.CODING, language="ar") == "custom-arabic:3b"


def test_fallback_never_equals_primary_for_any_task():
    """The invariant that keeps a broken model from taking the API down."""
    router = LLMRouter()
    for task in TaskType:
        primary = router.select_model(task, language="en")
        fallback = router.get_fallback(task)
        assert fallback != primary, f"{task.value}: fallback equals primary"


def test_fallback_never_equals_primary_in_arabic():
    router = LLMRouter()
    for task in TaskType:
        primary = router.select_model(task, language="ar")
        # The fallback must be computed for the same language: the Arabic
        # table prefers gemma4, so an English-computed fallback would collide.
        fallback = router.get_fallback(task, language="ar")
        assert fallback != primary, f"{task.value}: fallback equals primary (ar)"


def test_arabic_reasoning_chain_has_two_distinct_models():
    router = LLMRouter()
    chain = router.get_model_chain(TaskType.REASONING, language="ar")
    assert len(chain) == len(set(chain))
    assert len(chain) >= 2


def test_model_chain_starts_with_primary_and_has_no_duplicates():
    router = LLMRouter()
    for task in TaskType:
        chain = router.get_model_chain(task, language="en")
        assert chain[0] == router.select_model(task, language="en")
        assert len(chain) == len(set(chain))
        assert len(chain) >= 2


def test_chain_survives_env_making_fallback_equal_primary(monkeypatch):
    """A misconfigured environment must not collapse the chain to one model."""
    monkeypatch.setenv("DEFAULT_LLM_MODEL", "only:1b")
    monkeypatch.setenv("FALLBACK_LLM_MODEL", "only:1b")
    router = LLMRouter()
    chain = router.get_model_chain(TaskType.GENERAL, language="en")
    assert len(chain) >= 2
    assert chain[0] == "only:1b"
    assert len(chain) == len(set(chain))


def test_chain_for_general_starts_with_default_then_the_other_model():
    router = LLMRouter()
    chain = router.get_model_chain(TaskType.GENERAL, language="en")
    assert chain[0] == "gemma4:e2b"
    assert chain[1] == "deepseek-r1:14b"


def test_chain_for_reasoning_starts_with_the_reasoning_model():
    router = LLMRouter()
    chain = router.get_model_chain(TaskType.REASONING, language="en")
    assert chain[0] == "deepseek-r1:14b"
    assert chain[1] == "gemma4:e2b"


def test_known_models_are_distinct():
    models = LLMRouter.known_models()
    assert len(models) == len(set(models))
    assert "gemma4:e2b" in models
    assert "deepseek-r1:14b" in models
