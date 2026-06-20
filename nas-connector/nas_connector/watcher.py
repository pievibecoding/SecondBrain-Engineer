from pathlib import Path
import hashlib
from nas_connector.logger import logger

SUPPORTED_EXTENSIONS = {'.pdf', '.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt'}
METADATA_ONLY_EXTENSIONS = {'.dwg', '.dxf', '.png', '.jpg', '.jpeg', '.mp4', '.avi', '.step', '.stl'}


def compute_md5(file_path: Path) -> str:
    h = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


async def poll_once(mount_path: str, uploader) -> None:
    logger.info("Poll cycle started", mount_path=mount_path)
    count = 0
    root = Path(mount_path)
    scanned = set()
    for file_path in root.rglob('*'):
        if not file_path.is_file():
            continue
        ext = file_path.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS and ext not in METADATA_ONLY_EXTENSIONS:
            continue
        nas_path = str(file_path)
        ingest_content = ext in SUPPORTED_EXTENSIONS
        try:
            current_hash = compute_md5(file_path)
            stored_hash = await uploader.get_hash(nas_path)
            if stored_hash is None:
                await uploader.report_new(nas_path, current_hash, ext, ingest_content)
            elif stored_hash != current_hash:
                await uploader.report_changed(nas_path, current_hash)
            count += 1
            scanned.add(nas_path)
        except Exception as e:
            logger.error("File processing error", nas_path=nas_path, error=str(e))
            continue

    if hasattr(uploader, "get_known_paths"):
        try:
            known_paths = await uploader.get_known_paths()
            for known_path in known_paths:
                if known_path not in scanned:
                    await uploader.report_deleted(known_path)
        except Exception as e:
            logger.error("Deleted detection error", error=str(e))

    logger.info("Poll cycle done", files_processed=count)
