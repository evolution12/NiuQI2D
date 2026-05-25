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

# --- Quality pipeline templates ---

CHARACTER_BASE_IMAGE_TEMPLATE = """
Character design for a 2D game sprite.
Subject: {user_description}
Art style: {style_keywords}
Perspective: {perspective} view
{reference_style_note}
Requirements:
- Single full-body character, centered, standing in a neutral idle pose
- Distinctive silhouette, clear color palette, clean outlines
- All body parts fully visible, no cropping
- Transparent background (alpha=0), no ground, no shadow, no scenery
- If transparency not possible: solid white #FFFFFF background
- {extra_style_keywords}
Negative: NO text, NO logo, NO watermark, NO UI elements, NO grid,
NO background scene, NO extra characters, NO decorative effects,
NO multiple poses, NO animation frames
""".strip()

CHARACTER_DIRECTION_ROW_TEMPLATE = """
2D game sprite animation strip for {action_name}.
CRITICAL — Character orientation (must be identical in every frame):
{orientation_description}
Action: {action_description}
Action detail (applies to ALL frames): {action_details}
Frame count: EXACTLY {frame_count} frames total, no more and no fewer.
Layout: one horizontal row containing exactly {frame_count} evenly-sized frames.
Animation sequence: {frame_count} sequential frames forming one complete {action_name} loop.
- Frame 1 = starting pose
- Frame {frame_count} = final pose that loops back to frame 1
- Each frame shows the next logical step in the {action_name} motion
- All frames share the SAME angle, proportions, colors, and style
Per frame: one complete full-body character, centered, even padding, all body parts inside cell bounds.
Background: fully transparent alpha=0, no ground, no shadow, no scenery.
If transparency not possible: solid white #FFFFFF background.
Style: {style_keywords}, clean outlines, {extra_style_keywords}
Negative: NO merged frames, NO overlapping, NO character spanning multiple frames,
NO text, NO logo, NO watermark, NO UI, NO background scene, NO gradient,
NO extra characters, NO decorative effects, NO borders between frames,
NO other directions, NO other actions, NO missing frames, NO duplicate frames
""".strip()
