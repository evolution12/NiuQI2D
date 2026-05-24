from __future__ import annotations

import os
import sys
import tempfile
import unittest
import logging
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from PIL import Image

PYTHON_DIR = Path(__file__).resolve().parents[2] / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))


def _png_bytes(color: tuple[int, int, int, int]) -> bytes:
    image = Image.new("RGBA", (16, 16), color)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class FullFlowTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.tmp.name) / "data"
        self.export_dir = Path(self.tmp.name) / "exports"
        os.environ["NIUQI2D_DATA_DIR"] = str(self.data_dir)

        from fastapi.testclient import TestClient
        from fastapi_app.config import get_settings
        from fastapi_app.main import app

        get_settings.cache_clear()
        self.client = TestClient(app)
        self.client.__enter__()
        self.get_settings = get_settings

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        logging.shutdown()
        self.get_settings.cache_clear()
        os.environ.pop("NIUQI2D_DATA_DIR", None)
        self.tmp.cleanup()

    def test_generate_select_export_history_flow(self) -> None:
        from fastapi_app.providers.base import CostEstimate, GeneratedImage
        from fastapi_app.services.prompt_optimizer import PromptOptimizer

        class FakeProvider:
            provider_name = "fake"
            model = "fake-image-model"

            async def generate(
                self,
                prompt: str,
                size: tuple[int, int] = (1024, 1024),
                n: int = 1,
                transparent_background: bool = False,
                seed: str | None = None,
            ) -> list[GeneratedImage]:
                return [
                    GeneratedImage(
                        image_data=_png_bytes((40 + index, 120, 220, 255)),
                        seed=seed or f"seed-{index}",
                        revised_prompt=f"{prompt} #{index}",
                        size=(16, 16),
                        metadata={"index": index, "transparent": transparent_background},
                    )
                    for index in range(n)
                ]

            def estimate_cost(
                self,
                n: int = 1,
                size: tuple[int, int] = (1024, 1024),
                quality: str | None = None,
            ) -> CostEstimate:
                return CostEstimate(
                    provider=self.provider_name,
                    model=self.model,
                    image_count=n,
                    estimated_usd=0.0,
                )

        async def fake_optimize(self: PromptOptimizer, template_prompt: str) -> str:
            return f"optimized {template_prompt[:80]}"

        with (
            patch(
                "fastapi_app.services.image_generator.ImageGenerator._build_provider",
                return_value=FakeProvider(),
            ),
            patch(
                "fastapi_app.services.prompt_optimizer.PromptOptimizer._optimize_with_provider",
                fake_optimize,
            ),
        ):
            health = self.client.get("/health")
            self.assertEqual(health.status_code, 200)

            settings = self.client.put(
                "/api/v1/settings",
                json={
                    "image_api_key": "test-image-key",
                    "text_api_key": "test-text-key",
                    "preview_image_model": "fake-preview",
                    "quality_image_model": "fake-quality",
                    "default_export_path": str(self.export_dir),
                },
            )
            self.assertEqual(settings.status_code, 200, settings.text)
            self.assertTrue(settings.json()["image_api_key_set"])

            style = self.client.post(
                "/api/v1/styles",
                json={
                    "name": "Test Pixel",
                    "art_style": "pixel",
                    "default_size": {"w": 16, "h": 16},
                    "perspective": "top_down",
                },
            )
            self.assertEqual(style.status_code, 201, style.text)
            style_id = style.json()["id"]

            project = self.client.post(
                "/api/v1/projects",
                json={"name": "Integration Project", "style_id": style_id},
            )
            self.assertEqual(project.status_code, 201, project.text)
            project_id = project.json()["id"]

            generated = self.client.post(
                "/api/v1/generate/preview",
                json={
                    "project_id": project_id,
                    "style_id": style_id,
                    "user_prompt": "blue idle hero",
                    "asset_type": "character",
                    "asset_subtype": "static_image",
                    "target_size": [16, 16],
                    "candidate_count": 1,
                },
            )
            self.assertEqual(generated.status_code, 201, generated.text)
            records = generated.json()["records"]
            self.assertEqual(len(records), 1)
            self.assertIsNotNone(records[0]["image_url"])
            record_id = records[0]["id"]

            selected = self.client.post(
                f"/api/v1/generation/{record_id}/select",
                json={"name": "blue hero", "tags": ["hero"]},
            )
            self.assertEqual(selected.status_code, 200, selected.text)
            asset = selected.json()["asset"]
            self.assertEqual(asset["status"], "selected")
            asset_id = asset["id"]

            asset_list = self.client.get(f"/api/v1/assets?project_id={project_id}")
            self.assertEqual(asset_list.status_code, 200, asset_list.text)
            self.assertEqual(asset_list.json()["total"], 1)

            exported = self.client.post(
                "/api/v1/export",
                json={
                    "asset_ids": [asset_id],
                    "export_format": "png_single",
                    "export_path": str(self.export_dir),
                },
            )
            self.assertEqual(exported.status_code, 201, exported.text)
            exported_body = exported.json()
            self.assertEqual(exported_body["total_size"], exported_body["files"][0]["size"])
            self.assertTrue(Path(exported_body["files"][0]["path"]).exists())

            refreshed_asset = self.client.get(f"/api/v1/assets/{asset_id}")
            self.assertEqual(refreshed_asset.status_code, 200, refreshed_asset.text)
            self.assertEqual(refreshed_asset.json()["status"], "exported")

            history = self.client.get(f"/api/v1/export/history?project_id={project_id}")
            self.assertEqual(history.status_code, 200, history.text)
            self.assertEqual(len(history.json()), 1)
            self.assertEqual(history.json()[0]["id"], exported_body["export_id"])

            generation_history = self.client.get(f"/api/v1/generation?project_id={project_id}")
            self.assertEqual(generation_history.status_code, 200, generation_history.text)
            self.assertEqual(len(generation_history.json()), 1)


if __name__ == "__main__":
    unittest.main()
