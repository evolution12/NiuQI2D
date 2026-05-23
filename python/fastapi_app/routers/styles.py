from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..crud.style import StyleCRUD
from ..database import get_session
from ..schemas import StyleProfileCreateRequest, StyleProfileResponse, StyleProfileUpdateRequest

router = APIRouter(prefix="/styles", tags=["styles"])
crud = StyleCRUD()


@router.get("", response_model=list[StyleProfileResponse])
async def list_styles(
    session: AsyncSession = Depends(get_session),
) -> list[StyleProfileResponse]:
    items, _ = await crud.list(session, page_size=100)
    return [StyleProfileResponse.model_validate(s) for s in items]


@router.get("/{style_id}", response_model=StyleProfileResponse)
async def get_style(
    style_id: str,
    session: AsyncSession = Depends(get_session),
) -> StyleProfileResponse:
    item = await crud.get(session, style_id)
    return StyleProfileResponse.model_validate(item)


@router.post("", response_model=StyleProfileResponse, status_code=201)
async def create_style(
    body: StyleProfileCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> StyleProfileResponse:
    item = await crud.create(session, body)
    return StyleProfileResponse.model_validate(item)


@router.put("/{style_id}", response_model=StyleProfileResponse)
async def update_style(
    style_id: str,
    body: StyleProfileUpdateRequest,
    session: AsyncSession = Depends(get_session),
) -> StyleProfileResponse:
    item = await crud.update(session, style_id, body)
    return StyleProfileResponse.model_validate(item)


@router.delete("/{style_id}", status_code=204)
async def delete_style(
    style_id: str,
    session: AsyncSession = Depends(get_session),
) -> None:
    await crud.delete(session, style_id)
