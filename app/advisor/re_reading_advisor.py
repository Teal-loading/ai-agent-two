"""Re2 Advisor。

在请求前改写用户提示词，通过「让模型重读一遍问题」提升大模型的推理能力：

.. code-block:: text

    <原始问题>
    Read the question again: <原始问题>
"""

from __future__ import annotations

from langchain_core.messages import BaseMessage, HumanMessage

from app.prompts import RE_READING_TEMPLATE


def re_read_messages(messages: list[BaseMessage]) -> list[BaseMessage]:
    """返回改写后的消息列表（不修改入参）。"""
    if not messages:
        return messages
    last = messages[-1]
    if not isinstance(last, HumanMessage):
        return messages

    user_text = last.content if isinstance(last.content, str) else str(last.content)
    rewritten = RE_READING_TEMPLATE.format(user_text=user_text)
    return [*messages[:-1], HumanMessage(content=rewritten)]


def apply_re_reading(user_text: str) -> str:
    """只改写单条用户文本。"""
    return RE_READING_TEMPLATE.format(user_text=user_text)
