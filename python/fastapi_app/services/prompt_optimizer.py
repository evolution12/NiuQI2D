from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import httpx

from ..exceptions import ApiCallFailedError, ApiKeyInvalidError, GenerationTimeoutError, InvalidParamError
from ..models import ArtStyle, AssetSubtype, AssetType, Perspective, StyleProfile
from ..templates.character_prompt import (
    CHARACTER_BASE_IMAGE_TEMPLATE,
    CHARACTER_DIRECTION_ROW_TEMPLATE,
    CHARACTER_SPRITESHEET_TEMPLATE,
    CHARACTER_STATIC_TEMPLATE,
)
from ..templates.map_prompt import MAP_TEMPLATE
from ..templates.tile_prompt import TILE_TEMPLATE

PROMPT_OPTIMIZER_TIMEOUT_SECONDS = 30.0
MAX_PROMPT_CHARS = 4000
TARGET_MAX_WORDS = 500

SYSTEM_PROMPT = """
You are a professional game art prompt engineer. Convert the user's description into a structured English prompt optimized for text-to-image generation models.

Rules:
1. Output ONLY English. No Chinese.
2. Use comma-separated keywords and short phrases, avoid long sentences.
3. Preserve the user's core intent exactly.
4. Use minimal expansion: only add technical terms necessary for asset generation.
5. Do NOT invent new character identity, job, weapon, props, story, or scene.
6. Emphasize: single subject, clear composition, clean edges, simple/no background.
7. Output only the prompt text — no explanations, no titles, no Markdown.
""".strip()


@dataclass(slots=True)
class OptimizedPrompt:
    prompt: str
    template_used: str
    user_prompt_original: str


class PromptOptimizer:
    def __init__(self, api_provider: str, api_key: str, api_model: str) -> None:
        self.api_provider = api_provider
        self.api_key = api_key
        self.api_model = api_model

    async def optimize(
        self,
        user_prompt: str,
        asset_type: AssetType,
        asset_subtype: AssetSubtype | None = None,
        style: StyleProfile | None = None,
        reference_style_description: str | None = None,
        actions: list[str] | None = None,
        direction_count: int = 4,
        frame_count: int = 3,
        terrain_type: str | None = None,
        target_size: tuple[int, int] | None = None,
        edge_rule: str | None = None,
    ) -> OptimizedPrompt:
        cleaned_prompt = user_prompt.strip()
        if not cleaned_prompt:
            raise InvalidParamError("用户描述不能为空")
        if len(cleaned_prompt) > MAX_PROMPT_CHARS:
            raise InvalidParamError("用户描述过长", {"max_chars": MAX_PROMPT_CHARS})

        template_prompt, template_used = self._build_template_prompt(
            cleaned_prompt,
            asset_type,
            asset_subtype,
            style,
            reference_style_description,
            actions,
            direction_count,
            frame_count,
            terrain_type,
            target_size,
            edge_rule,
        )

        # For sprite sheets: use the structured template directly — the LLM
        # tends to lose grid/layout constraints during optimization.
        # But first translate the user's Chinese description to English keywords.
        # For other asset types: run through the LLM to refine the full prompt.
        if template_used == "character_spritesheet":
            english_desc = await self._translate_subject(cleaned_prompt)
            final_prompt, _ = self._build_template_prompt(
                english_desc,
                asset_type,
                asset_subtype,
                style,
                reference_style_description,
                actions,
                direction_count,
                frame_count,
                terrain_type,
                target_size,
                edge_rule,
            )
            optimized_prompt = final_prompt
        else:
            optimized_prompt = await self._optimize_with_provider(template_prompt)

        return OptimizedPrompt(
            prompt=self._trim_prompt(optimized_prompt),
            template_used=template_used,
            user_prompt_original=user_prompt,
        )

    def _build_template_prompt(
        self,
        user_prompt: str,
        asset_type: AssetType,
        asset_subtype: AssetSubtype | None,
        style: StyleProfile | None,
        reference_style_description: str | None,
        actions: list[str] | None,
        direction_count: int,
        frame_count: int,
        terrain_type: str | None = None,
        target_size: tuple[int, int] | None = None,
        edge_rule: str | None = None,
    ) -> tuple[str, str]:
        style_keywords = self._style_keywords(style)
        extra_style_keywords = self._extra_style_keywords(style, reference_style_description)
        perspective = self._perspective_keyword(style.perspective if style else Perspective.TOP_DOWN)
        # Use user-provided target_size, fallback to style default
        if target_size:
            width, height = target_size
        else:
            width, height = self._default_size(style)

        if asset_type == AssetType.CHARACTER:
            subtype = asset_subtype or AssetSubtype.STATIC_IMAGE
            if subtype == AssetSubtype.ANIMATED_SPRITESHEET:
                if direction_count not in (1, 2, 4, 8):
                    raise InvalidParamError("角色方向数必须为 1、2、4 或 8")
                if frame_count < 1 or frame_count > 8:
                    raise InvalidParamError("动画帧数必须在 1 到 8 之间")
                # Only use the first action for now — multi-action support comes later
                action_name = (actions or ["idle"])[0]
                return (
                    CHARACTER_SPRITESHEET_TEMPLATE.format(
                        style_keywords=style_keywords,
                        user_description=user_prompt,
                        perspective=perspective,
                        direction_count=direction_count,
                        frame_count=frame_count,
                        action_name=action_name,
                        action_description=self._action_description(action_name),
                        row_descriptions=self._build_row_descriptions(direction_count, action_name),
                        cell_width=width,
                        cell_height=height,
                        extra_style_keywords=extra_style_keywords,
                    ),
                    "character_spritesheet",
                )
            return (
                CHARACTER_STATIC_TEMPLATE.format(
                    style_keywords=style_keywords,
                    user_description=user_prompt,
                    perspective=perspective,
                    cell_width=width,
                    cell_height=height,
                    extra_style_keywords=extra_style_keywords,
                ),
                "character_static",
            )

        if asset_type == AssetType.TILE:
            effective_edge_rule = edge_rule or self._extra_param(style, "edge_rule", "clean seamless")
            terrain_label = terrain_type or self._extra_param(style, "terrain_type", "natural")
            return (
                TILE_TEMPLATE.format(
                    style_keywords=style_keywords,
                    user_description=user_prompt,
                    tile_width=width,
                    tile_height=height,
                    edge_rule=effective_edge_rule,
                    terrain_type=terrain_label,
                    extra_style_keywords=extra_style_keywords,
                ),
                "tile",
            )

        if asset_type == AssetType.MAP:
            return (
                MAP_TEMPLATE.format(
                    style_keywords=style_keywords,
                    user_description=user_prompt,
                    width=width,
                    height=height,
                    extra_style_keywords=extra_style_keywords,
                ),
                "map",
            )

        raise InvalidParamError("当前生成引擎仅支持 character、tile、map 素材")

    # OpenAI 兼容接口的 base URL 映射
    _BASE_URLS: dict[str, str] = {
        "openai": "https://api.openai.com/v1",
        "deepseek": "https://api.deepseek.com",
        "doubao": "https://ark.cn-beijing.volces.com/api/v3",
    }

    async def _optimize_with_provider(self, template_prompt: str) -> str:
        if not self.api_key:
            raise ApiKeyInvalidError("未配置文本生成 API Key")

        base_url = self._BASE_URLS.get(self.api_provider)
        if not base_url:
            raise InvalidParamError(f"暂不支持文本生成提供商 {self.api_provider}")

        payload: dict[str, Any] = {
            "model": self.api_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": template_prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 1000,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=PROMPT_OPTIMIZER_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            raise GenerationTimeoutError("Prompt 优化请求超时") from exc
        except httpx.HTTPError as exc:
            raise ApiCallFailedError("Prompt 优化 API 请求失败", {"provider": self.api_provider}) from exc

        if response.status_code in (401, 403):
            raise ApiKeyInvalidError("文本生成 API Key 无效")
        if response.status_code >= 400:
            raise ApiCallFailedError(
                "Prompt 优化 API 返回错误",
                {"status_code": response.status_code, "body": response.text[:500]},
            )

        data = response.json()
        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ApiCallFailedError("Prompt 优化 API 响应格式无效") from exc
        content = message.get("content") or message.get("reasoning_content") or ""
        if not isinstance(content, str) or not content.strip():
            raise ApiCallFailedError("Prompt 优化 API 返回空结果")
        await asyncio.sleep(0)
        return content.strip()

    def _style_keywords(self, style: StyleProfile | None) -> str:
        if style is None:
            return "clean 2D game art"
        keywords = {
            ArtStyle.PIXEL: "crisp pixel art, limited palette, hard edges",
            ArtStyle.HAND_DRAWN: "hand drawn 2D art, expressive lines",
            ArtStyle.CARTOON: "cartoon 2D art, bold readable shapes",
            ArtStyle.REALISTIC: "realistic painted 2D game art",
            ArtStyle.CUSTOM: "custom 2D game art",
        }
        return keywords[style.art_style]

    def _extra_style_keywords(
        self,
        style: StyleProfile | None,
        reference_style_description: str | None,
    ) -> str:
        parts: list[str] = []
        if style and style.color_palette:
            parts.append(f"palette: {', '.join(style.color_palette)}")
        if style and style.extra_params:
            for key, value in style.extra_params.items():
                parts.append(f"{key}: {value}")
        if reference_style_description:
            parts.append(f"reference style: {reference_style_description.strip()}")
        return ", ".join(parts) if parts else "consistent style"

    def _default_size(self, style: StyleProfile | None) -> tuple[int, int]:
        if style is None:
            return (16, 16)
        width = int(style.default_size.get("w", 16))
        height = int(style.default_size.get("h", width))
        return (width, height)

    def _perspective_keyword(self, perspective: Perspective) -> str:
        labels = {
            Perspective.TOP_DOWN: "top-down",
            Perspective.SIDE_SCROLLER: "side-scroller side",
            Perspective.ISOMETRIC: "isometric",
        }
        return labels[perspective]

    def _directions(self, direction_count: int) -> list[str]:
        """Return direction names using 2D game convention (screen-space)."""
        if direction_count == 1:
            return ["down"]
        if direction_count == 2:
            return ["left", "right"]
        if direction_count == 4:
            return ["up", "down", "left", "right"]
        return ["up", "up-right", "right", "down-right", "down", "down-left", "left", "up-left"]

    # Direction label map for row descriptions
    _DIRECTION_LABELS: dict[str, str] = {
        "down": "facing DOWN (toward the viewer, showing character's front)",
        "up": "facing UP (away from the viewer, showing character's back)",
        "left": "facing LEFT",
        "right": "facing RIGHT",
        "up-right": "facing UP-RIGHT (walking diagonally upper-right)",
        "up-left": "facing UP-LEFT (walking diagonally upper-left)",
        "down-right": "facing DOWN-RIGHT (walking diagonally lower-right)",
        "down-left": "facing DOWN-LEFT (walking diagonally lower-left)",
    }

    # Detailed orientation descriptions for direction-row generation
    _DIRECTION_ORIENTATIONS: dict[str, str] = {
        "down": (
            "Front view — the character faces TOWARD the viewer. "
            "Face, chest, and front of the body are FULLY visible. "
            "You CAN see the eyes, mouth, and front details. "
            "This is the character's FRONT — NOT the back."
        ),
        "up": (
            "Back view — the character faces AWAY from the viewer. "
            "Back, back of the head, and rear of the body are FULLY visible. "
            "You CANNOT see the face, eyes, or front of the body. "
            "This is the character's BACK — NOT the front."
        ),
        "left": (
            "Side view — the character is MOVING to the LEFT. "
            "The character's FACE is turned toward the LEFT side of the image. "
            "The character's HEAD points to the LEFT. "
            "The entire body faces LEFT. "
            "This is NOT a mirror — do NOT face the character to the right."
        ),
        "right": (
            "Side view — the character is MOVING to the RIGHT. "
            "The character's FACE is turned toward the RIGHT side of the image. "
            "The character's HEAD points to the RIGHT. "
            "The entire body faces RIGHT. "
            "This is NOT a mirror — do NOT face the character to the left."
        ),
        "up-right": (
            "The character is facing UP-RIGHT (diagonal back-right view). "
            "You see the character's back and right side. "
            "The character moves toward the upper-right corner."
        ),
        "up-left": (
            "The character is facing UP-LEFT (diagonal back-left view). "
            "You see the character's back and left side. "
            "The character moves toward the upper-left corner."
        ),
        "down-right": (
            "The character is facing DOWN-RIGHT (diagonal front-right view). "
            "You see the character's front and right side. "
            "The character moves toward the lower-right corner."
        ),
        "down-left": (
            "The character is facing DOWN-LEFT (diagonal front-left view). "
            "You see the character's front and left side. "
            "The character moves toward the lower-left corner."
        ),
    }

    def _build_row_descriptions(self, direction_count: int, action: str) -> str:
        """Generate explicit per-row direction labels for the template."""
        directions = self._directions(direction_count)
        lines = []
        for i, d in enumerate(directions):
            label = self._DIRECTION_LABELS.get(d, d)
            lines.append(f"Row {i + 1}: character {action} {label}")
        return "\n".join(lines)

    _ACTION_DESCRIPTIONS: dict[str, str] = {
        "idle": (
            "idle standing pose — subtle breathing/swaying motion. "
            "Each frame is a slightly different phase of the idle loop."
        ),
        "walk": (
            "walk cycle — character walks forward in-place. "
            "Frames show sequential leg positions: stride, contact, push-off. "
            "Arms swing opposite to legs. Clear alternation between left and right limbs."
        ),
        "attack": (
            "attack sequence — character performs an attack motion. "
            "Frames show: wind-up/preparation → strike/contact → follow-through/recovery. "
            "Weapon or limb moves through the full arc of the attack."
        ),
        "hurt": (
            "hurt/flinch reaction — character takes damage and recoils. "
            "Frames show: impact frame → stagger backward → recovery to standing. "
            "Body bends and recoils from the hit direction."
        ),
        "die": (
            "death/collapse sequence — character falls from standing to fallen. "
            "Frames show: initial buckle → falling motion → lying on ground."
        ),
    }

    def _action_description(self, action: str) -> str:
        return self._ACTION_DESCRIPTIONS.get(action, f"{action} animation sequence")

    async def _translate_subject(self, user_prompt: str) -> str:
        """Translate user's Chinese description to concise English subject keywords.

        This is used for sprite sheets where the full template goes directly
        to the image API — we need the subject in English but don't want
        the LLM to touch the structural layout constraints.
        """
        translate_prompt = (
            f"Convert this game asset description to concise English keywords "
            f"(3-8 words, comma-separated, describe the visual subject only).\n\n"
            f"Description: {user_prompt}\n\n"
            f"English keywords:"
        )
        payload: dict[str, Any] = {
            "model": self.api_model,
            "messages": [
                {"role": "system", "content": "Output only English keywords. No explanations."},
                {"role": "user", "content": translate_prompt},
            ],
            "temperature": 0.0,
            "max_tokens": 60,
        }
        base_url = self._BASE_URLS.get(self.api_provider)
        if not base_url:
            return user_prompt
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
            if response.status_code >= 400:
                return user_prompt
            data = response.json()
            content = data["choices"][0]["message"].get("content") or ""
            # Strip quotes, newlines, explanations
            content = content.strip().strip('"').strip("'")
            # Take only the first line
            content = content.split("\n")[0].strip()
            return content if content else user_prompt
        except Exception:
            return user_prompt

    def _extra_param(self, style: StyleProfile | None, key: str, default: str) -> str:
        if style is None or not style.extra_params:
            return default
        value = style.extra_params.get(key, default)
        return str(value)

    def _trim_prompt(self, prompt: str) -> str:
        words = prompt.split()
        if len(words) <= TARGET_MAX_WORDS:
            return prompt
        return " ".join(words[:TARGET_MAX_WORDS])

    # ------------------------------------------------------------------
    # Quality pipeline methods
    # ------------------------------------------------------------------

    async def optimize_base_character(
        self,
        user_prompt: str,
        style: StyleProfile | None = None,
        reference_style_description: str | None = None,
    ) -> OptimizedPrompt:
        """Step 1: Build prompt for generating a single base character image."""
        cleaned_prompt = user_prompt.strip()
        if not cleaned_prompt:
            raise InvalidParamError("用户描述不能为空")

        english_desc = await self._translate_subject(cleaned_prompt)
        style_keywords = self._style_keywords(style)
        extra_style_keywords = self._extra_style_keywords(style, reference_style_description)
        perspective = self._perspective_keyword(style.perspective if style else Perspective.TOP_DOWN)

        reference_note = ""
        if reference_style_description:
            reference_note = (
                f"Style reference: match the visual style described as \"{reference_style_description.strip()}\", "
                f"maintain consistent art style and color palette."
            )

        prompt = CHARACTER_BASE_IMAGE_TEMPLATE.format(
            style_keywords=style_keywords,
            user_description=english_desc,
            perspective=perspective,
            reference_style_note=reference_note,
            extra_style_keywords=extra_style_keywords,
        )
        return OptimizedPrompt(
            prompt=self._trim_prompt(prompt),
            template_used="character_base_image",
            user_prompt_original=user_prompt,
        )

    async def generate_action_details(
        self,
        character_description: str,
        action: str,
    ) -> str:
        """Generate a unified action-detail description via LLM.

        This ensures all directions use the SAME physical motion mechanics
        (e.g. a duck always pecks with its beak, not claws or wings).
        """
        if not self.api_key:
            return ""

        base_url = self._BASE_URLS.get(self.api_provider)
        if not base_url:
            return ""

        system_msg = (
            "You are a game animation designer. "
            "Given a character and an action, output 1-2 concise English sentences "
            "describing HOW this specific character physically performs the action. "
            "Be specific about body parts and movement. "
            "Output ONLY the description text — no explanations, no titles, no quotes."
        )

        user_msg = (
            f"Character: {character_description}\n"
            f"Action: {action}\n\n"
            f"Describe the physical motion (e.g. 'pecking forward with beak', "
            f"'swinging sword in an overhead arc', 'rearing up on hind legs').\n"
            f"Do NOT mention direction, camera angle, or orientation.\n\n"
            f"Action detail description:"
        )

        payload: dict[str, Any] = {
            "model": self.api_model,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            "temperature": 0.2,
            "max_tokens": 120,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=PROMPT_OPTIMIZER_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
            if response.status_code >= 400:
                return ""
            data = response.json()
            content = data["choices"][0]["message"].get("content") or ""
            content = content.strip().strip('"').strip("'")
            content = content.split("\n")[0].strip()
            return content
        except Exception:
            return ""

    def optimize_direction_row(
        self,
        direction: str,
        frame_count: int,
        action: str,
        action_details: str = "",
        style: StyleProfile | None = None,
    ) -> OptimizedPrompt:
        """Step 2: Build prompt for generating a single direction animation row."""
        style_keywords = self._style_keywords(style)
        extra_style_keywords = self._extra_style_keywords(style, None)

        orientation_description = self._DIRECTION_ORIENTATIONS.get(direction, direction)
        action_description = self._action_description(action)

        prompt = CHARACTER_DIRECTION_ROW_TEMPLATE.format(
            style_keywords=style_keywords,
            action_description=action_description,
            action_details=action_details or "performing the action naturally",
            frame_count=frame_count,
            action_name=action,
            orientation_description=orientation_description,
            extra_style_keywords=extra_style_keywords,
        )
        return OptimizedPrompt(
            prompt=self._trim_prompt(prompt),
            template_used="character_direction_row",
            user_prompt_original="",
        )
