"""Checkpointer：Agent 状态持久化。

- ``memory``：进程内 MemorySaver，适合本地开发/测试（重启即丢失）
- ``postgres``：AsyncPostgresSaver，把会话状态落到 PostgreSQL，支持断点恢复
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.checkpoint.memory import MemorySaver

from app.config import get_settings

logger = logging.getLogger(__name__)


class CheckpointerManager:
    """管理 Checkpointer 的生命周期（Postgres 版本需要在应用启动/关闭时开闭连接）。"""

    def __init__(self) -> None:
        self._checkpointer: Any = None
        self._context: Any = None

    @property
    def checkpointer(self) -> Any:
        if self._checkpointer is None:
            self._checkpointer = MemorySaver()
        return self._checkpointer

    async def startup(self) -> Any:
        settings = get_settings()
        if settings.manus_checkpointer != "postgres":
            logger.info("Manus Checkpointer: memory（会话状态仅保存在进程内）")
            return self.checkpointer

        if not settings.database_url:
            logger.warning("MANUS_CHECKPOINTER=postgres 但未配置 DATABASE_URL，回退为 memory")
            return self.checkpointer

        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        except ImportError:  # pragma: no cover - 可选依赖
            logger.warning("未安装 langgraph-checkpoint-postgres，回退为 memory Checkpointer")
            return self.checkpointer

        self._context = AsyncPostgresSaver.from_conn_string(settings.database_url)
        saver = await self._context.__aenter__()
        await saver.setup()
        self._checkpointer = saver
        logger.info("Manus Checkpointer: postgres（会话状态持久化到数据库）")
        return saver

    async def shutdown(self) -> None:
        if self._context is not None:
            await self._context.__aexit__(None, None, None)
            self._context = None
            self._checkpointer = None


checkpointer_manager = CheckpointerManager()
