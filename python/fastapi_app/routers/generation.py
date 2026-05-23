from __future__ import annotations

import io
import logging

from fastapi import APIRouter, Depends, Request
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..crud.asset import AssetCRUD
from ..crud.generation import GenerationCRUD
from ..crud.project import ProjectCRUD
from ..crud.style import StyleCRUD
from ..database import get_session
from ..exceptions import InvalidParamError
from ..models import AssetStatus, AssetType, GenerationRecord, new_id
from ..providers.base import GenerationMode
from ..schemas import (
    AssetCreateRequest,
    AssetResponse,
    GenerateRequest,
    GenerateResponse,
    GenerationRecordDetailResponse,
    PostProcessLog,
    SelectRecordRequest,
    SelectRecordResponse,
)
from ..services.image_generator import ImageGenerator
from ..services.postprocess import PostProcessContext, PostProcessPipeline
from ..services.prompt_optimizer import PromptOptimizer
from ..storage import StorageManager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["generation"])
generation_crud = GenerationCRUD()
project_crud = ProjectCRUD()
style_crud = StyleCRUD()
asset_crud = AssetCRUD()


def _get_storage(request: Request) -> StorageManager:
    return request.app.state.storage


async def _build_image_url(project_id: str, record_id: str, processed: bool = False) -> str:
    folder = "processed" if processed else "raw"
    return f"/images/{project_id}/{folder}/{record_id}.png"


def _record_to_detail(record: GenerationRecord, image_url: str) -> GenerationRecordDetailResponse:
    pp_logs = [PostProcessLog(**log) for log in (record.postprocess_log or [])]
    return GenerationRecordDetailResponse(
        id=record.id,
        image_url=image_url,
        user_prompt=record.user_prompt,
        optimized_prompt=record.optimized_prompt,
        style_id=record.style_id,
        asset_type=record.asset_type,
        asset_subtype=record.asset_subtype,
        api_provider=record.api_provider,
        api_model=record.api_model,
        seed=record.seed,
        postprocess_log=pp_logs,
        created_at=record.created_at,
    )


@router.post("/generate", response_model=GenerateResponse)
async def generate(
    body: GenerateRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> GenerateResponse:
    return await _run_generation(body, request, session, mode=GenerationMode.QUALITY)


@router.post("/generate/preview", response_model=GenerateResponse)
async def generate_preview(
    body: GenerateRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> GenerateResponse:
    return await _run_generation(body, request, session, mode=GenerationMode.PREVIEW)


async def _run_generation(
    body: GenerateRequest,
    request: Request,
    session: AsyncSession,
    mode: GenerationMode,
) -> GenerateResponse:
    storage = _get_storage(request)
    settings = get_settings()

    # 1. Resolve style
    style = None
    if body.style_id:
        style = await style_crud.get(session, body.style_id)
    else:
        project = await project_crud.get(session, body.project_id)
        if project.style_id:
            style = await style_crud.get(session, project.style_id)

    style_id = style.id if style else None

    # 2. Optimize prompt
    optimizer = PromptOptimizer(
        api_provider=settings.text_api_provider,
        api_key=settings.text_api_key,
        api_model=settings.text_api_model,
    )
    optimized = await optimizer.optimize(
        user_prompt=body.user_prompt,
        asset_type=body.asset_type,
        asset_subtype=body.asset_subtype,
        style=style,
        reference_style_description=body.reference_style_description,
        actions=body.actions,
        direction_count=body.direction_count,
        frame_count=body.frame_count,
    )

    # 3. Generate images
    generator = ImageGenerator(session=session, storage=storage, settings=settings)
    result = await generator.generate_candidates(
        project_id=body.project_id,
        user_prompt=body.user_prompt,
        optimized_prompt=optimized.prompt,
        style_id=style_id,
        asset_type=body.asset_type,
        asset_subtype=body.asset_subtype,
        mode=mode,
        transparent_background=body.transparent_background,
    )

    # 4. Post-process each candidate
    pipeline = PostProcessPipeline()
    detail_records: list[GenerationRecordDetailResponse] = []

    for stored in result.records:
        raw_bytes = await storage.get_image(stored.image_path)
        image = Image.open(io.BytesIO(raw_bytes)).convert("RGBA")

        ctx = PostProcessContext(
            image=image,
            asset_type=body.asset_type,
            asset_subtype=body.asset_subtype,
            style=style,
            api_had_transparent_bg=body.transparent_background,
            target_size=body.target_size,
        )

        if (
            body.asset_type == AssetType.CHARACTER
            and body.asset_subtype == "animated_spritesheet"
        ):
            ctx.sheet_rows = body.direction_count
            ctx.sheet_cols = body.frame_count

        ctx = await pipeline.run(ctx)

        # Save post-processed image
        processed_image = ctx.image
        buf = io.BytesIO()
        processed_image.save(buf, format="PNG")
        processed_bytes = buf.getvalue()
        processed_path = await storage.save_processed_image(
            body.project_id, stored.record_id, processed_bytes,
        )

        # Update record with postprocess log and processed image path
        pp_log_dicts = [
            {"step": log.step, "executed": log.executed, "params": log.params, "duration_ms": log.duration_ms}
            for log in ctx.log
        ]
        current_record = await generation_crud.get(session, stored.record_id)
        await generation_crud.update(
            session,
            stored.record_id,
            {
                "postprocess_log": pp_log_dicts,
                "api_params": {
                    **(current_record.api_params or {}),
                    "processed_image_path": processed_path,
                },
            },
        )

        image_url = await _build_image_url(body.project_id, stored.record_id, processed=True)
        record = await generation_crud.get(session, stored.record_id)
        detail_records.append(_record_to_detail(record, image_url))

    logger.info(
        "Generated %d candidates for project %s (mode=%s, type=%s)",
        len(detail_records),
        body.project_id,
        mode.value,
        body.asset_type.value,
    )

    return GenerateResponse(records=detail_records, optimized_prompt=optimized.prompt)


@router.get("/generation/{record_id}", response_model=GenerationRecordDetailResponse)
async def get_generation_record(
    record_id: str,
    session: AsyncSession = Depends(get_session),
) -> GenerationRecordDetailResponse:
    record = await generation_crud.get(session, record_id)
    image_url = await _build_image_url(record.project_id, record_id)
    return _record_to_detail(record, image_url)


@router.get("/generation", response_model=list[GenerationRecordDetailResponse])
async def list_generation_records(
    project_id: str,
    page: int = 1,
    page_size: int = 20,
    session: AsyncSession = Depends(get_session),
) -> list[GenerationRecordDetailResponse]:
    records, _ = await generation_crud.list_by_project(
        session, project_id=project_id, page=page, page_size=page_size,
    )
    results: list[GenerationRecordDetailResponse] = []
    for record in records:
        image_url = await _build_image_url(project_id, record.id)
        results.append(_record_to_detail(record, image_url))
    return results


@router.post("/generation/{record_id}/select", response_model=SelectRecordResponse)
async def select_generation_record(
    record_id: str,
    body: SelectRecordRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> SelectRecordResponse:
    storage = _get_storage(request)
    record = await generation_crud.get(session, record_id)
    style = await style_crud.get(session, record.style_id) if record.style_id else None

    if record.asset_id:
        raise InvalidParamError("该生成记录已被选中为资产")

    project_id = record.project_id

    # Get the raw image
    raw_path = (record.api_params or {}).get("raw_image_path", "")
    if not raw_path:
        raise InvalidParamError("生成记录缺少原始图片路径")
    raw_image_bytes = await storage.get_image(raw_path)

    # Run post-processing
    image = Image.open(io.BytesIO(raw_image_bytes)).convert("RGBA")
    pipeline = PostProcessPipeline()
    ctx = PostProcessContext(
        image=image,
        asset_type=record.asset_type,
        asset_subtype=record.asset_subtype,
        style=style,
        api_had_transparent_bg=True,
        target_size=(16, 16),
    )
    ctx = await pipeline.run(ctx)

    # Save processed image
    output_image = ctx.image
    buf = io.BytesIO()
    output_image.save(buf, format="PNG")
    processed_bytes = buf.getvalue()

    asset_id = new_id()
    source_path = await storage.save_processed_image(project_id, asset_id, processed_bytes)
    thumbnail_path = await storage.generate_thumbnail(source_path, record.asset_type)

    # Create asset
    asset = await asset_crud.create(
        session,
        AssetCreateRequest(
            project_id=project_id,
            name=body.name,
            asset_type=record.asset_type,
            status=AssetStatus.SELECTED,
            source_path=source_path,
            thumbnail_path=thumbnail_path,
            tags=body.tags,
        ),
    )

    # Link generation record to asset
    await generation_crud.update(session, record_id, {"asset_id": asset.id})

    return SelectRecordResponse(asset=AssetResponse.model_validate(asset))
