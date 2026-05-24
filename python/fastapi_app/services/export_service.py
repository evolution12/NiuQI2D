from __future__ import annotations

import asyncio
import json
import math
import shutil
from pathlib import Path
from typing import Any

from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..crud.asset import AssetCRUD
from ..crud.export import ExportCRUD
from ..exceptions import InvalidParamError
from ..models import Asset, AssetStatus, ExportFormat, ExportRecord
from ..postprocess.spritesheet import SpriteSheetConfig
from ..postprocess.tileset import TilesetConfig
from ..schemas import (
    ExportFileInfo,
    ExportRecordCreateRequest,
    ExportRequest,
    ExportResponse,
)
from ..storage import StorageManager
from .export_algorithms import build_spritesheet_export, build_tileset_export


class ExportService:
    def __init__(self, session: AsyncSession, storage: StorageManager) -> None:
        self.session = session
        self.storage = storage
        self.asset_crud = AssetCRUD()
        self.export_crud = ExportCRUD()

    async def export_assets(self, body: ExportRequest) -> ExportResponse:
        assets = await self._load_assets(body.asset_ids)
        export_dir = self._resolve_export_dir(body.export_path)
        files = await asyncio.to_thread(self._write_export_files, body, assets, export_dir)
        total_size = sum(file.size for file in files)
        record = await self.export_crud.create(
            self.session,
            ExportRecordCreateRequest(
                asset_ids=[asset.id for asset in assets],
                export_format=body.export_format,
                export_path=str(export_dir),
                metadata={
                    "project_id": assets[0].project_id,
                    "files": [file.model_dump(mode="json") for file in files],
                },
                file_size=total_size,
            ),
        )
        for asset in assets:
            await self.asset_crud.update(self.session, asset.id, {"status": AssetStatus.EXPORTED})
        return ExportResponse(export_id=record.id, files=files, total_size=total_size)

    async def list_history(self, project_id: str | None) -> list[ExportRecord]:
        records, _total = await self.export_crud.list(
            self.session,
            page=1,
            page_size=10_000,
            statement=select(ExportRecord).order_by(ExportRecord.created_at.desc()),
        )
        if project_id is None:
            return records

        filtered = []
        for record in records:
            metadata_project_id = record.export_metadata.get("project_id")
            if metadata_project_id == project_id:
                filtered.append(record)
                continue
            if await self._record_has_project_asset(record, project_id):
                filtered.append(record)
        return filtered

    async def get_record(self, export_id: str) -> ExportRecord:
        return await self.export_crud.get(self.session, export_id)

    async def _load_assets(self, asset_ids: list[str]) -> list[Asset]:
        if not asset_ids:
            raise InvalidParamError("导出至少需要选择 1 个资产")
        assets = [await self.asset_crud.get(self.session, asset_id) for asset_id in asset_ids]
        project_ids = {asset.project_id for asset in assets}
        if len(project_ids) > 1:
            raise InvalidParamError("一次导出只能包含同一项目的资产")
        return assets

    async def _record_has_project_asset(self, record: ExportRecord, project_id: str) -> bool:
        for asset_id in record.asset_ids:
            asset = await self.session.get(Asset, asset_id)
            if asset is not None and asset.project_id == project_id:
                return True
        return False

    def _resolve_export_dir(self, export_path: str) -> Path:
        if not export_path.strip():
            raise InvalidParamError("导出路径不能为空")
        path = Path(export_path).expanduser()
        if path.suffix:
            path = path.parent
        return path.resolve()

    def _write_export_files(
        self,
        body: ExportRequest,
        assets: list[Asset],
        export_dir: Path,
    ) -> list[ExportFileInfo]:
        export_dir.mkdir(parents=True, exist_ok=True)
        if body.export_format == ExportFormat.PNG_SINGLE:
            return self._write_png_single(assets, export_dir)
        if body.export_format == ExportFormat.SPRITESHEET_PNG_JSON:
            return self._write_spritesheet(body, assets, export_dir)
        if body.export_format == ExportFormat.TILESET_PNG_JSON:
            return self._write_tileset(body, assets, export_dir)
        raise InvalidParamError(f"暂不支持导出格式 {body.export_format}")

    def _write_png_single(self, assets: list[Asset], export_dir: Path) -> list[ExportFileInfo]:
        files: list[ExportFileInfo] = []
        used_names: set[str] = set()
        for index, asset in enumerate(assets):
            source = self.storage._resolve_image_path(asset.source_path)
            if not source.exists():
                raise InvalidParamError(f"资产 {asset.id} 源图片不存在")
            filename = self._unique_filename(self._safe_stem(asset.name) + ".png", used_names, index)
            target = export_dir / filename
            shutil.copyfile(source, target)
            files.append(self._file_info(target))
        return files

    def _write_spritesheet(
        self,
        body: ExportRequest,
        assets: list[Asset],
        export_dir: Path,
    ) -> list[ExportFileInfo]:
        frames = self._load_images(assets)
        frame_size = frames[0].size

        # Read animation layout from the asset's manifest
        layout = self._read_animation_layout(assets[0])
        actions = layout["actions"]
        directions = layout["directions"]
        frames_per_action = layout["frames_per_action"]
        total_expected = len(actions) * len(directions) * frames_per_action

        # Build spritesheet grid matching animation layout
        columns = frames_per_action
        rows = len(actions) * len(directions)

        # If loaded frames don't match expected layout, fall back to auto layout
        if len(frames) != total_expected:
            columns = self._spritesheet_columns(body.sheet_layout, len(frames))
            rows = math.ceil(len(frames) / columns)
            actions = ["default"]
            directions = ["front"]
            frames_per_action = len(frames)

        result = build_spritesheet_export(
            frames=frames,
            config=SpriteSheetConfig(
                frame_size=frame_size,
                columns=columns,
                rows=rows,
                padding=body.sheet_padding,
                margin=body.sheet_margin,
            ),
            image_filename="spritesheet.png",
            naming_template="{action}_{direction}_{frame}",
            actions=actions,
            directions=directions,
            frames_per_action=frames_per_action,
            generation={"asset_ids": [asset.id for asset in assets]},
        )
        out_dir = export_dir / "spritesheet"
        out_dir.mkdir(parents=True, exist_ok=True)
        png_path = out_dir / "spritesheet.png"
        json_path = out_dir / "spritesheet.json"
        png_path.write_bytes(result.png_data)
        json_path.write_bytes(result.json_data)
        return [self._file_info(png_path), self._file_info(json_path)]

    def _read_animation_layout(self, asset: Asset) -> dict[str, object]:
        """Read direction/action/frame layout from the asset's animation manifest."""
        default = {"actions": ["default"], "directions": ["front"], "frames_per_action": 1}

        source = self.storage._resolve_image_path(asset.source_path)
        manifest_path = source.parent / "animation.json"
        if not manifest_path.exists():
            return default

        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return default
        if not isinstance(data, dict):
            return default

        sheet_rows = int(data.get("sheet_rows", 1))
        sheet_cols = int(data.get("sheet_cols", 1))
        frames_data = data.get("frames")
        total = len(frames_data) if isinstance(frames_data, list) else sheet_rows * sheet_cols

        actions_data = data.get("actions")
        if not isinstance(actions_data, dict):
            return default

        # Extract action names (excluding "_all" variants)
        action_names = sorted(k for k in actions_data if isinstance(k, str) and not k.endswith("_all"))
        if not action_names:
            return default

        direction_count = max(1, sheet_rows // len(action_names)) if len(action_names) > 0 else 1
        frame_count = max(1, sheet_cols)

        directions: list[str]
        if direction_count == 1:
            directions = ["front"]
        elif direction_count == 2:
            directions = ["left", "right"]
        elif direction_count == 4:
            directions = ["front", "back", "left", "right"]
        elif direction_count == 8:
            directions = ["front", "front-right", "right", "back-right", "back", "back-left", "left", "front-left"]
        else:
            directions = [f"dir_{i}" for i in range(direction_count)]

        return {
            "actions": action_names,
            "directions": directions,
            "frames_per_action": frame_count,
        }

    def _write_tileset(
        self,
        body: ExportRequest,
        assets: list[Asset],
        export_dir: Path,
    ) -> list[ExportFileInfo]:
        if body.tileset_columns <= 0:
            raise InvalidParamError("tileset_columns 必须为正整数")
        tiles = self._load_images(assets)
        tile_size = body.tile_size or (64, 64)

        # Read terrain type from each asset's generation params or tags
        tile_types: list[str] = []
        for asset in assets:
            tile_type = self._read_tile_type(asset)
            tile_types.append(tile_type)

        result = build_tileset_export(
            tiles=tiles,
            config=TilesetConfig(
                tile_size=tile_size,
                columns=body.tileset_columns,
                spacing=body.tileset_spacing,
                margin=body.tileset_margin,
            ),
            image_filename="tileset.png",
            tile_types=tile_types,
            generation={"asset_ids": [asset.id for asset in assets]},
        )
        out_dir = export_dir / "tileset"
        out_dir.mkdir(parents=True, exist_ok=True)
        png_path = out_dir / "tileset.png"
        json_path = out_dir / "tileset.json"
        png_path.write_bytes(result.png_data)
        json_path.write_bytes(result.json_data)
        return [self._file_info(png_path), self._file_info(json_path)]

    def _read_tile_type(self, asset: Asset) -> str:
        """Read terrain type from asset. Uses terrain_type tag if set, otherwise the asset name."""
        # Try to get terrain_type from tags
        if asset.tags:
            for tag in asset.tags:
                if tag.startswith("terrain:"):
                    return tag.removeprefix("terrain:")
        # Fall back to asset name
        return self._safe_stem(asset.name)

    def _load_images(self, assets: list[Asset]) -> list[Image.Image]:
        images = []
        for asset in assets:
            frame_paths = self._animation_frame_paths(asset) or [asset.source_path]
            for frame_path in frame_paths:
                source = self.storage._resolve_image_path(frame_path)
                if not source.exists():
                    raise InvalidParamError(f"资产 {asset.id} 源图片不存在")
                with Image.open(source) as image:
                    images.append(image.convert("RGBA").copy())
        return images

    def _animation_frame_paths(self, asset: Asset) -> list[str]:
        source = self.storage._resolve_image_path(asset.source_path)
        manifest_path = source.parent / "animation.json"
        if not manifest_path.exists():
            return []
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        frames = data.get("frames") if isinstance(data, dict) else None
        if not isinstance(frames, list):
            return []
        return [frame for frame in frames if isinstance(frame, str)]

    def _spritesheet_columns(self, layout: str | None, frame_count: int) -> int:
        if frame_count <= 0:
            raise InvalidParamError("Sprite Sheet 至少需要 1 帧图片")
        if layout == "linear":
            return frame_count
        return min(frame_count, 8)

    def _safe_stem(self, value: str) -> str:
        cleaned = "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in value)
        return cleaned.strip("_") or "asset"

    def _unique_filename(self, filename: str, used_names: set[str], index: int) -> str:
        candidate = filename
        if candidate in used_names:
            stem = Path(filename).stem
            suffix = Path(filename).suffix
            candidate = f"{stem}_{index + 1}{suffix}"
        used_names.add(candidate)
        return candidate

    def _file_info(self, path: Path) -> ExportFileInfo:
        return ExportFileInfo(filename=path.name, path=str(path), size=path.stat().st_size)
