"""LLM model routing based on task type and language.

Routing reflects the measured CPU-only deployment (no CUDA):
- Coding tasks       -> gemma4:e2b
- Reasoning tasks    -> deepseek-r1:14b (falls back to gemma4:e2b on CPU)
- General tasks      -> gemma4:e2b

Arabic/Lebanese and English both route to the same CPU-friendly models;
the language only affects the prompt, not the model choice, because the
larger 32B variants do not fit the available hardware.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, ValidationError, validator

from llm.client import OllamaClient


class TaskType(str, Enum):
    CODING = "coding"
    REASONING = "reasoning"
    GENERAL = "general"
    AUTOMATION = "automation"
    RESEARCH = "research"
    SECURITY = "security"
    LEGAL = "legal"


class LanguageCode(str, Enum):
    AR = "ar"  # Modern Standard Arabic
    LB = "lb"  # Lebanese dialect
    EN = "en"  # English


class LLMResponseSchema(BaseModel):
    """Structured output schema for LLM responses between components.

    Ensures model output is validated before being passed to downstream
    components. Does NOT execute any code or queries.
    """

    answer: str
    language: str
    confidence: float = 0.5
    sources: list[str] = []
    needs_clarification: bool = False
    clarification_question: Optional[str] = None

    @validator("confidence")
    def confidence_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        return v


class LLMRouter:
    """Routes tasks to the appropriate Ollama model, language-aware."""

    DEFAULT_MODELS: Dict[TaskType, str] = {
        TaskType.CODING: "gemma4:e2b",
        TaskType.REASONING: "deepseek-r1:14b",
        TaskType.GENERAL: "gemma4:e2b",
        TaskType.AUTOMATION: "gemma4:e2b",
        TaskType.RESEARCH: "gemma4:e2b",
        TaskType.SECURITY: "gemma4:e2b",
        TaskType.LEGAL: "gemma4:e2b",
    }

    # Arabic-preferred models (Qwen3 has strong multilingual/Arabic support)
    ARABIC_MODELS: Dict[TaskType, str] = {
        TaskType.CODING: "gemma4:e2b",
        TaskType.REASONING: "gemma4:e2b",
        TaskType.GENERAL: "gemma4:e2b",
        TaskType.AUTOMATION: "gemma4:e2b",
        TaskType.RESEARCH: "gemma4:e2b",
        TaskType.SECURITY: "gemma4:e2b",
        TaskType.LEGAL: "gemma4:e2b",
    }

    FALLBACK_MODELS: Dict[TaskType, str] = {
        TaskType.CODING: "gemma4:e2b",
        TaskType.REASONING: "gemma4:e2b",
        TaskType.GENERAL: "gemma4:e2b",
        TaskType.AUTOMATION: "gemma4:e2b",
        TaskType.RESEARCH: "gemma4:e2b",
        TaskType.SECURITY: "gemma4:e2b",
        TaskType.LEGAL: "gemma4:e2b",
    }

    def __init__(
        self,
        custom_models: Dict[TaskType, str] | None = None,
    ) -> None:
        self.models = dict(self.DEFAULT_MODELS)
        if custom_models:
            self.models.update(custom_models)

    def select_model(
        self,
        task_type: TaskType,
        language: str = "ar",
    ) -> str:
        """Select the model for a task type and language.

        Arabic/Lebanese queries use Qwen3-preferred routing for better
        Arabic fluency. English queries use the default routing.
        """
        if language in (LanguageCode.AR, LanguageCode.LB):
            return self.ARABIC_MODELS.get(task_type, self.models[TaskType.GENERAL])
        return self.models.get(task_type, self.models[TaskType.GENERAL])

    def get_fallback(self, task_type: TaskType) -> str:
        """Get the fallback model for a task type."""
        return self.FALLBACK_MODELS.get(task_type, self.models[TaskType.GENERAL])

    def route_by_keywords(self, message: str) -> TaskType:
        """Heuristic routing based on message content (Arabic + English)."""
        text = message.lower()
        coding_kws = [
            "code",
            "script",
            "function",
            "class",
            "bug",
            "debug",
            "refactor",
            "python",
            "javascript",
            "typescript",
            "sql",
            "docker",
            "git",
            "api",
            "endpoint",
            "deploy",
            "كود",
            "برمجة",
            "تصحيح",
            "مراجعة",
            "سكريبت",
            "دالة",
            "متغير",
            "خطأ",
            "استثناء",
            "GitHub",
            "جيثب",
        ]
        reasoning_kws = [
            "analyze",
            "solve",
            "problem",
            "decision",
            "strategy",
            "compare",
            "evaluate",
            "calculate",
            "math",
            "منطق",
            "حل",
            "مشكلة",
            "قرار",
            "استراتيجية",
            "شو أحسن",
            "حل المشكلة",
            "لماذا",
            "كيف",
        ]
        general_kws = [
            "hello",
            "hi",
            "how are you",
            "what is",
            "who is",
            "مرحبا",
            "أهلاً",
            "كيفك",
            "كيف حالك",
            "شو الأخبار",
            "شو الحال",
            "أهلين",
        ]
        security_kws = [
            "security",
            "vulnerability",
            "audit",
            "penetration",
            "hack",
            "أمن",
            "ثغرة",
            "مراجعة أمنية",
            "اختراق",
        ]
        legal_kws = [
            "legal",
            "law",
            "contract",
            "agreement",
            "compliance",
            "قانوني",
            "قانون",
            "عقد",
            "اتفاقية",
            "امتثال",
        ]
        research_kws = [
            "research",
            "search",
            "find information",
            "web",
            "internet",
            "بحث",
            "بحث ويب",
            "معلومة",
            "مصادر",
        ]

        # Check in priority order: security/legal first, then coding/reasoning
        if any(kw in text for kw in security_kws):
            return TaskType.SECURITY
        if any(kw in text for kw in legal_kws):
            return TaskType.LEGAL
        if any(kw in text for kw in coding_kws):
            return TaskType.CODING
        if any(kw in text for kw in reasoning_kws):
            return TaskType.REASONING
        if any(kw in text for kw in research_kws):
            return TaskType.RESEARCH
        if any(kw in text for kw in general_kws):
            return TaskType.GENERAL
        return TaskType.GENERAL

    def validate_response(
        self,
        raw_answer: str,
        language: str = "ar",
    ) -> LLMResponseSchema:
        """Validate and structure raw LLM output.

        Falls back to a safe schema if validation fails.
        Never executes code or queries from model output.
        """
        try:
            # Try to parse as JSON if the model returned structured output
            import json

            data = json.loads(raw_answer)
            return LLMResponseSchema(**data)
        except (json.JSONDecodeError, ValidationError):
            # Treat entire response as the answer text
            return LLMResponseSchema(
                answer=raw_answer,
                language=language,
                confidence=0.6,
                sources=[],
                needs_clarification=False,
            )

    async def generate_structured(
        self,
        ollama_client: OllamaClient,
        model: str,
        messages: list[dict[str, str]],
        language: str = "ar",
        temperature: float = 0.3,
    ) -> LLMResponseSchema:
        """Generate a response and validate it against the structured schema."""
        response = await ollama_client.chat(
            model=model,
            messages=messages,
            temperature=temperature,
        )
        return self.validate_response(response.content, language=language)
