from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class Settings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000
    data_dir: str = Field(default="~/.niuqi2d/data")
    db_path: str = ""
    image_api_provider: str = "openai"
    image_api_key: str = ""
    image_api_model: str = "gpt-image-1"
    text_api_provider: str = "openai"
    text_api_key: str = ""
    text_api_model: str = "gpt-4o-mini"
    preview_image_model: str = "dall-e-3"
    quality_image_model: str = "gpt-image-1"
    volcengine_access_key: str = ""
    volcengine_secret_key: str = ""
    volcengine_req_key: str = "high_aes_general_v21"
    doubao_api_key: str = ""
    doubao_model: str = "doubao-seedream-4-5-251128"
    default_style_id: str | None = None
    default_export_path: str = ""

    @property
    def resolved_data_dir(self) -> Path:
        return Path(self.data_dir).expanduser().resolve()

    @property
    def resolved_db_path(self) -> Path:
        if self.db_path:
            return Path(self.db_path).expanduser().resolve()
        return self.resolved_data_dir / "niuqi2d.db"

    @property
    def config_path(self) -> Path:
        return self.resolved_data_dir / "config.json"


def _read_config_file(data_dir: Path) -> dict[str, Any]:
    config_path = data_dir / "config.json"
    if not config_path.exists():
        return {}
    with config_path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    return data if isinstance(data, dict) else {}


def _env_value(name: str) -> str | None:
    value = os.getenv(name)
    return value if value not in (None, "") else None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    data_dir = Path(_env_value("NIUQI2D_DATA_DIR") or "~/.niuqi2d/data").expanduser().resolve()
    file_config = _read_config_file(data_dir)
    values: dict[str, Any] = {
        "data_dir": str(data_dir),
        **file_config,
    }

    env_map = {
        "host": "NIUQI2D_HOST",
        "port": "NIUQI2D_PORT",
        "db_path": "NIUQI2D_DB_PATH",
        "image_api_provider": "NIUQI2D_IMAGE_API_PROVIDER",
        "image_api_key": "NIUQI2D_IMAGE_API_KEY",
        "image_api_model": "NIUQI2D_IMAGE_API_MODEL",
        "text_api_provider": "NIUQI2D_TEXT_API_PROVIDER",
        "text_api_key": "NIUQI2D_TEXT_API_KEY",
        "text_api_model": "NIUQI2D_TEXT_API_MODEL",
        "preview_image_model": "NIUQI2D_PREVIEW_IMAGE_MODEL",
        "quality_image_model": "NIUQI2D_QUALITY_IMAGE_MODEL",
        "volcengine_access_key": "NIUQI2D_VOLCENGINE_AK",
        "volcengine_secret_key": "NIUQI2D_VOLCENGINE_SK",
        "volcengine_req_key": "NIUQI2D_VOLCENGINE_REQ_KEY",
        "doubao_api_key": "NIUQI2D_DOUBAO_API_KEY",
        "doubao_model": "NIUQI2D_DOUBAO_MODEL",
        "default_style_id": "NIUQI2D_DEFAULT_STYLE_ID",
        "default_export_path": "NIUQI2D_DEFAULT_EXPORT_PATH",
    }
    for field_name, env_name in env_map.items():
        value = _env_value(env_name)
        if value is not None:
            values[field_name] = int(value) if field_name == "port" else value

    settings = Settings(**values)
    settings.resolved_data_dir.mkdir(parents=True, exist_ok=True)
    if not settings.config_path.exists():
        settings.config_path.write_text(
            json.dumps(
                {
                    "image_api_provider": settings.image_api_provider,
                    "image_api_key": settings.image_api_key,
                    "image_api_model": settings.image_api_model,
                    "text_api_provider": settings.text_api_provider,
                    "text_api_key": settings.text_api_key,
                    "text_api_model": settings.text_api_model,
                    "preview_image_model": settings.preview_image_model,
                    "quality_image_model": settings.quality_image_model,
                    "volcengine_access_key": settings.volcengine_access_key,
                    "volcengine_secret_key": settings.volcengine_secret_key,
                    "volcengine_req_key": settings.volcengine_req_key,
                    "doubao_api_key": settings.doubao_api_key,
                    "doubao_model": settings.doubao_model,
                    "default_style_id": settings.default_style_id,
                    "default_export_path": settings.default_export_path,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    return settings
