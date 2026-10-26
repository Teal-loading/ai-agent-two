"""大模型与 Embedding 工厂。

统一走 OpenAI 兼容协议接入阿里云百炼（DashScope compatible-mode），
因此可以复用 ``langchain-openai``，并天然支持 Tool Calling 与流式输出；
同时保留本地 Ollama 作为离线备选。
"""

from __future__ import annotations

import logging
from functools import lru_cache

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

from app.config import get_settings

logger = logging.getLogger(__name__)


class LLMNotConfiguredError(RuntimeError):
    """未配置大模型凭证时抛出，便于上层给出可读提示而不是堆栈。"""


def _require_dashscope_key() -> str:
    settings = get_settings()
    if not settings.dashscope_api_key:
        raise LLMNotConfiguredError(
            "未配置 DASHSCOPE_API_KEY，请在 .env 中填写阿里云百炼 API Key"
            "（参考 .env.example），或将 LLM_PROVIDER 切换为 ollama 使用本地模型。"
        )
    return settings.dashscope_api_key


@lru_cache(maxsize=4)
def get_chat_model(streaming: bool = False) -> BaseChatModel:
    """获取 Chat 模型（按需缓存）。

    :param streaming: 是否开启流式输出，SSE 接口需要置为 True。
    """
    settings = get_settings()

    if settings.llm_provider == "ollama":
        try:
            from langchain_ollama import ChatOllama
        except ImportError as exc:  # pragma: no cover - 可选依赖
            raise LLMNotConfiguredError("使用 Ollama 需要安装 langchain-ollama：pip install langchain-ollama") from exc
        return ChatOllama(
            model=settings.ollama_chat_model,
            base_url=settings.ollama_base_url,
            temperature=settings.chat_temperature,
        )

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.chat_model,
        api_key=_require_dashscope_key(),
        base_url=settings.dashscope_base_url,
        temperature=settings.chat_temperature,
        streaming=streaming,
        timeout=120,
        max_retries=2,
    )


@lru_cache(maxsize=2)
def get_embeddings() -> Embeddings:
    """获取 Embedding 模型（DashScope text-embedding-v3）。"""
    settings = get_settings()

    if settings.llm_provider == "ollama":
        try:
            from langchain_ollama import OllamaEmbeddings
        except ImportError as exc:  # pragma: no cover - 可选依赖
            raise LLMNotConfiguredError("使用 Ollama 需要安装 langchain-ollama：pip install langchain-ollama") from exc
        return OllamaEmbeddings(model="nomic-embed-text", base_url=settings.ollama_base_url)

    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=_require_dashscope_key(),
        base_url=settings.dashscope_base_url,
        dimensions=settings.embedding_dimensions,
        # DashScope 只接受原始文本，不做 token 预切分
        check_embedding_ctx_length=False,
        chunk_size=10,
        timeout=120,
        max_retries=2,
    )


def clear_model_cache() -> None:
    """测试用：清空模型缓存。"""
    get_chat_model.cache_clear()
    get_embeddings.cache_clear()
