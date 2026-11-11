"""Tests for task-aware LLM routing to local Ollama models."""

from __future__ import annotations

from llm.router import LLMRouter, TaskType


def test_reasoning_task_selects_deepseek():
    router = LLMRouter()
    assert router.select_model(TaskType.REASONING, language="en") == "deepseek-r1:14b"


def test_coding_task_selects_gemma():
    router = LLMRouter()
    assert router.select_model(TaskType.CODING, language="en") == "gemma4:e2b"


def test_general_task_selects_gemma():
    router = LLMRouter()
    assert router.select_model(TaskType.GENERAL, language="en") == "gemma4:e2b"


def test_arabic_language_uses_gemma_even_for_reasoning():
    router = LLMRouter()
    assert router.select_model(TaskType.REASONING, language="ar") == "gemma4:e2b"


def test_fallback_model_for_reasoning():
    router = LLMRouter()
    assert router.get_fallback(TaskType.REASONING) == "gemma4:e2b"


def test_get_agent_for_task_reasoning():
    router = LLMRouter()
    assert router.get_agent_for_task("reasoning") == "analyst"


def test_route_by_keywords_coding():
    router = LLMRouter()
    assert router.route_by_keywords("اكتب دالة بايثون لفرز قائمة") == TaskType.CODING


def test_route_by_keywords_reasoning():
    router = LLMRouter()
    # Auto-reasoning is off by default (deepseek-r1:14b is ~1.6 tok/s on CPU),
    # so a short message routes to GENERAL instead of REASONING.
    assert router.route_by_keywords("حل المشكلة paso a paso") == TaskType.GENERAL

    import os

    os.environ["ROUTING_AUTO_REASONING"] = "1"
    os.environ["ROUTING_MIN_REASONING_CHARS"] = "0"
    try:
        assert router.route_by_keywords("حل المشكلة paso a paso") == TaskType.REASONING
    finally:
        os.environ.pop("ROUTING_AUTO_REASONING", None)
        os.environ.pop("ROUTING_MIN_REASONING_CHARS", None)


def test_route_by_keywords_security():
    router = LLMRouter()
    assert router.route_by_keywords("security audit please") == TaskType.SECURITY


def test_validate_response_parses_json():
    router = LLMRouter()
    schema = router.validate_response(
        '{"answer": "42", "confidence": 0.9, "needs_clarification": false}',
        language="en",
    )
    assert schema.answer == "42"
    assert schema.confidence == 0.9
    assert schema.needs_clarification is False


def test_validate_response_plain_text_fallback():
    router = LLMRouter()
    schema = router.validate_response("Just a plain answer", language="ar")
    assert schema.answer == "Just a plain answer"
    assert schema.confidence == 0.5
    assert schema.needs_clarification is False
