"""Tests for routing work to n8n through a workflow webhook."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from orchestrator.router import (
    OpenCodeOrchestrator,
    OrchestrationResult,
    RouteDecision,
    RouteTarget,
    TaskClassifier,
    TaskType,
)


class _FakeAudit:
    """Records audit calls instead of writing them."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def log(self, **kwargs) -> None:
        self.calls.append(kwargs)


class _FakeRESTTool:
    """Stands in for tools.rest.RESTTool and records the request."""

    next_response: dict = {"status": 200, "body": {"id": "row-1"}}
    instances: list["_FakeRESTTool"] = []

    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self.requests: list[dict] = []
        self.closed = False
        self.result = _FakeRESTTool.next_response
        _FakeRESTTool.instances.append(self)

    async def post(self, path, json_body=None, headers=None):
        self.requests.append({"path": path, "json_body": json_body})
        return self.result

    async def close(self) -> None:
        self.closed = True


@pytest.fixture
def orchestrator(monkeypatch):
    """Orchestrator with only the collaborators needed by route_to_n8n."""
    orch = object.__new__(OpenCodeOrchestrator)
    orch.audit = _FakeAudit()
    _FakeRESTTool.instances = []
    _FakeRESTTool.next_response = {"status": 200, "body": {"id": "row-1"}}
    monkeypatch.setattr("tools.rest.RESTTool", _FakeRESTTool)
    monkeypatch.delenv("N8N_NOTIFY_WEBHOOK", raising=False)
    return orch


def test_posts_to_webhook_with_injected_user_id(orchestrator):
    result = asyncio.run(
        orchestrator.route_to_n8n(
            user_id="715ae2b7-2591-45ac-96a9-b1dc37423055",
            payload={"message": "hello", "type": "info"},
        )
    )

    tool = _FakeRESTTool.instances[0]
    assert tool.requests == [
        {
            "path": "/webhook/notify-webhook",
            "json_body": {
                "message": "hello",
                "type": "info",
                "user_id": "715ae2b7-2591-45ac-96a9-b1dc37423055",
            },
        }
    ]
    assert result.success is True
    assert result.error is None
    assert result.route_decision.target is RouteTarget.N8N_WORKFLOW
    assert result.tool_results == [
        {"workflow": "notify-webhook", "response": {"id": "row-1"}}
    ]
    assert '"id": "row-1"' in result.answer


def test_user_id_overrides_payload_value(orchestrator):
    asyncio.run(
        orchestrator.route_to_n8n(
            user_id="real-user",
            payload={"message": "hi", "user_id": "spoofed-user"},
        )
    )

    sent = _FakeRESTTool.instances[0].requests[0]["json_body"]
    assert sent["user_id"] == "real-user"


def test_uses_configured_webhook_path(orchestrator, monkeypatch):
    monkeypatch.setenv("N8N_NOTIFY_WEBHOOK", "another-hook")

    result = asyncio.run(
        orchestrator.route_to_n8n(user_id="u-1", payload={"message": "hi"})
    )

    assert _FakeRESTTool.instances[0].requests[0]["path"] == "/webhook/another-hook"
    assert result.route_decision.target_name == "another-hook"


def test_http_error_becomes_failed_result(orchestrator):
    _FakeRESTTool.next_response = {"status": 500, "error": "user_id must be a UUID"}

    result = asyncio.run(
        orchestrator.route_to_n8n(user_id="u-1", payload={"message": "hi"})
    )

    assert result.success is False
    assert result.error == "user_id must be a UUID"
    assert result.tool_results == []


def test_rejection_message_from_response_body_is_used(orchestrator):
    _FakeRESTTool.next_response = {
        "status": 400,
        "error": "Client error '400 Bad Request' for url 'http://n8n:5678/webhook/notify-webhook'",
        "body": {"error": "user_id must be a UUID"},
    }

    result = asyncio.run(
        orchestrator.route_to_n8n(user_id="u-1", payload={"message": "hi"})
    )

    assert result.success is False
    assert result.error == "user_id must be a UUID"


def test_error_without_status_is_still_a_failure(orchestrator):
    _FakeRESTTool.next_response = {"status": None, "error": "connection refused"}

    result = asyncio.run(
        orchestrator.route_to_n8n(user_id="u-1", payload={"message": "hi"})
    )

    assert result.success is False
    assert result.error == "connection refused"


def test_invalid_webhook_path_is_rejected_without_request(orchestrator):
    result = asyncio.run(
        orchestrator.route_to_n8n(
            user_id="u-1",
            payload={"message": "hi"},
            webhook_path="../../api/v1/workflows/execute",
        )
    )

    assert result.success is False
    assert result.error == "Invalid webhook path"
    assert _FakeRESTTool.instances == []


def test_client_is_closed_after_request(orchestrator):
    asyncio.run(orchestrator.route_to_n8n(user_id="u-1", payload={"message": "hi"}))

    assert _FakeRESTTool.instances[0].closed is True


def test_audit_entry_records_webhook_path(orchestrator):
    asyncio.run(orchestrator.route_to_n8n(user_id="u-1", payload={"message": "hi"}))

    entry = orchestrator.audit.calls[0]
    assert entry["action"] == "n8n_workflow"
    assert entry["resource_id"] == "notify-webhook"
    assert entry["metadata"] == {"payload_keys": ["message"]}


def _decision() -> RouteDecision:
    return RouteDecision(
        target=RouteTarget.N8N_WORKFLOW,
        target_name="notify-webhook",
        confidence=1.0,
        reasoning="ok",
        task_type=TaskType.AUTOMATION,
        model="",
    )


def test_notification_route_stores_conversation_and_confirms(orchestrator, monkeypatch):
    stored = []

    async def fake_n8n(**kwargs):
        return OrchestrationResult(
            success=True,
            answer='{"id": "row-1"}',
            language="ar",
            agent_used=None,
            route_decision=_decision(),
            tool_results=[{"workflow": "notify-webhook", "response": {"id": "row-1"}}],
            execution_time_ms=12.0,
        )

    async def fake_store(**kwargs):
        stored.append(kwargs)

    monkeypatch.setattr(orchestrator, "route_to_n8n", fake_n8n)
    monkeypatch.setattr(orchestrator, "_store_conversation", fake_store)

    result = asyncio.run(
        orchestrator._route_notification(
            user_id="u-1",
            message="سجّل تنبيه",
            conversation_id="c-1",
            project_id=None,
            language="ar",
            start_time=datetime.now(timezone.utc),
            memory_entries=[],
        )
    )

    assert result.success is True
    assert result.answer == "تم حفظ الإشعار بنجاح."
    assert result.agent_used == "n8n"
    assert stored[0]["agent_id"] == "n8n"
    assert stored[0]["user_message"] == "سجّل تنبيه"
    assert orchestrator.audit.calls[-1]["action"] == "notification_route"
    assert orchestrator.audit.calls[-1]["metadata"]["success"] is True


def test_notification_route_failure_is_returned(orchestrator, monkeypatch):
    async def fake_n8n(**kwargs):
        return OrchestrationResult(
            success=False,
            answer="",
            language="ar",
            agent_used=None,
            route_decision=_decision(),
            error="user_id must be a UUID",
        )

    async def fake_store(**kwargs):
        return None

    monkeypatch.setattr(orchestrator, "route_to_n8n", fake_n8n)
    monkeypatch.setattr(orchestrator, "_store_conversation", fake_store)

    result = asyncio.run(
        orchestrator._route_notification(
            user_id="u-1",
            message="سجّل تنبيه",
            conversation_id="c-1",
            project_id=None,
            language="ar",
            start_time=datetime.now(timezone.utc),
            memory_entries=[],
        )
    )

    assert result.success is False
    assert result.error == "user_id must be a UUID"
