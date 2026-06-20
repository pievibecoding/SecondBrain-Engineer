import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.schemas.auth import UserResponse
from backend.dependencies.auth import get_current_user
from backend.dependencies.services import get_lightrag_graph_client, get_lightrag_query_client
from backend.integrations.lightrag.errors import LightRAGNotFoundError


FAKE_USER = UserResponse.model_validate({
    "id": "test-user", "username": "test", "email": "test@x",
    "role": "user", "created_at": "2026-01-01T00:00:00",
})

FAKE_ENTITY = {
    "name": "Heineken 2024", "type": "PROJECT",
    "description": "Nhà máy bia", "relations": [], "sources": [],
}


class FakeGraphClient:
    async def get_entity(self, name, cid):
        return {**FAKE_ENTITY, "name": name}

    async def get_edges(self, name, cid):
        return []


class FakeGraphClientNotFound:
    async def get_entity(self, name, cid):
        raise LightRAGNotFoundError("not found", operation="get_entity", status_code=404)

    async def get_edges(self, name, cid):
        return []


class FakeQueryClient:
    async def query(self, q, cid, mode="mix"):
        return {"hits": [{"name": "Heineken 2024", "type": "PROJECT", "description": "d", "score": 0.9}]}


def _setup(graph_client=None, query_client=None):
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    if graph_client:
        app.dependency_overrides[get_lightrag_graph_client] = lambda: graph_client
    if query_client:
        app.dependency_overrides[get_lightrag_query_client] = lambda: query_client


def _teardown():
    app.dependency_overrides.clear()


# ── GET /api/wiki/entity/{name} ───────────────────────────────────────────────

def test_get_entity_returns_wiki_page_response():
    _setup(graph_client=FakeGraphClient())
    try:
        with TestClient(app) as client:
            res = client.get("/api/wiki/entity/Heineken")
        assert res.status_code == 200
        data = res.json()
        assert data["name"] == "Heineken"
        assert "relations" in data
        assert "sources" in data
        assert "graph_nodes" in data
        assert "graph_edges" in data
    finally:
        _teardown()


def test_get_entity_not_found_returns_404():
    _setup(graph_client=FakeGraphClientNotFound())
    try:
        with TestClient(app) as client:
            res = client.get("/api/wiki/entity/NonExistent")
        assert res.status_code == 404
    finally:
        _teardown()


def test_get_entity_requires_auth():
    with TestClient(app) as client:
        res = client.get("/api/wiki/entity/Heineken")
    assert res.status_code in (401, 403)  # 401 or 403 depending on auth impl


# ── GET /api/wiki/search ──────────────────────────────────────────────────────

def test_search_returns_list():
    _setup(query_client=FakeQueryClient())
    try:
        with TestClient(app) as client:
            res = client.get("/api/wiki/search?q=Heineken")
        assert res.status_code == 200
        assert isinstance(res.json(), list)
    finally:
        _teardown()


# ── GET /api/wiki/entities ────────────────────────────────────────────────────

def test_entities_returns_empty_list_http_200():
    _setup()
    try:
        with TestClient(app) as client:
            res = client.get("/api/wiki/entities?type=PROJECT")
        assert res.status_code == 200
        assert res.json() == []
    finally:
        _teardown()


def test_entities_no_type_filter_returns_200():
    _setup()
    try:
        with TestClient(app) as client:
            res = client.get("/api/wiki/entities")
        assert res.status_code == 200
    finally:
        _teardown()
