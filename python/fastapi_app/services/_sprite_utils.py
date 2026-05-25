"""Shared utilities for spritesheet generation."""
from __future__ import annotations

from io import BytesIO

from PIL import Image


def direction_names(direction_count: int) -> list[str]:
    if direction_count == 1:
        return ["down"]
    if direction_count == 2:
        return ["left", "right"]
    if direction_count == 4:
        return ["up", "down", "left", "right"]
    return ["up", "up-right", "right", "down-right", "down", "down-left", "left", "up-left"]


def build_action_mapping(
    actions: list[str],
    direction_names_list: list[str],
    frame_count: int,
    total_frames: int,
) -> dict[str, list[int]]:
    mapping: dict[str, list[int]] = {}
    index = 0
    for action in actions:
        action_indexes: list[int] = []
        for direction in direction_names_list:
            frame_indexes = list(range(index, min(index + frame_count, total_frames)))
            if frame_indexes:
                mapping[f"{action}_{direction}"] = frame_indexes
                action_indexes.extend(frame_indexes)
            index += frame_count
        if action_indexes:
            mapping[f"{action}_all"] = action_indexes
    return mapping


def prepare_preview_frames(frames: list[Image.Image]) -> list[Image.Image]:
    return [prepare_preview_frame(frame) for frame in frames]


def prepare_preview_frame(frame: Image.Image) -> Image.Image:
    rgba = frame.convert("RGBA")
    padding = max(2, round(max(rgba.size) * 0.08))
    canvas = Image.new("RGBA", (rgba.width + padding * 2, rgba.height + padding * 2), (0, 0, 0, 0))
    canvas.paste(rgba, (padding, padding), rgba)
    return canvas


def png_bytes(image: Image.Image) -> bytes:
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()
