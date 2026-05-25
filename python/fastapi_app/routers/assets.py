from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..crud.asset import AssetCRUD
from ..crud.project import ProjectCRUD
from ..database import get_session
from ..exceptions import InvalidParamError
from ..models import Asset, AssetStatus, AssetType
from ..schemas import (
    AnimationResponse,
    AssetBatchDeleteRequest,
    AssetBatchDeleteResponse,
    AssetCreateRequest,
    AssetListResponse,
    AssetResponse,
    AssetUpdateRequest,
    TagsResponse,
)

router = APIRouter(prefix="/assets", tags=["assets"])
tags_router = APIRouter(prefix="/tags", tags=["assets"])

asset_crud = AssetCRUD()
project_crud = ProjectCRUD()


@router.get("", response_model=AssetListResponse)
async def list_assets(
    project_id: str,
    asset_type: AssetType | None = None,
    status_filter: AssetStatus | None = Query(default=None, alias="status"),
    tag: str | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> AssetListResponse:
    await project_crud.get(session, project_id)
    items, total = await asset_crud.list_by_project(
        session=session,
        project_id=project_id,
        asset_type=asset_type,
        status=status_filter,
        tag=tag,
        search=search,
        page=page,
        page_size=page_size,
    )
    return AssetListResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def create_asset(
    body: AssetCreateRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> Asset:
    await project_crud.get(session, body.project_id)
    thumbnail_path = body.thumbnail_path
    if thumbnail_path is None:
        thumbnail_path = await request.app.state.storage.generate_thumbnail(
            body.source_path,
            body.asset_type,
        )
    return await asset_crud.create(session, body.model_copy(update={"thumbnail_path": thumbnail_path}))


@router.post("/batch-delete", response_model=AssetBatchDeleteResponse)
async def batch_delete_assets(
    body: AssetBatchDeleteRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> AssetBatchDeleteResponse:
    deleted_ids: list[str] = []
    for asset_id in body.asset_ids:
        asset = await asset_crud.get(session, asset_id)
        await _delete_asset_files(request, asset)
        await asset_crud.delete(session, asset_id)
        deleted_ids.append(asset_id)
    return AssetBatchDeleteResponse(deleted_ids=deleted_ids)


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(asset_id: str, session: AsyncSession = Depends(get_session)) -> Asset:
    return await asset_crud.get(session, asset_id)


@router.put("/{asset_id}", response_model=AssetResponse)
async def update_asset(
    asset_id: str,
    body: AssetUpdateRequest,
    session: AsyncSession = Depends(get_session),
) -> Asset:
    return await asset_crud.update(session, asset_id, body)


@router.patch("/{asset_id}", response_model=AssetResponse)
async def patch_asset(
    asset_id: str,
    body: AssetUpdateRequest,
    session: AsyncSession = Depends(get_session),
) -> Asset:
    return await asset_crud.update(session, asset_id, body)


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    asset_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> None:
    asset = await asset_crud.get(session, asset_id)
    await _delete_asset_files(request, asset)
    await asset_crud.delete(session, asset_id)


@router.get("/{asset_id}/animation", response_model=AnimationResponse)
async def get_asset_animation(
    asset_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> AnimationResponse:
    asset = await asset_crud.get(session, asset_id)
    if asset.asset_type != AssetType.CHARACTER:
        raise InvalidParamError("仅角色资产支持动画预览")

    frames, actions, frame_delay_ms = _animation_frames_from_asset(request.app.state.storage, asset)
    return AnimationResponse(
        frames=frames,
        frame_count=len(frames),
        frame_delay_ms=frame_delay_ms,
        actions=actions or ({"default": list(range(len(frames)))} if frames else {}),
    )


@tags_router.get("", response_model=TagsResponse)
async def list_tags(
    project_id: str,
    session: AsyncSession = Depends(get_session),
) -> TagsResponse:
    await project_crud.get(session, project_id)
    result = await session.execute(select(Asset.tags).where(Asset.project_id == project_id))
    tags = sorted({tag for row in result.scalars().all() for tag in (row or [])})
    return TagsResponse(tags=tags)


async def _delete_asset_files(request: Request, asset: Asset) -> None:
    storage = request.app.state.storage
    for image_path in {asset.source_path, asset.thumbnail_path}:
        await asyncio.to_thread(_unlink_stored_image, storage, image_path)
    await asyncio.to_thread(_unlink_animation_dir, storage, asset.source_path)


def _unlink_stored_image(storage: object, image_path: str | None) -> None:
    if not image_path:
        return
    resolver = getattr(storage, "_resolve_image_path")
    path = resolver(image_path)
    if path.exists() and path.is_file():
        path.unlink()


def _unlink_animation_dir(storage: object, image_path: str | None) -> None:
    if not image_path:
        return
    resolver = getattr(storage, "_resolve_image_path")
    path = resolver(image_path)
    if path.name.startswith("frame_") and path.parent.exists():
        for child in path.parent.glob("frame_*.png"):
            child.unlink()
        for child in path.parent.glob("preview_*.png"):
            child.unlink()
        manifest = path.parent / "animation.json"
        if manifest.exists():
            manifest.unlink()
        try:
            path.parent.rmdir()
        except OSError:
            pass


def _animation_frames_from_asset(storage: object, asset: Asset) -> tuple[list[str], dict[str, list[int]], int]:
    source_path = asset.source_path
    if Path(source_path).suffix.lower() == ".json":
        return [], {}, 120

    manifest = _read_animation_manifest(storage, source_path)
    if manifest is not None:
        frames = manifest.get("frames") or manifest.get("preview_frames", [])
        actions = manifest.get("actions", {})
        frame_delay_ms = manifest.get("frame_delay_ms", 120)
        return (
            [f"/images/{frame}" for frame in frames if isinstance(frame, str)],
            actions if isinstance(actions, dict) else {},
            int(frame_delay_ms) if isinstance(frame_delay_ms, int) else 120,
        )

    return [f"/images/{source_path}"], {"default": [0]}, 120


def _read_animation_manifest(storage: object, source_path: str) -> dict[str, Any] | None:
    resolver = getattr(storage, "_resolve_image_path")
    path = resolver(source_path)
    manifest_path = path.parent / "animation.json"
    if not manifest_path.exists():
        return None
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None
