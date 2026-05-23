from __future__ import annotations

import asyncio
from io import BytesIO

from PIL import Image

from .base import PostProcessContext, PostProcessStep, active_images, ensure_rgba, replace_active_images


class RemoveBackgroundStep(PostProcessStep):
    name = "remove_bg"

    def should_run(self, context: PostProcessContext) -> bool:
        return not context.api_had_transparent_bg

    def params(self, context: PostProcessContext) -> dict[str, bool]:
        return {"api_had_transparent_bg": context.api_had_transparent_bg}

    async def apply(self, context: PostProcessContext) -> PostProcessContext:
        images = await asyncio.to_thread(self._remove_all_sync, active_images(context))
        return replace_active_images(context, images)

    def _remove_all_sync(self, images: list[Image.Image]) -> list[Image.Image]:
        return [self._remove_one_sync(image) for image in images]

    def _remove_one_sync(self, image: Image.Image) -> Image.Image:
        rgba = ensure_rgba(image)
        try:
            from rembg import remove
        except ImportError:
            return rgba

        source = BytesIO()
        rgba.save(source, format="PNG")
        result = remove(source.getvalue())
        return Image.open(BytesIO(result)).convert("RGBA")
