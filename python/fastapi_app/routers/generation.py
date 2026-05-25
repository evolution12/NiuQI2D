from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..crud.generation import GenerationCRUD
from ..database import get_session
from ..providers.base import GenerationMode
from ..schemas import (
    GenerateRequest,
    GenerateResponse,
    GenerationCandidateResponse,
    QualityPipelineBaseResponse,
    QualityPipelineDirectionRequest,
    QualityPipelineDirectionResponse,
    SelectRecordRequest,
    SelectRecordResponse,
    VariantRequest,
)
from ..services.generation_service import GenerationService
from ..crud.style import StyleCRUD
from ..services.quality_pipeline_service import QualityPipelineService

router = APIRouter(tags=["generation"])

_record_response = GenerationService.candidate_response


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
    return _record_response(record)


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


# --- Quality Pipeline endpoints ---

@router.post("/generate/quality-pipeline/base", response_model=QualityPipelineBaseResponse, status_code=status.HTTP_201_CREATED)
async def quality_pipeline_base(
    body: GenerateRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> QualityPipelineBaseResponse:
    """Step 1: Generate base character image candidates."""
    storage = request.app.state.storage
    style = None
    if body.style_id:
        style = await StyleCRUD().get(session, body.style_id)

    ref_desc = body.reference_style_description
    if not ref_desc and style and style.extra_params:
        ref_desc = style.extra_params.get("reference_style_description")

    service = QualityPipelineService(session, storage)
    result = await service.generate_base_candidates(
        project_id=body.project_id,
        user_prompt=body.user_prompt,
        style=style,
        style_id=body.style_id,
        reference_style_description=ref_desc,
        target_size=body.target_size,
        candidate_count=body.candidate_count or 2,
        seed=body.seed,
        reference_image_path=body.reference_image_path,
    )

    # Convert raw dicts to GenerationCandidateResponse
    records = []
    for r in result["records"]:
        record = await GenerationCRUD().get(session, r["id"])
        records.append(_record_response(record))

    return QualityPipelineBaseResponse(
        records=records,
        optimized_prompt=result["optimized_prompt"],
        pipeline_id=result["pipeline_id"],
    )


@router.post("/generate/quality-pipeline/directions")
async def quality_pipeline_directions(
    body: QualityPipelineDirectionRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Step 2+3: Stream per-direction progress, then final result."""
    service = QualityPipelineService(session, request.app.state.storage)

    async def event_stream():
        async for line in service.generate_directions_stream(
            base_record_id=body.base_record_id,
            direction_count=body.direction_count,
            frame_count=body.frame_count,
            actions=body.actions or ["idle"],
            target_size=body.target_size,
            seed=body.seed,
        ):
            yield line + "\n"

    return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson",
    )
