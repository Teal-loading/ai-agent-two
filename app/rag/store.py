"""向量库管理。

两种实现：

- ``memory``：``InMemoryVectorStore``，进程内存储，默认
- ``pgvector``：``PGVector`` + PostgreSQL

初始化是惰性的：只有真正用到检索时才加载文档、做关键词增强、写向量库，
未配置大模型/数据库时自动降级为空检索，保证服务本身仍可启动。
"""

from __future__ import annotations

import asyncio
import logging

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore

from app.config import get_settings
from app.llm import get_embeddings
from app.rag.enricher import MyKeywordEnricher
from app.rag.loader import FitAppDocumentLoader

logger = logging.getLogger(__name__)

#: 问答场景的默认召回条数
DEFAULT_QA_TOP_K = 4


class VectorStoreManager:
    """向量库的懒加载与检索入口。"""

    def __init__(
        self,
        loader: FitAppDocumentLoader | None = None,
        enricher: MyKeywordEnricher | None = None,
        embeddings: Embeddings | None = None,
    ) -> None:
        self._loader = loader or FitAppDocumentLoader()
        self._enricher = enricher
        self._embeddings = embeddings
        self._store: VectorStore | None = None
        self._ready = False
        self._error: str | None = None
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    @property
    def ready(self) -> bool:
        return self._ready

    @property
    def error(self) -> str | None:
        return self._error

    def _build_store(self) -> VectorStore:
        settings = get_settings()
        embeddings = self._embeddings or get_embeddings()

        if settings.vector_store == "pgvector" and settings.database_url:
            from langchain_postgres import PGVector

            connection = settings.vector_database_url or settings.database_url
            # langchain-postgres 需要显式的 psycopg 驱动名
            if connection.startswith("postgresql://"):
                connection = connection.replace("postgresql://", "postgresql+psycopg://", 1)
            logger.info("向量库：pgvector（collection=%s）", settings.vector_table)
            return PGVector(
                embeddings=embeddings,
                collection_name=settings.vector_table,
                connection=connection,
                use_jsonb=True,
            )

        from langchain_core.vectorstores import InMemoryVectorStore

        logger.info("向量库：内存版 InMemoryVectorStore")
        return InMemoryVectorStore(embedding=embeddings)

    async def _ingest(self) -> VectorStore:
        documents = self._loader.load_markdowns()
        if not documents:
            raise RuntimeError("知识库文档为空，无法构建向量库")

        enricher = self._enricher if self._enricher is not None else MyKeywordEnricher()
        try:
            documents = await enricher.enrich_documents(documents)
        except Exception as exc:  # noqa: BLE001 - 关键词增强是可选增强项
            logger.warning("关键词增强跳过：%s", exc)

        store = self._build_store()
        await asyncio.to_thread(store.add_documents, documents)
        logger.info("向量库初始化完成，共写入 %s 个片段", len(documents))
        return store

    async def ensure_ready(self) -> bool:
        """确保向量库可用；失败时返回 False 并记录原因（不抛异常）。"""
        if self._ready:
            return True
        async with self._lock:
            if self._ready:
                return True
            settings = get_settings()
            if not settings.embedding_configured:
                self._error = "未配置 DASHSCOPE_API_KEY，知识库检索不可用"
                logger.warning(self._error)
                return False
            try:
                self._store = await self._ingest()
            except Exception as exc:  # noqa: BLE001
                self._error = f"向量库初始化失败：{exc}"
                logger.exception(self._error)
                return False
            self._ready = True
            return True

    # ------------------------------------------------------------------
    async def retrieve(
        self,
        query: str,
        k: int = DEFAULT_QA_TOP_K,
        status: str | None = None,
        score_threshold: float | None = None,
    ) -> list[Document]:
        """相似度检索；``status`` 用于按身体阶段过滤，``score_threshold`` 为相关性下限。"""
        if not query or not query.strip():
            return []
        if not await self.ensure_ready():
            return []
        assert self._store is not None

        fetch_k = k * 3 if status else k
        try:
            scored = await asyncio.to_thread(self._store.similarity_search_with_relevance_scores, query, fetch_k)
        except Exception as exc:  # noqa: BLE001
            logger.warning("向量检索失败：%s", exc)
            return []

        results: list[Document] = []
        for document, score in scored:
            if status and document.metadata.get("status") != status:
                continue
            if score_threshold is not None and score < score_threshold:
                continue
            results.append(document)
            if len(results) >= k:
                break
        return results


_manager: VectorStoreManager | None = None


def get_vector_store_manager() -> VectorStoreManager:
    global _manager
    if _manager is None:
        _manager = VectorStoreManager()
    return _manager


def reset_vector_store_manager() -> None:
    """测试用：丢弃向量库单例。"""
    global _manager
    _manager = None
