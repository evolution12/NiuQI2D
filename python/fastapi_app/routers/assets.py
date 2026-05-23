from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..crud.asset import AssetCRUD
from ..database import get_session
from ..exceptions import InvalidParamError, ResourceNotFoundError
from ..models import Asset, AssetStatus, AssetType
from ..schemas import (
    AssetListResponse,
    AssetResponse,
    AssetUpdateRequest,
    AnimationResponse,
    TagsResponse,
)
from ..storage import StorageManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assets", tags=["assets"])
asset_crud = AssetCRUD()


def _asset_to_response(asset: Asset) -> AssetResponse:
    """Convert DB Asset to API response, prefixing image paths with /images/."""
    resp = AssetResponse.model_validate(asset)
    if resp.source_path and not resp.source_path.startswith("/"):
        resp.source_path = f"/images/{resp.source_path}"
    if resp.thumbnail_path and not resp.thumbnail_path.startswith("/"):
        resp.thumbnail_path = f"/images/{resp.thumbnail_path}"
    return resp


def _get_storage(request: Request) -> StorageManager:
    return request.app.state.storage


@router.get("", response_model=AssetListResponse)
async def list_assets(
    project_id: str,
    asset_type: AssetType | None = None,
    status: AssetStatus | None = None,
    tag: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    session: AsyncSession = Depends(get_session),
) -> AssetListResponse:
    assets, total = await asset_crud.list_by_project(
        session,
        project_id=project_id,
        asset_type=asset_type,
        status=status,
        tag=tag,
        search=search,
        page=page,
        page_size=page_size,
    )
    return AssetListResponse(
        items=[_asset_to_response(a) for a in assets],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/tags", response_model=TagsResponse)
async def list_tags(
    project_id: str,
    session: AsyncSession = Depends(get_session),
) -> TagsResponse:
    stmt = (
        select(Asset.tags)
        .where(Asset.project_id == project_id)
    )
    result = await session.execute(stmt)
    all_tags: set[str] = set()
    for row in result.fetchall():
        tags = row[0]
        if tags:
            all_tags.update(tags)
    return TagsResponse(tags=sorted(all_tags))


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: str,
    session: AsyncSession = Depends(get_session),
) -> AssetResponse:
    asset = await asset_crud.get(session, asset_id)
    return _asset_to_response(asset)


@router.put("/{asset_id}", response_model=AssetResponse)
async def update_asset(
    asset_id: str,
    body: AssetUpdateRequest,
    session: AsyncSession = Depends(get_session),
) -> AssetResponse:
    asset = await asset_crud.update(session, asset_id, body)
    return _asset_to_response(asset)


@router.delete("/{asset_id}", status_code=204)
async def delete_asset(
    asset_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> None:
    storage = _get_storage(request)
    asset = await asset_crud.get(session, asset_id)

    # Delete associated files
    for path_str in (asset.source_path, asset.thumbnail_path):
        if path_str:
            try:
                file_path = storage._resolve_image_path(path_str)
                if file_path.exists():
                    file_path.unlink()
            except Exception:
                logger.warning("Failed to delete file %s", path_str, exc_info=True)

    await asset_crud.delete(session, asset_id)


@router.post("/batch-delete", status_code=204)
async def batch_delete_assets(
    body: dict[str, list[str]],
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> None:
    ids = body.get("ids", [])
    if not ids:
        return

    storage = _get_storage(request)
    for asset_id in ids:
        try:
            asset = await asset_crud.get(session, asset_id)
            for path_str in (asset.source_path, asset.thumbnail_path):
                if path_str:
                    try:
                        file_path = storage._resolve_image_path(path_str)
                        if file_path.exists():
                            file_path.unlink()
                    except Exception:
                        logger.warning("Failed to delete file %s", path_str, exc_info=True)
            await asset_crud.delete(session, asset_id)
        except ResourceNotFoundError:
            logger.warning("Asset %s not found during batch delete", asset_id)


@router.get("/{asset_id}/animation", response_model=AnimationResponse)
async def get_animation(
    asset_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> AnimationResponse:
    storage = _get_storage(request)
    asset = await asset_crud.get(session, asset_id)

    if asset.asset_type != AssetType.CHARACTER:
        raise InvalidParamError("仅角色类资产支持动画预览")

    # Read the processed image and split into frames based on generation records
    from ..crud.generation import GenerationCRUD
    generation_crud = GenerationCRUD()

    # Get the generation record linked to this asset
    stmt = select(generation_crud.model).where(
        generation_crud.model.asset_id == asset_id
    )
    result = await session.execute(stmt)
    gen_record = result.scalar_one_or_none()

    if not gen_record:
        raise ResourceNotFoundError(f"资产 {asset_id} 没有关联的生成记录")

    # Load the source image
    source_bytes = await storage.get_image(asset.source_path)
    from PIL import Image
    import io

    source_image = Image.open(io.BytesIO(source_bytes)).convert("RGBA")

    # Determine frame layout from generation record params
    api_params = gen_record.api_params or {}
    subtype = gen_record.asset_subtype

    frames: list[str] = []

    if subtype == "animated_spritesheet":
        # Extract individual frames from spritesheet
        cols = api_params.get("frame_count", 3)
        rows = api_params.get("direction_count", 4)
        cell_w = source_image.width // cols if cols > 0 else source_image.width
        cell_h = source_image.height // rows if rows > 0 else source_image.height

        for row in range(rows):
            for col in range(cols):
                frame = source_image.crop(
                    (col * cell_w, row * cell_h, (col + 1) * cell_w, (row + 1) * cell_h)
                )
                frame_path = f"{asset.project_id}/processed/{asset_id}_frame_{row}_{col}.png"
                buf = io.BytesIO()
                frame.save(buf, format="PNG")
                await storage.save_processed_image(asset.project_id, f"{asset_id}_frame_{row}_{col}", buf.getvalue())
                frames.append(f"/images/{frame_path}")
    else:
        # Static image - single frame
        frames.append(f"/images/{asset.source_path}")

    return AnimationResponse(
        frames=frames,
        frame_count=len(frames),
        frame_delay_ms=100,
    )
