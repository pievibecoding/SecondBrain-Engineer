from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from backend.dependencies.auth import get_current_user
from backend.dependencies.services import get_lightrag_graph_client, get_lightrag_query_client
from backend.dependencies.services import get_lightrag_graph_client as _graph_dep
from backend.schemas.wiki import WikiPageResponse, EntitySummaryResponse
from backend.services.wiki_builder import build_entity_page
from backend.integrations.lightrag.errors import LightRAGNotFoundError, LightRAGError, LightRAGTimeoutError
from backend.database import get_session
from backend.logger import get_correlation_id

router = APIRouter()

VALID_ENTITY_TYPES = {
    "PROJECT", "CLIENT", "EQUIPMENT", "COMPONENT", "SUPPLIER",
    "PERSON", "PROCESS", "ERROR_CODE", "DOCUMENT", "LOCATION", "STANDARD",
}


@router.get("/entity/{entity_name}", response_model=WikiPageResponse)
async def get_entity_page(entity_name: str, request: Request, db: AsyncSession = Depends(get_session), current_user=Depends(get_current_user), graph_client=Depends(get_lightrag_graph_client)):
    cid = request.headers.get("X-Correlation-ID") or get_correlation_id() or ""
    try:
        entity = await graph_client.get_entity(entity_name, cid)
        edges = await graph_client.get_edges(entity_name, cid)
    except LightRAGNotFoundError:
        raise HTTPException(status_code=404, detail="Entity not found")
    except LightRAGTimeoutError:
        raise HTTPException(status_code=504, detail="Graph service timeout")
    except LightRAGError:
        raise HTTPException(status_code=502, detail="Graph service error")

    page = build_entity_page(entity or {}, edges or [])
    return page


@router.get("/search")
async def search(q: str = Query(...), request: Request = None, current_user=Depends(get_current_user), query_client=Depends(get_lightrag_query_client)):
    cid = (request.headers.get("X-Correlation-ID") if request is not None else None) or get_correlation_id() or ""
    try:
        resp = await query_client.query(q, cid, mode="mix")
    except LightRAGTimeoutError:
        raise HTTPException(status_code=504, detail="LightRAG timeout")
    except LightRAGError:
        raise HTTPException(status_code=502, detail="LightRAG error")

    # normalize into EntitySummaryResponse[]
    items = []
    for hit in resp.get("hits", resp.get("results", [])):
        items.append(EntitySummaryResponse(name=hit.get("name"), type=hit.get("type"), description=hit.get("description"), score=hit.get("score")))
    return items


@router.get("/entities")
async def list_entities(type: str | None = None, current_user=Depends(get_current_user)):
    if type is not None and type not in VALID_ENTITY_TYPES:
        raise HTTPException(status_code=422, detail="Invalid entity type")
    # MVP limitation
    return []
