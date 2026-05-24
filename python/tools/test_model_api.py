from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any

import httpx


DEFAULT_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com",
    "doubao": "https://ark.cn-beijing.volces.com/api/v3",
}

DEFAULT_TEXT_MODELS = {
    "openai": "gpt-4o-mini",
    "deepseek": "deepseek-chat",
    # 豆包这里通常要填你在火山 Ark 控制台创建的模型 Endpoint ID。
    "doubao": "",
}

DEFAULT_IMAGE_MODELS = {
    "openai": "gpt-image-1",
    "doubao": "doubao-seedream-4-5-251128",
}

ENV_KEY_NAMES = {
    "openai": "OPENAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "doubao": "DOUBAO_API_KEY",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test LLM/image API connectivity without starting NiuQI2D.",
    )
    parser.add_argument(
        "--provider",
        choices=["openai", "deepseek", "doubao"],
        default="doubao",
        help="API provider to test. Default: doubao.",
    )
    parser.add_argument(
        "--kind",
        choices=["chat", "models", "image"],
        default="chat",
        help=(
            "Test type. 'chat' sends a tiny chat completion request; "
            "'models' calls /models; 'image' sends an image generation request and may incur cost."
        ),
    )
    parser.add_argument("--api-key", default="", help="API key. If omitted, read provider env var.")
    parser.add_argument("--model", default="", help="Model name or Ark Endpoint ID.")
    parser.add_argument("--base-url", default="", help="Override provider base URL.")
    parser.add_argument("--timeout", type=float, default=30.0, help="Request timeout seconds.")
    parser.add_argument("--prompt", default="ping", help="Prompt used for chat/image tests.")
    parser.add_argument(
        "--allow-billable-image-call",
        action="store_true",
        help="Required for --kind image because image generation may incur cost.",
    )
    parser.add_argument(
        "--show-key-prefix",
        action="store_true",
        help="Print the first and last 4 characters of the key for sanity checking.",
    )
    return parser.parse_args()


def compact_json(data: Any) -> str:
    try:
        return json.dumps(data, ensure_ascii=False, indent=2)
    except TypeError:
        return str(data)


def response_excerpt(response: httpx.Response, limit: int = 1200) -> str:
    content_type = response.headers.get("content-type", "")
    try:
        if "json" in content_type:
            text = compact_json(response.json())
        else:
            text = response.text
    except Exception:
        text = response.text
    return text[:limit]


def mask_key(api_key: str) -> str:
    if len(api_key) <= 8:
        return "*" * len(api_key)
    return f"{api_key[:4]}...{api_key[-4:]}"


def build_chat_payload(model: str, prompt: str) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 8,
        "temperature": 0,
    }


def build_image_payload(provider: str, model: str, prompt: str) -> dict[str, Any]:
    if provider == "openai":
        return {
            "model": model,
            "prompt": prompt,
            "size": "1024x1024",
            "n": 1,
        }
    if provider == "doubao":
        return {
            "model": model,
            "prompt": prompt,
            "size": "1920x1920",
            "n": 1,
            "response_format": "url",
        }
    raise ValueError(f"{provider} does not support image test in this script")


def explain_failure(provider: str, kind: str, status_code: int | None, body: str) -> list[str]:
    hints: list[str] = []
    lower_body = body.lower()
    if status_code in (401, 403):
        hints.append("Key 无效、Key 类型不匹配，或当前模型/Endpoint 没有授权。")
    if status_code == 404:
        hints.append("URL 或模型/Endpoint ID 可能不对。豆包 Ark 文本模型通常要填 Endpoint ID。")
    if status_code == 429:
        hints.append("触发限流、余额不足或配额不足。")
    if status_code and status_code >= 500:
        hints.append("服务端临时错误，建议稍后重试或换网络。")
    if "model" in lower_body and ("not" in lower_body or "invalid" in lower_body):
        hints.append("模型字段可疑：检查是否把图片模型填到了文本 API，或把文本 Endpoint 填到了图片 API。")
    if provider == "doubao" and kind == "chat":
        hints.append("豆包文本测试的 --model 建议使用火山 Ark 控制台里的 Endpoint ID。")
    if provider == "doubao" and kind == "image":
        hints.append("豆包图片测试使用 seedream 图片模型，不要填文本 Endpoint ID。")
    return hints


def main() -> int:
    args = parse_args()
    provider: str = args.provider
    kind: str = args.kind
    base_url = (args.base_url or DEFAULT_BASE_URLS[provider]).rstrip("/")
    env_key_name = ENV_KEY_NAMES[provider]
    api_key = args.api_key or os.getenv(env_key_name, "")

    if not api_key:
        print("FAILED: API key is empty.")
        print(f"Pass --api-key or set environment variable {env_key_name}.")
        return 2

    if kind == "image" and not args.allow_billable_image_call:
        print("FAILED: --kind image may incur cost.")
        print("Re-run with --allow-billable-image-call if you really want to call image generation.")
        return 2

    if kind == "chat":
        model = args.model or DEFAULT_TEXT_MODELS[provider]
        path = "/chat/completions"
        payload = build_chat_payload(model, args.prompt)
    elif kind == "models":
        model = args.model
        path = "/models"
        payload = None
    else:
        model = args.model or DEFAULT_IMAGE_MODELS.get(provider, "")
        path = "/images/generations"
        payload = build_image_payload(provider, model, args.prompt)

    if kind != "models" and not model:
        print("FAILED: model is empty.")
        if provider == "doubao" and kind == "chat":
            print("For Doubao chat, pass your Ark Endpoint ID with --model.")
        return 2

    url = f"{base_url}{path}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    print("=== Model API Connectivity Test ===")
    print(f"provider: {provider}")
    print(f"kind:     {kind}")
    print(f"url:      {url}")
    if model:
        print(f"model:    {model}")
    print(f"key env:  {env_key_name}" if not args.api_key else "key src:  --api-key")
    if args.show_key_prefix:
        print(f"key:      {mask_key(api_key)}")

    started = time.perf_counter()
    try:
        with httpx.Client(timeout=args.timeout, trust_env=True) as client:
            if kind == "models":
                response = client.get(url, headers=headers)
            else:
                response = client.post(url, headers=headers, json=payload)
    except httpx.ConnectError as exc:
        print("FAILED: network connection error.")
        print(f"detail: {exc}")
        print("hint: 检查代理、DNS、公司网络、防火墙，或能否直接访问目标域名。")
        return 1
    except httpx.TimeoutException as exc:
        print("FAILED: request timeout.")
        print(f"detail: {exc}")
        print("hint: 检查网络/代理，或用 --timeout 调大超时时间。")
        return 1
    except httpx.HTTPError as exc:
        print("FAILED: HTTP client error.")
        print(f"detail: {exc}")
        return 1

    latency_ms = int((time.perf_counter() - started) * 1000)
    body = response_excerpt(response)
    print(f"status:   {response.status_code}")
    print(f"latency:  {latency_ms}ms")

    if response.status_code >= 400:
        print("FAILED: provider returned an error.")
        print("--- response excerpt ---")
        print(body)
        hints = explain_failure(provider, kind, response.status_code, body)
        if hints:
            print("--- hints ---")
            for hint in hints:
                print(f"- {hint}")
        return 1

    print("SUCCESS: API responded successfully.")
    print("--- response excerpt ---")
    print(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
