from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..models import ExportRecord
from ..schemas import ExportRecordResponse, ExportRequest, ExportResponse
from ..services.export_service import ExportService

router = APIRouter(prefix="/export", tags=["export"])


@router.post("", response_model=ExportResponse, status_code=status.HTTP_201_CREATED)
async def create_export(
    body: ExportRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> ExportResponse:
    return await ExportService(session, request.app.state.storage).export_assets(body)


@router.get("/history", response_model=list[ExportRecordResponse])
async def list_export_history(
    request: Request,
    project_id: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[ExportRecord]:
    return await ExportService(session, request.app.state.storage).list_history(project_id)


@router.get("/{export_id}", response_model=ExportRecordResponse)
async def get_export_record(
    export_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> ExportRecord:
    return await ExportService(session, request.app.state.storage).get_record(export_id)
