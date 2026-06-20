from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


Recommendation = Literal["recommended", "not_recommended", "inconclusive"]


class AdaptiveChunkingReportSummary(BaseModel):
    id: str
    title: str
    created_at: str | None = None
    recommendation: Recommendation | str
    document_count: int
    path: str


class AdaptiveChunkingReportList(BaseModel):
    reports: list[AdaptiveChunkingReportSummary]


class AdaptiveChunkingReportDetail(BaseModel):
    id: str
    title: str
    created_at: str | None = None
    summary: dict[str, Any]
    documents: list[dict[str, Any]]
    markdown: str | None = None
    raw: dict[str, Any]


class AdaptiveChunkingRunDocument(BaseModel):
    document_id: str | None = None
    source_path: str


class AdaptiveChunkingRunRequest(BaseModel):
    run_id: str | None = None
    title: str | None = None
    documents: list[AdaptiveChunkingRunDocument] = Field(min_length=1)
    candidate_terms: dict[str, list[str]]
    expected_terms: list[str] = Field(default_factory=list)
    noise_terms: list[str] = Field(default_factory=list)
    target_chars: int = Field(default=2200, ge=300, le=20000)
    overlap_chars: int = Field(default=220, ge=0, le=5000)
    max_chars: int = Field(default=4200, ge=500, le=30000)
