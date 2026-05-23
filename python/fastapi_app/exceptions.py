from __future__ import annotations

from typing import Any


class NiuQIError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class ApiKeyInvalidError(NiuQIError):
    def __init__(self, message: str = "API Key 无效", details: dict[str, Any] | None = None) -> None:
        super().__init__("API_KEY_INVALID", message, 401, details)


class ApiCallFailedError(NiuQIError):
    def __init__(self, message: str = "API 调用失败", details: dict[str, Any] | None = None) -> None:
        super().__init__("API_CALL_FAILED", message, 502, details)


class GenerationTimeoutError(NiuQIError):
    def __init__(self, message: str = "生成请求超时", details: dict[str, Any] | None = None) -> None:
        super().__init__("TIMEOUT", message, 408, details)


class ResourceNotFoundError(NiuQIError):
    def __init__(self, message: str = "资源不存在", details: dict[str, Any] | None = None) -> None:
        super().__init__("RESOURCE_NOT_FOUND", message, 404, details)


class InvalidParamError(NiuQIError):
    def __init__(self, message: str = "参数无效", details: dict[str, Any] | None = None) -> None:
        super().__init__("INVALID_PARAM", message, 400, details)


class StorageFullError(NiuQIError):
    def __init__(self, message: str = "存储空间不足", details: dict[str, Any] | None = None) -> None:
        super().__init__("STORAGE_FULL", message, 507, details)
