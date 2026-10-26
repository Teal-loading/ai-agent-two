"""会话记忆：窗口裁剪 + 可插拔存储。

把「存储」与「窗口策略」拆开：``InMemoryMessageStore`` / ``FileMessageStore`` 负责存，
``WindowChatMemory`` 负责按条数裁剪（默认保留最近 20 条），持久化格式为可读的 JSON。
"""

from __future__ import annotations

import json
import logging
import threading
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from langchain_core.messages import BaseMessage, message_to_dict, messages_from_dict

from app.config import get_settings

logger = logging.getLogger(__name__)


class MessageStore(Protocol):
    """消息存储抽象。"""

    def load(self, conversation_id: str) -> list[BaseMessage]: ...

    def save(self, conversation_id: str, messages: list[BaseMessage]) -> None: ...

    def clear(self, conversation_id: str) -> None: ...


class InMemoryMessageStore:
    """进程内存储（默认）。"""

    def __init__(self) -> None:
        self._data: dict[str, list[BaseMessage]] = {}

    def load(self, conversation_id: str) -> list[BaseMessage]:
        return list(self._data.get(conversation_id, []))

    def save(self, conversation_id: str, messages: list[BaseMessage]) -> None:
        self._data[conversation_id] = list(messages)

    def clear(self, conversation_id: str) -> None:
        self._data.pop(conversation_id, None)


class FileMessageStore:
    """基于文件持久化的会话存储（JSON 序列化）。"""

    def __init__(self, directory: str | Path) -> None:
        self.base_dir = Path(directory)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _path(self, conversation_id: str) -> Path:
        # 防止会话 ID 里的路径分隔符逃逸出目录
        safe_id = conversation_id.replace("/", "_").replace("\\", "_") or "default"
        return self.base_dir / f"{safe_id}.json"

    def load(self, conversation_id: str) -> list[BaseMessage]:
        path = self._path(conversation_id)
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return messages_from_dict(payload)
        except Exception as exc:  # noqa: BLE001 - 记忆文件损坏不应阻断对话
            logger.warning("读取会话记忆失败（%s）：%s", path, exc)
            return []

    def save(self, conversation_id: str, messages: list[BaseMessage]) -> None:
        path = self._path(conversation_id)
        payload = [message_to_dict(message) for message in messages]
        with self._lock:
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def clear(self, conversation_id: str) -> None:
        path = self._path(conversation_id)
        if path.exists():
            path.unlink()


class WindowChatMemory:
    """只保留最近 ``max_messages`` 条消息的会话记忆。"""

    def __init__(self, store: MessageStore | None = None, max_messages: int | None = None) -> None:
        settings = get_settings()
        self._store = store or InMemoryMessageStore()
        self.max_messages = max_messages or settings.chat_memory_max_messages

    def get(self, conversation_id: str) -> list[BaseMessage]:
        return self._store.load(conversation_id)

    def add(self, conversation_id: str, messages: list[BaseMessage]) -> list[BaseMessage]:
        merged = self._store.load(conversation_id) + list(messages)
        trimmed = merged[-self.max_messages :] if self.max_messages > 0 else merged
        self._store.save(conversation_id, trimmed)
        return trimmed

    def clear(self, conversation_id: str) -> None:
        self._store.clear(conversation_id)


@lru_cache(maxsize=1)
def get_chat_memory() -> WindowChatMemory:
    """按配置构建默认会话记忆（memory / file）。"""
    settings = get_settings()
    if settings.chat_memory == "file":
        logger.info("会话记忆：file（%s）", settings.chat_memory_dir)
        return WindowChatMemory(store=FileMessageStore(settings.chat_memory_dir))
    return WindowChatMemory()


def reset_chat_memory() -> None:
    """测试用：清除单例。"""
    get_chat_memory.cache_clear()
