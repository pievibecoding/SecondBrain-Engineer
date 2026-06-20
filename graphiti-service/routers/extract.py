"""
POST /extract endpoint — accepts conversation turns, creates episode, runs extraction in background.
Returns accepted response immediately (non-blocking).
"""
import asyncio
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field

from logger import logger
from repositories.episode_repo import (
    create_episode,
    update_episode_status,
)
from services.extractor import extract_entities
from services.graph_writer import write_graph

router = APIRouter()


class Turn(BaseModel):
    role: str
    content: str


class ExtractRequest(BaseModel):
    conversation_id: str
    turns: list[Turn] = Field(min_length=1)
    timestamp: datetime | None = None


class ExtractResponse(BaseModel):
    ok: bool
    entities_added: int = 0
    relations_added: int = 0


@router.post("/extract", response_model=ExtractResponse)
async def post_extract(req: Request, payload: ExtractRequest):
    cid = req.headers.get("X-Correlation-ID")
    if not cid:
        logger.warning("missing_correlation_id", endpoint="POST /extract")

    logger.info(
        "extract_received",
        conversation_id=payload.conversation_id,
        turns_count=len(payload.turns),
        correlation_id=cid,
    )

    # validate turns length
    if len(payload.turns) < 1:
        raise HTTPException(status_code=422, detail="turns must have at least 1 item")

    # create episode record (pending)
    ep = await create_episode(payload.conversation_id)

    # schedule background extraction — does not block response
    asyncio.create_task(
        _run_extraction(ep.id, payload.conversation_id, [t.model_dump() for t in payload.turns], cid)
    )

    return ExtractResponse(ok=True)


async def _run_extraction(
    episode_id: str,
    conversation_id: str,
    turns: list[dict],
    correlation_id: str | None,
) -> None:
    """Background task: extract → write graph → update episode status."""
    try:
        await update_episode_status(episode_id, "processing")

        result = await extract_entities(turns, correlation_id=correlation_id)
        entities = result.get("entities", [])
        relations = result.get("relations", [])

        graph_result = await write_graph(episode_id, entities, relations, correlation_id)

        await update_episode_status(
            episode_id,
            "done",
            entities=graph_result["entities_added"],
            relations=graph_result["relations_added"],
        )
        logger.info(
            "extract_done",
            episode_id=episode_id,
            conversation_id=conversation_id,
            entities_added=graph_result["entities_added"],
            relations_added=graph_result["relations_added"],
            correlation_id=correlation_id,
        )
    except Exception as e:
        await update_episode_status(episode_id, "failed", error=str(e))
        logger.error(
            "extract_failed",
            episode_id=episode_id,
            conversation_id=conversation_id,
            error=str(e),
            correlation_id=correlation_id,
        )
