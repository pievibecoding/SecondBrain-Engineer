from datetime import datetime
from hashlib import md5
from pathlib import Path, PurePosixPath

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.integrations.lightrag.errors import LightRAGError
from backend.integrations.lightrag.ingest import LightRAGIngestClient
from backend.logger import logger
from backend.models.nas_file import NasFile
from backend.services.document_parser import parse_document_async


def _compute_lightrag_doc_id(content: str) -> str:
    return f"doc-{md5(content.strip().encode('utf-8')).hexdigest()}"


def build_lightrag_metadata(nas_file: NasFile) -> dict:
    return {
        "source": "nas",
        "nas_path": nas_file.nas_path,
        "folder": str(PurePosixPath(nas_file.nas_path).parent),
        "folder_type": nas_file.folder_type,
        "uploaded_by": "system",
    }


async def ingest_nas_file(
    db: AsyncSession,
    nas_file_id: str,
    lightrag_client: LightRAGIngestClient,
    correlation_id: str,
) -> NasFile:
    result = await db.execute(select(NasFile).where(NasFile.id == nas_file_id))
    nas_file = result.scalar_one_or_none()
    if nas_file is None:
        raise HTTPException(status_code=404, detail=f"NasFile not found: {nas_file_id}")

    if nas_file.status not in {"queued", "failed", "indexed"}:
        raise HTTPException(status_code=409, detail="File is not queued for ingestion")

    nas_file.status = "indexing"
    await db.flush()

    metadata = build_lightrag_metadata(nas_file)
    file_path = Path(nas_file.nas_path)

    try:
        response = await _ingest_with_parser(
            nas_file=nas_file,
            lightrag_client=lightrag_client,
            file_path=file_path,
            metadata=metadata,
            correlation_id=correlation_id,
        )
    except LightRAGError as exc:
        nas_file.status = "failed"
        nas_file.error_msg = str(exc)[:1000]
        await db.flush()
        logger.error(
            "nas_ingestion_failed",
            nas_file_id=str(nas_file.id),
            nas_path=nas_file.nas_path,
            error=str(exc),
            correlation_id=correlation_id,
        )
        return nas_file

    nas_file.lightrag_doc_id = response.get("id") or response.get("doc_id") or nas_file.lightrag_doc_id
    nas_file.status = "indexed"
    nas_file.indexed_at = datetime.utcnow()
    nas_file.error_msg = None
    await db.flush()
    logger.info(
        "nas_ingestion_completed",
        nas_file_id=str(nas_file.id),
        nas_path=nas_file.nas_path,
        lightrag_doc_id=nas_file.lightrag_doc_id,
        correlation_id=correlation_id,
    )
    return nas_file


async def _ingest_with_parser(
    nas_file: NasFile,
    lightrag_client: LightRAGIngestClient,
    file_path: Path,
    metadata: dict,
    correlation_id: str,
) -> dict:
    """
    Try pre-processing với python-docx / pdfplumber+pymupdf / openpyxl trước.
    Nếu pre-processing thành công → POST /documents/text (bypass native parser).
    Nếu không support hoặc fail → fallback POST /api/v1/docs (LightRAG native).
    """
    # Attempt pre-processing
    parse_result = await parse_document_async(file_path, correlation_id=correlation_id)

    if parse_result is None:
        # Extension không support pre-processing → LightRAG native
        logger.info(
            "parser_skipped_native_fallback",
            file=file_path.name,
            reason="extension not supported for pre-processing",
            correlation_id=correlation_id,
        )
        return await _ingest_native_with_duplicate_retry(
            lightrag_client=lightrag_client,
            file_path=nas_file.nas_path,
            metadata=metadata,
            correlation_id=correlation_id,
        )

    if not parse_result.success:
        # Parser fail → fallback về native, log warning
        logger.warning(
            "parser_failed_native_fallback",
            file=file_path.name,
            parser=parse_result.parser_used,
            error=parse_result.error,
            correlation_id=correlation_id,
        )
        return await _ingest_native_with_duplicate_retry(
            lightrag_client=lightrag_client,
            file_path=nas_file.nas_path,
            metadata=metadata,
            correlation_id=correlation_id,
        )

    if not parse_result.text.strip():
        # Parse thành công nhưng không có text → fallback
        logger.warning(
            "parser_empty_result_native_fallback",
            file=file_path.name,
            parser=parse_result.parser_used,
            correlation_id=correlation_id,
        )
        return await _ingest_native_with_duplicate_retry(
            lightrag_client=lightrag_client,
            file_path=nas_file.nas_path,
            metadata=metadata,
            correlation_id=correlation_id,
        )

    # Pre-processing thành công → gửi text qua /documents/text
    logger.info(
        "parser_sending_text",
        file=file_path.name,
        parser=parse_result.parser_used,
        chars=parse_result.char_count,
        tables=parse_result.table_count,
        correlation_id=correlation_id,
    )
    logger.info(
        "parsed_text_ready_for_lightrag",
        file=file_path.name,
        parser=parse_result.parser_used,
        chars=parse_result.char_count,
        lines=len(parse_result.text.splitlines()),
        preview=parse_result.text[:2000],
        correlation_id=correlation_id,
    )
    return await _ingest_text_with_duplicate_retry(
        lightrag_client=lightrag_client,
        text=parse_result.text,
        file_source=nas_file.nas_path,
        metadata={
            **metadata,
            "parser": parse_result.parser_used,
            "char_count": parse_result.char_count,
            "table_count": parse_result.table_count,
        },
        correlation_id=correlation_id,
    )


async def _ingest_text_with_duplicate_retry(
    lightrag_client: LightRAGIngestClient,
    text: str,
    file_source: str,
    metadata: dict,
    correlation_id: str,
) -> dict:
    try:
        return await lightrag_client.ingest_text(
            text=text,
            file_source=file_source,
            metadata=metadata,
            correlation_id=correlation_id,
        )
    except LightRAGError as exc:
        if exc.status_code != 409:
            raise
        doc_id = _compute_lightrag_doc_id(text)
        logger.warning(
            "lightrag_duplicate_detected",
            file_source=file_source,
            doc_id=doc_id,
            correlation_id=correlation_id,
        )
        # LightRAG đã có tài liệu cùng nội dung rồi; coi đây là ingest thành công
        # thay vì cố xóa bằng doc_id đoán mò và làm fail luồng mới.
        return {
            "id": doc_id,
            "status": "duplicate",
            "duplicate": True,
            "metadata": metadata,
        }


async def _ingest_native_with_duplicate_retry(
    lightrag_client: LightRAGIngestClient,
    file_path: str,
    metadata: dict,
    correlation_id: str,
) -> dict:
    try:
        return await lightrag_client.ingest_document(
            file_path=file_path,
            metadata=metadata,
            correlation_id=correlation_id,
        )
    except LightRAGError as exc:
        if exc.status_code != 409:
            raise
        logger.warning(
            "lightrag_duplicate_detected_native",
            file_path=file_path,
            correlation_id=correlation_id,
        )
        return {
            "status": "duplicate",
            "duplicate": True,
            "metadata": metadata,
        }
