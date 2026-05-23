from __future__ import annotations

from ..models import AssetSubtype
from .base import PostProcessContext, PostProcessStep, ensure_rgba


class FrameExtractorStep(PostProcessStep):
    name = "frame_extractor"

    def should_run(self, context: PostProcessContext) -> bool:
        return (
            context.asset_subtype == AssetSubtype.ANIMATED_SPRITESHEET
            and context.sheet_rows is not None
            and context.sheet_cols is not None
            and context.sheet_rows > 0
            and context.sheet_cols > 0
        )

    def params(self, context: PostProcessContext) -> dict[str, int | None]:
        return {
            "sheet_rows": context.sheet_rows,
            "sheet_cols": context.sheet_cols,
            "target_width": context.target_size[0],
            "target_height": context.target_size[1],
        }

    async def apply(self, context: PostProcessContext) -> PostProcessContext:
        image = ensure_rgba(context.image)
        rows = context.sheet_rows or 1
        cols = context.sheet_cols or 1
        cell_width = image.width / cols
        cell_height = image.height / rows
        frames = []

        for row in range(rows):
            for col in range(cols):
                left = round(col * cell_width)
                upper = round(row * cell_height)
                right = round((col + 1) * cell_width)
                lower = round((row + 1) * cell_height)
                frames.append(image.crop((left, upper, right, lower)).convert("RGBA"))

        context.image = image
        context.extracted_frames = frames
        return context
