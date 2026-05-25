from __future__ import annotations

import asyncio
import base64
import logging
from typing import Any

import httpx

from ..exceptions import ApiCallFailedError, ApiKeyInvalidError, GenerationTimeoutError, InvalidParamError
from .base import CostEstimate, GeneratedImage, ImageGeneratorBase

logger = logging.getLogger(__name__)

VISUAL_API_URL = "https://visual.volcengineapi.com"
GENERATION_TIMEOUT_SECONDS = 90.0
MAX_RETRIES = 3
RETRY_BASE_DELAY_SECONDS = 2.0

# 豆包文生图支持的常见尺寸
ALLOWED_SIZES = {
    (512, 512), (768, 768), (1024, 1024),
    (768, 1024), (1024, 768),
    (864, 1152), (1152, 864),
}


class VolcengineProvider(ImageGeneratorBase):
    """火山引擎豆包文生图 Provider"""

    provider_name = "volcengine"

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        req_key: str = "high_aes_general_v21",
        timeout_seconds: float = GENERATION_TIMEOUT_SECONDS,
        max_retries: int = MAX_RETRIES,
    ) -> None:
        self.access_key = access_key
        self.secret_key = secret_key
        self.req_key = req_key
        self.model = req_key
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
        self._validate_args(prompt, size, n)

        images: list[GeneratedImage] = []
        for i in range(n):
            payload = self._build_payload(prompt, size, seed)
            data = await self._post_with_retry(payload)
            parsed = self._parse_response(data, size, seed)
            images.extend(parsed)

        return images[:n]

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

        image_b64 = base64.b64encode(reference_image).decode("ascii")

        images: list[GeneratedImage] = []
        for i in range(n):
            payload = self._build_payload(prompt, size, seed)
            payload["binary_data_base64"] = [image_b64]
            data = await self._post_with_retry(payload)
            parsed = self._parse_response(data, size, seed)
            images.extend(parsed)

        return images[:n]

    def _build_payload(self, prompt: str, size: tuple[int, int], seed: str | None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "req_key": self.req_key,
            "prompt": prompt,
            "width": size[0],
            "height": size[1],
            "return_url": False,
            "logo_info": {"add_logo": False},
        }
        if seed is not None:
            try:
                payload["seed"] = int(seed)
            except ValueError:
                pass
        return payload

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
        if not self.access_key or not self.secret_key:
            raise ApiKeyInvalidError("未配置火山引擎 AK/SK")

        headers = self._build_headers(payload)
        body_str = self._serialize_body(payload)

        last_error: ApiCallFailedError | GenerationTimeoutError | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.post(
                        VISUAL_API_URL,
                        headers=headers,
                        content=body_str,
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
                raise ApiKeyInvalidError("火山引擎 AK/SK 无效")
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
                raise ApiCallFailedError(
                    "豆包文生图 API 返回错误",
                    {"status_code": response.status_code, "body": response.text[:500]},
                )

            result = response.json()
            code = result.get("code", -1)
            if code != -1 and code != 0:
                message = result.get("message", "未知错误")
                raise ApiCallFailedError(
                    f"豆包文生图业务错误: {message}",
                    {"code": code, "response": str(result)[:500]},
                )
            return result

        raise last_error or ApiCallFailedError("豆包文生图生成失败")

    def _build_headers(self, payload: dict[str, Any]) -> dict[str, str]:
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        timestamp = now.strftime("%Y%m%dT%H%M%SZ")
        date = now.strftime("%Y%m%d")

        return {
            "Content-Type": "application/json",
            "Host": "visual.volcengineapi.com",
            "X-Date": timestamp,
            "X-Content-Sha256": "UNSIGNED-PAYLOAD",
            "Authorization": self._build_authorization(timestamp, date, payload),
        }

    def _build_authorization(
        self,
        timestamp: str,
        date: str,
        payload: dict[str, Any],
    ) -> str:
        import hashlib
        import hmac

        region = "cn-north-1"
        service = "cv"
        algorithm = "HMAC-SHA256"

        credential_scope = f"{date}/{region}/{service}/request"
        canonical_querystring = "Action=CVProcess&Version=2022-08-31"

        body_str = self._serialize_body(payload)
        payload_hash = hashlib.sha256(body_str.encode("utf-8")).hexdigest()

        canonical_headers = (
            f"host:visual.volcengineapi.com\n"
            f"x-content-sha256:UNSIGNED-PAYLOAD\n"
            f"x-date:{timestamp}\n"
        )
        signed_headers = "host;x-content-sha256;x-date"

        canonical_request = "\n".join([
            "POST",
            "/",
            canonical_querystring,
            canonical_headers,
            signed_headers,
            payload_hash,
        ])

        string_to_sign = "\n".join([
            algorithm,
            timestamp,
            credential_scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        ])

        def _hmac_sha256(key: bytes, msg: str) -> bytes:
            return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

        k_date = _hmac_sha256(self.secret_key.encode("utf-8"), date)
        k_region = _hmac_sha256(k_date, region)
        k_service = _hmac_sha256(k_region, service)
        k_signing = _hmac_sha256(k_service, "request")
        signature = hmac.new(k_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

        return f"{algorithm} Credential={self.access_key}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"

    def _serialize_body(self, payload: dict[str, Any]) -> str:
        import json
        return json.dumps(payload, separators=(",", ":"))

    def _parse_response(
        self,
        data: dict[str, Any],
        size: tuple[int, int],
        seed: str | None,
    ) -> list[GeneratedImage]:
        images: list[GeneratedImage] = []

        # 响应格式: {"code": 10000, "data": {"binary_data_base64": ["base64str", ...]}}
        resp_data = data.get("data")
        if not resp_data or not isinstance(resp_data, dict):
            # 尝试旧格式: {"data": [{"b64_json": "..."}]}
            resp_data = data

        b64_list = resp_data.get("binary_data_base64", [])
        if not b64_list:
            # 兼容其他可能的字段名
            b64_list = resp_data.get("image_urls", [])

        if not b64_list:
            raise ApiCallFailedError(
                "豆包文生图响应中未找到图片数据",
                {"response_keys": sorted(data.keys())},
            )

        for b64_str in b64_list:
            if not isinstance(b64_str, str):
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
                    revised_prompt=None,
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
        if n < 1 or n > 6:
            raise InvalidParamError("候选数量必须在 1 到 6 之间")
        if size[0] <= 0 or size[1] <= 0:
            raise InvalidParamError("图片尺寸必须为正整数")

    async def _sleep_before_retry(self, attempt: int) -> None:
        delay = RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1))
        await asyncio.sleep(delay)
