"""LLM Router - connects frontend to Ollama deepseek-r1:14b model"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import httpx
import logging
import os
import json
from enum import Enum
from dataclasses import dataclass


# --- Task Type Enum ---
class TaskType(str, Enum):
    CODING = "coding"
    REASONING = "reasoning"
    GENERAL = "general"
    ARABIC = "arabic"
    AUTOMATION = "automation"
    RESEARCH = "research"
    SECURITY = "security"
    LEGAL = "legal"


# --- Language Code Enum ---
class LanguageCode(str, Enum):
    ARABIC = "ar"
    ENGLISH = "en"
    MIXED = "mixed"


# --- LLM Response Schema (Pydantic) ---
class LLMResponseSchema(BaseModel):
    """Structured response schema from the Ollama LLM."""

    answer: str = Field(..., description="The model's response text")
    language: LanguageCode = Field(
        default=LanguageCode.ENGLISH, description="Language code"
    )
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence score"
    )
    sources: List[str] = Field(
        default_factory=list, description="Source documents/files"
    )
    needs_clarification: bool = Field(
        default=False, description="Whether user clarification is needed"
    )
    clarification_question: Optional[str] = Field(
        default=None,
        description="Question to ask the user when clarification is needed",
    )


# --- LLMRouter Class ---
class LLMRouter:
    """Routes tasks to Ollama models."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: str = "deepseek-r1:14b",
        claude_max_cost: Optional[float] = None,
    ):
        self.base_url = base_url or os.getenv(
            "OLLAMA_BASE_URL", "http://127.0.0.1:11434"
        )
        self.model = model
        self.claude_max_cost = claude_max_cost
        self._claude = None
        self._ollama_providers: Dict[str, Any] = {}

    async def generate(
        self, prompt: str, model: Optional[str] = None, temperature: float = 0.7
    ) -> LLMResponseSchema:
        """Generate response using Ollama model."""
        from llm.client import OllamaClient

        client = OllamaClient(base_url=self.base_url)
        result = await client.generate(
            model=model or self.model,
            prompt=prompt,
            temperature=temperature,
        )
        return LLMResponseSchema(
            answer=result.content,
            language=LanguageCode.ENGLISH,
            confidence=1.0,
            sources=[],
            needs_clarification=False,
        )

    async def chat(
        self,
        model: Optional[str] = None,
        messages: Optional[list] = None,
        temperature: float = 0.7,
    ) -> LLMResponseSchema:
        """Chat with Ollama model."""
        from llm.client import OllamaClient

        client = OllamaClient(base_url=self.base_url)
        result = await client.chat(
            model=model or self.model,
            messages=messages or [],
            temperature=temperature,
        )
        return LLMResponseSchema(
            answer=result.content,
            language=LanguageCode.ENGLISH,
            confidence=1.0,
            sources=[],
            needs_clarification=False,
        )

    # Task -> agent mapping for the local deployment.
    TASK_TO_AGENT: Dict[str, str] = {
        "coding": "developer",
        "reasoning": "analyst",
        "general": "ceo",
        "automation": "ceo",
        "research": "researcher",
        "security": "security",
        "legal": "legal",
    }

    # Task -> default local Ollama model mappings.
    DEFAULT_MODELS: Dict[str, str] = {
        TaskType.CODING: "gemma4:e2b",
        TaskType.REASONING: "deepseek-r1:14b",
        TaskType.GENERAL: "gemma4:e2b",
        TaskType.AUTOMATION: "gemma4:e2b",
        TaskType.RESEARCH: "gemma4:e2b",
        TaskType.SECURITY: "gemma4:e2b",
        TaskType.LEGAL: "gemma4:e2b",
    }

    # Task -> Arabic-preferred local Ollama model mappings.
    ARABIC_MODELS: Dict[str, str] = {
        TaskType.CODING: "gemma4:e2b",
        TaskType.REASONING: "gemma4:e2b",
        TaskType.GENERAL: "gemma4:e2b",
        TaskType.AUTOMATION: "gemma4:e2b",
        TaskType.RESEARCH: "gemma4:e2b",
        TaskType.SECURITY: "gemma4:e2b",
        TaskType.LEGAL: "gemma4:e2b",
    }

    FALLBACK_MODELS: Dict[str, str] = {
        TaskType.CODING: "gemma4:e2b",
        TaskType.REASONING: "gemma4:e2b",
        TaskType.GENERAL: "gemma4:e2b",
        TaskType.AUTOMATION: "gemma4:e2b",
        TaskType.RESEARCH: "gemma4:e2b",
        TaskType.SECURITY: "gemma4:e2b",
        TaskType.LEGAL: "gemma4:e2b",
    }

    def _task_key(self, task_type: TaskType) -> TaskType:
        return task_type if isinstance(task_type, TaskType) else TaskType(task_type)

    def select_model(self, task_type: TaskType, language: str = "en") -> str:
        """Select the local Ollama model for a task type and language."""
        task = self._task_key(task_type)
        if str(language or "en") in ("ar", "lb", "arabic"):
            return self.ARABIC_MODELS.get(task, self.ARABIC_MODELS[TaskType.GENERAL])
        return self.DEFAULT_MODELS.get(task, self.DEFAULT_MODELS[TaskType.GENERAL])

    def get_fallback(self, task_type: TaskType) -> str:
        """Get the fallback model for a task type."""
        task = self._task_key(task_type)
        return self.FALLBACK_MODELS.get(task, self.FALLBACK_MODELS[TaskType.GENERAL])

    def get_agent_for_task(self, task_type: str) -> str:
        """Return the agent name for a task type."""
        return self.TASK_TO_AGENT.get(task_type, "ceo")

    def route_by_keywords(self, message: str) -> TaskType:
        """Heuristic task routing based on message content."""
        text = message.lower()
        security_kws = (
            "security",
            "vulnerability",
            "penetration",
            "audit",
            "أمن",
            "ثغرة",
        )
        legal_kws = ("legal", "law", "contract", "قانون", "عقد")
        coding_kws = (
            "code",
            "script",
            "function",
            "python",
            "bug",
            "debug",
            "refactor",
            "كود",
            "برمجة",
            "تصحيح",
            "سكريبت",
            "دالة",
        )
        reasoning_kws = (
            "analy",
            "reason",
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
        )
        research_kws = ("research", "search", "web", "internet", "بحث", "معلومة")
        general_kws = (
            "hello",
            "hi",
            "how are you",
            "what is",
            "who is",
            "where is",
            "when is",
            "why",
            "مرحبا",
            "أهلاً",
            "كيفك",
            "كيف حالك",
        )
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
        self, raw_answer: str, language: str = "en"
    ) -> LLMResponseSchema:
        """Validate and structure raw LLM output.

        Falls back to a safe schema if validation fails.
        Never executes code or queries from model output.
        """
        answer = raw_answer
        needs_clarification = False
        clarification_question = None
        confidence = 0.5
        sources: List[str] = []

        try:
            parsed = json.loads(raw_answer)
            if isinstance(parsed, dict):
                answer = str(parsed.get("answer") or raw_answer)
                confidence = float(parsed.get("confidence") or 0.5)
                raw_sources = parsed.get("sources") or []
                sources = (
                    [str(s) for s in raw_sources]
                    if isinstance(raw_sources, list)
                    else []
                )
                needs_clarification = bool(parsed.get("needs_clarification") or False)
                clarification_question = parsed.get("clarification_question")
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

        confidence = max(0.0, min(1.0, confidence))
        if str(language or "en") in ("ar", "lb", "arabic"):
            lang_code = LanguageCode.ARABIC
        elif str(language or "en") == "mixed":
            lang_code = LanguageCode.MIXED
        else:
            lang_code = LanguageCode.ENGLISH

        return LLMResponseSchema(
            answer=answer,
            language=lang_code,
            confidence=confidence,
            sources=sources,
            needs_clarification=needs_clarification,
            clarification_question=clarification_question,
        )

    # --- Provider orchestration: Claude with Ollama fallback ---

    # Task types worth the paid Claude provider.
    CLAUDE_TASKS: frozenset = frozenset({"reasoning", "complex", "analysis"})

    # Arabic/Lebanese tasks stay on the local model.
    ARABIC_LANGUAGES: frozenset = frozenset({"ar", "lb", "arabic"})

    def _claude_provider(self):
        """Return the cached ClaudeProvider (lazy, no network on creation)."""
        from llm.claude_provider import ClaudeProvider

        if self._claude is None:
            self._claude = ClaudeProvider()
        return self._claude

    def _ollama_provider(self, model: str):
        """Return a cached OllamaProvider for the given local model."""
        from llm.ollama_provider import OllamaProvider

        provider = self._ollama_providers.get(model)
        if provider is None:
            provider = OllamaProvider(base_url=self.base_url, model=model)
            self._ollama_providers[model] = provider
        return provider

    def _claude_cost_limit(self) -> float:
        """Worst-case spend allowed for a single Claude request."""
        if self.claude_max_cost is not None:
            return self.claude_max_cost
        return float(os.getenv("CLAUDE_MAX_COST_USD", "0.10"))

    def _claude_allowed(self, request: Any, claude: Any) -> bool:
        """Claude runs only for complex English tasks with a key and a safe cost."""
        if str(request.language or "en").lower() in self.ARABIC_LANGUAGES:
            return False
        if request.task_type not in self.CLAUDE_TASKS:
            return False
        if not claude.is_available():
            return False
        estimated = claude.get_cost_estimate(
            len(request.message) // 4, request.max_tokens
        )
        return not claude.should_fallback(estimated, self._claude_cost_limit())

    async def generate_with_fallback(self, request: Any):
        """Generate with Claude when allowed, otherwise with local Ollama.

        Claude is used only when an API key is configured, the task is a
        complex English task, and the worst-case cost stays under the limit.
        Any failure - network, auth, or a safety refusal - falls back to the
        local Ollama model for the same request.
        """
        model = self.model
        try:
            task = TaskType(request.task_type)
            model = self.select_model(task, language=request.language)
        except ValueError:
            pass

        ollama = self._ollama_provider(model)
        claude = self._claude_provider()
        attempted_claude = False

        if self._claude_allowed(request, claude):
            attempted_claude = True
            try:
                return await claude.generate(request)
            except Exception as exc:  # noqa: BLE001 - fallback is the contract
                logging.getLogger(__name__).warning(
                    "Claude provider failed (%s); falling back to Ollama model %s",
                    type(exc).__name__,
                    model,
                )

        response = await ollama.generate(request)
        response.fallback_used = attempted_claude
        return response


# --- FastAPI App ---
app = FastAPI(title="AI Assistant Router", version="1.0.0")

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
DEFAULT_MODEL = "deepseek-r1:14b"


class ChatRequest(BaseModel):
    message: str
    language: str = "en"
    task_type: str = "general"


class ChatResponse(BaseModel):
    success: bool
    model: str
    response: str
    language: str
    task_type: str


@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """Route tasks to the selected local Ollama model."""
    try:
        from llm.client import OllamaClient

        client = OllamaClient(base_url=OLLAMA_BASE_URL)
        task = (
            TaskType(request.task_type)
            if isinstance(request.task_type, TaskType)
            else TaskType(request.task_type)
        )
        llm_router = LLMRouter()
        model = llm_router.select_model(task, language=request.language)
        response = await client.generate(
            model=model,
            prompt=request.message,
            temperature=0.7,
        )
        return {
            "success": True,
            "model": model,
            "answer": response.content,
            "language": request.language,
            "task_type": request.task_type,
        }
    except Exception as e:
        return {
            "success": False,
            "model": DEFAULT_MODEL,
            "answer": f"Error: {str(e)}",
            "language": request.language,
            "task_type": request.task_type,
        }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "model": DEFAULT_MODEL, "status": "running"}


@app.get("/")
async def root():
    return {"message": "AI Assistant API is running", "model": DEFAULT_MODEL}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)

# Re-export for convenience
__all__ = [
    "LLMRouter",
    "TaskType",
    "LanguageCode",
    "LLMResponseSchema",
    "ChatRequest",
    "ChatResponse",
    "app",
]
