from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_session
from backend.models.nas_file import NasFile
from backend.models.nas_folder import NasFolder
from backend.schemas.nas import NasReportRequest
from backend.services import nas_notify
from backend.logger import logger

router = APIRouter()


async def get_nas_file_by_path(db: AsyncSession, nas_path: str) -> NasFile | None:
    result = await db.execute(select(NasFile).where(NasFile.nas_path == nas_path))
    return result.scalar_one_or_none()


async def get_nas_file_by_id(db: AsyncSession, file_id: str) -> NasFile | None:
    result = await db.execute(select(NasFile).where(NasFile.id == file_id))
    return result.scalar_one_or_none()


async def find_folder_by_path(db: AsyncSession, nas_path: str) -> NasFolder | None:
    result = await db.execute(select(NasFolder).where(NasFolder.is_active == True))
    folders = result.scalars().all()
    matches = [folder for folder in folders if nas_path.startswith(folder.path)]
    if not matches:
        return None
    return max(matches, key=lambda folder: len(folder.path))


async def _create_nas_file(db: AsyncSession, payload: NasReportRequest) -> NasFile:
    folder = await find_folder_by_path(db, payload.nas_path)
    folder_type = folder.folder_type if folder else "auto"
    status = "queued" if folder_type == "auto" else "pending_review"
    nas_file = NasFile(
        nas_path=payload.nas_path,
        folder_type=folder_type,
        file_hash=payload.file_hash,
        status=status,
    )
    db.add(nas_file)
    await db.flush()
    if folder_type == "manual":
        nas_notify.notify_admin(nas_file)
    return nas_file


@router.get("/hash")
async def get_hash(path: str = Query(...), db: AsyncSession = Depends(get_session)) -> dict:
    nas_file = await get_nas_file_by_path(db, path)
    if nas_file is None:
        raise HTTPException(status_code=404, detail="NasFile not found")
    return {"path": nas_file.nas_path, "hash": nas_file.file_hash}


@router.get("/paths")
async def get_paths(db: AsyncSession = Depends(get_session)) -> dict:
    result = await db.execute(select(NasFile.nas_path).where(NasFile.status != "rejected"))
    return {"paths": list(result.scalars().all())}


@router.post("/report")
async def report_nas_event(payload: NasReportRequest, request: Request, db: AsyncSession = Depends(get_session)) -> dict:
    correlation_id = request.headers.get("X-Correlation-ID", "")
    logger.info("nas_event_received", nas_event=payload.event, nas_path=payload.nas_path, correlation_id=correlation_id)

    if payload.event == "new":
        existing = await get_nas_file_by_path(db, payload.nas_path)
        if existing is None:
            await _create_nas_file(db, payload)
        else:
            existing.file_hash = payload.file_hash
    elif payload.event == "changed":
        nas_file = await get_nas_file_by_path(db, payload.nas_path)
        if nas_file is None:
            await _create_nas_file(db, payload)
        else:
            nas_file.file_hash = payload.file_hash
            if nas_file.status == "indexed":
                nas_file.status = "queued"
    elif payload.event == "deleted":
        nas_file = await get_nas_file_by_path(db, payload.nas_path)
        if nas_file is not None:
            nas_file.status = "rejected"
            nas_file.reject_reason = "File deleted from NAS"

    return {"ok": True}
