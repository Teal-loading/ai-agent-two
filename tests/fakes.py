"""测试替身：按脚本返回消息的 ChatModel（支持 bind_tools，无需真实 API Key）。"""

from __future__ import annotations

from typing import Any

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class ScriptedChatModel(BaseChatModel):
    """第 n 次调用返回 ``responses[n]``，用于驱动 Think–Act 循环。"""

    responses: list[AIMessage]
    calls: int = 0
    bound_tools: list[Any] | None = None
    seen: list[list[BaseMessage]] = []

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools: Any, **kwargs: Any) -> ScriptedChatModel:
        self.bound_tools = list(tools)
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        index = min(self.calls, len(self.responses) - 1)
        self.calls += 1
        self.seen.append(list(messages))
        return ChatResult(generations=[ChatGeneration(message=self.responses[index])])


def tool_call_message(name: str, args: dict[str, Any], call_id: str = "call-1") -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"name": name, "args": args, "id": call_id, "type": "tool_call"}],
    )
