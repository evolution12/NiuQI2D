from __future__ import annotations

import sys
import unittest
from pathlib import Path

PYTHON_DIR = Path(__file__).resolve().parents[2] / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from fastapi_app.models import ArtStyle, Perspective, StyleProfile
from fastapi_app.routers.styles import _compact_redundant_presets


def _style(
    style_id: str,
    name: str,
    art_style: ArtStyle,
    *,
    is_preset: bool = True,
) -> StyleProfile:
    return StyleProfile(
        id=style_id,
        name=name,
        art_style=art_style,
        color_palette=None,
        reference_image_path=None,
        default_size={"w": 16, "h": 16},
        perspective=Perspective.TOP_DOWN,
        extra_params=None,
        is_preset=is_preset,
    )


class StyleOptionsTest(unittest.TestCase):
    def test_compacts_legacy_pixel_size_presets(self) -> None:
        styles = [
            _style("old-16", "像素风 16×16", ArtStyle.PIXEL),
            _style("old-32", "像素风 32×32", ArtStyle.PIXEL),
            _style("canonical", "像素风", ArtStyle.PIXEL),
            _style("custom-pixel", "我的 32×32 像素风", ArtStyle.PIXEL, is_preset=False),
            _style("cartoon", "卡通风", ArtStyle.CARTOON),
        ]

        compacted = _compact_redundant_presets(styles)

        self.assertEqual([style.id for style in compacted], ["canonical", "custom-pixel", "cartoon"])


if __name__ == "__main__":
    unittest.main()
