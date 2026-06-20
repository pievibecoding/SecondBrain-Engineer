from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.integrations.lightrag.errors import LightRAGError, LightRAGTimeoutError
from backend.integrations.lightrag.ingest import LightRAGIngestClient
from backend.logger import get_correlation_id
from backend.models.nas_file import NasFile
from backend.models.nas_folder import NasFolder
from backend.schemas.nas import NasFolderResponse
from backend.schemas.nas_scan import NasFolderScanResponse
from backend.services.ingestion_service import ingest_nas_file

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt"}
METADATA_ONLY_EXTENSIONS = {".dwg", ".dxf", ".png", ".jpg", ".jpeg", ".mp4", ".avi", ".step", ".stl"}


def compute_md5(file_path: Path) -> str:
    import hashlib

    digest = hashlib.md5()
    with open(file_path, "rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_supported(file_path: Path) -> bool:
    return file_path.suffix.lower() in SUPPORTED_EXTENSIONS.union(METADATA_ONLY_EXTENSIONS)


def _folder_prefix(folder_path: str) -> str:
    return folder_path.rstrip("/")


def _is_under_folder(path: str, folder_path: str) -> bool:
    prefix = _folder_prefix(folder_path)
    return path == prefix or path.startswith(f"{prefix}/")


async def _get_existing_files(db: AsyncSession, folder_path: str) -> list[NasFile]:
    result = await db.execute(select(NasFile).where(NasFile.nas_path.like(f"{_folder_prefix(folder_path)}/%")))
    return list(result.scalars().all())


async def scan_nas_folder(
    db: AsyncSession,
    folder: NasFolder,
    lightrag_client: LightRAGIngestClient,
    correlation_id: str | None = None,
) -> NasFolderScanResponse:
    root = Path(folder.path)
    if not root.exists() or not root.is_dir():
        raise HTTPException(status_code=404, detail=f"Folder path not found on filesystem: {folder.path}")

    cid = correlation_id or get_correlation_id()
    existing_files = await _get_existing_files(db, folder.path)
    existing_by_path = {item.nas_path: item for item in existing_files}
    scanned_paths: set[str] = set()

    new_count = 0
    updated_count = 0
    deleted_count = 0
    queued_count = 0
    ingested_count = 0
    errors: list[str] = []

    for file_path in root.rglob("*"):
        if not file_path.is_file() or not _is_supported(file_path):
            continue

        nas_path = str(file_path)
        scanned_paths.add(nas_path)
        current_hash = compute_md5(file_path)
        nas_file = existing_by_path.get(nas_path)
        is_new = nas_file is None
        should_refresh = is_new or nas_file.file_hash != current_hash or nas_file.status in {"rejected", "failed"}

        if is_new:
            nas_file = NasFile(
                nas_path=nas_path,
                folder_type=folder.folder_type,
                file_hash=current_hash,
                status="queued" if folder.folder_type == "auto" else "pending_review",
            )
            db.add(nas_file)
            await db.flush()
            new_count += 1
        elif should_refresh:
            nas_file.file_hash = current_hash
            nas_file.folder_type = folder.folder_type
            nas_file.reject_reason = None
            nas_file.error_msg = None
            if folder.folder_type == "auto":
                nas_file.status = "queued"
            else:
                nas_file.status = "pending_review"
            await db.flush()
            updated_count += 1

        if should_refresh:
            if folder.folder_type == "auto":
                queued_count += 1
                try:
                    updated_file = await ingest_nas_file(db, str(nas_file.id), lightrag_client, cid)
                    if updated_file.status == "indexed":
                        ingested_count += 1
                    else:
                        errors.append(f"{nas_path}: {updated_file.error_msg or 'Ingest failed'}")
                except (LightRAGTimeoutError, LightRAGError, HTTPException) as exc:
                    errors.append(f"{nas_path}: {exc}")
            else:
                queued_count += 1

    for nas_file in existing_files:
        if _is_under_folder(nas_file.nas_path, folder.path) and nas_file.nas_path not in scanned_paths and nas_file.status != "rejected":
            nas_file.status = "rejected"
            nas_file.reject_reason = "File deleted from NAS"
            nas_file.error_msg = None
            deleted_count += 1
            await db.flush()

    folder.last_scanned = datetime.utcnow()
    await db.flush()

    refreshed_folder = NasFolderResponse.model_validate(folder)
    return NasFolderScanResponse(
        folder=refreshed_folder,
        scanned_count=len(scanned_paths),
        new_count=new_count,
        updated_count=updated_count,
        deleted_count=deleted_count,
        queued_count=queued_count,
        ingested_count=ingested_count,
        error_count=len(errors),
        last_scanned=folder.last_scanned,
        errors=errors,
    )
