from __future__ import annotations

import json
import time
from typing import Any

from fastapi import APIRouter

from ..config import get_settings
from ..exceptions import InvalidParamError
from ..schemas import ApiTestResponse, SettingsResponse, TestImageApiRequest, TestTextApiRequest, UpdateSettingsRequest

router = APIRouter(prefix="/settings", tags=["settings"])


def _build_settings_response() -> SettingsResponse:
    s = get_settings()
    return SettingsResponse(
        image_api_provider=s.image_api_provider,
        image_api_key_set=bool(s.image_api_key),
        image_api_model=s.image_api_model,
        text_api_provider=s.text_api_provider,
        text_api_key_set=bool(s.text_api_key),
        text_api_model=s.text_api_model,
        preview_image_model=s.preview_image_model,
        quality_image_model=s.quality_image_model,
        volcengine_access_key_set=bool(s.volcengine_access_key),
        volcengine_req_key=s.volcengine_req_key,
        doubao_api_key_set=bool(s.doubao_api_key),
        doubao_model=s.doubao_model,
        default_style_id=None,
        default_export_path="",
    )


def _persist_settings(updates: dict[str, Any]) -> None:
    settings = get_settings()
    config_path = settings.config_path
    existing: dict[str, Any] = {}
    if config_path.exists():
        existing = json.loads(config_path.read_text(encoding="utf-8"))
    existing.update(updates)
    config_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")


@router.get("", response_model=SettingsResponse)
async def get_settings_api() -> SettingsResponse:
    return _build_settings_response()


@router.put("", response_model=SettingsResponse)
async def update_settings(body: UpdateSettingsRequest) -> SettingsResponse:
    updates: dict[str, Any] = {}
    for field in body.model_fields:
        value = getattr(body, field, None)
        if value is not None:
            updates[field] = value

    if updates:
        _persist_settings(updates)
        get_settings.cache_clear()

    return _build_settings_response()


@router.post("/test-image-api", response_model=ApiTestResponse)
async def test_image_api(body: TestImageApiRequest) -> ApiTestResponse:
    s = get_settings()
    provider = body.provider
    if provider == "openai":
        return await _test_openai(body.api_key or s.image_api_key, body.model or s.image_api_model)
    if provider == "volcengine":
        return await _test_volcengine(
            body.volcengine_access_key or s.volcengine_access_key,
            body.volcengine_secret_key or s.volcengine_secret_key,
            body.volcengine_req_key or s.volcengine_req_key,
        )
    if provider == "doubao":
        return await _test_doubao(body.doubao_api_key or s.doubao_api_key, body.doubao_model or s.doubao_model)
    return ApiTestResponse(success=False, message=f"不支持的供应商: {provider}", latency_ms=None)


@router.post("/test-text-api", response_model=ApiTestResponse)
async def test_text_api(body: TestTextApiRequest) -> ApiTestResponse:
    s = get_settings()
    provider = body.provider
    if provider == "openai":
        return await _test_openai_text(body.api_key or s.text_api_key, body.model or s.text_api_model)
    if provider == "deepseek":
        return await _test_deepseek_text(body.api_key or s.text_api_key, body.model or s.text_api_model)
    return ApiTestResponse(success=False, message=f"不支持的供应商: {provider}", latency_ms=None)


async def _test_openai(api_key: str, model: str) -> ApiTestResponse:
    import httpx

    if not api_key:
        return ApiTestResponse(success=False, message="未设置 API Key", latency_ms=None)

    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
        latency = int((time.perf_counter() - start) * 1000)
        if resp.status_code == 200:
            return ApiTestResponse(success=True, message="OpenAI 连接正常", latency_ms=latency)
        return ApiTestResponse(success=False, message=f"HTTP {resp.status_code}", latency_ms=latency)
    except Exception as e:
        return ApiTestResponse(success=False, message=str(e)[:100], latency_ms=None)


async def _test_openai_text(api_key: str, model: str) -> ApiTestResponse:
    import httpx

    if not api_key:
        return ApiTestResponse(success=False, message="未设置 API Key", latency_ms=None)

    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5},
            )
        latency = int((time.perf_counter() - start) * 1000)
        if resp.status_code == 200:
            return ApiTestResponse(success=True, message="OpenAI Text API 连接正常", latency_ms=latency)
        return ApiTestResponse(success=False, message=f"HTTP {resp.status_code}", latency_ms=latency)
    except Exception as e:
        return ApiTestResponse(success=False, message=str(e)[:100], latency_ms=None)


async def _test_volcengine(access_key: str, secret_key: str, req_key: str) -> ApiTestResponse:
    import httpx

    if not access_key or not secret_key:
        return ApiTestResponse(success=False, message="未设置火山引擎 AK/SK", latency_ms=None)

    from ..providers.volcengine_provider import VolcengineProvider

    provider = VolcengineProvider(access_key=access_key, secret_key=secret_key, req_key=req_key)

    start = time.perf_counter()
    try:
        payload = {
            "req_key": req_key,
            "prompt": "test",
            "width": 512,
            "height": 512,
            "return_url": False,
            "logo_info": {"add_logo": False},
        }
        headers = provider._build_headers(payload)
        body_str = provider._serialize_body(payload)

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://visual.volcengineapi.com",
                headers=headers,
                content=body_str,
            )
        latency = int((time.perf_counter() - start) * 1000)

        if resp.status_code == 200:
            data = resp.json()
            code = data.get("code", -1)
            if code == 10000 or code == -1:
                return ApiTestResponse(success=True, message="火山引擎连接正常", latency_ms=latency)
            return ApiTestResponse(success=False, message=f"业务错误: code={code}", latency_ms=latency)
        return ApiTestResponse(success=False, message=f"HTTP {resp.status_code}", latency_ms=latency)
    except Exception as e:
        return ApiTestResponse(success=False, message=str(e)[:100], latency_ms=None)


async def _test_deepseek_text(api_key: str, model: str) -> ApiTestResponse:
    import httpx

    if not api_key:
        return ApiTestResponse(success=False, message="未设置 DeepSeek API Key", latency_ms=None)

    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.deepseek.com/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5},
            )
        latency = int((time.perf_counter() - start) * 1000)
        if resp.status_code == 200:
            return ApiTestResponse(success=True, message="DeepSeek API 连接正常", latency_ms=latency)
        if resp.status_code in (401, 403):
            return ApiTestResponse(success=False, message="API Key 无效", latency_ms=latency)
        body = resp.text[:200]
        return ApiTestResponse(success=False, message=f"HTTP {resp.status_code}: {body}", latency_ms=latency)
    except Exception as e:
        return ApiTestResponse(success=False, message=str(e)[:100], latency_ms=None)


async def _test_doubao(api_key: str, model: str) -> ApiTestResponse:
    import httpx

    if not api_key:
        return ApiTestResponse(success=False, message="未设置豆包 API Key", latency_ms=None)

    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            # 先验证 API Key 有效性：列出模型
            resp = await client.get(
                "https://ark.cn-beijing.volces.com/api/v3/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
        latency = int((time.perf_counter() - start) * 1000)

        if resp.status_code in (401, 403):
            return ApiTestResponse(success=False, message="API Key 无效", latency_ms=latency)
        if resp.status_code != 200:
            return ApiTestResponse(success=False, message=f"API 返回异常: HTTP {resp.status_code}", latency_ms=latency)

        # 检查指定模型是否存在
        data = resp.json()
        model_ids = [m.get("id", "") for m in data.get("data", [])]
        if model not in model_ids:
            available = [m for m in model_ids if "seedream" in m or "image" in m.lower()]
            hint = f"，可用的图像模型: {', '.join(available[:5])}" if available else ""
            return ApiTestResponse(success=False, message=f"模型 {model} 不存在{hint}", latency_ms=latency)

        return ApiTestResponse(success=True, message="豆包 Ark API 连接正常", latency_ms=latency)
    except Exception as e:
        return ApiTestResponse(success=False, message=str(e)[:100], latency_ms=None)
