"""切词器。

按字符递归切分，使用中文友好的分隔符；默认参数为 200 字 / 100 字重叠 / 最少 10 字。
"""

from __future__ import annotations

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

SEPARATORS = ["\n\n", "\n", "。", "！", "？", "；", " ", ""]


class MyTokenTextSplitter:
    """默认切分与自定义切分能力。"""

    def __init__(
        self,
        chunk_size: int = 200,
        chunk_overlap: int = 100,
        min_chunk_size: int = 10,
    ) -> None:
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=SEPARATORS,
            keep_separator=True,
        )
        self.min_chunk_size = min_chunk_size

    def split_documents(self, documents: list[Document]) -> list[Document]:
        return self._filter(self._splitter.split_documents(documents))

    def split_customized(self, documents: list[Document]) -> list[Document]:
        """按默认参数（200 字 / 100 字重叠 / 最少 10 字）切分。"""
        return self.split_documents(documents)

    def _filter(self, documents: list[Document]) -> list[Document]:
        return [doc for doc in documents if len(doc.page_content.strip()) >= self.min_chunk_size]
