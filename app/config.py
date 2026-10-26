"""应用配置。

统一从环境变量 / ``.env`` 读取，主要配置项如下：

===============  ==============================  ==========================
配置组             .env                            说明
===============  ==============================  ==========================
server           SERVER_PORT                     服务端口，默认 8123
dashscope        DASHSCOPE_API_KEY / CHAT_MODEL  阿里云百炼（兼容 OpenAI 协议）
ollama           OLLAMA_BASE_URL / ...           本地 Ollama 模型
search-api       SEARCH_API_KEY                  SearchAPI 联网搜索
vector-store     VECTOR_STORE / DATABASE_URL     向量库（memory / pgvector）
===============  ==============================  ==========================
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent
RESOURCE_DIR = BASE_DIR / "resources"
DOCUMENT_DIR = RESOURCE_DIR / "document"
PROJECT_ROOT = BASE_DIR.parent


class Settings(BaseSettings):
    """全局配置（线程/协程安全，通过 :func:`get_settings` 获取单例）。"""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---------- 应用 ----------
    app_name: str = "ai-agent-one"
    app_version: str = "0.0.1"
    server_port: int = 8123
    api_prefix: str = "/api"
    reload: bool = False
    log_level: str = "INFO"
    # 允许任意来源并携带凭证（浏览器不能对 "*" 携带凭证，故回显来源）
    cors_origin_pattern: str = ".*"

    # ---------- 大模型 ----------
    llm_provider: Literal["dashscope", "ollama"] = "dashscope"
    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    chat_model: str = "qwen-plus"
    chat_temperature: float = 0.7
    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "gemma3:1b"

    # ---------- 向量化 / 向量库 ----------
    embedding_model: str = "text-embedding-v3"
    embedding_dimensions: int = 1536
    vector_store: Literal["memory", "pgvector"] = "memory"
    vector_table: str = "vector_store"
    database_url: str = ""
    #: pgvector 专用连接串（留空则复用 DATABASE_URL，并自动补上 +psycopg 驱动）
    vector_database_url: str = ""
    rag_top_k: int = 3
    rag_similarity_threshold: float = 0.5
    rag_keyword_count: int = 5

    # ---------- 会话记忆 ----------
    chat_memory: Literal["memory", "file"] = "memory"
    chat_memory_dir: str = "tmp/chat-memory"
    chat_memory_max_messages: int = 20

    # ---------- 文件 / 工具 ----------
    file_save_dir: str = "tmp"
    search_api_key: str = ""
    terminal_timeout: int = 60

    # ---------- 智能体 ----------
    manus_max_steps: int = 20
    manus_checkpointer: Literal["memory", "postgres"] = "memory"
    manus_thread_prefix: str = "manus"

    # ---------- MCP ----------
    mcp_servers_config: str = "mcp-servers.json"
    pexels_api_key: str = ""
    mcp_server_port: int = 8127

    # ---------- 可选：阿里云百炼知识库 ----------
    dashscope_knowledge_index: str = "运动健康助手"
    dashscope_app_id: str = ""

    @field_validator("file_save_dir", "chat_memory_dir", "mcp_servers_config")
    @classmethod
    def _expand_relative(cls, value: str) -> str:
        """相对路径统一按项目根目录解析，避免受启动目录影响。"""
        path = Path(value)
        return str(path if path.is_absolute() else PROJECT_ROOT / path)

    # ------------------------------------------------------------------
    # 便捷属性
    # ------------------------------------------------------------------
    @property
    def llm_configured(self) -> bool:
        """是否具备调用大模型的条件（ollama 本地模型无需 key）。"""
        return self.llm_provider == "ollama" or bool(self.dashscope_api_key)

    @property
    def embedding_configured(self) -> bool:
        return bool(self.dashscope_api_key)

    @property
    def file_dir(self) -> Path:
        return Path(self.file_save_dir)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """返回全局配置单例。"""
    return Settings()


def reset_settings_cache() -> None:
    """测试用：清除配置缓存。"""
    get_settings.cache_clear()
