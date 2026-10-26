"""PDF 生成工具。

使用 ReportLab 内置的 CID 字体 ``STSong-Light``，无需外挂字体文件即可正确输出中文。
"""

from __future__ import annotations

import logging
from pathlib import Path

from langchain_core.tools import tool
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas as pdf_canvas

from app.config import get_settings
from app.tools.schemas import GeneratePdfInput

logger = logging.getLogger(__name__)

FONT_NAME = "STSong-Light"
FONT_SIZE = 12
LEADING = 20
MARGIN = 56
_registered = False


def pdf_dir() -> Path:
    path = get_settings().file_dir / "pdf"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _ensure_font() -> None:
    global _registered
    if not _registered:
        pdfmetrics.registerFont(UnicodeCIDFont(FONT_NAME))
        _registered = True


def _wrap_line(text: str, max_width: float, font: str, size: int) -> list[str]:
    """按字符宽度换行，兼容中英文混排。"""
    lines: list[str] = []
    current = ""
    for char in text:
        if char == "\n":
            lines.append(current)
            current = ""
            continue
        if pdfmetrics.stringWidth(current + char, font, size) > max_width and current:
            lines.append(current)
            current = char
        else:
            current += char
    lines.append(current)
    return lines


def write_pdf(file_name: str, content: str) -> Path:
    """把纯文本内容渲染为 PDF，返回文件路径。"""
    _ensure_font()
    file_path = pdf_dir() / file_name
    width, height = A4
    usable_width = width - MARGIN * 2

    pdf = pdf_canvas.Canvas(str(file_path), pagesize=A4)
    pdf.setFont(FONT_NAME, FONT_SIZE)
    y = height - MARGIN

    for raw_line in content.splitlines() or [""]:
        for line in _wrap_line(raw_line, usable_width, FONT_NAME, FONT_SIZE):
            if y < MARGIN:
                pdf.showPage()
                pdf.setFont(FONT_NAME, FONT_SIZE)
                y = height - MARGIN
            pdf.drawString(MARGIN, y, line)
            y -= LEADING

    pdf.save()
    return file_path


@tool("generatePDF", args_schema=GeneratePdfInput, description="Generate a PDF file with given content")
def generate_pdf(fileName: str, content: str) -> str:  # noqa: N803
    """根据给定内容生成 PDF 文件。"""
    try:
        file_path = write_pdf(fileName, content)
        return f"PDF generated successfully to: {file_path}"
    except Exception as exc:  # noqa: BLE001
        logger.exception("生成 PDF 失败")
        return f"Error generating PDF: {exc}"
