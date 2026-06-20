from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_session
from backend.dependencies.auth import require_admin
from backend.dependencies.services import get_lightrag_ingest_client
from backend.integrations.lightrag.ingest import LightRAGIngestClient
from backend.models.nas_folder import NasFolder
from backend.schemas.auth import UserResponse
from backend.schemas.nas import FolderRequest, FolderUpdateRequest, NasFolderResponse
from backend.schemas.nas_scan import NasFolderScanResponse
from backend.services.nas_scan_service import scan_nas_folder

router = APIRouter()


@router.get("", response_model=list[NasFolderResponse])
async def list_folders(
    db: AsyncSession = Depends(get_session),
    current_user: UserResponse = Depends(require_admin),
) -> list[NasFolderResponse]:
    result = await db.execute(select(NasFolder).order_by(NasFolder.path))
    return [NasFolderResponse.model_validate(item) for item in result.scalars().all()]


@router.post("", response_model=NasFolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(
    body: FolderRequest,
    db: AsyncSession = Depends(get_session),
    current_user: UserResponse = Depends(require_admin),
) -> NasFolderResponse:
    result = await db.execute(select(NasFolder).where(NasFolder.path == body.path))
    existing = result.scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Folder path already configured")
    folder = NasFolder(path=body.path, folder_type=body.folder_type, is_active=body.is_active)
    db.add(folder)
    await db.flush()
    return NasFolderResponse.model_validate(folder)


@router.patch("/{folder_id}", response_model=NasFolderResponse)
async def update_folder(
    folder_id: str,
    body: FolderUpdateRequest,
    db: AsyncSession = Depends(get_session),
    current_user: UserResponse = Depends(require_admin),
) -> NasFolderResponse:
    result = await db.execute(select(NasFolder).where(NasFolder.id == folder_id))
    folder = result.scalar_one_or_none()
    if folder is None:
        raise HTTPException(status_code=404, detail="Folder not found")
    if body.folder_type is not None:
        folder.folder_type = body.folder_type
    if body.is_active is not None:
        folder.is_active = body.is_active
    await db.flush()
    return NasFolderResponse.model_validate(folder)


@router.delete("/{folder_id}")
async def delete_folder(
    folder_id: str,
    db: AsyncSession = Depends(get_session),
    current_user: UserResponse = Depends(require_admin),
) -> dict:
    result = await db.execute(select(NasFolder).where(NasFolder.id == folder_id))
    folder = result.scalar_one_or_none()
    if folder is None:
        raise HTTPException(status_code=404, detail="Folder not found")
    await db.delete(folder)
    return {"ok": True}


@router.post("/{folder_id}/scan", response_model=NasFolderScanResponse)
async def scan_folder(
    folder_id: str,
    request: Request,
    db: AsyncSession = Depends(get_session),
    current_user: UserResponse = Depends(require_admin),
    lightrag_client: LightRAGIngestClient = Depends(get_lightrag_ingest_client),
) -> NasFolderScanResponse:
    result = await db.execute(select(NasFolder).where(NasFolder.id == folder_id))
    folder = result.scalar_one_or_none()
    if folder is None:
        raise HTTPException(status_code=404, detail="Folder not found")
    return await scan_nas_folder(
        db,
        folder,
        lightrag_client,
        request.headers.get("X-Correlation-ID"),
    )
