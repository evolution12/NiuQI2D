"""Shared image size calculation for provider APIs."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..config import Settings


def ensure_min_size(w: int, h: int) -> tuple[int, int]:
    w = max(w, 256)
    h = max(h, 256)
    return (w, h)


def provider_size_for_grid(
    settings: Settings,
    cols: int,
    rows: int,
) -> tuple[int, int]:
    """Pick the provider image size whose aspect ratio best matches cols:rows."""
    provider = settings.image_api_provider
    aspect = cols / rows

    if provider == "openai":
        model = (settings.quality_image_model or settings.image_api_model).lower()
        if model == "dall-e-3":
            candidates = [
                (1024, 1024),
                (1792, 1024),
                (1024, 1792),
            ]
        else:
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
            (3840, 1280),
            (3072, 1024),
            (4096, 1024),
            (5120, 1024),
        ]
    else:
        candidates = [
            (1024, 1024),
            (1024, 768),
            (768, 1024),
            (1152, 864),
            (864, 1152),
        ]

    return min(candidates, key=lambda size: abs((size[0] / size[1]) - aspect))
