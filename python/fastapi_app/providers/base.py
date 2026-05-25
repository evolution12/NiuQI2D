from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..exceptions import InvalidParamError


class GenerationMode(str, Enum):
    PREVIEW = "preview"
    QUALITY = "quality"


@dataclass(slots=True)
class CostEstimate:
    provider: str
    model: str
    image_count: int
    estimated_usd: float
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class GeneratedImage:
    image_data: bytes
    seed: str | None
    revised_prompt: str | None
    size: tuple[int, int]
    metadata: dict[str, Any] = field(default_factory=dict)


class ImageGeneratorBase(ABC):
    provider_name: str
    model: str

    # Subclasses can override to change the max n value
    MAX_N: int = 6

    # Retry configuration — subclasses override these
    RETRY_BASE_DELAY_SECONDS: float = 1.0

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        size: tuple[int, int] = (1024, 1024),
        n: int = 1,
        transparent_background: bool = False,
        seed: str | None = None,
    ) -> list[GeneratedImage]:
        raise NotImplementedError

    async def generate_with_reference(
        self,
        prompt: str,
        reference_image: bytes,
        size: tuple[int, int] = (1024, 1024),
        n: int = 1,
        transparent_background: bool = False,
        seed: str | None = None,
    ) -> list[GeneratedImage]:
        """带参考图的生成。各 provider 自行决定如何利用参考图。"""
        return await self.generate(prompt, size, n, transparent_background, seed)

    @abstractmethod
    def estimate_cost(
        self,
        n: int = 1,
        size: tuple[int, int] = (1024, 1024),
        quality: str | None = None,
    ) -> CostEstimate:
        raise NotImplementedError

    def _validate_args(self, prompt: str, size: tuple[int, int], n: int) -> None:
        if not prompt.strip():
            raise InvalidParamError("生成 Prompt 不能为空")
        if n < 1 or n > self.MAX_N:
            raise InvalidParamError(f"候选数量必须在 1 到 {self.MAX_N} 之间")
        if size[0] <= 0 or size[1] <= 0:
            raise InvalidParamError("图片尺寸必须为正整数")

    async def _sleep_before_retry(self, attempt: int) -> None:
        delay = self.RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1))
        await asyncio.sleep(delay)

