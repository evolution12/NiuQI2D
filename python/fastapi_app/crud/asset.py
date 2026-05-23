from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Asset, AssetStatus, AssetType
from ..schemas import AssetCreateRequest, AssetUpdateRequest
from .base import CRUDBase


class AssetCRUD(CRUDBase[Asset, AssetCreateRequest, AssetUpdateRequest]):
    def __init__(self) -> None:
        super().__init__(Asset, "资产")

    async def list_by_project(
        self,
        session: AsyncSession,
        project_id: str,
        asset_type: AssetType | None = None,
        status: AssetStatus | None = None,
        tag: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Asset], int]:
        stmt = select(Asset).where(Asset.project_id == project_id)
        if asset_type is not None:
            stmt = stmt.where(Asset.asset_type == asset_type)
        if status is not None:
            stmt = stmt.where(Asset.status == status)
        if search:
            stmt = stmt.where(Asset.name.ilike(f"%{search}%"))
        if tag:
            stmt = stmt.where(Asset.tags.contains([tag]))
        stmt = stmt.order_by(Asset.created_at.desc())
        return await self.list(session, page=page, page_size=page_size, statement=stmt)
