"""Base class for all specialized agents.

Each agent has:
- A system prompt defining its role and behavior (Arabic + English variants)
- Specialized tools it can call
- Memory access via the database manager
- Context management for conversation history
- Structured output validation via LLMResponseSchema
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from llm.client import OllamaClient, LLMResponse
from llm.router import LLMRouter, TaskType, LLMResponseSchema
from knowledge.store import KnowledgeStore
from db.models import DatabaseManager

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base agent."""

    def __init__(
        self,
        ollama_client: OllamaClient,
        llm_router: LLMRouter,
        knowledge_store: KnowledgeStore,
        db_manager: DatabaseManager,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
    ) -> None:
        self.ollama = ollama_client
        self.llm_router = llm_router
        self.knowledge = knowledge_store
        self.db = db_manager
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.name = self.__class__.__name__
        self.agent_type = self._agent_type()

    @abstractmethod
    def _agent_type(self) -> str:
        """Return the agent type identifier."""

    @abstractmethod
    def get_system_prompt(self, language: str = "ar") -> str:
        """Return the system prompt for this agent in the given language."""

    @abstractmethod
    def get_tools(self) -> List[str]:
        """Return the list of tool names this agent can use."""

    async def process(
        self,
        message: str,
        language: str,
        task_type: TaskType,
        model: str,
        context: Dict[str, Any],
        user_id: str,
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Process a user message and return a structured result.

        Uses structured output validation. Never executes model-generated
        code or queries directly.
        """
        system_prompt = self.get_system_prompt(language)

        # Build conversation messages
        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
        ]

        # Add context (memory, knowledge) as system context, bilingual
        # Context bounds (env-tunable, no silent quality drop):
        #   CONTEXT_MAX_SNIPPETS (default 8), CONTEXT_MAX_CHARS (default 12000),
        #   OUTPUT_MAX_TOKENS (default 1024 → num_predict)
        import os as _os

        max_snippets = int(_os.getenv("CONTEXT_MAX_SNIPPETS", "8"))
        max_chars = int(_os.getenv("CONTEXT_MAX_CHARS", "12000"))
        # Cap incoming knowledge to top-N by score (already relevance-filtered in store)
        knowledge_results = (context.get("knowledge_results", []) or [])[:max_snippets]
        # Limit incoming user message (hard input cap, explicit)
        max_input_chars = int(_os.getenv("INPUT_MAX_CHARS", "12000"))
        if len(message) > max_input_chars:
            message = (
                message[:max_input_chars]
                + "\n[truncated: input exceeds INPUT_MAX_CHARS]"
            )

        context_parts: list[str] = []
        if knowledge_results:
            if language == "ar":
                context_parts.append("معلومات ذات الصلة من قاعدة المعرفة:")
            else:
                context_parts.append("Relevant knowledge from the knowledge base:")
            for idx, item in enumerate(knowledge_results, start=1):
                snippet = item.get("content", "")[:300]
                source = item.get("filename", "unknown")
                src_lang = item.get("language", language)
                context_parts.append(f"[{idx}] {source} ({src_lang}): {snippet}")
        memory_entries = context.get("memory_entries", [])
        if memory_entries:
            if language == "ar":
                context_parts.append("ذكريات طويلة المدى ذات الصلة:")
            else:
                context_parts.append("Relevant long-term memory:")
            for idx, item in enumerate(memory_entries, start=1):
                context_parts.append(f"[{idx}] {item.get('content', '')[:200]}")

        if context_parts:
            joined = "\n".join(context_parts)
            if len(joined) > max_chars:
                joined = joined[:max_chars] + "\n[truncated: CONTEXT_MAX_CHARS reached]"
            messages.append(
                {
                    "role": "system",
                    "content": joined,
                }
            )

        # Add language instruction
        messages.append(
            {
                "role": "system",
                "content": self._format_language_instruction(language),
            }
        )

        messages.append({"role": "user", "content": message})

        # Call the LLM (real counters from Ollama prompt_eval_count/eval_count)
        effective_max_tokens = (
            self.max_tokens
            if self.max_tokens is not None
            else int(_os.getenv("OUTPUT_MAX_TOKENS", "1024"))
        )
        response: LLMResponse = await self.ollama.chat(
            model=model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=effective_max_tokens,
        )
        logger.info(
            "LLM tokens: model=%s prompt=%d completion=%d total=%d",
            model,
            response.prompt_tokens,
            response.completion_tokens,
            response.total_tokens,
        )

        # Validate and structure the output
        structured = self.llm_router.validate_response(
            response.content, language=language
        )

        # If model is uncertain, ask for clarification instead of inventing
        if structured.needs_clarification and structured.clarification_question:
            answer_text = structured.clarification_question
        else:
            answer_text = structured.answer

        # Extract sources from knowledge results (preserve original language)
        sources = []
        for item in knowledge_results:
            sources.append(
                {
                    "source": item.get("filename", "unknown"),
                    "content": item.get("content", ""),
                    "language": item.get("language", language),
                    "score": item.get("score", 0.0),
                }
            )

        return {
            "answer": answer_text,
            "agent": self.name,
            "agent_type": self.agent_type,
            "model": model,
            "language": language,
            "task_type": task_type.value,
            "sources": sources,
            "tool_results": [],
            "confidence": structured.confidence,
            "needs_clarification": structured.needs_clarification,
            "tokens": {
                "prompt": response.prompt_tokens,
                "completion": response.completion_tokens,
                "total": response.total_tokens,
            },
        }

    def _format_language_instruction(self, language: str) -> str:
        """Return a language instruction string in the target language."""
        if language == "ar":
            return (
                "أجب باللغة العربية الفصحى ما لم يُطلب غير ذلك. "
                "إذا لم تكن متأكداً من الجواب، قل ذلك بوضوح ولا تخترع معلومات. "
                "اقتبس المصادر عندما تكون متاحة."
            )
        if language == "en":
            return (
                "Answer in English unless otherwise requested. "
                "If you are unsure, say so clearly and do not invent information. "
                "Cite sources when available."
            )
        if language == "lb":
            return (
                "أجب بلهجة لبنانية بسيطة ما لم يُطلب غير ذلك. "
                "إذا ما كنت متأكد، قول بوضوح ولا تخترع معلومات. "
                "اشرح المصادر إذا كانت متاحة."
            )
        return "Respond in the same language as the user."
