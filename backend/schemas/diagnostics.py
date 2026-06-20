from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class DiagnosticRequest(BaseModel):
    query: str = Field(min_length=1)
    file_id: str | None = None
    folder_path: str | None = None
    expected_terms: list[str] = Field(default_factory=list)
    expected_source_paths: list[str] = Field(default_factory=list)


class DiagnosticDiagnosis(BaseModel):
    code: Literal["parse_failed", "chunk_failed", "retrieval_failed", "context_bad", "llm_bad", "api_failed", "ok"]
    reason: str
    next_action: str


class DiagnosticResponse(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    correlation_id: str
    query: str
    diagnosis: DiagnosticDiagnosis
    stages: dict[str, Any]
    raw_log: dict[str, Any]
