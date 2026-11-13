"""Tests for the generic REST tool, using a mocked transport (no network)."""

from __future__ import annotations

import asyncio

import httpx

from tools.rest import RESTTool


def _tool(monkeypatch, handler) -> RESTTool:
    """Build a RESTTool whose client talks to a mocked transport."""
    tool = RESTTool(base_url="http://example.test")

    async def _client():
        return httpx.AsyncClient(
            base_url="http://example.test", transport=httpx.MockTransport(handler)
        )

    monkeypatch.setattr(tool, "_get_client", _client)
    return tool


def test_success_returns_status_body_headers(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": "row-1"})

    tool = _tool(monkeypatch, handler)
    result = asyncio.run(tool.post("/webhook/notify", json_body={"message": "hi"}))

    assert result["status"] == 200
    assert result["body"] == {"id": "row-1"}
    assert "headers" in result


def test_http_error_keeps_response_body(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "user_id must be a UUID"})

    tool = _tool(monkeypatch, handler)
    result = asyncio.run(tool.post("/webhook/notify", json_body={"message": "hi"}))

    assert result["status"] == 400
    assert result["body"] == {"error": "user_id must be a UUID"}
    assert "Client error" in result["error"]


def test_http_error_without_json_body_keeps_raw_text(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, text="<html>bad gateway</html>")

    tool = _tool(monkeypatch, handler)
    result = asyncio.run(tool.get("/health"))

    assert result["status"] == 502
    assert result["body"] == {"raw": "<html>bad gateway</html>"}


def test_network_failure_has_no_body(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    tool = _tool(monkeypatch, handler)
    result = asyncio.run(tool.get("/health"))

    assert result["status"] is None
    assert result["error"] == "connection refused"
    assert "body" not in result
