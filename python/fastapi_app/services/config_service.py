from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

import httpx

from ..config import Settings, get_settings
from ..schemas import ApiTestResponse, SettingsResponse, UpdateSettingsRequest

OPENAI_MODELS_URL = "https://api.openai.com/v1/models"
API_TEST_TIMEOUT_SECONDS = 10.0


class ConfigService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def response(self) -> SettingsResponse:
        return SettingsResponse(
            image_api_provider=self.settings.image_api_provider,
            image_api_key_set=bool(self.settings.image_api_key),
            image_api_model=self.settings.image_api_model,
            text_api_provider=self.settings.text_api_provider,
            text_api_key_set=bool(self.settings.text_api_key),
            text_api_model=self.settings.text_api_model,
            preview_image_model=self.settings.preview_image_model,
            quality_image_model=self.settings.quality_image_model,
            volcengine_access_key_set=bool(self.settings.volcengine_access_key),
            volcengine_req_key=self.settings.volcengine_req_key,
            doubao_api_key_set=bool(self.settings.doubao_api_key),
            doubao_model=self.settings.doubao_model,
            default_style_id=self.settings.default_style_id,
            default_export_path=self.settings.default_export_path,
        )

    async def update(self, body: UpdateSettingsRequest) -> SettingsResponse:
        current = self._settings_dict()
        updates = body.model_dump(mode="json", exclude_unset=True)
        current.update({key: value for key, value in updates.items() if value is not None})
        await asyncio.to_thread(self._write_config, self.settings.config_path, current)
        get_settings.cache_clear()
        self.settings = get_settings()
        return self.response()

    async def test_image_api(self) -> ApiTestResponse:
        return await self._test_provider(
            self.settings.image_api_provider,
            self.settings.image_api_key,
            self.settings.image_api_model,
        )

    async def test_text_api(self) -> ApiTestResponse:
        return await self._test_provider(
            self.settings.text_api_provider,
            self.settings.text_api_key,
            self.settings.text_api_model,
        )

    def _settings_dict(self) -> dict[str, Any]:
        keys = [
            "image_api_provider",
            "image_api_key",
            "image_api_model",
            "text_api_provider",
            "text_api_key",
            "text_api_model",
            "preview_image_model",
            "quality_image_model",
            "volcengine_access_key",
            "volcengine_secret_key",
            "volcengine_req_key",
            "doubao_api_key",
            "doubao_model",
            "default_style_id",
            "default_export_path",
        ]
        return {key: getattr(self.settings, key) for key in keys}

    def _write_config(self, path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    async def _test_provider(self, provider: str, api_key: str, model: str) -> ApiTestResponse:
        started = time.perf_counter()
        if provider != "openai":
            return ApiTestResponse(success=False, message=f"暂不支持供应商 {provider}", latency_ms=0)
        if not api_key:
            return ApiTestResponse(success=False, message="API Key 未配置", latency_ms=0)

        try:
            async with httpx.AsyncClient(timeout=API_TEST_TIMEOUT_SECONDS) as client:
                response = await client.get(
                    OPENAI_MODELS_URL,
                    headers={"Authorization": f"Bearer {api_key}"},
                )
        except httpx.TimeoutException:
            return ApiTestResponse(success=False, message="网络超时", latency_ms=self._latency(started))
        except httpx.HTTPError:
            return ApiTestResponse(success=False, message="API 连接失败", latency_ms=self._latency(started))

        latency_ms = self._latency(started)
        if response.status_code in (401, 403):
            return ApiTestResponse(success=False, message="API Key 无效", latency_ms=latency_ms)
        if response.status_code >= 400:
            return ApiTestResponse(success=False, message="API 返回错误", latency_ms=latency_ms)
        return ApiTestResponse(success=True, message=f"连接成功，模型 {model} 可用于配置", latency_ms=latency_ms)

    def _latency(self, started: float) -> int:
        return int((time.perf_counter() - started) * 1000)
