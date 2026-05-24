from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..crud.export import ExportCRUD
from ..crud.asset import AssetCRUD
from ..crud.generation import GenerationCRUD
from ..exceptions import InvalidParamError, ResourceNotFoundError
from ..models import Asset, AssetStatus, AssetType, ExportFormat, ExportRecord
from ..postprocess.spritesheet import SpriteSheetConfig
from ..postprocess.tileset import TilesetConfig
from ..schemas import ExportFileInfo, ExportRequest, ExportResponse
from ..storage import StorageManager
from .export_algorithms import build_spritesheet_export, build_tileset_export

logger = logging.getLogger(__name__)

export_crud = ExportCRUD()
asset_crud = AssetCRUD()
generation_crud = GenerationCRUD()


async def run_export(
    body: ExportRequest,
    session: AsyncSession,
    storage: StorageManager,
) -> ExportResponse:
    if not body.asset_ids:
        raise InvalidParamError("至少需要选择一个资产")

    # Load all assets
    assets: list[Asset] = []
    for aid in body.asset_ids:
        asset = await asset_crud.get(session, aid)
        assets.append(asset)

    # Ensure all assets belong to the same project
    project_id = assets[0].project_id
    if any(a.project_id != project_id for a in assets):
        raise InvalidParamError("所有资产必须属于同一个项目")

    # Create export directory
    export_dir = Path(body.export_path)
    export_dir.mkdir(parents=True, exist_ok=True)

    files: list[ExportFileInfo] = []
    total_size = 0

    if body.export_format == ExportFormat.PNG_SINGLE:
        files, total_size = await _export_single_png(assets, storage, export_dir)
    elif body.export_format == ExportFormat.SPRITESHEET_PNG_JSON:
        files, total_size = await _export_spritesheet(
            assets, session, storage, export_dir, body
        )
    elif body.export_format == ExportFormat.TILESET_PNG_JSON:
        files, total_size = await _export_tileset(
            assets, storage, export_dir, body
        )

    # Create export record
    export_record = await export_crud.create(
        session,
        {
            "asset_ids": body.asset_ids,
            "export_format": body.export_format,
            "export_path": str(export_dir),
            "metadata": {"files": [f.model_dump() for f in files]},
            "file_size": total_size,
        },
    )

    # Update asset status
    for asset in assets:
        await asset_crud.update(session, asset.id, {"status": AssetStatus.EXPORTED})

    return ExportResponse(
        export_id=export_record.id,
        files=files,
        total_size=total_size,
    )


async def _export_single_png(
    assets: list[Asset],
    storage: StorageManager,
    export_dir: Path,
) -> tuple[list[ExportFileInfo], int]:
    files: list[ExportFileInfo] = []
    total_size = 0
    for asset in assets:
        image_bytes = await storage.get_image(asset.source_path)
        filename = _safe_filename(asset.name) + ".png"
        file_path = export_dir / filename
        file_path.write_bytes(image_bytes)
        size = len(image_bytes)
        files.append(ExportFileInfo(filename=filename, path=str(file_path), size=size))
        total_size += size
    return files, total_size


async def _export_spritesheet(
    assets: list[Asset],
    session: AsyncSession,
    storage: StorageManager,
    export_dir: Path,
    body: ExportRequest,
) -> tuple[list[ExportFileInfo], int]:
    from PIL import Image
    import io

    # Load images and generation records
    images: list[Image.Image] = []
    generation_data: dict = {}

    for asset in assets:
        image_bytes = await storage.get_image(asset.source_path)
        images.append(Image.open(io.BytesIO(image_bytes)).convert("RGBA"))

        # Try to load generation record for metadata
        stmt = select(generation_crud.model).where(generation_crud.model.asset_id == asset.id)
        result = await session.execute(stmt)
        gen_record = result.scalar_one_or_none()
        if gen_record:
            generation_data = {
                "user_prompt": gen_record.user_prompt,
                "optimized_prompt": gen_record.optimized_prompt,
                "api_provider": gen_record.api_provider,
                "api_model": gen_record.api_model,
            }

    # Determine config from first asset's generation record
    frame_w = images[0].width if images else 16
    frame_h = images[0].height if images else 16

    # Check if this is an animated spritesheet or static images
    stmt = select(generation_crud.model).where(generation_crud.model.asset_id == assets[0].id)
    result = await session.execute(stmt)
    gen = result.scalar_one_or_none()

    is_animated = (
        gen is not None
        and gen.asset_subtype is not None
        and gen.asset_subtype.value == "animated_spritesheet"
    )

    total_frames = len(images)

    if is_animated and gen and gen.api_params:
        # Full spritesheet layout with actions/directions
        params = gen.api_params
        actions = params.get("actions", ["idle"])
        direction_count = params.get("direction_count", 1)
        frame_count = params.get("frame_count", 1)
        frames_per_action = frame_count

        if direction_count == 1:
            directions = ["front"]
        elif direction_count == 2:
            directions = ["left", "right"]
        elif direction_count == 4:
            directions = ["front", "back", "left", "right"]
        else:
            directions = ["front", "front-right", "right", "back-right", "back", "back-left", "left", "front-left"]

        columns = frames_per_action
        rows = max(1, total_frames // columns) if columns > 0 else 1
    else:
        # Static images: simple grid layout, one frame per image
        actions = ["static"]
        directions = ["default"]
        frames_per_action = 1
        columns = max(1, total_frames)
        rows = 1
        # Auto-wrap into reasonable grid
        if total_frames > 4:
            columns = 4
            rows = (total_frames + columns - 1) // columns

    config = SpriteSheetConfig(
        frame_size=(frame_w, frame_h),
        columns=columns,
        rows=rows,
        padding=body.sheet_padding,
        margin=body.sheet_margin,
    )

    base_name = _safe_filename(assets[0].name) if len(assets) == 1 else "spritesheet"
    image_filename = f"{base_name}.png"
    naming_template = f"{base_name}_{{action}}_{{direction}}_{{frame}}"

    export_result = build_spritesheet_export(
        frames=images,
        config=config,
        image_filename=image_filename,
        naming_template=naming_template,
        actions=actions,
        directions=directions,
        frames_per_action=frames_per_action,
        generation=generation_data,
    )

    return _write_export_files(export_result, export_dir, base_name)


async def _export_tileset(
    assets: list[Asset],
    storage: StorageManager,
    export_dir: Path,
    body: ExportRequest,
) -> tuple[list[ExportFileInfo], int]:
    from PIL import Image
    import io

    tiles: list[Image.Image] = []
    tile_types: list[str] = []

    for asset in assets:
        image_bytes = await storage.get_image(asset.source_path)
        tiles.append(Image.open(io.BytesIO(image_bytes)).convert("RGBA"))
        tile_types.append(_safe_filename(asset.name))

    tile_w = tiles[0].width if tiles else 16
    tile_h = tiles[0].height if tiles else 16

    config = TilesetConfig(
        tile_size=(tile_w, tile_h),
        columns=body.tileset_columns,
        spacing=body.tileset_spacing,
        margin=body.tileset_margin,
    )

    base_name = "tileset"
    image_filename = f"{base_name}.png"

    export_result = build_tileset_export(
        tiles=tiles,
        config=config,
        image_filename=image_filename,
        tile_types=tile_types,
    )

    return _write_export_files(export_result, export_dir, base_name)


def _write_export_files(
    export_result,  # ExportAlgorithmResult
    export_dir: Path,
    base_name: str,
) -> tuple[list[ExportFileInfo], int]:
    files: list[ExportFileInfo] = []
    total_size = 0

    png_path = export_dir / f"{base_name}.png"
    png_path.write_bytes(export_result.png_data)
    files.append(ExportFileInfo(
        filename=png_path.name,
        path=str(png_path),
        size=len(export_result.png_data),
    ))
    total_size += len(export_result.png_data)

    json_path = export_dir / f"{base_name}.json"
    json_path.write_bytes(export_result.json_data)
    files.append(ExportFileInfo(
        filename=json_path.name,
        path=str(json_path),
        size=len(export_result.json_data),
    ))
    total_size += len(export_result.json_data)

    return files, total_size


def _safe_filename(name: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
    return safe[:64] if safe else "export"
