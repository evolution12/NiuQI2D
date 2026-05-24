from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..crud.asset import AssetCRUD
from ..crud.generation import GenerationCRUD
from ..crud.project import ProjectCRUD
from ..crud.style import StyleCRUD
from ..exceptions import InvalidParamError
from ..models import Asset, AssetStatus, AssetSubtype, AssetType, GenerationRecord, StyleProfile
from ..providers.base import GenerationMode
from ..schemas import (
    AssetCreateRequest,
    GenerateRequest,
    GenerateResponse,
    GenerationCandidateResponse,
    SelectRecordRequest,
    SelectRecordResponse,
    VariantRequest,
)
from ..services.image_generator import ImageGenerator
from ..services.prompt_optimizer import PromptOptimizer
from ..storage import StorageManager


class GenerationService:
    def __init__(self, session: AsyncSession, storage: StorageManager) -> None:
        self.session = session
        self.storage = storage
        self.project_crud = ProjectCRUD()
        self.style_crud = StyleCRUD()
        self.generation_crud = GenerationCRUD()
        self.asset_crud = AssetCRUD()
        self.settings = get_settings()

    async def generate(self, body: GenerateRequest, mode: GenerationMode) -> GenerateResponse:
        project = await self.project_crud.get(self.session, body.project_id)
        style_id = body.style_id or project.style_id
        if style_id is None:
            raise InvalidParamError("生成前必须选择风格")
        style = await self.style_crud.get(self.session, style_id)
        self._validate_asset_subtype(body.asset_type, body.asset_subtype)

        reference_description = self._reference_description(style, body.reference_style_description)
        optimizer = PromptOptimizer(
            self.settings.text_api_provider,
            self.settings.text_api_key,
            self.settings.text_api_model,
        )
        optimized = await optimizer.optimize(
            user_prompt=body.user_prompt,
            asset_type=body.asset_type,
            asset_subtype=body.asset_subtype,
            style=style,
            reference_style_description=reference_description,
            actions=body.actions,
            direction_count=body.direction_count,
            frame_count=body.frame_count,
        )
        generator = ImageGenerator(self.session, self.storage, self.settings)
        result = await generator.generate_candidates(
            project_id=body.project_id,
            user_prompt=body.user_prompt,
            optimized_prompt=optimized.prompt,
            style_id=style.id,
            asset_type=body.asset_type,
            asset_subtype=body.asset_subtype,
            mode=mode,
            candidate_count=body.candidate_count,
            transparent_background=body.transparent_background,
            seed=body.seed,
            reference_image_path=body.reference_image_path,
        )
        records = [
            self._candidate_response(await self.generation_crud.get(self.session, item.record_id))
            for item in result.records
        ]
        for record in records:
            await self._store_project_params(record.id, body.project_id, body.target_size)
        refreshed = [self._candidate_response(await self.generation_crud.get(self.session, record.id)) for record in records]
        return GenerateResponse(records=refreshed, optimized_prompt=optimized.prompt, mode=mode)

    async def select_record(
        self,
        record_id: str,
        body: SelectRecordRequest,
    ) -> SelectRecordResponse:
        record = await self.generation_crud.get(self.session, record_id)
        project_id = await self._project_id_for_record(record)
        source_path = record.api_params.get("raw_image_path")
        if not isinstance(source_path, str) or not source_path:
            raise InvalidParamError("生成记录缺少原始图片路径")
        thumbnail_path = await self.storage.generate_thumbnail(source_path, record.asset_type)
        asset = await self.asset_crud.create(
            self.session,
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
        await self.generation_crud.update(self.session, record.id, {"asset_id": asset.id})
        return SelectRecordResponse(asset=asset)

    async def list_records(
        self,
        project_id: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[GenerationCandidateResponse], int]:
        stmt = select(GenerationRecord).order_by(GenerationRecord.created_at.desc())
        items, total = await self.generation_crud.list(
            self.session,
            page=1,
            page_size=10_000,
            statement=stmt,
        )
        if project_id is not None:
            await self.project_crud.get(self.session, project_id)
            filtered = []
            for record in items:
                if await self._project_id_for_record(record, missing_ok=True) == project_id:
                    filtered.append(record)
            items = filtered
            total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        return [self._candidate_response(record) for record in items[start:end]], total

    async def reproduce(self, record_id: str) -> GenerateResponse:
        record = await self.generation_crud.get(self.session, record_id)
        project_id = await self._project_id_for_record(record)
        generator = ImageGenerator(self.session, self.storage, self.settings)
        mode = GenerationMode(record.api_params.get("mode", GenerationMode.QUALITY.value))
        result = await generator.generate_candidates(
            project_id=project_id,
            user_prompt=record.user_prompt,
            optimized_prompt=record.optimized_prompt,
            style_id=record.style_id,
            asset_type=record.asset_type,
            asset_subtype=record.asset_subtype,
            mode=mode,
            candidate_count=1,
            transparent_background=bool(record.api_params.get("transparent_background", True)),
            seed=record.seed,
            reference_image_path=record.reference_image_path,
        )
        records = [self._candidate_response(await self.generation_crud.get(self.session, item.record_id)) for item in result.records]
        for response in records:
            await self._store_project_params(response.id, project_id, self._target_size(record))
        refreshed = [self._candidate_response(await self.generation_crud.get(self.session, response.id)) for response in records]
        return GenerateResponse(records=refreshed, optimized_prompt=record.optimized_prompt, mode=mode)

    async def variant(self, record_id: str, body: VariantRequest) -> GenerateResponse:
        record = await self.generation_crud.get(self.session, record_id)
        project_id = await self._project_id_for_record(record)
        style_id = body.style_id_override or record.style_id
        style = await self.style_crud.get(self.session, style_id)
        user_prompt = body.prompt_override or record.user_prompt
        reference_description = self._reference_description(style, body.reference_style_description)

        optimized_prompt = record.optimized_prompt
        if body.prompt_override or body.style_id_override or body.reference_style_description:
            optimizer = PromptOptimizer(
                self.settings.text_api_provider,
                self.settings.text_api_key,
                self.settings.text_api_model,
            )
            optimized = await optimizer.optimize(
                user_prompt=user_prompt,
                asset_type=record.asset_type,
                asset_subtype=record.asset_subtype,
                style=style,
                reference_style_description=reference_description,
            )
            optimized_prompt = optimized.prompt

        mode = GenerationMode(record.api_params.get("mode", GenerationMode.QUALITY.value))
        generator = ImageGenerator(self.session, self.storage, self.settings)
        result = await generator.generate_candidates(
            project_id=project_id,
            user_prompt=user_prompt,
            optimized_prompt=optimized_prompt,
            style_id=style.id,
            asset_type=record.asset_type,
            asset_subtype=record.asset_subtype,
            mode=mode,
            candidate_count=body.candidate_count or 1,
            transparent_background=bool(record.api_params.get("transparent_background", True)),
            seed=body.seed_override,
            reference_image_path=body.reference_image_path or record.reference_image_path,
        )
        target_size = body.target_size_override or self._target_size(record)
        records = [self._candidate_response(await self.generation_crud.get(self.session, item.record_id)) for item in result.records]
        for response in records:
            await self._store_project_params(response.id, project_id, target_size)
        refreshed = [self._candidate_response(await self.generation_crud.get(self.session, response.id)) for response in records]
        return GenerateResponse(records=refreshed, optimized_prompt=optimized_prompt, mode=mode)

    def _validate_asset_subtype(self, asset_type: AssetType, asset_subtype: AssetSubtype | None) -> None:
        if asset_type == AssetType.CHARACTER and asset_subtype is None:
            raise InvalidParamError("asset_type=character 时必须提供 asset_subtype")
        if asset_type != AssetType.CHARACTER and asset_subtype is not None:
            raise InvalidParamError("仅 character 资产支持 asset_subtype")

    def _candidate_response(self, record: GenerationRecord) -> GenerationCandidateResponse:
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

    async def _store_project_params(
        self,
        record_id: str,
        project_id: str,
        target_size: tuple[int, int],
    ) -> None:
        record = await self.generation_crud.get(self.session, record_id)
        await self.generation_crud.update(
            self.session,
            record.id,
            {
                "api_params": {
                    **record.api_params,
                    "project_id": project_id,
                    "target_size": {"w": target_size[0], "h": target_size[1]},
                }
            },
        )

    async def _project_id_for_record(self, record: GenerationRecord, missing_ok: bool = False) -> str | None:
        project_id = record.api_params.get("project_id")
        if isinstance(project_id, str) and project_id:
            return project_id
        if record.asset_id:
            asset = await self.session.get(Asset, record.asset_id)
            if asset is not None:
                return asset.project_id
        if missing_ok:
            return None
        raise InvalidParamError("生成记录缺少项目上下文")

    def _target_size(self, record: GenerationRecord) -> tuple[int, int]:
        target_size = record.api_params.get("target_size")
        if isinstance(target_size, dict):
            return (int(target_size.get("w", 16)), int(target_size.get("h", 16)))
        return (16, 16)

    def _reference_description(
        self,
        style: StyleProfile,
        override: str | None,
    ) -> str | None:
        if override:
            return override
        extra_params = style.extra_params or {}
        value = extra_params.get("reference_style_description")
        return value if isinstance(value, str) else None
