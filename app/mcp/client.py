"""MCP Client。

把 ``mcp-servers.json`` 中声明的 MCP Server 接入为 LangChain 工具，
从而让 FitApp 能像调用本地工具一样调用外部 MCP 能力（高德地图、图片搜索等）。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from langchain_core.tools import BaseTool

from app.config import get_settings

logger = logging.getLogger(__name__)


class McpToolProvider:
    """惰性加载并缓存 MCP 工具。"""

    def __init__(self, config_path: str | Path | None = None) -> None:
        settings = get_settings()
        self.config_path = Path(config_path or settings.mcp_servers_config)
        self._client: Any = None
        self._tools: list[BaseTool] | None = None
        self._error: str | None = None

    # ------------------------------------------------------------------
    def load_config(self) -> dict[str, Any]:
        """读取并解包 ``{"mcpServers": {...}}`` 结构。"""
        if not self.config_path.exists():
            logger.warning("未找到 MCP 配置文件：%s", self.config_path)
            return {}
        payload = json.loads(self.config_path.read_text(encoding="utf-8"))
        servers = payload.get("mcpServers", payload)
        return {name: cfg for name, cfg in servers.items() if isinstance(cfg, dict)}

    async def get_tools(self) -> list[BaseTool]:
        """返回 MCP 工具列表；不可用时返回空列表并记录原因。"""
        if self._tools is not None:
            return self._tools

        servers = self.load_config()
        if not servers:
            self._tools = []
            return self._tools

        try:
            from langchain_mcp_adapters.client import MultiServerMCPClient
        except ImportError:
            self._error = "未安装 langchain-mcp-adapters，MCP 能力不可用"
            logger.warning(self._error)
            self._tools = []
            return self._tools

        try:
            self._client = MultiServerMCPClient(servers)
            self._tools = list(await self._client.get_tools())
            logger.info(
                "已加载 %s 个 MCP 工具：%s",
                len(self._tools),
                [tool.name for tool in self._tools],
            )
        except Exception as exc:  # noqa: BLE001 - MCP 服务不可用不应影响主链路
            self._error = f"MCP 工具加载失败：{exc}"
            logger.exception(self._error)
            self._tools = []
        return self._tools

    @property
    def error(self) -> str | None:
        return self._error


_provider: McpToolProvider | None = None


def get_mcp_tool_provider() -> McpToolProvider:
    global _provider
    if _provider is None:
        _provider = McpToolProvider()
    return _provider


def reset_mcp_tool_provider() -> None:
    """测试用：丢弃单例。"""
    global _provider
    _provider = None
