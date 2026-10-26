"""示例：直接用 HTTP 调用大模型（不依赖任何框架）。

运行：
    python examples/http_invoke.py
"""

from __future__ import annotations

import os

import httpx

URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"


def main() -> None:
    api_key = os.getenv("DASHSCOPE_API_KEY", "")
    if not api_key:
        raise SystemExit("请先设置环境变量 DASHSCOPE_API_KEY")

    payload = {
        "model": "qwen-plus",
        "input": {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "你是谁？"},
            ]
        },
        "parameters": {"result_format": "message"},
    }

    response = httpx.post(
        URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    response.raise_for_status()
    print(response.json()["output"]["choices"][0]["message"]["content"])


if __name__ == "__main__":
    main()
