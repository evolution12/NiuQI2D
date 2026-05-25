from __future__ import annotations

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..crud.style import StyleCRUD
from ..database import get_session
from ..exceptions import InvalidParamError
from ..models import StyleProfile
from ..schemas import (
    ReferenceUploadResponse,
    StyleProfileCreateRequest,
    StyleProfileResponse,
    StyleProfileUpdateRequest,
)
from ..services.reference_analyzer import ReferenceAnalyzer
from ..services.style_service import StyleService

router = APIRouter(prefix="/styles", tags=["styles"])

style_crud = StyleCRUD()


def _compact_redundant_presets(items: list[StyleProfile]) -> list[StyleProfile]:
    """Collapse legacy preset variants such as pixel 16x16/32x32 into one style."""
    best_by_art_style: dict[str, StyleProfile] = {}

    for item in items:
        if not item.is_preset:
            continue
        art_style = getattr(item.art_style, "value", str(item.art_style))
        existing = best_by_art_style.get(art_style)
        is_canonical = item.name in {"像素风", "卡通风", "手绘风", "写实风", "自定义"}
        existing_is_canonical = (
            existing is not None
            and existing.name in {"像素风", "卡通风", "手绘风", "写实风", "自定义"}
        )
        if existing is None or (is_canonical and not existing_is_canonical):
            best_by_art_style[art_style] = item

    emitted: set[str] = set()
    compacted: list[StyleProfile] = []
    for item in items:
        if not item.is_preset:
            compacted.append(item)
            continue
        art_style = getattr(item.art_style, "value", str(item.art_style))
        if item.id != best_by_art_style.get(art_style, item).id or art_style in emitted:
            continue
        emitted.add(art_style)
        compacted.append(item)
    return compacted


@router.get("", response_model=list[StyleProfileResponse])
async def list_styles(
    include_presets: bool = True,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> list[StyleProfile]:
    stmt = select(StyleProfile).order_by(StyleProfile.is_preset.desc(), StyleProfile.created_at.desc())
    if not include_presets:
        stmt = stmt.where(StyleProfile.is_preset.is_(False))
    items, _ = await style_crud.list(session, page=page, page_size=page_size, statement=stmt)
    return _compact_redundant_presets(items) if include_presets else items


@router.post("", response_model=StyleProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_style(
    body: StyleProfileCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> StyleProfile:
    return await style_crud.create(session, body)


@router.get("/{style_id}", response_model=StyleProfileResponse)
async def get_style(style_id: str, session: AsyncSession = Depends(get_session)) -> StyleProfile:
    return await style_crud.get(session, style_id)


@router.put("/{style_id}", response_model=StyleProfileResponse)
async def update_style(
    style_id: str,
    body: StyleProfileUpdateRequest,
    session: AsyncSession = Depends(get_session),
) -> StyleProfile:
    return await style_crud.update(session, style_id, body)


@router.patch("/{style_id}", response_model=StyleProfileResponse)
async def patch_style(
    style_id: str,
    body: StyleProfileUpdateRequest,
    session: AsyncSession = Depends(get_session),
) -> StyleProfile:
    return await style_crud.update(session, style_id, body)


@router.delete("/{style_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_style(style_id: str, session: AsyncSession = Depends(get_session)) -> None:
    style = await style_crud.get(session, style_id)
    await StyleService(session).ensure_deletable(style)
    await style_crud.delete(session, style_id)


@router.post("/{style_id}/reference", response_model=ReferenceUploadResponse)
async def upload_reference(
    style_id: str,
    request: Request,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> ReferenceUploadResponse:
    style = await style_crud.get(session, style_id)
    content_type = file.content_type or ""
    if content_type not in {"image/png", "image/jpeg", "image/webp"}:
        raise InvalidParamError("参考图仅支持 png/jpg/webp")
    image_data = await file.read()
    if not image_data:
        raise InvalidParamError("参考图不能为空")

    reference_path = await request.app.state.storage.save_reference_image(style.id, image_data)
    absolute_path = request.app.state.storage._resolve_image_path(reference_path)
    settings = get_settings()
    description = await ReferenceAnalyzer(
        settings.text_api_provider,
        settings.text_api_key,
        settings.text_api_model,
    ).analyze_style(str(absolute_path))
    extra_params = {**(style.extra_params or {}), "reference_style_description": description}
    await style_crud.update(
        session,
        style.id,
        {"reference_image_path": reference_path, "extra_params": extra_params},
    )
    return ReferenceUploadResponse(reference_image_path=reference_path, style_description=description)


@router.delete("/{style_id}/reference", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reference(
    style_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> None:
    style = await style_crud.get(session, style_id)
    if style.reference_image_path:
        path = request.app.state.storage._resolve_image_path(style.reference_image_path)
        if path.exists() and path.is_file():
            path.unlink()
    extra_params = {**(style.extra_params or {})}
    extra_params.pop("reference_style_description", None)
    await style_crud.update(
        session,
        style.id,
        {"reference_image_path": None, "extra_params": extra_params or None},
    )
