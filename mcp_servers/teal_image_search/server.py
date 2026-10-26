"""图片搜索 MCP Server。

基于 MCP Python SDK 的自定义 Server，把 Pexels 图片检索封装成标准工具：

- 工具名 / 描述 / 参数为稳定的 MCP 契约（``searchImage`` / ``query``）
- 返回文本（图片 URL 列表）+ 图片资源（首图预览），体现 MCP 的多内容返回能力
- 支持 stdio 与 SSE 两种传输方式

启动：

.. code-block:: bash

    # stdio（被 MCP Client 拉起，默认）
    python -m mcp_servers.teal_image_search.server
    # SSE
    MCP_TRANSPORT=sse MCP_PORT=8127 python -m mcp_servers.teal_image_search.server
"""

from __future__ import annotations

import base64
import logging
from typing import Annotated, Any

from mcp.types import ImageContent, TextContent
from pydantic import Field

from mcp_servers.teal_image_search._sdk import create_server, run_server
from mcp_servers.teal_image_search.config import ServerConfig
from mcp_servers.teal_image_search.tools import PexelsImageSearch

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

server_config = ServerConfig.from_env()
search_client = PexelsImageSearch()

mcp = create_server(
    name=server_config.name,
    version=server_config.version,
    instructions="图片搜索 MCP 服务：根据关键词检索网络图片，返回图片地址与首图预览。",
    host=server_config.host,
    port=server_config.port,
)


@mcp.tool(name="searchImage", description="search image from web", structured_output=False)
async def search_image(
    query: Annotated[str, Field(description="Search query keyword")],
) -> list[Any]:
    """按关键词搜索网络图片。"""
    try:
        urls = await search_client.search_medium_images(query)
    except Exception as exc:  # noqa: BLE001 - 工具错误以文本返回，由模型决定后续动作
        logger.exception("图片搜索失败")
        return [TextContent(type="text", text=f"Error search image: {exc}")]

    contents: list[Any] = [TextContent(type="text", text=",".join(urls))]
    if urls:
        download = await search_client.fetch_image(urls[0])
        if download is not None:
            data, mime = download
            contents.append(
                ImageContent(
                    type="image",
                    data=base64.b64encode(data).decode("ascii"),
                    mimeType=mime,
                )
            )
    return contents


def main() -> None:
    transport = server_config.transport
    logger.info(
        "%s 启动（transport=%s, host=%s, port=%s）",
        server_config.name,
        transport,
        server_config.host,
        server_config.port,
    )
    run_server(mcp, transport, server_config.host, server_config.port)


if __name__ == "__main__":
    main()
