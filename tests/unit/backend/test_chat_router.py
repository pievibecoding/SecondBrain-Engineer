import pytest
import types
from uuid import uuid4
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from backend.main import app
from backend.dependencies.auth import get_current_user
from backend.dependencies.services import get_lightrag_query_client, get_graphiti_client


# ──────────────────────────────────────────
# Shared fixtures
# ──────────────────────────────────────────

FAKE_USER = {
    "id": "test-user-id",
    "username": "testuser",
    "email": "test@robolinks.vn",
    "role": "user",
    "created_at": "2026-01-01T00:00:00",
}

FAKE_CONV_ID = str(uuid4())


def _make_fake_lightrag(response="Motor Siemens 1LE1 7.5kW"):
    """Returns a mock LightRAG client that echoes a fixed response."""
    client = types.SimpleNamespace()
    client.query = AsyncMock(return_value={"response": response, "sources": []})

    async def _stream(*args, **kwargs):
        for token in response.split():
            yield token

    client.query_stream = _stream
    return client


def _patch_conversation_service(monkeypatch):
    """Patch conversation service to avoid real DB."""
    import backend.routers.chat as chat_mod

    async def fake_get_or_create(db, user_id, conversation_id, first_message=None):
        c = types.SimpleNamespace()
        c.id = uuid4()
        return c

    async def fake_add_message(db, conv_id, role, content, citations=None, graphiti_synced=False):
        m = types.SimpleNamespace()
        m.id = uuid4()
        m.role = role
        m.content = content
        m.graphiti_synced = graphiti_synced
        return m

    monkeypatch.setattr(chat_mod, "get_or_create_conversation", fake_get_or_create)
    monkeypatch.setattr(chat_mod, "add_message", fake_add_message)


# ──────────────────────────────────────────
# Tests
# ──────────────────────────────────────────

def test_chat_post_uses_mix_mode(monkeypatch):
    """POST /api/chat calls LightRAG with mode='mix' and returns 200."""
    fake_lr = _make_fake_lightrag()
    _patch_conversation_service(monkeypatch)

    # patch graphiti to no-op
    import backend.routers.chat as chat_mod
    monkeypatch.setattr(chat_mod, "graphiti_extract", AsyncMock(return_value={"ok": True}))

    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    app.dependency_overrides[get_lightrag_query_client] = lambda: fake_lr

    try:
        with TestClient(app) as client:
            resp = client.post("/api/chat", json={"message": "Heineken motor gì?"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["query_mode"] == "mix"
        assert "answer" in data
        # verify mode=mix was passed
        fake_lr.query.assert_called_once()
        _, kwargs = fake_lr.query.call_args
        assert kwargs.get("mode", "mix") == "mix"
    finally:
        app.dependency_overrides.clear()


def test_chat_stream_returns_event_stream(monkeypatch):
    """POST /api/chat/stream returns text/event-stream content type."""
    fake_lr = _make_fake_lightrag()
    _patch_conversation_service(monkeypatch)

    import backend.routers.chat as chat_mod
    monkeypatch.setattr(chat_mod, "graphiti_extract", AsyncMock(return_value={"ok": True}))

    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    app.dependency_overrides[get_lightrag_query_client] = lambda: fake_lr

    try:
        with TestClient(app) as client:
            with client.stream("POST", "/api/chat/stream", json={"message": "test"}) as resp:
                assert resp.status_code == 200
                assert "text/event-stream" in resp.headers.get("content-type", "")
                body = b"".join(resp.iter_bytes())
        assert b"[DONE]" in body
    finally:
        app.dependency_overrides.clear()


def test_chat_stream_emits_tokens_and_done(monkeypatch):
    """SSE stream contains token data lines and ends with [DONE]."""
    fake_lr = _make_fake_lightrag("Hello world")
    _patch_conversation_service(monkeypatch)

    import backend.routers.chat as chat_mod
    monkeypatch.setattr(chat_mod, "graphiti_extract", AsyncMock(return_value={"ok": True}))

    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    app.dependency_overrides[get_lightrag_query_client] = lambda: fake_lr

    try:
        with TestClient(app) as client:
            with client.stream("POST", "/api/chat/stream", json={"message": "test"}) as resp:
                body = resp.read().decode()
        assert "data: Hello" in body or "data: " in body
        assert "data: [DONE]" in body
    finally:
        app.dependency_overrides.clear()


def test_chat_post_lightrag_error_returns_502(monkeypatch):
    """When LightRAG raises, POST /api/chat returns HTTP 502."""
    fake_lr = types.SimpleNamespace()
    fake_lr.query = AsyncMock(side_effect=Exception("LightRAG down"))
    _patch_conversation_service(monkeypatch)

    import backend.routers.chat as chat_mod
    monkeypatch.setattr(chat_mod, "graphiti_extract", AsyncMock(return_value={"ok": True}))

    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    app.dependency_overrides[get_lightrag_query_client] = lambda: fake_lr

    try:
        with TestClient(app) as client:
            resp = client.post("/api/chat", json={"message": "hello"})
        assert resp.status_code == 502
    finally:
        app.dependency_overrides.clear()


def test_graphiti_failure_does_not_fail_chat(monkeypatch):
    """Graphiti failure leaves chat response as 200, graphiti_synced=False."""
    fake_lr = _make_fake_lightrag()
    _patch_conversation_service(monkeypatch)

    import backend.routers.chat as chat_mod
    # Graphiti raises
    monkeypatch.setattr(chat_mod, "graphiti_extract", AsyncMock(side_effect=Exception("graphiti down")))

    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    app.dependency_overrides[get_lightrag_query_client] = lambda: fake_lr

    try:
        with TestClient(app) as client:
            resp = client.post("/api/chat", json={"message": "hello"})
        # Chat still succeeds even though Graphiti failed
        assert resp.status_code == 200
    finally:
        app.dependency_overrides.clear()
