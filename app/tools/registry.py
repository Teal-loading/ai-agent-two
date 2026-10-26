"""集中的工具注册。

注册顺序即模型看到的工具顺序，调整顺序会改变模型的工具选择偏好。
"""

from __future__ import annotations

import logging
from functools import lru_cache

from langchain_core.tools import BaseTool

from app.tools.file_operation import read_file, write_file
from app.tools.pdf_generation import generate_pdf
from app.tools.resource_download import download_resource
from app.tools.terminal_operation import execute_terminal_command
from app.tools.terminate import do_terminate
from app.tools.web_scraping import scrape_web_page
from app.tools.web_search import search_web

logger = logging.getLogger(__name__)

#: 全部内置工具（顺序固定，勿随意调整）
ALL_TOOLS: list[BaseTool] = [
    read_file,
    write_file,
    search_web,
    scrape_web_page,
    download_resource,
    execute_terminal_command,
    generate_pdf,
    do_terminate,
]


@lru_cache(maxsize=1)
def get_tools() -> tuple[BaseTool, ...]:
    """返回内置工具元组（供 Agent / FitApp 复用）。"""
    return tuple(ALL_TOOLS)


def get_tool_map() -> dict[str, BaseTool]:
    """返回 ``工具名 -> 工具`` 映射，便于按模型返回的 name 分发执行。"""
    return {tool.name: tool for tool in get_tools()}


def tool_names() -> list[str]:
    return [tool.name for tool in get_tools()]
