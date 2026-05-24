from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

import httpx

from ..config import Settings, get_settings
from ..schemas import ApiTestResponse, SettingsResponse, TestImageApiRequest, TestTextApiRequest, UpdateSettingsRequest

OPENAI_MODELS_URL = "https://api.openai.com/v1/models"
OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"
DEEPSEEK_CHAT_COMPLETIONS_URL = "https://api.deepseek.com/chat/completions"
DOUBAO_CHAT_COMPLETIONS_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
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

    async def test_image_api(self, body: TestImageApiRequest | None = None) -> ApiTestResponse:
        provider = body.provider if body and body.provider else self.settings.image_api_provider
        if provider == "doubao":
            api_key = body.doubao_api_key if body and body.doubao_api_key else self.settings.doubao_api_key
            return self._test_local_keys("doubao", bool(api_key))
        if provider == "openai":
            api_key = body.api_key if body and body.api_key else self.settings.image_api_key
            model = body.model if body and body.model else self.settings.image_api_model
            return await self._test_openai_models(api_key, model)
        if provider == "volcengine":
            access_key = body.volcengine_access_key if body and body.volcengine_access_key else self.settings.volcengine_access_key
            secret_key = body.volcengine_secret_key if body and body.volcengine_secret_key else self.settings.volcengine_secret_key
            return self._test_local_keys("volcengine", bool(access_key and secret_key))
        return ApiTestResponse(success=False, message=f"暂不支持供应商 {provider}", latency_ms=0)

    async def test_text_api(self, body: TestTextApiRequest | None = None) -> ApiTestResponse:
        provider = body.provider if body and body.provider else self.settings.text_api_provider
        api_key = body.api_key if body and body.api_key else self.settings.text_api_key
        model = body.model if body and body.model else self.settings.text_api_model
        return await self._test_chat_provider(provider, api_key, model)

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

    async def _test_openai_models(self, api_key: str, model: str) -> ApiTestResponse:
        started = time.perf_counter()
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

    async def _test_chat_provider(self, provider: str, api_key: str, model: str) -> ApiTestResponse:
        started = time.perf_counter()
        if not api_key:
            return ApiTestResponse(success=False, message="API Key 未配置", latency_ms=0)
        if not model:
            return ApiTestResponse(success=False, message="模型未配置", latency_ms=0)

        urls = {
            "openai": OPENAI_CHAT_COMPLETIONS_URL,
            "deepseek": DEEPSEEK_CHAT_COMPLETIONS_URL,
            "doubao": DOUBAO_CHAT_COMPLETIONS_URL,
        }
        url = urls.get(provider)
        if not url:
            return ApiTestResponse(success=False, message=f"暂不支持供应商 {provider}", latency_ms=0)

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 1,
            "temperature": 0,
        }
        try:
            async with httpx.AsyncClient(timeout=API_TEST_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
        except httpx.TimeoutException:
            return ApiTestResponse(success=False, message="网络超时", latency_ms=self._latency(started))
        except httpx.HTTPError:
            return ApiTestResponse(success=False, message="API 连接失败", latency_ms=self._latency(started))

        latency_ms = self._latency(started)
        if response.status_code in (401, 403):
            return ApiTestResponse(success=False, message="API Key 无效或模型无权限", latency_ms=latency_ms)
        if response.status_code >= 400:
            return ApiTestResponse(
                success=False,
                message=f"API 返回错误: {response.text[:200]}",
                latency_ms=latency_ms,
            )
        return ApiTestResponse(success=True, message=f"连接成功，模型 {model} 可用于配置", latency_ms=latency_ms)

    def _test_local_keys(self, provider: str, configured: bool) -> ApiTestResponse:
        if not configured:
            return ApiTestResponse(success=False, message="API Key 未配置", latency_ms=0)
        return ApiTestResponse(success=True, message=f"{provider} 密钥已填写，生成时将验证服务响应", latency_ms=0)

    def _latency(self, started: float) -> int:
        return int((time.perf_counter() - started) * 1000)
