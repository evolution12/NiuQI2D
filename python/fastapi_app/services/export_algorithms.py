from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from io import BytesIO
from typing import Any

from PIL import Image

from ..postprocess.spritesheet import SpriteSheetConfig, build_sprite_sheet
from ..postprocess.tileset import TilesetConfig, build_tileset


@dataclass(frozen=True)
class ExportAlgorithmResult:
    png_data: bytes
    json_data: bytes
    metadata: dict[str, Any]


def build_spritesheet_export(
    frames: list[Image.Image],
    config: SpriteSheetConfig,
    image_filename: str,
    naming_template: str,
    actions: list[str],
    directions: list[str],
    frames_per_action: int,
    generation: dict[str, Any] | None = None,
    animation_speed: int = 8,
) -> ExportAlgorithmResult:
    result = build_sprite_sheet(
        frames=frames,
        config=config,
        naming_template=naming_template,
        actions=actions,
        directions=directions,
        frames_per_action=frames_per_action,
    )
    metadata = {
        "meta": {
            "app": "NiuQI2D",
            "version": "1.0.0",
            "image": image_filename,
            "size": {"w": result.sheet_image.width, "h": result.sheet_image.height},
            "format": "RGBA8888",
            "scale": 1,
        },
        "frames": [asdict(frame) for frame in result.frames_metadata],
        "animations": _build_animations(actions, directions, frames_per_action, animation_speed),
        "generation": generation or {},
    }
    return ExportAlgorithmResult(
        png_data=_encode_png(result.sheet_image),
        json_data=_encode_json(metadata),
        metadata=metadata,
    )


def build_tileset_export(
    tiles: list[Image.Image],
    config: TilesetConfig,
    image_filename: str,
    tile_types: list[str],
    generation: dict[str, Any] | None = None,
) -> ExportAlgorithmResult:
    result = build_tileset(tiles=tiles, config=config, tile_types=tile_types)
    metadata = {
        "meta": {
            "app": "NiuQI2D",
            "version": "1.0.0",
            "image": image_filename,
            "tile_size": {"w": config.tile_size[0], "h": config.tile_size[1]},
            "tile_count": len(result.tiles_metadata),
            "columns": config.columns,
            "spacing": config.spacing,
            "margin": config.margin,
        },
        "tiles": [asdict(tile) for tile in result.tiles_metadata],
        "generation": generation or {},
    }
    return ExportAlgorithmResult(
        png_data=_encode_png(result.tileset_image),
        json_data=_encode_json(metadata),
        metadata=metadata,
    )


def _build_animations(
    actions: list[str],
    directions: list[str],
    frames_per_action: int,
    animation_speed: int,
) -> dict[str, dict[str, int | list[int]]]:
    animations = {}
    index = 0
    for action in actions:
        for direction in directions:
            frame_indexes = list(range(index, index + frames_per_action))
            animations[f"{action}_{direction}"] = {
                "frames": frame_indexes,
                "speed": animation_speed,
            }
            index += frames_per_action
    return animations


def _encode_png(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.convert("RGBA").save(buffer, format="PNG")
    return buffer.getvalue()


def _encode_json(metadata: dict[str, Any]) -> bytes:
    return json.dumps(metadata, ensure_ascii=False, indent=2).encode("utf-8")
