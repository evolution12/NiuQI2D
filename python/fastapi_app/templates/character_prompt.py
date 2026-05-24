from __future__ import annotations

CHARACTER_SPRITESHEET_TEMPLATE = """
{style_keywords} sprite sheet of {user_description},
preserve the user's subject exactly, do not invent extra character identity, job, weapon, props, story, or scene,
{perspective} view, actions in row groups: {actions},
for each action, create {direction_count} rows (one per direction: {directions}),
{frame_count} columns per row ({frame_count} animation frames for that action and direction),
total grid size is exactly actions times {direction_count} rows by {frame_count} columns,
each cell is an isolated square frame, {cell_width}px x {cell_height}px,
place one complete full-body character pose inside each cell, centered and fully visible,
leave clear padding around the character inside every cell,
head, feet, hands, weapon, tail, clothing, and silhouette must all stay inside the same cell,
do not draw one large character spanning multiple cells,
do not crop the character across cell boundaries,
do not touch the cell edges,
no camera-window effect, no sliding mask, no overlapping cells,
clean grid layout, uniform cell size, clean outlines,
transparent or plain empty background in each cell, no background scene elements,
single subject per cell, no text, no logo, no UI, no decorative effects unless the user asked for them,
game asset style,
{extra_style_keywords}
""".strip()

CHARACTER_STATIC_TEMPLATE = """
{style_keywords} character sprite of {user_description},
preserve the user's subject exactly, do not invent extra character identity, job, weapon, props, story, or scene,
{perspective} view, centered composition, clean outlines,
{cell_width}px x {cell_height}px, game asset style,
no background elements, single pose, single subject, no text, no logo, no UI,
no decorative effects, extra props, complex clothing, or environment details unless the user asked for them,
{extra_style_keywords}
""".strip()
