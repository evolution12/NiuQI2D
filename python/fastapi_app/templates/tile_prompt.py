from __future__ import annotations

TILE_TEMPLATE = """
{style_keywords} tileset of {user_description},
preserve the user's terrain/material exactly, do not invent extra objects, landmarks, buildings, characters, props, or story,
seamless tiles, {tile_width}px x {tile_height}px per tile,
{edge_rule} edges, {terrain_type} terrain,
repeating texture, game asset style,
tileable surface only, no perspective scene, no horizon, no text, no logo, no UI, no complex decoration unless the user asked for it,
{extra_style_keywords}
""".strip()
