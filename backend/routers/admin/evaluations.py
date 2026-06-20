from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.dependencies.auth import require_admin
from backend.schemas.evaluations import (
    AdaptiveChunkingReportDetail,
    AdaptiveChunkingReportList,
    AdaptiveChunkingRunRequest,
)
from backend.schemas.parser_evaluations import (
    ParserComparisonReportDetail,
    ParserComparisonReportList,
    ParserComparisonRunRequest,
)
from backend.services.adaptive_chunking_evaluation_service import run_adaptive_chunking_evaluation
from backend.services.evaluation_report_service import (
    get_adaptive_chunking_report,
    list_adaptive_chunking_reports,
)
from backend.services.parser_comparison_service import (
    get_pdf_parser_comparison_report,
    list_pdf_parser_comparison_reports,
    run_pdf_parser_comparison,
)

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/adaptive-chunking", response_model=AdaptiveChunkingReportList)
async def list_adaptive_chunking_evaluations() -> AdaptiveChunkingReportList:
    return AdaptiveChunkingReportList(reports=list_adaptive_chunking_reports())


@router.get("/adaptive-chunking/{report_id}", response_model=AdaptiveChunkingReportDetail)
async def get_adaptive_chunking_evaluation(report_id: str) -> AdaptiveChunkingReportDetail:
    report = get_adaptive_chunking_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Evaluation report not found")
    return AdaptiveChunkingReportDetail(**report)


@router.post("/adaptive-chunking/run", response_model=AdaptiveChunkingReportDetail)
async def run_adaptive_chunking_evaluation_endpoint(
    payload: AdaptiveChunkingRunRequest,
) -> AdaptiveChunkingReportDetail:
    try:
        report = run_adaptive_chunking_evaluation(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return AdaptiveChunkingReportDetail(**report)


@router.get("/pdf-parser-comparison", response_model=ParserComparisonReportList)
async def list_pdf_parser_comparison_evaluations() -> ParserComparisonReportList:
    return ParserComparisonReportList(reports=list_pdf_parser_comparison_reports())


@router.get("/pdf-parser-comparison/{report_id}", response_model=ParserComparisonReportDetail)
async def get_pdf_parser_comparison_evaluation(report_id: str) -> ParserComparisonReportDetail:
    report = get_pdf_parser_comparison_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Parser comparison report not found")
    return ParserComparisonReportDetail(**report)


@router.post("/pdf-parser-comparison/run", response_model=ParserComparisonReportDetail)
async def run_pdf_parser_comparison_endpoint(
    payload: ParserComparisonRunRequest,
) -> ParserComparisonReportDetail:
    try:
        report = run_pdf_parser_comparison(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return ParserComparisonReportDetail(**report)
