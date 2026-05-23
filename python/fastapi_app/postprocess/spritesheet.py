from __future__ import annotations

from dataclasses import dataclass
from string import Formatter
from typing import Any

from PIL import Image

from ..exceptions import InvalidParamError
from .base import ensure_rgba


@dataclass(frozen=True)
class SpriteSheetConfig:
    frame_size: tuple[int, int]
    columns: int
    rows: int
    padding: int = 0
    margin: int = 0


@dataclass(frozen=True)
class FrameMetadata:
    filename: str
    frame: dict[str, int]
    rotated: bool
    trimmed: bool
    spriteSourceSize: dict[str, int]
    sourceSize: dict[str, int]
    pivot: dict[str, float]


@dataclass(frozen=True)
class SpriteSheetResult:
    sheet_image: Image.Image
    frames_metadata: list[FrameMetadata]


def build_sprite_sheet(
    frames: list[Image.Image],
    config: SpriteSheetConfig,
    naming_template: str,
    actions: list[str],
    directions: list[str],
    frames_per_action: int,
) -> SpriteSheetResult:
    _validate_inputs(frames, config, actions, directions, frames_per_action)

    aligned_frames = _align_frames(frames, config.frame_size)
    sheet_width = config.margin * 2 + config.columns * config.frame_size[0]
    sheet_height = config.margin * 2 + config.rows * config.frame_size[1]
    sheet_width += max(config.columns - 1, 0) * config.padding
    sheet_height += max(config.rows - 1, 0) * config.padding
    sheet = Image.new("RGBA", (sheet_width, sheet_height), (0, 0, 0, 0))

    metadata = []
    for index, frame in enumerate(aligned_frames):
        row = index // config.columns
        col = index % config.columns
        x = config.margin + col * (config.frame_size[0] + config.padding)
        y = config.margin + row * (config.frame_size[1] + config.padding)
        sheet.paste(frame, (x, y), frame)
        metadata.append(
            _build_metadata(
                image=frame,
                filename=_format_frame_name(
                    naming_template,
                    index,
                    actions,
                    directions,
                    frames_per_action,
                ),
                x=x,
                y=y,
                frame_size=config.frame_size,
            )
        )

    return SpriteSheetResult(sheet_image=sheet, frames_metadata=metadata)


def _validate_inputs(
    frames: list[Image.Image],
    config: SpriteSheetConfig,
    actions: list[str],
    directions: list[str],
    frames_per_action: int,
) -> None:
    if not frames:
        raise InvalidParamError("Sprite Sheet 至少需要 1 帧图片")
    if config.frame_size[0] <= 0 or config.frame_size[1] <= 0:
        raise InvalidParamError("frame_size 必须为正整数")
    if config.columns <= 0 or config.rows <= 0:
        raise InvalidParamError("columns 和 rows 必须为正整数")
    if config.padding < 0 or config.margin < 0:
        raise InvalidParamError("padding 和 margin 不能为负数")
    if frames_per_action <= 0:
        raise InvalidParamError("frames_per_action 必须为正整数")
    if len(frames) > config.columns * config.rows:
        raise InvalidParamError("帧数量超过 Sprite Sheet 配置容量")
    expected_count = len(actions) * len(directions) * frames_per_action
    if actions and directions and len(frames) != expected_count:
        raise InvalidParamError(
            "帧数量与 actions、directions、frames_per_action 不匹配",
            {
                "frames": len(frames),
                "expected": expected_count,
            },
        )


def _align_frames(frames: list[Image.Image], target_size: tuple[int, int]) -> list[Image.Image]:
    prepared = [ensure_rgba(frame) for frame in frames]
    bboxes = [frame.getbbox() for frame in prepared]
    non_empty_bboxes = [bbox for bbox in bboxes if bbox is not None]
    if not non_empty_bboxes:
        return [Image.new("RGBA", target_size, (0, 0, 0, 0)) for _ in prepared]

    max_width = max(bbox[2] - bbox[0] for bbox in non_empty_bboxes)
    max_height = max(bbox[3] - bbox[1] for bbox in non_empty_bboxes)
    scale = min(target_size[0] / max_width, target_size[1] / max_height, 1.0)
    aligned = []

    for frame, bbox in zip(prepared, bboxes, strict=True):
        canvas = Image.new("RGBA", target_size, (0, 0, 0, 0))
        if bbox is None:
            aligned.append(canvas)
            continue

        subject = frame.crop(bbox)
        if scale < 1.0:
            resized_size = (
                max(1, int(subject.width * scale)),
                max(1, int(subject.height * scale)),
            )
            subject = subject.resize(resized_size, resample=Image.Resampling.NEAREST)

        x = (target_size[0] - subject.width) // 2
        y = (target_size[1] - subject.height) // 2
        canvas.paste(subject, (x, y), subject)
        aligned.append(canvas)

    return aligned


def _format_frame_name(
    naming_template: str,
    index: int,
    actions: list[str],
    directions: list[str],
    frames_per_action: int,
) -> str:
    action_span = max(len(directions) * frames_per_action, 1)
    action = actions[index // action_span] if actions else "action"
    direction_index = (index % action_span) // frames_per_action
    direction = directions[direction_index] if directions else "direction"
    frame = index % frames_per_action

    values: dict[str, Any] = {
        "action": action,
        "direction": direction,
        "frame": frame,
        "index": index,
    }
    fields = {field_name for _, field_name, _, _ in Formatter().parse(naming_template) if field_name}
    if not fields:
        return f"{naming_template}_{action}_{direction}_{frame}"
    return naming_template.format(**values)


def _build_metadata(
    image: Image.Image,
    filename: str,
    x: int,
    y: int,
    frame_size: tuple[int, int],
) -> FrameMetadata:
    bbox = image.getbbox()
    if bbox is None:
        sprite_source = {"x": 0, "y": 0, "w": 0, "h": 0}
    else:
        sprite_source = {
            "x": bbox[0],
            "y": bbox[1],
            "w": bbox[2] - bbox[0],
            "h": bbox[3] - bbox[1],
        }
    return FrameMetadata(
        filename=filename,
        frame={"x": x, "y": y, "w": frame_size[0], "h": frame_size[1]},
        rotated=False,
        trimmed=True,
        spriteSourceSize=sprite_source,
        sourceSize={"w": frame_size[0], "h": frame_size[1]},
        pivot={"x": 0.5, "y": 0.5},
    )
