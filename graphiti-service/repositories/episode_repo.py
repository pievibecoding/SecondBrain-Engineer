"""
Episode repository — DB access layer for Graphiti service.
Uses SQLAlchemy AsyncSession. Falls back to in-memory dict when no DB session provided (unit tests).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.episode import Episode


# ── In-memory fallback (used by unit tests / MVP without DB) ─────────────────

_IN_MEMORY: dict[str, Episode] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Async DB operations ───────────────────────────────────────────────────────

async def create_episode(
    conversation_id: str,
    db: Optional[AsyncSession] = None,
) -> Episode:
    ep = Episode(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        status="pending",
    )
    if db is not None:
        db.add(ep)
        await db.flush()
    else:
        _IN_MEMORY[ep.id] = ep
    return ep


async def update_episode_status(
    episode_id: str,
    status: str,
    entities: int = 0,
    relations: int = 0,
    error: Optional[str] = None,
    db: Optional[AsyncSession] = None,
) -> Optional[Episode]:
    if db is not None:
        result = await db.execute(select(Episode).where(Episode.id == episode_id))
        ep = result.scalar_one_or_none()
        if ep is None:
            return None
    else:
        ep = _IN_MEMORY.get(episode_id)
        if ep is None:
            return None

    ep.status = status
    ep.entities_added = entities
    ep.relations_added = relations
    ep.error_msg = error
    ep.updated_at = _now()

    if db is not None:
        await db.flush()
    return ep


async def get_episode_by_conversation(
    conversation_id: str,
    db: Optional[AsyncSession] = None,
) -> list[Episode]:
    if db is not None:
        result = await db.execute(
            select(Episode).where(Episode.conversation_id == conversation_id)
        )
        return list(result.scalars().all())
    return [e for e in _IN_MEMORY.values() if e.conversation_id == conversation_id]
