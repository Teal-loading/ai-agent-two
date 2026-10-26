"""Teal 的 AI 超级智能体（拥有自主规划能力，可以直接使用）。

用 LangGraph ``StateGraph`` 编排 Think–Act 循环：

.. code-block:: text

    START → think ─┬─(有工具调用)→ act ─┬─(未终止)→ think
                   └─(无工具调用)→ END  └─(已终止/异常)→ END

附加能力：状态快照与断点恢复（Checkpointer）、按 thread_id 隔离的会话上下文、
以及基于 ``astream`` 的逐步流式输出。
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph

from app.agent.checkpoint import checkpointer_manager
from app.agent.nodes import ThinkActNodes
from app.agent.state import AgentState, ManusState
from app.config import get_settings
from app.llm import get_chat_model
from app.prompts import (
    TEAL_MANUS_NEXT_STEP_PROMPT,
    TEAL_MANUS_SYSTEM_PROMPT,
    AgentMessages,
)
from app.tools.registry import get_tools

logger = logging.getLogger(__name__)


class AgentRunError(RuntimeError):
    """智能体运行前置校验失败。"""


class TealManus:
    """自主规划型超级智能体。"""

    name = "tealManus"

    def __init__(
        self,
        llm: BaseChatModel | None = None,
        tools: list[BaseTool] | None = None,
        checkpointer: Any = None,
        *,
        system_prompt: str = TEAL_MANUS_SYSTEM_PROMPT,
        next_step_prompt: str = TEAL_MANUS_NEXT_STEP_PROMPT,
        max_steps: int | None = None,
    ) -> None:
        settings = get_settings()
        self.system_prompt = system_prompt
        self.next_step_prompt = next_step_prompt
        self.max_steps = max_steps or settings.manus_max_steps
        self.nodes = ThinkActNodes(
            llm=llm or get_chat_model(),
            tools=tools if tools is not None else list(get_tools()),
            system_prompt=system_prompt,
            next_step_prompt=next_step_prompt,
            max_steps=self.max_steps,
        )
        self.graph = self._build(checkpointer or checkpointer_manager.checkpointer)

    # ------------------------------------------------------------------
    # 图构建
    # ------------------------------------------------------------------
    def _build(self, checkpointer: Any):
        graph = StateGraph(ManusState)
        graph.add_node("think", self.nodes.think)
        graph.add_node("act", self.nodes.act)
        graph.add_edge(START, "think")
        graph.add_conditional_edges(
            "think",
            self._route_after_think,
            {"act": "act", "end": END},
        )
        graph.add_conditional_edges(
            "act",
            self._route_after_act,
            {"think": "think", "end": END},
        )
        return graph.compile(checkpointer=checkpointer)

    @staticmethod
    def _finished(state: ManusState) -> bool:
        return state.get("status") in (AgentState.FINISHED.value, AgentState.ERROR.value)

    def _route_after_think(self, state: ManusState) -> str:
        if self._finished(state):
            return "end"
        messages = state.get("messages") or []
        has_tool_calls = bool(messages and getattr(messages[-1], "tool_calls", None))
        return "act" if has_tool_calls else "end"

    def _route_after_act(self, state: ManusState) -> str:
        return "end" if self._finished(state) else "think"

    # ------------------------------------------------------------------
    # 执行
    # ------------------------------------------------------------------
    def _config(self, thread_id: str) -> dict[str, Any]:
        return {
            "configurable": {"thread_id": thread_id},
            # 每一步涉及 think/act 两个节点，预留足够深度
            "recursion_limit": self.max_steps * 2 + 10,
        }

    def _initial_state(self, user_prompt: str) -> ManusState:
        return {
            "messages": [HumanMessage(content=user_prompt)],
            "step": 0,
            "status": AgentState.RUNNING.value,
            "logs": [],
            "last_action": "",
            "max_steps_reached": False,
        }

    @staticmethod
    def _validate(user_prompt: str, *, streaming: bool) -> None:
        if not user_prompt or not user_prompt.strip():
            raise AgentRunError(
                AgentMessages.STREAM_CANNOT_RUN_WITH_EMPTY_PROMPT
                if streaming
                else AgentMessages.CANNOT_RUN_WITH_EMPTY_PROMPT
            )

    async def run(self, user_prompt: str, thread_id: str | None = None) -> str:
        """同步执行（一次性返回全部步骤结果）。"""
        self._validate(user_prompt, streaming=False)
        thread_id = thread_id or f"{get_settings().manus_thread_prefix}-{uuid.uuid4().hex}"
        state = await self.graph.ainvoke(self._initial_state(user_prompt), config=self._config(thread_id))
        return "\n".join(state.get("logs") or [])

    async def run_stream(self, user_prompt: str, thread_id: str | None = None) -> AsyncIterator[str]:
        """流式执行：按步骤产出可读文本，供 SSE 增量推送。"""
        if not user_prompt or not user_prompt.strip():
            yield AgentMessages.STREAM_CANNOT_RUN_WITH_EMPTY_PROMPT
            return

        thread_id = thread_id or f"{get_settings().manus_thread_prefix}-{uuid.uuid4().hex}"
        max_steps_reached = False
        try:
            async for update in self.graph.astream(
                self._initial_state(user_prompt),
                config=self._config(thread_id),
                stream_mode="updates",
            ):
                for _node, delta in update.items():
                    if not isinstance(delta, dict):
                        continue
                    if delta.get("max_steps_reached"):
                        max_steps_reached = True
                    action = delta.get("last_action")
                    if action:
                        yield action
        except Exception as exc:  # noqa: BLE001 - 流式异常也要推给前端
            logger.exception("TealManus 执行失败")
            yield AgentMessages.STREAM_EXECUTION_ERROR + str(exc)
            return

        if max_steps_reached:
            yield AgentMessages.STREAM_MAX_STEPS_REACHED.format(max_steps=self.max_steps)


_teal_manus: TealManus | None = None


def get_teal_manus() -> TealManus:
    """返回智能体单例（图本身无状态，会话状态由 Checkpointer 按 thread_id 管理）。"""
    global _teal_manus
    if _teal_manus is None:
        _teal_manus = TealManus()
    return _teal_manus


def reset_teal_manus() -> None:
    """测试/热更新用：丢弃单例。"""
    global _teal_manus
    _teal_manus = None
