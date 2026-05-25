from __future__ import annotations

import base64
import io
from typing import Any

import httpx

from ..exceptions import ApiCallFailedError, ApiKeyInvalidError, GenerationTimeoutError, InvalidParamError
from .base import CostEstimate, GeneratedImage, ImageGeneratorBase

OPENAI_IMAGE_URL = "https://api.openai.com/v1/images/generations"
OPENAI_EDITS_URL = "https://api.openai.com/v1/images/edits"
GENERATION_TIMEOUT_SECONDS = 60.0
MAX_RETRIES = 3
RETRY_BASE_DELAY_SECONDS = 1.0

GPT_IMAGE_MAX_BATCH = 4
DALL_E_3_ALLOWED_SIZES = {(1024, 1024), (1792, 1024), (1024, 1792)}
GPT_IMAGE_ALLOWED_SIZES = {(1024, 1024), (1536, 1024), (1024, 1536)}


class OpenAIProvider(ImageGeneratorBase):
    provider_name = "openai"

    def __init__(
        self,
        api_key: str,
        model: str,
        quality: str = "standard",
        timeout_seconds: float = GENERATION_TIMEOUT_SECONDS,
        max_retries: int = MAX_RETRIES,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.quality = quality
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    async def generate(
        self,
        prompt: str,
        size: tuple[int, int] = (1024, 1024),
        n: int = 1,
        transparent_background: bool = False,
        seed: str | None = None,
    ) -> list[GeneratedImage]:
        self._validate_generate_args(prompt, size, n)
        if self._is_dall_e_3:
            return await self._generate_dall_e_3(prompt, size, n, seed)
        return await self._generate_gpt_image(prompt, size, n, transparent_background, seed)

    async def generate_with_reference(
        self,
        prompt: str,
        reference_image: bytes,
        size: tuple[int, int] = (1024, 1024),
        n: int = 1,
        transparent_background: bool = False,
        seed: str | None = None,
    ) -> list[GeneratedImage]:
        self._validate_generate_args(prompt, size, n)
        if self._is_dall_e_3:
            return await self._generate_dall_e_3(prompt, size, n, seed)
        return await self._generate_gpt_image_edit(prompt, reference_image, size, n, transparent_background, seed)

    def estimate_cost(
        self,
        n: int = 1,
        size: tuple[int, int] = (1024, 1024),
        quality: str | None = None,
    ) -> CostEstimate:
        selected_quality = quality or self.quality
        unit_cost = self._unit_cost(size, selected_quality)
        estimated = round(unit_cost * n, 4)
        return CostEstimate(
            provider=self.provider_name,
            model=self.model,
            image_count=n,
            estimated_usd=estimated,
            details={"unit_cost_usd": unit_cost, "quality": selected_quality, "size": self._size_string(size)},
        )

    async def _generate_dall_e_3(
        self,
        prompt: str,
        size: tuple[int, int],
        n: int,
        seed: str | None,
    ) -> list[GeneratedImage]:
        if size not in DALL_E_3_ALLOWED_SIZES:
            raise InvalidParamError("dall-e-3 仅支持 1024x1024、1792x1024、1024x1792")
        images: list[GeneratedImage] = []
        for _ in range(n):
            payload = {
                "model": self.model,
                "prompt": prompt,
                "size": self._size_string(size),
                "quality": self.quality,
                "n": 1,
                "response_format": "b64_json",
            }
            data = await self._post_with_retry(payload)
            images.extend(self._parse_images(data, size, seed))
        return images

    async def _generate_gpt_image(
        self,
        prompt: str,
        size: tuple[int, int],
        n: int,
        transparent_background: bool,
        seed: str | None,
    ) -> list[GeneratedImage]:
        if size not in GPT_IMAGE_ALLOWED_SIZES:
            raise InvalidParamError("gpt-image-1 仅支持 1024x1024、1536x1024、1024x1536")
        images: list[GeneratedImage] = []
        remaining = n
        while remaining > 0:
            batch_size = min(remaining, GPT_IMAGE_MAX_BATCH)
            payload: dict[str, Any] = {
                "model": self.model,
                "prompt": prompt,
                "size": self._size_string(size),
                "n": batch_size,
                "output_format": "png",
            }
            if transparent_background:
                payload["background"] = "transparent"
            data = await self._post_with_retry(payload)
            images.extend(self._parse_images(data, size, seed))
            remaining -= batch_size
        return images[:n]

    async def _generate_gpt_image_edit(
        self,
        prompt: str,
        reference_image: bytes,
        size: tuple[int, int],
        n: int,
        transparent_background: bool,
        seed: str | None,
    ) -> list[GeneratedImage]:
        if size not in GPT_IMAGE_ALLOWED_SIZES:
            raise InvalidParamError("gpt-image-1 仅支持 1024x1024、1536x1024、1024x1536")
        images: list[GeneratedImage] = []
        remaining = n
        while remaining > 0:
            batch_size = min(remaining, GPT_IMAGE_MAX_BATCH)
            data = await self._post_edit_with_retry(
                prompt=prompt,
                reference_image=reference_image,
                size=size,
                n=batch_size,
                transparent_background=transparent_background,
            )
            images.extend(self._parse_images(data, size, seed))
            remaining -= batch_size
        return images[:n]

    async def _post_edit_with_retry(
        self,
        prompt: str,
        reference_image: bytes,
        size: tuple[int, int],
        n: int,
        transparent_background: bool,
    ) -> dict[str, Any]:
        if not self.api_key:
            raise ApiKeyInvalidError("未配置图片生成 API Key")

        headers = {"Authorization": f"Bearer {self.api_key}"}

        last_error: ApiCallFailedError | GenerationTimeoutError | None = None
        for attempt in range(1, self.max_retries + 1):
            form_files: list[tuple[str, Any]] = []

            # Build multipart form data
            fields = {
                "model": self.model,
                "prompt": prompt,
                "size": self._size_string(size),
                "n": str(n),
            }
            if transparent_background:
                fields["background"] = "transparent"

            form_files = [(k, (None, v)) for k, v in fields.items()]
            form_files.append(("image", ("reference.png", io.BytesIO(reference_image), "image/png")))

            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.post(
                        OPENAI_EDITS_URL,
                        headers=headers,
                        files=form_files,
                    )
            except httpx.TimeoutException as exc:
                last_error = GenerationTimeoutError(
                    "图片编辑请求超时",
                    {"attempt": attempt, "max_retries": self.max_retries},
                )
                if attempt >= self.max_retries:
                    raise last_error from exc
                await self._sleep_before_retry(attempt)
                continue
            except httpx.HTTPError as exc:
                last_error = ApiCallFailedError(
                    "图片编辑 API 请求失败",
                    {"attempt": attempt, "provider": self.provider_name},
                )
                if attempt >= self.max_retries:
                    raise last_error from exc
                await self._sleep_before_retry(attempt)
                continue

            if response.status_code in (401, 403):
                raise ApiKeyInvalidError("图片生成 API Key 无效")
            if response.status_code in (408, 429) or response.status_code >= 500:
                last_error = ApiCallFailedError(
                    "图片编辑 API 暂时不可用",
                    {"attempt": attempt, "status_code": response.status_code, "body": response.text[:500]},
                )
                if attempt >= self.max_retries:
                    raise last_error
                await self._sleep_before_retry(attempt)
                continue
            if response.status_code >= 400:
                raise ApiCallFailedError(
                    "图片编辑 API 返回错误",
                    {"status_code": response.status_code, "body": response.text[:500]},
                )
            return response.json()

        raise last_error or ApiCallFailedError("图片编辑失败")

    def _parse_images(self, data: dict[str, Any], size: tuple[int, int], seed: str | None) -> list[GeneratedImage]:
        items = data.get("data")
        if not isinstance(items, list):
            raise ApiCallFailedError("图片生成 API 响应格式无效")

        images: list[GeneratedImage] = []
        for item in items:
            if not isinstance(item, dict):
                raise ApiCallFailedError("图片生成 API 响应条目格式无效")
            encoded = item.get("b64_json")
            if not isinstance(encoded, str):
                raise ApiCallFailedError("图片生成 API 未返回 PNG 二进制")
            try:
                image_data = base64.b64decode(encoded)
            except ValueError as exc:
                raise ApiCallFailedError("图片生成 API 返回的图片编码无效") from exc
            images.append(
                GeneratedImage(
                    image_data=image_data,
                    seed=seed,
                    revised_prompt=item.get("revised_prompt") if isinstance(item.get("revised_prompt"), str) else None,
                    size=size,
                    metadata={
                        "provider": self.provider_name,
                        "model": self.model,
                        "raw_response_keys": sorted(item.keys()),
                    },
                )
            )
        return images

    def _validate_generate_args(self, prompt: str, size: tuple[int, int], n: int) -> None:
        self._validate_args(prompt, size, n)

    def _unit_cost(self, size: tuple[int, int], quality: str) -> float:
        if self._is_dall_e_3:
            if size == (1024, 1024):
                return 0.08 if quality == "hd" else 0.04
            return 0.12 if quality == "hd" else 0.08
        megapixels = (size[0] * size[1]) / 1_000_000
        return round(0.04 * megapixels, 4)

    def _size_string(self, size: tuple[int, int]) -> str:
        return f"{size[0]}x{size[1]}"

    @property
    def _is_dall_e_3(self) -> bool:
        return self.model.lower() == "dall-e-3"
