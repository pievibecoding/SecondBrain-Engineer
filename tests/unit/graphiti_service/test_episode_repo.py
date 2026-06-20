"""
Unit tests for episode_repo using in-memory fallback (no DB).
"""
import pytest

from repositories.episode_repo import (
    create_episode,
    update_episode_status,
    get_episode_by_conversation,
    _IN_MEMORY,
)


@pytest.fixture(autouse=True)
def clear_store():
    _IN_MEMORY.clear()
    yield
    _IN_MEMORY.clear()


@pytest.mark.asyncio
async def test_create_episode_returns_pending():
    ep = await create_episode("conv-1")
    assert ep.conversation_id == "conv-1"
    assert ep.status == "pending"
    assert ep.id in _IN_MEMORY


@pytest.mark.asyncio
async def test_update_episode_status_done():
    ep = await create_episode("conv-1")
    updated = await update_episode_status(ep.id, "done", entities=3, relations=2)
    assert updated.status == "done"
    assert updated.entities_added == 3
    assert updated.relations_added == 2


@pytest.mark.asyncio
async def test_update_episode_status_failed_stores_error():
    ep = await create_episode("conv-1")
    updated = await update_episode_status(ep.id, "failed", error="LLM timeout")
    assert updated.status == "failed"
    assert updated.error_msg == "LLM timeout"


@pytest.mark.asyncio
async def test_update_nonexistent_episode_returns_none():
    result = await update_episode_status("nonexistent-id", "done")
    assert result is None


@pytest.mark.asyncio
async def test_get_episode_by_conversation_returns_all():
    ep1 = await create_episode("conv-42")
    ep2 = await create_episode("conv-42")
    ep_other = await create_episode("conv-99")

    results = await get_episode_by_conversation("conv-42")
    ids = [e.id for e in results]
    assert ep1.id in ids
    assert ep2.id in ids
    assert ep_other.id not in ids


@pytest.mark.asyncio
async def test_get_episode_by_conversation_empty():
    results = await get_episode_by_conversation("no-such-conv")
    assert results == []
