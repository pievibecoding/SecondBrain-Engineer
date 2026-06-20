import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.wiki_builder import build_entity_page
from backend.schemas.auth import UserResponse
from backend.dependencies.auth import get_current_user
from backend.dependencies.services import get_lightrag_graph_client, get_lightrag_query_client


# ── wiki_builder tests ────────────────────────────────────────────────────────

def test_build_entity_page_basic():
    entity = {
        "name": "E1", "type": "PROJECT", "description": "desc",
        "relations": [{"src": "E1", "rel_type": "USES", "tgt": "E2", "description": "d"}],
        "sources": [{"file": "BOM.xlsx", "nas_path": "/mnt/nas/BOM.xlsx"}],
    }
    page = build_entity_page(entity, [])
    assert page.name == "E1"
    assert page.type == "PROJECT"
    assert len(page.relations) == 1
    assert len(page.sources) == 1


def test_dedup_relations_and_sources():
    entity = {
        "name": "E1", "type": "PROJECT",
        "relations": [
            {"src": "E1", "rel_type": "USES", "tgt": "E2"},
            {"src": "E1", "rel_type": "USES", "tgt": "E2"},  # duplicate
        ],
        "sources": [{"file": "a.pdf"}, {"file": "a.pdf"}],  # duplicate
    }
    page = build_entity_page(entity, [])
    assert len(page.relations) == 1
    assert len(page.sources) == 1


def test_missing_optional_fields_returns_empty_lists_no_crash():
    entity = {"name": "E1", "type": "EQUIPMENT"}  # no relations, no sources, no description
    page = build_entity_page(entity, [])
    assert page.name == "E1"
    assert page.description is None
    assert page.relations == []
    assert page.sources == []
    assert isinstance(page.graph_nodes, list)
    assert isinstance(page.graph_edges, list)


def test_null_relations_no_crash():
    entity = {"name": "E1", "type": "PROJECT", "relations": None, "sources": None}
    page = build_entity_page(entity, [])
    assert page.relations == []
    assert page.sources == []
