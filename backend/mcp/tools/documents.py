from time import perf_counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.integrations.lightrag.query import LightRAGQueryClient
from backend.integrations.lightrag.errors import LightRAGError, LightRAGTimeoutError
from backend.logger import logger, get_correlation_id
from backend.models.nas_file import NasFile


async def list_documents(
    db: AsyncSession,
    project: str | None = None,
    doc_type: str | None = None,
) -> list:
    """Liệt kê tài liệu đã index. Filter theo dự án hoặc loại tài liệu."""
    cid = get_correlation_id()
    logger.info("mcp_tool_start", tool_name="list_documents", correlation_id=cid)

    stmt = select(NasFile).where(NasFile.status == "indexed")
    if project:
        stmt = stmt.where(NasFile.nas_path.ilike(f"%{project}%"))
    if doc_type:
        stmt = stmt.where(NasFile.nas_path.ilike(f"%{doc_type}%"))

    result = await db.execute(stmt)
    files = result.scalars().all()

    docs = [
        {
            "nas_path": f.nas_path,
            "status": f.status,
            "indexed_at": f.indexed_at.isoformat() if f.indexed_at else None,
        }
        for f in files
    ]
    logger.info("mcp_tool_done", tool_name="list_documents", correlation_id=cid, result_size=len(docs))
    return docs


async def get_document_context(db: AsyncSession, nas_path: str) -> str:
    """Lấy nội dung/context của một file cụ thể trên NAS."""
    cid = get_correlation_id()
    logger.info("mcp_tool_start", tool_name="get_document_context", correlation_id=cid)

    # look up NasFile
    result = await db.execute(select(NasFile).where(NasFile.nas_path == nas_path))
    nas_file = result.scalar_one_or_none()

    if nas_file is None or nas_file.status != "indexed":
        status = nas_file.status if nas_file else "not_found"
        logger.info("mcp_tool_not_found", tool_name="get_document_context", nas_path=nas_path, status=status, correlation_id=cid)
        return f"[Không tìm thấy] File '{nas_path}' chưa được index hoặc không tồn tại trong hệ thống."

    # query LightRAG for chunks
    client = LightRAGQueryClient(base_url=settings.LIGHTRAG_URL)
    try:
        result = await client.query(f"Nội dung file: {nas_path}", cid, mode="local")
        context = result.get("response", "")
        output = f"[{nas_path}] ({nas_file.status})\n\n{context}"
        logger.info("mcp_tool_done", tool_name="get_document_context", correlation_id=cid, result_size=len(output))
        return output
    except LightRAGTimeoutError:
        return f"[Lỗi timeout] Không thể lấy context cho file '{nas_path}'."
    except (LightRAGError, Exception) as e:
        logger.error("mcp_tool_error", tool_name="get_document_context", error_message=str(e), correlation_id=cid)
        return f"[Lỗi] Không thể lấy context: {e}"
