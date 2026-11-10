"""Dependency providers for FastAPI endpoints."""

from __future__ import annotations

import os
import time
from collections import defaultdict
from functools import lru_cache
from typing import Any, Dict, Optional

from fastapi import HTTPException, Header, Request, status

from db.models import DatabaseManager
from orchestrator.router import OpenCodeOrchestrator
from llm.client import OllamaClient
from llm.router import LLMRouter
from knowledge.store import KnowledgeStore
from llm.distributed_inference import DistributedConfig, DistributedInference
from llm.network_link import LinkType
from security.auth import AuthManager
from security.rbac import RBACManager
from security.audit import AuditLogger
from security.threat_detector import threat_detector, record_threat
from orchestrator.memory import MemoryManager
from orchestrator.knowledge import KnowledgeCoordinator
from voice.detector import LebaneseDialectProcessor
from voice.stt import STTEngine
from voice.tts import TTSEngine
from voice.pipeline import VoicePipeline

# ---------------------------------------------------------------------------
# Shared instances (created lazily)
# ---------------------------------------------------------------------------
_db: DatabaseManager | None = None
_auth: AuthManager | None = None
_rbac: RBACManager | None = None
_audit: AuditLogger | None = None
_ollama: OllamaClient | None = None
_llm_router: LLMRouter | None = None
_knowledge: KnowledgeStore | None = None
_distributed_inference: DistributedInference | None = None
_orchestrator: OpenCodeOrchestrator | None = None
_voice_pipeline: VoicePipeline | None = None


def get_db_manager() -> DatabaseManager:
    global _db
    if _db is None:
        _db = DatabaseManager()
    return _db


def get_auth_manager() -> AuthManager:
    global _auth
    if _auth is None:
        _auth = AuthManager(get_db_manager())
    return _auth


def get_rbac_manager() -> RBACManager:
    global _rbac
    if _rbac is None:
        enabled = os.getenv("RBAC_ENABLED", "true").lower() == "true"
        _rbac = RBACManager(enabled=enabled, db_manager=get_db_manager())
    return _rbac


def get_audit_logger() -> AuditLogger:
    global _audit
    if _audit is None:
        enabled = os.getenv("AUDIT_LOG_ENABLED", "true").lower() == "true"
        _audit = AuditLogger(get_db_manager(), enabled=enabled)
    return _audit


def get_ollama_client() -> OllamaClient:
    global _ollama
    if _ollama is None:
        _ollama = OllamaClient()
    return _ollama


def get_llm_router() -> LLMRouter:
    global _llm_router
    if _llm_router is None:
        _llm_router = LLMRouter()
    return _llm_router


def get_knowledge_store() -> KnowledgeStore:
    global _knowledge
    if _knowledge is None:
        _knowledge = KnowledgeStore()
    return _knowledge


def get_distributed_inference() -> DistributedInference:
    global _distributed_inference
    if _distributed_inference is None:
        config = DistributedConfig(
            total_layers=32,
            controller_memory_gb=128,
            controller_ratio=0.4,
            link_type=LinkType.LOOPBACK,
            simulated_latency_ms=0.5,
            max_new_tokens=50,
            language="ar",
        )
        _distributed_inference = DistributedInference(config=config)
    return _distributed_inference


def get_orchestrator() -> OpenCodeOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        use_distributed = (
            os.getenv("DISTRIBUTED_INFERENCE_ENABLED", "true").lower() == "true"
        )
        _orchestrator = OpenCodeOrchestrator(
            ollama_client=get_ollama_client(),
            llm_router=get_llm_router(),
            knowledge_store=get_knowledge_store(),
            db_manager=get_db_manager(),
            audit_logger=get_audit_logger(),
            distributed_inference=get_distributed_inference()
            if use_distributed
            else None,
        )
    return _orchestrator


def get_voice_pipeline() -> VoicePipeline:
    global _voice_pipeline
    if _voice_pipeline is None:

        async def _responder(text: str, language: str) -> Dict[str, Any]:
            result = await get_orchestrator().route(
                user_id="voice-assistant",
                message=text,
                language=language or "ar",
            )
            if not result.success:
                raise RuntimeError(result.error or "Orchestration failed")
            return {"answer": result.answer, "model": result.agent_used}

        _voice_pipeline = VoicePipeline(
            ollama_client=get_ollama_client(),
            llm_router=get_llm_router(),
            stt_engine=STTEngine(),
            tts_engine=TTSEngine(),
            dialect_processor=LebaneseDialectProcessor(enabled=True),
            responder=_responder,
        )
    return _voice_pipeline


# ---------------------------------------------------------------------------
# Authentication dependency (moved here so voice.py can import it)
# ---------------------------------------------------------------------------

# Rate limiting (simple sliding window, per API key)
RATE_LIMIT_REQUESTS = 60
RATE_LIMIT_WINDOW = 60.0
_rate_limit_state: Dict[str, list[float]] = defaultdict(list)


def rate_limit_check(api_key: str) -> None:
    """Simple sliding-window rate limiter. Raises HTTPException 429 on limit."""
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    timestamps = _rate_limit_state[api_key]
    _rate_limit_state[api_key] = [t for t in timestamps if t > window_start]
    if len(_rate_limit_state[api_key]) >= RATE_LIMIT_REQUESTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again later.",
        )
    _rate_limit_state[api_key].append(now)


async def get_current_user(
    request: Request,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> Dict[str, Any]:
    """Resolve the current user from API key or Bearer token."""
    from security.auth import AuthManager

    auth = get_auth_manager()
    api_key = x_api_key or auth.extract_api_key(dict(request.headers))
    token = auth.extract_bearer_token(authorization)

    if api_key:
        rate_limit_check(api_key)

    user = None
    if api_key:
        user = await auth.authenticate_api_key(api_key)
    if not user and token:
        payload = auth.decode_access_token(token)
        if payload:
            user = await get_db_manager().get_user(payload.get("sub", ""))
    if not user:
        client_ip = request.client.host if request.client else None
        record_threat(
            threat_detector.record_failure(
                user_id=None,
                ip_address=client_ip,
                endpoint=str(request.url.path),
                method=request.method,
                failure_type="auth",
            )
        )
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user
