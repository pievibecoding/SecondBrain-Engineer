from time import perf_counter

from backend.config import settings
from backend.integrations.lightrag.query import LightRAGQueryClient
from backend.integrations.lightrag.errors import LightRAGError, LightRAGTimeoutError
from backend.logger import logger, get_correlation_id
from backend.schemas.mcp import SearchKnowledgeInput


async def search_knowledge(query: str, mode: str = "mix") -> str:
    """Tìm kiếm trong knowledge base Robolinks. mode: 'mix' (mặc định), 'local', 'global'"""
    cid = get_correlation_id()
    start = perf_counter()

    # validate
    try:
        inp = SearchKnowledgeInput(query=query, mode=mode)
    except Exception as e:
        return f"[Lỗi validation] {e}"

    logger.info("mcp_tool_start", tool_name="search_knowledge", correlation_id=cid)

    client = LightRAGQueryClient(base_url=settings.LIGHTRAG_URL)
    try:
        result = await client.query(inp.query, cid, mode=inp.mode)
        answer = result.get("response", "")
        elapsed = int((perf_counter() - start) * 1000)
        logger.info(
            "mcp_tool_done",
            tool_name="search_knowledge",
            correlation_id=cid,
            duration_ms=elapsed,
            result_size=len(answer),
        )
        return answer
    except LightRAGTimeoutError:
        logger.error("mcp_tool_error", tool_name="search_knowledge", error_type="timeout", correlation_id=cid)
        return "[Lỗi] LightRAG không phản hồi (timeout). Vui lòng thử lại."
    except LightRAGError as e:
        logger.error("mcp_tool_error", tool_name="search_knowledge", error_type="lightrag_error", error_message=str(e), correlation_id=cid)
        return f"[Lỗi] Không thể truy vấn knowledge base: {e}"
    except Exception as e:
        logger.error("mcp_tool_error", tool_name="search_knowledge", error_type="unexpected", error_message=str(e), correlation_id=cid)
        return f"[Lỗi] {e}"
