from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_session
from backend.dependencies.auth import require_admin
from backend.dependencies.services import get_lightrag_ingest_client
from backend.integrations.lightrag.errors import LightRAGError, LightRAGTimeoutError
from backend.integrations.lightrag.ingest import LightRAGIngestClient
from backend.logger import get_correlation_id
from backend.logger import logger
from backend.models.nas_file import NasFile
from backend.schemas.auth import UserResponse
from backend.schemas.nas import DocumentCompareResponse, DocumentResponse
from backend.services.ingestion_service import ingest_nas_file
from backend.services.document_debug_service import build_document_compare_report

router = APIRouter()


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    status: str | None = None,
    db: AsyncSession = Depends(get_session),
    current_user: UserResponse = Depends(require_admin),
) -> list[DocumentResponse]:
    statement = select(NasFile).order_by(NasFile.created_at.desc())
    if status is not None:
        statement = statement.where(NasFile.status == status)
    result = await db.execute(statement)
    return [DocumentResponse.model_validate(item) for item in result.scalars().all()]


@router.post("/{file_id}/reindex", response_model=DocumentResponse)
async def reindex_document(
    file_id: str,
    request: Request,
    db: AsyncSession = Depends(get_session),
    current_user: UserResponse = Depends(require_admin),
    lightrag_client: LightRAGIngestClient = Depends(get_lightrag_ingest_client),
) -> DocumentResponse:
    result = await db.execute(select(NasFile).where(NasFile.id == file_id))
    nas_file = result.scalar_one_or_none()
    if nas_file is None:
        raise HTTPException(status_code=404, detail=f"NasFile not found: {file_id}")

    nas_file.status = "queued"
    nas_file.error_msg = None
    await db.flush()

    correlation_id = request.headers.get("X-Correlation-ID") or get_correlation_id()
    updated = await ingest_nas_file(db, file_id, lightrag_client, correlation_id)
    return DocumentResponse.model_validate(updated)


@router.delete("/{file_id}")
async def delete_document(
    file_id: str,
    request: Request,
    db: AsyncSession = Depends(get_session),
    current_user: UserResponse = Depends(require_admin),
    lightrag_client: LightRAGIngestClient = Depends(get_lightrag_ingest_client),
) -> dict:
    result = await db.execute(select(NasFile).where(NasFile.id == file_id))
    nas_file = result.scalar_one_or_none()
    if nas_file is None:
        raise HTTPException(status_code=404, detail=f"NasFile not found: {file_id}")

    correlation_id = request.headers.get("X-Correlation-ID") or get_correlation_id()

    if nas_file.lightrag_doc_id:
        try:
            await lightrag_client.delete_document(
                nas_file.lightrag_doc_id,
                correlation_id,
            )
        except LightRAGTimeoutError as exc:
            raise HTTPException(status_code=504, detail=str(exc)) from exc
        except LightRAGError as exc:
            if exc.status_code == 404:
                logger.warning(
                    "lightrag_delete_missing_document",
                    nas_file_id=str(nas_file.id),
                    nas_path=nas_file.nas_path,
                    lightrag_doc_id=nas_file.lightrag_doc_id,
                    correlation_id=correlation_id,
                )
            else:
                raise HTTPException(status_code=502, detail=str(exc)) from exc

    await db.delete(nas_file)
    return {"ok": True}


@router.get("/{file_id}/compare", response_model=DocumentCompareResponse)
async def compare_document(
    file_id: str,
    request: Request,
    db: AsyncSession = Depends(get_session),
    current_user: UserResponse = Depends(require_admin),
) -> DocumentCompareResponse:
    result = await db.execute(select(NasFile).where(NasFile.id == file_id))
    nas_file = result.scalar_one_or_none()
    if nas_file is None:
        raise HTTPException(status_code=404, detail=f"NasFile not found: {file_id}")

    correlation_id = request.headers.get("X-Correlation-ID") or get_correlation_id()
    report = await build_document_compare_report(db, nas_file, correlation_id)
    return DocumentCompareResponse.model_validate(report)
