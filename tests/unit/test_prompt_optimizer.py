from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PYTHON_DIR = Path(__file__).resolve().parents[2] / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from fastapi_app.services.prompt_optimizer import PromptOptimizer, SYSTEM_PROMPT


class _FakeResponse:
    status_code = 200
    text = ""

    def json(self) -> dict[str, object]:
        return {"choices": [{"message": {"content": "中文优化提示词"}}]}


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
    async def test_optimizer_system_prompt_requires_chinese_output(self) -> None:
        optimizer = PromptOptimizer(api_provider="openai", api_key="test-key", api_model="test-model")

        with patch("fastapi_app.services.prompt_optimizer.httpx.AsyncClient", _FakeAsyncClient):
            result = await optimizer._optimize_with_provider("template prompt")

        self.assertEqual(result, "中文优化提示词")
        self.assertIn("仅输出中文", SYSTEM_PROMPT)
        self.assertNotIn("Output English only", SYSTEM_PROMPT)

        payload = _FakeAsyncClient.payload
        self.assertIsNotNone(payload)
        messages = payload["messages"]  # type: ignore[index]
        self.assertEqual(messages[0]["content"], SYSTEM_PROMPT)  # type: ignore[index]


if __name__ == "__main__":
    unittest.main()
