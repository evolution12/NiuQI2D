from __future__ import annotations

import asyncio
from pathlib import Path

from PIL import Image

from ..exceptions import ResourceNotFoundError


class ReferenceAnalyzer:
    def __init__(self, api_provider: str, api_key: str, api_model: str) -> None:
        self.api_provider = api_provider
        self.api_key = api_key
        self.api_model = api_model

    async def analyze_style(self, image_path: str) -> str:
        path = Path(image_path)
        if not path.exists():
            raise ResourceNotFoundError(f"参考图 {image_path} 不存在")
        return await asyncio.to_thread(self._analyze_sync, path)

    def _analyze_sync(self, image_path: Path) -> str:
        with Image.open(image_path) as image:
            rgba = image.convert("RGBA")
            width, height = rgba.size
            colors = rgba.resize((64, 64)).getcolors(maxcolors=4096) or []
            opaque_colors = [
                color
                for _count, color in sorted(colors, reverse=True)
                if len(color) == 4 and color[3] > 24
            ][:6]
        palette = ", ".join(self._hex_color(color) for color in opaque_colors) or "mixed palette"
        density = "low detail" if width <= 32 and height <= 32 else "medium detail"
        edge_style = "crisp hard edges" if width <= 64 and height <= 64 else "soft rendered edges"
        return (
            f"2D game asset reference, {width}x{height}, {density}, "
            f"{edge_style}, dominant palette {palette}, transparent background aware"
        )

    def _hex_color(self, color: tuple[int, int, int, int]) -> str:
        return f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
