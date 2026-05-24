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
        return [self._resize_one(image, target_size, resample) for image in images]

    def _resize_one(
        self,
        image: Image.Image,
        target_size: tuple[int, int],
        resample: Image.Resampling,
    ) -> Image.Image:
        rgba = ensure_rgba(image)
        tw, th = target_size
        iw, ih = rgba.size

        # 已经是目标尺寸，直接返回
        if iw == tw and ih == th:
            return rgba

        padding = 0.9
        # 等比缩放并保留少量边距，避免角色贴边后看起来缺身体部位。
        scale = min((tw * padding) / iw, (th * padding) / ih)
        new_w = max(1, round(iw * scale))
        new_h = max(1, round(ih * scale))

        resized = rgba.resize((new_w, new_h), resample=resample)

        # 如果缩放后尺寸与 target_size 不完全一致，居中放到透明画布上
        if new_w != tw or new_h != th:
            canvas = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
            x = (tw - new_w) // 2
            y = (th - new_h) // 2
            canvas.paste(resized, (x, y), resized)
            return canvas

        return resized
