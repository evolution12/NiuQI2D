from __future__ import annotations

from io import BytesIO

from PIL import Image
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
from ..postprocess import FrameExtractorStep, PostProcessContext
from ..services.image_generator import ImageGenerator
from ..services.postprocess import PostProcessPipeline
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
        style = None
        if style_id:
            style = await self.style_crud.get(self.session, style_id)
        self._validate_asset_subtype(body.asset_type, body.asset_subtype)

        # Only support single action for now — multi-action generation comes later
        effective_actions = (body.actions or ["idle"])[:1]

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
            actions=effective_actions,
            direction_count=body.direction_count,
            frame_count=body.frame_count,
            terrain_type=body.terrain_type,
            target_size=body.target_size,
            edge_rule=body.edge_rule,
        )
        generator = ImageGenerator(self.session, self.storage, self.settings)
        result = await generator.generate_candidates(
            project_id=body.project_id,
            user_prompt=body.user_prompt,
            optimized_prompt=optimized.prompt,
            style_id=style_id,
            asset_type=body.asset_type,
            asset_subtype=body.asset_subtype,
            mode=mode,
            candidate_count=body.candidate_count,
            transparent_background=body.transparent_background,
            provider_size=self._provider_size_for_request(body, effective_actions),
            seed=body.seed,
            reference_image_path=body.reference_image_path,
        )
        records = [
            self._candidate_response(await self.generation_crud.get(self.session, item.record_id))
            for item in result.records
        ]
        for record in records:
            await self._store_project_params(
                record.id,
                body.project_id,
                body.target_size,
                body.direction_count,
                body.frame_count,
                effective_actions,
                body.terrain_type,
            )
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

        postprocess_log = record.postprocess_log
        if record.asset_subtype == AssetSubtype.ANIMATED_SPRITESHEET:
            processed = await self._process_animated_record(record, project_id, source_path)
            source_path = processed["source_path"]
            postprocess_log = processed["postprocess_log"]

        thumbnail_path = await self.storage.generate_thumbnail(source_path, record.asset_type)
        asset = await self.asset_crud.create(
            self.session,
            AssetCreateRequest(
                project_id=project_id,
                name=body.name,
                asset_type=record.asset_type,
                asset_subtype=record.asset_subtype,
                status=AssetStatus.SELECTED,
                source_path=source_path,
                thumbnail_path=thumbnail_path,
                tags=body.tags,
            ),
        )
        await self.generation_crud.update(
            self.session,
            record.id,
            {
                "asset_id": asset.id,
                "postprocess_log": postprocess_log,
                "api_params": {
                    **record.api_params,
                    "selected_source_path": source_path,
                },
            },
        )
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
            provider_size=self._provider_size_from_record(record),
            seed=record.seed,
            reference_image_path=record.reference_image_path,
        )
        records = [self._candidate_response(await self.generation_crud.get(self.session, item.record_id)) for item in result.records]
        for response in records:
            await self._store_project_params(
                response.id,
                project_id,
                self._target_size(record),
                int(record.api_params.get("direction_count", 4)),
                int(record.api_params.get("frame_count", 3)),
                self._actions(record),
                self._terrain_type(record),
            )
        refreshed = [self._candidate_response(await self.generation_crud.get(self.session, response.id)) for response in records]
        return GenerateResponse(records=refreshed, optimized_prompt=record.optimized_prompt, mode=mode)

    async def variant(self, record_id: str, body: VariantRequest) -> GenerateResponse:
        record = await self.generation_crud.get(self.session, record_id)
        project_id = await self._project_id_for_record(record)
        style_id = body.style_id_override or record.style_id
        style = await self.style_crud.get(self.session, style_id) if style_id else None
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
            style_id=style_id,
            asset_type=record.asset_type,
            asset_subtype=record.asset_subtype,
            mode=mode,
            candidate_count=body.candidate_count or 1,
            transparent_background=bool(record.api_params.get("transparent_background", True)),
            provider_size=self._provider_size_from_record(record),
            seed=body.seed_override,
            reference_image_path=body.reference_image_path or record.reference_image_path,
        )
        target_size = body.target_size_override or self._target_size(record)
        records = [self._candidate_response(await self.generation_crud.get(self.session, item.record_id)) for item in result.records]
        for response in records:
            await self._store_project_params(
                response.id,
                project_id,
                target_size,
                int(record.api_params.get("direction_count", 4)),
                int(record.api_params.get("frame_count", 3)),
                self._actions(record),
                self._terrain_type(record),
            )
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
        direction_count: int = 4,
        frame_count: int = 3,
        actions: list[str] | None = None,
        terrain_type: str | None = None,
    ) -> None:
        record = await self.generation_crud.get(self.session, record_id)
        action_names = actions or ["idle"]
        params_update: dict[str, object] = {
            "project_id": project_id,
            "target_size": {"w": target_size[0], "h": target_size[1]},
            "direction_count": direction_count,
            "frame_count": frame_count,
            "actions": action_names,
            "sheet_rows": direction_count * len(action_names),
            "sheet_cols": frame_count,
        }
        if terrain_type:
            params_update["terrain_type"] = terrain_type
        await self.generation_crud.update(
            self.session,
            record.id,
            {
                "api_params": {
                    **record.api_params,
                    **params_update,
                }
            },
        )

    async def _process_animated_record(
        self,
        record: GenerationRecord,
        project_id: str,
        source_path: str,
    ) -> dict[str, object]:
        image_bytes = await self.storage.get_image(source_path)
        with Image.open(BytesIO(image_bytes)) as image:
            source_image = image.convert("RGBA")

        target_size = self._target_size(record)
        actions = self._actions(record)
        direction_count = int(record.api_params.get("direction_count", 4))
        frame_count = int(record.api_params.get("frame_count", 3))
        sheet_rows = int(record.api_params.get("sheet_rows", max(direction_count * len(actions), 1)))
        sheet_cols = int(record.api_params.get("sheet_cols", frame_count))
        style = await self.style_crud.get(self.session, record.style_id) if record.style_id else None

        context = await PostProcessPipeline().run(
            PostProcessContext(
                image=source_image,
                asset_type=record.asset_type,
                asset_subtype=record.asset_subtype,
                style=style,
                api_had_transparent_bg=bool(record.api_params.get("transparent_background", False)),
                target_size=target_size,
                sheet_rows=sheet_rows,
                sheet_cols=sheet_cols,
            )
        )

        frames = context.extracted_frames or [context.image]
        sheet_rows = context.sheet_rows or sheet_rows
        sheet_cols = context.sheet_cols or sheet_cols
        direction_count = max(1, sheet_rows // max(len(actions), 1))
        frame_count = max(1, sheet_cols)
        preview_context = await FrameExtractorStep().run(
            PostProcessContext(
                image=source_image,
                asset_type=record.asset_type,
                asset_subtype=record.asset_subtype,
                target_size=target_size,
                sheet_rows=sheet_rows,
                sheet_cols=sheet_cols,
            )
        )
        preview_source_frames = preview_context.extracted_frames or frames
        if len(preview_source_frames) != len(frames):
            preview_source_frames = frames
        preview_frames = self._prepare_preview_frames(preview_source_frames)
        preview_paths: list[str] = []
        frame_paths: list[str] = []
        for index, frame in enumerate(preview_frames):
            preview_paths.append(
                await self.storage.save_preview_frame(
                    project_id,
                    record.id,
                    index,
                    self._png_bytes(frame),
                )
            )
        for index, frame in enumerate(frames):
            frame_paths.append(
                await self.storage.save_processed_frame(
                    project_id,
                    record.id,
                    index,
                    self._png_bytes(frame),
                )
            )

        manifest = {
            "frames": frame_paths,
            "preview_frames": preview_paths,
            "preview_frame_kind": "source_grid_full_frame",
            "frame_delay_ms": 120,
            "actions": self._animation_actions(actions, direction_count, frame_count, len(frame_paths)),
            "sheet_rows": sheet_rows,
            "sheet_cols": sheet_cols,
            "target_size": {"w": target_size[0], "h": target_size[1]},
        }
        await self.storage.save_animation_manifest(project_id, record.id, manifest)
        return {
            "source_path": frame_paths[0] if frame_paths else source_path,
            "postprocess_log": [
                {
                    "step": item.step,
                    "executed": item.executed,
                    "params": item.params,
                    "duration_ms": item.duration_ms,
                }
                for item in context.log
            ],
        }

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

    def _actions(self, record: GenerationRecord) -> list[str]:
        actions = record.api_params.get("actions")
        if isinstance(actions, list):
            names = [str(action) for action in actions if str(action)]
            if names:
                return names
        return ["idle"]

    def _terrain_type(self, record: GenerationRecord) -> str | None:
        t = record.api_params.get("terrain_type")
        return str(t) if isinstance(t, str) and t else None

    def _animation_actions(
        self,
        actions: list[str],
        direction_count: int,
        frame_count: int,
        total_frames: int,
    ) -> dict[str, list[int]]:
        direction_names = self._direction_names(direction_count)
        mapping: dict[str, list[int]] = {}
        index = 0
        for action in actions:
            action_indexes: list[int] = []
            for direction_index in range(direction_count):
                frame_indexes = list(range(index, min(index + frame_count, total_frames)))
                if frame_indexes:
                    dir_name = direction_names[direction_index] if direction_index < len(direction_names) else str(direction_index)
                    mapping[f"{action}_{dir_name}"] = frame_indexes
                    action_indexes.extend(frame_indexes)
                index += frame_count
            if action_indexes:
                mapping[f"{action}_all"] = action_indexes
        return mapping

    def _direction_names(self, direction_count: int) -> list[str]:
        if direction_count == 1:
            return ["down"]
        if direction_count == 2:
            return ["left", "right"]
        if direction_count == 4:
            return ["up", "down", "left", "right"]
        return ["up", "up_right", "right", "down_right", "down", "down_left", "left", "up_left"]

    def _provider_size_for_request(self, body: GenerateRequest, effective_actions: list[str] | None = None) -> tuple[int, int]:
        if body.asset_subtype == AssetSubtype.ANIMATED_SPRITESHEET:
            actions = effective_actions or body.actions or ["idle"]
            rows = max(1, body.direction_count * len(actions))
            cols = max(1, body.frame_count)
            return self._provider_size_for_grid(cols, rows)
        # Static images: use target_size from UI, ensure minimum pixel requirement
        tw, th = body.target_size or (256, 256)
        return self._ensure_min_size(tw, th)

    def _ensure_min_size(self, w: int, h: int) -> tuple[int, int]:
        """Ensure the image size meets minimum requirements for AI providers."""
        # Minimum dimension: at least 256px each side
        w = max(w, 256)
        h = max(h, 256)
        return (w, h)

    def _provider_size_from_record(self, record: GenerationRecord) -> tuple[int, int]:
        if record.asset_subtype != AssetSubtype.ANIMATED_SPRITESHEET:
            target = self._target_size(record)
            return self._ensure_min_size(target[0], target[1])
        cols = int(record.api_params.get("sheet_cols", record.api_params.get("frame_count", 3)))
        rows = int(record.api_params.get("sheet_rows", 4))
        return self._provider_size_for_grid(max(cols, 1), max(rows, 1))

    def _provider_size_for_grid(self, cols: int, rows: int) -> tuple[int, int]:
        """Pick the provider image size whose aspect ratio best matches cols:rows.

        Model-aware: for OpenAI, distinguishes between DALL-E 3 and GPT Image 1
        to avoid requesting disallowed sizes.
        """
        provider = self.settings.image_api_provider
        aspect = cols / rows

        if provider == "openai":
            model = (self.settings.quality_image_model or self.settings.image_api_model).lower()
            if model == "dall-e-3":
                candidates = [
                    (1024, 1024),
                    (1792, 1024),
                    (1024, 1792),
                ]
            else:
                # GPT Image 1 supports 1024×1024, 1536×1024, 1024×1536
                # but for grid matching we want more aspect-ratio variety,
                # so we generate at the closest allowed size
                candidates = [
                    (1024, 1024),
                    (1536, 1024),
                    (1024, 1536),
                ]
        elif provider == "doubao":
            candidates = [
                (2048, 2048),
                (1920, 1080),
                (1080, 1920),
                (2048, 1152),
                (1152, 2048),
            ]
        else:
            candidates = [
                (1024, 1024),
                (1024, 768),
                (768, 1024),
                (1152, 864),
                (864, 1152),
            ]

        # Score each candidate: prefer both aspect-ratio closeness AND
        # sufficient total pixels (avoid picking tiny sizes for large grids)
        return min(candidates, key=lambda size: abs((size[0] / size[1]) - aspect))

    def _prepare_preview_frames(self, frames: list[Image.Image]) -> list[Image.Image]:
        return [self._prepare_preview_frame(frame) for frame in frames]

    def _prepare_preview_frame(self, frame: Image.Image) -> Image.Image:
        rgba = frame.convert("RGBA")
        padding = max(2, round(max(rgba.size) * 0.08))
        canvas = Image.new("RGBA", (rgba.width + padding * 2, rgba.height + padding * 2), (0, 0, 0, 0))
        canvas.paste(rgba, (padding, padding), rgba)
        return canvas

    def _png_bytes(self, image: Image.Image) -> bytes:
        output = BytesIO()
        image.save(output, format="PNG")
        return output.getvalue()

    def _reference_description(
        self,
        style: StyleProfile | None,
        override: str | None,
    ) -> str | None:
        if override:
            return override
        if style is None:
            return None
        extra_params = style.extra_params or {}
        value = extra_params.get("reference_style_description")
        return value if isinstance(value, str) else None
