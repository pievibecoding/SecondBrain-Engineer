from time import perf_counter

from backend.config import settings
from backend.integrations.lightrag.graph import LightRAGGraphClient
from backend.integrations.lightrag.errors import LightRAGNotFoundError, LightRAGError, LightRAGTimeoutError
from backend.logger import logger, get_correlation_id
from backend.services.wiki_builder import build_entity_page


async def get_entity(entity_name: str) -> dict:
    """Lấy thông tin chi tiết về một entity. Trả về: description, relations, source documents."""
    cid = get_correlation_id()
    start = perf_counter()

    if not entity_name or not entity_name.strip():
        return {"error": "entity_name cannot be empty"}
    if len(entity_name) > 200:
        return {"error": "entity_name too long (max 200 chars)"}

    entity_name = entity_name.strip()
    logger.info("mcp_tool_start", tool_name="get_entity", correlation_id=cid)

    client = LightRAGGraphClient(base_url=settings.LIGHTRAG_URL)
    try:
        entity = await client.get_entity(entity_name, cid)
        edges = await client.get_edges(entity_name, cid)
        page = build_entity_page(entity, edges)
        result = page.model_dump()
        elapsed = int((perf_counter() - start) * 1000)
        logger.info(
            "mcp_tool_done",
            tool_name="get_entity",
            correlation_id=cid,
            duration_ms=elapsed,
            result_size=len(str(result)),
        )
        return result
    except LightRAGNotFoundError:
        logger.info("mcp_tool_not_found", tool_name="get_entity", entity_name=entity_name, correlation_id=cid)
        return {"error": "Entity not found", "entity_name": entity_name}
    except LightRAGTimeoutError:
        logger.error("mcp_tool_error", tool_name="get_entity", error_type="timeout", correlation_id=cid)
        return {"error": "LightRAG không phản hồi (timeout)", "entity_name": entity_name}
    except LightRAGError as e:
        logger.error("mcp_tool_error", tool_name="get_entity", error_type="lightrag_error", error_message=str(e), correlation_id=cid)
        return {"error": f"Không thể truy vấn graph: {e}", "entity_name": entity_name}
    except Exception as e:
        logger.error("mcp_tool_error", tool_name="get_entity", error_type="unexpected", error_message=str(e), correlation_id=cid)
        return {"error": str(e), "entity_name": entity_name}
