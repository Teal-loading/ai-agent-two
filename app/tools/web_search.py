"""网页搜索工具（SearchAPI + 百度引擎）。"""

from __future__ import annotations

import json

import httpx
from langchain_core.tools import tool

from app.config import get_settings
from app.tools.schemas import WebSearchInput

# SearchAPI 的搜索接口地址
SEARCH_API_URL = "https://www.searchapi.io/api/v1/search"
RESULT_LIMIT = 5


def search_baidu(query: str, api_key: str | None = None, timeout: float = 30.0) -> str:
    """调用 SearchAPI 的百度引擎，返回前 5 条结果的 JSON 文本（以逗号拼接）。"""
    key = api_key if api_key is not None else get_settings().search_api_key
    response = httpx.get(
        SEARCH_API_URL,
        params={"q": query, "api_key": key, "engine": "baidu"},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    organic_results = payload.get("organic_results") or []
    return ",".join(
        json.dumps(item, ensure_ascii=False, separators=(",", ":")) for item in organic_results[:RESULT_LIMIT]
    )


@tool("searchWeb", args_schema=WebSearchInput, description="Search for information from Baidu Search Engine")
def search_web(query: str) -> str:
    """使用百度搜索引擎检索信息。"""
    try:
        return search_baidu(query)
    except Exception as exc:  # noqa: BLE001
        return f"Error searching Baidu: {exc}"
