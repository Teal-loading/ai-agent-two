"""RAG 检索增强。

一次完整的 RAG 调用包含三步：

1. 查询重写：把口语化问题改写为检索友好的查询
2. 向量检索：召回相关片段（可按 ``status`` 过滤身体阶段，可设相关性阈值）
3. 上下文注入：把片段按模板拼进用户消息
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from langchain_core.documents import Document

from app.config import get_settings
from app.prompts import QA_PROMPT_TEMPLATE
from app.rag.rewriter import QueryRewriter
from app.rag.store import DEFAULT_QA_TOP_K, VectorStoreManager, get_vector_store_manager

logger = logging.getLogger(__name__)

CONTEXT_SEPARATOR = "\n\n"


@dataclass(slots=True)
class RagContext:
    """检索结果与拼装好的提示词。"""

    query: str
    documents: list[Document] = field(default_factory=list)

    @property
    def hit(self) -> bool:
        return bool(self.documents)

    @property
    def context(self) -> str:
        return CONTEXT_SEPARATOR.join(document.page_content for document in self.documents)

    def to_prompt(self) -> str:
        """按 QuestionAnswerAdvisor 的默认模板拼装用户消息。"""
        return QA_PROMPT_TEMPLATE.format(query=self.query, question_answer_context=self.context)

    @property
    def sources(self) -> list[str]:
        return [str(document.metadata.get("filename", "")) for document in self.documents]


class RagService:
    """查询重写 + 向量检索的统一入口。"""

    def __init__(
        self,
        store: VectorStoreManager | None = None,
        rewriter: QueryRewriter | None = None,
    ) -> None:
        self._store = store or get_vector_store_manager()
        self._rewriter = rewriter or QueryRewriter()

    async def build(
        self,
        query: str,
        *,
        rewrite: bool = True,
        top_k: int = DEFAULT_QA_TOP_K,
        status: str | None = None,
        score_threshold: float | None = None,
    ) -> RagContext:
        search_query = await self._rewriter.rewrite(query) if rewrite else query
        documents = await self._store.retrieve(search_query, k=top_k, status=status, score_threshold=score_threshold)
        return RagContext(query=search_query, documents=documents)


class FitAppRagCustomAdvisor:
    """自定义检索增强顾问：按身体阶段过滤 + 相似度阈值 + 空上下文兜底。"""

    def __init__(
        self,
        service: RagService,
        status: str,
        top_k: int | None = None,
        score_threshold: float | None = None,
    ) -> None:
        settings = get_settings()
        self.service = service
        self.status = status
        self.top_k = top_k or settings.rag_top_k
        self.score_threshold = score_threshold if score_threshold is not None else settings.rag_similarity_threshold

    async def build(self, query: str) -> RagContext | None:
        """返回检索上下文；``None`` 表示未命中，调用方应直接回复兜底文案。"""
        context = await self.service.build(
            query,
            rewrite=False,
            top_k=self.top_k,
            status=self.status,
            score_threshold=self.score_threshold,
        )
        return context if context.hit else None
