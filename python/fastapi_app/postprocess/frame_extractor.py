from __future__ import annotations

from PIL import Image

from ..models import AssetSubtype
from .base import PostProcessContext, PostProcessStep, ensure_rgba


MIN_GROUP_RATIO = 0.08
ACTIVE_COLUMN_RATIO = 0.015
MERGE_GAP_RATIO = 0.02
FRAME_PADDING_RATIO = 0.08
TARGET_SCAN_SIZE = 768


class FrameExtractorStep(PostProcessStep):
    name = "frame_extractor"

    def should_run(self, context: PostProcessContext) -> bool:
        return (
            context.asset_subtype == AssetSubtype.ANIMATED_SPRITESHEET
            and context.sheet_rows is not None
            and context.sheet_cols is not None
            and context.sheet_rows > 0
            and context.sheet_cols > 0
        )

    def params(self, context: PostProcessContext) -> dict[str, int | None]:
        return {
            "sheet_rows": context.sheet_rows,
            "sheet_cols": context.sheet_cols,
            "target_width": context.target_size[0],
            "target_height": context.target_size[1],
        }

    async def apply(self, context: PostProcessContext) -> PostProcessContext:
        image = ensure_rgba(context.image)
        rows = context.sheet_rows or 1
        cols = context.sheet_cols or 1
        frames = self._extract_detected_frames(image, rows, cols) or self._extract_uniform_frames(image, rows, cols)

        if frames:
            detected_rows, detected_cols = self._detected_grid_size(image, rows, cols)
            if detected_rows and detected_cols and len(frames) == detected_rows * detected_cols:
                context.sheet_rows = detected_rows
                context.sheet_cols = detected_cols

        context.image = image
        context.extracted_frames = frames
        return context

    def _extract_uniform_frames(self, image: Image.Image, rows: int, cols: int) -> list[Image.Image]:
        cell_width = image.width / cols
        cell_height = image.height / rows
        frames = []

        for row in range(rows):
            for col in range(cols):
                left = round(col * cell_width)
                upper = round(row * cell_height)
                right = round((col + 1) * cell_width)
                lower = round((row + 1) * cell_height)
                frames.append(image.crop((left, upper, right, lower)).convert("RGBA"))
        return frames

    def _extract_detected_frames(self, image: Image.Image, rows: int, cols: int) -> list[Image.Image]:
        row_groups, col_groups = self._detect_content_grid(image)
        if not row_groups or not col_groups:
            return []

        detected_count = len(row_groups) * len(col_groups)
        expected_count = rows * cols
        if detected_count <= 0 or detected_count == expected_count:
            return []

        frames: list[Image.Image] = []
        pad_x = max(1, round(image.width * FRAME_PADDING_RATIO / max(len(col_groups), 1)))
        pad_y = max(1, round(image.height * FRAME_PADDING_RATIO / max(len(row_groups), 1)))
        for top, bottom in row_groups:
            for left, right in col_groups:
                box = (
                    max(0, left - pad_x),
                    max(0, top - pad_y),
                    min(image.width, right + pad_x),
                    min(image.height, bottom + pad_y),
                )
                frames.append(image.crop(box).convert("RGBA"))
        return frames

    def _detected_grid_size(self, image: Image.Image, rows: int, cols: int) -> tuple[int | None, int | None]:
        row_groups, col_groups = self._detect_content_grid(image)
        if not row_groups or not col_groups:
            return None, None
        detected_count = len(row_groups) * len(col_groups)
        if detected_count <= 0 or detected_count == rows * cols:
            return None, None
        return len(row_groups), len(col_groups)

    def _detect_content_grid(self, image: Image.Image) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
        rgba = ensure_rgba(image)
        pixels = rgba.load()
        width, height = rgba.size
        stride = max(1, min(width, height) // TARGET_SCAN_SIZE)
        col_counts = [0] * width
        row_counts = [0] * height

        for y in range(0, height, stride):
            for x in range(0, width, stride):
                if self._is_content_pixel(pixels[x, y]):
                    col_counts[x] += 1
                    row_counts[y] += 1

        col_groups = self._projection_groups(col_counts, (height + stride - 1) // stride)
        row_groups = self._projection_groups(row_counts, (width + stride - 1) // stride)
        return row_groups, col_groups

    def _projection_groups(self, counts: list[int], cross_size: int) -> list[tuple[int, int]]:
        if not counts:
            return []

        active_threshold = max(2, round(cross_size * ACTIVE_COLUMN_RATIO))
        min_group_width = max(2, round(len(counts) * MIN_GROUP_RATIO))
        merge_gap = max(1, round(len(counts) * MERGE_GAP_RATIO))

        groups: list[tuple[int, int]] = []
        start: int | None = None
        last_active: int | None = None
        for index, count in enumerate(counts):
            if count >= active_threshold:
                if start is None:
                    start = index
                last_active = index
            elif start is not None and last_active is not None and index - last_active > merge_gap:
                groups.append((start, last_active + 1))
                start = None
                last_active = None
        if start is not None and last_active is not None:
            groups.append((start, last_active + 1))

        return [(start, end) for start, end in groups if end - start >= min_group_width]

    def _is_content_pixel(self, pixel: tuple[int, int, int, int]) -> bool:
        red, green, blue, alpha = pixel
        if alpha <= 8:
            return False
        high = max(red, green, blue)
        low = min(red, green, blue)
        saturation = high - low
        if saturation >= 24:
            return True
        return high < 96
