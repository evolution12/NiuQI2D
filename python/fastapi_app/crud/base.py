from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..exceptions import ResourceNotFoundError
from ..models import Base

ModelT = TypeVar("ModelT", bound=Base)
CreateSchemaT = TypeVar("CreateSchemaT", bound=BaseModel)
UpdateSchemaT = TypeVar("UpdateSchemaT", bound=BaseModel)


class CRUDBase(Generic[ModelT, CreateSchemaT, UpdateSchemaT]):
    def __init__(self, model: type[ModelT], resource_name: str) -> None:
        self.model = model
        self.resource_name = resource_name

    async def create(self, session: AsyncSession, body: CreateSchemaT | dict[str, Any]) -> ModelT:
        data = body.model_dump(mode="json") if isinstance(body, BaseModel) else body
        db_obj = self.model(**data)
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def get(self, session: AsyncSession, item_id: str) -> ModelT:
        db_obj = await session.get(self.model, item_id)
        if db_obj is None:
            raise ResourceNotFoundError(f"{self.resource_name} {item_id} 不存在")
        return db_obj

    async def list(
        self,
        session: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        statement: Select[tuple[ModelT]] | None = None,
    ) -> tuple[list[ModelT], int]:
        stmt = statement if statement is not None else select(self.model)
        total_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
        total = await session.scalar(total_stmt)
        result = await session.execute(stmt.offset((page - 1) * page_size).limit(page_size))
        return list(result.scalars().all()), int(total or 0)

    async def update(
        self,
        session: AsyncSession,
        item_id: str,
        body: UpdateSchemaT | dict[str, Any],
    ) -> ModelT:
        db_obj = await self.get(session, item_id)
        data = (
            body.model_dump(mode="json", exclude_unset=True, exclude_none=True)
            if isinstance(body, BaseModel)
            else body
        )
        for key, value in data.items():
            setattr(db_obj, key, value)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def delete(self, session: AsyncSession, item_id: str) -> None:
        db_obj = await self.get(session, item_id)
        await session.delete(db_obj)
        await session.commit()
