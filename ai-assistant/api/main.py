"""FastAPI application for the Enterprise AI Assistant.

Endpoints:
- POST /chat          - Text chat with orchestrator (bilingual, permission-aware)
- POST /voice         - Voice input processing (STT -> LLM -> TTS)
- GET  /agents        - List available agents
- POST /knowledge     - Knowledge base search (cross-language, permission-filtered)
- GET  /memory        - Get conversation memory
- POST /workflows     - Trigger n8n workflows (human approval required)
- POST /approvals     - Create/decide approval requests
- GET  /approvals     - List pending approvals
- GET  /settings      - Get settings
- GET  /health        - Health check
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from api.deps import (
    get_orchestrator,
    get_auth_manager,
    get_rbac_manager,
    get_audit_logger,
    get_db_manager,
    get_current_user,
)
from api.voice import router as voice_router
from security.rbac import RBACManager
from security.audit import AuditLogger
from security.validation import RequestValidator
from security.threat_detector import (
    threat_detector,
    record_threat,
    recent_threats,
    threat_count,
    clear_threats,
)

logger = logging.getLogger(__name__)

# Endpoints that carry free-form natural language; their bodies are not
# regex-scanned (see security/threat_detector.py design notes).
_NL_ENDPOINTS = ("/chat", "/voice", "/knowledge")
_MAX_INSPECTED_BODY = 64 * 1024


# ---------------------------------------------------------------------------
# Application lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: connect DB on startup (optional), close on shutdown."""
    db = get_db_manager()
    try:
        await db.connect()
        logger.info("Database connected successfully.")
    except Exception as exc:
        # DB is optional for running the UI/API; continue without it.
        logger.warning("Database unavailable (continuing without DB): %s", exc)
    yield
    try:
        await db.close()
    except Exception as exc:
        logger.warning("Database close failed during shutdown: %s", exc)


app = FastAPI(
    title="Enterprise AI Assistant",
    description="Orchestrator-powered bilingual AI assistant with OpenCode, Dify, n8n, Ollama",
    version="1.0.0",
    lifespan=lifespan,
)

import os as _os

_cors_origins = _os.getenv(
    "CORS_ORIGINS",
    "http://localhost:8000,http://127.0.0.1:8000,"
    "http://localhost:8001,http://127.0.0.1:8001,"
    "http://localhost:5679,http://127.0.0.1:5679",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Threat detection middleware (runs before every request)
# ---------------------------------------------------------------------------
@app.middleware("http")
async def threat_detection_middleware(request: Request, call_next):
    """Inspect incoming requests for attack patterns and rate abuse.

    Bodies of natural-language endpoints are deliberately not regex-scanned;
    see security/threat_detector.py for the rationale and CWE references.
    Reading the body here is safe because Starlette caches it on the request
    (``request.body()`` stores ``_body``), so downstream handlers still see it.
    """
    client_ip = request.client.host if request.client else None
    method = request.method
    endpoint = request.url.path

    body_str = ""
    if not endpoint.startswith(_NL_ENDPOINTS):
        content_length = request.headers.get("content-length")
        try:
            declared = int(content_length) if content_length else 0
        except ValueError:
            declared = 0
        if declared <= _MAX_INSPECTED_BODY:
            body_bytes = await request.body()
            body_str = body_bytes.decode("utf-8", errors="replace")

    threat = record_threat(
        threat_detector.detect_request(
            user_id=None,
            ip_address=client_ip,
            endpoint=endpoint,
            method=method,
            body=body_str,
            query_params=str(request.query_params),
        )
    )
    if threat is not None:
        logger.warning(
            "THREAT DETECTED: %s (severity=%s, ip=%s, endpoint=%s)",
            threat.threat_type,
            threat.severity,
            client_ip,
            endpoint,
        )
        return JSONResponse(
            status_code=403,
            content={
                "error": "security_threat",
                "threat_id": threat.threat_id,
                "threat_type": threat.threat_type,
                "severity": threat.severity,
                "description_ar": threat.description_ar,
                "description_en": threat.description_en,
                "recommended_action": threat.recommended_action,
            },
        )

    response = await call_next(request)

    # OWASP Secure Headers (ASVS 5.0 V14): cheap, safe defaults for an API.
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Cache-Control", "no-store")
    return response


from fastapi import Request as _Request


@app.exception_handler(PermissionError)
async def _permission_error_handler(request: _Request, exc: PermissionError):
    return JSONResponse(status_code=403, content={"detail": str(exc)})


app.include_router(voice_router)


# ---------------------------------------------------------------------------
# Auth dependency: get_current_user is imported from api.deps (canonical).
# ---------------------------------------------------------------------------


def get_language_from_header(
    accept_language: Optional[str] = Header(default=None, alias="Accept-Language"),
) -> str:
    """Extract preferred language from Accept-Language header."""
    if not accept_language:
        return "ar"
    # Simple parse: first supported language wins
    for part in accept_language.split(","):
        lang = part.split(";")[0].strip().lower()
        if lang in ("ar", "en", "lb"):
            return "lb" if lang == "lb" else lang
    return "ar"


# ---------------------------------------------------------------------------
# Chat endpoint
# ---------------------------------------------------------------------------
@app.post("/chat")
async def chat(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user),
    language: str = Depends(get_language_from_header),
    orchestrator=Depends(get_orchestrator),
    rbac: RBACManager = Depends(get_rbac_manager),
    audit: AuditLogger = Depends(get_audit_logger),
):
    # Override language from body if explicitly provided
    body = await request.json()
    message = body.get("message", "")
    conversation_id = body.get("conversation_id") or str(uuid.uuid4())
    project_id = body.get("project_id")
    body_language = body.get("language", language)

    # Validate
    err = RequestValidator.validate_message(message)
    if err:
        await audit.log(
            user_id=str(user["id"]),
            action="chat:validation_error",
            resource="chat",
            metadata={"error": err},
        )
        raise HTTPException(status_code=400, detail=err)
    err = RequestValidator.validate_language(body_language)
    if err:
        raise HTTPException(status_code=400, detail=err)

    # IDOR guard: a supplied conversation_id must belong to the caller.
    supplied_conversation_id = body.get("conversation_id")
    if supplied_conversation_id:
        conv = await orchestrator.db.get_conversation(supplied_conversation_id)
        if conv is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if str(conv.get("user_id")) != str(user["id"]):
            await audit.log(
                user_id=str(user["id"]),
                action="chat:idor_blocked",
                resource="conversation",
                resource_id=supplied_conversation_id,
                metadata={"conversation_owner": str(conv.get("user_id"))},
            )
            raise HTTPException(
                status_code=403, detail="Not authorized to use this conversation"
            )

    # RBAC role-level
    rbac.require_permission(user["role"], "chat:write")

    # ------------------------------------------------------------------
    # Idempotency (optional, IETF idempotency-key semantics).
    # Claimed only after all authorization checks pass, so a rejected
    # request never burns the key.
    # ------------------------------------------------------------------
    idem_key = request.headers.get("Idempotency-Key")
    idem_claimed = False
    if idem_key:
        err = RequestValidator.validate_idempotency_key(idem_key)
        if err:
            raise HTTPException(status_code=400, detail=err)
        canonical = json.dumps(
            {
                "message": message,
                "conversation_id": body.get("conversation_id") or "",
                "project_id": project_id or "",
                "language": body_language,
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        request_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        claim = await orchestrator.db.claim_idempotency(
            user_id=str(user["id"]),
            endpoint="/chat",
            key=idem_key,
            request_hash=request_hash,
        )
        state = claim["state"]
        if state == "replay":
            return JSONResponse(
                content=claim["response"] or {},
                headers={"Idempotency-Replayed": "true"},
            )
        if state == "in_flight":
            raise HTTPException(
                status_code=409,
                detail="A request with this Idempotency-Key is still in progress",
                headers={"Retry-After": "1"},
            )
        if state == "conflict":
            raise HTTPException(
                status_code=409,
                detail="Idempotency-Key was already used with a different payload",
            )
        idem_claimed = state == "claimed"

    # Audit the request
    await audit.log(
        user_id=str(user["id"]),
        action="chat:request",
        resource="conversation",
        resource_id=conversation_id,
        metadata={
            "message_length": len(message),
            "language": body_language,
            "project_id": project_id,
        },
    )

    try:
        result = await orchestrator.route(
            user_id=str(user["id"]),
            message=message,
            conversation_id=conversation_id,
            project_id=project_id,
            language=body_language,
            rbac=rbac,
        )
    except Exception:
        if idem_claimed:
            await orchestrator.db.complete_idempotency(idem_key, status="failed")
        raise

    if not result.success:
        if idem_claimed:
            await orchestrator.db.complete_idempotency(idem_key, status="failed")
        await audit.log(
            user_id=str(user["id"]),
            action="chat:error",
            resource="conversation",
            resource_id=conversation_id,
            metadata={"error": result.error},
        )
        raise HTTPException(
            status_code=500, detail=result.error or "Orchestration failed"
        )

    # Audit successful response
    await audit.log(
        user_id=str(user["id"]),
        action="chat:response",
        resource="conversation",
        resource_id=conversation_id,
        metadata={
            "agent": result.agent_used,
            "task_type": result.route_decision.task_type.value,
            "language": result.language,
            "execution_time_ms": result.execution_time_ms,
            "sources_count": len(result.sources),
        },
    )

    payload = {
        "success": True,
        "answer": result.answer,
        "language": result.language,
        "agent_used": result.agent_used,
        "conversation_id": conversation_id,
        "route": {
            "target": result.route_decision.target.value,
            "target_name": result.route_decision.target_name,
            "confidence": result.route_decision.confidence,
            "task_type": result.route_decision.task_type.value,
            "model": result.route_decision.model,
        },
        "sources": result.sources,
        "execution_time_ms": result.execution_time_ms,
    }

    if idem_claimed:
        await orchestrator.db.complete_idempotency(
            idem_key, response=payload, status="completed"
        )

    return payload


# ---------------------------------------------------------------------------
# Agents endpoint
# ---------------------------------------------------------------------------
@app.get("/agents")
async def list_agents(
    user: Dict[str, Any] = Depends(get_current_user),
    rbac: RBACManager = Depends(get_rbac_manager),
    audit: AuditLogger = Depends(get_audit_logger),
):
    rbac.require_permission(user["role"], "agents:read")
    await audit.log(
        user_id=str(user["id"]),
        action="agents:list",
        resource="agents",
    )
    return {
        "agents": [
            {
                "name": "CEO",
                "type": "ceo",
                "description_ar": "التنسيق الاستراتيجي واتخاذ القرارات التنفيذية",
                "description_en": "Executive orchestration and strategic decision-making",
            },
            {
                "name": "Developer",
                "type": "developer",
                "description_ar": "كتابة الكود، مراجعته، وتحليل المشاريع",
                "description_en": "Code writing, review, and project analysis",
            },
            {
                "name": "Researcher",
                "type": "researcher",
                "description_ar": "البحث في قاعدة المعرفة وتلخيص النتائج مع توثيق المصادر",
                "description_en": "Knowledge base search and summarization with citations",
            },
            {
                "name": "Analyst",
                "type": "analyst",
                "description_ar": "تحليل البيانات والاستدلال المنطقي ودعم اتخاذ القرارات",
                "description_en": "Data analysis, logical reasoning, and decision support",
            },
            {
                "name": "Security",
                "type": "security",
                "description_ar": "مراجعة الثغرات الأمنية وتحليل سجلات التدقيق",
                "description_en": "Security vulnerability review and audit log analysis",
            },
            {
                "name": "Legal",
                "type": "legal",
                "description_ar": "تحليل المستندات القانونية والتحقق من الامتثال",
                "description_en": "Legal document analysis and compliance checking",
            },
        ]
    }


# ---------------------------------------------------------------------------
# Knowledge endpoint (permission-filtered, cross-language)
# ---------------------------------------------------------------------------
@app.post("/knowledge")
async def knowledge_search(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user),
    rbac: RBACManager = Depends(get_rbac_manager),
    orchestrator=Depends(get_orchestrator),
    audit: AuditLogger = Depends(get_audit_logger),
):
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(
            status_code=400, detail="Request body must be a JSON object"
        )

    query = body.get("query", "")
    language = body.get("language", "ar")
    cross_language = body.get("cross_language", True)

    err = RequestValidator.validate_query(query)
    if err:
        await audit.log(
            user_id=str(user["id"]),
            action="knowledge:validation_error",
            resource="knowledge_base",
            metadata={"error": err},
        )
        raise HTTPException(status_code=400, detail=err)
    err = RequestValidator.validate_language(language)
    if err:
        raise HTTPException(status_code=400, detail=err)
    if not isinstance(cross_language, bool):
        raise HTTPException(status_code=400, detail="cross_language must be a boolean")
    top_k = RequestValidator.normalize_top_k(body.get("top_k", 5))

    rbac.require_permission(user["role"], "knowledge:read")

    # Get accessible document IDs for this user
    accessible_ids = await rbac.get_accessible_documents(
        str(user["id"]), required_permission="read"
    )

    # Audit the search
    await audit.log(
        user_id=str(user["id"]),
        action="knowledge:search",
        resource="knowledge_base",
        metadata={
            "query_length": len(query),
            "language": language,
            "cross_language": cross_language,
            "accessible_docs": len(accessible_ids),
        },
    )

    results = await orchestrator.knowledge.search(
        query=query,
        language=language,
        top_k=top_k,
        accessible_document_ids=accessible_ids,
        cross_language=cross_language,
    )
    from knowledge.citations import CitationFormatter

    citations = CitationFormatter.format_citations(results, language=language)

    # Audit retrieved sources
    await audit.log(
        user_id=str(user["id"]),
        action="knowledge:retrieve",
        resource="knowledge_base",
        metadata={
            "results_count": len(results),
            "source_documents": [r.get("document_id") for r in results],
        },
    )

    return {
        "results": results,
        "citations": citations,
        "accessible_documents_count": len(accessible_ids),
    }


# ---------------------------------------------------------------------------
# Memory endpoint
# ---------------------------------------------------------------------------
@app.get("/memory")
async def get_memory(
    conversation_id: str,
    user: Dict[str, Any] = Depends(get_current_user),
    rbac: RBACManager = Depends(get_rbac_manager),
    orchestrator=Depends(get_orchestrator),
    audit: AuditLogger = Depends(get_audit_logger),
):
    rbac.require_permission(user["role"], "memory:read")
    # IDOR guard: only the conversation owner may read its history.
    conv = await orchestrator.db.get_conversation(conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if str(conv.get("user_id")) != str(user["id"]):
        await audit.log(
            user_id=str(user["id"]),
            action="memory:idor_blocked",
            resource="conversation",
            resource_id=conversation_id,
            metadata={"conversation_owner": str(conv.get("user_id"))},
        )
        raise HTTPException(
            status_code=403, detail="Not authorized to read this conversation"
        )
    messages = await orchestrator.db.get_conversation_messages(conversation_id)
    if messages is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await audit.log(
        user_id=str(user["id"]),
        action="memory:read",
        resource="conversation",
        resource_id=conversation_id,
    )
    return {"conversation_id": conversation_id, "messages": messages}


# ---------------------------------------------------------------------------
# Workflows endpoint (human approval required)
# ---------------------------------------------------------------------------
@app.get("/workflows/status")
async def workflows_status(
    user: Dict[str, Any] = Depends(get_current_user),
    rbac: RBACManager = Depends(get_rbac_manager),
    orchestrator=Depends(get_orchestrator),
):
    """Real n8n health: can we reach the editor and list workflows?"""
    rbac.require_permission(user["role"], "chat:read")
    base_url = orchestrator._get_n8n_base_url()
    api_key = orchestrator._get_n8n_api_key()
    import httpx

    reachable = False
    workflows: list = []
    error = ""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            root = await client.get(base_url + "/")
            reachable = root.status_code == 200
            if api_key:
                resp = await client.get(
                    base_url + "/api/v1/workflows",
                    headers={"X-N8N-API-KEY": api_key},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    entries = data.get("data", data) if isinstance(data, dict) else data
                    workflows = [
                        {
                            "id": str(w.get("id", "")),
                            "name": str(w.get("name", "Unnamed")),
                            "active": bool(w.get("active", False)),
                        }
                        for w in entries
                    ]
                else:
                    error = f"n8n API returned {resp.status_code}"
    except Exception as exc:
        error = str(exc)

    return {
        "reachable": reachable,
        "base_url": base_url,
        "has_api_key": bool(api_key),
        "editor_url": base_url + "/",
        "workflows": workflows,
        "note": (
            "n8n editor is up but no API key is configured, so workflow ids "
            "cannot be listed or executed."
        )
        if reachable and not api_key
        else error,
    }


@app.post("/workflows")
async def trigger_workflow(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user),
    rbac: RBACManager = Depends(get_rbac_manager),
    orchestrator=Depends(get_orchestrator),
    audit: AuditLogger = Depends(get_audit_logger),
    db=Depends(get_db_manager),
):
    body = await request.json()
    workflow_id = body.get("workflow_id", "")
    payload = body.get("payload", {})
    auto_approve = body.get("auto_approve", False)

    rbac.require_permission(user["role"], "workflows:manage")

    # For consequential actions, require human approval unless auto_approve
    # (admin override). Otherwise create an approval request.
    if not auto_approve and user["role"] != "admin":
        approval = await db.create_approval_request(
            user_id=str(user["id"]),
            workflow_id=workflow_id,
            action_type="workflow:execute",
            target_resource=workflow_id,
            parameters=payload,
        )
        await audit.log(
            user_id=str(user["id"]),
            action="workflow:approval_requested",
            resource="workflow",
            resource_id=workflow_id,
            metadata={"approval_id": str(approval["id"])},
        )
        return {
            "success": False,
            "approval_required": True,
            "approval_id": str(approval["id"]),
            "message": "Human approval required before executing this workflow.",
        }

    result = await orchestrator.route_to_n8n(
        user_id=str(user["id"]),
        workflow_id=workflow_id,
        payload=payload,
    )
    if not result.success:
        await audit.log(
            user_id=str(user["id"]),
            action="workflow:error",
            resource="workflow",
            resource_id=workflow_id,
            metadata={"error": result.error},
        )
        raise HTTPException(status_code=500, detail=result.error or "Workflow failed")

    await audit.log(
        user_id=str(user["id"]),
        action="workflow:executed",
        resource="workflow",
        resource_id=workflow_id,
        metadata={"payload_keys": list(payload.keys())},
    )
    return {"success": True, "result": result.tool_results}


# ---------------------------------------------------------------------------
# Approvals endpoints
# ---------------------------------------------------------------------------
@app.post("/approvals")
async def create_approval(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user),
    rbac: RBACManager = Depends(get_rbac_manager),
    db=Depends(get_db_manager),
    audit: AuditLogger = Depends(get_audit_logger),
):
    body = await request.json()
    action_type = body.get("action_type", "")
    target_resource = body.get("target_resource")
    parameters = body.get("parameters", {})
    workflow_id = body.get("workflow_id")
    risk_level = body.get("risk_level", "medium")
    approval_level = body.get("approval_level", "B")

    if risk_level not in ("low", "medium", "high", "critical"):
        raise HTTPException(
            status_code=400, detail="risk_level must be low/medium/high/critical"
        )
    if approval_level not in ("A", "B", "C", "D"):
        raise HTTPException(status_code=400, detail="approval_level must be A/B/C/D")

    rbac.require_permission(user["role"], "workflows:manage")

    approval = await db.create_approval_request(
        user_id=str(user["id"]),
        workflow_id=workflow_id,
        action_type=action_type,
        target_resource=target_resource,
        parameters=parameters,
        risk_level=risk_level,
        approval_level=approval_level,
    )
    await audit.log(
        user_id=str(user["id"]),
        action="approval:create",
        resource="approval",
        resource_id=str(approval["id"]),
        metadata={
            "action_type": action_type,
            "risk_level": risk_level,
            "approval_level": approval_level,
        },
    )
    return {"success": True, "approval": approval}


@app.post("/approvals/{request_id}/decide")
async def decide_approval(
    request_id: str,
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user),
    rbac: RBACManager = Depends(get_rbac_manager),
    db=Depends(get_db_manager),
    audit: AuditLogger = Depends(get_audit_logger),
):
    body = await request.json()
    decision = body.get("decision", "")  # "approved" or "rejected"
    reason = body.get("reason")
    otp_code = body.get("otp_code")

    if decision not in ("approved", "rejected"):
        raise HTTPException(
            status_code=400, detail="decision must be 'approved' or 'rejected'"
        )

    # Only admins or the requester can decide
    approval = await db.get_approval_request(request_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if user["role"] != "admin" and str(approval["user_id"]) != str(user["id"]):
        raise HTTPException(
            status_code=403, detail="Not authorized to decide this approval"
        )

    # Expiry guard
    expires_at = approval.get("expires_at")
    if expires_at:
        exp = expires_at
        if isinstance(exp, str):
            exp = datetime.fromisoformat(exp)
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp <= datetime.now(timezone.utc):
            await db.decide_approval_request(
                request_id=request_id,
                decision="expired",
                decided_by=str(user["id"]),
                reason="expired before decision",
            )
            raise HTTPException(status_code=410, detail="Approval request expired")

    # Level D (critical) requires TOTP second factor
    if approval.get("approval_level") == "D" and decision == "approved":
        if not otp_code:
            raise HTTPException(
                status_code=403,
                detail="TOTP code required for critical (level D) approvals",
            )
        totp_ok = await db.verify_totp(user_id=str(user["id"]), otp_code=otp_code)
        if not totp_ok:
            await audit.log(
                user_id=str(user["id"]),
                action="approval:totp_failed",
                resource="approval",
                resource_id=request_id,
            )
            raise HTTPException(status_code=403, detail="Invalid or expired TOTP code")

    success = await db.decide_approval_request(
        request_id=request_id,
        decision=decision,
        decided_by=str(user["id"]),
        reason=reason,
    )
    if not success:
        raise HTTPException(
            status_code=400, detail="Approval already decided or expired"
        )

    await audit.log(
        user_id=str(user["id"]),
        action=f"approval:{decision}",
        resource="approval",
        resource_id=request_id,
        metadata={"reason": reason, "approval_level": approval.get("approval_level")},
    )
    return {"success": True, "decision": decision}


@app.get("/approvals")
async def list_approvals(
    user: Dict[str, Any] = Depends(get_current_user),
    rbac: RBACManager = Depends(get_rbac_manager),
    db=Depends(get_db_manager),
    audit: AuditLogger = Depends(get_audit_logger),
):
    rbac.require_permission(user["role"], "workflows:manage")
    approvals = await db.get_pending_approvals(
        user_id=None if user["role"] == "admin" else str(user["id"])
    )
    await audit.log(
        user_id=str(user["id"]),
        action="approvals:list",
        resource="approval",
    )
    return {"approvals": approvals}


# ---------------------------------------------------------------------------
# TOTP enrollment (second factor for level D approvals)
# ---------------------------------------------------------------------------
@app.post("/auth/totp/enroll")
async def enroll_totp(
    user: Dict[str, Any] = Depends(get_current_user),
    orchestrator=Depends(get_orchestrator),
    audit: AuditLogger = Depends(get_audit_logger),
):
    """Enroll the calling user in TOTP and return the otpauth:// URL once.

    The secret is shown exactly once; the server stores only its AES-256-GCM
    ciphertext. Re-enrolling replaces the previous authenticator.
    """
    from urllib.parse import quote

    secret = await orchestrator.db.enroll_totp(str(user["id"]))
    issuer = "AI Assistant"
    account = user.get("email") or user.get("username") or str(user["id"])
    otpauth_url = (
        f"otpauth://totp/{quote(issuer)}:{quote(str(account))}"
        f"?secret={secret}&issuer={quote(issuer)}"
        "&algorithm=SHA1&digits=6&period=30"
    )
    await audit.log(
        user_id=str(user["id"]),
        action="auth:totp:enroll",
        resource="approval_tokens",
        resource_id=str(user["id"]),
    )
    return {
        "secret": secret,
        "otpauth_url": otpauth_url,
        "algorithm": "SHA1",
        "digits": 6,
        "period": 30,
        "message_ar": "امسح رمز QR ثم أدخل الرمز المكوّن من 6 أرقام لتأكيد التسجيل.",
        "message_en": "Scan the QR code, then submit the 6-digit code to confirm enrollment.",
    }


@app.post("/auth/totp/verify")
async def verify_totp(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user),
    orchestrator=Depends(get_orchestrator),
    audit: AuditLogger = Depends(get_audit_logger),
):
    """Verify a TOTP code for the calling user (confirms enrollment or step-up)."""
    body = await request.json()
    code = str(body.get("code", "")).strip() if isinstance(body, dict) else ""
    if not code.isdigit() or len(code) != 6:
        raise HTTPException(status_code=400, detail="code must be 6 digits")

    ok = await orchestrator.db.verify_totp(str(user["id"]), code)
    await audit.log(
        user_id=str(user["id"]),
        action="auth:totp:verify",
        resource="approval_tokens",
        resource_id=str(user["id"]),
        metadata={"success": ok},
    )
    if not ok:
        client_ip = request.client.host if request.client else None
        record_threat(
            threat_detector.record_totp_failure(
                user_id=str(user["id"]),
                ip_address=client_ip,
                endpoint="/auth/totp/verify",
                method="POST",
            )
        )
        raise HTTPException(status_code=401, detail="Invalid or already-used code")
    return {"success": True}


# ---------------------------------------------------------------------------
# Settings endpoint
# ---------------------------------------------------------------------------
@app.get("/settings")
async def get_settings(
    user: Dict[str, Any] = Depends(get_current_user),
    rbac: RBACManager = Depends(get_rbac_manager),
    audit: AuditLogger = Depends(get_audit_logger),
):
    rbac.require_permission(user["role"], "settings:read")
    await audit.log(
        user_id=str(user["id"]),
        action="settings:read",
        resource="settings",
    )
    from llm.router import LLMRouter, TaskType

    models = LLMRouter.DEFAULT_MODELS
    return {
        "llm_models": {
            "coding": models[TaskType.CODING],
            "reasoning": models[TaskType.REASONING],
            "general": models[TaskType.GENERAL],
        },
        "voice": {
            "stt_engine": "faster-whisper",
            "tts_engine": "piper",
            "supported_languages": ["ar", "en", "lb"],
        },
        "knowledge": {
            "rag_top_k": 5,
            "hybrid_search": True,
            "reranking": True,
            "cross_language": True,
        },
        "supported_languages": ["ar", "en", "lb"],
    }


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "healthy"}


# ---------------------------------------------------------------------------
# Security threats endpoint (admin only)
# ---------------------------------------------------------------------------
@app.get("/security/threats")
async def list_security_threats(
    user: Dict[str, Any] = Depends(get_current_user),
    rbac: RBACManager = Depends(get_rbac_manager),
    audit: AuditLogger = Depends(get_audit_logger),
    limit: int = 50,
):
    """Return recent security threats. Admin/auditor only."""
    rbac.require_permission(user["role"], "audit:read")
    limit = max(1, min(limit, 500))
    items = recent_threats(limit)
    await audit.log(
        user_id=str(user["id"]),
        action="security:threats:read",
        resource="security",
        metadata={"limit": limit, "returned": len(items)},
    )
    return {
        "threats": [t.to_dict() for t in items],
        "total": threat_count(),
    }


@app.post("/security/threats/clear")
async def clear_security_threats(
    user: Dict[str, Any] = Depends(get_current_user),
    rbac: RBACManager = Depends(get_rbac_manager),
    audit: AuditLogger = Depends(get_audit_logger),
):
    """Clear the in-memory threat store. Admin only."""
    rbac.require_permission(user["role"], "audit:read")
    cleared = clear_threats()
    await audit.log(
        user_id=str(user["id"]),
        action="security:threats:clear",
        resource="security",
        metadata={"cleared": cleared},
    )
    return {"success": True, "cleared": cleared}


# ---------------------------------------------------------------------------
# Dashboard (static UI)
# ---------------------------------------------------------------------------
_DASHBOARD_DIR = _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "dashboard"
)

if _os.path.isdir(_DASHBOARD_DIR):
    app.mount(
        "/dashboard", StaticFiles(directory=_DASHBOARD_DIR, html=True), name="dashboard"
    )

    @app.get("/", include_in_schema=False)
    async def root_redirect():
        return RedirectResponse(url="/dashboard/index.html")
