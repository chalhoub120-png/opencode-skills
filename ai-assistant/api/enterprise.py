"""Enterprise endpoints: agents, memory, knowledge and settings.

These are the endpoints `ARCHITECTURE.md` describes but that were never
mounted. The chat path stays independent of them: an endpoint that needs
PostgreSQL or Qdrant reports 503 when that service is down instead of
breaking the chat.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.deps import get_current_user
from llm.router import LLMRouter, TaskType

logger = logging.getLogger(__name__)

router = APIRouter(tags=["enterprise"])

# Agent classes, keyed by the task type that selects them.
AGENT_CLASSES = {
    "ceo": ("agents.ceo", "CEOSAgent"),
    "developer": ("agents.developer", "DeveloperAgent"),
    "researcher": ("agents.researcher", "ResearcherAgent"),
    "analyst": ("agents.analyst", "AnalystAgent"),
    "security": ("agents.security", "SecurityAgent"),
    "legal": ("agents.legal", "LegalAgent"),
}

# Task type -> agent, mirroring orchestrator.router.TaskClassifier.
AGENT_BY_TASK = {
    "coding": "developer",
    "reasoning": "analyst",
    "general": "ceo",
    "automation": "ceo",
    "research": "researcher",
    "security": "security",
    "legal": "legal",
}


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    language: str = Field(default="ar")
    top_k: int = Field(default=5, ge=1, le=50)


def _agent_metadata() -> List[Dict[str, Any]]:
    """Describe every agent without opening a database connection.

    The agent classes only need an instance to expose their constants, so a
    bare instance is enough - no Ollama, Qdrant or PostgreSQL required.
    """
    agents: List[Dict[str, Any]] = []
    for agent_type, (module_name, class_name) in AGENT_CLASSES.items():
        entry: Dict[str, Any] = {"type": agent_type, "tasks": []}
        try:
            module = __import__(module_name, fromlist=[class_name])
            instance = getattr(module, class_name).__new__(getattr(module, class_name))
            entry["name"] = class_name
            entry["tools"] = list(instance.get_tools())
        except Exception as exc:  # noqa: BLE001 - describe what we can
            logger.warning("Could not describe agent %s: %s", agent_type, exc)
            entry["name"] = class_name
            entry["tools"] = []
        for task, name in AGENT_BY_TASK.items():
            if name == agent_type:
                entry["tasks"].append(task)
        agents.append(entry)
    return agents


@router.get("/agents")
async def list_agents(user: Dict[str, Any] = Depends(get_current_user)):
    """List the specialized agents and the tasks they handle."""
    return {"agents": _agent_metadata()}


@router.get("/memory")
async def search_memory(
    query: str = "",
    limit: int = 5,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Search the caller's long-term memory."""
    from api.deps import get_db_manager

    try:
        rows = await get_db_manager().search_memory(
            user_id=str(user.get("id")),
            query=query or "",
            limit=min(max(limit, 1), 50),
        )
    except Exception as exc:  # noqa: BLE001 - report, do not crash
        logger.error("Memory search failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The memory store is unavailable.",
        ) from exc
    return {"memories": rows, "count": len(rows)}


@router.post("/knowledge")
async def search_knowledge(
    payload: KnowledgeSearchRequest,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Search the RAG knowledge base, filtered by the caller's permissions."""
    from api.deps import get_knowledge_store, get_rbac_manager

    accessible: Optional[List[str]] = None
    try:
        accessible = await get_rbac_manager().get_accessible_documents(
            str(user.get("id")), required_permission="read"
        )
    except Exception as exc:  # noqa: BLE001 - permissions must not be skipped
        logger.error("Could not resolve document permissions: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Permissions could not be resolved.",
        ) from exc

    try:
        results = await get_knowledge_store().search(
            query=payload.query,
            language=payload.language,
            top_k=payload.top_k,
            accessible_document_ids=accessible,
            cross_language=True,
        )
    except Exception as exc:  # noqa: BLE001 - report, do not crash
        logger.error("Knowledge search failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The knowledge base is unavailable.",
        ) from exc
    return {"results": results, "count": len(results)}


@router.get("/settings")
async def get_settings(user: Dict[str, Any] = Depends(get_current_user)):
    """Report the runtime settings. Secrets are never returned."""
    router = LLMRouter()
    return {
        "models": {
            task.value: router.select_model(task, language="en") for task in TaskType
        },
        "chains": {
            task.value: router.get_model_chain(task, language="en") for task in TaskType
        },
        "language": {
            "default": os.getenv("DEFAULT_LANGUAGE", "ar"),
            "supported": os.getenv("SUPPORTED_LANGUAGES", "ar,en,lb").split(","),
        },
        "features": {
            "voice": os.getenv("VOICE_ENABLED", "true").lower() == "true",
            "distributed_inference": os.getenv(
                "DISTRIBUTED_INFERENCE_ENABLED", "true"
            ).lower()
            == "true",
            "rbac": os.getenv("RBAC_ENABLED", "true").lower() == "true",
        },
    }
