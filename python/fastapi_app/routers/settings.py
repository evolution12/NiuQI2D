from __future__ import annotations

from fastapi import APIRouter

from ..schemas import ApiTestResponse, SettingsResponse, UpdateSettingsRequest
from ..services.config_service import ConfigService

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsResponse)
async def get_app_settings() -> SettingsResponse:
    return ConfigService().response()


@router.put("", response_model=SettingsResponse)
async def update_app_settings(body: UpdateSettingsRequest) -> SettingsResponse:
    return await ConfigService().update(body)


@router.post("/test-image-api", response_model=ApiTestResponse)
async def test_image_api() -> ApiTestResponse:
    return await ConfigService().test_image_api()


@router.post("/test-text-api", response_model=ApiTestResponse)
async def test_text_api() -> ApiTestResponse:
    return await ConfigService().test_text_api()
