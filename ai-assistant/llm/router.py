"""LLM model routing based on task type and language.

Unified router with provider abstraction:
- Ollama: primary provider (local, free, private) - deepseek-r1:14b, gemma4:e2b
- Claude API: optional provider for complex English reasoning tasks
- Falls back to Ollama on Claude failure or cost limit

User-facing languages (Arabic, Lebanese, English) are handled in the
dashboard UI layer via LABELS. This module handles model/provider selection
in English code.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
import os
import logging
import uuid

from pydantic import BaseModel, ValidationError, validator

from llm.provider import BaseLLMProvider, LLMRequest, LLMResponse, LLMProviderType
from llm.ollama_provider import OllamaProvider
from llm.claude_provider import ClaudeProvider


logger = logging.getLogger(__name__)


class TaskType(str, Enum):
    """Task classification for model routing."""

    CODING = "coding"
    REASONING = "reasoning"
    GENERAL = "general"
    AUTOMATION = "automation"
    RESEARCH = "research"
    SECURITY = "security"
    LEGAL = "legal"


class LanguageCode(str, Enum):
    """Supported language codes."""

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
    """Unified LLM model router - Ollama primary, Claude API optional for complex tasks.

    Routes tasks based on type and language:
    - Ollama: primary, free, private (deepseek-r1:14b, gemma4:e2b)
    - Claude API: optional, for complex English reasoning tasks
    - Falls back to Ollama on Claude failure or cost limit
    """

    # From claude-api/managed-agents-core.md: task to agent mapping
    TASK_TO_AGENT: Dict[str, str] = {
        "coding": "developer",
        "reasoning": "analyst",
        "general": "ceo",
        "automation": "ceo",
        "research": "researcher",
        "security": "security",
        "legal": "legal",
    }

    # Tasks that prefer Claude API (adaptive thinking, stronger model)
    CLAUDE_PREFERRED_TASKS: set = {"reasoning", "complex", "analysis"}

    # Default model mappings (backward compatible with existing tests)
    DEFAULT_MODELS: Dict[TaskType, str] = {
        TaskType.CODING: "gemma4:e2b",
        TaskType.REASONING: "deepseek-r1:14b",
        TaskType.GENERAL: "gemma4:e2b",
        TaskType.AUTOMATION: "gemma4:e2b",
        TaskType.RESEARCH: "gemma4:e2b",
        TaskType.SECURITY: "gemma4:e2b",
        TaskType.LEGAL: "gemma4:e2b",
    }

    # Arabic-preferred models (gemma4:e2b for Arabic fluency)
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
        max_claude_cost_per_request: float = 0.10,
    ) -> None:
        self.models = dict(self.DEFAULT_MODELS)
        if custom_models:
            self.models.update(custom_models)

        self.max_claude_cost_per_request: float = max_claude_cost_per_request

        # Initialize provider abstraction layer
        self.providers: Dict[str, BaseLLMProvider] = {}
        self._setup_providers()

    def _setup_providers(self):
        """Initialize providers. Ollama always, Claude only if API key present."""
        # Ollama - always available, primary
        self.providers["ollama"] = OllamaProvider(
            base_url=os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434"),
            model=os.getenv("OLLAMA_MODEL", "deepseek-r1:14b"),
        )

        # Claude API - optional, only if API key configured
        # Security: key is read from env var inside ClaudeProvider, never stored here
        claude_key = os.getenv("ANTHROPIC_API_KEY")
        if claude_key:
            self.providers["claude"] = ClaudeProvider(
                api_key_env_var="ANTHROPIC_API_KEY",
                model=os.getenv("CLAUDE_MODEL", "claude-opus-5-5"),
            )

    def select_model(
        self,
        task_type: TaskType,
        language: str = "ar",
    ) -> str:
        """Select the model for a task type and language.

        Arabic/Lebanese queries use Qwen3-preferred routing for better
        Arabic fluency. English queries use the default routing.

        Backward compatible with existing tests.
        """
        if language in (LanguageCode.AR, LanguageCode.LB):
            return self.ARABIC_MODELS.get(task_type, self.models[TaskType.GENERAL])
        return self.models.get(task_type, self.models[TaskType.GENERAL])

    def get_fallback(self, task_type: TaskType) -> str:
        """Get the fallback model for a task type."""
        return self.FALLBACK_MODELS.get(task_type, self.models[TaskType.GENERAL])

    def route_by_keywords(self, message: str) -> TaskType:
        """Heuristic routing based on message content (Arabic + English).

        Backward compatible with existing tests.
        """
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
            import json

            # Try to parse as JSON if the model returned structured output
            parsed = json.loads(raw_answer)
            return LLMResponseSchema(**parsed)
        except (json.JSONDecodeError, ValidationError):
            pass

        return LLMResponseSchema(
            answer=raw_answer,
            language=language,
            confidence=0.5,
            sources=[],
            needs_clarification=False,
            clarification_question=None,
        )

    def select_provider(
        self,
        task_type: str,
        language: str,
        force_claude: bool = False,
    ) -> str:
        """Select provider for a given task.

        Rules:
        1. Ollama is primary for all tasks (privacy, cost-free)
        2. Claude API only for complex English reasoning if available
        3. Fallback to Ollama on Claude failure or cost limit
        """
        if force_claude and "claude" in self.providers:
            return "claude"

        if (
            task_type in self.CLAUDE_PREFERRED_TASKS
            and language == "en"
            and "claude" in self.providers
        ):
            return "claude"

        return "ollama"

    async def generate(
        self,
        task_type: str,
        message: str,
        language: str = "en",
        force_claude: bool = False,
    ) -> LLMResponse:
        """Generate response with automatic provider selection and fallback.

        Args:
            task_type: Type of task (coding, reasoning, general, etc.)
            message: User message text
            language: Language code (ar, en, lb)
            force_claude: Force Claude API even if not preferred

        Returns:
            LLMResponse with answer, provider, model, cost info
        """
        request_id = str(uuid.uuid4())
        provider_name = self.select_provider(task_type, language, force_claude)
        provider = self.providers[provider_name]

        request = LLMRequest(
            message=message,
            language=language,
            task_type=task_type,
            request_id=request_id,
        )

        try:
            response = await provider.generate(request)

            # Check Claude cost limit before accepting response
            if (
                provider_name == "claude"
                and response.cost_usd
                and response.cost_usd > self.max_claude_cost_per_request
            ):
                logger.warning(
                    "Claude cost %.4f exceeded limit %.4f - falling back to Ollama",
                    response.cost_usd,
                    self.max_claude_cost_per_request,
                )
                fallback = self.providers["ollama"]
                fallback_response = await fallback.generate(request)
                fallback_response.fallback_used = True
                return fallback_response

            return response

        except Exception as exc:
            # Fallback to Ollama if Claude fails
            if provider_name == "claude" and "ollama" in self.providers:
                logger.warning(
                    "Claude failed: %s - falling back to Ollama (request_id=%s)",
                    type(exc).__name__,
                    request_id,
                )
                fallback = self.providers["ollama"]
                fallback_response = await fallback.generate(request)
                fallback_response.fallback_used = True
                return fallback_response
            raise

    def get_agent_for_task(self, task_type: str) -> str:
        """From managed-agents-core.md: return agent name for task type."""
        return self.TASK_TO_AGENT.get(task_type, "ceo")

    def get_available_providers(self) -> List[str]:
        """Return list of available provider names."""
        return [name for name, p in self.providers.items() if p.is_available()]

    def estimate_claude_cost(
        self,
        tokens_in: int,
        tokens_out: int,
    ) -> float:
        """Estimate Claude API cost before sending request."""
        if "claude" in self.providers:
            return self.providers["claude"].get_cost_estimate(tokens_in, tokens_out)
        return 0.0
