import pytest
from pydantic import ValidationError
from backend.schemas.mcp import SearchKnowledgeInput, PushKnowledgeInput, PushKnowledgeOutput


# ── SearchKnowledgeInput ──────────────────────────────────────────────────────

def test_search_input_rejects_empty_query():
    with pytest.raises(ValidationError):
        SearchKnowledgeInput(query="")


def test_search_input_rejects_whitespace_query():
    with pytest.raises(ValidationError):
        SearchKnowledgeInput(query="   ")


def test_search_input_strips_query():
    inp = SearchKnowledgeInput(query="  Heineken motor  ")
    assert inp.query == "Heineken motor"


def test_search_input_default_mode_is_mix():
    inp = SearchKnowledgeInput(query="test")
    assert inp.mode == "mix"


def test_search_input_accepts_valid_modes():
    for mode in ("mix", "local", "global"):
        inp = SearchKnowledgeInput(query="test", mode=mode)
        assert inp.mode == mode


def test_search_input_rejects_invalid_mode():
    with pytest.raises(ValidationError):
        SearchKnowledgeInput(query="test", mode="naive")


# ── PushKnowledgeInput ───────────────────────────────────────────────────────

def test_push_input_rejects_missing_entity_name():
    with pytest.raises(ValidationError):
        PushKnowledgeInput(
            entity_type="PROJECT",
            description="desc",
            relations=[],
            source="file.pdf",
        )


def test_push_input_rejects_missing_source():
    with pytest.raises(ValidationError):
        PushKnowledgeInput(
            entity_name="Alpha",
            entity_type="PROJECT",
            description="desc",
            relations=[],
        )


def test_push_input_valid():
    inp = PushKnowledgeInput(
        entity_name="Heineken",
        entity_type="CLIENT",
        description="Khách hàng",
        relations=[{"src": "a", "rel_type": "b", "tgt": "c"}],
        source="BOM.xlsx",
    )
    assert inp.entity_name == "Heineken"
    assert len(inp.relations) == 1


# ── PushKnowledgeOutput ──────────────────────────────────────────────────────

def test_push_output_shape():
    out = PushKnowledgeOutput(ok=True, entity_name="Heineken", relations_added=2)
    assert out.ok is True
    assert out.relations_added == 2
