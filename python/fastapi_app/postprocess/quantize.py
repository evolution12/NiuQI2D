from __future__ import annotations

import asyncio

from PIL import Image

from .base import (
    PostProcessContext,
    PostProcessStep,
    active_images,
    ensure_rgba,
    get_art_style_value,
    get_pixel_color_count,
    replace_active_images,
)


class QuantizeStep(PostProcessStep):
    name = "quantize"

    def should_run(self, context: PostProcessContext) -> bool:
        return get_art_style_value(context.style) == "pixel"

    def params(self, context: PostProcessContext) -> dict[str, int]:
        return {"color_count": get_pixel_color_count(context.style)}

    async def apply(self, context: PostProcessContext) -> PostProcessContext:
        color_count = get_pixel_color_count(context.style)
        images = await asyncio.to_thread(
            self._quantize_all_sync,
            active_images(context),
            color_count,
        )
        return replace_active_images(context, images)

    def _quantize_all_sync(self, images: list[Image.Image], color_count: int) -> list[Image.Image]:
        return [self._quantize_one_sync(image, color_count) for image in images]

    def _quantize_one_sync(self, image: Image.Image, color_count: int) -> Image.Image:
        rgba = ensure_rgba(image)
        alpha = rgba.getchannel("A")
        rgb = rgba.convert("RGB")
        quantized = rgb.quantize(colors=color_count, method=Image.Quantize.MEDIANCUT)
        result = quantized.convert("RGBA")
        result.putalpha(alpha)
        return result
