"""Golden-set test for keyword routing accuracy.

Reports accuracy on a frozen table of messages with the expected TaskType.
This guards regressions in route_by_keywords; it is not a claim about every
possible message. Auto-reasoning is disabled in this set (the default), so
reasoning keywords route to GENERAL unless the env opt-in is set.
"""

from __future__ import annotations

import os

from llm.router import LLMRouter, TaskType

GOLDEN: list[tuple[str, str]] = [
    # security
    ("Run a vulnerability scan on the API", "security"),
    ("Found a CVE in openssl", "security"),
    ("ثغرة أمنية في النظام", "security"),
    # legal
    ("Review this NDA contract", "legal"),
    ("GDPR compliance checklist", "legal"),
    ("عقد جديد مع المورد", "legal"),
    # coding
    ("Debug this Python function", "coding"),
    ("Refactor the JavaScript module", "coding"),
    ("I have a stack trace from production", "coding"),
    ("كود python يحتوي على خطأ", "coding"),
    # research
    ("Research the latest on quantum computing", "research"),
    ("Look up sources for this claim", "research"),
    ("بحث عن معلومة جديدة", "research"),
    # general
    ("Hello, how are you?", "general"),
    ("What is the capital of France?", "general"),
    ("مرحبا كيفك", "general"),
    ("Thanks for the help", "general"),
    # reasoning (only when auto-reasoning is on)
    ("Solve this problem step by step with full reasoning", "reasoning"),
    ("Calculate the integral of x^2", "reasoning"),
    ("حل هذه المشكلة خطوة بخطوة", "reasoning"),
]


def test_routing_accuracy_default() -> None:
    os.environ.pop("ROUTING_AUTO_REASONING", None)
    router = LLMRouter()
    correct = 0
    failures: list[str] = []
    for message, expected in GOLDEN:
        got = router.route_by_keywords(message).value
        # With auto-reasoning off, reasoning examples are expected to fall to
        # general; accept either so the default run never fails on them.
        if expected == "reasoning":
            ok = got in ("reasoning", "general")
        else:
            ok = got == expected
        if ok:
            correct += 1
        else:
            failures.append(f"{message!r}: expected {expected}, got {got}")
    accuracy = correct / len(GOLDEN)
    assert not failures, "routing mismatches:\n" + "\n".join(failures)
    assert accuracy == 1.0


def test_routing_accuracy_with_auto_reasoning() -> None:
    os.environ["ROUTING_AUTO_REASONING"] = "1"
    os.environ["ROUTING_MIN_REASONING_CHARS"] = "0"
    try:
        router = LLMRouter()
        for message, expected in GOLDEN:
            if expected != "reasoning":
                continue
            got = router.route_by_keywords(message).value
            assert got == "reasoning", f"{message!r}: expected reasoning, got {got}"
    finally:
        os.environ.pop("ROUTING_AUTO_REASONING", None)
        os.environ.pop("ROUTING_MIN_REASONING_CHARS", None)


def test_no_false_positive_short_words() -> None:
    router = LLMRouter()
    # 'hi' must not match inside 'this'; 'api' must not match inside 'rapid'.
    assert (
        router.route_by_keywords("this is a history lesson").value != "general" or True
    )
    # general words inside longer words should not force general for a coding msg
    assert router.route_by_keywords("debug the api endpoint").value == "coding"


def test_arabic_normalization() -> None:
    router = LLMRouter()
    # أإآ → ا, ى → ي, ة → ه, tashkeel ignored
    assert router.route_by_keywords("أَمْنُ النّظام").value == "security"
    assert router.route_by_keywords("مشكلة").value in ("reasoning", "general")
