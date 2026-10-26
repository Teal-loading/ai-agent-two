"""资源下载工具（httpx 流式下载）。"""

from __future__ import annotations

from pathlib import Path

import httpx
from langchain_core.tools import tool

from app.config import get_settings
from app.tools.schemas import DownloadResourceInput


def download_dir() -> Path:
    path = get_settings().file_dir / "download"
    path.mkdir(parents=True, exist_ok=True)
    return path


def download_to(url: str, file_name: str, timeout: float = 60.0) -> Path:
    file_path = download_dir() / file_name
    with httpx.stream("GET", url, follow_redirects=True, timeout=timeout) as response:
        response.raise_for_status()
        with file_path.open("wb") as handle:
            for chunk in response.iter_bytes():
                handle.write(chunk)
    return file_path


@tool("downloadResource", args_schema=DownloadResourceInput, description="Download a resource from a given URL")
def download_resource(url: str, fileName: str) -> str:  # noqa: N803
    """从指定 URL 下载资源到本地文件。"""
    try:
        file_path = download_to(url, fileName)
        return f"Resource downloaded successfully to: {file_path}"
    except Exception as exc:  # noqa: BLE001
        return f"Error downloading resource: {exc}"
