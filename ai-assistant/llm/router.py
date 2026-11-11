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
    ):
        self.base_url = base_url or os.getenv(
            "OLLAMA_BASE_URL", "http://127.0.0.1:11434"
        )
        self.model = model
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

    # --- Provider orchestration: local model with local fallback ---

    def _resolve_task(self, task_type: Optional[str], message: str = "") -> TaskType:
        """Return a known TaskType, routing by keywords for unknown values."""
        try:
            return TaskType(task_type)
        except (ValueError, TypeError):
            return self.route_by_keywords(message or "")

    def _ollama_provider(self, model: str):
        """Return a cached OllamaProvider for the given local model."""
        from llm.ollama_provider import OllamaProvider

        provider = self._ollama_providers.get(model)
        if provider is None:
            provider = OllamaProvider(base_url=self.base_url, model=model)
            self._ollama_providers[model] = provider
        return provider

    async def generate_with_fallback(self, request: Any):
        """Generate with the task-selected local model, retrying on a lighter one.

        A heavy model (deepseek-r1:14b) can time out or be missing. When that
        happens the request is retried once with `get_fallback(task)`, so a
        single failing model cannot take the whole request down.
        """
        task = self._resolve_task(request.task_type, request.message)
        model = self.select_model(task, language=request.language)

        try:
            return await self._ollama_provider(model).generate(request)
        except Exception as exc:  # noqa: BLE001 - fallback is the contract
            fallback_model = self.get_fallback(task)
            if fallback_model == model:
                raise
            logging.getLogger(__name__).warning(
                "Local model %s failed (%s); retrying with %s",
                model,
                type(exc).__name__,
                fallback_model,
            )
            response = await self._ollama_provider(fallback_model).generate(request)
            response.fallback_used = True
            return response


# --- FastAPI App ---
app = FastAPI(title="AI Assistant Router", version="1.0.0")

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
DEFAULT_MODEL = "deepseek-r1:14b"


class ChatRequest(BaseModel):
    message: str
    language: str = "en"
    task_type: str = "general"


class StreamChatRequest(BaseModel):
    message: str
    language: str = "en"
    task_type: Optional[str] = None
    file_path: Optional[str] = None


# Same prompts the chat UI used when it talked to Ollama directly.
SYSTEM_PROMPTS: Dict[str, str] = {
    "en": "You are a helpful AI assistant. Respond in English.",
    "ar": "أنت مساعد ذكي. أجب باللغة العربية الفصحى بوضوح ودقة.",
    "lb": "أنت مساعد ذكي. أجب باللهجة اللبنانية ببساطة وطلاقة. استخدم كلمات شائعة في لبنان إذا لزم الأمر.",
}


def _build_messages(
    message: str, language: str, file_path: Optional[str]
) -> List[Dict[str, str]]:
    """Build the chat messages for the local model."""
    messages: List[Dict[str, str]] = [
        {
            "role": "system",
            "content": SYSTEM_PROMPTS.get(language, SYSTEM_PROMPTS["en"]),
        }
    ]
    if file_path:
        messages.append(
            {
                "role": "user",
                "content": f"The user uploaded a file: {file_path}. Analyze it and answer.",
            }
        )
    messages.append({"role": "user", "content": message})
    return messages


@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """Route the task to a local model, falling back to a lighter one."""
    from llm.provider import LLMRequest

    llm_router = LLMRouter()
    try:
        response = await llm_router.generate_with_fallback(
            LLMRequest(
                message=request.message,
                language=request.language,
                task_type=request.task_type,
            )
        )
        return {
            "success": True,
            "model": response.model,
            "answer": response.answer,
            "language": request.language,
            "task_type": request.task_type,
            "fallback_used": response.fallback_used,
        }
    except Exception as e:
        return {
            "success": False,
            "model": DEFAULT_MODEL,
            "answer": f"Error: {str(e)}",
            "language": request.language,
            "task_type": request.task_type,
            "fallback_used": False,
        }


@app.post("/chat/stream")
async def chat_stream_endpoint(request: StreamChatRequest):
    """Stream tokens as SSE, with one local fallback attempt on failure."""
    from fastapi.responses import StreamingResponse
    from llm.client import OllamaClient
    from llm.provider import LLMRequest

    llm_router = LLMRouter()
    task = llm_router._resolve_task(request.task_type, request.message)
    model = llm_router.select_model(task, language=request.language)
    messages = _build_messages(request.message, request.language, request.file_path)
    client = OllamaClient(base_url=OLLAMA_BASE_URL)

    def sse(payload: Any) -> str:
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    async def events():
        yield sse(
            {"model": model, "task_type": task.value, "language": request.language}
        )
        produced = False
        try:
            async for token in client.chat_stream(model=model, messages=messages):
                produced = True
                yield sse({"message": {"content": token}})
        except Exception as exc:  # noqa: BLE001 - fallback is the contract
            if produced:
                yield sse({"error": str(exc)})
                yield "data: [DONE]\n\n"
                return
            fallback_model = llm_router.get_fallback(task)
            if fallback_model == model:
                yield sse({"error": str(exc)})
                yield "data: [DONE]\n\n"
                return
            logging.getLogger(__name__).warning(
                "Stream model %s failed (%s); retrying with %s",
                model,
                type(exc).__name__,
                fallback_model,
            )
            yield sse({"fallback_model": fallback_model})
            try:
                response = await llm_router._ollama_provider(fallback_model).generate(
                    LLMRequest(
                        message=request.message,
                        language=request.language,
                        task_type=task.value,
                    )
                )
                yield sse({"message": {"content": response.answer}})
            except Exception as exc2:  # noqa: BLE001 - surface, do not crash
                yield sse({"error": str(exc2)})
        finally:
            await client.close()
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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
    "StreamChatRequest",
    "app",
]
