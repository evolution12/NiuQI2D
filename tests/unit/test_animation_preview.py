from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

PYTHON_DIR = Path(__file__).resolve().parents[2] / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from fastapi_app.routers.assets import _animation_frames_from_asset
from fastapi_app.services.generation_service import GenerationService


class _FakeStorage:
    def __init__(self, root: Path) -> None:
        self.root = root

    def _resolve_image_path(self, image_path: str) -> Path:
        return self.root / image_path


class AnimationPreviewTest(unittest.TestCase):
    def test_animation_endpoint_prefers_full_frames_over_cropped_previews(self) -> None:
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

    def test_preview_frame_preserves_entire_frame_canvas(self) -> None:
        service = GenerationService.__new__(GenerationService)
        frame = Image.new("RGBA", (10, 8), (0, 0, 0, 0))
        frame.putpixel((5, 4), (255, 0, 0, 255))

        preview = service._prepare_preview_frame(frame)

        self.assertEqual(preview.size, (14, 12))
        self.assertEqual(preview.getpixel((7, 6)), (255, 0, 0, 255))
