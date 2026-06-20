from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ParserRunDocument(BaseModel):
    document_id: str | None = None
    source_path: str


class ParserComparisonRunRequest(BaseModel):
    run_id: str | None = None
    title: str | None = None
    documents: list[ParserRunDocument] = Field(min_length=1)
    parsers: list[str] = Field(default_factory=lambda: ["pdfplumber", "pymupdf"])
    semantic_anchors: list[str] = Field(default_factory=list)
    candidate_terms: dict[str, list[str]] = Field(default_factory=dict)
    expected_terms: list[str] = Field(default_factory=list)
    noise_terms: list[str] = Field(default_factory=list)
    target_chars: int = Field(default=2200, ge=300, le=20000)
    overlap_chars: int = Field(default=220, ge=0, le=5000)
    max_chars: int = Field(default=4200, ge=500, le=30000)


class ParserComparisonReportSummary(BaseModel):
    id: str
    title: str
    created_at: str | None = None
    recommendation: str
    recommended_parser: str | None = None
    document_count: int
    path: str


class ParserComparisonReportList(BaseModel):
    reports: list[ParserComparisonReportSummary]


class ParserComparisonReportDetail(BaseModel):
    id: str
    title: str
    created_at: str | None = None
    summary: dict[str, Any]
    documents: list[dict[str, Any]]
    markdown: str | None = None
    raw: dict[str, Any]
