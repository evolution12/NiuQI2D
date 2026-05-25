"""Multi-step quality pipeline for animated spritesheet generation.

Flow:
  Step 1: Generate base character image candidates → user selects one
  Step 2: For each direction, generate 1-row animation using base image as reference
  Step 3: Compose all direction rows into final spritesheet → post-process → save
"""
from __future__ import annotations

import logging
import uuid
from io import BytesIO
from typing import Any

from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..crud.generation import GenerationCRUD
from ..exceptions import InvalidParamError
from ..models import AssetSubtype, AssetType, GenerationRecord, StyleProfile
from ..postprocess import PostProcessContext
from ..providers.base import GenerationMode
from ..schemas import GenerationRecordCreateRequest
from ..services.image_generator import ImageGenerator
from ..services.postprocess import PostProcessPipeline
from ..services.prompt_optimizer import PromptOptimizer
from ..storage import StorageManager

logger = logging.getLogger(__name__)


class QualityPipelineService:
    def __init__(self, session: AsyncSession, storage: StorageManager) -> None:
        self.session = session
        self.storage = storage
        self.settings = get_settings()
        self.generation_crud = GenerationCRUD()

    # ------------------------------------------------------------------
    # Step 1: Base character image
    # ------------------------------------------------------------------

    async def generate_base_candidates(
        self,
        project_id: str,
        user_prompt: str,
        style: StyleProfile | None,
        style_id: str | None,
        reference_style_description: str | None,
        target_size: tuple[int, int],
        candidate_count: int = 2,
        seed: str | None = None,
        reference_image_path: str | None = None,
    ) -> dict[str, Any]:
        """Generate base character image candidates for user selection."""

        optimizer = PromptOptimizer(
            self.settings.text_api_provider,
            self.settings.text_api_key,
            self.settings.text_api_model,
        )
        optimized = await optimizer.optimize_base_character(
            user_prompt=user_prompt,
            style=style,
            reference_style_description=reference_style_description,
        )

        generator = ImageGenerator(self.session, self.storage, self.settings)
        provider_size = self._provider_size_for_single(target_size)
        result = await generator.generate_candidates(
            project_id=project_id,
            user_prompt=user_prompt,
            optimized_prompt=optimized.prompt,
            style_id=style_id,
            asset_type=AssetType.CHARACTER,
            asset_subtype=AssetSubtype.ANIMATED_SPRITESHEET,
            mode=GenerationMode.QUALITY,
            candidate_count=candidate_count,
            transparent_background=True,
            provider_size=provider_size,
            seed=seed,
            reference_image_path=reference_image_path,
        )

        pipeline_id = str(uuid.uuid4())
        # Tag records with pipeline metadata
        for stored in result.records:
            await self.generation_crud.update(
                self.session,
                stored.record_id,
                {
                    "api_params": {
                        **(await self.generation_crud.get(self.session, stored.record_id)).api_params,
                        "pipeline_id": pipeline_id,
                        "pipeline_role": "base",
                    },
                },
            )

        return {
            "records": [self._record_response(await self.generation_crud.get(self.session, r.record_id)) for r in result.records],
            "optimized_prompt": optimized.prompt,
            "pipeline_id": pipeline_id,
        }

    # ------------------------------------------------------------------
    # Step 2+3: Per-direction generation + composition
    # ------------------------------------------------------------------

    async def generate_directions(
        self,
        base_record_id: str,
        direction_count: int,
        frame_count: int,
        actions: list[str],
        target_size: tuple[int, int],
        seed: str | None = None,
    ) -> dict[str, Any]:
        """Generate per-direction animation rows, compose into final spritesheet."""

        print(f"[Pipeline] generate_directions called: base_record_id={base_record_id}, "
              f"direction_count={direction_count}, frame_count={frame_count}, "
              f"actions={actions}, target_size={target_size}")

        base_record = await self.generation_crud.get(self.session, base_record_id)
        raw_image_path = base_record.api_params.get("raw_image_path")
        print(f"[Pipeline] base_record: project_id={base_record.project_id}, "
              f"raw_image_path={raw_image_path}, api_params_keys={list(base_record.api_params.keys())}")
        if not raw_image_path:
            raise InvalidParamError("基座图记录缺少原始图片路径")

        project_id = base_record.project_id
        if not project_id:
            raise InvalidParamError("基座图记录缺少项目 ID")

        # Load base image bytes for reference
        base_image_bytes = await self.storage.get_image(raw_image_path)
        print(f"[Pipeline] base_image_bytes loaded: {len(base_image_bytes)} bytes")

        # Prepare optimizer for direction row prompts
        optimizer = PromptOptimizer(
            self.settings.text_api_provider,
            self.settings.text_api_key,
            self.settings.text_api_model,
        )

        # Load style info
        from ..crud.style import StyleCRUD
        style_crud = StyleCRUD()
        style = await style_crud.get(self.session, base_record.style_id) if base_record.style_id else None

        direction_names = self._direction_names(direction_count)
        provider_size = self._provider_size_for_row(frame_count, target_size)
        print(f"[Pipeline] direction_names={direction_names}, provider_size={provider_size}")

        generator = ImageGenerator(self.session, self.storage, self.settings)
        pipeline_id = base_record.api_params.get("pipeline_id", str(uuid.uuid4()))

        # Step 2: Generate each direction row
        direction_results: list[dict[str, Any]] = []
        direction_rows: list[tuple[str, Image.Image]] = []  # (direction_name, row_image)

        for action in actions[:1]:  # Single action for now
            # Pre-generate unified action details so all directions share the same motion
            action_details = await optimizer.generate_action_details(
                character_description=base_record.user_prompt,
                action=action,
            )
            print(f"[Pipeline] action_details for '{action}': {action_details!r}")

            for i, direction in enumerate(direction_names):
                try:
                    dir_prompt = optimizer.optimize_direction_row(
                        direction=direction,
                        frame_count=frame_count,
                        action=action,
                        action_details=action_details,
                        style=style,
                    )

                    print(f"\n{'='*60}\n[DIRECTION PROMPT] {action}_{direction}:\n{'='*60}\n{dir_prompt.prompt}\n{'='*60}\n")

                    # Generate with base image as reference
                    provider = generator._build_provider(GenerationMode.QUALITY)
                    images = await provider.generate_with_reference(
                        prompt=dir_prompt.prompt,
                        reference_image=base_image_bytes,
                        size=provider_size,
                        n=1,
                        transparent_background=True,
                        seed=seed,
                    )

                    if not images:
                        direction_results.append({"direction": f"{action}_{direction}", "status": "failed", "record_id": None})
                        continue

                    # Save the generated row image
                    img = images[0]
                    row_record = await self._save_direction_record(
                        project_id=project_id,
                        user_prompt=base_record.user_prompt,
                        optimized_prompt=dir_prompt.prompt,
                        style_id=base_record.style_id,
                        provider=provider,
                        image=img,
                        pipeline_id=pipeline_id,
                        direction=f"{action}_{direction}",
                        action=action,
                        frame_count=frame_count,
                    )

                    # Load the row image for composition
                    row_record_data = await self.generation_crud.get(self.session, row_record)
                    row_path = row_record_data.api_params.get("raw_image_path")
                    row_bytes = await self.storage.get_image(row_path)
                    row_image = Image.open(BytesIO(row_bytes)).convert("RGBA")

                    direction_rows.append((direction, row_image))
                    direction_results.append({
                        "direction": f"{action}_{direction}",
                        "status": "success",
                        "record_id": row_record,
                    })
                except Exception as exc:
                    logger.error(
                        "方向 %s 生成失败: %s", f"{action}_{direction}", exc,
                        exc_info=True,
                    )
                    print(f"[Pipeline] 方向 {action}_{direction} 生成失败: {exc}")
                    direction_results.append({
                        "direction": f"{action}_{direction}",
                        "status": "failed",
                        "record_id": None,
                        "error": str(exc),
                    })

        if not direction_rows:
            errors = "; ".join(
                f"{r['direction']}: {r.get('error', 'unknown')}"
                for r in direction_results
                if r["status"] == "failed"
            )
            raise InvalidParamError(f"所有方向生成均失败 — {errors}")

        # Step 3: Compose spritesheet
        spritesheet = self._compose_spritesheet(direction_rows, frame_count, target_size)

        # Save the composed spritesheet as a raw image and create a generation record
        spritesheet_bytes = self._png_bytes(spritesheet)
        composed_record = await self.generation_crud.create(
            self.session,
            GenerationRecordCreateRequest(
                project_id=project_id,
                user_prompt=base_record.user_prompt,
                optimized_prompt=base_record.optimized_prompt,
                style_id=base_record.style_id,
                asset_type=AssetType.CHARACTER,
                asset_subtype=AssetSubtype.ANIMATED_SPRITESHEET,
                api_provider=base_record.api_provider,
                api_model=base_record.api_model,
                api_params={
                    "mode": GenerationMode.QUALITY.value,
                    "project_id": project_id,
                    "pipeline_id": pipeline_id,
                    "pipeline_role": "composed",
                    "direction_count": direction_count,
                    "frame_count": frame_count,
                    "actions": actions,
                    "target_size": {"w": target_size[0], "h": target_size[1]},
                    "sheet_rows": direction_count * len(actions),
                    "sheet_cols": frame_count,
                },
                reference_image_path=base_record.reference_image_path,
            ),
        )
        raw_path = await self.storage.save_raw_image(project_id, composed_record.id, spritesheet_bytes)
        await self.generation_crud.update(
            self.session,
            composed_record.id,
            {
                "api_params": {
                    **composed_record.api_params,
                    "raw_image_path": raw_path,
                    "image_url": f"/images/{raw_path}",
                },
            },
        )

        # Post-process the composed spritesheet
        manifest = await self._postprocess_and_save(
            spritesheet=spritesheet,
            project_id=project_id,
            group_id=composed_record.id,
            actions=actions,
            direction_count=direction_count,
            frame_count=frame_count,
            target_size=target_size,
            style=style,
        )

        return {
            "composed_record_id": composed_record.id,
            "pipeline_id": pipeline_id,
            "direction_results": direction_results,
            "manifest": manifest,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compose_spritesheet(
        self,
        direction_rows: list[tuple[str, Image.Image]],
        frame_count: int,
        target_size: tuple[int, int],
    ) -> Image.Image:
        """Stitch direction rows into a single spritesheet grid."""
        if not direction_rows:
            raise InvalidParamError("没有可拼接的方向行")

        # Normalize all rows to the same width (max width among rows)
        max_width = max(row.width for _, row in direction_rows)
        row_height = max(row.height for _, row in direction_rows)

        normalized_rows = []
        for direction, row in direction_rows:
            if row.width != max_width or row.height != row_height:
                new_row = Image.new("RGBA", (max_width, row_height), (0, 0, 0, 0))
                new_row.paste(row, ((max_width - row.width) // 2, (row_height - row.height) // 2))
                normalized_rows.append(new_row)
            else:
                normalized_rows.append(row)

        total_height = row_height * len(normalized_rows)
        canvas = Image.new("RGBA", (max_width, total_height), (0, 0, 0, 0))
        for i, row in enumerate(normalized_rows):
            canvas.paste(row, (0, i * row_height))

        return canvas

    async def _postprocess_and_save(
        self,
        spritesheet: Image.Image,
        project_id: str,
        group_id: str,
        actions: list[str],
        direction_count: int,
        frame_count: int,
        target_size: tuple[int, int],
        style: StyleProfile | None,
    ) -> dict[str, Any]:
        """Run post-processing pipeline on the composed spritesheet and save results."""

        sheet_rows = direction_count * len(actions)
        sheet_cols = frame_count

        context = await PostProcessPipeline().run(
            PostProcessContext(
                image=spritesheet,
                asset_type=AssetType.CHARACTER,
                asset_subtype=AssetSubtype.ANIMATED_SPRITESHEET,
                style=style,
                api_had_transparent_bg=True,
                target_size=target_size,
                sheet_rows=sheet_rows,
                sheet_cols=sheet_cols,
            )
        )

        frames = context.extracted_frames or [context.image]
        preview_frames = self._prepare_preview_frames(frames)

        preview_paths: list[str] = []
        frame_paths: list[str] = []
        for index, frame in enumerate(preview_frames):
            preview_paths.append(
                await self.storage.save_preview_frame(project_id, group_id, index, self._png_bytes(frame))
            )
        for index, frame in enumerate(frames):
            frame_paths.append(
                await self.storage.save_processed_frame(project_id, group_id, index, self._png_bytes(frame))
            )

        direction_names = self._direction_names(direction_count)
        action_mapping = self._build_action_mapping(actions, direction_names, frame_count, len(frame_paths))

        manifest = {
            "frames": frame_paths,
            "preview_frames": preview_paths,
            "frame_delay_ms": 120,
            "actions": action_mapping,
            "sheet_rows": sheet_rows,
            "sheet_cols": sheet_cols,
            "target_size": {"w": target_size[0], "h": target_size[1]},
        }
        await self.storage.save_animation_manifest(project_id, group_id, manifest)
        return manifest

    def _build_action_mapping(
        self,
        actions: list[str],
        direction_names: list[str],
        frame_count: int,
        total_frames: int,
    ) -> dict[str, list[int]]:
        mapping: dict[str, list[int]] = {}
        index = 0
        for action in actions:
            action_indexes: list[int] = []
            for direction in direction_names:
                frame_indexes = list(range(index, min(index + frame_count, total_frames)))
                if frame_indexes:
                    mapping[f"{action}_{direction}"] = frame_indexes
                    action_indexes.extend(frame_indexes)
                index += frame_count
            if action_indexes:
                mapping[f"{action}_all"] = action_indexes
        return mapping

    async def _save_direction_record(
        self,
        project_id: str,
        user_prompt: str,
        optimized_prompt: str,
        style_id: str | None,
        provider: Any,
        image: Any,
        pipeline_id: str,
        direction: str,
        action: str,
        frame_count: int,
    ) -> str:
        """Save a direction row generation record."""
        from ..providers.base import GeneratedImage

        record = await self.generation_crud.create(
            self.session,
            GenerationRecordCreateRequest(
                project_id=project_id,
                user_prompt=user_prompt,
                optimized_prompt=optimized_prompt,
                style_id=style_id,
                asset_type=AssetType.CHARACTER,
                asset_subtype=AssetSubtype.ANIMATED_SPRITESHEET,
                api_provider=provider.provider_name,
                api_model=provider.model,
                api_params={
                    "mode": GenerationMode.QUALITY.value,
                    "project_id": project_id,
                    "pipeline_id": pipeline_id,
                    "pipeline_role": "direction_row",
                    "direction": direction,
                    "action": action,
                    "frame_count": frame_count,
                },
                seed=image.seed,
            ),
        )
        image_path = await self.storage.save_raw_image(project_id, record.id, image.image_data)
        await self.generation_crud.update(
            self.session,
            record.id,
            {
                "api_params": {
                    **record.api_params,
                    "raw_image_path": image_path,
                    "revised_prompt": image.revised_prompt,
                },
            },
        )
        return record.id

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

    def _direction_names(self, direction_count: int) -> list[str]:
        if direction_count == 1:
            return ["down"]
        if direction_count == 2:
            return ["left", "right"]
        if direction_count == 4:
            return ["up", "down", "left", "right"]
        return ["up", "up_right", "right", "down_right", "down", "down_left", "left", "up_left"]

    def _provider_size_for_single(self, target_size: tuple[int, int]) -> tuple[int, int]:
        """Provider size for a single base image (non-grid)."""
        w, h = target_size
        w = max(w, 256)
        h = max(h, 256)
        # Pick a square or near-square size at 1024+
        return (1024, 1024)

    def _provider_size_for_row(self, frame_count: int, target_size: tuple[int, int]) -> tuple[int, int]:
        """Provider size for a 1×N row animation.

        Picks the provider size whose aspect ratio best matches frame_count:1.
        """
        from .generation_service import GenerationService
        gs = GenerationService.__new__(GenerationService)
        gs.settings = self.settings
        # Use the grid helper with cols=frame_count, rows=1
        size = gs._provider_size_for_grid(frame_count, 1)
        # If the best match is still too far from the target ratio (e.g. 1:1
        # picked for a 3:1 row), try to construct a custom wide size.
        aspect = size[0] / size[1]
        target_aspect = frame_count
        if abs(aspect - target_aspect) > 1.0:
            # Build a size that matches the aspect ratio at reasonable resolution
            h = 1024
            w = h * frame_count
            # Ensure we meet doubao min-pixels if needed
            if self.settings.image_api_provider == "doubao":
                min_pixels = 3_686_400
                if w * h < min_pixels:
                    scale = (min_pixels / (w * h)) ** 0.5
                    w, h = round(w * scale), round(h * scale)
            size = (w, h)
        return size

    def _record_response(self, record: GenerationRecord) -> dict[str, Any]:
        """Build a lightweight record response dict."""
        return {
            "id": record.id,
            "user_prompt": record.user_prompt,
            "optimized_prompt": record.optimized_prompt,
            "asset_type": record.asset_type.value if record.asset_type else None,
            "asset_subtype": record.asset_subtype.value if record.asset_subtype else None,
            "image_url": f"/images/{record.api_params.get('raw_image_path', '')}",
            "revised_prompt": record.api_params.get("revised_prompt"),
            "created_at": record.created_at.isoformat() if record.created_at else None,
        }
