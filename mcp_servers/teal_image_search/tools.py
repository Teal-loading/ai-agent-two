"""Pexels 图片搜索。

用 httpx 发请求并解析 JSON。
"""

from __future__ import annotations

import logging

import httpx

from mcp_servers.teal_image_search.config import ImageSearchConfig

logger = logging.getLogger(__name__)


class PexelsImageSearch:
    """封装 Pexels 搜索接口。"""

    def __init__(self, config: ImageSearchConfig | None = None) -> None:
        self.config = config or ImageSearchConfig.from_env()

    @property
    def available(self) -> bool:
        return bool(self.config.api_key)

    async def search_medium_images(self, query: str, per_page: int | None = None) -> list[str]:
        """搜索中等尺寸图片，返回图片 URL 列表。"""
        if not self.available:
            raise RuntimeError("未配置 PEXELS_API_KEY，无法使用图片搜索")
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.get(
                self.config.api_url,
                headers={"Authorization": self.config.api_key},
                params={"query": query, "per_page": per_page or self.config.per_page},
            )
            response.raise_for_status()
            payload = response.json()

        urls: list[str] = []
        for photo in payload.get("photos") or []:
            medium = ((photo.get("src") or {}).get("medium")) or ""
            if medium.strip():
                urls.append(medium)
        logger.info("Pexels 搜索「%s」返回 %s 张图片", query, len(urls))
        return urls

    async def fetch_image(self, url: str) -> tuple[bytes, str] | None:
        """下载图片二进制内容，返回 ``(bytes, mime)``；失败或超限返回 None。"""
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
        except Exception as exc:  # noqa: BLE001 - 图片下载失败降级为纯文本结果
            logger.warning("图片下载失败（%s）：%s", url, exc)
            return None

        content = response.content
        if not content or len(content) > self.config.max_image_bytes:
            return None
        mime = response.headers.get("content-type", "image/jpeg").split(";")[0]
        return content, mime
