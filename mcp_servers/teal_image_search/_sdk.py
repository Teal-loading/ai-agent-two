"""MCP SDK 兼容层。

MCP Python SDK 在 2.x 中把 ``FastMCP`` 重命名为 ``MCPServer`` 并调整了构造参数，
这里做一层薄适配，使本项目在 1.x 与 2.x 上都能运行。
"""

from __future__ import annotations

from typing import Any

try:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as _Server  # type: ignore[import-not-found]

    SDK_MAJOR = 1
except ModuleNotFoundError:  # pragma: no cover - 取决于安装的 SDK 版本
    from mcp.server.mcpserver import MCPServer as _Server  # type: ignore[import-not-found]

    SDK_MAJOR = 2


def create_server(
    name: str,
    version: str,
    instructions: str,
    host: str,
    port: int,
) -> Any:
    """创建 MCP Server 实例。"""
    if SDK_MAJOR == 1:
        return _Server(name=name, version=version, instructions=instructions, host=host, port=port)
    return _Server(name=name, version=version, instructions=instructions)


def run_server(server: Any, transport: str, host: str, port: int) -> None:
    """按指定传输方式启动（stdio / sse / streamable-http）。"""
    if SDK_MAJOR == 1:
        # 1.x 的 host/port 在构造时注入
        server.run(transport=transport)
    else:
        server.run(transport=transport, host=host, port=port)
