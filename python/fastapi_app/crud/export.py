from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import ExportRecord
from ..schemas import ExportRecordCreateRequest, ExportRecordUpdateRequest
from .base import CRUDBase


class ExportCRUD(CRUDBase[ExportRecord, ExportRecordCreateRequest, ExportRecordUpdateRequest]):
    def __init__(self) -> None:
        super().__init__(ExportRecord, "导出记录")

    async def create(
        self,
        session: AsyncSession,
        body: ExportRecordCreateRequest | dict[str, Any],
    ) -> ExportRecord:
        data = body.model_dump(mode="json") if isinstance(body, ExportRecordCreateRequest) else body
        if "metadata" in data:
            data["export_metadata"] = data.pop("metadata")
        return await super().create(session, data)

    async def update(
        self,
        session: AsyncSession,
        item_id: str,
        body: ExportRecordUpdateRequest | dict[str, Any],
    ) -> ExportRecord:
        data = (
            body.model_dump(mode="json", exclude_unset=True, exclude_none=True)
            if isinstance(body, ExportRecordUpdateRequest)
            else body
        )
        if "metadata" in data:
            data["export_metadata"] = data.pop("metadata")
        return await super().update(session, item_id, data)
