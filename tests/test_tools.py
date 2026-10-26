"""工具测试：文件读写、PDF 生成、终端命令、网页抓取与搜索（网络部分用 mock）。"""

from __future__ import annotations

from pathlib import Path

import httpx

from app.config import get_settings
from app.tools import get_tool_map, tool_names


def test_tool_names_are_stable() -> None:
    assert tool_names() == [
        "readFile",
        "writeFile",
        "searchWeb",
        "scrapeWebPage",
        "downloadResource",
        "executeTerminalCommand",
        "generatePDF",
        "doTerminate",
    ]


def test_tool_schema_preserved() -> None:
    tools = get_tool_map()
    schema = tools["writeFile"].args_schema.model_json_schema()
    assert set(schema["properties"]) == {"fileName", "content"}
    assert schema["properties"]["fileName"]["description"] == "Name of the file to write"
    assert schema["properties"]["content"]["description"] == "Content to write to the file"
    assert tools["readFile"].description == "Read content from a file"
    assert tools["generatePDF"].description == "Generate a PDF file with given content"


def test_file_tools_roundtrip() -> None:
    tools = get_tool_map()
    result = tools["writeFile"].invoke({"fileName": "profile.txt", "content": "运动健康档案"})
    assert "File written successfully to:" in result

    read_back = tools["readFile"].invoke({"fileName": "profile.txt"})
    assert read_back == "运动健康档案"


def test_read_missing_file_returns_error() -> None:
    result = get_tool_map()["readFile"].invoke({"fileName": "not-exists.txt"})
    assert result.startswith("Error reading file:")


def test_generate_pdf() -> None:
    result = get_tool_map()["generatePDF"].invoke(
        {"fileName": "训练计划.pdf", "content": "四周新手减脂计划\n第一周：快走 30 分钟/天"}
    )
    assert result.startswith("PDF generated successfully to:")

    pdf_path = Path(result.split(": ", 1)[1])
    assert pdf_path.exists()
    assert pdf_path.read_bytes()[:4] == b"%PDF"


def test_terminal_tool() -> None:
    result = get_tool_map()["executeTerminalCommand"].invoke({"command": "echo teal-agent"})
    assert "teal-agent" in result


def test_scrape_web_page_with_mock(monkeypatch) -> None:
    def fake_get(url: str, **kwargs):
        return httpx.Response(
            200,
            text="<html><body><h1>运动康复</h1></body></html>",
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx, "get", fake_get)
    result = get_tool_map()["scrapeWebPage"].invoke({"url": "https://example.com"})
    assert "运动康复" in result


def test_search_web_with_mock(monkeypatch) -> None:
    payload = {"organic_results": [{"title": f"结果{i}", "link": f"https://example.com/{i}"} for i in range(8)]}

    def fake_get(url: str, **kwargs):
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)
    result = get_tool_map()["searchWeb"].invoke({"query": "新手减脂"})
    # 只取前 5 条，且为紧凑 JSON
    assert result.count('"title"') == 5
    assert '"title":"结果0"' in result
    assert "结果5" not in result


def test_download_resource_with_mock(monkeypatch) -> None:
    class FakeStream:
        def __init__(self, url: str, **kwargs):
            self.url = url

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def raise_for_status(self) -> None:
            return None

        def iter_bytes(self):
            yield b"fake-image-bytes"

    monkeypatch.setattr(httpx, "stream", lambda method, url, **kwargs: FakeStream(url))
    result = get_tool_map()["downloadResource"].invoke({"url": "https://example.com/a.png", "fileName": "a.png"})
    assert result.startswith("Resource downloaded successfully to:")
    file_path = Path(result.split(": ", 1)[1])
    assert file_path.read_bytes() == b"fake-image-bytes"
    assert file_path.parent == get_settings().file_dir / "download"


def test_terminate_tool() -> None:
    assert get_tool_map()["doTerminate"].invoke({}) == "任务结束"
