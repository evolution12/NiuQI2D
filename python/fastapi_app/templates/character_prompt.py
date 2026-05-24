from __future__ import annotations

CHARACTER_SPRITESHEET_TEMPLATE = """
{style_keywords} sprite sheet of {user_description},
{perspective} view, actions in row groups: {actions},
for each action, create {direction_count} rows (one per direction: {directions}),
{frame_count} columns per row ({frame_count} animation frames for that action and direction),
total grid size is exactly actions times {direction_count} rows by {frame_count} columns,
each cell is an isolated square frame, {cell_width}px x {cell_height}px,
place one complete character pose inside each cell, centered and fully visible,
do not draw one large character spanning multiple cells,
do not crop the character across cell boundaries,
no camera-window effect, no sliding mask, no overlapping cells,
clean grid layout, uniform cell size, clean outlines,
transparent or plain empty background in each cell, no background scene elements,
game asset style,
{extra_style_keywords}
""".strip()

CHARACTER_STATIC_TEMPLATE = """
{style_keywords} character sprite of {user_description},
{perspective} view, centered composition, clean outlines,
{cell_width}px x {cell_height}px, game asset style,
no background elements, single pose,
{extra_style_keywords}
""".strip()
