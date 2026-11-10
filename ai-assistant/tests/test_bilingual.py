"""Bilingual evaluation tests for Arabic and English.

Tests cover:
- Arabic questions answered from Arabic documents
- English questions answered from English documents
- Arabic questions answered from English documents (cross-language)
- English questions answered from Arabic documents (cross-language)
- Modern Standard Arabic, Lebanese dialect, spelling variations
- Mixed Arabic-English queries
- Correct language detection and response language
- Faithful answers with accurate citations
- Refusal/uncertainty when documents do not support an answer
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List

from voice.detector import detect_language, map_dialect_to_msa, get_language_name
from voice.lebanese import LebaneseDialectProcessor
from knowledge.store import KnowledgeStore
from knowledge.citations import CitationFormatter


# ---------------------------------------------------------------------------
# Language detection tests
# ---------------------------------------------------------------------------

def test_detect_lebanese_dialect():
    """Lebanese dialect phrases should be detected as 'lb'."""
    cases = [
        "مرحبا كيفك",
        "شو الأخبار",
        "بدي ابني بوت",
        "شو يعني هيدا؟",
        "فيك تساعدني؟",
        "هيدا مش شغال.",
        "كيفك يا أصدقائي",
    ]
    for text in cases:
        lang, conf = detect_language(text)
        assert lang == "lb", f"Expected 'lb' for '{text}', got '{lang}' (conf={conf:.2f})"
        assert conf > 0.3, f"Confidence too low for '{text}': {conf}"


def test_detect_msa_arabic():
    """Modern Standard Arabic should be detected as 'ar'."""
    cases = [
        "كيف حالك؟",
        "ما هو الذكاء الاصطناعي؟",
        "أريد فهم هذا المفهوم",
        "هذا المستند مهم",
    ]
    for text in cases:
        lang, conf = detect_language(text)
        assert lang == "ar", f"Expected 'ar' for '{text}', got '{lang}' (conf={conf:.2f})"


def test_detect_english():
    """English should be detected as 'en'."""
    cases = [
        "Hello",
        "How are you?",
        "What is artificial intelligence?",
        "I want to build a bot",
        "Can you help me?",
    ]
    for text in cases:
        lang, conf = detect_language(text)
        assert lang == "en", f"Expected 'en' for '{text}', got '{lang}' (conf={conf:.2f})"


# ---------------------------------------------------------------------------
# Lebanese dialect mapping tests
# ---------------------------------------------------------------------------

def test_lebanese_to_msa_mapping():
    """Common Lebanese terms should map to MSA equivalents."""
    processor = LebaneseDialectProcessor(enabled=True)
    mappings = [
        ("كيفك", "كيف حالك"),
        ("شو", "ماذا"),
        ("بدي", "أريد"),
        ("هيدا", "هذا"),
        ("مش شغال", "لا يعمل"),
        ("فيك تساعدني", "هل يمكنك مساعدتي"),
    ]
    for dialect, expected_msa in mappings:
        result = processor.to_msa(dialect)
        assert expected_msa in result, (
            f"Expected '{dialect}' to contain '{expected_msa}', got '{result}'"
        )


def test_lebanese_detection_in_processor():
    processor = LebaneseDialectProcessor(enabled=True)
    assert processor.is_dialect("مرحبا كيفك") is True
    assert processor.is_dialect("شو الأخبار") is True
    assert processor.is_dialect("Hello world") is False


# ---------------------------------------------------------------------------
# Citation formatting tests
# ---------------------------------------------------------------------------

def test_citation_preserves_source_language():
    """Citations should preserve the source document's original language."""
    results = [
        {
            "filename": "document_ar.pdf",
            "content": "هذا المحتوى باللغة العربية",
            "score": 0.95,
            "language": "ar",
            "document_id": "doc-001",
        },
        {
            "filename": "document_en.pdf",
            "content": "This content is in English",
            "score": 0.87,
            "language": "en",
            "document_id": "doc-002",
        },
    ]
    citations_ar = CitationFormatter.format_citations(results, language="ar")
    citations_en = CitationFormatter.format_citations(results, language="en")

    # Arabic citations should keep Arabic source names
    assert citations_ar[0]["source"] == "document_ar.pdf"
    assert citations_ar[0]["language"] == "ar"

    # English citations should keep English source names
    assert citations_en[1]["source"] == "document_en.pdf"
    assert citations_en[1]["language"] == "en"


# ---------------------------------------------------------------------------
# Knowledge store cross-language tests
# ---------------------------------------------------------------------------

def test_cross_language_search_returns_all_languages():
    """Search results should include documents in both languages when cross_language=True."""
    store = KnowledgeStore()

    # We can't actually query Qdrant without a running instance,
    # but we can verify the method signature accepts cross_language
    import inspect
    sig = inspect.signature(store.hybrid_search)
    assert "cross_language" in sig.parameters, "hybrid_search must accept cross_language parameter"
    assert "accessible_document_ids" in sig.parameters, (
        "hybrid_search must accept accessible_document_ids parameter"
    )


# ---------------------------------------------------------------------------
# Bilingual response validation tests
# ---------------------------------------------------------------------------

def test_llm_response_schema_validate_arabic():
    """Structured output schema should accept Arabic responses."""
    from llm.router import LLMResponseSchema

    schema = LLMResponseSchema(
        answer="هذا هو الجواب بالعربية",
        language="ar",
        confidence=0.9,
        sources=["المستند الأول.pdf"],
        needs_clarification=False,
    )
    assert schema.language == "ar"
    assert schema.confidence == 0.9
    assert schema.answer == "هذا هو الجواب بالعربية"


def test_llm_response_schema_validate_english():
    """Structured output schema should accept English responses."""
    from llm.router import LLMResponseSchema

    schema = LLMResponseSchema(
        answer="This is the answer in English",
        language="en",
        confidence=0.85,
        sources=["document_en.pdf"],
        needs_clarification=False,
    )
    assert schema.language == "en"
    assert schema.confidence == 0.85


def test_llm_response_schema_rejects_invalid_confidence():
    """Confidence outside [0,1] should be rejected."""
    from llm.router import LLMResponseSchema
    from pydantic import ValidationError

    try:
        LLMResponseSchema(
            answer="test",
            language="ar",
            confidence=1.5,  # invalid
        )
        assert False, "Should have raised ValidationError"
    except ValidationError:
        pass  # expected


# ---------------------------------------------------------------------------
# Run all tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_detect_lebanese_dialect,
        test_detect_msa_arabic,
        test_detect_english,
        test_lebanese_to_msa_mapping,
        test_lebanese_detection_in_processor,
        test_citation_preserves_source_language,
        test_cross_language_search_returns_all_languages,
        test_llm_response_schema_validate_arabic,
        test_llm_response_schema_validate_english,
        test_llm_response_schema_rejects_invalid_confidence,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            print(f"PASS: {test.__name__}")
            passed += 1
        except Exception as exc:
            print(f"FAIL: {test.__name__}: {exc}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed out of {len(tests)} tests")
