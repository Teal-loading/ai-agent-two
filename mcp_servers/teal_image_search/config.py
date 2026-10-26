"""图片搜索 MCP Server 配置。"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True)
class ImageSearchConfig:
    """Pexels 图片搜索配置（通过环境变量注入，不写死在代码里）。"""

    api_key: str
    api_url: str = "https://api.pexels.com/v1/search"
    per_page: int = 10
    timeout: float = 30.0
    #: 单张图片最大下载体积，超过则只返回文本 URL
    max_image_bytes: int = 3 * 1024 * 1024

    @classmethod
    def from_env(cls) -> ImageSearchConfig:
        return cls(
            api_key=os.getenv("PEXELS_API_KEY", ""),
            api_url=os.getenv("PEXELS_API_URL", cls.api_url),
            per_page=int(os.getenv("PEXELS_PER_PAGE", "10")),
        )


@dataclass(slots=True)
class ServerConfig:
    """MCP 服务运行参数。"""

    name: str = "teal-image-search-mcp-server"
    version: str = "0.0.1"
    transport: str = "stdio"  # stdio | sse | streamable-http
    host: str = "0.0.0.0"
    port: int = 8127

    @classmethod
    def from_env(cls) -> ServerConfig:
        return cls(
            transport=os.getenv("MCP_TRANSPORT", "stdio"),
            host=os.getenv("MCP_HOST", "0.0.0.0"),
            port=int(os.getenv("MCP_PORT", "8127")),
        )
