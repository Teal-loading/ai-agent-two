"""日志 Advisor。

用 LangChain 的 CallbackHandler 记录单次请求与响应，挂在链路上即可。
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import BaseMessage

logger = logging.getLogger(__name__)


def _render(messages: Any) -> str:
    """把 messages 渲染成便于排查的文本。"""
    if not messages:
        return ""
    if isinstance(messages, list) and messages and isinstance(messages[0], list):
        messages = messages[-1]
    parts: list[str] = []
    for message in messages:
        if isinstance(message, BaseMessage):
            parts.append(f"{message.type}: {message.content}")
        else:  # pragma: no cover - 兼容非标准输入
            parts.append(str(message))
    return "\n".join(parts)


def extract_response_text(response: Any) -> str:
    """尽力从 LLMResult 中取出文本，供日志使用。"""
    try:
        generations = getattr(response, "generations", None) or []
        if generations and generations[0]:
            message = getattr(generations[0][0], "message", None)
            if message is not None:
                return str(message.content)
            return str(getattr(generations[0][0], "text", ""))
    except Exception:  # noqa: BLE001 - 日志逻辑永不抛出
        pass
    return ""


class MyLoggerCallback(BaseCallbackHandler):
    """打印 info 级别日志：单次用户提示词与 AI 回复文本。"""

    raise_error = False

    def on_chat_model_start(self, serialized: dict[str, Any], messages: Any, **kwargs: Any) -> None:
        logger.info("AI Request: %s", _render(messages))

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        logger.info("AI Response: %s", extract_response_text(response))

    def on_llm_error(self, error: BaseException, **kwargs: Any) -> None:
        logger.error("AI Error: %s", error)


def logger_callbacks() -> list[BaseCallbackHandler]:
    return [MyLoggerCallback()]
