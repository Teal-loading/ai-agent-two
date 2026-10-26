"""``app.rag`` —— 检索增强生成（文档加载、切分、向量库、检索顾问）。"""

from app.rag.advisors import FitAppRagCustomAdvisor, RagContext, RagService
from app.rag.cloud import DashScopeKnowledgeAdvisor
from app.rag.enricher import MyKeywordEnricher
from app.rag.loader import FitAppDocumentLoader
from app.rag.rewriter import QueryRewriter
from app.rag.splitter import MyTokenTextSplitter
from app.rag.store import VectorStoreManager, get_vector_store_manager, reset_vector_store_manager

__all__ = [
    "DashScopeKnowledgeAdvisor",
    "FitAppDocumentLoader",
    "FitAppRagCustomAdvisor",
    "MyKeywordEnricher",
    "MyTokenTextSplitter",
    "QueryRewriter",
    "RagContext",
    "RagService",
    "VectorStoreManager",
    "get_vector_store_manager",
    "reset_vector_store_manager",
]
