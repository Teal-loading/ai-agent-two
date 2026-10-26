"""运动健康助手应用文档加载器。

按以下语义切分 Markdown：

- 按 Markdown 分隔线（``---`` / ``***`` / ``___``）把文档切成多「篇」
- 忽略代码块与引用块
- 为每篇补充元信息：``filename``（文件名）与 ``status``（文件名倒数第 3、2 个字，
  即「起步」「突破」「康复」），供按身体阶段过滤检索

.. note::

   知识库正文（``app/resources/document/*.md``）属于契约内容，不做任何内容改动。
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from langchain_core.documents import Document

from app.config import DOCUMENT_DIR

logger = logging.getLogger(__name__)

#: 主题分隔线：--- / *** / ___（允许中间有空格，行首最多 3 个空格）
THEMATIC_BREAK_RE = re.compile(r"^ {0,3}(?:(?:-\s*){3,}|(?:\*\s*){3,}|(?:_\s*){3,})$")
FENCE_PREFIXES = ("```", "~~~")


def read_text(path: Path) -> str:
    """读取文档文本，UTF-8 优先、GB18030 兜底。"""
    raw = path.read_bytes()
    for encoding in ("utf-8", "gb18030"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    logger.warning("文档编码无法识别，按 UTF-8 强制解码：%s", path.name)
    return raw.decode("utf-8", errors="replace")


def split_by_thematic_break(text: str) -> list[str]:
    """按分隔线切分，分隔线本身不保留。"""
    blocks: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        if THEMATIC_BREAK_RE.match(line):
            blocks.append("\n".join(current))
            current = []
            continue
        current.append(line)
    blocks.append("\n".join(current))
    return blocks


def strip_noise(text: str) -> str:
    """剔除代码块与引用块内容。"""
    kept: list[str] = []
    in_code = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(FENCE_PREFIXES):
            in_code = not in_code
            continue
        if in_code:
            continue
        if stripped.startswith(">"):
            continue
        kept.append(line)
    return "\n".join(kept).strip()


def extract_status(filename: str) -> str:
    """取文件名倒数第 3、2 个字作为阶段标签（如「新手起步篇.md」→「起步」）。"""
    stem = filename[: -len(".md")] if filename.endswith(".md") else filename
    return stem[-3:-1] if len(stem) >= 3 else stem


class FitAppDocumentLoader:
    """运动健康助手应用文档加载器。"""

    def __init__(self, document_dir: Path | str | None = None) -> None:
        self.document_dir = Path(document_dir) if document_dir else Path(DOCUMENT_DIR)

    def load_markdowns(self) -> list[Document]:
        """加载目录下全部 Markdown 文档。"""
        documents: list[Document] = []
        paths = sorted(self.document_dir.glob("*.md"))
        if not paths:
            logger.warning("未找到知识库文档：%s", self.document_dir)
            return documents

        for path in paths:
            try:
                text = read_text(path)
            except OSError as exc:
                logger.error("Markdown 文档加载失败：%s（%s）", path, exc)
                continue

            status = extract_status(path.name)
            for block in split_by_thematic_break(text):
                content = strip_noise(block)
                if not content:
                    continue
                documents.append(
                    Document(
                        page_content=content,
                        metadata={"filename": path.name, "status": status},
                    )
                )
        logger.info("已加载 %s 篇文档（%s 个片段）", len(paths), len(documents))
        return documents
