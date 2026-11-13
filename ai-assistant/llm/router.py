"""LLM Router - connects frontend to Ollama deepseek-r1:14b model"""

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import httpx
import logging
import os
import re
import json
from enum import Enum
from dataclasses import dataclass
from functools import lru_cache

from llm import model_config
from security.chat_auth import get_optional_user


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


# --- Keyword routing helpers ---

# Tashkeel, Quranic marks and tatweel carry no routing meaning.
_ARABIC_MARKS = re.compile(r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed\u0640]")
_ARABIC_FOLD = str.maketrans(
    {"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ئ": "ي", "ؤ": "و", "ة": "ه"}
)
_ARABIC_RANGE = re.compile(r"[\u0621-\u064a]")


def _normalize_text(text: str) -> str:
    """Lowercase and normalize Arabic so spelling variants match the same keyword."""
    lowered = (text or "").lower()
    return _ARABIC_MARKS.sub("", lowered).translate(_ARABIC_FOLD)


@lru_cache(maxsize=256)
def _keyword_pattern(keyword: str) -> "re.Pattern[str]":
    """Build a boundary-aware pattern so `hi` does not match `this`.

    Latin keywords: no letter before the keyword, and short keywords (<=3 chars)
    also need a right boundary. Longer keywords match as prefixes, so `analyz`
    covers `analyze`/`analysis` and `debug` covers `debugging`.

    Arabic keywords: allow the common proclitics (و ب ل ك ف) and the article
    (ال) before the word, since Arabic attaches them to the same word.
    """
    if _ARABIC_RANGE.search(keyword):
        return re.compile(r"(?<![\u0621-\u064a])[وبلكف]{0,2}" + re.escape(keyword))
    escaped = re.escape(keyword)
    if len(keyword) <= 3:
        return re.compile(r"(?<![a-z])" + escaped + r"(?![a-z])")
    return re.compile(r"(?<![a-z])" + escaped)


def _matches_any(text: str, keywords: tuple) -> bool:
    """True when any keyword occurs in the already-normalized text."""
    return any(_keyword_pattern(kw).search(text) for kw in keywords)


# Keywords are stored normalized: no tashkeel, أإآ→ا, ى→ي, ة→ه.
KEYWORD_TASKS: Dict[TaskType, tuple] = {
    TaskType.SECURITY: (
        "security",
        "vulnerability",
        "exploit",
        "penetration",
        "malware",
        "ransomware",
        "phishing",
        "xss",
        "sql injection",
        "cve",
        "امن",
        "ثغره",
        "اختراق",
        "تشفير",
        "قرصنه",
    ),
    TaskType.LEGAL: (
        "legal",
        "lawyer",
        "lawsuit",
        "contract",
        "gdpr",
        "compliance",
        "قانون",
        "عقد",
        "محامي",
        "قضيه",
    ),
    TaskType.CODING: (
        "code",
        "coding",
        "program",
        "script",
        "function",
        "python",
        "javascript",
        "typescript",
        "sql",
        "api",
        "bug",
        "debug",
        "refactor",
        "stack trace",
        "كود",
        "برمجه",
        "سكريبت",
        "داله",
        "تصحيح",
    ),
    TaskType.REASONING: (
        "analyz",
        "analysis",
        "reason",
        "solve",
        "prove",
        "theorem",
        "decision",
        "trade-off",
        "compare",
        "evaluate",
        "calculate",
        "math",
        "منطق",
        "حل",
        "مشكله",
        "تحليل",
        "قارن",
        "احسب",
    ),
    TaskType.RESEARCH: (
        "research",
        "search the web",
        "look up",
        "sources",
        "cite",
        "paper",
        "بحث",
        "معلومه",
        "مصدر",
    ),
    TaskType.GENERAL: (
        "hello",
        "hi",
        "hey",
        "thanks",
        "what is",
        "who is",
        "where is",
        "when is",
        "مرحبا",
        "اهلا",
        "كيفك",
        "شكرا",
    ),
}


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
    # These are the built-in defaults; `llm.model_config` overrides them from
    # the environment so a missing or broken model can be swapped without a
    # code change.
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

    # Task -> fallback local Ollama model mappings.
    # A fallback that equals the primary model is no fallback at all: one
    # broken local model would take the whole endpoint down. Every entry
    # therefore names a different model than its primary.
    FALLBACK_MODELS: Dict[str, str] = {
        TaskType.CODING: "deepseek-r1:14b",
        TaskType.REASONING: "gemma4:e2b",
        TaskType.GENERAL: "deepseek-r1:14b",
        TaskType.AUTOMATION: "deepseek-r1:14b",
        TaskType.RESEARCH: "deepseek-r1:14b",
        TaskType.SECURITY: "deepseek-r1:14b",
        TaskType.LEGAL: "deepseek-r1:14b",
    }

    def _task_key(self, task_type: TaskType) -> TaskType:
        return task_type if isinstance(task_type, TaskType) else TaskType(task_type)

    @classmethod
    def known_models(cls) -> List[str]:
        """Every distinct model this router knows about, in preference order."""
        seen: List[str] = []
        for table in (cls.DEFAULT_MODELS, cls.ARABIC_MODELS, cls.FALLBACK_MODELS):
            for model in table.values():
                if model not in seen:
                    seen.append(model)
        return seen

    def select_model(self, task_type: TaskType, language: str = "en") -> str:
        """Select the local Ollama model for a task type and language.

        The environment wins over the built-in table (see `llm.model_config`).
        """
        task = self._task_key(task_type)
        override = model_config.env_primary(task.value, language)
        if override:
            return override
        if str(language or "en") in model_config.ARABIC_LANGUAGES:
            return self.ARABIC_MODELS.get(task, self.ARABIC_MODELS[TaskType.GENERAL])
        return self.DEFAULT_MODELS.get(task, self.DEFAULT_MODELS[TaskType.GENERAL])

    def get_fallback(self, task_type: TaskType, language: str = "en") -> str:
        """Get the fallback model for a task type (never the primary model).

        Language matters: the Arabic table prefers gemma4, so a fallback
        computed from the English table could equal the Arabic primary.
        """
        task = self._task_key(task_type)
        primary = self.select_model(task, language=language)
        override = model_config.env_fallback(task.value)
        candidate = override or self.FALLBACK_MODELS.get(
            task, self.FALLBACK_MODELS[TaskType.GENERAL]
        )
        if candidate != primary:
            return candidate
        # The configured fallback is the same model as the primary, so hand
        # back any other known model instead of a no-op fallback.
        for model in self.known_models():
            if model != primary:
                return model
        return candidate

    def get_model_chain(self, task_type: TaskType, language: str = "en") -> List[str]:
        """Ordered models to try for a task, primary first.

        The chain always holds at least two distinct models, so a broken local
        model (a partially downloaded blob answers 404) degrades to the next
        one instead of failing the request.
        """
        task = self._task_key(task_type)
        chain: List[str] = [self.select_model(task, language=language)]

        fallback = self.get_fallback(task, language=language)
        if fallback not in chain:
            chain.append(fallback)

        # Last resorts: any other known model, so the chain survives an
        # environment that points both the primary and the fallback at the
        # same (possibly broken) model.
        for model in self.known_models():
            if model not in chain:
                chain.append(model)
        return chain

    def get_agent_for_task(self, task_type: str) -> str:
        """Return the agent name for a task type."""
        return self.TASK_TO_AGENT.get(task_type, "ceo")

    def route_by_keywords(self, message: str) -> TaskType:
        """Route a message by keywords, with Arabic normalization and word boundaries.

        Order is most-specific first: security, legal, coding, reasoning,
        research, general. Reasoning is gated because `deepseek-r1:14b` runs at
        ~1.6 tok/s on CPU-only hardware; auto-routing into it would turn a
        one-line question into a multi-minute wait. Set `ROUTING_AUTO_REASONING=1`
        to enable it (still subject to `ROUTING_MIN_REASONING_CHARS`).
        """
        text = _normalize_text(message)
        if not text.strip():
            return TaskType.GENERAL

        for task in (
            TaskType.SECURITY,
            TaskType.LEGAL,
            TaskType.CODING,
            TaskType.RESEARCH,
            TaskType.GENERAL,
        ):
            if _matches_any(text, KEYWORD_TASKS[task]):
                return task

        if _matches_any(text, KEYWORD_TASKS[TaskType.REASONING]):
            auto = os.getenv("ROUTING_AUTO_REASONING", "0") == "1"
            min_chars = int(os.getenv("ROUTING_MIN_REASONING_CHARS", "60"))
            if auto and len(message.strip()) >= min_chars:
                return TaskType.REASONING
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
        """Generate with the task-selected local model, walking the model chain.

        A heavy model (deepseek-r1:14b) can time out, and a partially
        downloaded model answers 404. Walking the chain means a single failing
        model cannot take the whole request down.
        """
        task = self._resolve_task(request.task_type, request.message)
        chain = self.get_model_chain(task, language=request.language)
        logger = logging.getLogger(__name__)

        last_error: Optional[Exception] = None
        for index, model in enumerate(chain):
            try:
                response = await self._ollama_provider(model).generate(request)
            except Exception as exc:  # noqa: BLE001 - the chain is the contract
                last_error = exc
                logger.warning(
                    "Local model %s failed (%s); trying the next model in the chain",
                    model,
                    type(exc).__name__,
                )
                continue
            response.fallback_used = index > 0
            return response

        raise last_error or RuntimeError("No local model is available")


# --- FastAPI App ---
app = FastAPI(title="AI Assistant Router", version="1.0.0")

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "deepseek-r1:14b")


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


_UUID_PATTERN = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)


async def _try_notification(
    message: str,
    language: str,
    user: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Persist an explicit notification request instead of answering it.

    Returns ``None`` when the message is not a notification request, so the
    chat path keeps its normal behaviour. Anonymous callers (the ``local``
    user) cannot own a notification and also fall through to the model.
    """
    user_id = str((user or {}).get("id") or "")
    if not _UUID_PATTERN.fullmatch(user_id):
        return None

    try:
        # Imported lazily: the orchestrator imports this module, and the chat
        # path must keep working on a machine without the optional services.
        from orchestrator.router import TaskClassifier
    except Exception as exc:  # noqa: BLE001 - optional dependency
        logger.warning("Notification routing unavailable: %s", exc)
        return None

    task_type, _ = TaskClassifier.classify(message, language, {})
    if not TaskClassifier.is_notification_request(message, task_type):
        return None

    from api.deps import get_orchestrator

    result = await get_orchestrator().route_to_n8n(
        user_id=user_id,
        payload={
            "message": message,
            "type": "notification",
            "channel": "in_app",
        },
    )
    if not result.success:
        # Answering with the model here would hide a rejected notification.
        return {
            "success": False,
            "model": "n8n",
            "answer": f"Error: {result.error}",
            "language": language,
            "task_type": "automation",
            "fallback_used": False,
        }

    stored = (result.tool_results or [{}])[0].get("response", {})
    return {
        "success": True,
        "model": "n8n",
        "answer": (
            "تم حفظ الإشعار بنجاح."
            if language.startswith("ar")
            else "Notification saved."
        ),
        "language": language,
        "task_type": "automation",
        "fallback_used": False,
        "notification": stored,
    }


@app.post("/chat")
async def chat_endpoint(
    request: ChatRequest,
    user: Dict[str, Any] = Depends(get_optional_user),
):
    """Route the task to a local model, walking the model chain on failure."""
    from llm.provider import LLMRequest

    notification = await _try_notification(request.message, request.language, user)
    if notification is not None:
        return notification

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
async def chat_stream_endpoint(
    request: StreamChatRequest,
    user: Dict[str, Any] = Depends(get_optional_user),
):
    """Stream tokens as SSE, walking the model chain when a model fails."""
    from fastapi.responses import StreamingResponse
    from llm.client import OllamaClient
    from llm.provider import LLMRequest

    llm_router = LLMRouter()
    task = llm_router._resolve_task(request.task_type, request.message)
    chain = llm_router.get_model_chain(task, language=request.language)
    model = chain[0]
    messages = _build_messages(request.message, request.language, request.file_path)
    client = OllamaClient(base_url=OLLAMA_BASE_URL)

    # Cap output tokens: deepseek-r1:14b runs ~1.6 tok/s on CPU, so an
    # uncapped reasoning answer can take minutes. Configurable via env.
    if task == TaskType.REASONING:
        max_tokens = int(os.getenv("AI_REASONING_MAX_TOKENS", "256"))
    else:
        max_tokens = int(os.getenv("AI_MAX_TOKENS", "1024"))

    def sse(payload: Any) -> str:
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    async def events():
        yield sse(
            {"model": model, "task_type": task.value, "language": request.language}
        )
        produced = False
        last_error: Optional[str] = None
        try:
            for index, candidate in enumerate(chain):
                if index > 0:
                    # The chain moved on: tell the client which model is now
                    # answering so the UI can show it.
                    yield sse({"fallback_model": candidate})
                try:
                    if index == 0:
                        # The primary model streams.
                        async for kind, text in client.chat_stream(
                            model=candidate, messages=messages, max_tokens=max_tokens
                        ):
                            produced = True
                            if kind == "thinking":
                                yield sse({"thinking": text})
                            else:
                                yield sse({"message": {"content": text}})
                    else:
                        # A fallback that has to be retried after a broken
                        # stream is delivered in one piece: resuming a stream
                        # that already failed halfway is not possible.
                        response = await llm_router._ollama_provider(
                            candidate
                        ).generate(
                            LLMRequest(
                                message=request.message,
                                language=request.language,
                                task_type=task.value,
                            )
                        )
                        yield sse({"message": {"content": response.answer}})
                    last_error = None
                    break
                except Exception as exc:  # noqa: BLE001 - the chain is the contract
                    last_error = str(exc)
                    if produced:
                        # Tokens already reached the client: restarting would
                        # duplicate output, so report the error and stop.
                        break
                    logging.getLogger(__name__).warning(
                        "Stream model %s failed (%s); trying the next model in the chain",
                        candidate,
                        type(exc).__name__,
                    )
        finally:
            await client.close()

        if last_error is not None:
            yield sse({"error": last_error})
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


@app.get("/health/models")
async def model_health():
    """Report the model chain and which models Ollama can actually serve.

    A partially downloaded model is listed by Ollama but answers 404 when it
    is used, so listing is not enough: every candidate is probed with a
    one-token request and the result is reported per model.
    """
    from llm.client import OllamaClient

    llm_router = LLMRouter()
    client = OllamaClient(base_url=OLLAMA_BASE_URL)
    try:
        installed = await client.list_models()
    except Exception as exc:  # noqa: BLE001 - report, do not crash
        return {
            "status": "degraded",
            "ollama": {"reachable": False, "error": str(exc)},
            "models": [],
        }

    models: List[Dict[str, Any]] = []
    for model in llm_router.known_models():
        entry: Dict[str, Any] = {
            "model": model,
            "installed": model in installed,
            "usable": False,
        }
        if entry["installed"]:
            try:
                await client.chat(
                    model=model,
                    messages=[{"role": "user", "content": "ping"}],
                    max_tokens=1,
                )
                entry["usable"] = True
            except Exception as exc:  # noqa: BLE001 - report, do not crash
                entry["error"] = str(exc)
        models.append(entry)

    usable = [m["model"] for m in models if m["usable"]]
    return {
        "status": "healthy" if usable else "degraded",
        "ollama": {"reachable": True, "installed": installed},
        "models": models,
        "usable_models": usable,
        "chains": {
            task.value: llm_router.get_model_chain(task, language="en")
            for task in TaskType
        },
    }


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
