"""终端操作工具（ProcessBuilder → subprocess）。"""

from __future__ import annotations

import logging
import subprocess

from langchain_core.tools import tool

from app.config import get_settings
from app.tools.schemas import TerminalCommandInput

logger = logging.getLogger(__name__)


def run_command(command: str, timeout: int | None = None) -> str:
    """执行 shell 命令并返回标准输出。"""
    settings = get_settings()
    try:
        completed = subprocess.run(  # noqa: S602 - 该工具本身就是给智能体执行命令用的
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout or settings.terminal_timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return f"Error executing command: timed out after {timeout or settings.terminal_timeout}s"
    except Exception as exc:  # noqa: BLE001
        return f"Error executing command: {exc}"

    output = completed.stdout or ""
    if completed.returncode != 0:
        output += f"Command execution failed with exit code: {completed.returncode}"
        if completed.stderr:
            output += f"\n{completed.stderr}"
    return output


@tool("executeTerminalCommand", args_schema=TerminalCommandInput, description="Execute a command in the terminal")
def execute_terminal_command(command: str) -> str:
    """在终端执行命令。"""
    logger.info("执行终端命令: %s", command)
    return run_command(command)
