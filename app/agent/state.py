"""智能体状态定义。

用 LangGraph 的 StateGraph 编排执行流程：TypedDict 声明图状态，
``add_messages`` 自主维护消息上下文，Checkpointer 负责持久化。
"""

from __future__ import annotations

import operator
from enum import StrEnum
from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class AgentState(StrEnum):
    """代理执行状态。"""

    IDLE = "IDLE"
    RUNNING = "RUNNING"
    FINISHED = "FINISHED"
    ERROR = "ERROR"


class ManusState(TypedDict, total=False):
    """Super Agent 的图状态。

    :param messages: 完整消息上下文（含工具消息），``add_messages`` 负责去重追加
    :param step: 当前执行步数（从 1 开始）
    :param status: 当前状态，取值见 :class:`AgentState`
    :param logs: 每一步的可读结果，用于接口一次性返回与前端展示
    :param last_action: 本轮节点的结果文本（供流式输出即时推送）
    :param max_steps_reached: 是否因达到最大步数而终止
    """

    messages: Annotated[list[AnyMessage], add_messages]
    step: int
    status: str
    logs: Annotated[list[str], operator.add]
    last_action: str
    max_steps_reached: bool
