from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ArtStyle(str, Enum):
    PIXEL = "pixel"
    HAND_DRAWN = "hand_drawn"
    CARTOON = "cartoon"
    REALISTIC = "realistic"
    CUSTOM = "custom"


class Perspective(str, Enum):
    TOP_DOWN = "top_down"
    SIDE_SCROLLER = "side_scroller"
    ISOMETRIC = "isometric"


class AssetType(str, Enum):
    CHARACTER = "character"
    TILE = "tile"
    PROP = "prop"
    UI = "ui"
    EFFECT = "effect"


class AssetSubtype(str, Enum):
    STATIC_IMAGE = "static_image"
    ANIMATED_SPRITESHEET = "animated_spritesheet"


class AssetStatus(str, Enum):
    DRAFT = "draft"
    SELECTED = "selected"
    EXPORTED = "exported"
    DISCARDED = "discarded"


class ExportFormat(str, Enum):
    PNG_SINGLE = "png_single"
    SPRITESHEET_PNG_JSON = "spritesheet_png_json"
    TILESET_PNG_JSON = "tileset_png_json"


def new_id() -> str:
    return str(uuid.uuid4())


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    style_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("style_profiles.id", ondelete="SET NULL"), nullable=True
    )

    style: Mapped[StyleProfile | None] = relationship(foreign_keys=[style_id])
    assets: Mapped[list[Asset]] = relationship(back_populates="project", cascade="all, delete-orphan")


class StyleProfile(Base, TimestampMixin):
    __tablename__ = "style_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    art_style: Mapped[ArtStyle] = mapped_column(SAEnum(ArtStyle), nullable=False)
    color_palette: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    reference_image_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_size: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False, default=dict)
    perspective: Mapped[Perspective] = mapped_column(SAEnum(Perspective), nullable=False)
    extra_params: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    is_preset: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    generation_records: Mapped[list[GenerationRecord]] = relationship(back_populates="style")


class Asset(Base, TimestampMixin):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_type: Mapped[AssetType] = mapped_column(SAEnum(AssetType), nullable=False)
    status: Mapped[AssetStatus] = mapped_column(
        SAEnum(AssetStatus), nullable=False, default=AssetStatus.DRAFT
    )
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    thumbnail_path: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    project: Mapped[Project] = relationship(back_populates="assets")
    generation_records: Mapped[list[GenerationRecord]] = relationship(back_populates="asset")


class GenerationRecord(Base):
    __tablename__ = "generation_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    asset_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )
    user_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    optimized_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    style_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("style_profiles.id", ondelete="RESTRICT"), nullable=True
    )
    asset_type: Mapped[AssetType] = mapped_column(SAEnum(AssetType), nullable=False)
    asset_subtype: Mapped[AssetSubtype | None] = mapped_column(SAEnum(AssetSubtype), nullable=True)
    api_provider: Mapped[str] = mapped_column(String(100), nullable=False)
    api_model: Mapped[str] = mapped_column(String(100), nullable=False)
    api_params: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    seed: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reference_image_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    postprocess_log: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    asset: Mapped[Asset | None] = relationship(back_populates="generation_records")
    style: Mapped[StyleProfile] = relationship(back_populates="generation_records")


class ExportRecord(Base):
    __tablename__ = "export_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    asset_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    export_format: Mapped[ExportFormat] = mapped_column(SAEnum(ExportFormat), nullable=False)
    export_path: Mapped[str] = mapped_column(Text, nullable=False)
    export_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False, default=dict)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
