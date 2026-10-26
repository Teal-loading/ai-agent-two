"""文件操作工具（提供文件读写功能）。"""

from __future__ import annotations

from pathlib import Path

from langchain_core.tools import tool

from app.config import get_settings
from app.tools.schemas import ReadFileInput, WriteFileInput


def file_dir() -> Path:
    """文件读写目录：``{file_save_dir}/file``。"""
    path = get_settings().file_dir / "file"
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_file_text(file_name: str) -> str:
    return (file_dir() / file_name).read_text(encoding="utf-8")


@tool("readFile", args_schema=ReadFileInput, description="Read content from a file")
def read_file(fileName: str) -> str:  # noqa: N803 - 参数名与 Tool Schema 保持一致
    """读取指定文件内容。"""
    try:
        return read_file_text(fileName)
    except Exception as exc:  # noqa: BLE001 - 工具需把异常转成可读文本返回给模型
        return f"Error reading file: {exc}"


@tool("writeFile", args_schema=WriteFileInput, description="Write content to a file")
def write_file(fileName: str, content: str) -> str:  # noqa: N803
    """把内容写入指定文件。"""
    file_path = file_dir() / fileName
    try:
        file_dir().mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return f"File written successfully to: {file_path}"
    except Exception as exc:  # noqa: BLE001
        return f"Error writing to file: {exc}"
