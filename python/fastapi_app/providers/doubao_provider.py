from __future__ import annotations

import asyncio
import base64
import io
import logging
from typing import Any

import httpx

from ..exceptions import ApiCallFailedError, ApiKeyInvalidError, GenerationTimeoutError, InvalidParamError
from .base import CostEstimate, GeneratedImage, ImageGeneratorBase

logger = logging.getLogger(__name__)

ARK_API_URL = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
ARK_EDITS_URL = "https://ark.cn-beijing.volces.com/api/v3/images/edits"
GENERATION_TIMEOUT_SECONDS = 120.0
MAX_RETRIES = 3
RETRY_BASE_DELAY_SECONDS = 2.0

# doubao-seedream-4-5 要求最低约 3,686,400 像素（≈1920×1920）
ALLOWED_SIZES = [
    "2048x2048", "1920x1920", "1920x1080", "1080x1920",
    "2048x1152", "1152x2048",
]


class DoubaoArkProvider(ImageGeneratorBase):
    """火山引擎 Ark 平台豆包文生图 Provider（OpenAI 兼容接口）"""

    provider_name = "doubao"

    def __init__(
        self,
        api_key: str,
        model: str = "doubao-seedream-4-5-251128",
        timeout_seconds: float = GENERATION_TIMEOUT_SECONDS,
        max_retries: int = MAX_RETRIES,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    # doubao-seedream 模型最低像素数要求
    MIN_PIXELS = 3_686_400

    async def generate(
        self,
        prompt: str,
        size: tuple[int, int] = (1024, 1024),
        n: int = 1,
        transparent_background: bool = False,
        seed: str | None = None,
    ) -> list[GeneratedImage]:
        self._validate_args(prompt, size, n)

        size = self._adjust_size(size)

        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "size": f"{size[0]}x{size[1]}",
            "n": n,
            "response_format": "b64_json",
        }

        data = await self._post_with_retry(payload)
        return self._parse_response(data, size, seed)

    async def generate_with_reference(
        self,
        prompt: str,
        reference_image: bytes,
        size: tuple[int, int] = (1024, 1024),
        n: int = 1,
        transparent_background: bool = False,
        seed: str | None = None,
    ) -> list[GeneratedImage]:
        self._validate_args(prompt, size, n)

        size = self._adjust_size(size)

        image_b64 = base64.b64encode(reference_image).decode("ascii")
        # Try data-URI format which some APIs expect for inline base64 images
        image_data_uri = f"data:image/png;base64,{image_b64}"
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "size": f"{size[0]}x{size[1]}",
            "n": n,
            "response_format": "b64_json",
            "image": image_data_uri,
        }

        print(f"[Doubao] generate_with_reference: size={size}, prompt_len={len(prompt)}, image_data_uri_len={len(image_data_uri)}")
        data = await self._post_with_retry(payload)
        return self._parse_response(data, size, seed)

    def _adjust_size(self, size: tuple[int, int]) -> tuple[int, int]:
        """Adjust size to meet seedream minimum pixel requirements."""
        if size[0] * size[1] < self.MIN_PIXELS:
            scale = (self.MIN_PIXELS / (size[0] * size[1])) ** 0.5
            old_size = size
            size = (round(size[0] * scale), round(size[1] * scale))
            logger.info("尺寸 %s 低于最低像素要求，已调整为 %s", old_size, size)
        return size

    def estimate_cost(
        self,
        n: int = 1,
        size: tuple[int, int] = (1024, 1024),
        quality: str | None = None,
    ) -> CostEstimate:
        return CostEstimate(
            provider=self.provider_name,
            model=self.model,
            image_count=n,
            estimated_usd=0.0,
            details={"note": "豆包文生图按调用次数计费，具体价格参考火山引擎官网"},
        )

    async def _post_with_retry(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key:
            raise ApiKeyInvalidError("未配置豆包 API Key")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        last_error: ApiCallFailedError | GenerationTimeoutError | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.post(
                        ARK_API_URL,
                        headers=headers,
                        json=payload,
                    )
            except httpx.TimeoutException as exc:
                last_error = GenerationTimeoutError(
                    "豆包文生图请求超时",
                    {"attempt": attempt, "max_retries": self.max_retries},
                )
                if attempt >= self.max_retries:
                    raise last_error from exc
                await self._sleep_before_retry(attempt)
                continue
            except httpx.HTTPError as exc:
                last_error = ApiCallFailedError(
                    "豆包文生图 API 请求失败",
                    {"attempt": attempt, "provider": self.provider_name},
                )
                if attempt >= self.max_retries:
                    raise last_error from exc
                await self._sleep_before_retry(attempt)
                continue

            if response.status_code in (401, 403):
                raise ApiKeyInvalidError("豆包 API Key 无效")
            if response.status_code in (408, 429) or response.status_code >= 500:
                last_error = ApiCallFailedError(
                    "豆包文生图 API 暂时不可用",
                    {"attempt": attempt, "status_code": response.status_code, "body": response.text[:500]},
                )
                if attempt >= self.max_retries:
                    raise last_error
                await self._sleep_before_retry(attempt)
                continue
            if response.status_code >= 400:
                err_body = response.text[:800]
                print(f"[Doubao] generations API error: status={response.status_code}, body={err_body}")
                raise ApiCallFailedError(
                    f"豆包文生图 API 返回错误 (status={response.status_code})",
                    {"status_code": response.status_code, "body": err_body},
                )

            return response.json()

        raise last_error or ApiCallFailedError("豆包文生图生成失败")

    async def _post_edit_with_retry(self, form_files: list[tuple[str, Any]]) -> dict[str, Any]:
        """POST multipart form to /images/edits endpoint (with reference image)."""
        if not self.api_key:
            raise ApiKeyInvalidError("未配置豆包 API Key")

        headers = {"Authorization": f"Bearer {self.api_key}"}

        last_error: ApiCallFailedError | GenerationTimeoutError | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.post(
                        ARK_EDITS_URL,
                        headers=headers,
                        files=form_files,
                    )
            except httpx.TimeoutException as exc:
                last_error = GenerationTimeoutError(
                    "豆包图片编辑请求超时",
                    {"attempt": attempt, "max_retries": self.max_retries},
                )
                if attempt >= self.max_retries:
                    raise last_error from exc
                await self._sleep_before_retry(attempt)
                continue
            except httpx.HTTPError as exc:
                last_error = ApiCallFailedError(
                    "豆包图片编辑 API 请求失败",
                    {"attempt": attempt, "provider": self.provider_name},
                )
                if attempt >= self.max_retries:
                    raise last_error from exc
                await self._sleep_before_retry(attempt)
                continue

            if response.status_code in (401, 403):
                raise ApiKeyInvalidError("豆包 API Key 无效")
            if response.status_code in (408, 429) or response.status_code >= 500:
                last_error = ApiCallFailedError(
                    "豆包图片编辑 API 暂时不可用",
                    {"attempt": attempt, "status_code": response.status_code, "body": response.text[:500]},
                )
                if attempt >= self.max_retries:
                    raise last_error
                await self._sleep_before_retry(attempt)
                continue
            if response.status_code >= 400:
                err_body = response.text[:800]
                print(f"[Doubao] API error: status={response.status_code}, body={err_body}")
                raise ApiCallFailedError(
                    f"豆包图片编辑 API 返回错误 (status={response.status_code})",
                    {"status_code": response.status_code, "body": err_body},
                )

            return response.json()

        raise last_error or ApiCallFailedError("豆包图片编辑失败")

    def _parse_response(
        self,
        data: dict[str, Any],
        size: tuple[int, int],
        seed: str | None,
    ) -> list[GeneratedImage]:
        images: list[GeneratedImage] = []

        items = data.get("data", [])
        if not items:
            raise ApiCallFailedError(
                "豆包文生图响应中未找到图片数据",
                {"response_keys": sorted(data.keys())},
            )

        for item in items:
            b64_str = item.get("b64_json", "")
            if not b64_str:
                # 尝试 url 模式
                url = item.get("url", "")
                if url:
                    logger.info("收到图片 URL: %s", url[:80])
                continue

            try:
                image_data = base64.b64decode(b64_str)
            except ValueError:
                logger.warning("跳过无效的 base64 图片数据")
                continue

            images.append(
                GeneratedImage(
                    image_data=image_data,
                    seed=seed,
                    revised_prompt=item.get("revised_prompt"),
                    size=size,
                    metadata={
                        "provider": self.provider_name,
                        "model": self.model,
                    },
                )
            )

        if not images:
            raise ApiCallFailedError("豆包文生图未能生成任何有效图片")

        return images

    def _validate_args(self, prompt: str, size: tuple[int, int], n: int) -> None:
        if not prompt.strip():
            raise InvalidParamError("生成 Prompt 不能为空")
        if n < 1 or n > 10:
            raise InvalidParamError("候选数量必须在 1 到 10 之间")
        if size[0] <= 0 or size[1] <= 0:
            raise InvalidParamError("图片尺寸必须为正整数")

    async def _sleep_before_retry(self, attempt: int) -> None:
        delay = RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1))
        await asyncio.sleep(delay)
