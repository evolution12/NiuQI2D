from __future__ import annotations

CHARACTER_SPRITESHEET_TEMPLATE = """
{style_keywords} sprite sheet of {user_description},
{perspective} view, {direction_count} rows (one per direction: {directions}),
{frame_count} columns per row ({frame_count} animation frames per direction),
actions: {actions},
each cell {cell_width}px x {cell_height}px,
arranged in a clean grid layout with no overlap, uniform cell size,
character centered in each cell, clean outlines,
game asset style, no background elements,
{extra_style_keywords}
""".strip()

CHARACTER_STATIC_TEMPLATE = """
{style_keywords} character sprite of {user_description},
{perspective} view, centered composition, clean outlines,
{cell_width}px x {cell_height}px, game asset style,
no background elements, single pose,
{extra_style_keywords}
""".strip()

