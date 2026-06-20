from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.nas import NasFolderResponse


class NasFolderScanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    folder: NasFolderResponse
    scanned_count: int
    new_count: int
    updated_count: int
    deleted_count: int
    queued_count: int
    ingested_count: int
    error_count: int
    last_scanned: datetime
    errors: list[str] = Field(default_factory=list)
