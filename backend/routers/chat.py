from fastapi import APIRouter, Depends, Request, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
import asyncio
import json
from time import perf_counter

from sqlalchemy.ext.asyncio import AsyncSession
from backend.dependencies.auth import get_current_user
from backend.dependencies.services import get_lightrag_query_client, get_graphiti_client
from backend.database import get_session
from backend.schemas.chat import ChatRequest, ChatResponse, ConversationResponse, MessageResponse, CitationItem
from backend.services.conversation_service import get_or_create_conversation, add_message, list_conversations, list_messages
from backend.integrations.lightrag.query import LightRAGQueryClient
from backend.integrations.graphiti import extract as graphiti_extract
from backend.logger import get_correlation_id, logger

router = APIRouter()


def normalize_citations(raw) -> list[dict]:
    if not raw:
        return []
    items = []
    if isinstance(raw, dict):
        raw = raw.get("sources", [])
    for src in raw:
        if isinstance(src, dict):
            if src.get("file"):
                items.append({"type": "document", **src})
            elif src.get("entity"):
                items.append({"type": "graph_entity", **src})
            else:
                items.append({"type": "document", **src})
        else:
            items.append({"type": "document", "file": str(src)})
    return items


@router.post("/stream")
async def chat_stream(request: Request, payload: ChatRequest, db: AsyncSession = Depends(get_session), current_user=Depends(get_current_user), lightrag: LightRAGQueryClient = Depends(get_lightrag_query_client)):
    cid = request.headers.get("X-Correlation-ID") or get_correlation_id()
    start = perf_counter()

    user_id = current_user["id"] if isinstance(current_user, dict) else str(current_user.id)

    # create/load conversation and save user message
    try:
        conv = await get_or_create_conversation(db, user_id, payload.conversation_id, payload.message)
    except Exception:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await add_message(db, str(conv.id), "user", payload.message)

    async def event_generator():
        accumulated = []
        try:
            async for chunk in lightrag.query_stream(payload.message, cid, mode="mix"):
                yield f"data: {chunk}\n\n"
                accumulated.append(chunk)
        except Exception as e:
            logger.error("lightrag_stream_error", error=str(e), correlation_id=cid)
            err = json.dumps({"detail": "LightRAG stream error"})
            yield f"event: error\ndata: {err}\n\n"
            return

        full = "".join(accumulated)
        citations = []
        await add_message(db, str(conv.id), "assistant", full, citations)

        # fire-and-forget graphiti — own task, does not block stream
        async def trigger_graphiti():
            try:
                await graphiti_extract(
                    str(conv.id),
                    [{"role": "user", "content": payload.message}, {"role": "assistant", "content": full}],
                    cid,
                )
            except Exception:
                logger.warning("graphiti_failed", conversation_id=str(conv.id), correlation_id=cid)

        if full:  # skip if empty assistant response
            asyncio.create_task(trigger_graphiti())

        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("")
async def chat(payload: ChatRequest, request: Request, background: BackgroundTasks, db: AsyncSession = Depends(get_session), current_user=Depends(get_current_user), lightrag: LightRAGQueryClient = Depends(get_lightrag_query_client)):
    cid = request.headers.get("X-Correlation-ID") or get_correlation_id()
    start = perf_counter()

    user_id = current_user["id"] if isinstance(current_user, dict) else str(current_user.id)

    try:
        conv = await get_or_create_conversation(db, user_id, payload.conversation_id, payload.message)
    except Exception:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await add_message(db, str(conv.id), "user", payload.message)

    try:
        resp = await lightrag.query(payload.message, cid, mode="mix")
    except Exception as e:
        logger.error("lightrag_query_error", error=str(e), correlation_id=cid)
        raise HTTPException(status_code=502, detail="LightRAG error")

    answer = resp.get("response", "")
    sources = resp.get("sources", [])
    citations = normalize_citations(sources)

    await add_message(db, str(conv.id), "assistant", answer, citations)

    # background Graphiti — use async background task correctly
    async def _graphiti_bg():
        try:
            await graphiti_extract(
                str(conv.id),
                [{"role": "user", "content": payload.message}, {"role": "assistant", "content": answer}],
                cid,
            )
        except Exception:
            logger.warning("graphiti_failed", conversation_id=str(conv.id), correlation_id=cid)

    if answer:  # skip if empty
        background.add_task(_graphiti_bg)

    latency = int((perf_counter() - start) * 1000)
    return ChatResponse(
        conversation_id=str(conv.id),
        answer=answer,
        citations=[CitationItem(**c) for c in citations],
        query_mode="mix",
        latency_ms=latency,
    )


@router.get("/conversations", response_model=list[ConversationResponse])
async def get_conversations(db: AsyncSession = Depends(get_session), current_user=Depends(get_current_user)):
    convs = await list_conversations(db, current_user.id)
    return [ConversationResponse.model_validate(c) for c in convs]


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_messages(conversation_id: str, db: AsyncSession = Depends(get_session), current_user=Depends(get_current_user)):
    msgs = await list_messages(db, current_user.id, conversation_id)
    return [MessageResponse.model_validate(m) for m in msgs]
