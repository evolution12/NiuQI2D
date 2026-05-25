from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PYTHON_DIR = Path(__file__).resolve().parents[2] / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from fastapi_app.models import AssetSubtype, AssetType
from fastapi_app.services.prompt_optimizer import PromptOptimizer, SYSTEM_PROMPT


class _FakeResponse:
    status_code = 200
    text = ""

    def json(self) -> dict[str, object]:
        return {"choices": [{"message": {"content": "optimized English prompt"}}]}


class _FakeAsyncClient:
    payload: dict[str, object] | None = None

    def __init__(self, *args: object, **kwargs: object) -> None:
        pass

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        pass

    async def post(self, *args: object, **kwargs: object) -> _FakeResponse:
        self.__class__.payload = kwargs["json"]
        return _FakeResponse()


class PromptOptimizerTest(unittest.IsolatedAsyncioTestCase):
    async def test_optimizer_system_prompt_requires_english_output(self) -> None:
        optimizer = PromptOptimizer(api_provider="openai", api_key="test-key", api_model="test-model")

        with patch("fastapi_app.services.prompt_optimizer.httpx.AsyncClient", _FakeAsyncClient):
            result = await optimizer._optimize_with_provider("template prompt")

        self.assertEqual(result, "optimized English prompt")
        self.assertIn("Output English only", SYSTEM_PROMPT)
        self.assertIn("minimal expansion strategy", SYSTEM_PROMPT)
        self.assertIn("Do not proactively add", SYSTEM_PROMPT)
        self.assertNotIn("仅输出中文", SYSTEM_PROMPT)

        payload = _FakeAsyncClient.payload
        self.assertIsNotNone(payload)
        messages = payload["messages"]  # type: ignore[index]
        self.assertEqual(messages[0]["content"], SYSTEM_PROMPT)  # type: ignore[index]
        self.assertEqual(payload["temperature"], 0.15)  # type: ignore[index]

    def test_template_prompts_include_control_constraints(self) -> None:
        optimizer = PromptOptimizer(api_provider="openai", api_key="test-key", api_model="test-model")

        character_prompt, character_template = optimizer._build_template_prompt(
            user_prompt="蓝色史莱姆",
            asset_type=AssetType.CHARACTER,
            asset_subtype=AssetSubtype.STATIC_IMAGE,
            style=None,
            reference_style_description=None,
            actions=None,
            direction_count=4,
            frame_count=3,
        )
        self.assertEqual(character_template, "character_static")
        self.assertIn("蓝色史莱姆", character_prompt)
        self.assertIn("do not invent extra character identity", character_prompt)
        self.assertIn("single subject", character_prompt)

        tile_prompt, tile_template = optimizer._build_template_prompt(
            user_prompt="草地",
            asset_type=AssetType.TILE,
            asset_subtype=None,
            style=None,
            reference_style_description=None,
            actions=None,
            direction_count=4,
            frame_count=3,
        )
        self.assertEqual(tile_template, "tile")
        self.assertIn("草地", tile_prompt)
        self.assertIn("do not invent extra objects", tile_prompt)
        self.assertIn("tileable surface only", tile_prompt)


if __name__ == "__main__":
    unittest.main()
