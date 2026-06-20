from backend.logger import logger
from backend.models.nas_file import NasFile


def notify_admin(nas_file: NasFile) -> None:
    try:
        logger.info(
            "nas_pending_review",
            event="nas_pending_review",
            nas_path=nas_file.nas_path,
            nas_file_id=str(nas_file.id),
            folder_type=nas_file.folder_type,
        )
    except Exception:
        # Notification logging must not break NAS report processing.
        return None
