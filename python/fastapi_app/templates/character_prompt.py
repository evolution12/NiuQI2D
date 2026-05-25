from __future__ import annotations

CHARACTER_SPRITESHEET_TEMPLATE = """
{style_keywords} sprite sheet, {user_description},
{perspective} view, {action_description},
EXACT grid layout: {direction_count} rows × {frame_count} columns,
each cell exactly {cell_width}px × {cell_height}px, uniform square cells,
{row_descriptions},
each row has {frame_count} sequential frames forming a seamless looping {action_name} animation,
progressive body movement across frames, last frame loops smoothly back to frame 1,
one complete full-body character per cell, centered, even padding on all sides,
all body parts stay inside the cell, no cropping at cell boundaries,
fully transparent background alpha=0 in every cell, no ground plane no shadow no scenery,
if transparency not possible then solid pure white #FFFFFF background no texture,
clean outlines, uniform grid, game-ready sprite asset, single subject per cell,
{extra_style_keywords},
NO merged cells, NO overlapping cells, NO character spanning multiple cells,
NO cropping at edges, NO text, NO logo, NO watermark, NO UI elements,
NO background scene, NO gradient, NO pattern, NO extra characters,
NO decorative effects, NO out-of-grid elements, NO borders between cells
""".strip()

CHARACTER_STATIC_TEMPLATE = """
{style_keywords} character sprite, {user_description},
{perspective} view, centered composition, clean outlines,
single pose, {cell_width}px × {cell_height}px,
fully transparent background alpha=0, no background elements no ground no shadow,
if transparency not possible then solid pure white #FFFFFF background no texture,
game-ready asset, single subject,
{extra_style_keywords},
NO text, NO logo, NO watermark, NO UI elements,
NO background scene, NO extra characters, NO decorative effects
""".strip()
