from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_session
from backend.dependencies.auth import require_admin
from backend.dependencies.services import get_lightrag_query_client
from backend.integrations.lightrag.query import LightRAGQueryClient
from backend.logger import get_correlation_id
from backend.schemas.auth import UserResponse
from backend.schemas.diagnostics import DiagnosticRequest, DiagnosticResponse
from backend.services.diagnostics_service import run_diagnostic

router = APIRouter()


@router.get("")
async def diagnostics_health(current_user: UserResponse = Depends(require_admin)) -> dict:
    return {"ok": True, "feature": "retrieval-diagnostics"}


@router.post("", response_model=DiagnosticResponse)
async def create_diagnostic(
    payload: DiagnosticRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
    current_user: UserResponse = Depends(require_admin),
    lightrag: LightRAGQueryClient = Depends(get_lightrag_query_client),
) -> DiagnosticResponse:
    correlation_id = request.headers.get("X-Correlation-ID") or get_correlation_id()
    report = await run_diagnostic(db, payload, lightrag, correlation_id)
    return DiagnosticResponse.model_validate(report)
