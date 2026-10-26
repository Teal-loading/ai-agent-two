"""终止工具（让自主规划智能体能够合理地中断）。"""

from __future__ import annotations

from langchain_core.tools import tool

from app.prompts import TERMINATE_TOOL_DESCRIPTION, TERMINATE_TOOL_NAME, TERMINATE_TOOL_RESULT
from app.tools.schemas import TerminateInput


@tool(TERMINATE_TOOL_NAME, args_schema=TerminateInput, description=TERMINATE_TOOL_DESCRIPTION)
def do_terminate() -> str:
    """结束任务。"""
    return TERMINATE_TOOL_RESULT
