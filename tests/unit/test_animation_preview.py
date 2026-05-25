from __future__ import annotations

import json
import sys
import tempfile
import unittest
import asyncio
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

PYTHON_DIR = Path(__file__).resolve().parents[2] / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from fastapi_app.routers.assets import _animation_frames_from_asset
from fastapi_app.models import AssetSubtype
from fastapi_app.postprocess.base import PostProcessContext
from fastapi_app.postprocess.frame_extractor import FrameExtractorStep
from fastapi_app.services.generation_service import GenerationService


class _FakeStorage:
    def __init__(self, root: Path) -> None:
        self.root = root

    def _resolve_image_path(self, image_path: str) -> Path:
        return self.root / image_path


class AnimationPreviewTest(unittest.TestCase):
    def test_animation_endpoint_ignores_legacy_cropped_previews(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frame_dir = root / "project" / "processed" / "record"
            frame_dir.mkdir(parents=True)
            (frame_dir / "animation.json").write_text(
                json.dumps(
                    {
                        "frames": ["project/processed/record/frame_000.png"],
                        "preview_frames": ["project/processed/record/preview_000.png"],
                        "frame_delay_ms": 120,
                    }
                ),
                encoding="utf-8",
            )
            asset = SimpleNamespace(source_path="project/processed/record/frame_000.png")

            frames, _, _ = _animation_frames_from_asset(_FakeStorage(root), asset)

        self.assertEqual(frames, ["/images/project/processed/record/frame_000.png"])

    def test_animation_endpoint_uses_full_source_grid_previews_when_marked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frame_dir = root / "project" / "processed" / "record"
            frame_dir.mkdir(parents=True)
            (frame_dir / "animation.json").write_text(
                json.dumps(
                    {
                        "frames": ["project/processed/record/frame_000.png"],
                        "preview_frames": ["project/processed/record/preview_000.png"],
                        "preview_frame_kind": "source_grid_full_frame",
                        "frame_delay_ms": 120,
                    }
                ),
                encoding="utf-8",
            )
            asset = SimpleNamespace(source_path="project/processed/record/frame_000.png")

            frames, _, _ = _animation_frames_from_asset(_FakeStorage(root), asset)

        self.assertEqual(frames, ["/images/project/processed/record/preview_000.png"])

    def test_preview_frame_preserves_entire_frame_canvas(self) -> None:
        service = GenerationService.__new__(GenerationService)
        frame = Image.new("RGBA", (10, 8), (0, 0, 0, 0))
        frame.putpixel((5, 4), (255, 0, 0, 255))

        preview = service._prepare_preview_frame(frame)

        self.assertEqual(preview.size, (14, 12))
        self.assertEqual(preview.getpixel((7, 6)), (255, 0, 0, 255))

    def test_frame_extractor_detects_actual_grid_when_model_ignores_requested_grid(self) -> None:
        image = Image.new("RGBA", (400, 400), (245, 246, 242, 255))
        colors = [
            (220, 80, 70, 255),
            (80, 170, 90, 255),
            (80, 120, 220, 255),
            (220, 170, 60, 255),
        ]
        boxes = [
            (55, 55, 145, 145),
            (255, 55, 345, 145),
            (55, 255, 145, 345),
            (255, 255, 345, 345),
        ]
        for box, color in zip(boxes, colors, strict=True):
            for y in range(box[1], box[3]):
                for x in range(box[0], box[2]):
                    image.putpixel((x, y), color)

        context = PostProcessContext(
            image=image,
            asset_subtype=AssetSubtype.ANIMATED_SPRITESHEET,
            sheet_rows=4,
            sheet_cols=4,
        )

        result = asyncio.run(FrameExtractorStep().run(context))

        self.assertEqual(result.sheet_rows, 2)
        self.assertEqual(result.sheet_cols, 2)
        self.assertEqual(len(result.extracted_frames), 4)
        self.assertEqual([frame.size for frame in result.extracted_frames], [(200, 200)] * 4)

    def test_frame_extractor_does_not_collapse_multiframe_sheet_to_one_preview(self) -> None:
        image = Image.new("RGBA", (400, 400), (180, 220, 230, 255))
        for y in range(0, 400, 20):
            for x in range(400):
                image.putpixel((x, y), (120, 170, 190, 255))
        for x in range(0, 400, 20):
            for y in range(400):
                image.putpixel((x, y), (120, 170, 190, 255))

        context = PostProcessContext(
            image=image,
            asset_subtype=AssetSubtype.ANIMATED_SPRITESHEET,
            sheet_rows=4,
            sheet_cols=4,
        )

        result = asyncio.run(FrameExtractorStep().run(context))

        self.assertEqual(result.sheet_rows, 4)
        self.assertEqual(result.sheet_cols, 4)
        self.assertEqual(len(result.extracted_frames), 16)
