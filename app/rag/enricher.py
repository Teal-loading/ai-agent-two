"""基于 AI 的文档元信息增强器。

入库前让大模型为每个片段抽取若干关键词，写入 ``metadata["excerpt_keywords"]``，
检索时可作为辅助信号。
"""

from __future__ import annotations

import asyncio
import logging
import re

from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel

from app.config import get_settings
from app.llm import get_chat_model
from app.prompts import KEYWORD_ENRICH_PROMPT

logger = logging.getLogger(__name__)

MAX_CONCURRENCY = 4
KEYWORD_SEPARATORS = re.compile(r"[,，、;；\n]+")


class MyKeywordEnricher:
    """为文档补充关键词元信息。"""

    def __init__(self, llm: BaseChatModel | None = None, keyword_count: int | None = None) -> None:
        settings = get_settings()
        self._llm = llm
        self.keyword_count = keyword_count or settings.rag_keyword_count

    @property
    def llm(self) -> BaseChatModel:
        if self._llm is None:
            self._llm = get_chat_model()
        return self._llm

    @staticmethod
    def _parse_keywords(raw: str, limit: int) -> list[str]:
        text = raw.strip().strip("[]")
        keywords = [item.strip().strip("\"'") for item in KEYWORD_SEPARATORS.split(text)]
        return [keyword for keyword in keywords if keyword][:limit]

    async def _enrich_one(self, document: Document, semaphore: asyncio.Semaphore) -> Document:
        prompt = KEYWORD_ENRICH_PROMPT.format(count=self.keyword_count, text=document.page_content)
        async with semaphore:
            try:
                response = await self.llm.ainvoke(prompt)
            except Exception as exc:  # noqa: BLE001 - 增强失败不应阻断入库
                logger.warning("关键词增强失败：%s", exc)
                return document
        keywords = self._parse_keywords(str(response.content), self.keyword_count)
        if not keywords:
            return document
        metadata = {**document.metadata, "excerpt_keywords": ", ".join(keywords)}
        return Document(page_content=document.page_content, metadata=metadata)

    async def enrich_documents(self, documents: list[Document]) -> list[Document]:
        semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
        return await asyncio.gather(*(self._enrich_one(document, semaphore) for document in documents))
