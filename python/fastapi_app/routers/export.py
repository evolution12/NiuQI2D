from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..crud.export import ExportCRUD
from ..crud.asset import AssetCRUD
from ..database import get_session
from ..models import Asset, ExportRecord
from ..schemas import (
    ExportRecordResponse,
    ExportRequest,
    ExportResponse,
)
from ..services.export_service import run_export
from ..storage import StorageManager

router = APIRouter(prefix="/export", tags=["export"])
export_crud = ExportCRUD()
asset_crud = AssetCRUD()


def _get_storage(request: Request) -> StorageManager:
    return request.app.state.storage


@router.post("", response_model=ExportResponse)
async def create_export(
    body: ExportRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> ExportResponse:
    storage = _get_storage(request)
    return await run_export(body, session, storage)


@router.get("/history", response_model=list[ExportRecordResponse])
async def list_export_history(
    project_id: str,
    page: int = 1,
    page_size: int = 20,
    session: AsyncSession = Depends(get_session),
) -> list[ExportRecordResponse]:
    # Get asset IDs for this project
    result = await session.execute(
        select(Asset.id).where(Asset.project_id == project_id)
    )
    project_asset_ids = {row[0] for row in result.fetchall()}

    if not project_asset_ids:
        return []

    # Get all export records and filter by asset overlap
    result = await session.execute(
        select(ExportRecord).order_by(ExportRecord.created_at.desc())
    )
    all_records = list(result.scalars().all())

    filtered = [
        r for r in all_records
        if any(aid in project_asset_ids for aid in r.asset_ids)
    ]

    # Paginate
    start = (page - 1) * page_size
    page_records = filtered[start:start + page_size]

    return [ExportRecordResponse.model_validate(r) for r in page_records]


@router.get("/{export_id}", response_model=ExportRecordResponse)
async def get_export(
    export_id: str,
    session: AsyncSession = Depends(get_session),
) -> ExportRecordResponse:
    record = await export_crud.get(session, export_id)
    return ExportRecordResponse.model_validate(record)
