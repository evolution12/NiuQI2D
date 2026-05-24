from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path
from typing import Any

from PIL import Image

from .exceptions import ResourceNotFoundError
from .models import ArtStyle, AssetType


class StorageManager:
    def __init__(self, data_dir: str) -> None:
        self.data_dir = Path(data_dir).expanduser().resolve()
        self.images_dir = self.data_dir / "images"
        self.exports_dir = self.data_dir / "exports"
        self.logs_dir = self.data_dir / "logs"

    async def initialize(self) -> None:
        await asyncio.to_thread(self._initialize_sync)

    def _initialize_sync(self) -> None:
        for path in [
            self.data_dir,
            self.images_dir,
            self.images_dir / "references",
            self.exports_dir,
            self.logs_dir,
        ]:
            path.mkdir(parents=True, exist_ok=True)

    async def save_raw_image(self, project_id: str, record_id: str, image_data: bytes) -> str:
        return await self._save_image(
            self.images_dir / project_id / "raw" / f"{record_id}.png", image_data
        )

    async def save_processed_image(self, project_id: str, asset_id: str, image_data: bytes) -> str:
        return await self._save_image(
            self.images_dir / project_id / "processed" / f"{asset_id}.png", image_data
        )

    async def save_processed_frame(
        self,
        project_id: str,
        group_id: str,
        frame_index: int,
        image_data: bytes,
    ) -> str:
        return await self._save_image(
            self.images_dir / project_id / "processed" / group_id / f"frame_{frame_index:03d}.png",
            image_data,
        )

    async def save_animation_manifest(
        self,
        project_id: str,
        group_id: str,
        manifest: dict[str, Any],
    ) -> str:
        target_path = self.images_dir / project_id / "processed" / group_id / "animation.json"
        await asyncio.to_thread(self._save_json_sync, target_path, manifest)
        return self._relative_image_path(target_path)

    async def save_reference_image(self, style_id: str, image_data: bytes) -> str:
        return await self._save_image(self.images_dir / "references" / f"{style_id}.png", image_data)

    async def save_uploaded_image(
        self,
        relative_path: str,
        image_data: bytes,
    ) -> str:
        return await self._save_image(self.images_dir / relative_path, image_data)

    async def get_image(self, path: str) -> bytes:
        image_path = self._resolve_image_path(path)
        if not image_path.exists():
            raise ResourceNotFoundError(f"图片 {path} 不存在")
        return await asyncio.to_thread(image_path.read_bytes)

    async def generate_thumbnail(
        self,
        image_path: str,
        asset_type: AssetType = AssetType.CHARACTER,
        art_style: ArtStyle | None = None,
    ) -> str:
        source_path = self._resolve_image_path(image_path)
        if not source_path.exists():
            raise ResourceNotFoundError(f"图片 {image_path} 不存在")

        size = self._thumbnail_size(asset_type)
        thumbnail_path = source_path.parent.parent / "thumbnails" / f"{source_path.stem}_thumb.png"
        await asyncio.to_thread(self._generate_thumbnail_sync, source_path, thumbnail_path, size, art_style)
        return self._relative_image_path(thumbnail_path)

    async def get_storage_usage(self) -> dict[str, float]:
        return await asyncio.to_thread(self._get_storage_usage_sync)

    async def clear_cache(self, project_id: str | None = None) -> int:
        return await asyncio.to_thread(self._clear_cache_sync, project_id)

    async def _save_image(self, target_path: Path, image_data: bytes) -> str:
        await asyncio.to_thread(self._save_image_sync, target_path, image_data)
        return self._relative_image_path(target_path)

    def _save_image_sync(self, target_path: Path, image_data: bytes) -> None:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(image_data)

    def _save_json_sync(self, target_path: Path, data: dict[str, Any]) -> None:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _resolve_image_path(self, path: str) -> Path:
        candidate = Path(path)
        if candidate.is_absolute():
            resolved = candidate.resolve()
        else:
            cleaned = path.removeprefix("images/").lstrip("/\\")
            resolved = (self.images_dir / cleaned).resolve()
        if self.images_dir not in resolved.parents and resolved != self.images_dir:
            raise ResourceNotFoundError("图片路径不在存储目录内")
        return resolved

    def _relative_image_path(self, path: Path) -> str:
        return path.resolve().relative_to(self.images_dir).as_posix()

    def _thumbnail_size(self, asset_type: AssetType) -> tuple[int, int]:
        if asset_type == AssetType.CHARACTER:
            return (64, 64)
        if asset_type == AssetType.TILE:
            return (32, 32)
        return (128, 128)

    def _generate_thumbnail_sync(
        self,
        source_path: Path,
        thumbnail_path: Path,
        size: tuple[int, int],
        art_style: ArtStyle | None,
    ) -> None:
        thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
        resample = Image.Resampling.NEAREST if art_style == ArtStyle.PIXEL else Image.Resampling.LANCZOS
        with Image.open(source_path) as image:
            rgba = image.convert("RGBA")
            rgba.thumbnail(size, resample=resample)
            canvas = Image.new("RGBA", size, (0, 0, 0, 0))
            offset = ((size[0] - rgba.width) // 2, (size[1] - rgba.height) // 2)
            canvas.paste(rgba, offset, rgba)
            canvas.save(thumbnail_path, "PNG")

    def _get_storage_usage_sync(self) -> dict[str, float]:
        images_mb = self._directory_size_mb(self.images_dir)
        exports_mb = self._directory_size_mb(self.exports_dir)
        return {
            "total_mb": round(images_mb + exports_mb, 2),
            "images_mb": round(images_mb, 2),
            "exports_mb": round(exports_mb, 2),
        }

    def _directory_size_mb(self, path: Path) -> float:
        if not path.exists():
            return 0.0
        total = sum(file.stat().st_size for file in path.rglob("*") if file.is_file())
        return total / 1024 / 1024

    def _clear_cache_sync(self, project_id: str | None) -> int:
        target = self.images_dir / project_id if project_id else self.images_dir
        before = self._directory_size_mb(target)
        if target.exists():
            for child in target.iterdir():
                if child.name == "references" and project_id is None:
                    continue
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
        after = self._directory_size_mb(target)
        return int(before - after)
