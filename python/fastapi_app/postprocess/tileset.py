from __future__ import annotations

from dataclasses import dataclass
from math import ceil

from PIL import Image

from ..exceptions import InvalidParamError
from .base import ensure_rgba


@dataclass(frozen=True)
class TilesetConfig:
    tile_size: tuple[int, int]
    columns: int
    spacing: int = 0
    margin: int = 0


@dataclass(frozen=True)
class TileMetadata:
    id: int
    type: str
    terrain: list[str]
    frame: dict[str, int]


@dataclass(frozen=True)
class TilesetResult:
    tileset_image: Image.Image
    tiles_metadata: list[TileMetadata]


def build_tileset(
    tiles: list[Image.Image],
    config: TilesetConfig,
    tile_types: list[str],
) -> TilesetResult:
    _validate_inputs(tiles, config, tile_types)

    rows = ceil(len(tiles) / config.columns)
    width = config.margin * 2 + config.columns * config.tile_size[0]
    height = config.margin * 2 + rows * config.tile_size[1]
    width += max(config.columns - 1, 0) * config.spacing
    height += max(rows - 1, 0) * config.spacing
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    metadata = []
    for index, tile in enumerate(tiles):
        row = index // config.columns
        col = index % config.columns
        x = config.margin + col * (config.tile_size[0] + config.spacing)
        y = config.margin + row * (config.tile_size[1] + config.spacing)
        normalized = _normalize_tile(tile, config.tile_size)
        image.paste(normalized, (x, y), normalized)
        tile_type = tile_types[index]
        metadata.append(
            TileMetadata(
                id=index,
                type=tile_type,
                terrain=_terrain_from_type(tile_type),
                frame={"x": x, "y": y, "w": config.tile_size[0], "h": config.tile_size[1]},
            )
        )

    return TilesetResult(tileset_image=image, tiles_metadata=metadata)


def _validate_inputs(
    tiles: list[Image.Image],
    config: TilesetConfig,
    tile_types: list[str],
) -> None:
    if not tiles:
        raise InvalidParamError("Tileset 至少需要 1 张 Tile 图片")
    if config.tile_size[0] <= 0 or config.tile_size[1] <= 0:
        raise InvalidParamError("tile_size 必须为正整数")
    if config.columns <= 0:
        raise InvalidParamError("columns 必须为正整数")
    if config.spacing < 0 or config.margin < 0:
        raise InvalidParamError("spacing 和 margin 不能为负数")
    if len(tile_types) != len(tiles):
        raise InvalidParamError(
            "tile_types 数量必须与 tiles 一致",
            {"tiles": len(tiles), "tile_types": len(tile_types)},
        )


def _normalize_tile(tile: Image.Image, tile_size: tuple[int, int]) -> Image.Image:
    rgba = ensure_rgba(tile)
    if rgba.size == tile_size:
        return rgba
    return rgba.resize(tile_size, resample=Image.Resampling.NEAREST)


def _terrain_from_type(tile_type: str) -> list[str]:
    parts = [part for part in tile_type.split("_") if part]
    if len(parts) <= 1:
        return parts
    return parts[1:]
