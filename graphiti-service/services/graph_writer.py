"""
Graph writer service — upserts nodes and edges from extracted entities/relations.
Uses in-memory store for MVP. Replace with real graph DB (PostgreSQL AGE / Neo4j) later.
Implements:
  - deduplication by canonical name
  - provenance tracking (episode_id, timestamp)
  - idempotency: re-processing same episode does not create duplicates
  - temporal: newer contradicting edges mark older ones expired
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from logger import logger

# ── In-memory graph store (MVP) ───────────────────────────────────────────────

_NODES: dict[str, dict] = {}   # canonical_name → node
_EDGES: list[dict] = []        # list of edge records
_PROCESSED_EPISODES: set[str] = set()


def _canonical(name: str) -> str:
    return name.strip().lower()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _upsert_node(name: str, etype: str, description: str | None, episode_id: str) -> bool:
    """Returns True if new node created, False if merged into existing."""
    key = _canonical(name)
    if key not in _NODES:
        _NODES[key] = {
            "name": name,
            "type": etype,
            "description": description,
            "created_at": _now(),
            "episode_id": episode_id,
        }
        return True
    # merge: update description if newer has one
    if description and not _NODES[key].get("description"):
        _NODES[key]["description"] = description
    return False


def _upsert_edge(
    src: str,
    rel_type: str,
    tgt: str,
    description: str | None,
    episode_id: str,
    timestamp: str,
) -> bool:
    """Returns True if new edge created, False if already exists.
    Marks older contradicting edges expired when rel_type implies contradiction.
    """
    src_key = _canonical(src)
    tgt_key = _canonical(tgt)

    for existing in _EDGES:
        if (
            _canonical(existing["src"]) == src_key
            and existing["rel_type"] == rel_type
            and _canonical(existing["tgt"]) == tgt_key
            and existing.get("episode_id") == episode_id
        ):
            # already processed this episode edge → idempotent, skip
            return False

    # mark older edges with same src+rel_type expired (temporal semantics)
    for existing in _EDGES:
        if (
            _canonical(existing["src"]) == src_key
            and existing["rel_type"] == rel_type
            and not existing.get("expired")
        ):
            existing["expired"] = True
            existing["expired_at"] = timestamp

    _EDGES.append({
        "src": src,
        "rel_type": rel_type,
        "tgt": tgt,
        "description": description,
        "episode_id": episode_id,
        "timestamp": timestamp,
        "expired": False,
    })
    return True


async def write_graph(
    episode_id: str,
    entities: list[dict[str, Any]],
    relations: list[dict[str, Any]],
    correlation_id: str | None = None,
) -> dict:
    """
    Upsert entities and relations into graph store.

    Returns {"entities_added": int, "relations_added": int}.
    """
    # idempotency: skip if episode already processed
    if episode_id in _PROCESSED_EPISODES:
        logger.info(
            "graph_write_skipped_duplicate",
            episode_id=episode_id,
            correlation_id=correlation_id,
        )
        return {"entities_added": 0, "relations_added": 0}

    timestamp = _now()
    entities_added = 0
    relations_added = 0

    for e in entities or []:
        if _upsert_node(e.get("name", ""), e.get("type", ""), e.get("description"), episode_id):
            entities_added += 1

    for r in relations or []:
        if _upsert_edge(
            src=r.get("src", ""),
            rel_type=r.get("rel_type", "RELATED_TO"),
            tgt=r.get("tgt", ""),
            description=r.get("description"),
            episode_id=episode_id,
            timestamp=timestamp,
        ):
            relations_added += 1

    _PROCESSED_EPISODES.add(episode_id)

    logger.info(
        "graph_write_done",
        episode_id=episode_id,
        entities_added=entities_added,
        relations_added=relations_added,
        correlation_id=correlation_id,
    )
    return {"entities_added": entities_added, "relations_added": relations_added}


# ── Test helpers ──────────────────────────────────────────────────────────────

def _reset_graph() -> None:
    """Clear in-memory store — used in tests only."""
    _NODES.clear()
    _EDGES.clear()
    _PROCESSED_EPISODES.clear()


def get_nodes() -> dict:
    return dict(_NODES)


def get_edges() -> list:
    return list(_EDGES)
