from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..crud.generation import GenerationCRUD
from ..database import get_session
from ..providers.base import GenerationMode
from ..schemas import (
    GenerateRequest,
    GenerateResponse,
    GenerationCandidateResponse,
    SelectRecordRequest,
    SelectRecordResponse,
    VariantRequest,
)
from ..services.generation_service import GenerationService

router = APIRouter(tags=["generation"])


@router.post("/generate", response_model=GenerateResponse, status_code=status.HTTP_201_CREATED)
async def generate_asset(
    body: GenerateRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> GenerateResponse:
    mode = GenerationMode.PREVIEW if body.preview_mode else GenerationMode.QUALITY
    return await GenerationService(session, request.app.state.storage).generate(body, mode)


@router.post("/generate/preview", response_model=GenerateResponse, status_code=status.HTTP_201_CREATED)
async def preview_asset(
    body: GenerateRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> GenerateResponse:
    return await GenerationService(session, request.app.state.storage).generate(
        body.model_copy(update={"preview_mode": True}),
        GenerationMode.PREVIEW,
    )


@router.get("/generation", response_model=list[GenerationCandidateResponse])
async def list_generation_records(
    request: Request,
    project_id: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> list[GenerationCandidateResponse]:
    records, _total = await GenerationService(session, request.app.state.storage).list_records(
        project_id,
        page,
        page_size,
    )
    return records


@router.get("/generation/{record_id}", response_model=GenerationCandidateResponse)
async def get_generation_record(
    record_id: str,
    session: AsyncSession = Depends(get_session),
) -> GenerationCandidateResponse:
    record = await GenerationCRUD().get(session, record_id)
    image_url = record.api_params.get("image_url")
    return GenerationCandidateResponse(
        id=record.id,
        project_id=record.project_id,
        asset_id=record.asset_id,
        image_url=image_url if isinstance(image_url, str) else None,
        user_prompt=record.user_prompt,
        optimized_prompt=record.optimized_prompt,
        style_id=record.style_id,
        asset_type=record.asset_type,
        asset_subtype=record.asset_subtype,
        api_provider=record.api_provider,
        api_model=record.api_model,
        api_params=record.api_params,
        seed=record.seed,
        reference_image_path=record.reference_image_path,
        postprocess_log=record.postprocess_log,
        created_at=record.created_at,
    )


@router.post("/generation/{record_id}/select", response_model=SelectRecordResponse)
async def select_generation_record(
    record_id: str,
    body: SelectRecordRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> SelectRecordResponse:
    return await GenerationService(session, request.app.state.storage).select_record(record_id, body)


@router.post("/generation/{record_id}/reproduce", response_model=GenerateResponse)
async def reproduce_generation_record(
    record_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> GenerateResponse:
    return await GenerationService(session, request.app.state.storage).reproduce(record_id)


@router.post("/generation/{record_id}/variant", response_model=GenerateResponse)
async def variant_generation_record(
    record_id: str,
    body: VariantRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> GenerateResponse:
    return await GenerationService(session, request.app.state.storage).variant(record_id, body)
