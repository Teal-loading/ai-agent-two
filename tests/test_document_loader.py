"""知识库文档加载测试：元信息、切分、内容保真。"""

from __future__ import annotations

import hashlib
from pathlib import Path

from app.rag.loader import FitAppDocumentLoader, extract_status, split_by_thematic_break

#: 知识库正文的 MD5 指纹：内容属于契约，任何改动都会让测试失败
DOCUMENT_DIGESTS = {
    "运动与健康常见问题 - 新手起步篇.md": "1aee07b415c23a3ab787dc67c6e146ec",
    "运动与健康常见问题 - 进阶突破篇.md": "7f4a912cac9771a71312d3fa5ad3b11c",
    "运动与健康常见问题 - 伤痛康复篇.md": "9ed0ee757c89a188abe684f1b2891428",
}


def test_status_metadata(docs_dir: Path) -> None:
    documents = FitAppDocumentLoader(docs_dir).load_markdowns()
    statuses = {doc.metadata["status"] for doc in documents}
    assert statuses == {"起步", "突破", "康复"}

    filenames = {doc.metadata["filename"] for doc in documents}
    assert filenames == {
        "运动与健康常见问题 - 新手起步篇.md",
        "运动与健康常见问题 - 进阶突破篇.md",
        "运动与健康常见问题 - 伤痛康复篇.md",
    }


def test_extract_status() -> None:
    assert extract_status("运动与健康常见问题 - 新手起步篇.md") == "起步"
    assert extract_status("运动与健康常见问题 - 进阶突破篇.md") == "突破"
    assert extract_status("运动与健康常见问题 - 伤痛康复篇.md") == "康复"


def test_documents_have_content(docs_dir: Path) -> None:
    documents = FitAppDocumentLoader(docs_dir).load_markdowns()
    assert len(documents) >= 3
    for document in documents:
        assert document.page_content.strip()
        # 代码块与引用块应被剔除
        assert "```" not in document.page_content
        assert not any(line.strip().startswith(">") for line in document.page_content.splitlines())


def test_split_by_thematic_break() -> None:
    text = "# 标题\n正文一\n---\n正文二\n***\n正文三"
    blocks = [block.strip() for block in split_by_thematic_break(text)]
    assert blocks == ["# 标题\n正文一", "正文二", "正文三"]


def test_knowledge_base_files_untouched(docs_dir: Path) -> None:
    """知识库正文属于契约内容，不允许被改写（按 MD5 指纹校验）。"""
    files = sorted(docs_dir.glob("*.md"))
    assert {path.name for path in files} == set(DOCUMENT_DIGESTS)

    for path in files:
        digest = hashlib.md5(path.read_bytes()).hexdigest()
        assert digest == DOCUMENT_DIGESTS[path.name], f"文档内容被改动：{path.name}"
