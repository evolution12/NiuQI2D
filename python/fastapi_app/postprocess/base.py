from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from PIL import Image

from ..models import AssetSubtype, AssetType


@dataclass
class PostProcessLog:
    step: str
    executed: bool
    params: dict[str, Any] = field(default_factory=dict)
    duration_ms: int = 0


@dataclass
class PostProcessContext:
    image: Image.Image
    extracted_frames: list[Image.Image] = field(default_factory=list)
    asset_type: AssetType = AssetType.CHARACTER
    asset_subtype: AssetSubtype | None = None
    style: Any | None = None
    api_had_transparent_bg: bool = False
    target_size: tuple[int, int] = (16, 16)
    sheet_rows: int | None = None
    sheet_cols: int | None = None
    log: list[PostProcessLog] = field(default_factory=list)


class PostProcessStep(ABC):
    name: str

    async def run(self, context: PostProcessContext) -> PostProcessContext:
        started = time.perf_counter()
        executed = self.should_run(context)
        params = self.params(context)
        if executed:
            context = await self.apply(context)
        duration_ms = int((time.perf_counter() - started) * 1000)
        context.log.append(
            PostProcessLog(
                step=self.name,
                executed=executed,
                params=params,
                duration_ms=duration_ms,
            )
        )
        return context

    def should_run(self, context: PostProcessContext) -> bool:
        return True

    def params(self, context: PostProcessContext) -> dict[str, Any]:
        return {}

    @abstractmethod
    async def apply(self, context: PostProcessContext) -> PostProcessContext:
        raise NotImplementedError


def ensure_rgba(image: Image.Image) -> Image.Image:
    if image.mode == "RGBA":
        return image.copy()
    return image.convert("RGBA")


def get_art_style_value(style: Any | None) -> str | None:
    art_style = getattr(style, "art_style", None)
    if art_style is None:
        return None
    return getattr(art_style, "value", str(art_style))


def get_pixel_color_count(style: Any | None, default: int = 16) -> int:
    extra_params = getattr(style, "extra_params", None) or {}
    value = extra_params.get("color_count", default)
    if not isinstance(value, int):
        return default
    return max(2, min(value, 256))


def active_images(context: PostProcessContext) -> list[Image.Image]:
    return context.extracted_frames if context.extracted_frames else [context.image]


def replace_active_images(context: PostProcessContext, images: list[Image.Image]) -> PostProcessContext:
    if context.extracted_frames:
        context.extracted_frames = images
    elif images:
        context.image = images[0]
    return context
