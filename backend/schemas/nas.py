from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, field_validator


class NasFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str | UUID
    nas_path: str
    folder_type: str
    status: str
    file_hash: str | None = None
    lightrag_doc_id: str | None = None
    approved_by: str | UUID | None = None
    reject_reason: str | None = None
    created_at: datetime
    indexed_at: datetime | None = None


class NasReportRequest(BaseModel):
    event: str
    nas_path: str
    file_hash: str | None = None
    extension: str | None = None
    ingest_content: bool = True

    @field_validator("event")
    @classmethod
    def validate_event(cls, value: str) -> str:
        if value not in {"new", "changed", "deleted"}:
            raise ValueError("event must be one of: new, changed, deleted")
        return value


class ApproveRequest(BaseModel):
    approve: bool
    reject_reason: str | None = None


class FolderRequest(BaseModel):
    path: str
    folder_type: str
    is_active: bool = True

    @field_validator("folder_type")
    @classmethod
    def validate_folder_type(cls, value: str) -> str:
        if value not in {"auto", "manual"}:
            raise ValueError("folder_type must be one of: auto, manual")
        return value


class FolderUpdateRequest(BaseModel):
    folder_type: str | None = None
    is_active: bool | None = None

    @field_validator("folder_type")
    @classmethod
    def validate_folder_type(cls, value: str | None) -> str | None:
        if value is not None and value not in {"auto", "manual"}:
            raise ValueError("folder_type must be one of: auto, manual")
        return value


class NasFolderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str | UUID
    path: str
    folder_type: str
    is_active: bool
    last_scanned: datetime | None = None
    created_at: datetime


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str | UUID
    nas_path: str
    folder_type: str
    status: str
    file_hash: str | None = None
    lightrag_doc_id: str | None = None
    indexed_at: datetime | None = None
    created_at: datetime
    error_msg: str | None = None
    chunk_count: int | None = None


class DocumentCompareChunk(BaseModel):
    chunk_order_index: int | None = None
    tokens: int | None = None
    content: str | None = None


class DocumentCompareSection(BaseModel):
    success: bool
    parser_used: str | None = None
    char_count: int
    line_count: int
    text: str


class DocumentCompareChunks(BaseModel):
    count: int
    char_count: int
    line_count: int
    text: str
    items: list[DocumentCompareChunk]
    error: str | None = None


class DocumentCompareResult(BaseModel):
    similarity_ratio: float
    first_diff_index: int | None = None
    parsed_window: str
    chunk_window: str
    diff_preview: str


class DocumentCompareResponse(BaseModel):
    file_id: str | UUID
    nas_path: str
    status: str
    folder_type: str
    lightrag_doc_id: str | None = None
    parsed: DocumentCompareSection
    chunks: DocumentCompareChunks
    compare: DocumentCompareResult
