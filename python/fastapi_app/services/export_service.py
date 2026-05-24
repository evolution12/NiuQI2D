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
from ..models import Asset, AssetStatus, AssetSubtype, AssetType, ExportFormat, ExportRecord
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
        self._validate_export_format(body.export_format, assets)
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

    def _validate_export_format(self, fmt: ExportFormat, assets: list[Asset]) -> None:
        """Ensure all assets are compatible with the chosen export format."""
        for asset in assets:
            if fmt == ExportFormat.PNG_SINGLE:
                if asset.asset_type == AssetType.MAP:
                    raise InvalidParamError("地图类型素材不支持单图 PNG 导出，请选择 Tileset+JSON")
            elif fmt == ExportFormat.SPRITESHEET_PNG_JSON:
                if asset.asset_type != AssetType.CHARACTER or asset.asset_subtype != AssetSubtype.ANIMATED_SPRITESHEET:
                    raise InvalidParamError("仅动画精灵表素材支持 Sprite Sheet+JSON 导出")
            elif fmt == ExportFormat.TILESET_PNG_JSON:
                if asset.asset_type != AssetType.MAP:
                    raise InvalidParamError("仅地图类型素材支持 Tileset+JSON 导出")

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
        seen: dict[str, int] = {}
        for asset in assets:
            source = self.storage._resolve_image_path(asset.source_path)
            if not source.exists():
                raise InvalidParamError(f"资产 {asset.id} 源图片不存在")
            filename = self._disk_unique_filename(self._safe_stem(asset.name) + ".png", export_dir, seen)
            target = export_dir / filename
            shutil.copyfile(source, target)
            files.append(self._file_info(target))
            seen[filename] = seen.get(filename, 0) + 1
        return files

    def _disk_unique_filename(self, wanted: str, parent: Path, seen: dict[str, int]) -> str:
        """Return a filename that does not exist on disk and is unique within this batch."""
        counter = seen.get(wanted, 0) + 1
        candidate = wanted
        while True:
            if not (parent / candidate).exists() and candidate not in seen:
                return candidate
            stem = Path(wanted).stem
            suffix = Path(wanted).suffix
            candidate = f"{stem}_{counter}{suffix}"
            counter += 1

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

        base_name = self._safe_stem(assets[0].name) if assets else "spritesheet"

        result = build_spritesheet_export(
            frames=frames,
            config=SpriteSheetConfig(
                frame_size=frame_size,
                columns=columns,
                rows=rows,
                padding=body.sheet_padding,
                margin=body.sheet_margin,
            ),
            image_filename=f"{base_name}.png",
            naming_template="{action}_{direction}_{frame}",
            actions=actions,
            directions=directions,
            frames_per_action=frames_per_action,
            generation={"asset_ids": [asset.id for asset in assets]},
        )
        out_dir = self._unique_dir(export_dir, base_name)
        out_dir.mkdir(parents=True, exist_ok=True)
        png_path = out_dir / f"{base_name}.png"
        json_path = out_dir / f"{base_name}.json"
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
        """Export a map asset as tileset PNG+JSON.

        The map image is kept at its original size.  JSON metadata records
        each tile cell's position so game engines can slice it.
        """
        tile_w, tile_h = body.tile_size or (64, 64)
        if tile_w <= 0 or tile_h <= 0:
            raise InvalidParamError("tile_size 必须为正整数")

        # Load the single map image (one asset)
        asset = assets[0]
        images = self._load_images([asset])
        map_image = images[0].convert("RGBA")
        map_w, map_h = map_image.size

        cols = max(1, map_w // tile_w)
        rows = max(1, map_h // tile_h)

        # Build tile metadata — grid of cells over the map
        tile_metadata: list[dict[str, object]] = []
        for row in range(rows):
            for col in range(cols):
                tile_metadata.append({
                    "id": row * cols + col,
                    "type": f"tile_{row}_{col}",
                    "terrain": [],
                    "frame": {
                        "x": col * tile_w,
                        "y": row * tile_h,
                        "w": tile_w,
                        "h": tile_h,
                    },
                })

        metadata = {
            "meta": {
                "app": "NiuQI2D",
                "version": "1.0.0",
                "image": "tileset.png",
                "tile_size": {"w": tile_w, "h": tile_h},
                "map_size": {"w": map_w, "h": map_h},
                "tile_count": len(tile_metadata),
                "columns": cols,
                "rows": rows,
            },
            "tiles": tile_metadata,
            "generation": {"asset_ids": [asset.id for asset in assets]},
        }

        base_name = self._safe_stem(asset.name) if assets else "tileset"
        out_dir = self._unique_dir(export_dir, base_name)
        out_dir.mkdir(parents=True, exist_ok=True)
        png_path = out_dir / f"{base_name}.png"
        json_path = out_dir / f"{base_name}.json"

        # Update image reference in metadata to match actual filename
        metadata["meta"]["image"] = f"{base_name}.png"

        # Write PNG at original resolution
        map_image.save(png_path, format="PNG")
        json_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

        return [self._file_info(png_path), self._file_info(json_path)]

    def _unique_dir(self, parent: Path, name: str) -> Path:
        """Find a unique subdirectory name.  If 'name' exists, try 'name_2', 'name_3', etc."""
        candidate = parent / name
        if not candidate.exists():
            return candidate
        counter = 2
        while True:
            candidate = parent / f"{name}_{counter}"
            if not candidate.exists():
                return candidate
            counter += 1

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

    def _file_info(self, path: Path) -> ExportFileInfo:
        return ExportFileInfo(filename=path.name, path=str(path), size=path.stat().st_size)
