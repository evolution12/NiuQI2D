from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


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

