"""图片搜索 MCP Server 测试（离线，外部请求全部 mock）。"""

from __future__ import annotations

import httpx

from mcp_servers.teal_image_search import server
from mcp_servers.teal_image_search.config import ImageSearchConfig
from mcp_servers.teal_image_search.tools import PexelsImageSearch


def _schema(tool: object) -> dict:
    schema = getattr(tool, "input_schema", None) or getattr(tool, "inputSchema", None)
    assert schema is not None
    return schema


async def test_tool_schema_is_stable() -> None:
    tools = await server.mcp.list_tools()
    tool = next(item for item in tools if item.name == "searchImage")
    assert tool.description == "search image from web"
    schema = _schema(tool)
    assert list(schema["properties"]) == ["query"]
    assert schema["properties"]["query"]["description"] == "Search query keyword"
    assert schema["required"] == ["query"]


async def test_missing_api_key_returns_text_error() -> None:
    result = await server.search_image("fitness")
    assert len(result) == 1
    assert result[0].type == "text"
    assert result[0].text.startswith("Error search image:")


def _fake_client(payload: dict):
    class FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args) -> bool:
            return False

        async def get(self, url: str, **kwargs):
            request = httpx.Request("GET", url)
            if url.endswith("/search"):
                return httpx.Response(200, json=payload, request=request)
            return httpx.Response(
                200,
                content=b"\xff\xd8\xff-fake-jpeg",
                headers={"content-type": "image/jpeg"},
                request=request,
            )

    return FakeAsyncClient


async def test_search_and_fetch_image(monkeypatch) -> None:
    payload = {
        "photos": [
            {"src": {"medium": "https://img.example.com/1.jpg"}},
            {"src": {"medium": "https://img.example.com/2.jpg"}},
            {"src": {}},
        ]
    }
    monkeypatch.setattr("mcp_servers.teal_image_search.tools.httpx.AsyncClient", _fake_client(payload))

    client = PexelsImageSearch(ImageSearchConfig(api_key="test-key"))
    urls = await client.search_medium_images("健身")
    assert urls == ["https://img.example.com/1.jpg", "https://img.example.com/2.jpg"]

    downloaded = await client.fetch_image(urls[0])
    assert downloaded is not None
    data, mime = downloaded
    assert data.startswith(b"\xff\xd8\xff")
    assert mime == "image/jpeg"


async def test_server_returns_text_and_image(monkeypatch) -> None:
    payload = {"photos": [{"src": {"medium": "https://img.example.com/1.jpg"}}]}
    monkeypatch.setattr("mcp_servers.teal_image_search.tools.httpx.AsyncClient", _fake_client(payload))

    server.search_client = PexelsImageSearch(ImageSearchConfig(api_key="test-key"))
    try:
        contents = await server.search_image("健身")
    finally:
        server.search_client = PexelsImageSearch()

    assert contents[0].type == "text"
    assert contents[0].text == "https://img.example.com/1.jpg"
    assert contents[1].type == "image"
    # mcp 1.x 字段名为 mimeType，2.x 为 mime_type
    mime = getattr(contents[1], "mime_type", None) or getattr(contents[1], "mimeType", None)
    assert mime == "image/jpeg"
