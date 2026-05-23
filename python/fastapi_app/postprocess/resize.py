from __future__ import annotations

import asyncio

from PIL import Image

from .base import (
    PostProcessContext,
    PostProcessStep,
    active_images,
    ensure_rgba,
    get_art_style_value,
    replace_active_images,
)


class ResizeStep(PostProcessStep):
    name = "resize"

    def params(self, context: PostProcessContext) -> dict[str, object]:
        return {
            "target_size": context.target_size,
            "resample": "NEAREST" if get_art_style_value(context.style) == "pixel" else "LANCZOS",
        }

    async def apply(self, context: PostProcessContext) -> PostProcessContext:
        resample = Image.Resampling.NEAREST
        if get_art_style_value(context.style) != "pixel":
            resample = Image.Resampling.LANCZOS

        images = await asyncio.to_thread(
            self._resize_all_sync,
            active_images(context),
            context.target_size,
            resample,
        )
        return replace_active_images(context, images)

    def _resize_all_sync(
        self,
        images: list[Image.Image],
        target_size: tuple[int, int],
        resample: Image.Resampling,
    ) -> list[Image.Image]:
        return [ensure_rgba(image).resize(target_size, resample=resample) for image in images]
