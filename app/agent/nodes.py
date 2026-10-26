"""Think / Act 节点。

- think：拼接 next_step_prompt → 调用带工具的大模型 → 记录助手消息与工具调用意图
- act：执行模型选择的工具 → 把结果包装为 ToolMessage 回写上下文 → 判断是否调用终止工具

循环由 LangGraph StateGraph 驱动（条件边 + 路由），状态由 Checkpointer 负责持久化。
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import uuid4

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool

from app.agent.state import AgentState, ManusState
from app.prompts import TERMINATE_TOOL_NAME, AgentMessages

logger = logging.getLogger(__name__)


def extract_text(content: Any) -> str:
    """兼容 ``str`` 与多模态 content block 列表的文本提取。"""
    if isinstance(content, str):
        return content
    if not content:
        return ""
    parts: list[str] = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(str(block.get("text", "")))
    return "".join(parts)


def _stringify(output: Any) -> str:
    if isinstance(output, str):
        return output
    try:
        return json.dumps(output, ensure_ascii=False, default=str)
    except TypeError:  # pragma: no cover - 极端兜底
        return str(output)


class ThinkActNodes:
    """把 ReAct 的「思考-行动」实现为两个图节点。"""

    def __init__(
        self,
        llm: BaseChatModel,
        tools: list[BaseTool],
        system_prompt: str,
        next_step_prompt: str = "",
        max_steps: int = 20,
    ) -> None:
        self.tools = list(tools)
        self.tool_map: dict[str, BaseTool] = {tool.name: tool for tool in self.tools}
        self.llm = llm.bind_tools(self.tools) if self.tools else llm
        self.system_prompt = system_prompt
        self.next_step_prompt = next_step_prompt
        self.max_steps = max_steps

    # ------------------------------------------------------------------
    # 思考
    # ------------------------------------------------------------------
    async def think(self, state: ManusState) -> dict[str, Any]:
        step = int(state.get("step") or 0) + 1
        history = list(state.get("messages") or [])
        extra: list[Any] = []
        # 1、校验提示词，拼接用户提示词（与原逻辑一致：每次思考都追加 next_step_prompt）
        if self.next_step_prompt:
            extra.append(HumanMessage(content=self.next_step_prompt))

        # 2、调用大模型，获取工具调用结果
        try:
            response = await self.llm.ainvoke([SystemMessage(content=self.system_prompt), *history, *extra])
        except Exception as exc:  # noqa: BLE001 - 模型异常要转成可读文案继续执行
            logger.exception("%s 的思考过程遇到了问题", "TealManus")
            message = AgentMessages.THINK_ERROR + str(exc)
            logger.warning(message)
            return {
                "messages": [*extra, AIMessage(content=message)],
                "step": step,
                "status": AgentState.FINISHED.value,
                "logs": [f"Step {step}: {message}"],
                "last_action": message,
            }

        text = extract_text(response.content)
        tool_calls = list(getattr(response, "tool_calls", None) or [])
        logger.info("TealManus的思考：%s", text)
        logger.info("TealManus选择了 %s 个工具来使用", len(tool_calls))
        for call in tool_calls:
            logger.info("工具名称：%s，参数：%s", call.get("name"), call.get("args"))

        logs: list[str] = []
        update: dict[str, Any] = {
            "messages": [*extra, response],
            "step": step,
            "status": AgentState.RUNNING.value,
        }

        if tool_calls:
            last_action = f"Step {step}: 思考：{text}" if text else ""
        else:
            # 无需工具调用：说明模型已给出最终答复，结束本次任务
            last_action = f"Step {step}: {text}" if text else f"Step {step}: {AgentMessages.THINK_DONE_WITHOUT_ACTION}"
            update["status"] = AgentState.FINISHED.value

        if step >= self.max_steps:
            update["status"] = AgentState.FINISHED.value
            update["max_steps_reached"] = True
            logs.append(AgentMessages.MAX_STEPS_REACHED.format(max_steps=self.max_steps))

        if last_action:
            logs.insert(0, last_action)
        update["logs"] = logs
        update["last_action"] = last_action
        return update

    # ------------------------------------------------------------------
    # 行动
    # ------------------------------------------------------------------
    async def act(self, state: ManusState) -> dict[str, Any]:
        step = int(state.get("step") or 1)
        messages = list(state.get("messages") or [])
        tool_calls = list(getattr(messages[-1], "tool_calls", None) or []) if messages else []
        if not tool_calls:
            return {
                "status": AgentState.FINISHED.value,
                "logs": [f"Step {step}: {AgentMessages.NO_TOOL_TO_CALL}"],
                "last_action": AgentMessages.NO_TOOL_TO_CALL,
            }

        tool_messages: list[ToolMessage] = []
        results: list[str] = []
        terminated = False

        for call in tool_calls:
            name = str(call.get("name"))
            args = call.get("args") or {}
            call_id = str(call.get("id") or uuid4())
            tool = self.tool_map.get(name)

            if tool is None:
                output = f"Error: tool {name} not found"
            else:
                try:
                    output = _stringify(await tool.ainvoke(args))
                except Exception as exc:  # noqa: BLE001 - 工具异常回传给模型自行决策
                    logger.exception("工具 %s 执行失败", name)
                    output = f"Error executing tool {name}: {exc}"

            tool_messages.append(ToolMessage(content=output, tool_call_id=call_id, name=name))
            results.append(AgentMessages.TOOL_RESULT.format(name=name, result=output))
            if name == TERMINATE_TOOL_NAME:
                terminated = True

        joined = "\n".join(results)
        logger.info(joined)
        status = AgentState.FINISHED.value if terminated else AgentState.RUNNING.value
        # 流式输出与结果列表都带 "Step N: " 前缀
        step_text = f"Step {step}: {joined}"
        return {
            "messages": tool_messages,
            "status": status,
            "logs": [step_text],
            "last_action": step_text,
        }
