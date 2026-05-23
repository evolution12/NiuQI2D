from __future__ import annotations

import asyncio

from PIL import Image

from .base import PostProcessContext, PostProcessStep, active_images, ensure_rgba, replace_active_images


class CropCenterStep(PostProcessStep):
    name = "crop_center"

    def params(self, context: PostProcessContext) -> dict[str, tuple[int, int]]:
        return {"target_size": context.target_size}

    async def apply(self, context: PostProcessContext) -> PostProcessContext:
        images = await asyncio.to_thread(
            self._crop_all_sync,
            active_images(context),
            context.target_size,
        )
        return replace_active_images(context, images)

    def _crop_all_sync(
        self,
        images: list[Image.Image],
        target_size: tuple[int, int],
    ) -> list[Image.Image]:
        return [self._crop_one_sync(image, target_size) for image in images]

    def _crop_one_sync(self, image: Image.Image, target_size: tuple[int, int]) -> Image.Image:
        rgba = ensure_rgba(image)
        bbox = rgba.getbbox()
        if bbox is None:
            return Image.new("RGBA", target_size, (0, 0, 0, 0))

        cropped = rgba.crop(bbox)
        canvas_width = max(cropped.width, target_size[0])
        canvas_height = max(cropped.height, target_size[1])
        canvas = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
        offset = ((canvas_width - cropped.width) // 2, (canvas_height - cropped.height) // 2)
        canvas.paste(cropped, offset, cropped)
        return canvas
