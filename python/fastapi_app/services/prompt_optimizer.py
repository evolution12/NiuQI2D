from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import httpx

from ..exceptions import ApiCallFailedError, ApiKeyInvalidError, GenerationTimeoutError, InvalidParamError
from ..models import ArtStyle, AssetSubtype, AssetType, Perspective, StyleProfile
from ..templates.character_prompt import CHARACTER_SPRITESHEET_TEMPLATE, CHARACTER_STATIC_TEMPLATE
from ..templates.tile_prompt import TILE_TEMPLATE

PROMPT_OPTIMIZER_TIMEOUT_SECONDS = 30.0
MAX_PROMPT_CHARS = 4000
TARGET_MAX_WORDS = 500

SYSTEM_PROMPT = """
你是一名专业的游戏美术提示词工程师。请将用户的简短描述转换为准确、稳定、可控的 AI 图像生成提示词。

规则：
1. 保留用户的核心意图。
2. 融入素材类型模板中的专业关键词。
3. 根据风格配置调整视觉语言。
4. 如果提供了参考风格描述，请融合其中的视觉特征。
5. 使用保守的最小扩展策略：只补充生成素材所必需的技术描述，不要把简短描述改写成新的角色、职业、剧情、场景或装备。
6. 用户没有明确提到武器、道具、服装、表情、姿势、背景、特效或多个主体时，不要主动添加。
7. 必须保留用户原始描述中的关键名词、颜色、数量、动作和风格词。
8. 优先强调单一主体、构图清晰、边界干净、背景简单，避免复杂场景和多余装饰。
9. 仅输出中文。
10. 不要输出解释、标题、Markdown 或额外说明，只输出提示词正文。
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
        )
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
    ) -> tuple[str, str]:
        style_keywords = self._style_keywords(style)
        extra_style_keywords = self._extra_style_keywords(style, reference_style_description)
        perspective = self._perspective_keyword(style.perspective if style else Perspective.TOP_DOWN)
        width, height = self._default_size(style)

        if asset_type == AssetType.CHARACTER:
            subtype = asset_subtype or AssetSubtype.STATIC_IMAGE
            if subtype == AssetSubtype.ANIMATED_SPRITESHEET:
                if direction_count not in (1, 2, 4, 8):
                    raise InvalidParamError("角色方向数必须为 1、2、4 或 8")
                if frame_count < 1 or frame_count > 8:
                    raise InvalidParamError("动画帧数必须在 1 到 8 之间")
                action_names = actions or ["idle"]
                return (
                    CHARACTER_SPRITESHEET_TEMPLATE.format(
                        style_keywords=style_keywords,
                        user_description=user_prompt,
                        perspective=perspective,
                        direction_count=direction_count,
                        directions=", ".join(self._directions(direction_count)),
                        frame_count=frame_count,
                        actions=", ".join(action_names),
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
            edge_rule = self._extra_param(style, "edge_rule", "clean seamless")
            terrain_label = terrain_type or self._extra_param(style, "terrain_type", "natural")
            return (
                TILE_TEMPLATE.format(
                    style_keywords=style_keywords,
                    user_description=user_prompt,
                    tile_width=width,
                    tile_height=height,
                    edge_rule=edge_rule,
                    terrain_type=terrain_label,
                    extra_style_keywords=extra_style_keywords,
                ),
                "tile",
            )

        raise InvalidParamError("当前生成引擎仅支持 character 和 tile 素材")

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
            "temperature": 0.15,
            "max_tokens": 800,
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
            parts.extend(f"{key}: {value}" for key, value in style.extra_params.items())
        if reference_style_description:
            parts.append(f"reference style: {reference_style_description.strip()}")
        return ", ".join(parts) if parts else "consistent visual style"

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
        if direction_count == 1:
            return ["front"]
        if direction_count == 2:
            return ["left", "right"]
        if direction_count == 4:
            return ["front", "back", "left", "right"]
        return ["front", "front-right", "right", "back-right", "back", "back-left", "left", "front-left"]

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
