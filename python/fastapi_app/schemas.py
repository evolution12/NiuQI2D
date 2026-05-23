from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .models import ArtStyle, AssetStatus, AssetSubtype, AssetType, ExportFormat, Perspective


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class PostProcessLog(BaseModel):
    step: str
    executed: bool
    params: dict[str, Any] = Field(default_factory=dict)
    duration_ms: int


class ProjectCreateRequest(BaseModel):
    name: str
    style_id: str | None = None


class ProjectUpdateRequest(BaseModel):
    name: str | None = None
    style_id: str | None = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    style_id: str | None
    created_at: datetime
    updated_at: datetime


class StyleProfileCreateRequest(BaseModel):
    name: str
    art_style: ArtStyle
    color_palette: list[str] | None = None
    reference_image_path: str | None = None
    default_size: dict[str, int] = Field(default_factory=lambda: {"w": 16, "h": 16})
    perspective: Perspective = Perspective.TOP_DOWN
    extra_params: dict[str, Any] | None = None


class StyleProfileUpdateRequest(BaseModel):
    name: str | None = None
    art_style: ArtStyle | None = None
    color_palette: list[str] | None = None
    reference_image_path: str | None = None
    default_size: dict[str, int] | None = None
    perspective: Perspective | None = None
    extra_params: dict[str, Any] | None = None


class StyleProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    art_style: ArtStyle
    color_palette: list[str] | None
    reference_image_path: str | None
    default_size: dict[str, int]
    perspective: Perspective
    extra_params: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


class AssetCreateRequest(BaseModel):
    project_id: str
    name: str
    asset_type: AssetType
    status: AssetStatus = AssetStatus.DRAFT
    source_path: str
    thumbnail_path: str
    tags: list[str] = Field(default_factory=list)


class AssetUpdateRequest(BaseModel):
    name: str | None = None
    asset_type: AssetType | None = None
    status: AssetStatus | None = None
    source_path: str | None = None
    thumbnail_path: str | None = None
    tags: list[str] | None = None


class AssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    name: str
    asset_type: AssetType
    status: AssetStatus
    source_path: str
    thumbnail_path: str
    tags: list[str]
    created_at: datetime
    updated_at: datetime


class GenerationRecordCreateRequest(BaseModel):
    asset_id: str | None = None
    user_prompt: str
    optimized_prompt: str
    style_id: str
    asset_type: AssetType
    asset_subtype: AssetSubtype | None = None
    api_provider: str
    api_model: str
    api_params: dict[str, Any] = Field(default_factory=dict)
    seed: str | None = None
    reference_image_path: str | None = None
    postprocess_log: list[PostProcessLog] = Field(default_factory=list)


class GenerationRecordUpdateRequest(BaseModel):
    asset_id: str | None = None
    user_prompt: str | None = None
    optimized_prompt: str | None = None
    style_id: str | None = None
    asset_type: AssetType | None = None
    asset_subtype: AssetSubtype | None = None
    api_provider: str | None = None
    api_model: str | None = None
    api_params: dict[str, Any] | None = None
    seed: str | None = None
    reference_image_path: str | None = None
    postprocess_log: list[PostProcessLog] | None = None


class GenerationRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    asset_id: str | None
    user_prompt: str
    optimized_prompt: str
    style_id: str
    asset_type: AssetType
    asset_subtype: AssetSubtype | None
    api_provider: str
    api_model: str
    api_params: dict[str, Any]
    seed: str | None
    reference_image_path: str | None
    postprocess_log: list[PostProcessLog]
    created_at: datetime


class ExportRecordCreateRequest(BaseModel):
    asset_ids: list[str]
    export_format: ExportFormat
    export_path: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    file_size: int = 0


class ExportRecordUpdateRequest(BaseModel):
    asset_ids: list[str] | None = None
    export_format: ExportFormat | None = None
    export_path: str | None = None
    metadata: dict[str, Any] | None = None
    file_size: int | None = None


class ExportRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    asset_ids: list[str]
    export_format: ExportFormat
    export_path: str
    metadata: dict[str, Any] = Field(validation_alias="export_metadata", serialization_alias="metadata")
    file_size: int
    created_at: datetime


class UploadResponse(BaseModel):
    path: str
    url: str
    filename: str
    size: int
    content_type: str
