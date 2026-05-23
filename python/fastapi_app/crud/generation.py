from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import GenerationRecord
from ..schemas import GenerationRecordCreateRequest, GenerationRecordUpdateRequest
from .base import CRUDBase


class GenerationCRUD(
    CRUDBase[GenerationRecord, GenerationRecordCreateRequest, GenerationRecordUpdateRequest]
):
    def __init__(self) -> None:
        super().__init__(GenerationRecord, "生成记录")

    async def list_by_style(
        self,
        session: AsyncSession,
        style_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[GenerationRecord], int]:
        stmt = (
            select(GenerationRecord)
            .where(GenerationRecord.style_id == style_id)
            .order_by(GenerationRecord.created_at.desc())
        )
        return await self.list(session, page=page, page_size=page_size, statement=stmt)
