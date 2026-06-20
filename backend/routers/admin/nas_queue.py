from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_session
from backend.dependencies.auth import require_admin
from backend.dependencies.services import get_lightrag_ingest_client
from backend.integrations.lightrag.ingest import LightRAGIngestClient
from backend.logger import get_correlation_id
from backend.models.nas_file import NasFile
from backend.schemas.auth import UserResponse
from backend.schemas.nas import ApproveRequest, NasFileResponse
from backend.services.ingestion_service import ingest_nas_file

router = APIRouter()


@router.get("", response_model=list[NasFileResponse])
async def list_queue(
    db: AsyncSession = Depends(get_session),
    current_user: UserResponse = Depends(require_admin),
) -> list[NasFileResponse]:
    result = await db.execute(
        select(NasFile).where(NasFile.status == "pending_review").order_by(NasFile.created_at.desc())
    )
    return [NasFileResponse.model_validate(item) for item in result.scalars().all()]


@router.post("/{file_id}/action", response_model=NasFileResponse)
async def action_on_file(
    file_id: str,
    body: ApproveRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
    current_user: UserResponse = Depends(require_admin),
    lightrag_client: LightRAGIngestClient = Depends(get_lightrag_ingest_client),
) -> NasFileResponse:
    result = await db.execute(select(NasFile).where(NasFile.id == file_id))
    nas_file = result.scalar_one_or_none()
    if nas_file is None:
        raise HTTPException(status_code=404, detail=f"NasFile not found: {file_id}")
    if nas_file.status != "pending_review":
        raise HTTPException(status_code=409, detail="File is not in pending_review status")
    if body.approve:
        nas_file.status = "queued"
        nas_file.approved_by = current_user.id
        nas_file.approved_at = datetime.utcnow()
        await db.flush()
        nas_file = await ingest_nas_file(
            db,
            file_id,
            lightrag_client,
            request.headers.get("X-Correlation-ID") or get_correlation_id(),
        )
    else:
        if not body.reject_reason:
            raise HTTPException(status_code=422, detail="reject_reason is required when rejecting")
        nas_file.status = "rejected"
        nas_file.reject_reason = body.reject_reason
    await db.flush()
    return NasFileResponse.model_validate(nas_file)
