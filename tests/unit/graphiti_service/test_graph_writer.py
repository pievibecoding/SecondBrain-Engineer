"""
Unit tests for graphiti-service graph_writer.
Uses in-memory store — no real DB needed.
"""
import pytest

from services.graph_writer import (
    write_graph,
    _reset_graph,
    get_nodes,
    get_edges,
)


@pytest.fixture(autouse=True)
def reset():
    """Reset in-memory graph before each test."""
    _reset_graph()
    yield
    _reset_graph()


ENTITIES = [
    {"name": "Heineken 2024", "type": "PROJECT", "description": "Nhà máy bia"},
    {"name": "Motor Siemens", "type": "COMPONENT", "description": "7.5kW"},
]
RELATIONS = [
    {"src": "Heineken 2024", "rel_type": "USES", "tgt": "Motor Siemens", "description": "line 1"},
]


@pytest.mark.asyncio
async def test_write_graph_creates_nodes_and_edges():
    result = await write_graph("ep-1", ENTITIES, RELATIONS)
    assert result["entities_added"] == 2
    assert result["relations_added"] == 1
    assert len(get_nodes()) == 2
    assert len(get_edges()) == 1


@pytest.mark.asyncio
async def test_write_graph_idempotent_same_episode():
    await write_graph("ep-1", ENTITIES, RELATIONS)
    result = await write_graph("ep-1", ENTITIES, RELATIONS)
    # second call same episode → 0 added
    assert result["entities_added"] == 0
    assert result["relations_added"] == 0
    # store still has original data
    assert len(get_nodes()) == 2


@pytest.mark.asyncio
async def test_write_graph_deduplicates_nodes_across_episodes():
    # Same entity in two different episodes — should not duplicate
    await write_graph("ep-1", [ENTITIES[0]], [])
    await write_graph("ep-2", [ENTITIES[0]], [])
    nodes = get_nodes()
    # Only one node for "heineken 2024"
    assert len(nodes) == 1


@pytest.mark.asyncio
async def test_write_graph_marks_older_edges_expired():
    # First episode establishes an edge
    await write_graph("ep-1", ENTITIES, RELATIONS)
    edges_before = get_edges()
    assert not edges_before[0]["expired"]

    # Second episode adds a contradicting edge (same src+rel_type, different tgt)
    new_entities = [
        {"name": "Heineken 2024", "type": "PROJECT"},
        {"name": "Motor ABB", "type": "COMPONENT"},
    ]
    new_relations = [
        {"src": "Heineken 2024", "rel_type": "USES", "tgt": "Motor ABB"},
    ]
    await write_graph("ep-2", new_entities, new_relations)

    edges = get_edges()
    # Original edge should be expired
    original = next(e for e in edges if e["tgt"] == "Motor Siemens")
    assert original["expired"] is True
    # New edge should not be expired
    new_edge = next(e for e in edges if e["tgt"] == "Motor ABB")
    assert new_edge["expired"] is False


@pytest.mark.asyncio
async def test_write_graph_empty_inputs():
    result = await write_graph("ep-empty", [], [])
    assert result["entities_added"] == 0
    assert result["relations_added"] == 0
