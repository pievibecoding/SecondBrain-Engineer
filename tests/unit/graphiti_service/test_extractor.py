"""
Unit tests for graphiti-service extractor.
LLM is mocked — no real LLM needed.
"""
import pytest
from unittest.mock import AsyncMock, patch

from services.extractor import (
    extract_entities,
    _parse_llm_output,
    _validate_and_normalise,
    _format_turns,
    VALID_ENTITY_TYPES,
)


TURNS = [
    {"role": "user", "content": "Dự án Heineken dùng motor gì?"},
    {"role": "assistant", "content": "Dự án Heineken Bình Dương 2024 dùng Motor Siemens 1LE1 7.5kW."},
]

VALID_LLM_OUTPUT = """{
  "entities": [
    {"name": "Heineken Bình Dương 2024", "type": "PROJECT", "description": "Dự án nhà máy bia"},
    {"name": "Motor Siemens 1LE1", "type": "COMPONENT", "description": "Motor 7.5kW"}
  ],
  "relations": [
    {"src": "Heineken Bình Dương 2024", "rel_type": "USES", "tgt": "Motor Siemens 1LE1", "description": "dùng trong dây chuyền"}
  ]
}"""


# ── _parse_llm_output ─────────────────────────────────────────────────────────

def test_parse_plain_json():
    result = _parse_llm_output(VALID_LLM_OUTPUT)
    assert "entities" in result
    assert "relations" in result


def test_parse_with_markdown_fence():
    wrapped = f"```json\n{VALID_LLM_OUTPUT}\n```"
    result = _parse_llm_output(wrapped)
    assert "entities" in result


def test_parse_no_json_raises():
    with pytest.raises(ValueError):
        _parse_llm_output("No JSON here at all")


# ── _validate_and_normalise ───────────────────────────────────────────────────

def test_validate_filters_invalid_entity_type():
    data = {
        "entities": [
            {"name": "Valid", "type": "PROJECT"},
            {"name": "Invalid", "type": "UNKNOWN_TYPE"},
        ],
        "relations": [],
    }
    entities, _ = _validate_and_normalise(data)
    names = [e["name"] for e in entities]
    assert "Valid" in names
    assert "Invalid" not in names


def test_validate_deduplicates_case_insensitive():
    data = {
        "entities": [
            {"name": "Heineken", "type": "CLIENT"},
            {"name": "heineken", "type": "CLIENT"},
        ],
        "relations": [],
    }
    entities, _ = _validate_and_normalise(data)
    assert len(entities) == 1


def test_validate_normalises_relation_type_fallback():
    data = {
        "entities": [],
        "relations": [{"src": "A", "rel_type": "TOTALLY_INVALID", "tgt": "B"}],
    }
    _, relations = _validate_and_normalise(data)
    assert relations[0]["rel_type"] == "RELATED_TO"


def test_validate_accepts_valid_relation_type():
    data = {
        "entities": [],
        "relations": [{"src": "A", "rel_type": "USES", "tgt": "B"}],
    }
    _, relations = _validate_and_normalise(data)
    assert relations[0]["rel_type"] == "USES"


def test_validate_skips_entity_with_empty_name():
    data = {
        "entities": [{"name": "", "type": "PROJECT"}],
        "relations": [],
    }
    entities, _ = _validate_and_normalise(data)
    assert entities == []


# ── extract_entities (integration with mock LLM) ─────────────────────────────

@pytest.mark.asyncio
async def test_extract_entities_with_mock_llm():
    with patch("services.extractor._call_llm", new=AsyncMock(return_value=VALID_LLM_OUTPUT)):
        result = await extract_entities(TURNS, correlation_id="test-cid")

    assert result["entities_added"] == 2
    assert result["relations_added"] == 1
    assert len(result["entities"]) == 2
    assert len(result["relations"]) == 1


@pytest.mark.asyncio
async def test_extract_entities_invalid_json_returns_zeros():
    with patch("services.extractor._call_llm", new=AsyncMock(return_value="not valid json")):
        result = await extract_entities(TURNS)

    assert result["entities_added"] == 0
    assert result["relations_added"] == 0


@pytest.mark.asyncio
async def test_extract_entities_llm_not_configured_returns_zeros():
    # no mock → _call_llm raises RuntimeError (LLM not configured)
    result = await extract_entities(TURNS)
    assert result["entities_added"] == 0
    assert result["relations_added"] == 0


@pytest.mark.asyncio
async def test_extract_entities_empty_turns_returns_zeros():
    result = await extract_entities([])
    assert result["entities_added"] == 0


@pytest.mark.asyncio
async def test_extract_entities_partial_output():
    """LLM returns valid JSON but only entities, no relations."""
    partial = '{"entities": [{"name": "Motor Siemens", "type": "COMPONENT"}], "relations": []}'
    with patch("services.extractor._call_llm", new=AsyncMock(return_value=partial)):
        result = await extract_entities(TURNS)
    assert result["entities_added"] == 1
    assert result["relations_added"] == 0
