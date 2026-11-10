"""Central task router for the Enterprise AI Assistant.

Responsibilities:
- Task routing to the appropriate agent or tool
- Agent selection based on task type and context
- Memory access coordination
- Knowledge retrieval coordination
- Workflow execution coordination via n8n
- Result aggregation from multiple sources
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from agents.base import BaseAgent
from agents.ceo import CEOSAgent
from agents.developer import DeveloperAgent
from agents.researcher import ResearcherAgent
from agents.analyst import AnalystAgent
from agents.security import SecurityAgent
from agents.legal import LegalAgent
from llm.client import OllamaClient
from llm.router import LLMRouter, TaskType, LanguageCode
from llm.distributed_inference import DistributedInference
from knowledge.store import KnowledgeStore
from db.models import DatabaseManager
from security.audit import AuditLogger
from security.rbac import RBACManager

logger = logging.getLogger(__name__)


class RouteTarget(str, Enum):
    """Where a task should be routed."""

    AGENT = "agent"
    N8N_WORKFLOW = "n8n_workflow"
    DIFY_WORKFLOW = "dify_workflow"
    TOOL = "tool"
    DIRECT_LLM = "direct_llm"


@dataclass
class RouteDecision:
    """Result of routing analysis."""

    target: RouteTarget
    target_name: str
    confidence: float
    reasoning: str
    task_type: TaskType
    model: str
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrchestrationResult:
    """Aggregated result from orchestration."""

    success: bool
    answer: str
    language: str
    agent_used: Optional[str]
    route_decision: RouteDecision
    sources: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    memory_entries: List[Dict[str, Any]] = field(default_factory=list)
    execution_time_ms: float = 0.0
    error: Optional[str] = None


class TaskClassifier:
    """Classifies incoming user messages into task types and routes."""

    # Keywords that strongly indicate coding tasks
    CODING_KEYWORDS = [
        "code",
        "program",
        "script",
        "function",
        "class",
        "variable",
        "bug",
        "error",
        "exception",
        "debug",
        "review",
        "refactor",
        "python",
        "javascript",
        "typescript",
        "java",
        "c++",
        "rust",
        "go",
        "sql",
        "api",
        "endpoint",
        "docker",
        "kubernetes",
        "deploy",
        "git",
        "commit",
        "push",
        "pull",
        "merge",
        "branch",
        "repository",
        "akka kb kk",
        "اكتب كود",
        "برمجة",
        "كود",
        "تصحيح",
        "مراجعة كود",
        "سكريبت",
        "دالة",
        "متغير",
        "خطأ",
        "استثناء",
        "تصحيح أخطاء",
    ]

    # Keywords that strongly indicate reasoning / analysis tasks
    REASONING_KEYWORDS = [
        "analyze",
        "analysis",
        "reason",
        "logic",
        "solve",
        "problem",
        "decision",
        "strategy",
        "plan",
        "compare",
        "evaluate",
        "assess",
        "calculate",
        "math",
        "statistics",
        "forecast",
        "predict",
        "تفسير",
        "استنتاج",
        "منطق",
        "حل",
        "مشكلة",
        "قرار",
        "استراتيجية",
        "خطة",
        "قارن",
        "قيم",
        "قيّم",
        "احسب",
        "رياضيات",
        "إحصاء",
        "بدي ابني",
        "شو أحسن",
        "شو يعني",
        "فيك تساعدني",
        "هيدا مش شغال",
        "حل المشكلة",
    ]

    # Keywords that indicate general knowledge / conversation
    GENERAL_KEYWORDS = [
        "hello",
        "hi",
        "hey",
        "good morning",
        "good afternoon",
        "thank you",
        "thanks",
        "bye",
        "goodbye",
        "how are you",
        "what is",
        "who is",
        "where is",
        "when is",
        "why",
        "مرحبا",
        "أهلاً",
        "أهلين",
        "مرحبا كيفك",
        "كيف حالك",
        "شو الأخبار",
        "كيفك",
        "شو الحال",
        "شكون",
        "وين",
    ]

    # Keywords that indicate n8n automation / workflow tasks
    AUTOMATION_KEYWORDS = [
        "email",
        "send email",
        "gmail",
        "outlook",
        "telegram",
        "whatsapp",
        "github",
        "google drive",
        "microsoft 365",
        "database",
        "postgres",
        "automation",
        "workflow",
        "schedule",
        "cron",
        "trigger",
        "webhook",
        "integration",
        "إيميل",
        "بريد",
        "تليغرام",
        "واتساب",
        "جيثب",
        "غوغل درايف",
        "أتمتة",
        "سير عمل",
        "تكامل",
        "قاعدة بيانات",
    ]

    # Agent selection mapping by task type
    AGENT_BY_TASK_TYPE: dict[TaskType, str] = {
        TaskType.CODING: "developer",
        TaskType.REASONING: "analyst",
        TaskType.GENERAL: "ceo",
        TaskType.AUTOMATION: "ceo",
        TaskType.RESEARCH: "researcher",
        TaskType.SECURITY: "security",
        TaskType.LEGAL: "legal",
    }

    @classmethod
    def classify(
        cls,
        message: str,
        language: str,
        context: Dict[str, Any],
    ) -> tuple[TaskType, float]:
        """Classify a message into a TaskType with confidence score."""
        text = message.lower()
        scores: dict[TaskType, float] = {
            TaskType.CODING: 0.0,
            TaskType.REASONING: 0.0,
            TaskType.GENERAL: 0.0,
            TaskType.AUTOMATION: 0.0,
            TaskType.RESEARCH: 0.0,
            TaskType.SECURITY: 0.0,
            TaskType.LEGAL: 0.0,
        }

        for kw in cls.CODING_KEYWORDS:
            if kw in text:
                scores[TaskType.CODING] += 1.0

        for kw in cls.REASONING_KEYWORDS:
            if kw in text:
                scores[TaskType.REASONING] += 1.0

        for kw in cls.GENERAL_KEYWORDS:
            if kw in text:
                scores[TaskType.GENERAL] += 1.0

        for kw in cls.AUTOMATION_KEYWORDS:
            if kw in text:
                scores[TaskType.AUTOMATION] += 1.0

        # Security-related keywords
        security_kws = [
            "security",
            "vulnerability",
            "audit",
            "penetration",
            "hack",
            "أمن",
            "ثغرة",
            "مراجعة أمنية",
        ]
        for kw in security_kws:
            if kw in text:
                scores[TaskType.SECURITY] += 1.0

        # Legal-related keywords
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
        ]
        for kw in legal_kws:
            if kw in text:
                scores[TaskType.LEGAL] += 1.0

        # Research-related keywords
        research_kws = [
            "research",
            "search",
            "find information",
            "web",
            "internet",
            "بحث",
            "بحث ويب",
            "معلومة",
        ]
        for kw in research_kws:
            if kw in text:
                scores[TaskType.RESEARCH] += 1.0

        total = sum(scores.values())
        if total == 0:
            return TaskType.GENERAL, 0.5

        best_task = max(scores, key=scores.get)
        confidence = scores[best_task] / total
        # Cap confidence at 0.95 to leave room for uncertainty
        confidence = min(confidence, 0.95)
        return best_task, confidence


class OpenCodeOrchestrator:
    """Central orchestrator that routes tasks and aggregates results."""

    def __init__(
        self,
        ollama_client: OllamaClient,
        llm_router: LLMRouter,
        knowledge_store: KnowledgeStore,
        db_manager: DatabaseManager,
        audit_logger: AuditLogger,
        redis_client: Any = None,
        distributed_inference: Optional[DistributedInference] = None,
    ) -> None:
        self.ollama = ollama_client
        self.llm_router = llm_router
        self.knowledge = knowledge_store
        self.db = db_manager
        self.audit = audit_logger
        self.redis = redis_client
        self.distributed_inference = distributed_inference
        self.classifier = TaskClassifier()

        # Initialize agents
        self.agents: Dict[str, BaseAgent] = {
            "ceo": CEOSAgent(ollama_client, llm_router, knowledge_store, db_manager),
            "developer": DeveloperAgent(
                ollama_client, llm_router, knowledge_store, db_manager
            ),
            "researcher": ResearcherAgent(
                ollama_client, llm_router, knowledge_store, db_manager
            ),
            "analyst": AnalystAgent(
                ollama_client, llm_router, knowledge_store, db_manager
            ),
            "security": SecurityAgent(
                ollama_client, llm_router, knowledge_store, db_manager
            ),
            "legal": LegalAgent(ollama_client, llm_router, knowledge_store, db_manager),
        }

    async def route(
        self,
        user_id: str,
        message: str,
        conversation_id: Optional[str] = None,
        project_id: Optional[str] = None,
        language: str = "ar",
        context: Optional[Dict[str, Any]] = None,
        rbac: Optional[RBACManager] = None,
    ) -> OrchestrationResult:
        """Route a user message through the orchestrator and return aggregated result."""
        start_time = datetime.now(timezone.utc)
        context = context or {}

        # Audit log the incoming request
        await self.audit.log(
            user_id=user_id,
            action="route_request",
            resource="conversation",
            resource_id=conversation_id,
            metadata={"message_length": len(message), "language": language},
        )

        # Step 1: Retrieve relevant memory
        memory_entries = await self._retrieve_memory(
            user_id, project_id, conversation_id, message
        )

        # Step 2: Classify the task
        task_type, confidence = self.classifier.classify(message, language, context)

        # Step 3: Select model based on task type and language
        model = self.llm_router.select_model(task_type, language=language)

        # Step 4: Get accessible document IDs for permission-filtered search
        accessible_document_ids: Optional[List[str]] = None
        if rbac is not None:
            accessible_document_ids = await rbac.get_accessible_documents(
                user_id, required_permission="read"
            )

        # Step 5: Retrieve relevant knowledge from Qdrant (permission-filtered, cross-language)
        knowledge_results = await self.knowledge.search(
            query=message,
            language=language,
            top_k=5,
            project_id=project_id,
            accessible_document_ids=accessible_document_ids,
            cross_language=True,
        )

        # Step 5: Make routing decision
        agent_name = self.classifier.AGENT_BY_TASK_TYPE.get(task_type, "ceo")
        route_decision = RouteDecision(
            target=RouteTarget.AGENT,
            target_name=agent_name,
            confidence=confidence,
            reasoning=f"Classified as {task_type.value} with confidence {confidence:.2f}",
            task_type=task_type,
            model=model,
            context={
                "knowledge_results": knowledge_results,
                "memory_entries": memory_entries,
                "project_id": project_id,
                "conversation_id": conversation_id,
            },
            metadata={
                "classified_at": start_time.isoformat(),
                "language": language,
            },
        )

        # Optional: distributed inference path (Controller + Worker nodes).
        # Falls back to the regular agent pipeline if unavailable or on error,
        # so the current system is never blocked by this feature.
        if self.distributed_inference is not None:
            try:
                diag_start = datetime.now(timezone.utc)
                dist_result = await self.distributed_inference.run(
                    text=message,
                    language=language,
                )
                execution_time_ms = (
                    datetime.now(timezone.utc) - diag_start
                ).total_seconds() * 1000

                # Store conversation in memory (same as agent path).
                await self._store_conversation(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    project_id=project_id,
                    user_message=message,
                    assistant_response=dist_result.text,
                    language=language,
                    agent_id="distributed_inference",
                )

                route_decision = RouteDecision(
                    target=RouteTarget.DIRECT_LLM,
                    target_name="distributed_inference",
                    confidence=1.0,
                    reasoning="Routed via distributed inference (Controller + Worker)",
                    task_type=task_type,
                    model="distributed",
                    context={
                        "memory_entries": memory_entries,
                        "project_id": project_id,
                        "conversation_id": conversation_id,
                    },
                    metadata={
                        "distributed": True,
                        "controller_layers": dist_result.controller_layers,
                        "worker_layers": dist_result.worker_layers,
                        "latency_ms": dist_result.latency_ms,
                        "memory_used_mb": dist_result.memory_used_mb,
                    },
                )

                await self.audit.log(
                    user_id=user_id,
                    action="distributed_inference_route",
                    resource="conversation",
                    resource_id=conversation_id,
                    metadata={
                        "controller_layers": dist_result.controller_layers,
                        "worker_layers": dist_result.worker_layers,
                        "execution_time_ms": execution_time_ms,
                        "success": True,
                    },
                )

                return OrchestrationResult(
                    success=True,
                    answer=dist_result.text,
                    language=language,
                    agent_used="distributed_inference",
                    route_decision=route_decision,
                    sources=[],
                    tool_results=[],
                    memory_entries=memory_entries,
                    execution_time_ms=execution_time_ms,
                )
            except Exception as exc:
                logger.exception("Distributed inference failed, falling back to agents")
                await self.audit.log(
                    user_id=user_id,
                    action="distributed_inference_fallback",
                    resource="distributed_inference",
                    metadata={"error": str(exc)},
                )
                # Fall through to the regular agent path below.

        # Step 6: Execute via selected agent
        agent = self.agents.get(agent_name, self.agents["ceo"])
        try:
            result = await agent.process(
                message=message,
                language=language,
                task_type=task_type,
                model=model,
                context=route_decision.context,
                user_id=user_id,
                conversation_id=conversation_id,
            )
        except Exception as exc:
            logger.exception("Agent %s failed", agent_name)
            await self.audit.log(
                user_id=user_id,
                action="agent_error",
                resource="agent",
                resource_id=agent_name,
                metadata={"error": str(exc)},
            )
            execution_time_ms = (
                datetime.now(timezone.utc) - start_time
            ).total_seconds() * 1000
            return OrchestrationResult(
                success=False,
                answer="",
                language=language,
                agent_used=agent_name,
                route_decision=route_decision,
                execution_time_ms=execution_time_ms,
                error=str(exc),
            )

        # Step 7: Store conversation in memory
        await self._store_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
            project_id=project_id,
            user_message=message,
            assistant_response=result.get("answer", ""),
            language=language,
            agent_id=agent_name,
        )

        execution_time_ms = (
            datetime.now(timezone.utc) - start_time
        ).total_seconds() * 1000

        # Step 8: Aggregate and return
        aggregated = OrchestrationResult(
            success=True,
            answer=result.get("answer", ""),
            language=language,
            agent_used=agent_name,
            route_decision=route_decision,
            sources=result.get("sources", []),
            tool_results=result.get("tool_results", []),
            memory_entries=memory_entries,
            execution_time_ms=execution_time_ms,
        )

        await self.audit.log(
            user_id=user_id,
            action="route_complete",
            resource="conversation",
            resource_id=conversation_id,
            metadata={
                "agent": agent_name,
                "task_type": task_type.value,
                "execution_time_ms": execution_time_ms,
                "success": True,
                "tokens": result.get("tokens", {}),
            },
        )

        return aggregated

    async def route_to_n8n(
        self,
        user_id: str,
        workflow_id: str,
        payload: Dict[str, Any],
        conversation_id: Optional[str] = None,
    ) -> OrchestrationResult:
        """Route a task to an n8n workflow for automation."""
        # workflow_id is interpolated into a URL path. Restrict to a safe slug
        # so user input cannot alter the endpoint.
        if not re.fullmatch(r"[A-Za-z0-9_-]+", workflow_id or ""):
            return OrchestrationResult(
                success=False,
                answer="",
                language="ar",
                agent_used=None,
                route_decision=RouteDecision(
                    target=RouteTarget.N8N_WORKFLOW,
                    target_name=workflow_id,
                    confidence=1.0,
                    reasoning="Invalid workflow_id",
                    task_type=TaskType.AUTOMATION,
                    model="",
                ),
                execution_time_ms=0.0,
                error="Invalid workflow_id",
            )
        start_time = datetime.now(timezone.utc)

        await self.audit.log(
            user_id=user_id,
            action="n8n_workflow",
            resource="workflow",
            resource_id=workflow_id,
            metadata={"payload_keys": list(payload.keys())},
        )

        # n8n execution would be handled by the n8n adapter tool
        from tools.rest import RESTTool

        rest_tool = RESTTool(base_url=self._get_n8n_base_url())
        try:
            response = await rest_tool.post(
                path=f"/api/v1/workflows/{workflow_id}/execute",
                json_body=payload,
                headers={"X-N8N-API-KEY": self._get_n8n_api_key()},
            )
        except Exception as exc:
            execution_time_ms = (
                datetime.now(timezone.utc) - start_time
            ).total_seconds() * 1000
            return OrchestrationResult(
                success=False,
                answer="",
                language="ar",
                agent_used=None,
                route_decision=RouteDecision(
                    target=RouteTarget.N8N_WORKFLOW,
                    target_name=workflow_id,
                    confidence=1.0,
                    reasoning="n8n workflow execution",
                    task_type=TaskType.AUTOMATION,
                    model="",
                ),
                execution_time_ms=execution_time_ms,
                error=str(exc),
            )

        execution_time_ms = (
            datetime.now(timezone.utc) - start_time
        ).total_seconds() * 1000
        return OrchestrationResult(
            success=True,
            answer=json.dumps(response, ensure_ascii=False),
            language="ar",
            agent_used=None,
            route_decision=RouteDecision(
                target=RouteTarget.N8N_WORKFLOW,
                target_name=workflow_id,
                confidence=1.0,
                reasoning="n8n workflow executed successfully",
                task_type=TaskType.AUTOMATION,
                model="",
            ),
            tool_results=[{"workflow": workflow_id, "response": response}],
            execution_time_ms=execution_time_ms,
        )

    def _get_n8n_base_url(self) -> str:
        import os

        return os.getenv("N8N_BASE_URL", "http://localhost:5679")

    def _get_n8n_api_key(self) -> str:
        import os

        return os.getenv("N8N_API_KEY", "")

    async def _retrieve_memory(
        self,
        user_id: str,
        project_id: Optional[str],
        conversation_id: Optional[str],
        message: str,
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant long-term memory entries for the user."""
        entries: List[Dict[str, Any]] = []
        try:
            # Search semantic memory via embeddings if available
            rows = await self.db.search_memory(
                user_id=user_id,
                project_id=project_id,
                query=message,
                limit=5,
            )
            for row in rows:
                entries.append(
                    {
                        "id": str(row["id"]),
                        "content": row["content"],
                        "memory_type": row["memory_type"],
                        "created_at": row["created_at"].isoformat()
                        if row["created_at"]
                        else None,
                        "metadata": row["metadata"] or {},
                    }
                )
        except Exception as exc:
            logger.warning("Memory retrieval failed: %s", exc)
        return entries

    async def _store_conversation(
        self,
        user_id: str,
        conversation_id: Optional[str],
        project_id: Optional[str],
        user_message: str,
        assistant_response: str,
        language: str,
        agent_id: str,
    ) -> None:
        """Store the conversation turn in PostgreSQL."""
        try:
            await self.db.create_conversation_message(
                conversation_id=conversation_id,
                user_id=user_id,
                project_id=project_id,
                role="user",
                content=user_message,
                language=language,
            )
            await self.db.create_conversation_message(
                conversation_id=conversation_id,
                user_id=user_id,
                project_id=project_id,
                role="assistant",
                content=assistant_response,
                language=language,
                agent_id=agent_id,
            )
        except Exception as exc:
            logger.warning("Conversation storage failed: %s", exc)
